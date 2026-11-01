# Canonical URACE consolidation and gap verification

**Scope:** complete supplied conversation reconciled into 96 requirement rows, every inspected Python source/test file, every installed command path and option, exact source diffs, qualification logs, and live cohort evidence. Repeated requests are consolidated by concern.

**Claim boundary:** source coverage and identified engineering fixes can be verified. This report does not assert universal bug freedom, optimal resource allocation, actual-user adoption, market fit, or maintenance-free indefinite reliability. “ALL requested claims proven” is not established.

## Repositories, chronology and preservation

The parent URACE repository owns its public documents and remains separate from the lowercase runtime repository. No parent commit or push is authorized for this task. CLAUDE.md remains local and ignored. Existing parent changes, including unrelated licensing work noticed after recovery, are preserved.

RUNTIME was first created on **2026-10-22 at 20:33:09 -03** (filesystem birth timestamp). Its initial local commit was cb2f2bc66d720524738678d1ef5686e5d5197ec9 at21:38:18 -03. It was incorrectly introduced as an isolated specification-trial engine rather than integrated with the existing lowercase runtime. This was a scoping mistake, not a filesystem sandbox requirement.

The original runtime contained 28 modules and5 test files. All57 source/test files from the earlier qualified external candidate are present in lowercase urace. Current source changes and imports are enumerated below. Historical source, Git bundle, Product versions, receipts and clocks remain archived.

Uppercase directory currently exists: **False**. Archive: [/home/host/urace-evidence/alignment-fixes-20261023T053658Z/retirement/archive-manifest.json](/home/host/urace-evidence/alignment-fixes-20261023T053658Z/retirement/archive-manifest.json).

## Qualification and live release

Core regression: {"tests": 1730, "failures": 0, "errors": 0, "skipped": 1, "wall_seconds": 450.6439119470306}.

Trial/operations regression: 94 tests, no failures/errors/skips (see trial-suite.log in qualification evidence). Real executor fixtures are not counted as native work. Source hashes bind exact qualified bytes; superseded/cancelled test attempts remain historical.

Fresh release record:

```json
{
  "at": "2026-10-23T09:36:42.439770+00:00",
  "baseline_commit": "5688fda7911f8b14fed4284e54938602456fb318",
  "baseline_sha256": "3e2a31b79dde519d85bdc8542cfd091b39c6b90afe9f4530d06a09de28de9d2f",
  "clock": {
    "ends_at": "2026-11-22T09:36:42.439770+00:00",
    "ends_unix": 1795340202.43977,
    "started_at": "2026-10-23T09:36:42.439770+00:00",
    "started_unix": 1792748202.43977,
    "trial_id": "urace-spec-20261023T093642Z-c0c558ae"
  },
  "core_state": "/home/host/Desktop/mvp/URACE/urace/runtime/../trial/core-state/urace-spec-20261023T093642Z-c0c558ae/state.json",
  "legacy_state_preserved": {
    "path": "/home/host/Desktop/mvp/URACE/urace/runtime/../trial/core-state/urace-spec-20261023T090029Z-485bfbbb/state.json",
    "sha256": "a01046e392002aca7adb6fd7e07274d1d301a3dab46051e3c0d6e6d9924a1802"
  },
  "native_calls_at_start": 0,
  "old_costs_preserved": true,
  "old_data_excluded_from_default_metrics": true,
  "previous_state_archived": true,
  "previous_trial_snapshots_verified": [
    {
      "integrity_verified": true,
      "sha256": "3e2a31b79dde519d85bdc8542cfd091b39c6b90afe9f4530d06a09de28de9d2f",
      "version": 0
    },
    {
      "integrity_verified": true,
      "sha256": "291940c5eec97bad0051803757252bce1ff05eadd8016a0fc9e26eb8b1c8c061",
      "version": 1
    },
    {
      "integrity_verified": true,
      "sha256": "f18ea72d1f4c941f39244458fbfd3792c1d9b0e255a243506a569e6422085755",
      "version": 2
    },
    {
      "integrity_verified": true,
      "sha256": "eef952e79322608702a3222b40ed115ea200ee44b60e28fa3bb60a470a4d95da",
      "version": 3
    },
    {
      "integrity_verified": true,
      "sha256": "bac7db4f9cbc042d2bfe685ab950a8566a808bd1e427a65b3b1290db4574b6dd",
      "version": 4
    },
    {
      "integrity_verified": true,
      "sha256": "ada7988937f42b592964aa058731299c2594ea7b9e474f7ec8703625e94ccea7",
      "version": 5
    }
  ],
  "product_copy": "/home/host/Desktop/mvp/URACE/urace/trial/product/urace-spec-20261023T093642Z-c0c558ae/URACE.md",
  "runtime_root": "/home/host/Desktop/mvp/URACE/urace",
  "source_tests": {
    "errors": 0,
    "failures": 0,
    "skipped": 1,
    "tests": 1730,
    "wall_seconds": 450.6439119470306
  },
  "trial_id": "urace-spec-20261023T093642Z-c0c558ae",
  "trial_suite": {
    "errors": 0,
    "failures": 0,
    "skipped": 0,
    "tests": 94
  }
}
```

Live verification record:

```json
{
  "captured_at": "2026-10-23T09:50:00.372905+00:00",
  "trial_id": "urace-spec-20261023T093642Z-c0c558ae",
  "clock": {
    "ends_at": "2026-11-22T09:36:42.439770+00:00",
    "ends_unix": 1795340202.43977,
    "started_at": "2026-10-23T09:36:42.439770+00:00",
    "started_unix": 1792748202.43977,
    "trial_id": "urace-spec-20261023T093642Z-c0c558ae"
  },
  "baseline_commit": "5688fda7911f8b14fed4284e54938602456fb318",
  "source_qualification": {
    "tests": 1730,
    "failures": 0,
    "errors": 0,
    "skipped": 1,
    "wall_seconds": 450.6439119470306
  },
  "trial_qualification": {
    "tests": 94,
    "failures": 0,
    "errors": 0,
    "skipped": 0
  },
  "source_files_verified": 95,
  "source_drift": [],
  "pins_verified": 112,
  "pin_mismatches": [],
  "versions": [
    {
      "version": 0,
      "sha256": "3e2a31b79dde519d85bdc8542cfd091b39c6b90afe9f4530d06a09de28de9d2f",
      "metadata_sha256": "dee5b550b617b747e5822f6c02b796211df0a1ebb02c28f2e301ca6bb4370842",
      "integrity_verified": true,
      "engine_id": "adaf7224c4d8a9fc98e8734193420e3b692d799248a55b924802b95f7dedfe10",
      "job": null
    },
    {
      "version": 1,
      "sha256": "e53bea85674c19f5db2979e7babe1beed2190c64d3fc17b43e4c1308a74af209",
      "metadata_sha256": "31a2677c320a7b8918266437c2796ad7bea76be4fd4f67838d6a574464f84baa",
      "integrity_verified": true,
      "engine_id": "adaf7224c4d8a9fc98e8734193420e3b692d799248a55b924802b95f7dedfe10",
      "job": "/home/host/Desktop/mvp/URACE/urace/trial/runs/urace-spec-20261023T093642Z-c0c558ae/spec-eeba2b91191c43caa6c7c8e8f3df0b20"
    },
    {
      "version": 2,
      "sha256": "c11ea96c93d23136c3c978906a04b21442558637ed4e427c59d163dc714aeb72",
      "metadata_sha256": "2b3f4b7e62de1199c9343159ea35cb711d3659f4573ca620c0e3ae9f70ba8fcd",
      "integrity_verified": true,
      "engine_id": "adaf7224c4d8a9fc98e8734193420e3b692d799248a55b924802b95f7dedfe10",
      "job": "/home/host/Desktop/mvp/URACE/urace/trial/runs/urace-spec-20261023T093642Z-c0c558ae/spec-32a1a61fe3d84a7f932d02be2041e7b6"
    },
    {
      "version": 3,
      "sha256": "071be846cacdd74b11bc79e8a78fe08f788e9a5dea735bae9a6ccfa3e0700274",
      "metadata_sha256": "13cbf0fcad361e11c4ca6e8f03ed78ab863017c09966942043756038cdb8639c",
      "integrity_verified": true,
      "engine_id": "adaf7224c4d8a9fc98e8734193420e3b692d799248a55b924802b95f7dedfe10",
      "job": "/home/host/Desktop/mvp/URACE/urace/trial/runs/urace-spec-20261023T093642Z-c0c558ae/spec-59c9b7c5297a4e40b3e8c92e4e5b9bcc"
    },
    {
      "version": 4,
      "sha256": "f9936dd496ff997f5f3c7a0f37ce52d00a2d9303a7d5900214be6b291bd994ae",
      "metadata_sha256": "b8cebb64c7783ef93281a469c5d4fb630a43aa257a69a4aa95fa43aac20f84e6",
      "integrity_verified": true,
      "engine_id": "adaf7224c4d8a9fc98e8734193420e3b692d799248a55b924802b95f7dedfe10",
      "job": "/home/host/Desktop/mvp/URACE/urace/trial/runs/urace-spec-20261023T093642Z-c0c558ae/spec-a6728d7c2e5b4d059d875552d842279d"
    },
    {
      "version": 5,
      "sha256": "c6222242053182a813bf6bc246e3e0563ca60d09e17734eb01c899102653523c",
      "metadata_sha256": "5b72a54deaf9188f6d48a81c2fa4f6c6d63b366bab532b18e389427c1b1bc997",
      "integrity_verified": true,
      "engine_id": "adaf7224c4d8a9fc98e8734193420e3b692d799248a55b924802b95f7dedfe10",
      "job": "/home/host/Desktop/mvp/URACE/urace/trial/runs/urace-spec-20261023T093642Z-c0c558ae/spec-6cba1223f00d452984ac38b0049bf189"
    }
  ],
  "active_version": 5,
  "product_copy_matches_active_snapshot": true,
  "completed_tasks": 19,
  "outcomes": {
    "ACCEPTED_EDITORIAL_IMPROVEMENT": 5,
    "AUDITED_NO_CHANGE": 1,
    "REJECTED_OR_DEFERRED": 13
  },
  "inflight": null,
  "reserved_native_calls": 29,
  "finished_native_calls": 29,
  "known_native_tokens": 476422,
  "finished_calls_with_unknown_usage": 0,
  "providers": {
    "codex": {
      "calls": 28,
      "known_tokens": 438688,
      "actual_client_versions": [
        "codex-cli 0.163.0"
      ],
      "requested_models": [
        "gpt-5.6-sol"
      ]
    },
    "claude": {
      "calls": 1,
      "known_tokens": 37734,
      "actual_client_versions": [
        "2.1.112 (Claude Code)"
      ],
      "requested_models": [
        "claude-sonnet-4-6"
      ]
    }
  },
  "core_state_path": "/home/host/Desktop/mvp/URACE/urace/runtime/../trial/core-state/urace-spec-20261023T093642Z-c0c558ae/state.json",
  "core_lifecycle": "ACTIVE",
  "core_operations": 19,
  "core_native_receipt_mirrors": 29,
  "services": {
    "urace-spec-trial.service": {
      "MainPID": "0",
      "Result": "success",
      "ActiveState": "inactive",
      "SubState": "dead"
    },
    "urace-spec-trial.timer": {
      "Result": "success",
      "ActiveState": "active",
      "SubState": "waiting"
    },
    "urace-spec-trial-watchdog.timer": {
      "Result": "success",
      "ActiveState": "active",
      "SubState": "waiting"
    },
    "urace-executor-availability.service": {
      "MainPID": "0",
      "Result": "success",
      "ActiveState": "inactive",
      "SubState": "dead"
    },
    "urace-executor-availability.timer": {
      "Result": "success",
      "ActiveState": "active",
      "SubState": "waiting"
    },
    "urace-productive-native-daily-review.service": {
      "MainPID": "0",
      "Result": "success",
      "ActiveState": "inactive",
      "SubState": "dead"
    },
    "urace-productive-native-daily-review.timer": {
      "Result": "success",
      "ActiveState": "active",
      "SubState": "waiting"
    }
  },
  "operational_review": {
    "at": "2026-10-23T09:49:04.255494+00:00",
    "trial_id": "urace-spec-20261023T093642Z-c0c558ae",
    "review_pass": true,
    "issues": []
  },
  "scope": "Current fresh cohort only. Counts are actual native receipts/tasks; unit fixtures excluded. Token receipts are not subscription credit decrements.",
  "spec_evolution_invariant": "No new public specification section or unsupported runtime claim added. Accepted Product edits pass full-document normative/headings/code preservation plus separate editorial review.",
  "unproven_claims": [
    "actual-user adoption and market fit",
    "maintenance-free indefinite reliability",
    "globally optimal allocation",
    "universal correctness across every feature/input/platform"
  ],
  "parent_commit_created": false,
  "remote_push_performed": false,
  "runtime_local_commit": null
}
```

