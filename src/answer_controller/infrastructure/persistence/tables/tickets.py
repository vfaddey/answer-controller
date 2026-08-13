from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Index,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID

from answer_controller.infrastructure.persistence.tables.registry import metadata
from answer_controller.infrastructure.persistence.tables.types import sla_status

tickets = Table(
    "tickets",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("message_id", UUID(as_uuid=True), nullable=False),
    Column("client_id", String(128), nullable=False),
    Column("channel", String(64), nullable=False),
    Column("direction", String(128), nullable=False),
    Column("text", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("answered_at", DateTime(timezone=True)),
    Column("first_response_seconds", Integer),
    Column("sla_status", sla_status, nullable=False),
    CheckConstraint(
        "first_response_seconds IS NULL OR first_response_seconds >= 0",
        name="first_response_non_negative",
    ),
    UniqueConstraint("message_id", name="uq_tickets_message_id"),
    Index(
        "ix_tickets_open_direction_created",
        "direction",
        "created_at",
        postgresql_where=text("answered_at IS NULL"),
    ),
    Index("ix_tickets_created_at", "created_at"),
    Index("ix_tickets_answered_at", "answered_at"),
)
