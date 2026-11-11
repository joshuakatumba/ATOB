"""FAKE arithmetic fixtures only; these do not establish legal quality."""

import pytest
from pydantic import ValidationError

from evals.generation import GenerationReview, evaluate


def row(**changes):
    return GenerationReview.model_validate(
        {
            "query_id": "FAKE-1",
            "context_mode": "retrieved",
            "is_fake": True,
            "reviewed_by": "FAKE-reviewer",
            "answered": True,
            "claims": 2,
            "supported_claims": 1,
            "citations": 2,
            "supported_citations": 1,
            "expected_source_ids": ["FAKE-a", "FAKE-b"],
            "cited_source_ids": ["FAKE-a"],
            "relevance": 0.5,
            "correctness": None,
            **changes,
        }
    )


def test_fake_reviews_cannot_establish_quality():
    with pytest.raises(ValueError, match="no_reviewed_nonfake"):
        evaluate([row()])


def test_modes_and_abstention_do_not_inflate_support():
    # FAKE arithmetic exercising real-input aggregation; never used as acceptance scores.
    data = evaluate(
        [
            row(is_fake=False),
            row(is_fake=False, context_mode="oracle", supported_claims=2),
            row(
                is_fake=False,
                query_id="FAKE-2",
                answered=False,
                claims=0,
                supported_claims=0,
                citations=0,
                supported_citations=0,
                cited_source_ids=[],
                relevance=0.0,
            ),
        ]
    )
    assert data["contexts"]["retrieved"]["faithfulness"] == 0.5
    assert data["contexts"]["retrieved"]["answer_rate"] == 0.5
    assert data["contexts"]["retrieved"]["source_recall"] == 0.25
    assert data["contexts"]["oracle"]["faithfulness"] == 1.0
    assert data["contexts"]["retrieved"]["answer_correctness"] is None


def test_invalid_grades_and_duplicate_reviews_rejected():
    with pytest.raises(ValidationError):
        row(supported_claims=3)
    with pytest.raises(ValueError, match="duplicate"):
        evaluate([row(is_fake=False), row(is_fake=False)])
