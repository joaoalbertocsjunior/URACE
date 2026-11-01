# URACE System Spec

[← Documentation](../index.md)

What URACE guarantees, what the lifecycle looks like, and the invariants that hold across all deployments.

---

## What URACE Is

URACE is a lifecycle control plane for AI-assisted software products. It provides:

- **Goal tracking**: record and evolve what your product is supposed to do
- **Execution governance**: run improvement cycles with quality gate enforcement
- **Token reputation**: earn tokens from verified improvements, spend to borrow from peers
- **P2P feature marketplace**: share and acquire verified software capabilities
- **Self-evolution under governance**: the runtime can improve itself, subject to owner authorization

---

## Lifecycle Invariants

These hold in all URACE deployments:

1. **One earn path**: tokens are earned only from quality gate passes. No other mechanism creates tokens.
2. **No automatic self-modification**: the runtime never applies changes to itself without `urace update apply`.
3. **Quarantine before execution**: borrowed P2P features are never executed automatically.
4. **Executor price ceiling**: P2P borrow price ≤ executor reference price. Borrowers always save vs. building from scratch.
5. **Append-only ledger**: the context ledger is never modified retroactively.
6. **Protected files**: governance files cannot be modified by the runtime.
7. **Consensus persistence**: the P2P consensus threshold uses the all-time maximum network size, never a lower current estimate.

---

## Product Lifecycle Model

```
init
  ↓
add objectives
  ↓
run cycle ──────────────────────────────┐
  ↓                                     │
select operation (from plan)            │
  ↓                                     │
execute (executor)                      │
  ↓                                     │
measure quality delta                   │
  ↓                                     │
record evidence                         │
  ↓                                     │
quality gate pass? → earn tokens        │
  ↓                                     │
update plan                             │
  └───────────────────────────── repeat ┘
```

Each cycle is atomic. If execution fails, the quality gate does not pass and no tokens are earned.

---

## P2P Lifecycle Model

```
enable exchange
  ↓
create peer identity
  ↓
discover peers / pin peers
  ↓
mint features (after quality gate pass)
  ↓
peers discover listings
  ↓
peer borrows feature → tokens transfer to seller
  ↓
borrowed feature enters quarantine on buyer side
  ↓
buyer applies deliberately
```

---

## Quality Gate

The quality gate is a continuous score, not pass/fail:

- `score_delta > 0`: improvement — tokens earned
- `score_delta = 0`: no change — no tokens earned, no penalty
- `score_delta < 0`: regression — no tokens earned, operation recorded as failed evidence

Quality is measured relative to objectives. Each objective contributes a weighted component to the overall score.

---

## Token Economy

- **Supply**: derived from network capacity (sync budget), not arbitrary
- **Earn**: quality gate pass only
- **Spend**: borrow features, commission work
- **Settlement**: disabled by default; enabled explicitly via `token_settlement`
- **Precision**: 8 decimals (satoshi model)

---

## Self-Evolution Model

When the runtime generates a self-improvement:

1. Proposal is staged locally
2. Owner reviews with `urace update explain`
3. Owner applies with `urace update apply` (or discards)
4. Cryptographic signature verified before apply
5. Protected files excluded from any proposal

---

## Authority Hierarchy

```
Owner (you)
  └── Runtime (proposes, executes within permissions)
        └── Executor (builds features, measures quality)
              └── P2P Network (peers, features, work)
```

Each layer can only act within the permissions granted by the layer above. The runtime cannot grant itself new permissions.

---

## Supported Deployment Modes

| Mode | Description |
|------|-------------|
| Local-only | No P2P, no exchange. Pure lifecycle tracking and execution. |
| Local + self-evolve | Runtime improvements with owner review. No P2P. |
| Full P2P | Exchange enabled. Peer discovery, minting, borrowing. |
| Machine interface | `--json` outputs and `machine_interface_enabled` for CI/CD integration. |

---

## Related

- [Concepts](../getting-started/concepts.md) — conceptual overview
- [Security Overview](../security/overview.md) — security guarantees
- [Authority Boundary](../security/authority-boundary.md) — governance model
- [Tokenomics](../economics/tokenomics.md) — token model
