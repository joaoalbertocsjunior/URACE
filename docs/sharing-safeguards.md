# Sharing, ownership, anti-concentration and abuse boundaries

Design record 2026-10-29. Status labels below distinguish candidate policy/code from future economics. No live trading, token issuance or external ownership registration is enabled.

## Recommended balance

Keep URACE's core product-improvement and security functions usable without buying a marketplace feature or accumulating tokens. Permit owners to share optional improvements openly or under explicit reviewed terms. Make costs, rights, quality, dependencies and availability inspectable separately. No single scalar, popularity measure or token balance can establish fairness, useful value or authority.

An absolute globally optimal balance is unproven. Owners and users may reasonably value confidentiality, income, accessibility, competition and resource use differently. Measure these effects and expose the tradeoffs instead of silently inventing universal weights.

## Canonical records and duplication

One canonical content/version identifier represents the same logical artifact within its authorized visibility domain. Keep ownership assertions, contributor lineage, licenses, dependencies, usage grants and transfer receipts as references to it. Do not put raw proprietary artifacts or owner prompts into a public ledger. Existing candidate peer audit blocks record digests and metadata rather than artifact payloads.

Physical replicas and backups remain necessary for availability; logical deduplication does not forbid replication. Do not deduplicate private content across owners in a way that reveals its existence, equates independently granted rights or allows one owner to delete another's copy. Updating an artifact creates a new immutable content/version reference. Rename, repackage and split operations must not reset reward provenance or falsely count as new useful work.

A token/NFT-style record can identify a declared entitlement or provenance claim, but it cannot by itself prove lawful ownership, prevent copying, prove quality or make every use exclusive. On-chain tokenization is future, optional integration rather than the internal source of authority.

## Candidate enforceable owner policies

The candidate supports `product exchange feature policy` with explicit access, license reference, essential flag, resale declaration and owner-precommitted open-release time. Distribution terms are signed into each exported bundle. An existing recipient's signed terms do not silently change when the publisher changes future settings.

Default access remains reviewed-direct, payment is unavailable, ownership transfer is false and rights verification is explicitly unknown. Open sharing requires explicit reusable license terms. A feature marked essential cannot be configured as exclusively restricted. Once the owner explicitly commits to a timed open release, the effective price becomes zero at that time under the declared terms; a purchase count does not silently trigger release. Merely providing a license identifier is not independent proof that the sender has those rights.

These policies do not turn source inspection into prohibited behavior or enforce legal rights outside the system. Open sharing still respects peer/network opt-in, privacy and receiving permissions; "free" does not mean unsolicited distribution or automatic code execution.

## Economic design gates still required

Before enabling a paid market or spendable work credits, implement and adversarially validate:

* Exact independently testable feature atoms and dependency/license closure, with immutable version/contributor lineage.
* Issuer-scoped useful-work awards bound to authenticated independent acceptance or measured availability work. No self-reported CPU/tokens, useless hash grinding, duplicate receipts or circular trades may mint rewards.
* Per-issuer, per-lineage and per-beneficiary exposure caps; explicit attribution of dependencies and contributors; auditable exceptions and appeals. Identity-based caps alone do not prevent Sybil splitting.
* A fixed total reward budget per declared period where applicable. More spending or splitting cannot create additional budget; no speculative native currency is required.
* Explainable offer selection that preserves permission gates, explores unseen eligible peers, backs off temporary failures finitely and does not exclude new contributors solely for lacking history.
* Explicit voluntary funding thresholds or time-release covenants, specified before purchase, rather than retroactive confiscation or forced license changes.
* Independently validated fallback versions that meet unchanged minimum functionality/security. Lower price never excuses failing minimum acceptance.
* Public-core accessibility, data export, owner exit and non-exclusive alternatives. Paid popularity must not buy core governance, protocol authority or acceptance exemptions.
* Dispute and appeal process for false ownership, forged costs, collusion, fake availability, duplicate rewards, sham versioning and malicious reviews. Preserve evidence; do not let an unauthenticated accusation automatically seize assets or globally ban an identity.

Credit caps constrain the issuer's exposure, not proof that every market price or participant's total income is fair. URACE cannot guarantee optimal market-wide net gain, prevent all off-system collusion or stop another independent network from offering different terms. Evaluate concentration, newcomer access, creator retention, time to useful-feature availability, validated outcomes and actual resource costs before tuning these policies.

## Copying, tampering and reverse engineering

Cryptographic signatures and content hashes reject unauthorized changes. Per-peer/per-feature grants, encryption and explicit export review limit unauthorized disclosure. Sandboxed quarantine and independently sealed acceptance limit what an imported artifact can execute or alter. Blocking revokes future admissions; it cannot recall already delivered plaintext or revoke rights already granted under applicable terms.

No client-side software can guarantee that a recipient who can run or inspect it will never copy or reverse engineer it. Do not claim otherwise. Do not add intrusive monitoring, hidden resource consumption, retaliation or destructive enforcement to simulate such a guarantee.

Owners who require implementation secrecy may offer a hosted service instead of source delivery, with its uptime, privacy, independent-verification and vendor-dependence limits disclosed. Trusted execution, attestations, watermarking or obfuscation would each need a separately justified threat model and review; none is a universal solution.

Legitimate security inspection, interoperability work and vulnerability reporting must remain possible. A restriction must not protect unsafe features from scrutiny or prevent the recipient from validating what they are asked to incorporate. Actual license/legal questions need review for the chosen terms and jurisdiction; this design record is not a legal determination.

## Security and efficiency release checklist

Verify recipient/domain binding, replay/idempotency, counter-receipts, pinned identities, no silent key rotation, current permission at every admission/incorporation boundary, partial-write recovery, retained checkpoints, bounded decompression, data availability, metadata budgets and no cross-peer lock held during network waits. Test simultaneous reciprocal transfer, interrupted transfers, unavailable peers, blocked queued work, malicious payloads and incompatible dependencies.

Routine signatures, compression, peer ranking, ledger checks and accounting use local deterministic code with zero model calls. Measure CPU, bytes, latency and storage growth separately. Avoid copying large public-key descriptors or artifact payloads into every event where a verifiable canonical reference suffices. Efficient compaction preserves signed history and restore capability; it does not erase unfavorable evidence.

Candidate tests and documentation alone do not establish production security, market fairness or whole-pipeline post-quantum coverage. See the post-quantum and network-onboarding roadmaps for remaining gates.

## Development-only rewards and bundles

The user subsequently limited reward and pack/bundle experiments to development sandboxes, disabled by default. The standalone prototype lives in `dev/experiments/feature_market_v1/`; it is not imported by production, has no real wallet/network/asset transfer, and restricts writes to explicit `/tmp/urace-sandbox-*` roots. Fourteen isolated checks cover bounded simulation, caps, dependency attribution, conservative dynamic splits, cache authentication and concurrency/replay. Scenario assertions about identity, ROI and licensing are not authenticated market facts. No real credit redemption or production economy is claimed.
