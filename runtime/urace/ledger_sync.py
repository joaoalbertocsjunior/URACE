"""Economy ledger sliding-window sync for light/edge peers at million-peer scale.

Full peers: hold complete audit history.
Light peers: hold last LEDGER_BLOCK_SEAL + tail rows since seal.

A LEDGER_BLOCK_SEAL contains credit_balance_snapshot: {peer_id: balance_units}.
Light peers can compute accurate balances without full history by:
  balance = seal.credit_balance_snapshot[peer_id] + sum(tail deltas for peer_id)

This module is pure logic — no network I/O. Network transport uses existing
exchange RPC system. The cross-node sync RPC is a v3 stub.
"""
from __future__ import annotations

import hashlib
import json

SCHEMA = 'urace-ledger-sync-v1'
DEFAULT_TAIL_ROWS = 1000


def latest_seal(rows: list[dict]) -> dict | None:
    """Most recent LEDGER_BLOCK_SEAL row, or None."""
    seals = [r for r in rows if r.get('kind') == 'LEDGER_BLOCK_SEAL']
    if not seals:
        return None
    return max(seals, key=lambda r: float(r.get('at_unix', 0)))


def tail_since_seal(rows: list[dict], seal: dict | None = None) -> list[dict]:
    """Rows after the given seal (by seal's sha256). All rows if seal is None."""
    if seal is None:
        return list(rows)
    seal_sha = seal.get('sha256', '')
    # Find seal position and return everything after it
    for i, row in enumerate(rows):
        if row.get('sha256') == seal_sha:
            return rows[i + 1:]
    # Seal not found in rows — return all rows
    return list(rows)


def prune_to_window(rows: list[dict], tail_rows: int = DEFAULT_TAIL_ROWS) -> list[dict]:
    """Return: [latest_seal_row] + min(tail_rows, len(tail)) subsequent rows.
    If no seal: return last tail_rows rows (or all if fewer).
    The returned slice preserves chain continuity (starts from seal row).
    """
    seal = latest_seal(rows)
    if seal is None:
        return rows[-tail_rows:] if len(rows) > tail_rows else list(rows)
    tail = tail_since_seal(rows, seal)
    return [seal] + tail[:tail_rows]


def verify_tail(seal: dict, tail_rows: list[dict]) -> None:
    """Verify chain integrity of tail_rows starting from seal.
    Each row: row['previous'] must == previous row's sha256.
    Each row: sha256({row fields except 'sha256'}) must == row['sha256'].
    Raises ValueError on any violation.
    """
    prev_sha = seal.get('sha256', '')
    for i, row in enumerate(tail_rows):
        if row.get('previous') != prev_sha:
            raise ValueError(
                f"Chain broken at tail row {i}: previous={row.get('previous')!r} "
                f"expected={prev_sha!r}"
            )
        signed = {k: v for k, v in row.items() if k != 'sha256'}
        expected = hashlib.sha256(
            json.dumps(signed, sort_keys=True).encode()
        ).hexdigest()
        if row.get('sha256') != expected:
            raise ValueError(
                f"Hash mismatch at tail row {i}: stored={row.get('sha256')!r} "
                f"computed={expected!r}"
            )
        prev_sha = row['sha256']


def balance_from_seal(seal: dict, tail_rows: list[dict], peer_id: str) -> int:
    """Compute credit balance for peer_id from seal snapshot + tail events.

    seal.credit_balance_snapshot[peer_id] = base units at seal time.
    Then apply tail CREDIT_DELTA rows for this peer (amount_units field).
    Returns int (base units). Returns 0 if peer not in seal and no tail deltas.

    CREDIT_DELTA row fields: kind='CREDIT_DELTA', peer=peer_id, amount_units=int
    Positive amount_units = earn, negative = spend/decay.
    """
    snapshot = seal.get('credit_balance_snapshot', {})
    base = int(snapshot.get(peer_id, 0))
    delta = sum(
        int(r.get('delta_units', r.get('amount_units', 0)))
        for r in tail_rows
        if r.get('kind') == 'CREDIT_DELTA' and r.get('peer') == peer_id
    )
    return base + delta


def sync_summary(rows: list[dict]) -> dict:
    """Return sync state summary dict with keys:
    schema, total_rows, seal_at_unix, seal_sequence, tail_rows_since_seal,
    is_light_peer_sufficient (True if seal exists), pruned_row_count.
    """
    seal = latest_seal(rows)
    tail = tail_since_seal(rows, seal)
    if seal is not None:
        seal_at_unix = float(seal.get('at_unix', 0))
        seal_sequence = int(seal.get('sequence', seal.get('block_height', 0)))
    else:
        seal_at_unix = None
        seal_sequence = None
    # pruned_row_count = rows not included in [seal] + tail
    if seal is not None:
        included = 1 + len(tail)
    else:
        included = len(tail)
    pruned = len(rows) - included
    return {
        'schema': SCHEMA,
        'total_rows': len(rows),
        'seal_at_unix': seal_at_unix,
        'seal_sequence': seal_sequence,
        'tail_rows_since_seal': len(tail),
        'is_light_peer_sufficient': seal is not None,
        'pruned_row_count': max(0, pruned),
    }


def request_tail_payload(exchange) -> dict:
    """Create a sync payload a full peer would send to a light peer.
    Returns: {'seal': latest_seal_row, 'tail': tail_rows_since_seal}
    Returns {'seal': None, 'tail': []} if no seal yet.
    This is the DATA a full peer would send; actual network transport is a v3 stub.
    """
    try:
        rows = exchange.audit_rows()
    except Exception:
        rows = []
    seal = latest_seal(rows)
    if seal is None:
        return {'seal': None, 'tail': []}
    tail = tail_since_seal(rows, seal)
    return {'seal': seal, 'tail': tail}
