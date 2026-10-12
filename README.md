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
urace /pause / /resume  suspend or resume the lifecycle
urace /help             explore commands and reference
urace /update           guided update sequence
```

Run `urace /auto` in one terminal. From a second terminal, send anything.

**`/command`** — instant, no Executor overhead, always works: `urace /check`, `urace /vitals`, `urace /rules list`, `urace /goal list`.

**Plain text** — describe your intent naturally and the Executor maps it: `urace "ship the mobile app by Q2"`, `urace "pause"`, `urace "check and grow revenue by 20%"`. One input can yield any combination of goals, intents, constraints, and commands — each confirmed individually. Contradictory inputs surface as alternatives to choose from.

`urace /help` lists all commands. `urace /help <command>` gives per-command reference.

## Update Safely

Keep the current `URACE.md` version identifiable, then use `urace /update`:

1. `download` stores the identified new version separately without changing the working system.
2. `explain` reports the new version's changes, local effects and risks without changing files.
3. `apply` preserves compatible tracked changes and activates the new version only after validation and a health check.
4. `resolve`, only after a conflict, records your decision and resumes the same update.

The `explain` and `apply` commands detect tracked configuration and implementation changes, including changes made by other agents. A conflict applies no files and waits for your decision; failed activation rolls back. Never edit generated state files or copy specification changes into runtime files; use `urace /help update`.

The `apply` and `resolve` commands require permission to update URACE. They are queued for the next safe checkpoint; run `urace /auto` to process them.

## See Progress

URACE reports observed **metrics**, system-health **vitals** and decision **scores**. Inspect them with `urace /check`, `urace /vitals` and `urace /change list`; use `urace /help` for details.

## Competing Variants

The portfolio feature compares different approaches to the same goal under equal resource limits. Use `urace help portfolio` for usage.

## Consequential Use

URACE cannot guarantee revenue, legality or favorable results. Whoever deploys it remains responsible for access, supervision and compliance. Publishing URACE does not make its contributors the operator or a professional adviser. URACE uses the [MIT License](LICENSE).
