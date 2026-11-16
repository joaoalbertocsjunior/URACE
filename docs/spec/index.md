# Specifications

[← Documentation](../index.md)

| File | Purpose | License |
|------|---------|---------|
| [bootstrap.md](bootstrap.md) | URACE portable bootstrap blueprint — the invariants any conforming URACE implementation must satisfy | CC0 |
| [runtime.md](runtime.md) | Runtime system spec — authority hierarchy, executor contracts, token economy, P2P exchange invariants | Apache-2.0 |

`bootstrap.md` describes **what** a conforming URACE network must do — it is executor-agnostic and portable.

`runtime.md` describes **how** this implementation does it — authority scopes, lifecycle model, token invariants, P2P exchange protocol.

Both documents are complementary. `bootstrap.md` is the normative reference for any new URACE implementation; `runtime.md` is the reference for this specific runtime.

---
→ [Next: Runtime Spec](runtime.md) — authority scopes, lifecycle model, token invariants
