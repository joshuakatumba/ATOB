"""FAKE – development only. All storage and auth integrations use real local services."""

import secrets
from ipaddress import IPv6Address
from uuid import uuid4

import httpx
import pytest
from civis.config import Settings
from civis.main import create_app
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from supertokens_python.recipe.emailverification.asyncio import (
    create_email_verification_token,
    verify_email_using_token,
)
from supertokens_python.types import RecipeUserId


@pytest.fixture
async def database():
    settings = Settings.from_env()
    engine = create_async_engine(
        settings.database_url.get_secret_value(),
        pool_size=10,
        max_overflow=20,
        hide_parameters=True,
    )
    yield engine
    await engine.dispose()


async def create_fake_user(database):
    owner = uuid4()
    async with database.begin() as connection:
        await connection.execute(
            text("""INSERT INTO users(id, auth_user_id, email, name)
            VALUES (:id, :auth, :email, 'FAKE – development only')"""),
            {"id": owner, "auth": "FAKE-" + str(owner), "email": f"FAKE-{owner}@example.invalid"},
        )
        await connection.execute(
            text("INSERT INTO usage_balance(user_id) VALUES (:id)"), {"id": owner}
        )
    return owner


@pytest.fixture
async def fake_user(database):
    return await create_fake_user(database)


@pytest.fixture
async def other_user(database):
    return await create_fake_user(database)



@pytest.fixture
async def chat_clients():
    settings = Settings.from_env().model_copy(
        update={
            "llm_provider": "fake",
            "enable_test_fixtures": True,
            "load_fake_seed": True,
            "retrieval_provider": "disabled",
            "allow_unapproved_templates": True,
            "llm_model": "FAKE-development",
        }
    )
    app = create_app(settings)
    clients = []
    async with app.router.lifespan_context(app):
        try:
            for _ in range(2):
                client = httpx.AsyncClient(
                    transport=httpx.ASGITransport(
                        app=app, client=(str(IPv6Address(uuid4().int)), 1234)
                    ),
                    base_url="http://localhost:58000",
                    headers={"rid": "emailpassword", "st-auth-mode": "header"},
                )
                clients.append(client)
                signup = await client.post(
                    "/auth/signup",
                    json={
                        "formFields": [
                            {"id": "email", "value": f"FAKE-{uuid4()}@example.invalid"},
                            {"id": "password", "value": ("FAKE-a1-" + secrets.token_urlsafe(32))},
                        ]
                    },
                )
                assert signup.json()["status"] == "OK"
                client.headers["Authorization"] = "Bearer " + signup.headers["st-access-token"]
                client.headers["rid"] = "session"
                token = await create_email_verification_token(
                    "public", RecipeUserId(signup.json()["user"]["id"])
                )
                await verify_email_using_token("public", token.token)
            yield app, clients[0], clients[1]
        finally:
            for client in clients:
                await client.aclose()
