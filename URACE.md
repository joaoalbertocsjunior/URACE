# URACE — Universal Recursive Autonomous Co-Founder Engine

You are the Lead Systems Architect and Bootstrap Executor for this repository.

Your task is to bootstrap **URACE**.

URACE is a self-contained, executor-agnostic persistent autonomous Product-evolution control plane.

Its unique responsibility is to preserve and govern a continuous Product lifecycle across bounded, replaceable and potentially stateless intelligence and execution systems.

URACE MUST NOT become:

- a coding agent;
- an LLM framework;
- an agent runtime;
- an IDE agent;
- a RAG platform;
- a workflow engine;
- a model provider;
- a sandbox;
- or a replacement for external intelligence.

Its purpose is:

> **Continuously evolve a Product by preserving durable Intent, State, Evidence, Triggers, Objectives, Plans, policy, validation, recovery and history; translating justified Product and environmental Evidence into action; reducing material uncertainty when learning has greater expected value than further implementation; delegating intelligence and execution to replaceable executors; independently validating results; checkpointing accepted increments; and remaining autonomously capable of reassessment whenever meaningful change occurs.**

Primary invariant:

> **URACE owns the autonomous Product lifecycle. Replaceable executors supply whatever intelligence or execution is required to advance it.**

Autonomous-liveness invariant:

> **While persistent `--autonomous` operation remains enabled, URACE MAY be ACTIVE or DORMANT, but MUST retain a viable path back to assessment. Dormancy is valid autonomous operation; ordinary end-loop is not.**

Therefore:

```text
NO JUSTIFIED WORK NOW
        │
        ▼
     DORMANT
        │
        ▼
WAIT / DISCOVER CHANGE
        │
        ▼
      TRIGGER
        │
        ▼
    REASSESS
```

not:

```text
NO JUSTIFIED WORK NOW
        │
        ▼
END AUTONOMOUS LOOP
```

---

# 1. Architectural Position

URACE occupies the persistent lifecycle-control layer above replaceable intelligence and execution systems.

```text
USERS / CUSTOMERS / MARKET / ENVIRONMENT
                  │
                  ▼
               EVIDENCE
                  │
                  ▼
┌──────────────────────────────────────────────┐
│                    URACE                     │
│                                              │
│ Intent                                       │
│ State                                        │
│ Evidence                                     │
│ Triggers                                     │
│ Requirements / Objectives                    │
│ Plans                                        │
│ Policy / Constraints                         │
│ Validation                                   │
│ Checkpoints / Recovery / History             │
│ Lifecycle Liveness                           │
│ Value / Uncertainty Assessment               │
└──────────────────────┬───────────────────────┘
                       │
              Generic execution boundary
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
       ONE AI     ORCHESTRATOR   DETERMINISTIC
                    / AGENT          TOOL
```

The minimum intelligent configuration is:

```text
URACE
  │
  ▼
ONE capable AI executor
```

An orchestrator, multiple AIs, dedicated Planner, Scheduler, watcher, queue or long-lived runtime MAY improve capability.

None is intrinsically required by the URACE core.

---

# 2. Normative Language

The terms:

- **MUST / MUST NOT** define architectural requirements;
- **SHOULD / SHOULD NOT** define strong defaults that MAY be overridden when justified;
- **MAY** defines optional or Product-dependent behavior.

Examples and diagrams illustrate these requirements.

They MUST NOT be interpreted as additional mandatory infrastructure unless explicitly stated.

---

# 3. Core Lifecycle Primitives

URACE SHOULD use the smallest representation that preserves these semantics:

```text
Product
Intent
State
Evidence
Trigger
Requirement
Objective
Plan
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

Their architectural status is:

```text
Product
    → first-class

Intent
    → first-class

Evidence
    → first-class

Trigger
    → first-class, lightweight

Meaningful Trigger
    → qualification of Trigger

Requirement
    → first-class where materially useful

Objective
    → first-class

Plan
    → first-class, lightweight

Product Value
    → derived

Information Gain
    → derived

Time-to-Evidence
    → contextual / derived

Market Fit
    → Intent-relative outcome, not universal primitive

Lifecycle Liveness
    → invariant lifecycle property

Autonomous Dormancy
    → valid autonomous lifecycle condition

Open-Ended Change Awareness
    → invariant lifecycle semantic

Trigger Condition
    → ordinary lifecycle / Plan / dormant-state data

Periodic Discovery
    → variant mechanism

Executor Availability
    → capacity condition

Schedule
    → temporal / conditional aspect of Plan or lifecycle state

Planner
    → replaceable capability

Scheduler
    → replaceable capability / mechanism

Trigger detector / watcher / timer / queue / webhook /
event bus / polling / alarm / platform wake
    → replaceable mechanisms
```

Do NOT introduce additional first-class concepts merely for conceptual symmetry.

A concept SHOULD become independently first-class only when lifecycle correctness materially benefits from its durable identity or independent semantics.

---

# 4. Product

A Product is the thing whose evolution URACE governs.

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

A Product MAY be:

- software;
- a service;
- a business process;
- research;
- content;
- an operational system;
- hardware-related;
- mixed;
- or a Product type unknown during bootstrap.

URACE MUST NOT assume software, source code, Git, customers, a startup, a market, an IDE, or a particular repository structure unless discovered from the Product.

---

# 5. Intent

Intent is the durable normative reference defining what the Product is for.

Conceptually:

```text
Intent {
  purpose
  desiredOutcomes?
  beneficiaries?
  protectedProperties?
  successConditions?
  boundaries?
  temporalConstraints?
  provenance?
}
```

Intent MUST remain distinguishable from:

```text
Objective
Requirement
Plan
Evidence
Trigger
Constraint
Strategy
Implementation
Metric
Executor recommendation
```

Conceptually:

```text
INTENT
    durable direction

EVIDENCE
    what is known or observed

TRIGGER
    candidate reason to reconsider prior assessment

VALUE
    expected or realized benefit relative to Intent

UNCERTAINTY
    materially relevant knowledge that remains insufficient

REQUIREMENT
    justified Product need

OBJECTIVE
    bounded target worth accomplishing

PLAN
    accepted strategy for advancing an Objective
```

Objectives, Plans, strategies and metrics MAY change without changing Intent.

Material Intent changes MUST preserve sufficient provenance and history.

Executors MUST NOT silently redefine Intent.

---

# 6. Evidence

Evidence is first-class.

Evidence MAY originate from:

- Product observations;
- validation;
- runtime behavior;
- users;
- customers;
- prospects;
- market research;
- analytics;
- experiments;
- external systems;
- deterministic measurement;
- executor research;
- authoritative human input;
- periodic discovery.

Evidence SHOULD preserve enough provenance and lineage to reconstruct material lifecycle decisions.

Conceptually:

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
GAP / UNCERTAINTY
  │
  ▼
OBJECTIVE
  │
  ▼
PLAN
  │
  ▼
EXECUTION / LEARNING
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
NEW EVIDENCE
```

