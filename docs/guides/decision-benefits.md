# Decision benefit feedback

Enabled by default in `auto` mode. Auto mode computes local feedback from existing records and reuses explicitly linked forecasts already produced by normal discovery. It makes zero additional model calls. Regular discovery/execution prompts are unchanged: new feedback/history is not appended to their context. Decision lists show compact status, bottleneck IDs, action, score and an inspection link; full evidence is available on demand.

```
python3 -m urace configuration decision-feedback --json
python3 -m urace decision list --json
python3 -m urace decision inspect DECISION_ID --json
python3 -m urace decision assess DECISION_ID --json
```

Each evaluation records the detected gap/blocker (or UNKNOWN / REPORTED_UNVERIFIED), recommended action, authority status and separate execution status, expected benefits, provisional score, expected cost/risk/uncertainty, source references and subsequent observed metric feedback. APPROVED means the authority classification permits the decision; admission, owner pause, validation and acceptance remain separate. A score cannot approve a denied decision, change priority, unblock a task, weaken acceptance or claim an accepted edit has verified user benefit.

Existing executor `expected_value` estimates are reused only through an explicit matching proposal-evidence reference, never inferred from hardcoded goal defaults. They are uncalibrated 0..100 priors, not probabilities or a universal worth percentile. Missing inputs stay unknown. Costs/risks stay separate; no hidden utility weights are introduced.

An owner can record a forecast and link an existing detected bottleneck:

```
python3 -m urace decision assess DECISION_ID --forecast '{"bottleneck_id":"GAP_ID","recommended_action":"Deduplicate receipt IDs","benefits":[{"metric":"accuracy","unit":"proportion","baseline":0.7,"expected":0.9,"direction":"higher","target_gain":0.2}],"weights":{"accuracy":1},"cost":{"tokens":null},"risk":"Keep conflicting receipts visible","uncertainty":"Uncalibrated engineering estimate","evidence_refs":["GAP_ID"]}' --json
```

The example numbers are illustrative, not trial observations. Forecasts are persisted before optional inference; revisions retain immutable history. Late forecasts are marked retrospective. A changed intent, task or success contract makes an older forecast stale and withholds its score; explicit reconfirmation creates a new context-bound revision. Optional weighted scores use owner-declared target attainment: weighted mean of clamped expected gain / target gain, multiplied by 100 (range -100..100). Every dimension/weight/evidence reference must be present; unknown baselines, expected values or targets withhold the score. An explicit owner `expected_score` can instead be recorded as an uncalibrated estimate. No synthetic estimate is promoted to measured value.

Observed operation metrics, forecast errors and existing independent outcome records are linked separately. Acceptance alone does not validate a forecast, establish causal attribution or calibrate the score. Metric-unit and execution-condition compatibility still require verification.

## Optional executor assessment

```
python3 -m urace configuration decision-feedback --mode executor --executor claude --json
python3 -m urace decision assess DECISION_ID --json
python3 -m urace configuration decision-feedback --mode auto --json
python3 -m urace configuration decision-feedback --enabled false --json
```

Changing the configuration itself does not invoke an executor. Even in executor mode, background refresh and list/inspect remain local. Only an explicit assess command can request advisory inference. The selected complete decision packet is limited to 16KiB; larger packets defer rather than truncate evidence. The artifact-only worker has no workspace tools, uses the existing requested model/native effort, a 120-second wall bound, both ordinary and shared admission, unchanged quota/backoff/owner controls, and scoped receipts. Assessment overhead is charged to the declared parent product with a distinct decision_evaluation stage and no product-outcome credit. Provider-internal retries/auxiliary model calls may add tokens; exact credits remain unknown unless directly observed.

Identical successful/failed assessments are cached (default 18,900 seconds). Material decision/evidence/forecast/profile/executor changes invalidate the cache. A zero-inference admission deferral can be checked again under current guards. A cached score is flagged stale when inputs or freshness change. Output must contain valid advisory fields and an attributable receipt to be marked ADVISORY_COMPLETE. Failed output never becomes a successful score. Cancellation terminates the worker and allows its transport to close/settle.

CLI/API use the same parser and policy classification. Configuration changes and assess are mutating operations; inspection is read-only. No extra credentials, plugin installation, authority grant, commit or deployment is required for auto mode. Executor mode remains unavailable where the installation has no registered shared resource guard; it must defer rather than fall back to unguarded inference.
