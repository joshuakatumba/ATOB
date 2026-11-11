"""M1 users, consents, content provenance and atomic quota ledger."""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    for statement in (
        "CREATE EXTENSION IF NOT EXISTS vector",
        """CREATE TABLE users (
            id uuid PRIMARY KEY, auth_user_id text UNIQUE NOT NULL,
            email text NOT NULL, name varchar(200) NOT NULL DEFAULT '',
            plan_id uuid, preferences jsonb NOT NULL DEFAULT '{"theme":"system"}',
            referral_code uuid NOT NULL UNIQUE DEFAULT gen_random_uuid(), deleted_at timestamptz,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now())""",
        """CREATE TABLE consents (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid NOT NULL REFERENCES users(id), document text NOT NULL,
            version text NOT NULL, accepted_at timestamptz NOT NULL DEFAULT now(),
            created_at timestamptz NOT NULL DEFAULT now())""",
        """CREATE TABLE usage_balance (
            user_id uuid PRIMARY KEY REFERENCES users(id), balance integer NOT NULL DEFAULT 0
            CHECK (balance >= 0), created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now())""",
        """CREATE TABLE usage_ledger (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid NOT NULL REFERENCES users(id), kind text NOT NULL
            CHECK (kind IN ('grant','spend','refund')), amount integer NOT NULL CHECK (amount > 0),
            reason text NOT NULL, request_id uuid NOT NULL, balance_after integer NOT NULL,
            refund_of uuid REFERENCES usage_ledger(id),
            created_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE (request_id, kind), CHECK ((kind = 'refund') = (refund_of IS NOT NULL)))""",
        "CREATE INDEX ledger_owner ON usage_ledger(user_id, created_at)",
        """CREATE TABLE content_provenance (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(), source text NOT NULL,
            is_fake boolean NOT NULL, approved boolean NOT NULL DEFAULT false,
            enabled boolean NOT NULL DEFAULT false, created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now())""",
        """CREATE FUNCTION prevent_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN RAISE EXCEPTION 'append_only'; END $$""",
        """CREATE TRIGGER ledger_append_only BEFORE UPDATE OR DELETE ON usage_ledger
            FOR EACH ROW EXECUTE FUNCTION prevent_mutation()""",
        """CREATE TRIGGER consent_append_only BEFORE UPDATE OR DELETE ON consents
            FOR EACH ROW EXECUTE FUNCTION prevent_mutation()""",
        """CREATE FUNCTION mutate_quota(owner uuid, request uuid, operation text,
            quantity integer, purpose text) RETURNS integer LANGUAGE plpgsql AS $$
        DECLARE prior usage_ledger; spent usage_ledger; result integer;
        BEGIN
            IF operation NOT IN ('grant','spend','refund') OR quantity <= 0 THEN RETURN -1; END IF;
            -- Serialize all mutations for one account. Never use a read-then-write balance.
            PERFORM 1 FROM usage_balance WHERE user_id = owner FOR UPDATE;
            IF NOT FOUND THEN RETURN -1; END IF;
            SELECT * INTO prior FROM usage_ledger WHERE request_id = request AND kind = operation;
            IF FOUND THEN
                IF prior.user_id <> owner OR prior.amount <> quantity THEN RETURN -1; END IF;
                RETURN prior.balance_after;
            END IF;
            IF operation = 'refund' THEN
                SELECT * INTO spent FROM usage_ledger
                    WHERE request_id = request AND kind = 'spend' AND user_id = owner;
                IF NOT FOUND OR spent.amount <> quantity THEN RETURN -1; END IF;
            END IF;
            WITH updated AS (
                UPDATE usage_balance SET balance = balance +
                    CASE WHEN operation = 'spend' THEN -quantity ELSE quantity END,
                    updated_at = now()
                WHERE user_id = owner AND (operation <> 'spend' OR balance >= quantity)
                RETURNING balance
            ), inserted AS (
                INSERT INTO usage_ledger(user_id, kind, amount, reason, request_id,
                    balance_after, refund_of)
                SELECT owner, operation, quantity, purpose, request, balance,
                    CASE WHEN operation = 'refund' THEN spent.id ELSE NULL END FROM updated
                RETURNING balance_after
            ) SELECT balance_after INTO result FROM inserted;
            RETURN COALESCE(result, -1);
        END $$""",
    ):
        op.execute(statement)


def downgrade() -> None:
    for statement in (
        "DROP FUNCTION mutate_quota(uuid, uuid, text, integer, text)",
        "DROP TABLE content_provenance",
        "DROP TABLE usage_ledger",
        "DROP TABLE usage_balance",
        "DROP TABLE consents",
        "DROP TABLE users",
        "DROP FUNCTION prevent_mutation()",
        # Extension may predate this app; leave installed for other tenants.
    ):
        op.execute(statement)
