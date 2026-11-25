//! Automatic goal generation from observed system state.
//!
//! Rule-based only — no ML, no inference, no executor calls.
//! Goals are suggestions; existing authority and validation still govern execution.

use crate::goal::{Goal, GoalStatus};
use uuid::Uuid;

/// Engine for generating goals from observed system state metrics.
pub struct AutoGoalEngine;

impl AutoGoalEngine {
    pub fn new() -> Self {
        AutoGoalEngine
    }

    /// Suggest goals based on observed state counters.
    ///
    /// Rules (all rule-based, no ML):
    /// - `failed_syncs > 0`  → "resolve failed source syncs"
    /// - `sources_count == 0` → "configure at least one data source"
    /// - `pending_work > 10`  → "reduce pending work backlog"
    ///
    /// Returns a list of `Pending` goals. The caller is responsible for
    /// deduplicating against existing goals before persisting.
    pub fn suggest_goals(
        &self,
        sources_count: usize,
        failed_syncs: usize,
        pending_work: usize,
    ) -> Vec<Goal> {
        let mut goals = Vec::new();
        let now = now_iso();

        if failed_syncs > 0 {
            goals.push(Goal {
                goal_id: format!("auto-failed-syncs-{}", Uuid::new_v4()),
                title: format!(
                    "Resolve {} failed source sync{}",
                    failed_syncs,
                    if failed_syncs == 1 { "" } else { "s" }
                ),
                scope: "sources".to_owned(),
                status: GoalStatus::Pending,
                created_at: now.clone(),
                completed_at: None,
                score_delta: None,
            });
        }

        if sources_count == 0 {
            goals.push(Goal {
                goal_id: format!("auto-no-sources-{}", Uuid::new_v4()),
                title: "Configure at least one data source".to_owned(),
                scope: "sources".to_owned(),
                status: GoalStatus::Pending,
                created_at: now.clone(),
                completed_at: None,
                score_delta: None,
            });
        }

        if pending_work > 10 {
            goals.push(Goal {
                goal_id: format!("auto-work-backlog-{}", Uuid::new_v4()),
                title: format!(
                    "Reduce pending work backlog ({} tasks queued)",
                    pending_work
                ),
                scope: "work_market".to_owned(),
                status: GoalStatus::Pending,
                created_at: now,
                completed_at: None,
                score_delta: None,
            });
        }

        goals
    }
}

impl Default for AutoGoalEngine {
    fn default() -> Self {
        Self::new()
    }
}

fn now_iso() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    let secs = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs();
    format!("epoch-{secs}")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn no_issues_no_goals() {
        let engine = AutoGoalEngine::new();
        let goals = engine.suggest_goals(2, 0, 0);
        assert!(goals.is_empty());
    }

    #[test]
    fn failed_syncs_generates_goal() {
        let engine = AutoGoalEngine::new();
        let goals = engine.suggest_goals(1, 3, 0);
        assert_eq!(goals.len(), 1);
        assert!(goals[0].title.contains("failed source sync"));
        assert_eq!(goals[0].scope, "sources");
    }

    #[test]
    fn no_sources_generates_goal() {
        let engine = AutoGoalEngine::new();
        let goals = engine.suggest_goals(0, 0, 0);
        assert_eq!(goals.len(), 1);
        assert!(goals[0].title.contains("data source"));
    }

    #[test]
    fn large_pending_work_generates_goal() {
        let engine = AutoGoalEngine::new();
        let goals = engine.suggest_goals(1, 0, 11);
        assert_eq!(goals.len(), 1);
        assert_eq!(goals[0].scope, "work_market");
    }

    #[test]
    fn multiple_issues_multiple_goals() {
        let engine = AutoGoalEngine::new();
        let goals = engine.suggest_goals(0, 2, 15);
        // No sources → 1, failed syncs → 1, large backlog → 1 = 3 total.
        assert_eq!(goals.len(), 3);
    }

    #[test]
    fn all_goals_start_pending() {
        let engine = AutoGoalEngine::new();
        let goals = engine.suggest_goals(0, 1, 11);
        assert!(goals.iter().all(|g| g.status == GoalStatus::Pending));
    }
}
