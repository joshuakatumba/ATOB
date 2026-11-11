"""Create local-only credentials without printing or committing them."""

import argparse
import base64
import os
import secrets
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument(
    "--test-fixtures", action="store_true", help="Explicit isolated test setup only"
)
args = parser.parse_args()
path = Path(".env")
existing = (
    dict(
        line.split("=", 1)
        for line in path.read_text().splitlines()
        if line and not line.startswith("#")
    )
    if path.exists()
    else {}
)
password = secrets.token_hex(24)
auth_password = secrets.token_hex(24)
storage_password = secrets.token_hex(24)
values = {
    "APP_ENV": "development",
    "POSTGRES_PASSWORD": password,
    "AUTH_DB_PASSWORD": auth_password,
    "DATABASE_URL": f"postgresql+asyncpg://civis:{password}@localhost:55432/civis",
    "AUTH_DATABASE_URL": f"postgresql://auth:{auth_password}@auth-db:5432/auth",
    "REDIS_URL": "redis://localhost:56379/0",
    "SUPERTOKENS_URI": "http://localhost:53567",
    "SUPERTOKENS_API_KEY": secrets.token_hex(24),
    "API_DOMAIN": "http://localhost:58000",
    "WEB_DOMAIN": "http://localhost:53000",
    "S3_ENDPOINT": "http://localhost:59000",
    "S3_ACCESS_KEY": secrets.token_hex(12),
    "S3_SECRET_KEY": storage_password,
    "S3_BUCKET": "civis-private",
    "LOG_HMAC_KEY": secrets.token_hex(32),
    "SMTP_HOST": "localhost",
    "SMTP_PORT": "51025",
    "SMTP_FROM": "civis@localhost",
    "ALLOW_UNAPPROVED_TEMPLATES": "false",
    "LOAD_FAKE_SEED": "true" if args.test_fixtures else "false",
    "ENABLE_TEST_FIXTURES": "true" if args.test_fixtures else "false",
    "LLM_PROVIDER": "fake" if args.test_fixtures else "groq",
    "LLM_MODEL": "FAKE-development" if args.test_fixtures else "",
    "GROQ_API_KEY": "",
    "LAWS_AFRICA_API_KEY": "",
    "RETRIEVAL_PROVIDER": "disabled" if args.test_fixtures else "laws_africa",
    "FEATURE_UPLOADS": "false",
    "OWNER_TEMPLATES_FILE": "content/owner-supplied/templates.json",
    "REQUIRE_EMAIL_VERIFICATION": "false",
    "FAKE_MODEL": "true" if args.test_fixtures else "false",
    "S3_PUBLIC_ENDPOINT": "http://localhost:59000",
    "DOCUMENT_ENCRYPTION_KEY": base64.b64encode(secrets.token_bytes(32)).decode(),
}
if existing:
    additions = {key: value for key, value in values.items() if key not in existing}
    with path.open("a") as file:
        file.write("\n" + "".join(f"{key}={value}\n" for key, value in additions.items()))
    print("Existing private .env retained; missing development settings added")
else:
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "w") as file:
        file.write("".join(f"{key}={value}\n" for key, value in values.items()))
    print("Created private .env for local development")
