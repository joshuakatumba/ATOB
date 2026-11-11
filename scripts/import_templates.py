"""Import owner-supplied templates; approval is recorded from the owner's explicit instruction."""

import asyncio

from civis.config import Settings
from civis.templates import import_owner_templates
from sqlalchemy.ext.asyncio import create_async_engine


async def main() -> None:
    settings = Settings.from_env()
    engine = create_async_engine(settings.database_url.get_secret_value(), hide_parameters=True)
    try:
        count = await import_owner_templates(engine, settings)
        print(f"Imported {count} owner-approved templates")
    finally:
        await engine.dispose()


asyncio.run(main())
