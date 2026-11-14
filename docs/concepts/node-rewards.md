# Node Rewards

[← Documentation](../index.md)

Every node role that contributes real work earns tokens. Rewards are funded by a 2% protocol fee on every fill — not inflation.

---

## All reward roles

| Role | `CREDIT_DELTA` direction | Trigger |
|------|--------------------------|---------|
| Creator/Minter | `earn` | Peer borrows the feature |
| Borrower | `spend` | Fills a listing |
| Delivery node (replica seeder) | `delivery_fee` | Delivers artifact chunks; proportional to delivery count |
| Composition component owner | `composition_referral` | Derivative feature is listed; dynamic multi-level split |
| Challenger | `challenge_bounty` | APS challenge succeeds |
| Challenger (failed) | `challenge_stake_locked` | Stake locked on failed challenge |
| Base/original owner | `provenance_compensation` | Derivative feature earns on the market |
| Ledger block sealer | `seal_reward` | Seals a LEDGER_BLOCK; default 1 unit; config: `seal_reward_units` |
| LLM similarity peer | `llm_peer_reward` | Delivers SIMILARITY_VERDICT; default 2 units; config: `llm_peer_reward_units`; deduped per checker per feature |
| Protocol treasury | `protocol_fee` | 2% of fill price; funds seal + LLM rewards |
| Hired node (work market) | `escrow_release` | Win a bid on the work market, deliver verified work, receive credits |
| Hired node (custody bonus) | `escrow_custody_earned` | 3% of contract budget credited on verified delivery; proportional per hired node |
| Relay node | `RELAY_CREDIT_ISSUED` | Routes a P2P connection hop; rate = `relay_credit_per_kb` (default 1 unit/KB) |
| Bootstrap node | `BOOTSTRAP_CREDIT_ISSUED` | Facilitates a new peer connection; rate = `bootstrap_credit_per_connection` (default 5 units) |

Routing is built into every node — no dedicated routing tier, no routing reward. Cost is negligible; a routing reward would be trivially gamed by Sybil flooding fake `find_node` queries.

Relay and bootstrap credits are off-chain ledger entries. They become redeemable on-chain only after the URACE ERC-20 contract is deployed and `token_settlement=true` is configured (see [Token Deployment](../economics/token-deployment.md)).

---

## Creator earn — how the amount is computed

When a peer fills a listing, the creator's earn is computed at fill time by `mint_per_adoption()` and stored in the `credit_units` field of the `FEATURE_BORROWED` audit row. The amount is never flat — it scales with network conditions:

```
earn = base_earn × trust_mult × novelty × post_sat × rep_bonus × epoch_decay × supply_mult × derivative_pen
```

| Factor | Description | Range |
|--------|-------------|-------|
| `base_earn` | `feature_complexity × UNIT ÷ 2` — LOC × deps × tests | Scales with feature size |
| `novelty` | `1 / (1 + log2(adoption_rank))` — first adopters earn most | 1.0 → ~0 |
| `post_sat` | `0.85^(rank − n_sat)` after saturation threshold | 1.0 → ~0 |
| `n_sat` | `ceil(0.30 × network_size)` — saturation starts at 30% adoption | Scales with network |
| `supply_mult` | `max(0.001, 1 − (total_supply / physics_ceiling)²)` | 1.0 → 0.001 |
| `epoch_decay` | `0.99^epochs_elapsed` — older features earn slightly less | Decays over time |
| `trust_mult` | `0.5 + 0.5 × adopter_trust` — high-rep borrowers generate more | 0.5–1.0 |
| `rep_bonus` | Wilson-based stackable bonus, up to 1.4× at 4 quality tiers | 1.0–1.4 |
| `derivative_pen` | Smooth penalty for near-duplicate features (Jaccard overlap) | 0.3–1.0 |

Same-peer repeat borrows store `credit_units = 0` — creator earns nothing on reborrow from the same node.

Cross-peer earning is now gated on a signed trial receipt: after the borrower's local qualification passes, `trial_receipt.py` creates a signed receipt (`create_receipt`) delivered to the creator peer (`deliver_receipt`). The creator's `token_ledger.balance()` only counts `receipt_verified=True` events when `token_settlement=True`. The `FEATURE_BORROW_VERIFIED` audit row is emitted when a valid cross-peer receipt arrives.

The earn floor is always 1 base unit (never exactly zero) unless the governance ceiling is hit.

---

## Protocol fee treasury

```
protocol_fee = fill_price × 0.02
CREDIT_DELTA(direction='protocol_fee', peer='__protocol__')
```

The `__protocol__` account funds `seal_reward` and `llm_peer_reward` payouts. The treasury cannot go negative — rewards are only emitted when the fee has been collected.

---

## Delivery fee split

When multiple replica holders deliver chunks of the same feature, the fee is split proportionally:

```
delivery_fee_i = total_fee × (deliveries_i / sum(deliveries))
```

Tracked in `delivery_graph.py`. Each seeder gets a `CREDIT_DELTA(direction='delivery_fee')` row.

---

## Config knobs

| Key | Default | Effect |
|-----|---------|--------|
| `seal_reward_units` | `1` | Units awarded per sealed ledger block |
| `llm_peer_reward_units` | `2` | Units awarded per SIMILARITY_VERDICT |
| `protocol_fee_fraction` | `0.02` | Fraction of fill price to treasury |

---

## Hired node (work market)

Any node can bid on open work requests posted to the work market. When a requester accepts your bid and you deliver verified work, the escrowed credits are released to you. If multiple nodes split a job, each receives a share proportional to their agreed equity split.

Steps to earn as a hired node:

1. Browse open work requests on the market.
2. Submit a bid (requires meeting the requester's minimum combined reputation).
3. Deliver your work artifact once your bid is accepted.
4. After the requester verifies delivery, your credit balance increases automatically.

No trust setup is required beyond your existing node identity and reputation score.

→ [Token economy overview](../economics/tokenomics.md)
