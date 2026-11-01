# Post-quantum security roadmap

Design record: 2026-10-29. Status: bounded engineering release qualified and installed; whole-ledger migration and production-network security remain pending. This is not a security certification, a claim of post-quantum protection of the deployed system, or authorization to spend funds.

## Purpose and invariant

Protect URACE evidence, peer transactions and private artifacts against forgery and harvest-now/decrypt-later risks while keeping the product-improvement pipeline inexpensive. Protect every ledger through an explicit inventory and coverage report; do not label an entire deployment protected while any required writer, export, backup, tail or verifier remains outside the qualified boundary. Payment, work credits and peer reputation cannot grant execution permission or weaken acceptance.

URACE's own ledger remains authoritative for its own signed events, versions, permissions and evidence. External networks supply separately verified settlement observations. Neither chain signatures nor local signatures prove that remote resource costs, usefulness, fairness, anonymity or advertised functionality are true.

## Current, observed implementation status

* The 2026-10-29 engineering release includes the cryptography, signed-block and hybrid peer-transfer implementations. Full core/trial regression and actual isolated publication/recovery evidence bind that release; these are not independent cryptographic protocol certification.
* Candidate `ledger_crypto.py` uses PyCA cryptography 50.0.2. On this host its bundled OpenSSL backend exposes ML-DSA-65 and ML-KEM-768. The operating-system OpenSSL 3.0.13 does not itself supply these primitives.
* Candidate signatures require both Ed25519 and ML-DSA-65, bind a protocol domain and public-key identity, and reject missing or invalid components. Candidate encryption uses ML-KEM-768, HKDF-SHA-384 and AES-256-GCM with authenticated context and fresh random nonces.
* Candidate `signed_ledger.py` provides bounded canonical blocks, SHA-384 commitments, hybrid signatures, compressed storage, serialized append, explicit heads, head-write recovery and externally supplied checkpoint verification.
* Four focused tests passed: signature/domain tampering; recipient/context/ciphertext mismatch; decompression bounds/trailing data; signed-chain recovery/checkpoint/history tampering. These tests do not establish protocol-level security or complete runtime coverage.
* Hybrid peer integration is implemented and exercised in local mutual-TLS fixtures. Whole-ledger coverage/migration, key lifecycle, economic rules and network settlement still require additional implementation, independent review or qualification. External-network PQ properties are unknown unless independently established for that network and finality mechanism.

## Threat model and exclusions

Protect against hostile peers, tampered artifacts, replay, cross-protocol use, corrupt or substituted blocks, compression bombs, recipient substitution, and network interception within the implemented envelope. Treat imported instructions/code as untrusted quarantined data. Treat remote accounting and performance assertions as claims requiring independently attributable receipts and local validation.

A compromised administrator, compromised dependency/compiler, stolen signing seeds or malicious endpoint can defeat local controls. An attacker who rewrites all local state can roll history back unless another trusted party retains a checkpoint. Signatures cannot prove physical CPU consumption, prevent all identity splitting, ensure availability of disappeared peers, undo disclosed data, or make unfair economic terms fair. Confidentiality and authenticity do not hide IP addresses, timing, sizes, dependency relationships or wallet linkability.

## Cryptographic profile and agility

| Use | Initial candidate profile | Required checks |
|---|---|---|
| Message and block authentication | ML-DSA-65 AND Ed25519 | Both verify over identical domain-separated content; explicit algorithm/version/key ID; no silent classical fallback |
| Private peer content | ML-KEM-768 + HKDF-SHA-384 + AES-256-GCM | Authenticated recipient/context; bounded ciphertext; fresh nonce; authenticated out-of-band keys |
| Content commitments | SHA-384 over canonical uncompressed bytes | Exact canonical encoding, size limits, version, type and ordering |
| Transport | Existing mutually authenticated TLS plus authenticated application encryption after integration | Do not call current host TLS post-quantum; reject downgrade; bind certificate and pinned PQ identity |
| Archive protection | Signed immutable chunks/checkpoints, encrypted private replicas | Explicit covered byte range and uncovered tail; retained historical verification keys |

Prefer maintained standardized primitives and external review to invented cryptography. Algorithm agility means a versioned allowlist and migration procedure, not accepting whatever algorithm a peer proposes. Future alternatives such as SLH-DSA require measured size/latency and independent review before admission. Signature framing, KDF context, serialization and hybrid composition need protocol review even when their primitives are standardized.

## Ledger inventory and migration

Inventory peer audit/transfer/review/credit ledgers, native provider receipts, resource reservations and settlements, study/comparison histories, controller/review events, decision/milestone histories, product lineage/deployment journals and chat-assistance accounting. Enumerate exact authorized paths from application configuration and registered operation roots; never discover credentials or protected project configuration by recursive scanning.

For each ledger record: owner/product/accounting scope, writer, format, schema, sensitivity, historical byte count/hash, append semantics, rotation, key identity, verifier, retention, replicas and current protection status. Preserve existing records and reader compatibility. Seal legacy history with a dated checkpoint describing the observed bytes; never imply the checkpoint authenticates the original historical author or retroactively makes old cleartext confidential.

Migrate in stages: baseline inventory -> preserve snapshot -> signed bounded blocks/checkpoints -> dual-read verification -> fault injection -> single-writer rollout. Explicitly expose unsealed tails. Critical peer receipts and credits must be authenticated before affecting value or settlement. A periodic sidecar checkpoint protects only its declared prefix, not later writes. Recovery reconciles committed blocks, journals and head/index caches without deleting conflicting evidence.

