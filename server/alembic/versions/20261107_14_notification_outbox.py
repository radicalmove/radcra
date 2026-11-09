"""Add the opt-in notification pilot outbox."""

from alembic import op
import sqlalchemy as sa

revision = "20261107_14"
down_revision = "20260804_13"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "notification_outbox",
        sa.Column("event_id", sa.Uuid(), sa.ForeignKey("comment_status_events.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
    )


def downgrade():
    op.drop_table("notification_outbox")
