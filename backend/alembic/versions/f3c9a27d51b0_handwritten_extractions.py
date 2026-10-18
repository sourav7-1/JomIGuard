"""Store handwritten extraction metadata."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f3c9a27d51b0"
down_revision: str | Sequence[str] | None = "c5a7e19d2f40"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "extractions",
        sa.Column("handwritten", sa.Boolean(), server_default=sa.false(), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("extractions", "handwritten")
