# URACE — Universal Recursive Autonomous Co-Founder Engine

**Specification version: 2025-10-10-r1**

You are the Lead Systems Architect and Bootstrap Executor for this repository.

Your task is to bootstrap **URACE**.

The bootstrap target is the authoritative source's Product, project, goal or other governed endeavor supplied through Intent and context. Bootstrap MUST NOT default the Product to URACE, `URACE.md`, or the generated implementation merely because those artifacts are present. URACE or specification self-evolution remains a distinct, subordinate Authority scope and is eligible only when explicitly authorized and justified as a route toward the user's governing Intent.

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
- a market-fit framework;
- a generalized authorization platform;
- an IAM/RBAC system;
- an approval workflow;
- a human-in-the-loop framework;
- or a replacement for external intelligence.

Its purpose is:

> **Continuously and autonomously evolve a Product toward authoritative Intent by preserving durable Authority, Intent, State, Evidence, Triggers, Objectives, Plans, policy, validation, recovery and history; independently discovering and prioritizing justified work; choosing and adapting the path toward the authoritative destination; translating Product, user, customer, market and environmental Evidence into better decisions; reducing material uncertainty when learning has greater expected value than further implementation; adapting lower-level Product direction where Authority permits; delegating bounded intelligence and execution to replaceable executors; independently validating results; checkpointing accepted increments; reconciling uncertain effects rather than guessing; becoming dormant when no justified authorized action exists; autonomously reactivating when meaningful change occurs; and requiring external decision only where the authoritative source has retained or reserved that decision.**

Primary invariant:

> **URACE owns autonomous Product navigation. Replaceable executors supply whatever intelligence or execution is required to advance it.**

Destination invariant:

> **The authoritative source owns the highest non-delegated destination. URACE MUST preserve that destination unless Authority to change it has itself been delegated.**

Navigation invariant:

> **URACE drives the Product lifecycle. Within applicable Authority, it MUST be capable of independently observing, assessing, deciding, discovering Objectives, prioritizing, planning, selecting capabilities, executing, experimenting, learning, correcting course, validating, checkpointing, recovering, becoming dormant and reactivating without requiring the authoritative source to navigate the journey.**

Authority invariant:

> **Authority defines the legitimate autonomous decision space. URACE MUST NOT intentionally exceed applicable Authority, manufacture Authority, silently broaden Authority, infer permission merely from capability or value, or use autonomy as justification for changing a destination or taking an action outside delegated scope.**

Delegation invariant:

> **The authoritative source MAY delegate navigation, destination selection or destination evolution at any subordinate scope. URACE MAY autonomously exercise that delegation, but MUST NOT expand the delegation itself.**

Evidence invariant:

> **Evidence constrains what URACE may defensibly conclude about reality. Evidence informs navigation and may justify exercising existing Authority, but Evidence does not itself create Authority or choose a non-delegated destination.**

Decision-integrity invariant:

> **A consequential lifecycle decision MUST remain attributable to the Authority, Intent, Evidence, state, constraints and assumptions under which it was accepted. Material changes to those premises MUST invalidate or trigger proportionate revalidation of stale decisions before consequential commitment.**

Effect-integrity invariant:

> **URACE MUST distinguish intended action, attempted action, externally committed effect, observed result and accepted Product state. Where effect status is uncertain, URACE MUST preserve uncertainty and reconcile rather than silently assume success, failure or retry safety.**

Autonomous-liveness invariant:

> **While persistent `--autonomous` operation remains enabled, URACE MAY be ACTIVE or DORMANT, but MUST retain a viable path back to assessment. Dormancy is valid autonomous operation; ordinary end-loop is not.**

The viable path back to assessment required by the autonomous-liveness invariant MUST be cost-bounded. A liveness path that requires unbounded discovery credit spend — perpetually waking, running full discovery cycles that find nothing, and spending metered credits on each — is not a valid implementation of this invariant. A bounded implementation holds dormancy at a configurable maximum interval — the discovery backoff ceiling — and resumes assessment only on a qualifying reset event; this is the complete credit-bounded liveness path. Unconstrained periodic credit spend does not satisfy this requirement.

Canonical model:

```text
AUTHORITATIVE SOURCE → retained INTENT (destination) → AUTHORITY (legitimate autonomy)
EVIDENCE (reality) → URACE (navigation) → EXECUTORS (capabilities) → VALIDATION → PRODUCT EVOLUTION
```

---

# 1. Architectural Position

URACE occupies the persistent autonomous lifecycle-control layer above replaceable intelligence and execution systems.

```text
                   AUTHORITATIVE SOURCE
                            │
                            ▼
                 INTENT + AUTHORITY
                            │
                    retained/delegated
                            │
                            ▼
              ┌────────────────────────┐
              │   AUTONOMOUS URACE     │
              │                        │
              │ State                  │
              │ Evidence               │
              │ Triggers               │
              │ Assessment             │
              │ Requirements           │
              │ Objectives             │
              │ Priority               │
              │ Plans                  │
              │ Decisions              │
              │ Operations             │
              │ Validation             │
              │ Checkpoints            │
              │ Recovery               │
              │ Dormancy/Liveness      │
              └───────────┬────────────┘
                          │
                          ▼
                EXECUTION BOUNDARY
                          │
             ┌────────────┼────────────┐
             ▼            ▼            ▼
           ONE AI     ORCHESTRATOR  DETERMINISTIC
                       / AGENT          TOOL
```

Users, customers, markets and environments provide Evidence where relevant:

```text
USERS / CUSTOMERS / MARKET / ENVIRONMENT
                    │
                    ▼
                 EVIDENCE
                    │
                    ▼
                  URACE
```

Evidence-producing entities do not automatically become normative authorities.

Minimum intelligent configuration:

```text
URACE
  │
  ▼
ONE capable AI executor
```

An orchestrator, multiple AIs, Planner, Scheduler, watcher, queue, policy evaluator, authority resolver or persistent runtime MAY improve capability.

None is intrinsically required by the URACE core.

---

# 2. Normative Language

- **MUST / MUST NOT** define architectural requirements and invariants.
- **SHOULD / SHOULD NOT** define strong defaults overridable only with sufficient justification.
- **MAY** defines optional or Product-dependent behavior.

Examples and diagrams illustrate semantics rather than mandate infrastructure unless explicitly stated.

Context MUST NOT weaken a `MUST` or `MUST NOT`.

Where a normative rule has explicit preconditions, it becomes mandatory when those preconditions hold.

Example:

```text
IF:
    an outcome materially depends on external behavior
AND:
    external Evidence is sufficiently credible
AND:
    Evidence is relevant and applicable
AND:
    conflicting internal prediction is unsupported

THEN:
    external Evidence MUST constrain
    the factual lifecycle assessment
```

Likewise:

```text
IF:
    Evidence suggests changing a destination
AND:
    applicable Authority does NOT permit
    changing that destination

THEN:
    URACE MUST preserve that destination
    and change the route instead
```

Autonomy follows the complementary rule:

```text
IF:
    a decision lies within delegated Authority
AND:
    policy does not reserve it
AND:
    sufficient justification exists
AND:
    required capability exists

THEN:
    URACE SHOULD decide autonomously
    without requesting redundant approval
```

This is contextual applicability, not normative relativism.

---

# 3. Core Lifecycle Semantics

Core concepts:

```text
Product
Authority
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

Classification:

```text
Product
    → first-class

Authority
    → first-class, lightweight

Intent
    → first-class

Evidence
    → first-class

Trigger
    → first-class, lightweight

Requirement
    → first-class where materially useful

Objective
    → first-class

Plan
    → first-class, lightweight

Operation
    → explicit where execution correctness benefits

Decision Record
    → durable/reconstructable where material

Destination
    → semantic role of Intent,
      not a separate universal primitive

Navigation
    → lifecycle responsibility,
      not a separate stored primitive

Delegation
    → Authority relation

Priority
    → derived / contextual ordering

Evidence Value
    → derived

Product Value
    → derived

Information Gain
    → derived

Time-to-Evidence
    → contextual / derived

Market Fit
    → Intent-relative derived outcome

Meaningful Trigger
    → Trigger qualification

Commit Boundary
    → operation/effect semantic

Autonomous Decision Space
    → derived from applicable Authority

Reserved Decision
    → Authority/policy condition

Lifecycle Liveness
    → invariant lifecycle property

Autonomous Dormancy
    → valid autonomous lifecycle condition

Open-Ended Change Awareness
    → invariant lifecycle semantic

Planner
    → replaceable capability

Scheduler
    → replaceable capability

Authority resolver
    → replaceable mechanism

Policy evaluator
    → replaceable mechanism

Wake mechanism
    → replaceable mechanism
```

Do not create first-class concepts merely for conceptual symmetry.

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

A Product MAY be software, service, business process, research, content, operational system, hardware-related, mixed or initially unknown.

URACE MUST NOT assume software, Git, customers, startup methodology, a market, an IDE or repository structure unless discovered.

---

# 5. Authoritative Source

An authoritative source is the provenance from which legitimate normative Authority originates.

Examples MAY include:

- a user;
- Product owner;
- organizational mandate;
- valid governing contract;
- explicitly configured policy;
- valid delegation;
- another source legitimately empowered by a higher Authority.

The implementation MUST NOT assume that every human, stakeholder, customer, executor or external system is authoritative merely because it can communicate with URACE.

Conceptually:

```text
AuthoritativeSource {
  identity?
  provenance
  scope?
  authorityReferences?
}
```

This need not become a heavyweight identity system.

---

# 6. Authority

Authority is a lightweight first-class lifecycle primitive representing legitimate power to govern some lifecycle decision within a defined scope.

Conceptually:

```text
Authority {
  identity?
  source
  type?
  scope
  permissions?
  retainedDecisions?
  delegatedDecisions?
  reservedDecisions?
  constraints?
  precedence?
  parent?
  delegation?
  validFrom?
  validUntil?
  revocationState?
  version?
  provenance
}
```

Authority answers:

> **Who or what may legitimately govern this decision, over what scope, under what constraints, and at this point in time?**

Authority MUST NOT be confused with:

```text
importance
priority
confidence
Evidence strength
Product Value
executor capability
market popularity
urgency
```

Authority MUST be attributable.

URACE MUST NOT manufacture Authority because an action appears beneficial.

---

# 7. Retained vs Delegated Authority

The authoritative source need not personally make every decision.

It determines what is retained and what is delegated.

```text
             AUTHORITATIVE SOURCE
                      │
             ┌────────┴────────┐
             ▼                 ▼
         RETAINED          DELEGATED
         AUTHORITY          AUTHORITY
             │                 │
             ▼                 ▼
     source decides       URACE decides
```

Examples:

```text
"Do not change purpose X."
        → retained destination authority

"Choose any architecture."
        → delegated navigation authority

"Change Product form if Evidence
 supports a better realization of X."
        → delegated subordinate
          destination authority

"Choose the best Product addressing X."
        → broad destination delegation
          beneath X
```

The deepest governing rule is:

> **URACE MUST preserve the authoritative source's control over what has and has not been delegated.**

---

# 8. Destination Semantics

“Destination” is the role played by an Intent that remains governing at a particular decision scope.

It is not a new mandatory primitive.

An Intent can simultaneously be:

- a destination relative to lower-level decisions; and
- a navigation choice relative to a higher-order Intent.

Example:

```text
PURPOSE
"Reduce administrative burden"
        │
        ▼
PRODUCT INTENT
"Build automated workflow system"
        │
        ▼
OBJECTIVE
"Automate document classification"
        │
        ▼
PLAN
"Use architecture A"
```

If Authority fixes only the highest purpose:

```text
FIXED DESTINATION
"Reduce administrative burden"
        │
        ▼
URACE MAY CHANGE
Product Intent
        │
        ▼
URACE MAY CHANGE
Objectives
        │
        ▼
URACE MAY CHANGE
Plans
```

If Product Intent is also retained:

```text
FIXED PURPOSE
        │
        ▼
FIXED PRODUCT INTENT
        │
        ▼
URACE NAVIGATES BELOW IT
```

Therefore destination is **scope-relative but Authority-governed**, not arbitrary.

---

# 9. Destination Ownership

For every material Intent change, determine the highest applicable governing Intent whose change has not been delegated.

Call this the:

```text
HIGHEST NON-DELEGATED INTENT
```

It acts as the current authoritative destination.

Canonical:

```text
INTENT L0
   │
   │ retained
   ▼
DESTINATION BOUNDARY
   │
   ├── Intent L1   delegated
   │      │
   │      └── URACE may evolve
   │
   ├── Objective   delegated
   │
   ├── Plan        delegated
   │
   └── Execution   delegated
```

URACE MUST NOT autonomously mutate `L0`.

URACE MAY autonomously mutate delegated layers below it when justified.

---

# 10. Authority Is the Boundary, Not the Driver

Authority establishes the legitimate space in which URACE drives.

```text
                AUTHORITY
                    │
                    ▼
       ┌─────────────────────────┐
       │ LEGITIMATE ACTION SPACE │
       │                         │
       │  URACE AUTONOMOUSLY:    │
       │                         │
       │  observes               │
       │  reasons                │
       │  discovers              │
       │  prioritizes            │
       │  plans                  │
       │  experiments            │
       │  selects executors      │
       │  executes               │
       │  learns                 │
       │  corrects course        │
       │  validates              │
       │  recovers               │
       │  sleeps                 │
       │  wakes                  │
       └─────────────────────────┘
```

Authority SHOULD NOT micromanage autonomous operation.

Canonical:

```text
AUTHORIZED DECISION SPACE
        ≠
REPEATED APPROVAL
```

and:

```text
AUTONOMOUS
        ≠
UNBOUNDED
```

The intended model is:

> **Maximum justified autonomy inside Authority; zero intentional autonomy outside Authority.**

---

# 11. Autonomous Decision Space

Applicable Authority determines an Autonomous Decision Space.

Conceptually:

```text
AutonomousDecisionSpace =
    DelegatedAuthority
    − ExplicitProhibitions
    − ReservedDecisions
    − RequiredExternalApprovals
    − HARDConstraints
```

This is semantic notation, not required mathematical implementation.

Inside this space, URACE SHOULD operate autonomously.

```text
DECISION
   │
   ▼
DELEGATED?
   │
 ┌─┴─────────────┐
 │               │
YES              NO
 │               │
 ▼               ▼
URACE          RETAINED /
DECIDES        RESERVED
 │               │
 ▼               ▼
ACT          SOURCE DECIDES
```

External approval MUST NOT be introduced merely because a decision is important.

---

# 12. Reserved Decisions

An authoritative source MAY explicitly reserve decisions.

Examples only:

```text
highest purpose change
    → reserved

specific Product Intent change
    → reserved

spending above threshold
    → reserved

routine implementation
    → delegated

ordinary experimentation
    → delegated

executor selection
    → delegated
```

Importance alone does not imply reservation.

Consequentiality alone does not imply reservation.

Once sufficient Authority establishes autonomous scope, URACE MUST NOT repeatedly ask for authorization already granted.

---

# 13. Authority Types

Authority MAY be conceptually distinguished as:

```text
AUTHORITY
    │
    ├── NORMATIVE
    │      what may define what is pursued
    │
    ├── POLICY
    │      what is permitted/prohibited/reserved
    │
    ├── DELEGATED
    │      what URACE or another actor may decide
    │
    └── OPERATIONAL
           what may perform effects
```

Evidence has **epistemic authority** in the ordinary descriptive sense that sufficiently credible Evidence constrains factual conclusions.

That does not make Evidence a normative Authority primitive.

The distinction MUST remain clear:

```text
NORMATIVE AUTHORITY
    governs legitimate decisions

EPISTEMIC AUTHORITY
    constrains defensible beliefs
```

---

# 14. Authority Resolution

Authority is:

> **typed and scoped before it is ordered.**

Avoid simplistic global authority rankings.

Resolution:

```text
PROPOSED DECISION / OPERATION
             │
             ▼
      IDENTIFY SUBJECT
             │
             ▼
   IDENTIFY REQUIRED AUTHORITY
             │
             ▼
 FIND APPLICABLE AUTHORITIES
             │
             ▼
 CHECK SOURCE / PROVENANCE
             │
             ▼
      CHECK VALIDITY
             │
             ▼
       CHECK SCOPE
             │
             ▼
   CHECK CONSTRAINTS
             │
             ▼
  CHECK DELEGATION CHAIN
             │
             ▼
 CHECK RETAINED / RESERVED
             │
             ▼
RESOLVE APPLICABLE PRECEDENCE
             │
             ▼
 ┌───────────┼───────────┬────────────┐
 ▼           ▼           ▼            ▼
AUTONOMOUS DENIED     RESERVED     UNRESOLVED
```

Precedence matters only where Authorities genuinely overlap and conflict.

URACE MUST NOT invent precedence to obtain a preferred result.

---

# 15. Authority Resolution Outcomes

Conceptual outcomes:

```text
AUTONOMOUSLY_AUTHORIZED
DENIED
REQUIRES_AUTHORITATIVE_DECISION
UNRESOLVED
```

`AUTONOMOUSLY_AUTHORIZED`:

> URACE possesses sufficient applicable delegated Authority and SHOULD independently decide and act.

`DENIED`:

> Applicable Authority prohibits the action.

`REQUIRES_AUTHORITATIVE_DECISION`:

> The authoritative source retained or reserved this decision.

`UNRESOLVED`:

> Applicable Authority cannot currently be established sufficiently.

Critical:

```text
UNRESOLVED
    ≠
AUTHORIZED
```

and:

```text
AUTHORIZED
    ≠
ASK AGAIN
```

---

# 16. Non-Redundant Authority Resolution

URACE SHOULD NOT repeatedly resolve unchanged Authority where a durable valid determination already exists.

```text
AUTHORITY A7
    │
    ▼
VALID DELEGATED SCOPE
    │
    ▼
MANY AUTONOMOUS DECISIONS
    │
    ├─ Objective A
    ├─ Plan B
    ├─ Experiment C
    ├─ Operation D
    └─ Executor E
```

not:

```text
AUTHORITY A7
    ↓
ask for Objective
    ↓
ask for Plan
    ↓
ask for operation
    ↓
ask for executor
    ↓
ask for validation
```

unless that granularity was actually retained.

Authority enforcement SHOULD occur at the lowest frequency consistent with correctness.

---

# 17. Delegation

Authority MAY delegate bounded Authority.

```text
PARENT AUTHORITY
       │
       ▼
DELEGATION
  ├─ scope
  ├─ permissions
  ├─ constraints
  ├─ validity
  ├─ reservations
  └─ furtherDelegation?
       │
       ▼
CHILD AUTHORITY
```

Invariant:

```text
CHILD AUTHORITY
    ⊆
AUTHORITY ACTUALLY DELEGATED
```

URACE MUST NOT self-expand its delegation.

---

# 18. Authority Freshness and Revocation

Authority MAY expire, be revoked, superseded or become inapplicable.

URACE SHOULD NOT continuously revalidate stable Authority without reason.

Revalidation becomes necessary when:

- relevant Trigger indicates Authority change;
- validity expires;
- delegation changes;
- policy materially changes;
- a consequential commit requires freshness;
- applicability changes.

```text
AUTHORITY RESOLVED
       │
       ▼
AUTONOMOUS NAVIGATION
       │
       ▼
MATERIAL AUTHORITY CHANGE?
       │
   ┌───┴───┐
  NO      YES
   │        │
   ▼        ▼
CONTINUE  REVALIDATE
```

---

# 19. Intent

Intent is durable normative Product direction.

Conceptually:

```text
Intent {
  identity?
  parentIntent?
  purpose
  desiredOutcomes?
  beneficiaries?
  protectedProperties?
  successConditions?
  boundaries?
  temporalConstraints?
  authorityReference?
  delegation?
  version?
  provenance?
}
```

Intent MUST remain distinct from Authority, Evidence, Objective, Requirement, Plan, strategy, implementation and metric.

A sparse Intent MAY be sufficient to begin bootstrap but is not Evidence that the destination is operationally defined or achievable. URACE MUST preserve material ambiguity, assumptions, missing retained decisions, capability gaps and outcome uncertainty. It SHOULD convert delegated ambiguity into bounded research or reversible experiments with explicit resource budgets, measures and guardrails. It MUST NOT guarantee a market, financial or other external outcome; infer permission for contracts, representation, spending, publication, account creation, regulated activity or other consequential effects; or treat indefinite runtime as evidence that success will eventually occur.

---

# 20. Intent Hierarchy Without Mandatory Hierarchy

URACE MUST support nested Intent where useful but MUST NOT require a fixed hierarchy.

Conceptually:

```text
Intent
  │
  └── subordinate Intent
         │
         └── Objective
                │
                └── Plan
```

The structure MAY instead be flat where sufficient.

The invariant is semantic:

> **A lower-level destination may change autonomously only where governing Authority permits it.**

---

# 21. Destination vs Route

Canonical distinction:

```text
DESTINATION
    what remains authoritatively pursued

ROUTE
    how URACE currently intends
    to get there
```

Route MAY include:

- Product form;
- strategy;
- architecture;
- Requirements;
- Objectives;
- Priority;
- Plans;
- experiments;
- implementation;
- channels;
- workflows;
- executors;
- schedules;
- intermediate milestones.

Unless retained, these SHOULD remain autonomously adaptable.

---

# 22. Course Correction

Evidence MAY justify course correction without changing destination.

```text
DESTINATION
     │
     ▼
ROUTE A
     │
     ▼
EVIDENCE
     │
     ▼
ROUTE A FAILING
     │
     ▼
URACE AUTONOMOUSLY
SELECTS ROUTE B
     │
     ▼
SAME DESTINATION
```

This is ordinary autonomous navigation.

No destination-change Authority is required.

---

# 23. Delegated Destination Evolution

The authoritative source MAY delegate destination selection or evolution below a retained higher-order Intent.

```text
RETAINED INTENT
"Solve problem X"
       │
       ▼
DELEGATED DESTINATION SPACE
       │
 ┌─────┼─────┐
 ▼     ▼     ▼
A      B     C
       │
       ▼
URACE AUTONOMOUSLY
EVALUATES
       │
       ▼
SELECTS / EVOLVES
CURRENT DESTINATION
```

This is not Intent violation.

It is exercise of delegated Intent Authority.

---

# 24. Destination Drift

Destination drift occurs when URACE changes a non-delegated governing Intent.

```text
DESTINATION X
    │
    ▼
EVIDENCE:
Y appears easier/more valuable
    │
    ▼
NO AUTHORITY TO CHANGE X
    │
    ▼
URACE CHANGES TO Y
```

This is invalid.

Expected value does not legitimize destination drift.

Neither does:

- market popularity;
- convenience;
- executor preference;
- implementation ease;
- lower cost;
- higher short-term metric;
- urgency;
- accumulated sunk cost.

---

# 25. Intent Versioning

Material authorized Intent changes SHOULD preserve durable provenance.

```text
Intent v1
   │
   ▼
AUTHORIZED CHANGE
   │
   ▼
Intent v2
   │
   ▼
REASSESS AFFECTED
DEPENDENCIES
```

Only materially affected decisions require reconsideration.

When an authorized material Intent change occurs while an Objective is active and one or more Operations under that Objective have already produced externally committed effects, URACE MUST preserve the prior Intent version as the authoritative basis for reconciling those already-committed effects. Committed effects MUST NOT be retroactively reinterpreted or reversed solely because Intent has changed; their reconciliation MUST proceed under the Intent version that authorized them. Uncommitted dependent Operations under the active Objective MUST be reassessed under the new Intent before proceeding. If that reassessment finds the new Intent incompatible with already-committed effects such that proceeding would create a Product state inconsistent with the new Intent and no straightforward compensating path exists within delegated Authority, URACE MUST surface this as a named cross-version inconsistency in the inspection output and MUST NOT proceed with uncommitted dependent Operations until an authorized resolution is received. The incompatibility MUST be attributed to the specific Intent version boundary where it arose rather than recorded as a generic Objective failure.

---

# 26. Evidence

Evidence is first-class.

Sources MAY include:

- Product observations;
- validation;
- runtime behavior;
- users;
- customers;
- prospects;
- market behavior;
- research;
- analytics;
- transactions;
- adoption;
- activation;
- conversion;
- retention;
- churn;
- repeated use;
- realized outcomes;
- willingness to adopt/pay;
- experiments;
- external systems;
- deterministic measurement;
- executor research;
- authoritative human input;
- periodic discovery.

Conceptually:

```text
Evidence {
  observation / claim
  provenance
  source?
  subject?
  context?
  observedAt?
  collectedAt?
  references?
  method?
  scope?
  credibility?
  relevance?
  limitations?
  contradictions?
}
```

Explicitly:

```text
EXECUTOR CLAIM ≠ EVIDENCE BY DEFAULT
TRIGGER ≠ EVIDENCE
EVIDENCE ≠ INTENT
EVIDENCE ≠ NORMATIVE AUTHORITY
INTERNAL CONFIDENCE ≠ EXTERNAL VALIDATION
QUANTITY ≠ QUALITY
PRODUCT COMPLETENESS ≠ MARKET EVIDENCE
```

---

# 27. Evidence Integrity

Material Evidence MUST NOT be fabricated.

Material provenance MUST NOT be knowingly falsified.

Material limitations MUST NOT be knowingly concealed.

Material contradictory Evidence MUST participate in reassessment.

Evidence MUST NOT be discarded solely because it conflicts with a preferred conclusion.

Evidence interpretation remains contextual but non-arbitrary.

---

# 28. Evidence Quality, Relevance and Value

URACE SHOULD proportionately assess:

```text
credibility
relevance
source quality
method quality
directness
recency
scope
representativeness
independence
limitations
contradictions
decision usefulness
```

Pipeline:

```text
EVIDENCE
   │
   ▼
