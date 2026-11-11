#!/bin/sh
set -eu
# Use only a dedicated disposable test database. No database mocks.
export CIVIS_TEST_DATABASE=1
# Keep reproducible fixtures inside this test process; never rewrite the live .env.
export ENABLE_TEST_FIXTURES=true FAKE_MODEL=true LOAD_FAKE_SEED=true
export ALLOW_UNAPPROVED_TEMPLATES=true FAKE_LEGAL_TEXT=true
export LLM_PROVIDER=fake LLM_MODEL=FAKE-development RETRIEVAL_PROVIDER=disabled
export REQUIRE_EMAIL_VERIFICATION=true FEATURE_UPLOADS=false
python3 scripts/run.py .venv/bin/alembic -c apps/api/alembic.ini upgrade head
python3 scripts/run.py .venv/bin/alembic -c apps/api/alembic.ini downgrade base
python3 scripts/run.py .venv/bin/alembic -c apps/api/alembic.ini upgrade head
.venv/bin/ruff check apps/api scripts
.venv/bin/mypy apps/api/civis apps/worker
python3 scripts/run.py .venv/bin/pytest -q
python3 scripts/feature_coverage.py
