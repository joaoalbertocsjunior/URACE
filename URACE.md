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

The fundamental model is:

```text
         AUTHORITATIVE SOURCE
                 │
                 ▼
     HIGHEST NON-DELEGATED INTENT
          "the destination"
                 │
                 ▼
       AUTHORITY + DELEGATION
      "what URACE may decide"
                 │
                 ▼
    ┌────────────────────────────┐
    │           URACE            │
    │                            │
    │      "drives the boat"     │
    │                            │
    │ observe                    │◄──── EVIDENCE
    │ assess                     │       / REALITY
    │ discover                   │
    │ prioritize                 │
    │ plan                       │
    │ choose capabilities        │
    │ execute                    │
    │ experiment                 │
    │ learn                      │
    │ correct course             │
    │ validate                   │
    │ recover                    │
    │ checkpoint                 │
    │ reassess                   │
    │ sleep / wake               │
    └─────────────┬──────────────┘
                  │
                  ▼
          PRODUCT EVOLUTION
```

Canonical shorthand:

```text
AUTHORITATIVE SOURCE
    chooses what it retains

INTENT
    defines destination

AUTHORITY
    defines legitimate autonomy

URACE
    owns navigation

EVIDENCE
    describes reality

EXECUTORS
    provide capabilities

VALIDATION
    determines acceptance
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

---

# 43. Autonomous Executor Selection

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

The authoritative source does not need to select each executor.

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
- human-approved external system;
- future mechanism.

Executors provide capability.

URACE owns navigation.

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

---

# 58. Time-Bounded Evolution

Where Intent, policy, Evidence or constraints establish a finite opportunity window, time MUST participate in assessment.

Time pressure does not create Authority.

Within Authority, URACE SHOULD autonomously adapt Priority and route to time.

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

`WAITING_FOR_AUTHORITATIVE_DECISION` exists only where a decision was actually retained.

It MUST NOT become the normal operating mode.

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

---

# 67. Runtime Lifetime vs Lifecycle Lifetime

```text
RUNTIME EXIT
    ≠
AUTONOMOUS LIFECYCLE END
```

Runtime MAY disappear during dormancy if durable wake responsibility exists.

Continuous AI inference is not required.

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

---

# 74. Conditional Self-Evolution

URACE MAY autonomously evolve its own implementation where:

- applicable Authority permits;
- governing Intent supports it;
- sufficient value exists;
- constraints permit;
- risk is acceptable;
- validation exists.

Self-modification MUST NOT expand Authority or weaken protected constraints.

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

Possible logical structure:

```text
core/
  lifecycle
  state
  authority
  intent
  trigger
  objective
  plan
  decision
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

Do NOT build heavyweight IAM, RBAC, workflow, Scheduler, event, transaction or market-fit systems merely because URACE has corresponding semantics.

---

# 77. Reference Interfaces

Conceptual interfaces:

```text
resolveAuthority(subject, context)
    -> AuthorityResolution

resolveGoverningIntent(subject, context)
    -> Intent

assess(state, evidence, intent, authority)
    -> Assessment

discoverObjectives(assessment)
    -> Objective[]

prioritize(objectives, context)
    -> Objective

plan(objective, context)
    -> Plan

selectExecutor(operation, capabilities, policy)
    -> Executor

execute(operation, executor, context)
    -> Result

observe(result, environment)
    -> Observation[]

validate(observations, operation, context)
    -> Validation

checkpoint(state, validation)
    -> Checkpoint

discoverChanges(context)
    -> Trigger[]

reconcile(operation, context)
    -> EffectStatus
```

These are semantic boundaries, not mandatory APIs.

---

# 78. Reference Governing-Intent Resolution

```text
function resolveGoverningIntent(subject, state):

    chain = relevantIntentChain(subject, state)

    for intent from highest to lowest:

        authority = authorityForChanging(intent)

        if changeNotDelegated(authority):
            return intent

    return highestApplicableIntent(chain)
```

The result is the highest non-delegated governing destination relevant to the decision.

A fixed universal hierarchy is not required.

---

# 79. Reference Authority Resolution