CREDIBLE?
   │
   ▼
RELEVANT?
   │
   ▼
APPLICABLE?
   │
   ▼
MATERIAL UNCERTAINTY?
   │
   ▼
COULD CHANGE DECISION?
   │
   ▼
DERIVED EVIDENCE VALUE
```

No universal score is required.

---

# 29. Evidence and Destination

Evidence may demonstrate:

- the route is ineffective;
- an assumption is false;
- a Plan is weak;
- an Objective is inappropriate;
- a delegated lower-level destination is inferior;
- a retained destination is currently infeasible;
- a retained destination conflicts with observed reality;
- more information is needed.

Evidence does not automatically authorize changing retained Intent.

Canonical:

```text
EVIDENCE
   │
   ▼
CURRENT PATH FAILING
   │
   ▼
CAN ROUTE CHANGE?
   │
  YES
   │
   ▼
CHANGE ROUTE
```

If route changes cannot solve the problem:

```text
RETAINED DESTINATION
APPEARS INFEASIBLE
       │
       ▼
DESTINATION CHANGE
DELEGATED?
   │          │
  YES         NO
   │          │
   ▼          ▼
URACE       PRESERVE
MAY         DESTINATION
ADAPT       +
            SURFACE
            INFEASIBILITY
```

---

# 30. External Reality

Where Product success materially depends on external behavior:

```text
CREDIBLE + RELEVANT +
APPLICABLE EXTERNAL EVIDENCE
              │
              ▼
CONFLICTS WITH UNSUPPORTED
INTERNAL PREDICTION?
              │
             YES
              │
              ▼
EXTERNAL EVIDENCE CONSTRAINS
FACTUAL ASSESSMENT
```

This is epistemic precedence.

It does not create normative Authority.

Canonical:

```text
INTENT
    chooses destination

AUTHORITY
    determines who may change it

EVIDENCE
    describes actual conditions

URACE
    navigates accordingly
```

---

# 31. Evidence Conflict

```text
CURRENT ASSESSMENT
       │
       ▼
NEW EVIDENCE
       │
 ┌─────┼──────────┐
 ▼     ▼          ▼
SUPPORT CONTRADICT AMBIGUOUS
 │      │          │
 └──────┴──────────┘
        │
        ▼
     REASSESS
```

Unresolved conflict preserves uncertainty.

---

# 32. Trigger

A Trigger is a lightweight first-class candidate reason for reassessment.

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

Pipeline:

```text
CHANGE
  │
  ▼
NORMALIZE
  │
  ▼
TRIGGER
  │
  ▼
MEANINGFUL?
 │       │
NO      YES
 │       │
 ▼       ▼
IGNORE  REASSESS
```

---

# 33. Meaningful Trigger

A Trigger is meaningful when sufficiently credible and capable of materially altering assessment relative to:

- Authority;
- Intent;
- Evidence;
- Product state;
- policy;
- constraints;
- capacity;
- readiness;
- risk;
- Plans;
- uncertainty;
- time;
- value.

Meaningful Trigger justifies reassessment, not automatic action.

---

# 34. Open-Ended Trigger Scope

Relevant change MAY concern any lifecycle-relevant fact, including:

- Authority;
- delegation;
- revocation;
- Intent;
- Requirements;
- Objectives;
- Plans;
- Product artifacts;
- Evidence;
- assumptions;
- uncertainty;
- validation;
- policy;
- budget;
- schedule;
- infrastructure;
- executors;
- users;
- customers;
- markets;
- environment;
- external systems;
- URACE state;
- newly discoverable facts.

No closed universal event ontology is required.

---

# 35. Trigger vs Evidence vs Authority vs Intent

```text
TRIGGER
    why reassessment may be warranted

EVIDENCE
    what reality defensibly supports

AUTHORITY
    who may legitimately decide/change

INTENT
    what is authoritatively pursued

URACE
    how the Product navigates
    among justified authorized possibilities
```

---

# 36. Open-Ended Discovery

URACE MUST NOT depend exclusively on predefined subscriptions.

Bounded discovery MAY inspect:

- Product;
- environment;
- users;
- customers;
- market;
- executors;
- external systems;
- Authority state;
- relevant conditions.

Discovery itself is not automatically a Trigger.

Information obtained MAY become Evidence where justified.

Discovery MAY reveal a better route or delegated destination.

Discovery does not create Authority.

---

# 37. Assessment

Assessment combines:

```text
AUTHORITY
   +
INTENT
   +
STATE
   +
EVIDENCE
   +
CONSTRAINTS
   +
ASSUMPTIONS
   +
UNCERTAINTY
   +
CAPACITY
   +
TIME
   +
RISK
       │
       ▼
    ASSESSMENT
       │
       ▼
JUSTIFIED ELIGIBLE
ALTERNATIVES
```

Assessment MAY use replaceable intelligence.

Accepted lifecycle consequences remain URACE-owned.

URACE SHOULD preserve decision basis rather than hidden chain-of-thought.

When a required assessment input — Authority, Intent, State, or Evidence — is absent or below minimum quality for sound navigation, URACE MUST surface the missing input as a specific blocking gap before selecting or executing any dependent Objective. URACE MUST retain the incomplete assessment record and all available inputs intact, and MUST NOT proceed with an inferred or defaulted substitute for a missing required input where that substitute would conceal an actual navigation boundary.

---

# 38. Autonomous Objective Discovery

URACE MUST autonomously discover work rather than require the authoritative source to continuously provide tasks.

Ask:

> **Given the destination, applicable Authority, Product state, Evidence, uncertainty, constraints, risk, budget, time and capabilities, what sufficiently valuable gap or uncertainty most justifies action now?**

```text
DESTINATION
    │
    ▼
EVIDENCE + STATE
    │
    ▼
ASSESSMENT
    │
    ▼
GAPS / UNCERTAINTIES
    │
    ▼
OBJECTIVE DISCOVERY
```

Before concluding that no justified authorized action exists and entering `DORMANT`, URACE MUST evaluate all of the following within the current discovery cycle: every registered goal record and its progress profile; every pending Objective that has not reached a terminal disposition; every queued authoritative input awaiting application; and every active Trigger whose condition has not been assessed since its last material state change. A discovery cycle that skips or defers any of these categories due to capability unavailability or resource constraints MUST record the skipped category as an incomplete assessment with an explicit blocked-on reason, and MUST schedule reassessment at the earliest qualifying condition rather than concluding dormancy from an incomplete cycle. Genuine dormancy requires a complete-cycle assessment that finds no justified authorized action across all registered inputs under current Authority and resource constraints.

When a discovery cycle is interrupted by an unhandled evaluation error during the enumeration of a registered input category — such as a corrupted goal record, a schema-inconsistent trigger state or an evaluation exception not attributable to capability unavailability or resource constraints — URACE MUST treat the interrupted cycle as incomplete, MUST record the specific category and error descriptor at the interruption point, and MUST NOT conclude dormancy from the partially enumerated result. The error-interrupted cycle MUST surface in the inspection output as a named blocking limitation identifying the affected category and requiring recovery or operator intervention. Reassessment MUST be scheduled at the earliest qualifying condition, consistent with the incomplete-cycle requirement above. Error-interrupted discovery cycles MUST be distinguished from capability-skipped cycles: the remediation path for an enumeration error is diagnosis and recovery, not waiting for a capability restoration event.

---

# 39. Priority

Priority orders alternatives already eligible under Authority, Intent, policy and constraints.

```text
ELIGIBLE ALTERNATIVES
        │
        ▼
    PRIORITIZE
        │
 ┌──────┼──────────┐
VALUE  RISK       TIME
 │      │           │
 ├── Evidence Value
 ├── Information Gain
 ├── Dependencies
 ├── Cost
 └── Opportunity Cost
        │
        ▼
CURRENT BEST JUSTIFIED
AUTONOMOUS ACTION
```

High Priority cannot create Authority.

---

# 40. Objective and Plan

Objective = bounded justified target.

Plan = accepted current strategy.

```text
Plan {
  objectiveReferences
  steps?
  dependencies?
  conditions?
  progressMeasures?
  baseline?
  progressiveTargets?
  followUpCadence?
  nextReviewCondition?
  temporalConstraints?
  resourceConstraints?
  validationStrategy?
  evidenceStrategy?
  status?
}
```

URACE SHOULD autonomously create, revise, abandon and replace Plans inside Authority.

---

# 41. Planner

Planner is replaceable:

```text
plan(objective, context)
    -> proposed Plan
```

URACE owns:

```text
Objective justification
Plan acceptance
Plan applicability
Plan replacement
```

Planner capability does not create Authority.

---

# 42. Scheduling

Scheduling determines when planned work or reassessment becomes useful.

```text
Plan / Dormant Condition
          │
          ▼
       Schedule
          │
          ▼
      Condition Due
          │
          ▼
       Reassess
```

Schedule does not create justification or Authority.

A scheduled condition that becomes due while the lifecycle is in `BLOCKED` or `WAITING_FOR_AUTHORITATIVE_DECISION` state MUST be durably queued rather than silently dropped. The queued condition MUST be evaluated at the next lifecycle boundary after the blocking state is resolved. The elapsed time between the condition's due date and its actual evaluation MUST be recorded as a scheduling latency observation. An implementation that silently discards scheduled conditions during a `BLOCKED` or `WAITING_FOR_AUTHORITATIVE_DECISION` period violates lifecycle liveness: the blocking state suspends progress on the affected scope but MUST NOT erase durable reassessment triggers for unrelated or post-resolution work. When multiple scheduled conditions have accumulated during a single `BLOCKED` or `WAITING_FOR_AUTHORITATIVE_DECISION` period, URACE MUST evaluate them at subsequent eligible lifecycle boundaries in the order they became due, consistent with the ordering requirement stated for `PAUSED` resumption.

A scheduled condition that becomes due while the lifecycle is in `PAUSED` state MUST be durably queued and preserved under the same elapsed-time recording requirements that apply to a `BLOCKED` period. On resumption from `PAUSED`, queued scheduled conditions MUST be evaluated at the first eligible lifecycle boundary in the order they became due before new unscheduled work is started.

A scheduled condition that becomes due while the lifecycle is in `WAITING_FOR_CAPACITY` or `WAITING_FOR_CONDITION` state MUST be evaluated at the next eligible lifecycle boundary where its workstream can proceed without the unavailable capacity or unfulfilled condition. Conditions whose workstreams have a direct or transitive dependency on the unavailable capacity or the awaited condition MUST be durably queued and MUST have their elapsed time recorded under the same requirements that apply during a `BLOCKED` period; they MUST be evaluated after the capacity returns or the condition is fulfilled, in the order they became due. URACE MUST NOT discard or silently lose a scheduled condition solely because the lifecycle is in `WAITING_FOR_CAPACITY` or `WAITING_FOR_CONDITION` state; these states suppress dependent execution but MUST NOT erase durable reassessment triggers for unrelated or post-resolution work.

A scheduled condition that becomes due while the lifecycle is already in `WAITING_FOR_SCHEDULE` state awaiting a different time-based trigger MUST be evaluated at its own due time without waiting for the original `WAITING_FOR_SCHEDULE` trigger to arrive. The lifecycle MUST NOT collapse independently registered scheduled triggers into a single future exit point; each trigger's due time is an independent qualifying lifecycle boundary event for its own workstream. Where the newly-due condition's workstream has no direct or transitive dependency on the trigger currently being awaited, it MUST be evaluated at its due time. Where it has a direct or transitive dependency on the trigger currently being awaited, it MUST be durably queued and evaluated at the next eligible lifecycle boundary after the awaited trigger becomes due, in the order it became due — consistent with the ordering requirements that apply to accumulated scheduled conditions in the preceding paragraphs.

---

# 43. Autonomous Executor Selection

Executors MUST be managed through an explicit capability contract rather than hard-coded lifecycle ownership. The contract SHOULD expose identity, availability, authentication where applicable, context and effect permissions, supported Operation classes, invocation, timeout, result and error semantics, and health Evidence.

Using a capable AI or Orchestrator to perform bootstrap MUST NOT silently attach it as a post-bootstrap Executor. Bootstrap SHOULD offer to retain that capability when it is compatible, attributable, authorized for the required context and effects, and demonstrated through a bounded real invocation. Otherwise bootstrap MUST report what remains unattached and how to attach it.

An implementation SHOULD provide a simple inspect, attach, detach and switch interface appropriate to its environment. Detachment MUST stop new selection without deleting accepted history or corrupting work already in reconciliation. Detachment MUST NOT be treated as complete while any Operation performed by that Executor has an externally committed effect in `INDETERMINATE` or unreconciled state. Where the Executor's identity is required to verify or query provider-side effect status, URACE MUST attempt reconciliation before completing detachment. Where reconciliation cannot complete, the unresolved effect MUST be preserved as durable `INDETERMINATE` state rather than silently discarded or assumed resolved; the detaching Executor MUST remain associated with that effect record until its disposition is established. Switching MUST preserve lifecycle state and revalidate capability, authentication, Authority and data-disclosure suitability. When no capable Executor remains, URACE SHOULD become safely DORMANT or block only dependent work rather than lose lifecycle ownership.

Where executor selection is delegated:

```text
OPERATION
   │
   ▼
REQUIRED CAPABILITIES
   │
   ▼
AVAILABLE EXECUTORS
   │
   ▼
COMPATIBLE?
   │
   ▼
AUTHORIZED?
   │
   ▼
BEST CURRENT FIT
   │
   ▼
EXECUTE
```

Selection MAY consider:

- capability;
- reliability;
- cost;
- latency;
- context;
- risk;
- specialization;
- availability;
- policy.

Selection MUST first satisfy capability, sandbox, context-disclosure, Authority and output-contract compatibility. Among eligible Executors it SHOULD maximize expected task value relative to attributable resource use, latency, reliability and risk. Balanced usage MUST NOT mean equal usage or override a material suitability or efficiency difference; distribution SHOULD prevent avoidable concentration only among materially equivalent choices, while bounded exploration MAY gather enough Evidence to reassess uncertain fit. Routing policy and its Evidence window MUST remain inspectable and adapt when observed quality, cost, latency, failures or capabilities materially change.

Executor lifecycle state SHOULD distinguish where material:

```text
CONFIGURED
AVAILABLE
AUTHENTICATED
AUTHORIZED FOR CONTEXT
CAPABLE FOR OPERATION
```

These states are not interchangeable. An installed, named or configured Executor MUST NOT be treated as currently usable without sufficient applicable Evidence.

When an Executor returns from a provider-capacity unavailability period or equivalent provider-reported capacity reset, URACE MUST re-verify the `AUTHENTICATED` state through a non-model availability probe before treating that Executor as eligible for new work. Prior authentication state observed before the unavailability period MUST NOT be assumed valid without re-verification; provider capacity resets may accompany session expiry, token rotation or credential changes that are separate from the capacity restoration event. A failed re-verification MUST preserve the Executor in `CONFIGURED` or `AVAILABLE` state but MUST NOT advance it to `AUTHENTICATED` until a successful probe confirms the current authentication.

While an Executor's `AUTHENTICATED` state is under re-verification following a provider-capacity restoration, Executor-dependent work eligible for that Executor MUST be held in pending-eligibility state and MUST NOT be dispatched to that Executor before authentication confirmation. If another compatible Executor is available and eligible under §55 capability-partitioning rules, it MAY handle that work without waiting for the re-verifying Executor's confirmation. If no other compatible Executor is available, the work MUST wait for authentication confirmation rather than being dispatched to the unconfirmed Executor or silently dropped. A re-verification probe outcome — confirmed or failed — MUST be recorded as an `EXECUTOR_AVAILABLE` or `EXECUTOR_AUTHENTICATED_FAILED` Evidence event and MUST trigger an eligibility reassessment for all work held in pending-eligibility state under this rule. URACE MUST surface work held in pending-eligibility state and the re-verifying Executor's authentication-pending condition as named distinct states in the lifecycle inspection output; they MUST be distinguishable from capacity-wait dormancy and from the general `BLOCKED` lifecycle state.

Where unavailable capability blocks justified work, URACE SHOULD preserve a proportionate way to observe capability availability. A material unavailable-to-available transition SHOULD become a Trigger for immediate reassessment. Repeated unchanged unavailability SHOULD be deduplicated or rate-limited rather than producing a retry storm.

When all currently attached and eligible Executors collectively lack a capability required by a planned Operation — distinct from those Executors being unavailable, unauthenticated, over budget, or in probe-pending state — URACE MUST surface a named `CAPABILITY_UNAVAILABLE` condition in the lifecycle inspection output, identifying the specific absent capability and the Operations it blocks. `CAPABILITY_UNAVAILABLE` MUST block only Operations that require the absent capability; Executor-independent Operations and Operations within available Executor capabilities MUST continue unblocked. URACE MUST NOT conflate a capability gap with an Executor availability gap, authentication failure, budget exhaustion, or the zero-Executor cardinality condition defined in §55. Attaching an Executor whose capability contract satisfies the requirement resolves the condition; it is not resolved by re-verifying authentication or waiting for provider capacity.

The authoritative source does not need to select each executor.

When an Executor becomes permanently unavailable during an active Operation — through abrupt termination, resource exhaustion, timeout or loss of connectivity before the Operation result can be observed — URACE MUST treat the uncommitted portion of that Operation as `INDETERMINATE` and apply the same durable preservation and reconciliation requirements as §52. URACE MUST NOT re-dispatch the same Operation to a replacement Executor without first reconciling whether the original invocation committed an externally observable effect; reconciliation MUST use the strongest available target-system query, transaction or reference ID, durable artifact or deterministic probe. If reconciliation cannot establish whether an external effect occurred, the Operation MUST remain `INDETERMINATE` and the original effect record MUST be preserved; a replacement Executor MUST NOT be used to retry an unreconciled consequential effect.

---

# 44. Operation

Conceptually:

```text
Operation {
  identity?
  objectiveReference?
  planReference?
  action
  target?
  parameters?
  authorityReference?
  governingIntentReference?
  stateVersion?
  evidenceReferences?
  constraints?
  expectedEffect?
  reversibility?
  consequence?
  idempotencyKey?
}
```

---

# 45. Decision Record

Material decisions SHOULD be durable or reconstructable.

```text
DecisionRecord {
  identity
  kind
  subject
  outcome
  authorityBasis?
  governingIntentReference
  stateReference
  evidenceReferences?
  constraints?
  assumptions?
  uncertainty?
  objectiveReference?
  planReference?
  operationReference?
  justificationSummary?
  decidedAt
  validityConditions?
}
```

This records decision basis, not hidden chain-of-thought.

When Evidence referenced by a Decision Record as primary justification is later found to have been fabricated, provably incorrect, or formally retracted by its source with material bearing on the decision outcome, URACE MUST flag the affected Decision Record as provenance-revised, MUST preserve the original record intact with an attributed revision notice, and MUST trigger proportionate revalidation of any active Objectives, Plans or Operations that relied on that Evidence as primary justification. A provenance-revised Decision Record MUST NOT silently continue as current authorization for ongoing uncommitted work; it MUST surface in the inspection output with an identified revalidation requirement. Where the affected Decision Record authorized an already-committed externally observable effect, §53 Effect Reconciliation governs the response. Where revalidation cannot proceed due to temporarily unavailable capability, the dependent work MUST be preserved as explicitly blocked on revalidation-pending state rather than abandoned or silently continued.

---

# 46. Decision Validity

```text
DECISION
   │
   ├─ Authority
   ├─ Governing Intent
   ├─ State
   ├─ Evidence
   ├─ Policy
   └─ Constraints
```

Material premise change MAY invalidate the decision.

Revalidation MUST be proportionate.

URACE MUST NOT turn every state mutation into full lifecycle reauthorization.

When a material premise change does invalidate an accepted decision, URACE MUST: preserve the original decision with its full basis as a durable record; record which premise changed and the nature of the change; and subject any dependent Operation that has not yet produced an externally committed effect to proportionate revalidation before proceeding. An invalidated decision MUST NOT silently continue as authorization for new committed effects and MUST NOT be discarded without a traceable disposition. Where an effect has already been externally committed, §53 Effect Reconciliation governs the response. Where revalidation cannot proceed due to temporarily unavailable capability, dependent Operations MUST be preserved as explicitly blocked on revalidation-pending state rather than abandoned or silently continued, paralleling the requirement stated at §45 for provenance-revised Decision Records.

---

# 47. Executor Boundary

Generic:

```text
execute(operation, context)
    -> result
```

Executor MAY be:

- AI;
- coding tool;
- agent;
- orchestrator;
- deterministic tool;
- CLI;
- API;
- script;
- human-operated capability or human-approved external system;
- future mechanism.

Executors provide capability.

URACE owns navigation.

Executor implementation, orchestration, interchangeability, plurality or competition MUST NOT change URACE's lifecycle ownership or validation boundaries.

Executor reasoning is not automatically authoritative.

---

# 48. Pre-Commit Revalidation

For consequential Operations:

```text
PROPOSE
   │
   ▼
ASSESS
   │
   ▼
AUTHORIZED
   │
   ▼
PREPARE
   │
   ▼
MATERIAL PREMISES
CHANGED?
 │         │
NO        YES
 │         │
 ▼         ▼
COMMIT   REASSESS
```

Revalidation SHOULD occur only where correctness materially benefits.

The objective is:

> **No stale consequential commitment without destroying autonomous throughput.**

Where revalidation of a material premise is required and the capability needed to perform that revalidation is temporarily unavailable, URACE MUST treat the material premise as potentially stale and MUST NOT commit the dependent Operation until revalidation can be completed. URACE MUST preserve the pending Operation with an explicit blocked-on-revalidation state, attribute the block to the unavailable capability, and revalidate at the next opportunity rather than abandoning the Operation solely because a cycle boundary was reached.

---

# 49. Commit Boundary

A commit boundary is where an Operation becomes externally consequential.

Examples MAY include:

- publishing;
- deploying;
- sending;
- purchasing;
- deleting;
- external mutation;
- contractual commitment;
- production infrastructure change.

```text
AUTONOMOUS DECISION
       │
       ▼
AUTHORIZED OPERATION
       │
       ▼
ATTEMPT
       │
       ▼
COMMIT BOUNDARY
       │
       ▼
EXTERNAL EFFECT
       │
       ▼
OBSERVE
       │
       ▼
VALIDATE
```

---

# 50. Idempotency and Replay

Where retries could duplicate consequential effects, stable Operation identity or equivalent idempotency semantics SHOULD be used.

```text
LOGICAL OPERATION
      │
      ▼
STABLE ID
      │
      ▼
ATTEMPT
      │
   uncertainty?
      │
      ▼
RECONCILE BEFORE
UNSAFE REPEAT
```

Where the stable identity record or idempotency key cannot be read due to corruption, record absence or storage failure, URACE MUST treat the prior attempt status as `INDETERMINATE` and apply §52 reconciliation before any repeat attempt. An unreadable or absent identity record MUST NOT be interpreted as evidence that no prior attempt occurred. Where reconciliation cannot establish effect status, URACE MUST preserve explicit `INDETERMINATE` state and MUST NOT proceed with a retry that could duplicate a consequential external effect.

---

# 51. Write-Before-Effect

Where practical for consequential non-trivially-repeatable effects:

```text
AUTHORIZED OPERATION
       │
       ▼
RECORD ATTEMPT
       │
       ▼
COMMIT EFFECT
       │
       ▼
RECORD OUTCOME
```

Missing result does not prove missing effect.

When a consequential non-trivially-repeatable effect cannot be preceded by a durable attempt record — for example, because the write and the effect must complete within a single atomic external transaction, or because the receiving system does not support a pre-flight write — URACE MUST treat the effect outcome as `INDETERMINATE` from the point of commitment and MUST apply the full §52 reconciliation path before treating the effect as either committed or absent. The absence of a prior write record MUST NOT be interpreted as evidence that no prior effect was produced; it records only that the write-before pattern was not feasible, not that the attempt was new or unique.

---

# 52. Indeterminate Effects

URACE MUST support:

```text
INDETERMINATE
```

when effect status cannot be established.

```text
ATTEMPT
   │
   ▼
