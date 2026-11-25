//! Outcome verification: check receipts, validate score deltas, confirm authority outcomes.
//!
//! Ported from `runtime/urace/outcome_verification.py`. Validates trial outcomes
//! against a frozen outcome contract — baseline, direction, evidence kind, and
//! confidence bounds — without executing any product code.
//!
//! # Key invariants
//! - `SCORE_DELTA_THRESHOLD = 0.0` — verification only passes when net_value_delta > 0.
//! - Any path that affects settlement must be gated by the §62z authority boundary.
//! - Evidence sources must be independent (not executor-writable).
//! - Wilson 95% intervals are used for real-user evidence; engineering/synthetic
//!   evidence produces `OUTCOME_VERIFIED` but not `REAL_USER_VALUE_VERIFIED`.

use serde::{Deserialize, Serialize};
use thiserror::Error;

use crate::trial_common::SCORE_DELTA_THRESHOLD;

// ---------------------------------------------------------------------------
// Error type
// ---------------------------------------------------------------------------

#[derive(Debug, Error)]
pub enum OutcomeVerificationError {
    #[error("invalid contract: {0}")]
    InvalidContract(String),
    #[error("evidence unavailable or invalid: {0}")]
    EvidenceUnavailable(String),
    #[error("schema error: {0}")]
    Schema(#[from] serde_json::Error),
}

// ---------------------------------------------------------------------------
// Status enum
// ---------------------------------------------------------------------------

/// Possible verification statuses for a trial outcome.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum OutcomeStatus {
    /// More evidence windows are still required.
    PendingOutcome,
    /// Engineering or synthetic outcome confirmed.
    OutcomeVerified,
    /// Real-user value confirmed via randomised control comparison.
    RealUserValueVerified,
    /// Outcome moved in the wrong direction vs. the frozen baseline.
    Regressed,
    /// Prespecified target or minimum improvement not achieved.
    NotAchieved,
    /// Outcome contested by explicit negative feedback.
    Contested,
}

impl OutcomeStatus {
    /// True when the status represents a successfully verified outcome.
    pub fn is_verified(&self) -> bool {
        matches!(
            self,
            OutcomeStatus::OutcomeVerified | OutcomeStatus::RealUserValueVerified
        )
    }
}

// ---------------------------------------------------------------------------
// Outcome contract
// ---------------------------------------------------------------------------

/// Direction the measured metric must move to constitute improvement.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum MetricDirection {
    Nondecreasing,
    Nonincreasing,
}

/// Kind of evidence used to assess the outcome.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum EvidenceKind {
    RealUser,
    Engineering,
    Synthetic,
}

/// Frozen outcome contract captured before execution begins.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OutcomeContract {
    /// Measure identifier (matches objective id or outcome_measure_id).
    pub measure_id: String,
    /// Direction the metric must move.
    pub direction: MetricDirection,
    /// Evidence kind declared at contract time.
    pub evidence_kind: EvidenceKind,
    /// Prespecified experiment identifier.
    pub experiment_id: String,
    /// Proportion target in [0, 1].
    pub target: f64,
    /// Minimum absolute delta (nonnegative).
    pub min_delta: f64,
    /// Frozen baseline success rate.
    pub baseline_rate: f64,
    /// Sample count at baseline capture.
    pub baseline_n: u64,
    /// SHA-256 hex digest of the serialised contract, frozen at capture.
    pub contract_hash: String,
}

impl OutcomeContract {
    /// Validate the contract fields are internally consistent.
    pub fn validate(&self) -> Result<(), OutcomeVerificationError> {
        if !(0.0..=1.0).contains(&self.target) {
            return Err(OutcomeVerificationError::InvalidContract(
                "target must be a proportion in [0, 1]".into(),
            ));
        }
        if self.min_delta < 0.0 {
            return Err(OutcomeVerificationError::InvalidContract(
                "min_delta must be nonnegative".into(),
            ));
        }
        if self.experiment_id.is_empty() {
            return Err(OutcomeVerificationError::InvalidContract(
                "experiment_id must be non-empty".into(),
            ));
        }
        Ok(())
    }
}

// ---------------------------------------------------------------------------
// Observation
// ---------------------------------------------------------------------------

