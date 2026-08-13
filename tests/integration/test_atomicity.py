from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from answer_controller.application.dto import CustomerMessage, ProcessEventCommand
from answer_controller.application.interactors import ProcessEventInteractor
from answer_controller.application.ports import TransactionManager
from answer_controller.domain.entities import IncomingEvent, Ticket
from answer_controller.domain.enums import EventType
from tests.integration.fakes import InMemoryEventRepository, InMemoryTicketRepository


class TransactionalEventRepository(InMemoryEventRepository):
    def __init__(self) -> None:
        super().__init__()
        self.pending: dict[str, IncomingEvent] = {}

    async def add_if_absent(self, event: IncomingEvent) -> bool:
        if event.event_id in self.events or event.event_id in self.pending:
            return False
        self.pending[event.event_id] = event
        return True


class FailingTransactionalTicketRepository(InMemoryTicketRepository):
    def __init__(self) -> None:
        super().__init__()
        self.pending: dict[UUID, Ticket] = {}
        self.fail_next_add = True

    async def add(self, ticket: Ticket) -> None:
        if self.fail_next_add:
            self.fail_next_add = False
            raise RuntimeError("ticket creation failed")
        self.pending[ticket.id] = ticket


class InMemoryTransactionManager(TransactionManager):
    def __init__(
        self,
        events: TransactionalEventRepository,
        tickets: FailingTransactionalTicketRepository,
    ) -> None:
        self._events = events
        self._tickets = tickets

    async def commit(self) -> None:
        self._events.events.update(self._events.pending)
        self._tickets.tickets.update(self._tickets.pending)
        self._events.pending.clear()
        self._tickets.pending.clear()

    async def rollback(self) -> None:
        self._events.pending.clear()
        self._tickets.pending.clear()


async def test_event_can_be_retried_after_failure_inside_transaction() -> None:
    events = TransactionalEventRepository()
    tickets = FailingTransactionalTicketRepository()
    interactor = ProcessEventInteractor(
        events,
        tickets,
        InMemoryTransactionManager(events, tickets),
    )
    command = ProcessEventCommand(
        event_id=str(uuid4()),
        event_type=EventType.CUSTOMER_MESSAGE,
        occurred_at=datetime.now(UTC),
        payload=CustomerMessage(uuid4(), "customer", "chat", "support", "Help"),
    )

    with pytest.raises(RuntimeError, match="ticket creation failed"):
        await interactor.execute(command)

    assert events.events == {}
    assert tickets.tickets == {}

    result = await interactor.execute(command)

    assert result.duplicate is False
    assert len(events.events) == 1
    assert len(tickets.tickets) == 1
    assert next(iter(events.events.values())).ticket_id == next(iter(tickets.tickets))

    duplicate = await interactor.execute(command)
    assert duplicate.duplicate is True
    assert len(events.events) == 1
    assert len(tickets.tickets) == 1
