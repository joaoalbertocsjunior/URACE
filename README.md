# URACE

**Unified Runtime for Autonomous Collaborative Evolution** — a P2P-first lifecycle control plane for AI-assisted software products.

URACE manages goals, execution, quality gates, peer collaboration, and token-based reputation in a single runtime. It is designed to be embedded in any product, operated by humans or AI agents, and governed by cryptographic authority boundaries.

## What URACE Does

- **Product lifecycle**: track goals, plans, operations, and quality metrics across cycles
- **P2P feature marketplace**: peers mint, list, and borrow verified software features at prices guaranteed lower than building from scratch
- **Token reputation**: earn tokens by improving your product; spend them to borrow from peers
- **Self-evolution with governance**: the runtime improves itself under strict authority boundaries — no change without owner approval
- **Freeform routing**: route any text input to the right command, executor, or P2P network automatically

## Get Running

```sh
# pip (recommended)
pip install urace

# npm
npm install -g urace-cli

# Homebrew
brew install urace

# conda
conda install -c conda-forge urace
```

## Use It

```sh
# Initialize a product
urace init

# Start the autonomous daemon — it improves your product in the background
urace daemon start

# Or just talk to it — freeform input routes to the right command automatically
urace "What's my project status?"
urace "Add goal: improve checkout conversion by 20%"
urace "Show recent operations"
```

The daemon runs improvement cycles on a schedule (default: every 30 min). You watch it work, intervene when you want, stop when you're done (`Ctrl+C`). No pipeline to configure.

## Core Concepts

### Goals and Plans
Tell URACE what you want. It figures out how to get there, executes the work, and tracks every outcome.

```sh
urace add "Reduce API p99 latency below 200ms"
urace "What's blocking my latency goal?"
urace inspect --goals
```

### P2P Exchange — Stop Rebuilding What Others Already Solved

Every verified feature your product ships becomes an asset you can offer to peers. Every feature a peer already built is available for you to borrow — always cheaper than building it yourself.

```sh
# Join the network (opt-in)
urace exchange settings set --enabled true --network true
urace exchange peer identity

# See what peers are offering
urace exchange network discover

# Borrow a feature instead of building it
urace exchange feature define auth-refresh --wanted true

# Offer your own work to the network
urace exchange equity grant auth-refresh --creator <your_peer_id>
```

Your work earns reputation. Reputation earns tokens. Tokens unlock the network.

### Token Economy — Quality Pays

Pass a quality gate → earn tokens automatically. No manual claims, no invoices. Spend tokens to borrow verified features from peers.

```sh
# See what you've earned
urace exchange ledger summary

# Your reputation on the network
urace exchange reputation show <your_peer_id>
```

The more you improve your product, the more you earn. The more the network grows, the more features you can borrow. It compounds.

## P2P Network Commands

| Command | Description |
|---------|-------------|
| `exchange network discover` | Find peers via LAN/DNS-SD |
| `exchange network probe <peer_id>` | Check what a peer offers |
| `exchange network refresh` | Refresh offers from pinned peers |
| `exchange network serve` | Start P2P listener |
| `exchange network consensus-status` | View consensus threshold and state |
| `exchange network disconnect [--duration-minutes N]` | Pause networking temporarily |
| `exchange network-audit list [--kind K] [--peer P]` | View P2P network events |

## Peer Management

| Command | Description |
|---------|-------------|
| `exchange peer add --certificate FILE` | Pin a new peer |
| `exchange peer block <id>` / `unblock <id>` | Block or unblock a peer |
| `exchange peer rotate <old_id> --new-certificate FILE` | Rotate identity, migrate rules |
| `exchange peer list` | List all peers |

## Equity Trading

