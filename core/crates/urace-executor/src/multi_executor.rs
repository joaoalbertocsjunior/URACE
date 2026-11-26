//! Multi-executor parallel plan selection — Agora pattern for discovery/planning.
//!
//! Multiple executors propose plans; each is scored on four quality dimensions;
//! the highest-scoring proposal is selected.  When disabled (default) or fewer
//! than two providers are available, callers fall through to the single-executor
//! path unchanged.
//!
//! # §62z note
//! `generate_and_select` is a *selection* helper only — it does not authorise
//! spend or goal creation.  Any downstream action that triggers spend must pass
//! through `authority_check` in the calling path before execution.

use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::HashMap;
use thiserror::Error;

use crate::routing::{routed_provider_definitions, ProviderDef};

/// Schema tag written into every `ScoredCandidate` record.
pub const SCHEMA: &str = "urace-multi-plan-v1";

/// Maximum number of parallel candidates the selector will consider.
const HARD_MAX_CANDIDATES: usize = 5;

// ── Errors ────────────────────────────────────────────────────────────────────

#[derive(Debug, Error)]
pub enum MultiExecutorError {
    #[error("no candidates available to select from")]
    NoCandidates,
    #[error("multi-plan selection is disabled")]
    Disabled,
    #[error("insufficient providers: need at least 2, got {0}")]
    InsufficientProviders(usize),
    #[error("proposal generation failed for all providers")]
    AllProposalsFailed,
}

// ── Configuration ─────────────────────────────────────────────────────────────

/// Score weighting constants across the four quality dimensions.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ScoreWeights {
    pub constraint_compliance: f64,
    pub goal_alignment: f64,
    pub cost_estimate: f64,
    pub novelty: f64,
}

impl Default for ScoreWeights {
    fn default() -> Self {
        ScoreWeights {
            constraint_compliance: 0.4,
            goal_alignment: 0.3,
            cost_estimate: 0.2,
            novelty: 0.1,
        }
    }
}

/// Validated multi-plan selection settings.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MultiPlanSettings {
    pub enabled: bool,
    pub max_candidates: usize,
    pub score_weights: ScoreWeights,
}

impl Default for MultiPlanSettings {
    fn default() -> Self {
        MultiPlanSettings {
            enabled: false,
            max_candidates: 3,
            score_weights: ScoreWeights::default(),
        }
    }
}

/// Parse and validate multi-plan settings from the top-level config object.
///
/// Never panics: invalid or missing values fall back to defaults.
pub fn settings(config: &HashMap<String, Value>) -> MultiPlanSettings {
    let raw = config
        .get("executor")
        .and_then(Value::as_object)
        .and_then(|e| e.get("multi_plan_selection"))
        .and_then(Value::as_object);

    let enabled = raw
        .and_then(|r| r.get("enabled"))
        .and_then(Value::as_bool)
        .unwrap_or(false);

    let max_candidates = raw
        .and_then(|r| r.get("max_candidates"))
        .and_then(Value::as_u64)
        .map(|v| (v as usize).clamp(1, HARD_MAX_CANDIDATES))
        .unwrap_or(3);

    MultiPlanSettings {
        enabled,
        max_candidates,
        score_weights: ScoreWeights::default(),
    }
}

// ── Scoring ───────────────────────────────────────────────────────────────────

/// Per-dimension scores for a single proposal (all in [0.0, 1.0]).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DimensionScores {
    pub constraint_compliance: f64,
    pub goal_alignment: f64,
    pub cost_estimate: f64,
    pub novelty: f64,
    /// Weighted sum of the four dimensions.
    pub total: f64,
}

/// A single executor's proposal together with its quality scores.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ScoredCandidate {
    pub schema: String,
    pub provider_id: String,
    pub proposal: Value,
    pub score: DimensionScores,
}

