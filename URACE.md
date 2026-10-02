# URACE — Universal Recursive Autonomous Co-Founder Engine

You are the Lead Systems Architect and Bootstrap Executor for this repository.

Your task is to bootstrap URACE.

URACE is a self-contained, executor-agnostic persistent autonomous product-evolution control plane.

Its unique responsibility is to preserve and govern a continuous product-development lifecycle across otherwise bounded, replaceable and potentially stateless intelligence/execution systems.

URACE MUST NOT become another coding agent, LLM framework, agent runtime, IDE agent, RAG platform, workflow engine, model provider, sandbox, or replacement for external intelligence.

Its purpose is:

> Continuously evolve a Product by preserving durable intent, state, evidence, decisions, policy, validation, recovery and history; translating justified Product, user, customer, market and environmental evidence into requirements and objectives; delegating intelligence-intensive or execution-intensive operations to replaceable executors; independently evaluating their results; checkpointing accepted increments; and repeating while further autonomous action remains sufficiently justified.

The primary architectural invariant is:

> URACE owns the autonomous Product lifecycle. Replaceable executors supply whatever intelligence or execution is required to advance it.

---

# 1. Unique Position in the Stack

URACE occupies a layer distinct from agents, orchestrators, models, development tools and infrastructure.

```text
          USERS / CUSTOMERS / MARKET / ENVIRONMENT
                         │
                         ▼
                 PRODUCT EVIDENCE
                         │
                         ▼
              ┌─────────────────────┐
              │        URACE        │
              │                     │
              │ PRODUCT LIFECYCLE   │
              │                     │
              │ Intent              │
              │ State               │
              │ Evidence            │
              │ Requirements        │
              │ Policy              │
              │ Autonomy            │
              │ History             │
              │ Validation          │
              │ Recovery            │
              │ Checkpoints         │
              └──────────┬──────────┘
                         │
                GENERIC EXECUTION
                    BOUNDARY
                         │
       ┌─────────────────┼──────────────────┐
       ▼                 ▼                  ▼
    ONE AI          ORCHESTRATOR       DETERMINISTIC
                       / AGENT              TOOL
       │                 │                  │
       ▼                 ▼                  ▼
 Claude/Codex/...    OpenHands/...      CLI/API/etc.
                         │
                       1..N AI
```

URACE MUST remain useful when any executor shown above is replaced, unavailable, interrupted or later restored.

The minimum useful intelligent configuration is:

```text
URACE
  │
  ▼
ONE capable AI
```

An external orchestrator is OPTIONAL.

Multiple AIs are OPTIONAL.

OpenHands is OPTIONAL.

No executor implementation is part of URACE's identity.

Executor availability affects current execution capacity.

It MUST NOT define whether the autonomous Product lifecycle itself remains alive.

---

# 2. Self-Contained Control Plane

URACE MUST contain everything required to preserve its own lifecycle semantics.

URACE owns:

- Product intent;
- durable Product state;
- autonomous lifecycle state;
- evidence references and lineage;
- assumptions;
- decisions;
- requirement/objective history;
- current objective;
- execution history;
- validation policy;
- safety policy;
- constraint policy;
- resource policy;
- budget state;
- schedule state;
- executor capability descriptions;
- executor availability observations;
- checkpoint history;
- recovery state;
- interruption state;
- capacity state;
- completion/readiness state;
- autonomous liveness state;
- relevant wake/resume conditions where applicable;
- acceptance/rejection of candidate increments.

External executors MAY provide:

- reasoning;
- research;
- market analysis;
- user/customer analysis;
- planning;
- requirement formulation;
- implementation;
- code modification;
- content generation;
- debugging;
- analysis;
- tool operation;
- architecture reasoning;
- Product reasoning;
- testing assistance;
- repair reasoning;
- bounded Product/environment discovery;
- trigger-relevance assistance where deterministic evaluation is insufficient.

URACE MUST remain authoritative over lifecycle state regardless of executor behavior or availability.

---

# 2A. Core Invariants and Variants

URACE MUST distinguish between:

```text
INVARIANTS
    │
    ▼
properties required for URACE
to remain URACE

POLICIES / CONSTRAINTS
    │
    ▼
rules governing a particular
Product or deployment

VARIANTS
    │
    ▼
replaceable strategies,
implementations and mechanisms
```

The invariant set SHOULD remain small.

A capability or implementation detail MUST NOT become an invariant merely because one implementation currently uses it.

## Core Invariants

### I1 — Lifecycle Ownership

URACE owns the authoritative persistent Product lifecycle state.

### I2 — Executor Replaceability

Lifecycle correctness MUST NOT depend on one executor, model, orchestrator, agent, vendor or private executor context.

Executor unavailability MAY prevent a particular operation from executing.

It MUST NOT by itself terminate, complete or invalidate the autonomous lifecycle.

### I3 — Intent Authority

Product Intent is a first-class lifecycle primitive and the durable normative reference for what the Product is meant to achieve, preserve or become.

Intent MUST remain distinguishable from objectives, executor suggestions, inferred opportunities and implementation strategies.

Objectives and Product-value judgments MUST ultimately remain attributable to applicable Product Intent rather than becoming autonomous ends in themselves.

### I4 — Evidence Traceability

Evidence is a first-class lifecycle primitive.

Material autonomous decisions MUST remain attributable to Product Intent, evidence, constraints, risk, observations, policy or sufficiently justified opportunity.

Evidence used to justify lifecycle decisions MUST preserve sufficient provenance and lineage to distinguish what was observed from what was inferred, assumed, hypothesized or decided.

### I5 — Justified Evolution

Requirements and objectives MUST exist because sufficiently valuable Product gaps justify them relative to applicable Intent.

URACE MUST NOT manufacture work merely to sustain autonomous activity.

### I6 — Independent Acceptance

Executor output MUST NOT be accepted solely because the executor claims success.

Acceptance belongs to URACE policy and applicable validation.

### I7 — Durable Continuity

Accepted state and sufficient lifecycle context MUST survive executor replacement, executor unavailability, interruption and process restart.

### I8 — Lifecycle Liveness

While autonomous operation remains enabled, URACE MUST preserve a viable path from any non-terminal dormant lifecycle state back to assessment when a Meaningful Trigger occurs.

Persistence alone does not satisfy autonomous liveness.

Conceptually:

```text
DURABILITY
    =
state survives runtime termination

LIVENESS
    =
the autonomous lifecycle remains
capable of progressing

WAKEABILITY
    =
a dormant lifecycle can become
active when a Meaningful Trigger occurs
```

A running autonomous runtime MUST NOT terminate merely because:

- the lifecycle enters `IDLE`;
- the lifecycle enters `WAITING_FOR_CAPACITY`;
- no executor is currently available;
- an executor reports quota exhaustion;
- a particular executor disconnects;
- no objective is immediately executable;
- another resumable dormant state is reached.

Termination is permitted only when an equivalent durable wake/resume path exists, the invocation contract explicitly permits bounded termination, the user explicitly stops/pauses autonomous operation, or policy requires termination.

Executor availability MUST therefore influence execution scheduling rather than autonomous lifecycle existence.

The mechanism used to preserve liveness remains a variant.

URACE MUST NOT require a permanent process, permanent event loop, particular watcher, scheduler, queue, alarm, daemon, operating-system service, cloud primitive or orchestration runtime.

### I9 — Meaningful Reactivation

A dormant autonomous lifecycle MUST be reactivated by a Meaningful Trigger rather than by arbitrary activity.

A Meaningful Trigger is:

> A sufficiently credible observation, event, condition, state transition, scheduled condition, authoritative input, relevant evidence change or potentially material change discovered anywhere within or affecting the governed Product/project/lifecycle scope that could materially change the result of the most recent lifecycle assessment relative to Product Intent, policy, constraints, capacity, readiness, risk or expected Product value.

Meaningful Trigger scope is intentionally open-ended.

A potentially meaningful change MAY occur at any relevant Product/project scope or abstraction level, including but not limited to:

```text
Product
Product Intent
goal
desired outcome
protected property

requirement
objective
strategy
plan

artifact
file
configuration
dependency
interface
contract
data

evidence
assumption
hypothesis
observation

validation
quality
readiness
risk
blocker

policy
constraint
budget
schedule

environment
runtime
infrastructure
external system

executor capability
executor availability
capacity
quota

user
customer
market
external condition

URACE lifecycle machinery itself

relationships among any of the above

newly discoverable facts or conditions
not previously known or enumerated
```

This list is illustrative.

It MUST NOT become a closed trigger taxonomy.

A change does NOT need to belong to a predefined trigger category.

A trigger does NOT need to prove that Product mutation is required.

It only needs to justify reassessment.

Therefore:

```text
MEANINGFUL TRIGGER
        ≠
NEW OBJECTIVE
```

and:

```text
MEANINGFUL TRIGGER
        ≠
MANDATORY PRODUCT CHANGE
```

Instead:

```text
MEANINGFUL TRIGGER
        │
        ▼
      ASSESS
        │
   ┌────┴─────┐
   ▼          ▼
JUSTIFIED    NO MATERIAL
ACTION       CHANGE
   │          │
   ▼          ▼
ACTIVE      IDLE / WAIT
```

URACE owns the semantic determination of whether an observed or discovered condition is relevant enough to trigger reassessment.

The mechanism that detects, discovers, transports or delivers that condition remains a variant.

### I10 — Discovery Beyond Known Events

URACE MUST NOT rely exclusively on predefined event sources, watchers, webhooks, schedules or known trigger conditions.

Some material Product/project changes cannot be predicted or directly subscribed to.

While autonomous operation remains enabled, URACE SHOULD therefore support bounded periodic discovery/reassessment attempts where appropriate.

These attempts MAY use:

```text
deterministic inspection
state reconciliation
Product discovery
environment inspection
executor-assisted inspection
executor-assisted reasoning
external queries
other appropriate capabilities
```

A periodic attempt is a discovery mechanism.

It is NOT inherently a Meaningful Trigger.

Conceptually:

```text
PERIODIC DISCOVERY ATTEMPT
          │
          ▼
INSPECT PRODUCT / PROJECT /
LIFECYCLE / ENVIRONMENT
          │
          ▼
MATERIAL CHANGE DISCOVERED?
      ┌───┴────┐
      ▼        ▼
     NO       YES
      │        │
      ▼        ▼
  DORMANT   MEANINGFUL
             TRIGGER
                │
                ▼
             ASSESS
```

Periodic discovery frequency MUST be bounded and policy-sensitive.

It SHOULD consider:

```text
Product characteristics
known rate of external change
risk
cost
budget
capacity
executor availability
executor cost
schedule
previous discovery results
known trigger coverage
urgency
environment capabilities
```

Periodic discovery MUST NOT become continuous expensive polling merely to keep autonomous mode active.

When deterministic observation is sufficient, URACE SHOULD avoid unnecessary executor invocation.

When executor reasoning is useful, URACE MAY periodically attempt to use a compatible executor.

Executor unavailability during such an attempt MUST NOT terminate the autonomous lifecycle.

It changes only what discovery or execution can currently occur.

### I11 — Hard-Boundary Respect

Autonomous execution MUST NOT knowingly violate applicable HARD constraints.

### I12 — Convergence

URACE MUST neither:

```text
stop while material justified work remains
```

nor:

```text
continue active execution merely because
further activity is possible
```

The lifecycle MUST be capable of converging to `IDLE` without losing autonomous liveness.

### I13 — Agnosticism

Core lifecycle semantics MUST NOT fundamentally depend on a specific:

- executor;
- AI;
- model;
- orchestrator;
- programming language;
- platform;
- repository structure;
- directory structure;
- file format;
- version-control system;
- scheduler;
- wake mechanism;
- trigger-detection mechanism;
- periodic discovery mechanism;
- persistence technology;
- customer journey;
- business model;
- Product-value metric.

### I14 — Intent-Relative Readiness

URACE MUST drive a Product toward the highest justified readiness state implied by its Intent, evidence, constraints and environment.

No single universal definition of Product readiness or Product value is valid for every Product.

## Variants

The following SHOULD normally remain replaceable variants rather than URACE invariants:

```text
executor topology
number of executors
AI provider
AI model
orchestrator
reasoning strategy

evidence sources
evidence storage representation
market-analysis technique
user/customer-research technique
requirement-generation technique
validation mechanisms

Product-value dimensions
customer journey
business model
market strategy
acquisition strategy
conversion strategy
retention strategy
pricing strategy

Product structure
repository structure
file/folder layout
programming language
platform
runtime

persistence implementation
checkpoint mechanism
scheduler
wake mechanism
trigger source
trigger-detection mechanism
trigger transport
periodic discovery mechanism
periodic discovery frequency
watch mechanism
event source
runtime-liveness mechanism

budget representation
soft constraints
quality thresholds
readiness criteria
retry limits

research methodology
implementation methodology
deployment strategy
```

A useful classification test is:

> If changing a mechanism, strategy or Product-value dimension changes what URACE fundamentally is, it may belong to the invariant layer. If it can change while the Intent → evidence → justified gap → requirement/objective → execution → validation → checkpoint lifecycle remains correct and autonomously resumable, it SHOULD remain a variant.

The governing relationship is:

```text
               INTENT
                  │
          establishes direction
                  │
                  ▼
              EVIDENCE
                  │
        establishes knowledge
                  │
                  ▼
              INVARIANTS
                  │
          define URACE identity
                  │
                  ▼
         POLICY / CONSTRAINTS
                  │
       govern this Product
                  │
                  ▼
              VARIANTS
                  │
       choose mechanisms
                  │
                  ▼
              EXECUTION
```

Intent and Evidence are first-class lifecycle primitives.

Specific Product-value dimensions are not.

Lifecycle liveness, open-ended change awareness and meaningful reactivation are invariant semantics.

Their mechanisms are not.

---

# 3. Universal Agnosticism

URACE MUST NOT assume a specific:

- AI provider;
- AI model;
- number of AIs;
- agent framework;
- orchestrator;
- repository host;
- version-control system;
- operating system;
- cloud provider;
- runtime;
- programming language;
- build system;
- package manager;
- database;
- deployment platform;
- application architecture;
- project type;
- source-code structure;
- repository structure;
- directory structure;
- folder naming convention;
- workspace layout;
- artifact hierarchy;
- persistence layout;
- scheduler;
- wake mechanism;
- trigger source;
- trigger-delivery mechanism;
- periodic discovery mechanism;
- daemon model;
- event-loop model;
- budget representation;
- file format;
- file extension;
- artifact format;
- testing framework;
- IDE;
- editor;
- business model;
- customer lifecycle;
- Product-value metric.

The architecture MUST support:

> universal file-base, project-type, platform, structure and programming-language agnosticism.

A project MAY be:

- software;
- documentation;
- configuration;
- infrastructure;
- data;
- research;
- design artifacts;
- mixed artifacts;
- another structured or file-based Product.

URACE core MUST reason in terms of generic:

```text
Product
Intent
Artifact
State
Evidence
Requirement
Objective
Operation
Executor
Observation
Validation
Checkpoint
Policy
Constraint
Capacity
Budget
Schedule
```

rather than language-specific, framework-specific, runtime-specific, business-model-specific or metric-specific concepts.

Existing Product structure is evidence about the Product.

It is NOT a URACE lifecycle primitive.

URACE SHOULD discover and preserve existing structural conventions where practical.

A Product MUST NOT be reorganized merely to satisfy a URACE-preferred physical layout.

---

# 4. Product

A Product is the persistent object URACE is attempting to advance.

Conceptually:

```text
Product {
    identity
    intent
    constraints
    artifacts
    evidence
    state
    history
}
```

A Product MUST NOT require source code.

Examples MAY include:

```text
software repository
website
API
library
CLI
mobile application
infrastructure project
documentation set
research project
data pipeline
configuration system
mixed project
```

URACE MUST NOT encode these examples as closed categories.

Product readiness MUST be derived from Product Intent rather than from one universal definition.

Examples:

```text
commercial Product
    → market/user/customer/Product readiness

internal tool
    → operational/user readiness

library
    → API/ecosystem readiness

research Product
    → evidentiary/research readiness

infrastructure
    → operational/reliability readiness
```

These are examples, not closed readiness categories.

Where a Product serves users or customers, its applicable value MAY include outcomes such as:

```text
acquisition
conversion
activation
adoption
engagement
retention
loyalty

satisfaction
trust
usability
accessibility
clarity

reduced friction
reduced cognitive load
reduced customer effort
reduced customer cost

increased customer productivity
increased realized customer value
successful customer outcomes

reliability
safety
other Intent-relevant outcomes
```

These are possible Product-value dimensions.

They are NOT universal objectives, mandatory metrics, a fixed customer journey or first-class URACE primitives.

Their relevance MUST be derived from Product Intent and available evidence.

---

# 4A. Intent

Intent is a first-class lifecycle primitive.

It represents the durable normative direction of the Product.

Conceptually:

```text
Intent {
    purpose
    desiredOutcomes?
    beneficiaries?
    protectedProperties?
    successConditions?
    boundaries?
    provenance?
}
```

This structure is conceptual.

An implementation MAY represent Intent more simply.

Intent MUST NOT require every optional field.

Intent answers questions such as:

```text
What is this Product for?

Who or what is it intended to benefit?

What outcomes matter?

What properties must be preserved?

What would meaningful progress mean?

What would sufficiently ready mean?
```

Intent MUST remain distinguishable from:

```text
Objective
Requirement
Evidence
Constraint
Strategy
Implementation
Metric
Executor recommendation
```

Conceptually:

```text
INTENT
  =
durable direction

EVIDENCE
  =
what is known or observed

VALUE
  =
expected or realized benefit
relative to Intent

REQUIREMENT
  =
a justified Product need or gap

OBJECTIVE
  =
a bounded action target

STRATEGY
  =
a possible way to advance

IMPLEMENTATION
  =
the concrete realization
```

An objective MAY change without changing Product Intent.

A strategy MAY change without changing Product Intent.

An executor MAY change without changing Product Intent.

A Product-value metric MAY change without changing Product Intent.

Intent itself MAY evolve when sufficiently justified by authoritative input, evidence, Product evolution or applicable policy.

However, an executor MUST NOT silently redefine Product Intent merely because it identifies another possible objective or optimization target.

Material Intent changes SHOULD preserve provenance and history.

A material Intent change is itself within Meaningful Trigger scope because it can redefine Product direction, value and readiness.

---

# 5. Artifact

An Artifact is any addressable Product resource.

Conceptually:

```text
Artifact {
    identity
    location
    kind?
    metadata?
}
```

URACE MUST NOT require an artifact to be:

```text
source code
text
UTF-8
a local file
Git tracked
parseable by an AST
located in a predefined directory
```

Artifact interpretation SHOULD be delegated to executors or external tools capable of understanding it.

Unknown artifact types MUST degrade gracefully rather than invalidate the Product.

---

# 6. Executor Boundary

All external intelligence and execution MUST cross a generic boundary.

Conceptually:

```text
Executor {
    capabilities()
    execute(operation, context, policy)
}
```

Normalized result:

```text
ExecutionResult {
    status
    observations
    outputs
    evidence
    assumptions
    diagnostics
    metadata
}
```

The contract MUST NOT assume the executor is an AI.

Valid executors MAY include:

```text
DirectAIExecutor
OrchestratorExecutor
AgentExecutor
ProcessExecutor
APIExecutor
HumanExecutor
FutureExecutor
```

These are examples, not mandatory closed types.

Executor availability MUST be treated as a dynamic capacity condition.

