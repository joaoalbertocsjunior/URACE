# URACE

**Universal Recursive Autonomous Co-Founder Engine**

URACE is an executor-agnostic persistent autonomous product-evolution control plane.

**At its core, URACE is an open-source and editable idea:** a specification and bootstrap architecture for making the autonomous Product lifecycle persistent, evidence-aware, validated, recoverable, and independent of any particular AI or executor.

The idea can be inspected, adapted, extended, and evolved while preserving its core lifecycle invariants. The idea is open and editable; the Product, its accumulated intelligence, and its implementation can remain proprietary.

URACE turns bounded and replaceable AI/executor sessions into a continuous, evidence-aware, validated, and recoverable product-development lifecycle.

It provides product-management-like coordination over goals, constraints, evidence, objectives, validation, and execution outcomes. Its goal is to progressively automate the AI-driven product-development loop while keeping the underlying intelligence and execution replaceable.

> URACE owns the persistent autonomous Product lifecycle; replaceable executors provide the intelligence and execution required to advance it.

## Why URACE?

AI agents can research, reason, plan, code, test, and repair—but individual executions are bounded. Sessions end, context disappears, models change, providers fail, and orchestrators are replaced.

URACE keeps the Product lifecycle persistent while the intelligence underneath remains replaceable.

```text id="a0bk7q"
Product / Market / Users
          │
          ▼
       ┌───────┐
       │ URACE │
       └───┬───┘
           │
     Generic Executor
           │
   ┌───────┼────────┐
   ▼       ▼        ▼
 1 AI    Agents   Orchestrator
                     │
                    1..N AI
```

## Not an Executor Replacement

URACE does not replace coding agents, AI models, or orchestrators.

Use your preferred executor for intelligence and execution; URACE provides the persistent autonomous lifecycle around it.

Examples include:

- OpenAI GPT / Codex
- Anthropic Claude / Claude Code
- Google Gemini / Gemini CLI
- OpenHands
- other current or future AI agents, tools, APIs, and orchestrators

The minimum intelligent configuration is:

```text id="i6tsnl"
URACE → 1 capable AI
```

OpenHands, other orchestrators, and multi-agent or multi-model systems are optional.

For practical higher-capability deployments, however, the project recommends bootstrapping and operating URACE with at least one capable execution/orchestration environment, such as OpenHands, together with multiple independent capable AI models—for example GPT, Claude, and Gemini.

This is deployment guidance, not an architectural requirement. URACE itself requires neither an orchestrator nor multiple AIs. Such a configuration gives URACE access to independent reasoning and execution capabilities while preserving its independence from any particular model, provider, executor, or orchestrator.

## Universal by Design

URACE is designed for:

**AI · executor · orchestrator · programming-language · file-format · project-type · platform · repository · version-control · build-system · cloud-provider agnosticism.**

Its lifecycle is based on generic concepts:

```text id="l82yj3"
Product → Evidence → Objective → Operation
       → Executor → Validation → Checkpoint
```

Software is only one possible Product type.

URACE continuously determines what should happen next—and why—from the Product's goals, constraints, evidence, and execution outcomes.

In this role, it can serve as the persistent product-management layer around a Product—including Products built on proprietary intelligence—while delegating bounded intelligence and execution to replaceable external systems.

The URACE idea and lifecycle architecture can remain open and editable while the intelligence accumulated around a particular Product remains its own. Evidence, Product context, objectives, decisions, validation history, implementation, and other Product-specific knowledge may therefore remain proprietary without making proprietary infrastructure a requirement of URACE itself.

## Setup

URACE currently uses `URACE.md` as its bootstrap specification.

`URACE.md` is a prompt-as-bootstrap-file: give it to a capable AI coding executor or orchestrator with access to the target repository.

The executor reads the specification, inspects the environment, and bootstraps the smallest implementation that satisfies URACE's architectural invariants and acceptance tests.

### 1. Get the Bootstrap Specification

Clone or copy this repository and use:

```text id="lky8b2"
URACE.md
```

as the bootstrap prompt.

### 2. Choose an Executor

You only need one capable AI.

For example:

```text id="7k1m2c"
URACE.md
   │
   ├──► Codex
   ├──► Claude Code
   ├──► Gemini CLI
   └──► another capable executor
```

Give the executor access to the repository where URACE should be bootstrapped and instruct it to implement `URACE.md` completely.

For example:

