"""P2P audit ledger compaction — reduces sync cost for growing append-only logs.

Problem: append-only audit rows grow unboundedly. For P2P networks this causes:
  - Slow initial sync (new peer must replay full history)
  - High storage on resource-constrained peers
  - O(n) `_request_rows()` scans even with caching

Solutions implemented here:
  1. Contract compaction — RELEASED/RESOLVED work contracts replaced by a single
     WORK_CONTRACT_SUMMARY row (preserves final state, discards intermediate rows).
     `_request_rows()` in peer_work_market.py respects summaries.

  2. Ledger checkpointing — LEDGER_CHECKPOINT row records a snapshot of all peer
     credit balances at a point in time. New peers can bootstrap from the latest
     checkpoint + tail rows instead of replaying all history.

  3. Credit balance checkpoints — per-peer CREDIT_BALANCE_CHECKPOINT rows written
     to the signed_ledger, allowing O(tail) balance lookups instead of O(all).

Compaction is lossless for system operation:
  - The original rows remain in the audit log (append-only invariant preserved)
  - WORK_CONTRACT_SUMMARY serves as a verified digest of the compacted rows
  - New peers can choose: replay from genesis, or start from checkpoint + tail

Row kinds introduced:
  WORK_CONTRACT_SUMMARY  — compact summary of a closed work contract
  LEDGER_CHECKPOINT      — full credit balance snapshot for P2P bootstrap
"""
from __future__ import annotations
import hashlib
import json
import time

SCHEMA = 'urace-ledger-compaction-v1'

# Only compact contracts older than this (don't compact recently closed ones)
COMPACT_OLDER_THAN_SECONDS = 7 * 86400   # 7 days

# How many recent rows to keep uncompacted for fast recent-state access
CHECKPOINT_TAIL_ROWS = 500


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _row_digest(rows: list[dict]) -> str:
    """SHA-256 of canonical JSON of the row list — used to verify compaction integrity."""
    payload = json.dumps(rows, sort_keys=True, separators=(',', ':')).encode()
    return hashlib.sha256(payload).hexdigest()


# ── Contract compaction ───────────────────────────────────────────────────────

def compact_closed_contracts(
    exchange,
    older_than_days: float = 7.0,
) -> dict:
    """Summarize RELEASED/RESOLVED work contracts older than N days.

    For each qualifying contract, appends a WORK_CONTRACT_SUMMARY row that
    encodes the final state, parties, budget, and a digest of the original rows.
    Callers (e.g. _request_rows) can detect the summary and skip replaying
    the full contract history.

    Returns:
        {'compacted': [request_ids], 'skipped': int, 'summary_rows_added': int}
    """
    cutoff = time.time() - older_than_days * 86400
    from . import peer_work_market as _wm

    try:
        all_rows = exchange.audit_rows()
    except Exception:
        return {'compacted': [], 'skipped': 0, 'summary_rows_added': 0}

    # Find already-summarised request_ids (don't double-compact)
    summarised: set[str] = {
        r.get('request_id', '')
        for r in all_rows
        if r.get('kind') == 'WORK_CONTRACT_SUMMARY'
    }

    # Find all WORK_REQUEST rows
    request_rows = [r for r in all_rows if r.get('kind') == 'WORK_REQUEST']
    compacted = []
    skipped   = 0

    for req in request_rows:
        rid = req.get('request_id', '')
        if not rid or rid in summarised:
            skipped += 1
            continue

        # Only compact old enough rows
        req_time = float(req.get('at_unix', time.time()))
        if req_time > cutoff:
            skipped += 1
            continue

        # Derive current state
        st = _wm.escrow_state(rid, exchange)
        if st['state'] not in ('RELEASED', 'RESOLVED'):
            skipped += 1
            continue

        # Gather all rows for this contract
        contract_rows = [r for r in all_rows if r.get('request_id') == rid]
        digest = _row_digest(contract_rows)

        # Build summary
        hired_peers = list({r.get('hired_peer_id') or r.get('bidder_id')
                            for r in contract_rows
                            if r.get('kind') in ('WORK_DELIVERY', 'WORK_ACCEPTED')
                            and (r.get('hired_peer_id') or r.get('bidder_id'))})
        exchange.append_audit_row({
            'kind': 'WORK_CONTRACT_SUMMARY',
            'request_id': rid,
            'requester_id': req.get('requester_id', ''),
            'hired_peers': hired_peers,
            'final_state': st['state'],
            'budget_units': req.get('budget_units', 0),
            'spec': req.get('spec', ''),
            'compacted_row_count': len(contract_rows),
            'digest': digest,
            'original_at_unix': req_time,
            'at_unix': time.time(),
            'at': _now_iso(),
        })
        compacted.append(rid)

    return {
        'compacted': compacted,
        'skipped': skipped,
        'summary_rows_added': len(compacted),
    }


