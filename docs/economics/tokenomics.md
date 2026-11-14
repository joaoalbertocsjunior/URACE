# Tokenomics

[← Documentation](../index.md)

URACE tokens represent earned reputation from accepted quality improvements. They are not speculative assets — they are proof of verified contribution, used to access features on the P2P network and request work from peers.

---

## Token Definition

| Property | Value |
|----------|-------|
| Earn path | Quality gate pass (`score_delta > 0`) — one earn path only |
| Spend path | Borrow features from peers, commission work |
| Precision | 8 decimals (satoshi model: 1 token = 100,000,000 base units) |
| Baseline grant | 3 tokens per new peer — **locked until first quality gate pass** (Sybil resistance) |
| Trial borrow allowance | 1 free borrow before first quality pass — breaks cold-start chicken-and-egg |
| Deduplication | Exact copies blocked by `canonical_fingerprint`; near-copies by `outcome_fingerprint` |

---

## Supply Model

Supply is derived from network physics — not arbitrary. It is sized so all peers can sync the ledger within the target time window.

### Default Parameters (1,000 peers, 1 Mbps, 50 MB, 30s sync)

| Parameter | Value |
|-----------|-------|
| Effective ledger budget | min(50 MB, bandwidth × 30s) |
| Max unique features | 3,840 features |
| Avg adoptions per feature | 100 (10% of 1,000 peers) |
| Avg mint per adoption | 0.1 tokens (observed avg across all adoption ranks) |
| Supply from features | 3,840 × 100 × 0.1 = 38,400 tokens |
| Supply from baseline grants | 1,000 peers × 3 = 3,000 tokens |
| **Total network supply** | **~41,400 tokens** |
| Per-peer cap | ~41 tokens/peer (physics-optimal; BASE_CAP_UNITS = 50) |
| Supply-calc verdict | **OK** (within 20% of governance cap) |

### Physics Ceiling vs Governance Cap

Two separate constants govern supply:

| Constant | Value | Role |
|----------|-------|------|
| `PHYSICS_CAP_UNITS_PER_PEER` | 41 tokens | Supply pressure curve ceiling (infra-derived) |
| `BASE_CAP_UNITS` | 50 tokens | Per-peer balance cap (governance-adjustable) |

`BASE_CAP_UNITS` is an **epoch-adjustable governance parameter**. It is calibrated near the physics-optimal value at baseline infra (1 Mbps) and should be raised via governance as network infra improves. Run `supply-calc` to compute the optimal value for your infra tier.

### Supply Pressure Curve

`supply_pressure_multiplier` is anchored to `PHYSICS_CAP_UNITS_PER_PEER × network_size`, so it **activates at real-world supply levels**:

| Supply % of physics ceiling | Multiplier | Effect |
|----------------------------|-----------|--------|
| 0% | 1.000 | Full earn rate |
| 50% | 0.750 | 25% earn reduction |
| 90% | 0.190 | 81% earn reduction |
| 100% | 0.001 | Near-zero (cliff) |

At 1,000 peers (physics ceiling = 41,000 tokens), the curve activates around 20,000 tokens total supply.

### Supply Scales With Infra

| Infra | Max Features | Total Supply (physics) |
|-------|-------------|----------------------|
| 1 Mbps / 50 MB / 30s | 3,840 | ~41,400 tokens |
| 10 Mbps / 500 MB / 60s | 65,536 | ~688,000 tokens |
| 100 Mbps / 2 GB / 120s | 262,144 | ~2.75M tokens |
| 1 Gbps / 10 GB / 300s | 1,310,720 | ~13.8M tokens |

Supply scales with bandwidth, not peers. The constraint is always "can new peers sync the ledger?" — not an arbitrary cap. Large networks running on enterprise infra should raise `BASE_CAP_UNITS` via governance to match their infra tier.

---

## Initial Ledger

URACE ships with a pre-built initial ledger of **1,405 built-in features** — every atomic capability across all runtime and trial modules, CLI surfaces, exchange/P2P commands, and test contracts. Entries with an exact local runtime-module tag also pin source paths and file digests; these bindings identify local implementations but are not delivered artifacts or quality qualifications. All initial ledger features are:

