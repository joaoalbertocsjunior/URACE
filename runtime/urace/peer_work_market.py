"""Distributed work request and escrow-hire market for P2P feature delivery.

Audit row kinds (all append-only, never modified):
  WORK_REQUEST  — requester broadcasts a feature spec + budget
  WORK_BID      — eligible peer bids on a request
  WORK_ACCEPTED — requester accepts a bid (escrow locked)
  WORK_DELIVERY — hired node submits delivery (canonical_fingerprint)
  WORK_VERIFIED — requester verifies delivery (approved=True/False)
  WORK_DISPUTED — dispute filed by requester or hired node
  WORK_RESOLVED — multi-sig arbitrator resolution

State machine (derived from audit rows):
  OPEN → ASSIGNED → IN_DELIVERY → VERIFICATION → RELEASED
                                               ↘ DISPUTED → RESOLVED
"""
from __future__ import annotations
import hashlib as _hashlib
import math
import time
import weakref
from typing import Any

# ── Exceptions ────────────────────────────────────────────────────────────────

class EscrowNotFoundError(KeyError):
    """Raised when escrow_state_or_raise() cannot find the request_id."""


# ── Autonomous task decomposition ─────────────────────────────────────────────
DECOMPOSE_THRESHOLD = 0.7   # complexity ≥ this triggers auto-decomposition
DECOMPOSE_MIN_BP    = 0.25  # minimum complexity per sub-task (prevents infinite recursion)

# ── LLM-as-peer / executor node registration ──────────────────────────────────
EXECUTOR_PEER_KIND = 'EXECUTOR_PEER_REGISTERED'

SCHEMA = 'urace-work-market-v1'

# ── Work mode: open marketplace vs trusted cohort ─────────────────────────────
WORK_MODE_AGORA  = 'agora'   # open marketplace — any qualified peer can bid
WORK_MODE_COHORT = 'cohort'  # trusted group only — only pinned/pre-approved peers

# Equity constants
HIRED_CREATOR_SHARE   = 0.40   # hired node(s) share of future mint_per_adoption (default)
SPONSOR_CREATOR_SHARE = 0.60   # requester/sponsor share (default; overridden by consensus)
CUSTOM_WORK_PREMIUM   = 1.5    # budget = apply_borrow_cost() × 1.5
MAX_BUDGET_MULTIPLIER = 3.0    # fallback ceiling multiplier (dynamic preferred)
AUTO_RELEASE_SECONDS  = 7 * 86400   # fallback auto-release (overridden per-contract by complexity)

# Dynamic contract timeout: timeout = max(1d, complexity × BASE_DAYS × 2× buffer) / sqrt(n_nodes)
CONTRACT_BASE_SECONDS   = 3 * 86400    # 3 days × complexity for a single-node contract
CONTRACT_MIN_SECONDS    = 1 * 86400    # minimum 1 day
CONTRACT_MAX_SECONDS    = 30 * 86400   # maximum 30 days

# Pre-paid escrow deposit (anti-sybil, compensates hired nodes on abandonment)
ESCROW_DEPOSIT_FRACTION = 0.10   # 10% of budget upfront; deducted from final payment on success

# Late ownership claim
CLAIM_WINDOW_SECONDS    = 30 * 86400   # requester can claim within 30 days of delivery
LATE_CLAIM_FEE_FRACTION = 0.10         # 10% of current_mint_value as claim fee

# Colliding escrow (cost-sharing / boost)
BOOST_MARGIN_PER_CO    = 0.10          # +10% boost per additional co-requester
MAX_BOOST_MULTIPLIER   = 1.50          # cap at +50% total boost
MAX_CO_REQUESTER_SHARE = 0.80          # single requester cannot exceed 80% of merged budget

# Rate limiting (anti deposit-drain / sybil flood)
WORK_REQUEST_DAILY_LIMIT = 5           # max work requests per peer per 24h

# Multi-sig peer review quorum
VERIFICATION_QUORUM = 3                # independent peer reviews needed before escrow releases


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _check_rate_limit(exchange, requester_id: str) -> None:
    """Raise ValueError if requester has hit WORK_REQUEST_DAILY_LIMIT in last 24h."""
    cutoff = time.time() - 86400
    recent = [
        r for r in _request_rows(exchange)
        if r.get('kind') == 'WORK_REQUEST'
        and r.get('requester_id') == requester_id
        and float(r.get('at_unix', 0)) > cutoff
    ]
    if len(recent) >= WORK_REQUEST_DAILY_LIMIT:
        raise ValueError(
            f'Rate limit: {requester_id!r} created {len(recent)} work requests in 24h '
            f'(max {WORK_REQUEST_DAILY_LIMIT}). Prevents coordinated deposit-drain attacks.'
        )


def contract_timeout_seconds(complexity: float = 0.5, n_nodes: int = 1) -> int:
    """Dynamic contract timeout based on task complexity and node count.

    More nodes → faster expected delivery (√n scaling).
    Formula: clamp(MIN, MAX, BASE × complexity × 2× buffer / sqrt(n_nodes))
    """
    n = max(1, n_nodes)
    raw = CONTRACT_BASE_SECONDS * max(0.1, complexity) * 2.0 / math.sqrt(n)
    return int(max(CONTRACT_MIN_SECONDS, min(CONTRACT_MAX_SECONDS, raw)))


# Module-level row cache: (all_row_count) → filtered_work_rows
# Keyed separately for (None = all) and (request_id) slices.
# Per-exchange row cache: exchange → {(request_id_or_None): (row_count, result)}
# WeakKeyDictionary prevents id() reuse collisions when exchange objects are GC'd.
_ROW_CACHE: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()