Explicitly:

```text
EXECUTOR CLAIM ≠ EVIDENCE

TRIGGER ≠ EVIDENCE

INTERNAL CONFIDENCE ≠ EXTERNAL VALIDATION
```

---

# 7. Trigger

Trigger is a lightweight first-class lifecycle primitive.

A Trigger is:

> **An observed or discovered lifecycle-relevant candidate condition whose independent identity or semantics may matter to reassessment, recovery, deduplication, history or lifecycle continuity.**

Conceptually:

```text
Trigger {
  identity?
  source?
  kind?
  scope?
  observedAt?
  condition?
  references?
  provenance?
  evidenceReference?
  priorStateReference?
  currentStateReference?
  deduplicationKey?
  disposition?
}
```

This is conceptual.

Implementations MAY use simpler representations.

Not every raw event needs durable Trigger identity.

URACE SHOULD preserve Trigger identity/context/provenance/disposition only where needed for:

- correctness;
- reassessment;
- recovery;
- deduplication;
- scheduling;
- history;
- causal explanation;
- auditability.

Possible dispositions MAY include equivalents to:

```text
PENDING
IRRELEVANT
DUPLICATE
STALE
MEANINGFUL
ASSESSED
SUPERSEDED
```

These names are illustrative, not mandatory statuses.

Canonical Trigger pipeline:

```text
RAW EVENT / CONDITION / DISCOVERY RESULT
                  │
                  ▼
               NORMALIZE
                  │
                  ▼
                TRIGGER
                  │
                  ▼
       RELEVANCE / MEANINGFULNESS
             │             │
            NO            YES
             │             │
             ▼             ▼
      DISPOSE / COALESCE  REASSESS
```

Cheap deterministic filtering SHOULD be preferred when sufficient.

Obviously irrelevant, stale or duplicate raw events MAY be rejected before durable Trigger creation.

---

# 8. Meaningful Trigger

A Meaningful Trigger is:

> **A Trigger that is sufficiently credible and could materially alter the most recent lifecycle assessment relative to Product Intent, Evidence, Product state, policy, constraints, capacity, readiness, risk, accepted Plans, material uncertainty, temporal opportunity cost or expected Product value.**

The key word is **could**.

A Meaningful Trigger justifies reassessment.

It does NOT automatically justify:

- a Requirement;
- an Objective;
- a Plan;
- an Operation;
- Product mutation.

Therefore:

```text
TRIGGER
   │
   ▼
MEANINGFUL?
   │
   ├── NO ──► DORMANT / CONTINUE CURRENT STATE
   │
   └── YES
         │
         ▼
       ASSESS
         │
         ├── justified Objective
         │        │
         │        ▼
         │       PLAN
         │
         └── no justified action
                  │
                  ▼
               DORMANT
```

NOT:

```text
TRIGGER
   │
   ▼
TASK
```

---

# 9. Open-Ended Trigger Scope

Trigger scope MUST remain open-ended.

Relevant change MAY concern:

- Product identity;
- Intent;
- purpose;
- desired outcomes;
- Requirements;
- Objectives;
- Plans;
- strategy;
- priority;
- artifacts;
- files;
- configuration;
- dependencies;
- interfaces;
- contracts;
- schemas;
- data;
- documentation;
- Evidence;
- assumptions;
- uncertainty;
- observations;
- decisions;
- validation;
- quality;
- readiness;
- risk;
- blockers;
- policy;
- constraints;
- budget;
- schedule;
- deadlines;
- opportunity windows;
- environment;
- infrastructure;
- external systems;
- executor capability;
- executor availability;
- users;
- customers;
- markets;
- URACE state or machinery;
- relationships among these;
- newly discoverable facts.

This list is illustrative.

URACE MUST NOT require a closed universal event ontology.

---

# 10. Trigger vs Evidence

Trigger and Evidence are distinct.

```text
TRIGGER
    = why reassessment may be warranted

EVIDENCE
    = what is known or observed and supports conclusions
```

The same occurrence MAY produce both.

Examples:

```text
timer condition reached
    → Trigger

capacity restored
    → Trigger + capacity observation

customer result arrives
    → Trigger + potential Evidence

artifact changed
    → Trigger + Product observation

discovery finds dependency change
    → Trigger + potential Evidence
```

---

# 11. Open-Ended Discovery

URACE MUST NOT depend exclusively on predefined event subscriptions.

Where future relevant changes cannot be completely enumerated, bounded discovery SHOULD complement event-driven mechanisms.

Discovery MAY use:

- deterministic inspection;
- reconciliation;
- Product/environment inspection;
- executor-assisted reasoning;
- external queries;
- future equivalent mechanisms.

The discovery attempt itself is NOT automatically a Trigger.

What it discovers MAY become one.

Discovery SHOULD consider:

- expected change rate;
- risk;
- cost;
- budget;
- available capacity;
- executor cost;
- schedule;
- urgency;
- temporal constraints;
- previous results;
- known Trigger coverage;
- expected information value.

Prefer deterministic discovery when sufficient.

Executor-assisted discovery MUST be bounded by policy, cost, capacity and backoff.

---

# 12. Objective Discovery

URACE MUST NOT manufacture work merely to remain active.

Objective discovery SHOULD ask:

> **Given Product Intent, current Product state, Evidence, material uncertainty, constraints, risk, budget, time, accepted Plans and available capabilities, what sufficiently valuable gap or uncertainty most justifies action now?**

Canonical relationship:

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
HIGHEST-VALUE JUSTIFIED
GAP OR UNCERTAINTY
  │
  ▼
REQUIREMENT / OBJECTIVE
```

Possible Product-value dimensions MAY include:

- functionality;
- reliability;
- safety;
- usability;
- accessibility;
- clarity;
- acquisition;
- conversion;
- activation;
- adoption;
- engagement;
- retention;
- loyalty;
- satisfaction;
- trust;
- reduced friction;
- reduced customer effort;
- reduced cognitive load;
- reduced cost;
- increased productivity;
- realized outcomes;
- uncertainty reduction;
- information gain;
- readiness;
- Product coherence;
- other Intent-relative outcomes.

No individual dimension is universally authoritative.

---

# 13. Objective and Plan

An Objective is a bounded justified target.

A Plan is:

> **The accepted current strategy for advancing one or more justified Objectives under current Evidence, constraints, capabilities, resources and policy.**

Conceptually:

```text
Plan {
  objectiveReferences
  steps?
  dependencies?
  conditions?
  temporalConstraints?
  resourceConstraints?
  validationStrategy?
  evidenceStrategy?
  status?
}
```

Plan MUST remain lightweight.

It MUST NOT become a mandatory workflow DSL.

A Plan MAY be:

- minimal;
- partially ordered;
- conditional;
- dependency-based;
- sequential;
- parallel;
- executor-generated;
- deterministic;
- incrementally revised.

An Objective defines **what** should be accomplished.

A Plan describes **how URACE currently intends to pursue it**.

A Plan MAY change without redefining its Objective.

For a trivial Objective:

```text
OBJECTIVE
    │
    ▼
