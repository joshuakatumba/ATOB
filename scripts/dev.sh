#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 scripts/dev_env.py
docker compose up -d --wait postgres auth-db redis
docker compose up -d auth storage mail
docker compose build api web worker
docker compose run --rm api python scripts/check_live.py
docker compose run --rm api python scripts/wait_services.py
docker compose run --rm api alembic -c apps/api/alembic.ini upgrade head
docker compose run --rm api python scripts/bootstrap_storage.py
docker compose run --rm api python scripts/import_templates.py
docker compose up -d api worker web
printf 'Civis: http://localhost:53000\n'
