"""Add deed provenance, extraction actor and append-only document audit events."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d18a9f70bc31"
down_revision: str | Sequence[str] | None = "c0e41d7ab932"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("source_type", sa.String(40), server_default="user_upload", nullable=False),
    )
    op.add_column("extractions", sa.Column("created_by", sa.String(80), nullable=True))
    op.execute(
        "UPDATE extractions e SET created_by = CASE "
        "WHEN e.extractor = 'seed' THEN 'seed' "
        "WHEN e.extractor = 'human' THEN (SELECT d.owner_id::text FROM documents d "
        "WHERE d.id = e.document_id) ELSE 'ai' END"
    )
    op.create_table(
        "document_audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event", sa.String(40), nullable=False),
        sa.Column("actor", sa.String(80), nullable=False),
        sa.Column("details", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index(
        "ix_document_audit_events_document_id", "document_audit_events", ["document_id"]
    )
    op.execute(
        """CREATE FUNCTION reject_document_audit_mutation() RETURNS trigger
        LANGUAGE plpgsql AS $$ BEGIN
        RAISE EXCEPTION 'document audit events are append-only';
        END $$"""
    )
    op.execute(
        "CREATE TRIGGER document_audit_append_only BEFORE UPDATE OR DELETE "
        "ON document_audit_events FOR EACH ROW EXECUTE FUNCTION reject_document_audit_mutation()"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER document_audit_append_only ON document_audit_events")
    op.execute("DROP FUNCTION reject_document_audit_mutation()")
    op.drop_index("ix_document_audit_events_document_id", table_name="document_audit_events")
    op.drop_table("document_audit_events")
    op.drop_column("extractions", "created_by")
    op.drop_column("documents", "source_type")
