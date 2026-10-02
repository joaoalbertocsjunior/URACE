# URACE

**Universal Recursive Autonomous Co-Founder Engine**

> **It drives the boat. You pick the destination.**

More precisely: you retain whatever destination-setting authority you choose. URACE autonomously drives everything you delegate—including subordinate destination evolution when explicitly authorized.

## Description

URACE is an **executor-agnostic persistent autonomous Product-evolution control plane**.

**At its core, URACE is an open-source and editable idea as blueprint:** a specification and bootstrap architecture for making autonomous Product evolution persistent, evidence-aware, authority-bounded, validated, recoverable, and independent of any particular AI or executor.

The idea can be inspected, adapted, extended, and evolved while preserving or deliberately revising its lifecycle invariants. The idea is open and editable; a Product, its accumulated intelligence, and its implementation can remain proprietary.

URACE turns bounded and replaceable AI/executor sessions into a continuous autonomous Product lifecycle.

It preserves the durable layer that individual AI sessions generally do not own: **Intent, Authority, State, Evidence, Triggers, Objectives, Plans, decisions, validation, checkpoints, recovery, dormancy, and reactivation.**

Within delegated Authority, URACE autonomously determines what should happen next—and why—while delegating bounded intelligence and execution to replaceable systems.

> **The authoritative source chooses the destination it wishes to retain. URACE drives the Product toward it.**

---

## Why URACE?

AI agents can research, reason, plan, code, test, and repair—but individual executions are bounded.

Sessions end. Context disappears. Models change. Providers fail. Agents and orchestrators are replaced.

URACE makes the **Product lifecycle**, rather than any particular AI session, the persistent unit of autonomy.

```text
       AUTHORITATIVE SOURCE
                │
                ▼
        INTENT + AUTHORITY
     destination + delegation
                │
                ▼
       ┌─────────────────┐
       │      URACE      │◄──── Evidence / Reality
       │                 │
       │ discover        │
       │ decide          │
       │ prioritize      │
       │ plan            │
       │ execute         │
       │ learn           │
       │ correct course  │
       │ validate        │
       │ recover         │
       │ sleep / wake    │
       └────────┬────────┘
                │
                ▼
        Generic Executor
                │
        ┌───────┼────────┐
        ▼       ▼        ▼
       1 AI   Agents   Orchestrator
                          │
                          ▼
                        1..N AI
```

The distinction is deliberate:

```text
Intent
    defines destination

Authority
    defines legitimate autonomy

Evidence
    describes reality

URACE
    owns navigation

Executors
    provide replaceable capabilities
```

URACE does not require the user to continuously provide the next task, select the next route, choose the executor, or approve decisions that have already been delegated.

---

## Destination and Autonomy

URACE is autonomous without being unbounded.

The authoritative source retains control over whatever destination-setting Authority it does not delegate.

Inside delegated Authority, URACE owns the journey.

```text
AUTHORITATIVE SOURCE
        │
        ▼
"Build Product X"
        │
        ▼
URACE
  ├── discovers what matters next
  ├── prioritizes
  ├── plans
  ├── chooses capabilities
  ├── executes
  ├── gathers Evidence
  ├── validates
  ├── learns
  ├── corrects course
  ├── recovers
  └── continues autonomously
```

If the authoritative source instead says:

```text
"Solve problem X.
You may change the Product
if Evidence supports a better path."
```

then Product-level destination evolution has itself been delegated:

```text
HIGHER-ORDER INTENT
        │
        ▼
DELEGATED PRODUCT SPACE
        │
   ┌────┼────┐
   ▼    ▼    ▼
   A    B    C
        │
        ▼
Evidence + Assessment
        │
        ▼
URACE may autonomously
select or evolve the
Product direction
```

URACE therefore preserves a simple boundary:

> **The authoritative source controls what it retains. URACE autonomously controls what is delegated.**

Evidence can justify a different route—or an authorized destination change—but Evidence does not independently create Authority.

---

## Not an Executor Replacement

URACE does not replace coding agents, AI models, tools, or orchestrators.

