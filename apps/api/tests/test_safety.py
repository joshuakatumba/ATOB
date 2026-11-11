"""FAKE – development only: configuration and log safety."""

import json
import logging

import pytest
from civis.config import Settings
from civis.logs import SafeFormatter


@pytest.mark.parametrize(
    "key",
    [
        "ALLOW_UNAPPROVED_TEMPLATES",
        "LOAD_FAKE_SEED",
        "FAKE_LEGAL_TEXT",
    ],
)
def test_production_rejects_fake_flags(key):
    with pytest.raises(ValueError, match="production"):
        Settings.from_env({"APP_ENV": "production", key: "true"})


def test_production_requires_secrets():
    with pytest.raises(ValueError, match="production"):
        Settings.from_env({"APP_ENV": "production"})


def test_logs_discard_untrusted_messages_and_extra():
    record = logging.LogRecord(
        "FAKE", logging.ERROR, "", 0, "FAKE private email@example.invalid", (), None
    )
    record.secret = "FAKE credential"
    record.exc_text = "FAKE document contents"
    value = SafeFormatter().format(record)
    assert "FAKE" not in value
    assert set(json.loads(value)) == {"level", "event"}


def test_research_diagnostics_allow_only_bounded_technical_fields():
    record = logging.LogRecord("FAKE", logging.INFO, "", 0, "FAKE private text", (), None)
    record.research_stage = "verification"
    record.research_code = "unsupported_claim"
    record.research_ms = 25
    record.research_sources = 3
    record.query = "FAKE private question"
    value = json.loads(SafeFormatter().format(record))
    assert value["code"] == "unsupported_claim"
    assert "query" not in value and "FAKE" not in json.dumps(value)
    record.research_code = {"FAKE": "untrusted"}
    assert "research_code" not in json.loads(SafeFormatter().format(record))
