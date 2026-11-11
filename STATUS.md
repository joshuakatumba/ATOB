# Civis status

## Phase 1 & Phase 2 commercial product-readiness complete — 2026-11-09

- Completed all 15 tasks across Phase 1 (Tasks 1–9) and Phase 2 (Tasks 10–15):
  - **Generated documents:** Owner-scoped `GET /v1/documents`, `DELETE /v1/documents/{id}` (clears draft/message references and deletes S3 object), `docx` generation idempotency across `draft_revision` retries, and `cleanup_retention_job` in `apps/worker/civis_worker.py`.
  - **Chat interface:** Stop button (`■`), message thumbs feedback (`👍`/`👎`), conversation rename/delete (`⋯`), cursor pagination (`Load more chats`), conversation JSON export, and mode-switch stream cancellation.
  - **Privacy & data lifecycle:** `GET /v1/me/export` and `DELETE /v1/me` (row-locked deletion, S3 object cleanup for documents and uploads, soft-delete user/conversations, and SuperTokens `revoke_all_sessions_for_user`), wired into the account menu.
  - **Quota & abuse controls:** Client `request_id` idempotency on chat and drafting prefill, `GLOBAL_HOURLY_MODEL_REQUESTS` circuit-breaker, `TRUSTED_PROXY_HOPS` `X-Forwarded-For` parsing, and per-user rate limits on `docx` rendering and feedback.
  - **Templates & support:** Cross-field ISO date validation (`d2 >= d1`), non-blank field check in UI before generating, and optional SMTP support ticket delivery (`SUPPORT_EMAIL`).
  - **Accounts & multi-tab sync:** Cross-tab logout synchronization via `BroadcastChannel("civis-auth")`.
  - **Research AI & Legal source coverage:** Statute/section/case-name preservation in search preparation, date/conflict rules in grounded generation, and `GET /v1/sources/coverage` manifest (`content/corpus/laws-africa-uganda.json`) with zero local passage caching.
  - **Safety & verified Uganda contacts:** `apps/api/civis/safety.py` and `content/owner-supplied/safety.json` (`GET /v1/safety/contacts`) enforcing emergency referrals (`999`/`112`, Sauti `116`, Justice Centres `0800 100 210`, FIDA `0800 111 511`, ULS Legal Aid `+256 414 342 424`), English-only notice for Luganda/Swahili input, Uganda-jurisdiction boundaries, and adversarial injection blocking with automatic quota refund.
  - **Commercial Legal Pages:** `content/owner-supplied/legal.json` (`is_fake: false`) serving Uganda DPPA 2019 Privacy Policy and Terms & Conditions with versioned consent acceptance (`POST /v1/me/consents`).
  - **Commercial UGX Payments:** `apps/api/civis/billing.py` and migration `0007_uploads_and_billing.py` providing `Starter` (`UGX 25,000` / 50 prompts), `Pro` (`UGX 75,000` / 200 prompts), and `Chambers` (`UGX 250,000` / 1,000 prompts) plans, Flutterwave Mobile Money & Card checkout (`POST /v1/billing/checkout`), HMAC-verified webhooks (`POST /v1/billing/webhook/flutterwave`), idempotent prompt grants, and chargeback reversals.
  - **Document Uploads:** `apps/api/civis/uploads.py` (`POST /v1/uploads`, `GET /v1/uploads`, `DELETE /v1/uploads/{id}`) with ClamAV + structural/EICAR/macro malware scanning, PDF/DOCX page extraction, AES-GCM encryption at rest, sensitive NIN/ID/bank warnings, 1-prompt (`<= 15` pages) / 2-prompt (`16..30` pages) quota rule, `[Page N]` chat citations, and 30-day retention cleanup.
  - **Live Evaluation Runner:** `scripts/run_live_eval.py` paired with `evals/retrieval.py` and `evals/generation.py`.
