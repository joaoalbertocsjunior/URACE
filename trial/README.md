# URACE specification improvement trial

Product: `URACE.md`. Runtime engine: this `urace/trial/` directory. Baseline: user-selected committed `URACE.md`, Git 5688fda7911f8b14fed4284e54938602456fb318. The original working specification is untouched.

The active version-0 baseline is inside the snapshot series identified by `version-series.json`. Previous baseline series remain intact. Every accepted improvement gets a monotonically numbered `vNNNNNN` snapshot with source/parent/baseline hashes, acceptance evidence, native time/token receipts, and `parent.diff` plus `baseline.diff`. `version-comparisons.json` indexes the complete version chain. Timestamps supplement version comparisons. Rejected candidates remain in `runs/`, outside the accepted chain. Previous runtime-code trials remain historical and are not pooled as specification improvements.

The worker proposes bounded clarity corrections to existing specification sections; it preserves normative requirement sentences, headings and code fences, requires an existing contract quote and a separate critical model review. A different provider reviews when eligible; otherwise a separate invocation of the available provider reviews. Model scores are judgments, not executable validation or guarantees. New runtime behaviors are ineligible for this editorial trial. Large sections outside the context bound are not claimed as audited. Runtime engine changes are performed separately by us.

Run `python3 spec_trial.py status` for current health; services provide automatic work and three-hour reviews. Aggregate token/time spending caps are disabled by owner request; provider availability and runaway guards remain. A new trial window does not reset spending. Original files and Git index are not modified.

Resource counters now use the explicit accounting epoch in `accounting-epoch.json`. Status headline tokens, calls and executor seconds start at zero for that epoch; explicit `--scope lifetime` reports and append-only ledgers retain earlier costs. Per-version resource receipts remain unchanged. Tokens per accepted improvement include rejected-attempt costs and are withheld when usage is unknown or no improvement has been accepted.

Product/executor resource CLI (from the project root):

```sh
./urace/.urace/bin/urace trial status resources --product URACE.md
./urace/.urace/bin/urace trial status resources --product URACE.md --executor codex --scope lifetime
./urace/.urace/bin/urace trial status resources --all-products --executor claude --json
./urace/.urace/bin/urace trial status resources --all-products --scope lifetime --json
./urace/.urace/bin/urace trial status runtime --json
```

Reports include tokens, missing usage, calls, executor seconds, review outcomes and descriptive efficiency ratios. New reservations, native receipts and task reports carry a stable product identity. `products.json` explicitly binds earlier untagged RUNTIME events to this product; no other legacy trials are inferred into this product. All-products means registered products; currently URACE.md. Executor-specific task counts mean participation and may overlap. Efficiency is accepted editorial outcomes per token and elapsed hour, with all rejected costs included; these measurements alone do not demonstrate user benefit.

Custom efficiency scoring:

```sh
./urace/.urace/bin/urace trial config efficiency --show
./urace/.urace/bin/urace trial config efficiency --product URACE.md --file urace/trial/efficiency.example.json
./urace/.urace/bin/urace trial config efficiency --product URACE.md --review
./urace/.urace/bin/urace trial data metrics record --product URACE.md --name quality --value 8 --unit points --source "your actual evaluation reference"
./urace/.urace/bin/urace trial data metrics show --product URACE.md
```

The example weights and targets are illustrative, not calibrated or automatically enabled. Definitions use weighted normalized metrics (higher: min(value/target,1); lower: min(target/value,1), with zero lower-cost value mapped to1). `custom.NAME` can reference supplied observations; these remain explicitly unverified. Required missing data withholds the score. User-defined scoring never overrides acceptance or authority gates.

Every resource inspection saves its raw metrics, formula hash and methodology review under `reports/resource-inspections/`. Every calculation screens sample size, missing usage, metric balance and gaming risks, and identifies the lack of held-out calibration. Formula changes retain prior definitions in `history/`; scores under different formula hashes must not be compared without rescoring the same raw samples. A score is provisional until its relationship to independently validated outcomes is established; no formula is claimed best merely because it produces higher scores.

Freeform P2P retrieval now has an explicit sequence: classify source-grounded goals/intents first, search bounded local and authenticated peer catalogs only when actionable intent exists, rank each asset against those fields, then present candidates for explicit user review. Minted initial-ledger features with exact runtime-module tags carry source paths, byte counts and hashes; the runtime resolver checks those bindings against the local checkout and marks verified implementations in the candidate result. This metadata identifies local code but does not itself create a downloadable asset or qualify its quality. No asset is borrowed or executed automatically. A displayed `match_score` is a lexical retrieval heuristic, not a probability of equivalence, product quality, or savings. The entire built-in ledger is ranked before the top-ten display cap; remote discovery retrieves bounded catalogs before local ranking so raw-word filtering cannot discard paraphrased candidates. Conversational input with no actionable goal/intent does not trigger catalog discovery.