_WORK_KINDS = frozenset({
    'WORK_REQUEST', 'WORK_BID', 'WORK_ACCEPTED',
    'WORK_DELIVERY', 'WORK_VERIFIED', 'WORK_DISPUTED', 'WORK_RESOLVED',
    'WORK_MERGED', 'WORK_OWNERSHIP_CLAIM', 'WORK_ARBITRATOR_ASSIGNED',
    'WORK_PEER_REVIEW', EXECUTOR_PEER_KIND,
})


def _request_rows(exchange, request_id: str | None = None) -> list[dict]:
    """Return all work-market audit rows, optionally filtered by request_id.

    O(n) on cache miss; O(1) on hit (same row count = no new appends).
    Uses WeakKeyDictionary to avoid id() reuse collisions across exchange lifetimes.
    """
    try:
        rows = exchange.audit_rows()
    except Exception:
        return []
    n = len(rows)
    ex_cache = _ROW_CACHE.setdefault(exchange, {})
    cached = ex_cache.get(request_id)
    if cached is not None and cached[0] == n:
        return cached[1]

    if request_id is None:
        result = [r for r in rows if r.get('kind') in _WORK_KINDS]
    else:
        result = [r for r in rows if r.get('kind') in _WORK_KINDS and r.get('request_id') == request_id]
    ex_cache[request_id] = (n, result)
    return result


def escrow_state(request_id: str, exchange) -> dict[str, Any]:
    """Derive current state of a work request from audit rows.

    Returns:
        {
          'state': 'OPEN'|'ASSIGNED'|'IN_DELIVERY'|'VERIFICATION'|
                   'RELEASED'|'DISPUTED'|'RESOLVED'|'NOT_FOUND',
          'request': dict,
          'bids': list[dict],
          'accepted_bids': list[dict],
          'deliveries': list[dict],
          'verified': bool,
          'disputed': bool,
          'resolved': bool,
          'auto_release_due': bool,
          'quorum_fallback': bool,   # True if < VERIFICATION_QUORUM neutral peers available
        }
    """
    rows = _request_rows(exchange, request_id)
    if not rows:
        return {'state': 'NOT_FOUND', 'request': {}, 'bids': [], 'accepted_bids': [],
                'deliveries': [], 'verified': False, 'disputed': False, 'resolved': False,
                'auto_release_due': False, 'quorum_fallback': False, 'peer_reviews': [],
                'quorum': None}

    request = next((r for r in rows if r.get('kind') == 'WORK_REQUEST'), {})
    bids = [r for r in rows if r.get('kind') == 'WORK_BID']
    accepted = [r for r in rows if r.get('kind') == 'WORK_ACCEPTED']
    deliveries = [r for r in rows if r.get('kind') == 'WORK_DELIVERY']
    peer_reviews = [r for r in rows if r.get('kind') == 'WORK_PEER_REVIEW']
    verified = any(r.get('approved') for r in rows if r.get('kind') == 'WORK_VERIFIED')
    disputed = any(r.get('kind') == 'WORK_DISPUTED' for r in rows)
    resolved = any(r.get('kind') == 'WORK_RESOLVED' for r in rows)

    # Peer-review quorum: majority of VERIFICATION_QUORUM independent reviews
    quorum: bool | None = None
    if len(peer_reviews) >= VERIFICATION_QUORUM:
        approvals = sum(1 for r in peer_reviews if r.get('approved'))
        quorum = approvals > len(peer_reviews) / 2

    # Quorum stall fallback: when fewer than VERIFICATION_QUORUM neutral peers have
    # reviewed, check if there are even enough eligible neutrals in the entire audit log.
    # If not, set quorum_fallback=True so callers can fall back to requester-only verification
    # rather than stalling indefinitely.
    quorum_fallback = False
    if quorum is None and len(peer_reviews) < VERIFICATION_QUORUM:
        dispute_party_ids: set[str] = set()
        if request.get('requester_id'):
            dispute_party_ids.add(request['requester_id'])
        for bid in accepted:
            if bid.get('bidder_id'):
                dispute_party_ids.add(bid['bidder_id'])
        for d in deliveries:
            if d.get('hired_peer_id'):
                dispute_party_ids.add(d['hired_peer_id'])
        try:
            all_rows = exchange.audit_rows()
        except Exception:
            all_rows = []
        neutral_verified = {
            row.get('hired_peer_id') or row.get('bidder_id')
            for row in all_rows
            if row.get('kind') in ('WORK_VERIFIED', 'WORK_DELIVERY')
            and row.get('approved', False)
            and (row.get('hired_peer_id') or row.get('bidder_id')) not in dispute_party_ids
        } - {None}
        if len(neutral_verified) < VERIFICATION_QUORUM:
            quorum_fallback = True

    # Auto-release: use per-contract timeout (based on complexity), fall back to AUTO_RELEASE_SECONDS
    auto_release_due = False
    if deliveries and not disputed and not verified:
        latest_delivery_time = max(float(d.get('at_unix', 0)) for d in deliveries)
        req_complexity = float(request.get('complexity', 0.5))
        req_n_nodes = int(request.get('n_nodes', 1))
        timeout = int(request.get('timeout_seconds',
                                   contract_timeout_seconds(req_complexity, req_n_nodes)))
        auto_release_due = (time.time() - latest_delivery_time) > timeout

    # Derive state
    if resolved:
        state = 'RESOLVED'
    elif disputed:
        state = 'DISPUTED'
    elif verified or auto_release_due:
        state = 'RELEASED'
    elif deliveries:
        state = 'VERIFICATION'
    elif accepted:
        state = 'IN_DELIVERY'
    elif bids:
        state = 'OPEN'  # has bids but none accepted yet
    else:
        state = 'OPEN'

    return {
        'state': state,
        'request': request,
        'bids': bids,
        'accepted_bids': accepted,
        'deliveries': deliveries,
        'peer_reviews': peer_reviews,
        'quorum': quorum,
        'quorum_fallback': quorum_fallback,
        'verified': verified,
        'disputed': disputed,
        'resolved': resolved,
        'auto_release_due': auto_release_due,
    }


