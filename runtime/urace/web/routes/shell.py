from __future__ import annotations

import asyncio
import io
import json
import queue
import sys
import threading

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel


class _ShellInput(BaseModel):
    input: str


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


def _run_cli_streaming(argv: list[str]) -> queue.Queue:
    q: queue.Queue = queue.Queue()

    def _worker():
        from ...cli import main as cli_main

        class _LineCapture(io.TextIOBase):
            def write(self, s):
                if s.strip():
                    q.put(s.rstrip())
                return len(s)

            def flush(self):
                pass

        old_stdout = sys.stdout
        sys.stdout = _LineCapture()
        try:
            cli_main(argv)
        except SystemExit:
            pass
        except Exception as e:
            q.put(json.dumps({"error": str(e)}))
        finally:
            sys.stdout = old_stdout
            q.put(None)

    threading.Thread(target=_worker, daemon=True).start()
    return q


async def _sse_from_queue(q: queue.Queue):
    loop = asyncio.get_event_loop()
    while True:
        line = await loop.run_in_executor(None, q.get)
        if line is None:
            yield "data: [DONE]\n\n"
            break
        yield f"data: {line}\n\n"


def build_router(verify_token) -> APIRouter:
    router = APIRouter()

    @router.post("/run")
    async def shell_run(body: _ShellInput, _=Depends(verify_token)):
        user_input = body.input.strip()
        # Single-token input is a command; multi-word input is NL — pass whole
        # string as one argv element so the CLI freeform router handles it.
        tokens = user_input.split()
        argv = tokens if len(tokens) == 1 else [user_input]

        try:
            result = _rpc_call("dispatch", argv=argv)
            output = result.get("output") or result.get("error") or json.dumps(result)

            async def _single_sse():
                for line in output.splitlines():
                    if line.strip():
                        yield f"data: {line}\n\n"
                yield "data: [DONE]\n\n"

            return StreamingResponse(_single_sse(), media_type="text/event-stream")
        except (ConnectionRefusedError, OSError):
            q = _run_cli_streaming(["--json"] + argv)
            return StreamingResponse(_sse_from_queue(q), media_type="text/event-stream")

    return router
