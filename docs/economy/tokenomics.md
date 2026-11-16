# Token Economics

[← Documentation](../index.md) · [Price Mechanics](price-mechanics.md) · [Node Rewards](../economy/node-rewards.md) · [Spec](../spec/runtime.md)

URACE uses a dual-layer economic model: UCR tokens (economic participation) and consensus weights (reputation/trust). The two layers are intentionally independent — recalibrating earn amounts never affects reputation scoring, and changing consensus weights never affects token balances.

---

## Terminology: UCR Token vs Consensus Weight (Two Independent Layers)

**UCR token** — economic participation layer
- 1 UCR = 100,000,000 base units (8 decimals). `UNIT = 100_000_000`.
- Earned via: PoQ work, delivery, service, asset royalty → tagged `rep_source: 'work'`
- Acquired via: purchase/transfer → tagged `rep_source: 'trade'`
- `earned_balance()` = raw UCR sum (all provenance); never weighted
- When sold on-chain: seller's work-source balance decremented, buyer receives trade-tagged UCR

**Consensus weight** — reputation/trust layer
- `weighted_rep_score()` = Σ event_count × CONSENSUS_WEIGHTS[direction] (event-count based, not amount-based)
- Completely immune to UCR amount changes — recalibrating earn amounts has zero consensus effect
- 5 categories: quality, delivery, service, validation, longevity
- Not buyable: purchasing UCR has zero effect on consensus weight
- Used for: validator weight, bid ranking, governance votes

**Earned UCR vs Traded UCR** — provenance tags
- `rep_source: 'work'` = earned via genuine contribution → consensus-eligible
- `rep_source: 'trade'` = acquired via purchase/transfer → never consensus-eligible
- Both are fungible UCR on-chain; display always shows them separately

---

## Structural Concerns Resolved (P1–P5)

| Problem | Root Cause | Fix |
|---------|-----------|-----|
| P1: Service rewards 8 orders of magnitude too low | Config values in raw base units; borrow costs in token scale | seal/relay/llm defaults → 0.01–0.02 UCR (1M–2M base units) |
| P2: Bidirectional recalibration coupling | `weighted_rep_score` mixed amounts × weights | Decouple: `CONSENSUS_WEIGHTS` event-count based; `earned_balance()` raw sum only |
| P3: Flat 70% borrow ceiling scale-unaware | Single ceiling ignores micro-feature economics | Tiered 5%/8%/12%/10% by LOC scale |
| P4: Baseline grant Sybil amplification | 3 UCR unconditional → extract 3t×N | Provisional locked grant: usable only as stake, unlocked 1 UCR per delivery |
| P5: Out-of-P2P costs baked as constants | Tokenomics recalibration needed on each impl change | `BorrowCostContext` adapter: out-of-P2P costs measured at runtime; tokenomics stable |

---

## Token Genesis — How UCR Enters Circulation

**Three token creation paths:**
1. **Protocol reward events** (new UCR minted): `seal_reward`, `relay_reward`, `bootstrap_reward`, `llm_peer_reward`, PoQ `earn`, `challenge_bounty`, `provenance_compensation`
2. **Stake releases** (locked UCR returned): `mint_stake_released`, `challenge_stake_returned`
3. **Redistribution** (zero net supply change): `delivery_fee`, `asset_royalty`, `borrow_earn`, `escrow_custody_earned`

**Deflationary sinks:**
- `borrow_tax` → treasury (15% per borrow, recycled to rewards)
- `cartel_chunk_penalty` → treasury
- `decay` above BASE_CAP (50 UCR, 1%/day above cap) → burned
- Slashed stakes → treasury (never returned)

**Supply growth rate controlled by:**
- BASE_CAP (50 UCR/peer work-source) + decay 1%/day above cap
- PoQ quality gate: failed features produce no UCR

---

## Stage Definitions

| Stage | Nodes | Infra floor (seal+relay, illustrative) | Ref UCR price (illustrative) |
|-------|-------|-----------------------------------------|-------------------------------|
| Bootstrap | <100 | 1.50 UCR/day | $0.05 |
| Growth | 100–1,000 | 0.75 UCR/day | $0.50 |
| Scale | 1,000–50,000 | 0.25 UCR/day | $5.00 |
| Mature | >50,000 | flat base rate | $50.00 |

Protocol reward amounts are flat constants (`config.json`). Stage-based multipliers are not yet implemented — all stages currently use Mature (1×) base rates.

---

## Earn Method Glossary

