# URACE — Polygon PoS Integration Roadmap

[← Documentation](../index.md)

**Last updated:** 2026-11-16  
**Status:** Phase 1 complete (no-op adapter in place). Phase 2 begins at network traction milestone.

---

## Why Polygon PoS

URACE's trust model rests on three pillars: **consensus**, **reputation**, and **economic security**.
The off-chain ledger handles all three well for small-to-medium networks.
As the network scales, two things become important:

1. **External verifiability** — third parties (enterprises, auditors, integrators) need to verify reputation scores and stake events without trusting URACE's servers.
2. **Economic security** — stakes and slashes need real-money consequences to deter Sybil attacks and cartel formation at scale.

Polygon PoS provides both at low cost (~$0.0001/tx) without requiring every user interaction to touch the chain.

**Why not Base?** Base is Coinbase-sequenced, US-centric, and newer. Polygon PoS is independent, globally recognized since 2020, and has a stronger enterprise trust story. The adapter supports both — Polygon is the default.

**Why not Ethereum mainnet?** Gas cost per seal would be $1–$10. Unacceptable for a system that seals every few hundred operations.

---

## Architecture: Hybrid Off-Chain + On-Chain Settlement

```
┌─────────────────────────────────────────────────────────────┐
│  URACE off-chain runtime (unchanged in all phases)          │
│                                                             │
│  ledger_compaction.seal_ledger_block()                      │
│       │                                                     │
│       ▼                                                     │
│  chain_anchor.publish_seal()   ← thin adapter               │
│       │                                                     │
│       ▼  (Phase 2+)                                         │
│  Polygon PoS RPC → HashRegistry contract                    │
│                                                             │
│  provenance_stake.resolve_challenge()                       │
│       │                                                     │
│       ▼  (Phase 3+)                                         │
│  chain_anchor.publish_stake_event() → StakeLedger contract  │
└─────────────────────────────────────────────────────────────┘
```

Off-chain logic (PoQ evaluation, reputation scoring, game theory enforcement) stays entirely in Python. The chain is a notary and economic settlement layer, not the execution environment.

---

## Game Theory Coverage

| Threat | Off-chain (all phases) | On-chain addition (Phase 2+) |
|--------|----------------------|------------------------------|
| **Sybil attacks** | Reputation history + PoQ scoring | Staking cost anchored on-chain |
| **Cartel collusion** | Cross-peer reputation visibility | Slashing is economically final |
| **Cold-start** | Bootstrap peer incentives | Token rewards verifiable on-chain |
| **Proof-of-Quality fraud** | Local hash chain tamper detection | Block hash anchored = external audit |
| **Proof-of-Work fraud** | Signed work records | Sealed blocks verifiable by anyone |
| **Reputation gaming** | Stake-weighted scoring | Stake mint/slash publicly visible |

---

## Phase 1 — No-op Adapter (current, complete)

**What exists now:**

- `urace/chain_anchor.py` — full adapter interface, completely no-op when `enabled=false`
- Hook in `ledger_compaction.seal_ledger_block()` calls `chain_anchor.publish_seal()` on every seal
- Hook in `provenance_stake` calls `chain_anchor.publish_stake_event()` on mint/slash/resolve
- Config schema documented under `ledger.chain_anchor`

**Config (default, no action taken):**
```json
{
  "ledger": {
    "chain_anchor": {
      "enabled": false,
      "network": "polygon-amoy",
      "dry_run": true
    }
  }
}
```

**Zero capability netloss.** Zero maintenance burden. Zero gas cost. All existing ledger behavior unchanged.

---

## Phase 2 — Reputation Anchoring (trigger: 500+ active nodes)

**Goal:** Publish `block_hash + block_height` to HashRegistry contract on Polygon PoS.  
Any external party can verify that URACE's ledger state matches the on-chain hash.

**What to build:**

