"""Standalone sources+M2M control plane via sources-lib HTTPControlServer.

Optional complement to the FastAPI web server; usable in minimal deployments
where the full web stack is not running.
"""
from __future__ import annotations

import hmac
import json
import os
import sys
from typing import Any

from sources import HTTPControlServer, M2MServer

from .source_adapters import SOURCE_REGISTRY
from .source_adapters._sources_bridge import build_sources_registry
from .m2m_bridge import make_dispatch_fn
from .integration_bridge import Jobs, load_policy, owner_lifetime


def build_control_server(
    config: dict[str, Any],
    state: dict[str, Any],
    *,
    token: str | None = None,
    jobs: Any | None = None,
) -> HTTPControlServer:
    """Build a standalone HTTPControlServer backed by URACE's sources registry.

    Parameters
    ----------
    config:
        URACE top-level config dict.
    state:
        URACE state dict.
    token:
        If truthy, every request must supply this as a Bearer token.
        If None/empty, the control plane is open (no auth).
    jobs:
        Optional :class:`~urace.integration_bridge.Jobs` instance.
        When provided an M2MServer is wired up so that JSON-RPC calls are
        dispatched through it; when None no M2M endpoint is exposed.

    Returns
    -------
    HTTPControlServer
        Not yet started — call ``.start(host, port)`` to listen.
    """
    registry = build_sources_registry(SOURCE_REGISTRY, state, config)

    m2m_server: M2MServer | None = None
    if jobs is not None:
        m2m_server = M2MServer(dispatch_fn=make_dispatch_fn(jobs), auth_fn=None)

    if token:
        def auth_fn(t: str) -> bool:
            return hmac.compare_digest(t.encode(), token.encode())
    else:
        auth_fn = None  # type: ignore[assignment]

    return HTTPControlServer(registry=registry, m2m=m2m_server, auth_fn=auth_fn)


def serve(
    parser,
    policy_path: str | None = None,
    *,
    host: str = "127.0.0.1",
    port: int = 8880,
    token_env: str = "URACE_CTRL_TOKEN",
) -> int:
    """Start a standalone HTTPControlServer on ``host:port``.

    Loads policy/config via *parser*, optionally reads an auth token from the
    environment variable named by *token_env*, and blocks until interrupted.

    Returns 0 on clean exit (KeyboardInterrupt), 2 on configuration/runtime
    error.
    """
    jobs = server = None
    try:
        policy = load_policy(parser, policy_path)
        token = os.environ.get(token_env, "")
        jobs = Jobs(policy, private_env=(token_env,))

        from ._common import load_config
        config = load_config()
        state: dict[str, Any] = {}

        server = build_control_server(config, state, token=token or None, jobs=jobs)
        server.start(host=host, port=port)

        print(
            json.dumps({
                "transport": "http-control",
                "host": host,
                "port": port,
                "url": f"http://{host}:{port}",
                "m2m": jobs is not None,
                "auth": bool(token),
            }),
            file=sys.stderr,
            flush=True,
        )

        with owner_lifetime():
            import time
            while True:
                time.sleep(1)

    except KeyboardInterrupt:
        return 0
    except (ValueError, OSError, KeyError) as error:
        print("URACE control_server: " + str(error), file=sys.stderr)
        return 2
    finally:
        if server is not None:
            server.stop()
        if jobs is not None:
            jobs.close()
    return 0
