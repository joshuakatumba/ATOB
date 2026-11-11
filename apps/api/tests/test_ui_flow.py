"""FAKE – development only: UI contract against real auth, Postgres, Redis and S3."""

import asyncio
import io
import zipfile
from uuid import uuid4

import httpx
from civis.quota import QuotaDenied, mutate
from sqlalchemy import text


async def test_twenty_parallel_spends(database, fake_user):
    await mutate(database, fake_user, uuid4(), "grant", 5, "FAKE integration grant")

    async def spend():
        try:
            await mutate(database, fake_user, uuid4(), "spend", 1, "FAKE integration spend")
            return 1
        except QuotaDenied:
            return 0

    assert sum(await asyncio.gather(*(spend() for _ in range(20)))) == 5


async def test_ui_api_flow(chat_clients):
    app, client, stranger = chat_clients
    from civis.templates import seed_templates

    await seed_templates(app.state.engine, app.state.settings)
    before = (await client.get("/v1/me")).json()
    created = await client.post("/v1/conversations", json={"mode": "research"})
    assert created.status_code == 201
    cid = created.json()["id"]
    reply = await client.post(
        f"/v1/conversations/{cid}/messages",
        json={"mode": "research", "content": "FAKE integration message"},
    )
    assert reply.status_code == 200
    assert "event: delta" in reply.text and "event: done" in reply.text
    assert (await client.get("/v1/me")).json()["prompts_left"] == before["prompts_left"] - 1
    assert len((await client.get(f"/v1/conversations/{cid}")).json()["messages"]) == 2
    assert (await stranger.get(f"/v1/conversations/{cid}")).status_code == 404
    assert any(c["id"] == cid for c in (await client.get("/v1/conversations")).json()["items"])
    categories = (await client.get("/v1/templates/categories")).json()["items"]
    assert len(categories) >= 3
    large = next(c for c in categories if c["count"] > 9)
    page = (
        await client.get("/v1/templates", params={"category": large["name"], "limit": 9})
    ).json()
    assert len(page["items"]) == 9 and page["next_cursor"]
    assert (
        await client.get(
            "/v1/templates", params={"category": large["name"], "cursor": page["next_cursor"]}
        )
    ).json()["items"]
    slug = page["items"][0]["slug"]
    template = (await client.get(f"/v1/templates/{slug}")).json()
    values = {f["key"]: f["example"] for f in template["fields"]}
    values[template["fields"][0]["key"]] = 'FAKE <script>alert("x")</script> & text'
    preview = await client.post(
        f"/v1/templates/{slug}/render", json={"values": values, "format": "html"}
    )
    assert preview.status_code == 200
    assert '<span class="v">' in preview.json()["html"]
    assert "<script>" not in preview.json()["html"] and "&lt;script&gt;" in preview.json()["html"]
    generated = await client.post(
        f"/v1/templates/{slug}/render",
        json={"values": values, "format": "docx", "conversation_id": cid},
    )
    assert generated.status_code == 200
    did = generated.json()["id"]
    assert (await client.get(f"/v1/documents/{did}")).json()["html"] == preview.json()["html"]
    assert (await stranger.get(f"/v1/documents/{did}")).status_code == 404
    assert (await stranger.get(f"/v1/documents/{did}/download")).status_code == 404
    download = await client.get(f"/v1/documents/{did}/download")
    assert download.status_code == 307
    async with httpx.AsyncClient() as storage:
        file = await storage.get(download.headers["location"])
    assert file.status_code == 200
    with zipfile.ZipFile(io.BytesIO(file.content)) as word:
        assert "&lt;script&gt;" in word.read("word/document.xml").decode()
    assert (
        await client.post(
            "/v1/feedback",
            json={"category": "feedback", "message": "FAKE feedback", "conversation_id": cid},
        )
    ).status_code == 204
    assert (await client.patch("/v1/me", json={"preferences": {"theme": "dark"}})).json()[
        "preferences"
    ]["theme"] == "dark"
    assert (await client.get("/v1/legal/privacy")).status_code == 200
    assert (await client.get("/openapi.json")).status_code == 200
    async with app.state.engine.connect() as connection:
        assert await connection.scalar(
            text("SELECT count(*) FROM feedback_tickets WHERE user_id=:id"), {"id": before["id"]}
        )
    assert (await client.post("/auth/signout")).json()["status"] == "OK"
    client.headers.pop("Authorization", None)
    assert (await client.get("/v1/me")).status_code == 401
    assert (await client.get("/v1/templates/categories")).status_code == 401
    assert (await client.get("/v1/legal/privacy")).status_code == 401
