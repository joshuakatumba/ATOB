"""Interaction logging and preference signals for continuous model improvement."""

from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for statement in (
        """CREATE TABLE interaction_logs (
            id uuid PRIMARY KEY,
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            conversation_id uuid NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
            message_id uuid UNIQUE REFERENCES messages(id) ON DELETE CASCADE,
            mode varchar(20) NOT NULL CHECK (mode IN ('research','drafting')),
            prompt text NOT NULL,
            rewritten_query text,
            retrieved_sources jsonb NOT NULL DEFAULT '[]',
            response_text text NOT NULL DEFAULT '',
            draft_values jsonb,
            human_edited_values jsonb,
            status text NOT NULL DEFAULT 'incomplete',
            failure_stage varchar(60),
            failure_reason varchar(80),
            model_name varchar(120),
            latency_ms integer NOT NULL DEFAULT 0,
            input_tokens integer NOT NULL DEFAULT 0,
            output_tokens integer NOT NULL DEFAULT 0,
            explicit_rating smallint CHECK (explicit_rating IN (-1, 1)),
            copied_count integer NOT NULL DEFAULT 0,
            downloaded_count integer NOT NULL DEFAULT 0,
            supporting_opened_count integer NOT NULL DEFAULT 0,
            regenerated_count integer NOT NULL DEFAULT 0,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now())""",
        "CREATE INDEX interaction_logs_created ON interaction_logs(created_at DESC)",
        "CREATE INDEX interaction_logs_quality ON interaction_logs(status, explicit_rating)",
        "CREATE INDEX interaction_logs_conv ON interaction_logs(conversation_id, created_at DESC)",
    ):
        op.execute(statement)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS interaction_logs")