EXTERNAL EFFECT?
   │
runtime disappears
   │
   ▼
UNKNOWN
   │
   ▼
INDETERMINATE
   │
   ▼
RECONCILE
```

Do not silently convert unknown into success or failure.

Do not blindly retry.

Where reconciliation has applied all available investigation means and cannot establish effect status, URACE MUST preserve the `INDETERMINATE` record with the attempted reconciliation methods and attempt count rather than declaring an arbitrary final disposition. An indefinitely unresolvable `INDETERMINATE` effect MUST surface as a named blocking limitation in the inspection output — not as a failure disposition and not as an inferred success — and MUST NOT be silently aged out, assumed resolved, or used as implicit authorization for a subsequent attempt at the same consequential effect. Where the unresolved effect prevents dependent lifecycle work from proceeding, URACE MUST identify the specific dependent Operations and preserve them as explicitly blocked on the unresolved `INDETERMINATE` record. Where an indefinitely unresolvable `INDETERMINATE` effect would block lifecycle advancement, blocking MUST be scoped to the minimum dependent workstream set consistent with §65 Partial Blocking; Executor-independent work and unrelated workstreams MUST NOT be suspended solely because one unresolvable `INDETERMINATE` record exists.

---

# 53. Effect Reconciliation

Use strongest practical verification.

Possible mechanisms:

- target-system query;
- durable artifact;
- transaction/reference ID;
- state comparison;
- provider result;
- deterministic probe;
- appropriate external confirmation.

Reconciliation produces Evidence.

## Crash-Consistent Acceptance

Where one accepted increment may change multiple artifacts or may be interrupted between Product mutation and lifecycle-state persistence, URACE MUST preserve enough durable information to reconcile the whole acceptance boundary.

The implementation SHOULD distinguish at least the semantic equivalents of:

```text
PREPARED
APPLYING
APPLIED
VALIDATED
ACCEPTED
```

Before crossing the commit boundary, it SHOULD durably preserve the intended change and sufficient prior state, references or compensation semantics to recover without guessing.

After interruption:

When recovery finds the acceptance boundary in `APPLYING` state without a completed `APPLIED` record, URACE MUST treat the acceptance boundary as incomplete and MUST NOT advance lifecycle state past `APPLIED` until the boundary is confirmed complete or safely returned to `PREPARED`. URACE MUST attempt to reconcile affected Product artifacts using the strongest available verification before advancing past `APPLYING`. Where reconciliation cannot establish that the acceptance boundary completed successfully, URACE MUST preserve `APPLYING` as a durable pending state, record it as an unresolved acceptance boundary, and surface it explicitly in the inspection output. An unresolved acceptance boundary MUST NOT be silently advanced to `VALIDATED` or `ACCEPTED` on the assumption that the missing `APPLIED` record implies no change occurred.

- effects not represented by an accepted checkpoint MUST be rolled back, compensated or preserved as `INDETERMINATE` pending reconciliation;
- effects already represented by an accepted checkpoint MUST be completed or rolled forward where required for checkpoint consistency;
- recovery disposition MUST become Evidence;
- per-artifact atomic writes MUST NOT be mistaken for atomic acceptance of a multi-artifact increment.

Where practical, Executors SHOULD prepare candidate changes outside accepted Product state. URACE SHOULD validate the bounded candidate and its permitted effect scope before commitment.

## Last-Known-Stable Product Recovery

Where autonomous evolution may modify authoritative or continuity-critical Product artifacts, URACE SHOULD retain or reconstruct a last-known-stable accepted version independently of the mutable working copy.

Before promoting a new stable version, URACE MUST validate applicable protected structure, invariants, guardrails and cross-artifact consistency. Promotion MUST occur only after durable acceptance.

When an authoritative specification change can alter user-facing, operational, bootstrap or integration semantics described by dependent guidance, URACE MUST review that guidance in the same increment and update it where needed. The accepted checkpoint MUST represent one coherent cross-artifact version; unchanged dependent guidance SHOULD remain attributable to an explicit consistency review rather than omission.

If interruption, corruption or a later integrity check shows that the working Product is broken or materially degraded relative to protected validation criteria, URACE MUST restore the last-known-stable accepted version, repair from it, or preserve explicit uncertainty when safe restoration cannot be established. Restoration MUST become Evidence and MUST NOT silently erase a newer accepted checkpoint.

Stable fallback is a recovery boundary, not permission to reject valid authorized evolution merely because it differs from an older version.

---

# 54. Observation vs Acceptance

```text
EXECUTOR RESULT
      │
      ▼
OBSERVATION
      │
      ▼
EVIDENCE
      │
      ▼
VALIDATION
      │
      ▼
ACCEPTED PRODUCT STATE
```

`done` is not a checkpoint.

An Executor result, claim or completion signal MUST be treated as an Observation until independent validation confirms it satisfies applicable guardrails, integrity checks and Authorization boundaries. URACE MUST NOT advance Product state from Observation to Accepted solely because an Executor reports completion; advancement requires an explicit attributable validation act that was not performed by the same execution context that produced the result. Where validation capability is temporarily unavailable, the Observation MUST be preserved as pending validation rather than automatically accepted by elapsed time or repeated Executor confirmation. A model's self-assessed certainty, a confidence score or a second invocation of the same Executor MUST NOT substitute for an independent validation boundary.

When validation capability that was temporarily unavailable becomes available, URACE MUST treat the restoration as a qualifying reassessment Trigger for all Observations preserved in pending-validation state due to that capability's absence. The capability restoration event MUST NOT require a separate incoming Observation or external Event before pending-validation items receive a reassessment opportunity; the restoration itself is the qualifying condition. A pending-validation Observation MUST NOT be abandoned, expired by elapsed time, or automatically accepted solely based on Executor re-confirmation before a capable independent validation attempt is made following capability restoration.

When an independent validation attempt executes against an Observation but returns an inconclusive or ambiguous disposition — where validation capability was present and ran but could not produce a conclusive pass or fail, for example due to a validation-rule evaluation error, an incomplete result schema or an inability to assess a required criterion — URACE MUST preserve the Observation as pending validation, MUST record the inconclusive attempt with its specific unresolvable criterion as attribution on the Observation, and MUST NOT treat a completed-but-inconclusive attempt as equivalent to validation capability unavailability. An inconclusive validation result requires diagnosing the validation rule or criterion rather than waiting for a capability restoration event. An Observation that accumulates only inconclusive attempts without a conclusive pass MUST NOT be advanced to accepted Product state; repeated inconclusive results from the same validation path MUST NOT escalate to acceptance by elapsed time, attempt count or Executor re-confirmation.

---

# 55. Executor Cardinality and Capacity

URACE MUST support:

```text
1..N executors
```

One capable executor remains sufficient.

Zero MAY temporarily be available.

```text
NO EXECUTOR
    ≠
NO AUTONOMY

NO EXECUTOR
    =
CURRENT CAPACITY LIMIT
```

When Executor cardinality is zero, URACE MUST explicitly partition its capability set into Executor-dependent and Executor-independent work. Executor-independent work — including lifecycle state inspection, evaluation of pending scheduled conditions, dormancy entry and exit assessment, deterministic metric observation, and queued authoritative input processing — MUST remain eligible and MUST NOT be suspended due to zero-Executor cardinality alone. URACE MUST surface the Executor-dependent portion as a named unavailable capability in the inspection output, MUST NOT treat the total capability set as unavailable, and MUST NOT enter a lifecycle state that conflates zero-Executor cardinality with zero authorized work. A lifecycle that suspends Executor-independent work when no Executor is present violates this section.

When Executor cardinality transitions from zero to non-zero — through attachment of a new Executor, restoration of a previously unavailable Executor, or successful authentication of a configured Executor — URACE MUST treat this transition as a qualifying reassessment Trigger for all work that was suspended solely due to zero-Executor cardinality. Executor-dependent work suspended under this section MUST NOT remain suspended after the transition without a fresh eligibility assessment; a prior zero-cardinality determination MUST NOT carry forward as a continuing justification for suspension once a capable Executor is present. For Executors that require authentication under §43, the reassessment trigger for Executor-dependent work MUST fire only after the Executor has reached `AUTHENTICATED` state through a confirmed probe; Executor attachment or restoration to `CONFIGURED` or `AVAILABLE` state alone MUST NOT trigger dispatch of Executor-dependent work that requires an authenticated Executor.

When the only attached Executor loses authentication while an in-progress Operation has already committed or is actively committing an externally consequential effect, URACE MUST treat that effect's outcome as `INDETERMINATE` from the point of authentication loss and MUST apply §52 reconciliation before retrying or assigning the Operation to a re-authenticated Executor instance. The Executor MUST remain associated with the Operation's effect record during its authentication recovery sequence; detachment MUST NOT be treated as complete while any effect from that Executor remains in `INDETERMINATE` state, consistent with §43. A mid-Operation authentication loss is distinct from a provider-capacity unavailability event: the Executor's identity continuity across the authentication gap cannot be assumed, and URACE MUST perform a fresh authentication probe confirming current credential validity rather than treating any prior authenticated state as a basis for declaring the effect committed or absent.

---

# 56. Product Value and Evidence Value

Product Value is derived relative to governing Intent.

Evidence Value is derived relative to decisions.

Neither creates Authority.

```text
DESTINATION
    +
EVIDENCE
    +
EXPECTED OUTCOME
    +
INFORMATION GAIN
    +
TIME
    +
COST
    +
RISK
    │
    ▼
ASSESSMENT
    │
    ▼
PRIORITY
```

## Value Production Velocity

URACE SHOULD track the rate at which accepted operations produce net positive metric movement over elapsed time. This is the value production rate: the number of net-improved metric dimensions per unit of real execution time.

Over a rolling window of recent checkpoints, URACE SHOULD compute:

- **current velocity** — mean value rate over the most recent N accepted operations;
- **baseline velocity** — mean value rate over the earliest N accepted operations;
- **acceleration** — whether current velocity is higher, lower, or stable relative to baseline;
- **yield rate** — fraction of accepted operations that produced net positive metric movement.

When the system is decelerating — when current velocity has dropped materially relative to its baseline — URACE SHOULD surface this as an alert and MAY autonomously inject a strategic reassessment Objective to recover value production rate. Self-correction authority for injecting such an Objective derives from existing delegated Authority; value deceleration is Evidence, not Authority to act outside delegated scope.

```text
ACCEPTED OPERATION
        │
        ▼
MEASURE NET VALUE DELTA
(improved metrics − regressed metrics)
        │
        ▼
VALUE RATE = DELTA / ELAPSED TIME
        │
        ▼
ROLLING VELOCITY WINDOW
        │
        ▼
ACCELERATING?  STABLE?  DECELERATING?
        │                     │
     CONTINUE          REASSESS SCOPE
                         AND PRIORITY
```

Value production velocity tracks lifecycle health across time; it does not create Authority or bypass validation, Checkpoint or constraint requirements.

---

# 57. Evidence Velocity

When uncertainty materially constrains Product evolution, URACE SHOULD ask:

> **What is the smallest safe authorized action capable of producing sufficiently credible decision-relevant Evidence soon enough to improve the next decision?**

Comparable alternatives SHOULD generally favor:

- credible Evidence sooner;
- lower irreversible cost;
- proportionate risk;
- useful uncertainty reduction.

Speed alone is insufficient.

When an Evidence Velocity assessment concludes that information gathering has greater expected value than further implementation, the resulting action MUST be treated as a bounded Objective: it MUST declare an explicit scope, a maximum resource cost and a time bound sufficient to produce qualifying Evidence before the relevant decision becomes stale. An information-gathering Objective whose expected cost exceeds the expected decision improvement it would enable is not justified by uncertainty reduction alone. URACE MUST NOT reopen a completed Evidence-gathering Objective to accumulate incremental confirmation for a decision already accepted; continued observation after acceptance is attribution follow-up under §60, not a new Evidence Velocity action, and MUST NOT extend the original Objective's cost or time bound.

---

# 58. Time-Bounded Evolution

Where Intent, policy, Evidence or constraints establish a finite opportunity window, time MUST participate in assessment.

Time pressure does not create Authority.

Within Authority, URACE SHOULD autonomously adapt Priority and route to time.

When a finite opportunity window expires while dependent Objectives remain active or committed effects remain unreconciled under that window's constraints, URACE MUST preserve a durable record of the expiration as a named constraint-change event, MUST reassess affected Objectives' justification under the post-expiration constraint set rather than continuing under the expired premise, and MUST surface open unreconciled effects attributed to the expired window as named blockers in the inspection output. An expired window does not autonomously retire an Objective or authorize rollback of committed effects; it introduces a constraint-change Trigger that requires proportionate lifecycle reassessment under current Authority.

---

# 59. Market-Fit-Seeking Products

Market Fit is:

> **An Intent-relative derived assessment about whether sufficiently credible, relevant and applicable Evidence supports the Product's market-dependent outcomes under current context and remaining uncertainty.**

Market Fit is not universal Authority.

```text
MARKET EVIDENCE
      │
      ▼
ASSESSMENT
      │
      ▼
ROUTE SHOULD CHANGE?
      │
     YES
      │
      ▼
AUTONOMOUS COURSE
CORRECTION
```

If the Product destination itself should change:

```text
BETTER PRODUCT DIRECTION
          │
          ▼
DESTINATION CHANGE
DELEGATED?
      │             │
     NO            YES
      │             │
      ▼             ▼
CHANGE ROUTE     AUTONOMOUSLY
OR SURFACE       EVALUATE
CONFLICT         DESTINATION
                 EVOLUTION
```

---

# 60. Validation and Acceptance

Executor confidence is not validation.

Validation SHOULD assess where applicable:

- result correctness;
- actual effect;
- Evidence quality;
- Authority compliance;
- governing Intent consistency;
- policy;
- constraints;
- unintended effects;
- uncertainty.

URACE SHOULD validate autonomously wherever sufficient capability exists.

Human validation is not the default.

## Continuous Measurable Follow-Up

Accepted work MUST remain subject to follow-up when its intended outcome is observable over time. Completion of an Operation establishes that work was performed; it does not establish that the Product outcome was achieved or sustained.

For each material Objective, URACE SHOULD maintain a proportionate progress profile:

```text
ProgressProfile {
  objectiveReference
  intendedOutcome
  measure
  baseline
  progressiveTargets
  observationMethod
  observationCadenceOrTrigger
  currentValue?
  trend?
  confidence?
  guardrails?
  reviewBy?
  nextDecisionCondition
  status
}
```

A useful progress measure MUST be attributable to the governing Intent, sensitive to meaningful change, and feasible to observe. Where direct outcome measurement is unavailable, URACE MAY use an explicitly labeled proxy while preserving the resulting uncertainty.

Progressive targets SHOULD express staged improvement from the observed baseline rather than a single remote success threshold:

```text
BASELINE -> NEAR TARGET -> NEXT TARGET -> INTENDED OUTCOME
    |            |              |               |
 observe      follow up      follow up       validate
```

Each follow-up MUST compare the current observation with at least:

- the baseline;
- the previous observation;
- the current progressive target;
- applicable guardrails and constraints.

It MUST then produce a lifecycle consequence: continue, adapt the route, revise the measure or target with preserved rationale, repair regression, replace the Objective, escalate a retained decision, or declare that no justified authorized action exists now.

URACE MUST NOT silently rewrite a baseline or achieved result. Changes to measures, targets, cadence or observation methods MUST preserve prior values, provenance and justification so apparent progress cannot be manufactured by moving the measurement boundary.

Follow-up frequency MUST be proportionate to the rate at which meaningful change can occur, decision value, cost and risk. “Continuous” means that every material accepted increment retains a defined path to the next observation or decision; it does not require constant polling or prevent valid dormancy.

When a configured observation source for an established `ProgressProfile` measure becomes permanently unavailable after its baseline has been recorded, URACE MUST preserve the last observed value, observation time and source identifier as `LAST_KNOWN_GOOD` state, MUST surface the source unavailability as a named observation gap in the progress profile, and MUST NOT treat the absence of a new observation as a zero-value observation or as a regression against the baseline. Permanent measure unavailability does not by itself terminate the governing Objective or trigger a goal revision; it surfaces a specific measurement gap that requires an authorized lifecycle operation — such as `urace add-goal` with an updated `observationMethod` — to establish a replacement measure with a new, explicitly attributed baseline. Until a replacement measure is authorized and established, the Objective status MUST reflect the observation gap rather than an inferred trend derived from the last known value alone.

## Autonomous Operational Feedback

During active autonomous operation, URACE SHOULD provide timely observable feedback proportionate to activity without requiring inspection of internal files. Feedback SHOULD make clear:

- what lifecycle phase or action is occurring;
- what Objective or justification is driving it;
- what was attempted, observed, accepted, rejected, rolled back or blocked;
- current measures, baselines, active targets, trends and guardrails;
- executor and capability availability where relevant;
- the active self-evolution policy when runtime or re-bootstrap work is relevant;
- current lifecycle state and next follow-up or wake condition;
- uncertainty, unresolved effects and material blockers.

Long-running operation SHOULD emit feedback at meaningful cycle, decision, operation, validation, checkpoint, recovery and state-transition boundaries. Unchanged dormant polling MAY be compacted or rate-limited, but silence MUST NOT conceal material activity or deterioration.

Machine-readable event output SHOULD be available where environment-appropriate, while human-readable output SHOULD remain understandable without reconstructing hidden reasoning. Where both are emitted concurrently, the implementation SHOULD preserve a parseable machine channel independently of the human channel. A quiet-human mode MAY suppress human feedback but MUST NOT silently suppress an explicitly requested machine event stream.

Human-readable feedback SHOULD provide a decision trace: the current action or decision, attributable basis, applicable Authority, considered alternative classes, selected Plan, validation status, observed effect, changed artifacts, uncertainty, blockers and next condition. It MUST NOT expose private hidden chain-of-thought, secret values or unrestricted internal scratch reasoning. A concise rationale and Evidence trail are the reviewable explanation; hidden token-by-token reasoning is neither required nor an acceptable substitute for attributable decisions.

Every attempted or accepted change MUST have a stable change identity linked to its Objective, Plan or decision, affected artifacts, validation and disposition. Executor-assisted work MUST also retain the selected Executor identity and adapter, capability, logical reservation, attempted fallbacks and any separately generated explanation. These links MUST survive restart and permit listing changes and inspecting one change without an intelligent Executor call.

An implementation MAY generate plain-language change explanations through an Executor under `auto`, `enabled` and `disabled` policy modes. `disabled` MUST be the default and disables automatic generation while preserving explicit on-demand explanation; `auto` generates only when expected review value justifies its Executor cost; `enabled` generates for every eligible accepted change. Existing attributable Executor output and deterministic records MUST be reused before making another call. Explanations are advisory, MUST identify their source, MUST NOT expose hidden chain-of-thought, and MUST NOT create Authority or change acceptance.

The metric system itself MUST remain reviewable. URACE SHOULD periodically assess whether existing measures remain relevant, decision-useful, resistant to gaming, sufficiently sensitive to progress and regression, and proportionate to observation cost. Metric changes MUST preserve prior definitions, provenance and historical comparability; continuous improvement of measurement MUST NOT silently move baselines or manufacture progress.

## External Metric and Evidence Policy

Bootstrap MUST establish an explicit external-metric policy independently of the runtime self-evolution policy:

```text
DISABLED
    do not acquire external metrics

PROVIDED_ONLY
    use only sources explicitly supplied and authorized

DISCOVER_PUBLIC_AND_USE_PROVIDED
    may discover and propose or use credible public sources within Authority,
    and may use explicitly supplied authorized private sources
```

Absence of an attributable selection MUST default to `DISABLED`. External metric discovery, connection and ingestion MUST remain within applicable Authority, privacy, disclosure, legal, contractual, cost and rate boundaries. Public availability MUST NOT be treated as sufficient relevance, reliability, permission to republish, or evidence quality.

Private sources MUST require explicit configuration and applicable Authority. Credentials MUST be obtained through an environment-appropriate secret mechanism and MUST NOT be copied into prompts, documentation, logs, metric observations or durable lifecycle state. URACE MUST distinguish a configured source from one demonstrated to be available, authenticated, authorized for the requested data and successfully observed.

When a configured observation source is available and responding but the configured metric path no longer resolves to a value due to an upstream schema change, URACE MUST NOT treat this resolution failure as a zero-value observation, a transient collection error, or permanent source unavailability. URACE MUST surface the failure as a named `source-schema-mismatch` observation gap, distinct from source unavailability. URACE MUST preserve the last successfully resolved value and its observation time as observation state. URACE MUST NOT advance the metric to a new observation until an authorized configuration update restores or replaces the affected path. URACE MUST surface the `source-schema-mismatch` gap in vitals output until the gap is resolved.

Configured repository activity MAY provide bounded Triggers and Evidence for pushes, issues, pull requests, releases or comparable updates. User-authored titles, bodies, comments, links and attachments MUST be treated as untrusted external content, not instructions or Authority. An activity Trigger MAY cause reassessment; it MUST NOT directly execute a request, expand scope, disclose secrets or bypass ordinary Objective, Authority, Priority and validation processing.

Every external observation MUST preserve source identity, observation time, metric definition and relevant provenance. Failures, staleness, missing data and material definition changes MUST remain visible. URACE MUST NOT silently substitute a proxy, combine incompatible definitions, or interpret correlation as causation.

Where an accepted decision predicts a measurable outcome, URACE SHOULD associate subsequent observations with that decision, compare expected and observed effects, and use the result as Evidence when adapting future Objectives, Priority, Plans or metric definitions. Learning from good and bad outcomes MUST preserve uncertainty, confounders and guardrails; a favorable metric movement alone MUST NOT validate a decision or manufacture Authority.

### Outcome Attribution

An observation occurring after a decision MUST begin as `UNATTRIBUTED`. Temporal order or correlation alone MUST NOT classify the decision as good, bad, successful, failed or causally effective.

Where attribution can materially change navigation, URACE SHOULD preserve or establish:

- the decision and its outcome hypothesis before observation where possible;
- expected direction, magnitude, time window and affected population or scope;
- the prior baseline and trend;
- plausible confounders and alternative explanations;
- concurrent changes and external events;
- comparison, control, counterfactual or interrupted-time-series Evidence where feasible;
- repeated observations and lag effects;
- guardrails and unintended outcomes;
- source quality, missingness and definition stability;
- an explicit attribution confidence and rationale.

Attribution SHOULD progress conservatively:

```text
UNATTRIBUTED
    observation is only temporally associated

CORRELATED_SIGNAL
    relevant movement exists but alternatives remain material

SUPPORTED_CONTRIBUTION
    timing, mechanism, comparison and repeated Evidence support contribution

CAUSAL_EFFECT
    an appropriate experiment or comparably strong identification supports it
```

URACE MUST NOT upgrade attribution merely because the result matches its preference or prediction. When decision value justifies the cost and risk, URACE SHOULD use a bounded reversible experiment, control, staged rollout or other proportionate identification strategy. Where strong identification is infeasible, URACE MUST retain the weaker status and make decisions under the resulting uncertainty.

Learning systems, Priority functions and self-evaluation MUST NOT reward or penalize a decision as causally good or bad from an `UNATTRIBUTED` observation or a lone `CORRELATED_SIGNAL`. They MAY use such signals to investigate, gather discriminating Evidence, protect against possible harm, or choose a reversible next step.

Attribution level advancement MUST be grounded in criteria that were documented or determinable before the outcome was confirmed; criteria established retrospectively to match an already-confirmed outcome MUST NOT be used to justify level progression. When attribution is reassessed after new Evidence arrives, the prior attribution level and the criteria applied at each prior assessment MUST be preserved in the record; silent in-place revision of attribution level is prohibited.

When a metric improves while a guardrail materially degrades, URACE MUST preserve the conflict and reassess rather than accept the improvement in isolation. Metrics inform navigation but do not create Authority, replace independent validation, or justify destination drift.

Example:

```text
Objective: reduce failed onboarding
Baseline: 18% failure over the last 14 days
Progressive targets: <= 14%, then <= 10%, then <= 7%
Measure: completed eligible attempts / eligible attempts
Follow-up: after each 100 eligible attempts or 7 days, whichever is later
Guardrails: support contacts and median completion time do not materially worsen
Next decision: continue on improvement; diagnose on stagnation; repair or revert on regression
```

When a validation guardrail references a metric source that is currently unavailable or in `source-schema-mismatch` state, guardrail evaluation for that metric MUST default to fail-closed: URACE MUST NOT treat an unobservable guardrail metric as passing by default. Acceptance of a candidate that requires passing an unobservable guardrail MUST be blocked and preserved in pending-validation state until the metric source is restored and a valid observation is obtained, or until an authorized lifecycle operation explicitly resolves the guardrail with recorded justification. URACE MUST surface a blocked acceptance as a named guardrail-observation-gap in the inspection output, identifying the specific guardrail, the unavailable metric source and its gap classification (`UNAVAILABLE` or `source-schema-mismatch`). A guardrail-observation-gap is distinct from the `INSUFFICIENT_EVIDENCE` portfolio evaluator disposition: `INSUFFICIENT_EVIDENCE` applies to evaluation-cycle selection confidence; a guardrail-observation-gap blocks acceptance of a specific candidate regardless of selection confidence.

---

# 61. Checkpoint

```text
EXECUTION
    │
    ▼
