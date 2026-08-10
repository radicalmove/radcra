"""Merge the Rise interaction and account archiving migration branches."""

from collections.abc import Sequence

revision: str = "20260804_13"
down_revision: str | Sequence[str] | None = ("20260724_12", "20260804_12")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