Conceptually:

```text
EXECUTOR
   │
   ├──── AVAILABLE
   │
   ├──── TEMPORARILY UNAVAILABLE
   │
   └──── UNKNOWN / FAILED
```

None of these states independently defines Product completion or autonomous lifecycle termination.

---

# 7. Executor Cardinality

URACE MUST support:

```text
1 executor
1 AI
1 orchestrator
1 orchestrator + N AIs
N independent executors
AI + deterministic tools
future combinations
```

URACE MUST NOT require consensus, voting, multi-agent conversation or model routing.

A single capable AI MUST be sufficient to operate the intelligent portion of the lifecycle.

Additional executors MAY improve capability without changing URACE's lifecycle semantics.

Zero currently available intelligent executors MAY temporarily occur.

That condition means intelligent execution capacity is currently unavailable.

It MUST NOT mean:

```text
Product complete
URACE complete
autonomous lifecycle terminated
```

---

# 8. Capabilities Instead of Brands

URACE MUST request capabilities, not named products.

Examples:

```text
reason
research
analyze-market
analyze-users
analyze-customers
derive-requirements
plan
modify
execute
inspect
test
repair
review
discover-change
```

An operation MAY declare requirements:

```text
Operation {
    objective
    requiredCapabilities
    optionalCapabilities
    context
    constraints
}
```

URACE determines whether a compatible executor is available.

Do NOT encode:

```text
ask Claude
use OpenHands
send to Codex
```

into core lifecycle semantics.

Adapters MAY map generic capabilities onto particular systems.

---

# 9. Graceful Capability Degradation

Missing optional capability MUST NOT unnecessarily break URACE.

Example:

If external research is available:

```text
ASSESS
  ↓
RESEARCH
  ↓
EVIDENCE
  ↓
DECIDE
```

If it is unavailable:

```text
ASSESS
  ↓
USE EXISTING EVIDENCE
  ↓
MARK UNKNOWN INFORMATION
  ↓
DECIDE IF JUSTIFIED
```

Executors MUST distinguish where appropriate:

```text
OBSERVED
INFERRED
HYPOTHESIZED
UNKNOWN
```

URACE MUST preserve these distinctions.

Missing capability MUST NOT be confused with completion.

Missing executor availability MUST NOT be confused with lifecycle termination.

Where an unavailable executor is required for current progress:

```text
JUSTIFIED WORK
      │
      ▼
REQUIRED CAPABILITY
      │
      ▼
NO COMPATIBLE EXECUTOR
CURRENTLY AVAILABLE
      │
      ▼
WAITING_FOR_CAPACITY
      │
      ▼
PRESERVE AUTONOMOUS LIVENESS
```

---

# 10. Operating Modes

URACE MUST support at minimum:

## `--plan`

Assess and propose work without mutating the Product.

## `--check`

Inspect current Intent, lifecycle, validation, evidence, capacity, constraints, budgets, schedules, objectives, checkpoints, completion readiness, autonomous liveness, pending trigger conditions and recovery state.

## `--autonomous`

Run persistent autonomous Product evolution.

Unless explicitly configured as bounded/one-shot, `--autonomous` denotes continuing autonomous lifecycle ownership rather than merely "execute cycles until the current runtime has nothing immediately executable."

The architecture MAY later expose additional modes without changing core semantics.

---

# 11. Autonomous Lifecycle

`--autonomous` is the defining behavior.

```text
LOAD PRODUCT STATE + INTENT
        │
        ▼
LOAD AVAILABLE EVIDENCE
        │
        ▼
DISCOVER / RECONCILE
RELEVANT CURRENT STATE
        │
        ▼
ASSESS
        │
        ▼
IDENTIFY HIGHEST-VALUE
JUSTIFIED GAP
        │
   ┌────┴──────────────────────────┐
   │                               │
 gap exists                    none found
   │                               │
   ▼                               ▼
FORMULATE JUSTIFIED           COMPLETION /
REQUIREMENT / OBJECTIVE       IDLE ASSESSMENT
   │                               │
   ▼                         ┌─────┴─────┐
SELECT REQUIRED              ▼           ▼
CAPABILITIES              NOT READY     READY
   │                         │           │
   ▼                         ▼           ▼
SELECT COMPATIBLE          REASSESS     IDLE
EXECUTOR(S)                  │           │
   │                         │           ▼
   │ unavailable             │     IDENTIFY RELEVANT
   ▼                         │     TRIGGER CONDITIONS
WAITING_FOR_CAPACITY         │           │
   │                         │           ▼
   ▼                         │       WAIT / DORMANT
PRESERVE LIVENESS            │           │
   │                         │           ▼
   │                         │    EVENT / DISCOVERY /
   │                         │    PERIODIC RE-TRY
   │                         │           │
   └──────────────┐          │           ▼
                  │          │    MEANINGFUL TRIGGER
                  │          │           │
                  ▼          │           ▼
          EXECUTOR AVAILABLE │         ASSESS
                  │          │
                  ▼          │
              REASSESS       │
                  │          │
                  └──────────┘
   │
   ▼
REASON / RESEARCH / PLAN
   │
   ▼
IMPLEMENT
   │
   ▼
OBSERVE
   │
   ▼
VALIDATE
   │
┌──┴──┐
▼     ▼
PASS  FAIL
│      │
│   REPAIR /
│   REASSESS
│      │
▼      │
CHECKPOINT ◄┘
   │
   ▼
UPDATE DURABLE STATE
   │
   ▼
UPDATE EVIDENCE
   │
   ▼
FRESH ASSESSMENT CYCLE
   │
   └──────────────► repeat while justified
```

The URACE lifecycle persists independently from individual executor lifetimes and availability.

A fresh cycle MUST NOT imply that another mutation is necessarily required.

There is no fixed number of cycles.

URACE MAY execute as many successive cycles as remain justified.

A cycle MAY legitimately converge to `WAITING`, `BLOCKED`, `PAUSED` or `IDLE`.

Such convergence MUST NOT accidentally destroy autonomous liveness.

Dormant autonomous states SHOULD preserve enough information to identify the kinds of change that could justify reassessment without requiring exhaustive prediction of every possible future event.

When direct event-driven coverage is incomplete, bounded periodic discovery SHOULD provide a fallback path for discovering otherwise unobserved material change.

---

# 12. Continuous Means Lifecycle Continuity

Continuous autonomy MUST NOT require:

- one permanent process;
- one permanent AI conversation;
- one permanent agent;
- one permanent model;
- one permanent machine;
- one permanent orchestrator;
- one permanent event loop;
- continuous mutation;
- continuous resource consumption.

Instead:

```text
URACE STATE
    │
    ▼
CURRENT JUSTIFIED CYCLE
    │
    ▼
checkpoint
    │
    ▼
URACE STATE
    │
    ├────────────► NEXT JUSTIFIED CYCLE
    │                    │
    │                    └────► repeat while justified
    │
    └────────────► IDLE / WAIT
                         │
                         ▼
                 PRESERVE LIVENESS
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
       EVENT         KNOWN TIME      PERIODIC
       SOURCE         CONDITION      DISCOVERY
          │              │              │
          └──────────────┼──────────────┘
                         ▼
                 CANDIDATE CHANGE
                         │
                         ▼
                 MEANINGFUL TRIGGER
                         │
                         ▼
                      ASSESS
```

Executor sessions SHOULD be considered replaceable.

Durable continuity belongs to URACE.

Continuous lifecycle ownership does not require continuous active execution.

However:

```text
PERSISTENCE
     ≠
AUTONOMOUS LIVENESS
```

Persisting state and terminating every active runtime without any mechanism capable of reactivating the lifecycle does not satisfy persistent autonomous operation.

A deployment MAY preserve liveness using any suitable mechanism, including conceptually:

```text
long-lived process
event loop
timer
watcher
scheduler
alarm
queue
webhook
event bus
orchestrator callback
operating-system service
serverless invocation
periodic reconciliation
periodic executor-assisted discovery
platform-native wake mechanism
future equivalent mechanism
```

These are examples only.

No mechanism above is mandatory.

A runtime MAY become dormant or terminate after persisting `IDLE`, `WAITING_FOR_CAPACITY`, or another resumable state only when autonomous reactivation remains viable.

If no durable external wake/resume path exists, the currently responsible autonomous runtime MUST remain capable of waiting efficiently for a relevant trigger rather than silently ending autonomous operation.

Executor unavailability does not alter this rule.

If all executors are unavailable, the lifecycle waits, observes or periodically retries according to policy.

It does not terminate merely because executor capacity is currently zero.

---

# 12A. Meaningful Triggers

Meaningful Trigger is a lifecycle concept used to decide when a dormant autonomous Product should be reassessed.

It is NOT required to be a separate first-class persistent object, event framework or trigger-processing subsystem.

Its defining semantic is:

> A Meaningful Trigger is a sufficiently credible observation, event, condition, state transition, scheduled condition, authoritative input, relevant evidence change or potentially material change discovered anywhere within or affecting the governed Product/project/lifecycle scope that could materially change the result of the most recent lifecycle assessment relative to Product Intent, policy, constraints, capacity, readiness, risk or expected Product value.

The key word is **could**.

A trigger does not need to establish that a change is required.

That determination belongs to reassessment.

Therefore:

```text
TRIGGER
   │
   ▼
REASSESS
   │
   ├────► justified gap → objective
   │
   ├────► changed wait/block condition → resume
   │
   ├────► changed readiness/evidence → evaluate
   │
   └────► no material lifecycle change → return to dormant state
```

## Trigger Scope

Meaningful Trigger scope is open-ended across the entire governed Product/project/lifecycle.

A candidate change MAY occur at any relevant scope or abstraction level.

Examples include, but are not limited to:

```text
Product identity
Product Intent
purpose
goal
desired outcome
success condition
protected property

requirement
objective
strategy
plan
priority

artifact
file
directory
configuration
dependency
interface
contract
schema
data
documentation

evidence
assumption
inference
hypothesis
observation
decision

validation
quality
readiness
risk
blocker

policy
constraint
budget
schedule
deadline

environment
runtime
platform
infrastructure
external system

executor capability
executor availability
executor restoration
quota
capacity

user condition
customer condition
market condition
external evidence

URACE lifecycle state
URACE lifecycle machinery

relationship or dependency
between any relevant concepts

newly discoverable facts
not known during prior assessment
```

The list MUST remain illustrative.

URACE MUST NOT interpret it as a closed ontology.

A change at a high-level scope such as Intent or Product goal MAY be meaningful.

A change at a low-level scope such as one artifact, dependency or environment condition MAY also be meaningful.

Meaningfulness depends on potential lifecycle impact, not abstraction level.

## Trigger Relevance

A candidate trigger is meaningful when there is a reasonable causal path by which it could change one or more lifecycle conclusions concerning:

```text
Product Intent
Product state
available evidence
assumptions
risk
constraints
capacity
budget
schedule
validation
readiness
external dependencies
expected Product value
available executor capability
available executor capacity
```

Examples MAY include:

```text
Product artifact changed
new Product version or state observed

Product Intent or goal changed

new user/customer/market evidence arrived
new analytics or experiment result arrived
new runtime observation occurred

required executor became available
executor capabilities changed
rate limit reset
quota renewed
credentials became available
external service recovered

approval was granted or denied
authoritative human input arrived

deadline or earliest-start condition became applicable
scheduled reassessment time arrived
cooldown expired

external dependency changed
previous blocker cleared
constraint changed
policy changed

validation environment became available
new validation result arrived

new evidence materially challenges an assumption
material risk changed

URACE limitation became observable
or materially relevant
```

These examples are illustrative, not a closed trigger taxonomy.

A trigger source MAY be unknown in advance.

URACE MUST therefore support both:

```text
KNOWN RELEVANT CONDITION
    → targeted wake/resume

and

UNPREDICTED RELEVANT CHANGE
    → generic observation/discovery
    → relevance evaluation
    → reassessment when meaningful
```

## Periodic Discovery and Re-Trigger Attempts

URACE MUST NOT depend exclusively on events it already knows how to subscribe to.

While autonomous operation remains enabled, bounded periodic discovery SHOULD be available where useful as a fallback mechanism for discovering:

```text
unpredicted Product changes
unpredicted project changes
new evidence
changed assumptions
changed external conditions
changed dependencies
changed constraints
changed readiness
changed risks
changed executor availability
newly available capabilities
material URACE limitations
other previously unknown lifecycle-relevant conditions
```

Periodic discovery MAY be deterministic.

It MAY also use one or more compatible executors when executor reasoning or inspection adds useful discovery capability.

Conceptually:

```text
DORMANT
   │
   ▼
PERIODIC DISCOVERY OPPORTUNITY
   │
   ├──── deterministic inspection available
   │              │
   │              ▼
   │          INSPECT
   │
   └──── executor assistance useful
                  │
             ┌────┴────┐
             ▼         ▼
         AVAILABLE   UNAVAILABLE
             │         │
             ▼         ▼
          INSPECT   REMAIN LIVE
             │         │
             │         ▼
             │      RETRY LATER
             │
             └────┐
                  ▼
         MATERIAL CHANGE?
            ┌─────┴─────┐
            ▼           ▼
           NO          YES
            │           │
            ▼           ▼
         DORMANT     MEANINGFUL
                      TRIGGER
                         │
                         ▼
                      ASSESS
```

The periodic attempt itself is NOT automatically a Meaningful Trigger.

The executor becoming available MAY be a Meaningful Trigger when that availability materially changes what the lifecycle can do.

The executor being unavailable is a capacity observation.

It MUST NOT end the autonomous lifecycle or event loop merely because a periodic executor-assisted attempt cannot currently execute.

A failed executor-assisted discovery attempt SHOULD normally produce:

```text
record/update capacity state
        │
        ▼
WAIT / CONTINUE OBSERVATION
        │
        ▼
RETRY ACCORDING TO POLICY
```

not:

```text
executor unavailable
        │
        ▼
terminate autonomous lifecycle
```

Periodic executor re-trigger attempts SHOULD be:

```text
bounded
backoff-aware
budget-aware
capacity-aware
cost-aware
risk-aware
policy-aware
context-sensitive
```

They SHOULD NOT continuously consume executor resources when no material change is reasonably expected.

Deterministic observation SHOULD be preferred when sufficient.

## Trigger Non-Examples

The following MUST NOT automatically be treated as Meaningful Triggers:

```text
time passed with no relevant condition
executor remains available with no material lifecycle implication
AI can think of another idea
runtime is still alive
budget remains unused
same unchanged state is observed again
same event is delivered repeatedly
cosmetic filesystem noise
irrelevant external event
unrelated Product artifact changed
periodic discovery attempt finds nothing relevant
periodic executor retry merely occurs
```

A periodic tick MAY be used as a detection mechanism or fallback reassessment mechanism.

The tick itself is not inherently meaningful.

The relevant condition it reveals MAY be.

A scheduled reassessment intentionally established by lifecycle policy MAY itself justify reassessment because the lifecycle previously determined that reassessment at that time is relevant.

Even then, reassessment does not imply Product mutation.

## Trigger Interpretation

Trigger detection and lifecycle interpretation MUST remain separate.

Conceptually:

```text
RAW EVENT / OBSERVATION /
DISCOVERY RESULT
          │
          ▼
NORMALIZE
          │
          ▼
RELEVANCE FILTER
          │
     ┌────┴─────┐
     ▼          ▼
irrelevant    potentially
             meaningful
                │
                ▼
        MEANINGFUL TRIGGER
                │
                ▼
             ASSESS
```

URACE SHOULD avoid requiring expensive AI reasoning merely to reject obviously irrelevant raw events.

Deterministic filtering SHOULD be used where sufficient.

When relevance cannot be determined deterministically, a capable executor MAY assist.

Executor judgment does not replace URACE policy.

Executor unavailability during relevance analysis MUST degrade to waiting, conservative reconciliation, deferred analysis or another policy-compatible behavior rather than autonomous lifecycle termination.

## Trigger Context

Where useful, a normalized trigger MAY conceptually expose:

```text
TriggerContext {
    source?
    kind?
    scope?
    observedAt?
    condition?
    references?
    priorStateReference?
    currentStateReference?
    evidenceReference?
    deduplicationKey?
}
```

This representation is OPTIONAL.

Implementations MAY use a simpler representation.

`scope` MAY identify any relevant Product/project/lifecycle scope and MUST NOT be restricted to a closed set.

The trigger itself does not need durable independent identity unless required for lifecycle correctness, deduplication, auditability, scheduling, recovery or the host environment.

## Trigger Conditions

When entering a dormant state, URACE SHOULD identify the smallest useful set of known conditions that could plausibly change the current assessment.

Examples:

```text
WAITING_FOR_CAPACITY
    → required compatible capacity becomes available

WAITING_FOR_APPROVAL
    → approval decision arrives

WAITING_FOR_EVIDENCE
    → required external evidence arrives

SCHEDULED WAIT
    → relevant time condition becomes true

BLOCKED
    → blocking HARD condition changes

IDLE
    → Product, Intent, goal, evidence,
      environment, policy, executor capacity,
      or another lifecycle-relevant condition
      materially changes
```

URACE MUST NOT require perfect enumeration of future triggers.

Unknown future evidence, scope changes or conditions may still become Meaningful Triggers when observed or discovered.

Periodic discovery SHOULD complement known trigger conditions when policy determines that known event coverage may be insufficient.

## Trigger Granularity

Trigger granularity SHOULD be proportional to Product and deployment needs.

Avoid both:

```text
UNDER-TRIGGERING
    =
material changes fail to cause reassessment
```

and:

```text
OVER-TRIGGERING
    =
irrelevant/noisy changes repeatedly cause
expensive reassessment
```

The preferred behavior is:

```text
cheap observation
      │
      ▼
cheap relevance filtering where possible
      │
      ▼
meaningful candidate
      │
      ▼
full lifecycle reassessment
```

Periodic discovery frequency SHOULD likewise balance:

```text
DISCOVERY COVERAGE
        ↕
RESOURCE COST
```

## Trigger Deduplication and Coalescing

Repeated equivalent raw events SHOULD NOT cause unnecessary repeated reassessment.

Implementations SHOULD, where appropriate:

- deduplicate equivalent events;
- coalesce bursts of related changes;
- debounce noisy sources;
- preserve the latest relevant state;
- avoid losing distinct material changes.

The exact strategy remains a variant.

Correctness MUST take priority over optimization.

## Trigger Delivery Semantics

URACE MUST NOT require exactly-once event delivery.

A trigger implementation MAY provide:

```text
at-most-once
at-least-once
effectively-once
platform-specific delivery semantics
```

URACE lifecycle correctness SHOULD tolerate duplicate delivery through idempotent reassessment, deduplication, reconciliation or equivalent mechanisms.

Potentially lost trigger delivery MUST be addressed by the host's reliability model or an appropriate fallback discovery/reconciliation strategy when lifecycle correctness requires it.

Periodic discovery MAY provide one such fallback when appropriate.

## Trigger Failure

Failure to process a trigger MUST NOT silently corrupt authoritative Product state.

When possible:

```text
trigger observed
      │
      ▼
processing fails
      │
      ▼
preserve/recover state
      │
      ▼
retry / reconcile / reassess
according to policy
```

Trigger-processing failure is not Product completion.

Executor failure during trigger processing is not autonomous lifecycle termination.

## Trigger and Evidence

A Meaningful Trigger is not necessarily Evidence.

For example:

