"""Add probashi guardian snapshots and alerts."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d7f2a5c913ab"
down_revision: str | Sequence[str] | None = "c13e4ab2f0d1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("verified_name", sa.String(200), nullable=True))
    op.create_table(
        "guarded_lands",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("label_bn", sa.Text(), nullable=False),
        sa.Column("district", sa.String(120), nullable=False),
        sa.Column("upazila", sa.String(120), nullable=False),
        sa.Column("mouza", sa.String(120), nullable=False),
        sa.Column("dag_no", sa.String(100), nullable=False),
        sa.Column("khatian_no", sa.String(100), nullable=False),
        sa.Column("baseline_snapshot_id", sa.Uuid()),
        sa.Column("last_checked_at", sa.DateTime(timezone=True)),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_guarded_lands_user_id", "guarded_lands", ["user_id"])
    op.create_table(
        "guardian_snapshots",
        sa.Column("guarded_land_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("extraction_id", sa.Uuid(), nullable=False),
        sa.Column(
            "taken_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["extraction_id"], ["extractions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["guarded_land_id"], ["guarded_lands.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_guardian_snapshots_guarded_land_id", "guardian_snapshots", ["guarded_land_id"]
    )
    op.create_table(
        "guardian_alerts",
        sa.Column("guarded_land_id", sa.Uuid(), nullable=False),
        sa.Column("from_snapshot_id", sa.Uuid(), nullable=False),
        sa.Column("to_snapshot_id", sa.Uuid(), nullable=False),
        sa.Column("severity", sa.String(4), nullable=False),
        sa.Column("changes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("message_bn", sa.Text(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True)),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["from_snapshot_id"], ["guardian_snapshots.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["guarded_land_id"], ["guarded_lands.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["to_snapshot_id"], ["guardian_snapshots.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_guardian_alerts_guarded_land_id", "guardian_alerts", ["guarded_land_id"])


def downgrade() -> None:
    op.drop_index("ix_guardian_alerts_guarded_land_id", table_name="guardian_alerts")
    op.drop_table("guardian_alerts")
    op.drop_index("ix_guardian_snapshots_guarded_land_id", table_name="guardian_snapshots")
    op.drop_table("guardian_snapshots")
    op.drop_index("ix_guarded_lands_user_id", table_name="guarded_lands")
    op.drop_table("guarded_lands")
    op.drop_column("users", "verified_name")
