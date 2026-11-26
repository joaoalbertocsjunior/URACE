//! M45 — Post-delivery quality gate.
//!
//! The mandatory second gate after delivery proof (M44) and before mint.

use crate::quality_floor::{QualityFloor, QualityFloorError, QualityGateResult};
use serde::{Deserialize, Serialize};
use thiserror::Error;

#[derive(Debug, Error)]
pub enum PostDeliveryError {
    #[error("quality gate failure: {0}")]
    QualityGate(#[from] QualityFloorError),
    #[error("delivery proof not present for work_id '{0}'")]
    NoDeliveryProof(String),
    #[error("awaiting multi-evaluator consensus for work_id '{0}'")]
    PendingSampling(String),
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum PostDeliveryOutcome {
    Approved { score: f64 },
    Rejected { reason: String },
    PendingSampling { work_id: String, sampled_at: String },
}

pub struct PostDeliveryGate {
    quality_floor: QualityFloor,
    /// Fraction of work sampled for multi-evaluator consensus (0.0 to 1.0).
    sampling_probability: f64,
}

impl PostDeliveryGate {
    pub fn new(floor: f64, sampling_probability: f64) -> Self {
        PostDeliveryGate {
            quality_floor: QualityFloor::new(floor),
            sampling_probability: sampling_probability.clamp(0.0, 1.0),
        }
    }

    pub fn default() -> Self {
        PostDeliveryGate::new(0.6, 0.2) // 60% floor, 20% sampling
    }

    /// Evaluate work product.
    ///
    /// `delivery_proof_present` must be `true` (caller verifies via M44).
    /// `score` is the automated quality score (e.g. from M47 benchmark).
    /// `random_sample` is a \[0,1) value from a secure RNG — if less than
    /// `sampling_probability`, the work item is routed for multi-evaluator review.
    pub fn evaluate(
        &self,
        work_id: &str,
        score: f64,
        delivery_proof_present: bool,
        random_sample: f64,
    ) -> Result<PostDeliveryOutcome, PostDeliveryError> {
        if !delivery_proof_present {
            return Err(PostDeliveryError::NoDeliveryProof(work_id.to_string()));
        }
        // Quality floor gate (propagates QualityFloorError via From impl).
        let _gate_result: QualityGateResult = self.quality_floor.check(score)?;
        // Sampling gate.
        if random_sample < self.sampling_probability {
            return Err(PostDeliveryError::PendingSampling(work_id.to_string()));
        }
        Ok(PostDeliveryOutcome::Approved { score })
    }

    pub fn floor(&self) -> f64 {
        self.quality_floor.floor()
    }

    pub fn sampling_probability(&self) -> f64 {
        self.sampling_probability
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    fn gate() -> PostDeliveryGate {
        PostDeliveryGate::new(0.6, 0.2)
    }

    #[test]
    fn no_proof_rejected() {
        let g = gate();
        let err = g
            .evaluate("work-1", 0.9, false, 0.5)
            .expect_err("missing proof must be rejected");
        matches!(err, PostDeliveryError::NoDeliveryProof(_));
    }

    #[test]
    fn below_floor_rejected() {
        let g = gate();
        let err = g
            .evaluate("work-2", 0.4, true, 0.5)
            .expect_err("below-floor score must be rejected");
        matches!(err, PostDeliveryError::QualityGate(_));
    }

    #[test]
    fn above_floor_not_sampled_approved() {
        let g = gate();
        // random_sample = 0.5 >= sampling_probability 0.2 → not sampled
        let outcome = g
            .evaluate("work-3", 0.8, true, 0.5)
            .expect("should be approved");
        matches!(outcome, PostDeliveryOutcome::Approved { .. });
    }

    #[test]
    fn above_floor_sampled_pending() {
        let g = gate();
        // random_sample = 0.1 < sampling_probability 0.2 → sampled
        let err = g
            .evaluate("work-4", 0.8, true, 0.1)
            .expect_err("sampled work should return PendingSampling");
        matches!(err, PostDeliveryError::PendingSampling(_));
    }
}
