from datetime import UTC, datetime, timedelta
from uuid import uuid4

from answer_controller.application.interactors import CheckSlaInteractor
from answer_controller.domain.entities import Ticket
from answer_controller.domain.enums import SlaStatus
from tests.integration.fakes import (
    InMemoryOutboxRepository,
    InMemoryTicketRepository,
    NoopTransactionManager,
)


async def test_sla_check_is_idempotent_and_advances_to_overdue() -> None:
    now = datetime.now(UTC)
    ticket = Ticket(
        uuid4(),
        uuid4(),
        "customer",
        "chat",
        "sales",
        "Help",
        now - timedelta(seconds=70),
    )
    tickets = InMemoryTicketRepository()
    tickets.tickets[ticket.id] = ticket
    outbox = InMemoryOutboxRepository()
    interactor = CheckSlaInteractor(
        tickets,
        outbox,
        NoopTransactionManager(),
        warning_seconds=60,
        overdue_seconds=180,
        batch_size=100,
    )

    assert await interactor.execute() == 1
    assert await interactor.execute() == 0

    ticket.created_at = now - timedelta(seconds=200)
    assert await interactor.execute() == 1
    assert await interactor.execute() == 0
    assert {notification.threshold for notification in outbox.notifications.values()} == {
        SlaStatus.WARNING,
        SlaStatus.OVERDUE,
    }
