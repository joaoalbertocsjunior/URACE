# URACE

**Universal Recursive Autonomous Co-Founder Engine**

> **It drives the boat. You pick the destination.**

[`URACE`](URACE.md) is an open blueprint and complete portable [install-as-bootstrap](#get-running) specification for continuously improving a [**Product**](#what-is-a-product).

Delivered as an open-blueprint rather than traditional code, this project bridges the gap between visionaries and implementers without vendor lock-in. Grounded in innovation, communication, and runtime agnosticism, it relies on the same principles that built the internet.

You set the destination and boundaries. URACE delegates execution to replaceable Executors, validates results, learns and recovers. It changes itself only with your permission.

```text
BEFORE BOOTSTRAP                         AFTER BOOTSTRAP

YOU + URACE.md + PRODUCT                 YOU — choose the Product and outcome
           │                              │ RETAINS INTENT + AUTHORITY
           ▼                              ▼
       EXECUTOR ── builds ───────► URACE SYSTEM ◄── RESULTS + EVIDENCE ◄── PRODUCT
                                      │                                      ▲
                                      │ assigns bounded work                 │ accepted changes
                                      ▼                                      │
                                  EXECUTORS ── execute and return ──► URACE VALIDATES
```

## Why URACE

URACE automates replaceable Executors to improve the Product continuously, measurably and recoverably. It adapts its plans without changing what you control.

Every accepted change is bound to a snapshot of the active rules at the moment it was made. You can inspect the full rule graph, trace which rules governed any past change, and surface conflicts at any time — via `urace /rules`.

## What Is a Product?

A **Product** is whatever URACE improves: a project, service, process, research effort or other goal. It need not be software.

## What Is an Executor?

An **Executor** is an AI agent, orchestrator, program or person that can inspect the Product, change it and run checks. You need one to bootstrap URACE; compatible Executors can then be added, removed, combined or compared. [OpenHands](https://github.com/OpenHands/OpenHands) and [Caveman](https://github.com/JuliusBrussee/caveman) are examples.

## Get Running

1. Give [`URACE.md`](URACE.md) to a capable Executor with access to your Product.
2. Say **"Bootstrap."**
3. Follow the setup to define the outcome, delegation and protected boundaries.

`URACE.md` is the only required bootstrap document. Setup validates the result, keeps system files under `urace/`, and activates a `urace` command in the Product folder through an environment-appropriate launcher. If bootstrap was interrupted, run `urace /check` before issuing any commands.

## Use It

```text
urace /auto             run persistent evolution
urace /pause or /resume suspend or resume the lifecycle
urace <freeform-text>   describe goals, intents, and constraints in plain language
urace /help             explore commands and reference
urace /update           guided update sequence
```

Run `urace /auto` in one terminal. From a second terminal, send anything.

**`/command`** — instant, no Executor overhead, always works: `urace /check`, `urace /vitals`, `urace /rules list`, `urace /goal list`.

**Plain text** — the Executor maps your input to goals, intents, constraints, and commands — each confirmed individually. Contradictory inputs surface as alternatives.

`urace /help` lists all commands. `urace /help <command>` gives per-command reference. Options shared across commands (`--json`, `--scope`, `--verbose`, and others) are defined in [Standard Command Options](URACE.md#62k-standard-command-options).

## Update Safely

Run `urace /update` — it guides you through the full update sequence safely. Pass `--opt-in-patterns AP8,AP14` to limit which architectural patterns the update applies to. Use `urace /help update` for details.

## See Progress

URACE reports observed **metrics**, system-health **vitals** and decision **scores**. Inspect them with `urace /check`, `urace /vitals` and `urace /change list`; use `urace /help` for details.

## Inspect and Modify Context

URACE automatically and gradually compresses its full lifecycle state — objectives, evidence, decisions, operations, and all user-added context — as it grows, to maintain reliability over long runs. It decompresses gradually too, restoring full human-readable form for inspection or modification.

```text
urace /compact      gradually compress lifecycle state for reliability
urace /decompact    gradually restore full human-readable form
urace /amend <id>   correct a record in place without full decompaction
urace /crc show     inspect the current full-context Cognitive Resume
```

Use `urace /help compact` for details.

## Reuse URACE Patterns The Way You Want

Take any of URACE's 25 architectural patterns for your own project — no lifecycle, no commitment. Describe what you're building and URACE picks matching patterns automatically:

```
urace derive "resilient event log with compaction"
```

Add `--suggest` to preview which patterns match before committing. Use `--patterns` to complement or override the suggestions. Run `urace derive` with no arguments to browse the full catalog.

## Consequential Use

URACE cannot guarantee revenue, legality or favorable results. Whoever deploys it remains responsible for access, supervision and compliance. Publishing URACE does not make its contributors the operator or a professional adviser. URACE uses the [MIT License](LICENSE).
