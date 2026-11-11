# M1 foundations

Civis previously contained specifications and a visual reference. This change adds the
FastAPI foundations, provider-owned auth, owned profiles and consents, atomic quota ledger,
Redis rate limits, production content guards, private-storage readiness, and Arq runtime.
It includes reversible Alembic migrations, pinned local containers and GitHub Actions checks.

Local verification exercised real Postgres, Redis, SuperTokens and SMTP. The 100-request
quota race spends exactly five at balance five. Spend/refund replays, unverified allowance,
profile/consent ownership and production guards passed. Lint and strict Python typecheck pass.
Storage readiness and container verification are pending their builds; remote CI is pending.
M2–M6 and production deployment are not implemented by this milestone.

## Dependency additions and one-line justifications

| Package | Version | Purpose / official reference consulted |
|---|---|---|
| FastAPI | 0.115.12 | Required async API; pinned middleware documentation and installed dependency/response signatures. |
| Pydantic | 2.11.7 | Required strict input/output validation; pinned model documentation. |
| SQLAlchemy | 2.0.41 | Required async database engine; pinned asyncio documentation. |
| Alembic | 1.16.2 | Required reversible migrations; installed version's context/op signatures and asyncio cookbook. |
| asyncpg | 0.30.0 | Required PostgreSQL async driver; official usage documentation. |
| redis | 5.3.1 | Async cache and atomic Lua rate limits; pinned below 6 for Arq compatibility; installed asyncio/eval API docs. |
| supertokens-python | 0.30.3 | D1 provider-owned credentials, sessions and email flows; installed version's public recipes and signatures. |
| uvicorn | 0.34.3 | ASGI container entrypoint; installed CLI help. |
| boto3 / botocore | 1.38.46 | S3 private storage readiness/bootstrap; installed client service model and API signatures. |
| pytest | 8.4.1 | Test runner; official 8.4 fixtures guide. |
| pytest-asyncio | 1.0.0 | Async integration fixtures; versioned documentation. |
| httpx | 0.28.1 | ASGI integration client; pinned async documentation and installed transport signature. |
| ruff | 0.12.1 | Linting; installed CLI help. |
| mypy | 1.16.1 | Strict backend typecheck; installed CLI help. |
| arq | 0.26.3 | Required Redis worker runtime, JSON job serialization; pinned documentation and installed Worker API. |
| opentelemetry-api/sdk | 1.34.1 | Required request tracing with only allowlisted status metadata; pinned trace API source. |
| opentelemetry-exporter-otlp-proto-http | 1.34.1 | Export explicit spans to an environment-configured collector. |
| sentry-sdk | 2.30.0 | Required error reporting integration with strict event redaction; pinned client API source. |


Infrastructure: Python 3.12.11 runs the API/worker; pgvector 0.8.0/Postgres 17 provides local
vector-capable SQL; Postgres 17.5 isolates the auth database; Redis 7.4.4 supplies rate limits
and queues; SuperTokens 10.1.0 implements D1; Mailpit 1.26.2 captures local email;
ClamAV 1.4.2 defines the disabled upload scanner. MinIO RELEASE.2025-10-15T17-29-55Z
is built using Go 1.24.8 from upstream source. Checkout 4.2.2 and setup-python 5.6.0
provide pinned CI checkout and Python provisioning. Python transitive versions are frozen
in requirements.lock; upstream Go dependencies are fixed by its go.mod/go.sum.

See KNOWN_ISSUES.md for unresolved verification and OWNER_TASKS.md for release gates.