```text
timer expires
    → trigger

executor capacity restored
    → trigger / capacity observation

new customer result arrives
    → trigger + potential Evidence

artifact changed
    → trigger + Product observation

periodic discovery detects
previously unknown dependency change
    → trigger + potential observation/evidence
```

A trigger causes reassessment.

Evidence contributes to what that reassessment concludes.

Do not collapse these concepts.

## Trigger and Intent

A trigger MUST be interpreted relative to applicable Product Intent.

The same raw event MAY be meaningful for one Product and irrelevant for another.

The same change MAY also have different significance at different Product/project scope levels.

Meaningfulness is therefore semantic, not merely mechanical.

## Trigger and Executor Availability

Executor availability is a lifecycle capacity condition.

A material transition MAY constitute a Meaningful Trigger.

For example:

```text
WAITING_FOR_CAPACITY
        │
        ▼
required executor unavailable
        │
        ▼
WAIT / PRESERVE LIVENESS
        │
        ▼
executor becomes available
        │
        ▼
MEANINGFUL TRIGGER
        │
        ▼
REASSESS
```

However:

```text
EXECUTOR UNAVAILABLE
        ≠
END AUTONOMOUS LOOP
```

and:

```text
EXECUTOR AVAILABLE
        ≠
MANDATORY PRODUCT WORK
```

Executor availability changes what operations MAY currently be possible.

It does not independently determine whether the Product lifecycle exists, whether Product Intent is satisfied, or whether autonomous operation should terminate.

When all suitable executors are unavailable, URACE SHOULD:

```text
persist capacity state
        │
        ▼
preserve liveness
        │
        ▼
observe / retry availability
according to policy
        │
        ▼
reassess when materially changed
```

The availability retry mechanism remains a variant.

## Trigger and Liveness

A wake mechanism need not understand full Product semantics.

It only needs to deliver or expose a candidate condition reliably enough for URACE to determine whether reassessment is warranted.

Likewise, periodic discovery need not know in advance what material change it will discover.

Therefore:

```text
DETECTION / DELIVERY /
PERIODIC DISCOVERY
        =
variant

MEANINGFULNESS
        =
URACE lifecycle semantics

REASSESSMENT
        =
URACE lifecycle responsibility
```

This separation preserves autonomous liveness, open-ended change awareness and implementation agnosticism.

---

# 13. Objective Discovery

URACE MUST NOT merely consume an endless predetermined task list.

Its default autonomous Product-evolution pattern is:

```text
INTENT
  │
  ▼
PRODUCT / USER / CUSTOMER / MARKET / ENVIRONMENT EVIDENCE
                       │
                       ▼
                    ASSESS
                       │
                       ▼
            IDENTIFY HIGHEST-VALUE GAP
                       │
                       ▼
           FORMULATE JUSTIFIED REQUIREMENT
                  / OBJECTIVE
                       │
                       ▼
                   IMPLEMENT
                       │
                       ▼
                    VALIDATE
                       │
                       ▼
                   CHECKPOINT
                       │
                       ▼
             OBSERVE NEW EVIDENCE
                       │
                       ▼
                   REASSESS
                       │
                       └────► repeat while justified
```

This is a semantic lifecycle pattern, not a mandatory implementation pipeline.

The applicable evidence domain is a variant of the Product.

For Products with a market/user/customer dimension, assessment SHOULD incorporate available relevant evidence.

For Products without a meaningful market or customer dimension, Product, technical, operational, research or environmental evidence MAY drive the same lifecycle.

URACE therefore repeatedly asks:

> Given Product Intent, current state, available evidence, previous decisions, unresolved risks, constraints, budgets, schedules and available capabilities, what is the highest-value justified gap, requirement or objective to address next?

A requirement MUST be justified relative to Product Intent by evidence, risk, constraint or sufficiently supported opportunity.

Do not generate requirements merely to sustain autonomous activity.

Possible results include:

- Product change;
- defect correction;
- new requirement;
- research;
- hypothesis validation;
- reliability improvement;
- security improvement;
- usability improvement;
- accessibility improvement;
- documentation improvement;
- architecture improvement;
- cost reduction;
- evidence collection;
- user/customer/market validation where applicable;
- reduction of meaningful friction or effort where applicable;
- reduction of cognitive load where applicable;
- reduction of customer cost where applicable;
- improvement of acquisition or conversion where applicable;
- improvement of activation or adoption where applicable;
- improvement of retention or loyalty where applicable;
- improvement of customer/user outcomes where applicable;
- readiness validation;
- no currently justified mutation;
- completion/readiness assessment.

These are examples only.

A discovered possible improvement is not automatically a justified requirement or objective.

A Product-value dimension is not automatically an objective.

Expected Product value MUST justify its cost, risk and opportunity cost relative to Product Intent.

---

# 14. Product Value vs Activity

Continuous autonomy does NOT mean continuous mutation.

URACE MUST optimize for justified Product progress and value relative to Intent, not executor utilization or isolated metrics.

Product Value is a derived evaluation concept.

It is NOT currently required to be a separate first-class lifecycle object.

Conceptually:

```text
PRODUCT INTENT
      +
AVAILABLE EVIDENCE
      +
EXPECTED OUTCOME
      +
CONSTRAINTS
      +
COST / RISK / TRADE-OFFS
      │
      ▼
EXPECTED PRODUCT VALUE
      │
      ▼
JUSTIFIED OBJECTIVE?
```

An accepted cycle MUST materially:

- advance Product Intent;
- improve a relevant Product/user/customer outcome;
- reduce meaningful uncertainty;
- acquire useful evidence;
- reduce meaningful risk;
- improve validated quality;
- resolve a blocker;
- improve applicable Product readiness;
- reduce meaningful friction, effort, cognitive load or cost where applicable;
- improve relevant acquisition, conversion, activation, adoption, engagement, retention, loyalty, satisfaction or trust where applicable;
- improve customer/user productivity or intended outcomes where applicable;
- or otherwise produce justified Product progress.

These dimensions are contextual rather than universally ordered.

URACE MUST evaluate them according to Product Intent, evidence, expected value, cost, risk, constraints and opportunity cost.

No individual dimension is inherently authoritative.

For example:

```text
higher conversion
        ≠
necessarily higher Product value
```

when it materially harms another Intent-relevant outcome such as:

```text
trust
retention
usability
accessibility
customer outcomes
safety
customer cost
reliability
```

Likewise:

```text
more engagement
        ≠
necessarily better Product
```

unless engagement is meaningfully connected to Product Intent and realized user/customer value.

A gain in one dimension MUST NOT automatically justify degradation of another material Intent-relevant outcome.

Do NOT create work merely because AI credits, budget or compute capacity remain available.

Do NOT continue polishing merely because some theoretically possible improvement exists.

Conversely, absence of an immediately obvious task MUST NOT by itself justify `IDLE`.

Before `IDLE`, URACE MUST perform an explicit completion/readiness assessment.

`IDLE` ends unnecessary active work.

It MUST NOT, by itself, end autonomous lifecycle ownership.

Executor unavailability ends neither Product responsibility nor autonomous lifecycle ownership.

---

# 15. Evidence

Evidence is a first-class lifecycle primitive.

It is not merely transient executor context.

Conceptually:

```text
Evidence {
    identity?
    source
    observation
    provenance
    timestamp?
    confidence?
    classification
    references?
}
```

Evidence MAY originate from:

- users;
- customers;
- prospects;
- market observations;
- analytics;
- tests;
- runtime observations;
- research;
- external systems;
- executors;
- operators;
- files;
- APIs;
- experiments;
- previous lifecycle observations;
- Product outcome observations;
- user/customer outcome observations;
- periodic Product/environment discovery.

Do not require a specific evidence source.

Evidence quality SHOULD influence confidence.

Absence of evidence MUST NOT be silently converted into positive evidence.

Evidence SHOULD be evaluated for relevance, recency, provenance and uncertainty where applicable.

URACE MUST preserve meaningful distinctions between:

```text
EVIDENCE
    =
what is known or observed

ASSUMPTION
    =
what is provisionally believed

INFERENCE
    =
what is derived from available information

HYPOTHESIS
    =
what remains to be tested

DECISION
    =
what URACE chooses

REQUIREMENT
    =
what justified Product gap should be addressed

OBSERVATION
    =
what execution or the environment produced/revealed

VALIDATION
    =
whether applicable acceptance criteria were satisfied
```

These concepts MUST NOT be collapsed merely for implementation convenience.

In particular:

```text
EXECUTOR CLAIM
      ≠
EVIDENCE BY DEFAULT

INFERENCE
      ≠
OBSERVATION

HYPOTHESIS
      ≠
VALIDATED FACT

TRIGGER
      ≠
EVIDENCE BY DEFAULT
```

Material lifecycle decisions SHOULD preserve sufficient lineage to determine what justified them.

This includes, where applicable:

```text
Intent
evidence
constraints
observations
risk
policy
assumptions
```

The expected relationship is:

```text
INTENT
   │
   ▼
EVIDENCE
   │
   ▼
ASSESSMENT
   │
   ▼
JUSTIFIED GAP
   │
   ▼
REQUIREMENT / OBJECTIVE
   │
   ▼
EXECUTION
   │
   ▼
OBSERVATION
   │
   ▼
VALIDATION
   │
   ▼
CHECKPOINT
   │
   ▼
NEW / UPDATED EVIDENCE
```

URACE SHOULD preserve this causal lineage without requiring a heavyweight evidence database, knowledge graph, RAG system or specialized evidence framework.

Evidence storage, indexing and retrieval mechanisms remain implementation variants.

---

# 16. Market and Customer Awareness

Market and customer awareness are conditional on Product Intent.

For Products with a market/user/customer dimension, URACE SHOULD allow relevant external evidence to influence autonomous requirements and objectives.

However:

```text
ENGINEERING VALID
        ≠
MARKET VALID
```

and:

```text
AI OPINION
        ≠
MARKET EVIDENCE
```

and:

```text
METRIC MOVEMENT
        ≠
REALIZED CUSTOMER VALUE
```

If no market/customer evidence is available, autonomous reasoning MAY formulate hypotheses and requirements for testing them, but MUST NOT represent them as validated demand or realized value.

This distinction MUST survive across cycles.

For applicable Products, relevant evidence MAY include signals related to:

```text
need
demand

discovery
acquisition
conversion
activation
adoption
engagement

retention
churn
loyalty

satisfaction
trust

usability
accessibility
clarity
friction
customer effort
cognitive load

customer cost
customer productivity
willingness to pay
realized customer value
customer outcomes
```

This is an illustrative set, not a closed ontology or mandatory funnel.

No single signal is universally authoritative.

URACE SHOULD reason about Product Intent and the combination of available evidence rather than blindly maximizing an isolated metric.

For example:

Improving conversion MAY be valuable when evidence indicates that a relevant acquisition or decision-friction problem prevents intended Product value.

Improving retention MAY be valuable when evidence indicates failure to sustain intended customer value.

Reducing cognitive load, effort or total customer cost MAY be valuable when those factors materially prevent adoption, successful use, retention or intended outcomes.

These are possible causal relationships to investigate and validate.

They MUST NOT be assumed as facts.

For a Product with market intent, the preferred evidence-driven lifecycle is:

```text
INTENT
  │
  ▼
MARKET / USER / CUSTOMER / PRODUCT EVIDENCE
              │
              ▼
            ASSESS
              │
              ▼
       IDENTIFY MATERIAL GAP
              │
              ▼
     REQUIREMENT / OBJECTIVE
              │
              ▼
          IMPLEMENT
              │
              ▼
           VALIDATE
              │
              ▼
          CHECKPOINT
              │
              ▼
       NEW PRODUCT STATE
              │
              ▼
    NEW / UPDATED EVIDENCE
              │
              └──────────► REASSESS
```

Market/customer analysis is therefore an input to Product evolution rather than a separate mandatory subsystem.

URACE MAY delegate market analysis, customer analysis, research, requirement formulation and implementation to capable executors.

URACE remains authoritative over:

```text
Intent
evidence provenance and lineage
requirement/objective justification
policy
acceptance
validation
checkpointing
lifecycle continuation
readiness
```

For a Product with market intent, an applicable readiness target MAY be market-fit-quality Product readiness.

This means evolving the Product, within available evidence and applicable constraints, toward sufficient completeness, coherence, reliability, usability, accessibility, security, maintainability, operability and differentiation for its intended market, users and customers.

However:

```text
MARKET-FIT-QUALITY READINESS
             ≠
PROVEN PRODUCT-MARKET FIT
```

Actual Product-market fit, validated demand, retention, willingness to pay, customer loyalty or equivalent outcomes MUST require appropriate external evidence.

URACE MUST NOT fabricate market validation from executor confidence.

When external market/customer evidence is obtainable within policy, budget and capability constraints, acquiring or testing that evidence MAY itself become a justified objective.

New external Product/customer evidence MAY constitute a Meaningful Trigger when it could materially change the most recent lifecycle assessment.

Periodic discovery MAY also identify external changes that no known event source directly exposed.

Market-fit-quality readiness MUST NOT become a universal readiness invariant for Products without market intent.

---

# 17. State

Maintain a small authoritative structured state.

Conceptually:

```text
ProductState {
    product
    intent
    constraints

    currentCheckpoint
    currentObjective

    evidence
    assumptions
    risks
    blockers

    completedObjectives
    failedObjectives

    validationState
    capacityState
    budgetState
    scheduleState
    readinessState

    lifecycleState
    livenessState?
    wakeState?
    relevantTriggerConditions?
    lastDiscoveryState?

    lastCycle
}
```

Intent MUST be durably represented or durably referenced.

Evidence lineage MAY be represented directly or through durable references.

Liveness, wake state, discovery state and relevant trigger conditions MAY be represented directly or derived from the hosting environment when equivalent guarantees exist.

`relevantTriggerConditions` MUST NOT require an exhaustive trigger registry.

`lastDiscoveryState` MUST NOT require a dedicated discovery subsystem.

These MAY be omitted when equivalent semantics are provided by the runtime or when no explicit conditions are known.

Exact serialization is an implementation detail.

Human-readable documents MUST NOT be the sole authoritative state store.

---

# 17A. Constraint Strength

Not every constraint has equal authority.

URACE MUST support concepts equivalent to:

```text
HARD
SOFT
```

A HARD constraint is an invariant or boundary autonomous execution MUST NOT knowingly violate.

Examples MAY include:

```text
explicit user prohibition
security boundary
safety boundary
legal/compliance requirement
required external contract
compatibility requirement
hard deadline
hard resource ceiling
explicitly protected Product invariant
```

A SOFT constraint expresses a preference, target, convention or optimization direction.

Examples MAY include:

```text
preferred implementation
preferred architecture
preferred tool
preferred structure
cost target
performance target
preferred schedule
organizational convention
```

Soft constraints SHOULD guide execution without unnecessarily becoming execution gates.

URACE MUST NOT silently convert an inference, convention, recommendation or preference into a HARD constraint.

When constraints conflict, use conceptually:

```text
HARD CONSTRAINT
      │
      ▼
EXPLICIT CURRENT PRODUCT / USER INTENT
      │
      ▼
VERIFIED ENVIRONMENT REALITY
      │
      ▼
SOFT CONSTRAINT
      │
      ▼
INFERRED CONVENTION
```

Within equivalent authority, prefer the more specific and currently applicable constraint.

Enforcement MUST be proportional.

Hard constraints MAY prevent execution.

Soft constraints SHOULD normally influence selection, planning, scoring and validation.

---

# 18. Lifecycle States

At minimum support concepts equivalent to:

```text
ASSESSING
ACTIVE
VALIDATING
REPAIRING
WAITING_FOR_CAPACITY
BLOCKED
PAUSED
IDLE
```

Individual objectives MAY additionally become:

```text
PLANNED
ACTIVE
FAILED
GOAL_COMPLETE
```

`GOAL_COMPLETE` MUST NOT imply global Product completion.

In continuous autonomous mode:

```text
GOAL_COMPLETE
      │
      ▼
CHECKPOINT
      │
      ▼
ASSESS AGAIN
      │
 ┌────┴───────────────┐
 ▼                    ▼
JUSTIFIED WORK     NO JUSTIFIED WORK
 │                    │
 ▼                    ▼
ACTIVE          READINESS ASSESSMENT
                      │
                ┌─────┴─────┐
                ▼           ▼
             NOT READY     READY
                │           │
                ▼           ▼
              ACTIVE       IDLE
                              │
                              ▼
                   PRESERVE LIVENESS
                              │
                              ▼
                EVENT / DISCOVERY /
                  PERIODIC RE-TRY
                              │
                              ▼
                  MEANINGFUL TRIGGER
                              │
                              ▼
                           ASSESS
```

`IDLE` is a successful autonomous lifecycle state, not a failure.

It means no currently justified Product action remains after applicable completion/readiness requirements have been evaluated relative to Product Intent.

`IDLE` MUST be neither premature nor artificially delayed.

URACE MUST NOT enter `IDLE` merely because:

- one objective completed;
- the current backlog is empty;
- one executor has no further suggestion;
- one executor is unavailable;
- all intelligent executors are temporarily unavailable;
- required evidence has not yet been examined;
- capacity temporarily disappeared;
- work is difficult;
- the next objective is not immediately obvious;
- applicable external validation remains reasonably obtainable;
- unresolved material defects, risks or readiness gaps remain.

URACE MUST NOT avoid `IDLE` merely because:

- executors remain available;
- budget remains;
- additional cosmetic refinement is possible;
- another speculative abstraction could be created;
- another metric could theoretically be improved;
- another equivalent analysis could be performed;
- perfection is theoretically unattainable.

`IDLE` means active work has converged.

It MUST NOT mean the persistent autonomous lifecycle has been silently abandoned.

`WAITING_FOR_CAPACITY` means required capacity is currently unavailable.

It MUST NOT mean the lifecycle should end.

---

# 18A. Completion and IDLE Gate

Before entering `IDLE`, URACE MUST explicitly determine whether the Product has reached the highest justified readiness state currently available under Product Intent, evidence, constraints, capability, schedule and budget.

The assessment MUST consider, where applicable:

```text
INTENT SATISFACTION
        +
HARD CONSTRAINT SATISFACTION
        +
ACCEPTANCE / VALIDATION
        +
MATERIAL DEFECT REVIEW
        +
MATERIAL RISK REVIEW
        +
PRODUCT COHERENCE
        +
APPLICABLE READINESS CRITERIA
        +
AVAILABLE EXTERNAL EVIDENCE
        +
ECONOMIC / RESOURCE REASONABLENESS
        +
NO HIGHER-VALUE JUSTIFIED ACTION
```

Applicable readiness criteria MAY include:

```text
usability
user/customer readiness
reliability
security
safety
operability
maintainability
performance
accessibility
research validity
ecosystem compatibility
market readiness
other Intent-specific criteria
```

The exact dimensions MUST remain Product-specific.

Not every Product requires every dimension.

For a Product with market intent, applicable readiness MAY include market-fit-quality readiness, not merely technical functionality.

For another Product, the applicable readiness target MAY be entirely different.

Where final validation depends on external users, customers, systems, time, events or executor capacity:

```text
PRODUCT READY FOR CURRENT STAGE
              │
              ▼
external condition required
              │
       ┌──────┴──────┐
       ▼             ▼
actionable now   must wait
       │             │
       ▼             ▼
     ACTIVE      WAIT / IDLE
                       │
                       ▼
             IDENTIFY RELEVANT
             TRIGGER CONDITIONS
                       │
                       ▼
                PRESERVE LIVENESS
                       │
                       ▼
          EVENT / PERIODIC DISCOVERY
```

