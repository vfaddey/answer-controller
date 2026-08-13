from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from answer_controller.domain.enums import EventType


@dataclass(frozen=True, slots=True)
class CustomerMessage:
    message_id: UUID
    client_id: str
    channel: str
    direction: str
    text: str


@dataclass(frozen=True, slots=True)
class EmployeeResponse:
    reply_to_message_id: UUID
    employee_id: str
    text: str


@dataclass(frozen=True, slots=True)
class ProcessEventCommand:
    event_id: str
    event_type: EventType
    occurred_at: datetime
    payload: CustomerMessage | EmployeeResponse


@dataclass(frozen=True, slots=True)
class MetricsQuery:
    date_from: datetime
    date_to: datetime
