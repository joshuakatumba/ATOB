"""FAKE – development only: ledger safety tests using real Postgres."""

import asyncio
from uuid import uuid4

import pytest
from civis.quota import QuotaDenied, mutate
from sqlalchemy import text


async def test_100_requests_balance_five(database, fake_user):
    await mutate(database, fake_user, uuid4(), "grant", 5, "FAKE test grant")

    async def spend():
        try:
            await mutate(database, fake_user, uuid4(), "spend", 1, "FAKE test spend")
            return True
        except QuotaDenied:
            return False

    assert sum(await asyncio.gather(*(spend() for _ in range(100)))) == 5
    async with database.connect() as connection:
        assert (
            await connection.scalar(
                text("SELECT balance FROM usage_balance WHERE user_id=:id"), {"id": fake_user}
            )
            == 0
        )


async def test_duplicate_spend_and_refund(database, fake_user):
    await mutate(database, fake_user, uuid4(), "grant", 5, "FAKE test grant")
    request = uuid4()
    results = await asyncio.gather(
        *(mutate(database, fake_user, request, "spend", 1, "FAKE test spend") for _ in range(20))
    )
    assert results == [4] * 20
    results = await asyncio.gather(
        *(mutate(database, fake_user, request, "refund", 1, "FAKE test refund") for _ in range(20))
    )
    assert results == [5] * 20


async def test_refund_requires_owned_matching_spend(database, fake_user):
    with pytest.raises(QuotaDenied):
        await mutate(database, fake_user, uuid4(), "refund", 1, "FAKE invalid refund")


async def test_request_cannot_be_reused_by_other_owner(database, fake_user, other_user):
    request = uuid4()
    await mutate(database, fake_user, request, "grant", 1, "FAKE grant")
    with pytest.raises(QuotaDenied):
        await mutate(database, other_user, request, "grant", 1, "FAKE grant")
