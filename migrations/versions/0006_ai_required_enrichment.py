"""Store account enrichment and AI-backed outreach sequences.

Revision ID: 0006_ai_required_enrichment
Revises: 0005_account_prospecting
Create Date: 2026-08-27
"""

from alembic import op
import sqlalchemy as sa

revision = "0006_ai_required_enrichment"
down_revision = "0005_account_prospecting"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    company_columns = {column["name"] for column in inspector.get_columns("companies")}
    draft_columns = {column["name"] for column in inspector.get_columns("outreach_drafts")}
    if "enrichment_data" not in company_columns:
        op.add_column("companies", sa.Column("enrichment_data", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
    if "sequence" not in draft_columns:
        op.add_column("outreach_drafts", sa.Column("sequence", sa.JSON(), nullable=False, server_default=sa.text("'[]'")))
    if "ai_suggestion_id" not in draft_columns:
        op.add_column("outreach_drafts", sa.Column("ai_suggestion_id", sa.String(length=36), sa.ForeignKey("ai_suggestions.id"), nullable=True))


def downgrade() -> None:
    pass