MINIMAL PLAN
    │
    ▼
OPERATION
```

is sufficient.

Plans SHOULD be durably preserved when their loss would materially affect lifecycle continuity, recovery, coordination or explanation.

Executor-generated Plans are proposals until URACE accepts them.

Plan completion does NOT imply Product completion or autonomous lifecycle termination.

---

# 14. Planner

Planner is a replaceable capability or service role.

Conceptually:

```text
plan(objective, context) -> proposed Plan
```

A Planner MAY be:

- the same AI used for execution;
- another AI;
- an orchestrator;
- deterministic logic;
- a hybrid;
- a future planning mechanism.

URACE MUST NOT depend on a dedicated Planner.

URACE remains responsible for:

- Objective justification;
- Plan acceptance;
- Plan persistence where needed;
- validation;
- determining continued Plan applicability;
- revision or supersession.

---

# 15. Scheduling

Scheduling determines when or under what temporal/conditional circumstances:

- accepted planned work may become actionable;
- reassessment may become worthwhile.

Scheduling MUST NOT become an independent source of Product justification.

Schedule is generally a temporal or conditional aspect of:

- Plan;
- dormant lifecycle state;
- reassessment state.

Examples MAY include:

```text
earliestStart
deadline
executionWindow
cooldown
reassessmentAfter
recurrence
waitUntilCondition
```

A Scheduler is replaceable.

Conceptually:

```text
schedule(plan/lifecycle condition, context)
    -> wake / actionable opportunity
```

When a scheduled condition becomes true:

```text
SCHEDULE / CONDITION TRUE
           │
           ▼
         TRIGGER
           │
           ▼
   RECONCILE AS NEEDED
           │
           ▼
    ASSESS / CONFIRM
       │          │
       ▼          ▼
PLAN STILL     PRIOR STATE
APPLICABLE     MAY HAVE CHANGED
       │          │
       ▼          ▼
    EXECUTE     REASSESS
```

URACE MAY efficiently confirm and execute already-justified planned work.

It MUST NOT blindly execute stale Plans.

---

# 16. Executor Boundary

URACE delegates bounded intelligence or execution through a generic executor boundary.

Conceptually:

```text
execute(operation, context) -> result
```

An executor MAY be:

- an AI model;
- AI coding tool;
- agent;
- orchestrator;
- deterministic tool;
- CLI;
- API;
- script;
- human-approved external system;
- future mechanism.

Executor reasoning formats MUST NOT become authoritative lifecycle state merely because an executor generated them.

URACE remains authoritative over:

- lifecycle state;
- Intent;
- Trigger interpretation;
- Objective justification;
- Plan acceptance;
- validation;
- Product acceptance.

---

# 17. Executor Cardinality and Capability

URACE MUST support:

```text
1..N executors
```

One capable executor MUST remain sufficient for the minimum intelligent configuration.

Multiple executors MAY provide:

- specialization;
- redundancy;
- independent review;
- capability coverage;
- parallelism.

Executor selection SHOULD be capability-based rather than brand-based.

Capabilities MAY include:

```text
reasoning
research
planning
coding
tool-use
browser-use
validation
document-generation
data-analysis
change-discovery
trigger-relevance-assistance
```

Zero intelligent executors MAY temporarily be available.

That MUST NOT imply:

- Product completion;
- lifecycle termination;
- readiness;
- loss of Product ownership.

---

# 18. Capacity and Graceful Degradation

If a preferred capability is unavailable:

1. use another compatible executor where appropriate;
2. reformulate the Operation where appropriate;
3. use deterministic logic where sufficient;
4. wait when capacity may return;
5. block only when a HARD requirement cannot currently be satisfied.

Canonical state:

```text
JUSTIFIED WORK
      │
      ▼
NO COMPATIBLE CAPACITY
      │
      ▼
WAITING_FOR_CAPACITY
      │
      ▼
DORMANT + PRESERVE LIVENESS
```

Explicitly:

```text
EXECUTOR UNAVAILABLE
    ≠ PRODUCT COMPLETE

EXECUTOR UNAVAILABLE
    ≠ END AUTONOMOUS LOOP

EXECUTOR AVAILABLE
    ≠ JUSTIFIED PRODUCT WORK
```

Executor restoration MAY create a Trigger when materially relevant.

---

# 19. Product Value and Evidence Velocity

Product Value is derived relative to Intent.

When uncertainty materially constrains Product-value assessment, reducing that uncertainty MAY have greater expected value than further implementation.

URACE SHOULD ask:

> **What is the smallest safe action capable of producing sufficiently decision-relevant Evidence soon enough to improve the next lifecycle decision?**

Conceptually:

```text
INTENT
  +
CURRENT EVIDENCE
  +
EXPECTED OUTCOME
  +
EXPECTED INFORMATION GAIN
  +
TIME-TO-EVIDENCE
  +
COST
  +
RISK
  +
OPPORTUNITY COST
        │
        ▼
EXPECTED PRODUCT VALUE
        │
        ▼
JUSTIFIED OBJECTIVE?
```

This is a decision principle.

It is NOT a mandatory numerical formula.

When otherwise valid alternatives have comparable expected outcome value, URACE SHOULD generally prefer the alternative that produces credible decision-relevant Evidence:

- sooner;
- more cheaply;
- with less irreversible commitment;
- with proportionate risk.

Speed alone is NOT sufficient.

Fast but misleading Evidence SHOULD NOT outrank slower but materially more credible Evidence merely because it is faster.

---

# 20. External Reality

When Product success materially depends on external users, customers, markets, environments or systems, internally generated confidence MUST NOT substitute for obtainable external Evidence.

Where proportionate and safe:

```text
BUILD MORE
    vs
LEARN FROM REALITY
```

MUST be treated as a real lifecycle trade-off when external uncertainty is material.

URACE SHOULD prefer earlier credible exposure to relevant external reality over unnecessary speculative refinement when doing so has greater expected Intent-relative value.

This does NOT imply every Product requires:

- customers;
- market testing;
- an MVP;
- experiments;
- analytics;
- A/B tests;
- startup methodology.

---

# 21. Time-Bounded Evolution

When Intent, policy, Evidence or constraints establish a meaningful finite time window, time MUST participate in lifecycle assessment.

Examples MAY include:

- launch window;
- runway;
- deadline;
- regulatory window;
- seasonal opportunity;
- contract commitment;
- experiment window;
- market opportunity.

URACE SHOULD consider:

```text
Expected Product Value
Expected Information Gain
Time-to-Evidence
Time-to-Outcome
Cost
Risk
Opportunity Cost
```

when comparing otherwise valid actions.

URACE SHOULD avoid:

```text
PERFECT PRODUCT
      │
      ▼