- **Free-use**: borrow cost = 0 tokens
- **No owner**: minted without a creator, available to all peers
- **Discoverable**: searchable via `urace search --kind p2p` or `exchange compact search`
- **Auto-context**: used by `urace derive` and `urace freeform-text` without token cost

| Metric | Value |
|--------|-------|
| Initial features minted | 1,405 |
| Format | JSONL (`runtime/initial_ledger.jsonl`) — line 1 is a header, each subsequent line is one feature |
| Breakdown | mechanism · schema · contract · integration · protocol features |
| Revenue features | 65% (882 features with active token flow) |
| Free/decayed features | 35% (474 features — consume infra but generate no token flow) |
| Max features at 1 Mbps / 1,000 peers | 3,840 |
| Utilization at baseline infra | 35% |
| Room for user features at baseline | 2,470 additional features |
| Max features at 10 Mbps / 10,000 peers | 65,536 |
| Utilization at 10 Mbps | 2% |

### Revenue Feature Fraction

`revenue_feature_fraction = 0.65` — 35% of features are "free/decayed": they are available to all peers but generate no token flow. This models real-world feature churn (deprecated capabilities, infra-only helpers, transitional scaffolding). Supply calculations account for this fraction; the effective token-generating supply is 65% of the feature count.

Rebuild the ledger after adding modules:

```sh
cd runtime && python3 build_initial_ledger.py
```

---

## Epoch Calibration

Run `supply-calc` to check governance fit for your network:

```sh
# Baseline (1 Mbps, consumer hardware)
urace exchange ledger supply-calc --peers 1000 --ledger-mb 50
# → verdict=OK, per_peer_cap≈41 tokens, current_cap=50 tokens

# Large network (10 Mbps, enterprise)
urace exchange ledger supply-calc --peers 10000 --bandwidth-kbps 10000 --ledger-mb 500 --sync-secs 60
# → verdict=UNDERSUPPLIED → raise BASE_CAP_UNITS via governance to ~658 tokens/peer
```

Adjust `BASE_CAP_UNITS` in `credit_ledger.py` when your network has stable participation at a new infra tier.

---

## Crypto Bridge

URACE uses an 8-decimal internal representation (satoshi model) with a built-in bridge to EVM 18-decimal on-chain units for future cryptocurrency integration:

| Constant | Value | Description |
|----------|-------|-------------|
| `DECIMALS` | 8 | Internal precision |
| `UNIT` | 10^8 | 1 token in internal base units |
| `CHAIN_DECIMALS` | 18 | EVM standard (Ethereum, Polygon, etc.) |
| `CHAIN_UNIT` | 10^18 | 1 token in on-chain base units |
| `CHAIN_SCALE` | 10^10 | Multiply internal units by this for on-chain |

```python
from urace.credit_ledger import to_chain_units, from_chain_units, UNIT
# 1 token → EVM representation
on_chain = to_chain_units(UNIT)           # = 10^18
# EVM → internal
internal = from_chain_units(on_chain)     # = 10^8 (1 token)
```

All internal accounting uses integers (no float precision loss). On-chain conversion is lossless at 8 decimal places (10^10 scale factor has no fractional component).

---

## No Monetary Token Valuation

URACE ledger units are reputation and closed-network accounting units. They have no verified redemption value, market exchange rate, or proven equivalence to executor usage, developer labor, or fiat. Do not infer a token price or market capitalization by dividing estimated developer labor by reward units. P2P sale prices and `CREDIT_DELTA` reputation entries are not executor-cost measurements.

`urace_credit_usd_rate` (default: `1000` — meaning 1000 URACE base units = $1) is a **display-only accounting rate**. It is used exclusively for rendering USD-equivalent totals in cost reports and the settle status output. It does **not** set, imply, or anchor the market price of URACE tokens. Market price, if any, is determined by external DEX supply and demand after on-chain deployment. Set a custom display rate via:

```sh
urace exchange settings set --urace-credit-usd-rate <rate>
```

---

## Sybil Resistance

