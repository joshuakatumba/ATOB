"""Export PII-scrubbed SFT, DPO, and failure-audit JSONL datasets from PostgreSQL."""

import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from civis.learning import (
    InteractionRecord,
    build_dpo_pairs,
    build_sft_examples,
    scrub_pii,
)


def _as_dict(val: Any) -> dict[str, Any] | None:
    if isinstance(val, dict):
        return val
    if isinstance(val, str) and val.strip():
        return dict(json.loads(val))
    return None


def _as_list(val: Any) -> list[dict[str, Any]]:
    if isinstance(val, list):
        return [dict(item) for item in val if isinstance(item, dict)]
    if isinstance(val, str) and val.strip():
        return [dict(item) for item in json.loads(val) if isinstance(item, dict)]
    return []


async def export_all(database_url: str, out_dir: Path, limit: int) -> dict[str, int]:
    out_dir.mkdir(parents=True, exist_ok=True)
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            rows = (
                await connection.execute(
                    text(
                        """SELECT
                            id::text, mode, prompt, rewritten_query, retrieved_sources,
                            response_text, draft_values, human_edited_values,
                            status, failure_stage, failure_reason, explicit_rating,
                            copied_count, downloaded_count, supporting_opened_count,
                            regenerated_count
                        FROM interaction_logs
                        ORDER BY created_at DESC
                        LIMIT :limit"""
                    ),
                    {"limit": limit},
                )
            ).mappings().all()
    finally:
        await engine.dispose()

    records = [
        InteractionRecord(
            id=str(r["id"]),
            mode=str(r["mode"]),
            prompt=str(r["prompt"]),
            rewritten_query=r["rewritten_query"],
            retrieved_sources=_as_list(r["retrieved_sources"]),
            response_text=str(r["response_text"] or ""),
            draft_values=_as_dict(r["draft_values"]),
            human_edited_values=_as_dict(r["human_edited_values"]),
            status=str(r["status"]),
            failure_stage=r["failure_stage"],
            failure_reason=r["failure_reason"],
            explicit_rating=r["explicit_rating"],
            copied_count=int(r["copied_count"] or 0),
            downloaded_count=int(r["downloaded_count"] or 0),
            supporting_opened_count=int(r["supporting_opened_count"] or 0),
            regenerated_count=int(r["regenerated_count"] or 0),
        )
        for r in rows
    ]

    sft_rows = build_sft_examples(records)
    dpo_rows = build_dpo_pairs(records)
    failure_rows = [
        {
            "id": r.id,
            "mode": r.mode,
            "prompt": scrub_pii(r.prompt),
            "status": r.status,
            "failure_stage": r.failure_stage,
            "failure_reason": r.failure_reason,
            "source_count": len(r.retrieved_sources),
        }
        for r in records
        if r.status != "complete"
    ]

    for filename, payload in (
        ("sft_train.jsonl", sft_rows),
        ("dpo_train.jsonl", dpo_rows),
        ("failure_audit.jsonl", failure_rows),
    ):
        with (out_dir / filename).open("w", encoding="utf-8") as fh:
            for item in payload:
                fh.write(json.dumps(item, ensure_ascii=False) + "\n")

    return {
        "records": len(records),
        "sft": len(sft_rows),
        "dpo": len(dpo_rows),
        "failures": len(failure_rows),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Export Civis training datasets.")
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL", ""),
        help="SQLAlchemy async database URL.",
    )
    parser.add_argument("--out-dir", type=Path, default=Path("ml/data"))
    parser.add_argument("--limit", type=int, default=50000)
    args = parser.parse_args()
    if not args.database_url:
        raise SystemExit("DATABASE_URL is required (env var or --database-url).")
    counts = asyncio.run(export_all(args.database_url, args.out_dir, args.limit))
    print(json.dumps(counts, indent=2))


if __name__ == "__main__":
    main()

