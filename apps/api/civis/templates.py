"""Small authenticated catalog and owner-scoped server document rendering."""

import asyncio
import base64
import html
import io
import json
import re
import smtplib
import zipfile
from collections.abc import Awaitable, Callable
from datetime import date, datetime
from email.message import EmailMessage
from pathlib import Path
from typing import Annotated, Any, Literal
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

import boto3
from botocore.config import Config
from Crypto.Cipher import AES
from fastapi import Depends, FastAPI, HTTPException, Query, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from civis.config import Settings
from civis.main import Profile, StrictModel


class TemplateField(StrictModel):
    key: str = Field(pattern=r"^[a-z][a-z0-9_]*$", max_length=50)
    label: str = Field(min_length=1, max_length=200)
    example: str = Field(max_length=4000)
    max_length: int = Field(ge=1, le=4000)


class SeedTemplate(StrictModel):
    slug: str = Field(pattern=r"^[a-z0-9-]+$", max_length=200)
    title: str = Field(min_length=1, max_length=200)
    category: str = Field(min_length=1, max_length=100)
    label: Literal["FAKE – development only"]
    fields: list[TemplateField] = Field(min_length=1, max_length=50)
    body: list[list[str]] = Field(max_length=100)


class DocumentSummary(BaseModel):
    id: UUID
    name: str
    filename: str
    conversation_id: UUID | None
    created_at: datetime


class DocumentPage(BaseModel):
    items: list[DocumentSummary]
    next_cursor: UUID | None


class RenderRequest(StrictModel):
    values: dict[str, str] = Field(max_length=50)
    format: Literal["html", "docx"]
    conversation_id: Annotated[UUID, Field(strict=False)] | None = None
    version: int | None = Field(default=None, ge=1)
    draft_revision: int | None = Field(default=None, ge=1)


class Ticket(StrictModel):
    category: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=2000)
    conversation_id: Annotated[UUID, Field(strict=False)] | None = None


class TemplateSummary(BaseModel):
    slug: str
    title: str
    category: str
    is_fake: bool


class TemplateDetail(TemplateSummary):
    version: int
    status: str
    fields: list[TemplateField]


class TemplatePage(BaseModel):
    items: list[TemplateSummary]
    total: int
    next_cursor: int | None


class DocumentResult(BaseModel):
    version: int
    id: UUID
    name: str
    slug: str
    fields: list[TemplateField]
    values: dict[str, str]
    filename: str
    html: str


async def seed_templates(engine: AsyncEngine, settings: Settings) -> None:
    if settings.environment == "production" or not settings.load_fake_seed:
        raise ValueError("Development seed prohibited")
    records = json.loads(
        (Path(__file__).resolve().parents[3] / "content/dev-fake/templates.json").read_text()
    )
    async with engine.begin() as connection:
        for record in records:
            item = SeedTemplate.model_validate(record)
            tid = uuid5(NAMESPACE_URL, "civis:fake-template:" + item.slug)
            vid = uuid5(tid, "1")
            await connection.execute(
                text("""INSERT INTO templates(id,slug,title,category)
                VALUES (:id,:slug,:title,:category) ON CONFLICT (slug) DO NOTHING"""),
                {"id": tid, "slug": item.slug, "title": item.title, "category": item.category},
            )
            actual = await connection.scalar(
                text("SELECT id FROM templates WHERE slug=:slug"), {"slug": item.slug}
            )
            if actual != tid:
                # An owner catalog imported first owns this slug; fixtures must not replace it.
                continue
            await connection.execute(
                text("""INSERT INTO template_versions
                (id,template_id,version,fields,body,is_fake,status)
                VALUES (:id,:template,1,CAST(:fields AS jsonb),CAST(:body AS jsonb),true,'draft')
                ON CONFLICT (template_id,version) DO NOTHING"""),
                {
                    "id": vid,
                    "template": tid,
                    "fields": json.dumps([f.model_dump() for f in item.fields]),
                    "body": json.dumps(item.body),
                },
            )
            await connection.execute(
                text("""INSERT INTO content_provenance(id,source,is_fake,approved,enabled)
                VALUES (:id,'FAKE – development only',true,false,true)
                ON CONFLICT (id) DO NOTHING"""),
                {"id": vid},
            )


