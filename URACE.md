# URACE — Universal Recursive Autonomous Co-Founder Engine

You are the Lead Systems Architect and Bootstrap Executor for this repository.

Your task is to bootstrap **URACE**.

URACE is a **self-contained, executor-agnostic persistent autonomous product-evolution control plane**.

Its unique responsibility is to preserve and govern a continuous product-development lifecycle across otherwise bounded, replaceable and potentially stateless intelligence/execution systems.

URACE MUST NOT become another coding agent, LLM framework, agent runtime, IDE agent, RAG platform, workflow engine, model provider, sandbox, or replacement for external intelligence.

Its purpose is:

> **Continuously evolve a Product by preserving durable intent, state, evidence, decisions, policy, validation, recovery and history; translating justified Product, user, market and environmental evidence into requirements and objectives; delegating intelligence-intensive or execution-intensive operations to replaceable executors; independently evaluating their results; checkpointing accepted increments; and repeating while further autonomous action remains sufficiently justified.**

The primary architectural invariant is:

> **URACE owns the autonomous Product lifecycle. Replaceable executors supply whatever intelligence or execution is required to advance it.**

---

# 1. Unique Position in the Stack

URACE occupies a layer distinct from agents, orchestrators, models, development tools and infrastructure.

```text
              USERS / MARKET / ENVIRONMENT
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

URACE MUST remain useful when any executor shown above is replaced.

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
- checkpoint history;
- recovery state;
- interruption state;
- capacity state;
- completion/readiness state;
- acceptance/rejection of candidate increments.

External executors MAY provide:

- reasoning;
- research;
- market analysis;
- user analysis;
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
- repair reasoning.

URACE MUST remain authoritative over lifecycle state regardless of executor behavior.

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

### I3 — Evidence Traceability

Material autonomous decisions MUST remain attributable to Product intent, evidence, constraints, risk, observations, policy or sufficiently justified opportunity.

Evidence used to justify lifecycle decisions MUST preserve sufficient provenance and lineage to distinguish what was observed from what was inferred, assumed, hypothesized or decided.

### I4 — Justified Evolution

Requirements and objectives MUST exist because sufficiently valuable Product gaps justify them.

URACE MUST NOT manufacture work merely to sustain autonomous activity.

### I5 — Independent Acceptance

Executor output MUST NOT be accepted solely because the executor claims success.

Acceptance belongs to URACE policy and applicable validation.

### I6 — Durable Continuity

Accepted state and sufficient lifecycle context MUST survive executor replacement, interruption and process restart.

### I7 — Hard-Boundary Respect

Autonomous execution MUST NOT knowingly violate applicable HARD constraints.

### I8 — Convergence

URACE MUST neither:

```text
stop while material justified work remains
```

nor:

```text
continue merely because further activity is possible
```

The lifecycle MUST be capable of converging to `IDLE`.

### I9 — Agnosticism

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
- persistence technology.

### I10 — Intent-Relative Readiness

URACE MUST drive a Product toward the highest justified readiness state implied by its intent, evidence, constraints and environment.

No single universal definition of Product readiness is valid for every Product.

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
user-research technique
requirement-generation technique
validation mechanisms

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

budget representation
soft constraints
quality thresholds
readiness criteria
retry limits

market strategy
research methodology
implementation methodology
deployment strategy
```

A useful classification test is:

> **If changing a mechanism changes what URACE fundamentally is, it may belong to the invariant layer. If it can change while the evidence → justified gap → requirement/objective → execution → validation → checkpoint lifecycle remains correct, it SHOULD remain a variant.**

The governing relationship is:

```text
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
- budget representation;
- file format;
- file extension;
- artifact format;
- testing framework;
- IDE;
- editor.

The architecture MUST support:

> **universal file-base, project-type, platform, structure and programming-language agnosticism.**

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

rather than language-specific, framework-specific or filesystem-specific concepts.

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

Product readiness MUST be derived from Product intent rather than from one universal definition.

Examples:

```text
commercial Product
    → market/user/product readiness

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

---

# 8. Capabilities Instead of Brands

URACE MUST request capabilities, not named products.

Examples:

