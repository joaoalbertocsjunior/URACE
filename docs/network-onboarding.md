# Mainnet and subnet onboarding and settlement design

Design record: 2026-10-29. Status: future integration specification; no production settlement adapter, deployed token, funded wallet, bridge, exchange listing or live network membership is claimed. No paid network connection or transaction is authorized by this document.

## Core architecture

URACE's own signed ledger is independent of external chains. It records local intents, permissions, offers, acceptance, delivery, qualification, disputes and externally observed settlement proofs. A network adapter translates only settlement-related operations for an explicitly configured network. External confirmation never substitutes for local feature acceptance, and local acceptance never fabricates external payment finality.

Keep separate: (1) internal issuer-local useful-work credits; (2) an external network's native asset and gas; (3) an external token contract; (4) optional feature licenses/entitlements; and (5) provider/subscription credits. Never combine balances, mint one from the other automatically, or imply identical value. A feature's value is not its seller's claimed resource bill.

A subnet is not a universal protocol or security level. Each subnet, rollup, sidechain or mainnet needs an explicit adapter and trust/finality model. Mainnet membership is not proof of decentralization, quality or PQ security. Native payment on an already supported chain does not require launching URACE's own public blockchain.

## Disabled-by-default capability boundary

Configuration should contain versioned adapter ID/code hash, network namespace, chain ID and genesis hash, endpoint policy, allowed assets/contracts, finality policy, wallet interface, limits, settlement mode, privacy policy and enabled=false. Distinguish UNCONFIGURED, OFFLINE_READY, TESTNET_VALIDATED, BLOCKED_POLICY, ENABLED_READ_ONLY and ENABLED_SETTLEMENT. A configuration file alone cannot earn TESTNET_VALIDATED or PRODUCTION_READY.

All preparation, offer inspection, quote checking and offline simulation must work without funds or private keys. No background paid RPC subscriptions, chain deployment, faucet request, account creation, token approval, wallet connection, bridge, transaction or external publication during this preparation. Network reads also require explicit network opt-in and bounded request/byte/time budgets.

## Adapter contract

| Operation | Required input and result |
|---|---|
| describe | Namespaced network identity, version, capabilities, authentication, PQ limitations, finality and supported assets |
| validate_network | Compare configured chain ID AND genesis hash; verify endpoint response and allowed environment; reject mismatch |
| quote | Asset base-unit integer amount, decimals metadata, fee ceiling, expiry, recipient, feature/version/license hash and both parties' terms; no floating-point currency |
| simulate | Unsigned payload, preconditions, estimated fees, contract address/code hash and explicit failure reason; simulation is not settlement |
| prepare | Immutable trade/network/asset/recipient/amount/expiry/nonce/idempotency binding and unsigned wallet request |
| authorize | Explicit owner approval through a separately selected wallet; URACE does not take custody or read seed/private-key files |
| submit | Exactly approved signed bytes, transaction hash and attributable fee observation; timeouts become SUBMITTED_UNCONFIRMED, not automatic duplicate payment |
| observe | Pending/included/finalized/reverted/dropped/reorganized status with block/hash/height/finality evidence and source identity |
| reconcile | Idempotently update the independent URACE ledger; preserve conflicting, reorg and unknown observations |
| dispute/refund | Explicit protocol/contract capability and owner process; no promise that arbitrary chains can reverse transactions |

Typed errors distinguish unsupported operation, policy denial, insufficient funds, expired quote, fee ceiling, wrong network, RPC disagreement, invalid contract, wallet rejection, timeout, reorg, bridge delay and unavailable evidence. No error path may grant a feature, mark quality passed or clear a budget/backoff automatically.

## Transaction and trade lifecycle

DRAFT -> OFFERED -> TERMS_ACCEPTED -> OWNER_AUTHORIZED -> SUBMITTED_UNCONFIRMED -> INCLUDED -> FINALIZED -> DELIVERY_CONFIRMED -> LOCALLY_QUALIFIED -> INCORPORATED, with explicit BLOCKED/EXPIRED/REJECTED/REVERTED/REORGED/DISPUTED branches. Delivery may precede payment only if both parties explicitly choose that risk. Qualification can fail after payment; the terms must define that outcome before authorization.

Record each party's separate approval; signed recipient-bound offer; exact feature atom/version/dependency closure; license/provenance; acceptance contract; settlement asset/network; price and fee caps; expiry and replay nonce; delivery hash and counter-receipt; payment evidence; refund/dispute rule and privacy disclosures. A receipt that a peer received bytes is not a receipt for a working feature.

No atomic fair exchange is claimed for arbitrary features and networks. A hashlock can protect release of a particular preimage; it cannot prove that released code is useful or meets acceptance. Smart-contract escrow and bridges add their own trust, implementation and failure assumptions. They need separate audited adapters before being offered.

## Replay, reorganization and accounting

Bind signatures and idempotency to protocol version, network namespace, chain ID, genesis hash, asset contract, trade ID, recipient, feature/version, amount, expiry and nonce. Track local sequence and external account nonce separately. On submit timeout query the identical hash/nonce; never blindly prepare a fresh payment. Do not count a pending inclusion as finalized. Finality is chain-specific, and rollup inclusion may differ from settlement finality.

