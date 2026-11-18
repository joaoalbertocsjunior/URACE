from __future__ import annotations

import json

from fastapi import APIRouter, Depends


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

    @router.get("/list")
    async def rules_list(_=Depends(verify_token)):
        result = _dispatch(["rules", "list", "--json"])
        try:
            data = json.loads(result.get("output", "[]"))
            return data if isinstance(data, list) else []
        except Exception:
            return []

    @router.get("/graph")
    async def rules_graph(_=Depends(verify_token)):
        result = _dispatch(["rules", "graph", "--json"])
        try:
            data = json.loads(result.get("output", "{}"))
            return data if isinstance(data, dict) else {"rules": [], "relationships": []}
        except Exception:
            return {"rules": [], "relationships": []}

    @router.get("/conflicts")
    async def rules_conflicts(_=Depends(verify_token)):
        result = _dispatch(["rules", "conflicts", "--json"])
        try:
            data = json.loads(result.get("output", "[]"))
            return data if isinstance(data, list) else []
        except Exception:
            return []

    return router
