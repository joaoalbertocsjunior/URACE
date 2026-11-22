"""Ledger economics — pricing, minting, borrow costs, market mechanics."""
import math
import random
import time
import weakref as _weakref

from .ledger_primitives import (
    UNIT, BASE_CAP_UNITS, PHYSICS_CAP_UNITS_PER_PEER,
    POST_SAT_DECAY, REP_TIER_THRESHOLDS, REP_TIER_BONUS, JACCARD_DERIVATIVE_CAP,
    MAX_MINTABLE_UNITS,
    EARN_JITTER_FRAC, BORROW_JITTER_FRAC, ESCROW_JITTER_FRAC,
    DISTRIBUTION_FEE_MIN, DISTRIBUTION_FEE_MAX, DISTRIBUTION_FEE_DEFAULT,
    _APPROVED_FLOOR_BASE, _APPROVED_FLOOR_MIN, _APPROVED_FLOOR_DECAY,
    _ESCROW_PEER,
    _SPLIT_REQUESTER_FLOOR, _SPLIT_HIRED_FLOOR, _SPLIT_DEFAULT,
    _SPLIT_MIN_SAMPLES, _SPLIT_TTL_SECONDS,
    earn_units,
)
from .ledger_reputation import (
    _velocity_multiplier, _wilson_lower, peer_cap_units,
)
from .ledger_adapter import LedgerAdapter


