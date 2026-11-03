"""Equity auto-trading: configurable threshold-driven buy/sell automation.

Equity listings allow sellers to advertise a sell intent publicly. Buyers — human
or automated — can fill listings. The auto-trade engine runs on-demand against the
caller's configured thresholds.

Audit row kinds:
  EQUITY_LISTING           — seller lists bp at an ask_price
  EQUITY_LISTING_FILLED    — buyer fills a listing (calls sell_equity internally)
  EQUITY_LISTING_CANCELLED — seller cancels an open listing

Auto-trade config (per-peer, stored in exchange root):
  {
    "auto_buy": {
      "enabled": false,
      "min_quality_wilson": 0.65,       // skip features below this quality
      "min_adoption_count": 5,          // skip features with fewer distinct adopters
      "max_price_multiplier": 1.0,      // skip listings priced > base_borrow × mult
      "max_bp_per_feature": 2000,       // anti-concentration: cap new purchase
      "max_spend_per_run_units": 0      // 0 = unlimited; per auto-buy run budget
    },
    "auto_sell": {
      "enabled": false,
      "min_return_multiplier": 2.0,     // sell when market_price ≥ cost × this
      "bp_to_sell_per_trigger": 1000,   // bp to list per qualifying feature
      "min_hold_bp_to_trigger": 500     // only act if currently holding ≥ this
    }
  }

All thresholds are user-configurable. Sane defaults resist both panic-selling and
reckless accumulation.
"""
from __future__ import annotations
import hashlib
import json
import time
from pathlib import Path

SCHEMA = 'urace-equity-auto-trade-v1'

LISTING_EXPIRY_SECONDS = 30 * 86400   # listings expire after 30 days
MAX_EQUITY_BP_PER_FEATURE = 10_000    # total network-wide bp cap per feature (100% in bp)
WASH_TRADE_WINDOW_SECONDS = 86400     # 24h window for wash-trading detection
PRICE_MOMENTUM_MAX_MULTIPLIER = 1.5   # ask cannot exceed 1.5× 7-day median of recent sales
PRICE_MOMENTUM_WINDOW_SECONDS = 7 * 86400

DEFAULT_CONFIG: dict = {
    'auto_buy': {
        'enabled': False,
        'min_quality_wilson': 0.65,
        'min_adoption_count': 5,
        'max_price_multiplier': 1.0,
        'max_bp_per_feature': 2000,
        'max_spend_per_run_units': 0,
        # Depletion guards — protect against buying into saturated features
        'max_adoption_rate': 0.70,        # skip if > 70% of network already adopted
        'min_supply_pressure': 0.25,      # skip if supply_pressure < 0.25 (near-saturated)
        'min_remaining_adopters': 5,      # skip if < 5 new adopters possible
        # Lucrativity guard — projected earnings must exceed threshold
        'min_lucrativity_score': 0.10,    # skip if projected earnings score < 0.10
        'lucrativity_window_days': 30.0,  # projection horizon in days
    },
    'auto_sell': {
        'enabled': False,
        'min_return_multiplier': 2.0,
        'bp_to_sell_per_trigger': 1000,
        'min_hold_bp_to_trigger': 500,
        # Trigger early sell when depletion is detected
        'sell_on_near_depleted': True,    # auto-list when feature is NEAR_DEPLETED
        'sell_on_slowing': False,         # auto-list when feature is SLOWING (earlier exit)
    },
    'auto_mint': {
        'enabled': False,                 # opt-in: auto-mint completed minimal work to P2P
        'max_complexity_threshold': 0.5,  # only mint features with complexity < 0.5
        'min_quality_score': 0.6,         # skip low-quality work products
    },
}

# ── Feature depletion status ──────────────────────────────────────────────────

DEPLETION_STATES = ('HEALTHY', 'SLOWING', 'NEAR_DEPLETED', 'DEPLETED')


