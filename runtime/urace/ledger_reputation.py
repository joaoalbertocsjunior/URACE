"""Ledger reputation — scoring, trust weights, peer caps."""
import math
import time

from .ledger_primitives import (
    _credit_rows, _row_units, _all_blocks, _ledger, balance,
    earn_units, earned_balance,
    UNIT, BASE_CAP_UNITS, TARGET_SUPPLY_RATIO, NETWORK_FACTOR_LOW, NETWORK_FACTOR_HIGH,
    REP_SOURCE_WORK, REP_SOURCE_TRADE, CONSENSUS_WEIGHTS,
    VELOCITY_WINDOW_SECONDS, EMA_HALF_LIFE_SECONDS, TARGET_MINT_BURN_RATIO,
    VELOCITY_CLAMP_LOW, VELOCITY_CLAMP_HIGH,
)
from .ledger_adapter import LedgerAdapter


def _velocity_multiplier(root) -> float:
    """Compute mint multiplier using EMA-weighted mint/burn over 90 days (half-life 30d)."""
    import sys as _sys
    _cl = _sys.modules.get('urace.credit_ledger')
    _credit_rows_fn = _cl._credit_rows if _cl else _credit_rows

    now = time.time()
    cutoff = now - VELOCITY_WINDOW_SECONDS
    decay = math.log(2) / EMA_HALF_LIFE_SECONDS
    rows = _credit_rows_fn(root)
    minted = sum(
        r.get('delta_units', r.get('delta', 0) * UNIT)
        * math.exp(-decay * max(0.0, now - r.get('at_unix', now)))
        for r in rows
        if r.get('direction') == 'earn' and r.get('at_unix', 0) >= cutoff
    )
    burned = sum(
        abs(r.get('delta_units', r.get('delta', 0) * UNIT))
        * math.exp(-decay * max(0.0, now - r.get('at_unix', now)))
        for r in rows
        if r.get('direction') == 'spend' and r.get('at_unix', 0) >= cutoff
    )
    if burned == 0:
        return VELOCITY_CLAMP_LOW if minted > 0 else 1.0
    ratio = minted / burned
    if ratio > TARGET_MINT_BURN_RATIO:
        return max(VELOCITY_CLAMP_LOW, TARGET_MINT_BURN_RATIO / ratio)
    else:
        return min(VELOCITY_CLAMP_HIGH, TARGET_MINT_BURN_RATIO / ratio)


def _wilson_lower(k: int, n: int, z: float = 1.645) -> float:
    """Wilson score lower bound for proportion k/n at confidence z."""
    if n == 0:
        return 0.0
    z2 = z * z
    centre = k / n
    margin = z * math.sqrt(centre * (1.0 - centre) / n + z2 / (4.0 * n * n))
    denom = 1.0 + z2 / n
    return max(0.0, min(1.0, (centre + z2 / (2.0 * n) - margin) / denom))


