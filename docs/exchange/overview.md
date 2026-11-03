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

## Get Started

- [Setup](setup.md) — enable, create identity, configure
- [Features](features.md) — mint, borrow, and trade
- [Work Market](work-market.md) — commission and deliver work
- [Network](network.md) — P2P discovery and consensus
- [Reputation](reputation.md) — tokens, ledger, leaderboard
