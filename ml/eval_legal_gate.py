"""Automated legal evaluation gate for candidate Civis model checkpoints."""

import argparse
import json
import re
from pathlib import Path
from typing import Any

_EMOJI_RE = re.compile(
    "[\U0001f300-\U0001f9ff\U0001fa00-\U0001faff\u2600-\u27bf]", re.UNICODE
)
_CITATION_RE = re.compile(r"\[(\d+)\]")
_OXFORD_COMMA_RE = re.compile(r",\s+and\b", re.I)
_MULTI_DASH_RE = re.compile(r"--+|—{2,}")
_ABSTAIN_RE = re.compile(
    r"\b(?:unavailable|cannot verify|insufficient evidence|no verified|not covered)\b",
    re.I,
)


def evaluate_response(case: dict[str, Any], response_text: str) -> dict[str, Any]:
    """Check one candidate response against grounding, abstention, and style gates."""
    reasons: list[str] = []
    text = (response_text or "").strip()
    sources = case.get("sources") or []
    valid_indices = {str(i) for i in range(1, len(sources) + 1)}

    if _EMOJI_RE.search(text):
        reasons.append("contains_emoji")
    if _OXFORD_COMMA_RE.search(text):
        reasons.append("comma_before_and")
    if _MULTI_DASH_RE.search(text):
        reasons.append("excessive_dashes")

    cited = set(_CITATION_RE.findall(text))
    hallucinated = [c for c in cited if c not in valid_indices]
    if hallucinated:
        reasons.append("hallucinated_citation")

    if case.get("must_abstain"):
        if not _ABSTAIN_RE.search(text):
            reasons.append("missed_abstention")
    else:
        if not text:
            reasons.append("empty_response")
        for req in case.get("required_citations") or []:
            num = req.strip("[]")
            if num not in cited:
                reasons.append(f"missing_citation_{num}")
        lowered = text.lower()
        for kw in case.get("expected_keywords") or []:
            if kw.lower() not in lowered:
                reasons.append(f"missing_keyword:{kw}")

    return {"id": case["id"], "passed": len(reasons) == 0, "reasons": reasons}


def run_gate(benchmark_path: Path, predictions_path: Path) -> dict[str, Any]:
    cases = [
        json.loads(line)
        for line in benchmark_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    preds = {
        row["id"]: row["response"]
        for row in (
            json.loads(line)
            for line in predictions_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    }
    results = [evaluate_response(c, preds.get(c["id"], "")) for c in cases]
    passed = sum(1 for r in results if r["passed"])
    hallucinations = sum(1 for r in results if "hallucinated_citation" in r["reasons"])
    return {
        "gate_passed": passed == len(results) and hallucinations == 0,
        "total": len(results),
        "passed": passed,
        "hallucinations": hallucinations,
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Civis legal evaluation gate.")
    parser.add_argument(
        "--benchmark", type=Path, default=Path("ml/benchmark_uganda_law.jsonl")
    )
    parser.add_argument("--predictions", type=Path, required=True)
    args = parser.parse_args()
    report = run_gate(args.benchmark, args.predictions)
    print(json.dumps(report, indent=2))
    if not report["gate_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

