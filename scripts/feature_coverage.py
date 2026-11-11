"""Check the frozen React component inventory without changing acceptance records."""

from pathlib import Path

files = [
    "main.jsx",
    "App.jsx",
    "styles/civis.css",
    "lib/doc.js",
    "lib/http.js",
    "lib/api.js",
    "hooks/useMic.js",
]
files += [
    f"components/{name}.jsx"
    for name in (
        "Icon",
        "Auth",
        "Shell",
        "Sidebar",
        "ChatView",
        "Message",
        "Composer",
        "Templates",
        "DocPanel",
        "Modal",
        "AccountRecovery",
        "DocumentLibrary",
    )
]
missing = [name for name in files if not (Path("apps/web/src") / name).is_file()]
if missing:
    raise SystemExit("Missing frontend module: " + ", ".join(missing))
print(f"PASS: {len(files)} frozen React modules exist; acceptance is tracked in STATUS.md")
