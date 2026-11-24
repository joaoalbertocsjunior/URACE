# URACE Rust Transition Plan

## Phases

| Phase | Crate(s) | Status | Description |
|-------|----------|--------|-------------|
| R-0   | workspace | Done | Cargo workspace, 9 crates, CI scaffold |
| R-1   | urace-crypto | Done | GF(256)/0x11D, Shamir, HMAC-SHA256, Ed25519, AES-256-GCM |
| R-2   | urace-types | Done | AuthorityOutcome, LedgerEntry, NodeInfo, SourceRecord |
| R-3   | urace-ledger | Done | Append-only journal, atomic writes, UCR credit ledger |
| R-4   | sources-lib | Done | SourceAdapter trait, SourceRegistry, DirectoryAdapter, GitHubAdapter |
| R-5   | urace-authority | Done | §62z gate, FleetPolicy (Ed25519 + monotonic gen + DHT key) |
| R-6   | urace-p2p | Done | AdmissionGate, CartelGuard, Consensus, Federation, BEP 5 DHT |
| R-7   | urace-p2p | Done | PeerExchange, FreeformRouting, LocalRouteReputation |
| R-8   | urace-executor | Done | ExecutorPool sandbox, credential leak detection |
| R-9   | urace | Done | Full CLI dispatch, RuntimeState load/save |
| R-10  | sources-lib | Done | A2ASourceAdapter, LocalDataAdapter |
| R-11  | urace-settlement | Done | Lightning rail stub, mesh-llm passthrough, SettlementManager |

## Payment Settlement Sequence

Three options, correct execution order:

### Option 3 — mesh-llm executor passthrough (do now, zero build cost)

URACE dispatches inference to mesh-llm executors. mesh-llm already has live Lightning
channels. Wire URACE work-market bid settlement through that executor's payment channel.

Implementation: `MeshLlmPassthrough` in `urace-settlement/src/mesh_llm_passthrough.rs`.
Config: `settlement_rail = "mesh_llm_passthrough"`.

Covers all inference payments for nodes using mesh-llm as executor — immediate usability.
Full HTTP wiring to `{executor_endpoint}/payments` is deferred; stub returns
`status = "passthrough_pending"` until the executor confirms.

### Option 2 — UCR/Polygon settlement (do always, independent)

The UCR token economy is the URACE long-term store of value and is independent of which
executor handles inference payments. Option 3 buys time; Option 2 is never optional.

Implementation: `EvmSettlementAdapter` in `urace-settlement/src/evm.rs` with live
JSON-RPC + ERC-20 ABI.
Config: `settlement_rail = "evm"`, `evm_rpc_url`, `evm_chain_id` (default: 137 Polygon).

### Option 1 — Native Lightning (conditional on adoption)

Only needed for URACE nodes that use non-mesh-llm executors (OpenAI, Anthropic direct, etc.)
and need Lightning for work-market payments. Wait for adoption data.

Feature-gated: `urace-settlement` crate with `--features lightning` activates `ldk-node`.
Implementation: `LightningRail` in `urace-settlement/src/lightning.rs`.

Build if: >20% of URACE executor traffic flows outside mesh-llm.

### SettlementManager routing priority

```
mesh_llm_passthrough (Option 3) → evm (Option 2) → none (internal UCR only)
```

Configured via `settlement_manager::SettlementManager::from_config(&config)`.

## Crate architecture

```
urace-crypto       — GF(256), Shamir, HMAC, Ed25519, AES-GCM (no ring)
urace-types        — AuthorityOutcome, LedgerEntry, NodeInfo, SourceRecord
urace-ledger       — append-only journal, atomic writes, CreditLedger
sources-lib        — SourceAdapter trait, registry, 4 adapters
urace-authority    — §62z gate, FleetPolicy
urace-p2p          — Kademlia, AdmissionGate, CartelGuard, Consensus,
                     Federation, PeerExchange, FreeformRouting
urace-executor     — ExecutorPool, SandboxConfig, credential leak detection
urace-settlement   — EVM stub, LightningRail stub, MeshLlmPassthrough,
                     SettlementManager
urace              — main binary: CLI, RuntimeState
```

## Security invariants carried forward

- `relay_only=true` MUST NOT expose real IP (enforced in `DiscoverySession::may_announce_real_ip()`).
- `LocalRouteReputation` and `RouteCache` do NOT implement Serialize — process-local only.
- `select_target` filters non-admitted peers before scoring.
- `consensus_threshold` enforces minimum 2 — no single peer determines outcome.
- `validate_authority_proof` always returns false until wired to urace-authority.
- `ExecutorPool::submit` calls `authority_check` first, then `detect_credential_leak`.
- Parent env vars are never forwarded to child processes (`env_clear()` on `Command`).
- `FederationStore::accept_announce` enforces monotonic sequence IDs (anti-replay).
