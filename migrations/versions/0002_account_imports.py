"""Add account-import metadata and company profile storage.

Revision ID: 0002_account_imports
Revises: 0001_initial
Create Date: 2026-08-27
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_account_imports"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    import_columns = {column["name"] for column in inspector.get_columns("imports")}
    company_columns = {column["name"] for column in inspector.get_columns("companies")}
    import_indexes = {index["name"] for index in inspector.get_indexes("imports")}
    if "kind" not in import_columns:
        op.add_column("imports", sa.Column("kind", sa.String(length=16), nullable=False, server_default="leads"))
    if "ix_imports_kind" not in import_indexes:
        op.create_index("ix_imports_kind", "imports", ["kind"])
    if "profile_data" not in company_columns:
        op.add_column("companies", sa.Column("profile_data", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))


def downgrade() -> None:
    op.drop_column("companies", "profile_data")
    op.drop_index("ix_imports_kind", table_name="imports")
    op.drop_column("imports", "kind")
