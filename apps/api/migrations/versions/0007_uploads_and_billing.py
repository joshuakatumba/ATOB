"""Commercial UGX subscription billing, webhook reconciliation and private document uploads."""

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for statement in (
        """CREATE TABLE uploaded_documents (
            id uuid PRIMARY KEY,
            user_id uuid NOT NULL REFERENCES users(id),
            conversation_id uuid REFERENCES conversations(id),
            filename varchar(255) NOT NULL,
            content_type varchar(120) NOT NULL,
            size_bytes integer NOT NULL CHECK (size_bytes > 0 AND size_bytes <= 10485760),
            page_count integer NOT NULL CHECK (page_count >= 1 AND page_count <= 30),
            sha256 varchar(64) NOT NULL,
            storage_key text NOT NULL,
            encrypted_pages bytea NOT NULL,
            warnings jsonb NOT NULL DEFAULT '[]',
            status text NOT NULL CHECK (status IN ('processing','ready','failed','deleted'))
                DEFAULT 'ready',
            created_at timestamptz NOT NULL DEFAULT now(),
            expires_at timestamptz NOT NULL DEFAULT (now() + interval '30 days'),
            deleted_at timestamptz)""",
        "CREATE INDEX uploaded_documents_owner ON uploaded_documents(user_id, created_at DESC)",
        """CREATE TABLE payment_transactions (
            id uuid PRIMARY KEY,
            user_id uuid NOT NULL REFERENCES users(id),
            plan_id uuid NOT NULL REFERENCES plans(id),
            provider varchar(40) NOT NULL,
            tx_ref varchar(120) NOT NULL UNIQUE,
            provider_tx_id varchar(120),
            amount_ugx integer NOT NULL CHECK (amount_ugx > 0),
            currency varchar(10) NOT NULL DEFAULT 'UGX',
            status text NOT NULL CHECK (status IN ('pending','completed','failed','reversed'))
                DEFAULT 'pending',
            checkout_url text,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now())""",
        "CREATE INDEX payment_transactions_owner ON payment_transactions(user_id, created_at DESC)",
        """CREATE TABLE subscriptions (
            id uuid PRIMARY KEY,
            user_id uuid NOT NULL REFERENCES users(id),
            plan_id uuid NOT NULL REFERENCES plans(id),
            transaction_id uuid NOT NULL UNIQUE REFERENCES payment_transactions(id),
            status text NOT NULL CHECK (status IN ('active','expired','revoked')) DEFAULT 'active',
            starts_at timestamptz NOT NULL DEFAULT now(),
            expires_at timestamptz NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now())""",
        "CREATE INDEX subscriptions_owner ON subscriptions(user_id, expires_at DESC)",
        """INSERT INTO plans (id, name, price_ugx, prompts, duration_days) VALUES
            ('00000000-0000-0000-0000-000000000101', 'Starter', 25000, 50, 30),
            ('00000000-0000-0000-0000-000000000102', 'Pro', 75000, 200, 30),
            ('00000000-0000-0000-0000-000000000103', 'Chambers', 250000, 1000, 30)
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                price_ugx = EXCLUDED.price_ugx,
                prompts = EXCLUDED.prompts,
                duration_days = EXCLUDED.duration_days,
                updated_at = now()""",
    ):
        op.execute(statement)


def downgrade() -> None:
    for statement in (
        "DROP TABLE subscriptions",
        "DROP TABLE payment_transactions",
        "DROP TABLE uploaded_documents",
    ):
        op.execute(statement)

