# Asset Integrity — ALE and APS

[← Documentation](../index.md)

URACE enforces two independent mechanisms to ensure only original work reaches the market.

---

## Asset Lineage Enforcement (ALE)

Every feature grant passes three detection layers before it is accepted:

### Layer 1 — Exact fingerprint
SHA-256 of the raw artifact bytes. Any byte-for-byte copy is rejected immediately.

### Layer 2 — Perceptual similarity (dHash + Winnowing)
- **dHash**: perceptual image hash — catches visually identical or near-identical images even after re-encoding, cropping, or minor edits.
- **Winnowing shingle overlap**: document-level fingerprinting — catches copy-paste of text, code, or data at ≥ 60% Jaccard overlap.

### Layer 3 — LLM-peer SIMILARITY_CHECK
Independent peers run a semantic check and return a `SIMILARITY_VERDICT`. Rewarded with `llm_peer_reward`.

### Bundle / feature-pack protection
Layers 2 and 3 run **per member** inside a decomposed bundle — not on the aggregate. A pack of 5 stolen files each at 20% similarity is flagged (each member exceeds the per-member threshold). A grant where `sum(decomp_weights) > 0.95` — more than 95% of content traces back to known sources — is hard-blocked with a `ValueError`.

Empty artifacts are rejected at grant time.

---

## Asset Provenance Staking (APS)

After a feature is minted, the creator locks a stake for 30 days. During this window:

1. Any peer can submit a challenge with evidence.
2. If the challenge succeeds: stake is slashed, `provenance_compensation` CREDIT_DELTA goes to the original creator.
3. If the challenge fails: challenger's stake is locked (`challenge_stake_locked`).

This creates economic skin-in-the-game for originality claims.

---

## MIME artifact quality validators

Before an artifact is stored, structural validators run per content type:

| MIME type | Validation |
|-----------|------------|
| `image/*` | Magic bytes (PNG, JPEG, GIF, WebP, BMP) |
| `text/csv` | Column count consistency across rows |
| `application/pdf` | At least one `BT`…`ET` text block present |
| `application/json` | Parses as JSON; non-empty |
| `text/x-python`, `text/plain` | ≥ 3 non-blank lines |
| `application/zip` | ZIP magic bytes + ≥ 1 member file |

`validate_asset(raw_bytes, content_type)` → `(bool, reason_str)`.
`validate_asset_strict()` raises `ValueError` on failure.

---

→ [Security model](security-model.md) · [Node rewards](node-rewards.md)
