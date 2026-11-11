"""Deployment/test isolation checks. All synthetic content remains confined to tests."""

import subprocess
import sys
from pathlib import Path

import pytest
from civis.config import Settings
from civis.providers import FakeProvider, provider_from_settings


def test_missing_key_does_not_select_a_canned_model():
    settings = Settings.from_env().model_copy(
        update={
            "llm_provider": "disabled",
            "fake_model": False,
            "groq_api_key": None,
            "anthropic_api_key": None,
        }
    )
    assert provider_from_settings(settings) is None


def test_canned_model_requires_explicit_test_opt_in():
    settings = Settings.from_env().model_copy(
        update={
            "llm_provider": "fake",
            "fake_model": True,
            "enable_test_fixtures": False,
        }
    )
    with pytest.raises(ValueError, match="ENABLE_TEST_FIXTURES"):
        provider_from_settings(settings)
    assert isinstance(
        provider_from_settings(settings.model_copy(update={"enable_test_fixtures": True})),
        FakeProvider,
    )


def test_new_environment_defaults_to_real_services(tmp_path):
    script = Path("scripts/dev_env.py").resolve()
    subprocess.run([sys.executable, str(script)], cwd=tmp_path, check=True, capture_output=True)
    value = dict(
        line.split("=", 1) for line in (tmp_path / ".env").read_text().splitlines() if line
    )
    assert value["LLM_PROVIDER"] == "groq"
    assert (
        value["FAKE_MODEL"] == value["LOAD_FAKE_SEED"] == value["ENABLE_TEST_FIXTURES"] == "false"
    )
    assert value["RETRIEVAL_PROVIDER"] == "laws_africa"
    assert "seed.py" not in Path("scripts/dev.sh").read_text()


def test_live_configuration_retains_database_and_deduplicates_secrets(tmp_path):
    script = Path("scripts/configure_live.py").resolve()
    environment = tmp_path / ".env"
    environment.write_text(
        "POSTGRES_PASSWORD=FAKE-original-database-secret\n"
        "GROQ_API_KEY=FAKE-model-secret-123456789\n"
        "LAWS_AFRICA_API_KEY=FAKE-source-secret-123456789\n"
        "LLM_MODEL=FAKE-development\nFAKE_MODEL=true\n"
        "LOAD_FAKE_SEED=true\nENABLE_TEST_FIXTURES=true\n"
    )
    result = subprocess.run(
        [sys.executable, str(script)], cwd=tmp_path, check=True, capture_output=True, text=True
    )
    value = dict(line.split("=", 1) for line in environment.read_text().splitlines() if line)
    assert value["POSTGRES_PASSWORD"] == "FAKE-original-database-secret"
    assert value["LLM_PROVIDER"] == "groq" and value["RETRIEVAL_PROVIDER"] == "laws_africa"
    assert not value["LLM_MODEL"].startswith("FAKE")
    assert (
        value["FAKE_MODEL"] == value["LOAD_FAKE_SEED"] == value["ENABLE_TEST_FIXTURES"] == "false"
    )
    assert "FAKE-model-secret" not in result.stdout and "FAKE-source-secret" not in result.stdout
    assert environment.stat().st_mode & 0o777 == 0o600


async def test_live_history_and_catalog_exclude_diagnostic_records(chat_clients):
    import httpx
    from civis.main import create_app
    from civis.templates import import_owner_templates, seed_templates

    app, client, _ = chat_clients
    await import_owner_templates(app.state.engine, app.state.settings)
    await seed_templates(app.state.engine, app.state.settings)
    cid = (await client.post("/v1/conversations", json={"mode": "research"})).json()["id"]
    response = await client.post(
        f"/v1/conversations/{cid}/messages",
        json={"content": "FAKE user question", "mode": "research"},
    )
    assert "event: done" in response.text
    live_settings = app.state.settings.model_copy(
        update={
            "llm_provider": "disabled",
            "fake_model": False,
            "enable_test_fixtures": False,
            "retrieval_provider": "disabled",
        }
    )
    live = create_app(live_settings)
    async with live.router.lifespan_context(live):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=live),
            base_url="http://localhost:58000",
            headers=dict(client.headers),
        ) as real:
            history = (await real.get(f"/v1/conversations/{cid}")).json()["messages"]
            assert len(history) == 1 and history[0]["role"] == "user"
            catalog = await real.get("/v1/templates?limit=100")
            assert catalog.status_code == 200
            assert catalog.json()["total"] == 62
            assert all(not item["is_fake"] for item in catalog.json()["items"])
            slug = catalog.json()["items"][0]["slug"]
            assert (await real.get("/v1/templates/" + slug)).json()["status"] == "approved"
