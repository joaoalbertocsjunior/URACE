# URACE Documentation

**Unified Runtime for Autonomous Collaborative Evolution** — a P2P-first lifecycle control plane for AI-assisted software products.

URACE manages goals, execution, quality gates, peer collaboration, and token-based reputation in a single runtime. It runs inside your product, operated by you or your agents, governed by cryptographic authority boundaries.

---

## Getting Started

| | |
|---|---|
| [Install](getting-started/install.md) | pip install, requirements, verify |
| [Quick Start](getting-started/quick-start.md) | 5-minute guide — init, run, mint to P2P |
| [Concepts](getting-started/concepts.md) | Goals, plans, operations, lifecycle overview |

---

## Guides

| | |
|---|---|
| [Products](guides/products.md) | Product lifecycle: add goals, run cycles, inspect, status |
| [Controls](guides/controls.md) | Enable/disable capabilities per product |
| [Derive](guides/derive.md) | Extract architectural patterns from your product spec |
| [Search](guides/search.md) | Search context ledger and P2P audit trail |
| [Update](guides/update.md) | Runtime versioning: download, explain, apply |

---

## Exchange

| | |
|---|---|
| [Overview](exchange/overview.md) | What the exchange is and who it's for |
| [Setup](exchange/setup.md) | Enable, create identity, configure settings |
| [Features](exchange/features.md) | Mint features, borrow from peers, equity trading |
| [Work Market](exchange/work-market.md) | Request work, bids, escrow, verify delivery |
| [Network](exchange/network.md) | P2P discovery, consensus, disconnect, audit |
| [Reputation](exchange/reputation.md) | Tokens, ledger, reputation history, leaderboard |

---

## Economics

| | |
|---|---|
| [Tokenomics](economics/tokenomics.md) | Full token model: supply, earn, spend, epoch |
| [Price Mechanics](economics/price-mechanics.md) | Executor ceiling, momentum guard, wash trading prevention |

---

## Security

| | |
|---|---|
| [Overview](security/overview.md) | Defense in depth, security guarantees table |
| [Authority Boundary](security/authority-boundary.md) | Self-evolve governance, protected files |
| [Peer Security](security/peer-security.md) | TLS 1.3, post-quantum, quarantine, flood protection |

---

## Reference

| | |
|---|---|
| [CLI Reference](reference/cli.md) | All CLI commands in one table |
| [Config Reference](reference/config.md) | All config options with defaults |
| [Spec](reference/spec.md) | URACE system spec: guarantees, invariants, lifecycle |

---

## Other Docs

- [Agent Integrations](agent-integrations.md) — MCP and A2A agent integration
- [Runtime Improvement](runtime-improvement.md) — Runtime self-improvement workflows
- [Tokenomics (legacy redirect)](tokenomics.md) — Points to `economics/tokenomics.md`
- [Peer Sharing](peer-sharing.md) — P2P bundle operations and quarantine
- [Network Onboarding](network-onboarding.md) — Mainnet onboarding and settlement design
- [Sharing Safeguards](sharing-safeguards.md) — Security mechanisms for peer sharing
- [Post-Quantum Roadmap](post-quantum-roadmap.md) — Post-quantum cryptography roadmap

---

## For Executors and AI Agents

[**AGENTS.md**](../AGENTS.md) — Complete onboarding reference for executors and AI agents operating on URACE: authority model, command reference, file structure, machine interface contract, and what executors must not do.
