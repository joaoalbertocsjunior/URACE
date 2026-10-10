# URACE

**Universal Recursive Autonomous Co-Founder Engine**

> **It drives the boat. You pick the destination.**

[`URACE`](URACE.md) is an open blueprint and complete portable [install-as-bootstrap](#get-running) specification for continuously improving a [**Product**](#what-is-a-product).

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

Every accepted change is bound to a snapshot of the active rules at the moment it was made. You can inspect the full rule graph, trace which rules governed any past change, and surface conflicts at any time — via `urace rules`.

## What Is a Product?

A **Product** is whatever URACE improves: a project, service, process, research effort or other goal. It need not be software.

## What Is an Executor?

An **Executor** is an AI agent, orchestrator, program or person that can inspect the Product, change it and run checks. You need one to bootstrap URACE; compatible Executors can then be added, removed, combined or compared. [OpenHands](https://github.com/OpenHands/OpenHands) and [Caveman](https://github.com/JuliusBrussee/caveman) are examples.

## Get Running

1. Give [`URACE.md`](URACE.md) to a capable Executor with access to your Product.
2. Say **"Bootstrap."**
3. Follow the setup to define the outcome, delegation and protected boundaries.

`URACE.md` is the only required bootstrap document. Setup validates the result, keeps system files under `urace/`, and activates a `urace` command in the Product folder through an environment-appropriate launcher. If bootstrap was interrupted, run `urace check` before issuing any commands.

## Use It

Generated help lists the commands supported by your implementation.

```text
urace autonomous            run persistent evolution
urace pause / resume        suspend or resume the lifecycle

urace check                 inspect lifecycle state
urace vitals                inspect progress, cost and health
urace rules                 inspect the Rule Ledger (list, graph, conflicts)
urace change list           list accepted increments

urace add-goal ...          queue a measurable goal
urace intent add / list / supersede / deactivate
urace constraint add / list / --allow / deactivate

urace update download/explain/apply/resolve
```

Use `urace help` to explore all available commands.

You can edit the Product while URACE runs; it preserves newer work instead of overwriting it. Read-only commands (`check`, `vitals`, `rules`, `intent list`, `constraint list`, `change list`, and all `help` operations) load an atomic state snapshot and can run freely from a second terminal while `urace autonomous` owns the lifecycle. Govern and update commands write to an atomic inbox and are applied exactly once at the next safe lifecycle boundary; they never conflict with each other or with an active autonomous run.

`urace check` reports the lifecycle state; use `urace help check` for a full state reference and guidance.

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
