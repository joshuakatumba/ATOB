"""FAKE identifiers and labels only; these checks are not legal quality scores."""

import math
from pathlib import Path

import pytest

from evals.retrieval import Labels, Ranking, evaluate, metrics, read_records


def test_rank_order_and_cutoff():
    labels = {"FAKE-A": 3, "FAKE-B": 1}
    assert metrics(labels, ["FAKE-A", "FAKE-B"], 20) == {
        "recall": 1.0,
        "mrr": 1.0,
        "map": 1.0,
        "ndcg": 1.0,
    }
    result = metrics(labels, ["FAKE-X", "FAKE-B", "FAKE-A"], 2)
    assert result["recall"] == 0.5
    assert result["mrr"] == 0.5
    assert result["map"] == 0.25
    assert result["ndcg"] == pytest.approx((1 / math.log2(3)) / (7 + 1 / math.log2(3)))
    assert all(value == 0 for value in metrics(labels, [], 20).values())


def test_fake_data_cannot_generate_a_quality_report():
    row = Labels(
        query_id="FAKE-Q", relevant={"FAKE-A": 1}, is_fake=True, reviewed_by="FAKE reviewer"
    )
    with pytest.raises(ValueError, match="no_reviewed_nonfake"):
        evaluate([row], [Ranking(query_id="FAKE-Q", retrieved=["FAKE-A"])], 20)


def test_invalid_and_duplicate_runs():
    row = Labels(
        query_id="FAKE-Q", relevant={"FAKE-A": 1}, is_fake=True, reviewed_by="FAKE reviewer"
    )
    with pytest.raises(ValueError, match="duplicate_query"):
        evaluate([row, row], [], 20)
    with pytest.raises(ValueError, match="unexpected_query"):
        evaluate([row], [Ranking(query_id="FAKE-other", retrieved=[])], 20)
    with pytest.raises(ValueError, match="duplicate_retrieved"):
        evaluate([row], [Ranking(query_id="FAKE-Q", retrieved=["FAKE-A", "FAKE-A"])], 20)
    with pytest.raises(ValueError, match="invalid_k"):
        evaluate([], [], 0)


def test_input_errors_do_not_echo_content(tmp_path: Path):
    path = tmp_path / "FAKE.jsonl"
    path.write_text('{"FAKE-private-input":"FAKE secret"}\n')
    with pytest.raises(ValueError) as error:
        read_records(path, Labels)
    assert str(error.value) == "invalid_record_at_line_1"


def test_missing_runs_are_zero_and_fake_rows_excluded():
    # FAKE metadata simulates reviewed rows to test aggregation, never legal quality.
    labels = [
        Labels(
            query_id="FAKE-A",
            relevant={"FAKE-source": 1},
            is_fake=False,
            reviewed_by="FAKE reviewer",
        ),
        Labels(
            query_id="FAKE-B",
            relevant={"FAKE-source": 1},
            is_fake=False,
            reviewed_by="FAKE reviewer",
        ),
        Labels(
            query_id="FAKE-fixture",
            relevant={"FAKE-source": 1},
            is_fake=True,
            reviewed_by="FAKE reviewer",
        ),
        Labels(
            query_id="FAKE-unanswerable", relevant={}, is_fake=False, reviewed_by="FAKE reviewer"
        ),
    ]
    report = evaluate(labels, [Ranking(query_id="FAKE-A", retrieved=["FAKE-source"])], 20)
    assert report["queries_scored"] == 2
    assert report["missing_rankings"] == 1
    assert report["fake_excluded"] == 1
    assert report["unanswerable_excluded"] == 1
    assert report["coverage_at_k"] == 0.5
    assert report["metrics"] == {
        "recall_at_20": 0.5,
        "mrr_at_20": 0.5,
        "map_at_20": 0.5,
        "ndcg_at_20": 0.5,
    }
