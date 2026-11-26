//! M31 — Quality floor enforcement.
//!
//! Work results below a minimum quality score are rejected pre-mint.

use serde::{Deserialize, Serialize};
use thiserror::Error;

pub const DEFAULT_QUALITY_FLOOR: f64 = 0.6; // 60% minimum score

#[derive(Debug, Error)]
pub enum QualityFloorError {
    #[error("quality gate failure: score {score:.3} < floor {floor:.3}")]
    BelowFloor { score: f64, floor: f64 },
    #[error("score out of range [0.0, 1.0]: {score}")]
    InvalidScore { score: f64 },
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QualityGateResult {
    pub score: f64,
    pub floor: f64,
    pub passed: bool,
    pub evaluated_at: String, // Unix timestamp secs as string
}

pub struct QualityFloor {
    floor: f64,
}

impl QualityFloor {
    pub fn new(floor: f64) -> Self {
        QualityFloor {
            floor: floor.clamp(0.0, 1.0),
        }
    }

    pub fn default() -> Self {
        QualityFloor::new(DEFAULT_QUALITY_FLOOR)
    }

    /// Check whether `score` meets the quality floor.
    pub fn check(&self, score: f64) -> Result<QualityGateResult, QualityFloorError> {
        if !(0.0..=1.0).contains(&score) {
            return Err(QualityFloorError::InvalidScore { score });
        }
        let passed = score >= self.floor;
        let result = QualityGateResult {
            score,
            floor: self.floor,
            passed,
            evaluated_at: now_secs_str(),
        };
        if !passed {
            return Err(QualityFloorError::BelowFloor {
                score,
                floor: self.floor,
            });
        }
        Ok(result)
    }

    pub fn floor(&self) -> f64 {
        self.floor
    }
}

fn now_secs_str() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs().to_string())
        .unwrap_or_else(|_| "0".to_string())
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn above_floor_passes() {
        let gate = QualityFloor::new(0.6);
        let result = gate.check(0.75).expect("should pass above floor");
        assert!(result.passed);
        assert!((result.score - 0.75).abs() < f64::EPSILON);
    }

    #[test]
    fn at_floor_passes() {
        let gate = QualityFloor::new(0.6);
        let result = gate.check(0.6).expect("score at floor should pass");
        assert!(result.passed);
    }

    #[test]
    fn below_floor_fails() {
        let gate = QualityFloor::new(0.6);
        let err = gate.check(0.5).expect_err("should fail below floor");
        matches!(err, QualityFloorError::BelowFloor { .. });
    }

    #[test]
    fn invalid_score_rejected() {
        let gate = QualityFloor::new(0.6);
        let err = gate.check(1.5).expect_err("score > 1.0 should be rejected");
        matches!(err, QualityFloorError::InvalidScore { .. });
        let err2 = gate
            .check(-0.1)
            .expect_err("score < 0.0 should be rejected");
        matches!(err2, QualityFloorError::InvalidScore { .. });
    }
}
