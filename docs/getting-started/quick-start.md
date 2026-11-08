# Quick Start

[← Documentation](../index.md)

Get URACE running, improve your product, and mint the result to the P2P network — in under 5 minutes.

---

## 1. Install

```sh
pip install urace
```

---

## 2. Initialize Your Product

Run this inside your project directory:

```sh
urace init --auto
```

`--auto` detects your API keys (`ANTHROPIC_API_KEY` / `OPENAI_API_KEY`), configures the executor, ensures a P2P identity exists, and runs a health check — all in one step. If it finds everything it needs, the output ends with `"next_command": "urace auto"`.

If you prefer to configure manually:

```sh
urace init          # create state only
urace init --ready  # discover installed CLI clients and complete onboarding
```

**Product type is auto-detected** from your directory contents. You can also set it explicitly — including multiple types for mixed pipelines:

```sh
urace init --type media              # AI-generated media pipeline
urace init --type model              # ML training/evaluation pipeline
urace init --type data               # data ingestion or transformation pipeline
urace init --type content            # content production pipeline
urace init --type software --type media   # mixed: code + media generation
```

Types: `software` (default, auto-detected), `content`, `media`, `model`, `data`. Multiple `--type` flags or comma-separated values are accepted.

**Attaching any executor**: URACE supports three adapter types for connecting external tools, agent frameworks (LangChain, AutoGen, CrewAI), or REST APIs:

```yaml
# In executor.providers config:
- id: my-agent
  adapter: script   # any CLI tool: stdin=prompt, stdout=JSON
  command: ./run_agent.sh

- id: my-api
  adapter: http     # any REST endpoint (retries on 429/503)
  endpoint: http://localhost:8080/improve

- id: my-mcp
  adapter: mcp      # MCP stdio JSONRPC 2024-11-05
  command: npx my-mcp-server
  tool: improve
```

URACE does not modify your source code.

---

## 3. Add a Goal

Tell URACE what you want to improve:

```sh
urace add "Improve API response time"
```

Goals are tracked as objectives. The runtime uses them to select operations each cycle.

---

## 4. Run an Improvement Cycle

```sh
urace run
```

The executor analyzes your product, selects the best operation, applies it, and measures the result against your quality gate. If the result improves the score, tokens are earned.

Check the result:

```sh
urace status
urace inspect --goals
```

---

## 5. Self-Evolve: The Runtime Improves Itself

After running cycles, the runtime may generate improvements to itself (new capabilities, better routing, efficiency gains). These are **never applied without your approval**.

To see pending runtime updates:

```sh
urace update download
urace update explain --json
```

Review the changes, then apply:

```sh
urace update apply
```

Self-evolution is governed by a strict authority boundary — see [Authority Boundary](../security/authority-boundary.md).

---

## 6. Enable the P2P Exchange

Once you have a quality improvement, you can mint it to the P2P network so other peers can borrow it (and earn tokens from every adoption).

Enable minting:

```sh
urace controls set --p2p-mint-enabled true
```

Enable the exchange and networking:

```sh
urace exchange settings set --enabled true --network true
```

Create your peer identity:

```sh
urace exchange peer identity
```

**Choose a network mode** that matches your deployment. The default (`hybrid`) works for most teams:

| Mode | When to use |
|------|-------------|
| `intranet` | Air-gapped or fully private LAN — no internet peers |
| `hybrid` | LAN-first with optional internet gateway (default) |
| `internet` | Fully public deployment with DHT discovery |

```sh
# Default — no action needed. Or set explicitly:
urace exchange settings set --network-mode hybrid

# Private/air-gapped team:
urace exchange settings set --network-mode intranet

# Ready to connect to the wider public network:
urace exchange settings set --network-mode internet
```

See [Network Mode](../exchange/overview.md#network-mode) for upgrade steps when moving from intranet to internet.

---

## 7. Mint Your Improvement to the Network

Grant equity for the feature you just built and list it for sale:

```sh
urace exchange equity grant api-response-feature --creator <your-peer-id>
urace exchange equity list-for-sale api-response-feature --bp 5000 --price 80
```

- `--bp 5000` sets your equity stake at 50% (basis points out of 10,000)
- `--price 80` sets the borrow price at 80 URACE units (a configured reference may apply an estimate-based ceiling)

When another peer borrows your feature, you earn tokens automatically.

---

## 8. Check Your Token Balance

```sh
urace exchange ledger summary
```

See live token velocity and network health:

```sh
urace exchange market stats --json
```

---

## 9. Inspect Executor Costs

After any `urace run` or operation, the runtime auto-captures an executor receipt at the published provider rate. View aggregate USD and token usage:

```sh
urace cost summary
```

Per-call breakdown:

```sh
urace cost list --limit 20
```

Filter to recent calls:

```sh
urace cost summary --since 2026-11-01
```

Receipts are stored locally in `state/receipts/` and never leave your machine.

---

## What's Next

- [Product Lifecycle Guide](../guides/products.md) — goals, plans, operations, GitHub products
- [Exchange Setup](../exchange/setup.md) — full exchange configuration
- [Features Guide](../exchange/features.md) — mint, borrow, and trade features
- [Concepts](concepts.md) — understand the core model
