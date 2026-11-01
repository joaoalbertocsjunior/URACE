# Concepts

[← Documentation](../index.md)

Understanding URACE's core model makes every command make sense.

---

## Products

A **product** is any software system you attach URACE to. URACE does not care what language it's written in or where it runs. You initialize a product with `urace init` and URACE starts tracking its lifecycle.

Each product has:
- **Objectives** — goals you want to achieve (added with `urace add`)
- **Plans** — concrete steps derived from objectives
- **Operations** — individual actions the executor takes
- **Evidence** — recorded outcomes from each operation

---

## Goals → Plans → Operations

URACE follows a structured lifecycle:

```
Objectives (what you want)
    ↓
Plans (how to get there)
    ↓
Operations (what to do right now)
    ↓
Evidence (what happened)
```

Each call to `urace run` selects the best next operation from the current plan, executes it, measures the quality delta, and records the result as evidence.

---

## Quality Gates

Every operation is evaluated against a **quality gate** — a score that reflects how well the product meets its objectives. The gate is not a pass/fail test; it is a continuous signal. A positive delta means the product improved.

Tokens are earned only when the quality gate passes. This ensures the token supply is backed by real verified improvements.

---

## Executors

An **executor** is the agent that carries out operations. The default executor uses the configured AI model. You can enable or disable executors per product using `urace controls set --executor-enabled`.

---

## Freeform Routing

URACE accepts unstructured text and routes it to the right command, executor, or P2P action automatically. You don't need to know the exact command syntax for every operation — type what you mean and URACE resolves it.

Enable or disable freeform routing:

```sh
urace controls set --freeform-enabled true
```

---

## Self-Evolution

URACE can improve its own runtime. When the runtime generates a self-improvement proposal, it is staged for your review — never applied automatically. You review with `urace update explain` and apply with `urace update apply`.

See [Authority Boundary](../security/authority-boundary.md) for how this is governed.

---

## P2P Exchange

The exchange is an optional marketplace where peers share verified software features. You earn tokens by improving your product; you spend them to borrow features from peers.

The exchange is **off by default**. Enabling it is an explicit opt-in.

See [Exchange Overview](../exchange/overview.md).

---

## Tokens

Tokens are not a speculative currency — they are proof of verified contribution. You earn them by passing quality gates and spend them to borrow from the network.

See [Tokenomics](../economics/tokenomics.md) for the full model.

---

## Related

- [Quick Start](quick-start.md) — see concepts in action
- [Products Guide](../guides/products.md) — detailed lifecycle operations
- [Security Overview](../security/overview.md) — what URACE guarantees
