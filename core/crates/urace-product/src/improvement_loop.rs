//! Product improvement loop — the operational core of URACE's autonomous promise.
//!
//! An `ImprovementLoop` runs cycles: measure → generate task → execute → measure
//! → record delta → update planner. Each cycle either improves the product metric
//! or records a failed attempt. The loop does not require human input per cycle.
//!
//! # Autonomy gate
//! The loop uses a `SessionBudget` from `urace-authority`. Qualifying actions
//! (goal creation, spending) are gated by §62z. Per-task execution is
//! `scope = "implementation"` — standard authority, within the session budget.
//!
//! # Exit conditions
//! - `max_cycles` reached
//! - Goal threshold met (`ProductGoal::threshold_met`)
//! - Session budget exhausted → caller must obtain new authorisation

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use thiserror::Error;
use urace_authority::authority::{resolve_with_budget, Objective, SessionBudget};
use urace_executor::{ExecutionRequest, ExecutorPool, ResourceLimits};
use urace_goals::product_goal::{ProductDeltaRecord, ProductGoal};
use urace_goals::planner_model::PlannerModel;
use urace_ledger::{Journal, JournalError};
use urace_types::AuthorityOutcome;

#[derive(Debug, Error)]
pub enum LoopError {
    #[error("authority denied: {0}")]
    AuthorityDenied(String),
    #[error("session budget exhausted after {0} cycles")]
    BudgetExhausted(u64),
    #[error("executor error: {0}")]
    Executor(String),
    #[error("journal error: {0}")]
    Journal(#[from] JournalError),
    #[error("serialization error: {0}")]
    Serialization(#[from] serde_json::Error),
}

/// A single improvement cycle result.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CycleOutcome {
    pub cycle_number: u64,
    pub task_type: String,
    pub approved: bool,
    pub prior_metric: f64,
    pub current_metric: f64,
    /// Signed delta (positive = improvement).
    pub product_delta: f64,
    pub is_improvement: bool,
    /// Was this cycle autonomous (true) or required human confirmation (false)?
    pub autonomous: bool,
    pub recorded_at: String,
}

/// Configuration for an `ImprovementLoop` run.
pub struct LoopConfig {
    pub max_cycles: u64,
    pub authority_config: HashMap<String, serde_json::Value>,
    pub session_budget: SessionBudget,
}

/// Metric sampler — the loop calls this before and after task execution.
/// In production this would call a source adapter. Here it is a trait
/// so tests can inject a deterministic sampler.
pub trait MetricSampler: Send + Sync {
    /// Return the current value of `goal.metric` for the product at `product_id`.
    fn sample(&self, product_id: &str, metric: &str) -> f64;
}

/// Task generator — produces the code/change to execute for each cycle.
/// Production implementation calls the LLM executor; this trait allows
/// deterministic injection in tests.
pub trait TaskGenerator: Send + Sync {
    /// Return (task_type, code) for the next improvement attempt.
    fn generate(&self, product_id: &str, goal: &ProductGoal, cycle: u64) -> (String, String);
}

/// The improvement loop.
pub struct ImprovementLoop {
    pub product_id: String,
    pub goal: ProductGoal,
    executor_pool: ExecutorPool,
    journal: Journal,
}

impl ImprovementLoop {
    pub fn new(
        product_id: impl Into<String>,
        goal: ProductGoal,
        executor_pool: ExecutorPool,
        journal: Journal,
    ) -> Self {
        ImprovementLoop {
            product_id: product_id.into(),
            goal,
            executor_pool,
            journal,
        }
    }