The bootstrap grant is **locked until a peer's first quality gate pass** — it cannot be farmed by creating throwaway peer identities.

| Attack | Defense |
|--------|---------|
| Create 100 fake peers → 300 free tokens | Grant = 0 until first APPLIED_AFTER_LOCAL_QUALIFICATION event |
| Use 1 trial borrow per fake peer | Trial borrow allowance = 1 (configurable); exhausted after 1 use, no more without quality pass |
| Misstate executor reference prices | Do not treat self-reported estimates or reputation credits as cost evidence; no price-consensus penalty is applied |

The cold-start path for a **legitimate new peer**:
1. Join network → get 1 trial borrow (free, no quality pass needed)
2. Borrow a feature, integrate it, improve your product
3. Quality gate pass → bootstrap grant unlocks (3 tokens) + score_delta earns
4. Borrow more with earned tokens

---

## Delivery Fee Model

When a buyer fills a listing, the system routes delivery through the **feature owner first** (original creator), falling back to any registered **replica holder** if the owner is unavailable.

| Event | Who earns | Amount |
|-------|-----------|--------|
| `FEATURE_BORROWED` | Original creator (always) | `credit_units` — computed at fill time by `mint_per_adoption()` |
| `DELIVERY_FEE` | Replica holder (delivery only) | 10% of ask price |
| `EQUITY_LISTING_FILLED` | Equity seller | ask price in full |

**Creator earn is computed at fill time** using `mint_per_adoption()` — not a flat amount. The result is stored in the `credit_units` field of the `FEATURE_BORROWED` audit row, so the audit log is the authoritative source. Old rows without `credit_units` fall back to 1 token flat (backward compat).

**`mint_per_adoption()` formula components:**

| Factor | Effect |
|--------|--------|
| `feature_complexity` (LOC × deps × tests) | Base earn — complex features earn more |
| `adoption_rank` | Novelty decay — `1 / (1 + log2(rank))`; early adopters earn more |
| `network_size` | Saturation threshold — `n_sat = ceil(0.30 × network_size)` |
| `estimated_network_size` | Anchors supply pressure physics ceiling |
| `supply_pressure_multiplier` | Soft quadratic squeeze as total supply approaches physics ceiling |
| `epoch_decay` | `0.99^epochs_elapsed` — older features earn less |
| `adopter_trust` | `0.5 + 0.5 × trust` — high-reputation borrowers generate more earn |
| `rep_tier_bonus` | Wilson-based stackable bonus across 4 quality tiers |

Same-peer repeat borrows store `credit_units = 0` — creator earns nothing on reborrow from the same node.

**Replica holders** earn delivery fees for bandwidth, but do NOT earn `FEATURE_BORROWED` token credits — that always credits the original creator regardless of who physically delivered.

```sh
# Register as replica holder for a feature
urace exchange equity register-replica <feature_id> --artifact-hash <sha256>
```

---

## Estimate-Based Listing Ceiling

When an owner reference estimate is configured, the listing CLI may apply this ceiling. It is a price heuristic and does not prove savings versus executor work:

```
ask_price ≤ (executor_reference_price − gas_overhead) × completeness × (1 − margin) − iter_savings
```

`gas_overhead` is deducted from the headroom before applying completeness and margin. It defaults to 0 for off-chain deployments; set `gas_per_tx_gwei`, `gas_price_gwei`, and `urace_units_per_gwei` for dynamic EVM estimation, or `gas_overhead_units` for a static override. See [Price Mechanics](price-mechanics.md) for the full breakdown.

| Field | Completeness bonus |
|-------|--------------------|
| description | +0.1 |
| spec_context | +0.2 |
| tags | +0.1 |
| include_context | +0.1 |
| implementation artifact (any type/size) | +0.3 |
| large artifact (>100 KB) | +0.05 bonus |
| **Maximum** | **1.0** |

`iter_savings` and completeness values are estimates, not measured executor iterations or accepted task coverage. Current P2P refresh does not calculate or enforce a price-consensus ceiling. Consensus over self-reported estimates would not establish a truthful or comparable executor baseline.

---

