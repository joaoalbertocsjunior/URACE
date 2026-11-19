from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query


def build_router(get_config, verify_token) -> APIRouter:
    router = APIRouter()

    @router.get("/decisions")
    async def audit_decisions(
        outcome: Optional[str] = Query(default=None),
        since: Optional[str] = Query(default=None),
        limit: int = Query(default=50, ge=1, le=500),
        _=Depends(verify_token),
    ):
        from ..._common import load_state_for_read
        config = get_config()
        state = load_state_for_read(config) or {}
        decisions = state.get("decision_records", [])
        if not isinstance(decisions, list):
            decisions = []

        if outcome:
            decisions = [d for d in decisions if isinstance(d, dict) and d.get("outcome") == outcome]

        if since:
            try:
                since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
                filtered = []
                for d in decisions:
                    if not isinstance(d, dict):
                        continue
                    at = d.get("at")
                    if at:
                        try:
                            dt = datetime.fromisoformat(at.replace("Z", "+00:00"))
                            if dt >= since_dt:
                                filtered.append(d)
                        except (ValueError, TypeError):
                            filtered.append(d)
                    else:
                        filtered.append(d)
                decisions = filtered
            except (ValueError, TypeError):
                pass

        decisions = list(reversed(decisions))[:limit]
        return {"decisions": decisions}

    @router.get("/evidence")
    async def audit_evidence(
        kind: Optional[str] = Query(default=None),
        since: Optional[str] = Query(default=None),
        limit: int = Query(default=50, ge=1, le=500),
        _=Depends(verify_token),
    ):
        from ..._common import load_state_for_read
        config = get_config()
        state = load_state_for_read(config) or {}
        evidence = state.get("evidence", [])
        if not isinstance(evidence, list):
            evidence = []

        if kind:
            evidence = [e for e in evidence if isinstance(e, dict) and e.get("kind") == kind]

        if since:
            try:
                since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
                filtered = []
                for e in evidence:
                    if not isinstance(e, dict):
                        continue
                    at = e.get("at")
                    if at:
                        try:
                            dt = datetime.fromisoformat(at.replace("Z", "+00:00"))
                            if dt >= since_dt:
                                filtered.append(e)
                        except (ValueError, TypeError):
                            filtered.append(e)
                    else:
                        filtered.append(e)
                evidence = filtered
            except (ValueError, TypeError):
                pass

        evidence = list(reversed(evidence))[:limit]
        return {"evidence": evidence}

    return router
