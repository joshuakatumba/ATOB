# Known issues — 2026-11-09

- All 15 product-readiness areas (Tasks 1–15) are implemented and verified locally across backend (`pytest`, `mypy`, `ruff`, `pyrefly`), frontend (`vite build`, `feature_coverage.py`), and browser Playwright suites (`smoke_core.mjs`, `smoke_research_failure.mjs`, `smoke_research.mjs`).
- Live Flutterwave checkout requires production merchant keys (`PAYMENT_PROVIDER=flutterwave`, `FLUTTERWAVE_SECRET_KEY`, `FLUTTERWAVE_WEBHOOK_SECRET`) in `.env` on the production server.
- Document uploads (`FEATURE_UPLOADS=true`) enforce built-in EICAR/macro/active-content scanning and support optional ClamAV daemon scanning via `CLAMAV_HOST` / `CLAMAV_PORT`.
- Existing non-failing upstream library deprecation warnings (`botocore` `datetime.utcnow()` and `arq` `pool.close()`) remain in third-party packages.

See [STATUS.md](STATUS.md) for full implementation and verification details.