def escrow_state_or_raise(request_id: str, exchange) -> dict[str, Any]:
    """Like escrow_state() but raises EscrowNotFoundError instead of returning NOT_FOUND."""
    st = escrow_state(request_id, exchange)
    if st['state'] == 'NOT_FOUND':
        raise EscrowNotFoundError(f'Work request {request_id!r} not found')
    return st


def create_work_request(
    exchange,
    requester_id: str,
    spec: str,
    budget_units: int,
    min_combined_rep: float = 0.3,
    n_nodes: int = 1,
    sub_tasks: list[dict] | None = None,
    complexity: float = 0.5,
    root: str | None = None,
    work_mode: str = WORK_MODE_AGORA,
    cohort_rep_floor: float = 0.5,
) -> str:
    """Broadcast a WORK_REQUEST. Returns the request_id.

    budget_units: pre-computed via escrow_budget_units() (includes jitter + consensus floor).
    n_nodes:      number of hired nodes for distributed scope (1 = single node)
    sub_tasks:    list of {'id': str, 'spec': str, 'complexity': float} for N-node scope
    complexity:   normalised [0,1] task complexity — drives timeout_seconds calculation
    root:         ledger root. When provided, charges ESCROW_DEPOSIT_FRACTION × budget upfront
                  (anti-sybil; deducted from final payment on success; compensates hired nodes
                  on abandonment). Tests may pass None to skip ledger interaction.

    Raises ValueError if budget is below consensus escrow floor (anti-undercutting).
    """
    _check_rate_limit(exchange, requester_id)
    from . import credit_ledger as _cl
    floor = _cl.consensus_escrow_floor(exchange)
    if budget_units < floor:
        raise ValueError(
            f'budget_units {budget_units} < consensus_escrow_floor {floor} — '
            'suspected AI undercutting; use escrow_budget_units() to compute budget'
        )
    timeout = contract_timeout_seconds(complexity, n_nodes)
    request_id = f"wreq-{int(time.time() * 1000)}-{requester_id[:8]}"

    # Pre-paid deposit: charge upfront to deter sybil requesters / market-probing
    deposit_paid = 0
    if root is not None:
        deposit_paid = int(budget_units * ESCROW_DEPOSIT_FRACTION)
        if deposit_paid > 0:
            _cl.spend_units(root, requester_id, deposit_paid,
                            f'escrow-deposit:{request_id}', bundle_id=request_id)

    exchange.append_audit_row({
        'kind': 'WORK_REQUEST',
        'request_id': request_id,
        'requester_id': requester_id,
        'spec': spec,
        'budget_units': budget_units,
        'min_combined_rep': min_combined_rep,
        'n_nodes': n_nodes,
        'sub_tasks': sub_tasks or [],
        'complexity': complexity,
        'timeout_seconds': timeout,
        'deposit_paid': deposit_paid,
        'mode': work_mode,
        'cohort_rep_floor': cohort_rep_floor if work_mode == WORK_MODE_COHORT else None,
        'at_unix': time.time(),
        'at': _now_iso(),
    })
    return request_id


def submit_bid(
    exchange,
    request_id: str,
    bidder_id: str,
    combined_rep: float,
    sub_task_id: str | None = None,
) -> None:
    """Submit a WORK_BID. combined_rep must meet min_combined_rep to be valid."""
    st = escrow_state(request_id, exchange)
    if st['state'] != 'OPEN':
        raise ValueError(f'Request {request_id} is not open for bids (state={st["state"]})')
    min_rep = float(st['request'].get('min_combined_rep', 0.3))
    if combined_rep < min_rep:
        raise ValueError(f'combined_rep {combined_rep:.3f} < min {min_rep:.3f}')
    # Cohort mode: only peers with reputation >= cohort_rep_floor can bid
    req_mode = st['request'].get('mode', WORK_MODE_AGORA)
    if req_mode == WORK_MODE_COHORT:
        floor = float(st['request'].get('cohort_rep_floor') or 0.5)
        if combined_rep < floor:
            raise ValueError(
                f'Cohort mode: bidder combined_rep {combined_rep:.3f} < cohort_rep_floor {floor:.3f}. '
                'Only trusted peers (pinned + reputation >= floor) may bid on cohort requests.'
            )
    exchange.append_audit_row({
        'kind': 'WORK_BID',
        'request_id': request_id,
        'bidder_id': bidder_id,
        'combined_rep': combined_rep,
        'sub_task_id': sub_task_id,
        'at_unix': time.time(),
        'at': _now_iso(),
    })


def accept_bid(
    exchange,
    root: str,
    request_id: str,
    bidder_id: str,
    sub_task_id: str | None = None,
) -> None:
    """Accept a bid — locks escrow credits from requester.

    Calls credit_ledger.escrow_lock() to deduct budget from requester.
    """
    from . import credit_ledger as _cl
    st = escrow_state(request_id, exchange)
    if st['state'] not in ('OPEN',):
        raise ValueError(f'Cannot accept bid in state {st["state"]}')
    req = st['request']
    requester_id = req.get('requester_id', '')
    budget = int(req.get('budget_units', 0))
    if budget <= 0:
        raise ValueError('Invalid budget')
    _cl.escrow_lock(root, requester_id, request_id, budget)
    exchange.append_audit_row({
        'kind': 'WORK_ACCEPTED',
        'request_id': request_id,
        'requester_id': requester_id,
        'bidder_id': bidder_id,
        'budget_units': budget,
        'sub_task_id': sub_task_id,
        'at_unix': time.time(),
        'at': _now_iso(),
    })