def render_parts(
    template: dict[str, Any], values: dict[str, str], *, validate_dates: bool = False
) -> list[tuple[str, list[tuple[str, bool]]]]:
    fields = [TemplateField.model_validate(f) for f in template["fields"]]
    if set(values) != {f.key for f in fields} or any(
        len(values[f.key]) > f.max_length for f in fields
    ):
        raise HTTPException(422, "validation_failed")
    if validate_dates and "d1" in values and "d2" in values:
        d1_val, d2_val = values["d1"].strip(), values["d2"].strip()
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", d1_val) and re.fullmatch(
            r"\d{4}-\d{2}-\d{2}", d2_val
        ):
            try:
                if date.fromisoformat(d2_val) < date.fromisoformat(d1_val):
                    raise HTTPException(422, "validation_failed")
            except ValueError:
                raise HTTPException(422, "validation_failed") from None
    output = []
    for heading, paragraph in template["body"]:
        segments = []
        for index, piece in enumerate(re.split(r"\{(T|[a-z][a-z0-9_]*)\}", paragraph)):
            if index % 2:
                if piece == "T":
                    segments.append((template["title"], True))
                    continue
                if piece not in values:
                    raise HTTPException(503, "internal")
                segments.append((values[piece], True))
            else:
                segments.append((piece, False))
        output.append((heading, segments))
    return output


def render_html(title: str, parts: list[tuple[str, list[tuple[str, bool]]]]) -> str:
    result = "<h3>" + html.escape(title.upper()) + "</h3>"
    for heading, segments in parts:
        result += "<div>" + ("<h4>" + html.escape(heading) + "</h4>" if heading else "") + "<p>"
        for value, filled in segments:
            escaped = html.escape(value)
            result += '<span class="v">' + escaped + "</span>" if filled else escaped
        result += "</p></div>"
    return result


def render_word(title: str, parts: list[tuple[str, list[tuple[str, bool]]]]) -> bytes:
    # Minimal OOXML, all text escaped; same title, headings and segments as preview.
    paragraphs = [title.upper()]
    for heading, segments in parts:
        if heading:
            paragraphs.append(heading)
        paragraphs.append("".join(value for value, _ in segments))
    body = "".join(
        '<w:p><w:r><w:t xml:space="preserve">' + html.escape(p) + "</w:t></w:r></w:p>"
        for p in paragraphs
    )
    file = io.BytesIO()
    with zipfile.ZipFile(file, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            (
                '<?xml version="1.0"?>'
                '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                '<Default Extension="rels" '
                'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                '<Override PartName="/word/document.xml" '
                'ContentType="application/vnd.openxmlformats-officedocument.'
                'wordprocessingml.document.main+xml"/>'
                "</Types>"
            ),
        )
        archive.writestr(
            "_rels/.rels",
            (
                '<?xml version="1.0"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/'
                'officeDocument" Target="word/document.xml"/>'
                "</Relationships>"
            ),
        )
        archive.writestr(
            "word/document.xml",
            (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                "<w:body>"
            )
            + body
            + "<w:sectPr/></w:body></w:document>",
        )
    return file.getvalue()


def encryption_key(settings: Settings) -> bytes:
    if not settings.document_encryption_key:
        raise HTTPException(503, "internal")
    try:
        key = base64.b64decode(settings.document_encryption_key.get_secret_value(), validate=True)
        if len(key) != 32:
            raise ValueError()
        return key
    except ValueError:
        raise HTTPException(503, "internal") from None


