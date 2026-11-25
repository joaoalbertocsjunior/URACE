//! Planner trait and AutoPlanner — dependency-aware task sequencing with
//! interval-gated re-planning.
//!
//! `Planner` is the single extension point for sequencing algorithms.
//! `TopologicalPlanner` wraps the existing `implementation_sequence::plan`.
//! `AutoPlanner` gates re-planning behind a configurable interval so the
//! runtime loop does not recompute on every cycle.

use crate::implementation_sequence::{plan, PlanningContext, SequenceError, SequencePlan, Task};
use parking_lot::Mutex;
use std::sync::Arc;
use std::time::{Duration, Instant};

// ── Trait ─────────────────────────────────────────────────────────────────────

/// A stateless planning algorithm.
pub trait Planner: Send + Sync {
    fn plan(&self, tasks: Vec<Task>, ctx: &PlanningContext) -> Result<SequencePlan, SequenceError>;
    fn name(&self) -> &'static str;
}

// ── Default implementation ────────────────────────────────────────────────────

/// Topological planner — wraps `implementation_sequence::plan`.
pub struct TopologicalPlanner;

impl Planner for TopologicalPlanner {
    fn plan(&self, tasks: Vec<Task>, ctx: &PlanningContext) -> Result<SequencePlan, SequenceError> {
        plan(tasks, ctx.scores.as_ref(), ctx.eligible.as_ref())
    }

    fn name(&self) -> &'static str {
        "topological"
    }
}

// ── Auto-planner ──────────────────────────────────────────────────────────────

/// Wraps a `Planner` with interval-gated re-planning.
///
/// `maybe_plan` returns `None` (skip) when the last plan is still fresh.
/// Returns `Some(result)` when the interval has elapsed or no plan exists yet.
pub struct AutoPlanner {
    planner: Arc<dyn Planner>,
    last: Mutex<Option<(SequencePlan, Instant)>>,
    interval: Duration,
}

impl AutoPlanner {
    pub fn new(replan_interval_secs: u64) -> Self {
        Self::with_planner(Arc::new(TopologicalPlanner), replan_interval_secs)
    }

    pub fn with_planner(planner: Arc<dyn Planner>, replan_interval_secs: u64) -> Self {
        AutoPlanner {
            planner,
            last: Mutex::new(None),
            interval: Duration::from_secs(replan_interval_secs),
        }
    }

    /// Run planning if the interval has elapsed; return `None` to skip this cycle.
    pub fn maybe_plan(
        &self,
        tasks: Vec<Task>,
        ctx: &PlanningContext,
    ) -> Option<Result<SequencePlan, SequenceError>> {
        let mut guard = self.last.lock();
        let stale = guard
            .as_ref()
            .map(|(_, at)| at.elapsed() >= self.interval)
            .unwrap_or(true);

        if !stale {
            return None;
        }

        let result = self.planner.plan(tasks, ctx);
        if let Ok(ref plan) = result {
            *guard = Some((plan.clone(), Instant::now()));
        }
        Some(result)
    }

    /// Return the most recent plan, if any.
    pub fn last_plan(&self) -> Option<SequencePlan> {
        self.last.lock().as_ref().map(|(p, _)| p.clone())
    }

    /// Force the next `maybe_plan` call to replan regardless of interval.
    pub fn invalidate(&self) {
        *self.last.lock() = None;
    }

    pub fn planner_name(&self) -> &'static str {
        self.planner.name()
    }
}

// ── Tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use crate::implementation_sequence::Task;
    fn task(id: &str) -> Task {
        Task {
            id: id.to_owned(),
            status: "pending".to_owned(),
            dependencies: vec![],
            execution_kind: None,
            controller_action: None,
            priority: None,
            uncertainty_reduction: None,
            bottleneck_id: None,
            expected_benefit: None,
            expected_benefit_score: None,
            benefit_score_verified: None,
            action_recommendation: None,
            title: None,
            estimate: None,
        }
    }

    fn ctx() -> PlanningContext {
        PlanningContext {
            scores: None,
            eligible: None,
        }
    }

    #[test]
    fn topological_planner_plans_single_task() {
        let p = TopologicalPlanner;
        let result = p.plan(vec![task("t1")], &ctx());
        assert!(result.is_ok());
        let plan = result.unwrap();
        assert_eq!(plan.tasks.len(), 1);
    }

    #[test]
    fn auto_planner_runs_first_time() {
        let ap = AutoPlanner::new(300);
        let result = ap.maybe_plan(vec![task("t1")], &ctx());
        assert!(result.is_some());
        assert!(result.unwrap().is_ok());
    }

    #[test]
    fn auto_planner_skips_within_interval() {
        let ap = AutoPlanner::new(300);
        ap.maybe_plan(vec![task("t1")], &ctx()); // first run
        let second = ap.maybe_plan(vec![task("t1")], &ctx());
        assert!(second.is_none(), "should skip within interval");
    }

    #[test]
    fn auto_planner_reruns_after_invalidate() {
        let ap = AutoPlanner::new(300);
        ap.maybe_plan(vec![task("t1")], &ctx());
        ap.invalidate();
        let result = ap.maybe_plan(vec![task("t1")], &ctx());
        assert!(result.is_some(), "should replan after invalidate");
    }

    #[test]
    fn auto_planner_zero_interval_always_replans() {
        let ap = AutoPlanner::new(0);
        for _ in 0..3 {
            let r = ap.maybe_plan(vec![task("t1")], &ctx());
            assert!(r.is_some());
        }
    }

    #[test]
    fn last_plan_returns_most_recent() {
        let ap = AutoPlanner::new(300);
        assert!(ap.last_plan().is_none());
        ap.maybe_plan(vec![task("t1")], &ctx());
        assert!(ap.last_plan().is_some());
    }
}
