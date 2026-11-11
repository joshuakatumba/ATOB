"""Score ranked source IDs against advocate labels; never score FAKE fixtures as evidence."""

import argparse
import json
import math
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, ValidationError

Identifier = Annotated[str, Field(min_length=1, max_length=300)]
Grade = Annotated[int, Field(ge=1, le=3)]


class Labels(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    query_id: Identifier
    relevant: dict[Identifier, Grade]
    is_fake: bool
    reviewed_by: Identifier


class Ranking(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    query_id: Identifier
    retrieved: list[Identifier] = Field(max_length=10000)


def read_records[Record: BaseModel](path: Path, schema: type[Record]) -> list[Record]:
    records = []
    with path.open() as source:
        for number, line in enumerate(source, 1):
            if not line.strip():
                continue
            try:
                records.append(schema.model_validate_json(line))
            except ValidationError:
                # Do not include queries, labels or source text in error output.
                raise ValueError(f"invalid_record_at_line_{number}") from None
    return records


def metrics(relevant: dict[str, int], retrieved: list[str], k: int) -> dict[str, float]:
    if k < 1 or not relevant or len(set(retrieved)) != len(retrieved):
        raise ValueError("invalid_ranking_or_labels")
    top = retrieved[:k]
    hits = [rank for rank, source in enumerate(top, 1) if source in relevant]
    dcg = sum(
        (2 ** relevant.get(source, 0) - 1) / math.log2(rank + 1)
        for rank, source in enumerate(top, 1)
    )
    ideal = sum(
        (2**grade - 1) / math.log2(rank + 1)
        for rank, grade in enumerate(sorted(relevant.values(), reverse=True)[:k], 1)
    )
    return {
        "recall": len(hits) / len(relevant),
        "mrr": 1 / hits[0] if hits else 0.0,
        "map": sum(count / rank for count, rank in enumerate(hits, 1)) / min(k, len(relevant)),
        "ndcg": dcg / ideal,
    }


def evaluate(labels: list[Labels], rankings: list[Ranking], k: int) -> dict[str, object]:
    if k < 1:
        raise ValueError("invalid_k")
    expected = {row.query_id: row for row in labels}
    actual = {row.query_id: row for row in rankings}
    if len(expected) != len(labels) or len(actual) != len(rankings):
        raise ValueError("duplicate_query_ids")
    if set(actual) - set(expected):
        raise ValueError("unexpected_query_ids")
    if any(len(set(row.retrieved)) != len(row.retrieved) for row in rankings):
        raise ValueError("duplicate_retrieved_ids")
    eligible = [row for row in labels if not row.is_fake and row.relevant]
    if not eligible:
        raise ValueError("no_reviewed_nonfake_answerable_queries")
    scores = [
        metrics(row.relevant, actual[row.query_id].retrieved if row.query_id in actual else [], k)
        for row in eligible
    ]
    return {
        "layer": "retrieval",
        "k": k,
        "queries_scored": len(scores),
        "missing_rankings": sum(row.query_id not in actual for row in eligible),
        "fake_excluded": sum(row.is_fake for row in labels),
        "unanswerable_excluded": sum(not row.is_fake and not row.relevant for row in labels),
        "coverage_at_k": sum(score["recall"] > 0 for score in scores) / len(scores),
        "metrics": {
            f"{name}_at_{k}": sum(s[name] for s in scores) / len(scores)
            for name in ("recall", "mrr", "map", "ndcg")
        },
        "generation": "not_evaluated",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("labels", type=Path)
    parser.add_argument("rankings", type=Path)
    parser.add_argument("--k", type=int, default=20)
    args = parser.parse_args()
    try:
        report = evaluate(
            read_records(args.labels, Labels), read_records(args.rankings, Ranking), args.k
        )
    except (OSError, ValueError) as error:
        # OS error text may include private paths; never echo it.
        print(
            json.dumps({"error": "input_unavailable" if isinstance(error, OSError) else str(error)})
        )
        return 2
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
