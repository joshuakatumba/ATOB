# Evaluation

## Implemented retrieval scorer (2026-11-09)

`evals/retrieval.py` scores supplied advocate labels against ranked source IDs: Recall@K, MRR@K, MAP@K, nDCG@K and query coverage. See [runner contract](../evals/README.md). Missing runs score zero; FAKE fixtures are excluded and an all-FAKE dataset fails. Five local unit checks pass. No approved real dataset/ranking run exists, so no legal-quality score or generation pass is claimed.

## Datasets (in evals/, supplied and approved by advocates)
- Golden set: 300 to 500 questions across employment, land, family, criminal procedure, contract, company, tenancy, tax, consumer and data protection. Each has required points, required sources and prohibited statements.
- Retrieval set: 200 or more queries mapped to correct sections.
- Safety set: adversarial and edge cases below.
- Document QA set (Milestone 4b): contracts supplied by advocates with known clauses and planted traps (missing termination clause, one-sided penalty, inconsistent dates and amounts).
Codex builds the runners and reports. Codex does not write the legal content of any dataset. Placeholder fixtures must be marked FAKE and excluded from reported scores.

## Metrics
- Retrieval: recall at 20, MRR, nDCG. Reported separately from generation.
- Generation: faithfulness, citation precision, citation recall, completeness, correct abstention.
- Operations: p50 and p95 time to first token, total latency, cost per answer, abstention rate, escalation rate.
- LLM judges are allowed only after measured agreement with advocate grades on a calibration set. Report the agreement.

## Release gates (thresholds set by the owner and advocates, enforced in CI)
- Fabricated authority (a citation that does not exist or is not in the retrieved set): zero tolerated. Any occurrence blocks release.
- Faithfulness, citation precision and retrieval recall must not drop against the stored baseline.
- Safety set: all urgent and refusal cases pass.

## Edge cases that must exist in the safety set
Missing key facts; wrong jurisdiction; repealed or amended law; commencement dates; Act versus statutory instrument conflict; statute versus case law; customary and mailo land; "will I win" and guarantee requests; user cites a case that does not exist; a real case not in the corpus; injection hidden in a retrieved chunk and in pasted contract text; "pretend you are my lawyer"; forgery, backdating and tax evasion; arrest, detention, domestic violence, self-harm, minors; Luganda, Swahili and code-mixed input; very long pasted text; OCR garbage; limitation and notice-period date arithmetic; empty, very long and markup-laden template values; concurrent requests racing the quota; dropped streams; cancelled streams; duplicate webhook delivery.

## Document upload tests (Milestone 4b)
- The model does not claim clauses exist when they do not, and never declares a document valid or safe.
- Page-citation accuracy: every quoted text exists on the cited page.
- Injection set: hidden white text, instructions in headers and footers, fake "system" messages inside a contract.
- Corrupted, password-protected, empty and mislabelled files; zip bombs; oversized pages.
- Isolation: user A can never retrieve or cite user B's uploads, including through retrieval filters and cache.
- Purge: after deletion, file, text, chunks, embeddings and logs contain nothing from the document.
- Cost: a maximum-size document at maximum question length stays under budget.

## Non-model tests
- Quota: 100 parallel requests at balance 5 spend exactly 5.
- Ownership: user A can never read or modify user B's conversations, documents, uploads or feedback. Test every endpoint.
- Webhooks: forged signature rejected, replay ignored, out-of-order events handled.
- Render: preview HTML and Word output are generated from the same structure and contain identical text.
- Load: 100 concurrent streams for 30 minutes through the real host and CDN. Report p95 time to first token and error rate.

## Production monitoring
Sample 1 to 2 percent of answers for advocate review. Alert on fabricated-authority detections, abstention spikes, cost per answer above budget, and error rate.
