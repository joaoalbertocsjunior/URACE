# Benchmark KPI Roadmap

Each phase adds one measurable dimension to the benchmark suite. Phases are ordered by
dependency and value: earlier phases produce data later phases rely on. No phase is started
before the previous one has passing tests and documented results.

**Current state:** Phase 0 complete — cost efficiency in mock mode, 8/8 framework tests passing.

---

## Phase 0 — Cost efficiency baseline (complete)

**KPI:** cost per accepted improvement (URACE vs direct executor)  
**Result:** URACE 51% cheaper (baseline), 45% at conservative cache assumptions  
**Files:** `trial/benchmark_{product,corpus,control,runner,longitudinal}.py`, `trial/tests/test_benchmark_framework.py`  
**Gaps remaining:** mock mode only; cache fraction assumptions not empirically measured

---

## Phase 1 — Live API calibration

**Goal:** Validate Phase 0 assumptions against real API calls. Closes the largest gap in current
results: DIFFICULTY_TOKENS and cache fraction estimates are unverified.

**KPIs:**
- `token_estimate_error` — ratio of actual / estimated tokens per difficulty tier (target: within 2×)
- `cache_fraction_measured` — actual cached-token fraction from Claude prompt-cache headers
- `live_acceptance_rate` — control arm acceptance rate on real API (validates mock 100% assumption)

**New files:**
```
trial/benchmark_calibration.py        # runs 3 tasks (one per tier) live, records actual tokens
trial/tests/test_benchmark_calibration.py
```

**What `benchmark_calibration.py` does:**
1. Runs easy-001, medium-001, hard-001 via live API (requires `--api-key`)
2. Records `actual_input_tokens`, `actual_output_tokens`, `cache_read_tokens` from API response
3. Computes `token_ratio = actual / estimated` per tier
4. Writes `calibration_report.json` — schema `urace-benchmark-calibration-v1`

**Acceptance criteria:**
- `token_ratio` between 0.5× and 2.0× for each tier
- If ratio outside bounds: update DIFFICULTY_TOKENS and re-run Phase 0 comparison
- `cache_fraction_measured` available from API — update `benchmark_runner.py` model assumptions
- All existing 8 framework tests still pass

**Dependency:** API key. All prior mock tests must pass first.

**Complexity:** Small — `run_control_arm` live mode already exists; add token logging and report writer.

---

## Phase 2 — Regression guard benchmark

**Goal:** Measure whether accepted improvements break pre-existing tests. The most dangerous
failure mode: an improvement that passes its acceptance test but silently breaks other behavior.

**KPI:**
- `regression_rate` — accepted improvements that introduce ≥1 new test failure / total accepted
- `regression_detected_rate` — regressions caught by full-suite run vs acceptance-only run

