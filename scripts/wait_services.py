"""Bounded startup wait without displaying connection details."""

import time
import urllib.error
import urllib.request

from civis.config import Settings

settings = Settings.from_env()
for attempt in range(60):
    try:
        urllib.request.urlopen(settings.supertokens_uri + "/hello", timeout=2).close()
        urllib.request.urlopen(settings.s3_endpoint + "/minio/health/live", timeout=2).close()
        break
    except (OSError, urllib.error.URLError):
        time.sleep(1)
else:
    raise SystemExit("Auth or storage did not become ready")
