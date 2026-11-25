//! Value trajectory and acceleration tracking — port of `value_trajectory.py`.
//!
//! Tracks value production rate over successive checkpoints, computes acceleration
//! (is the system getting faster at producing value?), and surfaces deceleration alerts.
//!
//! # Key invariants
//! - Structural counts (normative_rules, behavioral_tests, unresolved_markers) are
//!   never credited as user-value.
//! - `trend()` requires at least 2 data points; returns 0.0 otherwise.

use serde::{Deserialize, Serialize};
use serde_json::Value;

/// Minimum checkpoints required before acceleration can be meaningfully reported.
pub const MIN_CHECKPOINTS_FOR_ACCELERATION: usize = 4;
/// Rolling window sizes for velocity computation.
const RECENT_WINDOW: usize = 5;
const BASELINE_WINDOW: usize = 5;
/// Deceleration alert threshold: velocity < 50% of baseline.
const DECELERATION_ALERT_RATIO: f64 = 0.5;

// ── TrajectoryPoint ───────────────────────────────────────────────────────────

/// A single recorded value-production checkpoint.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct TrajectoryPoint {
    /// ISO-8601 timestamp.
    pub at: String,
    /// APS score (Aggregate Product Score) or value_rate at this checkpoint.
    pub aps_score: f64,
    /// How many evidenced operations contributed to this point.
    pub evidence_count: usize,
    /// Cumulative cycle count at this checkpoint.
    pub cycle_count: usize,
}

// ── ValueTrajectory ───────────────────────────────────────────────────────────

/// Ordered sequence of value-production checkpoints.
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct ValueTrajectory {
    pub points: Vec<TrajectoryPoint>,
}

impl ValueTrajectory {
    pub fn new() -> Self {
        ValueTrajectory { points: Vec::new() }
    }

    /// Add a new checkpoint to the trajectory.
    pub fn push(&mut self, point: TrajectoryPoint) {
        self.points.push(point);
    }

    /// How many points have been recorded.
    pub fn len(&self) -> usize {
        self.points.len()
    }

    pub fn is_empty(&self) -> bool {
        self.points.is_empty()
    }
}

// ── compute_trajectory ────────────────────────────────────────────────────────

/// Build a `ValueTrajectory` from project state.
///
/// Reads `state["value_trajectory"]["checkpoints"]` (written by `record_checkpoint`
/// in the Python module) and converts each entry into a `TrajectoryPoint`.
pub fn compute_trajectory(state: &Value) -> ValueTrajectory {
    let mut trajectory = ValueTrajectory::new();

    let checkpoints = match state
        .get("value_trajectory")
        .and_then(|vt| vt.get("checkpoints"))
        .and_then(|c| c.as_array())
    {
        Some(c) => c,
        None => return trajectory,
    };

    for (i, cp) in checkpoints.iter().enumerate() {
        let aps_score = cp
            .get("value_rate")
            .and_then(|v| v.as_f64())
            .unwrap_or(0.0);
        let at = cp
            .get("at")
            .and_then(|v| v.as_str())
            .unwrap_or("unknown")
            .to_string();
        // evidence_count: operations that produced positive value
        let evidence_count = {
            let improved = cp
                .get("improved_metrics")
                .and_then(|v| v.as_u64())
                .unwrap_or(0) as usize;
            improved
        };
        trajectory.push(TrajectoryPoint {
            at,
            aps_score,
            evidence_count,
            cycle_count: i + 1,
        });
    }

    trajectory
}

// ── trend ─────────────────────────────────────────────────────────────────────

/// Compute the slope of APS scores over the trajectory.
///
/// Uses simple linear regression (least-squares slope) over all points.
/// Returns:
/// - A positive value when the trajectory is accelerating.
/// - A negative value when it is decelerating.
/// - `0.0` when fewer than 2 points exist.
pub fn trend(trajectory: &ValueTrajectory) -> f64 {
    let points = &trajectory.points;
    let n = points.len();
    if n < 2 {
        return 0.0;
    }

    // Least-squares slope: Σ(x_i * y_i) - n*x̄*ȳ  /  Σ(x_i²) - n*x̄²
    let xs: Vec<f64> = (0..n).map(|i| i as f64).collect();
    let ys: Vec<f64> = points.iter().map(|p| p.aps_score).collect();

    let x_mean: f64 = xs.iter().sum::<f64>() / n as f64;
    let y_mean: f64 = ys.iter().sum::<f64>() / n as f64;

    let numerator: f64 = xs.iter().zip(ys.iter()).map(|(x, y)| (x - x_mean) * (y - y_mean)).sum();
    let denominator: f64 = xs.iter().map(|x| (x - x_mean).powi(2)).sum();

    if denominator.abs() < 1e-12 {
        return 0.0;
    }
    numerator / denominator
}

