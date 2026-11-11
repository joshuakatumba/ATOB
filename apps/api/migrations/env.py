import asyncio

from alembic import context
from civis.config import Settings
from sqlalchemy.ext.asyncio import create_async_engine


def migrate(connection):
    context.configure(connection=connection, target_metadata=None)
    with context.begin_transaction():
        context.run_migrations()


async def run():
    engine = create_async_engine(
        Settings.from_env().database_url.get_secret_value(), hide_parameters=True
    )
    async with engine.connect() as connection:
        await connection.run_sync(migrate)
    await engine.dispose()


asyncio.run(run())
