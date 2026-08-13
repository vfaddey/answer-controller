from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from answer_controller.domain.enums import SlaStatus


@dataclass(frozen=True, slots=True)
class ProcessEventResult:
    event_id: str
    ticket_id: UUID
    duplicate: bool


@dataclass(frozen=True, slots=True)
class TicketView:
    id: UUID
    message_id: UUID
    client_id: str
    channel: str
    direction: str
    text: str
    created_at: datetime
    waiting_seconds: int
    sla_status: SlaStatus


@dataclass(frozen=True, slots=True)
class MetricsView:
    created: int
    answered: int
    overdue: int
    median_first_response_seconds: float | None