def submit_delivery(
    exchange,
    request_id: str,
    hired_peer_id: str,
    delivery_hash: str,
    sub_task_id: str | None = None,
) -> None:
    """Submit a WORK_DELIVERY row.

    Spam guard: rejects a second delivery from the same peer on the same
    sub_task unless the prior delivery was disputed (so peers cannot race
    auto-release by flooding submissions).
    """
    st = escrow_state(request_id, exchange)
    # Allow VERIFICATION for multi-node scope: different peers can still submit
    # their sub_task delivery even after the first sub_task triggered VERIFICATION.
    if st['state'] not in ('IN_DELIVERY', 'ASSIGNED', 'VERIFICATION'):
        raise ValueError(f'Cannot submit delivery in state {st["state"]}')
    # Spam guard: one submission per (peer, sub_task) before verification
    prior = [
        d for d in st['deliveries']
        if d.get('hired_peer_id') == hired_peer_id
        and d.get('sub_task_id') == sub_task_id
    ]
    if prior and not st['disputed']:
        raise ValueError(
            f'Delivery spam rejected: {hired_peer_id} already submitted for '
            f'sub_task={sub_task_id!r}. File a dispute to re-submit.'
        )
    exchange.append_audit_row({
        'kind': 'WORK_DELIVERY',
        'request_id': request_id,
        'hired_peer_id': hired_peer_id,
        'delivery_hash': delivery_hash,
        'sub_task_id': sub_task_id,
        'at_unix': time.time(),
        'at': _now_iso(),
    })


def verify_delivery(
    exchange,
    root: str,
    request_id: str,
    requester_id: str,
    approved: bool,
    dispute_reason: str = '',
    dispute_kind: str = 'quality',   # 'quality' | 'gibberish' | 'timeout' | 'other'
) -> None:
    """Verify delivery — releases or disputes escrow.

    On approval: calls credit_ledger.escrow_release() to pay hired node(s).
    On dispute: records WORK_DISPUTED for arbitration.
    """
    from . import credit_ledger as _cl
    st = escrow_state(request_id, exchange)
    if st['state'] not in ('VERIFICATION', 'RELEASED'):
        raise ValueError(f'Cannot verify in state {st["state"]}')

    if approved or st['auto_release_due']:
        # Build hired node list from accepted bids
        hired = [(r['bidder_id'], float(r.get('budget_units', 0)))
                 for r in st['accepted_bids']]
        if hired:
            total_budget = sum(amt for _, amt in hired)
            shares = equity_split_budget(hired, total_budget)
            _cl.escrow_release(root, request_id, shares)
        exchange.append_audit_row({
            'kind': 'WORK_VERIFIED',
            'request_id': request_id,
            'requester_id': requester_id,
            'approved': True,
            'auto_released': st['auto_release_due'],
            'at_unix': time.time(),
            'at': _now_iso(),
        })
    else:
        exchange.append_audit_row({
            'kind': 'WORK_DISPUTED',
            'request_id': request_id,
            'requester_id': requester_id,
            'dispute_reason': dispute_reason,
            'dispute_kind': dispute_kind,   # 'gibberish' triggers arbitration, not just auto-hold
            'at_unix': time.time(),
            'at': _now_iso(),
        })


def equity_split_budget(
    hired_nodes: list[tuple[str, float]],
    total_budget: int,
) -> list[tuple[str, int]]:
    """Compute per-node credit payment from escrow.

    hired_nodes: list of (peer_id, complexity_weight)
    total_budget: total escrow amount in base units

    Returns list of (peer_id, units) that sum to total_budget.
    """
    if not hired_nodes:
        return []
    total_weight = sum(w for _, w in hired_nodes)
    if total_weight == 0:
        # Equal split if no weight data
        per = total_budget // len(hired_nodes)
        return [(pid, per) for pid, _ in hired_nodes]
    splits = []
    distributed = 0
    for i, (pid, weight) in enumerate(hired_nodes):
        if i == len(hired_nodes) - 1:
            # Last node gets the remainder to avoid rounding loss
            splits.append((pid, total_budget - distributed))
        else:
            share = int(total_budget * weight / total_weight)
            splits.append((pid, share))
            distributed += share
    return splits


