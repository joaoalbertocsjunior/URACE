from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Query


def _rpc_call(method: str, **kwargs) -> dict:
    import socket
    from ..._daemon import RPC_TCP_HOST, RPC_TCP_PORT

    with socket.create_connection((RPC_TCP_HOST, RPC_TCP_PORT), timeout=30) as s:
        msg = {"method": method, **kwargs}
        s.sendall((json.dumps(msg) + "\n").encode())
        data = b""
        while b"\n" not in data:
            chunk = s.recv(4096)
            if not chunk:
                break
            data += chunk
        return json.loads(data.split(b"\n")[0])


def _dispatch(argv: list[str]) -> dict:
    try:
        return _rpc_call("dispatch", argv=argv)
    except (ConnectionRefusedError, OSError):
        import io
        import sys
        import threading

        q = __import__("queue").Queue()

        def _worker():
            from ...cli import main as cli_main

            class _Cap(io.TextIOBase):
                def write(self, s):
                    if s.strip():
                        q.put(s.rstrip())
                    return len(s)

                def flush(self):
                    pass

            old = sys.stdout
            sys.stdout = _Cap()
            try:
                cli_main(argv)
            except SystemExit:
                pass
            except Exception as e:
                q.put(json.dumps({"error": str(e)}))
            finally:
                sys.stdout = old
                q.put(None)

        threading.Thread(target=_worker, daemon=True).start()
        lines = []
        while True:
            line = q.get()
            if line is None:
                break
            lines.append(line)
        return {"output": "\n".join(lines)}


def build_router(get_config, verify_token) -> APIRouter:
    router = APIRouter()

    @router.get("/peers")
    async def exchange_peers(_=Depends(verify_token)):
        result = _dispatch(["network", "peers", "--json"])
        try:
            return json.loads(result.get("output", "{}"))
        except Exception:
            return {"peer_count": 0, "anonymized_peer_ids": [], "error": result.get("output", "unknown")}

    @router.get("/assets")
    async def exchange_assets(query: str = Query(default=""), _=Depends(verify_token)):
        argv = ["network", "assets"]
        if query:
            argv += ["--query", query]
        argv.append("--json")
        result = _dispatch(argv)
        try:
            return json.loads(result.get("output", "{}"))
        except Exception:
            return {"open_assets": [], "paid_listings": [], "error": result.get("output", "unknown")}

    @router.get("/search")
    async def exchange_search(
        q: str = Query(default=""),
        kind: str = Query(default="all"),
        _=Depends(verify_token),
    ):
        argv = ["search"]
        if q:
            argv.append(q)
        argv += ["--kind", kind, "--json"]
        result = _dispatch(argv)
        try:
            return json.loads(result.get("output", "{}"))
        except Exception:
            return {"error": result.get("output", "unknown")}

    return router
