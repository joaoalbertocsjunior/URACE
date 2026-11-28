//! MetricsDashboard — PCS + autonomy rate export for `ImprovementLoop`.
//!
//! Produces a point-in-time `DashboardSnapshot` from live planner model state,
//! cycle outcomes, and optional watchdog data. Snapshots are serialisable to
//! JSON for external monitoring consumption.
//!
//! # Design
//! - No mutable state: `snapshot(...)` is a pure function over its inputs.
//! - `human_confirmations` is computed from `outcomes[i].autonomous == false`.
//! - `supply_health_ratio` is `active_executors / max(queue_depth, 1)`.
//! - `is_well_calibrated` mirrors `PlannerModel::is_well_calibrated()` threshold (> 0.80).

use crate::improvement_loop::{autonomy_rate, improvement_count, CycleOutcome};
use crate::watchdog::LoopWatchdog;
use serde::{Deserialize, Serialize};
use urace_goals::planner_model::PlannerModel;

// ── DashboardSnapshot ─────────────────────────────────────────────────────────

/// A point-in-time metrics snapshot for a single product's improvement loop.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DashboardSnapshot {
    /// Product identifier this snapshot is for.
    pub product_id: String,
    /// Planner generation (epoch — increments every PCS_WINDOW cycles).
    pub planner_generation: u64,
    /// Planner Calibration Score. `None` if fewer than PCS_WINDOW samples exist.
    pub pcs: Option<f64>,
    /// True if `pcs > 0.80` (meta-improvement threshold).
    pub is_well_calibrated: bool,
    /// Fraction of cycles that completed without human confirmation.
    pub autonomy_rate: f64,
    /// Count of cycles that required human confirmation (`autonomous == false`).
    pub human_confirmations: u64,
    /// Total cycles observed in `outcomes`.
    pub total_cycles: u64,
    /// Count of cycles where `is_improvement == true`.
    pub improvement_count: u64,
    /// Delta of the most recent cycle (0.0 if no cycles).
    pub last_product_delta: f64,
    /// Cumulative stall count from the watchdog (0 if no watchdog).
    pub stall_count: u64,
    /// `active_executors / queue_depth` ratio at snapshot time (0.0 if no work).
    pub supply_health_ratio: f64,
    /// ISO-8601-ish timestamp (Unix epoch seconds as string for no-dep portability).
    pub snapshot_at: String,
}

// ── MetricsDashboard ──────────────────────────────────────────────────────────

/// Dashboard builder for a single product.
pub struct MetricsDashboard {
    pub product_id: String,
}

impl MetricsDashboard {
    /// Create a dashboard for `product_id`.
    pub fn new(product_id: impl Into<String>) -> Self {
        MetricsDashboard {
            product_id: product_id.into(),
        }
    }

    /// Produce a snapshot from the current loop state.
    ///
    /// `outcomes`        — all `CycleOutcome`s from the current run (may be empty).
    /// `watchdog`        — optional watchdog reference for stall/supply data.
    /// `active_executors`/ `queue_depth` — supply health inputs.
    pub fn snapshot(
        &self,
        planner: &PlannerModel,
        outcomes: &[CycleOutcome],
        watchdog: Option<&LoopWatchdog>,
        active_executors: usize,
        queue_depth: usize,
    ) -> DashboardSnapshot {
        let pcs = planner.pcs();
        let is_well_calibrated = pcs.map(|p| p > 0.80).unwrap_or(false);

        let total_cycles = outcomes.len() as u64;
        let human_confirmations = outcomes.iter().filter(|o| !o.autonomous).count() as u64;
        let ar = autonomy_rate(outcomes);
        let imp_count = improvement_count(outcomes) as u64;
        let last_delta = outcomes.last().map(|o| o.product_delta).unwrap_or(0.0);

        let stall_count = watchdog.map(|w| w.stall_count()).unwrap_or(0);

        let supply_health_ratio = if queue_depth == 0 {
            0.0
        } else {
            active_executors as f64 / queue_depth as f64
        };

        DashboardSnapshot {
            product_id: self.product_id.clone(),
            planner_generation: planner.planner_generation(),
            pcs,
            is_well_calibrated,
            autonomy_rate: ar,
            human_confirmations,
            total_cycles,
            improvement_count: imp_count,
            last_product_delta: last_delta,
            stall_count,
            supply_health_ratio,
            snapshot_at: now_iso(),
        }
    }

    /// Serialise the snapshot to a compact JSON string.
    pub fn to_json(&self, snapshot: &DashboardSnapshot) -> String {
        serde_json::to_string(snapshot).unwrap_or_else(|e| format!("{{\"error\":\"{e}\"}}"))
    }

