# URACE

**Your product improves while you sleep.**

Type what you want. URACE classifies it, discovers reusable peer features, executes improvements,
enforces quality gates, and checkpoints verified results.

Open-source, community-governed.

---

## Install

```sh
pip install urace          # Python 3.11+
npm install -g urace-cli   # Node 16+

export ANTHROPIC_API_KEY=...  # or OPENAI_API_KEY
urace init --auto             # detect product, wire executor
urace daemon start            # start background cycles
```

→ [Full setup](docs/getting-started/quick-start.md)

---

## Use it

```sh
urace "What's blocking my latency goal?"  # plain-text request, routed automatically
urace run && urace status                 # trigger a cycle, check results
urace cost summary                        # executor costs at published provider rates
```

→ [CLI reference](docs/reference/cli.md)

---

## P2P market

Peers mint, list, and borrow verified software features.

Listing prices are capped against owner-provided estimates — not a savings guarantee.
P2P borrows have `$0` provider cost in the current runtime; buyers pay URACE units at the listing ask.
No URACE↔USD exchange rate exists.
Use task-matched receipts to compare actual costs.

→ [P2P exchange](docs/exchange/overview.md)
→ [Cost breakdown and caveats](docs/economics/tokenomics.md#p2p-cost-dimensions)
→ [Token economy](docs/economics/tokenomics.md)

---

## Earn

| Role | Earns when |
|------|-----------|
| Creator / Minter | A peer borrows your feature |
| Delivery replica | You deliver an artifact (per borrow) |
| Composition owner | A derivative of your feature is filled |
| Challenger | Your APS challenge succeeds |
| Ledger sealer | You seal a block |
| LLM similarity peer | You submit a SIMILARITY_VERDICT |
| Hired Node | You win a work-market bid and your delivery is verified |

Funded by a protocol fee on every fill — not inflation.

→ [Node rewards](docs/concepts/node-rewards.md)
→ [Price mechanics](docs/economics/price-mechanics.md)

---

## Security

Post-quantum signatures · TLS 1.3 · at-rest encryption · escrow auto-refund · cartel protection ·
APS provenance staking · sybil resistance · wash-trading block.

Incoming artifacts are never auto-executed.

→ [Security overview](docs/security/overview.md)
→ [Security model](docs/concepts/security-model.md)

---

## Docs

| | |
|---|---|
| [Quick start](docs/getting-started/quick-start.md) | [CLI reference](docs/reference/cli.md) |
| [P2P exchange](docs/exchange/overview.md) | [Token economy](docs/economics/tokenomics.md) |
| [Price mechanics](docs/economics/price-mechanics.md) | [Node rewards](docs/concepts/node-rewards.md) |
| [Security model](docs/concepts/security-model.md) | [Spec (`URACE.md`)](URACE.md) |
| [Ecosystem roadmap](docs/ecosystem-roadmap.md) | [RPC contract (`urace-rpc-v1`)](docs/reference/urace-rpc-v1.md) |
| [Benchmark proof](docs/benchmark-proof.md) | [Full docs index](docs/index.md) |

---

v0.6.0 · Code: [Apache 2.0](LICENSES/Apache-2.0.txt) · Spec: [CSL 1.0](LICENSES/CSL-1.0.txt) · Copyright 2006–2026 Joao Alberto Cambauva dos Santos Junior