def _peer_quality_weights_from_exchange(exchange: LedgerAdapter, peer_id: str) -> float:
    """Quality factor for peer_id. Returns quality_factor in [1.0, 1.5]."""
    from collections import defaultdict
    try:
        rows = exchange.audit_rows()
    except Exception:
        return 1.0
    quality_verifications = 0
    total_adoptions = 0
    weights: dict = {}
    for row in rows:
        issuer = row.get('peer')
        subject = row.get('subject_peer_id') or row.get('subject_peer')
        kind = row.get('kind', '')
        if issuer != peer_id:
            continue
        if subject == peer_id:
            continue
        if kind == 'QUALITY_VERIFICATION':
            quality_verifications += 1
            weights[subject] = weights.get(subject, 0.0) + 1.0
        if kind in ('QUALITY_VERIFICATION', 'APPLIED_AFTER_LOCAL_QUALIFICATION'):
            total_adoptions += 1

    peers_seen: set = set()
    for row in rows:
        p = row.get('peer')
        if p:
            peers_seen.add(p)

    contact_sets: dict = defaultdict(set)
    for row in rows:
        row_peers = [p for p in [row.get('peer'), row.get('issuer'), row.get('verifier')] if p]
        for pa in row_peers:
            for pb in row_peers:
                if pa != pb:
                    contact_sets[pa].add(pb)

    edge_trust: dict = defaultdict(float)
    for row in rows:
        if row.get('kind') == 'QUALIFICATION_RECEIPT':
            p = row.get('peer')
            v = row.get('verifier') or row.get('issuer')
            if p and v and p != v:
                edge_trust[(p, v)] = max(edge_trust.get((p, v), 0.0), weights.get(p, 0.1))
                edge_trust[(v, p)] = edge_trust[(p, v)]

    import heapq as _hq

    def _path_cost(src: str, dst: str, all_peers: set) -> float:
        if src == dst:
            return 0.0
        adj: dict = defaultdict(list)
        for (a, b), t in edge_trust.items():
            cost = 1.0 / max(0.01, t)
            adj[a].append((cost, b))
            adj[b].append((cost, a))
        dist = {src: 0.0}
        heap = [(0.0, src)]
        while heap:
            d, u = _hq.heappop(heap)
            if u == dst:
                return d
            if d > dist.get(u, float('inf')):
                continue
            for cost, v in adj.get(u, []):
                nd = d + cost
                if nd < dist.get(v, float('inf')):
                    dist[v] = nd
                    _hq.heappush(heap, (nd, v))
        return float('inf')

    for peer in list(weights.keys()):
        other_peers = set(weights.keys()) - {peer}
        if not other_peers:
            continue
        avg_cost = sum(_path_cost(peer, other, peers_seen) for other in other_peers) / len(other_peers)
        path_weight = 1.0 - math.exp(-avg_cost * 0.3)
        weights[peer] *= max(0.05, path_weight)

    parent = {p: p for p in peers_seen}

    def _find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def _union(a, b):
        parent[_find(a)] = _find(b)

    for row in rows:
        rp = [p for p in [row.get('peer'), row.get('issuer')] if p in parent]
        for i in range(len(rp)):
            for j in range(i + 1, len(rp)):
                _union(rp[i], rp[j])
    cluster_of = {p: _find(p) for p in peers_seen}

    for peer in list(weights.keys()):
        if peer in contact_sets:
            other_verifiers = contact_sets[peer] & set(weights.keys())
            if len(other_verifiers) > len(weights) * 0.5:
                weights[peer] *= 0.1

        verifier_clusters = {cluster_of.get(p) for p in weights.keys() if cluster_of.get(p)}
        if len(verifier_clusters) < 3:
            weights[peer] = min(weights[peer], 0.5)

    quality_rate = _wilson_lower(quality_verifications, total_adoptions)
    return 1.0 + 0.5 * quality_rate


def _network_supply_factor(root, exchange: LedgerAdapter) -> float:
    """Automatic supply stabilizer."""
    import sys as _sys
    # Use late-bound balance so mock.patch.object(credit_ledger, 'balance', ...) is respected
    _cl = _sys.modules.get('urace.credit_ledger')
    _balance = _cl.balance if _cl else balance

    try:
        rows = exchange.audit_rows()
    except Exception:
        return 1.0
    try:
        _meta = exchange.load()
        _est = _meta.get('estimated_network_size', 0)
        estimated_peer_count = max(1, int(_est)) if _est else 0
    except Exception:
        estimated_peer_count = 0
    known_peers = {row.get('peer') for row in rows if row.get('peer')}
    fallback_peer_count = max(1, len(known_peers))
    known_peer_count = estimated_peer_count if estimated_peer_count > 0 else fallback_peer_count
    total_supply = sum(_balance(root, p) for p in known_peers)
    target_supply = BASE_CAP_UNITS * known_peer_count * TARGET_SUPPLY_RATIO
    raw = target_supply / max(1, total_supply)
    return max(NETWORK_FACTOR_LOW, min(NETWORK_FACTOR_HIGH, raw))


