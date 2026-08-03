"""Add soft-delete state for user accounts.

Revision ID: 20260804_12
Revises: 20260715_11
"""

import sqlalchemy as sa
from alembic import op


revision = "20260804_12"
down_revision = "20260715_11"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_users_deleted_at", "users", ["deleted_at"])


def downgrade() -> None:
    op.drop_index("ix_users_deleted_at", table_name="users")
    op.drop_column("users", "deleted_at")
