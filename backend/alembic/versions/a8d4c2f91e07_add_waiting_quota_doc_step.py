"""add waiting_quota document step

Revision ID: a8d4c2f91e07
Revises: 5c8371584fa6
Create Date: 2026-10-17
"""

from collections.abc import Sequence

from alembic import op

revision: str = "a8d4c2f91e07"
down_revision: str | Sequence[str] | None = "5c8371584fa6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE docstep ADD VALUE 'waiting_quota'")


def downgrade() -> None:
    op.execute(
        "UPDATE documents SET current_step = 'extracting' WHERE current_step = 'waiting_quota'"
    )
    op.execute("ALTER TABLE documents ALTER COLUMN current_step TYPE text")
    op.execute("DROP TYPE docstep")
    op.execute(
        "CREATE TYPE docstep AS ENUM ('queued', 'reading', 'classifying', 'extracting', "
        "'normalizing', 'finished')"
    )
    op.execute(
        "ALTER TABLE documents ALTER COLUMN current_step TYPE docstep USING current_step::docstep"
    )
