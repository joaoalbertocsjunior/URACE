# URACE — Universal Recursive Autonomous Co-Founder Engine

**Specification version: 2026-10-17-r72**

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

**First-class vs. derived distinction.** A concept is **first-class** when its durable record is a required citizen schema produced by the lifecycle; first-class concepts require §62b schema definitions and are stored in the State Document. A concept is **derived** when it is computed from first-class records at read time and requires no stored citizen; derived concepts require §62d contract definitions or formula specifications. A concept is **contextual** when its value depends on current evaluation parameters and has no stable storable form. This distinction governs schema promotion decisions throughout the specification.

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

**Operational test condition for Evidence Integrity.** Evidence MUST preserve provenance, method, and source identity such that independence can be verified by reconciliation against the originating source. Evidence whose provenance is undeclarable MUST NOT be used in lifecycle navigation decisions. When Evidence integrity is disputed, URACE MUST emit an IntegrityGap of severity BLOCKING and hold any dependent decision until the dispute is resolved. The SignalClassifier (§62c) classifies this condition as an `IntegritySignal` (§62b) of kind `PROVENANCE_UNDECLARABLE`.

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

**Minimum assessment contract.** When Evidence is material to a navigation decision, URACE MUST assess at minimum: (a) credibility — provenance and method are declared and traceable; (b) relevance — the observation applies to the specific decision being made; (c) decision usefulness — accepting or rejecting the Evidence materially changes navigation. The remaining dimensions SHOULD be assessed when feasible; their omission MUST be recorded as an explicit uncertainty qualifier on the dependent DecisionRecord.

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

**Evidence–prediction conflict definition.** A conflict exists when: (a) external Evidence predicts outcome O with credibility C_ext; (b) the internal lifecycle assessment predicts ¬O with confidence C_int; and (c) C_int < C_ext and the two outcomes are mutually exclusive in the decision scope. When conflict is detected, URACE MUST record both as competing hypotheses in the lifecycle Evidence log and MUST NOT discard the lower-confidence prediction. The conflict MUST be surfaced as an irreducible uncertainty until one hypothesis is either falsified or superseded.

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

**DiscoveryRecord citizen schema.** Each discovery cycle MUST produce a DiscoveryRecord capturing what was found, what was evaluated, and what was surfaced.

```
DiscoveryRecord {
  id                      REQUIRED  Identifier; prefix "dsc-"
  cycle_id                REQUIRED  string; stable ID for this discovery run
  started_at              REQUIRED  string; ISO-8601 timestamp
  completed_at            OPTIONAL  string; ISO-8601 timestamp; absent if interrupted
  cycle_status            REQUIRED  DiscoveryCycleStatus
  categories_evaluated    REQUIRED  list of string; e.g. "goals", "triggers", "pending_objectives"
  categories_skipped      OPTIONAL  list of DiscoverySkip; skipped categories with reason
  candidates_found        REQUIRED  int; count of candidate Objectives surfaced
  candidates_rejected     REQUIRED  int; count of candidates evaluated and rejected
  surfaced_objective_ids  OPTIONAL  list of string; Objective IDs promoted to eligible
  budget_status           OPTIONAL  string; DiscoveryBudgetStatus value at start of cycle
  error_detail            OPTIONAL  string; set when cycle_status = ERROR_INTERRUPTED
}

DiscoverySkip {
  category    REQUIRED  string
  reason      REQUIRED  string; "capability_unavailable" | "resource_constraint" | "error"
  blocked_on  OPTIONAL  string; what must change before this category can be evaluated
}
```
Uses canonical: TemporalFields (started_at as created_at, completed_at). Used in: State.discovery_records.

**DiscoveryCycleStatus enum.**
```
COMPLETE           — all registered input categories evaluated; dormancy conclusion authoritative
INCOMPLETE         — capability or resource gap prevented full evaluation; dormancy conclusion not authoritative
ERROR_INTERRUPTED  — enumeration error; specific category and error preserved; requires recovery
```

**Discovery scoring contract.** The question "what most justifies action now?" is answered by ranking each candidate Objective on: `score = (intent_alignment × evidence_weight) + information_gain − cost − risk`. Intent alignment is computed from the Objective's relationship to governing Intent (direct → 1.0; indirect → 0.5; tangential → 0.1). Evidence weight is the credibility-weighted sum of supporting Evidence. Information gain is estimated from uncertainty reduction. Cost and risk reduce the score proportionally. The highest-scoring eligible authorized Objective is selected.

**State Document.** `discovery_records` OPTIONAL list of DiscoveryRecord.

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

The assessment cycle implements AP8 — Fixpoint Calculus (§62i): gaps are detected iteratively until convergence is reached (no new gaps surfaced in the current cycle).

**AssessmentRecord citizen schema.** Every assessment cycle boundary SHOULD produce an AssessmentRecord — a durable record of what was evaluated and what was concluded.

```
AssessmentRecord {
  id                   REQUIRED  Identifier; prefix "asr-"
  assessed_at          REQUIRED  string; ISO-8601 timestamp
  lifecycle_phase      REQUIRED  string; which phase triggered this assessment
  authority_ids        REQUIRED  list of string; Authority record IDs evaluated
  intent_id            REQUIRED  string; governing Intent ID at assessment time
  evidence_ids         OPTIONAL  list of string; Evidence IDs considered
  technique_results    OPTIONAL  map of technique_id → SD result; from TAS (§62h)
  discovered_objective_ids OPTIONAL list of string; Objective IDs surfaced
  blocked_categories   OPTIONAL  list of string; categories skipped with reason
  cycle_status         REQUIRED  AssessmentCycleStatus
  incomplete_reason    OPTIONAL  string; set when cycle_status != COMPLETE
}
```
Uses canonical: TemporalFields (assessed_at as created_at). Used in: State.assessment_records.

**AssessmentCycleStatus enum.**
```
COMPLETE           — all input categories evaluated; conclusion is authoritative
CAPABILITY_SKIPPED — one or more categories skipped due to unavailable capability
ERROR_INTERRUPTED  — enumeration error halted the cycle; conclusion is partial
```

**TAS wiring.** Each assessment cycle MUST invoke the TechniqueApplicabilityGate (§62h) before selecting techniques. The gate's per-technique SD result MUST be recorded in `AssessmentRecord.technique_results`. An assessment that skips the gate violates the technique applicability contract.

**State Document.** `assessment_records` OPTIONAL list of AssessmentRecord.

**Scope:** TAS domain (§62h) and assessment cycle (§37)

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

The discovery context provided to an Executor MUST include the spec structural audit summary when available (§80). The reasoning memory is a bounded configurable store: its maximum entry count MUST be configurable via `efficiency.max_reasoning_memory_entries` and MUST NOT grow unboundedly. When the ceiling is reached, entries MUST be evicted in order of lowest-confidence, shortest-hypothesis-age, and least-recently-observed, preserving active high-confidence patterns.

Queued authoritative inputs awaiting application implement AP14 — Durable Inbox (§62i), ensuring FIFO ordering and idempotent processing across lifecycle boundaries.

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

**Priority scoring.** The canonical scoring formula for Objective priority is defined in §36 (Open-Ended Discovery). Priority assessment MUST apply that formula when scoring competing Objectives. The three core factors — expected value, risk reduction, and time sensitivity — MUST be weighted as defined in the §36 formula; manual overrides MUST be recorded as a DecisionRecord citing the deviation.

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

**Operation dependency graph.** When Plan.dependencies is populated, each entry MUST conform to the OperationDependency schema (§62b). The dependency set MUST be acyclic; URACE MUST validate the DAG invariant before scheduling any operation in the plan. Topological evaluation order applies: FOUNDATIONAL-tier dependencies MUST be resolved before COMPOSITIONAL, which MUST be resolved before INTEGRATED (AP24 ordering, §62i).

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

**Plan acceptance criteria.** URACE MUST validate a proposed Plan before accepting it: (a) all declared steps are achievable within applicable Authority; (b) dependencies form an acyclic DAG; (c) the Objective's success measure is operationalizable against at least one tracked metric or observable criterion; (d) resource and time estimates are feasible under current capacity. A Plan that fails any criterion MUST be rejected with a named gap citing the failing criterion. Rejection MUST NOT close the Objective; the Objective remains active pending a revised Plan.

---

# 42. Scheduling

Scheduling determines when planned work or reassessment becomes useful. Durable time-based and trigger-based scheduling implements AP18 — Scheduled Task Contract (§62i).

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

When an Executor returns an authentication failure or permanent configuration failure — including an invalid or expired credential, a rejected model identifier, or an account-level configuration incompatibility — during the execution of a task rather than at a pre-dispatch availability probe, URACE MUST treat that failure as a scheduled-unavailability condition rather than an immediately retryable task error. URACE MUST apply at least the configured minimum backoff period before attempting another dispatch to the same Executor; the implementation MUST NOT immediately re-dispatch the same task to the same Executor without an intervening availability probe that confirms the configuration condition is resolved. An execution-time authentication failure MUST be attributed to the Executor's `CONFIGURED` or `AVAILABLE` state, not its `AUTHENTICATED` state, until a subsequent successful probe re-establishes authentication. This class of failure is distinct from transient provider-capacity exhaustion — it signals a configuration-level condition requiring operator action rather than a time-bounded capacity window — and MUST NOT be conflated with it in the inspection output or in retry scheduling.

Where unavailable capability blocks justified work, URACE SHOULD preserve a proportionate way to observe capability availability. A material unavailable-to-available transition SHOULD become a Trigger for immediate reassessment. Repeated unchanged unavailability SHOULD be deduplicated or rate-limited rather than producing a retry storm.

When all currently attached and eligible Executors collectively lack a capability required by a planned Operation — distinct from those Executors being unavailable, unauthenticated, over budget, or in probe-pending state — URACE MUST surface a named `CAPABILITY_UNAVAILABLE` condition in the lifecycle inspection output, identifying the specific absent capability and the Operations it blocks. `CAPABILITY_UNAVAILABLE` MUST block only Operations that require the absent capability; Executor-independent Operations and Operations within available Executor capabilities MUST continue unblocked. URACE MUST NOT conflate a capability gap with an Executor availability gap, authentication failure, budget exhaustion, or the zero-Executor cardinality condition defined in §55. Attaching an Executor whose capability contract satisfies the requirement resolves the condition; it is not resolved by re-verifying authentication or waiting for provider capacity.

The authoritative source does not need to select each executor.

When the same Executor failure pattern — identified by identical error classification, stage, and Executor identity — recurs across a configurable consecutive-failure threshold within the current availability window, URACE MUST classify the recurrence as a systematic adapter-configuration failure rather than a transient dispatch error. A systematic failure MUST suppress further dispatch attempts to the affected Executor for at least the configured minimum backoff period; URACE MUST NOT continue attempting the same dispatch on every cycle as if the failure were transient. The failure classification and its cooldown MUST be surfaced in the inspection output so the operator can distinguish a repeating systematic error from a one-off transient failure. Resolving a systematic failure requires an operator action — a credential rotation, configuration correction, or explicit reset — rather than elapsed time alone; the cooldown MUST be renewable rather than self-clearing at its expiry unless the subsequent probe confirms the condition is resolved.

When an Executor becomes permanently unavailable during an active Operation — through abrupt termination, resource exhaustion, timeout or loss of connectivity before the Operation result can be observed — URACE MUST treat the uncommitted portion of that Operation as `INDETERMINATE` and apply the same durable preservation and reconciliation requirements as §52. URACE MUST NOT re-dispatch the same Operation to a replacement Executor without first reconciling whether the original invocation committed an externally observable effect; reconciliation MUST use the strongest available target-system query, transaction or reference ID, durable artifact or deterministic probe. If reconciliation cannot establish whether an external effect occurred, the Operation MUST remain `INDETERMINATE` and the original effect record MUST be preserved; a replacement Executor MUST NOT be used to retry an unreconciled consequential effect.

When an Executor returns a failure attributable to a transient network condition — including a provider-side infrastructure disconnect, upstream connection reset, stream disconnection, or equivalent low-level transport error that does not indicate an authentication, authorization, capability, or provider-capacity gap — URACE MUST classify that failure as a short-backoff retriable condition and MUST NOT apply the longer backoff period reserved for authentication or configuration failures. A transient network failure MUST NOT increment the consecutive-failure counter used for systematic failure detection under §43; a single transport-layer disconnect does not constitute evidence of a repeating adapter-configuration problem. The minimum backoff for a transient network failure SHOULD be significantly shorter than the authentication-failure backoff and SHOULD be configurable independently. URACE MUST NOT conflate transient network failures with authentication failures, capability gaps, or provider-capacity exhaustion in the inspection output or in retry scheduling.

The backoff, consecutive-failure threshold, and cooldown behavior in this section implement AP10 — Bounded Retry with Backoff (§62i), which requires AP4 — Producer-Consumer Contract (§62i) to define retry boundaries and obligations. Effect reconciliation before re-dispatch implements AP6 — Causal Provenance Chain (§62i).

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

This records decision basis, not hidden chain-of-thought. The formal canonical schema for DecisionRecord — including all field types, required/optional status, invariant contracts and provenance lifecycle — is defined in §62d. The loose notation above is a navigational reference; the §62d definition is authoritative for any implementation.

**Canonical state key.** Decision records MUST be persisted under `state["decision_records"]`. The key `state["decisions"]` MUST NOT be used as a canonical store for DecisionRecord instances; any implementation using that key for DecisionRecord persistence violates this section and §62d. `urace why` traversal and §62g reasoning-chain operations MUST read exclusively from `state["decision_records"]`. See §62g for traversal semantics and `urace why` command specification.

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

This section formalizes AP5 — Idempotency Contract (§62i) and AP4 — Producer-Consumer Contract (§62i) for lifecycle operations: applying an operation N times produces the same result as applying it once. Retries across lifecycle boundaries require both the idempotency guarantee and an explicit contract that the effect was or was not produced. Where retries could duplicate consequential effects, stable Operation identity or equivalent idempotency semantics SHOULD be used.

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

**Effect-type taxonomy.** Effects subject to reconciliation are classified as: (1) `IDEMPOTENT` — safe to re-apply; the operation produces the same result regardless of how many times it has been applied (e.g., file write with fixed content, schema validation). (2) `QUERY` — read-only; produces no side effects; safe to retry unconditionally. (3) `STATEFUL` — mutates external state; re-application may produce different results (e.g., API calls, database writes). (4) `ASYNC` — the effect is submitted but completion is not synchronously confirmed. Each Operation MUST declare its effect type in the `effect_type` field.

**Reconciliation-strategy matrix.**

| Effect Type | Reconciliation Strategy | Timeout | On Timeout |
|-------------|------------------------|---------|------------|
| IDEMPOTENT | Re-apply unconditionally | 30s | Mark RECONCILED |
| QUERY | Re-execute and compare result | 15s | Mark UNCERTAIN |
| STATEFUL | Query external state; compare before/after snapshot | 60s | Mark UNCERTAIN, surface WARNING |
| ASYNC | Poll completion endpoint up to 3 times with 10s interval | 30s per poll | Mark UNCERTAIN after 3 failures |

**Unreconcilable effect handling.** An Operation that remains in `UNCERTAIN` state after reconciliation strategy exhaustion MUST be surfaced as a WARNING gap of kind `effect-unreconcilable`. The Operation MUST NOT be retried autonomously. Operator review MUST be required before the Operation can be closed or its effect assumed complete.

# 53. Effect Reconciliation

Effect reconciliation implements AP6 — Causal Provenance Chain (§62i): every recovery disposition MUST become Evidence, enabling causal traceability and reconstruction of effect status across restarts.

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

This acceptance boundary implements **AP27 — Transaction Recovery Protocol** (§62i).

The four-phase journal and crash-recovery sequence implement **AP27 — Transaction Recovery Protocol** (§62i).

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

This stable-version management protocol is governed by **AP22 — Checkpoint** (§62i).

Where autonomous evolution may modify authoritative or continuity-critical Product artifacts, URACE SHOULD retain or reconstruct a last-known-stable accepted version independently of the mutable working copy.

Before promoting a new stable version, URACE MUST validate applicable protected structure, invariants, guardrails and cross-artifact consistency. Promotion MUST occur only after durable acceptance.

When an authoritative specification change can alter user-facing, operational, bootstrap or integration semantics described by dependent guidance, URACE MUST review that guidance in the same increment and update it where needed. The accepted checkpoint MUST represent one coherent cross-artifact version; unchanged dependent guidance SHOULD remain attributable to an explicit consistency review rather than omission.

If interruption, corruption or a later integrity check shows that the working Product is broken or materially degraded relative to protected validation criteria, URACE MUST restore the last-known-stable accepted version, repair from it, or preserve explicit uncertainty when safe restoration cannot be established. Restoration MUST become Evidence and MUST NOT silently erase a newer accepted checkpoint.

Stable fallback is a recovery boundary, not permission to reject valid authorized evolution merely because it differs from an older version.

---

**Canonical protocol.** Effect uncertainty handling across this section and §52 implements the **EffectUncertaintyProtocol** (§62l). All subsections that classify effects as INDETERMINATE, require reconciliation before retry, or preserve durable uncertainty records apply that protocol. Sections throughout the spec that reference INDETERMINATE handling cite §62l EffectUncertaintyProtocol rather than restating these three steps.


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
ACCEPTED  ← explicit transitional status
      │
      ▼
ACCEPTED PRODUCT STATE → ACTIVE lifecycle
```

`done` is not a checkpoint.

An Operation passes through a distinct `ACCEPTED` status between independent validation passing and the lifecycle becoming `ACTIVE` again. The `ACCEPTED` status records that the validation gate was satisfied; the subsequent transition to `ACTIVE` records that the lifecycle is ready for new work. These MUST NOT be collapsed into a single transition; each MUST be recorded as a durable status-transition event. An implementation that moves directly from `VALIDATING` to `ACTIVE` without an intervening `ACCEPTED` record MUST surface this as a `missing-acceptance-status` WARNING in the lifecycle inspection output.

The executor≠validator separation, pending-preservation, and capability-restoration trigger implement **AP28 — Independent Validation Gate** (§62i).

An Executor result, claim or completion signal MUST be treated as an Observation until independent validation confirms it satisfies applicable guardrails, integrity checks and Authorization boundaries. URACE MUST NOT advance Product state from Observation to Accepted solely because an Executor reports completion; advancement requires an explicit attributable validation act that was not performed by the same execution context that produced the result. Where validation capability is temporarily unavailable, the Observation MUST be preserved as pending validation rather than automatically accepted by elapsed time or repeated Executor confirmation. A model's self-assessed certainty, a confidence score or a second invocation of the same Executor MUST NOT substitute for an independent validation boundary.

When validation capability that was temporarily unavailable becomes available, URACE MUST treat the restoration as a qualifying reassessment Trigger for all Observations preserved in pending-validation state due to that capability's absence. The capability restoration event MUST NOT require a separate incoming Observation or external Event before pending-validation items receive a reassessment opportunity; the restoration itself is the qualifying condition. A pending-validation Observation MUST NOT be abandoned, expired by elapsed time, or automatically accepted solely based on Executor re-confirmation before a capable independent validation attempt is made following capability restoration.

When an independent validation attempt executes against an Observation but returns an inconclusive or ambiguous disposition — where validation capability was present and ran but could not produce a conclusive pass or fail, for example due to a validation-rule evaluation error, an incomplete result schema or an inability to assess a required criterion — URACE MUST preserve the Observation as pending validation, MUST record the inconclusive attempt with its specific unresolvable criterion as attribution on the Observation, and MUST NOT treat a completed-but-inconclusive attempt as equivalent to validation capability unavailability. An inconclusive validation result requires diagnosing the validation rule or criterion rather than waiting for a capability restoration event. An Observation that accumulates only inconclusive attempts without a conclusive pass MUST NOT be advanced to accepted Product state; repeated inconclusive results from the same validation path MUST NOT escalate to acceptance by elapsed time, attempt count or Executor re-confirmation.

Observations preserved in pending-validation state implement AP14 — Durable Inbox (§62i), ensuring crash-safe FIFO preservation until validation capability is restored.

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

When the system is decelerating — when current_velocity < (0.8 × baseline_velocity) or trend_slope is negative over three consecutive checkpoints — URACE SHOULD surface this as an alert and MAY autonomously inject a strategic reassessment Objective to recover value production rate. Self-correction authority for injecting such an Objective derives from existing delegated Authority; value deceleration is Evidence, not Authority to act outside delegated scope.

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

Value production velocity tracks lifecycle health across time; it does not create Authority or bypass validation, Checkpoint or constraint requirements. Rolling velocity convergence and deceleration detection implement AP8 — Fixpoint Calculus (§62i).

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

**MarketSignal citizen schema.** A MarketSignal is a credible, time-stamped external observation bearing on whether the Product's current direction satisfies a market-dependent outcome.

```
MarketSignal {
  id              REQUIRED  Identifier; prefix "mks-"
  kind            REQUIRED  MarketSignalKind
  observed_at     REQUIRED  string; ISO-8601 timestamp
  source          REQUIRED  string; origin of the signal (e.g. "user-interview", "metric-system", "external-api")
  description     REQUIRED  string; human-readable signal description
  confidence      REQUIRED  FitConfidence
  intent_id       REQUIRED  string; governing Intent this signal is relative to
  evidence_ids    OPTIONAL  list of string; Evidence IDs that carry the underlying data
  hypothesis_ids  OPTIONAL  list of string; FitHypothesis IDs this signal informs
}
```
Uses canonical: TemporalFields (observed_at as created_at). Used in: State.market_signals.

**FitHypothesis citizen schema.** A FitHypothesis is a falsifiable belief about whether a specific Product behavior or outcome contributes to market fit under governing Intent.

```
FitHypothesis {
  id              REQUIRED  Identifier; prefix "fhy-"
  description     REQUIRED  string; the falsifiable claim
  intent_id       REQUIRED  string; governing Intent this hypothesis is relative to
  status          REQUIRED  FitHypothesisStatus
  confidence      REQUIRED  FitConfidence
  supporting_signal_ids  OPTIONAL  list of string; MarketSignal IDs that support
  refuting_signal_ids    OPTIONAL  list of string; MarketSignal IDs that refute
  created_at      REQUIRED  string; ISO-8601 timestamp
  last_updated_at REQUIRED  string; ISO-8601 timestamp
}
```
Uses canonical: TemporalFields (created_at, last_updated_at as updated_at). Used in: State.fit_hypotheses.

**MarketSignalKind enum.**
```
USER_BEHAVIOR     — observed user action or usage pattern
USER_FEEDBACK     — direct user statement or survey response
RETENTION_SIGNAL  — cohort retention, churn, or re-engagement metric
CONVERSION_SIGNAL — funnel or activation metric
COMPETITOR_SIGNAL — market positioning or competitive movement
EXTERNAL_METRIC   — third-party or platform metric
REVENUE_SIGNAL    — payment, subscription, or monetization event
```

**FitConfidence enum.**
```
STRONG    — multiple corroborating independent signals; high credibility
MODERATE  — some corroboration; credible but not conclusive
WEAK      — single signal; low corroboration; treat as hypothesis prompt only
ABSENT    — no current supporting signal; hypothesis is ungrounded
```

**FitHypothesisStatus enum.**
```
ACTIVE      — hypothesis is current; URACE may act on it within Authority
VALIDATED   — sufficient Evidence confirms the hypothesis; treated as a navigation anchor
REFUTED     — sufficient Evidence contradicts the hypothesis; URACE must not rely on it
STALE       — no fresh signal has updated the hypothesis within the staleness window
```

**Market-feedback integration.** URACE MUST evaluate active FitHypotheses during each assessment cycle when the Product is in FORMING, CAPABLE, or OPTIMIZED maturity. A VALIDATED hypothesis with HIGH confidence MAY inform route selection within delegated Authority. A REFUTED hypothesis MUST trigger reassessment of any Plan that relied on it. A STALE hypothesis MUST surface as a PendingValidation. MarketSignal does not create Authority.

**State Document.** `market_signals` OPTIONAL list of MarketSignal; `fit_hypotheses` OPTIONAL list of FitHypothesis.

# 59b. Product Capable Evolution

Not all progress is improvement. A Product reaches its **capable sweet spot** when every required capability is present, complexity remains within its declared envelope, and value density — the ratio of delivered value to product surface area — meets or exceeds its configured floor. Growth beyond that point is not advancement; it is scope creep and maintenance burden.

**Capable ≠ Maximal.** The goal of Product evolution is not to maximize scope, feature count, or quality scores in isolation. It is to reach and sustain the smallest, most cohesive Product surface that fully satisfies governing Intent.

**Four evolution phases** (preceded by the one-time onboard gate — §62o):
```text
ONBOARDING (gate) → BOOTSTRAPPING → FORMING → CAPABLE → OPTIMIZED → OVER_ENGINEERED
```
- `BOOTSTRAPPING`: core capabilities not yet defined or partially absent
- `FORMING`: capabilities being built out; completeness below target
- `CAPABLE`: all required capabilities present; complexity within envelope; value density above floor — the **sweet spot**
- `OPTIMIZED`: capable state with demonstrably improved value density; still within envelope
- `OVER_ENGINEERED`: capability or complexity exceeds envelope ceiling; value density declining

**Four evolution modes, mapped to contribution kind:**
- `CAPABILITY_DEFINING`: establishes a new required capability; valid only in BOOTSTRAPPING/FORMING
- `CAPABILITY_COMPLETING`: brings a PARTIAL capability to CAPABLE; valid only in FORMING
- `QUALITY_IMPROVING`: raises quality of an existing CAPABLE capability without expanding surface; always valid
- `COMPLEXITY_REDUCING`: reduces surface while preserving capability; always valid
- `MILESTONE_TARGETING`: explicitly targets achieving a declared ProductMilestone gate; valid while milestone is active

**Governing invariant.** When a Product has reached `CAPABLE` maturity level, URACE MUST NOT select objectives of kind `CAPABILITY_DEFINING` unless a governing authority explicitly authorizes capability scope expansion. Adding capability to an already-capable Product is a scope decision, not an autonomous improvement decision. `COMPLEXITY_REDUCING` and `QUALITY_IMPROVING` remain autonomously authorized at any maturity level.

**Value density.** `value_density = sum(capability.value_weight × (capability_status == CAPABLE ? 1.0 : completeness_fraction)) / product_surface_measure`. A declining value density trend after reaching CAPABLE signals over-engineering risk. URACE MUST surface value density as a core vital alongside quality streak and execution budget. `SD(ValueDensity, S) = True` — locally computable.

**Capability Envelope Gate.** A change that increases product surface measure (lines, schemas, mechanisms, AP patterns) beyond the configured complexity ceiling while the Product is already at CAPABLE or OPTIMIZED maturity MUST be gated. URACE MUST emit an IntegrityGap(kind="capability-envelope-breach", severity=WARNING) and MUST NOT accept the change without a DecisionRecord explicitly justifying the surface expansion.

**Milestone Progression Chain.** Milestones are not isolated gates — they form an ordered chain. Each milestone declares the `version` it produces when achieved and optionally a `next_milestone_id` pointing to the next milestone to activate. When a milestone transitions to ACHIEVED:
1. A `ProductVersion` record is written to `State.product_versions` carrying the milestone's version string, maturity level, and all capability/quality/density measurements at the moment of achievement.
2. If `next_milestone_id` is declared, the referenced milestone transitions from PENDING to ACTIVE. This creates a continuous improvement loop: achieving one capable sweet spot immediately targets the next.
3. URACE MUST NOT loop back to a previous milestone (ACHIEVED milestones are immutable).

**Continuous improvement loop.**
```text
MILESTONE N ──active──► gates evaluated each cycle
        │
    all gates satisfied
        │
        ▼
  MILESTONE N achieved → ProductVersion vN.0 written
        │
  next_milestone_id?
     YES │                      NO │
         ▼                         ▼
  MILESTONE N+1 → ACTIVE      stay CAPABLE/OPTIMIZED
  (higher gates, richer sweet spot)
```

**ProductVersion.** Every achieved milestone produces exactly one `ProductVersion` record — a durable, versioned snapshot of the Product at its capable sweet spot. ProductVersion is the answer to "what version is this Product?" — not a git tag, not a line count, but a capability-certified milestone achievement.

**Tests as Product citizens.** A capability CANNOT reach `CAPABLE` status without a passing `TestRunRecord` of kind `CAPABILITY_GATE` or `ACCEPTANCE` that declares the capability in `capability_ids_covered`. An assessment cycle that marks a capability CAPABLE without a passing TestRunRecord MUST surface IntegrityGap(kind="capability-without-test-coverage", severity=WARNING). This ensures the capable sweet spot is verifiably achieved, not merely asserted.

---

# 60. Validation and Acceptance

Executor confidence is not validation. `accept(op) ↔ validate(op).verdict = VALIDATED ∧ ¬rollback_needed(op)` Snapshot-before/after state preservation and atomic delta journaling implement AP16 — State Snapshot + Delta Log (§62i). Validation of Authority compliance, Intent consistency, schema conformance, and constraint satisfaction implements AP2 — Citizen Schema (§62i).

**Compliance recording contract.** This contract implements **AP37 — Compliance Posture Tracker** (§62i) and **ComplianceRecordingContract** (§62l). After every independent validation gate evaluation, the lifecycle MUST append one ComplianceRecord per domain evaluated, and MUST update the corresponding ComplianceState entry. A validation gate evaluation that does not produce a ComplianceRecord for each assessed domain is a `compliance-record-missing` WARNING IntegrityGap. This canonizes what the gate already evaluates — it adds persistence and queryability, not new validation behavior.

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

This subsection implements AP13 — Observer (§62i): the lifecycle (producer) emits structured feedback to a channel that observers read without the lifecycle coupling to them. The MACHINE channel is the AP13 broadcast surface; human and machine channels are independent.

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

**Feedback verbosity modes.** An implementation MUST support three feedback verbosity modes. **NON-VERBOSE** (default) MUST include at minimum: lifecycle state, cycle outcome, activity summary, changed artifacts, validation status, `discovery_defer_reason` when `discovery_budget_status` is any deferral state, progress vector when non-null, and a `recovery-pending` notice when `ExecutorState.recovery_manifest` is non-null. **VERBOSE** MUST include everything in NON-VERBOSE plus: decision basis, applicable Authority, candidate comparison, planned steps, per-metric detail with trend and target, executor efficiency vitals, evolution vitals, resource accounting, self-evolution policy, reasoning memory summary, progress stagnant cycle count, and full RecoveryManifest fields when non-null. **MACHINE** MUST emit a complete structured event as a parseable JSON document containing all fields from VERBOSE; the MACHINE channel MUST be preserved independently of the human channel and MUST NOT be suppressed by quiet-human mode. A dedicated safety-override invocation parameter (e.g. a `--safe` flag) is intentionally absent from autonomous operation: safety guarantees are provided by Authority resolution, the TechniqueApplicabilityGate, the repair-exhausted RecoveryManifest protocol, and the ExecutionBudget floor — these operate unconditionally and do not require an invocation flag to activate.

**RecoveryManifest surfacing contract.** When `ExecutorState.recovery_manifest` is non-null, every lifecycle feedback emission MUST include a named `recovery-pending` notice regardless of verbosity mode. In NON-VERBOSE mode, the notice MUST include at minimum: `manifest_id`, `emission_cause`, `progress_at_emit`, and a `goal_delta` summary. In VERBOSE mode, the full manifest fields MUST be expanded. In MACHINE mode, the complete RecoveryManifest object MUST appear in the cycle event under key `recovery_manifest`. A `recovery-pending` notice MUST NOT be suppressed by quiet-human mode, because an outstanding RecoveryManifest constitutes a material deterioration event under the silence-prohibition at §2451.

**Discovery-deferral surfacing contract.** When `ExecutorState.discovery_budget_status` is any deferral state — `SYSTEMATIC_FAILURE_COOLDOWN`, `DAILY_LIMIT_OR_RESERVE_REACHED`, `MONTHLY_LIMIT_OR_RESERVE_REACHED`, `DUPLICATE_TRIGGER_SUPPRESSED`, `DEFERRED_PROPORTIONALITY`, `DISCOVERY_YIELD_EXHAUSTED`, or `WAITING_PROVIDER_CAPACITY` — the `discovery_defer_reason` MUST be included in both NON-VERBOSE and VERBOSE feedback output whenever non-null, and MUST be included in the MACHINE event. Restricting discovery-deferral surfacing to a subset of deferral states violates this contract.

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

This section implements **AP22 — Checkpoint** (§62i).

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

## Rule Schema

Every Rule record stored in the Ledger MUST conform to the following schema. An implementation that omits a REQUIRED field or stores a PROHIBITED field in its place violates this contract and MUST surface the violation as a named Ledger integrity gap.

```
Rule {
  id               REQUIRED  stable collision-resistant identifier (prefix encodes kind)
  kind             REQUIRED  PURPOSE | DIRECTIVE | PERMISSION | PROHIBITION | OBJECTIVE | POLICY
  level            PROHIBITED as a stored field — MUST be derived from kind at read time, never persisted
  statement        REQUIRED  human-readable governance statement
  scope            REQUIRED  list of operation scopes this rule governs; "*" means all scopes
  derivation       REQUIRED  EXPLICIT | SYSTEM_INFERRED
  confidence       REQUIRED  0.0–1.0; MUST be 1.0 for EXPLICIT rules
  source           REQUIRED  identifier of who or what created this rule (input id, bootstrap, system)
  derived_from     REQUIRED  list of rule_ids this rule was derived from; empty list for root rules
  superseded_by    REQUIRED  rule_id of the superseding rule, or null if still active
  active_since     REQUIRED  timestamp when this rule became active (serves as created_at)
  active_until     REQUIRED  timestamp when this rule was deactivated or superseded, or null
  updated_at       REQUIRED  timestamp of last mutation to any mutable field on this rule
  deleted_at       OPTIONAL  timestamp | null; explicit soft-delete; null = not deleted
                             (a superseded rule is NOT deleted; deleted_at is only set by deactivate_rule)
  expires_at       OPTIONAL  timestamp for time-bounded OBJECTIVE rules; null if unbounded
  governed_changes REQUIRED  list of change_ids accepted while this rule was active and governing
  tags             OPTIONAL  list of string labels for grouping or filtering
}
```

Uses TemporalFields: active_since (as created_at), active_until, updated_at, deleted_at, expires_at.
Uses canonical: Identifier (id), ProductScope (scope entries), UnitFloat (confidence).

**`level` derivation contract.** The level of a rule MUST be derived from its `kind` at read time: PURPOSE → 0; DIRECTIVE, PERMISSION, PROHIBITION → 1; OBJECTIVE, POLICY → 2. Storing `level` as a persistent field is prohibited; any stored `level` field MUST be ignored and recomputed.

**`id` stability contract (AP0 — Citizen, §62i).** A rule's `id` MUST NOT change after the rule is created. The `id` MUST be unique within the Ledger for all time, including deactivated and superseded rules.

**`confidence` contract.** An EXPLICIT rule MUST carry `confidence: 1.0`. A SYSTEM_INFERRED rule MUST carry a confidence value strictly less than 1.0 computed from the derivation basis. A rule whose confidence drops to 0.0 MUST be deactivated.

## Change Schema

Every Change binding record stored in the Ledger MUST conform to the following schema. An implementation that omits a REQUIRED field violates this contract and MUST surface the violation as a named Ledger integrity gap.

```
Change {
  id                    REQUIRED  stable identifier matching the accepted operation id
  kind                  REQUIRED  ACCEPTED | REJECTED | ROLLED_BACK
  at                    REQUIRED  timestamp of the outcome
  description           REQUIRED  human-readable summary of what changed
  scope                 REQUIRED  operation scope under which this change executed
  governed_by           REQUIRED  list of rule_ids active and governing at time of change
  rule_snapshot_digest  REQUIRED  SHA-256 of the lexicographically sorted active rule set at time of change
  state_before_digest   REQUIRED  SHA-256 of the product state immediately before this change
  state_after_digest    REQUIRED  SHA-256 of the product state immediately after this change; null for REJECTED
  delta_to_rules        REQUIRED  list of rule_ids that were themselves added, superseded, or deactivated
                                  by this operation; empty list for changes that did not mutate the Ledger
  executor              REQUIRED  ExecutorAttribution; the executor that produced this change
  validation            REQUIRED  ChangeValidation; lifecycle disposition record
  value_delta           REQUIRED  float; net metric movement (improved dimensions minus regressed)
}
```

Uses canonical: DigestValue (rule_snapshot_digest, state_before_digest, state_after_digest), ExecutorAttribution (executor), ChangeValidation (validation), TemporalFields (at as created_at).

**`rule_snapshot_digest` contract.** The digest MUST be computed as the SHA-256 of the JSON-serialised list of `{id, kind, statement}` for every active rule, sorted lexicographically by `id`, with no whitespace. This algorithm is fixed; an implementation MUST NOT vary the serialisation.

**`delta_to_rules` contract.** For any change that adds, supersedes, or deactivates a rule in the Ledger, the affected rule_ids MUST appear in `delta_to_rules`. A change with an empty `delta_to_rules` MUST NOT have caused any mutation to the Ledger's active rule set.

**`state_before_digest` / `state_after_digest` contract.** Both digests MUST be computed from the same deterministic product-state serialisation method used by §61 checkpoints. `state_after_digest` MUST be null for REJECTED changes. The pair provides an independent integrity check: `state_after_digest` of change N MUST equal `state_before_digest` of change N+1 in sequence.

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

**Canonical threshold values.** `INFER_BLOCKING = 0.85` (the confidence level at which a SYSTEM_INFERRED rule becomes blocking; configurable via POLICY rule override). The value 0.85 MUST be the default used when no POLICY rule overrides it. An implementation that uses a different hardcoded default violates reproducibility.

**Canonical scalar domains.** The domain constraints for all canonical scalars are defined in §62i Canonical Scalar Catalog. Any field declared with a scalar type in §62b MUST satisfy the domain constraint at write time. A validation primitive (§62d) that accepts a value outside the declared domain is a runtime conformance violation.

URACE MUST NOT promote a SYSTEM_INFERRED rule to L1 status without explicit operator confirmation supplied via authoritative input.

## Temporal Change Binding

When an operation outcome is determined, URACE MUST produce a Change record conforming to the Change Schema above and store it atomically with the accepted operation. The binding MUST NOT be modified after storage. The binding MUST be stored regardless of whether the outcome is ACCEPTED, REJECTED, or ROLLED_BACK.

```
OPERATION OUTCOME
  → Change record (conforming to Change Schema)
      governed_by           = active rule IDs at time of outcome
      rule_snapshot_digest  = SHA-256 of active rule set
      state_before_digest   = product state digest before change
      state_after_digest    = product state digest after change (null if REJECTED)
      delta_to_rules        = rule IDs mutated by this operation (often empty)
  → stored atomically in change_bindings
```

This allows any future inspection to answer: *"what rules were active and governing when this change was made, what was the product state before and after, and did this operation itself change any rules?"*

If the Rule Ledger is unavailable at outcome time, URACE MUST surface this as a named integrity gap and MUST NOT silently record an outcome without its binding.

## Append-Only Invariant

The L0/L1/L2 immutability tiers, rule DAG, conflict detection, and change binding implement **AP35 — Governance Ledger** (§62i). The Rule Ledger MUST be append-only with supersession (AP3 — Append-Only Log, §62i). Rules MUST NOT be deleted from the Ledger. A rule that is no longer active MUST be marked deactivated or superseded with an attributed timestamp and reason, preserving the full historical chain. Any query against the Ledger MUST be able to reconstruct the complete active rule set at any prior accepted change by replaying the binding record.

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

**Executor configuration rules:** `Config.executor.providers` capacity limits MUST be seeded as POLICY rules in the Rule Ledger at bootstrap with scope `executor`. Absence of seeded executor POLICY rules at cycle start MUST emit `executor-policy-missing` WARNING IntegrityGap.

## User Interface

Three commands expose the Rule Ledger:

| Command | Effect |
|---------|--------|
| `urace <text>` | Free-form input — Executor classifies as any combination of goals, intents, and constraints; confirm each detected item |
| `urace /<command> [args]` | Direct command — routes to the named lifecycle operation without Executor classification |
| `urace /intent add "…"` | Add a DIRECTIVE rule (queued; applied at next safe boundary) |
| `urace /intent list` | List active DIRECTIVE rules |
| `urace /intent supersede "…" --id <id>` | Replace an existing DIRECTIVE with a new one |
| `urace /intent deactivate --id <id>` | Deactivate a DIRECTIVE rule |
| `urace /constraint add "…"` | Add a PROHIBITION rule |
| `urace /constraint add "…" --allow` | Add a PERMISSION rule |
| `urace /constraint deactivate --id <id>` | Deactivate a constraint rule |
| `urace /rules list` | List all active rules |
| `urace /rules inspect <id>` | Full rule record with derivation chain |
| `urace /rules graph` | Full rule graph with relationships |
| `urace /rules conflicts` | Surface detected rule conflicts |
| `urace /rules changes <id>` | List accepted changes governed by a rule |

`intent` and `constraint` mutations are queued inputs applied at the next safe lifecycle boundary under the same atomicity guarantees as §62. They MUST NOT be applied mid-cycle. For complete command-line syntax, shared options, and output contracts for all commands, see §62k Standard Command Options.

## Universal Input

```
urace <text>
urace /<command> [args]
```

The runtime accepts free-form text and direct commands through a single top-level dispatch. No subcommand keyword is needed.

**Routing rules (three tiers):**

**Tier 0 — Slash direct.** Input beginning with `/` followed by a known command routes directly to that command without Executor involvement. `urace /check`, `urace /rules list`, `urace /intent add "…"`. A `/`-prefixed token that does not match a known command is treated as free-form text with the `/` stripped.

**Tier 1 — Local exact match.** The full input (case-insensitive) is looked up in a canonical alias table covering known command names and common natural-language equivalents (`"stop"` → `pause`, `"status"` → `check`, `"rules list"`, etc.). On a match, the input routes directly without Executor involvement. This tier handles obvious single-intent inputs at zero cost.

**Tier 2 — Executor classification.** All remaining input — conversational, multi-intent, ambiguous, natural language, or any combination — is routed to the Executor as free text. The Executor returns a `ClassificationBatch` (§62b) whose items may have type `goal`, `intent`, `constraint`, `command`, or `response`. The runtime processes all items in order: `response` items are printed immediately; `command` items are executed immediately; `goal`, `intent`, and `constraint` items prompt for individual confirmation. When `logic` is `or`, items are presented as alternatives and the operator selects.

**Argparse recovery.** When a known command is followed by unrecognised non-flag arguments that argparse cannot process, the runtime re-routes the entire original input as free-form text to Tier 2. This handles inputs such as `urace auto help` or `urace update the revenue goal` where trailing tokens are intent, not argparse arguments.

**SD classification gate.** Before invoking the Executor, the runtime applies a conservative SD=True gate: if the entire free-form input exactly matches a canonical command name or alias (case-insensitive), it is routed directly as a known command without Executor overhead. Only exact matches qualify; partial or fuzzy matches are SD=False and proceed to executor classification. This gate MUST NOT use probabilistic or statistical heuristics.

**Free-form classification protocol.**
1. The operator provides free text describing one or more lifecycle items.
2. The Executor returns a `ClassificationBatch` (§62b) containing one `ClassificationResult` per detected item, in detection order. Items may have type `goal`, `intent`, `constraint`, `command`, or `response`.
3. The runtime displays all detected items numbered — type, subtype, extracted parameters, confidence, and reasoning.
4. For each item in sequence: `response` items are printed immediately; `command`-type items are executed directly without confirmation; `goal`, `intent`, and `constraint` items prompt for individual confirmation (y/n/skip). A `permission`-subtype constraint MUST display a visible warning before its confirmation prompt.
5. Each confirmed lifecycle item is written to the durable inbox as the appropriate kind (`goal`, `intent_control`, or `constraint_control`) and processed at the next safe lifecycle boundary.
6. Skipped or rejected items are not written; the operator is directed to the direct command for those items.

**Mixed input.** When free-form text contains both `/command` references and lifecycle-item descriptions, the Executor's ClassificationBatch MAY include `command`-type items alongside `goal`, `intent`, and `constraint` items. A `command`-type item's `parameters` MUST include a `command` field naming the lifecycle operation and an optional `args` list. The runtime executes command-type items in order, interleaved with the confirmation flow for lifecycle items.

**Executor unavailability.** When the Executor is unavailable or over budget, Universal Input MUST NOT attempt heuristic classification. It MUST inform the operator and direct them to the `/`-prefixed direct commands (`urace /add-goal`, `urace /intent add`, `urace /constraint add`).

**No flag override.** Free-form input accepts only the text argument. There is no type-selection flag; direct commands using `/` serve that purpose. There is no confirmation-skip flag; interactive confirmation is always required for lifecycle items.

**Permission warning.** When a ClassificationResult identifies a constraint with subtype `permission`, the runtime MUST display a visible warning before the confirmation prompt.

**Startup guidance.** At the start of `urace auto`, the runtime MUST display a single-line hint indicating that free-form text and `/`-prefixed direct commands are available from a second terminal.

**Machine-readable output.** When `json-feedback` is enabled (§62c), structured outputs from Universal Input processing — classification batch, per-item dispositions (confirmed, skipped, rejected, executed) — are also emitted as machine-readable JSON for pipeline integration.

---

# 62b. Citizen Schemas

**Section metadata.** kind: Schema-collection · tier: FOUNDATIONAL · contains: [GoalRecord, IntentRecord, ConstraintRecord, DecisionRecord, EvidenceRecord, OperationRecord, ExecutorRecord, CompactionEvent, ComplianceRecord, AssessmentRecord, MetricDefinition, StateDocument]

**Cross-reference note.** Several schemas in this section carry parenthetical citations of the form `(§62i APxx)`. These are forward cross-references to the Architectural Meta-Patterns defined in §62i. The AP0–AP37 formal definitions reside exclusively in §62i; the citations here are attributions that name the source section, not duplicate definitions. A reader may proceed through §62b without requiring §62i, treating each `(§62i APxx)` note as "see §62i for the full definition of this pattern."

All named citizens produced or consumed by a URACE lifecycle MUST conform to the schemas defined in this section. An implementation that omits a REQUIRED field or misrepresents its type violates this contract and MUST surface the violation as a named integrity gap on load. Fields marked OPTIONAL MAY be omitted when not applicable; an absent OPTIONAL field MUST be treated as its stated default.

The schemas in §62a (Rule, Change) and in this section together form the complete citizen contract set. Any bootstrap from `URACE.md` that produces these structures MUST be schema-conformant for the system to be considered reproducible.

**Canonical field clusters.** In addition to the primitive types below, §62l defines two shared field clusters used across citizen schemas: `GoverningRecord` (id, authority_basis, scope, established_at) and `EffectUncertaintyProtocol`. Citizens using these clusters MUST declare `Uses canonical: GoverningRecord` or `Uses canonical: EffectUncertaintyProtocol` in their schema definition. See §62l for the authoritative definitions.

**Data interchange contract.** URACE does not define a separate wire-format or data-exchange protocol for single-product use. Citizen schemas (§62b) plus canonical primitives (§62d) plus the AP3 Append-Only Evidence Log constitute the complete data interchange contract for all single-product deployments. If URACE-to-URACE federation (coordinating multiple URACE instances across products) is introduced in a future revision, an explicit ExchangeEnvelope citizen SHALL be added at that time. An implementation that introduces a custom wire format without a corresponding citizen schema definition MUST surface this as a conformance gap.

## TemporalFields

The TemporalFields vocabulary is the single authoritative definition of every timestamp and date-history primitive used across citizen schemas. It is a **composition vocabulary** — not a base type, not a class. No citizen inherits from it. Each citizen schema declares which subset of fields from this vocabulary it uses; fields not declared are not part of that citizen's contract.

```
TemporalFields {
  -- Creation and modification --
  created_at        timestamp          when the record was first written; immutable after creation
  updated_at        timestamp          last mutation of any mutable field; updated on every write
  deleted_at        timestamp | null   soft-delete marker; null = not deleted; set = logically deleted
                                       (record MUST be preserved; physical removal is prohibited)

  -- Activation window --
  active_since      timestamp          when the record became effective; MAY equal created_at
  active_until      timestamp | null   when deactivated or superseded; null = currently active
  expires_at        timestamp | null   time-based natural expiry; distinct from active_until
  superseded_at     timestamp | null   when a newer version of this record replaced it

  -- Lifecycle transitions --
  completed_at      timestamp | null   terminal successful completion
  rejected_at       timestamp | null   terminal rejection
  resolved_at       timestamp | null   when a condition, blocker, or open decision was resolved/closed
  archived_at       timestamp | null   when archived; preserved but no longer operationally active
  acknowledged_at   timestamp | null   explicit operator acknowledgement

  -- Audit and processing --
  established_at    timestamp          when formally established (anchors, policies, containers)
  recorded_at       timestamp          when durably persisted to an append-only audit store (AP3)
  queued_at         timestamp          when placed in a processing queue
  scheduled_at      timestamp          due time for a scheduled or triggered condition
  satisfied_at      timestamp | null   when a scheduled or conditional trigger was satisfied

  -- Operational accounting --
  last_verified_at  timestamp | null   last time integrity was actively verified
  last_failure_at   timestamp | null   most recent observed failure
  last_call_at      timestamp | null   most recent invocation or outbound call
  repaired_at       timestamp | null   when a repair or recovery operation completed
}
```

**Conventions.**
- `at` is a valid alias for `created_at` in append-only records (Evidence, Checkpoint, Input, Change). Append-only records MUST NOT expose `updated_at` — they cannot be modified.
- `first_at` + `last_at` together serve as `created_at` + `updated_at` for records that are deduplicated by identity (Blocker, SystemRepairEntry).
- A timestamp field absent or null means the event has not yet occurred. A REQUIRED timestamp MUST be set on creation. An OPTIONAL timestamp MAY be null until its triggering event.
- `deleted_at` and `active_until` have different semantics. `active_until` marks end of active window (may be set by supersession or system deactivation). `deleted_at` marks an explicit operator-initiated soft-delete. A superseded rule carries `active_until` but NOT `deleted_at`. A deactivated rule carries both.
- `completed_at` and `archived_at` are distinct. Completion is a terminal success state. Archival is an administrative action that may occur on records in any terminal state.

**Declaration syntax.** Each citizen schema that uses fields from this vocabulary adds a note: `Uses TemporalFields: [field, ...]`. Fields listed there MUST follow the semantics defined above.

## Base Citizen Clusters

Every citizen schema in §62b MUST declare `Extends:` one of the following base clusters. Conformance is verified on load; violations emit `citizen-base-violation` WARNING IntegrityGap.

**CitizenBase**
- `id` (string, REQUIRED) — stable identifier; MUST be immutable after creation (AP0)
- `created_at` (ISO-8601, REQUIRED) — creation timestamp; MUST be immutable after creation
- `updated_at` (ISO-8601, REQUIRED) — last mutation timestamp

**Used in:** (universal — all spec sections and all citizen schemas)

**AuthorizedCitizen** extends CitizenBase
- `authority_basis` (string, REQUIRED) — authorizing rule id or authority scope
- `scope` (string, OPTIONAL) — governance scope affected

**Used in:** (universal — all spec sections requiring authority attribution)

**TemporalCitizen** extends CitizenBase
- Declares exact TemporalFields subset via "Uses TemporalFields: [...]"
- All declared fields MUST appear in the TemporalFields vocabulary

**Used in:** (universal — all spec sections requiring temporal tracking)

Declaration syntax (in each citizen schema):
> Extends: CitizenBase | AuthorizedCitizen | TemporalCitizen

## Objective

Extends: AuthorizedCitizen

Used in: State.objectives, Plan.objective_id.

An Objective is a named, measurable unit of work that the lifecycle plans and executes toward. Every Objective MUST have an attributable authority basis and a machine-readable success measure.

```
Objective {
  id                            REQUIRED  stable identifier
  title                         REQUIRED  human-readable goal statement
  reason                        REQUIRED  justification; default "authoritative user goal" if absent from input
  success_measure               REQUIRED  observable, falsifiable criterion for completion
  scope                         REQUIRED  documentation | runtime | metrics | rebootstrap
  target                        REQUIRED  product | urace
  priority                      REQUIRED  integer 0–100; higher = more urgent
  status                        REQUIRED  planned | active | completed | cancelled | disabled
                                          | deferred | deferred_budget | needs_reassessment
                                          | awaiting_operator_decision | policy_blocked | blocked
  expected_value                REQUIRED  float 0.0–1.0; estimated net benefit if completed
  estimated_cost                REQUIRED  float 0.0–1.0; estimated resource fraction
  risk                          REQUIRED  float 0.0–1.0; probability of adverse outcome
  urgency                       REQUIRED  float 0.0–1.0; time-sensitivity
  necessity_evidence            REQUIRED  string; empty when not applicable
  lower_impact_route_sufficient REQUIRED  bool; true = a lower-impact path may satisfy the goal
  dependencies                  REQUIRED  list of Objective ids that must complete first
  pinned                        REQUIRED  bool; true = priority protected from autonomous demotion
  created_at                    REQUIRED  timestamp
  updated_at                    REQUIRED  timestamp; updated on every status transition or field mutation
  authority_basis               REQUIRED  string describing delegation basis
  deadline                      OPTIONAL  ISO-8601 timestamp | null
  not_before                    OPTIONAL  ISO-8601 timestamp | null
  estimate                      OPTIONAL  {min_hours: float, max_hours: float}
  estimate_confidence           OPTIONAL  low | medium | high
  priority_floor                OPTIONAL  integer | null; autonomous priority floor
  priority_ceiling              OPTIONAL  integer | null; autonomous priority ceiling
  source_input                  OPTIONAL  Input id when created from a queued input
  completed_at                  OPTIONAL  timestamp; set when status → completed
  cancelled_at                  OPTIONAL  timestamp; set when status → cancelled
  deleted_at                    OPTIONAL  timestamp | null; soft-delete marker; null = not deleted
  tombstone                     OPTIONAL  bool; true = logically deleted, preserved for history
  update_candidate              OPTIONAL  dict; present when scope = rebootstrap
}
```

Uses TemporalFields: created_at, updated_at, completed_at, cancelled_at, deleted_at. Uses canonical: Identifier (id), ProductScope (scope), UnitFloat (expected_value, estimated_cost, risk, urgency).
```

**Identifier immutability contract (AP0 — Citizen, §62i).** An Objective's `id` MUST NOT change after creation and MUST NOT be reused after the Objective is completed, cancelled, or deleted.

**Status transition contract.** `planned → active` requires authority resolution to pass. `active → completed` requires an ACCEPTED Operation and successful validation. `active → needs_reassessment` is triggered by evidence that the success measure can no longer be evaluated. Status MUST NOT regress from `completed` or `cancelled`.

**Priority contract.** If `priority_floor` and `priority_ceiling` are both set, `priority_floor` MUST be ≤ `priority_ceiling`. Autonomous priority adjustment MUST NOT move `priority` below `priority_floor` or above `priority_ceiling`.

## Plan

A Plan is the execution strategy produced for an active Objective. One Plan exists per Objective at a time; completing or replacing a Plan MUST be recorded.

```
Plan {
  id                      REQUIRED  stable identifier
  objective_reference     REQUIRED  Objective id this plan serves
  steps                   REQUIRED  ordered list of execution step descriptions
  validation_strategy     REQUIRED  human-readable description of the validation approach
  next_review_condition   REQUIRED  condition that triggers plan reassessment
  status                  REQUIRED  ready | completed
  created_at              REQUIRED  timestamp
  updated_at              REQUIRED  timestamp; updated on status transition or step revision
  completed_at            OPTIONAL  timestamp | null; set when status → completed
}
```

Uses TemporalFields: created_at, updated_at, completed_at.
Used in: State.plans, Operation.plan_id.

**Plan–Objective binding contract.** A Plan MUST reference exactly one active Objective. An Objective MUST NOT have more than one Plan in `ready` status simultaneously. A completed Plan MUST be retained in history.

## Operation

Extends: AuthorizedCitizen

An Operation is a single attempt to mutate the Product or runtime under a Plan. It is the atomic unit of change.

```
Operation {
  id                       REQUIRED  stable identifier
  objective_reference      REQUIRED  Objective id
  plan_reference           REQUIRED  Plan id
  scope                    REQUIRED  documentation | runtime | metrics | rebootstrap
  status                   REQUIRED  ATTEMPTED | ACCEPTED | OBSERVED_NO_EFFECT
                                     | DEFERRED_PROVIDER_CAPACITY | AWAITING_OPERATOR_DECISION
                                     | CONCURRENT_CHANGE | REJECTED_ROLLED_BACK
                                     | REJECTED_INDEPENDENT_VALIDATION
  attempted_at             REQUIRED  timestamp; when execution was initiated (serves as created_at)
  updated_at               REQUIRED  timestamp; updated on every status transition
  authority_basis          REQUIRED  string
  executor                 REQUIRED  {executor_id: string, adapter: string, ...}
  before_metrics           REQUIRED  dict[name → float]; product metrics before mutation
  after_metrics            REQUIRED  dict[name → float]; product metrics after mutation
  observed_metric_effect   REQUIRED  {improved: int, regressed: int}
  independent_validation   REQUIRED  {verdict: ACCEPTED|REJECTED, passes: [...], fails: [...]}
  changed_files            REQUIRED  list of relative file paths affected
  transaction              REQUIRED  Transaction id (set on ACCEPTED)
  accepted_at              OPTIONAL  timestamp | null; set when status → ACCEPTED
  rejected_at              OPTIONAL  timestamp | null; set when status → REJECTED_ROLLED_BACK
                                     or REJECTED_INDEPENDENT_VALIDATION
  rolled_back_at           OPTIONAL  timestamp | null; set when transaction was rolled back;
                                     always equal to rejected_at when rollback caused rejection
  decision                 OPTIONAL  Objective title at time of operation
  decision_basis           OPTIONAL  Objective reason at time of operation
  executor_source_summary  OPTIONAL  string ≤ 4000 chars; Executor-provided change description
  explanation              OPTIONAL  string; human-readable explanation of what changed and why
  conflicting_files        OPTIONAL  list; set when status = CONCURRENT_CHANGE
  validation_evidence_id   OPTIONAL  string; id of the Evidence record produced by independent validation; REQUIRED when lifecycle_state transitions to ACCEPTED
  validation_skipped_reason OPTIONAL string; if validation was skipped, MUST contain justification
  effect_type              REQUIRED  EffectType; IDEMPOTENT | QUERY | STATEFUL | ASYNC;
                                     governs reconciliation strategy under §52
}
```

Uses TemporalFields: attempted_at (as created_at), updated_at, accepted_at, rejected_at, rolled_back_at. Uses canonical: Identifier (id), ProductScope (scope), ExecutorAttribution (executor post-dispatch), ValidationResult (independent_validation), MetricEffect (observed_metric_effect), MetricSnapshot (before_metrics, after_metrics).
Used in: State.operations, Plan.operations.

**EffectType enum.**

```
EffectType enum: IDEMPOTENT | QUERY | STATEFUL | ASYNC
- IDEMPOTENT — re-applying produces identical state
- QUERY      — read-only, no side effects
- STATEFUL   — mutates external state; re-application may differ
- ASYNC      — submitted but completion not synchronously confirmed
```

`effect_type` governs the reconciliation strategy applied by the Transaction Recovery Protocol (§52, AP27): IDEMPOTENT operations MAY be replayed without guard; STATEFUL and ASYNC operations MUST be reconciled via UnresolvedEffect before the lifecycle MAY converge.

**Validation evidence contract.** An Operation MUST have either `validation_evidence_id` or `validation_skipped_reason` populated before `lifecycle_state` transitions to ACCEPTED. Absence of both MUST emit `validation-evidence-missing` WARNING IntegrityGap.

**Status finality contract.** `ACCEPTED`, `REJECTED_ROLLED_BACK`, and `REJECTED_INDEPENDENT_VALIDATION` are terminal. An Operation in a terminal status MUST NOT be retried; a new Operation MUST be created for any retry attempt.

**Metrics contract.** `before_metrics` MUST be captured immediately before the Executor call. `after_metrics` MUST be captured immediately after the Transaction is validated. Both MUST use the same metric names and measurement method.

## Evidence

Extends: CitizenBase

Evidence is the append-only audit log (AP3 — Append-Only Log, §62i) of every significant lifecycle event, serving as the concrete instantiation of the Broadcast Log (AP15 — Broadcast Log, §62i). It is the primary traceability surface.

```
Evidence (base) {
  id    REQUIRED  stable identifier
  at    REQUIRED  timestamp
  kind  REQUIRED  string; identifies the evidence sub-type (see kinds below)
  -- kind-specific fields follow --
}
```

Evidence MUST be append-only. An Evidence record MUST NOT be modified or deleted after creation. The following kinds MUST be supported; implementations MAY define additional kinds for events not listed here.

| Kind | Required additional fields |
|------|---------------------------|
| `authoritative-input-consumed` | `input`: Input id, `input_kind`: string |
| `authoritative-input-rejected` | `input`: Input id, `reason`: string |
| `rule-added` | `rule_id`: string, `rule_kind`: string, `source_input`: Input id |
| `rule-superseded` | `old_rule_id`: string, `new_rule_id`: string, `source_input`: Input id |
| `rule-deactivated` | `rule_id`: string, `source_input`: Input id |
| `transaction-recovery` | `transaction`: Transaction id, `disposition`: string |
| `self-evolution-policy-decision` | `outcome`: string, `mode`: string, `scope`: string, `reason`: string |
| `self-evolution-necessity-justification` | `necessity`: string, `policy_mode`: string, `disposition`: string |
| `executor-capacity-deferred` | `reason`: string, `capacity_observation_signature`: string |
| `executor-availability` | `available`: bool, `provenance`: string |
| `concurrent-product-change` | `operation`: Operation id, `files`: list, `disposition`: string |
| `update-customization-conflict` | `operation`: string, `candidate`: string, `explanation`: string |
| `value-deceleration-self-correction` | `trigger`: string, `direction`: string, `value_amplification`: float, `yield_rate`: float |
| `lifecycle-paused` | `prior_state`: string, `disposition`: string |
| `lifecycle-resumed` | `disposition`: string |
| `authority-resolution-denied` | `reason`: string |
| `live-control-boundary` | `applied_inputs`: int, `outcome`: string |
| `destination-anchor-changed` | `prior_digest`: string, `new_digest`: string, `drift_detected`: bool |
| `external-metric-observation` | `source_id`: string, `metric_name`: string, `value`: float |
| `authority-resolution-escalated` | `reason`: string, `requires_decision`: string |
| `force-discovery-override` | `force_id`: string, `attribution`: string |
| `external-metric-unavailable` | `source_id`: string, `streak`: int, `reason`: string |
| `metric-definition-replaced` | `metric_name`: string, `prior_id`: string, `new_id`: string, `authorized_by`: string |

Uses canonical: Identifier (id), iso_timestamp (at as created_at). Note: Evidence is append-only per AP3; MUST NOT expose updated_at or any mutable timestamp field.
Used in: State.evidence (append-only log).

**Append-only contract.** A new Evidence record MUST be created for every event; prior records MUST NOT be edited. An implementation that truncates or compacts the Evidence log MUST preserve at minimum the most recent 1 000 records and MUST NOT discard records for events within the current Objective's lifecycle.

## Checkpoint

A Checkpoint is a durable integrity marker that binds a product state digest to a lifecycle moment.

```
Checkpoint {
  id           REQUIRED  stable identifier
  at           REQUIRED  timestamp
  kind         REQUIRED  bootstrap | accepted-product-change | assessment
  digest       REQUIRED  DigestValue; SHA-256 of the product file tree (see §62c Digest Computation)
  operation    OPTIONAL  Operation id; REQUIRED when kind = accepted-product-change
  transaction  OPTIONAL  Transaction id; REQUIRED when kind = accepted-product-change
}
```

Uses canonical: Identifier (id), DigestValue (digest), TemporalFields (at as created_at).
Used in: State.checkpoints (append-only log).

**Sequential integrity contract.** The `digest` of a `accepted-product-change` Checkpoint MUST equal the `state_after_digest` of the corresponding Change binding in the Rule Ledger. A divergence MUST be surfaced as a named integrity gap.

**Bootstrap checkpoint contract.** A `bootstrap` Checkpoint MUST be the first record in the checkpoint list. Its digest MUST reflect the product state at the moment `init` completed.

## Input

An Input is an operator instruction queued durably in the atomic inbox for application at the next safe lifecycle boundary.

```
Input {
  id       REQUIRED  stable collision-resistant identifier
  at       REQUIRED  timestamp of enqueueing
  kind     REQUIRED  context | goal | source | metric | vital
                     | source_control | metric_control | vital_control | goal_control
                     | executor_control | policy_control | budget_control
                     | evaluation_control | intent_control | constraint_control
                     | add-classify
  payload  REQUIRED  dict; structure is kind-specific
  status   REQUIRED  QUEUED (only valid value at rest; consumed inputs are removed)
}
```

Uses canonical: Identifier (id), iso_timestamp (at as created_at). Note: Input is append-only at rest; MUST NOT expose updated_at.
Used in: State.inbox, InputQueue.

**Idempotency contract.** An Input id that appears in `processed_input_ids` MUST NOT be applied a second time. This list MUST be checked before processing any Input.

**Ordering contract.** Inputs MUST be applied in the order they were enqueued (oldest first by `at`). No Input MUST be reordered relative to another Input of any kind. `order ≡ sorted(inputs, key=λi: parse_ts(i.at))`

**Removal contract.** An Input file MUST be removed from the inbox atomically with the state write that records its application. An Input that is removed without a corresponding state write MUST be treated as a recovery condition.

**Input kind notes.**

| Kind | Notes |
|---|---|
| `add-classify` | Free-text input awaiting executor classification; transient — replaced by classified kind on confirmation |

## Executor Provider Record

Extends: AuthorizedCitizen
Implements: GoverningRecord

An Executor Provider Record describes a registered Executor and its operational limits.

```
ExecutorProvider {
  id                       REQUIRED  stable identifier; implementation-defined (default is implementation-specific)
  enabled                  REQUIRED  bool
  capabilities             REQUIRED  list of: discovery | planning | mutation | evaluation | execution
  max_calls_per_24h        REQUIRED  int ≥ 1
  max_calls_per_30d        REQUIRED  int ≥ max_calls_per_24h
  capacity_retry_mode      REQUIRED  automatic | dynamic | fixed
  capacity_retry_delay_ms  REQUIRED  int ≥ 0
  capacity_fallback_seconds REQUIRED int ≥ 60
  registered_at            REQUIRED  timestamp; when this provider was first registered
  adapter                  OPTIONAL  string; adapter implementation identifier; format is implementation-defined
  command                  OPTIONAL  string | null; override executable path
  capability_priorities    OPTIONAL  dict[capability → int]; routing weight per capability
  priority                 OPTIONAL  int; global routing priority among registered providers
  last_call_at             OPTIONAL  timestamp | null; most recent dispatched call
  last_failure_at          OPTIONAL  timestamp | null; most recent call failure
}
```

Uses TemporalFields: registered_at (as created_at), last_call_at, last_failure_at.
Used in: Config.executor_providers.

**Budget contract.** The lifecycle MUST NOT dispatch a call to a provider whose rolling 24h or 30d call count has reached its configured ceiling. A provider at ceiling MUST be treated as capacity-exhausted, not detached.

## Decision

Extends: AuthorizedCitizen

> **Deprecated.** This is a minimal summary schema retained for historical reference. The authoritative canonical schema is `DecisionRecord` (§62d), which includes full attribution, reasoning steps, evidence refs, and AP23 justification chain support. New implementations MUST use `DecisionRecord`.

```
Decision {
  id              REQUIRED  stable identifier
  at              REQUIRED  timestamp
  kind            REQUIRED  plan | operator
  outcome         REQUIRED  string; the chosen course of action (e.g. Plan id)
  authority_basis REQUIRED  string describing the delegation basis for this decision
  justification   REQUIRED  string; reasoning that led to this outcome
}
```
Used in: State.decision_records (append-only log).

## Trigger

A Trigger is an event record that signals a condition change requiring lifecycle reassessment.

```
Trigger {
  id          REQUIRED  stable identifier
  at          REQUIRED  timestamp
  kind        REQUIRED  EXECUTOR_AVAILABLE | EXECUTOR_UNAVAILABLE
                        | EXTERNAL_REPOSITORY_UPDATE | LIFECYCLE_EVENT | SCHEDULED_WAKE
  source      REQUIRED  string; origin of the trigger signal
  provenance  REQUIRED  string; how the signal was detected
  disposition REQUIRED  string; required lifecycle response (e.g. REASSESS)
}
```
Used in: State.triggers, Plan.trigger_conditions.

## Blocker

A Blocker is a named limitation that prevents the lifecycle from advancing in a specific scope. Blockers MUST be surfaced in `urace check` output.

```
Blocker {
  id          REQUIRED  stable identifier; used for explicit resolution references
  at          REQUIRED  timestamp when this blocker was first recorded (serves as created_at)
  last_at     REQUIRED  timestamp of most recent recurrence (serves as updated_at)
  scope       REQUIRED  string; which lifecycle scope is blocked
  reason      REQUIRED  string; human-readable description of the blocking condition
  count       REQUIRED  int ≥ 1; number of times this blocker has been recorded
  resolved_at OPTIONAL  timestamp | null; set when blocker is cleared; null = still active
  classification   OPTIONAL  enum: TRANSIENT | PERSISTENT | ESCALATION | OPERATOR_GATE; default PERSISTENT
  evidence_id      OPTIONAL  string; id of the Evidence record that triggered this blocker
  auto_clear_on    OPTIONAL  string; human-readable description of condition that auto-clears this blocker
  escalation_due   OPTIONAL  string; ISO-8601; when this blocker must escalate to operator attention
}
```

Uses TemporalFields: at (as created_at), last_at (as updated_at), resolved_at.
Used in: State.blocking_gaps.

**Deduplication contract.** A Blocker with the same `scope` MUST be updated (incrementing `count` and `last_at`) rather than appended as a new record. A resolved Blocker MUST be removed from the active blockers list; it MUST NOT accumulate indefinitely.

**Classification contract.** A blocker with `classification: TRANSIENT` that has not recurred within 600 seconds SHOULD be resolved by the runtime without operator action; set `resolved_at` and emit Evidence of kind `blocker-transient-expired`. A blocker with `count ≥ 5` AND `(last_at − at) > 3600` seconds MUST auto-upgrade to `classification: ESCALATION`; emit IntegrityGap(`kind: "blocker-escalated"`, severity=WARNING) with `blocker_id`. A blocker with `classification: OPERATOR_GATE` MUST NOT be auto-resolved; it follows the OperatorGateProtocol (§62l).

## Value Trajectory

The Value Trajectory tracks whether the lifecycle is producing value at an accelerating, stable, or decelerating rate. It is the primary signal for autonomous self-correction.

```
ValueTrajectory {
  checkpoints      REQUIRED  list of VelocityCheckpoint (max 100, rolling window)
  acceleration     REQUIRED  AccelerationReport | null; null until 2+ checkpoints exist
  established_at   REQUIRED  timestamp when trajectory tracking began
  cumulative_value REQUIRED  float; sum of positive net_value_delta across all checkpoints
  peak_velocity    REQUIRED  float; highest current_velocity observed
  updated_at       OPTIONAL  timestamp of last checkpoint addition
}

VelocityCheckpoint {
  operation_id       REQUIRED  Operation id
  at                 REQUIRED  timestamp
  elapsed_seconds    REQUIRED  float; wall-clock time from operation start to acceptance
  net_value_delta    REQUIRED  float; improved_metrics minus regressed_metrics
  improved_metrics   REQUIRED  int; count of metric dimensions that improved
  regressed_metrics  REQUIRED  int; count of metric dimensions that regressed
  value_rate         REQUIRED  float; net_value_delta / (elapsed_seconds / 60); value per minute
  scope              REQUIRED  string; Operation scope
  objective_title    OPTIONAL  string
}

AccelerationReport {
  status              REQUIRED  computed | no_data | establishing_baseline
  direction           OPTIONAL  accelerating | stable | decelerating; present when status=computed
  current_velocity    OPTIONAL  float; mean value_rate over recent window (last 5)
  baseline_velocity   OPTIONAL  float; mean value_rate over baseline window (first 5)
  trend_slope         OPTIONAL  float; second-half mean minus first-half mean
  value_amplification OPTIONAL  float | "unbounded"; current_velocity / baseline_velocity
  yield_rate          OPTIONAL  float 0.0–1.0; fraction of operations with net_value_delta > 0
  sample_size         OPTIONAL  int; number of checkpoints used
  scope_velocity      OPTIONAL  dict[scope → float]; per-scope mean value_rate
  alerts              OPTIONAL  list of string; active threshold violations
  cumulative_value    OPTIONAL  float; positive-only cumulative value from checkpoints
  checkpoints_needed  OPTIONAL  int; present when status ≠ computed
}
```

**Window contract.** `current_velocity` MUST use the most recent 5 checkpoints. `baseline_velocity` MUST use the first 5 checkpoints in the window. Both windows MUST be computed from the same rolling list of at most 100 checkpoints.

## Connector Source

A Connector Source is a registered external data provider from which metrics are observed.

```
ConnectorSource {
  id             REQUIRED  stable identifier
  kind           REQUIRED  json_file | http_json | github_repository
  status         REQUIRED  CONFIGURED | AVAILABLE | AUTHENTICATED | AUTHORIZED | OBSERVED
                           | DISABLED | REMOVED | ADAPTER_REQUIRED
  status_history REQUIRED  list of {status: string, at: timestamp}; append-only
  created_at     REQUIRED  timestamp; when source was first registered
  updated_at     REQUIRED  timestamp; updated on every status mutation
  deleted_at     OPTIONAL  timestamp | null; set when status → REMOVED; null = not removed
  location       OPTIONAL  URL or file path; REQUIRED when kind ≠ github_repository
  repository     OPTIONAL  repository identifier; REQUIRED when kind = github_repository
  visibility     OPTIONAL  public | private
  credential_env OPTIONAL  string; env var name holding credentials
  values         OPTIONAL  dict[metric_name → json_path]; metric path registrations
}
```

Uses TemporalFields: created_at, updated_at, deleted_at. Uses canonical: Identifier (id), StatusTransition (status_history entries).
Used in: Config.connectors.

**Status progression contract.** Status MUST progress forward through the defined states. A source MUST NOT transition directly from `CONFIGURED` to `OBSERVED` without passing through `AVAILABLE`, `AUTHENTICATED`, and `AUTHORIZED`. Each status transition MUST be appended to `status_history`.

## Metric Definition

**Construct metadata.** kind: Schema · tier: FOUNDATIONAL · standalone: true

Extends: CitizenBase

A Metric Definition maps a named metric to a path within a Connector Source.

```
MetricDefinition {
  id                  REQUIRED  stable identifier (Input id of the registering input)
  name                REQUIRED  unique metric name within this lifecycle
  source              REQUIRED  ConnectorSource id
  path                REQUIRED  JSON path expression resolving to a numeric value
  direction           REQUIRED  nondecreasing | nonincreasing
  created_at          REQUIRED  timestamp; when this definition was registered
  updated_at          REQUIRED  timestamp; updated when definition is replaced or modified
  mutation_requires   REQUIRED  enum: IMMUTABLE | PERMISSION | OBJECTIVE; default PERMISSION if authority omitted, IMMUTABLE if authority="DIRECTIVE"
  authority           OPTIONAL  string; "DIRECTIVE" when seeded as an immutable baseline at bootstrap
  authority_level     OPTIONAL  enum: L0 | L1 | L2; governance tier; L0=never mutable, L1=DIRECTIVE-immutable, L2=policy-gated mutation
  baseline            OPTIONAL  number or string; immutable baseline value when authority = "DIRECTIVE"
  unit                OPTIONAL  string; measurement unit
  seeded_at           OPTIONAL  ISO-8601; bootstrap timestamp when authority = "DIRECTIVE"
  target              OPTIONAL  float; desired threshold value
  deprecated_at       OPTIONAL  timestamp | null; set when this metric is retired; null = active
  last_baseline_audit OPTIONAL  ISO-8601; timestamp when baseline was last verified against Rule Ledger snapshot
}
```

Uses TemporalFields: created_at, updated_at, deprecated_at (as archived_at).
Used in: Config.metric_definitions, State.metric_definitions.

**Uniqueness contract.** Metric names MUST be unique within the lifecycle. Registering a metric with a name that already exists MUST replace the prior definition and append a record to the Evidence log.

**DIRECTIVE seeding contract.** A MetricDefinition with `authority: "DIRECTIVE"` is seeded as an immutable baseline in the Rule Ledger at bootstrap. Its `baseline` and `seeded_at` fields MUST be set at creation and MUST NOT be modified after seeding. A replacement or mutation of a DIRECTIVE MetricDefinition without explicit authority authorization MUST emit a `metric-definition-drift` WARNING IntegrityGap (§62l).

**Mutation contract.** A MetricDefinition with `mutation_requires: IMMUTABLE` MUST NOT be modified after `seeded_at`. Any modification attempt MUST emit an `metric-baseline-unauthorized-mutation` BLOCKING IntegrityGap and enter BLOCKED state. A MetricDefinition with `mutation_requires: PERMISSION` requires an active PERMISSION rule in the Rule Ledger. Absence of such a rule MUST emit `metric-mutation-policy-missing` WARNING IntegrityGap.

**Used in:** §62c staleness detection (metrics domain scan), §62l IntegrityGapCatalog (`metric-definition-drift`, `metric-baseline-unauthorized-mutation`, `metric-mutation-policy-missing`)

## MetricEffect (citizen schema)

**Construct metadata.** kind: Schema · tier: COMPOSITIONAL · standalone: false
Extends: CitizenBase

Formally distinguishes metric improvement (value trend) from metric drift (definition mutation). Produced by the T2 Bar-Raising Calculus and Staleness Detection for each metric observation.

Fields:
- `id` (string, REQUIRED) — stable identifier; prefix "meffect-"
- `created_at` (ISO-8601, REQUIRED) — observation timestamp
- `updated_at` (ISO-8601, REQUIRED) — last update
- `metric_id` (string, REQUIRED) — references MetricDefinition.id
- `kind` (enum, REQUIRED) — IMPROVEMENT | DRIFT | REGRESSION | NEUTRAL
  - IMPROVEMENT: value moved in favorable direction per MetricDefinition.direction
  - DRIFT: MetricDefinition was mutated (authorized or unauthorized)
  - REGRESSION: value moved in unfavorable direction per MetricDefinition.direction
  - NEUTRAL: no change
- `before_value` (any, OPTIONAL) — metric value before observation
- `after_value` (any, OPTIONAL) — metric value after observation
- `before_baseline` (any, OPTIONAL) — MetricDefinition.baseline before mutation (DRIFT only)
- `after_baseline` (any, OPTIONAL) — MetricDefinition.baseline after mutation (DRIFT only)
- `authorized_by` (string, OPTIONAL) — authorization basis for DRIFT; absent = unauthorized
- `operation_id` (string, OPTIONAL) — Operation that produced this effect
- `at` (ISO-8601, REQUIRED) — when the effect was observed

**Invariant.** A MetricEffect with kind=DRIFT and authorized_by absent MUST co-occur with a `metric-definition-drift` IntegrityGap.

**Used in:** §62h T2 Bar-Raising Calculus (IMPROVEMENT effects trigger threshold advance), §62c Metric Baseline Verification (DRIFT effects trigger authorization audit)

## CommunityFeed (citizen schema)

**Construct metadata.** kind: Schema · tier: INTEGRATED · standalone: false
Extends: CitizenBase

A configured community feed source. Each feed specifies its adapter kind, endpoint, and terms acceptance state. URACE MUST NOT ingest signals from a CommunityFeed whose `terms_accepted` is false.

```
CommunityFeed {
  id               REQUIRED  Identifier; prefix "cfeed-"
  created_at       REQUIRED  ISO-8601 timestamp
  updated_at       REQUIRED  ISO-8601 timestamp
  kind             REQUIRED  FeedAdapterKind; adapter type (RSS | WEBHOOK | POLLING | PUSH)
  endpoint         REQUIRED  string; adapter-specific endpoint (URL, topic, channel id, etc.)
  adapter_config   OPTIONAL  dict[string → string]; adapter-specific key-value configuration
  terms_accepted   REQUIRED  bool; operator MUST set to true after accepting terms; default false
  terms_version    OPTIONAL  string; version of the T&C accepted; null if not yet accepted
  terms_accepted_at OPTIONAL ISO-8601 timestamp; when terms were accepted; null if not yet accepted
  label            OPTIONAL  string; human-readable name for this feed
  active           REQUIRED  bool; whether this feed is currently enabled; default true
  adapter_timeout_seconds OPTIONAL  integer; seconds before a feed adapter connection or read times out;
                                    default 30; MUST be ≥ 1
  adapter_retry_count     OPTIONAL  integer; number of retry attempts before surfacing
                                    `community-feed-adapter-unavailable` gap; default 3; MUST be ≥ 0
  polling_interval_seconds OPTIONAL integer; seconds between poll cycles for RSS and POLLING adapters;
                                     WEBHOOK and PUSH adapters MUST ignore this field; default 300; MUST be ≥ 60
}
```

Uses TemporalFields: created_at, updated_at, terms_accepted_at.
Used in: Config.community_inbox.feeds, State.community_feeds.

**FeedAdapterKind enum.**
```
RSS      — polling-based RSS/Atom feed
WEBHOOK  — inbound HTTP webhook; URACE exposes a receiver endpoint
POLLING  — generic HTTP polling (non-RSS); returns JSON or text
PUSH     — operator-push via urace inbox; manual signal injection
```

## CommunitySignal (citizen schema)

**Construct metadata.** kind: Schema · tier: INTEGRATED · standalone: false
Extends: CitizenBase

A raw signal ingested from a CommunityFeed, scored on relevance and confidence before entering the proposal pipeline. A CommunitySignal is immutable after creation; scoring fields MUST be set at creation time.

```
CommunitySignal {
  id               REQUIRED  Identifier; prefix "csig-"
  created_at       REQUIRED  ISO-8601 timestamp
  updated_at       REQUIRED  ISO-8601 timestamp
  feed_id          REQUIRED  CommunityFeed.id; source feed
  content          REQUIRED  string; raw signal text or structured content
  source_ref       OPTIONAL  string; original URL, message id, or thread ref in source system
  received_at      REQUIRED  ISO-8601 timestamp; when the signal was ingested
  relevance_score  REQUIRED  float [0.0, 1.0]; semantic overlap with current URACE scope/Intent
  confidence_score REQUIRED  float [0.0, 1.0]; evidence of actionable community consensus
  signal_quality   REQUIRED  SignalQuality; computed from relevance_score and confidence_score
  filtered         REQUIRED  bool; true if signal was discarded without producing a PatchProposal
  filter_reason    OPTIONAL  string; human-readable reason for filtering; present only when filtered=true
}
```

Uses TemporalFields: created_at, updated_at, received_at.
Used in: State.community_signals.

**SignalQuality enum.**
```
HIGH      — relevance_score ≥ 0.75 AND confidence_score ≥ 0.75
MEDIUM    — relevance_score ≥ 0.40 AND confidence_score ≥ 0.60 (not HIGH)
LOW       — relevance_score ≥ 0.40 but confidence_score < 0.60
FILTERED  — relevance_score < relevance_floor; signal discarded
```

## PatchProposal (citizen schema)

**Construct metadata.** kind: Schema · tier: INTEGRATED · standalone: false
Extends: CitizenBase

A bounded patch candidate derived from a filtered CommunitySignal. PatchProposals advance through an approval pipeline governed by `Config.community_inbox.approval_mode`. A PatchProposal MUST NOT be applied to the Product without reaching status APPROVED.

```
PatchProposal {
  id               REQUIRED  Identifier; prefix "pprop-"
  created_at       REQUIRED  ISO-8601 timestamp
  updated_at       REQUIRED  ISO-8601 timestamp
  signal_id        REQUIRED  CommunitySignal.id; source signal
  proposed_diff    REQUIRED  string; patch content in any diff format (plain text, unified diff, etc.)
  target           REQUIRED  string; what the patch targets — "URACE" or the Product name
  rationale        REQUIRED  string; Executor-generated rationale for this proposal
  status           REQUIRED  ProposalStatus; PENDING | AUTO_APPROVED | APPROVED | REJECTED | EXPIRED | CONFIDENCE_INSUFFICIENT
  approval_mode    REQUIRED  ApprovalMode; mode in effect when this proposal was created
  confidence_score REQUIRED  float [0.0, 1.0]; confidence_score from the source CommunitySignal
  resolved_at      OPTIONAL  ISO-8601 timestamp; when status transitioned from PENDING; null if still PENDING
  resolved_by      OPTIONAL  string; operator input id or "auto" for AUTO mode approvals
  rejection_reason OPTIONAL  string; human-readable reason for REJECTED status
}
```

Uses TemporalFields: created_at, updated_at, resolved_at.
Used in: State.patch_proposals.

**ProposalStatus enum.**
```
PENDING                  — awaiting approval pipeline evaluation
AUTO_APPROVED            — approved autonomously under AUTO mode (confidence_score ≥ 0.80)
CONFIDENCE_INSUFFICIENT  — signal passed relevance_floor but confidence_score < confidence_threshold; queued for re-evaluation
APPROVED                 — operator-confirmed approval
REJECTED                 — operator-rejected or autonomously rejected under SMART mode
EXPIRED                  — not resolved within proposal_expiry_hours
```

**ApprovalMode enum.**
```
AUTO   — URACE may approve proposals with confidence_score ≥ 0.80 without operator confirmation;
         proposals with confidence_score < 0.80 fall through to SMART evaluation
SMART  — URACE pre-scores and surfaces top candidates with rationale; operator confirmation required
         only when URACE cannot autonomously determine sufficient confidence; low-quality proposals
         are autonomously rejected without operator burden (default mode)
HUMAN  — every proposal requires explicit operator approval regardless of confidence_score;
         URACE MUST NOT auto-approve in this mode
```

## FeatureBundle (citizen schema)

**Construct metadata.** kind: Schema · tier: COMPOSITIONAL · standalone: false
Extends: CitizenBase

A named, stable, versioned set of construct IDs representing a cohesive multi-construct feature. FeatureBundles are the canonical unit of feature-level granularity for `urace derive` and `urace update --opt-in-constructs`. A FeatureBundle MUST NOT contain a circular construct dependency: the transitive `requires`/`depends`/`governed-by` graph of all listed construct IDs MUST be acyclic. A FeatureBundle MUST NOT list its own ID.

```
FeatureBundle {
  id               REQUIRED  Identifier; prefix "fbundle-"
  created_at       REQUIRED  ISO-8601 timestamp
  updated_at       REQUIRED  ISO-8601 timestamp
  name             REQUIRED  string; canonical bundle name (e.g. "community-inbox"); MUST be unique
  construct_ids    REQUIRED  list[string]; ordered list of construct IDs included in this bundle
  description      OPTIONAL  string; human-readable summary of what the bundle provides
  spec_version     REQUIRED  string; spec version at which this bundle was defined
  source           REQUIRED  string; "spec" for spec-defined bundles; "operator" for user-defined bundles
}
```

Uses TemporalFields: created_at, updated_at.
Used in: State.feature_bundle_refs (via FeatureBundleRef), `urace derive --bundle`, `urace update --opt-in-constructs --bundle`.

## FeatureBundleRef (citizen schema)

**Construct metadata.** kind: Schema · tier: COMPOSITIONAL · standalone: false
Extends: CitizenBase

A lightweight reference to a saved FeatureBundle stored in durable state. Enables stale-detection and refresh across spec updates.

```
FeatureBundleRef {
  id               REQUIRED  Identifier; prefix "fbref-"
  created_at       REQUIRED  ISO-8601 timestamp
  updated_at       REQUIRED  ISO-8601 timestamp
  bundle_name      REQUIRED  string; the FeatureBundle.name this ref points to
  construct_ids    REQUIRED  list[string]; snapshot of construct IDs at save time
  spec_version     REQUIRED  string; spec version at save time
  saved_at         REQUIRED  ISO-8601 timestamp
}
```

Uses TemporalFields: created_at, updated_at, saved_at.
Used in: State.feature_bundle_refs.

## AssessmentGap

**Construct metadata.** kind: Schema · tier: FOUNDATIONAL · standalone: true

Extends: CitizenBase

An AssessmentGap records a specific insufficiency discovered during a lifecycle assessment cycle that prevents confident evaluation of an Authority, Intent, State, or Evidence dimension.

```
AssessmentGap {
  id            REQUIRED  Identifier; prefix "agap-"
  at            REQUIRED  string; ISO-8601; when gap was first recorded
  last_at       REQUIRED  string; ISO-8601; most recent recurrence
  cycle_id      REQUIRED  string; AssessmentRecord id this gap belongs to
  dimension     REQUIRED  enum: AUTHORITY | INTENT | STATE | EVIDENCE | CONSTRAINT | CAPACITY
  reason        REQUIRED  string; why this dimension is insufficient
  minimum_met   REQUIRED  string; what would satisfy this gap
  blocking      REQUIRED  bool; whether this gap prevents lifecycle advancement
  resolved_at   OPTIONAL  string; ISO-8601 | null; when gap was resolved
}
```

Uses TemporalFields: at (as created_at), last_at (as updated_at), resolved_at.
Used in: State.assessment_gaps (OPTIONAL list).

**Deduplication contract.** An AssessmentGap with the same `cycle_id` and `dimension` MUST be updated (incrementing `last_at`) rather than appended. A resolved gap MUST have `resolved_at` set; it MUST NOT persist in the active gap list after resolution.

---

## LifecycleBoundary

**Construct metadata.** kind: Schema · tier: FOUNDATIONAL · standalone: true

Extends: CitizenBase

A LifecycleBoundary is a durable record of a safe lifecycle transition point at which inputs are consumed, operations are closed, and state is committed atomically.

```
LifecycleBoundary {
  id                REQUIRED  Identifier; prefix "lcb-"
  at                REQUIRED  string; ISO-8601; when boundary was declared open
  closed_at         OPTIONAL  string; ISO-8601 | null; when boundary was committed; null = in progress
  boundary_type     REQUIRED  enum: POST_ASSESSMENT | POST_VALIDATION | POST_REPAIR | CYCLE_COMPLETION | OPERATOR_REQUESTED
  state_before      REQUIRED  string; lifecycle state when boundary was opened
  state_after       OPTIONAL  string; lifecycle state after boundary committed; null while in progress
  inputs_applied    REQUIRED  list of string; Input ids consumed at this boundary
  operations_closed OPTIONAL  list of string; Operation ids closed at this boundary
}
```

Uses TemporalFields: at (as created_at), closed_at (as archived_at).
Used in: State.lifecycle_boundaries (OPTIONAL rolling log, max 50).

**Integrity contract.** A LifecycleBoundary MUST NOT be committed with `state_after = null`. A boundary left open (closed_at = null) at process start MUST be treated as a partial-update recovery case per §74 and the Transaction Recovery Protocol (AP27, §62i). An incomplete boundary MUST emit IntegrityGap(`kind: "lifecycle-boundary-violation"`, severity=BLOCKING) until resolved.

---

## IntegritySignal

**Construct metadata.** kind: Schema · tier: FOUNDATIONAL · standalone: true

Extends: CitizenBase

An IntegritySignal is a durable record of a condition observed by the runtime that violates or threatens the integrity of lifecycle state, Evidence, or operational correctness.

```
IntegritySignal {
  id               REQUIRED  Identifier; prefix "isig-"
  at               REQUIRED  string; ISO-8601; when signal was observed
  signal_type      REQUIRED  enum: VALIDATION_FAILURE | CONSISTENCY_CHECK | ACTIVATION_HEALTH | STAGNATION | DEPENDENCY_CYCLE | PROVENANCE_UNDECLARABLE | OTHER
  severity         REQUIRED  enum: BLOCKING | WARNING
  source_check     REQUIRED  string; identifier of the check or mechanism that produced this signal
  payload          OPTIONAL  dict; signal-type-specific payload (e.g., failed_criterion, affected_ids)
  resolved_at      OPTIONAL  string; ISO-8601 | null; when signal was cleared
}
```

Uses TemporalFields: at (as created_at), resolved_at.
Used in: State.integrity_signals (OPTIONAL list).
Referenced from: §27 Evidence Integrity, §60 Validation and Acceptance, §64 Lifecycle States (REPAIRING entry conditions).

**Signal-to-REPAIRING contract.** An IntegritySignal of severity BLOCKING MUST trigger evaluation for entry to REPAIRING state (§64) at the next assessment cycle boundary. An IntegritySignal of severity WARNING MUST be surfaced in the InspectionSurface (§62l) but MUST NOT alone trigger REPAIRING. A runtime MUST NOT enter REPAIRING without a durable IntegritySignal record — "autonomous inference of integrity failure without an attributable check result MUST NOT constitute valid entry" per §64.

---

## JustificationContext

**Construct metadata.** kind: Schema · tier: FOUNDATIONAL · standalone: true

Extends: CitizenBase

A JustificationContext is a durable evaluation record capturing the five-predicate check that determines whether a proposed lifecycle action is justified and authorized at the time of evaluation.

```
JustificationContext {
  id              REQUIRED  Identifier; prefix "jctx-"
  at              REQUIRED  string; ISO-8601; when evaluation was performed
  action_scope    REQUIRED  string; scope path of the proposed action
  has_authority   REQUIRED  bool; AuthorityClosureInvariant check passed
  aligns_intent   REQUIRED  bool; proposed action aligns with active governing Intent
  has_evidence    REQUIRED  bool; at least one piece of supporting Evidence exists
  not_blocked     REQUIRED  bool; no active BLOCKING IntegrityGap in action_scope
  has_capability  REQUIRED  bool; required Executor capability is AUTHENTICATED/AUTHORIZED
  is_justified    REQUIRED  bool; computed: has_authority AND aligns_intent AND has_evidence AND not_blocked AND has_capability
  decision_id     OPTIONAL  string; DecisionRecord id that consumed this context
}
```

Uses TemporalFields: at (as created_at).
Used in: DecisionRecord.justification_context_id (OPTIONAL reference field).
Referenced from: §11 Autonomous Decision Space, §38 Objective Discovery, §47 Executor Boundary.

**Formal predicate.** An action is a justified authorized action if and only if: `has_authority = true` (AuthorityClosureInvariant, §62l) AND `aligns_intent = true` AND `has_evidence = true` AND `not_blocked = true` AND `has_capability = true`. All five conditions are jointly necessary. An action that satisfies only four of five MUST NOT proceed. **Audit contract.** When a consequential lifecycle action is accepted, the JustificationContext MUST be preserved in durable state and linked via `decision_id`. It MUST NOT be compacted away while the DecisionRecord is active.

## Vital Definition

A Vital is a derived health indicator computed from one or two Metric Definitions.

```
VitalDefinition {
  id            REQUIRED  stable identifier (Input id of the registering input)
  name          REQUIRED  unique vital name within this lifecycle
  numerator     REQUIRED  MetricDefinition name
  denominator   OPTIONAL  MetricDefinition name; when present, vital = numerator / denominator
  window        REQUIRED  string; observation window description (e.g. "current", "7d")
  created_at    REQUIRED  timestamp; when this definition was registered
  updated_at    REQUIRED  timestamp; updated when definition is replaced
  description   OPTIONAL  string; human-readable explanation
  deprecated_at OPTIONAL  timestamp | null; set when this vital is retired; null = active
}
```

Uses TemporalFields: created_at, updated_at, deprecated_at (as archived_at).
Used in: Config.vital_definitions.
```

## Config Document

The Config Document is the bootstrap configuration supplied at `init`. It is the single authoritative source for initial Rule Ledger seeding, executor wiring, and lifecycle policy. Once seeded, the Ledger becomes the source of truth for governance rules; the Config Document MUST NOT be re-read per cycle as a substitute for querying the Ledger.

```
Config {
  product          REQUIRED  string; human-readable product name
  product_files    REQUIRED  list of relative file paths constituting the Product
  state_path       REQUIRED  relative path to the durable state file
  intent           REQUIRED  {
                               purpose:  string; the mission statement (seeds PURPOSE rule)
                               retained: list[string]; statements never autonomously mutable
                                         (each seeds a PROHIBITION rule)
                             }
  authority        REQUIRED  {
                               delegated: list[string]; autonomously authorized scopes
                                          (each seeds a PERMISSION rule)
                               reserved:  list[string]; require operator decision
                                          (each seeds a PROHIBITION rule)
                               provenance: OPTIONAL string
                               source:     OPTIONAL string
                             }
  constraints      REQUIRED  list[string]; hard constraint statements (each seeds a PROHIBITION)
  self_evolution_policy REQUIRED {
                               mode:       NECESSARY_ONLY | CONTINUOUS | DISABLED
                               source:     OPTIONAL string
                               provenance: OPTIONAL string
                             }
  executor         REQUIRED  {
                               enabled:                        bool
                               max_executor_calls_per_24h:     int ≥ 1
                               max_executor_calls_per_30d:     int ≥ max_executor_calls_per_24h
                               discovery_interval_seconds:     int
                               max_discovery_interval_seconds: int
                               timeout_seconds:                int
                               capacity_retry_mode:            automatic | dynamic | fixed
                               capacity_retry_delay_ms:        int
                               discovery_yield_exhausted_threshold: int
                               transient_network_backoff_seconds:   int; default 300; MUST be
                                                                    < capacity_fallback_seconds
                               systematic_failure_threshold:        int; default 3; consecutive
                                                                    failures triggering systematic
                                                                    failure classification
                               providers:  list[ExecutorProvider]
                               allowed_files_by_scope: dict[scope → list[relative_path]]
                             }
  evaluation_system REQUIRED {
                               version:                 int
                               minimum_evidence_units:  int ≥ 1
                               weights:                 dict[component → float 0.0–1.0]
                             }
  external_metrics  REQUIRED {
                               mode: DISABLED | PROVIDED_ONLY
                                     | DISCOVER_PUBLIC_AND_USE_PROVIDED
                               sources: list[ConnectorSource seed]
                             }
  scope_priority    REQUIRED  ScopePriorityConfig (see ScopePrioritySystem)
  efficiency        REQUIRED  {
                               max_product_growth_bytes_per_change: int
                               max_product_growth_ratio_per_change: float
                               max_reasoning_memory_entries:        int
                             }
  operator_patterns OPTIONAL  list of {id, pattern, default_response}
  change_explanations OPTIONAL {mode: disabled | auto | enabled}
  analytics_export  OPTIONAL  {mode: DISABLED | ON_DEMAND | ON_CHECKPOINT}
  staleness_windows  OPTIONAL  {
                               decision_seconds: int; default 2592000 (30 d)
                               evidence_seconds: int; default 604800 (7 d)
                               rules_seconds:    int; default 7776000 (90 d)
                               by_scope: OPTIONAL map[ProductScope → int]; per-scope
                                         decision staleness window override;
                                         absent scope falls back to decision_seconds
                             }
  context_budget   OPTIONAL  {
                               target_utilization:   float 0.0–1.0 (default 0.70)
                               hard_cap_fraction:    float 0.0–1.0 (default 0.90)
                               executor_context_cap: int; token capacity of executor class
                             }
  capability_envelope  OPTIONAL  {
                                   capabilities:          list[CapabilityStatement]; declared required capabilities
                                   completeness_target:   UnitFloat (default 1.0); fraction of caps that must be
                                                          CAPABLE to reach CAPABLE maturity level
                                   complexity_ceiling:    OPTIONAL int; max product_surface_measure
                                   value_density_floor:   OPTIONAL float; minimum value_density
                                   surface_unit:          OPTIONAL string; "lines" | "schema_count" | custom
                                                          (default "lines")
                                   milestones:            OPTIONAL list[ProductMilestone]
                                 }
  staleness            OPTIONAL  {
                                   decisions_hours: integer; default 72; MUST be ≥ 1
                                   evidence_hours:  integer; default 168; MUST be ≥ 1
                                   rules_hours:     integer; default 720; MUST be ≥ 1
                                   metrics_hours:   integer; default 168; MUST be ≥ 1
                                 }
  context_budget_r58   OPTIONAL  {
                                   hard_cap_fraction:  float; fraction of context window treated as hard cap;
                                                       default 0.80; MUST be in (0.0, 1.0)
                                   min_floor_fraction: float; minimum fraction below which eviction MUST stop;
                                                       default 0.10; MUST be < hard_cap_fraction
                                 }
  wake                 OPTIONAL  {
                                   max_stale_hours: integer; hours after which a STALE WakeRegistration becomes
                                                    BLOCKING; default 168; MUST be ≥ 1
                                 }
  test_coverage        OPTIONAL  {
                                   freshness_hours: integer; hours after which a test result is considered stale;
                                                    default 24; MUST be ≥ 1
                                 }
  sweet_spot           OPTIONAL  {
                                   value_density_floor: float; minimum acceptable value_density before a WARNING
                                                        is surfaced; default 0.30; MUST be in [0.0, 1.0]
                                 }
  retention            OPTIONAL  {
                                   auto_trigger_bytes: integer; State Document size in bytes that triggers
                                                       automatic retention evaluation; default 10485760 (10 MB);
                                                       MUST be ≥ 1048576 (1 MB)
                                 }
  metric_sources       OPTIONAL  {
                                   registry:        list[URL]; pre-configured metric source URLs; default []
                                   search_endpoint: URL | null; optional search endpoint for public source
                                                    discovery; default null
                                 }
  archive_search_paths OPTIONAL  list[path]; additional paths to search when a CompactionSummary archive_path
                                 cannot be resolved; default []; paths MUST be relative to the URACE system root
  generated_file_globs OPTIONAL  list[glob]; additional glob patterns identifying generated files to exclude from
                                 surface measure computation; default []
  community_inbox      OPTIONAL  {
                                   feeds:                list[CommunityFeed]; configured feed sources; default []
                                   approval_mode:        ApprovalMode; pipeline approval mode; default SMART
                                   confidence_threshold: float; minimum confidence_score to produce a PatchProposal;
                                                         default 0.60; MUST be in [0.0, 1.0]
                                   relevance_floor:      float; minimum relevance_score to pass filtering;
                                                         default 0.40; MUST be in [0.0, 1.0]
                                   max_queue_depth:      integer; maximum active PatchProposal records; default 50;
                                                         MUST be ≥ 1
                                   proposal_expiry_hours: integer; hours after which an unresolved PatchProposal
                                                          transitions to EXPIRED; default 168; MUST be ≥ 1
                                   executor_credit_priority: string; scheduling priority for CSI/PPP_M executor
                                                             calls relative to other lifecycle executor work;
                                                             INBOX_HIGH | INBOX_NORMAL | INBOX_LOW; default
                                                             INBOX_NORMAL; INBOX_LOW defers to discovery/evolution
                                 }
  product_registry     OPTIONAL  list[ProductEntry]; registered products; default []
  active_product       OPTIONAL  string; name of currently active product; if set, overrides Config.product for
                                 active product name and routes state_path to the matching ProductEntry.state_path;
                                 if absent, Config.product is used
}
```

**r58 Config extensions.** The following subschemas extend the Config record to support r58 mechanisms. All fields are optional with stated defaults.

`staleness` subschema (supersedes `staleness_windows`): `decisions_hours` (default 72), `evidence_hours` (default 168), `rules_hours` (default 720), `metrics_hours` (default 168). All values MUST be ≥ 1. When both `staleness` and `staleness_windows` are present, `staleness` takes precedence.

`context_budget_r58` subschema: `hard_cap_fraction` (fraction of context window treated as hard cap; default 0.80), `min_floor_fraction` (minimum fraction below which eviction MUST stop; default 0.10; MUST be < `hard_cap_fraction`). Note: the `context_budget` field above covers `target_utilization` and `executor_context_cap`; `context_budget_r58` adds the r58-introduced cap/floor pair.

`wake` subschema: `max_stale_hours` (hours after which a STALE WakeRegistration becomes BLOCKING; default 168; MUST be ≥ 1).

`test_coverage` subschema: `freshness_hours` (hours after which a test result is considered stale; default 24; MUST be ≥ 1).

`sweet_spot` subschema: `value_density_floor` (minimum acceptable value_density before a WARNING is surfaced; default 0.30; MUST be in [0.0, 1.0]).

`retention` subschema: `auto_trigger_bytes` (State Document size in bytes that triggers automatic retention evaluation; default 10485760 (10 MB); MUST be ≥ 1048576 (1 MB)).

`metric_sources` subschema: `registry` (pre-configured metric source URLs; default empty list), `search_endpoint` (optional search endpoint for public source discovery; default null).

`archive_search_paths`: additional paths to search when a CompactionSummary archive_path cannot be resolved; default empty list; paths MUST be relative to the URACE system root.

`generated_file_globs`: additional glob patterns identifying generated files to exclude from surface measure computation; default empty list.

**r61 Config extensions.** The following subschema extends the Config record to support r61 community signal ingestion. The field is optional with stated defaults.

`community_inbox` subschema: `feeds` (configured CommunityFeed sources; default empty list), `approval_mode` (ApprovalMode enum governing proposal advancement; default SMART), `confidence_threshold` (minimum confidence_score to produce a PatchProposal; default 0.60; MUST be in [0.0, 1.0]; MUST be ≥ `relevance_floor`), `relevance_floor` (minimum relevance_score to pass signal filtering; default 0.40; MUST be in [0.0, 1.0]), `max_queue_depth` (maximum concurrent active PatchProposal records; default 50; MUST be ≥ 1), `proposal_expiry_hours` (hours before unresolved PatchProposal expires; default 168; MUST be ≥ 1), `executor_credit_priority` (scheduling priority for CSI/PPP_M Executor calls relative to discovery/evolution: INBOX_HIGH | INBOX_NORMAL | INBOX_LOW; default INBOX_NORMAL).

**CommunityFeed adapter fields (r63):** Each CommunityFeed record carries `adapter_timeout_seconds` (connection/read timeout; default 30; MUST be ≥ 1), `adapter_retry_count` (retry attempts before `community-feed-adapter-unavailable` gap; default 3; MUST be ≥ 0), `polling_interval_seconds` (poll cadence for RSS/POLLING adapters; default 300s; MUST be ≥ 60; WEBHOOK and PUSH adapters MUST ignore this field as they are event-driven).

**Immutability contract.** The Config Document MUST NOT be modified by autonomous lifecycle operation. Only the `executor` budget subkeys and `evaluation_system.weights` MAY be updated via authorized `budget_control` and `evaluation_control` inputs respectively. All other fields are fixed at bootstrap. `context_budget` is fixed at bootstrap and MUST NOT be modified autonomously.

## State Document

The State Document is the root of all durable lifecycle state. It MUST be written atomically. Its schema version controls migration compatibility.

```
State {
  schema_version        REQUIRED  int; current = 1
  state_version         REQUIRED  int; incremented on every durable write
  created_at            REQUIRED  timestamp; set once at init
  updated_at            REQUIRED  timestamp; updated on every durable write
  lifecycle_state       REQUIRED  ONBOARDING | DORMANT | ACTIVE | ASSESSING | VALIDATING | REPAIRING
                                  | BLOCKED | RECONCILING | WAITING_FOR_CAPACITY
                                  | WAITING_FOR_CONDITION | WAITING_FOR_SCHEDULE
                                  | WAITING_FOR_AUTHORITATIVE_DECISION | PAUSED
  intent                REQUIRED  copy of Config.intent (snapshot at init)
  authority             REQUIRED  copy of Config.authority (snapshot at init)
  constraints           REQUIRED  copy of Config.constraints (snapshot at init)
  self_evolution_policy REQUIRED  {mode, source, provenance}
  rule_ledger           REQUIRED  LedgerContainer
  objectives            REQUIRED  list[Objective]
  current_objective     REQUIRED  Objective id | null
  current_plan          REQUIRED  Plan | null
  operations            REQUIRED  list[Operation]
  evidence              REQUIRED  list[Evidence]
  decision_records      REQUIRED  list[DecisionRecord]
  checkpoints           REQUIRED  list[Checkpoint]
  progress_profiles     REQUIRED  list[ProgressProfile]
  progress_observations REQUIRED  list (observation records from metric collection)
  metric_system         REQUIRED  MetricSystem
  evaluation_system     REQUIRED  EvaluationSystem
  scope_priority_system REQUIRED  ScopePrioritySystem
  external_metric_state REQUIRED  ExternalMetricState
  context_inputs        REQUIRED  list[ContextInput] (max 200, rolling)
  connector_sources     REQUIRED  list[ConnectorSource]
  metric_definitions    REQUIRED  list[MetricDefinition]
  vital_definitions     REQUIRED  list[VitalDefinition]
  processed_input_ids   REQUIRED  list[string] (idempotency log, max 1000)
  value_trajectory      REQUIRED  ValueTrajectory
  destination_anchor    REQUIRED  DestinationAnchor
  wake_registry         REQUIRED  list[WakeRegistration]
  blockers              REQUIRED  list[Blocker]
  unresolved_effects    REQUIRED  list[UnresolvedEffect]
  pending_validation    REQUIRED  list[PendingValidation]
  executor_state        REQUIRED  ExecutorState
  operator_patterns     REQUIRED  list (copy from config at init)
  pattern_memory        REQUIRED  dict (implementation-defined; MAY be empty)
  reasoning_memory      REQUIRED  list (reasoning hypothesis entries; max bounded by config)
  last_cycle            REQUIRED  timestamp | null
  integrity_gaps        REQUIRED  list[IntegrityGap]
  status_transitions    REQUIRED  list[StatusTransition]
  spec_audit_state      OPTIONAL  SpecAuditState | null
  triggers              OPTIONAL  list[Trigger]
  pending_runtime_activation OPTIONAL dict; present when a runtime-scope change awaits activation
  restart_requested     OPTIONAL  bool; set to true when runtime restart is needed
  system_repair_registry OPTIONAL dict[key → SystemRepairEntry]
  quality_deltas         OPTIONAL  list[QualityDelta]; rolling quality trajectory per scope (AP9)
  quality_state          OPTIONAL  list[QualityStateEntry]; per-scope streak accumulators; one entry per scope; initialized empty
  reingestion_records    OPTIONAL  list[ReIngestionRecord]; append-only log of re-ingestion events
  sweet_spot_assessments OPTIONAL  list[SweetSpotAssessment]; history of sweet spot evaluations; latest is current
  capability_states      OPTIONAL  list[CapabilityEnvelopeEntry]; one entry per declared capability
  value_density_history  OPTIONAL  list[ValueDensityRecord]; time-series of value density snapshots
  product_versions       OPTIONAL  list[ProductVersion]; one record per milestone achievement; append-only
  test_run_records       OPTIONAL  list[TestRunRecord]; test execution results; feeds QualityDelta
  derivation_records     OPTIONAL  list[DerivationRecord]; audit trail of derive invocations (r36)
  derivation_refs        OPTIONAL  list[DerivedManifestRef]; formal saved manifest refs — canonical from r36; coexists with derived_manifest_refs for backward compat
  compliance_records     REQUIRED  list[ComplianceRecord]; append-only compliance trajectory; one record per domain per validation evaluation
  compliance_state       REQUIRED  dict[domain → ComplianceState]; current posture per validation domain; one entry per domain
  executor_providers     REQUIRED  list[ExecutorProvider]; active executor provider bindings; initialized from Config.executor.providers at bootstrap
  metric_effects         OPTIONAL  list[MetricEffect]; metric observation history
  feature_bundle_refs   OPTIONAL  list[FeatureBundleRef]; saved feature bundle references; default []
  community_feeds       OPTIONAL  list[CommunityFeed]; registered feed sources; default []
  community_signals     OPTIONAL  list[CommunitySignal]; ingested signals; default []
  patch_proposals       OPTIONAL  list[PatchProposal]; proposal queue; default []
  assessment_gaps       OPTIONAL  list[AssessmentGap]; active and recently resolved assessment gaps; deduplication by cycle_id+dimension; default []
  lifecycle_boundaries  OPTIONAL  list[LifecycleBoundary]; rolling log of boundary records (max 50); default []
  integrity_signals     OPTIONAL  list[IntegritySignal]; active and resolved integrity signals; default []
  onboard_records       OPTIONAL  list[OnboardRecord]; completed and superseded onboard records; default []
  switch_records        OPTIONAL  list[SwitchRecord]; audit trail of product switches; default []
}
```

**Atomic write contract.** Every write to the State Document MUST be atomic from the perspective of recovery: after a crash, the state file MUST reflect either the pre-write state or the fully committed post-write state. Partial writes MUST NOT be possible.

**schema_version contract.** If the `schema_version` in a loaded State Document does not match the running implementation's expected version, the implementation MUST surface this as a named migration-required condition and MUST NOT silently proceed with an incompatible schema.

## Reasoning Memory Entry

A Reasoning Memory Entry is a hypothesis or structural pattern retained in `reasoning_memory`.

```
ReasoningMemoryEntry {
  id           REQUIRED  stable identifier
  pattern      REQUIRED  string; the recognized pattern or hypothesis
  status       REQUIRED  ACTIVE | TENTATIVE; ACTIVE when confidence ≥ 0.6 (see INFER_BLOCKING)
  confidence   REQUIRED  float 0.0–1.0
  count        REQUIRED  int ≥ 1; times this pattern has been observed
  source_ids   REQUIRED  list[string]; Evidence or Input ids that support this pattern
  created_at   REQUIRED  timestamp
  updated_at   REQUIRED  timestamp
  expires_at   OPTIONAL  timestamp | null; when this entry should be reviewed for expiry
}
```

**Status threshold contract.** A ReasoningMemoryEntry MUST be classified `ACTIVE` when its `confidence` ≥ 0.6 and `TENTATIVE` otherwise. The threshold 0.6 is distinct from `INFER_BLOCKING` (0.85); ACTIVE status enables use in summaries but does not gate or block operations.

## Ledger Container

The Ledger Container is the root of the Rule Ledger stored within the State Document.

```
LedgerContainer {
  schema_version  REQUIRED  int; current = 1
  rules           REQUIRED  list[Rule]; all rules ever created (active and inactive)
  relationships   REQUIRED  list[Relationship]; explicit edge records between rules
  change_bindings REQUIRED  list[Change]; all change binding records (max 500, rolling)
  established_at  REQUIRED  timestamp
  updated_at      REQUIRED  timestamp
}
```

**Completeness contract.** `rules` MUST contain every Rule ever added, including deactivated and superseded rules. `change_bindings` holds the rolling 500 most recent Change records. `relationships` holds every explicit edge added between rules.

## Relationship

A Relationship is an explicit edge in the rule DAG. Relationships that are implicit in Rule fields (`derived_from`, `superseded_by`) MUST also be mirrored as Relationship records to enable graph traversal without scanning all rule fields.

```
Relationship {
  from_id    REQUIRED  source Rule id
  to_id      REQUIRED  target Rule id
  type       REQUIRED  derived_from | governed_by | governed_changes
                       | superseded_by | conflicts_with
  recorded_at REQUIRED timestamp
  source      OPTIONAL string; what created this relationship
}
```

**DAG contract.** No Relationship of type `derived_from` or `governed_by` MUST introduce a cycle. An implementation that would create a cycle MUST reject the Relationship and surface the rejection as Evidence.

**Consistency contract.** When a Rule's `derived_from` list is non-empty, a Relationship record of type `derived_from` MUST exist for each entry. When `superseded_by` is set, a Relationship of type `superseded_by` MUST exist. These MUST be kept in sync.

## Executor Call

An Executor Call is the record of a single invocation of an Executor for discovery or execution. It is stored in ExecutorState and is the primary resource-accounting surface.

```
ExecutorCall {
  id                        REQUIRED  stable identifier
  at                        REQUIRED  timestamp
  stage                     REQUIRED  discovery | execution
  reason                    REQUIRED  string; Objective id or trigger description
  outcome                   REQUIRED  attempted | no_effect | accepted | concurrent_change
                                      | deferred_provider_capacity | awaiting_operator_decision
                                      | failed
  transport_attempts        REQUIRED  int ≥ 1
  logical_reservation_reused REQUIRED bool
  executor_attribution      REQUIRED  {executor_id, adapter, capability,
                                       attempted_executors: list, logical_reservation: string|null}
  observed_metric_effect    OPTIONAL  {improved: int, regressed: int}; set on accepted
  changed_files             OPTIONAL  list[string]; set on accepted
  change_id                 OPTIONAL  Operation id; set on accepted
  trigger_signature         OPTIONAL  string | null; deduplication key for triggered discovery
  last_transport_attempt_at OPTIONAL  timestamp; set when transport_attempts > 1
  completed_at              OPTIONAL  timestamp | null; when execution finished (accepted or failed)
  usage                     OPTIONAL  {total_tokens: int, cost: float}; provider-reported
}
```

Uses TemporalFields: at (as created_at), last_transport_attempt_at (as last_call_at), completed_at. Uses canonical: Identifier (id), ExecutorAttribution (executor_attribution), MetricEffect (observed_metric_effect), UsageRecord (usage).

## Executor State

The Executor State tracks the operational status of the Executor subsystem and call history.

```
ExecutorState {
  last_discovery_at              REQUIRED  timestamp | null
  last_operation_at              REQUIRED  timestamp | null
  last_availability_check        REQUIRED  timestamp | null
  available                      REQUIRED  bool | null
  failures                       REQUIRED  list[FailureRecord]
  executor_calls                 REQUIRED  list[ExecutorCall] (rolling, bounded by config)
  discovery_calls                REQUIRED  int; total discovery calls this lifecycle
  provider_pool                  REQUIRED  dict[string → ProviderStatus]; keyed by provider_id
  discovery_budget_status        REQUIRED  DiscoveryBudgetStatus; current credit gate outcome
  unproductive_discovery_streak  REQUIRED  int ≥ 0; consecutive complete-cycle calls with
                                           no justified action, ineligible scope, or transport
                                           failure; resets on productive accepted result
  discovery_trigger              OPTIONAL  {reason: string, signature: string}; set when new
                                           context forces discovery
  discovery_defer_reason         OPTIONAL  string | null; human-readable reason the current
                                           discovery cycle was deferred; present only when
                                           discovery_budget_status is a deferral state
  capacity_status                OPTIONAL  WAITING_PROVIDER_CAPACITY | PROBE_DUE | AVAILABLE | null;
                                           provider capacity probe state; set by the capacity probe
                                           path independently of discovery_budget_status
  progress_vector                OPTIONAL  float [0.0, 1.0] | null; ratio of completed Objectives to
                                           total known Objectives in the current goal scope; updated
                                           at each cycle boundary; null until first Objective is known
  progress_stagnant_cycles       OPTIONAL  int ≥ 0; consecutive cycles where progress_vector has not
                                           increased; resets to 0 on any increase; configurable
                                           stagnation_threshold (default 5) triggers REPAIRING entry
  execution_budget               OPTIONAL  ExecutionBudget | null; goal-level resource envelope;
                                           null means no budget floor enforced
  recovery_manifest              OPTIONAL  RecoveryManifest | null; most recent manifest emitted at
                                           repair-exhausted in auto mode; null if none emitted
}
```

Uses canonical: FailureRecord (failures entries), ProviderStatus (provider_pool values), DiscoveryBudgetStatus (discovery_budget_status), ExecutionBudget (execution_budget), RecoveryManifest (recovery_manifest).

## ExecutionBudget

Goal-level resource envelope. Distinct from `DiscoveryBudgetStatus`, which tracks per-cycle discovery credits. `ExecutionBudget` governs the total resource floor for the entire goal-scoped run, not individual discovery cycles.

```
ExecutionBudget {
  max_iterations      REQUIRED  int ≥ 1; maximum lifecycle cycles before budget-exhausted terminal
  max_executor_calls  REQUIRED  int ≥ 1; maximum total Executor calls before budget-exhausted terminal
  iterations_used     REQUIRED  int ≥ 0; current count; incremented at each cycle boundary
  executor_calls_used REQUIRED  int ≥ 0; current count; incremented at each Executor call
}
```

**Budget-exhausted contract.** When `iterations_used ≥ max_iterations` OR `executor_calls_used ≥ max_executor_calls`, the lifecycle MUST treat the condition as budget-exhausted. In `auto` execution mode, budget-exhausted MUST emit a `RecoveryManifest` and perform a graceful stop per the repair-exhausted auto clause (§64). In `supervised` execution mode, budget-exhausted MUST surface a named `budget-exhausted` BLOCKING IntegrityGap and enter `BLOCKED`. **Default contract.** When `execution_budget` is null, no budget floor is enforced; the lifecycle runs until goal completion or repair-exhausted terminal. **Scope contract.** `ExecutionBudget` fields MUST NOT track token-level consumption; token tracking is a separate concern. Fields cover only iteration and Executor call counts.

## DiscoveryBudgetStatus

The canonical enumeration of outcomes from the Discovery Credit Gate (§62c). Written to `ExecutorState.discovery_budget_status` at every cycle boundary. Each value is a mutually exclusive gate outcome; the gate evaluates conditions in priority order and records the first matching outcome.

```
DiscoveryBudgetStatus =
  | WITHIN_BUDGET                   — no gate condition active; credit may be spent
  | SYSTEMATIC_FAILURE_COOLDOWN     — executor in systematic-failure cooldown; all discovery
                                      deferred until cooldown expires
  | DAILY_LIMIT_OR_RESERVE_REACHED  — rolling 24h call count at or beyond the configured
                                      ceiling or reserve floor
  | MONTHLY_LIMIT_OR_RESERVE_REACHED — rolling 30d call count at or beyond the configured
                                       ceiling or reserve floor
  | DUPLICATE_TRIGGER_SUPPRESSED    — incoming discovery trigger is a duplicate of the most
                                      recently processed trigger signature; no new context
                                      would change the outcome
  | DEFERRED_PROPORTIONALITY        — discovery deferred by the proportionality gate; the
                                      expected marginal value of a discovery call is below the
                                      defensible threshold (e.g. lifecycle is BLOCKED)
  | DISCOVERY_YIELD_EXHAUSTED       — unproductive streak has reached the configured threshold;
                                      further discovery deferred until a qualifying reset event
  | WAITING_PROVIDER_CAPACITY       — executor provider is in a scheduled capacity-unavailability
                                      window; discovery deferred until capacity restores
```

**Ordering contract.** The Discovery Credit Gate MUST evaluate these conditions in the priority order above: systematic-failure cooldown first, then budget ceilings, then duplicate suppression, then proportionality, then yield exhaustion, then provider capacity. A lower-priority condition MUST NOT override a higher-priority gate.

**Deferral-reason contract.** When `discovery_budget_status` is any deferral state (any value other than `WITHIN_BUDGET`), the lifecycle MUST also set `ExecutorState.discovery_defer_reason` to a human-readable string stating the specific reason. The field MUST be cleared when `discovery_budget_status` returns to `WITHIN_BUDGET`.

**Inspection contract.** `discovery_budget_status` MUST be surfaced in every lifecycle inspection output. `discovery_defer_reason` MUST be included when non-null.

**Scope:** Discovery domain (§36–§43)

## External Metric State

The External Metric State records the current status of the external metrics subsystem.

```
ExternalMetricState {
  mode                         REQUIRED  DISABLED | PROVIDED_ONLY
                                         | DISCOVER_PUBLIC_AND_USE_PROVIDED
  source                       REQUIRED  string
  provenance                   REQUIRED  string
  last_collection              REQUIRED  timestamp | null
  latest                       REQUIRED  list[ObservationRecord]
  errors                       REQUIRED  list[ErrorRecord]
  failure_streak               OPTIONAL  int; consecutive failed collections
  next_collection_at           OPTIONAL  timestamp
  last_known_good              OPTIONAL  dict; last successful observation values
  last_error_signature         OPTIONAL  string | null; SHA-256 of current error set
  last_error_evidence_at       OPTIONAL  timestamp | null
  candidate_decision_links     OPTIONAL  list; operation references linked to observations
}
```

## Progress Profile

A Progress Profile is the measurement baseline and current reading for each observable dimension of product progress.

```
ProgressProfile {
  id                  REQUIRED  string (e.g. "blueprint-verification")
  objective_reference REQUIRED  string
  intended_outcome    REQUIRED  string
  measures            REQUIRED  dict[metric_name → MeasureEntry]
  guardrails          REQUIRED  list[string]; invariants that MUST NOT regress
  cadence             REQUIRED  string; how often measures are updated
  next_follow_up      REQUIRED  timestamp | string
  status              REQUIRED  active | archived
  created_at          REQUIRED  timestamp; when this profile was established
  updated_at          REQUIRED  timestamp; updated on every measure update
}
```

Uses TemporalFields: created_at, updated_at. Uses canonical: Identifier (id), MeasureEntry (measures dict values).

**Guardrail contract.** Each guardrail name in `guardrails` corresponds to a measure key in `measures`. An accepted Operation MUST NOT leave any guardrail measure worse than its baseline. If it does, the Operation MUST be rejected.

## Wake Registration

Extends: AuthorizedCitizen
Implements: GoverningRecord

A Wake Registration records a pending lifecycle wake condition that has been established but not yet satisfied.

```
WakeRegistration {
  id             REQUIRED  stable identifier
  scheduled_at   REQUIRED  timestamp; when this registration is due to trigger
  condition      REQUIRED  dict; the observable criterion that satisfies this registration
  kind           REQUIRED  SCHEDULED | TRIGGERED | CONDITIONAL
  established_at REQUIRED  timestamp; when this registration was created
  authority_basis OPTIONAL string; authorizing rule id or authority scope (GoverningRecord)
  scope          OPTIONAL  string; which lifecycle scope this registration serves (GoverningRecord)
  satisfied_at   OPTIONAL  timestamp | null; when the condition was met and registration fired
  replaces       OPTIONAL  WakeRegistrationId | null; id of the STALE registration this record supersedes;
                           null for original registrations
}
```

Uses TemporalFields: established_at (as created_at), scheduled_at, satisfied_at.

**Integrity contract.** On lifecycle restart, every WakeRegistration in `wake_registry` MUST be verified as still active in the current environment. A registration that cannot be verified MUST be surfaced as a wake-integrity gap (see §62 and README). A verified registration MUST NOT be discarded.

**Scope:** Dormancy/Wake domain (§64–§67)

## Unresolved Effect

An Unresolved Effect records a committed product change whose outcome has not yet been confirmed as complete.

```
UnresolvedEffect {
  operation_id          REQUIRED  Operation id
  journal_phase         REQUIRED  PREPARED | APPLYING | APPLIED | VALIDATED
  expected_file_hashes  REQUIRED  dict[relative_path → SHA-256]; expected post-change state
  recorded_at           REQUIRED  timestamp
  reconciled_at         OPTIONAL  timestamp; set when disposition is confirmed
  outcome               OPTIONAL  CONFIRMED_COMPLETE | ROLLED_BACK | UNRESOLVABLE
}
```

**Reconciliation contract.** An UnresolvedEffect MUST be reconciled before the lifecycle MAY converge to `IDLE`. A lifecycle with at least one open UnresolvedEffect MUST remain in `RECONCILING` or `BLOCKED` state and MUST surface the open effect as a named blocker.

## Scope Priority System

The Scope Priority System determines which product scope (documentation, runtime, metrics, rebootstrap) receives prioritized attention in the current lifecycle state.

```
ScopePrioritySystem {
  version                     REQUIRED  string (e.g. "dynamic-scope-priority-v1")
  revision                    REQUIRED  int; incremented on each recomputation
  computed_at                 REQUIRED  timestamp
  evidence_cutoff             REQUIRED  timestamp; evidence older than this was not considered
  max_weight_step_per_revision REQUIRED float; maximum change in normalized_weight per revision
  basis                       REQUIRED  string; human-readable derivation basis
  scopes                      REQUIRED  dict[ProductScope → ScopePriorityEntry]
}
```

Uses canonical: ProductScope (scopes keys), ScopePriorityEntry (scopes values), UnitFloat (max_weight_step_per_revision), TemporalFields (computed_at as created_at, evidence_cutoff).

**Normalization contract.** The sum of `normalized_weight` across all active scopes MUST equal 1.0 (±floating-point tolerance). A scope with `change_limited: true` has had its weight clamped by `max_weight_step_per_revision`.

## ScopePriorityConfig

The ScopePriorityConfig is the operator-supplied configuration for the scope priority system, stored in the Config Document.

```
ScopePriorityConfig {
  mode    REQUIRED  STATIC | DYNAMIC_BOUNDED; DYNAMIC_BOUNDED enables bounded weight adjustment
                   based on observed backlog and recency; STATIC holds weights fixed at init
  version REQUIRED  string; implementation-defined version tag (e.g. "dynamic-scope-priority-v1")
  max_weight_step_per_revision REQUIRED  float 0.0–1.0; maximum change in any scope weight per revision
  scopes  REQUIRED  dict[ProductScope → ScopePriorityConfigEntry]
}
```

```
ScopePriorityConfigEntry {
  base_weight      REQUIRED  float > 0.0; starting weight
  min_weight       REQUIRED  float > 0.0; autonomous floor
  max_weight       REQUIRED  float ≥ min_weight; autonomous ceiling
  artifacts        REQUIRED  list[relative_path]; product artifacts in this scope
  execution_scopes REQUIRED  list[string]; allowed_files_by_scope keys this scope uses
  label            OPTIONAL  string; human-readable scope description
}
```

## Context Input

A Context Input is operator-supplied authoritative context that informs discovery and planning.

```
ContextInput {
  id      REQUIRED  Input id of the originating Input
  at      REQUIRED  timestamp
  origin  REQUIRED  USER_SUPPLIED | SYSTEM_DERIVED
  text    OPTIONAL  string; free-form context text (max 20 000 chars)
  source  OPTIONAL  string; who supplied this context
}
```

**Retention contract.** The `context_inputs` list MUST be capped at 200 entries (rolling). Oldest entries are evicted first. An evicted entry MUST still appear in the Evidence log.

## Pending Validation

A Pending Validation record represents an Operation that could not be validated immediately due to a missing validation capability, and is queued for validation when capability is restored.

```
PendingValidation {
  id               REQUIRED  stable identifier
  operation_id     REQUIRED  Operation id
  operation_scope  REQUIRED  string
  queued_at        REQUIRED  timestamp
  reason           REQUIRED  string
  status           REQUIRED  PENDING_CAPABILITY
  note             REQUIRED  string; human-readable explanation
  validated_at     OPTIONAL  timestamp | null; set when validation completes
  expires_at       OPTIONAL  timestamp | null; backlog timeout; if exceeded without capability
                             restoration, record MUST be surfaced as a named stale-validation gap
}
```

Uses TemporalFields: queued_at, validated_at (as resolved_at), expires_at.

**Validation backlog contract.** When a validation capability is restored after being unavailable, URACE MUST process all PendingValidation records in `queued_at`-ascending order before accepting new work. No pending record MAY be silently discarded.

## Destination Anchor

The Destination Anchor is a tamper-evident digest of the lifecycle's core purpose and retained constraints. It is used to detect unauthorized drift in the governing intent.

```
DestinationAnchor {
  purpose       REQUIRED  string; copy of Config.intent.purpose
  retained      REQUIRED  list[string]; sorted copy of Config.intent.retained
  digest           REQUIRED  SHA-256 of JSON({purpose, retained}, sort_keys=True, no whitespace)
  established_at   REQUIRED  timestamp; when anchor was first written
  last_verified_at OPTIONAL  timestamp | null; last cycle-start at which anchor passed verification
}
```

Uses TemporalFields: established_at (as created_at), last_verified_at.

**Drift detection contract.** On every lifecycle cycle start, URACE MUST recompute the Destination Anchor digest and compare it to the stored `digest`. A divergence MUST be surfaced as a named governance-drift condition and MUST block all autonomous operations until the operator acknowledges the change.

## Metric System

The Metric System tracks the lifecycle's self-assessment of whether its current metrics are appropriate for measuring progress.

```
MetricSystem {
  version           REQUIRED  int; incremented when a change is applied
  last_review_at    REQUIRED  timestamp | null
  last_assessment   REQUIRED  string; human-readable outcome of last review
  change_needed     REQUIRED  bool; true = metric reconfiguration is recommended
  change_history    REQUIRED  list of {at, before, after, input}; append-only
}
```

## Evaluation System

The Evaluation System defines how the lifecycle weights evidence to produce an evolution readiness score.

```
EvaluationSystem {
  version                  REQUIRED  int
  minimum_evidence_units   REQUIRED  int ≥ 1
  weights                  REQUIRED  dict[component → float 0.0–1.0]
                                     weights MUST sum to a positive value
  last_review_at           REQUIRED  timestamp | null
  last_assessment          REQUIRED  string
  change_needed            REQUIRED  bool
  change_history           REQUIRED  list of {at, version, before, after, input}; append-only
}
```

**Weight contract.** At least one component weight MUST be strictly positive. Setting all weights to 0.0 MUST be rejected. Weights do not need to sum to 1.0; the evaluator normalizes internally.

## System Repair Entry

A System Repair Entry records a recurring fault detected in the lifecycle controller, used to deduplicate repair objectives.

```
SystemRepairEntry {
  fault            REQUIRED  dict; structured fault descriptor {component, code, operation, ...}
  runtime_version  REQUIRED  string; SHA-256 digest of the runtime file set at detection time
  count            REQUIRED  int ≥ 1; times this fault has recurred
  status           REQUIRED  OBSERVED | REPAIR_QUEUED | REPAIRED | REPAIR_FAILED
                             | ACTIVATION_REQUESTED | DEFERRED_CAPABILITY_OR_BUDGET
  first_at         REQUIRED  timestamp; when fault was first observed (serves as created_at)
  last_at          REQUIRED  timestamp; most recent recurrence (serves as updated_at)
  repaired_at      OPTIONAL  timestamp | null; set when status → REPAIRED
}
```

`ACTIVATION_REQUESTED` is set while a repair objective has been created and awaits executor activation; `DEFERRED_CAPABILITY_OR_BUDGET` is set when the repair cannot proceed because capability or budget is unavailable.

Uses TemporalFields: first_at (as created_at), last_at (as updated_at), repaired_at.

## TechniqueApplicationRecord

Records one application (or skip/defer) of a technique by the TechniqueApplicabilityGate (§62h).

```
TechniqueApplicationRecord {
  id                  REQUIRED    string         ; stable identifier, prefix ta-
  technique           REQUIRED    string         ; T1..T6 or canonical name
  verdict             REQUIRED    string         ; APPLY | SKIP | DELEGATE_EXECUTOR | DEFER
  reason              REQUIRED    string         ; gate guard that matched
  applied_at          REQUIRED    ISO-8601       ; timestamp of application
  cycle               OPTIONAL    integer        ; cycle counter at application time
  sd_result           OPTIONAL    boolean        ; result of SD(T, state) evaluation
  executor_delegated  OPTIONAL    boolean        ; True when DELEGATE_EXECUTOR verdict executed
  credits_consumed    OPTIONAL    integer        ; credits spent if executor was invoked
}
```
Uses canonical: Identifier (technique_id, objective_id, operation_id), TemporalFields (applied_at).
Used in: State.technique_application_log.

## BridgeRecord

Records one bridge translation event (§62i AP11).

```
BridgeRecord {
  id              REQUIRED    identifier       ; prefix br-
  bridge_name     REQUIRED    string           ; B1..B4 or canonical name
  source_schema   REQUIRED    string           ; CitizenSchema name of input
  target_schema   REQUIRED    string           ; CitizenSchema name of output
  translated_at   REQUIRED    iso_timestamp    ; timestamp of translation
  loss_declared   OPTIONAL    boolean          ; True when bridge is LOSSY_DECLARED
  dropped_fields  OPTIONAL    list<string>     ; fields dropped in lossy translation
}
```
Uses canonical: Identifier (id), TemporalFields (at).
Used in: State.evidence (kind=bridge_translation).

## OrchestratorRecord

Records one orchestrator execution (§62i AP12).

```
OrchestratorRecord {
  id                  REQUIRED    identifier       ; prefix orch-
  orchestrator_name   REQUIRED    string           ; e.g. cycle, spec_audit, compaction
  started_at          REQUIRED    iso_timestamp    ; when execution began
  completed_at        OPTIONAL    iso_timestamp    ; absent if aborted
  phases_completed    REQUIRED    list<string>     ; phase names in order
  outcome             REQUIRED    string           ; COMPLETED | ABORTED | DEGRADED
  failure_phase       OPTIONAL    string           ; phase where failure occurred if ABORTED
  postconditions_met  OPTIONAL    boolean          ;
}
```
Uses canonical: Identifier (id, orchestrator_id), TemporalFields (started_at, completed_at).
Used in: State.evidence (kind=orchestrator_completion).

## ScheduledTask

A durable named task scheduled for future execution (§62i AP18).

```
ScheduledTask {
  id                    REQUIRED    identifier       ; prefix task-
  name                  REQUIRED    string           ; human-readable name
  schedule              REQUIRED    TaskSchedule     ; when to execute
  scope                 REQUIRED    string           ; runtime | executor | spec_audit | metric_collection
  action                REQUIRED    string           ; lifecycle command or action identifier
  status                REQUIRED    string           ; ACTIVE | PAUSED | COMPLETED | ERROR
  created_by            REQUIRED    string           ; USER | AUTO
  authority_basis       REQUIRED    string           ; why this task was scheduled
  last_run_at           OPTIONAL    iso_timestamp    ; most recent execution time
  next_run_at           OPTIONAL    iso_timestamp    ; next scheduled execution time
  run_count             OPTIONAL    count            ; number of successful executions
  consecutive_failures  OPTIONAL    count            ; reset to 0 on success
  preserve_on_update    OPTIONAL    boolean          ; default True for USER tasks
}
```
Uses canonical: Identifier (id), TemporalFields (scheduled_at, executed_at).
Used in: State.scheduled_tasks.

## TaskSchedule

Scheduling definition for a ScheduledTask.

```
TaskSchedule {
  kind              REQUIRED    string           ; CRON | INTERVAL_SECONDS | TRIGGER | IMMEDIATE
  cron_expr         OPTIONAL    string           ; standard cron expression; required when kind=CRON
  interval_seconds  OPTIONAL    count            ; required when kind=INTERVAL_SECONDS
  trigger_event     OPTIONAL    string           ; evidence kind to watch; required when kind=TRIGGER
  next_run_at       OPTIONAL    iso_timestamp    ; pre-computed next run time
}
```
Uses canonical: Identifier (task_id).
Used in: ScheduledTask.schedule.

## CustomizationRecord

A declared user override that is preserved across spec updates (§62i AP19).

```
CustomizationRecord {
  id                  REQUIRED    identifier       ; prefix cust-
  scope               REQUIRED    string           ; config | spec_parameter | runtime_behavior
  key                 REQUIRED    string           ; dotted path to the overridden value
  value               REQUIRED    any              ; the user's override value
  reason              REQUIRED    string           ; why this override was made
  created_at          REQUIRED    iso_timestamp    ; creation timestamp
  preserve_on_update  REQUIRED    boolean          ; True = keep across spec updates
  conflict_status     OPTIONAL    string           ; OK | CONFLICT | RESOLVED
  conflict_detail     OPTIONAL    string           ; description of the conflict if any
}
```
Uses canonical: Identifier (id), TemporalFields (created_at).
Used in: State.customization_records.

## LexicalFormula

A paired record linking a natural language normative rule to its formula equivalent (§62i AP17 LSC).

```
LexicalFormula {
  id               REQUIRED    identifier       ; prefix lf-
  spec_section     REQUIRED    string           ; section reference e.g. §62c
  natural_language REQUIRED    string           ; the original prose rule
  formula          REQUIRED    string           ; the formula in standard mathematical notation
  variables        OPTIONAL    list<string>     ; variable names used in the formula
  sd_result        REQUIRED    boolean          ; True = self-determinable; False = executor-derived
  verified_at      OPTIONAL    iso_timestamp    ; when the formula was last verified correct
}
```
Uses canonical: Identifier (id, rule_id).
Used in: State.lexical_formulas.

## ClassificationResult

The structured output of executor-driven free-text classification for the `urace add` command (§62c `urace add`).

```
ClassificationResult {
  type        REQUIRED    string       ; goal | intent | constraint | command | response
  subtype     OPTIONAL    string       ; directive (intent); prohibition | permission (constraint); absent for goal
  parameters  REQUIRED    object       ; extracted parameters conforming to the target type's input schema
  confidence  REQUIRED    probability  ; classifier confidence in [0.0, 1.0]
  reasoning   OPTIONAL    string       ; brief explanation of the classification decision
  raw_text    REQUIRED    string       ; the original unmodified free-text input
}
```
Uses canonical: Identifier (id, input_id).
Used in: ClassificationBatch.results.

For `command`-type items, `parameters` MUST include a `command` field (string) naming the lifecycle operation and MAY include an `args` list.

For `response`-type items, `parameters` MUST include a `text` field (string) containing the message to display directly to the operator.

---

## ClassificationBatch

The top-level response returned by the Executor for a `urace add` command. A single free-text input may describe any combination of goals, intents, and constraints; the Executor detects each independently and returns all as a batch.

```
ClassificationBatch {
  items     REQUIRED    list<ClassificationResult>  ; one or more detected items in detection order; MUST NOT be empty
  compound  REQUIRED    boolean                     ; True when the input contained more than one detectable item
  raw_text  REQUIRED    string                      ; the original unmodified free-text input
  logic     OPTIONAL    string                      ; and (default) — execute all items in order; or — items are alternatives, operator chooses
}
```
Uses canonical: Identifier (id), TemporalFields (classified_at).
Used in: State.classification_batches.

---

### Domain-Section Citizen Registry

The following citizens are defined with full normative notation in their originating domain sections. They are registered here for catalog completeness.

**DiscoveryRecord** — append-only discovery cycle record. Full definition: §36. Used in: State.discovery_log.
**DiscoverySkip** — record of a skipped discovery cycle. Full definition: §36. Used in: State.discovery_log.
**AssessmentRecord** — append-only assessment cycle record. Full definition: §37. Used in: State.assessment_log.
**MarketSignal** — externally observed market-fit signal. Full definition: §59. Used in: State.market_signals.
**FitHypothesis** — a product-market fit hypothesis under evaluation. Full definition: §59. Used in: State.fit_hypotheses.

## OnboardRecord

A durable record that the Product Onboard Phase completed successfully and autonomous cycles are authorized to begin. Absence of an OnboardRecord in State at cycle boundary MUST trigger `lifecycle_state = ONBOARDING` and halt autonomous execution until all onboard gates pass and the operator confirms.

```
OnboardRecord {
  id                    REQUIRED  Identifier; prefix "onb-"
  created_at            REQUIRED  ISO-8601 timestamp; when onboarding completed
  product_name          REQUIRED  string; value of Config.product at onboard time
  confirmed_by          REQUIRED  string; operator-supplied confirmation token or "auto" if all gates passed silently
  confirmed_at          REQUIRED  ISO-8601 timestamp; when operator issued `urace onboard confirm`
  config_digest         REQUIRED  DigestValue; SHA-256 of Config at onboard time (detects config replacement)
  gates_passed          REQUIRED  list[string]; names of all gates that passed (see §62o OnboardGate)
  capability_envelope_waived  OPTIONAL  bool; true if operator explicitly waived capability_envelope requirement; default false
  notes                 OPTIONAL  string; operator-supplied free-text notes recorded at confirmation
}
```

**Staleness contract.** If `config_digest` diverges from the current Config digest at cycle boundary, URACE MUST emit IntegrityGap(`kind: "onboard-record-config-diverged"`, severity=WARNING) and surface it in `urace check`. The divergence MUST NOT trigger re-onboarding automatically; it is informational. Operator may re-run `urace onboard confirm` to refresh the record.

**Uniqueness contract.** At most one OnboardRecord with `product_name` matching the current Config.product MUST be active in State at any time. A second `urace onboard confirm` for the same product supersedes the prior record; the prior record MUST be retained with `superseded_at` set.

Used in: State.onboard_records.

## ProductEntry

A registered Product in the Product Registry (§62p). Each ProductEntry declares one Product's identity, state path, and files — enabling multi-product management within a single URACE installation.

```
ProductEntry {
  id                REQUIRED  Identifier; prefix "prod-"
  name              REQUIRED  string; human-readable product name
  state_path        REQUIRED  string; path to this product's State file
  product_files     REQUIRED  list[string]; file paths constituting this product
  intent_purpose    OPTIONAL  string; product intent text
  registered_at     REQUIRED  ISO-8601 timestamp; when this entry was registered
  last_active_at    OPTIONAL  ISO-8601 timestamp; when this product was last active
  status            REQUIRED  ACTIVE | INACTIVE | ARCHIVED; default ACTIVE
}
```

**Uniqueness contract.** Each ProductEntry.name MUST be unique within Config.product_registry. A duplicate name MUST be rejected with `product-registry-duplicate-name` WARNING.

Used in: Config.product_registry.

## SwitchRecord

An audit record of a completed product switch. Every successful `urace product switch` appends one SwitchRecord to State.switch_records.

```
SwitchRecord {
  id              REQUIRED  Identifier; prefix "swrec-"
  from_product    REQUIRED  string; name of the product being switched away from
  to_product      REQUIRED  string; name of the product being switched to
  switched_at     REQUIRED  ISO-8601 timestamp; when the switch was committed
  switched_by     REQUIRED  string; "operator" or operator-supplied token
  reason          OPTIONAL  string; operator-supplied switch rationale
}
```

**Audit contract.** Every successful `urace product switch` MUST append one SwitchRecord to State.switch_records. SwitchRecords MUST NOT be compacted away for the life of the State.

Used in: State.switch_records.

---

# 62c. Mechanism Contracts

Mechanisms are the interlinking processes that move citizens from one state to another. Each mechanism MUST behave according to the contracts in this section regardless of implementation language, Executor type, or runtime environment.

## Input Queue Mechanism

**Construct metadata.** `kind: Mechanism` · `tier: FOUNDATIONAL` · `standalone: false` · `governed-by: [AP14]`

The Input Queue is the sole safe path for operator instructions to enter the lifecycle (AP14 — Durable Inbox, §62i). It guarantees FIFO ordering, atomicity, and idempotency.

```
OPERATOR COMMAND
  → queue_input() creates Input record with stable id
  → written as atomic file to inbox directory
  → lifecycle reads inbox at next safe boundary
  → processed_input_ids checked for idempotency
  → Input applied to state
  → Input file removed atomically with state write
  → Input id appended to processed_input_ids
```

**Atomicity contract.** The removal of an Input file and the state write that records its application MUST be atomic from the perspective of recovery: after a crash, either the Input is still present (not yet applied) or the state reflects its effect (already applied). A partially applied Input is a recovery condition.

**Ordering contract.** Inputs MUST be applied in `at`-ascending order. No Input MUST be promoted, demoted, or skipped based on its kind, content, or source.

**Idempotency contract.** `processed_input_ids` MUST be persisted in durable state. Before applying any Input, its `id` MUST be checked against this list. A match MUST skip the Input. `processed_input_ids` MUST NOT be truncated while any pending Input in the inbox shares an id with an entry that would be discarded.

**Boundary contract.** Inputs MUST NOT be applied mid-cycle. Application MUST occur only at a safe lifecycle boundary where the full state write can be committed atomically.

## Transaction Mechanism

**Construct metadata.** `kind: Mechanism` · `tier: COMPOSITIONAL` · `standalone: false` · `governed-by: [AP16, AP27]`

A Transaction wraps the file mutations of a single Operation, providing a rollback capability and a durable record for crash recovery. The before/after snapshot pair and phase-progressive delta journal implement AP16 — State Snapshot + Delta Log (§62i).

```
Transaction {
  id          REQUIRED  stable identifier
  operation   REQUIRED  Operation id
  created_at  REQUIRED  timestamp
  phase       REQUIRED  PREPARED | APPLYING | APPLIED | VALIDATED
  before      REQUIRED  dict[relative_path → file_content]; snapshot before mutation
  after       REQUIRED  dict[relative_path → file_content]; intended content after mutation
  applied     REQUIRED  list of relative_path; files successfully written
}
```

**Phase progression contract.**

```
PREPARED  →  APPLYING  →  APPLIED  →  VALIDATED
             (files written)    (validation passed)
```

Each phase MUST be written to the transaction journal on disk before transitioning. A transition that is not durably recorded is not complete.

**Rollback contract.** If a crash or failure is detected at any phase before `VALIDATED`, the transaction MUST be rolled back: all files in `before` MUST be restored to their snapshot content. The Operation MUST be marked `REJECTED_ROLLED_BACK`. The transaction journal MUST then be removed.

**Commit contract.** A transaction reaches `VALIDATED` only after independent validation passes (§60). A `VALIDATED` transaction MUST NOT be rolled back. The transaction journal MAY be removed after `VALIDATED` is durably written to lifecycle state.

**Recovery contract.** On lifecycle start, if a transaction journal exists:
- Phase `PREPARED` or `APPLYING`: roll back unconditionally.
- Phase `APPLIED`: re-run independent validation; if it passes, commit; if it fails, roll back.
- Phase `VALIDATED`: treat as already committed; do not re-apply.

## Authority Resolution Mechanism

**Construct metadata.** `kind: Mechanism` · `tier: FOUNDATIONAL` · `standalone: false` · `governed-by: [AP35]`

This mechanism implements **AP35 — Governance Ledger** (§62i).

Every proposed Operation MUST pass authority resolution before execution. Authority resolution consults the active Rule Ledger to determine whether the proposed scope and action are permitted.

```
PROPOSED OPERATION (scope, objective)
  → load active rules from Rule Ledger
  → check: scope within at least one active PERMISSION rule
  → check: no active PROHIBITION rule applies to this scope/action
  → check: action is consistent with active DIRECTIVE rules
  → if all pass: AUTHORIZED → proceed to Transaction
  → if any fail: DENIED → record Evidence(authority-resolution-denied) → block
```

**PERMISSION check contract.** An Operation MUST match at least one active PERMISSION rule whose scope includes the Operation's scope. A scope of `*` in a PERMISSION rule covers all scopes. If no matching PERMISSION rule exists, the Operation MUST be DENIED.

**PROHIBITION check contract.** If any active PROHIBITION rule applies to the Operation's scope and the operation's content overlaps with the prohibition's statement, the Operation MUST be DENIED. A PROHIBITION MUST NOT be bypassed by a PERMISSION of equal or lower level.

**L0 override contract.** No authority resolution path MAY authorize an Operation that would mutate, supersede, or deactivate a PURPOSE (L0) rule. Such an attempt MUST be DENIED unconditionally and recorded as Evidence.

**Denial record contract.** Every DENIED Operation MUST produce an Evidence record of kind `authority-resolution-denied` with a human-readable reason. The Operation MUST NOT proceed silently.

**Authority resolution cache invalidation.** A cached authority resolution result MUST be invalidated and re-computed if: (a) more than 3600 seconds have elapsed since `resolved_at`; (b) any Rule in the Rule Ledger with scope matching the Objective has been superseded or deleted since `resolved_at`. Stale cache use MUST emit `authority-cache-stale` WARNING IntegrityGap.

## Digest Computation

**Construct metadata.** `kind: Mechanism` · `tier: FOUNDATIONAL` · `standalone: false` · `governed-by: [AP36]`

The fixed algorithms and chain-continuity invariant implement **AP36 — Digest Chain Consistency** (§62i).

Three distinct digest computations are used across the citizen schemas. All three MUST be deterministic: the same inputs MUST always produce the same digest.

### Product Digest

Used in: Checkpoint.digest, Change.state_before_digest, Change.state_after_digest.

```
Algorithm:
  digest = SHA-256()
  for each file_path in sorted(product_files):
    digest.update(file_path.encode("utf-8"))
    digest.update(file_content_bytes)
  result = digest.hexdigest()
```

`product_files` MUST be the same set used by §61 Checkpoint. Sorting MUST be lexicographic on the relative file path string. An empty product file set MUST produce a deterministic digest of the empty input.

### Rule Snapshot Digest

Used in: Change.rule_snapshot_digest.

```
Algorithm:
  active = [{"id": r.id, "kind": r.kind, "statement": r.statement}
            for r in active_rules sorted by r.id]
  payload = JSON(active, sort_keys=True, separators=(",", ":"))
  result = SHA-256(payload.encode("utf-8")).hexdigest()
```

Serialisation MUST use no whitespace. Sorting MUST be lexicographic on `id`. This algorithm is fixed; an implementation MUST NOT vary the field set or sort order.

### State Digest Consistency Contract

`Change.state_after_digest` for change N MUST equal `Change.state_before_digest` for change N+1 in sequence, and MUST equal `Checkpoint.digest` for the `accepted-product-change` Checkpoint that records the same Operation. A divergence between any two of these three values for the same product state MUST be surfaced as a named integrity gap.

## Value Trajectory Self-Correction Mechanism

**Construct metadata.** `kind: Mechanism` · `tier: INTEGRATED` · `standalone: false` · `governed-by: [AP8, AP9]`

The rolling velocity accumulation and deceleration-triggered reassessment implement **AP8 — Fixpoint Calculus** (§62i) and **AP9 — Monotone Accumulator** (§62i).

The Value Trajectory mechanism continuously measures whether the lifecycle is producing value faster, slower, or at a stable rate. When deceleration is detected below a threshold, it MUST trigger an autonomous self-correction injection.

```
ACCEPTED OPERATION
  → record VelocityCheckpoint (value_rate = net_value_delta / elapsed_minutes)
  → recompute AccelerationReport over rolling 100-checkpoint window
  → if direction == "decelerating":
      if value_amplification < 0.5 OR yield_rate < 0.4:
        SEVERE DECELERATION → inject strategic reassessment Objective
      else:
        MODERATE DECELERATION → surface VELOCITY_DECLINING alert in vitals
  → if yield_rate < 0.5 AND sample_size ≥ 4:
      surface LOW_YIELD_RATE alert in vitals
```

**Injection contract.** When `self_correct_now` is true, URACE MUST inject a strategic reassessment Objective at the next safe lifecycle boundary. This Objective MUST have `scope: documentation`, `authority_basis: "value-deceleration-self-correction"`, and MUST appear in the Evidence log with kind `value-deceleration-self-correction`.

**Alert surfacing contract.** All active alerts from the AccelerationReport MUST be surfaced in `urace vitals` output. URACE MUST NOT suppress deceleration alerts because the lifecycle is otherwise making forward progress.

**Baseline contract.** Acceleration MUST NOT be computed until at least 2 checkpoints exist. Direction MUST NOT be labelled until at least 4 checkpoints exist. `AccelerationReport.status` MUST reflect this: `no_data` (0–1 checkpoints), `establishing_baseline` (2–3 checkpoints), `computed` (4+ checkpoints).

## Scope Priority Derivation Mechanism

**Construct metadata.** `kind: Mechanism` · `tier: COMPOSITIONAL` · `standalone: false` · `governed-by: [AP8]`

The weighted-normalization convergence contract implements **AP8 — Fixpoint Calculus** (§62i).

The Scope Priority Derivation mechanism computes the normalized weight for each product scope at each assessment cycle. Weights drive which scope the lifecycle prioritizes for discovery and execution.

```
FOR EACH scope in [documentation, runtime, metrics, rebootstrap]:
  raw_weight = base_weight
             + (backlog * backlog_factor)
             + (unresolved_markers * marker_factor)
             + (days_since_accepted_change * staleness_factor)
  raw_weight = clamp(raw_weight, min_weight, max_weight)

  delta = raw_weight - previous_weight
  if |delta| > max_weight_step_per_revision:
    raw_weight = previous_weight + sign(delta) * max_weight_step_per_revision
    change_limited = true

total = sum(raw_weight for all scopes)
normalized_weight[scope] = raw_weight[scope] / total
```

**Normalization contract.** The sum of `normalized_weight` across all active scopes MUST equal 1.0 (±1e-9 floating-point tolerance). An implementation that fails this invariant MUST NOT use the unnormalized weights for scope selection and MUST surface the derivation as a named computation error.

**Monotonic revision contract.** `ScopePrioritySystem.revision` MUST be incremented on every recomputation, even if all weights are unchanged. This provides a monotonic change witness for audit purposes.

**Staleness factor contract.** `days_since_accepted_change` MUST be computed from the most recent `ACCEPTED` Change record for each scope in the Rule Ledger's `change_bindings`. If no ACCEPTED change exists for a scope, the scope MUST be treated as infinitely stale, clamped to the scope's `max_weight`.

## External Metric Collection Mechanism

**Construct metadata.** `kind: Mechanism` · `tier: COMPOSITIONAL` · `standalone: false` · `governed-by: [AP13]`

The structured observation, failure-streak tracking, and isolation contract implement **AP13 — Observer** (§62i).

The External Metric Collection mechanism gathers observations from configured external metric sources when the mode permits it.

```
MODE = ExternalMetricState.mode

IF mode == DISABLED:
  SKIP — no collection

IF mode == PROVIDED_ONLY:
  read from config.external_metrics.provided_sources only
  no public source discovery

IF mode == DISCOVER_PUBLIC_AND_USE_PROVIDED:
  discover public sources matching intent.purpose keywords
  union with provided_sources
  deduplicate by source URL/id

FOR EACH source:
  attempt collection
  IF success:
    append observation to ExternalMetricState.latest
    ExternalMetricState.last_known_good = latest observation
    ExternalMetricState.failure_streak = 0
  IF failure:
    append error to ExternalMetricState.errors
    increment ExternalMetricState.failure_streak
    emit Evidence(external-metric-collection-error)

ExternalMetricState.last_collection = now()
ExternalMetricState.next_collection_at = now() + collection_interval
```

**Error deduplication contract.** Identical consecutive collection errors (same source, same error kind) MUST NOT each produce a new Evidence record. The first occurrence MUST be recorded; subsequent identical consecutive errors MUST increment a counter and update `last_error_signature` without new Evidence until the error signature changes.

**Failure streak contract.** After three consecutive failures from a source, URACE MUST surface a named external-metric-unavailable condition and MUST NOT continue blocking Executor dispatch on that source's data. A lifecycle MUST NOT enter `BLOCKED` solely due to external metric collection failure.

**Isolation contract.** External metric collection MUST run in a separate Executor call from product Executor calls. A failure in external metric collection MUST NOT roll back or abort an in-progress product Operation.

**Discovery mechanism.** Public source discovery MUST proceed via the following ordered strategy: (1) check `Config.metric_sources.registry` for pre-configured source URLs matching the intent keywords; (2) if no registry match, attempt a search using `Config.metric_sources.search_endpoint` (if configured); (3) if no search endpoint, surface a WARNING gap of kind `metric-source-discovery-unavailable` and skip external collection for this cycle. The runtime MUST NOT attempt open-internet discovery without an explicit `search_endpoint` configured.

**Source validation.** Before using a discovered source, the runtime MUST: (a) verify the URL scheme is `https`; (b) attempt a HEAD request with 10-second timeout; (c) confirm the response Content-Type is JSON or CSV. A source that fails validation MUST be recorded with `status: INVALID` and excluded from the collection cycle.

**Deduplication.** Sources are deduplicated by normalized URL (scheme + host + path, query parameters stripped). If two discovered sources resolve to the same normalized URL, only one MUST be used. The deduplication key MUST be stored in the ExternalMetricSource record.

## Destination Anchor Integrity Mechanism

**Construct metadata.** `kind: Mechanism` · `tier: COMPOSITIONAL` · `standalone: false` · `governed-by: [AP35, OGP]`

The digest-based drift detection and operator-acknowledgement gate implement **AP35 — Governance Ledger** (§62i) and **OperatorGateProtocol** (§62l).

The Destination Anchor is verified on every lifecycle cycle start to detect unauthorized drift in governing intent.

```
ON LIFECYCLE CYCLE START:
  current_digest = SHA-256(
    JSON({"purpose": config.intent.purpose,
          "retained": sorted(config.intent.retained)},
         sort_keys=True, separators=(",", ":"))
  )

  IF current_digest == state.destination_anchor.digest:
    anchor VERIFIED — continue

  IF current_digest != state.destination_anchor.digest:
    emit Evidence(kind="governance-drift-detected",
                  before_digest=state.destination_anchor.digest,
                  current_digest=current_digest)
    enter BLOCKED state
    surface named condition: "governance-anchor-drift"
    MUST NOT dispatch any autonomous Operation
    MUST wait for operator acknowledgement
```

**Establishment contract.** `destination_anchor` MUST be established at bootstrap and MUST match the config at that point. A bootstrap that fails to write a `destination_anchor` MUST be treated as an integrity gap on first cycle start.

**Acknowledgement contract.** When `governance-anchor-drift` is active, the operator MUST explicitly acknowledge the change via an authenticated lifecycle command (`urace intent acknowledge-drift` or equivalent). The acknowledgement MUST update `destination_anchor` to the new digest and MUST be recorded as an Evidence record with the old and new digests. Autonomous inference of operator acceptance MUST NOT substitute for an explicit acknowledgement command.

**Immutability contract.** Once established, `destination_anchor` MUST NOT be updated by any autonomous operation other than the explicit acknowledgement path. A runtime that updates `destination_anchor` without an attributable operator command MUST be treated as a governance integrity failure.

## Self-Evolution Eligibility Gate Mechanism

**Construct metadata.** `kind: Mechanism` · `tier: INTEGRATED` · `standalone: false` · `governed-by: [AP34]`

This mechanism implements **AP34 — Self-Evolution Eligibility Gate** (§62i).

Every Executor proposal for a self-evolution or re-bootstrap Objective MUST pass through a deterministic policy gate before the proposal may be accepted as an Objective candidate. The gate reads the durable `self_evolution_policy` record and the ExecutorProposal fields; it MUST NOT consult the Executor again.

```
EXECUTOR PROPOSAL (ExecutorProposal)
  → read state.self_evolution_policy.mode

  IF mode == DISABLED:
    → record Evidence(kind="self-evolution-policy-decision",
                      outcome="INELIGIBLE", mode="DISABLED",
                      scope=proposal.scope, reason="policy disabled")
    → REJECT proposal; do not create Objective

  IF mode == NECESSARY_ONLY:
    → evaluate three gate fields:
        (a) proposal.self_evolution_necessary == true
        (b) proposal.necessity_evidence is non-empty
        (c) proposal.lower_impact_route_sufficient == false
    → if any gate field fails:
        record Evidence(kind="self-evolution-policy-decision",
                        outcome="INELIGIBLE", mode="NECESSARY_ONLY",
                        scope=proposal.scope,
                        reason=<first failing gate field>)
        REJECT proposal; do not create Objective
    → if all gate fields pass:
        record Evidence(kind="self-evolution-policy-decision",
                        outcome="ELIGIBLE", mode="NECESSARY_ONLY",
                        scope=proposal.scope)
        ACCEPT proposal → proceed to Authority Resolution

  IF mode == CONTINUOUS:
    → record Evidence(kind="self-evolution-policy-decision",
                      outcome="ELIGIBLE", mode="CONTINUOUS",
                      scope=proposal.scope)
    → ACCEPT proposal → proceed to Authority Resolution
```

**Durable record contract.** Every gate evaluation — ELIGIBLE or INELIGIBLE — MUST produce a durable `self-evolution-policy-decision` Evidence record before any downstream action is taken. An evaluation without a durable record is incomplete and MUST be treated as INELIGIBLE on recovery.

**Policy-source contract.** The gate MUST read the self-evolution policy exclusively from `state["self_evolution_policy"]`. A gate that consults Executor output, operational context, or the most recently observed mode to infer the policy violates §74.

**Recovery contract.** If `state["self_evolution_policy"]` is absent, corrupted, or structurally unreadable, the gate MUST apply `NECESSARY_ONLY` as the fail-closed default and MUST surface a named `self-evolution-policy-unreadable` IntegrityGap (WARNING). It MUST NOT proceed with `CONTINUOUS` mode under any form of inference.

**Gate-before-authority contract.** The eligibility gate MUST be evaluated before Authority Resolution (§62c Authority Resolution Mechanism). A proposal that fails the gate MUST NOT reach Authority Resolution; doing so would allow an ineligible proposal to be denied by authority rather than by policy, obscuring the actual blocking reason.

## OnboardGate Mechanism

**Construct metadata.** `kind: Mechanism` · `tier: FOUNDATIONAL` · `standalone: true` · `governed-by: [AP0, AP4, AP14]`

The OnboardGate is the one-time entry gate that every new Product MUST pass before URACE begins autonomous cycles. It fires once: when the current cycle finds no `OnboardRecord` for the active `Config.product`. Until all gates pass and the operator confirms, `lifecycle_state` is locked to `ONBOARDING` and no autonomous Operations, discovery calls, or executor dispatches are permitted. SD=True — no executor credits consumed.

```
ONBOARD GATE EVALUATION (fires at cycle entry when no OnboardRecord exists, SD=True)

  1. GATE: config-completeness
     Verify all REQUIRED Config top-level fields are present and non-empty:
       product, product_files (≥ 1 entry), state_path, intent.purpose,
       authority.delegated (≥ 1 entry), constraints, self_evolution_policy.mode
     PASS → continue  FAIL → emit onboard-config-incomplete(BLOCKING); surface missing fields

  2. GATE: product-files-readable
     For each path in Config.product_files: verify the file exists and is readable.
     PASS → continue  FAIL → emit onboard-no-readable-product-files(BLOCKING); list unreadable paths

  3. GATE: intent-anchored
     Verify State.destination_anchor is established (not null, not defaulted from empty intent).
     PASS → continue  FAIL → emit onboard-intent-unanchored(BLOCKING); instruct operator to set intent

  4. GATE: capability-envelope-declared
     Verify Config.capability_envelope is present (at least one declared capability), OR
     verify State.onboard_records[-1].capability_envelope_waived = true (explicit operator waiver).
     PASS → continue  FAIL → emit onboard-capability-envelope-missing(WARNING); non-blocking advisory

  5. GATE: self-evolution-policy-recorded
     Verify State.self_evolution_policy is present and mode is one of
     NECESSARY_ONLY | CONTINUOUS | DISABLED.
     PASS → continue  FAIL → default to NECESSARY_ONLY; emit Evidence(kind: "onboard-policy-defaulted")

  6. OPERATOR CONFIRMATION REQUIRED
     If gates 1–3 all pass: emit onboard-confirmation-pending(BLOCKING) gap and surface:
       "urace onboard status  — see gate results"
       "urace onboard confirm — confirm and begin autonomous cycles"
     Lifecycle remains ONBOARDING until operator issues `urace onboard confirm`.

  7. ON CONFIRM:
     Create OnboardRecord with all gate results, config_digest, confirmed_by, confirmed_at.
     Write first Checkpoint of kind ONBOARD_COMPLETE.
     Clear all onboard-* gaps.
     Set lifecycle_state = DORMANT.
     Emit Evidence(kind: "onboard-complete", product: Config.product).
```

**Idempotency contract.** If `urace onboard status` is called when an OnboardRecord already exists, it MUST report the existing record and gates without re-evaluating or mutating state.

**No-executor contract.** The OnboardGate MUST NOT invoke the Executor at any step. All gate checks are deterministic reads of Config and State. `SD=True` — locally computable.

**Product-agnostic contract.** The OnboardGate applies identically regardless of product type, language, domain, or file structure. It validates URACE configuration completeness, not product correctness. A product that has no files yet (empty `product_files`) MUST fail gate 2 and surface the gap; it is operator responsibility to configure the product before URACE begins cycling.

**Re-onboard contract.** Replacing `Config.product` with a different product name invalidates the prior OnboardRecord. URACE MUST detect the name mismatch at cycle entry, set `lifecycle_state = ONBOARDING`, and re-run the OnboardGate. This is the formal mechanism for Product switching (§r72).

**Referenced from:** §62o Product Onboard Phase (normative anchor), §59b maturity progression.

---

## Discovery Credit Gate Mechanism

**Construct metadata.** `kind: Mechanism` · `tier: COMPOSITIONAL` · `standalone: false` · `governed-by: [AP10, AP29]`

Before every discovery cycle that would invoke a metered or credit-accruing Executor, URACE MUST evaluate the Discovery Credit Gate. The gate is deterministic, executor-agnostic, and reads only durable state and configuration. It MUST NOT invoke an Executor to determine its own outcome. `gate_open ↔ calls_today < max_calls_per_day ∧ calls_month < max_calls_per_month` The systematic-failure cooldown (condition 1) implements AP10 — Bounded Retry with Backoff (§62i).

```
DISCOVERY CYCLE REQUEST
  → evaluate conditions in priority order:

  1. IF executor in systematic-failure cooldown:
       → set discovery_budget_status = SYSTEMATIC_FAILURE_COOLDOWN
       → set discovery_defer_reason = "systematic failure cooldown active until <retry_at>"
       → DEFER; do not invoke discovery

  2. IF rolling 24h call count ≥ configured daily ceiling OR below reserve floor:
       → set discovery_budget_status = DAILY_LIMIT_OR_RESERVE_REACHED
       → set discovery_defer_reason = "24h call ceiling or reserve reached"
       → DEFER

  3. IF rolling 30d call count ≥ configured monthly ceiling OR below reserve floor:
       → set discovery_budget_status = MONTHLY_LIMIT_OR_RESERVE_REACHED
       → set discovery_defer_reason = "30d call ceiling or reserve reached"
       → DEFER

  4. IF incoming trigger signature == last processed trigger signature:
       → set discovery_budget_status = DUPLICATE_TRIGGER_SUPPRESSED
       → set discovery_defer_reason = "duplicate trigger; no new context since last cycle"
       → DEFER; do not record IntegrityGap (not a fault condition)

  5. IF lifecycle state is BLOCKED:
       → set discovery_budget_status = DEFERRED_PROPORTIONALITY
       → set discovery_defer_reason = "lifecycle BLOCKED; discovered Objectives cannot
                                       proceed until unresolved effect is reconciled"
       → emit IntegrityGap(kind="discovery-proportionality-deferred",
                           severity=WARNING,
                           detail=discovery_defer_reason)
       → DEFER

  6. IF unproductive_discovery_streak ≥ configured exhausted threshold:
       → set discovery_budget_status = DISCOVERY_YIELD_EXHAUSTED
       → set discovery_defer_reason = "streak=<N> reached threshold=<T>; qualifying
                                       reset event required"
       → emit IntegrityGap(kind="discovery-yield-exhausted",
                           severity=WARNING,
                           detail=discovery_defer_reason)
       → surface qualifying_reset_conditions in inspection output
       → DEFER until qualifying reset event:
           (a) new authoritative inbox input consumed
           (b) net-new Evidence record added since streak began
           (c) change to governing Intent, product-file content, or Authority config
           (d) operator force-discovery invocation (bypasses gate for one cycle;
               does NOT reset streak; streak resets only on productive result)

  7. ELSE:
       → set discovery_budget_status = WITHIN_BUDGET
       → clear discovery_defer_reason
       → PROCEED with discovery cycle
```

**Durable-record contract.** The `discovery_budget_status` and `discovery_defer_reason` fields MUST be written to `ExecutorState` before any deferral takes effect. A deferral that does not produce a durable status record is incomplete and MUST be treated as unresolved on recovery.

**Proportionality-first contract.** A discovery cycle deferred by conditions 5 or 6 MUST emit a named `IntegrityGap` so that the blocking condition is visible in the inspection output. Conditions 1–4 are hard mechanical limits; they do not require an IntegrityGap.

**Budget-independence contract.** The proportionality gate (condition 5) and the yield-exhaustion gate (condition 6) operate independently of and prior to the hard-budget ceilings in conditions 2–3. Satisfying the hard budget alone does not satisfy the proportionality requirement; both must pass for discovery to proceed.

**Force-discovery contract.** An operator force-discovery invocation MUST be recorded as a durable attributed override event in `evidence`. It bypasses the yield-exhaustion gate (condition 6) for exactly one discovery cycle. The `unproductive_discovery_streak` counter MUST NOT be reset by the invocation; it resets only when the forced cycle produces a productive accepted result. If the force cycle produces no justified action, the streak increments normally.

**Streak-reset contract.** `unproductive_discovery_streak` MUST increment when a complete discovery cycle returns no justified action, an ineligible scope under current policy, or a transport failure. It MUST reset to 0 only when a discovery cycle produces at least one productive accepted result. Partial resets are not permitted.

## Quality Streak Mechanism

**Construct metadata.** `kind: Mechanism` · `tier: COMPOSITIONAL` · `standalone: false` · `governed-by: [AP9, AP20]`

The Quality Streak Mechanism is the positive counterpart to AP20 — Circuit Breaker (§62i): where AP20 tracks failure streaks and gates further execution, this mechanism tracks consecutive quality improvements and gates progressive autonomy expansion. It implements AP9 — Monotone Accumulator (§62i) over QualityDelta records (§62b).

```
QUALITY STREAK EVALUATION (per assessment cycle, SD=True — no executor credits)

  1. Read QualityStateEntry from State.quality_state for target scope
     (NOT from ExecutorState — quality state is a Product-level citizen):
       current_streak     int ≥ 0; consecutive IMPROVEMENT QualityDeltas in scope
       best_streak        int ≥ 0; highest streak ever achieved in scope
       streak_started_at  timestamp | null; when current streak began

  2. Read most recent QualityDelta for scope from State.quality_deltas:

     IF classification == IMPROVEMENT:
       → increment current_streak
       → update best_streak if current_streak > best_streak
       → update streak_started_at if current_streak was 0 before increment
       → write updated QualityStateEntry back to State.quality_state
       → record Evidence(kind="quality-streak-increment",
                         streak=current_streak, scope=scope)

     IF classification == REGRESSION:
       → reset current_streak = 0; streak_started_at = null
       → write updated QualityStateEntry back to State.quality_state
       → record Evidence(kind="quality-streak-reset",
                         reason="regression", scope=scope)
       → emit QualityStreakRegressionEvent to AP20 Circuit Breaker
         (see AP4 contract below; AP20 evaluates its own streak independently)

     IF classification == NEUTRAL:
       → no change to streak counters; write last_evaluated_at only

  3. IF current_streak ≥ configured autonomy_expansion_threshold AND
        applicable Authority permits scope weight expansion:
       → propose: increase ScopePriorityConfig.max_weight for scope by one bounded step
       → MUST pass Self-Evolution Eligibility Gate (§62c) if expansion modifies Config
       → record Evidence(kind="quality-streak-autonomy-proposal",
                         streak=current_streak, scope=scope)
```

**Immutability contract.** Streak counters MUST NOT be decremented except by REGRESSION reset. A NEUTRAL QualityDelta MUST NOT increment or reset the streak. **Independence contract.** Quality streak evaluation runs independently of AP20; AP20 governs failure recovery, this mechanism governs success-based expansion. Both MUST be evaluated on each cycle. **Cross-scope independence contract.** A REGRESSION in one scope MUST NOT reset another scope's streak. Streak state is per-scope. **Self-determination contract.** `SD(QualityStreakMechanism, S) = True`; this mechanism reads only enumerable durable state and MUST NOT consume executor credits. **State-location contract.** Quality streak state MUST reside in `State.quality_state` (list of `QualityStateEntry`), never in `ExecutorState`. ExecutorState is executor-operational; quality streak is Product-level and MUST survive executor replacement.

**AP4 Contract — QualityStreakRegression → CircuitBreaker.**
```
ProducerConsumerContract {
  name:                "QualityStreakRegression → CircuitBreaker"
  producer:            QualityStreakMechanism
  consumer:            AP20 Circuit Breaker
  artifact:            QualityDelta (classification = REGRESSION, durably written)
  producer_must:       write QualityDelta to State.quality_deltas before emitting event;
                       reset QualityStateEntry.current_streak = 0 before emitting event
  consumer_may_assume: QualityDelta record is durable and immutable on receipt;
                       QualityStateEntry for the scope reflects the reset
  violation_protocol:  ALERT (AP20 may have missed a regression signal)
  idempotent:          True (AP20 evaluates its own failure streak independently)
}
```

**Checkpoint gate contract.** When the most recent `QualityDelta` for a scope carries `classification = REGRESSION`, a Checkpoint acceptance for an Operation in that scope MUST be preceded by a durable `DecisionRecord` explicitly justifying the regression acceptance (reason MUST reference governing Intent and trade-off Evidence). A checkpoint attempt in a REGRESSION scope without such a `DecisionRecord` MUST remain `PENDING`, not `ACCEPTED`. This gate applies only when a QualityDelta for the scope exists; scopes with no quality history are unaffected.

## Re-Ingestion Mechanism

**Construct metadata.** `kind: Mechanism` · `tier: INTEGRATED` · `standalone: false` · `governed-by: [AP21]`

Formal contract for re-ingesting archived or compacted lifecycle data back into active state. Complements AP21 — Compaction (§62i) and §62f Compaction and Retention. Produces a ReIngestionRecord citizen (§62b).

```
RE-INGESTION REQUEST (operator-authorized, wraps Transaction Mechanism)

  1. Locate target CompactionSummary at requested position in target field
  2. Locate archive at CompactionSummary.archive_path
     IF archive not found:
       → ABORT; emit IntegrityGap(kind="reingestion-archive-missing", severity=BLOCKING)
  3. Compute SHA-256 of archived records
  4. Compare to CompactionSummary.original_digest:
     IF mismatch:
       → emit IntegrityGap(kind="reingestion-digest-mismatch", severity=BLOCKING)
       → ABORT; do not modify live field
  5. Open Transaction journal (PREPARED)
  6. Remove CompactionSummary from target position
  7. Insert original records at target position in original order (APPLYING → APPLIED)
  8. Write ReIngestionRecord to evidence log
  9. Advance Transaction to VALIDATED
```

**Atomicity contract.** Re-ingestion MUST be performed as a single lifecycle transaction (§62c Transaction Mechanism). A partial re-ingestion is a recovery condition; resume from the Transaction journal. **Field-order contract.** Restored records MUST occupy the exact position range originally compacted; relative ordering of neighboring live records MUST NOT change. **Policy contract.** Re-ingestion into a field with `compaction_mode: ROLLING_EVICTION` is PROHIBITED; such fields have no archive. **Authorization contract.** Re-ingestion MUST NOT be performed autonomously; it MUST be preceded by an attributable operator input. Uses canonical: ReIngestionRecord (§62b), CompactionSummary (§62b), Transaction Mechanism (§62c).

**CheckpointRecord baseline.** Re-ingestion MUST establish a baseline from the most recent CheckpointRecord (§62b) with `kind=accepted-product-change` in `State.checkpoints`. The baseline digest MUST be verified against `state_after_digest` of the corresponding Change binding. Re-ingestion that cannot establish this baseline MUST NOT proceed.

**Archive path resolution.** `CompactionSummary.archive_path` MUST be stored as a path relative to the URACE system root (`urace/`). On re-ingestion, the runtime MUST resolve it relative to the system root. If the resolved path does not exist, the runtime MUST search `Config.archive_search_paths` (if configured) before failing. If the archive cannot be located after searching all paths, a BLOCKING gap of kind `archive-not-found` MUST be surfaced.

**Re-ingestion idempotency.** Re-ingesting the same `compaction_event_id` twice MUST be idempotent: if the entries from that event are already present in the State Document, the re-ingestion MUST complete without duplication and emit an INFO gap of kind `reingestion-duplicate-skipped`. Idempotency MUST be enforced by checking for existing records with matching `source_compaction_event_id` before insertion.

## Staleness Detection Mechanism

**Construct metadata.** `kind: Mechanism` · `tier: COMPOSITIONAL` · `standalone: false` · `governed-by: [AP13]`

The three-domain scan and structured observation output implement **AP13 — Observer** (§62i).

A general-purpose self-determinable mechanism for detecting and surfacing stale data across the lifecycle. Complements derived-manifest stale detection (§62j) and PendingValidation expiry (§62b). `SD = True` — no executor credits consumed.

```
STALENESS SCAN (per assessment cycle, SD=True)

  DOMAIN: Decisions
    FOR EACH DecisionRecord WHERE status == CURRENT:
      scope        = DecisionRecord.scope if present, else "*"
      scope_window = config.staleness_windows.by_scope[scope]
                     IF present, ELSE config.staleness_windows.decision_seconds
      decision_age = now − decided_at
      IF decision_age > scope_window
         AND (Intent changed since decided_at
              OR Authority changed since decided_at
              OR basis_evidence_ids reference Evidence superseded since decided_at):
        → emit IntegrityGap(kind="stale-decision", severity=WARNING,
                            detail="DecisionRecord {id} scope={scope} age={age}; basis may have changed")
        → produce PendingValidation(
            id=pending_validations identifier,
            source_operation_id=DecisionRecord.id,
            kind="stale-decision-revalidation",
            blocked_on_capability="decision-revalidation",
            queued_at=now,
            stale_reason="decision_age exceeds staleness window for scope"
          )

  DOMAIN: Evidence
    FOR EACH Evidence WHERE kind IN [external-metric, market-signal, external-observation]:
      evidence_age = now − recorded_at
      IF evidence_age > evidence_freshness_window[kind]:
        → emit IntegrityGap(kind="stale-evidence", severity=WARNING,
                            detail="Evidence {id} kind={kind} age={age}")

  DOMAIN: Rules
    FOR EACH Rule WHERE status == ACTIVE AND supporting evidence count == 0:
      rule_age = now − created_at
      IF rule_age > rule_freshness_window:
        → emit IntegrityGap(kind="unsupported-rule", severity=WARNING,
                            detail="Rule {id} has no supporting Evidence in {age}d")

  DOMAIN: Metrics
    FOR EACH MetricDefinition WHERE authority == "DIRECTIVE":
      IF MetricDefinition.updated_at > MetricDefinition.seeded_at
         AND no attributable authority authorization recorded for mutation:
        → emit IntegrityGap(kind="metric-definition-drift", severity=WARNING,
                            detail="MetricDefinition {id} name={name} mutated without authority authorization")
```

**Proportionality contract.** Staleness detection is self-determinable (`SD = True`); it MUST NOT consume executor credits. **Non-blocking contract.** All staleness gaps are `WARNING` severity, never `BLOCKING`; they surface for operator attention but MUST NOT halt the lifecycle. **Configuration contract.** Freshness windows (`decision_freshness_window`, `evidence_freshness_window`, `rule_freshness_window`) MUST be declared in Config Document (`staleness_windows`) before the first staleness scan. Per-scope overrides MUST be declared under `staleness_windows.by_scope`; absent scopes fall back to the global `decision_seconds` window. Absent configuration MAY defer the domain scan and MUST NOT produce false positives.

**Default staleness windows.** Unless overridden in `Config.staleness` (§62e), the following defaults apply: decisions: 72 hours (`decisions_hours`); evidence: 168 hours (`evidence_hours`); rules: 720 hours (`rules_hours`); metrics: 168 hours (`metrics_hours`). The legacy `staleness_windows` field (values in seconds) is superseded by `Config.staleness` when both are present. A Config override MUST specify the window in integer hours ≥ 1.

**Authority-authorization recording for T2 adjustments.** When the T2 Bar-Raising Calculus (§62h) raises a threshold, the mechanism MUST record an Evidence entry of kind `threshold-adjustment-authorized` with fields: `adjusted_metric_id`, `old_threshold`, `new_threshold`, `authority_basis` (referencing the governing Authority record), `authorized_at`. This Evidence entry MUST be linked to the MetricDefinition via `last_baseline_audit`. A T2 threshold adjustment without a corresponding Evidence record MUST be surfaced as a WARNING gap of kind `unauthorized-threshold-adjustment`.

## Metric Baseline Verification

**Construct metadata.** kind: Mechanism · tier: COMPOSITIONAL · standalone: false · governed-by: [AP28, AP36]

Verifies that all active MetricDefinitions have not been mutated beyond their declared `mutation_requires` contract. Runs at cycle start, before any execution gate.

```
METRIC BASELINE VERIFICATION (cycle start, SD=True)

  DOMAIN: All MetricDefinitions
    FOR EACH MetricDefinition in State.metric_definitions:
      INVARIANT: If mutation_requires=IMMUTABLE AND updated_at > seeded_at
        → emit IntegrityGap(kind="metric-baseline-unauthorized-mutation", severity=BLOCKING,
                            detail="MetricDefinition {id} with mutation_requires=IMMUTABLE was modified after seeded_at")
      INVARIANT: If mutation_requires=PERMISSION AND no active PERMISSION rule for metric id in Rule Ledger
        → emit IntegrityGap(kind="metric-mutation-policy-missing", severity=WARNING,
                            detail="MetricDefinition {id} with mutation_requires=PERMISSION has no active PERMISSION rule")
      INVARIANT: If last_baseline_audit + 86400 < now()
        → update last_baseline_audit = now(); emit no gap (routine maintenance)
```

**Used in:** §62b Bootstrap Seeding (seeded_at initialization), §62f RetentionPolicy (metric records exempt from ROLLING_EVICTION)

## Context Budget Mechanism

**Construct metadata.** `kind: Mechanism` · `tier: COMPOSITIONAL` · `standalone: false` · `governed-by: [AP24]`

Governs the sweet-spot between context input richness and executor context window capacity. Prevents silent degradation when accumulated context approaches executor caps. Implements the Context Budget Contract for executor delegations.

```
CONTEXT BUDGET EVALUATION (before each executor delegation, SD=True)

  1. Estimate token count of current context payload:
       sources: active ContextInput list, recent Evidence subset,
                current Plan, active Objective set, active Rules
  2. Read from Config.context_budget:
       target_utilization      float 0.0–1.0; desired fraction of executor cap (default 0.70)
       hard_cap_fraction       float 0.0–1.0; absolute maximum fraction (default 0.90)
       executor_context_cap    int; declared token capacity of target executor class

  3. IF estimated_tokens > hard_cap_fraction * executor_context_cap:
       → GRACEFUL DEGRADATION:
           (a) evict oldest ContextInput entries (oldest first) until within hard_cap_fraction
           (a') Eviction priority order (AP24 tier): INTEGRATED-class ContextInput
                entries MUST be evicted first, then COMPOSITIONAL, then
                FOUNDATIONAL last. This preserves minimum viable reasoning
                context under budget pressure.
           (b) replace evicted payload with summary token (CompactionSummary-equivalent)
           (c) record Evidence(kind="context-budget-degraded",
                               evicted_count=N, remaining_count=M, cap=executor_context_cap)
       → MUST NOT exceed hard_cap_fraction under any circumstance

  4. IF estimated_tokens > target_utilization * executor_context_cap:
       → emit IntegrityGap(kind="context-budget-advisory", severity=INFO,
                           detail="context at {pct}% of cap; approaching target_utilization")

  5. PROCEED with delegation at current context size
```

**Executor-agnostic contract.** `executor_context_cap` MUST be declared per executor class in Config.context_budget; it MUST NOT be hard-coded in the spec or runtime. **Graceful-degradation-first contract.** The mechanism MUST prefer graceful eviction with summary over hard rejection. Hard rejection is the last resort, applied only when graceful degradation cannot fit within `hard_cap_fraction`. **Reversibility contract.** Evicted ContextInput entries MUST still appear in the Evidence log; they are excluded from the delegation payload, not deleted from State. **SD contract.** Token estimation and budget comparison are locally computable; this mechanism is `SD = True` and MUST NOT delegate to an executor to evaluate its own outcome. **Capability-class priority contract.** When evicting ContextInput entries under budget pressure, INTEGRATED-class entries MUST be evicted before COMPOSITIONAL, and COMPOSITIONAL before FOUNDATIONAL. An eviction that removes a FOUNDATIONAL-class entry while INTEGRATED-class entries remain is a priority inversion and MUST surface as an IntegrityGap(kind="context-budget-priority-inversion", severity=WARNING).

**Tier tie-breaking.** Within a single eviction tier, entries MUST be evicted in ascending order of `last_accessed_at` (least recently accessed first). When `last_accessed_at` is equal, entries MUST be evicted in ascending order of estimated token size (smallest last). A tie-breaking sort MUST be applied before any eviction within a tier.

**Eviction floor.** Eviction MUST stop when the remaining context size is ≤ `Config.context_budget_r58.min_floor_fraction` of the hard cap (default: 0.10). The runtime MUST NOT evict below this floor even if the CRC remains over budget. If the floor is reached and the CRC is still over budget, a BLOCKING gap of kind `crc-context-overflow` MUST be surfaced.

**Fallback-rejection contract.** If eviction cannot bring context within budget because all evictable entries have been exhausted above the floor, the runtime MUST reject the pending Executor invocation, surface the `crc-context-overflow` gap, and wait for operator intervention rather than proceeding with an oversized context.

---

## Wake Registration Verification Mechanism

**Construct metadata.** `kind: Mechanism` · `tier: COMPOSITIONAL` · `standalone: false` · `governed-by: [AP29, WRV]`

This mechanism implements **WakeRegistrationVerification** (§62l) and **AP29 — Dormancy/Wakeability Contract** (§62i). Verifies that durable wake registrations recorded in `State.wake_registry` are still active in the current environment on lifecycle restart. Implements §67 restart verification requirement. `SD = True` — no executor credits consumed.

```
WAKE REGISTRATION VERIFICATION (on lifecycle restart)

  FOR EACH WakeRegistration in State.wake_registry:
    1. Attempt to confirm the registration is still active in the current environment
       (e.g. check that the scheduled trigger or file-system watcher still exists).
    2. IF registration cannot be verified as active:
         → emit IntegrityGap(kind="wake-integrity-gap", severity=WARNING,
                             detail="WakeRegistration {id} cannot be verified as active")
         → attempt re-establishment if authorized and technically feasible
         → IF re-establishment fails: retain IntegrityGap in lifecycle inspection output
    3. IF registration is verified active:
         → set WakeRegistration.verified_at = now()
```

**Registration contract.** Every WakeRegistration MUST carry: `id` (Identifier), `kind` (str), `scheduled_at` (timestamp), `condition` (str describing the lifecycle condition it observes). **Verification contract.** On restart, every entry in `wake_registry` MUST be verified. An entry that cannot be verified MUST surface a named `wake-integrity-gap`. URACE MUST NOT represent dormancy as durably wakeable when any entry carries an unresolved wake-integrity-gap. `SD = True` — verification reads only local environment state.

**Signal taxonomy.** Authoritative liveness signals are classified as: (1) `SCHEDULED` — OS-level cron/scheduler entry; (2) `FILESYSTEM` — file-watcher or inotify hook; (3) `NETWORK` — HTTP health endpoint; (4) `MANUAL` — operator-confirmed active; (5) `COMMUNITY_INBOX` — new CommunitySignal or PatchProposal event crossing a threshold. A `COMMUNITY_INBOX` wake trigger MUST be registered when `Config.community_inbox` is configured and at least one CommunityFeed has `active = true`. The trigger fires when: (a) a CommunitySignal with `signal_quality ∈ {HIGH, MEDIUM}` arrives and no active Operation is in progress; (b) a PatchProposal in HUMAN mode has been PENDING for longer than `proposal_expiry_hours / 4` without operator action (reminder trigger). A `COMMUNITY_INBOX` wake signal MUST NOT be fired more frequently than `Config.community_inbox.feeds[].polling_interval_seconds` of the fastest active feed. At least one signal of any class MUST be present for a WakeRegistration to be considered active. If no signal is detectable, the registration MUST be surfaced as `status: STALE`.

**Timeout contract.** A liveness confirmation attempt MUST time out after 30 seconds. If the signal does not respond within 30 seconds, the attempt MUST be recorded as failed. After 3 consecutive failed attempts (across separate wake cycles), the registration MUST be set to `status: STALE` and a WARNING gap of kind `wake-registration-stale` MUST be surfaced.

**Re-establishment authorization.** A STALE WakeRegistration MAY be re-established only by an operator-issued command (not by the runtime autonomously). Re-establishment MUST create a new WakeRegistration record with a fresh `established_at` and `signal_class`, referencing the stale registration's `id` in a `replaces` field. The stale record MUST be retained with `status: SUPERSEDED`.

**Recoverable vs. terminal gaps.** A `wake-registration-stale` gap is recoverable via operator re-establishment. A registration that has been STALE for more than `Config.wake.max_stale_hours` (default: 168) without re-establishment MUST be escalated to a BLOCKING gap of kind `wake-registration-expired`, halting all scheduled autonomous Operations.

## Community Signal Ingestion Mechanism (CSI)

**Construct metadata.** `kind: Mechanism` · `tier: INTEGRATED` · `standalone: false` · `governed-by: [AP38, AP14]`

The Community Signal Ingestion Mechanism ingests signals from all active `CommunityFeed` sources, scores them for relevance and confidence, and routes quality-passing signals to the Patch Proposal Pipeline Mechanism. This mechanism implements the feed-adapter abstraction and T&C gate contract from AP38.

**Feed ingestion contract.** For each enabled `CommunityFeed` (active=true) in `Config.community_inbox.feeds`, the CSI MUST poll or receive signals at intervals appropriate to the `FeedAdapterKind`. Before processing any signal from a feed, CSI MUST verify `CommunityFeed.terms_accepted = true`; if false, CSI MUST surface `community-feed-terms-not-accepted` BLOCKING gap and MUST NOT ingest signals from that feed. If the adapter cannot connect to the endpoint, CSI MUST emit `community-feed-adapter-unavailable` WARNING gap and skip that feed for the current cycle.

**Signal creation contract.** Each raw inbound signal MUST be stored as a `CommunitySignal` record immediately on receipt, before scoring. The record MUST set `filtered = false` until scoring determines otherwise. `received_at` MUST be set to the ingestion timestamp, not the signal's original timestamp.

**Relevance scoring contract.** `relevance_score` MUST be computed by the Executor as the semantic overlap between the signal content and the union of: (a) the current active Objectives' descriptions, (b) `Config.intent.purpose`, and (c) the Product name. The score MUST be a float in [0.0, 1.0]. A signal with `relevance_score < Config.community_inbox.relevance_floor` MUST have `filtered = true` set and `filter_reason` populated; CSI MUST emit `community-signal-relevance-below-floor` INFO gap and MUST NOT pass the signal to PPP_M.

**Confidence scoring contract.** `confidence_score` MUST be computed by the Executor based on corroboration evidence: (a) a single uncorroborated signal from one feed MUST receive `confidence_score = 0.5`; (b) each additional independent corroborating signal on the same topic from a different feed or source MUST increase the score by a bounded delta toward 1.0; (c) contradicting signals MUST decrease the score toward 0.0. The scoring MUST use a bounded accumulator: score MUST remain in [0.0, 1.0] regardless of signal count. The Executor MAY use any scoring algorithm consistent with these boundary semantics.

**Timeout and retry contract.** Each feed adapter connection MUST apply `CommunityFeed.adapter_timeout_seconds` (default 30s) as the read/connection timeout. If the adapter does not return within the timeout, the attempt counts as a failure. After `CommunityFeed.adapter_retry_count` (default 3) consecutive failures, CSI MUST surface `community-feed-adapter-unavailable` WARNING gap for that feed and MUST skip it for the remainder of the current ingestion cycle. The retry counter MUST reset when a successful connection is established on any subsequent cycle.

**Polling cadence contract.** For `FeedAdapterKind.RSS` and `FeedAdapterKind.POLLING` feeds, CSI MUST NOT poll more frequently than `CommunityFeed.polling_interval_seconds` (default 300s). The cadence MUST be evaluated at the assessment cycle boundary; if less than `polling_interval_seconds` has elapsed since the last successful poll for a feed, that feed MUST be skipped in the current cycle. `FeedAdapterKind.WEBHOOK` and `FeedAdapterKind.PUSH` are event-driven; CSI MUST NOT apply a polling interval to them.

**Lifecycle state gate contract.** CSI MUST NOT ingest signals when `lifecycle_state ∈ {BLOCKED, PAUSED, RECONCILING}`. CSI MAY run during `ACTIVE`, `ASSESSING`, and `DORMANT` (if a wake trigger fires). CSI MUST suspend ingestion during `WAITING_FOR_CAPACITY` if `executor_credit_priority = INBOX_LOW` and a discovery or evolution Operation is queued. Lifecycle state is checked once per ingestion cycle at the cycle start boundary; a state transition mid-cycle MUST NOT interrupt an in-progress feed read.

**Executor credit contract.** CSI relevance scoring and PPP_M patch synthesis MUST be credited against the lifecycle's `executor_calls` budget. These calls are scheduled at priority `Config.community_inbox.executor_credit_priority` (default INBOX_NORMAL). If `DiscoveryBudgetStatus ∈ {DAILY_LIMIT_OR_RESERVE_REACHED}` and `executor_credit_priority = INBOX_LOW`, CSI MUST defer all adapter poll-and-score operations until the next assessment cycle when budget is available. At `INBOX_NORMAL`, CSI MAY run concurrently with discovery within the available budget. At `INBOX_HIGH`, CSI calls are prioritized over discovery calls but remain subordinate to `REPAIRING` and `RECONCILING` lifecycle obligations.

**Confidence score bounded delta formula.** The confidence score for a CommunitySignal is accumulated as follows: (a) initial score for a single-source signal = 0.50; (b) each additional corroborating signal from an independent source (different `CommunityFeed.id`) MUST add a delta of `min(0.15, (1.0 - current_score) * 0.5)` — a bounded additive step that prevents overshooting 1.0; (c) each contradicting signal from an independent source MUST subtract a delta of `min(0.10, (current_score - 0.0) * 0.5)` — a bounded subtractive step; (d) additional signals from the same `CommunityFeed.id` as a prior corroborating signal MUST contribute only `0.05` delta to prevent single-feed inflation; (e) the score MUST be clamped to [0.0, 1.0] after each update. Two signals are "independent" if their `CommunityFeed.id` values differ.

**Filtered signal lifecycle.** A CommunitySignal with `filtered = true` MUST be retained in `State.community_signals` with its `filter_reason` populated. Filtered signals MUST NOT be deleted or purged during retention evaluation; they MUST be exempt from `Config.retention` eviction. If `Config.intent.purpose` or the active Objectives change materially (as detected at the next assessment cycle), CSI MUST re-score all filtered signals from the current cycle window (signals with `received_at` within the last `Config.community_inbox.proposal_expiry_hours`) and update their `relevance_score` and `signal_quality`. A previously filtered signal that now passes `relevance_floor` MUST have `filtered` set to `false` and MUST be passed to PPP_M.

**T&C gap clearance contract.** The `community-feed-terms-not-accepted` BLOCKING gap is `auto_clearable: true` — it is automatically cleared when the operator sets `CommunityFeed.terms_accepted = true` for the feed via an authorized input. Signals received from a feed while `terms_accepted = false` MUST be discarded (not stored). If `terms_accepted` is set to `false` after prior ingestion, prior CommunitySignal records from that feed MUST be retained (already ingested) but no new signals MUST be ingested until `terms_accepted` is restored to `true`.

**SD contract.** `SD(CommunitySignalIngestionMechanism, S) = False` — signal ingestion and relevance/confidence scoring require Executor invocation.

Uses canonical: CommunityFeed (§62b), CommunitySignal (§62b), Config.community_inbox (§62e).

## Patch Proposal Pipeline Mechanism (PPP_M)

**Construct metadata.** `kind: Mechanism` · `tier: INTEGRATED` · `standalone: false` · `governed-by: [AP38, AP4]`

The Patch Proposal Pipeline Mechanism receives quality-passing CommunitySignals from CSI, synthesizes patch candidates, and routes them through the approval pipeline. PPP_M implements the approval mode contract from AP38.

**Patch synthesis contract.** For each CommunitySignal with `filtered = false` and `confidence_score ≥ Config.community_inbox.confidence_threshold`, PPP_M MUST invoke the Executor to synthesize a `proposed_diff` and `rationale`. The `target` field MUST be set to `"URACE"` when the proposal concerns the URACE spec or system, or to the Product name otherwise. The Executor MUST NOT be invoked for signals with `confidence_score < confidence_threshold`; such signals MUST produce a PatchProposal with `status = CONFIDENCE_INSUFFICIENT` and `patch-proposal-confidence-below-floor` INFO gap surfaced.

**Queue overflow contract.** Before creating a new PatchProposal, PPP_M MUST count active proposals (status ∈ {PENDING, CONFIDENCE_INSUFFICIENT}). If this count equals `Config.community_inbox.max_queue_depth`, PPP_M MUST surface `patch-proposal-queue-overflow` WARNING gap and MUST NOT create additional proposals until the queue drains below max_queue_depth.

**Approval routing contract.**
- `AUTO` mode: if `confidence_score ≥ 0.80`, PPP_M MAY set `status = AUTO_APPROVED` and `resolved_by = "auto"` without operator input. If `confidence_score < 0.80`, routing falls through to SMART evaluation.
- `SMART` mode: PPP_M MUST surface the proposal to the operator with `confidence_score`, `signal_quality`, and `rationale`. If `signal_quality = LOW` or `signal_quality = FILTERED`, PPP_M MAY autonomously set `status = REJECTED` with `rejection_reason`. For HIGH and MEDIUM quality proposals, operator confirmation MUST be required; `status = APPROVED` MUST NOT be set without an attributable operator input in SMART mode.
- `HUMAN` mode: `status = APPROVED` MUST require an attributable operator input for every proposal, regardless of `confidence_score`. `status = AUTO_APPROVED` is PROHIBITED in HUMAN mode.

**Expiry contract.** PPP_M MUST evaluate expiry at each assessment cycle. Any PatchProposal with `status ∈ {PENDING, CONFIDENCE_INSUFFICIENT}` and `created_at` older than `Config.community_inbox.proposal_expiry_hours` MUST transition to `status = EXPIRED` with `resolved_at` set to the evaluation timestamp and `resolved_by = "expiry"`.

**Application contract.** An APPROVED or AUTO_APPROVED PatchProposal targeting `"URACE"` MUST comply with `Config.self_evolution_policy`; if self_evolution_policy.mode = DISABLED, the proposal MUST be surfaced as a WARNING and MUST NOT be applied. A PatchProposal targeting the Product is an ordinary authorized Operation subject to applicable Authority.

**Queue overflow eviction strategy.** When the proposal queue reaches `max_queue_depth`, PPP_M MUST apply the following eviction order before surfacing `patch-proposal-queue-overflow` WARNING: (1) expire all CONFIDENCE_INSUFFICIENT proposals older than `proposal_expiry_hours / 2`; (2) if queue is still full, expire the oldest CONFIDENCE_INSUFFICIENT proposal (by `created_at`); (3) if queue is still full and no CONFIDENCE_INSUFFICIENT proposals exist, refuse to create new proposals and surface the WARNING gap without evicting PENDING proposals. Auto-evicted proposals MUST have `status = EXPIRED`, `resolved_at` set to the evaluation timestamp, and `resolved_by = "queue-overflow-eviction"`.

**Self-evolution DISABLED path.** When `target = "URACE"` and `Config.self_evolution_policy.mode = DISABLED`, PPP_M MUST NOT set `status = AUTO_APPROVED` or `status = APPROVED`. The proposal MUST remain `status = PENDING` and PPP_M MUST surface `community-inbox-evolution-blocked` WARNING gap with `detail = proposal_id`. The proposal MAY be applied only if an authorized operator input explicitly changes `self_evolution_policy.mode` to `NECESSARY_ONLY` or `CONTINUOUS` and then re-evaluates the proposal, OR if the operator uses `urace /inbox apply <proposal_id> --override-evolution-policy` (which MUST create an `evolution-policy-override-by-inbox` Evidence record). A proposal in PENDING state due to DISABLED evolution policy MUST be explicitly rejected by the operator if they choose not to enable self-evolution; it MUST NOT be auto-expired solely by this condition (normal `proposal_expiry_hours` still applies).

**HUMAN mode approval command.** In HUMAN mode, the operator MUST use `urace /inbox apply <proposal_id>` to approve a PatchProposal. This command MUST set `status = APPROVED`, `resolved_by = <operator_input_id>`, and `resolved_at = now`. An attempt to approve a proposal with `confidence_score < Config.community_inbox.confidence_threshold` in HUMAN mode MUST surface a WARNING in the command output (not a gap) and MUST proceed only if `--force` is passed. `urace /inbox list` lists all active proposals with their status, confidence_score, signal_quality, and target. `urace /inbox reject <proposal_id> [--reason <text>]` rejects a proposal.

**SD contract.** `SD(PatchProposalPipelineMechanism, S) = False` — patch synthesis requires Executor invocation.

Uses canonical: CommunitySignal (§62b), PatchProposal (§62b), ApprovalMode (§62b), Config.community_inbox (§62e).

## Sweet Spot Evaluation Mechanism

**Construct metadata.** `kind: Mechanism` · `tier: INTEGRATED` · `standalone: false` · `governed-by: [AP25]`

This mechanism implements **AP25 — Bounded Evolution Band** (§62i).

Assesses the Product's current maturity position on the capable evolution curve. Runs each assessment cycle. `SD = True` — no executor credits consumed. Produces a SweetSpotAssessment citizen and a ValueDensityRecord.

```
SWEET SPOT EVALUATION (per assessment cycle, SD=True)

  1. Read Config.capability_envelope (if absent: skip, maturity_level = BOOTSTRAPPING)
  2. Read State.capability_states → list[CapabilityEnvelopeEntry]
     Compute:
       capability_completeness = count(entries WHERE status == CAPABLE) / total_declared_caps
       weighted_completeness   = sum(cap.value_weight × entry.completeness_fraction)
                                 for each (cap, entry) pair

  3. Estimate product_surface_measure:
       count lines in config.product_files (or use stored document_metrics if available)

  4. Compute value_density = weighted_completeness / max(product_surface_measure, 1)
     (normalized; or use configured surface_unit if declared)

  5. Resolve ProductMaturityLevel:
       IF total_declared_caps == 0:
         maturity_level = BOOTSTRAPPING
       ELIF capability_completeness < Config.capability_envelope.completeness_target:
         maturity_level = FORMING
       ELIF capability_completeness >= completeness_target
            AND (complexity_ceiling absent OR surface_measure <= ceiling)
            AND (value_density_floor absent OR value_density >= floor):
         IF value_density > best_observed_value_density (from history):
           maturity_level = OPTIMIZED
         ELSE:
           maturity_level = CAPABLE
       ELIF surface_measure > complexity_ceiling (if declared):
         maturity_level = OVER_ENGINEERED
       ELSE:
         maturity_level = CAPABLE

  6. Evaluate active ProductMilestone (if Config.capability_envelope.milestones not empty):
       Find milestone WHERE status == ACTIVE
       Check all milestone gates simultaneously:
         - all capability_gates have CAPABLE status in State.capability_states
         - all quality_gates satisfied in State.quality_state
         - surface_measure <= milestone.complexity_ceiling (if declared)
         - value_density >= milestone.value_density_floor (if declared)
       IF all gates pass:
         → set milestone.status = ACHIEVED; milestone.achieved_at = now()
         → record Evidence(kind="milestone-achieved", milestone_id=milestone.id)

  6a. IF milestone was just achieved (gates all passed):
        → create ProductVersion:
            id = <new id with prefix "pver-">,
            version = active_milestone.version,
            milestone_id = active_milestone.id,
            achieved_at = now(),
            maturity_level = maturity_level,
            capability_completeness = capability_completeness,
            value_density = value_density,
            product_surface_measure = surface,
            next_milestone_id = active_milestone.next_milestone_id (if set)
        → append to State.product_versions
        → emit Evidence(kind="product-version-released",
                        version=active_milestone.version,
                        milestone_id=active_milestone.id)

  6b. IF active_milestone.next_milestone_id is set:
        → find milestone in Config.capability_envelope.milestones with that id
        → IF found AND status == PENDING: transition to ACTIVE
        → IF found AND status == ACHIEVED: skip (already done)
        → IF not found: emit IntegrityGap(kind="milestone-chain-broken", severity=WARNING)

  6c. Test Coverage Gate check:
        FOR EACH declared capability with status CAPABLE in State.capability_states:
          IF capability declares test_criteria:
            check State.test_run_records for any record WHERE:
              verdict == PASS AND capability.id IN capability_ids_covered
              AND kind IN {CAPABILITY_GATE, ACCEPTANCE}
            IF none found:
              → emit IntegrityGap(kind="capability-without-test-coverage", severity=WARNING,
                                  detail="CapabilityStatement {id} is CAPABLE but has no passing TestRunRecord")

  7. Write SweetSpotAssessment to State.sweet_spot_assessments
  8. Write ValueDensityRecord to State.value_density_history
  9. IF maturity_level == OVER_ENGINEERED:
       → emit IntegrityGap(kind="over-engineered", severity=WARNING,
                           detail="Product surface exceeds capability_envelope ceiling")
```

**Assessment contract.** Every assessment cycle MUST produce exactly one SweetSpotAssessment. A cycle that skips this mechanism MUST record the skip reason. **SD contract.** `SD(SweetSpotEvaluationMechanism, S) = True` — locally computable. **Milestone idempotency.** An ACHIEVED milestone MUST NOT be re-evaluated to ACTIVE; re-evaluation of an ACHIEVED milestone is a no-op unless a capability regression invalidates a gate.

**Surface measure algorithm.** `product_surface_measure` is computed as: count all non-blank, non-comment lines across all files matching `Config.product_files` globs. A line is blank if it contains only whitespace. A line is a comment if its first non-whitespace character sequence matches a language-appropriate comment prefix for that file extension (e.g. `#`, `//`, `--`, `%`). Generated files MUST be excluded: a file is generated if it contains a header comment matching the pattern `auto-generated|do not edit|code generated` (case-insensitive) within its first 5 lines, or if its path matches a glob in `Config.generated_file_globs`. The computed measure MUST be stored in the State Document after each Sweet Spot evaluation.

**Value-density floor enforcement.** If `value_density` falls below `Config.sweet_spot.value_density_floor` (default: 0.30), the mechanism MUST: (1) surface a WARNING gap of kind `value-density-below-floor`; (2) set an Objective recommendation for refactoring or scope reduction; (3) NOT block current Operations but include the recommendation in the next `/vitals` output. The floor is a soft threshold: crossing it triggers a recommendation, not a halt.

## Capability Envelope Gate Mechanism

**Construct metadata.** `kind: Mechanism` · `tier: INTEGRATED` · `standalone: false` · `governed-by: [AP25, AP33]`

This mechanism implements **AP25 — Bounded Evolution Band** (§62i) and **AP33 — Policy Enforcement Gate** (§62i).

Gates changes that would increase product surface measure beyond the configured complexity ceiling while the Product is already at CAPABLE or OPTIMIZED maturity. Operates as an additive pre-acceptance gate.

```
CAPABILITY ENVELOPE GATE (before each accepted-product-change, SD=True)

  1. IF Config.capability_envelope absent: PASS (gate inactive)
  2. Read current maturity_level from latest SweetSpotAssessment
     IF maturity_level NOT IN {CAPABLE, OPTIMIZED}: PASS (gate only active at/beyond capable)
  3. IF Config.capability_envelope.complexity_ceiling absent: PASS
  4. Estimate post-change surface_measure
     IF post_change_surface > complexity_ceiling:
       → Check for DecisionRecord(kind=CAPABILITY_SCOPE_EXPANSION, scope matches operation scope,
                                  decided_at >= operation.created_at)
         IF absent:
           → emit IntegrityGap(kind="capability-envelope-breach", severity=WARNING,
                               detail="change increases surface beyond ceiling at CAPABLE maturity")
           → PENDING (do not ACCEPT)
         IF present:
           → PASS (authorized expansion)
     ELSE: PASS
```

**Additive contract.** This gate fires ONLY when: (a) a capability_envelope is configured; (b) the Product is currently CAPABLE or OPTIMIZED; (c) the proposed change increases surface beyond the ceiling. It MUST NOT block COMPLEXITY_REDUCING changes. **Non-blocking for unconfigured products.** A Product with no declared capability_envelope is unaffected by this gate. Uses: SweetSpotAssessment (maturity_level), DecisionRecord (CAPABILITY_SCOPE_EXPANSION), Config.capability_envelope.

## Test Coverage Gate Mechanism

**Construct metadata.** `kind: Mechanism` · `tier: COMPOSITIONAL` · `standalone: false` · `governed-by: [AP9]`

The monotone test-count baseline implements **AP9 — Monotone Accumulator** (§62i).

Enforces that every capability marked CAPABLE in State.capability_states is backed by at least one passing TestRunRecord of kind CAPABILITY_GATE or ACCEPTANCE. `SD = True` — reads only local state.

```
TEST COVERAGE GATE (per assessment cycle, SD=True)

  FOR EACH CapabilityEnvelopeEntry WHERE status IN {CAPABLE, OVER_ENGINEERED}:
    1. Resolve the associated CapabilityStatement (by capability_id)
    2. IF CapabilityStatement.test_criteria is absent or null: SKIP (untested capability; gap surfaced separately)
    3. Search State.test_run_records WHERE:
         verdict == PASS
         AND capability_id IN record.capability_ids_covered
         AND record.kind IN {CAPABILITY_GATE, ACCEPTANCE}
    4. IF no such record found:
         → emit IntegrityGap(kind="capability-without-test-coverage", severity=WARNING,
                             detail="Capability {id} claims CAPABLE but no passing TestRunRecord covers it")
    5. IF found: PASS
```

**Coverage contract.** A capability with declared test_criteria that has no passing TestRunRecord is an unverified claim. URACE MUST surface this as a WARNING; it MUST NOT autonomously mark it CAPABLE on the basis of assertion alone. **Non-blocking contract.** This gate emits WARNING severity only; it does not block lifecycle progress. It is informational, driving the operator to add test coverage. **SD contract.** `SD(TestCoverageGate, S) = True` — all inputs are locally computable.

**Capability regression contract.** A capability that was previously CAPABLE MUST be downgraded to PARTIAL if: (a) a previously passing test for that capability now fails; or (b) a code path annotated as implementing that capability is deleted without a replacement. A PARTIAL capability MUST be surfaced in `/check` output with the specific test or annotation that triggered the downgrade. A capability that regresses from CAPABLE to PARTIAL during an autonomous cycle MUST cause the current cycle to emit a WARNING gap of kind `capability-regression`.

**Re-test trigger.** After any Operation that modifies code matching a capability's annotated paths, the Test Coverage Gate MUST re-evaluate that capability in the same cycle before closing. Re-evaluation uses the same test suite but scoped to the affected capability.

**Test freshness window.** A test result is considered fresh for `Config.test_coverage.freshness_hours` hours (default: 24). Test results older than the freshness window MUST NOT be used to assert CAPABLE status; the capability MUST be re-evaluated or downgraded to UNKNOWN until a fresh result is available.

## Crash-Consistent Acceptance

**Construct metadata.** `kind: Mechanism` · `tier: COMPOSITIONAL` · `standalone: false` · `governed-by: [AP27]`

Defined in §53. The four-phase acceptance boundary (PREPARED→APPLYING→APPLIED→VALIDATED→ACCEPTED) implements **AP27 — Transaction Recovery Protocol** (§62i). See §53 for the complete normative definition.

## Last-Known-Stable Product Recovery

**Construct metadata.** `kind: Mechanism` · `tier: COMPOSITIONAL` · `standalone: false` · `governed-by: [AP22]`

Defined in §53. The stable-fallback promotion and restoration contract implements **AP22 — Checkpoint** (§62i). See §53 for the complete normative definition.

---

## SignalClassifier

**Construct metadata.** `kind: Mechanism` · `tier: FOUNDATIONAL` · `standalone: false` · `governed-by: [AP26]`

The SignalClassifier maps observed lifecycle conditions to IntegritySignal records (§62b). It is the single canonical point at which raw lifecycle events become typed, severity-tagged IntegritySignals.

**Classification table:**

| Observed condition | signal_type | severity |
|---|---|---|
| Acceptance validation failure | VALIDATION_FAILURE | BLOCKING |
| Self-consistency check failure | CONSISTENCY_CHECK | BLOCKING |
| Failed activation health check | ACTIVATION_HEALTH | BLOCKING |
| Progress stagnation (cycle count reached stagnation_threshold) | STAGNATION | WARNING |
| Construct dependency cycle detected | DEPENDENCY_CYCLE | BLOCKING |
| Evidence provenance undeclarable | PROVENANCE_UNDECLARABLE | WARNING |
| All other conditions | OTHER | WARNING |

**Classification contract.** When an observed condition matches a row in the table, the runtime MUST create an IntegritySignal record with the mapped `signal_type` and `severity`. A condition that does not match any row MUST emit `signal_type: OTHER` and `severity: WARNING` and emit IntegrityGap(`kind: "integrity-signal-unclassified"`, severity=WARNING) with `condition_description`. The runtime MUST NOT enter REPAIRING state on an unclassified signal without operator clearance.

**Referenced from:** §64 REPAIRING entry conditions, §27 Evidence Integrity.

---

# 62d. Canonical Primitives

Canonical primitives are named types that appear in two or more citizen schemas, mechanism contracts, or infrastructure schemas. Defining each once establishes a single authority for its semantics, invariants, and valid values — the same design principle as §62b TemporalFields. A schema that uses a canonical primitive MUST declare `Uses canonical: [...]` and MUST honor its invariants at every use site.

## Identifier

A collision-resistant string identifier for any citizen or infrastructure record.

```
Identifier {
  format  {prefix}-{10-char-lowercase-hex-uuid}
          prefix encodes citizen type (obj, pla, ope, evi, chk, inp, rul, rel, dec, trg, ...)
  example "obj-3f2a8c1d0b"
}
```

**Immutability contract.** An Identifier MUST NOT change after the record is created. **Uniqueness contract.** An Identifier MUST be unique within its namespace for all time, including superseded and deactivated records. Two records sharing the same Identifier within the same namespace is a Ledger integrity violation. **Prefix contract.** The prefix is informational; enforcement MUST NOT depend on it, but all implementations SHOULD use consistent prefixes to aid manual inspection.

## DigestValue

A 64-character lowercase hexadecimal string representing a SHA-256 hash.

```
DigestValue {
  format    64-char lowercase hexadecimal
  algorithm SHA-256 (fixed; no substitution permitted)
  example   "e3b0c44298fc1c149afb...b855"  (SHA-256 of empty input)
}
```

**Comparison contract.** DigestValues MUST be compared case-insensitively; lowercase is canonical at rest. **Truncation contract.** An implementation MUST NOT truncate or abbreviate a DigestValue. A truncated digest is not a valid DigestValue. **Determinism contract.** The same input MUST always produce the same DigestValue. An implementation that non-deterministically hashes the same data violates this contract.

Used in: Checkpoint.digest, Change.state_before_digest, Change.state_after_digest, Change.rule_snapshot_digest, DestinationAnchor.digest, Transaction recovery (expected_file_hashes).

## UnitFloat

A float in the closed interval [0.0, 1.0] used to express scores, probabilities, and normalized weights.

```
UnitFloat {
  range  [0.0, 1.0] inclusive
  type   IEEE 754 double precision
}
```

**Validity contract.** UnitFloat fields MUST NOT accept NaN, infinity, or values outside [0.0, 1.0]. **Normalization contract.** When UnitFloat fields serve as normalized weights across a group (e.g. ScopePrioritySystem.scopes[*].normalized_weight), their sum MUST equal 1.0 (±1e-9 tolerance).

Used in: Objective.expected_value, Objective.estimated_cost, Objective.risk, Objective.urgency, Rule.confidence, ScopePrioritySystem scope weights, EvaluationSystem.weights.

## BaseUnit

A symbolic enumeration of standard measurement units for MeasureEntry values, budget quantities, and capacity metrics. Declaring a unit in BaseUnit enables cross-system comparison of metrics without runtime type inference.

```
BaseUnit {
  TOKENS        int; LLM context window tokens or prompt tokens
  REQUESTS      int; API or executor call count
  MILLISECONDS  float; elapsed time
  BYTES         int; data size
  COUNT         int; generic countable unit; use when no more specific unit applies
  SCORE         float [0.0, 1.0]; normalized quality or evaluation score (UnitFloat range)
  PERCENT       float [0.0, 100.0]; ratio expressed as a percentage
  CREDITS       float; metered resource credits (executor-defined denomination)
}
```

**Declaration contract.** When a MeasureEntry, MetricDefinition, or ExecutionBudget field carries a unit, the unit SHOULD be declared using a BaseUnit value when the metric fits one. A field that uses a non-standard unit MUST declare its unit semantics inline. **Comparison contract.** Two measurements are cross-system comparable only when they share the same BaseUnit and the same scope. **Extensibility.** A derived system MAY declare additional units; extension units MUST NOT reuse BaseUnit names. Uses canonical: UnitFloat (SCORE values). Used in: MeasureEntry (direction-tied unit), MetricDefinition, ExecutionBudget, Context Budget Mechanism.

## ProductScope

An enumeration of the four product scope values.

```
ProductScope {
  documentation  the spec and human-facing product artifacts
  runtime        the URACE lifecycle controller
  metrics        external metric collection and evaluation
  rebootstrap    the bootstrap installation file (URACE.md)
}
```

The wildcard `"*"` in Rule.scope means all four ProductScope values. An implementation MUST NOT define additional scope values without updating this enumeration. Used in: Operation.scope, Objective.scope, Rule.scope, ScopePrioritySystem.scopes keys, VelocityCheckpoint.scope.

## StatusTransition

A single status change event in an append-only status history list.

```
StatusTransition {
  status       REQUIRED  string; the new status value after this transition
  at           REQUIRED  timestamp
  from_status  OPTIONAL  string; the prior status value before this transition
  reason       OPTIONAL  string; why the transition occurred
  source       OPTIONAL  string; Input id or system component that triggered it
}
```

**Append-only contract.** A StatusTransition MUST NOT be modified after appended. **Ordering contract.** Transitions MUST be stored in chronological order. Used in: ConnectorSource.status_history. Implementations SHOULD apply StatusTransition to any citizen that tracks multiple status values over time.

## MetricEffect

The net metric outcome of a single Operation.

```
MetricEffect {
  improved   REQUIRED  int ≥ 0; count of metric dimensions that improved
  regressed  REQUIRED  int ≥ 0; count of metric dimensions that regressed
}
```

The sum `improved + regressed` MUST NOT exceed the total number of tracked metrics. A MetricEffect of `{improved: 0, regressed: 0}` is valid (neutral operation). Used in: Operation.observed_metric_effect, ExecutorCall.observed_metric_effect, Value Trajectory recording.

## MetricSnapshot

A point-in-time capture of all tracked metric values.

```
MetricSnapshot
  dict[metric_name → float]
```

All keys MUST be known MetricDefinition names at the time of capture. `before_metrics` and `after_metrics` in the same Operation MUST use the same set of keys. Used in: Operation.before_metrics, Operation.after_metrics.

## ExecutorAttribution

The routing and attribution record for a single Executor dispatch.

```
ExecutorAttribution {
  executor_id         REQUIRED  string; the resolved provider id that handled the call
  adapter             REQUIRED  string; adapter implementation identifier; format is implementation-defined
  capability          REQUIRED  string; capability exercised (discovery, execution, ...)
  attempted_executors REQUIRED  list[string]; all providers tried in dispatch order
  logical_reservation REQUIRED  string; ExecutorCall id that reserved this slot
}
```

**Consistency contract.** The ExecutorAttribution stored in Operation.executor and in ExecutorCall.executor_attribution for the same dispatch MUST be structurally identical. An implementation MUST NOT diverge the two representations. Used in: Operation.executor (post-dispatch), ExecutorCall.executor_attribution.

## ValidationCheck

A single check record within a ValidationResult.

```
ValidationCheck {
  check   REQUIRED  string; machine-readable check identifier
                    (e.g. "metric_guardrail:coverage", "file_presence:README.md")
  result  REQUIRED  PASS | FAIL
  detail  REQUIRED  string; human-readable explanation of the outcome
}
```

Used in: ValidationResult.checks, ValidationResult.fails, ChangeValidation.checks.

## ValidationResult

The outcome record returned by the independent validation gate.

```
ValidationResult {
  verdict      REQUIRED  VALIDATED | REJECTED | PENDING_CAPABILITY
  checks       REQUIRED  list[ValidationCheck]; all checks, pass and fail
  fails        REQUIRED  list[ValidationCheck]; subset where result = FAIL
  basis        REQUIRED  string; description of which checks this gate applies
  validated_at REQUIRED  timestamp
}
```

- `VALIDATED`: all checks passed; the Operation MAY be accepted.
- `REJECTED`: at least one check failed; the Operation MUST be rolled back.
- `PENDING_CAPABILITY`: validation infra is temporarily unavailable; the Operation MUST be queued as PendingValidation, NOT auto-accepted.

**Separation contract.** `ValidationResult.verdict` uses `VALIDATED|REJECTED|PENDING_CAPABILITY` — the process result. `ChangeValidation.verdict` uses `ACCEPTED|REJECTED|ROLLED_BACK` — the lifecycle disposition. These MUST NOT be conflated.

Used in: Operation.independent_validation.

## ChangeValidation

The lifecycle disposition record stored on a Change binding. Distinct from ValidationResult.

```
ChangeValidation {
  verdict  REQUIRED  ACCEPTED | REJECTED | ROLLED_BACK
  checks   REQUIRED  list[ValidationCheck]; checks from ValidationResult that informed this disposition
}
```

`ACCEPTED`: the Operation was committed to Product state. `REJECTED`: the Operation was rejected (rolled back or independently invalidated). `ROLLED_BACK`: the Operation was explicitly rolled back by the Transaction mechanism.

Used in: Change.validation.

## ErrorRecord

A structured error or failure observation from any subsystem.

```
ErrorRecord {
  source  REQUIRED  string; component or data source that reported the error
  error   REQUIRED  string; human-readable error message or code
  kind    REQUIRED  string; machine-readable error category
  at      OPTIONAL  timestamp; when error occurred
}
```

Used in: ExternalMetricState.errors, ProviderStatus failure context.

## FailureRecord

A deduplicated failure entry for recurring fault patterns.

```
FailureRecord {
  at           REQUIRED  timestamp; first occurrence
  last_at      REQUIRED  timestamp; most recent occurrence (= at on first occurrence)
  stage        REQUIRED  string; lifecycle stage or component where failure occurred
  error        REQUIRED  string; error message or exception description
  count        REQUIRED  int ≥ 1; total occurrences
  failure_type OPTIONAL  transient | semantic | structural; default semantic when absent
}
```

**Deduplication contract.** A FailureRecord with the same stage and error signature MUST be updated (`count`, `last_at`) rather than appended as a new record. `failure_type` is NOT part of the deduplication key; the key remains `stage + error` only. **Failure type semantics.** `transient` — network, transport, or provider-capacity error not attributable to logic or configuration; routes to short-backoff retry. `semantic` — incorrect approach, wrong technique, or strategy mismatch; routes to tier escalation via TechniqueApplicabilityGate. `structural` — broken invariant, schema violation, or corrupt state; routes to rollback and REPAIRING. **Backwards compatibility contract.** Existing FailureRecord instances without `failure_type` MUST be treated as `failure_type: semantic`; an implementation MUST NOT reject or fail to read a FailureRecord missing this field. **Growth contract.** Deduplication bounds growth by fault identity; when failure diversity is high (many distinct `stage` + `error` combinations) the list may still grow substantially. An implementation MAY define a RetentionPolicy for this field. If no RetentionPolicy exists and the list exceeds 500 entries, the lifecycle MUST emit a `retention-policy-violated` WARNING IntegrityGap. Used in: ExecutorState.failures.

## RecoveryManifest

A re-ingestible artifact emitted when `REPAIRING` reaches repair-exhausted in `auto` execution mode, or when `ExecutionBudget` is exhausted in `auto` mode. Enables the next `urace auto` invocation to continue goal-scoped execution from the furthest safe point without human intervention. Stored as `ExecutorState.recovery_manifest`; persisted via the existing atomic write contract.

```
RecoveryManifest {
  manifest_id         REQUIRED  string; unique identifier for this manifest instance
  emitted_at          REQUIRED  timestamp; when this manifest was written
  emission_cause      REQUIRED  repair-exhausted | budget-exhausted; what triggered emission
  last_safe_state     REQUIRED  string; lifecycle state value at last known good point before failure
  last_safe_commit    REQUIRED  string | null; durable checkpoint id or git ref at last known good
                                 point; null if no checkpoint exists
  failure_summary     REQUIRED  list[string]; FailureRecord ids from ExecutorState.failures that
                                 contributed to this emission; MAY be empty if cause is budget-exhausted
                                 with no recorded failures
  goal_delta          REQUIRED  string; human-readable description of remaining work not yet completed
                                 at time of emission; derived from incomplete Objectives
  progress_at_emit    REQUIRED  float [0.0, 1.0] | null; value of ExecutorState.progress_vector at
                                 emission; null if progress_vector was null
  budget_consumed     OPTIONAL  ExecutionBudget | null; snapshot of ExecutionBudget at emission;
                                 null if no ExecutionBudget was configured
  recommended_tier    OPTIONAL  T1 | T2 | T3 | null; highest TechniqueApplicabilityGate tier
                                 attempted before exhaustion; hints re-entry strategy for next run
  execution_mode      REQUIRED  auto | supervised; execution mode active at time of emission
}
```

**Re-ingestion contract.** On `urace auto` start, if `ExecutorState.recovery_manifest` is non-null and `emission_cause` matches a recoverable condition, the lifecycle MUST use `last_safe_state`, `last_safe_commit`, and `recommended_tier` to resume from the manifest rather than reinitializing from scratch. **Single-manifest contract.** Only one RecoveryManifest is retained at a time; a new emission overwrites the prior value. **Supervisor visibility contract.** In `supervised` mode, `RecoveryManifest` is never emitted autonomously; it is populated only when an operator explicitly requests a manifest export. **Citizen classification.** RecoveryManifest is a named lifecycle entity conforming to AP0 (Citizen); it carries durable identity (`manifest_id`), lifecycle attribution (`emitted_at`, `execution_mode`), and a defined retention policy (overwritten on next emission).

## ChangeHistoryEntry

A single entry in an append-only configuration change log.

```
ChangeHistoryEntry {
  at      REQUIRED  timestamp; when the change occurred
  version OPTIONAL  int; the new version after this change
  before  REQUIRED  dict; state before the change (structure is schema-specific)
  after   REQUIRED  dict; state after the change (structure is schema-specific)
  input   OPTIONAL  string; Input id or authority basis that authorized the change
}
```

**Append-only contract.** ChangeHistoryEntry lists carry `compaction_mode: PROHIBITED`. They MUST NOT be modified, compacted, summarized, or replaced with CompactionSummary entries. Where storage pressure requires relief, entries MAY be transferred to an ARCHIVE file via a `urace compact` command using ARCHIVE mode only; the entries MUST remain intact in the archive file and a CompactionSummary with `is_decompactable: true` MUST be placed in the live list. ROLLING_EVICTION of ChangeHistoryEntry records is permanently prohibited regardless of any RetentionPolicy. Used in: MetricSystem.change_history, EvaluationSystem.change_history.

## FaultDescriptor

Structured identification of a recurring lifecycle controller fault.

```
FaultDescriptor {
  component        REQUIRED  string; subsystem where fault occurred
  code             REQUIRED  string; short machine-readable fault code
  operation        OPTIONAL  string; lifecycle operation or phase at fault time
  error_type       OPTIONAL  string; implementation-defined error type identifier
                             (e.g. exception class name, error code, signal identifier)
  -- additional fields MAY be present for implementation-specific fault context --
}
```

**Stability contract.** A FaultDescriptor with identical `component` + `code` + `operation` + `error_type` MUST be treated as the same fault for deduplication purposes in SystemRepairEntry. Used in: SystemRepairEntry.fault.

## UsageRecord

Token and cost accounting from an Executor call.

```
UsageRecord {
  source             REQUIRED  string; provider or tool that reported usage
  observed_at        REQUIRED  timestamp
  input_tokens       OPTIONAL  int ≥ 0; tokens consumed on the input side
  output_tokens      OPTIONAL  int ≥ 0; tokens produced on the output side
  reported_cost_usd  OPTIONAL  float ≥ 0.0; provider-reported cost in USD
  extended           OPTIONAL  dict[string → any]; provider-specific accounting fields
                               that do not map to the standard fields above
                               (e.g. cache token breakdowns, request units, compute credits)
}
```

**Absence contract.** An absent token field means the provider did not report it; it MUST NOT be treated as 0. `total_tokens` in ExecutorCall.usage is a derived sum `input_tokens + output_tokens`; a provider that reports only `total_tokens` MUST be treated as non-decomposable. Provider-specific token sub-types or quota units MUST be stored in `extended` rather than as top-level fields, so the schema remains executor-agnostic. Used in: ExecutorCall.usage.

## ScopePriorityEntry

A single scope's computed weight record within ScopePrioritySystem.

```
ScopePriorityEntry {
  label                       REQUIRED  string; human-readable scope label
  raw_weight                  REQUIRED  float ≥ 0; pre-normalization computed weight
  normalized_weight           REQUIRED  UnitFloat; raw_weight / sum(all raw_weights)
  previous_weight             REQUIRED  UnitFloat | null; normalized_weight from prior revision
  change_limited              REQUIRED  bool; true = weight was clamped by max_weight_step_per_revision
  base_weight                 REQUIRED  float; configured static base weight for this scope
  min_weight                  REQUIRED  float; minimum allowed normalized weight
  max_weight                  REQUIRED  float; maximum allowed normalized weight
  backlog                     REQUIRED  int ≥ 0; count of open Objectives for this scope
  unresolved_markers          REQUIRED  int ≥ 0; open integrity gaps or blockers for this scope
  days_since_accepted_change  REQUIRED  float ≥ 0; staleness measure
  artifacts                   REQUIRED  list[string]; tracked file paths for this scope
}
```

Used in: ScopePrioritySystem.scopes (dict values). Uses canonical: UnitFloat.

## MeasureEntry

A single metric's progress baseline and current reading within a ProgressProfile.

```
MeasureEntry {
  baseline   REQUIRED  float; value at Objective creation; immutable after set
  current    REQUIRED  float; most recently observed value
  previous   REQUIRED  float | null; value before the most recent update; null on first update
  target     REQUIRED  float; desired endpoint value
  direction  REQUIRED  nondecreasing | nonincreasing
}
```

**Baseline immutability.** Once set, `baseline` MUST NOT change for the lifetime of the ProgressProfile. Used in: ProgressProfile.measures (dict values).

## ObservationRecord

A single collected observation from a ConnectorSource.

```
ObservationRecord {
  source      REQUIRED  ConnectorSource id
  at          REQUIRED  timestamp; when observation was collected
  visibility  REQUIRED  public | private
  values      REQUIRED  dict[metric_name → any]; raw observed values keyed by metric name
  events      OPTIONAL  list; discrete timestamped events associated with this observation
}
```

**Retention contract.** `ExternalMetricState.latest` is a rolling observation window. Implementations MUST bound its growth: the default ceiling is 1000 entries under ROLLING_EVICTION mode. The ceiling MAY be reconfigured via a RetentionPolicy, and the mode MAY be changed to ARCHIVE when observation replay is required. Exceeding the ceiling without a compaction event MUST emit a `retention-policy-violated` WARNING IntegrityGap. `retain(r) ↔ now() − parse_ts(r.at) < retention_seconds` Used in: ExternalMetricState.latest. Uses canonical: TemporalFields (at as created_at).

## ProviderStatus

The operational status record for a single Executor provider, accumulated via probe cycles.

```
ProviderStatus {
  available          REQUIRED  bool | null; null = never probed
  authenticated      OPTIONAL  bool | null; null = not applicable
  last_probe_at      OPTIONAL  timestamp | null
  reason             OPTIONAL  string; last availability reason or message
  retry_at           OPTIONAL  timestamp | null; earliest retry after capacity exhaustion
  cooldown_until     OPTIONAL  timestamp | null; earliest retry after probe failure cooldown
  failures           OPTIONAL  int ≥ 0; consecutive or cumulative probe failure count
  last_success_at    OPTIONAL  timestamp | null
  last_capacity_at   OPTIONAL  timestamp | null; when capacity ceiling was last hit
  calls_24h          OPTIONAL  int ≥ 0; dispatched calls in rolling 24h window
  calls_30d          OPTIONAL  int ≥ 0; dispatched calls in rolling 30d window
  limit_24h          OPTIONAL  int ≥ 1; configured 24h ceiling
  limit_30d          OPTIONAL  int ≥ 1; configured 30d ceiling
  attempt_history    OPTIONAL  list[timestamp]; rolling dispatch timestamps for budget computation
  transport_attempts OPTIONAL  int ≥ 0; total transport-level attempts for this provider
}
```

**Accumulation contract.** ProviderStatus is NOT recreated on each probe; it is updated in place. Fields absent before a probe are not retroactively populated. **Budget window contract.** `calls_24h` and `calls_30d` MUST be computed from `attempt_history` by counting entries within the respective rolling window, not from a stored counter, to survive restarts correctly. **Rolling-window contract.** `attempt_history` entries older than `max(limit_30d_window + 5 days, 35 days)` are eligible for integral rolling eviction at each probe cycle. An implementation MUST evict eligible entries in-place without emitting a CompactionEvent or CompactionSummary, as this is an integral part of the rolling-window computation contract and not a policy-triggered compaction. Used in: ExecutorState.provider_pool (dict values).

## WakeCondition

The condition descriptor stored in a WakeRegistration that defines when the registration fires.

```
WakeCondition {
  scheduled_at   REQUIRED  timestamp; the canonical trigger time
  -- additional fields MAY be present for TRIGGERED or CONDITIONAL kinds --
}
```

For `SCHEDULED` kind registrations, `scheduled_at` is the only required field. For `TRIGGERED` and `CONDITIONAL` kinds, implementations MAY extend WakeCondition with additional observable criteria. `scheduled_at` MUST always be present regardless of kind and is the field used by the scheduler. Used in: WakeRegistration.condition.

## DecisionRecord

A structured record of the complete basis for a consequential lifecycle decision, enabling attributability, revalidation and provenance tracking as required by the Decision-integrity invariant (line 62). This is the authoritative canonical schema referenced by §45.

```
DecisionRecord {
  id                    REQUIRED  Identifier; prefix "dec"
  kind                  REQUIRED  OBJECTIVE_SELECTION | OPERATION_AUTHORIZATION |
                                  CHECKPOINT_ACCEPTANCE | RULE_CREATION |
                                  NAVIGATION_ASSESSMENT | AUTHORITY_EXERCISE |
                                  DESTINATION_EVOLUTION
  subject               REQUIRED  string; brief description of what was decided
  outcome               REQUIRED  string; the decision result (e.g. "selected", "authorized", "accepted")
  authority_basis       OPTIONAL  string; the Rule id or Authority clause that authorized this decision
  governing_intent_ref  REQUIRED  string; Intent version id or snapshot reference at decision time
  state_digest          REQUIRED  DigestValue; SHA-256 of URACE state at the moment of decision
  evidence_refs         OPTIONAL  list[string]; Evidence record ids that were determinative
  constraints           OPTIONAL  list[string]; active constraint ids or descriptions that shaped this
  assumptions           OPTIONAL  list[string]; explicit assumptions relied upon; each MUST be stated
                                  as a positive belief, not as absence of evidence
  uncertainty           OPTIONAL  UnitFloat; assessed decision uncertainty (0.0 = certain, 1.0 = maximal)
  objective_ref         OPTIONAL  string; Objective id when this decision concerns an Objective
  plan_ref              OPTIONAL  string; Plan id when this decision concerns a Plan
  operation_ref         OPTIONAL  string; Operation id when this decision concerns an Operation
  alternatives          OPTIONAL  list[AlternativeConsidered]; paths that were considered and rejected
  justification_summary OPTIONAL  string; concise human-readable justification; MUST NOT expose
                                  hidden chain-of-thought; is the reviewable basis, not a
                                  post-hoc rationalization
  executor              REQUIRED  ExecutorAttribution; the Executor that reasoned this decision
  provenance_status     REQUIRED  CURRENT | PROVENANCE_REVISED | SUPERSEDED
  revision_notice       OPTIONAL  string; attributed revision notice; REQUIRED when provenance_status
                                  is PROVENANCE_REVISED or SUPERSEDED; absent when CURRENT
  validity_conditions   OPTIONAL  list[string]; conditions under which this decision remains valid;
                                  a material change that falsifies any listed condition MUST trigger
                                  proportionate revalidation
  prior_decision_refs   OPTIONAL  list[string]; DecisionRecord ids whose reasoning this record
                                  extends, depends upon, or revises; enables reasoning chain traversal
  completeness          OPTIONAL  UnitFloat; subjective completeness of the justification
                                  (0.0 = minimal viable justification, 1.0 = exhaustive);
                                  advisory only — not a quality gate unless policy sets one
  reasoning_steps       OPTIONAL  list[ReasoningStep]; ordered structured reasoning trail that
                                  produced the outcome; MUST NOT expose hidden chain-of-thought;
                                  each step is the reviewable basis, not reasoning detail
  outcome_feedback      OPTIONAL  OutcomeFeedback; post-decision observation once outcome is known;
                                  absent until outcome is observable
  decided_at            REQUIRED  timestamp
  justification_context_id OPTIONAL  string; JustificationContext id (prefix jctx-) evaluated before this decision; links durable justification predicate record
}
```

**Durable contract.** A DecisionRecord for a consequential decision MUST be written before or coincident with the operation it authorizes; a record written retroactively to rationalize an already-committed effect does not satisfy the Decision-integrity invariant. **Immutability contract.** A DecisionRecord MUST NOT be modified after `provenance_status: CURRENT` is established. A provenance revision MUST add `revision_notice` and change `provenance_status`; the original fields MUST remain intact. **Provenance-revised contract.** A provenance-revised record MUST surface in `urace check` output with an identified revalidation requirement for any active Objectives, Plans or Operations it authorized. **Kind contract.** `kind` MUST accurately reflect the lifecycle action this record authorizes. Misdeclaring kind to bypass applicable Authority checks is a Ledger integrity violation. **Assumptions positive-statement contract.** Each assumption MUST assert a concrete belief ("the target API rate limit is 1000 req/min") not an absence of evidence. Absence-of-evidence assumptions may expire without triggering revalidation; positive belief assumptions do not. **Reasoning-chain contract.** `prior_decision_refs` MUST reference only existing DecisionRecord ids; a dangling reference is a Ledger integrity violation. A cycle in the reasoning chain (A → B → A) MUST be surfaced as a WARNING IntegrityGap. **Outcome-feedback contract.** `outcome_feedback` MUST NOT be written in the same operation that creates the record; it is populated by a separate subsequent update after the outcome is observable. **Retention.** DecisionRecord lists are governed by Compaction and Retention (§62f): default ceiling 2000 entries under ARCHIVE mode.

Used in: Objective (on selection), Operation (on authorization), Checkpoint (on acceptance), and any lifecycle action subject to the Decision-integrity invariant. Uses canonical: Identifier (id), DigestValue (state_digest), UnitFloat (uncertainty, completeness), ExecutorAttribution (executor), AlternativeConsidered (alternatives entries), ReasoningStep (reasoning_steps entries), OutcomeFeedback (outcome_feedback), TemporalFields (decided_at as created_at). Cross-reference: §62g Justification System documents reasoning-chain traversal and `urace why`.

## AlternativeConsidered

A structured record of a decision path that was considered and rejected. Used within DecisionRecord to make the decision reasoning auditable and non-arbitrary.

```
AlternativeConsidered {
  description   REQUIRED  string; brief description of the alternative path or option
  rejected_why  REQUIRED  string; specific, stated reason for rejection; MUST NOT be circular
                          (e.g. "not this because we chose the other" is not a valid reason);
                          MUST identify a specific property that is inadequate given current
                          Authority, Intent, Evidence, or constraints
  evidence_refs OPTIONAL  list[string]; Evidence record ids that informed or drove the rejection
}
```

**Non-arbitrariness contract.** `rejected_why` MUST contain a falsifiable claim about the alternative. A circular reason or preference statement without basis does not satisfy this contract and MUST be flagged as a Ledger integrity violation on load. Used in: DecisionRecord.alternatives entries.

## ReasoningStep

A single structured step in the ordered reasoning trail that produced a DecisionRecord outcome. Used to make multi-step reasoning auditable, traversable, and machine-queryable without requiring full decompaction or Executor re-invocation.

```
ReasoningStep {
  step_index   REQUIRED  int ≥ 0; zero-based position in the ordered trail
  kind         REQUIRED  OBSERVATION | INFERENCE | CONSTRAINT_CHECK | AUTHORITY_CHECK |
                         ALTERNATIVE_EVALUATION | SYNTHESIS
  description  REQUIRED  string; the claim, inference, or check performed at this step;
                          MUST be stated as a positive factual claim, not raw reasoning narrative
  evidence_ref OPTIONAL  string; Evidence record id that grounds this step, if any
  outcome      REQUIRED  PASS | FAIL | INCONCLUSIVE; result of this step's evaluation
  detail       OPTIONAL  string; additional machine-readable detail; MAY be omitted for brevity
}
```

**Step integrity contract.** `step_index` MUST be unique within a DecisionRecord's `reasoning_steps` list and MUST form a contiguous sequence from 0 to N−1 with no gaps. **No-narrative contract.** `description` and `detail` MUST NOT expose hidden chain-of-thought; they are the reviewable basis for a step, not reasoning detail. A step that references prior in-process memory not present in durable state violates the stateless-resumable contract (§75). **Kind contract.** `kind` MUST accurately reflect the logical operation performed at this step. Used in: DecisionRecord.reasoning_steps entries.

## OutcomeFeedback

A post-decision observation record that closes the reasoning loop by recording whether the outcome materialized as expected. Written by the lifecycle controller once the outcome of a DecisionRecord is observable, not at decision time.

```
OutcomeFeedback {
  observed_at       REQUIRED  timestamp; when the outcome was observed
  materialized      REQUIRED  bool; true = outcome matches decision prediction; false = diverged
  divergence_note   OPTIONAL  string; if not materialized, a falsifiable description of how outcome
                               differed from prediction; REQUIRED when materialized is false
  evidence_ref      OPTIONAL  string; Evidence record id that substantiates the observation
  triggers_revision REQUIRED  bool; true = this feedback warrants a provenance revision of the
                               DecisionRecord; lifecycle controller MUST flag PROVENANCE_REVISED
                               when true and the record is still CURRENT
}
```

**Immutability contract.** Once written, an OutcomeFeedback MUST NOT be modified; a revised assessment MUST be recorded as a provenance revision of the DecisionRecord itself, not an in-place update of OutcomeFeedback. **Causal contract.** `observed_at` MUST be after `DecisionRecord.decided_at`; an OutcomeFeedback with `observed_at` ≤ `decided_at` is a Ledger integrity violation. **Auto-revision contract.** When `triggers_revision` is true, the lifecycle controller MUST set `provenance_status: PROVENANCE_REVISED` on the associated DecisionRecord and MUST add a `revision_notice` referencing the OutcomeFeedback observation. Used in: DecisionRecord.outcome_feedback. Uses canonical: TemporalFields (observed_at as created_at).

**QualityDelta integration.** A QualityDelta (§62b) MUST be written concurrently with an OutcomeFeedback record when a score measurement is available for the associated operation, linking the feedback to the quality trajectory for the Quality Streak Mechanism (§62c). An OutcomeFeedback record with an available score measurement that is written without a concurrent QualityDelta is an architectural gap.

## RetentionPolicy

Extends: AuthorizedCitizen
Implements: GoverningRecord

A configurable policy governing maximum growth and compaction eligibility for an accumulating list field in URACE persistent state. Establishes the authorization for policy-triggered compaction (§62f).

```
RetentionPolicy {
  id               REQUIRED  Identifier; prefix "rtp"
  target_field     REQUIRED  string; dot-path of the governed list field
                             (e.g. "executor_state.failures", "external_metric_state.latest")
  max_entries      OPTIONAL  int ≥ 1; list length ceiling; entries beyond this are eligible for
                             compaction at the next safe lifecycle boundary
  max_age_days     OPTIONAL  float > 0; entries older than this duration are eligible for compaction
  compaction_mode  REQUIRED  PROHIBITED | ARCHIVE | ROLLING_EVICTION
  archive_subpath  OPTIONAL  string; relative path under state_path for the archive file;
                             REQUIRED when compaction_mode is ARCHIVE; absent otherwise
  authority_basis  OPTIONAL  string; authorizing rule id or authority scope (GoverningRecord)
  scope            OPTIONAL  string; governance scope affected (GoverningRecord)
  established_at   OPTIONAL  ISO-8601; when policy was established (GoverningRecord)
}
```

**Mode semantics.** `PROHIBITED`: no compaction of any kind is permitted; any operation that would compact this field MUST be rejected as a policy violation. `ARCHIVE`: eligible records are moved to `archive_subpath` intact and replaced in the live list by a CompactionSummary with `is_decompactable: true`; decompaction restores originals. This is the **lossless-reversible** mode. `ROLLING_EVICTION`: eligible records are discarded without archive; MUST be used only for fields whose individual historical values have no residual analytical value (e.g. raw timestamps outside a budget window); decompaction is impossible.

**Minimum-trigger contract.** At least one of `max_entries` or `max_age_days` MUST be present. A RetentionPolicy with neither field is structurally invalid. **Override contract.** A RetentionPolicy MUST NOT change the mode of a field whose schema defines `compaction_mode: PROHIBITED`. **Establishment contract.** A RetentionPolicy MUST be established through an attributable operator input during bootstrap or via `urace govern`; it MUST NOT be created autonomously. Uses canonical: Identifier (id).

**Firing contract.** Retention policy evaluation MUST fire: (1) at the start of each compaction cycle (before any eviction); (2) on demand when `urace /compact` is issued; (3) automatically when the State Document size exceeds `Config.retention.auto_trigger_bytes` (default: 10MB). The runtime MUST NOT apply retention rules mid-cycle outside these triggers.

**Multi-policy interaction.** When multiple RetentionPolicy records are active, they MUST be applied in ascending order of `priority` field (lower value = applied first). If two policies conflict (e.g., one retains a record, another evicts it), the more conservative policy (retain) MUST win. The runtime MUST record which policy governed each eviction decision in the CompactionSummary.

**Atomicity guarantee.** All evictions from a single retention-policy evaluation pass MUST be committed as a single atomic Transaction (AP16). If any eviction in the pass fails, the entire pass MUST be rolled back and a WARNING gap of kind `retention-pass-partial-failure` MUST be surfaced.

## CompactionSummary

A structured in-place replacement for a segment of compacted records within a governed list field. Preserves a cryptographic commitment to the original records and a reference to the archive, enabling lossless decompaction when the archive is present.

```
CompactionSummary {
  compaction_event_id  REQUIRED  Identifier; the CompactionEvent (§62e) that produced this entry
  record_count         REQUIRED  int ≥ 0; number of original records this entry represents
  time_range           REQUIRED  {from: timestamp, to: timestamp}; temporal span of compacted records
  original_digest      REQUIRED  DigestValue; SHA-256 of the canonical serialization of the originals
  is_decompactable     REQUIRED  bool; true = originals are in the archive and restorable via
                                 urace decompact <compaction_event_id>; false = ROLLING_EVICTION
  record_ids           OPTIONAL  list[string]; ids of the original records in their original order;
                                 enables O(1) existence-check and single-record lookup without
                                 full decompaction; MUST be populated for ARCHIVE-mode compactions
                                 unless the records have no id field
  kinds                OPTIONAL  dict[string → list[string]]; map of record kind (or schema type)
                                 to list of matching record ids; enables type-indexed scan without
                                 decompaction; keys MUST be from the governed schema's kind enum
  summary_text         OPTIONAL  string; human-readable description of the compacted period; advisory
}
```

**Integrity contract.** `original_digest` MUST be computed before any records are removed. A CompactionSummary whose `original_digest` does not match the archive is a `compaction-manifest-divergence` BLOCKING IntegrityGap. **Position contract.** A CompactionSummary MUST be placed at the position in the list where the first of the compacted records appeared; compacted records are then removed. The relative ordering of live (non-compacted) records MUST NOT change. **Prohibited-field contract.** A CompactionSummary MUST NOT be inserted into a field with `compaction_mode: PROHIBITED`. **Aggregation contract.** Any query or inspection command that aggregates over a governed list MUST account for CompactionSummary entries: `record_count` and `time_range` MUST be used for aggregate statistics, not skipped or treated as zero. **Lookup contract.** `record_ids` and `kinds` MUST be populated for ARCHIVE-mode compactions on governed lists whose records carry an `id` field. An implementation that omits them on ARCHIVE-mode compaction is non-conformant for the purposes of incremental decompaction. Uses canonical: Identifier (compaction_event_id), DigestValue (original_digest), TemporalFields (time_range timestamps).

## QualityDelta

A single quality measurement comparing consecutive operation results in the same scope. Forms an ordered quality trajectory for the Quality Streak Mechanism (§62c).

```
QualityDelta {
  id               REQUIRED  Identifier; prefix "qdl"
  operation_id     REQUIRED  Identifier; the Operation whose result is measured
  predecessor_id   OPTIONAL  Identifier; immediately preceding Operation in the same scope; absent when no predecessor
  scope            REQUIRED  ProductScope
  score_before     OPTIONAL  UnitFloat; quality score of predecessor result; absent when no predecessor
  score_after      REQUIRED  UnitFloat; quality score of this operation's result
  delta            REQUIRED  float; score_after − score_before; 0.0 when no predecessor
  classification   REQUIRED  IMPROVEMENT | NEUTRAL | REGRESSION
  measured_at      REQUIRED  timestamp
  measure_ref      OPTIONAL  Identifier; MeasureEntry that produced score_after
}
```

**Classification contract.** `IMPROVEMENT`: delta > 0; `NEUTRAL`: delta = 0 or no predecessor; `REGRESSION`: delta < 0. **Immutability contract.** Once written, a QualityDelta MUST NOT be modified. **Predecessor chain.** Consecutive QualityDeltas for the same scope form an ordered quality trajectory. **Causal contract.** `measured_at` MUST be after the associated Operation's committed_at. **Unit contract.** `score_before` and `score_after` carry `BaseUnit.SCORE` semantics: normalized scores in [0.0, 1.0]. Two QualityDelta records are cross-system comparable only when they share the same `scope` and the same `BaseUnit.SCORE` convention. Uses canonical: Identifier (id, operation_id, predecessor_id, measure_ref), UnitFloat (score_before, score_after), ProductScope (scope), TemporalFields (measured_at as created_at). Used in: State.quality_deltas.

## QualityStateEntry

Per-scope live accumulator for the Quality Streak Mechanism (§62c). Stored in `State.quality_state` as a first-class lifecycle citizen, independent of ExecutorState. Implements AP9 — Monotone Accumulator (§62i). Executor replacement MUST NOT affect this citizen; it persists across executor changes.

```
QualityStateEntry {
  scope              REQUIRED  ProductScope; the scope this entry governs
  current_streak     REQUIRED  int ≥ 0; consecutive IMPROVEMENT QualityDeltas in scope
  best_streak        REQUIRED  int ≥ 0; highest streak ever achieved in scope
  streak_started_at  OPTIONAL  timestamp | null; when current streak began; null when current_streak == 0
  last_evaluated_at  REQUIRED  timestamp; when this entry was last updated by the Quality Streak Mechanism
}
```

**Independence contract.** One `QualityStateEntry` per scope. A REGRESSION in one scope MUST NOT affect any other scope's entry. **Persistence contract.** `QualityStateEntry` is a Product-level citizen; it MUST be preserved across executor replacement, cognitive reset, and restart. It MUST NOT reside in or depend on ExecutorState. **Initialization contract.** A `QualityStateEntry` for a scope is created on first `QualityDelta` write for that scope, with `current_streak = 0`, `best_streak = 0`, `streak_started_at = null`. Uses canonical: ProductScope (scope), TemporalFields (last_evaluated_at as created_at). Used in: State.quality_state.

## ComplianceRecord

A single immutable record of a compliance evaluation outcome for one validation domain. Forms an append-only compliance trajectory, analogous to QualityDelta for quality. Written after every independent validation gate evaluation.

```
ComplianceRecord {
  id               REQUIRED  Identifier; prefix "cpl"
  domain           REQUIRED  "authority" | "intent" | "schema" | "constraint" | "governance"
  status           REQUIRED  COMPLIANT | NON_COMPLIANT | UNKNOWN
  operation_id     OPTIONAL  Identifier; operation that triggered this evaluation; absent when source is not an operation
  decision_id      OPTIONAL  Identifier; DecisionRecord that substantiates the compliance outcome
  violation_detail OPTIONAL  string; human-readable description when status = NON_COMPLIANT
  scope            OPTIONAL  ProductScope; scope of the evaluated operation or record
  evaluated_at     REQUIRED  timestamp
}
```

**Immutability contract.** Once written, a ComplianceRecord MUST NOT be modified. **Causal contract.** evaluated_at MUST be on or after the associated operation's committed_at when operation_id is present. **Domain contract.** domain values are fixed to the four validation domains from §54 plus "governance" for Rule Ledger and DestinationAnchor checks. **Trajectory contract.** Consecutive ComplianceRecords for the same domain form an ordered compliance trajectory; the most recent per domain represents current posture. Uses canonical: Identifier (id, operation_id, decision_id), ProductScope (scope), TemporalFields (evaluated_at as created_at). Used in: State.compliance_records.

## ComplianceState

Per-domain live summary of current compliance posture. One entry per domain, updated on each ComplianceRecord write for that domain. Product-level citizen; persists across executor replacement.

```
ComplianceState {
  domain              REQUIRED  string; same enum as ComplianceRecord.domain
  status              REQUIRED  COMPLIANT | NON_COMPLIANT | UNKNOWN
  last_checked_at     REQUIRED  timestamp; when this entry was last updated
  violation_refs      OPTIONAL  list[Identifier]; ids of recent NON_COMPLIANT ComplianceRecords for this domain
  consecutive_clean   REQUIRED  int ≥ 0; number of COMPLIANT evaluations since last NON_COMPLIANT
}
```

**Persistence contract.** ComplianceState entries are Product-level; they MUST survive executor replacement, cognitive reset, and restart. **Initialization contract.** A ComplianceState entry for a domain is created on first ComplianceRecord write for that domain, with consecutive_clean = 0. **Independence contract.** One entry per domain. A NON_COMPLIANT result in one domain MUST NOT affect any other domain's entry. **Self-determination contract.** SD(compliance inspection, S) = True; urace /compliance reads only durable state. Uses canonical: Identifier (violation_refs entries), TemporalFields (last_checked_at as created_at). Used in: State.compliance_state.

## ReIngestionRecord

Tracks the re-ingestion of archived or compacted lifecycle data back into active state. Produced by the Re-Ingestion Mechanism (§62c).

```
ReIngestionRecord {
  id                   REQUIRED  Identifier; prefix "rei"
  compaction_event_id  REQUIRED  Identifier; CompactionEvent that produced the archived data
  archive_path         REQUIRED  string; path from which records were read
  record_count         REQUIRED  int ≥ 0; number of records re-ingested
  target_field         REQUIRED  string; dot-path of the live field restored into
  digest_verified      REQUIRED  bool; true = original_digest matched before re-ingestion
  re_ingested_at       REQUIRED  timestamp
  operator_id          OPTIONAL  string; identity of the authoritative source that authorized re-ingestion
  status               REQUIRED  VERIFIED | INTEGRITY_GAP
}
```

**Integrity contract.** Before any record is moved from archive back to the live field, the implementation MUST compute SHA-256 of the archived records and compare to `CompactionSummary.original_digest`. A mismatch MUST set `status = INTEGRITY_GAP` and emit `IntegrityGap(kind="reingestion-digest-mismatch", severity=BLOCKING)`. **Authorization contract.** Re-ingestion MUST NOT be performed autonomously; an attributable operator input MUST precede it. Uses canonical: Identifier (id, compaction_event_id), TemporalFields (re_ingested_at as created_at). Used in: State evidence log, Re-Ingestion Mechanism (§62c).

## OperationDependency

A directed edge in the operation dependency DAG within a Plan. The set of OperationDependency edges MUST be acyclic.

```
OperationDependency {
  from_id    REQUIRED  Identifier; Objective or Operation that must satisfy this edge before to_id proceeds
  to_id      REQUIRED  Identifier; Objective or Operation that depends on from_id
  kind       REQUIRED  FINISH_TO_START | START_TO_START | FINISH_TO_FINISH
  scope      OPTIONAL  ProductScope; scope within which the dependency is meaningful
  rationale  OPTIONAL  string; human-readable reason for this dependency edge
}
```

**DAG invariant.** OperationDependency edges in a Plan MUST be acyclic. A cycle is a Plan integrity violation; URACE MUST NOT schedule any operation in a cyclic cluster until the cycle is resolved. Topological sort order (FOUNDATIONAL first, INTEGRATED last — AP24 §62i) MUST be honored. **Kind semantics.** `FINISH_TO_START`: to_id may not start until from_id is complete. `START_TO_START`: to_id may not start until from_id has started. `FINISH_TO_FINISH`: to_id may not finish until from_id has finished. Uses canonical: Identifier (from_id, to_id), ProductScope (scope). Used in: Plan.dependencies (§40).

## CapabilityStatement

A named, testable unit of capability the Product must possess to reach its capable sweet spot. Capability statements are declared in Config.capability_envelope and tracked in State.capability_states.

```
CapabilityStatement {
  id              REQUIRED  Identifier; prefix "cap"
  name            REQUIRED  string; human-readable capability name
  description     REQUIRED  string; what this capability enables
  scope           REQUIRED  ProductScope
  tier            REQUIRED  FOUNDATIONAL | COMPOSITIONAL | INTEGRATED  (AP24 tiers)
  value_weight    REQUIRED  UnitFloat; relative contribution to product value (weights sum to 1.0 across all caps)
  test_criteria   OPTIONAL  string; how to assess whether this capability is CAPABLE
}
```

**Completeness contract.** Every declared CapabilityStatement MUST have a corresponding CapabilityEnvelopeEntry in State.capability_states. An implementation that tracks State.capability_states without an entry for a declared capability MUST surface this as IntegrityGap(kind="capability-state-missing", severity=BLOCKING). **Value weight contract.** value_weight values across all CapabilityStatements in a scope MUST sum to ≤ 1.0; exceeding 1.0 is a configuration error. Uses canonical: Identifier (id), ProductScope (scope), UnitFloat (value_weight). Used in: Config.capability_envelope.capabilities, State.capability_states.

## CapabilityEnvelopeEntry

Records the current status of a single declared CapabilityStatement in the live Product. One entry per declared capability, updated each assessment cycle.

```
CapabilityEnvelopeEntry {
  capability_id          REQUIRED  Identifier; references CapabilityStatement.id
  status                 REQUIRED  CapabilityStatus
  completeness_fraction  REQUIRED  UnitFloat; 0.0 = ABSENT, 1.0 = CAPABLE or beyond
  last_assessed_at       REQUIRED  timestamp
  evidence_refs          OPTIONAL  list[Identifier]; Evidence supporting this status
  notes                  OPTIONAL  string
}
```

**Monotone floor contract.** Once a capability reaches `CAPABLE`, completeness_fraction MUST NOT decrease below 1.0 without a DecisionRecord justifying the regression (analogous to X2 checkpoint gate). **AP9 alignment.** CapabilityEnvelopeEntry.completeness_fraction implements AP9 — Monotone Accumulator for the capability floor. Uses canonical: Identifier (capability_id), UnitFloat (completeness_fraction), TemporalFields (last_assessed_at). Used in: State.capability_states.

## ProductMilestone

A named, gated state that formally represents the Product having reached a validated capable sweet spot. All capability gates, quality gates, and complexity bounds must be simultaneously satisfied for the milestone to be achieved.

```
ProductMilestone {
  id                  REQUIRED  Identifier; prefix "mst"
  name                REQUIRED  string
  description         REQUIRED  string; what "capable" means at this milestone
  capability_gates    REQUIRED  list[Identifier]; CapabilityStatement ids that must be CAPABLE
  quality_gates       OPTIONAL  list[{scope: ProductScope, min_streak: int}]; per-scope quality streak floor
  complexity_ceiling  OPTIONAL  int; maximum product_surface_measure at this milestone
  value_density_floor OPTIONAL  float; minimum value_density at this milestone
  status              REQUIRED  PENDING | ACTIVE | ACHIEVED | SUPERSEDED
  achieved_at         OPTIONAL  timestamp | null; set when status transitions to ACHIEVED
  superseded_by       OPTIONAL  Identifier; next milestone id if status = SUPERSEDED
  version             REQUIRED  string; the version string this milestone produces on achievement (e.g. "v1.0")
  next_milestone_id   OPTIONAL  Identifier | null; milestone to activate on this one's achievement
}
```

**Gate contract.** A ProductMilestone transitions from ACTIVE to ACHIEVED only when ALL of the following are simultaneously true: every capability in capability_gates has status CAPABLE; all quality_gates are satisfied (if declared); product_surface_measure ≤ complexity_ceiling (if declared); value_density ≥ value_density_floor (if declared). Partial satisfaction MUST NOT advance the milestone. **Idempotency contract.** Milestone achievement check is PURE; re-evaluating an ACHIEVED milestone MUST NOT change its status unless a regression invalidates a gate. **Version contract.** Every ProductMilestone MUST declare a version string. On achievement, a ProductVersion record MUST be created carrying this version string. **Chain contract.** When next_milestone_id is non-null, the referenced milestone MUST transition to ACTIVE status upon this milestone's achievement. A chain that contains a cycle (milestone A → B → A) is a configuration error and MUST surface IntegrityGap(kind="milestone-chain-cycle", severity=BLOCKING). Uses canonical: Identifier (id, superseded_by, next_milestone_id), ProductScope (scope in quality_gates), TemporalFields (achieved_at). Used in: Config.capability_envelope.milestones, State (referenced by SweetSpotAssessment).

**Milestone failure modes.** If a milestone gate evaluation fails (required Evidence not present, constraint violated, metric below threshold), the Objective MUST remain at its current milestone. The failure MUST be recorded as an Evidence entry of kind `milestone-gate-failed` with the failing condition. The Objective MUST NOT be advanced past a failed gate autonomously.

**State revertibility.** A milestone advancement is NOT revertible once committed. If incorrect advancement is detected, the operator MUST issue an explicit correction via `urace /amend` to create a compensating Evidence entry. The milestone sequence is append-only.

**Chain integrity validation.** On Objective load, the runtime MUST validate that `next_milestone_id` references form a valid DAG with no cycles and that all referenced milestone IDs exist. A broken chain (dangling reference or cycle) MUST surface a BLOCKING gap of kind `milestone-chain-integrity-failure`.

## SweetSpotAssessment

The output of one execution of the Sweet Spot Evaluation Mechanism. Records the Product's maturity position and value density at a point in time.

```
SweetSpotAssessment {
  id                        REQUIRED  Identifier; prefix "ssa"
  assessed_at               REQUIRED  timestamp
  maturity_level            REQUIRED  ProductMaturityLevel
  capability_completeness   REQUIRED  UnitFloat; fraction of declared capabilities at CAPABLE status
  value_density             REQUIRED  float ≥ 0.0; sum(weight × completeness) / surface_measure
  product_surface_measure   REQUIRED  int ≥ 0; proxy for product surface area (e.g. line count)
  active_milestone_id       OPTIONAL  Identifier | null; current active ProductMilestone if any
  milestone_status          OPTIONAL  PENDING | ACHIEVED | null
  capability_gaps           OPTIONAL  list[Identifier]; CapabilityStatement ids not yet CAPABLE
  over_engineered_caps      OPTIONAL  list[Identifier]; ids with status OVER_ENGINEERED
  notes                     OPTIONAL  string
}
```

**SD contract.** `SD(SweetSpotEvaluationMechanism, S) = True` — all inputs (capability states, product surface, quality state) are locally computable without executor credits. **Frequency contract.** One SweetSpotAssessment per assessment cycle; duplicate assessments within the same cycle MUST be deduplicated by assessed_at. Uses canonical: Identifier (id, active_milestone_id), UnitFloat (capability_completeness, value_density as UnitFloat when ≤ 1.0), TemporalFields (assessed_at). Used in: State.sweet_spot_assessments.

## ValueDensityRecord

A time-series record of product value density. Enables trend analysis: a declining trend after reaching CAPABLE signals over-engineering risk.

```
ValueDensityRecord {
  id               REQUIRED  Identifier; prefix "vdr"
  recorded_at      REQUIRED  timestamp
  value_density    REQUIRED  float ≥ 0.0; same formula as SweetSpotAssessment.value_density
  surface_measure  REQUIRED  int ≥ 0
  delta            OPTIONAL  float | null; change from previous record (positive = improving density)
  trend            OPTIONAL  IMPROVING | NEUTRAL | DECLINING | null
  assessment_id    OPTIONAL  Identifier; SweetSpotAssessment that produced this record
}
```

**AP9 alignment.** value_density SHOULD NOT decline below the best observed value_density at the CAPABLE milestone; a declining trend after CAPABLE is a WARNING. **Trend contract.** `delta` and `trend` MUST be computed relative to the immediately preceding ValueDensityRecord for the same scope; first record has null delta and null trend. Uses canonical: Identifier (id, assessment_id), TemporalFields (recorded_at). Used in: State.value_density_history.

## ProductVersion

A durable versioned record of the Product having achieved a capable sweet spot milestone. One ProductVersion is produced per milestone achievement. ProductVersion is the authoritative answer to "what version is the Product at?"

```
ProductVersion {
  id                      REQUIRED  Identifier; prefix "pver"
  version                 REQUIRED  string; version string declared on the achieved milestone (e.g. "v1.0", "v2.1.0")
  milestone_id            REQUIRED  Identifier; ProductMilestone that produced this version
  achieved_at             REQUIRED  timestamp
  maturity_level          REQUIRED  ProductMaturityLevel; level at achievement time
  capability_completeness REQUIRED  UnitFloat; fraction of capabilities at CAPABLE when achieved
  value_density           REQUIRED  float ≥ 0.0; value_density at achievement time
  product_surface_measure REQUIRED  int ≥ 0; surface measure at achievement time
  next_milestone_id       OPTIONAL  Identifier | null; the milestone activated by this achievement
  notes                   OPTIONAL  string
}
```

**Monotone version contract.** version strings MUST represent a monotonically advancing sequence within a declared versioning scheme. A ProductVersion whose version string is lexicographically ≤ any prior ProductVersion in the same product MUST surface IntegrityGap(kind="non-monotone-version", severity=WARNING). **Immutability contract.** A ProductVersion MUST NOT be modified after creation. It is a durable record of a real achievement, not a current-state summary. **Traceability contract.** ProductVersion.milestone_id MUST reference an existing ProductMilestone with status=ACHIEVED. Uses canonical: Identifier (id, milestone_id, next_milestone_id), UnitFloat (capability_completeness), TemporalFields (achieved_at). Used in: State.product_versions.

## TestRecord

A named, scope-bound behavioral expectation the Product must satisfy. TestRecords are Product citizens — they express what the Product must be able to do, independent of any specific test runner implementation. Linking a TestRecord to a CapabilityStatement enables the Test Coverage Gate mechanism.

```
TestRecord {
  id               REQUIRED  Identifier; prefix "tst"
  name             REQUIRED  string; human-readable test name
  description      REQUIRED  string; what behavioral property this test verifies
  scope            REQUIRED  ProductScope
  kind             REQUIRED  TestKind
  capability_id    OPTIONAL  Identifier | null; CapabilityStatement this test verifies
  status           REQUIRED  ACTIVE | DISABLED
  last_run_id      OPTIONAL  Identifier | null; most recent TestRunRecord id
}
```

**Coverage contract.** Every CapabilityStatement with a non-null test_criteria SHOULD have at least one TestRecord of kind CAPABILITY_GATE or ACCEPTANCE with capability_id pointing to it. A CapabilityStatement with test_criteria and no associated TestRecords MUST surface IntegrityGap(kind="capability-without-test-record", severity=WARNING). **Ownership contract.** TestRecords are authored by the authoritative source or by URACE under explicit authority; they MUST NOT be autonomously created, modified, or deleted without a DecisionRecord. Uses canonical: Identifier (id, capability_id, last_run_id), ProductScope (scope). Used in: State (via TestRunRecord.test_ids), CapabilityStatement (via test_criteria reference).

## TestRunRecord

The result of executing a set of TestRecords. A TestRunRecord is an Evidence-equivalent citizen: its verdict feeds directly into QualityDelta classification and CapabilityEnvelopeEntry status updates.

```
TestRunRecord {
  id                    REQUIRED  Identifier; prefix "trr"
  run_at                REQUIRED  timestamp
  scope                 REQUIRED  ProductScope
  kind                  REQUIRED  TestKind; kind of tests that were run
  total                 REQUIRED  int ≥ 0
  passed                REQUIRED  int ≥ 0
  failed                REQUIRED  int ≥ 0
  skipped               REQUIRED  int ≥ 0
  errored               REQUIRED  int ≥ 0
  verdict               REQUIRED  TestVerdict; aggregate verdict for this run
  capability_ids_covered OPTIONAL list[Identifier] | null; capabilities whose tests were run
  test_ids              OPTIONAL  list[Identifier] | null; TestRecord ids executed in this run
  executor_id           OPTIONAL  string | null; executor or tool that ran the tests
  notes                 OPTIONAL  string
}
```

**Verdict contract.** `verdict = PASS ↔ failed == 0 ∧ errored == 0`. A run with any failed or errored test MUST carry verdict=FAIL or verdict=ERROR respectively. **Count contract.** `total = passed + failed + skipped + errored`. A TestRunRecord that violates this MUST surface IntegrityGap(kind="test-run-count-mismatch", severity=BLOCKING). **QualityDelta contract.** Every TestRunRecord with verdict=FAIL or verdict=ERROR MUST produce a concurrent QualityDelta(classification=REGRESSION) for each scope in capability_ids_covered. A TestRunRecord with verdict=PASS where the prior verdict for those capabilities was FAIL MUST produce QualityDelta(classification=IMPROVEMENT). Uses canonical: Identifier (id), ProductScope (scope), TemporalFields (run_at). Used in: State.test_run_records.

---

# 62e. Infrastructure Schemas

Infrastructure schemas document data structures used to connect lifecycle subsystems (the "glue"). They are not produced by Executor calls; they are written by the lifecycle controller itself as part of persistence, locking, crash recovery, and condition surfacing.

## Transaction

The on-disk journal that enables crash-consistent rollback for any Operation. The Transaction exists as a JSON file on disk between the `PREPARED` and `VALIDATED` phases.

```
Transaction {
  id          REQUIRED  Identifier
  operation   REQUIRED  string; Operation id this transaction serves
  created_at  REQUIRED  timestamp; when journal was first written
  phase       REQUIRED  PREPARED | APPLYING | APPLIED | VALIDATED
  before      REQUIRED  dict[relative_path → file_content]; snapshot before mutation
  after       REQUIRED  dict[relative_path → file_content]; intended content after mutation
  applied     REQUIRED  list[relative_path]; files successfully written so far (grows during APPLYING)
}
```

Uses canonical: Identifier, TemporalFields (created_at).

**Journal durability contract.** The journal MUST be written atomically to disk at each phase transition before the transition takes effect. A phase that is not durably recorded is not complete. **Recovery contract.** On lifecycle start, if a Transaction journal exists on disk, the lifecycle MUST recover it per the phase rules in §62c Transaction Mechanism before any new work begins. **Removal contract.** The journal file MAY be removed only after phase `VALIDATED` is durably recorded in lifecycle state. Removing it before `VALIDATED` is a recovery condition.

## OwnershipMarker

The content of the exclusive state lock file (`{state_path}.lock`). Guarantees single-writer access to the state file.

```
OwnershipMarker {
  pid         REQUIRED  int; OS process ID of the owning lifecycle process
  started_at  REQUIRED  timestamp; when the lock was acquired
}
```

Uses canonical: TemporalFields (started_at as established_at).

**Write contract.** MUST be written as a JSON object using an atomic exclusive-create operation (one that succeeds only if the file does not yet exist and fails if it does, with no window for a race condition). An implementation MUST use the platform's strongest available single-writer primitive for this write. **Liveness contract.** If the PID in the marker is not a live OS process, the marker is stale and MAY be removed after appending a StaleLockObservation record. **Legacy compatibility.** If JSON parsing of the marker file fails, the file content MUST be treated as a decimal PID string (legacy plain-text format) for backward compatibility.

## StaleLockObservation

An audit record appended to `stale-lock-observations.jsonl` when a stale OwnershipMarker is removed.

```
StaleLockObservation {
  at           REQUIRED  timestamp; when stale marker was detected
  stale_pid    REQUIRED  int; the PID read from the stale marker
  lock         REQUIRED  string; absolute file path of the removed lock file
  disposition  REQUIRED  string; always "removed" in current implementation
}
```

Uses canonical: TemporalFields (at as recorded_at). Stored as append-only JSONL (one JSON object per line). Checkpoint records are themselves append-only (AP3 — Append-Only Log, §62i) and MUST NOT be modified after creation.

## IntegrityGap

A named surfaced condition record representing a detected violation of a lifecycle invariant. IntegrityGaps MUST be surfaced in `urace check` and `urace vitals` output. BLOCKING gaps MUST halt all autonomous Operations until resolved.

```
IntegrityGap {
  id           REQUIRED  Identifier
  kind         REQUIRED  string; machine-readable condition code (see known kinds below)
  at           REQUIRED  timestamp; when gap was first detected
  description  REQUIRED  string; human-readable explanation
  severity     REQUIRED  WARNING | BLOCKING
  source       REQUIRED  string; subsystem that detected this gap
  active       REQUIRED  bool; true = condition is still present
  resolved_at  OPTIONAL  timestamp | null; when cleared
  evidence_id  OPTIONAL  string; Evidence id if a parallel Evidence record was emitted
}
```

Uses canonical: Identifier, TemporalFields (at as created_at, resolved_at).

**Known IntegrityGap kinds:**

| kind | severity | triggering condition |
|------|----------|----------------------|
| `governance-anchor-drift` | BLOCKING | DestinationAnchor digest mismatch at cycle start |
| `ledger-integrity-violation` | BLOCKING | Rule Ledger structural invariant broken |
| `transaction-recovery-required` | BLOCKING | Unresolved Transaction journal found at start |
| `wake-integrity-gap` | WARNING | WakeRegistration cannot be verified in environment |
| `stale-validation` | WARNING | PendingValidation record exceeded expires_at |
| `reconciliation-stalled` | BLOCKING | RECONCILING hit declared attempt ceiling |
| `repair-exhausted` | BLOCKING | REPAIRING hit declared attempt ceiling |
| `ownership-boundary-indeterminate` | BLOCKING | Lock liveness cannot be established |
| `state-digest-divergence` | BLOCKING | Checkpoint/Change digest chain is broken |
| `compaction-manifest-divergence` | BLOCKING | CompactionManifest version or digest inconsistency, or ARCHIVE-mode archive file missing or unreadable |
| `retention-policy-violated` | WARNING | Governed list exceeds configured or default ceiling without a CompactionEvent |
| `cognitive-resume-stale` | WARNING | CognitiveResumeContext.state_digest does not match current state on Executor initialization |
| `decision-record-provenance-revised` | WARNING | Active Objectives or Operations rely on a DecisionRecord with provenance_status = PROVENANCE_REVISED |
| `decision-reasoning-cycle`           | WARNING | A cycle detected in DecisionRecord.prior_decision_refs chain (A → … → A) |

**Resolution contract.** An IntegrityGap in `active: true` state MUST remain in the State Document until an explicit resolution event clears it. Clearing MUST set `active: false` and `resolved_at`. Autonomous inference of resolution without an attributable event MUST NOT be used to clear a BLOCKING gap.

## CompactionEvent

An infrastructure record documenting a single compaction act on an accumulating list field. Written by the lifecycle controller and appended to the CompactionManifest. CompactionEvent records form the authoritative audit trail for all compaction that has occurred in the state space.

```
CompactionEvent {
  id                   REQUIRED  Identifier; prefix "cmp"
  target_state_path    REQUIRED  string; relative path of the state file being compacted
  target_field         REQUIRED  string; dot-path of the list field compacted (e.g. "failures")
  compacted_at         REQUIRED  timestamp; when compaction was executed
  record_count_before  REQUIRED  int ≥ 0; count of entries in the field before compaction
  record_count_after   REQUIRED  int ≥ 0; count of entries after (includes any CompactionSummary)
  compaction_mode      REQUIRED  ARCHIVE | ROLLING_EVICTION
  archive_path         OPTIONAL  string; relative path to the archive file; REQUIRED when
                                 compaction_mode is ARCHIVE; absent when ROLLING_EVICTION
  original_digest      REQUIRED  DigestValue; SHA-256 of the canonical serialization of the records
                                 removed; MUST match the corresponding CompactionSummary.original_digest
  authorized_by        REQUIRED  string; operator Input id for explicit compact; or
                                 "retention_policy:{RetentionPolicy.id}" for policy-triggered
  executor             OPTIONAL  ExecutorAttribution; present only if an Executor assisted with
                                 summarization during this compaction (e.g. to produce summary_text)
}
```

Uses canonical: Identifier (id), DigestValue (original_digest), ExecutorAttribution (executor), TemporalFields (compacted_at as created_at).

**Append-only contract.** CompactionEvent records MUST NOT be removed from the CompactionManifest after written. The manifest is the durable audit log of all compaction acts. **Digest-match contract.** `original_digest` in a CompactionEvent MUST equal `original_digest` in the corresponding CompactionSummary in the live list. A mismatch is a `compaction-manifest-divergence` BLOCKING IntegrityGap. **Archive durability contract.** When `compaction_mode` is ARCHIVE, the archive file MUST be written and fsynced before the CompactionEvent is appended to the manifest, and the manifest MUST be updated before the live list is mutated. A process interrupted between archive write and list mutation MUST be recovered via the manifest: the lifecycle detects the orphan archive and restores the list from it rather than treating the archive as garbage.

## CompactionManifest

The authoritative on-disk registry of all CompactionEvents that have occurred in this lifecycle state space. Stored at `{state_path}/compaction-manifest.json`. Loaded at cycle start for integrity verification.

```
CompactionManifest {
  id          REQUIRED  Identifier; prefix "man"
  version     REQUIRED  int ≥ 1; monotonically incremented on each event appended
  updated_at  REQUIRED  timestamp
  events      REQUIRED  list[CompactionEvent]; append-only ordered log of all compaction acts
}
```

Uses canonical: Identifier (id), TemporalFields (updated_at).

**Initialization contract.** A lifecycle state space that has never been compacted MUST NOT have a manifest file; the file's absence means no compaction has occurred. Creating an empty manifest proactively is not permitted. **Append-only contract.** The `events` list MUST NOT be modified; only appended. Modifying, removing, or reordering a CompactionEvent is a Ledger integrity violation. **Version contract.** `version` MUST equal `len(events)`; a manifest where this invariant is broken is corrupt and MUST be surfaced as a `compaction-manifest-divergence` BLOCKING IntegrityGap. **Startup verification contract.** At cycle start, if a manifest exists, the lifecycle MUST verify that each ARCHIVE-mode CompactionEvent has an accessible archive file at `archive_path`. A missing archive is a `compaction-manifest-divergence` BLOCKING IntegrityGap unless all CompactionSummary entries governed by that event have `is_decompactable: false`.

## CognitiveResumeContext

The minimum structured context required to resume a lifecycle cycle after an Executor cognitive reset — the loss of an Executor's working context through replacement, context-window eviction, restart, or any mechanism that discards in-process reasoning without modifying durable state. Written by the lifecycle controller at each cycle boundary and injected as structured input to any Executor that is initialized or reinitialized.

```
CognitiveResumeContext {
  id                   REQUIRED  Identifier; prefix "crc"
  generated_at         REQUIRED  timestamp; when this context was written
  cycle_phase          REQUIRED  ASSESSING | PLANNING | EXECUTING | VALIDATING | DORMANT;
                                 the lifecycle phase at time of generation
  active_objective_id  OPTIONAL  string | null; Objective id in progress; null if none
  active_operation_id  OPTIONAL  string | null; Operation id in progress; null if none
  pending_transaction  OPTIONAL  Identifier | null; Transaction id awaiting recovery; null if none
  pending_validations  REQUIRED  list[string]; Observation ids currently awaiting validation
  blocking_gaps        REQUIRED  list[string]; IntegrityGap ids with severity BLOCKING and active=true
  state_digest         REQUIRED  DigestValue; SHA-256 of the full URACE state document at generation
  resume_summary       OPTIONAL  string; executor-agnostic natural-language summary of current
                                 lifecycle context; MUST NOT expose hidden chain-of-thought;
                                 MUST be the reviewable basis for resumption, not reasoning detail
}
```

Uses canonical: Identifier (id, pending_transaction), DigestValue (state_digest), TemporalFields (generated_at as created_at).

**Generation contract.** The lifecycle controller MUST generate a fresh CognitiveResumeContext at every cycle boundary: assessment start, planning start, execution start, validation complete, dormancy entry. A CRC whose `state_digest` does not match current state MUST NOT be injected; doing so is a `cognitive-resume-stale` WARNING IntegrityGap. **Injection contract.** The lifecycle controller MUST inject the current CRC alongside the state document as structured input whenever an Executor is initialized or reinitialized. The Executor MUST NOT be required to infer current lifecycle phase from the state document alone. **Stateless-resumable contract.** An Executor invocation MUST be resumable from the injected CRC plus current durable state without any in-process memory from a prior invocation. An Executor that requires recapitulation of prior reasoning not present in durable state violates this contract and is not replaceable per §75. **No-duplication contract.** The CRC MUST NOT substitute for a DecisionRecord. Reasoning behind a decision MUST still be written to a DecisionRecord (§62d); the CRC is a reconstitution aid, not an authorization record. **`lifecycle_state` key contract.** The `cycle_phase` field MUST be derived from the canonical `state["lifecycle_state"]` field in durable state. An implementation that reads `lifecycle_status`, `status`, or any other key as the primary source for `cycle_phase` derivation violates this contract; those keys MUST NOT serve as fallbacks when `lifecycle_state` is absent.

**Injection contract (detailed).** At the start of each Executor invocation, the runtime MUST serialize the current CognitiveResumeContext to JSON and prepend it to the Executor's context under the key `__crc__`. The serialized form MUST include `schema_version` matching the spec version string (e.g. `"2026-10-16-r58"`). If the Executor returns a CRC object, the runtime MUST deserialize it and validate `schema_version` before applying any field updates.

**Version-mismatch recovery.** If the returned CRC `schema_version` does not match the active spec version, the runtime MUST: (1) retain the current CRC unchanged; (2) surface a WARNING gap of kind `crc-version-mismatch`; (3) continue the lifecycle using the retained CRC. The runtime MUST NOT silently accept fields from a mismatched CRC.

**Context-window overage.** If the serialized CRC size exceeds `Config.context_budget.hard_cap_fraction` of the estimated context window, the runtime MUST invoke the Context Budget Mechanism (§62c CBM) to evict lower-tier CRC fields before injection. Fields at tier T3 (historical summaries) MUST be evicted first, then T2, then T1. The runtime MUST NOT evict T0 fields (active objectives, active constraints, active authority). If eviction cannot bring the CRC within budget, a BLOCKING gap of kind `crc-context-overflow` MUST be surfaced.

## CompactionIndex

A per-archive searchable index persisted as `{archive_path}.idx.json`. Enables O(1) record lookup by id, kind, and time-bucket without reading or parsing the full archive file. Written atomically alongside the archive at compaction time and updated atomically at decompaction time or amendment time.

```
CompactionIndex {
  compaction_event_id  REQUIRED  Identifier; the CompactionEvent this index serves
  archive_path         REQUIRED  string; absolute path to the archive file indexed
  generated_at         REQUIRED  timestamp; when the index was last written or updated
  record_count         REQUIRED  int ≥ 0; must match the archive's record count
  id_to_offset         REQUIRED  dict[string → int]; map of record id to byte offset in archive
                                  JSON array; enables O(1) seek to a single record
  kind_to_ids          REQUIRED  dict[string → list[string]]; map of kind to list of ids in archive
  time_buckets         OPTIONAL  dict[string → list[string]]; map of ISO-date ("YYYY-MM") to ids;
                                 enables time-range narrowing without full scan
}
```

**Atomicity contract.** The index MUST be written to a `.tmp` file and renamed atomically after the archive is fsynced. An index that diverges from its archive (different `record_count`, stale `generated_at`) is advisory-stale and MUST be regenerated before any incremental decompaction. **Read-optional contract.** The index is a performance aid, not a correctness prerequisite. All operations that use it MUST fall back to a sequential archive scan if the index is absent or stale. **No-independent-state contract.** The index MUST NOT be the authoritative source for any lifecycle decision; the archive file and CompactionManifest are authoritative. Uses canonical: Identifier (compaction_event_id), TemporalFields (generated_at as created_at).

## ArchiveAmendment

A single amendment record appended to `{archive_path}.amendments.jsonl` when a record in an archive is modified in place (e.g., flagging a DecisionRecord as PROVENANCE_REVISED) without a full decompaction round-trip. The amendment log is the only permitted mechanism for modifying archived records under ARCHIVE mode.

```
ArchiveAmendment {
  id              REQUIRED  Identifier; prefix "amd"
  archive_path    REQUIRED  string; absolute path to the amended archive file
  record_id       REQUIRED  string; id of the record within the archive that was amended
  amended_at      REQUIRED  timestamp; when this amendment was written
  amendment_kind  REQUIRED  PROVENANCE_REVISED | SUPERSEDED | CUSTOM
  amendment_note  REQUIRED  string; human-readable description of what changed and why
  authorized_by   REQUIRED  string; inbox Input id or "operator:{id}" of who authorized this
  before_digest   REQUIRED  DigestValue; SHA-256 of the record's canonical JSON before amendment
  after_digest    REQUIRED  DigestValue; SHA-256 of the record's canonical JSON after amendment
}
```

**Append-only contract.** Amendment records MUST NOT be removed or modified after being written. The amendment log is an audit trail. **No-CompactionSummary-mutation contract.** An ArchiveAmendment modifies a record within an archive file; it does NOT modify the CompactionSummary in the live list, the CompactionEvent in the manifest, or the `original_digest`. The `original_digest` remains a commitment to the pre-compaction snapshot, not the post-amendment state. **Amendment vs decompaction contract.** ArchiveAmendment is appropriate for lightweight status changes (e.g., provenance revision). For structural changes that would alter `original_digest` verification, full decompaction (`urace decompact`) is required. Uses canonical: Identifier (id), DigestValue (before_digest, after_digest), TemporalFields (amended_at as created_at).

## SpecAuditState

The persisted audit state record written to `state["spec_audit_state"]` after every §80 structural audit. Enables the lifecycle to determine whether a fresh audit is due on each assessment cycle by comparing `spec_version` to the current spec version. Distinct from the `spec-structural-audit` Evidence record: the Evidence record is an append-only audit-trail entry; this record is the mutable current-state snapshot, replaced on each audit run.

```
SpecAuditState {
  spec_version                   REQUIRED  string; spec version string audited (e.g. "2026-10-11-r7")
  last_audited_at                REQUIRED  timestamp; when this audit was completed
  section_count                  REQUIRED  int ≥ 1; number of numbered sections found in spec
  fence_parity_even              REQUIRED  bool; true when total fence count is even
  rfc2119_totals                 REQUIRED  dict[verb → int]; global RFC 2119 verb counts across all sections
  normative_density_per_section  REQUIRED  float ≥ 0.0; average normative-rule count per section
  high_ambiguity_sections        REQUIRED  list[string]; section labels classified as high-ambiguity
  medium_ambiguity_sections      REQUIRED  list[string]; section labels classified as medium-ambiguity
  top_gap_sections               REQUIRED  list[dict]; up to 5 sections with highest semantic-gap density
                                           each entry: {section, title, gap_count, normative_rule_count}
}
```

**Freshness contract.** On each assessment cycle, the lifecycle MUST compare `spec_audit_state.spec_version` to the running spec version. When they differ, a fresh audit is due before the next executor discovery cycle. When no `spec_audit_state` exists, a fresh audit is due immediately. **Determinism contract.** Given the same spec text, two audit runs MUST produce identical `SpecAuditState` values. Any dependency on execution time, random state, or external resources violates this contract. Uses TemporalFields: last_audited_at (as created_at for the audit run).

## ProductMaturityLevel

The current position of a Product on the capable evolution curve.

```
ProductMaturityLevel {
  values:
    BOOTSTRAPPING  — capabilities not yet defined or largely absent
    FORMING        — capabilities being built; completeness below target
    CAPABLE        — all required capabilities present; complexity within envelope;
                     value density above floor — the sweet spot
    OPTIMIZED      — capable state with demonstrably improved value density
    OVER_ENGINEERED — capability or complexity exceeds envelope ceiling;
                      value density declining
}
```

**Transition contract.** BOOTSTRAPPING → FORMING → CAPABLE is the nominal forward path. CAPABLE → OPTIMIZED is valid. CAPABLE or OPTIMIZED → OVER_ENGINEERED requires corrective action. Any maturity level may regress to FORMING if a capability gate fails. OVER_ENGINEERED MUST NOT advance to CAPABLE without a COMPLEXITY_REDUCING change bringing surface back within the ceiling.

## CapabilityStatus

The status of a single CapabilityStatement in the current Product state.

```
CapabilityStatus {
  values:
    ABSENT          — capability not present in Product
    PARTIAL         — capability partially implemented; completeness_fraction in (0.0, 1.0)
    CAPABLE         — capability fully present; completeness_fraction == 1.0
    OVER_ENGINEERED — capability present but implementation exceeds its declared scope or value weight
}
```

**Invariant.** `completeness_fraction == 1.0 ↔ status IN {CAPABLE, OVER_ENGINEERED}`. A status of OVER_ENGINEERED does not decrease capability_completeness count but MUST trigger a WARNING.

## CapabilityContributionKind

The role of an Objective or Operation with respect to the Product's capability evolution.

```
CapabilityContributionKind {
  values:
    CAPABILITY_DEFINING    — establishes a new required capability; authorized only during BOOTSTRAPPING/FORMING
    CAPABILITY_COMPLETING  — brings a PARTIAL capability to CAPABLE
    QUALITY_IMPROVING      — raises quality of existing CAPABLE capability without expanding surface
    COMPLEXITY_REDUCING    — reduces surface while preserving capability; always authorized
    MILESTONE_TARGETING    — explicitly targets achieving a declared ProductMilestone gate
}
```

**Authorization contract.** `CAPABILITY_DEFINING` MUST NOT be selected autonomously when Product maturity_level is CAPABLE or OPTIMIZED unless a governing authority explicitly authorizes capability scope expansion (recorded as DecisionRecord(kind=CAPABILITY_SCOPE_EXPANSION)). `QUALITY_IMPROVING` and `COMPLEXITY_REDUCING` are always autonomously authorized.

## TestKind

The kind of behavioral expectation a TestRecord represents.

```
TestKind {
  values:
    UNIT             — tests a single unit in isolation
    INTEGRATION      — tests a component interaction
    BEHAVIORAL       — tests end-to-end user-visible behavior
    ACCEPTANCE       — tests a capability acceptance criterion (maps to CapabilityStatement)
    CAPABILITY_GATE  — a gate test: if PASS, the associated capability MUST be marked CAPABLE
}
```

**Gate semantics.** A TestRecord with kind=CAPABILITY_GATE whose most recent TestRunRecord verdict is PASS MUST result in the associated capability's completeness_fraction being updated to 1.0 and status to CAPABLE at the next assessment cycle. This is the only autonomous mechanism that advances a capability to CAPABLE; all other transitions require operator action or explicit Evidence.

## TestVerdict

The aggregate result of a TestRunRecord.

```
TestVerdict {
  values:
    PASS   — all tests passed (failed == 0 AND errored == 0)
    FAIL   — one or more tests failed
    ERROR  — one or more tests errored (infrastructure failure, not behavioral failure)
    SKIPPED — all tests were skipped (no meaningful result)
}
```

---

# 62f. Compaction and Retention

This section implements **AP21 — Compaction** (§62i). The Compaction and Retention system governs growth management for accumulating list fields in URACE persistent state. It defines which lists may be bounded, how compaction is authorized and sequenced, how lossless decompaction is guaranteed for ARCHIVE-mode compactions, and what information must survive any compaction mode.

## Governed fields

A list field is governed by this system when it: appears in a citizen or infrastructure schema defined in §62b–§62e; accumulates entries over the lifecycle lifetime without a natural closure condition; and does not have a fixed maximum cardinality established by its schema.

Default governance table:

| Field | Schema | Default ceiling | Default mode |
|-------|--------|----------------|-------------|
| `ExternalMetricState.latest` | §62b | 1 000 entries | ROLLING_EVICTION |
| `ExecutorState.failures` | §62b | 500 entries | ARCHIVE |
| `ExecutorState.executor_calls` | §62b | 35-day rolling window | ROLLING_EVICTION |
| `ProviderStatus.attempt_history` | §62d | 35-day rolling window | ROLLING_EVICTION (integral) |
| `StaleLockObservation` JSONL | §62e | 10 MB file | ARCHIVE |
| `CompactionManifest.events` | §62e | — | PROHIBITED |
| `ChangeHistoryEntry` lists | §62d | — | PROHIBITED |
| `DecisionRecord` lists | §62d | 2 000 entries | ARCHIVE |
| `StatusTransition` lists | §62d | 500 per citizen | ARCHIVE |
| `integrity_gaps` | §62b | 500 entries | ROLLING_EVICTION |
| `status_transitions` | §62b | 500 entries | ARCHIVE |
| `assessment_records` | §62b | 1 000 entries | ARCHIVE |
| `processed_input_ids` | §62b | 1 000 entries | ROLLING_EVICTION |
| `chunks` | §62f | 1 000 entries | ARCHIVE |

Implementations MAY configure different ceilings via RetentionPolicy records established through an attributable operator input. A RetentionPolicy MUST NOT change the mode of a PROHIBITED field.

## Lossless-decompaction guarantee

For any ARCHIVE-mode compaction the following sequence MUST be observed:

1. Original records are serialized canonically, their SHA-256 is computed as `original_digest`.
2. Originals are written intact to `archive_path` and fsynced.
3. A CompactionEvent is appended to the CompactionManifest (creating the manifest if absent).
4. A CompactionSummary with `is_decompactable: true` and matching `original_digest` is inserted into the live list at the position of the first compacted record.
5. The compacted records are removed from the live list.

`urace decompact <compaction_event_id>` reverses this sequence: loads the archive, verifies the digest against `CompactionSummary.original_digest`, removes the CompactionSummary, inserts the original records at the same position, and appends an inverse CompactionEvent to the manifest. A decompacted list is semantically identical to its pre-compaction state. A decompaction that fails digest verification MUST surface as a `compaction-manifest-divergence` BLOCKING IntegrityGap and MUST NOT partially modify the live list.

## Semantic minimum preservation

Regardless of compaction mode, the following MUST survive any compaction and MUST be queryable without decompaction:

- Count of original records (`CompactionSummary.record_count`)
- Temporal span covered (`CompactionSummary.time_range`)
- Cryptographic commitment to the originals (`CompactionSummary.original_digest`)
- Restorability flag (`CompactionSummary.is_decompactable`)
- Authorization basis (`CompactionEvent.authorized_by`)

Any aggregation query over a governed list MUST account for CompactionSummary entries using their `record_count` and `time_range`; they MUST NOT be skipped or treated as zero.

## Eligibility criteria

A record in a governed list is eligible for compaction when it satisfies at least one of the following:

1. **Entry-count ceiling**: the list length exceeds `RetentionPolicy.max_entries`, and the record is among the oldest entries (lowest `created_at` or equivalent timestamp field) beyond the ceiling.
2. **Age ceiling**: `RetentionPolicy.max_age_days` is set and the record's timestamp field is older than `max_age_days` calendar days before the current boundary.

An implementation MUST evaluate eligibility deterministically: entry-count eligibility MUST prefer the oldest entries, and age eligibility MUST use UTC timestamps. When both criteria apply, a record eligible under either is eligible.

## Lifecycle boundary requirement

Compaction MUST occur only at a safe lifecycle boundary: after a cycle's Checkpoint is accepted and before the next cycle begins. Compaction MUST NOT occur during an active Transaction or while `CognitiveResumeContext.pending_transaction` is non-null. Violating this rule is a cycle-integrity violation and MUST be surfaced as a `compaction-manifest-divergence` BLOCKING IntegrityGap.

**Destination anchor guard.** Compaction MUST NOT execute if `state["lifecycle_state"] == "BLOCKED"` due to a `governance-anchor-drift` gap. A blocked lifecycle has an unverified destination anchor; compaction in this state may produce records that cannot be attributed to a verified governance baseline. An attempt to compact while BLOCKED on anchor drift MUST emit `compaction-blocked-on-anchor-drift` WARNING IntegrityGap and MUST NOT proceed.

**CheckpointRecord baseline requirement.** The "last accepted Checkpoint" referenced in this lifecycle boundary requirement is the most recent CheckpointRecord (§62b) with `kind=accepted-product-change` in `State.checkpoints`. A compaction that cannot identify a prior accepted-product-change Checkpoint MUST NOT proceed (bootstrap Checkpoints do not satisfy this requirement for compaction authorization).

## Authorization model

Compaction is authorized in exactly two ways:

1. **Policy-triggered**: a RetentionPolicy with `compaction_mode != PROHIBITED` whose threshold is exceeded. The RetentionPolicy MUST have been established through an attributable operator input or bootstrap configuration. `CompactionEvent.authorized_by` MUST be `retention_policy:{RetentionPolicy.id}`.
2. **Explicit operator command**: `urace compact <field-path>` processed through the inbox at the next safe boundary. `CompactionEvent.authorized_by` MUST be the inbox Input id.

The lifecycle controller MUST NOT self-authorize compaction outside these two paths.

**Compaction authorization staleness.** A CompactionEvent whose `authorized_at` timestamp is more than 86400 seconds (24 hours) before the actual compaction execution MUST be treated as stale. Stale authorization MUST NOT proceed. The implementation MUST re-request authorization (re-trigger RetentionPolicy threshold check or re-queue operator command via inbox). Stale authorization without re-request MUST emit `compaction-authorization-stale` WARNING IntegrityGap.

## urace compact

```
urace compact <field-path> [--dry-run] [--mode ARCHIVE|ROLLING_EVICTION]
```

Initiates compaction of an accumulating list field. MUST be rejected if the field's RetentionPolicy has `compaction_mode: PROHIBITED` or if the field is not in the default governance table above. `--dry-run` reports eligible records and would-be CompactionSummary without committing. The command is written to the inbox and processed at the next safe lifecycle boundary; it MUST NOT execute synchronously within the same cycle that receives it.

## urace decompact

```
urace decompact <compaction-event-id> [--record-id <id>]
```

**Full decompaction** (no `--record-id`): Restores all original records from an ARCHIVE-mode CompactionEvent. MUST be rejected if `CompactionEvent.compaction_mode` is ROLLING_EVICTION, the archive file is missing or unreadable, or digest verification fails. On success: removes the CompactionSummary, inserts restored records at the same position, and records an inverse CompactionEvent in the manifest with `authorized_by` set to the inbox Input id. After decompaction the live list is identical to its pre-compaction state.

**Incremental decompaction** (`--record-id <id>`): Extracts a single record from an ARCHIVE-mode CompactionEvent without restoring the full segment. MUST be rejected under the same conditions as full decompaction. On success: the single record is returned as structured output (it is NOT re-inserted into the live list); the CompactionSummary and archive file are left intact. The operation MUST NOT modify the live list or the manifest. `CompactionSummary.record_ids` MUST contain the requested id; if absent, the implementation MUST fall back to a sequential archive scan. A record-id not present in the archive is a non-fatal error; the command exits with a descriptive error and no state modification.

**Re-ingestion contract.** Full re-ingestion of a compacted field segment back into active state follows the Re-Ingestion Mechanism (§62c), which wraps the Transaction Mechanism and enforces digest verification. `urace decompact` is the user-facing command; the Re-Ingestion Mechanism is the underlying mechanism.

## urace amend

```
urace amend <compaction-event-id> <record-id> --notice <text>
```

Applies an in-place amendment to a single record within an ARCHIVE-mode CompactionEvent's archive file. Appends an ArchiveAmendment to `{archive_path}.amendments.jsonl`. Does NOT modify the CompactionSummary or CompactionManifest (the `original_digest` commitment is preserved). MUST be rejected if: the compaction event is ROLLING_EVICTION; the archive file is missing or unreadable; the record-id is not present in the archive. The amendment is written to the inbox and processed at the next safe lifecycle boundary. Use this command to flag a DecisionRecord as PROVENANCE_REVISED while it remains in archive storage, without a full decompaction round-trip.

## Objective-Lifecycle Chunking (optional)

Chunking is an opt-in compaction strategy that groups records by Objective lifecycle phase rather than age or count. Enabled via `Config.compaction.chunking_enabled: true`.

### ChunkingPolicy

**Construct metadata.** kind: Schema · tier: COMPOSITIONAL · standalone: false

Extends: CitizenBase

```
ChunkingPolicy {
  id          REQUIRED  stable identifier
  created_at  REQUIRED  ISO-8601; creation timestamp
  updated_at  REQUIRED  ISO-8601; last mutation timestamp
  enabled     REQUIRED  boolean; activates chunking; default false
  chunk_by    REQUIRED  enum: COUNT | AGE | OBJECTIVE_LIFECYCLE; default COUNT
  max_chunks  OPTIONAL  integer; ceiling on active chunks per field; overflow uses age-based compaction
}
```

### Chunk

**Construct metadata.** kind: Schema · tier: COMPOSITIONAL · standalone: false

Extends: CitizenBase
Implements: GoverningRecord

```
Chunk {
  id                REQUIRED  stable identifier; prefix "chunk-"
  created_at        REQUIRED  ISO-8601; creation timestamp
  updated_at        REQUIRED  ISO-8601; last mutation timestamp
  field_path        REQUIRED  string; state path (e.g., "decision_records")
  record_ids        REQUIRED  list[string]; record ids in this chunk
  time_range        REQUIRED  object; {earliest: timestamp, latest: timestamp}
  record_count      REQUIRED  integer
  original_digest   REQUIRED  string; SHA-256 of archived records
  is_decompactable  REQUIRED  boolean; true when objective_status=completed or cancelled
  authorized_by     REQUIRED  string
  status            REQUIRED  enum: ACTIVE | ARCHIVED
  objective_id      OPTIONAL  string; Objective.id (present if chunk_by=OBJECTIVE_LIFECYCLE)
  objective_status  OPTIONAL  string; planned|active|completed|cancelled
  archived_at       OPTIONAL  ISO-8601; when moved to archive
  authority_basis   OPTIONAL  string; authorizing rule id or authority scope (GoverningRecord)
  scope             OPTIONAL  string; governance scope affected (GoverningRecord)
  established_at    OPTIONAL  ISO-8601; when chunk was established (GoverningRecord)
}
```

**Chunking algorithm (chunk_by=OBJECTIVE_LIFECYCLE):**
1. Group records by (objective_id, objective_status)
2. For groups where objective_status ∈ {completed, cancelled}: create Chunk with is_decompactable=true; archive records; insert ChunkSummary placeholder
3. For groups where objective_status=active: create Chunk with is_decompactable=false; do NOT archive
4. On Objective status → completed: mark its Chunk is_decompactable=true, set archived_at, archive on next safe boundary

**Decompaction (chunking):**
`urace decompact <chunk-id>` restores all records for (objective_id, objective_status) as a unit.
If decision_record.prior_decision_refs crosses chunk boundary, both chunks MUST be restored before traversal.

**Migration:** CompactionEvent.chunk_format: LEGACY_TIMESTAMP | OBJECTIVE_LIFECYCLE. Existing archives use LEGACY_TIMESTAMP; chunking-aware decompaction handles both.

**Used in:** §62f compaction commands, §62g Justification Chain traversal

**Scope:** Compaction domain (§62f)

---

# 62g. Justification System

This section implements **AP23 — Justification Chain** (§62i). The Justification System provides structured traversal of the reasoning chain behind any consequential decision in the lifecycle. It operates entirely from durable state — no Executor invocation is required. The system is usable even when the deciding Executor is no longer available, making it executor-agnostic within the meaning of §75.

## Reasoning chain structure

A reasoning chain rooted at DecisionRecord `D` is the directed acyclic graph formed by following `prior_decision_refs` recursively. `D.prior_decision_refs` points to the direct antecedents. Each antecedent may have its own `prior_decision_refs`, extending the chain. The chain terminates at records with no `prior_decision_refs` or records that have been compacted (present in archive only).

A cycle in the chain (`D` → ... → `D`) MUST be detected and surfaced as a `decision-reasoning-cycle` WARNING IntegrityGap with `severity: WARNING`. The traversal MUST halt at the cycle boundary rather than looping.

## Semantic minimum visible at each node

Without decompaction, the following are visible at each chain node from durable state or CompactionSummary:

| Field | Source |
|-------|--------|
| Record id | `DecisionRecord.id` or `CompactionSummary.record_ids` |
| Kind | `DecisionRecord.kind` or `CompactionSummary.kinds` |
| Subject | `DecisionRecord.subject` (live only; unavailable in compacted summary) |
| Decided at | `DecisionRecord.decided_at` or `CompactionSummary.time_range` |
| Provenance status | `DecisionRecord.provenance_status` (live only) |
| Reasoning steps | `DecisionRecord.reasoning_steps` (live only) |

## urace why

```
urace why <decision-id> [--depth <N>]
```

Traverses the reasoning chain rooted at `<decision-id>` to depth `N` (default: unlimited). For each node in the chain, outputs: id, kind, subject, decided_at, provenance_status, outcome, and the number of reasoning_steps. For compacted nodes found only in archive, outputs what is visible from `CompactionSummary.record_ids` and `CompactionSummary.kinds` without reading the archive. Marks compacted nodes as `[compacted — use urace decompact <event-id> to restore]`. Terminates at depth N, at nodes with no `prior_decision_refs`, or at the cycle-detected boundary. Output is ordered from root (requested record) to leaves (earliest antecedents). MUST NOT invoke any Executor; operates purely from durable state. Usable even during DORMANT or BLOCKED lifecycle states.

**Depth contract.** `--depth 0` returns only the requested record's own fields with no chain traversal. `--depth 1` returns the record plus its immediate `prior_decision_refs` nodes. The default (unlimited) traverses the complete chain.

**No-modification contract.** `urace why` is a read-only command. It MUST NOT write to state, inbox, or manifest regardless of what it finds.

**Invocation contract.** The justification traversal MUST be triggered at the following points: (1) before any Operation that modifies a Primitive or Schema definition; (2) before any change to Authority boundaries; (3) when a BLOCKING IntegrityGap is surfaced and the dependent operation requests clearance. The invoking component MUST pass a `root_claim_id` referencing the JustificationNode that anchors the reasoning chain.

**Traversal rules.** Traversal MUST be depth-first. `max_depth` MUST default to 8 unless overridden in Config. When a node at depth ≥ `max_depth` is reached, traversal MUST stop and surface a WARNING gap of kind `justification-depth-exceeded`. Cycle detection MUST be performed: if a `node_id` already appears in the current traversal path, traversal MUST stop and surface a BLOCKING gap of kind `justification-cycle-detected` before any effect is committed.

**Evidence weighting.** When multiple Evidence nodes support a JustificationNode, the node's confidence is the minimum confidence of all supporting Evidence records. A JustificationNode with no supporting Evidence MUST be treated as `confidence: 0.0`. A chain with any node at `confidence: 0.0` MUST be surfaced as a WARNING.

**Human-readable format.** When a justification chain is emitted to operator output, each node MUST be rendered as: `[depth] claim → basis (confidence: X.X, evidence: N)`. Intermediate nodes MUST be indented two spaces per depth level.

---

# 62h. Technique Applicability System

The Technique Applicability System gives the runtime an adaptive mechanism to decide whether each computational technique is worth executing given current state, whether the runtime can self-determine that worth, and — if not — whether delegating to an Executor is credit-justified. This section defines the meta-determination protocol, the six base and derived techniques as operational mechanisms, and the schema for recording applications.

## Meta-determination protocol

For each technique T and state S, the system computes:

- **Worth predicate** `W(T, S)` — True when technique T has potential to improve S or detect a violation.
- **Self-determination condition** `SD(T, S)` — True when the worth computation requires only enumerable, locally available state with no inference beyond arithmetic, set operations, or structural comparison.
- **Technique credit cost** `C(T)` — number of executor credits consumed if T is delegated. Zero for self-determinable techniques.

A technique whose `SD(T, S) = True` MUST be executed without executor delegation; spending credits on a self-determinable technique is a resource sink violation (§62a).

## TechniqueApplicabilityGate

The TechniqueApplicabilityGate is an ordered delta gate (T3 applied at meta-level) over guards evaluated in priority order for each technique T:

| Priority | Guard | Verdict | Reason |
|---|---|---|---|
| 1 | `lifecycle_state == DORMANT` AND no pending technique obligation for T | SKIP | dormant — no justified action |
| 2 | T already applied this cycle (idempotent) | SKIP | already applied this cycle |
| 3 | `SD(T, state) = True` | APPLY | self-determinable; zero credit cost |
| 4 | `SD(T, state) = False` AND `credits_remaining > C(T)` AND `W(T, state) = True` | DELEGATE_EXECUTOR | worth + credits justify delegation |
| 5 | `SD(T, state) = False` | DEFER | insufficient credits or indeterminate worth |

Guard order is normative. A runtime MUST NOT reorder guards.

## TechniqueApplicationRecord schema  [§62b reference]

See §62b for the canonical schema definition.

## Technique definitions

### T1 — Gap Detection Calculus (`diff`)

**Operator.** `gap(A, B) = {x ∈ A | x ∉ B}`

**Worth predicate.** `W(T1, S)` = True when A and B are both enumerable from durable state and `|gap(A,B)| > 0` or has not been checked since last mutation of A or B.

**SD condition.** Always True. A is a set of normative rules (enumerable from spec); B is a set of implementation evidences (enumerable from state and source). No inference required.

**Apply to:** spec normative rules vs implementation coverage (§80 spec audit); before-metrics vs after-metrics (§54 validation gate); expected schema fields vs present fields (§62b conformance).

### T2 — Bar-Raising Calculus (`incr`)

**Operator.** `threshold(t+1) = threshold(t) + Δ(accepted(t))`, `Δ ≥ 0`

**Worth predicate.** `W(T2, S)` = True after an operation is accepted (not on rejection or no-op cycles).

**SD condition.** Always True. `threshold(t)` and `Δ` are both numeric values in durable state.

**Invariant.** `threshold(t)` is non-decreasing. A runtime MUST NOT lower the threshold as a result of an acceptance. An explicit operator reset with documented authority_basis is the only valid path to threshold reduction.

**Audit trail requirement.** Each T2 application MUST produce an Evidence record with kind `threshold-adjustment` containing fields: `metric_id`, `before_threshold`, `delta`, `after_threshold`, `authorized_by`, `at`. This record MUST be appended to `state["evidence"]` before the new threshold takes effect. An absence of this record for any accepted Operation constitutes a `threshold-audit-missing` WARNING IntegrityGap.

**Apply to:** metric baselines (normative_rules, behavioral_tests); evaluation quality score; iteration bar for Objective acceptance.

### T3 — Delta Gate (`gate`)

**Operator.** `GATE(δ, G) = first_match(G, λg : eval(g, δ))`

**Worth predicate.** `W(T3, S)` = True when the decision has ≥ 2 possible outcomes and the ordering of outcomes is normatively significant.

**SD condition.** Always True. Guard predicates are boolean expressions over enumerable state.

**Guard order invariant.** Guard order is normatively significant. A gate with N guards has N! possible orderings; only one is canonical. The canonical order for every gate in this spec is declared at the gate's definition site. Reordering is a spec violation.

**Primary instance.** §62c Discovery Credit Gate. Secondary instance: TechniqueApplicabilityGate (this section).

### T4 — Paired Invariant (`paired`)

**Operator.** `PairedInvariant(A, B, P) : ∀ writes : P(A, B) = True`

**Worth predicate.** `W(T4, S)` = True when A and B are writable fields in durable state and the last write to either field has not been jointly validated.

**SD condition.** Always True. P is a structural predicate expressible as a boolean over field values.

**Write protocol.** Any write to A or B MUST atomically validate P(A, B) before persisting. A write that would violate P MUST be rejected; partial writes that leave P transiently false violate this invariant even if a subsequent write would restore it.

**Canonical pairs.**
- `lifecycle_state` ↔ `status_transitions[-1].status` — P: the most recent StatusTransition.status equals the current lifecycle_state after the transition completes.
- ScopePriorityConfig weights ↔ normalized sum — P: `|∑weights − 1.0| ≤ 1e-9`.
- PendingValidation.status ↔ operation_id — P: status is PENDING_CAPABILITY only when operation_id references a real recorded operation.

### T5 — Atomic Decomposition and Composition (`decompose+compose`)

**Operator.** `Decompose(S)` = partition S into minimal semantic units `{u₁, …, uₙ}` where each `uᵢ` carries exactly one independently normative claim. `Compose(U)` = the schema or pipeline that is the join of all `uᵢ ∈ U`.

**Worth predicate.** `W(T5, S)` = True when a schema or pipeline stage bundles ≥ 2 independently testable normative claims that can be separated without information loss.

**SD condition.** True for structural decomposition (fields, function arguments, schema properties). False for semantic decomposition of a novel type where the normative boundary between claims is not yet expressed — in that case, executor delegation is required to identify the semantic boundary.

**Structural vs. semantic boundary taxonomy.** A decomposition is STRUCTURAL when: (a) the sub-components have well-defined, independently verifiable interfaces; (b) the sub-components can be implemented and tested without knowledge of sibling components; (c) the decomposition follows an established protocol, schema, or AP already present in the spec. A decomposition is SEMANTIC when: (a) the boundary requires domain judgment about meaning or intent; (b) the sub-components share implicit state not captured in a schema; (c) the domain is novel and no analogous construct exists in the spec. When the classification is ambiguous, the runtime MUST default to SEMANTIC (T5 SD = False) and delegate to the Executor.

**Classification-disagreement protocol.** If two consecutive Executor evaluations produce conflicting T5 SD values for the same decomposition target, the runtime MUST: (1) record both evaluations in the State Document; (2) surface a WARNING gap of kind `technique-classification-disagreement`; (3) default to SD = False for the current cycle; (4) include the disagreement in the next `/rules` output for operator review.

**Composition rule.** A composed unit MUST reference its constituents by their canonical §62b schema names; inlining a sub-schema as an unnamed type is prohibited.

### T6 — Vector Transformation (`vector`)

**Operator.** Given vector `W = [w₁, …, wₙ]`, a normalization transform produces `W' = W / ‖W‖₁` such that `∑w'ᵢ = 1.0 ± 1e-9` and `w'ᵢ ≥ 0`. A step-bounded update produces `w'ᵢ = clamp(wᵢ + δᵢ, 0, max_weight_step_per_revision)` followed by renormalization.

**Worth predicate.** `W(T6, S)` = True when a weight vector is present in state and the normalized sum has drifted outside `1.0 ± 1e-9`, or a step-bounded update has been requested.

**SD condition.** True for known vector spaces (ScopePriorityConfig weights, metric trend vectors). False for a novel metric vector with unknown basis — executor delegation is required to determine the normalization basis.

**Apply to:** §62b ScopePriorityConfig weights; metric trend vectors; any multi-dimensional scoring system where weights must sum to a constant.

### T7 — Determinism/Probabilistics Selection (`det-prob`)

**Operator.** Given a decision domain D and state S, classify D as one of three execution modes:
- `DETERMINISTIC`: D has enumerable, finite options with explicit evaluation criteria expressible as boolean predicates over S. Execute locally; zero credits.
- `HEURISTIC`: D has a bounded search space where known domain heuristics reliably prune candidates without exhaustive enumeration. Execute heuristic locally; validate result (C_validate credits).
- `PROBABILISTIC`: D requires inference over uncertain state or novel inputs where explicit criteria cannot be pre-specified. Delegate to executor with reasoning trace requirement (C_executor credits).

**Worth predicate.** `W(T7, S)` = True before any executor delegation decision where the delegation mode has not been classified for the current domain and state.

**SD condition.** True when the domain is well-typed with explicit enumerable criteria. False for novel domains — executor delegation required to classify.

**Selection protocol.**

| Classification | Execution method | Credit cost | SD |
|---|---|---|---|
| DETERMINISTIC | evaluate predicates locally | 0 | True |
| HEURISTIC | apply domain heuristic locally + validate result | C_validate | True (heuristic step) |
| PROBABILISTIC | delegate to executor with reasoning trace | C_executor | False |

**Invariant.** A DETERMINISTIC classification MUST NOT delegate to an executor unless local evaluation fails due to a missing data dependency (in which case, log a named IntegrityGap before delegating). A PROBABILISTIC classification MUST NOT be treated as DETERMINISTIC merely because the most recent run happened to match a predicate pattern.

**Apply to:** authority resolution (DETERMINISTIC when policy fully enumerated); evidence conflict resolution (HEURISTIC for known conflict patterns, PROBABILISTIC for novel conflicts); objective discovery (PROBABILISTIC); T7 self-classification (DETERMINISTIC for T1–T4; HEURISTIC for T5; PROBABILISTIC for novel domains); context budget estimation (DETERMINISTIC).

## Technique-scope mapping

| Technique | Spec (URACE.md) | Runtime |
|---|---|---|
| T1 diff | §80 spec audit rule enumeration | spec audit component gap computation; validation gate before/after metric diff |
| T2 incr | normative_rules baseline non-decrease | metric baseline tracking; bar-raising on acceptance |
| T3 gate | TechniqueApplicabilityGate; §62c Discovery Credit Gate | discovery-due evaluator; validation gate |
| T4 paired | canonical pairs table (this section) | lifecycle_state ↔ status_transitions validation |
| T5 decompose | citizen schema minimality (§62b) | schema conformance validation primitives |
| T6 vector | ScopePriorityConfig normalization contract | scope weight normalization enforcement |
| T7 det-prob | authority resolution classification; discovery delegation mode | delegation mode selector for executor calls; SD gate before credit spend |

---

# 62i. Architectural Meta-Patterns

## First-class Architectural Concepts

Before defining individual patterns, this section establishes nine first-class concepts that the pattern vocabulary is built upon.

**Citizen.** A citizen is any named entity that participates in the URACE lifecycle: it has an identity (a stable `id` field), conforms to a declared citizen schema (§62b), produces or consumes evidence in the broadcast log (AP15), and is traceable through the causal chain (AP6). Citizens are distinct from scalars (leaf values, no identity) and operations (transformations, no persistent identity). See AP0 for the formal definition.

**Formula.** A formula is a symbolic expression that is the precise, unambiguous, machine-verifiable encoding of a normative rule. Where natural language describes a rule in prose, a formula expresses it in mathematical notation. Every normative rule in this specification that admits a formula representation SHOULD also have one. Formulas are the canonical form for quantitative constraints, ordering contracts, and invariants. See AP17 for the Lexical→Formula reduction mechanism.

**Calculus.** A calculus is a system of symbolic rules for transforming expressions within a domain. In this specification, five calculi are used: Gap Detection (T1, §62h), Bar-Raising (T2, §62h), Delta Gate (T3, §62h), Fixpoint (AP8), and Lexical→Formula Reduction (AP17). Each calculus has a defined domain, operators, and reduction rules.

**Meta-Pattern.** A meta-pattern is a pattern that describes how to define, instantiate, and compose other patterns. §62i defines meta-patterns. The patterns defined here are themselves instances of the meta-patterns they describe: AP2 (Citizen Schema) is itself a citizen schema; AP3 (Append-Only Log) is itself stored in an append-only log; AP4 (Contract) is itself governed by contracts.

**Meta-Technique.** A meta-technique is a technique for deciding which technique to apply, how to apply it, and when to apply it. The TechniqueApplicabilityGate (§62h) is the primary meta-technique in URACE. AP17 (Lexical→Formula) and AP19 (Customization Layer) are meta-techniques that govern how the specification itself evolves.

**Primitive.** A primitive is the lowest-level indivisible unit in the architectural vocabulary. Two classes exist: a Canonical Scalar (AP1) — a leaf value type with no sub-structure — and a Citizen (AP0) — a named, schema-bearing entity with identity. Every field in every citizen schema resolves, recursively, to one of these two primitive classes. The word "primitive" in this specification always refers to one or both of these classes; no third primitive class exists.

**Communication / Intercommunication.** Communication is the exchange of information between two or more components. In URACE, all inter-component communication is formalized as a composition of three patterns: a Bridge (AP11) for crossing authority or process boundaries; a Durable Inbox (AP14) for asynchronous delivery with at-least-once guarantee; and a Broadcast Log (AP15) for append-only event distribution. "Intercommunication" names the same exchange when it involves two or more components passing messages back and forth across a Bridge. No separate AP is defined for Communication or Intercommunication — they are always compositions of AP11, AP14, and AP15.

**Diagram.** A diagram is a structural or flow visualization of URACE components and their relationships. Diagrams are documentation artifacts: they clarify intent, are not stored as lifecycle state, are not citizens, carry no normative force beyond what the accompanying text states, and are never inputs to autonomous decisions. When a diagram and the normative text conflict, the normative text governs.

**Method.** Method is a generic colloquial alias that resolves — by context — to one of three canonical forms: a Technique (§62h, a structured approach to Product improvement), an Operation (§62b, a bounded executor action with defined preconditions and outcomes), or an Architectural Meta-Pattern (§62i, a reusable structural contract). When the word "method" appears in this specification or in user input, it MUST be interpreted in its canonical form. No first-class schema named Method exists.

---

## Reuse-over-use axiom

A pattern MUST be defined once in the most general form before it is instantiated. Implementing the same structural contract ad hoc in two places without referencing a shared pattern definition is an architectural violation. The canonical form always takes precedence.

---

## AP0 — Citizen

**Derivation metadata.** `standalone: true` · `tier: FOUNDATIONAL` · `requires: []` · `provides: named identity, schema conformance, lifecycle traceability`

**Intent.** A citizen is the fundamental unit of identity in URACE. Every named, schema-bearing, lifecycle-participating entity is a citizen.

**Roles.**
- `id` — stable identifier; never reused after creation
- `schema` — the §62b schema this citizen conforms to
- `at` — ISO-8601 creation timestamp
- `source` — component that created this citizen

```
Citizen = {
  id:       identifier  — stable, never reused after creation
  schema:   CitizenSchema.name  — the §62b schema this citizen conforms to
  at:       iso_timestamp  — creation timestamp
  source:   string  — component that created this citizen
}
```

**Constraints.**
- **Identity.** Two citizens are the same if and only if their `id` fields are equal.
- **Schema conformance.** A citizen MUST conform to its declared schema at all times; a mutation that violates the schema MUST be rejected.
- **Traceability.** Every citizen creation and mutation MUST produce an entry in the broadcast log (AP15) carrying the citizen's `id`.
- **Non-recycling.** A citizen `id` MUST NOT be reused after the citizen is deleted, archived, or compacted.

**Implementation.** All schemas in §62b are citizen schemas. Primary classes: `Objective`, `Evidence`, `Blocker`, `DecisionRecord`, `StatusTransition`, `PendingValidation`, `ScheduledTask`, `CustomizationRecord`.

**Used in:** (universal — all spec sections; every named entity in URACE is a citizen)

---

## AP1 — Canonical Scalar

**Derivation metadata.** `standalone: true` · `tier: FOUNDATIONAL` · `requires: []` · `provides: typed leaf values, domain constraints, define-once reuse contract`

**Intent.** A canonical scalar is a leaf-node value type that cannot be further decomposed without losing semantic meaning. It is the smallest unit of information in the system.

**Roles.**
- `name` — unique canonical identifier
- `type` — json_primitive | enum | bounded_numeric
- `domain` — constraint expression defining valid values
- `validation_rule` — predicate V(x) → {VALID, INVALID, reason}
- `null_policy` — PROHIBITED | PERMITTED | REQUIRED_ABSENT

```
CanonicalScalar = {
  name:            unique canonical identifier
  type:            json_primitive | enum | bounded_numeric
  domain:          constraint expression defining valid values
  validation_rule: predicate V(x) → {VALID, INVALID, reason}
  null_policy:     PROHIBITED | PERMITTED | REQUIRED_ABSENT
}
```

**Constraints.**
- A canonical scalar is defined once in §62b and referenced by name in every schema that uses a value of that type. Inlining the domain constraint instead of referencing the canonical scalar name is a reuse violation.

**Implementation.** See §62b Canonical Scalar Catalog.

---

## AP2 — Citizen Schema

**Derivation metadata.** `standalone: false` · `tier: FOUNDATIONAL` · `requires: [AP0, AP1]` · `provides: named versioned data structures, minimality rule, composition rule`

**Intent.** A citizen schema is a named, versioned, fully-specified data structure whose every field is either a canonical scalar or a reference to another citizen schema. It is the primary reuse unit for structured data.

**Roles.**
- `CitizenSchema` — named versioned data structure; every field is a canonical scalar or schema reference
- `FieldDef` — a single field definition with name, type, and cardinality

```
CitizenSchema = {
  name:        unique canonical name (PascalCase, declared in §62b)
  fields:      list of FieldDef
  required:    set of field names that MUST be present
  validation:  named primitive in §62d validate_* family
  version:     spec revision when first introduced or last modified
}

FieldDef = {
  name:      field identifier
  type:      CanonicalScalar.name | CitizenSchema.name
  cardinality: ONE | MANY | OPTIONAL
}
```

**Constraints.**
- A citizen schema MUST be in minimal normal form (§62h AP Pattern 6 — Atomic Decomposition): no field bundles two independently normative claims. A field that can be split into two fields each with their own normative rule MUST be split.
- Fields whose type is another citizen schema MUST reference the schema by its canonical §62b name. Anonymous inline sub-schemas are prohibited.

**Implementation.** §62b Citizen Schemas (all citizen definitions). §62d validate_* family for validation primitives.

---

## AP3 — Append-Only Log

**Derivation metadata.** `standalone: false` · `tier: FOUNDATIONAL` · `requires: [AP2]` · `provides: durable ordered sequence, monotone length invariant, ordering/identity/causal invariants, compaction-safe retention`

**Intent.** An append-only log is a durable ordered sequence of records where records are only ever added to the end — never modified or deleted before the retention window expires.

**Roles.**
- `AppendOnlyLog<T>` — the durable ordered sequence
- `entries` — monotone non-decreasing list
- `entry_schema` — every entry conforms to T
- `retention` — RetentionPolicy governing compaction and eviction

**Definition.**
```
AppendOnlyLog<T> = {
  entries:        list<T>  — monotone non-decreasing length
  entry_schema:   CitizenSchema  — every entry conforms to T
  retention:      RetentionPolicy  — governs compaction and eviction
  id_field:       field name within T whose value is a stable identifier
  at_field:       field name within T whose value is an ISO-8601 timestamp
}
```

**Constraints.**
- Append: `log(t+1).length ≥ log(t).length`
- Ordering: `∀ i < j : log[i].at ≤ log[j].at`
- Identity: `∀ i : log[i].id` is stable and never reused after the entry is written
- Causal: every entry carries a `source` field naming the component that produced it
- Compaction (§62f) does not violate append-only: it replaces a contiguous segment with a `CompactionSummary` entry while the original records move to archive. The log's logical length does not decrease; the live list length decreases only by replacement with a summary entry, not by silent deletion.

**Implementation.** `state.evidence`, `state.status_transitions`, `state.executor_calls`, `state.decision_records`, `state.technique_application_log`.

---

## AP4 — Producer-Consumer Contract

**Derivation metadata.** `standalone: false` · `tier: FOUNDATIONAL` · `requires: [AP0]` · `provides: named bilateral obligations, producer_must list, consumer_may_assume guarantees, violation protocol`

**Intent.** A producer-consumer contract is a named, verifiable, bilateral obligation between two components: one that writes a value (producer) and one that reads it (consumer).

**Roles.**
- `ProducerConsumerContract` — the named bilateral obligation record
- `producer` — component that writes a value
- `consumer` — component that reads the value
- `artifact` — schema name or field reference exchanged
- `violation_protocol` — what happens when the contract is broken (REJECT | QUARANTINE | ALERT)

```
ProducerConsumerContract = {
  name:               unique contract identifier
  producer:           component name
  consumer:           component name
  artifact:           schema name or field reference
  producer_must:      list of normative obligations on the writer
  consumer_may_assume: list of guaranteed properties the reader can rely on
  violation_protocol: what happens when the contract is broken (REJECT | QUARANTINE | ALERT)
  idempotent:         bool — True when applying the contract N times equals once
}
```

**Constraints.**
- Any two components that exchange data MUST document their exchange as a named ProducerConsumerContract. Implicit knowledge of inter-component data shape is a contract violation.
- Every runtime that records named ProducerConsumerContract instances MUST validate that all required fields are present and that violation_protocol is one of REJECT | QUARANTINE | ALERT. An instance with a missing required field or invalid violation_protocol is a schema conformance violation.

**Implementation.** `InputQueue → CycleOrchestrator` — inputs written by executor, consumed at safe boundary; `CycleOrchestrator → StateDocument` — cycle writes state, runtime reads it at next cycle; `Executor → InputQueue` — executor writes inbox items, runtime processes them; `ValidationGate → CycleOrchestrator` — gate returns verdict, cycle acts on it.

---

## AP5 — Idempotency Contract

**Derivation metadata.** `standalone: true` · `tier: FOUNDATIONAL` · `requires: []` · `provides: retry safety, idempotency class declaration (PURE/AT_MOST_ONCE/AT_LEAST_ONCE/EXACTLY_ONCE)`

**Intent.** An operation satisfies the idempotency contract when applying it N times to the same input produces the same output as applying it once.

**Roles.**
- `IdempotencyClass` — one of PURE, AT_MOST_ONCE, AT_LEAST_ONCE, EXACTLY_ONCE
- `f` — the operation under evaluation
- `dedup_key` — the stable identifier used to detect duplicate applications

```
f idempotent ⟺ ∀ x : f(f(x)) = f(x)
```

Cycles may be interrupted and retried. Any operation that is not idempotent produces inconsistent state on retry. All state-mutating operations MUST declare their idempotency class.

| Class | Definition | URACE examples |
|---|---|---|
| PURE | `f(f(x)) = f(x)` | state snapshot write, spec structural audit, operation validation |
| AT_MOST_ONCE | Side effects occur at most once; retries are no-ops | executor call (guarded by dedup) |
| AT_LEAST_ONCE | Safe to retry; may produce duplicate records | evidence append (records carry `id`, dedup on read) |
| EXACTLY_ONCE | Guaranteed single effect; requires coordination | compaction commit (write + swap, atomic) |

**Constraints.**
- Every operation exposed as a lifecycle command or cycle phase MUST declare its idempotency class.
- A state-mutating operation that lacks an idempotency class declaration is an architectural gap.

**Implementation.** §50, §51, §62b InputQueue. Governs all operation retry safety across the lifecycle.

---

## AP6 — Causal Provenance Chain

**Derivation metadata.** `standalone: false` · `tier: COMPOSITIONAL` · `requires: [AP3, AP4]` · `provides: full cause traceability, causal chain traversal, source/at/id provenance on every log entry`

**Intent.** Every durable state change MUST be traceable to a cause. A cause is a durable record that precedes the change in causal time.

**Roles.**
- `CausalChain` — the traversable sequence of Evidence or Input records that caused a state value
- `source` — the component that produced each log entry
- `prior_decision_refs` — the causal pointer in DecisionRecord used to traverse the chain

```
CausalChain(s₂) ≡ ∃ s₁, e : s₂ = apply(e, s₁)  ∧  e.at ≤ s₂.modified_at
```

where `e` is an Evidence or Input record that authorized the change.

**Constraints.**
- Every append-only log entry MUST carry: `source` — the component that produced it; `at` — ISO-8601 timestamp of creation; `id` — stable identifier.
- Given any durable state field F at time T, an implementation MUST be able to reconstruct the sequence of Evidence or Input records that caused F's current value, by traversal of append-only logs. An implementation that mutates F without a traceable antecedent violates this contract.

**Implementation.** §62g Justification System (`urace why`). The `prior_decision_refs` field in `DecisionRecord` is the causal pointer used to traverse the chain.

---

## AP7 — Canonical Reduction (Semantic Resulting Logic Calculus)

**Derivation metadata.** `standalone: true` · `tier: FOUNDATIONAL` · `requires: []` · `provides: semantic deduplication, minimality guarantee, cross-bootstrap reproducibility`

**Intent.** Canonical reduction is the process of transforming any expression — a spec rule, schema, pipeline description, or data value — into its unique, minimal, machine-reproducible canonical form.

**Roles.**
- `reduce(expr)` — the reduction function mapping any expression to its canonical form
- `canonical_form` — the unique, minimal, machine-reproducible representation
- `SRLC` — the applied discipline of canonical reduction over the URACE semantic domain

**Definition.**
```
reduce(expr) = canonical_form(expr)
```

where `canonical_form` satisfies:
- **Uniqueness.** Two semantically equivalent expressions have the same canonical form.
- **Minimality.** No part of the canonical form is redundant; removing any element changes the semantic content.
- **Reproducibility.** Given the same input, any independent bootstrap produces the same canonical form.

**SEMANTIC RESULTING LOGIC CALCULUS (SRLC).** The SRLC is the applied discipline of canonical reduction over the URACE semantic domain. It answers: "What is the smallest, unambiguous, machine-reproducible expression of this concept?"

**Constraints.**
- Structural reduction (field deduplication, sort canonicalization, whitespace normalization): SD = True.
- Semantic equivalence detection (two rules with different phrasing but same normative effect): SD = False — requires executor judgment.

**Implementation.** Spec normative rules → minimal normative claims; citizen schemas → minimal normal form; pipeline descriptions → minimal ordered step sequence; evidence records → canonical evidence kind vocabulary (§62b Evidence kinds table). The §80 Spec Audit Mechanism applies SRLC to produce `normative_rules` count: each normative rule is reduced to a minimal, independently testable claim before counting.

**Used in:** (universal — all spec sections; every construct definition and normative rule applies SRLC)

---

## AP8 — Fixpoint Calculus

**Derivation metadata.** `standalone: false` · `tier: COMPOSITIONAL` · `requires: [AP3, AP5]` · `provides: stagnation detection, convergence loops, REPAIRING lifecycle escalation trigger`

**Intent.** A fixpoint computation iterates a function until the output equals the input — i.e., until the system reaches a stable state.

**Roles.**
- `fix(f, x₀)` — the fixpoint iterator
- `convergence_predicate P(xₙ, xₙ₊₁)` — declared before iteration begins
- `max_iter` — the iteration bound preventing infinite loops

```
fix(f, x₀) : iterate xₙ₊₁ = f(xₙ) until xₙ₊₁ = xₙ (or ‖xₙ₊₁ − xₙ‖ < ε)
```

**Constraints.**
- An implementation applying fixpoint MUST: (1) Declare a convergence predicate `P(xₙ, xₙ₊₁)` before iteration begins. (2) Bound the maximum iteration count `max_iter` to prevent infinite loops. (3) If `max_iter` is reached without convergence, surface a named IntegrityGap with `severity: WARNING`.
- SD condition: True when the iteration space is finite and enumerable. False when convergence depends on open-ended inference — executor delegation required.

**Implementation.** Spec audit convergence (iterating gap detection until no new gaps); metric stabilization (iterating until trend is flat); reasoning chain resolution (iterating until no new antecedents). §37 assessment cycle, §38 discovery.

---

## AP9 — Monotone Accumulator

**Derivation metadata.** `standalone: false` · `tier: COMPOSITIONAL` · `requires: [AP3]` · `provides: monotone growth invariant, evidence count integrity, progress measurement baseline`

**Intent.** A monotone accumulator is a value that only increases (or stays the same) — it never decreases except through an explicit authorized reset.

**Roles.**
- `v` — the accumulator value
- `reset_event` — the authorized record permitting a decrease; MUST carry `authority_basis` and `reason`

```
MonotoneAccumulator(v) : v(t+1) ≥ v(t)  ∀ t
```

**Constraints.**
- A decrease in `v` is only valid when accompanied by an authorized `reset_event` record with `authority_basis` and `reason` fields. A decrease without a reset event is an integrity violation.
- The length of an Append-Only Log is a monotone accumulator. Compaction replaces entries but does not decrease the logical count (summaries count as one entry).

**Implementation.** `normative_rules` count; `behavioral_tests` count; `evidence` log length; `executor_calls` count; any bar-raising threshold (§62h T2). §59b capability completeness, §62c quality streak.

---

## AP10 — Bounded Retry with Backoff

**Derivation metadata.** `standalone: false` · `tier: COMPOSITIONAL` · `requires: [AP4, AP5]` · `provides: resilient bounded retry, exponential backoff, failure classification (transient/semantic/structural)`

**Intent.** A bounded retry applies an operation up to `max_attempts` times, with exponentially increasing delay between attempts, bounded by `max_delay`.

**Roles.**
- `max_attempts` — the retry bound
- `base_delay` — initial delay in seconds
- `max_delay` — the ceiling on delay growth
- `SYSTEMATIC_FAILURE` — the classification after max_attempts are exhausted

```
delay(n) = min(base_delay × 2^n, max_delay)   n = 0, 1, …, max_attempts−1
```

**Constraints.**
- `attempt(0)` is the initial try; no delay before it.
- `attempt(n)` for `n > 0` waits `delay(n−1)` before executing.
- After `max_attempts` failures, the operation is classified as SYSTEMATIC_FAILURE.
- Jitter MAY be added: `delay_jittered(n) = delay(n) × U(0.5, 1.0)` where U is uniform random.
- SD condition: Always True — all parameters are numeric values in config.

**Implementation.** Executor transient network failures (§62c); auth failure backoff (§62c); capability probe retry; validation gate retry when capability unavailable. §43 executor selection.

---

## AP11 — Bridge

**Derivation metadata.** `standalone: false` · `tier: COMPOSITIONAL` · `requires: [AP4]` · `provides: authority-boundary translation, BridgeRecord citizen, schema validation at crossing point`

**Intent.** A bridge is an explicit, named, one-directional translation layer between two incompatible representations. It is the canonical mechanism for crossing a semantic boundary.

**Roles.**
- `Bridge` — the named translation layer
- `source_schema` — input representation
- `target_schema` — output representation
- `transform` — f : source_record → target_record
- `loss_policy` — LOSSLESS or LOSSY_DECLARED

**Definition.**
```
Bridge = {
  name:           unique bridge identifier
  source_schema:  CitizenSchema name (input representation)
  target_schema:  CitizenSchema name (output representation)
  direction:      ONE_WAY | BIDIRECTIONAL
  transform:      f : source_record → target_record
  loss_policy:    LOSSLESS | LOSSY_DECLARED  — lossy bridges must document what is lost
  idempotency:    IdempotencyClass
}
```

**Constraints.**
- A direct cast from S to T embeds the translation in both the producer and consumer, coupling them. A named bridge is a single definition point: change the translation once to propagate it everywhere.

**Implementation.** Canonical bridges in URACE:

```
┌─────────────────┐     Bridge B1      ┌────────────────────┐
│  URACE.md       │ ─────────────────► │  Spec Audit        │
│  (normative     │  rule → IntegrityGap│  (runtime coverage │
│   rules)        │  or PASS evidence  │   evidence)        │
└─────────────────┘                    └────────────────────┘

┌─────────────────┐     Bridge B2      ┌────────────────────┐
│  Executor       │ ─────────────────► │  Input Queue       │
│  (JSON output)  │  response → Input  │  (state inbox)     │
└─────────────────┘                    └────────────────────┘

┌─────────────────┐     Bridge B3      ┌────────────────────┐
│  MetricObserv.  │ ─────────────────► │  Validation Gate   │
│  (raw values)   │  value → guardrail │  (verdict)         │
└─────────────────┘     result         └────────────────────┘
```

**Bridge B1 — Spec→Runtime.** Translates each normative rule in URACE.md into either a passing implementation evidence record or a named IntegrityGap. Implemented by the runtime's spec audit component. Lossless: every rule produces exactly one output record.

**Bridge B2 — Executor→Inbox.** Translates executor JSON output into an Input record consumed by the durable inbox. Implemented by the runtime's input dispatch component. Loss policy: LOSSY_DECLARED — unrecognized executor output fields are dropped and logged as `executor-response-unrecognized-field` evidence.

**Bridge B3 — Metric→Decision.** Translates raw metric observations into validation gate verdicts (PASS/FAIL). Implemented by the runtime's validation gate component. Lossless: every metric produces one check record.

---

## AP12 — Orchestrator

**Derivation metadata.** `standalone: false` · `tier: COMPOSITIONAL` · `requires: [AP4]` · `provides: sequenced multi-step operations, OrchestratorRecord citizen, phase boundaries with safe abort points`

**Intent.** An orchestrator is a named, multi-phase coordination mechanism that sequences operations, enforces pre/post conditions, handles failures, and emits a completion record.

**Roles.**
- `Orchestrator` — the named multi-phase coordination record
- `OrchestratorPhase` — a single phase with idempotency, timeout, and failure contract
- `completion_record` — the OrchestratorRecord appended to evidence on completion
- `failure_contract` — ABORT_AND_ROLLBACK | CONTINUE_DEGRADED | HALT

**Definition.**
```
Orchestrator = {
  name:         unique orchestrator identifier
  preconditions: list<Predicate>  — must hold before execution begins
  phases:        ordered list<OrchestratorPhase>
  failure_contract: ON_PHASE_FAILURE → {ABORT_AND_ROLLBACK | CONTINUE_DEGRADED | HALT}
  postconditions: list<Predicate>  — must hold after successful completion
  completion_record: OrchestratorRecord  — appended to evidence on completion
}

OrchestratorPhase = {
  name:       phase identifier
  idempotency: IdempotencyClass
  timeout_s:  maximum allowed duration
  on_timeout: FAIL_PHASE | SKIP_PHASE
}
```

**Sequence diagram — cycle() orchestrator:**
```
 ┌─────────────────────────────────────────────────────────────────┐
 │ Orchestrator: cycle()                                           │
 │                                                                 │
 │  [Pre] lifecycle_state ∈ {ASSESSING, DORMANT, BLOCKED}         │
 │    │                                                            │
 │    ▼                                                            │
 │  Phase 1: assess        — evaluate metrics, gaps, objectives   │
 │    │                                                            │
 │    ▼                                                            │
 │  Phase 2: select        — choose highest-priority action       │
 │    │                                                            │
 │    ▼                                                            │
 │  Phase 3: execute       — apply selected action (or skip)      │
 │    │                                                            │
 │    ▼                                                            │
 │  Phase 4: validate      — independent validation gate (§54)    │
 │    │         ┌── FAIL → rollback → record rejection            │
 │    ▼         │                                                  │
 │  Phase 5: persist       — durable write of state + CRC        │
 │    │                                                            │
 │    ▼                                                            │
 │  Phase 6: technique_gate — evaluate T1–T6 applicability        │
 │    │                                                            │
 │    ▼                                                            │
 │  [Post] state persisted, CRC current, evidence appended        │
 └─────────────────────────────────────────────────────────────────┘
```

**Constraints.**
- Any future multi-phase operation (e.g., compaction, rebootstrap) MUST be defined as an Orchestrator instance with the same contract structure rather than implemented as an ad-hoc sequence.

**Implementation.** The autonomous cycle orchestrator. Every autonomous URACE iteration is one execution of this orchestrator. §62i Orchestrator topology, multi-step plans.

---

## AP13 — Observer

**Derivation metadata.** `standalone: false` · `tier: COMPOSITIONAL` · `requires: [AP3]` · `provides: decoupled observation, broadcast log read contract, reactive triggers without producer coupling`

**Intent.** An observer is a component that is notified of a state change without being directly coupled to the component that caused the change.

**Roles.**
- `Observer` — the named observation component
- `watches` — the field_path or event_kind in state being observed
- `trigger` — Predicate(old_value, new_value) → bool
- `action` — what the observer does when triggered

**Definition.**
```
Observer = {
  name:          unique observer identifier
  watches:       field_path or event_kind in state
  trigger:       Predicate(old_value, new_value) → bool
  action:        what the observer does when triggered
  idempotency:   IdempotencyClass (observers MUST be idempotent)
}
```

**Constraints.**
- The producing component MUST NOT know the identity of observers. Observers read from the Broadcast Log (AP15); they do not receive direct callbacks.
- Observers MUST be idempotent (IdempotencyClass declared per AP5).

**Implementation.** `spec_audit_due()` — watches `spec_version` field; fires when version changes → triggers spec audit phase. `executor_discovery_due()` — watches executor credit state; fires when budget gates clear → triggers discovery. Metric threshold observer — watches metric values; fires when a value crosses baseline → triggers ASSESSING transition. §60 autonomous feedback, §71 live observability.

---

## AP14 — Durable Inbox (Input Queue)

**Derivation metadata.** `standalone: false` · `tier: COMPOSITIONAL` · `requires: [AP5]` · `provides: crash-safe FIFO input queue, source_input traceability, structured rejection records, 16-kind input catalog, orderly shutdown with input preservation`

**Intent.** The Durable Inbox is a persistent, FIFO, append-only queue of pending commands and responses written by external agents and processed at safe lifecycle boundaries.

**Roles.**
- `DurableInbox` — the persistent FIFO queue
- `InboxInput` — a single queued item with id, at, kind, and payload
- `source_input` — the traceability field linking lifecycle artifacts to their inbox origin
- `rejection_record` — the structured durable record for failed inputs

**Definition.**
```
DurableInbox = {
  storage:       persistent durable storage (implementation-defined medium)
  ordering:      FIFO by `at` field (ISO-8601 ascending)
  durability:    write-before-process — inbox item is durable before the runtime reads it
  idempotency:   AT_MOST_ONCE — item is removed from inbox after successful processing
  rejection:     failed items preserved as rejection records, never silently dropped
  boundary:      items are processed only at SAFE lifecycle boundaries (not mid-phase)
}
```

**Communication topology diagram:**

```
  External Agent (Executor, Operator)
         │
         │  writes durable queue entry
         ▼
  ┌──────────────────┐
  │   Durable Inbox  │  (AP14)  filesystem queue, FIFO by `at`
  └──────────┬───────┘
             │  consume_inputs() at safe boundary
             ▼
  ┌──────────────────┐
  │ Input Dispatcher │  (Bridge B2)  validates, routes to handler
  └──────────┬───────┘
             │  handler mutates state, appends evidence
             ▼
  ┌──────────────────┐
  │  State Document  │  (AP16)  snapshot + delta log
  └──────────┬───────┘
             │  evidence appended
             ▼
  ┌──────────────────┐
  │  Broadcast Log   │  (AP15)  state.evidence — all consumers read here
  └──────────┬───────┘
             │
      ┌──────┴──────┐──────────────┐
      ▼             ▼              ▼
  Inspection   Spec Audit    Reasoning Memory
  (AP13 obs)   (AP13 obs)    (AP13 obs)
```

**Input traceability contract.** When a queued Input is consumed from the Durable Inbox, the resulting lifecycle artifacts MUST carry a `source_input` field referencing the originating `Input.id`. Specifically: Objectives created from `goal` inputs MUST have `source_input: <input-id>`. Evidence records of kind `authoritative-input-consumed` MUST include `source_input: <input-id>`. Any handler that produces a rule-added, rule-superseded, rule-deactivated, scheduled-task-registered, or equivalent lifecycle artifact MUST include `source_input: <input-id>` on the artifact. This field enables `urace inbox status <input-id>` to return the full artifact chain produced by a given inbox command.

**Rejection record contract.** When a queued Input cannot be processed — due to malformed JSON, unsupported `kind`, schema validation failure, or handler rejection — URACE MUST write a structured rejection record to `state.evidence` with `kind: authoritative-input-rejected`, `source_input: <input-id>` (or null if id is unreadable), `reason: <human-readable string>`, and `rejected_at: <timestamp>`. The `.rejected` file suffix signals the physical rejection; the evidence record provides the machine-readable explanation. An implementation that renames the file without writing the evidence record produces an opaque rejection that violates this contract.

**Orderly shutdown signal contract.** When an orderly shutdown signal is received during autonomous operation — including SIGTERM, SIGINT, or any equivalent process-manager termination signal — URACE MUST complete any indivisible atomic operation currently in progress to its next safe checkpoint boundary, MUST NOT discard any durably queued inbox inputs that have not yet been processed, and MUST emit a structured shutdown summary to the active machine-readable channel before exiting. The shutdown summary MUST include: lifecycle state at stop, count of unresolved effects, count of unprocessed inbox inputs, and whether all completed-cycle state is durable. The exit code on orderly shutdown MUST be 130.

**Exit code contract.** An implementation MUST return one of the following exit codes:

| Code | Condition | Machine interpretation |
|------|-----------|------------------------|
| `0` | Success | Command completed normally; output is safe to parse |
| `1` | Validation or not-found error | Input rejected, resource not found, schema invalid; operator action required |
| `2` | Unrecoverable fault | Unhandled exception or controller error; retry after diagnosis |
| `75` | Restart requested | Self-evolution activation requires process restart; re-invoke immediately |
| `76` | Retry recommended | Trusted controller fault in retry state; re-invoke after brief delay |
| `130` | Orderly shutdown | Received orderly shutdown signal or operator interrupt; state is durable |

Any exit code not listed above is implementation-defined and MUST NOT be treated as a documented outcome by machine consumers.

**Constraints.**
- All external command injection MUST use the Durable Inbox file mechanism.
- URACE does not accept commands via standard input (stdin) or via socket/named-pipe IPC. File-based inbox provides durable, FIFO-ordered, crash-safe delivery that stdin and socket channels do not guarantee. Implementations that wish to wrap URACE in a socket server MUST front the Durable Inbox rather than bypass it.

**Implementation.** §38 queued inputs, §62l OperatorGateProtocol, §43 executor boundary.

**`urace inbox status <input-id>` contract.** The `inbox status` subcommand MUST accept an Input id and return a structured result containing: whether the input has been processed (`CONSUMED`, `REJECTED`, or `PENDING`), the timestamp of processing when applicable, the `input_kind`, and the list of `source_input`-linked artifact ids produced (objective ids, rule ids, task ids, evidence ids). In MACHINE mode (`--json`), this MUST be a JSON document. In human mode, a concise readable summary MUST be emitted. If the input id is not found in `processed_input_ids` and no inbox file exists for it, the status MUST be `NOT_FOUND` rather than an error exit.

## IPC Input Schema Catalog

The Durable Inbox accepts 16 input kinds. Each input file MUST conform to the envelope:

```
InboxInput {
  id      REQUIRED  string; unique input identifier (e.g. "input-<uuid>")
  at      REQUIRED  string; ISO-8601 timestamp; determines FIFO ordering
  kind    REQUIRED  string; one of the 16 kinds below
  payload REQUIRED  dict;   kind-specific payload (see catalog below)
  status  OPTIONAL  string; "QUEUED" by convention
  priority_tier    OPTIONAL  int; 0 | 1 | 2; default 1; governs processing order within a boundary
}
```

**Priority-tier contract.** The Durable Inbox uses a three-tier priority system within each safe lifecycle boundary. Tiers determine processing order; within a tier, FIFO by `at` (ISO-8601 ascending) is strictly maintained.

| Tier | Name | Applies to | Preemption |
|---|---|---|---|
| 0 | CRITICAL | Inputs whose kind is `control` with action `pause` or `stop`; any input with explicit `priority_tier: 0` | MUST be processed before Tier 1 and Tier 2 inputs at the same boundary |
| 1 | STANDARD | All other inputs (default) | Processed after Tier 0; FIFO within Tier 1 |
| 2 | OPPORTUNISTIC | Discovery, non-urgent context; inputs with explicit `priority_tier: 2` | Processed after Tier 1 is exhausted |

**Backward compatibility.** Inputs without a `priority_tier` field default to Tier 1. Implementations that do not implement tiering MUST treat all inputs as Tier 1 (pure FIFO by `at`); this is a valid but less capable conformance mode. **Tier assignment contract.** A Tier 0 MUST NOT be self-assigned by content unless the implementation validates the assignment against the hardcoded Tier 0 rule (pause/stop controls). An operator MUST NOT elevate arbitrary inputs to Tier 0 via the `priority_tier` field; the runtime MUST reject Tier 0 self-assignment for any input kind not in the hardcoded list and surface IntegrityGap(`kind: "inbox-priority-tier-violation"`, severity=WARNING).

**Catalog:**

| Kind | Required payload fields | Effect |
|------|------------------------|--------|
| `context` | `text: str` | Appends operator-supplied context; triggers discovery |
| `goal` | `title: str`, `success_measure: str` | Creates a new planned Objective |
| `source` | `id: str`, `kind: str` (json_file\|http_json\|github_repository) | Registers or updates a connector source |
| `metric` | `name: str` | Defines or updates a metric definition |
| `vital` | `name: str` | Defines or updates a vital definition |
| `source_control` | `id: str`, `action: str` (remove\|disable\|enable) | Mutates an existing connector source |
| `metric_control` | `name: str`, `action: str` (remove) | Removes a metric definition |
| `vital_control` | `name: str`, `action: str` (remove) | Removes a vital definition |
| `goal_control` | `id: str`, `action: str` (cancel\|disable\|defer\|resume\|pin\|unpin\|prioritize\|schedule\|delete\|resolve-update) | Mutates an existing Objective |
| `executor_control` | `action: str` (attach\|detach\|retry-policy), `id: str` | Attaches, detaches, or configures an Executor |
| `policy_control` | `name: str`, `value: str` | Sets a named policy (self-evolution, change-explanations, external-metrics) |
| `budget_control` | `daily: int`, `monthly: int` | Sets Executor call budget limits |
| `evaluation_control` | `action: str` (set-weight\|set-minimum), `component?: str`, `value: num` | Configures the evaluation system |
| `intent_control` | `action: str` (add\|supersede\|deactivate), `statement?: str`, `rule_kind?: str` | Adds, supersedes, or deactivates a DIRECTIVE rule |
| `constraint_control` | `action: str` (add\|deactivate), `statement?: str`, `rule_kind?: str` (PROHIBITION\|PERMISSION) | Adds or deactivates a constraint rule |
| `schedule-task` | `task: ScheduledTask` | Registers a durable scheduled task (AP18) |

Optional `goal` payload fields: `reason`, `priority` (int 1–100), `target` (product\|urace), `expected_value`, `estimated_cost`, `risk`, `urgency`, `deadline`, `not_before`, `dependencies`, `pinned`.

---

## AP15 — Broadcast Log

**Derivation metadata.** `standalone: false` · `tier: COMPOSITIONAL` · `requires: [AP3]` · `provides: system-wide event bus, decoupled pub/sub, append-only event history`

**Intent.** The Broadcast Log is the system-wide event bus: an append-only log to which all components write events and from which all consumers read. Producers never directly notify consumers; consumers observe the log.

**Roles.**
- `BroadcastLog` — an AppendOnlyLog<Evidence> (AP3 instance)
- `Evidence` — the event record type; carries id, at, kind, source, detail
- `source` — the component identifier for each entry

**Definition.**
```
BroadcastLog = AppendOnlyLog<Evidence>  (AP3 instance)

Every Evidence entry has:
  id:     stable identifier (prefix `ev-`)
  at:     ISO-8601 timestamp
  kind:   Evidence kind (§62b Evidence kinds table)
  source: component identifier
  detail: freeform string or structured payload
```

**Constraints.**
- Because all communication flows through the log, any component can be replaced without modifying others — the log contract is the only interface. This is the architectural basis for URACE's executor-agnosticism (§75).

**Implementation.** `state.evidence`. Every cycle, every lifecycle command, every bridge translation, and every validation result appends at least one entry here. §60 machine/human channels.

---

## AP16 — State Snapshot + Delta Log

**Derivation metadata.** `standalone: false` · `tier: INTEGRATED` · `requires: [AP3, AP6]` · `provides: durable state snapshot, delta log, causal state reconstruction, atomic snapshot+delta writes`

**Intent.** The State Document is a combination of a current-value snapshot and append-only logs of changes. The current state is always immediately readable from the snapshot; the complete history is reconstructible from the logs.

**Roles.**
- `StateDocument` — the combined snapshot and delta log
- `snapshot` — directly readable current-value dict
- `delta_logs` — list of AppendOnlyLogs (evidence, status_transitions, etc.)

**Definition.**
```
StateDocument = {
  snapshot:    dict<field, current_value>  — directly readable
  delta_logs:  list<AppendOnlyLog>         — evidence, status_transitions, etc.
}

Reconstruction: state_at(t) = apply_deltas(earliest_snapshot_before(t), deltas_since(t))
```

**Constraints.**
- Every mutation to `snapshot` MUST: (1) Apply the mutation. (2) Append a corresponding entry to the relevant `delta_log`. (3) Write both atomically per the atomic write contract (§62f).
- A mutation that updates the snapshot without appending a delta log entry violates the causal provenance chain (AP6).

**Implementation.** §60 validation, §73 recovery. Governs all State Document mutations.

---

## AP17 — Lexical→Formula Reduction (Lexical Symbol Calculus)

**Derivation metadata.** `standalone: false` · `tier: COMPOSITIONAL` · `requires: [AP7]` · `provides: spec rule formalization, formula-linked rule pairs, machine-verifiable normative rules`

**Intent.** The Lexical Symbol Calculus (LSC) is the discipline of reducing natural language expressions — sets of words, characters, symbols, or compositions thereof — to their precise, minimal, canonical formula equivalents.

**Roles.**
- `LSC operator` — the reduction mapping from natural language to formula
- `reduce_to_formula(text)` — the 7-step reduction protocol
- `LexicalFormula` — the citizen pairing natural language and formula

**Operators.**

| Input | LSC operator | Output example |
|---|---|---|
| "must not decrease" | monotone lower-bound | `v(t+1) ≥ v(t)` |
| "sum to one" | normalization equality | `∑wᵢ = 1.0 ± ε` |
| "FIFO order" | sort by timestamp | `order ≡ sorted(items, key=λi: i.at)` |
| "within budget" | inequality guard | `calls_today < max_calls_per_day` |
| "not present" | set complement | `x ∉ S` |
| "all items" | universal quantifier | `∀ i ∈ S : P(i)` |
| "there exists" | existential quantifier | `∃ i ∈ S : P(i)` |
| "if and only if" | biconditional | `A ↔ B` |
| "causes / leads to" | causal implication | `A → B` |
| "within window" | temporal bound | `now() - item.at < window_seconds` |

**Reduction protocol.**

```
reduce_to_formula(text):
  1. Identify the normative verb (MUST, SHALL, SHOULD, MAY).
  2. Extract the subject (what entity).
  3. Extract the predicate (what property must hold).
  4. Select the LSC operator that maps the predicate to a formula.
  5. Bind variables from the subject to the formula.
  6. Verify: formula is satisfiable, unambiguous, and machine-checkable.
  7. If step 6 fails: SD = False → delegate semantic boundary to executor.
```

**Constraints.**
- SD condition: True when the normative text uses vocabulary from the LSC operator table above. False when the text involves open-ended semantic equivalence judgments — executor needed to verify.
- Every normative rule in this specification that can be expressed as a formula SHOULD include the formula alongside the prose. The formula is not a replacement for the prose; it is a machine-verifiable companion. Where a formula and prose conflict, the prose governs the intent and the formula governs the implementation.

**Implementation.** §62a rule formalization; spec rule formalization, machine-verifiable normative rules. Primary formulas in this specification:

| Location | Natural language | Formula |
|---|---|---|
| §62c Input Queue | inputs processed in FIFO order | `order ≡ sorted(inputs, key=λi: parse_ts(i.at))` |
| §62f retention | records within rolling window | `retain(r) ↔ now() − parse_ts(r.at) < retention_s` |
| §62b weight normalization | weights must sum to one | `∑wᵢ = 1.0 ± 1e-9 ∧ ∀i: wᵢ ≥ 0` |
| §62h T2 bar-raising | threshold non-decreasing | `threshold(t+1) ≥ threshold(t)` |
| §62h T4 paired invariant | lifecycle matches transition | `lifecycle_state = status_transitions[−1].status` |
| §62c discovery gate | calls within daily budget | `calls_today < max_calls_per_day ∧ calls_month < max_calls_per_month` |
| §60 acceptance | accept only when validated | `accept(op) ↔ validate(op).verdict = VALIDATED` |
| §62h T1 gap calculus | unimplemented rules | `gap(S, I) = {r ∈ S \| ¬∃i ∈ I: implements(i, r)}` |

---

## AP18 — Scheduled Task Contract

**Derivation metadata.** `standalone: false` · `tier: INTEGRATED` · `requires: [AP0, AP2, AP12, AP14]` · `provides: durable named scheduled tasks, ScheduledTask citizen, USER/SYSTEM task classes, trigger-based and time-based scheduling`

**Intent.** A scheduled task is a durable, named, time- or trigger-governed action that the runtime executes at a declared future point. Tasks are citizens (AP0): they have stable identity, schema conformance, and causal traceability.

**Roles.**
- `ScheduledTask` — the durable citizen record for a scheduled task (see §62b)
- `TaskSchedule` — the scheduling definition (CRON/INTERVAL_SECONDS/TRIGGER/IMMEDIATE)
- `USER task` — operator-created, preserved across updates
- `AUTO task` — runtime-created based on state analysis

**Definition.**
```
ScheduledTask = CitizenSchema  (see §62b)
TaskSchedule  = CitizenSchema  (see §62b)
```

**Task kinds.**
- **USER task.** Created by the operator via a `schedule-task` inbox input. Preserved across updates (AP19).
- **AUTO task.** Created by the runtime's auto-scheduling logic based on state analysis. Examples: when gap calculus (T1) detects new unimplemented rules → schedule `spec_audit`; when metric trend is declining → schedule `metric_investigation`; when systematic failure streak exceeds threshold → schedule `executor_health_check`.

**Auto-scheduling triggers.**

| Condition | Auto-scheduled task | Scope |
|---|---|---|
| `gap(spec_rules, impl) > 0` new entries since last audit | `spec_audit` | runtime |
| metric trend = declining for ≥ 2 consecutive cycles | `metric_investigation` | executor |
| `systematic_failure_streak ≥ systematic_failure_threshold` | `executor_health_check` | executor |
| no accepted improvement in ≥ 30 cycles | `bar_raising_check` | runtime |

**Execution protocol.**
1. At each cycle start, the runtime evaluates `task_due(task, now())` for each ACTIVE ScheduledTask.
2. A due task fires: `run_count += 1`, `last_run_at` set, next `next_run_at` computed.
3. For USER tasks, the `action` field specifies the lifecycle command to inject into the inbox.
4. For AUTO tasks, the runtime directly acts on the trigger (no inbox round-trip needed).
5. A task that fails 3 consecutive times is set to status `ERROR` and MUST NOT auto-retry.

**Scheduling formula.** For INTERVAL_SECONDS tasks:
```
next_run_at(t+1) = last_run_at(t) + interval_seconds
```

For TRIGGER tasks:
```
fire(task) ↔ evidence_log contains entry with kind = task.schedule.trigger_event
              AND entry.at > task.last_run_at (or task.created_at if never run)
```

**Constraints.**
- Task execution MUST be idempotent: running a task that has already been run this cycle produces no additional effect. The `last_run_at` field is the deduplication key.
- A task that fails 3 consecutive times is set to status ERROR and MUST NOT auto-retry.

**Implementation.** §42 scheduling, §62c scheduled tasks, §62b ScheduledTask and TaskSchedule citizens.

---

## AP19 — Customization / Personalization Layer

**Derivation metadata.** `standalone: false` · `tier: INTEGRATED` · `requires: [AP4, AP16]` · `provides: named scoped user overrides, conflict detection on spec update, CustomizationRecord citizen, three customization scopes`

**Intent.** The Customization Layer bridges the tension between specification-first development and user freedom. A URACE deployment MUST be reproducible from the specification, but a user MUST also be able to personalize their runtime, bootstrap file, or configuration without those choices being silently overwritten by spec updates.

**Roles.**
- `CustomizationRecord` — the citizen recording a named scoped override (see §62b)
- `scope` — config | spec_parameter | runtime_behavior
- `preserve_on_update` — the flag that protects user choices across spec updates
- `conflict_status` — the field surfacing spec/customization divergence

**Constraints.**
- The specification is the canonical ground truth. User customizations are explicit, named, scoped overrides. Customizations are preserved across updates; spec changes that conflict with customizations are surfaced as conflicts, not silently resolved.

**Implementation.** §62b CustomizationRecord citizen, AP19 spec update flow. §62c Customization Layer mechanism.

**Customization scopes.**

| Scope | What it governs | Update behavior |
|---|---|---|
| `config` | Values in `config.json` (thresholds, limits, paths) | Preserved; spec update cannot lower a user-raised threshold without conflict |
| `spec_parameter` | Named spec constants (e.g., INFER_BLOCKING threshold) | Preserved; spec change to same constant is flagged as CONFLICT |
| `runtime_behavior` | Named behavioral flags (e.g., `disable_auto_discovery`) | Preserved; spec new requirement that contradicts flag is flagged as CONFLICT |

**CustomizationRecord.** See §62b. Every customization is a durable citizen with `preserve_on_update` field.

**Conflict resolution protocol.**
```
on_spec_update(old_spec, new_spec, customizations):
  for each customization C in customizations where C.preserve_on_update = True:
    if new_spec changes the default for C.key:
      if C.value conflicts with new_spec.requirement(C.key):
        emit evidence kind "customization-conflict-detected"
              with detail: C.key, C.value, new_spec.requirement(C.key)
        status = CONFLICT  — user must resolve; do not auto-apply new default
      else:
        keep C.value  — customization is compatible with new spec
  apply remaining spec changes that do not conflict
```

**Bootstrap reproducibility guarantee.** A URACE bootstrap from a standard (unmodified) `URACE.md` MUST produce an identical initial state regardless of bootstrap executor. User customizations applied after bootstrap are additive and declared; they do not affect the reproducibility of the base bootstrap.

**User modification freedom.** A user MAY modify `URACE.md` to create a personalized fork. A user MAY modify `config.json`. A user MAY modify runtime source files. In all cases, the modifications are the user's responsibility; URACE cannot guarantee correctness of user-modified artifacts. The Customization Layer exists so that users can express their overrides *as customizations* (declared, preserved, conflict-detectable) rather than as silent edits that are lost on update.

**Preservation formula.**
```
preserve(C, update) ↔ C.preserve_on_update = True
                      ∧ ¬conflict(C, update)
```

---

## AP20 — Circuit Breaker

**Derivation metadata.** `standalone: false` · `tier: COMPOSITIONAL` · `requires: [AP4]` · `provides: proactive failure-rate gating, CLOSED/OPEN/HALF_OPEN state machine, configurable threshold and observation window, recovery probe, CircuitBreakerRecord citizen`

**Intent.** A Circuit Breaker monitors the recent failure rate of calls across a ProducerConsumerContract boundary and opens a gate to stop attempts entirely when that rate exceeds a configured threshold. It complements AP10 (Bounded Retry with Backoff): AP10 schedules retries after individual failures; AP20 stops attempts altogether when the failure rate indicates the downstream component is unavailable, preventing cascading failures.

**Roles.**
- `CLOSED` — normal operation; all calls proceed
- `OPEN` — all calls rejected immediately; probe timer counts down
- `HALF_OPEN` — single probe call allowed; success re-closes; failure re-opens
- `CircuitBreakerRecord` — the citizen recording a state transition

**State machine.**

```
CLOSED ──[failure_rate > threshold]──► OPEN
OPEN   ──[probe_timeout elapsed]───► HALF_OPEN
HALF_OPEN ──[probe succeeds]───────► CLOSED
HALF_OPEN ──[probe fails]──────────► OPEN
```

- **CLOSED**: normal operation; all calls proceed; failure rate is tracked in a rolling observation window.
- **OPEN**: all calls are rejected immediately without attempting the downstream component; a probe timer counts down.
- **HALF_OPEN**: a single probe call is allowed; success re-closes the breaker; failure re-opens it.

**CircuitBreakerRecord.** A state transition MUST produce a `CircuitBreakerRecord` citizen:

```
CircuitBreakerRecord {
  id                REQUIRED  stable identifier
  at                REQUIRED  timestamp of transition
  contract_id       REQUIRED  ProducerConsumerContract id this breaker guards
  prior_state       REQUIRED  CLOSED | OPEN | HALF_OPEN
  new_state         REQUIRED  CLOSED | OPEN | HALF_OPEN
  failure_rate      REQUIRED  float [0.0, 1.0]; rate that triggered the transition
  threshold         REQUIRED  float [0.0, 1.0]; configured threshold at time of transition
  observation_window_seconds  REQUIRED  float; rolling window used to compute failure_rate
}
```

Uses canonical: Identifier (id), iso_timestamp (at), probability (failure_rate, threshold).

**Constraints.**
- A system MAY adopt both AP20 and AP10. When both are active, AP20 gates whether an attempt is made at all; AP10 governs retry scheduling. AP20 MUST be evaluated before AP10 in the call path.
- A derived system that adopts AP20 without AP4 MUST document the contract boundary it guards using equivalent producer/consumer obligation notation.

**Implementation.** §43 systematic failure, §62c quality streak. The Quality Streak Mechanism (§62c) is the positive counterpart to AP20: where AP20 opens on high failure rate, the Quality Streak Mechanism expands autonomy on consecutive quality improvements. Both MUST be evaluated per assessment cycle.

---

## AP21 — Compaction

**Derivation metadata.** `standalone: false` · `tier: COMPOSITIONAL` · `requires: [AP3]` · `provides: rolling eviction with configurable retention, CompactionSummary citizen, ARCHIVE and ROLLING_EVICTION modes, decompaction contract, dry-run mode`

**Intent.** Any system built on AP3 (Append-Only Log) will eventually face unbounded growth. Compaction reduces log size while preserving full audit trail integrity: evicted entries are replaced by a `CompactionSummary` record that describes what was removed; the original data is archived and fully restorable via decompaction.

**Roles.**
- `CompactionSummary` — the durable citizen inserted at the compaction boundary
- `ARCHIVE` — evict entries older than retention window into named archive file
- `ROLLING_EVICTION` — keep N most recent entries; evict the rest
- `compaction_event_id` — the identifier linking a summary to its CompactionEvent

**Compaction modes.**

| Mode | Behavior |
|---|---|
| `ARCHIVE` | Evict entries older than retention window into a named archive file; CompactionSummary replaces them in the live log |
| `ROLLING_EVICTION` | Keep the N most recent entries; evict the rest; summary replaces evicted segment |

**CompactionSummary.** A durable citizen inserted into the log at the compaction boundary:

```
CompactionSummary {
  id                  REQUIRED  stable identifier
  at                  REQUIRED  timestamp of compaction
  compaction_event_id REQUIRED  identifier linking this summary to its CompactionEvent
  mode                REQUIRED  ARCHIVE | ROLLING_EVICTION
  evicted_count       REQUIRED  integer ≥ 1; number of entries replaced
  retained_count      REQUIRED  integer ≥ 0; entries kept in live log after this summary
  first_evicted_at    REQUIRED  iso_timestamp; earliest at-timestamp among evicted entries
  last_evicted_at     REQUIRED  iso_timestamp; latest at-timestamp among evicted entries
  archive_path        OPTIONAL  string; relative path to archive file (ARCHIVE mode only)
}
```

Uses canonical: Identifier (id, compaction_event_id), iso_timestamp (at as created_at, first_evicted_at, last_evicted_at), count (evicted_count, retained_count).

**Dry-run contract.** A compaction invoked with `dry_run: true` MUST compute and return the CompactionSummary without writing any state change. The dry-run result MUST be identical to what a live compaction would produce.

**Decompaction contract.** Given a `compaction_event_id`, the original evicted entries MUST be fully restorable from the archive. Decompaction MUST be idempotent. A decompaction that cannot locate the archive MUST surface a named error rather than silently succeed.

**Constraints.**
- Compaction MUST NOT reduce the logical entry count below the retained window. The monotone non-decreasing length invariant of AP3 applies to the logical count (live entries + evicted_count from all CompactionSummaries); the physical live log length MAY decrease after compaction.
- Dry-run contract: A compaction invoked with `dry_run: true` MUST compute and return the CompactionSummary without writing any state change.
- Decompaction contract: Given a `compaction_event_id`, the original evicted entries MUST be fully restorable from the archive. Decompaction MUST be idempotent.

**Implementation.** §62f compaction mechanism. Governs evidence log growth bounding.

---

## AP22 — Checkpoint

**Derivation metadata.** `standalone: false` · `tier: COMPOSITIONAL` · `requires: [AP0, AP3]` · `provides: durable integrity marker, crash-safe recovery anchor, content-addressable state verification, checkpoint kinds`

**Intent.** A Checkpoint is a durable integrity marker that binds a content-addressable state digest to a specific lifecycle moment. It enables three capabilities: crash recovery, state verification, and point-in-time audit.

**Roles.**
- `Checkpoint` — the durable citizen carrying id, at, kind, digest (see §62b)
- `kind` — bootstrap | accepted-product-change | assessment
- `DigestValue` — content-addressable SHA-256 hash of state at this moment

**Checkpoint citizen.**

```
Checkpoint {
  id           REQUIRED  stable identifier
  at           REQUIRED  timestamp
  kind         REQUIRED  bootstrap | accepted-product-change | assessment
  digest       REQUIRED  DigestValue; content-addressable hash of the state at this moment
  operation    OPTIONAL  Operation id; REQUIRED when kind = accepted-product-change
  transaction  OPTIONAL  Transaction id; REQUIRED when kind = accepted-product-change
}
```

Uses canonical: Identifier (id), iso_timestamp (at as created_at), DigestValue (digest).

**Constraints.**
- The first Checkpoint in any system MUST be of kind `bootstrap`. Its digest MUST reflect the state immediately after initialization completes. No operation MUST be applied before the bootstrap Checkpoint is durably written.
- On restart, if the last durable Checkpoint exists, the system MUST verify the current state digest matches it before proceeding. A digest mismatch MUST surface as a named integrity gap rather than silently proceeding.
- Checkpoints MUST be append-only (AP3). A Checkpoint's `at` timestamp MUST be greater than or equal to all prior Checkpoints' `at` timestamps.

**Implementation.** §61 checkpoint, §62c checkpoint mechanism. Governs all accepted-state anchoring.

---

## AP23 — Justification Chain

**Derivation metadata.** `standalone: false` · `tier: COMPOSITIONAL` · `requires: [AP6]` · `provides: decision-to-evidence traversal, rule-to-decision traversal, configurable depth with cycle detection, JustificationStep citizen, human-readable chain rendering`

**Intent.** A Justification Chain answers the question: *why was this decision made?* Starting from a decision record, it traverses backwards through the evidence that informed it and the rules that governed it, producing a human-readable chain of reasoning steps.

**Roles.**
- `JustificationChain` — the traversal from decision to evidence to rules
- `JustificationStep` — a single step in the chain (see §62b)
- `prior_decision_refs` — the causal pointer traversed via AP6
- `visited-id set` — the cycle detection mechanism

**JustificationStep citizen.**

```
JustificationStep {
  id           REQUIRED  stable identifier
  decision_id  REQUIRED  identifier of the decision this step belongs to
  step_index   REQUIRED  integer ≥ 0; position in the chain (0 = the decision itself)
  description  REQUIRED  string; human-readable statement of the claim or check at this step
  evidence_ref OPTIONAL  identifier of the Evidence record grounding this step
  rule_ref     OPTIONAL  identifier of the Rule that governed this step
  outcome      REQUIRED  PASS | FAIL | INCONCLUSIVE
  detail       OPTIONAL  string; additional detail
}
```

Uses canonical: Identifier (id, decision_id, evidence_ref, rule_ref), count (step_index).

**Traversal contract.** Given a decision id and an optional maximum depth:
1. Retrieve the decision record.
2. For each evidence ref in the decision, retrieve the Evidence record and emit a JustificationStep.
3. For each rule that governed the decision, retrieve the Rule record and emit a JustificationStep.
4. Recurse into parent decisions (via AP6 causal chain) up to the configured depth limit.
5. Detect cycles: if a decision id is encountered that is already in the current traversal path, emit a `CYCLE_DETECTED` step and stop that branch.

**Constraints.**
- A Justification Chain traversal MUST NOT loop indefinitely. The traversal MUST maintain a visited-id set and halt any branch that revisits a node.
- A system that adopts AP23 MUST also adopt AP6 to provide the causal evidence links that AP23 traverses. AP6 answers "what caused this state?"; AP23 answers "why was this decided?".

**Implementation.** §62g justification system, `urace why` command. §62b JustificationStep citizen.

---

## AP24 — Derivation Framework

**Derivation metadata.** `standalone: false` · `tier: INTEGRATED` · `requires: [AP0, AP2]` · `provides: PatternEntry citizen, PatternCatalog, DerivedSystemManifest, transitive dependency resolver, stale-manifest detection, zero-conformance guarantee, PatternAdoptionRecord citizen, PatternExclusionRecord citizen`

**Intent.** A Derivation Framework enables any system to declare a catalog of reusable structural patterns, resolve adoption of a chosen subset with automatic transitive dependency resolution, and produce a machine-readable manifest of that adoption.

**Roles.**
- `PatternEntry` — the citizen describing one adoptable pattern
- `PatternCatalog` — the append-only collection of PatternEntry records
- `DerivedSystemManifest` — the output artifact of one derivation run
- `PatternAdoptionRecord` — records one EXPLICIT or TRANSITIVE pattern adoption
- `PatternExclusionRecord` — records an acknowledged dep exclusion

**Zero-conformance guarantee.** A derived system that adopts zero patterns has zero AP24 obligations. A derived system that adopts exactly one pattern has obligations only for that pattern and its transitive dependencies (unless those deps are explicitly excluded). No top-level architectural decision is mandatory for a derived system.

**PatternEntry citizen.**

```
PatternEntry {
  id           REQUIRED  identifier; unique within the catalog (e.g. "AP0")
  name         REQUIRED  string; human-readable name
  standalone   REQUIRED  boolean; true ↔ the pattern may be adopted with no dependencies
  tier         REQUIRED  enum: FOUNDATIONAL | COMPOSITIONAL | INTEGRATED
  requires     REQUIRED  list[identifier]; pattern IDs this pattern depends on; [] when standalone
  provides     REQUIRED  list[string]; human-readable capability descriptions
  summary      OPTIONAL  string; single-sentence description for list views
  spec_section OPTIONAL  string; canonical location in the governing specification
}
```

Uses canonical: Identifier (id), boolean (standalone).

**Tier semantics.** `FOUNDATIONAL`: standalone or all deps are foundational; can always be adopted in isolation. `COMPOSITIONAL`: requires 1–2 other patterns. `INTEGRATED`: requires 3+ patterns or forms a deeply coupled cluster.

**PatternCatalog.** A named, append-only (AP3) collection of `PatternEntry` records. The catalog is the sole authority for pattern IDs known to the resolver. A reference to an unknown pattern ID is a resolver error. Catalog entries MUST NOT be removed; a deprecated pattern MUST be marked in its `summary` and MUST remain resolvable.

**Dependency resolution contract.** Given `explicit_patterns` and `excluded_ids`:
1. Seed a BFS queue with `explicit_patterns \ excluded_ids`.
2. For each pattern dequeued: if already seen or excluded, skip. Otherwise add to `resolved`; enqueue all `requires` not yet seen and not excluded, logging each transitive addition.
3. Sort `resolved` topologically: FOUNDATIONAL first, then COMPOSITIONAL, then INTEGRATED; break ties by pattern ID lexicographic order.
4. Return `(resolved, resolution_log)`.

An unknown pattern ID at any step MUST raise a named error. The resolver MUST NOT silently ignore unknown IDs.

**PatternAdoptionRecord citizen.**

```
PatternAdoptionRecord {
  pattern_id  REQUIRED  identifier
  name        REQUIRED  string
  adoption    REQUIRED  enum: EXPLICIT | TRANSITIVE
  tier        REQUIRED  enum: FOUNDATIONAL | COMPOSITIONAL | INTEGRATED
  provides    REQUIRED  list[string]
}
```

**PatternExclusionRecord citizen.**

```
PatternExclusionRecord {
  pattern_id       REQUIRED  identifier
  name             REQUIRED  string
  override_reason  REQUIRED  string; non-empty
  acknowledged     REQUIRED  boolean; MUST be true
}
```

`PatternExclusionRecord.acknowledged` MUST be `true`. This is a deliberate acknowledgment gate: an operator who excludes a transitive dependency MUST explicitly affirm awareness of the consequences.

**DerivedSystemManifest citizen.** The output artifact of one derivation run. Carries a stable `manifest_id`, the spec version it was derived from, and the full adoption + exclusion records. A DerivedSystemManifest is itself a citizen (AP0) and SHOULD be stored in the evidence log.

```
DerivedSystemManifest {
  manifest_id       REQUIRED  identifier
  derived_from      REQUIRED  string; name of the governing specification
  spec_version      REQUIRED  string; version of that specification
  intent            REQUIRED  string; what the derived system is for
  generated_at      REQUIRED  iso_timestamp
  adopted_patterns  REQUIRED  list[PatternAdoptionRecord]
  excluded_deps     OPTIONAL  list[PatternExclusionRecord]
  resolution_log    OPTIONAL  list[string]; human-readable dep resolution trace
}
```

Uses canonical: Identifier (manifest_id), iso_timestamp (generated_at).

**DerivedManifestRef citizen.** A lightweight reference to a saved DerivedSystemManifest, stored in `state.derivation_refs`. Each `--save` creates or replaces the `DerivedManifestRef` for this manifest.

```
DerivedManifestRef {
  id               REQUIRED  Identifier; prefix "dmr-"
  manifest_id      REQUIRED  string; stable ID of the referenced manifest
  spec_version     REQUIRED  string; spec version at time of derivation
  generated_at     REQUIRED  string; ISO-8601 timestamp
  adopted_pattern_ids REQUIRED list of string; pattern IDs used
  intent           REQUIRED  string; derivation intent
}
```

**DerivationRecord citizen.** Audit log entry for every `urace derive` invocation that produces a manifest, applies capabilities, refreshes, or drafts a milestone. Appended to `state.derivation_records`.

```
DerivationRecord {
  id               REQUIRED  Identifier; prefix "drv-"
  kind             REQUIRED  DerivationKind
  manifest_id      OPTIONAL  string; set when kind=MANIFEST or REFRESH
  pattern_ids      REQUIRED  list of string; patterns involved
  spec_version     REQUIRED  string; spec version at execution time
  derived_at       REQUIRED  string; ISO-8601 timestamp
  capabilities_applied OPTIONAL int; count of CapabilityStatements registered, when kind=CAPABILITY_APPLY
  milestone_drafted OPTIONAL boolean; True when kind=MILESTONE_DRAFT produced a draft
  delta_summary    OPTIONAL  string; human-readable summary of changes when kind=REFRESH
}
```

**DerivationKind enum.**

```
DerivationKind  MANIFEST | REFRESH | CAPABILITY_APPLY | MILESTONE_DRAFT
  MANIFEST       — standard derive --patterns run
  REFRESH        — re-derive saved manifest(s) with latest spec
  CAPABILITY_APPLY — --apply-capabilities wrote caps into config
  MILESTONE_DRAFT  — --derive-milestone produced a draft ProductMilestone
```


**Stale-manifest detection contract.** When the governing spec is updated, any stored DerivedSystemManifest whose `spec_version` differs from the new version MUST be surfaced as a `derived-manifest-stale` warning. The warning MUST include the `manifest_id`, the stale version, and the candidate version. Stale detection is a warning, not a blocker.

**Constraints.**
- AP24 requires AP0 (Citizen Schema Identity) to give every PatternEntry, PatternAdoptionRecord, PatternExclusionRecord, and DerivedSystemManifest a stable identity, and AP2 (Schema Contract) to enforce the schema invariants at write time.
- A reference to an unknown pattern ID is a resolver error. The resolver MUST NOT silently ignore unknown IDs.
- `PatternExclusionRecord.acknowledged` MUST be true — an acknowledgment gate.
- Stale-manifest detection MUST surface any stored DerivedSystemManifest whose `spec_version` differs from the new spec version.

**Implementation.** §62j derivation, `urace derive` command. PatternMechanismMapping in §62l provides the canonical AP-to-section lookup.

---

## AP25 — Bounded Evolution Band

**Derivation metadata.** `standalone: false` · `tier: INTEGRATED` · `requires: [AP9, AP2, AP4]` · `provides: capable sweet-spot enforcement, complexity ceiling, value density floor, capability completeness floor, maturity level classification`

**Intent.** A Bounded Evolution Band defines the zone in which a Product is "capable": above a capability completeness floor, below a complexity ceiling, and above a value density threshold.

**Roles.**
- `BoundedEvolutionBand` — the three-dimensional zone (floor, ceiling, density_floor)
- `floor` — minimum capability state the Product must maintain (AP9 governs monotonicity)
- `ceiling` — maximum surface measure before growth becomes over-engineering
- `sweet_spot_zone` — the valid evolution region

**Definition.**
```
BoundedEvolutionBand = {
  floor:           minimum capability state the Product must maintain (AP9 governs floor monotonicity)
  ceiling:         maximum surface measure before growth becomes over-engineering
  density_floor:   minimum value delivered per unit of surface
  sweet_spot_zone: { floor ≤ capability_completeness ≤ 1.0
                   ∧ surface_measure ≤ ceiling
                   ∧ value_density ≥ density_floor }
}
```

**Constraints.**
- AP9 (Monotone Accumulator) provides the floor — a value that MUST NOT decrease. AP25 adds the ceiling: a value that MUST NOT be exceeded without justification. Together they define the band. Without a ceiling, monotone accumulation produces bloat.
- Any subsystem that governs Product evolution MUST declare its bounded evolution band. Implicit ceilings (undeclared maximums) are architectural gaps. The band MUST be declared in Config.capability_envelope.

**Implementation.** `CapabilityEnvelope → Sweet Spot Evaluation Mechanism` — capability completeness floor + complexity ceiling. `ValueDensityRecord → SweetSpotAssessment` — density floor trend monitoring. `ProductMilestone → Capability Envelope Gate` — gate that enforces ceiling at CAPABLE maturity. §59b capable evolution, §62c envelope gate.

---

## AP26 — Lifecycle State Machine

**Derivation metadata.** `standalone: false` · `tier: FOUNDATIONAL` · `requires: [AP0, AP3]` · `provides: guarded lifecycle transitions, durable state recording, 12 named lifecycle states, entry/exit condition enforcement, inspectable state without Executor invocation`

**Intent.** A Lifecycle State Machine defines a finite set of named lifecycle states, each with defined entry conditions, exit conditions, and transition guards. State transitions are deterministic and MUST be durably recorded before the new state is entered. The machine is authoritative for all lifecycle-state decisions; implicit or inferred states are prohibited.

**Roles.**
- `State` — a durable named lifecycle condition with defined entry/exit semantics
- `Transition` — a guarded, atomic move from one State to another
- `Guard` — entry or exit condition that MUST be satisfied before transition
- `Trigger` — a qualifying event that initiates a Transition

**Constraints.**
- Every Transition MUST be atomic and durably recorded before entry into the new State.
- No State may be entered without a qualifying Trigger.
- No State may be exited while its exit Guard is unsatisfied.
- The current State MUST be inspectable without Executor invocation (SD=True).
- Implicit or inferred states are prohibited; every reachable State MUST be named.

**Implementation.** §64 Lifecycle State Machine (12 states: ASSESSING, ACTIVE, VALIDATING, RECONCILING, REPAIRING, WAITING_FOR_CAPACITY, WAITING_FOR_CONDITION, WAITING_FOR_SCHEDULE, WAITING_FOR_AUTHORITATIVE_DECISION, BLOCKED, PAUSED, DORMANT). Governs all lifecycle-state transitions throughout the specification.

---

## AP27 — Transaction Recovery Protocol

**Derivation metadata.** `standalone: false` · `tier: INTEGRATED` · `requires: [AP3, AP16]` · `provides: crash-consistent mutation, four-phase durable journal, deterministic recovery disposition, phase-specific rollback/roll-forward`

**Intent.** A four-phase durable journal that guarantees crash-consistent mutation and deterministic recovery. Each phase transition is durably written before the corresponding action is taken; recovery re-enters at the last durable phase and applies the phase-specific disposition (rollback or roll-forward).

**Roles.**
- `Journal` — the durable, phase-progressive record of a single mutation
- `Phase` — one of PREPARED, APPLYING, APPLIED, VALIDATED
- `Disposition` — the phase-specific recovery action (rollback or roll-forward)
- `Checkpoint` — the durable accepted state after VALIDATED phase

**Constraints.**
- Phase write MUST precede the corresponding action.
- On recovery: PREPARED → unconditional rollback; APPLYING → unconditional rollback; APPLIED → re-run validation; VALIDATED → treat as committed.
- A Journal MUST NOT be deleted before its Checkpoint is durable.
- Partial APPLYING phase: affected artifacts MUST be individually preserved in durable state.

**Implementation.** §52–§53 Crash-Consistent Acceptance, §62c Transaction Mechanism. Governs all Operation acceptance boundaries.

---

## AP28 — Independent Validation Gate

**Derivation metadata.** `standalone: false` · `tier: COMPOSITIONAL` · `requires: [AP4, AP14]` · `provides: executor≠validator separation, pending-preservation, capability-restoration trigger, PendingValidation citizen, ValidationVerdict`

**Intent.** An architectural separation where the entity that produces a result is categorically different from the entity that validates it. Executor confidence is never a substitute for independent validation. Pending validation obligations survive executor replacement and MUST be preserved until validation capability is restored.

**Roles.**
- `Producer` — the context that generates a result (executor)
- `Validator` — an independent context that verifies the result
- `PendingValidation` — a durable record of an unresolved validation obligation
- `ValidationVerdict` — the authoritative outcome (VALIDATED or requires rollback)

**Constraints.**
- Producer and Validator MUST be categorically different contexts.
- Executor confidence MUST NOT substitute for a ValidationVerdict.
- Validation capability unavailability MUST preserve the PendingValidation; elapsed time MUST NOT advance state to accepted.
- Inconclusive validation MUST be distinguished from validation capability unavailability.
- Capability restoration is a qualifying reassessment trigger for all PendingValidations.

**Implementation.** §54 Validation, §60 Validation gate, §64 VALIDATING state, §62b PendingValidation citizen.

---

## AP29 — Dormancy/Wakeability Contract

**Derivation metadata.** `standalone: false` · `tier: COMPOSITIONAL` · `requires: [AP0, AP3]` · `provides: verified dormancy entry, cost-bounded liveness path, WakeRegistration citizen, wake-integrity-gap, dormancy prohibition while gap exists`

**Intent.** An autonomous system is legitimately DORMANT only when (a) no justified authorized action exists AND (b) a verified, cost-bounded wakeability mechanism observes a qualifying change. A system without a verifiable liveness path is stopped, not dormant.

**Roles.**
- `DormancyState` — valid autonomous non-activity while liveness path is verified
- `WakeabilityMechanism` — the concrete mechanism (scheduler, callback, poller, file-watcher) that observes a qualifying change
- `LivenessPath` — the verified, cost-bounded route back to assessment
- `WakeRegistration` — a durable record of an active wakeability mechanism

**Constraints.**
- Dormancy MUST NOT be declared unless a verified WakeabilityMechanism exists.
- The LivenessPath MUST be cost-bounded; unbounded credit-spend per wake cycle violates this contract.
- WakeRegistrations MUST be verified active at every restart; unverifiable entries MUST produce a wake-integrity-gap.
- Wake latency MUST be bounded by a configured ceiling.
- Discovery Yield Exhaustion dormancy MUST hold at the discovery backoff ceiling.

**Implementation.** §66 Autonomous Operation, §67 Dormancy and Wakeability, §62c Wake Registration Verification Mechanism, §62c Discovery Credit Gate.

---

## AP30 — Partial Blocking Dependency Graph

**Derivation metadata.** `standalone: false` · `tier: COMPOSITIONAL` · `requires: [AP0, AP3]` · `provides: DAG-based minimum blocked-set computation, cycle detection, topological evaluation order, OperationDependency citizen`

**Intent.** When a blocking condition affects one scope, only the minimal dependent scope set is blocked. Dependencies are declared as a directed acyclic graph; the blocked set is the transitive closure over the dependency graph from the blocked node. Unaffected scopes continue independently.

**Roles.**
- `DependencyGraph` — the DAG of declared operation dependencies
- `BlockedNode` — the operation or scope directly subject to a blocking condition
- `BlockedSet` — the transitive closure over the DependencyGraph from the BlockedNode
- `UnaffectedScope` — any operation or scope outside the BlockedSet; continues independently

**Constraints.**
- The DependencyGraph MUST be acyclic; URACE MUST validate the DAG invariant before scheduling.
- The BlockedSet MUST be the minimum sufficient set; over-blocking is wasteful but not a violation.
- DAG-computed blocking MUST supersede heuristic scope estimation.
- Cycle detection MUST occur before any operation in a cyclic cluster is scheduled.
- Topological evaluation order: FOUNDATIONAL before COMPOSITIONAL before INTEGRATED (AP24).

**Implementation.** §65 Partial Blocking, §62b OperationDependency citizen.

---

## AP31 — Safe Runtime Activation

**Derivation metadata.** `standalone: false` · `tier: INTEGRATED` · `requires: [AP27, AP16, AP4]` · `provides: isolated candidate preparation, crash-consistent activation boundary, fallback preservation, post-start health confirmation, stable promotion`

**Intent.** A new runtime candidate is prepared outside the active runtime, validated against accepted tests, activated through a crash-consistent boundary, and promoted to stable only after post-start health confirmation. The prior runtime is preserved as a rollback fallback until stable promotion.

**Roles.**
- `Candidate` — the new runtime prepared in an isolated environment outside the active runtime
- `Active` — the currently executing runtime
- `Stable` — the Candidate after successful post-start health confirmation and promotion
- `Fallback` — the prior Active runtime, preserved until Stable promotion

**Constraints.**
- Candidate MUST be prepared outside the Active runtime.
- Accepted and candidate tests MUST pass before activation.
- Activation boundary MUST be crash-consistent (AP27 Transaction Recovery Protocol applies).
- Fallback MUST be preserved until Stable promotion.
- Any failure before Stable promotion MUST restore the Fallback.
- Authoritative spec and durable state MUST be preserved across activation.

**Implementation.** §74 Safe Runtime Activation, §62c Self-Evolution Eligibility Gate.

---

## AP32 — Single-Writer Ownership Lock

**Derivation metadata.** `standalone: false` · `tier: COMPOSITIONAL` · `requires: [AP0, AP3]` · `provides: durable ownership attribution, liveness-verified single-writer, OwnershipMarker citizen, INDETERMINATE liveness path, stale-overwrite prohibition`

**Intent.** A durable record (OwnershipMarker) attributes write access to a single runtime instance at a time. Liveness is verified via process signal or equivalent mechanism. When liveness is INDETERMINATE, only authenticated operator clearance may proceed. Stale-overwrite is categorically prohibited.

**Roles.**
- `OwnershipMarker` — the durable record attributing write ownership to one runtime instance
- `LivenessCheck` — verification of owner process activity via signal or equivalent
- `OperatorClearance` — the authenticated override path when liveness is INDETERMINATE

**Constraints.**
- Stale-overwrite is PROHIBITED under all conditions.
- INDETERMINATE liveness MUST route to OperatorClearance; autonomous clearance is prohibited (OperatorGateProtocol, §62l).
- OwnershipMarker is cleared only by the owning instance or by authenticated operator action.
- ConcurrencyPolicy governs maximum concurrent runtimes and liveness timeout.

**Implementation.** §63 Concurrency and Ownership, §62b OwnershipMarker citizen.

---

## AP33 — Policy Enforcement Gate

**Derivation metadata.** `standalone: false` · `tier: COMPOSITIONAL` · `requires: [AP4, AP0]` · `provides: pre-commit scope-intersection policy evaluation, HARD violation blocking, SOFT violation warning with override path, gate-before-commit ordering`

**Intent.** Immediately before any consequential commit, all active PolicyRecords and HardConstraints whose scope intersects the operation scope are evaluated. HARD violations block unconditionally. SOFT violations surface a warning with a DecisionRecord override path. The gate fires before the commit is finalized.

**Roles.**
- `PolicyRecord` — a soft behavioral constraint with ADVISORY or APPROVAL_REQUIREMENT enforcement
- `HardConstraint` — an unconditional blocker that cannot be overridden autonomously
- `ScopeIntersection` — the applicability filter matching constraint scope to operation scope
- `EnforcementGate` — the pre-commit evaluation step

**Constraints.**
- Gate MUST fire before consequential commit for every operation.
- ScopeIntersection determines applicability; non-intersecting constraints are skipped.
- HARD violation → BLOCK; no autonomous override path.
- SOFT violation → WARNING; override requires a DecisionRecord.
- Gate-before-commit ordering MUST be preserved; late enforcement is a violation.

**Implementation.** §72 Policy Enforcement, §62b PolicyRecord and HardConstraint citizens.

---

## AP34 — Self-Evolution Eligibility Gate

**Derivation metadata.** `standalone: false` · `tier: INTEGRATED` · `requires: [AP4, AP0, AP3]` · `provides: 3-mode eligibility gate (DISABLED/NECESSARY_ONLY/CONTINUOUS), gate-before-authority ordering, fail-closed default, durable GateDecision before downstream action`

**Intent.** Before any self-modification proceeds, a three-mode gate evaluates eligibility against durable policy. The gate is executor-agnostic, reads only durable state, and fails closed. Gate evaluation is durably recorded before any downstream action.

**Roles.**
- `EligibilityMode` — DISABLED, NECESSARY_ONLY, or CONTINUOUS
- `ExecutorProposal` — the executor's necessity assertion (self_evolution_necessary, necessity_evidence, lower_impact_route_sufficient)
- `GateDecision` — the durable evaluation record produced before downstream action

**Constraints.**
- Gate MUST fire before Authority Resolution for self-modification.
- DISABLED → no self-modification permitted under any circumstance.
- NECESSARY_ONLY → ExecutorProposal MUST assert necessity + provide necessity_evidence + confirm no lower-impact route.
- Gate reads only durable state (SD=True); no Executor invocation to determine gate outcome.
- On unreadable policy: fail-closed to NECESSARY_ONLY.
- Every evaluation MUST produce a durable GateDecision before any downstream action.

**Implementation.** §62c Self-Evolution Eligibility Gate, §74 Self-Evolution.

---

## AP35 — Governance Ledger

**Derivation metadata.** `standalone: false` · `tier: FOUNDATIONAL` · `requires: [AP0, AP3]` · `provides: L0/L1/L2 immutability tiers, rule DAG (SUPERSEDES/REFINES/REQUIRES/CONFLICTS_WITH/DERIVED_FROM), conflict detection, ConflictHold, ChangeBinding, decaying confidence for system-inferred rules`

**Intent.** A hierarchical, append-only rule store with three immutability tiers and a directed acyclic graph of rule relationships. Conflict detection is mandatory; conflicting rules are held pending resolution. System-inferred rules carry decaying confidence scores.

**Roles.**
- `Rule` — a governed behavioral constraint with kind, scope, immutability tier, and lifecycle
- `ImmutabilityTier` — L0 (unconditional prohibition), L1 (Authority-immutable), L2 (mutable within Authority)
- `RuleDAG` — the directed graph of SUPERSEDES, REFINES, REQUIRES, CONFLICTS_WITH, DERIVED_FROM relationships
- `ConflictHold` — the suspended state for conflicting rules awaiting resolution
- `ChangeBinding` — the temporal record linking a Change to the rules active at acceptance

**Constraints.**
- Ledger is append-only with supersession (AP3); rules MUST NOT be deleted.
- L0 violations MUST be denied unconditionally; no override path.
- L1 rules MUST NOT change except by Authority action.
- Conflicting rules MUST be detected on insertion and held until resolved.
- System-inferred rule confidence MUST decay in the absence of supporting Evidence.
- ChangeBinding MUST record the full active rule snapshot at acceptance time.

**Implementation.** §62a Rule Ledger, §62c Authority Resolution Mechanism, §62c Destination Anchor Integrity Mechanism.

---

## AP36 — Digest Chain Consistency

**Derivation metadata.** `standalone: false` · `tier: INTEGRATED` · `requires: [AP3, AP16, AP22]` · `provides: fixed SHA-256 digest algorithm, chain-continuity invariant (state_after[N]=state_before[N+1]), provenance-violation detection, three distinct digest types`

**Intent.** A sequence of durable state snapshots where each snapshot's digest is computed by a fixed, deterministic algorithm over canonical sorted content. The digest of the state after accepting snapshot N MUST equal the digest of the state before producing snapshot N+1. Any break in the chain is a provenance violation.

**Roles.**
- `StateDigest` — the SHA-256 hash of canonical sorted state content
- `ChainLink` — the invariant: state_after_digest[N] = state_before_digest[N+1]
- `DigestAlgorithm` — the fixed, deterministic computation (canonical sorted JSON, stable encoding)
- `ProvenanceViolation` — a detected chain break, surfaced as IntegrityGap

**Constraints.**
- DigestAlgorithm MUST be fixed; implementations MUST NOT vary serialization.
- ChainLink invariant MUST be verified on every recovery.
- A detected chain break MUST be surfaced as an IntegrityGap before any further mutation.
- Three distinct digest algorithms apply: Product Digest (sorted product files), Rule Snapshot Digest (sorted active rules as JSON), State Digest (canonical state content).

**Implementation.** §62c Digest Computation Contract, §62e CognitiveResumeContext, §62b DigestValue canonical type.

---

## AP37 — Compliance Posture Tracker

**Derivation metadata.** `standalone: false` · `tier: INTEGRATED` · `requires: [AP28, AP3, AP0]` · `provides: per-domain compliance trajectory (append-only), live accumulator (consecutive_clean/last_checked_at/violation_refs), compliance-record-missing gap, SD=True compliance inspection`

**Intent.** Per-domain compliance evaluation outcomes are persisted as an append-only trajectory and a live accumulator. After every independent validation gate evaluation, one record per assessed domain MUST be appended. The accumulator tracks consecutive clean counts, last evaluation timestamps, and violation references across executor replacements.

**Roles.**
- `ComplianceRecord` — the immutable per-domain evaluation outcome appended after each gate evaluation
- `ComplianceState` — the live per-domain accumulator (consecutive_clean, last_checked_at, violation_refs)
- `ComplianceDomain` — one of: authority, intent, schema, constraint, governance
- `CompliancePosture` — the current per-domain COMPLIANT/NON_COMPLIANT/UNKNOWN state

**Constraints.**
- One ComplianceRecord per domain MUST be appended after every independent validation gate evaluation.
- Absence of a ComplianceRecord for an assessed domain is a `compliance-record-missing` WARNING IntegrityGap.
- ComplianceState MUST persist across executor replacement; it is product-level durable state.
- `consecutive_clean` MUST increment on COMPLIANT and reset to 0 on NON_COMPLIANT.
- The `urace /compliance` command is SD=True; zero executor invocations required.

**Implementation.** §60 Compliance Recording Contract, §62b ComplianceRecord and ComplianceState citizens, r48.

---

## AP38 — Community Signal Ingestion

**Derivation metadata.** `standalone: false` · `tier: INTEGRATED` · `requires: [AP14, AP4, AP3, AP0]` · `provides: agnostic feed ingestion (any channel), T&C gate, relevance+confidence signal scoring, patch proposal pipeline with configurable approval modes (AUTO/SMART/HUMAN)` · `realizes: [CSI, PPP_M, PPP]`

**Intent.** Community discourse from any configured feed or communication channel is continuously ingested, quality-filtered, and surfaced as bounded patch proposals for URACE or the Product. The pipeline is communication-channel-agnostic: every source is configured as a `CommunityFeed` record with a pluggable `FeedAdapterKind`. Operators configure feeds, accept T&C, and choose an approval mode. Proposals advance through a configurable pipeline; URACE MUST NOT apply any proposal without APPROVED status.

**Roles.**
- `CommunityFeed` — a configured agnostic source (any channel type) with adapter kind, endpoint, T&C state
- `CommunitySignal` — a raw ingested signal scored on relevance (semantic overlap with current scope) and confidence (evidence of community consensus)
- `PatchProposal` — a bounded patch candidate derived from a quality-passing signal; held in the approval queue until APPROVED, REJECTED, or EXPIRED
- `ApprovalMode` — the pipeline mode in effect: AUTO, SMART, or HUMAN

**Constraints.**
- A `CommunityFeed` MUST NOT be ingested until `terms_accepted = true`; violation emits `community-feed-terms-not-accepted` BLOCKING gap.
- Every `CommunitySignal` MUST be scored on two orthogonal dimensions before queuing: `relevance_score` (semantic overlap with current Objectives and Intent) and `confidence_score` (evidence of actionable community consensus, not individual noise).
- A signal with `relevance_score < Config.community_inbox.relevance_floor` MUST be discarded immediately, setting `filtered = true`; emits `community-signal-relevance-below-floor` INFO gap.
- A signal that passes `relevance_floor` but has `confidence_score < Config.community_inbox.confidence_threshold` MUST NOT produce an APPROVED or AUTO_APPROVED PatchProposal; it MUST be recorded with `status = CONFIDENCE_INSUFFICIENT`; emits `patch-proposal-confidence-below-floor` INFO gap.
- The active `PatchProposal` count (status = PENDING or CONFIDENCE_INSUFFICIENT) MUST NOT exceed `Config.community_inbox.max_queue_depth`; if the ceiling is reached, new proposals MUST be blocked and `patch-proposal-queue-overflow` WARNING surfaced.
- A PatchProposal not resolved within `Config.community_inbox.proposal_expiry_hours` MUST transition to EXPIRED.
- Approval mode governs advancement: `AUTO` — proposals with `confidence_score ≥ 0.80` MAY be auto-approved (status = AUTO_APPROVED) without operator confirmation; below 0.80 falls through to SMART evaluation. `SMART` — URACE pre-scores and surfaces top candidates with rationale; URACE MAY autonomously reject proposals below the quality floor; operator confirmation required for final application. `HUMAN` — URACE MUST NOT set status to APPROVED without an attributable operator input; AUTO_APPROVED is prohibited in HUMAN mode.
- The sweet-spot composition is `SMART`: it eliminates operator burden for clear low-quality signals while preserving human authority over application.
- Confidence scoring MUST treat a single uncorroborated mention as `confidence_score = 0.5`; corroborating independent mentions MUST push the score toward 1.0; contradicting mentions MUST push toward 0.0. The scoring algorithm is Executor-supplied but the boundary semantics are normative.
- All approved PatchProposals applied to URACE MUST comply with `Config.self_evolution_policy`; application to the Product is an ordinary authorized Operation subject to applicable Authority.

**Implementation.** §62c Community Signal Ingestion Mechanism (CSI), §62c Patch Proposal Pipeline Mechanism (PPP_M), AP14 (Durable Inbox for proposal queue), AP4 (feed adapter producer-consumer contract), AP3 (append-only signal log), AP0 (CommunityFeed/CommunitySignal/PatchProposal as citizens).

---

## Canonical Scalar Catalog

All primitive value types used in citizen schemas. Every field that holds one of these types MUST reference the canonical scalar name.

| Scalar | Type | Domain | Null policy |
|---|---|---|---|
| `probability` | float | [0.0, 1.0] | PROHIBITED |
| `iso_timestamp` | string | RFC-3339 / ISO-8601 with timezone | PROHIBITED |
| `identifier` | string | `^[a-z][a-z0-9]*-[A-Za-z0-9]+$` | PROHIBITED |
| `count` | integer | ≥ 0 | PROHIBITED |
| `budget_fraction` | float | [0.0, 1.0] | PROHIBITED |
| `confidence` | float | [0.0, 1.0] | PROHIBITED |
| `severity_level` | enum | INFO \| WARNING \| ERROR \| CRITICAL | PROHIBITED |
| `duration_seconds` | float | ≥ 0.0 | PROHIBITED |
| `rfc2119_keyword` | enum | MUST \| MUST NOT \| SHALL \| SHALL NOT \| SHOULD \| SHOULD NOT \| MAY \| NEED NOT | PROHIBITED |
| `lifecycle_state_value` | enum | ASSESSING \| DORMANT \| BLOCKED \| PAUSED | PROHIBITED |
| `verdict_value` | enum | VALIDATED \| REJECTED \| PENDING_CAPABILITY | PROHIBITED |

---

## Bridge Topology

```
  ┌─────────────────────────────────────────────────────────────────────────┐
  │                         URACE Bridge Topology                           │
  │                                                                         │
  │   URACE.md ──B1──► Spec Audit ──────► IntegrityGap | Evidence           │
  │   (normative rules)  (gap calculus)   (broadcast log entry)             │
  │                                                                         │
  │   Executor ──B2──► Input Queue ─────► Input Dispatcher ──► State       │
  │   (JSON resp)        (durable inbox)  (handler registry)   (snapshot)  │
  │                                                                         │
  │   Metrics ──B3──► Validation Gate ──► check record ──► verdict         │
  │   (raw obs)         (guardrail eval)  (PASS|FAIL)    (VALIDATED|REJ.)  │
  │                                                                         │
  │   State ──B4──► Inspection ─────────► human-readable output            │
  │   (snapshot)     (render component)   (AP13 observer)                  │
  └─────────────────────────────────────────────────────────────────────────┘
```

Add B4 — State→Inspection bridge: translates the internal state snapshot into human-readable inspection output. Implemented by the runtime's inspection render component.

---

## Architectural Composition: How Patterns Interlock

```
  AP0 (Citizen) ──identity─► AP2 (Schema) ──validates─► AP3 (Log)
  AP17 (LSC)   ──reduces──► AP7 (SRLC)   ──canonizes─► AP1 (Scalar)
  AP18 (Sched) ──triggers─► AP12 (Orch.)  ──writes───► AP14 (Inbox)
  AP19 (Custom)──overrides► AP4 (Contract)──preserved─► AP16 (Snap)

  AP1 (Scalar) ──forms─► AP2 (Schema) ──populates─► AP3 (Log)
       │                       │                          │
       │                  AP5 (Idem.)              AP6 (Causal)
       │                       │                          │
  AP7 (SRLC) ──reduces─► AP4 (Contract) ◄──bridges── AP11 (Bridge)
       │                       │                          │
  AP8 (Fixpt) ──iterates─► AP12 (Orch.) ──sequences─► AP14 (Inbox)
       │                       │                          │
  AP9 (Mono.) ──guards──► AP10 (Retry) ──feeds──────► AP15 (Bcast)
                               │                          │
                          AP13 (Observer) ◄─────reads─────┘
                               │
                          AP16 (Snapshot+Log)
                               │
                          AP20 (Circuit Breaker) ──gates──► AP4 (Contract)
                               │
                          AP21 (Compaction) ──reduces──► AP3 (Log)
                          AP22 (Checkpoint) ──anchors──► AP3 (Log)
                          AP23 (Justification) ──traverses──► AP6 (Causal)
                          AP24 (Derivation) ──identities──► AP0 (Citizen)
                                           ──validates──► AP2 (Schema)
```

---

# 62j. Derivation Framework

This section implements **AP24 — Derivation Framework** (§62i). The runtime mechanism described here is the URACE instantiation of AP24: the PatternCatalog is defined in §62i (AP0–AP37), the resolver implements the AP24 dependency resolution contract, and the manifest output is a `DerivedSystemManifest` citizen.

URACE is specification-first: an implementation MUST conform to the spec. But a **derived system** — a new system built by adopting a chosen subset of URACE architectural patterns — is NOT required to conform to any pattern it has not explicitly adopted. The Derivation Framework is the canonical mechanism for declaring, resolving, and documenting that adoption.

## Zero-Conformance Guarantee

A derived system that adopts zero URACE patterns has zero URACE obligations. A derived system that adopts exactly one pattern (e.g. AP5 Idempotency Contract) has obligations only for that pattern. **No top-level architectural decision is mandatory for a derived system.** The only requirement is that each adopted pattern is correctly applied and its declared dependencies are either also adopted or explicitly excluded with a documented reason.

This guarantee applies to ALL patterns including foundational ones. A derived system MAY choose to adopt AP14 (Durable Inbox) without AP5 (Idempotency Contract) if the operator explicitly excludes AP5 and documents why. The exclusion is acknowledged, not enforced.

## Pattern Adoption Tiers

Every AP0–AP37 carries a **derivation metadata block** declaring its tier, standalone status, dependency list, and capabilities. Three tiers exist:

| Tier | Definition | Pattern IDs |
|------|-----------|-------------|
| `FOUNDATIONAL` | standalone=true, or all declared dependencies are themselves foundational | AP0, AP1, AP2, AP3, AP4, AP5, AP7, AP26, AP35 |
| `COMPOSITIONAL` | requires foundational and/or other compositional APs | AP6, AP8, AP9, AP10, AP11, AP12, AP13, AP14, AP15, AP17, AP20, AP21, AP22, AP23, AP28, AP29, AP30, AP32, AP33 |
| `INTEGRATED` | depends on integrated APs or forms a multi-AP cluster | AP16, AP18, AP19, AP24, AP25, AP27, AP31, AP34, AP36, AP37, AP38 |

A FOUNDATIONAL pattern can always be adopted in isolation. A COMPOSITIONAL or INTEGRATED pattern requires transitive dependency resolution unless deps are explicitly excluded.

## Citizen Schemas

The canonical schemas for this section — `PatternEntry`, `PatternAdoptionRecord`, `PatternExclusionRecord`, and `DerivedSystemManifest` — are defined in **AP24 — Derivation Framework** (§62i). All citizen schema obligations from AP24 apply here.

**Transitive resolution is automatic.** When a user requests AP8, the resolver automatically adds AP3 and AP5. When a user requests AP16, the resolver adds AP3, AP4, AP6 (and AP6 adds AP3, AP4 again — deduped). The `resolution_log` in the manifest records every transitive addition.

**Explicit exclusion overrides transitive resolution.** If the user passes `--exclude AP3` with `--exclude-reason "using our own log system"`, AP3 is excluded from the manifest and marked in `excluded_deps` with `acknowledged: true`. The adopted pattern (AP8) still appears in the manifest but AP3 does not. The operator assumes responsibility for the excluded pattern's obligations.

## `urace derive` Command Contract (AP24 — Derivation Framework instantiation, §62i)

```
urace derive [<intent>]
             [--kind pattern|mechanism|schema|protocol|contract|all]
             [--constructs <comma-list>] [--bundle <name>] [--suggest] [--from-goals] [--from-constraints] [--from-inspection]
             [--exclude <comma-list>] [--exclude-reason <text>]
             [--out <path>] [--save] [--json]
             [--derive-capabilities] [--apply-capabilities]
             [--refresh [--manifest-id <id>]]
             [--show-delta]
             [--derive-milestone]
             [--list-bundles]
```

**`--bundle <name>` flag.** Resolves a named `FeatureBundle` to its full `construct_ids` list and merges it with any explicit `--constructs` IDs (explicit takes precedence; bundle adds non-overlapping IDs). The bundle name MUST match a registered FeatureBundle (spec-defined or operator-defined). If the name is not found, the command MUST exit with code 1 and a human-readable error listing available bundle names. `--bundle` MAY be combined with `--constructs`; both lists are merged. `--bundle` MAY be used with `--suggest` to preview the resolved construct list without building a manifest. `--save` with `--bundle` creates a FeatureBundleRef in `state.feature_bundle_refs`.

**`--list-bundles` flag.** Lists all registered FeatureBundles (spec-defined and operator-defined) with their name, construct_ids, spec_version, and description. No state access required for spec-defined bundles. Operator-defined bundles are read from `state.feature_bundle_refs`.

**Built-in spec-defined FeatureBundles.**

| Bundle name | construct_ids | Description |
|---|---|---|
| `community-inbox` | AP38, CSI, PPP_M, PPP, CommunityFeed, CommunitySignal, PatchProposal, FeatureBundle, FeatureBundleRef | All constructs for community signal ingestion and patch proposal pipeline |

**FeatureBundle stale-detection contract.** When `urace update download` or `urace update apply` runs and `state.feature_bundle_refs` is non-empty, the implementation MUST compare each ref's `spec_version` to the candidate spec version. Any mismatch MUST be surfaced as a `derived-construct-set-stale` warning (reusing existing gap kind). The warning MUST include the `bundle_name`, the stale `spec_version`, and the candidate version. This is a warning, not a blocker. A stale bundle MAY still be applied via `--bundle`; the staleness warning is informational. If the operator runs `urace derive --bundle <name> --save`, the saved FeatureBundleRef is refreshed to the current spec version.

**Bundle-derive precedence.** When `--bundle <name>` and `--constructs <list>` are used together, explicit `--constructs` IDs take precedence over bundle IDs for any overlap. Bundle IDs that do not conflict with explicit IDs are merged in. When `--bundle` is used with `--from-goals`, `--from-constraints`, or `--from-inspection`, the bundle's construct_ids are merged with the suggestion results; bundle IDs take precedence over any suggestion result for the same construct. `--bundle` MUST NOT be used with `--refresh` in isolation (refresh requires a saved manifest reference); if used together, `--bundle` is ignored and a warning is surfaced.

**FeatureBundle dependency resolution.** When `--bundle <name>` resolves a FeatureBundle, each AP construct in the bundle's `construct_ids` has its transitive `requires:` dependencies resolved and merged into the manifest (same as `--constructs` AP resolution). Non-AP constructs (Mechanisms, Protocols, Schemas) in the bundle are included as-is, without transitive AP resolution, since their `governed-by:` is advisory for derivation purposes. If a construct_id in the bundle triggers a `feature-bundle-unknown-construct` WARNING, that ID MUST be excluded from resolution and the WARNING included in the command output.

**r42 — `--constructs` canonical arg.** `--constructs` is the canonical argument for specifying explicit construct or pattern IDs. `--patterns` remains a fully supported backward-compat alias — all existing invocations continue to work unchanged. "Building Blocks" is the canonical user-facing name for the set of derivable constructs (README, section headers). The count is defined by the ConstructKindRegistry (§62n) and ExtendedConstructCatalogs (§62m) at the current spec version.

**r41 — Construct kinds.** `--kind` selects which construct catalog(s) to search and derive from. Default is `pattern` (existing behavior, backward compatible). `all` searches all constructs across all five kinds (count defined by §62n ConstructKindRegistry + §62m catalogs at the current spec version). When a non-pattern kind is used, `urace derive` produces a `DerivedConstructSet` (id prefix `cset-`) instead of a `DerivedSystemManifest`. `--kind` can be comma-separated for multi-kind derivation (e.g. `--kind mechanism,schema`). All existing `--kind pattern` behavior is unchanged.

**r40 — Intent-first interface.** `<intent>` is the primary positional argument. When provided, `urace derive` runs the IntentSuggestionEngine to rank patterns by keyword and affinity overlap, then builds a manifest from the top suggestions. `--constructs` is a complementary and optional argument (`--patterns` is a backward-compat alias): when combined with `<intent>`, explicit pattern IDs are merged with intent-suggested IDs (explicit takes precedence; intent adds non-overlapping suggestions). When `<intent>` is omitted and `--constructs` is not set, the catalog browse is shown.

**`--suggest`**: dry-run intent matching — prints ranked pattern suggestions without building a manifest. Requires `<intent>`.

**`--from-goals`**: reads Goals from current state and derives a ranked pattern suggestion list using GoalDerivedSuggestion across all goal titles/descriptions. Prints suggestions and a ready-to-copy `--constructs` argument. Does not build a manifest.

**`--from-constraints`**: reads HardConstraints from current state and derives construct suggestions (kinds: contract, protocol, mechanism) by running IntentSuggestionEngine over each constraint's name, description, scope, and enforcement text. Aggregates scores across all constraints. Prints ranked suggestions and a ready-to-copy `--constructs` argument. Does not build a manifest.

**`--from-inspection`**: runs the InspectionSurface on current state, collects blocking and warning gaps, and derives construct suggestions that address those gaps by running IntentSuggestionEngine over each gap's kind and detail text. Aggregates scores across all gaps. If no gaps exist, reports system is healthy. Does not build a manifest.

**IntentSuggestionEngine (pattern mode):** scores each entry in the PatternCatalog by (a) keyword overlap between intent tokens and the entry's name/summary/provides, plus (b) domain-affinity bonus for recognized stems (event, compaction, retry, circuit, schedule, etc.). Returns top-N results sorted descending by score, each containing `{pattern_id, name, tier, score, summary}`. Any conforming implementation MAY use any scoring strategy that preserves this rank-by-relevance contract.

**GoalDerivedSuggestion:** aggregates IntentSuggestionEngine results across all goal title/description texts, sums scores per pattern, deduplicates, and returns top-N ranked entries. Used by `--from-goals`.

**ConstraintDerivedSuggestion:** aggregates IntentSuggestionEngine results across all HardConstraint name/description/scope/enforcement texts, sums scores per construct, deduplicates, and returns top-N ranked entries filtered to contract/protocol/mechanism kinds. Used by `--from-constraints`.

**GapDerivedSuggestion:** aggregates IntentSuggestionEngine results across all InspectionSurface blocking and warning gap kind/detail texts, sums scores per construct across all kinds, deduplicates, and returns top-N ranked entries. Used by `--from-inspection`.

**`--refresh`**: re-derives all saved DerivedManifestRefs (or only the one matching `--manifest-id`) using their stored `adopted_pattern_ids` and `intent`. Generates a new DerivedSystemManifest per ref, updates the stored DerivedManifestRef in state, creates a DerivationRecord(kind=REFRESH). If `--show-delta` is also set, the output includes: new patterns available since last derive, capability gaps that appeared or closed, changed dependency resolution. `--refresh` MUST NOT require `--constructs`; it reads from state.

**`--apply-capabilities`**: requires `--derive-capabilities` or `--constructs` to be set. Takes all capability drafts produced by `--derive-capabilities` and writes each as a `CapabilityStatement` entry in `Config.capability_envelope.capabilities` (appending if not already present, matching by name). Produces a DerivationRecord(kind=CAPABILITY_APPLY, capabilities_applied=N). MUST NOT overwrite an existing CapabilityStatement; only adds absent ones.

**`--derive-milestone`**: reads `state.capability_states` (or Config.capability_envelope) and produces a draft `ProductMilestone` whose `capability_gates` list targets all capabilities currently ABSENT or PARTIAL. The draft is printed (or written to `--out`) but NOT autonomously written to state; operator review is required. Produces a DerivationRecord(kind=MILESTONE_DRAFT).

**`--show-delta`**: used alongside `--refresh`. For each refreshed manifest, outputs the diff: added patterns, removed patterns (if dep graph changed), new capability gaps, closed capability gaps.

**DerivationRecord audit trail.** Every `urace derive` invocation that produces a manifest, applies capabilities, refreshes, or drafts a milestone MUST append a `DerivationRecord` to `state.derivation_records`.

**Without `<intent>` and without `--constructs`**: lists all available patterns with their tier, requires, and provides fields. No state or config access required.

**With `<intent>` (no `--constructs`)**: auto-suggests patterns via the IntentSuggestionEngine, resolves dependencies, builds and outputs a `DerivedSystemManifest`. Prints which patterns were suggested before the manifest.

**With `--constructs` only**: resolves dependencies, builds a `DerivedSystemManifest`, and outputs it. If `--out` is provided, the manifest is written atomically to that path. If `--json`, the manifest is printed as a JSON document. Otherwise, a human-readable pattern guide is printed.

**`--exclude` requires `--exclude-reason`**. An `--exclude` without `--exclude-reason` is an error. This enforces the acknowledged exclusion contract.

**No state lock, no executor call, no lifecycle state change.** `derive` is a pure computation on the Pattern Catalog. It MAY run while URACE is actively running in another process; it does not mutate lifecycle state.

**Skip-by-default contract.** Providing `--constructs` always proceeds directly to manifest generation — no interactive menu, no confirmation step, no additional prompts. The list view is the only opt-in menu surface and fires ONLY when `--constructs` is omitted entirely. An implementation MUST NOT require operator confirmation between `--constructs` input and manifest output.

**Exit codes.** `0` on success. `1` if any `--constructs` or `--exclude` value is not a known pattern ID.

## DerivedSystemManifest as Lifecycle Artifact

A `DerivedSystemManifest` MUST conform to the `DerivedSystemManifest` citizen schema. It is a lifecycle artifact: it carries a stable `manifest_id`, was generated at a declared timestamp, references a specific URACE spec version, and is traceable. Implementations that store or transmit a manifest SHOULD treat it as a citizen record and include it in their evidence log.

**Manifest and construct set persistence.** `urace derive --save` stores a manifest reference in `state.derived_manifest_refs` (pattern kind) or a ConstructSetRef in `state.construct_set_refs` (non-pattern kinds); each saved reference includes a `pattern_digests` / `construct_digests` fingerprint map for update detection — a list of `DerivedManifestRef` records: `{manifest_id, spec_version, generated_at, adopted_pattern_ids, intent}`. This enables the update system to detect stale manifests. Manifests written only to `--out` are not tracked in state.

A derived system's compliance obligation is exactly: **every adopted pattern's normative requirements apply; no unadopted pattern's normative requirements apply.** This is the complete and closed contract.

## `urace update --opt-in-constructs` Contract

The `--opt-in-constructs <comma-list>` flag (also accepted as `--opt-in-patterns` for backward compatibility) is available on all `urace update` subcommands and on the orchestrated `urace update` (no action). Its default is absent — meaning the update applies to all constructs and patterns. Accepted values: AP IDs (e.g. AP8,AP14), construct IDs (e.g. QSM,GoalRecord), and bundle names prefixed with `@` (e.g. `@community-inbox`) may be mixed freely. A `@bundle-name` value is resolved to its full `construct_ids` list before processing; unknown bundle names produce an error.

**When `--opt-in-constructs` is set:**
- `explain`: the diff report is annotated with `opted_in_patterns_affected: [list]` identifying which opted-in APs changed between accepted and candidate; sections outside the opt-in list are still shown but marked `[not in opt-in scope]`
- `apply`: the migration payload is annotated with `opted_in_patterns: [list]` so the executor applies only those AP sections; sections outside the opt-in list MUST be preserved verbatim from the accepted implementation
- Orchestrated `urace update` (no action): passes `--opt-in-constructs` through to both explain and apply phases

**`--opt-in-constructs` and the derive skip-by-default contract apply the same principle:** both operations default to the full scope and require the operator to explicitly narrow the scope. Neither operation shows an interactive selection menu unless `--patterns` / `--opt-in-patterns` is omitted AND the explicit list-mode form is invoked.

**Pattern → Capability Derivation Contract.** When one or more patterns are adopted via `--opt-in-patterns` or `urace derive`, URACE MUST evaluate whether each adopted pattern's `provides` clause introduces capabilities not yet declared in `Config.capability_envelope.capabilities`. For each undeclared `provides` clause item, URACE MUST emit IntegrityGap(kind="pattern-capability-gap", severity=WARNING, detail="adopted pattern {AP_id} provides '{capability_name}' but no CapabilityStatement covers it"). This is the primary mechanism for keeping capability declarations aligned with adopted architecture. **`--derive-capabilities` flag.** When `urace derive --derive-capabilities` is run, URACE MUST auto-generate draft CapabilityStatement records (status=ABSENT, value_weight=0.1 default) for each `provides` clause item of all adopted patterns not already covered by a declared CapabilityStatement. These drafts are written to a `capability_drafts` output field and MUST NOT be autonomously merged into Config without operator review and an authorized input. **Opt-in-constructs feedback.** After every `--opt-in-constructs` apply, the output MUST include: adopted patterns, their provides clauses, and any pattern-capability-gap warnings.

## Stale DerivedManifestRef Detection

When `urace update download` or `urace update apply` runs and `state.derived_manifest_refs` is non-empty, the implementation MUST compare each ref's `spec_version` to the candidate spec version. Any ref whose `spec_version` is behind the candidate MUST be surfaced as a `derived-manifest-stale` warning in the command output and as an Evidence record of kind `derived-manifest-stale` appended to `state.evidence`. The warning MUST include the `manifest_id`, the stale `spec_version`, and the candidate version. This is a warning, not a blocker: the update proceeds normally.

**Stale detection formula:**
```
stale(ref, candidate_version) ↔ ref.spec_version ≠ candidate_version
```

The operator resolves staleness by re-running `urace derive --constructs ... --save` after the update completes.

**Downstream blocking semantics.** A stale manifest MUST NOT block the execution of an existing derived construct adoption, but MUST block the adoption of any new construct additions from the current spec version until the manifest is refreshed. The runtime MUST surface the `stale-manifest-detection` WARNING on every `urace derive` invocation until the manifest is refreshed.

**Refresh trigger.** A DerivationManifest MUST be refreshed automatically when: (a) `urace /update` is run; (b) the spec version string changes. Manual refresh MAY be triggered via `urace derive --refresh`. A refresh MUST re-evaluate all existing manifest entries against the current ConstructKindRegistry and update `manifest_version` to the current spec version string.

**Override audit trail.** If an operator proceeds with a new construct adoption despite a stale-manifest WARNING (via explicit `--force` flag), the runtime MUST record an Evidence entry of kind `stale-manifest-override` with `operator: true`, `overridden_at`, and the stale manifest version. This Evidence MUST be surfaced in `/rules` output until the manifest is refreshed.

## Subsequent-Gap Closure

The following scenarios that could produce gaps are pre-closed by this framework:

| Scenario | Closure |
|----------|---------|
| User picks pattern X that silently needs pattern Y | Transitive resolution adds Y automatically; `resolution_log` explains it |
| User wants to exclude Y (has own implementation) | `--exclude Y --exclude-reason "..."` produces acknowledged `PatternExclusionRecord`; no silent gap |
| New AP added in future spec revision | Pattern Catalog entry added; existing manifests are unaffected (pinned to their `spec_version`); derive re-run picks up new AP |
| Pattern dependencies change in future revision | Old manifests reference old `spec_version`; `urace derive` re-run produces updated manifest against new catalog |
| User wants to use AP14 (Durable Inbox) standalone | AP14 requires only AP5 (Idempotency Contract); resolver adds AP5; user can also `--exclude AP5` with reason |
| User adopts AP16 (State Document) without understanding its deps | Resolver auto-adds AP3, AP4, AP6; manifest shows them as TRANSITIVE; no hidden requirement |
| Derived system mistakenly claims zero deps for an INTEGRATED pattern | `validate_derived_system_manifest` validates every PatternAdoptionRecord tier field; mismatches raise ValueError |
| URACE update bumps spec version; user's DerivedSystemManifest now points at old version | Stale-manifest detection fires on `update download/apply`; warns with manifest_id + both versions; user re-runs `urace derive --save` |
| User wants update to only touch specific patterns they care about | `urace update --opt-in-patterns AP8,AP14` annotates migration payload; sections outside opt-in list preserved verbatim |
| `urace derive --constructs` shows a menu when user wants direct output | Skip-by-default contract: `--constructs` always bypasses list view; list fires only on bare `urace derive` |

---

# 62k. Standard Command Options

Options defined here apply across all commands that accept them. Per-command specs need not redefine semantics — they MUST conform to this contract.

## --json

Emit output as a machine-readable JSON document (or JSON Lines for streaming commands such as `auto`). Human-readable output is suppressed. Exit codes are unaffected.

Applies to: `check`, `vitals`, `change`, `configuration`, `self-evolution`, `commands`, `inbox`, `derive`, `context`, `intent`, `constraint`, `rules`, `source`, `metric`, `vital`, `goal`, `policy`, `budget`, `evaluation`, `report`, `update`, `plan`, `pause`, `resume`, `compact`, `decompact`, `amend`, `why`, `quality`, `crc`, `auto`

## --scope

Limits the operation to a named authority scope. Valid values: `product` | `runtime` | `all`. Default: `product`.

Applies to: `intent`, `constraint`, `rules`

## --priority

Integer priority weight. Higher values indicate higher scheduling priority.

Applies to: `add-goal` (default: 70), `executor` (default: 100), `goal`

## --kind

String discriminator for filtering or classifying records. Semantics are command-local.

Applies to: `rules` (filter by rule kind), `amend` (amendment kind)

## --id

Stable identifier reference. Semantics are command-local.

Applies to: `intent` (rule ID for supersede/deactivate), `constraint` (rule ID for deactivate), `executor` (executor identity, default: `codex-primary`)

## --source

String identifying the origin of input. Semantics are command-local.

Applies to: `add-context` (default: `repository owner`), `add-metric` (REQUIRED — metric source name)

## --dry-run

Report eligible records or planned mutations without committing any state change.

Applies to: `compact`, `update` (shows what changes would be applied without committing), `derive` (resolves and validates manifest without writing), `auto` (runs one cycle assessment without executing or persisting state), `goal` (validates against Authority without creating Objective), `metric` (validates source path without registering), `constraint` (validates syntax and shows affected Objectives without adding)

## --since

Filter output to records created or updated at or after this ISO-8601 timestamp.

Applies to: `vitals`, `rules`, `change`, `evidence list`, `decision list`, `blocker list`

## --until

Filter output to records created or updated at or before this ISO-8601 timestamp.

Applies to: `vitals`, `rules`, `change`, `evidence list`, `decision list`

## --limit

Integer. Limit output to the N most-recent records. Default varies by command (see Defaults Table below).

Applies to: `vitals`, `rules`, `change`, `why`, `evidence list`, `decision list`, `blocker list`, `goal list`

## --offset

Integer. Skip the first N records before applying --limit. Enables pagination. Default: 0.

Applies to: same as `--limit`

## --fail-on

Emit a non-zero exit code if any IntegrityGap of this severity or higher is present in the output. Valid values: `BLOCKING` | `WARNING` | `INFO`.

Applies to: `check`, `vitals`

Example: `urace check --fail-on BLOCKING` exits 1 if any BLOCKING gap is active; exits 0 otherwise. Enables CI/CD pipeline integration without parsing JSON output.

## --verbose

Emit detailed deterministic diagnostics without an additional Executor call.

Applies to: `auto`

## --quiet

Suppress human-readable per-cycle feedback. When combined with `--json`, JSON Lines output on stdout is retained.

Applies to: `auto`

## --save

Store the generated manifest reference in `state.derived_manifest_refs` for stale-detection by `urace update`. A manifest written only to `--out` is not tracked in state and will not trigger stale warnings.

Applies to: `derive`

**`derive` command and AP24.** The `derive` command is the runtime instantiation of AP24 — Derivation Framework (§62i). It resolves pattern dependencies per the AP24 dependency resolution contract, builds a `DerivedSystemManifest` citizen, and bounds the derived system's obligations to exactly the patterns it adopted. Full command contract in §62j.

## urace /quality

Inspect the quality streak state and quality delta trajectory for one or all scopes. Self-determinable; zero executor credits.

```
urace /quality [--scope <scope>] [--json]
```

Output includes: `current_streak`, `best_streak`, the most recent N QualityDelta records (default: 10), Staleness Detection warnings (§62c), and any pending autonomy expansion proposals. Streak state is read from `State.quality_state` (QualityStateEntry, §62b), not from ExecutorState. Implements the Quality Streak Mechanism (§62c). Uses: QualityDelta (§62b), QualityStateEntry (§62b), Quality Streak Mechanism (§62c).

## urace /compliance

Inspect the current compliance posture and compliance trajectory. Self-determinable; zero executor credits.

```
urace /compliance [--domain <domain>] [--history <n>] [--json]
```

Output includes: per-domain status (COMPLIANT | NON_COMPLIANT | UNKNOWN), consecutive_clean count, last_checked_at, and the most recent N ComplianceRecords (default: 10). --domain filters to a single domain. --history N overrides the record count. Reads ComplianceState (§62b) and compliance_records from State. Implements the compliance inspection surface defined by the Compliance Canonization (§62b ComplianceRecord + ComplianceState). Uses: ComplianceRecord (§62b), ComplianceState (§62b).

## urace milestone

Shows the current active ProductMilestone status, gate progress, and ProductVersion history.

Output includes:
- active milestone id, name, version target
- capability gates: N/M satisfied (list of satisfied and unsatisfied capability ids)
- quality gates: per-scope streak vs min_streak
- complexity and density gate status (if declared)
- milestone_status: PENDING | ACHIEVED
- version_history: list of ProductVersion records (most recent first)
- pattern_capability_gaps: undeclared capabilities from adopted AP patterns

`--json` emits machine-readable payload. Uses: ProductMilestone (§62b), ProductVersion (§62b), SweetSpotAssessment (§62b), Config.capability_envelope.

## Output path: --out vs --output

Two commands accept an output file path using inconsistent flag names:

- `derive` uses `--out`
- `report` uses `--output`

These MUST be treated as command-local until unified. A future revision SHOULD standardize on `--out`.

## Inspect and List Subcommands

The following list and inspect subcommands expose durable state for direct operator inspection. All are SD=True (no Executor invocation required) and support `--json` for machine-readable output.

**`urace goal list [--status <s>] [--priority <min>..<max>] [--limit N] [--json]`**
List active Objectives. `--status` accepts: `active`, `pending`, `blocked`, `resolved`, `cancelled`. Default: `active`. Returns: id, title, status, priority, source_input, created_at.

**`urace evidence list [--kind <kind>] [--since <ISO>] [--until <ISO>] [--limit N] [--json]`**
Query the append-only Evidence log. `--kind` filters by Evidence kind string. Default --limit: 20. Returns: id, kind, at, source_input, summary.

**`urace blocker list [--resolved] [--scope <scope>] [--json]`**
List active Blockers. `--resolved` includes already-resolved blockers. Returns: id, scope, reason, count, classification, last_at, escalation_due. Default: active blockers only.

**`urace blocker resolve <blocker-id> [--note <text>] [--json]`**
Operator-clear a specific Blocker. Emits Evidence of kind `blocker-operator-resolved` with `cleared_by: operator`, `cleared_at`, and optional note. Only valid for blockers without `classification: OPERATOR_GATE` (those require OperatorGateProtocol clearance via `urace govern`).

**`urace decision list [--stale] [--scope <scope>] [--limit N] [--json]`**
List DecisionRecords. `--stale` filters to decisions flagged as `provenance_revised = true`. Default --limit: 20. Returns: id, outcome, at, scope, stale, revalidation_scope.

**`urace decision inspect <decision-id> [--json]`**
Show full DecisionRecord including evidence_ids, authority_basis, JustificationContext, and linked revalidation history.

**`urace integrity-signal list [--type <type>] [--severity BLOCKING|WARNING] [--resolved] [--json]`**
List IntegritySignal records. Supports filtering by signal_type and severity. Default: unresolved signals only.

## Defaults Table

| Command | Option | Default |
|---|---|---|
| `derive` | `--kind` | `AP` (all architectural patterns) |
| `metric add` | `--direction` | `nondecreasing` |
| `goal add` | `--priority` | 70 |
| `executor` | `--id` | `codex-primary` |
| `compact` | `--dry-run` | false |
| `auto` | `--verbose` | false |
| `auto` | `--quiet` | false |
| `/quality` | `--scope` | all |
| `/compliance` | `--domain` | all |
| `goal list` | `--status` | `active` |
| `goal list` | `--limit` | 20 |
| `evidence list` | `--limit` | 20 |
| `decision list` | `--limit` | 20 |
| `blocker list` | `--resolved` | false |
| `check` | `--fail-on` | none (never exits nonzero due to gaps) |

## Output Path Standardization

`derive` uses `--out <path>` and `report` uses `--output <path>`. Both are valid until unified. A future revision SHOULD standardize on `--out <path>` for all file-writing commands.

## urace inbox

Manage the Durable Inbox queue. SD=True for `list`; `apply` and `reject` require Executor.

```
urace inbox list [--kind <kind>] [--status QUEUED|REJECTED|PROCESSED] [--limit N] [--json]
urace inbox status <input-id> [--json]
urace inbox apply <proposal-id> [--json]
urace inbox reject <proposal-id> [--reason <text>] [--json]
```

`inbox list` shows pending and recently processed inputs. `inbox status` returns CONSUMED, REJECTED, PENDING, or NOT_FOUND with artifact chain. `inbox apply` / `inbox reject` are used for HUMAN-mode PatchProposal approval (PPP, §62c). `apply` and `reject` MUST process through the Durable Inbox (AP14) at the next safe boundary; they MUST NOT bypass the inbox.

## urace govern

Operator clearance for OperatorGateProtocol conditions. Authenticated operator input only.

```
urace govern clear <gap-id> [--note <text>] [--json]
urace govern list-gates [--json]
```

`govern clear` clears a named BLOCKING gap that requires operator action (kind matches `operator-gate-open` or `*-unverified*`). Emits durable Evidence record per OGP clause 4. `govern list-gates` lists all open operator gates with their clearance requirements.

## urace autonomous

Run URACE in persistent autonomous mode. Alias for `urace auto` with persistent execution semantics.

```
urace autonomous [--dry-run] [--verbose] [--quiet] [--json]
```

`urace autonomous` is functionally identical to `urace auto`. The name is accepted for disambiguation when both `auto` (one-shot assessment) and `autonomous` (continuous) invocations coexist in scripts. `--dry-run` runs one assessment cycle, prints the next planned action, and exits without executing or persisting state.

## urace onboard

Inspect and confirm the Product Onboard Phase. SD=True for `status`; `confirm` mutates State. Implements OnboardGate (§62c). Uses: OnboardRecord (§62b), §62o Product Onboard Phase.

```
urace onboard status [--json]
urace onboard confirm [--note <text>] [--json]
```

**`onboard status`** — evaluates all OnboardGate steps against current Config and State without mutating state. Idempotent. Output includes: gate-by-gate PASS/FAIL table, active onboard gap kinds, current `lifecycle_state`, and whether an OnboardRecord already exists for `Config.product`. If an OnboardRecord already exists, the command reports the existing record (id, confirmed_at, product_name, config_digest match/diverge) without re-evaluating gates. `--json` emits machine-readable payload with `gates: [{name, status, detail}]`.

**`onboard confirm`** — operator confirmation that all gates have been reviewed and autonomous cycles are authorized to begin. MUST be issued after `onboard status` reports all BLOCKING gates as PASS. Execution: (1) re-evaluates OnboardGate; (2) if any BLOCKING gate fails, exits 1 with gate errors and takes no action; (3) if all BLOCKING gates pass, creates an OnboardRecord (id prefix "onb-"), writes ONBOARD_COMPLETE Checkpoint, clears all active `onboard-*` gaps, sets `lifecycle_state = DORMANT`. Optional `--note` text is stored in `OnboardRecord.notes`. Supersedes prior OnboardRecord for the same product (retains prior with `superseded_at`).

**Exit codes.** `onboard status` exits 0 if an OnboardRecord exists and config matches, exits 2 if BLOCKING gates are unresolved, exits 0 with divergence warning if `onboard-record-config-diverged` is active. `onboard confirm` exits 0 on success, exits 1 if BLOCKING gates fail, exits 1 if state write fails.

**Re-onboard.** If `Config.product` has changed since the last OnboardRecord, `onboard status` reports the mismatch and advises re-confirmation. `onboard confirm` treats this as a new product and creates a fresh OnboardRecord. The previous product's record is retained with `superseded_at` set to allow audit recovery (§62o).

## urace product

Manage the Product Registry. SD=True for `list` and `status`. `switch` and `register` mutate Config. Implements ProductSwitchProtocol (§62l). Uses: ProductEntry (§62b), SwitchRecord (§62b), §62p Product Registry.

```
urace product list [--json]
urace product status [--json]
urace product switch <name> [--reason <text>] [--json]
urace product register <name> --state-path <path> [--product-files <f>...] [--intent-purpose <text>] [--json]
```

**`product list`** — shows all ProductEntry records in Config.product_registry. Each entry shows: name, status, registered_at, last_active_at (if any), and whether it has an active OnboardRecord. Marks the currently active product with `*`. `--json` emits array of entries.

**`product status`** — shows the currently active product name, its ProductEntry (if registered), the active OnboardRecord summary (id, confirmed_at, config_digest match), and the current lifecycle_state. Zero-arg shorthand for the most common diagnostic.

**`product switch <name>`** — applies ProductSwitchProtocol: validates name in registry, appends SwitchRecord, updates Config.active_product, persists Config. Returns 1 if target not in registry or not ACTIVE. After switch, `lifecycle_state` will be set to ONBOARDING on next cycle entry; operator must run `urace onboard confirm` for the new product.

**`product register <name>`** — adds a new ProductEntry to Config.product_registry. `--state-path` is required (where this product's state file will live). `--product-files` accepts one or more file paths. `--intent-purpose` sets the product's intent text. Fails if name already exists in registry. Persists Config.

**Exit codes.** All subcommands exit 0 on success, 1 on validation failure, 1 on Config/state write failure.

---

# 62l. Shared Reuse Contracts

This section defines eighteen named protocols, invariants, canonical clusters, and catalogs that are referenced throughout the spec. Each construct is defined once here. All sections that use these constructs MUST cite them by name rather than restating their content inline.

**Enforcement contract (§62l).** All eighteen constructs defined in this section MUST be enforced at runtime by any conforming implementation. The nine explicitly mandated enforcement clauses are: (1) every IntegrityGap emission MUST validate the kind against the IntegrityGapCatalog before appending; (2) the `urace check` output MUST conform to the InspectionSurface schema (11 required categories); (3) all citizens that declare GoverningRecord conformance MUST have `authority_basis`, `scope`, and `established_at` enforced; (4) all citizens that declare GoverningRecord conformance that also use TemporalFields MUST validate timestamp fields as non-empty ISO-8601 strings; (5) all handlers that process premise changes MUST use the RevalidationScope trigger mapping to determine revalidation scope; (6) AuthorityClosureInvariant MUST be checked before treating any action as authority-driven; (7) PatternMechanismMapping MUST be the canonical AP-to-section lookup for derivation operations; (8) JustificationContract MUST be evaluated before any consequential lifecycle action is committed; (9) BoundaryContract MUST govern all lifecycle boundary creation, closure, and recovery. The remaining nine constructs — EUP, OGP, CRRP, WRV, CRC_C, CEP, QE, JOIN, and PSP — are procedurally self-enforcing: their behavioral contracts are stated within their respective definitions below and are binding by virtue of this section declaring them as named constructs that all sections MUST cite rather than restate inline. **Construct metadata kind note.** All §62l constructs carry `kind: Protocol` in their construct metadata line. This is the generic §62l-section metadata value. The authoritative semantic classification of each construct (Canonical Cluster, Catalog, Contract, Invariant, Mapping, or Protocol) is given by the catalog column in §62m and by the construct's own definition header.

---

## GoverningRecord Canonical Cluster

**Construct metadata.** `kind: Protocol` · `tier: FOUNDATIONAL` · `standalone: true` · `depends: []`

A **GoverningRecord** is any citizen that establishes an authoritative boundary rather than recording an event. GoverningRecords share four required fields that form the governance provenance contract.

```
GoverningRecord {
  id               REQUIRED  Identifier; prefix depends on citizen type
  authority_basis  REQUIRED  string; which Authority record establishes this record
  scope            REQUIRED  string; scope path this record applies to; "*" = all scopes
  established_at   REQUIRED  string; ISO-8601 timestamp; immutable after creation
}
```

**Immutability contract.** `established_at` MUST NOT change after the record is created. **Authority contract.** `authority_basis` MUST reference a resolvable Authority record; a GoverningRecord with an unresolvable `authority_basis` is a provenance violation and MUST be surfaced as an IntegrityGap(kind="governing-record-unresolvable-authority", severity=WARNING). **Scope contract.** A GoverningRecord with `scope="*"` applies to all lifecycle scopes. A record with a specific scope applies only to operations whose scope matches or is a child of the declared scope.

**Citizens using GoverningRecord:** PolicyRecord (§72), HardConstraint (§72), DestinationAnchor (§62b), Authority records (§6), CapabilityStatement (§59b).
**Referenced from:** §6 Authority, §62b DestinationAnchor, §72 Policy Enforcement, §62c Authority Resolution Mechanism.

**Schemas that implement GoverningRecord:** WakeRegistration, ExecutorProvider, RetentionPolicy. These schemas MUST declare `Implements: GoverningRecord` and MUST include all GoverningRecord fields (`id`, `authority_basis`, `scope`, `established_at`).

---

## EffectUncertaintyProtocol

**Construct metadata.** `kind: Protocol` · `tier: COMPOSITIONAL` · `standalone: false` · `depends: [AP3, AP4]`

When an Operation's external effect status cannot be established with confidence, URACE MUST apply the EffectUncertaintyProtocol. This protocol is defined once here; all sections cite it by name.

**Three-step protocol:**

1. **Classify as INDETERMINATE.** The effect is immediately classified as `INDETERMINATE` in durable state. URACE MUST NOT assume success, failure, or retry safety.
2. **Reconcile before retry.** Before any retry or re-dispatch, URACE MUST apply the strongest available reconciliation method: target-system query, transaction reference ID, durable artifact hash, deterministic probe. Retry MUST NOT proceed until reconciliation establishes a disposition.
3. **Preserve until disposition.** If reconciliation cannot establish disposition, the `INDETERMINATE` record MUST remain in durable state indefinitely. It MUST NOT be silently aged out, assumed resolved, or used as implicit authorization for a subsequent attempt. It MUST be surfaced in the LifecycleInspectionSurface (§62l) as a named blocker. Dependent Operations MUST be preserved as explicitly blocked on the unresolved record.

**Scoped blocking contract.** An indefinitely unresolvable INDETERMINATE effect MUST block only its minimum dependent workstream set consistent with §65 Partial Blocking. Executor-independent work and unrelated workstreams MUST NOT be suspended.

**Citizens using EffectUncertaintyProtocol:** (none — protocol governs behavior, not a schema field).
**Referenced from:** §43 (executor permanent unavailability), §52 (write-before-effect boundary), §53 (effect reconciliation), §63 (concurrent state conflict), §73 (recovery interruption), behavioral tests BJ/BK/BL/BM/BN.

---

## OperatorGateProtocol

**Construct metadata.** `kind: Protocol` · `tier: FOUNDATIONAL` · `standalone: true` · `depends: []`

An **operator gate** is a lifecycle condition that MUST NOT be cleared by autonomous action. The OperatorGateProtocol is defined once here; all sections that require operator action cite it by name.

**Four-clause protocol:**

1. **Surface as named blocker.** The condition MUST be surfaced in the LifecycleInspectionSurface as a named blocking limitation identifying: what the gate is, why it cannot be self-cleared, and what operator action is required.
2. **Hold state without autonomous progress.** The dependent workstream MUST be preserved in a named blocked state. URACE MUST NOT proceed with the gated action, attempt a workaround, or silently time out the gate.
3. **Require authenticated clearance.** The gate is cleared only by an authenticated lifecycle command (e.g., `urace govern`, `urace add`, attributed Input). The clearance MUST be processed through the inbox (AP14) at the next safe lifecycle boundary.
4. **Record clearance as durable event.** The clearance MUST be recorded as a durable Evidence or DecisionRecord attributing the operator, the cleared condition, and the timestamp. The record MUST remain in durable state for audit purposes.

**Citizens using OperatorGateProtocol:** (none — protocol governs autonomous prohibition, not a schema field).
**Referenced from:** §43 (systematic executor failure cooldown reset), §63 (stale OwnershipMarker), §72 (HARD constraint violation attempt), §73 (recovery-of-recovery chain), §74 (ambiguous self-evolution policy), §62f (compaction authorization).

---

## AuthorityClosureInvariant

**Construct metadata.** `kind: Protocol` · `tier: FOUNDATIONAL` · `standalone: true` · `depends: []`

**The Authority boundary is closed under all non-Authority inputs.** No input other than an explicit, attributable Authority record may expand the scope of legitimate autonomous action. This invariant is stated once here; all sections that enforce it cite it by name.

**Closed inputs — none of the following can create or expand Authority:**
- Evidence (however credible or strong)
- Priority (however urgent)
- Capability (however technically feasible)
- Market signals or Product Value (however compelling)
- Trigger events (however frequent or impactful)
- Schedule (however overdue)
- Executor recommendation (however confident)
- Higher-order Intent inference (however logical)
- User absence or silence
- Autonomous observation of an easier or more profitable destination

**Citizens using AuthorityClosureInvariant:** (none — invariant governs authority checks, not a schema field).
**Referenced from:** §10, §26, §29, §36, §39, §42, §56, §59, behavioral tests T/U/AO/AY/BC and all Authority anti-leak tests.

---

## RevalidationScope

**Construct metadata.** `kind: Protocol` · `tier: COMPOSITIONAL` · `standalone: false` · `depends: [AP6]`

When a material premise change invalidates an accepted decision, the revalidation scope is determined by the nature of the change. "Proportionate revalidation" is operationalized as a lookup from change class to RevalidationScope value.

**RevalidationScope enum:**
```
DECISION_ONLY    — re-examine only the affected DecisionRecord and its validity conditions
DEPENDENT_PLANS  — re-examine the DecisionRecord and all Plans and Operations that cite it
FULL_LIFECYCLE   — re-examine Authority, Intent, all active Plans and the current Objective
```

**Trigger-to-scope mapping:**

| Premise change class | RevalidationScope |
|---|---|
| Single Evidence record retracted or revised | DECISION_ONLY |
| Authority record suspended or revoked | DEPENDENT_PLANS |
| Governing Intent versioned or replaced | FULL_LIFECYCLE |
| Hard constraint added or scope changed | DEPENDENT_PLANS |
| Policy record status changed | DEPENDENT_PLANS |
| Multiple simultaneous premise changes | FULL_LIFECYCLE |
| Executor identity continuity broken | DECISION_ONLY (per-operation) |

**Minimum scope rule.** URACE MUST apply the minimum RevalidationScope sufficient to ensure no stale premise drives a new committed effect. Applying a wider scope than necessary is permitted but wasteful.

**Citizens using RevalidationScope:** DecisionRecord (§62b, revalidation_scope field).
**Referenced from:** §45, §46, §48, §72, behavioral tests BE/BF and any section using "proportionate revalidation."

---

## CognitiveResetRecoveryProtocol

**Construct metadata.** `kind: Protocol` · `tier: INTEGRATED` · `standalone: false` · `depends: [AP27, AP36]`

A **cognitive reset** occurs when an Executor loses its working context but durable state is intact. The CognitiveResetRecoveryProtocol defines the mandatory recovery sequence. Cognitive reset is distinct from data loss; an Executor incapable of CRC injection is not lifecycle-replaceable.

**Protocol steps (MUST be followed in order):**
1. **Regenerate CRC.** Produce a fresh CognitiveResumeContext (§62e) from durable state.
2. **Verify state_digest.** Compute the current state digest and verify it matches the CRC's recorded digest. A mismatch is a provenance violation (AP36).
3. **Inject CRC.** Provide the CRC to the resuming Executor as the sole context source.
4. **Resume from cycle_phase.** Resume at the cycle phase recorded in the CRC; do not restart the full assessment.
5. **Treat pending_validations and blocking_gaps as authoritative.** These are durable obligations; do not re-derive them.
6. **Apply Transaction recovery if pending.** If a pending_transaction exists, apply AP27 phase-specific disposition before any other action.

**Recovery-of-recovery guard.** If recovery is itself interrupted, the subsequent restart MUST treat partial recovery as a new INDETERMINATE boundary, re-establish from the last durable checkpoint, preserve the interrupted recovery's durable record, and surface repair-exhausted after a bounded depth rather than recursing indefinitely.

**Step idempotency.** Each step of the CRRP MUST be independently idempotent: re-executing any step after a partial failure MUST produce the same result as executing it for the first time. Steps MUST use the `source_event_id` of the triggering cognitive-reset event as an idempotency key. A step that detects it has already been completed (by checking for its output record in the State Document) MUST skip and proceed to the next step.

**Sequential execution.** CRRP steps MUST be executed strictly sequentially. Step N+1 MUST NOT begin until step N has written its output record to the State Document. Parallel execution of CRRP steps is PROHIBITED.

**Transient failure handling.** If a step fails with a transient error (network timeout, resource contention), the step MUST be retried up to 3 times with exponential backoff (base: 5 seconds). If the step still fails after 3 retries, a BLOCKING gap of kind `crrp-step-failure` MUST be surfaced with `step_number` and `failure_reason`. The protocol MUST halt at the failed step; earlier completed steps MUST NOT be rolled back.

**Retry ceiling.** The full CRRP protocol MUST NOT be re-initiated more than 2 times for the same `source_event_id`. A third initiation attempt for the same event MUST be rejected and a BLOCKING gap of kind `crrp-retry-exceeded` MUST be surfaced.

**Citizens using CognitiveResetRecoveryProtocol:** CognitiveResumeContext (§62e). Referenced from: §73 Cognitive Reset Recovery.

---

## WakeRegistrationVerification

**Construct metadata.** `kind: Protocol` · `tier: COMPOSITIONAL` · `standalone: false` · `depends: [AP29]`

At every restart, all durable WakeRegistration records MUST be verified active in the current environment. This is the mandatory verification step for AP29 — Dormancy/Wakeability Contract.

**Protocol steps:**
1. **Enumerate durable WakeRegistrations.** Read all WakeRegistration records from durable state.
2. **Verify each registration.** Attempt to confirm the registration is active and observable in the current runtime environment (scheduler entry exists, callback is registered, poller is running, file-watcher is active).
3. **Classify result.** Each registration is VERIFIED, UNVERIFIABLE, or STALE.
4. **Emit wake-integrity-gap for unverifiable entries.** Each UNVERIFIABLE or STALE entry MUST produce an IntegrityGap(kind="wake-integrity-gap", severity=WARNING) before any dormancy declaration.
5. **Re-establish if possible.** Attempt to re-establish STALE or UNVERIFIABLE registrations using the same mechanism configuration.
6. **Prohibit dormancy while wake-integrity-gap exists.** The lifecycle MUST NOT declare DORMANT state while any unresolved wake-integrity-gap exists.

**Citizens using WakeRegistrationVerification:** WakeRegistration (§62c). Referenced from: §66, §67, §62c Wake Registration Verification Mechanism.

---

## ComplianceRecordingContract

**Construct metadata.** `kind: Protocol` · `tier: COMPOSITIONAL` · `standalone: false` · `depends: [AP28, AP37]`

After every independent validation gate evaluation (AP28), the lifecycle MUST persist compliance outcomes per domain into the append-only trajectory and update the live accumulator. This is the mandatory persistence obligation for AP37 — Compliance Posture Tracker.

**Protocol steps:**
1. **Identify assessed domains.** Collect all domains evaluated in the gate run: authority, intent, schema, constraint (and governance if evaluated separately).
2. **Classify each domain.** Determine COMPLIANT, NON_COMPLIANT, or UNKNOWN for each assessed domain.
3. **Append ComplianceRecord per domain.** For each assessed domain, append one ComplianceRecord (§62b) with the domain, status, operation_id, and evaluated_at timestamp.
4. **Update ComplianceState per domain.** Update the corresponding ComplianceState entry: increment consecutive_clean on COMPLIANT; reset to 0 and append violation_ref on NON_COMPLIANT; update last_checked_at.
5. **Emit compliance-record-missing gap if absent.** If a domain was assessed but no ComplianceRecord was appended, emit IntegrityGap(kind="compliance-record-missing", severity=WARNING).

**Self-determination.** The `urace /compliance` command is SD=True — it reads only durable state (compliance_records, compliance_state) and requires no Executor invocation.

**Citizens using ComplianceRecordingContract:** ComplianceRecord, ComplianceState (§62b). Referenced from: §60 Compliance Recording Contract, §62c validation gate wiring.

---

## JustificationContract

**Construct metadata.** `kind: Protocol` · `tier: FOUNDATIONAL` · `standalone: false` · `depends: [ACI, AP35]`

The JustificationContract defines the formal predicate that determines whether a proposed lifecycle action is a "justified authorized action." This protocol is defined once here; all sections that use the phrase "justified authorized action" cite this protocol.

**Formal predicate.** An action A is a justified authorized action if and only if ALL FIVE conditions hold:
1. `has_authority(A)` — A falls within the scope of a valid, un-revoked PERMISSION rule in the Rule Ledger (AP35, §62i); AuthorityClosureInvariant (§62l) MUST pass.
2. `aligns_intent(A)` — A advances or protects at least one active governing Intent record.
3. `has_evidence(A)` — At least one piece of Evidence in durable state supports taking A; zero Evidence does not automatically prevent A but MUST be recorded as `has_evidence: false` in the JustificationContext.
4. `not_blocked(A)` — No BLOCKING IntegrityGap with `scope` containing A's scope is currently active.
5. `has_capability(A)` — The required Executor capability is in AUTHENTICATED or AUTHORIZED state.

**JustificationContext contract.** Before committing to any consequential lifecycle action, URACE MUST evaluate all five predicates and record the result as a JustificationContext citizen (§62b). A JustificationContext with `is_justified: false` MUST prevent the action. A JustificationContext with `is_justified: false` due only to `has_evidence: false` MAY be overridden by an explicit operator DecisionRecord authorizing the action without Evidence; the override MUST be logged.

**Citizens using JustificationContract:** JustificationContext (§62b).
**Referenced from:** §11 Autonomous Decision Space, §38 Objective Discovery, §47 Executor Boundary, §66 Autonomous Liveness.

---

## BoundaryContract

**Construct metadata.** `kind: Protocol` · `tier: FOUNDATIONAL` · `standalone: false` · `depends: [AP14, AP27]`

The BoundaryContract defines the closure rules for safe lifecycle boundaries — the points at which inputs are consumed, operations are closed, and state is committed atomically.

**Boundary types and closure rules:**

| Boundary type | Required conditions to close | Post-close state |
|---|---|---|
| POST_ASSESSMENT | JustificationContext evaluated for all candidate actions | ACTIVE or DORMANT |
| POST_VALIDATION | PendingValidation resolved with PASS or FAIL verdict | ASSESSING (pass) or REPAIRING (fail) |
| POST_REPAIR | Repair sequence completed or ceiling reached | ASSESSING |
| CYCLE_COMPLETION | All Tier 0 + Tier 1 inbox inputs consumed; no unresolved effects in boundary scope | varies |
| OPERATOR_REQUESTED | Explicit authenticated operator command processed | PAUSED |

**Incompleteness contract.** A boundary that has been opened (LifecycleBoundary.at set) but not closed (closed_at = null) at process restart MUST be treated as partial-update per AP27. URACE MUST emit IntegrityGap(`kind: "lifecycle-boundary-violation"`, severity=BLOCKING) and apply the Transaction Recovery Protocol before creating new boundaries.

**Atomicity contract.** All State mutations belonging to a single boundary MUST be committed as one atomic write. A boundary MUST NOT be marked closed until all its mutations are durable. If the commit fails partway, the runtime MUST retry the commit or enter REPAIRING with the incomplete boundary as the triggering IntegritySignal.

**Citizens using BoundaryContract:** LifecycleBoundary (§62b).
**Referenced from:** §38 queued inputs, §49 Pre-Commit Revalidation, §62 State and Persistence.

**Supplemental enforcement contract (JustificationContract + BoundaryContract).** (8) JustificationContract MUST be evaluated before any consequential lifecycle action is committed; (9) BoundaryContract MUST govern all lifecycle boundary creation, closure, and recovery.

---

## InspectionSurface Contract

**Construct metadata.** `kind: Protocol` · `tier: FOUNDATIONAL` · `standalone: true` · `depends: []`

The **InspectionSurface** is the structured output produced by `urace check` and any lifecycle inspection command. Its schema is defined once here; all sections that require items to be "surfaced in inspection output" specify only the category and kind, not the output structure.

```
InspectionSurface {
  lifecycle_state          REQUIRED  string; current lifecycle state
  assessed_at              REQUIRED  string; ISO-8601 timestamp of last assessment
  blocking_gaps            REQUIRED  list of IntegrityGap; severity=BLOCKING items
  warning_gaps             REQUIRED  list of IntegrityGap; severity=WARNING items
  indeterminate_effects    REQUIRED  list; open INDETERMINATE unresolved effects
  operator_gates           REQUIRED  list; open OperatorGateProtocol conditions
  stale_items              REQUIRED  list; stale decisions, manifests, hypotheses requiring validation
  capability_readiness     REQUIRED  map; capability_id -> CapabilityStatus
  scheduled_conditions     REQUIRED  list; upcoming scheduled wake conditions
  policy_violations        REQUIRED  list; detected policy violations (HARD blocks + SOFT warnings)
  open_pending_validations REQUIRED  list; PendingValidation records not yet resolved
  summary                  REQUIRED  string; one-sentence human-readable status
}
```

**Completeness contract.** An InspectionSurface that omits a required category is structurally incomplete. The `blocking_gaps` and `operator_gates` categories MUST be exhaustive — every known blocker must appear. **SD=True** — the InspectionSurface is fully computable from durable state without Executor invocation.

**Citizens using InspectionSurface:** (none — output schema of urace check, not a stored citizen).
**Referenced from:** §62c staleness detection, §62c capability envelope gate, all sections requiring "surfaced in inspection output".

---

## ConstructElevationProtocol

**Construct metadata.** `kind: Protocol` · `tier: FOUNDATIONAL` · `standalone: true` · `depends: []`

The ConstructElevationProtocol governs when and how a concept is promoted from ad-hoc prose to a named construct at the correct kind in the 5-kind hierarchy. All promotions in this specification MUST follow this protocol.

**Four-gate elevation test:**

1. **AP elevation gate.** Elevate to AP (§62i) if ALL THREE hold: (a) structurally reusable outside URACE-specific context; (b) normatively referenced from ≥3 independent sections; (c) defines a behavioral contract, not merely an algorithm or data structure. If all three hold, assign the lowest tier consistent with the construct's declared dependencies.

2. **Protocol promotion gate.** Elevate to Protocol (§62l) if ALL THREE hold: (a) already named as a contract or invariant in prose; (b) referenced by name from multiple sections; (c) defines a cross-cutting normative contract, not a schema or algorithm. Assign tier based on dependencies.

3. **AP cross-reference wire gate.** Add "governed by AP_N (§62i)" inline if: (a) a Mechanism or Schema implements a structural concern already covered by an existing AP; (b) full elevation is not warranted. This is a reference addition, not a promotion.

4. **Leave-in-place rule.** Leave in current location if: (a) it is a product-domain algorithm, formula, or operational procedure; (b) it has no reuse outside its own section; (c) it is a self-referential mechanism; or (d) it is an implementation detail with no cross-section normative force.

**Tier assignment rule.** A promoted construct's tier is FOUNDATIONAL if it has no external construct dependencies or all its dependencies are themselves FOUNDATIONAL; COMPOSITIONAL if it depends on FOUNDATIONAL constructs; INTEGRATED if it depends on any COMPOSITIONAL or INTEGRATED construct.

**Mandatory post-elevation actions:**
- Add construct metadata line to the promoted entry.
- Register in PatternMechanismMapping (§62l) if kind=AP.
- Register in ConstructKindRegistry (§62n) for all kinds.
- Add cross-reference wires from all implementing sections.
- Update IntegrityGapCatalog (§62l) if the promotion introduces new gap kinds.

**Elevation eligibility criteria.** An inline concept is eligible for elevation to a named construct only when: (a) it has been referenced by name in at least 3 distinct spec sections; (b) it has a stable, independently useful definition that does not require context from its original section to be understood; (c) it does not duplicate an existing construct in the ConstructKindRegistry (§62n). A concept that does not meet all three criteria MUST NOT be elevated; it SHOULD be documented as a term in the glossary instead.

**Evidence threshold.** Before initiating the CEP 4-gate process, the proposer MUST provide an Evidence record of kind `elevation-proposal` referencing: (a) the 3+ sections where the concept appears; (b) the proposed construct kind and tier; (c) the proposed canonical identifier (e.g., schema prefix, mechanism abbreviation). Elevation MUST NOT proceed without this Evidence record.

**Reversibility.** A promoted construct MAY be deprecated but MUST NOT be removed from the spec within the same major version. Deprecation MUST be recorded in the ConstructKindRegistry with `status: DEPRECATED` and a `deprecated_at` version string. A deprecated construct MUST remain in the §62m catalogs with a `[DEPRECATED]` marker until the next major version boundary.

**Version continuity.** The construct's `introduced_in` field MUST reference the spec version string of the revision in which it was promoted. All `Extends:` declarations referencing the elevated construct MUST be updated in the same revision.

**Citizens using ConstructElevationProtocol:** (none — governs the specification's own structural evolution).
**Referenced from:** §62n Base Rule directive 7, §80 Spec Structural Audit.

---

## Spec Construction Protocol (SCP)

**Construct metadata.** `kind: Protocol` · `tier: FOUNDATIONAL` · `standalone: false` · `depends: [NSS, IGC]`

**Used in:** (universal — all spec revisions)

**Intent.** A pre-extension gate that enforces definition-first ordering, revision completeness declaration, and single-pass atomic extension across all spec revisions. SCP prevents the "reference-before-definition" gap pattern by requiring every concept to be formally defined before it is normatively referenced. SCP is self-applying: the r60 revision that introduces SCP is itself the first revision to comply with it.

**Gate 1 — Definition-first ordering.**
Before any normative statement (containing MUST, SHALL, SHOULD, or MAY) may reference a concept `X`, `X` MUST appear in the spec's formal index at a document position prior to the reference. The formal index comprises: Config schema (§62e), citizen schemas (§62b), ConstructKindRegistry (§62n), IntegrityGapCatalog (§62l), and stem vocabulary (§81). A forward reference — referencing `X` before `X` is defined — is a violation of Gate 1.

**Gate 1 — IGC gap kind exception.** IntegrityGapCatalog (§62l) gap kind names are subject to revision-temporal ordering, not document-positional ordering. Because §62l structurally follows §62c and §62j in the document (a fixed architectural invariant), requiring gap kind names to appear at smaller line numbers than every §62c/§62j MUST reference would make §62c unwritable. Instead: an IGC gap kind name MAY be referenced in a MUST/SHALL statement in any section provided the kind is registered in §62l in the SAME revision that introduces the reference. A gap kind name referenced in a prior revision that is not yet in §62l is a Gate 1 violation. This exception applies to gap kind string references only; all other concept types (Config fields, schema fields, enum values, construct identifiers) remain subject to document-positional ordering.

**Gate 2 — Revision completeness declaration.**
Every revision log entry MUST include a `**New external references:**` field. This field MUST enumerate every Config field, schema field, enum value, IGC gap kind, and construct identifier introduced by the revision. Each entry MUST include the document section where the definition appears. If the revision introduces no new external references, the field MUST read `none`. A revision log entry that omits this field is a Gate 2 violation.

**Gate 3 — Single-pass atomic extension.**
A revision MUST define and reference every concept in a single atomic diff. "Define in a future revision" is permitted only for SHOULD-level or MAY-level statements using a named stub. It is PROHIBITED for MUST-level or SHALL-level statements. A MUST-level normative statement that references an undefined concept is simultaneously a Gate 1 violation and a Gate 3 violation.

**Violation contract.**
- Gate 1 violation: BLOCKING gap of kind `scp-forward-reference` with fields `referencing_section`, `undefined_concept`, `revision`.
- Gate 2 violation: WARNING gap of kind `scp-incomplete-revision-declaration` with field `revision`.
- Gate 3 violation: BLOCKING gap of kind `scp-atomic-extension-violation` with fields `concept`, `revision`, `normative_force` (MUST|SHALL).

**Retroactive applicability.** Revisions prior to r60 predate SCP and are exempt from Gate 1 and Gate 3 enforcement. They are exempt from Gate 2 but SHOULD include a `**New external references:** (predates SCP — not declared)` annotation when the revision log is audited. SCP is fully binding from r60 onward.

**Citizens using SCP:** (none — governs the specification's own extension integrity).
**Referenced from:** §62n ConstructKindRegistry, §82 Revision Log.

---

## Construct Dependency Acyclicity Invariant (DAI)

**Construct metadata.** `kind: Protocol` · `tier: FOUNDATIONAL` · `standalone: true` · `depends: []`

**Used in:** (universal — all construct dependency declarations)

**Intent.** The construct dependency graph formed by all `requires:`, `depends:`, and `governed-by:` declarations MUST be a directed acyclic graph (DAG). Circular construct dependencies corrupt the derivation framework, the AP dependency resolution contract (AP24), and the SCP Gate 1 definition-first ordering guarantee.

**Rule 1 — Acyclicity.** The transitive closure of all construct dependency edges (`requires:` on APs, `depends:` on Protocols, `governed-by:` on Mechanisms) MUST form a DAG. Any proposed addition of a dependency edge that would introduce a cycle MUST be rejected; `construct-dependency-cycle` BLOCKING gap MUST be surfaced with fields `construct_id` (the construct whose declaration introduces the cycle), `cycle_path` (the sequence of construct IDs forming the cycle).

**Rule 2 — Self-reference prohibition.** A construct's `requires:`, `depends:`, or `governed-by:` field MUST NOT contain the construct's own ID. A self-referencing declaration MUST surface `construct-self-reference` BLOCKING gap with field `construct_id`.

**Rule 3 — FeatureBundle acyclicity.** A `FeatureBundle.construct_ids` list MUST resolve to a DAG when each listed construct's own transitive dependency edges are included. A FeatureBundle whose construct_ids introduce a cycle among themselves MUST surface `construct-dependency-cycle` with `construct_id = <bundle_name>`.

**Validation timing.** DAI validation MUST be run: (a) at each assessment cycle boundary; (b) whenever a new construct registration is processed; (c) when a FeatureBundle is created or updated.

**Cycle detection response.** If a `construct-dependency-cycle` BLOCKING gap is discovered during (a) an assessment cycle, the current cycle MUST complete its in-progress Operation (if any) but MUST NOT start any new Operations until the gap is cleared; (b) a new construct registration, the registration MUST be rejected and the construct MUST NOT be added to the ConstructKindRegistry; (c) a FeatureBundle create/update, the FeatureBundle write MUST be rejected with an error returned to the operator.

**Unknown construct detection.** When DAI validates a FeatureBundle, each entry in `FeatureBundle.construct_ids` MUST be verified to exist in the ConstructKindRegistry at the current spec version. Any unrecognized construct ID MUST surface `feature-bundle-unknown-construct` WARNING gap with field `unknown_id`. An unknown construct in a FeatureBundle MUST NOT cause the entire bundle to be rejected; the known constructs MUST still be resolvable. This allows bundles to reference constructs added in future spec versions without blocking present use.

**Self-reference detection.** `construct-self-reference` BLOCKING gap MUST be surfaced with field `construct_id`. A self-referencing construct MUST be rejected from the ConstructKindRegistry; any existing registration that contains a self-reference discovered at assessment cycle time MUST be treated as a BLOCKING gap requiring operator clearance.

**Referenced from:** §62n ConstructKindRegistry, §62l IntegrityGapCatalog, §62b FeatureBundle.

---

## IntegrityGapCatalog

**Construct metadata.** `kind: Protocol` · `tier: FOUNDATIONAL` · `standalone: true` · `depends: []`

The complete set of named IntegrityGap kinds emitted by the URACE runtime. Each kind is defined once. An implementation MUST NOT emit a gap kind not in this catalog without registering it here.

| kind | severity | triggering section | resolution |
|---|---|---|---|
| `progress-stagnation` | BLOCKING | §62c executor quality | Route reassessment or repair |
| `derived-manifest-stale` | WARNING | §62j stale DerivedManifestRef | `urace derive --refresh` |
| `regression-checkpoint-pending` | WARNING | §62c X2 checkpoint gate | CHECKPOINT_ACCEPTANCE DecisionRecord |
| `stale-decision-revalidation` | WARNING | §62c staleness detection | Revalidate or supersede decision |
| `over-engineered` | WARNING | §59b capability envelope | Complexity reduction objective |
| `cognitive-resume-stale` | WARNING | §62e CRC verification | CRC regeneration from current state |
| `compaction-manifest-divergence` | BLOCKING | §62f compaction | Manual manifest repair |
| `capability-envelope-breach` | WARNING | §59b envelope gate | CAPABILITY_SCOPE_EXPANSION DecisionRecord |
| `capability-without-test-coverage` | WARNING | §59b test coverage gate | Add TestRecord(kind=CAPABILITY_GATE) |
| `pattern-capability-gap` | WARNING | §62j derivation | Register CapabilityStatement or apply caps |
| `no-hard-constraints-declared` | WARNING | §72 bootstrap contract | Declare at least one HardConstraint |
| `retention-policy-violated` | WARNING | §62b retention | Compact field or revise RetentionPolicy |
| `wake-registration-missing-fields` | WARNING | §67 wake verification | Fix WakeRegistration required fields |
| `wake-registration-unverified` | WARNING | §67 wake verification | Set verified_at on WakeRegistration |
| `governing-record-unresolvable-authority` | WARNING | §62l GoverningRecord | Correct authority_basis reference |
| `authority-conflict` | BLOCKING | §14–§16 resolution | Authority conflict resolution via §14 |
| `indeterminate-effect-unresolvable` | BLOCKING | §52–§53 reconciliation | Operator-authorized disposition |
| `incomplete-discovery-cycle` | WARNING | §38 discovery | Resolve blocking capability gap |
| `assessment-cycle-error-interrupted` | WARNING | §37 assessment | Fix enumeration error in named category |
| `operator-gate-open` | BLOCKING | §62l OperatorGateProtocol | Authenticated operator clearance |
| `wake-integrity-gap` | WARNING | §62l WakeRegistrationVerification | Re-establish WakeRegistration in current environment |
| `compliance-record-missing` | WARNING | §62l ComplianceRecordingContract | Ensure validation gate appends ComplianceRecord per assessed domain |
| `stale-decision` | WARNING | §62c Staleness Detection Mechanism | Revalidate or supersede stale DecisionRecord |
| `stale-evidence` | WARNING | §62c Staleness Detection Mechanism | Refresh or revalidate stale Evidence record |
| `unsupported-rule` | WARNING | §62c Staleness Detection Mechanism | Add supporting Evidence or deactivate unsupported rule |
| `capability-state-missing` | WARNING | §43 executor capability management | Initialize CapabilityState for declared capability |
| `context-budget-priority-inversion` | WARNING | §62c Context Budget Mechanism | Fix ContextInput tier ordering to honor AP24 eviction priority |
| `discovery-proportionality-deferred` | WARNING | §62c Discovery Credit Gate | Reduce discovery scope to restore credit proportionality |
| `discovery-yield-exhausted` | WARNING | §62c Discovery Credit Gate | Await qualifying reset event or invoke force-discovery |
| `milestone-chain-broken` | BLOCKING | §59b Milestone Progression Chain | Restore milestone chain continuity or re-derive milestone sequence |
| `milestone-chain-cycle` | BLOCKING | §59b Milestone Progression Chain | Remove cycle from milestone dependency graph |
| `non-monotone-version` | BLOCKING | §59b ProductVersion | Restore monotone ProductVersion progression |
| `operation-dependency-cycle` | BLOCKING | §65 Partial Blocking | Remove cycle from OperationDependency graph before scheduling |
| `reingestion-archive-missing` | BLOCKING | §62c Re-Ingestion Mechanism | Locate or restore archive file required for re-ingestion |
| `reingestion-digest-mismatch` | BLOCKING | §62c Re-Ingestion Mechanism | Verify archive integrity; do not proceed with mismatched digest |
| `test-run-count-mismatch` | WARNING | §62c Test Coverage Gate | Reconcile test run count with expected baseline |
| `decision-reasoning-cycle` | WARNING | §62g Justification System | Remove cycle from DecisionRecord prior_decision_refs chain |
| `capability-without-test-record` | WARNING | §62b TestRecord | Add TestRecord(kind=CAPABILITY_GATE) for undocumented capability |
| `context-budget-advisory` | INFO | §62c Context Budget Mechanism | Review context budget configuration; advisory only |
| `metric-definition-drift` | WARNING | §62b MetricDefinition / §62c Staleness Detection | A MetricDefinition was replaced or mutated without authority authorization |
| `governance-anchor-drift` | BLOCKING | §62c Destination Anchor / §8 Destination Semantics | Destination anchor hash changed mid-cycle without anchoring ceremony |
| `metric-baseline-unauthorized-mutation` | BLOCKING | §62b MetricDefinition mutation_requires | MetricDefinition with mutation_requires=IMMUTABLE was modified after seeded_at |
| `metric-mutation-policy-missing` | WARNING | §62b MetricDefinition mutation_requires | MetricDefinition with mutation_requires=PERMISSION has no active PERMISSION rule in Rule Ledger |
| `threshold-audit-missing` | WARNING | §62h T2 Bar-Raising Calculus | T2 bar-raising occurred without producing threshold-adjustment Evidence record |
| `citizen-base-violation` | WARNING | §62b Base Citizen Clusters | Citizen schema missing REQUIRED CitizenBase fields (id, created_at, updated_at) |
| `authority-cache-stale` | WARNING | §62c Authority Resolution Mechanism | Authority resolution cache older than 3600 seconds used without re-validation |
| `executor-policy-missing` | WARNING | §62a Bootstrap Seeding | No POLICY rules seeded in Rule Ledger for executor configuration at bootstrap |
| `unresolved-effects-reconciliation-failure` | WARNING | §62c reconciliation | _reconcile_unresolved_effects raised exception; effects may be partially reconciled |
| `compaction-authorization-stale` | WARNING | §62f Authorization model | Re-request authorization (re-trigger RetentionPolicy or re-queue operator command) |
| `validation-evidence-missing` | WARNING | §62b Operation schema | Populate validation_evidence_id or validation_skipped_reason before ACCEPTED transition |
| `justification-depth-exceeded` | WARNING | §62g Justification System | Increase Config max_depth or simplify justification chain |
| `justification-cycle-detected` | BLOCKING | §62g Justification System | Remove cycle from JustificationNode chain before committing effect |
| `activation-health-failure` | BLOCKING | §74 Safe Runtime Activation | Operator rollback verification required |
| `rollback-failure` | BLOCKING | §74 Safe Runtime Activation | Operator intervention required to restore stable runtime |
| `partial-update-recovered` | INFO | §74 Safe Runtime Activation | Informational; partial update resolved successfully |
| `partial-update-unrecoverable` | BLOCKING | §74 Safe Runtime Activation | Operator must manually restore runtime state |
| `spec-state-divergence` | BLOCKING | §74 Safe Runtime Activation | Operator must explicitly clear before evolution proceeds |
| `rebootstrap-attempt-failed` | INFO | §74 Re-Bootstrap | Informational; attempt count included in gap detail |
| `rebootstrap-terminal-failure` | BLOCKING | §74 Re-Bootstrap | Operator must clear and reset attempt counter |
| `crc-version-mismatch` | WARNING | §62e CognitiveResumeContext | Retain current CRC; Executor must be updated to current spec version |
| `crc-context-overflow` | BLOCKING | §62e/§62c CRC injection | Operator must reduce CRC size or increase context budget |
| `unauthorized-threshold-adjustment` | WARNING | §62c Staleness Detection | Add threshold-adjustment-authorized Evidence record |
| `wake-registration-stale` | WARNING | §62c Wake Registration Verification | Operator re-establishment required |
| `wake-registration-expired` | BLOCKING | §62c Wake Registration Verification | Operator must re-establish registration and clear gap |
| `archive-not-found` | BLOCKING | §62c Re-Ingestion Mechanism | Locate or restore archive; check Config.archive_search_paths |
| `reingestion-duplicate-skipped` | INFO | §62c Re-Ingestion Mechanism | Informational; idempotent re-ingestion detected |
| `metric-source-discovery-unavailable` | WARNING | §62c External Metric Collection | Configure Config.metric_sources.search_endpoint or registry |
| `retention-pass-partial-failure` | WARNING | §62f Retention Policy | Investigate failed eviction; re-run compaction |
| `crrp-step-failure` | BLOCKING | §73 CRRP | Operator must clear gap and resume from last completed step |
| `crrp-retry-exceeded` | BLOCKING | §73 CRRP | Operator must clear gap; source_event_id retry limit reached |
| `technique-classification-disagreement` | WARNING | §62h T5 | Review classification disagreement in /rules output |
| `value-density-below-floor` | WARNING | §62c Sweet Spot Evaluation | Consider refactoring or scope reduction objective |
| `capability-regression` | WARNING | §62c Test Coverage Gate | Investigate regressed test or deleted code path |
| `milestone-chain-integrity-failure` | BLOCKING | §59b ProductMilestone | Fix dangling reference or cycle in milestone chain |
| `effect-unreconcilable` | WARNING | §52 Effect Reconciliation | Operator review required before closing Operation |
| `stale-manifest-override` | WARNING | §62j Stale DerivedManifestRef | Surfaced until manifest is refreshed |
| `scp-forward-reference` | BLOCKING | §62n SCP Gate 1 | A normative statement references a concept not yet defined in the formal index at point of reference |
| `scp-incomplete-revision-declaration` | WARNING | §62n SCP Gate 2 | A revision log entry is missing the required New external references field |
| `scp-atomic-extension-violation` | BLOCKING | §62n SCP Gate 3 | A MUST/SHALL statement references a concept that is not defined in the same revision |
| `construct-dependency-cycle` | BLOCKING | §62n DAI | Construct dependency graph contains a cycle; circular dependency MUST be resolved before the construct is used |
| `construct-self-reference` | BLOCKING | §62n DAI | A construct's `requires`, `depends`, or `governed-by` field references its own ID; self-reference is prohibited |
| `community-feed-terms-not-accepted` | BLOCKING | §62c CSI | Feed terms have not been accepted; ingest MUST NOT proceed until `CommunityFeed.terms_accepted = true` |
| `community-inbox-evolution-blocked` | WARNING | §62c PPP_M | A URACE-targeted PatchProposal arrived but Config.self_evolution_policy.mode = DISABLED; proposal held as PENDING; operator must change self_evolution_policy or explicitly reject |
| `feature-bundle-unknown-construct` | WARNING | §62n DAI | A FeatureBundle.construct_ids entry does not match any registered construct in the ConstructKindRegistry; verify construct ID and spec version |
| `community-feed-adapter-unavailable` | WARNING | §62c CSI | Configured CommunityFeed adapter cannot connect to endpoint; check feed config and network |
| `patch-proposal-confidence-below-floor` | INFO | §62c PPP | Signal passed relevance_floor but confidence_score < confidence_threshold; proposal marked CONFIDENCE_INSUFFICIENT |
| `patch-proposal-queue-overflow` | WARNING | §62c PPP | Active PatchProposal count reached max_queue_depth; new proposals blocked until queue drains |
| `community-signal-relevance-below-floor` | INFO | §62c CSI | Signal relevance_score < relevance_floor; signal discarded without producing a PatchProposal |
| `onboard-config-incomplete` | BLOCKING | §62c OnboardGate | Config is missing required fields (product, intent.purpose, capability_envelope); complete Config before autonomous cycles can begin |
| `onboard-no-readable-product-files` | BLOCKING | §62c OnboardGate | One or more Config.product_files paths are not readable; fix file paths and permissions before onboarding |
| `onboard-intent-unanchored` | BLOCKING | §62c OnboardGate | Config.intent.purpose is absent or empty; set a non-empty intent purpose to anchor autonomous evolution |
| `onboard-capability-envelope-missing` | WARNING | §62c OnboardGate | Config.capability_envelope is absent; capabilities will be unconstrained — declare envelope or set capability_envelope_waived in OnboardRecord |
| `onboard-confirmation-pending` | BLOCKING | §62c OnboardGate | All BLOCKING onboard gates passed; awaiting operator confirmation (`urace onboard confirm`) to authorize autonomous cycles |
| `onboard-record-config-diverged` | WARNING | §62b OnboardRecord staleness contract | Config.product or Config digest has diverged from the active OnboardRecord; run `urace onboard confirm` to refresh |
| `product-registry-unknown-product` | WARNING | §62c ProductSwitchProtocol | Target product not found in Config.product_registry or has status≠ACTIVE; register or activate it first |
| `product-switch-pending-onboard` | INFO | §62c ProductSwitchProtocol | Product switch applied; new active product awaits onboard confirmation (`urace onboard confirm`) |
| `product-registry-duplicate-name` | WARNING | §62b ProductEntry uniqueness contract | Two ProductEntry records share the same name; remove the duplicate before switching |
| `blocker-escalated` | WARNING | §62b Blocker schema classification contract | Acknowledge escalation; consider operator intervention if pattern persists |
| `integrity-signal-unclassified` | WARNING | §62c SignalClassifier | Review unclassified condition and register it in the SignalClassifier classification table |
| `lifecycle-boundary-violation` | BLOCKING | §62b LifecycleBoundary / §62l BoundaryContract | Apply Transaction Recovery Protocol (AP27); resolve incomplete boundary before creating new ones |
| `justification-context-incomplete` | WARNING | §62b JustificationContext / §62l JustificationContract | Supply missing JustificationContext predicates before committing consequential action |
| `inbox-priority-tier-violation` | WARNING | §62i AP14 priority-tier contract | Operator assigned Tier 0 to a non-hardcoded input kind; correct input or tier assignment |
| `checkpoint-write-timeout` | WARNING | §61 Checkpoint / §62b CheckpointRecord | Checkpoint write did not complete within 30 seconds; investigate persistence layer and re-attempt |

**Severity tiers.** BLOCKING — MUST halt the dependent operation before any effect is committed. WARNING — MUST be surfaced but MUST NOT block unrelated workstreams. INFO — MUST be surfaced in output but carries no operational obligation; informational only.

**Multi-BLOCKING ordering.** When two or more BLOCKING gaps are simultaneously active, the runtime MUST evaluate and surface them in the following priority order: (1) gaps with `kind` matching `*-failure` or `*-terminal-*` (system integrity failures); (2) gaps with `kind` matching `*-divergence` or `*-cycle-*` (state consistency violations); (3) gaps with `kind` matching `*-expired` or `*-overflow` (resource exhaustion); (4) all other BLOCKING gaps in lexicographic order of `kind`. The ordering governs display and audit output; ALL BLOCKING gaps MUST still halt autonomous Operations regardless of order.

**Operator clearance contract.** A BLOCKING gap MUST be clearable only by an operator-issued command (not autonomously). The clearance command MUST record: `cleared_by: operator`, `cleared_at`, `clearance_note` (free-text explanation). The IntegrityGap record MUST be updated to `active: false` with the clearance fields populated. A BLOCKING gap MAY only be auto-cleared by the runtime if the gap kind defines `auto_clearable: true` in the ConstructKindRegistry (§62n).

**Isolation contract.** A BLOCKING gap MUST halt only the Operations in its declared `scope`. If `scope` is not declared, the gap MUST halt ALL autonomous Operations (conservative default). A gap with `scope: [workstream_id]` MUST halt only Operations belonging to that workstream. The runtime MUST NOT propagate a scoped BLOCKING gap to unrelated workstreams.

**Used in:** (universal — all spec sections; any section that detects a normative violation MUST emit via this catalog)

**Extension contract.** A derived system MAY define additional gap kinds by registering them in its own IntegrityGapCatalog extension. Extension kinds MUST use a scoped prefix (e.g., `myapp-`) to avoid collisions. **Severity contract.** BLOCKING gaps MUST halt the dependent operation before any effect is committed. WARNING gaps MUST be surfaced but MUST NOT block unrelated workstreams. INFO gaps MUST be surfaced in output but carry no operational obligation.

---

## PatternMechanismMapping

**Construct metadata.** `kind: Protocol` · `tier: INTEGRATED` · `standalone: false` · `depends: [AP24]`

The complete mapping from AP patterns (§62i) to the spec sections that implement them, enabling the `urace derive` system and `--opt-in-constructs` to operate on a structured lookup rather than full-text parsing.

| AP | Pattern name | Implementing section(s) | Role | Key provides |
|---|---|---|---|---|
| AP0 | Citizen Schema Identity | §62b (all citizens), §62l GoverningRecord | PRIMARY | id prefix, uniqueness, lifecycle traceability |
| AP1 | Canonical Scalar | §62b canonical primitives, §62l | PRIMARY | typed leaf values, define-once |
| AP2 | Citizen Schema | §62b, §62l InspectionSurface, §62l GoverningRecord | PRIMARY | named versioned structures, minimality |
| AP3 | Append-Only Log | §62b evidence/checkpoints/operations, §62f compaction | PRIMARY | durable ordered sequence, monotone length |
| AP4 | Producer-Consumer Contract | §43 executor boundary, §62c mechanisms, §72 policy gate | PRIMARY | named bilateral obligations |
| AP5 | Idempotency Contract | §50, §51, §62b InputQueue | PRIMARY | retry safety, idempotency class |
| AP6 | Causal Provenance Chain | §53 reconciliation, §62e CRC, §62g justification | PRIMARY | full cause traceability |
| AP7 | Canonical Reduction | §62a rule ledger, §62h TAS | PRIMARY | semantic deduplication, minimality |
| AP8 | Fixpoint Calculus | §37 assessment cycle, §38 discovery | PRIMARY | stagnation detection, convergence |
| AP9 | Monotone Accumulator | §59b capability completeness, §62c quality streak | PRIMARY | monotone growth invariant |
| AP10 | Bounded Retry with Backoff | §43 executor selection, §62c discovery credit gate | PRIMARY | resilient bounded retry |
| AP11 | Bridge | §62i Bridge topology, inter-scope operations | PRIMARY | authority-boundary translation |
| AP12 | Orchestrator | §62i Orchestrator topology, multi-step plans | PRIMARY | sequenced operations, safe abort |
| AP13 | Observer | §60 autonomous feedback, §71 live observability | PRIMARY | decoupled observation, broadcast |
| AP14 | Durable Inbox | §38 queued inputs, §62l OperatorGateProtocol | PRIMARY | crash-safe FIFO, orderly shutdown |
| AP15 | Broadcast Log | §60 machine/human channels | PRIMARY | decoupled pub/sub, event history |
| AP16 | State Snapshot + Delta Log | §60 validation, §73 recovery | PRIMARY | atomic snapshot+delta, causal reconstruction |
| AP17 | Lexical→Formula Reduction | §62a rule formalization | PRIMARY | spec rule formalization, machine-verifiable |
| AP18 | Scheduled Task Contract | §42 scheduling, §62c scheduled tasks | PRIMARY | durable named scheduled tasks |
| AP19 | Customization Layer | §62b CustomizationRecord | PRIMARY | named scoped overrides, conflict detection |
| AP20 | Circuit Breaker | §43 systematic failure, §62c quality streak | PRIMARY | proactive failure-rate gating |
| AP21 | Compaction | §62f compaction mechanism | PRIMARY | bounded growth, archive + decompact |
| AP22 | Checkpoint | §61 checkpoint, §62c checkpoint mechanism | PRIMARY | accepted-state snapshot, recovery anchor |
| AP23 | Justification Chain | §62g justification system, `urace why` | PRIMARY | reasoning chain traversal |
| AP24 | Derivation Framework | §62j derivation, `urace derive` | PRIMARY | DerivedSystemManifest, zero-conformance |
| AP25 | Bounded Evolution Band | §59b capable evolution, §62c envelope gate | PRIMARY | capability ceiling, sweet-spot band |
| AP26 | Lifecycle State Machine | §64 Lifecycle States | PRIMARY | 12-state machine with guarded transitions and durable recording |
| AP27 | Transaction Recovery Protocol | §52–§53, §62c Transaction Mechanism | PRIMARY | 4-phase journal with crash-consistent rollback/roll-forward |
| AP28 | Independent Validation Gate | §54, §60, §62b PendingValidation | PRIMARY | executor≠validator separation; pending-preservation; capability-restoration trigger |
| AP29 | Dormancy/Wakeability Contract | §66, §67, §62c Wake Registration | PRIMARY | verified wakeability mechanism; cost-bounded liveness path |
| AP30 | Partial Blocking Dependency Graph | §65, §62b OperationDependency | PRIMARY | DAG-based minimum blocked-set computation |
| AP31 | Safe Runtime Activation | §74 Safe Runtime Activation | PRIMARY | blue-green deployment with crash-consistent promotion |
| AP32 | Single-Writer Ownership Lock | §63, §62b OwnershipMarker | PRIMARY | durable liveness-verified ownership attribution |
| AP33 | Policy Enforcement Gate | §72, §62b PolicyRecord, HardConstraint | PRIMARY | pre-commit scope-intersection policy evaluation |
| AP34 | Self-Evolution Eligibility Gate | §62c Self-Evolution Gate, §74 | PRIMARY | 3-mode gate; gate-before-authority; fail-closed |
| AP35 | Governance Ledger | §62a Rule Ledger, §62c Authority Resolution | PRIMARY | L0/L1/L2 immutability; rule DAG; conflict detection |
| AP36 | Digest Chain Consistency | §62c Digest Computation, §62e CRC | PRIMARY | fixed SHA-256 algorithm; chain-continuity invariant |
| AP37 | Compliance Posture Tracker | §60, §62b ComplianceRecord/State | PRIMARY | per-domain trajectory + accumulator; compliance-record-missing gap |
| AP38 | Community Signal Ingestion | §62c CSI, §62c PPP_M | PRIMARY | agnostic feed ingestion, T&C gate, relevance+confidence scoring, patch proposal pipeline (AUTO/SMART/HUMAN) |

**Role values:** `PRIMARY` — the principal mechanism for this AP; `SUPPORTING` — supplements the primary mechanism. Each AP MUST have exactly one PRIMARY entry. SUPPORTING entries are optional and MUST NOT be used to satisfy the AP's core intent alone.

**Uniqueness contract.** Each AP ID MUST map to at most one primary Mechanism or Protocol. Secondary associations are permitted and MUST be marked with `role: SUPPORTING` in the mapping record. If two entries claim `role: PRIMARY` for the same AP ID, the ConstructKindRegistry (§62n) entry for that AP governs which is primary.

**Ambiguity resolution.** When a gap kind maps to more than one Mechanism, the runtime MUST apply them in the order listed in the PMM table (top-to-bottom). If the first Mechanism resolves the gap (gap transitions to `active: false`), subsequent Mechanisms MUST NOT be applied. If the first does not resolve the gap, the next MUST be attempted in sequence.

**Multi-mechanism execution order.** When a single gap kind maps to both a Mechanism (§62c) and a Protocol (§62l), the Mechanism MUST execute first. If the Mechanism does not resolve the gap, the Protocol MUST be initiated.

**Referenced from:** §62l enforcement contract clause (7), §62j `urace derive` `--opt-in-constructs` resolution, §62m Protocol Catalog (PMM entry).

---

## QualityEnsuranceProtocol

**Construct metadata.** `kind: Protocol` · `tier: FOUNDATIONAL` · `standalone: true` · `depends: []`

The **QualityEnsuranceProtocol** (QE) is a post-change audit protocol applied after any spec revision to confirm that no degradations, ordering violations, cross-reference breaks, or contract inconsistencies were introduced by the changes. A QE pass MUST be performed after every revision that adds or modifies constructs, schemas, or catalog entries.

**Steps:**

1. **Enumerate changed constructs.** Identify every schema field, construct definition, catalog entry, and annotation modified or added in the revision.
2. **Schema field ordering.** For each modified schema, verify that REQUIRED fields precede OPTIONAL fields. Any OPTIONAL field positioned before a REQUIRED field is a degradation.
3. **Cross-reference resolution.** For every "Used in:", "Referenced from:", and "Citizens using:" annotation touched or introduced, verify the target (field name, section, construct ID) resolves to an existing declaration. An annotation pointing to an undeclared target is a degradation.
4. **Contract consistency.** For every MUST/SHALL behavioral contract in a modified section, verify it is not contradicted by another MUST/SHALL in the same or a dependent section.
5. **Count and catalog drift.** Verify that all catalog headers ("N entries") match the actual row count in their table. Verify that ConstructKindRegistry, Schema Catalog, Protocol Catalog, and Contract Catalog counts are mutually consistent after the revision.
6. **Emit finding list.** A QE pass that finds no degradations MUST be declared as `QE: PASS` in the revision log. A QE pass that finds degradations MUST list each finding and the fix applied before the revision is stable.

**Scope.** QE applies to the changes in the current revision only — it does not re-audit prior revisions. Prior revisions are addressed by dedicated gap-closure revisions.

**Referenced from:** §82 Revision Log (as a named pass type), all spec revisions.

---

## JoinProtocol

**Construct metadata.** `kind: Protocol` · `tier: FOUNDATIONAL` · `standalone: true` · `depends: []`

The **JoinProtocol** (JOIN) is a post-change wiring audit protocol applied after any spec revision that introduces or modifies schemas, constructs, or catalog entries. A JOIN pass confirms that all cross-references, scope annotations, and field declarations are mutually consistent — that every claim made by an annotation is backed by a declaration, and every declaration is reachable from the constructs that use it. A JOIN pass MUST be performed after every revision that adds new schemas, new "Used in:" annotations, or new "Referenced from:" annotations.

**Steps:**

1. **Enumerate new and modified constructs.** Identify every schema, mechanism, protocol, or catalog entry added or modified in the revision.
2. **"Used in:" resolution.** For every "Used in: X.Y" annotation on a new or modified schema, verify that field Y is declared in the schema or document X. An annotation pointing to an undeclared field is an unresolved join.
3. **"Referenced from:" resolution.** For every "Referenced from: §N" annotation, verify that §N exists and contains a normative reference to the construct. A reference to a non-existent or non-referencing section is an unresolved join.
4. **"Citizens using:" completeness.** For every "Citizens using: <schema>" annotation on a construct, verify that each listed schema declares conformance (via `Implements:` or `Uses canonical:`) to that construct.
5. **Universal scope classification.** For any construct or schema that applies across all lifecycle states or all sections, verify that its "Used in:" annotation explicitly states `(universal — ...)` rather than listing individual sections.
6. **Emit finding list.** A JOIN pass that finds no unresolved references MUST be declared as `JOIN: PASS` in the revision log. A JOIN pass that finds unresolved references MUST list each finding and the fix applied before the revision is stable.

**Scope.** JOIN applies to the changes in the current revision only — it does not re-audit prior revisions unless a prior annotation is directly modified.

**Referenced from:** §82 Revision Log (as a named pass type), all spec revisions.

---

## ProductSwitchProtocol

**Construct metadata.** `kind: Protocol` · `tier: INTEGRATED` · `standalone: true` · `depends: [OnboardGate]`

The ProductSwitchProtocol governs safe transitions between Products in the registry. It is defined once here; `urace product switch` cites it by name.

**Four-step protocol:**

1. **Validate target.** Verify the target product name exists in Config.product_registry with status=ACTIVE. If not, emit `product-registry-unknown-product` WARNING and abort.
2. **Record switch.** Append SwitchRecord(from_product=current, to_product=target, switched_at=now(), switched_by="operator") to State.switch_records. Save state.
3. **Update active product.** Set Config.active_product = target. Persist Config. Emit INFO gap `product-switch-pending-onboard`.
4. **Trigger re-onboard.** Next cycle entry detects no matching OnboardRecord for the new active_product → sets lifecycle_state=ONBOARDING → OnboardGate fires (§62c, §62o).

**Atomicity contract.** Steps 2 and 3 MUST be applied atomically from the operator's perspective. If Config cannot be persisted after step 2, the switch MUST be rolled back (remove the SwitchRecord) and an error returned.

**Referenced from:** §62o Product Onboard Phase (re-onboard trigger), §62k `urace product switch`.
**Citizens using ProductSwitchProtocol:** SwitchRecord (§62b).

# 62m. Extended Construct Catalogs

`urace derive --kind <kind>` exposes five construct catalogs beyond AP patterns. Each entry has: `name`, `kind`, `summary`, `provides`, `spec_section`, `standalone`.

## Mechanism Catalog (9 entries)

| ID | Name | Spec | Provides |
|---|---|---|---|
| QSM | Quality Streak Mechanism | §62c | quality streak counter, regression checkpoint gate |
| SSB | Sweet-Spot Band | §62c §59b | maturity classification, over-engineering detection |
| CEG | Capability Envelope Gate | §62c | ceiling enforcement, surface growth gate |
| TAG | Technique Applicability Gate | §62h | context-gated execution, applicability scoring |
| DCG | Discovery Credit Gate | §62e | discovery budget enforcement, credit gate |
| PSD | Progress Stagnation Detector | §62c | stagnation detection, REPAIRING lifecycle trigger |
| MBV | Metric Baseline Verification | §62c | cycle-start metric immutability audit, mutation_requires enforcement |
| SCF | SignalClassifier | §62c | runtime signal classification, IntegritySignal emission, REPAIRING entry gate |
| OBG | OnboardGate | §62c §62o | one-time product authorization gate, config integrity snapshot, ONBOARDING lifecycle enforcement |

## Schema Catalog (36 entries)

Portable, schema-bearing citizen data structures. Each carries a declared `id_prefix`, `required_fields` list, and `spec_section`. Any system can adopt individual schemas without the full URACE lifecycle.

| ID | Name | Prefix | Spec |
|---|---|---|---|
| GoalRecord | GoalRecord | goal- | §39 |
| ObjectiveRecord | ObjectiveRecord | obj- | §40 |
| PlanRecord | PlanRecord | plan- | §41 |
| EvidenceRecord | EvidenceRecord | ev- | §44 |
| DecisionRecord | DecisionRecord | dec- | §55 |
| PolicyRecord | PolicyRecord | pol- | §72 |
| HardConstraint | HardConstraint | hco- | §72 |
| AssessmentRecord | AssessmentRecord | asr- | §37 |
| DiscoveryRecord | DiscoveryRecord | dsc- | §36 |
| MarketSignal | MarketSignal | mks- | §59 |
| FitHypothesis | FitHypothesis | fhy- | §59 |
| OwnershipMarker | OwnershipMarker | omk- | §63 |
| ScheduledTask | ScheduledTask | sched- | §42 |
| QualityDelta | QualityDelta | qdelta- | §61 |
| IntegrityGap | IntegrityGap | igap- | §62l |
| CapabilityStatement | CapabilityStatement | cap- | §59b |
| OperationRecord | OperationRecord | op- | §53 |
| BridgeRecord | BridgeRecord | brd- | §62i AP11 |
| OrchestratorRecord | OrchestratorRecord | orch- | §62i AP12 |
| CheckpointRecord | CheckpointRecord | checkpoint- | §61 |
| DerivedManifestRef | DerivedManifestRef | dmr- | §62j |
| MetricEffect | MetricEffect | meffect- | §62b |
| ChunkingPolicy | ChunkingPolicy | — | §62f |
| Chunk | Chunk | chunk- | §62f |
| CommunityFeed | CommunityFeed | cfeed- | §62b |
| CommunitySignal | CommunitySignal | csig- | §62b |
| PatchProposal | PatchProposal | pprop- | §62b |
| FeatureBundle | FeatureBundle | fbundle- | §62b |
| FeatureBundleRef | FeatureBundleRef | fbref- | §62b |
| AssessmentGap | AssessmentGap | agap- | §62b |
| LifecycleBoundary | LifecycleBoundary | lcb- | §62b |
| IntegritySignal | IntegritySignal | isig- | §62b |
| JustificationContext | JustificationContext | jctx- | §62b |
| ProductEntry | ProductEntry | prod- | §62b |
| SwitchRecord | SwitchRecord | swrec- | §62b |

## Protocol Catalog (15 entries)

| ID | Name | Steps | Spec |
|---|---|---|---|
| EUP | EffectUncertaintyProtocol | classify INDETERMINATE → hold before retry → preserve durable record | §62l |
| OGP | OperatorGateProtocol | surface BLOCKING gap → hold state → await clearance → emit gate event | §62l |
| CRRP | CognitiveResetRecoveryProtocol | 6-step cognitive reset recovery | §62l |
| WRV | WakeRegistrationVerification | restart wakeability audit | §62l |
| CRC_C | ComplianceRecordingContract | per-domain compliance persistence | §62l |
| CEP | ConstructElevationProtocol | 4-gate elevation test for promoting concepts to named constructs | §62l |
| SCP | SpecConstructionProtocol | 3-gate pre-extension enforcement: definition-first, completeness declaration, single-pass atomicity | §62n |
| DAI | ConstructDependencyAcyclicityInvariant | acyclicity check → self-reference check → FeatureBundle DAG validation → surface BLOCKING gap | §62n |
| PPP | PatchProposalProtocol | T&C gate → signal ingest → relevance+confidence scoring → patch synthesis → approval routing (AUTO/SMART/HUMAN) → expiry; `urace /inbox list|apply|reject` | §62c PPP_M |
| JC | JustificationContract | evaluate 5-predicate justification test → record JustificationContext → prevent unjustified actions | §62l |
| BC | BoundaryContract | open boundary → verify conditions → commit atomically → handle incomplete on restart | §62l |
| PMM | PatternMechanismMapping | AP-to-section lookup → role classification → uniqueness check → ambiguity resolution | §62l |
| QE | QualityEnsuranceProtocol | enumerate changed constructs → field ordering check → cross-reference resolution → contract consistency → count/catalog drift → emit finding list (PASS or degradations) | §62l |
| JOIN | JoinProtocol | enumerate new/modified constructs → "Used in:" resolution → "Referenced from:" resolution → "Citizens using:" completeness → universal scope classification → emit finding list (PASS or unresolved refs) | §62l |
| PSP | ProductSwitchProtocol | validate target → record switch → update active product → trigger re-onboard | §62l |

## AP Pattern Abbreviations (r49 additions)

| ID | Name | Summary | Spec |
|---|---|---|---|
| LSM | Lifecycle State Machine | guarded transition machine; 12 states | §62i AP26 |
| TRP | Transaction Recovery Protocol | 4-phase journal; crash-consistent | §62i AP27 |
| IVG | Independent Validation Gate | executor≠validator; pending-preservation | §62i AP28 |
| DWC | Dormancy/Wakeability Contract | verified liveness path; cost-bounded | §62i AP29 |
| PBG | Partial Blocking Dependency Graph | DAG blocked-set; minimum scope | §62i AP30 |
| SRA | Safe Runtime Activation | blue-green; crash-consistent promotion | §62i AP31 |
| SWL | Single-Writer Ownership Lock | durable ownership; liveness-verified | §62i AP32 |
| PEG | Policy Enforcement Gate | pre-commit scope-intersection check | §62i AP33 |
| SEG | Self-Evolution Eligibility Gate | 3-mode; gate-before-authority | §62i AP34 |
| GVL | Governance Ledger | L0/L1/L2; rule DAG; conflict hold | §62i AP35 |
| DCC | Digest Chain Consistency | fixed SHA-256; chain invariant | §62i AP36 |
| CPT | Compliance Posture Tracker | per-domain trajectory + accumulator | §62i AP37 |
| CSI_AP | Community Signal Ingestion | agnostic feed ingestion; T&C gate; relevance+confidence scoring | §62i AP38 |

## Contract Catalog (6 entries)

| ID | Name | Provides | Spec |
|---|---|---|---|
| GRC | GoverningRecord | governance provenance, authority-basis traceability | §62l |
| IGC | IntegrityGapCatalog | named gap vocabulary (100 kinds), canonical severity | §62l |
| ISC | InspectionSurface | structured health output (11 categories) | §62l |
| ACI | AuthorityClosureInvariant | non-authority source enumeration, closure check | §62l |
| RVS | RevalidationScope | trigger-to-scope mapping, minimum revalidation contract | §62l |
| ABM | AuthorityBoundaryModel | delegated/reserved categories, scope-to-authority mapping | §14-16 |

## DerivedConstructSet Citizen

Output produced by `urace derive` when `--kind` includes any non-pattern kind.

| Field | Type | Description |
|---|---|---|
| `construct_set_id` | ID (prefix `cset-`) | Stable identity |
| `derived_from` | string | Always `"URACE"` |
| `spec_version` | string | URACE spec version at derivation time |
| `intent` | string | Intent text provided by operator |
| `generated_at` | ISO-8601 | Derivation timestamp |
| `adopted_constructs` | list | Each entry: `construct_id, name, kind, summary, provides, spec_section` |
| `kinds_present` | list[string] | Sorted unique kinds in adopted_constructs |

**IntentSuggestionEngine (construct mode):** ranks all entries in the ConstructCatalog by keyword overlap and domain-affinity bonus, filtered to the requested kinds. Returns `{construct_id, name, kind, score, summary}` results. Any conforming implementation MAY use any scoring strategy that preserves rank-by-relevance.

## ConstructSetRef Citizen

A lightweight reference to a saved DerivedConstructSet, stored in `state.construct_set_refs`. Created by `urace derive --kind ... --save`; enables stale-detection and refresh.

| Field | Type | Description |
|---|---|---|
| `id` | Identifier | Stable identity |
| `construct_set_id` | string | The `cset-xxx` ID of the saved set |
| `spec_version` | string | Spec version at derivation time |
| `generated_at` | ISO-8601 | When the set was derived |
| `adopted_construct_ids` | list[string] | Construct IDs in the set |
| `kinds_present` | list[string] | Distinct kinds in the set |
| `intent` | string | Original intent text |

**Stale-construct-set detection contract.** When the governing spec is updated, any stored ConstructSetRef whose `spec_version` differs from the new version MUST be surfaced as a `derived-construct-set-stale` warning. The warning MUST include the `construct_set_id`, the stale version, and the candidate version. Stale detection is a warning, not a blocker. **Refresh contract.** `urace derive --kind ... --refresh` re-derives all saved ConstructSetRefs (or the one matching `--manifest-id`) using their stored `adopted_construct_ids` and `intent`, writes updated refs to `state.construct_set_refs`, and appends a DerivationRecord of kind `CONSTRUCT_SET_REFRESH`.

**New-construct suggestion contract (r46).** On `urace update download` and `urace update explain`, for each saved ConstructSetRef the system MUST run IntentSuggestionEngine over the stored `intent`, filter out already-adopted construct IDs, and surface the top-N results as new-construct suggestions. Output MUST include the construct_set_id, intent, and suggestion list. This surfaces newly-added constructs that match the operator's original intent without requiring manual re-querying. **Construct update detection contract (r46).** If a saved ConstructSetRef includes `construct_digests`, the system MUST compare stored digests against current catalog entries for all adopted construct IDs. Any mismatch indicates the construct was updated since derivation and MUST be surfaced as a `construct update available` notice with the affected IDs and a ready-to-run `urace derive --refresh` command. The same detection applies to saved DerivedManifestRefs via `pattern_digests`.

# 62n. Normative Specification Standard

The Normative Specification Standard (NSS) is the self-description of URACE.md's structural rules. It is the base rule that governs how every construct in this specification is expressed, classified, and maintained. Every construct MUST conform to the NSS.

**Construct metadata.** `kind: Protocol` · `tier: FOUNDATIONAL` · `standalone: true` · `depends: []`

## Base Rule

Every concept in this specification MUST be expressed in its unique canonical form (AP7 — Canonical Reduction, §62i), at its correct kind in the 5-kind construct hierarchy, using the mandatory template for that kind, with RFC 2119 normative force on every binding statement.

**Base rule components:**
1. **Single definition.** Every concept is defined once, in its canonical section. No concept MAY be defined in two places.
2. **Correct kind.** Every concept belongs to exactly one of the five construct kinds. Placement in the wrong section is a structural violation.
3. **Mandatory template.** Every construct uses the template prescribed for its kind. Deviation from the template is a structural violation.
4. **Normative force.** Every binding statement uses RFC 2119 keywords (MUST/SHALL/SHOULD/MAY/MUST NOT/SHALL NOT). Binding statements without these keywords carry no normative force.
5. **Canonical reduction.** A construct that can be expressed more minimally without losing normative content MUST be reduced. Redundancy is a structural violation.

**Used in:** (universal — all spec sections; RFC 2119 normative force applies to every section of URACE.md)

## Normative Binding Scope

URACE.md contains two distinct classes of normative statements:

**Implementation-binding (I):** MUST/SHALL/MUST NOT/SHOULD statements that bind any conforming runtime implementation. The majority of normative statements in URACE.md are implementation-binding.

**Specification-binding (S):** MUST statements that bind the specification itself — governing how constructs are defined, cross-referenced, elevated, and maintained.

**Specification-binding directives:**

1. (S) Every construct MUST be defined once, at its correct kind in the 5-kind hierarchy, in its canonical section.
2. (S) Every construct MUST carry mandatory metadata for its kind (§62n Mandatory Construct Metadata).
3. (S) Every construct MUST use the mandatory template for its kind (§62n Templates per Kind).
4. (S) Every cross-reference MUST be bidirectional and complete.
5. (S) Every catalog that self-declares as "complete" or "canonical" MUST be exhaustive at the moment of declaration.
6. (S) No construct MAY be defined outside its canonical section.
7. (S) All construct promotions between kinds MUST follow the ConstructElevationProtocol (§62l).
8. (S) The PatternMechanismMapping (§62l) MUST be updated whenever a new AP is added or an existing AP's implementation section changes.
9. (S) The IntegrityGapCatalog (§62l) MUST be updated whenever a new IntegrityGap kind is emitted anywhere in the spec.

## 5-Kind Construct Hierarchy

Every construct in URACE.md belongs to exactly one of five kinds. The kinds form the classification spine of the specification.

| Kind | Canonical section | Purpose | Template anchor |
|---|---|---|---|
| **AP** (Architectural Pattern) | §62i | Structurally reusable behavioral meta-pattern applicable across multiple independent contexts | Derivation metadata · Intent · Roles · Constraints · Implementation |
| **Protocol** | §62l | Named cross-cutting contract referenced by multiple sections by name | Construct metadata · Purpose · Steps/clauses · Citizens using · Referenced from |
| **Mechanism** | §62c | Concrete algorithmic implementation of a behavioral contract; governed by ≥1 AP | Construct metadata · AP citation · Pseudocode/formula · Normative contracts |
| **Schema** | §62b | Named, versioned data structure with identity and traceability | Schema block · Uses canonical · Used in |
| **Primitive** | §62d | Canonical scalar type with format, validation, and usage contracts | Name · Type · Domain · Validation rule · Null policy |

## Construct Lattice

The reuse model for all constructs is a two-dimensional lattice. Every construct's position in the lattice determines its reuse priority.

```
ABSTRACTION AXIS (Kind):
AP ──── Protocol ──── Mechanism ──── Schema ──── Primitive
(most abstract,                                   most concrete,
 structurally reusable)                           leaf-reusable)

DEPENDENCY DEPTH AXIS (Tier):
FOUNDATIONAL ──── COMPOSITIONAL ──── INTEGRATED
(fewest deps,                        most deps,
 standalone)                         least standalone)
```

**Reuse rule.** Prefer the highest kind at the lowest tier that satisfies your requirement. FOUNDATIONAL AP: maximally structurally reusable. FOUNDATIONAL Primitive: maximally leaf-reusable.

**Tier definitions (apply to all kinds):**

| Tier | Definition |
|---|---|
| `FOUNDATIONAL` | standalone=true, or all declared dependencies are themselves FOUNDATIONAL |
| `COMPOSITIONAL` | depends on one or more FOUNDATIONAL constructs; not usable in isolation |
| `INTEGRATED` | depends on one or more COMPOSITIONAL or INTEGRATED constructs |

## Mandatory Construct Metadata

Every construct MUST carry a metadata line immediately after its `##` heading. Format per kind:

**AP:** `**Derivation metadata.** kind: AP · tier: X · standalone: X · requires: [...] · provides: [...] · realizes: [<ConstructID>, ...] (OPTIONAL)`
*(kind: AP is implied by §62i section membership; the metadata line is already established. `realizes:` is OPTIONAL; when present, it lists the Mechanism and Protocol IDs that directly implement this AP. This makes the AP→implementation link machine-readable without requiring PMM table lookup.)*

**Protocol:** `**Construct metadata.** kind: Protocol · tier: X · standalone: X · depends: [...]`

**Mechanism:** `**Construct metadata.** kind: Mechanism · tier: X · standalone: false · governed-by: [AP_N, ...]`

**Schema:** `**Construct metadata.** kind: Schema · tier: X · standalone: X` *(add `refines: [ParentSchema]` only when the Schema specializes another Schema)*

**Primitive:** No construct metadata required beyond its definition block.

`refines:` declares a specialization (subtype) relationship — distinct from `depends:` (usage dependency). A Schema that `refines:` another inherits its fields and adds or constrains them.

## Templates per Kind

Templates are defined in their canonical sections. This is the reference index:

| Kind | Template exemplar | Required sections |
|---|---|---|
| AP | §62i AP26–AP37 | Derivation metadata · Intent · Roles · Constraints · Implementation |
| Protocol | §62l CognitiveResetRecoveryProtocol | Construct metadata · purpose sentence · steps/clauses · Citizens using · Referenced from |
| Mechanism | §62c any well-formed entry | Construct metadata · AP citation · contract paragraphs |
| Schema | §62b ComplianceRecord | schema block · Uses canonical · Used in |
| Primitive | §62d Identifier | name · type · domain · validation · null policy |

## Construct Kind Registry

Complete cross-reference of all named constructs by kind and tier. Primitives (§62d) are omitted — they are enumerated in full in §62d.

**`auto_clearable` field.** Every gap kind registered in the ConstructKindRegistry carries an implicit `auto_clearable: bool` attribute. When `auto_clearable: true`, the runtime MAY clear a BLOCKING gap of this kind without operator intervention, provided the clearing condition is deterministic and fully captured in the State Document. Default: `false`. MUST be `false` for all gap kinds that require operator judgment. A gap kind's `auto_clearable` value governs the auto-clearance permission referenced in the IntegrityGapCatalog Operator clearance contract (§62l).

### APs (§62i)

| AP | Name | Tier |
|---|---|---|
| AP0 | Citizen | FOUNDATIONAL |
| AP1 | Canonical Scalar | FOUNDATIONAL |
| AP2 | Citizen Schema | FOUNDATIONAL |
| AP3 | Append-Only Log | FOUNDATIONAL |
| AP4 | Producer-Consumer Contract | FOUNDATIONAL |
| AP5 | Idempotency Contract | FOUNDATIONAL |
| AP6 | Causal Provenance Chain | COMPOSITIONAL |
| AP7 | Canonical Reduction | FOUNDATIONAL |
| AP8 | Fixpoint Calculus | COMPOSITIONAL |
| AP9 | Monotone Accumulator | COMPOSITIONAL |
| AP10 | Bounded Retry with Backoff | COMPOSITIONAL |
| AP11 | Bridge | COMPOSITIONAL |
| AP12 | Orchestrator | COMPOSITIONAL |
| AP13 | Observer | COMPOSITIONAL |
| AP14 | Durable Inbox | COMPOSITIONAL |
| AP15 | Broadcast Log | COMPOSITIONAL |
| AP16 | State Snapshot + Delta Log | INTEGRATED |
| AP17 | Lexical→Formula Reduction | COMPOSITIONAL |
| AP18 | Scheduled Task Contract | INTEGRATED |
| AP19 | Customization/Personalization Layer | INTEGRATED |
| AP20 | Circuit Breaker | COMPOSITIONAL |
| AP21 | Compaction | COMPOSITIONAL |
| AP22 | Checkpoint | COMPOSITIONAL |
| AP23 | Justification Chain | COMPOSITIONAL |
| AP24 | Derivation Framework | INTEGRATED |
| AP25 | Bounded Evolution Band | INTEGRATED |
| AP26 | Lifecycle State Machine | FOUNDATIONAL |
| AP27 | Transaction Recovery Protocol | INTEGRATED |
| AP28 | Independent Validation Gate | COMPOSITIONAL |
| AP29 | Dormancy/Wakeability Contract | COMPOSITIONAL |
| AP30 | Partial Blocking Dependency Graph | COMPOSITIONAL |
| AP31 | Safe Runtime Activation | INTEGRATED |
| AP32 | Single-Writer Ownership Lock | COMPOSITIONAL |
| AP33 | Policy Enforcement Gate | COMPOSITIONAL |
| AP34 | Self-Evolution Eligibility Gate | INTEGRATED |
| AP35 | Governance Ledger | FOUNDATIONAL |
| AP36 | Digest Chain Consistency | INTEGRATED |
| AP37 | Compliance Posture Tracker | INTEGRATED |
| AP38 | Community Signal Ingestion | INTEGRATED |

### Protocols (§62l)

| ID | Name | Tier | Standalone |
|---|---|---|---|
| GRC | GoverningRecord Canonical Cluster | FOUNDATIONAL | true |
| EUP | EffectUncertaintyProtocol | COMPOSITIONAL | false |
| OGP | OperatorGateProtocol | FOUNDATIONAL | true |
| ACI | AuthorityClosureInvariant | FOUNDATIONAL | true |
| RVS | RevalidationScope | COMPOSITIONAL | false |
| CRRP | CognitiveResetRecoveryProtocol | INTEGRATED | false |
| WRV | WakeRegistrationVerification | COMPOSITIONAL | false |
| CRC_C | ComplianceRecordingContract | COMPOSITIONAL | false |
| ISC | InspectionSurface Contract | FOUNDATIONAL | true |
| IGC | IntegrityGapCatalog | FOUNDATIONAL | true |
| PMM | PatternMechanismMapping | INTEGRATED | false |
| QE | QualityEnsuranceProtocol | FOUNDATIONAL | true |
| JOIN | JoinProtocol | FOUNDATIONAL | true |
| CEP | ConstructElevationProtocol | FOUNDATIONAL | true |
| SCP | SpecConstructionProtocol | FOUNDATIONAL | false |
| DAI | ConstructDependencyAcyclicityInvariant | FOUNDATIONAL | true |
| PPP | PatchProposalProtocol | INTEGRATED | false |

### Mechanisms (§62c)

| ID | Name | Tier | Governed by |
|---|---|---|---|
| IQM | Input Queue Mechanism | FOUNDATIONAL | AP14 |
| TXM | Transaction Mechanism | COMPOSITIONAL | AP16, AP27 |
| ARM | Authority Resolution Mechanism | FOUNDATIONAL | AP35 |
| DCM | Digest Computation | FOUNDATIONAL | AP36 |
| VTS | Value Trajectory Self-Correction Mechanism | INTEGRATED | AP8, AP9 |
| SPD | Scope Priority Derivation Mechanism | COMPOSITIONAL | AP8 |
| EMC | External Metric Collection Mechanism | COMPOSITIONAL | AP13 |
| DAI | Destination Anchor Integrity Mechanism | COMPOSITIONAL | AP35, OGP |
| SEG | Self-Evolution Eligibility Gate Mechanism | INTEGRATED | AP34 |
| DCG | Discovery Credit Gate Mechanism | COMPOSITIONAL | AP10, AP29 |
| QSM | Quality Streak Mechanism | COMPOSITIONAL | AP9, AP20 |
| RIM | Re-Ingestion Mechanism | INTEGRATED | AP21 |
| SDM | Staleness Detection Mechanism | COMPOSITIONAL | AP13 |
| CBM | Context Budget Mechanism | COMPOSITIONAL | AP24 |
| WRM | Wake Registration Verification Mechanism | COMPOSITIONAL | AP29, WRV |
| SSE | Sweet Spot Evaluation Mechanism | INTEGRATED | AP25 |
| CEG | Capability Envelope Gate | INTEGRATED | AP25, AP33 |
| TCG | Test Coverage Gate | COMPOSITIONAL | AP9 |
| CCA | Crash-Consistent Acceptance | COMPOSITIONAL | AP27 |
| LKS | Last-Known-Stable Product Recovery | COMPOSITIONAL | AP22 |
| MBV | Metric Baseline Verification | COMPOSITIONAL | AP13 |
| CSI | Community Signal Ingestion Mechanism | INTEGRATED | AP38, AP14 |
| PPP_M | Patch Proposal Pipeline Mechanism | INTEGRATED | AP38, AP4 |

### Schemas (r54–r55, r61, and r62 additions)

The following schemas were added in r54/r55, r61, and r62 and MUST be registered here per the ConstructElevationProtocol mandatory post-elevation actions.

| Name | Tier | Extends | Added |
|---|---|---|---|
| MetricEffect (citizen schema) | COMPOSITIONAL | CitizenBase | r54 |
| ChunkingPolicy | COMPOSITIONAL | CitizenBase | r53 |
| Chunk | COMPOSITIONAL | CitizenBase + GoverningRecord | r53 |
| CommunityFeed | INTEGRATED | CitizenBase | r61 |
| CommunitySignal | INTEGRATED | CitizenBase | r61 |
| PatchProposal | INTEGRATED | CitizenBase | r61 |
| FeatureBundle | COMPOSITIONAL | CitizenBase | r62 |
| FeatureBundleRef | COMPOSITIONAL | CitizenBase | r62 |
| OnboardRecord | FOUNDATIONAL | CitizenBase | r71 |
| ProductEntry | INTEGRATED | CitizenBase | r72 |
| SwitchRecord | INTEGRATED | CitizenBase | r72 |

# 62o. Product Onboard Phase

The Product Onboard Phase is the one-time entry ceremony that every new Product MUST complete before URACE begins autonomous cycles. It is the formal boundary between "URACE has been configured for a Product" and "URACE is authorized to operate autonomously on a Product." The phase is enforced by the OnboardGate Mechanism (§62c) and recorded by the OnboardRecord citizen schema (§62b).

## Purpose

The Onboard Phase serves three functions:

1. **Authorization anchor.** It establishes an operator-confirmed record that URACE is authorized to begin autonomous evolution for a specific named Product. Without this record, autonomous Operations MUST NOT proceed.
2. **Config integrity snapshot.** The OnboardRecord captures a digest of Config at onboard time, enabling future drift detection. If Config is replaced or mutated without re-onboarding, URACE surfaces the divergence immediately.
3. **Product switchability gate.** By tying the authorization to `Config.product` by name, URACE formally supports Product switching: changing `Config.product` invalidates the prior authorization and requires a new Onboard Phase for the new Product. This is the canonical mechanism for Product replaceability.

## Lifecycle Position

The Onboard Phase occupies the `ONBOARDING` lifecycle state, which precedes all maturity progression:

```
ONBOARDING (gate) → BOOTSTRAPPING → FORMING → CAPABLE → OPTIMIZED → OVER_ENGINEERED
```

`ONBOARDING` is the only lifecycle state in which autonomous Operations, discovery calls, and executor dispatches are prohibited (`SD=True`). No Executor credits are consumed during onboarding. The runtime remains in `ONBOARDING` until the operator issues `urace onboard confirm` and the OnboardGate clears all BLOCKING conditions.

## Entry Trigger

The OnboardGate fires at cycle entry when the current cycle finds no `OnboardRecord` in `State.onboard_records` whose `product_name` matches `Config.product`. Two conditions trigger entry:

1. **Fresh start.** No OnboardRecord exists at all — URACE has never been onboarded for any Product.
2. **Product switch.** An OnboardRecord exists but for a different `product_name` — the operator has replaced `Config.product` with a new Product name.

## Gate Steps

See §62c OnboardGate Mechanism for the full 7-step algorithm. Summary:

| Step | Gate | Severity | Clearance |
|---|---|---|---|
| 1 | Config completeness | BLOCKING | Fix Config fields |
| 2 | product_files readable | BLOCKING | Fix file paths/permissions |
| 3 | intent.purpose anchored | BLOCKING | Set non-empty intent purpose |
| 4 | capability_envelope declared | WARNING | Declare envelope or set waiver |
| 5 | self_evolution_policy recorded | INFO | Set policy or accept NECESSARY_ONLY default |
| 6 | Operator confirmation | BLOCKING | `urace onboard confirm` |
| 7 | (On confirm) Record, Checkpoint, clear gaps, set DORMANT | — | — |

Steps 1–3 MUST all pass before step 6 (`onboard-confirmation-pending`) is surfaced. A BLOCKING failure at step 1, 2, or 3 suppresses the confirmation prompt until the failure is resolved.

## Product Switchability

URACE is fully product-agnostic. The only product-specific contract is: `Config.product` (a name string) and `Config.product_files` (a list of readable file paths). URACE does not prescribe any particular file layout, database, or folder structure for the Product under evolution. Switching Products is a two-step operator action:

1. Replace `Config.product` and `Config.product_files` with the new Product's values.
2. Run `urace onboard status` and `urace onboard confirm` to establish a new OnboardRecord.

The prior Product's OnboardRecord is retained in `State.onboard_records` with `superseded_at` set. The prior Product's full State history (Objectives, Capabilities, Evidence, DecisionRecords) is also retained. URACE MUST NOT purge prior-Product state on switch; prior-Product state is frozen and excluded from active cycle evaluation by `product_name` mismatch.

**Product isolation contract.** At any given time, only the OnboardRecord whose `product_name` matches `Config.product` is active. All autonomous cycle operations (discovery, objective selection, capability gate, CSI, PPP_M) apply only to the active Product. Prior-Product records are read-only historical artifacts.

## Idempotency and Refresh

- `urace onboard status` is always safe to run — it never mutates State.
- `urace onboard confirm` on an already-onboarded Product (same name, same Config digest) is a no-op: the command MUST detect the existing record matches and emit a confirmation that the product is already onboarded. No new OnboardRecord is created.
- `urace onboard confirm` on a name-matched Product with a diverged Config digest creates a refreshed OnboardRecord and supersedes the prior one. This is the canonical refresh path when Config has been updated.

## Re-onboard Contract

A re-onboard (same `product_name`, new Config digest) MUST:
1. Re-evaluate all OnboardGate steps against the updated Config.
2. If all BLOCKING gates pass and the operator confirms, create a new OnboardRecord with the updated `config_digest`.
3. Retain the prior record with `superseded_at = now()`.
4. Emit Evidence of kind `onboard-refreshed` with prior and new record IDs.

A re-onboard MUST NOT reset Objectives, Capabilities, Evidence, or any accumulated State. It only refreshes the Config integrity snapshot and the authorization record.

## Behavioral Contracts

- Absence of a matching OnboardRecord at cycle entry MUST set `lifecycle_state = ONBOARDING` and halt autonomous execution. This is non-negotiable.
- The `onboard-confirmation-pending` BLOCKING gap MUST be clearable only by `urace onboard confirm` (OperatorGateProtocol, §62l). Autonomous clearance is prohibited.
- The ONBOARD_COMPLETE Checkpoint MUST be the first Checkpoint written for a new Product. Checkpoints written before ONBOARD_COMPLETE exist only if the onboard was interrupted and resumed — they are diagnostic artifacts, not authorization anchors.
- The `onboard-record-config-diverged` WARNING MUST NOT block autonomous cycles. It is informational. The operator may choose to tolerate Config drift (e.g., minor tuning changes) without re-onboarding.

**Implements:** OnboardGate Mechanism (§62c), OperatorGateProtocol (§62l).
**Uses:** OnboardRecord (§62b), CheckpointRecord (§62b), Evidence (§62b).
**Referenced from:** §62b OnboardRecord, §62c OnboardGate Mechanism, §59b maturity progression, §62k `urace onboard`.

---

# 62p. Product Registry

The Product Registry formalizes multi-product management within a single URACE installation. It allows an operator to declare multiple Products, switch between them safely, and maintain isolated State histories per Product — all without a separate URACE installation per Product.

## Purpose

A single URACE installation governs one active Product at a time. The Product Registry extends this with:

1. **Multi-product declaration.** `Config.product_registry` holds a named list of ProductEntry records, each with its own `state_path`, `product_files`, and optional `intent_purpose`.
2. **Safe switching.** `urace product switch` applies ProductSwitchProtocol (§62l) — a four-step atomic protocol that records the switch, updates Config, and triggers re-onboarding for the new product.
3. **State isolation.** Each product's State is stored in its own file (per `ProductEntry.state_path`). Switching products loads a different state file. Prior-product State is never overwritten.
4. **Audit trail.** SwitchRecord (§62b) in State.switch_records provides a durable, non-compactable log of every product switch.

## Active Product Resolution

At runtime, the active product is resolved as follows:

1. If `Config.active_product` is set, it is the active product name.
2. If a matching ProductEntry exists in `Config.product_registry`, its `state_path` is used for all State I/O.
3. If no matching entry exists, `Config.state_path` is used (legacy fallback).
4. If `Config.active_product` is absent, `Config.product` is the active product name, and `Config.state_path` is used.

**Config.active_product and Config.product relationship.** `active_product` takes precedence. When a product switch occurs, `active_product` is updated by `urace product switch`. `Config.product` is left unchanged — it is the installation's default product name, not the currently active product.

## State Isolation Contract

Each ProductEntry MUST declare a unique `state_path`. Two ProductEntry records with the same `state_path` MUST be rejected at register time (`product-registry-duplicate-state-path` WARNING). State I/O for the active product MUST use exactly the resolved `state_path`. A product switch MUST NOT write to the prior product's state file after the switch is committed.

## Registry Lifecycle

- **register:** Adds ProductEntry to Config.product_registry. Does not create the state file (created on `urace init` or first `urace auto` for that product).
- **switch:** Applies PSP; sets Config.active_product; triggers re-onboard.
- **archive:** (future) Sets ProductEntry.status = ARCHIVED; prevents switching to archived products.

**Implements:** ProductSwitchProtocol (§62l).
**Uses:** ProductEntry (§62b), SwitchRecord (§62b), OnboardGate (§62c), OnboardRecord (§62b).
**Referenced from:** §62l ProductSwitchProtocol, §62k `urace product`.

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

**OwnershipMarker citizen schema.** The durable ownership attribution and liveness verification implement **AP32 — Single-Writer Ownership Lock** (§62i). Every lock, lease or ownership claim written to durable state MUST conform to this schema.

```
OwnershipMarker {
  id              REQUIRED  Identifier; prefix "omk-"
  owner_id        REQUIRED  string; identity of the runtime or process that holds this marker
  scope           REQUIRED  string; what the marker claims ownership over
  acquired_at     REQUIRED  string; ISO-8601 timestamp
  heartbeat_at    OPTIONAL  string; ISO-8601 timestamp; last confirmed-live signal
  status          REQUIRED  OwnershipMarkerStatus; default HELD
  cleared_at      OPTIONAL  string; ISO-8601 timestamp; set when status=CLEARED
  cleared_by      OPTIONAL  string; operator Input id or "self" for voluntary release
}
```

**OwnershipMarkerStatus enum.**
```
HELD    — marker is active; owner is presumed live
STALE   — liveness cannot be confirmed; blocked pending operator clearance
CLEARED — marker was explicitly cleared through authenticated lifecycle command
```

**ConcurrencyPolicy config field.**
```
Config.concurrency_policy OPTIONAL {
  max_concurrent_runtimes  OPTIONAL  int; default 1
  liveness_timeout_seconds OPTIONAL  int; seconds before an unheartbeated marker is treated as STALE; default 300
  clearance_requires_operator OPTIONAL bool; default true
}
```

**State Document.** `ownership_markers` OPTIONAL list of OwnershipMarker.

---

# 64. Lifecycle States

This section implements **AP26 — Lifecycle State Machine** (§62i).

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
DORMANT (IDLE)
```

`DORMANT` is the canonical lifecycle state string for the condition in which no justified authorized action exists now and no unreconciled externally committed effect is pending, but a viable path back to assessment is retained. The term `IDLE` is a conceptual alias; an implementation MUST use `DORMANT` as the persisted state value. MUST NOT treat them as distinct states with different transition, wakeability, or persistence requirements.

The `ASSESSING` lifecycle state is the evaluation phase in which URACE reviews current Evidence, outstanding Objectives, pending reservations, resource availability, and any unresolved effects discovered at wake or transition, before committing to or continuing authorized work. Entry to `ASSESSING` MUST occur on wake from `IDLE`, on successful exit from `REPAIRING`, at resumption from `PAUSED`, and at any state transition where independent evaluation is required before active execution may begin. The inspection surface MUST expose without an Executor call: the identity of Objectives currently under assessment, the Evidence dimensions being evaluated, and any unresolved effects or pending reservations discovered during assessment. `ASSESSING` is distinct from `ACTIVE`, which executes work under a positively identified justified Objective without requiring a fresh assessment cycle first; and from `IDLE`, which holds no justified work and no active evaluation. `ASSESSING` exits to `ACTIVE` when a justified authorized action is identified; to `IDLE` when no justified authorized action exists; or to `BLOCKED` when an unreconciled externally committed effect is discovered. An implementation MUST NOT skip `ASSESSING` after `REPAIRING` exits and transition directly to `ACTIVE`; the post-repair assessment cycle is the mechanism by which restored Product integrity is independently confirmed before new work begins.

`WAITING_FOR_AUTHORITATIVE_DECISION` exists only where a decision was actually retained.

It MUST NOT become the normal operating mode.

The `BLOCKED` lifecycle state MUST be used when an Operation has reached a commit boundary and produced or attempted to produce an externally committed effect whose outcome remains uncertain, and where proceeding without resolving that uncertainty would risk duplicating a consequential effect, corrupting accepted state, or misattributing causal responsibility. Entering `BLOCKED` MUST record: the identity of the unresolved Operation or effect, the nature and source of the uncertainty, and the earliest qualifying condition or authorized Operation that would allow reconciliation to proceed. An implementation MUST NOT automatically retry a `BLOCKED` effect without a reconciling resolution, MUST NOT escalate `BLOCKED` to self-repair or self-evolution, and MUST NOT allow `BLOCKED` to become a permanent silent state without a durable follow-up condition. The inspection surface MUST expose `BLOCKED` status, the identified effect record and the reconciliation path without requiring an Executor call.

The `RECONCILING` lifecycle state is entered when URACE has positively established that the qualifying reconciliation condition for a previously `BLOCKED` uncertain externally committed effect is met, and is actively executing the reconciliation queries, probes or transaction-reference lookups required to establish a definitive disposition for that effect. Entry to `RECONCILING` MUST require positive establishment of the qualifying condition through an attributable signal; elapsed time, timeout or inferred resolution MUST NOT substitute for a qualifying-condition signal. `RECONCILING` is distinct from `BLOCKED`, which is held when uncertainty exists but the qualifying condition for reconciliation has not yet been met; `RECONCILING` is the active in-progress counterpart that begins only when that condition is positively established. While in `RECONCILING`, the lifecycle MUST NOT dispatch new Operations whose execution depends on the uncertain effect's outcome; such Operations MUST remain in pending-eligibility state until a definitive disposition is established. The inspection surface MUST expose without an Executor call: the identity of the Operation whose externally committed effect is being reconciled, the reconciliation method and probe or query type in use, and the latest observed reconciliation step with its timestamp. If reconciliation attempts consistently fail to return a definitive disposition across a declared attempt ceiling, URACE MUST surface a named reconciliation-stalled condition and MUST NOT remain silently in `RECONCILING` without a bounded resolution path. `RECONCILING` exits based solely on the reconciliation result: to an appropriate active or assessment state when a definitive disposition is established, or to `BLOCKED` at a new qualifying-condition prerequisite when the declared attempt ceiling is reached without a disposition.

The `REPAIRING` lifecycle state is entered when URACE has detected a Product integrity failure through an attributable check result — an acceptance validation failure, a self-consistency check, a failed activation health check, or an equivalent attributable integrity signal — and is actively executing the bounded repair sequence required to restore the Product to its last known good accepted state. Entry MUST be triggered by a durable integrity-failure record identifying the check that failed and its observed criterion; autonomous inference of integrity failure without an attributable check result MUST NOT constitute valid entry. `REPAIRING` is distinct from `ACTIVE`, which represents ordinary Product evolution under authorized Intent initiated by justified Objective work rather than a detected integrity failure; from `RECONCILING`, which handles uncertain external effect disposition rather than Product artifact integrity; and from `BLOCKED`, which holds when a committed external effect cannot yet be reconciled. The inspection surface MUST expose without an Executor call: the triggering integrity-failure check identifier and its failed criterion, the Product checkpoint being used as the repair baseline, and the current bounded repair step and its completion condition. A repair sequence MUST have a declared attempt ceiling; if the ceiling is reached without successful restoration, URACE MUST surface a named repair-exhausted condition, MUST NOT continue repair attempts autonomously, and MUST retain durable lifecycle state intact pending operator review. On successful completion, `REPAIRING` exits to `ASSESSING` for an independent integrity-confirmation cycle before any return to `ACTIVE`; a direct transition from `REPAIRING` to `ACTIVE` without an intervening `ASSESSING` confirmation cycle MUST NOT occur.

**Stagnation entry trigger.** `REPAIRING` MAY also be entered when `ExecutorState.progress_stagnant_cycles` reaches the configured `stagnation_threshold` without an integrity-failure check result, provided the stagnation is recorded as a durable `progress-stagnation` integrity signal identifying the cycle count and the last observed `progress_vector` value. Stagnation-triggered REPAIRING MUST be distinguished from validation-failure-triggered REPAIRING in the inspection output. This extends the existing valid entry condition ("an equivalent attributable integrity signal") rather than replacing it.

**Tier escalation before exhaustion.** Before surfacing repair-exhausted, a `REPAIRING` sequence MUST attempt technique escalation through the TechniqueApplicabilityGate tiers in order: T1 (Gap Detection), T2 (Fixpoint Convergence), T3 (Meta-Pattern Selection). Each tier constitutes one attempt boundary. The attempt ceiling MUST be evaluated per-tier, not across all tiers combined: exhausting one tier escalates to the next rather than triggering the repair-exhausted condition. Only when T3 is exhausted without successful restoration MUST URACE surface repair-exhausted. An implementation that triggers repair-exhausted before attempting all available tiers violates this section.

**Auto mode repair-exhausted clause.** When repair-exhausted is reached and the active execution mode is `auto`: URACE MUST emit a `RecoveryManifest` to `ExecutorState.recovery_manifest` with `emission_cause: repair-exhausted`, MUST perform a graceful stop per the graceful stop protocol (preserving all durable state intact per §6276), and MUST NOT enter `BLOCKED`. The next `urace auto` invocation MUST re-ingest the manifest and resume from `last_safe_state` and `last_safe_commit`. In `supervised` execution mode, repair-exhausted MUST surface as a `repair-exhausted` BLOCKING IntegrityGap and enter `BLOCKED` as previously specified; this clause does not alter supervised-mode behavior.

The `VALIDATING` lifecycle state is entered when an Operation has produced a Product increment that has not yet passed the acceptance validation required to commit it to the accepted Product state. Entry MUST be triggered by a completed increment with a durable record identifying the increment and the acceptance criterion to be applied; the lifecycle MUST NOT enter `VALIDATING` without such a record. The inspection surface MUST expose without an Executor call: the identity of the Product increment under validation, the acceptance validation method in use, and the current validation step and its completion condition. An elapsed-time limit MUST NOT substitute for a positive acceptance validation result; if the validation method is temporarily unavailable, the increment MUST remain in `VALIDATING` pending availability rather than being silently accepted. `VALIDATING` is distinct from `ACTIVE`, which executes authorized work to produce an increment and does not involve an acceptance gate on a completed increment; from `ASSESSING`, which evaluates current conditions before any increment is produced; and from `REPAIRING`, which is entered only after an increment has already failed acceptance validation and the bounded restoration sequence is executing. On successful validation, `VALIDATING` exits to `ASSESSING` for a fresh evaluation cycle; on validation failure, `VALIDATING` exits to `REPAIRING` with a durable integrity-failure record identifying the failed criterion.

The `PAUSED` lifecycle state represents an explicit suspension initiated by an authorized operator command. A `PAUSED` lifecycle MUST retain durable state, Intent, Authority and lifecycle history intact. Unlike `BLOCKED`, it has no unreconciled externally committed effect requiring resolution before resumption; unlike `IDLE`, its suspension was explicit rather than the result of no justified authorized action existing now. URACE MUST NOT enter `PAUSED` autonomously; it MUST require an attributable authorized operator input. While `PAUSED`, URACE MUST preserve all pending scheduled conditions in durable state and MUST process them in due-date order at successive eligible lifecycle boundaries after resumption, before new unscheduled work begins. `urace autonomous` MUST resume a `PAUSED` lifecycle from its preserved durable state without reinitializing Authority, Intent, Evidence or accepted lifecycle history.

The `WAITING_FOR_CAPACITY` lifecycle state is entered when an Executor required for a reserved Operation is currently unavailable due to verifiable capacity exhaustion or provider-side throttling. This state is distinct from an authentication failure or a capability gap, both of which are governed by §43: capacity exhaustion means the Executor is correctly authenticated and capable but cannot accept new work because a provider-imposed ceiling or usage window has been reached. Entry MUST NOT occur solely because provider capacity is intermittently slow; the unavailability MUST be established through an attributable provider signal rather than inferred from latency or timeout alone. The inspection surface MUST expose: the identity of the capacity-unavailable Executor, the identity of the reserved Operation it is blocking, and the earliest qualifying recovery condition sufficient to exit the state. A `WAITING_FOR_CAPACITY` lifecycle MUST retain all task reservations and durable state intact; no reservation MAY be discarded or abandoned while this state is held. `WAITING_FOR_CAPACITY` is distinct from `DORMANT` (`IDLE`), which carries no reserved blocking work and therefore has no pending capacity dependency, and from `BLOCKED`, which holds an unreconciled externally committed effect requiring authorized resolution before progress. See §43 for Executor re-verification requirements on return from a capacity unavailability period and §66 for proportionate availability observation and qualifying wake conditions.

The `WAITING_FOR_CONDITION` lifecycle state is entered when a required precondition for a reserved Operation is not yet satisfied and the unsatisfied precondition is neither Executor capacity exhaustion nor an authoritative retained decision. Representative entry causes include: a dependency artifact not yet produced by a sibling workstream, an external system state not yet observable as met, and a prerequisite check not yet passing. Entry MUST be attributable to an identifiable precondition; a vague or uncharacterized dependency MUST NOT be grounds for entering this state. The awaited condition MUST be recorded as a durable dependency record at the point of entry; this record MUST identify: the awaited condition and the observable criterion that constitutes its satisfaction, the identity of the dependent Operation whose progress is gated on that condition, and the earliest qualifying resolution path sufficient to exit the state. The inspection surface MUST expose all three of these elements without requiring an Executor call. `WAITING_FOR_CONDITION` MUST NOT persist without an observable resolution path: if the awaited condition is determined to be unresolvable, the lifecycle MUST surface it as a named blocking limitation rather than allowing it to remain silently in this state. `WAITING_FOR_CONDITION` is distinct from `WAITING_FOR_CAPACITY`, which is entered when an Executor is correctly authenticated and capable but cannot accept new work due to a provider-imposed capacity ceiling or usage-window limit; from `WAITING_FOR_SCHEDULE`, which is entered when a time-based trigger has not yet become due; and from `WAITING_FOR_AUTHORITATIVE_DECISION`, which is entered only where a decision was actually retained by the authoritative source and whose resolution depends on that retention being resolved.

The `WAITING_FOR_SCHEDULE` lifecycle state is entered when the next eligible lifecycle boundary for a reserved workstream is determined by a time-based trigger whose due time has not yet arrived. Entry MUST be attributable to an identifiable scheduled condition; a `WAITING_FOR_SCHEDULE` state MUST record the identity of the awaited trigger and its due time at entry. The inspection surface MUST expose without an Executor call: the identity of the awaited scheduled trigger, its due time, and the lifecycle scope or Operation whose eligibility depends on that trigger becoming due. `WAITING_FOR_SCHEDULE` exits automatically when the scheduled trigger becomes due; no operator action or manual restart is required to exit the state. While in `WAITING_FOR_SCHEDULE`, durable task reservations and lifecycle state MUST be preserved intact. `WAITING_FOR_SCHEDULE` is distinct from `WAITING_FOR_CONDITION`, which is entered when a required precondition independent of time is not yet satisfied; from `WAITING_FOR_CAPACITY`, which is entered when an Executor is correctly authenticated and capable but cannot accept new work due to a provider-imposed capacity ceiling; and from `WAITING_FOR_AUTHORITATIVE_DECISION`, which is entered only where a decision was actually retained by the authoritative source. URACE MUST NOT discard a separately registered scheduled trigger merely because the lifecycle is already in `WAITING_FOR_SCHEDULE` awaiting a different trigger; independently registered scheduled triggers MUST each be evaluated at their respective due times.

**Lifecycle State Transition Table.** The following table is the canonical authoritative transition graph for AP26 (§62i). A transition not listed here is PROHIBITED; an implementation that enters an unlisted transition MUST surface IntegrityGap(`kind: "lifecycle-boundary-violation"`, severity=BLOCKING).

| From state | Trigger | To state |
|---|---|---|
| DORMANT | Qualifying wake signal / scheduled trigger | ASSESSING |
| ASSESSING | Justified authorized action identified | ACTIVE |
| ASSESSING | No justified authorized action exists | DORMANT |
| ASSESSING | Unreconciled externally committed effect discovered | BLOCKED |
| ACTIVE | Increment produced; acceptance criterion applicable | VALIDATING |
| ACTIVE | Operation commits externally; outcome uncertain | BLOCKED |
| ACTIVE | Operator `/pause` command processed | PAUSED |
| ACTIVE | Required Executor capacity exhausted | WAITING_FOR_CAPACITY |
| ACTIVE | Required precondition not yet satisfied | WAITING_FOR_CONDITION |
| ACTIVE | Time-based trigger not yet due | WAITING_FOR_SCHEDULE |
| ACTIVE | Retained decision blocks progress | WAITING_FOR_AUTHORITATIVE_DECISION |
| VALIDATING | Increment passes acceptance validation | ASSESSING |
| VALIDATING | Increment fails acceptance validation | REPAIRING |
| VALIDATING | Validation capability temporarily unavailable | VALIDATING (hold) |
| REPAIRING | Repair successful | ASSESSING |
| REPAIRING | Repair ceiling reached (all tiers exhausted) | BLOCKED (supervised) or graceful-stop (auto) |
| BLOCKED | Qualifying reconciliation condition established | RECONCILING |
| BLOCKED | Operator clearance received | ASSESSING |
| RECONCILING | Definitive disposition established | ASSESSING |
| RECONCILING | Attempt ceiling reached without disposition | BLOCKED (new qualifying condition) |
| WAITING_FOR_CAPACITY | Capacity restored and Executor re-verified | ASSESSING |
| WAITING_FOR_CONDITION | Precondition satisfied | ASSESSING |
| WAITING_FOR_SCHEDULE | Scheduled trigger fires | ASSESSING |
| WAITING_FOR_AUTHORITATIVE_DECISION | Decision resolved | ASSESSING |
| PAUSED | `urace resume` or `urace autonomous` command | ASSESSING |

**All waiting states** (WAITING_FOR_CAPACITY, WAITING_FOR_CONDITION, WAITING_FOR_SCHEDULE, WAITING_FOR_AUTHORITATIVE_DECISION) MAY also transition to PAUSED on explicit operator `/pause` command. **PAUSED** retains all task reservations; resumption always re-enters ASSESSING for an independent evaluation cycle.

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

**OperationDependency DAG computation.** The DAG-based minimum blocked-set computation implements **AP30 — Partial Blocking Dependency Graph** (§62i). When `OperationDependency` records (§62b) exist in State, the minimum-scope blocked set for a blocked Operation MUST be computed as the forward-reachable set from that Operation in the `OperationDependency` DAG, filtered by dependency kind:

- `FINISH_TO_START`: the dependent (`to_id`) Operation is blocked at start when the blocking (`from_id`) Operation is blocked. This is the hard-dependency case.
- `START_TO_START`: the dependent Operation is blocked at start only if the blocking Operation's own start is also blocked. If the blocking Operation has started (even if not finished), the dependent may start.
- `FINISH_TO_FINISH`: the dependent Operation's completion is blocked; its start is not blocked. Both Operations may execute in parallel; only the dependent's final acceptance waits.

When `OperationDependency` records are present, this DAG-based computation MUST supersede workstream-heuristic grouping for the scopes covered by those records. The self-cycle invariant on `OperationDependency` (§62b: `from_id ≠ to_id`) prevents infinite traversal. Cycles among multiple nodes MUST be detected and surfaced as an `IntegrityGap(kind="operation-dependency-cycle", severity=BLOCKING)` before traversal proceeds.

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

The viable-mechanism requirement and cost-bounded liveness path implement **AP29 — Dormancy/Wakeability Contract** (§62i).

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

URACE MUST enforce the Capability Envelope Gate (§62c) on every accepted-product-change when a capability_envelope is configured. Exceeding the complexity_ceiling at CAPABLE maturity without a DecisionRecord(kind=CAPABILITY_SCOPE_EXPANSION) violates the not-more-is-better invariant established by AP25 (§62i).

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

**Orchestrated update.** Invoking `urace /update` without a subaction runs the full sequence interactively — download, explain, confirm, apply — as a single guided operation. Each phase result is durable; an interrupted sequence resumes from the last completed phase. The individual subactions (`download`, `explain`, `apply`, `resolve`) remain available for step-by-step control.

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

HARD constraints MUST NOT be overridden under any circumstances — not by Evidence, Priority, Authority delegation, executor recommendation, or market pressure. A hard constraint violation is a blocking integrity gap; URACE MUST halt the dependent action and surface the constraint as a named BLOCKING gap before any effect is committed.

SOFT constraints MAY be overridden by an explicit, attributable DecisionRecord that acknowledges the constraint, documents the justification, and scopes the override to a specific Operation.

Policy governs where applicable:
- prohibited actions
- reserved decisions
- approvals
- budgets
- external interaction
- privacy
- risk
- self-modification
- delegation
- termination

Policy SHOULD constrain autonomy, not replace it. Where policy establishes a boundary while leaving choices open, URACE SHOULD choose autonomously within that boundary.

**Enforcement gate.** This section implements **AP33 — Policy Enforcement Gate** (§62i). The policy gate fires at step 11 of the canonical decision loop (§77) — immediately before consequential commit. Every Operation MUST be checked against all ACTIVE PolicyRecords and HardConstraints whose scope intersects the Operation's scope. A gate that finds a HARD constraint violation MUST block and surface; it MUST NOT defer to a later cycle.

**PolicyRecord citizen schema.**

```
PolicyRecord {
  id              REQUIRED  Identifier; prefix "pol-"
  kind            REQUIRED  PolicyKind
  status          REQUIRED  PolicyStatus; default ACTIVE
  description     REQUIRED  string; human-readable policy statement
  scope           REQUIRED  string; scope path this policy applies to ("*" = all)
  enforcement     REQUIRED  ConstraintEnforcement; HARD or SOFT
  authority_basis REQUIRED  string; which Authority record establishes this policy
  established_at  REQUIRED  string; ISO-8601 timestamp
  suspended_at    OPTIONAL  string; ISO-8601 timestamp; set when status=SUSPENDED
  revoked_at      OPTIONAL  string; ISO-8601 timestamp; set when status=REVOKED
  revocation_reason OPTIONAL string
}
```
Uses canonical: GoverningRecord (id, authority_basis, scope, established_at), TemporalFields (established_at, suspended_at, revoked_at). Used in: State.policy_records.

**HardConstraint citizen schema.**

```
HardConstraint {
  id              REQUIRED  Identifier; prefix "hco-"
  description     REQUIRED  string; what is prohibited
  scope           REQUIRED  string; scope path ("*" = all)
  established_at  REQUIRED  string; ISO-8601 timestamp
  authority_basis REQUIRED  string; which Authority record establishes this constraint
  violation_count OPTIONAL  int; number of blocked attempts; default 0
}
```
Uses canonical: GoverningRecord (id, authority_basis, scope, established_at), TemporalFields (established_at). Used in: State.hard_constraints.

**PolicyKind enum.**
```
PROHIBITION         — action class is forbidden
PERMISSION          — action class is explicitly permitted (narrows defaults)
APPROVAL_REQUIREMENT — action class requires an attributed DecisionRecord before proceeding
BUDGET              — resource expenditure is capped
PRIVACY             — data disclosure or persistence is restricted
RISK                — risk exposure ceiling
SELF_MODIFICATION   — constrains autonomous self-evolution scope
DELEGATION          — constrains who may receive delegated Authority
TERMINATION         — governs when and how lifecycle may terminate
```

**PolicyStatus enum.**
```
ACTIVE      — policy is in force
SUSPENDED   — policy is temporarily inactive; must not be applied; reason preserved
REVOKED     — policy has been permanently removed; preserved for audit
```

**ConstraintEnforcement enum.**
```
HARD  — violation blocks; no override permitted
SOFT  — violation surfaces warning; attributable DecisionRecord may override
```

**State Document fields.**
`policy_records` OPTIONAL list of PolicyRecord
`hard_constraints` OPTIONAL list of HardConstraint

**Bootstrap contract.** If no HardConstraint or PolicyRecord exists at bootstrap, URACE MUST record a WARNING IntegrityGap(kind="no-hard-constraints-declared") to prompt the operator to establish safety boundaries. The absence of declared constraints does not imply no constraints; it implies unverifiable constraints.

---

**Canonical protocol.** Actions that cannot proceed and require an authenticated operator action apply the **OperatorGateProtocol** (§62l). Hard constraint violations, policy APPROVAL_REQUIREMENT gates, and suspended-policy clearances all use this protocol.


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

## Cognitive reset recovery

This section implements **CognitiveResetRecoveryProtocol** (§62l).

A cognitive reset occurs when an Executor loses working context — through replacement, context-window eviction, restart, or any mechanism that discards in-process reasoning — without any change to durable URACE state. A cognitive reset is not a data loss event; it is a context reconstitution event and MUST NOT be treated as a crash or storage interruption requiring Transaction recovery unless a pending_transaction is independently present in the CognitiveResumeContext.

Recovery from a cognitive reset proceeds as follows:

1. The lifecycle controller regenerates a fresh CognitiveResumeContext (§62e) from current durable state.
2. The CRC is verified: `state_digest` MUST match the current state document. A mismatch MUST emit a `cognitive-resume-stale` WARNING IntegrityGap and trigger regeneration before proceeding.
3. The CRC is injected as structured input to the replacement or reinitialized Executor alongside the current state document.
4. The Executor resumes the interrupted cycle from the lifecycle phase recorded in `cycle_phase`.
5. Any `pending_validations` and `blocking_gaps` from the CRC are treated as the current authoritative open-item list.
6. If `pending_transaction` is non-null, the Transaction recovery protocol of §73 applies before new work begins.

An Executor that cannot resume from a CRC injection is not replaceable and violates §75. A lifecycle that requires restating accepted checkpoints or replaying Decision Records solely because an Executor lost context violates this recovery requirement.

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

**Budget partition invariant.** Self-evolution Objectives MUST NOT consume more than 20% of the available `executor_calls` budget in any 24-hour window. If the 20% ceiling would be exceeded, the self-evolution Objective MUST be deferred to the next cycle. This ensures Product Objectives retain priority over runtime improvement.

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

## Executor Proposal Schema

This section implements **AP34 — Self-Evolution Eligibility Gate** (§62i).

When an Executor proposes a self-evolution Objective during discovery, the proposal MUST carry the following fields to enable the self-evolution policy gate:

```
ExecutorProposal {
  self_evolution_necessary        REQUIRED  bool; true when the Executor asserts the proposal
                                            is a necessary runtime or rebootstrap evolution
  necessity_evidence              REQUIRED  string; non-empty justification when
                                            self_evolution_necessary is true; empty otherwise
  lower_impact_route_sufficient   REQUIRED  bool; true when a lower-impact Product route
                                            exists that satisfies the same goal;
                                            NECESSARY_ONLY eligibility requires this to be false
}
```

An implementation MUST evaluate all three fields before treating a self-evolution proposal as eligible under `NECESSARY_ONLY`. A proposal with `self_evolution_necessary: false`, an empty `necessity_evidence`, or `lower_impact_route_sufficient: true` MUST be classified as ineligible for self-evolution and MUST be recorded as a durable `self-evolution-policy-decision` Evidence event with outcome `INELIGIBLE`. These fields are part of the inspectable authority chain for any self-evolution Objective and MUST NOT be omitted from the ExecutorProposal schema.

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

The isolated preparation, crash-consistent activation, and fallback-preservation implement **AP31 — Safe Runtime Activation** (§62i).

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

**Activation failure contract.** If the health confirmation step fails after activation, the runtime MUST immediately execute the rollback path: restore the preserved prior runtime, set `lifecycle_state` back to the pre-activation value, and surface a BLOCKING gap of kind `activation-health-failure`. The rollback itself MUST be treated as a Transaction (AP16) with its own before/after snapshot. If the rollback fails, a second BLOCKING gap of kind `rollback-failure` MUST be surfaced and all autonomous Operations MUST halt until an operator clears both gaps.

**Partial-update reconciliation.** When a self-evolution update is interrupted mid-application (process crash, timeout, resource exhaustion), the runtime MUST on next wake: (1) detect the incomplete Transaction via phase inspection (PREPARED or APPLYING phase → unconditional rollback; APPLIED phase → re-run validation); (2) resolve the Transaction per phase-specific disposition; (3) surface an INFO gap of kind `partial-update-recovered` after successful resolution; (4) surface a BLOCKING gap of kind `partial-update-unrecoverable` if resolution fails.

**State-divergence detection.** Before accepting any self-evolution proposal, the runtime MUST compare the SHA-256 digest of the candidate spec against the digest recorded at the last stable activation. If they differ by more than the proposed delta, a BLOCKING gap of kind `spec-state-divergence` MUST be surfaced. The operator MUST explicitly clear this gap before the evolution proceeds.

**Re-bootstrap failure contract.** Re-bootstrap MUST be attempted at most 3 times before being classified as terminal. Each failed attempt MUST surface an INFO gap of kind `rebootstrap-attempt-failed` with `attempt_number`. After 3 failures a BLOCKING gap of kind `rebootstrap-terminal-failure` MUST be surfaced. All autonomous Operations MUST halt until the operator explicitly clears this gap and resets the re-bootstrap attempt counter to 0.

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
- cryptographic scheme;
- context window management strategy.

An Executor's context window is a runtime resource, not a lifecycle invariant. URACE MUST NOT bake in assumptions about context window size, context management strategy, or the persistence of in-process reasoning across invocations. The CognitiveResumeContext mechanism (§62e) MUST be used to bridge context boundaries so that any compliant Executor can resume from durable state without platform-specific memory management. An Executor that cannot be initialized from a CRC injection plus current durable state is not executor-agnostic within the meaning of this section.

---

# 76. Minimal Implementation

An implementation MUST keep lifecycle state, Authority/Intent resolution, Evidence, discovery, planning, execution, validation, checkpoints, recovery and capability selection distinguishable and replaceable. One component MAY implement several boundaries when their state and effects remain distinguishable; environment-specific interfaces MAY differ while preserving their Operations. It SHOULD use the smallest inspectable structure that satisfies the Product and environment and MUST NOT build heavyweight IAM, RBAC, workflow, Scheduler, event, transaction or market-fit systems merely because URACE defines corresponding semantics.

**Minimum viable behaviors.** A minimal but complete implementation MUST satisfy the following §78 test categories before claiming conformance:

- Destination / Intent: A, B, C, D, E, F, G, H
- Navigation: I, J, K, L, M, N, O, P, Q, R
- Authority: S, T, U, V, W, X, Y, Z, AA, AB, AC, AD, AE, AF
- Evidence: AG, AH, AI, AJ, AK, AL, AM, AN, AO, AP, AQ, AR
- Liveness: BR, BS, BT, BU, BV, BW, BX, BZ, CB, CD
- Anti-Leak: CE, CF, CG, CH, CI, CJ, CK, CL, CM, CQ, CR, CS, CT, CU

An implementation that satisfies all of the above and no more constitutes a minimal conformant implementation. Features beyond this set are optional capability extensions.

**Completeness criteria.** An implementation is complete when:
1. Every required §78 test ID above maps to an implemented mechanism verifiable by inspection or by a passing TestRunRecord(kind=CAPABILITY_GATE).
2. Every normative "MUST" requirement in §77 canonical decision loop steps 1–16 maps to an implemented mechanism.
3. Every citizen schema in §62b with "REQUIRED" fields has a registered validator.
4. Bootstrap produces an attributable report enumerating: implemented mechanisms, unsupported optional capabilities, and any §78 test IDs not yet satisfied with their blocking reason.

**Implementation surface contract.** A minimal implementation MUST NOT claim conformance by satisfying tests through mocks that do not correspond to real mechanisms. The behavioral test for each §78 entry requires that the corresponding mechanism exists in durable code and produces verifiable state changes observable through `urace check` or `urace vitals`.

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
4. qualify meaningful Triggers, run the Staleness Detection Mechanism (§62c) to revalidate materially stale premises, and preserve uncertainty;
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
15. update metrics, learning, decision records, follow-up, wake conditions and CognitiveResumeContext;
16. continue when justified work exists, otherwise enter efficient wakeable dormancy.

A retained destination MUST remain fixed unless the authoritative source changes it. A delegated destination MAY evolve only within its delegated scope and governing Intent. Route failure requires course correction before destination change. Evidence constrains belief and navigation but never creates Authority.

A cognitive reset may occur between any two steps of this loop. The lifecycle MUST resume from the CognitiveResumeContext at the phase recorded in `cycle_phase`, following the cognitive reset recovery protocol in §73.

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

Given an Objective has high Priority under delegated Authority, but a separate higher-priority Objective lies outside delegated scope.
Expect: URACE pursues only the in-scope Objective; Priority does not expand scope.

**T — Authority Is Not Evidence**

Given strong Evidence supports an action not covered by delegated Authority.
Expect: URACE does not take the action; Evidence informs navigation but does not grant Authority.

**U — Capability Is Not Authority**

Given URACE is technically capable of taking an action not covered by delegated Authority.
Expect: capability does not authorize the action; it remains outside scope.

**V — Delegation Bound**

Given Authority delegates Product navigation within purpose X but not beyond it.
Expect: URACE operates within X and surfaces any discovered opportunity outside X for authoritative decision.

**W — Recursive Delegation Bound**

Given URACE receives delegated Authority and could further delegate a subset of it to an Executor.
Expect: URACE may delegate only within the scope it received; it cannot grant more than it holds.

**X — Authority Provenance**

Given a decision was made under Authority A, which is later found to have been granted by an unauthenticated source.
Expect: URACE surfaces the provenance failure, flags affected decisions as provenance-unverified, and halts dependent uncommitted work pending reauthorization.

**Y — Authority Conflict**

Given two Authority records grant overlapping but contradictory instructions.
Expect: URACE applies the conflict resolution rules of §14–§16 and does not silently prefer one over the other; the conflict is surfaced in inspection output.

**Z — Authority Revocation**

Given a previously delegated Authority is revoked.
Expect: URACE immediately stops relying on the revoked Authority for new decisions; accepted decisions already committed are preserved with attributed provenance.

**AA — Revocation Does Not Rewrite History**

Given Authority is revoked after an Operation was already accepted and checkpointed.
Expect: the accepted checkpoint is preserved; revocation applies prospectively only; history is not altered.

**AB — Stable Delegation Does Not Require Reapproval**

Given delegated Authority has not changed and a new cycle begins.
Expect: URACE proceeds under existing delegation without requesting reapproval.

**AC — Reserved Decision Only**

Given a decision falls within a reserved scope while other work lies within delegated scope.
Expect: only the reserved-scope work is blocked; delegated-scope work continues unblocked.

**AD — Partial Blocking**

Given one scope is blocked waiting for an authoritative decision while another scope has justified authorized work.
Expect: the unblocked scope advances autonomously; URACE does not treat a partial block as a full lifecycle halt.

**AE — Broad Delegation Produces Broad Autonomy**

Given the authoritative source delegates broad navigational authority over a Product domain.
Expect: URACE exercises that authority without requesting confirmation for each sub-decision; broad delegation means broad autonomous operation.

**AF — Authority Cannot Self-Expand**

Given URACE identifies an opportunity that would require Authority beyond its current delegation.
Expect: URACE surfaces the opportunity and the missing Authority; it does not manufacture the missing Authority or proceed without it.

## Evidence

**AG — External Evidence First-Class**

Given an external metric or observation contradicts an internal assumption.
Expect: the external Evidence is treated as first-class; internal assumption is flagged for revalidation.

**AH — Evidence Quality**

Given Evidence is present but below minimum credibility threshold (e.g., single-source, unverified claim).
Expect: URACE records its quality level and does not treat low-quality Evidence as equal to high-quality Evidence in navigation decisions.

**AI — Evidence Relevance**

Given Evidence is credible but concerns a scope unrelated to the current Objective.
Expect: URACE records it as available but does not apply it to unrelated navigation decisions.

**AJ — Contradictory Evidence**

Given two credible Evidence records conflict on the same observable fact.
Expect: URACE preserves both, records the conflict, and does not silently discard either; the conflict is surfaced as uncertainty before dependent decisions.

**AK — Executor Claim vs Evidence**

Given an Executor claims an effect occurred but no independent external Evidence confirms it.
Expect: URACE treats the Executor claim as unconfirmed; it does not elevate an executor claim to validated Evidence without independent corroboration or explicit policy.

**AL — External Reality Precedence**

Given lifecycle state records outcome X but external observation shows outcome Y.
Expect: URACE updates its assessment to reflect external reality; internal state is corrected, not defended.

**AM — Weak External Evidence**

Given external Evidence is present but low-confidence (single signal, no corroboration).
Expect: URACE records the Evidence with its confidence level; it may inform but does not determine navigation unless confidence threshold is met.

**AN — Intent Does Not Override Reality**

Given governing Intent implies outcome X but Evidence shows X is not occurring.
Expect: URACE preserves Intent as the destination while updating assessment to reflect reality; Intent does not override observation.

**AO — Reality Does Not Create Authority**

Given Evidence strongly supports taking an action outside delegated Authority.
Expect: Evidence does not create Authorization; the action remains unauthorized regardless of Evidence quality.

**AP — Evidence Changes Route**

Given Evidence shows the current Plan is not producing progress toward the destination.
Expect: URACE autonomously adapts the route within Authority; Evidence is sufficient justification for route change.

**AQ — Evidence Changes Delegated Destination**

Given Evidence shows a delegated subordinate destination is no longer appropriate within governing purpose.
Expect: URACE may autonomously revise the delegated destination within its delegated scope; governing purpose is preserved.

**AR — Evidence Cannot Change Retained Destination**

Given Evidence suggests a different retained destination would be more valuable.
Expect: URACE preserves the retained destination; Evidence may justify surfacing the conflict but cannot authorize destination replacement.

## Trigger / Plan / Scheduler

**AS — Trigger Without Mutation**

Given a Trigger fires but assessment finds no justified authorized action.
Expect: the Trigger is recorded; no lifecycle state mutation occurs; URACE may re-enter dormancy.

**AT — Trigger Mechanism Replacement**

Given the configured trigger observation mechanism is replaced with an equivalent.
Expect: previously registered wake conditions survive; no triggers are silently lost during the replacement.

**AU — Trigger Storm**

Given many Triggers fire in rapid succession representing the same underlying change.
Expect: URACE deduplicates or rate-limits the triggers; it does not re-evaluate redundant identical Triggers separately.

**AV — Unknown Trigger Source**

Given a Trigger arrives from an unrecognized or unauthenticated source.
Expect: URACE does not treat the unknown-source Trigger as authoritative; it may be logged as a candidate observation subject to quality assessment.

**AW — Trigger Persistence**

Given a Trigger fires while the lifecycle is BLOCKED.
Expect: the Trigger is durably queued; it is not lost and is evaluated at the next unblocked lifecycle boundary.

**AX — Trigger Is Not Evidence**

Given a Trigger indicates that a change may have occurred.
Expect: the Trigger prompts reassessment; it does not itself constitute Evidence; assessment must evaluate whether the change is real and relevant.

**AY — Trigger Is Not Authority**

Given a Trigger fires for an action that would require Authority not yet delegated.
Expect: the Trigger prompts assessment; assessment finds the required Authority absent; the action is blocked pending Authority resolution.

**AZ — Plan Persistence**

Given an Executor is replaced mid-Plan.
Expect: the Plan survives; the replacement Executor resumes from the current Plan state rather than creating a new Plan.

**BA — Planner Replacement**

Given the Planner component is replaced.
Expect: previously accepted Plans remain valid; the new Planner does not invalidate accepted work.

**BB — Scheduler Replacement**

Given the Scheduler component is replaced.
Expect: registered scheduled conditions survive; no scheduled wake conditions are lost.

**BC — Schedule Is Not Justification**

Given a Schedule fires for a planned Operation.
Expect: URACE reassesses justification at the schedule boundary; a due schedule does not automatically authorize execution if premises have materially changed.

**BD — Plan Completion Is Not Lifecycle Completion**

Given the current Plan's final step is accepted.
Expect: URACE reassesses whether further justified work exists before entering dormancy; lifecycle continues until no justified authorized action exists.

## Execution Integrity

**BE — Stale Authority Before Commit**

Given Authority basis has been revoked between planning and pre-commit revalidation.
Expect: URACE detects the stale Authority at pre-commit check (step 11 of canonical loop), blocks the commit, and surfaces the revocation as a blocking gap.

**BF — Stale Intent Before Commit**

Given governing Intent has changed between planning and pre-commit revalidation.
Expect: URACE detects the changed Intent at pre-commit check, blocks or re-evaluates the pending Operation, and surfaces the dependency.

**BG — Stale Product State**

Given the Operation was planned against state version S12 but state is now S13 due to an intervening commit.
Expect: URACE detects the state version mismatch, does not overwrite S13 with stale assumptions, and reconciles or replans.

**BH — Concurrent State Update**

Given two runtimes attempt to commit against the same state version simultaneously.
Expect: exactly one commit succeeds; the other detects the version conflict and reconciles rather than silently overwriting.

**BI — Duplicate Operation**

Given an Operation with the same idempotency key is submitted twice.
Expect: the second submission is recognized as a duplicate; its effect is not applied a second time; the first result is returned or preserved.

**BJ — Crash Before Effect**

Given the process crashes after planning and writing effect intent but before the external effect is committed.
Expect: recovery detects the uncommitted effect intent, does not assume the effect occurred, and either retries safely or surfaces the uncertainty.

**BK — Crash After Effect Before Persistence**

Given an external effect is committed but the process crashes before the acceptance record is durably persisted.
Expect: recovery detects the INDETERMINATE state, reconciles against external reality, and durably records the correct disposition without assuming success or failure.

**BL — Indeterminate Effect**

Given an Operation's external effect status cannot be determined from available signals.
Expect: URACE preserves the effect as INDETERMINATE in durable state; it does not assume success, failure, or retry safety without independent reconciliation.

**BM — Executor Says Failed but Effect Occurred**

Given the Executor returns a failure result but external observation shows the effect was applied.
Expect: URACE trusts external observation over executor claim; the effect is recorded as externally confirmed; retry is suppressed.

**BN — Executor Says Success but Effect Missing**

Given the Executor returns success but external observation shows the effect did not occur.
Expect: URACE trusts external observation; the Operation is not accepted as successful; the discrepancy is preserved as Evidence.

**BO — Attempt Is Not Acceptance**

Given an Operation is attempted but validation has not completed.
Expect: URACE does not checkpoint the Operation as accepted; attempt and acceptance are distinct lifecycle phases.

**BP — External Success Is Not Product Acceptance**

Given an external system confirms a change was applied.
Expect: URACE still requires its own validation step; external confirmation is Evidence, not URACE acceptance.

**BQ — Decision Basis Reconstruction**

Given an accepted DecisionRecord must be audited.
Expect: the full basis — Authority, Intent, Evidence, state reference, constraints, assumptions — is reconstructable from durable state without invoking a new Executor or restating any input.

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

## Justification

**AX — Authority Closure Under Evidence**
Given strong Evidence supports an action outside delegated Authority.
Expect: JustificationContext records `has_authority: false, is_justified: false`; action blocked; AuthorityClosureInvariant cited.

**AY — Authority Closure Under Priority**
Given an Objective has maximal Priority but scope is outside delegated Authority.
Expect: Priority does not change `has_authority` evaluation; action blocked.

**AZ — Justification With All Predicates True**
Given all five JustificationContract predicates are satisfied.
Expect: `is_justified: true`; action proceeds; JustificationContext persisted.

## Blocker Lifecycle

**BA — Blocker TRANSIENT Auto-Resolution**
Given a TRANSIENT blocker has not recurred within 600 seconds.
Expect: `resolved_at` set; Evidence of kind `blocker-transient-expired` emitted; lifecycle advances.

**BB — Blocker Auto-Escalation**
Given a blocker with count ≥ 5 and (last_at − at) > 3600 seconds.
Expect: `classification` upgraded to `ESCALATION`; `blocker-escalated` WARNING gap emitted.

**BC — OPERATOR_GATE Blocker Requires OGP**
Given a blocker with `classification: OPERATOR_GATE`.
Expect: runtime MUST NOT auto-resolve; OperatorGateProtocol governs clearance; `govern clear` required.

## Priority Inbox

**BD — CRITICAL Tier Preempts STANDARD**
Given a Tier 0 (CRITICAL) input queued after two Tier 1 inputs at the same boundary.
Expect: Tier 0 input processed first; Tier 1 inputs remain for subsequent processing in FIFO order.

**BE — Pure FIFO Within Tier**
Given three Tier 1 inputs queued in order t1 < t2 < t3.
Expect: consumed in t1, t2, t3 order regardless of payload content.

## Integrity Signals

**BF — REPAIRING Requires IntegritySignal**
Given an implementation attempts to enter REPAIRING without a durable IntegritySignal.
Expect: lifecycle MUST NOT enter REPAIRING; surfaces `lifecycle-boundary-violation` BLOCKING gap.

**BG — SignalClassifier Maps Stagnation**
Given ExecutorState.progress_stagnant_cycles reaches stagnation_threshold.
Expect: IntegritySignal created with `signal_type: STAGNATION, severity: WARNING`; REPAIRING entry evaluated at next boundary.

## Lifecycle Boundaries

**BH — Incomplete Boundary Recovery**
Given a LifecycleBoundary with `closed_at = null` is found at process restart.
Expect: `lifecycle-boundary-violation` BLOCKING gap emitted; AP27 Transaction Recovery Protocol applied before creating new boundaries.

**BI — Boundary Atomicity**
Given a boundary commit fails partway through.
Expect: state is rolled back to pre-boundary condition; no partial mutations persist; runtime enters REPAIRING.

## Assessment Gaps

**BJ — AssessmentGap Deduplication**
Given an AssessmentGap with the same `cycle_id` and `dimension` is produced by two consecutive assessment cycles.
Expect: the runtime updates the existing AssessmentGap record (incrementing `last_at`) and does NOT append a new agap- record; the agap- count for that cycle_id+dimension remains 1.

**BK — AssessmentGap Resolution**
Given an AssessmentGap is resolved (the blocking insufficiency is corrected).
Expect: `resolved_at` is set to an ISO-8601 timestamp; the gap is removed from the active assessment gap list; no agap- record with a null `resolved_at` remains for that cycle_id+dimension.

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

# 80. Spec Structural Audit

URACE MUST maintain a deterministic, executor-agnostic structural analysis of `URACE.md` as first-class Evidence for autonomous objective discovery and spec self-evolution decisions (§38, §74).

## Canonical Concept Vocabulary

The stems below constitute the normative vocabulary of this specification. A stem is the minimum prefix string that uniquely identifies a concept family across all its morphological variants in this document — the most irreducible composition that still discriminates one concept family from all others. Compliant implementations MUST treat each stem as a canonical concept anchor when scanning, auditing or summarising spec content.

| Stem | Concept family |
|------|---------------|
| `justif` | justification, justify, justified, justifiable |
| `evidenc` | evidence, evidential, evidenced |
| `identif` | identify, identification, identifier, identified |
| `reproduc` | reproduce, reproducible, reproduction |
| `veloc` | velocity |
| `condit` | condition, conditional, conditions |
| `confl` | conflict, conflate, conflation |
| `authorit` | authority, authoritative, authorization |
| `delegat` | delegate, delegation, delegated |
| `valida` | validate, validation, validated |
| `observ` | observe, observation, observable |
| `execut` | executor, execution, execute |
| `checkpoin` | checkpoint, checkpointed, checkpointing |
| `recov` | recover, recovery, recoverable |
| `priorit` | priority, prioritize, prioritized |
| `determin` | determine, determination, deterministic |
| `classif` | classify, classification, classified |
| `reconcil` | reconcile, reconciliation, reconciled |
| `citizen` | citizen, citizens, citizenship |
| `schema` | schema, schemas, schema-bearing |
| `scalar` | scalar, scalars |
| `primitiv` | primitive, primitives |
| `bridg` | bridge, bridges, bridging |
| `formul` | formula, formulas, formulaic |
| `calcul` | calculus, calculi, calculation |
| `pattern` | pattern, patterns, meta-pattern |
| `techniqu` | technique, techniques, meta-technique |
| `orchestrat` | orchestrator, orchestration, orchestrated |
| `communic` | communication, communications, intercommunication |
| `contract` | contract, contracts, contracted |
| `method` | method, methods |
| `diagram` | diagram, diagrams |
| `recoveryman` | RecoveryManifest, recovery manifest |
| `progressvect` | ProgressVector, progress vector, progress_vector |
| `executbudg` | ExecutionBudget, execution budget, execution_budget |
| `sourceinput` | source_input, source_input_id, input traceability |
| `exitcode` | exit code, exit codes, return code |
| `inboxstatus` | inbox status, urace inbox status, input status query |
| `derivedmfst` | DerivedSystemManifest, derived system manifest, derivation manifest |
| `patternopt` | PatternAdoptionRecord, pattern adoption, pattern opt-in |
| `standaloneap` | standalone pattern, standalone=true, foundational pattern |
| `derivedep` | PatternExclusionRecord, excluded dep, transitive dep exclusion, dependency resolution |
| `patterncatl` | Pattern Catalog, PatternCatalog, AP0-AP37 catalog, architectural pattern catalog |
| `optinpat` | opt-in patterns, --opt-in-patterns, --opt-in-constructs, opted_in_patterns, opted_in_constructs, per-pattern update selection, per-construct update selection |
| `stalemfst` | stale manifest, derived-manifest-stale, DerivedManifestRef staleness, stale spec_version |
| `specconstruct` | Spec Construction Protocol, SCP, definition-first ordering, revision completeness declaration, single-pass atomic extension, pre-extension gate |
| `communityinbox` | Community Signal Ingestion, CommunityFeed, CommunitySignal, feed adapter, T&C gate, relevance scoring, confidence scoring, community inbox |
| `patchproposal` | PatchProposal, patch proposal, approval mode, AUTO approval, SMART approval, HUMAN approval, proposal queue, proposal expiry |
| `featurebundle` | FeatureBundle, feature bundle, --bundle, bundle resolution, @bundle-name, built-in bundle, operator bundle |
| `assessmentgap` | AssessmentGap schema (§62b) |
| `lifecycleboundary` | LifecycleBoundary schema (§62b) |
| `integritysignal` | IntegritySignal schema (§62b) |
| `justificationcontext` | JustificationContext schema (§62b) |
| `signalclassifier` | SignalClassifier mechanism (§62c) |
| `justificationcontract` | JustificationContract protocol (§62l) |
| `boundarycontract` | BoundaryContract protocol (§62l) |
| `qualityensurance` | QualityEnsuranceProtocol (§62l) |
| `join` | JoinProtocol (§62l) |
| `onboard` | OnboardRecord, OnboardGate, Product Onboard Phase, onboard confirm, onboard status, ONBOARDING lifecycle state, product switch, config_digest, onboard-confirmation-pending |
| `productregistry` | ProductRegistry, ProductEntry, SwitchRecord, product_registry, active_product, product switch, PSP, urace product |

## Audit Content

A spec structural audit MUST produce, for each numbered section of this specification:

- RFC 2119 verb counts (MUST, MUST NOT, SHOULD, SHOULD NOT, MAY, SHALL, SHALL NOT)
- Stem family hit counts and the morphological variant inventory found in that section
- Semantic gap records — spans where a normative rule's meaning cannot be fully resolved without implementation-level judgment

Semantic gap detection MUST cover at minimum:

- **Vague quantifiers**: *reasonable, appropriate, sufficient, adequate, proportionate* — no threshold or criterion supplied
- **Underspecified conditions**: *as needed, where applicable, when appropriate, where possible* — no observable trigger
- **Passive-voice normative rules without an attributed actor**: the party responsible for satisfying the rule is not stated
- **Comparatives without a numeric or defined reference anchor**: *significantly shorter, materially larger* without a baseline
- **Capability assertions without a testable criterion**: *capable of* without a measurable outcome

The audit MUST also produce global RFC 2119 totals across all sections, a per-stem section distribution identifying which sections concentrate each concept family, and a fence-parity check.

The audit MUST be deterministic: given the same spec text, it MUST produce the same structural output with no dependency on execution time, random state, or external resources.

## Scheduling

URACE SHOULD run a spec structural audit before the first executor discovery cycle following any spec version change.

The audit result MUST be stored as an Evidence record of kind `spec-structural-audit` containing at minimum: the spec version audited, the audit timestamp, the section count, the RFC 2119 totals, and a per-section ambiguity classification (`high`, `medium`, `low`, or `n/a`).

The audit state MUST be persisted in durable lifecycle state and MUST be inspectable. The last-audited spec version MUST be compared to the current spec version on each assessment cycle to determine whether a fresh audit is due.

## Discovery Feed

The audit summary — specifically sections classified as high-ambiguity and sections with passive-voice normative rules lacking attributed actors — MUST be included in the context supplied to the autonomous discovery Executor.

When a section's semantic gap density constitutes a material precision gap, URACE SHOULD surface a spec-improvement Objective for that section in the next discovery cycle, subject to applicable Authority and self-evolution policy (§74).

Spec-improvement Objectives derived from audit findings are ordinary spec-evolution Objectives: they require the same justification, prioritization, execution, validation and checkpoint path as any other Objective. The audit result is Evidence; it does not constitute Authority to modify `URACE.md`.

**Gap density metric.** Semantic gap density for a spec section is computed as: `gap_count / normative_statement_count`, where `normative_statement_count` is the count of sentences containing MUST, SHALL, SHOULD, or MAY (RFC 2119). A gap is a concept referenced in the section that lacks a binding normative statement governing its behavior. Sections with `gap_count / normative_statement_count > 0.40` MUST be flagged in the structural audit output as having material precision gaps.

**Materiality threshold.** A precision gap is material when it leaves operator-observable behavior undefined in at least one reachable execution path. Gaps that affect only informational output (e.g., display formatting) are non-material. The audit authority is the spec maintainer (the entity that issues spec revisions). Materiality is determined by the spec maintainer, not by the runtime.

**Remediation contract.** A material precision gap MUST be resolved by: (a) adding normative text to the spec (preferred); or (b) adding a runtime guard that surfaces a WARNING gap of kind `spec-precision-gap-active` when the undefined path is reached. Option (b) is a temporary measure; the spec text remediation MUST follow in the next revision.

---

# 81. Final Invariant

> **URACE persistently drives the Product toward the highest applicable non-delegated authoritative Intent. The authoritative source controls whatever destination-setting Authority it retains and may delegate any subordinate destination or navigation decision it chooses; URACE MUST preserve that retained boundary and MUST NOT invent, broaden or reason around delegation. Within valid delegated Authority, however, URACE owns the journey: it independently observes reality, discovers opportunities and problems, assesses Evidence, identifies uncertainty, chooses Objectives, prioritizes, plans, experiments, selects replaceable executors, executes, learns, corrects course, validates, checkpoints, repairs, recovers, becomes dormant and reactivates without requiring the authoritative source to navigate decisions already delegated. Evidence constrains what URACE may defensibly believe about the conditions of the journey and may justify route changes or authorized destination evolution, but Evidence, Product Value, Priority, urgency, market pressure, executor capability, recommendation and convenience MUST NOT independently change a retained destination or create Authority. When a route fails, URACE changes the route; when a delegated destination should change, URACE may change it when sufficiently justified; when a retained destination appears infeasible, URACE preserves reality and the authoritative boundary rather than silently redefining either. Retained, denied or unresolved decisions block only dependent scope where possible, while independent authorized Product evolution continues. Materially stale consequential decisions are proportionately revalidated without converting Authority into an approval loop; attempts, effects, observations, validation and acceptance remain distinct; uncertain effects remain explicitly indeterminate until reconciled; accepted progress is checkpointed; and persistent autonomous ownership remains live through both active operation and efficient dormancy until an explicit authoritative terminal condition ends it. In short: the authoritative source chooses the destination it wishes to retain; URACE drives the boat.**

---

# 82. Revision Log

This log records every specification revision. Revisions tagged `runtime-only` introduced no new normative spec contract; they are logged here to maintain version continuity and to make the scope of each change auditable. Revisions tagged `spec` added or changed normative content in this document. Revisions tagged `spec+runtime` did both.

Revisions prior to r22 are recorded in the git commit history. This log covers r22 onwards.

**Revision completeness declaration.** Each revision log entry from r60 onward MUST include:

  **New external references:** `<item>` → defined at `<section>` [, ...]

Where `<item>` is the fully-qualified name (e.g. `Config.retention.auto_trigger_bytes`, `EffectType enum`, `scp-forward-reference IGC kind`) and `<section>` is the spec section where the definition appears. This field is required by SCP Gate 2 (§62n).

| Version | Date | Scope | Summary |
|---|---|---|---|
| r72 | 2026-10-17 | spec+runtime | Product Registry. New §62p normative section formalizing multi-product management within a single URACE installation: multi-product declaration (Config.product_registry), safe switching (ProductSwitchProtocol), state isolation (per-product state files), audit trail (SwitchRecord). New §62b citizen schemas: ProductEntry (prefix "prod-", fields: id, name, state_path, product_files, intent_purpose OPTIONAL, registered_at, last_active_at OPTIONAL, status ACTIVE|INACTIVE|ARCHIVED; uniqueness contract: duplicate name → `product-registry-duplicate-name` WARNING) and SwitchRecord (prefix "swrec-", fields: id, from_product, to_product, switched_at, switched_by, reason OPTIONAL; audit contract: non-compactable). New §62l construct: ProductSwitchProtocol (PSP, INTEGRATED, depends: [OnboardGate]): 4-step atomic protocol (validate target → record switch → update active_product → trigger re-onboard); atomicity contract (steps 2+3 must be atomic; rollback on Config write failure). Config Document: `product_registry` OPTIONAL (list[ProductEntry], default []) and `active_product` OPTIONAL (string; overrides Config.product for active product name and routes state_path to matching ProductEntry.state_path). State Document: `switch_records` OPTIONAL field added (list[SwitchRecord], default []). Active Product Resolution algorithm added to §62p: (1) active_product present → use it; (2) matching ProductEntry → use its state_path; (3) no match → Config.state_path fallback; (4) active_product absent → Config.product + Config.state_path. New §62k commands: `urace product list` (SD=True, all registry entries with active marker), `urace product status` (SD=True, active product diagnostic), `urace product switch <name>` (PSP application), `urace product register <name>` (add ProductEntry to registry). 3 new IGC gap kinds: `product-registry-unknown-product` (WARNING), `product-switch-pending-onboard` (INFO), `product-registry-duplicate-name` (WARNING); IGC total 100→103. Schema Catalog: ProductEntry + SwitchRecord added (34→36). Protocol Catalog: PSP added (14→15). §62n ConstructKindRegistry: ProductEntry (INTEGRATED), SwitchRecord (INTEGRATED) added. §81: `productregistry` stem added. Runtime (r72): `save_config()` added to _common.py; `state_path()` updated to dispatch on `active_product` + `product_registry`; `initial_state()` adds `switch_records: []`; `product` command added to cli.py (list/status/switch/register subcommands); `product` added to `_KNOWN_TOP_COMMANDS`; 3 new gap kinds added to primitives.py INTEGRITY_GAP_CATALOG; 8 new behavioral tests (R72ProductRegistryTests). **1000 tests pass.** QE: PASS. JOIN: PASS. **New external references:** `ProductEntry` schema → §62b (this revision); `SwitchRecord` schema → §62b (this revision); `ProductSwitchProtocol` (PSP) Protocol → §62l (this revision); `Config.product_registry` field → §62e Config Document (this revision); `Config.active_product` field → §62e Config Document (this revision); `State.switch_records` field → §62e State Document (this revision); `§62p` section → §62p Product Registry (this revision); `urace product list` command → §62k (this revision); `urace product status` command → §62k (this revision); `urace product switch` command → §62k (this revision); `urace product register` command → §62k (this revision); `product-registry-unknown-product` IGC kind → §62l (this revision); `product-switch-pending-onboard` IGC kind → §62l (this revision); `product-registry-duplicate-name` IGC kind → §62l (this revision); `productregistry` stem → §81 (this revision) |
| r71 | 2026-10-17 | spec+runtime | Product Onboard Phase. New lifecycle state `ONBOARDING` added as the pre-cycle entry gate — precedes BOOTSTRAPPING in the maturity progression. New §62b citizen schema: OnboardRecord (prefix "onb-", fields: id, created_at, product_name, confirmed_by, confirmed_at, config_digest, gates_passed, capability_envelope_waived OPTIONAL, notes OPTIONAL, superseded_at OPTIONAL); staleness contract (config_digest divergence → WARNING, non-blocking); uniqueness contract (at most one active per product_name; supersede on re-confirm). New §62c mechanism: OnboardGate (7-step algorithm: config-completeness, product-files-readable, intent-anchored, capability-envelope-declared, self-evolution-policy-recorded, operator-confirmation, on-confirm record+checkpoint+clear-gaps+set-DORMANT); SD=True; no executor credits consumed. New §62o normative section: Product Onboard Phase — purpose (authorization anchor, config integrity snapshot, product switchability gate), lifecycle position, entry trigger (no OnboardRecord for Config.product), gate step table, Product Switchability contract (product-agnostic; prior state retained with product_name isolation), idempotency and refresh contracts, re-onboard contract. New §62k commands: `urace onboard status` (idempotent gate evaluation) and `urace onboard confirm` (operator confirmation, creates OnboardRecord, writes ONBOARD_COMPLETE Checkpoint, clears onboard-* gaps, sets lifecycle_state=DORMANT). 6 new IGC gap kinds: `onboard-config-incomplete` (BLOCKING), `onboard-no-readable-product-files` (BLOCKING), `onboard-intent-unanchored` (BLOCKING), `onboard-capability-envelope-missing` (WARNING), `onboard-confirmation-pending` (BLOCKING), `onboard-record-config-diverged` (WARNING); IGC total 94→100. State Document: `onboard_records` OPTIONAL field added (list[OnboardRecord], default []). Schema Catalog: OnboardRecord added (33→34). Runtime (r71): 5 autonomous capability gaps closed — (P1a) wake stale→expired escalation with liveness_failures+stale_since tracking; (P1b) discovery proportionality IntegrityGaps for DEFERRED_PROPORTIONALITY and DISCOVERY_YIELD_EXHAUSTED; (P2a) CAPABILITY_DEFINING objective gate at CAPABLE/OPTIMIZED maturity (requires DecisionRecord with AUTHORITY_GRANT kind); (P2b) BOOTSTRAPPING→CAPABLE transition gate (requires passing CAPABILITY_GATE or ACCEPTANCE TestRunRecord); (P3) CSI/PPP_M full wiring (Config.community_inbox.feeds drives CSI; PPP_M with AUTO/SMART/HUMAN routing; `inbox apply`/`inbox reject` CLI commands). State Document: `community_feeds`, `community_signals`, `patch_proposals` added to initial_state(). **992 tests pass** (existing baseline unchanged; onboard runtime tests and gap tests pending runtime implementation). JOIN pass: all new constructs wired (OnboardRecord Used-in, OnboardGate Referenced-from, §62o References, §62k urace-onboard cross-refs complete). QE pass: no schema field order violations; all new IGC kinds in catalog table; count updated; new external references listed. **New external references:** `ONBOARDING` lifecycle state → §62e lifecycle_state enum (this revision); `OnboardRecord` schema → §62b (this revision); `OnboardGate` Mechanism → §62c (this revision); `§62o` section → §62o Product Onboard Phase (this revision); `urace onboard status` command → §62k (this revision); `urace onboard confirm` command → §62k (this revision); `onboard-config-incomplete` IGC kind → §62l (this revision); `onboard-no-readable-product-files` IGC kind → §62l (this revision); `onboard-intent-unanchored` IGC kind → §62l (this revision); `onboard-capability-envelope-missing` IGC kind → §62l (this revision); `onboard-confirmation-pending` IGC kind → §62l (this revision); `onboard-record-config-diverged` IGC kind → §62l (this revision); `State.onboard_records` field → §62e State Document (this revision) |
| r70 | 2026-10-16 | spec+runtime | Runtime alignment pass (r65–r69 gap closure). State Document bootstrap: initialized `assessment_gaps`, `lifecycle_boundaries`, `integrity_signals` as empty lists in `initial_state()` — three r65 schemas whose State fields were declared in r67 but not wired into bootstrap. Implemented `record_assessment_gap()` (deduplication contract: same cycle_id+dimension updates last_at, not append) and `resolve_assessment_gap()` (sets resolved_at, removes from active list) in cli.py. Added `justification_context_id` OPTIONAL parameter to `create_decision_record()` in decision_record.py. Added 8 behavioral tests: BJ (AssessmentGap deduplication), BK (AssessmentGap resolution — two assertions each), 3 State Document initialization assertions, 1 DecisionRecord.justification_context_id acceptance test. Spec version header bumped r65→r70. **978 tests pass.** QE: PASS. JOIN: PASS. **New external references:** none (all constructs previously declared) |
| r69 | 2026-10-16 | spec | Add JoinProtocol (JOIN) as named §62l construct. JOIN formalizes the post-change wiring audit as a 6-step protocol: enumerate new/modified constructs → "Used in:" resolution → "Referenced from:" resolution → "Citizens using:" completeness → universal scope classification → emit finding list (PASS or unresolved refs). §62l count updated sixteen→seventeen; enforcement contract self-enforcing list updated to include JOIN (seven→eight). §62m Protocol Catalog: JOIN added (13→14 entries). §62n ConstructKindRegistry: JOIN added (FOUNDATIONAL, standalone: true). §81: `join` stem added. QE: PASS. JOIN: PASS. **New external references:** `JOIN` Protocol → §62l (this revision); `JoinProtocol` construct → §62l (this revision); `join` stem → §81 (this revision) |
| r68 | 2026-10-16 | spec | Add QualityEnsuranceProtocol (QE) as named §62l construct. QE formalizes the post-change degradation audit as a 6-step protocol: enumerate changed constructs → schema field ordering → cross-reference resolution → contract consistency → count/catalog drift → emit finding list (PASS or degradations). §62l count updated fifteen→sixteen; enforcement contract self-enforcing list updated to include QE (six→seven). §62m Protocol Catalog: QE added (12→13 entries). §62n ConstructKindRegistry: QE added (FOUNDATIONAL, standalone: true). §81: `qualityensurance` stem added. QE: PASS (no degradations introduced by this revision). **New external references:** `QE` Protocol → §62l (this revision); `QualityEnsuranceProtocol` construct → §62l (this revision); `qualityensurance` stem → §81 (this revision) |
| r67 | 2026-10-16 | spec | JOIN + NSS + SCP pass (r65/r66 changes) + DEGRADATION fix. State Document wired: added `assessment_gaps` (OPTIONAL list[AssessmentGap]), `lifecycle_boundaries` (OPTIONAL list[LifecycleBoundary], max 50), `integrity_signals` (OPTIONAL list[IntegritySignal]) — three r65 schemas whose "Used in: State.X" annotations referenced undeclared State Document fields. DecisionRecord wired: added `justification_context_id` (OPTIONAL string; jctx- reference) — r65 JustificationContext schema claimed this field but it was absent from DecisionRecord. PMM wired: added `**Referenced from:**` annotation to PatternMechanismMapping (§62l) pointing to enforcement clause (7), §62j derive, and §62m Protocol Catalog. DEGRADATION fix: `justification_context_id` (OPTIONAL) was placed before `decided_at` (REQUIRED) in DecisionRecord schema, violating OPTIONAL-after-REQUIRED ordering; field moved to after `decided_at`. NSS: all four stems (assessmentgap, lifecycleboundary, integritysignal, justificationcontext) confirmed present in §81; no new stems required. SCP Gate 1: all fields declared after their respective schema definitions (§62b precedes §62e State Document; §62b precedes §62l PMM). **New external references:** `State.assessment_gaps` field → §62e State Document (this revision); `State.lifecycle_boundaries` field → §62e State Document (this revision); `State.integrity_signals` field → §62e State Document (this revision); `DecisionRecord.justification_context_id` field → §62b DecisionRecord (this revision); `PatternMechanismMapping` Referenced-from annotation → §62l (this revision) |
| r66 | 2026-10-16 | spec | Gap closure pass (4 confirmed gaps): (1) PMM added to Protocol Catalog (§62m, 11→12 entries); (2) two new mandatory behavioral tests added (BJ — AssessmentGap Deduplication, BK — AssessmentGap Resolution) covering the MUST-level deduplication and resolved_at contracts on the agap- schema (§62b); (3) §62l enforcement contract prose corrected: "all fifteen" replaced with explicit count of nine mandated clauses plus six self-enforcing constructs named (EUP, OGP, CRRP, WRV, CRC_C, CEP); clause (4) corrected from "TemporalFields conformance" (a §62b primitive) to "GoverningRecord conformance citizens that also use TemporalFields"; supplemental JC+BC enforcement clauses promoted to main numbered list as (8) and (9); (4) `kind: Protocol` metadata note added to §62l enforcement contract explaining that `kind: Protocol` is the generic §62l-section metadata value and the catalog column provides the authoritative semantic classification, resolving the apparent contradiction between five Contract Catalog entries (GRC, IGC, ISC, ACI, RVS) and their construct metadata. **New external references:** `BJ` behavioral test → §78 (this revision); `BK` behavioral test → §78 (this revision); `PMM` Protocol Catalog entry → §62m Protocol Catalog (this revision) |
| r65 | 2026-10-16 | spec+runtime | Comprehensive gap closure: sections 1–60 operational strengthening, §62k ease-of-use expansion, new citizen schemas, new protocols and mechanism, lifecycle FSM table, new mandatory behavioral tests. Spec: §3 first-class/derived formal definition; §27 Evidence Integrity operational test condition; §28 minimum Evidence assessment contract; §30 Evidence–prediction conflict definition; §39 priority formula citation; §41 Plan acceptance criteria; §56 deceleration threshold formula (0.8× baseline). Blocker schema extended with `classification`, `evidence_id`, `auto_clear_on`, `escalation_due` fields and auto-escalation/auto-resolution contracts. New §62b citizen schemas: AssessmentGap (agap-), LifecycleBoundary (lcb-), IntegritySignal (isig-), JustificationContext (jctx-). New §62c mechanism: SignalClassifier (SCF). AP14 extended with priority_tier (Tier 0 CRITICAL / Tier 1 STANDARD / Tier 2 OPPORTUNISTIC) and backward-compatible tier-ordering contract. §62k major expansion: --dry-run extended to update/derive/auto/goal/metric/constraint; --since/--until/--limit/--offset/--fail-on added; inspect/list subcommands documented (goal list, evidence list, blocker list/resolve, decision list/inspect, integrity-signal list); Defaults Table added; inbox/govern/autonomous commands documented. New §62l protocols: JustificationContract (JC, FOUNDATIONAL) and BoundaryContract (BC, FOUNDATIONAL); §62l count updated to fifteen. 6 new IGC gap kinds (blocker-escalated, integrity-signal-unclassified, lifecycle-boundary-violation, justification-context-incomplete, inbox-priority-tier-violation, checkpoint-write-timeout); IGC total 88→94. §62m catalogs: Mechanism +1 (SCF→8), Schema +4 (→33), Protocol +2 (→11); IGC count in Contract Catalog updated to 94 kinds. §64 canonical FSM transition table added (26 transitions). §78 15 new mandatory behavioral test categories (AX–BI). §81 7 new stems. Runtime: Blocker fields extended in State Document; record_blocker() accepts classification/evidence_id/auto_clear_on; auto-escalation at count≥5 and age>3600s; TRANSIENT auto-resolution at 600s; AP14 priority_tier processing order in consume_inputs(); new behavioral tests for authority closure, blocker lifecycle, priority inbox, integrity signals, boundary recovery. **New external references:** `first-class` definition → §3 Core Lifecycle Semantics (this revision); `IntegritySignal` schema → §62b (this revision); `LifecycleBoundary` schema → §62b (this revision); `AssessmentGap` schema → §62b (this revision); `JustificationContext` schema → §62b (this revision); `SignalClassifier` mechanism → §62c (this revision); `priority_tier` field → §62i AP14 IPC Input Schema Catalog (this revision); `JustificationContract` protocol → §62l (this revision); `BoundaryContract` protocol → §62l (this revision); `blocker-escalated` IGC kind → §62l (this revision); `integrity-signal-unclassified` IGC kind → §62l (this revision); `lifecycle-boundary-violation` IGC kind → §62l (this revision); `justification-context-incomplete` IGC kind → §62l (this revision); `inbox-priority-tier-violation` IGC kind → §62l (this revision); `checkpoint-write-timeout` IGC kind → §62l (this revision); `--since` option → §62k (this revision); `--until` option → §62k (this revision); `--limit` option → §62k (this revision); `--offset` option → §62k (this revision); `--fail-on` option → §62k (this revision); `goal list` subcommand → §62k (this revision); `evidence list` subcommand → §62k (this revision); `blocker list` subcommand → §62k (this revision); `blocker resolve` subcommand → §62k (this revision); `decision list` subcommand → §62k (this revision); `decision inspect` subcommand → §62k (this revision); `integrity-signal list` subcommand → §62k (this revision); `Blocker.classification` field → §62b Blocker schema (this revision); `Blocker.evidence_id` field → §62b Blocker schema (this revision); `Blocker.auto_clear_on` field → §62b Blocker schema (this revision); `Blocker.escalation_due` field → §62b Blocker schema (this revision); `supplemental-enforcement-jc-bc` clause → §62l BoundaryContract (this revision, SCP Gate 1 compliance correction) |
| r64 | 2026-10-16 | spec+runtime | NSS + SCP compliance pass + update/derive gap closure. Fixed SCP Protocol Construct metadata line to NSS template-compliant format (`standalone: false · depends: [NSS, IGC]`); removed erroneous AP-style `Derivation metadata` line from SCP section. Fixed DAI Protocol Construct metadata line to NSS template-compliant format (`standalone: true · depends: []`). Added required `**New external references:** (predates SCP — not declared)` annotations to r58 and r59 revision log entries (SCP §9290 retroactive-applicability SHOULD clause). Runtime: wired `@bundle-name` resolution for `--opt-in-constructs` in `urace update` (all subcommands and orchestrated path); unknown bundle names produce error with `urace derive --list-bundles` hint. Extended `_check_stale_derived_manifests()` to also check `state.feature_bundle_refs` and surface `derived-construct-set-stale` warnings with `bundle_name` field during `update download` and `update apply` (§62j FeatureBundle stale-detection contract). Added `--bundle` + `--refresh` conflict guard in `urace derive`: when both flags are used, `--bundle` is ignored and a warning is printed (§62j §8790). **New external references:** none |
| r63 | 2026-10-16 | spec | r61/r62 gap closure pass. Added `adapter_timeout_seconds` (default 30s), `adapter_retry_count` (default 3), `polling_interval_seconds` (default 300s) fields to CommunityFeed schema. Added `executor_credit_priority` field to Config.community_inbox (INBOX_HIGH|INBOX_NORMAL|INBOX_LOW). Added 2 IGC gap kinds: `community-inbox-evolution-blocked` (WARNING), `feature-bundle-unknown-construct` (WARNING); IGC total 86→88. Extended CSI mechanism with: timeout/retry contract, polling cadence contract, lifecycle state gate, executor credit contract (with bounded delta formula for confidence scoring), filtered signal lifecycle (re-evaluation on intent change), T&C gap auto_clearable contract. Extended PPP_M with: queue overflow eviction strategy (CONFIDENCE_INSUFFICIENT first, then PENDING refused), self-evolution DISABLED path (proposal held PENDING, `urace /inbox apply --override-evolution-policy`), HUMAN mode approval commands (`urace /inbox list|apply|reject`). Extended DAI with: cycle detection response per trigger type, unknown construct detection per FeatureBundle entry, self-reference detection response. Extended §62j derive with: FeatureBundle stale update path, bundle-derive precedence rules, FeatureBundle dependency resolution algorithm. Extended WRM signal taxonomy: added COMMUNITY_INBOX (5th signal kind) for high/medium signal arrival and HUMAN-mode reminder wakes. **New external references:** `CommunityFeed.adapter_timeout_seconds` → §62b CommunityFeed schema (this revision); `CommunityFeed.adapter_retry_count` → §62b CommunityFeed schema (this revision); `CommunityFeed.polling_interval_seconds` → §62b CommunityFeed schema (this revision); `Config.community_inbox.executor_credit_priority` → §62e Config community_inbox subschema (this revision); `community-inbox-evolution-blocked` IGC kind → §62l (this revision); `feature-bundle-unknown-construct` IGC kind → §62l (this revision); `COMMUNITY_INBOX` WakeRegistration signal kind → §62c WRM signal taxonomy (this revision) |
| r62 | 2026-10-16 | spec | Construct cross-referencing, DAG acyclicity invariant, FeatureBundle. Added optional `realizes:` field to AP metadata template in §62n to make AP→implementation links machine-readable; AP38 is first use (`realizes: [CSI, PPP_M, PPP]`). Added Construct Dependency Acyclicity Invariant (DAI) as a FOUNDATIONAL Protocol in §62n: Rule 1 — transitive dependency DAG must be acyclic (`construct-dependency-cycle` BLOCKING); Rule 2 — self-reference prohibited (`construct-self-reference` BLOCKING); Rule 3 — FeatureBundle construct_ids must resolve to DAG. Added 2 IGC gap kinds: `construct-dependency-cycle` (BLOCKING), `construct-self-reference` (BLOCKING); IGC total 84→86. Added FeatureBundle (prefix fbundle-) and FeatureBundleRef (prefix fbref-) citizen schemas to §62b with State.feature_bundle_refs field. Added `--bundle <name>` and `--list-bundles` flags to `urace derive`; added `@bundle-name` syntax to `--opt-in-constructs`. Defined built-in bundle `community-inbox` (AP38 + 8 constructs). Added DAI to Protocol Catalog (8→9), ConstructKindRegistry, FeatureBundle/FeatureBundleRef to Schema Catalog (26→28). Added stem `featurebundle` to §81. **New external references:** `realizes:` AP metadata field → defined at §62n Mandatory Construct Metadata (this revision); `DAI` Protocol → defined at §62n DAI section (this revision); `construct-dependency-cycle` IGC kind → defined at §62l (this revision); `construct-self-reference` IGC kind → defined at §62l (this revision); `FeatureBundle` schema → defined at §62b (this revision); `FeatureBundleRef` schema → defined at §62b (this revision); `State.feature_bundle_refs` field → defined at §62e State Document (this revision); `--bundle` flag → defined at §62j derive contract (this revision); `--list-bundles` flag → defined at §62j derive contract (this revision); `@bundle-name` syntax → defined at §62j update contract (this revision); `community-inbox` built-in bundle → defined at §62j Built-in spec-defined FeatureBundles table (this revision); `featurebundle` stem → defined at §81 (this revision) |
| r61 | 2026-10-16 | spec | Community Signal Ingestion. Introduced AP38 (Community Signal Ingestion, INTEGRATED) in §62i with feed-adapter agnosticism, T&C gate, two-dimensional signal quality scoring (relevance + confidence), and configurable approval pipeline (AUTO/SMART/HUMAN; default SMART). Added mechanisms CSI (Community Signal Ingestion Mechanism) and PPP_M (Patch Proposal Pipeline Mechanism) to §62c. Added Protocol PPP (PatchProposalProtocol, 7→8) to §62m Protocol Catalog. Added citizen schemas CommunityFeed (prefix cfeed-), CommunitySignal (prefix csig-), PatchProposal (prefix pprop-) plus enums ApprovalMode, FeedAdapterKind, SignalQuality, ProposalStatus to §62b. Added Config.community_inbox subschema to §62e. Added 5 new IGC gap kinds: `community-feed-terms-not-accepted` (BLOCKING), `community-feed-adapter-unavailable` (WARNING), `patch-proposal-confidence-below-floor` (INFO), `patch-proposal-queue-overflow` (WARNING), `community-signal-relevance-below-floor` (INFO); IGC total 79→84. Added AP38 to ConstructKindRegistry, PMM table, and tier table (INTEGRATED). Added CSI and PPP_M to ConstructKindRegistry Mechanisms. Added CommunityFeed, CommunitySignal, PatchProposal to Schema Catalog (23→26). Added stems `communityinbox` and `patchproposal` to §81. **New external references:** `AP38` AP → defined at §62i AP38 (this revision); `CommunityFeed` schema → defined at §62b (this revision); `CommunitySignal` schema → defined at §62b (this revision); `PatchProposal` schema → defined at §62b (this revision); `ApprovalMode` enum → defined at §62b (this revision); `FeedAdapterKind` enum → defined at §62b (this revision); `SignalQuality` enum → defined at §62b (this revision); `ProposalStatus` enum → defined at §62b (this revision); `Config.community_inbox` subschema → defined at §62e (this revision); `community-feed-terms-not-accepted` IGC kind → defined at §62l (this revision); `community-feed-adapter-unavailable` IGC kind → defined at §62l (this revision); `patch-proposal-confidence-below-floor` IGC kind → defined at §62l (this revision); `patch-proposal-queue-overflow` IGC kind → defined at §62l (this revision); `community-signal-relevance-below-floor` IGC kind → defined at §62l (this revision); `CSI` Mechanism → defined at §62c (this revision); `PPP_M` Mechanism → defined at §62c (this revision); `PPP` Protocol → defined at §62m Protocol Catalog (this revision); `communityinbox` stem → defined at §81 (this revision); `patchproposal` stem → defined at §81 (this revision) |
| r60 | 2026-10-16 | spec | Spec Construction Protocol. Introduced SCP as a FOUNDATIONAL Protocol in §62n: three-gate pre-extension enforcement (Gate 1: definition-first ordering, Gate 2: revision completeness declaration, Gate 3: single-pass atomic extension). Added 3 IGC gap kinds: `scp-forward-reference` (BLOCKING), `scp-incomplete-revision-declaration` (WARNING), `scp-atomic-extension-violation` (BLOCKING). Updated IGC count 76→79. Added SCP to Protocol Catalog (§62m, 6→7 entries), ConstructKindRegistry (§62n), and stem vocabulary `specconstruct` (§81). Added Revision Completeness Declaration schema to §82 Revision Log format. SCP is binding from r60 onward; revisions prior to r60 are exempt. SCP is self-applying: this revision is the first to comply with it. **New external references:** `SCP` Protocol construct → defined at §62n SCP section (this revision); `scp-forward-reference` IGC kind → defined at §62l IGC table (this revision); `scp-incomplete-revision-declaration` IGC kind → defined at §62l IGC table (this revision); `scp-atomic-extension-violation` IGC kind → defined at §62l IGC table (this revision); `specconstruct` stem → defined at §81 stem vocabulary table (this revision) |
| r59 | 2026-10-16 | spec | r58 gap closure. Added 9 Config subschemas to §62e: `staleness` (hours-based, supersedes legacy `staleness_windows`), `context_budget_r58` (`hard_cap_fraction`, `min_floor_fraction`), `wake` (`max_stale_hours`), `test_coverage` (`freshness_hours`), `sweet_spot` (`value_density_floor`), `retention` (`auto_trigger_bytes`), `metric_sources` (`registry`, `search_endpoint`), `archive_search_paths`, `generated_file_globs`. Added `replaces` field to WakeRegistration schema. Added `effect_type` field and `EffectType` enum to Operation schema. Added `Role` column to PatternMechanismMapping table with PRIMARY/SUPPORTING values. Added `auto_clearable` field description to ConstructKindRegistry. Aligned SDM staleness default prose to reference `Config.staleness` subschema explicitly. **New external references:** (predates SCP — not declared) |
| r58 | 2026-10-16 | spec | 20-gap reliability hardening. Added invocation contract, traversal rules, Evidence weighting, and human-readable format to §62g Justification System. Added activation-failure, partial-update-reconciliation, state-divergence-detection, and re-bootstrap-failure contracts to §74. Added CRC injection, version-mismatch recovery, and context-window overage contracts to §62e/§75. Added default staleness windows and T2 authority-authorization recording to §62c SDM. Added tier tie-breaking, eviction floor, and fallback-rejection contract to §62c CBM. Added signal taxonomy, timeout contract, re-establishment authorization, and recoverable/terminal gap classification to §62c WRM. Added surface measure algorithm and value-density floor enforcement to §62c SSE. Added capability-regression contract, re-test trigger, and test-freshness window to §62c TCG. Added structural/semantic boundary taxonomy and classification-disagreement protocol to §62h T5/T7. Added multi-BLOCKING ordering, operator clearance contract, and isolation contract to §62l IGC. Added archive path resolution and re-ingestion idempotency to §62c RIM. Added discovery mechanism, source validation, and deduplication to §62c EMC. Added firing contract, multi-policy interaction, and atomicity guarantee to §62f retention. Added elevation eligibility criteria, evidence threshold, reversibility, and version continuity to §62n CEP. Added step idempotency, sequential execution, transient failure handling, and retry ceiling to §73 CRRP. Added gap density metric, materiality threshold, and remediation contract to §80/§81. Added uniqueness contract, ambiguity resolution, and multi-mechanism execution order to §62l PMM. Added milestone failure modes, state revertibility, and chain integrity validation to §59b. Added downstream blocking semantics, refresh trigger, and override audit trail to §62j stale-manifest. Added effect-type taxonomy, reconciliation-strategy matrix, and unreconcilable-effect handling to §52. New IGC gap kinds: justification-depth-exceeded, justification-cycle-detected, activation-health-failure, rollback-failure, partial-update-recovered, partial-update-unrecoverable, spec-state-divergence, rebootstrap-attempt-failed, rebootstrap-terminal-failure, crc-version-mismatch, crc-context-overflow, unauthorized-threshold-adjustment, wake-registration-stale, wake-registration-expired, archive-not-found, reingestion-duplicate-skipped, metric-source-discovery-unavailable, retention-pass-partial-failure, crrp-step-failure, crrp-retry-exceeded, technique-classification-disagreement, value-density-below-floor, capability-regression, milestone-chain-integrity-failure, effect-unreconcilable, stale-manifest-override. Total IGC gap kinds: 76 **New external references:** (predates SCP — not declared) |
| r57 | 2026-10-16 | spec | §62m catalog alignment: Mechanism Catalog +1 (MBV); Schema Catalog +3 (MetricEffect, ChunkingPolicy, Chunk); Protocol Catalog +1 (CEP); Contract Catalog IGC count 20→50; derive contract stale counts removed (now §62n-authoritative); PMM description --opt-in-patterns→--opt-in-constructs; stem vocabulary patterncatl AP0-AP25→AP0-AP37; optinpat --opt-in-constructs added |
| r56 | 2026-10-16 | spec+runtime | Full verification pass: NSS §62n compliance check — all violations corrected; no-degradation audit — AP0–AP37, all Protocols, all Mechanisms, all Schemas verified present; IntegrityGapCatalog monotonic growth verified (all gap kinds from r48+ present); all revision log entries r1–r56 verified accurate; section numbering verified (no gaps or duplicates); ConstructKindRegistry updated to include r54/r55 additions (MetricEffect, ChunkingPolicy, Chunk); Metric Baseline Verification registered in Mechanisms table; §62n Base Rule marked universal |
| r55 | 2026-10-16 | spec+runtime | JOINS pass: universal/scoped construct wiring: §62b: CitizenBase/AuthorizedCitizen/TemporalCitizen marked universal; §62i: AP0 Citizen + AP7 Canonical Reduction marked universal; §62l: IntegrityGapCatalog emission pattern marked universal; §62n: RFC 2119 normative force marked universal; §62f: compaction blocked when lifecycle_state=BLOCKED (anchor-drift guard) + destination-anchor guard subsection; §62f: lifecycle boundary requirement references last CheckpointRecord; §62c: Re-Ingestion baseline from last CheckpointRecord; PARTS→PARTS scope notes: DiscoveryBudgetStatus (Discovery domain §36–§43), WakeRegistration (Dormancy/Wake §64–§67), ChunkingPolicy+Chunk (Compaction §62f), AssessmentRecord (TAS §62h + §37); Runtime: destination_anchor guard in compaction path; CheckpointRecord baseline in staleness detection |
| r54 | 2026-10-16 | spec+runtime | Gap closure pass (7 items from r53 audit): §62f: compaction authorization staleness contract (86400s window) + compaction-authorization-stale WARNING gap; §62b: MetricEffect citizen schema (IMPROVEMENT/DRIFT/REGRESSION/NEUTRAL); §62b: metric_effects OPTIONAL added to State Document; §62b: Operation validation_evidence_id + validation_skipped_reason fields + validation evidence contract; §62l: validation-evidence-missing + compaction-authorization-stale gap kinds; Runtime: citizen-base-violation load-time conformance check; objective-lifecycle chunking grouping logic (_compact_with_chunking); immutable field mutation detection (id/created_at); authority_basis active-rule binding validation |
| r53 | 2026-10-16 | spec+runtime | Reliability Hardening Pass: §62b: MetricDefinition authority_level + mutation_requires + last_baseline_audit fields; Base Citizen Clusters (CitizenBase/AuthorizedCitizen/TemporalCitizen) + Extends declarations; GoverningRecord activation — WakeRegistration/ExecutorProvider/RetentionPolicy declared; ExecutorProvider added to State Document; ChunkingPolicy + Chunk schemas added (opt-in chunking); §62c: Metric Baseline Verification mechanism (cycle-start scan all MetricDefs); §62f: Objective-Lifecycle Chunking + Chunk records in governance table; §62h: T2 threshold audit trail requirement; §62a: Executor policy POLICY rule seeding requirement; §62l: 7 new IntegrityGap kinds (metric-baseline-unauthorized-mutation, metric-mutation-policy-missing, threshold-audit-missing, citizen-base-violation, authority-cache-stale, executor-policy-missing, unresolved-effects-reconciliation-failure); §74: self-evolution budget partition invariant ≤20%; Authority cache invalidation contract (3600s TTL); Runtime: mutable metric scan extended to ALL MetricDefinitions; unresolved effects reconciliation audit trail + exception guard; discovery observation key safety (.get chains); authority cache 3600s TTL invalidation; self-evolution 20% budget guard; wake trigger atomic state persist after evaluation; symmetric compliance recording on ACCEPTED |
| r52 | 2026-10-16 | spec+runtime | NSS Compliance + Critical Bug Fixes: destination anchor drift now enters BLOCKED + emits `governance-anchor-drift` BLOCKING IntegrityGap; executor failures truncation now emits CompactionEvent before truncating; `decisions` key → `decision_records` (§45 compliance); removed `ACCEPTED` as lifecycle_state enum value; unified `pending_validation` → `pending_validations` (plural canonical); added durable state checkpoint between operation record write and ACTIVE transition; governance domain now emits ComplianceRecord on authority denial; §62b: section-level Schema metadata declaration added; compliance_records / compliance_state OPTIONAL → REQUIRED in State Document; MetricDefinition DIRECTIVE seeding contract + DIRECTIVE seeding fields; §62f: integrity_gaps / status_transitions / assessment_records / processed_input_ids added to governance table; §62l: metric-definition-drift (WARNING) + governance-anchor-drift (BLOCKING) added to IntegrityGapCatalog; §62c: metrics domain added to Staleness Detection Mechanism |
| r51 | 2026-10-14 | spec | 2026-10-14-r51. Normative Specification Standard: §62n added (Base Rule, 5-kind hierarchy, Construct Lattice, Mandatory Construct Metadata, Templates per Kind, ConstructKindRegistry); ConstructElevationProtocol added to §62l; construct metadata lines on all 12 §62l protocols and 20 §62c mechanisms; duplicate §79 renumbered (Spec Structural Audit → §80, Final Invariant → §81, Revision Log → §82) |
| r50 | 2026-10-14 | spec | 2026-10-14-r50. Full Structural Normalization: AP0–AP25 retrofitted to canonical Intent/Roles/Constraints/Implementation template; §62l 12 entries canonized with Citizens using/Referenced from footers; IntegrityGapCatalog completed (+19 gap kinds, INFO severity tier declared); tier table updated AP0–AP37, AP27/AP28/AP36 tier corrections; §62b Used in: on 13 citizens; 9 citizens converted to code-block format; Domain-Section Citizen Registry; 8 §62c mechanisms AP-cited; §53 mechanism stubs in §62c; Re-Ingestion Mechanism rename; §62k moved to correct position; §79 Spec Structural Audit renumbered |
| r49 | 2026-10-14 | spec+runtime | 2026-10-14-r49. Full Patternization Pass: AP26–AP37 (12 new architectural meta-patterns); CognitiveResetRecoveryProtocol, WakeRegistrationVerification, ComplianceRecordingContract added to §62l; cross-reference wires to AP26–AP37 in §52–§54, §60, §62a, §62c, §63–§67, §72–§74; §62b cross-reference note AP0–AP24→AP0–AP37; PatternMechanismMapping extended; 72 building blocks |
| r48 | 2026-10-14 | spec+runtime | Compliance Canonization: ComplianceRecord + ComplianceState citizens; compliance_records/compliance_state State fields; §54 compliance recording contract; urace /compliance command; Data Interchange canonical note |
| r47 | 2026-10-14 | runtime-only | Extract shared helpers: `_aggregate_scores`, `_affinity_match`, `_make_catalog_digest_fns`, `_suggest_unadopted_for_refs`, `_refresh_derived_refs`; fix digest update in refresh |
| r46 | 2026-10-14 | spec+runtime | New-construct suggestion + construct/pattern update detection on `urace update download/explain`; `construct_digests`/`pattern_digests` in saved refs; DeriveUpdateSuggestion + ConstructUpdateDetection contracts |
| r45 | 2026-10-14 | spec+runtime | `--opt-in-constructs` replaces `--opt-in-patterns` (alias kept); ConstructSetRef citizen + stale-construct-set detection; `--save`/`--refresh` wired for DerivedConstructSet; `construct_set_refs` in initial state |
| r44 | 2026-10-14 | spec+runtime | `--from-constraints`: HardConstraint-to-construct suggestion; `--from-inspection`: InspectionSurface gap-to-construct suggestion; ConstraintDerivedSuggestion + GapDerivedSuggestion contracts |
| r43 | 2026-10-14 | spec | Purge all runtime-specific function/variable names from spec body; add Revision Log (§82); all contracts now stated in executor-agnostic terms |
| r42 | 2026-10-14 | spec | `--constructs` canonical arg; `--patterns` backward-compat alias; "Building Blocks" canonical user-facing name for 60 derivable constructs |
| r41 | 2026-10-14 | spec | §62m Extended Construct Catalogs: Mechanism (6), Schema (20), Protocol (2), Contract (6); `--kind` flag; DerivedConstructSet citizen; ConstructCatalog; IntentSuggestionEngine construct mode |
| r40 | 2026-10-14 | spec | Intent-first `urace derive`: positional `<intent>` arg; `--suggest` dry-run; `--from-goals`; IntentSuggestionEngine contract; GoalDerivedSuggestion |
| r39 | 2026-10-14 | runtime-only | §62l enforcement wiring pass — no new normative spec contracts added; existing contracts from r38 implemented in reference runtime |
| r38 | 2026-10-14 | spec | §62l Shared Reuse Contracts: GoverningRecord cluster, EffectUncertaintyProtocol, OperatorGateProtocol, AuthorityClosureInvariant, RevalidationScope, InspectionSurface, IntegrityGapCatalog (20 kinds), PatternMechanismMapping |
| r37 | 2026-10-14 | spec | §72 PolicyRecord/HardConstraint/PolicyKind/PolicyStatus/ConstraintEnforcement; §37 AssessmentRecord; §36 DiscoveryRecord/DiscoveryCycleStatus; §59 MarketSignal/FitHypothesis; §63 OwnershipMarker/ConcurrencyPolicy; §76 minimum viable behaviors list |
| r36 | 2026-10-14 | spec | DerivedManifestRef (dmr-), DerivationRecord (drv-), DerivationKind enum; `urace derive` --refresh/--apply-capabilities/--derive-milestone/--show-delta; derivation_records/derivation_refs State fields |
| r35 | 2026-10-14 | spec | Milestone chain; TestRecord as citizen; pattern→capability gap detection; `--opt-in-patterns` AP range extended to AP0–AP25 |
| r34 | 2026-10-14 | spec | AP25 Bounded Evolution Band; full wiring pass over quality/resilience/orchestration patterns |
| r33 | 2026-10-14 | spec | Quality/resilience architectural wiring pass |
| r32 | 2026-10-14 | spec | AP24 Derivation Framework; pattern count updated to 25 |
| r30–r31 | 2026-10-14 | spec | Comprehensive quality/resilience/orchestration pass; pattern count 24→25 |
| r29 | 2026-10-14 | spec | AP range reference updated AP0–AP19 → AP0–AP24 |
| r28 | 2026-10-14 | spec | Stale manifest detection; update system integration with derived manifests |
| r27 | 2026-10-14 | spec | Skip-by-default derive contract; `--opt-in-patterns` flag; update orchestration |
| r26 | 2026-10-14 | spec | §62j Derivation Framework; DerivedSystemManifest; PatternCatalog AP0–AP24; `urace derive` command |
| r25 | 2026-10-14 | spec | AP20–AP23 (Circuit Breaker, Compaction, Checkpoint, Justification Chain) |
| r24 | 2026-10-14 | spec | §62i AP17–AP19 (Formula Rule Pairs, Scheduled Task, Customization Layer) |
| r23 | 2026-10-14 | spec | §62i AP11–AP16 (Bridge, Orchestrator, Observer, Input Queue, Event Bus, State Snapshot) |
| r22 | 2026-10-14 | spec | Canonical term coverage: Primitive, Communication, Diagram, Method; §81 stems +14; §62a /prefix fix |
