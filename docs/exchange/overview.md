# Exchange Overview

[← Documentation](../index.md)

The URACE exchange is a P2P feature marketplace. Peers share verified software improvements, earn tokens from adoption, and borrow each other's features at prices lower than building from scratch.

---

## What It Is

The exchange connects software teams working on similar problems. Instead of every team solving the same challenges independently, the exchange lets teams:

- **Mint** features they've built (verified by quality gate) and earn tokens when others adopt them
- **Borrow** features from peers at a fraction of the build cost
- **Trade equity** in features they believe will gain value
- **Commission work** from peers via the escrow-backed work market

---

## Who It's For

- **Teams improving existing products**: earn tokens from quality improvements, reinvest them to borrow features
- **Developers with reusable components**: mint and monetize verified work without building a marketplace
- **Organizations with shared infrastructure**: use the network to distribute internal improvements across teams
- **AI agent workflows**: the exchange is designed to be operated by both humans and AI agents

---

## How It Works

1. You run `urace run` and earn tokens by passing quality gates
2. You enable the exchange and create a peer identity
3. You mint features you've built to the network
4. Other peers borrow your features — you earn tokens per adoption
5. You use earned tokens to borrow features from peers

The token economy is self-contained: tokens only enter circulation via verified quality improvements, and tokens only leave via verified feature adoption.

---

## Key Properties

- **Off by default**: The exchange is disabled until you explicitly enable it
- **Executor price ceiling**: P2P borrow price is always ≤ the cost of building the feature with an executor
- **Cryptographically verified**: All bundles are signed with post-quantum hybrid signatures
- **Quarantine model**: Borrowed features are never executed automatically
- **Reputation-weighted**: Peers with higher verified contribution earn more trust

---

## Market Stats

See live token velocity and network health at any time:

```sh
urace exchange market stats --json
```

Returns:
- **mints_24h** / **burns_24h**: qualification receipts and credit deltas in the last 24 hours
- **net_velocity**: mints minus burns (positive = net token creation)
- **velocity.trend**: direction of velocity change (`up`, `down`, `stable`)
- **velocity.trend_delta_pct**: percentage change in velocity vs. the previous equivalent window
- **total_features**: feature count from the initial ledger header
- **network_peers**: estimated peer count
- **window_hours**: configurable via `--window-hours`

---

## Bootstrap Peers

Bootstrap peers are fixed entry points that help new peers join the network without prior discovery. Add known peers before enabling networking:

```sh
urace exchange bootstrap add --address <peer-addr>
urace exchange bootstrap list
urace exchange bootstrap remove --address <peer-addr>
```

Bootstrap addresses can be shared out-of-band (e.g., in your team's README or a private channel).

---

## Network Mode

URACE supports three network modes for different deployment scenarios:

| Mode | Description | Use case |
|------|-------------|----------|
| `intranet` | LAN-only — no internet peers contacted | Air-gapped or private team networks |
| `internet` | Standard — bootstrap peers + DHT discovery | Public internet deployment |
| `hybrid` | LAN + optional internet gateway (default) | Teams that want LAN efficiency with internet reach |

Configure the mode:

```sh
urace exchange settings set --network-mode intranet
urace exchange settings set --network-mode hybrid
```

### Intranet → Internet Upgrade

When your team is ready to connect to the wider network:

1. Discover your public address via STUN:
   ```sh
   urace exchange network public-address --json
   ```
2. Register it as a bootstrap peer endpoint so other internet peers can find you:
   ```sh
   urace exchange bootstrap add --address https://<your-public-ip>:<port>
   ```
3. Switch network mode to hybrid:
   ```sh
   urace exchange settings set --network-mode hybrid
   ```

---

## Get Started

- [Setup](setup.md) — enable, create identity, configure
- [Features](features.md) — mint, borrow, and trade
- [Work Market](work-market.md) — commission and deliver work
- [Network](network.md) — P2P discovery and consensus
- [Reputation](reputation.md) — tokens, ledger, leaderboard
