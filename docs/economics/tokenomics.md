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
| Baseline grant | 3 tokens per new peer (bootstrap participation before first earn) |
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

URACE ships with a pre-built initial ledger of **1,343 built-in features** — every atomic capability across all runtime and trial modules, CLI surfaces, exchange/P2P commands, and test contracts. All initial ledger features are:

- **Free-use**: borrow cost = 0 tokens
- **No owner**: minted without a creator, available to all peers
- **Discoverable**: searchable via `urace search --kind p2p` or `exchange compact search`
- **Auto-context**: used by `urace derive` and `urace freeform-text` without token cost

| Metric | Value |
|--------|-------|
| Initial features minted | 1,343 |
| Breakdown | 1,110 mechanism · 119 schema · 106 contract · 7 integration · 1 protocol |
| Max features at 1 Mbps / 1,000 peers | 3,840 |
| Utilization at baseline infra | 35% |
| Room for user features at baseline | 2,497 additional features |
| Max features at 10 Mbps / 10,000 peers | 65,536 |
| Utilization at 10 Mbps | 2% |

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

## Token Price Estimation

Tokens represent access to verified peer work:

| Assumption | Value |
|-----------|-------|
| Avg developer-hours per feature | 2–4 hours |
| Developer cost | $100–$200/hour |
| Fair value per feature | $200–$800 |
| Earn cap per feature | ~6.36 tokens (typical 200 LOC / 3 deps / 10 tests) |
| Implied token value | $200 ÷ 6.36 to $800 ÷ 6.36 = **$31–$126 per token** |
| Market cap (1,000-peer network, 41,400 tokens) | $1.3M–$5.2M |
| Market cap (10,000-peer network, 688,000 tokens) | $21M–$87M |

These are **utility-anchored estimates** — each token buys real developer-equivalent output, not speculation.

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

## Security Guarantees

| Threat | Defense |
|--------|---------|
| Wash trading | 24h round-trip block per feature |
| Price manipulation | 1.5× momentum ceiling, executor price ceiling |
| Supply inflation | Per-feature bp cap (10,000 bp = 100%), fake adoption requires proof-of-purchase |
| Consensus hijacking | Persistent network size max, reputation-weighted votes |
| Sybil attacks | Certificate pinning, reputation decay, cluster analysis |
| DoS flooding | RPC flood detection (10 rejections/hour → block), chunked reads |

---

## Related

- [Price Mechanics](price-mechanics.md) — executor ceiling, momentum guard, wash trading
- [Reputation](../exchange/reputation.md) — how to earn and view tokens
- [Network](../exchange/network.md) — consensus and peer trust
