> Historical broad audit. Current core implementation and acceptance are tracked in CORE_EXECUTION.md and STATUS.md; statements below about absent retrieval/evaluation/CI predate those implementations. Unchecked items are not automatically accepted.

# Civis complete product-readiness task register

Audited 2026-11-09 against current code, STATUS.md, KNOWN_ISSUES.md and the product specifications.
Scope: all documented product capabilities and reliability work. AWS deployment, VM sizing,
DNS/TLS setup, server provisioning and infrastructure operations are intentionally excluded.
The original audit was read-only; the testing-slice updates below record subsequent implementation and local checks.

There are **188 acceptance tasks** in this register: 8 completed for the local testing scope, 180 open. An open task may complete or verify
an existing foundation; it does not mean the entire subsystem is absent. Counts are not an
estimate of effort or a percentage-complete score. [OWNER] means an owner/advocate/provider input
is required; the agent must not fabricate legal content, access rights or acceptance thresholds.

The basic account/chat/history/quota/template-render/download flows have passed earlier local
fake-data integration checks. Reuse those foundations. A fake-data pass is not evidence of real
legal research/drafting quality. Implementation tasks below are proposed work, not permission to
redesign the frozen JSX, add arbitrary dependencies or bypass content approval.

Payments are a release dependency if charging; upload analysis is a release dependency if offered.
Hosted retrieval versus a local index is unresolved: do not build both by default. Choosing hosted
retrieval would require an explicit update to the existing local-index specification.

## Testing slice completed after this audit

On 2026-11-09 the owner approved the original templates for testing and authorised Groq.
Real Groq streaming/recall, 62 unchanged template imports and bounded conversation context now pass
local checks. Approved-version selection was corrected. See CORE_TESTING.md and STATUS.md.
Approved-template prefill and encrypted unfinished-form autosave now pass local API/live Groq/browser checks.
Version pinning and stale generated-file links are fixed. Eight implemented tasks are checked below;
these local results do not close source-verified RAG, privacy/customer lifecycle or complete release acceptance.

## Code evidence and concrete gaps

- `apps/api/civis/chat.py`: calls the provider without retrieval and emits an empty citations list.
- `apps/api/civis/templates.py`: now imports the 62 owner-approved testing templates; approved-version selection is corrected. The UI pins the selected version through draft saves and generation.
- `apps/web/src/components/Shell.jsx`: server-backed draft autosave/reload and edit invalidation now pass; broad multi-tab/concurrency acceptance remains open.
- `apps/api/civis/templates.py` field validation currently checks field keys and length; typed/required/cross-field rules are not implemented.
- `apps/worker/civis_worker.py`: only health_job exists; no ingestion, extraction, purge, export, reconciliation or support-delivery jobs.
- `.github/workflows/m1.yml` still invokes frontend scripts absent from `apps/web/package.json`.
- `evals/` has no tracked evaluation runner/golden dataset in the inspected file inventory; current safety tests cover configuration/log redaction, not the full legal behavior suite.
- Current legal route requires authentication while the older API table says public; signup/legal-access behavior needs an explicit resolution before implementation.
- This workspace contains an untracked SSH-key filename and nested checkout; no private key contents were read. Never stage these with product work.

## DEC — Product and owner decisions

Current state: Owner decisions; do not silently adopt defaults.

- [ ] DEC-01 [OWNER] Confirm release scope: research, approved drafting, uploaded-document analysis and paid plans; mark any unshipped capability unavailable.
- [ ] DEC-02 [OWNER] Confirm corpus sources/access rights (D9), provider collection coverage, attribution, storage/caching permissions and update access.
- [ ] DEC-03 [OWNER] Choose hosted retrieval or a maintained local index from a common benchmark; choose embeddings/reranker only if required (D10).
- [ ] DEC-04 [OWNER] Approve answer-quality, retrieval, abstention, safety, latency and cost acceptance thresholds.
- [ ] DEC-05 [OWNER] Confirm free allowance, spending/refund rules, plan entitlements, prices and payment provider (D3-D7).
- [ ] DEC-06 [OWNER] Confirm supported languages and unsupported-language behavior (D11).
- [ ] DEC-07 [OWNER] Resolve retention, document transfer/processing, upload access/limits, exactly-15-page pricing and sensitive-document behavior (D12, D14-D17).
- [ ] DEC-08 [OWNER] Supply approved template wording, legal pages, consent/disclaimer/refusal/routing text, verified referral contacts and support destination (D13).

