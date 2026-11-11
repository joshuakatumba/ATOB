"""Load local environment without printing credentials, then execute an argument vector."""

import os
import sys
from pathlib import Path

if Path(".env").is_file():
    for line in Path(".env").read_text().splitlines():
        if line and not line.startswith("#"):
            key, value = line.split("=", 1)
            os.environ.setdefault(key, value)
if len(sys.argv) < 2:
    raise SystemExit("Usage: python scripts/run.py COMMAND [ARG ...]")
root = Path(__file__).resolve().parent.parent
os.environ["PYTHONPATH"] = os.pathsep.join(
    [
        str(root / "apps/api"),
        str(root / "apps/worker"),
        os.environ.get("PYTHONPATH", ""),
    ]
)
if os.environ.get("CIVIS_TEST_DATABASE") == "1":
    if os.environ.get("APP_ENV") == "production":
        raise SystemExit("Test commands cannot target production")
    # The URL is generated locally; retain credentials/host and select the disposable database.
    database_url = os.environ.get("DATABASE_URL", "")
    os.environ["DATABASE_URL"] = database_url.rsplit("/", 1)[0] + "/civis_test"
os.execvp(sys.argv[1], sys.argv[1:])