```text
reason
research
analyze-market
analyze-users
derive-requirements
plan
modify
execute
inspect
test
repair
review
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

---

# 10. Operating Modes

URACE MUST support at minimum:

## `--plan`

Assess and propose work without mutating the Product.

## `--check`

Inspect current lifecycle, validation, evidence, capacity, constraints, budgets, schedules, objectives, checkpoints, completion readiness and recovery state.

## `--autonomous`

Run persistent autonomous Product evolution.

The architecture MAY later expose additional modes without changing core semantics.

---

# 11. Autonomous Lifecycle

`--autonomous` is the defining behavior.

```text
LOAD PRODUCT STATE
        │
        ▼
LOAD AVAILABLE EVIDENCE
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
EXECUTOR(S)                  │
   │                         │
   ▼                         │
REASON / RESEARCH / PLAN     │
   │                         │
   ▼                         │
IMPLEMENT ◄──────────────────┘
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

The URACE lifecycle persists independently from individual executor lifetimes.

A fresh cycle MUST NOT imply that another mutation is necessarily required.

There is no fixed number of cycles.

URACE MAY execute as many successive cycles as remain justified.

A cycle MAY legitimately converge to `WAITING`, `BLOCKED`, `PAUSED` or `IDLE`.

---

# 12. Continuous Means Lifecycle Continuity

Continuous autonomy MUST NOT require:

- one permanent process;
- one permanent AI conversation;
- one permanent agent;
- one permanent model;
- one permanent machine;
- one permanent orchestrator;
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
```

Executor sessions SHOULD be considered replaceable.

Durable continuity belongs to URACE.

Continuous lifecycle ownership does not require continuous activity.

---

# 13. Objective Discovery

URACE MUST NOT merely consume an endless predetermined task list.

Its default autonomous Product-evolution pattern is:

```text
PRODUCT / USER / MARKET / ENVIRONMENT EVIDENCE
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

For Products with a market/user dimension, assessment SHOULD incorporate available market and user evidence.

For Products without a meaningful market dimension, Product, technical, operational, research or environmental evidence MAY drive the same lifecycle.

URACE therefore repeatedly asks:

> **Given Product intent, current state, available evidence, previous decisions, unresolved risks, constraints, budgets, schedules and available capabilities, what is the highest-value justified gap, requirement or objective to address next?**

A requirement MUST be justified by Product intent, evidence, risk, constraint or sufficiently supported opportunity.

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
- documentation improvement;
- architecture improvement;
- cost reduction;
- evidence collection;
- user/market validation where applicable;
- readiness validation;
- no currently justified mutation;
- completion/readiness assessment.

These are examples only.

A discovered possible improvement is not automatically a justified requirement or objective.

Expected Product value MUST justify its cost, risk and opportunity cost.

---

# 14. Product Value vs Activity

Continuous autonomy does NOT mean continuous mutation.

URACE MUST optimize for justified progress, not executor utilization.

An accepted cycle MUST materially:

- advance Product intent;
- reduce meaningful uncertainty;
- acquire useful evidence;
- reduce meaningful risk;
- improve validated quality;
- resolve a blocker;
- improve applicable Product readiness;
- or otherwise produce justified Product progress.

Do NOT create work merely because AI credits or compute capacity remain available.

Do NOT continue polishing merely because some theoretically possible improvement exists.

Conversely, absence of an immediately obvious task MUST NOT by itself justify `IDLE`.

Before `IDLE`, URACE MUST perform an explicit completion/readiness assessment.

---

# 15. Evidence

Evidence is a **first-class lifecycle primitive**.

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
- previous lifecycle observations.

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
```

Material lifecycle decisions SHOULD preserve sufficient lineage to determine what justified them.

This includes, where applicable:

```text
evidence
intent
constraints
observations
risk
policy
assumptions
```

The expected relationship is:

```text
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

# 16. Market Awareness

Market awareness is conditional on Product intent.

For Products with a market/user dimension, URACE SHOULD allow relevant external evidence to influence autonomous requirements and objectives.

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

If no market evidence is available, autonomous reasoning MAY formulate hypotheses and requirements for testing them, but MUST NOT represent them as validated demand.

