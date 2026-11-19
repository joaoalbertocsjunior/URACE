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

    @router.get("/")
    async def products_list(_=Depends(verify_token)):
        result = _dispatch(["product", "list", "--json"])
        try:
            return json.loads(result.get("output", "[]"))
        except Exception:
            return []

    @router.get("/status")
    async def products_status(_=Depends(verify_token)):
        result = _dispatch(["product", "status", "--json"])
        try:
            return json.loads(result.get("output", "{}"))
        except Exception:
            return {"active_product": None}

    @router.post("/{name}/switch")
    async def products_switch(name: str, _=Depends(verify_token)):
        result = _dispatch(["product", "switch", name, "--json"])
        try:
            return json.loads(result.get("output", "{}"))
        except Exception:
            return result

    @router.post("/{name}/activate")
    async def products_activate(name: str, _=Depends(verify_token)):
        result = _dispatch(["product", "activate", name, "--json"])
        try:
            return json.loads(result.get("output", "{}"))
        except Exception:
            return result

    @router.post("/{name}/deactivate")
    async def products_deactivate(name: str, _=Depends(verify_token)):
        result = _dispatch(["product", "deactivate", name, "--json"])
        try:
            return json.loads(result.get("output", "{}"))
        except Exception:
            return result

    @router.get("/improvements")
    async def products_improvements(_=Depends(verify_token)):
        result = _dispatch(["product", "improvements", "list", "--json"])
        try:
            return json.loads(result.get("output", "{}"))
        except Exception:
            return {"products": []}

    return router