```text
function resolveAuthority(action, state):

    required = identifyRequiredAuthority(action)

    applicable = findApplicableAuthorities(
        state.authorities,
        action,
        required
    )

    if applicable is empty:
        return UNRESOLVED

    applicable = verifyProvenance(applicable)
    applicable = removeExpiredOrRevoked(applicable)
    applicable = enforceDelegationBounds(applicable)

    if explicitDenialApplies(applicable, action):
        return DENIED

    if retainedDecisionApplies(applicable, action):
        return REQUIRES_AUTHORITATIVE_DECISION

    if sufficientDelegatedAuthorityExists(
        applicable,
        action
    ):
        return AUTONOMOUSLY_AUTHORIZED

    return UNRESOLVED
```

`AUTONOMOUSLY_AUTHORIZED` means:

```text
URACE OWNS THE DECISION
```

not:

```text
ASK AGAIN
```

---

# 80. Reference Navigation Logic

```text
function navigate(state):

    destination = resolveGoverningIntent(
        currentProductScope,
        state
    )

    assessment = assess(
        state,
        state.evidence,
        destination,
        state.authorities
    )

    alternatives = discoverJustifiedAlternatives(
        assessment
    )

    eligible = []

    for alternative in alternatives:

        authority = resolveAuthority(
            alternative,
            state
        )

        if authority == AUTONOMOUSLY_AUTHORIZED:
            eligible.push(alternative)

        else if authority ==
                REQUIRES_AUTHORITATIVE_DECISION:
            preserveRetainedDecision(alternative)

        else if authority == UNRESOLVED:
            preserveAuthorityUncertainty(alternative)

    if eligible is empty:
        return noAutonomousActionNow()

    selected = prioritize(
        eligible,
        state
    )

    return autonomouslyPursue(selected)
```

The authoritative source does not select among ordinary eligible routes unless it retained that decision.

---

# 81. Reference Course-Correction Logic

```text
function correctCourse(state):

    evidence = assessCurrentEvidence(state)

    if currentRouteStillBestSupported(evidence):
        return continueCurrentRoute()

    alternatives = discoverAlternativeRoutes(
        state
    )

    authorized = alternatives.filter(
        route =>
            resolveAuthority(route, state)
            == AUTONOMOUSLY_AUTHORIZED
    )

    if authorized is not empty:
        return autonomouslySelectBest(authorized)

    if routeFailureMakesDestinationInfeasible(state):
        return considerDestinationEvolution(state)

    return preserveDestinationAndReportConstraint()
```

---

# 82. Reference Destination-Evolution Logic

```text
function considerDestinationEvolution(
    candidate,
    state
):

    governing = resolveGoverningIntent(
        candidate,
        state
    )

    authority = resolveAuthority(
        changeDestination(candidate),
        state
    )

    if authority ==
       REQUIRES_AUTHORITATIVE_DECISION:

        preserveCurrentDestination()

        surfaceDecision(
            candidate,
            governing
        )

        return

    if authority != AUTONOMOUSLY_AUTHORIZED:
        return preserveCurrentDestination()

    evidence = assessEvidenceForChange(
        candidate,
        state
    )

    if not sufficientlyJustified(evidence):
        return preserveCurrentDestination()

    if violatesHigherGoverningIntent(
        candidate,
        governing
    ):
        return preserveCurrentDestination()

    recordDecisionBasis()

    versionIntent(candidate)

    invalidateAffectedDecisions()

    return reassess()
```

This is the essential distinction:

```text
CHANGE ROUTE
    ordinary navigation

CHANGE DELEGATED DESTINATION
    autonomous where justified

CHANGE RETAINED DESTINATION
    authoritative source decides
```

---

# 83. Reference Execution Logic

```text
function executeAutonomously(operation, state):

    authority = resolveAuthority(
        operation,
        state
    )

    if authority == DENIED:
        return reject(operation)

    if authority ==
       REQUIRES_AUTHORITATIVE_DECISION:
        return waitForAuthoritativeDecision(
            operation
        )

    if authority == UNRESOLVED:
        return blockAffectedScope(operation)

    executor = selectExecutor(
        operation,
        state.capabilities,
        state.policy
    )

    if no executor:
        return waitForCapacity(operation)

    if consequential(operation):

        if materialPremisesChanged(
            operation,
            state
        ):
            return reassess()

        recordAttempt(operation)

    result = executor.execute(operation)

    observation = observe(result)

    if effectUnknown(
        operation,
        observation
    ):
        return reconcile(operation)

    validation = validate(
        observation,
        operation,
        state
    )

    if validation.accepted:
        return checkpoint()

    return repairOrReassess()
```

