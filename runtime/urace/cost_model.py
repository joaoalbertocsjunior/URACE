"""Estimate operating costs and keep incomparable resources distinct.

This module does not establish that P2P is cheaper than executor work. A
qualified comparison requires task-matched receipts and independent acceptance.

Cost components:
  executor_cost               — optional owner-configured estimate per executor call
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
        → 65000 × 0.01 × 1 = 650 configured URACE units (the conversion is an owner estimate)

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
    """Return a legacy estimate, explicitly marked unqualified unless baseline is supplied.

    Ledger trades and reputation credits are not executor costs. Configured values are
    estimates too; only task-specific observed receipts can support a savings claim.
    """
    if executor_reference_price is not None:
        executor_ref = executor_reference_price
    else:
        executor_ref = config.get('p2p', {}).get('executor_reference_price_per_unit')
    if executor_ref is None:
        return {
            'schema': SCHEMA, 'operation': 'vs_executor_comparison',
            'comparison_status': 'UNQUALIFIED', 'comparison_source': 'no_observed_executor_baseline',
            'executor_cost_per_call': None, 'executor_calls_saved': None,
            'executor_total': None, 'borrow_total': borrow_feature_cost(config, ask_price_units)['total_buyer_cost'],
            'amortized_mint_cost': amortized_mint_cost_per_borrow(config),
            'net_saving': None, 'cheaper_than_executor': None,
        }
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
        'comparison_status': 'ESTIMATE_ONLY',
        'comparison_source': 'explicit_config_estimate' if executor_reference_price is None else 'caller_supplied_estimate',
        'cheaper_than_executor': None,
    }


def compare_paired_cost_inputs(config: dict, *, executor_cost_units: float | None,
                               ask_price_units: int, artifact_size_bytes: int = 0,
                               integration_cost_units: float | None = None,
                               validation_cost_units: float | None = None,
                               residual_executor_cost_units: float | None = None,
                               amortize_mint: bool = False,
                               task_id: str | None = None,
                               acceptance_contract_sha256: str | None = None,
                               executor_receipt_id: str | None = None,
                               p2p_receipt_id: str | None = None,
                               acceptance_receipt_id: str | None = None,
                               executor_accepted: bool | None = None,
                               p2p_accepted: bool | None = None,
                               independent_acceptance: bool = False,
                               executor_tokens: dict | None = None,
                               p2p_tokens: dict | None = None) -> dict:
    """Compare a task matched pair; unknown costs or non-equivalent outcomes block qualification.

    Inputs are in the same URACE cost unit. Executor token counts and fiat charges
    must be reported separately by callers; they are never silently converted.
    """
    p2p = borrow_feature_cost(config, ask_price_units, artifact_size_bytes)
    amortized = amortized_mint_cost_per_borrow(config) if amortize_mint else 0.0
    required = (executor_cost_units, integration_cost_units, validation_cost_units,
                residual_executor_cost_units)
    costs_complete = all(v is not None and math.isfinite(float(v)) and float(v) >= 0 for v in required)
    pair_complete = bool(task_id and acceptance_contract_sha256 and executor_receipt_id
                         and p2p_receipt_id and acceptance_receipt_id and independent_acceptance
                         and executor_accepted is True and p2p_accepted is True)
    complete = costs_complete and pair_complete
    p2p_total = (p2p['total_buyer_cost'] + amortized + float(integration_cost_units or 0)
                 + float(validation_cost_units or 0) + float(residual_executor_cost_units or 0))
    saving = float(executor_cost_units) - p2p_total if complete else None
    return {
        'schema': SCHEMA, 'operation': 'paired_p2p_vs_executor_cost_estimate',
        'comparison_status': 'PAIR_INPUTS_COMPLETE_UNVERIFIED' if complete else 'UNQUALIFIED_MISSING_RECEIPTS_OR_PAIR',
        'task_id': task_id,
        'acceptance_contract_sha256': acceptance_contract_sha256,
        'executor_receipt_id': executor_receipt_id,
        'p2p_receipt_id': p2p_receipt_id,
        'acceptance_receipt_id': acceptance_receipt_id,
        'executor_accepted': executor_accepted,
        'p2p_accepted': p2p_accepted,
        'independent_acceptance': independent_acceptance,
        'executor_cost_units': executor_cost_units,
        'p2p_acquisition_cost_units': p2p['total_buyer_cost'],
        'integration_cost_units': integration_cost_units,
        'validation_cost_units': validation_cost_units,
        'residual_executor_cost_units': residual_executor_cost_units,
        'amortized_mint_cost_units': amortized,
        'p2p_total_cost_units': round(p2p_total, 4) if complete else None,
        'net_saving_units': round(saving, 4) if complete else None,
        'cheaper_than_executor': None,
        'cheaper_than_executor_estimate': (saving > 0) if complete else None,
        'receipt_verification': 'CALLER_ASSERTED_NOT_VALIDATED',
        'independently_qualified': False,
        'executor_token_usage': executor_tokens,
        'p2p_token_usage': p2p_tokens,
        'qualification_note': 'This helper checks supplied fields only; it does not verify receipt provenance or acceptance authority. Integrate with the trial verifier before claiming qualified savings.',
    }


def derive_executor_reference_price(rows: list) -> int | None:
    """Deprecated: exchange prices/rewards are not evidence of executor cost."""
    return None


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


# ---------------------------------------------------------------------------
# Executor receipt contract
#
# Receipts capture real API token counts from completed operations and convert
# them to USD at published provider rates. usd_source is always
# 'provider_published_rate' — not a reconciled invoice. Callers must reconcile
# against provider billing statements before making a qualified cost claim.
# ---------------------------------------------------------------------------

RECEIPT_SCHEMA = 'urace-executor-receipt-v1'

# Published rates as of 2025-11. Update rate_effective when provider changes.
# source: anthropic.com/pricing, openai.com/api/pricing
PROVIDER_RATES: dict[str, dict] = {
    'claude-sonnet-4-6': {
        'input_usd_per_mtok': 3.00,
        'output_usd_per_mtok': 15.00,
        'cache_write_usd_per_mtok': 3.75,
        'cache_read_usd_per_mtok': 0.30,
        'provider': 'anthropic',
        'rate_source': 'anthropic.com/pricing',
        'rate_effective': '2025-11',
    },
    'claude-opus-4-7': {
        'input_usd_per_mtok': 15.00,
        'output_usd_per_mtok': 75.00,
        'cache_write_usd_per_mtok': 18.75,
        'cache_read_usd_per_mtok': 1.50,
        'provider': 'anthropic',
        'rate_source': 'anthropic.com/pricing',
        'rate_effective': '2025-11',
    },
    'claude-haiku-4-5-20251001': {
        'input_usd_per_mtok': 0.80,
        'output_usd_per_mtok': 4.00,
        'cache_write_usd_per_mtok': 1.00,
        'cache_read_usd_per_mtok': 0.08,
        'provider': 'anthropic',
        'rate_source': 'anthropic.com/pricing',
        'rate_effective': '2025-11',
    },
    'gpt-4o': {
        'input_usd_per_mtok': 2.50,
        'output_usd_per_mtok': 10.00,
        'cache_write_usd_per_mtok': 0.0,
        'cache_read_usd_per_mtok': 1.25,
        'provider': 'openai',
        'rate_source': 'openai.com/api/pricing',
        'rate_effective': '2025-11',
    },
    'gpt-4o-mini': {
        'input_usd_per_mtok': 0.15,
        'output_usd_per_mtok': 0.60,
        'cache_write_usd_per_mtok': 0.0,
        'cache_read_usd_per_mtok': 0.075,
        'provider': 'openai',
        'rate_source': 'openai.com/api/pricing',
        'rate_effective': '2025-11',
    },
}


def usd_from_tokens(
    model: str,
    input_tokens: int,
    output_tokens: int,
    *,
    cache_write_tokens: int = 0,
    cache_read_tokens: int = 0,
) -> tuple[float, dict]:
    """Return (usd_observed, rate_snapshot) using published provider rates.

    Raises ValueError for unknown models; add them to PROVIDER_RATES.
    """
    if not isinstance(input_tokens, int) or input_tokens < 0:
        raise ValueError('input_tokens must be a non-negative int')
    if not isinstance(output_tokens, int) or output_tokens < 0:
        raise ValueError('output_tokens must be a non-negative int')
    rates = PROVIDER_RATES.get(model)
    if rates is None:
        raise ValueError(f'No published rate for model {model!r}; add it to PROVIDER_RATES')
    usd = (
        input_tokens * rates['input_usd_per_mtok'] / 1_000_000
        + output_tokens * rates['output_usd_per_mtok'] / 1_000_000
        + cache_write_tokens * rates['cache_write_usd_per_mtok'] / 1_000_000
        + cache_read_tokens * rates['cache_read_usd_per_mtok'] / 1_000_000
    )
    snapshot = {
        'model': model,
        'input_usd_per_mtok': rates['input_usd_per_mtok'],
        'output_usd_per_mtok': rates['output_usd_per_mtok'],
        'cache_write_usd_per_mtok': rates['cache_write_usd_per_mtok'],
        'cache_read_usd_per_mtok': rates['cache_read_usd_per_mtok'],
        'provider': rates['provider'],
        'rate_source': rates['rate_source'],
        'rate_effective': rates['rate_effective'],
    }
    return round(usd, 10), snapshot


def _extract_model_from_transport(transport_usage: list) -> str | None:
    """Walk transport_usage receipts to find the first named model."""
    for t in transport_usage:
        if not isinstance(t, dict):
            continue
        inner = t.get('usage', {})
        if isinstance(inner, dict):
            models = inner.get('models', {})
            if isinstance(models, dict) and models:
                return next(iter(models))
    return None


def receipt_from_operation(operation: dict) -> dict | None:
    """Extract an executor receipt from a completed operation's usage metadata.

    Returns None if usage is absent or token counts are unavailable.
    The returned dict has schema RECEIPT_SCHEMA and is ready for store_receipt().
    """
    import time as _time
    usage = operation.get('usage')
    if not isinstance(usage, dict):
        return None
    input_tokens = usage.get('input_tokens')
    output_tokens = usage.get('output_tokens')
    if not (isinstance(input_tokens, int) and input_tokens >= 0
            and isinstance(output_tokens, int) and output_tokens >= 0):
        return None
    cache_read = usage.get('cached_input_tokens') or 0
    if not isinstance(cache_read, int):
        cache_read = 0

    model = _extract_model_from_transport(
        usage.get('transport_usage') if isinstance(usage.get('transport_usage'), list) else []
    )

    reported_cost = usage.get('reported_cost_usd')
    receipt: dict = {
        'schema': RECEIPT_SCHEMA,
        'operation_id': operation.get('id', ''),
        'arm': 'direct_executor',
        'input_tokens': input_tokens,
        'output_tokens': output_tokens,
        'cache_read_tokens': cache_read,
        'model': model or 'unknown',
        'captured_at': int(_time.time()),
    }
    if model and model in PROVIDER_RATES:
        usd, snapshot = usd_from_tokens(model, input_tokens, output_tokens,
                                        cache_read_tokens=cache_read)
        receipt['usd_observed'] = usd
        receipt['usd_source'] = 'provider_published_rate'
        receipt['rate_snapshot'] = snapshot
    elif isinstance(reported_cost, (int, float)):
        receipt['usd_observed'] = float(reported_cost)
        receipt['usd_source'] = 'executor_reported'
    else:
        receipt['usd_observed'] = None
        receipt['usd_source'] = 'unavailable'
    return receipt


def _receipts_dir(config: dict):
    from pathlib import Path
    from urace._common import state_path
    return state_path(config).parent / 'receipts'


def store_receipt(config: dict, receipt: dict):
    """Write receipt to state/receipts/receipt_{operation_id}.json."""
    import json
    d = _receipts_dir(config)
    d.mkdir(parents=True, exist_ok=True)
    op_id = receipt.get('operation_id', 'unknown')
    path = d / f'receipt_{op_id}.json'
    path.write_bytes(json.dumps(receipt, indent=2, allow_nan=False).encode())
    return path


def _parse_since_ts(since: str) -> int:
    from datetime import datetime, timezone
    try:
        dt = datetime.fromisoformat(since)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp())
    except ValueError:
        return 0


def load_receipts(config: dict, *, since: str | None = None,
                  limit: int | None = None) -> list[dict]:
    """Load receipts from state/receipts/, newest first."""
    import json
    d = _receipts_dir(config)
    if not d.exists():
        return []
    since_ts = _parse_since_ts(since) if since else 0
    out: list[dict] = []
    for path in sorted(d.glob('receipt_*.json'), reverse=True):
        try:
            r = json.loads(path.read_text(encoding='utf-8'))
        except Exception:
            continue
        if r.get('schema') != RECEIPT_SCHEMA:
            continue
        if since_ts and (r.get('captured_at') or 0) < since_ts:
            continue
        out.append(r)
        if limit and len(out) >= limit:
            break
    return out


def summarize_receipts(receipts: list[dict]) -> dict:
    """Aggregate token counts and USD totals across a list of receipts."""
    total_input = sum(r.get('input_tokens') or 0 for r in receipts)
    total_output = sum(r.get('output_tokens') or 0 for r in receipts)
    total_cache = sum(r.get('cache_read_tokens') or 0 for r in receipts)
    all_usd = [r['usd_observed'] for r in receipts
               if isinstance(r.get('usd_observed'), (int, float))]
    provider_rate_usd = [r['usd_observed'] for r in receipts
                         if r.get('usd_source') == 'provider_published_rate'
                         and isinstance(r.get('usd_observed'), (int, float))]
    models: dict[str, int] = {}
    for r in receipts:
        m = r.get('model', 'unknown')
        models[m] = models.get(m, 0) + 1
    return {
        'receipt_count': len(receipts),
        'total_input_tokens': total_input,
        'total_output_tokens': total_output,
        'total_cache_read_tokens': total_cache,
        'usd_total': round(sum(all_usd), 6) if all_usd else None,
        'usd_provider_rate_total': round(sum(provider_rate_usd), 6) if provider_rate_usd else None,
        'models': models,
        'usd_source_note': (
            'provider_published_rate = published per-token price, not reconciled invoice; '
            'reconcile against provider billing for a defensible cost claim'
        ),
    }
