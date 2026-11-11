# Known risks and things that will fail if ignored

R1. The owner JSX has been split into React 18 components without redesign. Local API/browser integration and backend static checks pass; production acceptance remains pending. See KNOWN_ISSUES.md.

R2. Template content. The owner confirms that the supplied Civis.jsx templates are legitimate and counsel-approved. Preserve their wording and serve the imported approved versions. Diagnostic fixtures are separate and must never enter the normal catalog. New legal wording still comes from the owner, not Codex.

R3. Corpus access. Retrieval is useless without a lawful corpus. Scraping sources without permission can infringe copyright or terms. Confirm licences before M3. If no corpus is available, the "grounded in Ugandan law" claim cannot be made and the product must be positioned as general information.

R4. Citation verification limits. It stops invented authorities. It does not stop a correct citation being misread, an outdated law being used because the corpus is stale, or advice that sounds right but is wrong for the facts. Advocate review of samples is mandatory, and the corpus needs an update process for new amendments.

R5. Local-only integration allows unverified signup; production still requires email verification. Free-prompt abuse. Mitigations: verified email required, per-IP and per-device signals, disposable-email blocking, rate limits, spend alerts on the model account. These reduce abuse but cannot eliminate it. Set a daily spend cap on the model account.

R6. Streaming through proxies. CDNs and hosts may buffer or time out long responses. Verified in S1, not assumed. If S1 fails, the delivery design changes.

R7. Voice input. The browser speech feature depends on the browser and may send audio to a third party. It is unavailable or unreliable in some browsers and probably weak for Luganda. It stays as a labelled convenience feature in v1. A server-side speech service is a separate project with its own cost and privacy review.

R8. Mobile-money billing. Mobile money payments are generally customer-approved per payment, not automatic card-style recurring charges. Design plans as prepaid periods unless the provider confirms otherwise in writing (S5). Webhooks arrive late, twice or out of order; reconcile with a scheduled job.

R9. Model provider limits and cost. Rate limits and quotas must be raised before launch. Retrieval multiplies input tokens per answer. Without cost alerts and caps, one abuse incident can be expensive.

R10. Data protection. Conversations contain sensitive personal data and prompts leave the country to the model provider. Counsel must decide on registration, consent wording, transfer basis and retention (D12) before real users are onboarded.

R11. Auth system choice. Self-hosted auth increases your operational and security burden. Verify licence and SDK support in S2. If it fails, use the fallback in D1 and do not write password handling yourself.

R12. Latency. If the nearest host region is far from Kampala, time to first token suffers. Measured in S6. Mobile networks add more. Keep the first load small and show progress immediately.

R13. Codex failure modes. It will confidently use library APIs that do not exist in the pinned version, skip hard cases, and mock the very things that need real tests. Countermeasures are in AGENTS.md: docs-first, real-database integration tests, small PRs, and stopping instead of working around blockers.

R14. Scale. 5,000 users is not a hard scaling problem. The hard problems are answer quality, legal accuracy, abuse and compliance. Do not add queues, services or caches that no measured problem requires.

R15. User uploads. OCR quality on phone photos is unknown and likely poor. Contract review can miss clauses and users may rely on it. Privacy exposure is high. Do not ship before the evaluation in DOCUMENT_UPLOADS.md section 6, and do not market it as contract approval.

R16. Malware scanning must exist in the deployment. Confirm the host supports it in M0 (S7), or keep uploads disabled.

R17. Storage cost and abuse. Without caps, uploads become free storage and free compute.