    /// Run up to `config.max_cycles` improvement cycles.
    ///
    /// Returns the list of cycle outcomes. The loop halts early if:
    /// - the goal threshold is met
    /// - the session budget is exhausted
    /// - an unrecoverable executor error occurs
    pub fn run(
        &self,
        config: &mut LoopConfig,
        sampler: &dyn MetricSampler,
        generator: &dyn TaskGenerator,
        planner: &mut PlannerModel,
    ) -> Result<Vec<CycleOutcome>, LoopError> {
        let mut outcomes = Vec::new();
        let mut cycle = 0u64;

        while cycle < config.max_cycles {
            cycle += 1;

            // Authority gate for this execution cycle (scope = implementation).
            let objective = Objective {
                id: Some(format!("cycle-{cycle}")),
                scope: "implementation".into(),
                title: format!(
                    "autonomous improvement cycle {} for product {}",
                    cycle, self.product_id
                ),
                reason: Some(format!("optimising {}", self.goal.metric)),
                necessity_evidence: None,
                lower_impact_route_sufficient: None,
            };

            let resolution = resolve_with_budget(
                &objective,
                &config.authority_config,
                None,
                &[],
                Some(&mut config.session_budget),
            );

            let autonomous = resolution.outcome == AuthorityOutcome::AutonomouslyAuthorized;
            if !autonomous {
                if resolution.outcome == AuthorityOutcome::Denied {
                    return Err(LoopError::AuthorityDenied(resolution.basis));
                }
                // RequiresAuthoritativeDecision or Unresolved → budget exhausted or watchdog
                return Err(LoopError::BudgetExhausted(cycle - 1));
            }

            // Sample metric before change.
            let prior = sampler.sample(&self.product_id, &self.goal.metric);

            // Generate task.
            let (task_type, code) = generator.generate(&self.product_id, &self.goal, cycle);

            // Execute.
            let exec_result = self.executor_pool.submit(ExecutionRequest {
                executor_id: format!("loop-{cycle}"),
                scope: "implementation".into(),
                code,
                resource_limits: ResourceLimits::default(),
                context_prefix: None,
            });

            let approved = exec_result.map(|r| r.success).unwrap_or(false);

            // Sample metric after change (only meaningful if approved).
            let current = if approved {
                sampler.sample(&self.product_id, &self.goal.metric)
            } else {
                prior
            };

            // Record delta.
            let record = ProductDeltaRecord::new(&self.goal, "loop", &task_type, prior, current);

            // Update planner model.
            if let Err(e) = planner.record_feedback(&task_type, approved) {
                tracing::warn!("planner model update failed: {e}");
            }

            // Write to journal.
            let outcome = CycleOutcome {
                cycle_number: cycle,
                task_type: task_type.clone(),
                approved,
                prior_metric: prior,
                current_metric: current,
                product_delta: record.delta,
                is_improvement: record.is_improvement,
                autonomous,
                recorded_at: now_iso(),
            };
            self.journal.append(
                "improvement_cycle",
                serde_json::to_value(&outcome)?,
            )?;

            let threshold_met = self.goal.threshold_met(current);
            outcomes.push(outcome);

            if threshold_met {
                break;
            }
        }

        Ok(outcomes)
    }
}

/// Compute autonomy rate: fraction of cycles that were autonomous.
pub fn autonomy_rate(outcomes: &[CycleOutcome]) -> f64 {
    if outcomes.is_empty() {
        return 0.0;
    }
    let autonomous = outcomes.iter().filter(|o| o.autonomous).count();
    autonomous as f64 / outcomes.len() as f64
}

/// Count cycles with is_improvement = true.
pub fn improvement_count(outcomes: &[CycleOutcome]) -> usize {
    outcomes.iter().filter(|o| o.is_improvement).count()
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
    use std::sync::atomic::{AtomicU64, Ordering};
    use std::sync::Arc;
    use tempfile::NamedTempFile;
    use urace_goals::product_goal::GoalDirection;

    struct SteppingMetric {
        value: Arc<AtomicU64>,
    }
    impl MetricSampler for SteppingMetric {
        fn sample(&self, _product_id: &str, _metric: &str) -> f64 {
            self.value.load(Ordering::SeqCst) as f64 / 100.0
        }
    }

    struct AlwaysImprovingGenerator {
        value: Arc<AtomicU64>,
    }
    impl TaskGenerator for AlwaysImprovingGenerator {
        fn generate(&self, _pid: &str, _goal: &ProductGoal, _cycle: u64) -> (String, String) {
            // Advance the metric by 1 each cycle.
            self.value.fetch_add(1, Ordering::SeqCst);
            // Simple python that exits 0 (approved)
            ("lint_fix".into(), "print('ok')".into())
        }
    }

    fn make_authority_config() -> HashMap<String, serde_json::Value> {
        let mut m = HashMap::new();
        m.insert(
            "delegated".into(),
            serde_json::json!(["local implementation changes"]),
        );
        m.insert("reserved".into(), serde_json::json!([]));
        m
    }

    #[test]
    fn loop_runs_and_records_improvements() {
        let metric_val = Arc::new(AtomicU64::new(80)); // start at 0.80
        let journal_f = NamedTempFile::new().unwrap();
        let planner_f = NamedTempFile::new().unwrap();

        let goal = ProductGoal::new("test_pass_rate", GoalDirection::Maximize, None, 0.005).unwrap();
        let journal = Journal::open(journal_f.path(), [0u8; 32]).unwrap();
        let pool = ExecutorPool::new(make_authority_config(), vec![]);

        let sampler = SteppingMetric { value: Arc::clone(&metric_val) };
        let generator = AlwaysImprovingGenerator { value: Arc::clone(&metric_val) };

        let mut planner = PlannerModel::open(planner_f.path(), [0u8; 32]).unwrap();
        let lp = ImprovementLoop::new("prod-1", goal, pool, journal);

        let mut config = LoopConfig {
            max_cycles: 5,
            authority_config: make_authority_config(),
            session_budget: SessionBudget::new(1000, "test-session"),
        };

        let outcomes = lp.run(&mut config, &sampler, &generator, &mut planner).unwrap();
        assert_eq!(outcomes.len(), 5);
        // All cycles are autonomous
        assert!(outcomes.iter().all(|o| o.autonomous));
        // Autonomy rate = 1.0
        assert!((autonomy_rate(&outcomes) - 1.0).abs() < 1e-9);
    }
}
