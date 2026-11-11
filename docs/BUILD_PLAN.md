> Current owner scope (2026-11-07): integrate the supplied React 18/plain JSX/Vite UI with existing FastAPI/SuperTokens services. Preserve markup, copy and CSS. The earlier Next.js rebuild and milestone ordering below are historical; current scope and evidence are tracked in STATUS.md.

## Current integration acceptance

Backend routes and React server seams pass local integration acceptance.
Passed: twenty-way quota race, Vite build, API/web Docker builds, Python compile,
reversible migration and unchanged CSS/dependencies.
The reopened UUID/Word/static-check blockers are resolved. API smoke, browser flow and complete startup pass.
Remote integration CI and production acceptance remain pending. STATUS.md is the continuation record.
The historical milestones below remain future product/release goals, not this task’s scope.


# Build plan

Do not start a milestone until the previous one's acceptance criteria pass in CI.

## M0 — Spikes (nothing ships)
Prove the risky assumptions first. Output is a short report in docs/spikes/.
- S1: Stream a model response through the chosen host and CDN to a browser. Pass if tokens arrive incrementally, a 5 minute stream survives, and client disconnect cancels the upstream call.
- S2: Auth service: signup, verify, login, reset, session check from FastAPI and Next.js. Confirm current licence terms in writing in the report.
- S3: pgvector available on the chosen managed Postgres. Record version and filtered-search behaviour.
- S4: Embedding benchmark harness running against a small advocate-supplied set.
- S5: Payment provider sandbox: create a checkout and receive a signed webhook.
- S6: Nearest host region and measured latency from Kampala.
- S7: Malware scanning and direct-to-storage signed uploads available on the chosen host.
If any spike fails, stop and report. Do not proceed with a workaround.

## M1 — Foundations
Repo, CI, containers, migrations, auth integration, GET and PATCH /me, consents, quota ledger, rate limiting, health checks, structured logging with redaction.
Accept: ownership tests pass; quota race test passes; migrations reversible; unverified users get zero prompts.

## M2 — Chat without retrieval
Next.js app with landing, auth screens, sidebar, chat, streaming, conversation CRUD, stop, feedback, error states, dark mode, PWA shell. Model integration behind the provider interface with Research and Drafting prompts.
Accept: every M2 row of FEATURE_MAP works against the API; stream cancel works; incomplete messages persist; no localStorage auth code exists.

## M3 — Retrieval and verified citations (hosted D9/D10 approved 2026-11-09)
Owner approved Laws.Africa hosted Uganda Knowledge Bases instead of local ingestion, embeddings, hybrid search and reranking. Implement structured answers, verification, abstention, trace logging, eval runners and the advocate golden set. Hosted access is not a release-quality gate pass.
Accept: retrieval recall at 20 meets the owner's threshold; zero fabricated authority on the safety set; abstention works on out-of-corpus questions.

## M4 — Drafting
Template import command, template API, server rendering for HTML and Word, documents with storage and signed downloads, prefill endpoint, preview debounce.
Accept: only approved template versions are served; preview and Word text are identical; hostile field values cannot alter the document structure; prefill never invents values.

## M4b — Document uploads (blocked until M3 passes and D14 to D17 are set)
Direct-to-storage upload, scanning, extraction, quality gates, page store, attach to chat, verified page citations, source viewer, delete and purge.
Accept: isolation and purge tests pass; every citation quote exists on its cited page; hidden-text and injection tests pass; unsupported and corrupted files fail cleanly without consuming prompts; the cost test passes; advocates sign off on a sample of reviews.

## M5 — Billing, support, legal
Plans, checkout, webhooks, entitlements, feedback, legal pages and consent, delete account and export jobs.
Accept: duplicate and forged webhooks handled; subscription expiry returns the account to the free tier; deletion removes personal data from every table, storage and queues within the agreed window.

## M6 — Hardening and launch readiness
Load test, external penetration test, backup restore drill, alerting, cost alerts, runbooks, staging soak with 50 to 100 beta users.
Accept: restore from backup proven; load test passes; no critical or high findings open; advocate sign-off on a sampled set of real beta answers.