Use your preferred executor for intelligence and execution; URACE provides the persistent autonomous lifecycle around it.

Examples include:

- OpenAI GPT / Codex
- Anthropic Claude / Claude Code
- Google Gemini / Gemini CLI
- OpenHands
- other current or future AI agents, tools, APIs, and orchestrators

The minimum intelligent configuration is:

```text
URACE → 1 capable AI
```

OpenHands, other orchestrators, and multi-agent or multi-model systems are optional.

For practical higher-capability deployments, the project recommends bootstrapping and operating URACE with at least one capable execution/orchestration environment and, where useful, multiple independent capable AI models.

This is deployment guidance, not an architectural requirement.

URACE itself requires neither an orchestrator nor multiple AIs.

Every intelligence and execution component underneath URACE remains replaceable.

---

## Executor Data and Privacy Warning

**URACE being open and executor-agnostic does not determine what an external AI executor does with data sent to it.**

An AI executor **may** transmit, retain, log, review, process, or use submitted information for service operation or model improvement/training, depending on the executor and the conditions under which it is used.

**“May” is intentional.** Data handling is not universal across AI systems. It can depend on factors such as:

- the provider and service;
- consumer vs. business/API/enterprise products;
- account and privacy settings;
- opt-in or opt-out configuration;
- contractual and data-processing terms;
- retention policies;
- deployment mode;
- self-hosted vs. externally hosted execution;
- organization-specific controls;
- changes to provider policies over time.

Therefore, the fact that a Product's intelligence **can remain proprietary within the URACE architecture does not mean that sending that intelligence to an arbitrary executor preserves its confidentiality.**

Before giving an executor access to proprietary, confidential, personal, regulated, security-sensitive, or otherwise restricted information, verify the executor's current terms, privacy and retention policies, training/model-improvement practices, deployment configuration, and applicable organizational requirements.

Where necessary, constrain what URACE is authorized to disclose:

```text
PROPRIETARY PRODUCT STATE
          │
          ▼
   URACE AUTHORITY
    + DATA POLICY
          │
          ▼
   MINIMIZE / FILTER
          │
          ▼
 APPROVED EXECUTOR
          │
          ▼
   BOUNDED CONTEXT
```

Executor capability does not imply permission to disclose information to that executor.

A deployment may instead use approved enterprise/API configurations, privacy-preserving integrations, local or self-hosted models, isolated execution environments, deterministic tools, or other mechanisms appropriate to its requirements.

URACE does not itself guarantee the confidentiality, privacy, retention behavior, or training practices of third-party executors.

---

## Universal by Design

URACE is designed for:

**AI · executor · orchestrator · programming-language · file-format · project-type · platform · repository · version-control · build-system · cloud-provider agnosticism.**

Its lifecycle is based on generic concepts:

```text
Authoritative Source
        │
        ▼
Intent + Authority
        │
        ▼
Product + Evidence
        │
        ▼
Assessment
        │
        ▼
Objective
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
        └──────────► Reassess
```

Software is only one possible Product type.

URACE can govern evolution of software, services, research, content, business processes, operational systems, mixed Products, or initially unknown Product forms.

It does not require a particular Product-development methodology, market model, repository structure, runtime, scheduler, event system, persistence technology, or AI provider.

---

## Evidence-Driven, Not Mutation-Driven

Autonomy does not mean changing the Product indefinitely.

URACE continuously evaluates whether further implementation, experimentation, learning, repair, validation, or no immediate action has the greatest justified value relative to Intent.

```text
Intent
  +
Evidence
  +
State
  +
Constraints
  +
Uncertainty
  +
Risk
  +
Time
  +
Capacity
    │
    ▼
Assessment
    │
    ▼
Best justified
authorized action
```

Where Product success depends on external reality, credible relevant external Evidence constrains what URACE may defensibly conclude.

Internal confidence is not a substitute for external validation.

At the same time:

```text
Evidence ≠ Authority
```

Evidence can show that a route is failing.

URACE can autonomously change that route.