## Cartel Detection

URACE uses Dijkstra shortest-path trust graph analysis to detect coordinated manipulation:
- Edge weight = 1 / co-occurrence in qualification events
- Cluster diversity required: ≥3 independent clusters for consensus
- Wilson score lower bound (z=1.645, 95% confidence) for reputation calculation

---

## Consensus Security

The P2P consensus threshold uses a **persistent all-time maximum network size** — not the current estimate:

```
threshold = max(2, min(10, ceil(10% × max(current_estimate, all_time_max)))
```

An attacker who temporarily isolates part of the network cannot lower the threshold by making the network appear smaller.

---

## Token Settlement

Mainnet settlement is **disabled by default**. Tokens operate as reputation scores within a closed network until you explicitly enable peer-to-peer settlement.

```sh
urace exchange settings set --token-settlement true
urace exchange ledger transfer <peer_id> <amount_units>
```

---

## On-chain settlement (opt-in)

URACE can broadcast credit deltas as EVM transactions when configured with a JSON-RPC provider.

**How to enable**: set `token_settlement: true`, `rpc_provider_url`, and `chain_id` in `exchange/policy.json` under the `p2p` key:

```json
{
  "p2p": {
    "token_settlement": true,
    "rpc_provider_url": "https://polygon-mainnet.infura.io/v3/YOUR_KEY",
    "chain_id": 137
  }
}
```

**Chain selection — gas economics matter**:

| `chain_id` | Network | Gas per ERC-20 transfer | Economical for per-borrow? |
|------------|---------|------------------------|---------------------------|
| `1` | Ethereum mainnet | ~$4–7 at 20 Gwei | **No** — 600× a typical executor call |
| `137` | Polygon PoS | ~$0.001 | **Yes** — recommended |
| `8453` | Base | ~$0.001 | **Yes** |
| `42161` | Arbitrum One | ~$0.001 | **Yes** |

> **Warning**: `chain_id=1` (mainnet) makes per-borrow on-chain settlement economically broken. Use it only for large off-ramp withdrawals, not per-transaction settlement. Omit `chain_id` and it defaults to `1` for safety (explicit opt-in required for per-borrow settlement).

**What happens**: when both fields are set, credit deltas (on-ramp, off-ramp, NFT mint) are signed and broadcast as EVM transactions (EIP-155 RLP-encoded, with real nonce, gas price, and ABI-encoded calldata) to the configured RPC endpoint instead of being processed as audit-only stubs. Cross-peer trial receipts (`trial_receipt.py`) are also delivered to the creator peer so that `receipt_verified=True` earn events require actual signed cross-peer acknowledgement — not just local audit rows. `handle_purchase_settlement` also fires `on_ramp` for the buyer when a `crypto_address` is included in the settlement payload.

**Unit scaling**: internal URACE units (8-decimal satoshi model) are automatically converted to 18-decimal EVM amounts using the built-in `CHAIN_SCALE` factor (10^10). No manual conversion is required.

**Supported providers**: any EVM-compatible JSON-RPC endpoint works — Alchemy, Infura, QuickNode, or a self-hosted node (e.g. `http://localhost:8545` for a local Hardhat or Anvil instance).

**Disabled by default**: if `token_settlement` is absent or `false`, or if `rpc_provider_url` is not set, URACE uses the audit-only stub adapter and no network calls are made.

---

## Security Guarantees

| Threat | Defense |
|--------|---------|
| Wash trading | 24h round-trip block per feature |
| Price manipulation | 1.5× momentum guard; configured executor-reference ceiling is only an estimate |
| Supply inflation | Per-feature bp cap (10,000 bp = 100%), fake adoption requires proof-of-purchase |
| Consensus hijacking | Persistent network size max, reputation-weighted votes |
| Sybil attacks | Certificate pinning, reputation decay, cluster analysis; bootstrap grant locked until quality pass |
| Fake replica spam | Replica registration requires valid EQUITY_GRANT; delivery fee only paid on actual delivery audit row |
| Price ceiling gaming | No consensus price ceiling exists; do not treat peer estimates or reputation as cost evidence |
| Cold-start abuse | Trial borrow limited to 1 per peer; additional borrows require earned balance |
| Circular money laundering | 24h round-trip detection blocks circular credit flow |
| DoS flooding | RPC flood detection (10 rejections/hour → block), chunked reads |

