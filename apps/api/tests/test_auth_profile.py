"""FAKE – development only: real SuperTokens and Postgres ownership tests."""

import secrets
from ipaddress import IPv6Address
from uuid import UUID, uuid4

import httpx
from civis.main import create_app
from sqlalchemy import text
from supertokens_python.recipe.emailpassword.asyncio import create_reset_password_token
from supertokens_python.recipe.emailverification.asyncio import (
    create_email_verification_token,
    verify_email_using_token,
)
from supertokens_python.types import RecipeUserId


async def test_authentication_verification_ownership_and_consents(database):
    app = create_app()
    async with app.router.lifespan_context(app):
        async with (
            httpx.AsyncClient(
                transport=httpx.ASGITransport(
                    app=app, client=(str(IPv6Address(uuid4().int)), 1234)
                ),
                base_url="http://localhost:58000",
                headers={"rid": "emailpassword", "st-auth-mode": "header"},
            ) as first,
            httpx.AsyncClient(
                transport=httpx.ASGITransport(
                    app=app, client=(str(IPv6Address(uuid4().int)), 1234)
                ),
                base_url="http://localhost:58000",
                headers={"rid": "emailpassword", "st-auth-mode": "header"},
            ) as second,
        ):
            for path, method, body in [
                ("/v1/me", "GET", None),
                ("/v1/me", "PATCH", {"name": "FAKE"}),
                ("/v1/me/consents", "POST", {"document": "terms", "version": "FAKE"}),
            ]:
                response = await first.request(method, path, json=body)
                assert response.status_code == 401
                assert response.json()["error"]["code"] == "unauthenticated"

            ids = []
            for client in (first, second):
                response = await client.post(
                    "/auth/signup",
                    json={
                        "formFields": [
                            {"id": "email", "value": f"FAKE-{uuid4()}@example.invalid"},
                            {"id": "password", "value": ("FAKE-a1-" + secrets.token_urlsafe(32))},
                        ]
                    },
                )
                assert response.status_code == 200
                assert response.json()["status"] == "OK"
                token = response.headers["st-access-token"]
                client.headers["Authorization"] = "Bearer " + token
                client.headers["rid"] = "session"
                initial = await client.get("/v1/me")
                assert initial.status_code == 200
                assert initial.json()["prompts_left"] == 0
                assert initial.json()["verified"] is False
                ids.append(initial.json()["id"])
                recipe_id = RecipeUserId(response.json()["user"]["id"])
                verification = await create_email_verification_token("public", recipe_id)
                assert hasattr(verification, "token")
                await verify_email_using_token("public", verification.token)
                verified = await client.get("/v1/me")
                assert verified.json()["prompts_left"] == 20
                assert (await client.get("/v1/me")).json()["prompts_left"] == 20

            rejected = await first.patch("/v1/me", json={"id": ids[1], "name": "FAKE attack"})
            assert rejected.status_code == 422
            changed = await first.patch(
                "/v1/me",
                json={
                    "name": "FAKE – development only",
                    "preferences": {"theme": "dark"},
                },
            )
            assert changed.status_code == 200
            assert changed.json()["preferences"]["theme"] == "dark"
            assert (await second.get("/v1/me")).json()["name"] == ""
            response = await first.post(
                "/v1/me/consents",
                json={
                    "document": "terms",
                    "version": "FAKE-development-only",
                },
            )
            assert response.status_code == 204
            async with database.connect() as connection:
                count = await connection.scalar(
                    text("SELECT count(*) FROM consents WHERE user_id=:id"), {"id": UUID(ids[1])}
                )
                assert count == 0
            assert (
                await first.post(
                    "/v1/me/consents",
                    json={
                        "document": "terms",
                        "version": "FAKE",
                        "user_id": ids[1],
                    },
                )
            ).status_code == 422


async def test_auth_ip_rate_limit():
    app = create_app()
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app, client=(str(IPv6Address(uuid4().int)), 1234)),
            base_url="http://localhost:58000",
        ) as client:
            for _ in range(10):
                response = await client.post("/auth/signin", json={})
                assert response.status_code != 429
            response = await client.post("/auth/signin", json={})
            assert response.status_code == 429
            assert int(response.headers["Retry-After"]) > 0


async def test_provider_password_reset_login_and_revocation():
    app = create_app()
    email = f"FAKE-{uuid4()}@example.invalid"
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app, client=(str(IPv6Address(uuid4().int)), 1234)),
            base_url="http://localhost:58000",
            headers={"rid": "emailpassword", "st-auth-mode": "header"},
        ) as client:
            signup = await client.post(
                "/auth/signup",
                json={
                    "formFields": [
                        {"id": "email", "value": email},
                        {"id": "password", "value": ("FAKE-a1-" + secrets.token_urlsafe(32))},
                    ]
                },
            )
            assert signup.json()["status"] == "OK"
            requested = await client.post(
                "/auth/user/password/reset/token",
                json={
                    "formFields": [
                        {"id": "email", "value": email},
                    ]
                },
            )
            assert requested.json()["status"] == "OK"
            # Tokens remain provider-owned; never implement reset logic or inspect its tables.
            token = await create_reset_password_token("public", signup.json()["user"]["id"], email)
            assert hasattr(token, "token")
            password = ("FAKE-a1-" + secrets.token_urlsafe(32))
            reset = await client.post(
                "/auth/user/password/reset",
                json={
                    "token": token.token,
                    "formFields": [{"id": "password", "value": password}],
                },
            )
            assert reset.json()["status"] == "OK"
            signin = await client.post(
                "/auth/signin",
                json={
                    "formFields": [
                        {"id": "email", "value": email},
                        {"id": "password", "value": password},
                    ]
                },
            )
            assert signin.json()["status"] == "OK"
            client.headers["Authorization"] = "Bearer " + signin.headers["st-access-token"]
            client.headers["rid"] = "session"
            assert (await client.get("/v1/me")).status_code == 200
            assert (await client.post("/auth/signout")).json()["status"] == "OK"
            assert (await client.get("/v1/me")).status_code == 401


async def test_google_oauth_configuration_and_provider_lookup():
    from os import environ

    import pytest
    from civis.config import Settings
    from pydantic import SecretStr

    base = Settings.from_env()
    with pytest.raises(ValueError, match="Incomplete Google OAuth configuration"):
        env = dict(environ, GOOGLE_CLIENT_ID="FAKE-client-id", GOOGLE_CLIENT_SECRET="")
        Settings.from_env(env)

    app = create_app(
        base.model_copy(
            update={
                "google_client_id": "FAKE-google-client-id",
                "google_client_secret": SecretStr("FAKE-google-client-secret"),
            }
        )
    )
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app, client=(str(IPv6Address(uuid4().int)), 1234)),
            base_url="http://localhost:58000",
            headers={"rid": "thirdparty"},
        ) as client:
            response = await client.get(
                "/auth/authorisationurl",
                params={
                    "thirdPartyId": "google",
                    "redirectURIOnProviderDashboard": "http://localhost:53000/auth/callback/google",
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "OK"
            assert "accounts.google.com" in data["urlWithQueryParams"]
            assert "FAKE-google-client-id" in data["urlWithQueryParams"]