def routing_score(
    exchange,
    local_credit_balance: int,
    baseline_grant_units: int,
    spec_complexity: float,
    executor_cost_units: int,
    available_peers: list[dict] | None = None,
) -> dict:
    """Decide: executor | network_hire | p2p_feature.

    Returns:
        {
          'route': 'executor' | 'network_hire' | 'p2p_feature',
          'confidence': float,   # 0.0–1.0 routing confidence
          'reason': str,
          'network_hire_viable': bool,
          'avg_peer_rep': float,
          'credit_pressure': float,
          'executor_cost_factor': float,
        }

    Routing logic (evaluated in priority order):
      1. p2p_feature  — if exchange has adopted features matching intent (handled upstream)
      2. network_hire — if:
           - spec_complexity ≥ 0.6 (non-trivial work)
           AND avg_peer_rep ≥ 0.5 (network quality sufficient)
           AND (executor_cost_factor ≥ 1.5 OR credit_pressure ≥ 0.6)
      3. executor     — fallback

    executor_cost_factor = executor_cost_units / consensus_escrow_floor(exchange)
    Ratio > 1.5 means hiring peers is cheaper than running the executor.
    """
    from . import credit_ledger as _cl

    credit_pressure = max(0.0, min(1.0, 1.0 - local_credit_balance / max(1, baseline_grant_units * 10)))

    peers = available_peers or []
    avg_peer_rep = (
        sum(p.get('combined_rep', 0.0) for p in peers) / len(peers)
        if peers else 0.0
    )
    network_hire_viable = (
        len(peers) >= 1
        and avg_peer_rep >= 0.5
        and spec_complexity >= 0.6
    )

    escrow_floor = _cl.consensus_escrow_floor(exchange)
    executor_cost_factor = (
        executor_cost_units / escrow_floor
        if escrow_floor > 0 else 0.0
    )

    route = 'executor'
    reason = 'default executor path'
    confidence = 0.7

    if network_hire_viable and (executor_cost_factor >= 1.5 or credit_pressure >= 0.6):
        route = 'network_hire'
        confidence = min(0.95, 0.5 + 0.25 * avg_peer_rep + 0.2 * credit_pressure)
        reason = (
            f'network_hire preferred: complexity={spec_complexity:.2f} '
            f'avg_rep={avg_peer_rep:.2f} cost_factor={executor_cost_factor:.2f} '
            f'credit_pressure={credit_pressure:.0%}'
        )
    elif not network_hire_viable and credit_pressure < 0.4:
        confidence = 0.8
        reason = f'executor: low credit_pressure={credit_pressure:.0%} network insufficient'

    return {
        'route': route,
        'confidence': confidence,
        'reason': reason,
        'network_hire_viable': network_hire_viable,
        'avg_peer_rep': avg_peer_rep,
        'credit_pressure': credit_pressure,
        'executor_cost_factor': executor_cost_factor,
    }


def future_mint_split(
    mint_amount: int,
    hired_nodes: list[tuple[str, float]],
    exchange=None,
    co_requester_shares: dict[str, float] | None = None,
) -> dict[str, int]:
    """Split mint_per_adoption between sponsor(s) and hired creators.

    Uses network consensus split shares (consensus_split_shares) when exchange
    is provided; falls back to SPONSOR_CREATOR_SHARE (0.60) / HIRED_CREATOR_SHARE (0.40).

    co_requester_shares: {requester_id: fraction} for merged contracts — fractions
        must sum to 1.0. Requester portion is split proportionally among co-requesters.

    Returns {'requester'|requester_id: units, peer_id: units, ...}
    """
    if not hired_nodes or mint_amount <= 0:
        return {}
    from . import credit_ledger as _cl
    req_share, hired_share = _cl.consensus_split_shares(exchange)
    requester_total = int(mint_amount * req_share)
    hired_total = mint_amount - requester_total

    result: dict[str, int] = {}
    # Split requester portion among co-requesters if provided
    if co_requester_shares:
        total_w = sum(co_requester_shares.values())
        dist = 0
        items = list(co_requester_shares.items())
        for i, (rid, w) in enumerate(items):
            if i == len(items) - 1:
                result[rid] = requester_total - dist
            else:
                amt = int(requester_total * w / total_w) if total_w > 0 else 0
                result[rid] = amt
                dist += amt
    else:
        result['requester'] = requester_total

    # Split hired portion by complexity weight
    total_weight = sum(w for _, w in hired_nodes)
    distributed = 0
    for i, (pid, weight) in enumerate(hired_nodes):
        if i == len(hired_nodes) - 1:
            result[pid] = hired_total - distributed
        else:
            share = int(hired_total * weight / total_weight) if total_weight > 0 else hired_total // len(hired_nodes)
            result[pid] = share
            distributed += share
    return result


# ── Late ownership claim ──────────────────────────────────────────────────────

def claim_ownership(
    exchange,
    root: str,
    request_id: str,
    requester_id: str,
    current_mint_value: int,
) -> None:
    """Requester claims ownership rights post-delivery within the claim window.

    Anti-abuse protections:
    1. Time-boxed: must be called within CLAIM_WINDOW_SECONDS of delivery.
       After the window, hired node auto-promotes to co-creator at no cost.
       Prevents strategic delay ("wait and see if feature is market-valuable").
    2. Claim fee: LATE_CLAIM_FEE_FRACTION × current_mint_value.
       Fee scales with adoption — probing market value is expensive.
    3. One claim per request_id.

    Records WORK_OWNERSHIP_CLAIM audit row.
    Raises ValueError on window expiry or duplicate claim.
    """
    from . import credit_ledger as _cl
    st = escrow_state(request_id, exchange)
    if st['state'] not in ('RELEASED', 'RESOLVED', 'VERIFICATION'):
        raise ValueError(f'Cannot claim ownership in state {st["state"]}')
    # Identity guard: only the original requester can claim ownership
    original_requester = st['request'].get('requester_id', '')
    if original_requester and requester_id != original_requester:
        raise ValueError(
            f'Identity mismatch: {requester_id!r} is not the original requester '
            f'{original_requester!r} — fake ownership claims rejected'
        )
    # Check window
    if st['deliveries']:
        latest_ts = max(float(d.get('at_unix', 0)) for d in st['deliveries'])
        elapsed = time.time() - latest_ts
        if elapsed > CLAIM_WINDOW_SECONDS:
            raise ValueError(
                f'Claim window expired ({elapsed/86400:.1f}d > {CLAIM_WINDOW_SECONDS//86400}d). '
                'Hired node auto-promoted to co-creator.'
            )
    # Duplicate claim guard
    existing_claims = [r for r in _request_rows(exchange, request_id)
                       if r.get('kind') == 'WORK_OWNERSHIP_CLAIM']
    if existing_claims:
        raise ValueError(f'Ownership already claimed for {request_id}')
    # Pay claim fee (scales with mint value — discourages opportunistic probing)
    fee = int(current_mint_value * LATE_CLAIM_FEE_FRACTION)
    if fee > 0:
        _cl.spend_units(root, requester_id, fee, f'ownership-claim-fee:{request_id}',
                        bundle_id=request_id)
    exchange.append_audit_row({
        'kind': 'WORK_OWNERSHIP_CLAIM',
        'request_id': request_id,
        'requester_id': requester_id,
        'claim_fee_paid': fee,
        'current_mint_value': current_mint_value,
        'at_unix': time.time(),
        'at': _now_iso(),
    })


