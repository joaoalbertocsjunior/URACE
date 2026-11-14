# Contributing to URACE

## Navigation

| I want to… | Go to |
|-----------|-------|
| Set up and run tests | [Quick Start](#quick-start) |
| Run only fast tests | [Test Profiles](#test-profiles) |
| Add a new command | [Adding a New Command](#adding-a-new-command) |
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

# P2P evidence protocol (separate suite under trial/)
cd urace
PYTHONPATH=runtime python3 -m pytest trial/test_p2p_pair_protocol.py trial/test_p2p_cost_claim_review.py -q
```

**Slow tests** (`@pytest.mark.slow`) use real subprocesses, real git operations, or real network discovery. They run in CI but are excluded from the fast dev loop.

The P2P trial suite makes no provider calls and no live network requests. Synthetic cohort results validate evidence plumbing only — MUST NOT be reported as observed product value or economic savings.

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

1. Implement handler in `runtime/urace/cli.py`.
2. Register in `_KNOWN_TOP_COMMANDS` to prevent freeform routing.
3. Add entry to `docs/reference/cli.md`.
4. Add at least one test in `tests/`.
5. Update `AGENTS.md` if executor behavior changes.

---

## Ecosystem Contributions

New IDE plugins, dashboard clients, mobile apps, and other UI-layer tools build against
the [urace-rpc-v1 socket contract](docs/reference/urace-rpc-v1.md) — not against URACE internals.
See [docs/roadmap/ecosystem-roadmap.md](docs/roadmap/ecosystem-roadmap.md) for what contracts exist, what can
be built on top, and why this boundary was chosen.

New contracts (RPC methods, row kinds, export formats) must be implemented in the runtime
first (§62z) before being added to docs.

---

## Security Issues

Do not open a public issue. See [SECURITY.md](SECURITY.md).

---

## License

By contributing you agree your work is licensed under the applicable project license:
- Code contributions: [Apache 2.0](LICENSES/Apache-2.0.txt)
- Specification contributions: [CSL 1.0](LICENSES/CSL-1.0.txt)
