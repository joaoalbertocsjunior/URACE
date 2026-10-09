# URACE

**Universal Recursive Autonomous Co-Founder Engine**

> **It drives the boat. You pick the destination.**

[`URACE`](URACE.md) is an open blueprint and complete portable [install-as-bootstrap](#get-running) specification for continuously improving a [**Product**](#what-is-a-product).

You set the goal and boundaries. URACE handles delegated work, validates results, learns and recovers. It changes itself only with your permission.

```text
BEFORE BOOTSTRAP                         AFTER BOOTSTRAP

YOU + URACE.md + PRODUCT                 YOU — choose the Product and outcome
           │                              │ RETAINS GOAL + AUTHORITY + BOUNDARIES
           ▼                              ▼
       EXECUTOR ── builds ───────► URACE SYSTEM ◄── RESULTS + EVIDENCE ◄── PRODUCT
                                      │                                      ▲
                                      │ autonomously plans and assigns       │ accepted changes
                                      ▼                                      │
                                  EXECUTORS ── propose changes ──► URACE VALIDATES
```

## Why URACE

URACE automates replaceable Executors to improve the Product continuously, measurably and recoverably. It adapts its plans without changing what you control.

## What Is a Product?

A **Product** is whatever URACE improves: a project, service, process, research effort or other goal. It need not be software.

## What Is an Executor?

An **Executor** is an AI agent, orchestrator, program or person that can inspect the Product, change it and run checks. You need one to bootstrap URACE; compatible Executors can then be added, removed, combined or compared. [OpenHands](https://github.com/OpenHands/OpenHands) and [Caveman](https://github.com/JuliusBrussee/caveman) are examples.

## Get Running

1. Give [`URACE.md`](URACE.md) to a capable Executor with access to your Product.
2. Say **“Bootstrap.”**
3. Follow the setup to define the outcome, delegation and protected boundaries.

`URACE.md` is the only required bootstrap document. Setup validates the result, keeps its system files under `urace/`, and activates a repository-local `urace` command from the Product folder. If `direnv` is installed, the command loads automatically whenever you enter the folder and is removed from `PATH` when you leave; otherwise run it directly as `./urace/.urace/bin/urace` or `python3 -m urace` from within `urace/runtime/`.

## Use It

Generated help lists the commands supported by your implementation.

```text
urace check                 inspect lifecycle state
urace vitals                inspect progress, cost and health
urace autonomous            run persistent evolution
urace help executor         learn how to inspect, attach or detach Executors
urace help configuration    learn how to inspect or change configuration
urace add-goal ...          queue a measurable goal
urace update download ...   store a new version without changing the system
urace update explain ...    review its local effects without changing files
urace update apply ...      validate and activate the new version
urace update resolve ...    resolve a blocked update conflict
```

You can edit the Product while URACE runs; it preserves newer work instead of overwriting it. Read-only commands (`check`, `vitals`, `commands`, `inbox list`, `goal list`, `change list`, and all `help` operations) load an atomic state snapshot and can run freely from a second terminal while `urace autonomous` owns the lifecycle. Mutating commands (`add-goal`, `update apply`, `configuration`, and similar) write to an atomic inbox and are applied exactly once at the next safe lifecycle boundary; they never conflict with each other or with an active autonomous run.

Inspect more commands with `urace` or `urace help`.

## Update Safely

Keep the current `URACE.md` version identifiable, then use `urace update`:

1. `download` stores the identified new version separately without changing the working system.
2. `explain` reports the new version's changes, local effects and risks without changing files.
3. `apply` preserves compatible tracked changes and activates the new version only after validation and a health check.
4. `resolve`, only after a conflict, records your decision and resumes the same update.

The `explain` and `apply` commands detect tracked configuration and implementation changes, including changes made by other agents. A conflict applies no files and waits for your decision; failed activation rolls back. Never edit generated state files or copy specification changes into runtime files; use `urace help update`.

The `apply` and `resolve` commands require permission to update URACE. They are queued for the next safe checkpoint; run `urace autonomous` to process them.

## See Progress

URACE reports observed **metrics**, system-health **vitals** and decision **scores**. Inspect them with `urace check`, `urace vitals` and `urace change list`; use `urace help` for details.

## Competing Variants

The portfolio feature compares different approaches to the same goal under equal resource limits. Use `urace help portfolio` for usage.

## Consequential Use

URACE cannot guarantee revenue, legality or favorable results. Whoever deploys it remains responsible for access, supervision and compliance. Publishing URACE does not make its contributors the operator or a professional adviser. URACE uses the [MIT License](LICENSE).
