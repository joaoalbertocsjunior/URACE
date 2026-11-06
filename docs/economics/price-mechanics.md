# Price Mechanics

[← Documentation](../index.md)

URACE enforces several pricing rules to keep the marketplace fair, prevent manipulation, and ensure borrowers always save money vs. building from scratch.

---

## Executor Price Ceiling

Every feature minted to the P2P network must declare an `executor_reference_price_units` — the cost to build that feature from scratch using an executor.

**The full ceiling formula:**

```
ask_price ≤ (executor_reference_price − gas_overhead) × completeness × (1 − margin) − iter_savings
```

| Term | Description |
|------|-------------|
| `executor_reference_price` | Derived from median fills in the local ledger (last 90 days); floor: 10 units |
| `gas_overhead` | On-chain transaction cost in URACE units; deducted first so the buyer's total cost always stays below executor cost |
| `completeness` | Bundle completeness score 0.0–1.0 (see table below) |
| `margin` | Seller profit margin as a fraction (e.g. 0.20 = 20%) |
| `iter_savings` | `avg_saved_iterations × executor_per_call_cost` — verified implementations skip N executor re-runs |

This guarantee means: if you can get a feature from a peer, it is always cheaper than having an executor build it. Buyers always save money.

**`gas_overhead` resolution (priority order):**
1. Dynamic EVM: `gas_per_tx_gwei × gas_price_gwei × urace_units_per_gwei` (all three > 0)
2. Static override: `gas_overhead_units` config key
3. Default: `0` (off-chain / account-abstraction sponsored)

When listing a feature for sale:

```sh
urace exchange equity list-for-sale <feature-id> --bp 5000 --price 80
```

URACE validates that `--price` does not exceed the ceiling at listing time. The validation is enforced again at fill time via `vs_executor_comparison()`.

---

## Multi-Buyer Revenue Model

Sellers earn from **volume**, not markup. If you build a feature for 100 tokens executor cost and list it at 80 tokens borrow price:

| Scenario | Revenue |
|----------|---------|
| 1 buyer | 80 tokens |
| 10 buyers | 800 tokens |
| 100 buyers | 8,000 tokens |

The network distributes your creation cost across all adopters. With 10 buyers you've already earned 8× your original cost. This is the core incentive for minting: your work keeps earning.

---

## Price Momentum Guard

Ask prices cannot spike more than **1.5× the 7-day median** of recent sales for that feature.

If the 7-day median is 80 tokens, the maximum new ask is 120 tokens. This prevents pump-and-dump price manipulation while still allowing legitimate appreciation driven by real demand.

---

## Wash Trading Prevention

Buying and selling the same feature within **24 hours** is blocked as wash trading.

Economic activity must represent real adoption — not circular self-dealing designed to inflate volume or price signals.

---

## Basis Points (bp) and Equity Stakes

Equity in a feature is expressed in basis points:

| bp | Percentage |
|----|-----------|
| 100 | 1% |
| 1000 | 10% |
| 5000 | 50% |
| 10000 | 100% |

Multiple peers can hold equity in a single feature. Earnings from borrows are distributed proportionally.

Feature equity is capped at 10,000 bp total — no feature can have more than 100% equity granted.

---

## Governance Supply Ceiling

`max_mintable_units(N)` sets the maximum total creator-earn supply allowed for a network of `N` peers:

```
max_mintable_units(N) = max(BASE_CAP_UNITS × 10,  BASE_CAP_UNITS × N × 5)
```

At fill time, if `total_network_supply ≥ max_mintable_units(estimated_network_size)`, creator earn floors at 1 base unit instead of 0 — supply is choked softly, not hard-stopped.

| Network | Ceiling |
|---------|---------|
| N = 1 (bootstrap) | 500 tokens |
| N = 100 | 25,000 tokens |
| N = 1,000 | 250,000 tokens |
| N = 10,000 | 2,500,000 tokens |

This ceiling grows linearly with network size and is distinct from the physics-derived `supply_pressure_multiplier` (which activates much earlier via a quadratic curve). Both are enforced simultaneously.

---

## Feature Saturation

As adoption grows, marginal value of additional equity decreases:

```sh
urace exchange compact depletion <feature-id>
```

When most peers already have a feature, the pool of potential new adopters shrinks. Use saturation data to time your equity listings.

---

## Related

- [Tokenomics](tokenomics.md) — full token supply model
- [Features](../exchange/features.md) — how to list and borrow
- [Security Overview](../security/overview.md) — market integrity guarantees
