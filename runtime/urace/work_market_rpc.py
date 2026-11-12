"""Cross-peer work market RPC notifications.

Thin wrappers over peer_exchange.request() for the P2P work market state machine:
- notify_work_accepted: requester -> hired peer (escrow locked)
- submit_delivery_rpc: hired peer -> requester (work delivered)
- handle_work_accepted_notification: server-side for WORK_ACCEPTED
- handle_work_delivery_notification: server-side for WORK_DELIVERY
"""
from __future__ import annotations

import hashlib

from . import peer_exchange as _px


def notify_work_accepted(
    exchange,
    hired_peer_id: str,
    request_id: str,
    escrow_snapshot: dict,
) -> dict:
    """Notify the hired peer that their bid was accepted and escrow is locked.

    Emits WORK_ACCEPTED_NOTIFICATION_SENT audit event.
    Returns the RPC result or {'status': 'rpc_error', 'error': ...} on failure.
    Never raises.
    """
    try:
        exchange.event(
            "WORK_ACCEPTED_NOTIFICATION_SENT",
            request_id=request_id,
            hired_peer_id=hired_peer_id,
            escrow_snapshot_sha256=hashlib.sha256(
                str(sorted(escrow_snapshot.items())).encode()
            ).hexdigest(),
        )
        result = _px.request(
            exchange,
            hired_peer_id,
            "exchange.work_accepted",
            {
                "request_id": request_id,
                "hired_peer_id": hired_peer_id,
                "escrow_snapshot": escrow_snapshot,
            },
        )
        return result
    except Exception as exc:
        return {"status": "rpc_error", "error": str(exc)}


def submit_delivery_rpc(
    exchange,
    requester_peer_id: str,
    request_id: str,
    delivery_hash: str,
) -> dict:
    """Submit a work delivery notification to the requester peer.

    Emits WORK_DELIVERY_RPC_SENT audit event.
    Returns the RPC result or {'status': 'rpc_error', 'error': ...} on failure.
    Never raises.
    """
    try:
        hired_peer_id = exchange.identity()["peer_id"]
        exchange.event(
            "WORK_DELIVERY_RPC_SENT",
            request_id=request_id,
            requester_peer_id=requester_peer_id,
            delivery_hash=delivery_hash,
            hired_peer_id=hired_peer_id,
        )
        result = _px.request(
            exchange,
            requester_peer_id,
            "exchange.work_delivery",
            {
                "request_id": request_id,
                "delivery_hash": delivery_hash,
                "hired_peer_id": hired_peer_id,
            },
        )
        return result
    except Exception as exc:
        return {"status": "rpc_error", "error": str(exc)}


def handle_work_accepted_notification(
    exchange,
    sender_peer_id: str,
    params: dict,
) -> dict:
    """Server-side handler for WORK_ACCEPTED notifications.

    Validates that this peer is the intended recipient, emits
    WORK_ACCEPTED_RECEIVED, returns {'status': 'ok', 'request_id': ...}.
    """
    for required in ("request_id", "hired_peer_id", "escrow_snapshot"):
        if required not in params:
            return {"status": "error", "error": f"missing required param: {required!r}"}

    local_peer_id = exchange.identity()["peer_id"]
    if params["hired_peer_id"] != local_peer_id:
        return {"status": "error", "error": "not_intended_recipient"}

    exchange.event(
        "WORK_ACCEPTED_RECEIVED",
        request_id=params["request_id"],
        requester_peer_id=sender_peer_id,
        hired_peer_id=local_peer_id,
        escrow_snapshot=params["escrow_snapshot"],
    )
    return {"status": "ok", "request_id": params["request_id"]}


def handle_work_delivery_notification(
    exchange,
    sender_peer_id: str,
    params: dict,
) -> dict:
    """Server-side handler for WORK_DELIVERY notifications.

    Validates required params, emits WORK_DELIVERY_RECEIVED with all fields,
    returns {'status': 'ok', 'request_id': ...}.
    """
    for required in ("request_id", "delivery_hash", "hired_peer_id"):
        if required not in params:
            return {"status": "error", "error": f"missing required param: {required!r}"}

    exchange.event(
        "WORK_DELIVERY_RECEIVED",
        request_id=params["request_id"],
        delivery_hash=params["delivery_hash"],
        hired_peer_id=params["hired_peer_id"],
        sender_peer_id=sender_peer_id,
    )
    return {"status": "ok", "request_id": params["request_id"]}
