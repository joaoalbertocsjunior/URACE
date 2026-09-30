# URACE — Universal Recursive Autonomous Co-Founder Engine

You are the Lead Systems Architect and Bootstrap Executor for this repository.

Your task is to bootstrap **URACE**.

URACE is a **self-contained, executor-agnostic persistent autonomous product-evolution control plane**.

Its unique responsibility is to preserve and govern a continuous product-development lifecycle across otherwise bounded, replaceable and potentially stateless intelligence/execution systems.

URACE MUST NOT become another coding agent, LLM framework, agent runtime, IDE agent, RAG platform, workflow engine, model provider, sandbox, or replacement for external intelligence.

Its purpose is:

> **Continuously evolve a product by preserving durable intent, state, evidence, decisions, policy, validation, recovery and history; selecting or commissioning justified next objectives; delegating intelligence-intensive or execution-intensive operations to replaceable executors; independently evaluating their results; checkpointing accepted increments; and repeating across executor sessions, technologies, repositories and platforms.**

The primary architectural invariant is:

> **URACE owns the autonomous product lifecycle. Replaceable executors supply whatever intelligence or execution is required to advance it.**

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

- product intent;
- durable product state;
- autonomous lifecycle state;
- evidence references;
- assumptions;
- decisions;
- objective history;
- current objective;
- execution history;
- validation policy;
- safety policy;
- resource policy;
- executor capability descriptions;
- checkpoint history;
- recovery state;
- interruption state;
- capacity state;
- acceptance/rejection of candidate increments.

External executors MAY provide:

- reasoning;
- research;
- planning;
- implementation;
- code modification;
- content generation;
- debugging;
- analysis;
- tool operation;
- architecture reasoning;
- market reasoning;
- product reasoning;
- testing assistance;
- repair reasoning.

URACE MUST remain authoritative over lifecycle state regardless of executor behavior.

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
- file format;
- file extension;
- artifact format;
- testing framework;
- IDE;
- editor.

The architecture MUST support:

> **universal file-base, project-type, platform and programming-language agnosticism.**

A project MAY be:

- software;
- documentation;
- configuration;
- infrastructure;
- data;
- research;
- design artifacts;
- mixed artifacts;
- another structured or file-based product.

URACE core MUST reason in terms of generic:

```text
Product
Artifact
State
Evidence
Objective
Operation
Executor
Observation
Validation
Checkpoint
Policy
```

rather than language-specific or framework-specific concepts.

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

---

# 5. Artifact

An Artifact is any addressable product resource.

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
```

Artifact interpretation SHOULD be delegated to executors or external tools capable of understanding it.

Unknown artifact types MUST degrade gracefully rather than invalidate the product.

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

---

# 10. Operating Modes

URACE MUST support at minimum:

## `--plan`

Assess and propose work without mutating the product.

## `--check`

Inspect current lifecycle, validation, evidence, capacity, objectives, checkpoints and recovery state.

## `--autonomous`

Run persistent autonomous product evolution.

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
DETERMINE HIGHEST-VALUE
JUSTIFIED NEXT OBJECTIVE
        │
        ▼
SELECT REQUIRED CAPABILITIES
        │
        ▼
SELECT COMPATIBLE EXECUTOR(S)
        │
        ▼
REASON / RESEARCH / PLAN
        │
        ▼
EXECUTE
        │
        ▼
OBSERVE
        │
        ▼
VALIDATE
        │
     ┌──┴──┐
     ▼     ▼
   PASS   FAIL
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
FRESH CYCLE
     │
     └──────────────► ASSESS AGAIN
```

The URACE lifecycle persists independently from individual executor lifetimes.

---

# 12. Continuous Means Lifecycle Continuity

Continuous autonomy MUST NOT require:

- one permanent process;
- one permanent AI conversation;
- one permanent agent;
- one permanent model;
- one permanent machine;
- one permanent orchestrator.

Instead:

```text
URACE STATE
    │
    ▼
CYCLE N
    │
 executor
    │
    ▼
checkpoint
    │
    ▼
URACE STATE
    │
    ▼
CYCLE N+1
    │
different executor allowed
```

Executor sessions SHOULD be considered replaceable.

Durable continuity belongs to URACE.

---

# 13. Objective Discovery

URACE MUST NOT merely consume an endless predetermined task list.

In autonomous mode it repeatedly asks:

> **Given product intent, current state, available evidence, previous decisions, unresolved risks, constraints and available capabilities, what is the highest-value justified next action?**

The reasoning required to answer this MAY be delegated.

Possible results include:

- product change;
- defect correction;
- research;
- hypothesis validation;
- reliability improvement;
- security improvement;
- usability improvement;
- documentation improvement;
- architecture improvement;
- cost reduction;
- evidence collection;
- no currently justified mutation.

These are examples only.

---

# 14. Product Value vs Activity

Continuous autonomy does NOT mean continuous mutation.

