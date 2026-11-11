"""Add the referenced plan schema without editing the applied foundation migration."""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""CREATE TABLE plans (
        id uuid PRIMARY KEY, name text NOT NULL,
        price_ugx integer NOT NULL CHECK (price_ugx >= 0),
        prompts integer NOT NULL CHECK (prompts >= 0),
        duration_days integer NOT NULL CHECK (duration_days > 0),
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now())""")
    op.execute(
        "ALTER TABLE users ADD CONSTRAINT users_plan_fk FOREIGN KEY (plan_id) REFERENCES plans(id)"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP CONSTRAINT users_plan_fk")
    op.execute("DROP TABLE plans")