def peer_cap_units(root, peer_id: str, exchange: LedgerAdapter | None = None) -> int:
    """Dynamic per-peer balance cap: three-factor formula."""
    try:
        if exchange is None:
            from .peer_exchange import Exchange as _Exchange
            from pathlib import Path as _Path
            _candidates = sorted((_Path(root) / 'exchange').glob('*/policy.json'))
            if not _candidates:
                _candidates = sorted((_Path(root).parent / 'exchange').glob('*/policy.json'))
            if not _candidates:
                raise FileNotFoundError('No exchange policy.json found near root')
            exchange = _Exchange(_candidates[-1].parent)
        weights = _peer_trust_weights_from_exchange(exchange)
        trust = weights.get(peer_id, 0.1)
        quality_factor = _peer_quality_weights_from_exchange(exchange, peer_id)
        network_factor = _network_supply_factor(root, exchange)
    except Exception as _exc:
        import logging as _log
        _log.getLogger(__name__).warning(
            'peer_cap_units: exchange lookup failed for %s — using baseline cap: %s',
            peer_id[:12] if peer_id else '?', _exc,
        )
        trust = 0.1
        quality_factor = 1.0
        network_factor = 1.0
    trust_factor = 1.0 + trust
    return int(BASE_CAP_UNITS * trust_factor * quality_factor * network_factor)


def _peer_trust_weights_from_exchange(exchange: LedgerAdapter) -> dict:
    """Extract trust weights using Wilson lower-bound on delivery rate."""
    from collections import defaultdict
    rows = exchange.audit_rows()
    verified: dict = defaultdict(int)
    applied: dict = defaultdict(int)
    peers_seen: set = set()
    for row in rows:
        peer = row.get('peer')
        if not peer:
            continue
        kind = row.get('kind', '')
        peers_seen.add(peer)
        if kind == 'QUALIFICATION_RECEIPT':
            verified[peer] += 1
            applied[peer] += 1
        elif kind == 'APPLIED_AFTER_LOCAL_QUALIFICATION':
            applied[peer] += 1
    weights = {}
    for peer in peers_seen:
        total = applied[peer]
        k = verified[peer]
        if total == 0:
            raw = 0.1
        else:
            raw = _wilson_lower(k, total)
        weights[peer] = max(0.1, min(1.0, raw))
    return weights


def _peer_held_features(root, peer_id: str) -> set:
    """Return set of feature_ids ever recorded in earn rows for this peer."""
    rows = _credit_rows(root, peer_id)
    held = set()
    for r in rows:
        fid = r.get('feature_id') or (r.get('metadata') or {}).get('feature_id')
        if fid:
            held.add(fid)
    return held


def weighted_rep_score(root, peer_id: str,
                       longevity_multiplier: float = 1.0) -> float:
    """Consensus weight score — event-count weighted, fully decoupled from UCR amounts."""
    rows = _credit_rows(root, peer_id)
    total = 0.0
    for r in rows:
        if r.get('rep_source', REP_SOURCE_WORK) != REP_SOURCE_WORK:
            continue
        direction = r.get('direction', '')
        weight = CONSENSUS_WEIGHTS.get(direction, 0.0)
        if weight <= 0.0:
            continue
        total += weight
    return total * max(0.0, longevity_multiplier)


def transfer_earned_rep(root, from_peer_id: str, to_peer_id: str, units: int) -> dict:
    """Transfer earned reputation on-chain (creates trade rep for receiver)."""
    import time as _time
    if units <= 0:
        raise ValueError('units must be positive')
    current = earned_balance(root, from_peer_id)
    if current < units:
        raise ValueError(
            f'Insufficient earned rep: {from_peer_id!r} has {current}, needs {units}')
    t = _time.time()
    _ledger(root).append('CREDIT_DELTA', {
        'peer': from_peer_id, 'delta_units': -units,
        'direction': 'rep_transfer_out', 'rep_source': REP_SOURCE_WORK,
        'to_peer_id': to_peer_id, 'at_unix': t,
    })
    _ledger(root).append('CREDIT_DELTA', {
        'peer': to_peer_id, 'delta_units': units,
        'direction': 'rep_transfer_in', 'rep_source': REP_SOURCE_TRADE,
        'from_peer_id': from_peer_id, 'at_unix': t,
    })
    return {
        'status': 'transferred',
        'from_peer_id': from_peer_id,
        'to_peer_id': to_peer_id,
        'units': units,
        'note': 'receiver holds this as trade_rep — never converts back to earned_rep',
    }