Evidence can support changing a delegated Product direction.

URACE can autonomously evaluate that change.

But Evidence alone cannot silently redefine a destination whose Authority was retained.

---

## Persistent Autonomy

`--autonomous` means persistent ownership of the Product lifecycle—not an endless executor loop.

```text
Observe
   ↓
Assess
   ↓
Discover
   ↓
Decide
   ↓
Prioritize
   ↓
Plan
   ↓
Execute
   ↓
Observe Effect
   ↓
Validate
   ↓
Checkpoint
   ↓
Reassess
   ↺
```

When no sufficiently justified authorized action exists:

```text
NO JUSTIFIED WORK NOW
        │
        ▼
      DORMANT
        │
        ▼
Preserve lifecycle ownership
        │
   ┌────┼────────────┐
   ▼    ▼            ▼
Evidence Schedule   Discovery
change   / time      / environment
   │      │            │
   └──────┼────────────┘
          ▼
        Trigger
          │
          ▼
       Reassess
```

Dormancy is autonomous operation.

It does not mean the lifecycle has ended.

A runtime may even disappear during dormancy where durable wake responsibility exists.

The important invariant is that URACE retains a viable path back to assessment.

---

# Bootstrap and Use

URACE uses **`URACE.md` as a prompt-as-bootstrap-file**.

This is an important distinction:

```text
URACE.md
    ≠
the running URACE system
```

`URACE.md` defines the architecture, invariants, lifecycle semantics, implementation constraints, behavioral tests, and bootstrap requirements.

A capable executor consumes that specification and **creates the actual persistent URACE implementation inside the target environment**.

After bootstrap, normal operation is driven by that implementation—not by repeatedly asking an AI to reread `URACE.md` and pretend to be URACE.

The lifecycle is therefore:

```text
PHASE 1 — BOOTSTRAP

URACE.md
    │
    ▼
Bootstrap Executor
    │
    ├── inspect target Product/environment
    ├── interpret specification
    ├── implement URACE
    ├── establish persistence
    ├── establish executor boundary
    ├── establish validation/recovery
    ├── run behavioral tests
    └── prove bootstrap invariants
    │
    ▼
RUNNING URACE


PHASE 2 — NORMAL OPERATION

Authoritative Source
    │
    ▼
Intent + Authority
    │
    ▼
URACE
    │
    ├── assess
    ├── discover
    ├── decide
    ├── prioritize
    ├── plan
    ├── select capabilities
    ├── delegate execution
    ├── observe
    ├── validate
    ├── checkpoint
    ├── recover
    └── sleep / wake
    │
    ▼
Replaceable Executors
```

This role reversal is fundamental:

```text
BOOTSTRAP

AI / Orchestrator
       │
       ▼
   reads URACE.md
       │
       ▼
 creates URACE


NORMAL OPERATION

      URACE
       │
       ▼
selects / delegates to
       │
       ▼
AI / Tools / Agents /
Orchestrators / APIs
```

The bootstrap executor creates URACE.

Once bootstrapped, **URACE becomes the persistent lifecycle owner and executors become replaceable capabilities beneath it.**

---

## Bootstrap Technique

### 1. Place `URACE.md` in the Target Context

Clone this repository, copy `URACE.md`, or otherwise make the specification available to a capable executor with access to the Product environment that URACE should govern.

Conceptually:

```text
Target Product / Repository
        │
        ├── existing Product artifacts
        ├── environment
        ├── constraints
        └── URACE.md
```

`URACE.md` does not assume that the target is software or that Git exists.

The target context can be whatever environment the selected executor can inspect and modify.

### 2. Select a Bootstrap Executor

Only one capable executor is required.

```text
URACE.md
   │
   ├──► Codex
   ├──► Claude Code
   ├──► Gemini CLI
   ├──► OpenHands
   └──► another capable executor
```

The executor needs sufficient access to inspect the target environment and create the required implementation.

**Before providing Product data or repository access, verify that the selected executor's data-handling practices are compatible with the information it will receive.**

