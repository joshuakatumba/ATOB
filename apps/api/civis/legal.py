from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Annotated, Any, Literal

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from civis.config import Settings


class LegalDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")
    document: Literal["terms", "privacy"]
    version: str = Field(min_length=1, max_length=100)
    text: str = Field(min_length=1)
    consent_label: str = Field(min_length=1)
    is_fake: bool


def legal_documents(settings: Settings) -> list[LegalDocument]:
    path = settings.legal_content_file
    if path is None:
        if (
            settings.enable_test_fixtures
            and settings.load_fake_seed
            and settings.environment != "production"
        ):
            path = str(Path(__file__).resolve().parents[3] / "content/dev-fake/legal.json")
        else:
            candidate = Path(__file__).resolve().parents[3] / "content/owner-supplied/legal.json"
            if candidate.exists():
                path = str(candidate)
    if path is None:
        return []
    documents = TypeAdapter(list[LegalDocument]).validate_json(Path(path).read_text())
    if settings.environment == "production" and any(document.is_fake for document in documents):
        raise ValueError("Fake legal content prohibited in production")
    if not settings.enable_test_fixtures and any(document.is_fake for document in documents):
        raise ValueError("Test legal documents require ENABLE_TEST_FIXTURES=true")
    return documents


def install_legal(
    app: FastAPI, settings: Settings, current_dependency: Callable[..., Awaitable[Any]]
) -> None:
    Current = Annotated[Any, Depends(current_dependency)]
    documents = {document.document: document for document in legal_documents(settings)}

    @app.get("/v1/legal/{document}", response_model=LegalDocument)
    async def legal(document: Literal["terms", "privacy"], current: Current) -> LegalDocument:
        if document not in documents:
            raise HTTPException(404, "not_found")
        return documents[document]
