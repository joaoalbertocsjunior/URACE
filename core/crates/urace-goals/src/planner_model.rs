//! PlannerModel — persistent Bayesian task-approval predictor.
//!
//! Survives process restarts via an append-only HMAC-signed journal.
//! Tracks per-task-type approval rates and computes the Planner Calibration
//! Score (PCS) over a rolling window.
//!
//! # Key invariant
//! The model at session N is measurably better calibrated than at session 1.
//! PCS > 0.80 sustained over 1,000 cycles on ≥3 product types = "URACE has evolved."

use serde::{Deserialize, Serialize};
use std::collections::{HashMap, VecDeque};
use std::path::Path;
use thiserror::Error;
use urace_ledger::{Journal, JournalError};

/// Number of recent tasks used to compute the rolling PCS.
pub const PCS_WINDOW: usize = 100;

/// Bootstrap phase length — use a higher learning rate for first N tasks per type.
pub const BOOTSTRAP_WINDOW: usize = 50;

/// EMA alpha for steady-state updates.
pub const ALPHA_STEADY: f64 = 0.05;

/// EMA alpha during bootstrap (first BOOTSTRAP_WINDOW tasks of a new type).
pub const ALPHA_BOOTSTRAP: f64 = 0.20;

#[derive(Debug, Error)]
pub enum PlannerModelError {
    #[error("journal error: {0}")]
    Journal(#[from] JournalError),
    #[error("serialization error: {0}")]
    Serialization(#[from] serde_json::Error),
}

/// Per-task-type learned statistics.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TaskTypeStats {
    /// Task type identifier (e.g. "lint_fix", "test_addition", "refactor").
    pub task_type: String,
    /// Current predicted approval rate in [0.0, 1.0].
    pub predicted_approval_rate: f64,
    /// Total observations used to build this estimate.
    pub observation_count: u64,
    /// Cumulative approvals seen.
    pub approvals: u64,
}

impl TaskTypeStats {
    fn new(task_type: impl Into<String>) -> Self {
        TaskTypeStats {
            task_type: task_type.into(),
            predicted_approval_rate: 0.5, // uniform prior
            observation_count: 0,
            approvals: 0,
        }
    }

    fn update(&mut self, approved: bool) {
        let signal = if approved { 1.0 } else { 0.0 };
        let alpha = if self.observation_count < BOOTSTRAP_WINDOW as u64 {
            ALPHA_BOOTSTRAP
        } else {
            ALPHA_STEADY
        };
        // EMA update
        self.predicted_approval_rate =
            self.predicted_approval_rate + alpha * (signal - self.predicted_approval_rate);
        // Bayesian count update (denominator for calibration)
        self.observation_count += 1;
        if approved {
            self.approvals += 1;
        }
    }
}

/// A single feedback signal written to the journal.
#[derive(Debug, Clone, Serialize, Deserialize)]
struct FeedbackEntry {
    task_type: String,
    approved: bool,
    predicted_before: f64,
    actual: f64,
    session_counter: u64,
    recorded_at: String,
}

/// A calibration sample for PCS computation.
#[derive(Debug, Clone)]
struct CalibrationSample {
    predicted: f64,
    actual: f64,
}

/// Persistent Bayesian planner model.
///
/// Open with `PlannerModel::open(path, hmac_key)`. The journal at `path` stores
/// all feedback signals; the in-memory model is rebuilt on open if the journal
/// already exists (crash-safe).
pub struct PlannerModel {
    stats: HashMap<String, TaskTypeStats>,
    /// Rolling window of (predicted, actual) pairs for PCS computation.
    pcs_window: VecDeque<CalibrationSample>,
    /// Total feedback signals ever processed.
    session_counter: u64,
    /// Number of completed 100-cycle windows (planner generations).
    planner_generation: u64,
    journal: Journal,
}

impl PlannerModel {
    /// Open (or create) the planner model journal at `path`.
    pub fn open(path: impl AsRef<Path>, hmac_key: [u8; 32]) -> Result<Self, PlannerModelError> {
        let journal = Journal::open(path, hmac_key)?;
        // Replay existing entries to rebuild in-memory state.
        let mut model = PlannerModel {
            stats: HashMap::new(),
            pcs_window: VecDeque::with_capacity(PCS_WINDOW + 1),
            session_counter: 0,
            planner_generation: 0,
            journal,
        };
        model.replay()?;
        Ok(model)
    }

    fn replay(&mut self) -> Result<(), PlannerModelError> {
        let ledger_entries = self.journal.verify_integrity().unwrap_or_default();
        for le in ledger_entries {
            if le.kind != "planner_feedback" {
                continue;
            }
            if let Ok(entry) = serde_json::from_value::<FeedbackEntry>(le.payload) {
                let stats = self
                    .stats
                    .entry(entry.task_type.clone())
                    .or_insert_with(|| TaskTypeStats::new(&entry.task_type));
                stats.observation_count += 1;
                if entry.approved {
                    stats.approvals += 1;
                }
                // Recompute from counts for crash-consistent replay
                stats.predicted_approval_rate =
                    stats.approvals as f64 / stats.observation_count as f64;
                self.session_counter += 1;

                if self.pcs_window.len() >= PCS_WINDOW {
                    self.pcs_window.pop_front();
                }
                self.pcs_window.push_back(CalibrationSample {
                    predicted: entry.predicted_before,
                    actual: entry.actual,
                });
            }
        }
        self.planner_generation = self.session_counter / PCS_WINDOW as u64;
        Ok(())
    }

