from __future__ import annotations

from fastapi import APIRouter, Depends


def build_router(get_config, verify_token) -> APIRouter:
    router = APIRouter()

    @router.get("/")
    async def vitals(_=Depends(verify_token)):
        from ..._common import load_state_for_read
        config = get_config()
        state = load_state_for_read(config) or {}

        lifecycle_state = state.get("lifecycle_state", "UNKNOWN")

        checkpoints = state.get("checkpoints", [])
        last_cycle_at = None
        if checkpoints:
            try:
                last_cycle_at = max(
                    (c.get("completed_at") or c.get("started_at") for c in checkpoints if isinstance(c, dict)),
                    default=None,
                )
            except Exception:
                pass

        aps_score = state.get("aps_score")
        if aps_score is None:
            aps_score = state.get("current_aps_score")

        objectives = state.get("objectives", [])
        evidence = state.get("evidence", [])

        return {
            "lifecycle_state": lifecycle_state,
            "last_cycle_at": last_cycle_at,
            "aps_score": aps_score,
            "cycle_count": len(checkpoints),
            "objectives_count": len(objectives) if isinstance(objectives, list) else 0,
            "evidence_count": len(evidence) if isinstance(evidence, list) else 0,
        }

    return router