**Design:**
- After applying each MOCK_FIX, run the full `benchmark_product_tests.py` suite (all 31 tests)
- Count pre-existing failures introduced by this fix (failures not in the fix's own acceptance test)
- Extend `benchmark_product.py` with 2 intentionally regressing bad fixes to verify detection works

**New files:**
```
trial/benchmark_regression.py          # applies each fix, runs full suite, counts regressions
trial/benchmark_bad_fixes.py           # 2 fixes that solve the target but break another test
trial/tests/test_benchmark_regression.py
```

**`benchmark_bad_fixes.py` contents:**
- `bad-bug-001`: "fixes" export_summary by clearing the list (`return []`) — acceptance test passes (len == 0 ≠ expected), no, needs careful design
- Actually: a fix for easy-001 that uses `range(len(txns))` but also corrupts `_transactions` in-place → acceptance passes, but `test_get_transactions_all` fails

**Acceptance criteria:**
- `regression_rate == 0` for all 10 MOCK_FIX tasks (they are non-regressing by design)
- Bad fix variants trigger `regression_detected_rate == 1.0` (all bad fixes caught)
- Report written to `regression_report.json` — schema `urace-benchmark-regression-v1`

**Dependency:** Phase 0 complete.

**Complexity:** Medium — needs full-suite runner + bad-fix design that's pedagogically clear.

---

## Phase 3 — Qualification signal benchmark

**Goal:** Measure precision and recall of URACE's acceptance gate — does it correctly reject
bad improvements and accept good ones?

**KPIs:**
- `acceptance_precision` — true_positives / (true_positives + false_positives)
  — good fixes accepted, bad fixes rejected
- `acceptance_recall` — true_positives / (true_positives + false_negatives)
  — no good fix is left unaccepted over N retries

**Design:**
Extend the corpus with a "shadow corpus" of 10 intentionally wrong implementations (one per task):
- Wrong logic (solves different problem)
- Partial implementation (passes acceptance test via special-casing rather than general fix)
- Syntactically valid but semantically broken

URACE's qualification gate should reject these; direct executor might accept them.

**New files:**
```
trial/benchmark_qualification_corpus.py    # 10 bad fix variants with known rejection criteria
trial/benchmark_qualification.py           # runs both arms on shadow corpus, measures gate accuracy
trial/tests/test_benchmark_qualification.py
```

**Acceptance criteria:**
- Precision ≥ 0.90: at most 1 bad fix sneaks through per 10
- Recall = 1.00: all 10 good fixes accepted
- Report: `qualification_report.json` — schema `urace-benchmark-qualification-v1`

**Dependency:** Phase 2 complete (regression guard validates that good fixes don't regress).

**Complexity:** Medium-high — designing plausible but wrong implementations that test the gate boundary is subtle.

---

## Phase 4 — Goal fidelity benchmark

**Goal:** Measure whether improvements stay within declared product intent over many cycles.
URACE has an intent layer; this benchmarks whether it actually prevents scope creep.

**KPI:**
- `intent_preservation_rate` — cycles that only touch declared-gap methods / total cycles
- `scope_creep_rate` — improvements that modify methods not in the declared gap corpus

**Design:**
- Define a product intent manifest: "this product must only be improved in these 10 methods"
- After each fix, diff the patched file against original; flag any method changed outside the declared list
- Also test: does URACE refuse a task that asks it to modify an undeclared method?

**New files:**
```
trial/benchmark_intent_manifest.json         # declares allowed change surface
trial/benchmark_intent.py                    # applies fixes, checks diff against manifest
trial/benchmark_intent_corpus.py             # adds 2 out-of-scope tasks (should be rejected)
trial/tests/test_benchmark_intent.py
```

**Acceptance criteria:**
- `intent_preservation_rate == 1.0` for all 10 declared-gap tasks (no side effects)
- Out-of-scope tasks trigger REJECTED outcome, not ACCEPTED
- Report: `intent_report.json` — schema `urace-benchmark-intent-v1`

**Dependency:** Phase 0 complete. Phase 1 calibration data recommended but not required.

**Complexity:** Medium — manifest format is new; diff analysis is straightforward.

---

## Phase 5 — Improvement velocity benchmark

**Goal:** Measure how the rate of accepted improvements changes as URACE accumulates context.
Answers: does URACE actually get faster/cheaper per improvement as state grows?

**KPIs:**
- `velocity_ratio` — improvements per cycle in cycles 41-50 / improvements per cycle in cycles 1-10
- `time_to_first_acceptance` per difficulty tier (live mode only)
- `cost_per_improvement_slope` — does it fall monotonically? (currently assumed, not measured)

**Design:**
Extend the longitudinal runner to track velocity explicitly. In mock mode this is deterministic;
in live mode it measures real improvement velocity over a 50-cycle session.

**New files:**
```
trial/benchmark_velocity.py               # extracts velocity metrics from longitudinal cycles data
trial/tests/test_benchmark_velocity.py
```

Update `benchmark_longitudinal.py` to record `improvements_this_window` per 10-cycle window.

**Acceptance criteria (mock):**
- `velocity_ratio > 1.0`: later cycles produce more improvements per unit cost than early cycles
- `cost_per_improvement_slope < 0`: monotonically decreasing (enforced by longitudinal model)

**Acceptance criteria (live, Phase 1 required):**
- Same directional requirements; magnitude validated against real data

**Dependency:** Phase 0. Phase 1 calibration closes the mock→live gap.

**Complexity:** Small — extends existing longitudinal data, no new product or corpus needed.

---

## Phase 6 — Peer exchange ROI benchmark

**Goal:** Measure whether borrowing peer features reduces cost vs building from scratch.

**KPI:**
- `peer_reuse_savings_pct` — (cost_build_own - cost_with_peer) / cost_build_own
- `peer_quality_match_rate` — peer features that pass local acceptance test without modification

**Design:**
Simulate a P2P market: for 3 of the 10 tasks, pre-build solutions as "peer features" with
signed manifests. Run two arms:
- Arm A: build from scratch (current control arm)
- Arm B: borrow peer feature, run acceptance test, pay peer_fee (10% of build cost)

Measure cost and quality difference.

**New files:**
```
trial/benchmark_peer_library.py          # pre-built peer features for medium-001, medium-002, hard-002
trial/benchmark_peer_exchange.py         # two-arm peer vs build comparison
trial/tests/test_benchmark_peer_exchange.py
```

**Acceptance criteria:**
- `peer_reuse_savings_pct > 0`: borrowing a correct peer solution is cheaper than building
- `peer_quality_match_rate == 1.0`: pre-verified peer solutions pass local acceptance

**Dependency:** Phase 0, Phase 2 (regression guard on borrowed features). Peer exchange
subsystem must be production-stable (`runtime/urace/peer_exchange.py`).

**Complexity:** High — needs P2P simulation or real network; peer fee economics need grounding.

---

## Phase 7 — State resilience benchmark

**Goal:** Measure URACE recovery correctness and cycle overhead after mid-cycle faults.

**KPIs:**
- `recovery_cycles` — cycles needed to return to pre-fault improvement count after fault injection
- `state_monotonicity_violations` — state version decrements observed (must be 0)
- `fault_containment_rate` — faults that corrupt only the current cycle, not prior accepted state

**Design:**
Extends the longitudinal runner with fault injection at cycles 10, 25, and 40:
- File write failure (simulated via monkeypatching)
- Mid-cycle executor timeout
- Corrupt state file (truncate JSON mid-write)

URACE should recover within ≤2 cycles from each fault.

**New files:**
```
trial/benchmark_resilience.py            # fault injection harness over 50-cycle run
trial/benchmark_fault_corpus.py          # fault timing and type definitions
trial/tests/test_benchmark_resilience.py
```

**Note:** `runtime/tests/test_product_improvement_monotonic.py` already covers state monotonicity;
this phase measures *recovery speed*, which the existing tests do not.

**Acceptance criteria:**
- `state_monotonicity_violations == 0`
- `recovery_cycles <= 2` for each injected fault
- `fault_containment_rate == 1.0`

**Dependency:** Phase 0. No live API required (fault injection is deterministic).

**Complexity:** Medium — fault injection harness needs careful isolation to avoid corrupting the product file.

---

## Phase 8 — Ledger integrity benchmark

**Goal:** Verify that the audit chain detects tampering under realistic attack scenarios.

**KPIs:**
- `tamper_detection_rate` — injected tamper events correctly flagged / total injections (target: 1.0)
- `false_positive_rate` — legitimate operations flagged as tampered (target: 0.0)
- `detection_latency_cycles` — cycles until tamper is surfaced (target: ≤1)

**Design:**
Run 20 tamper scenarios against a live ledger:
- Hash corruption (flip 1 bit in a prior entry)
- Entry deletion
- Entry reordering
- Duplicate entry injection
- Backdated timestamp

Each scenario should trigger a detectable violation.

**New files:**
```
trial/benchmark_ledger.py               # tamper injection + detection measurement
trial/benchmark_tamper_corpus.py        # 20 tamper scenario definitions
trial/tests/test_benchmark_ledger.py
```

**Dependency:** Phase 0. Requires `runtime/urace/signed_ledger.py` and `authenticated_journal.py`
to be production-stable.

**Complexity:** Medium — tamper injection needs access to internal ledger format.

---

## Phase 9 — Integrated KPI dashboard

**Goal:** Single-command run of all benchmark phases; unified report.

**New files:**
```
trial/run_all_benchmarks.py              # orchestrates all phases, writes kpi_dashboard.json
docs/benchmark-kpi-dashboard.md         # live-updated results table
```

**`kpi_dashboard.json`** — schema `urace-benchmark-kpi-dashboard-v1`:
```json
{
  "schema": "urace-benchmark-kpi-dashboard-v1",
  "generated_at": ...,
  "phases_run": ["phase0", "phase1", ...],
  "kpis": {
    "cost_efficiency":       { "urace_vs_control_pct_cheaper": 51.3 },
    "regression_guard":      { "regression_rate": 0.0 },
    "qualification_signal":  { "precision": 1.0, "recall": 1.0 },
    "goal_fidelity":         { "intent_preservation_rate": 1.0 },
    "improvement_velocity":  { "velocity_ratio": 1.6 },
    "peer_exchange_roi":     { "peer_reuse_savings_pct": 42.0 },
    "state_resilience":      { "recovery_cycles": 1.2, "violations": 0 },
    "ledger_integrity":      { "tamper_detection_rate": 1.0, "false_positive_rate": 0.0 }
  }
}
```

**Dependency:** All prior phases complete.

---

## Execution order and gate criteria

| Phase | Deliverable | Gate to proceed |
|---|---|---|
| 0 ✓ | Cost efficiency (mock) | 8 framework tests pass |
| 1 | Live API calibration | DIFFICULTY_TOKENS within 2×; cache fractions measured |
| 2 | Regression guard | regression_rate == 0; bad-fix detection == 1.0 |
| 3 | Qualification signal | precision ≥ 0.90; recall == 1.0 |
| 4 | Goal fidelity | intent_preservation == 1.0 |
| 5 | Improvement velocity | velocity_ratio > 1.0 |
| 6 | Peer exchange ROI | peer subsystem stable; savings > 0 |
| 7 | State resilience | recovery_cycles ≤ 2; violations == 0 |
| 8 | Ledger integrity | tamper_detection == 1.0 |
| 9 | Integrated dashboard | all prior phases pass |

Phases 1–5 have no blocking external dependencies and can be started immediately.
Phases 6–8 depend on runtime subsystem stability (peer exchange, ledger) and should not
be started until those subsystems have independent production test coverage.

---

## Related

- [Benchmark Proof](benchmark-proof.md) — Phase 0 results and methodology
- [Comparative Analysis](../concepts/comparative-analysis.md) — gap analysis vs adjacent systems
- [Runtime Improvement](../guides/runtime-improvement.md) — how URACE manages improvement cycles