# ── Colliding escrow (cost-sharing + boost) ────────────────────────────────────

def merge_work_requests(
    exchange,
    root: str,
    primary_request_id: str,
    co_requester_id: str,
    co_budget_units: int,
) -> dict:
    """Merge a co-requester into an existing OPEN work request.

    Cost sharing: co-requester contributes proportionally to the total budget.
    Boost: hired nodes receive a premium for satisfying multiple requesters.
        boost = 1.0 + BOOST_MARGIN_PER_CO × (current_co_count)
        capped at MAX_BOOST_MULTIPLIER.

    Anti-monopoly:
    - Any single requester (including primary) cannot exceed MAX_CO_REQUESTER_SHARE
      of the merged total budget.
    - Boost ceiling prevents merged budget from exceeding executor cost.

    Records WORK_MERGED audit row. Returns updated budget info.
    """
    from . import credit_ledger as _cl
    st = escrow_state(primary_request_id, exchange)
    if st['state'] != 'OPEN':
        raise ValueError(f'Can only merge into OPEN request (state={st["state"]})')
    # Count existing co-requesters
    prior_merges = [r for r in _request_rows(exchange, primary_request_id)
                    if r.get('kind') == 'WORK_MERGED']
    n_co = len(prior_merges) + 1   # including this merge
    primary_budget = int(st['request'].get('budget_units', 0))
    total_before_boost = primary_budget + co_budget_units
    # Anti-monopoly: each party ≤ MAX_CO_REQUESTER_SHARE
    for label, amt in [('primary', primary_budget), ('co-requester', co_budget_units)]:
        if total_before_boost > 0 and amt / total_before_boost > MAX_CO_REQUESTER_SHARE:
            raise ValueError(
                f'{label} share {amt/total_before_boost:.0%} exceeds '
                f'MAX_CO_REQUESTER_SHARE {MAX_CO_REQUESTER_SHARE:.0%}'
            )
    # Boost margin for hired nodes (supply/demand premium for prioritised work)
    boost = min(MAX_BOOST_MULTIPLIER, 1.0 + BOOST_MARGIN_PER_CO * n_co)
    merged_budget = int(total_before_boost * boost)
    # Escrow the co-requester's share (their proportional contribution)
    co_fraction = co_budget_units / total_before_boost if total_before_boost > 0 else 0.5
    co_escrow = int(merged_budget * co_fraction)
    _cl.escrow_lock(root, co_requester_id, primary_request_id, co_escrow)
    exchange.append_audit_row({
        'kind': 'WORK_MERGED',
        'request_id': primary_request_id,
        'co_requester_id': co_requester_id,
        'co_budget_units': co_budget_units,
        'co_escrow_locked': co_escrow,
        'merged_budget_units': merged_budget,
        'boost_multiplier': boost,
        'n_co_requesters': n_co,
        'at_unix': time.time(),
        'at': _now_iso(),
    })
    return {
        'merged_budget_units': merged_budget,
        'boost_multiplier': boost,
        'co_fraction': co_fraction,
        'n_co_requesters': n_co,
    }


def merged_co_requester_shares(request_id: str, exchange) -> dict[str, float]:
    """Derive {requester_id: fraction} for future mint split in merged contracts.

    Primary requester gets share proportional to their budget contribution.
    Each co-requester likewise. Fractions sum to 1.0.
    """
    st = escrow_state(request_id, exchange)
    req = st['request']
    primary_id = req.get('requester_id', 'requester')
    primary_budget = float(req.get('budget_units', 0))
    contributions: dict[str, float] = {primary_id: primary_budget}
    for row in _request_rows(exchange, request_id):
        if row.get('kind') == 'WORK_MERGED':
            cid = row.get('co_requester_id', '')
            if cid:
                contributions[cid] = contributions.get(cid, 0) + float(row.get('co_budget_units', 0))
    total = sum(contributions.values())
    if total == 0:
        return {primary_id: 1.0}
    return {k: v / total for k, v in contributions.items()}


# ── Arbitrator selection ───────────────────────────────────────────────────────

