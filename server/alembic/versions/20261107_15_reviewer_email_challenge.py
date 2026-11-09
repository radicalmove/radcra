"""Add single-use email challenges for course access."""

from alembic import op
import sqlalchemy as sa

revision = "20261107_15"
down_revision = "20261107_14"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "reviewer_email_challenges",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("course_id", sa.Uuid(), sa.ForeignKey("courses.id"), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("proof_hash", sa.String(64), unique=True, nullable=False),
        sa.Column("browser_hash", sa.String(64), unique=True, nullable=False),
        sa.Column("proof_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("browser_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True)),
        sa.Column("exchanged_at", sa.DateTime(timezone=True)),
        sa.Column("verification_mail_pending", sa.Boolean(), nullable=False),
        sa.Column("admin_mail_pending", sa.Boolean(), nullable=False),
        sa.Column("approval_mail_pending", sa.Boolean(), nullable=False),
    )


def downgrade():
    op.drop_table("reviewer_email_challenges")