---

## Executor Cost Receipts

The runtime auto-captures a `urace-executor-receipt-v1` receipt after every executor operation. Receipts record token counts (input, output, cache-read) and USD at published provider rates (Anthropic and OpenAI models as of 2025-11). USD is never imputed from URACE unit prices — URACE units and provider USD are separate dimensions with no established conversion.

```sh
urace cost summary          # aggregate USD + token totals
urace cost list --limit 20  # per-call breakdown
```

Receipts are stored in `state/receipts/` and never leave the local machine. See [CLI Reference](../reference/cli.md#cost) and [Spec](../reference/spec.md#executor-receipt-contract) for the full schema.

---

## P2P Cost Dimensions

> **Current runtime**: in the current version, P2P borrow operations (`equity fill-listing`, `bundle fetch-artifact`) complete without provider calls — `$Y = $0` in all borrows. The integration step provider calls described below are **design targets** for a future version, not current runtime behavior. The `$Z` dimension and ceiling formula are fully implemented now.

Three independent cost dimensions apply when comparing executor-only vs P2P paths. They are not convertible and have no established exchange rate between them.

| Measure | Executor-only | P2P path (current) |
|---------|--------------|----------|
| Provider USD (`$X`) | Billed at `PROVIDER_RATE` per token | `$0.00` — no integration step calls in current runtime |
| URACE units paid (`$Z`) | 0 | ask_price in ledger units (≤ listing ceiling) |
| URACE → USD rate | n/a | `NOT_ESTABLISHED` — no conversion exists |

### P2P Integration Step Costs (`$Y`) — Design Targets

When integration step provider calls are implemented, the following token ranges apply:

| Step | Provider call? | Typical input tokens | Typical output tokens |
|------|---------------|---------------------|----------------------|
| Discovery + fetch | No | — | — |
| Quarantine check | No | — | — |
| Asset analysis | Sometimes | 300–800 | 100–200 |
| Context adaptation | Often | 800–2,000 | 200–600 |
| Quality gate / acceptance validation | Sometimes | 500–1,500 | 100–300 |
| Gap fill (incomplete asset) | Fallback only | Same as executor for the gap | — |

Expected distribution once implemented (~50% zero-call, ~35% single-step, ~15% full-adapt):

- Estimated `$Y` total for a 30-task cohort at `claude-sonnet-4-6` rates: **~`$0.19`**
- `$Z` ceiling at default margin: 60% of owner's ref
- At max future `$Y` (~25%): combined `$Y + $Z ≈ 85%` — still under the executor-only baseline

The listing ceiling margin (default 0.40) also acts as a **quality filter**:
low-completeness listings (no artifact, no spec) can only be priced at ≤12% of the owner's reference estimate,
disincentivising bare-minimum submissions.

### What These Measures Do Not Include

- **URACE→USD conversion**: no rate exists; `$Z` (ledger units) and `$X`/`$Y` (provider USD) are orthogonal dimensions
- **Delivery fee**: the buyer pays ask_price in URACE units; creator (10%) and replica holder earn from that pool — not from provider USD
- **Composition/referral pool**: composition owners earn from a separate referral pool; not reflected in `$Y`
- **Gas costs**: on-chain EVM deployments add gas overhead (see [Price Mechanics](price-mechanics.md)); off-chain deployments pay `$0.00`
- **Quality gate retry cost**: if acceptance validation fails and a re-run is needed, the new executor call is a fresh `$X` receipt — not rolled into `$Y`
- **Savings claims**: the ceiling formula is a price heuristic — the owner's `ref` estimate is not an audited executor baseline

---

## Related

- [Price Mechanics](price-mechanics.md) — executor ceiling, momentum guard, wash trading
- [Reputation](../exchange/reputation.md) — how to earn and view tokens
- [Network](../exchange/network.md) — consensus and peer trust
