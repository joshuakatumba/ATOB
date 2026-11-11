"""FAKE – development only: production must detect loaded content despite disabled seed flags."""

from uuid import uuid4

import pytest
from civis.config import Settings
from civis.main import create_app
from sqlalchemy import text


@pytest.mark.parametrize("fake,approved,enabled", [(True, True, False), (False, False, True)])
async def test_production_refuses_loaded_unsafe_content(database, fake, approved, enabled):
    marker = uuid4()
    async with database.begin() as connection:
        await connection.execute(
            text("""INSERT INTO content_provenance
            (id, source, is_fake, approved, enabled) VALUES
            (:id, 'FAKE – development only', :fake, :approved, :enabled)"""),
            {"id": marker, "fake": fake, "approved": approved, "enabled": enabled},
        )
    settings = Settings.from_env().model_copy(
        update={
            "environment": "production",
            "llm_provider": "disabled",
            "fake_model": False,
            "enable_test_fixtures": False,
            "load_fake_seed": False,
            "api_domain": "https://api.example.invalid",
            "web_domain": "https://web.example.invalid",
        }
    )
    app = create_app(settings)
    try:
        with pytest.raises(RuntimeError, match="Unsafe production content state"):
            async with app.router.lifespan_context(app):
                pytest.fail("Production started with unsafe content")
    finally:
        async with database.begin() as connection:
            await connection.execute(
                text("DELETE FROM content_provenance WHERE id=:id"), {"id": marker}
            )