- **Verification:**
  - PASS: `ruff`, `mypy --strict`, `pyrefly check`, `feature_coverage.py` (19 React modules), and `vite build`.
  - PASS: 86 pytest checks (3 optional paid live provider tests skipped by default), including `test_commercial_features.py`, `test_document_library.py`, and `test_drafting.py`.
  - PASS: `scripts/smoke_research_failure.mjs`, `scripts/smoke_core.mjs`, and live `scripts/smoke_research.mjs`.

## Core implementation continuation — 2026-11-09

Latest owner direction: **code first; stop Docker Compose runs and deployment**. No server changes made.
The ordered task register and exact remaining acceptance gaps are in [docs/CORE_EXECUTION.md](docs/CORE_EXECUTION.md).

- Added strict Groq structured generation, focused search query preparation, original passage references, whole-answer verification and safe failure-stage/HTTP diagnostics. Drafting chat follow-ups now use the same grounding path.
- Direct live dismissal check passed with two citations (20B); direct live car-import check passed with two citations (120B). Private local model now selects 120B/low reasoning and 2048 completion tokens. No model/key is hard-coded in application logic.
- Research browser acceptance remains open: one attempt failed upstream during verification. Earlier direct checks also withheld answers; no broad legal-accuracy claim is made.
- Added account recovery/verification screens, provider callback routing, single-use reset checks, token/referrer protection, duplicate-submit guards and request cancellation on leaving the app. Existing JSX design/CSS/template wording remain intact.
- Retained quota, memory, encrypted autosave and private document flows. Fixed test-seed collision when approved owner templates were imported first.
- Repaired CI commands for React/Vite; isolated test settings from private live defaults and made paid live tests explicit opt-in. Added separate generation-review scoring alongside retrieval scoring.
- Verification: API lint/typecheck pass; migration up/down/up passed. Full run: 78 passed, 2 skipped, one optional live-prefill failure; that check is now opt-in. Focused final drafting/concurrency run: 5 passed, 1 skipped. Generation scorer: 3 passed. Latest small metadata/cancellation/recovery changes pass lint/typecheck and the Vite production build; runtime acceptance remains pending.
- Measured fixture-provider concurrency: 16 streams across 8 real-auth accounts, 0 errors, p50 2165 ms/p95 2182 ms. This does not measure Groq peak capacity.
- Browser reached approved-template generation; QA harness had missing-title/selector errors, now corrected but final rerun deferred. No passing complete browser or remote CI result claimed.
- Owner has no approved routing text, verified contacts or advocate labels. Existing availability response remains; urgent/unsafe/unsupported routes withhold and refund. No legal text/contacts/gold labels invented.
- AWS read-only check found e8bca6e and healthy live configuration. Existing remote MinIO Dockerfile edit was preserved. Deployment remains stopped.

Earlier entries below are historical snapshots; this entry supersedes their current-state statements.

## User-facing test-response leak fixed — 2026-11-09

- Owner reported deployed UI showing a canned diagnostic reply during a presentation. Root cause: dev_env.py still selected the test provider/seed, and provider selection silently fell back to canned replies without keys.
- Normal defaults now select Groq and hosted Uganda retrieval, disable fixture flags, and no longer run sample seeding. CI opts into isolated fixtures explicitly.
- Removed automatic canned-provider fallback. Explicit test providers require ENABLE_TEST_FIXTURES=true; normal startup preflight rejects fixture/catalog settings.
- Normal history/model context excludes prior diagnostic assistant replies without deleting records; normal catalog excludes fixture versions even if an old unapproved-template flag remains set.
- Supplied owner-approved 62-template content is unchanged. Owner confirmed legitimacy/counsel approval; docs corrected. No UI/CSS/dependency/schema changes.
- Added scripts/configure_live.py: private masked key setup, live flags, duplicate live-setting cleanup, atomic 0600 .env write, existing database/storage credentials retained.
- PASS: 15 tests covering defaults, no silent fallback, explicit test isolation, config credential preservation, real-auth live history/catalog isolation, legal isolation, production guard and chat/quota/document flows.
- PASS: lint, strict API typecheck, API/worker builds, local live preflight and readiness. Local private configuration switched to fixture-free real services.
- Server remains separately configured: fetch integrate/civis-ui-api, run sudo python3 scripts/configure_live.py, then sudo ./scripts/dev.sh. No remote AWS access or server fix is claimed.
- Real Research verification remains the separate unresolved acceptance issue; removing sample replies does not establish a passing grounded answer.


