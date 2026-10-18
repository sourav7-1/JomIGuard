"""Store per-user land assistant conversations."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "c5a7e19d2f40"
down_revision = "a42d0cb730a9"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "agent_conversations",
        sa.Column(
            "land_id", sa.Uuid(), sa.ForeignKey("lands.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_agent_conversations_land_id", "agent_conversations", ["land_id"])
    op.create_index("ix_agent_conversations_user_id", "agent_conversations", ["user_id"])
    op.create_table(
        "agent_messages",
        sa.Column(
            "conversation_id",
            sa.Uuid(),
            sa.ForeignKey("agent_conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("tool_calls", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("tool_results", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_agent_messages_conversation_id", "agent_messages", ["conversation_id"])


def downgrade():
    op.drop_table("agent_messages")
    op.drop_table("agent_conversations")
