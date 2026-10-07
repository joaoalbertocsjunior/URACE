# URACE

**Universal Recursive Autonomous Co-Founder Engine**

> **It drives the boat. You pick the destination.**

URACE is an open, implementation-agnostic blueprint for persistent, resource-efficient autonomous Product evolution. It turns retained Intent into a continuous, measurable lifecycle that survives individual prompts, sessions, agents, models and runtimes.

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

An AI session can complete a task. URACE preserves the Intent, Authority, Evidence and state needed to keep evolving a Product across prompts, sessions, agents and models. Evidence may change the route; it cannot manufacture Authority or silently replace the destination.

Within delegated Authority, URACE can discover and prioritize opportunities, create measurable Objectives, select replaceable Executors, validate effects, checkpoint accepted progress, recover from interruption, accept new goals and context while running, and become dormant when further work is not justified.

Executors may be agentic, orchestrated, deterministic, human-operated, interchangeable, or competing (e.g., [OpenHands](https://github.com/OpenHands/OpenHands) or [Caveman](https://github.com/JuliusBrussee/caveman)) without changing URACE's lifecycle model.

## Get Running

You need:

1. [`URACE.md`](URACE.md);
2. your Product or access to its environment; and
3. a capable execution system that can read the specification and build there.

Give that system **`URACE.md` and your Product context**. This README is not a bootstrap input. A small context note is enough:

```text
Product: <what should evolve>
Desired outcome: <observable result>
Retain: <decisions only I may make>
Delegate: <decisions URACE may make>
Protect: <data, cost, behavior or other boundaries>
Available capabilities: <tools, tests, services or Executors>
Self-evolution: disabled | necessary-only | continuous
External Evidence: disabled | provided-only | discover-public-and-use-provided
```

Ask the system to bootstrap and validate `URACE.md` completely. It should report what it generated, the durable-state boundary, attached capabilities, validation results, unresolved limits and exact commands for help, inspection, bounded operation and persistent operation. Downloading this repository alone does not install a universal `urace` command.

## Use It

Start with the generated help surface:

```text
urace help
urace help <operation>
```

Use the exact generated commands. A command-line implementation commonly provides equivalents of:

```text
urace check                 inspect lifecycle state
urace vitals                inspect progress, cost and health
urace plan                  assess without execution
urace autonomous            run persistent evolution
urace executor status       inspect attached Executors
urace add-context ...       queue attributable context
urace add-goal ...          queue a measurable goal
urace goal forecast         explain goal order and advisory completion ranges
```

Generated help identifies unavailable capabilities, durable controls and safe inspection without an Executor call. Use it for goals, policies, Executors and recovery rather than editing runtime state.

## Update Safely

Keep the accepted specification identifiable by commit, tag or content hash. Obtain the newer `URACE.md` from a trusted source and review the version diff before updating your generated implementation:

```sh
# When both versions are Git commits available locally:
git diff ACCEPTED_COMMIT NEW_COMMIT -- URACE.md

# When comparing two independent files:
git diff --no-index accepted/URACE.md new/URACE.md
```

Give the newer specification and version diff to your bootstrap system as bounded migration input. Ask it to create an isolated, backward-compatible migration candidate; preserve Product work and durable state; check state compatibility; run both accepted and new validation suites; and activate only after health confirmation, with rollback available.

The diff is review input, not a patch for runtime or state files. Use generated help to find the update, self-evolution or re-bootstrap operation. If none exists, bootstrap the newer specification as a candidate and promote it through the same validation and rollback process.

## See Progress

Use generated `check`, `vitals`, goal forecast and portfolio feedback operations. They distinguish observed **metrics**, interpreted **vitals**, decision-aid **scores**, resource proxies, blockers, retry conditions and accepted progress without treating any of them as Authority or proof of causation.

## Compare Alternatives Safely

Where installed, portfolio evolution tests isolated alternatives under one frozen contract and equal bounded resources. Use `help portfolio` for preflight, finite or persistent runs, feedback, stopping and resumption. Shared findings remain advisory; a winner still requires ordinary validation and acceptance. Use this mode only when comparison justifies its extra cost.

## Stay Safe and Recover

Execution, observed effects, validation and acceptance are separate events. Candidates are prepared away from stable artifacts; concurrent edits are preserved; interrupted effects are reconciled or remain explicitly uncertain; accepted progress is checkpointed; and persistent operation remains bounded by Authority, budgets, isolation, validation, backoff, stop controls and recovery.

External content is Evidence rather than executable instruction. Keep credentials in the deployment's secret mechanism. Choose Executors and services for both what they can do and what information they may legitimately receive.

## Consequential Use

No command, model, metric or runtime can guarantee revenue, demand, legality or a favorable outcome. Consequential effects require explicit Authority, accountable operators, exposure limits, appropriate professional review and independently reconciled records.

The person or organization deploying the generated system remains responsible for its use, credentials, Authority, supervision and compliance. URACE and its contributors do not become the operator, principal, agent, employer, fiduciary, accountant, tax adviser or legal counsel by publishing this architecture.

## License

[MIT](LICENSE)
