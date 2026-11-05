"""Add durable lead verification outcomes.

Revision ID: 0011_lead_verification
Revises: 0010_integration_foundation
"""

from alembic import op
import sqlalchemy as sa


revision = "0011_lead_verification"
down_revision = "0010_integration_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("leads")}
    if "verification_status" not in columns:
        op.add_column("leads", sa.Column("verification_status", sa.String(length=32), nullable=False, server_default="unverified"))
        op.create_index("ix_leads_verification_status", "leads", ["verification_status"])
    if "verification_provider" not in columns:
        op.add_column("leads", sa.Column("verification_provider", sa.String(length=64)))
    if "verification_detail" not in columns:
        op.add_column("leads", sa.Column("verification_detail", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
    if "verified_at" not in columns:
        op.add_column("leads", sa.Column("verified_at", sa.DateTime(timezone=True)))


def downgrade() -> None:
    pass