## Gaps corrected in this continuation

| Area | Correction | Verification |
|---|---|---|
| Automatic goals | Disabled replenishment prevents new automatic goals after prior work; initial/current work remains usable | Failing-before/passing-after witnesses; core tests |
| Owner intent | Active and older retained owner context is forwarded; oversized contexts fail explicitly rather than silently losing authority | Core context/boundary tests |
| Core lifecycle | Real onboarding, input consumption, planning, pause, evidence reconciliation and isolated Product synchronization are used | Boundary tests, core smoke, live cohort |
| Resource effort | Core cadence consumes global/per-provider allocation effort; native model/reasoning remains separate | Core control tests |
| Resource truth | Strict integer counters, cache accounting, unknown usage, failed costs, stable receipt IDs and transport cleanup | Core/trial malformed-usage tests |
| Durable accounting | Product-scoped SQLite retention and freeform journals survive controller retention; quoted/Unicode URI paths handled | Retention/replay/product-isolation tests |
| Trial accounting | Core/freeform costs reconcile without double counting trial mirrors; legacy provider aliases resolve correctly | Trial resource tests |
| Lifetime data | Old archive filenames without a final.json suffix are included, without rewriting old evidence | Lifetime regression |
| Recovery | Launcher resolves active Product state; recovery snapshot includes extension source and pins without granting mutation permissions | Launcher/recovery tests |
| Packaging | Selected operational helper Python code is bundled under lowercase trial; active services use canonical sources | Standalone Docker trial suite; service inspection |
| Source integrity | Validated operator effort/model/enable/budget controls remain usable; authority/source changes remain pinned; actual config bytes get distinct engine bundles | Integrity tests |
| Coverage | Lossless UTF-8 windows include formerly oversized specification sections; full-document acceptance gates remain | Context coverage/preservation tests |
| Commands | Shared CLI/API grammar retained; trial concern classified correctly; inspection routes are read-only; nullable provider call ceilings supported | Grammar/API/control tests |
| Defaults | Ready bootstrap and newly attached providers do not invent hard call ceilings; explicit settings remain authoritative | Bootstrap/control tests |
| Period feedback | 3h/day/week/month comparisons; sparse percentiles and zero-baseline gains withheld | Period-feedback tests and reports |
| Operational review | Three-hour integrity/service review and evidence-gated optional-idle adaptation; no acceptance/source-policy weakening | Review-policy tests and scheduled unit |
| Product setup | Fresh Product is selected committed URACE.md; old root document and legacy state are preserved | Baseline hash and release record |

## Full requirement comparison

The provenance columns describe work in each historical scope. The audit result supersedes older completion wording; empirical limits are not converted into success flags.

