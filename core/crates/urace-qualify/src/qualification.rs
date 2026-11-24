//! Qualification engine: score_delta computation and mint-trigger logic.
//!
//! # Key invariants
//! - `qualify()` only sets `should_mint = true` when `score_delta > 0`.
//!   Zero or negative deltas NEVER trigger minting.
//! - `UNIT = 100_000_000` (10^8 UCR base units).
//! - Mint triggers only on qualified acceptance — never on zero or negative score_delta.

use serde::{Deserialize, Serialize};
use thiserror::Error;

use crate::UNIT;

#[derive(Debug, Error)]
pub enum QualificationError {
    #[error("invalid score: {0}")]
    InvalidScore(String),
}

/// A qualification score capturing baseline and candidate metric values.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QualificationScore {
    /// The metric value of the baseline (accepted) product.
    pub baseline_score: i64,
    /// The metric value of the candidate.
    pub candidate_score: i64,
    /// Delta: candidate_score - baseline_score. Positive means improvement.
    pub score_delta: i64,
}

impl QualificationScore {
    /// Create a new score and compute the delta.
    pub fn new(baseline_score: i64, candidate_score: i64) -> Self {
        QualificationScore {
            baseline_score,
            candidate_score,
            score_delta: candidate_score - baseline_score,
        }
    }
}

/// Result of running the qualification engine.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QualificationResult {
    pub trial_id: String,
    pub feature_id: String,
    pub score: QualificationScore,
    /// True only when score_delta > 0 (the sole valid mint condition).
    pub should_mint: bool,
    /// Mint amount in base UCR units (None when should_mint is false).
    pub mint_amount: Option<u64>,
}

/// Qualification engine: evaluates a trial and determines minting eligibility.
pub struct QualificationEngine;

impl QualificationEngine {
    pub fn new() -> Self {
        QualificationEngine
    }

    /// Qualify a trial run. Minting is authorised **only** when `score_delta > 0`.
    ///
    /// # Invariant
    /// - `result.should_mint == true` IFF `score.score_delta > 0`.
    /// - Zero or negative score_delta never produce a mint.
    pub fn qualify(
        &self,
        trial_id: &str,
        feature_id: &str,
        baseline_score: i64,
        candidate_score: i64,
    ) -> Result<QualificationResult, QualificationError> {
        let score = QualificationScore::new(baseline_score, candidate_score);

        // §mint-invariant: only positive score_delta authorises minting.
        let should_mint = score.score_delta > 0;
        let mint_amount = if should_mint {
            // Clamp delta to [1, PEER_CAP / UNIT] tokens, expressed in base units.
            let peer_cap_units: u64 = 50 * UNIT; // 50 UCR
            let raw = score.score_delta as u64;
            Some(raw.clamp(1, peer_cap_units))
        } else {
            None
        };

        Ok(QualificationResult {
            trial_id: trial_id.to_owned(),
            feature_id: feature_id.to_owned(),
            score,
            should_mint,
            mint_amount,
        })
    }
}

impl Default for QualificationEngine {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn positive_delta_enables_mint() {
        let engine = QualificationEngine::new();
        let result = engine.qualify("trial-1", "feat-a", 100, 105).unwrap();
        assert_eq!(result.score.score_delta, 5);
        assert!(result.should_mint, "score_delta=5 must trigger mint");
        assert!(result.mint_amount.is_some());
        assert_eq!(result.mint_amount.unwrap(), 5);
    }

    #[test]
    fn zero_delta_does_not_mint() {
        let engine = QualificationEngine::new();
        let result = engine.qualify("trial-1", "feat-a", 100, 100).unwrap();
        assert_eq!(result.score.score_delta, 0);
        assert!(!result.should_mint, "score_delta=0 must NOT trigger mint");
        assert!(result.mint_amount.is_none());
    }

    #[test]
    fn negative_delta_does_not_mint() {
        let engine = QualificationEngine::new();
        let result = engine.qualify("trial-1", "feat-a", 100, 90).unwrap();
        assert_eq!(result.score.score_delta, -10);
        assert!(!result.should_mint, "negative score_delta must NOT trigger mint");
        assert!(result.mint_amount.is_none());
    }

    #[test]
    fn unit_constant_is_correct() {
        // UNIT = 10^8 UCR base units
        assert_eq!(UNIT, 100_000_000u64);
    }

    #[test]
    fn mint_amount_clamped_to_peer_cap() {
        let engine = QualificationEngine::new();
        let huge_delta = (50 * UNIT as i64) + 1_000_000;
        let result = engine.qualify("trial-1", "feat-a", 0, huge_delta).unwrap();
        assert!(result.should_mint);
        assert_eq!(result.mint_amount.unwrap(), 50 * UNIT);
    }
}