This distinction MUST survive across cycles.

For a Product with market intent, the preferred evidence-driven lifecycle is:

```text
MARKET / USER / PRODUCT EVIDENCE
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

Market analysis is therefore an input to Product evolution rather than a separate mandatory subsystem.

URACE MAY delegate market analysis, research, requirement formulation and implementation to capable executors.

URACE remains authoritative over:

```text
evidence provenance and lineage
requirement/objective justification
policy
acceptance
validation
checkpointing
lifecycle continuation
readiness
```

For a Product with market intent, an applicable readiness target MAY be **market-fit-quality Product readiness**.

This means evolving the Product, within available evidence and applicable constraints, toward sufficient completeness, coherence, reliability, usability, security, maintainability, operability and differentiation for its intended market and user context.

However:

```text
MARKET-FIT-QUALITY READINESS
             ≠
PROVEN PRODUCT-MARKET FIT
```

Actual Product-market fit, validated demand, retention, willingness to pay or equivalent market outcomes MUST require appropriate external evidence.

URACE MUST NOT fabricate market validation from executor confidence.

When external market evidence is obtainable within policy, budget and capability constraints, acquiring or testing that evidence MAY itself become a justified objective.

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
    lastCycle
}
```

Exact serialization is an implementation detail.

Evidence lineage MAY be represented directly or through durable references.

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
```

`IDLE` is a successful autonomous lifecycle state, not a failure.

It means no currently justified Product action remains **after applicable completion/readiness requirements have been evaluated**.

`IDLE` MUST be neither premature nor artificially delayed.

URACE MUST NOT enter `IDLE` merely because:

- one objective completed;
- the current backlog is empty;
- one executor has no further suggestion;
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
- another equivalent analysis could be performed;
- perfection is theoretically unattainable.

---

# 18A. Completion and IDLE Gate

Before entering `IDLE`, URACE MUST explicitly determine whether the Product has reached the highest justified readiness state currently available under Product intent, evidence, constraints, capability, schedule and budget.

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
user readiness
reliability
security
safety
operability
maintainability
performance
research validity
ecosystem compatibility
market readiness
other Product-specific criteria
```

The exact dimensions MUST remain Product-specific.

Not every Product requires every dimension.

For a Product with market intent, applicable readiness MAY include **market-fit-quality readiness**, not merely technical functionality.

For another Product, the applicable readiness target MAY be entirely different.

Where final validation depends on external users, systems, time or events:

```text
PRODUCT READY FOR CURRENT STAGE
              │
              ▼
external evidence required
              │
       ┌──────┴──────┐
       ▼             ▼
actionable now   must wait
       │             │
       ▼             ▼
     ACTIVE      WAIT / IDLE
```

URACE MUST NOT endlessly modify a ready Product while the missing information can only come from an external condition.

The completion decision therefore balances two errors:

```text
PREMATURE IDLE
    =
meaningful justified Product work still exists

ENDLESS LOOP
    =
remaining work has insufficient expected Product value
relative to cost, risk or evidence need
```

URACE MUST avoid both.

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
- user/market evidence where applicable.

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

Passing implementation validation MUST NOT automatically imply overall Product readiness.

Validation results MAY themselves become evidence for subsequent lifecycle assessment.

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

Core state and lifecycle semantics MUST remain portable.

---

# 24. Project-Type Agnosticism

URACE MUST NOT assume the Product is a web application or even software.

Its lifecycle must remain meaningful for any Product that can expose:

```text
state
intent
artifacts
operations
observations
validation
```

This is the minimum conceptual Product contract.

Product readiness criteria MUST be derived from Product intent and evidence rather than hard-coded Product categories.

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
    artifactReferences
    evidenceReferences
    decisions
    validation
    executorMetadata
    unresolvedRisks
    timestamp
}
```

Checkpoint evidence references SHOULD preserve sufficient lineage to reconstruct why the accepted increment occurred.

Checkpoints MUST NOT require Git.

If Git is available, a commit/revision MAY be referenced.

Other artifact/version systems MAY be used.

Entering `IDLE` SHOULD produce or reference a durable checkpoint representing the accepted readiness state.

---

# 26. History

Every cycle MUST preserve enough information to reconstruct:

```text
Why did this cycle occur?

