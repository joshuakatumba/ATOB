"""Refuse to launch the user-facing app with test replies or test catalog settings."""

from civis.config import Settings
from civis.providers import provider_from_settings

try:
    settings = Settings.from_env()
except ValueError:
    raise SystemExit("Run python3 scripts/configure_live.py to configure real services") from None
if (
    settings.enable_test_fixtures
    or settings.fake_model
    or settings.load_fake_seed
    or settings.allow_unapproved_templates
    or settings.fake_legal_text
    or settings.llm_provider not in {"groq", "anthropic"}
):
    raise SystemExit(
        "Live startup requires real service settings. Run python3 scripts/configure_live.py"
    )
if provider_from_settings(settings) is None:
    raise SystemExit("Configure the real model provider before startup")
if settings.retrieval_provider != "laws_africa" or not settings.laws_africa_api_key:
    raise SystemExit("Configure Laws.Africa retrieval before startup")
print("Live model and approved-catalog configuration checked")