| # | Requirement | Original urace | Earlier external work | Incorrect RUNTIME scope | Canonical urace | Audit result |
|---:|---|---|---|---|---|---|
| 1 | Canonical runtime location | Full implementation existed | Separate experimental copies | Erroneous second engine directory | Full implementation in runtime/; trial component in trial/ | All inspected source/evidence migrated; complete 688-file uppercase archive hash-verified. Retirement status below. |
| 2 | Independent local Git repository | No nested Git at inspected roots | External experimental artifacts | Local Git cb2f2bc | Separate urace Git requested; preserve cb2 history | Separate lowercase repository; no parent commit or push. Final local commit status is recorded in release evidence. |
| 3 | Parent repository separation | Ignored /urace | Not in parent Git | Initially unignored; then /RUNTIME/ ignored | Keep /urace ignored; remove /RUNTIME/ ignore only after retirement | Source retained/imported and relevant engineering qualification completed; see exact files, command grammar and live release record. |
| 4 | Preserve original source and unrelated work | Existing source; no independent source history | Candidate history retained | Trial source/history retained | 33 originally inspected Python files reconstructed and hash-verified in rollback archive | Source retained/imported and relevant engineering qualification completed; see exact files, command grammar and live release record. |
| 5 | Keep CLAUDE.md local | Private symlink/config | Not modified | Not committed | Unchanged, parent ignored; never included in runtime staging | Source retained/imported and relevant engineering qualification completed; see exact files, command grammar and live release record. |
| 6 | Do not commit unrelated parent .gitignore changes | Existing dirty ignore file | N/A | Added /RUNTIME/ exclusion | Only task-specific exclusion removal after retirement; no parent commit | Source retained/imported and relevant engineering qualification completed; see exact files, command grammar and live release record. |
| 7 | Preserve dirty parent README.md and URACE.md | Both already dirty | Copied as test fixtures | Working originals not edited | Byte-identical to pre-integration copies | Source retained/imported and relevant engineering qualification completed; see exact files, command grammar and live release record. |
| 8 | Runtime purpose: Product evolution under Intent/Authority | Implemented control plane | Preserved in candidates | Only bounded specification workflow | Original control plane retained; explicit isolated workflow for selected URACE.md | Source retained/imported and relevant engineering qualification completed; see exact files, command grammar and live release record. |
| 9 | r120 continuation module | Present when inspected | Present in imported candidate | Not a substitute for it | degrade, handle_unspecified, reset_confidence retained | Source retained/imported and relevant engineering qualification completed; see exact files, command grammar and live release record. |
| 10 | r120 cycle integration | Present when inspected | Present in imported candidate | Separate worker loop | Core cycle confidence reset and unknown-situation recording retained | Source retained/imported and relevant engineering qualification completed; see exact files, command grammar and live release record. |
| 11 | Spec Evolution Invariant | Runtime/source consistency requirement | Guards preserved | Rejects new runtime claims in editorial edits | No new public specification sections; existing text corrections only | Source retained/imported and relevant engineering qualification completed; see exact files, command grammar and live release record. |
| 12 | Operator gate preservation | Existing _apply_operator_gate | No migration change requested | Not used as replacement | Original authority gate preserved rather than removed | Source retained/imported and relevant engineering qualification completed; see exact files, command grammar and live release record. |
| 13 | Full lifecycle and durable state | Implemented | Retained/improved | Not implemented as full control plane | Original lifecycle code retained; legacy state not reset | Core boundary consumes queued input, preserves lifecycle/owner controls, synchronizes Product copy and reconciles completed evidence. Tested and live qualification recorded below. |
| 14 | Authority resolution and scope boundaries | Implemented | Retained | Limited editorial contract | Original authority/destination/validation modules retained; trial has narrow no-new-behavior gate | Source retained/imported and relevant engineering qualification completed; see exact files, command grammar and live release record. |
| 15 | Independent validation and value trajectory | Implemented | Engineering fixes/witnesses | Model editorial acceptance only | Both code paths retained; model acceptance not relabeled as real-user proof | Source retained/imported and relevant engineering qualification completed; see exact files, command grammar and live release record. |
| 16 | Autonomous automatic goals | Not installed as new feature | auto_goals.py implemented | Section-driven automatic assessment | Imported project-derived goals; trial derives review work from actual selected specification | Source retained/imported and relevant engineering qualification completed; see exact files, command grammar and live release record. |
| 17 | Auto-goal toggle default enabled | Missing new controls | user_controls/configuration implemented | Settings true | Canonical configuration controls feed trial; default true | Source retained/imported and relevant engineering qualification completed; see exact files, command grammar and live release record. |
| 18 | Backlog replenishment toggle bound to auto-goals | Missing new controls | Configuration plus external study/controller behavior | Settings true; initially not fully honored | Effective master/sub-toggle honored by trial scheduling | FIXED: core replenishment-disable now prevents creation of subsequent automatic goals while allowing initial/current work. |
| 19 | Choose next work after task/milestone | Existing discovery | Project requirements and external replenishment | Least-recently reviewed eligible section | Retained automatic review selection and original project-goal mechanisms | Source retained/imported and relevant engineering qualification completed; see exact files, command grammar and live release record. |
| 20 | Continue without declared next milestone | Existing bounded discovery | Requirement/discovery mechanisms | Can select another specification section | Specification workflow replenishes assessments from its Product | Source retained/imported and relevant engineering qualification completed; see exact files, command grammar and live release record. |
| 21 | Automatic quotas/credit retry | Provider retry support | Improved classification and scheduling | Shared provider backoff | Independent retry eligibility and metadata refresh retained | Source retained/imported and relevant engineering qualification completed; see exact files, command grammar and live release record. |
| 22 | Five-hour-fifteen-minute availability window | Configurable retry | 18900-second shared retry | Shared governor/availability | Existing 18900-second retry retained; metadata may refresh sooner | Source retained/imported and relevant engineering qualification completed; see exact files, command grammar and live release record. |
| 23 | Real Codex executor | Codex adapter | Actual native canaries/cases | Real Codex app-server transport | Native transport and provider-reported usage retained | Source retained/imported and relevant engineering qualification completed; see exact files, command grammar and live release record. |
| 24 | Real Claude executor | Adapter existed | Native tests/replays and capacity-wording fixes | Real Claude CLI transport | Registered independently; enabled when actual quota/auth permits | Source retained/imported and relevant engineering qualification completed; see exact files, command grammar and live release record. |
| 25 | Provider independence/failover | Provider pool existed | Pool usage/classification fixes | Independent eligible list | One unavailable provider does not gate the other; review can use another provider | Source retained/imported and relevant engineering qualification completed; see exact files, command grammar and live release record. |
| 26 | No synthetic calls counted as native value | Unit fixtures separate | Historical native and simulation records separate | Native receipts separate from unit tests | Same separation; tests never entered in live ledger | Source retained/imported and relevant engineering qualification completed; see exact files, command grammar and live release record. |
| 27 | Measure AI tokens and elapsed time | Usage fields/proxies | Usage truth fixes | Actual tokens/native wall/task elapsed | Canonical resource reports retain actual and missing usage separately | FIXED: native units normalized; cache double counting rejected; core/freeform/trial reconciliation and durable Product-scoped receipts implemented. |
| 28 | Malformed Claude usage remains unknown | Older usage behavior | Validated accounting fix | Transport accounting separate | Imported executor fix plus trial accounting; real zero stays distinguishable | FIXED: bool/fractional/negative/nonfinite usage remains unknown; malformed Codex accounting always closes transport. |
| 29 | Subscription credits versus token counts | Not directly observable | Explicit limits on inference | Credit decrement null | Actual native tokens/time tracked; subscription decrement remains unknown | Source retained/imported and relevant engineering qualification completed; see exact files, command grammar and live release record. |
| 30 | Per-product resource counts | Core per-product state | Added accounting/context work | Stable Product identity and epoch | URACE.md Product registry/ledger retained with CLI filters | Source retained/imported and relevant engineering qualification completed; see exact files, command grammar and live release record. |
| 31 | Per-executor resource counts | Pool metadata | Accounting fixes | Codex/Claude filtering | Filters retained; provider participation not causal attribution | Source retained/imported and relevant engineering qualification completed; see exact files, command grammar and live release record. |
| 32 | Product/executor combinations and all-products totals | Core registry and fleet | External comparisons | Registered-products aggregation | Retained product/executor/all-products filtering | Source retained/imported and relevant engineering qualification completed; see exact files, command grammar and live release record. |
| 33 | Fresh trial data and counter reset | Legacy state retained | Multiple earlier cohorts | Explicit trial/epoch IDs | Fresh state must exclude older trials while lifetime preserves costs | Fresh core-integrated committed-5688fda cohort; exact clock, native activity, accepted versions and metadata verification recorded below. No unit fixtures counted as live evidence. |
| 34 | No erasure of historical cost/evidence | Existing state | Multiple old trials preserved | Append-only ledger/history | Historical trials and versions preserved, not pooled into fresh default metrics | Source retained/imported and relevant engineering qualification completed; see exact files, command grammar and live release record. |
| 35 | No aggregate call/token/time caps for current trial | Old local 4/20 configuration | Nullable budgets qualified | Aggregate guards null | Local deployment call caps null; shared aggregate caps remain null | Source retained/imported and relevant engineering qualification completed; see exact files, command grammar and live release record. |
| 36 | Generous throughput, no consumption target | Older tight defaults | Studies/calibration and cap amendments | Fixed one-minute inter-task idle | High5s/medium15s/low60s provider-specific inter-task idle; no calls/day target | Source retained/imported and relevant engineering qualification completed; see exact files, command grammar and live release record. |
| 37 | URACE allocation effort low/medium/high | Not installed | user_controls profiles | Trial resource effort high | Imported canonical controls; live trial high; generic missing-setting default medium | FIXED: core effort changes assessment cadence; native reasoning remains independent. |
| 38 | Per-executor allocation effort | Not installed | Implemented controls/profiles | Previously separate settings | Overrides feed trial idle policy independently of native reasoning | FIXED: per-provider overrides apply to core/trial cadence independently of native model settings. |
| 39 | Native model and reasoning options | Fixed/limited provider settings | Provider-specific native_options | Initially hard-coded model/medium | Canonical overrides now reach real trial calls | Source retained/imported and relevant engineering qualification completed; see exact files, command grammar and live release record. |
| 40 | Adaptive optimal resource allocation | No globally proven optimizer | Matched-effort studies/provisional policies | Quota-aware eligibility; round-robin provider use | Retained guards/profiles; actual effort-responsive cadence | Implemented bounded evidence-responsive cadence; globally optimal strategy is not proven. |
| 41 | Spend more when justified, low usage is not success | Not a reliable standalone score | Explicit allocation objective | Acceptance/time/token measurements | Resource reports include outcome yield and time; no low-spend success claim | Source retained/imported and relevant engineering qualification completed; see exact files, command grammar and live release record. |
| 42 | Custom efficiency score formulas via CLI | Not installed as new feature | Other experimental metrics | Declarative weighted scoring | Trial config efficiency preserved behind canonical CLI/API | Source retained/imported and relevant engineering qualification completed; see exact files, command grammar and live release record. |
| 43 | User custom metrics via CLI | External metrics/vitals | Experimental sources | Custom metric records with provenance | Canonical trial data metrics record/show retained | Source retained/imported and relevant engineering qualification completed; see exact files, command grammar and live release record. |
| 44 | Review/calibrate efficiency formulas | Core evaluators | Earlier studies | Methodology screens per measurement | Missing data/sample/balance/gaming checks retained | Formula screening and revision provenance implemented; held-out calibration remains unestablished. |
| 45 | Percentile gains/losses and period comparisons | Core analytics/value trajectory | Matched studies with descriptive percentiles | Current-trial ratios; no full matched period experiment | Original analytics retained; new trial raw data supports later analysis | IMPLEMENTED: 3h/day/week/month comparisons and sample-screened descriptive percentiles. |
| 46 | Three-hour reviews instead of daily-only | No host review supervisor | Three-hour host review configured | Review dispatch to spec status | Three-hour review remains configured; per-candidate quality review is immediate | Source retained/imported and relevant engineering qualification completed; see exact files, command grammar and live release record. |
| 47 | Autonomous runtime maintenance/improvement | Necessary-only evolution | Separate bounded maintenance/self-improvement workers | Trusted worker cannot rewrite itself | Generic evolution code retained; old maintenance workers remain paused | Guarded core self-evolution retained; three-hour operational review can adapt idle cadence. No unrestricted autonomous code rewriting is enabled. |
| 48 | Host failure and restart safeguards | Durable locks/recovery | Crash-lock/activation fixes | Systemd restart/watchdog/transactional publication | Imported recovery plus supervised canonical auto workflow | FIXED: Product-specific recovery paths and extension source/pin snapshots; immutable mutation boundaries preserved. |
| 49 | Budget exhaustion/safety/trial expiry boundaries | Implemented governance | Nullable-budget and quota wording fixes | Provider/runaway/authority/expiry guards | Preserved; no unsafe never-stop promise | Source retained/imported and relevant engineering qualification completed; see exact files, command grammar and live release record. |
| 50 | Clean purpose-based command grouping | Many original commands | command_surface.py audit/fixes | Only status/config/data trial roots | Imported shared status/configuration grammar; trial is explicit workflow concern | FIXED: trial is grouped with execution concerns; inferred read-only trial commands require no unnecessary mutation confirmation. |
| 51 | Persistent configuration commands | Older grammar | Nested configuration grammar | Trial efficiency config only | Canonical configuration covers goals, effort, native options and workflow | Source retained/imported and relevant engineering qualification completed; see exact files, command grammar and live release record. |
| 52 | Status base command | Original check/vitals commands | Read-only status subjects | Separate trial status | Default status/runtime/resources/vitals select active workflow; core commands remain available | Source retained/imported and relevant engineering qualification completed; see exact files, command grammar and live release record. |
| 53 | Fine-grained resource CLI inspection | Older resource views | Typed CLI/API improvements | Product/executor/scope/all-products flags | Canonical status resources and explicit trial views share actual trial data | Source retained/imported and relevant engineering qualification completed; see exact files, command grammar and live release record. |
| 54 | Redundant commands and compatibility | Many aliases | Aliases hidden/grouped by concern | Small separate command tree | No capability dropped solely to reduce root count | Source retained/imported and relevant engineering qualification completed; see exact files, command grammar and live release record. |
| 55 | Quoted freeform input | Existing classifier | Exact-command match, section spans and guarded inference | Not a replacement for full routing | Imported original enhanced freeform machinery | Source retained/imported and relevant engineering qualification completed; see exact files, command grammar and live release record. |
| 56 | Fallback to executors for unmatched prose | Existing classifier | Validated inference schema/correction path | Editorial worker only | Imported inference fallback with original input retained | Source retained/imported and relevant engineering qualification completed; see exact files, command grammar and live release record. |
| 57 | Semantic sections, conditions and alternatives | Limited original classification | Span/conjunction/ambiguity handling | Not general-purpose input routing | Imported bounded section-aware routing | Source retained/imported and relevant engineering qualification completed; see exact files, command grammar and live release record. |
| 58 | Full CLI/API feature discovery and typed dispatch | Earlier API implementation | api_interface.py full grammar adapter | Trial CLI had separate parser | Shared trial grammar integrated with canonical API discovery; exact argv retained | Source retained/imported and relevant engineering qualification completed; see exact files, command grammar and live release record. |
| 59 | API streaming, batches, false/repeated values, errors | Earlier limited transport | Implemented typed/streamed adapter | Not full generic API | Imported unchanged and regression-tested with new trial routes | Source retained/imported and relevant engineering qualification completed; see exact files, command grammar and live release record. |
| 60 | Real data connectors and urace data | Existing registry/placeholders | Real local JSON/CSV/SQLite transports; unsupported remote errors | No generic data source registry replacement | Imported transports and persistence/verification behavior | Source retained/imported and relevant engineering qualification completed; see exact files, command grammar and live release record. |
| 61 | Credential separation for data sources | Secret references | Truthful transport readiness fixes | No credential provisioning | No secrets read from state/secrets or committed; references/config remain local | Source retained/imported and relevant engineering qualification completed; see exact files, command grammar and live release record. |
| 62 | Useful compress/decompress and relatives | Compaction implementation | Hash/path checks and lossless archive fixes | Not full compaction implementation | Imported integrity fixes; aliases and amend/CRC preserved | Source retained/imported and relevant engineering qualification completed; see exact files, command grammar and live release record. |
| 63 | Ready-to-run bootstrap and urace auto | Existing init/onboard/launcher | init --ready installed-client discovery | Separate direct spec script | Canonical auto selects installed specification workflow; dry-run avoids calls/writes | FIXED: real onboarding retained; missing call ceilings default to unlimited after ready bootstrap; explicit operator ceilings preserved. |
| 64 | Ordinary auto command actually runs the intended Product | Old disabled executor deployment | External runtime work not installed | Worker bypassed ordinary core CLI | Local workflow setting specification-trial; service runs urace.cli auto --cycles1 | Fresh core-integrated committed-5688fda cohort; exact clock, native activity, accepted versions and metadata verification recorded below. No unit fixtures counted as live evidence. |
| 65 | Correct Product is URACE.md, not AWS/Render/generic app | Original blueprint Product | Earlier unrelated app trials were later superseded | Specification-only target | Same selected URACE.md baseline; generic app outputs excluded | Fresh core-integrated committed-5688fda cohort; exact clock, native activity, accepted versions and metadata verification recorded below. No unit fixtures counted as live evidence. |
| 66 | Baseline must be commit 5688fda | Original parent HEAD differs | User-selected baseline recorded | Switched from earlier HEAD baseline to 5688fda | Selected commit and exact Git bytes retained | Fresh core-integrated committed-5688fda cohort; exact clock, native activity, accepted versions and metadata verification recorded below. No unit fixtures counted as live evidence. |
| 67 | Version-based snapshots of every accepted document | Core product versions | Other versioned runtime candidates | vNNNNNN per trial, parent/baseline diffs | All snapshots copied intact; future snapshots inside urace/trial | Fresh core-integrated committed-5688fda cohort; exact clock, native activity, accepted versions and metadata verification recorded below. No unit fixtures counted as live evidence. |
| 68 | Per-snapshot Product/result metadata | Core change records | Candidate verification receipts | Identity/lineage/changes/quality/evidence | Retained exact originals plus future complete declared schema | Source retained/imported and relevant engineering qualification completed; see exact files, command grammar and live release record. |
| 69 | Per-snapshot runtime/resource/time metadata | Core usage/decision records | Runtime candidate reports | Calls, tokens, time, engine/config/native receipts | Retained; entire installed core source also pinned in engine bundle | Fresh core-integrated committed-5688fda cohort; exact clock, native activity, accepted versions and metadata verification recorded below. No unit fixtures counted as live evidence. |
| 70 | Product-wide analysis | Core per-product analytics | External study summaries | Product rollup | Current-trial Product rollup retained | Source retained/imported and relevant engineering qualification completed; see exact files, command grammar and live release record. |
| 71 | Entire-runtime overall analysis | Core views and fleet | Shared governor/allocation studies | All registered trial products rollup | Same rollup retained; generic historical core state is not silently pooled | Registered trial Product totals now reconcile canonical native/freeform costs without adapter mirror duplication; registry scope remains explicit. |
| 72 | Fine-grained complete metadata coverage | Many primitives/features | Feature-specific test artifacts | 18 declared workflow feature mappings | Schema/inventory retained; raw unknown fields marked unavailable | Declared per-version/Product/runtime schema retained, with additional core receipts, source/config builds and period feedback; unavailable observations remain explicit. |
| 73 | Engine/configuration/source provenance | Core runtime snapshots | Qualified source manifests | Frozen engine bundles | Full installed runtime source and trial code pinned; qualified-source hashes retained | Fresh core-integrated committed-5688fda cohort; exact clock, native activity, accepted versions and metadata verification recorded below. No unit fixtures counted as live evidence. |
| 74 | Atomic publication and crash recovery | Core transaction recovery | Crash-lock improvements | Staged directory, fsync, atomic pointer, verified recovery | Both mechanisms retained; no partial snapshot promotion | Source retained/imported and relevant engineering qualification completed; see exact files, command grammar and live release record. |
| 75 | Cosmetic change filtering and productivity acceptance | Core outcome/value guards | Witnessed engineering fixes | Concrete failure case, cosmetic prefilter, independent material-gain review | Preserved all acceptance checks; no regression/new behavior allowed | Source retained/imported and relevant engineering qualification completed; see exact files, command grammar and live release record. |
| 76 | Preserve normative sentences/headings/code fences | Core validation | Semantic/compaction guards | Sentence-level normative guard including wraps/dotted filenames | Same protection retained after relocation | Source retained/imported and relevant engineering qualification completed; see exact files, command grammar and live release record. |
| 77 | Independent review and accept/decline proof | Core independent acceptance | Fail-before/pass-after runtime cases | Separate native calls; other provider when eligible | Accepted/rejected/no-change outcomes retained with all costs | Fresh core-integrated committed-5688fda cohort; exact clock, native activity, accepted versions and metadata verification recorded below. No unit fixtures counted as live evidence. |
| 78 | No source/data poisoning or authority from prompts | Core authority and portfolio isolation | Bounded schema/routing tests | Specification passed as data; tools disabled | Same artifact-only native policy and exact edit anchors retained | Source retained/imported and relevant engineering qualification completed; see exact files, command grammar and live release record. |
| 79 | Historical absolute references after directory move | Original deployment paths | External provenance paths | RUNTIME absolute paths in metadata | Pinned read-time relocation map; original hash-bound bytes unchanged | Source retained/imported and relevant engineering qualification completed; see exact files, command grammar and live release record. |
| 80 | No evidence or source history discarded | No nested source repo originally | All external history retained | Local Git and generated evidence | External hash-verified archive and Git bundle; code imported, data retained | All inspected source/evidence migrated; complete 688-file uppercase archive hash-verified. Retirement status below. |
| 81 | Fresh 30-day trial uses urace only | Legacy core state separate | Old trials remain superseded | Former worker root was RUNTIME | Release should start fresh isolated cohort under urace/trial via canonical auto | Fresh core-integrated committed-5688fda cohort; exact clock, native activity, accepted versions and metadata verification recorded below. No unit fixtures counted as live evidence. |
| 82 | Live task completion and executor-call verification | Not inferred from timer alone | Native historical cases | Real calls/completions before move | Require new post-release calls and completed jobs, plus snapshot acceptance integrity | Fresh core-integrated committed-5688fda cohort; exact clock, native activity, accepted versions and metadata verification recorded below. No unit fixtures counted as live evidence. |
| 83 | Strong sustained real-user benefit and market fit | Not established | Synthetic/engineering and public-input cases | Editorial acceptance only | No fabricated users/adoption; current trial supplies bounded project evidence | NOT PROVEN: actual-user adoption, sustained benefit and market fit. |
| 84 | Maintenance-free long-run reliability guarantee | Not established | Bounded recovery experiments | Local supervision; interruptions occurred | 30-day observation remains prospective; migration interruptions retained | NOT GUARANTEED: maintenance-free indefinite reliability; fresh observation is prospective. |
| 85 | Value and reliability of ALL runtime features in real use | Many implemented features | Full regression + selected real executor cases | Only specification workflow exercised live | Full engineering suite retained; editorial trial is not full live feature coverage | Engineering regression and live selected-workflow evidence; not live proof of every feature and every deployment. |
| 86 | Trustworthy real-world simulations | Engineering fixtures | Genuine source-defect reproducers and native cases | Model editorial hypotheses, clearly labeled | Fixtures never counted as users; project cases remain auditable | Engineering simulations remain labeled; project/native evidence is real but does not prove market fit. |
| 87 | No guaranteed globally optimal quality/time/credits | Not established | Provisional studies | Explicit optimality false | Same honest limit; ratios alone do not prove optimum | No global optimality guarantee introduced. |
| 88 | No universal arbitrary-input correctness guarantee | Not established | Robust routing cases | Not addressed by trial engine | Schema/route validation and ambiguity handling retained | Quoted deterministic routes, inference and validation implemented; universal semantic correctness is not guaranteed. |
| 89 | Cross-host disaster failover and cloud hosting | Not implemented | No AWS/Render provisioning | Local services only | No cloud resources, credential changes or cross-host guarantee introduced | No cloud/cross-host disaster guarantee introduced. |
| 90 | No remote pushes or parent commits | Parent repository separate | External work uncommitted | One prior local initial commit | Only authorized separate local runtime commit after verification | Separate lowercase repository; no parent commit or push. Final local commit status is recorded in release evidence. |
| 91 | Autonomous unreviewed runtime rewrites | Necessary-only protected evolution | Bounded candidate maintenance, not arbitrary edits | Pinned worker code | No unattended arbitrary promotion that bypasses tests/authority/source guards | No unrestricted unattended source promotion bypassing qualification introduced. |
| 92 | Omitted/unsupported integrations remain explicit | Optional adapters | Unsupported remote types return errors | No provisioned customer connectors | No invented adapters, credentials, billing or customer outcomes | Unsupported adapters, unavailable billing and external outcomes remain explicit. |
| 93 | Remaining platform test limitation | Bubblewrap-dependent portfolio behavior | Host-isolation limitation recorded | Not removed to force green | One host-dependent test skipped; no security restrictions bypassed | One existing host-dependent portfolio isolation test remains skipped; not counted as passed. |
| 94 | Evidence scope changed from application outputs to URACE itself | Original target blueprint | Earlier earthquake/application outputs now historical | New target specification-only | No unrelated application results relabeled as URACE Product improvements | Source retained/imported and relevant engineering qualification completed; see exact files, command grammar and live release record. |
| 95 | Original runtime state and secrets preservation | Existing state/config/stable runtime | Test environments isolated | Only own trial state | Legacy state/secrets not reset; local deployment configuration changed explicitly | Legacy state and credentials preserved; fresh cohort uses a distinct core-state path and refreshed full recovery snapshot. |
| 96 | Claims about all requested work being complete | Handoff not independently trusted | Historical qualification not taken as current proof | Earlier duplicate not full replacement | Separate code alignment, activation and empirical-outcome status | All inspected source coverage and identified implementation fixes are documented. A blanket guarantee covering all requested empirical claims is NOT established. |