The synthetic 30-pair transport cohort now packages actual Apache-2.0 local modules named by minted-feature source bindings. Each task plan pins feature ID, module paths, source manifest and artifact digests; the verifier checks the bundle against the local ledger and current source files. Task outcomes, value scores, provider receipts and USD cost inputs remain synthetic. Source-backed bytes make asset identity and transfer sizes representative of URACE code, but they do not establish that an asset improves a task or lowers real executor cost.

Measure retrieval quality on held-out cases with real user tasks and human-labeled relevant assets before changing ranking weights or claiming ranking improvement. Use two independent reviewers, adjudicate disagreements, and keep test cases separate from development/tuning cases. Each JSONL dataset starts with a header containing `schema` (`urace-p2p-retrieval-dataset-v1`), `dataset_kind`, `split`, `independent_reviewers`, `disagreements_adjudicated`, `source_description`, and `case_count`; each following row contains a unique `case_id`, `raw_text`, validated `batch`, candidate `features`, and nonempty `relevant_candidate_ids`. Run:

```sh
python3 trial/p2p_retrieval_benchmark.py /path/to/held-out-retrieval.jsonl
```

The tool compares raw-request ranking with classified-intent ranking using Recall@1/3/5, NDCG@1/3/5, and MRR@1/3/5, and includes the dataset hash. Its review metadata is self-reported; even a held-out retrieval gain is only evidence about asset ranking, not accepted work, value, or cost. No real labeled retrieval dataset is currently included, so no empirical retrieval gain is claimed. The paired 30-task live cohort remains necessary to assess delivered value and end-to-end costs.

P2P-first versus direct-executor comparisons use the separate `p2p_pair_protocol.py` evidence contract. It reconciles transport receipts, signed acceptance and normalized value scores (including failed outcomes), seller-pinned bundle and portable acknowledgement signatures, artifact bytes, and paired cost receipts. It reports value, provider-native tokens, provider-cost basis, other USD costs, URACE units, and measured discovery/fetch/network/integration/validation separately. Exact task and acceptance/rubric text are hash-frozen; each evaluator-signed arm result must include a value score from 0 to 1 under that same rubric. A paired cost receipt must cover both arms and state the same provider billing basis; URACE units remain separate until a defensible conversion is verified. Even a complete 30-pair live result supports only a cohort-specific claim pending independent review, not general market savings.

The economic claim gate is frozen in each study plan. A LIVE plan requires a source-custodian signature over the source-corpus digest and exact selected task manifest; the two final reviewers also sign attestations that they reviewed the evidence and workload provenance and confirm their independence. These signatures make the statements attributable and auditable; they do not automatically prove that a custodian or reviewer is honest. Eligibility requires a complete 30-pair LIVE cohort (at least six per family), acceptance in both arms for every pair, P2P value no lower in every pair, complete comparable USD totals, zero URACE units, an allowed provider billing basis, and a paired 95% bootstrap upper bound below zero. `trial/p2p_cost_claim_review.py` then requires two distinct pinned reviewer signatures bound to the exact cohort hash and summary bytes. The output receipt scopes any claim to that cohort only. Synthetic or unspecified evidence can never pass this step; no result here creates a general executor-price guarantee.

The local synthetic protocol run samples 30 of the 1,392 initial-ledger features (six per each of five families). This is the intended bounded feature subset for protocol validation, not a representative set of product workloads. Its source assets are actual local URACE modules; tasks, acceptance, value, provider token receipts, and USD fixtures are constructed. A real cost claim still requires real product workloads and product-specific adapters.

Freeze a counterbalanced cohort before collecting results. Supply exactly 30 task manifests, six per family. Each must include nonempty `task_specification`, `acceptance_contract`, and `value_rubric` UTF-8 text (each at most 128 KiB) with SHA-256 hashes of those exact strings. One value rubric is pinned per task family. The identity pins evaluator public key and provider/model/client-version/native-effort profile. Seeded order is balanced 3:3 within each family. Use a new output path; plans refuse overwrite:

```sh
python3 p2p_study_plan.py --tasks tasks.json --identity identity.json \
  --seed 20261108 --output /path/to/frozen-study/cohort-plan.json
```

Collect both arms according to `pairs[].arm_order`, preserving that planned identity and order in each pair row. Then run the read-only verifier:

```sh
PYTHONPATH=../runtime python3 p2p_pair_protocol.py \
  --study-root /path/to/frozen-study \
  --plan /path/to/frozen-study/cohort-plan.json \
  --pairs /path/to/frozen-study/pairs.jsonl
```