def feature_depletion_status(
    feature_id: str,
    exchange,
    estimated_network_size: int = 1,
    adoption_count: int | None = None,
) -> dict:
    """Evaluate how close a feature is to borrow-revenue exhaustion.

    A feature earns revenue on each borrow. Once most of the network has
    adopted it, new borrows approach zero and the equity value collapses.
    Supply pressure (quadratic decay) is the leading indicator.

    Returns:
        {
          'state': 'HEALTHY'|'SLOWING'|'NEAR_DEPLETED'|'DEPLETED',
          'adoption_rate': float,           # adopted_peers / network_size
          'supply_pressure': float,         # from supply_pressure_multiplier()
          'remaining_adopters': int,        # estimated new adopters possible
          'estimated_remaining_revenue_units': int,  # per bp held
          'notes': str,
        }
    """
    from . import credit_ledger as _cl

    # Derive distinct adoption count from exchange if not provided
    if adoption_count is None:
        try:
            rows = exchange.audit_rows()
        except Exception:
            rows = []
        adopter_ids: set[str] = set()
        for r in rows:
            if r.get('kind') == 'CREDIT_DELTA' and r.get('direction') == 'spend':
                if r.get('feature_id') == feature_id:
                    pid = r.get('peer', '')
                    if pid:
                        adopter_ids.add(pid)
        adoption_count = len(adopter_ids)

    net = max(1, estimated_network_size)
    adoption_rate = min(1.0, adoption_count / net)
    remaining_adopters = max(0, net - adoption_count)

    # Feature total spend (supply pressure input)
    try:
        rows_for_supply = exchange.audit_rows()
    except Exception:
        rows_for_supply = []
    feature_spend = sum(
        abs(int(r.get('delta_units', 0) or 0))
        for r in rows_for_supply
        if r.get('kind') == 'CREDIT_DELTA' and r.get('direction') == 'spend'
        and r.get('feature_id') == feature_id
    )

    supply_pressure = _cl.supply_pressure_multiplier(feature_spend, net)
    base_borrow = _cl.apply_borrow_cost()
    mint_per = _cl.UNIT // 100   # 0.01 tokens per adoption (approximate)

    # Revenue per bp = (remaining adopters × mint_per × bp_fraction)
    # Report for 1 bp (caller scales by actual holdings)
    rev_per_bp = int(remaining_adopters * mint_per * supply_pressure / _cl.EQUITY_TOTAL_BP
                     if hasattr(_cl, 'EQUITY_TOTAL_BP') else
                     remaining_adopters * mint_per * supply_pressure / 10_000)

    if adoption_rate > 0.95 or supply_pressure < 0.05:
        state = 'DEPLETED'
        notes = f'{adoption_rate:.0%} adopted, supply_pressure={supply_pressure:.3f}. No meaningful borrow revenue remains.'
    elif adoption_rate > 0.80 or supply_pressure < 0.20:
        state = 'NEAR_DEPLETED'
        notes = f'{adoption_rate:.0%} adopted, supply_pressure={supply_pressure:.3f}. Revenue declining rapidly; consider selling.'
    elif adoption_rate > 0.50 or supply_pressure < 0.50:
        state = 'SLOWING'
        notes = f'{adoption_rate:.0%} adopted, supply_pressure={supply_pressure:.3f}. Growth slowing; peak revenue likely passed.'
    else:
        state = 'HEALTHY'
        notes = f'{adoption_rate:.0%} adopted, supply_pressure={supply_pressure:.3f}. Significant borrow revenue potential remains.'

    from . import credit_ledger as _cl2
    eq_total = 10_000  # EQUITY_TOTAL_BP

    return {
        'feature_id': feature_id,
        'state': state,
        'listable': state != 'DEPLETED',   # DEPLETED features cannot be listed for sale
        'adoption_rate': round(adoption_rate, 4),
        'adoption_count': adoption_count,
        'estimated_network_size': net,
        'supply_pressure': round(supply_pressure, 4),
        'remaining_adopters': remaining_adopters,
        'estimated_remaining_revenue_per_bp_units': rev_per_bp,
        'notes': notes,
    }


def lucrativity_assessment(
    feature_id: str,
    exchange,
    window_days: float = 30.0,
    bp_held: int = 10_000,
    estimated_network_size: int = 1,
    competing_features_count: int | None = None,
) -> dict:
    """Project earnings from a held equity stake over a future time window.

    Considers:
      - adoption_velocity: average new adopters per day (last 30 days of history)
      - supply_pressure decay: as adoption_rate rises, each new borrow earns less
      - bp_held fraction of total equity

    Returns:
        {
          'feature_id': str,
          'depletion': dict,
          'window_days': float,
          'bp_held': int,
          'adoption_velocity_per_day': float,
          'projected_new_adopters': int,
          'dilution_factor': float,       # market-share dilution from competing features
          'projected_revenue_units': int,
          'projected_revenue_tokens': float,
          'lucrativity_score': float,     # 0.0–1.0; 1.0 = max projected return
          'verdict': str,                 # 'HIGH'|'MEDIUM'|'LOW'|'EXHAUSTED'
        }
    """
    from . import credit_ledger as _cl

    dep = feature_depletion_status(feature_id, exchange,
                                   estimated_network_size=estimated_network_size)

    # Compute adoption velocity: count distinct adopters in last 30 days
    history_window = 30 * 86400
    cutoff = time.time() - history_window
    try:
        rows = exchange.audit_rows()
    except Exception:
        rows = []
    recent_adopters: set[str] = set()
    for r in rows:
        if (r.get('kind') == 'CREDIT_DELTA' and r.get('direction') == 'spend'
                and r.get('feature_id') == feature_id
                and float(r.get('at_unix', 0)) > cutoff):
            pid = r.get('peer', '')
            if pid:
                recent_adopters.add(pid)
    velocity = len(recent_adopters) / 30.0   # adopters per day

    projected_new = min(dep['remaining_adopters'], int(velocity * window_days))

    # Project revenue: each new adopter generates mint_per_adoption × bp_fraction × supply_pressure
    # Supply pressure is estimated at midpoint of adoption window
    mid_adoption_count = dep['adoption_count'] + projected_new // 2
    mid_rate = min(1.0, mid_adoption_count / estimated_network_size)
    supply_at_mid = _cl.supply_pressure_multiplier(
        int(mid_rate * estimated_network_size * _cl.apply_borrow_cost()),
        estimated_network_size,
    )
    # Dilution factor: as more features enter the ecosystem, adoption budget splits.
    # Each additional competing feature reduces velocity by a small fraction.
    # Auto-count active features from exchange when not provided.
    if competing_features_count is None:
        try:
            all_rows = exchange.audit_rows()
        except Exception:
            all_rows = []
        competing_features_count = len({
            r.get('feature_id', '')
            for r in all_rows
            if r.get('kind') in ('EQUITY_GRANT', 'WORK_REQUEST') and r.get('feature_id', '') != feature_id
        } - {''})

    # Dilution: each additional feature captures ~0.5% of adoption budget from all others.
    # Formula: 1 / (1 + n_competing × 0.005) — soft logarithmic cap.
    # 10 competitors → 0.95×, 100 → 0.67×, 200 → 0.50× reduction in projected velocity.
    dilution_factor = 1.0 / (1.0 + competing_features_count * 0.005)
    adjusted_velocity = velocity * dilution_factor
    projected_new = min(dep['remaining_adopters'], int(adjusted_velocity * window_days))

    # Use consensus-observed mint rate rather than hardcoded constant
    from . import ledger_compaction as _lcomp
    mint_per = _lcomp.consensus_mint_per_adoption(exchange)
    bp_fraction = bp_held / 10_000
    projected_revenue = int(projected_new * mint_per * bp_fraction * supply_at_mid)

    # Lucrativity score: normalize against theoretical max (undiluted, full remaining adopters)
    theoretical_max = int(dep['remaining_adopters'] * mint_per * bp_fraction)
    score = (projected_revenue / theoretical_max) if theoretical_max > 0 else 0.0
    score = min(1.0, score)

    if dep['state'] == 'DEPLETED' or projected_new == 0:
        verdict = 'EXHAUSTED'
    elif score >= 0.5:
        verdict = 'HIGH'
    elif score >= 0.2:
        verdict = 'MEDIUM'
    else:
        verdict = 'LOW'

    return {
        'feature_id': feature_id,
        'depletion': dep,
        'window_days': window_days,
        'bp_held': bp_held,
        'adoption_velocity_per_day': round(velocity, 4),
        'competing_features_count': competing_features_count,
        'dilution_factor': round(dilution_factor, 4),
        'projected_new_adopters': projected_new,
        'projected_revenue_units': projected_revenue,
        'projected_revenue_tokens': round(projected_revenue / _cl.UNIT, 8),
        'lucrativity_score': round(score, 4),
        'verdict': verdict,
    }

