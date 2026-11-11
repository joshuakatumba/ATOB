"""Optional paid live smoke test; never sends personal data or legal requests."""

import os

import pytest
from civis.config import Settings
from civis.providers import AnthropicProvider, Turn


@pytest.mark.skipif(
    not (
        os.getenv("ANTHROPIC_API_KEY")
        and os.getenv("LLM_MODEL")
        and os.getenv("CIVIS_RUN_LIVE_PROVIDER_TESTS") == "1"
    ),
    reason="Optional live provider credentials absent",
)
async def test_optional_live_anthropic_smoke():
    settings = Settings.from_env().model_copy(update={"llm_max_output_tokens": 16})
    provider = AnthropicProvider(settings)
    events = [
        event
        async for event in provider.stream(
            "Return only the requested test marker.",
            [Turn(role="user", content="FAKE – development only. Return FAKE.")],
        )
    ]
    assert any(event.kind == "text" and event.text for event in events)
