"""Authenticated template catalog, private generated documents and support tickets."""

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for statement in (
        """CREATE TABLE templates (id uuid PRIMARY KEY, slug text NOT NULL UNIQUE,
        title varchar(200) NOT NULL, category varchar(100) NOT NULL)""",
        """CREATE TABLE template_versions (id uuid PRIMARY KEY,
        template_id uuid NOT NULL REFERENCES templates(id), version integer NOT NULL,
        fields jsonb NOT NULL, body jsonb NOT NULL, is_fake boolean NOT NULL,
        status text NOT NULL CHECK(status IN ('draft','approved')), UNIQUE(template_id,version))""",
        """CREATE TABLE documents (id uuid PRIMARY KEY, user_id uuid NOT NULL REFERENCES users(id),
        conversation_id uuid REFERENCES conversations(id),
        template_version_id uuid NOT NULL REFERENCES template_versions(id),
        encrypted_values bytea NOT NULL, storage_key text NOT NULL, filename text NOT NULL,
        created_at timestamptz NOT NULL DEFAULT now())""",
        "CREATE INDEX documents_owner ON documents(user_id, created_at DESC)",
        "ALTER TABLE messages ADD COLUMN document_id uuid REFERENCES documents(id)",
        """CREATE TABLE feedback_tickets (id uuid PRIMARY KEY,
        user_id uuid NOT NULL REFERENCES users(id), category varchar(100) NOT NULL,
        message varchar(2000) NOT NULL, conversation_id uuid REFERENCES conversations(id),
        created_at timestamptz NOT NULL DEFAULT now())""",
    ):
        op.execute(statement)


def downgrade() -> None:
    for statement in (
        "DROP TABLE feedback_tickets",
        "ALTER TABLE messages DROP COLUMN document_id",
        "DROP TABLE documents",
        "DROP TABLE template_versions",
        "DROP TABLE templates",
    ):
        op.execute(statement)
