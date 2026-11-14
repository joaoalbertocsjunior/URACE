# Qualified comparative engineering evidence

The primary trial product remains URACE.md from baseline5688fda. Ordinary repository pairs measure runtime orchestration infrastructure, not textual product-version improvement. Frozen specification studies supply the product text separately. Neither proves comprehension, real-user benefit or market fit.

The versioned protocol is in trial/qualification_protocol.py and is frozen in each repository study plan before dispatch. Cohort identity binds trial, task contracts including phase two, evaluator/quality data, execution code, native client versions, requested models/efforts, tool schema, sandbox image and controller Python. A changed identity starts a separate cohort; prior plans, rows and snapshots remain intact.

The existing repository study compares standalone and URACE-managed executor workflows. It is not a P2P-first-versus-direct-executor benchmark. The two P2P comparison arms are: `direct_executor`, solving the frozen task from scratch; and `p2p_borrow` (P2P-first), discovering/selecting an asset, fetching an eligible artifact into quarantine, integrating and validating it, and using executor calls for remaining work as needed. They must share the frozen task and independent acceptance contract, with counterbalanced order. Cohort plans embed the exact task and acceptance text, verify both hashes, and pin provider/model/client/native effort. `trial/p2p_pair_protocol.py` defines an evidence gate using task and acceptance hashes, matched provider/model/effort, transport receipts reconciled to authoritative files, signed acceptance outcomes (pass or fail), and the artifact digest. It validates open-asset transfer evidence, including buyer quarantine acknowledgement and seller attestation. Every attempted pair and measured acceptance failure remains visible; readiness requires at least 30 valid measured pairs and six in each frozen task family. Provider-token usage, P2P URACE units and other costs remain separate; total savings are not claimed until every material cost is measured and a defensible common valuation exists.

The pair verifier and `trial/p2p_study_plan.py` are an evidence gate and frozen-plan generator, not a live study runner. The runtime supports authenticated remote catalog discovery and explicit open-use asset fetch into quarantine. `p2p_cost_qualification.py` now implements the qualification runner (`run_qualification_round`, `bootstrap_complete`, `qualification_statistics`) with Wilson-lower-bound statistics and the 30-pair bootstrap requirement; executing a full 30-pair round requires real network peers but the runner code is complete. Cross-peer purchase settlement is implemented via `purchase_settlement.py`; production activation requires live mutually-pinned peers. Local audit-chain validity is not global ledger consensus. Do not label the protocol a qualified benchmark until a runner produces complete evidence for both arms and the cohort passes the frozen gates.

Each provider/native-effort profile needs at least 30 compatible ordinary matched pairs with six in each of navigation, recovery, interruption, receipts and requirements_change. Failover is separately labeled simulation. Sampling prioritizes incomplete pairs, then the least represented profiles/families. Eligibility is independent per executor. Completed failures are counted rather than replaced because of their outcomes. Pair and arm launch records expose attrition and queue time.

Standalone and managed arms share task, tools, public tests, provider/model/native effort and a 480-second active wall allowance spanning requirement phases. Order is counterbalanced. Managed goal/context packets, up to three outer repair attempts and atomic publication differ from standalone's one outer attempt and are explicitly treatment. Ordinary repairs keep the requested provider. End-to-end times include admission and controller gaps; nested native/tool timing is not added to workflow elapsed time.

Functional acceptance remains outside executor workspaces. Functional cases, robustness data and runner are hashed before inference and verified on resume. Every completed attempt, including failed public development, is measured without sending private diagnostics into repair prompts. Existing functional, robustness, determinism and regression gates are unchanged. Tests share a fixed synthetic task oracle; independent human review and representative real usage are unmeasured.

Receipt reconciliation verifies embedded records against authoritative native transport receipts, deduplicates equal IDs, rejects conflicting IDs and cached-total disagreement, checks provider/product scope and native time against workflow time, and preserves unknown usage/credits. Failed and unmatched completed arms are separately visible. Incomplete launched pairs block a complete assessment; all pending attempts remain in native/product accounting.

Comparisons remain per profile, with six-per-family gates, measured quality/delivery deltas, explicitly defined resource reductions and deterministic paired bootstrap intervals. Inputs are sorted before resampling. Intervals are conditional/descriptive; repeated fixed tasks may be dependent. P50/P90/P95 require 5/20/40 observations. There is no universal worth percentile. Routing retains its 20% gain/5% cross-resource tolerance, quality nonregression and stricter narrow-sample rules.

