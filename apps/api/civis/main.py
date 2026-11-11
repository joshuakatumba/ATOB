import asyncio
import hashlib
import hmac
import json
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Annotated, Literal, cast
from uuid import UUID, uuid4, uuid5

import boto3
from botocore.config import Config
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from supertokens_python import get_all_cors_headers
from supertokens_python.asyncio import get_user
from supertokens_python.framework.fastapi import get_middleware
from supertokens_python.recipe.emailverification.asyncio import is_email_verified
from supertokens_python.recipe.session import SessionContainer
from supertokens_python.recipe.session.asyncio import revoke_all_sessions_for_user
from supertokens_python.recipe.session.framework.fastapi import verify_session

from civis.auth import configure_auth
from civis.config import Settings
from civis.logs import configure_logging
from civis.model_traces import ModelTracing
from civis.quota import mutate
from civis.telemetry import configure_telemetry, report_failure, request_tracer

RATE_SCRIPT = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
return {count, redis.call('TTL', KEYS[1])}
"""


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Preferences(StrictModel):
    theme: Literal["light", "dark", "system"] = "system"


class ProfilePatch(StrictModel):
    name: str | None = Field(default=None, max_length=200)
    preferences: Preferences | None = None


class Consent(StrictModel):
    document: Literal["terms", "privacy"]
    version: str = Field(min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_.-]+$")


class Profile(BaseModel):
    id: UUID
    email: str
    name: str
    plan: str
    prompts_left: int
    preferences: Preferences
    verified: bool
    verification_required: bool = False
    free_allowance: int
    uploads_enabled: bool = False


class Status(BaseModel):
    status: Literal["ok"] = "ok"


def error(code: str, status: int, retry: int | None = None) -> JSONResponse:
    messages = {
        "unauthenticated": "Sign in to continue.",
        "not_found": "Not found.",
        "validation_failed": "Check the submitted fields.",
        "rate_limited": "Try again later.",
        "internal": "Service unavailable.",
        "model_unavailable": "Response unavailable.",
        "email_unverified": "Verify your email to continue.",
        "quota_exhausted": "No prompts remaining.",
        "uploads_disabled": "Document uploads are currently disabled.",
        "malware_detected": "The uploaded file failed security checks.",
        "storage_quota_exceeded": "Upload storage limit reached.",
        "payment_unavailable": "Payment service is temporarily unavailable.",
    }
    return JSONResponse(
        {"error": {"code": code, "message": messages.get(code, "Request failed.")}},
        status_code=status,
        headers={"Retry-After": str(retry)} if retry else None,
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    configure_logging()
    configure_auth(settings)
    telemetry = configure_telemetry()
    tracer = request_tracer(telemetry)
    model_tracing = ModelTracing()
    engine = create_async_engine(
        settings.database_url.get_secret_value(),
        hide_parameters=True,
        pool_size=10,
        max_overflow=20,
    )
    redis: Redis = Redis.from_url(settings.redis_url.get_secret_value(), decode_responses=True)
    storage = boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.s3_access_key.get_secret_value(),
        aws_secret_access_key=settings.s3_secret_key.get_secret_value(),
        config=Config(
            region_name="us-east-1",
            connect_timeout=2,
            read_timeout=2,
            retries={"max_attempts": 0},
            s3={"addressing_style": "path"},
        ),
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        try:
            from civis.billing import ensure_plans

            await ensure_plans(engine)
            if settings.environment == "production":
                async with engine.connect() as connection:
                    unsafe = await connection.scalar(
                        text("""SELECT EXISTS (
                        SELECT 1 FROM content_provenance WHERE is_fake OR (enabled AND NOT approved)
                    )""")
                    )
                    if unsafe:
                        raise RuntimeError("Unsafe production content state")
            yield
        finally:
            await engine.dispose()
            await redis.aclose()
            await asyncio.to_thread(telemetry.shutdown)
            await asyncio.to_thread(model_tracing.shutdown)

    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.state.engine = engine
    app.state.redis = redis
    app.state.settings = settings
    app.state.model_tracing = model_tracing
    from civis.providers import provider_from_settings

    app.state.model_provider = provider_from_settings(settings)
    from civis.research import LawsAfricaRetriever

    app.state.retriever = (
        LawsAfricaRetriever(settings) if settings.retrieval_provider == "laws_africa" else None
    )
    app.add_middleware(get_middleware())  # type: ignore[no-untyped-call]

    async def rate(key: str, maximum: int, window: int) -> int | None:
        digest = hmac.new(
            settings.log_hmac_key.get_secret_value().encode(), key.encode(), hashlib.sha256
        ).hexdigest()
        count, ttl = await cast(
            Awaitable[list[int]], redis.eval(RATE_SCRIPT, 1, "rate:" + digest, str(window))
        )
        return max(1, int(ttl)) if int(count) > maximum else None

    @app.middleware("http")
    async def limits(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        try:
            ip = request.client.host if request.client else "unknown"
            forwarded = request.headers.get("x-forwarded-for", "")
            if settings.trusted_proxy_hops > 0 and forwarded:
                chain = [part.strip() for part in forwarded.split(",") if part.strip()]
                if chain:
                    index = max(0, len(chain) - settings.trusted_proxy_hops)
                    ip = chain[index]
            retry = await rate("ip:" + ip, 120, 60)
            if retry:
                return error("rate_limited", 429, retry)
            if request.url.path.startswith("/auth/"):
                if request.url.path not in (
                    "/auth/session/refresh",
                    "/auth/signout",
                    "/auth/authorisationurl",
                ):
                    retry = await rate("auth-ip:" + ip, 10, 900)
                    if retry:
                        return error("rate_limited", 429, retry)
                if request.method == "POST":
                    body = await request.body()
                    if len(body) > 16384:
                        return error("validation_failed", 422)
                    try:
                        data = json.loads(body) if body else {}
                        fields = data.get("formFields", []) if isinstance(data, dict) else []
                        for field in fields:
                            if isinstance(field, dict) and field.get("id") == "email":
                                email = field.get("value")
                                if isinstance(email, str):
                                    retry = await rate(
                                        "auth-account:" + email.strip().casefold(), 10, 900
                                    )
                                    if retry:
                                        return error("rate_limited", 429, retry)
                    except (ValueError, TypeError):
                        return error("validation_failed", 422)
            with tracer.start_as_current_span(
                "http.request", record_exception=False, set_status_on_exception=False
            ) as span:
                response = await call_next(request)
                span.set_attribute("http.response.status_code", response.status_code)
            if response.status_code == 401 and request.url.path.startswith("/v1/"):
                return error("unauthenticated", 401)
            return response
        except Exception:
            # Never serialize dependency exceptions, SQL parameters or upstream payloads.
            report_failure()
            return error("internal", 503)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.web_domain],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Content-Type", *get_all_cors_headers()],
    )

    @app.exception_handler(RequestValidationError)
    async def invalid(request: Request, exc: RequestValidationError) -> JSONResponse:
        return error("validation_failed", 422)

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        retry = (
            int(exc.headers["Retry-After"])
            if exc.headers and "Retry-After" in exc.headers
            else None
        )
        return error(str(exc.detail), exc.status_code, retry)

    async def profile(
        auth: Annotated[SessionContainer, Depends(verify_session(check_database=True))],
    ) -> Profile:
        user = await get_user(auth.get_user_id())
        if user is None or not user.emails:
            raise HTTPException(401, "unauthenticated")
        verified = await is_email_verified(auth.get_recipe_user_id(), user.emails[0])
        payload = auth.get_access_token_payload()
        raw_name = payload.get("name")
        default_name = raw_name.strip()[:200] if isinstance(raw_name, str) else ""
        async with engine.begin() as connection:
            await connection.execute(
                text("""INSERT INTO users(id, auth_user_id, email, name)
                VALUES (:id, :auth_id, :email, :name) ON CONFLICT (auth_user_id) DO UPDATE
                SET name = CASE WHEN users.name = '' AND EXCLUDED.name <> ''
                THEN EXCLUDED.name ELSE users.name END"""),
                {
                    "id": uuid4(),
                    "auth_id": auth.get_user_id(),
                    "email": user.emails[0],
                    "name": default_name,
                },
            )
            row = (
                (
                    await connection.execute(
                        text("""SELECT u.id, u.email, u.name, u.preferences,
                        coalesce(lower(p.name), 'free') AS plan_name
                        FROM users u
                        LEFT JOIN plans p ON p.id = u.plan_id
                        WHERE u.auth_user_id=:auth_id AND u.deleted_at IS NULL"""),
                        {"auth_id": auth.get_user_id()},
                    )
                )
                .mappings()
                .one_or_none()
            )
            if row is None:
                raise HTTPException(401, "unauthenticated")
            await connection.execute(
                text("""INSERT INTO usage_balance(user_id) VALUES (:id)
                ON CONFLICT DO NOTHING"""),
                {"id": row["id"]},
            )
        if (verified or not settings.require_email_verification) and settings.free_prompts:
            await mutate(
                engine,
                row["id"],
                uuid5(row["id"], "initial-verified-grant"),
                "grant",
                settings.free_prompts,
                "initial_verified_allowance",
            )
        async with engine.connect() as connection:
            balance = await connection.scalar(
                text("SELECT balance FROM usage_balance WHERE user_id=:id"), {"id": row["id"]}
            )
        return Profile(
            id=row["id"],
            email=str(row["email"]),
            name=str(row["name"]),
            preferences=Preferences.model_validate(row["preferences"]),
            plan=str(row["plan_name"] or "free"),
            prompts_left=int(balance or 0)
            if verified or not settings.require_email_verification
            else 0,
            verified=verified,
            verification_required=settings.require_email_verification,
            free_allowance=settings.free_prompts,
            uploads_enabled=settings.feature_uploads,
        )

    Current = Annotated[Profile, Depends(profile)]

    @app.get("/v1/health", response_model=Status)
    async def health() -> Status:
        return Status()

    @app.get("/v1/ready", response_model=Status)
    async def ready() -> Status:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        await redis.ping()
        await asyncio.to_thread(storage.head_bucket, Bucket=settings.s3_bucket)
        return Status()

    @app.get("/v1/me", response_model=Profile)
    async def me(current: Current) -> Profile:
        return current

    @app.patch("/v1/me", response_model=Profile)
    async def patch_me(body: ProfilePatch, current: Current) -> Profile:
        values = body.model_dump(exclude_none=True)
        assignments = []
        params: dict[str, object] = {"id": current.id}
        if "name" in values:
            assignments.append("name=:name")
            params["name"] = values["name"]
        if "preferences" in values:
            assignments.append("preferences=CAST(:preferences AS jsonb)")
            params["preferences"] = json.dumps(values["preferences"])
        if assignments:
            async with engine.begin() as connection:
                await connection.execute(
                    text(
                        "UPDATE users SET "
                        + ",".join(assignments)
                        + ", updated_at=now() WHERE id=:id AND deleted_at IS NULL"
                    ),
                    params,
                )
        return Profile.model_validate(current.model_dump() | values)

    @app.post("/v1/me/consents", status_code=204)
    async def consent(body: Consent, current: Current) -> Response:
        async with engine.begin() as connection:
            await connection.execute(
                text("""INSERT INTO consents(user_id, document, version)
                SELECT id, :document, :version FROM users WHERE id=:id AND deleted_at IS NULL"""),
                {"id": current.id, **body.model_dump()},
            )
        return Response(status_code=204)

    @app.get("/v1/me/export")
    async def export_account(current: Current) -> dict[str, object]:
        async with engine.connect() as connection:
            consents_rows = (
                (
                    await connection.execute(
                        text("""SELECT document, version, accepted_at FROM consents
                WHERE user_id=:id ORDER BY accepted_at"""),
                        {"id": current.id},
                    )
                )
                .mappings()
                .all()
            )
            conv_rows = (
                (
                    await connection.execute(
                        text("""SELECT id, title, mode, created_at, updated_at
                FROM conversations WHERE user_id=:id AND deleted_at IS NULL
                ORDER BY created_at"""),
                        {"id": current.id},
                    )
                )
                .mappings()
                .all()
            )
            doc_rows = (
                (
                    await connection.execute(
                        text("""SELECT d.id, t.title AS name, d.filename, d.conversation_id,
                d.created_at FROM documents d
                JOIN template_versions v ON v.id=d.template_version_id
                JOIN templates t ON t.id=v.template_id
                WHERE d.user_id=:id ORDER BY d.created_at"""),
                        {"id": current.id},
                    )
                )
                .mappings()
                .all()
            )
        return {
            "profile": current.model_dump(mode="json"),
            "consents": [
                {
                    "document": r["document"],
                    "version": r["version"],
                    "accepted_at": r["accepted_at"].isoformat(),
                }
                for r in consents_rows
            ],
            "conversations": [
                {
                    "id": str(r["id"]),
                    "title": r["title"],
                    "mode": r["mode"],
                    "created_at": r["created_at"].isoformat(),
                    "updated_at": r["updated_at"].isoformat(),
                }
                for r in conv_rows
            ],
            "documents": [
                {
                    "id": str(r["id"]),
                    "name": r["name"],
                    "filename": r["filename"],
                    "conversation_id": str(r["conversation_id"]) if r["conversation_id"] else None,
                    "created_at": r["created_at"].isoformat(),
                }
                for r in doc_rows
            ],
        }

    @app.delete("/v1/me", status_code=204)
    async def delete_account(
        auth: Annotated[SessionContainer, Depends(verify_session(check_database=True))],
        current: Current,
    ) -> Response:
        keys: list[str] = []
        async with engine.begin() as connection:
            locked = await connection.scalar(
                text("""SELECT id FROM users
                WHERE id=:id AND deleted_at IS NULL FOR UPDATE"""),
                {"id": current.id},
            )
            if locked is None:
                raise HTTPException(401, "unauthenticated")
            keys = list(
                (
                    await connection.execute(
                        text("""SELECT storage_key FROM documents WHERE user_id=:id
                        UNION ALL
                        SELECT storage_key FROM uploaded_documents WHERE user_id=:id"""),
                        {"id": current.id},
                    )
                )
                .scalars()
                .all()
            )
            await connection.execute(
                text("DELETE FROM uploaded_documents WHERE user_id=:id"),
                {"id": current.id},
            )
            await connection.execute(
                text("DELETE FROM conversation_drafts WHERE user_id=:id"),
                {"id": current.id},
            )
            await connection.execute(
                text("""UPDATE messages SET document_id=NULL
                WHERE document_id IN (SELECT id FROM documents WHERE user_id=:id)"""),
                {"id": current.id},
            )
            await connection.execute(
                text("DELETE FROM documents WHERE user_id=:id"),
                {"id": current.id},
            )
            await connection.execute(
                text("""UPDATE conversations SET deleted_at=now(), updated_at=now()
                WHERE user_id=:id AND deleted_at IS NULL"""),
                {"id": current.id},
            )
            await connection.execute(
                text("""UPDATE users SET deleted_at=now(), name='', updated_at=now()
                WHERE id=:id"""),
                {"id": current.id},
            )
        for key in keys:
            try:
                await asyncio.to_thread(
                    storage.delete_object, Bucket=settings.s3_bucket, Key=key
                )
            except Exception:
                pass
        await revoke_all_sessions_for_user(auth.get_user_id())
        return Response(status_code=204)

    from civis.billing import install_billing

    install_billing(app, engine, settings, profile)
    from civis.chat import install_chat

    install_chat(app, engine, redis, profile)
    from civis.legal import install_legal

    install_legal(app, settings, profile)
    from civis.templates import install_templates

    install_templates(app, engine, settings, profile)
    from civis.uploads import install_uploads

    install_uploads(app, engine, redis, settings, profile)

    @app.get("/v1/safety/contacts")
    async def safety_contacts(current: Current) -> dict[str, object]:
        del current
        from civis.safety import load_safety_config

        return load_safety_config().model_dump()

    @app.get("/v1/sources/coverage")
    async def sources_coverage(current: Current) -> dict[str, object]:
        del current
        from pathlib import Path

        manifest = Path(__file__).resolve().parents[3] / "content/corpus/laws-africa-uganda.json"
        return dict(json.loads(manifest.read_text()))

    @app.get("/openapi.json", include_in_schema=False)
    async def schema(current: Current) -> dict[str, object]:
        return app.openapi()

    return app
