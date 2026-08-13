from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from answer_controller.application.dto import (
    CustomerMessage,
    EmployeeResponse,
    MetricsQuery,
    ProcessEventCommand,
)
from answer_controller.domain.enums import EventType


class CustomerMessagePayload(BaseModel):
    message_id: UUID
    client_id: Annotated[str, Field(min_length=1, max_length=128)]
    channel: Annotated[str, Field(min_length=1, max_length=64)]
    direction: Annotated[str, Field(min_length=1, max_length=128)]
    text: Annotated[str, Field(min_length=1, max_length=10000)]


class EmployeeResponsePayload(BaseModel):
    reply_to_message_id: UUID
    employee_id: Annotated[str, Field(min_length=1, max_length=128)]
    text: Annotated[str, Field(min_length=1, max_length=10000)]


class EventEnvelope(BaseModel):
    event_id: UUID
    occurred_at: datetime

    @field_validator("occurred_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            msg = "occurred_at must include a timezone"
            raise ValueError(msg)
        return value


class CustomerMessageEvent(EventEnvelope):
    event_type: Literal[EventType.CUSTOMER_MESSAGE]
    payload: CustomerMessagePayload

    def to_command(self) -> ProcessEventCommand:
        return ProcessEventCommand(
            event_id=str(self.event_id),
            event_type=self.event_type,
            occurred_at=self.occurred_at,
            payload=CustomerMessage(**self.payload.model_dump()),
        )


class EmployeeResponseEvent(EventEnvelope):
    event_type: Literal[EventType.EMPLOYEE_RESPONSE]
    payload: EmployeeResponsePayload

    def to_command(self) -> ProcessEventCommand:
        return ProcessEventCommand(
            event_id=str(self.event_id),
            event_type=self.event_type,
            occurred_at=self.occurred_at,
            payload=EmployeeResponse(**self.payload.model_dump()),
        )


class MetricsParameters(BaseModel):
    date_from: datetime | None = None
    date_to: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("date_from", "date_to")
    @classmethod
    def require_period_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            msg = "metric period dates must include a timezone"
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def resolve_period(self) -> "MetricsParameters":
        if self.date_from is None:
            self.date_from = self.date_to - timedelta(days=1)
        if self.date_from >= self.date_to:
            msg = "date_from must precede date_to"
            raise ValueError(msg)
        return self

    def to_query(self) -> MetricsQuery:
        if self.date_from is None:
            raise RuntimeError
        return MetricsQuery(self.date_from, self.date_to)
