"""Interaction logging, implicit signal tracking, PII scrubbing, and SFT/DPO dataset curation."""

import json
import logging
import re
from collections.abc import Awaitable, Callable
from contextlib import suppress
from dataclasses import dataclass
from typing import Annotated, Any, Literal
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from civis.config import Settings
from civis.main import Profile, StrictModel

logger = logging.getLogger(__name__)

SignalKind = Literal["copied", "downloaded", "supporting_opened", "regenerated"]

_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_PHONE_RE = re.compile(r"(?:\+?256|0)\s*[37]\d{2}[\s-]?\d{3}[\s-]?\d{3}\b|\+\d{1,3}[\s-]?\d{6,12}\b")
_NIN_RE = re.compile(r"\b(?:CM|CF)[A-Z0-9]{10,14}\b")
_TOKEN_PARAM_RE = re.compile(r"([?&](?:token|key|secret|auth|signature)=)[^&\s]+", re.I)

_SIGNAL_COLUMN: dict[SignalKind, str] = {
    "copied": "copied_count",
    "downloaded": "downloaded_count",
    "supporting_opened": "supporting_opened_count",
    "regenerated": "regenerated_count",
}

DEFAULT_SYSTEM_PROMPT = (
    "You are Civis, a grounded Uganda legal assistant. Cite only verified statutory "
    "provisions and case law from the retrieved context. Never use emojis, never place "
    "commas before 'and' in lists, and keep formatting clean and concise."
)


class SignalRequest(StrictModel):
    signal: SignalKind


class LearningStats(BaseModel):
    total_interactions: int
    complete_count: int
    incomplete_count: int
    positive_ratings: int
    negative_ratings: int
    copied_signals: int
    downloaded_signals: int
    human_edited_drafts: int
    failure_reasons: dict[str, int]


@dataclass(frozen=True)
class InteractionRecord:
    id: str
    mode: str
    prompt: str
    rewritten_query: str | None
    retrieved_sources: list[dict[str, Any]]
    response_text: str
    draft_values: dict[str, Any] | None
    human_edited_values: dict[str, Any] | None
    status: str
    failure_stage: str | None
    failure_reason: str | None
    explicit_rating: int | None
    copied_count: int
    downloaded_count: int
    supporting_opened_count: int
    regenerated_count: int


def scrub_pii(value: str) -> str:
    """Redact emails, Ugandan/international phone numbers, NINs, and URL secrets."""
    if not value:
        return value
    cleaned = _EMAIL_RE.sub("[EMAIL]", value)
    cleaned = _PHONE_RE.sub("[PHONE]", cleaned)
    cleaned = _NIN_RE.sub("[ID]", cleaned)
    cleaned = _TOKEN_PARAM_RE.sub(r"\1[REDACTED]", cleaned)
    return cleaned


def _format_context(sources: list[dict[str, Any]]) -> str:
    if not sources:
        return ""
    lines = ["Retrieved legal sources:"]
    for idx, src in enumerate(sources[:6], start=1):
        title = str(src.get("title") or "Legal Source").strip()
        excerpt = scrub_pii(str(src.get("text") or "").strip())
        if len(excerpt) > 600:
            excerpt = excerpt[:600].rstrip() + "..."
        lines.append(f"[{idx}] {title}: {excerpt}")
    return "\n".join(lines)


def _is_positive(row: InteractionRecord) -> bool:
    if row.status != "complete" or not row.response_text.strip():
        return False
    if row.explicit_rating == -1:
        return False
    return bool(
        row.explicit_rating == 1
        or row.copied_count > 0
        or row.downloaded_count > 0
        or row.human_edited_values is not None
    )


def _is_rejected(row: InteractionRecord) -> bool:
    if row.explicit_rating == -1:
        return True
    if row.regenerated_count > 0 and row.explicit_rating != 1:
        return True
    return row.status != "complete" and bool(row.response_text.strip())


def _preferred_output(row: InteractionRecord) -> str:
    if row.mode == "drafting" and row.human_edited_values:
        return json.dumps(
            {k: scrub_pii(str(v)) for k, v in row.human_edited_values.items()},
            ensure_ascii=False,
        )
    return scrub_pii(row.response_text.strip())


def build_sft_examples(
    records: list[InteractionRecord],
    system_prompt: str = DEFAULT_SYSTEM_PROMPT,
) -> list[dict[str, Any]]:
    """Build Supervised Fine-Tuning (SFT) chat examples from positively signaled turns."""
    examples: list[dict[str, Any]] = []
    for row in records:
        if not _is_positive(row):
            continue
        user_content = scrub_pii(row.prompt.strip())
        ctx = _format_context(row.retrieved_sources)
        if ctx:
            user_content = f"{user_content}\n\n{ctx}"
        assistant_content = _preferred_output(row)
        if not user_content or not assistant_content:
            continue
        examples.append(
            {
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                    {"role": "assistant", "content": assistant_content},
                ],
                "metadata": {
                    "id": row.id,
                    "mode": row.mode,
                    "explicit_rating": row.explicit_rating,
                    "copied_count": row.copied_count,
                    "downloaded_count": row.downloaded_count,
                    "has_human_edit": row.human_edited_values is not None,
                },
            }
        )
    return examples


