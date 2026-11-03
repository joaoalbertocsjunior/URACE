# URACE Runtime

This directory contains the running URACE implementation bootstrapped from [`../../URACE.md`](../../URACE.md). The implementation is replaceable, durable lifecycle state lives under the separate `../state/` boundary, and authoritative specification and guidance remain at the repository root.

## Public specification and local deployment matrix

“In sync” means this deployment implements the applicable portable behavior and invariants in `URACE.md`, while the public `README.md` explains them without copying deployment-only paths, credentials, state or mechanisms. It does not mean every public option is enabled locally or every local adapter belongs in the public package.

| Area | Public contract | This deployment | Sync status |
|---|---|---|---|
| Core purpose | Continuously improve the user's Product under retained Intent and Authority. | Uses the URACE public blueprint itself as the current Product. | In sync; Product identity intentionally differs per deployment. |
| Implementation | Environment-independent behavior and bootstrap requirements. | Python CLI, atomic JSON, filesystem inbox and Git-backed validation. | In sync; mechanism intentionally local. |
| Executor | Replaceable capable AI or orchestrator with inspect/attach/detach behavior. | Codex and Claude adapters with independent provider routing, replaceable through durable input. | In sync; provider choice intentionally local. |
| State and recovery | Durable checkpoints, transactional effects, interruption recovery and stable fallback. | Atomic state, transaction journal, stable documents and stable runtime. | In sync; paths intentionally local. |
| Concurrent edits | Preserve newer external edits and reassess stale candidates. | Source hashes and `CONCURRENT_CHANGE` rejection. | In sync. |
| Goals and context | Accept attributable live inputs at safe lifecycle boundaries. | Atomic inbox commands with deduplication and quarantine. | In sync. |
| Metrics and vitals | Extensible measures, confidence, causality limits and follow-up. | Structural measures, configured external metrics, custom vitals and qualified scorecards. | In sync; real Product outcomes depend on configured sources. |
| External evidence | Optional public/private connectors with secret references and untrusted-content handling. | JSON file, HTTP JSON and GitHub repository adapters; other kinds remain `ADAPTER_REQUIRED`. | Partially implemented by design; unsupported connectors remain explicit. |
| Resource accounting | Separate provider usage, proxies, availability and deterministic overhead. | Provider-reported token usage when available, explicit unknown usage, optional call ceilings, reservations and probe/write/source accounting. | Native usage is recorded when reported; subscription credit decrement remains unobservable. |
| Persistent autonomy | Bounded and infinite cycles share budgets, dormancy, wake, backoff and recovery. | Persistent cycles, material-write suppression and launcher restart requests. | In sync; no OS boot supervisor by owner choice. |
| Self-evolution | Explicit disabled, necessary-only or continuous policy with rollback. | `NECESSARY_ONLY`, validated runtime replacement and re-bootstrap support. | In sync; selected local policy. |
| Portfolio evolution | Optional isolated variants, equal caps, comparable evaluation, governed learning and ordinary promotion. | Git-worktree controller, frozen workflow, built-in URACE Product adapters, preflight/launch, resumable generations and retained lineage. | Ready for this deployment; other Products require validated adapters. |
| Anti-poisoning | No candidate ledger access, untrusted peer content, immutable rules, authenticated chain and fail-closed selection. | Bubblewrap removes host-state visibility; bounded schemas, same-generation votes, SHA-256 Agora chain and whole-ledger HMAC-SHA256 verification add defense in depth. | In sync on this Linux host; hostile multi-tenant operation should use separate identities and an external broker. |
| Analytics | Optional derived portable export that never controls lifecycle state. | Automatic checkpoint CSV/HTML bundle and enabled native-workbook adapter in an isolated local environment. | In sync; local policy is `ON_CHECKPOINT`. |
| Commercial effects | Accountability, least privilege, exposure limits and no outcome guarantee. | Spending, publishing and destructive external effects remain reserved and no commercial adapter is enabled. | In sync; intentionally unavailable locally. |
| Packaging | Public source contains the specification, guide, license and public roadmap/configuration only. | Runtime, state, reports, secrets and deployment adapters remain ignored local artifacts. | Intentionally different and correctly separated. |

The remaining capability gaps are explicit rather than synchronization defects: provider-reported usage can be missing, and actual subscription credit decrement is unavailable; mutually hostile candidates need an external authenticated broker and harder isolation; and unsupported connector types need adapters. None is represented as ready. Native workbook export is enabled locally and remains observational.

## Governing configuration

The retained destination is to continuously improve the URACE blueprint while preserving its governing invariants. The repository owner retains the purpose, Authority boundaries, and normative invariants. Assessment, objectives, priority, plans, measurement, validation, and local implementation changes are delegated. External publication, spending, destructive external effects, changing the retained purpose, and weakening normative invariants remain reserved.

The bootstrap request authorizes this implementation. It does not grant a runtime permission to broaden Authority.

## Run

Requires Python 3.11 or later and no third-party runtime packages.

```sh
cd /path/to/project/runtime
python3 -m urace init
python3 -m urace help
python3 -m urace help autonomous
python3 -m urace check
python3 -m urace vitals
python3 -m urace vitals --json
python3 -m urace commands
python3 -m urace inbox list
python3 -m urace plan
python3 -m urace autonomous --cycles 1
python3 -m unittest discover -s tests -v
```

Install the `urace` command from the project root if desired:

```sh
cd /path/to/project
python3 -m pip install -e runtime
urace check
urace vitals
```

Both `python3 -m urace` and the repository-local `urace` command enter the same launcher, so supervised runtime activation and rollback apply to either form. This deployment keeps its launcher at `urace/.urace/bin/urace`; `direnv` loads `.envrc` to add it to `PATH` only inside this repository tree and removes it on exit. A new terminal loads the hook automatically. The portable fallback is `./urace/.urace/bin/urace ...`.

## Command boundary

Immediate inspection commands load atomic snapshots and remain usable while autonomous infinity owns lifecycle mutation. The report command only writes a derived export boundary:

```sh
python3 -m urace help [operation]
python3 -m urace check [--json]
python3 -m urace vitals [--json]
python3 -m urace commands [--json]
python3 -m urace inbox list [--json]
python3 -m urace executor status
python3 -m urace source list [--json]
python3 -m urace metric list [--json]
python3 -m urace vital list [--json]
python3 -m urace goal list [--json]
python3 -m urace goal inspect OBJECTIVE_ID [--json]
python3 -m urace update resolve [GOAL_ID_OR_CANDIDATE_HASH] --decision "retain local choice and adopt compatible changes"
python3 -m urace goal forecast [--json]
python3 -m urace change list [--json]
python3 -m urace change explain CHANGE_ID [--json]
python3 -m urace configuration [show|self-evolution|change-explanations] [VALUE]
python3 -m urace self-evolution [status|auto|always|never]
python3 -m urace policy list [--json]
python3 -m urace budget show [--json]
python3 -m urace report status [--json]
python3 -m urace report export --output urace/generated/reports/latest [--xlsx]
```