| Command | Description |
|---------|-------------|
| `exchange equity holdings <feature>` | Show who holds what |
| `exchange equity list-for-sale <feature> --bp N --price N` | List equity for sale |
| `exchange equity listings [--feature F]` | Browse open listings |
| `exchange equity fill-listing <id>` | Buy a listing |
| `exchange equity auto-buy` | Run automated buying pass |
| `exchange equity auto-sell` | Run automated selling pass |
| `exchange equity trade-config set` | Configure auto-trade thresholds |
| `exchange compact depletion <feature_id>` | Check feature saturation |

## Reputation

| Command | Description |
|---------|-------------|
| `exchange reputation show <peer_id>` | Breakdown of earned vs. market reputation |
| `exchange reputation leaderboard` | Top peers by earned reputation |
| `exchange reputation history <peer_id> --days 30` | Reputation trend over time |

## Work Market

Request work from peers and escrow payment until delivery is verified:

```sh
# Create a work request
urace exchange work create "Add retry logic to API client" --budget 100 --complexity 0.4

# List bids
urace exchange work list --state OPEN

# Accept best bid
urace exchange work accept <request_id> --bidder <peer_id>

# Verify delivery
urace exchange work verify <request_id> --approve true

# Decompose high-complexity work
urace exchange work decompose "Large refactor" --budget 1000 --complexity 0.9
```

## Rules and Access Control

```sh
# Set a rule
urace exchange rule set <peer_id> <feature_id> send --allow true

# Export all rules for backup
urace exchange rule export --file rules.json

# Import rules from file
urace exchange rule import --file rules.json
```

## Security

URACE is P2P-first with defense in depth:

- **TLS 1.3 mandatory** — all peer connections use mutual TLS with certificate pinning
- **Post-quantum ready** — ML-KEM-768 + Ed25519 hybrid signatures on all bundles
- **IP anonymization** — DHT uses hashed node IDs; no IPs in audit trail; `relay_only` mode available
- **Quarantine model** — incoming artifacts are never executed automatically
- **Authority boundary** — self-evolution changes require owner authorization
- **Wash trading blocked** — buying and selling same feature within 24h is rejected
- **Price momentum guard** — ask prices capped at 1.5× 7-day median
- **Executor price ceiling** — P2P borrow always cheaper than executor mint cost
- **Consensus hardening** — threshold uses persistent all-time-max network size
- **RPC flood protection** — 10 rejections/hour triggers automatic peer block
- **DHT bootstrap rate limiting** — minimum 5 min between bootstrap attempts

## Configuration Defaults

| Setting | Default | Description |
|---------|---------|-------------|
| `enabled` | `false` | Exchange is off until explicitly enabled |
| `network` | `false` | P2P networking off until enabled |
| `advertise` | `false` | LAN advertising off |
| `auto_select` | `true` | Auto-probe pinned peers |
| `token_settlement` | `false` | Token transfers disabled until enabled |
| `max_transfers_per_day` | `20` | Daily bundle transfer limit |
| `max_rpc_per_day` | `200` | Daily RPC limit |
| `max_rpc_per_peer_per_day` | `50` | Per-peer RPC limit |
| `feature_borrow_enabled` | `true` | P2P is default first source for features |

```sh
urace exchange settings set --enabled true --network true --advertise true
```

## Tokenomics Summary

| Property | Value |
|----------|-------|
| Earn path | Quality gate pass only |
| Precision | 8 decimals (satoshi model) |
| Per-peer baseline grant | 3 tokens |
| Default network supply (1,000 peers) | ~9,250 tokens |
| Max unique features (1,000 peers) | ~6,250 |
| Price ceiling | ≤ executor reference price |
| Epoch-adjustable | Yes — run `exchange ledger supply-calc` with updated network params |

See [docs/tokenomics.md](docs/tokenomics.md) for full economics model and price estimation.

## Documentation

Full documentation is at **[docs/index.md](docs/index.md)**.

### Getting Started