def build_dpo_pairs(
    records: list[InteractionRecord],
    system_prompt: str = DEFAULT_SYSTEM_PROMPT,
) -> list[dict[str, Any]]:
    """Pair chosen vs rejected responses on matching prompts for Direct Preference Optimization."""
    by_prompt: dict[str, list[InteractionRecord]] = {}
    for row in records:
        key = re.sub(r"\s+", " ", scrub_pii(row.prompt).strip().lower())
        if key:
            by_prompt.setdefault(key, []).append(row)

    pairs: list[dict[str, Any]] = []
    for norm_prompt, group in by_prompt.items():
        chosen_rows = [r for r in group if _is_positive(r)]
        rejected_rows = [r for r in group if _is_rejected(r)]
        if not chosen_rows or not rejected_rows:
            continue
        best = max(
            chosen_rows,
            key=lambda r: (
                1 if r.human_edited_values else 0,
                1 if r.explicit_rating == 1 else 0,
                r.copied_count + r.downloaded_count,
            ),
        )
        worst = min(
            rejected_rows,
            key=lambda r: (
                0 if r.explicit_rating == -1 else 1,
                -r.regenerated_count,
            ),
        )
        chosen_text = _preferred_output(best)
        rejected_text = scrub_pii(worst.response_text.strip())
        if not chosen_text or not rejected_text or chosen_text == rejected_text:
            continue
        ctx = _format_context(best.retrieved_sources)
        full_prompt = f"{system_prompt}\n\nUser: {scrub_pii(best.prompt.strip())}"
        if ctx:
            full_prompt = f"{full_prompt}\n\n{ctx}"
        pairs.append(
            {
                "prompt": full_prompt,
                "chosen": chosen_text,
                "rejected": rejected_text,
                "metadata": {
                    "prompt_key": norm_prompt[:120],
                    "chosen_id": best.id,
                    "rejected_id": worst.id,
                    "mode": best.mode,
                },
            }
        )
    return pairs


async def record_interaction(
    engine: AsyncEngine,
    *,
    user_id: UUID,
    conversation_id: UUID,
    message_id: UUID | None = None,
    mode: str,
    prompt: str,
    rewritten_query: str | None = None,
    retrieved_sources: list[dict[str, Any]] | None = None,
    response_text: str = "",
    draft_values: dict[str, Any] | None = None,
    status: str = "complete",
    failure_stage: str | None = None,
    failure_reason: str | None = None,
    model_name: str | None = None,
    latency_ms: int = 0,
    input_tokens: int = 0,
    output_tokens: int = 0,
) -> None:
    """Persist an assistant turn and its retrieval/verification telemetry safely."""
    with suppress(Exception):
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    """INSERT INTO interaction_logs (
                        id, user_id, conversation_id, message_id, mode, prompt,
                        rewritten_query, retrieved_sources, response_text, draft_values,
                        status, failure_stage, failure_reason, model_name,
                        latency_ms, input_tokens, output_tokens
                    ) VALUES (
                        :id, :user_id, :conversation_id, :message_id, :mode, :prompt,
                        :rewritten_query, CAST(:retrieved_sources AS jsonb), :response_text,
                        CAST(:draft_values AS jsonb), :status, :failure_stage, :failure_reason,
                        :model_name, :latency_ms, :input_tokens, :output_tokens
                    )
                    ON CONFLICT (message_id) DO UPDATE SET
                        rewritten_query = COALESCE(EXCLUDED.rewritten_query, interaction_logs.rewritten_query),
                        retrieved_sources = EXCLUDED.retrieved_sources,
                        response_text = EXCLUDED.response_text,
                        status = EXCLUDED.status,
                        failure_stage = EXCLUDED.failure_stage,
                        failure_reason = EXCLUDED.failure_reason,
                        latency_ms = EXCLUDED.latency_ms,
                        input_tokens = EXCLUDED.input_tokens,
                        output_tokens = EXCLUDED.output_tokens,
                        updated_at = now()"""
                ),
                {
                    "id": uuid4(),
                    "user_id": user_id,
                    "conversation_id": conversation_id,
                    "message_id": message_id,
                    "mode": mode,
                    "prompt": prompt,
                    "rewritten_query": rewritten_query,
                    "retrieved_sources": json.dumps(retrieved_sources or []),
                    "response_text": response_text,
                    "draft_values": json.dumps(draft_values) if draft_values is not None else None,
                    "status": status,
                    "failure_stage": failure_stage,
                    "failure_reason": failure_reason,
                    "model_name": model_name,
                    "latency_ms": max(0, int(latency_ms)),
                    "input_tokens": max(0, int(input_tokens)),
                    "output_tokens": max(0, int(output_tokens)),
                },
            )