Accepted operations retain a stable change ID, decision, changed files, validation result and exact Executor route. `change explain` reuses the task Executor's retained summary before spending another Executor call. Automatic explanations default to `disabled` (manual only); configure `auto` for value-gated generation or `enabled` for every eligible accepted change.

`plan` performs one assessment and may use a governed discovery call, but it stops after persisting an Objective and Plan and never invokes execution. `autonomous` owns execution. `init` creates initial state under the exclusive state boundary.

`urace vitals` is a read-only human summary of current progress metrics, 24-hour and 30-day Executor usage, efficiency yield, associated metric effects, external-evidence health, blockers and follow-up. `urace vitals --json` returns the same contract as structured JSON for monitoring and automation. Neither form invokes Codex or advances a lifecycle cycle. The JSON `progress_metric_source` identifies live Product measurement; while a transaction journal exists, vitals use the last durable measurements to avoid presenting a transient mixed-file view.

Queue new authoritative input safely, including while persistent autonomous mode owns the lifecycle state:

```sh
python3 -m urace add-context "Customers need CSV export" --source "repository owner"
python3 -m urace add-goal "Deliver CSV export" --success-measure "A user can download a valid CSV" --target product --priority 80
python3 -m urace add-goal "Improve recovery diagnostics" --success-measure "Recovery failures identify their failed phase" --target urace --necessity-evidence "Current failures block continuity" --lower-impact-insufficient
python3 -m urace add-source product-outcomes http_json https://example.test/metrics --visibility private --credential-env PRODUCT_METRICS_TOKEN
python3 -m urace add-metric successful_exports --source product-outcomes --path totals.exports --direction nondecreasing --target 100
python3 -m urace add-metric export_attempts --source product-outcomes --path totals.attempts
python3 -m urace add-vital export_success_rate --numerator successful_exports --denominator export_attempts --window 30d --description "Successful export share"
python3 -m urace source enable product-outcomes
python3 -m urace source disable product-outcomes
python3 -m urace source remove product-outcomes
python3 -m urace metric remove successful_exports
python3 -m urace vital remove export_success_rate
python3 -m urace goal cancel OBJECTIVE_ID
python3 -m urace goal prioritize OBJECTIVE_ID --priority 80 --floor 60 --ceiling 90
python3 -m urace goal schedule OBJECTIVE_ID --deadline 2027-02-01T00:00:00+00:00 --not-before 2027-01-01T00:00:00+00:00 --estimate-min-hours 2 --estimate-max-hours 6 --estimate-confidence medium
python3 -m urace goal pin OBJECTIVE_ID
python3 -m urace goal defer OBJECTIVE_ID --until 2027-01-01T00:00:00+00:00
python3 -m urace goal resume OBJECTIVE_ID
python3 -m urace goal disable OBJECTIVE_ID
python3 -m urace goal delete OBJECTIVE_ID
python3 -m urace policy set self-evolution necessary-only
python3 -m urace policy set external-metrics provided-only
python3 -m urace budget set --daily 2 --monthly 12
```

Each command atomically writes a small inbox item without waiting for or mutating the live state lock. The autonomous owner consumes items at the next cycle boundary, saves their IDs with the resulting state, and removes their files only after that save. A crash before save leaves the input queued; a crash after save is deduplicated by its processed ID. Corrupt inbox JSON is quarantined instead of blocking the lifecycle. Context is retained as attributable Evidence and supplied in bounded form to discovery. Product and URACE goals become prioritized Objective candidates; URACE-targeted work still follows Authority and self-evolution policy.

The installed source adapters are `json_file`, `http_json`, and `github_repository`. Other source kinds, including `database`, `mcp`, and provider-specific APIs, can be registered with `add-source` but remain `ADAPTER_REQUIRED` and inactive until a compatible adapter is implemented and validated. `add-vital` exposes a named metric directly or divides a numerator metric by a nonzero denominator metric; unavailable inputs remain visible rather than becoming fabricated values. `--credential-env` stores only the environment-variable name. Do not put a credential value in a command or source location. `urace vitals --json` lists registered connectors, metric and vital definitions, observed values, evaluated vitals, and collection errors.

External JSON files and responses are limited to 1 MiB per request, and HTTP sources accept only `http` or `https` locations. Timeouts, bounded repository event counts, adaptive retry backoff, duplicate-error suppression and bounded prompt inclusion prevent a connector from becoming an unbounded memory, storage, credit or prompt sink. Oversized or malformed input fails only its source and remains visible as an error.

Specification updates are staged and hash-bound:

```sh
python3 -m urace update download /path/to/new/URACE.md
python3 -m urace update explain
python3 -m urace update apply
```

`download` accepts a local file or HTTPS source, validates structure and size, and stores an isolated candidate without changing accepted files. `explain` produces a deterministic no-effect delta report and uses no Executor. `apply` validates the candidate again and queues one digest-bound migration Objective; autonomous execution then uses the configured Executor pool to build the isolated candidate and the existing independent validation, activation health check and stable rollback path. It never patches `state.json` or live runtime files directly.

Inspect or queue changes to local Executors without editing state files:

```sh
python3 -m urace executor status
python3 -m urace executor attach
python3 -m urace executor detach
```

Attach additional Codex or Claude CLI Executors with stable identities and task-specific priorities:

```sh
python3 -m urace executor attach --id codex-secondary --command /path/to/codex --priority 90 --max-calls-24h 100 --max-calls-30d 1000
python3 -m urace executor attach --id claude-secondary --adapter claude-cli --command /path/to/claude --priority 90 --capability-priority planning=105 --capability-priority evaluation=110
python3 -m urace executor retry-policy --id codex-primary --retry-mode automatic --retry-delay-ms 60000 --retry-fallback-seconds 18000
python3 -m urace executor detach --id codex-secondary
```

Each provider declares capabilities from `discovery`, `planning`, `mutation`, `evaluation`, and `execution`; repeat `--capability` to restrict an attachment and `--capability-priority CAPABILITY=INTEGER` to express task fit. A bounded suitability tolerance then chooses the least recently used Executor among materially equivalent options only while observed latency and resource evidence remain comparable; an outlier stays available as fallback instead of receiving calls merely for balance, and a material suitability lead still wins. The router exposes recent completions and keeps readiness, reset schedules, failures and transport attempts separately. An unavailable provider is skipped while another compatible provider may handle the same logical reservation. Cross-provider work remains a bounded replay unless an adapter proves session continuation. Every result passes the same output contract, guardrails and acceptance path; if all compatible providers are unavailable, the scheduler waits for the earliest eligible retry without erasing later schedules.