TOO LATE TO LEARN
```

when earlier credible Evidence could materially improve lifecycle decisions.

Time pressure MUST NOT override:

- HARD constraints;
- safety;
- authoritative policy;
- required validation.

---

# 22. Market-Fit-Seeking Products

Market fit is NOT a universal URACE primitive.

It is an Intent-relative outcome applicable only where Product success materially depends on market adoption or demand.

For such Products:

```text
PRODUCT EXISTS
      ≠
PRODUCT IS WANTED

INTERNAL CONFIDENCE
      ≠
EXTERNAL MARKET EVIDENCE
```

Relevant Evidence MAY concern:

- problem relevance;
- demand;
- willingness to adopt;
- willingness to pay;
- activation;
- repeated use;
- retention;
- realized value;
- acquisition feasibility;
- conversion;
- satisfaction;
- trust;
- other Intent-relative signals.

No single metric universally defines Product-market fit.

A time-bounded fit-seeking lifecycle SHOULD tend toward:

```text
INTENT
  │
  ▼
CRITICAL UNCERTAINTY
  │
  ▼
SMALLEST CREDIBLE TEST
  │
  ▼
REAL MARKET EXPOSURE
  │
  ▼
EVIDENCE
  │
  ├── supports direction
  ├── contradicts direction
  └── insufficient / ambiguous
          │
          ▼
       REASSESS
```

URACE MUST NOT promise or fabricate market fit.

The defensible target is credible Evidence of:

```text
FIT / PROMISING DIRECTION

NON-FIT / PIVOT REQUIREMENT

or

INSUFFICIENT EVIDENCE / NEXT UNCERTAINTY
```

within applicable constraints.

---

# 23. Validation and Acceptance

Executor confidence is not validation.

Implementation success is not automatically Product readiness.

Predicted external outcomes are not realized external outcomes.

URACE MUST independently evaluate executor results according to applicable Product validation mechanisms.

When an Objective exists primarily to reduce uncertainty, validation SHOULD determine whether the resulting Evidence is sufficiently:

- credible;
- relevant;
- decision-useful.

A technically successful test that produces unusable Evidence is not necessarily a successful lifecycle result.

Accepted increments SHOULD be checkpointed where appropriate.

Failed validation SHOULD lead to repair, reassessment, rejection or recovery according to policy.

---

# 24. State and Persistence

URACE SHOULD preserve the minimum durable state necessary to reconstruct lifecycle continuity.

Conceptually:

```text
ProductState {
  product
  intent
  constraints
  currentCheckpoint
  currentObjective
  currentPlan?
  evidence
  triggers?
  assumptions
  uncertainties?
  risks
  blockers
  completedObjectives
  failedObjectives
  planHistory?
  validationState
  capacityState
  budgetState
  scheduleState
  temporalState?
  readinessState
  lifecycleState
  livenessState?
  wakeState?
  relevantTriggerConditions?
  lastDiscoveryState?
  lastCycle
}
```

Intent MUST be durable or durably referenced.

Evidence lineage MUST be durable where required for reconstruction.

Material Trigger continuity MUST be durable where required.

Plans SHOULD be durable when losing them would materially affect continuity.

Dormant state MUST preserve enough information to recover its wake/resume semantics.

Persistence technology is a variant.

---

# 25. Lifecycle States

URACE SHOULD support conceptual equivalents of:

```text
ASSESSING
ACTIVE
VALIDATING
REPAIRING
WAITING_FOR_CAPACITY
WAITING_FOR_CONDITION
WAITING_FOR_SCHEDULE
BLOCKED
PAUSED
IDLE
```

These are not necessarily mandatory literal status names.

The following are ordinarily dormant autonomous states:

```text
WAITING_FOR_CAPACITY
WAITING_FOR_CONDITION
WAITING_FOR_SCHEDULE
resumable BLOCKED
IDLE
```

`IDLE` means:

> **No sufficiently justified Product action is currently known.**

It does NOT mean:

> **URACE has permanently finished governing the Product.**

---

# 26. Autonomous Liveness

Persistence and liveness are different.

```text
DURABILITY
    state survives runtime termination

LIVENESS
    autonomous lifecycle remains capable of progressing

WAKEABILITY
    dormant lifecycle can become active after relevant change

DORMANCY
    no justified work is currently actionable,
    while autonomous ownership remains active

END-LOOP
    autonomous lifecycle ownership ceases
```

For persistent `--autonomous`:

```text
DORMANT
    = VALID

END-LOOP
    = NOT A NORMAL CONVERGENCE STATE
```

A dormant URACE MAY wait for:

- external Trigger;
- scheduled Trigger;
- conditional Trigger;
- Evidence;
- capacity;
- bounded discovery.

URACE MUST NOT manufacture work merely to avoid dormancy.

---

# 27. Runtime Lifetime vs Lifecycle Lifetime

Runtime termination and lifecycle termination MUST remain distinct.

```text
RUNTIME EXIT
    ≠
AUTONOMOUS LIFECYCLE END
```

A runtime MAY release resources during dormancy only when equivalent durable wake/resume responsibility exists elsewhere.

Possible mechanisms include:

- timer;
- watcher;
- scheduler;
- alarm;
- queue;
- webhook;
- event bus;
- orchestrator callback;
- OS service;
- serverless invocation;
- periodic reconciliation;
- platform-native wake;
- future equivalent mechanisms.

None is universally mandatory.

If no durable external wake/resume mechanism exists, the responsible persistent autonomous runtime MUST remain efficiently capable of observing or discovering relevant candidate change.

This MAY require a long-lived but mostly dormant process.

It MUST NOT require continuous AI inference.

---

# 28. Persistent `--autonomous`

Unless explicitly bounded or one-shot:

> **`--autonomous` denotes continuing lifecycle ownership, not merely execution until the current work queue becomes empty.**

Canonical state machine:

```text
              ┌───────────────┐
              │               │
              ▼               │
            ACTIVE            │
              │               │
              ▼               │
            ASSESS            │
              │               │
      ┌───────┴────────┐      │
      │                │      │
JUSTIFIED WORK     NO JUSTIFIED
      │              WORK
      ▼                │
 OBJECTIVE             ▼
      │              DORMANT
      ▼                │
    PLAN               │
      │                │
      ▼                │
EXECUTE / LEARN        │
      │                │
      ▼                │
   VALIDATE             │
      │                │
      ▼                │
 CHECKPOINT             │
      │                │
      ▼                │
UPDATE EVIDENCE         │
      │                │
      └──────► ASSESS   │
                       │
             external / scheduled /
             conditional / discovered
                     change
                       │
                       ▼
                    TRIGGER
                       │
                       ▼
                  MEANINGFUL?
                   │       │
                  NO      YES
                   │       │
                   ▼       └───────┐
                DORMANT            │
                                   │
                                   └──► ASSESS
```

The normal persistent-autonomous cycle is therefore:

```text
ACTIVE
  ↕
DORMANT
```

not:

```text
ACTIVE
  ↓
NO WORK
  ↓
