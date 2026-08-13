"""add ticket message id

Revision ID: 3b4d9e7f2a11
Revises: e9c10901aa00
Create Date: 2026-08-13 12:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "3b4d9e7f2a11"
down_revision: str | Sequence[str] | None = "e9c10901aa00"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("tickets", sa.Column("message_id", sa.UUID(), nullable=True))
    op.execute("UPDATE tickets SET message_id = id WHERE message_id IS NULL")
    op.alter_column("tickets", "message_id", nullable=False)
    op.create_unique_constraint("uq_tickets_message_id", "tickets", ["message_id"])


def downgrade() -> None:
    op.drop_constraint("uq_tickets_message_id", "tickets", type_="unique")
    op.drop_column("tickets", "message_id")
