# URACE — Claude Code Session Guide

URACE is a governance-first P2P runtime for autonomous product improvement via AI executors.
It is NOT a coding agent, LLM framework, workflow engine, IAM system, or sandbox.
Its job: preserve and evolve a Product toward authoritative Intent across replaceable executors.

## Repository layout

```
runtime/urace/      170+ Python modules — the entire runtime (flat, no sub-packages)
trial/              Qualification harness and cohort validation
exchange/           Feature ledger (1 400+ JSONL entries) + EVM token contract stub
docs/               Spec, economy, security model
packaging/          conda / homebrew / npm wrappers
```

## Layer map (read before touching any file)

| Layer | Key files | Do not touch without reading runtime/urace/CLAUDE.md |
|---|---|---|
| Sources / data | `source_adapters/`, `control_server.py` | — |
| Identity / crypto | `signed_records.py` `key_lifecycle.py` `crypto_wallet.py` `mesh_identity.py` | Yes |
| Ledger / financial | `authenticated_journal.py` `credit_ledger.py` `signed_ledger.py` `ledger_crypto.py` `ledger_audit.py` `escrow_timeout.py` | Yes |
| Authority | `authority.py` | Yes |
| P2P / network | `peer_discovery.py` `kademlia.py` `freeform_routing.py` `cartel_guard.py` `consensus.py` `federation.py` | Yes |
| Execution | `executor.py` `execution_backend.py` `executor_pool.py` | Yes |
| Cost / economics | `cost_tracker.py` `cost_adapter.py` `cost_model.py` `p2p_cost_qualification.py` | — |
| CLI / control | `cli/` `cli_*.py` `command_dispatch.py` `control_server.py` | — |

## Build and test

```sh
cd runtime
pip install -e ".[test]"
python3 -m pytest tests/ -x -q                          # full suite
python3 -m pytest tests/ -x -q -m "not slow"            # fast loop
```

Never use `run_in_background` for pytest — output must stream synchronously.

## External dependency: sources-lib

`sources-lib` (at `git+https://github.com/joaoalbertocsjunior/sources-lib`) is the sources adapter,
M2M JSON-RPC, and HTTP control library. URACE consumes it — do not reimplement what it provides.

Import paths: `from sources_lib import ...`, `from sources_lib.m2m import ...`, `from sources_lib.http import ...`

The bridge registry is in `source_adapters/_sources_bridge.py`.

## Cross-cutting invariants (apply everywhere)

- **§62z / Authority boundary**: the authority boundary must never be crossed without explicit
  user confirmation. No automated path may take a qualifying action (spend, transfer, goal
  creation) without a confirmation gate. Executors must not bypass `authority.py` gates.
  Reserved phrases (`override authority`, `bypass authority`, `ignore authority`) trigger hard rejection.
  Outcomes: AUTONOMOUSLY_AUTHORIZED / DENIED / REQUIRES_AUTHORITATIVE_DECISION / UNRESOLVED (treat as DENIED).
- **Implement = document same PR**: never add docs for a feature not implemented in the same change.
  All constants from a single source-of-truth module.
- **Append-only ledger**: no row in any `*_journal*` or `*_ledger*` file may be deleted or
  mutated after write. Use `atomic_write_json` for all mutations.
- **No silent exception swallowing** in financial, signing, or authority code paths.
  `except Exception: pass` is forbidden there — failures must surface.
- **No hardcoded secrets, keys, or tokens** anywhere in source.
- **State files are gitignored** — never commit `state/state.json`, `exchange/config.json`,
  `exchange/audit.json`, or any `*.key` file.

## Two-phase upgrade

Launcher validates a candidate runtime before activation. Exit codes: 75 = re-validate, 76 = one retry.
Never bypass this by editing `launcher.py` without also updating the validation path.

## Token economics (read before touching ledger or cost files)

Base unit: `UNIT = 10^8 UCR`. Peer cap: 50 UNIT. Mint on qualified acceptance only.
EVM settlement is deferred (Polygon mainnet stub exists in `eth_settlement_adapter.py`).