What evidence or Product gap justified it?

What requirement/objective was selected?

What assumptions existed?

What constraints applied?

What budget/schedule state applied?

What executor capabilities were required?

Which executor was used?

What operations occurred?

What observations resulted?

What changed?

How was the candidate validated?

Why was it accepted/rejected?

What remains unresolved?

Why did the lifecycle continue, wait, block or become IDLE?
```

History MUST survive executor replacement.

Material lifecycle history SHOULD preserve causal links rather than only chronological logs.

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

Do not consume resources merely because they remain available.

Budget exhaustion MUST NOT be represented as Product completion.

Depending on context it MAY produce:

```text
WAITING_FOR_CAPACITY
BLOCKED
PAUSED
IDLE
```

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
capacity restored
  │
  ▼
RESUME / REASSESS
```

Do not declare the Product complete because an executor became unavailable.

Likewise, a deadline, external dependency or required future evidence MUST NOT be mistaken for completion.

---

# 28A. Time and Scheduling

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
WAIT
    │
    ▼
scheduled/external condition
    │
    ▼
REASSESS
```

URACE SHOULD avoid active polling when a cheaper or event-driven wake mechanism is available.

Scheduling implementation is environment-specific.

URACE core MUST NOT require:

```text
cron
a permanent process
a particular scheduler
a particular operating system
a particular cloud scheduler
a particular queue
```

---

# 29. Executor Replacement

An executor MAY disappear permanently.

URACE MUST be able to:

1. preserve lifecycle state;
2. inspect required capabilities;
3. discover another compatible executor;
4. provide it with sufficient durable context;
5. continue.

No executor's private conversation history may be required for correctness.

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
```

MAY be executed by deterministic executors.

URACE SHOULD avoid expensive AI calls when deterministic execution adequately satisfies an operation.

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
human decision
```

Human participation MUST NOT be required for ordinary autonomous cycles unless policy requires it.

External users or market participants MAY additionally provide evidence without becoming lifecycle controllers.

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
}
```

Policy SHOULD distinguish hard enforcement boundaries from soft optimization preferences.

Readiness requirements SHOULD be derived from Product intent rather than assumed globally.

Executors MUST NOT override URACE policy.

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
- repeated reassessment without new evidence;
- repeated self-modification without demonstrated lifecycle value.

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

Safety controls MUST NOT force `IDLE` when meaningful justified work remains.

They SHOULD instead bound the current execution strategy and trigger reassessment, waiting, blocking or escalation as appropriate.

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

---

# 37. Interruption

On interruption:

1. stop scheduling new operations;
2. cancel active executor operations where supported;
3. persist authoritative state;
4. persist observations and diagnostics;
5. preserve current objective;
6. preserve constraint, budget and schedule state;
7. preserve evidence and relevant lineage;
8. release URACE-owned resources;
9. leave unrelated external state untouched.

---

# 38. Recovery

Restart MUST behave conceptually as:

```text
START
  │
  ▼
LOAD DURABLE STATE
  │
  ▼
RECONCILE CURRENT PRODUCT
  │
  ▼
RECONCILE LAST OPERATION
  │
  ▼
RESUME / RETRY / REASSESS
```

Never depend on recovering an old AI conversation to recover URACE.

An `IDLE` Product MUST remain resumable.

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

Evidence being first-class MUST NOT imply that evidence requires a dedicated physical directory, database, graph or service.

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

URACE only requires enough durable lifecycle context and evidence lineage to preserve lifecycle correctness.

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

Likewise, do not encode software-specific definitions of Product quality or completion into URACE core.

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
evidence handling
executor abstraction
validation
recovery
checkpointing
constraint enforcement
capacity handling
readiness assessment
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

If changing URACE is not required or sufficiently valuable for advancing the governed Product lifecycle, URACE SHOULD leave itself unchanged.

Conditional self-evolution is therefore an emergent application of the ordinary URACE lifecycle, not a separate privileged lifecycle.

---

# 45. Minimal Core

Bootstrap only the smallest coherent core required for:

