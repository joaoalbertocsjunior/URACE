# Automation, feature economics and feature bundles: retained design requirements

Recorded 2026-10-29. These requirements arrived during release qualification. This document preserves them without falsely claiming their full implementation. The qualified release already supplies some foundations; a decentralized token economy and production settlement are not implemented by documenting them.

## Core direction and defaults

Refinement targets: owner-intent fidelity, independently accepted improvement, complete resource efficiency, context/sequence quality, continuity/shared interfaces, controlled reuse and independent retained user benefit. The candidate exposes these through comprehensive assessment without model calls or self-awarded scores.

Local assessment, bounded metadata interpretation, requirement coverage and recommendations may run automatically. Automatic changes need a narrow declared allowlist, attributable expected benefit, unchanged quality/authority/resource floors and a reversible source-bound transaction. Defaults must not silently enable network participation, disclose a feature, mint an asset, spend funds, accept arbitrary updates or expand authority.

| Capability | Recommended starting policy | Current release scope |
|---|---|---|
| Local assessment, decision feedback and milestone suggestions | Enabled automatically; no extra native call merely to restate metadata | Implemented local controls/feedback; external benefit still needs evidence |
| Task-relevant skill/context packets | Enabled within bounded task scopes | Candidate implemented; not arbitrary native plugin installation |
| Adaptive operational settings | Recommendations enabled; automatic application separately opt-in and allowlisted | Broad autonomous settings tuner still requires implementation/qualification; existing effort and owner controls remain |
| Peer metadata ranking | Auto while owner explicitly runs enabled network service | Candidate implemented; sharing/network default off |
| Public sharing/trading/minting and paid purchases | Separate explicit opt-in per product/feature/peer/action and spending ceiling | Network/permissions and feature policies implemented; production economics/minting/purchase not implemented |
| Dynamic distribution-mode selection | Suggest first; apply only within explicitly preauthorized modes, license and disclosure limits | Future policy engine; no silent release or repricing of an existing grant |
| Alternative-feature fallback | Opt-in, scope/authority/quality constrained | Economic selection beyond current feature-match ranking not yet qualified |
| Authority changes by a higher orchestrator | Explicit owner-delegated narrow policy; default no authority expansion | Existing machine interface supports explicit operator policy; autonomous grant redesign not claimed |
| Update check/stage | Local inspection by default; no automatic application | Existing staged/hash-pinned workflow retained |
| Upgrade/application and complete combined workflow | Explicit opt-in auto-approval, independent acceptance and rollback; preserve legacy command aliases | Existing apply controls retained; a new Linux-like update/upgrade command split is not implemented here |

No "always non-breaking" guarantee is justified. Require declared compatibility versions, migration and rollback tests, unchanged public-contract checks and explicit refusal when compatibility is unknown. Retain legacy CLI/API aliases unless an expressly approved migration is necessary.

## Meaning of a feature

Use "button" as the example name. The unit is not merely a word or source line: it must bind observable behavior, interface, independently testable acceptance and dependencies. A minimal useful unit depends on context. Splitting every line into a tradable unit increases coordination cost and can game rewards.

Candidate catalogue declarations are content-addressed and immutable by version alias; dependencies must already exist, cycles are rejected, repeated declarations/aliases do not duplicate the atom or mint rewards, and lifecycle changes preserve history. Raw content is referenced rather than copied into the catalogue ledger. Atomicity and semantic equivalence remain explicitly unproven until independent review and acceptance support them.

## Credits, reputation, prestige and bonuses

Do not mint spendable credits merely because someone downloads a feature. Grab bots and colluding identities can manufacture those events. Merely publishing a new feature also does not prove useful work: copied, split, irrelevant or failing features must not earn rewards by declaration. Writing a block is not independently valuable unless it performs requested, verifiable availability/validation work.

A safer proposed system uses capped issuer-scoped budgets for independently validated useful contributions and availability work, with duplicate-proof work IDs, contributor/lineage attribution, verified outcomes, explicit issuer obligations and auditable spending. A grab/purchase transfers an existing usage entitlement/payment; it does not create currency. Free sharing remains zero-price under explicit license and may accrue separately scoped non-transferable reputation/prestige only from verified outcomes. Any monetary bonus comes from a fixed declared budget; it is not free unbacked value.

Reputation, prestige and bonus are distinct reward forms, not interchangeable balances. Repeated use, Sybil identities and circular trades must not amplify unverified reputation. Show sample counts, uncertainty, dependence and potential manipulation. Avoid using reputation as permission, a security exemption or an automatic monopoly multiplier.

Issuer-local credits are not a globally scarce transferable network token. Transferable network credits require a separate distributed state/consensus design, finality, double-spend protection, governance, key lifecycle, economic review and adversarial pilots. None is supplied by a local signed log. Maintainers must have no protocol override; independent validators reject invalid transitions and require the necessary parties' signatures. A local administrator can modify their own software, but cannot thereby make honest remote validators accept invalid state. Preserve checkpoints outside the author's control.

## Ownership, usage and public persistence

A buy normally grants explicit usage rights, not ownership. An optional ownership transfer is a different mutually authorized transaction and must preserve prior grants, contributor attribution, dependencies and legal limits. An NFT or signed record alone does not establish legal ownership or prevent copying. No current on-chain ownership transfer is claimed.