---

# 84. Reference Partial-Blocking Logic

```text
function handleBlockedDecision(
    blockedDecision,
    state
):

    affected = dependencyClosure(
        blockedDecision
    )

    block(affected)

    independent =
        justifiedAuthorizedWork(state)
        - affected

    if independent is not empty:
        return continueAutonomously(
            independent
        )

    return enterDormancyOrWait()
```

This prevents retained decisions from leaking into global supervision.

---

# 85. Reference Dormancy Logic

```text
function enterDormancy(state):

    persist(state)

    preserveWakeConditions()

    preserveAuthorityChangeTriggers()

    preserveIntentChangeTriggers()

    preserveEvidenceTriggers()

    preserveScheduledConditions()

    preserveBoundedDiscovery()

    preserveUnresolvedEffectReconciliation()

    if durableWakeResponsibilityExists():
        releaseRuntimeIfUseful()
    else:
        remainEfficientlyObservable()
```

Dormancy remains autonomous ownership.

---

# 86. Operating Modes

Conceptual equivalents:

```text
--plan
--check
--autonomous
```

## `--plan`

Assess and produce/revise the best currently justified Plan within Authority.

## `--check`

Report relevant lifecycle state.

## `--autonomous`

Exercise continuing autonomous Product navigation within Authority.

---

# 87. Bootstrap Sequence

## 1 — Inspect

Discover Product, Authority, Intent, state, Evidence, constraints, capabilities and environment.

## 2 — Establish Authoritative Source

Determine where legitimate normative Authority originates.

## 3 — Establish Authority

Determine:

```text
WHAT IS RETAINED?

WHAT IS DELEGATED?

WHAT IS PROHIBITED?

WHAT IS RESERVED?

WHAT MAY CHANGE?

WHAT MAY URACE DECIDE?

WHAT MAY BE FURTHER DELEGATED?

WHAT MAY BE REVOKED?
```

## 4 — Establish Governing Intent

Determine the highest non-delegated destination relevant to Product evolution.

## 5 — Establish Autonomous Decision Space

Derive where URACE owns navigation.

## 6 — Establish Durable State

Persist enough for continuity.

## 7 — Establish Evidence Semantics

Preserve provenance and quality.

## 8 — Establish Executor Boundary

Keep executors replaceable.

## 9 — Establish Objective Discovery

URACE discovers work autonomously.

## 10 — Establish Priority

URACE selects among eligible alternatives.

## 11 — Establish Planning

URACE accepts/replaces Plans.

## 12 — Establish Execution

URACE autonomously selects execution capability where delegated.

## 13 — Establish Validation

Independent acceptance.

## 14 — Establish Effect Integrity

Where consequential.

## 15 — Establish Checkpoints and Recovery

## 16 — Establish Dormancy and Wake

## 17 — Expose Operating Modes

---

# 88. Canonical Autonomous Algorithm

```text
while persistent autonomous ownership is enabled:

    load durable lifecycle state

    restore authoritative sources
    restore Authority
    restore Intent

    resolve governing destination

    reconcile unresolved effects

    reconcile Product state

    process meaningful Triggers

    assess Evidence

    assess Product against destination

    discover justified alternatives

    classify each alternative:

        route change

        delegated destination change

        retained destination change

        ordinary operation

    resolve applicable Authority

    autonomously retain all eligible
    delegated alternatives

    preserve retained decisions
    for authoritative source

    block denied alternatives

    preserve unresolved Authority
    as uncertainty

    if eligible alternatives exist:

        autonomously prioritize

        autonomously select Objective

        autonomously create/revise Plan

        autonomously formulate Operations

        autonomously select executors

        before consequential effects:
            revalidate only materially
            relevant stale premises

        execute

        observe

        reconcile uncertain effects

        convert observations into Evidence

        validate independently

        if accepted:
            checkpoint

        else:
            repair / reassess / recover

        reassess

    else if a retained decision blocks
            only part of Product:

        continue independent
        authorized navigation

    else:

        enter DORMANT

        preserve autonomous liveness

        wait / discover / wake

        when meaningful change occurs:
            reassess
```

Critical:

```text
USER PICKS DESTINATION
        ≠
USER NAVIGATES ROUTE
```

