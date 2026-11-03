# Quick Start

[← Documentation](../index.md)

Get URACE running, improve your product, and mint the result to the P2P network — in under 5 minutes.

---

## 1. Install

```sh
pip install urace
```

---

## 2. Initialize Your Product

Run this inside your project directory:

```sh
urace init
```

This creates a local state directory and registers the product. URACE does not modify your source code.

---

## 3. Add a Goal

Tell URACE what you want to improve:

```sh
urace add "Improve API response time"
```

Goals are tracked as objectives. The runtime uses them to select operations each cycle.

---

## 4. Run an Improvement Cycle

```sh
urace run
```

The executor analyzes your product, selects the best operation, applies it, and measures the result against your quality gate. If the result improves the score, tokens are earned.

Check the result:

```sh
urace status
urace inspect --goals
```

---

## 5. Self-Evolve: The Runtime Improves Itself

After running cycles, the runtime may generate improvements to itself (new capabilities, better routing, efficiency gains). These are **never applied without your approval**.

To see pending runtime updates:

```sh
urace update download
urace update explain --json
```

Review the changes, then apply:

```sh
urace update apply
```

Self-evolution is governed by a strict authority boundary — see [Authority Boundary](../security/authority-boundary.md).

---

## 6. Enable the P2P Exchange

Once you have a quality improvement, you can mint it to the P2P network so other peers can borrow it (and earn tokens from every adoption).

Enable minting:

```sh
urace controls set --p2p-mint-enabled true
```

Enable the exchange and networking:

```sh
urace exchange settings set --enabled true --network true
```

Create your peer identity:

```sh
urace exchange peer identity
```

---

## 7. Mint Your Improvement to the Network

Grant equity for the feature you just built and list it for sale:

```sh
urace exchange equity grant api-response-feature --creator <your-peer-id>
urace exchange equity list-for-sale api-response-feature --bp 5000 --price 80
```

- `--bp 5000` sets your equity stake at 50% (basis points out of 10,000)
- `--price 80` sets the borrow price at 80 tokens (must be ≤ executor reference price)

When another peer borrows your feature, you earn tokens automatically.

---

## 8. Check Your Token Balance

```sh
urace exchange ledger summary
```

---

## What's Next

- [Product Lifecycle Guide](../guides/products.md) — goals, plans, operations in depth
- [Exchange Setup](../exchange/setup.md) — full exchange configuration
- [Features Guide](../exchange/features.md) — mint, borrow, and trade features
- [Concepts](concepts.md) — understand the core model