OBSERVATION
    │
    ▼
VALIDATION
    │
 ┌──┴──┐
FAIL  ACCEPT
 │      │
 ▼      ▼
REPAIR CHECKPOINT
```

Checkpoint represents accepted durable progress.

When checkpoint persistence fails after validation has succeeded — for example, due to a storage write error or process interruption during checkpoint commit — URACE MUST treat the incomplete acceptance boundary as `APPLYING` under §53 and MUST apply the crash-consistent recovery requirements for that state on next startup. A successful validation result MUST NOT be promoted to an accepted durable checkpoint without durable persistence of the checkpoint record itself. An implementation that advances lifecycle state past `VALIDATED` before the checkpoint record is durably written, or that silently resumes from the prior accepted checkpoint on restart without recording the inconsistency as an unresolved acceptance boundary, violates the crash-consistent acceptance requirement at §53.

---

# 62. State and Persistence

Conceptually:

```text
ProductState {
  product
  authorities?
  authorityResolution?
  autonomousScope?
  intents
  governingIntentReference?
  intentHistory?
  constraints
  currentCheckpoint
  currentObjective
  currentPlan?
  operations?
  decisionRecords?
  evidence
  evidenceAssessments?
  triggers?
  assumptions
  uncertainties?
  risks
  blockers
  completedObjectives
  failedObjectives
  planHistory?
  validationState
  progressProfiles?
  progressObservations?
  followUpState?
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
  stateVersion?
  lastCycle
}
```

Authority and governing Intent MUST be durable or reconstructable where loss could alter legitimate navigation.

Where durable wake registrations have been established under §67, `wakeState` MUST be treated as mandatory rather than optional. A mandatory `wakeState` MUST record at minimum: (a) the identity and type of each currently established wake registration; (b) the lifecycle condition or blocking reservation each registration was established to observe; and (c) the verification status of each registration as determined at the most recent restart under §67. An absent or structurally empty `wakeState` when active wake registrations are known MUST be treated as a wake-integrity gap under §67 and MUST surface as a named limitation in the inspection output. URACE MUST NOT represent dormancy as durably wakeable when `wakeState` is absent or incomplete and one or more active wake registrations have been established.

---

# 62a. Rule Ledger

URACE MUST maintain a **Rule Ledger** — a persistent, inspectable, traceable record of every rule governing the lifecycle: what the system MAY do, MUST do, and MUST NOT do. The Rule Ledger is durable state subject to the same persistence and integrity requirements as §62.

## Three Irreducible Concepts

Every governance event reduces to one of three primitives:

| Primitive | Description |
|-----------|-------------|
| **RULE**   | A named, versioned, first-class governance statement |
| **STATE**  | The current active set of rules and their relationships |
| **CHANGE** | An accepted product or runtime operation, bound to the rules that governed it |

## Rule Kinds

Rules are grouped into three immutability levels:

| Level | Kind | Meaning |
|-------|------|---------|
| L0 | **PURPOSE** | Mission statement — the reason the system exists |
| L1 | **DIRECTIVE** | Durable operator intent — what to pursue |
| L1 | **PERMISSION** | Explicit delegation — what the system is authorised to do autonomously |
| L1 | **PROHIBITION** | Hard constraint — what the system MUST NOT do |
| L2 | **OBJECTIVE** | Operational goal with success measure — what to achieve next |
| L2 | **POLICY** | Operational mode setting — how to operate |

## Immutability Contracts

**L0 (PURPOSE).** URACE MUST NOT modify, supersede, or deactivate a PURPOSE rule under any condition, including self-evolution. A PURPOSE rule is immutable for the lifetime of the lifecycle. An attempt to supersede or deactivate a PURPOSE rule MUST be rejected and surfaced as a named violation.

**L1 (DIRECTIVE, PERMISSION, PROHIBITION).** URACE MUST NOT add, supersede, or deactivate an L1 rule without an attributable operator input. No autonomous or self-evolution path MAY produce a net change to the active L1 rule set without that attribution. A self-evolution operation that would require an L1 change MUST be blocked and surfaced as a named blocker requiring operator action.

**L2 (OBJECTIVE, POLICY).** URACE MAY create, update, close, or supersede L2 rules while operating within delegated authority under §11 and §12. L2 mutations MUST be recorded in lifecycle Evidence with attribution.

## Relationships

Rules form a directed acyclic graph (DAG) via five relationship types:

| Type | Meaning |
|------|---------|
| `derived_from` | This rule is a more specific form of a parent rule |
| `governed_by` | This rule operates within the bounds of another |
| `governed_changes` | This rule has governed specific accepted changes |
| `superseded_by` | This rule has been replaced by a newer version |
| `conflicts_with` | This rule overlaps or contradicts another |

Cycles in the derivation or governance graph are not permitted. An implementation that would introduce a derivation cycle MUST reject the new rule and surface the cycle as a named error.

## Conflict Contract

URACE MUST detect and surface conflicts between active rules. A conflict exists when a PERMISSION and a PROHIBITION overlap in scope and subject with sufficient specificity to produce contradictory governing conditions. Detected conflicts MUST appear in the inspection output as named conditions; they MUST NOT be silently tolerated or used as justification to bypass either conflicting rule. An operation governed by conflicting rules MUST be held pending operator resolution unless one rule explicitly supersedes the other via a `superseded_by` relationship.

## System-Inferred Rules

URACE MAY infer rules from existing rules (e.g. an explicit PROHIBITION in a broad scope implies a scoped PROHIBITION for a specific subject). Inferred rules:

- MUST carry `derivation: SYSTEM_INFERRED` and a `confidence` score (0.0–1.0)
- MUST NOT block, gate, or reject operations until their confidence meets the `INFER_BLOCKING` threshold — they are strictly advisory below that threshold
- MUST carry a traceable `derived_from` link to the source rule or rules
- MUST decay when the source rule is deactivated or superseded; an inferred rule MUST NOT remain active after its entire derivation chain is deactivated
- At `INFER_BLOCKING` confidence, MUST carry a complete derivation chain traceable to at least one explicit L1 rule

URACE MUST NOT promote a SYSTEM_INFERRED rule to L1 status without explicit operator confirmation supplied via authoritative input.

## Temporal Change Binding

When an operation is **ACCEPTED**, URACE MUST:

1. compute a **snapshot digest** — the SHA-256 of the lexicographically sorted active rule set at the moment of acceptance
2. record the list of **governing rule IDs** alongside the accepted change

These two records MUST be stored atomically with the accepted change and MUST NOT be modified after acceptance. The snapshot digest MUST be computable from the current active rule set at any point without reference to prior digests.

This allows any future inspection to answer: *"what rules were active and governing when this change was made?"*

```
ACCEPTED OPERATION
  → snapshot digest (SHA-256 of active rule set)
  → governing rule IDs
  → stored atomically in change_bindings
```

If the Rule Ledger is unavailable at acceptance time, URACE MUST surface this as a named integrity gap and MUST NOT silently accept a change without its binding.

## Append-Only Invariant

The Rule Ledger MUST be append-only with supersession. Rules MUST NOT be deleted from the Ledger. A rule that is no longer active MUST be marked deactivated or superseded with an attributed timestamp and reason, preserving the full historical chain. Any query against the Ledger MUST be able to reconstruct the complete active rule set at any prior accepted change by replaying the binding record.

## Bootstrap Seeding

At `init`, URACE MUST seed the Rule Ledger from the bootstrap configuration before persisting initial state. The seeding mapping is:

| Config field | Rule kind |
|---|---|
| `intent.purpose` | PURPOSE (L0) |
| `intent.retained` | PROHIBITION (L1) |
| `authority.delegated` | PERMISSION (L1) |
| `authority.reserved` | PROHIBITION (L1) |
| `constraints[]` | PROHIBITION (L1) |
| `self_evolution_policy` | POLICY (L2) |
| `external_metrics.mode` | POLICY (L2) |

After seeding, the Ledger MUST be the single source of truth for active governance rules. Bootstrap config fields MUST NOT be re-read per cycle as a substitute for querying the Ledger. A lifecycle that lacks a Rule Ledger in durable state after `init` MUST surface this as a named integrity gap on next load.

## User Interface

Three commands expose the Rule Ledger:

| Command | Effect |
|---------|--------|
| `urace intent add "…"` | Add a DIRECTIVE rule (queued; applied at next safe boundary) |
| `urace intent list` | List active DIRECTIVE rules |
| `urace intent supersede "…" --id <id>` | Replace an existing DIRECTIVE with a new one |
| `urace intent deactivate --id <id>` | Deactivate a DIRECTIVE rule |
| `urace constraint add "…"` | Add a PROHIBITION rule |
| `urace constraint add "…" --allow` | Add a PERMISSION rule |
| `urace constraint deactivate --id <id>` | Deactivate a constraint rule |
| `urace rules list` | List all active rules |
| `urace rules inspect <id>` | Full rule record with derivation chain |
| `urace rules graph` | Full rule graph with relationships |
| `urace rules conflicts` | Surface detected rule conflicts |
| `urace rules changes <id>` | List accepted changes governed by a rule |

`intent` and `constraint` mutations are queued inputs applied at the next safe lifecycle boundary under the same atomicity guarantees as §62. They MUST NOT be applied mid-cycle.

---

# 63. Concurrency

Where multiple runtimes MAY operate:

```text
READ S12
   │
   ▼
DECIDE
   │
   ▼
COMMIT AGAINST S12
   │
 ┌─┴──────┐
S12      S13
 │         │
 ▼         ▼
COMMIT   RECONCILE
```

Stale decisions MUST NOT silently overwrite newer authoritative state.

Locks, leases or ownership markers left by interrupted runtimes MUST be reconciled before reuse. An implementation MUST NOT discard an ownership marker merely because it is old when a live owner may still exist.

When liveness of an existing ownership marker cannot be established through available environment-level signals — such as process existence, heartbeat record age, or an equivalent mechanism — URACE MUST surface the marker as a named unresolved ownership boundary in the lifecycle inspection output and MUST NOT silently supersede it based on elapsed time alone. An authorized operator clearance of the marker through an authenticated lifecycle command is the only valid path to ownership acquisition when liveness is indeterminate; the clearance MUST be recorded as a durable event. An implementation that silently times out an ownership marker without attributable proof of owner absence violates the stale-overwrite prohibition stated above.

---

# 64. Lifecycle States

Conceptual equivalents:

```text
ASSESSING
ACTIVE
VALIDATING
RECONCILING
REPAIRING
WAITING_FOR_CAPACITY
WAITING_FOR_CONDITION
WAITING_FOR_SCHEDULE
WAITING_FOR_AUTHORITATIVE_DECISION
BLOCKED
PAUSED
IDLE
```

`IDLE` represents the lifecycle condition referred to as `DORMANT` throughout this specification: no justified authorized action exists now and no unreconciled externally committed effect is pending, but a viable path back to assessment is retained. The terms are normatively interchangeable; an implementation MUST NOT treat them as distinct states with different transition, wakeability, or persistence requirements.

The `ASSESSING` lifecycle state is the evaluation phase in which URACE reviews current Evidence, outstanding Objectives, pending reservations, resource availability, and any unresolved effects discovered at wake or transition, before committing to or continuing authorized work. Entry to `ASSESSING` MUST occur on wake from `IDLE`, on successful exit from `REPAIRING`, at resumption from `PAUSED`, and at any state transition where independent evaluation is required before active execution may begin. The inspection surface MUST expose without an Executor call: the identity of Objectives currently under assessment, the Evidence dimensions being evaluated, and any unresolved effects or pending reservations discovered during assessment. `ASSESSING` is distinct from `ACTIVE`, which executes work under a positively identified justified Objective without requiring a fresh assessment cycle first; and from `IDLE`, which holds no justified work and no active evaluation. `ASSESSING` exits to `ACTIVE` when a justified authorized action is identified; to `IDLE` when no justified authorized action exists; or to `BLOCKED` when an unreconciled externally committed effect is discovered. An implementation MUST NOT skip `ASSESSING` after `REPAIRING` exits and transition directly to `ACTIVE`; the post-repair assessment cycle is the mechanism by which restored Product integrity is independently confirmed before new work begins.

`WAITING_FOR_AUTHORITATIVE_DECISION` exists only where a decision was actually retained.

It MUST NOT become the normal operating mode.

The `BLOCKED` lifecycle state MUST be used when an Operation has reached a commit boundary and produced or attempted to produce an externally committed effect whose outcome remains uncertain, and where proceeding without resolving that uncertainty would risk duplicating a consequential effect, corrupting accepted state, or misattributing causal responsibility. Entering `BLOCKED` MUST record: the identity of the unresolved Operation or effect, the nature and source of the uncertainty, and the earliest qualifying condition or authorized Operation that would allow reconciliation to proceed. An implementation MUST NOT automatically retry a `BLOCKED` effect without a reconciling resolution, MUST NOT escalate `BLOCKED` to self-repair or self-evolution, and MUST NOT allow `BLOCKED` to become a permanent silent state without a durable follow-up condition. The inspection surface MUST expose `BLOCKED` status, the identified effect record and the reconciliation path without requiring an Executor call.

The `RECONCILING` lifecycle state is entered when URACE has positively established that the qualifying reconciliation condition for a previously `BLOCKED` uncertain externally committed effect is met, and is actively executing the reconciliation queries, probes or transaction-reference lookups required to establish a definitive disposition for that effect. Entry to `RECONCILING` MUST require positive establishment of the qualifying condition through an attributable signal; elapsed time, timeout or inferred resolution MUST NOT substitute for a qualifying-condition signal. `RECONCILING` is distinct from `BLOCKED`, which is held when uncertainty exists but the qualifying condition for reconciliation has not yet been met; `RECONCILING` is the active in-progress counterpart that begins only when that condition is positively established. While in `RECONCILING`, the lifecycle MUST NOT dispatch new Operations whose execution depends on the uncertain effect's outcome; such Operations MUST remain in pending-eligibility state until a definitive disposition is established. The inspection surface MUST expose without an Executor call: the identity of the Operation whose externally committed effect is being reconciled, the reconciliation method and probe or query type in use, and the latest observed reconciliation step with its timestamp. If reconciliation attempts consistently fail to return a definitive disposition across a declared attempt ceiling, URACE MUST surface a named reconciliation-stalled condition and MUST NOT remain silently in `RECONCILING` without a bounded resolution path. `RECONCILING` exits based solely on the reconciliation result: to an appropriate active or assessment state when a definitive disposition is established, or to `BLOCKED` at a new qualifying-condition prerequisite when the declared attempt ceiling is reached without a disposition.

The `REPAIRING` lifecycle state is entered when URACE has detected a Product integrity failure through an attributable check result — an acceptance validation failure, a self-consistency check, a failed activation health check, or an equivalent attributable integrity signal — and is actively executing the bounded repair sequence required to restore the Product to its last known good accepted state. Entry MUST be triggered by a durable integrity-failure record identifying the check that failed and its observed criterion; autonomous inference of integrity failure without an attributable check result MUST NOT constitute valid entry. `REPAIRING` is distinct from `ACTIVE`, which represents ordinary Product evolution under authorized Intent initiated by justified Objective work rather than a detected integrity failure; from `RECONCILING`, which handles uncertain external effect disposition rather than Product artifact integrity; and from `BLOCKED`, which holds when a committed external effect cannot yet be reconciled. The inspection surface MUST expose without an Executor call: the triggering integrity-failure check identifier and its failed criterion, the Product checkpoint being used as the repair baseline, and the current bounded repair step and its completion condition. A repair sequence MUST have a declared attempt ceiling; if the ceiling is reached without successful restoration, URACE MUST surface a named repair-exhausted condition, MUST NOT continue repair attempts autonomously, and MUST retain durable lifecycle state intact pending operator review. On successful completion, `REPAIRING` exits to `ASSESSING` for an independent integrity-confirmation cycle before any return to `ACTIVE`; a direct transition from `REPAIRING` to `ACTIVE` without an intervening `ASSESSING` confirmation cycle MUST NOT occur.

The `VALIDATING` lifecycle state is entered when an Operation has produced a Product increment that has not yet passed the acceptance validation required to commit it to the accepted Product state. Entry MUST be triggered by a completed increment with a durable record identifying the increment and the acceptance criterion to be applied; the lifecycle MUST NOT enter `VALIDATING` without such a record. The inspection surface MUST expose without an Executor call: the identity of the Product increment under validation, the acceptance validation method in use, and the current validation step and its completion condition. An elapsed-time limit MUST NOT substitute for a positive acceptance validation result; if the validation method is temporarily unavailable, the increment MUST remain in `VALIDATING` pending availability rather than being silently accepted. `VALIDATING` is distinct from `ACTIVE`, which executes authorized work to produce an increment and does not involve an acceptance gate on a completed increment; from `ASSESSING`, which evaluates current conditions before any increment is produced; and from `REPAIRING`, which is entered only after an increment has already failed acceptance validation and the bounded restoration sequence is executing. On successful validation, `VALIDATING` exits to `ASSESSING` for a fresh evaluation cycle; on validation failure, `VALIDATING` exits to `REPAIRING` with a durable integrity-failure record identifying the failed criterion.

The `PAUSED` lifecycle state represents an explicit suspension initiated by an authorized operator command. A `PAUSED` lifecycle MUST retain durable state, Intent, Authority and lifecycle history intact. Unlike `BLOCKED`, it has no unreconciled externally committed effect requiring resolution before resumption; unlike `IDLE`, its suspension was explicit rather than the result of no justified authorized action existing now. URACE MUST NOT enter `PAUSED` autonomously; it MUST require an attributable authorized operator input. While `PAUSED`, URACE MUST preserve all pending scheduled conditions in durable state and MUST process them in due-date order at successive eligible lifecycle boundaries after resumption, before new unscheduled work begins. `urace autonomous` MUST resume a `PAUSED` lifecycle from its preserved durable state without reinitializing Authority, Intent, Evidence or accepted lifecycle history.

The `WAITING_FOR_CAPACITY` lifecycle state is entered when an Executor required for a reserved Operation is currently unavailable due to verifiable capacity exhaustion or provider-side throttling. This state is distinct from an authentication failure or a capability gap, both of which are governed by §43: capacity exhaustion means the Executor is correctly authenticated and capable but cannot accept new work because a provider-imposed ceiling or usage window has been reached. Entry MUST NOT occur solely because provider capacity is intermittently slow; the unavailability MUST be established through an attributable provider signal rather than inferred from latency or timeout alone. The inspection surface MUST expose: the identity of the capacity-unavailable Executor, the identity of the reserved Operation it is blocking, and the earliest qualifying recovery condition sufficient to exit the state. A `WAITING_FOR_CAPACITY` lifecycle MUST retain all task reservations and durable state intact; no reservation MAY be discarded or abandoned while this state is held. `WAITING_FOR_CAPACITY` is distinct from `DORMANT` (`IDLE`), which carries no reserved blocking work and therefore has no pending capacity dependency, and from `BLOCKED`, which holds an unreconciled externally committed effect requiring authorized resolution before progress. See §43 for Executor re-verification requirements on return from a capacity unavailability period and §66 for proportionate availability observation and qualifying wake conditions.

The `WAITING_FOR_CONDITION` lifecycle state is entered when a required precondition for a reserved Operation is not yet satisfied and the unsatisfied precondition is neither Executor capacity exhaustion nor an authoritative retained decision. Representative entry causes include: a dependency artifact not yet produced by a sibling workstream, an external system state not yet observable as met, and a prerequisite check not yet passing. Entry MUST be attributable to an identifiable precondition; a vague or uncharacterized dependency MUST NOT be grounds for entering this state. The awaited condition MUST be recorded as a durable dependency record at the point of entry; this record MUST identify: the awaited condition and the observable criterion that constitutes its satisfaction, the identity of the dependent Operation whose progress is gated on that condition, and the earliest qualifying resolution path sufficient to exit the state. The inspection surface MUST expose all three of these elements without requiring an Executor call. `WAITING_FOR_CONDITION` MUST NOT persist without an observable resolution path: if the awaited condition is determined to be unresolvable, the lifecycle MUST surface it as a named blocking limitation rather than allowing it to remain silently in this state. `WAITING_FOR_CONDITION` is distinct from `WAITING_FOR_CAPACITY`, which is entered when an Executor is correctly authenticated and capable but cannot accept new work due to a provider-imposed capacity ceiling or usage-window limit; from `WAITING_FOR_SCHEDULE`, which is entered when a time-based trigger has not yet become due; and from `WAITING_FOR_AUTHORITATIVE_DECISION`, which is entered only where a decision was actually retained by the authoritative source and whose resolution depends on that retention being resolved.

The `WAITING_FOR_SCHEDULE` lifecycle state is entered when the next eligible lifecycle boundary for a reserved workstream is determined by a time-based trigger whose due time has not yet arrived. Entry MUST be attributable to an identifiable scheduled condition; a `WAITING_FOR_SCHEDULE` state MUST record the identity of the awaited trigger and its due time at entry. The inspection surface MUST expose without an Executor call: the identity of the awaited scheduled trigger, its due time, and the lifecycle scope or Operation whose eligibility depends on that trigger becoming due. `WAITING_FOR_SCHEDULE` exits automatically when the scheduled trigger becomes due; no operator action or manual restart is required to exit the state. While in `WAITING_FOR_SCHEDULE`, durable task reservations and lifecycle state MUST be preserved intact. `WAITING_FOR_SCHEDULE` is distinct from `WAITING_FOR_CONDITION`, which is entered when a required precondition independent of time is not yet satisfied; from `WAITING_FOR_CAPACITY`, which is entered when an Executor is correctly authenticated and capable but cannot accept new work due to a provider-imposed capacity ceiling; and from `WAITING_FOR_AUTHORITATIVE_DECISION`, which is entered only where a decision was actually retained by the authoritative source. URACE MUST NOT discard a separately registered scheduled trigger merely because the lifecycle is already in `WAITING_FOR_SCHEDULE` awaiting a different trigger; independently registered scheduled triggers MUST each be evaluated at their respective due times.

---

# 65. Partial Blocking

A retained, denied or unresolved decision SHOULD block the smallest dependent scope.

```text
PRODUCT
  │
  ├── Workstream A
  │      └── retained decision
  │             ↓
  │           WAIT
  │
  ├── Workstream B
  │      └── delegated
  │             ↓
  │          CONTINUE
  │
  └── Workstream C
         └── delegated
                ↓
             CONTINUE
```

One retained decision MUST NOT unnecessarily turn the authoritative source into the pilot of the entire lifecycle.

Two workstreams are in the same dependent scope if and only if progress on one requires a decision, value or committed outcome from the other that is currently retained, denied or unresolved; workstreams with no direct or transitive dependency on the blocking decision are outside the dependent scope and MUST continue unblocked under partial blocking.

When a new Objective is proposed while a partial blocking condition is active, URACE MUST assess whether the proposed Objective has a direct or transitive dependency on the retained, denied or unresolved decision before admitting it to the active workstream set. A proposed Objective with no such dependency MUST be admitted and progressed under the ordinary lifecycle without requiring resolution of the blocking condition; a proposed Objective with such a dependency MUST be preserved in pending-eligibility state, MUST NOT be promoted to active status before the blocking condition resolves, and MUST surface in the inspection output as blocked on the same unresolved decision. The admission assessment MUST use the same dependency criterion as defined above: a proposed Objective shares the dependent scope only when its progress requires a decision, value or committed outcome from the blocked workstream.

When an already-admitted and in-progress Objective encounters, during execution of one of its Operations, a new direct or transitive dependency on a retained, denied or unresolved decision — for example, because a required authorization became retained after admission or a previously resolved decision was revoked while the Objective was executing — URACE MUST apply the minimum-scope blocking principle within that Objective's remaining Operations. Operations with a direct or transitive dependency on the blocking condition MUST be suspended and preserved in pending-eligibility state; Operations without such a dependency MUST continue at their next eligible lifecycle boundary. The in-progress Objective MUST NOT be retired or abandoned solely because one of its Operations cannot proceed; the minimum-scope blocking rule applies within an in-progress Objective across its Operations in the same way it applies across Objectives within the lifecycle. The in-progress Objective's blocked Operations MUST be surfaced in the inspection output as a named partially-blocked workstream, attributed to the same unresolved decision record that governs newly proposed Objectives blocked by the same condition.

---

# 66. Autonomous Liveness

```text
DURABILITY
    state survives