## Whole-answer decision and evidence-first generation — 2026-11-09

- Owner explicitly chose “Withhold the whole answer”; partial supported paragraphs are never released.
- Added versioned v2 generation/verification prompts: one concise paragraph, literal evidence excerpts for every cited source, and explicit verifier indexes.
- Evidence IDs must match cited source IDs, excerpts must be nonblank literal substrings, and the separate whole-answer support gate is unchanged.
- PASS: 14 Research tests plus five retrieval metric checks, lint, strict API typecheck and API/worker builds. No UI/dependency/schema changes in this slice.
- The one-of-three supported-paragraph regression confirms zero answer text/citations are released and quota is refunded.
- Live dismissal-question browser check still returned an error after this generation fix. Do not claim a passing real answer, legal accuracy or production readiness; no further prompt-fix loop performed.
- Next unresolved work: identify the current failing generation/evidence/verification stage with safe metadata, improve supported generation without relaxing withholding, and pass the real answer/citation/reload check.


## Owner screenshot fix — 2026-11-09

- Reproduced dismissal question: Laws.Africa retrieval 200 and valid Groq generation, followed by verification 429 with Retry-After: 2.
- Groq rate-limit responses now carry a sanitized typed delay. Research retries once only for delays <=15 seconds before any model output; repeated/long limits emit rate_limited with retry_after and refund before a delta.
- Preserved message status in React; empty streaming placeholders are hidden and incomplete empty responses render the existing availability text. No CSS/dependency changes.
- PASS: 16 API tests (12 Research plus four chat checks), strict typecheck, lint, Vite/container builds and browser FAKE-history failure/reload/streaming-placeholder regression. No schema change.
- Readiness wait now tolerates a connection reset during container startup. QA auth bucket expired normally; no limits weakened or Redis cleared.
- Live browser still returned an error. Subsequent sanitized diagnosis: retrieval and both model calls returned 200; generator returned three paragraphs; verifier accepted only index 1. Existing all-or-nothing policy therefore withheld the answer.
- Owner subsequently confirmed whole-answer withholding; no partial-answer behavior is enabled.
- Continue under strict whole-answer withholding; do not redo template/chat integration or weaken individual source checks. Research release/advocate accuracy acceptance and CI remain unverified.

## Hosted Research implementation — 2026-11-09 (acceptance incomplete)

- Owner approved Laws.Africa hosted Uganda Knowledge Bases, replacing local index/embedding selection; D9/D10 and relevant docs updated.
- Implemented Research retrieval with Uganda/link/date/lifecycle filtering, bounded source context and follow-up user context.
- Implemented schema-validated segments, retrieved-ID/literal-quote checks and a separate model support check before any answer delta.
- Added migration 0006 for owned message citation metadata; React renders source links/dates and restores citations from history. CSS/dependencies unchanged.
- PASS: 13 chat/ownership/refund/disconnect/limit tests; subsequently seven focused research checks including fake-source integration, ownership, quote rejection and retrieval filters.
- PASS: lint, strict API typecheck, Vite build, API/web/worker container builds and migration 0006 up/down/up on disposable Postgres. Local readiness ok.
- Live Laws.Africa retrieval returned six Uganda passages. Groq returned 429 during real grounding tests (account header: 8000 tokens/minute).
- One context-budget fix: default source context reduced to 12000 chars, local output capped at 1024 tokens, verifier supplied only cited sources. Live generation still failed closed after this fix; no further model-fix loop performed.
- Live browser acceptance remains incomplete: initial readiness race fixed, then streaming-body QA issue fixed; final source-link/reload check has not passed. scripts/smoke_research.mjs preserves the failing acceptance harness.
- Do not claim research ready, legal accuracy or remote CI passed. No unsupported answer was accepted as a success. Existing template/chat milestones are not redone.
- Local RETRIEVAL_PROVIDER=laws_africa is enabled for testing and fails closed on research errors; other machines are unchanged. Default sample flag is disabled until explicitly configured.
- Next: diagnose the recorded live generation/check failure in a newly authorised fix cycle, verify a real answer/citation reload, and obtain advocate relevance/accuracy labels, production entitlements and approved safety/abstention wording.


