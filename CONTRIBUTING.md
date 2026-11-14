# Contributing to URACE

## Navigation

| I want to… | Go to |
|-----------|-------|
| Set up and run tests | [Quick Start](#quick-start) |
| Run only fast tests | [Test Profiles](#test-profiles) |
| Add a new command | [Adding a New Command](#adding-a-new-command) |
| Update a cross-cutting protocol constant | [Protocol Single Source of Truth](#protocol-single-source-of-truth) |
| Add a network I/O code path | [Network-Gated Code](#network-gated-code) |
| Build an IDE plugin or dashboard | [Ecosystem Contributions](#ecosystem-contributions) |
| Understand the spec invariant | [§62z](#spec-evolution-invariant-62z) |
| Submit a PR | [Branch and PR Conventions](#branch-and-pr-conventions) |
| Report a security issue | [Security Issues](#security-issues) |

---

## Quick Start

```sh
git clone https://github.com/joaoalbertocsjunior/URACE.git
cd URACE/urace/runtime
pip install -e ".[test]"
pytest tests/ -n auto -m "not slow" -x -q   # fast dev loop (~20 min)
pytest tests/ -x -q                          # full suite (~58 min)
```

---

## Test Profiles

```sh
# Fast loop — skips network-heavy and subprocess-heavy tests
pytest tests/ -n auto -m "not slow" -x -q

# Full suite — all tests including slow
pytest tests/ -x -q

# Single test
pytest tests/ -k "test_name" -x -q

# Trial evidence suite (P2P evidence protocol, synthetic cohorts)
# Run from URACE/urace/
PYTHONPATH=runtime:trial python3 -m pytest trial/ --ignore=trial/core-state --ignore=trial/tests -m "not slow" -x -q

# Trial performance benchmarks
PYTHONPATH=runtime:trial python3 -m pytest trial/tests/ -x -q
```

**Slow tests** (`@pytest.mark.slow`) use real subprocesses, real git operations, or real network discovery. They run in CI but are excluded from the fast dev loop.

Trial suite makes no provider calls and no live network requests. Synthetic cohort results validate evidence plumbing only — never report as observed product value.

All PRs must maintain or improve test coverage. No green CI = no merge.

---

## Spec Evolution Invariant (§62z)

**Spec describes only what the runtime implements.**

- Never add a doc section without a corresponding runtime implementation in the same PR.
- Never document a flag, command, or behavior that does not exist in the code.

---

## Branch and PR Conventions

- Branch from `main`.
- One logical change per PR.
- PR title: `type: short description` where type is `feat`, `fix`, `docs`, `refactor`, `test`, `chore`.
- Link related issues with `Closes #N`.

---

## DCO Sign-Off (Required)

All commits must include a Developer Certificate of Origin sign-off:

```sh
git commit -s -m "feat: your change"
```

PRs without DCO sign-off on every commit will not be merged.

---

## Commit Message Format

```
type: short imperative summary (≤72 chars)

Optional body. Explain why, not what.

Signed-off-by: Your Name <email@example.com>
```

---

## Protocol Single Source of Truth

URACE uses a **domain-module ownership** pattern: each cross-cutting protocol constant lives in its authoritative module. All other code imports from that module — never duplicates the value.

### Where constants live

| Concern | Authoritative module | Key constants / functions |
|---------|---------------------|--------------------------|
| MIME type policy | `mime_policy.py` | `NETWORK_MIME_POLICY`, `DEFAULT_ALLOWED`, `is_network_allowed()`, `is_allowed()` |
| Token economics | `credit_ledger.py` | `DECIMALS`, `UNIT`, `BASE_CAP_UNITS`, `CHAIN_SCALE`, `mint_per_adoption()` |
| Protocol version | `peer_exchange.py` | `SCHEMA`, `PROTOCOL_VERSION` |
| Quality gate thresholds | `aps_scorer.py` / `evolution_guard.py` | score delta thresholds, `quality_gate_pass()` |
| Initial feature catalog | `build_initial_ledger.py` | generates `initial_ledger.jsonl` — a **static catalog** read directly by the runtime (not imported into live exchange audit); rebuild it when adding new built-in features |
| CLI command dispatch | `cli/__init__.py` | `_KNOWN_TOP_COMMANDS`, `main()` — all commands are thin wrappers |

### NETWORK_* vs configurable constants

| Prefix | Meaning | Who uses it |
|--------|---------|-------------|
| `NETWORK_*` | Network-enforced — ignores per-node user config | Protocol gates: `receive()`, mint, `should_replicate()` |
| _(no prefix)_ | User-configurable default — can be overridden via `p2p.*` config | CLI validation, local filtering, display |

A `NETWORK_*` constant is used when ALL nodes in the network must agree on the value for protocol correctness. A user changing their local config must not be able to bypass it.

**To relax a network-enforced rule** (e.g., expand allowed MIME types when APS gains new quality-gate support):
1. Update the `NETWORK_*` constant in its authoritative module — one line change.
2. All protocol gates pick it up automatically via their `is_network_*()` function call.
3. No other files need updating; no grep-and-replace.

### What should NOT be in a central hub

The following do NOT belong in a central `protocol.py` and should NOT be moved there:
- Configuration defaults — owned by their domain module
- CLI flags and argument parsers — owned by `cli/`
- Test fixtures and mocks — test-local only
- Operational state (PID files, exchange state) — runtime-managed

Adding a central hub would create circular import risk and over-engineering. Import chain: `cli/` → domain modules → no upward imports.

---

## Network-Gated Code

HTTP RPC calls in `exchange_cli.py` (and any future transport module) must always be gated on `network_mode`:

```python
_net_mode = _settings.get('network_mode', 'intranet')
if _net_mode in ('internet', 'hybrid'):
    # issue real HTTP request to bootstrap peer
    ...
else:
    result = {'status': 'stub', 'note': 'local only — set network_mode=internet to enable'}
```

`intranet` mode must return the stub response unchanged — no network I/O, no imports of `urllib`. This invariant ensures all test fixtures (which never set `network_mode`) remain fast and fully offline.

---

## Adding a New Command

1. Implement handler in `runtime/urace/cli/` (add to the appropriate submodule and register in `cli/__init__.py`).
2. Register in `_KNOWN_TOP_COMMANDS` to prevent freeform routing.
3. Add entry to `docs/reference/cli.md`.
4. Add at least one test in `tests/`.
5. Update `AGENTS.md` if executor behavior changes.

---

## Ecosystem Contributions

UI-layer tools (IDE plugins, dashboards, mobile apps) build against the [urace-rpc-v1 socket contract](docs/reference/urace-rpc-v1.md) — not against URACE internals. See [ecosystem roadmap](docs/roadmap/ecosystem-roadmap.md) for buildable surfaces.

New RPC methods, row kinds, or export formats: implement in runtime first (§62z), then document.

---

## Security Issues

Do not open a public issue. See [SECURITY.md](SECURITY.md).

---

## License

By contributing you agree your work is licensed under the applicable project license:
- Code contributions: [Apache 2.0](LICENSES/Apache-2.0.txt)
- Specification contributions: [CSL 1.0](LICENSES/CSL-1.0.txt)