async def sync_rating_signal(
    engine: AsyncEngine, message_id: UUID, user_id: UUID, rating: int
) -> None:
    """Mirror explicit message feedback ratings into interaction_logs."""
    with suppress(Exception):
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    """UPDATE interaction_logs
                    SET explicit_rating = :rating, updated_at = now()
                    WHERE message_id = :message_id AND user_id = :user_id"""
                ),
                {"message_id": message_id, "user_id": user_id, "rating": rating},
            )


async def record_draft_edit(
    engine: AsyncEngine, conversation_id: UUID, user_id: UUID, edited_values: dict[str, Any]
) -> None:
    """Capture lawyer corrections to AI-prefilled draft fields."""
    with suppress(Exception):
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    """UPDATE interaction_logs
                    SET human_edited_values = CAST(:values AS jsonb), updated_at = now()
                    WHERE id = (
                        SELECT id FROM interaction_logs
                        WHERE conversation_id = :cid AND user_id = :uid AND mode = 'drafting'
                        ORDER BY created_at DESC LIMIT 1
                    )"""
                ),
                {"cid": conversation_id, "uid": user_id, "values": json.dumps(edited_values)},
            )


def install_learning(
    app: FastAPI,
    engine: AsyncEngine,
    settings: Settings,
    profile: Callable[..., Awaitable[Profile]],
) -> None:
    del settings
    Current = Annotated[Profile, Depends(profile)]

    @app.post("/v1/messages/{message_id}/signal", status_code=204)
    async def record_message_signal(
        message_id: UUID, body: SignalRequest, current: Current
    ) -> Response:
        col = _SIGNAL_COLUMN[body.signal]
        async with engine.begin() as connection:
            exists = await connection.execute(
                text(
                    """SELECT m.id FROM messages m
                    JOIN conversations c ON c.id = m.conversation_id
                    WHERE m.id = :id AND m.role = 'assistant'
                    AND c.user_id = :owner AND c.deleted_at IS NULL"""
                ),
                {"id": message_id, "owner": current.id},
            )
            if exists.scalar_one_or_none() is None:
                raise HTTPException(404, "not_found")
            await connection.execute(
                text(
                    f"""UPDATE interaction_logs
                    SET {col} = {col} + 1, updated_at = now()
                    WHERE message_id = :id AND user_id = :owner"""
                ),
                {"id": message_id, "owner": current.id},
            )
        return Response(status_code=204)

    @app.get("/v1/learning/stats", response_model=LearningStats)
    async def learning_stats(current: Current) -> LearningStats:
        del current
        async with engine.connect() as connection:
            summary = (
                await connection.execute(
                    text(
                        """SELECT
                            count(*) AS total_interactions,
                            count(*) FILTER (WHERE status = 'complete') AS complete_count,
                            count(*) FILTER (WHERE status <> 'complete') AS incomplete_count,
                            count(*) FILTER (WHERE explicit_rating = 1) AS positive_ratings,
                            count(*) FILTER (WHERE explicit_rating = -1) AS negative_ratings,
                            coalesce(sum(copied_count), 0) AS copied_signals,
                            coalesce(sum(downloaded_count), 0) AS downloaded_signals,
                            count(*) FILTER (WHERE human_edited_values IS NOT NULL) AS human_edited_drafts
                        FROM interaction_logs"""
                    )
                )
            ).mappings().one()
            reason_rows = (
                await connection.execute(
                    text(
                        """SELECT coalesce(failure_reason, 'unknown') AS reason, count(*) AS cnt
                        FROM interaction_logs
                        WHERE status <> 'complete'
                        GROUP BY 1"""
                    )
                )
            ).mappings().all()
        return LearningStats(
            total_interactions=int(summary["total_interactions"]),
            complete_count=int(summary["complete_count"]),
            incomplete_count=int(summary["incomplete_count"]),
            positive_ratings=int(summary["positive_ratings"]),
            negative_ratings=int(summary["negative_ratings"]),
            copied_signals=int(summary["copied_signals"]),
            downloaded_signals=int(summary["downloaded_signals"]),
            human_edited_drafts=int(summary["human_edited_drafts"]),
            failure_reasons={str(r["reason"]): int(r["cnt"]) for r in reason_rows},
        )
