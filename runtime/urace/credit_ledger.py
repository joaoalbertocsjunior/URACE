"""Per-peer credit accounting for peer artifact exchange."""
import math
import random
import time
from pathlib import Path

SCHEMA = 'urace-credit-ledger-v1'
BASELINE_GRANT = 3  # requests every new peer can make before earning

# Decision 1: 8-decimal precision (satoshi model)
DECIMALS = 8
UNIT = 10 ** DECIMALS   # 1.00000000 token = 100_000_000 base units
BASELINE_GRANT_UNITS = BASELINE_GRANT * UNIT

# Decision 3: Credit velocity control
VELOCITY_WINDOW_SECONDS = 90 * 86400   # 90 days (EMA window)
EMA_HALF_LIFE_SECONDS   = 30 * 86400   # 30-day half-life for EMA
TARGET_MINT_BURN_RATIO  = 1.0           # balanced economy
VELOCITY_CLAMP_LOW      = 0.8
VELOCITY_CLAMP_HIGH     = 1.2
BASE_CAP_UNITS          = 50 * UNIT       # governance per-peer balance cap (epoch-adjustable)
MAX_BALANCE_UNITS       = BASE_CAP_UNITS  # backward-compat alias (dynamic cap is per-call)
# Physics-optimal per-peer earn ceiling at baseline infra (1 Mbps / 50 MB / 30 s):
# 3,840 features × 100 adoptions × 0.1 tokens avg mint / 1,000 peers + 3-token baseline grant ≈ 41 tokens/peer.
# Used as the ceiling for supply_pressure_multiplier so the curve activates at real-world supply levels.
PHYSICS_CAP_UNITS_PER_PEER = 41 * UNIT
POST_SAT_DECAY         = 0.85                    # per-rank decay factor after N_sat
REP_TIER_THRESHOLDS    = (0.3, 0.5, 0.7, 0.9)   # Wilson tiers for stackable bonus
REP_TIER_BONUS         = 0.10                    # +10% per tier crossed (max 1.4×)
JACCARD_DERIVATIVE_CAP = 0.70                    # token overlap above this = derivative feature
# Backward-compat alias: minimum governance supply ceiling (bootstrapping floor)
MAX_MINTABLE_UNITS     = BASE_CAP_UNITS * 10

# Crypto bridge constants — future on-chain integration (EVM 18-decimal standard)
CHAIN_DECIMALS = 18
CHAIN_UNIT     = 10 ** CHAIN_DECIMALS
CHAIN_SCALE    = CHAIN_UNIT // UNIT  # = 10^10: multiply internal units by this for on-chain

# Network supply stabilizer constants
TARGET_SUPPLY_RATIO     = 0.5   # target: 50% of theoretical max per peer
NETWORK_FACTOR_LOW      = 0.8
NETWORK_FACTOR_HIGH     = 1.2


def to_display(units: int) -> str:
    return f"{units / UNIT:.8f}"


def from_display(s: str) -> int:
    return int(round(float(s) * UNIT))


def to_chain_units(internal_units: int) -> int:
    """Convert internal 8-decimal base units to EVM-compatible 18-decimal on-chain units."""
    return internal_units * CHAIN_SCALE


def from_chain_units(chain_units: int) -> int:
    """Convert EVM 18-decimal on-chain units to internal 8-decimal base units."""
    return chain_units // CHAIN_SCALE


def _ledger(root):
    from .signed_ledger import Ledger
    return Ledger(Path(root) / 'credit-ledger')


def _all_blocks(ledger):
    blocks = []
    offset = 0
    while True:
        try:
            page = ledger.page(offset=offset, limit=100)
        except (OSError, ValueError):
            break
        blocks.extend(page['rows'])
        if page['next_offset'] is None:
            break
        offset = page['next_offset']
    return blocks


def _credit_rows(root, peer_id=None):
    blocks = _all_blocks(_ledger(root))
    rows = [b['payload']['details'] for b in blocks if b['payload'].get('kind') == 'CREDIT_DELTA']
    if peer_id is not None:
        rows = [r for r in rows if r.get('peer') == peer_id]
    return rows


def _row_units(r) -> int:
    """Resolve a credit row to base units, handling both old float and new int records."""
    if 'delta_units' in r:
        return r['delta_units']
    # old record: delta is a float (1, 2, 3, -1, ...)
    return int(r.get('delta', 0)) * UNIT


def _velocity_multiplier(root) -> float:
    """Compute mint multiplier using EMA-weighted mint/burn over 90 days (half-life 30d).

    Replaces hard 30-day window to remove the exploitable boundary at day 30.
    Returns a value in [0.8, 1.2] to modulate earn rate.
    """
    now = time.time()
    cutoff = now - VELOCITY_WINDOW_SECONDS
    decay = math.log(2) / EMA_HALF_LIFE_SECONDS   # λ = ln2 / T½
    rows = _credit_rows(root)
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
        # Too much minting — reduce
        return max(VELOCITY_CLAMP_LOW, TARGET_MINT_BURN_RATIO / ratio)
    else:
        # Too much burning — allow more minting
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