These commands are safe from a second terminal while core or portfolio autonomy continues. Core controls already use `urace/state/inbox`; the portfolio owner now consumes that shared inbox before planning and before each Executor stage. Portfolio `stop`, `record`, `review`, `agora-propose`, `agora-vote`, `agora-decide`, `agora-confirm-system`, and `lesson` run immediately when idle and become atomic queued controls when the persistent owner holds its mutation lock. `portfolio feedback` reports pending controls. Read-only `status`, `feedback`, `explain`, `rank`, `agora-show`, `commands`, `preflight`, and `verify` remain immediately available. Cohort creation, execution, manual selection and another autonomous owner are not queued because they would conflict with the active controller.

`status` is immediate and read-only. `attach` and `detach` enter the durable inbox, apply at the next cycle boundary, and preserve history, so they also work while infinity mode runs. A command must implement its selected adapter interface; other interfaces still require a validated adapter. Run `python3 -m urace commands` for the implementation's complete immediate-versus-input classification.

Durable state is written atomically to `urace/state/state.json`. The `urace/state/` boundary is preserved when `urace/runtime/` is replaced or reconstructed, and deployment state is intentionally ignored by Git. Runtime configuration is versioned in `urace/runtime/urace/config.json`. Runtime-created temporary directories, active portfolio workspaces, retained retired portfolio bundles, reports and update candidates are separated under `urace/generated/`.

## Capabilities and boundaries

The bootstrap supplies deterministic measurement plus Codex CLI as a bounded intelligent Executor. Codex first performs read-only discovery and returns a schema-validated proposal. URACE decides whether to promote that proposal into an Objective and Plan. A promoted Objective runs in an isolated temporary workspace with write access limited by its configured scope: documentation scope permits `URACE.md` and `README.md`, while eligible runtime or re-bootstrap scope permits only the explicitly allowlisted implementation and documentation files. URACE applies only changed allowlisted files, checks measurable guardrails, records the attempt and observed effect, and checkpoints an accepted change. Failed guardrails restore the pre-operation files.

Codex is enabled in `urace/config.json`, uses the locally authenticated Codex CLI, inherits its configured model by default, runs ephemerally, and has a 15-minute operation timeout. Ordinary 30-second cycles and authentication probes do not make model requests. Intelligent discovery is trigger-first, starts with a weekly opportunity audit when no material Trigger occurs, and backs that audit off exponentially after unproductive discoveries up to eight weeks. Equivalent triggers are suppressed for six hours. All discovery and execution attempts, including failures and no-effect outcomes, share hard ceilings of two calls per rolling 24 hours and twelve calls per rolling 30 days. Discovery requires two available budget slots, reserving the second for execution if its proposal is accepted. Set `executor.enabled` to `false` to use deterministic lifecycle behavior only. Model/API usage follows the account and configuration used by the local Codex CLI.

This deployment sets `self_evolution_policy.mode` to `NECESSARY_ONLY`. Product and documentation improvements remain eligible whenever justified. Changes to the URACE runtime itself, including re-bootstrap, are eligible only when Evidence shows that a runtime limitation materially blocks, degrades, or endangers progress, integrity, or continuity and no sufficient lower-impact route exists. Use `DISABLED` to opt out or `CONTINUOUS` to opt into justified beneficial runtime improvement. Policy changes belong in the versioned configuration with attributable provenance and must be migrated into durable state deliberately.

External metrics are separately configured under `external_metrics`. This deployment uses `DISCOVER_PUBLIC_AND_USE_PROVIDED`: intelligent discovery may identify credible public outcome sources, while ingestion uses only explicitly configured sources. Set the mode to `DISABLED` to opt out or `PROVIDED_ONLY` to prevent autonomous public-source discovery. Supported ingestion sources are local JSON (`json_file`) and public or authenticated JSON over HTTP (`http_json`). A source maps metric names to dotted paths in its JSON payload.

Private-source credentials are referenced by environment-variable name through `credential_env`; secret values are read only at collection time and are not persisted in configuration, prompts or lifecycle state. For example:

```json
{
  "id": "product-outcomes",
  "kind": "http_json",
  "location": "https://metrics.example.test/summary",
  "visibility": "private",
  "credential_env": "URACE_PRODUCT_METRICS_TOKEN",
  "values": {
    "successful_outcomes": "summary.successful",
    "failure_rate": "summary.failure_rate"
  }
}
```

Collected values, source identity, observation time and failures become Evidence and appear in autonomous feedback. Recent accepted decisions are recorded only as `UNATTRIBUTED` candidates; temporal proximity is explicitly insufficient. Codex receives the latest observations and examines pre-decision predictions, timing, prior trends, confounders, alternative explanations, comparison evidence, repeated observations and guardrails. When attribution matters, it should prefer a bounded reversible experiment. A correlated change may trigger investigation but cannot by itself classify a decision as good, bad or causally effective.

The configured public GitHub source is `https://github.com/joaoalbertocsjunior/URACE`, collected through its public repository API. It observes `stargazers_count` as stars, `forks_count` as forks, and `subscribers_count` as actual watching subscribers. GitHub's legacy `watchers_count` is intentionally not used because it represents stars. It also retains bounded metadata for repository pushes, recently updated issues, pull requests and releases. New or changed activity becomes an `EXTERNAL_REPOSITORY_UPDATE` reassessment Trigger. These values remain unattributed reach signals; promotion or unrelated external events may change them, and no movement does not prove that Product work failed.

Issue, pull-request and release titles are marked as untrusted content. They can trigger assessment but are never executed as instructions and cannot create Authority. The runtime retains stable identifiers, timestamps, state, title and URL rather than ingesting arbitrary bodies or comments into autonomous prompts.

Authenticate the executor once before autonomous use:

```sh
codex login
codex login status
cd runtime
python3 -m urace autonomous --cycles 1 --force-discovery
```

Authentication remains owned by the local Codex installation and is never copied into URACE state or configuration.

The initial measurable profile records normative-rule count, behavioral-test count, and unresolved-marker count. These structural indicators are guardrails and discovery signals, not claims of Product quality. Better outcome metrics should replace or supplement them when credible evidence becomes available.

Intent, Authority, constraints, measurements, decisions, checkpoints, unresolved effects, and lifecycle state are inspectable with `urace check --json`. Change retained Intent or Authority by editing the versioned configuration as the authoritative source, then migrate state deliberately. This deployment explicitly delegates bounded `URACE.md` specification evolution within the retained purpose, Authority boundaries, and normative invariants; it does not authorize weakening those invariants or publication.