## Every source/test file

| Path | Original comparison | External candidate comparison | Lines | SHA-256 |
|---|---|---|---:|---|
| [runtime/tests/test_alignment_fixes.py](/home/host/Desktop/mvp/URACE/urace/runtime/tests/test_alignment_fixes.py) | added | added | 198 | c2f5febd07383fbd5689a4d48542eb4c5321c1216e698adbffd2165c95ccdc1d |
| [runtime/tests/test_auto_goals.py](/home/host/Desktop/mvp/URACE/urace/runtime/tests/test_auto_goals.py) | added | identical | 43 | 1d6581c899a118dc6c957000602a16ddd5ed43e4c3cf3621519842f12f8b9dd9 |
| [runtime/tests/test_bootstrap_ready.py](/home/host/Desktop/mvp/URACE/urace/runtime/tests/test_bootstrap_ready.py) | added | changed | 24 | 2acf1913030431459384fdce279019331948a2b8c2efd191c2faf8bd070b9caa |
| [runtime/tests/test_command_surface.py](/home/host/Desktop/mvp/URACE/urace/runtime/tests/test_command_surface.py) | added | identical | 103 | bce6b53789c5f6030f52559d0264f55fe3f483e95c66c76c8dbf83d29faa40aa |
| [runtime/tests/test_compaction_integrity.py](/home/host/Desktop/mvp/URACE/urace/runtime/tests/test_compaction_integrity.py) | added | identical | 21 | 1a8ddf026f57ec2ecd6e881691aec9022a0044586976beebb62e523524ada974 |
| [runtime/tests/test_data_cli_persistence.py](/home/host/Desktop/mvp/URACE/urace/runtime/tests/test_data_cli_persistence.py) | added | identical | 49 | f0383eaa0035ecf9d3c58d114bfc176930eb55f0a2b23066398415d043bc2517 |
| [runtime/tests/test_data_source_truthfulness.py](/home/host/Desktop/mvp/URACE/urace/runtime/tests/test_data_source_truthfulness.py) | added | identical | 50 | 57025472a9d41aca5247f3af436ad26b04055b3b58fc06a9039f8228543692d4 |
| [runtime/tests/test_data_transports.py](/home/host/Desktop/mvp/URACE/urace/runtime/tests/test_data_transports.py) | added | identical | 44 | 09e4d7882de33ad6c3142a4a2fce5f3f7b416ca71fc04497ae0674cfe185772d |
| [runtime/tests/test_freeform_routing.py](/home/host/Desktop/mvp/URACE/urace/runtime/tests/test_freeform_routing.py) | added | identical | 63 | a8aecaf34c2a11b55d25407680dcb64cc876c74976b3fdcd17d6f431c2390c35 |
| [runtime/tests/test_json_flags.py](/home/host/Desktop/mvp/URACE/urace/runtime/tests/test_json_flags.py) | added | identical | 21 | 03e21445ba7a396f0e65c2d38725343f32b0fb71f56284b746aab8977a302a90 |
| [runtime/tests/test_lock_crash_recovery.py](/home/host/Desktop/mvp/URACE/urace/runtime/tests/test_lock_crash_recovery.py) | added | identical | 148 | 4b3acb57ca45c67676117eb2afebc54e219ce9c2688cd4c67d97510102ab0bba |
| [runtime/tests/test_metric_file_resource_bound.py](/home/host/Desktop/mvp/URACE/urace/runtime/tests/test_metric_file_resource_bound.py) | added | identical | 36 | ca185cfbcffa77e1838d92c4d2f9e4a009e89fe8ba0d0aa578a0482e3d740949 |
| [runtime/tests/test_native_usage_errors.py](/home/host/Desktop/mvp/URACE/urace/runtime/tests/test_native_usage_errors.py) | added | identical | 15 | a59f7c40284d9e31172c11a28100eeeb14a7910b6ff2f1dba6a847ff156bfbf9 |
| [runtime/tests/test_nested_repository.py](/home/host/Desktop/mvp/URACE/urace/runtime/tests/test_nested_repository.py) | added | added | 40 | 1a1582b458eb0e0c6ec4719fb9fe2be8dca84abfffbc01a2a3690d2799a36806 |
| [runtime/tests/test_nullable_budgets.py](/home/host/Desktop/mvp/URACE/urace/runtime/tests/test_nullable_budgets.py) | added | identical | 19 | 8a38699834bdd41cc90c164e597e7d0d47bb488359290e743fbfb03be0301def |
| [runtime/tests/test_operator_bootstrap.py](/home/host/Desktop/mvp/URACE/urace/runtime/tests/test_operator_bootstrap.py) | added | identical | 84 | b90e04ed1be03cbc2db69ef4f0955b7f1a58c4a0a060afe26757e42baecdf1e1 |
| [runtime/tests/test_owner_value_readiness.py](/home/host/Desktop/mvp/URACE/urace/runtime/tests/test_owner_value_readiness.py) | identical | identical | 497 | 84421fd7bda171c7323fe29b63eb56271e086b1be3e47d5637eb685cd28bd68e |
| [runtime/tests/test_portfolio.py](/home/host/Desktop/mvp/URACE/urace/runtime/tests/test_portfolio.py) | identical | identical | 491 | e0ea6f54489b51481ab6e12c792092cc5ef0631ca724685d18eae348064a3837 |
| [runtime/tests/test_quota_wording.py](/home/host/Desktop/mvp/URACE/urace/runtime/tests/test_quota_wording.py) | added | identical | 8 | 0d9e93a061368edfc9681b6ed3e7b7a719cb55eacacc033e462bd6d21a6942bb |
| [runtime/tests/test_trial_bridge.py](/home/host/Desktop/mvp/URACE/urace/runtime/tests/test_trial_bridge.py) | added | added | 47 | a44d38ec54c3e19c841f503c23d0b1cc46ee1c07235afe421107d6352345ea95 |
| [runtime/tests/test_trial_workflow.py](/home/host/Desktop/mvp/URACE/urace/runtime/tests/test_trial_workflow.py) | added | added | 56 | b2f69b3dfd08f02d1826011c4abc5a77d5574e52231e069ec21dfde04cf9cf78 |
| [runtime/tests/test_urace.py](/home/host/Desktop/mvp/URACE/urace/runtime/tests/test_urace.py) | changed | changed | 13892 | bea380e33999796cc11792a85517327b4dd65b87eed795e1001c686956e2df40 |
| [runtime/tests/test_urace_r109.py](/home/host/Desktop/mvp/URACE/urace/runtime/tests/test_urace_r109.py) | changed | identical | 1355 | c35ffd77f6db09df3b941990438cf206fb899832ae02cc095e4d2de07aae155d |
| [runtime/tests/test_urace_usage_truth_contract.py](/home/host/Desktop/mvp/URACE/urace/runtime/tests/test_urace_usage_truth_contract.py) | added | identical | 11 | 44d1b90c7740a725b8fe9040a3160e37c505e926f235a173a489c9b7c606d60f |
| [runtime/tests/test_user_controls.py](/home/host/Desktop/mvp/URACE/urace/runtime/tests/test_user_controls.py) | added | identical | 47 | 137a1e6025b0c78fd660d31a9221c2bbeba42a250d14456d02821242951e418a |
| [runtime/tests/test_value_production.py](/home/host/Desktop/mvp/URACE/urace/runtime/tests/test_value_production.py) | identical | identical | 402 | 5a56f6ac80daee833e29fa60394d6d8e09774b86d99744ebe66a4d833f1b3525 |
| [runtime/urace/__init__.py](/home/host/Desktop/mvp/URACE/urace/runtime/urace/__init__.py) | identical | identical | 3 | 37bd43f5956056b68fddcab8a09ae63824a65f63d9cf0c12506af5da0ab84148 |
| [runtime/urace/__main__.py](/home/host/Desktop/mvp/URACE/urace/runtime/urace/__main__.py) | identical | identical | 3 | 52599717c0fc98e3c25187622b183a83d582b90854d2509bd739eb655844c75e |
| [runtime/urace/_common.py](/home/host/Desktop/mvp/URACE/urace/runtime/urace/_common.py) | changed | changed | 339 | fa9912d7d019c61f8c680abc3ee8130b89d5dd0fa1125e3e1f0695e1ef009063 |
| [runtime/urace/analytics.py](/home/host/Desktop/mvp/URACE/urace/runtime/urace/analytics.py) | identical | identical | 146 | 202c3e634f0303ecac1c18852b9c3420f24fe86c192f3c6d258b14260b73c63c |
| [runtime/urace/api_interface.py](/home/host/Desktop/mvp/URACE/urace/runtime/urace/api_interface.py) | added | identical | 157 | e20d9dc8ff01272d337347a44d266cf136d23d8dab2749e1c3cdf1e37ab8dfff |
| [runtime/urace/authority.py](/home/host/Desktop/mvp/URACE/urace/runtime/urace/authority.py) | identical | identical | 188 | f0dc035892768228876d60ffd1a4af1d31414db5a4dc79f2341533397488b223 |
| [runtime/urace/auto_goals.py](/home/host/Desktop/mvp/URACE/urace/runtime/urace/auto_goals.py) | added | changed | 76 | be4f8d24c8c3034834b08a1faa22cd84c09bcea1cb8b9d81bd36d32873e9d417 |
| [runtime/urace/bootstrap.py](/home/host/Desktop/mvp/URACE/urace/runtime/urace/bootstrap.py) | added | changed | 32 | 0ec751033767fca1b0a4035486b99f11d5e62a88408c3bf5d95b19e0d82ee48e |
| [runtime/urace/cli.py](/home/host/Desktop/mvp/URACE/urace/runtime/urace/cli.py) | changed | changed | 8961 | 9994ab518d171969ed7c9109bd909a65fb8d9f31af708ff058bbd2e499751b23 |
| [runtime/urace/cognitive_resume.py](/home/host/Desktop/mvp/URACE/urace/runtime/urace/cognitive_resume.py) | identical | identical | 243 | 7accb46f18a5e43009da9e5a3f73ff0079d845ba73fa63c295b05c6f71844c3b |
| [runtime/urace/command_surface.py](/home/host/Desktop/mvp/URACE/urace/runtime/urace/command_surface.py) | added | changed | 224 | b8175f76701ee93a77586909fcec89f9c4466efd77f6037e2a2e684e5c43a2db |
| [runtime/urace/compaction.py](/home/host/Desktop/mvp/URACE/urace/runtime/urace/compaction.py) | changed | identical | 1062 | 289854781a82462bf3bfd9c7e563173d8f11183533944dbccd2ffdaf9b5f4f50 |
| [runtime/urace/continuation.py](/home/host/Desktop/mvp/URACE/urace/runtime/urace/continuation.py) | identical | identical | 80 | ab4706f5967fa66214e2bf98eb63afce061b6a58f8fe366827445119783fe3d7 |
| [runtime/urace/data_transport.py](/home/host/Desktop/mvp/URACE/urace/runtime/urace/data_transport.py) | added | identical | 146 | 7743b97bd16a6cd8b0fc856c165e5db8dd5324d1d0880709760e7d08b4a1b2dc |
| [runtime/urace/decision_record.py](/home/host/Desktop/mvp/URACE/urace/runtime/urace/decision_record.py) | identical | identical | 363 | bfca409ff8af4436b34cf17941ba5e0806f0f3c8eb7a57327b5255933e2c0b6a |
| [runtime/urace/destination.py](/home/host/Desktop/mvp/URACE/urace/runtime/urace/destination.py) | identical | identical | 161 | 4faf0528396c6f5055e211f49eac8608752ce8b3e15fc9a00fbbd93af4fe6d2a |
| [runtime/urace/evolution_guard.py](/home/host/Desktop/mvp/URACE/urace/runtime/urace/evolution_guard.py) | identical | identical | 96 | 2884b2f2bdaff30df10ec5afaa4476e79a5f3498090414e31bc4e09323ec037d |
| [runtime/urace/executor.py](/home/host/Desktop/mvp/URACE/urace/runtime/urace/executor.py) | changed | changed | 959 | 514d99a082fd84833d96a0929e45d68fd3e7646a75a6560c7fd9d8cac2c78b6e |
| [runtime/urace/external_metrics.py](/home/host/Desktop/mvp/URACE/urace/runtime/urace/external_metrics.py) | changed | identical | 124 | 932c953956124972c5251c5507ce671934eb71b530324022a65e6ec24031eb22 |
| [runtime/urace/freeform_routing.py](/home/host/Desktop/mvp/URACE/urace/runtime/urace/freeform_routing.py) | added | changed | 169 | f95d4f5c749c94f1c8abfa6b2a8241b9c0b062b2ba9f4f4d415238c6b4b26379 |
| [runtime/urace/inputs.py](/home/host/Desktop/mvp/URACE/urace/runtime/urace/inputs.py) | changed | changed | 478 | b677ec688f4e06f4edb759aeb2cdd2d06e94855b5227cd6c69e41afdf2a81808 |
| [runtime/urace/inspection.py](/home/host/Desktop/mvp/URACE/urace/runtime/urace/inspection.py) | changed | changed | 846 | ba6612df3dfe4fcc24ac4bf48b03485ad703b3f33620f696f42e7ad5c2c8a1bd |
| [runtime/urace/launcher.py](/home/host/Desktop/mvp/URACE/urace/runtime/urace/launcher.py) | changed | changed | 117 | ba98bb4a458a149566f6e80027553335bf88c4d35c02e68169c5a0e338fc7ef9 |
| [runtime/urace/outcome_verification.py](/home/host/Desktop/mvp/URACE/urace/runtime/urace/outcome_verification.py) | identical | identical | 349 | e6d752a53079a554a1bad77008871ce98a40b1b96536dcd392f405cd43dc6715 |
| [runtime/urace/patterns.py](/home/host/Desktop/mvp/URACE/urace/runtime/urace/patterns.py) | identical | identical | 1348 | ca7a64eb5283cf6437d7ca21d8c037fd07bd1a5ed32531958e6c245b43ae6bc9 |
| [runtime/urace/portfolio.py](/home/host/Desktop/mvp/URACE/urace/runtime/urace/portfolio.py) | changed | changed | 2421 | fece0af159ba0766391be5b71b73b6b50837e6b39e920f87049ff250e986d49e |
| [runtime/urace/primitives.py](/home/host/Desktop/mvp/URACE/urace/runtime/urace/primitives.py) | identical | identical | 2339 | a4b5beae4f6875f871625734646aec32231311904b36f7a44733143e2b383a19 |
| [runtime/urace/resource_usage.py](/home/host/Desktop/mvp/URACE/urace/runtime/urace/resource_usage.py) | added | added | 122 | f80917078273cd8fa4f0a51b9d379f3754988418e44e405cf9ad565acc6a57e5 |
| [runtime/urace/rules.py](/home/host/Desktop/mvp/URACE/urace/runtime/urace/rules.py) | identical | identical | 619 | 7c82c585cb962201bb71106a051b6f60fac6c7d18b1aaed9ecba8f6b54643004 |
| [runtime/urace/schema_export.py](/home/host/Desktop/mvp/URACE/urace/runtime/urace/schema_export.py) | identical | identical | 42 | 2274c0df5273a603793ca87ba79c76597cba1ceccfb0667ab56bd4c63f4dde2e |
| [runtime/urace/scope_priority.py](/home/host/Desktop/mvp/URACE/urace/runtime/urace/scope_priority.py) | identical | identical | 103 | 230e2b8dea0236c53b8dc98eed0e5e6031de7c68e10a948bd200724619d06bab |
| [runtime/urace/spec_audit.py](/home/host/Desktop/mvp/URACE/urace/runtime/urace/spec_audit.py) | identical | identical | 376 | 295d64f14a5106bd8929181ac3aca603d5bb260d95eaad81b47da14f5b1f93d1 |
| [runtime/urace/trial.py](/home/host/Desktop/mvp/URACE/urace/runtime/urace/trial.py) | added | added | 60 | e28f6149b5bff7dc4fc18e79031b61574667a57dda0f5bf797038d90bb2de811 |
| [runtime/urace/trial_cli.py](/home/host/Desktop/mvp/URACE/urace/runtime/urace/trial_cli.py) | added | added | 26 | 67f44a54b00f08f1d5cb8e61f39f4e353d8e1b2007624eb257c86a04821d4c06 |
| [runtime/urace/updater.py](/home/host/Desktop/mvp/URACE/urace/runtime/urace/updater.py) | identical | identical | 370 | 7e9127f99b68c6a7a1129f63a34398fa0c3fd3cf39f2780aacb58ff98484d58e |
| [runtime/urace/user_controls.py](/home/host/Desktop/mvp/URACE/urace/runtime/urace/user_controls.py) | added | changed | 38 | 9bfedb47f5773d511c55b7f91fdfbef7d407fbd3489a4c5d4c569f69f28a8cac |
| [runtime/urace/validation.py](/home/host/Desktop/mvp/URACE/urace/runtime/urace/validation.py) | identical | identical | 206 | 7bbd2daa327a93447b6e98189299b434fa44d212802c6261eaab6b1b7be41595 |
| [runtime/urace/value_trajectory.py](/home/host/Desktop/mvp/URACE/urace/runtime/urace/value_trajectory.py) | identical | identical | 296 | ea99645711b7de9f3126f22df81b39b1305e22ae69f585063286f690321100d4 |
| [runtime/urace/workflow_state.py](/home/host/Desktop/mvp/URACE/urace/runtime/urace/workflow_state.py) | added | added | 205 | 20c15d87b1a210dbfda5915b4cd0a064a1ea96de70ca76eb914ab9fdd49811bd |
| [trial/accounting.py](/home/host/Desktop/mvp/URACE/urace/trial/accounting.py) | added | added | 24 | 1f741e5a967dd036fab1f59332147ee37aab65082b7f629f283ea20fe07cca37 |
| [trial/allocation.py](/home/host/Desktop/mvp/URACE/urace/trial/allocation.py) | added | added | 59 | 14fdd4c9526e0ac8dd00da8da26ef37deb04049124cfcbad857bbf1b7eb23efc |
| [trial/availability.py](/home/host/Desktop/mvp/URACE/urace/trial/availability.py) | added | added | 59 | aa5c702826e59681460aaf0cfc313f7ea9b7915ff89e3ba864f62dce6877dbd6 |
| [trial/common.py](/home/host/Desktop/mvp/URACE/urace/trial/common.py) | added | added | 64 | 59a6dd9db84d936c119d9b9b698c93f4d877ba3106e1e3e9a1933d9e50c55a3f |
| [trial/controls.py](/home/host/Desktop/mvp/URACE/urace/trial/controls.py) | added | added | 84 | 0617380e710ba2a29aeb355a5290b5c322b11e9cc3dfe63a5682f28107abebda |
| [trial/core_resources.py](/home/host/Desktop/mvp/URACE/urace/trial/core_resources.py) | added | added | 52 | 428f4a2ef98db7f465b1e1e66e4e5d93db9bc5be71dcac0057c70e3ba6943442 |
| [trial/efficiency_score.py](/home/host/Desktop/mvp/URACE/urace/trial/efficiency_score.py) | added | added | 93 | 2be62d03b2f0c7d6445b48b986b088c325c9bf7fa00be1e402ede9720120f8d1 |
| [trial/period_feedback.py](/home/host/Desktop/mvp/URACE/urace/trial/period_feedback.py) | added | added | 36 | 4c2a7a7a9d5a2c6bf92828fc21e3240f52aa1c102e8ce2162ce4c59c539c3c9c |
| [trial/product_resources.py](/home/host/Desktop/mvp/URACE/urace/trial/product_resources.py) | added | added | 61 | bb25a227111b96d03b17e1b7b3d2e6e69b75a1a329a1356e11c7394739b46d7b |
| [trial/providers.py](/home/host/Desktop/mvp/URACE/urace/trial/providers.py) | added | added | 187 | 82aa437a8e9962b18ac918ee2ebdba90efdd964cf6b6ab80638f9265cc2197db |
| [trial/resource_governor.py](/home/host/Desktop/mvp/URACE/urace/trial/resource_governor.py) | added | added | 100 | dcba7e553df6166aac204a99eef57362f0d79c651d42f93c675e27d6bf8012e9 |
| [trial/resource_report.py](/home/host/Desktop/mvp/URACE/urace/trial/resource_report.py) | added | added | 32 | 9ac2d71c913866d479d2b7393bfd75e71cf18969e04ba506f76f1f01e2e2e500 |
| [trial/review.py](/home/host/Desktop/mvp/URACE/urace/trial/review.py) | added | added | 66 | 0a18d0634dfad039f0e2a5c6ffc8909c21d6909e1be3a7e8bd4d7132fe2d7304 |
| [trial/routing.py](/home/host/Desktop/mvp/URACE/urace/trial/routing.py) | added | added | 25 | 2dfb925f2bdefda85129febe5b2c9def4a06e4f33161f39c8d72d6b03bc952be |
| [trial/snapshot_metadata.py](/home/host/Desktop/mvp/URACE/urace/trial/snapshot_metadata.py) | added | added | 154 | 22a0d4f3d18ddeebbe0661cd081ebe8a1e4950791cb688aeab14c29a626fead9 |
| [trial/source_integrity.py](/home/host/Desktop/mvp/URACE/urace/trial/source_integrity.py) | added | added | 46 | 5157d2954f53e02df739f437bf37f1f482fa2084e6c623b9f25990ce32a99796 |
| [trial/spec_trial.py](/home/host/Desktop/mvp/URACE/urace/trial/spec_trial.py) | added | added | 306 | f3f32a24162f872ff53f07dc526b61eadbed03c58d96b322429a2d1e96f394d5 |
| [trial/stream_usage.py](/home/host/Desktop/mvp/URACE/urace/trial/stream_usage.py) | added | added | 19 | 6751e8cd691c9e525ca26a4b412dc31601ee69677581290e740b2bf36349e143 |
| [trial/test_allocation.py](/home/host/Desktop/mvp/URACE/urace/trial/test_allocation.py) | added | added | 25 | d1157abc6fce0507cd0d94a408432db9849aec722478e10967798d23203d4663 |
| [trial/test_availability.py](/home/host/Desktop/mvp/URACE/urace/trial/test_availability.py) | added | added | 9 | b7c1886110bdce6d2f09afc8a677383a3e1c3f3791cca5c6596d19cfbec75859 |
| [trial/test_controls.py](/home/host/Desktop/mvp/URACE/urace/trial/test_controls.py) | added | added | 66 | 380556cde74b85be841a62ba32359f512cfd3ed6bda07bc13c11d9dade76c755 |
| [trial/test_efficiency_score.py](/home/host/Desktop/mvp/URACE/urace/trial/test_efficiency_score.py) | added | added | 38 | 2237a990233348087a9f9faa0a2a873ad924e267f2adb28cafe77e38c704cd53 |
| [trial/test_governor.py](/home/host/Desktop/mvp/URACE/urace/trial/test_governor.py) | added | added | 81 | b9662f03d9bf6075610c064f8ef3b00cec7fcf3c665af1975c547323d0462d4b |
| [trial/test_lifecycle.py](/home/host/Desktop/mvp/URACE/urace/trial/test_lifecycle.py) | added | added | 128 | d9f817ed51e951ee1eab2274cffe6c2def2c2440a0d0eec5ae513dc183236abc |
| [trial/test_product_resources.py](/home/host/Desktop/mvp/URACE/urace/trial/test_product_resources.py) | added | added | 64 | 8cf12fb380cdcf07660314c1ca2ad4e0aefa0f0d13a2e51e1a6c71d13f38ec2f |
| [trial/test_relocation.py](/home/host/Desktop/mvp/URACE/urace/trial/test_relocation.py) | added | added | 21 | 7738d6ef0ea0ff81d379397ee6dbe10babe6ae707b34a9206d7821bbbd8d1b0f |
| [trial/test_resource_report.py](/home/host/Desktop/mvp/URACE/urace/trial/test_resource_report.py) | added | added | 12 | 1f0cb4a0156d5a714ca17d89e2ae9fd71b98b760edea5156296df921b32af882 |
| [trial/test_snapshot_metadata.py](/home/host/Desktop/mvp/URACE/urace/trial/test_snapshot_metadata.py) | added | added | 54 | 13d491fc8e553b0855f5f742a2f37adff11472a05828f9451f87a96e31574f63 |
| [trial/test_source_integrity.py](/home/host/Desktop/mvp/URACE/urace/trial/test_source_integrity.py) | added | added | 19 | a3de1bfa11250b7fb3c5d1c091500b83042771b062a656348ff3b7d2471d258f |
| [trial/test_spec_trial.py](/home/host/Desktop/mvp/URACE/urace/trial/test_spec_trial.py) | added | added | 81 | c1c2025890e2d5966df83a9927767f12792e6d26cf5e2574575d71174379752b |