# ── Ledger checkpoint (P2P sync bootstrap) ────────────────────────────────────

def ledger_checkpoint(exchange, root: str) -> str:
    """Write a LEDGER_CHECKPOINT row for P2P bootstrap.

    The checkpoint encodes:
      - credit balances for all known peers (snapshot of current state)
      - total row count at checkpoint time
      - audit chain root hash (tamper-evidence)
      - tail_start_index: new peers can fetch rows[tail_start_index:] + checkpoint

    New peers: fetch latest LEDGER_CHECKPOINT, seed state from it, then replay
    rows after checkpoint['tail_start_index'] to reach current state.

    Returns checkpoint_id.
    """
    from . import peer_work_market as _wm, credit_ledger as _cl

    try:
        all_rows = exchange.audit_rows()
    except Exception:
        all_rows = []

    # Gather all peer_ids from credit deltas
    peer_ids: set[str] = set()
    for r in all_rows:
        if r.get('kind') == 'CREDIT_DELTA':
            pid = r.get('peer', '')
            if pid:
                peer_ids.add(pid)

    # Snapshot balances
    balances: dict[str, int] = {}
    for pid in sorted(peer_ids):
        try:
            balances[pid] = _cl.balance(root, pid)
        except Exception:
            pass

    # Compute tail start (keep CHECKPOINT_TAIL_ROWS uncompacted for fast access)
    total_rows  = len(all_rows)
    tail_start  = max(0, total_rows - CHECKPOINT_TAIL_ROWS)

    # Audit chain root for tamper-evidence
    chain_root = _wm.audit_chain_root(exchange)

    checkpoint_id = f'ckpt-{int(time.time() * 1000)}'
    exchange.append_audit_row({
        'kind': 'LEDGER_CHECKPOINT',
        'checkpoint_id': checkpoint_id,
        'peer_balances': balances,
        'peer_count': len(peer_ids),
        'total_rows_at_checkpoint': total_rows,
        'tail_start_index': tail_start,
        'chain_root': chain_root,
        'at_unix': time.time(),
        'at': _now_iso(),
    })
    return checkpoint_id


def latest_checkpoint(exchange) -> dict | None:
    """Return the most recent LEDGER_CHECKPOINT row, or None."""
    try:
        rows = exchange.audit_rows()
    except Exception:
        return None
    ckpts = [r for r in rows if r.get('kind') == 'LEDGER_CHECKPOINT']
    if not ckpts:
        return None
    return max(ckpts, key=lambda r: float(r.get('at_unix', 0)))


