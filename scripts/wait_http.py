"""Bounded readiness wait for local integration services; never print response bodies."""
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen

for url in sys.argv[1:]:
    deadline = time.monotonic() + 60
    while True:
        try:
            with urlopen(url, timeout=2) as response:
                if response.status == 200:
                    break
        except (URLError, TimeoutError, ConnectionError):
            pass
        if time.monotonic() >= deadline:
            raise SystemExit('Local service did not become ready')
        time.sleep(0.25)
print('Local services ready')