## COR — Legal corpus and coverage

Current state: Missing approved real corpus; source access is not yet connected.

- [ ] COR-01 Create a source manifest recording provider, collection, licence/permission, jurisdiction, formats and permitted uses.
- [ ] COR-02 Obtain approved legislation and judgment access; establish precisely whether results contain full text, summaries or both.
- [ ] COR-03 Inventory coverage by topic, court, date and document type; document known gaps rather than imply complete coverage.
- [ ] COR-04 Store canonical source identifiers, URLs, titles, citations, court, dates, language and provenance.
- [ ] COR-05 Preserve source originals and immutable source versions where permission allows; record hashes and retrieval dates.
- [ ] COR-06 Track legislation commencement, amendment, repeal and point-in-time applicability.
- [ ] COR-07 Track judgment court/authority and subsequent treatment only where verified; represent unknown treatment explicitly.
- [ ] COR-08 Handle duplicate versions, corrected judgments, withdrawn documents and provider removals.
- [ ] COR-09 Assign a corpus maintenance owner and implement scheduled updates/change review.
- [ ] COR-10 Quarantine missing, unlicensed, corrupt or low-quality sources; permit reproducible removal/reindexing.

## ING — Ingestion and indexing

Current state: Missing feature jobs and corpus/chunk tables.

- [ ] ING-01 Build an admin-triggered worker ingestion job or validated hosted-retrieval adapter, depending on DEC-03.
- [ ] ING-02 For local ingestion, parse legal structure, paragraph/page identifiers, headings, definitions and cross-references.
- [ ] ING-03 Preserve judgment reasoning and outcome structure; prevent extraction errors from silently becoming indexed evidence.
- [ ] ING-04 Chunk by structure with parent links; test the specified size range instead of relying only on fixed token splits.
- [ ] ING-05 If contextual chunk descriptions are used, version them and never treat generated descriptions as original legal evidence.
- [ ] ING-06 Create corpus/chunk metadata, full-text and vector storage through migrations if maintaining a local index.
- [ ] ING-07 Implement idempotent content-hash imports, bounded retries, failure states and a reviewable quarantine.
- [ ] ING-08 Version extraction/chunking/embedding configuration and apply required model-specific query/document formats.
- [ ] ING-09 Implement compatible index rebuilds/re-embedding and invalidation of removed or changed sources.
- [ ] ING-10 Check extraction completeness, OCR quality, encoding, tables and language; keep OCR disabled until accepted.

## RET — Retrieval and ranking

Current state: Not wired into chat; current chat returns no retrieved citations.

- [ ] RET-01 Classify request intent and resolve follow-up questions without inventing missing facts.
- [ ] RET-02 Implement exact lookup for named sources/citations before approximate retrieval.
- [ ] RET-03 Implement and compare keyword and semantic retrieval or the equivalent hosted API behavior.
- [ ] RET-04 Merge/rerank results and tune candidate/context limits using held-out data.
- [ ] RET-05 Apply Uganda, document-type, authority and relevant-date filters; use distinct legislation and case-status rules.
- [ ] RET-06 Expand relevant passages to needed parent sections, definitions and cross-references within a context budget.
- [ ] RET-07 Handle conflicting authorities and missing historical versions explicitly.
- [ ] RET-08 Tune evidence-sufficiency/abstention thresholds; provide a safe result when retrieval/provider access fails.
- [ ] RET-09 Version any retrieval caches and keep user-private results isolated; add caching only for a measured need.
- [ ] RET-10 Record source/passages, filters, rankings, scores and timings for reproducible evaluation without logging private text.

