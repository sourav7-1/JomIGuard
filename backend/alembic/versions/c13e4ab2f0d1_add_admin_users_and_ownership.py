"""Add admin users and ownership boundaries.

Revision ID: c13e4ab2f0d1
Revises: 229c6bc6c37e, a8d4c2f91e07
Create Date: 2026-10-17
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.core.config import settings

revision: str = "c13e4ab2f0d1"
down_revision: str | Sequence[str] | None = ("229c6bc6c37e", "a8d4c2f91e07")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
    )
    admin_id = uuid.uuid4()
    op.get_bind().execute(
        sa.text("INSERT INTO users (id, username, password_hash) VALUES (:id, :name, :hash)"),
        {"id": admin_id, "name": settings.admin_username, "hash": "!"},
    )
    op.add_column("lands", sa.Column("owner_id", sa.Uuid(), nullable=True))
    op.create_index("ix_lands_owner_id", "lands", ["owner_id"])
    op.create_foreign_key("fk_lands_owner_id_users", "lands", "users", ["owner_id"], ["id"])
    op.add_column("documents", sa.Column("owner_id", sa.Uuid(), nullable=True))
    op.create_index("ix_documents_owner_id", "documents", ["owner_id"])
    op.create_foreign_key("fk_documents_owner_id_users", "documents", "users", ["owner_id"], ["id"])
    op.execute(
        sa.text("UPDATE lands SET owner_id = :id WHERE owner_id IS NULL").bindparams(id=admin_id)
    )
    op.execute(
        sa.text("UPDATE documents SET owner_id = :id WHERE owner_id IS NULL").bindparams(
            id=admin_id
        )
    )


def downgrade() -> None:
    op.drop_constraint("fk_documents_owner_id_users", "documents", type_="foreignkey")
    op.drop_index("ix_documents_owner_id", table_name="documents")
    op.drop_column("documents", "owner_id")
    op.drop_constraint("fk_lands_owner_id_users", "lands", type_="foreignkey")
    op.drop_index("ix_lands_owner_id", table_name="lands")
    op.drop_column("lands", "owner_id")
    op.drop_table("users")
