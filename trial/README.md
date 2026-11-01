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