## GEN — Real model and answer generation

Current state: Provider adapter exists; real legal answering remains unverified.

- [ ] GEN-01 Run live Anthropic contract and full-flow tests with approved sources; retain environment-configured models.
- [ ] GEN-02 Validate structured answers containing claims/segments, supporting passage IDs and optional clarification requests.
- [ ] GEN-03 Build the prompt context from retrieved evidence, user facts and explicit provenance boundaries.
- [ ] GEN-04 Implement missing-fact clarification and refusal to invent personal facts, quotations or authorities.
- [ ] GEN-05 Version research/drafting prompts and validate context-window, history and output-token budgets.
- [ ] GEN-06 Test relevant conversation history selection, including exclusion of unrelated/generated file-card content.
- [ ] GEN-07 Handle provider timeouts, overload, malformed events, truncated output and refusal responses.
- [ ] GEN-08 Bound provider calls/retries and total generation time; prevent retries from producing duplicate messages or charges.
- [ ] GEN-09 Define the streaming contract for provisional versus verified content; never present removed/unverified claims as final.
- [ ] GEN-10 Persist final, incomplete, blocked and abstained outcomes coherently; make unavailable capabilities explicit.

## CIT — Citation verification and evidence display

Current state: Missing verifier, persistence and source UI.

- [ ] CIT-01 Create persistent citations linking each supported claim to retrieved passage IDs and source versions.
- [ ] CIT-02 Reject unknown, fabricated or non-retrieved source identifiers.
- [ ] CIT-03 Verify quotations against original passages with a documented normalization policy.
- [ ] CIT-04 Check case names, legislative references and section numbers against the supplied evidence.
- [ ] CIT-05 Validate claim support separately; calibrate automated checks against advocate review.
- [ ] CIT-06 Implement bounded correction/removal and final abstention when evidence is insufficient.
- [ ] CIT-07 Display citations, source excerpts, public links and applicable/source dates; restore them on conversation reload.
- [ ] CIT-08 Test missing/broken sources, conflicting evidence, unverifiable claims and verifier failure without allowing unsupported final output.

## SAF — Legal safety and answer behavior

Current state: Versioned prompts exist; full behavior is not implemented or evaluated.

- [ ] SAF-01 Implement and test jurisdiction, supported-language and out-of-scope routing.
- [ ] SAF-02 Implement urgent/high-risk routing using owner-approved text and verified contacts, without inventing details.
- [ ] SAF-03 Implement specified advocate-referral topics and configurable triggers.
- [ ] SAF-04 Implement refusal behavior for prohibited assistance using owner-approved policy/content.
- [ ] SAF-05 Test prompt injection in user messages, retrieved sources, uploaded text and metadata; enforce access outside model instructions.
- [ ] SAF-06 Display approved limitations/disclaimer text consistently for legal answers and document analysis.
- [ ] SAF-07 Test uncertain/conflicting law, missing facts, date-sensitive questions and unanswerable requests.
- [ ] SAF-08 Prevent claims of professional status, guaranteed outcomes or document approval beyond the accepted product scope.
- [ ] SAF-09 Ensure unsupported statements about case treatment, applicability or deadlines cannot bypass verification.
- [ ] SAF-10 Record policy outcomes without private text and create a review path for false refusals and missed unsafe responses.

## TPL — Template import, review and catalog

Current state: Catalog and fake seed exist; approved-content lifecycle is missing.

