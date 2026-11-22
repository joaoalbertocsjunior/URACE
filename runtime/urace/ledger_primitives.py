"""Ledger primitives — storage access, unit conversions, core CRUD."""
import math
import time
from pathlib import Path

from .p2p_constants import DECIMALS, UNIT, CHAIN_DECIMALS, CHAIN_UNIT, CHAIN_SCALE  # noqa: F401
from .ledger_adapter import LedgerAdapter  # noqa: F401

SCHEMA = 'urace-credit-ledger-v1'
BASELINE_GRANT = 3  # requests every new peer can make before earning

# 8-decimal precision — imported from p2p_constants; kept as module-level
# aliases for backward compatibility with existing callers.
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

# CHAIN_DECIMALS, CHAIN_UNIT, CHAIN_SCALE imported from p2p_constants above.

# Network supply stabilizer constants
TARGET_SUPPLY_RATIO     = 0.5   # target: 50% of theoretical max per peer
NETWORK_FACTOR_LOW      = 0.8
NETWORK_FACTOR_HIGH     = 1.2

# ── Earned vs. traded reputation ─────────────────────────────────────────────
REP_SOURCE_WORK  = 'work'    # earned via delivery, quality, adoption — counts for earned_rep
REP_SOURCE_TRADE = 'trade'   # purchased / traded — market_rep only, never earned_rep

# ── Consensus weights — event-count based, fully decoupled from UCR amounts ───
CONSENSUS_WEIGHTS: dict[str, float] = {
    # Tier 1 — PoQ-verified quality, direct output signal
    'earn':                    1.00,
    'delivery_fee':            0.90,
    'challenge_bounty':        0.90,
    # Tier 2 — Network service
    'seal_reward':             0.80,
    'relay_reward':            0.80,
    'bootstrap_reward':        0.75,
    'llm_peer_reward':         0.70,
    # Tier 3 — Referral / composition
    'composition_referral':    0.60,
    'provenance_compensation': 0.60,
    # Tier 4 — Borrow / adoption
    'borrow_earn':             0.40,
    'escrow_custody_earned':   0.30,
    # Stake returns — not earn signals, excluded
    'mint_stake_released':     0.00,
    'challenge_stake_returned': 0.00,
    # Trade-source only — never earned consensus
    'asset_royalty':           0.00,
    'purchase_receive':        0.00,
    'cartel_penalty':          0.00,
    'decay':                   0.00,
    # Locked grant — usable as stake only
    'baseline_grant_locked':   0.00,
}

# Backward-compat alias
EARN_WEIGHTS = CONSENSUS_WEIGHTS

# Direction constant for provisional/locked baseline grant
BASELINE_GRANT_LOCKED_DIRECTION = 'baseline_grant_locked'

# ── AI underpricing defenses ──────────────────────────────────────────────────
EARN_JITTER_FRAC   = 0.05   # ±5% uniform noise on final earn
BORROW_JITTER_FRAC = 0.03   # ±3% on borrow cost
ESCROW_JITTER_FRAC = 0.04   # ±4% — between earn ±5% and borrow ±3%

# Distribution fee constants
DISTRIBUTION_FEE_MIN = 0.05
DISTRIBUTION_FEE_MAX = 0.30
DISTRIBUTION_FEE_DEFAULT = 0.10

# Approved gate constants
_APPROVED_FLOOR_BASE  = 0.50
_APPROVED_FLOOR_MIN   = 0.05
_APPROVED_FLOOR_DECAY = 7.0

# Escrow virtual peer
_ESCROW_PEER = '__escrow__'

# Dynamic split consensus constants
_SPLIT_REQUESTER_FLOOR = 0.50
_SPLIT_HIRED_FLOOR     = 0.20
_SPLIT_DEFAULT         = (0.60, 0.40)
_SPLIT_MIN_SAMPLES     = 5
_SPLIT_TTL_SECONDS     = 60


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