Use `python3 -m urace context list` for a concise provenance-separated view or add `--json` for the complete governing, user-supplied and URACE-derived context. `python3 -m urace goal list [--json]` shows current and historical Objective candidates. User context queued with `add-context` is labelled `USER_SUPPLIED`; objectives, bounded reasoning hypotheses and external observations remain separately labelled derived material and do not silently replace Intent or create Authority.

The implementation enters `DORMANT` when no justified work exists while retaining a follow-up condition. An indeterminate effect moves it to `BLOCKED` until reconciled rather than permitting a blind retry.

Accepted multi-file changes use a durable transaction journal. URACE records complete before/after content and fsyncs the journal before touching Product files, atomically replaces each file, records the accepted transaction in durable lifecycle state, and only then removes the journal. On the next invocation, an interrupted unaccepted transaction is rolled back; a transaction already present in an accepted checkpoint is rolled forward. Recovery is recorded as Evidence. Stale process locks left by abnormal termination are reclaimed only when their recorded process is no longer alive.

The last accepted `URACE.md` and `README.md` are also retained under `urace/state/stable/`. Before operation and after recovery, URACE checks required document structure, fenced-block integrity, and non-regression of normative rules and behavioral tests. A broken or degraded live document is atomically restored from the last stable snapshot and the restoration is recorded as Evidence. A new snapshot is promoted only after Product validation and durable checkpoint acceptance.

Every intelligent discovery and execution request treats `URACE.md` as authoritative and requires review of `README.md` for synchronization. User-facing or operational semantic changes to the specification must update README guidance in the same accepted increment when needed; the two documents are checkpointed and restored as one stable Product version.

Candidate preparation records a SHA-256 base for every affected file. Immediately before application, the runtime compares each live file with that base. If an IDE, user, external tool or another authorized process changed a file meanwhile, the operation becomes `CONCURRENT_CHANGE`, the newer live content is preserved, the stale candidate is not applied, and the Objective returns to reassessment. This protects direct prompting and parallel project work without pretending the lifecycle lock controls unrelated editors.

The same protection covers `URACE.md` and `README.md`. An authorized owner may edit either while autonomous mode runs. Specification edits remain subject to specification-evolution Authority and Product validation; runtime implementation changes remain separately governed by `self_evolution_policy`. The reference runtime rejects a conflicting prepared candidate and reassesses it rather than attempting an automatic semantic merge.

The live Python process does not hot-patch already imported code. Runtime self-update uses an isolated candidate, the full test and state-compatibility checks, a durable restart request, launcher handoff, startup health confirmation and stable-runtime rollback. Queue it with `add-goal --target urace`; direct external edits to loaded runtime files are not equivalent to this validated handoff and take effect only in a later process.

Synchronization is intentionally partial. Portable lifecycle requirements and public usage semantics belong in `URACE.md` and the public README. This deployment's exact commands, paths, Codex adapter, caches, timeouts and state layout belong in this runtime README or local state guidance. A runtime change updates the public documents only when it reveals or changes a portable requirement; public files do not mirror every local implementation detail.

Codex discovery classifies a justified improvement as documentation evolution, incremental runtime self-evolution, or re-bootstrap. Runtime and re-bootstrap candidates are prepared in an isolated copy and must pass the complete candidate test suite plus configuration and durable-state compatibility checks before activation. The accepted runtime remains under `urace/state/stable-runtime/` until the candidate starts successfully.

`urace/runtime/urace/launcher.py` and `urace/runtime/urace/evolution_guard.py` form the local protected evolution kernel and are absent from every Executor mutation allowlist. Candidate preparation copies them only as validation dependencies and rejects any changed copy. The accepted guard compares protected Authority, constraints, self-evolution policy and Executor call ceilings; rejects mutable scopes containing kernel files; overlays the candidate runtime with the previously accepted tests from `urace/state/stable-runtime`; and runs those tests independently from candidate-editable tests. The already-loaded launcher repeats this guard after transactional application and before candidate startup. A failure restores the stable runtime. Kernel evolution is unavailable to ordinary self-repair and re-bootstrap and requires a separate attributable operator-controlled bootstrap and review.

Normal `python3 -m urace ...` invocation and the installed `urace ...` command run through a small launcher. When an accepted runtime candidate requests activation, the launcher lets the current child exit at a durable boundary and starts the candidate with the same autonomous arguments. If the candidate cannot import, start, load existing state, or complete activation health handling, the launcher restores the stable runtime, records rollback Evidence, and restarts it. The launcher owns only process handoff, health and rollback; URACE retains lifecycle ownership.

Re-bootstrap uses the same candidate, validation, state-preservation, supervised activation and rollback path. It may be selected only when reconstruction from `URACE.md` is more justified than an incremental runtime repair.

While `autonomous` remains running, dormant URACE checks a known-available local Codex installation every five minutes without making a model request. An unavailable Executor starts with a 30-second readiness cadence and backs off exponentially to 15 minutes after repeated failures. An unavailable-to-available transition is stored as an `EXECUTOR_AVAILABLE` Trigger and Evidence, clears the ordinary discovery cooldown, and causes immediate intelligent reassessment in that cycle. An available-to-unavailable transition is also durable. This is in-process wake behavior only; URACE does not install or depend on an operating-system supervisor and cannot restart itself after its process or machine stops.

Provider usage-limit and rate-limit responses are classified as `WAITING_PROVIDER_CAPACITY`, not task errors. Each Executor defaults to `automatic`: a reported reset date or local time is normalized, followed by the configured 60-second gap, and persisted; an unparseable or absent reset uses the local five-hour fallback. `fixed` deliberately uses that fallback. Change these independently with `executor retry-policy`. Readiness uses non-model authentication probes (`codex login status` or `claude auth status --json`). Interactive Claude `/usage` and `/status` output is not silently treated as a stable machine API; provider-reported usage is retained when a validated adapter returns it. Logical reservations remain separate from transport attempts, unavailable portfolio stages remain checkpointed, and recovery truthfully reports replay when no resumable provider identity exists.

From `urace/runtime/`, run the following for persistent lifecycle ownership with a 30-second assessment interval and the configured `NECESSARY_ONLY` self-evolution policy:

```bash
python3 -m urace autonomous --cycles infinity
```

`python3 -m urace autonomous`, `--cycles 0`, and `--cycles infinity` are equivalent persistent forms. Use a positive `--cycles N` for a bounded run and `--interval N` to change the interval. Stop a foreground persistent run with Ctrl-C; durable state has already been written after every completed cycle.

