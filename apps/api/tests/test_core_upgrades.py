import json
from collections.abc import AsyncIterator

import pytest

from civis.config import Settings
from civis.providers import FallbackProvider, ModelEvent, ProviderRateLimited, Turn
from civis.research import GroundedProvider, ResearchFailure, Source, _norm_quote
from civis.uploads import _detect_image_mime


class _StaticRetriever:
    async def retrieve(self, query: str) -> list[Source]:
        del query
        return [
            Source(
                id="src-1",
                text="Section 68: An employer may summarily dismiss an employee for fundamental breach.",
                title="Employment Act — Section 68",
                url="https://ulii.org/akn/ug/act/2006/6/eng@2006-06-05",
                date="2006-06-05",
                knowledge_base="legislation-ug",
                portion_type="section",
                work_uri="/akn/ug/act/2006/6",
                expression_uri="/akn/ug/act/2006/6/eng@2006-06-05",
            )
        ]


class _MixedGroundedModel:
    def __init__(self, quote: str) -> None:
        self.quote = quote
        self.calls = 0

    async def stream(self, system: str, messages: list[Turn]) -> AsyncIterator[ModelEvent]:
        del system, messages
        self.calls += 1
        if self.calls == 1:
            payload = {
                "abstain": False,
                "segments": [
                    {
                        "text": "Summary dismissal applies for fundamental breach.",
                        "source_ids": ["src-1"],
                        "evidence": [{"source_id": "src-1", "quote": self.quote}],
                    },
                    {
                        "text": "Unsupported extra claim.",
                        "source_ids": ["src-1"],
                        "evidence": [{"source_id": "src-1", "quote": self.quote}],
                    },
                ],
            }
        else:
            payload = {"supported": [0]}
        yield ModelEvent(kind="text", text=json.dumps(payload))
        yield ModelEvent(kind="usage", input_tokens=10, output_tokens=20, finish_reason="stop")


@pytest.mark.asyncio
async def test_grounded_partial_recovery_and_normalized_quotes() -> None:
    # Quote has extra whitespace to exercise _norm_quote normalization.
    strict_model = _MixedGroundedModel("Section 68:   An employer may summarily dismiss an employee")
    strict_provider = GroundedProvider(strict_model, _StaticRetriever(), allow_partial=False)
    with pytest.raises(ResearchFailure) as exc:
        async for _ in strict_provider.stream("sys", [Turn(role="user", content="summary dismissal")]):
            pass
    assert exc.value.code == "unsupported_claim"

    partial_model = _MixedGroundedModel("Section 68:   An employer may summarily dismiss an employee")
    partial_provider = GroundedProvider(partial_model, _StaticRetriever(), allow_partial=True)
    chunks = [
        ev.text
        async for ev in partial_provider.stream("sys", [Turn(role="user", content="summary dismissal")])
        if ev.kind == "text"
    ]
    out = "".join(chunks)
    assert "Summary dismissal applies for fundamental breach." in out
    assert "Unsupported extra claim." not in out
    assert len(partial_provider.citations) == 1


@pytest.mark.asyncio
async def test_fallback_provider_recovers_on_primary_rate_limit() -> None:
    class _RateLimitedPrimary:
        async def stream(self, system: str, messages: list[Turn]) -> AsyncIterator[ModelEvent]:
            del system, messages
            raise ProviderRateLimited(30)
            yield  # pragma: no cover

    class _HealthyFallback:
        async def stream(self, system: str, messages: list[Turn]) -> AsyncIterator[ModelEvent]:
            del system, messages
            yield ModelEvent(kind="text", text="Fallback legal response")
            yield ModelEvent(kind="usage", input_tokens=5, output_tokens=3, finish_reason="stop")

    fb = FallbackProvider(_RateLimitedPrimary(), _HealthyFallback())
    events = [ev async for ev in fb.stream("sys", [Turn(role="user", content="hi")])]
    assert "".join(ev.text for ev in events if ev.kind == "text") == "Fallback legal response"


def test_detect_image_mime_and_norm_quote() -> None:
    assert _detect_image_mime(b"\x89PNG\r\n\x1a\nrest") == "image/png"
    assert _detect_image_mime(b"\xff\xd8\xff\xe0rest") == "image/jpeg"
    assert _detect_image_mime(b"RIFF1234WEBPdata") == "image/webp"
    assert _detect_image_mime(b"not-an-image") is None
    assert _norm_quote("“Section  68” — test") == '"Section 68" - test'


def test_settings_reads_partial_and_fallback_env() -> None:
    base = {
        "DATABASE_URL": "postgresql+asyncpg://u:p@localhost/db",
        "REDIS_URL": "redis://localhost:6379/0",
        "SUPERTOKENS_URI": "http://localhost:3567",
        "SUPERTOKENS_API_KEY": "k",
        "API_DOMAIN": "http://localhost:8000",
        "WEB_DOMAIN": "http://localhost:3000",
        "S3_ENDPOINT": "http://localhost:9000",
        "S3_ACCESS_KEY": "a",
        "S3_SECRET_KEY": "b",
        "S3_BUCKET": "c",
        "LOG_HMAC_KEY": "d",
        "SMTP_HOST": "localhost",
        "SMTP_PORT": "1025",
        "SMTP_FROM": "noreply@example.com",
        "RESEARCH_ALLOW_PARTIAL": "true",
        "FALLBACK_LLM_PROVIDER": "anthropic",
        "FALLBACK_LLM_MODEL": "claude-3-5-sonnet-latest",
    }
    s = Settings.from_env(base)
    assert s.research_allow_partial is True
    assert s.fallback_llm_provider == "anthropic"
    assert s.fallback_llm_model == "claude-3-5-sonnet-latest"