```text id="q01yfh"
Read URACE.md completely.

Treat it as the authoritative bootstrap specification.

Inspect this repository and implement the smallest complete URACE
system satisfying its architecture, invariants, tests and success
criteria.

Do not merely describe the implementation.

Implement it, run the required validation and bootstrap demonstrations,
repair failures, and report the resulting state.
```

### 3. Or Use an Orchestrator

For practical higher-capability deployments, using an orchestrator with multiple independent capable AI models is recommended by the project, although it is not required by URACE.

An orchestrator such as OpenHands may consume `URACE.md` and use its configured AI executors:

```text id="2zqr7l"
             URACE.md
                 │
                 ▼
             OpenHands
                 │
         ┌───────┼───────┐
         ▼       ▼       ▼
       Codex   Claude   Gemini
                 │
                 ▼
           Bootstrap URACE
```

A practical reference configuration therefore combines a capable orchestration/execution environment with multiple independent capable AIs, such as GPT, Claude, and Gemini.

The specific number and choice of models are deployment decisions rather than URACE requirements. Using three independent capable model families is a recommended reference configuration, not a claim that three is a necessary or optimal number.

OpenHands is not required by URACE. It is simply one possible bootstrap and execution environment, and every component underneath URACE remains replaceable.

### 4. Validate the Bootstrap

The executor should not stop after generating files.

`URACE.md` requires the implementation to prove the relevant bootstrap invariants, including:

- operation with a single AI;
- continuity across fresh executor sessions;
- executor replacement;
- persistent state and checkpoints;
- independent validation;
- interruption/restart recovery;
- capacity-loss recovery;
- project/language/artifact agnosticism;
- autonomous multi-cycle evolution.

Only after those requirements pass should the bootstrap be considered complete.

## After Bootstrap

Once bootstrapped, URACE becomes the persistent layer and the relationship reverses:

```text id="k9y9pu"
BOOTSTRAP

URACE.md
    │
    ▼
AI / OpenHands
    │
    ▼
  URACE


NORMAL OPERATION

  URACE
    │
    ▼
Generic Executor
    │
 ┌──┼────────────┐
 ▼  ▼            ▼
AI  Tools   Orchestrator
```

At that point the generated implementation exposes the operational interface defined by the bootstrap, including conceptually:

```text id="3nrzxz"
# Inspect lifecycle state
urace --check

# Assess/plan without Product mutation
urace --plan

# Run persistent autonomous Product evolution
urace --autonomous
```

Exact installation and invocation details are determined by the implementation produced for the host environment.

## Autonomous Evolution

```text id="5b8rgq"
Assess → Select Objective → Execute → Validate
   ↑                                  │
   └──── Checkpoint ← Persist ←───────┘
```

`--autonomous` continuously reassesses the Product and available evidence, delegates justified work, independently validates results, checkpoints accepted increments, and continues across replaceable executor sessions.

Through this lifecycle, URACE is designed to progressively automate the loop between product and market evidence, product decisions, implementation, validation, and subsequent evolution without making any particular AI or execution environment permanent infrastructure.

The lifecycle is intentionally evidence-driven rather than mutation-driven: autonomy does not mean changing the Product indefinitely. When no sufficiently justified next objective exists, URACE may remain idle until new evidence, changed conditions, unmet requirements, or other justified work makes further evolution appropriate.

URACE itself may also be managed as a Product, allowing controlled evolution of URACE through the same policy-governed, evidence-aware, validated, checkpointed, and recoverable lifecycle without introducing privileged self-modification semantics.

Because URACE is itself an open and editable specification, its architecture may also evolve over time. Changes to URACE do not require treating its current structure as immutable; what matters is preserving or deliberately revising the invariants that define the lifecycle.

## The Boundary

```text id="edzcl6"
┌──────────────────────────────┐
│   Product / Market / Users   │
└──────────────┬───────────────┘
               ▼
┌──────────────────────────────┐
│            URACE             │
│                              │
│ State · Evidence · Policy    │
│ Objectives · Validation      │
│ History · Recovery           │
│ Checkpoints · Autonomy       │
└──────────────┬───────────────┘
               ▼
┌──────────────────────────────┐
│  Intelligence / Execution    │
│                              │
│ GPT · Claude · Gemini        │
│ OpenHands · Agents · Tools   │
│ APIs · Future Executors      │
└──────────────────────────────┘
```

Models improve. Agents change. Orchestrators come and go.

The autonomous Product lifecycle remains.

**The idea is open and editable. The intelligence built around each Product can remain its own.**

## License

MIT License — see `LICENSE`.