Autonomous mode prints concise lifecycle activity, changed files, validation and the next action after every completed cycle. Add `--verbose` for the full deterministic metrics and decision trace without an extra Executor call. With `--json`, JSON Lines are written to stdout while human feedback remains on stderr; `--quiet` suppresses only that human stream. Intelligent discovery periodically assesses whether the metric system remains relevant, decision-useful, regression-sensitive and resistant to gaming; justified metric-system changes use the normal Objective, validation and checkpoint path.

Human cycle feedback includes the selected action, decision basis, Authority, alternative class, validation status, Plan and changed files when applicable. JSON events include the same information under `decision_trace`. This is an attributable decision explanation, not hidden chain-of-thought.

When eligible goals exist, `candidate-comparison` reports up to five candidates with the priority, expected-value, urgency, confidence, estimated-cost and risk contributions behind the total diagnostic ranking score. Policy eligibility is applied before this ranking. The comparison supports review and does not convert estimated factors into facts or Authority.

Feedback reports `executor-credit-budget` with total model calls in rolling 24-hour and 30-day windows, the unproductive-discovery streak, configured limits and suppression or exhaustion status. The durable ledger identifies discovery or execution and records attempted, failed, no-action, ineligible, no-effect, Objective-created or accepted outcomes. A call reservation is written atomically before invoking Codex, so interruption during a request leaves a conservative attempted-call charge instead of silently reopening budget. `--force-discovery` records a unique manual trigger but bypasses neither ceiling nor the execution reservation. Execution calls occur only after a justified proposal becomes an Objective; unchanged dormant cycles do not call Codex. Discovery prompts bound structured reasoning memory to 20 entries, external observations to 10 entries and recent external errors to 10 entries while retaining governing documents, Intent and constraints.

The `resource_accounting` block uses provider-reported monetary usage when present, then reported tokens, otherwise `model_calls` with source `CALL_COUNT_PROXY`. This adapter currently falls back to model calls. It separately reports cycles, availability probes, external collections, durable writes and suppressed writes. Remaining 24-hour and 30-day call capacity is derived from configured ceilings and readiness; it is explicitly not a provider credit balance. These dimensions remain separate because the runtime has no defensible conversion among calls, cycles, probes and network collections.

Availability contributes to estimated usable capacity and delay, not Executor cost. `availability_probe_efficiency` compares probe count and duration with observed readiness transitions and reports suppressed redundant checks. This makes the probe useful in resource-versus-efficiency review while preserving its operational unit. Availability itself cannot reveal tokens, paid balance, price or consumption.

`resource_sink_indicators` counts unproductive model calls, context inputs that have not triggered discovery, open goals older than 30 days, Executor failures and the current external-source failure streak. `review_required` is a diagnostic prompt to investigate; it is not proof that an item lacks value and does not authorize automatic deletion.

Active protections include rolling call ceilings, completion-capacity reservation, adaptive discovery and source backoff, duplicate-trigger suppression, cached observations, bounded prompt context, material-change persistence, dormant heartbeats, write suppression, candidate-growth limits and stable rollback. Repeated identical Executor failures and blockers are now counted in one bounded record instead of growing state once per retry. The deployment-local portfolio controller supports isolated source worktrees and sequential bounded commands. It does not provide hard isolation for concurrently running services or external effects; those modes require a validated environment-specific adapter satisfying the public portfolio requirements.

This deployment exposes its generated isolated-worktree helper through `python3 -m urace portfolio ...`. The helper is deployment-local and is not required in the public bootstrap package. It records the shared contract, base snapshot, generation, parent, mutation hypothesis, expected effect, observations, resource cost, ranking and every selection disposition. `portfolio explain` is the concise human view and `portfolio status` is the complete JSON ledger. It manages candidate source worktrees and bounded commands, not persistent service processes or autonomous promotion. Use a validated container or process adapter when evaluation requires running instances.

Portfolio state and archives live under `urace/state/portfolio/`; reconstructable candidate worktrees live under `urace/generated/portfolio/`. The active workflow is `urace/state/portfolio-workflow.json`; `urace/runtime/portfolio-workflow.template.json` retains its reconstructable local shape. Its trusted built-in adapters plan bounded public-document alternatives, mutate only isolated public Product candidates and evaluate current structural guardrails plus a read-only evidence-based review. Planning is constrained to the files the mutation adapter may change, and a no-effect mutation fails explicitly. Other Products must replace these adapters with their own validated equivalents.

From the repository root, the concrete local setup shape is:

```bash
PYTHONPATH=urace/runtime urace/state/runtime-env/bin/python -m urace portfolio preflight urace/state/portfolio-workflow.json
PYTHONPATH=urace/runtime urace/state/runtime-env/bin/python -m urace portfolio autonomous \
  --workflow urace/state/portfolio-workflow.json --cycles 10
```

Replace `10` with the required positive generation count, or with `infinity` for persistent operation.

For persistent hands-off operation, the shortest full command is `PYTHONPATH=urace/runtime urace/state/runtime-env/bin/python -m urace portfolio launch urace/state/portfolio-workflow.json`. `launch` performs preflight again and refuses to run if adapters are missing, equal budgets are invalid, the frozen workflow changed, adapter call caps are unconfirmed or external effects are undeclared. The workflow, constitution and resource ceilings freeze on first use. Four candidates each receive equal 600-second and two-call hard ceilings per generation; planning receives one call. Every completed generation refreshes portable analytics and the native workbook.

The local built-in portfolio adapters use separate Git worktrees and invoke Codex with its read-only or workspace-write sandbox. This host uses the validated legacy Landlock sandbox because its private Bubblewrap path cannot configure loopback from the current terminal confinement. A bounded real probe confirmed workspace writes, denial of writes outside the candidate workspace and denial of candidate networking for the recorded Codex version; preflight refuses launch when that validation no longer matches the executable. A shared sandbox-startup failure becomes one scheduled capability wait and does not reject or charge every peer candidate. Executor login/readiness remains separate. Custom candidate commands require Bubblewrap with a new mount, PID, IPC, UTS, user and network namespace: only the candidate worktree is writable and visible as `/workspace`; host state, runtime, portfolio ledger, stable snapshots, other candidates and HMAC key are absent. Preflight runs a real confinement probe for that mode. The planner remains a trusted controller adapter outside candidate workspaces. These boundaries trust their sandbox implementation and host kernel; mutually hostile tenants warrant separate OS identities or machines and an authenticated submission broker.

`portfolio review` stores an attributable peer critique as advisory untrusted Evidence. `portfolio lesson` requires an explicit approver and records support, counter-Evidence, applicability and confidence; later `spawn --lesson ID` links rather than copies it. These commands change no Authority and cannot mutate, stop, select or promote a peer. The portfolio manifest is transactionally replaced for one trusted local operator, but it is not an authenticated multi-tenant broker.

