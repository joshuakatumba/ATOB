from __future__ import annotations

import os
from typing import TYPE_CHECKING

import sentry_sdk
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

if TYPE_CHECKING:
    from sentry_sdk._types import Event, Hint


def sanitize_event(event: Event, hint: Hint) -> Event:
    clean: Event = {"message": "service_failure"}
    if "event_id" in event:
        clean["event_id"] = event["event_id"]
    if "timestamp" in event:
        clean["timestamp"] = event["timestamp"]
    if "level" in event:
        clean["level"] = event["level"]
    return clean


def configure_telemetry() -> TracerProvider:
    # Explicit spans only. No automatic request/DB instrumentation can collect personal data.
    provider = TracerProvider(resource=Resource({"service.name": "civis-api"}))
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT")
    if endpoint:
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
    if os.environ.get("SENTRY_DSN"):
        sentry_sdk.init(
            default_integrations=False,
            auto_enabling_integrations=False,
            send_default_pii=False,
            before_send=sanitize_event,
            before_breadcrumb=lambda crumb, hint: None,
            traces_sample_rate=0,
        )
    return provider


def request_tracer(provider: TracerProvider) -> trace.Tracer:
    return provider.get_tracer("civis.http")


def report_failure() -> None:
    sentry_sdk.capture_message("service_failure", level="error")
