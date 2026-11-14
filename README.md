# URACE

**Autonomous improvement. P2P feature market. Token rewards for every contribution.**

Type a goal — URACE executes, verifies, and checkpoints. Borrow proven features from peers instead
of building from scratch. Mint yours and earn when others borrow them. Run a node and earn for
every delivery, relay, or block you seal.

Open-source, community-governed.

---

## Install

```sh
pip install urace          # Python 3.11+
npm install -g urace-cli   # Node 16+

export ANTHROPIC_API_KEY=...  # or OPENAI_API_KEY
urace start                   # boot daemon, wire executor, join P2P
```

→ [Full setup](docs/getting-started/quick-start.md)

---

## Daily use

```sh
urace start                      # boot
urace                            # open shell — type goals, rules, context, questions
urace status                     # see health, goals, decisions, activity
urace stop                       # shutdown
```

Inside the shell:

```
> improve test coverage and reduce build time
→ Goal added

> never modify database migrations without a review
→ Rule added (prohibition)

> /events --follow               # live activity tail
> /status                        # daemon + network status
```

---

## Core commands

| Command | What it does |
|---------|-------------|
| `urace start` | Boot daemon + join P2P network |
| `urace` | Open shell (your main workspace) |
| `urace status` | Health, goals, decisions, activity |
| `urace source add --kind <kind>` | Connect data, executors, metrics, github, peers |
| `urace config` | Change settings |
| `urace update` | Apply spec updates |
| `urace stop` | Shutdown |

→ [All commands](docs/reference/ux-guide.md) · [Full reference](docs/reference/ux-surfaces.md)

---

## P2P market

Peers mint, list, and borrow verified software features.

P2P borrows have `$0` provider cost in the current runtime; buyers pay URACE units at the listing ask.
No URACE↔USD exchange rate exists.

→ [P2P exchange](docs/exchange/overview.md) · [Token economy](docs/economics/tokenomics.md)

---

## Earn

| Role | Earns when |
|------|-----------|
| Creator / Minter | A peer borrows your feature |
| Delivery replica | You deliver an artifact (per borrow) |
| Composition owner | A derivative of your feature is filled |
| Challenger | Your APS challenge succeeds |
| Ledger sealer | You seal a block |
| Hired Node | You win a work-market bid and your delivery is verified |

→ [Node rewards](docs/concepts/node-rewards.md)

---

## Docs

| | |
|---|---|
| [Quick start](docs/getting-started/quick-start.md) | [5-min guide](docs/reference/ux-guide.md) |
| [Full CLI reference](docs/reference/ux-surfaces.md) | [P2P exchange](docs/exchange/overview.md) |
| [Token economy](docs/economics/tokenomics.md) | [Node rewards](docs/concepts/node-rewards.md) |
| [Security model](docs/concepts/security-model.md) | [Spec (`URACE.md`)](URACE.md) |
| [Ecosystem roadmap](docs/roadmap/ecosystem-roadmap.md) | [Full docs index](docs/index.md) |

---

v0.7.0 · Code: [Apache 2.0](LICENSES/Apache-2.0.txt) · Spec: [CSL 1.0](LICENSES/CSL-1.0.txt) · Copyright 2006–2026 Joao Alberto Cambauva dos Santos Junior
