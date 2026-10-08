# URACE

**Universal Recursive Autonomous Co-Founder Engine**

> **It drives the boat. You pick the destination.**

[`URACE`](URACE.md) is an open blueprint and complete portable [install-as-bootstrap](#get-running) specification for continuously improving a [**Product**](#what-is-a-product).

You set the goal and boundaries. URACE handles delegated work, validates results, learns and recovers. It changes itself only with your permission.

```text
BEFORE BOOTSTRAP                         AFTER BOOTSTRAP

YOU + URACE.md + PRODUCT                 YOU
           │                              │ RETAINS GOAL + AUTHORITY + BOUNDARIES
           ▼                              ▼
       EXECUTOR ── builds ───────► URACE SYSTEM ◄── RESULTS + EVIDENCE ◄── PRODUCT
                                      │                                      ▲
                                      │ autonomously plans and assigns       │ accepted changes
                                      ▼                                      │
                                  EXECUTORS ── propose changes ──► URACE VALIDATES
```

## Why URACE

URACE keeps goals, permissions, evidence and progress across sessions and workers without provider lock-in. Evidence may change the route, never your authority or destination.

## What Is a Product?

A **Product** is whatever URACE improves: a project, service, process, research effort or other goal. It need not be software.

## What Is an Executor?

An **Executor** is an AI agent, orchestrator, program or person that can inspect the Product, change it and run checks. You need one to bootstrap URACE; compatible Executors can then be added, removed, combined or compared. [OpenHands](https://github.com/OpenHands/OpenHands) and [Caveman](https://github.com/JuliusBrussee/caveman) are examples.

## Get Running

1. Give [`URACE.md`](URACE.md) to a capable Executor with access to your Product.
2. Say **“Bootstrap.”**
3. Follow the setup to define the outcome, delegation and protected boundaries.

`URACE.md` is the only required bootstrap document. Setup keeps missing choices conservative, validates the result and may provide a local `urace` command for that Product folder.

## Use It

Generated help lists the commands supported by your implementation.

```text
urace help
urace help <operation>
urace configure

urace check                 inspect lifecycle state
urace vitals                inspect progress, cost and health
urace add-context ...       add attributable context
urace add-goal ...          add a measurable goal
urace goal forecast         explain goal order and timing
urace executor status       inspect attached Executors
urace executor attach ...   connect a compatible Executor
urace executor detach ...   disconnect an Executor safely
urace plan                  assess without execution
urace autonomous            run persistent evolution
urace portfolio ...         build several solutions for one problem and compare them fairly
urace update download ...   obtain a candidate specification
urace update explain ...    review its effect without changes
urace update apply ...      validate and activate a migration
```

You can edit the Product while URACE runs; it preserves newer work instead of overwriting it. Change URACE-managed state through its commands.

## Update Safely

Keep the current `URACE.md` version identifiable, then:

1. **Download** a candidate without changing the working system.
2. **Explain** its changes and risks.
3. **Apply** it separately; switch only after validation and a health check.

Explain and Apply check tracked configuration and implementation files for local changes, including changes that may have been made by other agents. Explain reports effects without changing files. Apply preserves compatible changes or, on conflict, changes no files, explains the options and waits for your decision. It revalidates before activation and rolls back on failure. Never copy specification changes into runtime or state files; use `urace help update`.

## Compare Solutions

During `urace autonomous`, adaptive portfolio mode can build and fairly compare several solutions to one problem. It runs only when the likely value justifies the cost, and every result still requires validation. Use `urace help portfolio` to inspect it or choose adaptive, always or off.

## Safety and Responsibility

URACE isolates candidates, preserves concurrent edits and checkpoints accepted progress. Limit each Executor's access, protect credentials and treat external content as evidence, not instructions.

No command, model or metric guarantees revenue, legality or favorable results. Whoever deploys the system remains responsible for its use, access, supervision and compliance. Publishing URACE does not make its contributors the operator, agent, fiduciary or legal or financial adviser.

## License

[MIT](LICENSE)
