# URACE

**Universal Recursive Autonomous Co-Founder Engine**

> **It drives the boat. You pick the destination.**

URACE is an open, implementation-agnostic blueprint for persistent, resource-efficient autonomous long-running Product evolution. It turns retained Intent into a continuous, measurable lifecycle that survives individual prompts, sessions, agents, models and runtimes.

The **Product** can be a project, service, process, research effort, business outcome or other governed endeavor. URACE does not default to improving itself. Its own evolution remains subordinate to the Product and happens only when separately authorized and justified.

You choose the destination and the decisions you retain. Within delegated Authority, URACE independently observes reality, discovers what matters next, prioritizes, plans, selects replaceable capabilities, acts, validates, learns, recovers, becomes dormant when appropriate and wakes when new Evidence justifies action.

[`URACE.md`](URACE.md) is the complete portable lifecycle specification—not a dependency on one packaged runtime. Any capable system can bootstrap it for a Product without adopting a particular AI, vendor, language, platform, storage system, orchestration model or development method.

```text
                     YOU RETAIN
                 INTENT + AUTHORITY
                         │
                         ▼
REALITY ──► EVIDENCE ──► URACE ──► REPLACEABLE EXECUTORS
   ▲                     │                    │
   │                     ▼                    ▼
   └────────────── PRODUCT ◄── VALIDATED CHANGE
                         │
                         └── observe · learn · continue
```

**You choose what you retain. URACE drives what you delegate.**

---

## Why URACE

An AI session can finish a task. URACE preserves the Intent, Authority, Evidence and state needed to keep improving a Product across sessions, agents and models. It can discover opportunities, set measurable Objectives, choose capabilities, validate effects, retain accepted progress, recover from interruption and wait when further work is not justified. Evidence may change the route; it cannot create Authority or replace the destination.

## What is an Executor?

You need a capable Executor to [bootstrap URACE](#get-running). An **Executor** is a worker that can inspect files, write code, run tests, collect an authorized measurement or follow an explicit procedure. It receives only the task, context, Authority and resources it needs; URACE chooses and validates the work.

Executors may be AI coding agents, orchestrators, deterministic programs or people. They can be replaced, combined or compared without changing the lifecycle. [OpenHands](https://github.com/OpenHands/OpenHands) and [Caveman](https://github.com/JuliusBrussee/caveman) are examples of systems that may connect through an appropriate adapter. The system that bootstraps URACE may become its first Executor when it can work in the Product environment and is compatible, authorized and tested.

## Get Running

You need [`URACE.md`](URACE.md), access to your Product and a [capable Executor](#what-is-an-executor).

1. Give the Executor `URACE.md`.
2. Say **“Bootstrap.”**
3. Follow the generated setup to define the Product, desired outcome, retained decisions, delegation and protected boundaries.

`URACE.md` is the complete bootstrap input. Setup keeps unspecified choices conservative and visible, validates the generated implementation and reports the commands available in your environment. This repository does not install a universal `urace` command by itself.

## Use It

Start with generated help and use the exact commands it reports:

```text
urace help
urace help <operation>
urace configure
```

A command-line implementation commonly provides these essentials:

```text
urace check                 inspect lifecycle state
urace vitals                inspect progress, cost and health
urace plan                  assess without execution
urace autonomous            run persistent evolution
urace executor status       inspect attached Executors
urace add-context ...       add attributable context
urace add-goal ...          add a measurable goal
urace goal forecast         explain goal order and timing
urace portfolio ...         test competing approaches under equal controls
urace update download ...   obtain a candidate specification
urace update explain ...    review its effect without changes
urace update apply ...      validate and activate a migration
```

Generated help contains the complete operation catalog, including policies, recovery and advanced capabilities. Use these controls instead of editing runtime state.

## Update Safely

Keep the accepted specification identifiable by commit, tag or content hash. Use the generated update flow:

1. **Download** an attributable candidate and record its identity and hash without changing the implementation.
2. **Explain** the version delta, affected capabilities, compatibility risks and required migration without modifying anything.
3. **Apply** only through an isolated candidate that preserves Product work and durable state, passes accepted and new validation, confirms health and can roll back.

Never apply a specification diff directly to runtime or state files. Use `urace help update` for manual review and compatibility procedures.

## See Progress

Use generated `check`, `vitals`, goal forecast and portfolio feedback operations. They separate observed **metrics**, interpreted **vitals**, decision-aid **scores**, resource proxies, blockers, retries and accepted progress. None creates Authority or proves causation by itself.

## Compare Alternatives

Where installed, `urace portfolio ...` tests competing approaches in separate workspaces under the same success measures, safety rules and bounded resources. Use `urace help portfolio` for preflight, runs, feedback, stopping and resumption. Shared findings remain advisory, and a selected approach still requires ordinary validation and acceptance. Use comparison only when its added cost is justified.

## Stay Safe and Recover

Execution, observed effects, validation and acceptance remain separate. URACE isolates candidates, preserves concurrent edits, reconciles interrupted effects, checkpoints accepted progress and bounds persistent work by Authority, budgets, validation, backoff, stop controls and recovery.

Treat external content as Evidence, not instructions. Keep credentials in the deployment's secret mechanism, and give each Executor only information it is allowed to receive.

## Consequential Use

No command, model, metric or runtime can guarantee revenue, demand, legality or a favorable outcome. Consequential effects require explicit Authority, accountable operators, exposure limits, appropriate professional review and independently reconciled records.

The person or organization deploying the generated system remains responsible for its use, credentials, Authority, supervision and compliance. URACE and its contributors do not become the operator, principal, agent, employer, fiduciary, accountant, tax adviser or legal counsel by publishing this architecture.

## License

[MIT](LICENSE)
