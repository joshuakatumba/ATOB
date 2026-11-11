# Dependency record (M1)

All Python runtime and test dependencies, including transitive packages, are pinned in
requirements.lock. Container and CI action versions are pinned in compose.yaml and the workflow.
This is not a completed dependency security audit; M6 must audit and update the lock as necessary.

Direct additions and justification:

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

Official references:
- https://raw.githubusercontent.com/fastapi/fastapi/0.115.12/docs/en/docs/tutorial/middleware.md
- https://raw.githubusercontent.com/pydantic/pydantic/v2.11.7/docs/concepts/models.md
- https://raw.githubusercontent.com/sqlalchemy/sqlalchemy/rel_2_0_41/doc/build/orm/extensions/asyncio.rst
- https://alembic.sqlalchemy.org/en/latest/cookbook.html#using-asyncio-with-alembic
- https://magicstack.github.io/asyncpg/current/usage.html
- https://redis.readthedocs.io/en/v6.2.0/examples/asyncio_examples.html
- https://supertokens.com/docs/quickstart
- https://supertokens.com/docs/additional-verification/email-verification/initial-setup
- https://github.com/encode/httpx/blob/0.28.1/docs/async.md
- https://docs.pytest.org/en/8.4.x/how-to/fixtures.html
- https://pytest-asyncio.readthedocs.io/en/v1.0.0/
- https://docs.docker.com/compose/how-tos/startup-order/
- https://github.com/actions/checkout/tree/v4.2.2
- https://github.com/actions/setup-python/tree/v5.6.0
- https://raw.githubusercontent.com/python-arq/arq/v0.26.3/docs/index.rst
- https://raw.githubusercontent.com/getsentry/sentry-python/2.30.0/sentry_sdk/client.py
- https://raw.githubusercontent.com/open-telemetry/opentelemetry-python/v1.34.1/opentelemetry-sdk/src/opentelemetry/sdk/trace/__init__.py
- https://raw.githubusercontent.com/minio/minio/RELEASE.2025-10-15T17-29-55Z/README.md

Some pinned documentation URLs were unavailable to the browsing tool. Installed vendor source
and signatures were inspected rather than assuming APIs from memory. This does not establish
compatibility until integration tests pass. Transitive dependencies are not called directly by Civis.

## D1 licence check — 2026-11-07
The official community licence says: “This software is licensed under the Apache License,
Version 2.0”. Source: https://supertokens.com/legal/community-license
The installed Python SDK 0.30.3 contains the same Apache-2.0 notice.
Core repository separates enterprise code from community code:
https://github.com/supertokens/supertokens-core
**Owner and counsel to confirm** the exact deployed artifact and enabled features.
Core 10.1.0 advertises CDI 5.3, required by SDK 0.30.3. Core 9.3.0 was incompatible
and is no longer configured. Backend signup, verification, login and reset have run against Core.

## Infrastructure and deferred integrations
- MinIO is built from upstream RELEASE.2025-10-15T17-29-55Z with Go 1.24.8, following
  its source-only distribution instructions. Published Docker Hub/Quay images were unavailable.
  This remains local development storage; production private S3 storage is supplied by the owner.
- pgvector 0.8.0/Postgres 17, Redis 7.4.4, SuperTokens 10.1.0, Mailpit 1.26.2 and
  optional ClamAV 1.4.2 implement the requested local services.
- Arq health-job roundtrip passed against real Redis. Feature jobs belong to later milestones.
- OpenTelemetry and Sentry exporter delivery has not been tested with external collector credentials.
- Langfuse belongs to the model tracing work; M1 has no model calls to trace.

## Historical M2 additions (replaced frontend)

| Package | Pin | One-line justification |
|---|---|---|
| next / eslint-config-next | 16.4.5 | Required App Router application and framework lint rules. |
| react / react-dom | 19.3.1 | Interactive workspace and auth screens. |
| supertokens-web-js | 0.15.0 | Provider-owned browser sessions and all five auth flows. |
| typescript | 5.9.3 | Strict frontend typechecking. |
| tailwindcss / @tailwindcss/postcss | 4.3.5 | Required styling stack and its build integration. |
| postcss | 8.5.32 | CSS processing; updated to remove the detected high advisory. |
| eslint | 9.39.1 | Frontend lint runner, compatible with pinned Next configuration. |
| @types/node | 22.15.30 | Build/test Node types. |
| @types/react / @types/react-dom | 19.2.2 | Strict React/DOM types. |
| @playwright/test | 1.65.0 | Real browser integration tests. |
| langfuse | 3.1.0 | LLM traces containing technical metadata and usage only. |
| anyio | 4.16.0 (existing lock) | Shield persistence/refunds during client disconnect cleanup. |

Official API references consulted: pinned Next 16.4.5 server/client guide, React 19.3 hooks,
TypeScript 5.9 release notes, Tailwind 4.3 Next guide, installed SuperTokens 0.15 declarations,
Playwright 1.65 vendor types, AnyIO 4.16 cancellation/shielding docs, Anthropic streaming API,
and Langfuse 3.1.0 client source/signatures. npm transitive versions are frozen in package-lock.json.

- https://raw.githubusercontent.com/vercel/next.js/v16.4.5/docs/01-app/01-getting-started/05-server-and-client-components.mdx
- https://react.dev/reference/react/useState
- https://www.typescriptlang.org/docs/handbook/release-notes/typescript-5-9.html
- https://tailwindcss.com/docs/installation/framework-guides/nextjs
- https://anyio.readthedocs.io/en/stable/cancellation.html
- https://platform.claude.com/docs/en/build-with-claude/streaming
- https://raw.githubusercontent.com/langfuse/langfuse-python/v3.1.0/langfuse/_client/client.py

Eight moderate npm advisories remain for M6 audit; the detected high PostCSS advisory was fixed.

## Current React/Vite integration

Active frontend pins: react/react-dom 18.3.1, vite 8.3.6, @vitejs/plugin-react 6.2.1.
No integration dependency was added; package.json and lock are unchanged from the port input.
The historical Next.js/TypeScript/Tailwind/SuperTokens browser SDK list above is not the active frontend.
Existing pycryptodome 3.20.0 supplies authenticated encryption; stdlib zipfile/XML escaping supplies OOXML.
Backend lint/typecheck now pass; this is not a dependency security audit.

Groq testing integration adds no dependency: existing httpx 0.28.1 calls the Groq OpenAI-compatible v1 HTTP API.
Official references consulted: https://console.groq.com/docs/openai, https://console.groq.com/docs/text-chat,
https://console.groq.com/docs/api-reference and https://console.groq.com/docs/models.
The active model is selected from the account's live available models and stored in private environment configuration.
