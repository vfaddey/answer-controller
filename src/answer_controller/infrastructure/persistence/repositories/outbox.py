from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from answer_controller.application.ports import OutboxRepository
from answer_controller.domain.entities import OutboxNotification
from answer_controller.domain.enums import OutboxStatus
from answer_controller.infrastructure.persistence.tables import outbox_notifications


class SqlAlchemyOutboxRepository(OutboxRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_many_if_absent(self, notifications: list[OutboxNotification]) -> int:
        if not notifications:
            return 0
        statement = (
            insert(outbox_notifications)
            .values(
                [
                    {
                        "id": notification.id,
                        "ticket_id": notification.ticket_id,
                        "threshold": notification.threshold,
                        "direction": notification.direction,
                        "status": notification.status,
                        "created_at": notification.created_at,
                        "sent_at": notification.sent_at,
                        "attempts": notification.attempts,
                        "last_error": notification.last_error,
                    }
                    for notification in notifications
                ]
            )
            .on_conflict_do_nothing(constraint="uq_outbox_ticket_threshold")
            .returning(outbox_notifications.c.id)
        )
        return len((await self._session.execute(statement)).scalars().all())

    async def claim_batch(self, limit: int) -> list[OutboxNotification]:
        statement = (
            select(OutboxNotification)
            .where(outbox_notifications.c.status == OutboxStatus.PENDING)
            .order_by(outbox_notifications.c.created_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        notifications = list((await self._session.execute(statement)).scalars())
        for notification in notifications:
            notification.mark_processing()
        return notifications
