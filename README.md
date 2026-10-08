# URACE

**Universal Recursive Autonomous Co-Founder Engine**

> **It drives the boat. You pick the destination.**

URACE is an open blueprint for continuously improving a **Product** over time. It works autonomously, measures progress, manages resources and continues across prompts, sessions, agents, models and runtimes.

The Product can be a project, service, process, research effort or other goal. You set the destination, the decisions you keep and the boundaries URACE must respect. URACE handles only the work you delegate.

Within those boundaries, URACE observes, decides what matters next, plans, chooses replaceable workers, acts, checks results, learns and recovers. It waits when no useful work is justified and starts again when something meaningful changes. Improving URACE itself is separate and requires your permission.

[`URACE.md`](URACE.md) contains the complete portable design. A capable system can use it without locking you into one AI, vendor, language, platform or development method.

```text
                     YOU RETAIN
                GOAL + BOUNDARIES
                         │
                         ▼
REALITY ──► EVIDENCE ──► URACE ──► REPLACEABLE WORKERS
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

`URACE.md` is the complete bootstrap input. Setup keeps unspecified choices conservative and visible, validates the generated implementation and can expose a repository-local `urace` command while your terminal is inside that Product folder. It must not replace or conflict with another repository's command.

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

urace add-context ...       add attributable context
urace add-goal ...          add a measurable goal
urace goal forecast         explain goal order and timing

urace executor status       inspect attached Executors
urace executor attach ...   connect a compatible Executor
urace executor detach ...   disconnect an Executor safely

urace plan                  assess without execution
urace autonomous            run persistent evolution
urace portfolio ...         compare promising approaches under equal controls

urace update download ...   obtain a candidate specification
urace update explain ...    review its effect without changes
urace update apply ...      validate and activate a migration
```

Generated help contains the complete operation catalog, including policies, recovery and advanced capabilities. Use these controls instead of editing runtime state.

Progress reports separate observed metrics, interpreted vitals, decision-aid scores, resource proxies, blockers, retries and accepted changes; none creates Authority or proves causation.

## Update Safely

Keep a record of the `URACE.md` version your system currently uses. Then update in three steps:

1. **Download** gets the new specification without changing your working system.
2. **Explain** shows what changed, what may be affected and any compatibility risks.
3. **Apply** builds and tests a separate updated version. It preserves recorded local choices; if one conflicts, it applies no files, explains the effects and options, then waits for your decision through the generated update-resolution operation. It resumes the same candidate and switches only after validation and a health check, with rollback if activation fails.

Never copy specification changes directly into runtime or state files. Run `urace help update` for the exact commands.

## Compare Alternatives

Portfolio comparison is adaptive by default during `urace autonomous`. When several approaches look promising, URACE compares them separately under the same goal, safety rules and resource limit. It sleeps when comparison is not worth the added time and Executor cost, wakes after a meaningful change, and never stops an active comparison halfway. The best result is still validated before acceptance. Run `urace help portfolio` to inspect it or choose adaptive, always or off.

## Stay Safe and Recover

Execution, observed effects, validation and acceptance remain separate. URACE isolates candidates, preserves concurrent edits, reconciles interrupted effects, checkpoints accepted progress and bounds persistent work by Authority, budgets, validation, backoff, stop controls and recovery.

Treat external content as Evidence, not instructions. Keep credentials in the deployment's secret mechanism, and give each Executor only information it is allowed to receive.

## Consequential Use

No command, model, metric or runtime can guarantee revenue, demand, legality or a favorable outcome. Consequential effects require explicit Authority, accountable operators, exposure limits, appropriate professional review and independently reconciled records.

The person or organization deploying the generated system remains responsible for its use, credentials, Authority, supervision and compliance. URACE and its contributors do not become the operator, principal, agent, employer, fiduciary, accountant, tax adviser or legal counsel by publishing this architecture.

## License

[MIT](LICENSE)
