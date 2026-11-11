"""M1 development seed: provenance marker only; no legal content is supplied."""

import asyncio
import json
from pathlib import Path
from uuid import UUID

from civis.config import Settings
from pydantic import BaseModel, ConfigDict
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


class FakeSeed(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    label: str
    is_fake: bool
    approved: bool
    enabled: bool


async def seed() -> None:
    settings = Settings.from_env()
    if (
        settings.environment == "production"
        or not settings.enable_test_fixtures
        or not settings.load_fake_seed
    ):
        raise SystemExit("Development seed requires LOAD_FAKE_SEED=true outside production")
    record = FakeSeed.model_validate(
        json.loads(Path("content/dev-fake/provenance.json").read_text())
    )
    if not record.is_fake or record.label != "FAKE – development only" or record.approved:
        raise SystemExit("Invalid development seed")
    engine = create_async_engine(settings.database_url.get_secret_value(), hide_parameters=True)
    try:
        async with engine.begin() as connection:
            await connection.execute(
                text("""INSERT INTO content_provenance
                (id, source, is_fake, approved, enabled)
                VALUES (:id, :label, :is_fake, :approved, :enabled) ON CONFLICT (id) DO NOTHING"""),
                record.model_dump(),
            )
        from civis.templates import seed_templates

        await seed_templates(engine, settings)
    finally:
        await engine.dispose()
    print("Loaded FAKE – development only provenance and template catalog; no legal corpus loaded")


asyncio.run(seed())
