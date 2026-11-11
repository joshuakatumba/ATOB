"""FAKE – development only: enforce limits with real concurrent requests and real Redis."""

import asyncio
from uuid import UUID, uuid4

from civis.providers import FakeProvider
from civis.quota import mutate


async def test_two_streams_per_account(chat_clients):
    app, client, _ = chat_clients
    app.state.model_provider = FakeProvider.from_file(delay=0.2)
    conversation = (await client.post("/v1/conversations", json={"mode": "research"})).json()["id"]
    path = "/v1/conversations/" + conversation + "/messages"
    results = await asyncio.gather(
        *(
            client.post(
                path,
                json={
                    "content": "FAKE – development only",
                    "mode": "research",
                },
            )
            for _ in range(3)
        )
    )
    assert sorted(response.status_code for response in results) == [200, 200, 429]
    limited = next(response for response in results if response.status_code == 429)
    assert int(limited.headers["Retry-After"]) > 0
    assert (await client.get("/v1/me")).json()["prompts_left"] == 18


async def test_thirty_messages_per_hour(chat_clients, database):
    app, client, _ = chat_clients
    app.state.model_provider = FakeProvider.from_file(delay=0)
    me = (await client.get("/v1/me")).json()
    await mutate(database, UUID(me["id"]), uuid4(), "grant", 20, "FAKE limit test grant")
    conversation = (await client.post("/v1/conversations", json={"mode": "research"})).json()["id"]
    path = "/v1/conversations/" + conversation + "/messages"
    for _ in range(30):
        result = await client.post(
            path, json={"content": "FAKE – development only", "mode": "research"}
        )
        assert result.status_code == 200
        assert "event: done" in result.text
    limited = await client.post(path, json={"content": "FAKE", "mode": "research"})
    assert limited.status_code == 429
    assert int(limited.headers["Retry-After"]) > 0
    assert (await client.get("/v1/me")).json()["prompts_left"] == 10
