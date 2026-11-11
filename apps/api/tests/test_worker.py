"""FAKE – development only: Arq execution uses real Redis, JSON serialization."""

from uuid import uuid4

from arq.connections import RedisSettings, create_pool
from arq.worker import Worker
from civis.config import Settings
from civis_worker import deserialize, health_job, serialize


async def test_worker_roundtrip():
    redis = await create_pool(
        RedisSettings.from_dsn(Settings.from_env().redis_url.get_secret_value()),
        job_serializer=serialize,
        job_deserializer=deserialize,
    )
    queue = "FAKE-test-" + str(uuid4())
    job = await redis.enqueue_job("health_job", _queue_name=queue)
    assert job is not None
    worker = Worker(
        [health_job],
        redis_pool=redis,
        queue_name=queue,
        burst=True,
        handle_signals=False,
        job_serializer=serialize,
        job_deserializer=deserialize,
        log_results=False,
    )
    try:
        await worker.async_run()
        assert await job.result(timeout=5) is True
    finally:
        await worker.close()