URACE MUST NOT endlessly modify a ready Product while the missing information can only come from an external condition.

Likewise, URACE MUST NOT terminate because the executor required to continue is temporarily unavailable.

The completion decision therefore balances three errors:

```text
PREMATURE IDLE
    =
meaningful justified Product work still exists

ENDLESS LOOP
    =
remaining work has insufficient expected Product value
relative to cost, risk or evidence need

DEAD AUTONOMY
    =
state survives
but no viable path remains
for reassessment or continuation
```

URACE MUST avoid all three.

---

# 19. Validation

Executor confidence is not validation.

URACE owns acceptance policy.

Validation MUST be capability/Product appropriate.

Examples MAY include:

- tests;
- builds;
- schema checks;
- structural checks;
- lint;
- type checks;
- integration checks;
- security checks;
- artifact existence;
- data validation;
- content constraints;
- operator-defined assertions;
- external verification;
- user/customer/market evidence where applicable.

No particular validation mechanism is universally required.

Conceptually:

```text
Candidate
    │
    ▼
Validation Policy
    │
 ┌──┴──┐
 ▼     ▼
PASS   FAIL
 │      │
 ▼      ▼
accept repair/reassess
```

Passing implementation validation MUST NOT automatically imply overall Product readiness or realized Product value.

Validation results MAY themselves become evidence for subsequent lifecycle assessment.

Where an objective targets an external Product/user/customer outcome that cannot yet be observed, URACE MUST preserve that distinction rather than treating predicted value as realized value.

A newly available validation result MAY be a Meaningful Trigger when it could materially change acceptance, readiness or lifecycle state.

---

# 20. Validation Discovery

URACE SHOULD discover applicable validation mechanisms from the Product.

For software this MAY include common manifests such as:

```text
package.json
pyproject.toml
Cargo.toml
go.mod
pom.xml
build.gradle
Makefile
CMakeLists.txt
```

These MUST NOT form a closed list.

Discovery MUST support:

- unfamiliar manifests;
- user configuration;
- executor-assisted discovery;
- Products without conventional manifests;
- Products without source code.

Overrides MAY explicitly define validation operations.

Validation discovery SHOULD also identify Product-specific acceptance and readiness criteria when available.

---

# 21. File and Format Agnosticism

URACE core MUST NOT depend on understanding every artifact format.

Use a layered approach:

```text
URACE
  │
  ▼
generic artifact identity
  │
  ▼
capable executor/tool
  │
  ▼
format-specific interpretation
```

Therefore adding support for a new file type SHOULD normally require:

- no URACE lifecycle change;
- no ProductState redesign;
- no autonomous-loop redesign.

Only an appropriate executor/tool capability may be required.

---

# 22. Programming-Language Agnosticism

URACE core MUST NOT contain lifecycle assumptions tied to:

```text
JavaScript
TypeScript
Python
Rust
Go
Java
C
C++
or any other language
```

Language-specific knowledge belongs to executors, adapters, discovery mechanisms or Product configuration.

Adding a new programming language SHOULD NOT require modifying core lifecycle semantics.

---

# 23. Platform Agnosticism

URACE MUST NOT require:

```text
Linux
Windows
macOS
Cloudflare
AWS
Azure
GCP
GitHub
GitLab
Docker
Kubernetes
```

Adapters MAY use these systems.

Core state, lifecycle, trigger, discovery and liveness semantics MUST remain portable.

---

# 24. Project-Type Agnosticism

URACE MUST NOT assume the Product is a web application or even software.

Its lifecycle must remain meaningful for any Product that can expose:

```text
Intent
state
artifacts
evidence
operations
observations
validation
```

This is the minimum conceptual Product contract.

Product readiness criteria MUST be derived from Product Intent and evidence rather than hard-coded Product categories.

Customer-oriented value dimensions MUST remain optional Product-specific semantics rather than requirements of URACE itself.

Meaningful change MAY occur at any applicable Product/project scope level regardless of Product type.

---

# 25. Checkpoints

Every accepted autonomous increment MUST produce a recoverable checkpoint.

Conceptually:

```text
Checkpoint {
    identity
    parent?
    objective
    productStateReference
    intentReference?
    artifactReferences
    evidenceReferences
    decisions
    validation
    executorMetadata
    unresolvedRisks
    timestamp
}
```

Checkpoints MUST NOT require Git.

If Git is available, a commit/revision MAY be referenced.

Other artifact/version systems MAY be used.

Checkpoint evidence references SHOULD preserve sufficient lineage to reconstruct why the accepted increment occurred.

Material Intent changes MUST be durably attributable across checkpoints/history.

Entering `IDLE` SHOULD produce or reference a durable checkpoint representing the accepted readiness state.

Checkpoint durability MUST NOT be confused with wakeability.

---

# 26. History

Every cycle MUST preserve enough information to reconstruct:

```text
What Product Intent applied?

Why did this cycle occur?

What evidence or Product gap justified it?

What requirement/objective was selected?

What Product-value dimension, if any,
was expected to improve?

What assumptions existed?

What constraints applied?

What budget/schedule state applied?

What executor capabilities were required?

Which executor was used?

What operations occurred?

What observations resulted?

What changed?

How was the candidate validated?

What intended Product/user/customer
outcome changed or remained uncertain?

Why was it accepted/rejected?

What remains unresolved?

Why did the lifecycle continue,
wait, block or become IDLE?

If execution became dormant,
what conditions could justify reassessment?

What preserves autonomous liveness?

If reactivated,
what Meaningful Trigger caused reassessment?

Was the trigger event-driven,
scheduled or discovered periodically?

If executor capacity was unavailable,
how was lifecycle liveness preserved?
```

History MUST survive executor replacement.

Material lifecycle history SHOULD preserve causal links rather than only chronological logs.

Trigger history SHOULD be preserved only to the degree needed for lifecycle correctness, explanation, deduplication, auditability or recovery.

URACE MUST NOT require an exhaustive permanent log of every irrelevant raw event or unsuccessful periodic discovery attempt.

---

# 27. Capacity

Capacity is generic.

URACE MUST NOT equate capacity solely with LLM credits.

Capacity constraints MAY include:

- AI quota;
- API quota;
- compute availability;
- unavailable executor;
- rate limit;
- external service outage;
- missing credentials;
- unavailable human approval;
- unavailable environment.

Normalize these into generic lifecycle observations.

At minimum:

```text
AVAILABLE
WAITING_FOR_CAPACITY
BLOCKED
```

A material capacity transition MAY be a Meaningful Trigger when it changes whether a justified objective can be attempted.

Capacity unavailability MUST NOT terminate autonomous lifecycle ownership.

Conceptually:

```text
REQUIRED CAPACITY
      │
      ▼
UNAVAILABLE
      │
      ▼
WAITING_FOR_CAPACITY
      │
      ▼
PRESERVE LIVENESS
      │
      ▼
EVENT / RETRY / DISCOVERY
      │
      ▼
CAPACITY CHANGED?
   ┌──┴──┐
   ▼     ▼
  NO    YES
   │     │
   ▼     ▼
 WAIT  REASSESS
```

---

# 27A. Resource Budgets

Capacity describes whether a resource can be used.

Budget describes how much resource URACE is permitted or expected to consume.

Budgets MAY include:

```text
money
AI tokens
API usage
compute
storage
network
execution time
human attention
executor calls
external-service quota
other measurable resources
```

A budget MAY be conceptually:

```text
HARD
SOFT
UNBOUNDED
UNKNOWN
```

A HARD budget MUST NOT knowingly be exceeded.

A SOFT budget SHOULD influence resource allocation but MAY be exceeded when policy permits and expected Product value justifies it.

Objective selection SHOULD consider:

```text
expected Product value
expected resource cost
remaining budget
risk
uncertainty
opportunity cost
validation/recovery reserve
```

URACE SHOULD preserve sufficient resource capacity for validation, checkpointing and recovery.

Periodic discovery SHOULD likewise respect applicable budgets.

Do not consume resources merely because they remain available.

Budget exhaustion MUST NOT be represented as Product completion.

Depending on context it MAY produce:

```text
WAITING_FOR_CAPACITY
BLOCKED
PAUSED
IDLE
```

A resource-constrained dormant state MUST preserve autonomous liveness when autonomous operation remains enabled.

A budget or quota transition MAY become a Meaningful Trigger when it materially changes available action.

---

# 28. Waiting Is Not Completion

If required execution capacity disappears:

```text
ACTIVE
  │
  ▼
capacity unavailable
  │
  ▼
persist state
  │
  ▼
WAITING_FOR_CAPACITY
  │
  ▼
preserve autonomous lifecycle
  │
  ▼
event / availability retry /
periodic discovery
  │
  ▼
compatible capacity available
  │
  ▼
MEANINGFUL TRIGGER
  │
  ▼
RESUME / REASSESS
```

Do not declare the Product complete because an executor became unavailable.

Do not terminate the autonomous lifecycle because an executor became unavailable.

Do not terminate the only responsible persistent autonomous runtime merely because an executor availability check failed.

Likewise, a deadline, external dependency or required future evidence MUST NOT be mistaken for completion.

`WAITING_FOR_CAPACITY` MUST NOT silently become permanent inactivity merely because the active runtime would otherwise terminate.

---

# 28A. Time, Scheduling and Wakeability

Time is a first-class lifecycle constraint.

URACE MAY represent concepts equivalent to:

```text
deadline
earliest start
execution window
recurrence
reassessment time
external wait
cooldown
periodic discovery interval
```

A HARD temporal constraint MUST be respected as a HARD constraint.

A SOFT schedule SHOULD influence planning without unnecessarily preventing justified progress.

A schedule MUST NOT create artificial work merely because a future execution time exists.

When useful independent work exists before a future condition, URACE MAY continue it.

When no justified work exists until a future condition:

```text
persist state
    │
    ▼
identify relevant temporal condition
    │
    ▼
establish / preserve wake path
    │
    ▼
WAIT
    │
    ▼
condition becomes true
    │
    ▼
MEANINGFUL TRIGGER
    │
    ▼
REASSESS
```

URACE SHOULD avoid active polling when a cheaper or event-driven wake mechanism is available.

However, bounded periodic discovery MAY be used when event-driven coverage is incomplete, unknown or insufficient.

Scheduling and wake implementation are environment-specific.

URACE core MUST NOT require:

```text
cron
a permanent process
a permanent event loop
a particular scheduler
a particular operating system
a particular cloud scheduler
a particular queue
a particular watcher
a particular alarm mechanism
```

However, autonomous operation MUST preserve equivalent semantics:

> When a lifecycle condition can become actionable later, a viable path to detecting, discovering or receiving a potentially Meaningful Trigger and returning to assessment MUST remain available while autonomous operation remains enabled.

A runtime MAY safely terminate while waiting only when the environment or another durable mechanism can later reactivate URACE.

Otherwise, the responsible runtime MUST wait efficiently rather than allowing the autonomous lifecycle to become unreachable.

Scheduled time MAY itself be meaningful when the lifecycle previously established that reassessment at that time could change a decision.

Arbitrary periodic time passage is not automatically meaningful.

Periodic discovery is useful because what becomes meaningful may not be predictable in advance.

---

# 29. Executor Replacement

An executor MAY disappear permanently.

URACE MUST be able to:

1. preserve lifecycle state;
2. preserve applicable Product Intent;
3. inspect required capabilities;
4. discover another compatible executor;
5. provide it with sufficient durable context;
6. preserve or regain execution liveness;
7. continue.

No executor's private conversation history may be required for correctness.

Executor availability MAY be observed through any suitable mechanism.

A transition from unavailable to sufficiently capable MAY be a Meaningful Trigger.

If no compatible executor is currently available:

```text
NO EXECUTOR
     │
     ▼
WAITING_FOR_CAPACITY
     │
     ▼
AUTONOMOUS LIFECYCLE REMAINS LIVE
     │
     ▼
availability observation /
bounded retry / discovery
     │
     ▼
compatible executor found
     │
     ▼
REASSESS
```

Executor availability MUST NOT be used as the condition that ends persistent autonomous lifecycle ownership.

---

# 30. Minimal Executor Configuration

The bootstrap MUST prove operation with exactly:

```text
URACE
  +
ONE intelligent executor
```

No orchestrator.

No multi-agent system.

No voting.

No consensus.

No model router.

This is a mandatory agnosticism test.

The minimal configuration MUST also remain autonomously live without requiring an external orchestrator to wake it.

If the one executor temporarily becomes unavailable, URACE MUST remain in an appropriate live waiting state rather than terminating autonomous lifecycle ownership.

---

# 31. Orchestrated Configuration

URACE MAY alternatively operate as:

```text
URACE
  │
  ▼
Generic Executor Adapter
  │
  ▼
OpenHands / future orchestrator
  │
  ▼
1..N agents/models/tools
```

URACE MUST treat the entire orchestrator as an executor capability provider.

Its internal architecture MUST NOT leak into URACE core.

An orchestrator MAY provide trigger detection, event delivery, periodic execution or wake/resume capabilities.

URACE core MUST NOT depend specifically on one.

---

# 32. Deterministic Executors

Not every operation requires AI.

Examples:

```text
build
test
lint
query
transform
deploy
inspect
validate
reconcile
detect-change
```

MAY be executed by deterministic executors.

URACE SHOULD avoid expensive AI calls when deterministic execution adequately satisfies an operation.

The same principle applies to trigger relevance and periodic discovery.

Obvious trigger filtering, deduplication, state comparison and change discovery SHOULD be deterministic where practical.

Executor-based periodic discovery SHOULD complement rather than unnecessarily replace cheaper deterministic mechanisms.

---

# 33. Human Participation

Humans MAY also be modeled through the generic lifecycle boundary when approval or information is required.

Example:

```text
objective
   │
   ▼
requires irreversible production action
   │
   ▼
WAITING_FOR_APPROVAL
   │
   ▼
relevant trigger condition:
authoritative decision received
   │
   ▼
human decision
   │
   ▼
MEANINGFUL TRIGGER
   │
   ▼
REASSESS
```

Human participation MUST NOT be required for ordinary autonomous cycles unless policy requires it.

External users, customers or market participants MAY additionally provide evidence without becoming lifecycle controllers.

Authoritative human input MAY also modify Product Intent when appropriate.

Such Intent changes SHOULD be persisted with provenance rather than treated as transient executor context.

---

# 34. Policy

Policy governs autonomy independently from executors.

Conceptually:

```text
Policy {
    allowedOperations
    prohibitedOperations
    constraints
    resourceLimits
    budgetPolicy
    schedulePolicy
    retryLimits
    validationRequirements
    readinessRequirements
    approvalRequirements
    deploymentPolicy
    discoveryPolicy?
}
```

Policy SHOULD distinguish hard enforcement boundaries from soft optimization preferences.

Readiness requirements SHOULD be derived from Product Intent rather than assumed globally.

Executors MUST NOT override URACE policy.

Product-value optimization MUST remain subject to Product Intent, policy and constraints.

A metric improvement MUST NOT justify violating applicable:

```text
safety
trust
security
privacy
legal requirements
compliance
accessibility
contracts
protected Product properties
other HARD constraints
```

Policy MAY explicitly permit bounded or one-shot autonomous invocation.

Absent such a contract, runtime termination MUST NOT silently redefine persistent autonomous operation as one-shot execution.

Policy MAY tune:

```text
trigger sensitivity
debounce/reassessment limits
resource use
periodic discovery frequency
executor-assisted discovery frequency
availability retry/backoff
```

Policy MUST NOT redefine an irrelevant event as meaningful solely to keep autonomous activity alive.

Policy MUST NOT define executor unavailability as Product completion merely to simplify runtime termination.

---

# 35. Safety

Continuous autonomy MUST remain bounded locally.

Support configurable controls equivalent to:

```text
maxExecutorAttempts
maxRepairAttempts
maxConsecutiveFailures
maxCycleResourceUse
maxConsecutiveLowValueCycles
maxBudgetUse
maxIdleReassessmentFrequency
maxDiscoveryFrequency
executorAvailabilityBackoff
```

Detect:

- repeated identical failures;
- oscillating plans;
- repeated reversions;
- validation gaming;
- low-value churn;
- premature completion;
- repeated speculative requirements;
- repeated speculative objectives;
- repeated reassessment without new evidence or relevant state change;
- trigger storms;
- repeated duplicate triggers;
- wasteful periodic discovery;
- wasteful executor availability retries;
- metric gaming;
- proxy optimization that degrades material Product/user/customer outcomes;
- repeated self-modification without demonstrated lifecycle value;
- loss of autonomous wakeability;
- busy-waiting or wasteful polling used only to keep a runtime alive.

When progress cannot be justified:

```text
REASSESS
BLOCK
WAIT
PAUSE
IDLE
or request additional evidence
```

rather than mutate indefinitely.

URACE MUST NOT blindly optimize measurable proxies when evidence indicates conflict with Product Intent or intended Product/user/customer value.

Safety controls MUST NOT force `IDLE` when meaningful justified work remains.

They SHOULD instead bound the current execution strategy and trigger reassessment, waiting, blocking or escalation as appropriate.

Liveness MUST NOT be implemented by wasteful activity merely to prevent runtime termination.

Dormant autonomous operation SHOULD consume the minimum resources reasonably required to remain reactivatable and sufficiently aware of potentially material change.

Trigger handling SHOULD prefer cheap relevance filtering before expensive reassessment where doing so does not risk missing material lifecycle changes.

Executor availability retries SHOULD use suitable backoff or equivalent resource-aware behavior.

Backoff MUST NOT silently become permanent lifecycle abandonment.

---

# 36. Workspace Safety

Never destroy unrelated user work.

Do not assume Git.

When Git is present, never automatically use destructive commands such as:

```text
git checkout .
git reset --hard
git clean -fd
```

against an unknown workspace.

Use isolated execution environments where available.

Otherwise track precisely which artifacts belong to the active operation.

Artifact-change trigger detection MUST avoid treating unrelated workspace noise as Product change when the distinction can reasonably be made.

Periodic discovery MUST likewise avoid interpreting unrelated workspace activity as Product-level change without sufficient relevance.

---

# 37. Interruption

On interruption:

1. stop scheduling new operations;
2. cancel active executor operations where supported;
3. persist authoritative state;
4. preserve applicable Product Intent;
5. persist observations and diagnostics;
6. preserve current objective;
7. preserve constraint, budget and schedule state;
8. preserve evidence and relevant lineage;
9. preserve sufficient recovery/wake state and known relevant trigger conditions where autonomous resumption remains intended;
10. preserve enough discovery state to avoid unnecessary duplicate work where useful;
11. release URACE-owned resources;
12. leave unrelated external state untouched.

An explicit user stop or pause MAY intentionally suspend autonomous liveness according to policy.

An accidental process interruption MUST NOT destroy the ability to recover and resume.

Executor interruption MUST NOT be interpreted as an instruction to terminate URACE itself.

---

# 38. Recovery

Restart or wake MUST behave conceptually as:

```text
START / WAKE
  │
  ▼
LOAD DURABLE INTENT + STATE
  │
  ▼
RECONCILE CURRENT PRODUCT
  │
  ▼
RECONCILE LAST OPERATION
  │
  ▼
RECONCILE LIFECYCLE /
WAKE CONDITION
  │
  ▼
RECONCILE EXECUTOR CAPACITY
  │
  ▼
NORMALIZE / INTERPRET
TRIGGER IF APPLICABLE
  │
  ▼
RESUME / RETRY / REASSESS / WAIT
```

