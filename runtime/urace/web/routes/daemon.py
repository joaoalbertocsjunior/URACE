from __future__ import annotations

import os
import signal
import subprocess
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates


def build_router(templates: Jinja2Templates, verify_token) -> APIRouter:
    router = APIRouter()

    def _pid_file(config: dict) -> Path | None:
        from ..._common import state_path
        try:
            sp = state_path(config)
            return sp.parent / "daemon.pid"
        except Exception:
            return None

    def _load_config():
        from ..._common import load_config
        try:
            return load_config()
        except Exception:
            return {}

    def _is_running(config: dict) -> tuple[bool, int | None]:
        pid_path = _pid_file(config)
        if pid_path is None or not pid_path.exists():
            return False, None
        try:
            pid = int(pid_path.read_text().strip())
        except (ValueError, OSError):
            return False, None
        try:
            os.kill(pid, 0)
            return True, pid
        except ProcessLookupError:
            return False, None
        except PermissionError:
            return True, pid

    def _cycle_active(config: dict) -> bool:
        from ..._common import load_state_for_read
        state = load_state_for_read(config)
        if state is None:
            return False
        return state.get("lifecycle_state") == "ACTIVE"

    @router.get("/status")
    async def daemon_status(request: Request, _=Depends(verify_token)):
        config = _load_config()
        running, pid = _is_running(config)
        cycle = _cycle_active(config) if running else False
        payload = {"status": "running" if running else "stopped", "pid": pid, "cycle_active": cycle}
        if request.headers.get("HX-Request"):
            return templates.TemplateResponse(
                request, "daemon_bar.html",
                context={"status": payload["status"], "cycle_active": cycle},
            )
        return payload

    @router.post("/start")
    async def daemon_start(_=Depends(verify_token)):
        subprocess.Popen(["urace", "start"], start_new_session=True)
        return {"status": "starting"}

    @router.post("/stop")
    async def daemon_stop(request: Request, _=Depends(verify_token)):
        config = _load_config()
        running, pid = _is_running(config)
        if not running or pid is None:
            payload = {"status": "not_running"}
        else:
            try:
                os.kill(pid, signal.SIGTERM)
                payload = {"status": "stopped"}
            except OSError:
                payload = {"status": "error"}
        if request.headers.get("HX-Request"):
            bar_status = "running" if payload["status"] == "running" else "stopped"
            return templates.TemplateResponse(
                request, "daemon_bar.html",
                context={"status": bar_status, "cycle_active": False},
            )
        return payload

    return router
