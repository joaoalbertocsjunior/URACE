# Install URACE

[← Documentation](../index.md)

URACE runs inside your existing project directory. There is no server to manage, no daemon to run, and no data leaves your machine unless you explicitly enable the P2P exchange. Install takes under a minute.

---

## Requirements

- Python 3.11 or higher
- pip 22+
- An existing software product directory (URACE attaches to it)

**Platform support:**

| Platform | Status |
|----------|--------|
| Linux | Primary — full feature set including TUI |
| macOS | Fully supported |
| Windows | Best-effort — CLI works; TUI and some P2P discovery features unavailable |

---

## Quick Start

```sh
# one-liner (Linux / macOS / WSL):
curl -fsSL https://raw.githubusercontent.com/joaoalbertocsjunior/URACE/main/install.sh | sh

# pip:
pip install urace

# npm:
npm install -g urace-cli

# Homebrew:
brew install urace

# conda:
conda install -c conda-forge urace
```

```sh
export ANTHROPIC_API_KEY=...
urace start    # boot daemon, wire executor, join P2P
urace          # open interactive shell
```

Run `urace --version` to verify the install.

---

## Update

```sh
curl -fsSL https://raw.githubusercontent.com/joaoalbertocsjunior/URACE/main/install.sh | sh
pip install --upgrade urace
npm install -g urace-cli@latest
brew upgrade urace
conda update -c conda-forge urace
```

---

## Advanced / Headless Setup

For server or systemd use, skip the interactive shell:

```sh
pip install urace
urace --version    # verify
urace start        # headless daemon + P2P server
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

## Optional Extras

```sh
pip install "urace[evm]"              # Correct EIP-155 signing with recovery_id for Polygon/EVM settlement (eth_account)
pip install "urace[telemetry]"        # OpenTelemetry tracing (OTLP export to Jaeger, Grafana Tempo, Datadog, etc.)
pip install "urace[all]"              # All of the above
```

Telemetry is opt-in and requires `OTEL_EXPORTER_OTLP_ENDPOINT` to be set; without it the dependency is installed but no spans are emitted. Set `OTEL_SDK_DISABLED=true` to suppress all telemetry even when the endpoint is configured.

---

## What Gets Installed

`pip install urace` installs:

- The `urace` CLI entry point
- The lifecycle control plane (`urace/` Python package)
- `pysha3` — keccak256 for EVM-compatible wallet address derivation
- `miniupnpc` — UPnP IGD for automatic inbound port mapping (P2P relay/bootstrap nodes)
- No server, no daemon — URACE runs in your terminal and writes state to your project directory

State is stored in `urace/state/` (relative to your product root). No data leaves your machine unless you explicitly enable the P2P exchange.

---

## Next Steps

- [Quick Start](quick-start.md) — be up and running in 5 minutes
- [Concepts](concepts.md) — understand goals, plans, and lifecycle