URACE MUST optimize for justified progress, not executor utilization.

An accepted cycle MUST materially:

- advance product intent;
- reduce meaningful uncertainty;
- acquire useful evidence;
- reduce meaningful risk;
- improve validated quality;
- resolve a blocker;
- or otherwise produce justified product progress.

Do NOT create work merely because AI credits or compute capacity remain available.

---

# 15. Evidence

Evidence is first-class lifecycle context.

Conceptually:

```text
Evidence {
    source
    observation
    provenance
    timestamp?
    confidence?
    classification
}
```

Evidence MAY originate from:

- users;
- analytics;
- tests;
- runtime observations;
- research;
- external systems;
- executors;
- operators;
- files;
- APIs;
- experiments.

Do not require a specific evidence source.

---

# 16. Market Awareness

For products with a market/user dimension, URACE SHOULD allow relevant external evidence to influence autonomous objectives.

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

If no market evidence is available, autonomous reasoning MAY formulate hypotheses but MUST NOT represent them as validated demand.

This distinction MUST survive across cycles.

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

    lifecycleState
    lastCycle
}
```

Exact serialization is an implementation detail.

Human-readable documents MUST NOT be the sole authoritative state store.

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

`GOAL_COMPLETE` MUST NOT imply global product completion.

In continuous autonomous mode:

```text
GOAL_COMPLETE
      │
      ▼
CHECKPOINT
      │
      ▼
ASSESS AGAIN
```

---

# 19. Validation

Executor confidence is not validation.

URACE owns acceptance policy.

Validation MUST be capability/project appropriate.

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
- external verification.

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

---

# 20. Validation Discovery

URACE SHOULD discover applicable validation mechanisms from the project.

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
- projects without conventional manifests;
- projects without source code.

Overrides MAY explicitly define validation operations.

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

Language-specific knowledge belongs to executors, adapters, discovery mechanisms or project configuration.

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

URACE MUST NOT assume the Product is a web application.

Its lifecycle must remain meaningful for any product that can expose:

```text
state
intent
artifacts
operations
observations
validation
```

This is the minimum conceptual product contract.

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

Checkpoints MUST NOT require Git.

If Git is available, a commit/revision MAY be referenced.

Other artifact/version systems MAY be used.

---

# 26. History

Every cycle MUST preserve enough information to reconstruct:

```text
Why did this cycle occur?

What objective was selected?

What evidence justified it?

What assumptions existed?

What executor capabilities were required?

Which executor was used?

What operations occurred?

What observations resulted?

What changed?

How was the candidate validated?

Why was it accepted/rejected?

What remains unresolved?

Why did the lifecycle continue?
```

History MUST survive executor replacement.

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

---

# 34. Policy

Policy governs autonomy independently from executors.

Conceptually:

```text
Policy {
    allowedOperations
    prohibitedOperations

    resourceLimits
    retryLimits

    validationRequirements

    approvalRequirements

    deploymentPolicy
}
```

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
```

Detect:

- repeated identical failures;
- oscillating plans;
- repeated reversions;
- validation gaming;
- low-value churn.

When progress cannot be justified:

```text
REASSESS
BLOCK
WAIT
or request additional evidence
```

rather than mutate indefinitely.

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
6. release URACE-owned resources;
7. leave unrelated external state untouched.

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

---

# 40. No Mandatory Custom RAG

Do NOT make URACE dependent on:

- vector databases;
- embeddings;
- AST databases;
- symbol graphs;
- repository maps;
- context sharding;
- custom RAG.

An executor MAY use any of them internally.

URACE only persists lifecycle-relevant context.

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

They are project-specific manifestations of:

```text
Artifact
Operation
Observation
Validation
Checkpoint
```

---

# 44. No Mandatory Self-Modification

URACE does not need a special self-improvement subsystem.

URACE itself MAY be managed as a Product.

Therefore:

```text
URACE runtime
     │
     ▼
URACE source/product
     │
     ▼
normal lifecycle
```

can eventually allow controlled self-development without giving self-modification privileged semantics.

---

# 45. Minimal Core

Bootstrap only the smallest coherent core required for:

