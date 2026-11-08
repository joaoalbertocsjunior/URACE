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
| Artifact integrity | Content-addressed store (SHA-256); `artifact_ref` verified on every receive |
| Bundle single-holder risk | Warning emitted on `list-for-sale` if no replica holders exist |
| Circular transfer / laundering | 24h window detection blocks circular credit flows |
| Price evidence | No P2P consensus price ceiling is enforced; declared reference values are estimates, not measured executor costs |
| Sybil token farming | Bootstrap grant locked until first quality gate pass; 1 trial borrow limit |
| Delivery fraud | `DELIVERY_FEE` only paid on verified `BUNDLE_REPLICA_REGISTERED` holders; `FEATURE_BORROWED` always credits original creator |
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
- Bootstrap grant locked until quality pass prevents Sybil token farming
- Consensus applies to selected exchange protocol decisions, not executor cost or feature prices. Peer prices and reputation credits are not proof of lower execution cost.

**At the artifact distribution layer:**
- All artifact bytes stored content-addressed (SHA-256); integrity verified on receive
- Bundle single-holder risk warning emitted on listing — promotes replication
- Delivery fee only paid for registered replica holders (verified in audit log)
- Original creator credit is always correct regardless of delivery path

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

## Run a Security Audit

Check your local deployment posture at any time — no external connections required:

```sh
urace security audit
urace security audit --json
```

The audit checks:
- Wallet key file permissions (`~/.urace/wallet/key.json` should be chmod 600)
- Peer certificate pinning hygiene
- Authority boundary integrity
- Compliance mode status
- Capability flag anomalies (e.g., minting enabled without an identity)
- Audit trail completeness for state-modifying commands

Each finding includes a severity (`info`, `warning`, or `critical`) and a remediation hint. Any `critical` finding returns a non-zero exit code so CI/CD pipelines can catch it automatically.

---

## Detailed Topics

- [Authority Boundary](authority-boundary.md) — self-evolve governance, protected files
- [Peer Security](peer-security.md) — TLS 1.3, post-quantum, quarantine, flood protection
- [Price Mechanics](../economics/price-mechanics.md) — market integrity
- [Tokenomics](../economics/tokenomics.md) — supply security and cartel detection
