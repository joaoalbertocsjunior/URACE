from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from pydantic import BaseModel


class _RunBody(BaseModel):
    dry_run: bool = True


class _BroadcastBody(BaseModel):
    command: str


class _ConfigPushBody(BaseModel):
    key: str
    value: str


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

    @router.get("/status")
    async def fleet_status(_=Depends(verify_token)):
        result = _dispatch(["fleet", "status", "--json"])
        try:
            return json.loads(result.get("output", "[]"))
        except Exception:
            return []

    @router.get("/capacity")
    async def fleet_capacity(_=Depends(verify_token)):
        result = _dispatch(["fleet", "capacity", "--json"])
        try:
            return json.loads(result.get("output", "{}"))
        except Exception:
            return {"fleet_size": 0, "members": []}

    @router.post("/run")
    async def fleet_run(body: _RunBody, _=Depends(verify_token)):
        argv = ["fleet", "run"]
        if body.dry_run:
            argv.append("--dry-run")
        argv.append("--json")
        result = _dispatch(argv)
        try:
            return json.loads(result.get("output", "{}"))
        except Exception:
            return result

    @router.post("/broadcast")
    async def fleet_broadcast(body: _BroadcastBody, _=Depends(verify_token)):
        result = _dispatch(["fleet", "broadcast", "--json"])
        try:
            return json.loads(result.get("output", "{}"))
        except Exception:
            return result

    @router.post("/config-push")
    async def fleet_config_push(body: _ConfigPushBody, _=Depends(verify_token)):
        result = _dispatch([
            "fleet", "config-push",
            "--config-key", body.key,
            "--config-value", body.value,
            "--json",
        ])
        try:
            return json.loads(result.get("output", "{}"))
        except Exception:
            return result

    return router