## Every uppercase trial file

| RUNTIME file → urace/trial | Comparison | Old lines | Current lines |
|---|---|---:|---:|
| .gitignore | changed | 20 | 37 |
| README.md | changed | 53 | 57 |
| accounting.py | changed | 16 | 24 |
| allocation.py | added | 0 | 59 |
| availability.py | added | 0 | 59 |
| common.py | changed | 36 | 64 |
| controls.py | added | 0 | 84 |
| core_resources.py | added | 0 | 52 |
| efficiency.example.json | identical | 23 | 23 |
| efficiency_score.py | identical | 93 | 93 |
| empty-mcp.json | identical | 1 | 1 |
| period_feedback.py | added | 0 | 36 |
| product_resources.py | changed | 55 | 61 |
| providers.py | changed | 182 | 187 |
| resource_governor.py | added | 0 | 100 |
| resource_report.py | added | 0 | 32 |
| review.py | added | 0 | 66 |
| routing.py | identical | 25 | 25 |
| snapshot_metadata.py | changed | 139 | 154 |
| source_integrity.py | added | 0 | 46 |
| spec_trial.py | changed | 244 | 306 |
| stream_usage.py | identical | 19 | 19 |
| test_allocation.py | added | 0 | 25 |
| test_availability.py | added | 0 | 9 |
| test_controls.py | added | 0 | 66 |
| test_efficiency_score.py | identical | 38 | 38 |
| test_governor.py | added | 0 | 81 |
| test_lifecycle.py | added | 0 | 128 |
| test_product_resources.py | changed | 57 | 64 |
| test_relocation.py | added | 0 | 21 |
| test_resource_report.py | added | 0 | 12 |
| test_snapshot_metadata.py | identical | 54 | 54 |
| test_source_integrity.py | added | 0 | 19 |
| test_spec_trial.py | identical | 81 | 81 |
| urace | changed | 81 | 66 |

