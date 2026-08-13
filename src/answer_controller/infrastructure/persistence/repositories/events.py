from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from answer_controller.application.ports import EventRepository
from answer_controller.domain.entities import IncomingEvent
from answer_controller.infrastructure.persistence.tables import incoming_events


class SqlAlchemyEventRepository(EventRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_if_absent(self, event: IncomingEvent) -> bool:
        statement = (
            insert(incoming_events)
            .values(
                event_id=event.event_id,
                event_type=event.event_type,
                occurred_at=event.occurred_at,
                payload=event.payload,
                ticket_id=event.ticket_id,
                processed_at=event.processed_at,
            )
            .on_conflict_do_nothing(index_elements=[incoming_events.c.event_id])
            .returning(incoming_events.c.event_id)
        )
        return (await self._session.execute(statement)).scalar_one_or_none() is not None

    async def get(self, event_id: str) -> IncomingEvent | None:
        statement = select(IncomingEvent).where(incoming_events.c.event_id == event_id)
        return (await self._session.execute(statement)).scalar_one_or_none()