Use integer base units; validate asset identity and declared decimals rather than ticker alone. Record offered price, observed transfer, gas, approval fees, bridge fees, failed transactions, waits and unknowns separately. Actual subscription/provider costs remain separate. Unknown settlement fees, remote costs and exchange rates remain unknown. Do not publish unsupported ROI or universal fair-value scores.

## Feature market and peer fairness

Owners explicitly opt in per feature/version/peer/direction. Blocked peers cannot receive new admissions or spend credits to bypass restrictions. Minimum independently usable feature atoms need tests, dependencies, provenance and licenses; splitting must not conceal required components or multiply reward claims. Contribution lineage and supersession remain immutable. A newer feature earns superiority only through compatible independent evidence; obsolete versions remain traceable.

Offer both parties' expected benefit, resource commitments and risks as separate scoped observations. Do not calculate a universal market net gain without validated utility weights and a reference population. Evidence of local useful work may earn capped issuer-local credits under declared rules; self-reported CPU/tokens and repeated replays cannot mint value. Fraud-resistant receipts improve accountability but do not eliminate collusion, Sybil identities, dishonest benchmarks or market manipulation.

An affordable older feature may be offered when its license, dependency closure and minimum security/functionality requirements still pass. Affordability cannot weaken those minimums. Owner consent is required to change price, license, dependencies, disclosure or settlement network.

## Onboarding checklist: future operator procedure

1. Select a network based on actual required settlement capabilities, costs and security. Record why it is needed and why an internal ledger alone is insufficient. This document recommends no asset purchase or investment.
2. Implement the adapter against official network documentation and freeze its source/schema/dependencies. Record unsupported capabilities explicitly. No generic adapter may claim all networks supported.
3. Obtain independent security review of payment paths, contracts, permissions, replay handling and privacy. Evaluate whether the network/wallet/bridge/finality signatures meet the configured PQ policy. Strict PQ mode blocks unverified external boundaries.
4. Configure allowlisted endpoints, chain ID AND genesis identity, asset contracts/code hashes, finality requirements, request budgets and fee ceilings. Avoid embedding RPC credentials in public files or logs; actual credential provisioning is a separate owner-managed step.
5. Validate with offline RPC fixtures and a disposable local development network. Test wrong network, counterfeit token, decimal/overflow, expired terms, nonce collision, double submission, replacement transaction, reorg, finality disagreement, endpoint tampering, wallet refusal and recovery after process interruption.
6. If separately authorized, use an unfunded or explicitly funded testnet wallet managed by the owner. Use test assets only. Preserve simulated/testnet labels and costs. Test delivery/qualification failure after payment and dispute handling.
7. Review the resulting evidence and decide whether any mainnet pilot is justified. Record human-readable terms, license, data disclosures, refunds, support and applicable legal/tax obligations for the actual jurisdictions and custody model; these have not been determined here.
8. Obtain explicit owner authorization for wallet connection, real asset allowance, spending ceiling, contract approval and first transaction. Approvals must be narrowly scoped and revocable. Never use unlimited token allowance by default.
9. Enable a bounded pilot for selected peers/assets. Observe finality/reorgs, economics, resource use and fraud signals. Disable new admissions on uncertainty without deleting prior evidence or trapping the owner's exit controls.
10. Publish an operator runbook: health, reconciliation, export, opt-out, outstanding-payment handling, incident response, adapter upgrade and rollback. Requalify after chain/contract/finality/wallet changes.

## CLI and machine-interface structure

Keep settlement inside the existing product exchange group rather than adding top-level roots. Proposed future namespace: `product exchange settlement network`, `quote`, `prepare`, `status`, `reconcile` and explicit owner-controlled `authorize/submit`. Read-only inspection should be distinct from wallet/network mutation in the shared CLI/API grammar. These are proposed commands, not installed command claims. Use the existing typed API, scoped policies, cancellation/deadline/job receipts and source/version identity; ordinary machine callers cannot acquire wallet authority by invoking an adapter.

## Required documentation and release artifacts

Network capability matrix and security model; adapter protocol/schema and compatibility policy; independent-ledger/settlement mapping; asset and contract registry; exact chain/finality identification; wallet and custody boundary; key/PQ limitations; state/error/replay/reorg recovery specification; consent and approval UX; pricing/fee/accounting definitions; privacy/export/licensing controls; testnet versus mainnet separation; security review and adversarial evidence; operational budget/storage/latency measurements; fraud/dispute/refund model; incident/exit runbooks; unresolved legal/tax analysis for actual deployment jurisdictions.

## Primary references and limits

Ethereum JSON-RPC: https://ethereum.org/developers/docs/apis/json-rpc/
Ethereum replay-domain example EIP-155: https://eips.ethereum.org/EIPS/eip-155
Ethereum transactions: https://ethereum.org/developers/docs/transactions/
Ethereum proof of stake: https://ethereum.org/developers/docs/consensus-mechanisms/pos/
Ethereum post-quantum transition: https://ethereum.org/roadmap/security/quantum-resistance/

These sources inform interface patterns, not a claim that an Ethereum adapter, subnet integration, token deployment or PQ-compatible settlement is implemented. See `post-quantum-roadmap.md` for the migration and release gates.