Do not assume that using URACE, an API, an enterprise product, or a particular model automatically establishes confidentiality or prevents retention or model-improvement use. Those properties depend on the actual executor/service and configuration being used.

### 3. Bootstrap from the Specification

Give the executor `URACE.md` as the authoritative bootstrap specification.

A suitable bootstrap instruction is:

```text
Read URACE.md completely.

Treat it as the authoritative bootstrap specification for URACE.

Inspect the current Product, repository, environment, available
capabilities, constraints, existing state, and relevant artifacts.

Bootstrap the smallest complete implementation satisfying URACE.md.

Do not merely summarize, simulate, or describe URACE.

Implement the persistent lifecycle system itself.

Preserve the architectural boundary:
URACE owns persistent autonomous Product navigation;
replaceable executors provide bounded intelligence and execution.

Establish the required durable state, Authority and Intent semantics,
Evidence and Trigger handling, Objective discovery, prioritization,
planning, executor boundary, validation, checkpointing, recovery,
effect integrity, dormancy, wakeability, and autonomous lifecycle.

Adapt the implementation to this environment rather than assuming a
particular language, framework, repository structure, database,
orchestration system, or executor.

Run the applicable behavioral tests and bootstrap demonstrations defined
by URACE.md.

Repair failures until the implementation satisfies the applicable
invariants and success criteria.

Then report:
1. what was implemented;
2. how URACE is invoked;
3. where durable state lives;
4. which executors/capabilities are available;
5. which Authority and Intent were established;
6. which validation was completed;
7. any unresolved constraints or retained decisions;
8. how persistent autonomous operation is started.
```

The important technique is:

```text
SPECIFICATION
      │
      ▼
ENVIRONMENT-SPECIFIC
BOOTSTRAP
      │
      ▼
VALIDATED PERSISTENT
URACE IMPLEMENTATION
```

—not:

```text
URACE.md
   │
   ▼
generic fixed implementation
copied into every Product
```

URACE defines lifecycle semantics and boundaries.

The bootstrap executor determines the smallest appropriate implementation for the actual host environment.

---

## Bootstrap with One AI

The minimum configuration is intentionally simple:

```text
Target Product
     +
  URACE.md
     │
     ▼
Capable AI Executor
     │
     ▼
Bootstrap URACE
```

After bootstrap:

```text
Authoritative Source
        │
        ▼
      URACE
        │
        ▼
same AI or another executor
```

The AI used to bootstrap URACE does not become a permanent dependency.

---

## Bootstrap with an Orchestrator

An orchestrator MAY be used when stronger execution capacity is useful.

For example:

```text
             URACE.md
                 │
                 ▼
             OpenHands
                 │
        ┌────────┼────────┐
        ▼        ▼        ▼
      Codex    Claude   Gemini
                 │
                 ▼
           Bootstrap URACE
```

The orchestrator is still a bootstrap/execution mechanism, not URACE itself.

After bootstrap:

```text
                 URACE
                   │
                   ▼
             Executor Boundary
                   │
          ┌────────┼────────┐
          ▼        ▼        ▼
      OpenHands    AI      Tools
          │
      ┌───┼───┐
      ▼   ▼   ▼
     GPT Claude Gemini
```

URACE may use an orchestrator as one capability while remaining architecturally independent of it.

The number and choice of models are deployment decisions.

Multiple independent capable models can improve practical execution and cross-validation, but neither multiple models nor an orchestrator are architectural requirements.

**An orchestrator does not automatically create a privacy boundary.** If it forwards Product context to one or more external executors, the policies and configurations of those downstream systems may also matter.

---

## Bootstrap Validation

Bootstrap is **not complete when files have merely been generated**.

The resulting implementation must demonstrate the applicable requirements defined by `URACE.md`.

At minimum, bootstrap should establish and test the relevant equivalents of:

```text
Persistent lifecycle state
        ✓

Authoritative Intent
        ✓

Authority / delegation boundary
        ✓

Autonomous Objective discovery
        ✓

Priority / planning
        ✓

Replaceable executor boundary
        ✓

Evidence / Trigger handling
        ✓

Independent validation
        ✓

Checkpoint / recovery
        ✓

Fresh executor continuation
        ✓

Executor replacement
        ✓

Single-executor operation
        ✓

Interruption recovery
        ✓

Effect reconciliation where applicable
        ✓

Dormancy / wakeability
        ✓

Multi-cycle autonomous evolution
        ✓
```

A generated implementation that merely calls an AI repeatedly without preserving URACE's lifecycle semantics is **not** a successful bootstrap.

Likewise, an implementation that requires the user to continually choose Objectives, Plans, routes, executors, or ordinary course corrections has not implemented the intended autonomous boundary.

---

# Using URACE After Bootstrap

After bootstrap, stop treating `URACE.md` as the operational loop.

Use the generated URACE implementation.

The exact interface is environment-specific, but the canonical operating modes are conceptually:

```text
# Inspect current lifecycle state
urace --check

# Assess the Product and produce/revise the current Plan
# without intentionally mutating the Product
urace --plan

# Start persistent autonomous Product evolution
urace --autonomous
```

The bootstrap implementation MAY expose these through:

```text
CLI
API
service
daemon
worker
container
agent interface
scheduled runtime
serverless runtime
another suitable interface
```

The interface is replaceable.

The lifecycle semantics are not.

---

## 1. Establish the Destination and Authority

Before autonomous operation, URACE needs sufficient authoritative Intent and Authority.

This can be explicit:

```text
Build Product X.

Preserve requirements A and B.

You may autonomously change architecture, implementation,
Objectives, Plans, experiments, tools, and executors.

Do not change Product purpose X without my decision.
```

Or broader:

```text
Solve problem X.

Autonomously determine and evolve the Product realization
according to credible Evidence.

Preserve constraints A and B.
```

The first retains Product destination.

The second delegates more destination-setting Authority.

The governing rule remains:

```text
SOURCE
   │
   ▼
defines retained destination
and delegation
   │
   ▼
URACE
   │
   ▼
autonomously navigates
everything delegated
```

Authority should also govern disclosure boundaries where required.

For example:

```text
Do not disclose proprietary source code to external AI services.

Executor A may receive Product requirements but not customer data.

Only locally hosted executors may receive confidential Evidence.
```

URACE's executor selection and delegation should respect those constraints.

---

## 2. Inspect

Use the implementation's equivalent of:

```text
urace --check
```

to inspect lifecycle state.

A useful implementation should make relevant state observable, such as:

```text
governing Intent
Authority / delegation
current lifecycle state
current Objective
current Plan
important Evidence
material uncertainty
pending Operations
unresolved effects
validation state
checkpoint
capacity
dormancy / wake state
retained decisions
blockers
```

`--check` observes.

It does not transfer navigation responsibility back to the user.

---

## 3. Plan Without Product Mutation

Use:

```text
urace --plan
```

when you want URACE to reassess and expose its current intended navigation without intentionally executing Product mutations.

Conceptually:

```text
State + Intent + Authority + Evidence
                │
                ▼
             Assess
                │
                ▼
        Discover Objectives
                │
                ▼
            Prioritize
                │
                ▼
              Plan
                │
                ▼
             Report
```

The Plan remains URACE's current strategy rather than an immutable contract.

Later Evidence may justify replacing it.

---

## 4. Run Autonomous Product Evolution

Use:

```text
urace --autonomous
```

for persistent autonomous ownership.

The operating technique is:

```text
                ┌─────────────────────────┐
                │                         │
                ▼                         │
Observe → Assess → Discover → Prioritize  │
                         │                │
                         ▼                │
                        Plan              │
                         │                │
                         ▼                │
                Select Capability         │
                         │                │
                         ▼                │
                       Execute            │
                         │                │
                         ▼                │
                       Observe            │
                         │                │
                         ▼                │
                      Validate            │
                         │                │
                         ▼                │
                     Checkpoint           │
                         │                │
                         └────────────────┘
```

The user does not need to supply a new prompt for every cycle.

---