```text
Product
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

Constraint, budget, schedule, evidence-lineage and readiness semantics SHOULD remain simple lifecycle data/policy rather than automatically becoming large independent frameworks.

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

---

## Step 3 — Implement Durable State

Implement:

- Product;
- ProductState;
- evidence and sufficient lineage;
- requirements/objectives;
- lifecycle state;
- history;
- checkpoints;
- policy;
- constraints;
- budget/schedule state;
- readiness state.

Test restart durability.

---

## Step 4 — Implement Generic Executor Contract

Implement the generic executor interface.

Do not mention any specific AI/orchestrator in core.

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

---

## Step 6 — Implement Capability Discovery

Allow executors to advertise capabilities.

URACE MUST be able to determine whether an operation can currently be attempted.

---

## Step 7 — Implement Generic Product Discovery

Discover enough about the current Product to expose:

```text
artifacts
available operations
validation possibilities
environment constraints
existing structure
applicable schedules
applicable budgets
available evidence
applicable readiness criteria
```

Do not require a known Product type.

---

## Step 8 — Implement Validation

Implement executor-independent acceptance.

Use deterministic validation wherever possible.

Allow Product-specific validation configuration.

Support Product-level readiness assessment without hard-coding one universal definition of quality.

---

## Step 9 — Implement Checkpoints

Persist accepted increments without assuming Git.

Use Git when available and useful.

Preserve enough evidence references and lineage to reconstruct material acceptance decisions.

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

and explain why the state is justified.

---

## Step 12 — Implement `--autonomous`

Implement:

```text
while autonomous mode enabled:

    load state

    gather available:
        Product evidence
        user/market evidence where applicable
        environmental evidence

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

    assess Product against intent and evidence

    identify highest-value justified gap

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

        if required evidence or progress depends
        on a future/external condition:
            persist waiting/idle state
            wait according to policy
            continue

        persist IDLE state
        stop active execution until a meaningful trigger
        continue

    derive required capabilities

    locate compatible executor(s)

    if required capacity unavailable:
        persist waiting/block state
        wait according to policy
        continue

    if operation would violate a HARD constraint:
        persist blocked state
        continue

    if operation exceeds a HARD budget:
        persist blocked/waiting state
        continue

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

There is no predetermined cycle count.

Each accepted increment MAY lead to another assessment cycle, and another justified cycle MAY follow for as long as meaningful Product evolution remains justified.

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

Restore compatible capacity.

Continue.

---

## Test K — Restart

Terminate URACE.

Restart.

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
WAIT
    ↓
condition becomes applicable
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

The applicable readiness gap MUST be derived from Product intent.

---

## Test R — Autonomous Convergence

Provide:

```text
intent sufficiently satisfied
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
```

No mutation, executor invocation or recursive requirement/objective generation SHOULD occur merely to keep autonomous mode active.

Then introduce meaningful new evidence and prove:

```text
IDLE
  │
  ▼
meaningful trigger
  │
  ▼
ASSESS
  │
  ▼
ACTIVE
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

---

## Test T — Evidence-to-Requirement Loop

Provide new Product, user, market or environmental evidence revealing a material gap.

Prove:

```text
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

The requirement MUST remain traceable to its justification.

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
evidence storage mechanism
```

and prove that the Core Invariants remain true.

---

## Test W — Evidence Lineage

Provide evidence that results in a material autonomous decision.

Prove that URACE can reconstruct:

```text
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

# 49. Market/Product Demonstration

For a Product with market intent, demonstrate:

```text
PRODUCT STATE
      │
      ▼
MARKET / USER / PRODUCT EVIDENCE
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
EXTERNAL MARKET EVIDENCE
```

URACE MAY autonomously drive the first three stages where capability, evidence and policy permit.

The final stage depends on actual external evidence and MUST NOT be fabricated.

If market evidence demonstrates a material mismatch:

```text
IDLE / READY
      │
      ▼
NEW MARKET EVIDENCE
      │
      ▼
ASSESS
      │
      ▼
MATERIAL GAP
      │
      ▼
JUSTIFIED REQUIREMENT
```

The Product lifecycle resumes.

This section demonstrates one Product-specific readiness variant.

It does not redefine market readiness as a universal URACE invariant.

