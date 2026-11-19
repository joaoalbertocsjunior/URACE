from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from pydantic import BaseModel


class _AddGoalBody(BaseModel):
    title: str
    description: str = ""
    priority: int = 50


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
        output = "\n".join(lines)
        return {"output": output}


def build_router(get_config, verify_token) -> APIRouter:
    router = APIRouter()

    @router.get("/")
    async def goals_list(_=Depends(verify_token)):
        from ..._common import load_state_for_read
        config = get_config()
        state = load_state_for_read(config) or {}
        objectives = state.get("objectives", [])
        if not isinstance(objectives, list):
            objectives = []
        return {"goals": objectives}

    @router.post("/add")
    async def goals_add(body: _AddGoalBody, _=Depends(verify_token)):
        argv = [
            "add-goal",
            "--title", body.title,
            "--description", body.description,
            "--json",
        ]
        result = _dispatch(argv)
        return result

    @router.post("/{goal_id}/pin")
    async def goals_pin(goal_id: str, _=Depends(verify_token)):
        return _dispatch(["goal", "pin", goal_id, "--json"])

    @router.post("/{goal_id}/unpin")
    async def goals_unpin(goal_id: str, _=Depends(verify_token)):
        return _dispatch(["goal", "unpin", goal_id, "--json"])

    @router.post("/{goal_id}/defer")
    async def goals_defer(goal_id: str, _=Depends(verify_token)):
        return _dispatch(["goal", "defer", goal_id, "--json"])

    @router.post("/{goal_id}/cancel")
    async def goals_cancel(goal_id: str, _=Depends(verify_token)):
        return _dispatch(["goal", "cancel", goal_id, "--json"])

    @router.get("/forecast")
    async def goals_forecast(_=Depends(verify_token)):
        return _dispatch(["goal", "forecast", "--json"])

    return router