## 5. Let URACE Delegate Execution

Normal operation should look like:

```text
URACE
  │
  ├── identifies justified work
  ├── determines required capability
  ├── determines permitted data exposure
  ├── selects an authorized executor
  ├── minimizes/bounds context where required
  ├── delegates execution
  ├── receives result
  ├── observes actual effect
  ├── validates independently
  └── updates durable lifecycle state
```

rather than:

```text
User
  │
  ├── chooses next task
  ├── chooses executor
  ├── prompts executor
  ├── evaluates result
  ├── decides next task
  └── repeats
```

That distinction is the practical meaning of URACE owning navigation.

---

## 6. Replace Executors Freely

A normal executor handoff is:

```text
Executor A
    │
    ▼
bounded work
    │
    ▼
URACE validates
    │
    ▼
durable checkpoint
    │
    ▼
Executor A disappears
    │
    ▼
Executor B
    │
    ▼
continues from URACE state
```

Executor B should receive the bounded context required for its Operation rather than depending on Executor A's conversation history.

Executor replacement must not silently expand disclosure Authority. A replacement executor may have different privacy, retention, deployment, or data-use properties.

This is one of the core reasons URACE separates lifecycle ownership from execution.

---

## 7. Intervene Without Becoming the Pilot

The authoritative source may inspect, constrain, redirect, pause, revoke delegation, change retained Intent, change disclosure policy, or stop the lifecycle.

For example:

```text
Change the retained destination.

Add a HARD constraint.

Revoke permission to deploy.

Do not send proprietary data to external executors.

Allow Executor B to receive source code.

Delegate Product-direction changes.

Pause autonomous execution.

Resume autonomous execution.

Stop persistent ownership.
```

Such intervention updates the authoritative lifecycle context.

It does not imply that normal navigation becomes manual.

```text
AUTHORITATIVE CHANGE
        │
        ▼
URACE REASSESSMENT
        │
        ▼
AUTONOMOUS NAVIGATION
RESUMES WITHIN NEW BOUNDARY
```

---

## 8. Dormancy Is Normal

`--autonomous` does not require constant mutation or constant AI inference.

When no sufficiently valuable justified authorized action exists:

```text
ACTIVE
  │
  ▼
NO ACTION JUSTIFIED NOW
  │
  ▼
DORMANT
  │
  ▼
wait / discover / schedule / observe
  │
  ▼
meaningful Trigger
  │
  ▼
ASSESS
  │
  ▼
ACTIVE
```

A correct implementation may release runtime resources during dormancy if another durable mechanism owns reactivation.

Persistent autonomy means **persistent lifecycle ownership**, not an infinite busy loop.

---

## 9. Recover Instead of Starting Over

After interruption:

```text
START
  │
  ▼
LOAD DURABLE STATE
  │
  ▼
RESTORE AUTHORITY + INTENT
  │
  ▼
RECONCILE PENDING EFFECTS
  │
  ▼
RESTORE OBJECTIVE / PLAN
  │
  ▼
REASSESS CURRENT REALITY
  │
  ▼
CONTINUE
```

The user should not have to reconstruct the Product's lifecycle from chat history.

---

## 10. Re-Bootstrap Only When Appropriate

Normal use does **not** require repeatedly bootstrapping URACE.

```text
BOOTSTRAP ONCE
     │
     ▼
OPERATE URACE
     │
     ▼
EVOLVE THROUGH
NORMAL LIFECYCLE
```

Re-bootstrap may be appropriate when intentionally creating a new URACE implementation, migrating to a fundamentally different host environment, recovering from loss of the implementation itself, or deliberately rebuilding from the specification.

Ordinary Product evolution belongs to the running URACE lifecycle.

---

## Replaceable Intelligence

URACE separates durable lifecycle ownership from bounded intelligence.

```text
                  URACE
                    │
        ┌───────────┼───────────┐
        ▼           ▼           ▼
      GPT         Claude      Gemini
        │           │           │
        └───────────┼───────────┘
                    ▼
              other executors
```

