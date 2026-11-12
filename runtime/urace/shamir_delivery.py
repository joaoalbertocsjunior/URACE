"""Shamir DEK share delivery over peer_exchange RPC.

Handles the network transport for Shamir secret sharing:
- request_share: request one share from a holder peer
- collect_shares: gather k shares from k holder peers
- reconstruct_dek: reconstruct the secret from collected shares
- handle_share_request: server-side handler for incoming share requests
"""
from __future__ import annotations

import base64
import hashlib

from . import shamir as _shamir
from . import peer_exchange as _px


def request_share(exchange, holder_peer_id: str, feature_id: str, share_index: int) -> dict:
    """Request one Shamir share from a holder peer.

    Calls exchange.shamir_deliver RPC and emits SHAMIR_SHARE_REQUESTED audit event.
    Returns the result dict from the RPC.
    """
    exchange.event(
        "SHAMIR_SHARE_REQUESTED",
        feature_id=feature_id,
        share_index=share_index,
        holder_peer_id=holder_peer_id,
    )
    result = _px.request(
        exchange,
        holder_peer_id,
        "exchange.shamir_deliver",
        {
            "feature_id": feature_id,
            "share_index": share_index,
            "requester_peer_id": exchange.identity()["peer_id"],
        },
    )
    return result


def collect_shares(
    exchange,
    feature_id: str,
    threshold: int,
    holder_peers: list,
) -> list:
    """Gather at least *threshold* Shamir shares from holder peers.

    holder_peers: list of (peer_id, share_index) tuples.

    Stops once *threshold* successful responses are collected.
    Raises ValueError if fewer than *threshold* valid responses are received.
    Returns list of (share_index, share_bytes) tuples suitable for shamir.reconstruct().
    """
    collected: list[tuple[int, bytes]] = []
    for peer_id, share_index in holder_peers:
        if len(collected) >= threshold:
            break
        try:
            resp = request_share(exchange, peer_id, feature_id, share_index)
        except Exception:
            continue
        if isinstance(resp, dict) and resp.get("status") == "ok" and "share_b64" in resp:
            try:
                share_bytes = base64.b64decode(resp["share_b64"])
                collected.append((share_index, share_bytes))
            except Exception:
                continue
    if len(collected) < threshold:
        raise ValueError(
            f"collect_shares: needed {threshold} shares for feature {feature_id!r}, "
            f"got {len(collected)}"
        )
    return collected


def reconstruct_dek(
    exchange,
    feature_id: str,
    threshold: int,
    holder_peers: list,
) -> bytes:
    """Collect shares then reconstruct the DEK secret.

    Emits SHAMIR_DEK_RECONSTRUCTED audit event.
    Returns the reconstructed secret bytes.
    """
    shares = collect_shares(exchange, feature_id, threshold, holder_peers)
    secret = _shamir.reconstruct(shares)
    exchange.event(
        "SHAMIR_DEK_RECONSTRUCTED",
        feature_id=feature_id,
        threshold=threshold,
        shares_used=len(shares),
        secret_sha256=hashlib.sha256(secret).hexdigest(),
    )
    return secret


def handle_share_request(
    exchange,
    requesting_peer_id: str,
    feature_id: str,
    share_index: int,
    requester_peer_id: str,
) -> dict:
    """Server-side handler for incoming Shamir share requests.

    Scans the local audit chain for a SHAMIR_SHARE_STORED row with matching
    feature_id and share_index.  If found, returns the share; otherwise returns
    a not_found response.
    """
    share_bytes: bytes | None = None
    for row in exchange.audit_rows():
        if (
            row.get("kind") == "SHAMIR_SHARE_STORED"
            and row.get("feature_id") == feature_id
            and row.get("share_index") == share_index
        ):
            raw = row.get("share_b64") or row.get("share_bytes_b64")
            if raw:
                try:
                    share_bytes = base64.b64decode(raw)
                    break
                except Exception:
                    continue

    if share_bytes is not None:
        exchange.event(
            "SHAMIR_SHARE_DELIVERED",
            feature_id=feature_id,
            share_index=share_index,
            requester_peer_id=requester_peer_id,
            requesting_peer_id=requesting_peer_id,
        )
        return {
            "status": "ok",
            "share_b64": base64.b64encode(share_bytes).decode(),
            "feature_id": feature_id,
            "share_index": share_index,
        }

    return {
        "status": "not_found",
        "feature_id": feature_id,
        "share_index": share_index,
    }