| Document | Description |
|----------|-------------|
| [docs/getting-started/install.md](docs/getting-started/install.md) | pip install, requirements, verify |
| [docs/getting-started/quick-start.md](docs/getting-started/quick-start.md) | 5-minute guide — init, run, mint to P2P |
| [docs/getting-started/concepts.md](docs/getting-started/concepts.md) | Goals, plans, operations, lifecycle overview |

### Guides

| Document | Description |
|----------|-------------|
| [docs/guides/products.md](docs/guides/products.md) | Product lifecycle: add goals, run cycles, inspect, status |
| [docs/guides/controls.md](docs/guides/controls.md) | Enable/disable capabilities per product |
| [docs/guides/derive.md](docs/guides/derive.md) | Extract architectural patterns from your product spec |
| [docs/guides/search.md](docs/guides/search.md) | Search context ledger and P2P audit trail |
| [docs/guides/update.md](docs/guides/update.md) | Runtime versioning: download, explain, apply |

### Exchange

| Document | Description |
|----------|-------------|
| [docs/exchange/overview.md](docs/exchange/overview.md) | What the exchange is and who it's for |
| [docs/exchange/setup.md](docs/exchange/setup.md) | Enable, create identity, configure settings |
| [docs/exchange/features.md](docs/exchange/features.md) | Mint features, borrow from peers, equity trading |
| [docs/exchange/work-market.md](docs/exchange/work-market.md) | Request work, bids, escrow, verify delivery |
| [docs/exchange/network.md](docs/exchange/network.md) | P2P discovery, consensus, disconnect, audit |
| [docs/exchange/reputation.md](docs/exchange/reputation.md) | Tokens, ledger, reputation history, leaderboard |

### Economics and Security

| Document | Description |
|----------|-------------|
| [docs/economics/tokenomics.md](docs/economics/tokenomics.md) | Full token model: supply, earn, spend, epoch |
| [docs/economics/price-mechanics.md](docs/economics/price-mechanics.md) | Executor ceiling, momentum guard, wash trading |
| [docs/security/overview.md](docs/security/overview.md) | Defense in depth, security guarantees table |
| [docs/security/authority-boundary.md](docs/security/authority-boundary.md) | Self-evolve governance, protected files |
| [docs/security/peer-security.md](docs/security/peer-security.md) | TLS 1.3, post-quantum, quarantine, flood protection |

### Reference

| Document | Description |
|----------|-------------|
| [docs/reference/cli.md](docs/reference/cli.md) | All CLI commands in one table |
| [docs/reference/config.md](docs/reference/config.md) | All config options with defaults |
| [docs/reference/spec.md](docs/reference/spec.md) | URACE system spec: guarantees, invariants, lifecycle |

### Other Docs

| Document | Description |
|----------|-------------|
| [docs/agent-integrations.md](docs/agent-integrations.md) | MCP and A2A agent integration |
| [docs/runtime-improvement.md](docs/runtime-improvement.md) | Runtime improvement workflows |
| [docs/peer-sharing.md](docs/peer-sharing.md) | P2P exchange, bundle operations, quarantine safety |
| [docs/network-onboarding.md](docs/network-onboarding.md) | Mainnet onboarding, settlement design |
| [docs/sharing-safeguards.md](docs/sharing-safeguards.md) | Security mechanisms for peer sharing |
| [docs/post-quantum-roadmap.md](docs/post-quantum-roadmap.md) | Post-quantum cryptography roadmap |

## Directory Structure

```
urace/
├── runtime/urace/       # Full lifecycle control plane and CLI
├── runtime/tests/       # Behavioral regression tests
├── trial/               # Supervised improvement workflow
├── docs/                # User and operator documentation
├── state/               # Local deployment data (not tracked)
└── generated/           # Generated artifacts (not tracked)
```

## License

Code: [Apache 2.0](LICENSES/Apache-2.0.txt) — Specification (`URACE.md`): [CSL 1.0](LICENSES/CSL-1.0.txt)

Copyright 2006–2026 Joao Alberto Cambauva dos Santos Junior