---

# 50. Anti-Churn Demonstration

Prove that continuous autonomy does not mean arbitrary activity.

Given:

```text
no new evidence
no meaningful defect
no material readiness gap
no justified improvement
no unresolved objective
```

URACE MUST NOT repeatedly modify the Product simply because an executor remains available.

The same rule applies to URACE itself.

URACE MUST NOT repeatedly self-modify simply because improvements to its own implementation can be imagined.

It MAY:

- reassess later;
- wait for evidence;
- wait for a scheduled condition;
- become `IDLE` while autonomous mode remains enabled.

However, `no unresolved objective` alone is insufficient.

Before `IDLE`, URACE MUST establish that no material Product-level readiness gap is being hidden by an empty objective list.

The preferred convergence is:

```text
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
 │
 ▼
ACTIVE
```

This prevents both premature completion and endless autonomous churn.

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
21. It preserves evidence, provenance, lineage and assumptions sufficiently for lifecycle correctness.
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
40. `IDLE` preserves lifecycle continuity without continuous resource consumption.
41. `IDLE` requires Product-level readiness assessment rather than merely an empty task/objective list.
42. Material unresolved defects, risks or readiness gaps prevent premature `IDLE`.
43. Low-value speculative improvement does not prevent justified `IDLE`.
44. A meaningful new trigger can resume assessment from `IDLE`.
45. Readiness is derived from Product intent rather than one universal Product-quality definition.
46. Market validation remains evidence-based where applicable and is never inferred solely from AI opinion.
47. Budget, schedule, constraint and structural semantics remain portable across executor replacement.
48. The lifecycle avoids both premature completion and endless perfection loops.
49. Product, user, market and environmental evidence can produce traceable justified requirements where applicable.
50. Requirements do not exist independently from their Product justification.
51. Implementation results feed new evidence into subsequent assessment.
52. Market analysis remains an input/capability rather than becoming a mandatory URACE subsystem.
53. Core invariants remain stable while implementation and strategy variants change.
54. Product-specific readiness criteria can change without redefining URACE.
55. Variants remain replaceable unless promoting one is required to preserve a Core Invariant.
56. Evidence is a first-class lifecycle primitive without requiring a heavyweight evidence subsystem.
57. Material lifecycle decisions preserve sufficient evidence lineage to reconstruct their justification.
58. Observations, assumptions, inferences, hypotheses and validated evidence remain meaningfully distinguishable.
59. URACE can identify a material limitation in its own lifecycle machinery without requiring the Product/user to explicitly nominate URACE as the target.
60. URACE self-evolution follows ordinary lifecycle governance rather than privileged self-modification semantics.
61. URACE does not self-modify merely because self-improvement is possible.
62. Autonomous evolution supports an unbounded sequence of justified cycles rather than implying exactly one subsequent cycle.

---

# 52. Defensible Boundary

Do not allow URACE's purpose to drift downward into executor implementation.

The stack boundary is:

```text
┌─────────────────────────────────────┐
│ PRODUCT / USER / MARKET /           │
│ ENVIRONMENT                         │
└──────────────────┬──────────────────┘
                   │
                evidence
                   │
                   ▼
┌─────────────────────────────────────┐
│                URACE                │
│                                     │
│ Persistent Autonomous Product      │
│ Lifecycle Control Plane             │
│                                     │
│ intent                              │
│ state                               │
│ evidence + lineage                  │
│ requirements                        │
│ objectives                          │
│ policy                              │
│ constraints                         │
│ budgets / schedules                 │
│ validation                          │
│ readiness                           │
│ history                             │
│ recovery                            │
│ checkpoints                         │
└──────────────────┬──────────────────┘
                   │
          generic capabilities
                   │
                   ▼
┌─────────────────────────────────────┐
│       EXECUTION / INTELLIGENCE      │
│                                     │
│ one AI                              │
│ many AIs                            │
│ OpenHands                           │
│ another orchestrator                │
│ deterministic tools                 │
│ APIs                                │
│ humans                              │
│ future systems                      │
└─────────────────────────────────────┘
```

URACE's defensible responsibility is not producing superior intelligence.

