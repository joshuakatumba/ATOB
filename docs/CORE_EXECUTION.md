# Core execution — 2026-11-09

Owner authorised the ordered 30-task core implementation. Latest instruction: develop code; no Docker Compose runs or deployment. Preserve the React design, supplied template wording, environment-only credentials and whole-answer verification. Implemented does not mean release-accepted.

| # | Task | State / evidence |
|---|---|---|
| 1 | Verify server version/configuration | Verified read-only: AWS e8bca6e, live Groq/Laws.Africa settings, readiness OK. No server changes. |
| 2 | Precise private failure diagnostics | Implemented: stage/reason/duration/source count and allowlisted HTTP status; no prompts, answers or keys logged. |
| 3 | Reproduce dismissal/car-import questions | Reproduced. Direct dismissal check passed with 20B; direct car-import check passed with 120B. Earlier failures retained as evidence; browser acceptance incomplete. |
| 4 | Relevant Laws.Africa coverage | Uganda legislation and judgment collections connected. Portion type/canonical IDs retained. Preview completeness and use entitlement not established. |
| 5 | Follow-up/spelling-aware query preparation | Implemented schema-constrained keyword preparation from recent user facts; joined words/spelling handled by configured model. |
| 6 | Relevant source selection/deduplication | Implemented original contiguous query-focused excerpts, lifecycle/jurisdiction/link filters, collection interleaving, deduplication and context cap. |
| 7 | Context/token budget | Implemented query output cap, configured completion cap and optional reasoning effort. Local model now 120B/low, 2048 completion tokens. Provider capacity remains a limit. |
| 8 | Supported generation | Implemented strict structured output and passage IDs. Server copies literal evidence; no unsupported answer fallback. Limited live passes are not an accuracy benchmark. |
| 9 | Model suitability | Controlled 20B/120B checks performed; local configuration selects 120B. Model remains environment-configured; independent comparative quality not scored. |
| 10 | Whole-answer verification | Implemented; every segment must pass evidence checks and separate verification before any answer delta. Mixed-support regression passes. |
| 11 | Insufficient-evidence response | Existing Response unavailable retained. Owner has no approved alternative wording; no legal notice authored. |
| 12 | Provider limits/cancellation | One bounded short-429 retry, timeout, cancellation/refund path. Frontend now aborts on unmount; latest frontend cancellation not browser-verified. |
| 13 | Atomic quota/refunds | Existing ledger/auth/ownership/refund integration checks pass; no ledger/schema change. |
| 14 | Citation delivery/reload | Implemented and fake-source persistence/ownership verified. Live browser attempt failed verification/upstream, so real browser acceptance remains open. |
| 15 | Failed response/duplicate handling | Existing failed-history rendering retained; synchronous send/auth guards added. External browser harness selectors repaired; final rerun deliberately deferred. |
| 16 | Conversation memory/isolation | Existing persisted bounded per-conversation history retained; ownership/memory checks pass. No cross-chat memory. |
| 17 | Ground legal Drafting follow-ups | Implemented: chat in either mode uses retrieval when configured; prefill and template wording remain separate. Passage/routing/refund integration checks include Drafting. |
| 18 | Approved template discovery | 62 supplied templates unchanged. Search/category/Show all exercised in browser; fixture seeding now safely skips owner-first slug collisions. |
| 19 | Template selection/prefill | Existing approved-catalog selection/literal facts/ambiguity handling retained; focused integration checks pass. Live checks require explicit opt-in. |
| 20 | Encrypted drafts/autosave | Existing version-pinned encrypted autosave, revision conflicts and edit invalidation retained; focused integration checks pass. |
| 21 | Preview/Word/private document flow | All-62 preview/Word equivalence and private ownership checks pass. Browser reached successful generation; final download harness selector corrected, rerun pending. |
| 22 | Account/session/reset/verification | Implemented recovery/verification screens and provider callback routing; reset single-use and invalid verification tests pass. Tokens removed from URL; callback logs/referrers suppressed. Latest UI edits need browser acceptance. |
| 23 | Privacy/ownership | Existing isolation/redaction tests retained; diagnostics allowlist tested. Recovery tokens never stored in browser storage. Recent cancellation/token UI changes statically checked only. |
| 24 | Safety routing | Implemented structured urgent/unsafe/unsupported holds with no answer delta and refund. Fake routing checks pass. Approved emergency wording/contacts and independent safety review absent. |
| 25 | Current-stack CI | Removed obsolete Next/frontend commands, pinned external Playwright QA, non-mutating component inventory, isolated test settings and opt-in live checks. Remote CI not run. |
| 26 | Separate retrieval/generation evaluations | Both runners implemented; generation separates oracle/retrieved context and reports support/citations/relevance/correctness/abstention. Arithmetic tests pass; owner has no reviewed dataset, so real scores remain unavailable. |
| 27 | Full browser acceptance | Partial: recovery entry, signup, catalog/search/category/paging/form/preview/generation exercised. Harness fixes made. Full final browser run not passed; owner requested code-first work. |
| 28 | Concurrent reliability/limits | Measured 16 simultaneous streams/8 accounts with FAKE model and real auth/Postgres/Redis: 16 completed, 0 errors, p50 2165 ms, p95 2182 ms. Not a 100-user hosted-model capacity claim. |
| 29 | AWS flow/build reuse | Deferred by latest owner instruction: stop deployment and Docker Compose work. Read-only server inspection only; existing MinIO Dockerfile edit left untouched. |
| 30 | Acceptance/docs/commits | Current implementation/evidence recorded here, STATUS.md and KNOWN_ISSUES.md. No release-readiness or all-30-accepted claim. |
