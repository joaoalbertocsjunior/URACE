# LATEST — Recent Changes

[← Documentation](index.md)

Curated outcomes from recent releases — what changed and why it matters. This is not a changelog (that's git history) and not implementation detail (that's code). Each entry leads with the outcome and links to the doc that explains it in full.

---

## v0.9.x — Tokenomics Decoupling and Reward Calibration

**UCR token and consensus weight are now two independent layers.**
Recalibrating earn amounts no longer affects reputation scoring, and changing
consensus weights never affects token balances. The two were previously coupled,
creating risk during any parameter adjustment.
→ [Token Economics](economy/tokenomics.md)

**Service reward amounts are now viable for infrastructure operators.**
Seal, relay, and LLM-peer rewards were previously dust (10⁻⁸ UCR per event).
They are now calibrated to 0.01–0.02 UCR per event, making relay node operation
economically meaningful at the Bootstrap stage.
→ [Node Rewards](economy/node-rewards.md) · [Stage Definitions](economy/tokenomics.md#stage-definitions)

**Borrow prices are now tiered by feature scale.**
Micro features (1–50 LOC) cost ≤5% of executor price. Standard features ≤8%.
Large features ≤12%. P2P savings range from 86–95% regardless of feature size.
→ [Price Mechanics](economy/price-mechanics.md) · [Borrower Cost](economy/tokenomics.md#section-c--borrower-cost-demand-side)

**Baseline grant is now provisional and locked.**
New peers receive 3 UCR that can only be used as stake for a first bid — not
transferred. It unlocks 1 UCR per accepted delivery. This eliminates the
Sybil-farming vector where N wallets could extract 3t×N free tokens.
→ [Onboarding](economy/tokenomics.md#section-h--onboarding-provisional-grant)

**Out-of-P2P costs are now measured at runtime, not configured.**
Tokenomics (ceilings, weights, amounts) no longer need recalibration when
routing improves or local LLM peers replace executor calls.
→ [BorrowCostContext](economy/tokenomics.md#borrowcostcontext-usage)

**Asset registry is now wired into the execution paths.**
Every minted feature is automatically registered as an asset on stake lock.
Every borrow records a usage earn event. Asset earn rate and portfolio are
queryable via `urace exchange asset portfolio` and `asset opportunities`.
→ [Features: Mint, Borrow, and Trade](power-users/exchange-features.md)

**Cartel detection and sybil gate are now fully wired into the auto cycle.**
`detect_mutual_approval_cartel()` (Kosaraju SCC on QUALITY_VERIFICATION rows) and
`sybil_gate()` (5-category reputation check) now both run every 24 hours in the
daemon auto cycle, emitting `CARTEL_CANDIDATE` and `SYBIL_CANDIDATE` rows with
7-day deduplication. A tuple/dict return-type mismatch that silently suppressed
all SYBIL_CANDIDATE emission has been fixed.
→ [Sharing Safeguards](power-users/sharing-safeguards.md) · [Security Model](security/security-model.md)
