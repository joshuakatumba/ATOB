"""Commercial UGX subscription plans with Pesapal or Flutterwave checkout and callbacks."""

import hmac
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID, uuid4

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from civis.config import Settings
from civis.main import Profile, StrictModel
from civis.quota import mutate

COMMERCIAL_PLANS = (
    (UUID("00000000-0000-0000-0000-000000000101"), "Starter", 25000, 50, 30),
    (UUID("00000000-0000-0000-0000-000000000102"), "Pro", 75000, 200, 30),
    (UUID("00000000-0000-0000-0000-000000000103"), "Chambers", 250000, 1000, 30),
)


class PlanOut(BaseModel):
    id: UUID
    name: str
    price_ugx: int
    prompts: int
    duration_days: int


class PlansCatalog(BaseModel):
    items: list[PlanOut]
    payment_enabled: bool
    provider: str


class CheckoutRequest(StrictModel):
    plan_id: Annotated[UUID, Field(strict=False)]


class CheckoutResponse(BaseModel):
    transaction_id: UUID
    tx_ref: str
    checkout_url: str
    amount_ugx: int
    currency: str
    status: Literal["pending", "completed", "failed", "reversed"]


class SubscriptionOut(BaseModel):
    id: UUID
    plan_name: str
    prompts: int
    price_ugx: int
    status: str
    starts_at: datetime
    expires_at: datetime


class BillingStatus(BaseModel):
    subscription: SubscriptionOut | None
    prompts_left: int


async def ensure_plans(engine: AsyncEngine) -> None:
    async with engine.begin() as connection:
        for plan_id, name, price_ugx, prompts, duration_days in COMMERCIAL_PLANS:
            await connection.execute(
                text("""INSERT INTO plans (id, name, price_ugx, prompts, duration_days)
                VALUES (:id, :name, :price, :prompts, :days)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    price_ugx = EXCLUDED.price_ugx,
                    prompts = EXCLUDED.prompts,
                    duration_days = EXCLUDED.duration_days,
                    updated_at = now()"""),
                {
                    "id": plan_id,
                    "name": name,
                    "price": price_ugx,
                    "prompts": prompts,
                    "days": duration_days,
                },
            )


