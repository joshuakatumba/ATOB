"""M1 worker runtime. Feature jobs are added only in their gated milestones."""

import asyncio
import json
from typing import Any

import boto3
from arq.connections import RedisSettings
from botocore.config import Config
from civis.config import Settings
from civis.logs import configure_logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


def serialize(value: dict[str, Any]) -> bytes:
    return json.dumps(value).encode()


def deserialize(value: bytes) -> dict[str, Any]:
    result: dict[str, Any] = json.loads(value)
    return result


async def health_job(context: dict[str, Any]) -> bool:
    return bool(await context["redis"].ping())


async def cleanup_retention_job(context: dict[str, Any]) -> int:
    settings = Settings.from_env()
    engine = create_async_engine(
        settings.database_url.get_secret_value(), hide_parameters=True
    )
    storage = boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.s3_access_key.get_secret_value(),
        aws_secret_access_key=settings.s3_secret_key.get_secret_value(),
        config=Config(region_name="us-east-1", s3={"addressing_style": "path"}),
    )
    try:
        async with engine.begin() as connection:
            keys = list(
                (
                    await connection.execute(
                        text("""SELECT d.storage_key FROM documents d
                        JOIN users u ON u.id=d.user_id
                        WHERE u.deleted_at IS NOT NULL
                        UNION ALL
                        SELECT up.storage_key FROM uploaded_documents up
                        JOIN users u ON u.id=up.user_id
                        WHERE u.deleted_at IS NOT NULL OR up.expires_at <= now()""")
                    )
                )
                .scalars()
                .all()
            )
            await connection.execute(
                text("""DELETE FROM uploaded_documents
                WHERE expires_at <= now()
                OR user_id IN (SELECT id FROM users WHERE deleted_at IS NOT NULL)""")
            )
            await connection.execute(
                text("""UPDATE subscriptions SET status='expired'
                WHERE status='active' AND expires_at <= now()""")
            )
            await connection.execute(
                text("""DELETE FROM conversation_drafts
                WHERE user_id IN (SELECT id FROM users WHERE deleted_at IS NOT NULL)""")
            )
            await connection.execute(
                text("""UPDATE messages SET document_id=NULL
                WHERE document_id IN (
                    SELECT d.id FROM documents d JOIN users u ON u.id=d.user_id
                    WHERE u.deleted_at IS NOT NULL)""")
            )
            await connection.execute(
                text("""DELETE FROM documents
                WHERE user_id IN (SELECT id FROM users WHERE deleted_at IS NOT NULL)""")
            )
        removed = 0
        for key in keys:
            try:
                await asyncio.to_thread(
                    storage.delete_object, Bucket=settings.s3_bucket, Key=key
                )
                removed += 1
            except Exception:
                pass
        return removed
    finally:
        await engine.dispose()


async def startup(context: dict[str, Any]) -> None:
    configure_logging()


class WorkerSettings:
    functions = [health_job, cleanup_retention_job]
    redis_settings = RedisSettings.from_dsn(Settings.from_env().redis_url.get_secret_value())
    on_startup = startup
    job_serializer = staticmethod(serialize)
    job_deserializer = staticmethod(deserialize)
    log_results = False
    keep_result = 0
    max_jobs = 10
