"""FAKE – development only: real auth/Postgres/Redis, repeatable model outputs."""

import json
import os
from uuid import uuid4

import pytest
from civis.providers import FakeProvider, FakeReply
from civis.quota import mutate
from civis.templates import import_owner_templates
from sqlalchemy import text


async def setup_draft(app, client):
    await import_owner_templates(app.state.engine, app.state.settings)
    template = (await client.get("/v1/templates/lease-agreement")).json()
    cid = (await client.post("/v1/conversations", json={"mode": "drafting"})).json()["id"]
    return template, cid


def answer(app, value):
    app.state.model_provider = FakeProvider(
        FakeReply(label="FAKE – development only", parts=[json.dumps(value)])
    )


async def test_prefill_autosave_reload_and_generation(chat_clients):
    app, client, stranger = chat_clients
    template, cid = await setup_draft(app, client)
    before = (await client.get("/v1/me")).json()["prompts_left"]
    answer(
        app,
        {
            "slug": "lease-agreement",
            "values": {"a": "FAKE Alpha", "b": "FAKE Beta", "amt": "invented amount"},
            "confidence": 0.95,
        },
    )
    result = await client.post(
        "/v1/drafting/prefill",
        json={
            "description": "FAKE test: Lease Agreement between FAKE Alpha and FAKE Beta.",
            "conversation_id": cid,
        },
    )
    assert result.status_code == 200
    data = result.json()
    assert data["prompts_left"] == before - 1
    assert data["values"]["a"] == "FAKE Alpha"
    assert data["values"]["amt"] is None
    assert "amt" in data["missing_fields"]
    draft = (await client.get(f"/v1/conversations/{cid}/draft")).json()
    assert draft["values"]["a"] == "FAKE Alpha" and draft["values"]["amt"] == ""
    assert draft["version"] == template["version"]
    assert (await stranger.get(f"/v1/conversations/{cid}/draft")).status_code == 404
    values = dict(draft["values"], a="FAKE Edited")
    saved = await client.patch(
        f"/v1/conversations/{cid}/draft",
        json={
            "slug": draft["slug"],
            "version": draft["version"],
            "values": values,
            "revision": draft["revision"],
        },
    )
    assert saved.status_code == 200
    revision = saved.json()["revision"]
    assert (await client.get(f"/v1/conversations/{cid}/draft")).json()["values"][
        "a"
    ] == "FAKE Edited"
    assert (
        await client.patch(
            f"/v1/conversations/{cid}/draft",
            json={
                "slug": draft["slug"],
                "version": draft["version"],
                "values": draft["values"],
                "revision": draft["revision"],
            },
        )
    ).status_code == 409
    mismatched = await client.post(
        "/v1/templates/lease-agreement/render",
        json={
            "values": dict(values, a="FAKE Unsaved"),
            "format": "docx",
            "conversation_id": cid,
            "version": draft["version"],
            "draft_revision": revision,
        },
    )
    assert mismatched.status_code == 409
    assert (await client.get(f"/v1/conversations/{cid}/draft")).json()["id"] is None
    generated = await client.post(
        "/v1/templates/lease-agreement/render",
        json={
            "values": values,
            "format": "docx",
            "conversation_id": cid,
            "version": draft["version"],
            "draft_revision": revision,
        },
    )
    assert generated.status_code == 200
    assert (await client.get(f"/v1/conversations/{cid}/draft")).json()["id"] == generated.json()[
        "id"
    ]
    edited = await client.patch(
        f"/v1/conversations/{cid}/draft",
        json={
            "slug": draft["slug"],
            "version": draft["version"],
            "values": dict(values, a="FAKE New"),
            "revision": revision,
        },
    )
    assert edited.status_code == 200 and edited.json()["id"] is None
    async with app.state.engine.connect() as connection:
        raw = await connection.scalar(
            text("SELECT encrypted_values FROM conversation_drafts WHERE conversation_id=:id"),
            {"id": cid},
        )
    assert b"FAKE New" not in bytes(raw)
    assert (await client.get("/v1/me")).json()["prompts_left"] == before - 1


@pytest.mark.parametrize(
    "value",
    [
        {"slug": "missing-template", "values": {}, "confidence": 0.9},
        {"slug": "lease-agreement", "values": {"unknown": "FAKE"}, "confidence": 0.9},
    ],
)
async def test_invalid_prefill_refunds(chat_clients, value):
    app, client, _ = chat_clients
    _, cid = await setup_draft(app, client)
    before = (await client.get("/v1/me")).json()["prompts_left"]
    answer(app, value)
    r = await client.post(
        "/v1/drafting/prefill", json={"description": "FAKE test", "conversation_id": cid}
    )
    assert r.status_code == 503
    assert (await client.get("/v1/me")).json()["prompts_left"] == before
    assert (await client.get(f"/v1/conversations/{cid}/draft")).json() is None


async def test_prefill_ambiguity_and_quota(chat_clients):
    app, client, stranger = chat_clients
    _, cid = await setup_draft(app, client)
    answer(app, {"slug": None, "values": {}, "confidence": 0.1})
    r = await client.post(
        "/v1/drafting/prefill", json={"description": "FAKE ambiguous", "conversation_id": cid}
    )
    assert r.status_code == 200 and r.json()["slug"] is None
    assert (
        await stranger.post(
            "/v1/drafting/prefill", json={"description": "FAKE", "conversation_id": cid}
        )
    ).status_code == 404
    me = (await client.get("/v1/me")).json()
    await mutate(
        app.state.engine, me["id"], uuid4(), "spend", me["prompts_left"], "FAKE quota test"
    )
    assert (
        await client.post(
            "/v1/drafting/prefill", json={"description": "FAKE", "conversation_id": cid}
        )
    ).status_code == 402


@pytest.mark.skipif(
    not (os.getenv("GROQ_API_KEY") and os.getenv("CIVIS_RUN_LIVE_PROVIDER_TESTS") == "1"),
    reason="Live provider checks require explicit opt-in",
)
async def test_live_groq_prefill(chat_clients):
    from civis.config import Settings
    from civis.providers import GroqProvider

    app, client, _ = chat_clients
    _, cid = await setup_draft(app, client)
    app.state.model_provider = GroqProvider(Settings.from_env())
    result = await client.post(
        "/v1/drafting/prefill",
        json={
            "description": (
                "FAKE test. Please prepare a Lease Agreement between FAKE Alpha and FAKE Beta."
            ),
            "conversation_id": cid,
        },
    )
    assert result.status_code == 200
    data = result.json()
    assert data["slug"] == "lease-agreement"
    assert data["values"]["a"] == "FAKE Alpha" and data["values"]["b"] == "FAKE Beta"
    assert data["values"]["amt"] is None
    assert data["draft"]["values"]["a"] == "FAKE Alpha"