## Laws.Africa access verified — 2026-11-09

- Owner proposed Laws.Africa and supplied a key, stored only in ignored private .env (LAWS_AFRICA_API_KEY).
- Live collection list and both Uganda metadata/retrieve calls returned HTTP 200: legislation-ug and judgments-ug.
- Both collections are labelled preview; sample results include source URLs/dates; judgment sample consists of summaries.
- Proposed hosted Knowledge Bases -> Groq -> citation/claim verification path documented in docs/LAWS_AFRICA.md.
- Owner subsequently approved hosted retrieval; the implementation/acceptance result is recorded above.
- Hosted Research is now enabled locally for testing; complete coverage, accuracy and production entitlement are not claimed.
- Remaining: live grounding acceptance and advocate relevance/answer evaluation.


## Research continuation — 2026-11-09

- Added retrieval evaluation runner in evals/retrieval.py: Recall@K, MRR@K, MAP@K, nDCG@K and query coverage.
- Separates retrieval from generation; missing runs score zero, FAKE fixtures never contribute to legal-quality reports.
- PASS: five arithmetic/input/aggregation checks, lint and strict typecheck; included in default pytest discovery.
- No app, UI, dependencies, database schema or prompt changes in this slice.
- Required input remains D9 approved corpus/access and D10 advocate query/source labels. content/corpus is empty.
- Asked owner for these inputs; no embedding choice, scraper, ingestion or source-backed answer claim was substituted.
- ULII terms fetch returned 403; no bulk/API permission assumed. See evals/README.md for runner contract and inputs.
- Continue with approved source ingestion/retrieval after those inputs; existing completed drafting/chat work stays intact.

## Immediate core testing — 2026-11-09

Owner prioritised a small testable core, approved the existing Civis.jsx templates for testing,
and authorised Groq with environment-only credentials. See [docs/CORE_TESTING.md](docs/CORE_TESTING.md).
- Groq streaming adapter implemented with existing httpx; provider/model/key remain environment settings.
- The configured model was verified against the account's available models. No key is committed or printed.
- 62 original templates imported unchanged with the owner's testing approval; import is idempotent.
- New drafts no longer hide the latest approved template version. FAKE fixtures remain separate.
- Chat history is persisted per owner/conversation; each request uses up to 60 completed non-file messages,
  limited by LLM_HISTORY_MAX_CHARS (default 24000). Older history remains in Postgres; no cross-chat memory/summarisation.
- Unfinished forms now autosave encrypted values per owner/conversation, pin template versions and reject stale saves.
- Natural-language Drafting selects approved templates and prefills literal stated facts; missing facts stay blank.
- Editing clears the active generated-file reference; earlier documents remain immutable in chat history.
- PASS: ten targeted API tests across drafting, chat memory, quota/refunds, ownership, generation and all-template text equivalence; additional live Groq prefill verification passes.
- PASS: live HTTP flow through the web proxy: signup, Groq stream, recall, history reload, quota, owner template
  preview/generate/reopen/download and logout. Readiness ok; frontend HTTP 200; all nine services running locally.