The single supervisor retains 3-hour reviews and persisted deadlines, 20-minute metadata refresh and 30-second idle admission checks. Every review includes day/week/month windows. A separate Claude diagnostic uses ordinary shared admission, a 120-second wall cap and a persisted 18,900-second cooldown. Its product is urace-qualification-preflight, excluded from productive proof. No quota/backoff/credit policies are changed.

## Smaller evidence and executor packets

Use `python3 -m urace trial status analysis --kind packet --json` for a read-only current evidence index through the existing grouped CLI/API. It includes exact health/progress and hashed paths to full reports, not a replacement for detailed assessment. Drill down for code, failures, quality and resource claims; verify freshness and current source qualification. No missing facts become success.

Executor prompt JSON uses compact separators, preserving every decoded key/value and every source string. This removes redundant formatting only. Actual token savings and job-quality equivalence remain unmeasured. More aggressive context reduction defaults OFF unless exact model/native effort/client/runtime/task conditions, >=35 matched context cases, complete resources and nonregressing quality satisfy the existing gain rule. No additional lossy compression or lowered gates is enabled.


Protocol v3 records cumulative active invocation intervals across resumes and requirement phases. The same 480-second allowance applies to both arms and includes active validation/publication processing. Inactive queue and controller-suspension gaps remain in end-to-end elapsed time and resource reports but do not consume active allowance. Prior-phase consumption cannot be reset. Incomplete hard-crash intervals are charged conservatively and flagged as uncertain, withholding qualification. Legacy incomplete checkpoints cannot acquire a fresh allowance. Completed historical results remain unchanged; v3 requires a separate frozen execution/measurement cohort. Actual publication is retained in history if total active processing overruns, while qualified delivery credit is withheld.

---

## P2P Cost Qualification Readiness

This section describes what a user must do to qualify a P2P cost savings claim. It is distinct from the executor study above, which compares standalone versus URACE-managed workflows. A P2P cost claim compares borrowing a peer asset (P2P-first) against solving the same task from scratch with a direct executor.

**A P2P cost claim is never qualified by synthetic data.** Only a live cohort study counts. Running the pair protocol against mock peers or offline fixtures does not satisfy any requirement here.

### Minimum cohort requirements

- At least **30 live pairs** across **6 task families** (navigation, recovery, interruption, receipts, requirements_change, and one additional family), with at least 5 pairs per family.
- Both arms must be **accepted** in every pair — a failed acceptance in either arm removes that pair from qualification counting.
- Every pair must use a frozen task and acceptance contract with hashes matching the cohort plan. Provider, model, and native effort must be pinned and identical across both arms.
- Complete, comparable USD costs must be recorded for every pair. Zero URACE units paid is required; reputation credits are not a cost offset.
- P2P value must be no lower than direct executor value in every qualifying pair.
- The paired 95% bootstrap upper bound on the cost difference must be below zero.

### Network and settlement requirements

- `network_mode` must be set to `internet` or `hybrid` with at least one live bootstrap peer reachable during the study.
- On-chain settlement must be active: `token_settlement=true`. Pairs run without on-chain settlement do not count toward a qualified claim.
- Transport receipts (buyer quarantine acknowledgement and seller attestation) must be present and reconciled for every P2P-first arm.

### Review and signing

Two independent reviewers must sign the cohort using `trial/p2p_cost_claim_review.py`. Both reviewers must attest to:

- Full evidence review (all pairs, receipts, and cost records)
- Workload provenance review (the frozen task corpus and source digest)
- Reviewer independence (neither reviewer may be the cohort operator)

Their public keys must be pinned in the frozen cohort plan before the study begins. Review signatures after the fact, over a plan that was not pre-registered with those keys, do not qualify.

### What is NOT a savings claim

Until the above conditions are met:

- P2P borrows have **$0 provider cost** to the borrower, but this is not evidence of savings versus executor work.
- Listing prices capped against an owner estimate (see [Price Mechanics](price-mechanics.md)) are a pricing heuristic, not a savings guarantee.
- No reputation credit, token payout, or cohort with fewer than 30 qualifying pairs constitutes a qualified cost savings claim.
- Synthetic pairs, unspecified evidence, and partial cohorts cannot qualify any savings claim for any scope.

A qualified claim is cohort-specific. It does not prove a universal executor price ceiling or generalize to other task types, providers, or network conditions.
