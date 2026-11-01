# Peer Security

[← Documentation](../index.md)

URACE's P2P layer is built for adversarial environments. Here's what protects you when connecting to unknown peers.

---

## TLS 1.3 Mandatory

All peer connections use TLS 1.3 with mutual authentication. There are no fallback cipher suites and no plaintext connections.

Connections from peers that do not present a valid certificate are rejected at the transport layer before any data is exchanged.

---

## Certificate Pinning

URACE does not rely on certificate authorities. Peers are trusted only if their certificate is explicitly pinned:

```sh
urace exchange peer add --certificate peer-cert.pem
```

This means a compromised CA cannot be used to impersonate a peer. You choose exactly which peers to trust.

---

## Post-Quantum Signatures

All feature bundles are signed with a **hybrid post-quantum signature scheme**:

- ML-KEM-768 (CRYSTALS-Kyber) — post-quantum key encapsulation
- Ed25519 — classical elliptic curve signature

The hybrid scheme ensures bundles remain secure against both classical and quantum adversaries. A valid bundle must have a valid signature from both schemes.

---

## Quarantine Model

Borrowed features **never execute automatically**. When a peer sends you a feature bundle:

1. It arrives in quarantine — isolated from your product
2. URACE verifies the signature
3. You review the contents
4. You deliberately apply it

Even if a peer sends malicious code, quarantine ensures it cannot affect your system without your explicit action.

---

## IP Anonymization

- DHT peer IDs are hashed — real IP addresses are not published in the DHT
- IP addresses are never stored in the P2P audit trail
- `relay_only` mode routes all traffic through relay peers, hiding your IP from direct connections

---

## RPC Flood Protection

If a peer sends more than 10 rejected RPC calls within an hour, URACE automatically blocks them:

```
10 rejections/hour → automatic peer block
```

This protects against both accidental misconfiguration and intentional denial-of-service attempts.

---

## DHT Bootstrap Rate Limiting

DHT bootstrap attempts are rate-limited to a minimum of **5 minutes** between attempts. This prevents DHT flooding and ensures bootstrap traffic is proportional to legitimate network activity.

---

## Peer Blocking

Block a misbehaving peer immediately:

```sh
urace exchange peer block <peer_id>
```

Blocked peers cannot connect, send RPC calls, or deliver bundles until unblocked.

---

## Identity Rotation

If a keypair is compromised, rotate your identity:

```sh
urace exchange peer rotate <old_id> --new-certificate new-cert.pem
```

This migrates all your access control rules to the new identity and notifies pinned peers.

---

## Related

- [Authority Boundary](authority-boundary.md) — quarantine and governance
- [Security Overview](overview.md) — full security guarantees table
- [Network](../exchange/network.md) — peer management commands
- [Post-Quantum Roadmap](../post-quantum-roadmap.md) — future cryptography upgrades
