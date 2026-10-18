"""Record the known upload history for documents that predate the audit table."""

from collections.abc import Sequence

from alembic import op

revision: str = "d2714bc8a10f"
down_revision: str | Sequence[str] | None = "d18a9f70bc31"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """INSERT INTO document_audit_events (id, document_id, event, actor, details, created_at)
        SELECT gen_random_uuid(), d.id, 'uploaded', COALESCE(d.owner_id::text, 'system'),
        jsonb_build_object('source_type', d.source_type, 'backfilled', true), d.created_at
        FROM documents d
        WHERE NOT EXISTS (
          SELECT 1 FROM document_audit_events e
          WHERE e.document_id = d.id AND e.event = 'uploaded'
        )"""
    )


def downgrade() -> None:
    # Audit entries are append-only and are intentionally retained on downgrade.
    pass
