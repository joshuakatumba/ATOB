"""FAKE identities only. Exercise the pinned auth provider, never its database tables."""

import secrets

from sqlalchemy import text
from supertokens_python.recipe.emailpassword.asyncio import create_reset_password_token


async def test_provider_reset_token_is_single_use_and_changes_login(chat_clients):
    app, client, _ = chat_clients
    profile = (await client.get("/v1/me")).json()
    async with app.state.engine.connect() as connection:
        auth_id = await connection.scalar(
            text("SELECT auth_user_id FROM users WHERE id=:id"), {"id": profile["id"]}
        )
    token = await create_reset_password_token("public", auth_id, profile["email"])
    password = "FAKE-a1-" + secrets.token_urlsafe(32)
    body = {"token": token.token, "formFields": [{"id": "password", "value": password}]}
    result = await client.post(
        "/auth/user/password/reset", json=body, headers={"rid": "emailpassword"}
    )
    assert result.json()["status"] == "OK"
    reused = await client.post(
        "/auth/user/password/reset", json=body, headers={"rid": "emailpassword"}
    )
    assert reused.json()["status"] == "RESET_PASSWORD_INVALID_TOKEN_ERROR"
    login = await client.post(
        "/auth/signin",
        headers={"rid": "emailpassword"},
        json={
            "formFields": [
                {"id": "email", "value": profile["email"]},
                {"id": "password", "value": password},
            ]
        },
    )
    assert login.json()["status"] == "OK"
    assert profile["verification_required"] is app.state.settings.require_email_verification


async def test_invalid_verification_link_never_verifies_an_account(chat_clients):
    _, client, _ = chat_clients
    result = await client.post(
        "/auth/user/email/verify",
        json={"token": "FAKE-invalid-token"},
        headers={"rid": "emailverification"},
    )
    assert result.json()["status"] == "EMAIL_VERIFICATION_INVALID_TOKEN_ERROR"
