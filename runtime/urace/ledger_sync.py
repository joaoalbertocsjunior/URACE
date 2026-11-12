"""Economy ledger sliding-window sync for light/edge peers at million-peer scale.

Full peers: hold complete audit history.
Light peers: hold last LEDGER_BLOCK_SEAL + tail rows since seal.

A LEDGER_BLOCK_SEAL contains credit_balance_snapshot: {peer_id: balance_units}.
Light peers can compute accurate balances without full history by:
  balance = seal.credit_balance_snapshot[peer_id] + sum(tail deltas for peer_id)

This module is pure logic — no network I/O. Network transport uses existing
exchange RPC system. Cross-node sync via GET /urace/rpc/v1/ledger-tail (internet mode).
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


def _row_sha256(row: dict) -> str:
    """Compute or verify the content-addressed sha256 for a row.

    Excludes 'sha256' (the signed envelope field) and 'artifact_discovery'
    (local source binding — mutable on every code rebuild and not part of
    network identity).  Stable across rebuilds for initial_ledger entries.
    """
    signed = {k: v for k, v in row.items() if k not in ('sha256', 'artifact_discovery')}
    return hashlib.sha256(json.dumps(signed, sort_keys=True).encode()).hexdigest()


def apply_tail_payload(local_rows: list[dict], payload: dict) -> dict:
    """Merge an incoming peer tail payload into local rows.

    Content-addressed merge: rows already present (by sha256) are not duplicated.
    Chain integrity is verified before merging.

    Args:
        local_rows: existing local ledger rows
        payload: {'seal': seal_row_or_None, 'tail': [row, ...]}

    Returns:
        {'merged': merged_rows, 'added': count_of_new_rows, 'skipped': count_of_duplicate_rows}

    Raises ValueError on chain integrity failure.
    """
    seal = payload.get('seal')
    incoming_tail = payload.get('tail', [])

    if seal is not None:
        verify_tail(seal, incoming_tail)

    local_sha_set = {row.get('sha256', _row_sha256(row)) for row in local_rows}

    merged = list(local_rows)
    added = 0
    skipped = 0
    for row in incoming_tail:
        row_sha = row.get('sha256', _row_sha256(row))
        if row_sha in local_sha_set:
            skipped += 1
        else:
            merged.append(row)
            local_sha_set.add(row_sha)
            added += 1

    return {'merged': merged, 'added': added, 'skipped': skipped}


def build_sync_attestation(peer_id: str, payload_sha256: str, merged_count: int,
                            added_count: int) -> dict:
    """Build an attestation record for a completed peer sync event.

    This record can be appended to the local signed ledger as kind=LEDGER_SYNC_ATTESTED
    to provide an auditable trail of which peer syncs were accepted.

    Returns a dict suitable for passing to Ledger.append('LEDGER_SYNC_ATTESTED', record).
    """
    import time as _time
    return {
        'schema': 'urace-sync-attestation-v1',
        'peer_id': peer_id,
        'payload_sha256': payload_sha256,
        'merged_count': merged_count,
        'added_count': added_count,
        'attested_at': _time.time(),
    }


def fetch_tail_from_peer(endpoint: str, timeout: float = 10.0) -> dict:
    """Fetch ledger tail payload from a bootstrap peer via HTTP GET."""
    import urllib.request, json as _json
    url = endpoint.rstrip('/') + '/urace/rpc/v1/ledger-tail'
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return _json.loads(resp.read(65536))


def request_tail_payload(exchange) -> dict:
    """Create a sync payload a full peer would send to a light peer.
    Returns: {'seal': latest_seal_row, 'tail': tail_rows_since_seal}
    Returns {'seal': None, 'tail': []} if no seal yet.
    This is the DATA a full peer would send; served via GET /urace/rpc/v1/ledger-tail on the Exchange server.
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


