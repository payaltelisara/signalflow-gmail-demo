"""Allow path-like resource identifiers in the audit log.

Revision ID: 0004_audit_resource_identifier
Revises: 0003_outreach_drafts
Create Date: 2026-08-27
"""

from alembic import op
import sqlalchemy as sa

revision = "0004_audit_resource_identifier"
down_revision = "0003_outreach_drafts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    column = next(item for item in inspector.get_columns("audit_logs") if item["name"] == "resource_id")
    if getattr(column["type"], "length", 0) < 512:
        op.alter_column("audit_logs", "resource_id", existing_type=sa.String(length=36), type_=sa.String(length=512))


def downgrade() -> None:
    # Narrowing could truncate historical export keys, so this revision is intentionally irreversible.
    pass
