from typing import Literal
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


class QuotaDenied(Exception):
    pass


async def mutate(
    engine: AsyncEngine,
    user_id: UUID,
    request_id: UUID,
    kind: Literal["grant", "spend", "refund"],
    amount: int,
    reason: str,
) -> int:
    async with engine.begin() as connection:
        balance = await connection.scalar(
            text("SELECT mutate_quota(:owner, :request, :kind, :amount, :reason)"),
            {
                "owner": user_id,
                "request": request_id,
                "kind": kind,
                "amount": amount,
                "reason": reason,
            },
        )
        if balance is None or balance < 0:
            raise QuotaDenied()
        return int(balance)
