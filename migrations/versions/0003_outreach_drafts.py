"""Add human-reviewed outreach drafts.

Revision ID: 0003_outreach_drafts
Revises: 0002_account_imports
Create Date: 2026-08-27
"""

from alembic import op
import sqlalchemy as sa

revision = "0003_outreach_drafts"
down_revision = "0002_account_imports"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "outreach_drafts" not in inspector.get_table_names():
        op.create_table(
            "outreach_drafts",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
            sa.Column("lead_id", sa.String(length=36), sa.ForeignKey("leads.id", ondelete="CASCADE"), nullable=False),
            sa.Column("subject", sa.String(length=320), nullable=False),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("rationale", sa.JSON(), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("reviewed_by", sa.String(length=36), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("lead_id", "version", name="uq_outreach_draft_lead_version"),
        )
        op.create_index("ix_outreach_drafts_workspace_id", "outreach_drafts", ["workspace_id"])
        op.create_index("ix_outreach_drafts_lead_id", "outreach_drafts", ["lead_id"])
        op.create_index("ix_outreach_drafts_status", "outreach_drafts", ["status"])


def downgrade() -> None:
    op.drop_table("outreach_drafts")
