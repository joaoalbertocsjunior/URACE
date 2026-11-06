"""Unified cost model for URACE operations.

Every token-denominated cost of operating on the P2P network passes through here.
Enables the core claim: 'cheaper than raw executor' by making costs transparent and comparable.

Cost components:
  executor_cost               — reference price per executor call (from policy or ledger median)
  p2p_delivery_cost           — estimated bandwidth/relay overhead per byte delivered
  erasure_cost                — per-chunk overhead for Reed-Solomon n_parity extra replicas
  mint_stake_cost             — amortized mint stake over expected feature lifetime (borrows)
  consensus_cost              — currently 0 (PoQ not PoW; no mining)
  composition_referral        — fraction of borrow_cost flowing to provenance holders
  bandwidth_cost              — metered internet cost per MB transferred
  artifact_production_cost    — proxy for creator's production effort per KB
  protocol_fee                — 2% of fill price → protocol treasury (funds seal/llm_peer rewards)
  consensus_cost_per_check    — units spent per LLM similarity check
  gas_overhead_units          — on-chain gas cost per transaction in URACE units (0 = off-chain)
                                 Set gas_per_tx_gwei + gas_price_gwei + urace_units_per_gwei
                                 for dynamic EVM estimation, or gas_overhead_units for static.

Returns a breakdown dict so callers can explain cost to users.
"""
from __future__ import annotations
import math

SCHEMA = 'urace-cost-model-v1'

# Default constants — all overridable via config p2p.*
_DEFAULTS = {
    'executor_reference_price_per_unit': 1,   # 1 token per executor call
    'p2p_bytes_per_unit': 1_000_000,          # 1 token per MB delivered
    'erasure_overhead_fraction': 0.5,          # n_parity=2 out of n_total=6 → ~0.5 overhead
    'mint_stake_units': 3,                     # default stake
    'expected_lifetime_borrows': 20,           # amortize stake over 20 borrows
    'composition_referral_rate': 0.20,
    'delivery_fee_fraction': 0.10,
    'challenge_window_days': 30,
    'bandwidth_cost_per_mb': 0.0,             # 0 = LAN/unmetered; set >0 for metered internet
    'artifact_production_cost_per_kb': 0.0,   # proxy for creator's production effort
    'protocol_fee_fraction': 0.02,             # 2% of fill price → protocol treasury
    'consensus_cost_per_check': 1,             # units spent per LLM similarity check
    # On-chain gas overhead — all three fields needed for dynamic EVM estimation;
    # set gas_overhead_units alone for a static override; default 0 = off-chain/sponsored.
    'gas_overhead_units': 0,                  # static URACE units per on-chain tx (direct override)
    'gas_per_tx_gwei': 0,                     # EVM gas consumed per tx (e.g. 21000 simple transfer; ~65000 ERC-20)
    'gas_price_gwei': 0,                      # current gas price in Gwei (fetch from oracle or set manually)
    'urace_units_per_gwei': 0,                # conversion: how many URACE units = 1 Gwei of gas cost
}


def _cfg(config: dict, key: str):
    return config.get('p2p', {}).get(key, _DEFAULTS[key])


def estimate_gas_overhead(config: dict) -> float:
    """Return gas overhead in URACE units for one on-chain transaction.

    Priority:
    1. Dynamic EVM estimate: gas_per_tx_gwei × gas_price_gwei × urace_units_per_gwei
       (all three must be > 0)
    2. Static override: gas_overhead_units (direct config value)
    3. Default: 0.0 (off-chain / sponsored / no on-chain settlement)

    Example configs:
      Base/Arbitrum cheap tx (~65k gas, 0.01 Gwei, 1 unit/Gwei):
        gas_per_tx_gwei: 65000, gas_price_gwei: 0.01, urace_units_per_gwei: 1
        → 65000 × 0.01 × 1 = 650 units  (adjust urace_units_per_gwei to your token price)

      Static override (measured externally, set once):
        gas_overhead_units: 5  → 5 URACE units per tx regardless of chain conditions

      Off-chain / account-abstraction sponsored:
        (default) → 0.0
    """
    p2p = config.get('p2p', {})
    gas_per_tx = float(p2p.get('gas_per_tx_gwei', _DEFAULTS['gas_per_tx_gwei']))
    gas_price = float(p2p.get('gas_price_gwei', _DEFAULTS['gas_price_gwei']))
    units_per_gwei = float(p2p.get('urace_units_per_gwei', _DEFAULTS['urace_units_per_gwei']))
    if gas_per_tx > 0 and gas_price > 0 and units_per_gwei > 0:
        return gas_per_tx * gas_price * units_per_gwei
    return float(p2p.get('gas_overhead_units', _DEFAULTS['gas_overhead_units']))


