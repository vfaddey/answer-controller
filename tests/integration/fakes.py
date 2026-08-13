import asyncio
from datetime import datetime
from statistics import median
from uuid import UUID

from answer_controller.application.dto import MetricsQuery, MetricsView, TicketView
from answer_controller.application.ports import (
    EventRepository,
    HealthRepository,
    OutboxRepository,
    TicketRepository,
    TransactionManager,
)
from answer_controller.domain.entities import IncomingEvent, OutboxNotification, Ticket


class InMemoryEventRepository(EventRepository):
    def __init__(self) -> None:
        self.events: dict[str, IncomingEvent] = {}
        self._lock = asyncio.Lock()

    async def add_if_absent(self, event: IncomingEvent) -> bool:
        async with self._lock:
            if event.event_id in self.events:
                return False
            self.events[event.event_id] = event
            return True

    async def get(self, event_id: str) -> IncomingEvent | None:
        return self.events.get(event_id)


class InMemoryTicketRepository(TicketRepository):
    def __init__(self, warning_seconds: int = 60, overdue_seconds: int = 180) -> None:
        self.tickets: dict[UUID, Ticket] = {}
        self._warning_seconds = warning_seconds
        self._overdue_seconds = overdue_seconds

    async def add(self, ticket: Ticket) -> None:
        self.tickets[ticket.id] = ticket

    async def get_for_update_by_message_id(self, message_id: UUID) -> Ticket | None:
        return next(
            (ticket for ticket in self.tickets.values() if ticket.message_id == message_id),
            None,
        )

    async def list_open(self, direction: str | None, now: datetime) -> list[TicketView]:
        open_tickets = (
            ticket
            for ticket in self.tickets.values()
            if ticket.is_open and (direction is None or ticket.direction == direction)
        )
        return [
            TicketView(
                id=ticket.id,
                message_id=ticket.message_id,
                client_id=ticket.client_id,
                channel=ticket.channel,
                direction=ticket.direction,
                text=ticket.text,
                created_at=ticket.created_at,
                waiting_seconds=max(0, int((now - ticket.created_at).total_seconds())),
                sla_status=ticket.expected_sla(
                    now,
                    self._warning_seconds,
                    self._overdue_seconds,
                ),
            )
            for ticket in sorted(open_tickets, key=lambda item: item.created_at)
        ]

    async def lock_open_batch(self, limit: int) -> list[Ticket]:
        return sorted(
            (ticket for ticket in self.tickets.values() if ticket.is_open),
            key=lambda item: item.created_at,
        )[:limit]

    async def metrics(self, query: MetricsQuery, now: datetime) -> MetricsView:
        cohort = [
            ticket
            for ticket in self.tickets.values()
            if query.date_from <= ticket.created_at < query.date_to
        ]
        response_times = [
            ticket.first_response_seconds
            for ticket in cohort
            if ticket.first_response_seconds is not None
        ]
        overdue = sum(
            (
                ticket.first_response_seconds is not None
                and ticket.first_response_seconds > self._overdue_seconds
            )
            or (
                ticket.is_open and (now - ticket.created_at).total_seconds() > self._overdue_seconds
            )
            for ticket in cohort
        )
        return MetricsView(
            created=len(cohort),
            answered=sum(not ticket.is_open for ticket in cohort),
            overdue=overdue,
            median_first_response_seconds=(
                float(median(response_times)) if response_times else None
            ),
        )


class InMemoryOutboxRepository(OutboxRepository):
    def __init__(self) -> None:
        self.notifications: dict[tuple[UUID, object], OutboxNotification] = {}

    async def add_many_if_absent(self, notifications: list[OutboxNotification]) -> int:
        created = 0
        for notification in notifications:
            key = notification.ticket_id, notification.threshold
            if key not in self.notifications:
                self.notifications[key] = notification
                created += 1
        return created

    async def claim_batch(self, limit: int) -> list[OutboxNotification]:
        return list(self.notifications.values())[:limit]


class NoopTransactionManager(TransactionManager):
    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


class ReadyHealthRepository(HealthRepository):
    async def is_ready(self) -> bool:
        return True