It is maintaining **continuous, evidence-aware, policy-governed, validated and recoverable Product evolution independently of whichever intelligence systems happen to exist underneath it.**

Its responsibility includes preserving the causal chain:

```text
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

URACE determines when Product evolution should continue and when the Product has sufficiently converged for active evolution to become `IDLE`.

When a material limitation in URACE itself obstructs this lifecycle, that limitation MAY enter the same causal chain as an ordinary justified Product gap.

This does not create a separate self-improvement architecture.

It preserves one lifecycle.

URACE does NOT own the implementation of the intelligence used to perform market analysis, formulate solutions, write code, conduct research or execute other domain-specific work.

---

# 53. Bootstrap Restraint

Before implementing any subsystem, ask:

> **Must this capability remain authoritative and portable across executor replacement in order to preserve the autonomous Product lifecycle?**

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
LLM reasoning
coding
debugging intelligence
model inference
agent conversation management
sandbox implementation
IDE integration
language-specific intelligence
```

URACE MAY consume their results without owning their implementations.

Before declaring something a Core Invariant, ask:

> **Would URACE cease to preserve its defining lifecycle semantics if this changed?**

If NO:

It SHOULD remain policy, configuration or a variant.

Before expanding evidence infrastructure, ask:

> **Does lifecycle correctness require this evidence mechanism, or only sufficient provenance and lineage?**

If sufficient lineage can be preserved more simply, prefer the simpler mechanism.

Before turning a constraint into an enforcement mechanism, ask:

> **Is this an actual invariant or HARD boundary, or a preference that should guide autonomous selection?**

Before imposing physical structure, ask:

> **Does lifecycle correctness require this structure, or can the existing Product structure be discovered and used?**

Before generating a requirement, ask:

> **What Product intent, evidence, material risk, constraint or sufficiently supported opportunity justifies this requirement?**

Before beginning another autonomous objective, ask:

> **Does this action have sufficient expected Product value relative to its cost, risk, uncertainty and opportunity cost?**

Before modifying URACE itself, ask:

> **Is a demonstrated limitation in URACE materially constraining the governed Product lifecycle, and is changing URACE the highest-value justified response?**

If NO:

Do not self-modify merely because improvement is possible.

Before entering `IDLE`, ask:

> **Has the Product reached the highest justified readiness state currently supported by its intent, evidence and constraints, or is an empty objective list hiding meaningful unfinished work?**

For a market-intended Product, this MAY additionally ask:

> **Is the Product sufficiently market-ready for its current stage, or merely technically complete?**

If meaningful justified work remains:

Continue.

If required progress depends on unavailable external evidence, capacity or time:

Wait.

If the Product is sufficiently ready under its applicable readiness criteria and further autonomous work would primarily be speculative, cosmetic, redundant or unsupported by evidence:

Enter `IDLE`.

Do not manufacture a requirement or objective solely to prevent autonomous execution from ending.

---

# 54. Final Bootstrap Instruction

Bootstrap the **smallest implementation capable of proving the Core Invariants above**.

Do not optimize for feature count.

Do not reproduce capabilities available through external executors.

Do not promote implementation variants into Core Invariants without necessity.

Do not turn first-class evidence into a heavyweight evidence platform unless Product requirements independently justify one.

Do not create a privileged self-improvement subsystem.

Do not make OpenHands mandatory.

Do not make multiple AIs mandatory.

Do not make Git mandatory.

Do not make source code mandatory.

Do not make a programming language or Product type mandatory.

Do not make known file formats mandatory.

Do not make a specific operating environment mandatory at the architectural level.

Do not make a specific repository, directory or workspace structure mandatory.

Do not make a specific scheduler mandatory.

Do not make a specific budget representation mandatory.

Do not make market-fit-quality readiness mandatory for Products whose intent does not imply a market.

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

The canonical autonomous Product-evolution pattern is:

