from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from answer_controller.domain.enums import EventType, OutboxStatus, SlaStatus
from answer_controller.domain.errors import InvalidResponseTimeError


@dataclass
class Ticket:
    id: UUID
    message_id: UUID
    client_id: str
    channel: str
    direction: str
    text: str
    created_at: datetime
    answered_at: datetime | None = None
    first_response_seconds: int | None = None
    sla_status: SlaStatus = SlaStatus.NORMAL

    @property
    def is_open(self) -> bool:
        return self.answered_at is None

    def close(self, answered_at: datetime) -> bool:
        if not self.is_open:
            return False
        response_seconds = int((answered_at - self.created_at).total_seconds())
        if response_seconds < 0:
            raise InvalidResponseTimeError
        self.answered_at = answered_at
        self.first_response_seconds = response_seconds
        return True

    def expected_sla(self, now: datetime, warning_seconds: int, overdue_seconds: int) -> SlaStatus:
        elapsed = int((now - self.created_at).total_seconds())
        if elapsed > overdue_seconds:
            return SlaStatus.OVERDUE
        if elapsed > warning_seconds:
            return SlaStatus.WARNING
        return SlaStatus.NORMAL

    def advance_sla(self, target: SlaStatus) -> list[SlaStatus]:
        transitions: list[SlaStatus] = []
        if self.sla_status is SlaStatus.NORMAL and target in {SlaStatus.WARNING, SlaStatus.OVERDUE}:
            transitions.append(SlaStatus.WARNING)
        if target is SlaStatus.OVERDUE and self.sla_status is not SlaStatus.OVERDUE:
            transitions.append(SlaStatus.OVERDUE)
        if transitions:
            self.sla_status = transitions[-1]
        return transitions


@dataclass
class IncomingEvent:
    event_id: str
    event_type: EventType
    occurred_at: datetime
    payload: dict[str, object]
    ticket_id: UUID
    processed_at: datetime

    @classmethod
    def create(
        cls,
        event_id: str,
        event_type: EventType,
        occurred_at: datetime,
        payload: dict[str, object],
        ticket_id: UUID,
    ) -> "IncomingEvent":
        return cls(event_id, event_type, occurred_at, payload, ticket_id, datetime.now(UTC))


@dataclass
class OutboxNotification:
    id: UUID
    ticket_id: UUID
    threshold: SlaStatus
    direction: str
    status: OutboxStatus
    created_at: datetime
    sent_at: datetime | None = None
    attempts: int = 0
    last_error: str | None = None

    def mark_processing(self) -> None:
        self.status = OutboxStatus.PROCESSING
        self.attempts += 1

    def mark_sent(self, sent_at: datetime) -> None:
        self.status = OutboxStatus.SENT
        self.sent_at = sent_at
        self.last_error = None

    def mark_failed(self, error: str) -> None:
        self.status = OutboxStatus.PENDING
        self.last_error = error[:1000]