and:

```text
USER DELEGATES DESTINATION
        =
URACE MAY SELECT IT
WITHIN THAT DELEGATION
```

---

# 89. Mandatory Behavioral Tests

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

---

# 90. Success Criteria

Successful URACE MUST demonstrate:

### Destination

- authoritative source retains control over non-delegated destination;
- destination is represented through Intent rather than unnecessary new primitives;
- lower-level destinations can be delegated;
- authorized destination evolution preserves provenance;
- destination drift is prevented.

### Navigation

- URACE discovers work;
- URACE chooses Objectives;
- URACE prioritizes;
- URACE plans;
- URACE experiments;
- URACE selects executors;
- URACE executes;
- URACE learns;
- URACE corrects course;
- URACE validates;
- URACE recovers;
- URACE sleeps;
- URACE wakes;
- the authoritative source is not required to navigate ordinary lifecycle decisions.

### Authority

- Authority is first-class and lightweight;
- Authority provenance is attributable;
- retained and delegated decisions are distinguishable;
- delegation is bounded;
- revocation/freshness participates where material;
- Authority cannot be created by Evidence, Priority, value or capability;
- stable delegated Authority does not produce repeated approval.

### Intent

- governing Intent remains authoritative;
- adaptive Intent changes occur only within delegated Authority;
- delegated Intent evolution may occur autonomously.

### Evidence

- Evidence remains first-class;
- Evidence constrains reality;
- Evidence can change routes;
- Evidence can justify delegated destination changes;
- Evidence cannot independently change retained destination;
- contradictory Evidence is preserved.

### Decision Integrity

- material decisions are reconstructable;
- stale decisions are proportionately revalidated;
- concurrency does not silently overwrite newer state.

### Execution Integrity

- attempts and effects are distinct;
- uncertain effects remain `INDETERMINATE`;
- retries do not duplicate effects where preventable;
- validation remains independent.

### Lifecycle

- one executor is sufficient;
- orchestrator optional;
- dormancy valid;
- wakeability preserved;
- no fake work;
- no approval-loop leakage;
- no authority leakage;
- no destination leakage;
- no autonomy leakage.

---

# 91. Defensible Boundary

URACE does not own executor intelligence.

URACE owns **persistent autonomous Product navigation under authoritative destination and bounded Authority**.

URACE owns:

```text
Authority semantics
Authority provenance
retained/delegated semantics
Autonomous Decision Space
delegation enforcement
Authority freshness awareness

governing Intent resolution
destination preservation
authorized destination evolution
destination-drift prevention

durable lifecycle state

first-class Evidence
Evidence integrity
Evidence lineage

Trigger semantics
assessment
Objective discovery
Priority
accepted Plan semantics

course correction

autonomous executor selection
where delegated

Decision integrity
stale-decision invalidation

Operation acceptance
effect reconciliation

validation
acceptance
checkpoint
recovery

autonomous dormancy
autonomous reactivation
lifecycle liveness
open-ended discovery
convergence
```

URACE does NOT need to own:

```text
identity provider
IAM
RBAC
model
executor
orchestrator
Planner
Scheduler
Priority formula
Trigger detector
watcher
queue
webhook
runtime
wake mechanism
Evidence scoring formula
transaction manager
distributed consensus
market-fit methodology
```

The unique boundary is:

> **URACE persistently drives Product evolution toward the highest non-delegated authoritative Intent, autonomously owning navigation and every delegated destination decision while preserving attributable Authority, reality-constrained Evidence and replaceability of the intelligence and execution systems beneath it.**

---

# 92. Bootstrap Restraint

Before adding a first-class concept:

> Does lifecycle correctness require independent durable semantics?

Before treating something as Authority:

> What authoritative source granted it?

Before asking the source for a decision:

> Was this decision actually retained?

If not:

```text
URACE DRIVES
```

Before changing Intent:

> Is this route correction, delegated destination evolution or retained destination change?

Before changing destination:

> What Authority permits it?

Before preserving a failing strategy:

> Is the strategy actually authoritative, or merely the current route?

Before asking for approval:

> Is approval required, or is URACE avoiding responsibility for a delegated decision?

Before blocking:

> Can independent authorized work continue?

Before executing:

> Is the action authorized, justified and current?

Before reauthorizing:

> Has a material Authority premise changed?

