# URACE

**Universal Recursive Autonomous Co-Founder Engine**

> **It drives the boat. You pick the destination.**

[`URACE`](URACE.md) is an open blueprint and complete portable [install-as-bootstrap](#get-running) specification for continuously improving a [**Product**](#what-is-a-product).

Delivered as an open-blueprint rather than traditional code, this project bridges the gap between visionaries and implementers without vendor lock-in. Grounded in innovation, communication, and runtime agnosticism, it relies on the same principles that built the internet.

You set the destination and boundaries. URACE delegates execution to replaceable Executors, validates results, learns and recovers. It changes itself only with your permission.

```text
BEFORE BOOTSTRAP                         AFTER BOOTSTRAP

    URACE.md                         YOU — Select Product(s) + Outcomes
        │                              │ RETAINS INTENT + AUTHORITY
        ▼                              ▼
    EXECUTOR ── builds ───────► URACE SYSTEM ◄── RESULTS + EVIDENCE ◄── PRODUCTS
                                    │    │  ProductRegistry                  ▲
                                    │    └─ Fleet: run all products          │ accepted changes
               assigns bounded work │                                        │
                                    ▼                                        │
                                EXECUTORS ── execute and return ──► URACE VALIDATES
```

## Why URACE

URACE automates replaceable Executors to improve the Product continuously, measurably and recoverably. It adapts its plans without changing what you control.

Every accepted change is bound to a snapshot of the active rules at the moment it was made. You can inspect the full rule graph, trace which rules governed any past change, and surface conflicts at any time — via `urace /rules list`.

## What Is a Product?

A **Product** is whatever URACE improves: a project, service, process, research effort or other goal. It need not be software. URACE can manage multiple Products through a Product Registry — register each with its own state path, switch the active one with `urace product switch`, or run all in parallel with `urace fleet run`.

## What Is an Executor?

An **Executor** is any capable runtime URACE can delegate to: an LLM, AI agent, API, CLI, script, deterministic tool, or human-operated system — anything that can inspect the Product, produce changes, run checks, and return results. URACE validates independently and decides what is accepted. You need one to bootstrap; compatible Executors can then be added, removed, combined or compared. [OpenHands](https://github.com/OpenHands/OpenHands) and [Caveman](https://github.com/JuliusBrussee/caveman) are examples.

## Get Running

1. Give [`URACE.md`](URACE.md) to a capable Executor.
2. Say **"Bootstrap."**
3. Run `urace /onboard confirm` to activate the lifecycle. Use `urace /help onboard` for a step-by-step guide.
4. Follow the setup to define the outcome, delegation and protected boundaries.

`URACE.md` is the only required bootstrap document. Setup keeps system files under `urace/` and activates a `urace` command through an environment-appropriate launcher. Product files can be at any path — URACE is agnostic to folder structure. If bootstrap was interrupted, run `urace /check` before issuing any commands.

## Use It

```text
urace /auto             run persistent evolution
urace /pause or /resume suspend or resume the lifecycle
urace "<freeform-text>" describe any task, goal, intent, or constraint in plain language
urace /help             explore commands and reference
urace /update           guided update sequence
urace fleet sync        propagate a product's broadcast to its dependents
urace add evidence --kind test-pass --summary "CI green"
```

**`/command`** — instant, no Executor overhead, always works: `urace /check`, `urace /vitals`, `urace /rules list`, `urace /goal list`.

**Plain text** — `urace "improve onboarding flow"`. A universal router: one prompt resolves to one or more commands dispatched in the correct order. Contradictory sub-intents surface as conflicts before dispatch.

`urace /help` lists all commands; `urace /help <command>` gives per-command reference. The full command list with category and purpose is in the [Command Reference](URACE.md#command-reference). Shared options including `--dry-run`, `--json`, `--format json|xml`, `--scope` and `--verbose` are defined in [Standard Command Options](URACE.md#62k-standard-command-options).

## Update Safely

Run `urace /update` for the guided update sequence. Pass `--hash <sha256>` to verify the downloaded spec; `--verify` to re-verify the stored candidate before applying. Options `--opt-in-constructs` and `@bundle-name` scope the update.

## See Progress

Inspect metrics, vitals, state, and resource usage with `urace /check`, `urace /vitals`, `urace /change list`, and `urace /resource status`.

## Inspect and Modify Context

URACE automatically and gradually compresses its full lifecycle state — objectives, evidence, decisions, operations, and all user-added context — as it grows, to maintain reliability over long runs. It decompresses gradually too, restoring full human-readable form for inspection or modification.

```text
urace /compact      gradually compress lifecycle state for reliability
urace /decompact    gradually restore full human-readable form
urace /amend <id>   correct a record in place without full decompaction
urace /crc show     inspect the current full-context Cognitive Resume
```


## Connect Data Sources

Register any database, file, or cloud store once; URACE automatically pulls evidence from it each cycle and pushes records back after cycle completion. `--direction read|write|both` controls flow. Credentials stored as pointers only — env var, vault path, or k8s secret ref; never raw values in state.

```text
urace data add mydb --type postgres --connect "postgresql://host/db" --direction both
urace data list|inspect|update|remove
urace data sync mydb   # on-demand PULL override
urace data push mydb   # on-demand PUSH override
```

Adapters: SQL (postgres, mysql, sqlite, bigquery, snowflake), NoSQL (mongodb, redis, dynamodb, firestore), graph (neo4j, arangodb), time-series (influxdb, timescaledb), search (elasticsearch), files (csv, excel, parquet, json, xml, yaml), cloud (s3, gcs, azure-blob). Extensible via `Config.data.registered_adapters`. Full contract: [DataSourceRegistry](URACE.md#62x-datasourceregistry).

## Machine Interface

URACE exposes a machine-readable interface for automation and external tools. Every command supports `--json` output. For XML consumers, use `--format xml` (or `--format json` explicitly) — available as a top-level flag on any command:

```text
urace --format xml compact decision_records --status
urace --format xml crc show
urace --format json inspect                    # same as --json
```

`--format xml` forces JSON-mode output from the handler then converts to elements-only XML with a `<urace>` root. Non-JSON output (error messages, human text) passes through unchanged. Structured commands can also be issued via `urace api`:

```text
urace api call --command <command> [--params <json>]
urace api batch --input-json <path|->
urace api watch [--follow]
urace api version
```

Feedback and lifecycle events can be submitted in machine-readable form via `urace feedback submit --input-json`. The full I/O contract is defined in [External Interface Protocol](URACE.md#62w-external-interface-protocol).

## Reuse URACE Building Blocks The Way You Want

Take any of URACE's building blocks — patterns, mechanisms, schemas, protocols, and contracts — for your own project, no lifecycle required. Describe what you're building and URACE picks matching blocks automatically. See the full [Derivation Framework and bundle catalog](URACE.md#62j-derivation-framework) for available building blocks.

```
urace derive "resilient event log with compaction"
urace derive "quality tracking with regression gates" --kind mechanism,schema
```

Run `urace derive` with no arguments to browse. Use `--verify` to re-verify all saved manifest hashes; `--hash <sha256>` to verify a specific manifest.

## Consequential Use

URACE cannot guarantee revenue, legality or favorable results. Whoever deploys it remains responsible for access, supervision and compliance. Publishing URACE does not make its contributors the operator or a professional adviser. URACE is dedicated to the public domain under [CC0 1.0 Universal](LICENSE).