## Key lifecycle and privacy

Separate ledger signing, recipient encryption, TLS and external-wallet authorities. Local seed storage must be owner-only, excluded from exports and logs, and backed up through an explicitly chosen secure process. No automatic wallet generation, credential reads or private-key import during roadmap preparation.

Before release implement and test initial enrollment; fingerprint/PQ descriptor verification through an independent channel; dual-authorized rotation; retained old verification keys; revocation effective times; stolen-key response; lost-key recovery; restore testing; and conflicts between peers' retained checkpoints. A classical-only certificate cannot safely bootstrap a PQ identity against a capable active quantum attacker. Do not silently trust a newly advertised replacement key.

Use pseudonymous product/peer identities, selective disclosure, encrypted artifacts and minimum necessary receipts. Public mainnet wallet activity may remain linkable. Do not publish raw owner prompts, proprietary features, private cost receipts or peer relationship graphs. Any externally anchored commitment needs an explicit privacy review and consent; commitments alone can still permit correlation or guessing.

## Blocks, compression, availability and growth

Commit to canonical logical bytes; compression is storage/transport encoding, not a different signed meaning. Bound compressed and expanded sizes, reject trailing streams and malformed content, and avoid compression of mixed attacker-controlled text and secrets in shared observable channels. Never delete historical evidence merely to shrink a ledger.

Use immutable bounded blocks, paginated retrieval and rebuildable indexes. Verify the head incrementally for ordinary append and provide complete chain/checkpoint verification separately; incremental verification is not a new full-history audit. Compression/compaction must preserve signed commitments and lineage. Define signed segment manifests and independent retained checkpoints before introducing segment rotation or pruning.

Measure logical/stored bytes, signature overhead, append/verification latency, catch-up bandwidth, growth per day and estimated retention cost. Replicas must prove retrieval of requested content, not merely advertise a hash. Availability credits require bounded fresh challenges and independently verified useful work; do not use wasteful hash grinding. Unavailable data remains explicitly unavailable. Unknown remote production cost stays unknown.

## Delivery phases and release gates

1. Inventory and frozen protocol: freeze schemas, threat model, dependencies and coverage definition. Gate: every required ledger/writer classified; no undocumented fallback.
2. Primitive and block foundations: positive/negative vectors, cross-process interoperability, canonicalization, corruption, replay, decompression and interrupted-write tests. Gate: deterministic compatibility and observed resource envelope.
3. Peer integration: signed bundles and counter-receipts; pinned hybrid identities; application encryption; replay/fork handling; blocked-peer/permission checks. Gate: actual reciprocal network fixture, timeout/retry/crash tests, no code execution on receipt.
4. Whole-pipeline migration: attributable native receipts, all ledger prefixes/tails, recovery snapshots and restores. Gate: coverage report plus end-to-end source-bound qualification, no lost historical rows.
5. Key lifecycle and independent security review: rotation/revocation/restore, dependency review, adversarial protocol review. Gate: material findings resolved; unreviewed boundaries prominently disclosed.
6. External network pilot: offline fixtures, local development chain or expressly authorized testnet, then separate owner approval for a mainnet transaction. Gate: chain identity/finality/reorg/contract/wallet/privacy/budget criteria from the network onboarding document.

Performance acceptance must be measured on representative data; set explicit owner budgets after baseline measurement, rather than inventing a universal percentage. Native executor use for sealing, peer ranking, compression, signature verification or routine polling must be zero. Verify token savings and quality separately for executor jobs.

## External-network limitation

A PQ-protected URACE receipt cannot make an external classical transaction, bridge, validator set, wallet or smart contract post-quantum secure. Default to BLOCKED_EXTERNAL_PQ_UNVERIFIED where strict PQ policy applies. Record exactly which guarantees hold locally and which fail outside the boundary. Network upgrades require a newly verified adapter/capability version and new evidence; never silently relabel old trades.

## Documentation and evidence required before release

Protocol schemas and domain constants; algorithm/parameter/dependency lock and hashes; key enrollment/rotation/revocation/recovery manual; ledger inventory and migration map; trust/privacy model; transport negotiation and downgrade rules; complete error/state catalogue; receipt attribution and unknowns; storage/availability/backup/restore procedures; resource measurements; adversarial tests and full source-bound qualification; incident response and disclosure process; compatibility policy; limitations and outstanding independent reviews.

No finite test suite proves permanent cryptographic safety or fraud-free trade. Reassess when algorithms, dependencies, exposure, attacker capabilities or integration boundaries change.

## Primary references

* NIST finalized standards announcement: https://www.nist.gov/news-events/news/2024/08/nist-releases-first-3-finalized-post-quantum-encryption-standards
* FIPS 203 ML-KEM: https://csrc.nist.gov/pubs/fips/203/final
* FIPS 204 ML-DSA: https://csrc.nist.gov/pubs/fips/204/final
* FIPS 205 SLH-DSA: https://csrc.nist.gov/pubs/fips/205/final
* PyCA ML-DSA: https://cryptography.io/en/latest/hazmat/primitives/asymmetric/mldsa/
* PyCA ML-KEM: https://cryptography.io/en/latest/hazmat/primitives/asymmetric/mlkem/
* Ethereum PQ migration context: https://ethereum.org/roadmap/security/quantum-resistance/

The PyCA latest documentation is a development branch; release qualification must verify the actual installed/pinned release API and backend, as the focused host probe did for 50.0.2.
