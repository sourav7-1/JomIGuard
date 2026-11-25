"""NID name reading: English name, match result, confidence and name source."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a7c4e91b2d30"
down_revision: str | Sequence[str] | None = "e5b9c03d7a21"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "identity_verifications", sa.Column("name_en_as_per_nid", sa.String(200), nullable=True)
    )
    op.add_column("identity_verifications", sa.Column("match_result", sa.String(12), nullable=True))
    op.add_column(
        "identity_verifications", sa.Column("match_confidence", sa.Float(), nullable=True)
    )
    op.add_column(
        "identity_verifications",
        sa.Column("name_source", sa.String(10), server_default="typed", nullable=False),
    )


def downgrade() -> None:
    for column in ("name_source", "match_confidence", "match_result", "name_en_as_per_nid"):
        op.drop_column("identity_verifications", column)
