# Contributing to URACE

## Quick Start

```sh
git clone https://github.com/joaoalbertocsjunior/URACE.git
cd URACE/urace/runtime
pip install -e ".[peer-security,peer-discovery]"
pytest tests/ -x -q
```

## DCO Sign-Off (Required)

All commits must include a Developer Certificate of Origin sign-off:

```sh
git commit -s -m "feat: your change"
```

PRs without DCO sign-off on every commit will not be merged.

## Branch and PR Conventions

- Branch from `main`.
- One logical change per PR.
- PR title: `type: short description` where type is `feat`, `fix`, `docs`, `refactor`, `test`, `chore`.
- Link related issues with `Closes #N`.

## Spec Evolution Invariant (§62z)

**Spec describes only what the runtime implements.**

- Never add a doc section without a corresponding runtime implementation in the same PR.
- Never document a flag, command, or behavior that does not exist in the code.

## Tests

```sh
cd urace/runtime
pytest tests/ -x -q          # full suite
pytest tests/ -k "test_name" # single test
```

All PRs must maintain or improve test coverage. No green CI = no merge.

## Commit Message Format

```
type: short imperative summary (≤72 chars)

Optional body. Explain why, not what.

Signed-off-by: Your Name <email@example.com>
```

## Adding a New Command

1. Implement handler in `runtime/urace/cli.py`.
2. Register in `_KNOWN_TOP_COMMANDS` to prevent freeform routing.
3. Add entry to `docs/reference/cli.md`.
4. Add at least one test in `tests/`.
5. Update `AGENTS.md` if executor behavior changes.

## Security Issues

Do not open a public issue. See [SECURITY.md](SECURITY.md).

## License

By contributing you agree your work is licensed under the [MIT License](LICENSE).
