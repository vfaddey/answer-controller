from datetime import UTC, datetime, timedelta
from uuid import uuid4

from answer_controller.domain.entities import Ticket
from answer_controller.domain.enums import SlaStatus


def ticket(created_at: datetime) -> Ticket:
    return Ticket(
        id=uuid4(),
        message_id=uuid4(),
        client_id="customer-1",
        channel="chat",
        direction="sales",
        text="Help",
        created_at=created_at,
    )


def test_ticket_sla_and_first_response_rules() -> None:
    now = datetime.now(UTC)
    open_ticket = ticket(now - timedelta(seconds=60))
    assert open_ticket.expected_sla(now, 60, 180) is SlaStatus.NORMAL
    open_ticket.created_at = now - timedelta(seconds=61)
    assert open_ticket.expected_sla(now, 60, 180) is SlaStatus.WARNING
    open_ticket.created_at = now - timedelta(seconds=181)
    assert open_ticket.expected_sla(now, 60, 180) is SlaStatus.OVERDUE

    answered_ticket = ticket(now)
    assert answered_ticket.close(now + timedelta(seconds=42)) is True
    assert answered_ticket.close(now + timedelta(seconds=90)) is False
    assert answered_ticket.first_response_seconds == 42