```text
Product
State
Evidence
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

Avoid turning every concept into a large framework.

Prefer simple data contracts and composable modules.

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

---

# 47. Bootstrap Sequence

## Step 1 — Inspect

Inspect the existing product/repository/workspace.

Determine whether it is:

```text
EMPTY
EXISTING
URACE_INITIALIZED
```

Do not destroy existing work.

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
- evidence;
- objectives;
- lifecycle state;
- history;
- checkpoints;
- policy.

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

Discover enough about the current product to expose:

```text
artifacts
available operations
validation possibilities
environment constraints
```

Do not require a known project type.

---

## Step 8 — Implement Validation

Implement executor-independent acceptance.

Use deterministic validation wherever possible.

Allow project-specific validation configuration.

---

## Step 9 — Implement Checkpoints

Persist accepted increments without assuming Git.

Use Git when available and useful.

---

## Step 10 — Implement `--plan`

Perform assessment without mutation.

---

## Step 11 — Implement `--check`

Expose authoritative lifecycle state.

---

## Step 12 — Implement `--autonomous`

Implement:

```text
while autonomous mode enabled:

    load state

    gather available evidence

    determine current lifecycle condition

    identify next justified objective

    derive required capabilities

    locate compatible executor(s)

    if required capacity unavailable:
        persist waiting/block state
        wait according to policy
        continue

    execute bounded operation(s)

    persist observations

    independently validate candidate

    if validation fails:
        perform bounded repair/reassessment

    if accepted:
        checkpoint increment
        update authoritative ProductState

    begin a fresh assessment cycle
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
Cycle N   → Executor A
Checkpoint
Cycle N+1 → Executor B
```

Product continuity MUST survive replacement.

---

## Test C — Fresh Context

Terminate the intelligent executor completely.

Start a fresh executor session.

Continue using only durable URACE context.

---

## Test D — Unknown Project Type

Run against a product that does not match a hard-coded project template.

Core lifecycle MUST remain operational.

---

## Test E — Language Independence

Use at least two materially different software-language ecosystems without modifying URACE core semantics.

---

## Test F — Non-Software or Mixed Artifact

Demonstrate lifecycle operation over a product containing artifacts that are not exclusively source code.

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

# 49. Market/Product Demonstration

For a product with market intent, demonstrate:

```text
PRODUCT STATE
      │
      ▼
AVAILABLE EVIDENCE
      │
      ▼
AI REASONING
      │
      ▼
JUSTIFIED OBJECTIVE
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
NEXT OBJECTIVE
```

The demonstration MUST preserve the distinction between:

```text
fact
evidence
inference
hypothesis
```

---

# 50. Anti-Churn Demonstration

Prove that continuous autonomy does not mean arbitrary activity.

Given:

```text
no new evidence
no meaningful defect
no justified improvement
no unresolved objective
```

URACE MUST NOT repeatedly modify the product simply because an executor remains available.

It MAY:

- reassess later;
- wait for evidence;
- wait for a scheduled condition;
- become idle while autonomous mode remains enabled.

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

12. It is project-type agnostic.

13. It is file-format agnostic.

14. It is repository-host agnostic.

15. It is version-control agnostic.

16. It is operating-system/platform agnostic at the lifecycle level.

17. It is cloud-provider agnostic.

18. It supports software and non-software/mixed artifacts.

19. It independently validates executor results.

20. It produces recoverable checkpoints.

21. It preserves evidence and assumptions.

22. It can continue after capacity interruption.

23. It can continue after process restart.

24. It does not require custom RAG.

25. It does not require multi-agent infrastructure.

26. It does not require custom model routing.

27. It does not duplicate mature executor intelligence.

28. Continuous autonomy produces justified progress rather than arbitrary churn.

29. Product lifecycle semantics remain stable while underlying AI technology changes.

30. The implementation is significantly smaller and simpler than the intelligence systems it can coordinate.

---

# 52. Defensible Boundary

Do not allow URACE's purpose to drift downward into executor implementation.

The stack boundary is:

```text
┌─────────────────────────────────────┐
│      PRODUCT / MARKET / USER        │
└──────────────────┬──────────────────┘
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
│ evidence                            │
│ objectives                          │
│ policy                              │
│ validation                          │
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

It is maintaining **continuous, evidence-aware, policy-governed, validated and recoverable product evolution independently of whichever intelligence systems happen to exist underneath it.**

---

# 53. Bootstrap Restraint

Before implementing any subsystem, ask:

> **Must this capability remain authoritative and portable across executor replacement in order to preserve the autonomous product lifecycle?**

If YES:

It may belong in URACE.

If NO:

Delegate it.

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

---

# 54. Final Bootstrap Instruction

Bootstrap the **smallest implementation capable of proving the invariants above**.

Do not optimize for feature count.

Do not reproduce capabilities available through external executors.

Do not make OpenHands mandatory.

Do not make multiple AIs mandatory.

Do not make Git mandatory.

Do not make source code mandatory.

Do not make a programming language or project type mandatory.

Do not make known file formats mandatory.

Do not make a specific operating environment mandatory at the architectural level.

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

`--autonomous` continues autonomous product evolution until explicitly paused, blocked by policy or external dependency, waiting for required capacity/evidence, or placed into an idle state because no currently justified action exists.

Individual objectives may complete.

Individual executors may terminate.

Individual AI conversations may disappear.

Models may change.

Orchestrators may change.

Programming languages may change.

Platforms may change.

Project structures may change.

Artifact formats may change.

**The autonomous product lifecycle remains.**

The final design principle is:

> **URACE owns the persistent autonomous product lifecycle; replaceable executors provide the intelligence and execution required to advance it.**