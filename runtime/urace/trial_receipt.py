"""Cross-peer signed trial receipts for token settlement.

A TrialReceipt is created by the borrower after a successful local qualification
and delivered to the creator peer. The creator's token_ledger then counts
receipt_verified=True events only when a valid signed receipt is on file.
"""
from __future__ import annotations

import hashlib
import time

from . import ledger_crypto
from . import peer_exchange as _px


def create_receipt(
    identity,
    feature_id: str,
    creator_peer_id: str,
    outcome_delta: float,
    borrower_peer_id: str,
) -> dict:
    """Create a signed trial receipt.

    identity: ledger_crypto.Identity instance belonging to the borrower.
    Returns {'payload': {...}, 'signature': {...}}.
    """
    payload = {
        "schema": "urace-trial-receipt-v1",
        "feature_id": feature_id,
        "creator_peer_id": creator_peer_id,
        "borrower_peer_id": borrower_peer_id,
        "outcome_delta": float(outcome_delta),
        "at_unix": time.time(),
    }
    sig = identity.sign(payload, "trial-receipt")
    return {"payload": payload, "signature": sig}


def verify_receipt(receipt: dict, borrower_public_key: dict) -> bool:
    """Verify a trial receipt signature.

    borrower_public_key: validated public key dict (urace-hybrid-keys-v1 schema).
    Returns True if valid.
    Raises ValueError on tamper or schema mismatch.
    """
    if not isinstance(receipt, dict):
        raise ValueError("receipt must be a dict")
    payload = receipt.get("payload")
    signature = receipt.get("signature")
    if not isinstance(payload, dict) or not isinstance(signature, dict):
        raise ValueError("receipt missing payload or signature")
    if payload.get("schema") != "urace-trial-receipt-v1":
        raise ValueError(
            f"unsupported receipt schema: {payload.get('schema')!r}"
        )
    # ledger_crypto.verify raises on failure, returns True on success
    ledger_crypto.verify(borrower_public_key, payload, signature, "trial-receipt")
    return True


def deliver_receipt(exchange, creator_peer_id: str, receipt: dict) -> dict:
    """Deliver a signed trial receipt to the creator peer via RPC.

    Emits TRIAL_RECEIPT_DELIVERED audit event.
    Returns the RPC result dict.
    """
    exchange.event(
        "TRIAL_RECEIPT_DELIVERED",
        creator_peer_id=creator_peer_id,
        feature_id=receipt.get("payload", {}).get("feature_id", ""),
        borrower_peer_id=receipt.get("payload", {}).get("borrower_peer_id", ""),
        outcome_delta=receipt.get("payload", {}).get("outcome_delta", 0.0),
    )
    result = _px.request(
        exchange,
        creator_peer_id,
        "exchange.trial_receipt",
        {"receipt": receipt},
    )
    return result


def handle_receipt_delivery(exchange, sender_peer_id: str, receipt: dict) -> dict:
    """Server-side handler for incoming trial receipt deliveries.

    Security: only accepts receipts where sender_peer_id == borrower_peer_id
    (relayed receipts are rejected — the borrower must deliver directly).

    Emits TRIAL_RECEIPT_RECEIVED and FEATURE_BORROW_VERIFIED audit events.
    Returns {'status': 'ok', 'receipt_recorded': True}.
    """
    if not isinstance(receipt, dict):
        return {"status": "error", "error": "invalid receipt type"}

    payload = receipt.get("payload")
    if not isinstance(payload, dict) or payload.get("schema") != "urace-trial-receipt-v1":
        return {"status": "error", "error": "invalid receipt schema"}

    borrower_peer_id = payload.get("borrower_peer_id", "")
    feature_id = payload.get("feature_id", "")
    outcome_delta = payload.get("outcome_delta", 0.0)

    # Relay-prevention security check
    if sender_peer_id != borrower_peer_id:
        return {
            "status": "error",
            "error": "sender_peer_id does not match borrower_peer_id; relayed receipts are rejected",
        }

    # Verify borrower signature
    try:
        p = exchange.load()
        borrower_public = exchange.trusted_crypto(p, borrower_peer_id)
        verify_receipt(receipt, borrower_public)
    except (ValueError, KeyError) as exc:
        return {"status": "error", "error": f"signature verification failed: {exc}"}

    exchange.event(
        "TRIAL_RECEIPT_RECEIVED",
        feature_id=feature_id,
        borrower_peer_id=borrower_peer_id,
        outcome_delta=float(outcome_delta),
        receipt_verified=True,
        sender_peer_id=sender_peer_id,
    )

    # Emit FEATURE_BORROW_VERIFIED so token_ledger.balance() can count it
    exchange.event(
        "FEATURE_BORROW_VERIFIED",
        feature_id=feature_id,
        borrower_peer_id=borrower_peer_id,
        outcome_delta=float(outcome_delta),
        receipt_verified=True,
        receipt_payload_sha256=hashlib.sha256(
            ledger_crypto.canonical(payload)
        ).hexdigest(),
    )

    return {"status": "ok", "receipt_recorded": True}