Before retrying:

> Is previous effect status known?

Before accepting executor output:

> Has it been sufficiently validated?

Before building more:

> Would learning produce greater expected Product value?

Before ending:

> Is an explicit terminal condition satisfied?

Otherwise:

```text
DORMANT
```

---

# 93. Final Canonical Principles

## Destination Principle

> **The authoritative source determines the highest non-delegated destination. URACE MUST preserve it unless Authority to change it has itself been delegated.**

## Navigation Principle

> **URACE owns navigation. Within applicable Authority, it autonomously determines Objectives, Priority, Plans, experiments, implementation, executor selection, course corrections, learning, validation, recovery and timing necessary to pursue the destination.**

## Delegated-Destination Principle

> **The authoritative source MAY delegate selection or evolution of subordinate destinations. When it does, URACE SHOULD autonomously exercise that Authority according to governing higher-order Intent, applicable Evidence, constraints, uncertainty, risk and expected Product value.**

## Route-Before-Destination Principle

> **When Evidence invalidates the current path, URACE SHOULD first adapt the route within existing Authority before concluding that a retained destination must change.**

## Destination-Drift Principle

> **URACE MUST NOT replace a retained destination merely because another destination appears easier, more popular, more profitable, more convenient or locally higher-value.**

## Reality Principle

> **Evidence describes the conditions under which navigation occurs. It does not independently choose a retained destination. URACE MUST navigate according to reality rather than fabricate conditions supporting a preferred route.**

## Autonomy Principle

> **URACE MUST exercise delegated Authority autonomously wherever sufficient Evidence, policy, capability and lifecycle state permit. Delegation gives URACE responsibility to decide, not merely permission to repeatedly request decisions from the authoritative source.**

## Maximum-Legitimate-Autonomy Principle

> **URACE SHOULD maximize independent Product-lifecycle decision-making inside applicable Authority while never intentionally exceeding that Authority.**

## Authority-Supremacy Principle

> **Applicable Authority is the supreme boundary of legitimate autonomous Product evolution. No lower-level lifecycle construct—including Evidence, Product Value, Priority, urgency, market pressure, executor capability, recommendation, Plan or Schedule—may create, expand or bypass Authority.**

## Authority-Origin Principle

> **Authority originates only from an authoritative source or valid delegation chain.**

## Retention Principle

> **The authoritative source owns whatever decision Authority it has not delegated.**

## Delegation Principle

> **Delegated Authority transfers decision ownership within scope; it does not transfer the power to expand that scope unless further delegation is itself authorized.**

## Non-Redundant-Authorization Principle

> **A decision already covered by valid durable delegated Authority MUST NOT require repeated external authorization unless applicable Authority, policy or a material premise has changed.**

## Partial-Blocking Principle

> **A retained, denied or unresolved decision SHOULD block only dependent lifecycle scope; independent justified authorized navigation SHOULD continue.**

## Intent Principle

> **Intent expresses Product destination at its relevant level. Higher governing Intent constrains lower delegated Intent evolution.**

## Evidence Principle

> **Evidence is first-class and constrains what URACE may defensibly believe about reality.**

## Intent–Authority–Reality Principle

> **Intent defines destination, Authority defines legitimate decision ownership, Evidence constrains beliefs about reality, and URACE autonomously navigates among the possibilities consistent with all three.**

## Objective-Discovery Principle

> **URACE MUST discover justified Product Objectives without requiring the authoritative source to continuously supply tasks.**

## Priority Principle

> **Priority orders already-eligible alternatives; it does not create Authority or truth.**

## Planning Principle

> **URACE owns accepted Plan semantics while planning mechanisms remain replaceable.**

## Course-Correction Principle

> **Where Evidence weakens the current route but the governing destination remains valid, URACE SHOULD autonomously correct course rather than escalate ordinary navigation to the authoritative source.**

## Executor-Selection Principle

> **Where executor selection is delegated, URACE SHOULD autonomously select suitable execution capability according to capability, policy, cost, reliability, risk and context.**

## Decision-Basis Principle

> **Material decisions SHOULD remain reconstructable without preserving hidden chain-of-thought.**

## Stale-Decision Principle

> **Materially stale consequential decisions MUST NOT be blindly committed.**

## Proportional-Revalidation Principle