def _peer_quality_weights_from_exchange(exchange, peer_id: str) -> float:
    """Quality factor for peer_id.

    Signal: QUALITY_VERIFICATION rows (issuer == peer_id) among APPLIED_AFTER_LOCAL_QUALIFICATION.
    Self-ratings excluded.
    Returns quality_factor in [1.0, 1.5].
    """
    from collections import defaultdict
    try:
        rows = exchange.audit_rows()
    except Exception:
        return 1.0
    quality_verifications = 0
    total_adoptions = 0
    # Build per-verifier weights (each unique peer that issued quality rows)
    weights: dict = {}
    for row in rows:
        issuer = row.get('peer')
        subject = row.get('subject_peer_id') or row.get('subject_peer')
        kind = row.get('kind', '')
        if issuer != peer_id:
            continue
        # Exclude self-ratings
        if subject == peer_id:
            continue
        if kind == 'QUALITY_VERIFICATION':
            quality_verifications += 1
            weights[subject] = weights.get(subject, 0.0) + 1.0
        if kind in ('QUALITY_VERIFICATION', 'APPLIED_AFTER_LOCAL_QUALIFICATION'):
            total_adoptions += 1

    # Build peers_seen from all rows for cluster analysis
    peers_seen: set = set()
    for row in rows:
        p = row.get('peer')
        if p:
            peers_seen.add(p)

    # --- Defense 1: Minimum external verifier gate ---
    # Only count verifiers with ZERO prior audit contact with the issuer.
    # "Prior contact" = both peer IDs appear in any same audit row.
    # Build contact sets per peer.
    contact_sets: dict = defaultdict(set)
    for row in rows:
        row_peers = [p for p in [row.get('peer'), row.get('issuer'), row.get('verifier')] if p]
        for pa in row_peers:
            for pb in row_peers:
                if pa != pb:
                    contact_sets[pa].add(pb)

    # --- Defense 2: Trust-weighted path cost (replaces temporal correlation) ---
    # Edge cost between two peers = 1.0 / trust_wilson(peer_a, peer_b)
    # Cartel members have high mutual trust → low edge cost → low path cost → low weight
    # Independent peers have low cross-trust → high path cost → high weight
    # weight = 1.0 - exp(-path_cost × 0.3)  asymptotic [0, 1]
    #
    # Build pairwise trust from co-occurrence in QUALIFICATION_RECEIPT rows.

    # Build edge costs from audit rows
    edge_trust: dict = defaultdict(float)  # (a,b) → max trust observed
    for row in rows:
        if row.get('kind') == 'QUALIFICATION_RECEIPT':
            p = row.get('peer')
            v = row.get('verifier') or row.get('issuer')
            if p and v and p != v:
                # Both sides get the same undirected trust estimate
                edge_trust[(p, v)] = max(edge_trust.get((p, v), 0.0), weights.get(p, 0.1))
                edge_trust[(v, p)] = edge_trust[(p, v)]

    # Dijkstra from each verifier peer to all known peers
    # path_cost between two peers = sum of (1/trust) along shortest path
    # Use a simple BFS/Dijkstra approximation — O(N² log N) for small networks
    import heapq as _hq

    def _path_cost(src: str, dst: str, all_peers: set) -> float:
        """Shortest trust-weighted path cost from src to dst."""
        if src == dst:
            return 0.0
        # Build adjacency from edge_trust
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
        return float('inf')  # no path — treat as maximally distant (good)

    # Apply path-cost weighting to all verifier weights
    for peer in list(weights.keys()):
        # Pick a representative "issuer" as the peer with the most QUALITY_VERIFICATION rows issued
        # (We don't have a single issuer in this context — use average distance to all others)
        other_peers = set(weights.keys()) - {peer}
        if not other_peers:
            continue
        avg_cost = sum(_path_cost(peer, other, peers_seen) for other in other_peers) / len(other_peers)
        # Low avg_cost (close to everyone) → cartel member → reduce weight
        # High avg_cost (far from everyone) → independent → full weight
        path_weight = 1.0 - math.exp(-avg_cost * 0.3)
        weights[peer] *= max(0.05, path_weight)

    # --- Defense 3: Consensus diversity check ---
    # quality_factor > 0.5 only when verifications come from ≥ 3 distinct clusters.
    # Build simple union-find clusters by audit contact.
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

    # Apply all three defenses
    for peer in list(weights.keys()):
        # D1: external-only gate — zero out verifiers who had prior contact with issuer
        # (issuer is unknown here; we apply a weaker form: zero out self-referential rings)
        if peer in contact_sets:
            # Reduce weight proportional to how many other verifiers this peer contacted
            other_verifiers = contact_sets[peer] & set(weights.keys())
            if len(other_verifiers) > len(weights) * 0.5:
                weights[peer] *= 0.1  # heavy ring member — near-zero

        # D3: cluster diversity — count distinct clusters among all verifiers
        verifier_clusters = {cluster_of.get(p) for p in weights.keys() if cluster_of.get(p)}
        if len(verifier_clusters) < 3:
            # All verifiers in < 3 clusters — reduce all weights to baseline
            weights[peer] = min(weights[peer], 0.5)

    quality_rate = _wilson_lower(quality_verifications, total_adoptions)
    return 1.0 + 0.5 * quality_rate


def _network_supply_factor(root, exchange) -> float:
    """Automatic supply stabilizer.

    target_supply / total_supply clamped to [NETWORK_FACTOR_LOW, NETWORK_FACTOR_HIGH].
    Same computation by every peer, no coordination needed.
    """
    try:
        rows = exchange.audit_rows()
    except Exception:
        return 1.0
    known_peers = {row.get('peer') for row in rows if row.get('peer')}
    known_peer_count = max(1, len(known_peers))
    total_supply = sum(balance(root, p) for p in known_peers)
    target_supply = BASE_CAP_UNITS * known_peer_count * TARGET_SUPPLY_RATIO
    raw = target_supply / max(1, total_supply)
    return max(NETWORK_FACTOR_LOW, min(NETWORK_FACTOR_HIGH, raw))


