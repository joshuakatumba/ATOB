"""Private PDF/DOCX/TXT uploads, audio transcription, scanning, page extraction and deletion."""

import asyncio
import base64
import hashlib
import json
import re
import struct
import xml.etree.ElementTree as ET
import zipfile
import zlib
from collections.abc import Awaitable, Callable
from datetime import datetime
from io import BytesIO
from typing import Annotated, Any, cast
from uuid import UUID, uuid4

import boto3
import httpx
from botocore.config import Config
from fastapi import Depends, FastAPI, HTTPException, Response
from pydantic import BaseModel, Field
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from civis.config import Settings
from civis.main import Profile, StrictModel
from civis.templates import decrypt, encrypt

DAILY = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then redis.call('EXPIRE', KEYS[1], 86400) end
return count
"""

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_USER_STORAGE_BYTES = 50 * 1024 * 1024
MAX_UPLOAD_PAGES = 30
EICAR_MARKER = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
_PDF_DANGEROUS_TOKENS = (b"/JavaScript", b"/JS", b"/Launch", b"/RichMedia", b"/EmbeddedFiles")
_NIN_PATTERN = re.compile(r"\bC[MF][A-Z0-9]{12}\b")
_SENSITIVE_ID_PATTERN = re.compile(
    r"\b(national identification|republic of uganda.*national id|passport no)\b", re.IGNORECASE
)
_SENSITIVE_BANK_PATTERN = re.compile(
    r"\b(bank statement|statement of account|opening balance.*closing balance)\b", re.IGNORECASE
)


class UploadRequest(StrictModel):
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=120)
    data_base64: str = Field(min_length=4, max_length=15_000_000)
    conversation_id: Annotated[UUID, Field(strict=False)] | None = None


class AudioTranscribeRequest(StrictModel):
    data_base64: str = Field(min_length=4, max_length=15_000_000)
    content_type: str = Field(default="audio/webm", max_length=120)


class AudioTranscribeResponse(BaseModel):
    text: str


class UploadedDocumentOut(BaseModel):
    id: UUID
    conversation_id: UUID | None
    filename: str
    content_type: str
    size_bytes: int
    page_count: int
    quota_cost: int
    warnings: list[str]
    status: str
    created_at: datetime
    expires_at: datetime


class UploadedDocumentsPage(BaseModel):
    items: list[UploadedDocumentOut]


def quota_cost_for_pages(page_count: int) -> int:
    return 1 if page_count <= 15 else 2


async def scan_clamav(host: str, port: int, payload: bytes) -> None:
    reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=10.0)
    try:
        writer.write(b"zINSTREAM\0")
        offset = 0
        while offset < len(payload):
            chunk = payload[offset : offset + 8192]
            writer.write(struct.pack("!I", len(chunk)) + chunk)
            offset += len(chunk)
        writer.write(struct.pack("!I", 0))
        await writer.drain()
        response = await asyncio.wait_for(reader.read(1024), timeout=10.0)
        if b"FOUND" in response:
            raise HTTPException(422, "malware_detected")
    finally:
        writer.close()


def detect_sensitive_warnings(pages: list[dict[str, Any]]) -> list[str]:
    combined = "\n".join(str(p.get("text", "")) for p in pages)
    warnings: list[str] = []
    if _NIN_PATTERN.search(combined) or _SENSITIVE_ID_PATTERN.search(combined):
        warnings.append(
            "This file appears to contain a National ID or passport number. "
            "Upload identity documents only when necessary."
        )
    if _SENSITIVE_BANK_PATTERN.search(combined):
        warnings.append(
            "This file appears to contain a bank statement. "
            "Verify that you are comfortable sharing financial details."
        )
    return warnings


def extract_text_pages(payload: bytes) -> list[dict[str, Any]]:
    if EICAR_MARKER in payload:
        raise HTTPException(422, "malware_detected")
    try:
        decoded = payload.decode("utf-8")
    except UnicodeDecodeError:
        decoded = payload.decode("latin-1", errors="ignore")
    cleaned = decoded.replace("\r\n", "\n").strip()
    if not cleaned:
        return [{"page": 1, "text": ""}]
    pages: list[str] = []
    step = 2400
    for start in range(0, len(cleaned), step):
        pages.append(cleaned[start : start + step])
        if len(pages) >= MAX_UPLOAD_PAGES:
            break
    return [{"page": idx + 1, "text": text_page[:6000]} for idx, text_page in enumerate(pages)]


def extract_docx_pages(payload: bytes) -> list[dict[str, Any]]:
    if EICAR_MARKER in payload:
        raise HTTPException(422, "malware_detected")
    try:
        with zipfile.ZipFile(BytesIO(payload)) as archive:
            names = archive.namelist()
            if "word/document.xml" not in names:
                raise HTTPException(422, "validation_failed")
            total_uncompressed = 0
            for info in archive.infolist():
                lower_name = info.filename.lower()
                if lower_name.endswith(("vbaproject.bin", ".exe", ".dll", ".vbs", ".js", ".bat")):
                    raise HTTPException(422, "malware_detected")
                total_uncompressed += info.file_size
                if total_uncompressed > 25 * 1024 * 1024:
                    raise HTTPException(422, "validation_failed")
            xml_bytes = archive.read("word/document.xml")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(422, "validation_failed") from None

    if b"<!ENTITY" in xml_bytes or b"<!DOCTYPE" in xml_bytes:
        raise HTTPException(422, "malware_detected")
    try:
        root = ET.fromstring(xml_bytes)
    except Exception:
        raise HTTPException(422, "validation_failed") from None

    ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    pages: list[str] = []
    current_lines: list[str] = []
    current_chars = 0

    for para in root.iter(f"{ns}p"):
        texts: list[str] = []
        page_break = False
        for elem in para.iter():
            if elem.tag == f"{ns}t" and elem.text:
                texts.append(elem.text)
            elif elem.tag == f"{ns}lastRenderedPageBreak":
                page_break = True
            elif elem.tag == f"{ns}br" and elem.attrib.get(f"{ns}type") == "page":
                page_break = True
        line = "".join(texts).strip()
        if line:
            current_lines.append(line)
            current_chars += len(line)
        if (page_break or current_chars >= 2400) and current_lines:
            pages.append("\n".join(current_lines))
            current_lines = []
            current_chars = 0
    if current_lines or not pages:
        pages.append("\n".join(current_lines))
    if len(pages) > MAX_UPLOAD_PAGES:
        raise HTTPException(422, "validation_failed")
    return [{"page": idx + 1, "text": text_page[:6000]} for idx, text_page in enumerate(pages)]


def _decode_pdf_hex_string(hex_str: str) -> str:
    raw = re.sub(r"\s+", "", hex_str)
    if not raw:
        return ""
    if len(raw) % 2 == 1:
        raw += "0"
    try:
        data = bytes.fromhex(raw)
    except ValueError:
        return ""
    if len(data) >= 2 and len(data) % 2 == 0 and (data.startswith(b"\xfe\xff") or b"\x00" in data):
        return data.decode("utf-16-be", errors="ignore")
    return data.decode("latin-1", errors="ignore")


def _decode_pdf_text_stream(stream_bytes: bytes) -> str:
    data = stream_bytes
    for candidate in (stream_bytes, stream_bytes.strip(b"\r\n")):
        try:
            data = zlib.decompress(candidate)
            break
        except Exception:
            continue
    decoded = data.decode("latin-1", errors="ignore")
    chunks: list[str] = []
    for match in re.finditer(r"\(([^()\\]*(?:\\.[^()\\]*)*)\)\s*(?:Tj|'|\"\s*)", decoded):
        chunks.append(match.group(1))
    for hex_match in re.finditer(r"<([0-9A-Fa-f\s]+)>\s*Tj", decoded):
        piece = _decode_pdf_hex_string(hex_match.group(1))
        if piece:
            chunks.append(piece)
    for array_match in re.finditer(r"\[(.*?)\]\s*TJ", decoded, re.DOTALL):
        arr = array_match.group(1)
        for token in re.finditer(
            r"\(([^()\\]*(?:\\.[^()\\]*)*)\)|<([0-9A-Fa-f\s]+)>", arr
        ):
            if token.group(1) is not None:
                chunks.append(token.group(1))
            elif token.group(2) is not None:
                piece = _decode_pdf_hex_string(token.group(2))
                if piece:
                    chunks.append(piece)
    cleaned = " ".join(chunks)
    cleaned = (
        cleaned.replace(r"\(", "(")
        .replace(r"\)", ")")
        .replace(r"\n", "\n")
        .replace(r"\r", " ")
        .replace(r"\t", " ")
    )
    return re.sub(r"\s+", " ", cleaned).strip()


def extract_pdf_pages(payload: bytes) -> list[dict[str, Any]]:
    if not payload.startswith(b"%PDF-"):
        raise HTTPException(422, "validation_failed")
    non_stream = re.sub(rb"stream\r?\n.*?\r?\nendstream", b"", payload, flags=re.DOTALL)
    if EICAR_MARKER in payload or any(token in non_stream for token in _PDF_DANGEROUS_TOKENS):
        raise HTTPException(422, "malware_detected")
    page_markers = len(re.findall(rb"/Type\s*/Page\b", payload))
    page_count = max(1, page_markers)
    if page_count > MAX_UPLOAD_PAGES:
        raise HTTPException(422, "validation_failed")
    streams = [
        _decode_pdf_text_stream(m.group(1))
        for m in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", payload, re.DOTALL)
    ]
    non_empty = [s for s in streams if s]
    pages: list[dict[str, Any]] = []
    if len(non_empty) <= page_count:
        for idx in range(page_count):
            text_content = non_empty[idx] if idx < len(non_empty) else ""
            pages.append({"page": idx + 1, "text": text_content[:6000]})
    else:
        per_page = max(1, (len(non_empty) + page_count - 1) // page_count)
        for idx in range(page_count):
            group = non_empty[idx * per_page : (idx + 1) * per_page]
            text_content = "\n".join(group)
            pages.append({"page": idx + 1, "text": text_content[:6000]})
    return pages


def _s3_client(settings: Settings) -> Any:
    config = Config(
        region_name="us-east-1", signature_version="s3v4", s3={"addressing_style": "path"}
    )
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.s3_access_key.get_secret_value(),
        aws_secret_access_key=settings.s3_secret_key.get_secret_value(),
        config=config,
    )


def store_upload_object(
    settings: Settings, key: str, payload: bytes, content_type: str
) -> None:
    _s3_client(settings).put_object(
        Bucket=settings.s3_bucket,
        Key=key,
        Body=payload,
        ContentType=content_type,
    )


def remove_upload_object(settings: Settings, key: str) -> None:
    try:
        _s3_client(settings).delete_object(Bucket=settings.s3_bucket, Key=key)
    except Exception:
        return


async def load_upload_context(
    engine: AsyncEngine,
    settings: Settings,
    owner: UUID,
    attachment_ids: list[UUID],
    conversation_id: UUID | None = None,
) -> tuple[int, str, list[dict[str, str]]]:
    if not attachment_ids and conversation_id is None:
        return 1, "", []
    if not settings.feature_uploads:
        if attachment_ids:
            raise HTTPException(422, "validation_failed")
        return 1, "", []
    async with engine.begin() as connection:
        if attachment_ids and conversation_id is not None:
            for aid in attachment_ids:
                await connection.execute(
                    text("""UPDATE uploaded_documents
                    SET conversation_id = :cid
                    WHERE id = :id AND user_id = :owner AND conversation_id IS NULL"""),
                    {"cid": conversation_id, "id": aid, "owner": owner},
                )
        rows = (
            (
                await connection.execute(
                    text("""SELECT id, conversation_id, filename, page_count, encrypted_pages
                    FROM uploaded_documents
                    WHERE user_id = :owner AND deleted_at IS NULL
                    AND status = 'ready' AND expires_at > now()
                    ORDER BY created_at ASC"""),
                    {"owner": owner},
                )
            )
            .mappings()
            .all()
        )
    by_id = {row["id"]: row for row in rows}
    selected = []
    if attachment_ids:
        for aid in attachment_ids:
            if aid not in by_id:
                raise HTTPException(404, "not_found")
            selected.append(by_id[aid])
        cost = max(quota_cost_for_pages(int(row["page_count"])) for row in selected)
    else:
        selected = [row for row in rows if row["conversation_id"] == conversation_id]
        if not selected:
            return 1, "", []
        cost = 1
    sections: list[str] = []
    citations: list[dict[str, str]] = []
    for row in selected:
        decrypted = decrypt(settings, bytes(row["encrypted_pages"]))
        for page_str, page_text in sorted(decrypted.items(), key=lambda kv: int(kv[0])):
            if page_text:
                page_no = int(page_str)
                sections.append(
                    f"[Uploaded Document: {row['filename']} | Page {page_no}]\n{page_text}"
                )
                citations.append(
                    {
                        "id": f"upload-{row['id']}-p{page_no}",
                        "title": f"{row['filename']} (Page {page_no})",
                        "citation": f"Page {page_no}",
                        "date": "Uploaded document",
                        "url": f"#upload-{row['id']}-p{page_no}",
                        "text": page_text,
                    }
                )
    context_block = "\n\n".join(sections)[:16000]
    return cost, context_block, citations[:10]


def install_uploads(
    app: FastAPI,
    engine: AsyncEngine,
    redis: Redis,
    settings: Settings,
    current_dependency: Callable[..., Awaitable[Profile]],
) -> None:
    Current = Annotated[Profile, Depends(current_dependency)]

    @app.post("/v1/audio/transcribe", response_model=AudioTranscribeResponse)
    async def transcribe_audio(
        body: AudioTranscribeRequest, current: Current
    ) -> AudioTranscribeResponse:
        del current
        if not settings.groq_api_key:
            raise HTTPException(503, "model_unavailable")
        try:
            payload = base64.b64decode(body.data_base64, validate=True)
        except Exception:
            raise HTTPException(422, "validation_failed") from None
        if not payload or len(payload) > MAX_UPLOAD_BYTES:
            raise HTTPException(422, "validation_failed")

        ctype = body.content_type.lower().split(";")[0].strip()
        if "ogg" in ctype:
            filename, mime_type = "audio.ogg", "audio/ogg"
        elif "mp4" in ctype or "m4a" in ctype:
            filename, mime_type = "audio.m4a", "audio/mp4"
        elif "wav" in ctype:
            filename, mime_type = "audio.wav", "audio/wav"
        else:
            filename, mime_type = "audio.webm", "audio/webm"

        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=10.0)) as client:
            response = await client.post(
                settings.groq_base_url.rstrip("/") + "/audio/transcriptions",
                headers={"Authorization": "Bearer " + settings.groq_api_key.get_secret_value()},
                files={"file": (filename, payload, mime_type)},
                data={
                    "model": "whisper-large-v3-turbo",
                    "response_format": "verbose_json",
                    "temperature": "0",
                },
            )
        if response.status_code == 429:
            raise HTTPException(429, "rate_limited")
        if response.status_code != 200:
            raise HTTPException(503, "model_unavailable")
        data = response.json()
        transcript = str(data.get("text") or "").strip()
        segments = data.get("segments") or []
        if segments and all(float(seg.get("no_speech_prob", 0.0)) > 0.85 for seg in segments):
            transcript = ""
        return AudioTranscribeResponse(text=transcript)

    @app.get("/v1/uploads", response_model=UploadedDocumentsPage)
    async def list_uploads(current: Current) -> UploadedDocumentsPage:
        async with engine.connect() as connection:
            rows = (
                (
                    await connection.execute(
                        text("""SELECT id, conversation_id, filename, content_type,
                        size_bytes, page_count, warnings, status, created_at, expires_at
                        FROM uploaded_documents
                        WHERE user_id = :owner AND deleted_at IS NULL AND expires_at > now()
                        ORDER BY created_at DESC LIMIT 50"""),
                        {"owner": current.id},
                    )
                )
                .mappings()
                .all()
            )
        return UploadedDocumentsPage(
            items=[
                UploadedDocumentOut.model_validate(
                    {
                        **dict(row),
                        "quota_cost": quota_cost_for_pages(int(row["page_count"])),
                    }
                )
                for row in rows
            ]
        )

    @app.post("/v1/uploads", response_model=UploadedDocumentOut, status_code=201)
    async def upload_document(body: UploadRequest, current: Current) -> UploadedDocumentOut:
        if not settings.feature_uploads:
            raise HTTPException(403, "uploads_disabled")
        if settings.require_email_verification and not current.verified:
            raise HTTPException(403, "email_unverified")
        try:
            payload = base64.b64decode(body.data_base64, validate=True)
        except Exception:
            raise HTTPException(422, "validation_failed") from None
        if not payload or len(payload) > MAX_UPLOAD_BYTES:
            raise HTTPException(422, "validation_failed")

        lower_name = body.filename.lower().strip()
        is_pdf = lower_name.endswith(".pdf") or body.content_type == "application/pdf"
        is_docx = lower_name.endswith(".docx") or body.content_type in (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ) or (lower_name.endswith(".docx") and body.content_type == "application/octet-stream")
        is_text = lower_name.endswith((".txt", ".md", ".csv")) or body.content_type.startswith(
            ("text/plain", "text/markdown", "text/csv")
        )
        if not (is_pdf or is_docx or is_text):
            raise HTTPException(422, "validation_failed")

        daily_count = int(
            await cast(Awaitable[int], redis.eval(DAILY, 1, f"uploads:daily:{current.id}"))
        )
        if daily_count > 50:
            raise HTTPException(429, "rate_limited")

        async with engine.connect() as connection:
            used_bytes = int(
                await connection.scalar(
                    text("""SELECT coalesce(sum(size_bytes), 0) FROM uploaded_documents
                    WHERE user_id = :owner AND deleted_at IS NULL AND expires_at > now()"""),
                    {"owner": current.id},
                )
                or 0
            )
            if used_bytes + len(payload) > MAX_USER_STORAGE_BYTES:
                raise HTTPException(422, "storage_quota_exceeded")
            if body.conversation_id is not None:
                owns_conv = await connection.scalar(
                    text("""SELECT id FROM conversations
                    WHERE id = :cid AND user_id = :owner AND deleted_at IS NULL"""),
                    {"cid": body.conversation_id, "owner": current.id},
                )
                if not owns_conv:
                    raise HTTPException(404, "not_found")

        if settings.clamav_host:
            await scan_clamav(settings.clamav_host, settings.clamav_port, payload)

        if is_pdf:
            pages = extract_pdf_pages(payload)
        elif is_docx:
            pages = extract_docx_pages(payload)
        else:
            pages = extract_text_pages(payload)
        page_count = len(pages)
        warnings = detect_sensitive_warnings(pages)
        upload_id = uuid4()
        storage_key = f"uploads/{current.id}/{upload_id}"
        sha256_hex = hashlib.sha256(payload).hexdigest()
        encrypted_pages = encrypt(
            settings,
            {str(p["page"]): str(p["text"]) for p in pages},
        )
        normalized_type = (
            "application/pdf"
            if is_pdf
            else (
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                if is_docx
                else "text/plain"
            )
        )
        await asyncio.to_thread(
            store_upload_object, settings, storage_key, payload, normalized_type
        )
        try:
            async with engine.begin() as connection:
                row = (
                    (
                        await connection.execute(
                            text("""INSERT INTO uploaded_documents
                            (id, user_id, conversation_id, filename, content_type,
                            size_bytes, page_count, sha256, storage_key, encrypted_pages,
                            warnings, status)
                            VALUES (:id, :owner, :cid, :filename, :ctype, :size, :pages,
                            :sha, :key, :encrypted, CAST(:warnings AS jsonb), 'ready')
                            RETURNING id, conversation_id, filename, content_type,
                            size_bytes, page_count, warnings, status, created_at, expires_at"""),
                            {
                                "id": upload_id,
                                "owner": current.id,
                                "cid": body.conversation_id,
                                "filename": body.filename,
                                "ctype": normalized_type,
                                "size": len(payload),
                                "pages": page_count,
                                "sha": sha256_hex,
                                "key": storage_key,
                                "encrypted": encrypted_pages,
                                "warnings": json.dumps(warnings),
                            },
                        )
                    )
                    .mappings()
                    .one()
                )
        except Exception:
            await asyncio.to_thread(remove_upload_object, settings, storage_key)
            raise

        return UploadedDocumentOut.model_validate(
            {
                **dict(row),
                "quota_cost": quota_cost_for_pages(page_count),
            }
        )

    @app.delete("/v1/uploads/{upload_id}", status_code=204)
    async def delete_upload(upload_id: UUID, current: Current) -> Response:
        async with engine.begin() as connection:
            row = (
                (
                    await connection.execute(
                        text("""UPDATE uploaded_documents
                        SET deleted_at = now(), status = 'deleted'
                        WHERE id = :id AND user_id = :owner AND deleted_at IS NULL
                        RETURNING storage_key"""),
                        {"id": upload_id, "owner": current.id},
                    )
                )
                .mappings()
                .one_or_none()
            )
            if row is None:
                raise HTTPException(404, "not_found")
        await asyncio.to_thread(remove_upload_object, settings, str(row["storage_key"]))
        return Response(status_code=204)