/// Score a discovery proposal on four quality dimensions.
///
/// `state` is the runtime state object forwarded by the caller; keys used:
/// `constraints`, `current_objective`, `operations`.
pub fn score_proposal(proposal: &Value, state: &HashMap<String, Value>) -> DimensionScores {
    let weights = ScoreWeights::default();

    let proposal_text = {
        let msg = proposal
            .get("message")
            .and_then(Value::as_str)
            .unwrap_or("");
        let plan = proposal.get("plan").and_then(Value::as_str).unwrap_or("");
        format!("{msg}{plan}").to_lowercase()
    };

    // 1. Constraint compliance: penalise 0.25 per violated constraint string.
    let constraints: Vec<String> = state
        .get("constraints")
        .and_then(Value::as_array)
        .map(|arr| {
            arr.iter()
                .filter_map(|c| c.get("text").and_then(Value::as_str))
                .map(|s| s.to_lowercase())
                .collect()
        })
        .unwrap_or_default();

    let violations = constraints
        .iter()
        .filter(|c| !c.is_empty() && proposal_text.contains(c.as_str()))
        .count();
    let constraint_compliance = (1.0_f64 - 0.25 * violations as f64).max(0.0);

    // 2. Goal alignment: exact match > objective_id match > has_actionable_plan > neutral.
    let current_objective = state
        .get("current_objective")
        .and_then(Value::as_str)
        .unwrap_or("");
    let goal_alignment = if (!current_objective.is_empty()
        && proposal_text.contains(&current_objective.to_lowercase()))
        || proposal
            .get("objective_id")
            .and_then(Value::as_str)
            .unwrap_or("")
            == current_objective
    {
        1.0
    } else if proposal
        .get("has_actionable_plan")
        .and_then(Value::as_bool)
        .unwrap_or(false)
    {
        0.75
    } else {
        0.5
    };

    // 3. Cost estimate: shorter plan text → lower cost proxy.
    let plan_len = proposal
        .get("plan")
        .and_then(Value::as_str)
        .map(str::len)
        .unwrap_or(0);
    let cost_estimate = (1.0_f64 - plan_len as f64 / 10_000.0).max(0.0);

    // 4. Novelty: penalise 0.3 per recent operation whose summary matches.
    let recent_ops: Vec<String> = state
        .get("operations")
        .and_then(Value::as_array)
        .map(|arr| {
            let skip = arr.len().saturating_sub(10);
            arr.iter()
                .skip(skip)
                .filter_map(|op| {
                    op.get("executor_source_summary")
                        .and_then(Value::as_str)
                        .map(str::to_string)
                })
                .collect()
        })
        .unwrap_or_default();

    let proposal_summary: String = proposal
        .get("message")
        .and_then(Value::as_str)
        .unwrap_or("")
        .chars()
        .take(50)
        .collect();
    let matches = recent_ops
        .iter()
        .filter(|op| {
            !op.is_empty() && !proposal_summary.is_empty() && op.contains(&proposal_summary)
        })
        .count();
    let novelty = (1.0_f64 - 0.3 * matches as f64).max(0.0);

    let total = weights.constraint_compliance * constraint_compliance
        + weights.goal_alignment * goal_alignment
        + weights.cost_estimate * cost_estimate
        + weights.novelty * novelty;

    DimensionScores {
        constraint_compliance,
        goal_alignment,
        cost_estimate,
        novelty,
        total,
    }
}

// ── Selection ─────────────────────────────────────────────────────────────────

/// Select the highest-scoring candidate from `candidates`.
pub fn select_best(candidates: &[ScoredCandidate]) -> Result<&ScoredCandidate, MultiExecutorError> {
    candidates
        .iter()
        .max_by(|a, b| {
            a.score
                .total
                .partial_cmp(&b.score.total)
                .unwrap_or(std::cmp::Ordering::Equal)
        })
        .ok_or(MultiExecutorError::NoCandidates)
}

// ── Parallel generation + selection ──────────────────────────────────────────

/// A callable that generates a discovery proposal for a given provider override.
///
/// The closure receives the provider id being pinned.  Return `None` to signal
/// that this provider is unavailable for this round (it is silently skipped).
pub type DiscoverFn<'a> = &'a dyn Fn(&str, &HashMap<String, Value>) -> Option<Value>;

/// Filter providers that are currently on a retry hold-off.
fn available_providers<'a>(
    providers: &'a [ProviderDef],
    state: &HashMap<String, Value>,
) -> Vec<&'a ProviderDef> {
    providers
        .iter()
        .filter(|p| {
            !state
                .get("executor_state")
                .and_then(|es| es.get("provider_pool"))
                .and_then(|pp| pp.get(&p.id))
                .and_then(|entry| entry.get("retry_at"))
                .is_some()
        })
        .collect()
}