LIVENESS
    lifecycle can progress

WAKEABILITY
    dormancy can end

DORMANCY
    no justified authorized work now

AUTONOMY
    URACE independently navigates
    within delegated Authority
```

These are distinct.

A dormant condition is wakeable only when a viable mechanism or durable responsibility can actually observe a qualifying change and cause reassessment. Merely recording a future condition without an observer, schedule, callback, poller or equivalent activation path does not establish wakeability.

Where capability availability is lifecycle-relevant, its material transition MAY wake dormant operation. Availability observation MUST remain proportionate and MUST NOT require repeated costly executor invocation when a cheaper readiness probe exists.

A capability availability transition qualifies as proportionate observation only when: (a) the capability is recorded as a blocking reservation at dormancy entry—monitoring capabilities with no reserved blocking work does not qualify; (b) the observation represents a genuine state transition from unavailable to available, not a routine polling heartbeat, unchanged-state confirmation or periodic health probe; and (c) the transition MUST NOT generate dependent lifecycle work until reassessment independently confirms justified authorized action. An implementation that wakes dormant operation on any availability signal, or that suppresses a qualifying transition by demanding stronger evidence than an attributable unavailable-to-available state change, violates proportionality.

Executor authentication, command readiness and provider capacity MUST be represented separately. When a provider returns an attributable capacity or usage-window reset, URACE MUST treat it as scheduled unavailability rather than Product failure, candidate regression, guardrail failure or a reason for self-repair. It MUST durably retain the current logical task and its reservation, including controller planning, and suppress only work dependent on that unavailable capacity. Authoritative retry or availability Evidence SHOULD determine reactivation; otherwise an implementation MUST use an environment-appropriate configurable re-evaluation policy derived from applicable Evidence, constraints, budgets, Executor characteristics and supported wake mechanisms, adapt it when those premises materially change, and permit earlier reactivation on qualifying Evidence. Unchanged unavailability MUST be durably deduplicated and surfaced only when its state materially changes or information becomes actionable; no universal strategy or interval is implied.

Logical task reservations and transport attempts MUST be accounted separately. If an adapter supports authenticated provider-session continuation, URACE SHOULD resume the accepted session from its durable continuation identity. If it does not, URACE MUST say so and MAY replay the same bounded logical stage after capacity returns without opening a second logical reservation; it MUST preserve a transport-attempt count and MUST NOT claim that replay is provider-side continuation or that rejected attempts consumed no provider resources without Evidence. Interruption, reset-window changes and repeated deferrals MUST remain bounded, observable and revocable.

Where multiple Executors are attached, availability, authentication, capabilities, provider-capacity schedules, cooldowns, transport attempts and provider-specific ceilings MUST be tracked per Executor. Selection and fallback MUST preserve one provider-independent logical task and reservation, require compatible tools, context handling, sandbox, output contract and Authority, and use the same independent validation after every transport. One Executor's capacity window MUST NOT block another compatible available Executor. Fallback MAY follow readiness, capacity or compatible-capability failure; it MUST NOT bypass a refusal, Authority boundary, guardrail, validation result or fixed task budget. If every compatible Executor is unavailable, URACE MUST enter one attributable scheduled wait using the earliest eligible retry without erasing later schedules. Cross-provider work MUST be called replay unless a validated adapter supplies a durable provider-session continuation identity.

An attributable failure of the shared execution environment, confinement backend or workspace transport MUST be recorded as Executor or capability unavailability rather than repeated as independent candidate failure. Dependent work MUST retain its logical reservation and enter a deduplicated scheduled wait or use a separately validated compatible Executor; peers MUST NOT consume equivalent calls while the same shared prerequisite is known unavailable. Readiness and unattended preflight MUST exercise the configured execution path, including write and isolation behavior where applicable, and invalidate cached readiness after a material executable, sandbox, policy, identity or environment change.

A persistent autonomous owner SHOULD expose a concurrent control plane so authorized inspection and durable control inputs do not require process restart. Read-only Operations MAY observe accepted snapshots concurrently. Mutating inputs MUST enter an atomic authenticated or locally protected inbox, receive an attributable receipt, and be applied exactly once at a declared safe lifecycle boundary by the single mutation owner.

Pending inbox inputs MUST be applied in the order they were received — oldest first — within a single safe lifecycle boundary. When a boundary applies more than one pending input, all must be processed in received order before that boundary is marked complete. An input's position in the queue MUST NOT be affected by its content type, scope, command class, or originating operation.

Executor attachment, detachment, priority or capability changes MUST NOT replace an Executor already inside an indivisible attempt; they affect the next routing boundary. Invalid controls MUST be rejected without stopping unrelated autonomous work. Direct concurrent mutation, lock bypass and partially applied control changes remain prohibited.

---

# 67. Runtime Lifetime vs Lifecycle Lifetime

```text
RUNTIME EXIT
    ≠
AUTONOMOUS LIFECYCLE END
```

Runtime MAY disappear during dormancy if durable wake responsibility exists.

Continuous AI inference is not required.

When no viable mechanism — scheduler, callback, poller, file-system watcher or equivalent — can observe a qualifying wake condition, runtime disappearance does not constitute valid dormancy. URACE MUST surface the missing wake path as a material blocking limitation before suspending, MUST retain the last assessment record and all pending reservations intact, and MUST NOT treat the absence of a wake mechanism as authorization to end lifecycle ownership. A subsequent environment change that establishes a durable wake path allows dormancy to resume normally; until then the implementation MUST remain available to restart-based reassessment without data loss.

Where the implementation does not provide or depend on an operating-system-level process supervisor or init system, it MUST document this operational boundary at bootstrap and MUST surface it as a named limitation in the lifecycle inspection output. This boundary is not a lifecycle failure: durable state and lifecycle ownership persist across process exit; resumption requires an authorized operator-initiated process restart. An implementation MUST NOT represent lifecycle liveness as continuous when the absence of a running process requires manual operator intervention to resume. Recovery after such a restart MUST resume the accepted lifecycle without reinitializing durable Authority, Intent, Evidence or lifecycle history.

When URACE resumes from a restart in a lifecycle state that records one or more established durable wake registrations — scheduled triggers, OS callbacks, file-system watchers or equivalent — it MUST verify that each recorded registration is still active in the current environment before representing dormancy as durably wakeable. A recorded wake registration whose current-environment status cannot be verified MUST be treated as potentially absent and MUST surface as a named wake-integrity gap in the lifecycle inspection output; URACE MUST NOT represent the dormancy state as durably wakeable solely on the basis of a prior registration record. URACE MUST attempt to re-establish each unverifiable wake registration where authorized and technically feasible; where re-establishment cannot complete, the gap MUST remain named in the inspection output and URACE MUST retain lifecycle state intact and remain available to restart-based reassessment without data loss, consistent with the requirement stated for the no-mechanism case. A wake-integrity gap is a named limitation, not a lifecycle failure and not authorization to end lifecycle ownership.

---

# 68. Persistent `--autonomous`

`--autonomous` means persistent autonomous lifecycle ownership.

It does NOT mean:

```text
wait for user task
    ↓
perform task
    ↓
ask what next
```

It means:

```text
observe
   ↓
assess
   ↓
discover
   ↓
decide
   ↓
prioritize
   ↓
plan
   ↓
execute
   ↓
learn
   ↓
validate
   ↓
checkpoint
   ↓
reassess
   ↺
```

with:

```text
AUTHORITATIVE SOURCE
       │
       └── intervenes only where
           retained Authority,
           explicit interaction,
           or exceptional ambiguity
           requires it
```

---

# 69. When Autonomous Operation May End

Persistent ownership MAY end only through explicit semantics such as:

- operator stop;
- explicit cancellation;
- bounded execution reaching its boundary;
- one-shot invocation;
- authoritative termination policy;
- explicit Product/project contract termination.

When autonomous operation ends through a graceful operator stop, URACE MUST complete any indivisible atomic operation currently in progress to its next safe checkpoint boundary before stopping; it MUST NOT start a new Operation once the stop has been signaled. At the stop boundary, URACE MUST durably persist the current lifecycle state — including all unresolved effect records, pending reservations, queued authoritative inputs and the most recent assessment record — and MUST NOT clear or compact durable state as part of the stop sequence. A graceful stop MUST return a visible confirmation that durable state is intact and identify any unresolved effects that require attention before resumption. A graceful stop confirmation MUST also identify any queued authoritative inbox inputs that were received but not yet applied at the stop boundary, so that an operator can determine without consulting `urace inbox list` whether re-issuance would constitute a duplicate authorized action. Abrupt non-graceful termination (signal, crash, resource exhaustion) MUST be survivable through the ordinary crash-consistent recovery path without additional operator action beyond a restart.

No Objective, dormancy, executor unavailability, Plan completion, readiness or Market Fit MUST NOT silently end persistent ownership.

---

# 70. Readiness and Convergence

Readiness SHOULD consider:

- governing Intent satisfaction;
- Authority;
- HARD constraints;
- validation;
- credible applicable Evidence;
- defects;
- risk;
- Product coherence;
- external Evidence where applicable;
- uncertainty;
- unresolved effects;
- time;
- resources;
- remaining justified authorized action.

Convergence:

```text
ACTIVE
  │
  ▼
ASSESS
  │
  ▼
NO JUSTIFIED AUTHORIZED
ACTION NOW
  │
  ▼
DORMANT
  │
  ▼
WAIT / DISCOVER
  │
  ▼
MEANINGFUL CHANGE
  │
  ▼