An executor can disappear and another can continue from durable Product state.

A new executor should not need the complete conversational history of its predecessor.

URACE preserves the lifecycle state required for continuity.

**Replaceable does not mean interchangeable from a privacy perspective.**

Different executors can have different data-handling, retention, training/model-improvement, security, contractual, and deployment properties.

Executor selection therefore may be constrained by both:

```text
CAPABILITY
    +
AUTHORITY
    +
DATA POLICY
    +
ENVIRONMENTAL CONSTRAINTS
```

not capability alone.

---

## Proprietary Intelligence Can Remain Proprietary

URACE can serve as the persistent Product-management and autonomous lifecycle layer around Products built using proprietary intelligence.

The **URACE idea and lifecycle architecture can remain open and editable** while Product-specific intelligence remains its own.

That may include:

- Product context;
- accumulated Evidence;
- proprietary data;
- decisions;
- Objectives;
- validation history;
- implementation;
- business logic;
- specialized models;
- integrations;
- other Product-specific knowledge.

This is an **architectural separation**, not a guarantee about third-party data handling.

If proprietary intelligence is transmitted to an external AI executor, that executor **may** retain, process, review, or use the information for model improvement/training depending on the provider, product, agreement, settings, and deployment configuration.

Accordingly:

> **Open URACE does not require open Product intelligence—but preserving proprietary intelligence also requires choosing and configuring executors whose data practices satisfy the Product's requirements.**

Where confidentiality matters, treat executor data access as part of Authority and policy rather than assuming that every capable executor may receive every part of Product state.

---

## The Boundary

```text
┌────────────────────────────────────┐
│        AUTHORITATIVE SOURCE        │
│                                    │
│ Retained Intent                    │
│ Authority · Delegation             │
│ Data / Disclosure Constraints      │
└─────────────────┬──────────────────┘
                  │
                  ▼
┌────────────────────────────────────┐
│               URACE                │
│                                    │
│ Intent · Authority · State         │
│ Evidence · Triggers                │
│ Assessment · Objectives            │
│ Priority · Plans                   │
│ Decisions · Operations             │
│ Executor / Disclosure Boundaries   │
│ Validation · Checkpoints           │
│ Recovery · Dormancy · Liveness     │
│                                    │
│      Autonomous navigation         │
└──────────────┬───────────────▲─────┘
               │               │
               ▼               │
┌──────────────────────────┐   │
│ Intelligence / Execution │   │ Evidence /
│                          │   │ Reality
│ GPT · Claude · Gemini    │   │
│ OpenHands · Agents       │   │
│ Tools · APIs             │   │
│ Local / Future Executors │   │
│                          │   │
│ External data practices  │   │
│ may independently apply  │   │
└──────────────────────────┘   │
                               │
              ┌────────────────┴───────┐
              │ Product · Users        │
              │ Customers · Market     │
              │ Environment            │
              └────────────────────────┘
```

The boundary is intentionally narrow:

> **URACE owns persistent autonomous Product navigation under authoritative Intent and bounded Authority.**

It does not need to own the intelligence doing the work.

It does not need to own the orchestrator coordinating executors.

It does not need to own the systems producing external Evidence.

It does not need to own the mechanisms implementing persistence, scheduling, wake-up, identity, authorization, or execution.

It does not control the independent data practices of external executors merely by integrating with them.

It owns the durable lifecycle semantics that allow those mechanisms to remain replaceable and allows Authority and policy to constrain which mechanisms may receive which information.

---

## In One Sentence

> **You choose the destination you want to retain; bootstrap URACE from `URACE.md` with a suitable executor, then URACE persistently drives the Product toward that destination—autonomously deciding everything you delegate, adapting to Evidence, respecting Authority and disclosure constraints, and using replaceable intelligence and execution underneath it.**

Models improve. Agents change. Orchestrators come and go.

**The autonomous Product lifecycle remains.**

**The idea is open and editable. The intelligence built around each Product can remain its own—subject to the data practices of the executors you authorize to access it.**

## License

MIT License — see `LICENSE`.