# ── Auto-config presets ────────────────────────────────────────────────────────
AUTO_CONFIG_PRESETS = {
    "conservative": {
        "auto_buy": {
            "min_quality_wilson": 0.75,
            "min_adoption_count": 10,
            "max_price_multiplier": 0.9,
            "max_bp_per_feature": 1000,
            "max_spend_per_run_units": 0,
            "max_adoption_rate": 0.60,
            "min_supply_pressure": 0.30,
            "min_remaining_adopters": 10,
            "min_lucrativity_score": 0.20,
        },
        "auto_sell": {
            "min_return_multiplier": 3.0,
            "bp_to_sell_per_trigger": 500,
            "min_hold_bp_to_trigger": 1000,
        },
        "description": "Low risk: high quality gate, low spend, high return target. Longer ROI but lower loss risk.",
        "roi_preference": "long_term",
    },
    "balanced": {
        "auto_buy": {
            "min_quality_wilson": 0.65,
            "min_adoption_count": 5,
            "max_price_multiplier": 1.0,
            "max_bp_per_feature": 2000,
            "max_spend_per_run_units": 0,
            "max_adoption_rate": 0.70,
            "min_supply_pressure": 0.25,
            "min_remaining_adopters": 5,
            "min_lucrativity_score": 0.10,
        },
        "auto_sell": {
            "min_return_multiplier": 2.0,
            "bp_to_sell_per_trigger": 1000,
            "min_hold_bp_to_trigger": 500,
        },
        "description": "Balanced: moderate quality gate, medium spend, fair return. Good for most users.",
        "roi_preference": "medium_term",
    },
    "aggressive": {
        "auto_buy": {
            "min_quality_wilson": 0.50,
            "min_adoption_count": 3,
            "max_price_multiplier": 1.2,
            "max_bp_per_feature": 3000,
            "max_spend_per_run_units": 0,
            "max_adoption_rate": 0.80,
            "min_supply_pressure": 0.15,
            "min_remaining_adopters": 3,
            "min_lucrativity_score": 0.05,
        },
        "auto_sell": {
            "min_return_multiplier": 1.5,
            "bp_to_sell_per_trigger": 2000,
            "min_hold_bp_to_trigger": 250,
        },
        "description": "High activity: lower quality gate, higher spend, faster turnover. Higher risk/reward.",
        "roi_preference": "short_term",
    },
}


def apply_preset(config: dict, preset_name: str) -> dict:
    """Apply a named preset to the auto-trade config dict. Returns updated config."""
    preset = AUTO_CONFIG_PRESETS.get(preset_name)
    if not preset:
        raise ValueError(f"Unknown preset: {preset_name!r}. Available: {list(AUTO_CONFIG_PRESETS)}")
    import copy
    result = copy.deepcopy(config)
    for section in ("auto_buy", "auto_sell"):
        if section in preset:
            result.setdefault(section, {}).update(preset[section])
    return result