| Method | Who earns | Effort type | Description |
|--------|-----------|-------------|-------------|
| `seal_reward` | Node operator | Passive-auto | System pays full-node operators per ledger block sealed |
| `relay_reward` | Relay operator | Passive-auto | System pays relay/bootstrap nodes per routed connection |
| `bootstrap_reward` | Bootstrap node | Passive-auto | System pays bootstrapper per new peer connected |
| `llm_peer_reward` | LLM peer | Passive-auto | System pays LLM quality-check node per verified work unit |
| `asset_royalty` | Feature owner | Passive-auto | Owner earns per borrow of their feature by another peer |
| `borrow_earn` | Borrower | Action-triggered | Small rebate for choosing P2P over direct executor |
| `delivery_fee` | Deliverer | Agent-auto | % of borrow cost on accepted delivery (daemon bids autonomously) |
| `challenge_bounty` | Challenger | Agent-auto | 50% of stake returned + bonus if challenge upheld; daemon auto-files |
| PoQ `earn` | Creator | High-effort | Credits on quality-verification acceptance of submitted feature |
| `baseline_grant_locked` | New peer | Conditional unlock | 3 UCR locked; usable as stake; unlocked 1 UCR per accepted delivery |

---

## Section A — Network Infrastructure (Passive-auto)

Flat base rates (from `config.json`). Stage-based multipliers are not yet implemented.

| Direction | Task | UCR/event | Base units | Consensus wt |
|-----------|------|-----------|------------|--------------|
| `seal_reward` | Seal ledger block (5-min cycle) | 0.0100 | 1,000,000 | 0.80 |
| `relay_reward` | Route P2P connection | 0.0100 | 1,000,000 | 0.80 |
| `bootstrap_reward` | Bootstrap new peer | 0.0150 | 1,500,000 | 0.75 |
| `llm_peer_reward` | LLM quality-verify work unit | 0.0200 | 2,000,000 | 0.70 |

**Illustrative daily UCR per full-stack infra node at current flat rates** (Ref UCR price from Stage Definitions):

| Stage | Seals (288/day) | Relay | Bootstrap | LLM | Total UCR/day | USD/day (illustrative) |
|-------|----------------|-------|-----------|-----|--------------|----------------------|
| Bootstrap ($0.05) | 288×0.010=2.9 | 50×0.010=0.5 | 5×0.015=0.1 | 10×0.020=0.2 | **3.7** | **$0.18** |
| Growth ($0.50) | 288×0.010=2.9 | 500×0.010=5.0 | 30×0.015=0.5 | 50×0.020=1.0 | **9.4** | **$4.70** |
| Mature ($50.00) | 288×0.010=2.9 | 5000×0.010=50.0 | 200×0.015=3.0 | 500×0.020=10.0 | **65.9** | **$3,295** |

→ [Node Rewards](../economy/node-rewards.md) for per-role daily breakdown.

---

## Section B — Asset Royalties (Passive-auto after creation)

Royalty = borrow_cost = ceiling × executor_reference (1.2 UCR default). Self-borrow blocked.

| Feature scale | LOC | Ceiling | Royalty/borrow | 1,000-borrow lifetime |
|--------------|-----|---------|----------------|----------------------|
| Micro | 1–50 | 5% | 0.0600 UCR | 60 UCR |
| Standard | 51–500 | 8% | 0.0960 UCR | 96 UCR |
| Large | 501+ | 12% | 0.1440 UCR | 144 UCR |
| Bundle (total) | any | 10% | 0.1200 UCR | 120 UCR split |

→ [Features: Mint, Borrow, and Trade](../power-users/exchange-features.md) for asset lifecycle.

---

## Section C — Borrower Cost (demand side)

| Feature scale | Borrow cost | Tax 15% | Rebate 5% | Net paid | vs Executor 1.2 UCR | Savings |
|--------------|-------------|---------|-----------|----------|---------------------|---------|
| Micro (5%) | 0.0600 | 0.0090 | −0.0030 | **0.0660 UCR** | 1.2 UCR | **94.5%** |
| Standard (8%) | 0.0960 | 0.0144 | −0.0048 | **0.1056 UCR** | 1.2 UCR | **91.2%** |
| Large (12%) | 0.1440 | 0.0216 | −0.0072 | **0.1584 UCR** | 1.2 UCR | **86.8%** |
| Bundle (10%) | 0.1200 | 0.0180 | −0.0060 | **0.1320 UCR** | 1.2 UCR | **89.0%** |

**Including BorrowCostContext pre-borrow overhead:**

| Routing state | Overhead | Micro total | Savings | Large total | Savings |
|--------------|----------|-------------|---------|-------------|---------|
| Optimised (1 LLM peer, 0.040 UCR) | 0.040 | 0.106 | **91.2%** | 0.198 | **83.5%** |
| Today (3 executor calls, 0.120 UCR) | 0.120 | 0.186 | **84.5%** | 0.278 | **76.8%** |
| Slow (5 calls, 0.200 UCR) | 0.200 | 0.266 | **77.8%** | 0.358 | **70.2%** |