- [x] TPL-01 Build an owner-run import command for supplied real template definitions; an admin upload UI is optional, not required to import.
- [ ] TPL-02 Define supported source formats and editable-field mapping; preserve supplied wording and identify unsupported formatting.
- [ ] TPL-03 Expand field schemas to required/optional values, supported types, limits and cross-field rules.
- [ ] TPL-04 Validate imported bodies, placeholders, schema consistency and provenance before acceptance.
- [ ] TPL-05 Implement draft, review, approval, active-version selection, retirement and rollback with authorized reviewer records.
- [x] TPL-06 Fix approved-version selection so a newer draft does not hide the last approved version.
- [x] TPL-07 Pin the selected version from form loading through preview, prefill, generation and document reopening.
- [ ] TPL-08 Populate and advocate-review real templates/categories; never let Codex author or approve legal wording.
- [ ] TPL-09 Prevent examples from silently becoming user facts or final documents; explicitly handle unfilled required fields.
- [ ] TPL-10 Verify catalog search/category/count/pagination behavior on the real catalog, including the documented title/category search semantics.

## PRE — AI drafting selection and prefill

Current state: Approved-template selection, literal fact extraction, quota/refunds and frontend autosave are implemented and locally tested. Typed/cross-field validation and broader hostile-input evaluation remain open.

- [x] PRE-01 Implement POST /v1/drafting/prefill with validated request/response schemas.
- [x] PRE-02 Retrieve suitable approved template candidates from the real catalog.
- [x] PRE-03 Use structured extraction to map only stated user facts to allowed fields.
- [x] PRE-04 Return unknown values as null/placeholders; reject invented/unknown fields.
- [ ] PRE-05 Return missing-field information and request a user choice when selection confidence is insufficient.
- [ ] PRE-06 Validate dates, amounts, names and supported cross-field consistency rules.
- [x] PRE-07 Connect describe-the-document chat to selection/prefill and editable confirmation without unauthorized wording changes.
- [ ] PRE-08 Apply atomic quota/idempotency and test ambiguity, hallucination, failure/refund and hostile input behavior.

## DOC — Preview, generation and document lifecycle

Current state: Basic server HTML/OOXML generation and private downloads work locally.

- [ ] DOC-01 Validate real templates with required fields, date/amount types, Unicode and XML-forbidden/control characters.
- [ ] DOC-02 Generate preview and Word text from one pinned template/value snapshot and test equivalence.
- [ ] DOC-03 Confirm required Word formatting, numbering, tables, page breaks and signatures against each supported template; document unsupported layouts.
- [ ] DOC-04 Fix stale-file behavior after editing a generated document: show/regenerate the matching version rather than silently download the old snapshot.
- [ ] DOC-05 Test rapid field edits, stale preview responses, template updates and repeated Generate requests.
- [ ] DOC-06 Add generation idempotency and reconcile file writes with database commits; clean orphaned objects safely.
- [ ] DOC-07 Complete authenticated document list/delete APIs and the product controls needed to manage generated files.
- [ ] DOC-08 Implement approved expiry, deletion and retention jobs for records, objects and encrypted values.
- [ ] DOC-09 Handle expired sessions/links, unavailable objects and failed downloads through product error states.
- [ ] DOC-10 Validate encryption-key configuration/recovery expectations and test Word files in supported editors; keep filenames/content disposition safe.

## UPL — User document upload and analysis

Current state: Entire feature disabled; required before offering uploaded-document analysis.

- [ ] UPL-01 Resolve upload limits, entitlement, exact quota costs and retention before enabling FEATURE_UPLOADS.
- [ ] UPL-02 Build authenticated signed upload creation/completion/status/list/page/delete routes.
- [ ] UPL-03 Enforce size, count and storage limits plus owned upload keys and signed URL constraints.
- [ ] UPL-04 Validate actual type, archive expansion limits, encryption/corruption and unsupported/macro-enabled files.
- [ ] UPL-05 Implement malware scanning and fail closed when scanning is unavailable.
- [ ] UPL-06 Implement uploaded/scanning/extracting/ready/failed/rejected states with reason codes and idempotent jobs.
- [ ] UPL-07 Extract PDF/DOCX text, pages, clauses and tables, with quality/language/hidden-text checks.
- [ ] UPL-08 Store private originals and extracted page text; deduplicate within one user only.
- [ ] UPL-09 Enforce token budgets; use whole-document context or private retrieval without silent truncation.
- [ ] UPL-10 Isolate private chunks, searches and any caches by owner; never add uploads to the public legal corpus.
- [ ] UPL-11 Implement attachment selection, upload progress, status, list, delete and source-viewer UI.
- [ ] UPL-12 Implement grounded summaries, key-term extraction and document questions with claim/page references.
- [ ] UPL-13 Verify every quoted excerpt and distinguish uploaded evidence from public legal sources.
- [ ] UPL-14 Apply approved sensitive-document warnings, limitations and referral behavior.
- [ ] UPL-15 Implement expiry/deletion/account-purge cascades and prove original/text/chunk/vector removal.
- [ ] UPL-16 Test isolation, zip bombs, corruption, hidden instructions, failures/refunds and maximum-size cost; keep OCR off until its separate benchmark passes.