Public minting would require explicit informed consent about persistence, license, disclosures, replication and inability to retract already distributed copies. Never automatically convert an existing private feature to irrevocably public property. A ledger commitment can persist while content becomes unavailable; use bounded retrieval/replication checks rather than claiming permanent availability.

GPL-style copyleft permits recipients to redistribute without requiring later recipients to pay the original publisher. It is incompatible with calling a mandatory per-user ledger royalty "GPL copyleft." Choose either an actual compatible open-source license with optional paid delivery/support, or a separately reviewed paid usage license; do not silently combine incompatible obligations. Existing rights cannot be retroactively removed by a new price or NFT transfer.

Sources: https://www.gnu.org/licenses/gpl-faq.en.html#DoesTheGPLAllowRequireFee ; https://www.gnu.org/licenses/gpl-3.0.en.html . Actual terms need review for the selected license/jurisdiction; this document does not resolve those legal questions.

## Worth, suitability and build-versus-buy

The decision set is buy/license, free share, borrow/hosted service, reuse an existing entitlement, construct locally, postpone or no change. "Best worth" means most suitable feasible candidate and, when sufficiently measured, highest expected net benefit/ROI within the owner's products, objectives, scope, budget, acceptance, disclosure and authority limits. A cross-scope candidate is eligible only if the owner opted in and it helps those objectives without neglecting required functionality.

Include complete acquisition, integration, adaptation, validation, support, dependency, network, failure, waiting and maintenance costs. Compare the buyer's benefit and each party's verified resource commitments separately; remote production cost is not automatically the buyer's value. Unknown cost/benefit remains unknown. Do not rank a fake numerical ROI when a denominator is unknown or zero.

A costly "button" should compete with a free compatible implementation and the ordinary pipeline's cost of building it. If no permitted purchase is justified, the normal authorized pipeline may construct the feature under unchanged acceptance and admission. This is not permission for unbounded model-driven negotiation or blind repeated rebuilding. Respect existing product priorities and stop/reconsider conditions.

Market demand and uniqueness may inform a quote, but neither proves quality, utility, scarcity of copyable code nor a fair price. Use scoped evidence, fee/price ceilings, quote expiry and explicit terms; do not force a continuously changing ledger price onto an already granted license. No globally optimal or monopoly-free pricing rule has been established.

## Feature bundles

Apply the same controls to bundles, plus dependency/license compatibility and whole-bundle acceptance. A feature bundle is a canonical manifest of exact atom versions and dependencies; it does not duplicate their payloads or create automatic additional rewards. Do not confuse this with the existing transport CLI's signed artifact "bundle."

Compare bundle cost and integration benefit against individual components, already owned rights, alternatives and local construction. Prevent double charging/rewarding shared dependencies, sham repackaging, hidden mandatory components and duplicate contributor claims. Atomicity means either all required grant/delivery conditions complete or the transaction remains explicitly partial/disputed; arbitrary cross-network atomic fair exchange is not assumed.

Automatic economic bundles remain experimental and separately opt-in until independent acceptance, rollback, partial-delivery, license conflicts, pricing and abuse tests pass. Default receipt/import behavior remains quarantine rather than code execution.

## Higher-level orchestration

Expose installed operation discovery, exact typed parameters, finite jobs, idempotency, cancellation, deadlines, shared resource receipts and explicit permission scopes. Higher-level orchestration may select sequences within declared authority. It cannot bypass peer ledger rules, backoff, isolation, source qualification or required owner consent. Delegated operator capability is explicit; do not give a generic freeform string permission to invent new authority.

A full orchestration/freeform interpretation envelope should retain original text, requirement IDs, ambiguity/relationship status, proposed operations, costs/unknowns and required approval. Preserve the existing distinction between interpretation, queueing, execution, acceptance and actual benefit. The candidate's source coverage and clarification mechanisms improve this boundary but do not prove perfect intent understanding.

## Delivery and proof gates

Stabilize the qualified core first, gather compatible matched comparisons, and then validate independent retained-user benefit. Simulations stay labeled. Financial/token economics, independent consensus, autonomous pricing and licensing obligations need separately frozen protocols and adversarial evidence before activation. These remain requirements, not completed capabilities or claims erased from the report.

## Latest scope clarification

Rewards and economic feature packs/bundles are development-sandbox experiments only, disabled by default. A standalone prototype implements simulated funded reward caps, reputation/prestige observations, base-owner floors, opt-in prospective dynamic allocations, dependency closure, identity/duplicate checks within fixture assumptions, and suitable net-benefit/build alternatives. It makes no real payment, mints no network credit, and transfers no ownership. It cannot authenticate independent real users or market ROI from input booleans. See `dev/experiments/feature_market_v1/README.md`.

"Equity" is interpreted as contribution-linked revenue/reward sharing, not company shares. Ownership transfer remains a distinct explicit opt-in. A paid right to use and redistribute with mandatory royalties needs reviewed royalty-bearing terms; it is not standard GPL copyleft. Future accepted splits must be frozen before execution and preserve base-owner terms and prior grants.

The existing production update command already exposes download/explain and apply/resolve phases, plus a combined `urace update --source SOURCE` flow. Explicit `--yes` opts in to queueing without an interactive confirmation; migration still requires the owner policy and independent validation. Do not add redundant top-level commands merely to imitate Linux names. No unattended paid updater or automatic authority expansion was enabled.
