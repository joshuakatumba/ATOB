"""Run one real research request and report technical results without answer/query text."""

import argparse
import asyncio
import json
import time
from pathlib import Path

from civis.config import Settings
from civis.providers import Turn, provider_from_settings
from civis.research import GroundedProvider, LawsAfricaRetriever, ResearchFailure


async def probe(query: str) -> None:
    settings = Settings.from_env()
    provider = provider_from_settings(settings)
    if provider is None or provider.is_fake:
        raise SystemExit("Real provider required")
    grounded = GroundedProvider(provider, LawsAfricaRetriever(settings))
    started = time.monotonic()
    report: dict[str, object] = {}
    try:
        events = [
            event
            async for event in grounded.stream(
                Path("apps/api/civis/prompts/research-v1.txt").read_text(),
                [Turn(role="user", content=query)],
            )
        ]
        report.update(
            result="verified",
            citations=len(grounded.citations),
            answer_characters=sum(len(e.text) for e in events),
        )
    except ResearchFailure as error:
        report.update(result="withheld", stage=error.stage, reason=error.code)
    except Exception as error:
        report.update(result="failed", stage=grounded.stage, reason=type(error).__name__)
    report.update(
        sources=grounded.source_count,
        input_tokens=grounded.input_tokens,
        output_tokens=grounded.output_tokens,
        elapsed_ms=int((time.monotonic() - started) * 1000),
        upstream_status=grounded.upstream_status,
    )
    print(json.dumps(report))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query")
    asyncio.run(probe(parser.parse_args().query))