## ACC — Accounts, sessions and consent

Current state: Provider auth works; complete customer recovery/verification flows are missing.

- [ ] ACC-01 Add provider-owned email verification screens, resend/status handling and verified-only allowance behavior.
- [ ] ACC-02 Add provider-owned password-reset request/completion screens and expired/used-token handling.
- [ ] ACC-03 Exercise real transactional email delivery, provider links and account recovery end to end.
- [ ] ACC-04 Complete versioned legal consent capture before account use and handle approved document updates.
- [ ] ACC-05 Reconcile pre-signup access to legal text: current authenticated endpoint conflicts with the older public API row; owner must decide.
- [ ] ACC-06 Ensure generic authentication errors, password policy alignment and duplicate-submit protection.
- [ ] ACC-07 Test session expiry/refresh races, revoked sessions, logout during work and multiple tabs.
- [ ] ACC-08 Test CSRF, cookie and origin protections against authenticated state-changing endpoints.
- [ ] ACC-09 Enforce disabled/deleted-account access restrictions and revoke provider sessions during deletion.
- [ ] ACC-10 Ensure frontend API outages are distinguished from unauthenticated state; retain safe no-browser-credential storage behavior.

## CHAT — Conversation and frontend completeness

Current state: Basic flows pass locally; several specified controls and state cases are missing.

- [ ] CHAT-01 Add stop-generation control using cancellation; preserve correct incomplete state and refund behavior.
- [ ] CHAT-02 Add stored citation/source display and useful verified-answer formatting without interpreting arbitrary model HTML.
- [ ] CHAT-03 Connect existing per-message feedback API to thumbs/review interactions.
- [ ] CHAT-04 Add conversation rename/delete controls and their retention behavior.
- [ ] CHAT-05 Persist selected template/unsubmitted drafting state according to an explicit product decision; current selection is browser state.
- [ ] CHAT-06 Fix research/drafting mode races when creating or loading conversations.
- [ ] CHAT-07 Prevent stale chat loads, cross-chat stream completion and pending responses from changing the wrong active conversation.
- [ ] CHAT-08 Keep history genuinely paged, prevent duplicate empty conversations and handle large/long histories.
- [ ] CHAT-09 Cover loading, empty, offline, failure, incomplete, verification-required, rate-limit and quota-exhausted states; preserve unsent text on failure.
- [ ] CHAT-10 Check keyboard/mobile/accessibility, long answers, auto-scroll, reconnects and unsupported browser voice/install behavior; only advertise PWA install if implemented.

## QUO — Quota, rate limits and abuse controls

Current state: Atomic ledger and races pass; all new model-consuming paths still need integration.

- [ ] QUO-01 Confirm displayed allowance/plan labels come from server entitlements, including future paid plans.
- [ ] QUO-02 Extend spending/refunds to prefill and document analysis while keeping render/download free as approved.
- [ ] QUO-03 Add request idempotency across client retries/reconnects; existing server-generated message IDs do not prevent duplicate submissions.
- [ ] QUO-04 Test concurrent tabs, duplicate requests, cancellation, pre/post-first-token failure and account ownership for every spending path.
- [ ] QUO-05 Implement specified per-user feedback and upload limits in addition to general IP/message limits.
- [ ] QUO-06 Test proxy/client identity handling so distinct customers do not accidentally share a single proxy-IP auth limit.
- [ ] QUO-07 Implement bounded provider/conversation concurrency and accurate recovery of leases after worker/API failures.
- [ ] QUO-08 Apply model-output/input limits and account/global spend protection without bypassing the ledger.
- [ ] QUO-09 Validate allowance changes, grants, refunds and paid entitlement expiry with auditable reconciliation.