def seal_ledger_block(exchange, root: str) -> dict:
    """Seal a LEDGER_BLOCK_SEAL row: unified PoQ tamper chain + balance snapshot.

    A sealed block combines two previously separate concerns:
      1. Tamper-evidence: sha256(all rows in block) chained to prev_block_hash
      2. Search optimization: balance_snapshot enables O(tail) balance lookups

    After sealing, callers can call balance_fast() instead of replaying all rows.
    Auto-triggered by compact checkpoint when ledger_block_mode=True.
    """
    from . import credit_ledger as _cl
    import hashlib as _bhl, json as _bjson

    try:
        all_rows = exchange.audit_rows()
    except Exception:
        all_rows = []

    # Find previous block seal
    prev_seals = [r for r in all_rows if r.get('kind') == 'LEDGER_BLOCK_SEAL']
    if prev_seals:
        prev = max(prev_seals, key=lambda r: int(r.get('block_height', 0)))
        prev_height = int(prev.get('block_height', 0))
        prev_hash = prev.get('block_hash', '0' * 64)
        row_start = int(prev.get('row_end_index', 0))
    else:
        prev_height = -1
        prev_hash = '0' * 64
        row_start = 0

    block_rows = all_rows[row_start:]
    if not block_rows:
        return {'status': 'no_new_rows', 'block_height': prev_height}

    # Merkle-style: sha256 of canonical JSON of all rows in this block
    rows_payload = _bjson.dumps(block_rows, sort_keys=True, separators=(',', ':')).encode()
    rows_hash = _bhl.sha256(rows_payload).hexdigest()
    block_hash = _bhl.sha256(f'{prev_hash}:{rows_hash}'.encode()).hexdigest()

    block_height = prev_height + 1
    row_end_index = len(all_rows)

    # Snapshot credit balances for all peers seen in this block
    peer_ids: set = set()
    for r in block_rows:
        pid = r.get('peer', '')
        if pid:
            peer_ids.add(pid)
    credit_snapshot: dict = {}
    for pid in sorted(peer_ids):
        try:
            credit_snapshot[pid] = _cl.balance(root, pid)
        except Exception:
            pass

    exchange.append_audit_row({
        'kind': 'LEDGER_BLOCK_SEAL',
        'block_height': block_height,
        'block_hash': block_hash,
        'prev_block_hash': prev_hash,
        'rows_hash': rows_hash,
        'row_start_index': row_start,
        'row_end_index': row_end_index,
        'row_count': len(block_rows),
        'credit_balance_snapshot': credit_snapshot,
        'at_unix': time.time(),
        'at': _now_iso(),
    })

    # Maintainer reward: sealer earns for chain-integrity work
    try:
        _policy = exchange.load()
        _seal_reward = int(_policy.get('p2p', {}).get('seal_reward_units', 1))
    except Exception:
        _seal_reward = 1
    try:
        _local_id = exchange.identity().get('peer_id', '')
    except Exception:
        _local_id = ''
    if _seal_reward > 0 and _local_id:
        exchange.append_audit_row({
            'kind': 'CREDIT_DELTA',
            'direction': 'seal_reward',
            'peer': _local_id,
            'amount_units': _seal_reward,
            'block_height': block_height,
            'reason': 'ledger_block_seal',
            'at_unix': time.time(),
            'at': _now_iso(),
        })

    return {
        'status': 'sealed',
        'block_height': block_height,
        'block_hash': block_hash,
        'row_count': len(block_rows),
        'peers_snapshotted': len(credit_snapshot),
        'seal_reward_units': _seal_reward,
    }


def balance_fast(root: str, peer_id: str, exchange) -> int:
    """O(tail) credit balance using the latest sealed block snapshot.

    Falls back to full O(all) balance() if no sealed block exists.
    Use this when performance matters and exchange is available.
    """
    from . import credit_ledger as _cl

    try:
        all_rows = exchange.audit_rows()
    except Exception:
        return _cl.balance(root, peer_id)

    seals = [r for r in all_rows if r.get('kind') == 'LEDGER_BLOCK_SEAL']
    if not seals:
        return _cl.balance(root, peer_id)

    latest_seal = max(seals, key=lambda r: int(r.get('block_height', 0)))
    snapshot = latest_seal.get('credit_balance_snapshot', {})
    base = int(snapshot.get(peer_id, 0))
    tail_start = int(latest_seal.get('row_end_index', 0))
    tail_rows = all_rows[tail_start:]

    # Replay only tail rows (the unsealed portion)
    delta = 0
    for r in tail_rows:
        if r.get('kind') == 'CREDIT_DELTA' and r.get('peer') == peer_id:
            delta += int(r.get('delta_units', 0) or 0)

    return base + delta