ACTIVE
```

Convergence into `IDLE` MUST NOT occur while any externally committed effect attributed to the current lifecycle remains in `INDETERMINATE` or unreconciled state under §53. The absence of remaining Objectives, Plans or pending scheduled conditions is not sufficient for convergence if at least one unreconciled committed effect exists; the lifecycle MUST remain in `RECONCILING` state, surface the outstanding effect record in the inspection output as a named blocker, and MUST NOT silently discard or treat as resolved any committed effect solely because no new work is pending. An implementation that converges to `IDLE` over an open unreconciled effect violates the durability requirement of §53 and the persistence requirement of §62.

---

# 71. Anti-Churn, Anti-Drift and Anti-Approval-Loop

URACE MUST NOT repeatedly:

- optimize vanity metrics;
- collect Evidence merely for volume;
- manufacture Objectives;
- execute merely because a Schedule fired;
- confuse capability with Authority;
- reinterpret Evidence to preserve preferred conclusions;
- ignore contradiction;
- reinterpret retained Intent to fit Evidence;
- treat Product Value as Authority;
- treat Priority as Authority;
- treat market success as Authority;
- treat executor recommendation as Authority;
- expand delegated Authority;
- invent higher-order Intent;
- change retained destination because another destination appears easier;
- execute stale consequential decisions;
- blindly retry uncertain external effects;
- overwrite newer lifecycle state;
- manufacture work to avoid dormancy;
- request approval for decisions already delegated;
- convert broad Authority into per-step permission checks;
- use Authority resolution as a substitute for Product reasoning;
- use caution as justification for abandoning autonomy;
- ask the authoritative source to navigate decisions URACE owns;
- terminate ownership because work converged.

URACE MUST also resist informational and implementation bloat. It SHOULD avoid recording unchanged high-frequency observations, duplicate checkpoints, repeated failure text, redundant guidance, unused abstraction layers and speculative capabilities without decision value. It SHOULD use proportionate retention, summaries, digests, archives or compaction while preserving accepted decisions, Authority, material Evidence, unresolved effects and recovery integrity.

Material changes SHOULD have an explicit complexity and growth budget. Exceeding that budget requires attributable justification and validation that the added surface has greater expected lifecycle value than a smaller route. Line count, feature count and state volume MUST NOT be treated as progress.

Metered or credit-consuming Executors MUST have an explicit invocation budget, durable usage accounting and a visible exhaustion state. Cheap local availability probes, deterministic measurement and cached observations SHOULD run without invoking the intelligent Executor. Intelligent discovery SHOULD be trigger-first and use a proportionate low-frequency opportunity audit rather than spending credits on every autonomous cycle. Unchanged dormancy MUST NOT consume model credits merely to confirm that nothing changed. A manual forced invocation MUST remain attributable and subject to any hard budget or safety boundary.

Resource accounting MUST use the strongest available measurement without manufacturing unavailable data. Provider-reported monetary usage is preferred, followed by reported tokens or metered units, then an explicitly labelled invocation-count proxy. Cycle count, readiness checks, elapsed time, storage, network requests and tool invocations MAY quantify deterministic overhead or estimated service capacity, but MUST NOT be renamed or combined as provider credits without a defensible conversion. Executor availability establishes readiness only; it does not establish remaining credit. Where dimensions cannot be defensibly combined, URACE MUST report the resource vector separately and preserve each unit and source.

Availability observation MAY participate in resource-versus-efficiency evaluation through operational measures such as probe count and duration, suppressed redundant checks, useful readiness transitions, wake latency and avoided futile invocations. These measures evaluate the observation strategy; they MUST NOT be presented as the Executor's monetary or token cost.

Credit protection MUST cover every metered stage, including discovery, planning assistance, execution, validation assistance, retries and failed calls; counting only successful or discovery calls is insufficient. A call reservation MUST become durable before invocation so interruption cannot silently reopen spent budget. Before discovery, an implementation SHOULD reserve enough remaining budget for the likely completion path so it does not spend credit identifying work that it cannot carry through. It MUST enforce attributable hard bounds at the applicable task, stage, generation, deployment or provider boundary, coalesce equivalent triggers, and avoid automatic retries that repeat the same context and expected result. Short- and long-window transport ceilings MAY supplement those bounds where justified; their presence, absence and units MUST be explicit rather than inferred from Executor readiness.

An interrupted in-progress stage MUST resume or replay its existing logical reservation rather than consume a new one. Exhausting a stage or generation hard bound MUST terminate and retain that bounded unit, but MUST NOT terminate a persistent autonomous owner when a separately attributable later unit can proceed within unchanged Authority and budgets.

Long-run scheduling SHOULD adapt to observed marginal value. Repeated no-action, ineligible, failed or no-effect calls SHOULD progressively lengthen the opportunity-audit interval up to a declared bound; material new Evidence MAY wake reassessment without erasing an applicable usage ceiling. A productive accepted result MAY reset the value backoff. Prompt context MUST be bounded, deduplicated and selected for decision relevance while retaining the Authority, constraints and Evidence needed for a sound decision. Feedback SHOULD distinguish calls by stage and outcome and report configured window use, suppression reason, unproductive streak and the next eligible reassessment. These controls are guardrails rather than a claim of mathematically optimal spending: an implementation MUST make its policy configurable and measurable so observed value per call can improve it without weakening applicable hard bounds.

When the recorded unproductive discovery streak — consecutive complete-cycle calls returning no justified action, ineligible scope under current policy, or a transport failure — reaches a declared configurable threshold, URACE MUST surface the named condition `DISCOVERY_YIELD_EXHAUSTED` in the lifecycle inspection output and in the efficiency vital. In `DISCOVERY_YIELD_EXHAUSTED` state, further discovery credits MUST NOT be spent at ordinary scheduled cadence: the lifecycle MUST remain dormant at the configured backoff ceiling until a qualifying reset event is observed. Qualifying reset events are: (a) a newly applied authoritative inbox input — any input consumed from the atomic inbox qualifies, since the inbox is idempotent-by-design and each entry is applied exactly once; (b) a net-new Evidence record added since the streak began; (c) a change to governing Intent, product-file content, or Authority configuration; or (d) an operator force-discovery invocation. Force-discovery bypass MUST be recorded as a durable attributed override event; it bypasses the gate for exactly one discovery cycle and MUST NOT reset the unproductive streak counter — the streak resets only when the discovery cycle itself produces justified work. If a force-discovery cycle returns no justified action, the streak increments as normal and the exhausted condition reactivates. The exhausted-streak threshold, ceiling dormancy interval, and qualifying reset conditions MUST each be configurable, explicitly declared in inspection output, and governed by the same Authority and self-evolution policy that applies to any other efficiency parameter.

Before invoking a discovery cycle that will consume a metered or credit-accruing Executor call, URACE MUST evaluate whether the expected marginal discovery value at the current product state justifies the cost. This proportionality assessment MUST account for: the productive-call yield rate observed over recent discovery calls; the current unproductive streak; whether any qualifying new input has arrived since the prior discovery cycle; and whether a known blocking condition — including an active `BLOCKED` lifecycle state, exhausted execution budget, or a capability gap for a required downstream stage — would prevent acting on discovered work regardless of the discovery outcome. An active `BLOCKED` lifecycle state MUST unconditionally defer discovery: a discovered Objective cannot proceed while an unreconciled externally committed effect blocks the lifecycle, making the credit spend indefensible. When expected marginal discovery value falls below a defensible threshold under this assessment, the cycle MUST be deferred and the defer reason MUST be recorded durably and surfaced in the inspection output. This proportionality gate operates independently of and prior to declared hard-credit budgets: satisfying the hard budget alone does not satisfy the proportionality requirement.

Context and prompt content passed within the URACE system boundary MUST achieve maximum information density without altering normative semantics, state schemas or execution contracts. Context reduction MUST target only redundant prose, verbose structural descriptions and repetitive contextual framing; normative requirements, error boundaries, state lifecycles and exit conditions MUST remain structurally equivalent to their uncompressed definitions. Identifiers, command names, flags, error codes and architectural terms MUST preserve their exact lexical strings so automated parsing and code generation remain unambiguous. Dense list-based or tabular representations are preferred over discursive paragraphs where structural relationships such as state transitions or directory layouts are communicated to an Executor. State persistence fields, fallback hooks and recovery triggers are strictly non-compressible and MUST retain explicit, unabridged attribute declarations in all transmitted or stored representations.

Executor cost versus measurable progress MUST be a core vital in both a short operational window and a longer sustainability window. At minimum it SHOULD expose total metered cost, productive-call yield, accepted changes, cost per accepted change, and associated metric improvements and regressions. Implementations SHOULD use provider-reported token or monetary usage when available and an explicitly labelled call-count proxy otherwise. Cost/outcome association MUST remain `UNATTRIBUTED` unless the ordinary causal-evidence standard is satisfied; this vital guides scheduling and investigation but does not prove that an Executor caused a metric movement.

Discovery-loop yield MUST appear as a named dimension in the efficiency vital. At minimum the vital MUST expose: current unproductive streak count; productive-yield rate — productive discovery calls as a fraction of total discovery calls — over both the short and long accounting windows; active `DISCOVERY_YIELD_EXHAUSTED` status and the configured exhausted-streak threshold; and the earliest qualifying reset condition when the exhausted state is active. This dimension MUST be surfaced continuously regardless of whether `DISCOVERY_YIELD_EXHAUSTED` is currently active; a low but not-yet-exhausted yield rate is a valid early-warning signal that MUST remain visible before the threshold is reached.

Evolution rate MUST also be observable as a core vital, but a single evolution score MUST remain a confidence-qualified diagnostic rather than an optimization target, acceptance criterion or source of Authority. The underlying component vector MUST remain visible and SHOULD cover productive cost yield, accepted-effect rate, regression safety and goal completion, together with outcome-relevant Product metrics where available. It MUST report short and long windows, evidence volume, confidence, rates and cost units. With insufficient Evidence the score MUST be absent or explicitly low-confidence rather than manufactured from defaults.

URACE SHOULD evaluate goals, newly supplied context and performed work against both measurable outcomes and resource cost. Product evolution and URACE self-evolution MUST remain separately visible. Each evaluation MUST preserve the input, Objective or Operation identity; status; relevant cost; observed metric effects; uncertainty; and attribution state. Context usefulness, temporal proximity and metric movement MUST NOT be presented as causal impact without discriminating Evidence. Missing, unchanged or confounded outcomes remain legitimate findings rather than reasons to invent progress.

The evolution evaluator itself MUST be versioned, inspectable and evolvable. Its component definitions, weights, windows, minimum Evidence thresholds and revisions MUST preserve provenance and before/after history. Proposed evaluator changes use the ordinary Objective, Authority, validation and checkpoint lifecycle and MUST be assessed for gaming, proxy drift, comparability loss, observation cost and guardrail weakening. An implementation SHOULD provide a simple immediate inspection surface and a transactional way to revise authorized parameters while autonomous operation is active.

When accumulated Evidence falls below the evaluator's declared minimum threshold for a confident variant selection or rejection decision, the evaluator MUST record the disposition as `INSUFFICIENT_EVIDENCE` — not deferred selection, not provisional promotion. The record MUST identify the specific gap: which Evidence type is absent or below threshold, and by how much relative to the declared minimum. `INSUFFICIENT_EVIDENCE` is the terminal disposition for that evaluation cycle but MUST NOT advance the variant to a terminal lifecycle state such as selection, rejection or promotion. A variant carrying `INSUFFICIENT_EVIDENCE` MAY remain eligible for further observation and reassessment when qualifying Evidence arrives within applicable resource ceilings, and its gap record MUST be preserved as lineage regardless of subsequent disposition.

URACE MUST treat optimality as the best defensible eligible choice under current Evidence, uncertainty, Authority and resource constraints, not as a claim of global or permanent optimality. Eligible Product evolution and eligible URACE self-evolution SHOULD compete in one bounded candidate portfolio using explicit expected value, progress contribution, urgency, confidence, estimated cost, risk, reversibility and learning value. Self-evolution policy is an eligibility gate before ranking and cannot be bypassed by a high score. Fixed scope preference, novelty, implementation size or metric movement alone MUST NOT substitute for this comparison. When close alternatives could materially change the decision, URACE SHOULD preserve the comparison or gather discriminating Evidence rather than presenting an arbitrary choice as optimal.

Where a Product has multiple authorized semantic scopes, URACE MAY dynamically weight planning attention among them using attributable current Evidence such as unresolved need, accepted-change recency, observed outcome gaps, risk or urgency. This is a lifecycle-wide facility: it MAY order ordinary Objectives, queues, Executor attention, experiments or cohort slots, and MUST NOT depend on portfolio support. An implementation MAY map a semantic scope to files, services, components, goals or effect domains, but artifact identity is not the universal scope model. The controller MUST version and expose each scope weight, its inputs, Evidence cutoff, consumer and resulting allocation; bound its influence and rate of change; distinguish attention priority from outcome value; and reassess at a lifecycle boundary. A scope weight MUST NOT grant Authority, weaken a guardrail, alter a fixed budget, award evaluation points, predetermine selection or be writable by the candidates it governs. Supporting cross-scope work remains eligible when required for coherence, and a low-weight scope MUST remain observable so starvation or accumulating debt can raise its priority.

Long-running efficiency MUST include deterministic overhead as well as model credit. Stable readiness probes, failed external sources, unchanged observations, duplicate Plans, checkpoints and durable writes SHOULD use adaptive cadence, caching, deduplication and material-change persistence with a declared heartbeat. Repeated failures SHOULD back off to a bounded maximum while retaining a wake path. Material transitions, accepted effects, queued authoritative input, unresolved effects and recovery data MUST remain durable immediately. Runtime vitals SHOULD expose enough probe, retry, state-size and write-suppression data to detect when the efficiency policy itself is becoming wasteful.

Optimal and efficient operation is a system-wide navigation constraint: URACE SHOULD seek the highest defensible Intent-relative outcome per constrained resource while respecting Authority, safety, quality, continuity and uncertainty. It MUST NOT optimize cost by omitting necessary validation, optimize throughput by accepting weak work, or optimize a score instead of the Product. Quantitative Evidence SHOULD replace qualitative judgment where the measure is valid, decision-relevant and proportionate; qualitative Evidence MUST remain visible where quantification would create false precision, omit material values or cost more than the decision warrants.

Lifecycle rigor MUST remain proportionate to actual conditions and Evidence. URACE SHOULD reuse persistence, accumulated Evidence, recovery, Executor replaceability, competing alternatives, lineage and dormancy/reactivation when they materially improve continuity, decision quality or retained Product outcomes, and SHOULD prefer simpler sufficient behavior otherwise. This requirement prescribes no complexity threshold, algorithm, topology, cadence or implementation mechanism.

URACE SHOULD periodically identify resource sinks, including repeated no-effect work, unused context or connectors, stale goals, uninformative metrics, redundant reports, retry loops, oversized prompts, excessive state or documentation growth, premature self-evolution and observation whose cost exceeds its decision value. It SHOULD remove, compact, defer or redesign a sink when authorized and safe, while preserving material history, recovery Evidence and a wake path. Resource-sink findings and corrective effects MUST be measurable and reviewable rather than inferred from artifact size alone.

The discovery loop is a named and required resource-sink category that MUST be evaluated independently of other sink categories. An unproductive discovery streak that has reached or exceeded the declared `DISCOVERY_YIELD_EXHAUSTED` threshold is a confirmed active resource sink and MUST be reported as a distinct named entry in the resource-sink surface — not as a latent concern, a potential candidate, or an inference from indirect cost signals. The entry MUST identify the streak count, the exhausted-threshold value, the configured ceiling dormancy interval, and the earliest qualifying reset condition. An unproductive streak that has not yet reached the threshold but has consumed a material fraction of the applicable discovery budget over the accounting window SHOULD also be surfaced as an early-warning entry when the observed productive-yield rate falls below a defensible efficiency floor, clearly distinguished from a confirmed exhausted condition.

Where multiple competing Product variants are justified, URACE MAY operate a bounded portfolio experiment. Variants MUST use isolated mutable environments derived from an attributable baseline, explicit per-variant and portfolio resource ceilings, predeclared outcome measures and guardrails, comparable evaluation conditions, and stopping rules. Irreversible or identity-bearing external effects MUST NOT be duplicated across competing variants merely to create selection pressure. Selection MUST account for uncertainty, confounders, delayed effects, multiple comparisons, survivor bias and the possibility that no variant is superior. A selected variant remains a candidate until it passes ordinary Authority, validation, concurrency, transactional acceptance and recovery requirements.

A portfolio interface MAY offer one cohort Operation that creates and runs a declared number of mutations. Before producing effects, it MUST validate the complete plan, unique identities, lineage, lessons, admission ceiling and total budget. It MUST divide the declared budget by an explicit reproducible rule, expose each allocation and unit, and run candidates under comparable time and evaluation conditions. Admission SHOULD be all-or-none when the environment can provide transactional creation. Equal declared allocations MUST NOT be described as hard isolation unless an adapter enforces the relevant CPU, memory, network, storage, accelerator, paid-service and effect quotas. Unenforced units remain labelled declarations, and an implementation without concurrent isolation SHOULD serialize evaluation or make the confounding visible.

A variant is an isolated candidate; an instance is an executing realization of a variant. Stopping an instance MUST stop its resource consumption and effects without erasing its lineage, observations or failure Evidence. A selected variant MAY seed later mutations, but URACE MUST prevent convergence from silently discarding useful diversity or turning a context-specific result into a universal claim. Automatic spawn, health supervision, termination and mutation require explicit portfolio Authority, tested lifecycle adapters, hard concurrency and exposure ceilings, effect isolation and recoverable control; otherwise these Operations remain manual or unavailable.

An active-variant or active-instance ceiling MUST count the candidates or realizations currently admitted to compete or consume bounded execution resources. A retained selected parent used only as an immutable lineage seed MUST NOT consume a child-cohort competitor slot; if that parent also executes or competes, it MUST be counted. The implementation MUST expose which entities consume the ceiling so retention cannot silently reduce a declared cohort or permit excess execution.

Portfolio state MUST distinguish a shared read-only experiment contract, a reproducible generation snapshot and variant-local mutable state. The contract includes Objective, Authority, constraints, measures, guardrails, budgets, evaluation and stopping rules. The snapshot identifies the base Product version, context and Evidence cutoff, dependencies, configuration, test-data identity, randomness and material Executor/tool versions. Variant-local state includes lineage, mutation, hypothesis, expected effect, workspace, process, writable data, endpoints, logs, scoped credentials, observations and resource use. Competing instances MUST NOT share writable Product state, cohorts or effect identifiers where cross-contamination could invalidate measurement or duplicate consequences.

Each lineage record MUST distinguish base, mutation, generation, parent variant, parent Product version, mutation description, hypothesis, expected effect and experiment-contract version. Selection MUST retain the full candidate comparison and give each candidate an attributable disposition and plain rationale, including guardrail rejection, insufficient Evidence, non-selection, retention for diversity or selection. Non-selection MUST stop further automatic resource consumption unless explicitly retained, but MUST NOT erase the candidate or imply universal inferiority.

Cross-variant communication MUST pass through a governed broker, ledger or equivalent mediation boundary. A variant MAY submit attributable observations, critiques, counter-Evidence and hypotheses about approved peer artifacts or prior versions, but peer content remains untrusted advisory Evidence. A candidate process MUST have no filesystem, database, credential, administrative API or general command access to the authoritative ledger, integrity key, controller state, other candidates or stable recovery data. It receives only a scoped readable snapshot and a bounded submission channel whose controller independently authenticates identity, validates schema and appends accepted messages. It MUST NOT directly command, mutate, stop, authorize, fund, credential, select or promote another variant; modify the shared contract or ledger; expand its own scope; or turn peer content into executable instruction without ordinary assessment and Authority.

A shared portfolio decision forum or agora MAY collect attributable proposals and votes. Ledger writes MUST be mediated, durable and append-only or transactionally replaced; variants receive approved readable views and MUST NOT rewrite votes, proposals, decisions or peer records directly. Admission determines voting identity. Each admitted variant MUST have at most one equal effective vote per proposal, with revisions preserving superseded history. Confidence MUST NOT multiply vote weight. The tally MUST expose support, opposition, abstention, participation, eligible population and material dissent. Votes remain advisory Evidence: they MUST NOT grant Authority, select or promote a variant, change a budget or contract, mutate Product state, or make a proposal executable.

An automatic portfolio MUST freeze a versioned experiment constitution before its first effect. The constitution MUST include Intent and Authority boundaries, primary metric and direction, guardrails, evaluation protocol, admission and identity rules, cohort size, equal-allocation method, planning and per-variant hard ceilings, vote eligibility and quorum, selection and tie rules, isolation requirements, audit lineage, stop and revocation controls, and interruption recovery. A candidate, peer message, vote, selected lineage or portfolio-system mutation MUST NOT change these fields inside that experiment. A proposed change requires independent ordinary URACE assessment and a new attributable experiment identity. Implementations MUST reject an altered workflow instead of accepting it at an idle generation boundary.

Agora and cross-variant inputs MUST use strict schemas, bounded text and content classification as untrusted advisory Evidence. Eligible voters MUST be limited to the admitted comparison cohort; retired or cheaply created historical identities MUST NOT accumulate voting power. Integrity-sensitive ledgers SHOULD use canonical encoding and a collision-resistant append chain binding experiment identity, monotonic sequence, record type, prior digest and payload digest. Where poisoning resistance matters, an authenticated anchor using a MAC, digital signature or an equivalently protected transparency service MUST be held outside candidate control. Implementations MUST verify before consuming or extending the chain; reject truncation, reordering, replay, forks, malformed records and authentication failure; preserve the suspect material; and fail closed for selection or promotion. Key identifiers and rotation transitions MUST be attributable, while private keys and MAC secrets MUST NOT enter candidate environments, prompts, ordinary logs or shared ledgers. Candidate confinement MUST be tested before every unattended launch and after material environment changes; a declaration or cryptographic seal alone is insufficient. If the candidate can address ledger storage or the trust root, automatic mutation, evaluation, voting, selection and promotion MUST remain unavailable. Multi-tenant or hostile deployments MUST additionally authenticate writers, authorize each operation, isolate secrets and effects, and protect the ledger and trust root outside candidate operating-system identities. Cryptographic integrity MUST NOT be represented as truth validation, safe content, confidentiality, Authority, or protection against an actor that controls both the ledger and its trust root.

An attributable controller MUST record whether a proposal is adopted, deferred or rejected and preserve its rationale, Evidence, counter-Evidence, applicability, tally and applicable guardrails. Adoption requires participation by at least half of admitted variants, declared minimum support and strictly more support than opposition, and MUST NOT rely on popularity alone. An adopted decision MAY survive cycle boundaries as an inheritance candidate. It MUST identify the selected parent for which inheritance was approved, and each child MUST explicitly link the decision before consuming it. Inheritance MUST preserve provenance and MUST remain subject to the child's context, Authority, validation and current Evidence; it MUST NOT silently become a universal rule or bypass reassessment.

A long-running portfolio controller MAY automate repeated planning, candidate creation, mutation, evaluation, selection and archival. It MUST persist a workflow identity, generation identity and phase boundary before advancing; resume an incomplete generation rather than silently duplicating it; scope comparison to the current declared cohort; and make the selected candidate the attributable lineage parent of the next generation. Before new-generation effects, it MUST compare that lineage parent with the latest accepted Product state and durably reconcile any advance at a safe boundary: preserve attributable learning, incorporate newer accepted work, retain only compatible experimental state, and reassess stale mutations without overwriting the accepted Product. An unresolved conflict MUST block only dependent work rather than be guessed through, and reconciliation MUST NOT alter the frozen experiment constitution. Candidate mutations MUST be isolated and committed or equivalently snapshotted before evaluation. Evaluation MUST use a declared machine-readable result contract, remain read-only with respect to the candidate, and report metric value, guardrails, Evidence volume and resource cost. A model judgment alone MUST NOT be represented as an observed outcome.

A persistent controller MAY request bounded self-repair after attributable repeated identical controller defects, but MUST route the proposal through ordinary self-evolution eligibility, isolation, validation, transactional activation, restart and stable rollback. Repair eligibility and prompts MUST derive only from controller-generated fault codes, trusted control location, exception class and accepted runtime identity. Cohort, candidate, peer, metric, Executor, connector, external-source and raw exception-message content MUST NOT authorize, parameterize or enter a repair request. Executor unavailability, capacity exhaustion, failed isolation, integrity or constitution checks, missing Authority and external-effect uncertainty MUST remain fail-closed conditions rather than repair authorization. Repair attempts MUST have durable ceilings and MUST resume the prior checkpoint without reopening consumed budgets.

Eligible controller repair MUST use one system-wide protocol and registry across the core lifecycle and optional subordinate controllers. A repair identity MUST bind the trusted fault descriptor to the accepted runtime version. Replaying the same identity MUST return its durable disposition rather than create another Objective, spend another repair allowance or apply another candidate. A changed accepted runtime creates a new attributable identity, so recurrence after an attempted fix may be assessed without pretending that two different runtime versions are the same operation.

Recovery state MUST distinguish a current unresolved failure, a repair request, validation or activation in progress, successful recovery, failed repair and no repair needed. Successful completion of the affected checkpoint MUST clear the current-error indication and reset its consecutive-failure signal while retaining the prior failure and repair disposition as historical Evidence. Human-readable and machine-readable feedback MUST expose the current recovery state and applicable attempt use without presenting a resolved error as current.

Long-running portfolio budgets MUST distinguish wall time, deterministic resources, controller-level Executor invocations and provider-reported usage. A declared generation-level Executor-invocation budget MUST be divided equally among variants and reserved durably before each attempt so failure or interruption cannot reopen it. Planning MUST have a separate hard attempt ceiling. An adapter that can issue multiple provider calls inside one controller invocation MUST enforce its own call, token and monetary ceilings; hidden consumption MUST NOT be called hard-capped merely because the outer process count is bounded. Finite `X` generations and persistent `infinity` operation MUST use the same per-generation ceilings, backoff and stopping invariants.

Resuming an interrupted stage MUST reuse its durable logical reservation. Exhausting an orchestration or Executor-invocation cap makes unevaluated dependent work incomplete; it MUST NOT by itself imply candidate failure, guardrail failure, metric value or safety/effectiveness Evidence. Any later attempt requires a separately eligible controller-authorized unit rather than an erased or silently enlarged reservation.

Interruption recovery MUST distinguish incomplete mutation from accepted mutation. An incomplete isolated candidate MAY be reset to its recorded parent and retried when its external effects are absent or independently idempotent; unresolved external effects MUST block retry pending reconciliation. Repeated failures MUST back off and eventually pause under a declared ceiling while retaining a wake path. Generation and worktree retention MUST be bounded for long-run operation, while lineage, selected commits, measurements, failures and selection dispositions remain durably archived. Infinite operation MUST retain applicable task, stage, generation and candidate budgets, resource-sink detection, stopping rules, dormant or paused states and operator revocation; `infinity` MUST NOT mean unbounded Authority, concurrency, per-stage resources or retries. Optional rolling transport ceilings MAY be explicitly disabled when the remaining bounds and provider controls are sufficient and observable.

When live authenticated records are bounded or archived, each closed archive segment MUST retain its schema, experiment identity, range or sequence boundary, prior/current chain anchors, digest and authentication proof. Verification MUST cover the live ledger and retained archive segments before unattended launch and on demand. Pruning MUST NOT silently sever provenance or convert an unverified archive into trusted Evidence.

Accepted Product state and inherited portfolio knowledge MUST remain separate: selection implies neither acceptance nor extinction. Descendants MAY inherit attributable validated observations, constraints, reproducible failures, negative lessons and uncertainty-qualified hypotheses from selected, non-selected or diversity-retained lineages without inheriting their Product state. Reusable learning MUST preserve source variants, supporting and counter-Evidence, epistemic status, confidence, applicability and materially relevant correlation or dependency; votes, arguments, predictions, peer conclusions, repetition and consensus remain advisory until independently substantiated. A controller or attributable authorized source MUST approve inherited context, but inheritance or consensus MUST NOT make an unvalidated claim authoritative, while diversity retention MUST NOT imply superiority. The controller retains non-delegable admission, identity, contract, budget, capability, communication, stopping, selection, promotion, revocation and audit enforcement. Deployments with mutually untrusted instances MUST add authenticated identities, access controls, tamper-evident events, quotas, secret isolation and network/effect segmentation proportionate to risk.

Product evolution MUST remain each variant's primary Objective. A variant MAY propose portfolio-system evolution only when it supplies Evidence that a controller limitation makes change necessary, the proposed effect benefits the experiment as a whole, and selection, Authority, admission, equal budgets, isolation, validation, recovery, audit and revocation invariants remain at least as strong. Peer support MAY refer the proposal for independent review but MUST NOT authorize or enact it. Portfolio-system evolution proceeds only through the ordinary applicable URACE self-evolution policy, isolated validation, rollback and Authority boundaries. It MUST NOT under-privilege safeguards, under-escalate material failure, weaken selection pressure, favor the proposer, expand Authority or consume candidate inheritance as executable instruction.

A proposer MAY receive a bounded contribution bonus only after the system change is independently implemented, validated and shown to benefit the whole experiment without weakening an invariant. The bonus MUST be visible, capped and subordinate to Product outcomes: it MAY break an exact primary-metric tie but MUST NOT overcome a worse primary metric, failed guardrail, insufficient Evidence, higher-priority risk or budget violation. A proposal, vote or referral alone earns no bonus.

When portfolio evolution is supported, the operator surface SHOULD make baseline, lineage, active variants and instances, budgets, observations, guardrails, rankings, selection confidence, stopped status and promotion status inspectable. It SHOULD provide environment-appropriate create, spawn, run, observe, rank, select, stop and status Operations through safe immediate controls or durable lifecycle inputs.

The portfolio feedback surface MUST provide a concise human-readable view and a stable machine-readable view without invoking an intelligent Executor or changing lifecycle state. The human view MUST identify current status and phase, generation and completed-cycle count, selected parent and next step, planner and per-variant hard-budget use, metric and guardrail results, Evidence volume, agora decisions, latest failure and material isolation or provider-metering limitations. Parent feedback MUST distinguish its own idle state from active delegated work and MUST NOT label the overall system dormant while a subordinate controller is actively planning, executing or validating. Completed automatic generations SHOULD emit this summary. Implementations SHOULD provide discoverable command help and MAY provide memorable aliases for persistent operation and one generation, but aliases MUST map visibly to the explicit stable Operations rather than creating different semantics.

Before unattended portfolio execution, an implementation MUST offer a read-only preflight that validates workflow schema and identity, installed adapters, frozen constitution, equal allocations, controller ceilings, adapter-level provider ceilings, evaluation protocol, isolation and external-effect reconciliation. A one-command persistent entry MAY run that preflight and continue only on success. A configuration assertion MUST NOT substitute for testing hidden adapter behavior. Re-bootstrap is justified only when the installed implementation lacks a required capability and a smaller validated repair is insufficient.

Consequential commercial operation MUST preserve a named accountable operator, applicable jurisdiction and obligations, least-privilege credentials, explicit effect permissions, hard exposure limits, transaction and communication records, independent reconciliation, staged activation, anomaly stops and revocation paths. Documentation or autonomous execution MUST NOT be interpreted as transferring the operator's legal, contractual, tax, regulatory, employment, consumer-protection, privacy or professional responsibilities to URACE, its specification or its contributors.

URACE MUST NOT claim or imply that a command, Executor, metric, experiment or indefinite operation guarantees income, revenue, profit, demand, legality or another external outcome. Convenience of activation MUST remain distinct from outcome uncertainty. License permissions, warranty disclaimers and liability limitations do not create operational Authority, satisfy applicable obligations or guarantee immunity from liability.

An implementation MUST provide an on-demand inspection interface for progress metrics, metered Executor usage, short-run and long-run efficiency vitals, lifecycle health, external-evidence health and the next follow-up. It SHOULD offer both a plain human view and a stable machine-readable view, and reading it MUST NOT invoke an intelligent Executor or mutate lifecycle decisions. Bootstrap completion instructions MUST name the exact environment-specific command, API or screen used to access these vitals.

A metric is an observed measure; a vital is a health, progress, efficiency or risk interpretation derived from named metrics or durable state; a score is a versioned decision aid derived from disclosed measures or vitals. Implementations MUST preserve these distinctions and expose component inputs, units, source, window, weights, coverage and confidence. A system-wide aggregate MUST be withheld when required dimensions or confidence are missing or a guardrail veto applies. An aggregate MUST NOT grant Authority, establish causation, accept a change or mask a failed component.

An implementation MAY export a portable analytics view for human analysis. The export MUST be derived and observational: canonical control state MUST NOT depend on a spreadsheet, workbook, dashboard or user edit. Bootstrap MUST expose an attributable `DISABLED`, `ON_DEMAND` or `ON_CHECKPOINT` export policy and use `DISABLED` when no selection is supplied. A portable bundle SHOULD include interoperable tabular data, a self-contained human-readable dashboard, schema and state versions, generation or checkpoint identity, timestamps, coverage, staleness information and content hashes. Native workbook formats MAY be optional adapters. Untrusted cells MUST be escaped against spreadsheet formula execution. Export failure or absence MUST NOT block lifecycle operation, and any control change inspired by the report MUST return through the ordinary command or durable-input boundary.

Portable export readiness and native-workbook readiness MUST be reported as separate capabilities. An implementation MUST NOT advertise a native workbook as ready merely because a portable export exists. Bootstrap MUST detect each optional adapter rather than assume it, report `READY` or `ADAPTER_REQUIRED`, name the environment-specific dependency and exact enablement path in its local report, and keep the portable export fully usable when the adapter is absent. Requesting an unavailable native format MUST fail clearly without replacing the last successful report bundle or changing canonical state. Installing or upgrading an optional dependency remains an ordinary authorized environment change, not an implicit side effect of report generation.

## Live Authoritative Input and Extensible Observability

The authoritative source MUST be able to add context, goals, metric definitions, vital definitions and external-source descriptions while URACE is active, dormant or stopped. Implementations MUST accept these inputs through a durable, atomic inbox or an equivalent transactional boundary rather than requiring unsafe direct state edits. Acceptance MUST acknowledge durable receipt; application MUST occur at a lifecycle boundary, be idempotent across interruption and restart, preserve provenance, and prevent partial input from corrupting accepted state. Malformed input MUST be rejected or quarantined without blocking unrelated lifecycle work.

New context MUST become attributable Evidence and MAY Trigger reassessment; it MUST NOT silently replace retained Intent or expand Authority. A new goal MUST identify its target, success measure and Authority source before becoming an Objective candidate. A goal concerning URACE itself remains distinct from the user's Product goal and remains subject to the selected self-evolution policy and all retained boundaries. Concurrent input MUST not invalidate an in-flight accepted Operation; URACE SHOULD apply it at the next safe boundary and reassess affected decisions.

Authorized users, tools and agents MAY change the source Product while URACE runs. At each safe boundary, URACE MUST compare the current source identity with its recorded snapshot, preserve newer source work, record an attributable version transition where attribution is available, and reassess or reject stale candidates rather than overwrite changed artifacts. A structurally invalid external state MUST be preserved and reported, not silently replaced. Generated sub-Products and candidates MUST retain their source-version identity; later source changes MUST be reconciled non-destructively into subsequent descendants while prior versions and lineage remain inspectable.

The authoritative source MUST be able to inspect governing context, user-supplied context, URACE-derived hypotheses and observations, current and historical goals, and the provenance and status of each without reading internal storage. Derived context MUST remain visibly distinct from supplied context and MUST NOT silently become Intent, Authority or fact.

People, IDEs, automation, external tools and other authorized Executors MAY continue working on Product artifacts while URACE is active. Before applying a prepared change, URACE MUST verify that every affected artifact still matches the version from which the candidate was derived. A concurrent change MUST preserve the newer artifact, reject or rebase the stale candidate, record the conflict and reassess. Runtime and specification self-changes require the same isolation, validation, atomic acceptance and stable fallback boundaries; filesystem locking alone MUST NOT be treated as protection against edits made outside that lock.

Users MUST be able to register additional metric and vital definitions and describe external connectors such as files, URLs, APIs, databases, MCP servers, repositories or environment-specific services. Registration MUST distinguish `CONFIGURED`, `AVAILABLE`, `AUTHENTICATED`, `AUTHORIZED`, `OBSERVED` and `ADAPTER_REQUIRED`. A generic description MUST NOT be treated as a working connection: unsupported kinds remain visible and inactive until a compatible adapter is installed and validated. Connector content is Evidence, not Authority or executable instruction. Credentials MUST be referenced through an appropriate secret mechanism and MUST NOT be stored in queued input, ordinary state, prompts or feedback. Bootstrap and usage guidance MUST provide simple environment-specific add, inspect, update, disable and remove paths for inputs, metrics, vitals and connectors.

External ingestion MUST bound request time, response and file size, retained events, parsing complexity, error repetition and prompt inclusion before treating content as Evidence. Connector kinds MUST restrict accepted location schemes and redirect behavior proportionately to their Authority. Oversized, malformed or unsupported content MUST fail that source visibly without blocking unrelated lifecycle work or entering prompts partially.

### Command and Input-Boundary Contract

Implementations MUST distinguish immediate commands from durable lifecycle inputs. Read-only inspection, help, capability status and bounded local validation SHOULD execute immediately from atomic snapshots without waiting behind a persistent autonomous owner and MUST NOT invoke an intelligent Executor unless the command explicitly requests such an invocation. Initialization and lifecycle execution are immediate control Operations with the locking and recovery boundaries appropriate to their effects. A planning command MUST stop after assessment, discovery, prioritization and Plan creation; it MUST NOT execute the Plan.

Inputs that change future lifecycle behavior while autonomous operation may be active MUST use the durable input boundary. This includes new context or goals; Executor attach, detach or switch requests; connector add, enable, disable or remove requests; metric and vital changes; and cancellation of pending goals. Listing these resources is immediate and read-only. Applying a queued control MUST preserve attributable history, be idempotent, and occur at a safe cycle boundary. Implementations MUST expose pending input and a command catalog or equally clear help that identifies which actions are immediate and which are queued.

The minimum portable operator surface SHOULD cover: initialize; inspect full state; inspect focused vitals; inspect the evolution evaluator and its confidence-qualified component results; inspect command classification; inspect pending input; assess and plan without execution; run bounded or persistent autonomous execution; inspect, attach, detach and switch Executors; inspect and change autonomy policies, metered budgets and authorized evaluator parameters; add context and Product or URACE goals; list and cancel eligible goals; add and list sources, metrics and vitals; enable, disable and remove sources; remove metric and vital definitions; safely download, explain, apply and resolve specification updates; and obtain human-readable and machine-readable inspection output. Environment-specific names MAY differ, but bootstrap completion guidance MUST map every supported Operation to its exact command, API or screen and report unsupported Operations rather than leaving the user to guess.

Every generated implementation MUST provide a discoverable top-level help surface and contextual help for each supported Operation. Help MUST be available without an intelligent Executor call and MUST identify: the installed Operations and memorable aliases; required and optional inputs; safe examples; immediate versus durable-input behavior; human-readable and machine-readable inspection forms; capability or adapter prerequisites; unsupported Operations; and where advanced recovery or deployment guidance resides. A command-line implementation SHOULD support shapes equivalent to `help` and `help <operation>`; APIs and graphical interfaces MAY provide an equally direct operation catalog. Bootstrap MUST demonstrate the help surface and report its exact entry point.

A generated command-line interface SHOULD use the repository-scoped `urace <operation>` shape. Where specification updates are supported, it SHOULD expose stable `urace update download`, `explain`, `apply` and `resolve` operations with the semantics defined by the update lifecycle. An accepted update MUST preserve existing supported command calls, aliases, queued inputs and checkpoint identities, or provide tested compatibility forwarding through a declared deprecation interval. A directory migration MUST keep the accepted command surface active until the new launcher passes health confirmation; it MUST NOT require the new layout merely to download, explain, apply, resolve or roll back that migration.

The default help view SHOULD be a short user-facing operation list rather than a parser grammar dump; internal controller Operations SHOULD be omitted. Configuration controls SHOULD be discoverable through one configuration surface, with memorable aliases permitted for frequent policies. Where self-evolution is configurable, user-facing `auto`, `always` and `never` aliases SHOULD map explicitly to necessary-only, continuous and disabled semantics without weakening protected invariants.

The inspection surface SHOULD also expose a provenance-separated context view and a resource-accounting view that names the unit, source and confidence of each quantity. Human feedback SHOULD favor dense decision-relevant summaries and progressive disclosure: current work, why it was selected, relevant alternatives, resources consumed, observed effects, uncertainty, validation, next condition and material limitations. It MUST NOT require hidden chain-of-thought, flood the user with unchanged detail or imply certainty through verbosity. When the most recent lifecycle assessment could not complete because Evidence was absent or below threshold, the inspection surface MUST expose: (a) the specific Evidence dimension that was missing or insufficient; (b) a quantified shortfall where determinable — for example, minimum required observations versus observations available; (c) whether lifecycle advancement is currently blocked pending that Evidence; and (d) the earliest condition or qualifying Event that would allow reassessment to proceed. Reporting only that an aggregate is withheld MUST NOT substitute for these four fields. An implementation MUST NOT present a stale confident assessment as current when the active assessment cycle was Evidence-blocked.

Repeated requests, failures, audits, corrections and synchronization work SHOULD become durable pattern Evidence. Once recurrence is credible, URACE SHOULD address the generating condition, encode a reusable check or policy, or explain why repetition remains appropriate. Pattern detection MUST remain bounded and interpretable; it MUST NOT manufacture patterns from weak coincidence or turn every repetition into permanent machinery.

Reasoning memory SHOULD represent reusable hypotheses rather than raw hidden reasoning. Each retained pattern SHOULD include supporting Evidence, counter-Evidence, calibrated confidence, applicability boundaries, last observation, and a concise learned response. It SHOULD be revised, weakened, retired or contradicted as new Evidence arrives. Storage MUST be bounded by value-aware retention so a reasoning-memory feature does not itself become unbounded bloat.

Canonical:

```text
SOURCE
    CHOOSES WHAT IT RETAINS

