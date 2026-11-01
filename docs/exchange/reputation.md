# Reputation: Tokens, Ledger, and History

[← Documentation](../index.md)

In URACE, reputation is earned — not bought. Your reputation score reflects verified contributions: quality improvements you've made, features you've minted, and work you've delivered.

---

## Token Balance

Check your current balance:

```sh
urace exchange ledger summary
```

This shows:
- Earned tokens (from quality gate passes)
- Spent tokens (features borrowed, work commissioned)
- Current balance
- Pending escrow

---

## Your Reputation Score

```sh
urace exchange reputation show <peer_id>
```

Breakdown shows:
- **Earned reputation**: based on verified quality improvements (Wilson score, 95% CI)
- **Market reputation**: based on successful feature adoptions and work deliveries
- **Trust graph position**: your clustering relative to independent peer groups

---

## Reputation History

Track how your reputation has changed over time:

```sh
urace exchange reputation history <peer_id> --days 30
```

---

## Leaderboard

See the top peers by earned reputation:

```sh
urace exchange reputation leaderboard
```

---

## How Tokens Are Earned

Tokens enter circulation only through **quality gate passes**:

```
urace run → quality gate pass → score_delta > 0 → tokens earned
```

There is exactly one earn path. Tokens cannot be minted arbitrarily or transferred from outside the network. Each token represents a verified improvement.

---

## Token Transfers

When `token_settlement` is enabled, transfer tokens directly to peers:

```sh
urace exchange ledger transfer <peer_id> <amount_units>
```

Token settlement is off by default. Enable it explicitly:

```sh
urace exchange settings set --token-settlement true
```

---

## Network Supply Calculator

Estimate the optimal token supply for your network size:

```sh
urace exchange ledger supply-calc \
  --peers 1000 \
  --ledger-mb 50 \
  --bandwidth-kbps 1000 \
  --sync-secs 30 \
  --adoption-rate 0.10
```

See [Tokenomics](../economics/tokenomics.md) for the full supply model.

---

## Cartel Detection

URACE uses trust graph analysis to detect coordinated reputation manipulation:
- Peers who co-occur frequently in qualification events are weighted less
- Cluster diversity requires ≥3 independent peer clusters for consensus
- Wilson score lower bound prevents small sample exploitation

See [Tokenomics](../economics/tokenomics.md) for details.

---

## Related

- [Tokenomics](../economics/tokenomics.md) — full token supply model
- [Price Mechanics](../economics/price-mechanics.md) — pricing rules
- [Features](features.md) — earn by minting
- [Work Market](work-market.md) — earn by delivering work