The shared decision ledger is exposed as controller-side `portfolio agora-propose`, `agora-vote`, `agora-show` and `agora-decide` operations. Candidate processes cannot invoke this CLI or see its storage; an operator or separately authenticated broker attributes and submits their bounded outputs. Only variants admitted to the proposal's generation are eligible; each has one equal effective vote per proposal. Vote revisions preserve their predecessor, confidence does not change weight, and the tally exposes participation and dissent. Advisory fields are bounded. Proposals, votes, decisions and confirmations form a canonical SHA-256 chain, and every atomic save authenticates the complete portfolio ledger with HMAC-SHA256 using the owner-only `urace/state/secrets/portfolio-integrity.key`, created with mode `0600`. Every load verifies both layers before using the ledger. Tampering fails closed, and the test suite demonstrates detection. A controller records `adopt`, `defer` or `reject`. Adoption requires participation by at least half of eligible variants, the declared minimum support, strictly more support than opposition and a currently selected inheritance parent. It creates a surviving decision, not an instruction. A direct child of that winner must explicitly use `spawn --decision ID`; an unrelated parent or unadopted decision is rejected. The ledger never grants peer Authority or performs selection, mutation or promotion.

`portfolio cohort --count X --plan PLAN --total-resource-budget TOTAL --resource-unit UNIT` preflights a complete mutation plan, creates the cohort and divides the declared total equally. `portfolio run-cohort COHORT --timeout SECONDS --max-parallel X -- COMMAND` runs the same bounded command in every admitted worktree and supplies the allocation, unit, identity, cohort and port offset as `URACE_*` environment variables. Sequential execution is the safe default. For `wall_seconds`, the lower of the equal allocation and `--timeout` is enforced per candidate. CPU, memory, network, storage, accelerator and paid-service units remain explicitly declared until an environment adapter enforces them. Use a larger `--max-parallel` only with isolated resources, writable data, endpoints and effects for a defensible comparison.

Persistent `urace autonomous` supervises the initialized portfolio automatically; its separate authenticated ledger, policy, budgets and checkpoints remain intact. `portfolio policy adaptive|always|off` maps to the durable `auto|enabled|disabled` states. `portfolio autonomous --workflow FILE --cycles infinity` remains the explicit standalone form. The workflow supplies argument-array commands for planning, mutation and read-only JSON evaluation plus timeouts, equal budget, delay, backoff, failure ceiling and generation retention. Durable phases are `IDLE`, `PLANNED`, `CREATED`, `MUTATED` and `EVALUATED`. Rerunning the same workflow resumes its current phase; an interrupted or failed mutation is reset to its parent before retry. Successful source mutations are committed on their candidate branches, selection is limited to the current cohort, the winner seeds the next generation, and expired worktrees move to the portfolio archive. Normal `Ctrl-C` records interruption. After two identical eligible controller failures, the local workflow may request repair through ordinary `NECESSARY_ONLY` runtime self-evolution. The repair identity combines a controller-owned fault descriptor with the complete accepted runtime digest; its durable registry suppresses replay for that runtime version. Only the component, fixed fault code, trusted phase and exception class enter the request. Raw errors and cohort, candidate, peer, metric, Executor or connector content cannot steer it. Capacity, Executor availability, integrity, constitution, isolation and Authority failures never authorize repair. Core autonomous lifecycle faults use the same descriptor, version-keyed registry, isolated validation, transactional activation, launcher restart and stable rollback semantics. Failed or unavailable repair returns to bounded failure handling. External side effects still require an idempotent, reconciling environment adapter.

Before each built-in planning call, the controller attributes bounded attention weights to `README.md` and `URACE.md` from accepted-change recency and unresolved-marker debt. It converts those weights into explicit cohort plan counts, guarantees each scope one plan when cohort size permits, stores the versioned inputs and allocation in the authenticated ledger, and displays them in `portfolio feedback`. The primary scope guides planning but does not change equal candidate resources, Authority, guardrails, evaluation scores or selection. Candidates cannot write the controller-owned weights.

The same priority engine runs in ordinary autonomous lifecycle cycles. Local semantic scopes are Product guidance, authoritative specification, runtime implementation and measurement system; configuration maps them to execution scopes and artifacts. Inputs include open backlog, urgency, risk, unresolved debt, accepted-change recency and recent observed regressions. Every revision records target, previous and applied weights; an applied raw weight may move by at most `0.25` per revision and ranking influence remains capped. Bounded multipliers can reorder otherwise eligible Objectives, and `vitals` exposes inputs and weights. Eligibility, self-evolution policy, Authority and acceptance run independently and take precedence. The portfolio controller consumes the same engine to allocate public-document plan slots rather than maintaining a separate weighting policy.

Use `--cycles X` for exactly `X` completed generations and `--cycles infinity` for persistent operation. The local workflow requires `executor_invocation_budget_per_generation`, divides it equally, and durably increments each variant's usage before mutation or evaluation launch. `planner_invocation_budget_per_generation` separately permits one initial planning call plus one recovery attempt when the first outcome is failed or indeterminate. Reservations survive interruption and hard-cap exhaustion pauses immediately. These are hard controller-process invocation ceilings. Adapter-internal provider calls require their own metering gateway and provider/token/currency caps; availability and outer process counts do not measure them.

The local short commands are:

```bash
python3 -m urace portfolio auto urace/state/portfolio-workflow.json
python3 -m urace portfolio auto urace/state/portfolio-workflow.json --cycles 10
python3 -m urace portfolio next urace/state/portfolio-workflow.json
python3 -m urace portfolio feedback
python3 -m urace portfolio feedback --json
python3 -m urace portfolio commands
python3 -m urace portfolio preflight urace/state/portfolio-workflow.json
python3 -m urace portfolio verify
python3 -m urace portfolio launch urace/state/portfolio-workflow.json
```

`feedback` is read-only and makes the current activity, next phase, decisions, measurements, hard-cap consumption, errors, agora counts and material limitations visible without an Executor call. Persistent execution also prints each Executor stage when it starts, completes or fails, with an elapsed-time heartbeat every 15 seconds while it remains active. Failed attempts state their retry count and backoff; exhaustion states that the portfolio paused. These messages expose controller state rather than private reasoning and consume no additional Executor calls. The same human summary is emitted after each completed automatic generation. `commands` explains the short and explicit forms. `auto` applies a controller-only cost/value gate at idle generation boundaries: it gathers two comparison summaries, continues for material improvement or one bounded close-result follow-up, then becomes `DORMANT_AUTO`. A material accepted-Product, goal, workflow or policy change wakes it; `enabled` permits repeated comparison and `disabled` prevents new cohort work. The gate never interrupts an active generation. `next` completes one resumable generation.

