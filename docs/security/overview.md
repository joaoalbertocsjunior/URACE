# Security Overview

[← Documentation](../index.md)

URACE is designed with defense in depth. Every layer — networking, feature exchange, self-evolution, token economy — has independent security controls.

---

## Security Guarantees Table

| Area | Guarantee |
|------|-----------|
| Peer connections | TLS 1.3 mandatory, mutual certificate pinning |
| Bundle signatures | Post-quantum hybrid (ML-KEM-768 + Ed25519) |
| Self-evolution | No change applied without explicit owner authorization |
| Feature execution | Quarantine model — borrowed features never auto-execute |
| Token supply | Only earn path is verified quality gate pass |
| Price integrity | Executor ceiling, 1.5× momentum guard, wash trading block |
| Consensus | Persistent network size max prevents threshold lowering |
| Identity | Certificate pinning, rotation with rule migration |
| IP privacy | DHT uses hashed node IDs; no IPs in audit trail |
| Flood protection | 10 RPC rejections/hour → automatic peer block |

---

## Defense in Depth

URACE does not rely on a single security mechanism. Multiple independent defenses must fail simultaneously for an attack to succeed:

**At the network layer:**
- TLS 1.3 encrypts all traffic
- Certificate pinning prevents MITM even with compromised CAs
- Relay-only mode available for additional IP privacy

**At the feature exchange layer:**
- All bundles are cryptographically signed before transmission
- Quarantine model ensures no automatic execution
- Per-feature and per-peer access control rules

**At the token economy layer:**
- Single earn path prevents inflation
- Wash trading detection blocks circular self-dealing
- Cartel detection via trust graph analysis

**At the governance layer:**
- Self-evolution changes require explicit owner approval
- Protected files cannot be modified by the runtime
- Authority boundary separates the runtime from its own control plane

---

## What URACE Does Not Do

- URACE does not store or transmit source code without your action
- URACE does not apply changes to your product without executor + quality gate
- URACE does not transfer tokens without explicit `token_settlement` enabled
- URACE does not auto-execute borrowed features
- URACE does not modify protected files

---

## Detailed Topics

- [Authority Boundary](authority-boundary.md) — self-evolve governance, protected files
- [Peer Security](peer-security.md) — TLS 1.3, post-quantum, quarantine, flood protection
- [Price Mechanics](../economics/price-mechanics.md) — market integrity
- [Tokenomics](../economics/tokenomics.md) — supply security and cartel detection