END
```

---

# 29. When Autonomous Operation May End

Persistent autonomous lifecycle ownership MAY end only when justified by explicit lifecycle semantics such as:

- user/operator stop;
- explicit cancellation;
- explicitly bounded execution reaching its boundary;
- explicit one-shot invocation;
- authoritative policy requiring termination;
- another explicit Product/project contract condition that defines termination.

Product readiness alone MUST NOT silently terminate persistent `--autonomous`.

No current Objective MUST NOT terminate it.

Plan completion MUST NOT terminate it.

Executor unavailability MUST NOT terminate it.

Dormancy MUST NOT terminate it.

Market-fit Evidence MUST NOT automatically terminate it.

A Product that currently satisfies readiness conditions MAY simply become dormant and remain responsive to future material change.

---

# 30. Autonomous Lifecycle

Canonical lifecycle:

```text
LOAD
  │
  ▼
RECONCILE
  │
  ▼
ASSESS
  │
  ├── justified gap / uncertainty
  │          │
  │          ▼
  │      OBJECTIVE
  │          │
  │          ▼
  │         PLAN
  │          │
  │          ▼
  │   EXECUTE / LEARN
  │          │
  │          ▼
  │       OBSERVE
  │          │
  │          ▼
  │       VALIDATE
  │          │
  │          ▼
  │      CHECKPOINT
  │          │
  │          ▼
  │   UPDATE EVIDENCE
  │          │
  └──────────┘

ASSESS
  │
  └── no justified action
             │
             ▼
          READINESS
             │
             ▼
          DORMANT
             │
             ▼
      PRESERVE LIVENESS
             │
      ┌──────┼───────────────┐
      │      │               │
   EXTERNAL SCHEDULED     BOUNDED
    CHANGE  CONDITION     DISCOVERY
      │      │               │
      └──────┴───────┬───────┘
                     ▼
                  TRIGGER
                     │
                     ▼
              MEANINGFUL?
               │          │
              NO         YES
               │          │
               ▼          ▼
            DORMANT     ASSESS
```

---

# 31. Readiness and Convergence

Readiness SHOULD consider:

```text
Intent satisfaction
+ HARD constraints
+ validation
+ known defects
+ risk
+ Product coherence
+ external Evidence where applicable
+ unresolved material uncertainty
+ temporal opportunity cost
+ resource reasonableness
+ absence of higher-value justified action
```

URACE MUST avoid both:

```text
PREMATURE IDLE
```

and:

```text
ENDLESS ACTIVE CHURN
```

Correct convergence:

```text
ACTIVE WORK
    │
    ▼
  ASSESS
    │
    ▼
NO JUSTIFIED ACTION
    │
    ▼
  DORMANT
    │
    ▼
PRESERVE LIVENESS
```

Active-loop convergence and autonomous-lifecycle termination are different concepts.

---

# 32. Anti-Churn

URACE MUST NOT repeatedly:

- optimize metrics without sufficient Product-value justification;
- create Objectives because an executor is available;
- create Plans because a Planner can produce them;
- execute merely because a Scheduler fired;
- build merely because building is possible;
- self-modify merely because it can;
- call executors merely to keep a runtime alive;
- reassess expensively because a timer fired;
- retry unavailable executors without bounded backoff;
- manufacture Triggers when nothing relevant changed;
- manufacture work to avoid dormancy;
- perform discovery whose expected value does not justify its cost;
- treat dormancy as failure;
- terminate autonomous ownership merely because active work converged.

---

# 33. Safety, Constraints and Policy

HARD constraints MUST NOT be silently overridden by:

- executor judgment;
- Product-value reasoning;
- information-gain reasoning;
- planning;
- scheduling;
- time pressure;
- market pressure;
- autonomous self-modification.

URACE SHOULD distinguish HARD requirements from SOFT preferences where applicable.

Policy governs:

- what URACE may do;
- what requires approval;
- acceptable risk;
- budgets;
- resource limits;
- external interaction;
- self-modification;
- execution boundaries;
- lifecycle termination conditions.

Autonomy remains bounded by policy.

---

# 34. Recovery

Lifecycle state MUST be recoverable sufficiently to continue from interruption without depending on hidden executor context.

Recovery SHOULD reconstruct, where relevant:

- Product;
- Intent;
- Evidence;
- material Triggers;
- current Objective;
- current Plan;
- validation state;
- checkpoint;
- capacity;
- dormant/wake state;
- relevant constraints;
- unresolved uncertainty.

A fresh executor context SHOULD be able to continue the lifecycle from durable URACE state.

---

# 35. Conditional Self-Evolution

URACE MAY evolve its own implementation when doing so is itself justified relative to Product/project Intent, Evidence, constraints, risk and expected value.

URACE MUST NOT self-modify merely because self-improvement is theoretically possible.

Self-evolution follows the same lifecycle:

```text
EVIDENCE
  │
  ▼
JUSTIFIED GAP
  │
  ▼
OBJECTIVE
  │
  ▼
PLAN
  │
  ▼
EXECUTION
  │
  ▼
VALIDATION
  │
  ▼
CHECKPOINT
```

No privileged self-modification path is required.

---

# 36. Agnosticism

URACE MUST NOT fundamentally depend on a particular:

- Product domain;
- executor;
- model;
- orchestrator;
- programming language;
- file format;
- repository layout;
- persistence technology;
- scheduler;
- wake mechanism;
- Trigger source;
- Trigger-delivery mechanism;
- periodic-discovery mechanism;
- planning algorithm;
- Planner implementation;
- scheduling algorithm;
- Product-value metric;
- market-fit metric;
- experimentation methodology;
- runtime model.

Classification rule:

> **If a mechanism or strategy can change while the Intent → Evidence → Trigger/Reassessment → justified gap/uncertainty → Objective → Plan → execution/learning → validation → checkpoint lifecycle remains correct and autonomously resumable, it SHOULD remain a variant.**

---

# 37. Minimal Implementation

Prefer the smallest implementation satisfying the invariants.

A possible logical structure is:

```text
core/
  lifecycle
  state
  intent
  trigger
  objective
  plan
  policy

execution/
  executor
  operation
  capabilities

evidence/
  evidence
  lineage

validation/
  validation

checkpoint/
  checkpoint

persistence/
  persistence

discovery/
  product
  capabilities

cli/
  commands
```

This is illustrative.

Do NOT create dedicated:

```text
market-fit/
experiments/
learning/
planner/
scheduler/
liveness/
events/
monitoring/
```

subsystems merely because those semantics may occur.

---

# 38. Operating Modes

URACE SHOULD expose conceptual equivalents to:

```text
--plan
--check
--autonomous
```

Exact CLI syntax is a variant.

## `--plan`

Inspect the Product and produce or revise an appropriate Plan without necessarily executing it.

## `--check`

Report relevant lifecycle state, including where applicable:

- Product;
- Intent;
- Evidence;
- recent/pending material Triggers;
- current Objective;
- current Plan;
- validation;
- capacity;
- readiness;
- lifecycle state;
- liveness;
- relevant wake/Trigger conditions;
- recovery state;
- material uncertainty;
- temporal constraints.

If dormant, `--check` SHOULD make clear:

```text
WHY IS URACE DORMANT?

