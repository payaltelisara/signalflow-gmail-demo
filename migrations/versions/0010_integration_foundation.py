"""Add provider-neutral integration, mapping, and webhook records.

Revision ID: 0010_integration_foundation
Revises: 0009_campaign_audience
"""

from alembic import op
import sqlalchemy as sa


revision = "0010_integration_foundation"
down_revision = "0009_campaign_audience"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("integration_connections"):
        op.create_table(
            "integration_connections",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
            sa.Column("provider", sa.String(length=64), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="not_configured"),
            sa.Column("configuration", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("encrypted_credentials", sa.Text()),
            sa.Column("capabilities", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
            sa.Column("sync_status", sa.String(length=32), nullable=False, server_default="idle"),
            sa.Column("retry_state", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("last_test_at", sa.DateTime(timezone=True)),
            sa.Column("last_sync_at", sa.DateTime(timezone=True)),
            sa.Column("last_error", sa.Text()),
            sa.Column("created_by", sa.String(length=36), sa.ForeignKey("users.id")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("workspace_id", "provider", name="uq_integration_workspace_provider"),
        )
        for column in ("workspace_id", "provider", "status", "sync_status"):
            op.create_index(f"ix_integration_connections_{column}", "integration_connections", [column])
    if not inspector.has_table("external_record_mappings"):
        op.create_table(
            "external_record_mappings",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
            sa.Column("integration_id", sa.String(length=36), sa.ForeignKey("integration_connections.id", ondelete="SET NULL")),
            sa.Column("provider", sa.String(length=64), nullable=False),
            sa.Column("resource_type", sa.String(length=64), nullable=False),
            sa.Column("resource_id", sa.String(length=128), nullable=False),
            sa.Column("external_id", sa.String(length=320), nullable=False),
            sa.Column("external_url", sa.String(length=1024)),
            sa.Column("metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("workspace_id", "provider", "resource_type", "external_id", name="uq_external_mapping_workspace_provider_record"),
        )
        for column in ("workspace_id", "integration_id", "provider", "resource_type", "resource_id", "external_id"):
            op.create_index(f"ix_external_record_mappings_{column}", "external_record_mappings", [column])
    if not inspector.has_table("webhook_events"):
        op.create_table(
            "webhook_events",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id", ondelete="CASCADE")),
            sa.Column("integration_id", sa.String(length=36), sa.ForeignKey("integration_connections.id", ondelete="SET NULL")),
            sa.Column("provider", sa.String(length=64), nullable=False),
            sa.Column("external_event_id", sa.String(length=320)),
            sa.Column("event_type", sa.String(length=128)),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="received"),
            sa.Column("payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("error_message", sa.Text()),
            sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("processed_at", sa.DateTime(timezone=True)),
            sa.UniqueConstraint("provider", "external_event_id", name="uq_webhook_provider_event"),
        )
        for column in ("workspace_id", "integration_id", "provider", "status"):
            op.create_index(f"ix_webhook_events_{column}", "webhook_events", [column])


def downgrade() -> None:
    pass
