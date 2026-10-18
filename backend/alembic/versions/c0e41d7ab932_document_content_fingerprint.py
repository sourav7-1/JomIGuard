"""Store the upload-time document fingerprint."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c0e41d7ab932"
down_revision: str | Sequence[str] | None = "b7e42c1a90df"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("content_sha256", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("documents", "content_sha256")