## PAY — Subscriptions and payments

Current state: Missing; required before charging for paid plans, not for an unpaid release.

- [ ] PAY-01 [OWNER] Finalize UGX plans, allowances, duration, payment provider and support/refund rules.
- [ ] PAY-02 Implement plan listing, checkout creation and server-side plan selection/validation.
- [ ] PAY-03 Integrate provider sandbox transactions for the intended payment methods.
- [ ] PAY-04 Implement authenticated subscription status and real Subscribe/Upgrade/confirmation states.
- [ ] PAY-05 Verify webhook signatures and limit/validate public webhook bodies.
- [ ] PAY-06 Handle duplicate, delayed, replayed and out-of-order payment events idempotently.
- [ ] PAY-07 Grant entitlements atomically only after verified payment; never trust a browser success redirect.
- [ ] PAY-08 Implement entitlement expiry, failed/cancelled payment behavior and appropriate refund/reversal handling.
- [ ] PAY-09 Reconcile provider transactions with local events and make support investigations possible without exposing payment secrets.
- [ ] PAY-10 Test forged callbacks, double payment, amount/currency/plan mismatches and quota grants end to end.

## PRI — Privacy, authorization and data lifecycle

Current state: Ownership/encryption/log redaction foundations exist; lifecycle is incomplete.

- [ ] PRI-01 Apply authenticated ownership checks and tests to every current and new private endpoint, job, lookup and cache.
- [ ] PRI-02 Implement account data export with owner-only expiring delivery.
- [ ] PRI-03 Implement account deletion, session revocation and complete data-purge worker jobs.
- [ ] PRI-04 Implement approved conversation/document/upload retention and explain pending/failed deletion states.
- [ ] PRI-05 Define auditable handling of retained payment/audit records with owner/counsel input rather than guessing obligations.
- [ ] PRI-06 Test deletion races against streams, jobs, exports and regenerated documents; prevent deleted content from reappearing.
- [ ] PRI-07 Check redaction across application/provider/error/trace paths; permit content review only through an approved consent/access process.
- [ ] PRI-08 Create least-privilege reviewer/admin authorization and audit records for imports, approvals, exports, deletion and entitlement changes.
- [ ] PRI-09 Review HTML/XML injection, signed-link leakage, object ownership and sensitive file names; add meaningful abuse tests.
- [ ] PRI-10 Keep development keys/SSH private keys out of Git and build contexts; audit dependencies and resolve applicable security findings.

## SUP — Support, approved content and secondary promises

Current state: Feedback is stored; support delivery/review and approved content are incomplete.

- [ ] SUP-01 Replace placeholder legal pages, disclaimers, referrals and other legal copy with owner-approved versioned files.
- [ ] SUP-02 Wire stored feedback to the approved support destination with bounded, idempotent delivery/retries.
- [ ] SUP-03 Provide a controlled way to inspect/resolve support tickets and flag inaccurate/harmful answers.
- [ ] SUP-04 Build a documented process for correcting templates/sources and identifying affected saved outputs.
- [ ] SUP-05 Check landing/Subscribe/install/voice/invite/share wording against actual shipped capabilities; retain link-only referrals unless rewards are approved.
- [ ] SUP-06 Complete promised PWA behavior and browser support testing if advertised; otherwise explicitly scope it out of the release.

## EVA — Evaluation, tests and CI

Current state: Local fake-model smoke passes; complete AI quality evidence and current CI wiring are missing.

