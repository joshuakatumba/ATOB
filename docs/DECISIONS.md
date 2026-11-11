> Current owner scope (2026-11-07): integrate the supplied React 18/plain JSX/Vite UI with existing FastAPI/SuperTokens services. Preserve markup, copy and CSS. The earlier Next.js rebuild and milestone ordering below are historical; current scope and evidence are tracked in STATUS.md.

# Decisions the owner must confirm before Codex starts

Codex must not choose any of these. Defaults are proposals, not approvals.

| ID | Decision | Proposed default | Why it matters |
|----|----------|------------------|----------------|
| D1 | Auth system | SuperTokens self-hosted (core as a container with its own database): email and password, email verification, reset. Google sign-in optional. | Verify in Milestone 0: current licence, Python and Next.js SDK support, session handling. If it fails, fall back to Ory Kratos. |
| D2 | Host | Render first; all services containerised | Check the nearest region. Latency to Uganda may be high. |
| D3 | Free allowance | 20 prompts per account, lifetime, no reset | Frontend shows "X of 20 free prompts left". A monthly reset changes the ledger design. |
| D4 | What counts as a prompt | One user request that calls the model: a chat message or a drafting prefill. Rendering a template and downloading are free. | Defines the ledger. |
| D5 | Aborted generations | Prompt is consumed once the first token is sent. Refunded on any server error before the first token. | Prevents abuse by cancelling. |
| D6 | Plans and prices | Not defined. Needs names, price in UGX, prompt allowance, duration. | Billing cannot be built without it. |
| D7 | Payment provider | One of Flutterwave, Pesapal, DPO | Must support MTN MoMo and Airtel Money. Verify sandbox access and webhook signing. |
| D8 | Referral reward | None in v1: share link only, no backend | A reward invites fraud. If wanted: +5 prompts to both after the invitee verifies email, capped at 5 rewards per user. |
| D9 | Corpus sources | Owner approved Laws.Africa hosted Uganda legislation-ug and judgments-ug Knowledge Bases for testing on 2026-11-09. | Preview collections; production plan/rights and completeness require review. No local text corpus replicated. |
| D10 | Retrieval architecture | Owner approved hosted Laws.Africa retrieval on 2026-11-09, replacing local embedding/index selection for this integration. | No local embedding/reranker is selected. Advocate query/source labels remain needed to benchmark hosted relevance. |
| D11 | Languages | English only in v1. Luganda and Swahili input is detected and answered with a polite English-only notice. | Quality in other languages is untested. |
| D12 | Data residency and retention | Counsel decides: where data may live, whether prompts may go to a US-based model provider, how long conversations are kept. | Data Protection and Privacy Act 2019 questions. Not an engineering call. |
| D13 | Support channel | One support email | Feedback form delivers there. |
| D14 | Upload limits | 10 MB, 30 pages, PDF and DOCX only, 5 uploads per day, 50 MB storage per user | Cost and abuse control. |
| D15 | Quota cost of a document question | 1 prompt under 15 pages, 2 above. Owner decides whether free users may upload at all. | Defines the ledger for uploads. |
| D16 | Upload retention | 30 days, or earlier on deletion | Privacy. Pending D12. |
| D17 | Sensitive document types | Warn on ID documents and bank statements, do not block | Pending counsel. |

## Owner testing decisions — 2026-11-09

The owner approved using Groq through environment-configured credentials/models for immediate product testing.
The owner stated existing templates were counsel-approved for this use case; the 62 original Civis.jsx
templates are copied unchanged into content/owner-supplied/templates.json and imported with that testing approval.
This records the owner's instruction; it does not claim an independent legal review or verified legal RAG.
Hosted Uganda Knowledge Base access and architecture are now approved for testing; production release/content coverage decisions remain unresolved.

## Whole-answer verification — owner decision 2026-11-09

Owner explicitly chose “Withhold the whole answer” when some paragraphs pass source verification
and others fail. No partial verified answer is released. This overrides partial-removal behavior
for the hosted Research integration. Improving generation must not lower individual source checks.

## Supplied content and user-facing runtime — owner clarification 2026-11-09

Owner confirms supplied templates/content are legitimate and ready for building, and objects to
diagnostic labels appearing in the product. The 62 owner-approved templates remain unchanged.
Normal startup uses real providers and approved content only. Synthetic fixtures remain confined
to explicit isolated test mode; no sample response is relabelled as a real answer.


## Core continuation and development-only direction — 2026-11-09

Owner requested the 30 ordered core tasks, then explicitly stopped deployment and Docker Compose
work in favour of code development. No server mutation was performed. The owner has no additional
approved routing wording, contacts or advocate dataset; these remain missing inputs, not fabricated
acceptance. Existing technical availability wording is retained. Whole-answer withholding remains fixed.
Model/key/reasoning configuration stays in environment settings; the local controlled testing model
is now 120B. Limited successful checks do not establish independent legal accuracy or release approval.