def select_arbitrators(exchange, request_id: str, n: int = 3) -> list[str]:
    """Select neutral arbitrators for a disputed work request.

    Priority model:
    - Eligible: peers with ≥1 approved delivery that produced mint (block-closers).
    - Score: combined_rep × (1 − graph_proximity_to_dispute_parties).
    - graph_proximity: 1.0 if peer appeared in same request rows as requester/hired;
      0.0 if fully independent.
    - Tie-break: deterministic seed from hash(request_id + peer_id).
    - Requires odd number ≥ n for majority vote (bumps to n+1 if n is even).

    Returns list of peer_ids (may be empty if no eligible arbitrators).
    """
    import hashlib as _hl
    # Ensure odd number for majority vote
    if n % 2 == 0:
        n += 1
    st = escrow_state(request_id, exchange)
    # Identify dispute parties
    dispute_party_ids: set[str] = set()
    req = st['request']
    if req.get('requester_id'):
        dispute_party_ids.add(req['requester_id'])
    for bid in st['accepted_bids']:
        if bid.get('bidder_id'):
            dispute_party_ids.add(bid['bidder_id'])
    for d in st['deliveries']:
        if d.get('hired_peer_id'):
            dispute_party_ids.add(d['hired_peer_id'])

    # Gather all audit rows to find block-closers and their proximity
    try:
        all_rows = exchange.audit_rows()
    except Exception:
        return []

    # Block-closers: peers whose delivery was approved and in a different request
    block_closer_reps: dict[str, float] = {}
    for row in all_rows:
        if row.get('kind') == 'WORK_VERIFIED' and row.get('approved'):
            rid = row.get('request_id', '')
            if rid != request_id:
                # Find hired peers for this verified request
                for drow in all_rows:
                    if drow.get('kind') == 'WORK_DELIVERY' and drow.get('request_id') == rid:
                        pid = drow.get('hired_peer_id', '')
                        if pid and pid not in dispute_party_ids:
                            cr = float(row.get('combined_rep', 0.5))
                            block_closer_reps[pid] = max(block_closer_reps.get(pid, 0.0), cr)

    if not block_closer_reps:
        return []

    # Graph proximity: which peers appeared alongside dispute parties?
    peers_in_dispute_requests: set[str] = set()
    for row in all_rows:
        if row.get('kind') in ('WORK_BID', 'WORK_ACCEPTED', 'WORK_DELIVERY'):
            rid = row.get('request_id', '')
            pid = row.get('bidder_id') or row.get('hired_peer_id') or ''
            # If this peer bid/worked on any request involving a dispute party...
            dispute_req_ids = {
                r2.get('request_id', '')
                for r2 in all_rows
                if r2.get('kind') in ('WORK_BID', 'WORK_ACCEPTED', 'WORK_DELIVERY')
                and (r2.get('bidder_id') in dispute_party_ids
                     or r2.get('hired_peer_id') in dispute_party_ids)
            }
            if rid in dispute_req_ids and pid:
                peers_in_dispute_requests.add(pid)

    # Score candidates
    scored: list[tuple[float, str, str]] = []   # (score, tiebreak, peer_id)
    for pid, rep in block_closer_reps.items():
        proximity = 1.0 if pid in peers_in_dispute_requests else 0.0
        score = rep * (1.0 - proximity)
        tiebreak = _hl.sha256(f'{request_id}:{pid}'.encode()).hexdigest()
        scored.append((score, tiebreak, pid))

    scored.sort(key=lambda x: (-x[0], x[1]))   # desc score, asc tiebreak
    selected = [pid for _, _, pid in scored[:n]]

    if selected:
        exchange.append_audit_row({
            'kind': 'WORK_ARBITRATOR_ASSIGNED',
            'request_id': request_id,
            'arbitrators': selected,
            'n_requested': n,
            'at_unix': time.time(),
            'at': _now_iso(),
        })
    return selected


# ── Multi-sig peer review quorum ──────────────────────────────────────────────

def submit_peer_review(
    exchange,
    request_id: str,
    reviewer_id: str,
    approved: bool,
    root: str | None = None,
) -> None:
    """Submit an independent peer review for delivery quorum verification.

    Reviewer must:
    - Be a neutral block-closer (not a dispute party)
    - Not have already reviewed this request

    When VERIFICATION_QUORUM independent reviews accumulate with a majority
    verdict, escrow_state() reports quorum=True/False and escrow_release can
    proceed without requester involvement — removing the honest-requester
    assumption and enabling trustless delivery verification.
    """
    st = escrow_state(request_id, exchange)
    if st['state'] != 'VERIFICATION':
        raise ValueError(f'Peer review only valid in VERIFICATION state (got {st["state"]})')

    # Collect dispute party IDs
    dispute_parties: set[str] = set()
    if st['request'].get('requester_id'):
        dispute_parties.add(st['request']['requester_id'])
    for bid in st['accepted_bids']:
        if bid.get('bidder_id'):
            dispute_parties.add(bid['bidder_id'])
    for d in st['deliveries']:
        if d.get('hired_peer_id'):
            dispute_parties.add(d['hired_peer_id'])

    if reviewer_id in dispute_parties:
        raise ValueError(
            f'{reviewer_id!r} is a dispute party and cannot review this request'
        )

    # Duplicate review guard
    already = [r for r in st['peer_reviews'] if r.get('reviewer_id') == reviewer_id]
    if already:
        raise ValueError(f'{reviewer_id!r} has already submitted a review for {request_id!r}')

    exchange.append_audit_row({
        'kind': 'WORK_PEER_REVIEW',
        'request_id': request_id,
        'reviewer_id': reviewer_id,
        'approved': approved,
        'at_unix': time.time(),
        'at': _now_iso(),
    })


def quorum_reached(request_id: str, exchange) -> bool | None:
    """Return quorum verdict for a work request.

    Returns:
      True   — majority approved (escrow can release)
      False  — majority rejected (dispute should be filed)
      None   — quorum not yet reached (< VERIFICATION_QUORUM reviews)
    """
    st = escrow_state(request_id, exchange)
    return st.get('quorum')


