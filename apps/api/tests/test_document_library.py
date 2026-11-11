"""FAKE identities; supplied templates, real auth and private storage."""

from uuid import uuid4

from civis.templates import import_owner_templates


async def test_document_library_is_owned_and_validates_paging(chat_clients):
    app, client, other = chat_clients
    await import_owner_templates(app.state.engine, app.state.settings)
    template = (await client.get("/v1/templates/lease-agreement")).json()
    values = {field["key"]: "FAKE library value" for field in template["fields"]}
    result = await client.post(
        "/v1/templates/lease-agreement/render",
        json={"format": "docx", "values": values},
    )
    assert result.status_code == 200
    identifier = result.json()["id"]
    page = await client.get("/v1/documents?limit=1")
    assert page.status_code == 200 and page.json()["items"][0]["id"] == identifier
    assert identifier not in str((await other.get("/v1/documents")).json())
    assert (await other.get("/v1/documents", params={"cursor": identifier})).status_code == 404
    assert (await client.get("/v1/documents?limit=0")).status_code == 422
    assert (await other.delete(f"/v1/documents/{identifier}")).status_code == 404
    assert (await client.delete(f"/v1/documents/{identifier}")).status_code == 204
    assert (await client.get(f"/v1/documents/{identifier}")).status_code == 404


async def test_document_generation_idempotency_and_field_validation(chat_clients):
    app, client, _ = chat_clients
    await import_owner_templates(app.state.engine, app.state.settings)
    template = (await client.get("/v1/templates/lease-agreement")).json()
    values = {field["key"]: "FAKE valid value" for field in template["fields"]}
    bad_dates = dict(values, d1="2026-12-10", d2="2026-12-01")
    assert (
        await client.post(
            "/v1/templates/lease-agreement/render",
            json={"format": "docx", "values": bad_dates},
        )
    ).status_code == 422
    cid = (await client.post("/v1/conversations", json={"mode": "drafting"})).json()["id"]
    saved = (
        await client.patch(
            f"/v1/conversations/{cid}/draft",
            json={
                "slug": "lease-agreement",
                "version": template["version"],
                "values": values,
                "revision": 0,
            },
        )
    ).json()
    first = await client.post(
        "/v1/templates/lease-agreement/render",
        json={
            "format": "docx",
            "values": values,
            "conversation_id": cid,
            "version": saved["version"],
            "draft_revision": saved["revision"],
        },
    )
    second = await client.post(
        "/v1/templates/lease-agreement/render",
        json={
            "format": "docx",
            "values": values,
            "conversation_id": cid,
            "version": saved["version"],
            "draft_revision": saved["revision"],
        },
    )
    assert first.status_code == 200 and second.status_code == 200
    assert first.json()["id"] == second.json()["id"]


async def test_account_export_deletion_and_proxy_controls(chat_clients):
    app, client, other = chat_clients
    consent = await client.post("/v1/me/consents", json={"document": "terms", "version": "FAKE-1"})
    assert consent.status_code == 204
    cid = (await client.post("/v1/conversations", json={"mode": "research"})).json()["id"]
    req_id = str(uuid4())
    msg = await client.post(
        f"/v1/conversations/{cid}/messages",
        json={"content": "FAKE idempotency check", "mode": "research", "request_id": req_id},
    )
    assert msg.status_code == 200
    exported = (await client.get("/v1/me/export")).json()
    assert exported["profile"]["email"].lower().startswith("fake-")
    assert any(c["version"] == "FAKE-1" for c in exported["consents"])
    assert any(c["id"] == cid for c in exported["conversations"])
    deleted = await client.delete("/v1/me")
    assert deleted.status_code == 204
    assert (await client.get("/v1/me")).status_code == 401
    assert (await other.get("/v1/me")).status_code == 200
