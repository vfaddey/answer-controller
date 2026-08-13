from datetime import datetime
from uuid import UUID

from sqlalchemy import Integer, and_, case, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from answer_controller.application.dto import MetricsQuery, MetricsView, TicketView
from answer_controller.application.ports import TicketRepository
from answer_controller.domain.entities import Ticket
from answer_controller.domain.enums import SlaStatus
from answer_controller.infrastructure.persistence.tables import tickets


class SqlAlchemyTicketRepository(TicketRepository):
    def __init__(
        self,
        session: AsyncSession,
        warning_seconds: int,
        overdue_seconds: int,
    ) -> None:
        self._session = session
        self._warning_seconds = warning_seconds
        self._overdue_seconds = overdue_seconds

    async def add(self, ticket: Ticket) -> None:
        self._session.add(ticket)

    async def get_for_update_by_message_id(self, message_id: UUID) -> Ticket | None:
        statement = select(Ticket).where(tickets.c.message_id == message_id).with_for_update()
        return (await self._session.execute(statement)).scalar_one_or_none()

    async def list_open(self, direction: str | None, now: datetime) -> list[TicketView]:
        waiting = cast(
            func.greatest(0, func.extract("epoch", now - tickets.c.created_at)),
            Integer,
        )
        status = case(
            (waiting > self._overdue_seconds, SlaStatus.OVERDUE.value),
            (waiting > self._warning_seconds, SlaStatus.WARNING.value),
            else_=SlaStatus.NORMAL.value,
        )
        statement = select(
            tickets.c.id,
            tickets.c.message_id,
            tickets.c.client_id,
            tickets.c.channel,
            tickets.c.direction,
            tickets.c.text,
            tickets.c.created_at,
            waiting.label("waiting_seconds"),
            status.label("sla_status"),
        ).where(tickets.c.answered_at.is_(None))
        if direction:
            statement = statement.where(tickets.c.direction == direction)
        rows = (await self._session.execute(statement.order_by(tickets.c.created_at))).mappings()
        return [
            TicketView(
                id=row.id,
                message_id=row.message_id,
                client_id=row.client_id,
                channel=row.channel,
                direction=row.direction,
                text=row.text,
                created_at=row.created_at,
                waiting_seconds=row.waiting_seconds,
                sla_status=SlaStatus(row.sla_status),
            )
            for row in rows
        ]

    async def lock_open_batch(self, limit: int) -> list[Ticket]:
        statement = (
            select(Ticket)
            .where(tickets.c.answered_at.is_(None))
            .order_by(tickets.c.created_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return list((await self._session.execute(statement)).scalars())

    async def metrics(self, query: MetricsQuery, now: datetime) -> MetricsView:
        cohort = and_(tickets.c.created_at >= query.date_from, tickets.c.created_at < query.date_to)
        open_waiting = func.extract("epoch", now - tickets.c.created_at)
        overdue = or_(
            tickets.c.first_response_seconds > self._overdue_seconds,
            and_(tickets.c.answered_at.is_(None), open_waiting > self._overdue_seconds),
        )
        statement = select(
            func.count().label("created"),
            func.count().filter(tickets.c.answered_at.is_not(None)).label("answered"),
            func.count().filter(overdue).label("overdue"),
            func.percentile_cont(0.5)
            .within_group(tickets.c.first_response_seconds)
            .filter(tickets.c.first_response_seconds.is_not(None))
            .label("median"),
        ).where(cohort)
        row = (await self._session.execute(statement)).one()
        return MetricsView(
            created=row.created,
            answered=row.answered,
            overdue=row.overdue,
            median_first_response_seconds=float(row.median) if row.median is not None else None,
        )