def encrypt(settings: Settings, values: dict[str, str]) -> bytes:
    cipher = AES.new(encryption_key(settings), AES.MODE_GCM, nonce=None)
    ciphertext, tag = cipher.encrypt_and_digest(json.dumps(values).encode())
    return bytes(cipher.nonce) + bytes(tag) + bytes(ciphertext)


def decrypt(settings: Settings, data: bytes) -> dict[str, str]:
    cipher = AES.new(encryption_key(settings), AES.MODE_GCM, nonce=data[:16])
    decoded = cipher.decrypt_and_verify(data[32:], data[16:32])
    return dict(json.loads(decoded))


def install_templates(
    app: FastAPI,
    engine: AsyncEngine,
    settings: Settings,
    current_dependency: Callable[..., Awaitable[Profile]],
) -> None:
    Current = Annotated[Profile, Depends(current_dependency)]
    config = Config(
        region_name="us-east-1", signature_version="s3v4", s3={"addressing_style": "path"}
    )
    arguments = {
        "aws_access_key_id": settings.s3_access_key.get_secret_value(),
        "aws_secret_access_key": settings.s3_secret_key.get_secret_value(),
        "config": config,
    }
    storage = boto3.client("s3", endpoint_url=settings.s3_endpoint, **arguments)
    public_storage = boto3.client(
        "s3", endpoint_url=settings.s3_public_endpoint or settings.s3_endpoint, **arguments
    )
    visible = "(v.status='approved' AND NOT v.is_fake)"
    if (
        settings.environment != "production"
        and settings.enable_test_fixtures
        and settings.allow_unapproved_templates
    ):
        visible = "true"
    catalog = (
        """SELECT t.slug,t.title,t.category,v.id AS version_id,v.version,v.fields,v.body,
        v.status,v.is_fake FROM templates t JOIN template_versions v ON v.template_id=t.id
        WHERE """
        + visible
        + """ AND v.version=(SELECT max(v2.version) FROM template_versions v2
        WHERE v2.template_id=t.id AND """
        + visible.replace("v.", "v2.")
        + """) AND EXISTS (SELECT 1 FROM users
        WHERE id=:owner AND deleted_at IS NULL)"""
    )

    async def template_for(slug: str, owner: UUID, version: int | None = None) -> dict[str, Any]:
        query = catalog + " AND t.slug=:slug"
        params: dict[str, Any] = {"owner": owner, "slug": slug}
        if version is not None:
            query = (
                """SELECT t.slug,t.title,t.category,v.id AS version_id,v.version,
                v.fields,v.body,v.status,v.is_fake FROM templates t
                JOIN template_versions v ON v.template_id=t.id
                WHERE t.slug=:slug AND v.version=:version AND """
                + visible
                + """
                AND EXISTS (SELECT 1 FROM users WHERE id=:owner AND deleted_at IS NULL)"""
            )
            params["version"] = version
        async with engine.connect() as connection:
            row = (await connection.execute(text(query), params)).mappings().one_or_none()
        if row is None:
            raise HTTPException(404, "not_found")
        return dict(row)

    async def owned_conversation(connection: Any, conversation: UUID | None, owner: UUID) -> None:
        if conversation is not None and not await connection.scalar(
            text("""SELECT id FROM conversations
            WHERE id=:id AND user_id=:owner AND deleted_at IS NULL"""),
            {"id": conversation, "owner": owner},
        ):
            raise HTTPException(404, "not_found")

    @app.get("/v1/templates/categories")
    async def categories(current: Current) -> dict[str, Any]:
        async with engine.connect() as connection:
            rows = (
                (
                    await connection.execute(
                        text(
                            "SELECT category AS name,count(*) AS count FROM ("
                            + catalog
                            + ") catalog GROUP BY category ORDER BY category"
                        ),
                        {"owner": current.id},
                    )
                )
                .mappings()
                .all()
            )
        return {"items": [dict(r) for r in rows], "total": sum(r["count"] for r in rows)}

    @app.get("/v1/templates", response_model=TemplatePage)
    async def listing(
        current: Current,
        q: str = Query(default="", max_length=200),
        category: str = Query(default="", max_length=100),
        limit: int = Query(default=9, ge=1, le=100),
        cursor: int = Query(default=0, ge=0),
    ) -> TemplatePage:
        query = (
            catalog
            + " AND (:category='' OR t.category=:category) AND strpos(lower(t.title),lower(:q))>0"
        )
        params = {
            "owner": current.id,
            "category": category,
            "q": q,
            "limit": limit,
            "offset": cursor,
        }
        async with engine.connect() as connection:
            total = int(
                await connection.scalar(
                    text("SELECT count(*) FROM (" + query + ") catalog"), params
                )
                or 0
            )
            rows = (
                (
                    await connection.execute(
                        text(
                            query
                            + """ ORDER BY CASE WHEN :category='' THEN CASE t.title
                            WHEN 'Lease Agreement' THEN 0
                            WHEN 'Employment Contract Agreement' THEN 1
                            WHEN 'Court Judgment' THEN 2
                            WHEN 'Real Estate Property Power of Attorney' THEN 3
                            WHEN 'Business Sale Agreement' THEN 4
                            WHEN 'Disciplinary Form' THEN 5
                            ELSE 99 END ELSE 99 END, t.title, t.slug LIMIT :limit OFFSET :offset"""
                        ),
                        params,
                    )
                )
                .mappings()
                .all()
            )
        return TemplatePage(
            items=[TemplateSummary.model_validate(r) for r in rows],
            total=total,
            next_cursor=cursor + limit if cursor + limit < total else None,
        )

    @app.get("/v1/templates/{slug}", response_model=TemplateDetail)
    async def detail(slug: str, current: Current) -> TemplateDetail:
        return TemplateDetail.model_validate(await template_for(slug, current.id))

    @app.post("/v1/templates/{slug}/render")
    async def render(slug: str, body: RenderRequest, current: Current) -> dict[str, Any]:
        template = await template_for(slug, current.id, body.version)
        parts = render_parts(template, body.values, validate_dates=True)
        preview = render_html(template["title"], parts)
        async with engine.connect() as connection:
            await owned_conversation(connection, body.conversation_id, current.id)
        if body.format == "html":
            return {"html": preview}
        from civis.chat import HOURLY

        render_count = int(
            await app.state.redis.eval(HOURLY, 1, f"renders:{current.id}")
        )
        if render_count > 60:
            raise HTTPException(429, "rate_limited", headers={"Retry-After": "3600"})
        filename = re.sub(r"[^A-Za-z0-9]+", "_", template["title"]) + ".docx"
        if body.conversation_id and body.draft_revision is not None:
            async with engine.connect() as connection:
                existing_row = (
                    (
                        await connection.execute(
                            text("""SELECT document_id,encrypted_values FROM conversation_drafts
                            WHERE conversation_id=:cid AND user_id=:owner
                            AND template_version_id=:version AND revision=:revision"""),
                            {
                                "cid": body.conversation_id,
                                "owner": current.id,
                                "version": template["version_id"],
                                "revision": body.draft_revision,
                            },
                        )
                    )
                    .mappings()
                    .one_or_none()
                )
            if (
                existing_row is not None
                and existing_row["document_id"] is not None
                and decrypt(settings, existing_row["encrypted_values"]) == body.values
            ):
                return {
                    "id": str(existing_row["document_id"]),
                    "name": template["title"],
                    "slug": slug,
                    "version": template["version"],
                    "filename": filename,
                    "html": preview,
                    "fields": template["fields"],
                    "values": body.values,
                }
        identifier = uuid4()
        key = f"{current.id}/{identifier}.docx"
        encrypted = encrypt(settings, body.values)
        await asyncio.to_thread(
            storage.put_object,
            Bucket=settings.s3_bucket,
            Key=key,
            Body=render_word(template["title"], parts),
            ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ContentDisposition=f'attachment; filename="{filename}"',
        )
        try:
            async with engine.begin() as connection:
                await owned_conversation(connection, body.conversation_id, current.id)
                await connection.execute(
                    text("""INSERT INTO documents
                    (id,user_id,conversation_id,template_version_id,encrypted_values,storage_key,filename)
                    VALUES (:id,:owner,:conversation,:version,:values,:key,:filename)"""),
                    {
                        "id": identifier,
                        "owner": current.id,
                        "conversation": body.conversation_id,
                        "version": template["version_id"],
                        "values": encrypted,
                        "key": key,
                        "filename": filename,
                    },
                )
                if body.conversation_id and body.draft_revision is not None:
                    snapshot = await connection.scalar(
                        text("""SELECT encrypted_values FROM conversation_drafts
                        WHERE conversation_id=:cid AND user_id=:owner
                        AND template_version_id=:version AND revision=:revision FOR UPDATE"""),
                        {
                            "cid": body.conversation_id,
                            "owner": current.id,
                            "version": template["version_id"],
                            "revision": body.draft_revision,
                        },
                    )
                    if snapshot is None or decrypt(settings, snapshot) != body.values:
                        raise HTTPException(409, "conflict")
                    updated = await connection.execute(
                        text("""UPDATE conversation_drafts
                        SET document_id=:document WHERE conversation_id=:cid AND user_id=:owner
                        AND template_version_id=:version AND revision=:revision
                        RETURNING revision"""),
                        {
                            "document": identifier,
                            "cid": body.conversation_id,
                            "owner": current.id,
                            "version": template["version_id"],
                            "revision": body.draft_revision,
                        },
                    )
                    if updated.scalar_one_or_none() is None:
                        raise HTTPException(409, "conflict")
                if body.conversation_id:
                    await connection.execute(
                        text("""INSERT INTO messages
                        (id,conversation_id,role,content,status,document_id,created_at) VALUES
                        (:user,:conversation,'user','Generate the draft','complete',NULL,now()),
                        (:reply,:conversation,'assistant',:reply_text,'complete',NULL,
                        now()+interval '1 microsecond'),
                        (:file,:conversation,'assistant',:title,'complete',:document,
                        now()+interval '2 microseconds')"""),
                        {
                            "user": uuid4(),
                            "reply": uuid4(),
                            "file": uuid4(),
                            "conversation": body.conversation_id,
                            "reply_text": (
                                f"Here is your completed **{template['title']}**. "
                                "You can open the preview or download the Word document below."
                            ),
                            "title": template["title"],
                            "document": identifier,
                        },
                    )
                    await connection.execute(
                        text("""UPDATE conversations SET updated_at=now(),
                        title=CASE WHEN title='' THEN :title ELSE title END
                        WHERE id=:id AND user_id=:owner"""),
                        {
                            "id": body.conversation_id,
                            "owner": current.id,
                            "title": template["title"],
                        },
                    )
        except BaseException:
            await asyncio.to_thread(storage.delete_object, Bucket=settings.s3_bucket, Key=key)
            raise
        return {
            "id": str(identifier),
            "name": template["title"],
            "slug": slug,
            "version": template["version"],
            "filename": filename,
            "html": preview,
            "fields": template["fields"],
            "values": body.values,
        }

    async def document_for(identifier: UUID, owner: UUID) -> dict[str, Any]:
        async with engine.connect() as connection:
            row = (
                (
                    await connection.execute(
                        text("""SELECT d.*,t.title,t.slug,v.fields,v.body,v.version FROM documents d
                JOIN template_versions v ON v.id=d.template_version_id
                JOIN templates t ON t.id=v.template_id
                WHERE d.id=:id AND d.user_id=:owner"""),
                        {"id": identifier, "owner": owner},
                    )
                )
                .mappings()
                .one_or_none()
            )
        if row is None:
            raise HTTPException(404, "not_found")
        return dict(row)

    @app.get("/v1/documents", response_model=DocumentPage)
    async def documents(
        current: Current,
        limit: int = Query(default=30, ge=1, le=100),
        cursor: UUID | None = None,
    ) -> DocumentPage:
        params: dict[str, Any] = {"owner": current.id, "limit": limit + 1}
        position = ""
        async with engine.connect() as connection:
            if cursor:
                previous = (
                    await connection.execute(
                        text("SELECT created_at FROM documents WHERE id=:id AND user_id=:owner"),
                        {"id": cursor, "owner": current.id},
                    )
                ).scalar_one_or_none()
                if previous is None:
                    raise HTTPException(404, "not_found")
                params.update(cursor=cursor, created=previous)
                position = " AND (d.created_at,d.id) < (:created,:cursor)"
            rows = (
                (
                    await connection.execute(
                        text(
                            "SELECT d.id,t.title AS name,d.filename,d.conversation_id,d.created_at "
                            "FROM documents d JOIN template_versions v "
                            "ON v.id=d.template_version_id "
                            "JOIN templates t ON t.id=v.template_id WHERE d.user_id=:owner"
                            + position
                            + " ORDER BY d.created_at DESC,d.id DESC LIMIT :limit"
                        ),
                        params,
                    )
                )
                .mappings()
                .all()
            )
        return DocumentPage(
            items=[DocumentSummary.model_validate(row) for row in rows[:limit]],
            next_cursor=rows[limit - 1]["id"] if len(rows) > limit else None,
        )

    @app.get("/v1/documents/{identifier}", response_model=DocumentResult)
    async def document(identifier: UUID, current: Current) -> DocumentResult:
        row = await document_for(identifier, current.id)
        values = decrypt(settings, row["encrypted_values"])
        return DocumentResult(
            version=row["version"],
            id=row["id"],
            name=row["title"],
            slug=row["slug"],
            fields=row["fields"],
            values=values,
            filename=row["filename"],
            html=render_html(row["title"], render_parts(row, values)),
        )

    @app.get("/v1/documents/{identifier}/download")
    async def download(identifier: UUID, current: Current) -> RedirectResponse:
        row = await document_for(identifier, current.id)
        url = public_storage.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.s3_bucket, "Key": row["storage_key"]},
            ExpiresIn=300,
        )
        return RedirectResponse(url, headers={"Cache-Control": "no-store"})

    @app.delete("/v1/documents/{identifier}", status_code=204)
    async def delete_document(identifier: UUID, current: Current) -> Response:
        row = await document_for(identifier, current.id)
        async with engine.begin() as connection:
            await connection.execute(
                text("""UPDATE conversation_drafts SET document_id=NULL
                WHERE document_id=:id AND user_id=:owner"""),
                {"id": identifier, "owner": current.id},
            )
            await connection.execute(
                text("""UPDATE messages SET document_id=NULL
                WHERE document_id=:id AND EXISTS (
                    SELECT 1 FROM conversations c
                    WHERE c.id=messages.conversation_id AND c.user_id=:owner)"""),
                {"id": identifier, "owner": current.id},
            )
            deleted = await connection.execute(
                text("DELETE FROM documents WHERE id=:id AND user_id=:owner RETURNING id"),
                {"id": identifier, "owner": current.id},
            )
            if deleted.scalar_one_or_none() is None:
                raise HTTPException(404, "not_found")
        try:
            await asyncio.to_thread(
                storage.delete_object, Bucket=settings.s3_bucket, Key=row["storage_key"]
            )
        except Exception:
            pass
        return Response(status_code=204)

    def send_support_email(ticket_id: UUID, category: str, message: str) -> None:
        if not settings.support_email:
            return
        email = EmailMessage()
        email["Subject"] = f"Civis support [{category}]"
        email["From"] = settings.smtp_from
        email["To"] = settings.support_email
        email.set_content(f"Ticket: {ticket_id}\nCategory: {category}\n\n{message}")
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=5) as smtp:
            if settings.environment == "production":
                smtp.starttls()
            if settings.smtp_username and settings.smtp_password:
                smtp.login(settings.smtp_username, settings.smtp_password.get_secret_value())
            smtp.send_message(email)

    @app.post("/v1/feedback", status_code=204)
    async def feedback(body: Ticket, current: Current) -> Response:
        from civis.chat import HOURLY

        fb_count = int(await app.state.redis.eval(HOURLY, 1, f"feedback:{current.id}"))
        if fb_count > 30:
            raise HTTPException(429, "rate_limited", headers={"Retry-After": "3600"})
        ticket_id = uuid4()
        async with engine.begin() as connection:
            await owned_conversation(connection, body.conversation_id, current.id)
            await connection.execute(
                text("""INSERT INTO feedback_tickets(id,user_id,category,message,conversation_id)
                VALUES (:id,:owner,:category,:message,:conversation_id)"""),
                {"id": ticket_id, "owner": current.id, **body.model_dump()},
            )
        if settings.support_email:
            try:
                await asyncio.to_thread(
                    send_support_email, ticket_id, body.category, body.message
                )
            except Exception:
                pass
        return Response(status_code=204)

    from civis.drafting import install_drafting

    install_drafting(app, engine, settings, current_dependency, template_for)


