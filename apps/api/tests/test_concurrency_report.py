"""FAKE model/identities: measured app concurrency, not hosted-model capacity."""

import asyncio
import json
import secrets
import time
from contextlib import AsyncExitStack
from ipaddress import IPv6Address
from uuid import uuid4

import httpx
from civis.providers import FakeProvider
from supertokens_python.recipe.emailverification.asyncio import (
    create_email_verification_token,
    verify_email_using_token,
)
from supertokens_python.types import RecipeUserId


async def test_measured_sixteen_streams_across_eight_accounts(chat_clients):
    app, _, _ = chat_clients
    app.state.retriever = None
    app.state.model_provider = FakeProvider.from_file(delay=0.05)
    requests = []
    async with AsyncExitStack() as stack:
        for _ in range(8):
            client = await stack.enter_async_context(
                httpx.AsyncClient(
                    transport=httpx.ASGITransport(
                        app=app, client=(str(IPv6Address(uuid4().int)), 1)
                    ),
                    base_url="http://localhost:58000",
                    headers={"rid": "emailpassword", "st-auth-mode": "header"},
                )
            )
            signup = await client.post(
                "/auth/signup",
                json={
                    "formFields": [
                        {"id": "email", "value": f"FAKE-{uuid4()}@example.invalid"},
                        {"id": "password", "value": "FAKE-a1-" + secrets.token_urlsafe(32)},
                    ]
                },
            )
            assert signup.json()["status"] == "OK"
            verification = await create_email_verification_token(
                "public", RecipeUserId(signup.json()["user"]["id"])
            )
            await verify_email_using_token("public", verification.token)
            client.headers.update(
                {"rid": "session", "Authorization": "Bearer " + signup.headers["st-access-token"]}
            )
            cid = (await client.post("/v1/conversations", json={"mode": "research"})).json()["id"]
            requests.extend([(client, f"/v1/conversations/{cid}/messages")] * 2)

        async def send(client, path):
            started = time.monotonic()
            response = await client.post(
                path, json={"content": "FAKE concurrency marker", "mode": "research"}
            )
            return response, (time.monotonic() - started) * 1000

        results = await asyncio.wait_for(asyncio.gather(*(send(c, p) for c, p in requests)), 30)
        assert all(r.status_code == 200 and "event: done" in r.text for r, _ in results)
        balances = await asyncio.gather(*(c.get("/v1/me") for c in {c for c, _ in requests}))
        assert all(response.json()["prompts_left"] == 18 for response in balances)
        times = sorted(ms for _, ms in results)
        print(
            json.dumps(
                {
                    "benchmark": "FAKE model; real auth/Postgres/Redis",
                    "accounts": 8,
                    "concurrent_requests": len(times),
                    "completed": len(results),
                    "errors": 0,
                    "p50_ms": round(times[len(times) // 2]),
                    "p95_ms": round(times[-1]),
                }
            )
        )