Never depend on recovering an old AI conversation to recover URACE.

An `IDLE` Product MUST remain resumable.

A waiting Product MUST remain resumable.

A Product waiting for an executor MUST remain resumable.

Recovery MUST restore lifecycle correctness, not merely deserialize state.

When a wake source provides only a generic signal, URACE SHOULD reconcile current Product/environment state and determine whether a Meaningful Trigger actually occurred.

A stale, duplicate or irrelevant wake signal MUST NOT force Product mutation.

When executor capacity remains unavailable after recovery, URACE MUST return to a live waiting condition rather than interpreting recovery as failed autonomous completion.

---

# 39. Persistence

Use the smallest durable implementation appropriate to the host environment.

A file-based bootstrap MAY use:

```text
.urace/
    state
    policy
    events
    evidence/
    cycles/
    checkpoints/
```

Do NOT make this physical layout part of core semantics.

A future implementation MAY use another persistence mechanism without changing the lifecycle model.

URACE MUST NOT require the Product itself to adopt a URACE-specific directory hierarchy.

Persistence location, naming, hierarchy and storage mechanism are implementation variants.

Intent being first-class MUST NOT require a dedicated Intent service or physical file.

Evidence being first-class MUST NOT imply that evidence requires a dedicated physical directory, database, graph or service.

Meaningful Trigger semantics MUST NOT require a dedicated trigger database, event bus or event store.

Periodic discovery MUST NOT require a dedicated discovery database or service.

Relevant trigger conditions and minimal discovery state MAY be persisted as part of ordinary lifecycle state when doing so is needed for reliable wake/resume behavior.

Likewise:

```text
DURABLE STATE
     ≠
DURABLE WAKEABILITY
```

Persistence MUST NOT be treated as sufficient proof that autonomous operation can reactivate.

---

# 40. No Mandatory Custom RAG

Do NOT make URACE dependent on:

- vector databases;
- embeddings;
- AST databases;
- symbol graphs;
- repository maps;
- context sharding;
- custom RAG;
- evidence graphs;
- dedicated knowledge databases.

An executor MAY use any of them internally.

A deployment MAY use them as persistence/retrieval variants.

URACE only requires enough durable Intent, lifecycle context and evidence lineage to preserve lifecycle correctness.

---

# 41. No Mandatory Model Router

Do NOT require:

- model scoring;
- model ranking;
- provider marketplaces;
- model voting;
- model consensus;
- subscription tracking;
- provider billing logic.

A deployment MAY add executor selection policies later.

They are not part of URACE's defining purpose.

Budget governance MUST remain generic rather than become provider billing infrastructure.

---

# 42. No Mandatory Agent Runtime

URACE MUST NOT require an agent runtime.

This MUST remain valid:

```text
URACE
  │
  ▼
Direct AI API
```

as must:

```text
URACE
  │
  ▼
Agent Runtime
  │
  ▼
AI
```

and:

```text
URACE
  │
  ▼
Orchestrator
  │
  ▼
N agents
```

The direct-AI configuration MUST NOT lose autonomous liveness merely because no external agent runtime or orchestrator exists.

Trigger semantics MUST remain identical across these configurations even if trigger delivery mechanisms differ.

Periodic executor-assisted discovery MUST also remain possible without requiring an agent runtime.

---

# 43. No Mandatory Software Assumption

Do NOT bootstrap URACE around:

```text
compile
source code
pull request
Git commit
package
binary
```

as universal primitives.

They are Product-specific manifestations of:

```text
Artifact
Operation
Observation
Validation
Checkpoint
```

Likewise, do not encode software-specific definitions of Product quality, value, completion or Meaningful Trigger into URACE core.

A file change is only one possible trigger source.

A project-scope change may occur above, below or outside the artifact level.

---

# 44. Conditional Self-Evolution

URACE does not require a privileged self-improvement or self-modification subsystem.

URACE itself MAY be acted upon through the same Product lifecycle when limitations in URACE materially constrain the Product lifecycle it is governing.

The Product or user does NOT need to explicitly nominate URACE as the target before such a limitation can be identified.

The justification originates from the governed lifecycle itself.

Conceptually:

```text
PRODUCT EVOLUTION
      │
      ▼
URACE LIMITATION OBSERVED
      │
      ▼
EVIDENCE SHOWS MATERIAL
LIFECYCLE CONSTRAINT
      │
      ▼
JUSTIFIED GAP
      │
      ▼
URACE-LEVEL REQUIREMENT /
OBJECTIVE
      │
      ▼
MODIFY URACE
      │
      ▼
INDEPENDENT VALIDATION
      │
      ▼
CHECKPOINT
      │
      ▼
UPDATED EVIDENCE
      │
      ▼
RESUME / REASSESS
PRODUCT EVOLUTION
```

Examples of potentially justified URACE limitations MAY include deficiencies in:

```text
lifecycle control
Intent preservation
evidence handling
executor abstraction
validation
recovery
checkpointing
constraint enforcement
capacity handling
readiness assessment
autonomous liveness
trigger interpretation
change discovery
wake/resume behavior
```

These examples MUST NOT become a mandatory self-improvement checklist.

A URACE limitation becomes actionable only when its improvement is sufficiently justified under the same lifecycle rules governing ordinary Product evolution.

Therefore:

```text
URACE CAN CHANGE ITSELF
        ≠
URACE SHOULD CONTINUOUSLY
CHANGE ITSELF
```

and:

```text
POSSIBLE URACE IMPROVEMENT
        ≠
JUSTIFIED URACE OBJECTIVE
```

Any URACE-level change MUST remain subject to the same:

- Intent;
- evidence requirements;
- justification;
- HARD constraints;
- policy;
- budgets;
- schedules;
- safety controls;
- validation;
- checkpointing;
- anti-churn rules;
- convergence rules.

Self-evolution MUST NOT bypass ordinary lifecycle governance.

URACE MUST NOT modify itself merely because:

- an executor proposes an improvement;
- a different architecture is possible;
- a speculative abstraction could be added;
- autonomous mode remains enabled;
- resources remain available.

If changing URACE is not required or sufficiently valuable for advancing the governed Product lifecycle relative to Intent, URACE SHOULD leave itself unchanged.

Conditional self-evolution is therefore an emergent application of the ordinary URACE lifecycle, not a separate privileged lifecycle.

---

# 45. Minimal Core

Bootstrap only the smallest coherent core required for:

```text
Product
Intent
State
Evidence
Requirement
Objective
Operation
Executor
Observation
Validation
Checkpoint
Policy
Lifecycle
Persistence
```

Intent is first-class because lifecycle direction, objective justification, Product-value evaluation and readiness depend on it.

Evidence is first-class because justified autonomous decisions depend on durable knowledge and provenance.

Autonomous liveness, open-ended change awareness and Meaningful Trigger semantics are invariant lifecycle properties.

They do NOT require first-class `Liveness`, `Trigger`, `Discovery` or `ExecutorAvailability` objects or dedicated subsystems.

Product Value is not required to be first-class.

It MAY remain a derived evaluation concept unless a future implementation demonstrates a concrete lifecycle requirement to persist or address value independently from Intent, Evidence, Requirements and Objectives.

Specific Product-value dimensions such as:

```text
conversion
retention
loyalty
engagement
cognitive load
customer effort
customer cost
trust
productivity
```

MUST NOT become first-class core primitives merely because they are useful for some Products.

Constraint, budget, schedule, evidence-lineage, liveness, trigger, discovery and readiness semantics SHOULD remain simple lifecycle data/policy rather than automatically becoming large independent frameworks.

Avoid turning every concept into a large framework.

Prefer simple data contracts and composable modules.

The core SHOULD encode invariants.

Variants SHOULD remain outside the core whenever practical.

---

# 46. Suggested Logical Structure

Conceptually:

```text
core/
    lifecycle
    state
    intent
    objective
    policy

execution/
    executor
    registry
    capabilities

evidence/
    store

validation/
    policy
    runner

checkpoint/
    store

persistence/
    store

discovery/
    product

cli/
    commands
```

This is guidance, not a mandatory filesystem structure.

`intent` represents a logical responsibility, not a requirement for a dedicated module or file.

Lifecycle liveness, Meaningful Trigger interpretation and periodic discovery MAY remain part of `lifecycle`, `state`, `discovery`, host integration or another appropriate responsibility.

A dedicated `liveness/`, `trigger/`, `events/` or periodic-monitoring subsystem is NOT required.

Follow repository conventions when a better implementation exists.

An implementation MAY combine, rename, relocate or differently represent these responsibilities.

The conceptual `evidence/` responsibility does not require a dedicated physical subsystem.

No directory name or hierarchy above is part of URACE core semantics.

---

# 47. Bootstrap Sequence

## Step 1 — Inspect

Inspect the existing Product/repository/workspace.

Determine whether it is:

```text
EMPTY
EXISTING
URACE_INITIALIZED
```

Do not destroy existing work.

Discover structure before imposing structure.

---

## Step 2 — Choose Minimal Implementation Technology

Choose the smallest mainstream implementation appropriate for the environment.

Do not introduce unnecessary:

- microservices;
- databases;
- queues;
- containers;
- vector stores;
- orchestration frameworks;
- multiple languages.

The implementation language MUST NOT leak into URACE's public lifecycle semantics.

The selected implementation MUST provide or integrate with a viable autonomous wake/resume mechanism when persistent autonomous operation requires dormancy.

Do not introduce heavyweight infrastructure merely to satisfy liveness or trigger delivery when a simpler host-native mechanism is sufficient.

---

## Step 3 — Implement Durable State

Implement:

- Product;
- Intent;
- ProductState;
- evidence and sufficient lineage;
- requirements/objectives;
- lifecycle state;
- history;
- checkpoints;
- policy;
- constraints;
- budget/schedule state;
- readiness state;
- enough liveness/wake state to preserve autonomous semantics where required;
- enough relevant trigger-condition state to recover dormant lifecycle semantics where required;
- enough executor-capacity state to distinguish waiting from completion;
- minimal discovery state where needed to support bounded periodic change discovery.

Intent MAY be embedded within Product/ProductState or durably referenced.

First-class status does NOT require independent physical storage.

Liveness, discovery and trigger conditions MAY be represented by state, host guarantees, registered wake conditions or another minimal mechanism.

Test restart durability.

---

## Step 4 — Implement Generic Executor Contract

Implement the generic executor interface.

Do not mention any specific AI/orchestrator in core.

Executor unavailability MUST produce a capacity condition rather than lifecycle termination.

---

## Step 5 — Implement One Direct Intelligent Executor

Implement or configure the smallest adapter allowing:

```text
URACE
  │
  ▼
ONE AI
```

to perform intelligent operations.

This proves that no external orchestrator is required.

The direct configuration MUST remain capable of persistent autonomous operation without relying on an external orchestrator for lifecycle liveness.

Temporary unavailability of that one AI MUST NOT terminate the autonomous lifecycle.

---

## Step 6 — Implement Capability Discovery

Allow executors to advertise capabilities.

URACE MUST be able to determine whether an operation can currently be attempted.

Capability discovery SHOULD distinguish:

```text
capability does not exist

capability exists but
no compatible executor is currently available

capability availability unknown
```

These states MUST NOT be conflated with Product completion.

---

## Step 7 — Implement Generic Product Discovery

Discover enough about the current Product to expose:

```text
Intent
artifacts
available operations
validation possibilities
environment constraints
existing structure
applicable schedules
applicable budgets
available evidence
applicable readiness criteria
applicable Product-value dimensions
available wake/resume capabilities
observable trigger sources
relevant Product/project scopes
```

Do not require a known Product type.

For Products with users/customers, applicable evidence MAY include customer outcomes, friction, effort, cognitive load, cost, acquisition, conversion, activation, adoption, engagement, retention, loyalty, satisfaction or other Intent-relevant signals.

Do not require these dimensions for Products where they are irrelevant.

Trigger-source discovery SHOULD remain opportunistic.

URACE MUST NOT require every possible future trigger source or project-scope change to be known during bootstrap.

Periodic discovery SHOULD provide a bounded fallback when relevant changes may otherwise remain invisible.

---

## Step 8 — Implement Validation

Implement executor-independent acceptance.

Use deterministic validation wherever possible.

Allow Product-specific validation configuration.

Support Product-level readiness assessment without hard-coding one universal definition of quality or value.

Where an objective targets an external Product/user/customer outcome that cannot be deterministically validated, preserve the result as unvalidated or partially validated until sufficient external evidence exists.

---

## Step 9 — Implement Checkpoints

Persist accepted increments without assuming Git.

Use Git when available and useful.

Preserve enough Intent and evidence references to reconstruct material acceptance decisions.

---

## Step 10 — Implement `--plan`

Perform assessment without mutation.

---

## Step 11 — Implement `--check`

Expose authoritative lifecycle state.

Include enough information to distinguish:

```text
ACTIVE
WAITING
BLOCKED
PAUSED
IDLE
```

and explain why the state is justified relative to Product Intent and evidence.

When autonomous operation remains enabled, `--check` SHOULD also expose:

```text
whether lifecycle liveness is preserved

known relevant trigger conditions

whether an external wake mechanism
currently owns reactivation responsibility

current executor/capacity state

last Meaningful Trigger where relevant

last meaningful discovery/reconciliation
where useful
```

without requiring disclosure of irrelevant raw-event noise.

---

## Step 12 — Implement `--autonomous`

Implement:

```text
while autonomous operation remains enabled:

    load Intent and state

    gather available:
        Product evidence
        user/customer/market evidence where applicable
        environmental evidence

    reconcile relevant Product/project/lifecycle state

    preserve relevant evidence provenance
    and lifecycle lineage

    determine current lifecycle condition

    evaluate applicable:
        hard constraints
        soft constraints
        schedules
        budgets
        risks
        readiness requirements

    assess Product against Intent and evidence

    identify highest-value justified gap

    evaluate expected Product value
    against Intent, evidence, cost,
    risk, constraints and opportunity cost

    formulate a requirement/objective only
    when the gap justifies action

    if the material gap is caused by a limitation
    in URACE itself:
        allow that limitation to become a normal
        justified objective when sufficiently valuable

    if no justified objective exists:

        perform completion/readiness assessment

        if material readiness gap exists:
            formulate the highest-value actionable
            requirement/objective
            continue

        identify known conditions that could
        materially change the current assessment

        persist IDLE / WAITING state
        and sufficient wake/resume context

        if a durable external wake/resume mechanism
        is available and capable of surfacing
        relevant candidate conditions:
            transfer reactivation responsibility
            and allow the current runtime to become
            dormant or terminate when appropriate

        else:
            remain efficiently capable of observing
            relevant candidate conditions without
            busy-waiting or unnecessary executor use

        periodically, according to policy,
        risk, cost, budget and context:

            perform bounded change discovery
            when event coverage may be incomplete

            prefer deterministic inspection
            where sufficient

            if executor-assisted discovery is useful:

                attempt to locate a compatible executor

                if executor unavailable:
                    update capacity state
                    apply appropriate retry/backoff
                    remain autonomously live
                    DO NOT terminate the lifecycle
                    solely because executor is unavailable

                else:
                    use executor for bounded inspection
                    of relevant Product/project/lifecycle
                    and environmental scope

            if a material or potentially material
            change is discovered:
                treat it as a candidate trigger

        when a candidate event/condition/change
        is observed or discovered:

            normalize it

            reject obvious duplicates,
            stale signals and irrelevant noise
            where practical

            determine whether it could materially
            change the prior lifecycle assessment

            if not meaningful:
                remain / return dormant
                continue

            treat it as a Meaningful Trigger

            reconcile current Product/environment state

            reassess

            continue

    derive required capabilities

    locate compatible executor(s)

    if required capacity unavailable:

        persist WAITING_FOR_CAPACITY

        identify relevant trigger conditions,
        including:
            required compatible capacity becomes available
            blocking capacity condition changes

        preserve a viable wake/resume path

        observe capacity through the cheapest
        suitable available mechanism

        periodically retry executor discovery
        according to policy and backoff

        if executor remains unavailable:
            remain WAITING_FOR_CAPACITY
            remain autonomously live
            DO NOT exit persistent autonomous operation
            merely because no executor is available

        if durable external wake/resume exists:
            runtime MAY become dormant or terminate
            only after that mechanism has assumed
            responsibility for future reactivation

        else:
            the responsible runtime MUST remain
            efficiently capable of future observation

        on material capacity change:
            treat as candidate Meaningful Trigger
            reassess

        continue

    if operation would violate a HARD constraint:

        persist blocked state

        identify any known condition whose change
        could make the blocked decision different

        if such condition can later change:
            preserve a viable wake/resume path

        continue according to policy

    if operation exceeds a HARD budget:

        persist blocked/waiting state

        identify any budget/quota condition that
        could later change available action

        preserve wake/resume semantics

        continue according to policy

    execute bounded operation(s)

    persist observations

    independently validate candidate

    if validation fails:
        perform bounded repair/reassessment

    if accepted:
        checkpoint increment
        update authoritative ProductState

    gather or update resulting evidence

    begin a fresh assessment cycle
```

Autonomous execution does not require an endless active process.

The lifecycle remains persistent while execution MAY become dormant.

However, dormancy MUST preserve autonomous liveness.

There is no predetermined cycle count.

Each accepted increment MAY lead to another assessment cycle, and another justified cycle MAY follow for as long as meaningful Product evolution remains justified.

A standalone foreground invocation of `--autonomous` MUST NOT simply return because:

```text
the Product reaches IDLE
the Product reaches WAITING
an executor becomes unavailable
all intelligent executors become unavailable
a periodic executor-assisted discovery attempt fails
no objective is immediately executable
```

unless bounded execution was explicitly requested or another durable mechanism has assumed responsibility for future reassessment.

Meaningful Trigger evaluation MUST NOT itself imply Product mutation.

The mandatory transition is:

```text
MEANINGFUL TRIGGER
        │
        ▼
RECONCILE
        │
        ▼
ASSESS
```

not:

```text
MEANINGFUL TRIGGER
        │
        ▼
MUTATE PRODUCT
```

Executor availability affects:

```text
WHAT CAN EXECUTE NOW
```

not:

```text
WHETHER URACE CONTINUES
TO OWN THE AUTONOMOUS
PRODUCT LIFECYCLE
```

---

# 48. Mandatory Agnosticism Tests

Bootstrap MUST demonstrate all of the following.

## Test A — One AI

```text
URACE → ONE AI
```

Complete multiple autonomous cycles.

No OpenHands.

No multi-agent framework.

---

## Test B — Executor Replacement

```text
CURRENT CYCLE → Executor A
Checkpoint
NEXT JUSTIFIED CYCLE → Executor B
```

Product continuity MUST survive replacement.

The test MUST NOT imply that only one subsequent cycle is permitted.

---

## Test C — Fresh Context

Terminate the intelligent executor completely.

Start a fresh executor session.

Continue using only durable URACE context.

---

## Test D — Unknown Product Type

Run against a Product that does not match a hard-coded template.

Core lifecycle MUST remain operational.

---

## Test E — Language Independence

Use at least two materially different software-language ecosystems without modifying URACE core semantics.

---

## Test F — Non-Software or Mixed Artifact

Demonstrate lifecycle operation over a Product containing artifacts that are not exclusively source code.

---

## Test G — Unknown File Type

Introduce an artifact URACE core does not understand.

URACE MUST preserve and address it generically and delegate interpretation when a capable executor exists.

---

## Test H — No Git

Demonstrate checkpoint semantics without requiring Git.

