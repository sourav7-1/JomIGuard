"""Mark replaced demo escrow deals as archived without deleting their history."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b7e42c1a90df"
down_revision: str | Sequence[str] | None = "f3c9a27d51b0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "escrow_deals",
        sa.Column("archived", sa.Boolean(), server_default=sa.false(), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("escrow_deals", "archived")