def auto_tune_config(exchange, base_config: dict | None = None) -> dict:
    """Derive optimal auto-trade settings from observed network conditions.

    Adjusts quality thresholds, adoption count gate, and return multiplier
    based on: median feature quality, network adoption rate, available supply.
    Returns a config dict with optimal values for current network state.
    """
    import copy
    import math
    cfg = copy.deepcopy(base_config or load_config(str(exchange.root)))
    rows = []
    try:
        rows = exchange.audit_rows()
    except Exception:
        pass
    # Measure network adoption rate
    grants = [r for r in rows if r.get('kind') == 'EQUITY_GRANT']
    sells = [r for r in rows if r.get('kind') == 'EQUITY_SELL']
    n_features = max(1, len(grants))
    adoption_rate = min(0.95, len(sells) / max(1, n_features * 100))  # per-feature adoption proxy
    # Adjust buy gate: loosen when adoption rate is low (market thin), tighten when high
    quality_adj = max(0.50, 0.65 - (adoption_rate - 0.10) * 0.30)
    count_adj = max(3, int(5 * (1 + adoption_rate)))
    cfg.setdefault('auto_buy', {})['min_quality_wilson'] = round(quality_adj, 2)
    cfg.setdefault('auto_buy', {})['min_adoption_count'] = count_adj
    # Adjust return multiplier: higher when market thin (more upside), lower when liquid
    sell_mult = max(1.5, 2.0 + (1 - adoption_rate) * 1.5)
    cfg.setdefault('auto_sell', {})['min_return_multiplier'] = round(sell_mult, 2)
    cfg['_auto_tuned'] = True
    cfg['_tune_basis'] = {'n_features': n_features, 'adoption_proxy': round(adoption_rate, 4)}
    return cfg


_CONFIG_FILE = 'equity-auto-trade-config.json'


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


# ── Config persistence ────────────────────────────────────────────────────────

def load_config(root: str) -> dict:
    """Load auto-trade config from root. Returns DEFAULT_CONFIG if not set."""
    path = Path(root) / _CONFIG_FILE
    if not path.exists():
        return json.loads(json.dumps(DEFAULT_CONFIG))   # deep copy
    try:
        data = json.loads(path.read_text())
        # Merge with defaults so new keys appear transparently
        merged = json.loads(json.dumps(DEFAULT_CONFIG))
        for section in ('auto_buy', 'auto_sell'):
            if section in data:
                merged[section].update(data[section])
        return merged
    except (OSError, ValueError):
        return json.loads(json.dumps(DEFAULT_CONFIG))


def save_config(root: str, config: dict) -> None:
    """Persist auto-trade config to root."""
    path = Path(root) / _CONFIG_FILE
    path.write_text(json.dumps(config, indent=2, sort_keys=True))


def update_config(root: str, section: str, **kwargs) -> dict:
    """Update specific keys in a config section and persist.

    section: 'auto_buy' or 'auto_sell'
    kwargs: key=value pairs to update (only recognised keys are accepted)
    """
    cfg = load_config(root)
    if section not in cfg:
        raise ValueError(f'Unknown config section {section!r}')
    for k, v in kwargs.items():
        if k not in cfg[section]:
            raise ValueError(f'Unknown config key {k!r} in section {section!r}')
        cfg[section][k] = v
    save_config(root, cfg)
    return cfg


# ── Listing integrity guards ──────────────────────────────────────────────────

def _check_wash_trading(exchange, seller_id: str, feature_id: str) -> None:
    """Raise ValueError if seller bought AND sold the same feature within 24 hours."""
    try:
        rows = exchange.audit_rows()
    except Exception:
        return
    cutoff = time.time() - WASH_TRADE_WINDOW_SECONDS
    bought = any(
        r.get('kind') in ('EQUITY_LISTING_FILLED', 'EQUITY_SELL')
        and r.get('buyer_id') == seller_id
        and r.get('feature_id') == feature_id
        and float(r.get('at_unix', 0)) > cutoff
        for r in rows
    )
    sold = any(
        r.get('kind') in ('EQUITY_LISTING', 'EQUITY_SELL')
        and r.get('seller_id') == seller_id
        and r.get('feature_id') == feature_id
        and float(r.get('at_unix', 0)) > cutoff
        for r in rows
    )
    if bought and sold:
        raise ValueError(
            f'Wash trading detected: {seller_id!r} bought and sold {feature_id!r} '
            f'within {WASH_TRADE_WINDOW_SECONDS // 3600}h. '
            'Round-trip trading within 24h is not permitted.'
        )