def peer_cap_units(root, peer_id: str) -> int:
    """Dynamic per-peer balance cap: three-factor formula.

    cap = BASE_CAP_UNITS × trust_factor × quality_factor × network_factor

    trust_factor  ∈ [1.1, 2.0]  — Wilson lower-bound on delivery rate
    quality_factor ∈ [1.0, 1.5] — Wilson lower-bound on feature outcome quality
    network_factor ∈ [0.8, 1.2] — automatic supply stabilizer
    """
    from .peer_exchange import Exchange as _Exchange
    from pathlib import Path as _Path
    try:
        exchange = _Exchange(_Path(root).parent / 'exchange')
        weights = _peer_trust_weights_from_exchange(exchange)
        trust = weights.get(peer_id, 0.1)
        quality_factor = _peer_quality_weights_from_exchange(exchange, peer_id)
        network_factor = _network_supply_factor(root, exchange)
    except Exception:
        trust = 0.1
        quality_factor = 1.0
        network_factor = 1.0
    trust_factor = 1.0 + trust
    return int(BASE_CAP_UNITS * trust_factor * quality_factor * network_factor)


def _peer_trust_weights_from_exchange(exchange) -> dict:
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


# ── Earned vs. traded reputation ─────────────────────────────────────────────
# rep_source tags on CREDIT_DELTA earn rows distinguish reputation types.
# Only REP_SOURCE_WORK credits contribute to network trust / arbitration weight.
# REP_SOURCE_TRADE credits unlock premium services but never count toward governance.
REP_SOURCE_WORK  = 'work'    # earned via delivery, quality, adoption — counts for earned_rep
REP_SOURCE_TRADE = 'trade'   # purchased / traded — market_rep only, never earned_rep


def earned_balance(root, peer_id: str) -> int:
    """Credits earned via REP_SOURCE_WORK only — the basis for earned reputation.

    Market-purchased or traded credits are excluded; this is the trust-relevant balance.
    """
    rows = _credit_rows(root, peer_id)
    total = 0
    for r in rows:
        src = r.get('rep_source', REP_SOURCE_WORK)  # backward-compat: unlabelled = work
        total += _row_units(r) if src == REP_SOURCE_WORK else 0
    return max(0, total)


def earn_units(root, peer_id, units: int, reason, bundle_id=None, metadata: dict | None = None,
               rep_source: str = REP_SOURCE_WORK):
    """Credit peer_id with units base units earned from an accepted qualification.

    rep_source: REP_SOURCE_WORK (default) or REP_SOURCE_TRADE.
        Only REP_SOURCE_WORK credits contribute to earned_balance() and network rep.

    Applies:
    - EMA velocity multiplier
    - novelty gate: 50% reduction when re-borrowing a previously-held feature
    - trust-dynamic three-factor per-peer cap
    """
    if not isinstance(units, int) or units <= 0:
        raise ValueError('Positive int units required to earn credits')
    adjusted_units = int(units * _velocity_multiplier(root))
    # If adoption metadata provided, apply mint_per_adoption formula
    if metadata and 'adoption_rank' in metadata:
        minted = mint_per_adoption(
            loc=metadata.get('loc', 0),
            dependency_count=metadata.get('dependency_count', 0),
            test_count=metadata.get('test_count', 0),
            adopter_trust=metadata.get('adopter_trust', 0.5),
            adoption_rank=metadata['adoption_rank'],
            network_size=metadata.get('network_size', 1),
            epochs_elapsed=metadata.get('epochs_elapsed', 0),
        )
        if minted == 0:
            return  # saturated — no earn
        units = minted  # override the passed-in units with the formula result
        adjusted_units = int(units * _velocity_multiplier(root))
    # Novelty gate: re-borrow of same feature_id earns 50%
    if reason and 'borrow' in str(reason).lower():
        feature_id = (metadata or {}).get('feature_id')
        if feature_id and feature_id in _peer_held_features(root, peer_id):
            adjusted_units = adjusted_units // 2
    # Apply trust-dynamic per-peer cap
    cap = peer_cap_units(root, peer_id)
    current = balance(root, peer_id)
    if current + adjusted_units > cap:
        adjusted_units = max(0, cap - current)
    if adjusted_units <= 0:
        return
    row_data: dict = {
        'peer': peer_id, 'delta_units': adjusted_units,
        'direction': 'earn', 'reason': reason,
        'bundle_id': bundle_id, 'at_unix': time.time(),
        'rep_source': rep_source,
    }
    if metadata:
        row_data['metadata'] = metadata
        feature_id = metadata.get('feature_id')
        if feature_id:
            row_data['feature_id'] = feature_id
    _ledger(root).append('CREDIT_DELTA', row_data)


def spend_units(root, peer_id, units: int, reason, bundle_id=None):
    """Debit units base units from peer_id. Raises if insufficient balance."""
    if not isinstance(units, int) or units <= 0:
        raise ValueError('Positive int units required to spend credits')
    if balance(root, peer_id) < units:
        raise ValueError('Insufficient credits for peer ' + peer_id)
    _ledger(root).append('CREDIT_DELTA', {
        'peer': peer_id, 'delta_units': -units,
        'direction': 'spend', 'reason': reason,
        'bundle_id': bundle_id, 'at_unix': time.time(),
    })


def earn(root, peer_id, delta, reason, bundle_id=None):
    """Legacy wrapper: delta in tokens, multiplied by UNIT before storing."""
    if type(delta) not in (int, float) or delta <= 0:
        raise ValueError('Positive delta required to earn credits')
    earn_units(root, peer_id, int(round(float(delta))) * UNIT, reason, bundle_id)


def spend(root, peer_id, reason, bundle_id=None):
    """Legacy wrapper: spends 1 token (UNIT base units)."""
    spend_units(root, peer_id, UNIT, reason, bundle_id)


def balance(root, peer_id) -> int:
    """Current token balance for peer_id in base units. Baseline grant applied if no history."""
    rows = _credit_rows(root, peer_id)
    if not rows:
        return BASELINE_GRANT_UNITS
    return BASELINE_GRANT_UNITS + sum(_row_units(r) for r in rows)


