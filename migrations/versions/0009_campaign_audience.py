"""Associate campaign uploads with a reviewed campaign audience.

Revision ID: 0009_campaign_audience
Revises: 0008_rfc_message_threading
Create Date: 2026-08-28
"""

from alembic import op
import sqlalchemy as sa


revision = "0009_campaign_audience"
down_revision = "0008_rfc_message_threading"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    import_columns = {column["name"] for column in inspector.get_columns("imports")}
    if "campaign_id" in import_columns and inspector.has_table("campaign_audience_members"):
        return
    op.add_column("imports", sa.Column("campaign_id", sa.String(length=36), nullable=True))
    op.create_foreign_key("fk_imports_campaign_id", "imports", "campaigns", ["campaign_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_imports_campaign_id", "imports", ["campaign_id"])
    op.create_table(
        "campaign_audience_members",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("campaign_id", sa.String(length=36), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
        sa.Column("lead_id", sa.String(length=36), sa.ForeignKey("leads.id", ondelete="CASCADE"), nullable=True),
        sa.Column("company_id", sa.String(length=36), sa.ForeignKey("companies.id", ondelete="SET NULL"), nullable=True),
        sa.Column("import_id", sa.String(length=36), sa.ForeignKey("imports.id", ondelete="SET NULL"), nullable=True),
        sa.Column("selected", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("readiness", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("warning", sa.String(length=256), nullable=True),
        sa.Column("exclusion_reason", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("campaign_id", "lead_id", name="uq_campaign_audience_lead"),
    )
    op.create_index("ix_campaign_audience_members_campaign_id", "campaign_audience_members", ["campaign_id"])
    op.create_index("ix_campaign_audience_members_lead_id", "campaign_audience_members", ["lead_id"])


def downgrade() -> None:
    pass