def mint_feature_cost(config: dict, artifact_size_bytes: int = 0,
                      n_replicas: int = 2) -> dict:
    """Cost to mint a feature and distribute to replicas."""
    stake = _cfg(config, 'mint_stake_units')
    erasure_frac = _cfg(config, 'erasure_overhead_fraction')
    p2p_rate = _cfg(config, 'p2p_bytes_per_unit')
    delivery_bytes = artifact_size_bytes * (1 + erasure_frac) * n_replicas
    p2p_cost = delivery_bytes / p2p_rate if p2p_rate > 0 else 0
    bandwidth_cost_per_mb = _cfg(config, 'bandwidth_cost_per_mb')
    artifact_production_cost_per_kb = _cfg(config, 'artifact_production_cost_per_kb')
    network_distribution_cost_units = int(artifact_size_bytes * n_replicas / 1_000_000 * bandwidth_cost_per_mb)
    artifact_production_cost_units = int(artifact_size_bytes / 1024 * artifact_production_cost_per_kb)
    total = stake + p2p_cost + network_distribution_cost_units + artifact_production_cost_units
    return {
        'schema': SCHEMA,
        'operation': 'mint_feature',
        'mint_stake': stake,
        'p2p_delivery_cost': round(p2p_cost, 4),
        'erasure_overhead_fraction': erasure_frac,
        'n_replicas': n_replicas,
        'artifact_size_bytes': artifact_size_bytes,
        'consensus_cost': 0,
        'network_distribution_cost_units': network_distribution_cost_units,
        'artifact_production_cost_units': artifact_production_cost_units,
        'total_units': round(total, 4),
    }


def borrow_feature_cost(config: dict, ask_price_units: int,
                        artifact_size_bytes: int = 0,
                        has_replica_delivery: bool = False) -> dict:
    """Cost to borrow a feature (from buyer's perspective)."""
    delivery_fee = int(ask_price_units * _cfg(config, 'delivery_fee_fraction')) if has_replica_delivery else 0
    referral_pool = int((ask_price_units - delivery_fee) * _cfg(config, 'composition_referral_rate'))
    creator_net = ask_price_units - delivery_fee - referral_pool
    p2p_rate = _cfg(config, 'p2p_bytes_per_unit')
    p2p_cost = artifact_size_bytes / p2p_rate if p2p_rate > 0 else 0
    bandwidth_cost_per_mb = _cfg(config, 'bandwidth_cost_per_mb')
    protocol_fee_fraction = _cfg(config, 'protocol_fee_fraction')
    network_download_cost_units = int(artifact_size_bytes / 1_000_000 * bandwidth_cost_per_mb)
    protocol_fee_units = int(ask_price_units * protocol_fee_fraction)
    gas_overhead = estimate_gas_overhead(config)
    total = ask_price_units + p2p_cost + network_download_cost_units + protocol_fee_units + gas_overhead
    return {
        'schema': SCHEMA,
        'operation': 'borrow_feature',
        'ask_price_units': ask_price_units,
        'delivery_fee': delivery_fee,
        'composition_referral_pool': referral_pool,
        'creator_net': creator_net,
        'p2p_delivery_cost': round(p2p_cost, 4),
        'consensus_cost': 0,
        'network_download_cost_units': network_download_cost_units,
        'protocol_fee_units': protocol_fee_units,
        'gas_overhead_units': round(gas_overhead, 4),
        'total_buyer_cost': round(total, 4),
    }


def list_for_sale_cost(config: dict) -> dict:
    """Cost to list a feature for sale (negligible — audit row append only)."""
    return {
        'schema': SCHEMA,
        'operation': 'list_for_sale',
        'listing_cost': 0,
        'note': 'Listing is free; cost is paid at fill time by buyer.',
    }


def challenge_cost(config: dict) -> dict:
    """Cost to file a provenance challenge."""
    stake = int(config.get('p2p', {}).get('challenger_stake_units', 2))
    return {
        'schema': SCHEMA,
        'operation': 'challenge',
        'challenger_stake': stake,
        'max_bounty': stake + _cfg(config, 'mint_stake_units'),
        'note': 'Stake returned + bounty if upheld; stake slashed if rejected.',
    }


def amortized_mint_cost_per_borrow(config: dict) -> float:
    """Mint stake amortized over expected lifetime borrows."""
    stake = _cfg(config, 'mint_stake_units')
    lifetime = _cfg(config, 'expected_lifetime_borrows')
    return stake / lifetime if lifetime > 0 else stake


