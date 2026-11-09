"""Persist admin-first reviewer requests with safe legacy defaults."""
from alembic import op
import sqlalchemy as sa

revision = "20261110_17"
down_revision = "20261110_16"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("reviewer_email_challenges", sa.Column("admin_first", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("reviewer_email_challenges", sa.Column("requested_role", sa.String(20), nullable=False, server_default="beta_tester"))


def downgrade():
    op.drop_column("reviewer_email_challenges", "requested_role")
    op.drop_column("reviewer_email_challenges", "admin_first")
