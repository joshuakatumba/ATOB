import importlib.util
from pathlib import Path

from civis.learning import (
    InteractionRecord,
    build_dpo_pairs,
    build_sft_examples,
    scrub_pii,
)

_GATE_SPEC = importlib.util.spec_from_file_location(
    "eval_legal_gate", Path(__file__).resolve().parents[3] / "ml/eval_legal_gate.py"
)
assert _GATE_SPEC and _GATE_SPEC.loader
_gate = importlib.util.module_from_spec(_GATE_SPEC)
_GATE_SPEC.loader.exec_module(_gate)


def _record(**overrides) -> InteractionRecord:
    base = dict(
        id="rec-1",
        mode="research",
        prompt="What is the notice period under the Employment Act?",
        rewritten_query="Employment Act notice period",
        retrieved_sources=[
            {"id": "1", "title": "Employment Act s.58", "text": "Notice depends on service length."}
        ],
        response_text="Under section 58 of the Employment Act, notice depends on length of service [1].",
        draft_values=None,
        human_edited_values=None,
        status="complete",
        failure_stage=None,
        failure_reason=None,
        explicit_rating=None,
        copied_count=0,
        downloaded_count=0,
        supporting_opened_count=0,
        regenerated_count=0,
    )
    base.update(overrides)
    return InteractionRecord(**base)


def test_scrub_pii_redacts_sensitive_fields() -> None:
    raw = "Contact jane.doe@example.ug or +256 772 123 456 (NIN CM90012345ABCD) at https://x.test?token=secret123"
    cleaned = scrub_pii(raw)
    assert "jane.doe@example.ug" not in cleaned
    assert "+256 772 123 456" not in cleaned
    assert "CM90012345ABCD" not in cleaned
    assert "secret123" not in cleaned
    assert "[EMAIL]" in cleaned
    assert "[PHONE]" in cleaned
    assert "[ID]" in cleaned
    assert "[REDACTED]" in cleaned


def test_build_sft_examples_prefers_human_edited_drafts() -> None:
    rec_good = _record(id="1", explicit_rating=1)
    rec_copied = _record(id="2", copied_count=1, explicit_rating=None)
    rec_bad = _record(id="3", explicit_rating=-1)
    rec_draft = _record(
        id="4",
        mode="drafting",
        prompt="Draft a lease for Plot 10",
        response_text='{"landlord": "AI Guess"}',
        draft_values={"landlord": "AI Guess"},
        human_edited_values={"landlord": "Grace Nakimera"},
    )
    examples = build_sft_examples([rec_good, rec_copied, rec_bad, rec_draft])
    ids = [e["metadata"]["id"] for e in examples]
    assert ids == ["1", "2", "4"]
    assert "Grace Nakimera" in examples[2]["messages"][2]["content"]


def test_build_dpo_pairs_matches_chosen_and_rejected() -> None:
    chosen = _record(
        id="good-1",
        explicit_rating=1,
        response_text="An employee may complain to a labour officer within six months [1].",
    )
    rejected = _record(
        id="bad-1",
        explicit_rating=-1,
        response_text="Response unavailable.",
    )
    pairs = build_dpo_pairs([chosen, rejected])
    assert len(pairs) == 1
    assert pairs[0]["metadata"]["chosen_id"] == "good-1"
    assert pairs[0]["metadata"]["rejected_id"] == "bad-1"
    assert "six months [1]" in pairs[0]["chosen"]


def test_legal_eval_gate_checks_citations_style_and_abstention() -> None:
    case = {
        "id": "ug-emp-01",
        "required_citations": ["[1]"],
        "expected_keywords": ["six months", "labour officer"],
        "must_abstain": False,
        "sources": [{"id": "1", "title": "Employment Act", "text": "..."}],
    }
    ok = _gate.evaluate_response(
        case, "You may complain to a labour officer within six months [1]."
    )
    assert ok["passed"] is True

    bad = _gate.evaluate_response(
        case, "You may complain to a labour officer, and wait six months [99] ✅"
    )
    assert bad["passed"] is False
    assert "hallucinated_citation" in bad["reasons"]
    assert "contains_emoji" in bad["reasons"]
    assert "comma_before_and" in bad["reasons"]

    abstain_case = {"id": "ab-1", "must_abstain": True, "sources": []}
    abstain_ok = _gate.evaluate_response(
        abstain_case, "Cannot verify this query because there is insufficient evidence."
    )
    assert abstain_ok["passed"] is True