/// A single post-deployment observation window.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OutcomeObservation {
    /// Unique identifier for this observation (must not be replayed).
    pub id: String,
    /// Operation id this observation is attributed to.
    pub operation_id: String,
    /// Experiment id — must match the contract.
    pub experiment_id: String,
    /// Number of successes in the treatment arm.
    pub successes: u64,
    /// Total trials in the treatment arm.
    pub trials: u64,
    /// Control arm successes (required for real_user evidence).
    pub control_successes: Option<u64>,
    /// Control arm trials (required for real_user evidence).
    pub control_trials: Option<u64>,
    /// ISO-8601 window start timestamp.
    pub window_start: String,
    /// ISO-8601 observation end timestamp.
    pub at: String,
}

impl OutcomeObservation {
    /// Success rate for this observation (treatment arm).
    pub fn rate(&self) -> Result<f64, OutcomeVerificationError> {
        if self.trials == 0 || self.successes > self.trials {
            return Err(OutcomeVerificationError::EvidenceUnavailable(
                "observation requires 0 <= successes <= trials and trials > 0".into(),
            ));
        }
        Ok(self.successes as f64 / self.trials as f64)
    }

    /// Control arm success rate.
    pub fn control_rate(&self) -> Result<f64, OutcomeVerificationError> {
        let cs = self.control_successes.ok_or_else(|| {
            OutcomeVerificationError::EvidenceUnavailable(
                "control_successes required for real_user evidence".into(),
            )
        })?;
        let ct = self.control_trials.ok_or_else(|| {
            OutcomeVerificationError::EvidenceUnavailable(
                "control_trials required for real_user evidence".into(),
            )
        })?;
        if ct == 0 || cs > ct {
            return Err(OutcomeVerificationError::EvidenceUnavailable(
                "control arm requires 0 <= successes <= trials and trials > 0".into(),
            ));
        }
        Ok(cs as f64 / ct as f64)
    }
}

// ---------------------------------------------------------------------------
// Wilson 95% interval helper
// ---------------------------------------------------------------------------

/// Wilson 95% confidence interval for a binomial proportion.
fn wilson_interval(successes: u64, trials: u64) -> (f64, f64) {
    let n = trials as f64;
    let p = successes as f64 / n;
    let z = 1.959_963_984_540_054_f64; // 97.5th percentile of standard normal
    let denom = 1.0 + z * z / n;
    let center = (p + z * z / (2.0 * n)) / denom;
    let half = z * (p * (1.0 - p) / n + z * z / (4.0 * n * n)).sqrt() / denom;
    (center - half, center + half)
}

// ---------------------------------------------------------------------------
// Verification result
// ---------------------------------------------------------------------------

/// Full outcome verification result.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OutcomeVerificationResult {
    /// Verification status.
    pub status: OutcomeStatus,
    /// Evidence kind declared by the contract.
    pub evidence_kind: EvidenceKind,
    /// Attribution string for the verification.
    pub attribution: String,
    /// Net value delta (mean of per-window deltas vs frozen baseline).
    pub net_value_delta: f64,
    /// True only for REAL_USER_VALUE_VERIFIED.
    pub real_user_value_verified: bool,
    /// Human-readable reason or explanation.
    pub reason: String,
    /// Number of qualifying observation windows.
    pub windows: usize,
}

impl OutcomeVerificationResult {
    fn pending(reason: impl Into<String>, evidence_kind: EvidenceKind) -> Self {
        OutcomeVerificationResult {
            status: OutcomeStatus::PendingOutcome,
            evidence_kind,
            attribution: "UNATTRIBUTED".into(),
            net_value_delta: 0.0,
            real_user_value_verified: false,
            reason: reason.into(),
            windows: 0,
        }
    }
}

// ---------------------------------------------------------------------------
// Core verification function
// ---------------------------------------------------------------------------

