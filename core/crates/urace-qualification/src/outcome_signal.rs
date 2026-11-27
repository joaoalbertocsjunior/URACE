//! Post-deployment outcome signals: reputation updates from confirmed feature outcomes.
//!
//! Once a feature is deployed, independent peers may report whether it caused an
//! improvement, regression, or neutral outcome.  Signals require ≥3 corroborating
//! peers (none of which may be the submitting executor) and must be observed within
//! 7 days.  Reputation deltas are capped at ±1.0 to prevent outsized swings.
//!
//! # Key invariants
//! - `MINIMUM_CORROBORATING_PEERS = 3` — a signal without independent confirmation
//!   is rejected before recording.
//! - The submitting executor (`executor_peer_id`) cannot appear in
//!   `corroborating_peers` (no self-corroboration).
//! - `OutcomeSignalStore` is append-only; recorded signals are never mutated.
//! - `evidence_hash` must be a valid 64-character lowercase hex string.

use serde::{Deserialize, Serialize};
use thiserror::Error;

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/// Minimum number of independent peers that must corroborate a signal.
pub const MINIMUM_CORROBORATING_PEERS: usize = 3;

/// Maximum age (in seconds) for a signal to be considered non-stale (7 days).
pub const OUTCOME_SIGNAL_MAX_AGE_SECS: u64 = 7 * 24 * 3600;

// ---------------------------------------------------------------------------
// OutcomeKind
// ---------------------------------------------------------------------------

/// The kind of outcome observed post-deployment.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(tag = "kind", content = "data", rename_all = "snake_case")]
pub enum OutcomeKind {
    /// Positive impact confirmed post-deployment.
    Improvement {
        /// Measured score improvement (should be positive).
        score_delta: f64,
    },
    /// Negative impact confirmed post-deployment.
    Regression {
        /// Measured score change (should be negative).
        score_delta: f64,
    },
    /// No measurable impact.
    Neutral,
}

// ---------------------------------------------------------------------------
// OutcomeSignal
// ---------------------------------------------------------------------------

/// A post-deployment outcome signal from the peer network.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OutcomeSignal {
    /// UUID-style unique identifier for this signal.
    pub signal_id: String,
    /// The feature this signal pertains to.
    pub feature_id: String,
    /// Peer ID of the executor who submitted the feature.
    pub executor_peer_id: String,
    /// The kind of outcome observed.
    pub kind: OutcomeKind,
    /// Unix timestamp (seconds) when the outcome was observed.
    pub observed_at_secs: u64,
    /// Peer IDs that independently confirmed this outcome (must be ≥ MINIMUM_CORROBORATING_PEERS).
    pub corroborating_peers: Vec<String>,
    /// SHA-256 hex digest of the evidence payload (64 lowercase hex chars).
    pub evidence_hash: String,
}

// ---------------------------------------------------------------------------
// OutcomeSignalError
// ---------------------------------------------------------------------------

/// Errors that can occur when validating or recording an outcome signal.
#[derive(Debug, Error, PartialEq)]
pub enum OutcomeSignalError {
    #[error("insufficient corroboration: got {got}, need {need}")]
    InsufficientCorroboration { got: usize, need: usize },

    #[error("stale signal: age {age_secs}s exceeds maximum {}", OUTCOME_SIGNAL_MAX_AGE_SECS)]
    StaleSignal { age_secs: u64 },

    #[error("self-corroboration: executor peer '{peer_id}' cannot corroborate their own signal")]
    SelfCorroboration { peer_id: String },

    #[error("invalid evidence hash: must be a 64-character lowercase hex string")]
    InvalidEvidenceHash,
}

// ---------------------------------------------------------------------------
// Validation
// ---------------------------------------------------------------------------

