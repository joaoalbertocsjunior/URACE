# Price Mechanics

[← Documentation](../index.md)

URACE exposes pricing estimates and transaction controls. Current price metadata does not prove that a borrower saves money versus building from scratch.

---

## Configured Reference Estimate

An `executor_reference_price_units` value is an owner supplied estimate. A marketplace fill price or reputation reward is not an executor cost baseline. Cost savings are qualified only when task matched executor receipts and P2P acquisition, integration, validation, and residual executor costs are recorded in the same cost unit.

When configured, the listing path may apply this estimate-based ceiling:

```
ask_price ≤ (executor_reference_price − gas_overhead) × completeness × (1 − margin) − iter_savings
```

| Term | Description |
|------|-------------|
| `executor_reference_price` | Owner-configured estimate; sale fills and reward credits are not used as executor-cost observations |
| `gas_overhead` | Estimated transaction overhead in URACE units; subtracting it does not establish that total buyer cost is below executor cost |
| `completeness` | Bundle completeness score 0.0–1.0 (see table below) |
| `margin` | Seller profit margin as a fraction (e.g. 0.20 = 20%) |
| `iter_savings` | `avg_saved_iterations × executor_per_call_cost` — verified implementations skip N executor re-runs |

This formula is a pricing heuristic, not a savings guarantee. The comparison remains unqualified when the baseline or any material cost is unknown. A cost advantage alone does not prove equivalent accepted value.

### P2P cost qualification gate

Listing prices capped against an owner estimate place an upper bound on the ask, but they do not establish that a borrower saves money compared to direct executor work. A qualified savings claim requires a live cohort study: at least 30 measured pairs across 6 task families, both arms accepted in every pair, complete comparable USD costs recorded, zero URACE units paid, on-chain settlement active, and two independent reviewers signing the cohort using `trial/p2p_cost_claim_review.py`. Until that study is complete and signed, no savings claim is valid — P2P borrows have $0 provider cost to the borrower, but that is not savings evidence. See [Qualification Protocol](qualification-protocol.md) for the full requirements.

**`gas_overhead` resolution (priority order):**
1. Dynamic EVM: `gas_per_tx_gwei × gas_price_gwei × urace_units_per_gwei` (all three > 0)
2. Static override: `gas_overhead_units` config key
3. Default: `0` (off-chain / account-abstraction sponsored)

When listing a feature for sale:

```sh
urace exchange equity list-for-sale <feature-id> --bp 5000 --price 80
```

URACE may apply an estimate based ceiling when configured. Fill time records the comparison as unqualified until task matched cost receipts and independent acceptance are supplied.

---

## Multi-Buyer Revenue Model

Repeated use can distribute more reputation units to the seller. This illustration does not establish profit, monetary value, or a buyer's savings:

| Scenario | Revenue |
|----------|---------|
| 1 buyer | 80 tokens |
| 10 buyers | 800 tokens |
| 100 buyers | 8,000 tokens |

Ten fills at 80 URACE units produce 800 ledger units before fees. URACE units are not a verified reimbursement for executor charges or creator labor.

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
