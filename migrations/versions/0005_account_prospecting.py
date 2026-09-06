"""Add account-level qualification and routing.

Revision ID: 0005_account_prospecting
Revises: 0004_audit_resource_identifier
Create Date: 2026-08-27
"""

from alembic import op
import sqlalchemy as sa

revision = "0005_account_prospecting"
down_revision = "0004_audit_resource_identifier"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("companies")}
    if "score" not in columns:
        op.add_column("companies", sa.Column("score", sa.Integer(), nullable=False, server_default="0"))
    if "qualification" not in columns:
        op.add_column("companies", sa.Column("qualification", sa.String(length=32), nullable=False, server_default="unqualified"))
    if "next_action" not in columns:
        op.add_column("companies", sa.Column("next_action", sa.String(length=64), nullable=False, server_default="research_required"))
    if "owner_id" not in columns:
        op.add_column("companies", sa.Column("owner_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=True))


def downgrade() -> None:
    pass