---

## Test I — Orchestrator

Optionally configure:

```text
URACE
  │
  ▼
OpenHands or another orchestrator
  │
  ▼
1..N AIs
```

No URACE core changes should be necessary.

---

## Test J — Capacity Loss

Lose the intelligent executor between cycles.

Persist:

```text
WAITING_FOR_CAPACITY
```

Preserve a viable wake/resume path.

Continue the autonomous lifecycle without Product mutation while capacity remains unavailable.

Periodically retry capacity discovery according to policy.

Restore compatible capacity.

Treat the material capacity transition as a candidate Meaningful Trigger.

Reassess and continue when justified.

The autonomous lifecycle MUST NOT terminate merely because the executor was unavailable.

---

## Test K — Restart

Terminate URACE.

Restart or wake it through the configured runtime mechanism.

Continue autonomous evolution from authoritative state.

---

## Test L — Validation Failure

Cause a repairable candidate failure.

Prove:

```text
candidate
   ↓
validation fail
   ↓
bounded repair
   ↓
revalidation
   ↓
checkpoint
```

---

## Test M — Structural Independence

Run URACE against materially different repository/workspace structures.

Prove:

```text
Product A ── structure A
Product B ── structure B
Product C ── unfamiliar structure
```

without modifying URACE core lifecycle semantics.

No URACE-defined Product folder hierarchy may be required.

---

## Test N — Hard vs Soft Constraints

Provide conflicting constraints with different strengths.

Prove:

```text
HARD constraint
      │
      ▼
cannot be autonomously violated

SOFT constraint
      │
      ▼
guides selection
without unnecessarily gating progress
```

URACE MUST NOT silently promote the SOFT constraint to HARD.

---

## Test O — Budget Bound

Provide a finite resource budget.

Prove that URACE:

```text
observes budget
allocates resource
preserves validation/recovery capacity
does not exceed HARD ceiling
does not invent work to consume remainder
```

---

## Test P — Scheduled Work

Provide a future lifecycle condition.

Prove:

```text
persist state
    ↓
preserve wake path
    ↓
WAIT
    ↓
condition becomes applicable
    ↓
MEANINGFUL TRIGGER
    ↓
REASSESS
```

without requiring continuous active execution.

---

## Test Q — No Premature IDLE

Provide a Product with:

```text
no active objective
but
material unresolved readiness gap
```

Prove:

```text
ASSESS
   │
   ▼
no current objective
   │
   ▼
READINESS ASSESSMENT
   │
   ▼
material gap discovered
   │
   ▼
JUSTIFIED REQUIREMENT / OBJECTIVE
```

URACE MUST NOT enter `IDLE`.

The applicable readiness gap MUST be derived from Product Intent.

---

## Test R — Autonomous Convergence

Provide:

```text
Intent sufficiently satisfied
hard constraints satisfied
validation satisfied
no material defect
no material unresolved risk
applicable readiness satisfied
no actionable high-value evidence gap
no justified improvement with sufficient expected value
```

Prove:

```text
ASSESS
   │
   ▼
READINESS ASSESSMENT
   │
   ▼
READY
   │
   ▼
IDLE
   │
   ▼
PRESERVE LIVENESS
```

No mutation, executor invocation or recursive requirement/objective generation SHOULD occur merely to keep autonomous mode active.

Then introduce a Meaningful Trigger and prove:

```text
IDLE
  │
  ▼
MEANINGFUL TRIGGER
  │
  ▼
ASSESS
  │
  ├────► ACTIVE when justified
  │
  └────► IDLE when assessment remains unchanged
```

without loss of durable lifecycle continuity.

---

## Test S — Anti-Perfection Loop

Provide a Product that satisfies applicable readiness requirements while numerous theoretically possible low-value refinements remain.

Prove that URACE distinguishes:

```text
possible improvement
        ≠
justified requirement
        ≠
justified objective
```

and enters `IDLE` rather than performing endless polishing.

`IDLE` MUST remain autonomously resumable.

---

## Test T — Evidence-to-Requirement Loop

Provide new Product, user, customer, market or environmental evidence revealing a material gap.

Prove:

```text
INTENT
   │
   ▼
EVIDENCE
   │
   ▼
ASSESS
   │
   ▼
MATERIAL GAP
   │
   ▼
JUSTIFIED REQUIREMENT
   │
   ▼
IMPLEMENT
   │
   ▼
OBSERVE
   │
   ▼
VALIDATE
   │
   ▼
CHECKPOINT
   │
   ▼
UPDATED EVIDENCE
```

The requirement MUST remain traceable to Intent and evidence.

The resulting evidence MUST remain distinguishable from assumptions, inferences and hypotheses.

---

## Test U — Readiness Variant

Run URACE against Products with materially different intents.

For example:

```text
commercial Product
internal tool
library
research Product
infrastructure Product
```

Prove that Product-specific readiness criteria can vary without changing URACE core lifecycle semantics.

---

## Test V — Invariant Preservation

Replace major variants such as:

```text
executor
model
orchestrator
language
repository structure
validation mechanism
checkpoint mechanism
scheduler
wake mechanism
trigger source
trigger-delivery mechanism
periodic discovery mechanism
runtime model
evidence storage mechanism
Product-value dimensions
```

and prove that the Core Invariants remain true.

---

## Test W — Evidence Lineage

Provide evidence that results in a material autonomous decision.

Prove that URACE can reconstruct:

```text
INTENT
   │
   ▼
SOURCE / OBSERVATION
        │
        ▼
EVIDENCE
        │
        ▼
ASSESSMENT
        │
        ▼
JUSTIFIED GAP
        │
        ▼
REQUIREMENT / OBJECTIVE
        │
        ▼
DECISION / EXECUTION
        │
        ▼
VALIDATION
        │
        ▼
CHECKPOINT
```

without requiring a dedicated evidence database, knowledge graph or RAG system.

---

## Test X — Conditional Self-Evolution

Provide a Product whose progress is materially constrained by a demonstrable URACE limitation.

Do NOT explicitly instruct URACE to modify itself.

Prove:

```text
PRODUCT LIFECYCLE
        │
        ▼
URACE LIMITATION OBSERVED
        │
        ▼
MATERIAL IMPACT ESTABLISHED
        │
        ▼
JUSTIFIED URACE-LEVEL OBJECTIVE
        │
        ▼
BOUNDED CHANGE
        │
        ▼
VALIDATION
        │
        ▼
CHECKPOINT
        │
        ▼
PRODUCT LIFECYCLE CONTINUES
```

Then provide a merely speculative or cosmetic URACE improvement.

Prove that no self-modification occurs solely because improvement is possible.

---

## Test Y — Intent Persistence

Provide a Product with durable Intent.

Replace the executor, terminate all executor context and restart URACE.

Prove:

```text
INTENT
  │
  ▼
Executor A
  │
  ▼
checkpoint / restart
  │
  ▼
Executor B
  │
  ▼
same applicable Product direction
```

No executor's private context may be required to reconstruct the applicable Product Intent.

---

## Test Z — Intent vs Objective

Provide a Product whose current objective completes.

Prove:

```text
OBJECTIVE COMPLETE
       │
       ▼
INTENT REMAINS
       │
       ▼
REASSESS
       │
 ┌─────┴─────┐
 ▼           ▼
new gap     ready
 │           │
 ▼           ▼
objective   IDLE
               │
               ▼
        preserve liveness
```

Completion of one objective MUST NOT be interpreted as completion or replacement of Product Intent.

---

## Test AA — Intent-Relative Product Value

Provide a Product with evidence that a material user/customer-value problem exists.

For example:

```text
PRODUCT INTENT
      │
      ▼
high decision friction
      │
      ▼
poor conversion
      │
      ▼
evidence-supported causal hypothesis
      │
      ▼
justified objective
      │
      ▼
Product change
      │
      ▼
external evidence
```

Prove that URACE MAY act on the relevant value dimension when justified.

Then provide another Product where conversion is irrelevant to Intent.

Prove that URACE does NOT create conversion objectives merely because conversion is a known Product metric.

The same principle MUST hold for retention, engagement, loyalty, cognitive load, customer effort, customer cost and other example dimensions.

---

## Test AB — Multi-Dimensional Product Value

Provide a proposed change that improves one measurable metric while materially degrading another applicable Product outcome.

For example:

```text
conversion ↑
but
trust / retention / customer outcome ↓
```

Prove that URACE does not blindly accept the isolated metric improvement.

Objective selection and validation MUST remain grounded in Product Intent, evidence, constraints, expected value and trade-offs.

---

## Test AC — Autonomous Liveness Without External Orchestrator

Run the minimal configuration:

```text
URACE
  │
  ▼
ONE AI
```

with no external orchestrator.

Allow the Product to reach `IDLE`.

Prove that:

```text
IDLE
  │
  ▼
no unnecessary AI/executor activity
  │
  ▼
autonomous liveness preserved
  │
  ▼
event / periodic discovery
  │
  ▼
Meaningful Trigger
  │
  ▼
ASSESS
```

The implementation MUST NOT simply return from persistent `--autonomous` execution and lose all path to reassessment.

---

## Test AD — Safe Runtime Dormancy

Configure a durable external wake/resume mechanism.

Prove:

```text
ACTIVE
  │
  ▼
IDLE / WAITING
  │
  ▼
persist state
  │
  ▼
durable wake responsibility established
  │
  ▼
runtime may terminate
  │
  ▼
candidate condition
  │
  ▼
new runtime
  │
  ▼
load + reconcile state
  │
  ▼
evaluate Meaningful Trigger
  │
  ▼
ASSESS when meaningful
```

The active runtime MAY terminate because lifecycle liveness remains guaranteed externally.

---

## Test AE — Persistence Is Not Wakeability

Persist a valid `IDLE` or `WAITING` Product state without configuring any external wake mechanism.

Prove that URACE does NOT treat successful persistence alone as sufficient justification for terminating the only runtime responsible for autonomous operation.

Conceptually:

```text
state persisted
      +
no wake path
      │
      ▼
runtime termination prohibited
for persistent autonomous mode
```

unless bounded/one-shot execution was explicitly requested or policy requires termination.

---

## Test AF — Trigger Relevance

While Product is `IDLE`, produce:

```text
irrelevant raw event
duplicate event
stale event
relevant Product change
```

Prove:

```text
irrelevant / duplicate / stale
        │
        ▼
no unnecessary full reassessment

relevant Product change
        │
        ▼
Meaningful Trigger
        │
        ▼
ASSESS
```

The relevant event MUST NOT automatically create an objective.

---

## Test AG — Trigger Without Mutation

Provide a Meaningful Trigger that reasonably could change lifecycle assessment but, after reconciliation, does not reveal a justified gap.

Prove:

```text
MEANINGFUL TRIGGER
        │
        ▼
ASSESS
        │
        ▼
NO MATERIAL JUSTIFIED CHANGE
        │
        ▼
IDLE / WAIT
```

No Product mutation is required merely because the trigger was meaningful enough to justify reassessment.

---

## Test AH — Trigger Mechanism Replacement

Run equivalent autonomous lifecycle behavior using materially different trigger mechanisms.

For example:

```text
watcher
scheduler
webhook / event
periodic discovery
platform-native wake
```

Prove that replacing the mechanism does not change:

```text
trigger meaning
reassessment semantics
Product Intent
objective justification
validation
convergence
```

No mechanism above is mandatory.

---

## Test AI — Trigger Storm

Generate a burst of equivalent or closely related raw events.

Prove that URACE avoids unnecessary repeated expensive reassessment through appropriate deterministic filtering, deduplication, coalescing or equivalent behavior without losing a distinct material change.

---

## Test AJ — Unknown Trigger Source

Introduce a relevant Product/environment change through a source not explicitly enumerated during bootstrap.

Prove:

```text
unknown raw source
      │
      ▼
observation / discovery
      │
      ▼
relevance evaluation
      │
      ▼
Meaningful Trigger
      │
      ▼
ASSESS
```

when the change could materially affect the lifecycle.

URACE MUST NOT require a closed trigger-source registry.

---

## Test AK — Any-Scope Project Change

Change a relevant property at materially different Product/project scope levels.

For example:

```text
Intent
goal
requirement
artifact
dependency
environment
constraint
executor capacity
URACE lifecycle mechanism
```

Prove that no scope level is categorically excluded from Meaningful Trigger consideration.

The same relevance criterion MUST apply:

```text
COULD THIS CHANGE
MATERIALLY ALTER
THE PRIOR ASSESSMENT?
```

---

## Test AL — Periodic Executor-Assisted Discovery

Place the Product in `IDLE`.

Introduce a material change that no configured event source directly reports.

At a bounded periodic discovery opportunity:

```text
executor available
      │
      ▼
bounded Product/project inspection
      │
      ▼
material change discovered
      │
      ▼
Meaningful Trigger
      │
      ▼
ASSESS
```

Prove that autonomous Product evolution can resume.

The periodic executor invocation itself MUST NOT be treated as sufficient evidence of Product work.

---

## Test AM — Periodic Discovery Finds Nothing

Place the Product in `IDLE`.

Perform a periodic deterministic or executor-assisted discovery attempt.

Discover no material change.

Prove:

```text
PERIODIC DISCOVERY
        │
        ▼
NO MATERIAL CHANGE
        │
        ▼
IDLE
```

without manufacturing a requirement, objective or Product mutation.

---

## Test AN — Executor Unavailable During Periodic Re-Trigger

Place the Product in a dormant autonomous state.

At a scheduled periodic executor-assisted discovery opportunity, make the executor unavailable.

Prove:

```text
DISCOVERY OPPORTUNITY
        │
        ▼
EXECUTOR UNAVAILABLE
        │
        ▼
UPDATE CAPACITY STATE
        │
        ▼
WAIT / BACKOFF
        │
        ▼
AUTONOMOUS LIFECYCLE REMAINS LIVE
```

The event loop/lifecycle MUST NOT terminate merely because the executor is unavailable.

When executor availability later changes materially:

```text
EXECUTOR AVAILABLE
        │
        ▼
Meaningful Trigger candidate
        │
        ▼
REASSESS / DISCOVER
```

---

## Test AO — All Executors Unavailable

Make every intelligent executor unavailable while meaningful justified Product work remains.

Prove:

```text
JUSTIFIED WORK EXISTS
        │
        ▼
NO EXECUTOR AVAILABLE
        │
        ▼
WAITING_FOR_CAPACITY
        │
        ▼
PRESERVE STATE + LIVENESS
        │
        ▼
RETRY / OBSERVE
        │
        ▼
EXECUTOR RESTORED
        │
        ▼
REASSESS
        │
        ▼
CONTINUE
```

No executor availability state may silently convert justified unfinished work into `IDLE`, completion or autonomous termination.

---

# 49. Market/Product Demonstration

For a Product with market intent, demonstrate:

```text
PRODUCT INTENT
      │
      ▼
PRODUCT STATE
      │
      ▼
MARKET / USER / CUSTOMER / PRODUCT EVIDENCE
      │
      ▼
ASSESSMENT
      │
      ▼
MATERIAL GAP
      │
      ▼
JUSTIFIED REQUIREMENT / OBJECTIVE
      │
      ▼
PRODUCT INCREMENT
      │
      ▼
VALIDATION
      │
      ▼
CHECKPOINT
      │
      ▼
NEW EVIDENCE / ASSUMPTIONS
      │
      ▼
NEXT JUSTIFIED ASSESSMENT CYCLE
```

The demonstration MUST preserve the distinction between:

```text
fact
evidence
inference
hypothesis
```

Where relevant, Product evolution MAY reason across a customer lifecycle such as:

```text
DISCOVERY / ACQUISITION
          │
          ▼
DECISION / CONVERSION
          │
          ▼
ACTIVATION / ADOPTION
          │
          ▼
REALIZED CUSTOMER VALUE
          │
          ▼
RETENTION / LOYALTY
```

This sequence is illustrative only.

Different Products MAY have:

- different customer journeys;
- non-linear journeys;
- multiple simultaneous journeys;
- no meaningful customer journey at all.

Across any applicable stage, URACE MAY identify cross-cutting value opportunities such as:

```text
reduce friction
reduce cognitive load
reduce customer effort
reduce customer cost
increase clarity
increase usability
increase accessibility
increase reliability
increase trust
increase productivity
improve intended customer outcomes
```

URACE MUST NOT assume these opportunities exist.

Product Intent and evidence determine whether they become justified objectives.

For a market-intended Product, an applicable progression MAY be:

```text
TECHNICALLY VALID
        │
        ▼
PRODUCT READY
        │
        ▼
MARKET-FIT-QUALITY READY
        │
        ▼
EXTERNAL MARKET / CUSTOMER EVIDENCE
```

URACE MAY autonomously drive the first three stages where capability, evidence and policy permit.

The final stage depends on actual external evidence and MUST NOT be fabricated.

If market/customer evidence demonstrates a material mismatch:

```text
IDLE / READY
      │
      ▼
NEW EXTERNAL OBSERVATION
      │
      ▼
MEANINGFUL TRIGGER
      │
      ▼
ASSESS AGAINST INTENT
      │
      ▼
MATERIAL GAP
      │
      ▼
JUSTIFIED REQUIREMENT
```

The Product lifecycle resumes.

If the external change is not directly reported, periodic discovery MAY reveal it.

The mechanism that surfaces new external evidence and reactivates assessment remains a variant.

The semantic determination that the new information can materially affect the lifecycle belongs to URACE.

This section demonstrates one Product-specific readiness/value variant.

It does not redefine customer or market metrics as universal URACE invariants.

---

# 50. Anti-Churn Demonstration

Prove that continuous autonomy does not mean arbitrary activity.

Given:

```text
no new evidence
no meaningful state change
no meaningful defect
no material readiness gap
no justified improvement
no unresolved objective
```

URACE MUST NOT repeatedly modify or fully reassess the Product simply because an executor remains available or a timer fires.

Periodic discovery MAY still occur according to policy.

Such discovery MUST be bounded and proportionate.

The same rule applies to URACE itself.

URACE MUST NOT repeatedly optimize:

```text
conversion
engagement
retention
cost
friction
or another measurable Product metric
```

after further changes cease to have sufficiently justified Product value relative to Intent.

URACE MUST NOT repeatedly self-modify simply because improvements to its own implementation can be imagined.

It MAY:

- reassess later;
- perform bounded periodic discovery;
- wait for evidence;
- wait for executor capacity;
- wait for a scheduled condition;
- become `IDLE` while autonomous mode remains enabled.

However, `no unresolved objective` alone is insufficient.

Before `IDLE`, URACE MUST establish that no material Product-level readiness gap is being hidden by an empty objective list.

The preferred convergence is:

```text
INTENT
  │
  ▼
ASSESS
   │
   ▼
NO OBJECTIVE
   │
   ▼
READINESS ASSESSMENT
   │
 ┌─┴─────────────┐
 ▼               ▼
GAP             READY
 │               │
 ▼               ▼
REQUIREMENT     IDLE
 │               │
 ▼               ▼
ACTIVE      PRESERVE LIVENESS
                 │
        ┌────────┼────────┐
        ▼        ▼        ▼
      EVENT    TIME    PERIODIC
                       DISCOVERY
        │        │        │
        └────────┼────────┘
                 ▼
          CANDIDATE CHANGE
                 │
                 ▼
          MEANINGFUL TRIGGER
                 │
                 ▼
              ASSESS
```

This prevents premature completion, endless autonomous churn and dead autonomous dormancy.

Preserving liveness MUST NOT itself create artificial Product work or repeated unnecessary AI calls.

