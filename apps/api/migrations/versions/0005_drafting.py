"""Encrypted conversation drafts with pinned template versions and optimistic revisions."""

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""CREATE TABLE conversation_drafts (
        conversation_id uuid PRIMARY KEY REFERENCES conversations(id),
        user_id uuid NOT NULL REFERENCES users(id),
        template_version_id uuid NOT NULL REFERENCES template_versions(id),
        encrypted_values bytea NOT NULL,
        revision integer NOT NULL CHECK(revision>0),
        document_id uuid REFERENCES documents(id),
        updated_at timestamptz NOT NULL DEFAULT now())""")
    op.execute("CREATE INDEX conversation_drafts_owner ON conversation_drafts(user_id)")


def downgrade() -> None:
    op.execute("DROP TABLE conversation_drafts")