def feature_complexity_score(
    loc: int = 0,
    dependency_count: int = 0,
    test_count: int = 0,
    *,
    descriptor: dict | None = None,
    complexity_metrics: dict | None = None,
    domain: str = 'software',
) -> float:
    """Complexity score in [1.0, ∞)."""
    if descriptor is not None:
        m = descriptor.get('complexity_metrics') or {}
        interface_symbols = int(m.get('interface_symbol_count', 0))
        dep_cnt = int(m.get('dependency_count', dependency_count))
        tst_cnt = int(m.get('test_count', test_count))
        acc_cnt = int(m.get('acceptance_criterion_count', 0))
        if interface_symbols == 0:
            interface_symbols = int(m.get('loc', loc)) // 5
        return 1.0 + math.log2(
            1 + interface_symbols / 10 + dep_cnt + tst_cnt * 3 + acc_cnt / 5
        )

    if complexity_metrics is not None:
        loc = int(complexity_metrics.get('primary_size', loc))
        dependency_count = int(complexity_metrics.get('integration_count', dependency_count))
        test_count = int(complexity_metrics.get('validation_count', test_count))

    interface_symbols_approx = loc // 5
    return 1.0 + math.log2(
        1 + interface_symbols_approx / 10 + dependency_count + test_count * 3
    )


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
    """Borrow cost weighted by feature reputation (Wilson lower-bound)."""
    score = feature_complexity_score(loc, dependency_count, test_count)
    rep_rate = _wilson_lower(quality_verifications, total_adoptions)
    rep_multiplier = 0.5 + rep_rate
    base = int(score * UNIT // 10)
    return max(UNIT // 10_000, int(base * rep_multiplier))


def supply_pressure_multiplier(total_supply_units: int, estimated_network_size: int = 1,
                               physics_max_units: int | None = None) -> float:
    """Soft quadratic pressure against physics-bounded supply ceiling."""
    if physics_max_units is None:
        physics_max_units = max(
            PHYSICS_CAP_UNITS_PER_PEER * 10,
            PHYSICS_CAP_UNITS_PER_PEER * max(1, estimated_network_size),
        )
    cap = max(1, physics_max_units)
    ratio = min(1.0, total_supply_units / cap)
    return max(0.001, 1.0 - ratio ** 2)


def _rep_tier_bonus(quality_verifications: int, total_adoptions: int) -> float:
    """Stackable rep bonus: each Wilson tier crossed adds REP_TIER_BONUS (max 1.4×)."""
    if total_adoptions == 0:
        return 1.0
    rate = _wilson_lower(quality_verifications, total_adoptions)
    tiers_crossed = sum(1 for t in REP_TIER_THRESHOLDS if rate >= t)
    return 1.0 + REP_TIER_BONUS * tiers_crossed


def approved_gate_floor(total_accepted: int = 0) -> float:
    """Decay-based approved gate floor."""
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
    """Combined reputation for work request bid ranking."""
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


def feature_creator_id(canonical_fp: str, exchange: LedgerAdapter) -> str | None:
    """Return the peer_id that first broadcast a feature with this canonical fingerprint."""
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


def distribution_fee_units(borrow_cost: int, quality_score: float | None = None) -> int:
    """Quality-dynamic distribution fee for the feature's distributor."""
    if quality_score is None:
        frac = DISTRIBUTION_FEE_DEFAULT
    else:
        frac = max(DISTRIBUTION_FEE_MIN, min(DISTRIBUTION_FEE_MAX, quality_score * DISTRIBUTION_FEE_MAX))
    return max(0, int(borrow_cost * frac))


def pay_distribution_fee(
    root,
    borrow_cost: int,
    feature_id: str,
    exchange: LedgerAdapter,
    fallback_peer: str = '',
    quality_score: float | None = None,
) -> int:
    """Credit the distribution fee to the feature's distributor."""
    fee = distribution_fee_units(borrow_cost, quality_score=quality_score)
    if fee <= 0:
        return 0
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


def _network_complexity_floor(exchange: LedgerAdapter | None = None) -> float:
    """Consensus complexity floor from approved features seen in audit rows."""
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
    """Smooth three-tier derivative penalty based on token Jaccard similarity."""
    if not feature_id or not parent_feature_id:
        return 1.0
    j = _jaccard_token_sim(feature_id, parent_feature_id)
    if j > JACCARD_DERIVATIVE_CAP:
        return max(0.0, 1.0 - j)
    if j > 0.40:
        return 0.5 + 0.5 * (JACCARD_DERIVATIVE_CAP - j) / (JACCARD_DERIVATIVE_CAP - 0.40)
    return 1.0


def max_mintable_units(estimated_network_size: int = 1) -> int:
    """Dynamic supply ceiling: 5× per-peer BASE_CAP × estimated network size."""
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
    exchange: LedgerAdapter | None = None,
    estimated_network_size: int = 1,
) -> int:
    """Mint amount for one adoption event."""
    complexity = feature_complexity_score(loc, dependency_count, test_count)
    n_sat = max(10, math.ceil(0.30 * max(1, network_size)))

    base_earn = int(complexity * UNIT // 2)
    novelty = 1.0 / (1.0 + math.log2(max(1, adoption_rank)))

    post_sat = POST_SAT_DECAY ** max(0, adoption_rank - n_sat) if adoption_rank > n_sat else 1.0

    rep_bonus = _rep_tier_bonus(quality_verifications, total_adoptions)
    epoch_decay = 0.99 ** max(0, epochs_elapsed)
    trust_mult = 0.5 + 0.5 * max(0.0, min(1.0, adopter_trust))
    supply_mult = supply_pressure_multiplier(total_network_supply, estimated_network_size)

    derivative_pen = _derivative_penalty(feature_id, parent_feature_id)

    cap = feature_earn_cap_units(loc, dependency_count, test_count)
    earn = min(cap, int(base_earn * trust_mult * novelty * post_sat *
                        rep_bonus * epoch_decay * supply_mult * derivative_pen))

    if complexity < complexity_floor:
        earn = int(earn * 0.3)

    return _jitter(max(1, earn), EARN_JITTER_FRAC)


def feature_earn_cap_units(loc: int = 0, dependency_count: int = 0, test_count: int = 0) -> int:
    """Maximum tokens earnable per borrow event."""
    score = feature_complexity_score(loc, dependency_count, test_count)
    return min(10 * UNIT, int(score * UNIT))


def _jitter(value: int, frac: float) -> int:
    """Apply uniform ±frac noise to an integer amount. Minimum 1 base unit."""
    if value <= 1:
        return value
    delta = int(value * frac)
    if delta == 0:
        return value
    return max(1, value + random.randint(-delta, delta))


def consensus_borrow_floor(exchange: LedgerAdapter | None = None, estimated_network_size: int = 1) -> int:
    """Network-consensus minimum borrow cost."""
    if exchange is None:
        return UNIT // 10_000
    try:
        from .p2p_cost_qualification import bootstrap_complete as _bootstrap_complete
        if not _bootstrap_complete(exchange):
            return UNIT // 10_000
    except Exception:
        pass
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
    return max(UNIT // 10_000, median // 2)


def apply_borrow_cost(
    loc: int = 0,
    dependency_count: int = 0,
    test_count: int = 0,
    quality_verifications: int = 0,
    total_adoptions: int = 0,
    exchange: LedgerAdapter | None = None,
    estimated_network_size: int = 1,
    *,
    atom_id: str = '',
    descriptor: dict | None = None,
) -> int:
    """Final borrow cost with consensus floor, REPRICE_OBSERVED anchor, and jitter."""
    if atom_id and exchange is not None:
        repriced = _get_reprice_observed(exchange, atom_id)
        if repriced is not None:
            anchored = int(repriced.get('anchored_cost_units', 0))
            if anchored > 0:
                floor = consensus_borrow_floor(exchange, estimated_network_size)
                return _jitter(max(anchored, floor), BORROW_JITTER_FRAC)

    if descriptor is not None:
        complexity = feature_complexity_score(descriptor=descriptor)
        formula_cost = max(UNIT // 10_000, int(complexity * UNIT // 10))
    else:
        formula_cost = feature_borrow_cost_with_rep(
            loc, dependency_count, test_count,
            quality_verifications, total_adoptions,
        )
    floor = consensus_borrow_floor(exchange, estimated_network_size)
    cost = max(formula_cost, floor)
    return _jitter(cost, BORROW_JITTER_FRAC)


def _get_reprice_observed(exchange: LedgerAdapter, atom_id: str) -> dict | None:
    """Return the most recent REPRICE_OBSERVED record for atom_id, or None."""
    try:
        rows = exchange.audit_rows()
    except Exception:
        return None
    for row in reversed(rows):
        if row.get('operation') == 'REPRICE_OBSERVED' and row.get('atom') == atom_id:
            return row
    return None


def write_reprice_observed(
    exchange: LedgerAdapter,
    atom_id: str,
    observed_median_outcome_delta: float,
    borrow_count: int,
    network_rate: float = 1.0,
) -> dict | None:
    """Write a REPRICE_OBSERVED event when ≥5 verified borrows have been recorded."""
    if borrow_count < 5:
        return None
    try:
        from .p2p_cost_qualification import bootstrap_complete as _bootstrap_complete
        if not _bootstrap_complete(exchange):
            return None
    except Exception:
        pass

    import time
    anchored_cost = max(
        UNIT // 10_000,
        int(abs(observed_median_outcome_delta) * network_rate * UNIT),
    )
    record = {
        'operation': 'REPRICE_OBSERVED',
        'atom': atom_id,
        'observed_median_outcome_delta': observed_median_outcome_delta,
        'borrow_count': borrow_count,
        'anchored_at_unix': int(time.time()),
        'network_rate': network_rate,
        'anchored_cost_units': anchored_cost,
    }
    try:
        exchange.append_audit_row(record)
    except Exception:
        return None
    return record


def consensus_escrow_floor(exchange: LedgerAdapter | None = None) -> int:
    """Network-consensus minimum escrow budget from recent WORK_REQUEST rows."""
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
    exchange: LedgerAdapter | None = None,
    premium: float = 1.5,
) -> int:
    """Final escrow budget: base × premium, consensus floor, ±4% jitter."""
    raw = int(base_borrow_cost * premium)
    floor = consensus_escrow_floor(exchange)
    budget = max(raw, floor)
    return _jitter(budget, ESCROW_JITTER_FRAC)


# Per-exchange TTL cache
_split_shares_cache: _weakref.WeakKeyDictionary = _weakref.WeakKeyDictionary()


def consensus_split_shares(exchange: LedgerAdapter | None = None) -> tuple[float, float]:
    """Dynamic requester/hired mint split derived from past approved releases."""
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


def dynamic_budget_ceiling_multiplier(
    exchange: LedgerAdapter | None = None,
    total_minted: int = 0,
    network_size: int = 1,
    executor_cost_units: int = 0,
) -> float:
    """Anti-monopoly max budget multiplier for escrow work requests."""
    from .ledger_primitives import BASELINE_GRANT_UNITS
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

    if executor_cost_units > 0:
        base_borrow = apply_borrow_cost()
        if base_borrow > 0:
            executor_mult = executor_cost_units / base_borrow
            mult = min(mult, executor_mult)

    return mult


def feature_market_price(
    feature_id: str,
    exchange: LedgerAdapter,
    base_borrow_cost: int,
    quality_wilson: float = 0.5,
    adoption_count: int = 0,
    estimated_network_size: int = 1,
) -> int:
    """Dynamic borrow price reflecting feature quality, adoption velocity, supply."""
    quality_mult = max(0.8, min(2.0, 1.0 + quality_wilson))

    distinct_adopters = adoption_count
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

    feature_physics_max = max(UNIT, PHYSICS_CAP_UNITS_PER_PEER * max(1, estimated_network_size) // 20)
    s_mult = supply_pressure_multiplier(feature_spend, physics_max_units=feature_physics_max)
    raw = int(base_borrow_cost * quality_mult * velocity_mult * s_mult)
    price = max(base_borrow_cost, raw)
    return _jitter(price, BORROW_JITTER_FRAC)


def apply_cartel_penalty(exchange: LedgerAdapter, peer_id: str) -> dict:
    """Check if peer is operating as cartel member and apply penalty if so."""
    import time as _t
    import statistics as _stats

    try:
        rows = exchange.audit_rows()
    except Exception:
        return {'applied': False, 'reason': 'no_audit_rows'}

    now = _t.time()
    window_30d = now - 30 * 86400
    window_7d = now - 7 * 86400

    recent_penalties = [
        r for r in rows
        if r.get('kind') == 'CREDIT_DELTA'
        and r.get('direction') == 'cartel_penalty'
        and r.get('peer') == peer_id
        and float(r.get('at_unix', 0)) > window_7d
    ]
    if recent_penalties:
        return {'applied': False, 'reason': 'already_penalized_in_7d_window'}

    earn_rows = [
        r for r in rows
        if r.get('kind') == 'CREDIT_DELTA'
        and r.get('direction') in ('earn', 'composition_referral', 'delivery_fee', 'borrow_earn', 'seal_reward', 'llm_peer_reward')
        and float(r.get('at_unix', 0)) > window_30d
    ]
    if not earn_rows:
        return {'applied': False, 'reason': 'no_earn_rows'}

    peer_totals: dict[str, int] = {}
    for r in earn_rows:
        p = r.get('peer', '')
        if p:
            peer_totals[p] = peer_totals.get(p, 0) + abs(int(r.get('delta_units', r.get('amount_units', 0))))

    if len(peer_totals) < 2:
        return {'applied': False, 'reason': 'insufficient_peers_for_comparison'}

    peer_earn = peer_totals.get(peer_id, 0)
    if peer_earn == 0:
        return {'applied': False, 'reason': 'peer_has_no_earnings'}

    network_median = _stats.median(peer_totals.values())
    if network_median <= 0:
        return {'applied': False, 'reason': 'zero_network_median'}

    cartel_threshold = 3.0 * network_median
    if peer_earn <= cartel_threshold:
        return {'applied': False, 'reason': f'earn_rate_ok ({peer_earn} <= {cartel_threshold:.1f})'}

    confidence = min(1.0, (peer_earn / network_median - 3.0) / 3.0)

    excess = peer_earn - network_median
    if confidence < 0.5:
        import datetime as _dt
        exchange.append_audit_row({
            'kind': 'CARTEL_WARNING',
            'peer': peer_id,
            'peer_earn_30d': peer_earn,
            'network_median_30d': round(network_median, 2),
            'confidence': round(confidence, 3),
            'at_unix': now,
            'at': _dt.datetime.now(_dt.timezone.utc).isoformat(),
            'note': f'Cartel warning (conf={confidence:.2f}): earn {peer_earn} > 3× median — no penalty yet',
        })
        return {'applied': False, 'reason': f'cartel_warning_only (confidence={confidence:.2f})', 'confidence': confidence}
    elif confidence < 0.8:
        penalty = max(1, int(excess * 0.30))
    else:
        penalty = max(1, int(excess * 0.50))

    import datetime as _dt
    exchange.append_audit_row({
        'kind': 'CREDIT_DELTA',
        'direction': 'cartel_penalty',
        'peer': peer_id,
        'amount_units': -penalty,
        'peer_earn_30d': peer_earn,
        'network_median_30d': round(network_median, 2),
        'cartel_threshold': round(cartel_threshold, 2),
        'excess': excess,
        'at_unix': now,
        'at': _dt.datetime.now(_dt.timezone.utc).isoformat(),
        'note': f'Cartel penalty: earn {peer_earn} > 3× median {network_median:.1f} — excess*0.5={penalty}',
    })
    exchange.append_audit_row({
        'kind': 'CARTEL_WEIGHT_PENALTY',
        'peer': peer_id,
        'penalty_units': penalty,
        'peer_earn_30d': peer_earn,
        'network_median_30d': round(network_median, 2),
        'at_unix': now,
        'at': _dt.datetime.now(_dt.timezone.utc).isoformat(),
    })
    return {'applied': True, 'penalty_units': penalty, 'peer_earn_30d': peer_earn,
            'network_median_30d': round(network_median, 2)}