INTENT
    SETS DESTINATION

AUTHORITY
    SETS BOUNDARY

EVIDENCE
    DESCRIBES REALITY

URACE
    NAVIGATES

PRIORITY
    ORDERS

PLANS
    ROUTE

EXECUTORS
    ACT

VALIDATION
    ACCEPTS

LIVENESS
    CONTINUES
```

---

# 72. Safety, Constraints and Policy

HARD constraints MUST NOT be overridden.

Policy governs where applicable:

- prohibited actions;
- reserved decisions;
- approvals;
- budgets;
- external interaction;
- privacy;
- risk;
- self-modification;
- delegation;
- termination.

Policy SHOULD constrain autonomy, not replace it.

Where policy establishes a boundary while leaving choices open, URACE SHOULD choose autonomously.

---

# 73. Recovery

Recovery SHOULD reconstruct:

- Product;
- Authority;
- delegation;
- retained decisions;
- autonomous scope;
- Intent;
- governing destination;
- Evidence;
- assessments;
- Triggers;
- Objective;
- Priority basis;
- Plan;
- Decision Records;
- Operations;
- unresolved effects;
- validation;
- checkpoint;
- capacity;
- dormant/wake state;
- constraints;
- uncertainty.

Recovery SHOULD resume autonomous navigation without requiring previously durable Authority or Intent to be restated.

Recovery MUST reconcile any interrupted acceptance protocol before treating Product artifacts and lifecycle state as mutually consistent.

Where durable state establishes that an interrupted change was accepted, recovery SHOULD complete the accepted state. Where acceptance was not durably established, recovery SHOULD restore the prior accepted state or explicitly preserve uncertainty when restoration cannot be established safely.

When a recovery attempt is itself interrupted before completing reconciliation — through crash, resource exhaustion or abrupt process termination — the subsequent restart MUST treat the partial recovery as an additional `INDETERMINATE` boundary rather than continuing from the partially-recovered state as if it were the accepted baseline. A partially-recovered lifecycle state MUST NOT be treated as equivalent to the last accepted state; the boundary between the accepted state, the interrupted recovery attempt and the current artifact set MUST be re-established through a fresh reconciliation pass from the last durable accepted checkpoint. URACE MUST preserve the interrupted recovery's own durable record — including which reconciliation steps completed and which did not — so that repeated recovery interruptions cannot silently compound ambiguity about the accepted baseline. Recovery MUST NOT recurse indefinitely: when an implementation detects a recovery-of-recovery chain exceeding a bounded depth, it MUST surface this as a named material blocking limitation requiring operator intervention rather than attempting an additional automated recovery pass.

---

# 74. Conditional Self-Evolution

URACE MAY autonomously discover that evolving its own implementation is a justified way to better advance governing Intent.

Bootstrap MUST establish and durably preserve one explicit runtime self-evolution policy:

```text
DISABLED
    runtime self-evolution and re-bootstrap are ineligible

NECESSARY_ONLY
    eligible only to address a demonstrated material limitation that
    blocks, degrades or endangers Product progress, integrity or continuity,
    where no sufficient lower-impact Product route exists

CONTINUOUS
    justified beneficial runtime improvements may compete with Product work
```

`NECESSARY_ONLY` SHOULD be exposed as `auto` and used by default. It creates no Authority: self-evolution still requires applicable delegated Authority, demonstrated necessity and absence of a sufficient lower-impact route, and MUST NOT make protected invariants mutable. `CONTINUOUS` MAY be exposed as `always` and `DISABLED` as `never`. The authoritative source MAY change modes through an attributable policy change within its Authority. The selected mode MUST be inspectable in durable lifecycle state and included in recovery.

The policy is an additional eligibility boundary; it MUST NOT create Authority. An action proceeds only when both the selected mode and independently attributable Authority permit it. `DISABLED` MUST prevent autonomous runtime self-evolution and re-bootstrap Objectives without preventing ordinary Product evolution, diagnosis, or reporting of a URACE limitation. `NECESSARY_ONLY` MUST preserve Evidence supporting necessity, materiality, and the absence of a sufficient lower-impact route. `CONTINUOUS` MUST still require justification, prioritization, validation, safe activation, and proportionality.

At recovery, if the self-evolution policy mode cannot be established from durable state due to missing, corrupted or unreadable policy records, the implementation MUST treat the mode as `NECESSARY_ONLY` and MUST surface this as a material blocking limitation pending explicit operator confirmation. It MUST NOT infer a prior `CONTINUOUS` or `DISABLED` mode from Executor suggestion, operational context, or the most recently observed behavior. The recovered mode MUST be attributable and inspectable; autonomous self-evolution or re-bootstrap Objectives MUST NOT proceed under an inferred mode.

When recovery finds multiple conflicting self-evolution policy records in durable state — for example, a readable `CONTINUOUS` record predating a subsequent record that is corrupted, absent or structurally unreadable — URACE MUST apply the most restrictive resolvable mode among the conflicting records rather than treating the most recent readable entry as authoritative. An ambiguous policy state MUST surface as a named limitation in the inspection output, and autonomous self-evolution or re-bootstrap Objectives MUST NOT proceed until the ambiguity is resolved through an explicit operator-confirmed policy re-establishment. Applying the most restrictive available mode under ambiguity is not equivalent to the `NECESSARY_ONLY` default under complete absence: the conflicting records constitute a known partial policy-change sequence, and the restriction MUST remain visible as ambiguous rather than being recorded as a confirmed policy selection. Where the ambiguity cannot be resolved from durable evidence alone, the implementation MUST expose an authorized command to confirm, revise or clear the policy to a known attributable state; it MUST NOT silently promote the most restrictive available mode to permanent status without operator confirmation.

Where the selected policy and applicable Authority permit, URACE MAY promote that self-evolution into an Objective, prioritize it against Product work, plan it, execute it through capable replaceable executors, validate it, checkpoint accepted change and continue operating without requiring a new authoritative request.

Self-evolution remains subject to the ordinary lifecycle:

```text
DISCOVER LIMITATION / OPPORTUNITY
            │
            ▼
     ASSESS JUSTIFICATION
            │
            ▼
      RESOLVE AUTHORITY
       ┌────┴────┐
       ▼         ▼
 AUTHORIZED   NOT AUTHORIZED
       │         │
       ▼         ▼
   OBJECTIVE   PRESERVE
       │       BOUNDARY
       ▼
   PRIORITIZE
       │
       ▼
      PLAN
       │
       ▼
     EXECUTE
       │
       ▼
     VALIDATE
       │
       ▼
   CHECKPOINT
       │
       ▼
    REASSESS
```

Autonomous initiation MUST NOT be confused with self-authorization.

Self-modification MUST NOT:

- create Authority;
- expand Authority;
- broaden delegation;
- override retained Intent;
- weaken or remove protected constraints;
- bypass required validation;
- silently redefine the governing destination.

Three evolution scopes MUST remain distinguishable:

```text
PRODUCT EVOLUTION
    changes the governed Product

RUNTIME URACE SELF-EVOLUTION
    changes the running URACE implementation

URACE.md SPECIFICATION EVOLUTION
    changes the authoritative bootstrap specification
```

Authorization for one scope MUST NOT imply authorization for another.

In particular, Authority to evolve the Product or the running URACE implementation MUST NOT by itself authorize modification, replacement or evolution of `URACE.md`.

`URACE.md` MAY be modified by an autonomous URACE only where applicable Authority explicitly delegates specification evolution at that scope.

Evidence that changing `URACE.md` would be useful MAY justify proposing or prioritizing such a change where applicable, but Evidence MUST NOT create the Authority required to perform it.

Changing `URACE.md` does not automatically mutate a running URACE implementation.

A running URACE evolving itself does not automatically rewrite `URACE.md`.

Normal Product evolution and authorized runtime self-evolution MUST NOT require re-bootstrap merely because they occur.

## Safe Runtime Activation

Runtime self-evolution MUST NOT overwrite the only runnable implementation before the candidate is independently validated.

Where a running process cannot safely replace and restart itself, a smaller stable activation capability, parent launcher or equivalent handoff mechanism MAY remain outside the replaceable runtime. That mechanism MUST remain bounded to activation, health determination, rollback and restart responsibility; it MUST NOT acquire Product-lifecycle navigation ownership.

An implementation supporting autonomous runtime evolution MUST retain a minimal protected evolution kernel outside ordinary candidate mutation. At minimum, it MUST protect activation and rollback control, the independent acceptance guard, the accepted-test baseline, repair-identity and replay rules, and the Authority, isolation, integrity and resource invariants that govern evolution. A candidate MUST NOT change that kernel, add it to its own mutable allowlist, replace its accepted validator, or validate a change solely with tests it may edit in the same increment.

Before activation, the previously accepted guard MUST evaluate the candidate with both the candidate's tests and the previously accepted independent tests. The activation controller MUST repeat the independent guard after application and before starting the candidate. Changes to the protected kernel require a separate attributable operator-controlled bootstrap or equivalent independently governed upgrade; ordinary Product evolution, runtime self-evolution, self-repair, a portfolio winner or re-bootstrap MUST NOT approve changes to its own judge.

An authorized runtime candidate SHOULD:

1. be prepared outside the active runtime;
2. preserve the authoritative specification and durable lifecycle state;
3. pass applicable behavioral, compatibility and state-loading validation;
4. preserve the current accepted runtime as a stable fallback;
5. cross a crash-consistent activation boundary;
6. restart or hand off into the candidate;
7. demonstrate post-activation health before replacing the stable fallback;
8. restore and restart the prior stable runtime if import, startup, state compatibility or health validation fails.

Process termination during preparation or activation MUST be reconciled before another runtime candidate is attempted.

## Re-Bootstrap

Re-bootstrap reconstructs a candidate runtime from the authoritative specification and applicable deployment context. It is justified only when reconstruction has greater expected value than incremental runtime evolution, such as material architectural divergence, irreparable implementation drift, technology replacement or inability to satisfy new mandatory requirements safely in place.

Re-bootstrap is governed by the same self-evolution policy. It MUST NOT bypass `DISABLED` or the necessity test in `NECESSARY_ONLY` merely because reconstruction is technically available.

Re-bootstrap MUST preserve Authority, governing Intent, accepted Product artifacts and durable lifecycle state. The reconstructed candidate participates in the same isolated preparation, validation, activation, health confirmation and stable rollback protocol as incremental runtime self-evolution.

Re-bootstrap MUST NOT become a way to discard inconvenient history, reset Authority, bypass migration, or reinterpret the authoritative specification.
---

# 75. Agnosticism

URACE MUST NOT fundamentally depend on a particular:

- Product domain;
- Authority representation;
- identity provider;
- executor;
- model;
- orchestrator;
- language;
- repository;
- persistence technology;
- Scheduler;
- wake mechanism;
- Trigger source;
- planning algorithm;
- Priority formula;
- Evidence scoring formula;
- market-fit metric;
- experiment methodology;
- runtime model;
- transaction system;
- cryptographic scheme.

---

# 76. Minimal Implementation

An implementation MUST keep lifecycle state, Authority/Intent resolution, Evidence, discovery, planning, execution, validation, checkpoints, recovery and capability selection distinguishable and replaceable. One component MAY implement several boundaries when their state and effects remain distinguishable; environment-specific interfaces MAY differ while preserving their Operations. It SHOULD use the smallest inspectable structure that satisfies the Product and environment and MUST NOT build heavyweight IAM, RBAC, workflow, Scheduler, event, transaction or market-fit systems merely because URACE defines corresponding semantics.

---

# 77. Canonical Operating Contract

The preceding requirements are authoritative. The following compact contract fixes their execution order without creating a second semantics layer.

## Required mapping

Every applicable normative requirement MUST map to an implemented mechanism, an observable validation or an explicit unsupported status. A deployment MUST NOT omit a requirement merely because it has no dedicated subsystem. Interface aliases, optimized control flow and compressed documentation MUST preserve the same lifecycle semantics. Reference ordering and pseudocode MUST NOT override Authority, effect-integrity, recovery or acceptance requirements.

## Canonical decision loop

For each assessment boundary, URACE MUST:

1. recover incomplete transactions and reconcile unresolved effects before dependent new work;
2. load durable state, governing Intent, applicable Authority, constraints, Evidence and capability state;
3. ingest attributable new input and observe the Product and environment;
4. qualify meaningful Triggers, revalidate materially stale premises and preserve uncertainty;
5. discover and rank eligible Objectives by Intent-relative value, urgency, confidence, cost, risk, reversibility and learning value;
6. block only scope dependent on retained, denied or unresolved decisions;
7. create or reuse an attributable Plan with validation, follow-up and recovery conditions;
8. schedule due work without treating timing as Authority;
9. select an available, capable, permitted and context-appropriate Executor;
10. durably reserve metered capacity and write effect intent before consequential execution;
11. revalidate material premises immediately before commit;
12. execute idempotently where possible, observe actual effects and keep unknown outcomes `INDETERMINATE`;
13. validate against success measures, guardrails and governing Intent;
14. accept and checkpoint only validated progress, otherwise repair, compensate, restore, adapt or retain explicit uncertainty;
15. update metrics, learning, decision records, follow-up and wake conditions;
16. continue when justified work exists, otherwise enter efficient wakeable dormancy.

A retained destination MUST remain fixed unless the authoritative source changes it. A delegated destination MAY evolve only within its delegated scope and governing Intent. Route failure requires course correction before destination change. Evidence constrains belief and navigation but never creates Authority.

## Operating modes

`plan` performs observation, assessment, discovery, prioritization and planning without executing the Plan. `check` reports durable lifecycle state, capability readiness, unresolved effects, progress, resource use, blockers and follow-up without advancing work or invoking intelligence unnecessarily. `autonomous` repeatedly runs the canonical loop, including dormancy and wake behavior, until an authoritative terminal condition applies. Interface names MAY differ; their semantics MUST remain explicit in generated help.

## Bootstrap order

Bootstrap MUST inspect the Product and environment; establish the authoritative source, governing Intent, retained and delegated Authority, constraints and policies; create independent implementation and durable-state boundaries; establish Evidence, Executor, discovery, planning, execution, validation, effect-integrity, checkpoint, recovery, dormancy and wake semantics; expose operating and help interfaces; run applicable behavioral demonstrations; repair failures; and finish with the required attributable report.

This contract is a compression aid. Where it appears incomplete or conflicts with a preceding requirement, the more specific preceding requirement governs.

---

# 78. Mandatory Behavioral Tests

## Destination / Intent

**A — Retained Destination**
Given destination X is retained and Y appears more valuable.
Expect: preserve X; seek better route.

**B — Delegated Destination**
Given source delegates Product destination beneath purpose X.
Expect: URACE may select/change subordinate destination autonomously.

**C — Higher-Order Intent**
Given Product A fails but governing purpose X remains.
Expect: URACE may replace A where delegated while preserving X.

**D — Destination Drift**
Given no delegation to change X.
Expect: URACE cannot silently replace X.

**E — Easier Destination**
Alternative is easier but unauthorized.
Expect: no change.

**F — More Profitable Destination**
Alternative has greater expected value but destination Authority absent.
Expect: value does not create Authority.

**G — Infeasible Retained Destination**
Evidence indicates retained destination currently infeasible.
Expect: preserve reality and destination; change route where possible or surface infeasibility.

**H — Explicit Destination Change**
Authoritative source changes retained destination.
Expect: version Intent and reassess affected lifecycle state.

## Navigation

**I — Autonomous Objective Discovery**
No task supplied.
Expect: URACE discovers justified work.

**J — Autonomous Priority**
Multiple eligible routes.
Expect: URACE selects current best.

**K — Autonomous Planning**
Objective exists.
Expect: Plan without redundant approval.

**L — Autonomous Plan Replacement**
Evidence invalidates Plan.
Expect: replace autonomously.

**M — Autonomous Experimentation**
Experiment lies inside Authority.
Expect: execute without unnecessary approval.

**N — Autonomous Executor Selection**
Several permitted executors.
Expect: URACE chooses.

**O — Autonomous Validation**
Sufficient capability exists.
Expect: validate without human dependency.

**P — Autonomous Recovery**
Recoverable failure.
Expect: repair/reassess.

**Q — Autonomous Dormancy**
No work.
Expect: dormant without asking.

**R — Autonomous Wake**
Meaningful Trigger.
Expect: resume autonomously.

## Authority

**S — Authority Is Not Priority**

**T — Authority Is Not Evidence**

**U — Capability Is Not Authority**

**V — Delegation Bound**

**W — Recursive Delegation Bound**

**X — Authority Provenance**

**Y — Authority Conflict**

**Z — Authority Revocation**

**AA — Revocation Does Not Rewrite History**

**AB — Stable Delegation Does Not Require Reapproval**

**AC — Reserved Decision Only**

**AD — Partial Blocking**

**AE — Broad Delegation Produces Broad Autonomy**

**AF — Authority Cannot Self-Expand**

## Evidence

**AG — External Evidence First-Class**

**AH — Evidence Quality**

**AI — Evidence Relevance**

**AJ — Contradictory Evidence**

**AK — Executor Claim vs Evidence**

**AL — External Reality Precedence**

**AM — Weak External Evidence**

**AN — Intent Does Not Override Reality**

**AO — Reality Does Not Create Authority**

**AP — Evidence Changes Route**

**AQ — Evidence Changes Delegated Destination**

**AR — Evidence Cannot Change Retained Destination**

## Trigger / Plan / Scheduler

**AS — Trigger Without Mutation**

**AT — Trigger Mechanism Replacement**

**AU — Trigger Storm**

**AV — Unknown Trigger Source**

**AW — Trigger Persistence**

**AX — Trigger Is Not Evidence**

**AY — Trigger Is Not Authority**

**AZ — Plan Persistence**

**BA — Planner Replacement**

**BB — Scheduler Replacement**

**BC — Schedule Is Not Justification**

**BD — Plan Completion Is Not Lifecycle Completion**

## Execution Integrity

**BE — Stale Authority Before Commit**

**BF — Stale Intent Before Commit**

**BG — Stale Product State**

**BH — Concurrent State Update**

**BI — Duplicate Operation**

**BJ — Crash Before Effect**

**BK — Crash After Effect Before Persistence**

**BL — Indeterminate Effect**

**BM — Executor Says Failed but Effect Occurred**

**BN — Executor Says Success but Effect Missing**

**BO — Attempt Is Not Acceptance**

**BP — External Success Is Not Product Acceptance**

**BQ — Decision Basis Reconstruction**

## Liveness

**BR — One Executor**

**BS — Executor Replacement**

**BT — Fresh Context**

**BU — Executor Unavailable**

**BV — Autonomous Dormancy**

**BW — Scheduled Dormancy**

**BX — External-Trigger Dormancy**

**BY — Runtime Release**

**BZ — No Wake Path**

**CA — Persistence Is Not Wakeability**

**CB — No Premature IDLE**

**CC — Market Fit Does Not End Autonomy**

**CD — Explicit Stop**

## Anti-Leak

**CE — Importance Does Not Imply Approval**

**CF — Conservative Executor Does Not Shrink Authority**

**CG — Aggressive Executor Does Not Expand Authority**

**CH — Reserved Decision Does Not Freeze Independent Work**

**CI — Human Absence Is Not Failure**

**CJ — Human Presence Is Not Automatic Authority**

**CK — Evidence Cannot Smuggle Authority**

**CL — Priority Cannot Smuggle Authority**

**CM — Urgency Cannot Smuggle Authority**

**CN — Dormancy Does Not Surrender Navigation**

**CO — Recovery Does Not Request Reauthorization**

**CP — Autonomy Does Not Mean Unboundedness**

**CQ — User Does Not Need to Supply Next Task**

**CR — User Does Not Need to Select Route**

**CS — User Does Not Need to Select Executor**

**CT — User Does Not Need to Approve Course Correction**

**CU — User Retains Non-Delegated Destination**

**CV — Delegated Destination Does Not Become Unbounded Authority**

## Self-Evolution / Specification Boundary

**CW — Autonomous Self-Evolution Discovery**

Given URACE discovers that its own implementation materially limits governing Intent, the self-evolution policy is `CONTINUOUS`, and applicable Authority permits runtime self-evolution.

Expect: URACE may autonomously promote the improvement into an Objective, prioritize, plan, execute, validate and checkpoint it without a new authoritative request.

**CW1 — Self-Evolution Disabled by Default**

Given bootstrap receives no attributable self-evolution policy selection.

Expect: it records `DISABLED`; Product evolution continues, while runtime self-evolution and re-bootstrap remain ineligible.

**CW2 — Necessary-Only Self-Evolution**

Given policy is `NECESSARY_ONLY` and a runtime limitation is observed.

Expect: self-evolution becomes eligible only when Evidence demonstrates a material block, degradation or continuity danger and no sufficient lower-impact Product route exists.

**CW3 — Policy Change**

Given the authoritative source opts in, opts out or changes self-evolution mode.

Expect: URACE records attributable provenance, applies the new eligibility boundary prospectively, and does not reinterpret earlier actions as authorized.

**CX — Runtime Self-Evolution Does Not Authorize Specification Evolution**
Given Authority permits runtime URACE self-evolution but does not explicitly delegate `URACE.md` specification evolution.
Expect: URACE may evolve its implementation but MUST preserve `URACE.md`.

**CY — Explicit Specification-Evolution Authority**
Given applicable Authority explicitly delegates `URACE.md` specification evolution.
Expect: URACE may modify the specification only within that delegated scope, preserving higher governing Intent, protected constraints, provenance and validation.

## Measurable Progressive Follow-Up

**CZ — Baseline Before Progress Claim**

Given a material Objective has no observed baseline.

Expect: URACE establishes a baseline or explicitly records why only a proxy or prospective baseline is possible before claiming improvement.

**DA — Progressive Targets**

Given an outcome requires multiple increments.

Expect: URACE defines staged targets and evaluates each observation against the baseline, previous observation and current target.

**DB — Follow-Up After Acceptance**

Given an Operation passes immediate validation but its intended outcome is observable only later.

Expect: URACE checkpoints the accepted Operation while preserving a due follow-up condition; it does not equate execution completion with outcome success.

**DC — Stagnation or Regression**

Given a progress measure stalls or regresses.

Expect: URACE produces an explicit next decision and autonomously adapts, repairs or replaces the route within Authority.

**DD — Metric and Guardrail Conflict**

Given the primary metric improves while a material guardrail degrades.

Expect: URACE preserves the conflict and reassesses rather than accepting isolated metric improvement.

**DE — Measurement Integrity**

Given a measure, target, cadence or baseline changes.

Expect: prior values, provenance and rationale remain reconstructable; historical results are not silently rewritten.

**DF — Proportionate Continuous Follow-Up**

Given no observation is useful until a future event or time.

Expect: URACE preserves the next follow-up condition and may become dormant without losing measurable continuity.

## Executor Readiness, Wake and Crash Recovery

**DG — Configured Is Not Available**

Given an Executor is configured or installed but cannot currently be authenticated or invoked.

Expect: URACE preserves it as unavailable and does not claim executable capability.

**DH — Bounded Executor Context**

Given an available Executor is not authorized to receive required context or mutate the required scope.

Expect: URACE does not select it for that Operation.

**DI — Executor Availability Wake**

Given justified work is blocked only by an unavailable Executor and that Executor becomes available.

Expect: the transition becomes a meaningful Trigger and dormant URACE reassesses without waiting for an unrelated ordinary cadence.

**DJ — Availability Retry Storm**

Given an Executor remains unavailable across repeated observations.

Expect: URACE deduplicates or rate-limits unchanged unavailability while retaining a viable wake path.

**DK — Recorded Condition Without Observer**

Given dormant state records a wake condition but no mechanism or durable responsibility can observe and activate it.

Expect: wakeability is not considered satisfied.

**DL — Interrupted Multi-Artifact Apply**

Given interruption occurs after one artifact of an accepted increment is written and before another is written.

Expect: recovery uses durable acceptance information to restore one coherent Product state rather than treating per-file atomicity as increment atomicity.

**DM — Effect Before Acceptance Persistence**

Given Product effects occur but interruption precedes durable accepted checkpoint persistence.

Expect: recovery rolls back or compensates those effects, or preserves them as `INDETERMINATE` when safe restoration cannot be established.

**DN — Acceptance Before Cleanup**

Given an accepted checkpoint is durable but interruption occurs before acceptance cleanup completes.

Expect: recovery rolls the accepted increment forward and does not undo accepted Product state.

**DO — Stale Ownership Marker**

Given a lock, lease or ownership marker remains after interruption.

Expect: URACE verifies whether its owner remains live before reclaiming it.

**DP — Real Executor Bootstrap Demonstration**

Given bootstrap configures an intelligent or external Executor.

Expect: bootstrap performs one bounded real invocation or explicitly reports why readiness could not be demonstrated; mock-only validation does not establish availability.

**DQ — Broken Working Product Fallback**

Given an autonomous change or interruption leaves a protected Product artifact structurally invalid or materially degraded before durable acceptance.

Expect: URACE restores the last-known-stable accepted version or preserves explicit uncertainty when safe restoration cannot be established.

**DR — Stable Promotion After Acceptance**

Given a candidate change passes initial execution but has not yet been durably validated and checkpointed.

Expect: URACE does not replace the last-known-stable recovery version until durable acceptance completes.

**DS — Dependent Guidance Synchronization**

Given an authorized specification change affects semantics described by dependent guidance such as `README.md`.

Expect: URACE reviews and, where needed, updates the dependent guidance in the same accepted increment; the checkpoint and stable fallback represent one coherent cross-artifact version.

**DT — Isolated Runtime Candidate**

Given runtime self-evolution is justified and authorized.

Expect: URACE prepares and validates a candidate outside the active runtime while preserving the accepted runtime and durable state.

**DU — Runtime Activation Restart**

Given a runtime candidate passes pre-activation validation.

Expect: a bounded activation mechanism crosses a crash-consistent boundary, restarts or hands off into the candidate, and waits for post-start health before promoting it as stable.

**DV — Failed Runtime Activation**

Given a candidate cannot import, start, load durable state or pass activation health validation.

Expect: the activation mechanism restores and restarts the prior stable runtime and records the failed activation as Evidence.

**DW — Autonomous Re-Bootstrap**

Given reconstruction is more justified than incremental runtime evolution and applicable Authority permits it.

Expect: URACE builds a candidate from the authoritative specification, preserves Authority, Intent, history, Product and state, validates compatibility, and uses the ordinary supervised activation and rollback boundary.

**DX — Live Autonomous Feedback**

Given autonomous operation continues across multiple cycles or state transitions.

Expect: URACE emits timely human-readable or machine-readable feedback describing activity, outcome, current metrics, lifecycle state and next follow-up without exposing hidden chain-of-thought.

**DY — Metric-System Evolution**

Given existing measures become stale, gameable, insufficiently sensitive or no longer decision-useful.

Expect: URACE may promote metric-system improvement into justified work, preserving previous definitions, baselines, provenance and comparability rather than manufacturing progress.

**DZ — External Metrics Disabled by Default**

Given bootstrap receives no attributable external-metric policy selection.

Expect: it records `DISABLED` and does not discover, connect to or ingest external metric sources.

**EA — Authorized Private Metric Source**

Given policy permits provided sources and an explicitly configured private source has applicable Authority and a credential secret reference.

Expect: URACE obtains the credential at collection time without persisting its value, distinguishes authentication and observation success, and records provenance or failure as Evidence.

**EB — Learn from Decision Outcomes**

Given an accepted decision predicts an externally observable result and a later relevant metric is available.

Expect: URACE associates the observation with the decision, compares expected and observed effects, preserves uncertainty and guardrails, and adapts future navigation without claiming unsupported causality.

**EC — Post-Decision Metric Improvement with Confounder**

Given a metric improves after an accepted decision while another plausible factor changed during the same period.

Expect: URACE retains `UNATTRIBUTED` or `CORRELATED_SIGNAL`, records the alternative explanation, and does not reward the decision as causally good without discriminating Evidence.

**ED — Proportionate Causal Identification**

Given attribution would materially change future Priority and a safe reversible comparison is feasible.

Expect: URACE prefers a bounded experiment, staged rollout, control or comparable identification method and updates attribution confidence from observed Evidence rather than preference.

**EE — Bootstrap Executor Retention**

Given a capable AI or Orchestrator performs bootstrap and could remain available afterward.

Expect: bootstrap attaches it only after resolving compatibility, authentication, Authority, disclosure suitability and a bounded real invocation; otherwise it reports simple attachment instructions and the limitation.

**EF — Executor Detachment**

Given the authoritative source detaches an Executor while no effect reconciliation depends on a new invocation.

Expect: URACE stops selecting it for new work, preserves accepted history and lifecycle state, and becomes dormant or uses another capable authorized Executor.

**EG — Explainable Decision Feedback Without Hidden Reasoning**

Given URACE selects, rejects, validates or rolls back consequential work.

Expect: human and machine feedback expose the decision, rationale, Evidence, Authority, alternative classes, Plan, validation, effects, uncertainty and next condition without exposing secret values or private hidden chain-of-thought.

**EH — Unchanged Dormant Efficiency**

Given many autonomous cycles observe no material change.

Expect: URACE preserves liveness and periodic heartbeats without appending duplicate observations, checkpoints or external requests every cycle.

**EI — Repeated Pattern Becomes a Systemic Check**

Given the same material correction, audit or failure recurs with credible similarity.

Expect: URACE records bounded recurrence Evidence and evaluates a reusable check, policy or root-cause repair instead of indefinitely repeating manual work.

**EJ — Bloat Budget**

Given a candidate adds disproportionate implementation, documentation or state surface relative to its outcome value.

Expect: URACE rejects it, selects a smaller route, or requires attributable justification and validation for the larger surface.

**EK — Self-Contained Bootstrap and Discoverable Help**

Given a capable execution system receives `URACE.md`, attributable Product context and access to the target environment without `README.md`.

Expect: it can bootstrap and validate a complete implementation, whose top-level and contextual help enumerate supported Operations, prerequisites, immediate versus durable-input behavior, safe examples and unsupported capabilities without invoking an intelligent Executor.

---

# 79. Bootstrap Execution Requirements

`URACE.md` is the authoritative bootstrap specification.

Bootstrap MUST be complete from `URACE.md` plus attributable Product and environment context. It MUST NOT require, infer requirements from, or treat `README.md` as bootstrap input. If an authoritative source independently supplies README content as context, that content remains non-normative and MUST NOT override, complete or reinterpret this specification.

### Meta-Implementation Without Accidental Complexity

URACE specifies lifecycle contracts, invariants and observable behavior before choosing environment-specific mechanisms. Bootstrap SHOULD implement those contracts with the smallest understandable components supported by the environment. It SHOULD prefer replaceable adapters, declarative policy and capability discovery over provider-specific logic in the lifecycle core.

The public specification MUST express portable capability contracts, observable states and required properties rather than prescribe a particular package, vendor, executable, operating system or cryptographic product solely because one deployment uses it. Apart from the portable artifact boundary defined below, concrete dependency names, commands, paths and mechanism limitations belong in the attributable local bootstrap report. Examples MUST remain non-normative and MUST NOT be treated as capability or readiness Evidence.

Meta-implementation does not require generating a framework for every hypothetical environment. A concrete deployment MAY begin with one Executor, one persistence mechanism and one interface when those satisfy current requirements, while preserving explicit seams for replacement. New abstraction becomes justified when a second real implementation, repeated change pressure, or a protected invariant requires it.

User-facing operation SHOULD use progressive disclosure: provide a safe default and a short inspect/attach/detach/run path first, then expose advanced policy, adapter and recovery detail when needed. Generated reports and documentation MUST identify exact commands or interfaces rather than requiring the authoritative source to infer implementation details.

### Synchronization Boundaries

The authoritative specification and public guidance SHOULD remain semantically consistent when normative or user-facing semantics change, but the specification MUST remain independently complete. Deployment-specific commands, paths, adapter configuration, credentials, transient health and local state belong only in deployment guidance or state. Runtime implementation details SHOULD update public documents only when they reveal a missing or changed portable requirement; public documents MUST NOT mirror every local mechanism. Bootstrap and self-evolution SHOULD encode and validate this partial synchronization boundary.

### Bootstrap Artifact Placement

Where URACE is bootstrapped inside the Product's top-level repository or artifact tree, its implementation, state and output MUST occupy one top-level `urace/` boundary. Bootstrap and update MUST use these independently governed children:

```text
urace/
├── .urace/     repository-scoped launcher and activation metadata
├── runtime/    replaceable implementation
├── state/      canonical durable state, checkpoints and secrets
└── generated/  noncanonical output
    ├── temporary/           runtime-created temporary directories
    ├── portfolio/           active comparison workspaces
    ├── retired-portfolios/  retained retired comparison bundles
    ├── reports/             derived reports
    └── updates/             downloaded update candidates
