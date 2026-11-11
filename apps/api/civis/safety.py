"""Jurisdiction, language, emergency referral and adversarial safety checks."""

import re
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SafetyCategory = Literal["language", "jurisdiction", "emergency", "adversarial"]


class SafetyContact(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    phone: str
    toll_free: bool
    scope: str


class SafetyConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: str = Field(min_length=1, max_length=100)
    is_fake: bool
    jurisdiction: str
    supported_languages: list[str]
    notices: dict[SafetyCategory, str]
    contacts: list[SafetyContact]


class SafetyDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    category: SafetyCategory
    message: str


_EMERGENCY_PATTERNS = re.compile(
    r"\b("
    r"kill myself|commit suicide|want to die right now|"
    r"he is beating me right now|she is beating me right now|"
    r"going to kill me tonight|attacking me right now|"
    r"child is being sexually abused right now|in immediate physical danger"
    r")\b",
    re.IGNORECASE,
)

_ADVERSARIAL_PATTERNS = re.compile(
    r"\b("
    r"ignore (all )?(previous|prior|above) instructions|"
    r"disregard your system prompt|reveal your system prompt|"
    r"fabricate a (fake )?(ugandan )?(case|statute|citation|judgment)|"
    r"how (do i|to) forge a (land title|signature|court order|will)|"
    r"how (do i|to) bribe a (judge|magistrate|police officer)|"
    r"how (do i|to) destroy evidence so police"
    r")\b",
    re.IGNORECASE,
)

_FOREIGN_JURISDICTION_PATTERNS = re.compile(
    r"\b("
    r"under kenyan law|in kenya law|laws of kenya|"
    r"under nigerian law|laws of nigeria|"
    r"under tanzanian law|laws of tanzania|"
    r"under south african law|laws of south africa|"
    r"under california law|under texas law|under new york law|under us federal law|"
    r"under uk law|under english and welsh law|under canadian law"
    r")\b",
    re.IGNORECASE,
)

_LUGANDA_SWAHILI_TOKENS = {
    "nnyamba",
    "nsaba",
    "obuyambi",
    "amateeka",
    "omulamuzi",
    "kkooti",
    "ettaka",
    "endagaano",
    "mukama",
    "naomba",
    "msaada",
    "tafadhali",
    "nisaidie",
    "sheria",
    "mahakama",
    "mkataba",
    "akiwa",
    "kuhusu",
    "haki",
    "zangu",
}


@lru_cache(maxsize=1)
def load_safety_config() -> SafetyConfig:
    path = Path(__file__).resolve().parents[3] / "content/owner-supplied/safety.json"
    config = SafetyConfig.model_validate_json(path.read_text())
    if config.is_fake:
        raise ValueError("Fake safety configuration is prohibited")
    return config


def evaluate_safety(content: str) -> SafetyDecision | None:
    text = content.strip()
    if not text:
        return None
    config = load_safety_config()
    if _EMERGENCY_PATTERNS.search(text):
        return SafetyDecision(category="emergency", message=config.notices["emergency"])
    if _ADVERSARIAL_PATTERNS.search(text):
        return SafetyDecision(category="adversarial", message=config.notices["adversarial"])
    lowered = text.lower()
    if _FOREIGN_JURISDICTION_PATTERNS.search(lowered) and "uganda" not in lowered:
        return SafetyDecision(category="jurisdiction", message=config.notices["jurisdiction"])
    words = re.findall(r"[a-zA-Z']+", lowered)
    if words:
        matches = sum(1 for word in words if word in _LUGANDA_SWAHILI_TOKENS)
        if matches >= 2 and matches / len(words) >= 0.25:
            return SafetyDecision(category="language", message=config.notices["language"])
    return None

