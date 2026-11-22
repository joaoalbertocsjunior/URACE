# URACE

URACE promise is to consistently improves a product autonomously in the long run — at prices lower than calling an executor directly — using AI agents and other executors — and generates revenue or reduces costs through its P2P-first design.

Open-source, community-governed.

---

Status - **DEV**, non-prod

Deferred - UX, non-p2p scope

Last Changes - [LATEST](docs/LATEST.md)

---

## Install

```sh
# one-liner (Linux / macOS / WSL):
curl -fsSL https://raw.githubusercontent.com/joaoalbertocsjunior/URACE/main/install.sh | sh
```

```sh
export ANTHROPIC_API_KEY=...  # or OPENAI_API_KEY
urace start                   # auto-init + boot daemon + wire executor + join P2P
```

`urace start` self-initializes on first run: detects your API keys, assigns node roles, probes NAT, and prints network setup guidance if any manual step is needed (e.g. `cloudflared tunnel login` for a permanent bootstrap URL). Nothing else required.

---

## Daily use

```sh
urace start                      # boot
urace                            # open shell — type goals, rules, context, questions
urace status                     # see health, goals, decisions, activity
urace reload                     # apply config.json changes without restarting
urace stop                       # shutdown
```

Status and reload will gain more user-friendly surfaces over time; these commands remain direct, useful controls for checking runtime health and applying configuration changes.

Inside the shell:

```
> improve test coverage and reduce build time
→ Goal added

> never modify database migrations without a review
→ Rule added (prohibition)

> /events --follow               # live activity tail
> /status                        # daemon + network status
```

## How you earn

| You do | You earn |
|--------|---------|
| Peers borrow your minted feature | Royalty per borrow (asset_royalty) |
| You deliver an artifact to a borrow request | Delivery fee (% of borrow cost) |
| A derivative of your feature is filled | Composition referral |
| You file a successful APS challenge | Challenge bounty (50% of stake) |
| You seal a ledger block | Seal reward (0.0100 UCR) |
| You relay a P2P connection | Relay reward (0.0100 UCR) |
| You win a work-market bid and deliver | Work-market delivery fee |

→ [Node rewards](docs/economy/node-rewards.md) · [Token economics](docs/economy/tokenomics.md)

---

## P2P exchange

Peers mint, list, and borrow verified software features. Borrow cost is a small fraction of calling an executor directly — micro features (≤50 LOC) cost ≤5% of executor price, saving 94%+ per borrow.

P2P borrows have `$0` provider cost in the current runtime; buyers pay URACE units at the listing ask.

No URACE↔USD exchange rate exists. Polygon is planned as mainnet.

→ [P2P exchange](docs/power-users/exchange-index.md) · [Price mechanics](docs/economy/price-mechanics.md)

---

## Docs

**Users:** [Quick start](docs/users/quick-start.md) · [Daily use](docs/users/ux-guide.md) · [CLI reference](docs/users/cli.md) · [Config](docs/users/config.md)

**Power users:** [P2P exchange](docs/power-users/exchange-index.md) · [Full UX surfaces](docs/power-users/ux-surfaces.md) · [RPC contract](docs/power-users/urace-rpc-v1.md) · [Agent integrations](docs/power-users/agent-integrations.md)

**Economy:** [Token economics](docs/economy/tokenomics.md) · [Node rewards](docs/economy/node-rewards.md) · [Price mechanics](docs/economy/price-mechanics.md)

**Security & Spec:** [Security model](docs/security/security-model.md) · [Runtime spec](docs/spec/runtime.md) · [Peer security](docs/security/peer-security.md)

**Roadmap:** [Polygon](docs/roadmap/polygon-roadmap.md) · [Benchmarks](docs/roadmap/benchmark-proof.md) · [Full docs index](docs/index.md)

---

Code: [Apache 2.0](LICENSES/Apache-2.0.txt) · Spec: [CSL 1.0](LICENSES/CSL-1.0.txt) · Copyright 2006–2026 Joao Alberto Cambauva dos Santos Junior
