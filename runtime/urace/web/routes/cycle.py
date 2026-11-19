from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates


def build_router(templates: Jinja2Templates, get_config, verify_token) -> APIRouter:
    router = APIRouter()

    @router.get("/state")
    async def cycle_state(request: Request, _=Depends(verify_token)):
        from ..._common import load_state_for_read
        config = get_config()
        state = load_state_for_read(config) or {}

        def _last5(items):
            if not isinstance(items, list):
                return []
            return items[-5:]

        objectives_raw = state.get("objectives", [])
        active_objectives = [
            o for o in (objectives_raw if isinstance(objectives_raw, list) else [])
            if isinstance(o, dict) and o.get("status") == "active"
        ]
        objectives = active_objectives[-5:] if active_objectives else _last5(objectives_raw)

        evidence = _last5(state.get("evidence", []))
        decisions = _last5(state.get("decision_records", []))
        operations = _last5(state.get("operations", []))
        checkpoints = _last5(state.get("checkpoints", []))
        lifecycle_state = state.get("lifecycle_state", "UNKNOWN")

        if request.headers.get("HX-Request"):
            return templates.TemplateResponse(
                request,
                "cycle_state.html",
                context={
                    "objectives": objectives,
                    "evidence": evidence,
                    "decisions": decisions,
                    "operations": operations,
                    "checkpoints": checkpoints,
                    "lifecycle_state": lifecycle_state,
                },
            )

        return JSONResponse({
            "objectives_count": len(objectives_raw) if isinstance(objectives_raw, list) else 0,
            "evidence_count": len(state.get("evidence", [])) if isinstance(state.get("evidence"), list) else 0,
            "decisions_count": len(state.get("decision_records", [])) if isinstance(state.get("decision_records"), list) else 0,
            "operations_count": len(state.get("operations", [])) if isinstance(state.get("operations"), list) else 0,
            "checkpoints_count": len(state.get("checkpoints", [])) if isinstance(state.get("checkpoints"), list) else 0,
            "lifecycle_state": lifecycle_state,
        })

    return router
