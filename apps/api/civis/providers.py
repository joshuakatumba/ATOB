"""Model providers. No model identifiers or legal content are supplied by application code."""

import asyncio
import json
import math
import os
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Literal, Protocol

import httpx
from pydantic import BaseModel, ConfigDict, Field

from civis.config import Settings


class ModelEvent(BaseModel):
    kind: Literal["text", "usage"]
    text: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    finish_reason: str = "stop"


class Turn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ModelProvider(Protocol):
    is_fake: bool

    def stream(self, system: str, messages: list[Turn]) -> AsyncIterator[ModelEvent]: ...


class ProviderUnavailable(Exception):
    pass


class ProviderHTTPError(ProviderUnavailable):
    def __init__(self, status: int):
        self.status = status if 400 <= status <= 599 else 502
        super().__init__("provider_http_error")


class ProviderRateLimited(ProviderUnavailable):
    def __init__(self, retry_after: int):
        self.retry_after = retry_after
        super().__init__("provider_rate_limited")


class FakeReply(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: Literal["FAKE – development only"]
    parts: list[str] = Field(min_length=1)


class FakeProvider:
    is_fake = True

    def __init__(
        self, reply: FakeReply, delay: float = 0.01, failure_after: int | None = None
    ) -> None:
        self.reply = reply
        self.delay = delay
        self.failure_after = failure_after
        self.cancelled = asyncio.Event()

    @classmethod
    def from_file(cls, failure_after: int | None = None, delay: float = 0.01) -> "FakeProvider":
        path = Path(__file__).resolve().parents[3] / "content/dev-fake/chat.json"
        return cls(FakeReply.model_validate_json(path.read_text()), delay, failure_after)

    async def stream(self, system: str, messages: list[Turn]) -> AsyncIterator[ModelEvent]:
        complete = False
        try:
            for index, part in enumerate(self.reply.parts):
                if self.failure_after is not None and index >= self.failure_after:
                    raise ProviderUnavailable()
                await asyncio.sleep(self.delay)
                yield ModelEvent(kind="text", text=part)
            complete = True
            yield ModelEvent(kind="usage", input_tokens=1, output_tokens=len(self.reply.parts))
        finally:
            if not complete:
                self.cancelled.set()


class RemoteUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0


class RemoteMessage(BaseModel):
    usage: RemoteUsage = Field(default_factory=RemoteUsage)


class RemoteDelta(BaseModel):
    type: str | None = None
    text: str | None = None
    stop_reason: str | None = None


class RemoteEvent(BaseModel):
    type: str
    message: RemoteMessage | None = None
    delta: RemoteDelta | None = None
    usage: RemoteUsage | None = None


class AnthropicProvider:
    is_fake = False

    def __init__(self, settings: Settings) -> None:
        if not settings.anthropic_api_key or not settings.llm_model:
            raise ProviderUnavailable()
        self.settings = settings

    async def stream(self, system: str, messages: list[Turn]) -> AsyncIterator[ModelEvent]:
        settings = self.settings
        assert settings.anthropic_api_key is not None
        headers = {
            "x-api-key": settings.anthropic_api_key.get_secret_value(),
            "anthropic-version": "2023-06-01",
        }
        payload = {
            "model": settings.llm_model,
            "max_tokens": settings.llm_max_output_tokens,
            "system": [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            "messages": [turn.model_dump() for turn in messages],
            "stream": True,
        }
        timeout = httpx.Timeout(connect=10, read=None, write=30, pool=10)
        input_tokens = output_tokens = 0
        finish = "stop"
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream(
                "POST", settings.anthropic_base_url + "/v1/messages", headers=headers, json=payload
            ) as response:
                if response.status_code != 200:
                    raise ProviderHTTPError(response.status_code)
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    event = RemoteEvent.model_validate(json.loads(line[5:].strip()))
                    if event.type == "error":
                        raise ProviderUnavailable()
                    if event.message:
                        input_tokens = event.message.usage.input_tokens
                    if event.usage:
                        output_tokens = event.usage.output_tokens
                    if event.delta and event.delta.stop_reason:
                        finish = event.delta.stop_reason
                    if event.delta and event.delta.type == "text_delta" and event.delta.text:
                        yield ModelEvent(kind="text", text=event.delta.text)
                    if event.type == "message_stop":
                        yield ModelEvent(
                            kind="usage",
                            input_tokens=input_tokens,
                            output_tokens=output_tokens,
                            finish_reason=finish,
                        )
                        return
                raise ProviderUnavailable()


class GroqDelta(BaseModel):
    content: str | None = None


class GroqChoice(BaseModel):
    delta: GroqDelta = Field(default_factory=GroqDelta)
    finish_reason: str | None = None


class GroqUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0


class GroqMetadata(BaseModel):
    usage: GroqUsage | None = None


class GroqChunk(BaseModel):
    choices: list[GroqChoice] = Field(default_factory=list)
    usage: GroqUsage | None = None
    error: dict[str, object] | None = None
    x_groq: GroqMetadata | None = None


class GroqProvider:
    is_fake = False

    def __init__(self, settings: Settings) -> None:
        if not settings.groq_api_key or not settings.llm_model:
            raise ProviderUnavailable()
        self.settings = settings

    async def structured_stream(
        self,
        system: str,
        messages: list[Turn],
        schema: type[BaseModel],
        max_tokens: int | None = None,
    ) -> AsyncIterator[ModelEvent]:
        """Buffer a schema-constrained completion; Groq does not stream strict JSON."""
        settings = self.settings
        assert settings.groq_api_key is not None
        payload: dict[str, object] = {
            "model": settings.llm_model,
            "messages": [{"role": "system", "content": system}]
            + [m.model_dump() for m in messages],
            "max_completion_tokens": max_tokens or settings.llm_max_output_tokens,
            "temperature": 0.2,
            "stream": False,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": schema.__name__,
                    "strict": True,
                    "schema": schema.model_json_schema(),
                },
            },
        }
        if settings.groq_reasoning_effort:
            payload["reasoning_effort"] = settings.groq_reasoning_effort
        async with httpx.AsyncClient(timeout=httpx.Timeout(60, connect=10)) as client:
            async with client.stream(
                "POST",
                settings.groq_base_url.rstrip("/") + "/chat/completions",
                headers={"Authorization": "Bearer " + settings.groq_api_key.get_secret_value()},
                json=payload,
            ) as response:
                if response.status_code == 429:
                    try:
                        delay = max(
                            1,
                            min(3600, math.ceil(float(response.headers.get("retry-after", "60")))),
                        )
                    except (ValueError, OverflowError):
                        delay = 60
                    raise ProviderRateLimited(delay)
                if response.status_code != 200:
                    raise ProviderHTTPError(response.status_code)
                body = bytearray()
                async for chunk in response.aiter_bytes():
                    body.extend(chunk)
                    if len(body) > 2000000:
                        raise ProviderUnavailable()
        data = json.loads(body)
        choices = data.get("choices", [])
        if len(choices) != 1:
            raise ProviderUnavailable()
        choice = choices[0]
        usage = GroqUsage.model_validate(data.get("usage") or {})
        # Account for truncated completions before rejecting their content.
        yield ModelEvent(
            kind="usage",
            input_tokens=usage.prompt_tokens,
            output_tokens=usage.completion_tokens,
            finish_reason=choice.get("finish_reason") or "unknown",
        )
        content = choice.get("message", {}).get("content")
        if not isinstance(content, str):
            raise ProviderUnavailable()
        yield ModelEvent(kind="text", text=content)

    async def stream(self, system: str, messages: list[Turn]) -> AsyncIterator[ModelEvent]:
        settings = self.settings
        assert settings.groq_api_key is not None
        payload = {
            "model": settings.llm_model,
            "messages": [{"role": "system", "content": system}]
            + [m.model_dump() for m in messages],
            "max_completion_tokens": settings.llm_max_output_tokens,
            "temperature": 0.2,
            "stream": True,
        }
        if settings.groq_reasoning_effort:
            payload["reasoning_effort"] = settings.groq_reasoning_effort
        usage = GroqUsage()
        finish = "stop"
        async with httpx.AsyncClient(timeout=httpx.Timeout(60, connect=10)) as client:
            async with client.stream(
                "POST",
                settings.groq_base_url.rstrip("/") + "/chat/completions",
                headers={"Authorization": "Bearer " + settings.groq_api_key.get_secret_value()},
                json=payload,
            ) as response:
                if response.status_code == 429:
                    try:
                        seconds = float(response.headers.get("retry-after", "60"))
                        delay = max(1, min(3600, math.ceil(seconds)))
                    except (ValueError, OverflowError):
                        delay = 60
                    raise ProviderRateLimited(delay)
                if response.status_code != 200:
                    raise ProviderHTTPError(response.status_code)
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        yield ModelEvent(
                            kind="usage",
                            input_tokens=usage.prompt_tokens,
                            output_tokens=usage.completion_tokens,
                            finish_reason=finish,
                        )
                        return
                    chunk = GroqChunk.model_validate_json(data)
                    if chunk.error:
                        raise ProviderUnavailable()
                    if chunk.usage:
                        usage = chunk.usage
                    elif chunk.x_groq and chunk.x_groq.usage:
                        usage = chunk.x_groq.usage
                    for choice in chunk.choices:
                        if choice.delta.content:
                            yield ModelEvent(kind="text", text=choice.delta.content)
                        if choice.finish_reason:
                            finish = choice.finish_reason
                raise ProviderUnavailable()


def provider_from_settings(settings: Settings) -> ModelProvider | None:
    if settings.fake_model or settings.llm_provider == "fake":
        if settings.environment == "production":
            raise ValueError("Fake provider prohibited in production")
        if not settings.enable_test_fixtures:
            raise ValueError(
                "Test model requires ENABLE_TEST_FIXTURES=true; configure a real provider"
            )
        return FakeProvider.from_file(delay=float(os.environ.get("FAKE_STREAM_DELAY", "0.01")))
    if settings.llm_provider == "groq":
        return GroqProvider(settings)
    if settings.llm_provider == "anthropic":
        return AnthropicProvider(settings)
    return None