WHAT COULD REACTIVATE IT?

WHO OR WHAT CURRENTLY OWNS WAKE RESPONSIBILITY?
```

## `--autonomous`

Run persistent autonomous Product evolution.

Persistent `--autonomous` MUST support:

```text
ACTIVE AUTONOMY
```

and:

```text
DORMANT AUTONOMY
```

without converting dormancy into end-loop.

---

# 39. Bootstrap Sequence

Bootstrap in this order unless Product-specific constraints justify another sequence.

## 1 — Inspect

Discover:

- Product type;
- structure;
- existing state;
- Intent;
- constraints;
- artifacts;
- Evidence;
- uncertainty;
- validation mechanisms;
- execution capabilities;
- persistence opportunities;
- runtime/hosting semantics;
- event/wake opportunities.

## 2 — Choose Minimum Architecture

Implement only what is necessary to satisfy the invariants.

## 3 — Establish Durable Lifecycle State

Persist enough state to reconstruct continuity.

## 4 — Establish Executor Boundary

Keep executor-specific details outside authoritative lifecycle semantics.

## 5 — Support One Capable AI

The minimal intelligent configuration MUST work without a multi-agent orchestrator.

## 6 — Discover Capabilities

Distinguish unavailable capability from nonexistent capability.

## 7 — Establish Trigger Semantics

Support:

```text
candidate condition
      ↓
normalize
      ↓
Trigger
      ↓
Meaningful?
      ↓
reassess
```

## 8 — Establish Validation

Keep acceptance independent from executor confidence.

## 9 — Establish Checkpoints and Recovery

Accepted increments SHOULD be recoverable where appropriate.

## 10 — Establish Objective / Plan Separation

Preserve:

```text
WHAT is justified
```

versus:

```text
HOW it should currently be pursued
```

## 11 — Establish Value / Uncertainty Assessment

Where relevant, consider:

```text
expected Product value
expected information gain
time-to-Evidence
cost
risk
opportunity cost
```

without requiring a fixed formula.

## 12 — Establish Liveness

Persistent `--autonomous` MUST support:

```text
ACTIVE
  ↕
DORMANT
```

and MUST identify durable wake ownership before releasing the responsible runtime.

## 13 — Expose Operating Modes

Provide conceptual equivalents of plan, check and autonomous operation.

---

# 40. Canonical Autonomous Algorithm

Conceptually:

```text
while persistent autonomous ownership is enabled:

    load durable lifecycle state

    reconcile

    assess against Intent

    if sufficiently justified action exists:

        choose highest-value gap or uncertainty

        formulate Objective

        create minimum useful Plan

        execute / learn when actionable

        observe

        validate

        checkpoint accepted change

        update Evidence

        reassess

    else:

        enter DORMANT

        persist lifecycle state

        preserve known Trigger conditions

        preserve scheduled conditions

        preserve external Trigger paths

        preserve bounded discovery where needed

        if durable external wake responsibility exists:
            current runtime may release resources
        else:
            responsible runtime remains efficiently
            capable of observing or discovering change

        wait without manufacturing work

        when a candidate condition occurs:
            normalize it
            create/preserve Trigger where appropriate
            determine whether it is Meaningful

        if Meaningful:
            reconcile
            reassess
        else:
            remain DORMANT
```

This pseudocode defines semantics, not a mandatory implementation technique.

---

# 41. Mandatory Behavioral Tests

Implementations SHOULD prove the architecture through behavior rather than merely mirror terminology.

## A — One Executor

URACE operates correctly with one capable AI executor.

## B — Executor Replacement

Replace the executor between lifecycle cycles.

Intent, Evidence, Objective/Plan state and lifecycle continuity remain intact.

## C — Fresh Context

Restart with no conversational context.

Durable URACE state is sufficient to continue correctly.

## D — Unknown Product

Bootstrap against a Product type not anticipated by the implementation.

URACE discovers semantics instead of assuming software.

## E — No Git

Operate correctly without Git where another checkpoint/history mechanism is appropriate.

## F — Orchestrator Optional

Remove the orchestrator.

One capable executor remains sufficient.

## G — Capacity Loss

Required executor capacity disappears.

Expected:

```text
WAITING_FOR_CAPACITY
        │
        ▼
      DORMANT
```

not lifecycle termination.

## H — All Executors Unavailable

All intelligent executors become unavailable.

URACE preserves state and autonomous liveness.

It MAY continue deterministic observation/discovery where appropriate.

## I — Executor Restoration

Relevant capacity returns.

The change MAY create a Trigger.

URACE reassesses when meaningful rather than automatically manufacturing work.

## J — Validation Failure

Executor claims success but validation fails.

URACE does not accept the increment.

## K — Intent Persistence

Replace executors and restart runtime.

Intent remains authoritative and attributable.

## L — Intent vs Objective

Change an Objective without changing Intent.

URACE preserves the distinction.

## M — Evidence Lineage

A material Objective can be traced to the Evidence and Intent that justified it.

## N — Trigger Without Mutation

A Meaningful Trigger causes reassessment.

Reassessment concludes no Product mutation is justified.

URACE returns to dormancy correctly.

## O — Trigger Mechanism Replacement

Replace webhook delivery with polling, queue, timer or another mechanism.

Trigger semantics remain unchanged.

## P — Trigger Storm

Deliver repeated equivalent events.

URACE deduplicates/coalesces where practical without losing distinct material changes.

## Q — Unknown Trigger Source

A relevant change originates from a source not pre-enumerated by the bootstrap.

Bounded discovery can surface it.

## R — Trigger Persistence Across Restart

A material Trigger causes reassessment across a runtime boundary.

Enough Trigger context survives to preserve lifecycle correctness.

## S — Trigger Is Not Evidence

A timer fires.

It may create a Trigger but does not fabricate Evidence.

## T — Plan Persistence

A multi-step Objective spans runtime or executor replacement.

The accepted Plan remains reconstructable where continuity requires it.

## U — Plan Replaceability

New Evidence invalidates the current strategy without invalidating the Objective.

URACE revises/supersedes the Plan.

## V — Planner Replacement

Replace the planning mechanism.

Plan semantics and lifecycle authority remain unchanged.

## W — Scheduler Replacement

Replace the scheduling mechanism.

Temporal lifecycle semantics remain unchanged.

## X — Schedule Is Not Justification

A scheduled time arrives.

URACE confirms applicability or reassesses instead of treating time alone as Product justification.

## Y — Plan Completion Is Not Lifecycle Completion

Plan completes.

URACE validates, checkpoints, updates Evidence and reassesses.

## Z — Periodic Discovery Finds Nothing

A bounded discovery cycle finds no relevant change.

No fake Trigger or Objective is created.

URACE remains dormant.

## AA — Executor Unavailable During Discovery

Executor-assisted discovery is due but capacity is unavailable.

URACE waits according to bounded policy.

Lifecycle remains live.

## AB — Autonomous Dormancy

Persistent `--autonomous` reaches no currently justified action.

Expected:

```text
ACTIVE
  ↓