// ── acceleration ──────────────────────────────────────────────────────────────

/// Direction of the value production trend.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum AccelerationDirection {
    Accelerating,
    Decelerating,
    Stable,
    InsufficientData,
}

/// Full acceleration report mirroring `compute_acceleration()` output.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AccelerationReport {
    pub direction: AccelerationDirection,
    pub current_velocity: f64,
    pub baseline_velocity: f64,
    pub trend_slope: f64,
    pub yield_rate: f64,
    pub sample_size: usize,
    pub alerts: Vec<String>,
}

/// Compute acceleration metrics from a `ValueTrajectory`.
pub fn compute_acceleration(trajectory: &ValueTrajectory) -> AccelerationReport {
    let points = &trajectory.points;
    let n = points.len();

    if n < 2 {
        return AccelerationReport {
            direction: AccelerationDirection::InsufficientData,
            current_velocity: 0.0,
            baseline_velocity: 0.0,
            trend_slope: 0.0,
            yield_rate: 0.0,
            sample_size: n,
            alerts: vec![],
        };
    }

    let rates: Vec<f64> = points.iter().map(|p| p.aps_score).collect();

    let recent: &[f64] = &rates[rates.len().saturating_sub(RECENT_WINDOW)..];
    let baseline: &[f64] = &rates[..RECENT_WINDOW.min(rates.len())];

    let current_velocity = recent.iter().sum::<f64>() / recent.len() as f64;
    let baseline_velocity = baseline.iter().sum::<f64>() / baseline.len() as f64;

    let slope = trend(trajectory);

    let direction = if slope.abs() < 0.005 {
        AccelerationDirection::Stable
    } else if slope > 0.0 {
        AccelerationDirection::Accelerating
    } else {
        AccelerationDirection::Decelerating
    };

    // Yield rate: fraction of points with positive aps_score.
    let positive = points.iter().filter(|p| p.aps_score > 0.0).count();
    let yield_rate = positive as f64 / n as f64;

    let mut alerts: Vec<String> = Vec::new();
    if direction == AccelerationDirection::Decelerating {
        if baseline_velocity.abs() > 1e-9 && current_velocity / baseline_velocity < DECELERATION_ALERT_RATIO {
            alerts.push(format!(
                "VELOCITY_BELOW_HALF_BASELINE: current={:.4} is <50% of baseline={:.4}; \
                 consider scope reassessment or task granularity reduction",
                current_velocity, baseline_velocity
            ));
        } else {
            alerts.push(
                "VELOCITY_DECLINING: value production rate is decreasing; monitor for continued decline"
                    .to_string(),
            );
        }
    }
    if yield_rate < 0.5 && n >= MIN_CHECKPOINTS_FOR_ACCELERATION {
        alerts.push(format!(
            "LOW_YIELD_RATE: only {:.0}% of operations produced positive value; \
             consider reprioritizing objectives",
            yield_rate * 100.0
        ));
    }

    AccelerationReport {
        direction,
        current_velocity,
        baseline_velocity,
        trend_slope: slope,
        yield_rate,
        sample_size: n,
        alerts,
    }
}

// ── render_trajectory ─────────────────────────────────────────────────────────

/// Return an ASCII sparkline summary of the trajectory.
///
/// Each point maps to one of `▁▂▃▄▅▆▇█` based on its normalised score.
/// Followed by a one-line text summary of direction + yield.
pub fn render_trajectory(trajectory: &ValueTrajectory) -> String {
    let sparkline_chars: &[char] = &['▁', '▂', '▃', '▄', '▅', '▆', '▇', '█'];

    if trajectory.is_empty() {
        return "No trajectory data recorded yet.".to_string();
    }

    let scores: Vec<f64> = trajectory.points.iter().map(|p| p.aps_score).collect();
    let min_score = scores.iter().cloned().fold(f64::INFINITY, f64::min);
    let max_score = scores.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
    let range = max_score - min_score;

    let sparkline: String = scores
        .iter()
        .map(|&s| {
            if range < 1e-12 {
                sparkline_chars[3] // mid-point when all equal
            } else {
                let idx = ((s - min_score) / range * 7.0).round() as usize;
                sparkline_chars[idx.min(7)]
            }
        })
        .collect();

    let accel = compute_acceleration(trajectory);
    let direction_str = match accel.direction {
        AccelerationDirection::Accelerating => "accelerating",
        AccelerationDirection::Decelerating => "decelerating",
        AccelerationDirection::Stable => "stable",
        AccelerationDirection::InsufficientData => "insufficient data",
    };

    format!(
        "{} | direction={} velocity={:.4} yield={:.0}% points={}",
        sparkline,
        direction_str,
        accel.current_velocity,
        accel.yield_rate * 100.0,
        trajectory.len(),
    )
}