## Full command grammar

Consistent original/current counting expands the portfolio grammar on both sides: **118 original paths; 161 current paths; no original path removed**. Earlier88→161 reporting incorrectly counted30 pre-existing portfolio paths as additions. Positional settings promoted to subcommands are structural changes, not newly invented capabilities.

Configuration --daily/--monthly moved under executor-budget; --component moved under evaluation-weight. Existing finite choices remain represented. New flags include auto --dry-run, init --ready, API --argv/--stream and commands discovery, data push --input-json, and analysis --period. Provider ceilings accept the explicit unlimited value and default to no local cap.

| Path | Positional arguments/action choices | Options/defaults |
|---|---|---|
| `help` | operation | --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `trial` |  |  |
| `trial status` |  |  |
| `trial status resources` |  | --product product [default=None]; --all-products all_products [default=False]; --executor executor {all, codex, claude} [default=all]; --scope scope {trial, epoch, lifetime} [default=trial]; --json json [default=False] |
| `trial status runtime` |  | --json json [default=False] |
| `trial status analysis` |  | --kind analysis_scope {snapshot, product, runtime} [default=product]; --version version [default=None]; --json json [default=False]; --period period {3h, day, week, month} [default=None] |
| `trial config` |  |  |
| `trial config efficiency` |  | --product product [default=*]; --executor executor {all, codex, claude} [default=all]; --scope scope {trial, epoch, lifetime} [default=trial]; --file file [default=None]; --show show [default=False]; --disable disable [default=False]; --review review [default=False] |
| `trial data` |  |  |
| `trial data metrics` |  |  |
| `trial data metrics record` |  | --product product [default=URACE.md]; --executor executor {all, codex, claude} [default=all]; --name name [default=None]; --value value [default=None]; --unit unit [default=]; --source source [default=None] |
| `trial data metrics show` |  | --product product [default=URACE.md]; --executor executor {all, codex, claude} [default=all] |
| `init` |  | --ready ready [default=False] |
| `check` |  | --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==]; --fail-on fail_on {BLOCKING, WARNING, INFO} [default=None]; --migration-dry-run migration_dry_run [default=False] |
| `vitals` |  | --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==]; --since since [default=None]; --until until [default=None]; --limit limit [default=None]; --fail-on fail_on {BLOCKING, WARNING, INFO} [default=None] |
| `change` | action {list, explain}; id | --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `configuration` |  | --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `configuration show` |  | --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `configuration workflow` | value | --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `configuration self-evolution` | value | --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `configuration change-explanations` | value | --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `configuration external-metrics` | value | --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `configuration analytics-export` | value | --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `configuration executor-budget` | value | --daily daily [default=None]; --monthly monthly [default=None]; --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `configuration evaluation-minimum` | value | --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `configuration evaluation-weight` | value | --component component [default=None]; --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `configuration auto-goals` | action {status, enable, disable, replenish}; value {status, enable, disable} | --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `configuration effort` | mode {status, low, medium, high, inherit} | --executor executor_id [default=None]; --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `configuration executor` | executor_id | --model model [default=None]; --inherit-model inherit_model [default=False]; --native-effort native_effort {low, medium, high, inherit} [default=None]; --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `self-evolution` | mode {status, auto, always, never} | --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `commands` |  | --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `inbox` | action {list, status, apply, reject, help}; input_id | --reason reason [default=None]; --kind kind [default=None]; --status status {QUEUED, REJECTED, PROCESSED} [default=None]; --limit limit [default=None]; --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `onboard` | action {status, confirm, help} | --note note [default=None]; --scan scan [default=False]; --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `product` | action {list, status, switch, register, remove, deactivate, activate, help}; name | --state-path product_state_path [default=None]; --product-files product_files [default=[]]; --intent-purpose intent_purpose [default=None]; --reason reason [default=None]; --force force [default=False]; --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `fleet` | action {run, status, stop, broadcast, help}; name | --dry-run dry_run [default=False]; --verbose verbose [default=False]; --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `data` |  |  |
| `data add` | name | --type adapter_kind [default=None]; --connect dsn [default=None]; --direction direction {read, write, both} [default=read]; --auto auto [default=True]; --schema schema_hint [default=None]; --label label [default=]; --format format {text, json} [default=text]; --json format [default===SUPPRESS==] |
| `data update` | name | --type adapter_kind [default=None]; --connect dsn [default=None]; --direction direction {read, write, both} [default=None]; --auto auto [default=None]; --schema schema_hint [default=None]; --label label [default=None]; --format format {text, json} [default=text]; --json format [default===SUPPRESS==] |
| `data remove` | name | --format format {text, json} [default=text]; --json format [default===SUPPRESS==] |
| `data list` |  | --type adapter_kind [default=None]; --direction direction {read, write, both} [default=None]; --status status {CONNECTED, DISCONNECTED, DEGRADED, PENDING} [default=None]; --format format {text, json} [default=text]; --json format [default===SUPPRESS==] |
| `data sync` | name | --format format {text, json} [default=text]; --json format [default===SUPPRESS==] |
| `data push` | name | --input-json data_input_json [default=None]; --format format {text, json} [default=text]; --json format [default===SUPPRESS==] |
| `data inspect` | name | --format format {text, json} [default=text]; --json format [default===SUPPRESS==] |
| `data verify` | name | --format format {text, json} [default=text]; --json format [default===SUPPRESS==] |
| `data status` |  | --format format {text, json} [default=text]; --json format [default===SUPPRESS==] |
| `data credential` |  |  |
| `data credential add` | name | --auth auth_kind {DSN, API_KEY, OAUTH2, CERT, BASIC, KERBEROS, IAM_ROLE, VAULT_PATH, ENV_VAR} [default=None]; --ref secret_ref [default=None]; --expires expires_at [default=None]; --format format {text, json} [default=text]; --json format [default===SUPPRESS==] |
| `data credential remove` | name | --format format {text, json} [default=text]; --json format [default===SUPPRESS==] |
| `data credential inspect` | name | --format format {text, json} [default=text]; --json format [default===SUPPRESS==] |
| `trace` | action {list, inspect, help}; trace_id | --kind kind {CYCLE, OPERATION, DECISION, TRANSITION, GAP, ONBOARD, SWITCH, FLEET} [default=None]; --cycle-id cycle_id [default=None]; --since since [default=None]; --until until [default=None]; --limit limit [default=50]; --offset offset [default=0]; --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `schema` | action {list, inspect, export, help}; schema_command | --target target {output-schemas, bundles, all} [default=all]; --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `feedback` | action {list, submit, help}; target_id | --signal signal {POSITIVE, NEGATIVE, NEUTRAL} [default=None]; --detail detail [default=]; --evidence evidence_id [default=None]; --target filter_target [default=None]; --limit limit [default=20]; --offset offset [default=0]; --input-json input_json [default=None]; --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `resource` | action {status, report, help} | --since since [default=None]; --until until [default=None]; --limit limit [default=20]; --offset offset [default=0]; --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `derive` | intent | --constructs/--patterns constructs [default=None]; --kind kind [default=pattern]; --suggest suggest [default=False]; --from-goals from_goals [default=False]; --from-constraints from_constraints [default=False]; --from-inspection from_inspection [default=False]; --exclude exclude [default=None]; --exclude-reason exclude_reason [default=]; --out out [default=None]; --save save [default=False]; --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==]; --derive-capabilities derive_capabilities [default=False]; --apply-capabilities apply_capabilities [default=False]; --refresh refresh [default=False]; --manifest-id manifest_id [default=None]; --show-delta show_delta [default=False]; --derive-milestone derive_milestone [default=False]; --bundle bundle [default=None]; --list-bundles list_bundles [default=False]; --verify verify [default=False]; --no-verify no_verify [default=False]; --hash derive_expected_hash [default=None] |
| `context` | action {list} | --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `add-context` | text | --source source [default=repository owner]; --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `classify` | text | --confirm confirm [default=False]; --selection selection [default=None]; --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `add-goal` | title | --success-measure success_measure [default=None]; --reason reason [default=None]; --target target {product, urace} [default=product]; --priority priority [default=70]; --expected-value expected_value [default=0.7]; --outcome-measure outcome_measure [default=None]; --estimated-cost estimated_cost [default=0.5]; --risk risk [default=0.3]; --urgency urgency [default=0.5]; --depends-on depends_on [default=[]]; --deadline deadline [default=None]; --not-before not_before [default=None]; --estimate-min-hours estimate_min_hours [default=0]; --estimate-max-hours estimate_max_hours [default=0]; --estimate-confidence estimate_confidence {low, medium, high} [default=low]; --priority-floor priority_floor [default=None]; --priority-ceiling priority_ceiling [default=None]; --pin pin [default=False]; --necessity-evidence necessity_evidence [default=None]; --lower-impact-insufficient lower_impact_insufficient [default=False]; --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `intent` | action {add, list, supersede, deactivate, rollback}; statement | --id rule_id [default=None]; --scope scope [default=product]; --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `constraint` | action {add, list, deactivate}; statement | --id rule_id [default=None]; --allow allow [default=False]; --scope scope [default=product]; --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `rules` | action {list, inspect, graph, conflicts, changes}; id | --kind kind [default=None]; --scope scope [default=None]; --inferred inferred [default=False]; --since since [default=None]; --until until [default=None]; --limit limit [default=None]; --offset offset [default=0]; --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `add-source` | id; kind; location | --visibility visibility {public, private} [default=private]; --credential-env credential_env [default=None]; --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `add-metric` | name | --source source [default=None]; --path path [default=None]; --direction direction {nondecreasing, nonincreasing} [default=nondecreasing]; --target target [default=None]; --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `add-vital` | name | --numerator numerator [default=None]; --denominator denominator [default=None]; --window window [default=current]; --description description [default=]; --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `add` |  |  |
| `add context` | text | --source source [default=repository owner]; --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `add goal` | title | --success-measure success_measure [default=None]; --reason reason [default=None]; --target target [default=None]; --priority priority [default=70]; --expected-value expected_value [default=0.5]; --estimated-cost estimated_cost [default=0.3]; --risk risk [default=0.3]; --urgency urgency [default=0.5]; --necessity-evidence necessity_evidence [default=None]; --lower-impact-insufficient lower_impact_insufficient [default=False]; --depends-on depends_on [default=[]]; --deadline deadline [default=None]; --not-before not_before [default=None]; --estimate-min-hours estimate_min_hours [default=0]; --estimate-max-hours estimate_max_hours [default=0]; --estimate-confidence estimate_confidence {low, medium, high} [default=low]; --priority-floor priority_floor [default=None]; --priority-ceiling priority_ceiling [default=None]; --pin pin [default=False]; --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `add source` | id | --kind kind [default=None]; --location location [default=None]; --visibility visibility [default=private]; --credential-env credential_env [default=None]; --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `add metric` | name | --source source [default=None]; --path path [default=None]; --direction direction {nondecreasing, nonincreasing} [default=nondecreasing]; --target target [default=None]; --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `add vital` | name | --numerator numerator [default=None]; --denominator denominator [default=None]; --window window [default=None]; --description description [default=None]; --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `add evidence` |  | --kind kind [default=None]; --summary summary [default=None]; --source source [default=None]; --detail detail [default=None]; --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `add principal` | name | --precedence precedence [default=1]; --scope scope [default=product]; --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `declare` |  |  |
| `declare context` | declare_remainder |  |
| `declare goal` | declare_remainder |  |
| `declare source` | declare_remainder |  |
| `declare metric` | declare_remainder |  |
| `declare vital` | declare_remainder |  |
| `explain` | id | --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `source` | action {list, enable, disable, remove}; id | --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `metric` | action {list, remove}; name | --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `vital` | action {list, remove}; name | --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `goal` | action {list, inspect, forecast, prioritize, schedule, pin, unpin, defer, resume, resolve-update, disable, cancel, delete}; id | --priority priority [default=None]; --floor floor [default=None]; --ceiling ceiling [default=None]; --until until [default=None]; --deadline deadline [default=None]; --not-before not_before [default=None]; --clear-deadline clear_deadline [default=False]; --clear-not-before clear_not_before [default=False]; --estimate-min-hours estimate_min_hours [default=None]; --estimate-max-hours estimate_max_hours [default=None]; --estimate-confidence estimate_confidence {low, medium, high} [default=None]; --depends-on depends_on [default=None]; --clear-dependencies clear_dependencies [default=False]; --decision decision [default=None]; --status status {active, pending, blocked, resolved, cancelled, all} [default=active]; --limit limit [default=20]; --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `policy` | action {list, set}; name {self-evolution, external-metrics, analytics-export}; value | --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `budget` | action {show, set} | --daily daily [default=None]; --monthly monthly [default=None]; --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `evaluation` | action {show, set-weight, set-minimum}; component; value | --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `report` | action {status, export} | --output output [default=urace/generated/reports/latest]; --xlsx xlsx [default=False]; --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `update` | action {download, explain, apply, resolve, help}; reference | --decision decision [default=None]; --opt-in-constructs/--opt-in-patterns opt_in_constructs [default=None]; --hash expected_hash [default=None]; --verify verify [default=False]; --no-verify no_verify [default=False]; --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `portfolio` | portfolio_args | --help portfolio_help [default=False] |
| `portfolio init` |  | --objective objective [default=None]; --metric metric [default=None]; --direction direction {maximize, minimize} [default=None]; --minimum-evidence minimum_evidence [default=3]; --max-active max_active [default=3]; --authority authority [default=None]; --guardrail-definition guardrail_definition [default=None]; --evaluation-protocol evaluation_protocol [default=None]; --context-snapshot context_snapshot [default=None] |
| `portfolio spawn` | variant | --parent parent [default=None]; --mutation mutation [default=None]; --hypothesis hypothesis [default=None]; --expected-effect expected_effect [default=None]; --lesson lesson [default=[]]; --decision decision [default=[]] |
| `portfolio cohort` |  | --count count [default=None]; --prefix prefix [default=None]; --plan plan [default=None]; --parent parent [default=None]; --total-resource-budget total_resource_budget [default=None]; --resource-unit resource_unit [default=None] |
| `portfolio run-cohort` | cohort; command | --timeout timeout [default=300]; --max-parallel max_parallel [default=None] |
| `portfolio run` | variant; command | --timeout timeout [default=300] |
| `portfolio autonomous` |  | --workflow workflow [default=None]; --cycles cycles [default=1] |
| `portfolio policy` | mode {adaptive, always, auto, disabled, enabled, off} |  |
| `portfolio policy-status` |  | --json json [default=False] |
| `portfolio accepted-state-source` | mode {lifecycle, repository} | --ref ref [default=None] |
| `portfolio accepted-state-source-status` |  | --json json [default=False] |
| `portfolio preflight` | workflow | --json json [default=False] |
| `portfolio verify` |  | --json json [default=False] |
| `portfolio launch` | workflow |  |
| `portfolio auto` | workflow | --cycles cycles [default=None] |
| `portfolio next` | workflow |  |
| `portfolio record` | variant | --value value [default=None]; --resource-cost resource_cost [default=0]; --evidence-units evidence_units [default=1]; --guardrails guardrails {pass, fail} [default=None]; --note note [default=] |
| `portfolio rank` |  | --cohort cohort [default=None] |
| `portfolio select` | variant | --cohort cohort [default=None] |
| `portfolio stop` | variant |  |
| `portfolio review` | reviewer; subject | --finding finding [default=None]; --evidence evidence [default=None]; --recommendation recommendation [default=None]; --confidence confidence [default=None] |
| `portfolio agora-propose` | variant | --decision decision [default=None]; --rationale rationale [default=None]; --evidence evidence [default=None]; --counterevidence counterevidence [default=None]; --applicability applicability [default=None]; --expected-effect expected_effect [default=None]; --scope scope {candidate, portfolio-system} [default=candidate]; --necessity-evidence necessity_evidence [default=None]; --experiment-benefit experiment_benefit [default=None]; --invariants-preserved invariants_preserved [default=None] |
| `portfolio agora-vote` | voter; proposal | --choice choice {support, oppose, abstain} [default=None]; --reason reason [default=None]; --evidence evidence [default=None]; --confidence confidence [default=None] |
| `portfolio agora-decide` | proposal | --outcome outcome {adopt, refer, reject, defer} [default=None]; --approved-by approved_by [default=None]; --reason reason [default=None]; --applicability applicability [default=None]; --minimum-support minimum_support [default=1]; --inherit-from inherit_from [default=None] |
| `portfolio agora-confirm-system` | proposal | --approved-by approved_by [default=None]; --validation-evidence validation_evidence [default=None]; --experiment-benefit experiment_benefit [default=None]; --invariants-preserved invariants_preserved [default=False]; --bonus bonus [default=0] |
| `portfolio agora-show` |  |  |
| `portfolio lesson` |  | --from-variants from_variants [default=None]; --statement statement [default=None]; --evidence evidence [default=None]; --counterevidence counterevidence [default=None]; --applicability applicability [default=None]; --confidence confidence [default=None]; --approved-by approved_by [default=None] |
| `portfolio explain` |  |  |
| `portfolio status` |  |  |
| `portfolio feedback` |  | --json json [default=False] |
| `portfolio commands` |  | --json json [default=False] |
| `plan` |  | --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `auto` |  | --dry-run dry_run [default=False]; --cycles cycles [default=0]; --interval interval [default=30]; --force-discovery force_discovery [default=False]; --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==]; --quiet quiet [default=False]; --verbose verbose [default=False] |
| `executor` | action {status, attach, detach, retry-policy} | --command executor_binary [default=None]; --id executor_id [default=codex-primary]; --adapter adapter {codex-cli, claude-cli} [default=codex-cli]; --priority priority [default=100]; --capability capability {discovery, planning, mutation, evaluation, execution} [default=None]; --capability-priority capability_priority [default=[]]; --max-calls-24h max_calls_24h [default=None]; --max-calls-30d max_calls_30d [default=None]; --retry-mode retry_mode {automatic, dynamic, fixed} [default=automatic]; --retry-delay-ms retry_delay_ms [default=60000]; --retry-fallback-seconds retry_fallback_seconds [default=18000]; --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `repair-controller` |  | --component component {portfolio} [default=None]; --code code {ACTIVE_COHORT_ACCOUNTING, UNEXPECTED_CONTROLLER_EXCEPTION} [default=None]; --phase phase {IDLE, PLANNED, CREATED, MUTATED, EVALUATED, UNKNOWN} [default=None]; --exception-class exception_class {SystemExit, AssertionError, AttributeError, KeyError, TypeError} [default=None]; --confirmed-recurrence confirmed_recurrence [default=False] |
| `executor-capacity` | action {defer, clear} | --retry-at retry_at [default=None]; --stage stage [default=portfolio] |
| `api` | action {call, batch, help, watch, version, commands} | --argv argv [default=None]; --stream stream [default=False]; --command api_command [default=None]; --params params [default=None]; --input-json input_json [default=None]; --continue-on-error continue_on_error [default=False]; --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==]; --kinds kinds [default=]; --since since [default=None]; --follow follow [default=False] |
| `pause` |  | --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `resume` |  | --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `compact` | field_path | --dry-run dry_run [default=False]; --mode mode {ARCHIVE, ROLLING_EVICTION} [default=None]; --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==]; --status status [default=False]; --target target [default=None]; --product product [default=None]; --products product [default=None] |
| `compress` | field_path | --dry-run dry_run [default=False]; --mode mode {ARCHIVE, ROLLING_EVICTION} [default=None]; --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==]; --status status [default=False]; --target target [default=None]; --product product [default=None]; --products product [default=None] |
| `decompact` | compaction_event_id | --field-path field_path [default=None]; --record-id record_id [default=None]; --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==]; --target target [default=None]; --product product [default=None]; --products product [default=None] |
| `decompress` | compaction_event_id | --field-path field_path [default=None]; --record-id record_id [default=None]; --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==]; --target target [default=None]; --product product [default=None]; --products product [default=None] |
| `amend` | compaction_event_id; record_id | --notice notice [default=None]; --kind kind {PROVENANCE_REVISED, SUPERSEDED, CUSTOM} [default=PROVENANCE_REVISED]; --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==]; --target target [default=None]; --product product [default=None] |
| `why` | decision_id | --depth depth [default=None]; --limit limit [default=None]; --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `crc` | action {show, regenerate} | --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==]; --product product [default=None]; --products product [default=None] |
| `quality` |  | --scope scope [default=None]; --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `compliance` |  | --domain domain {authority, intent, schema, constraint, governance} [default=None]; --history history [default=10]; --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `milestone` |  | --scope scope [default=None]; --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `evidence` | action {list} | --kind kind [default=None]; --since since [default=None]; --until until [default=None]; --limit limit [default=20]; --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `blocker` | action {list, resolve}; blocker_id | --resolved resolved [default=False]; --scope scope [default=None]; --note note [default=None]; --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `decision` | action {list, inspect}; decision_id | --stale stale [default=False]; --scope scope [default=None]; --limit limit [default=20]; --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `integrity-signal` | action {list} | --type signal_type [default=None]; --severity severity {BLOCKING, WARNING, INFO} [default=None]; --resolved resolved [default=False]; --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `govern` | action {clear, list-gates}; gap_id | --note note [default=None]; --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `autonomous` |  | --dry-run dry_run [default=False]; --cycles cycles [default=0]; --interval interval [default=30]; --force-discovery force_discovery [default=False]; --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==]; --quiet quiet [default=False]; --verbose verbose [default=False] |
| `status` |  | --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `status runtime` |  | --fail-on fail_on {BLOCKING, WARNING, INFO} [default=None]; --migration-dry-run migration_dry_run [default=False]; --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `status vitals` |  | --since since [default=None]; --until until [default=None]; --limit limit [default=None]; --fail-on fail_on {BLOCKING, WARNING, INFO} [default=None]; --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `status executors` |  | --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `status resources` |  | --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==]; --product product [default=None]; --all-products all_products [default=False]; --executor executor {codex, claude, all} [default=None]; --scope scope {trial, epoch, lifetime} [default=None] |
| `status products` |  | --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `status fleet` |  | --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `status data` |  | --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `status quality` |  | --scope scope [default=None]; --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `status compliance` |  | --domain domain {authority, intent, schema, constraint, governance} [default=None]; --history history [default=10]; --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `status milestones` |  | --scope scope [default=None]; --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `status blockers` |  | --resolved resolved [default=False]; --scope scope [default=None]; --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `status integrity` |  | --type signal_type [default=None]; --severity severity {BLOCKING, WARNING, INFO} [default=None]; --resolved resolved [default=False]; --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `status onboarding` |  | --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `status configuration` |  | --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `status inbox` |  | --kind kind [default=None]; --status status {QUEUED, REJECTED, PROCESSED} [default=None]; --limit limit [default=None]; --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `status goals` |  | --status status {active, pending, blocked, resolved, cancelled, all} [default=active]; --limit limit [default=20]; --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |
| `status evaluation` |  | --format format {json, xml} [default===SUPPRESS==]; --json format [default===SUPPRESS==] |

