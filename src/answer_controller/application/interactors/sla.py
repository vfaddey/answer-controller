from datetime import UTC, datetime
from uuid import uuid4

from answer_controller.application.ports import (
    OutboxRepository,
    TicketRepository,
    TransactionManager,
)
from answer_controller.domain.entities import OutboxNotification
from answer_controller.domain.enums import OutboxStatus


class CheckSlaInteractor:
    def __init__(
        self,
        tickets: TicketRepository,
        outbox: OutboxRepository,
        tm: TransactionManager,
        warning_seconds: int,
        overdue_seconds: int,
        batch_size: int,
    ) -> None:
        self._tickets = tickets
        self._outbox = outbox
        self._tm = tm
        self._warning_seconds = warning_seconds
        self._overdue_seconds = overdue_seconds
        self._batch_size = batch_size

    async def execute(self) -> int:
        now = datetime.now(UTC)
        notifications = []
        for ticket in await self._tickets.lock_open_batch(self._batch_size):
            target = ticket.expected_sla(now, self._warning_seconds, self._overdue_seconds)
            notifications.extend(
                OutboxNotification(
                    id=uuid4(),
                    ticket_id=ticket.id,
                    threshold=threshold,
                    direction=ticket.direction,
                    status=OutboxStatus.PENDING,
                    created_at=now,
                )
                for threshold in ticket.advance_sla(target)
            )
        created = await self._outbox.add_many_if_absent(notifications)
        await self._tm.commit()
        return created