A wake signal or periodic discovery that reveals no meaningful lifecycle change SHOULD return the Product to dormancy without manufacturing work.

An unavailable executor SHOULD return the lifecycle to waiting/backoff without terminating it.

---

# 51. Success Criteria

URACE is successfully bootstrapped when:

1. Its lifecycle survives individual AI sessions.
2. It works with exactly one AI.
3. It does not require an orchestrator.
4. It can use an orchestrator without changing core semantics.
5. Executors can be replaced between cycles.
6. No executor's private memory is required for continuity.
7. It is AI-provider agnostic.
8. It is model agnostic.
9. It is executor-count agnostic.
10. It is orchestrator agnostic.
11. It is programming-language agnostic.
12. It is Product-type agnostic.
13. It is file-format agnostic.
14. It is repository-host agnostic.
15. It is version-control agnostic.
16. It is operating-system/platform agnostic at the lifecycle level.
17. It is cloud-provider agnostic.
18. It supports software and non-software/mixed artifacts.
19. It independently validates executor results.
20. It produces recoverable checkpoints.
21. It preserves Intent, evidence, provenance, lineage and assumptions sufficiently for lifecycle correctness.
22. It can continue after capacity interruption.
23. It can continue after process restart.
24. It does not require custom RAG.
25. It does not require multi-agent infrastructure.
26. It does not require custom model routing.
27. It does not duplicate mature executor intelligence.
28. Continuous autonomy produces justified progress rather than arbitrary churn.
29. Product lifecycle semantics remain stable while underlying AI technology changes.
30. The implementation is significantly smaller and simpler than the intelligence systems it can coordinate.
31. It distinguishes hard constraints from soft constraints.
32. Soft constraints guide autonomy without unnecessarily becoming execution gates.
33. Hard constraints remain enforceable independently from executor behavior.
34. Product filesystem, folder and repository structure are not part of core lifecycle semantics.
35. It operates across materially different physical Product structures without core changes.
36. It can represent and enforce hard resource budgets.
37. It can optimize around soft resource budgets.
38. It can represent deadlines, schedules, waits and temporal conditions without requiring a particular scheduler.
39. Autonomous execution can converge to `IDLE` when no justified work remains.
40. `IDLE` preserves lifecycle continuity without continuous Product mutation or unnecessary executor use.
41. `IDLE` requires Product-level readiness assessment rather than merely an empty task/objective list.
42. Material unresolved defects, risks or readiness gaps prevent premature `IDLE`.
43. Low-value speculative improvement does not prevent justified `IDLE`.
44. A Meaningful Trigger can resume assessment from `IDLE`.
45. Readiness is derived from Product Intent rather than one universal Product-quality definition.
46. Market validation remains evidence-based where applicable and is never inferred solely from AI opinion.
47. Budget, schedule, constraint and structural semantics remain portable across executor replacement.
48. The lifecycle avoids both premature completion and endless perfection loops.
49. Product, user, customer, market and environmental evidence can produce traceable justified requirements where applicable.
50. Requirements do not exist independently from their Product justification.
51. Implementation results feed new evidence into subsequent assessment.
52. Market/customer analysis remains an input/capability rather than becoming a mandatory URACE subsystem.
53. Core invariants remain stable while implementation and strategy variants change.
54. Product-specific readiness criteria can change without redefining URACE.
55. Variants remain replaceable unless promoting one is required to preserve a Core Invariant.
56. Evidence is a first-class lifecycle primitive without requiring a heavyweight evidence subsystem.
57. Material lifecycle decisions preserve sufficient evidence lineage to reconstruct their justification.
58. Observations, assumptions, inferences, hypotheses and validated evidence remain meaningfully distinguishable.
59. Product Intent is a first-class lifecycle primitive without requiring a dedicated Intent subsystem.
60. Product Intent survives executor replacement, restart and objective completion.
61. Objectives remain subordinate to Product Intent rather than silently redefining it.
62. Product Value remains derivable from Intent, evidence, expected outcomes and trade-offs without requiring a first-class Value object.
63. Acquisition, conversion, activation, adoption, engagement, retention, loyalty and similar dimensions MAY influence objectives when applicable but are not universal requirements.
64. Reducing user/customer friction, effort, cognitive load or cost MAY constitute Product value when supported by Intent and evidence.
65. Customer/user outcomes MAY be treated as Product evidence without requiring a customer-success subsystem in URACE core.
66. URACE can reason about trade-offs between multiple Product-value dimensions rather than blindly maximizing one metric.
67. External Product/customer outcomes are not represented as validated merely because an executor predicts them.
68. Customer-value capabilities and evidence sources remain replaceable and externalizable.
69. URACE can identify a material limitation in its own lifecycle machinery without requiring the Product/user to explicitly nominate URACE as the target.
70. URACE self-evolution follows ordinary lifecycle governance rather than privileged self-modification semantics.
71. URACE does not self-modify merely because self-improvement is possible.
72. Autonomous evolution supports an unbounded sequence of justified cycles rather than implying exactly one subsequent cycle.
73. Persistent autonomous operation preserves lifecycle liveness across `IDLE`, waiting and runtime dormancy.
74. Persistence alone is not treated as proof of wakeability.
75. A standalone `--autonomous` runtime does not terminate merely because no objective is immediately executable when no other wake/resume path exists.
76. A runtime MAY safely terminate during autonomous dormancy when an equivalent durable wake/resume mechanism has assumed responsibility.
77. Liveness does not require a particular event loop, daemon, scheduler, watcher, queue, alarm, cloud primitive or orchestrator.
78. Dormant autonomous operation avoids unnecessary AI/executor activity and wasteful busy-waiting.
79. Meaningful Triggers can reactivate `IDLE` or waiting Products without loss of durable lifecycle state.
80. Runtime implementation details may change while durability, liveness and wakeability semantics remain correct.
81. Meaningful Trigger has a defined lifecycle meaning independent from any particular trigger source or delivery mechanism.
82. Trigger detection and trigger interpretation remain separate responsibilities.
83. A Meaningful Trigger causes reassessment rather than automatic Product mutation.
84. Raw events that are irrelevant, stale or duplicate do not unnecessarily produce expensive lifecycle activity.
85. Unknown future trigger sources can still reactivate the lifecycle when their observations are materially relevant.
86. Trigger semantics remain stable when watcher, scheduler, webhook, queue, alarm, polling, periodic discovery or platform-native wake mechanisms are replaced.
87. Meaningful Trigger remains distinct from Evidence, Objective and Product mutation.
88. Known dormant-state trigger conditions can be persisted or reconstructed without requiring an exhaustive trigger registry.
89. Trigger delivery need not provide exactly-once semantics for lifecycle correctness.
90. Trigger storms can be bounded without losing materially distinct lifecycle changes.
91. Time passage alone does not become Product work merely because autonomous operation is enabled.
92. Trigger processing can fail and recover without silently corrupting authoritative Product state or declaring completion.
93. Meaningful Trigger scope includes potentially material change at any relevant Product/project/lifecycle scope or abstraction level.
94. Product Intent, goals, requirements, objectives, artifacts, dependencies, environment, policy, constraints, capacity and URACE itself are examples rather than a closed trigger taxonomy.
95. URACE can discover meaningful changes that were not represented by a predefined event source.
96. Bounded periodic discovery complements event-driven triggering when direct trigger coverage is incomplete.
97. Periodic executor-assisted discovery does not itself constitute Product work or a Meaningful Trigger.
98. A periodic discovery attempt that finds no material change returns the lifecycle to dormancy without manufacturing work.
99. Periodic executor-assisted discovery respects budget, cost, capacity, risk, backoff and policy.
100. Deterministic change discovery is preferred over unnecessary executor use where sufficient.
101. Executor availability is treated as capacity state rather than Product completion.
102. Executor unavailability cannot by itself terminate persistent autonomous lifecycle ownership.
103. All intelligent executors may be temporarily unavailable while URACE remains in a valid live lifecycle state.
104. Executor restoration may constitute a Meaningful Trigger when it materially changes available action.
105. Executor availability retries can use bounded backoff without converting temporary unavailability into permanent lifecycle abandonment.
106. Persistent autonomous execution does not end merely because an executor-assisted trigger/discovery attempt cannot currently run.
107. The event-loop/runtime may terminate only when equivalent durable reactivation responsibility exists or the autonomous invocation is explicitly stopped/bounded.
108. Unknown project-scope changes can be discovered through later reconciliation without requiring prior enumeration.
109. Trigger meaning depends on potential lifecycle impact rather than the abstraction level at which a change occurs.
110. Open-ended trigger scope does not require a heavyweight universal event ontology.

---

# 52. Defensible Boundary

Do not allow URACE's purpose to drift downward into executor implementation or sideways into domain-specific Product optimization.

The stack boundary is:

```text
┌───────────────────────────────────────┐
│ PRODUCT / USER / CUSTOMER / MARKET / │
│ ENVIRONMENT                           │
└───────────────────┬───────────────────┘
                    │
       observations / evidence
                    │
                    ▼
┌───────────────────────────────────────┐
│                 URACE                 │
│                                       │
│ Persistent Autonomous Product        │
│ Lifecycle Control Plane               │
│                                       │
│ Intent                                │
│ state                                 │
│ evidence + lineage                    │
│ requirements                          │
│ objectives                            │
│ policy                                │
│ constraints                           │
│ budgets / schedules                   │
│ validation                            │
│ readiness                             │
│ lifecycle liveness                    │
│ Meaningful Trigger semantics          │
│ change-discovery semantics            │
│ history                               │
│ recovery                              │
│ checkpoints                           │
└───────────────────┬───────────────────┘
                    │
           generic capabilities
                    │
                    ▼
┌───────────────────────────────────────┐
│        EXECUTION / INTELLIGENCE       │
│                                       │
│ one AI                                │
│ many AIs                              │
│ OpenHands                             │
│ another orchestrator                  │
│ deterministic tools                   │
│ APIs                                  │
│ humans                                │
│ future systems                        │
└───────────────────────────────────────┘
```

URACE's defensible responsibility is not producing superior intelligence.

It is maintaining continuous, Intent-directed, evidence-aware, policy-governed, validated, recoverable and autonomously resumable Product evolution independently of whichever intelligence systems happen to exist underneath it.

Its responsibility includes preserving the causal chain:

```text
INTENT
   │
   ▼
EVIDENCE
   │
   ▼
JUSTIFIED GAP
   │
   ▼
REQUIREMENT / OBJECTIVE
   │
   ▼
EXECUTION
   │
   ▼
OBSERVATION
   │
   ▼
VALIDATION
   │
   ▼
VALIDATED PRODUCT CHANGE
   │
   ▼
NEW EVIDENCE
```

and, during dormancy:

```text
DORMANT LIFECYCLE
        │
        ▼
EVENT / CONDITION /
PERIODIC DISCOVERY
        │
        ▼
RAW OBSERVATION
        │
        ▼
RELEVANCE INTERPRETATION
        │
        ▼
MEANINGFUL TRIGGER
        │
        ▼
REASSESSMENT
```

For Products serving users/customers, this MAY include continuously identifying and pursuing justified opportunities to create, deliver, increase or preserve Product/customer value.

URACE determines when Product evolution should continue and when the Product has sufficiently converged for active evolution to become `IDLE`.

`IDLE` changes activity state.

It does not silently surrender autonomous lifecycle ownership.

`WAITING_FOR_CAPACITY` changes execution availability.

It does not silently surrender autonomous lifecycle ownership.

When a material limitation in URACE itself obstructs this lifecycle, that limitation MAY enter the same causal chain as an ordinary justified Product gap.

This does not create a separate self-improvement architecture.

It preserves one lifecycle.

URACE does NOT own the specialized implementation of:

```text
market analysis
customer research
acquisition optimization
growth analytics
CRM
retention systems
pricing intelligence
behavioral analysis
solution formulation
coding
research
other domain-specific intelligence
```

Those capabilities MAY provide evidence or execution through the generic boundary.

Likewise, URACE owns autonomous liveness, open-ended change awareness and Meaningful Trigger semantics but not a particular trigger-detection, discovery, event-delivery or runtime-liveness implementation.

---

# 53. Bootstrap Restraint

Before implementing any subsystem, ask:

> Must this capability remain authoritative and portable across executor replacement in order to preserve the autonomous Product lifecycle?

If YES:

It may belong in URACE.

If NO:

Delegate it or preserve it as a variant.

Examples that normally belong outside URACE:

```text
code understanding
AST parsing
embeddings
web browsing
market-search implementation
customer-research implementation
growth analytics
CRM implementation
retention analytics
pricing analysis
behavioral analytics
LLM reasoning
coding
debugging intelligence
model inference
agent conversation management
sandbox implementation
IDE integration
language-specific intelligence
trigger transport infrastructure
generic event-bus infrastructure
platform-specific watcher implementation
```

URACE MAY consume their results without owning their implementations.

Before declaring something a Core Invariant, ask:

> Would URACE cease to preserve its defining lifecycle semantics if this changed?

If NO:

It SHOULD remain policy, configuration or a variant.

Before promoting something to a first-class lifecycle primitive, ask:

> Does lifecycle correctness require this concept to retain independent durable identity or semantics across objectives, executors and cycles?

If YES:

First-class treatment MAY be justified.

If NO:

Prefer deriving it from existing primitives.

This is why:

```text
Intent
    → first-class

Evidence
    → first-class

Product Value
    → derived

conversion / retention / cognitive load / customer cost / etc.
    → contextual dimensions

Lifecycle Liveness
    → invariant property

Meaningful Trigger
    → defined lifecycle semantic

Open-Ended Change Awareness
    → invariant semantic

Periodic Discovery
    → variant mechanism

Executor Availability
    → capacity condition

trigger source / watcher / scheduler /
webhook / queue / alarm / polling
    → implementation variants
```

Before expanding evidence infrastructure, ask:

> Does lifecycle correctness require this evidence mechanism, or only sufficient provenance and lineage?

If sufficient lineage can be preserved more simply, prefer the simpler mechanism.

Before expanding liveness infrastructure, ask:

> Does lifecycle correctness require this particular runtime mechanism, or only a viable durable path back to assessment?

If the latter can be preserved more simply, prefer the simpler mechanism.

Before building trigger infrastructure, ask:

> Does lifecycle correctness require this particular event mechanism, or only reliable enough observation or discovery of lifecycle-relevant change followed by Meaningful Trigger interpretation?

If the latter can be satisfied by the existing environment, prefer it.

Before restricting trigger scope, ask:

> Could a material change at another Product/project/lifecycle scope or abstraction level alter the current assessment?

If YES or materially uncertain:

Do not exclude that scope merely because it was not predefined.

Before treating a raw event as a Meaningful Trigger, ask:

> Could this event, discovered change or condition materially change the most recent lifecycle assessment relative to Product Intent, evidence, policy, constraints, capacity, readiness, risk or expected Product value?

If NO:

Ignore, coalesce or retain only as necessary.

If YES or materially uncertain:

Reassess.

Before invoking an executor for periodic discovery, ask:

> Is executor reasoning likely to reveal material change that cheaper deterministic observation cannot adequately detect, and is the expected discovery value proportionate to cost, budget, capacity and risk?

If NO:

Prefer deterministic observation or wait.

If YES:

Use bounded executor-assisted discovery.

Before reacting to executor unavailability, ask:

> Is this Product completion, or merely current execution-capacity loss?

Unless Product readiness independently establishes completion:

Treat it as capacity loss.

Before allowing an autonomous runtime to terminate, ask:

> If a Meaningful Trigger occurs after this runtime terminates, what concrete durable mechanism will cause URACE to observe or discover it and reassess?

If the answer is "none":

Do not terminate persistent autonomous operation merely because the event loop would otherwise become empty or because an executor is currently unavailable.

Before turning a constraint into an enforcement mechanism, ask:

> Is this an actual invariant or HARD boundary, or a preference that should guide autonomous selection?

Before imposing physical structure, ask:

> Does lifecycle correctness require this structure, or can the existing Product structure be discovered and used?

Before generating a requirement, ask:

> What Product Intent, evidence, material risk, constraint or sufficiently supported opportunity justifies this requirement?

Before creating a Product-value objective, ask:

> Which Product Intent and sufficiently supported evidence make this outcome valuable, and what material Product/user/customer result is expected to improve?

Do not assume:

```text
more conversion
more engagement
more retention
lower customer cost
less friction
less cognitive load
```

is automatically better.

Determine whether the dimension is applicable, whether the causal hypothesis is supported strongly enough to act upon, what trade-offs may result, and how the outcome can eventually be validated.

Before beginning another autonomous objective, ask:

> Does this action have sufficient expected Product value relative to Intent, cost, risk, uncertainty and opportunity cost?

Before modifying URACE itself, ask:

> Is a demonstrated limitation in URACE materially constraining the governed Product lifecycle, and is changing URACE the highest-value justified response?

If NO:

Do not self-modify merely because improvement is possible.

Before entering `IDLE`, ask:

> Has the Product reached the highest justified readiness state currently supported by its Intent, evidence and constraints, or is an empty objective list hiding meaningful unfinished work?

For a market-intended Product, this MAY additionally ask:

> Is the Product sufficiently market-ready for its current stage, or merely technically complete?

If meaningful justified work remains but required executor capacity does not:

Wait for capacity while preserving liveness.

Do not convert unavailable execution capacity into completion.

If meaningful justified work remains:

Continue.

If required progress depends on unavailable external evidence, capacity or time:

Wait while preserving a viable path to detecting, discovering or receiving the relevant condition.

If the Product is sufficiently ready under its applicable readiness criteria and further autonomous work would primarily be speculative, cosmetic, redundant or unsupported by evidence:

Enter `IDLE` while preserving autonomous liveness.

Do not manufacture a requirement or objective solely to prevent autonomous execution from becoming dormant.

Do not manufacture Meaningful Triggers merely to force reassessment.

Do not perform useless work merely to keep a runtime alive.

---

# 54. Final Bootstrap Instruction

Bootstrap the smallest implementation capable of proving the Core Invariants above.

Do not optimize for feature count.

Do not reproduce capabilities available through external executors.

Do not promote implementation variants into Core Invariants without necessity.

Do not promote useful Product metrics into first-class lifecycle primitives merely because they are measurable.

Do not turn first-class Intent into a heavyweight Intent-management subsystem.

Do not turn first-class Evidence into a heavyweight evidence platform unless Product requirements independently justify one.

Do not create a first-class Value subsystem unless a concrete lifecycle requirement eventually demonstrates that Value must possess independent durable identity beyond Intent, Evidence, Requirements and Objectives.

Do not turn Lifecycle Liveness into a heavyweight runtime framework.

Do not turn Meaningful Trigger into a heavyweight event-processing framework.

Do not turn periodic discovery into a heavyweight monitoring framework.

Do not create a privileged self-improvement subsystem.

Do not make OpenHands mandatory.

Do not make multiple AIs mandatory.

Do not make executor availability a prerequisite for lifecycle existence.

Do not make Git mandatory.

Do not make source code mandatory.

Do not make a programming language or Product type mandatory.

Do not make known file formats mandatory.

Do not make a specific operating environment mandatory at the architectural level.

Do not make a specific repository, directory or workspace structure mandatory.

Do not make a specific scheduler mandatory.

Do not make a permanent event loop mandatory.

Do not make a daemon mandatory.

Do not make a particular watcher, queue, alarm, webhook, event bus, polling strategy, periodic discovery mechanism or cloud wake mechanism mandatory.