/// Verify trial outcome observations against a frozen `OutcomeContract`.
///
/// Returns `PENDING_OUTCOME` when evidence is insufficient, `REGRESSED` on
/// regression, and `OUTCOME_VERIFIED` / `REAL_USER_VALUE_VERIFIED` on success.
/// Net value delta must exceed `SCORE_DELTA_THRESHOLD` (0.0) to pass.
///
/// §62z: callers that act on a verified result (e.g. triggering settlement)
/// must route through the authority gate before taking any autonomous action.
pub fn verify(
    contract: &OutcomeContract,
    operation_id: &str,
    observations: &[OutcomeObservation],
    min_samples: u64,
    min_windows: usize,
) -> Result<OutcomeVerificationResult, OutcomeVerificationError> {
    contract.validate()?;

    let ek = contract.evidence_kind.clone();

    if contract.baseline_n < min_samples {
        return Ok(OutcomeVerificationResult::pending(
            "frozen baseline has insufficient samples",
            ek,
        ));
    }

    let sign: f64 = match contract.direction {
        MetricDirection::Nondecreasing => 1.0,
        MetricDirection::Nonincreasing => -1.0,
    };

    // Filter observations to this operation and experiment; deduplicate by id.
    let mut seen_ids: std::collections::HashSet<String> = std::collections::HashSet::new();
    let mut qualifying: Vec<&OutcomeObservation> = Vec::new();

    for obs in observations {
        if obs.operation_id != operation_id || obs.experiment_id != contract.experiment_id {
            continue;
        }
        if obs.id.is_empty() {
            return Err(OutcomeVerificationError::EvidenceUnavailable(
                "observation identity is required".into(),
            ));
        }
        if seen_ids.contains(&obs.id) {
            return Err(OutcomeVerificationError::EvidenceUnavailable(
                "replayed or duplicate observation identity".into(),
            ));
        }
        seen_ids.insert(obs.id.clone());
        if obs.trials < min_samples {
            continue;
        }
        if contract.evidence_kind == EvidenceKind::RealUser {
            let ct = obs.control_trials.unwrap_or(0);
            if ct < min_samples {
                continue;
            }
        }
        qualifying.push(obs);
    }

    if qualifying.is_empty() {
        return Ok(OutcomeVerificationResult::pending(
            "no new operation-linked observations with sufficient samples",
            ek,
        ));
    }

    // Compute per-window deltas, checking for regression on each.
    let baseline = contract.baseline_rate;
    let mut deltas: Vec<f64> = Vec::with_capacity(qualifying.len());

    for obs in &qualifying {
        let rate = obs.rate()?;
        let delta = sign * (rate - baseline);

        if delta < 0.0 {
            return Ok(OutcomeVerificationResult {
                status: OutcomeStatus::Regressed,
                evidence_kind: ek,
                attribution: "INDEPENDENT_MEASUREMENT".into(),
                net_value_delta: delta,
                real_user_value_verified: false,
                reason: "measured outcome regressed against frozen baseline".into(),
                windows: qualifying.len(),
            });
        }

        let achieved = sign * (rate - contract.target) >= 0.0;
        let above_min_delta = delta > contract.min_delta;
        if !achieved || !above_min_delta {
            return Ok(OutcomeVerificationResult {
                status: OutcomeStatus::NotAchieved,
                evidence_kind: ek,
                attribution: "INDEPENDENT_MEASUREMENT".into(),
                net_value_delta: 0.0,
                real_user_value_verified: false,
                reason: "prespecified target and minimum improvement not achieved".into(),
                windows: qualifying.len(),
            });
        }

        deltas.push(delta);
    }

    if qualifying.len() < min_windows {
        return Ok(OutcomeVerificationResult::pending(
            "more independent follow-up windows are required",
            ek,
        ));
    }

    let mean_delta = deltas.iter().sum::<f64>() / deltas.len() as f64;

    // Guard against trivially zero or negative net delta.
    if mean_delta <= SCORE_DELTA_THRESHOLD {
        return Ok(OutcomeVerificationResult {
            status: OutcomeStatus::NotAchieved,
            evidence_kind: ek,
            attribution: "INDEPENDENT_MEASUREMENT".into(),
            net_value_delta: 0.0,
            real_user_value_verified: false,
            reason: "net value delta does not exceed threshold".into(),
            windows: qualifying.len(),
        });
    }

    // Real-user evidence requires Wilson-bound comparison.
    if contract.evidence_kind == EvidenceKind::RealUser {
        for obs in &qualifying {
            let rate = obs.rate()?;
            let control = obs.control_rate()?;
            let ct = obs.control_trials.unwrap_or(0);
            let (t_lo, _) = wilson_interval(obs.successes, obs.trials);
            let (_, c_hi) = wilson_interval(obs.control_successes.unwrap_or(0), ct);
            let lower_benefit = if sign > 0.0 {
                t_lo - c_hi
            } else {
                control - rate
            };
            if lower_benefit <= contract.min_delta {
                return Ok(OutcomeVerificationResult {
                    status: OutcomeStatus::NotAchieved,
                    evidence_kind: EvidenceKind::RealUser,
                    attribution: "RANDOMIZED_CONTROL_COMPARISON".into(),
                    net_value_delta: 0.0,
                    real_user_value_verified: false,
                    reason:
                        "comparison does not establish improvement with conservative 95% bounds"
                            .into(),
                    windows: qualifying.len(),
                });
            }
        }
        return Ok(OutcomeVerificationResult {
            status: OutcomeStatus::RealUserValueVerified,
            evidence_kind: EvidenceKind::RealUser,
            attribution: "RANDOMIZED_CONTROL_COMPARISON".into(),
            net_value_delta: mean_delta,
            real_user_value_verified: true,
            reason: "positive measured net benefit across the prespecified trial windows; future value is not guaranteed".into(),
            windows: qualifying.len(),
        });
    }

    Ok(OutcomeVerificationResult {
        status: OutcomeStatus::OutcomeVerified,
        evidence_kind: ek,
        attribution: "INDEPENDENT_MEASUREMENT".into(),
        net_value_delta: mean_delta,
        real_user_value_verified: false,
        reason:
            "engineering or synthetic outcome verified; this does not establish real-user value"
                .into(),
        windows: qualifying.len(),
    })
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    fn engineering_contract() -> OutcomeContract {
        OutcomeContract {
            measure_id: "test-measure".into(),
            direction: MetricDirection::Nondecreasing,
            evidence_kind: EvidenceKind::Engineering,
            experiment_id: "exp-1".into(),
            target: 0.8,
            min_delta: 0.01,
            baseline_rate: 0.70,
            baseline_n: 200,
            contract_hash: "hash-placeholder".into(),
        }
    }

    fn obs(id: &str, op: &str, successes: u64, trials: u64) -> OutcomeObservation {
        OutcomeObservation {
            id: id.into(),
            operation_id: op.into(),
            experiment_id: "exp-1".into(),
            successes,
            trials,
            control_successes: None,
            control_trials: None,
            window_start: "2026-01-01T00:00:00Z".into(),
            at: "2026-01-02T00:00:00Z".into(),
        }
    }

    #[test]
    fn passes_when_improvement_exceeds_target() {
        let contract = engineering_contract();
        // 90/100 = 0.90 rate, well above target 0.80 and min_delta 0.01
        let observations = vec![obs("obs-1", "op-1", 90, 100)];
        let result = verify(&contract, "op-1", &observations, 10, 1).unwrap();
        assert_eq!(result.status, OutcomeStatus::OutcomeVerified);
        assert!(!result.real_user_value_verified);
        assert!(result.net_value_delta > SCORE_DELTA_THRESHOLD);
    }

    #[test]
    fn regressed_when_rate_below_baseline() {
        let contract = engineering_contract();
        // 50/100 = 0.50, below baseline 0.70
        let observations = vec![obs("obs-2", "op-2", 50, 100)];
        let result = verify(&contract, "op-2", &observations, 10, 1).unwrap();
        assert_eq!(result.status, OutcomeStatus::Regressed);
        assert!(result.net_value_delta < 0.0);
    }

    #[test]
    fn pending_when_no_qualifying_observations() {
        let contract = engineering_contract();
        // wrong operation_id — no observations match
        let observations = vec![obs("obs-3", "op-other", 90, 100)];
        let result = verify(&contract, "op-3", &observations, 10, 1).unwrap();
        assert_eq!(result.status, OutcomeStatus::PendingOutcome);
    }

    #[test]
    fn not_achieved_when_below_target() {
        let contract = engineering_contract();
        // 75/100 = 0.75, above baseline 0.70 but below target 0.80
        let observations = vec![obs("obs-4", "op-4", 75, 100)];
        let result = verify(&contract, "op-4", &observations, 10, 1).unwrap();
        assert_eq!(result.status, OutcomeStatus::NotAchieved);
    }

    #[test]
    fn duplicate_observation_id_is_rejected() {
        let contract = engineering_contract();
        let observations = vec![
            obs("dup-id", "op-5", 90, 100),
            obs("dup-id", "op-5", 85, 100),
        ];
        let result = verify(&contract, "op-5", &observations, 10, 1);
        assert!(result.is_err(), "duplicate observation id must be rejected");
    }
}
