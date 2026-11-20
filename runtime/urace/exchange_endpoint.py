"""P2P CREDIT_SETTLEMENT endpoint.

Accepts authenticated CREDIT_SETTLEMENT RPC calls from peer nodes and
wires them to credit_ledger.earn_units() / spend_units(). This module is
imported by the Exchange server when token_settlement=True.
"""
from __future__ import annotations

from typing import Any


SCHEMA = "urace-credit-settlement-v1"


def handle_credit_settlement(
    exchange,
    peer_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Process a CREDIT_SETTLEMENT request from a peer.

    payload fields:
      action        -- "earn" | "spend"
      peer_id       -- local peer receiving the credit change
      units         -- positive integer
      reason        -- human-readable reason string
      operation_id  -- idempotency key (deduplicated on replay)
      schema        -- must equal SCHEMA

    Returns {"status": "ok", "units": N} or {"status": "error", "error": "..."}.
    """
    if payload.get("schema") != SCHEMA:
        return {"status": "error", "error": f"unsupported schema: {payload.get('schema')!r}"}

    action = payload.get("action")
    target_peer = payload.get("peer_id", "")
    units = payload.get("units", 0)
    reason = payload.get("reason", "settlement")
    operation_id = payload.get("operation_id", "")

    if not isinstance(units, int) or units <= 0:
        return {"status": "error", "error": "units must be a positive integer"}
    if action not in ("earn", "spend"):
        return {"status": "error", "error": f"unknown action: {action!r}"}

    try:
        from pathlib import Path
        from ._common import state_path
        from . import credit_ledger as _cl

        p = exchange.load()
        root = Path(exchange._root) if hasattr(exchange, "_root") else None
        if root is None:
            return {"status": "error", "error": "exchange root unavailable"}

        if action == "earn":
            _cl.earn_units(root, target_peer, units, f"settlement:{reason}", bundle_id=operation_id)
        else:
            _cl.spend_units(root, target_peer, units, f"settlement:{reason}", bundle_id=operation_id)

        exchange.audit(
            kind="CREDIT_SETTLEMENT_APPLIED",
            peer_id=peer_id,
            target_peer=target_peer,
            action=action,
            units=units,
            operation_id=operation_id,
        )
        return {"status": "ok", "action": action, "units": units, "operation_id": operation_id}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def build_settlement_router(exchange_factory, verify_token=None):
    """Build a FastAPI APIRouter for the settlement endpoint.

    exchange_factory: callable() → Exchange
    verify_token: optional FastAPI Depends callable for auth
    """
    try:
        from fastapi import APIRouter, Depends, HTTPException
        from pydantic import BaseModel

        router = APIRouter()

        class SettlementRequest(BaseModel):
            schema_version: str = SCHEMA
            action: str
            peer_id: str
            units: int
            reason: str = ""
            operation_id: str = ""

        deps = [Depends(verify_token)] if verify_token else []

        @router.post("/p2p/settle", dependencies=deps)
        async def settle(req: SettlementRequest, peer_id: str = ""):
            exchange = exchange_factory()
            if exchange is None:
                raise HTTPException(status_code=503, detail="Exchange not available")
            payload = {
                "schema": SCHEMA,
                "action": req.action,
                "peer_id": req.peer_id,
                "units": req.units,
                "reason": req.reason,
                "operation_id": req.operation_id,
            }
            result = handle_credit_settlement(exchange, peer_id or req.peer_id, payload)
            if result.get("status") == "error":
                raise HTTPException(status_code=400, detail=result["error"])
            return result

        return router
    except ImportError:
        return None