Each JSONL row is one attempted pair; include failed and incomplete attempts. Acceptance failures remain measured outcomes with a signed normalized value score; do not discard them. For a P2P arm with no provider call, include the independent evaluator's signed no-call receipt; missing usage is never treated as zero. Fee amounts must reconcile to the buyer's audit ledger. Cost receipts bind measured discovery/fetch time and bytes plus complete paired cost dimensions under a frozen methodology. Exit code 0 means all predeclared pairs passed evidence and coverage checks and are ready for independent review, not that total economic savings are proven. Exit code 2 means invalid/incomplete evidence or verifier input error.

Run the deterministic synthetic integration cohort without provider calls or external peers:

```sh
python3 p2p_synthetic_cohort.py
```

It creates 30 synthetic product tasks (six per family), 30 synthetic assets, and uses two localhost-only mutually authenticated peers for real catalog discovery, fetch, quarantine, and portable seller-ack verification. Value scores, provider usage receipts, and USD cost fixtures are synthetic. Its report is explicitly `SYNTHETIC_PIPELINE_VALIDATION_ONLY`; it is not a live benchmark or savings evidence.

`p2p_study_runner.py` is the live coordinator interface. It requires pinned product-specific arm, independent evaluator, and cost adapters plus a preconfigured buyer exchange and seller allowlist. `--preflight` performs local checks without contacting peers or invoking providers; `--run-live` is the explicit live-effect gate. A live cohort still requires the adapters and external configuration, then a budget-capped pilot and independent evidence review before the full 30-pair run.

Fresh-data enforcement: the default CLI scope is `trial`, matched by explicit trial identity on native records and tasks. It excludes all older trials, including prior URACE.md trials. New task artifacts are isolated under `runs/TRIAL_ID/`; inspection reports under `reports/trials/TRIAL_ID/`. The active state starts with no completed tasks and the exact committed version0. Historical state remains archived and is read only for an explicit `--scope lifetime` request. Default current-trial quality/efficiency results never pool historical acceptance or coverage.

Candidate-quality correction: proposals must identify a concrete interpretation/decision failure; punctuation/case/article-only edits are rejected before paid review. Independent review requires supported failure case and material quality gain in clarity, substantive consistency or conciseness, with no dimension regression. Acceptance gates for requirements, authority and new runtime behavior remain intact. These changes address observed cosmetic churn; improved acceptance/efficiency is a hypothesis to measure on fresh data.

The normative preservation guard now protects complete requirement sentences, including wrapped lines and dotted artifact names. Non-normative explanation sharing a Markdown line can be reviewed instead of being rejected automatically. Static replay of a real rejected proposal confirms this false positive is removed; the proposal is not thereby accepted. Requirements, headings and code-example preservation and independent no-new-behavior/failure-case/material-gain gates remain tested.

Analysis metadata has three explicit levels: each version snapshot, product overall and entire-runtime overall across registered products. Current-trial aggregation is the default at every level. Snapshot `metadata.json` separates product-result and runtime-operation fields through its scope index; `metadata-schema.json` declares the implemented feature inventory; `completion.json` records the final task outcome and links back to the metadata hash. Baselines have no producing executor task. Native tokens, wall time, rejected costs, unknown usage, provider receipts, context, validation, source lineage, engine/configuration builds, scoring definitions and provenance are retained. Remote model CPU/GPU, actual subscription billing and independently established customer benefit remain explicitly unavailable. No field is guessed.

```sh
./urace/.urace/bin/urace trial status analysis --kind snapshot --version 0 --json
./urace/.urace/bin/urace trial status analysis --kind product --json
./urace/.urace/bin/urace trial status analysis --kind runtime --json
```

Snapshots are prepared in separate pending directories and activated after complete metadata/evidence creation. Metadata, source, diffs, evidence and frozen engine bundles are hash checked. Incomplete publication never advances the active pointer. Recovery reconciles a fully verified published snapshot after a journal interruption without replaying executor work. Immutable engine bundles allow later analysis after local engine changes. Overall reports index raw receipts and task artifacts rather than repeatedly embedding every large payload. The schema covers the declared local-runtime feature inventory; it does not claim observations for unimplemented or externally unobservable features.

The canonical runtime CLI exposes this workflow under `urace trial`; its exact grammar is shared with API discovery and typed dispatch. Operator model/reasoning overrides and goal/replenishment controls come from the canonical runtime configuration. Trial allocation defaults to high; native reasoning defaults separately to medium. Historical absolute evidence references are resolved through the pinned `path-relocations.json`; their hash-bound original bytes are preserved.

Review contexts now cover the complete Product using exact UTF-8 windows of at most 22,000 bytes, including previously oversized sections. No chunk edit bypasses complete-document normative, heading, code-example, authority or independent editorial review gates. Core/freeform resource receipts are reconciled without duplicating trial mirrors. Period comparisons are available through `status analysis --period 3h|day|week|month`; sparse descriptive percentiles remain null. Required operational Python helpers are bundled here; their deployment state remains untracked.
