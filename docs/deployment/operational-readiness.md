# Operational Readiness

[← Documentation](../index.md)

This document covers features whose **runtime code is complete and tested** but whose full activation requires external operational setup — a live EVM node, real network peers, funded wallets, or public endpoints.

These are not spec gaps. The runtime modules exist, import cleanly, and are covered by the test suite. What's missing is infrastructure, not code.

---

## 1. EVM On-Chain Settlement

**Runtime module:** `eth_settlement_adapter.py`  
**Status:** Code complete. `on_ramp`, `off_ramp`, `mint_nft`, `verify` all produce proper EIP-155 RLP-signed transactions with real nonce, gas price, and ABI calldata.

**What you need:**

| Requirement | Description |
|-------------|-------------|
| JSON-RPC endpoint | Alchemy, Infura, QuickNode, or `http://localhost:8545` (Hardhat/Anvil) |
| Funded wallet | Private key with ETH for gas; set up via `urace exchange wallet generate` |
| Deployed ERC-20 contract | The URACE token contract address |
| Deployed NFT contract | For feature attestation minting |

**Activation:**

```json
{
  "p2p": {
    "token_settlement": true,
    "rpc_provider_url": "https://mainnet.infura.io/v3/YOUR_KEY",
    "erc20_contract": "0xYOUR_TOKEN_CONTRACT",
    "nft_contract_address": "0xYOUR_NFT_CONTRACT",
    "wallet_dir": "/path/to/wallet"
  }
}
```

```sh
urace exchange settings set --token-settlement true
```

**What activates:** `get_chain_adapter()` in `integration_bridge.py` returns `EthSettlementAdapter` instead of `NullAdapter`. All `stub_nft_mint`, `stub_crypto_on_ramp`, `stub_crypto_off_ramp` calls broadcast real signed transactions.

---

## 2. Cross-Peer Purchase Settlement

**Runtime module:** `purchase_settlement.py`  
**Status:** Code complete. `initiate_purchase`, `handle_purchase_settlement`, `settlement_state` are all implemented and tested.

**What you need:**

| Requirement | Description |
|-------------|-------------|
| Two live peers | Both must be running `urace exchange network serve` |
| Mutual pinning | Each peer must have the other pinned (`urace exchange peer pin`) |
| `token_settlement=true` | Settlement mode enabled on both sides |
| Feature listed | Seller must have an open equity listing |

**Flow:**

1. Buyer calls `fill-listing` — `equity_auto_trade.fill_listing()` calls `initiate_purchase()` automatically.
2. `initiate_purchase()` deducts locally, sends signed `PURCHASE_SETTLEMENT` RPC to seller.
3. Seller's `handle_purchase_settlement()` verifies signature, records `PURCHASE_SETTLEMENT_RECEIVED`.
4. `settlement_state(exchange, listing_id)` returns `'CONFIRMED'` on both sides.

---

## 3. 30-Pair P2P Cost Qualification

**Runtime module:** `p2p_cost_qualification.py`  
**Status:** Code complete. `run_qualification_round`, `bootstrap_complete`, `qualification_statistics` (Wilson lower bound) are implemented and tested.

**What you need:**

| Requirement | Description |
|-------------|-------------|
| ≥30 peer pairs | Each pair: two peers that complete a borrow/deliver cycle |
| Live network | `network_mode=internet` with public endpoints or LAN |
| Bootstrap peers configured | At least one stable bootstrap node |

**Activation:**

```python
from urace.p2p_cost_qualification import run_qualification_round, bootstrap_complete

pairs = [('peer_a_id', 'peer_b_id'), ...]  # 30+ pairs
result = run_qualification_round(exchange, pairs)
print(result['bootstrap_complete'])   # True when ≥30 pairs done
```

**Gate:** `credit_ledger.consensus_borrow_floor()` returns the minimum floor until `bootstrap_complete()` returns `True`. After bootstrap, the full supply-pressure-adjusted floor activates.

**Statistics available without bootstrap:**

```python
from urace.p2p_cost_qualification import qualification_statistics
stats = qualification_statistics(exchange)
# {'total_pairs': N, 'delivery_rate': 0.87, 'wilson_lower_bound': 0.74, ...}
```

---

## 4. Cross-Peer Trial Receipts (token_settlement mode)

**Runtime module:** `trial_receipt.py`  
**Status:** Code complete. `create_receipt`, `verify_receipt`, `deliver_receipt`, `handle_receipt_delivery` implemented and tested. `peer_improvement.py` delivers receipts automatically after qualification.

**What you need:**

| Requirement | Description |
|-------------|-------------|
| Two live peers | Creator and borrower both online |
| `token_settlement=true` | Enables `receipt_verified` gating in `token_ledger.balance()` |
| Mutual pinning with post-quantum identity | `exchange.peer()` with `post_quantum=` set |

**What activates:** After a borrower's local qualification passes, `peer_improvement.py` automatically calls `deliver_receipt()` to the creator. The creator's `FEATURE_BORROW_VERIFIED` audit row enables `receipt_verified=True` earn events in `token_ledger.balance()`.

Without live peers: receipts are delivered best-effort; failures are silently ignored and do not block local qualification.

---

## 5. Shamir DEK Share Delivery (network mode)

**Runtime module:** `shamir_delivery.py`  
**Status:** Code complete. `request_share`, `collect_shares`, `reconstruct_dek`, `handle_share_request` implemented and tested.

**What you need:**

