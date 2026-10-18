"""Add the mock-backed bayna escrow state machine."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "a42d0cb730a9"
down_revision = "e8b31a7f44c2"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "escrow_deals",
        sa.Column("land_id", sa.Uuid(), nullable=False),
        sa.Column("buyer_user_id", sa.Uuid(), nullable=False),
        sa.Column("seller_names", postgresql.JSONB(), nullable=False),
        sa.Column("price_paisa", sa.Integer(), nullable=False),
        sa.Column("bayna_paisa", sa.Integer(), nullable=False),
        sa.Column("deadline", sa.Date(), nullable=False),
        sa.Column("state", sa.String(24), nullable=False, server_default="draft"),
        sa.Column("buyer_agreed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("seller_agreed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("conditions_snapshot", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("registration_deed_no", sa.String(100)),
        sa.Column("registration_date", sa.Date()),
        sa.Column("seller_token_hash", sa.String(64), unique=True),
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["land_id"], ["lands.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["buyer_user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_escrow_deals_land_id", "escrow_deals", ["land_id"])
    op.create_table(
        "escrow_events",
        sa.Column("deal_id", sa.Uuid(), nullable=False),
        sa.Column("event", sa.String(32), nullable=False),
        sa.Column("from_state", sa.String(24), nullable=False),
        sa.Column("to_state", sa.String(24), nullable=False),
        sa.Column("actor", sa.String(200), nullable=False),
        sa.Column("message_bn", sa.Text(), nullable=False),
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["deal_id"], ["escrow_deals.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_escrow_events_deal_id", "escrow_events", ["deal_id"])
    op.create_table(
        "bank_mock_ledger",
        sa.Column("deal_id", sa.Uuid(), nullable=False),
        sa.Column("idempotency_key", sa.String(120), unique=True, nullable=False),
        sa.Column("operation", sa.String(16), nullable=False),
        sa.Column("amount_paisa", sa.Integer(), nullable=False),
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["deal_id"], ["escrow_deals.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_bank_mock_ledger_deal_id", "bank_mock_ledger", ["deal_id"])
    op.add_column("seller_links", sa.Column("escrow_deal_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_seller_links_escrow_deal",
        "seller_links",
        "escrow_deals",
        ["escrow_deal_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.execute("""
        CREATE FUNCTION reject_escrow_event_mutation() RETURNS trigger AS $$
        BEGIN RAISE EXCEPTION 'escrow_events is append-only'; END;
        $$ LANGUAGE plpgsql;
        CREATE TRIGGER escrow_events_append_only BEFORE UPDATE OR DELETE ON escrow_events
        FOR EACH ROW EXECUTE FUNCTION reject_escrow_event_mutation();
    """)


def downgrade():
    op.execute("DROP TRIGGER IF EXISTS escrow_events_append_only ON escrow_events")
    op.execute("DROP FUNCTION IF EXISTS reject_escrow_event_mutation()")
    op.drop_constraint("fk_seller_links_escrow_deal", "seller_links", type_="foreignkey")
    op.drop_column("seller_links", "escrow_deal_id")
    op.drop_index("ix_bank_mock_ledger_deal_id", table_name="bank_mock_ledger")
    op.drop_table("bank_mock_ledger")
    op.drop_index("ix_escrow_events_deal_id", table_name="escrow_events")
    op.drop_table("escrow_events")
    op.drop_index("ix_escrow_deals_land_id", table_name="escrow_deals")
    op.drop_table("escrow_deals")
