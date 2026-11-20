"""Add land plot geometry and satellite checks."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e5b9c03d7a21"
down_revision: str | Sequence[str] | None = "d2714bc8a10f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "lands", sa.Column("geometry", postgresql.JSONB(astext_type=sa.Text()), nullable=True)
    )
    op.create_table(
        "satellite_checks",
        sa.Column("land_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(10), server_default="pending", nullable=False),
        sa.Column("buffer_m", sa.Float(), server_default="200", nullable=False),
        sa.Column("years", sa.JSON(), nullable=True),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["land_id"], ["lands.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_satellite_checks_land_id", "satellite_checks", ["land_id"])


def downgrade() -> None:
    op.drop_index("ix_satellite_checks_land_id", table_name="satellite_checks")
    op.drop_table("satellite_checks")
    op.drop_column("lands", "geometry")