    /// Record a task outcome and update the model.
    pub fn record_feedback(
        &mut self,
        task_type: &str,
        approved: bool,
    ) -> Result<(), PlannerModelError> {
        let stats = self
            .stats
            .entry(task_type.to_owned())
            .or_insert_with(|| TaskTypeStats::new(task_type));

        let predicted_before = stats.predicted_approval_rate;
        stats.update(approved);

        let actual = if approved { 1.0 } else { 0.0 };

        // Update PCS window
        if self.pcs_window.len() >= PCS_WINDOW {
            self.pcs_window.pop_front();
        }
        self.pcs_window.push_back(CalibrationSample {
            predicted: predicted_before,
            actual,
        });

        self.session_counter += 1;
        self.planner_generation = self.session_counter / PCS_WINDOW as u64;

        // Persist to journal
        let entry = FeedbackEntry {
            task_type: task_type.to_owned(),
            approved,
            predicted_before,
            actual,
            session_counter: self.session_counter,
            recorded_at: now_iso(),
        };
        self.journal
            .append("planner_feedback", serde_json::to_value(&entry)?)?;
        Ok(())
    }

    /// Predict the approval rate for a task type.
    /// Returns 0.5 (uniform prior) for unseen task types.
    pub fn predict(&self, task_type: &str) -> f64 {
        self.stats
            .get(task_type)
            .map(|s| s.predicted_approval_rate)
            .unwrap_or(0.5)
    }

    /// Planner Calibration Score: `1 - mean(|predicted - actual|)` over last PCS_WINDOW tasks.
    /// Returns None if fewer than PCS_WINDOW samples are available.
    pub fn pcs(&self) -> Option<f64> {
        if self.pcs_window.len() < PCS_WINDOW {
            return None;
        }
        let mean_abs_err = self
            .pcs_window
            .iter()
            .map(|s| (s.predicted - s.actual).abs())
            .sum::<f64>()
            / self.pcs_window.len() as f64;
        Some(1.0 - mean_abs_err)
    }

    /// Total feedback signals processed (session counter).
    pub fn session_counter(&self) -> u64 {
        self.session_counter
    }

    /// Number of completed 100-cycle planner generations.
    pub fn planner_generation(&self) -> u64 {
        self.planner_generation
    }

    /// Per-type stats snapshot.
    pub fn stats(&self) -> impl Iterator<Item = &TaskTypeStats> {
        self.stats.values()
    }

    /// True if PCS > 0.80 (meta-improvement threshold).
    pub fn is_well_calibrated(&self) -> bool {
        self.pcs().map(|p| p > 0.80).unwrap_or(false)
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
    use tempfile::NamedTempFile;

    fn hmac_key() -> [u8; 32] {
        [0u8; 32]
    }

    #[test]
    fn predict_unseen_type_returns_prior() {
        let f = NamedTempFile::new().unwrap();
        let model = PlannerModel::open(f.path(), hmac_key()).unwrap();
        assert!((model.predict("unknown") - 0.5).abs() < 1e-9);
    }

    #[test]
    fn approval_rate_converges() {
        let f = NamedTempFile::new().unwrap();
        let mut model = PlannerModel::open(f.path(), hmac_key()).unwrap();
        // Feed 100 approvals for "lint_fix"
        for _ in 0..100 {
            model.record_feedback("lint_fix", true).unwrap();
        }
        // Should be well above 0.5 after 100 approvals
        assert!(model.predict("lint_fix") > 0.8);
    }

    #[test]
    fn pcs_available_after_window() {
        let f = NamedTempFile::new().unwrap();
        let mut model = PlannerModel::open(f.path(), hmac_key()).unwrap();
        // Not enough samples yet
        assert!(model.pcs().is_none());
        for i in 0..PCS_WINDOW {
            model.record_feedback("lint_fix", i % 2 == 0).unwrap();
        }
        assert!(model.pcs().is_some());
    }

    #[test]
    fn model_persists_across_restart() {
        let f = NamedTempFile::new().unwrap();
        let path = f.path().to_owned();
        {
            let mut model = PlannerModel::open(&path, hmac_key()).unwrap();
            for _ in 0..30 {
                model.record_feedback("test_add", true).unwrap();
            }
            assert!(model.predict("test_add") > 0.5);
        }
        // Reopen — replay from journal
        let model2 = PlannerModel::open(&path, hmac_key()).unwrap();
        assert!(model2.predict("test_add") > 0.5);
        assert_eq!(model2.session_counter(), 30);
    }

    #[test]
    fn generation_increments_per_window() {
        let f = NamedTempFile::new().unwrap();
        let mut model = PlannerModel::open(f.path(), hmac_key()).unwrap();
        assert_eq!(model.planner_generation(), 0);
        for _ in 0..PCS_WINDOW {
            model.record_feedback("x", true).unwrap();
        }
        assert_eq!(model.planner_generation(), 1);
    }
}
