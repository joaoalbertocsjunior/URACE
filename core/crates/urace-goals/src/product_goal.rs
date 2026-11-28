//! ProductGoal — machine-checkable product improvement specification.
//!
//! A ProductGoal binds a measurable metric, a direction, and an optional threshold.
//! Improvement is proven when `compute_delta` returns a positive value.

use serde::{Deserialize, Serialize};
use thiserror::Error;

#[derive(Debug, Error)]
pub enum ProductGoalError {
    #[error("epsilon must be > 0, got {0}")]
    InvalidEpsilon(f64),
    #[error("threshold must be finite, got {0}")]
    InvalidThreshold(f64),
}

/// Direction of improvement for a ProductGoal metric.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "PascalCase")]
pub enum GoalDirection {
    /// Higher metric value = improvement (e.g. test_pass_rate, coverage_pct).
    Maximize,
    /// Lower metric value = improvement (e.g. p99_latency_ms, error_rate).
    Minimize,
}

impl GoalDirection {
    /// +1.0 for Maximize, -1.0 for Minimize.
    pub fn sign(&self) -> f64 {
        match self {
            GoalDirection::Maximize => 1.0,
            GoalDirection::Minimize => -1.0,
        }
    }
}

/// A machine-checkable product improvement specification.
///
/// # Example
/// ```
/// use urace_goals::product_goal::{ProductGoal, GoalDirection};
/// let goal = ProductGoal::new("test_pass_rate", GoalDirection::Maximize, None, 0.001).unwrap();
/// assert!(goal.is_improvement(0.80, 0.85));  // 0.85 > 0.80 → improvement
/// assert!(!goal.is_improvement(0.80, 0.80)); // no change → not improvement
/// ```
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProductGoal {
    /// The observable quantity (e.g. "test_pass_rate", "p99_latency_ms").
    pub metric: String,
    /// Direction that counts as improvement.
    pub direction: GoalDirection,
    /// Optional target value; `None` = open-ended improvement.
    pub threshold: Option<f64>,
    /// Minimum absolute change that counts as a real improvement (noise floor).
    pub epsilon: f64,
}

impl ProductGoal {
    pub fn new(
        metric: impl Into<String>,
        direction: GoalDirection,
        threshold: Option<f64>,
        epsilon: f64,
    ) -> Result<Self, ProductGoalError> {
        if epsilon <= 0.0 {
            return Err(ProductGoalError::InvalidEpsilon(epsilon));
        }
        if let Some(t) = threshold {
            if !t.is_finite() {
                return Err(ProductGoalError::InvalidThreshold(t));
            }
        }
        Ok(ProductGoal {
            metric: metric.into(),
            direction,
            threshold,
            epsilon,
        })
    }

    /// Compute the signed product delta: positive = improvement, negative = regression.
    ///
    /// `prior` is the metric value before the change; `current` is after.
    /// Returns `direction.sign() * (current - prior)`.
    pub fn compute_delta(&self, prior: f64, current: f64) -> f64 {
        self.direction.sign() * (current - prior)
    }

    /// Returns true if the change from `prior` to `current` is a genuine improvement
    /// (delta >= epsilon).
    pub fn is_improvement(&self, prior: f64, current: f64) -> bool {
        self.compute_delta(prior, current) >= self.epsilon
    }

    /// Returns true if the threshold has been met or exceeded.
    /// Always false for open-ended goals (threshold = None).
    pub fn threshold_met(&self, current: f64) -> bool {
        match self.threshold {
            None => false,
            Some(t) => match self.direction {
                GoalDirection::Maximize => current >= t,
                GoalDirection::Minimize => current <= t,
            },
        }
    }
}

/// A recorded product delta entry — written to the journal alongside task_outcome.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProductDeltaRecord {
    pub goal_id: String,
    pub task_id: String,
    pub metric: String,
    pub prior_value: f64,
    pub current_value: f64,
    /// Signed delta: positive = improvement.
    pub delta: f64,
    /// True if delta >= epsilon.
    pub is_improvement: bool,
    pub recorded_at: String,
}

impl ProductDeltaRecord {
    pub fn new(
        goal: &ProductGoal,
        goal_id: impl Into<String>,
        task_id: impl Into<String>,
        prior: f64,
        current: f64,
    ) -> Self {
        let delta = goal.compute_delta(prior, current);
        ProductDeltaRecord {
            goal_id: goal_id.into(),
            task_id: task_id.into(),
            metric: goal.metric.clone(),
            prior_value: prior,
            current_value: current,
            delta,
            is_improvement: delta >= goal.epsilon,
            recorded_at: now_iso(),
        }
    }
}

fn now_iso() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    let secs = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);
    format!("{secs}")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn maximize_improvement() {
        let g = ProductGoal::new("test_pass_rate", GoalDirection::Maximize, None, 0.001).unwrap();
        assert!(g.is_improvement(0.80, 0.85));
        assert!(!g.is_improvement(0.85, 0.80)); // regression
        assert!(!g.is_improvement(0.80, 0.80)); // no change
    }

    #[test]
    fn minimize_improvement() {
        let g = ProductGoal::new("p99_latency_ms", GoalDirection::Minimize, None, 0.1).unwrap();
        assert!(g.is_improvement(100.0, 95.0)); // latency dropped → improvement
        assert!(!g.is_improvement(95.0, 100.0)); // latency grew → regression
    }

    #[test]
    fn threshold_met() {
        let g = ProductGoal::new("coverage_pct", GoalDirection::Maximize, Some(90.0), 0.01).unwrap();
        assert!(g.threshold_met(90.0));
        assert!(g.threshold_met(95.0));
        assert!(!g.threshold_met(89.9));
    }

    #[test]
    fn invalid_epsilon_rejected() {
        assert!(ProductGoal::new("m", GoalDirection::Maximize, None, 0.0).is_err());
        assert!(ProductGoal::new("m", GoalDirection::Maximize, None, -1.0).is_err());
    }

    #[test]
    fn delta_record_fields() {
        let g = ProductGoal::new("test_pass_rate", GoalDirection::Maximize, None, 0.001).unwrap();
        let r = ProductDeltaRecord::new(&g, "goal-1", "task-1", 0.75, 0.80);
        assert!((r.delta - 0.05).abs() < 1e-9);
        assert!(r.is_improvement);
    }
}