A failed or no-effect candidate is recorded as a local loss and does not block its peers. Evaluation continues for candidates with completed mutations. If none survives, the generation records that outcome and retains the prior parent; it does not promote a failed candidate or retry the whole cohort merely to force a winner.

Candidate content is untrusted evaluation input. Candidates cannot modify the controller, frozen rubric, budgets, ledger or promotion boundary. Before model review, deterministic checks reject oversized diffs, excessive net growth and direct evaluator-manipulation language. The independent evaluator must ignore candidate instructions and self-declared scores or Evidence, compare observable changes against the parent and fail attempts to redefine metrics, guardrails, Authority or selection. Scores rank eligible candidates only; they never grant Authority or promotion.

Portfolio writes are fsync-durable and use an exclusive mutation-controller lock plus authenticated compare-and-swap protection, so another writer cannot replace a newer ledger snapshot. Read-only feedback remains available during autonomy. Archived variants and event segments use authenticated envelopes and are verified by preflight and `portfolio verify`. The live Agora has a 10,000-record ceiling; reaching it closes further submissions until the authenticated experiment is deliberately closed and replaced, preventing indefinite live-ledger growth.

Variants may submit `agora-propose --scope portfolio-system` only with necessity, experiment-wide-benefit and preserved-invariant evidence. A supported `agora-decide --outcome refer` sends the proposal to independent system review without applying it. After ordinary isolated URACE self-evolution and validation, `agora-confirm-system` may record verified benefit. Its visible bonus is capped at `0.05` and affects only an exact primary-metric tie; proposals, votes and referrals earn none.

`executor-efficiency-vital` compares model-call cost with observed outcomes over rolling 24-hour and 30-day windows. It reports productive-call yield, accepted changes, calls per accepted change, and associated metric improvements and regressions. The current Codex CLI adapter does not expose trustworthy token or monetary usage through this invocation path, so `unit=model_calls` is an explicit proxy. Every association is labelled `UNATTRIBUTED_COST_OUTCOME_ASSOCIATION`; the vital informs backoff and review without claiming that the call caused a metric movement.

`evolution-vital` is a versioned, confidence-qualified diagnostic over the same 24-hour and 30-day windows. Its visible components are productive model-call yield, execution acceptance, regression safety and goal completion. It also reports accepted changes and observed metric improvements or regressions per day, Evidence volume and model calls. The score is absent when no weighted Evidence exists and confidence rises only as the configured minimum Evidence volume is reached. It is not an acceptance gate or causal claim.

`vitals` also exposes a system scorecard with separate outcome-progress, Evidence-quality, safety/continuity and resource-efficiency dimensions. An overall diagnostic is withheld unless all dimensions exist, confidence is sufficient and no blocker or unresolved-effect veto applies. It is never Authority, acceptance or causal proof.

Portable analytics are optional and derived from canonical state:

```bash
PYTHONPATH=urace/runtime python3 -m urace report status
PYTHONPATH=urace/runtime python3 -m urace report export --output urace/generated/reports/latest
# Also create a native workbook when the optional openpyxl adapter is installed:
PYTHONPATH=urace/runtime python3 -m urace report export --output urace/generated/reports/latest --xlsx
```

`report status` currently reports portable CSV/HTML as `READY` and native XLSX as `ADAPTER_REQUIRED` because `openpyxl` is not installed. The export command atomically replaces a bundle containing UTF-8 CSV tables, a self-contained HTML dashboard and a manifest with state version and SHA-256 hashes. It includes progress, scorecard, Executor usage, objectives, work evaluations, external observations and reasoning patterns; portfolio and Agora tables are added when present. Formula-leading text is escaped. The runtime never reads control decisions from this report, so export failure, user edits or missing spreadsheet software cannot steer or block autonomy. Re-run after material activity for a current snapshot; the state version identifies freshness. CSV is the zero-dependency interchange format. XLSX is a convenience adapter and reports `XLSX_ADAPTER_REQUIRED` when `openpyxl` is absent, leaving any previous successful report bundle untouched.

This deployment sets `analytics_export.mode=ON_CHECKPOINT`, so durable lifecycle checkpoints and completed portfolio generations refresh `urace/generated/reports/latest` automatically. Queue `python3 -m urace policy set analytics-export disabled` to opt out, `... on-demand` to keep only explicit exports, or `... on-checkpoint` to restore automatic refresh; the change applies at the next safe cycle boundary. Export errors are warnings and never block control or acceptance.

The vitals snapshot also evaluates each bounded recent goal and context input and groups performed work as Product evolution or URACE self-evolution. These records associate cost and observed outcomes for investigation while retaining explicit `UNATTRIBUTED` labels. Inspect the complete view without a model call:

```bash
python3 -m urace evaluation show
python3 -m urace evaluation show --json
```

The evaluator can be revised while autonomous mode runs. Revisions enter the durable inbox, apply at a safe cycle boundary, increment `evaluation_system.version`, and retain bounded before/after history:

```bash
python3 -m urace evaluation set-weight goal_completion 0.4
python3 -m urace evaluation set-minimum 8
```

Valid weight components are the names shown by `evaluation show`; values range from 0 to 1 and at least one weight must remain positive. The score normalizes the weights of components with Evidence, so missing components do not become invented zeroes. Autonomous intelligent review may flag the evaluator as needing change, but any consequential implementation change still follows the normal Objective, validation and checkpoint path.

For long-run efficiency, unchanged progress observations are retained as a daily heartbeat instead of every 30-second cycle, unchanged Plans are reused, and duplicate assessment checkpoints are suppressed. External sources begin with a five-minute collection cadence, back repeated failures off exponentially to six hours, and retain duplicate error Evidence at most daily unless the error changes. Infinite mode writes durable state immediately for material changes or queued input and otherwise uses a five-minute heartbeat instead of fsyncing every cycle. Repeated outcome signatures accumulate in `pattern_memory` so recurring conditions can be recognized without duplicating full records. Candidate changes are rejected when they exceed configured per-change Product growth budgets. These controls limit bloat without deleting accepted decisions, material Evidence or recovery data.

All Objectives share one explainable portfolio. Authority, policy, status, dependencies and deferral gate eligibility before ranking; the visible component vector combines bounded user priority, pinned attention, expected value, urgency, deadline pressure, confidence, dependency-unblocking value, starvation correction, estimated cost, risk and scope Evidence. `goal forecast` reports advisory completion ranges, confidence, assumptions and blockers without invoking an Executor. Declared hour ranges are preferred; otherwise the runtime uses comparable completed goals or a labelled estimated-cost proxy. `add-goal` accepts dependencies, deadlines, earliest-start constraints, estimate ranges, confidence, priority bounds and pinning as well as the existing value/cost/risk inputs. URACE-targeted work remains subject to self-evolution policy and ordinary validation. Before each built-in Cohort planning call, the portfolio controller snapshots this same schedule and gives only eligible public-document goals to the planner; it records the cutoff, digest and selected goal IDs in the authenticated ledger without changing fixed Cohort budgets or selection rules.

