"""HTTP adapter port — simple JSON-RPC POST over HTTPS without cert pinning.

Used for unauthenticated bootstrap RPC calls. The certificate-pinned P2P peer
RPC path in peer_exchange.py uses http.client directly because it requires
raw socket access for TOFU certificate pinning — httpx does not expose
binary peer certificates.
"""
from __future__ import annotations

import json
import ssl
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class HttpAdapter(Protocol):
    """Port for HTTPS JSON-RPC calls that do not require certificate pinning."""

    def post_json(self, url: str, payload: dict[str, Any], *, timeout: float = 10.0) -> dict[str, Any]: ...


class HttpxAdapter:
    """HttpAdapter backed by httpx."""

    def post_json(self, url: str, payload: dict[str, Any], *, timeout: float = 10.0) -> dict[str, Any]:
        import httpx
        with httpx.Client(verify=False, timeout=timeout) as client:  # noqa: S501
            resp = client.post(url, json=payload, headers={"Content-Type": "application/json"})
            resp.raise_for_status()
            return resp.json()


class StdlibHttpAdapter:
    """HttpAdapter backed by stdlib http.client — zero extra deps."""

    def post_json(self, url: str, payload: dict[str, Any], *, timeout: float = 10.0) -> dict[str, Any]:
        import http.client
        import urllib.parse
        u = urllib.parse.urlsplit(url)
        body = json.dumps(payload, separators=(",", ":")).encode()
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        conn = http.client.HTTPSConnection(u.hostname, u.port or 443, context=ctx, timeout=timeout)
        try:
            conn.request("POST", u.path or "/", body, {"Content-Type": "application/json", "Content-Length": str(len(body))})
            resp = conn.getresponse()
            data = resp.read(4 * 1024 * 1024)
            if resp.status != 200:
                raise ValueError(f"HTTP {resp.status}")
            return json.loads(data)
        finally:
            conn.close()


def make_http_adapter() -> HttpAdapter:
    """Return HttpxAdapter if httpx is available, else StdlibHttpAdapter."""
    try:
        import httpx  # noqa: F401
        return HttpxAdapter()
    except ImportError:
        return StdlibHttpAdapter()