def quorum_auto_release(request_id: str, exchange, root: str | None = None) -> bool:
    """Auto-release escrow when quorum=True, or fall back to requester verify on quorum_fallback.

    Returns True if release was triggered, False if nothing happened.
    Symmetric counterpart to verify_delivery() for trustless quorum-driven release.
    """
    st = escrow_state(request_id, exchange)
    verdict = st.get('quorum')
    fallback = st.get('quorum_fallback', False)

    if verdict is True and root is not None and st['state'] == 'VERIFICATION':
        from . import credit_ledger as _cl
        hired = [(r['bidder_id'], float(r.get('budget_units', 0)))
                 for r in st['accepted_bids']]
        if hired:
            total_budget = sum(amt for _, amt in hired)
            shares = equity_split_budget(hired, total_budget)
            _cl.escrow_release(root, request_id, shares)
        exchange.append_audit_row({
            'kind': 'WORK_VERIFIED',
            'request_id': request_id,
            'requester_id': '__quorum__',
            'approved': True,
            'auto_released': False,
            'quorum_released': True,
            'at_unix': time.time(),
            'at': _now_iso(),
        })
        return True

    if fallback and verdict is None:
        # Network is too small — quorum is structurally impossible. Signal caller
        # that requester-only verification is the only viable path.
        exchange.append_audit_row({
            'kind': 'WORK_QUORUM_FALLBACK',
            'request_id': request_id,
            'reason': 'insufficient_neutral_peers',
            'at_unix': time.time(),
            'at': _now_iso(),
        })
        return False

    return False


# ── Autonomous task decomposition ─────────────────────────────────────────────

def auto_decompose_request(
    exchange,
    requester_id: str,
    spec: str,
    budget_units: int,
    complexity: float,
    root: str | None = None,
    min_combined_rep: float = 0.3,
) -> list[str]:
    """Recursively decompose a high-complexity request into parallel sub-requests.

    When complexity ≥ DECOMPOSE_THRESHOLD (0.7), splits the task into two halves
    with halved complexity and budget split proportionally. Recursion stops when
    complexity < DECOMPOSE_MIN_BP (0.25) or budget would fall below escrow floor.

    Returns list of created request_ids (leaf nodes — no further decomposition).
    """
    from . import credit_ledger as _cl
    floor = _cl.consensus_escrow_floor(exchange)

    if complexity < DECOMPOSE_THRESHOLD or budget_units // 2 < floor:
        rid = create_work_request(
            exchange, requester_id, spec, budget_units,
            min_combined_rep=min_combined_rep,
            complexity=complexity, root=root,
        )
        return [rid]

    half_complexity = max(DECOMPOSE_MIN_BP, complexity / 2.0)
    half_budget = budget_units // 2
    left = auto_decompose_request(
        exchange, requester_id, f'{spec} [part-A]', half_budget,
        half_complexity, root, min_combined_rep,
    )
    right = auto_decompose_request(
        exchange, requester_id, f'{spec} [part-B]', budget_units - half_budget,
        half_complexity, root, min_combined_rep,
    )
    return left + right


# ── LLM-as-peer / executor node registration ──────────────────────────────────

def register_executor_peer(
    exchange,
    executor_id: str,
    model_id: str,
    capabilities: list[str] | None = None,
    initial_rep: float = 0.3,
) -> None:
    """Register an LLM executor as a first-class peer node in the work market.

    Executor peers can bid on work requests, earn rep through approved deliveries,
    and lose rep through rejected deliveries — identical incentive structure to
    human peers. initial_rep seeds the executor's combined_rep before any history.
    """
    existing = [r for r in _request_rows(exchange)
                if r.get('kind') == EXECUTOR_PEER_KIND and r.get('executor_id') == executor_id]
    if existing:
        return   # idempotent

    exchange.append_audit_row({
        'kind': EXECUTOR_PEER_KIND,
        'executor_id': executor_id,
        'model_id': model_id,
        'capabilities': capabilities or [],
        'initial_rep': initial_rep,
        'at_unix': time.time(),
        'at': _now_iso(),
    })


def executor_peer_combined_rep(executor_id: str, exchange) -> float:
    """Return current combined_rep for an executor peer derived from delivery history.

    Falls back to initial_rep if no delivery history exists yet.
    """
    rows = _request_rows(exchange)
    reg = next((r for r in rows if r.get('kind') == EXECUTOR_PEER_KIND
                and r.get('executor_id') == executor_id), None)
    if reg is None:
        return 0.0

    initial = float(reg.get('initial_rep', 0.3))
    deliveries = [r for r in rows if r.get('kind') == 'WORK_DELIVERY'
                  and r.get('hired_peer_id') == executor_id]
    if not deliveries:
        return initial

    # Find verified outcomes for executor deliveries
    approved = rejected = 0
    for d in deliveries:
        rid = d.get('request_id', '')
        verified = [r for r in rows if r.get('kind') == 'WORK_VERIFIED'
                    and r.get('request_id') == rid]
        for v in verified:
            if v.get('approved'):
                approved += 1
            else:
                rejected += 1

    total = approved + rejected
    if total == 0:
        return initial
    from . import credit_ledger as _cl
    delivery_w = _cl.wilson_lower(approved, total)
    quality_w  = _cl.wilson_lower(approved, total)
    return _cl.combined_rep_score(delivery_w, quality_w, total_accepted=approved)


# ── On-chain audit finality (rolling SHA-256 hash chain) ──────────────────────

def audit_chain_root(exchange) -> str:
    """Compute rolling SHA-256 hash of all work-market audit rows in chronological order.

    Each row is hashed as: sha256(prev_hash + canonical_json(row)).
    Returns the final hex digest — a merkle-like chain root for tamper-evident finality.
    Deterministic across identical row sequences; changes on any mutation.
    """
    import json as _json
    rows = _request_rows(exchange)
    rows_sorted = sorted(rows, key=lambda r: float(r.get('at_unix', 0)))
    h = _hashlib.sha256(b'urace-audit-genesis').hexdigest()
    for row in rows_sorted:
        payload = _json.dumps(row, sort_keys=True, separators=(',', ':'))
        h = _hashlib.sha256(f'{h}:{payload}'.encode()).hexdigest()
    return h
