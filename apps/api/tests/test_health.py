"""FAKE – development only: public health endpoints still use real Redis rate limits."""

from ipaddress import IPv6Address
from uuid import uuid4

import httpx
from civis.config import Settings
from civis.main import create_app


async def test_health_and_ready_fail_closed():
    app = create_app(Settings.from_env().model_copy(update={"s3_endpoint": "http://127.0.0.1:1"}))
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app, client=(str(IPv6Address(uuid4().int)), 1234)),
            base_url="http://localhost:58000",
        ) as client:
            assert (await client.get("/v1/health")).json() == {"status": "ok"}
            response = await client.get("/v1/ready")
            assert response.status_code == 503
            assert response.json()["error"]["code"] == "internal"


async def test_ready_with_real_storage():
    app = create_app()
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app, client=(str(IPv6Address(uuid4().int)), 1234)),
            base_url="http://localhost:58000",
        ) as client:
            response = await client.get("/v1/ready")
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}