class OwnerTemplate(StrictModel):
    slug: str = Field(pattern=r"^[a-z0-9-]+$", max_length=200)
    title: str = Field(min_length=1, max_length=200)
    category: str = Field(min_length=1, max_length=100)
    kind: str
    fields: list[TemplateField]
    body: list[list[str]]


class OwnerCatalog(StrictModel):
    approval: Literal["owner-approved-for-testing-2026-11-09"]
    source: Literal["Civis.jsx"]
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    templates: list[OwnerTemplate]


async def import_owner_templates(engine: AsyncEngine, settings: Settings) -> int:
    if not settings.owner_templates_file:
        return 0
    catalog = OwnerCatalog.model_validate_json(Path(settings.owner_templates_file).read_text())
    async with engine.begin() as connection:
        for item in catalog.templates:
            import hashlib

            digest = hashlib.sha256(item.model_dump_json().encode()).hexdigest()
            tid = await connection.scalar(
                text("""INSERT INTO templates(id,slug,title,category)
                VALUES (:id,:slug,:title,:category) ON CONFLICT (slug) DO UPDATE
                SET title=EXCLUDED.title,category=EXCLUDED.category
                RETURNING id"""),
                {
                    "id": uuid5(NAMESPACE_URL, "civis:owner:" + item.slug),
                    "slug": item.slug,
                    "title": item.title,
                    "category": item.category,
                },
            )
            vid = uuid5(tid, digest)
            if await connection.scalar(
                text("SELECT id FROM template_versions WHERE id=:id"), {"id": vid}
            ):
                continue
            await connection.execute(
                text("""INSERT INTO template_versions
                (id,template_id,version,fields,body,is_fake,status)
                SELECT :id,:tid,COALESCE(max(version),0)+1,CAST(:fields AS jsonb),
                CAST(:body AS jsonb),false,'approved' FROM template_versions
                WHERE template_id=:tid"""),
                {
                    "id": vid,
                    "tid": tid,
                    "fields": json.dumps([f.model_dump() for f in item.fields]),
                    "body": json.dumps(item.body),
                },
            )
            await connection.execute(
                text("""INSERT INTO content_provenance(id,source,is_fake,approved,enabled)
                VALUES (:id,:source,false,true,true) ON CONFLICT (id) DO NOTHING"""),
                {"id": vid, "source": catalog.approval + ":" + catalog.source_sha256},
            )
    return len(catalog.templates)