→ [Price Mechanics](price-mechanics.md) for ceiling computation detail.

---

## Section D — Work Market (Agent-auto)

**D1 — Delivery Fee** (10% × (executor_ref − total_borrow_cost_used), consensus wt = 0.90):

| Job type | Borrow cost | delivery_fee | USD-A | USD-B |
|----------|-------------|-------------|-------|-------|
| Micro job (2 micro) | 0.120 UCR | **0.108 UCR** | $0.108 | $1.08 |
| Standard job (3 std) | 0.288 UCR | **0.091 UCR** | $0.091 | $0.91 |
| Complex (2L + 1 bundle) | 0.408 UCR | **0.079 UCR** | $0.079 | $0.79 |

**D2 — Escrow Custody** (3% of job budget, consensus wt = 0.30):

| Job budget | Custody fee (3%) | Capital locked | Net yield % |
|-----------|-----------------|---------------|-------------|
| 1.2 UCR (std job) | **0.036 UCR** | 1.2 UCR | 3.0% |

→ [Work Market](../power-users/work-market.md) for job lifecycle and escrow mechanics.

---

## Section E — Security/Governance (Agent-auto)

**E1 — Challenge Bounty** (50% of stake returned on upheld challenge, consensus wt = 0.90):

| Scale | Stake required | Upheld: net bounty | USD-A | USD-B |
|-------|--------------|-------------------|-------|-------|
| Small | 0.10 UCR | **0.05 UCR** | $0.050 | $0.50 |
| Medium | 0.50 UCR | **0.25 UCR** | $0.250 | $2.50 |
| Large | 2.00 UCR | **1.00 UCR** | $1.000 | $10.00 |

