"""documents land_id index and set null

Revision ID: 794f1ab998c6
Revises: f28bef5d7d7f
Create Date: 2026-10-09 12:56:47.720213

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "794f1ab998c6"
down_revision: str | Sequence[str] | None = "f28bef5d7d7f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint("documents_land_id_fkey", "documents", type_="foreignkey")
    op.create_foreign_key(
        "documents_land_id_fkey",
        "documents",
        "lands",
        ["land_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(op.f("ix_documents_land_id"), "documents", ["land_id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_documents_land_id"), table_name="documents")
    op.drop_constraint("documents_land_id_fkey", "documents", type_="foreignkey")
    op.create_foreign_key(
        "documents_land_id_fkey",
        "documents",
        "lands",
        ["land_id"],
        ["id"],
    )
