"""FAKE – development only: public owner-content mechanism and production refusal."""

import pytest
from civis.config import Settings
from civis.legal import legal_documents


async def test_test_documents_require_explicit_fixture_mode(chat_clients):
    _, client, _ = chat_clients
    for document in ("terms", "privacy"):
        result = await client.get("/v1/legal/" + document)
        assert result.status_code == 200
        assert result.json()["is_fake"] is True
        assert result.json()["text"] == "FAKE – development only"

    settings = Settings.from_env().model_copy(
        update={
            "enable_test_fixtures": False,
            "legal_content_file": "content/dev-fake/legal.json",
        }
    )
    with pytest.raises(ValueError, match="ENABLE_TEST_FIXTURES"):
        legal_documents(settings)


def test_fake_owner_content_file_refused_in_production():
    settings = Settings.from_env().model_copy(
        update={
            "environment": "production",
            "legal_content_file": "content/dev-fake/legal.json",
        }
    )
    with pytest.raises(ValueError, match="Fake legal content"):
        legal_documents(settings)
