# URACE

**Universal Recursive Autonomous Co-Founder Engine**

> **It drives the boat. You pick the destination.**

URACE is a general-purpose, recursive autonomous product-evolution control plane that owns the journey from intent to continuously evolving product.

The Product is the user's project, goal, service, process, research effort, business outcome or other governed endeavor. Bootstrap does not default to improving URACE itself; URACE self-evolution is subordinate and occurs only when separately justified and authorized as a way to advance the user's governing Intent.

It preserves and governs a continuous Product lifecycle across bounded, replaceable, and potentially stateless intelligence and execution systems.

**You choose the destination you want to retain. URACE drives everything you delegate beneath it.** Within that delegated Authority, URACE independently discovers what should happen next, prioritizes, plans, selects capabilities, executes, learns from Evidence, validates results, checkpoints accepted progress, recovers across interruptions, becomes dormant when no justified action exists, reactivates when meaningful change occurs, and continues evolving the Product.

At its core, URACE is also an **open, editable, and bootstrap-ready idea expressed as an open-source blueprint** through `URACE.md`. It applies **meta-implementation principles**: the blueprint defines a lifecycle architecture that can be instantiated as an environment-appropriate implementation rather than prescribing a single fixed implementation. It can be inspected, adapted, extended, and evolved without depending on any particular Product, AI, [Executor, or Orchestrator](#where-urace-sits).

URACE sits **above those replaceable execution capabilities**, preserving lifecycle ownership while delegating bounded Operations beneath it.

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

## Start Here

URACE is a specification that a capable coding or execution system uses to build a running implementation for your Product. Downloading this repository does not itself install an `urace` command.

For a first bootstrap, you need only:

1. `URACE.md` from this repository;
2. a short companion document describing your Product, desired outcome and boundaries; and
3. one capable AI, coding agent or execution system that can inspect and modify your Product environment.

A minimal companion document can be plain text:

```text
Product: <what should be improved>
Desired outcome: <what observable result should improve>
Do not change: <protected files, behavior, data, cost or other boundaries>
You may decide: <work URACE may plan and execute without asking each time>
Ask me first: <decisions I retain>
Available capabilities: <AI, coding tool, APIs, tests or services URACE may use>
Self-evolution policy: necessary-only
External-metric policy: provided-only
```

Give that document and `URACE.md` to the capable system and say:

```text
Read URACE.md completely as the authoritative specification. Use my companion
document as deployment context. Bootstrap and test the smallest complete URACE
implementation for my Product. Finish by showing me the exact inspect command,
one bounded-run command, persistent autonomous command, generated implementation
location, durable-state location, attached Executor status and unresolved limits.
```

Then use the exact commands in the bootstrap report. Do not guess a command, create implementation folders manually or execute `URACE.md` as a program. If bootstrap reports a feature as unsupported, either attach the missing capability and re-bootstrap or use the supported lifecycle without that optional feature.

Continue to [Bootstrap](#bootstrap) for the complete setup and validation requirements. After bootstrap, follow [Using URACE](#using-urace).

---

## Summary

- **[Start Here](#start-here)** — The shortest path from the two public documents to a tested running implementation.
- **[Introduction](#urace)** — A persistent autonomous product-evolution control plane that owns lifecycle navigation above replaceable intelligence and execution systems.
- **[Why URACE](#why-urace)** — Preserves continuous product evolution beyond individual AI sessions, models, agents, and orchestrators.
- **[Core Model](#core-model)** — Separates Intent, Authority, Evidence, URACE navigation, executor capabilities, and Validation.
- **[Authority](#you-decide-what-you-retain)** — You decide what remains authoritative; URACE autonomously drives what you delegate.
- **[Autonomous Evolution](#autonomous-product-evolution)** — Discovers, prioritizes, executes, validates, and checkpoints justified product evolution.
- **[Evidence](#evidence-driven-evolution)** — Uses observed reality to guide evolution without allowing Evidence to manufacture Authority.
- **[Recursive Self-Evolution](#recursive-self-evolution)** — Can discover and execute improvements to its own implementation where already authorized.
- **[Evolution Boundaries](#three-kinds-of-evolution)** — Keeps product evolution, runtime URACE self-evolution, and `URACE.md` specification evolution distinct.
- **[Executors and Orchestrators](#executors-and-orchestrators)** — Keeps intelligence and execution replaceable; one capable executor is sufficient, while richer orchestration remains optional.
- **[Universal Design](#universal-by-design)** — Remains independent of particular models, executors, orchestrators, languages, repositories, platforms, and product types.
- **[Consequential Commercial Operation](#accountable-consequential-commercial-operation)** — Provides an optional accountability and control checklist for real-world commercial effects without recommending them.
- **[Competing Variants](#controlled-competing-variants)** — Describes bounded isolated portfolio experiments and evidence-based selection.
- **[Portable Analytics](#portable-analytics-and-system-scorecard)** — Exports observable history for spreadsheets and a browser dashboard without making control depend on either.
- **[Bootstrap](#bootstrap)** — Uses `URACE.md` as the authoritative bootstrap specification for creating an environment-appropriate running URACE.
- **[Measurable Progress](#measurable-progress-and-follow-up)** — Preserves baselines, progressive targets, guardrails, follow-up conditions, and explicit decisions from observed outcomes.
- **[Using URACE](#using-urace)** — Operates through the generated persistent implementation rather than repeatedly using the bootstrap specification.
- **[Persistent Autonomy](#persistent-autonomy)** — Remains lifecycle-active through both execution and efficient dormant/wake states.
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

A capable model-backed agent, deterministic tool, service or orchestrator may fulfill these roles. Product names do not establish compatibility; actual capability and suitability depend on the Operation and deployment.

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

URACE itself can participate in the lifecycle when the bootstrap self-evolution policy permits it.

Self-improvement is a deployment choice with three modes:

| Mode | Behavior |
|---|---|
| `disabled` | Do not create or execute runtime self-evolution or re-bootstrap Objectives. Product evolution continues normally. |
| `necessary-only` | Repair or replace URACE only when a demonstrated URACE limitation materially blocks, degrades, or endangers the governed Product or its continuity, and no lower-impact Product route is sufficient. This is the recommended mode. |
| `continuous` | Allow justified URACE improvements to compete with Product work even when they are beneficial rather than necessary. |

Bootstrap records the selected mode in durable policy. If no mode is supplied, it uses `disabled`; self-improvement therefore requires an explicit opt-in. The authoritative source can later opt in, opt out, or switch modes through an attributable policy change. A mode controls eligibility and never supplies Authority by itself.

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

Where the selected mode and existing Authority permit it, URACE may autonomously discover that its own implementation is limiting the governing Intent, promote that limitation into an Objective, prioritize it against Product work, plan the improvement, execute it through replaceable Executors, validate it, checkpoint the accepted change, and continue operating. In `necessary-only` mode, the Evidence must establish necessity and URACE must prefer a sufficient lower-impact route when one exists.

### Safe Runtime Activation

A runtime candidate is prepared away from the active implementation and must pass applicable tests and durable-state compatibility checks. The current runtime remains the stable fallback until the candidate starts successfully and reports healthy operation.

Where the active process cannot safely replace itself, a small stable launcher may supervise activation and restart without becoming the Product-lifecycle owner. If the candidate cannot import, start, load existing state, or pass its activation health check, the launcher restores and restarts the prior stable runtime.

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

## Re-Bootstrap vs. Self-Evolve

Incremental self-evolution changes the existing runtime when a bounded repair or improvement is sufficient. Re-bootstrap reconstructs a candidate runtime from `URACE.md` and deployment context when architectural divergence, irreparable drift, technology replacement, or new mandatory requirements make reconstruction more valuable.

Both remain governed by the selected self-evolution mode. `disabled` prohibits autonomous use of either path. `necessary-only` permits them only to resolve a demonstrated material necessity. `continuous` permits justified beneficial changes within Authority.

Both paths preserve the authoritative specification, Authority, Intent, accepted Product artifacts, history, and durable lifecycle state. Both use isolated preparation, validation, state-compatibility checks, supervised activation, post-start health confirmation, and rollback to the last stable runtime.

Re-bootstrap does not authorize resetting history, expanding Authority, discarding state, or bypassing migration.

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
                      │
          ┌───────────┼───────────┐
          ▼           ▼           ▼
    EXECUTOR A   EXECUTOR B   EXECUTOR C
```

The complementary Executors provide a broader capability pool; they need not participate in every Operation or occupy permanent roles. URACE selects among available capabilities according to the work at hand.

These labels describe roles, not products or dependencies. Current capabilities, availability, terms, privacy characteristics and suitability should be verified for the deployment.

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

This is architectural portability, not a promise that one generated adapter can operate every Product or workflow. A deployment works only where its Executors, connectors, permissions, validation methods and effect channels cover the required Operations. Bootstrap must report unsupported capabilities plainly and preserve dormant or blocked work until a suitable capability exists.

The public contract names capabilities, observable states and safety properties. It does not prescribe a package, vendor, executable, storage layout, operating system or cryptographic product merely because one deployment uses it. Bootstrap selects and validates concrete mechanisms for the actual environment, and its local completion report names exact dependencies, commands, paths and limitations. An illustrative interface in this guide never counts as proof that a deployment supports it.

A very thin starting project can be valid, but a broad commercial objective lacks the definition needed to claim success safely. URACE should preserve the Intent, identify assumptions and missing retained decisions, establish outcome measures, resource budgets, and legal or reputational guardrails, then discover and rank authorized reversible experiments. It cannot guarantee revenue, market demand, eventual discovery or lawful completion merely by running indefinitely. It should report those gaps rather than simulate progress.

## Accountable Consequential Commercial Operation

Here, **operator** means the person or organization that chooses to configure, authorize, deploy or use the generated system. This setup is optional guidance for an operator who has independently chosen to delegate commercially consequential work. It is not a recommendation to pursue a particular activity, opportunity, market, transaction or level of autonomy.

No command, model, metric, portfolio experiment or length of operation can guarantee income, revenue, profit, demand, legality or a favorable outcome. URACE can run bounded experiments and preserve Evidence; it cannot control customers, markets, counterparties, law, platform decisions or unrelated events. A one-line command changes operating convenience, not that limit.

Before enabling real-world effects, the operator should provide and verify:

- a specific lawful Product, beneficiary, jurisdiction and success definition;
- named human or organizational accountability for every delegated role;
- explicit Authority for research, communication, representation, contracting, purchasing, publishing, account access, payment handling and data use, with undelegated effects denied by default;
- hard per-action and cumulative budgets for cash, credit, compute, time and downside exposure;
- approved counterparties, channels, claims, terms, refund or dispute processes and escalation contacts;
- credential isolation, least privilege, separation of duties and revocable access;
- an append-only action, approval, communication, transaction and Evidence trail;
- independent reconciliation of orders, invoices, receipts, balances, fees, taxes, liabilities and realized outcomes;
- staged rollout, sandbox or test mode, rate limits, anomaly thresholds, a kill switch and recovery procedures;
- jurisdiction- and sector-specific review for contracts, tax, employment, consumer protection, privacy, licensing, advertising and regulated activity;
- outcome metrics based on realized net results, with time, risk, complaints, reversals, concentration and compliance as guardrails;
- human review for irreversible, identity-bearing, legally binding, high-value or high-impact effects unless applicable Authority and law clearly support a stronger arrangement.

The operator remains responsible for deciding whether and how to deploy the generated system, granting credentials and Authority, supervising effects, complying with applicable obligations and obtaining qualified professional advice. URACE, its specification, documentation and contributors do not become the operator, principal, agent, employer, fiduciary, accountant, tax adviser or legal counsel by describing a control architecture. Documentation cannot transfer responsibility or waive duties imposed by applicable law or agreement. No documentation can guarantee immunity from liability in every jurisdiction or factual setting.

The repository uses the [MIT License](LICENSE). Its permission grant and its `AS IS`, warranty and liability terms govern distribution of this software. They do not grant operational Authority, satisfy laws or contracts, or replace advice about a particular deployment.

Useful starting references include the [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework), [FTC advertising and marketing guidance](https://www.ftc.gov/business-guidance/advertising-marketing), and, for United States recordkeeping context, [IRS Publication 583](https://www.irs.gov/forms-pubs/about-publication-583). They are not substitutes for requirements that apply to the operator's jurisdiction, sector and facts.

## Controlled Competing Variants

Some Products benefit from evolving several candidates at once: isolate variants, measure them under comparable conditions, stop weak variants, select supported winners, then seed the next generation from a selected branch. This can find solutions that a single linear path misses while keeping the live Product stable.

A **variant** is an isolated candidate. An **instance** is a running copy of a variant. Source-only work needs variants; behavioral or service evaluation usually needs instances too. Do not run several mutators against one working directory.

Keep the experiment comparable by separating three kinds of information:

| Boundary | What belongs there | Why |
|---|---|---|
| **Shared read-only contract** | Objective, Authority, constraints, metric definitions, guardrails, selection method, total and per-variant budgets, stopping rules, schemas and approved Evidence sources. | Every variant competes under the same rules. Changing it creates a new experiment version. |
| **Generation snapshot** | Base commit, context and Evidence cutoff, dependency locks, configuration versions, fixed test data or digest, random seeds, Executor/tool versions and evaluation protocol. | Every mutation in a generation starts from a reconstructable comparable state. |
| **Variant/instance local** | Isolated workspace, mutation description, hypothesis, process, writable database, endpoint, cache, temporary files, logs, scoped credentials and observations. | Mutations cannot corrupt each other or leak effects between cohorts. |

A credential service, immutable dataset or observation service may be physically shared only through separately scoped read-only or least-privilege access. Never share writable Product state, queues, sessions, output directories, ports, test cohorts or effect identifiers among competing instances. Store the central lineage and result ledger append-only or transactionally; variants may report to it but must not rewrite competitors' records.

### Safe communication and learning

Variants may inspect approved snapshots of prior versions, observations, failures, peer reviews, agora decisions and selected lessons. They may submit findings about one another, challenge a hypothesis and propose a decision or lesson. Communication goes through the controller's shared ledger. The **agora** is the readable decision-exchange view of that ledger; variants submit through mediated commands rather than editing it directly:

```text
variant A ──proposal/review──► AGORA ◄──vote/review── variant B
                                  │
                    equal vote + Evidence tally
                                  │
                       controller decision
                                  │
                    approved inheritance link
                                  │
                    selected winner's children
```

Peer messages are advisory untrusted Evidence, never commands or Authority. A variant cannot edit another workspace or record, change the contract, increase budgets, grant credentials, select itself, promote itself, stop a peer, create unrestricted descendants or communicate directly with external effects outside its scope. The authoritative source and URACE controller retain contract, admission, capability, budget, stop, selection, promotion and revocation powers. Every message identifies sender, subject, Evidence, confidence and intended scope; secrets and hidden chain-of-thought do not enter the shared ledger.

The experiment constitution never mutates inside an experiment. It freezes Intent and Authority, metric direction, guardrails, evaluation protocol, admission and identity rules, cohort size, planning and per-variant hard ceilings, equal-allocation method, vote eligibility and quorum, selection order, audit lineage, isolation requirements, stop and revocation controls, and recovery behavior. A variant may propose a controller improvement, but cannot apply it or earn Authority through discussion. Changing a protected field starts a separately reviewed experiment with a new identity.

Candidates never receive direct access to the ledger, controller state, integrity key, stable recovery data or another candidate. Give them a scoped read-only snapshot and a bounded submission channel; the controller authenticates the candidate identity, validates the message and performs the append. Test this confinement before unattended launch and after environment changes. If a candidate can address protected storage, keep automatic mutation, voting, selection and promotion unavailable.

Use two integrity layers for the decision exchange: a canonical collision-resistant append chain binds order and content, while an authenticated anchor kept outside candidate control establishes provenance. Verify before reading or extending it and stop selection or promotion on a missing record, fork, replay, reorder, malformed entry or failed authentication. Preserve suspect material for review. Cryptography detects unauthorized ledger changes; it does not prove that submitted Evidence is true, make content safe or grant Authority. Mutually hostile tenants require independently protected identities, storage, secrets, execution environments and an authenticated broker.

Learning is also mediated. Preserve supporting Evidence, counter-Evidence, applicability and confidence. Each admitted variant has one equal effective vote per proposal; a later vote supersedes its earlier vote without deleting history. Confidence is recorded but does not increase voting weight. Adoption requires participation by at least half of admitted variants, the declared minimum support, and more support than opposition. The tally reports support, opposition, abstention and participation, but popularity is not proof. An attributable controller decides whether to adopt, defer or reject the proposal after considering Evidence, guardrails, applicability, vote coverage and dissent.

An adopted proposal survives as an approved decision. It records the selected winner from which it may be inherited, and a child must explicitly link it with `--decision`. Votes never change Authority, select a winner, alter code or force inheritance. This prevents a persuasive majority, correlated variants or cheaply spawned voters from silently controlling later generations. In a hostile or multi-tenant deployment, use an authenticated broker, per-instance identities, access controls, signed or tamper-evident events, admission controls, quotas and network isolation; a same-user workspace is not a security boundary.

The lineage vocabulary is intentionally small:

```text
BASE
  ├── MUTATION generation=1 parent=BASE hypothesis=A
  ├── MUTATION generation=1 parent=BASE hypothesis=B
  └── MUTATION generation=1 parent=BASE hypothesis=C
             │
             └── SELECTED because metric + guardrails + Evidence
                    ├── MUTATION generation=2 parent=selected hypothesis=D
                    └── MUTATION generation=2 parent=selected hypothesis=E
```

For every candidate, record `parent_variant`, `parent_commit`, `generation`, `mutation`, `hypothesis`, `expected_effect`, contract digest, observations, resource cost and guardrail results. For every selection, record the complete ranking and a disposition for every candidate: `SELECTED`, `NOT_SELECTED`, `REJECTED_GUARDRAIL` or `INSUFFICIENT_EVIDENCE`, plus a plain reason. “Lost” means only that the candidate was not selected under this experiment contract and Evidence; it does not mean deletion or universal inferiority.

1. Freeze one attributable baseline and create isolated snapshots, workspaces or environments.
2. Give each variant the same Authority boundary, input snapshot, resource budget and evaluation protocol; record any differences in Executors or conditions.
3. Define outcome metrics, guardrails, stopping rules, minimum Evidence, time horizon and selection method before observing results.
4. Prevent variants from duplicating or conflicting in irreversible external effects. Use simulation, shadow traffic, test accounts, staged cohorts or mutually exclusive assignments where appropriate.
5. Measure quality, net outcome, risk, latency, resource use and learning value. Preserve failed and inconclusive results to reduce survivor and publication bias.
6. Compare against the baseline and account for noise, confounders, multiple comparisons and delayed effects. No movement and ties are valid results.
7. Submit the selected candidate through ordinary Authority, validation, concurrency, transaction and stable-fallback checks before it becomes live.
8. Retain useful diversity when Evidence does not support one universal winner, and stop the portfolio when expected information value no longer justifies its cost.

Stopping a variant means preventing further execution and resource use. Preserve its branch, observations and failure Evidence until retention policy permits cleanup. Selection does not erase losers, prove universal superiority or immediately deploy the winner. A later generation may mutate the selected variant and retain another variant when different conditions favor it.

URACE may automatically spawn, run, stop and mutate variants only when portfolio Authority, active-instance ceilings, per-variant and total budgets, effect isolation, health checks, stopping rules and a tested adapter are present. A versioning or snapshot mechanism manages source isolation; an environment-appropriate lifecycle adapter owns running instances. Automatic portfolio operation is optional and remains subordinate to ordinary Product evolution.

### Hands-on portfolio usage

This is an optional advanced feature. Skip this section unless the bootstrap report says portfolio evolution is supported.

When supported, bootstrap generates an environment-appropriate `urace portfolio` interface and reports its exact commands, isolation mechanism and limitations. The commands below describe that interface; no packaged example directory is required. An implementation creates one dedicated generated-data boundary for isolated candidate workspaces and never promotes or deletes a candidate automatically. If the illustrated interface is unavailable, do not copy helper files or invent paths: use the reported equivalent or re-bootstrap with the missing isolation and evaluation capabilities.

Start an experiment with one metric and a maximum of three active variants:

```bash
urace portfolio init \
  --objective "Reduce response latency without increasing failures" \
  --metric p95_ms --direction minimize \
  --minimum-evidence 3 --max-active 3 \
  --authority "May change query implementation; may not change public behavior" \
  --guardrail-definition "Error rate and correctness must not regress" \
  --evaluation-protocol "Same fixture, machine, warmup and five windows" \
  --context-snapshot "commit + locked dependencies + fixture-v3"
```

For the shortest feature-complete path, put exactly `X` mutation descriptions in a plan and create the whole cohort in one command:

```bash
cat > mutations.json <<'JSON'
[
  {"name":"cache-a","mutation":"Add bounded result cache","hypothesis":"Repeated reads dominate latency","expected_effect":"Lower p95 with stable errors"},
  {"name":"cache-b","mutation":"Cache immutable lookups only","hypothesis":"A narrower cache retains most benefit","expected_effect":"Moderate p95 reduction with lower risk"},
  {"name":"simpler-query","mutation":"Use one indexed query","hypothesis":"Query shape is the bottleneck","expected_effect":"Lower p95 without correctness loss"}
]
JSON

urace portfolio cohort \
  --count 3 --prefix generation-1 --plan mutations.json \
  --total-resource-budget 900 --resource-unit wall_seconds

urace portfolio run-cohort generation-1 \
  --timeout 300 --max-parallel 1 -- <project-validation-command>
```

This allocates `300 wall_seconds` to each candidate and exposes each allocation through scoped candidate metadata. A `wall_seconds` allocation caps each command's timeout; the lower of that allocation and `--timeout` wins. Other units are declared accounting limits until an environment adapter enforces equal compute, memory, network, storage, accelerator and paid-service quotas. Equal numbers alone do not isolate a shared host. Sequential evaluation is the default and `--max-parallel 1` states it explicitly. Use a larger value only with isolated resources, writable data, endpoints and effects under comparable conditions.

### Continuous automatic generations

The same portfolio can run complete generations continuously and resume from its last durable phase. Bootstrap should generate and validate the workflow file and its three adapter commands. Start it using the path reported at bootstrap:

```bash
urace portfolio autonomous \
  --workflow path/reported-by-bootstrap.json --cycles infinity
```

The following is the shape of that generated file. The `tools/...` names are illustrative and will not work unless bootstrap created those exact adapters:

```json
{
  "cohort_size": 2,
  "total_resource_budget": 600,
  "resource_unit": "wall_seconds",
  "executor_invocation_budget_per_generation": 12,
  "planner_invocation_budget_per_generation": 3,
  "evaluation_protocol_version": "fixture-v3-five-windows",
  "provider_internal_hard_caps": true,
  "external_effects": "none",
  "candidate_isolation": "<validated-isolation-profile>",
  "candidate_network": false,
  "candidate_environment_allowlist": [],
  "plan_command": ["<planner-adapter>"],
  "mutate_command": ["<mutation-adapter>"],
  "evaluate_command": ["<evaluation-adapter>"],
  "cycle_delay_seconds": 60,
  "error_backoff_seconds": 300,
  "max_consecutive_failures": 5,
  "retain_generations": 10
}
```

Use `--cycles 10` for exactly ten completed generations, replacing `10` with any positive integer. Use `--cycles infinity` for persistent generations. With the values above, two variants receive equal `300 wall_seconds` allocations and equal hard ceilings of six controller-level Executor invocations per generation. Planning has its own hard ceiling of three attempts. Choose a generous total that fits the actual provider and operational limits; “generous” never means unlimited.

The controller reserves an invocation durably before each planner, mutation or evaluation process starts, so interruption and retry cannot silently reopen that allowance. An adapter that performs several model or provider calls inside one process must enforce its own token, monetary and provider-call ceiling through a metering gateway or equivalent; the controller cannot infer hidden calls. Bootstrap must state which limits are controller-enforced and which are adapter-enforced before calling them hard caps.

For everyday operation, the generated interface may provide these equivalent short forms:

```bash
# Persistent generations
urace portfolio auto path/reported-by-bootstrap.json

# Exactly 10 generations
urace portfolio auto path/reported-by-bootstrap.json --cycles 10

# One resumable generation
urace portfolio next path/reported-by-bootstrap.json

# Human-readable current state; add --json for automation
urace portfolio feedback

# Verify the authenticated live ledger and retained archive segments
urace portfolio verify

# Discover portfolio commands without guessing
urace portfolio commands
```

Before a persistent run, verify the workflow without calling its adapters. `launch` repeats this preflight and starts only if every check passes:

```bash
urace portfolio preflight path/reported-by-bootstrap.json

# Full persistent path: preflight, then resumable generations and per-generation feedback
urace portfolio launch path/reported-by-bootstrap.json
```

The one-line `launch` command is the preferred hands-off entry point. It verifies adapter existence, equal controller budgets, frozen experiment rules, adapter-level provider caps, declared external-effect handling and a real candidate-confinement probe that denies access to controller and ledger storage. It cannot verify hidden provider behavior merely from a boolean; bootstrap must test the adapter before setting `provider_internal_hard_caps` to `true`. Run `preflight` again after environment changes. Re-bootstrap is needed only when the installed implementation lacks a required capability and a smaller validated repair cannot supply it; it is not a routine prerequisite.

`auto` is a shortcut for `autonomous`; `next` is a shortcut for one cycle. The explicit commands remain the stable, unambiguous form. `feedback` is read-only and reports status, phase, completed generations, selected parent, next step, planner and per-variant hard budgets, metric and guardrail results, Evidence volume, agora state, the last error and material isolation/provider-limit caveats. `verify` checks the authenticated live ledger, Agora chain and retained archive envelopes without running a candidate.

The workflow names three project-specific commands as JSON argument arrays:

| Command | Input | Required output or effect |
|---|---|---|
| `plan_command` | `URACE_GENERATION` and `URACE_COHORT` | One JSON array containing exactly `cohort_size` objects with `mutation`, `hypothesis`, and `expected_effect`; optional `lessons` and adopted `decisions` may be linked. |
| `mutate_command` | Runs inside each isolated candidate workspace with the mutation, hypothesis, identity and equal budget in scoped variables. | A bounded candidate change recorded by the versioning adapter. |
| `evaluate_command` | Runs inside the mutated candidate workspace with the same environment. | One schema-valid result containing value, guardrails, Evidence units, resource cost and note. It must be read-only; detected source changes are discarded and fail the phase. |

The controller performs `plan → create → mutate → evaluate → select → archive` for every generation. Selection compares only that generation. Its winner becomes the next generation's parent; the former winner becomes a retained seed. Old candidate workspaces are removed after `retain_generations`, while their full records remain in the generated portfolio archive boundary; old plans are removed and oversized event history is moved to bounded archive batches. The current phase, workflow digest, generation, errors and completed-cycle count remain in the portfolio ledger. Bootstrap reports the environment-specific location.

Every candidate stage is checkpointed. If the process stops between phases, running the identical command resumes the incomplete generation. If interruption occurs during mutation, the controller restores that isolated workspace to its recorded parent snapshot before retrying, so a partial mutation cannot become a winner. Repeated failures use the configured backoff and pause ceiling instead of spending resources forever. A handled interruption records `INTERRUPTED` before exit. Abrupt termination cannot corrupt a transactionally committed ledger, though external effects from a terminated adapter require that adapter's own idempotency and reconciliation.

This mode is fully automatic only after those three adapters provide real planning, mutation and discriminating evaluation for the Product. They may call a capable AI Executor or Orchestrator, deterministic tooling, or both. The controller does not treat an unevaluated model opinion as a metric. Keep mutation effects inside candidate workspaces and test environments; use an environment adapter for services, credentials, external effects and hard resource quotas. After a process or machine restart, invoke the reported command to resume; continuous process restart behavior remains a deployment choice.

The equivalent manual path is:

```bash
urace portfolio spawn cache-a \
  --mutation "Add bounded result cache" \
  --hypothesis "Repeated reads dominate latency" \
  --expected-effect "Lower p95 with stable errors"

urace portfolio spawn cache-b \
  --mutation "Cache only immutable lookups" \
  --hypothesis "A narrower cache keeps most benefit with less risk" \
  --expected-effect "Moderate p95 reduction with lower resource cost"

urace portfolio spawn simpler-query \
  --mutation "Replace nested lookup with one indexed query" \
  --hypothesis "Query shape is the bottleneck" \
  --expected-effect "Largest p95 reduction without correctness loss"
```

Each printed path is an independent candidate workspace. Edit it manually, point an Executor at it, or run a bounded command inside it:

```bash
urace portfolio run cache-a --timeout 300 -- <project-validation-command>
```

After measuring each variant in equivalent conditions, record the observed metric, comparable resource cost, Evidence volume and guardrail result:

```bash
urace portfolio record cache-a \
  --value 82 --resource-cost 4 --evidence-units 5 --guardrails pass \
  --note "Five isolated load-test windows"

urace portfolio record cache-b \
  --value 91 --resource-cost 3 --evidence-units 5 --guardrails pass

urace portfolio record simpler-query \
  --value 79 --resource-cost 7 --evidence-units 5 --guardrails fail \
  --note "Failure-rate guardrail regressed"

urace portfolio rank
urace portfolio select
```

The selector excludes failed guardrails and insufficient Evidence and orders the declared metric in its declared direction. A separately validated experiment-wide system contribution may break an exact primary-metric tie; lower recorded resource cost is the next tie-breaker. Review the result before normal validation and promotion.

Record a peer critique, then turn supported cross-variant learning into an explicitly approved lesson:

```bash
urace portfolio review cache-b cache-a \
  --finding "Cache invalidation dominates the remaining failures" \
  --evidence "Failure logs reference stale keys in 4 of 5 windows" \
  --recommendation "Test bounded expiry in the next generation" \
  --confidence 0.8

urace portfolio lesson \
  --from-variants cache-a,cache-b \
  --statement "Bound cache entries by expiry and immutable-key scope" \
  --evidence "Both variants reduced reads; stale keys explain observed failures" \
  --counterevidence "Only one fixture and five windows were observed" \
  --applicability "Read-heavy paths with immutable or expiring keys" \
  --confidence 0.7 --approved-by portfolio-controller
```

Use the shared agora when variants have exchanged a concrete decision that should compete for survival across cycles:

```bash
urace portfolio agora-propose cache-a \
  --decision "Use bounded expiry for mutable cache entries" \
  --rationale "It retains the latency benefit while limiting stale entries" \
  --evidence "Four of five stale-key failures involved unbounded entries" \
  --counterevidence "Only one fixture was evaluated" \
  --applicability "Read-heavy paths whose entries have a safe expiry" \
  --expected-effect "Keep most latency improvement without stale-key failures"

urace portfolio agora-vote cache-b proposal-1 \
  --choice support --reason "Consistent with the immutable-cache result" \
  --evidence "cache-b passed all guardrails" --confidence 0.8

urace portfolio agora-vote simpler-query proposal-1 \
  --choice abstain --reason "The query variant did not test caching" \
  --evidence "No discriminating cache evidence" --confidence 0.9

urace portfolio agora-show
urace portfolio agora-decide proposal-1 \
  --outcome adopt --minimum-support 1 --approved-by portfolio-controller \
  --reason "Supported, bounded and applicable to the selected cache winner"
```

After `cache-a` is selected, its child can inherit that surviving decision when applicable:

```bash
urace portfolio spawn generation-2-a \
  --mutation "Add bounded expiry to the selected cache" \
  --hypothesis "The agora decision addresses the observed stale-key failure" \
  --expected-effect "Retain lower p95 while passing correctness guardrails" \
  --decision decision-1
```

The ledger retains every proposal, vote revision, frozen tally and controller disposition. `agora-show` provides the full machine-readable view; `explain` reports the number of proposals and surviving decisions.

### Evolving the selection system

Improving the Product remains every variant's primary purpose. A variant may propose changing the portfolio controller only when a demonstrated controller limitation makes the change necessary and the proposed result benefits the experiment as a whole. Such a proposal must identify necessity Evidence, experiment-wide benefit, counter-Evidence and the preserved selection, Authority, budget, isolation and recovery invariants. Variants may vote to refer it, but cannot apply, authorize or inherit it:

```bash
urace portfolio agora-propose cache-a \
  --scope portfolio-system \
  --decision "Repair biased cohort admission" \
  --rationale "The defect excludes eligible mutations before evaluation" \
  --evidence "Three reproducible admissions disagree with the declared contract" \
  --counterevidence "No failure appears with two-candidate cohorts" \
  --applicability "Cohorts larger than two" \
  --expected-effect "Restore equal admission without changing selection criteria" \
  --necessity-evidence "The defect invalidates current comparisons" \
  --experiment-benefit "Every admitted variant receives the declared equal opportunity" \
  --invariants-preserved "Authority, guardrails, hard budgets, isolation, recovery and metric priority"

urace portfolio agora-decide proposal-2 \
  --outcome refer --minimum-support 2 --approved-by portfolio-controller \
  --reason "Necessary-system-change evidence merits independent validation"
```

Referral creates Evidence for the ordinary authorized URACE self-evolution path; it does not modify the controller. Only after isolated implementation, regression testing and independent confirmation of experiment-wide benefit may `agora-confirm-system` record the result. An optional bonus is capped at `0.05` and can break only an exact primary-metric tie, never compensate for a worse Product outcome, failed guardrail, insufficient Evidence, excess resource use, reduced privileges, weakened safeguards or expanded Authority.

Stop a non-selected variant without destroying its Evidence, then create the next generation from the selected branch. When `--parent` is omitted after selection, `spawn` automatically uses that selected branch:

```bash
urace portfolio stop cache-b
urace portfolio spawn generation-2-a \
  --mutation "Tune selected design for lower memory" \
  --hypothesis "The selected result has removable allocation overhead" \
  --expected-effect "Same p95 with lower memory cost" \
  --lesson lesson-1
urace portfolio spawn generation-2-b \
  --mutation "Combine selected design with bounded prefetch" \
  --hypothesis "Predictable next reads can reduce tail latency" \
  --expected-effect "Lower p95 without increasing errors"
urace portfolio explain
urace portfolio status
```

For a service or other live system, build and start each candidate workspace with isolated endpoints, data, credentials and cohorts using a suitable deployment adapter. Feed the resulting observations back through `record`. Do not share writable production data or send the same irreversible action from multiple instances.

Use `explain` for a short lineage and selection narrative; use `status` for the complete machine-readable ledger. An environment-specific URACE implementation may expose equivalent `portfolio init`, `spawn`, `run`, `record`, `rank`, `select`, `stop`, `review`, `agora-propose`, `agora-vote`, `agora-decide`, `agora-show`, `lesson`, `explain` and `status` commands or durable inputs. Unsupported portfolio automation must remain visibly unavailable rather than pretending that ordinary concurrent editing provides experimental isolation.

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
- self-evolution policy: `disabled`, `necessary-only` (recommended), or `continuous`; omission defaults to `disabled` and does not imply permission;
- external-metric policy: `disabled`, `provided-only`, or `discover-public-and-use-provided`; omission defaults to `disabled`;
- authorized public or private metric sources, metric definitions, and credential environment-variable names or secret references without credential values;
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

For example, attach or otherwise make both documents available to a capable coding or execution system and give it this request:

```text
Read URACE.md completely and treat it as the authoritative specification.
Read the companion bootstrap document as deployment context.

Bootstrap the smallest complete environment-appropriate URACE implementation
for the Product described in the companion document. Put generated
implementation files in one dedicated child boundary by default, keep durable
lifecycle state in a separate sibling or equivalent persistence boundary, and
do not scatter generated implementation files across the Product root.

Preserve the stated Intent, retained and delegated Authority, constraints,
protected Product artifacts, and selected self-evolution policy. Implement and
test persistent autonomous operation, measurable progressive follow-up,
observable feedback, a versioned confidence-qualified evolution evaluator,
goal/context/action cost-outcome evaluation, honest resource accounting,
concurrent-edit protection, interruption recovery, dormant wake paths, safe
runtime replacement and applicable re-bootstrap behavior. Repair failures before
reporting completion. Do not modify URACE.md unless the companion document
contains explicit applicable specification-evolution Authority.

Apply the selected external-metric policy. Use only authorized sources. Keep
credential values in the environment-appropriate secret mechanism and out of
prompts, generated documentation, logs and durable lifecycle state. Demonstrate
configured source readiness where possible and report unavailable sources.

Finish with the complete bootstrap report required by URACE.md, including what
was implemented; generated boundaries; durable-state location; exact
initialization, inspection and persistent autonomous-start commands or
equivalent interfaces; governing Intent and retained/delegated Authority;
how governing configuration can be inspected and changed; active
self-evolution policy; Executor and Orchestrator readiness with real-invocation
results; external-metric policy, source readiness and observation limitations;
validation and behavioral-test results; progress profiles; evaluator version,
components, confidence and revision interface; dormant wake paths and
demonstrations; interruption, recovery and stale-ownership
results; context and goal inspection; resource units and proxy limitations;
concurrent-edit behavior; and every unresolved limitation, missing capability
or Authority uncertainty.
```

Do not execute `URACE.md` as if it were a program. The bootstrap capability reads the specification and creates the environment-specific implementation. Use the exact invocation reported by that implementation after bootstrap.

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

Bootstrap should demonstrate that configured Executors are actually available, authenticated where applicable, authorized to receive required context and produce required effects, and capable for their assigned Operations. If a real bounded invocation cannot be completed, bootstrap should report that limitation rather than claiming readiness from configuration or mock tests.

Bootstrap should also demonstrate concrete dormant wake paths, a material capability transition that triggers reassessment where applicable, interruption recovery before effects, during partial application, after effects but before durable acceptance, and after acceptance but before cleanup, plus safe reconciliation of any stale locks, leases, or ownership markers. Inapplicable cases should be reported explicitly rather than silently skipped.

Bootstrap should demonstrate bloat protection as behavior: unchanged cycles do not append duplicate observations or checkpoints, external polling is proportionately cached, active state has bounded retention or archival semantics, and oversized candidate changes require justification or a smaller route.

### Default Artifact Boundaries

When specification, implementation and state share one artifact tree, bootstrap should place the generated implementation inside one clearly named child folder by default. It should not scatter generated implementation files or multiple implementation folders across the Product root.

Durable lifecycle state should occupy one separate sibling folder or an equivalently independent persistence boundary so implementation replacement and re-bootstrap cannot erase it. Conceptually:

```text
PRODUCT ROOT
├── AUTHORITATIVE SPECIFICATION
├── <DEDICATED IMPLEMENTATION>/
├── <DEDICATED LIFECYCLE DATA>/
└── USER PRODUCT ARTIFACTS
```

The exact folder names are deployment choices. The layout may differ for installed packages, services, containers, separate repositories, non-filesystem persistence or existing Product structures that already provide equivalent isolation. The required behavior is one independently replaceable implementation boundary, one independently preserved lifecycle-state boundary, and no silent replacement of the authoritative specification or accepted Product artifacts during runtime replacement or re-bootstrap.

### Apply Meta-Implementation Practically

Start with the lifecycle contracts and observable behavior required by `URACE.md`, then implement the smallest clear mechanism that satisfies them. Keep provider-specific behavior behind replaceable adapters and policy in inspectable configuration. Do not build a universal framework for hypothetical future providers before a real second implementation or repeated change pressure justifies the abstraction.

Use progressive disclosure for people operating the result: first show safe defaults and exact inspect, attach, detach and run actions; place adapter internals, recovery protocols and advanced policy behind deeper documentation. This applies the meta-implementation principle at system-design level while keeping ordinary use understandable.

### Small surface, complete behavior

Compress the **operating surface**, not the safety model. Short commands, generated defaults, progressive disclosure and one report bundle can make the system easy to use while the specification retains Authority, Evidence, transaction, recovery and audit semantics. Remove duplicate prose, state and adapters when their behavior is provably covered elsewhere. Do not merge distinct concepts, hide uncertainty in one score or delete a guardrail merely to reduce file count. A feature earns its place when it protects an invariant or serves demonstrated use; otherwise keep it optional, defer it or remove it with migration Evidence.

### Bloat Protection

Long-running implementations should suppress duplicate unchanged observations and checkpoints, cache proportionately, summarize or archive repetitive history, and apply explicit complexity and growth budgets to candidate changes. They must preserve accepted decisions, material Evidence, unresolved effects and recovery integrity while doing so. More files, lines, features, metrics or state are costs to justify, not evidence of progress.

Resource use should be reported with honest units. Prefer provider-reported cost, then reported tokens or metered units, then a clearly labelled model-call proxy. Cycles, availability probes, network collections, storage and writes are useful deterministic resource measures, but they are not provider credits. Availability means that an Executor appears ready; it does not reveal its remaining paid balance. Keep dimensions separate when no defensible conversion exists.

URACE should continuously look for resource sinks: repeated no-effect calls, stale goals, unused context or connectors, uninformative metrics, retry storms, oversized prompts, redundant reports, excessive state growth and self-improvement that does not advance the Product. Correcting a sink still requires Authority, validation and measurable follow-up. Cheap operation is not efficient when it produces weak or unsafe results.

Credit-consuming AI calls should be trigger-first, durably counted and capped. Fast autonomous cycles may perform local checks without calling a model. A low-frequency opportunity audit can still discover improvements when no event occurs, while unchanged dormancy should not spend credits repeatedly. Usage feedback should expose recent calls, limits and budget exhaustion so persistent autonomy cannot silently become a credit-burning polling loop.

The budget should cover the complete AI workflow, including discovery, execution, retries, failures and any model-assisted validation. Persist each call reservation before invocation so interruption cannot reopen that budget. A discovery should reserve enough budget to execute an accepted proposal. Use both burst and long-window limits, suppress duplicate triggers, and progressively back off low-value opportunity audits after no-action, ineligible, failed or no-effect results. Keep prompts bounded and decision-relevant instead of repeatedly sending unbounded history. Report calls by stage and outcome, both budget windows, the current backoff and why a call was delayed. These controls let long-running installations measure and improve value per call while retaining a hard user-configured ceiling.

Treat executor cost versus measurable progress as a core vital over both short and long windows. Report productive-call yield, accepted changes, cost per accepted change, and associated metric improvements or regressions. Prefer actual provider token or monetary usage when available; clearly label call count when it is only a cost proxy. Keep the association unattributed unless stronger causal evidence exists, since a nearby metric change may have another cause.

“Optimal” means the best defensible eligible choice from current Evidence and constraints. Product work and permitted URACE self-improvement should share a bounded comparison of expected value, progress contribution, urgency, confidence, cost, risk, reversibility and learning value. Self-evolution policy applies before ranking. This avoids automatically favoring self-work, feature volume or the newest idea while remaining honest that future Evidence can change the choice.

Evolution rate is also a core vital. Treat its overall score as a diagnostic summary, never as the goal itself. Show the component values behind it: productive credit yield, accepted-effect rate, regression safety, goal completion, and relevant Product outcomes when available. Report short and long windows, Evidence volume and confidence. With too little Evidence, show no score or low confidence instead of a reassuring number.

Evaluate goals, supplied context, Product changes and URACE self-improvements separately against their observed outcomes and costs. Keep those links explicitly unattributed until stronger Evidence supports causality. This reveals expensive goals, unused context and unproductive self-work without claiming that a nearby metric change was caused by them.

The evaluator can evolve too. Keep its component definitions, weights, minimum Evidence threshold and version visible, and retain every before/after revision. Changes follow normal Authority, validation and checkpoint rules and should be checked for gaming, proxy drift, lost historical comparability and added measurement cost.

Efficiency also covers local overhead. Long-running implementations should adapt readiness probes and failing external-source retries, reuse unchanged Plans, suppress duplicate checkpoints, and persist unchanged dormant state on a heartbeat instead of every fast assessment. Material input, decisions, effects and recovery information remain immediately durable. Vitals should expose state growth and suppressed writes so these optimizations remain measurable rather than assumed.

Reasoning memory should store structured reusable hypotheses rather than raw conversations or hidden chain-of-thought. Useful entries include supporting Evidence, counter-Evidence, confidence, applicability, last observation and a concise learned response. Entries should be revised or retired when contradicted, and retention should be bounded by value so the memory system does not become another source of bloat.

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

A normal first-use sequence is:

1. Inspect the bootstrap report and confirm the generated implementation and lifecycle-state boundaries.
2. Run the reported initialization command if bootstrap did not already initialize durable state.
3. Run the reported inspection command and verify Intent, Authority, self-evolution policy, Executor readiness, measures, blockers and next follow-up.
4. Run one bounded autonomous cycle to demonstrate the real execution path and feedback without treating that bounded run as lifecycle termination.
5. Start the reported persistent autonomous command. Keep any required process supervisor or service active when continuity across process or machine restarts is desired.

If the reported command is missing, fails before showing lifecycle state, or differs from the examples below, use the bootstrap report as the source for the environment-specific invocation and ask the bootstrap capability to repair or explain the mismatch. A missing command means bootstrap is incomplete or that capability is unsupported; it is not a reason to guess module paths or edit durable state manually.

## Attach, Remove or Switch an Executor

The AI or Orchestrator that performs bootstrap is not automatically trusted forever merely because it created the implementation. Bootstrap should retain it as the first Executor only when it is compatible with the generated capability contract, authorized to receive the required context and produce the required effects, and demonstrated with a bounded real invocation.

The bootstrap report must give exact environment-specific steps equivalent to:

```text
# See what is attached and whether it works
urace executor status

# Queue attachment of an available supported Executor
urace executor attach

# Queue detachment without deleting history
urace executor detach
```

Attach and detach requests should use durable input when persistent autonomy may be active, then apply at the next safe boundary. Some implementations may use a settings screen, service configuration, API or adapter file instead of these example commands. The user should not need to guess provider flags, edit lifecycle internals, or understand orchestration architecture. Attaching any capable system depends on an available adapter and its current interface; a product label alone does not prove compatibility. The implementation should validate availability, authentication, permissions, supported Operations and one bounded invocation, then report readiness plainly.

Removing or switching an Executor preserves Intent, Authority, accepted history and unresolved-effect reconciliation. If no suitable Executor remains, URACE stays safely dormant or blocks only work that needs it. Adding a different Executor does not transfer lifecycle ownership or expand Authority.

Conceptually, an implementation may expose:

```text
# Inspect lifecycle state
urace check

# Inspect progress, credit usage, efficiency, and health
urace vitals
urace vitals --json

# Assess, discover, prioritize, and plan
urace plan

# Run persistent autonomous lifecycle operation
urace autonomous
```

The command boundary should be explicit:

| Immediate command | Purpose |
|---|---|
| `urace init` | Initialize lifecycle state safely. |
| `urace check [--json]` | Read complete durable state without waiting for a persistent run. |
| `urace vitals [--json]` | Read focused metrics, credit usage, efficiency and health. |
| `urace evaluation show [--json]` | Inspect evaluator version, components, confidence and goal/context/action evaluations. |
| `urace report status [--json]` | Inspect portable and native-workbook export readiness without advancing lifecycle state. |
| `urace report export --output PATH` | Export the portable analytics bundle. Use an optional native-workbook mode only when bootstrap reports it as ready. |
| `urace portfolio ...` | Use an optional installed portfolio helper for isolated variants; availability is deployment-specific. |
| `urace commands [--json]` | Show immediate versus durable-input actions. |
| `urace inbox list [--json]` | Inspect pending durable input. |
| `urace context list [--json]` | Inspect governing, user-supplied and URACE-derived context with provenance. |
| `urace executor status` | Inspect Executor readiness without a model call. |
| `urace source\|metric\|vital\|goal list [--json]` | Inspect applied definitions or goals. |
| `urace policy list`, `budget show` | Inspect autonomy modes and metered limits. |
| `urace plan [--json]` | Assess, discover, prioritize and create a Plan without execution. |
| `urace autonomous ...` | Execute bounded or persistent lifecycle cycles. |

| Durable input command | Purpose |
|---|---|
| `urace add-context`, `add-goal` | Add attributable context or an Objective candidate. |
| `urace add-source`, `add-metric`, `add-vital` | Add observability definitions. |
| `urace source enable\|disable\|remove ID` | Change a connector at the next safe boundary. |
| `urace metric\|vital remove NAME` | Remove an observability definition safely. |
| `urace goal cancel ID` | Cancel an eligible pending goal while retaining history. |
| `urace executor attach\|detach` | Change future Executor selection at the next safe boundary. |
| `urace policy set NAME VALUE` | Change self-evolution, external-metric or analytics-export policy safely. |
| `urace evaluation set-weight COMPONENT VALUE` | Queue an audited component-weight revision. |
| `urace evaluation set-minimum COUNT` | Queue an audited minimum-Evidence revision. |
| `urace budget set --daily N --monthly N` | Change short-run and long-run model-call ceilings safely. |

Equivalent APIs or settings screens are valid. Read-only commands should use atomic snapshots and remain available while persistent autonomy runs. Configuration changes should use durable input so interruption cannot leave half-applied state.

You may keep prompting an attached AI, use an IDE, run external tools or edit the Product while autonomous operation is active. A resilient implementation compares each artifact with the exact base used to prepare its candidate. If another edit arrived first, URACE preserves it and reassesses or rebases instead of overwriting it. Use the durable context and goal commands when the information should explicitly enter lifecycle governance; ordinary file changes remain Product Evidence and do not silently expand Authority.

This includes authorized edits to `URACE.md` while URACE runs. Direct specification edits remain subject to retained specification Authority and validation. A runtime-prepared specification candidate based on an older version is rejected or rebased; it does not overwrite the newer edit. Runtime implementation changes remain a separate scope governed by the configured self-evolution policy.

The already-running executable cannot safely rewrite its in-memory code in place. A resilient self-update prepares and validates a candidate away from the live runtime, checkpoints state, reaches a safe cycle boundary, hands ownership to the candidate process, verifies startup health and restores the stable runtime if activation fails. Queue such work as a URACE-targeted goal rather than editing loaded runtime files directly. For example:

```bash
urace add-goal "Upgrade the runtime adapter" \
  --target urace \
  --success-measure "The new adapter passes compatibility and restart recovery tests" \
  --necessity-evidence "The current adapter blocks an authorized Product operation" \
  --lower-impact-insufficient
```

Under `necessary-only`, the necessity Evidence and absence of a sufficient lower-impact route are required. Under `continuous`, a justified beneficial candidate may be eligible. Under `disabled`, runtime self-update remains unavailable while Product evolution continues.

Where a CLI exposes cycle limits, it may use equivalent persistent forms such as:

```text
urace autonomous
urace autonomous --cycles 0
urace autonomous --cycles infinity
```

A positive integer runs a bounded number of cycles for demonstration, diagnosis or supervised operation:

```text
urace autonomous --cycles 10
```

Finishing a bounded invocation does not terminate URACE's durable lifecycle ownership.

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

`urace check` may expose:

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

Use the implementation's vitals interface for a focused operational view of progress metrics, Executor credit usage, short-run and long-run cost efficiency, external-evidence health, blockers, unresolved effects and the next follow-up. A CLI implementation should provide commands equivalent to `urace vitals` for people and `urace vitals --json` for monitoring. Reading vitals should be local and must not spend Executor credit.

## Add context, goals, metrics, and sources while URACE runs

A generated implementation should provide simple commands, an API, or a settings screen for adding authoritative context, goals, metrics, vitals, and connector descriptions without editing lifecycle state. Inputs should be durably queued and applied exactly once at a safe cycle boundary, so they survive process interruption and work while autonomous mode is active or between sessions.

Conceptually, a CLI may expose:

```text
urace add-context "Customers need CSV export"
urace add-goal "Deliver CSV export" --success-measure "A user can download a valid CSV"
urace add-source product-outcomes http_json https://example.test/metrics --credential-env PRODUCT_METRICS_TOKEN
urace add-metric successful_exports --source product-outcomes --path totals.exports --direction nondecreasing --target 100
urace add-vital export_success_rate --numerator successful_exports --denominator export_attempts --window 30d
urace context list
urace context list --json
urace goal list
urace vitals
```

Management remains equally explicit:

```text
urace inbox list
urace source list
urace source enable product-outcomes
urace source disable product-outcomes
urace source remove product-outcomes
urace metric list
urace metric remove successful_exports
urace vital list
urace vital remove export_success_rate
urace goal list
urace goal cancel OBJECTIVE_ID
```

Context becomes attributable Evidence rather than silently replacing Intent. A goal becomes an Objective candidate with an explicit success measure. A goal targeting URACE itself remains separate from the Product goal and respects the selected self-evolution policy. A vital may expose one named metric directly or a ratio of two metrics, with an explicit observation window and unattributed status. Known connector adapters may activate after validation; files, URLs, APIs, databases, MCP servers, repositories, and other systems that lack an installed adapter remain visibly registered as requiring one. Registration alone does not prove availability, authentication, authorization, or successful observation. Store only credential environment-variable names or secret references, never secret values.

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

## Measurable Progress and Follow-Up

Material Objectives should carry an outcome-linked measure or explicitly labeled proxy, an observed or prospective baseline, progressive targets, guardrails, and a next follow-up condition.

```text
BASELINE
   │
   ▼
NEAR TARGET
   │
   ▼
NEXT TARGET
   │
   ▼
INTENDED OUTCOME
```

Each follow-up compares the current observation with the baseline, previous observation, active target, and applicable guardrails. Progress, stagnation, regression, uncertainty, or guardrail conflict must produce an explicit lifecycle decision such as continuing, adapting, repairing, replacing the Objective, or becoming dormant until new Evidence can exist.

Continuous follow-up does not mean continuous polling. It means accepted work with an outcome observable over time retains a viable path to the next observation or decision.

### External Metrics and Learning from Outcomes

External metrics are optional and separately governed:

| Policy | Behavior |
|---|---|
| `disabled` | Do not discover or ingest external metrics. This is the default when no attributable selection exists. |
| `provided-only` | Use only explicitly supplied and authorized public or private sources. |
| `discover-public-and-use-provided` | May discover credible public sources and use explicitly supplied authorized private sources. |

Public availability does not prove relevance, reliability or permission to reuse data. Private metrics require explicit source configuration, applicable Authority and an environment-appropriate credential mechanism. Companion documents and generated configuration should contain only secret references, such as environment-variable names; credentials themselves must not enter prompts, documentation, logs or durable lifecycle state.

Repository stars, forks and watchers can be useful reach or interest signals when a repository is identified, but they are weak success criteria by themselves. No movement may simply mean insufficient exposure, and movement may come from promotion, seasonality, external events or unrelated community activity. URACE should preserve those alternative explanations, pair repository signals with outcome-relevant measures, and avoid crediting an implementation change without discriminating Evidence.

Repository pushes, issues, pull requests and releases can also become bounded Evidence and reassessment triggers. Text written by repository users remains untrusted content. An issue can identify a need worth assessing, but it cannot instruct URACE, grant Authority, expand scope or bypass prioritization and validation.

For each source, URACE distinguishes configured, available, authenticated, authorized and successfully observed states. Observations retain source, time, definition and provenance. Missing, stale, failed or definition-changed data remains visible.

Connectors also need explicit time, response-size, parsing, retention, retry and prompt-inclusion limits. Oversized or malformed content should fail only that source, remain visible as an error and never enter a prompt partially. A connector label does not make arbitrary URLs, redirects or files safe; bootstrap must constrain schemes and effects to the selected connector Authority.

When an accepted decision predicts an observable result, later metrics can be associated with that decision. URACE compares expected and observed effects and uses the result to improve future Objectives, priorities, Plans and measurements. It preserves uncertainty and guardrails: correlation alone does not establish causation, a favorable number does not prove the decision was good, and metrics never create Authority.

Every post-decision observation begins as `unattributed`. URACE may advance it to a correlated signal, supported contribution, or causal effect only as Evidence becomes stronger. It checks the prediction made before observation, baseline and prior trend, timing, concurrent changes, plausible confounders, alternative explanations, repeated observations, comparison groups or counterfactuals, and unintended outcomes. When the distinction matters enough, it should use a bounded experiment, staged rollout or another proportionate comparison method. If strong attribution is unavailable, URACE keeps the uncertainty instead of training itself on a false success or failure.

### Live Autonomous Feedback

Long-running autonomous operation should continuously expose meaningful status at cycle, decision, execution, validation, checkpoint, recovery and lifecycle-transition boundaries. Feedback includes what URACE is doing, why it is doing it, what happened, current measures and trends, executor availability, blockers, and the next follow-up or wake condition.

When self-evolution could be relevant, feedback also exposes the active `disabled`, `necessary-only`, or `continuous` policy and records why a runtime or re-bootstrap proposal was eligible or rejected.

Human-readable feedback should remain concise and understandable. Machine-readable event output may support monitoring and integration. When both are enabled, implementations should keep the machine stream parseable, such as JSON Lines on stdout with human feedback on stderr; a quiet option may suppress the human stream without suppressing machine events. Unchanged dormant checks may be compacted, but material work, failure, rollback or deterioration must not be hidden by silence.

Human feedback should show the reviewable decision chain: what was selected, the Evidence and Authority supporting it, the alternative classes considered, the Plan, validation, observed effects, changed artifacts, uncertainty and next condition. It should not expose private hidden chain-of-thought or secret scratch reasoning. Clear rationale, provenance and decision records provide useful explanation without requiring raw internal reasoning tokens.

URACE also reviews the metric system itself. When measures become stale, gameable, expensive, insensitive or no longer useful for decisions, improving the measures may become justified work. Prior definitions, baselines and provenance remain preserved so changing the measurement system cannot manufacture progress.

### Metrics, vitals, and scores

A **metric** is an observed measure. A **vital** interprets metrics and durable state to describe health, progress, efficiency or risk. A **score** is a versioned decision aid built from named metrics or vitals. They are related and remain distinct so an aggregate cannot conceal its inputs.

An overall score is reported only when its required dimensions have enough Evidence and no guardrail veto applies. The system scorecard keeps outcome progress, Evidence quality, safety and continuity, and resource efficiency visible beside their confidence and source. Its aggregate is withheld when coverage or confidence is insufficient. No score grants Authority, proves causation, accepts a change or overrides a failed guardrail.

### Portable analytics and system scorecard

Tabular and visual analysis is an optional observation surface. Bootstrap should ask for `disabled`, `on-demand` or `on-checkpoint` export and use `disabled` when no choice is supplied. URACE's canonical state and autonomous control never read decisions back from an exported table, workbook or dashboard, so a missing, stale or edited report cannot steer or stop the system.

When the generated implementation supports it, export an atomic report bundle:

```bash
# Check portable and optional native-workbook readiness separately
urace report status

urace report export --output path/reported-by-bootstrap

# For a native workbook, use the optional flag reported by bootstrap
urace report export --output path/reported-by-bootstrap <reported-native-workbook-flag>
```

The portable bundle contains interoperable tables, a self-contained human-readable dashboard, a schema/version manifest, source state version and content hashes. It should open with common analysis tools without requiring a proprietary product. A native workbook is an optional derived convenience and never a dependency. Bootstrap detects its adapter rather than silently assuming or installing it, reports `READY` or `ADAPTER_REQUIRED`, and gives the exact authorized enablement path. An unavailable native export must leave the last successful report intact and cannot affect autonomous control. Potential formula cells are escaped so imported Evidence cannot become executable spreadsheet content.

The export covers progress metrics, scorecard dimensions, Executor usage, objectives, work evaluations, external observations, reasoning patterns and, when present, portfolio variants, events and Agora records. Export again after material activity for a current snapshot; an environment may safely automate that same read-only export after accepted checkpoints. The manifest's state version and generation reveal staleness. Use the dashboard to inspect trends and drill into CSV history, then make changes through URACE's normal commands or durable input boundary rather than editing the report.

The generated usage report must give the exact policy command or setting for enabling, disabling and selecting checkpoint refresh. For a command-line implementation, the shape may be `urace policy set analytics-export disabled|on-demand|on-checkpoint`; use the exact command reported by bootstrap.

---

## Run Autonomous Product Evolution

```text
urace autonomous
```

`--cycles infinity` may be used when an explicit persistent-cycle value is preferable. Omit `--cycles` for the shortest equivalent command; use a positive integer only for a bounded run.

Choose `necessary-only` in the bootstrap companion configuration to keep Product improvement continuous while allowing URACE to repair or reconstruct itself only when a demonstrated runtime limitation materially blocks, degrades, or endangers progress or continuity and no sufficient lower-impact route exists. The implementation must durably expose the selected policy; the exact configuration syntax is environment-specific.

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

URACE distinguishes an Executor that is configured from one that is available, authenticated where applicable, authorized for the required context and effects, and capable for the particular Operation. These states are not interchangeable.

Where unavailable capability blocks justified work, an unavailable-to-available transition may become a meaningful Trigger and wake dormant operation. Unchanged unavailability should be deduplicated or rate-limited rather than causing costly retry loops.

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

A recorded wake condition is insufficient by itself. A Scheduler, watcher, callback, bounded poller, external trigger mechanism, or equivalent durable responsibility must be able to observe the qualifying change and cause reassessment.

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

## Crash-Consistent Acceptance

For changes spanning multiple artifacts or the Product/lifecycle-state boundary, per-file atomic writes are insufficient. URACE preserves enough durable before/after information to recover one coherent accepted state.

After interruption, effects not represented by an accepted checkpoint are rolled back, compensated, or kept explicitly `INDETERMINATE`. Effects already represented by an accepted checkpoint are completed or rolled forward when required for checkpoint consistency. Recovery disposition becomes Evidence.

Where practical, Executors prepare bounded candidate changes outside accepted Product state so URACE can validate them before commitment.

For continuity-critical artifacts, deployments should preserve a last-known-stable accepted version outside the mutable working copy. A candidate becomes the new stable recovery point only after validation and durable checkpoint acceptance. If interruption, corruption, broken structure, or protected-metric regression is detected, URACE restores the stable version or preserves explicit uncertainty when safe restoration cannot be established. The restoration becomes Evidence.

When `URACE.md` changes user-facing, operational, bootstrap, or integration semantics, `README.md` is reviewed and updated where needed in the same increment. The specification and its dependent guidance are validated, checkpointed, and restored as one coherent documentation version. If README text remains unchanged, the accepted decision should still record that consistency was reviewed.

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