## Scope accounting and what is not introduced

| Scope | Work | Remaining boundary |
|---|---|---|
| Parent public repository | Preserved owner work and repository separation | No parent commit/push |
| Original lowercase runtime | Preserved lifecycle/authority/data/compaction/API capabilities; imported prior improvements and applied fixes | Full all-feature live/customer proof is not established |
| Earlier external candidate | All57 source/test files included; modifications explicitly diffed | Historical qualification is not substituted for current qualification |
| Uppercase trial | Full source/evidence archive and migration comparison | Retirement only after qualified/live verification |
| Canonical trial | Core-integrated Product workflow, native transports, gates, snapshots, accounting, feedback/review | Actual quota/auth/safety/expiry boundaries remain |
| Host services | Canonical worker, watchdog, metadata monitor and three-hour reviewer | Local-host recovery; no cross-host disaster guarantee |
| Analysis | Per-version, Product and registered-runtime metadata, raw receipts and formula provenance | No invented remote CPU/GPU, subscription charges, customer outcomes or calibration |
| Git | Separate local runtime repository and preserved initial-trial history | Final commit state recorded in release evidence; no remote push |

Not introduced or guaranteed: unrestricted unattended source rewrites; cloud hosting/failover; actual-user market-fit proof; globally optimal allocation; universally correct arbitrary-input inference; indefinite maintenance-free reliability; guessed credit/billing values; unsupported connectors presented as working. Engineering simulations remain labeled.

Exact diffs: [/home/host/urace-evidence/alignment-fixes-20261023T053658Z/original-to-canonical.diff](/home/host/urace-evidence/alignment-fixes-20261023T053658Z/original-to-canonical.diff), [/home/host/urace-evidence/alignment-fixes-20261023T053658Z/external_candidate-to-canonical.diff](/home/host/urace-evidence/alignment-fixes-20261023T053658Z/external_candidate-to-canonical.diff), [/home/host/urace-evidence/alignment-fixes-20261023T053658Z/RUNTIME-to-canonical.diff](/home/host/urace-evidence/alignment-fixes-20261023T053658Z/RUNTIME-to-canonical.diff).