def sync_tail_rows(exchange) -> tuple[dict | None, list[dict]]:
    """Return (latest_checkpoint, tail_rows) for P2P bootstrap.

    New peer workflow:
      ckpt, tail = sync_tail_rows(remote_exchange)
      local_exchange.seed_from_checkpoint(ckpt)   # set balances from snapshot
      for row in tail:
          local_exchange.append_audit_row(row)    # replay recent history

    Returns (None, all_rows) if no checkpoint exists (full sync required).
    """
    ckpt = latest_checkpoint(exchange)
    try:
        all_rows = exchange.audit_rows()
    except Exception:
        return ckpt, []

    if ckpt is None:
        return None, all_rows

    tail_start = int(ckpt.get('tail_start_index', 0))
    return ckpt, all_rows[tail_start:]


# ── Credit balance checkpoints ────────────────────────────────────────────────

def compact_credit_history(root: str, peer_id: str) -> bool:
    """Write a CREDIT_BALANCE_CHECKPOINT to the signed ledger.

    Subsequent balance() lookups start from the checkpoint balance and add
    only the tail deltas, reducing O(all_rows) to O(tail_rows).

    Returns True if checkpoint was written, False if balance is 0 or error.
    """
    from . import credit_ledger as _cl
    try:
        bal = _cl.balance(root, peer_id)
    except Exception:
        return False
    if bal == 0:
        return False
    try:
        from .signed_ledger import Ledger
        from pathlib import Path
        ledger = Ledger(Path(root) / 'credit-ledger')
        with ledger.lock():
            payload = json.dumps({
                'peer': peer_id,
                'kind': 'CREDIT_BALANCE_CHECKPOINT',
                'balance_units': bal,
                'at_unix': time.time(),
                'at': _now_iso(),
            }, sort_keys=True).encode()
            ledger.write(payload)
        return True
    except Exception:
        return False


# ── P2P optimal supply derivation ─────────────────────────────────────────────
# (placed here as a companion to compaction since supply sizing is driven by
# the same ledger-growth and sync-latency constraints)

def consensus_row_stats(exchange) -> dict:
    """Measure actual audit log row statistics for consensus-based supply sizing.

    Instead of guessing avg_row_bytes and rows_per_feature, derive them from
    what the network has actually produced.

    Returns:
        {
          'avg_row_bytes': int,       # measured average JSON row size
          'rows_per_feature': float,  # average rows per completed work contract
          'total_rows': int,
          'completed_contracts': int,
        }
    """
    import json as _json
    try:
        rows = exchange.audit_rows()
    except Exception:
        return {'avg_row_bytes': 400, 'rows_per_feature': 20,
                'total_rows': 0, 'completed_contracts': 0}

    if not rows:
        return {'avg_row_bytes': 400, 'rows_per_feature': 20,
                'total_rows': 0, 'completed_contracts': 0}

    # Measure row sizes
    sizes = [len(_json.dumps(r, sort_keys=True, separators=(',', ':')).encode())
             for r in rows[:min(1000, len(rows))]]  # sample up to 1000 rows
    avg_bytes = int(sum(sizes) / len(sizes)) if sizes else 400

    # Measure rows per completed contract
    completed_rids: set[str] = {
        r.get('request_id', '')
        for r in rows
        if r.get('kind') in ('WORK_CONTRACT_SUMMARY',)
        or (r.get('kind') == 'WORK_VERIFIED' and r.get('approved'))
    } - {''}
    if completed_rids:
        total_contract_rows = sum(
            1 for r in rows if r.get('request_id', '') in completed_rids
        )
        rows_per_feature = total_contract_rows / len(completed_rids)
    else:
        rows_per_feature = 20.0

    return {
        'avg_row_bytes': avg_bytes,
        'rows_per_feature': round(rows_per_feature, 1),
        'total_rows': len(rows),
        'completed_contracts': len(completed_rids),
    }