def earn_units(root, peer_id, units: int, reason, bundle_id=None, metadata: dict | None = None,
               rep_source: str = REP_SOURCE_WORK, exchange: LedgerAdapter | None = None):
    """Credit peer_id with units base units earned from an accepted qualification.

    Uses late-bound imports via sys.modules so that mock.patch.object(credit_ledger, ...)
    is respected at call time (not bound at import time).
    """
    import sys as _sys
    _cl = _sys.modules.get('urace.credit_ledger')
    _velocity_multiplier = _cl._velocity_multiplier if _cl else None
    _peer_held_features_fn = _cl._peer_held_features if _cl else None
    _mint_per_adoption = _cl.mint_per_adoption if _cl else None
    _peer_cap_units = _cl.peer_cap_units if _cl else None

    # Fallback: direct imports (when credit_ledger hub not yet loaded)
    if _velocity_multiplier is None:
        from .ledger_reputation import _velocity_multiplier
    if _peer_held_features_fn is None:
        from .ledger_reputation import _peer_held_features as _peer_held_features_fn
    if _mint_per_adoption is None:
        from .ledger_economics import mint_per_adoption as _mint_per_adoption
    if _peer_cap_units is None:
        from .ledger_reputation import peer_cap_units as _peer_cap_units

    if not isinstance(units, int) or units <= 0:
        raise ValueError('Positive int units required to earn credits')
    adjusted_units = int(units * _velocity_multiplier(root))
    # If adoption metadata provided, apply mint_per_adoption formula
    if metadata and 'adoption_rank' in metadata:
        minted = _mint_per_adoption(
            loc=metadata.get('loc', 0),
            dependency_count=metadata.get('dependency_count', 0),
            test_count=metadata.get('test_count', 0),
            adopter_trust=metadata.get('adopter_trust', 0.5),
            adoption_rank=metadata['adoption_rank'],
            network_size=metadata.get('network_size', 1),
            estimated_network_size=metadata.get('estimated_network_size', metadata.get('network_size', 1)),
            total_network_supply=metadata.get('total_network_supply', 0),
            epochs_elapsed=metadata.get('epochs_elapsed', 0),
        )
        if minted == 0:
            return  # saturated — no earn
        units = minted  # override the passed-in units with the formula result
        adjusted_units = int(units * _velocity_multiplier(root))
    # Novelty gate: re-borrow of same feature_id earns 50%.
    if reason and 'borrow' in str(reason).lower():
        feature_id = (metadata or {}).get('feature_id')
        if feature_id and feature_id in _peer_held_features_fn(root, peer_id):
            adjusted_units = adjusted_units // 2
    # Apply trust-dynamic per-peer cap
    cap = _peer_cap_units(root, peer_id, exchange=exchange)
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
    from .event_bus import _BUS as _eb
    _eb.publish('ledger.earned', peer_id=peer_id, units=adjusted_units, reason=reason)


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
    from .event_bus import _BUS as _eb
    _eb.publish('ledger.spent', peer_id=peer_id, units=units, reason=reason)


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


def earned_balance(root, peer_id: str) -> int:
    """Credits earned via REP_SOURCE_WORK only."""
    rows = _credit_rows(root, peer_id)
    total = 0
    for r in rows:
        src = r.get('rep_source', REP_SOURCE_WORK)
        total += _row_units(r) if src == REP_SOURCE_WORK else 0
    return max(0, total)


def locked_grant_balance(root, peer_id: str) -> int:
    """Return the still-locked portion of the baseline grant for peer_id."""
    rows = _credit_rows(root, peer_id)
    unlocked = sum(
        abs(_row_units(r)) for r in rows
        if r.get('direction') == 'baseline_grant_unlock'
    )
    return max(0, BASELINE_GRANT_UNITS - unlocked)


def unlock_grant(root, peer_id: str, delivery_earn_units: int) -> dict:
    """Unlock 1 UCR of the baseline grant after a successful delivery acceptance."""
    import time as _t
    still_locked = locked_grant_balance(root, peer_id)
    if still_locked <= 0:
        return {'unlocked': 0, 'remaining_locked': 0}
    unlock_amount = min(UNIT, still_locked)
    _ledger(root).append('CREDIT_DELTA', {
        'peer': peer_id,
        'delta_units': 0,
        'direction': 'baseline_grant_unlock',
        'rep_source': REP_SOURCE_WORK,
        'unlock_units': unlock_amount,
        'triggered_by_delivery_earn': delivery_earn_units,
        'at_unix': _t.time(),
    })
    return {'unlocked': unlock_amount, 'remaining_locked': max(0, still_locked - unlock_amount)}


def escrow_lock(root, requester_id: str, request_id: str, amount: int) -> None:
    """Lock amount base units from requester into escrow."""
    spend_units(root, requester_id, amount, f'escrow-lock:{request_id}', bundle_id=request_id)


def escrow_release(
    root,
    request_id: str,
    splits: list[tuple[str, int]],
) -> None:
    """Release escrowed credits to hired node(s)."""
    for peer_id, units in splits:
        if units > 0:
            earn_units(root, peer_id, units, f'escrow-release:{request_id}',
                       bundle_id=request_id)


def escrow_refund(root, request_id: str, requester_id: str, amount: int) -> None:
    """Refund escrowed credits to requester."""
    if amount <= 0:
        return
    rows = _credit_rows(root, requester_id)
    already = any(
        r.get('direction') in ('earn',) and r.get('reason') == f'escrow-refund:{request_id}'
        for r in rows
    )
    if already:
        return
    earn_units(root, requester_id, amount, f'escrow-refund:{request_id}',
               bundle_id=request_id)