    /// Print a human-readable one-pager to stdout.
    pub fn print_summary(&self, snapshot: &DashboardSnapshot) {
        let pcs_str = snapshot
            .pcs
            .map(|p| format!("{:.4}", p))
            .unwrap_or_else(|| "n/a (< window)".into());
        let calibrated = if snapshot.is_well_calibrated {
            "YES (> 0.80)"
        } else {
            "NO"
        };
        println!("┌─── URACE Dashboard: {} ───", snapshot.product_id);
        println!("│  Snapshot at         : {}", snapshot.snapshot_at);
        println!("│  Planner generation  : {}", snapshot.planner_generation);
        println!("│  PCS                 : {pcs_str}");
        println!("│  Well calibrated     : {calibrated}");
        println!(
            "│  Autonomy rate       : {:.1}%  ({}/{} autonomous)",
            snapshot.autonomy_rate * 100.0,
            snapshot.total_cycles.saturating_sub(snapshot.human_confirmations),
            snapshot.total_cycles
        );
        println!(
            "│  Human confirmations : {}",
            snapshot.human_confirmations
        );
        println!("│  Improvements        : {}/{}", snapshot.improvement_count, snapshot.total_cycles);
        println!("│  Last product delta  : {:.6}", snapshot.last_product_delta);
        println!("│  Stall count         : {}", snapshot.stall_count);
        println!(
            "│  Supply health ratio : {:.2}",
            snapshot.supply_health_ratio
        );
        println!("└──────────────────────────────────────────────────");
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

// ── Tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use crate::watchdog::LoopWatchdog;
    use tempfile::NamedTempFile;
    use urace_goals::planner_model::PlannerModel;

    fn fresh_planner() -> (PlannerModel, NamedTempFile) {
        let f = NamedTempFile::new().unwrap();
        let p = PlannerModel::open(f.path(), [0u8; 32]).unwrap();
        (p, f)
    }

    fn outcome(cycle: u64, delta: f64, autonomous: bool, improved: bool) -> CycleOutcome {
        CycleOutcome {
            cycle_number: cycle,
            task_type: "lint_fix".into(),
            approved: true,
            prior_metric: 0.8,
            current_metric: 0.8 + delta,
            product_delta: delta,
            is_improvement: improved,
            autonomous,
            recorded_at: "0".into(),
        }
    }

    #[test]
    fn empty_outcomes_snapshot() {
        let (planner, _f) = fresh_planner();
        let dash = MetricsDashboard::new("prod-1");
        let snap = dash.snapshot(&planner, &[], None, 0, 0);
        assert_eq!(snap.total_cycles, 0);
        assert_eq!(snap.human_confirmations, 0);
        assert!((snap.autonomy_rate).abs() < 1e-9);
        assert_eq!(snap.improvement_count, 0);
        assert!((snap.last_product_delta).abs() < 1e-9);
        assert_eq!(snap.stall_count, 0);
        assert!((snap.supply_health_ratio).abs() < 1e-9);
        assert!(snap.pcs.is_none());
        assert!(!snap.is_well_calibrated);
    }

    #[test]
    fn human_confirmations_counted_correctly() {
        let (planner, _f) = fresh_planner();
        let dash = MetricsDashboard::new("prod-2");
        let outcomes = vec![
            outcome(1, 0.01, true, true),
            outcome(2, -0.001, false, false), // human
            outcome(3, 0.005, true, true),
            outcome(4, 0.002, false, true), // human
        ];
        let snap = dash.snapshot(&planner, &outcomes, None, 4, 2);
        assert_eq!(snap.total_cycles, 4);
        assert_eq!(snap.human_confirmations, 2);
        assert!((snap.autonomy_rate - 0.5).abs() < 1e-9);
        assert_eq!(snap.improvement_count, 3);
        assert!((snap.last_product_delta - 0.002).abs() < 1e-9);
    }

    #[test]
    fn supply_health_ratio_zero_when_no_queue() {
        let (planner, _f) = fresh_planner();
        let dash = MetricsDashboard::new("prod-3");
        let snap = dash.snapshot(&planner, &[], None, 10, 0);
        assert!((snap.supply_health_ratio).abs() < 1e-9);
    }

    #[test]
    fn supply_health_ratio_computed_when_queue_nonzero() {
        let (planner, _f) = fresh_planner();
        let dash = MetricsDashboard::new("prod-4");
        let snap = dash.snapshot(&planner, &[], None, 6, 3);
        assert!((snap.supply_health_ratio - 2.0).abs() < 1e-9);
    }

    #[test]
    fn watchdog_stall_count_propagated() {
        let (planner, _f) = fresh_planner();
        let wd = LoopWatchdog::new(0); // threshold 0 → always stalls
        std::thread::sleep(std::time::Duration::from_millis(5));
        wd.check_stall();
        wd.check_stall();
        let dash = MetricsDashboard::new("prod-5");
        let snap = dash.snapshot(&planner, &[], Some(&wd), 1, 5);
        assert_eq!(snap.stall_count, 2);
    }

    #[test]
    fn to_json_round_trips() {
        let (planner, _f) = fresh_planner();
        let dash = MetricsDashboard::new("prod-6");
        let snap = dash.snapshot(&planner, &[], None, 0, 0);
        let json_str = dash.to_json(&snap);
        let round: DashboardSnapshot = serde_json::from_str(&json_str).unwrap();
        assert_eq!(round.product_id, "prod-6");
    }
}
