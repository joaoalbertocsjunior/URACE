# URACE — Claude Code Session Guide

Governance-first P2P runtime for autonomous product improvement via AI executors.
NOT a coding agent, LLM framework, workflow engine, IAM system, or sandbox.

## Repository layout

| Path | Contents |
|---|---|
| `runtime/urace/` | 170+ Python modules — entirely flat, no sub-packages |
| `runtime/tests/` | Acceptance suite (`test_*.py`) |
| `trial/` | Qualification harness + cohort validation |
| `exchange/` | Feature ledger (1 400+ JSONL) + EVM token contract stub |
| `docs/` | Spec, economy, security model |

## Layer map

| Layer | Key files | Invariants |
|---|---|---|
| Sources / data | `source_adapters/`, `control_server.py` | Use sources-lib — do not reimplement |
| Identity / crypto | `signed_records.py` `key_lifecycle.py` `crypto_wallet.py` `mesh_identity.py` | See runtime/urace/CLAUDE.md |
| Ledger / financial | `authenticated_journal.py` `credit_ledger.py` `signed_ledger.py` `ledger_crypto.py` `ledger_audit.py` `escrow_timeout.py` | Append-only, HMAC-signed, atomic writes only |
| Authority | `authority.py` | §62z — never cross without user confirmation |
| P2P / network | `peer_discovery.py` `kademlia.py` `freeform_routing.py` `cartel_guard.py` `consensus.py` `federation.py` | See runtime/urace/CLAUDE.md |
| Execution | `executor.py` `execution_backend.py` `executor_pool.py` | Sandbox boundary required; no credential leak |
| Cost / economics | `cost_tracker.py` `cost_adapter.py` `cost_model.py` `p2p_cost_qualification.py` | litellm as pricing calc only |
| CLI / control | `cli/` `cli_*.py` `command_dispatch.py` | Entry: `cli/__init__.py::main()` |

Per-module invariants for all high-risk layers: **`runtime/urace/CLAUDE.md`**

## Build and test

```sh
cd runtime
pip install -e ".[test]"
python3 -m pytest tests/ -x -q -m "not slow"   # fast loop (~20 min)
python3 -m pytest tests/ -x -q                 # full suite (~58 min)
```

Never use `run_in_background` for pytest — output must stream synchronously.

## sources-lib (external dep)

Provides: SourceAdapter protocol, SourceRegistry, M2M JSON-RPC, HTTPControlServer, Bridge, 11 adapters.
Do not reimplement anything sources-lib provides.

```python
from sources_lib import SourceRegistry, Bridge
from sources_lib.m2m import M2MServer
from sources_lib.http import HTTPControlServer
from sources_lib.adapters.github import GitHubAdapter
```

Bridge registry: `source_adapters/_sources_bridge.py`

## Hard invariants (apply to every file)

- **§62z / Authority boundary** — no automated path takes a qualifying action (spend, transfer, goal creation) without a confirmation gate. `authority.py` owns this. Reserved phrases (`override authority`, `bypass authority`, `ignore authority`) trigger hard rejection. Outcomes: `AUTONOMOUSLY_AUTHORIZED` / `DENIED` / `REQUIRES_AUTHORITATIVE_DECISION` / `UNRESOLVED` (treat as DENIED).
- **Append-only ledger** — rows in `*_journal*` / `*_ledger*` files are never deleted or mutated after write. All mutations via `atomic_write_json`.
- **No silent swallowing** — `except Exception: pass` is forbidden in financial, signing, and authority paths. Failures must surface.
- **No secrets in source** — no hardcoded keys, tokens, or credentials anywhere.
- **State files are gitignored** — never commit `state/state.json`, `exchange/config.json`, `exchange/audit.json`, `*.key`.
- **Implement = document same PR** — never document a feature not implemented in the same change. Constants from a single source-of-truth module.

## Token economics

`UNIT = 10^8 UCR`. Peer cap: 50 UNIT. Mint on qualified acceptance only (`score_delta > 0`).
EVM settlement deferred — `eth_settlement_adapter.py` is a stub.

## Two-phase upgrade

`launcher.py` validates a candidate runtime before activation. Exit 75 = re-validate, 76 = one retry.
Never bypass by editing `launcher.py` without updating the validation path.
