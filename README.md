# Civis

React 18/plain JSX/Vite frontend based on the owner’s Civis.jsx, with an existing FastAPI,
Postgres, Redis, SuperTokens and private S3 backend. The active integration passes local API and browser smoke checks; production and remote CI remain unverified.
See [STATUS.md](STATUS.md), [KNOWN_ISSUES.md](KNOWN_ISSUES.md) and [NOTES.md](NOTES.md).

## Real Groq chat and existing templates

See [docs/CORE_TESTING.md](docs/CORE_TESTING.md) for the short setup. Set LLM_PROVIDER=groq,
FAKE_MODEL=false, GROQ_API_KEY and LLM_MODEL in the existing private .env. Changing the key
requires only replacing that environment value and recreating API/worker containers.
The owner-approved testing catalog imports the 62 original Civis.jsx templates without wording changes.
Chat memory persists per conversation and sends bounded recent history to the model; it is not cross-chat memory.
Unsubmitted forms, verified legal RAG and automatic template prefill remain unfinished.

## Local development

Requirements: Docker with Compose v2, Python 3, and free localhost ports listed below.
From the repository root, the startup entry point is:

```sh
./scripts/dev.sh
```

This generates private credentials in ignored `.env`, starts dependencies, builds containers,
waits for auth/storage, applies migrations, creates the private bucket, seeds development
records and starts API, worker and web. The command and browser flow have been verified locally.
An existing `.env` retains its values; missing development settings are appended.
See [.env.example](.env.example) for configuration. Never commit `.env`.
For an older environment, enable `ALLOW_UNAPPROVED_TEMPLATES=true` to expose development drafts.

- Web: <http://localhost:53000> (same-origin API/auth proxy).
- API health: <http://localhost:58000/v1/health>; dependency health: `/v1/ready`.
- Authenticated schema: `/openapi.json`.
- Mail catcher: <http://localhost:58025>.
- Private storage endpoint: <http://localhost:59000> (downloads use five-minute signed URLs).

Development uses explicitly labelled fake model/template/legal records from `content/dev-fake/`.
Fake test fixtures remain available for automated tests. The normal testing catalog uses the owner-approved original templates.
No real legal corpus is connected; owner approval of the original templates is recorded for testing. `content/templates/` is untouched.
`REQUIRE_EMAIL_VERIFICATION=false` is a local-only setting because the supplied UI has no
verification screen. Production refuses that setting, fake flags and fake loaded provenance.
To use Anthropic locally, set `FAKE_MODEL=false`, `LLM_PROVIDER=anthropic`, `LLM_MODEL` and
`ANTHROPIC_API_KEY`. Without a key, development streams the labelled fake fixture.

The first MinIO source build can take several minutes. All services use the `civis-dev` Compose
project; production must use managed Postgres and separately provisioned private storage.
For frontend-only development with the API running on port 58000:

```sh
npm --prefix apps/web ci
npm --prefix apps/web run dev
```

## Checks

Install pinned Python tooling with `python3 -m venv .venv` and
`.venv/bin/pip install -r requirements.lock`. Use a disposable database for migration reversals:

```sh
docker compose exec -T postgres createdb -U civis civis_test
CIVIS_TEST_DATABASE=1 python3 scripts/run.py .venv/bin/alembic -c apps/api/alembic.ini upgrade head
CIVIS_TEST_DATABASE=1 python3 scripts/run.py .venv/bin/pytest apps/api/tests/test_ui_flow.py -q
npm --prefix apps/web run build
docker compose build api web
```

The integration test uses real Postgres, Redis, SuperTokens and storage with the fake model.
It covers server chat/quota/reload, template search/paging/escaping, generation/download,
ownership, preferences, feedback and logout. The full smoke and the separate twenty-request quota race pass.
The new migration completed up/down/up on `civis_test`. Browser acceptance passes locally; remote CI remains pending.

## Scope

The original UI’s CSS, classes, copy and elements are frozen; no frontend dependency was added.
Native fetch handles cookies and SSE. Provider httpOnly cookies replace the browser account store.
Voice input, install guidance, sharing, invites and sidebar collapse retain their original behavior.
Stop, thumbs, citations UI, verification/reset screens, deletion/export, uploads, payments,
real legal retrieval and production release are deferred. These are not completed features.

Optional sanitized telemetry: `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT`, `SENTRY_DSN`,
`LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`.
External delivery is unverified. Owner release inputs remain in [OWNER_TASKS.md](OWNER_TASKS.md).
# ATOB