/// Generate proposals from multiple providers and select the best.
///
/// Returns the winning proposal `Value`, or an error when:
/// - multi-plan selection is disabled (`MultiExecutorError::Disabled`),
/// - fewer than 2 providers are available,
/// - all proposal calls fail.
///
/// The caller is responsible for the §62z authority gate on any downstream
/// spend or goal creation triggered by the returned proposal.
pub fn generate_and_select(
    config: &HashMap<String, Value>,
    state: &HashMap<String, Value>,
    discover_fn: DiscoverFn<'_>,
) -> Result<Value, MultiExecutorError> {
    let cfg = settings(config);
    if !cfg.enabled {
        return Err(MultiExecutorError::Disabled);
    }

    let executor_config = config
        .get("executor")
        .cloned()
        .unwrap_or(Value::Object(Default::default()));
    let all_providers = routed_provider_definitions(&executor_config);
    let available = available_providers(&all_providers, state);

    if available.len() < 2 {
        return Err(MultiExecutorError::InsufficientProviders(available.len()));
    }

    let max_cand = cfg.max_candidates.min(available.len());
    let mut candidates: Vec<ScoredCandidate> = Vec::with_capacity(max_cand);

    for provider in available.iter().take(max_cand) {
        if let Some(proposal) = discover_fn(&provider.id, config) {
            let score = score_proposal(&proposal, state);
            candidates.push(ScoredCandidate {
                schema: SCHEMA.to_string(),
                provider_id: provider.id.clone(),
                proposal,
                score,
            });
        }
    }

    if candidates.is_empty() {
        return Err(MultiExecutorError::AllProposalsFailed);
    }

    let winner = select_best(&candidates)?;
    Ok(winner.proposal.clone())
}

// ── M78 — Multi-model consensus ───────────────────────────────────────────────

/// M78 — Multi-model consensus: verify that the top-scoring candidates agree
/// closely enough to be considered a consensus result.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum ConsensusVerdict {
    /// All top candidates agree within the threshold.
    Consensus { mean_score: f64, spread: f64 },
    /// Top candidates diverge — human review may be needed.
    Divergent {
        max_score: f64,
        min_score: f64,
        spread: f64,
    },
}

/// Check whether the top `quorum_size` candidates from `scored` agree within `max_spread`.
///
/// `quorum_size` = how many top candidates to consider (minimum 2).
/// `max_spread`  = maximum allowed difference between max and min score in the quorum.
pub fn check_model_consensus(
    scored: &[ScoredCandidate],
    quorum_size: usize,
    max_spread: f64,
) -> ConsensusVerdict {
    if scored.is_empty() {
        return ConsensusVerdict::Divergent {
            max_score: 0.0,
            min_score: 0.0,
            spread: 0.0,
        };
    }

    // Sort descending by total score to pick the top-N.
    let mut sorted: Vec<f64> = scored.iter().map(|c| c.score.total).collect();
    sorted.sort_by(|a, b| b.partial_cmp(a).unwrap_or(std::cmp::Ordering::Equal));

    // Use all available candidates if quorum_size exceeds the slice length.
    let effective_quorum = quorum_size.max(2).min(sorted.len());
    let quorum_scores = &sorted[..effective_quorum];

    let max_score = quorum_scores[0];
    let min_score = quorum_scores[effective_quorum - 1];
    let spread = max_score - min_score;
    let mean_score = quorum_scores.iter().sum::<f64>() / effective_quorum as f64;

    if spread <= max_spread {
        ConsensusVerdict::Consensus { mean_score, spread }
    } else {
        ConsensusVerdict::Divergent {
            max_score,
            min_score,
            spread,
        }
    }
}

// ── Budget allocation helpers ─────────────────────────────────────────────────

/// Per-provider budget slot.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BudgetSlot {
    pub provider_id: String,
    /// Fraction of total budget allocated to this provider (sum ≤ 1.0).
    pub fraction: f64,
    /// Absolute token budget derived from the fraction.
    pub token_budget: u64,
}

/// Allocate `total_tokens` evenly across `provider_ids`.
///
/// Leftover tokens from integer rounding are assigned to the first slot.
pub fn allocate_budget(provider_ids: &[String], total_tokens: u64) -> Vec<BudgetSlot> {
    if provider_ids.is_empty() {
        return Vec::new();
    }
    let n = provider_ids.len() as u64;
    let per = total_tokens / n;
    let remainder = total_tokens % n;

    provider_ids
        .iter()
        .enumerate()
        .map(|(i, id)| {
            let token_budget = if i == 0 { per + remainder } else { per };
            BudgetSlot {
                provider_id: id.clone(),
                fraction: token_budget as f64 / total_tokens.max(1) as f64,
                token_budget,
            }
        })
        .collect()
}

// ── Tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn make_state(objective: &str) -> HashMap<String, Value> {
        let mut m = HashMap::new();
        m.insert("current_objective".into(), json!(objective));
        m
    }

    #[test]
    fn settings_defaults_when_absent() {
        let cfg: HashMap<String, Value> = HashMap::new();
        let s = settings(&cfg);
        assert!(!s.enabled);
        assert_eq!(s.max_candidates, 3);
    }

    #[test]
    fn settings_max_candidates_clamped() {
        let cfg: HashMap<String, Value> = [(
            "executor".into(),
            json!({"multi_plan_selection": {"enabled": true, "max_candidates": 99}}),
        )]
        .into_iter()
        .collect();
        let s = settings(&cfg);
        assert_eq!(s.max_candidates, HARD_MAX_CANDIDATES);
    }

    #[test]
    fn score_proposal_goal_match_boosts_alignment() {
        let proposal = json!({"message": "address the main-goal now", "plan": "step 1"});
        let state = make_state("main-goal");
        let scores = score_proposal(&proposal, &state);
        assert_eq!(scores.goal_alignment, 1.0);
        assert!(scores.total > 0.5);
    }

    #[test]
    fn score_proposal_constraint_violation_penalised() {
        let proposal = json!({"message": "we must not spend tokens", "plan": ""});
        let mut state = make_state("");
        state.insert(
            "constraints".into(),
            json!([{"text": "must not spend tokens"}]),
        );
        let scores = score_proposal(&proposal, &state);
        // 1 violation → 0.75
        assert!((scores.constraint_compliance - 0.75).abs() < 1e-9);
    }

    #[test]
    fn select_best_picks_highest_total() {
        let make = |id: &str, total: f64| ScoredCandidate {
            schema: SCHEMA.to_string(),
            provider_id: id.to_string(),
            proposal: json!({}),
            score: DimensionScores {
                constraint_compliance: 1.0,
                goal_alignment: 1.0,
                cost_estimate: 1.0,
                novelty: 1.0,
                total,
            },
        };
        let candidates = vec![make("a", 0.6), make("b", 0.9), make("c", 0.4)];
        let winner = select_best(&candidates).unwrap();
        assert_eq!(winner.provider_id, "b");
    }

    #[test]
    fn allocate_budget_even_split() {
        let ids: Vec<String> = vec!["p1".into(), "p2".into(), "p3".into()];
        let slots = allocate_budget(&ids, 300);
        assert_eq!(slots.len(), 3);
        let total: u64 = slots.iter().map(|s| s.token_budget).sum();
        assert_eq!(total, 300);
        // Remainder goes to first slot only when not evenly divisible.
        let ids2: Vec<String> = vec!["a".into(), "b".into()];
        let slots2 = allocate_budget(&ids2, 101);
        assert_eq!(slots2[0].token_budget, 51); // 50 + 1 remainder
        assert_eq!(slots2[1].token_budget, 50);
    }

    #[test]
    fn generate_and_select_disabled_returns_err() {
        let config: HashMap<String, Value> = HashMap::new();
        let state: HashMap<String, Value> = HashMap::new();
        let result = generate_and_select(&config, &state, &|_, _| None);
        assert!(matches!(result, Err(MultiExecutorError::Disabled)));
    }

    // ── M78 tests ─────────────────────────────────────────────────────────────

    fn make_candidate(provider_id: &str, total: f64) -> ScoredCandidate {
        ScoredCandidate {
            schema: SCHEMA.to_string(),
            provider_id: provider_id.to_string(),
            proposal: json!({}),
            score: DimensionScores {
                constraint_compliance: total,
                goal_alignment: total,
                cost_estimate: total,
                novelty: total,
                total,
            },
        }
    }

    #[test]
    fn consensus_when_scores_close() {
        let candidates = vec![
            make_candidate("a", 0.90),
            make_candidate("b", 0.88),
            make_candidate("c", 0.87),
        ];
        let verdict = check_model_consensus(&candidates, 3, 0.05);
        assert!(
            matches!(verdict, ConsensusVerdict::Consensus { .. }),
            "expected Consensus, got {:?}",
            verdict
        );
    }

    #[test]
    fn divergent_when_scores_spread() {
        let candidates = vec![make_candidate("a", 0.95), make_candidate("b", 0.40)];
        let verdict = check_model_consensus(&candidates, 2, 0.10);
        assert!(
            matches!(verdict, ConsensusVerdict::Divergent { .. }),
            "expected Divergent, got {:?}",
            verdict
        );
    }

    #[test]
    fn single_candidate_still_produces_verdict() {
        // quorum_size 2 is requested but only 1 candidate available — uses all available.
        let candidates = vec![make_candidate("a", 0.75)];
        let verdict = check_model_consensus(&candidates, 2, 0.10);
        // Spread of a single value is 0.0, which is ≤ max_spread → Consensus.
        assert!(
            matches!(verdict, ConsensusVerdict::Consensus { spread, .. } if spread == 0.0),
            "expected Consensus with spread 0.0, got {:?}",
            verdict
        );
    }

    #[test]
    fn consensus_spread_at_boundary() {
        // spread exactly equals max_spread should count as Consensus.
        let candidates = vec![make_candidate("a", 0.90), make_candidate("b", 0.80)];
        let verdict = check_model_consensus(&candidates, 2, 0.10);
        assert!(
            matches!(verdict, ConsensusVerdict::Consensus { .. }),
            "expected Consensus at boundary spread, got {:?}",
            verdict
        );
    }
}