1. Deploy `HashRegistry.sol` to Polygon Amoy testnet:
```solidity
// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.20;

contract HashRegistry {
    mapping(uint64 => bytes32) public seals;
    address public immutable owner;

    constructor() { owner = msg.sender; }

    function store(bytes32 blockHash, uint64 blockHeight, bytes32 rowsHash) external {
        require(msg.sender == owner, "unauthorized");
        seals[blockHeight] = blockHash;
        emit Sealed(blockHeight, blockHash, rowsHash, block.timestamp);
    }

    event Sealed(uint64 indexed blockHeight, bytes32 blockHash, bytes32 rowsHash, uint256 at);
}
```

2. Configure `chain_anchor` in production:
```json
{
  "ledger": {
    "chain_anchor": {
      "enabled": true,
      "network": "polygon-pos",
      "rpc_url": "https://polygon-rpc.com",
      "hash_registry_address": "0x...",
      "dry_run": false,
      "publish_every_n_seals": 1
    }
  }
}
```

3. Set `URACE_CHAIN_KEY` env var with the hex private key of the publisher wallet.

4. Install web3.py: `pip install web3` (MIT, optional — graceful no-op if absent).

**Runtime change:** zero — `chain_anchor.publish_seal()` is already the hook point.  
**Cost per seal:** ~$0.0001 (Polygon PoS, ~21,000 gas × current MATIC price).  
**Maintenance burden:** minimal — contract is immutable, adapter is ~50 LOC.

**User experience:** invisible. No wallet required for normal users.

---

## Phase 3 — Staking + Slashing on Chain (trigger: token liquidity or enterprise requirement)

**Goal:** `provenance_stake.py` mint/slash/resolve events are anchored to `StakeLedger.sol`.  
Stakes have real MATIC (or future URACE token) value. Slashes are economically final.

**What to build:**

1. Deploy `StakeLedger.sol` to Polygon Amoy testnet:
```solidity
// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.20;

contract StakeLedger {
    uint8 constant MINT    = 0;
    uint8 constant SLASH   = 1;
    uint8 constant RESOLVE = 2;

    event StakeEvent(
        bytes32 indexed featureId,
        bytes32 indexed peerId,
        uint64 amount,
        uint8 kind,
        uint256 at
    );

    function record(bytes32 featureId, bytes32 peerId, uint64 amount, uint8 kind) external {
        emit StakeEvent(featureId, peerId, amount, kind, block.timestamp);
    }
}
```

2. Add `publish_stake_event()` calls in `provenance_stake.py` at mint/slash/resolve points.

3. Add `stake_ledger_address` to config.

**Runtime change:** minor — 3 call sites in `provenance_stake.py`.  
**Cost per stake event:** ~$0.0001.  
**Maintenance burden:** low — contract is an event log, no upgradeable logic.

---

## Phase 3.5 — Earn-Backed Asset Certificates (trigger: active asset trading)

**Goal:** Assets (code features, improvements) are ownable, transferable, and earn royalties proportional to real usage. Anyone can audit the earn rate. This separates trade reputation (asset holders) from earned reputation (contributors) — permanently and verifiably.

**Key design invariant:**
- Earned reputation = soulbound, non-transferable, reflects contribution quality
- Trade reputation = transferable, reflects asset ownership and royalty income
- These are ALWAYS displayed separately — buying assets never inflates earned reputation

**What to build:**

`asset_registry.py` — already implemented (off-chain, no-op on-chain until Phase 3.5 activates).

