from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Table, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from answer_controller.infrastructure.persistence.tables.registry import metadata
from answer_controller.infrastructure.persistence.tables.tickets import tickets
from answer_controller.infrastructure.persistence.tables.types import outbox_status, sla_status

outbox_notifications = Table(
    "outbox_notifications",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("ticket_id", UUID(as_uuid=True), ForeignKey(tickets.c.id), nullable=False),
    Column("threshold", sla_status, nullable=False),
    Column("direction", String(128), nullable=False),
    Column("status", outbox_status, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("sent_at", DateTime(timezone=True)),
    Column("attempts", Integer, nullable=False, server_default="0"),
    Column("last_error", String(1000)),
    UniqueConstraint("ticket_id", "threshold", name="uq_outbox_ticket_threshold"),
    Index("ix_outbox_status_created", "status", "created_at"),
)
