from sqlalchemy import JSON, Column, DateTime, ForeignKey, Index, String, Table
from sqlalchemy.dialects.postgresql import UUID

from answer_controller.infrastructure.persistence.tables.registry import metadata
from answer_controller.infrastructure.persistence.tables.tickets import tickets
from answer_controller.infrastructure.persistence.tables.types import event_type

incoming_events = Table(
    "incoming_events",
    metadata,
    Column("event_id", String(128), primary_key=True),
    Column("event_type", event_type, nullable=False),
    Column("occurred_at", DateTime(timezone=True), nullable=False),
    Column("payload", JSON, nullable=False),
    Column(
        "ticket_id",
        UUID(as_uuid=True),
        ForeignKey(tickets.c.id, deferrable=True, initially="DEFERRED"),
        nullable=False,
    ),
    Column("processed_at", DateTime(timezone=True), nullable=False),
    Index("ix_incoming_events_ticket_id", "ticket_id"),
)