def _validate_ask_price_momentum(exchange, feature_id: str, ask_price_units: int) -> None:
    """Raise ValueError if ask_price exceeds 1.5× 7-day median of recent filled sales."""
    try:
        rows = exchange.audit_rows()
    except Exception:
        return
    cutoff = time.time() - PRICE_MOMENTUM_WINDOW_SECONDS
    recent_prices = sorted(
        int(r.get('price_units', 0))
        for r in rows
        if r.get('kind') == 'EQUITY_SELL'
        and r.get('feature_id') == feature_id
        and float(r.get('at_unix', 0)) > cutoff
        and int(r.get('price_units', 0)) > 0
    )
    if not recent_prices:
        return
    n = len(recent_prices)
    median = recent_prices[n // 2] if n % 2 else (recent_prices[n // 2 - 1] + recent_prices[n // 2]) // 2
    ceiling = int(median * PRICE_MOMENTUM_MAX_MULTIPLIER)
    if ask_price_units > ceiling:
        raise ValueError(
            f'ask_price_units {ask_price_units} exceeds price-momentum ceiling {ceiling} '
            f'(7-day median {median} × {PRICE_MOMENTUM_MAX_MULTIPLIER}). '
            'Sudden price spikes above recent market trend are not allowed.'
        )


# ── Equity listings ───────────────────────────────────────────────────────────

def list_for_sale(
    exchange,
    feature_id: str,
    seller_id: str,
    basis_points: int,
    ask_price_units: int,
    estimated_network_size: int = 1,
) -> str:
    """Broadcast a sell intent for basis_points of feature_id at ask_price_units.

    The listing is non-binding: it does not lock bp. When a buyer fills the
    listing, sell_equity() is called to atomically transfer ownership.

    Raises ValueError if:
      - seller doesn't hold enough bp
      - feature is DEPLETED (non-listable: no borrow revenue remains, listing is
        misleading to buyers — direct zero-price sell_equity() still allowed for exit)

    Returns listing_id.
    """
    from . import feature_equity as _fe

    # Auto-detect network size from exchange when not provided (avoids impossible 100% adoption)
    if estimated_network_size <= 1:
        try:
            all_rows = exchange.audit_rows()
        except Exception:
            all_rows = []
        observed_peers = len({r.get('peer', '') for r in all_rows
                              if r.get('kind') == 'CREDIT_DELTA' and r.get('peer')}) or 1
        estimated_network_size = observed_peers

    # Depletion guard: DEPLETED features cannot be listed on the open market
    dep = feature_depletion_status(feature_id, exchange,
                                   estimated_network_size=estimated_network_size)
    if dep['state'] == 'DEPLETED':
        raise ValueError(
            f'Feature {feature_id!r} is DEPLETED ({dep["adoption_rate"]:.0%} adopted, '
            f'supply_pressure={dep["supply_pressure"]:.3f}). '
            'No borrow revenue remains — listing would mislead buyers. '
            'Use sell_equity(price_units=0) for a zero-price exit transfer.'
        )

    holdings = _fe.equity_holdings(feature_id, exchange)
    held = holdings.get(seller_id, 0)
    if held < basis_points:
        raise ValueError(
            f'{seller_id!r} holds {held} bp, cannot list {basis_points} bp for sale'
        )
    if basis_points < _fe.EQUITY_MIN_TRADE_BP:
        raise ValueError(
            f'Minimum listing is {_fe.EQUITY_MIN_TRADE_BP} bp, got {basis_points}'
        )

    # Price floor and type validation
    if ask_price_units < 0:
        raise ValueError('ask_price_units cannot be negative')
    if not isinstance(ask_price_units, int):
        raise ValueError('ask_price_units must be an integer (no fractional pricing)')

    # Wash-trading guard: reject 24h round-trips
    _check_wash_trading(exchange, seller_id, feature_id)

    # Price-momentum guard: reject sudden spikes above 1.5× 7-day median
    if ask_price_units > 0:
        _validate_ask_price_momentum(exchange, feature_id, ask_price_units)

    # Executor price ceiling: P2P borrow price MUST be ≤ executor mint cost.
    # This guarantees the P2P market is always cheaper than hiring the executor
    # to generate the feature from scratch. Sellers earn from volume (many buyers),
    # not from overpricing — total earnings can exceed original cost via multi-buyer.
    if ask_price_units > 0:
        try:
            all_rows = exchange.audit_rows()
        except Exception:
            all_rows = []
        created_row = next(
            (r for r in all_rows
             if r.get('kind') == 'EQUITY_CREATED' and r.get('feature_id') == feature_id),
            None,
        )
        if created_row:
            exec_ref = int(created_row.get('executor_reference_price_units', 0))
            if exec_ref > 0 and ask_price_units > exec_ref:
                raise ValueError(
                    f'ask_price_units {ask_price_units} exceeds executor reference price {exec_ref}. '
                    f'P2P borrow price must be ≤ executor mint cost (buyers must always save vs executor). '
                    f'Earn more by selling to many buyers, not by charging above executor price.'
                )

    listing_id = f'elst-{int(time.time() * 1000)}-{seller_id[:8]}'
    exchange.append_audit_row({
        'kind': 'EQUITY_LISTING',
        'listing_id': listing_id,
        'feature_id': feature_id,
        'seller_id': seller_id,
        'basis_points': basis_points,
        'ask_price_units': ask_price_units,
        'expires_at_unix': time.time() + LISTING_EXPIRY_SECONDS,
        'at_unix': time.time(),
        'at': _now_iso(),
    })
    return listing_id


def cancel_listing(exchange, listing_id: str, seller_id: str) -> None:
    """Cancel an open equity listing. Only the original seller can cancel."""
    lst = _get_listing(exchange, listing_id)
    if lst is None:
        raise ValueError(f'Listing {listing_id!r} not found')
    if lst.get('seller_id') != seller_id:
        raise ValueError(f'{seller_id!r} is not the seller of listing {listing_id!r}')
    if _listing_state(exchange, listing_id) != 'OPEN':
        raise ValueError(f'Listing {listing_id!r} is not open')
    exchange.append_audit_row({
        'kind': 'EQUITY_LISTING_CANCELLED',
        'listing_id': listing_id,
        'seller_id': seller_id,
        'at_unix': time.time(),
        'at': _now_iso(),
    })


def fill_listing(
    exchange,
    root: str,
    listing_id: str,
    buyer_id: str,
) -> None:
    """Fill an open equity listing — transfers ownership at the listed ask price.

    Deducts ask_price from buyer and calls sell_equity() to record the transfer.
    Raises ValueError if listing is not open, expired, or buyer can't afford it.
    """
    from . import feature_equity as _fe, credit_ledger as _cl

    lst = _get_listing(exchange, listing_id)
    if lst is None:
        raise ValueError(f'Listing {listing_id!r} not found')
    if _listing_state(exchange, listing_id) != 'OPEN':
        raise ValueError(f'Listing {listing_id!r} is not open or already filled')
    if time.time() > float(lst.get('expires_at_unix', 0)):
        raise ValueError(f'Listing {listing_id!r} has expired')

    feature_id = lst['feature_id']
    seller_id  = lst['seller_id']
    bp         = int(lst['basis_points'])
    price      = int(lst['ask_price_units'])

    _fe.sell_equity(exchange, root, feature_id, seller_id, buyer_id, bp,
                    price_units=price)
    exchange.append_audit_row({
        'kind': 'EQUITY_LISTING_FILLED',
        'listing_id': listing_id,
        'feature_id': feature_id,
        'seller_id': seller_id,
        'buyer_id': buyer_id,
        'basis_points': bp,
        'price_units': price,
        'at_unix': time.time(),
        'at': _now_iso(),
    })


def open_listings(exchange, feature_id: str | None = None) -> list[dict]:
    """Return all currently open (unfilled, uncancelled, unexpired) listings.

    Optionally filtered to a single feature_id.
    """
    try:
        rows = exchange.audit_rows()
    except Exception:
        return []
    listings: dict[str, dict] = {}
    filled: set[str] = set()
    cancelled: set[str] = set()

    for r in rows:
        kind = r.get('kind', '')
        if kind == 'EQUITY_LISTING':
            listings[r['listing_id']] = r
        elif kind == 'EQUITY_LISTING_FILLED':
            filled.add(r.get('listing_id', ''))
        elif kind == 'EQUITY_LISTING_CANCELLED':
            cancelled.add(r.get('listing_id', ''))

    now = time.time()
    result = []
    for lid, lst in listings.items():
        if lid in filled or lid in cancelled:
            continue
        if now > float(lst.get('expires_at_unix', 0)):
            continue
        if feature_id is not None and lst.get('feature_id') != feature_id:
            continue
        result.append(lst)
    return result


def _get_listing(exchange, listing_id: str) -> dict | None:
    try:
        rows = exchange.audit_rows()
    except Exception:
        return None
    return next((r for r in rows
                 if r.get('kind') == 'EQUITY_LISTING' and r.get('listing_id') == listing_id),
                None)


def _listing_state(exchange, listing_id: str) -> str:
    try:
        rows = exchange.audit_rows()
    except Exception:
        return 'NOT_FOUND'
    filled    = any(r.get('listing_id') == listing_id for r in rows if r.get('kind') == 'EQUITY_LISTING_FILLED')
    cancelled = any(r.get('listing_id') == listing_id for r in rows if r.get('kind') == 'EQUITY_LISTING_CANCELLED')
    if filled:
        return 'FILLED'
    if cancelled:
        return 'CANCELLED'
    lst = _get_listing(exchange, listing_id)
    if lst is None:
        return 'NOT_FOUND'
    if time.time() > float(lst.get('expires_at_unix', 0)):
        return 'EXPIRED'
    return 'OPEN'


# ── Auto-buy engine ───────────────────────────────────────────────────────────

def auto_buy(
    exchange,
    root: str,
    buyer_id: str,
    config: dict | None = None,
    quality_scores: dict[str, float] | None = None,
    adoption_counts: dict[str, int] | None = None,
) -> dict:
    """Run one auto-buy pass against open listings, filtered by configured thresholds.

    quality_scores: {feature_id: wilson_quality_score} — caller provides current scores
    adoption_counts: {feature_id: distinct_adopter_count} — caller provides counts
    Both default to empty dicts (no scores = no buys from quality/adoption gate).

    Returns:
        {
          'bought': [{'listing_id', 'feature_id', 'bp', 'price'}],
          'skipped': [{'listing_id', 'feature_id', 'reason'}],
          'spent_units': int,
        }
    """
    from . import feature_equity as _fe, credit_ledger as _cl

    cfg = (config or {}).get('auto_buy', {})
    if not cfg.get('enabled', False):
        return {'bought': [], 'skipped': [], 'spent_units': 0}

    min_q           = float(cfg.get('min_quality_wilson', 0.65))
    min_adopt       = int(cfg.get('min_adoption_count', 5))
    max_price_x     = float(cfg.get('max_price_multiplier', 1.0))
    max_bp          = int(cfg.get('max_bp_per_feature', 2000))
    max_spend       = int(cfg.get('max_spend_per_run_units', 0))
    max_adopt_rate   = float(cfg.get('max_adoption_rate', 0.70))
    min_supply_pres  = float(cfg.get('min_supply_pressure', 0.25))
    min_remain       = int(cfg.get('min_remaining_adopters', 5))
    min_lucrativity  = float(cfg.get('min_lucrativity_score', 0.10))
    lucr_window      = float(cfg.get('lucrativity_window_days', 30.0))

    qs = quality_scores or {}
    ac = adoption_counts or {}

    listings = open_listings(exchange)
    bought   = []
    skipped  = []
    spent    = 0

    base_borrow = _cl.apply_borrow_cost()

    for lst in listings:
        lid        = lst['listing_id']
        feature_id = lst['feature_id']
        seller_id  = lst['seller_id']
        bp         = int(lst['basis_points'])
        ask        = int(lst['ask_price_units'])

        if seller_id == buyer_id:
            skipped.append({'listing_id': lid, 'feature_id': feature_id, 'reason': 'own_listing'})
            continue

        # Quality gate
        q = qs.get(feature_id, 0.0)
        if q < min_q:
            skipped.append({'listing_id': lid, 'feature_id': feature_id,
                            'reason': f'quality {q:.2f} < {min_q}'})
            continue

        # Adoption gate
        adopt = ac.get(feature_id, 0)
        if adopt < min_adopt:
            skipped.append({'listing_id': lid, 'feature_id': feature_id,
                            'reason': f'adoption {adopt} < {min_adopt}'})
            continue

        # Price gate
        max_price = int(base_borrow * max_price_x)
        if max_price > 0 and ask > max_price:
            skipped.append({'listing_id': lid, 'feature_id': feature_id,
                            'reason': f'ask {ask} > max_price {max_price}'})
            continue

        # Depletion guard — protect buyer from purchasing exhausted revenue streams
        # Use max(observed_peers, adopt+1) to prevent impossible 100% adoption from
        # a small observed CREDIT_DELTA peer set (e.g. new exchange with no credit history)
        net_size = len({r.get('peer', '') for r in exchange.audit_rows()
                        if r.get('kind') == 'CREDIT_DELTA' and r.get('peer')}) or 1
        net_size = max(net_size, adopt + 1)
        dep = feature_depletion_status(feature_id, exchange,
                                       estimated_network_size=net_size,
                                       adoption_count=adopt)
        if dep['adoption_rate'] > max_adopt_rate:
            skipped.append({'listing_id': lid, 'feature_id': feature_id,
                            'reason': f'depletion: adoption_rate {dep["adoption_rate"]:.0%} > {max_adopt_rate:.0%}'})
            continue
        if dep['supply_pressure'] < min_supply_pres:
            skipped.append({'listing_id': lid, 'feature_id': feature_id,
                            'reason': f'depletion: supply_pressure {dep["supply_pressure"]:.3f} < {min_supply_pres}'})
            continue
        if dep['remaining_adopters'] < min_remain:
            skipped.append({'listing_id': lid, 'feature_id': feature_id,
                            'reason': f'depletion: remaining_adopters {dep["remaining_adopters"]} < {min_remain}'})
            continue
        if dep['state'] == 'DEPLETED':
            skipped.append({'listing_id': lid, 'feature_id': feature_id,
                            'reason': 'depletion: feature is DEPLETED — no borrow revenue remains'})
            continue

        # Lucrativity gate — projected earnings in window must be worth the purchase
        lucr = lucrativity_assessment(feature_id, exchange,
                                      window_days=lucr_window,
                                      bp_held=bp,
                                      estimated_network_size=net_size)
        if lucr['lucrativity_score'] < min_lucrativity:
            skipped.append({'listing_id': lid, 'feature_id': feature_id,
                            'reason': f'lucrativity {lucr["lucrativity_score"]:.3f} < {min_lucrativity} '
                                      f'({lucr["verdict"]}, window={lucr_window}d)'})
            continue

        # Anti-concentration
        holdings = _fe.equity_holdings(feature_id, exchange)
        buyer_holds = holdings.get(buyer_id, 0)
        if buyer_holds + bp > max_bp:
            skipped.append({'listing_id': lid, 'feature_id': feature_id,
                            'reason': f'would hold {buyer_holds+bp} > max_bp {max_bp}'})
            continue

        # Budget
        if max_spend > 0 and spent + ask > max_spend:
            skipped.append({'listing_id': lid, 'feature_id': feature_id,
                            'reason': 'run_budget_exhausted'})
            continue

        # Execute
        try:
            fill_listing(exchange, root, lid, buyer_id)
            bought.append({'listing_id': lid, 'feature_id': feature_id,
                           'bp': bp, 'price_units': ask})
            spent += ask
        except ValueError as e:
            skipped.append({'listing_id': lid, 'feature_id': feature_id, 'reason': str(e)})

    return {'bought': bought, 'skipped': skipped, 'spent_units': spent}


# ── Auto-sell engine ──────────────────────────────────────────────────────────

def auto_sell(
    exchange,
    root: str,
    seller_id: str,
    config: dict | None = None,
    quality_scores: dict[str, float] | None = None,
    adoption_counts: dict[str, int] | None = None,
) -> dict:
    """Run one auto-sell pass, creating listings for qualifying held equity.

    Evaluates each feature the seller holds equity in against configured thresholds.
    Creates EQUITY_LISTING rows (not immediate sells — buyer must fill them).

    Returns:
        {
          'listed': [{'listing_id', 'feature_id', 'bp', 'ask_price'}],
          'skipped': [{'feature_id', 'reason'}],
        }
    """
    from . import feature_equity as _fe, credit_ledger as _cl

    cfg = (config or {}).get('auto_sell', {})
    if not cfg.get('enabled', False):
        return {'listed': [], 'skipped': []}

    min_return           = float(cfg.get('min_return_multiplier', 2.0))
    bp_to_list           = int(cfg.get('bp_to_sell_per_trigger', 1000))
    min_hold_bp          = int(cfg.get('min_hold_bp_to_trigger', 500))
    sell_on_near_dep     = bool(cfg.get('sell_on_near_depleted', True))
    sell_on_slowing      = bool(cfg.get('sell_on_slowing', False))

    qs = quality_scores or {}
    ac = adoption_counts or {}

    # Find all features this seller holds equity in
    try:
        rows = exchange.audit_rows()
    except Exception:
        rows = []

    feature_ids: set[str] = set()
    for r in rows:
        if r.get('kind') in ('EQUITY_GRANT', 'EQUITY_SELL'):
            fid = r.get('feature_id', '')
            if fid:
                feature_ids.add(fid)

    base_borrow = _cl.apply_borrow_cost()
    listed      = []
    skipped     = []

    for feature_id in sorted(feature_ids):
        holdings = _fe.equity_holdings(feature_id, exchange)
        held     = holdings.get(seller_id, 0)

        if held < min_hold_bp:
            skipped.append({'feature_id': feature_id,
                            'reason': f'hold {held} < min_hold_bp {min_hold_bp}'})
            continue

        # Estimate purchase cost from audit history (0 for original grants)
        purchase_cost = _purchase_cost(exchange, feature_id, seller_id)
        adopt_cnt = ac.get(feature_id, 0)
        market_price  = _cl.feature_market_price(
            feature_id, exchange, base_borrow,
            quality_wilson=qs.get(feature_id, 0.5),
            adoption_count=adopt_cnt,
        )

        # Check depletion state — can override return threshold for protective exit
        net_size = len({r.get('peer', '') for r in exchange.audit_rows()
                        if r.get('kind') == 'CREDIT_DELTA' and r.get('peer')}) or 1
        net_size = max(net_size, adopt_cnt + 1)
        dep = feature_depletion_status(feature_id, exchange,
                                       estimated_network_size=net_size,
                                       adoption_count=adopt_cnt)

        # Depletion-triggered sell only for NEAR_DEPLETED/SLOWING — not DEPLETED
        # (DEPLETED features cannot be listed; only zero-price OTC transfer is valid)
        depletion_triggered = (
            (dep['state'] == 'NEAR_DEPLETED' and sell_on_near_dep) or
            (dep['state'] == 'SLOWING' and sell_on_slowing)
        )

        threshold = int(purchase_cost * min_return) if purchase_cost > 0 else base_borrow
        if not depletion_triggered and market_price < threshold:
            skipped.append({'feature_id': feature_id,
                            'reason': f'market {market_price} < threshold {threshold}'})
            continue

        sell_bp = min(bp_to_list, held)
        try:
            lid = list_for_sale(exchange, feature_id, seller_id, sell_bp, market_price)
            listed.append({'listing_id': lid, 'feature_id': feature_id,
                           'bp': sell_bp, 'ask_price_units': market_price,
                           'depletion_state': dep['state'],
                           'depletion_triggered': depletion_triggered})
        except ValueError as e:
            skipped.append({'feature_id': feature_id, 'reason': str(e)})

    return {'listed': listed, 'skipped': skipped}


def _purchase_cost(exchange, feature_id: str, buyer_id: str) -> int:
    """Estimate what buyer_id paid for their equity in feature_id.

    Returns 0 for original grants (creator received equity for free).
    For purchased equity, returns the recorded price_units.
    """
    try:
        rows = exchange.audit_rows()
    except Exception:
        return 0
    total = 0
    for r in rows:
        if r.get('kind') == 'EQUITY_SELL' and r.get('feature_id') == feature_id:
            if r.get('buyer_id') == buyer_id:
                total += int(r.get('price_units', 0))
    return total


# ── Auto-mint minimal features ────────────────────────────────────────────────

def auto_mint_minimal_features(exchange, root: str, owner_id: str, config: dict | None = None) -> list[dict]:
    """Scan completed work contracts and auto-mint atomic outputs to the P2P network.

    Only fires when config['auto_mint']['enabled'] = True (default: False).
    Mints work products whose complexity is below max_complexity_threshold and
    quality exceeds min_quality_score, skipping any already minted to the network.

    Multi-buyer model: each EQUITY_BORROW earns the minter revenue. Total earnings
    across all buyers can exceed the original executor cost — the P2P network
    distributes the work cost across many adopters.
    """
    cfg = (config or {}).get('auto_mint', {})
    if not cfg.get('enabled', False):
        return []

    max_complexity = float(cfg.get('max_complexity_threshold', 0.5))
    min_quality = float(cfg.get('min_quality_score', 0.6))

    try:
        all_rows = exchange.audit_rows()
    except Exception:
        return []

    # Features already minted — avoid duplicates
    minted_ids: set[str] = {r.get('feature_id', '') for r in all_rows if r.get('kind') == 'EQUITY_CREATED'}

    # Completed work contracts owned by this peer
    completed_ids: set[str] = {
        r.get('request_id', '') for r in all_rows
        if r.get('kind') in ('WORK_RELEASED', 'WORK_CONTRACT_SUMMARY')
        and r.get('requester_id') == owner_id
        and r.get('request_id')
    }

    minted_now: list[dict] = []
    for request_id in completed_ids:
        req_row = next(
            (r for r in all_rows if r.get('kind') == 'WORK_REQUEST' and r.get('request_id') == request_id),
            None,
        )
        if req_row is None:
            continue

        complexity = float(req_row.get('complexity', 1.0))
        if complexity >= max_complexity:
            continue

        quality = float(req_row.get('quality_score', 0.0))
        if quality < min_quality:
            continue

        # Deterministic feature_id from owner + request — idempotent across runs
        feature_id = 'auto:' + hashlib.sha256(f'{owner_id}:{request_id}'.encode()).hexdigest()[:16]
        if feature_id in minted_ids:
            continue

        executor_ref_price = int(req_row.get('budget_units', 100))

        exchange.append_audit_row({'kind': 'EQUITY_CREATED',
            'feature_id': feature_id, 'owner_id': owner_id,
            'total_basis_points': 10000, 'source_request_id': request_id,
            'complexity': complexity, 'quality_score': quality,
            'auto_minted': True,
            'executor_reference_price_units': executor_ref_price, 'root': root})
        minted_ids.add(feature_id)
        minted_now.append({
            'feature_id': feature_id,
            'source_request_id': request_id,
            'complexity': complexity,
            'quality_score': quality,
            'executor_reference_price_units': executor_ref_price,
        })

    return minted_now
