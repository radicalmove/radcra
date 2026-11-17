"""Default-off per-course LEARN enrollment."""
from alembic import op
import sqlalchemy as sa

revision = "20261118_18"
down_revision = "20261110_17"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("courses", sa.Column("email_onboarding_enabled", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("courses", sa.Column("email_onboarding_configured", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("reviewer_email_challenges", sa.Column("course_onboarding", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("reviewer_email_challenges", sa.Column("signin_only", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_table("course_migration_previews",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("actor_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("source_course_id", sa.Uuid(), sa.ForeignKey("courses.id"), nullable=False),
        sa.Column("target_course_id", sa.Uuid(), sa.ForeignKey("courses.id"), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("rows", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("applied_at", sa.DateTime(timezone=True)),
        sa.Column("selection", sa.JSON()), sa.Column("result", sa.JSON()))
    op.create_table("course_migration_mappings",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("source_course_id", sa.Uuid(), sa.ForeignKey("courses.id"), nullable=False),
        sa.Column("target_course_id", sa.Uuid(), sa.ForeignKey("courses.id"), nullable=False, unique=True),
        sa.Column("actor_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("source_course_id", "target_course_id", name="uq_course_migration_pair"))


def downgrade():
    op.drop_table("course_migration_mappings")
    op.drop_table("course_migration_previews")
    op.drop_column("reviewer_email_challenges", "signin_only")
    op.drop_column("reviewer_email_challenges", "course_onboarding")
    op.drop_column("courses", "email_onboarding_configured")
    op.drop_column("courses", "email_onboarding_enabled")