Deploy `AssetRegistry.sol` to Polygon Amoy testnet:
```solidity
// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.20;

contract AssetRegistry {
    struct Asset { bytes32 ownerId; uint64 cumulative; uint256 lastUpdated; }
    mapping(bytes32 => Asset) public assets;

    event EarningRecorded(bytes32 indexed featureId, bytes32 indexed ownerId,
                          uint64 earnUnits, uint64 cumulative, uint256 at);
    event OwnershipTransferred(bytes32 indexed featureId, bytes32 indexed from,
                               bytes32 indexed to, uint64 cumulativeAtTransfer, uint256 at);

    function recordEarning(bytes32 featureId, bytes32 ownerId,
                           uint64 earnUnits, uint64 cumulative) external {
        assets[featureId] = Asset(ownerId, cumulative, block.timestamp);
        emit EarningRecorded(featureId, ownerId, earnUnits, cumulative, block.timestamp);
    }

    function transfer(bytes32 featureId, bytes32 newOwnerId,
                      uint64 cumulativeAtTransfer) external {
        bytes32 prev = assets[featureId].ownerId;
        assets[featureId].ownerId = newOwnerId;
        assets[featureId].lastUpdated = block.timestamp;
        emit OwnershipTransferred(featureId, prev, newOwnerId, cumulativeAtTransfer, block.timestamp);
    }

    function getCumulative(bytes32 featureId) external view returns (uint64) {
        return assets[featureId].cumulative;
    }
}
```

Add `asset_registry_address` to config. Hook `asset_registry.record_usage_earn()` to call `chain_anchor.publish_asset_earning()`.

**NOT an ERC-721.** This is a custom registry optimised for URACE's use case — no IPFS metadata, no marketplace compatibility bloat, no speculative trading surface. The "NFT-like" property (unique ownership, transferable, auditable history) comes from the registry semantics, not the ERC standard.

**Auditability:** anyone can call `getCumulative(featureId)` on Polygon to verify an asset's earn history. Earn rate = cumulative delta / time window. This is the figure that determines fair market value — no speculation required.

---

## Phase 4 — Native Token (optional, post-PMF only)

Deploy an ERC-20 `URACE` token on Polygon PoS. Replace MATIC-denominated stakes with URACE tokens.

**Decision gate:** Only pursue if network effects clearly justify a token economy.  
**Risk:** "another crypto" framing. Mitigate by positioning token as infrastructure (like LINK, not like ICO tokens).  
**Prerequisite:** Phase 3 fully live and stable.

This phase is not planned — it is listed here as a decision point, not a commitment.

---

## Maintenance Burden Assessment

| Phase | New files | Changed files | Ongoing burden |
|-------|-----------|--------------|----------------|
| Phase 1 (done) | `chain_anchor.py` | `ledger_compaction.py` (+12 LOC) | None — no-op |
| Phase 2 | `HashRegistry.sol` | None (adapter already written) | Low — wallet key rotation, RPC endpoint |
| Phase 3 | `StakeLedger.sol` | `provenance_stake.py` (+3 call sites) | Low — contract is immutable |
| Phase 4 | ERC-20 contract | `chain_anchor.py` token address | Medium — token governance |

The hybrid design keeps maintenance burden low by design: the chain is append-only event storage. No upgradeable contracts, no on-chain logic to maintain, no gas optimization loops.

---

## "Is this just another crypto?"

No — if framed correctly.

The chain is infrastructure, not the product. URACE's value proposition is autonomous code improvement and P2P reputation. The chain anchors trust. Users never see gas fees, wallets, or transactions in normal operation.

Framing to avoid: "AI + blockchain", "decentralized AI", "tokenized intelligence"  
Framing to use: "verifiable reputation", "tamper-evident audit trail", "stake-backed quality signals"

The difference is whether the chain is a feature you sell or a foundation you rely on. It should be the latter.

---

## Transition Checklist

- [x] Phase 1: `chain_anchor.py` adapter stub
- [x] Phase 1: hook in `ledger_compaction.seal_ledger_block()`
- [ ] Phase 2: deploy `HashRegistry.sol` to Polygon Amoy
- [ ] Phase 2: test with `dry_run: true` on staging
- [ ] Phase 2: enable on production, monitor gas costs
- [ ] Phase 3: deploy `StakeLedger.sol`
- [ ] Phase 3: add call sites in `provenance_stake.py`
- [ ] Phase 3: add `stake_ledger_address` to config schema docs
- [ ] Phase 4: decision gate review

---
→ [Next: Operational Readiness](operational-readiness.md) — features with complete runtime code awaiting external setup