def vs_executor_comparison(config: dict, ask_price_units: int,
                            executor_calls_saved: int = 1,
                            executor_reference_price: int | None = None) -> dict:
    """Compare cost of borrowing a feature vs running the executor directly.

    executor_reference_price — override the config value (e.g. from network median).
    cheaper_than_executor is ALWAYS computed; never silently skipped.
    """
    if executor_reference_price is not None:
        executor_ref = executor_reference_price
    else:
        executor_ref = _cfg(config, 'executor_reference_price_per_unit')
    executor_total = executor_ref * executor_calls_saved
    borrow = borrow_feature_cost(config, ask_price_units)
    # Use the full buyer cost (includes network_download + protocol_fee)
    p2p_total_cost = borrow['total_buyer_cost']
    amortized = amortized_mint_cost_per_borrow(config)
    net_saving = executor_total - (p2p_total_cost + amortized)
    return {
        'schema': SCHEMA,
        'operation': 'vs_executor_comparison',
        'executor_cost_per_call': executor_ref,
        'executor_calls_saved': executor_calls_saved,
        'executor_total': executor_total,
        'borrow_total': p2p_total_cost,
        'amortized_mint_cost': round(amortized, 4),
        'net_saving': round(net_saving, 4),
        'cheaper_than_executor': net_saving > 0,
    }


def derive_executor_reference_price(rows: list) -> int:
    """Derive executor reference price from local ledger history.

    Priority:
    1. Median price from EQUITY_LISTING_FILLED rows (last 90 days)
    2. Median amount_units from CREDIT_DELTA(direction='earn') rows (last 90 days)
    3. Fallback: 10 (hardcoded floor)
    Returns int >= 1.
    """
    import time as _time
    cutoff = _time.time() - 90 * 86400
    filled = [r for r in rows
              if r.get('kind') == 'EQUITY_LISTING_FILLED'
              and float(r.get('at_unix', 0)) >= cutoff
              and r.get('price_units') is not None]
    if filled:
        prices = sorted(int(r['price_units']) for r in filled)
        mid = len(prices) // 2
        median = prices[mid] if len(prices) % 2 == 1 else (prices[mid - 1] + prices[mid]) // 2
        return max(1, median)
    earn = [r for r in rows
            if r.get('kind') == 'CREDIT_DELTA'
            and r.get('direction') == 'earn'
            and float(r.get('at_unix', 0)) >= cutoff
            and r.get('amount_units') is not None]
    if earn:
        amounts = sorted(int(r['amount_units']) for r in earn)
        mid = len(amounts) // 2
        median = amounts[mid] if len(amounts) % 2 == 1 else (amounts[mid - 1] + amounts[mid]) // 2
        return max(1, median)
    return 10  # hardcoded floor


def minimum_viable_price(config: dict, artifact_size_bytes: int = 0) -> int:
    """Minimum price that covers creator's production + network + protocol costs.

    = ceil(artifact_production_cost + network_distribution_cost_amortized + protocol_fee_on_min_price)
    where network_distribution_cost_amortized = distribution_cost / expected_lifetime_borrows
    Returns int >= 1.
    """
    bandwidth_cost_per_mb = _cfg(config, 'bandwidth_cost_per_mb')
    artifact_production_cost_per_kb = _cfg(config, 'artifact_production_cost_per_kb')
    expected_lifetime_borrows = _cfg(config, 'expected_lifetime_borrows')
    protocol_fee_fraction = _cfg(config, 'protocol_fee_fraction')
    n_replicas = int(config.get('p2p', {}).get('default_replicas', 2))
    artifact_production_cost = artifact_size_bytes / 1024 * artifact_production_cost_per_kb
    distribution_cost = artifact_size_bytes * n_replicas / 1_000_000 * bandwidth_cost_per_mb
    network_distribution_cost_amortized = distribution_cost / max(1, expected_lifetime_borrows)
    gas_overhead = estimate_gas_overhead(config)
    base = artifact_production_cost + network_distribution_cost_amortized + gas_overhead
    # Solve: price = base + protocol_fee_fraction * price  →  price = base / (1 - fee)
    fee_frac = float(protocol_fee_fraction)
    if fee_frac >= 1.0:
        fee_frac = 0.0
    if base <= 0:
        return 1
    price = base / (1.0 - fee_frac)
    return max(1, math.ceil(price))


def total_operation_cost(operation: str, config: dict, **kwargs) -> dict:
    """Unified entry point for all operation cost computations."""
    ops = {
        'mint_feature': mint_feature_cost,
        'borrow_feature': borrow_feature_cost,
        'list_for_sale': list_for_sale_cost,
        'challenge': challenge_cost,
    }
    fn = ops.get(operation)
    if not fn:
        return {'schema': SCHEMA, 'operation': operation, 'error': f'Unknown operation: {operation!r}'}
    return fn(config, **kwargs)