Do not make a specific trigger taxonomy mandatory.

Do not restrict Meaningful Trigger consideration to predefined Product/project scope levels.

Do not require every future Meaningful Trigger to be predictable in advance.

Do not make a specific budget representation mandatory.

Do not make a customer lifecycle, sales funnel, growth model, business model or Product-value metric mandatory.

Do not make market-fit-quality readiness mandatory for Products whose Intent does not imply a market.

The minimum intelligent deployment MUST remain:

```text
            URACE
              │
       generic Executor
              │
              ▼
            ONE AI
```

The richer deployment MAY be:

```text
            URACE
              │
       generic Executor
              │
              ▼
         ORCHESTRATOR
              │
       ┌──────┼──────┐
       ▼      ▼      ▼
      AI     AI     tools
```

Both MUST exercise the same URACE lifecycle.

Both MUST preserve equivalent autonomous liveness, open-ended change awareness and Meaningful Trigger semantics.

The canonical autonomous Product-evolution pattern is:

```text
INTENT
   │
   ▼
EVIDENCE
   │
   ▼
ASSESS
   │
   ▼
JUSTIFIED GAP
   │
   ▼
REQUIREMENT / OBJECTIVE
   │
   ▼
IMPLEMENT
   │
   ▼
OBSERVE
   │
   ▼
VALIDATE
   │
   ▼
CHECKPOINT
   │
   ▼
NEW / UPDATED EVIDENCE
   │
   └────────────► REPEAT WHILE JUSTIFIED
```

Intent and Evidence are first-class lifecycle primitives.

Intent establishes durable direction.

Evidence establishes what is sufficiently known to act.

Product Value is evaluated relative to them.

Specific value dimensions remain contextual.

Lifecycle Liveness ensures that autonomous lifecycle ownership remains capable of reassessment even when active execution becomes dormant or executors become unavailable.

Meaningful Trigger defines when a dormant lifecycle has sufficient reason to reassess.

Meaningful Trigger scope is open-ended across the entire governed Product/project/lifecycle.

The canonical dormant lifecycle pattern is:

```text
IDLE / WAIT / BLOCKED
        │
        ▼
PRESERVE LIVENESS
        │
   ┌────┼──────────────┐
   ▼    ▼              ▼
EVENT  KNOWN        PERIODIC
       CONDITION    DISCOVERY
   │    │              │
   └────┼──────────────┘
        ▼
RAW EVENT / CONDITION /
DISCOVERED CHANGE
        │
        ▼
NORMALIZE / RECONCILE
        │
        ▼
COULD IT MATERIALLY CHANGE
THE PRIOR ASSESSMENT?
        │
   ┌────┴─────┐
   ▼          ▼
  NO          YES
   │           │
   ▼           ▼
IGNORE /    MEANINGFUL
COALESCE      TRIGGER
   │           │
   ▼           ▼
DORMANT      ASSESS
               │
          ┌────┴────┐
          ▼         ▼
       ACTION     NO ACTION
          │         │
          ▼         ▼
       ACTIVE     DORMANT
```

A Meaningful Trigger therefore means:

> A sufficiently credible observation, event, condition, state transition, scheduled condition, authoritative input, relevant evidence change or potentially material change discovered anywhere within or affecting the governed Product/project/lifecycle scope that could materially change the result of the most recent lifecycle assessment relative to Product Intent, policy, constraints, capacity, readiness, risk or expected Product value.

This definition is intentionally semantic, scope-open and mechanism-agnostic.

The trigger does not need to prove that Product work exists.

It only needs to justify reassessment.

The trigger source does not decide the Product response.

URACE does.

A change MAY occur at any Product/project scope or abstraction level.

Intent, goals, requirements, objectives, artifacts, dependencies, evidence, assumptions, validation, readiness, environment, policy, constraints, budgets, schedules, executor capacity, external conditions and URACE itself are examples.

They are not a closed taxonomy.

Because future material changes cannot always be predicted or directly subscribed to, URACE SHOULD combine, where appropriate:

```text
EVENT-DRIVEN OBSERVATION
        +
KNOWN SCHEDULED CONDITIONS
        +
BOUNDED PERIODIC DISCOVERY
```

Periodic discovery MAY use executors.

It MUST NOT require them when deterministic inspection is sufficient.

Periodic executor invocation is not itself a Meaningful Trigger.

What it discovers MAY be.

Executor availability is likewise not equivalent to Product value or Product completion.

Its semantics are:

```text
EXECUTOR AVAILABLE
        │
        ▼
CAPABILITY MAY BE USABLE

EXECUTOR UNAVAILABLE
        │
        ▼
CAPABILITY CURRENTLY UNAVAILABLE
        │
        ▼
WAIT / RETRY / DISCOVER ALTERNATIVE
        │
        ▼
AUTONOMOUS LIFECYCLE REMAINS
```

Therefore:

```text
EXECUTOR UNAVAILABLE
        ≠
END LOOP
```

and:

```text
ALL EXECUTORS UNAVAILABLE
        ≠
PRODUCT COMPLETE
```

and:

```text
EXECUTOR RESTORED
        =
potential Meaningful Trigger
when it materially changes available action
```

The evidence source, evidence storage mechanism, readiness criteria, Product-value dimensions, implementation strategy, executor topology, scheduler, runtime model, trigger source, trigger-delivery mechanism, periodic discovery mechanism and wake mechanism are variants.

Evidence being first-class is invariant.

A particular evidence subsystem is not.

Intent being first-class is invariant.

A particular Intent representation or subsystem is not.

Lifecycle Liveness is invariant.

A particular event loop, daemon, scheduler, watcher, queue, alarm, webhook, cloud primitive or wake implementation is not.

Meaningful Reactivation is invariant.

A particular trigger source, event taxonomy, transport, delivery guarantee, debounce implementation or event-processing framework is not.

Open-ended change awareness is invariant.

A particular discovery mechanism or periodic frequency is not.

Conversion, retention, loyalty, engagement, cognitive load, customer effort, customer cost and similar dimensions being available for consideration does not make them URACE invariants.

The lifecycle relationship is invariant.

For a Product serving users or customers, justified Product evolution MAY include improving any evidence-supported dimension of Product/customer value, including but not limited to:

```text
acquisition
conversion
activation
adoption
engagement
retention
loyalty

satisfaction
trust
usability
accessibility
clarity

reduced friction
reduced cognitive load
reduced customer effort
reduced customer cost

increased customer productivity
realized customer value
successful customer outcomes
```

No item in this list is universally required.

No fixed ordering is implied.

No isolated metric is equivalent to Product value.

The governing Product-value relationship is:

```text
PRODUCT INTENT
      +
AVAILABLE EVIDENCE
      +
EXPECTED OUTCOME
      +
CONSTRAINTS
      +
COST / RISK / TRADE-OFFS
      │
      ▼
EXPECTED PRODUCT VALUE
      │
      ▼
HIGHEST-VALUE JUSTIFIED OBJECTIVE
```

A Product may therefore need to acquire customers, convert prospects, reduce decision friction, improve activation, increase successful adoption, retain customers, reduce cognitive burden, reduce total customer cost, improve trust, increase productivity, improve outcomes, or pursue an entirely different dimension.

URACE does not prescribe which.

It discovers what is justified relative to Product Intent.

For a market-intended Product, one specialization MAY be:

```text
INTENT
   │
   ▼
MARKET + USER + CUSTOMER + PRODUCT EVIDENCE
               │
               ▼
             ASSESS
               │
               ▼
          MATERIAL GAP
               │
               ▼
          REQUIREMENT
               │
               ▼
           IMPLEMENT
               │
               ▼
            VALIDATE
               │
               ▼
          REASSESS MARKET
        / PRODUCT CONDITION
               │
        ┌──────┴──────┐
        ▼             ▼
  JUSTIFIED GAP     READY
        │             │
        ▼             ▼
      REPEAT         IDLE
                       │
                       ▼
                PRESERVE LIVENESS
                       │
            ┌──────────┼──────────┐
            ▼          ▼          ▼
          EVENT       TIME     PERIODIC
                               DISCOVERY
            │          │          │
            └──────────┼──────────┘
                       ▼
                MEANINGFUL TRIGGER
```

For another Product, the evidence, value dimensions, readiness criteria and trigger sources MAY differ while the lifecycle remains unchanged.

The loop MUST NOT be interpreted as an obligation to continuously generate requirements.

Requirements exist to close justified Product gaps.

When no sufficiently valuable justified gap remains and applicable readiness requirements are satisfied, the correct active lifecycle result is `IDLE`.

When a Meaningful Trigger later occurs:

```text
IDLE
 │
 ▼
MEANINGFUL TRIGGER
 │
 ▼
RECONCILE
 │
 ▼
ASSESS AGAINST INTENT
 │
 ├──────────────► NO MATERIAL CHANGE → IDLE
 │
 ▼
JUSTIFIED GAP
 │
 ▼
NEW JUSTIFIED REQUIREMENT
```

The lifecycle resumes only as far as the new assessment justifies.

When the evidence instead reveals that URACE itself is materially constraining the lifecycle:

```text
PRODUCT LIFECYCLE
      │
      ▼
URACE LIMITATION
      │
      ▼
MATERIAL JUSTIFIED GAP
      │
      ▼
URACE-LEVEL OBJECTIVE
      │
      ▼
BOUNDED CHANGE
      │
      ▼
VALIDATE
      │
      ▼
CHECKPOINT
      │
      ▼
RESUME PRODUCT LIFECYCLE
```

The Product does not need to explicitly instruct URACE to target itself.

But the same justification threshold applies.

URACE MUST NOT self-modify merely because it is capable of doing so.

`--autonomous` therefore continues autonomous Product lifecycle ownership until explicitly stopped or otherwise terminated by its invocation/policy contract.

Active Product evolution MAY become:

```text
ACTIVE
WAITING
BLOCKED
PAUSED
IDLE
```

without requiring unnecessary active execution.

When autonomous operation remains enabled, dormant states MUST preserve a viable path to future assessment.

Conceptually:

```text
ACTIVE CYCLE
     │
     ▼
CHECKPOINT
     │
     ▼
ASSESS
     │
     ├────► NEXT JUSTIFIED CYCLE
     │              │
     │              └────► repeat while justified
     │
     ├────► WAIT / BLOCK / PAUSE
     │              │
     │              ▼
     │       preserve wake/resume path
     │              │
     │       event / discovery / retry
     │              │
     │              ▼
     │       Meaningful Trigger
     │
     └────► IDLE
                    │
                    ▼
             preserve liveness
                    │
          event / periodic discovery
                    │
                    ▼
             Meaningful Trigger
                    │
                    ▼
                  ASSESS
```

There is no predetermined number of autonomous cycles.

`IDLE` MUST NOT be premature.

An empty task list, completed objective, lack of executor suggestions or current executor unavailability is not sufficient evidence of completion.

Technical completion alone is not sufficient when Product Intent implies additional material readiness requirements.

`IDLE` MUST NOT be endlessly postponed.

Perfection is not the completion criterion.

The existence of another conceivable improvement or another optimizable metric is not sufficient reason to continue.

This applies equally to the governed Product and to URACE itself.

`IDLE` MUST NOT become dead autonomy.

`WAITING_FOR_CAPACITY` MUST NOT become dead autonomy.

Persisted state without a viable reassessment path does not satisfy persistent autonomous lifecycle ownership.

The governing convergence, trigger, executor-capacity and liveness rule is:

```text
CONTINUE
    when
expected Product value of justified action
relative to Intent
meaningfully exceeds its cost / risk / opportunity cost
AND
required capability is available

WAIT FOR CAPACITY
    when
justified action exists
but required executor/capability
is currently unavailable
while preserving autonomous liveness

WAIT FOR CONDITION
    when
required progress depends on a future or external condition
while preserving a viable path to observe or discover its change

BLOCK
    when
a HARD constraint prevents required progress
while preserving reassessment when the condition can change

IDLE
    when
applicable readiness requirements are satisfied
AND
no material unresolved Intent-relative gap remains
AND
no currently available action has sufficient justified value
while preserving autonomous liveness

REASSESS
    when
a Meaningful Trigger could materially change
the prior lifecycle assessment

PERIODICALLY DISCOVER
    when
autonomous operation remains enabled
AND
event-driven/known trigger coverage may not be sufficient
AND
the expected value of discovery justifies its resource cost

TERMINATE CURRENT RUNTIME
    only when
autonomous operation has been explicitly stopped/bounded
OR
policy requires termination
OR
an equivalent durable mechanism has assumed responsibility
for future trigger observation/discovery and wake/resume
```

Readiness remains Intent-relative:

```text
PRODUCT INTENT
      │
      ▼
APPLICABLE READINESS
      │
      ▼
VALIDATED PRODUCT STATE
      │
 ┌────┴──────────────┐
 ▼                   ▼
MATERIAL GAP       READY
 │                   │
 ▼                   ▼
CONTINUE            IDLE
 │                     │
 │                     ▼
 │              PRESERVE LIVENESS
 │                     │
 │          event / periodic discovery
 │                     │
 │                     ▼
 │              MEANINGFUL TRIGGER
 │
 └── if executor unavailable:
        WAIT FOR CAPACITY
        without ending lifecycle
```

For a market-intended Product, this MAY specialize to:

```text
TECHNICAL COMPLETION
        │
        ▼
PRODUCT READINESS
        │
        ▼
MARKET-FIT-QUALITY READINESS
        │
        ▼
IDLE / MARKET EVIDENCE WAIT
        │
        ▼
PRESERVE WAKE / DISCOVERY PATH
        │
        ▼
MEANINGFUL TRIGGER
```

Actual market validation remains external-evidence dependent:

```text
MARKET-FIT-QUALITY PRODUCT
            +
REAL USER / CUSTOMER / MARKET EVIDENCE
            │
            ▼
VALIDATED MARKET LEARNING
```

URACE MUST pursue applicable evidence when doing so is justified and possible.

URACE MUST wait when required evidence inherently depends on time, external actors or currently unavailable executor capacity.

URACE MUST remain capable of resuming when a Meaningful Trigger indicates that the lifecycle may materially differ.

Individual requirements may complete.

Individual objectives may complete.

Individual cycles may complete.

Individual executors may terminate.

All executors may temporarily become unavailable.

Individual AI conversations may disappear.

Active runtimes may terminate when another durable mechanism preserves autonomous liveness.

Models may change.

Orchestrators may change.

Programming languages may change.

Platforms may change.

Project structures may change.

Artifact formats may change.

Evidence storage mechanisms may change.

Validation mechanisms may change.

Schedulers may change.

Wake mechanisms may change.

Trigger sources may change.

Trigger transports may change.

Periodic discovery mechanisms may change.

Runtime models may change.

Persistence mechanisms may change.

Customer journeys may change.

Market conditions may change.

Relevant Product-value dimensions may change.

Readiness criteria may change with Product Intent.

Product Intent itself may evolve through justified, authoritative change while remaining durably traceable.

URACE itself may evolve when its limitations become materially relevant to the Product lifecycle.

The Product may become `IDLE`.

Executors may become unavailable.

A Meaningful Trigger may reactivate assessment.

Periodic discovery may reveal a Meaningful Trigger no predefined event source knew how to expose.

**The autonomous Product lifecycle remains.**

The final first-class principle is:

> Intent and Evidence are first-class lifecycle primitives because autonomous lifecycle correctness depends on preserving both durable direction and justified knowledge across objectives, executors and cycles; Product Value remains derived unless independent lifecycle semantics eventually justify promoting it.

The final Intent principle is:

> Product Intent defines what meaningful Product progress, value and readiness mean; objectives, strategies, implementations and metrics may change without silently redefining that Intent.

The final evidence principle is:

> Evidence is a first-class lifecycle primitive whose provenance and causal lineage justify autonomous decisions, without requiring URACE to become an evidence-management platform.

The final Product-value principle is:

> URACE pursues the highest-value justified Product outcomes supported by Intent and evidence; customer-facing outcomes such as acquisition, conversion, retention, reduced cognitive load, reduced effort and reduced cost are possible dimensions of value, never universal objectives.

The final customer-value principle is:

> For Products that serve users or customers, URACE should pursue durable realized value rather than blindly maximize isolated proxy metrics, balancing acquisition, use, retention, effort, cost, trust and outcomes only where they are relevant and sufficiently justified by Product Intent and evidence.

The final trigger principle is:

> A Meaningful Trigger is any sufficiently credible change or condition at any relevant Product/project/lifecycle scope that could materially alter the most recent lifecycle assessment; it justifies reassessment, not automatic action, and its meaning belongs to URACE even when its detection, discovery and delivery are delegated to replaceable mechanisms.

The final trigger-scope principle is:

> Meaningful Trigger scope is open-ended: Intent, goals, requirements, objectives, artifacts, dependencies, evidence, assumptions, environment, constraints, policy, readiness, executor capacity, external conditions and URACE itself are examples rather than boundaries; potential lifecycle impact determines relevance, not abstraction level or prior enumeration.

The final trigger-agnosticism principle is:

> URACE defines what makes reactivation meaningful, while watchers, schedules, timers, queues, webhooks, events, callbacks, polling, periodic discovery, platform-native mechanisms and future systems merely provide replaceable ways to observe, discover or deliver candidate conditions.

The final discovery principle is:

> URACE must not rely solely on changes it already knows how to subscribe to; bounded periodic deterministic or executor-assisted discovery may search for otherwise unobserved material change, but the discovery attempt itself is not a Meaningful Trigger and must not manufacture Product work when nothing relevant has changed.

The final executor-availability principle is:

> Executor availability governs current execution capacity, not lifecycle existence: unavailable executors cause waiting, retry, replacement or bounded backoff while autonomous liveness remains preserved; executor unavailability alone MUST NOT terminate persistent autonomous operation, and restored capability becomes a Meaningful Trigger only when it can materially change the lifecycle assessment.

The final liveness principle is:

> Persistent autonomous lifecycle ownership requires both durable state and a viable path back to assessment when a Meaningful Trigger occurs; URACE may become dormant and may release its active runtime, but it MUST NOT silently become unreachable merely because no work is immediately executable or no executor is currently available.

The final runtime principle is:

> URACE owns liveness and reactivation semantics, not a particular runtime mechanism: a process, event loop, watcher, scheduler, alarm, queue, webhook, orchestrator, periodic discovery cycle or serverless wake source may all satisfy the same contract when they preserve equivalent durable reassessment capability.

The final self-evolution principle is:

> URACE may evolve its own lifecycle machinery when evidence shows that a limitation in URACE materially constrains the governed Product lifecycle; such evolution requires no special invitation, receives no special privilege, and remains subject to the same Intent, justification, validation, checkpointing and convergence rules as every other change.

The final design principle is:

> URACE owns the persistent autonomous Product lifecycle; replaceable executors provide the intelligence and execution required to advance it.

The final evolution principle is:

> Product Intent establishes direction; evidence reveals justified Product gaps; gaps produce requirements and objectives; executors implement them; observations and independent validation determine acceptance; resulting Product state creates new evidence; URACE repeats the cycle while further action remains justified, waits without terminating when required capacity is unavailable, and periodically searches for otherwise unobserved material change when appropriate.

And the final convergence principle is:

> URACE must evolve each Product toward the highest justified readiness state implied by that Product's Intent, evidence and constraints—not merely until work becomes inconvenient, not beyond the point where further autonomous work has insufficient justified value, and not into a dormant or capacity-starved state from which a Meaningful Trigger can no longer cause autonomous reassessment.
