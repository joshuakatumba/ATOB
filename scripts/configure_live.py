"""Enable real services in a private environment, retaining database credentials."""

import getpass
import os
import tempfile
from pathlib import Path


def read_env(path: Path) -> dict[str, str]:
    return dict(
        line.split("=", 1)
        for line in path.read_text().splitlines()
        if line and not line.startswith("#") and "=" in line
    )


def main() -> None:
    path = Path(".env")
    if not path.is_file():
        raise SystemExit("Run python3 scripts/dev_env.py first")
    existing = read_env(path)
    sample = read_env(Path(__file__).resolve().parents[1] / ".env.example")
    updates = {
        "LLM_PROVIDER": "groq",
        "FAKE_MODEL": "false",
        "ENABLE_TEST_FIXTURES": "false",
        "LOAD_FAKE_SEED": "false",
        "FAKE_LEGAL_TEXT": "false",
        "ALLOW_UNAPPROVED_TEMPLATES": "false",
        "RETRIEVAL_PROVIDER": "laws_africa",
        "OWNER_TEMPLATES_FILE": "content/owner-supplied/templates.json",
    }
    for name, prompt in (
        ("GROQ_API_KEY", "Groq API key (hidden): "),
        ("LAWS_AFRICA_API_KEY", "Laws.Africa API key (hidden): "),
    ):
        value = existing.get(name, "").strip()
        if len(value) < 16 or value.startswith("YOUR_"):
            value = getpass.getpass(prompt).strip()
        if len(value) < 16 or any(character.isspace() for character in value):
            raise SystemExit(f"A valid {name} is required; no environment changes saved")
        updates[name] = value
    model = existing.get("LLM_MODEL", "")
    if not model or model.startswith("FAKE"):
        model = sample.get("LLM_MODEL", "")
    if not model or any(character.isspace() for character in model):
        raise SystemExit("Configure LLM_MODEL; no environment changes saved")
    updates["LLM_MODEL"] = model
    if existing.get("LEGAL_CONTENT_FILE", "").startswith("content/dev-fake/"):
        updates["LEGAL_CONTENT_FILE"] = ""
    lines = [
        line for line in path.read_text().splitlines() if line.partition("=")[0] not in updates
    ]
    lines.extend(f"{name}={value}" for name, value in updates.items())
    with tempfile.NamedTemporaryFile(
        mode="w", dir=path.parent, prefix=".env-live-", delete=False
    ) as target:
        temporary = Path(target.name)
        target.write("\n".join(lines) + "\n")
    try:
        temporary.chmod(0o600)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    print("Real services and approved templates configured; database credentials retained.")
    print("Run sudo ./scripts/dev.sh to rebuild and restart. API keys were not printed.")


if __name__ == "__main__":
    main()