- [ ] EVA-01 Repair CI commands that still reference removed Next.js npm scripts; use plain-JS/Vite checks without changing framework or adding unapproved dependencies.
- [ ] EVA-02 Commit a reproducible browser acceptance harness; current integration browser checks were run from a temporary external QA directory.
- [ ] EVA-03 [OWNER] Supply advocate-reviewed research golden set, passage relevance labels, safety cases and document QA fixtures; legal fixture content must not be invented.
- [ ] EVA-04 Build a versioned evaluation dataset format and frozen held-out test split; exclude fake fixtures from reported legal-quality scores.
- [ ] EVA-05 Implement retrieval Recall@K, MRR/nDCG and coverage evaluation with explicit relevance judgments.
- [ ] EVA-06 Run generator-with-expert-context separately from full-pipeline evaluation to diagnose retrieval versus generation errors.
- [ ] EVA-07 Evaluate claim support, completeness, factual/legal correctness, citation precision/recall and abstention separately.
- [ ] EVA-08 Calibrate any LLM judge against advocates; report disagreement and uncertainty rather than a single opaque score.
- [ ] EVA-09 Test adversarial injection, conflicting/stale sources, missing facts, language/jurisdiction limits and unsupported questions.
- [ ] EVA-10 Test real template outputs, hostile values, preview/Word text equality, supported formatting and generation idempotency.
- [ ] EVA-11 Run current full unit/integration/browser suites, real Postgres/Redis/storage ownership/race checks and reversible migrations in CI.
- [ ] EVA-12 Gate content/model/prompt/retrieval changes on accepted baselines; include representative concurrency, fault and recovery tests without hiding skipped live checks.

## OBS — Product-level quality and incident feedback

Current state: Sanitized tracing hooks exist; answer-quality instrumentation is incomplete.

- [ ] OBS-01 Record request outcome, model/prompt/corpus/template versions, retrieval IDs/scores, verifier removals and abstention decisions.
- [ ] OBS-02 Measure time to first useful answer, total latency, token usage, per-feature cost and errors separately.
- [ ] OBS-03 Instrument and review unexpected abstention, fabricated-authority detections, broken generation and quota complaints.
- [ ] OBS-04 Implement consent-aware advocate sampling/review and feed confirmed failures back into frozen regression cases.
- [ ] OBS-05 Define triage, correction, feature disablement and user-support handling for confirmed harmful/incorrect outputs.
- [ ] OBS-06 Define graceful product behavior for unavailable model/retrieval/storage/scanner services; no silent fake success.

## REL — Product acceptance and release evidence

Current state: No complete real-content release evidence exists.

- [ ] REL-01 Freeze an exact release feature list and remove or disable promises for anything unfinished.
- [ ] REL-02 Demonstrate research using approved real sources with inspectable verified citations and correct abstention.
- [ ] REL-03 Demonstrate approved template selection/prefill/edit/preview/generate/download/reopen with no invented facts or wording drift.
- [ ] REL-04 Demonstrate complete account recovery, consent, privacy requests, quota and paid/upload flows for every feature actually offered.
- [ ] REL-05 Collect passing CI/evaluation reports and owner/advocate acceptance of the release sample; document remaining limitations explicitly.

## Suggested execution order (not a change to CI gates)

1. DEC + EVA foundations: resolve actual owner inputs, repair current CI, define dataset/schema and acceptance gates.
2. COR/ING/RET/GEN/CIT/SAF: build a verified research vertical slice, measure it, then broaden approved coverage.
3. TPL/PRE/DOC: replace fake templates, complete approved versioning and grounded drafting, fix state/version defects.
4. ACC/CHAT/QUO/PRI/SUP/OBS: complete customer flows and lifecycle in parallel only where dependencies permit.
5. PAY and UPL: finish before advertising/selling the corresponding capabilities; keep disabled otherwise.
6. REL: pass the agreed real-content checks and record release acceptance.

These are task dependencies, not an assurance that everything can be finished today. Product readiness
requires content, credentials, decisions and review in addition to implementation. Do not start a new
milestone contrary to BUILD_PLAN CI gates without the owner explicitly changing that requirement.
