# URACE

**Universal Recursive Autonomous Co-Founder Engine**

URACE is an **executor-agnostic persistent autonomous product-evolution control plane**.

It turns bounded and replaceable AI/executor sessions into a continuous, evidence-aware, validated, and recoverable product-development lifecycle.

> **URACE owns the persistent autonomous Product lifecycle; replaceable executors provide the intelligence and execution required to advance it.**

## Why URACE?

AI agents can research, reason, plan, code, test, and repair—but individual executions are bounded. Sessions end, context disappears, models change, providers fail, and orchestrators are replaced.

URACE keeps the **Product lifecycle persistent while the intelligence underneath remains replaceable**.

```text id="skf27b"
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

URACE does **not** replace coding agents, AI models, or orchestrators.

Use your preferred executor for intelligence and execution; URACE provides the persistent autonomous lifecycle around it.

Examples include:

- OpenAI GPT / Codex
- Anthropic Claude / Claude Code
- Google Gemini / Gemini CLI
- OpenHands
- other current or future AI agents, tools, APIs, and orchestrators

The minimum intelligent configuration is:

```text id="wqpjz2"
URACE → 1 capable AI
```

OpenHands and multi-agent systems are optional.

## Universal by Design

URACE is designed for:

**AI · executor · orchestrator · programming-language · file-format · project-type · platform · repository · version-control · build-system · cloud-provider agnosticism.**

Its lifecycle is based on generic concepts:

```text id="7pqnbu"
Product → Evidence → Objective → Operation
       → Executor → Validation → Checkpoint
```

Software is only one possible Product type.

## Setup

URACE currently uses **`URACE.md` as its bootstrap specification**.

`URACE.md` is a prompt-as-bootstrap-file: give it to a capable AI coding executor or orchestrator with access to the target repository.

The executor reads the specification, inspects the environment, and bootstraps the smallest implementation that satisfies URACE's architectural invariants and acceptance tests.

### 1. Get the Bootstrap Specification

Clone or copy this repository and use:

```text id="j8uv2z"
URACE.md
```

as the bootstrap prompt.

### 2. Choose an Executor

You only need **one capable AI**.

For example:

```text id="d2o84g"
URACE.md
   │
   ├──► Codex
   ├──► Claude Code
   ├──► Gemini CLI
   └──► another capable executor
```

Give the executor access to the repository where URACE should be bootstrapped and instruct it to implement `URACE.md` completely.

For example:

```text id="pgum1a"
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

An orchestrator such as OpenHands may instead consume `URACE.md` and use its configured AI executors:

```text id="q1s8wa"
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

OpenHands is **not required by URACE**.

It is simply one possible bootstrap/execution environment.

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

```text id="chvd75"
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

```bash id="cyh4ik"
# Inspect lifecycle state
urace --check

# Assess/plan without Product mutation
urace --plan

# Run persistent autonomous Product evolution
urace --autonomous
```

Exact installation and invocation details are determined by the implementation produced for the host environment.

## Autonomous Evolution

```text id="y3w66r"
Assess → Select Objective → Execute → Validate
   ↑                                  │
   └──── Checkpoint ← Persist ←───────┘
```

`--autonomous` continuously reassesses the Product and available evidence, delegates justified work, independently validates results, checkpoints accepted increments, and continues across replaceable executor sessions.

URACE may also evolve **itself** through the same policy-governed, validated, checkpointed, and recoverable lifecycle.

## The Boundary

```text id="4g1z26"
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

**The autonomous Product lifecycle remains.**

## License

MIT License — see `LICENSE`.