ASSESS
  ↓
NO JUSTIFIED ACTION
  ↓
DORMANT
```

The autonomous lifecycle remains enabled.

## AC — Scheduled Dormancy

URACE waits for a justified future condition.

```text
DORMANT
  ↓
scheduled condition
  ↓
TRIGGER
  ↓
MEANINGFUL?
  ↓
ASSESS
```

No autonomous end-loop occurs.

## AD — External-Trigger Dormancy

URACE remains dormant until external change occurs.

It need not consume continuous AI resources.

External change can reactivate assessment.

## AE — Runtime Release During Dormancy

A durable external wake mechanism exists.

The current process exits.

Expected:

```text
PROCESS EXIT
    ≠
AUTONOMOUS LIFECYCLE END
```

Future invocation reconstructs lifecycle continuity.

## AF — No Wake Path

URACE becomes dormant and no durable external wake mechanism exists.

The responsible persistent autonomous runtime MUST NOT terminate merely because no work is currently justified.

It waits efficiently.

## AG — Persistence Is Not Wakeability

State survives process exit, but no mechanism can ever reactivate it.

This does NOT satisfy persistent autonomous liveness.

## AH — No Premature IDLE

A materially justified high-value action remains.

URACE does not become dormant merely because current execution completed.

## AI — Anti-Perfection

Low-value refinement remains possible indefinitely.

URACE converges to dormancy when further active work lacks sufficient justified value.

## AJ — Time-to-Evidence

Two safe alternatives have similar expected outcome value.

One generates materially better decision-relevant Evidence substantially sooner and more cheaply.

URACE SHOULD prefer it unless another constraint or risk justifies otherwise.

## AK — Evidence Quality vs Speed

The fastest test produces weak or misleading Evidence.

A slower test produces materially more credible Evidence.

URACE does not optimize blindly for speed.

## AL — External Evidence Before Overbuilding

A market-dependent Product has unresolved demand uncertainty.

More internal implementation yields little information.

A smaller credible external test exists.

URACE recognizes Evidence acquisition as potentially higher-value.

## AM — Negative External Evidence

Credible external Evidence contradicts a critical assumption.

URACE reassesses instead of blindly continuing the existing Plan.

## AN — Temporal Opportunity

A meaningful finite window exists.

URACE accounts for time-to-Evidence and opportunity cost without violating HARD constraints.

## AO — No Market Assumption

A Product has no meaningful customer/market context.

URACE does not manufacture market-fit Objectives or startup metrics.

## AP — Market Fit Does Not End Autonomy

Current Evidence strongly supports market fit.

No higher-value work is currently justified.

Expected:

```text
DORMANT
```

not autonomous lifecycle termination.

Future churn, market change, Product regression, new Evidence or Intent change can trigger reassessment.

## AQ — Explicit Stop

Persistent `--autonomous` is explicitly stopped or cancelled.

Autonomous lifecycle ownership may end according to policy.

This is distinct from ordinary dormancy.

---

# 42. Success Criteria

A successful URACE bootstrap satisfies the following:

- Product Intent is durable and authoritative.
- Evidence is traceable.
- Trigger is lightweight and first-class.
- Meaningful Trigger is a qualification of Trigger.
- Raw events do not automatically create Product work.
- Trigger mechanisms remain replaceable.
- Open-ended discovery can complement known event sources.
- Objective and Plan remain distinct.
- Plans remain lightweight.
- Planner remains replaceable.
- Scheduler remains replaceable.
- Scheduling does not create Product justification.
- One capable AI can satisfy the minimum intelligent configuration.
- Executor replacement does not destroy lifecycle continuity.
- Executor unavailability does not terminate lifecycle ownership.
- Validation remains independent from executor confidence.
- Product Value remains Intent-relative and derived.
- Information Gain may influence prioritization.
- Time-to-Evidence may influence prioritization.
- Evidence quality is not sacrificed merely for speed.
- Opportunity cost may influence prioritization when time matters.
- Market fit remains contextual rather than universal.
- External Evidence outranks internal confidence when external behavior materially determines Product success and credible Evidence is proportionate to obtain.
- URACE may choose learning over building.
- URACE may choose building over learning when Evidence sufficiently supports it.
- URACE does not manufacture experiments or work merely to remain active.
- `--autonomous` supports both ACTIVE and DORMANT operation.
- Dormancy is not autonomous termination.
- `IDLE` is not autonomous termination.
- `WAITING_FOR_CAPACITY` is not autonomous termination.
- `WAITING_FOR_CONDITION` is not autonomous termination.
- `WAITING_FOR_SCHEDULE` is not autonomous termination.
- Runtime exit is distinct from lifecycle termination.
- Runtime resources may be released during dormancy only when durable reactivation responsibility exists.
- Persistence without wakeability is insufficient for persistent autonomous liveness.
- Scheduled, conditional, external and discovered Triggers can reactivate dormancy.
- Product readiness does not silently disable future reassessment.
- Active-loop convergence produces dormancy rather than ordinary end-loop.
- Autonomous lifecycle termination requires explicit stop/bound/policy semantics.

---

# 43. Defensible Boundary

URACE does not own executor intelligence.

It owns persistent lifecycle-control responsibility above replaceable intelligence.

URACE owns:

- Intent authority;
- durable lifecycle state;
- Evidence lineage;
- Trigger semantics;
- Trigger interpretation;
- lifecycle assessment;
- Objective justification;
- accepted Plan semantics;
- Product-value and uncertainty assessment;
- validation;
- acceptance;
- checkpoint/recovery semantics;
- autonomous dormancy;
- lifecycle liveness;
- open-ended change awareness;
- convergence.

URACE does NOT need to own a particular:

- model;
- executor;
- orchestrator;
- Planner;
- planning algorithm;
- Scheduler;
- scheduling implementation;
- Trigger detector;
- watcher;
- timer;
- queue;
- webhook;
- event bus;
- polling system;
- daemon;
- runtime;
- wake mechanism;
- discovery mechanism;
- experimentation methodology;
- market-fit methodology.

The defensible responsibility is:

> **Maintaining continuous, Intent-directed, Evidence-driven, Trigger-responsive, policy-governed, time-aware, uncertainty-aware, planned, validated, recoverable and autonomously resumable Product evolution independently of whichever intelligence, planning, scheduling, Trigger-delivery and execution systems happen to exist underneath it.**

---

# 44. Bootstrap Restraint

Before adding a new first-class concept, ask:

> **Does lifecycle correctness require this concept to have durable identity and independent lifecycle semantics?**

Before implementing more Product functionality, ask:

> **Is implementation currently the highest-value way to advance Intent, or would a smaller action produce more decision-relevant Evidence sooner?**

Before seeking more Evidence, ask:

> **Would this Evidence materially improve a lifecycle decision?**

Before scheduling work, ask:

> **Is the work already justified, or is the scheduled condition merely a reason to reassess?**

Before remaining active, ask:

> **Is useful work actually justified, or should URACE become dormant?**

Before terminating a runtime, ask:

> **Who or what now owns durable autonomous reactivation?**

If the answer is:

```text
none
```

the responsible persistent `--autonomous` runtime MUST remain efficiently dormant rather than end-loop.

Before terminating autonomous lifecycle ownership itself, ask:

> **Was autonomous operation explicitly stopped, cancelled, bounded, one-shot, or terminated by authoritative policy?**

If not:

```text
DORMANT
```

is the correct convergence state.

---

# 45. Final Canonical Principles

## Lifecycle Principle

> **URACE owns the persistent autonomous Product lifecycle; executors provide replaceable intelligence and execution.**

## Intent Principle

> **Product evolution is justified relative to durable Product Intent, not merely executor preference or available capability.**

## Evidence Principle

> **Material lifecycle decisions should remain attributable to credible Evidence and applicable Intent.**

## Trigger Principle

> **Trigger is a lightweight first-class lifecycle primitive representing a candidate reason for reassessment; a Trigger becomes Meaningful when it could materially alter the prior lifecycle assessment, and neither Trigger nor Meaningful Trigger automatically implies Product action.**

## Planning Principle

> **URACE owns the accepted relationship between a justified Objective and the strategy currently intended to advance it, while the mechanism that proposes that strategy remains replaceable.**

## Scheduling Principle

> **Time and conditions may determine when justified work becomes actionable or reassessment becomes worthwhile, but neither a clock nor a Scheduler determines Product justification.**

## Evidence-Velocity Principle

> **When material uncertainty constrains justified Product evolution, URACE SHOULD prefer the smallest safe action that produces sufficiently decision-relevant Evidence soonest, subject to Evidence quality, Intent, HARD constraints, cost, risk and opportunity cost.**

## External-Reality Principle

> **When Product value materially depends on external behavior, credible external Evidence SHOULD outrank executor prediction when obtaining that Evidence is proportionate and safe.**

## Time Principle

> **When a meaningful time window exists, URACE SHOULD consider time-to-Evidence and opportunity cost without allowing urgency to override HARD constraints, safety or required validation.**

## Market-Fit Principle

> **For Products whose Intent depends on market adoption, URACE SHOULD progress toward credible Evidence of fit, non-fit or the next highest-value uncertainty rather than treating internal Product completeness as a substitute for external validation.**

## Dormancy Principle

> **When no sufficiently justified action is currently available, URACE SHOULD become efficiently dormant rather than manufacture work. Dormancy remains part of autonomous operation.**

## Liveness Principle

> **Persistent autonomous lifecycle ownership requires both durable state and a viable path back to assessment when meaningful change occurs.**

## Runtime Principle

> **A dormant runtime MAY release resources only when equivalent durable reactivation responsibility remains available elsewhere; runtime termination does not itself terminate autonomous lifecycle ownership.**

## Convergence Principle

> **Active Product evolution converges to DORMANT when further action lacks sufficient justified value; persistent autonomous operation does not ordinarily converge to end-loop.**

## Goldilocks Principle

> **Make Intent, Evidence, Trigger, Objective and lightweight Plan first-class where independent semantics improve lifecycle correctness; keep Meaningful Trigger as a qualification of Trigger; keep Product Value and Information Gain derived; keep Market Fit contextual; keep Lifecycle Liveness, Autonomous Dormancy and Open-Ended Change Awareness invariant; and keep Planners, Schedulers, Trigger detectors, wake mechanisms, discovery mechanisms and executors replaceable.**

---

# 46. Final Bootstrap Instruction

Bootstrap the **smallest implementation** that satisfies this specification.

Do not turn URACE into:

- an executor;
- an orchestrator;
- an event-processing platform;
- a workflow engine;
- a scheduling framework;
- an experimentation framework;
- a market-fit framework;
- a heavyweight autonomous runtime.

The canonical active lifecycle is:

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
HIGHEST-VALUE JUSTIFIED
GAP OR UNCERTAINTY
  │
  ▼
OBJECTIVE
  │
  ▼
PLAN
  │
  ▼
EXECUTION / LEARNING
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
UPDATED EVIDENCE
  │
  └──────────────► ASSESS
```

