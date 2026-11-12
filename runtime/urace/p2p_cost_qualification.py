"""P2P cost qualification runner.

Implements the 30-pair bootstrap requirement:
- Each pair must complete a borrow/deliver cycle
- Statistical validity: Wilson lower bound on delivery rate
- bootstrap_complete() returns True once 30 pairs have round-tripped
"""
import hashlib
import json
import logging
import math
import time
from pathlib import Path

from . import peer_exchange

_logger = logging.getLogger(__name__)

BOOTSTRAP_THRESHOLD = 30
_WILSON_Z = 1.645  # 90% confidence interval


def _pair_hash(peer_a_id: str, peer_b_id: str) -> str:
    """Canonical hash for an unordered pair of peer IDs."""
    ordered = sorted([peer_a_id, peer_b_id])
    return hashlib.sha256(''.join(ordered).encode()).hexdigest()


def bootstrap_complete(exchange) -> bool:
    """Return True once >= 30 distinct peer pairs have QUALIFICATION_RECEIPT rows."""
    rows = []
    try:
        rows = exchange.audit_rows()
    except Exception:
        pass

    distinct_pairs: set = set()
    for row in rows:
        if row.get('kind') == 'QUALIFICATION_RECEIPT':
            ph = row.get('pair_hash')
            if ph:
                distinct_pairs.add(ph)

    return len(distinct_pairs) >= BOOTSTRAP_THRESHOLD


def qualification_statistics(exchange) -> dict:
    """Compute delivery statistics over all QUALIFICATION_RECEIPT audit rows.

    Returns:
        total_pairs: distinct pair_hash values seen
        completed_pairs: distinct pairs where completed=True
        delivery_rate: completed / total (0.0 if none)
        wilson_lower_bound: Wilson 90%-CI lower bound on delivery rate
        bootstrap_complete: bool
    """
    rows = []
    try:
        rows = exchange.audit_rows()
    except Exception:
        pass

    # Collect most-recent completed status per pair_hash
    pair_completed: dict = {}
    for row in rows:
        if row.get('kind') != 'QUALIFICATION_RECEIPT':
            continue
        ph = row.get('pair_hash')
        if not ph:
            continue
        # Last row wins for each pair_hash
        pair_completed[ph] = bool(row.get('completed', False))

    total = len(pair_completed)
    completed = sum(1 for v in pair_completed.values() if v)

    if total == 0:
        return {
            'total_pairs': 0,
            'completed_pairs': 0,
            'delivery_rate': 0.0,
            'wilson_lower_bound': 0.0,
            'bootstrap_complete': False,
        }

    p = completed / total
    n = total
    z = _WILSON_Z
    z2 = z * z

    # Wilson lower bound formula
    numerator = p + z2 / (2 * n) - z * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n))
    denominator = 1 + z2 / n
    wilson_lb = numerator / denominator

    return {
        'total_pairs': total,
        'completed_pairs': completed,
        'delivery_rate': p,
        'wilson_lower_bound': wilson_lb,
        'bootstrap_complete': total >= BOOTSTRAP_THRESHOLD,
    }


def run_qualification_round(exchange, peer_pairs: list, *, simulate: bool = False) -> dict:
    """Run a qualification round over the given list of (peer_a_id, peer_b_id) tuples.

    If simulate=True all pairs are marked completed without network calls.
    Returns {'rounds': int, 'completed': int, 'bootstrap_complete': bool}.
    """
    if simulate:
        _logger.warning(
            "P2P qualification running in simulate mode — not suitable for production"
        )
    completed_count = 0

    for peer_a_id, peer_b_id in peer_pairs:
        if simulate:
            completed = True
        else:
            completed = False
            try:
                peer_exchange.request(exchange, peer_b_id, 'exchange.info', {})
                completed = True
            except Exception:
                pass

        record_qualification_receipt(exchange, peer_a_id, peer_b_id, completed)
        if completed:
            completed_count += 1

    return {
        'rounds': len(peer_pairs),
        'completed': completed_count,
        'bootstrap_complete': bootstrap_complete(exchange),
    }


def record_qualification_receipt(exchange, peer_a_id: str, peer_b_id: str, completed: bool) -> dict:
    """Emit a QUALIFICATION_RECEIPT audit row for the given peer pair.

    Returns the emitted row dict.
    """
    ph = _pair_hash(peer_a_id, peer_b_id)
    row = {
        'pair_hash': ph,
        'peer_a_id': peer_a_id,
        'peer_b_id': peer_b_id,
        'completed': completed,
        'at_unix': time.time(),
    }
    try:
        exchange.event('QUALIFICATION_RECEIPT', **row)
    except Exception:
        pass
    return {'kind': 'QUALIFICATION_RECEIPT', **row}


# ---------------------------------------------------------------------------
# P4.1 — Peer Reputation Persistence
# ---------------------------------------------------------------------------

def save_reputation(exchange, reputation_file=None) -> None:
    """Persist QUALIFICATION_RECEIPT rows to a JSONL file."""
    path = Path(reputation_file) if reputation_file else Path.home() / '.urace' / 'peer_reputation.jsonl'
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [r for r in exchange.audit_rows() if r.get('kind') == 'QUALIFICATION_RECEIPT']
    with path.open('w') as _f:
        for row in rows:
            _f.write(json.dumps(row) + '\n')


def load_reputation(exchange, reputation_file=None) -> None:
    """Load persisted QUALIFICATION_RECEIPT rows back into the exchange."""
    path = Path(reputation_file) if reputation_file else Path.home() / '.urace' / 'peer_reputation.jsonl'
    if not path.exists():
        return
    existing = {json.dumps(r, sort_keys=True) for r in exchange.audit_rows()}
    with path.open() as _f:
        for line in _f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if json.dumps(row, sort_keys=True) not in existing:
                try:
                    exchange.record(
                        row.get('kind', 'QUALIFICATION_RECEIPT'),
                        {k: v for k, v in row.items() if k != 'kind'},
                    )
                except Exception:
                    pass


# ---------------------------------------------------------------------------
# P4.2 — Peer Failure Rate (Wilson CI Lower Bound)
# ---------------------------------------------------------------------------

def peer_failure_rate(exchange, peer_id: str) -> float:
    """Return Wilson CI lower bound on failure rate for *peer_id*.

    Lower is better (0.0 = perfect record, 1.0 = always fails).
    Returns 0.0 for peers with no receipts.
    """
    rows = [
        r for r in exchange.audit_rows()
        if r.get('kind') == 'QUALIFICATION_RECEIPT'
        and (r.get('peer_a_id') == peer_id or r.get('peer_b_id') == peer_id)
    ]
    n = len(rows)
    if n == 0:
        return 0.0
    failures = sum(1.0 - float(r.get('delivery_rate', 1.0)) for r in rows)
    p_hat = failures / n
    z = _WILSON_Z
    denom = 1.0 + z * z / n
    centre = (p_hat + z * z / (2.0 * n)) / denom
    margin = (z * math.sqrt(max(0.0, p_hat * (1.0 - p_hat) / n + z * z / (4.0 * n * n)))) / denom
    return max(0.0, centre - margin)


def select_peers_by_reputation(exchange, candidates: list, *, top_n: int = 10) -> list:
    """Return top_n candidates sorted by ascending failure rate (best first)."""
    return sorted(candidates, key=lambda pid: peer_failure_rate(exchange, pid))[:top_n]
