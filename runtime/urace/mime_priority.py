"""Node MIME replication priority auto-calibration.

Each node tracks which MIME types its own features borrow most.
Used to prioritize which chunks to replicate in background.
"""
import time
from datetime import datetime, timezone

_CALIBRATION_CACHE: dict = {}  # peer_id -> last_calibrated_unix


def calibrate_mime_priority(exchange) -> dict[str, float]:
    """Scan audit rows for FEATURE_BORROWED by this node.

    Look up each feature's content_type from its EQUITY_GRANT.
    Count frequencies; normalize to {content_type: weight} summing to 1.0.
    """
    try:
        rows = exchange.audit_rows()
        local_id = exchange.local_peer_id() if hasattr(exchange, 'local_peer_id') else ''
    except Exception:
        return {}

    # Build content_type index from EQUITY_GRANT rows
    ct_index: dict[str, str] = {}
    for r in rows:
        if r.get('kind') == 'EQUITY_GRANT':
            fid = r.get('feature_id', '')
            ct = r.get('content_type', '')
            if fid and ct:
                ct_index[fid] = ct

    # Count borrowed MIME types for this node
    counts: dict[str, int] = {}
    for r in rows:
        if r.get('kind') == 'FEATURE_BORROWED':
            peer = r.get('peer_id', r.get('borrower_peer_id', ''))
            if local_id and peer and peer != local_id:
                continue
            fid = r.get('feature_id', '')
            ct = ct_index.get(fid, '')
            if ct:
                counts[ct] = counts.get(ct, 0) + 1

    # Also seed from own EQUITY_GRANT rows — new node with no borrows still gets signal
    for r in rows:
        if r.get('kind') == 'EQUITY_GRANT':
            if local_id and r.get('peer_id', '') != local_id:
                continue
            ct = r.get('content_type', '')
            if ct:
                counts[ct] = counts.get(ct, 0) + 1

    if not counts:
        return {}

    total = sum(counts.values())
    return {ct: round(count / total, 6) for ct, count in sorted(counts.items(), key=lambda x: -x[1])}


def should_replicate(content_type: str, exchange, threshold: float = 0.05) -> bool:
    """Return True if MIME policy allows AND (weight >= threshold OR bootstrap mode)."""
    # Policy gate first — never replicate what policy blocks regardless of priority
    try:
        from . import mime_policy as _mp
        config = exchange.load() if hasattr(exchange, 'load') else {}
        allowed, _ = _mp.is_allowed(content_type, config)
        if not allowed:
            return False
    except Exception:
        pass  # if policy check fails, fall through to weight check
    priorities = calibrate_mime_priority(exchange)
    if len(priorities) < 5:
        # Bootstrap: replicate everything when new node
        return True
    ct = (content_type or '').lower().split(';')[0].strip()
    return priorities.get(ct, 0.0) >= threshold


def get_priority_rank(content_type: str, exchange) -> float:
    """Return normalized weight (0.0–1.0); higher = replicate sooner."""
    priorities = calibrate_mime_priority(exchange)
    ct = (content_type or '').lower().split(';')[0].strip()
    return priorities.get(ct, 0.0)


def emit_mime_calibration_event(exchange) -> dict:
    """Emit MIME_PRIORITY_CALIBRATED audit row.

    Idempotent: skip if calibrated in last 24 hours.
    """
    _24H = 86400
    now_unix = time.time()

    try:
        local_id = exchange.local_peer_id() if hasattr(exchange, 'local_peer_id') else ''
    except Exception:
        local_id = ''

    cache_key = local_id or id(exchange)
    last = _CALIBRATION_CACHE.get(cache_key, 0)
    if now_unix - last < _24H:
        return {'status': 'skipped', 'reason': 'calibrated_recently'}

    priorities = calibrate_mime_priority(exchange)

    row = {
        'kind': 'MIME_PRIORITY_CALIBRATED',
        'peer_id': local_id,
        'priorities': priorities,
        'at_unix': now_unix,
        'at': datetime.now(timezone.utc).isoformat(),
    }
    try:
        exchange.append_audit_row(row)
        _CALIBRATION_CACHE[cache_key] = now_unix
    except Exception:
        pass

    return row
