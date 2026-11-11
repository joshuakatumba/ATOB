"""M2 owned conversations, immutable completed messages and feedback."""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for sql in (
        """CREATE TABLE conversations (
            id uuid PRIMARY KEY, user_id uuid NOT NULL REFERENCES users(id),
            title varchar(200) NOT NULL DEFAULT '', mode text NOT NULL
            CHECK (mode IN ('research','drafting')), deleted_at timestamptz,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now())""",
        "CREATE INDEX conversations_owner_updated ON conversations(user_id, updated_at DESC, id)",
        """CREATE TABLE messages (
            id uuid PRIMARY KEY, conversation_id uuid NOT NULL REFERENCES conversations(id),
            role text NOT NULL CHECK (role IN ('user','assistant')),
            content text NOT NULL DEFAULT '',
            status text NOT NULL CHECK (status IN ('complete','incomplete','blocked')),
            model text, input_tokens integer NOT NULL DEFAULT 0,
            output_tokens integer NOT NULL DEFAULT 0, retrieval_trace_id uuid,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now())""",
        "CREATE INDEX messages_conversation ON messages(conversation_id, created_at)",
        """CREATE TABLE message_feedback (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            message_id uuid NOT NULL REFERENCES messages(id),
            user_id uuid NOT NULL REFERENCES users(id),
            rating smallint NOT NULL CHECK (rating IN (-1,1)), comment varchar(2000),
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(), UNIQUE(message_id, user_id))""",
        """CREATE FUNCTION protect_completed_message() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN IF OLD.status = 'complete' THEN RAISE EXCEPTION 'immutable_message';
            END IF; RETURN NEW; END $$""",
        """CREATE TRIGGER complete_message_immutable BEFORE UPDATE ON messages
            FOR EACH ROW EXECUTE FUNCTION protect_completed_message()""",
    ):
        op.execute(sql)


def downgrade() -> None:
    for sql in (
        "DROP TABLE message_feedback",
        "DROP TABLE messages",
        "DROP FUNCTION protect_completed_message()",
        "DROP TABLE conversations",
    ):
        op.execute(sql)
