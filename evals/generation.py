"""Aggregate independently reviewed generation grades; no self-awarded legal accuracy."""

import argparse
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from evals.retrieval import Identifier, read_records


class GenerationReview(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    query_id: Identifier
    context_mode: Literal["oracle", "retrieved"]
    is_fake: bool
    reviewed_by: Identifier
    answered: bool
    claims: int = Field(ge=0)
    supported_claims: int = Field(ge=0)
    citations: int = Field(ge=0)
    supported_citations: int = Field(ge=0)
    expected_source_ids: list[Identifier]
    cited_source_ids: list[Identifier]
    relevance: float = Field(ge=0, le=1)
    correctness: float | None = Field(ge=0, le=1)

    @model_validator(mode="after")
    def counts(self):
        if self.supported_claims > self.claims or self.supported_citations > self.citations:
            raise ValueError("invalid_review_counts")
        if not self.answered and (self.claims or self.citations or self.cited_source_ids):
            raise ValueError("withheld_answer_has_claims")
        if len(set(self.expected_source_ids)) != len(self.expected_source_ids):
            raise ValueError("duplicate_expected_sources")
        if len(set(self.cited_source_ids)) != len(self.cited_source_ids):
            raise ValueError("duplicate_cited_sources")
        return self


def evaluate(reviews: list[GenerationReview]) -> dict[str, object]:
    keys = [(r.query_id, r.context_mode) for r in reviews]
    if len(set(keys)) != len(keys):
        raise ValueError("duplicate_generation_review")
    eligible = [row for row in reviews if not row.is_fake]
    if not eligible:
        raise ValueError("no_reviewed_nonfake_generation")
    reports = {}
    for mode in ("oracle", "retrieved"):
        rows = [row for row in eligible if row.context_mode == mode]
        if not rows:
            continue
        answered = [row for row in rows if row.answered]
        claims = sum(row.claims for row in rows)
        citations = sum(row.citations for row in rows)
        expected = sum(len(row.expected_source_ids) for row in rows)
        correct = [row.correctness for row in answered if row.correctness is not None]
        reports[mode] = {
            "queries_reviewed": len(rows),
            "answer_rate": len(answered) / len(rows),
            "faithfulness": sum(row.supported_claims for row in rows) / claims if claims else None,
            "citation_precision": sum(row.supported_citations for row in rows) / citations
            if citations
            else None,
            "source_recall": sum(
                len(set(row.cited_source_ids) & set(row.expected_source_ids)) for row in rows
            )
            / expected
            if expected
            else None,
            "answer_relevance": sum(row.relevance for row in answered) / len(answered)
            if answered
            else None,
            "answer_correctness": sum(correct) / len(correct) if correct else None,
            "correctness_reviews": len(correct),
        }
    return {
        "layer": "generation",
        "contexts": reports,
        "fake_excluded": len(reviews) - len(eligible),
        "retrieval": "evaluate_separately",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reviews", type=Path)
    args = parser.parse_args()
    try:
        report = evaluate(read_records(args.reviews, GenerationReview))
    except (OSError, ValueError) as error:
        print(
            json.dumps({"error": "input_unavailable" if isinstance(error, OSError) else str(error)})
        )
        return 2
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