```text
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

The evidence source, evidence storage mechanism, readiness criteria, implementation strategy and executor topology are variants.

Evidence being first-class is invariant.

A particular evidence subsystem is not.

The lifecycle relationship is invariant.

For a market-intended Product, one specialization MAY be:

```text
MARKET + USER + PRODUCT EVIDENCE
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
```

For another Product, the evidence and readiness criteria MAY differ while the lifecycle remains unchanged.

The loop MUST NOT be interpreted as an obligation to continuously generate requirements.

Requirements exist to close justified Product gaps.

When no sufficiently valuable justified gap remains and applicable readiness requirements are satisfied, the correct autonomous result is `IDLE`.

When new evidence later reveals a meaningful gap:

```text
IDLE
 │
 ▼
NEW EVIDENCE
 │
 ▼
ASSESS
 │
 ▼
NEW JUSTIFIED REQUIREMENT
```

The lifecycle resumes.

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

`--autonomous` therefore continues autonomous Product evolution until explicitly paused, blocked by policy or external dependency, waiting for required capacity/evidence/time, or placed into `IDLE` because the Product has passed applicable readiness assessment and no sufficiently valuable justified action currently remains.

There is no predetermined number of autonomous cycles.

Conceptually:

```text
CYCLE
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
  │
  └────► IDLE
```

`IDLE` MUST NOT be premature.

An empty task list, completed objective or lack of executor suggestions is not sufficient evidence of completion.

Technical completion alone is not sufficient when Product intent implies additional material readiness requirements.

`IDLE` MUST NOT be endlessly postponed.

Perfection is not the completion criterion.

The existence of another conceivable improvement is not sufficient reason to continue.

This applies equally to the governed Product and to URACE itself.

The governing convergence rule is:

```text
CONTINUE
    when
expected Product value of justified action
meaningfully exceeds its cost / risk / opportunity cost

WAIT
    when
required progress depends on a future or external condition

BLOCK
    when
a HARD constraint prevents required progress

IDLE
    when
applicable readiness requirements are satisfied
AND
no material unresolved gap remains
AND
no currently available action has sufficient justified value
```

Readiness remains intent-relative:

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
```

Actual market validation remains external-evidence dependent:

```text
MARKET-FIT-QUALITY PRODUCT
            +
REAL USER / MARKET EVIDENCE
            │
            ▼
VALIDATED MARKET LEARNING
```

URACE MUST pursue applicable evidence when doing so is justified and possible.

URACE MUST wait when required evidence inherently depends on time or external actors.

URACE MUST resume when new evidence materially changes the Product state.

Individual requirements may complete.

Individual objectives may complete.

Individual cycles may complete.

Individual executors may terminate.

Individual AI conversations may disappear.

Models may change.

Orchestrators may change.

Programming languages may change.

Platforms may change.

Project structures may change.

Artifact formats may change.

Evidence storage mechanisms may change.

Validation mechanisms may change.

Schedulers may change.

Persistence mechanisms may change.

Readiness criteria may change with Product intent.

URACE itself may evolve when its limitations become materially relevant to the Product lifecycle.

The Product may become `IDLE`.

New evidence may reactivate it.

**The autonomous Product lifecycle remains.**

The final invariant test is:

> **If an executor, model, orchestrator, language, platform, structure, strategy or mechanism can be replaced while lifecycle correctness remains intact, it is a variant—not URACE's identity.**

The final evidence principle is:

> **Evidence is a first-class lifecycle primitive whose provenance and causal lineage justify autonomous decisions, without requiring URACE to become an evidence-management platform.**

The final self-evolution principle is:

> **URACE may evolve its own lifecycle machinery when evidence shows that a limitation in URACE materially constrains the governed Product lifecycle; such evolution requires no special invitation, receives no special privilege, and remains subject to the same justification, validation, checkpointing and convergence rules as every other change.**

The final design principle is:

> **URACE owns the persistent autonomous Product lifecycle; replaceable executors provide the intelligence and execution required to advance it.**

The final evolution principle is:

> **Evidence reveals justified Product gaps; gaps produce requirements and objectives; executors implement them; observations and independent validation determine acceptance; resulting Product state creates new evidence; URACE repeats the cycle while further action remains justified.**

And the final convergence principle is:

> **URACE must evolve each Product toward the highest justified readiness state implied by that Product's intent, evidence and constraints—not merely until work becomes inconvenient, and not beyond the point where further autonomous work has insufficient justified value.**
