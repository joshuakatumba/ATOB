#!/usr/bin/env python3
"""Live Laws.Africa Uganda retrieval & grounded generation benchmark runner."""

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api"))
sys.path.insert(0, str(ROOT))

from civis.config import Settings  # noqa: E402
from civis.providers import Turn, provider_from_settings  # noqa: E402
from civis.research import GroundedProvider, LawsAfricaRetriever  # noqa: E402

BENCHMARK_QUERIES = [
    {
        "query_id": "ug-emp-notice",
        "question": (
            "What notice period applies to termination of an employment contract "
            "under the Employment Act in Uganda?"
        ),
    },
    {
        "query_id": "ug-limitation-contract",
        "question": (
            "What is the limitation period for bringing a breach of contract action in Uganda?"
        ),
    },
    {
        "query_id": "ug-data-protection-rights",
        "question": (
            "What rights does a data subject have under the Data Protection and "
            "Privacy Act in Uganda?"
        ),
    },
]


async def run() -> int:
    settings = Settings.from_env()
    if settings.retrieval_provider != "laws_africa" or not settings.laws_africa_api_key:
        print(json.dumps({"error": "LAWS_AFRICA_API_KEY not configured"}))
        return 1
    retriever = LawsAfricaRetriever(settings)
    provider = provider_from_settings(settings)
    prompt = (ROOT / "apps/api/civis/prompts/research-v1.txt").read_text()
    results = []
    for item in BENCHMARK_QUERIES:
        sources = await retriever.retrieve(item["question"])
        entry: dict[str, object] = {
            "query_id": item["query_id"],
            "retrieved_count": len(sources),
            "retrieved_sources": [
                {
                    "id": s.source_id,
                    "title": s.title,
                    "citation": s.citation,
                    "url": s.url,
                }
                for s in sources
            ],
        }
        if provider is not None:
            grounded = GroundedProvider(provider, retriever)
            chunks: list[str] = []
            turns = [Turn(role="user", content=item["question"])]
            async for event in grounded.stream(prompt, turns):
                if event.kind == "text":
                    chunks.append(event.text)
            entry["verified_answer_chars"] = len("".join(chunks))
            entry["citations"] = grounded.citations
        results.append(entry)
    print(json.dumps({"benchmark": "uganda_live_eval", "queries": results}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