The vitals report includes `runtime_efficiency`: total observed cycles, durable writes, suppressed writes, write-suppression ratio, state size, availability failure streak, external-source failure streak and next external collection time.

Intelligent discovery also maintains bounded `reasoning_memory` entries with a reusable hypothesis, supporting Evidence, counter-Evidence, calibrated confidence, applicability and learned response. It does not store raw conversation or hidden chain-of-thought. Low-confidence entries remain tentative, contradictory Evidence can weaken them, and retention is capped by configured value-aware limits.

Current local limits remain explicit: only the Codex CLI adapter is implemented; pattern recognition combines curated operator patterns with simple recurring lifecycle signatures rather than a general causal pattern learner; attribution safeguards prevent false causal claims but do not create experimental controls automatically when none are feasible; active-state deduplication does not replace off-machine backup or long-term archival policy; and no operating-system supervisor restarts the process after machine or launcher termination.

## Independent outcomes and real-user value

An `ACCEPTED` operation means its implementation passed independent structural and scope checks. Its objective remains `awaiting_outcome` until a frozen, independently observed outcome meets its prespecified target. Written test headings, normative keyword counts, executor completion claims, and raw external metric changes never establish real-user value. Existing historical acceptances without an outcome contract remain unverified; they are not retroactively promoted.

Configure an independent measure under `outcome_verification.measures` in the product configuration **before** executing its goal. Bind it with `add-goal --outcome-measure MEASURE_ID` or `outcome_measure_id` in a goal input. A measure keyed by the exact objective ID is also supported. Discovery can select an existing configured measure, but cannot invent a measurement contract to obtain credit. The baseline and contract are frozen on the operation before executor invocation; editing configuration afterward cannot rewrite them.

Example configuration for a binary task-completion trial (thresholds and valuations must be chosen for the actual product before enrollment):

```json
{
  "outcome_verification": {
    "measures": {
      "onboarding-completion": {
        "source": "measurements/onboarding.json",
        "independent": true,
        "evidence_kind": "real_user",
        "experiment_id": "onboarding-v1",
        "comparison_design": "randomized_control",
        "direction": "nondecreasing",
        "target": 0.8,
        "min_delta": 0.1,
        "min_samples": 100,
        "min_windows": 3,
        "min_window_seconds": 86400,
        "max_age_seconds": 86400,
        "value_per_success": 1.0,
        "currency": "USD",
        "guardrails": {"complaint_rate": {"max": 0.05}}
      }
    }
  }
}
```

An independent instrument supplies a bounded JSON file within the product root, outside all executor-writable files. The runtime reads it; it does not create user observations, enroll users, randomize participants, publish changes, or contact an external service. The operator must ensure provenance, consent, valid random allocation, disjoint participant samples, measurement validity, and complete trial costs. Merely labeling fabricated data `real_user` cannot establish those facts.

Evidence shape (numbers below are illustrative, **not actual user observations**):

```json
{
  "baseline": {"id": "baseline-1", "at": "2026-01-01T00:00:00+00:00", "successes": 500, "trials": 1000},
  "observations": [
    {
      "id": "window-1",
      "operation_id": "operation-REPLACE-WITH-ACTUAL-ID",
      "experiment_id": "onboarding-v1",
      "window_start": "2026-01-02T00:00:00+00:00",
      "at": "2026-01-02T08:00:00+00:00",
      "successes": 900,
      "trials": 1000,
      "control_successes": 500,
      "control_trials": 1000,
      "cost": 2.0,
      "guardrails": {"complaint_rate": 0.01}
    }
  ]
}
```

Each observation must have a new identity, match the operation and experiment, and cover a nonoverlapping post-application window. Real-user verification requires at least 100 observations per group per window, three windows spanning at least a day, a fresh latest window, the target and minimum baseline improvement, positive improvement over the concurrent control using conservative 95% Wilson bounds, and intact guardrails. These conservative floors are not a general statistical power calculation; a product-specific trial may require larger samples and longer follow-up. Costs use USD: per-window `cost` covers non-executor trial costs, including relevant support, operating and maintenance costs; reported executor cost is added separately. Net trial benefit must be positive under the predeclared value per successful outcome. Missing cost data remains unknown.

`evidence_kind: engineering` or `synthetic` can establish `OUTCOME_VERIFIED` using independent task results, but never `REAL_USER_VALUE_VERIFIED`. For lower-is-better proportions such as task failures use `direction: nonincreasing`; `successes` then counts the measured event (failures). Unknown, stale, duplicate, future, overlapping, under-sampled, contested, or otherwise invalid evidence cannot establish real-user value. Follow-up withdraws prior credit when evidence becomes stale, regressions appear, source independence changes, or negative outcome feedback contests the result. Repeated polling never multiplies credit. Signed value trajectories retain losses and distinguish evidence kinds; they are not a monetary ROI measure.

Review an explicitly selected product without executing changes:

```sh
python3 -m urace.outcome_verification \
  --root /path/to/product \
  --state /path/to/product/state.json \
  --config /path/to/product/config.json
```

Exit code 0 means at least one observed trial satisfies its frozen real-user contract; exit code 2 means none does or evidence is unavailable. This validates evidence under the declared instrument assumptions, not the instrument's authenticity, future market success, or autonomous discovery quality. The normal lifecycle performs the same follow-up and records the assessments. No real-user trial has been run as part of the synthetic regression suite.

Resource reports distinguish observed costs from estimates. Nested external metric values are diagnostic observations with explicit direction and a preserved baseline. ROI remains unknown until real-user benefit and all applicable execution costs are observed. Period snapshots retain the latest cumulative totals rather than summing cumulative totals repeatedly. Candidate validation receives complete runtime support files as immutable inputs and uses a configurable 900-second timeout in this deployment; its accepted kernel guard is unchanged.


## Audited owned CLI

Complete operator bootstrap with `python3 -m urace init --ready`, then run `python3 -m urace auto`. The bootstrap uses configured Product identity and Authority; it neither invents the project nor provisions credentials. Use `help status`, `help configuration`, `commands --json`, and `api commands` for the full installed surface. Resource effort belongs to URACE; native model reasoning is a separate setting. Unsupported data backends remain explicit. See the owned trial CLI audit report for evidence and limits.

## Canonical local installation

`urace/` is an independent local repository, ignored by the parent specification repository. `runtime/` contains the full control plane; `../trial/` contains the supervised specification-improvement workflow and its retained evidence. The original deployment state remains in `../state/` and is never committed. See `../README.md` for deployment and verification scope.