// ── self_correction ───────────────────────────────────────────────────────────

/// Return a self-correction prescription if the trajectory is decelerating
/// with enough data, or `None` when no correction is warranted.
pub fn self_correction_needed(trajectory: &ValueTrajectory) -> Option<String> {
    let accel = compute_acceleration(trajectory);
    if accel.sample_size < MIN_CHECKPOINTS_FOR_ACCELERATION {
        return None;
    }
    if accel.direction != AccelerationDirection::Decelerating {
        return None;
    }
    let severe = accel.baseline_velocity.abs() > 1e-9
        && accel.current_velocity / accel.baseline_velocity < DECELERATION_ALERT_RATIO;
    let low_yield = accel.yield_rate < 0.4;

    if severe || low_yield {
        Some(
            "Inject strategic reassessment objective: review scope priorities, \
             task granularity, and objective quality to recover value production rate"
                .to_string(),
        )
    } else {
        Some("Monitor for continued deceleration before intervening".to_string())
    }
}

// ── Tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn make_trajectory(scores: &[f64]) -> ValueTrajectory {
        let mut traj = ValueTrajectory::new();
        for (i, &s) in scores.iter().enumerate() {
            traj.push(TrajectoryPoint {
                at: format!("2026-01-{:02}T00:00:00Z", i + 1),
                aps_score: s,
                evidence_count: 1,
                cycle_count: i + 1,
            });
        }
        traj
    }

    #[test]
    fn trend_ascending_returns_positive() {
        let traj = make_trajectory(&[1.0, 2.0, 3.0, 4.0, 5.0]);
        assert!(trend(&traj) > 0.0, "ascending data must produce positive trend");
    }

    #[test]
    fn trend_descending_returns_negative() {
        let traj = make_trajectory(&[5.0, 4.0, 3.0, 2.0, 1.0]);
        assert!(trend(&traj) < 0.0, "descending data must produce negative trend");
    }

    #[test]
    fn trend_flat_returns_near_zero() {
        let traj = make_trajectory(&[3.0, 3.0, 3.0, 3.0]);
        assert!(trend(&traj).abs() < 1e-10);
    }

    #[test]
    fn trend_requires_at_least_two_points() {
        let traj = make_trajectory(&[7.5]);
        assert_eq!(trend(&traj), 0.0);
    }

    #[test]
    fn compute_trajectory_reads_state_checkpoints() {
        let state = json!({
            "value_trajectory": {
                "checkpoints": [
                    { "at": "2026-01-01T00:00:00Z", "value_rate": 1.5, "improved_metrics": 2 },
                    { "at": "2026-01-02T00:00:00Z", "value_rate": 2.0, "improved_metrics": 3 },
                ]
            }
        });
        let traj = compute_trajectory(&state);
        assert_eq!(traj.len(), 2);
        assert_eq!(traj.points[0].aps_score, 1.5);
        assert_eq!(traj.points[1].aps_score, 2.0);
    }

    #[test]
    fn render_trajectory_non_empty() {
        let traj = make_trajectory(&[1.0, 2.0, 3.0]);
        let rendered = render_trajectory(&traj);
        assert!(rendered.contains("points=3"));
    }

    #[test]
    fn acceleration_detects_decelerating() {
        // Scores falling sharply — velocity below half baseline.
        let traj = make_trajectory(&[10.0, 9.0, 1.0, 0.5, 0.1, 0.05]);
        let report = compute_acceleration(&traj);
        assert_eq!(report.direction, AccelerationDirection::Decelerating);
        assert!(!report.alerts.is_empty());
    }

    #[test]
    fn self_correction_none_when_insufficient_data() {
        let traj = make_trajectory(&[1.0, 2.0]);
        assert!(self_correction_needed(&traj).is_none());
    }
}