- PASS: lint, strict backend typecheck and API/web/worker container builds. No CSS/frontend dependency changes.
- PASS: browser live Groq prefill, literal facts/missing fields, edit/reload, generate/download, edit invalidation and regenerate; no browser errors/auth storage. Reproducible external-QA harness: scripts/smoke_drafting.mjs.
- PASS: migration 0005 down to 0004/up on disposable Postgres; encrypted drafts added through Alembic.
- Corrected a duplicate placeholder GROQ_API_KEY in private local .env that had overridden the verified key in Docker.
- Remaining core gap: verified legal RAG/citations and source-backed answer evaluation; uploads remain disabled.
- Run ./scripts/dev.sh on the updated branch to apply migration/import/build on another machine. No remote CI or AWS verification is claimed.
- AWS instance environment is not changed by local code/config updates; it needs the updated branch and its own private Groq settings.

## Product-readiness audit — 2026-11-09

The owner requested the full product task list, excluding deployment. See
[docs/PRODUCT_READINESS.md](docs/PRODUCT_READINESS.md): 188 open acceptance tasks across
research, source management, evaluation, approved drafting, uploads, accounts, customer flows,
quota, payments, privacy, support and product quality. This is a code/spec audit, not a new
implementation or test pass. Earlier fake-data integration results remain valid within their scope.
Current CI still references removed frontend scripts; real legal RAG and approved-content release
acceptance are incomplete. This register does not authorize a UI redesign or decide unresolved D9-D17 inputs.

## Active scope
Integrate the supplied React UI with the existing backend, preserving CSS, markup and copy.
The owner’s latest integration request supersedes the earlier port-only stop and Next.js milestone gates.

## Completed input
- M1 foundations: commit 7f57faf; CI 42384631605 passed 18 tests.
- M2 streaming backend: commit 2705de7; real auth, quota and conversation routes are reused.
- React 18/plain JSX/Vite component port: commit 18b6928. Root Civis.jsx is the owner reference.
- Read-only code inspection and ten-line NOTES.md completed. No new frontend dependencies authorized.

## Implemented and locally verified
Branch: integrate/civis-ui-api; two local integration commits (backend then frontend). Backend catalog, server documents and feedback storage are added.
React cookie auth, SSE, persisted chats, server quota and template flows now call the backend.
Delivery: one backend commit, one frontend commit; one-command startup; README and .env.example.

## Verification
- PASS: backend lint and strict typecheck; full API integration smoke; twenty-way quota race (exactly five spends).
- PASS: browser signup/login/logout; streaming chat/server counter; chat reload persistence.
- PASS: template category/search/Show all/form/escaped preview/generate/Word download; document reload.
- PASS: dark mode persistence and sidebar collapse; no JavaScript errors or browser auth storage.
- PASS: one-command ./scripts/dev.sh startup, API readiness, API/web Docker builds and Vite production build.
- PASS: migration 0004 up/down/up on disposable Postgres; CSS and frontend dependency files unchanged from 18b6928.
- Not run: remote integration CI, live Anthropic, physical microphone, production deployment/external telemetry.
API smoke used real Postgres, Redis, SuperTokens and private S3 with the labelled fake model.

## Fixes completed in the owner-requested follow-up
Strict UUID parsing now accepts JSON UUID strings only on optional conversation_id fields;
all other strict validation remains. Word XML is passed as a single payload to the archive writer.
Long XML strings are split without changing their contents. The previously failing checks now pass.

## Continuation
Local integration acceptance is complete for the active scope; no production readiness is claimed.
Run ./scripts/dev.sh and open http://localhost:53000. Services are currently running.
Keep the two integration commits on integrate/civis-ui-api; no remote push or CI result is claimed.
Do not redo foundations, redesign the UI, change CSS or add frontend dependencies.

## Deferred
Stop button, thumbs, citations UI, email verification/reset screens, chat/account deletion, export,
uploads, payments, real legal content/corpus and production release approval.

## Approved decisions
Ledger uniqueness is per (request_id, kind), refunds linked to spend.
M1 preceded M2 by owner approval; the active frontend is React/Vite rather than Next.js.

Container verification: docker compose build api web passed for both API and web images.