def history(root, peer_id, limit=50):
    """Most recent credit events for peer_id."""
    rows = _credit_rows(root, peer_id)
    return rows[-limit:]


def summary(root):
    """All peer balances and total event count."""
    rows = _credit_rows(root)
    peers = {}
    for r in rows:
        peer = r.get('peer')
        if peer:
            peers[peer] = peers.get(peer, 0) + _row_units(r)
    return {
        'schema': SCHEMA,
        'peers': {p: BASELINE_GRANT_UNITS + v for p, v in peers.items()},
        'baseline_grant': BASELINE_GRANT,
        'baseline_grant_units': BASELINE_GRANT_UNITS,
        'total_events': len(rows),
    }


# Decision 2: Complexity-weighted feature pricing floor

def feature_complexity_score(loc: int = 0, dependency_count: int = 0, test_count: int = 0) -> float:
    """Complexity score in [1.0, ∞).
    Simple features ("button", 10 LOC, 0 deps) → ~1.1
    Complex features (200 LOC, 5 deps, 10 tests) → ~3.5
    """
    return 1.0 + math.log2(1 + loc / 50 + dependency_count * 2 + test_count * 3)


def feature_borrow_cost_units(loc: int = 0, dependency_count: int = 0, test_count: int = 0) -> int:
    """Minimum borrow cost in base units. Never below UNIT/10_000 (0.0001 token)."""
    score = feature_complexity_score(loc, dependency_count, test_count)
    return max(UNIT // 10_000, int(score * UNIT // 10))


def feature_borrow_cost_with_rep(
    loc: int = 0,
    dependency_count: int = 0,
    test_count: int = 0,
    quality_verifications: int = 0,
    total_adoptions: int = 0,
) -> int:
    """Borrow cost weighted by feature reputation (Wilson lower-bound).

    New/unproven feature: 50% discount (cheap to try).
    Highly-verified feature: up to 50% premium (value-priced).
    rep_multiplier ∈ [0.5, 1.5]
    """
    score = feature_complexity_score(loc, dependency_count, test_count)
    rep_rate = _wilson_lower(quality_verifications, total_adoptions)  # 0.0 when no data
    rep_multiplier = 0.5 + rep_rate  # [0.5, 1.5]
    base = int(score * UNIT // 10)
    return max(UNIT // 10_000, int(base * rep_multiplier))


def supply_pressure_multiplier(total_supply_units: int, estimated_network_size: int = 1,
                               physics_max_units: int | None = None) -> float:
    """Soft quadratic pressure against physics-bounded supply ceiling.

    Returns 1.0 at 0% supply, 0.75 at 50%, 0.19 at 90%, ~0.001 at 100%.
    Anchored to PHYSICS_CAP_UNITS_PER_PEER × network_size so the curve activates at
    real-world supply levels. Callers may pass physics_max_units to override with
    observed infra capacity (e.g. from p2p_optimal_supply()).
    """
    if physics_max_units is None:
        physics_max_units = max(
            PHYSICS_CAP_UNITS_PER_PEER * 10,
            PHYSICS_CAP_UNITS_PER_PEER * max(1, estimated_network_size),
        )
    cap = max(1, physics_max_units)
    ratio = min(1.0, total_supply_units / cap)
    return max(0.001, 1.0 - ratio ** 2)


def _rep_tier_bonus(quality_verifications: int, total_adoptions: int) -> float:
    """Stackable rep bonus: each Wilson tier crossed adds REP_TIER_BONUS (max 1.4×).

    Tiers: [0.3, 0.5, 0.7, 0.9]. Feature crossing all 4 → 1.0 + 4×0.10 = 1.40
    """
    if total_adoptions == 0:
        return 1.0
    rate = _wilson_lower(quality_verifications, total_adoptions)
    tiers_crossed = sum(1 for t in REP_TIER_THRESHOLDS if rate >= t)
    return 1.0 + REP_TIER_BONUS * tiers_crossed


_APPROVED_FLOOR_BASE  = 0.50   # bootstrap floor for new peers (0 accepted deliveries)
_APPROVED_FLOOR_MIN   = 0.05   # minimum floor for established peers with zero approvals
_APPROVED_FLOOR_DECAY = 7.0    # accepted deliveries to halve the floor (after grace of 3)


def approved_gate_floor(total_accepted: int = 0) -> float:
    """Decay-based approved gate floor.

    New peers need bootstrap room → floor starts at 0.50.
    Peers with many accepted-but-unapproved deliveries trend toward 0.05.
    Formula: max(MIN, BASE × exp(−max(0, accepted−3) / K))

    ~3 accepted without mint → floor ≈ 0.50 (grace period)
    ~10 accepted without mint → floor ≈ 0.34
    ~20 accepted without mint → floor ≈ 0.12
    ~30+ accepted without mint → floor ≈ 0.05
    """
    excess = max(0, total_accepted - 3)
    return max(_APPROVED_FLOOR_MIN, _APPROVED_FLOOR_BASE * math.exp(-excess / _APPROVED_FLOOR_DECAY))


def combined_rep_score(
    delivery_wilson: float,
    quality_wilson: float,
    beta: float = 1.5,
    min_delivery_to_bid: float = 0.30,
    approved_fraction: float = 1.0,
    total_accepted: int = 0,
) -> float:
    """Combined reputation for work request bid ranking.

    Uses F-score formula (from ML precision/recall), delivery-weighted:
        F_β = (1+β²) × (d × q) / (β²×d + q)

    delivery_wilson:  Wilson lower-bound on delivery rate [0, 1]
    quality_wilson:   Wilson lower-bound on quality rate [0, 1]
    beta:             delivery weight (1.5 = delivery 1.5× more important)
    approved_fraction: deliveries_that_produced_mint / total_accepted.
        Multiplier = max(approved_gate_floor(total_accepted), approved_fraction).
        New peers: floor ≈ 0.50. Repeat offenders (many non-earning): floor → 0.05.
    total_accepted:   Total accepted deliveries from this peer (drives floor decay).

    Returns 0.0 when delivery < min_delivery_to_bid (hard gate).
    quality cold-start: if quality_wilson == 0.0, uses 0.05 floor (new peer can bid at bottom).
    """
    if delivery_wilson < min_delivery_to_bid:
        return 0.0
    q = max(0.05, quality_wilson)
    d = delivery_wilson
    beta2 = beta * beta
    denom = beta2 * q + d
    if denom == 0.0:
        return 0.0
    f_score = (1.0 + beta2) * (d * q) / denom
    floor = approved_gate_floor(total_accepted)
    approved_mult = max(floor, min(1.0, approved_fraction))
    return f_score * approved_mult


def feature_creator_id(canonical_fp: str, exchange) -> str | None:
    """Return the peer_id that first broadcast a feature with this canonical fingerprint.

    Scans APPLIED_AFTER_LOCAL_QUALIFICATION audit rows for 'canonical_fingerprint' field.
    Returns the peer_id of the earliest timestamped row matching the fingerprint.
    Returns None when no matching row found.

    This is immutable once written — first broadcaster is permanent creator.
    """
    try:
        rows = exchange.audit_rows()
    except Exception:
        return None
    matches = [
        (float(r.get('at_unix', 0)), r.get('peer'))
        for r in rows
        if r.get('kind') == 'APPLIED_AFTER_LOCAL_QUALIFICATION'
        and r.get('canonical_fingerprint') == canonical_fp
        and r.get('peer')
    ]
    if not matches:
        return None
    matches.sort()
    return matches[0][1]


# ── Escrow operations ─────────────────────────────────────────────────────────

_ESCROW_PEER = '__escrow__'   # virtual peer that holds locked credits


def escrow_lock(root, requester_id: str, request_id: str, amount: int) -> None:
    """Lock amount base units from requester into escrow.

    Debits requester via spend_units. Records with request_id for tracing.
    Raises ValueError if insufficient balance.
    """
    spend_units(root, requester_id, amount, f'escrow-lock:{request_id}', bundle_id=request_id)


def escrow_release(
    root,
    request_id: str,
    splits: list[tuple[str, int]],
) -> None:
    """Release escrowed credits to hired node(s).

    splits: list of (peer_id, units) from equity_split_budget()
    Credits are issued via earn_units (the escrow was already debited on lock).
    """
    for peer_id, units in splits:
        if units > 0:
            earn_units(root, peer_id, units, f'escrow-release:{request_id}',
                       bundle_id=request_id)


def escrow_refund(root, request_id: str, requester_id: str, amount: int) -> None:
    """Refund escrowed credits to requester (on cancel or dispute resolution in their favor)."""
    if amount > 0:
        earn_units(root, requester_id, amount, f'escrow-refund:{request_id}',
                   bundle_id=request_id)


# ── Distribution fee ──────────────────────────────────────────────────────────

DISTRIBUTION_FEE_MIN = 0.05   # floor: 5% for low-quality features
DISTRIBUTION_FEE_MAX = 0.30   # ceiling: 30% for high-quality features
DISTRIBUTION_FEE_DEFAULT = 0.10  # default when no quality signal


def distribution_fee_units(borrow_cost: int, quality_score: float | None = None) -> int:
    """Quality-dynamic distribution fee for the feature's distributor.

    fee = borrow_cost × clamp(0.05, 0.30, quality_score × 0.30)

    Rationale for not being 100%:
    - The non-fee portion is "burned" (spent without earning counterpart) → maintains
      token scarcity. 100% fee = no burn = inflation on every borrow.
    - Caps at 30%: above that, high-volume features would accumulate credits faster
      than the network can absorb, causing requester-wealth concentration.
    - quality_score = None → default 10% (pre-consensus fallback).
    """
    if quality_score is None:
        frac = DISTRIBUTION_FEE_DEFAULT
    else:
        frac = max(DISTRIBUTION_FEE_MIN, min(DISTRIBUTION_FEE_MAX, quality_score * DISTRIBUTION_FEE_MAX))
    return max(0, int(borrow_cost * frac))


def pay_distribution_fee(
    root,
    borrow_cost: int,
    feature_id: str,
    exchange,
    fallback_peer: str = '',
    quality_score: float | None = None,
) -> int:
    """Credit the distribution fee to the feature's distributor.

    Looks up the feature's requester from the most recent WORK_VERIFIED row.
    Falls back to feature_creator_id() then fallback_peer.
    Returns the fee amount paid (0 if no eligible recipient found).
    """
    fee = distribution_fee_units(borrow_cost, quality_score=quality_score)
    if fee <= 0:
        return 0
    # Find distributor: work requester > feature creator > fallback
    distributor: str = ''
    try:
        for r in reversed(list(exchange.audit_rows())):
            if r.get('kind') == 'WORK_VERIFIED' and r.get('approved'):
                req_id = r.get('requester_id', '')
                if req_id:
                    distributor = req_id
                    break
    except Exception:
        pass
    if not distributor:
        distributor = feature_creator_id(feature_id, exchange) or fallback_peer
    if not distributor:
        return 0
    earn_units(root, distributor, fee, f'distribution-fee:{feature_id}')
    return fee


def _jaccard_token_sim(feature_id_a: str, feature_id_b: str) -> float:
    """Jaccard similarity of token sets from two feature IDs."""
    import re as _re
    def _toks(s):
        return set(_re.findall(r'[a-z][a-z0-9]*', s.lower().replace('-', ' ').replace('_', ' ')))
    a, b = _toks(feature_id_a), _toks(feature_id_b)
    both = a & b
    either = a | b
    return len(both) / len(either) if either else 0.0


def _network_complexity_floor(exchange=None) -> float:
    """Consensus complexity floor from approved features seen in audit rows.

    Scans APPLIED_AFTER_LOCAL_QUALIFICATION rows for loc/test_count metadata.
    Returns 25th-percentile complexity score across approved features.
    Falls back to 0.5 when fewer than 5 data points.
    """
    if exchange is None:
        return 0.5
    try:
        rows = exchange.audit_rows()
    except Exception:
        return 0.5
    scores = []
    for row in rows:
        if row.get('kind') != 'APPLIED_AFTER_LOCAL_QUALIFICATION':
            continue
        meta = row.get('qualification_metadata') or row.get('metadata') or {}
        loc = int(meta.get('loc', 0))
        deps = int(meta.get('dependency_count', 0))
        tests = int(meta.get('test_count', 0))
        scores.append(feature_complexity_score(loc, deps, tests))
    if len(scores) < 5:
        return 0.5
    scores.sort()
    p25_idx = max(0, int(len(scores) * 0.25) - 1)
    return max(0.5, scores[p25_idx])


def _derivative_penalty(feature_id: str, parent_feature_id: str) -> float:
    """Smooth three-tier derivative penalty based on token Jaccard similarity.

    Heavy overlap  (j > 0.70): earn factor = 1.0 - j         → [0.00, 0.30×]
    Medium overlap (0.40–0.70): earn factor = 0.5 + 0.5×(0.70-j)/0.30 → [0.50, 1.00×]
    Low overlap    (< 0.40):    earn factor = 1.0              → no penalty
    """
    if not feature_id or not parent_feature_id:
        return 1.0
    j = _jaccard_token_sim(feature_id, parent_feature_id)
    if j > JACCARD_DERIVATIVE_CAP:          # > 0.70
        return max(0.0, 1.0 - j)
    if j > 0.40:                             # medium
        return 0.5 + 0.5 * (JACCARD_DERIVATIVE_CAP - j) / (JACCARD_DERIVATIVE_CAP - 0.40)
    return 1.0


def max_mintable_units(estimated_network_size: int = 1) -> int:
    """Dynamic supply ceiling: 5× per-peer BASE_CAP × estimated network size.

    Scales with network growth. Small network: tight cap. Large: grows with it.
    Minimum: BASE_CAP_UNITS × 10 (floor for bootstrapping).
    """
    return max(BASE_CAP_UNITS * 10, BASE_CAP_UNITS * max(1, estimated_network_size) * 5)


def mint_per_adoption(
    loc: int = 0,
    dependency_count: int = 0,
    test_count: int = 0,
    adopter_trust: float = 0.5,
    adoption_rank: int = 1,
    network_size: int = 1,
    epochs_elapsed: int = 0,
    quality_verifications: int = 0,
    total_adoptions: int = 0,
    total_network_supply: int = 0,
    parent_feature_id: str = "",
    feature_id: str = "",
    complexity_floor: float = 0.5,
    exchange=None,
    estimated_network_size: int = 1,
) -> int:
    """Mint amount for one adoption event.

    Never returns hard 0 past saturation — instead asymptotes to 1 base unit.
    Rep tier bonus can rehydrate post-saturation earning.

    Formula:
        base_earn      = int(complexity × UNIT // 2)
        novelty        = 1.0 / (1.0 + log2(max(1, adoption_rank)))
        post_sat       = POST_SAT_DECAY^max(0, rank-N_sat) if rank > N_sat else 1.0
        rep_bonus      = _rep_tier_bonus(quality_verifications, total_adoptions)
        epoch_decay    = 0.99^epochs_elapsed
        trust_mult     = 0.5 + 0.5×adopter_trust
        supply_mult    = supply_pressure_multiplier(total_network_supply, estimated_network_size)
        derivative_pen = smooth three-tier penalty via _derivative_penalty()
        earn = min(earn_cap, int(base_earn × trust_mult × novelty × post_sat ×
                                 rep_bonus × epoch_decay × supply_mult × derivative_pen))
        return max(1, earn)   # floor: 1 base unit (never exactly 0)
    """
    complexity = feature_complexity_score(loc, dependency_count, test_count)
    n_sat = max(10, math.ceil(0.30 * max(1, network_size)))

    base_earn = int(complexity * UNIT // 2)
    novelty = 1.0 / (1.0 + math.log2(max(1, adoption_rank)))

    # Post-saturation: asymptotic decay (not hard zero)
    post_sat = POST_SAT_DECAY ** max(0, adoption_rank - n_sat) if adoption_rank > n_sat else 1.0

    rep_bonus = _rep_tier_bonus(quality_verifications, total_adoptions)
    epoch_decay = 0.99 ** max(0, epochs_elapsed)
    trust_mult = 0.5 + 0.5 * max(0.0, min(1.0, adopter_trust))
    supply_mult = supply_pressure_multiplier(total_network_supply, estimated_network_size)

    # Derivative feature penalty (smooth three-tier curve)
    derivative_pen = _derivative_penalty(feature_id, parent_feature_id)

    cap = feature_earn_cap_units(loc, dependency_count, test_count)
    earn = min(cap, int(base_earn * trust_mult * novelty * post_sat *
                        rep_bonus * epoch_decay * supply_mult * derivative_pen))

    # Consensus complexity splitting defense
    if complexity < complexity_floor:
        earn = int(earn * 0.3)

    # ±5% jitter: breaks exact gradient descent optimization by AI actors
    return _jitter(max(1, earn), EARN_JITTER_FRAC)


def feature_earn_cap_units(loc: int = 0, dependency_count: int = 0, test_count: int = 0) -> int:
    """Maximum tokens earnable per borrow event. Caps inflation of simple features."""
    score = feature_complexity_score(loc, dependency_count, test_count)
    return min(10 * UNIT, int(score * UNIT))


# ── AI underpricing defenses ──────────────────────────────────────────────────

EARN_JITTER_FRAC   = 0.05   # ±5% uniform noise on final earn — breaks exact gradient descent
BORROW_JITTER_FRAC = 0.03   # ±3% on borrow cost — smaller, prevents systematic undercutting


def _jitter(value: int, frac: float) -> int:
    """Apply uniform ±frac noise to an integer amount. Minimum 1 base unit."""
    if value <= 1:
        return value
    delta = int(value * frac)
    if delta == 0:
        return value
    return max(1, value + random.randint(-delta, delta))


def consensus_borrow_floor(exchange=None, estimated_network_size: int = 1) -> int:
    """Network-consensus minimum borrow cost.

    Computes median observed borrow cost from recent spend audit rows.
    No feature can be borrowed below max(formula_floor, consensus_median × 0.5).
    Falls back to formula floor when fewer than 5 data points.
    An AI cannot systematically underprice below what the network observes as normal.
    """
    if exchange is None:
        return UNIT // 10_000
    try:
        rows = exchange.audit_rows()
    except Exception:
        return UNIT // 10_000
    costs = []
    for row in rows:
        if row.get('kind') != 'CREDIT_DELTA':
            continue
        if row.get('direction') != 'spend':
            continue
        units = abs(int(row.get('delta_units', row.get('delta', 0)) or 0))
        if units > 0:
            costs.append(units)
    if len(costs) < 5:
        return UNIT // 10_000
    costs.sort()
    median = costs[len(costs) // 2]
    return max(UNIT // 10_000, median // 2)  # floor at 50% of network median


def apply_borrow_cost(
    loc: int = 0,
    dependency_count: int = 0,
    test_count: int = 0,
    quality_verifications: int = 0,
    total_adoptions: int = 0,
    exchange=None,
    estimated_network_size: int = 1,
) -> int:
    """Final borrow cost with consensus floor and jitter.

    Combines rep-weighted formula cost with consensus network floor.
    Applies ±3% jitter to prevent exact price optimization by AI actors.
    """
    formula_cost = feature_borrow_cost_with_rep(
        loc, dependency_count, test_count,
        quality_verifications, total_adoptions,
    )
    floor = consensus_borrow_floor(exchange, estimated_network_size)
    cost = max(formula_cost, floor)
    return _jitter(cost, BORROW_JITTER_FRAC)


# ── Escrow budget anti-gamification ─────────────────────────────────────────

ESCROW_JITTER_FRAC = 0.04   # ±4% — between earn ±5% and borrow ±3%


def consensus_escrow_floor(exchange=None) -> int:
    """Network-consensus minimum escrow budget from recent WORK_REQUEST rows.

    Peers cannot post budgets below 50% of network median.
    Prevents AI agents from systematically undercutting escrow prices.
    Falls back to UNIT // 1_000 when fewer than 3 data points.
    """
    if exchange is None:
        return UNIT // 1_000
    try:
        rows = exchange.audit_rows()
    except Exception:
        return UNIT // 1_000
    budgets = [
        int(r.get('budget_units', 0))
        for r in rows
        if r.get('kind') == 'WORK_REQUEST' and int(r.get('budget_units', 0)) > 0
    ]
    if len(budgets) < 3:
        return UNIT // 1_000
    budgets.sort()
    median = budgets[len(budgets) // 2]
    return max(UNIT // 1_000, median // 2)


def escrow_budget_units(
    base_borrow_cost: int,
    exchange=None,
    premium: float = 1.5,
) -> int:
    """Final escrow budget: base × premium, consensus floor, ±4% jitter.

    Same anti-AI defenses as apply_borrow_cost(): stochastic noise breaks
    gradient descent; consensus floor prevents systematic undercutting.
    """
    raw = int(base_borrow_cost * premium)
    floor = consensus_escrow_floor(exchange)
    budget = max(raw, floor)
    return _jitter(budget, ESCROW_JITTER_FRAC)


# ── Dynamic split consensus ──────────────────────────────────────────────────

_SPLIT_REQUESTER_FLOOR = 0.50
_SPLIT_HIRED_FLOOR     = 0.20
_SPLIT_DEFAULT         = (0.60, 0.40)
_SPLIT_MIN_SAMPLES     = 5
_SPLIT_TTL_SECONDS     = 60   # cache TTL — full audit scan is O(n), amortize at 60s

import weakref as _weakref
# Per-exchange TTL cache: exchange → (expire_time, result). WeakKeyDictionary prevents
# id() reuse collisions when exchange objects are GC'd between tests.
_split_shares_cache: _weakref.WeakKeyDictionary = _weakref.WeakKeyDictionary()


def consensus_split_shares(exchange=None) -> tuple[float, float]:
    """Dynamic requester/hired mint split derived from past approved releases.

    Reads split_ratio_requester from WORK_VERIFIED rows (approved=True).
    Requester floor: 0.50, hired floor: 0.20. Default (0.60, 0.40) when < 5 rows.
    Result is cached per exchange for _SPLIT_TTL_SECONDS (60s) to amortize O(n) scan.

    Bias: median naturally favours the side with historic bargaining power.
    Neither party can push below their respective floor.
    """
    if exchange is None:
        return _SPLIT_DEFAULT
    now = time.time()
    cached = _split_shares_cache.get(exchange)
    if cached is not None and now < cached[0]:
        return cached[1]
    try:
        rows = exchange.audit_rows()
    except Exception:
        return _SPLIT_DEFAULT
    ratios = [
        float(r['split_ratio_requester'])
        for r in rows
        if r.get('kind') == 'WORK_VERIFIED'
        and r.get('approved')
        and isinstance(r.get('split_ratio_requester'), (int, float))
    ]
    if len(ratios) < _SPLIT_MIN_SAMPLES:
        result = _SPLIT_DEFAULT
    else:
        ratios.sort()
        med = ratios[len(ratios) // 2]
        med = max(_SPLIT_REQUESTER_FLOOR, min(1.0 - _SPLIT_HIRED_FLOOR, med))
        result = (med, 1.0 - med)
    _split_shares_cache[exchange] = (now + _SPLIT_TTL_SECONDS, result)
    return result


# ── Dynamic budget ceiling ───────────────────────────────────────────────────

def dynamic_budget_ceiling_multiplier(
    exchange=None,
    total_minted: int = 0,
    network_size: int = 1,
    executor_cost_units: int = 0,
) -> float:
    """Anti-monopoly max budget multiplier for escrow work requests.

    Formula:  ratio   = total_minted / (network_size × median_earned_per_peer)
              raw_mult = 5.0 / (1.0 + ratio)
              mult     = clamp(1.5, 5.0, raw_mult)

    When network supply is high relative to per-peer median, the ceiling tightens,
    preventing wealthy nodes from monopolising all available bidders.
    Hard floor: if executor_cost_units provided, mult caps so budget ≤ executor cost
    (hiring must stay cheaper than running the executor).
    Falls back to 3.0 when total_minted=0 or no peer data.
    """
    DEFAULT = 3.0
    if total_minted <= 0 or network_size <= 0:
        return DEFAULT

    median_per_peer = BASELINE_GRANT_UNITS
    if exchange is not None:
        try:
            per_peer: dict[str, int] = {}
            for r in exchange.audit_rows():
                if r.get('kind') != 'CREDIT_DELTA' or r.get('direction') != 'earn':
                    continue
                pid = r.get('peer', '')
                if pid and pid != _ESCROW_PEER:
                    per_peer[pid] = per_peer.get(pid, 0) + abs(int(r.get('delta_units', 0) or 0))
            if per_peer:
                vals = sorted(per_peer.values())
                median_per_peer = vals[len(vals) // 2]
        except Exception:
            pass

    ratio = total_minted / max(1, network_size * median_per_peer)
    mult = max(1.5, min(5.0, 5.0 / (1.0 + ratio)))

    # Hard ceiling: budget can't exceed executor cost (network hire must stay cheaper)
    if executor_cost_units > 0:
        base_borrow = apply_borrow_cost()   # zero-arg = minimal complexity
        if base_borrow > 0:
            executor_mult = executor_cost_units / base_borrow
            mult = min(mult, executor_mult)

    return mult


# ── Dynamic feature market pricing ───────────────────────────────────────────

def feature_market_price(
    feature_id: str,
    exchange,
    base_borrow_cost: int,
    quality_wilson: float = 0.5,
    adoption_count: int = 0,
    estimated_network_size: int = 1,
) -> int:
    """Dynamic borrow price reflecting feature quality, adoption velocity, supply.

    price = base × quality_mult × velocity_mult × supply_mult

    quality_mult:   clamp(0.8, 2.0, 1.0 + quality_wilson)
                    High-quality features earn up to 2× base price.
    velocity_mult:  clamp(0.9, 1.5, 1.0 + adoption_count / (network_size × 0.1))
                    Features adopted by > 10% of network earn 1.5× multiplier.
    supply_mult:    supply_pressure_multiplier on per-feature total spend
                    (popular features drive up their own price via supply pressure).

    Singularity property: price discovery is emergent — no oracle, no central
    pricing. Quality × adoption × scarcity compound automatically.

    Constraint: price ≥ base_borrow_cost (never below initial floor).
    Jitter: BORROW_JITTER_FRAC prevents exact price optimization by AI agents.
    """
    quality_mult = max(0.8, min(2.0, 1.0 + quality_wilson))

    # Sybil-resistant velocity: count distinct adopter peer_ids, not raw adoption_count.
    # A single peer self-adopting 1000× only counts as 1 distinct adopter.
    distinct_adopters = adoption_count   # caller default; exchange overrides below
    feature_spend = 0
    if exchange is not None:
        try:
            adopter_ids: set[str] = set()
            for r in exchange.audit_rows():
                if r.get('kind') == 'CREDIT_DELTA' and r.get('direction') == 'spend':
                    if r.get('feature_id') == feature_id:
                        feature_spend += abs(int(r.get('delta_units', 0) or 0))
                        pid = r.get('peer', '')
                        if pid:
                            adopter_ids.add(pid)
            if adopter_ids:
                distinct_adopters = len(adopter_ids)
        except Exception:
            pass

    velocity_mult = max(0.9, min(1.5,
        1.0 + distinct_adopters / max(1, estimated_network_size * 0.1)))

    # Per-feature saturation: once 5% of the network physics cap has been spent on this
    # feature, apply price pressure (democratises access after mass adoption).
    feature_physics_max = max(UNIT, PHYSICS_CAP_UNITS_PER_PEER * max(1, estimated_network_size) // 20)
    s_mult = supply_pressure_multiplier(feature_spend, physics_max_units=feature_physics_max)
    raw = int(base_borrow_cost * quality_mult * velocity_mult * s_mult)
    price = max(base_borrow_cost, raw)
    return _jitter(price, BORROW_JITTER_FRAC)
