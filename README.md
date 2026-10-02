# URACE

**Universal Recursive Autonomous Co-Founder Engine**

> **It drives the boat. You pick the destination.**

URACE is a general-purpose, recursive autonomous product-evolution control plane that owns the journey from intent to continuously evolving product.

It preserves and governs a continuous Product lifecycle across bounded, replaceable, and potentially stateless intelligence and execution systems.

**You choose the destination you want to retain. URACE drives everything you delegate beneath it.** Within that delegated Authority, URACE independently discovers what should happen next, prioritizes, plans, selects capabilities, executes, learns from Evidence, validates results, checkpoints accepted progress, recovers across interruptions, becomes dormant when no justified action exists, reactivates when meaningful change occurs, and continues evolving the Product.

At its core, URACE is also an **open and editable idea expressed as an open-source blueprint** through `URACE.md`, from which its lifecycle architecture can be bootstrapped into an implementation, inspected, adapted, extended, and evolved without depending on any particular Product, AI, [Executor, or Orchestrator](#where-urace-sits). URACE sits **above those replaceable execution capabilities**, preserving lifecycle ownership while delegating bounded Operations beneath it.

**URACE is MIT-licensed.** Users may keep their resulting products, derived sub-products, and accumulated product intelligence proprietary, subject to the MIT License and applicable third-party rights.

When external Executors, Orchestrators, AI models, APIs, or services receive Product information, their own data-handling terms and controls still apply. See [Executor Data, Privacy, and Disclosure](#executor-data-privacy-and-disclosure).

```text
        PRODUCT / USERS / CUSTOMERS / MARKET / ENVIRONMENT
                              │
                              ▼
                           REALITY
                              │
                              ▼
                           EVIDENCE
                              │
                              ▼
                            IDEA
                              │
                              ▼
                    NORMATIVE DIRECTION
                              │
                              ▼
                     AUTHORITATIVE SOURCE
                              │
                              ▼
                      INTENT + AUTHORITY
                              │
                              ▼
                         ┌─────────┐
                         │  URACE  │◄────────────────────────┐
                         └────┬────┘                         │
                              │                              │
                  owns autonomous navigation                │
                              │                              │
                   delegates execution to                   │
              capable, replaceable Executor(s)              │
                              │                              │
                   ┌──────────┴──────────┐                   │
                   ▼                     ▼                   │
                PRODUCT              URACE ITSELF            │
                   │                  if justified           │
                   │                  + authorized           │
                   ▼                                          │
           USERS / CUSTOMERS                                  │
                   │                                          │
                   ▼                                          │
                 MARKET                                       │
                   │                                          │
                   ▼                                          │
              ENVIRONMENT                                     │
                   │                                          │
                   ▼                                          │
                 REALITY                                      │
                   │                                          │
                   ▼                                          │
                EVIDENCE ─────────────────────────────────────┘
```

**You choose what you retain. URACE drives what you delegate.**

---

## Summary

- **[Introduction](#URACE)** — A persistent autonomous product-evolution control plane that owns lifecycle navigation above replaceable intelligence and execution systems.
- **[Why URACE](#why-urace)** — Preserves continuous product evolution beyond individual AI sessions, models, agents, and orchestrators.
- **[Core Model](#the-core-model)** — Separates Intent, Authority, Evidence, URACE navigation, executor capabilities, and Validation.
- **[Authority](#you-decide-what-you-retain)** — You decide what remains authoritative; URACE autonomously drives what you delegate.
- **[Autonomous Evolution](#autonomous-product-evolution)** — Discovers, prioritizes, executes, validates, and checkpoints justified product evolution.
- **[Evidence](#evidence-driven-not-mutation-driven)** — Uses observed reality to guide evolution without allowing Evidence to manufacture Authority.
- **[Recursive Self-Evolution](#recursive-self-evolution)** — Can discover and execute improvements to its own implementation where already authorized.
- **[Evolution Boundaries](#three-kinds-of-evolution)** — Keeps product evolution, runtime URACE self-evolution, and `URACE.md` specification evolution distinct.
- **[Executors and Orchestrators](#not-an-executor-replacement)** — Keeps intelligence and execution replaceable; one capable executor is sufficient, while richer orchestration remains optional.
- **[Universal Design](#universal-by-design)** — Remains independent of particular models, executors, orchestrators, languages, repositories, platforms, and product types.
- **[Bootstrap](#bootstrap)** — Uses `URACE.md` as the authoritative bootstrap specification for creating an environment-appropriate running URACE.
- **[Using URACE](#using-urace-after-bootstrap)** — Operates through the generated persistent implementation rather than repeatedly using the bootstrap specification.
- **[Persistent Autonomy](#persistent-autonomy-and-dormancy)** — Remains lifecycle-active through both execution and efficient dormant/wake states.
- **[Validation and Effect Integrity](#validation-before-acceptance)** — Separates execution, observation, external effects, Validation, acceptance, and recovery.
- **[Executor Data, Privacy, and Disclosure](#executor-data-privacy-and-disclosure)** — Treats capability and permission to receive product information as separate concerns.
- **[Re-Bootstrap vs. Self-Evolve](#re-bootstrap-vs-self-evolve)** — Distinguishes rebuilding from the specification from normal authorized runtime evolution.
- **[Complete Model](#complete-model)** — Brings the architectural relationships together into the full URACE lifecycle.
- **[In One Sentence](#in-one-sentence)** — The shortest statement of URACE's purpose and operating model.

---

## Why URACE?

Most AI-assisted Product development still behaves roughly like this:

```text
User
 │
 ▼
choose task
 │
 ▼
AI / Agent
 │
 ▼
result
 │
 ▼
User chooses what happens next
```

The intelligence may be powerful, but lifecycle navigation still belongs to the user or to an individual execution session.

URACE moves that responsibility into a persistent layer:

```text
discover
   │
decide
   │
prioritize
   │
plan
   │
select capability
   │
execute
   │
observe
   │
validate
   │
checkpoint
   │
reassess
   └──────────────► repeat
```

Within applicable Authority, you do not need to continuously provide the next task, route, Executor, Plan, ordinary course correction, or decision already delegated to URACE.

Models improve. Agents change. Orchestrators come and go.

**The autonomous Product lifecycle remains.**

---

## Where URACE Sits

URACE is the **persistent autonomous Product-lifecycle layer above replaceable execution and orchestration systems**.

```text
AUTHORITATIVE SOURCE
        │
        ▼
INTENT + AUTHORITY
        │
        ▼
      URACE
        │
        │ owns lifecycle + delegates bounded Operations
        ▼
optional ORCHESTRATOR
        │
        │ coordinates execution
        ▼
   EXECUTOR(S)
        │
        │ provide intelligence / execution
        ▼
      EFFECTS
```

An **Executor** is a replaceable system to which URACE delegates a bounded Operation requiring intelligence and/or execution. It may be an AI, agent, tool, API, script, deterministic system, or another suitable capability.

A **capable Executor** is an Executor capable of performing a particular Operation under its applicable context and constraints while returning enough observable information for URACE to evaluate and validate the result. Capability is contextual. A capable AI is one possible capable Executor.

An **Orchestrator** is an optional, replaceable execution-layer system that coordinates one or more Executors.

A **capable Orchestrator** provides sufficient execution control and observability for URACE to delegate and supervise required Operations through it without transferring lifecycle ownership or making the Executors beneath it irreplaceable.

URACE can also delegate directly:

```text
URACE ──► EXECUTOR
```

Examples of systems that may fulfill Executor roles include **Codex, Claude Code, and Gemini CLI**. **OpenHands** is an example of a system that may fulfill the Orchestrator role. These are examples, not architectural dependencies; actual capability and suitability depend on the Operation and deployment.

> **Executors provide capabilities. Orchestrators coordinate execution. URACE sits above both and owns the persistent autonomous Product lifecycle.**

One capable Executor is sufficient when it can perform the required Operations. For the richer recommended topology, see [Minimum and Recommended Execution Setups](#minimum-and-recommended-execution-setups).

---

## Core Model

URACE separates responsibilities that are often collapsed together:

```text
INTENT       → destination
AUTHORITY    → legitimate autonomous decision space
EVIDENCE     → reality
URACE        → navigation
EXECUTORS    → capabilities
VALIDATION   → acceptance
```

**Intent** describes what the Product is ultimately trying to accomplish.

**Authority** determines which decisions you retain and which URACE may make autonomously.

**Evidence** constrains what URACE may defensibly conclude about reality.

**URACE** owns persistent lifecycle navigation inside applicable Authority.

**Executors** provide bounded intelligence and/or execution.

**Validation** determines whether observed results become accepted Product state.

Evidence may justify changing a route or a delegated destination. It does not create Authority to change a destination you retained.

Executor capability does not create Authority.

Executor output does not automatically become accepted Product state.

> **URACE owns persistent autonomous Product navigation. Replaceable Executors supply whatever intelligence or execution is required to advance it.**

The governing principle is:

> **Maximum justified autonomy inside applicable Authority; zero intentional autonomy outside it.**

---

## Intent + Authority

Intent and Authority are designed to work together.

```text
INTENT
"What should be accomplished?"
        +
AUTHORITY
"What may URACE decide
while pursuing it?"
        │
        ▼
GOVERNING AUTONOMOUS SCOPE
        │
        ▼
URACE navigates autonomously
inside that scope
```

Intent without Authority does not establish which decisions URACE may autonomously make.

Authority without Intent does not establish what those decisions should advance.

> **Intent defines what URACE is trying to accomplish. Authority defines how much of the journey URACE owns. Together, they define the governing scope of autonomous Product evolution.**

For example:

```text
Intent:
  Build Product X.

Authority:
  Retain:
    - Product X
    - requirement A

  Delegate:
    - Objectives and prioritization
    - strategy
    - experiments
    - architecture
    - implementation
    - Plans
    - Executor selection
```

URACE may then autonomously navigate everything delegated beneath `Product X`, while preserving `Product X` and requirement A.

A broader configuration may instead be:

```text
Intent:
  Solve problem X for Y.

Authority:
  Retain:
    - problem X
    - beneficiary Y
    - constraint A

  Delegate:
    - Product realization
    - Product direction below problem X
    - Objectives and prioritization
    - strategy and experiments
    - architecture and implementation
    - Executor selection
```

In this case, URACE may autonomously determine and evolve the Product realization while preserving the higher-order destination you retained.

Conceptually:

```text
Intent + Authority
        │
        ▼
highest retained destination
        +
delegated decision space
        │
        ▼
autonomous navigation
```

This combination is established during bootstrap and remains part of the durable lifecycle state.

---

## Minimum Intelligent Setup

URACE requires no fixed execution stack. At minimum:

```text
Idea / Intent
     +
1 capable Executor
     │
     ▼
   URACE.md
     │
  bootstrap
     │
     ▼
    URACE
     │
     ▼
capable Executor(s)
     │
     ▼
   Product
```

> **One idea + one capable Executor is enough to start. A capable AI can be that Executor.**

The starting point may instead be an existing Product, problem, mandate, desired outcome, or other sufficient Intent. The bootstrap Executor may continue beneath URACE, be replaced, or be joined by others.

See [Where URACE Sits](#where-urace-sits) for role definitions and [Minimum and Recommended Execution Setups](#minimum-and-recommended-execution-setups) for richer deployments.

---

## You Decide What You Retain

The starting goal does not become disposable merely because URACE is autonomous.

**If you choose a destination and do not delegate Authority to change it, URACE preserves that destination.**

```text
RETAINED DECISION
        │
        ▼
     YOU decide


DELEGATED DECISION
        │
        ▼
    URACE decides
```

For example:

```text
YOU
 │
 ▼
"Build Product X"
 │
 │ retained destination
 ▼
URACE
 │
 ├── discover Objectives
 ├── prioritize
 ├── choose strategy
 ├── plan
 ├── choose architecture
 ├── run experiments
 ├── select Executors
 ├── implement
 └── correct course
 │
 ▼
PRODUCT X
```

URACE may radically change the journey without silently replacing `Product X`.

Alternatively:

```text
YOU
 │
 ▼
"Solve problem X.
Choose and evolve the Product
realization when justified."
 │
 ▼
URACE
 │
 ▼
Evidence + Assessment
 │
 ▼
autonomously choose or evolve
Product direction
```

Here, solving problem X remains the higher-order retained destination while Product realization has been delegated to URACE.

The same principle works recursively:

```text
YOU RETAIN
     │
     ▼
highest non-delegated destination
     │
     ▼
YOU DELEGATE
     │
     ▼
URACE owns navigation and
subordinate decisions
```

A retained destination remains retained until valid Authority changes it.

A delegated decision belongs to URACE while that delegation remains applicable.

Stable delegation should not become a repeated approval loop.

> **Autonomy changes who navigates the delegated journey. It does not silently change the destination you chose to retain.**

---

## Autonomous Product Evolution

URACE is not merely a task queue or wrapper around an AI.

It continuously reassesses what should happen next:

```text
              INTENT
                 │
                 ▼
              PRODUCT
                 │
                 ▼
              REALITY
                 │
                 ▼
             EVIDENCE
                 │
                 ▼
              ASSESS
                 │
                 ▼
        discover Objectives
                 │
                 ▼
             prioritize
                 │
                 ▼
               plan
                 │
                 ▼
       select capability
                 │
                 ▼
              execute
                 │
                 ▼
              observe
                 │
                 ▼
             validate
                 │
                 ▼
            checkpoint
                 │
                 └──────────────► reassess
```

Depending on what you delegate, autonomous evolution may include Objectives, Priority, Plans, experiments, implementation, architecture, processes, strategy, Executor selection, and Product direction.

When a route fails, URACE changes the route.

When a delegated destination should change, URACE may change it when sufficiently justified.

When a retained destination appears infeasible, URACE preserves both the observed reality and your retained boundary rather than silently redefining either.

---

## Evidence-Driven Evolution

Autonomy without reality is drift.

URACE therefore treats Evidence as a first-class lifecycle input.

Evidence may come from Product behavior, runtime observations, users, customers, prospects, analytics, transactions, adoption, activation, conversion, retention, churn, repeated use, realized outcomes, experiments, research, external systems, deterministic measurement, Executor research, or authoritative input.

```text
Product / Users / Market / Environment
                  │
                  ▼
               EVIDENCE
                  │
                  ▼
                ASSESS
                  │
                  ▼
          justified change
                  │
                  ▼
          preserve or evolve
```

But:

```text
Evidence ≠ Intent
Evidence ≠ Authority
Evidence ≠ automatic truth
Executor claim ≠ Evidence by default
Quantity ≠ quality
```

Evidence may justify exercising existing Authority. It does not manufacture new Authority.

Conflicting, incomplete, or weak Evidence should preserve appropriate uncertainty rather than manufacture certainty.

---

## Recursive Self-Evolution

URACE itself can participate in the lifecycle.

You do not need to notice every limitation and manually request every improvement.

```text
            GOVERNING INTENT
                   │
                   ▼
                 URACE
                   │
                 assess
                   │
         ┌─────────┴─────────┐
         ▼                   ▼
     Product gap          URACE gap
         │                   │
         ▼                   ▼
Product Objective     Self-Evolution Objective
         │                   │
         └─────────┬─────────┘
                   ▼
               prioritize
                   │
                   ▼
                  plan
                   │
                   ▼
                 execute
                   │
                   ▼
                validate
                   │
                   ▼
               checkpoint
                   │
                   └──────────► reassess
```

Where existing Authority permits it, URACE may autonomously discover that its own implementation is limiting the governing Intent, promote that limitation into an Objective, prioritize it against Product work, plan the improvement, execute it through replaceable Executors, validate it, checkpoint the accepted change, and continue operating.

### Self-Evolution Is Not Self-Authorization

Autonomous initiation does not create Authority.

```text
discover justified
self-evolution
       │
       ▼
resolve Authority
       │
   ┌───┴───┐
   ▼       ▼
AUTHORIZED NOT AUTHORIZED
   │       │
   ▼       ▼
evolve   preserve boundary
```

URACE may not use self-evolution to create its own Authority, broaden delegation, override retained Intent, remove protected constraints, or bypass validation.

> **URACE may autonomously initiate its own evolution. It may not autonomously expand the Authority under which that evolution occurs.**

---

## Three Kinds of Evolution

URACE distinguishes three related but different processes:

```text
PRODUCT EVOLUTION

Running URACE
     │
     ▼
evolve Product
     │
     ▼
validate + checkpoint


RUNTIME SELF-EVOLUTION

Running URACE
     │
discovers own limitation
     │
     ▼
authorized self-evolution
     │
     ▼
validate + checkpoint
     │
     ▼
continue improved


SPECIFICATION EVOLUTION

URACE.md
   │
open / editable development
   │
   ▼
Evolved URACE.md
```

Changing `URACE.md` does not automatically mutate a running URACE implementation.

A running URACE improving itself does not automatically rewrite `URACE.md`.

Normal Product evolution and authorized runtime self-evolution do not inherently require re-bootstrap.

---

## Executors and Orchestrators

The execution roles are defined in [Where URACE Sits](#where-urace-sits).

The architectural rule is simple:

> **URACE owns the lifecycle. Executors provide capabilities. Orchestrators optionally coordinate them.**

Lifecycle continuity must not depend on any particular Executor or Orchestrator.

For topology choices, see [Minimum and Recommended Execution Setups](#minimum-and-recommended-execution-setups). For replacement behavior, see [Replaceable Intelligence](#replaceable-intelligence). For disclosure and privacy constraints on selection, see [Executor Data, Privacy, and Disclosure](#executor-data-privacy-and-disclosure).

---

## Minimum and Recommended Execution Setups

URACE distinguishes **architectural sufficiency** from a **richer general-purpose deployment**.

### Minimum

```text
URACE
  │
  ▼
1 capable Executor
```

One [capable Executor](#where-urace-sits) is sufficient when it can perform the Operations required by the lifecycle.

### Recommended General-Purpose Setup

For stronger general-purpose autonomous operation, the recommended topology is:

> **One capable Orchestrator plus at least three complementary capable AI Executors.**

```text
                    URACE
                      │
             owns Product lifecycle
                      │
                      ▼
             CAPABLE ORCHESTRATOR
                e.g. OpenHands
                      │
          ┌───────────┼───────────┐
          ▼           ▼           ▼
       Codex      Claude Code   Gemini CLI
```

The complementary Executors provide a broader capability pool; they need not participate in every Operation or occupy permanent roles. URACE selects among available capabilities according to the work at hand.

These products are examples, not dependencies. Current capabilities, availability, terms, privacy characteristics, and suitability should be verified for the deployment.

> **One capable Executor is sufficient. A capable Orchestrator plus at least three complementary capable AI Executors is the recommended richer general-purpose setup.**

More Executors are not automatically better. The goal is useful complementary capability, not Executor count.

---

## Replaceable Intelligence

Lifecycle continuity belongs to URACE rather than to a particular intelligence provider or conversation.

```text
               URACE
                 │
                 ▼
             Executor A
                 │
           bounded result
                 │
                 ▼
         observe + validate
                 │
                 ▼
            checkpoint
                 │
         Executor A disappears
                 │
                 ▼
             Executor B
                 │
                 ▼
              continue
```

A replacement Executor receives the bounded context necessary for its Operation rather than inheriting lifecycle ownership through a previous conversation.

Replaceability does not imply equivalent capability, privacy, security, reliability, specialization, context capacity, cost, latency, or data handling.

---

## Universal by Design

URACE's lifecycle semantics are designed to remain agnostic to any particular:

- AI or model;
- Executor;
- Orchestrator;
- Product type;
- programming language;
- file format;
- platform;
- repository or version-control system;
- build system;
- runtime;
- persistence technology;
- or cloud provider.

The generic lifecycle remains:

```text
You / Authoritative Source
        │
        ▼
Intent + Authority
        │
        ▼
Assessment
        │
        ▼
Objective
        │
        ▼
Priority
        │
        ▼
Plan
        │
        ▼
Operation
        │
        ▼
Executor
        │
        ▼
Observation
        │
        ▼
Validation
        │
        ▼
Checkpoint
        │
        ▼
Reassessment
```

Software is only one possible Product form.

Implementations may be environment-specific.

The lifecycle architecture is not tied to a particular environment.

---

# Bootstrap

`URACE.md` is a **prompt-as-bootstrap-file**.

It is the blueprint, not the running system.

```text
URACE.md
   │
   │ specification
   ▼
CAPABLE EXECUTION
   │
   │ creates
   ▼
RUNNING URACE
```

It defines the architecture, invariants, lifecycle semantics, implementation constraints, behavioral expectations, and bootstrap requirements from which an environment-appropriate persistent implementation can be created.

---

## 1. Establish Intent + Authority

Define the governing Intent and which decisions remain retained versus delegated. These become part of the [Companion Bootstrap Document](#4-bootstrap-from-the-specification).

For the underlying semantics and examples, see [Intent + Authority](#intent--authority).

---

## 2. Provide Starting Context

Add the Product context, relevant artifacts, existing state, constraints, protected properties, available capabilities, and environment-specific information required for bootstrap to the same [Companion Bootstrap Document](#4-bootstrap-from-the-specification).

The target need not be a software repository, and URACE does not require Git, a particular language, framework, cloud, or runtime.

---

## 3. Choose the Bootstrap Setup

Use either the [minimum or recommended execution topology](#minimum-and-recommended-execution-setups).

The selected capability performs bootstrap; it does not thereby acquire persistent lifecycle ownership.

---

## 4. Bootstrap from the Specification

`URACE.md` is authoritative. This README provides non-authoritative positioning, usage, examples, and deployment guidance. If they differ, `URACE.md` governs.

### Prepare a Companion Bootstrap Document

Keep deployment-specific information outside `URACE.md` in a companion document containing, as applicable:

- governing Intent and retained/delegated Authority;
- Product context and relevant artifacts;
- constraints and protected properties;
- existing state;
- available Executors, Orchestrators, tools, APIs, and other capabilities;
- environment-specific bootstrap information.

Then provide both to the selected [bootstrap capability](#3-choose-the-bootstrap-setup):

```text
        URACE.md
 authoritative specification
             +
    COMPANION DOCUMENT
 Intent + Authority
 Product context
 constraints
 existing state
 capabilities
             │
             ▼
   BOOTSTRAP CAPABILITY
             │
             ▼
   UNDERSTAND ENVIRONMENT
             │
             ▼
BUILD SMALLEST COMPLETE
     IMPLEMENTATION
             │
             ▼
TEST SPECIFICATION INVARIANTS
             │
             ▼
      REPAIR FAILURES
             │
             ▼
  VALIDATED RUNNING URACE
```

Instruct the bootstrap capability to build and validate the **smallest complete implementation satisfying `URACE.md`**, using the companion document only as deployment-specific context.

The separation is intentional:

```text
URACE.md
    │
    └── authoritative lifecycle specification

Companion Bootstrap Document
    │
    └── deployment-specific Intent, Authority,
        Product context, constraints, state,
        and available capabilities
```

The companion document supplements `URACE.md`; it cannot override it, manufacture Authority, broaden delegation, weaken specification invariants, or reinterpret retained Intent.

Normative Authority, self-evolution, specification-evolution, validation, effect-integrity, recovery, dormancy, wakeability, behavioral-test, and bootstrap-reporting requirements remain in `URACE.md`.

---

## 5. Validate the Bootstrap

A valid bootstrap must satisfy the behavioral tests and success criteria defined by `URACE.md`; generating files or repeatedly calling an AI is not sufficient.

---

## Bootstrap Role Reversal

The important distinction is not **AI before vs. AI after bootstrap**.

It is **lifecycle ownership before vs. after bootstrap**.

```text
BOOTSTRAP

URACE.md
   │
   ▼
EXECUTOR / ORCHESTRATOR + EXECUTORS
   │
   ▼
creates URACE


NORMAL OPERATION

YOU
 │
 ▼
INTENT + AUTHORITY
 │
 ▼
URACE
 │
owns lifecycle
 │
selects + delegates
 ▼
ORCHESTRATOR
 │
 ├── Executor A
 ├── Executor B
 └── Executor C
```

> **Before bootstrap, capable execution systems create URACE. After bootstrap, URACE becomes the persistent lifecycle owner and uses those systems as replaceable capabilities beneath it.**

The same systems may appear on both sides of that boundary.

Their role changes.

Lifecycle ownership does not remain with them.

---

# Using URACE

After bootstrap, use the generated persistent implementation rather than treating `URACE.md` itself as the operational loop.

Conceptually:

```text
# Inspect lifecycle state
urace --check

# Assess, discover, prioritize, and plan
urace --plan

# Run persistent autonomous lifecycle operation
urace --autonomous
```

The actual interface may instead be an API, service, daemon, worker, container, scheduled runtime, serverless runtime, agent interface, or another appropriate mechanism.

The interface is replaceable.

The lifecycle semantics are not.

---

## Configure Intent + Authority

Intent and Authority remain the primary governing combination during operation.

For narrow Product autonomy:

```text
Intent:
  Build Product X.

Authority:
  Retain:
    - Product X
    - requirement A

  Delegate:
    - Objectives
    - Priority
    - Plans
    - strategy
    - experiments
    - architecture
    - implementation
    - Executor selection
```

For broader Product autonomy:

```text
Intent:
  Solve problem X.

Authority:
  Retain:
    - problem X
    - protected constraints

  Delegate:
    - Product realization
    - subordinate Product direction
    - Objectives
    - Priority
    - Plans
    - strategy
    - experiments
    - implementation
    - Executor selection
```

Changing Intent or Authority materially should cause URACE to reassess affected lifecycle decisions rather than silently continuing under stale premises.

---

## Inspect

`--check` may expose:

- governing Intent;
- retained and delegated Authority;
- current lifecycle state;
- current Objective;
- current Plan;
- Evidence;
- assumptions and uncertainty;
- pending Operations;
- unresolved effects;
- validation state;
- current checkpoint;
- available capabilities;
- dormancy and wake state;
- retained decisions;
- and blockers.

Observability does not transfer navigation responsibility back to you.

---

## Plan

```text
State + Intent + Authority + Evidence
                 │
                 ▼
               ASSESS
                 │
                 ▼
        DISCOVER OBJECTIVES
                 │
                 ▼
             PRIORITIZE
                 │
                 ▼
                PLAN
```

Plans are replaceable strategies.

Material changes in Authority, Intent, Evidence, state, constraints, or assumptions may justify reassessment and replanning.

---

## Run Autonomous Product Evolution

```text
urace --autonomous
```

During persistent autonomous operation:

```text
                 URACE
                   │
                 observe
                   │
                 assess
                   │
                discover
                   │
         ┌─────────┴─────────┐
         ▼                   ▼
    Product Work         URACE Work
         │                   │
         └─────────┬─────────┘
                   ▼
               prioritize
                   │
                  plan
                   │
           select capability
                   │
                 execute
                   │
                 observe
                   │
                validate
                   │
               checkpoint
                   │
                   └──────────► reassess
```

You do not need to provide a new prompt for every cycle.

---

## Autonomous Executor Selection

URACE selects among [available execution capabilities](#where-urace-sits) according to the actual Operation.

Selection includes not only technical capability, reliability, cost, and availability, but also whether the capability may legitimately receive the required context.

> **Capability does not imply disclosure Authority or suitability.**

For the complete data-handling boundary, see [Executor Data, Privacy, and Disclosure](#executor-data-privacy-and-disclosure).

---

## Intervene Without Becoming the Pilot

You may change a retained destination, grant or narrow delegation, revoke Authority, establish HARD constraints, restrict Executors or disclosure, pause, resume, or terminate operation.

URACE then reassesses against the changed authoritative state.

Intervention does not require you to resume ordinary lifecycle navigation.

---

# Persistent Autonomy

Persistent autonomy does not mean infinite busy execution.

```text
             ACTIVE
               │
               ▼
             ASSESS
               │
               ▼
      JUSTIFIED ACTION?
          │          │
         yes         no
          │          │
          ▼          ▼
       EXECUTE    DORMANT
          │          │
          │    meaningful change
          │          │
          │          ▼
          │       TRIGGER
          │          │
          └──────────┴────► ACTIVE
```

Dormancy is valid autonomous operation.

A runtime may release resources while dormant as long as durable lifecycle state and a viable path back to assessment remain.

Persistent autonomy means persistent **lifecycle ownership**, not permanent compute activity.

---

# Validation, Effect Integrity, and Recovery

## Validation Before Acceptance

```text
EXECUTE
   │
   ▼
OBSERVE
   │
   ▼
VALIDATE
   │
 ┌─┴─┐
 ▼   ▼
FAIL PASS
 │    │
 ▼    ▼
REPAIR CHECKPOINT
```

An Executor reporting that an Operation is complete does not by itself establish an accepted checkpoint.

URACE independently determines acceptance according to applicable validation.

## Effect Integrity

URACE distinguishes:

```text
INTENDED ACTION
      │
      ▼
    ATTEMPT
      │
      ▼
EXTERNAL EFFECT
      │
      ▼
 OBSERVATION
      │
      ▼
  VALIDATION
      │
      ▼
  ACCEPTANCE
```

Where an external effect is uncertain, URACE preserves that uncertainty and reconciles it rather than silently assuming success, failure, or retry safety.

## Recovery

```text
CRASH / STOP / RESTART
          │
          ▼
   load durable state
          │
          ▼
 restore Intent + Authority
          │
          ▼
reconcile uncertain effects
          │
          ▼
 restore Objective / Plan
          │
          ▼
    reassess reality
          │
          ▼
       continue
```

URACE should not depend on reconstructing its lifecycle from previous chat history.

---

# Executor Data, Privacy, and Disclosure

> **Disclosure / Disclaimer:** URACE itself does not guarantee the confidentiality, retention behavior, security, privacy, **training or model-improvement use**, or other data practices of third-party Executors, Orchestrators, models, APIs, or services.

Executor replaceability does not make available systems equivalent in trust, privacy, security, capability, or data handling.

Information delegated to an external system may be transmitted, retained, logged, reviewed, used for model training or improvement, or otherwise processed according to the provider, product, account type, configuration, deployment model, contractual terms, retention settings, organizational controls, and current policies.

Whether a particular service uses submitted information for training or model improvement varies.

**Verify the current practices, controls, and applicable terms of each external system rather than assuming that all Executors or AI services handle data identically.**

Before delegation, determine whether the selected capability may legitimately receive the required context under applicable Authority, constraints, policy, and data-handling requirements.

```text
SENSITIVE / PROPRIETARY CONTEXT
             │
             ▼
           URACE
             │
             ▼
MAY THIS CAPABILITY RECEIVE IT?
          ┌──┴──┐
          ▼     ▼
         YES    NO
          │      │
          ▼      ▼
      MINIMIZE   SELECT ANOTHER
       CONTEXT     CAPABILITY
```

Sensitive or restricted context may include proprietary source code, credentials, secrets, personal or customer data, confidential business information, regulated data, security-sensitive material, unpublished intellectual property, or other information subject to disclosure restrictions.

Relevant selection factors include capability, disclosure Authority, data sensitivity, training/model-improvement practices, retention/logging, privacy/security/isolation, context minimization, reliability/observability, compliance requirements, cost, latency, and availability.

Where appropriate, deployments may use data minimization, redaction, scoped credentials, deterministic tools, isolated environments, local or self-hosted models, private deployments, or configurations whose applicable controls satisfy the Product's requirements.

> **Capability does not imply disclosure Authority or suitability.**

**Choose an Executor for both what it can do and what it may safely and legitimately receive.**

URACE makes execution replaceable. It does **not** make third-party data practices interchangeable or override the Authority, constraints, policies, legal requirements, or contractual terms governing a deployment.

---

# Open Blueprint, Independent Products

URACE separates its open lifecycle blueprint from Products governed through it.

```text
OPEN / EDITABLE BLUEPRINT
        │
        ├── URACE idea
        ├── URACE.md
        └── lifecycle architecture
                 │
                 ▼
         bootstrap / govern
                 │
                 ▼
              PRODUCT
```

The blueprint can be inspected, adapted, extended, and evolved independently of any particular Product or [execution stack](#where-urace-sits).

A Product may independently contain proprietary data, implementation, integrations, decisions, Evidence, context, business logic, or accumulated intelligence.

> **An open blueprint does not require an open Product.**

For external-system confidentiality and data handling, see [Executor Data, Privacy, and Disclosure](#executor-data-privacy-and-disclosure).

---

# Complete Model

```text
                              YOU
                               │
                      choose what to retain
                               │
                               ▼
                            INTENT
                         destination
                               │
                               ▼
                           AUTHORITY
                retained / delegated / constraints
                               │
                               ▼
                            URACE
                               ▲
                               │
                        EVIDENCE / REALITY
                               │
                               ▼
           ┌────────────────────────────────────┐
           │ observe                            │
           │ assess                             │
           │ discover                           │
           │ prioritize                         │
           │ plan                               │
           │ decide                             │
           │ select capabilities                │
           │ execute                            │
           │ learn                              │
           │ validate                           │
           │ checkpoint                         │
           │ recover                            │
           │ sleep / wake                       │
           └─────────────────┬──────────────────┘
                             │
                ┌────────────┴────────────┐
                ▼                         ▼
             PRODUCT                 URACE ITSELF
                               if justified + authorized
                │                         │
                └────────────┬────────────┘
                             │
                             ▼
                      REALITY / EVOLUTION
                             │
                             └──────────────► Evidence


                 EXECUTION DELEGATION

                            URACE
                              │
                              ▼
                   optional ORCHESTRATOR
                              │
                  ┌───────────┼───────────┐
                  ▼           ▼           ▼
               EXECUTOR    EXECUTOR    EXECUTOR
```

The architectural boundary is:

> **URACE persistently drives Product evolution toward the highest destination you have not delegated Authority to change, autonomously owning navigation and every delegated destination decision while preserving attributable Authority, reality-constrained Evidence, independent validation, recoverable continuity, and replaceability of the intelligence and execution systems beneath it.**

In the underlying architecture, that retained governing destination is the **highest applicable non-delegated authoritative Intent**, allowing the same model to work when the authoritative source is a user, Product owner, organization, governing mandate, contract, policy, or another legitimate source of Authority.

URACE does not need to own a particular model, Executor, Orchestrator, scheduler, database, cloud, repository, identity system, or external Evidence source.

It owns the durable lifecycle semantics connecting them.

---

# In One Sentence

> **Starting from as little as an idea and one capable Executor—which may be a capable AI—bootstrap URACE from `URACE.md`; you choose the destination and destination-setting Authority you want to retain, while URACE persistently drives everything you delegate beneath that boundary through replaceable capabilities, autonomously discovers what should happen next—including when its own evolution is justified—learns from Evidence, validates results, recovers across interruptions, becomes dormant and reactivates when appropriate, and keeps the intelligence and execution beneath it replaceable.**

---

**You choose the destination you want to retain.**

**URACE drives what you delegate.**

**URACE autonomously discovers what should evolve.**

That can include the Product.

That can include URACE itself.

Self-evolution can be autonomously initiated.

Self-evolution never means self-authorization.

**One idea + one capable Executor is enough to start. A capable AI can be that Executor.**

**For stronger general-purpose operation, the recommended setup is one capable Orchestrator plus at least three complementary capable AI Executors.**

Models improve. Agents change. Orchestrators come and go.

**The autonomous Product lifecycle remains.**

---

# License

MIT
