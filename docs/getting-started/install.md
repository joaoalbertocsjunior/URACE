# Install URACE

[← Documentation](../index.md)

---

## Requirements

- Python 3.10 or higher
- pip 22+
- An existing software product directory (URACE attaches to it)

---

## Install

```sh
pip install urace
```

Verify the install:

```sh
urace --version
```

---

## Optional: Development Install

To install from source (for contributors or pre-release builds):

```sh
git clone https://github.com/urace/urace
cd urace/runtime
pip install -e ".[dev]"
```

Run the test suite:

```sh
cd runtime
pytest tests/
```

---

## What Gets Installed

`pip install urace` installs:

- The `urace` CLI entry point
- The lifecycle control plane (`urace/` Python package)
- No server, no daemon — URACE runs in your terminal and writes state to your project directory

State is stored in `urace/state/` (relative to your product root). No data leaves your machine unless you explicitly enable the P2P exchange.

---

## Next Steps

- [Quick Start](quick-start.md) — be up and running in 5 minutes
- [Concepts](concepts.md) — understand goals, plans, and lifecycle
