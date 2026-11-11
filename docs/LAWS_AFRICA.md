# Laws.Africa Uganda access check — 2026-11-09

Owner supplied a platform key and proposed Laws.Africa as the Uganda source.
The key is stored only in the ignored private .env as LAWS_AFRICA_API_KEY.
No key, passage text, case summary or statute text is committed here.

## Verified against the live API

- GET https://api.laws.africa/ai/v1/knowledge-bases: HTTP 200.
- Uganda collections returned: legislation-ug and judgments-ug, both labelled preview.
- GET metadata for each Uganda collection: HTTP 200.
- POST retrieve for each collection with a short topical query and top_k=2: HTTP 200, two results each.
- Legislation request used principal=true, repealed=false, frbr_place=ug filters.
- Results provided text plus source metadata: public URL, expression date, source identifier;
  legislation also supplied portion/section URLs and lifecycle flags. Judgment results in this
  sample were summaries, not proof of complete judgment text or complete case coverage.
- Returned text was used only for the access check and was not saved to the repository.
- These checks prove access, not retrieval accuracy, completeness, legal correctness or production entitlement.

## Approved integration (owner reply, 2026-11-09)

Civis server -> Laws.Africa Uganda Knowledge Bases -> bounded source context -> Groq ->
claim/citation verification -> existing chat and persisted source links.
Use only Uganda collection codes and validate country metadata. Keep credentials on the server.
No local embeddings, scraping or corpus ingestion is needed for this hosted retrieval path.
Owner explicitly approved replacing the local hybrid/vector/reranker pipeline and embedding choice D10 with hosted retrieval. The active Research implementation uses that approval.
Grounding still needs follow-up query handling, failure/quota handling, source identifiers,
per-claim support checks, linked citations, no-source behavior and advocate evaluation.
Hosted retrieval does not establish legal accuracy or remove the need for relevance labels.
Research retrieval is now implemented and enabled in the private local environment. Templates and generic Drafting chat retain their existing behavior.

## Official documentation checked

- [Authentication](https://developers.laws.africa/get-started/authentication): Bearer API key; access depends on account services/plan.
- [API choice](https://developers.laws.africa/get-started/choose-an-api): Knowledge Bases maintain retrieval/indexes; Content API supports full local copies.
- [Quick start](https://developers.laws.africa/knowledge-bases/quick-start): v1 collection listing and retrieval contract, filters, results/metadata.
- [Plans](https://developers.laws.africa/get-started/pricing): distinguishes evaluation from production use; actual account plan/production terms not verified.

The proposed path is Knowledge Bases, not full Content API corpus replication.
Review account limits/terms before launch. Rotate the chat-shared key in the platform and replace
its single .env entry; no code change should be needed for replacement.

## Environment and operation

Set RETRIEVAL_PROVIDER=laws_africa and LAWS_AFRICA_API_KEY privately. Optional
LAWS_AFRICA_BASE_URL defaults to https://api.laws.africa/ai/v1. RETRIEVAL_TOP_K defaults to
3 per collection; RETRIEVAL_MAX_CHARS defaults to 12000 across selected passages.
Run ./scripts/dev.sh after updating the branch to apply migration 0006 and rebuild.
For only key replacement, recreate API with docker compose up -d --force-recreate api.
Local Groq testing uses LLM_MAX_OUTPUT_TOKENS=1024 to bound generation/verification requests.
The account returned an 8000-token/minute Groq limit; larger workloads require suitable provider limits.
Failed/unsupported answers are withheld, not silently retried or served ungrounded.
Source expression dates are shown as metadata; they are not proof that every subsequent amendment is covered.

## Acceptance status

Seven focused FAKE-source/filter integration checks pass; migration round trip, static checks, builds
and underlying chat ownership/quota/disconnect checks pass. Real retrieval succeeds, but real grounded
generation and browser source-link/reload acceptance have not passed after one context-budget fix.
Observed Groq rate-limit errors are not proof of the cause of every subsequent failure. The later
fail-closed generation/check cause remains unresolved. Do not mark Research production-ready.

## Provider-limit fix — 2026-11-09

Reproduction of the owner’s dismissal question established: both Laws.Africa calls returned 200,
Groq generation returned valid two-segment JSON, then verification returned HTTP 429 with Retry-After: 2.
Groq rate-limit responses now expose only a typed retry delay, never their response body. Each
Research generation/verification call may retry once after a delay of at most 15 seconds plus a
0.5-second margin, only if no text has arrived. Long delays or a second 429 fail without another
retry; SSE reports rate_limited/retry_after and existing prompt refunds apply. This preserves all
source checks. Failed restored messages show the existing availability text instead of blank bubbles.

Subsequent live diagnosis returned 200 for both Groq calls, but the verifier accepted one of
three paragraphs. Current all-or-nothing policy withheld the answer. Owner was asked whether
partial verified answers are desired for testing; no partial-answer policy has yet changed.
Sixteen API checks and the separate FAKE browser failure-rendering regression pass.

## Whole-answer policy and evidence-first generation

Owner chose whole-answer withholding on 2026-11-09. No partial-answer option is enabled.
Versioned v2 generation requires exact evidence excerpts for all cited source IDs and requests
one concise paragraph limited to what those excerpts establish. Excerpts must match retrieved
source text before the separate verifier runs. The verifier receives explicit paragraph indexes.
The existing all-paragraphs-must-pass gate is preserved, including when only one of three passes.
