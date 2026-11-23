# runtime/urace — Module-level invariants

Read this before modifying any file in this directory.
Top-level rules are in `../../CLAUDE.md` — this file adds per-cluster detail.

## Cluster: Ledger / financial

Files: `authenticated_journal.py`, `credit_ledger.py`, `signed_ledger.py`,
       `ledger_crypto.py`, `ledger_audit.py`, `ledger_primitives.py`,
       `ledger_compaction.py`, `ledger_economics.py`, `ledger_reputation.py`,
       `ledger_sync.py`, `token_ledger.py`, `escrow_timeout.py`

- Append-only invariant: rows are never deleted or mutated after write.
  Every mutation must go through `atomic_write_json`.
- Double-spend prevention: every debit must check balance before deducting.
  Read-modify-write on balance requires the caller to hold the lock.
- Every ledger entry must carry a valid HMAC-SHA256 signature before persisting.
  `ledger_crypto.py` owns signing — use `hmac.compare_digest`, never `==`.
  Key material must never appear in log output or exception messages.
- Audit trail: every state transition must emit an audit row via `ledger_audit.py`.
  No branch may mutate state silently.
- Escrow release: use monotonic time only. Verify the releasing party held the escrow lock.
- `ledger_compaction.py`: compaction must preserve the full audit chain — no entries dropped.

## Cluster: Identity / crypto

Files: `signed_records.py`, `key_lifecycle.py`, `crypto_wallet.py`, `mesh_identity.py`,
       `session_dek.py`, `shamir.py`, `shamir_delivery.py`

- `signed_records.py`: HMAC-SHA256 — always use `hmac.compare_digest`. The `seq` field must
  be included in every signed message (replay-attack vector if omitted).
- `crypto_wallet.py`: private key material must never appear in logs, exceptions, or return
  values other than designated sign/export calls. Never serialise a private key to a
  non-encrypted store. Use constant-time comparison for all signature/key checks.
- `key_lifecycle.py`: key rotation must invalidate old signatures. Use only cryptographic
  hash functions for key derivation. Key storage must not be plaintext or world-readable.
- `mesh_identity.py`: node IDs must be cryptographically random — never sequential or
  user-supplied without verification.

## Cluster: Authority

File: `authority.py`

- §62z invariant: the authority boundary must never be crossed without explicit user confirmation.
- No automated path may take a qualifying action (spend, transfer, goal creation) without a
  confirmation gate.
- Capability escalation must be logged to the audit journal.
- Reserved phrases that must trigger hard rejection (do not add code paths that allow them through):
  `override authority`, `bypass authority`, `ignore authority`, `disable authority`,
  `remove authority`, `skip authority check`
- Authority check outcomes: `AUTONOMOUSLY_AUTHORIZED` / `DENIED` /
  `REQUIRES_AUTHORITATIVE_DECISION` / `UNRESOLVED` (treat UNRESOLVED as DENIED).

## Cluster: P2P / network

Files: `peer_discovery.py`, `kademlia.py`, `freeform_routing.py`, `cartel_guard.py`,
       `consensus.py`, `federation.py`, `p2p_matching.py`, `peer_selection.py`,
       `peer_exchange.py`, `peer_work_market.py`, `nat_check.py`, `stun_client.py`, `ddns.py`

- `peer_discovery.py`: untrusted peers must pass `AdmissionGate` before receiving routing traffic.
  Never shortcut quarantine. DHT lookups must verify peer-supplied data signatures.
  `relay_only=True` must not expose the node's real IP.
- `kademlia.py`: Sybil resistance — a single IP must not occupy multiple bucket slots.
  Node ID generation must be cryptographically random.
  Never trust peer-supplied routing tables without verification.
- `freeform_routing.py`: routing decisions must not leak internal state to untrusted peers.
  Cache evidence is process-local — never gossip it. `LocalRouteReputation` must not be
  serialised or sent over the wire. `select_target` must not return a peer that failed AdmissionGate.
- `p2p_matching.py`: executors must not inflate their own `match_score` or TPS weight by
  self-reporting. `DemandCounter` entries must be local-only — never accept from remote peers.
- `cartel_guard.py`: quorum checks must not be satisfiable by a single actor controlling
  multiple peer IDs. Evidence thresholds must not be runtime-configurable without authority verification.
- `consensus.py`: vote counting requires strict 2/3 supermajority. No single peer may determine
  outcome. Never skip message authentication for performance.
- `federation.py`: cross-federation requests must carry valid authority proofs.
  Never accept a federation peer's claims without verifying the originating federation's signing key.

## Cluster: Execution

Files: `executor.py`, `execution_backend.py`, `executor_pool.py`, `executor_routing.py`,
       `executor_capabilities.py`, `multi_executor.py`

- `execution_backend.py`: LLM-generated code must not execute without a sandbox boundary.
  Resource limits (CPU, memory, time) must be present and not user-controllable without
  authority verification.
- `executor.py`: credentials must not pass outside the executor's declared scope.
  Executors must not persist state beyond their declared session.

## Cluster: EVM / settlement

File: `eth_settlement_adapter.py`

- EVM transaction safety: ABI encoding must validate address checksums.
  Gas limit values must not be user-controlled without bounds.
  Never submit a transaction without first simulating or estimating gas.
- `TopologyLock` and `ArchitectureCertificate` stubs are intentional — do not remove them.

## Cluster: Sources / data

Files: `source_adapters/`, `control_server.py`, `data_transport.py`, `data_cli.py`

- All source adapter integration goes through `source_adapters/_sources_bridge.py`.
  Do not add direct litellm, mcp, or github imports outside of sources-lib adapters.
- `control_server.py`: imports `HTTPControlServer` from `sources_lib.http` and
  `M2MServer` from `sources_lib.m2m` — do not move these back to a top-level import.

## Tests

```sh
cd /home/host/Desktop/URACE/runtime
python3 -m pytest tests/ -x -q -m "not slow"   # fast loop
python3 -m pytest tests/ -x -q                 # full suite
```

Security tests (`tests/test_security.py`) are intentionally adversarial — never weaken
assertions, catch exceptions they are designed to surface, or reduce coverage. Add, never remove.
