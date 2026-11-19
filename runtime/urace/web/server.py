from __future__ import annotations

import importlib.util
import secrets
import sys


def capabilities() -> dict:
    missing = []
    for name in ("fastapi", "uvicorn", "jinja2"):
        if importlib.util.find_spec(name) is None:
            missing.append(name)
    if missing:
        return {"status": "ADAPTER_REQUIRED", "missing": missing}
    return {"status": "READY"}


def serve(config: dict, host: str = "127.0.0.1", port: int = 7475, token: str | None = None) -> int:
    caps = capabilities()
    if caps["status"] != "READY":
        missing = caps.get("missing", [])
        print(
            f"web deps missing: {', '.join(missing)}. Install with: pip install 'urace[web]'",
            file=sys.stderr,
        )
        return 1

    if token is None:
        token = secrets.token_urlsafe(32)
        print(f"URACE web token: {token}", flush=True)

    import uvicorn
    from .app import create_app

    app = create_app(config, token)
    uvicorn.run(app, host=host, port=port)
    return 0