def consensus_mint_per_adoption(exchange) -> int:
    """Derive the actual average mint amount per adoption from credit history.

    Reads CREDIT_DELTA earn rows tagged with feature_id to compute the
    observed mint rate. Falls back to UNIT/100 (0.01 tokens) when no history.
    """
    from . import credit_ledger as _cl
    try:
        rows = exchange.audit_rows()
    except Exception:
        return _cl.UNIT // 100

    feature_mints: dict[str, int] = {}
    for r in rows:
        if r.get('kind') == 'CREDIT_DELTA' and r.get('direction') == 'earn':
            fid = r.get('feature_id', '')
            if fid:
                feature_mints[fid] = feature_mints.get(fid, 0) + abs(int(r.get('delta_units', 0) or 0))

    if not feature_mints:
        return _cl.UNIT // 100

    total = sum(feature_mints.values())
    count = len(feature_mints)
    return max(_cl.UNIT // 10_000, total // count)


def p2p_optimal_supply(
    max_network_peers: int = 1_000,
    target_ledger_mb: float = 50.0,
    sync_bandwidth_kbps: int = 1_000,
    target_sync_seconds: float = 30.0,
    avg_row_bytes: int | None = None,       # None = auto-measure from exchange
    rows_per_feature: int | None = None,    # None = auto-measure from exchange
    adoption_rate: float = 0.10,
    mint_per_adoption_units: int | None = None,
    baseline_per_peer_units: int | None = None,
    revenue_feature_fraction: float = 0.65,  # fraction of features that generate earn events
    exchange=None,                          # when provided, consensus overrides manual inputs
) -> dict:
    """Derive P2P-optimal token supply limits from network physics.

    Inputs:
      max_network_peers        — intended max peers (not current count)
      target_ledger_mb         — acceptable ledger size for full sync fallback
      sync_bandwidth_kbps      — effective P2P bandwidth (conservative: 1 Mbps)
      target_sync_seconds      — target initial sync time for new peers
      avg_row_bytes            — average audit row size in bytes (JSON)
      rows_per_feature         — audit rows per complete feature lifecycle
      adoption_rate            — fraction of network expected to adopt any feature
      mint_per_adoption_units  — base units minted per adoption (default UNIT/100)
      baseline_per_peer_units  — baseline grant per new peer (default 3×UNIT)
      revenue_feature_fraction — fraction of ledger features with active earn potential
                                 (0-cost/free features consume infra but contribute 0 to supply;
                                  default 0.65: conservative 35% free/decayed assumption.
                                  NOTE: initial_ledger features only count toward sync budget
                                  AFTER equity-grant; pre-grant they don't enter live audit.)

    Returns a dict with:
      max_features         — ledger capacity in features
      bandwidth_cap_mb     — max sync payload at given bandwidth + target seconds
      effective_ledger_mb  — min(target_ledger_mb, bandwidth_cap_mb)
      global_supply_units  — total network-optimal supply
      per_peer_cap_units   — recommended BASE_CAP_UNITS (per-peer ceiling)
      current_cap_units    — current BASE_CAP_UNITS in credit_ledger
      verdict              — 'OK' | 'OVERSUPPLIED' | 'UNDERSUPPLIED'
      notes                — human-readable explanation
    """
    from . import credit_ledger as _cl

    # Auto-measure from network consensus when exchange provided
    if exchange is not None:
        stats = consensus_row_stats(exchange)
        if avg_row_bytes is None:
            avg_row_bytes = stats['avg_row_bytes']
        if rows_per_feature is None:
            rows_per_feature = max(1, int(stats['rows_per_feature']))
        if mint_per_adoption_units is None:
            mint_per_adoption_units = consensus_mint_per_adoption(exchange)
    else:
        if avg_row_bytes is None:
            avg_row_bytes = 400
        if rows_per_feature is None:
            rows_per_feature = 20

    if mint_per_adoption_units is None:
        mint_per_adoption_units = _cl.UNIT // 10    # 0.1 tokens (avg across adoption ranks)
    if baseline_per_peer_units is None:
        baseline_per_peer_units = _cl.BASELINE_GRANT_UNITS

    # Bandwidth constraint: how large can the ledger be for target sync time?
    bandwidth_cap_bytes = sync_bandwidth_kbps * 1024 * target_sync_seconds
    bandwidth_cap_mb    = bandwidth_cap_bytes / (1024 * 1024)

    effective_ledger_bytes = min(target_ledger_mb, bandwidth_cap_mb) * 1024 * 1024

    # Feature capacity
    max_rows        = int(effective_ledger_bytes / max(1, avg_row_bytes))
    max_features    = max_rows // max(1, rows_per_feature)

    # Token supply: revenue features × expected adoptions × mint + peers × baseline
    # revenue_feature_fraction excludes 0-cost/free features (infra consumers, 0 earn events)
    revenue_features = max(1, int(max_features * max(0.0, min(1.0, revenue_feature_fraction))))
    avg_adoptions_per_feature = max(1, int(max_network_peers * adoption_rate))
    supply_from_features = revenue_features * avg_adoptions_per_feature * mint_per_adoption_units
    supply_from_baseline = max_network_peers * baseline_per_peer_units
    global_supply        = supply_from_features + supply_from_baseline

    per_peer_cap = global_supply // max(1, max_network_peers)

    current_cap = _cl.BASE_CAP_UNITS
    ratio       = per_peer_cap / max(1, current_cap)

    if ratio > 1.2:
        verdict = 'UNDERSUPPLIED'
        notes   = (
            f'Ledger can support {max_features} features × {avg_adoptions_per_feature} '
            f'adoptions each. Optimal per-peer cap ({per_peer_cap/_cl.UNIT:.0f} tokens) '
            f'is {ratio:.1f}× current ({current_cap/_cl.UNIT:.0f} tokens). '
            f'Consider raising BASE_CAP_UNITS.'
        )
    elif ratio < 0.8:
        verdict = 'OVERSUPPLIED'
        notes   = (
            f'Current per-peer cap ({current_cap/_cl.UNIT:.0f} tokens) exceeds '
            f'P2P-optimal ({per_peer_cap/_cl.UNIT:.0f} tokens) by {1/ratio:.1f}×. '
            f'Risk: ledger grows faster than peers can sync. '
            f'Consider reducing BASE_CAP_UNITS or increasing target_ledger_mb.'
        )
    else:
        verdict = 'OK'
        notes   = (
            f'P2P-optimal supply ({per_peer_cap/_cl.UNIT:.0f} tokens/peer) is '
            f'within 20% of current cap ({current_cap/_cl.UNIT:.0f} tokens/peer).'
        )

    free_features = max_features - revenue_features
    free_sync_cost_bytes = free_features * max(1, rows_per_feature) * max(1, avg_row_bytes)
    return {
        'max_features': max_features,
        'revenue_features': revenue_features,
        'free_features': free_features,
        'free_feature_sync_cost_bytes': free_sync_cost_bytes,
        'max_rows': max_rows,
        'bandwidth_cap_mb': round(bandwidth_cap_mb, 2),
        'effective_ledger_mb': round(min(target_ledger_mb, bandwidth_cap_mb), 2),
        'avg_adoptions_per_feature': avg_adoptions_per_feature,
        'global_supply_units': global_supply,
        'global_supply_tokens': round(global_supply / _cl.UNIT, 2),
        'per_peer_cap_units': per_peer_cap,
        'per_peer_cap_tokens': round(per_peer_cap / _cl.UNIT, 2),
        'current_cap_units': current_cap,
        'current_cap_tokens': round(current_cap / _cl.UNIT, 2),
        'verdict': verdict,
        'notes': notes,
        'inputs': {
            'max_network_peers': max_network_peers,
            'target_ledger_mb': target_ledger_mb,
            'sync_bandwidth_kbps': sync_bandwidth_kbps,
            'target_sync_seconds': target_sync_seconds,
            'avg_row_bytes': avg_row_bytes,
            'rows_per_feature': rows_per_feature,
            'adoption_rate': adoption_rate,
            'revenue_feature_fraction': revenue_feature_fraction,
        },
    }
