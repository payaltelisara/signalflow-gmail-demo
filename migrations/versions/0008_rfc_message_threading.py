"""Preserve RFC message identifiers for threaded Gmail follow-ups.

Revision ID: 0008_rfc_message_threading
Revises: 0007_campaign_jobs_gmail
Create Date: 2026-08-28
"""

from alembic import op
import sqlalchemy as sa


revision = "0008_rfc_message_threading"
down_revision = "0007_campaign_jobs_gmail"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("messages")}
    if "rfc_message_id" in columns:
        return
    op.add_column("messages", sa.Column("rfc_message_id", sa.String(length=320), nullable=True))
    op.create_index("ix_messages_rfc_message_id", "messages", ["rfc_message_id"])


def downgrade() -> None:
    pass