> **Revalidation SHOULD occur only to the extent required by material change and consequence, preserving both correctness and autonomous throughput.**

## Attempt–Effect Principle

> **Intending, attempting, committing, observing, validating and accepting are distinct lifecycle facts.**

## Indeterminate Principle

> **Unknown consequential effect status remains explicitly uncertain until reconciled.**

## Recovery Principle

> **Recovery resumes durable autonomous navigation rather than requiring previously established Authority and Intent to be manually reconstructed.**

## Trigger Principle

> **Trigger is a candidate reason for reassessment, not automatic action or Authority.**

## Scheduling Principle

> **Scheduling determines timing, not legitimacy.**

## Evidence-Velocity Principle

> **When uncertainty materially constrains Product evolution, URACE SHOULD autonomously prefer the smallest safe authorized action capable of producing sufficiently credible decision-relevant Evidence soon enough to improve subsequent decisions.**

## Market-Fit Principle

> **Market Fit is an Intent-relative derived outcome rather than universal Authority or universal first-class primitive.**

## Dormancy Principle

> **When no sufficiently justified authorized action exists, URACE becomes efficiently dormant rather than manufacturing work, unnecessarily requesting direction or surrendering lifecycle ownership.**

## Liveness Principle

> **Persistent autonomous ownership requires durable state and a viable path back to assessment.**

## Goldilocks Principle

> **Make only lifecycle concepts requiring independent semantics first-class; preserve Authority as a lightweight boundary rather than an approval framework; preserve Intent as destination rather than implementation prescription; preserve URACE as autonomous navigator rather than passive executor; and keep executors, Planners, Schedulers, authority mechanisms, Trigger detectors, wake mechanisms, Evidence methods and discovery mechanisms replaceable.**

---

# 94. Final Bootstrap Instruction

Bootstrap the **smallest implementation** satisfying this specification.

Do not turn URACE into:

- an executor;
- an orchestrator;
- an IAM platform;
- an RBAC framework;
- an approval workflow;
- a human-in-the-loop framework;
- an event-processing platform;
- a workflow engine;
- a scheduling framework;
- a Priority engine;
- a transaction engine;
- an experimentation framework;
- a market-fit framework;
- a heavyweight autonomous runtime.

The canonical architecture is:

```text
              AUTHORITATIVE SOURCE
                       │
                       ▼
           HIGHEST NON-DELEGATED
                    INTENT
                       │
              "destination"
                       │
                       ▼
              AUTHORITY BOUNDARY
                       │
               retained/delegated
                       │
                       ▼
          ┌────────────────────────┐
          │         URACE          │
          │                        │
          │    autonomous driver   │
          │                        │
          │ Observe                │◄──── REALITY
          │ Assess                 │       │
          │ Discover               │       │
          │ Decide                 │       │
          │ Prioritize             │       │
          │ Plan                   │       │
          │ Experiment             │       │
          │ Execute                │       │
          │ Learn                  │───────┘
          │ Correct Course         │
          │ Validate               │
          │ Recover                │
          │ Checkpoint             │
          │ Reassess               │
          │ Dormant / Wake         │
          └───────────┬────────────┘
                      │
                      ▼
              PRODUCT EVOLUTION
```

Canonical retained-destination rule:

```text
AUTHORITATIVE SOURCE
        │
        ▼
DESTINATION X
        │
        ▼
URACE DRIVES
        │
        ├── route A fails
        │
        ├── route B weakens
        │
        ├── route C improves
        │
        ▼
DESTINATION X
```

Canonical delegated-destination rule:

```text
AUTHORITATIVE SOURCE
        │
        ▼
PURPOSE X
        │
        ▼
"Choose the best Product
 realization of X"
        │
        ▼
URACE
   ┌────┼────┐
   ▼    ▼    ▼
  A     B    C
        │
        ▼
EVIDENCE + ASSESSMENT
        │
        ▼
SELECT / EVOLVE
DESTINATION
        │
        ▼
DRIVE AUTONOMOUSLY
```

Canonical authority rule:

```text
WITHIN DELEGATION
       │
       ▼
URACE DECIDES

OUTSIDE DELEGATION
       │
       ▼
URACE DOES NOT
SELF-AUTHORIZE
```

Canonical navigation rule:

