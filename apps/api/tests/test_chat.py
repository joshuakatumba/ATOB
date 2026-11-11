"""FAKE – development only: real database/auth/cache, fake model adapter only."""

from uuid import uuid4

import pytest
from civis.providers import FakeProvider


async def test_conversation_and_feedback_ownership(chat_clients):
    app, first, second = chat_clients
    created = await first.post("/v1/conversations", json={"mode": "research"})
    assert created.status_code == 201
    conversation = created.json()["id"]
    path = "/v1/conversations/" + conversation
    assert (await second.get(path)).status_code == 404
    assert (await second.patch(path, json={"title": "FAKE attack"})).status_code == 404
    assert (await second.delete(path)).status_code == 404
    assert (
        await second.post(
            path + "/messages", json={"content": "FAKE – development only", "mode": "research"}
        )
    ).status_code == 404
    assert (await second.get("/v1/conversations")).json()["items"] == []
    stream = await first.post(
        path + "/messages", json={"content": "FAKE – development only", "mode": "research"}
    )
    assert stream.status_code == 200
    assert "event: meta" in stream.text
    assert "event: delta" in stream.text
    assert "event: citations" in stream.text
    assert "event: done" in stream.text
    stored = (await first.get(path)).json()
    assert [message["status"] for message in stored["messages"]] == ["complete", "complete"]
    assistant = stored["messages"][1]["id"]
    feedback = "/v1/messages/" + assistant + "/feedback"
    assert (await second.post(feedback, json={"rating": 1})).status_code == 404
    assert (await first.post(feedback, json={"rating": 1})).status_code == 204
    assert (await first.post(feedback, json={"rating": -1})).status_code == 204
    assert (await first.patch(path, json={"title": "FAKE renamed"})).json()[
        "title"
    ] == "FAKE renamed"
    assert (await first.delete(path)).status_code == 204
    assert (await first.get(path)).status_code == 404
    assert (await first.get("/v1/conversations")).json()["items"] == []


@pytest.mark.parametrize("failure_after,expected_balance", [(0, 20), (1, 19)])
async def test_failure_persists_incomplete_and_refunds_before_first_delta(
    chat_clients,
    failure_after,
    expected_balance,
):
    app, first, _ = chat_clients
    app.state.model_provider = FakeProvider.from_file(failure_after=failure_after)
    created = await first.post("/v1/conversations", json={"mode": "drafting"})
    path = "/v1/conversations/" + created.json()["id"]
    result = await first.post(
        path + "/messages", json={"content": "FAKE – development only", "mode": "drafting"}
    )
    assert "event: error" in result.text
    assert (await first.get("/v1/me")).json()["prompts_left"] == expected_balance
    stored = (await first.get(path)).json()["messages"]
    assert stored[1]["status"] == "incomplete"
    assert bool(stored[1]["content"]) is bool(failure_after)


async def test_message_schema_and_attachment_rejection(chat_clients):
    _, first, _ = chat_clients
    conversation = (await first.post("/v1/conversations", json={"mode": "research"})).json()["id"]
    path = "/v1/conversations/" + conversation + "/messages"
    for body in [
        {"content": "", "mode": "research"},
        {"content": "x" * 8001, "mode": "research"},
        {"content": "FAKE", "mode": "unknown"},
        {"content": "FAKE", "mode": "research", "attachment_ids": [str(uuid4())]},
    ]:
        assert (await first.post(path, json=body)).status_code == 422
    assert (await first.get("/v1/me")).json()["prompts_left"] == 20
