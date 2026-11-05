"""Add campaigns, observable workflow jobs, and Gmail mailbox connections.

Revision ID: 0007_campaign_jobs_gmail
Revises: 0006_ai_required_enrichment
Create Date: 2026-08-28
"""

from alembic import op
import sqlalchemy as sa


revision = "0007_campaign_jobs_gmail"
down_revision = "0006_ai_required_enrichment"
branch_labels = None
depends_on = None


def uuid_column(name: str = "id"):
    return sa.Column(name, sa.String(length=36), primary_key=name == "id", nullable=False)


def upgrade() -> None:
    # The original initial migration creates the current SQLAlchemy metadata for
    # local portfolio installs. Avoid re-creating these tables when upgrading
    # such a database through Alembic's historical revisions.
    if sa.inspect(op.get_bind()).has_table("workflow_jobs"):
        return
    op.create_table(
        "workflow_jobs",
        uuid_column(), sa.Column("workspace_id", sa.String(36), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id")), sa.Column("job_type", sa.String(64), nullable=False),
        sa.Column("name", sa.String(160), nullable=False), sa.Column("status", sa.String(32), nullable=False, server_default="queued"),
        sa.Column("phase", sa.String(96), nullable=False, server_default="queued"), sa.Column("resource_type", sa.String(64)),
        sa.Column("resource_id", sa.String(128)), sa.Column("counters", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("details", sa.JSON(), nullable=False, server_default=sa.text("'{}'")), sa.Column("error_message", sa.Text()),
        sa.Column("idempotency_key", sa.String(128), nullable=False), sa.Column("attempt", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("cancellation_requested", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("queued_at", sa.DateTime(timezone=True), nullable=False), sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("workspace_id", "idempotency_key", name="uq_workflow_job_idempotency"),
    )
    op.create_index("ix_workflow_jobs_workspace_id", "workflow_jobs", ["workspace_id"])
    op.create_index("ix_workflow_jobs_job_type", "workflow_jobs", ["job_type"])
    op.create_index("ix_workflow_jobs_status", "workflow_jobs", ["status"])
    op.create_index("ix_workflow_jobs_resource_id", "workflow_jobs", ["resource_id"])
    op.create_table("workflow_job_logs", uuid_column(), sa.Column("job_id", sa.String(36), sa.ForeignKey("workflow_jobs.id", ondelete="CASCADE"), nullable=False), sa.Column("level", sa.String(16), nullable=False, server_default="info"), sa.Column("message", sa.String(500), nullable=False), sa.Column("context", sa.JSON(), nullable=False, server_default=sa.text("'{}'")), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_workflow_job_logs_job_id", "workflow_job_logs", ["job_id"])
    op.create_table("mailbox_connections", uuid_column(), sa.Column("workspace_id", sa.String(36), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False), sa.Column("connected_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False), sa.Column("provider", sa.String(32), nullable=False, server_default="gmail"), sa.Column("email", sa.String(320), nullable=False), sa.Column("encrypted_refresh_token", sa.Text(), nullable=False), sa.Column("scopes", sa.JSON(), nullable=False, server_default=sa.text("'[]'")), sa.Column("status", sa.String(32), nullable=False, server_default="connected"), sa.Column("last_history_id", sa.String(128)), sa.Column("last_sync_at", sa.DateTime(timezone=True)), sa.Column("last_error", sa.Text()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("workspace_id", "email", name="uq_mailbox_workspace_email"))
    op.create_index("ix_mailbox_connections_workspace_id", "mailbox_connections", ["workspace_id"])
    op.create_index("ix_mailbox_connections_email", "mailbox_connections", ["email"])
    op.create_index("ix_mailbox_connections_status", "mailbox_connections", ["status"])
    op.create_table("gmail_oauth_states", uuid_column(), sa.Column("state", sa.String(128), nullable=False, unique=True), sa.Column("workspace_id", sa.String(36), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False), sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("code_verifier", sa.String(160), nullable=False), sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_gmail_oauth_states_state", "gmail_oauth_states", ["state"])
    op.create_index("ix_gmail_oauth_states_workspace_id", "gmail_oauth_states", ["workspace_id"])
    op.create_index("ix_gmail_oauth_states_user_id", "gmail_oauth_states", ["user_id"])
    op.create_index("ix_gmail_oauth_states_expires_at", "gmail_oauth_states", ["expires_at"])
    op.create_table("campaigns", uuid_column(), sa.Column("workspace_id", sa.String(36), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False), sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False), sa.Column("mailbox_id", sa.String(36), sa.ForeignKey("mailbox_connections.id")), sa.Column("name", sa.String(160), nullable=False), sa.Column("status", sa.String(32), nullable=False, server_default="draft"), sa.Column("audience_filter", sa.JSON(), nullable=False, server_default=sa.text("'{}'")), sa.Column("timezone", sa.String(64), nullable=False, server_default="UTC"), sa.Column("business_hours", sa.JSON(), nullable=False, server_default=sa.text("'{\"start\": 9, \"end\": 17, \"weekdays\": [0, 1, 2, 3, 4]}'")), sa.Column("daily_limit", sa.Integer(), nullable=False, server_default="20"), sa.Column("per_domain_limit", sa.Integer(), nullable=False, server_default="1"), sa.Column("test_sent_at", sa.DateTime(timezone=True)), sa.Column("approved_by", sa.String(36), sa.ForeignKey("users.id")), sa.Column("approved_at", sa.DateTime(timezone=True)), sa.Column("activated_at", sa.DateTime(timezone=True)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    for column in ("workspace_id", "created_by", "mailbox_id", "status"):
        op.create_index(f"ix_campaigns_{column}", "campaigns", [column])
    op.create_table("campaign_steps", uuid_column(), sa.Column("campaign_id", sa.String(36), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False), sa.Column("position", sa.Integer(), nullable=False), sa.Column("delay_hours", sa.Integer(), nullable=False, server_default="0"), sa.Column("subject", sa.String(320), nullable=False), sa.Column("body", sa.Text(), nullable=False), sa.Column("facts_used", sa.JSON(), nullable=False, server_default=sa.text("'[]'")), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("campaign_id", "position", name="uq_campaign_step_position"))
    op.create_index("ix_campaign_steps_campaign_id", "campaign_steps", ["campaign_id"])
    op.create_table("campaign_enrollments", uuid_column(), sa.Column("campaign_id", sa.String(36), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False), sa.Column("lead_id", sa.String(36), sa.ForeignKey("leads.id", ondelete="CASCADE"), nullable=False), sa.Column("status", sa.String(32), nullable=False, server_default="queued"), sa.Column("next_step", sa.Integer(), nullable=False, server_default="1"), sa.Column("next_send_at", sa.DateTime(timezone=True)), sa.Column("stopped_reason", sa.String(96)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("campaign_id", "lead_id", name="uq_campaign_enrollment_lead"))
    for column in ("campaign_id", "lead_id", "status", "next_send_at"):
        op.create_index(f"ix_campaign_enrollments_{column}", "campaign_enrollments", [column])
    op.create_table("scheduled_messages", uuid_column(), sa.Column("workspace_id", sa.String(36), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False), sa.Column("campaign_id", sa.String(36), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False), sa.Column("enrollment_id", sa.String(36), sa.ForeignKey("campaign_enrollments.id", ondelete="CASCADE"), nullable=False), sa.Column("step_position", sa.Integer(), nullable=False), sa.Column("status", sa.String(32), nullable=False, server_default="scheduled"), sa.Column("send_at", sa.DateTime(timezone=True), nullable=False), sa.Column("idempotency_key", sa.String(160), nullable=False, unique=True), sa.Column("error_message", sa.Text()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    for column in ("workspace_id", "campaign_id", "enrollment_id", "status", "send_at", "idempotency_key"):
        op.create_index(f"ix_scheduled_messages_{column}", "scheduled_messages", [column])
    op.create_table("messages", uuid_column(), sa.Column("workspace_id", sa.String(36), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False), sa.Column("mailbox_id", sa.String(36), sa.ForeignKey("mailbox_connections.id")), sa.Column("campaign_id", sa.String(36), sa.ForeignKey("campaigns.id")), sa.Column("enrollment_id", sa.String(36), sa.ForeignKey("campaign_enrollments.id")), sa.Column("lead_id", sa.String(36), sa.ForeignKey("leads.id")), sa.Column("direction", sa.String(16), nullable=False), sa.Column("gmail_message_id", sa.String(160)), sa.Column("gmail_thread_id", sa.String(160)), sa.Column("to_email", sa.String(320)), sa.Column("subject", sa.String(320), nullable=False), sa.Column("body", sa.Text(), nullable=False), sa.Column("delivery_status", sa.String(32), nullable=False, server_default="queued"), sa.Column("reply_classification", sa.String(48)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("workspace_id", "gmail_message_id", name="uq_message_workspace_gmail_message"))
    for column in ("workspace_id", "mailbox_id", "campaign_id", "enrollment_id", "lead_id", "direction", "gmail_thread_id", "delivery_status"):
        op.create_index(f"ix_messages_{column}", "messages", [column])
    op.create_table("suppressions", uuid_column(), sa.Column("workspace_id", sa.String(36), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False), sa.Column("normalized_email", sa.String(320), nullable=False), sa.Column("reason", sa.String(96), nullable=False), sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id")), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("workspace_id", "normalized_email", name="uq_suppression_workspace_email"))
    op.create_index("ix_suppressions_workspace_id", "suppressions", ["workspace_id"])
    op.create_index("ix_suppressions_normalized_email", "suppressions", ["normalized_email"])
    op.create_table("prompt_versions", uuid_column(), sa.Column("workspace_id", sa.String(36), sa.ForeignKey("workspaces.id", ondelete="CASCADE")), sa.Column("name", sa.String(96), nullable=False), sa.Column("version", sa.String(64), nullable=False), sa.Column("template", sa.Text(), nullable=False), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("workspace_id", "name", "version", name="uq_prompt_version"))
    op.create_index("ix_prompt_versions_workspace_id", "prompt_versions", ["workspace_id"])
    op.create_index("ix_prompt_versions_name", "prompt_versions", ["name"])


def downgrade() -> None:
    # Production migrations are intentionally forward-only for this local portfolio project.
    pass
