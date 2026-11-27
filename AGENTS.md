# AGENTS.md

## Project
URACE — governance-first P2P runtime for autonomous product improvement via AI executors.

NOT a coding agent, LLM framework, workflow engine, IAM system, or sandbox.

## Build
```sh
cd core
cargo build
cargo test
```

For the Python acceptance suite (legacy):
```sh
cd runtime
pip install -e ".[test]"
python3 -m pytest tests/ -x -q -m "not slow"
```

## File layout
| Path | Contents |
|---|---|
| `core/crates/` | Rust workspace — all production code |
| `core/crates/urace/` | Main binary (CLI + daemon) |
| `core/crates/urace-mcp/` | MCP server (Axum, §62z-gated) |
| `core/crates/urace-authority/` | §62z authority gate |
| `core/crates/urace-executor/` | Executor pool + sandbox |
| `core/crates/urace-ledger/` | Append-only reputation ledger |
| `core/crates/urace-audit/` | Chain integrity + audit log |
| `core/crates/urace-p2p/` | Kademlia P2P discovery |
| `core/crates/urace-qualification/` | Multi-evaluator qualification |
| `core/crates/urace-identity/` | Identity continuity |
| `docs/` | Spec, economy, security model |

## Authority boundary (§62z)
Every write operation (spend, transfer, goal creation, GitHub write) requires an authority resolution via `urace_authority::authority::resolve()`. Outcomes: `AutonomouslyAuthorized` / `Denied` / `RequiresAuthoritativeDecision` / `Unresolved` (treat as Denied). Never bypass.

Reserved phrases that trigger hard rejection: "override authority", "bypass authority", "ignore authority", "disable authority".

## Conventions
- All ledger rows are append-only — never mutate after write
- No `unwrap()` in non-test code — use `?` or proper error handling
- No secrets in source — credentials via env vars only
- Sandbox boundary required in executor — no credential leak
- `cargo test` must pass before any commit to main
- Never commit state files: `state/state.json`, `*.key`, `exchange/config.json`

## MCP server
URACE exposes an MCP server on `127.0.0.1:7701` when running (`urace run`).
Sources-lib MCP server expected on `127.0.0.1:7700`.
