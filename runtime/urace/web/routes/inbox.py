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
        output = "\n".join(lines)
        return {"output": output}


def build_router(get_config, verify_token) -> APIRouter:
    router = APIRouter()

    @router.get("/")
    async def inbox_list(_=Depends(verify_token)):
        try:
            result = _dispatch(["inbox", "list", "--json"])
            output = result.get("output", "")
            if output:
                try:
                    parsed = json.loads(output)
                    if isinstance(parsed, list):
                        return {"items": parsed}
                    if isinstance(parsed, dict) and "items" in parsed:
                        return parsed
                except (json.JSONDecodeError, ValueError):
                    pass
            from ..._common import load_state_for_read
            config = get_config()
            state = load_state_for_read(config) or {}
            proposals = state.get("patch_proposals", [])
            if not isinstance(proposals, list):
                proposals = []
            return {"items": proposals}
        except Exception as e:
            return {"items": [], "error": str(e)}

    @router.post("/{item_id}/apply")
    async def inbox_apply(item_id: str, _=Depends(verify_token)):
        return _dispatch(["inbox", "apply", item_id, "--json"])

    @router.post("/{item_id}/reject")
    async def inbox_reject(item_id: str, _=Depends(verify_token)):
        return _dispatch(["inbox", "reject", item_id, "--json"])

    @router.get("/count")
    async def inbox_count(_=Depends(verify_token)):
        try:
            from ..._common import load_state_for_read
            config = get_config()
            state = load_state_for_read(config) or {}
            proposals = state.get("patch_proposals", [])
            if not isinstance(proposals, list):
                proposals = []
            count = sum(
                1 for p in proposals
                if isinstance(p, dict) and p.get("status") == "PENDING"
            )
            return {"count": count}
        except Exception:
            return {"count": 0}

    return router