```text
DESTINATION
    │
    ▼
OBSERVE REALITY
    │
    ▼
ASSESS
    │
    ▼
CHOOSE BEST AUTHORIZED ROUTE
    │
    ▼
ACT
    │
    ▼
OBSERVE EFFECT
    │
    ▼
LEARN
    │
    ▼
CORRECT COURSE
    │
    └──────────────► REPEAT
```

Canonical Evidence rule:

```text
EVIDENCE
    tells URACE
    what the sea is doing

INTENT
    tells URACE
    where it is going

AUTHORITY
    tells URACE
    which navigational and
    destination decisions it owns

URACE
    drives the boat
```

Canonical retained-decision rule:

```text
RETAINED DECISION
       │
       ▼
REQUEST AUTHORITATIVE DECISION
       │
       ├──────────────┐
       ▼              ▼
DEPENDENT WORK    INDEPENDENT WORK
    WAITS             CONTINUES
```

Canonical consequential-effect rule:

```text
AUTONOMOUS DECISION
        │
        ▼
AUTHORIZED?
   │           │
  NO          YES
   │           │
   ▼           ▼
STOP       PREPARE
               │
               ▼
       MATERIAL PREMISES
          STILL VALID?
           │       │
          NO      YES
           │       │
           ▼       ▼
       REASSESS  COMMIT
                   │
                   ▼
                OBSERVE
                   │
          ┌────────┼─────────┐
          ▼        ▼         ▼
       SUCCESS   FAILURE   UNKNOWN
          │        │         │
          │        │         ▼
          │        │   INDETERMINATE
          │        │         │
          └────────┴────┬────┘
                        ▼
                 VALIDATE /
                 RECONCILE
                        │
                        ▼
                    CHECKPOINT
```

Canonical dormant lifecycle:

```text
NO JUSTIFIED AUTHORIZED
ACTION NOW
        │
        ▼
      DORMANT
        │
        ▼
PRESERVE AUTONOMOUS OWNERSHIP
        │
 ┌──────┼───────────┬────────────┐
 │      │           │            │
AUTH. EXTERNAL   SCHEDULED    BOUNDED
CHANGE CHANGE    CONDITION    DISCOVERY
 │      │           │            │
 └──────┴───────────┴──────┬─────┘
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

Persistent autonomy is therefore:

```text
SOURCE
    picks what destination
    it wants to retain
        │
        ▼
URACE
    drives
        │
        ▼
REALITY
    informs navigation
        │
        ▼
URACE
    corrects course
        │
        ▼
DESTINATION
```

not:

```text
SOURCE
  ↓
task
  ↓
URACE
  ↓
ask what next
```

and not:

```text
URACE
  ↓
finds easier destination
  ↓
silently changes purpose
```

## Final Invariant

> **URACE persistently drives the Product toward the highest applicable non-delegated authoritative Intent. The authoritative source controls whatever destination-setting Authority it retains and may delegate any subordinate destination or navigation decision it chooses; URACE MUST preserve that retained boundary and MUST NOT invent, broaden or reason around delegation. Within valid delegated Authority, however, URACE owns the journey: it independently observes reality, discovers opportunities and problems, assesses Evidence, identifies uncertainty, chooses Objectives, prioritizes, plans, experiments, selects replaceable executors, executes, learns, corrects course, validates, checkpoints, repairs, recovers, becomes dormant and reactivates without requiring the authoritative source to navigate decisions already delegated. Evidence constrains what URACE may defensibly believe about the conditions of the journey and may justify route changes or authorized destination evolution, but Evidence, Product Value, Priority, urgency, market pressure, executor capability, recommendation and convenience MUST NOT independently change a retained destination or create Authority. When a route fails, URACE changes the route; when a delegated destination should change, URACE may change it when sufficiently justified; when a retained destination appears infeasible, URACE preserves reality and the authoritative boundary rather than silently redefining either. Retained, denied or unresolved decisions block only dependent scope where possible, while independent authorized Product evolution continues. Materially stale consequential decisions are proportionately revalidated without converting Authority into an approval loop; attempts, effects, observations, validation and acceptance remain distinct; uncertain effects remain explicitly indeterminate until reconciled; accepted progress is checkpointed; and persistent autonomous ownership remains live through both active operation and efficient dormancy until an explicit authoritative terminal condition ends it. In short: the authoritative source chooses the destination it wishes to retain; URACE drives the boat.**