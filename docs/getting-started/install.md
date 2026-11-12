# Install URACE

[← Documentation](../index.md)

URACE runs inside your existing project directory. There is no server to manage, no daemon to run, and no data leaves your machine unless you explicitly enable the P2P exchange. Install takes under a minute.

---

## Requirements

- Python 3.10 or higher
- pip 22+
- An existing software product directory (URACE attaches to it)

**Platform support:**

| Platform | Status |
|----------|--------|
| Linux | Primary — full feature set including TUI |
| macOS | Fully supported |
| Windows | Best-effort — CLI works; TUI and some P2P discovery features unavailable |

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

## Optional Extras

```sh
pip install "urace[peer-security]"    # P2P cryptographic signatures (secp256k1)
pip install "urace[peer-discovery]"   # LAN peer discovery via mDNS/Zeroconf
pip install "urace[telemetry]"        # OpenTelemetry tracing (OTLP export to Jaeger, Grafana Tempo, Datadog, etc.)
pip install "urace[all]"              # All of the above
```

Telemetry is opt-in and requires `OTEL_EXPORTER_OTLP_ENDPOINT` to be set; without it the dependency is installed but no spans are emitted. Set `OTEL_SDK_DISABLED=true` to suppress all telemetry even when the endpoint is configured.

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
