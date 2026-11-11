"""FAKE – development only: private payloads must not reach telemetry exporters."""

from civis.telemetry import sanitize_event


def test_sentry_allowlist():
    event = {
        "event_id": "FAKE",
        "level": "error",
        "request": {"data": "FAKE private body"},
        "user": {"email": "FAKE@example.invalid"},
        "exception": {"values": "FAKE document"},
        "breadcrumbs": ["FAKE secret"],
        "extra": {"password": "FAKE credential"},
    }
    assert sanitize_event(event, {}) == {
        "event_id": "FAKE",
        "level": "error",
        "message": "service_failure",
    }