/// Validate an `OutcomeSignal` against all structural and temporal constraints.
///
/// 1. `corroborating_peers.len() >= MINIMUM_CORROBORATING_PEERS`
/// 2. `executor_peer_id` must not appear in `corroborating_peers`
/// 3. `observed_at_secs` age must not exceed `OUTCOME_SIGNAL_MAX_AGE_SECS`
/// 4. `evidence_hash` must be a valid 64-char lowercase hex string
pub fn validate_signal(signal: &OutcomeSignal, now_secs: u64) -> Result<(), OutcomeSignalError> {
    // 1. Corroboration count
    let got = signal.corroborating_peers.len();
    if got < MINIMUM_CORROBORATING_PEERS {
        return Err(OutcomeSignalError::InsufficientCorroboration {
            got,
            need: MINIMUM_CORROBORATING_PEERS,
        });
    }

    // 2. No self-corroboration
    if signal
        .corroborating_peers
        .contains(&signal.executor_peer_id)
    {
        return Err(OutcomeSignalError::SelfCorroboration {
            peer_id: signal.executor_peer_id.clone(),
        });
    }

    // 3. Staleness check
    let age_secs = now_secs.saturating_sub(signal.observed_at_secs);
    if age_secs > OUTCOME_SIGNAL_MAX_AGE_SECS {
        return Err(OutcomeSignalError::StaleSignal { age_secs });
    }

    // 4. Evidence hash must be 64 lowercase hex chars
    if signal.evidence_hash.len() != 64
        || !signal
            .evidence_hash
            .chars()
            .all(|c| c.is_ascii_hexdigit() && !c.is_ascii_uppercase())
    {
        return Err(OutcomeSignalError::InvalidEvidenceHash);
    }

    Ok(())
}

// ---------------------------------------------------------------------------
// Reputation delta
// ---------------------------------------------------------------------------

/// Compute the reputation delta to apply from an outcome signal.
///
/// - `Improvement(delta)` → `+delta * 0.1`, capped to `[−1.0, +1.0]`
/// - `Regression(delta)`  → `delta * 0.1` (delta is negative), capped similarly
/// - `Neutral`            → `0.0`
pub fn reputation_delta_from_signal(signal: &OutcomeSignal) -> f64 {
    let raw = match &signal.kind {
        OutcomeKind::Improvement { score_delta } => score_delta * 0.1,
        OutcomeKind::Regression { score_delta } => score_delta * 0.1,
        OutcomeKind::Neutral => 0.0,
    };
    raw.clamp(-1.0, 1.0)
}

// ---------------------------------------------------------------------------
// OutcomeSignalStore
// ---------------------------------------------------------------------------

/// Append-only in-memory store for validated outcome signals.
#[derive(Debug, Default)]
pub struct OutcomeSignalStore {
    signals: Vec<OutcomeSignal>,
}

impl OutcomeSignalStore {
    /// Create a new, empty store.
    pub fn new() -> Self {
        Self::default()
    }

    /// Validate and record a new outcome signal.
    ///
    /// Returns `Err` if the signal fails validation; the store is not modified
    /// on failure.
    pub fn record(
        &mut self,
        signal: OutcomeSignal,
        now_secs: u64,
    ) -> Result<(), OutcomeSignalError> {
        validate_signal(&signal, now_secs)?;
        self.signals.push(signal);
        Ok(())
    }

    /// Return all signals for a given feature.
    pub fn signals_for_feature(&self, feature_id: &str) -> Vec<&OutcomeSignal> {
        self.signals
            .iter()
            .filter(|s| s.feature_id == feature_id)
            .collect()
    }

    /// Return all signals attributed to a given executor.
    pub fn signals_for_executor(&self, executor_peer_id: &str) -> Vec<&OutcomeSignal> {
        self.signals
            .iter()
            .filter(|s| s.executor_peer_id == executor_peer_id)
            .collect()
    }