def install_billing(
    app: FastAPI,
    engine: AsyncEngine,
    settings: Settings,
    current_dependency: Callable[..., Awaitable[Profile]],
) -> None:
    Current = Annotated[Profile, Depends(current_dependency)]

    def payment_ready() -> bool:
        if settings.payment_provider == "flutterwave":
            return settings.flutterwave_secret_key is not None
        if settings.payment_provider == "pesapal":
            return bool(settings.pesapal_consumer_key and settings.pesapal_consumer_secret)
        return False

    @app.get("/v1/billing/plans", response_model=PlansCatalog)
    async def list_plans(current: Current) -> PlansCatalog:
        del current
        async with engine.connect() as connection:
            rows = (
                (
                    await connection.execute(
                        text("""SELECT id, name, price_ugx, prompts, duration_days
                        FROM plans ORDER BY price_ugx ASC""")
                    )
                )
                .mappings()
                .all()
            )
        return PlansCatalog(
            items=[PlanOut.model_validate(row) for row in rows],
            payment_enabled=payment_ready(),
            provider=settings.payment_provider,
        )

    @app.get("/v1/billing/status", response_model=BillingStatus)
    async def billing_status(current: Current) -> BillingStatus:
        async with engine.connect() as connection:
            sub_row = (
                (
                    await connection.execute(
                        text("""SELECT s.id, p.name AS plan_name, p.prompts, p.price_ugx,
                        s.status, s.starts_at, s.expires_at
                        FROM subscriptions s
                        JOIN plans p ON p.id = s.plan_id
                        WHERE s.user_id = :owner AND s.status = 'active' AND s.expires_at > now()
                        ORDER BY s.expires_at DESC LIMIT 1"""),
                        {"owner": current.id},
                    )
                )
                .mappings()
                .one_or_none()
            )
        return BillingStatus(
            subscription=SubscriptionOut.model_validate(sub_row) if sub_row else None,
            prompts_left=current.prompts_left,
        )

    @app.post("/v1/billing/checkout", response_model=CheckoutResponse, status_code=201)
    async def create_checkout(body: CheckoutRequest, current: Current) -> CheckoutResponse:
        if settings.require_email_verification and not current.verified:
            raise HTTPException(403, "email_unverified")
        if not payment_ready():
            raise HTTPException(503, "payment_unavailable")
        async with engine.connect() as connection:
            plan = (
                (
                    await connection.execute(
                        text("""SELECT id, name, price_ugx, prompts, duration_days
                        FROM plans WHERE id = :id"""),
                        {"id": body.plan_id},
                    )
                )
                .mappings()
                .one_or_none()
            )
        if plan is None:
            raise HTTPException(404, "not_found")
        tx_id = uuid4()
        tx_ref = f"civis-{tx_id}"
        if settings.payment_provider == "pesapal":
            try:
                checkout_url = await pesapal_checkout(tx_ref, plan, current)
            except HTTPException:
                raise
            except Exception:
                raise HTTPException(503, "payment_unavailable") from None
        else:
            checkout_url = await flutterwave_checkout(tx_ref, plan, current)
        async with engine.begin() as connection:
            await connection.execute(
                text("""INSERT INTO payment_transactions
                (id, user_id, plan_id, provider, tx_ref, amount_ugx,
                currency, status, checkout_url)
                VALUES (:id, :owner, :plan, :provider, :ref, :amount,
                'UGX', 'pending', :url)"""),
                {
                    "id": tx_id,
                    "owner": current.id,
                    "plan": plan["id"],
                    "provider": settings.payment_provider,
                    "ref": tx_ref,
                    "amount": plan["price_ugx"],
                    "url": checkout_url,
                },
            )
        return CheckoutResponse(
            transaction_id=tx_id,
            tx_ref=tx_ref,
            checkout_url=checkout_url,
            amount_ugx=plan["price_ugx"],
            currency="UGX",
            status="pending",
        )

    async def flutterwave_checkout(tx_ref: str, plan: Any, current: Profile) -> str:
        if not settings.flutterwave_secret_key:
            raise HTTPException(503, "payment_unavailable")
        payload = {
            "tx_ref": tx_ref,
            "amount": int(plan["price_ugx"]),
            "currency": "UGX",
            "redirect_url": settings.web_domain,
            "payment_options": "mobilemoneyuganda,card",
            "customer": {
                "email": current.email,
                "name": current.name or "Civis User",
            },
            "customizations": {
                "title": f"Civis {plan['name']} Plan",
                "description": f"{plan['prompts']} legal research & drafting prompts (30 days)",
            },
        }
        transport = getattr(app.state, "payment_transport", None)
        try:
            async with httpx.AsyncClient(timeout=20.0, transport=transport) as client:
                secret = settings.flutterwave_secret_key.get_secret_value()
                response = await client.post(
                    f"{settings.flutterwave_base_url.rstrip('/')}/payments",
                    headers={"Authorization": f"Bearer {secret}"},
                    json=payload,
                )
                response.raise_for_status()
                body_json = response.json()
                checkout_url = str(body_json.get("data", {}).get("link") or "")
                if not checkout_url.startswith("https://"):
                    raise ValueError("Invalid checkout link")
        except Exception:
            raise HTTPException(503, "payment_unavailable") from None

        return checkout_url

    async def apply_outcome(
        tx_ref: str,
        event: str,
        status: str,
        provider_tx_id: str,
        currency: str,
        amount: int,
    ) -> dict[str, str]:
        async with engine.begin() as connection:
            tx = (
                (
                    await connection.execute(
                        text("""SELECT t.id, t.user_id, t.plan_id, t.amount_ugx, t.status,
                        p.name AS plan_name, p.prompts, p.duration_days
                        FROM payment_transactions t
                        JOIN plans p ON p.id = t.plan_id
                        WHERE t.tx_ref = :ref FOR UPDATE OF t"""),
                        {"ref": tx_ref},
                    )
                )
                .mappings()
                .one_or_none()
            )
            if tx is None:
                raise HTTPException(404, "not_found")
            if event in ("charge.reversed", "charge.refunded") or status in (
                "reversed",
                "refunded",
            ):
                if tx["status"] == "reversed":
                    return {"status": "already_reversed"}
                await connection.execute(
                    text("""UPDATE payment_transactions
                    SET status = 'reversed', updated_at = now() WHERE id = :id"""),
                    {"id": tx["id"]},
                )
                await connection.execute(
                    text("""UPDATE subscriptions
                    SET status = 'revoked' WHERE transaction_id = :id"""),
                    {"id": tx["id"]},
                )
                await connection.execute(
                    text("""UPDATE users SET plan_id = NULL, updated_at = now()
                    WHERE id = :owner AND plan_id = :plan"""),
                    {"owner": tx["user_id"], "plan": tx["plan_id"]},
                )
                await connection.execute(
                    text("""UPDATE usage_balance
                    SET balance = GREATEST(0, balance - :prompts), updated_at = now()
                    WHERE user_id = :owner"""),
                    {"owner": tx["user_id"], "prompts": tx["prompts"]},
                )
                return {"status": "reversed"}

            if status == "successful" and currency == "UGX" and amount >= int(tx["amount_ugx"]):
                if tx["status"] == "completed":
                    return {"status": "already_processed"}
                await connection.execute(
                    text("""UPDATE payment_transactions
                    SET status = 'completed', provider_tx_id = :ptx, updated_at = now()
                    WHERE id = :id"""),
                    {"id": tx["id"], "ptx": provider_tx_id},
                )
                await connection.execute(
                    text("""INSERT INTO subscriptions
                    (id, user_id, plan_id, transaction_id, status, starts_at, expires_at)
                    VALUES (:id, :owner, :plan, :tx, 'active', now(),
                        now() + make_interval(days => :days))
                    ON CONFLICT (transaction_id) DO NOTHING"""),
                    {
                        "id": uuid4(),
                        "owner": tx["user_id"],
                        "plan": tx["plan_id"],
                        "tx": tx["id"],
                        "days": int(tx["duration_days"]),
                    },
                )
                await connection.execute(
                    text("""UPDATE users SET plan_id = :plan, updated_at = now()
                    WHERE id = :owner"""),
                    {"plan": tx["plan_id"], "owner": tx["user_id"]},
                )
            else:
                await connection.execute(
                    text("""UPDATE payment_transactions
                    SET status = 'failed', provider_tx_id = :ptx, updated_at = now()
                    WHERE id = :id AND status = 'pending'"""),
                    {"id": tx["id"], "ptx": provider_tx_id},
                )
                return {"status": "failed"}

        await mutate(
            engine,
            tx["user_id"],
            tx["id"],
            "grant",
            int(tx["prompts"]),
            f"plan:{str(tx['plan_name']).lower()}",
        )
        return {"status": "completed"}


    @app.post("/v1/billing/webhook/flutterwave")
    async def flutterwave_webhook(
        payload: dict[str, Any],
        verif_hash: Annotated[str | None, Header(alias="verif-hash")] = None,
    ) -> dict[str, str]:
        if not settings.flutterwave_webhook_secret or not verif_hash:
            raise HTTPException(401, "unauthenticated")
        expected = settings.flutterwave_webhook_secret.get_secret_value()
        if not hmac.compare_digest(verif_hash.encode("utf-8"), expected.encode("utf-8")):
            raise HTTPException(401, "unauthenticated")
        event = str(payload.get("event") or "")
        raw_data = payload.get("data")
        data: dict[str, Any] = raw_data if isinstance(raw_data, dict) else payload
        tx_ref = str(data.get("tx_ref") or "")
        status = str(data.get("status") or "").lower()
        provider_tx_id = str(data.get("id") or "")
        currency = str(data.get("currency") or "UGX").upper()
        amount = int(data.get("amount") or 0)
        if not tx_ref:
            raise HTTPException(422, "validation_failed")

        return await apply_outcome(tx_ref, event, status, provider_tx_id, currency, amount)

    async def pesapal_token(client: httpx.AsyncClient) -> str:
        if not settings.pesapal_consumer_key or not settings.pesapal_consumer_secret:
            raise HTTPException(503, "payment_unavailable")
        response = await client.post(
            f"{settings.pesapal_base_url.rstrip('/')}/api/Auth/RequestToken",
            headers={"Accept": "application/json"},
            json={
                "consumer_key": settings.pesapal_consumer_key.get_secret_value(),
                "consumer_secret": settings.pesapal_consumer_secret.get_secret_value(),
            },
        )
        response.raise_for_status()
        token = str(response.json().get("token") or "")
        if not token:
            raise ValueError("Pesapal token missing")
        return token

    async def pesapal_ipn_id(client: httpx.AsyncClient, token: str) -> str:
        cached = settings.pesapal_ipn_id or getattr(app.state, "pesapal_ipn_id", None)
        if cached:
            return str(cached)
        response = await client.post(
            f"{settings.pesapal_base_url.rstrip('/')}/api/URLSetup/RegisterIPN",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            json={
                "url": f"{settings.api_domain.rstrip('/')}/v1/billing/ipn/pesapal",
                "ipn_notification_type": "GET",
            },
        )
        response.raise_for_status()
        ipn_id = str(response.json().get("ipn_id") or "")
        if not ipn_id:
            raise ValueError("Pesapal IPN registration failed")
        app.state.pesapal_ipn_id = ipn_id
        return ipn_id

    async def pesapal_checkout(
        tx_ref: str, plan: Any, current: Profile
    ) -> str:
        transport = getattr(app.state, "payment_transport", None)
        async with httpx.AsyncClient(timeout=20.0, transport=transport) as client:
            token = await pesapal_token(client)
            ipn_id = await pesapal_ipn_id(client, token)
            first, _, last = (current.name or "Civis User").partition(" ")
            response = await client.post(
                f"{settings.pesapal_base_url.rstrip('/')}/api/Transactions/SubmitOrderRequest",
                headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
                json={
                    "id": tx_ref,
                    "currency": "UGX",
                    "amount": int(plan["price_ugx"]),
                    "description": f"Civis {plan['name']} plan, {plan['prompts']} prompts"[:100],
                    "callback_url": f"{settings.web_domain.rstrip('/')}/?payment=pesapal",
                    "notification_id": ipn_id,
                    "billing_address": {
                        "email_address": current.email,
                        "first_name": first[:50] or "Civis",
                        "last_name": last[:50],
                    },
                },
            )
            response.raise_for_status()
            data = response.json()
            url = str(data.get("redirect_url") or "")
            if not url.startswith("https://"):
                raise ValueError("Invalid Pesapal redirect")
            return url

    async def pesapal_verify(order_tracking_id: str) -> dict[str, str]:
        transport = getattr(app.state, "payment_transport", None)
        try:
            async with httpx.AsyncClient(timeout=20.0, transport=transport) as client:
                token = await pesapal_token(client)
                response = await client.get(
                    f"{settings.pesapal_base_url.rstrip('/')}"
                    "/api/Transactions/GetTransactionStatus",
                    params={"orderTrackingId": order_tracking_id},
                    headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
                )
                response.raise_for_status()
                data = response.json()
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(503, "payment_unavailable") from None
        tx_ref = str(data.get("merchant_reference") or "")
        if not tx_ref:
            raise HTTPException(404, "not_found")
        code = int(data.get("status_code") or 0)
        status = {1: "successful", 2: "failed", 3: "reversed"}.get(code, "pending")
        if status == "pending":
            return {"status": "pending"}
        return await apply_outcome(
            tx_ref,
            "",
            status,
            order_tracking_id,
            str(data.get("currency") or "UGX").upper(),
            int(float(data.get("amount") or 0)),
        )

    @app.get("/v1/billing/ipn/pesapal")
    async def pesapal_ipn(
        OrderTrackingId: str = "",  # noqa: N803
        OrderMerchantReference: str = "",  # noqa: N803
        OrderNotificationType: str = "IPNCHANGE",  # noqa: N803
    ) -> dict[str, Any]:
        if settings.payment_provider != "pesapal" or not OrderTrackingId:
            raise HTTPException(404, "not_found")
        await pesapal_verify(OrderTrackingId)
        return {
            "orderNotificationType": OrderNotificationType,
            "orderTrackingId": OrderTrackingId,
            "orderMerchantReference": OrderMerchantReference,
            "status": 200,
        }

    class ConfirmRequest(StrictModel):
        order_tracking_id: Annotated[str, Field(min_length=1, max_length=120)]

    @app.post("/v1/billing/confirm")
    async def confirm_payment(body: ConfirmRequest, current: Current) -> dict[str, Any]:
        if settings.payment_provider != "pesapal":
            raise HTTPException(404, "not_found")
        result = await pesapal_verify(body.order_tracking_id)
        async with engine.connect() as connection:
            balance = (
                await connection.execute(
                    text("SELECT balance FROM usage_balance WHERE user_id = :owner"),
                    {"owner": current.id},
                )
            ).scalar_one_or_none()
        return {"status": result.get("status", "pending"), "prompts_left": int(balance or 0)}