**E2 — Provenance Compensation** (from thief's slashed stake, consensus wt = 0.60):

| Theft scale | Compensation received | USD-A | USD-B |
|------------|----------------------|-------|-------|
| Minor | 0.10–0.50 UCR | $0.10–$0.50 | $1–$5 |
| Moderate | 0.50–2.00 UCR | $0.50–$2.00 | $5–$20 |
| Major | 2.00–10.00 UCR | $2–$10 | $20–$100 |

→ [Sharing Safeguards](../power-users/sharing-safeguards.md) for cartel detection and sybil gate.

---

## Section F — PoQ Creation (High-effort setup)

One-time earn on quality-verified acceptance. `direction: 'earn'`. Consensus wt = 1.00 (highest).

| Feature scale | LOC | PoQ earn | USD-A | USD-B | Lifetime royalty (1,000 borrows) |
|--------------|-----|----------|-------|-------|----------------------------------|
| Micro | 1–50 | 0.10–0.50 UCR | $0.10–$0.50 | $1–$5 | 60 UCR ($60/$600) |
| Standard | 51–500 | 0.50–2.00 UCR | $0.50–$2 | $5–$20 | 96 UCR ($96/$960) |
| Large | 501+ | 2.00–8.00 UCR | $2–$8 | $20–$80 | 144 UCR ($144/$1,440) |

---

## Section G — Financial/Trade (Trade-source, not consensus-eligible)

| Direction | Event | Consensus wt | Notes |
|-----------|-------|-------------|-------|
| `purchase_receive` | Buy UCR | 0.00 | Trade-tagged; never earns consensus |
| `rep_transfer_in` | Receive sold earned rep | 0.00 | Reclassified permanently as trade-source |

---

## Section H — Onboarding: Provisional Grant

| Direction | UCR | Condition | Notes |
|-----------|-----|-----------|-------|
| `baseline_grant_locked` | 3.00 locked | — | Stake-only; not transferable |
| Unlock per delivery | 1.00 freed | Per accepted delivery | Up to 3.00 UCR total |
| Fully unlocked | 3.00 | After 3 deliveries | Liquid work-source UCR |

The grant is locked at creation and can only be used as stake for a first bid. It unlocks 1 UCR per accepted delivery. This eliminates the Sybil-farming vector where N wallets could extract 3t×N free tokens.

---

## Section I — Stake Mechanics (return, not earn)

| Direction | Event | Amount returned | Notes |
|-----------|-------|----------------|-------|
| `mint_stake_released` | Feature accepted after challenge window | = staked amount | Typical stake: 1–10 UCR |
| `challenge_stake_returned` | Challenge upheld | = staked amount | Returned alongside bounty |

---

## Section J — Debit Paths (penalties / fees)

| Direction | Trigger | Amount | Purpose |
|-----------|---------|--------|---------|
| `borrow_tax` | Per borrow | 15% of borrow_cost | Anti-inflation treasury |
| `mint_stake_locked` | Submit feature | 1–10 UCR | Collateral; returned on acceptance |
| `mint_stake_slashed` | Challenge upheld against you | = stake | Penalty for fraudulent feature |
| `cartel_chunk_penalty` | Cartel detection | proportional to excess | Excess earn clawed back |
| `decay` | Balance above BASE_CAP (50 UCR) | 1%/period above cap | Prevents hoarding |

---

## Section K — Full Role Comparison by Stage

| Role | Bootstrap $/day | Growth $/day | Scale $/day | Mature $/day |
|------|-----------------|-------------|-------------|--------------|
| Full-stack infra node | **$0.91** | **$14.0** | **$213** | **$3,295** |
| Popular micro asset owner (500 borrows/day) | $0.006 | $1.80 | $45 | $1,500 |
| Bundle component (25% LOC, 100 borrows/day) | $0.0015 | $0.15 | $1.50 | $75 |
| Autonomous deliverer (200 jobs/day) | $0.009 | $0.48 | $23.75 | $950 |
| Escrow holder (50 jobs/day) | $0.0018 | $0.18 | $4.50 | $900 |
| Auto challenger (30 upheld/day, med stake) | $0.031 | $0.75 | $18.75 | $375 |
| PoQ creator (1 micro/week) | $0.075/wk | $0.45/wk | $2.25/wk | $15/wk |
| **Full-stack autonomous agent** | **~$0.96** | **~$17.2** | **~$306** | **~$6,120** |

---

## Section L — System Balance Verification

| Property | Value | Verdict |
|----------|-------|---------|
| P2P savings floor (worst routing, slow 5 calls) | 70.2% | Always strongly favours P2P |
| P2P savings ceiling (optimised, 1 LLM peer) | 94.5% | Micro features extremely cheap |
| Infra vs delivery @ Bootstrap | 18.3 vs 0.19 UCR/day | Relay ~96× — infra dominant early |
| Infra vs delivery @ Mature | 65.9 vs 19 UCR/day | Market evens out at scale |
| Asset royalty at 10 borrows | 0.60 UCR | Reliable at 10+; exponential at 1,000+ |
| Sybil grant cost | 3 deliveries required | Net effort > 3 UCR → unprofitable |
| Full-stack autonomous daily range | Bootstrap $0.96 → Mature $6,120 | Viable at every stage |
| Consensus weight ordering | earn 1.00 → delivery/challenge 0.90 → seal/relay 0.80 → bootstrap 0.75 → llm 0.70 → referral/provenance 0.60 → borrow 0.40 → escrow 0.30 → trade 0.00 | Reflects contribution depth |
| Supply growth rate | Decelerates Bootstrap→Mature | Stage multipliers naturally throttle inflation |
| Treasury recycling | borrow_tax (15%) + decay + slashes | Net supply growth ≈ genuine contribution value |

---

## CONSENSUS_WEIGHTS Reference

```python
CONSENSUS_WEIGHTS = {
    'earn':                    1.00,
    'delivery_fee':            0.90,
    'challenge_bounty':        0.90,
    'seal_reward':             0.80,
    'relay_reward':            0.80,
    'bootstrap_reward':        0.75,
    'llm_peer_reward':         0.70,
    'composition_referral':    0.60,
    'provenance_compensation': 0.60,
    'borrow_earn':             0.40,
    'escrow_custody_earned':   0.30,
    'baseline_grant_locked':   0.00,
    # trade-source: always 0.00
}
```

Source: `urace/runtime/urace/credit_ledger.py` — `CONSENSUS_WEIGHTS` dict.

---

## BorrowCostContext Usage

```python
from urace.cost_model import BorrowCostContext, borrow_feature_cost

ctx = BorrowCostContext(
    executor_calls=3,              # LLM routing/classification calls made
    executor_cost_per_call=0.04,   # from config.p2p.executor_reference_price_per_unit / 30
    cycles_cost=0.0,               # local CPU/inference
    mitm_cost=0.0,                 # human review time (0 in auto mode)
)
result = borrow_feature_cost(config, borrow_cost_units, loc=50, borrow_ctx=ctx)
# result keys: borrow_tax_units, scale_tier, ceiling_ratio, ceiling_compliant,
#              savings_vs_executor_pct, total_with_overhead
```

Routing improvement is the key multiplier: 5 calls → 1 call reduces pre-borrow overhead by 80%. Tokenomics (ceilings, weights, amounts) never change when routing improves.

→ [Reputation](../power-users/exchange-reputation.md) for how consensus weight affects peer ranking.

---
→ [Next: Price Mechanics](price-mechanics.md) — executor ceiling, momentum guard, wash trading rules