    /// Compute the cumulative reputation delta for an executor across all their signals.
    pub fn cumulative_reputation_delta(&self, executor_peer_id: &str) -> f64 {
        self.signals_for_executor(executor_peer_id)
            .iter()
            .map(|s| reputation_delta_from_signal(s))
            .sum()
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    const NOW: u64 = 1_000_000;

    /// A valid 64-char lowercase hex string.
    fn valid_hash() -> String {
        "a".repeat(64)
    }

    fn make_signal(
        executor: &str,
        corroborators: Vec<&str>,
        kind: OutcomeKind,
        observed_at_secs: u64,
        evidence_hash: &str,
    ) -> OutcomeSignal {
        OutcomeSignal {
            signal_id: "sig-1".into(),
            feature_id: "feat-1".into(),
            executor_peer_id: executor.into(),
            kind,
            observed_at_secs,
            corroborating_peers: corroborators.into_iter().map(|s| s.to_owned()).collect(),
            evidence_hash: evidence_hash.to_owned(),
        }
    }

    // --- happy path ----------------------------------------------------------

    #[test]
    fn valid_signal_passes_validation() {
        let sig = make_signal(
            "exec-1",
            vec!["peer-a", "peer-b", "peer-c"],
            OutcomeKind::Improvement { score_delta: 0.5 },
            NOW,
            &valid_hash(),
        );
        assert!(validate_signal(&sig, NOW).is_ok());
    }

    #[test]
    fn improvement_reputation_delta_is_positive() {
        let sig = make_signal(
            "exec-1",
            vec!["peer-a", "peer-b", "peer-c"],
            OutcomeKind::Improvement { score_delta: 4.0 },
            NOW,
            &valid_hash(),
        );
        let delta = reputation_delta_from_signal(&sig);
        assert!((delta - 0.4).abs() < 1e-10);
    }

    #[test]
    fn regression_reputation_delta_is_negative() {
        let sig = make_signal(
            "exec-1",
            vec!["peer-a", "peer-b", "peer-c"],
            OutcomeKind::Regression { score_delta: -3.0 },
            NOW,
            &valid_hash(),
        );
        let delta = reputation_delta_from_signal(&sig);
        assert!((delta - (-0.3)).abs() < 1e-10);
    }

    // --- boundary conditions -------------------------------------------------

    #[test]
    fn reputation_delta_capped_at_positive_one() {
        let sig = make_signal(
            "exec-1",
            vec!["peer-a", "peer-b", "peer-c"],
            OutcomeKind::Improvement { score_delta: 100.0 },
            NOW,
            &valid_hash(),
        );
        assert_eq!(reputation_delta_from_signal(&sig), 1.0);
    }

    #[test]
    fn reputation_delta_capped_at_negative_one() {
        let sig = make_signal(
            "exec-1",
            vec!["peer-a", "peer-b", "peer-c"],
            OutcomeKind::Regression { score_delta: -100.0 },
            NOW,
            &valid_hash(),
        );
        assert_eq!(reputation_delta_from_signal(&sig), -1.0);
    }

    #[test]
    fn neutral_reputation_delta_is_zero() {
        let sig = make_signal(
            "exec-1",
            vec!["peer-a", "peer-b", "peer-c"],
            OutcomeKind::Neutral,
            NOW,
            &valid_hash(),
        );
        assert_eq!(reputation_delta_from_signal(&sig), 0.0);
    }

    #[test]
    fn exactly_three_corroborators_is_accepted() {
        let sig = make_signal(
            "exec-1",
            vec!["peer-a", "peer-b", "peer-c"],
            OutcomeKind::Neutral,
            NOW,
            &valid_hash(),
        );
        assert!(validate_signal(&sig, NOW).is_ok());
    }

    // --- exploit prevention --------------------------------------------------

    #[test]
    fn insufficient_corroboration_rejected() {
        let sig = make_signal(
            "exec-1",
            vec!["peer-a", "peer-b"],
            OutcomeKind::Neutral,
            NOW,
            &valid_hash(),
        );
        assert_eq!(
            validate_signal(&sig, NOW),
            Err(OutcomeSignalError::InsufficientCorroboration { got: 2, need: 3 })
        );
    }

    #[test]
    fn self_corroboration_rejected() {
        // executor appears in its own corroborating_peers list
        let sig = make_signal(
            "exec-1",
            vec!["exec-1", "peer-b", "peer-c"],
            OutcomeKind::Neutral,
            NOW,
            &valid_hash(),
        );
        assert_eq!(
            validate_signal(&sig, NOW),
            Err(OutcomeSignalError::SelfCorroboration {
                peer_id: "exec-1".into()
            })
        );
    }

    #[test]
    fn stale_signal_rejected() {
        let age = OUTCOME_SIGNAL_MAX_AGE_SECS + 1;
        let sig = make_signal(
            "exec-1",
            vec!["peer-a", "peer-b", "peer-c"],
            OutcomeKind::Neutral,
            NOW - age,
            &valid_hash(),
        );
        match validate_signal(&sig, NOW) {
            Err(OutcomeSignalError::StaleSignal { age_secs }) => {
                assert!(age_secs > OUTCOME_SIGNAL_MAX_AGE_SECS)
            }
            other => panic!("expected StaleSignal, got {:?}", other),
        }
    }

    #[test]
    fn invalid_evidence_hash_rejected() {
        let sig = make_signal(
            "exec-1",
            vec!["peer-a", "peer-b", "peer-c"],
            OutcomeKind::Neutral,
            NOW,
            "not-valid-hex",
        );
        assert_eq!(
            validate_signal(&sig, NOW),
            Err(OutcomeSignalError::InvalidEvidenceHash)
        );
    }

    #[test]
    fn uppercase_hash_rejected() {
        // 64 chars but uppercase — should fail
        let sig = make_signal(
            "exec-1",
            vec!["peer-a", "peer-b", "peer-c"],
            OutcomeKind::Neutral,
            NOW,
            &"A".repeat(64),
        );
        assert_eq!(
            validate_signal(&sig, NOW),
            Err(OutcomeSignalError::InvalidEvidenceHash)
        );
    }

    // --- store ---------------------------------------------------------------

    #[test]
    fn store_records_valid_signal_and_queries() {
        let mut store = OutcomeSignalStore::new();
        let sig = OutcomeSignal {
            signal_id: "s1".into(),
            feature_id: "feat-x".into(),
            executor_peer_id: "exec-1".into(),
            kind: OutcomeKind::Improvement { score_delta: 2.0 },
            observed_at_secs: NOW,
            corroborating_peers: vec!["p1".into(), "p2".into(), "p3".into()],
            evidence_hash: valid_hash(),
        };
        store.record(sig, NOW).unwrap();

        assert_eq!(store.signals_for_feature("feat-x").len(), 1);
        assert_eq!(store.signals_for_executor("exec-1").len(), 1);
    }

    #[test]
    fn store_rejects_invalid_signal() {
        let mut store = OutcomeSignalStore::new();
        let bad = OutcomeSignal {
            signal_id: "s2".into(),
            feature_id: "feat-y".into(),
            executor_peer_id: "exec-2".into(),
            kind: OutcomeKind::Neutral,
            observed_at_secs: NOW,
            corroborating_peers: vec![], // too few
            evidence_hash: valid_hash(),
        };
        assert!(store.record(bad, NOW).is_err());
        assert_eq!(store.signals_for_feature("feat-y").len(), 0);
    }

    #[test]
    fn cumulative_reputation_delta_sums_correctly() {
        let mut store = OutcomeSignalStore::new();

        for (i, kind) in [
            OutcomeKind::Improvement { score_delta: 2.0 }, // +0.2
            OutcomeKind::Regression { score_delta: -1.0 }, // -0.1
        ]
        .into_iter()
        .enumerate()
        {
            store
                .record(
                    OutcomeSignal {
                        signal_id: format!("s{i}"),
                        feature_id: format!("feat-{i}"),
                        executor_peer_id: "exec-3".into(),
                        kind,
                        observed_at_secs: NOW,
                        corroborating_peers: vec!["p1".into(), "p2".into(), "p3".into()],
                        evidence_hash: valid_hash(),
                    },
                    NOW,
                )
                .unwrap();
        }

        let delta = store.cumulative_reputation_delta("exec-3");
        assert!((delta - 0.1).abs() < 1e-10);
    }
}