def fork_resolution_policy(local_rows: list[dict], incoming_payload: dict) -> dict:
    """Detect and resolve ledger fork between local rows and incoming payload.

    Policy: prefer the longer chain (higher sequence/row count). If equal length,
    prefer the chain with the lexicographically higher head sha256 (deterministic tiebreak).

    Returns:
        {'action': 'keep_local'|'accept_incoming'|'fork_detected',
         'fork_detected': bool,
         'local_head_sha': str,
         'incoming_head_sha': str,
         'reason': str}
    """
    local_seal = latest_seal(local_rows)
    incoming_seal = incoming_payload.get('seal')
    incoming_tail = incoming_payload.get('tail', [])

    local_head_sha = local_rows[-1]['sha256'] if local_rows else '0' * 64
    incoming_head_sha = incoming_tail[-1]['sha256'] if incoming_tail else (
        incoming_seal['sha256'] if incoming_seal else '0' * 64
    )

    # Same head — no fork
    if local_head_sha == incoming_head_sha:
        return {'action': 'keep_local', 'fork_detected': False,
                'local_head_sha': local_head_sha, 'incoming_head_sha': incoming_head_sha,
                'reason': 'identical heads'}

    local_seq = int(local_seal.get('sequence', local_seal.get('block_height', 0))) if local_seal else 0
    incoming_seq = int(incoming_seal.get('sequence', incoming_seal.get('block_height', 0))) if incoming_seal else 0

    local_total = local_seq + len(local_rows)
    incoming_total = incoming_seq + len(incoming_tail)

    if incoming_total > local_total:
        return {'action': 'accept_incoming', 'fork_detected': True,
                'local_head_sha': local_head_sha, 'incoming_head_sha': incoming_head_sha,
                'reason': f'incoming chain longer ({incoming_total} > {local_total})'}
    elif local_total > incoming_total:
        return {'action': 'keep_local', 'fork_detected': True,
                'local_head_sha': local_head_sha, 'incoming_head_sha': incoming_head_sha,
                'reason': f'local chain longer ({local_total} > {incoming_total})'}
    else:
        # Equal length: deterministic tiebreak on head sha256
        if incoming_head_sha > local_head_sha:
            return {'action': 'accept_incoming', 'fork_detected': True,
                    'local_head_sha': local_head_sha, 'incoming_head_sha': incoming_head_sha,
                    'reason': 'equal length, incoming sha256 wins tiebreak'}
        return {'action': 'keep_local', 'fork_detected': True,
                'local_head_sha': local_head_sha, 'incoming_head_sha': incoming_head_sha,
                'reason': 'equal length, local sha256 wins tiebreak'}


def exchange_checkpoint(exchange, peer_id: str, peer_rows: list[dict] | None = None) -> dict:
    """Exchange chain head checkpoint with a peer (or verify local consistency).

    If peer_rows is provided (simulating a peer response), compares heads.
    Returns checkpoint dict with match/mismatch status.

    In live usage, the caller fetches peer_rows via RPC then passes them here.
    """
    import time as _t
    local_rows = []
    try:
        local_rows = exchange.audit_rows()
    except Exception:
        pass

    local_seal = latest_seal(local_rows)
    local_seq = int(local_seal.get('sequence', local_seal.get('block_height', 0))) if local_seal else 0
    local_head = local_rows[-1].get('sha256', '0' * 64) if local_rows else '0' * 64

    checkpoint = {
        'schema': SCHEMA,
        'peer_id': peer_id,
        'local_sequence': local_seq,
        'local_head_sha': local_head,
        'local_row_count': len(local_rows),
        'checked_at': _t.time(),
    }

    if peer_rows is not None:
        peer_seal = latest_seal(peer_rows)
        peer_seq = int(peer_seal.get('sequence', peer_seal.get('block_height', 0))) if peer_seal else 0
        peer_head = peer_rows[-1].get('sha256', '0' * 64) if peer_rows else '0' * 64
        match = (local_head == peer_head)
        checkpoint.update({
            'peer_sequence': peer_seq,
            'peer_head_sha': peer_head,
            'peer_row_count': len(peer_rows),
            'match': match,
            'status': 'MATCH' if match else 'CHECKPOINT_CONFLICT',
        })
        if not match:
            try:
                exchange.event('LEDGER_CHECKPOINT_CONFLICT',
                               peer=peer_id,
                               local_head=local_head,
                               peer_head=peer_head)
            except Exception:
                pass

    return checkpoint
