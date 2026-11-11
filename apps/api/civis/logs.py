import json
import logging


class SafeFormatter(logging.Formatter):
    """Allowlisted telemetry: arbitrary messages, extras and exceptions never leave process."""

    def format(self, record: logging.LogRecord) -> str:
        value: dict[str, str | int] = {"level": record.levelname, "event": "service_log"}
        stage = getattr(record, "research_stage", None)
        code = getattr(record, "research_code", None)
        if (
            isinstance(stage, str)
            and isinstance(code, str)
            and stage in {"retrieval", "generation", "evidence", "verification"}
            and code
            in {
                "ok",
                "output_limit",
                "truncated_output",
                "invalid_output",
                "rate_limited",
                "timeout",
                "cancelled",
                "upstream_failure",
                "no_sources",
                "insufficient_evidence",
                "unknown_source",
                "evidence_mapping",
                "nonliteral_evidence",
                "untrusted_link",
                "nonliteral_quote",
                "unsupported_claim",
                "safety_hold",
            }
        ):
            value.update(event="research", stage=stage, code=code)
            for name in ("research_ms", "research_sources"):
                number = getattr(record, name, None)
                if type(number) is int and 0 <= number <= 3600000:
                    value[name] = number
            status = getattr(record, "research_upstream_status", None)
            if type(status) is int and 400 <= status <= 599:
                value["research_upstream_status"] = status
        return json.dumps(value)


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(SafeFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "supertokens", "httpx"):
        logger = logging.getLogger(name)
        logger.handlers = []
        logger.propagate = True
