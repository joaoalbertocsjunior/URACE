# config.json Reference

[← Documentation](../index.md) · [Config](../users/config.md)

URACE is configured via a single JSON file at `~/.urace/config.json`.  
The package default lives at `runtime/urace/config.json` and is merged at startup.  
Changes take effect on `urace start` or `urace reload`.

---

## executor

Controls AI executor providers and dispatch behaviour.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | bool | `false` | Master switch. Set to `true` automatically when providers are detected. |
| `providers` | array | `[]` | List of provider objects (see below). |
| `kind` | string | `"subprocess"` | Adapter kind; currently only `subprocess`. |
| `model` | string\|null | `null` | Default model override passed to providers that support it. |
| `command` | string\|null | `null` | Default command path (overridden per-provider). |
| `timeout_seconds` | int | `300` | Per-call wall-clock timeout. |
| `healthcheck_timeout_seconds` | int | `10` | Timeout for provider liveness probes. |
| `discovery_interval_seconds` | int | `300` | How often the runtime re-scans for new providers. |
| `max_executor_calls_per_24h` | int\|null | `null` | Aggregate 24-hour call budget (null = unlimited). |
| `max_executor_calls_per_30d` | int\|null | `null` | Aggregate 30-day call budget (null = unlimited). |
| `max_executor_result_bytes` | int | `1048576` | Maximum response size per call. |
| `routing_balance_window_seconds` | int | `86400` | Window for load-balance accounting. |
| `routing_efficiency_tolerance_ratio` | float | `0.15` | Allowed cost overhead when routing. |
| `capacity_fallback_seconds` | int | `300` | Back-off when all providers report capacity pressure. |
| `capacity_retry_delay_ms` | int | `500` | Retry delay under capacity pressure. |
| `capacity_retry_mode` | string | `"linear"` | Retry strategy: `linear` or `exponential`. |
| `progress_heartbeat_seconds` | int | `30` | How often the daemon polls for cycle progress. |
| `sandbox_bwrap_directory` | string\|null | `null` | Optional bwrap sandbox root. |
| `disabled_features` | array | `[]` | Feature IDs to disable for this executor. |
| `context_hints` | array | `[]` | Static context strings injected into every executor prompt. |

### executor.providers[]

Each entry describes one executor client.

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Stable provider identity (e.g. `"env-claude"`). |
| `adapter` | string | Adapter kind: `"claude-cli"` or `"codex-cli"`. |
| `command` | string | Absolute path to the binary. |
| `model` | string | Model name passed to the CLI. |
| `enabled` | bool | Whether this provider participates in routing. |
| `priority` | int | Routing priority; higher = preferred. |
| `capabilities` | array | Subset of `discovery`, `planning`, `mutation`, `evaluation`, `execution`. |
| `max_calls_per_24h` | int\|null | Per-provider 24-hour call budget. |
| `max_calls_per_30d` | int\|null | Per-provider 30-day call budget. |
| `_source` | string | Informational: how the provider was detected (e.g. `"ANTHROPIC_API_KEY"`). |

---

## network

Controls the P2P exchange server started alongside the daemon.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | bool | `false` | Whether to start the P2P exchange server on `urace start`. |
| `mode` | string | `"hybrid"` | Network topology: `"intranet"`, `"hybrid"`, or `"internet"`. |
| `tunnel` | string | `"auto"` | Tunnel mode passed to the exchange server: `"auto"`, `"cloudflared"`, `"none"`. |
| `roles` | array | `[]` | Node roles, e.g. `["relay", "storage"]`. Auto-assigned from NAT detection if empty. |
| `bootstrap_peers` | array | `[]` | Static peer addresses to connect to on startup. |
| `port` | int | `7301` | TCP port for the P2P exchange server. |

---

## api

Controls optional MCP and A2A server endpoints.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `mcp.enabled` | bool | `false` | Start the MCP stdio server when the daemon starts. |
| `a2a.enabled` | bool | `false` | Start the A2A HTTP server when the daemon starts. |
| `a2a.port` | int | `8080` | Loopback port for the A2A server. |

---

## resources

Controls execution budget and effort level.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `effort` | string | `"medium"` | Effort hint passed to executors: `"low"`, `"medium"`, or `"high"`. |

---

## auto_goals

Controls automatic goal replenishment.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | bool | `false` | Allow the runtime to generate goals automatically. |
| `replenish_backlog` | bool | `true` | Re-populate the backlog when it empties. |

---

## rules

Static operator rules seeded into state on every `urace start`.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `rules` | array | `[]` | List of rule objects in the same schema as `urace rule add` produces. Each rule not already present in state is registered on startup. |

Example entry:
```json
{
  "kind": "PROHIBITION",
  "statement": "Never publish to production without a passing test suite.",
  "scope": "product"
}
```

---

## sources

External connector sources pre-registered on startup.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `sources` | array | `[]` | List of source objects. Each entry is preserved and available for reference; actual connection logic requires the source to also be registered via `urace source add`. |

---

## analytics_export

Controls automated report generation.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `mode` | string | `"ON_CHECKPOINT"` | When to export: `"ON_CHECKPOINT"`, `"NEVER"`, `"ALWAYS"`. |
| `output` | string | `"generated/reports/latest"` | Report output directory. |
| `include_xlsx` | bool | `false` | Also generate XLSX alongside HTML. |

---

## github

GitHub integration settings.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `repo` | string | `"owner/repo"` | Target repository in `owner/repo` format. |
| `token_env` | string | `"URACE_GITHUB_TOKEN"` | Environment variable containing the GitHub token. |

---

## evaluation_system

Scoring weights for the improvement evaluation loop.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `minimum_evidence_units` | int | `5` | Minimum evidence records required before scoring. |
| `weights.goal_completion` | float | `1.0` | Weight applied to goal-completion signals. |
| `weights.execution_acceptance` | float | `1.5` | Weight applied to executor acceptance signals. |
| `weights.regression_safety` | float | `2.0` | Weight applied to regression-safety signals. |
| `weights.productive_call_yield` | float | `1.0` | Weight applied to call-yield signals. |

---
→ [Next: Controls](controls.md) — enable/disable capabilities per product
