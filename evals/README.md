# Retrieval evaluation

Run with the pinned backend environment (no new dependencies):

```sh
.venv/bin/python -m evals.retrieval /private/labels.jsonl /private/rankings.jsonl --k 20
.venv/bin/pytest evals/test_retrieval.py -q
```

Each labels JSONL record has query_id, relevant (source ID to integer relevance grade 1–3),
is_fake (explicit boolean), reviewed_by (reviewer reference). Grade 0/unjudged sources are omitted.
An empty relevant mapping identifies an unanswerable query; these are counted separately,
not given a perfect retrieval score. Labels and grades must come from advocate review.
Each rankings record has the same query_id and retrieved (unique source IDs in rank order).
Use stable section/chunk IDs, with the same granularity in both files. Keep query text and
source text out of this interface. Keep real datasets private; no real legal dataset is bundled.

The aggregate report separates retrieval from generation. It reports macro Recall@K,
MRR@K, MAP@K (AP denominator min(K, relevant count)), nDCG@K (gain 2^grade−1),
and query coverage (fraction with at least one relevant result in top K).
Missing runs score zero. Duplicate/unknown query IDs and duplicate retrieved IDs are rejected.
FAKE rows are always excluded; an empty/all-FAKE/unanswerable-only dataset fails with exit 2.
Malformed inputs report line numbers without echoing content. Test arithmetic uses explicitly FAKE identifiers;
it is not published as evidence of legal quality. Tests are included in default pytest discovery.

This is the benchmark scorer, not a retriever, embedding model, source licence or release gate.
No source-backed quality score is available until approved labels and ranked results exist.
Generation must be evaluated separately using expert context and end-to-end context; this tool
intentionally reports generation as not_evaluated. Judge calibration and release thresholds remain owner inputs.

# Inputs still required

D9/D10: owner approved Laws.Africa hosted Uganda retrieval on 2026-11-09, replacing local embedding selection.
The metadata-only source manifest is content/corpus/laws-africa-uganda.json. Advocate query-to-source labels
are still needed to evaluate hosted relevance; no real labels were fabricated.
ULII access was investigated; its full terms page returned 403 to the browsing tool, so no bulk/API
permission was assumed and no document content was fetched. Source: https://ulii.org/en/terms-of-use/

Generation is evaluated separately:

```sh
.venv/bin/python -m evals.generation /private/generation-reviews.jsonl
```

`GenerationReview` in `evals/generation.py` defines the strict review record. Use `oracle`
context for generation tested with counsel-selected evidence, and `retrieved` for the complete
pipeline. Report these groups separately. Reviewers count supported/total claims and citations,
record expected/cited source IDs, and grade relevance and (when a reference exists) correctness.
Withheld answers count toward answer rate and source recall; they do not receive perfect
faithfulness for producing no claims. Missing correctness references produce `null`, not a pass.
FAKE records are excluded. An LLM verifier inside the product is not an independent quality score.

No advocate-reviewed dataset or approved routing messages were supplied. Start with the two
owner-reported questions and a small counsel review, recording expected sources before tuning.
Do not invent gold labels or report unit-test arithmetic as legal performance. Provider preview
coverage and use terms still require owner confirmation before a market-readiness claim.