| Requirement | Description |
|-------------|-------------|
| `network_mode=internet` | Required for `shamir-deliver` CLI to make network calls |
| Bootstrap peers | Used as routing endpoints |
| Replica holders | Peers must have stored their shares (`SHAMIR_SHARE_STORED` audit rows) |

**Activation:**

```sh
urace exchange network shamir-deliver <feature_id> --holder <peer_id> --share-index 0
```

In `intranet` mode: emits a local `SHAMIR_DELIVER_REQUESTED` row only — no network call.

---

## 6. Ledger Tail Sync (network mode)

**Runtime module:** `ledger_sync.py` + `peer_exchange.server()`  
**Status:** Code complete. `GET /urace/rpc/v1/ledger-tail` endpoint live on Exchange server. `fork_resolution_policy`, `exchange_checkpoint`, `apply_tail_payload` all implemented.

**What you need:**

| Requirement | Description |
|-------------|-------------|
| `network_mode=internet` | Required for `tail-sync` CLI to fetch from bootstrap peers |
| Running peer | At least one peer serving `urace exchange network serve` |
| Bootstrap peers | Configured in `policy.json` |

**Activation:**

```sh
urace exchange network tail-sync --from-peer <peer_id>
```

**Fork resolution:** longer chain wins; lexicographic sha256 tiebreak on equal length. `LEDGER_CHECKPOINT_CONFLICT` audit row emitted on mismatch.

---

## 7. BFT-Lite Consensus / Ledger Finality

**Runtime module:** `consensus.py`  
**Status:** Code complete. `propose_seal`, `collect_seal_votes`, `handle_seal_vote`, `finalize_seal` implemented. `exchange.seal_vote` RPC handler live on Exchange server.

**What you need:**

| Requirement | Description |
|-------------|-------------|
| ≥2 live peers | `consensus_threshold = max(2, ceil(2N/3))` |
| Peers reachable | All pinned peers must be online for vote collection |
| `estimated_network_size` set | Used for threshold computation |

**Activation:**

```python
from urace.consensus import propose_seal, collect_seal_votes, finalize_seal

rows = exchange.audit_rows()
proposal = propose_seal(exchange, rows)
votes = collect_seal_votes(exchange, peer_ids, proposal)
result = finalize_seal(exchange, proposal, votes)
# result['finalized'] == True when threshold met
```

A `SEAL_FINALIZED` audit row is emitted when the threshold is reached. Without ≥2 live peers: `finalize_seal` returns `{'finalized': False}` — no error.

---

## 8. Key Rotation and Revocation

**Runtime module:** `key_lifecycle.py`  
**Status:** Code complete. `rotate_identity`, `create_rotation_proof`, `verify_rotation_proof`, `broadcast_revocation` all implemented and tested.

**What you need:**

| Requirement | Description |
|-------------|-------------|
| Live peers (for broadcast) | Revocation notification is best-effort RPC to known peers |
| Peers re-pinned after rotation | Peers must re-pin your new identity with rotation proof |

**Activation:**

```python
from urace.key_lifecycle import rotate_identity, broadcast_revocation

result = rotate_identity(exchange)
# result['rotated'] == True; old key backed up
broadcast_revocation(exchange, peer_ids=['peer_a', 'peer_b'], reason='scheduled rotation')
```

Rotation without notifying peers: peers will reject the new key on next contact (key replacement is blocked without rotation proof). Always broadcast before the new key is used for peer communication.

---

## 9. External Network Pilot (Phase 6-S6)

**Status:** All prerequisite code complete (phases 2.1, 3.1, 1.2, 7). Operational setup required.

**Checklist:**

- [ ] ≥5 geographically distributed nodes
- [ ] Each node: public IP or TURN relay, `network_mode=internet`
- [ ] Bootstrap peers cross-configured between all nodes
- [ ] Post-quantum identities mutually pinned
- [ ] `urace exchange network serve` running on all nodes
- [ ] 72h continuous operation for convergence evidence
- [ ] `ledger_audit.full_inventory()` run across all peers to verify chain consistency
- [ ] `p2p_cost_qualification.run_qualification_round()` with ≥30 peer pairs
- [ ] `consensus.finalize_seal()` achieving threshold on all nodes

**Latent bug resolved:** `_DHTClient.bootstrap()` previously had a `self._exchange` AttributeError silently swallowed — fixed. DHT bootstrap now runs cleanly on internet nodes.

---

## Summary table

| Feature | Module | Code status | Operational requirement |
|---------|--------|-------------|------------------------|
| EVM on-chain settlement | `eth_settlement_adapter.py` | Complete | RPC node + funded wallet + deployed contracts |
| Cross-peer purchase settlement | `purchase_settlement.py` | Complete | 2 live mutually-pinned peers |
| 30-pair qualification | `p2p_cost_qualification.py` | Complete | 30 real peer pairs |
| Cross-peer trial receipts | `trial_receipt.py` | Complete | 2 live peers + `token_settlement=true` |
| Shamir DEK delivery | `shamir_delivery.py` | Complete | `network_mode=internet` + bootstrap peers |
| Ledger tail sync | `ledger_sync.py` | Complete | `network_mode=internet` + 1 running peer |
| BFT-lite consensus | `consensus.py` | Complete | ≥2 live peers |
| Key rotation/revocation | `key_lifecycle.py` | Complete | Live peers for broadcast (best-effort) |
| External network pilot | Multiple | Complete | ≥5 distributed nodes, 72h run |