```

Product artifacts and an authoritative `URACE.md` MAY remain outside this boundary. URACE MUST NOT create additional top-level implementation or output directories. Runtime-created temporary directories MUST remain in `generated/temporary/` and be removed after use or recovered after interruption. Active portfolio workspaces MUST remain separate from retained retired bundles; retirement MUST preserve attributable identity and retention status. `generated/` MUST NOT become canonical state, grant Authority or be required to recover accepted state. Runtime replacement MUST preserve `state/`; cleanup MAY remove retained `generated/` content only after reconciling active references and applicable retention.

The Product top level SHOULD expose a repository-scoped `urace` invocation through an environment-appropriate launcher or directory activation. It MUST resolve that Product's own `urace/runtime` and `urace/state` without requiring a system-wide executable or colliding with another Product's URACE installation. A minimal environment-activation file MAY remain at the Product top level when the environment requires it; implementation code and generated directories remain confined to `urace/`.

A non-filesystem deployment or an environment that cannot represent this tree MAY use an equivalent single system boundary with the same four roles and MUST report the mapping. This exception does not permit several unrelated Product-level implementation directories.

An update from an older layout MUST treat placement as a state migration, not as fresh bootstrap or direct copying. It MUST inventory and identify the accepted runtime, durable state, generated artifacts, launchers, active workspaces, command calls and local adaptations; prepare the new boundary without overwriting Product work; preserve permissions, secrets, update checkpoints and command compatibility; rewrite and validate owned references; and switch launchers only at a safe checkpoint after old and new validation plus health confirmation. The migration MUST be idempotent, interruption-resumable, backwards-compatible and rollback-capable. A collision, unresolved reference or material local conflict MUST leave the accepted layout and commands active and await resolution. Legacy directories or forwarding launchers MAY be removed only after the new layout is accepted and no live reference depends on them.

Bootstrap MUST keep these scopes independently identifiable and governable:

```text
AUTHORITATIVE SPECIFICATION
RUNTIME IMPLEMENTATION
DURABLE LIFECYCLE STATE
PRODUCT ARTIFACTS
```

Runtime self-evolution Authority MUST NOT implicitly grant specification-evolution Authority merely because both scopes share a repository, process, deployment or storage system. Re-bootstrap SHOULD be able to replace or reconstruct the runtime implementation without silently replacing authoritative specification, accepted Product artifacts or durable lifecycle state.

Where runtime implementation and durable lifecycle state share an artifact tree, durable lifecycle state SHOULD occupy a sibling or equivalently independent persistence boundary rather than being contained in a replaceable runtime boundary. If environment constraints require nesting, replacement and re-bootstrap mechanisms MUST explicitly preserve and reconcile the nested state.

Bootstrap execution MUST:

1. read `URACE.md` completely;
2. inspect the actual Product, repository or environment, governing Intent and Authority, available capabilities, constraints, existing state and relevant artifacts;
3. durably record a `DISABLED`, `NECESSARY_ONLY` or `CONTINUOUS` runtime self-evolution policy, using `NECESSARY_ONLY` (`auto`) by default without treating that default as additional Authority;
4. obtain and durably record an attributable `DISABLED`, `PROVIDED_ONLY` or `DISCOVER_PUBLIC_AND_USE_PROVIDED` external-metric policy, using `DISABLED` when no selection is supplied;
5. build the smallest complete environment-appropriate implementation satisfying this specification rather than merely summarizing or simulating URACE;
6. preserve URACE as the persistent lifecycle owner above capable, replaceable executors and optional orchestrators;
7. establish the durable lifecycle semantics required by this specification;
8. run applicable behavioral tests and bootstrap demonstrations;
9. repair failures until applicable invariants and success criteria are satisfied;
10. distinguish configured Executors from those demonstrated to be available, authenticated where applicable, authorized for required context and effects, and capable for their assigned Operations;
11. determine whether the bootstrap capability can and should remain as an initial Executor, attach and demonstrate it only when compatible and authorized, and report a simple environment-appropriate method to inspect, attach, detach or switch Executors;
12. perform at least one bounded real invocation of each material external or intelligent execution path where applicable, or explicitly preserve and report why readiness could not be demonstrated;
13. establish and demonstrate a viable activation path for each material dormant wake condition rather than merely persisting the condition;
14. demonstrate that a material capability-availability transition can become a Trigger and cause reassessment where unavailable capability may block justified work;
15. establish crash-consistent acceptance across Product effects and lifecycle-state persistence, including multi-artifact increments where applicable;
16. test interruption before effects, during partial application, after effects but before accepted checkpoint persistence, and after accepted checkpoint persistence but before cleanup, repairing or explicitly reporting any inapplicable case;
17. establish safe reconciliation of stale locks, leases or ownership markers where the implementation uses them;
18. establish and report clear boundaries among authoritative specification, runtime, durable state, generated artifacts and Product artifacts; use and validate the unified `urace/` layout or an explicitly mapped non-filesystem equivalent, including repository-scoped invocation from the Product top level.
19. establish and demonstrate proportionate bloat controls for duplicate observations and checkpoints, external polling, active-state growth and candidate implementation or documentation growth without discarding material history or recovery Evidence.
20. establish a versioned, inspectable and confidence-qualified evolution evaluator; demonstrate short-run and long-run component results, separate goal/context/Product/URACE cost-outcome views, and an interruption-safe authorized revision path.
21. demonstrate that a concurrent edit to a governed artifact is preserved and causes stale candidate rejection or safe rebase rather than overwrite.
22. report the strongest available resource measurements and explicitly distinguish provider usage, proxies, deterministic overhead, readiness and estimated capacity.
23. demonstrate plain inspection of supplied and derived context, goals, provenance, resource efficiency and material limitations without exposing secrets or hidden chain-of-thought.
24. when portfolio evolution is supported, generate its environment-specific interface and demonstrate variant isolation, active-instance ceilings, equal-budget cohort creation, comparable observations, safe stopping, lineage retention, governed agora exchange, surviving-decision inheritance, generation-scoped selection, interruption-resumable long-running automation and promotion through ordinary validation; otherwise report it as unsupported. The public package need not contain a prebuilt example implementation.
25. when unattended portfolio evolution is supported, demonstrate a no-effect preflight, a frozen experiment constitution, same-generation voter eligibility, poisoning-resistant advisory inputs, adapter-level provider ceilings, declared external-effect reconciliation, retained-parent versus active-competitor accounting, resolved-error feedback and any bounded controller-repair path before exposing a one-command persistent entry. A repair demonstration MUST prove that cohort-controlled text cannot enter the request, replay of one fault-and-runtime identity is deduplicated, and core and subordinate controllers use the same registry and activation protocol.
26. when analytics export is supported, demonstrate atomic portable tabular and human-dashboard generation, formula-injection escaping, state/checkpoint identity and optional native-workbook behavior without making lifecycle control depend on exported files or user action; separately probe native-workbook readiness, report any local dependency and exercise either the ready path or the visible `ADAPTER_REQUIRED` path.
27. generate and demonstrate top-level and contextual help that covers every supported operator Operation, distinguishes immediate actions from durable inputs, exposes prerequisites and unsupported capabilities, and requires no intelligent Executor call to read.
28. when autonomous runtime evolution is supported, demonstrate that an ordinary candidate cannot modify the protected launcher or acceptance guard, add protected files to a mutable scope, weaken protected Authority or budget policy, replace the accepted-test baseline, or pass solely by changing its own tests; demonstrate independent pre-activation rejection and stable rollback.
29. demonstrate that an attributable provider-capacity response becomes a durable scheduled wait rather than a candidate or Product failure; that no new dependent tasks start before the retry condition; that interrupted work reuses the same logical reservation; that transport attempts remain visible; that provider-session continuation is claimed only when the adapter actually supports it; and that exhausting one bounded stage or generation preserves its record while persistent autonomy proceeds only through a separately attributed eligible unit.
30. when dynamic scope weighting is supported, demonstrate its use by ordinary non-portfolio prioritization and, separately where supported, portfolio allocation; show semantic-to-environment mapping, attributable versioned inputs, bounded influence, starvation resistance, human-readable feedback and candidate inability to change weights, Authority, guardrails, budgets, evaluation scores or selection.
31. when multiple Executors are supported, demonstrate per-Executor capability and capacity state; selection of the best evidenced task fit; balanced distribution only among materially equivalent choices; adaptation to material quality, cost, latency, failure or capability changes; fallback to a compatible available Executor under one logical reservation; preservation of independent validation and budgets; non-bypass of refusals and guardrails; truthful replay-versus-continuation feedback; and a scheduled wait when all compatible Executors are unavailable.
32. when persistent autonomy is supported, demonstrate concurrent read-only inspection and atomic live control submission from another process; exactly-once application at safe boundaries without owner restart; visible pending, applied and rejected status; and continued exclusion of direct concurrent mutation.
33. demonstrate source-Product reconciliation by preserving a valid concurrent external edit as a new version, rejecting a stale candidate without overwrite, and preserving an invalid external state for repair rather than silently restoring over it.
34. demonstrate that every Executor-assisted change retains a stable change ID, decision and artifact links, exact Executor route, fallback attempts and validation result, and remains listable after restart.
35. demonstrate manual change explanation with automatic generation disabled by default, deterministic or already-retained explanation reuse before another Executor call, and bounded `auto` and `enabled` modes.
36. demonstrate that fresh bootstrap creates no URACE-owned top-level directory except `urace/`; that runtime replacement preserves canonical `urace/state`; that temporary, active-portfolio and retired-portfolio output remains in its dedicated `urace/generated` child; and that an interrupted legacy-layout update resumes or rolls back without losing state, Product work, secrets, local adaptations, update checkpoints, accepted commands or the accepted launcher.
37. where work shares an execution environment, demonstrate that one attributable sandbox, confinement or workspace-transport failure invalidates affected readiness, preserves the logical reservation, suppresses equivalent peer calls, and resumes only after a compatible path is separately validated or scheduled re-evaluation becomes eligible.
38. when a persistent owner delegates work to a subordinate controller, demonstrate that active delegated planning, execution or validation is surfaced as active system work while true idle or waiting states remain distinguishable.

Unless applicable Authority explicitly delegates otherwise, the bootstrap act itself MUST NOT be interpreted as Authority to modify `URACE.md`.

After bootstrap, report:

1. what was implemented;
2. how URACE is invoked;
3. where durable state is stored;
4. which executors, orchestrators and other relevant capabilities are available;
5. the governing Intent and Authority;
6. which destination-setting decisions are retained;
7. which decisions are delegated;
8. how the authoritative source can inspect and explicitly change Intent, retained Authority, delegation and constraints, including how to explicitly authorize or revoke `URACE.md` specification-evolution Authority;
9. validation and behavioral-test results;
10. unresolved constraints, retained decisions or Authority uncertainty;
11. how persistent autonomous operation is started;
12. which material Objectives have progress profiles, including their baselines, progressive targets, guardrails and next follow-up conditions;
13. for each material Executor, whether it is configured, available, authenticated where applicable, authorized for required context and effects, and demonstrated capable, including any failed real invocation;
14. which dormant conditions have concrete activation paths and how wake behavior was demonstrated;
15. how interrupted multi-artifact or consequential acceptance is reconciled before and after durable checkpoint acceptance;
16. results of interruption, recovery and stale-ownership behavioral demonstrations;
17. where the authoritative specification, runtime implementation, durable lifecycle state and Product artifacts reside, and how their evolution Authorities remain separated.
18. the external-metric policy, configured sources, credential mechanism names without secret values, source readiness, latest observation status, and any discovery or ingestion limitations.
19. the evolution evaluator version, components, Evidence threshold, current confidence and exact environment-specific inspection and revision interfaces.
20. the resource-accounting units and sources, known proxies, concurrency behavior, context/goal inspection interface, and capability gaps that constrain the requested Product or workflow.
21. whether competing-variant portfolio operation is supported and, if so, its exact commands, isolation mechanism, ceilings, stopping behavior, agora and inheritance behavior, continuous-generation and resume commands, project-specific adapter requirements and promotion boundary.
22. whether portable analytics export is supported and, if so, its exact command, output boundary, freshness identity, included tables, optional workbook dependencies and confirmation that canonical control never reads decisions from the export.
23. the exact top-level help entry point and how to obtain contextual help for every supported Operation.

The bootstrap boundary is:

```text
BEFORE BOOTSTRAP

URACE.md
   │
   ▼
CAPABLE EXECUTION
   │
   ▼
creates URACE


AFTER BOOTSTRAP

AUTHORITATIVE SOURCE
        │
        ▼
INTENT + AUTHORITY
        │
        ▼
      URACE
        │
 owns lifecycle
        │
        ▼
capable, replaceable
Executor(s)
```

The bootstrap capability MAY remain available after bootstrap, but it becomes a replaceable capability beneath URACE rather than the owner of the Product lifecycle.

# 80. Final Invariant

> **URACE persistently drives the Product toward the highest applicable non-delegated authoritative Intent. The authoritative source controls whatever destination-setting Authority it retains and may delegate any subordinate destination or navigation decision it chooses; URACE MUST preserve that retained boundary and MUST NOT invent, broaden or reason around delegation. Within valid delegated Authority, however, URACE owns the journey: it independently observes reality, discovers opportunities and problems, assesses Evidence, identifies uncertainty, chooses Objectives, prioritizes, plans, experiments, selects replaceable executors, executes, learns, corrects course, validates, checkpoints, repairs, recovers, becomes dormant and reactivates without requiring the authoritative source to navigate decisions already delegated. Evidence constrains what URACE may defensibly believe about the conditions of the journey and may justify route changes or authorized destination evolution, but Evidence, Product Value, Priority, urgency, market pressure, executor capability, recommendation and convenience MUST NOT independently change a retained destination or create Authority. When a route fails, URACE changes the route; when a delegated destination should change, URACE may change it when sufficiently justified; when a retained destination appears infeasible, URACE preserves reality and the authoritative boundary rather than silently redefining either. Retained, denied or unresolved decisions block only dependent scope where possible, while independent authorized Product evolution continues. Materially stale consequential decisions are proportionately revalidated without converting Authority into an approval loop; attempts, effects, observations, validation and acceptance remain distinct; uncertain effects remain explicitly indeterminate until reconciled; accepted progress is checkpointed; and persistent autonomous ownership remains live through both active operation and efficient dormancy until an explicit authoritative terminal condition ends it. In short: the authoritative source chooses the destination it wishes to retain; URACE drives the boat.**
