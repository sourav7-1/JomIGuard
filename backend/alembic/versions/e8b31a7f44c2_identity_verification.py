"""Add result-only identity verification and one-use seller links."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e8b31a7f44c2"
down_revision: str | Sequence[str] | None = "d7f2a5c913ab"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "identity_verifications",
        sa.Column("land_id", sa.Uuid(), nullable=True),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("party", sa.String(10), nullable=False),
        sa.Column("seller_name_on_deed", sa.String(200), nullable=True),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("name_bn_as_per_nid", sa.String(200), nullable=True),
        sa.Column("father_name_as_per_nid", sa.String(200), nullable=True),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("provider_ref", sa.String(100), nullable=False),
        sa.Column("consent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consent_version", sa.String(40), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["land_id"], ["lands.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_identity_verifications_land_id", "identity_verifications", ["land_id"])
    op.create_index("ix_identity_verifications_user_id", "identity_verifications", ["user_id"])
    op.create_table(
        "seller_links",
        sa.Column("land_id", sa.Uuid(), nullable=False),
        sa.Column("seller_name_on_deed", sa.String(200), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consent_version", sa.String(40), nullable=True),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["land_id"], ["lands.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_seller_links_land_id", "seller_links", ["land_id"])


def downgrade() -> None:
    op.drop_index("ix_seller_links_land_id", table_name="seller_links")
    op.drop_table("seller_links")
    op.drop_index("ix_identity_verifications_user_id", table_name="identity_verifications")
    op.drop_index("ix_identity_verifications_land_id", table_name="identity_verifications")
    op.drop_table("identity_verifications")
