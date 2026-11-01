# Ethereum patterns: adopted selectively

URACE is a product-improvement controller, not a cryptocurrency or general smart-contract platform.

Useful patterns adopted in the peer ledger design:

* Signed, domain-separated messages with explicit protocol version and recipient.
* Per-author sequence numbers and previous-block commitments, rejecting replay and conflicting history.
* Explicit transfer, quarantine, review, qualification and incorporation states. Delivery is not quality.
* Bounded work and storage allowances before admission, analogous to gas limits but without a token fee market.
* Immutable evidence with rebuildable indexes and independently verifiable compressed blocks.
* Signed checkpoints with explicit data availability and historical/unsealed scope.

Not adopted: EVM execution, public token markets, proof-of-work grinding, global replication of private artifacts, or permission grants based on stake/credits. Those add attack surface and operating costs without demonstrated benefit for the current pairwise exchange. Useful-work credits, if enabled, are issuer-local, capped and distinct from provider credits; they never prove feature value or confer execution authority.

Ethereum uses proof of stake, not mining. Its existing elliptic-curve signatures do not satisfy URACE's post-quantum requirement. URACE's candidate uses standardized ML-DSA-65 plus Ed25519 signatures and ML-KEM-768/AES-256-GCM application encryption, with explicit identity pinning and no classical downgrade. This does not claim post-quantum TLS, anonymous networking, fraud-free economics or independently audited protocol security.

Sources: https://ethereum.org/developers/docs/transactions/ ; https://ethereum.org/developers/docs/consensus-mechanisms/pos/ ; https://ethereum.org/roadmap/security/quantum-resistance/ .