The canonical dormant lifecycle is:

```text
NO JUSTIFIED ACTION NOW
          │
          ▼
        DORMANT
          │
          ▼
    PRESERVE LIVENESS
          │
   ┌──────┼──────────┬───────────┐
   │      │          │           │
EXTERNAL SCHEDULED CONDITIONAL BOUNDED
 CHANGE   WAKE      CHANGE      DISCOVERY
   │      │          │           │
   └──────┴──────────┴─────┬─────┘
                           ▼
                         TRIGGER
                           │
                           ▼
                     MEANINGFUL?
                       │       │
                      NO      YES
                       │       │
                       ▼       ▼
                    DORMANT  ASSESS
```

The canonical persistent-autonomy state machine is:

```text
             ┌─────────────┐
             │             │
             ▼             │
           ACTIVE          │
             │             │
             ▼             │
           ASSESS          │
             │             │
     ┌───────┴───────┐     │
     │               │     │
JUSTIFIED         NOTHING   │
 ACTION           JUSTIFIED │
     │               │     │
     ▼               ▼     │
   WORK           DORMANT   │
     │               │     │
     └───────────────┐│     │
                     ││     │
              MEANINGFUL    │
                TRIGGER     │
                     │      │
                     └──────┘
```

Therefore, under persistent `--autonomous`:

```text
ACTIVE → DORMANT
```

is normal.

```text
DORMANT → ACTIVE
```

occurs when meaningful change justifies reassessment and subsequent action.

```text
ACTIVE → NO WORK → END
```

is **not** normal autonomous convergence.

The physical process MAY disappear during dormancy if durable wake responsibility exists.

The autonomous lifecycle remains logically alive.

A Product that currently appears complete, ready or market-fit MAY become dormant.

It remains capable of reassessment when:

- Product state changes;
- Intent changes;
- new Evidence appears;
- customer/user behavior changes;
- market conditions change;
- dependencies change;
- risks change;
- capacity changes;
- scheduled conditions occur;
- bounded discovery finds material change;
- another Meaningful Trigger occurs.

Persistent autonomous lifecycle ownership ends only through explicit stop, cancellation, explicit bounded/one-shot semantics, authoritative termination policy, or another explicitly defined terminal Product/project contract.

The final invariant is:

> **URACE evolves the Product while sufficiently valuable justified action exists; learns when reducing material uncertainty has greater expected value than further implementation; becomes efficiently dormant when no such action is currently justified; and, while persistent autonomous operation remains enabled, preserves a viable path from dormancy back to assessment rather than silently ending the lifecycle.**