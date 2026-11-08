# Security Model

[← Documentation](../index.md)

Defense in depth across transport, storage, delivery, market integrity, and network topology.

---

## Transport and identity

- **TLS 1.3** on all peer connections + certificate pinning
- **Post-quantum signatures**: ML-KEM-768 (key encapsulation) + Ed25519 (signing)
- **RPC flood protection**: rate limiting per peer per method
- **Quarantine model**: incoming artifacts are never auto-executed; require explicit owner authorization

---

## Artifact delivery — session-bound DEK

Each borrow generates a fresh encryption key (DEK) bound to the buyer's session:

```
ephemeral_keypair = X25519()
shared_secret = ECDH(ephemeral_priv, buyer_pub)
dek_key = HKDF-SHA256(shared_secret)
wrapped_dek = AES-256-GCM(dek, nonce)
wire = ephemeral_pub(32) || nonce(12) || ciphertext+tag
```

The raw DEK never appears in an audit row. Only the buyer's private key can unwrap it. The `ARTIFACT_KEY_GRANT` row holds the wrapped form only.

### Escrow auto-refund

If the seller does not deliver the DEK within 48 hours:

1. `ESCROW_REFUND` audit row emitted (idempotent)
2. `CREDIT_DELTA(direction='escrow_refund')` returns tokens to buyer
3. `CREDIT_DELTA(direction='escrow_clawback')` debits seller

Configurable via `escrow_timeout_hours` (default: 48).

---

## Storage

- **At-rest encryption**: artifact bytes encrypted in ChunkStore; replica holders store ciphertext only
- **Content-addressed**: chunks identified by SHA-256 hash; integrity verifiable without decryption
- **Erasure coding**: RS(n_data=4, n_parity=2) — reconstructible from any 4 of 6 chunks

---

## Cartel and hijack prevention

A cluster of co-registered nodes attempting to hold availability-ransom over a feature is detected and penalized:

**Two independent conditions (either alone triggers a flag):**

1. **Coverage**: cluster holds > ⅓ of distinct chunk indices (threshold = `(n_total - n_data) / n_total ≈ 0.334`)
2. **Slot count**: cluster controls ≥ `n_parity + 1 = 3` replica slots — enough to deny any RS reconstruction

**Detection mechanics:**
- Nodes are grouped into clusters by co-registration time window (default: 300s)
- BFS connected-component clustering on pairwise within-window adjacency
- `register_replica_guard()` runs pre-registration — raises `ValueError` before the row is written

**Penalty:**
- `CARTEL_CHUNK_CONCENTRATION` audit row emitted
- `CREDIT_DELTA(direction='cartel_chunk_penalty', amount=-1)` per cluster peer
- Idempotent: skips if same feature + cluster penalized within 24h

---

## Market integrity

- **Wash trading block**: self-fills rejected; circular trade detection
- **Price ceiling**: configured estimate based ceiling may be applied at listing; it is not a qualified cost savings claim
- **Minimum viable price floor**: `ask_price ≥ production_cost + bandwidth + protocol_fee`
- **Single-node cartel detection**: single peer holding disproportionate balance flagged in `credit_ledger.py`

---

## MIME replication policy

Each node auto-calibrates which MIME types to replicate based on its own feature usage history. `should_replicate()` checks the MIME policy gate first — policy-blocked types are never replicated regardless of weight.

---

→ [Asset integrity](asset-integrity.md) · [Peer security](../security/peer-security.md) · [Full security overview](../security/overview.md)
