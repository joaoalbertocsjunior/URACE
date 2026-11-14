# URACE — Complete UX Surface Reference

> Source of truth: extracted directly from runtime code (`cli_parser.py`, `exchange_cli.py`,
> `cli/__init__.py`, `shell.py`, `_daemon.py`, `peer_exchange.py`, `_common.py`).
> Generated 2026-11-13. §62z: spec describes only what is implemented.

---

## Table of Contents

1. [UX Interfaces Overview](#1-ux-interfaces-overview)
2. [Unix CLI — Global Flags](#2-unix-cli--global-flags)
3. [Unix CLI — Lifecycle Commands](#3-unix-cli--lifecycle-commands)
4. [Unix CLI — Improvement Engine](#4-unix-cli--improvement-engine)
5. [Unix CLI — Inspection & Status](#5-unix-cli--inspection--status)
6. [Unix CLI — Goals & Rules](#6-unix-cli--goals--rules)
7. [Unix CLI — Data & Sources](#7-unix-cli--data--sources)
8. [Unix CLI — State Operations](#8-unix-cli--state-operations)
9. [Unix CLI — P2P Exchange](#9-unix-cli--p2p-exchange)
10. [Unix CLI — Governance](#10-unix-cli--governance)
11. [Unix CLI — Integration](#11-unix-cli--integration)
12. [Unix CLI — System Tools](#12-unix-cli--system-tools)
13. [Interactive Shell (REPL)](#13-interactive-shell-repl)
14. [M2M Interface](#14-m2m-interface)
15. [Daemon RPC (TCP :7474)](#15-daemon-rpc-tcp-7474)
16. [API Server Interface](#16-api-server-interface)
17. [Config Files & Schemas](#17-config-files--schemas)
18. [Environment Variables](#18-environment-variables)
19. [Unix CLI — Configuration & Advanced Commands](#19-unix-cli--configuration--advanced-commands)

---

## 1. UX Interfaces Overview

| Interface | Entry Point | Use Case |
|-----------|-------------|----------|
| Unix CLI | `urace <command> [args]` | Human operator, scripts, CI |
| Interactive Shell | `urace` (no args, TTY) or `urace shell` | Control plane REPL, real-time ops |
| Dashboard TUI | `urace dashboard` or `urace` (no-args, non-TTY) | Curses monitoring |
| M2M | `urace m2m '<json>'` or `--stdin` | Machine-to-machine JSON dispatch |
| API Server | `urace api serve` | MCP stdio / A2A HTTP server |
| Daemon RPC | TCP `127.0.0.1:7474` (JSON-newline) | In-process control from shell/scripts |

All interfaces call the same `main(argv)` — one capability registry, zero maintenance overhead.

---

## 2. Unix CLI — Global Flags

Applied before any subcommand. Parsed from top-level `ArgumentParser`.

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--version` | flag | — | print `urace <RUNTIME_VERSION>` and exit |
| `--format json\|xml` | str | `None` | output format for all subcommands |
| `--json` | flag | — | alias for `--format json` |
| `--resume` | flag | `False` | prepend saved session context turns to input |

**No-args behaviour (special):**
- TTY → auto-start daemon thread (if not running) + open interactive shell
- Non-TTY → launch curses TUI dashboard

---

## 3. Unix CLI — Lifecycle Commands

### `urace init`

Initialize state. Default: runs `auto_complete()` (zero-config: detect API keys, configure
exchange, verify health). Re-entrant calls from inside `auto_complete` fall through to basic
state init.

| Flag | Default | Description |
|------|---------|-------------|
| `--ready` | `False` | complete validated operator bootstrap (discover clients, real onboarding) |
| `--auto` | `False` | explicit zero-config flag (same as default) |
| `--type TYPE [TYPE…]` | auto-detect | product type(s): `software content media model data` |

---

### `urace start`

Init (if needed) → start daemon + P2P exchange server.

| Flag | Default | Description |
|------|---------|-------------|
| `--interval-minutes FLOAT` | `30.0` | minutes between improvement cycles |
| `--format json\|xml` | `None` | output format |

---

### `urace stop`

Stop the running daemon (sends SIGTERM).

| Flag | Default | Description |
|------|---------|-------------|
| `--format json\|xml` | `None` | output format |

---

### `urace run`

Run one improvement cycle. Alias: `urace auto --cycles 1`.

| Flag | Default | Description |
|------|---------|-------------|
| `--format json\|xml` | `None` | output format |

---

### `urace shell`

Open interactive URACE control shell (REPL). Same as `urace` with no args in a TTY.

| Flag | Default | Description |
|------|---------|-------------|
| `--format json\|xml` | `None` | output format |

---

### `urace dashboard`

Open curses monitoring dashboard. Same as `urace` with no args in non-TTY.

| Flag | Default | Description |
|------|---------|-------------|
| `--format json\|xml` | `None` | output format |

---

### `urace daemon [action]`

Foreground improvement daemon.

| Action | Description |
|--------|-------------|
| `start` (default) | start foreground daemon loop |
| `status` | check if daemon PID file exists |
| `stop` | send stop signal to running daemon |

**`daemon start` flags:**

| Flag | Default | Description |
|------|---------|-------------|
| `--interval-minutes FLOAT` | `30.0` | minutes between improvement cycles |
| `--max-cycles INT` | `0` | stop after N cycles; 0=run forever |
| `--format json\|xml` | `None` | output format |

**Daemon behaviour on start:**
- Writes PID to `<state_dir>/daemon.pid`
- Starts P2P exchange server (`urace exchange network serve --host 0.0.0.0 --port 7301`) in background thread
- Starts RPC server on `127.0.0.1:7474`
- Loops `urace auto --cycles 1 --quiet` every `interval_seconds`
- Handles SIGTERM / SIGHUP for graceful shutdown

---

### `urace pause`

Suspend autonomous operation. Durable state is preserved intact.

| Flag | Default | Description |
|------|---------|-------------|
| `--format json\|xml` | `None` | output format |

---

### `urace resume`

Resume a PAUSED lifecycle.

| Flag | Default | Description |
|------|---------|-------------|
| `--format json\|xml` | `None` | output format |

---

## 4. Unix CLI — Improvement Engine

### `urace auto` (alias: `urace autonomous`)

Run the improvement lifecycle.

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--dry-run` | flag | `False` | preview snapshot without cycles/writes/network/executor calls |
| `--cycles INT\|infinity` | int | `0` | cycle limit; 0 or `infinity` = run indefinitely |
| `--interval FLOAT` | seconds | `30` | seconds between assessments |
| `--force-discovery` | flag | `False` | run discovery now, ignoring cadence |
| `--quiet` | flag | `False` | suppress per-cycle human feedback |
| `--verbose` | flag | `False` | show detailed cycle diagnostics |
| `--report` | flag | `False` | emit machine-readable improvement report (JSON) after all cycles |
| `--format json\|xml` | str | `None` | output format |

**Note:** When `execution_workflow = "specification-trial"`, routes to `trial.run_workflow()`.

---

### `urace derive [intent]`

Describe intent and URACE suggests patterns.

| Argument/Flag | Type | Default | Description |
|---------------|------|---------|-------------|
| `intent` | str | `""` | what you're building — auto-suggests patterns |
| `--constructs ID,...` | str | `None` | explicit construct/pattern IDs (e.g. `AP0,AP4`) |
| `--kind KIND,...` | str | `"all"` | `pattern,mechanism,schema,protocol,contract,all` |
| `--source runtime\|spec` | str | `"runtime"` | derive from runtime (default) or spec catalog |
| `--suggest` | flag | `False` | show suggestions without building manifest |
| `--from-goals` | flag | `False` | derive suggestions from declared Goals |
| `--from-constraints` | flag | `False` | derive from HardConstraints |
| `--from-inspection` | flag | `False` | derive from InspectionSurface gaps |
| `--exclude ID,...` | str | `None` | exclude transitive deps (requires `--exclude-reason`) |
| `--exclude-reason TEXT` | str | `""` | reason for exclusion |
| `--out PATH` | str | `None` | write DerivedSystemManifest JSON to file |
| `--save` | flag | `False` | store manifest reference in state |
| `--derive-capabilities` | flag | `False` | auto-generate CapabilityStatements |
| `--apply-capabilities` | flag | `False` | register capability drafts into config |
| `--refresh` | flag | `False` | re-derive all saved manifests |
| `--manifest-id ID` | str | `None` | target specific manifest with `--refresh` |
| `--show-delta` | flag | `False` | show what changed vs saved manifest |
| `--derive-milestone` | flag | `False` | draft ProductMilestone from capability gaps |
| `--bundle NAME` | str | `None` | resolve named FeatureBundle (e.g. `community-inbox`) |
| `--list-bundles` | flag | `False` | list all built-in FeatureBundles and exit |
| `--verify` | flag | `False` | re-verify stored content_hash of saved manifest |
| `--no-verify` | flag | `False` | skip automatic hash verification |
| `--hash SHA256` | str | `None` | verify manifest against this SHA-256 digest |
| `--format json\|xml` | str | `None` | output format |

---

### `urace update [action] [reference]`

Download, explain, apply, or resolve a spec update.

| Action | Description |
|--------|-------------|
| `download` | download spec update |
| `explain` | explain a candidate update |
| `apply` | apply reviewed candidate |
| `resolve` | resolve a checkpointed conflict |

| Flag | Default | Description |
|------|---------|-------------|
| `reference` | `None` | download source, candidate hash prefix, or local path |
| `--source PATH` | `None` | explicit spec source |
| `--yes` | `False` | skip confirmation prompt |
| `--decision TEXT` | `None` | operator decision for checkpointed conflict |
| `--opt-in-constructs ID,...` | `None` | limit update scope to these construct IDs |
| `--hash SHA256` | `None` | expected SHA-256 of downloaded artifact |
| `--verify` | `False` | re-verify previously hashed candidate |
| `--no-verify` | `False` | skip hash verification on apply |
| `--format json\|xml` | `None` | output format |

---

## 5. Unix CLI — Inspection & Status

### `urace status`

Show full lifecycle status.

| Flag | Default | Description |
|------|---------|-------------|
| `--format json\|xml` | `None` | output format |

---

### `urace check`

Inspect the system surface for blockers, warnings, info.

| Flag | Default | Description |
|------|---------|-------------|
| `--fail-on BLOCKING\|WARNING\|INFO` | `None` | exit non-zero if any issue at this level exists |
| `--migration-dry-run` | `False` | simulate State Document schema migration without writing |
| `--query TEXT` | `None` | filter inspection surface output by keyword |
| `--format json\|xml` | `None` | output format |

---

### `urace vitals`

Show progress, credit usage, efficiency, and lifecycle health.

| Flag | Default | Description |
|------|---------|-------------|
| `--since ISO` | `None` | start date |
| `--until ISO` | `None` | end date |
| `--limit INT` | `None` | max records |
| `--fail-on BLOCKING\|WARNING\|INFO` | `None` | exit non-zero on issue level |
| `--format json\|xml` | `None` | output format |

---

### `urace quality`

Inspect quality deltas and quality streak across operations.

| Flag | Default | Description |
|------|---------|-------------|
| `--scope TEXT` | `None` | filter by ProductScope |
| `--format json\|xml` | `None` | output format |

---

### `urace compliance`

Inspect compliance posture per domain.

| Flag | Default | Description |
|------|---------|-------------|
| `--domain authority\|intent\|schema\|constraint\|governance` | `None` | filter to one domain |
| `--history INT` | `10` | number of recent ComplianceRecords |
| `--export FILE` | `None` | export all records to `.json` or `.jsonl` |
| `--since ISO_DATE` | `None` | lower bound |
| `--until ISO_DATE` | `None` | upper bound |
| `--strict` | `False` | exit non-zero if any domain is NON_COMPLIANT |
| `--format json\|xml` | `None` | output format |

---

### `urace milestone`

Show milestone progress, gate status, ProductVersion history.

| Flag | Default | Description |
|------|---------|-------------|
| `--scope TEXT` | `None` | filter scope |
| `--format json\|xml` | `None` | output format |

---

### `urace trace action [trace_id]`

Query lifecycle trace log.

| Action | Description |
|--------|-------------|
| `list` | list trace records |
| `inspect` | inspect one record |

| Flag | Default | Description |
|------|---------|-------------|
| `trace_id` | `None` | trace record ID (inspect) |
| `--kind CYCLE\|OPERATION\|DECISION\|TRANSITION\|GAP\|ONBOARD\|SWITCH\|FLEET` | `None` | filter by kind |
| `--cycle-id ID` | `None` | filter by cycle |
| `--since ISO` | `None` | start |
| `--until ISO` | `None` | end |
| `--limit INT` | `50` | max records |
| `--offset INT` | `0` | skip N records |
| `--format json\|xml` | `None` | output format |

---

### `urace evidence list`

| Flag | Default | Description |
|------|---------|-------------|
| `--kind TEXT` | `None` | filter by evidence kind |
| `--since ISO` | `None` | start |
| `--until ISO` | `None` | end |
| `--limit INT` | `20` | max records |
| `--format json\|xml` | `None` | output format |

---

### `urace blocker action [blocker_id]`

| Action | Description |
|--------|-------------|
| `list` | list active blockers |
| `resolve` | resolve a blocker by ID |

| Flag | Default | Description |
|------|---------|-------------|
| `blocker_id` | `None` | required for `resolve` |
| `--resolved` | `False` | include already-resolved blockers |
| `--scope TEXT` | `None` | filter by scope |
| `--note TEXT` | `None` | resolution note |
| `--format json\|xml` | `None` | output format |

---

### `urace decision action [decision_id]`

| Action | Description |
|--------|-------------|
| `list` | list DecisionRecords |
| `inspect` | inspect one record |
| `assess` | assess a decision forecast |

| Flag | Default | Description |
|------|---------|-------------|
| `decision_id` | `None` | required for `inspect`/`assess` |
| `--forecast JSON` | `None` | explicit forecast JSON |
| `--stale` | `False` | show only stale decisions |
| `--scope TEXT` | `None` | filter by scope |
| `--limit INT` | `20` | max records |
| `--format json\|xml` | `None` | output format |

---

### `urace integrity-signal list`

| Flag | Default | Description |
|------|---------|-------------|
| `--type TEXT` | `None` | filter by signal type |
| `--severity BLOCKING\|WARNING\|INFO` | `None` | filter by severity |
| `--resolved` | `False` | include resolved signals |
| `--format json\|xml` | `None` | output format |

---

### `urace why decision_id`

Traverse reasoning chain behind a DecisionRecord.

| Flag | Default | Description |
|------|---------|-------------|
| `decision_id` | required | DecisionRecord ID |
| `--depth INT` | unlimited | maximum traversal depth |
| `--limit INT` | unlimited | max reasoning entries |
| `--format json\|xml` | `None` | output format |

---

### `urace explain id`

Synthesize human-readable explanation of a DecisionRecord.

| Flag | Default | Description |
|------|---------|-------------|
| `id` | required | DecisionRecord ID |
| `--format json\|xml` | `None` | output format |

---

### `urace crc action`

Inspect or regenerate CognitiveResumeContext.

| Action | Description |
|--------|-------------|
| `show` | display CRC |
| `regenerate` | rebuild from current state |

| Flag | Default | Description |
|------|---------|-------------|
| `--product ID,...\|all` | `None` | target product(s) |
| `--format json\|xml` | `None` | output format |

---

### `urace audit`

Inspect or verify enterprise audit chain.

| Flag | Default | Description |
|------|---------|-------------|
| `--verify` | `False` | verify audit chain integrity |
| `--format json\|xml` | `None` | output format |

---

### `urace search [query]`

Search the URACE context ledger and P2P audit ledger.

| Flag | Default | Description |
|------|---------|-------------|
| `query` | `None` | freeform text or `field=value` filter |
| `--kind objective\|operation\|evidence\|decision\|checkpoint\|blocker\|p2p` | `None` | filter by kind |
| `--scope pipeline\|quality_gate\|exchange\|runtime\|output` | `None` | filter by scope |
| `--since ISO_DATE` | `None` | lower bound |
| `--limit INT` | `50` | max results |
| `--format json\|xml` | `None` | output format |

---

### `urace context action`

| Action | Description |
|--------|-------------|
| `list` | list gathered context |
| `graph` | graph context provenance |
| `attention` | show attention-weighted context |

| Flag | Default | Description |
|------|---------|-------------|
| `--id ID` | `None` | filter by context node ID |
| `--depth INT` | `1` | traversal depth |
| `--limit INT` | `32` | max records |
| `--format json\|xml` | `None` | output format |

---

### `urace rules action [id]`

Inspect the Rule Ledger.

| Action | Description |
|--------|-------------|
| `list` | list all rules |
| `inspect` | inspect one rule |
| `graph` | dependency graph |
| `conflicts` | show rule conflicts |
| `changes` | show changes to a rule |

| Flag | Default | Description |
|------|---------|-------------|
| `id` | `None` | rule ID for `inspect`/`changes` |
| `--kind PURPOSE\|DIRECTIVE\|PERMISSION\|PROHIBITION\|OBJECTIVE\|POLICY` | `None` | filter |
| `--scope TEXT` | `None` | filter by scope |
| `--inferred` | `False` | include system-inferred rules |
| `--since ISO` | `None` | start |
| `--until ISO` | `None` | end |
| `--limit INT` | `None` | max records |
| `--offset INT` | `0` | skip N |
| `--format json\|xml` | `None` | output format |

---

### `urace features action`

| Action | Description |
|--------|-------------|
| `list` | list all runtime features |
| `filter` | filter by status/tag |
| `summary` | count per status |
| `show <feature_id>` | detail for one feature |
| `candidates` | list stub/stale/review features by priority |

**`filter` flags:**

| Flag | Description |
|------|-------------|
| `--status TEXT` | `stable/complete/active/stub/stale/review/deprecated/experimental` |
| `--tag TEXT` | `core/integration/optional/security/observability/delivery/self-improvement/ux` |

---

### `urace schema action`

| Action | Description |
|--------|-------------|
| `list` | list output schemas |
| `inspect` | inspect one schema |
| `export` | export schemas |

| Flag | Default | Description |
|------|---------|-------------|
| `--target output-schemas\|bundles\|all` | `"all"` | which registry to export |
| `--format json\|xml` | `None` | output format |

---

### `urace similarity`

Score peer features by TF-IDF intent similarity and collaborative adoption.

| Flag | Default | Description |
|------|---------|-------------|
| `--max-peer-age SECONDS` | `86400` | exclude peers older than this |
| `--timeout SECONDS` | `5.0` | return partial results after timeout |
| `--min-score FLOAT` | `0.0` | omit results below this threshold |

---

### `urace doctor`

Check system health and configuration.

| Flag | Default | Description |
|------|---------|-------------|
| `--json` | `False` | output as JSON |
| `--fix` | `False` | attempt to auto-fix detected issues |

---

### `urace commands`

Show immediate vs durable-input command classification.

| Flag | Default | Description |
|------|---------|-------------|
| `--format json\|xml` | `None` | output format |

---

### `urace change action [id]`

| Action | Description |
|--------|-------------|
| `list` | list accepted changes |
| `explain` | explain one change by ID |

---

### `urace onboard action`

Inspect and confirm the Product Onboard Phase.

| Action | Description |
|--------|-------------|
| `status` | show onboard phase status |
| `confirm` | confirm onboarding complete |

| Flag | Default | Description |
|------|---------|-------------|
| `--note TEXT` | `None` | optional note in OnboardRecord |
| `--scan` | `False` | scan neighbors for unregistered products |
| `--format json\|xml` | `None` | output format |

---

### `urace inbox action [input_id]`

Inspect durable pending input and manage patch proposals.

| Action | Description |
|--------|-------------|
| `list` | list pending inputs |
| `status` | show one input |
| `apply` | apply a proposal |
| `reject` | reject a proposal |

| Flag | Default | Description |
|------|---------|-------------|
| `input_id` | `None` | input or proposal ID |
| `--reason TEXT` | `None` | rejection reason |
| `--kind TEXT` | `None` | filter by kind |
| `--status QUEUED\|REJECTED\|PROCESSED` | `None` | filter by status |
| `--limit INT` | `None` | max records |
| `--format json\|xml` | `None` | output format |

---

### `urace cost summary\|list`

Show executor call receipts and USD estimates.

| `summary` flags | Default | Description |
|-----------------|---------|-------------|
| `--since ISO_DATE` | `None` | lower bound |
| `--limit INT` | `None` | max receipts |
| `--format json\|xml` | `None` | output format |

| `list` flags | Default | Description |
|--------------|---------|-------------|
| `--since ISO_DATE` | `None` | lower bound |
| `--limit INT` | `20` | max receipts |
| `--format json\|xml` | `None` | output format |

---

### `urace usage patterns`

Show aggregated usage patterns, top commands, goal outcomes.

| Flag | Default | Description |
|------|---------|-------------|
| `--limit INT` | `20` | max results |
| `--json` | `False` | JSON output |

---

### `urace resource action`

Inspect per-product resource usage and ROI.

| Action | Description |
|--------|-------------|
| `status` | health overview |
| `report` | detailed report |

| Flag | Default | Description |
|------|---------|-------------|
| `--since ISO` | `None` | start |
| `--until ISO` | `None` | end |
| `--limit INT` | `20` | max records |
| `--offset INT` | `0` | skip N |
| `--format json\|xml` | `None` | output format |

---

### `urace report [action]`

Export optional portable analytics.

| Action | Description |
|--------|-------------|
| `status` | show analytics dependency capabilities |
| `export` | export analytics report |

| Flag | Default | Description |
|------|---------|-------------|
| `--output PATH` | `urace/generated/reports/latest` | output directory |
| `--out FILE` | `urace_report.html` | HTML file path |
| `--xlsx` | `False` | also create XLSX (requires `openpyxl`) |
| `--format json\|xml` | `None` | output format |

---

## 6. Unix CLI — Goals & Rules

### `urace add-goal title`

Queue a Product or URACE goal.

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `title` | str | required | goal title |
| `--success-measure TEXT` | str | required | success criterion |
| `--reason TEXT` | str | `None` | rationale |
| `--target product\|urace` | str | `"product"` | goal target |
| `--priority INT` | int | `70` | 0–100 priority |
| `--expected-value FLOAT` | float | `0.7` | expected value 0–1 |
| `--outcome-measure ID` | str | `None` | authoritative outcome measure identifier |
| `--estimated-cost FLOAT` | float | `0.5` | cost estimate 0–1 |
| `--risk FLOAT` | float | `0.3` | risk 0–1 |
| `--urgency FLOAT` | float | `0.5` | urgency 0–1 |
| `--depends-on ID` | append | `[]` | dependency IDs (repeatable) |
| `--deadline ISO` | str | `None` | deadline |
| `--not-before ISO` | str | `None` | earliest start |
| `--estimate-min-hours FLOAT` | float | `0` | min hours estimate |
| `--estimate-max-hours FLOAT` | float | `0` | max hours estimate |
| `--estimate-confidence low\|medium\|high` | str | `"low"` | confidence level |
| `--priority-floor INT` | int | `None` | minimum priority |
| `--priority-ceiling INT` | int | `None` | maximum priority |
| `--pin` | flag | `False` | pin goal |
| `--necessity-evidence TEXT` | str | `None` | evidence of necessity |
| `--lower-impact-insufficient` | flag | `False` | mark lower impact as insufficient |
| `--format json\|xml` | str | `None` | output format |

---

### `urace goal action [id]`

| Action | Description |
|--------|-------------|
| `list` | list goals |
| `inspect` | inspect one goal |
| `forecast` | forecast goal completion |
| `prioritize` | reprioritize a goal |
| `schedule` | set schedule constraints |
| `pin` / `unpin` | pin/unpin a goal |
| `defer` | defer a goal until date |
| `resume` | resume a deferred goal |
| `resolve-update` | update resolution metadata |
| `disable` / `cancel` / `delete` | disable/cancel/delete a goal |

| Flag | Default | Description |
|------|---------|-------------|
| `id` | `None` | goal ID |
| `--priority INT` | `None` | new priority |
| `--floor INT` | `None` | priority floor |
| `--ceiling INT` | `None` | priority ceiling |
| `--until ISO` | `None` | defer until |
| `--deadline ISO` | `None` | deadline |
| `--not-before ISO` | `None` | earliest start |
| `--clear-deadline` | `False` | clear deadline |
| `--clear-not-before` | `False` | clear not-before |
| `--estimate-min-hours FLOAT` | `None` | min hours |
| `--estimate-max-hours FLOAT` | `None` | max hours |
| `--estimate-confidence low\|medium\|high` | `None` | confidence |
| `--depends-on ID` | append | dependencies |
| `--clear-dependencies` | `False` | clear all dependencies |
| `--decision ID` | `None` | associated decision |
| `--status active\|pending\|blocked\|resolved\|cancelled\|all` | `"active"` | filter status |
| `--limit INT` | `20` | max records |
| `--format json\|xml` | `None` | output format |

---

### `urace intent action [statement]`

Add or manage DIRECTIVE rules.

| Action | Description |
|--------|-------------|
| `add` | add intent statement |
| `list` | list directives |
| `supersede` | supersede a rule |
| `deactivate` | deactivate a rule |
| `rollback` | rollback to prior version |

| Flag | Default | Description |
|------|---------|-------------|
| `statement` | `None` | intent text or version ID |
| `--id RULE_ID` | `None` | rule ID for supersede/deactivate |
| `--scope product\|runtime\|all` | `"product"` | authority scope |
| `--format json\|xml` | `None` | output format |

---

### `urace constraint action [statement]`

Add or manage PROHIBITION/PERMISSION rules.

| Action | Description |
|--------|-------------|
| `add` | add constraint |
| `list` | list constraints |
| `deactivate` | deactivate a constraint |

| Flag | Default | Description |
|------|---------|-------------|
| `statement` | `None` | constraint text |
| `--id RULE_ID` | `None` | rule ID for deactivate |
| `--allow` | `False` | add as PERMISSION instead of PROHIBITION |
| `--scope TEXT` | `"product"` | scope |
| `--format json\|xml` | `None` | output format |

---

### `urace policy action [name] [value]`

Inspect or queue autonomy policy changes.

| Action | Description |
|--------|-------------|
| `list` | list current policies |
| `set` | set a policy value |

Settable policy names: `self-evolution`, `external-metrics`, `analytics-export`

---

### `urace budget action`

| Action | Description |
|--------|-------------|
| `show` | show executor call limits |
| `set` | set limits |

| Flag | Default | Description |
|------|---------|-------------|
| `--daily INT` | `None` | daily executor call limit |
| `--monthly INT` | `None` | monthly executor call limit |
| `--format json\|xml` | `None` | output format |

---

### `urace evaluation action [component] [value]`

Inspect or queue changes to evolution evaluator.

| Action | Description |
|--------|-------------|
| `show` | show current weights |
| `set-weight` | set a component weight |
| `set-minimum` | set minimum threshold |

---

### `urace govern action [gap_id]`

Operator clearance for OperatorGateProtocol conditions.

| Action | Description |
|--------|-------------|
| `clear` | clear an operator gate |
| `list-gates` | list pending gates |

| Flag | Default | Description |
|------|---------|-------------|
| `gap_id` | `None` | gate ID to clear |
| `--note TEXT` | `None` | clearance note |
| `--format json\|xml` | `None` | output format |

---

### `urace self-evolution [mode]`

Control URACE self-evolution mode.

| Mode | Description |
|------|-------------|
| `status` (default) | show current mode |
| `auto` | evolve only when necessary (default mode) |
| `always` | allow eligible improvements |
| `never` | disable self-evolution |

---

## 7. Unix CLI — Data & Sources

### `urace add-context text`

Queue authoritative context.

| Flag | Default | Description |
|------|---------|-------------|
| `text` | required | context text |
| `--source TEXT` | `"repository owner"` | attribution |
| `--format json\|xml` | `None` | output format |

---

### `urace add source`

Queue an external connector source.

| Flag | Default | Description |
|------|---------|-------------|
| `id` | required | source ID |
| `--kind TEXT` | required | source kind |
| `--location URL` | required | source URL |
| `--visibility public\|private` | `"private"` | visibility |
| `--credential-env ENV_VAR` | `None` | env var holding credential |

---

### `urace add metric`

| Flag | Default | Description |
|------|---------|-------------|
| `name` | required | metric name |
| `--source ID` | required | connector source ID |
| `--path TEXT` | required | field path in source |
| `--direction nondecreasing\|nonincreasing` | `"nondecreasing"` | trend direction |
| `--target FLOAT` | `None` | target value |

---

### `urace add vital`

| Flag | Default | Description |
|------|---------|-------------|
| `name` | required | vital name |
| `--numerator ID` | required | metric ID |
| `--denominator ID` | `None` | metric ID (for ratio) |
| `--window TEXT` | `"current"` | time window |
| `--description TEXT` | `""` | description |

---

### `urace add evidence`

Queue operator-provided evidence record.

| Flag | Default | Description |
|------|---------|-------------|
| `--kind TEXT` | required | evidence kind |
| `--summary TEXT` | required | human-readable summary |
| `--source ID` | `None` | source record ID |
| `--detail TEXT` | `None` | extended detail |
| `--format json\|xml` | `None` | output format |

---

### `urace add principal name`

Create a new PrincipalRecord (requires precedence=0 authorization).

| Flag | Default | Description |
|------|---------|-------------|
| `name` | required | identity (email, team ID) |
| `--precedence INT` | `1` | authority lattice (0=root; lower wins) |
| `--scope product\|runtime\|all` | `"product"` | authority scope |
| `--format json\|xml` | `None` | output format |

---

### `urace data action`

Manage structural data sources.

| Action | Description |
|--------|-------------|
| `add <name>` | register a new data source |
| `update <name>` | update an existing data source |
| `remove <name>` | deregister a data source |
| `list` | list registered data sources |
| `sync <name>` | pull evidence from source |
| `push <name>` | push URACE records to source |
| `inspect <name>` | inspect a data source |
| `verify <name>` | test adapter connectivity |
| `status` | health overview of all sources |
| `credential add\|remove\|inspect <name>` | manage credentials |

**`data add` flags:**

| Flag | Default | Description |
|------|---------|-------------|
| `name` | required | data source name |
| `--type TYPE` | required | `json, json_file, csv, sqlite` (others via plugin) |
| `--connect DSN` | required | DSN, path, or connection string |
| `--direction read\|write\|both` | `"read"` | data flow direction |
| `--auto true\|false` | `True` | auto-sync changed readable sources |
| `--schema TEXT` | `None` | schema hint (table, sheet, collection) |
| `--label TEXT` | `""` | description |

**`data credential add` flags:**

| Flag | Default | Description |
|------|---------|-------------|
| `name` | required | data source name |
| `--auth DSN\|API_KEY\|OAUTH2\|CERT\|BASIC\|KERBEROS\|IAM_ROLE\|VAULT_PATH\|ENV_VAR` | required | auth kind |
| `--ref TEXT` | required | pointer to secret (env var, vault path) |
| `--expires ISO` | `None` | expiry timestamp |

**`data list` filters:**

| Flag | Description |
|------|-------------|
| `--type TYPE` | filter by adapter kind |
| `--direction read\|write\|both` | filter by direction |
| `--status CONNECTED\|DISCONNECTED\|DEGRADED\|PENDING` | filter by status |

---

### `urace content action`

Binary content references.

| Action | Description |
|--------|-------------|
| `ref --path FILE` | register by file path |
| `list` | list references |
| `show ref_id` | show one reference |

---

### `urace feedback action [target_id]`

Submit or list outcome feedback.

| Action | Description |
|--------|-------------|
| `list` | list feedback records |
| `submit [target_id]` | submit feedback |

| Flag | Default | Description |
|------|---------|-------------|
| `target_id` | `None` | target record ID |
| `--signal POSITIVE\|NEGATIVE\|NEUTRAL` | `None` | feedback signal |
| `--detail TEXT` | `""` | detail text |
| `--evidence ID` | `None` | evidence record ID |
| `--target ID` | `None` | filter target for list |
| `--limit INT` | `20` | max records |
| `--offset INT` | `0` | skip N |
| `--input-json PATH\|-` | `None` | read from JSON file or stdin |
| `--format json\|xml` | `None` | output format |

---

### `urace export`

Export session context as APS bundle.

| Flag | Default | Description |
|------|---------|-------------|
| `--format aps` | `"aps"` | export format |
| `--out FILE` | `"session.aps.json"` | output file path |

---

### `urace import file`

Import a previously exported APS bundle.

| Arg | Description |
|-----|-------------|
| `file` | path to APS bundle file |

---

## 8. Unix CLI — State Operations

### `urace compact [field_path]` (alias: `compress`)

Queue compaction of an accumulating list field.

| Flag | Default | Description |
|------|---------|-------------|
| `field_path` | `None` | dot-path of field (e.g. `decision_records`) |
| `--dry-run` | `False` | report eligible records without committing |
| `--mode ARCHIVE\|ROLLING_EVICTION` | `None` | override compaction mode |
| `--status` | `False` | show manifest status without queuing |
| `--target FIELD[:PREDICATE]\|all` | `None` | scope; `all` compacts all governed fields |
| `--product ID,...\|all` | `None` | target products |
| `--prompt TEXT` | `None` | freeform guide for field selection |
| `--query TEXT` | `None` | freeform pre-select filter |
| `--format json\|xml` | `None` | output format |

---

### `urace decompact [compaction_event_id]` (alias: `decompress`)

Restore records from an ARCHIVE-mode CompactionEvent.

| Flag | Default | Description |
|------|---------|-------------|
| `compaction_event_id` | `None` | CompactionEvent ID |
| `--field-path TEXT` | `None` | dot-path of field (inferred from manifest if omitted) |
| `--record-id ID` | `None` | extract single record read-only |
| `--target FIELD:latest\|FIELD:EVENT-ID` | `None` | auto-resolve from manifest |
| `--product ID,...\|all` | `None` | target products |
| `--query TEXT` | `None` | freeform filter for output |
| `--format json\|xml` | `None` | output format |

---

### `urace amend [compaction_event_id] [record_id]`

Apply in-place amendment to an archived record.

| Flag | Default | Description |
|------|---------|-------------|
| `compaction_event_id` | `None` | CompactionEvent ID |
| `record_id` | `None` | record ID within archive |
| `--notice TEXT` | required | amendment notice (what changed and why) |
| `--kind PROVENANCE_REVISED\|SUPERSEDED\|CUSTOM` | `"PROVENANCE_REVISED"` | amendment kind |
| `--target RECORD-ID` | `None` | auto-find compaction event covering this record |
| `--product ID` | `None` | target specific product |
| `--format json\|xml` | `None` | output format |

---

### `urace reset`

Reset URACE state to clean defaults.

| Flag | Default | Description |
|------|---------|-------------|
| `--release-clean` | `False` | flush all personal data and improvement queues |
| `--yes` | `False` | skip confirmation prompt |

---

### `urace rollback`

Restore product files from last accepted stable snapshot.

| Flag | Default | Description |
|------|---------|-------------|
| `--dry-run` | `False` | show what would be restored |
| `--json` | `False` | machine-readable output |

---

## 9. Unix CLI — P2P Exchange

### `urace exchange settings show`

Show all exchange settings (from `policy.json`).

---

### `urace exchange settings set`

Persist exchange settings to `policy.json`.

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--enabled` | bool | `True` | enable/disable exchange |
| `--network` | bool | `False` | enable network participation |
| `--advertise` | bool | `False` | advertise to peers |
| `--auto-select` | bool | `True` | auto-select peers |
| `--max-transfers-per-day INT` | int | `20` | daily transfer limit |
| `--max-transfers-per-peer-per-day INT` | int | `5` | per-peer daily transfer limit |
| `--max-bytes-per-day INT` | int | `1048576` (1 MB) | daily byte limit |
| `--max-rpc-per-day INT` | int | `200` | daily RPC call limit |
| `--max-rpc-per-peer-per-day INT` | int | `50` | per-peer daily RPC limit |
| `--min-peer-version INT` | int | `2` | minimum peer protocol version |
| `--feature-borrow-enabled` | bool | `True` | allow feature borrowing |
| `--p2p-mint-enabled` | bool | (from policy) | allow P2P minting |
| `--p2p-sell-enabled` | bool | (from policy) | allow P2P selling |
| `--compress-enabled` | bool | (from policy) | enable compression |
| `--decompress-enabled` | bool | (from policy) | enable decompression |
| `--compress-wire` | bool | `False` | compress wire transfer |
| `--bundle-max-age-seconds INT` | int | `604800` (7d) | max bundle age |
| `--bandwidth-profile auto\|low\|high` | str | `"auto"` | wire transfer profile |
| `--transfer-chunk-size INT` | int | `0` | override chunk size (512–131072 bytes) |
| `--relay-only` | bool | `False` | route all traffic through relays |
| `--network-mode intranet\|internet\|hybrid` | str | `"hybrid"` | network scope |
| `--internet-gateway PEER_ID` | str | `None` | bridge peer for intranet→internet |
| `--crypto-network ID` | str | `None` | blockchain network ID |
| `--rpc-provider-url URL` | str | `None` | EVM JSON-RPC endpoint |
| `--chain-id INT` | int | `137` (Polygon PoS) | EVM chain ID |
| `--erc20-contract ADDR` | str | `None` | URACE ERC-20 contract address |
| `--urace-credit-usd-rate INT` | int | `1000` | display-only accounting rate (N base units = $1) |
| `--consensus-min-threshold INT` | int | `2` | min consensus peer threshold |
| `--baseline-grant-tokens INT` | int | `3` | baseline grant for new peers |

---

### `urace exchange network`

| Verb | Description |
|------|-------------|
| `discover [--seconds 3]` | discover peers |
| `probe <peer_id>` | probe a specific peer |
| `refresh [--limit 3]` | refresh peer list |
| `serve [--host 127.0.0.1] [--port 0] [--tunnel auto\|none\|localhost.run\|cloudflare] [--install-service]` | start P2P server |
| `assets [query] [--peer-limit 3]` | search peer catalogs |
| `fetch-asset <peer_id> <asset_id>` | fetch asset into quarantine |
| `consensus-status` | show P2P consensus state |
| `public-address [--stun-host stun.l.google.com] [--stun-port 19302]` | STUN probe |
| `disconnect [--duration-minutes 60]` | temporarily pause networking |
| `reconnect` | clear disconnect, resume networking |
| `reachability [--type bootstrap,relay] [--timeout 5.0]` | check NAT type and node capability |
| `setup-node [--timeout 5.0]` | check NAT, assign roles, print next steps |
| `peers [--detail]` | show connected peer count and anonymized IDs |
| `size` | estimated network size from gossip |
| `routing-table` | Kademlia DHT routing table |
| `port-to-internet [--auto] [--dry-run] [--features ID,...] [--min-kpi-score 0.5] [--min-ratings 2]` | guide intranet→internet migration |
| `find-node <target_peer_id>` | Kademlia find_node RPC |
| `shamir-deliver <feature_id> --holder <peer_id> --share-index INT` | deliver DEK share |
| `tail-sync --from-peer <peer_id>` | pull ledger seal+tail |

**`serve` tunnel modes:**
- `auto` (default): checks direct inbound (STUN); if blocked, uses SSH localhost.run (zero install, zero account); never downloads binaries
- `localhost.run`: SSH reverse tunnel via `ssh -R 80:localhost:{port} nokey@localhost.run`
- `cloudflare`: requires `cloudflared` binary already installed
- `none`: disabled

---

### `urace exchange peer`

| Verb | Description |
|------|-------------|
| `list` | list known peers |
| `identity` | show local identity |
| `add --certificate CERT [--endpoint URL] [--post-quantum-identity PQI]` | add a peer |
| `block <peer_id>` | block a peer |
| `unblock <peer_id>` | unblock a peer |
| `rotate <old_peer_id> --new-certificate CERT` | rotate peer identity |
| `role [peer_id] [--set admin\|operator\|readonly]` | show/set peer role |

---

### `urace exchange bootstrap`

| Verb | Description |
|------|-------------|
| `list` | list bootstrap peers |
| `add <endpoint>` | add a bootstrap peer |
| `remove <endpoint>` | remove a bootstrap peer |
| `announce [--endpoint URL] [--timeout 5.0]` | announce self to bootstrap peers (STUN auto-detect if no endpoint) |

---

### `urace exchange node`

| Verb | Description |
|------|-------------|
| `check [--timeout 5.0]` | check which roles are locally feasible |
| `roles [--set bootstrap,relay,consumer,creator]` | show or set node roles |

---

### `urace exchange ledger`

| Verb | Description |
|------|-------------|
| `summary` | overall ledger summary |
| `balance <peer_id>` | balance for a peer |
| `history <peer_id> [--limit 50]` | transaction history |
| `earned <peer_id>` | earned balance (REP_SOURCE_WORK only) |
| `transfer <peer_id> <amount_units> [--yes]` | manually transfer tokens |
| `supply-calc [--peers 1000] [--ledger-mb 50] [--bandwidth-kbps 1000] [--sync-secs 30] [--row-bytes 400] [--rows-per-feature 20] [--adoption-rate 0.1]` | derive optimal token supply |

---

### `urace exchange feature`

| Verb | Description |
|------|-------------|
| `define <feature_id> [--depends-on ID] [--wanted bool] [--offered bool] [--wants ID] [--language TEXT]` | define a feature |
| `policy <feature_id> [--access reviewed-direct\|open] [--license-id ID] [--essential bool] [--open-after-unix UNIX] [--resale bool]` | set feature policy |
| `catalog` | list all features |
| `declare <feature_id> --manifest PATH` | declare a feature manifest |
| `lifecycle <atom_id> <active\|deprecated\|obsolete> [--replacement ID]` | set lifecycle status |
| `rate <feature_id> --outcome positive\|negative\|neutral [--score FLOAT]` | rate a feature |
| `recommend [--limit 5]` | recommend top features for current context |

---

### `urace exchange equity`

| Verb | Flags | Description |
|------|-------|-------------|
| `holdings <feature_id>` | — | show equity holdings |
| `grant <feature_id>` | `[--creator ID] [--description TEXT] [--tags TEXT] [--include-context kinds] [--isolate-context] [--skip-pii-check] [--spec-context TEXT] [--artifact-path PATH] [--visibility private\|org\|public]` | grant initial equity |
| `sell <feature_id>` | `--to <buyer_id> --bp INT [--price INT]` | sell equity tranche |
| `price <feature_id>` | — | current market price |
| `transfers <feature_id>` | — | equity transfer history |
| `list-for-sale <feature_id>` | `[--bp INT] [--price INT]` | list equity for sale |
| `listings` | `[--feature ID]` | open equity listings |
| `cancel-listing <listing_id>` | — | cancel listing |
| `fill-listing <listing_id>` | `[--yes] [--skip-quality-check] [--skip-trust-check]` | buy a listing |
| `deprecate <feature_id>` | `--creator ID [--reason TEXT]` | deprecate feature |
| `register-replica <feature_id>` | `[--artifact-hash SHA256] [--chunk-indices LIST]` | register as replica holder |
| `auto-buy` | — | run one auto-buy pass |
| `auto-sell` | — | run one auto-sell pass |
| `challenge <feature_id>` | `--challenger ID [--reference-feature ID] [--evidence TEXT] [--stake INT]` | file provenance challenge |
| `resolve-challenge <challenge_id>` | `--verdict upheld\|rejected [--resolver ID]` | resolve challenge |
| `release-stake <feature_id>` | — | release stake after window expires |
| `challenge-status <feature_id>` | — | show challenge status |
| `cost <operation>` | `[--price INT] [--artifact-size INT] [--executor-calls INT]` | operation cost breakdown |
| `dek-unwrap` | `--listing-id ID --private-key-hex HEX` | unwrap DEK |
| `escrow-status` | — | show pending escrow |
| `trade-config show\|set\|show-presets` | see below | auto-trade thresholds |
| `visibility` | `--feature-id ID` | show feature visibility |

**`equity trade-config set` flags:**

| Flag | Description |
|------|-------------|
| `--auto-buy-enabled bool` | enable auto-buy |
| `--min-quality FLOAT` | minimum Wilson quality |
| `--min-adoption INT` | minimum adoption count |
| `--max-price-mult FLOAT` | max price multiplier |
| `--max-bp INT` | max basis points per feature |
| `--max-spend INT` | max spend per run |
| `--max-adoption-rate FLOAT` | max adoption rate |
| `--min-supply-pressure FLOAT` | min supply pressure |
| `--min-remaining-adopters INT` | min remaining adopters |
| `--min-lucrativity FLOAT` | min lucrativity score |
| `--lucrativity-window FLOAT` | lucrativity window in days |
| `--auto-sell-enabled bool` | enable auto-sell |
| `--min-return-mult FLOAT` | min return multiplier |
| `--bp-to-sell INT` | basis points to sell per trigger |
| `--min-hold-bp INT` | min hold BP to trigger |
| `--sell-on-near-depleted bool` | sell when nearly depleted |
| `--sell-on-slowing bool` | sell when growth slowing |
| `--preset conservative\|balanced\|aggressive` | apply named preset |
| `--auto-tune` | auto-derive from network conditions |
| `--roi-preference short_term\|medium_term\|long_term` | ROI preference preset |

---

### `urace exchange work`

| Verb | Flags | Description |
|------|-------|-------------|
| `list [--state STATE]` | — | list work requests |
| `status <request_id>` | — | show request state |
| `create <spec>` | `--budget INT --min-rep 0.3 --nodes 1 --complexity 0.5 --mode agora\|cohort --cohort-reputation-floor 0.5` | create request |
| `bid <request_id>` | `--rep FLOAT` | bid on a request |
| `accept <request_id>` | `--bidder ID` | accept a bid |
| `deliver <request_id>` | `--hash SHA256` | submit delivery |
| `verify <request_id>` | `--approve bool --reason TEXT [--dispute-kind quality\|gibberish\|timeout\|other]` | verify delivery |
| `review <request_id>` | `--approve bool` | peer review for quorum |
| `merge <request_id>` | `--budget INT` | merge as co-requester |
| `arbitrate <request_id>` | `[--count 3]` | trigger arbitrator selection |
| `claim <request_id>` | `[--mint-value INT]` | claim delivered work |
| `decompose <spec>` | `--budget INT [--complexity 0.8]` | auto-decompose into sub-requests |
| `chain-root` | — | compute tamper-evident audit chain hash |

---

### `urace exchange settle`

| Verb | Flags | Description |
|------|-------|-------------|
| `status` | — | show settlement config and pending balance |
| `run [--dry-run]` | — | execute pending on-ramp/off-ramp settlements |

---

### `urace exchange compact`

| Verb | Flags | Description |
|------|-------|-------------|
| `contracts [--older-than-days 7.0]` | — | compact closed work contracts |
| `checkpoint` | — | write ledger checkpoint for P2P bootstrap |
| `search [query] [--kind KIND] [--peer ID] [--feature ID] [--since-unix FLOAT] [--limit 50]` | — | search P2P audit ledger |
| `sync-tail` | — | show checkpoint+tail for fast sync |
| `sync-state` | — | show sliding-window sync state |
| `light-balance <peer_id>` | — | compute balance from seal+tail |
| `depletion <feature_id> [--network-size 1]` | — | check depletion status |
| `balance-fast <peer_id>` | — | O(tail) balance from latest sealed block |
| `compress [--older-than-days 30.0] [--dry-run]` | — | compress old audit rows to archive |
| `decompress [archive_id] [--limit 200]` | — | decompress archive for inspection |

---

### `urace exchange bundle`

| Verb | Flags | Description |
|------|-------|-------------|
| `prepare <peer_id> <feature_id>` | `--file PATH [--reviewed]` | prepare bundle |
| `inspect <bundle_id>` | — | inspect bundle |
| `send <bundle_id>` | — | send bundle to peer |
| `import --file PATH` | — | import a bundle |
| `review <bundle_id>` | `<approved-for-evaluation\|rejected\|blocked> [--note TEXT]` | review bundle |
| `evaluate <bundle_id>` | — | evaluate a bundle |
| `manifest <peer_id>` | `--baseline-evaluation-id ID [--failures ID ...]` | generate manifest |
| `fetch-artifact <bundle_id>` | `[--out PATH]` | fetch artifact bytes |

---

### `urace exchange chunk`

| Verb | Flags | Description |
|------|-------|-------------|
| `status <artifact_sha256>` | — | show chunk store status |
| `store <artifact_sha256>` | `--input PATH` | manually store artifact |
| `find-holders <artifact_sha256> <chunk_idx>` | — | Kademlia DHT lookup for chunk holders |

---

### `urace exchange rule`

| Verb | Flags | Description |
|------|-------|-------------|
| `set <peer_id> <feature_id> <send\|receive>` | `--allow bool` | set transfer rule |
| `export [--file PATH]` | — | export all rules to JSON |
| `import --file PATH` | — | import rules from JSON |

---

### `urace exchange reputation`

| Verb | Flags | Description |
|------|-------|-------------|
| `show <peer_id>` | — | reputation breakdown |
| `leaderboard [--limit 10]` | — | top peers by earned reputation |
| `history <peer_id> [--days 30]` | — | reputation event trend |

---

### `urace exchange network-audit list`

| Flag | Default | Description |
|------|---------|-------------|
| `--kind TEXT` | `None` | filter by event kind |
| `--peer ID` | `None` | filter by peer |
| `--limit INT` | `100` | max records |

---

### `urace exchange market stats`

| Flag | Default | Description |
|------|---------|-------------|
| `--window-hours INT` | `24` | velocity window in hours |

---

### `urace exchange bridge`

Stubs (blockchain not yet connected).

| Verb | Flags | Description |
|------|-------|-------------|
| `nft-mint` | `--feature-id ID [--creator ID]` | request NFT attestation (stub) |
| `on-ramp` | `--amount INT --address ADDR` | request crypto on-ramp (stub) |
| `off-ramp` | `--amount INT --address ADDR` | request crypto off-ramp (stub) |
| `on-chain-verify` | `--feature-id ID` | request on-chain verification (stub) |

---

### `urace exchange reset all`

Delete all exchange audit rows.

| Flag | Default | Description |
|------|---------|-------------|
| `--yes` | `False` | skip confirmation |

---

### `urace exchange status\|audit\|rank`

| Verb | Flags | Description |
|------|-------|-------------|
| `status` | — | exchange status summary |
| `audit [--detail] [--limit 50] [--offset 0] [--peer-id ID] [--feature-id ID]` | — | audit log |
| `rank [--want FEATURE ...]` | — | rank peers by want list |

---

### `urace p2p`

Operator tools for P2P security update distribution.

| Action | Flags | Description |
|--------|-------|-------------|
| `keygen [--out PATH]` | — | generate Ed25519 release keypair |
| `build-update --key PATH [--out PATH] [--log-rekor] [--anchor-ots]` | — | build signed update bundle |
| `publish-update --bundle PATH --key PATH [--url URL]` | — | publish bundle to DHT |
| `check-update` | — | query DHT for available update |
| `apply-update --bundle PATH [--no-tests]` | — | verify and apply update (operator-gate) |

---

## 10. Unix CLI — Governance

### `urace controls show\|set`

Show or set system capability flags.

**`controls set` flags:**

| Flag | Description |
|------|-------------|
| `--executor-enabled bool` | enable/disable executor |
| `--freeform-enabled bool` | enable/disable freeform input |
| `--machine-interface-enabled bool` | enable/disable M2M interface |
| `--compress-enabled bool` | enable/disable compression |
| `--decompress-enabled bool` | enable/disable decompression |
| `--p2p-mint-enabled bool` | enable/disable P2P minting |
| `--p2p-sell-enabled bool` | enable/disable P2P selling |
| `--p2p-borrow-enabled bool` | enable/disable P2P borrowing |
| `--context-mint-enabled bool` | enable/disable context minting |
| `--context-mint-objectives bool` | include objectives in context mint |
| `--context-mint-evidence bool` | include evidence in context mint |
| `--context-mint-decisions bool` | include decisions in context mint |
| `--context-mint-operations bool` | include operations in context mint |
| `--context-mint-checkpoints bool` | include checkpoints in context mint |
| `--compliance-mode bool` | enable compliance mode |
| `--executor-id ID` | target specific executor |
| `--data-source-id ID` | target specific data source |
| `--product-id ID` | apply to specific product |

---

### `urace peer-review action`

| Action | Description |
|--------|-------------|
| `list` | list quarantined peer artifacts |
| `evaluate <bundle_id>` | evaluate for safety |
| `promote <bundle_id>` | promote into improvement workflow |

---

### `urace fleet action`

Run multiple products in parallel.

| Action | Description |
|--------|-------------|
| `run` | run all products |
| `status` | show fleet status |
| `stop [name]` | stop one or all products |
| `broadcast` | broadcast command to all products |
| `capacity` | show capacity info |
| `config-push` | push config to all products |

| Flag | Default | Description |
|------|---------|-------------|
| `--dry-run` | `False` | simulate without executing |
| `--verbose` | `False` | verbose output |
| `--config-key KEY` | `None` | dot-separated config key to push |
| `--config-value JSON` | `None` | JSON-encoded value |
| `--format json\|xml` | `None` | output format |

---

## 11. Unix CLI — Integration

### `urace github action`

| Action | Flags | Description |
|--------|-------|-------------|
| `status [--repo OWNER/REPO]` | — | GitHub connection status |
| `connect <OWNER/REPO> [--token-env URACE_GITHUB_TOKEN]` | — | connect to repo |
| `push-goals [--dry-run]` | — | push goals as GitHub issues |
| `trigger-workflow <workflow> [--ref main] [--inputs JSON]` | — | trigger GitHub Actions |

---

### `urace git [git_args...]`

Pass-through to git CLI, scoped to current product.

---

### `urace gh [gh_args...]`

Pass-through to GitHub CLI (`gh` must be installed).

---

### `urace executor action`

| Action | Flags | Description |
|--------|-------|-------------|
| `status` | — | show executor config |
| `attach` | `--command PATH --id codex-primary --adapter codex-cli\|claude-cli --priority 100 --capability [discovery\|planning\|mutation\|evaluation\|execution] [--max-calls-24h N] [--max-calls-30d N]` | attach executor |
| `detach` | `--id ID` | detach executor |
| `retry-policy` | `--retry-mode automatic\|dynamic\|fixed --retry-delay-ms 60000 --retry-fallback-seconds 18000` | set retry policy |
| `circuit-breaker` | `--cb-action status\|reset [--cb-provider ID]` | circuit breaker control |

---

### `urace api action`

Machine interface (ExternalInterfaceProtocol).

| Action | Description |
|--------|-------------|
| `call` | execute one command |
| `batch` | execute array of commands |
| `serve` | start MCP stdio or A2A HTTP server |
| `watch` | stream trace records |
| `version` | show API version |
| `commands` | list available commands |
| `protocols` | list supported protocols |

**`api call` / `api batch` flags:**

| Flag | Default | Description |
|------|---------|-------------|
| `--command TEXT` | `None` | command string |
| `--argv JSON` | `None` | exact argv array as JSON |
| `--params JSON` | `None` | JSON object of parameters |
| `--input-json PATH\|-` | `None` | JSON input file or stdin |
| `--stream` | `False` | emit NDJSON progress |
| `--continue-on-error` | `False` | continue batch on error |
| `--format json\|xml` | `None` | output format |

**`api serve` flags:**

| Flag | Default | Description |
|------|---------|-------------|
| `--transport stdio\|a2a` | `"stdio"` | MCP stdio or A2A HTTP |
| `--policy PATH` | `None` | integration capability policy JSON |
| `--port INT` | `8765` | A2A loopback port |
| `--token-env ENV_VAR` | `"URACE_A2A_TOKEN"` | env var with A2A bearer secret |

**`api watch` flags:**

| Flag | Default | Description |
|------|---------|-------------|
| `--kinds KINDS` | `""` | comma-separated TraceRecord kinds |
| `--since ISO` | `None` | start timestamp |
| `--follow` | `False` | tail live trace records |

---

## 12. Unix CLI — System Tools

### `urace plan`

Show current improvement plan.

| Flag | Default | Description |
|------|---------|-------------|
| `--format json\|xml` | `None` | output format |

---

### `urace classify [text]`

Internal freeform executor routing (not user-facing — called by shell for NL input).

| Flag | Default | Description |
|------|---------|-------------|
| `text` | `""` | freeform text to classify |
| `--confirm` | `False` | confirm validated non-permission sections |
| `--selection TEXT` | `None` | explicit alternative number or skip |
| `--p2p-asset ID` | `None` | remote open-asset ID to fetch |
| `--file PATH` | `None` | load input from file instead of inline |
| `--path PATH` | `None` | load file content into freeform context |
| `--ledger-context auto\|always\|never` | `"auto"` | ledger context injection control |
| `--format json\|xml` | `None` | output format |

---

### `urace help [operation...]`

Show operation catalog or contextual help.

---

### `urace portfolio [--help] [portfolio_args...]`

Run optional isolated-worktree portfolio helper.

---

---

## 13. Interactive Shell (REPL)

Entry: `urace` (no args, TTY) or `urace shell`

**Prompt format:**
```
urace [daemon:running·internet·rel+boo·P2P:7301]>
```
- `daemon:running` or `daemon:stopped`
- `network_mode` from exchange config
- Role abbreviations: `rel`=relay, `boo`=bootstrap, `con`=consumer, `cre`=creator
- `P2P:<port>` from exchange config

**Tab completion:** slash commands + `_KNOWN_FIRST_WORDS`
**History:** `~/.urace/shell_history` (readline, 500 entries)

---

### Slash Commands

| Command | Syntax | Description |
|---------|--------|-------------|
| `/help` | `/help` | show slash command reference |
| `/status` | `/status` | daemon RPC status + node roles |
| `/stop` | `/stop` | stop daemon and P2P server |
| `/pause` | `/pause` | pause improvement loop |
| `/resume` | `/resume` | resume improvement loop |
| `/events` | `/events [N] [--follow\|-f]` | recent audit events; `--follow` = 2s poll streaming |
| `/config` | `/config [key] [value]` | get/set config; dotted keys: `p2p.network_mode internet` |
| `/peers` | `/peers` | connected peers (anonymized) |
| `/roles` | `/roles` | node roles |
| `/exit` / `/quit` | `/exit` | exit shell |

**Input routing:**
1. `/command` → slash handler
2. Known first word (see list below) → `main(argv)` inline
3. Any other text → `main(['classify', text])` (NL executor routing)

**Known first words (direct CLI dispatch from shell):**
```
status check vitals rules auto pause resume init exchange compact search doctor
controls trial daemon start stop crypto cost export report schema data product
features rollback security config resource trace explain watch feedback
freeform-text
```

---

## 14. M2M Interface

### `urace m2m '<json>'` or `urace m2m --stdin`

Machine-to-machine JSON dispatch. Converts JSON body to argv and calls `main()`.

**Request schema:**

```json
{
  "command": "exchange settings set",
  "params": {
    "enabled": true,
    "network_mode": "internet",
    "max_transfers_per_day": 50
  }
}
```

**Rules:**
- `command` (required): space-separated CLI command string
- `params` (optional): object; boolean `true` → `--flag`, boolean `false` → omitted,  
  other values → `--flag=value`
- Always appends `--json` to output
- Returns standard CLI JSON output

**Example calls:**

```bash
# inline
urace m2m '{"command": "exchange settings show"}'
urace m2m '{"command": "exchange bootstrap announce"}'
urace m2m '{"command": "status"}'

# stdin
echo '{"command":"exchange settings set","params":{"network_mode":"internet"}}' \
  | urace m2m --stdin

# via API server
urace api call --command "exchange settings show" --params '{}' --json
```

---

### `urace api batch` Input Schema (NDJSON / JSON array)

```json
[
  {"command": "check", "params": {}},
  {"command": "exchange settings show", "params": {}},
  {"argv": ["status", "--json"]}
]
```

Each entry supports `command+params` **or** `argv` (exact string array).

---

### APS Bundle Schema (`urace export` / `urace import`)

```json
{
  "schema": "urace-aps-v1",
  "exported_at": "2026-11-13T00:00:00Z",
  "turns": [/* session context rows */]
}
```

---

## 15. Daemon RPC (TCP :7474)

**Transport:** TCP, `127.0.0.1:7474`  
**Protocol:** newline-delimited JSON (`msg\n` → `response\n`)  
**Schema:** `urace-rpc-v1`

### Methods

#### `ping`

```json
// Request
{"method": "ping"}

// Response
{"schema": "urace-rpc-v1", "pong": true}
```

---

#### `status`

```json
// Request
{"method": "status"}

// Response
{"schema": "urace-rpc-v1", "status": "running", "pid": 12345}
// or
{"schema": "urace-rpc-v1", "status": "stopped", "pid": null}
```

---

#### `stop`

```json
// Request
{"method": "stop"}

// Response
{"schema": "urace-rpc-v1", "status": "stopping"}
```

Side effect: sets daemon `stopped[0] = True` → loop exits, PID cleared.

---

#### `dispatch`

Run any `urace` argv inline, capture JSON output.

```json
// Request
{"method": "dispatch", "argv": ["exchange", "settings", "show"]}

// Response (success)
{"schema": "urace-rpc-v1", "output": "{\"enabled\":true,...}"}

// Response (error)
{"schema": "urace-rpc-v1", "error": "...", "output": ""}
```

Notes:
- `--json` is auto-appended if not in argv
- Runs in-process via `cli.main()`
- stdout captured; stderr not captured

---

#### `events`

Fetch recent P2P network audit events.

```json
// Request
{"method": "events", "limit": 20}

// Response
{"schema": "urace-rpc-v1", "output": "[{\"kind\":\"PEER_DISCOVERED\",...}]"}
```

Calls `exchange network-audit list --limit N --json` internally.

---

## 16. API Server Interface

### MCP stdio (`urace api serve`)

Implements MCP protocol over stdio. Used by Claude Desktop, VS Code MCP extensions.

```bash
urace api serve --transport stdio [--policy capability-policy.json]
```

---

### A2A HTTP (`urace api serve --transport a2a`)

Loopback HTTP server.

```bash
urace api serve --transport a2a --port 8765 --token-env URACE_A2A_TOKEN
```

**Endpoint:** `http://127.0.0.1:8765`  
**Auth:** Bearer token from env var  
**Call format:** same as `api call` params

---

## 17. Config Files & Schemas

### `config.json`

Path: `urace/runtime/urace/config.json`  
Override active product: env var `URACE_ACTIVE_PRODUCT`

**Top-level keys and defaults:**

| Key | Default | Description |
|-----|---------|-------------|
| `analytics_export.include_xlsx` | `false` | include XLSX in reports |
| `analytics_export.mode` | `"ON_CHECKPOINT"` | when to export |
| `analytics_export.output` | `"generated/reports/latest"` | output path |
| `authority.source` | `"repository owner"` | authority source |
| `authority.provenance` | `"CI bootstrap"` | provenance |
| `authority.delegated` | see below | delegated authority areas |
| `authority.reserved` | see below | reserved authority (not delegatable) |
| `auto_goals.enabled` | `false` | auto-generate goals |
| `auto_goals.replenish_backlog` | `true` | replenish goal backlog |
| `execution_workflow` | `"core"` | `"core"` or `"specification-trial"` |
| `executor.enabled` | `false` | executor enabled |
| `executor.kind` | `"subprocess"` | executor kind |
| `executor.command` | `null` | executor binary path |
| `executor.timeout_seconds` | `300` | execution timeout |
| `executor.max_executor_result_bytes` | `1048576` | max result bytes |
| `executor.max_executor_calls_per_24h` | `null` | daily call limit |
| `executor.max_executor_calls_per_30d` | `null` | monthly call limit |
| `executor.discovery_interval_seconds` | `300` | discovery interval |
| `executor.max_discovery_interval_seconds` | `3600` | max discovery interval |
| `executor.capacity_fallback_seconds` | `300` | capacity fallback |
| `executor.validation_timeout_seconds` | `60` | validation timeout |
| `executor.progress_heartbeat_seconds` | `30` | heartbeat interval |
| `github.repo` | `"owner/repo"` | GitHub repo |
| `github.token_env` | `"URACE_GITHUB_TOKEN"` | token env var |
| `p2p` | `{}` | P2P nested config (see below) |
| `product` | `"ci-test-product"` | active product name |
| `product_registry` | `[]` | list of registered products |
| `product_type` | `"generic"` | primary product type |
| `product_types` | `["generic"]` | list of product types |
| `self_evolution_policy.mode` | `"NECESSARY_ONLY"` | `NECESSARY_ONLY\|ALWAYS\|NEVER` |
| `state_path` | `"/tmp/.../state.json"` | state file path |
| `evaluation_system.weights.regression_safety` | `2.0` | evaluator weight |
| `evaluation_system.weights.execution_acceptance` | `1.5` | evaluator weight |
| `evaluation_system.weights.goal_completion` | `1.0` | evaluator weight |
| `evaluation_system.weights.productive_call_yield` | `1.0` | evaluator weight |
| `evaluation_system.minimum_evidence_units` | `5` | min evidence for cycle |

**`authority.delegated`:** `assessment, objectives, priority, plans, measurement, validation`  
**`authority.reserved`:** `change retained purpose, weaken normative invariants, publish externally, spend money`

---

### `exchange/policy.json`

Path: `<state_dir>/exchange/<product_hash_prefix>/policy.json`  
Schema: `urace-exchange-v2`

**Default values (from `Exchange.load()`):**

```json
{
  "schema": "urace-exchange-v2",
  "enabled": true,
  "network": false,
  "advertise": false,
  "auto_select": true,
  "auto_relay": false,
  "token_settlement": false,
  "auto_trust_first_contact": false,
  "default_feature_rules": {},
  "relay_only": false,
  "peers": {},
  "features": {},
  "rules": {},
  "feature_borrow_enabled": true,
  "max_transfers_per_day": 20,
  "max_transfers_per_peer_per_day": 5,
  "max_bytes_per_day": 1048576,
  "max_rpc_per_day": 200,
  "max_rpc_per_peer_per_day": 50,
  "min_peer_version": 2,
  "bootstrap_peers": [],
  "compress_wire": false,
  "bandwidth_profile": "auto",
  "transfer_chunk_size": 0,
  "relay_credit_per_kb": 1,
  "node_roles": [],
  "urace_credit_usd_rate": 1000,
  "bootstrap_credit_per_connection": 5,
  "bundle_max_age_seconds": 604800,
  "network_mode": "hybrid",
  "internet_gateway": null,
  "rpc_provider_url": null,
  "erc20_contract": null,
  "chain_id": 137,
  "crypto_network": null,
  "p2p": {
    "consensus_trigger_min_peers": 2,
    "baseline_grant_tokens": 3
  }
}
```

**Notable fields:**
- `urace_credit_usd_rate`: display-only accounting (1000 base units = $1); never sets market price
- `token_settlement`: CRYPTO_PENDING — activates when `crypto_network` is configured
- `node_roles`: `[]` by default; upgraded to `["relay", "bootstrap"]` when tunnel URL is obtained

---

### `state.json`

Path: `<state_dir>/state.json` (atomic write, flock-guarded)

**Selected top-level fields:**

| Field | Description |
|-------|-------------|
| `schema` | state document schema version |
| `decision_records` | DecisionRecord list |
| `evidence` | EvidenceRecord list |
| `goals` | GoalRecord list |
| `rules` | RuleRecord list |
| `blockers` | BlockerRecord list |
| `compliance_records` | ComplianceRecord list |
| `trace_records` | TraceRecord list |
| `milestones` | ProductMilestone list |
| `unresolved_effects` | pending effects awaiting reconciliation |
| `integrity_signals` | IntegritySignal list |
| `compaction_manifest` | CompactionManifest |

---

### `transaction.json`

Path: `<state_dir>/transaction.json`  
Interim write buffer; merged into `state.json` on `reconcile_transaction()`.

---

### `daemon.pid`

Path: `<state_dir>/daemon.pid`  
Contains process PID as ASCII integer.

---

### `~/.urace/shell_history`

Readline history for interactive shell. 500 entries max.

---

### Exchange directory structure

```
<state_dir>/exchange/<product_hash>/
  policy.json              # exchange settings (above)
  audit.jsonl              # append-only audit rows (authenticated chain)
  bundle-artifacts/        # AES-GCM encrypted artifacts
    <sha256[:2]>/<sha256>
  artifact-seed.bin        # local private seed for artifact key derivation (chmod 600)
  chunks/                  # erasure-coded ChunkStore (v2 DHT path)
  checkpoint.json          # ledger checkpoint for fast sync
```

---

## 18. Environment Variables

| Variable | Description |
|----------|-------------|
| `URACE_ACTIVE_PRODUCT` | override active product from `config.json` |
| `URACE_GITHUB_TOKEN` | GitHub personal access token |
| `URACE_A2A_TOKEN` | A2A HTTP server bearer token |

---

## 19. Unix CLI — Configuration & Advanced Commands

### `urace configuration setting [value]`

Inspect or change persistent settings.

| Setting | Description |
|---------|-------------|
| `show` | show all persistent settings |
| `effort status\|low\|medium\|high\|inherit` | URACE resource allocation |
| `executor-budget [--daily INT] [--monthly INT]` | executor call budget |
| `evaluation-weight [component] [value] [--component TEXT]` | evaluator weight |
| `value-discovery [--enabled bool] [--external-research bool] [--ranking bool] [--freshness-seconds INT] [--research-seconds INT] [--research-sources INT]` | project value suggestions config |
| `decision-feedback [--enabled bool] [--mode auto\|executor] [--executor auto\|codex\|claude] [--cache-seconds INT]` | local decision benefit forecasts |
| `executor-skills [--enabled bool] [--mode auto\|off] [--max-selected INT] [--max-instruction-bytes INT] [--catalog-file PATH]` | executor instruction skills |
| `context-guard [--enabled bool]` | source-bound requirement retrieval |
| `runtime-improvement [--enabled bool] [--auto-deploy bool] [--interval-seconds INT]` | bounded runtime cycle controls |
| `github-workflow [--auto-pull bool] [--auto-commit bool] [--auto-push bool] [--commit-message-template TEXT] [--branch-strategy current\|new_branch]` | GitHub automatic git operations |
| `auto-milestones [--enabled bool]` | local milestone drafts |
| `auto-goals [status\|enable\|disable\|replenish]` | automatic project goals |

---

### `urace config show-all`

Show complete configuration: controls, executor, exchange, fleet.

---

### `urace watch [action]`

Observe runtime improvement cycles and deployment evidence.

| Action | Description |
|--------|-------------|
| (default) | runtime improvement view |
| `report` | improvement report view |
| `guard` | regression guard view |
| `dashboard` | dashboard view |
| `events [--follow\|-f] [--limit 20]` | stream lifecycle events |

| Flag | Default | Description |
|------|---------|-------------|
| `--follow` / `-f` | `False` | follow/tail live events |
| `--limit INT` | `20` | max events |
| `--report` | `False` | compat alias for `watch report` |
| `--guard` | `False` | compat alias for `watch guard` |
| `--dashboard` | `False` | compat alias for `watch dashboard` |
| `--format json\|xml` | `None` | output format |

---

### `urace status [subject]`

Read-only operational views. No args = runtime check.

| Subject | Equivalent to | Description |
|---------|---------------|-------------|
| (none) | `urace check` | runtime inspection surface |
| `runtime` | `urace check` | runtime status |
| `improvements` | `urace watch dashboard` | improvement activity |
| `vitals [--since] [--until] [--limit] [--fail-on]` | `urace vitals` | health vitals |
| `executors` | `urace executor status` | executor status |
| `resources [--product] [--all-products] [--executor codex\|claude\|all] [--scope trial\|epoch\|lifetime]` | `urace resource status` | resource usage |
| `products` | `urace product list` | registered products |
| `fleet` | `urace fleet status` | fleet status |
| `data` | `urace data status` | data sources |
| `quality [--scope]` | `urace quality` | quality deltas |
| `compliance [--domain] [--history]` | `urace compliance` | compliance posture |
| `milestones [--scope]` | `urace milestone` | milestone progress |
| `blockers [--resolved] [--scope]` | `urace blocker list` | active blockers |
| `integrity [--type] [--severity] [--resolved]` | `urace integrity-signal list` | integrity signals |
| `onboarding` | `urace onboard status` | onboard phase |
| `configuration` | `urace configuration` | configuration |
| `inbox [--kind] [--status] [--limit]` | `urace inbox list` | pending inputs |
| `goals [--status] [--limit]` | `urace goal list` | goals |
| `evaluation` | `urace evaluation show` | evaluation config |
| `value` | value evidence/unknowns | project value status |
| `scores` | spec workflow scores | workflow score deltas |

---

### `urace product action [name]`

Manage products, isolated work, value evidence and improvement controls.

| Action | Flags | Description |
|--------|-------|-------------|
| `list` | — | list all registered products |
| `status [name]` | — | status for one or all products |
| `register name` | `[--state-path PATH] [--product-files FILES...] [--intent-purpose TEXT] [--github OWNER/REPO] [--clone-to PATH] [--type TYPE...] [--reason TEXT]` | register a product |
| `switch name` | `[--reason TEXT]` | switch active product |
| `deactivate name` | `[--reason TEXT]` | deactivate a product |
| `activate name` | `[--reason TEXT]` | activate a product |
| `remove name` | `[--force] [--reason TEXT]` | remove a product |
| `enable name` | `[--reason TEXT]` | compat alias: enable improvements |
| `disable name` | `[--reason TEXT]` | compat alias: disable improvements |
| `git name [git_args...]` | — | git operations on product clone |
| `create description` | `[--name TEXT]` | bootstrap product from description |
| `work init\|run\|status\|clarify\|stop` | see below | isolated executable product work |
| `value propose\|list\|rank\|define\|observe\|evidence\|experiment` | `[--id ID] [--data JSON]` | project value evidence |
| `improvements list\|enable\|disable [product_id]` | `[--all-products]` | improvement worker controls |

**`product work` flags:**

| Flag | Default | Description |
|------|---------|-------------|
| `--project TEXT` | required | project identifier |
| `--template navigation\|failover\|recovery\|receipts\|requirements_change\|interruption` | `"navigation"` | work template (init only) |
| `--executor auto\|codex\|claude` | `"auto"` | executor selection |
| `--execution-mode auto\|lightweight\|managed` | `"auto"` | execution mode |
| `--max-seconds INT` | `480` | max execution seconds |
| `--run-id TEXT` | `None` | explicit run ID |
| `--adaptive true\|false` | `"true"` | adaptive execution |
| `--requirement-id ID` | required (clarify only) | requirement to clarify |
| `--answer TEXT` | required (clarify only) | clarification answer |

---

### `urace crypto action`

Local wallet and signing primitives. Gas-free; no on-chain broadcast.

**`crypto wallet` actions:**

| Action | Flags | Description |
|--------|-------|-------------|
| `init` | `[--wallet-dir PATH] [--overwrite]` | generate new secp256k1 keypair |
| `show` | `[--wallet-dir PATH]` | show public address (never private key) |
| `sign <payload>` | `[--wallet-dir PATH]` | sign payload with wallet private key |
| `rotate` | `[--backup-dir PATH] [--wallet-dir PATH]` | rotate keypair with chain-of-custody signature |

---

### `urace security audit`

Security posture audit: wallet, consensus, compliance, circuit breaker, GitHub release integrity.

| Flag | Default | Description |
|------|---------|-------------|
| `--no-network` | `False` | skip GitHub release check (offline mode) |
| `--format json\|xml` | `None` | output format |

---

### `urace qualification action`

Qualification audit: replay and verify past evidence/decision pairs.

| Action | Flags | Description |
|--------|-------|-------------|
| `replay` | `--evidence-id ID --mode estimate\|full` | replay qualification; verify evidence integrity |
| `list` | `[--kind TEXT] [--limit 20]` | list evidence records eligible for replay |

**`replay` modes:**
- `estimate` (default): heuristic score
- `full`: use stored evaluation_system weights to detect criteria drift

---

### `urace source action [id]`

Unified external source management. `add --kind <kind>` connects anything external; other actions manage existing sources.

**Add verbs:**

```bash
urace source add mydb     --kind file      --connect ./data.json
urace source add metrics  --kind csv       --connect ./metrics.csv --direction read
urace source add feed     --kind json      --connect ./feed.json
urace source add db       --kind sqlite    --connect ./app.db
urace source add svc      --kind api       --connect https://api.example.com/data
urace source add myrepo   --kind connector --location https://github.com/org/repo
urace source add claude   --kind executor  --command claude-code --adapter claude-cli
urace source add coverage --kind metric    --metric-source mydb --metric-path $.coverage
urace source add pass-rate --kind vital   --numerator passed_tests --denominator total_tests
urace source add          --kind github    --repo owner/repo
urace source add product-id --kind product
urace source add peer-address --kind peer
```

**`add` flags (kind-specific):**

| Flag | Kinds | Description |
|------|-------|-------------|
| `--kind` | all | required: file\|csv\|json\|sqlite\|api\|connector\|executor\|metric\|vital\|github\|product\|peer |
| `--connect DSN` | file/csv/json/sqlite/api | connection string or file path |
| `--type TYPE` | data kinds | adapter type override |
| `--direction read\|write\|both` | data/metric | data flow direction (default: read) |
| `--auto true\|false` | data kinds | auto-sync on change (default: true) |
| `--location URL` | connector | source URL |
| `--visibility public\|private` | connector | visibility (default: private) |
| `--credential-env ENV` | connector | env var holding credential |
| `--repo owner/repo` | github | GitHub repository |
| `--token-env ENV` | github | env var for token (default: URACE_GITHUB_TOKEN) |
| `--command PATH` | executor | executor binary path |
| `--adapter TYPE` | executor | codex-cli\|claude-cli |
| `--max-calls-24h N` | executor | daily call ceiling |
| `--max-calls-30d N` | executor | monthly call ceiling |
| `--metric-source NAME` | metric | data source providing metric |
| `--metric-path PATH` | metric | JSON path to metric value |
| `--metric-target FLOAT` | metric | target value |
| `--numerator FIELD` | vital | numerator field name |
| `--denominator FIELD` | vital | denominator field name |

**Management actions:**

| Action | Description |
|--------|-------------|
| `list` | list connector sources |
| `status` | health of all data source connections |
| `enable id` | enable a source |
| `disable id` | disable a source |
| `remove id` | remove a source |
| `sync name` | pull evidence from a data source |
| `inspect name` | inspect a data source |

| Flag | Default | Description |
|------|---------|-------------|
| `--format json\|xml` | `None` | output format |

---

### `urace metric action [name]`

| Action | Description |
|--------|-------------|
| `list` | list all metrics |
| `remove name` | remove a metric |

---

### `urace vital action [name]`

| Action | Description |
|--------|-------------|
| `list` | list all vitals |
| `remove name` | remove a vital |

---

### `urace peer-review action`

| Action | Description |
|--------|-------------|
| `list` | list quarantined peer artifacts |
| `evaluate <bundle_id>` | evaluate for safety |
| `promote <bundle_id>` | promote into improvement workflow |

---

### `urace similarity`

Score peer features by TF-IDF intent similarity and collaborative adoption.

| Flag | Default | Description |
|------|---------|-------------|
| `--max-peer-age SECONDS` | `86400` | exclude peers older than N seconds |
| `--timeout SECONDS` | `5.0` | partial results timeout |
| `--min-score FLOAT` | `0.0` | omit results below score |

---

### `urace add-source id kind location`

Queue an external metric or Evidence connector (top-level shorthand).

| Flag | Default | Description |
|------|---------|-------------|
| `id` | required | source ID |
| `kind` | required | connector kind |
| `location` | required | URL/path |
| `--visibility public\|private` | `"private"` | visibility |
| `--credential-env ENV_VAR` | `None` | env var for credential |

---

### `urace add-metric name`

Queue a metric mapping onto a connector (top-level shorthand).

| Flag | Default | Description |
|------|---------|-------------|
| `name` | required | metric name |
| `--source ID` | required | connector source ID |
| `--path TEXT` | required | field path |
| `--direction nondecreasing\|nonincreasing` | `"nondecreasing"` | trend direction |
| `--target FLOAT` | `None` | target value |

---

### `urace add-vital name`

Queue a vital definition (top-level shorthand).

| Flag | Default | Description |
|------|---------|-------------|
| `name` | required | vital name |
| `--numerator ID` | required | metric ID |
| `--denominator ID` | `None` | metric ID (for ratio) |
| `--window TEXT` | `"current"` | time window |
| `--description TEXT` | `""` | description |

---

### `urace declare` (deprecated)

Deprecated alias for `urace add`. Prints deprecation warning and re-dispatches.
Supported sub-actions: `context goal source metric vital`

---

### `urace help [operation...]`

Show operation catalog or contextual help without an Executor call.

---

## Appendix: Protocol Constants

| Constant | Value | Location |
|----------|-------|----------|
| `PROTOCOL_VERSION` | `2` | `peer_exchange.py` |
| `SCHEMA` (exchange) | `"urace-exchange-v2"` | `peer_exchange.py` |
| `RPC_SCHEMA` | `"urace-rpc-v1"` | `_daemon.py` |
| `RPC_TCP_HOST` | `"127.0.0.1"` | `_daemon.py` |
| `RPC_TCP_PORT` | `7474` | `_daemon.py` |
| `LIMIT` (artifact inline) | `524288` (512 KB) | `peer_exchange.py` |
| `ARTIFACT_INLINE_LIMIT` | `65536` (64 KB) | `peer_exchange.py` |
| `ARTIFACT_STORE_LIMIT` | `104857600` (100 MB) | `peer_exchange.py` |
| `P2P default port` | `7301` | `_daemon.py` serve thread |
| `A2A default port` | `8765` | `cli_parser.py` |
| Tunnel provider (zero-install) | `nokey@localhost.run` | `tunnel_server.py` |
| Tunnel provider (optional) | `cloudflared` | `tunnel_install.py` |

---

## Appendix: CRYPTO_PENDING Features

The following features are implemented but not connected to any blockchain network. They activate when `exchange settings set --crypto-network <id>` is configured:

| Feature | Activation |
|---------|-----------|
| `token_settlement` | mainnet EVM settlement — requires `rpc_provider_url` + `erc20_contract` + `chain_id` |
| `cross_chain_transfer` | ETH/SOL bridge — gas fee aware; future feature |
| `nft-mint` | NFT attestation — stub, requires bridge activation |
| `on-ramp` / `off-ramp` | Crypto on/off ramp — stub, requires bridge activation |
