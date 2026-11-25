//! Work implementation sequencing: dependency resolution, DAG ordering, executor routing.
//!
//! Local controller actions route to `LOCAL_CONTROLLER`; all others are `EXECUTOR_CANDIDATE`.
//! Never dispatch speculative work — recheck authority and acceptance before each dispatch.

use serde::{Deserialize, Serialize};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::collections::{HashMap, HashSet};
use thiserror::Error;

pub const SCHEMA: &str = "implementation-sequence-v1";

static LOCAL_ACTIONS: &[&str] = &[
    "plan_sequence",
    "draft_milestones",
    "rank_peers",
    "status",
    "assessment_index",
    "reconcile_receipts",
    "refresh_metadata",
];

static DONE_STATUSES: &[&str] = &["completed", "achieved", "superseded", "cancelled"];
static SKIP_STATUSES: &[&str] = &[
    "blocked",
    "policy_blocked",
    "disabled",
    "awaiting_operator_decision",
    "deferred",
];

// ── Errors ────────────────────────────────────────────────────────────────────

/// Errors from sequencing operations.
#[derive(Debug, Error)]
pub enum SequenceError {
    #[error("bounded implementation task list required (max 2000)")]
    TooManyTasks,

    #[error("unique task identity required; duplicate or missing id")]
    DuplicateTaskId,

    #[error("task dependencies must be string identifiers")]
    InvalidDependencies,

    #[error("serialization error: {0}")]
    Serialization(#[from] serde_json::Error),
}

// ── Types ─────────────────────────────────────────────────────────────────────

/// A single implementation task submitted for sequencing.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Task {
    pub id: String,
    #[serde(default)]
    pub status: String,
    #[serde(default)]
    pub dependencies: Vec<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub execution_kind: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub controller_action: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub priority: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub uncertainty_reduction: Option<bool>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub bottleneck_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub expected_benefit: Option<Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub expected_benefit_score: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub benefit_score_verified: Option<bool>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub action_recommendation: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub title: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub estimate: Option<Estimate>,
}

/// Cost estimate for a task.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Estimate {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub max_hours: Option<f64>,
}

/// Execution route for a sequenced task.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum Route {
    LocalController,
    ExecutorCandidate,
}

/// Readiness status of a sequenced task.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum TaskStatus {
    Ready,
    PlannedAfterPredecessors,
    Blocked,
}

/// A single row in the sequenced plan output.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SequencedTask {
    pub id: String,
    pub rank: Option<usize>,
    pub phase: Option<usize>,
    pub status: TaskStatus,
    pub route: Route,
    pub dependencies: Vec<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub bottleneck: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub expected_benefit: Option<Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub expected_benefit_score: Option<f64>,
    pub benefit_score_verified: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub action_recommendation: Option<String>,
    pub why: Vec<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub estimated_cost: Option<Estimate>,
    pub authority: String,
}

/// Full plan result from `plan`.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SequencePlan {
    pub schema: String,
    pub source_sha256: String,
    pub tasks: Vec<SequencedTask>,
    pub dependency_phases: Vec<Vec<String>>,
    pub dispatch_order: Vec<String>,
    pub native_model_calls: u32,
    pub absolute_optimum_proven: bool,
    pub uncertainty: String,
}

// ── Helpers ───────────────────────────────────────────────────────────────────

fn is_local_only(task: &Task) -> bool {
    task.execution_kind.as_deref() == Some("local_orchestration")
        || task
            .controller_action
            .as_deref()
            .map(|a| LOCAL_ACTIONS.contains(&a))
            .unwrap_or(false)
}

fn is_done(status: &str) -> bool {
    DONE_STATUSES.contains(&status.to_ascii_lowercase().as_str())
}

fn is_skip(status: &str) -> bool {
    SKIP_STATUSES.contains(&status.to_ascii_lowercase().as_str())
}

fn is_finite(v: f64) -> bool {
    v.is_finite()
}

fn tasks_digest(tasks: &[Task]) -> Result<String, SequenceError> {
    let val = serde_json::to_value(tasks).map_err(SequenceError::Serialization)?;
    let canonical = serde_json::to_string(&val).map_err(SequenceError::Serialization)?;
    let hash = Sha256::digest(canonical.as_bytes());
    Ok(hex::encode(hash))
}

// ── Core plan algorithm ───────────────────────────────────────────────────────

/// Compute a dependency-respecting execution sequence for `tasks`.
///
/// `scores` overrides per-task priority; `eligible` gates `READY` status.
pub fn plan(
    tasks: Vec<Task>,
    scores: Option<&HashMap<String, f64>>,
    eligible: Option<&HashMap<String, bool>>,
) -> Result<SequencePlan, SequenceError> {
    if tasks.len() > 2000 {
        return Err(SequenceError::TooManyTasks);
    }

    // Build index; validate uniqueness and dependency types.
    let mut by_id: HashMap<String, Task> = HashMap::new();
    let mut positions: HashMap<String, usize> = HashMap::new();
    for (i, task) in tasks.iter().enumerate() {
        if task.id.is_empty() || by_id.contains_key(&task.id) {
            return Err(SequenceError::DuplicateTaskId);
        }
        for dep in &task.dependencies {
            if dep.is_empty() {
                return Err(SequenceError::InvalidDependencies);
            }
        }
        positions.insert(task.id.clone(), i);
        by_id.insert(task.id.clone(), task.clone());
    }

    let source_sha256 = tasks_digest(&tasks)?;

    let empty_scores = HashMap::new();
    let scores = scores.unwrap_or(&empty_scores);

    // Active tasks (not done).
    let active: HashMap<String, &Task> = by_id
        .iter()
        .filter(|(_, t)| !is_done(&t.status))
        .map(|(k, v)| (k.clone(), v))
        .collect();

    let mut pending: HashSet<String> = active.keys().cloned().collect();
    let mut resolved: HashSet<String> = by_id
        .iter()
        .filter(|(_, t)| {
            matches!(
                t.status.to_ascii_lowercase().as_str(),
                "completed" | "achieved" | "superseded"
            )
        })
        .map(|(k, _)| k.clone())
        .collect();

    // Pre-compute unknown-dependency blocks.
    let blocked_reasons: HashMap<String, Vec<String>> = active
        .iter()
        .map(|(k, t)| {
            let unknown: Vec<String> = t
                .dependencies
                .iter()
                .filter(|d| !by_id.contains_key(d.as_str()))
                .map(|d| format!("Unknown dependency {d}"))
                .collect();
            (k.clone(), unknown)
        })
        .collect();

    let ordering = |k: &str| -> (i64, bool, bool, bool, f64, usize) {
        let task = &active[k];
        let raw_score = scores.get(k).copied().or(task.priority).unwrap_or(50.0);
        let s = if is_finite(raw_score) { raw_score } else { 0.0 };
        let cost = task
            .estimate
            .as_ref()
            .and_then(|e| e.max_hours)
            .filter(|&c| is_finite(c) && c > 0.0);
        let cost_known = cost.is_some();
        (
            -(s as i64),
            !task.uncertainty_reduction.unwrap_or(false),
            !is_local_only(task),
            !cost_known,
            cost.unwrap_or(f64::INFINITY),
            *positions.get(k).unwrap_or(&usize::MAX),
        )
    };

    let mut rows: Vec<SequencedTask> = Vec::new();
    let mut groups: Vec<Vec<String>> = Vec::new();
    let mut rank_counter = 0usize;

    while !pending.is_empty() {
        let mut ready: Vec<String> = pending
            .iter()
            .filter(|k| {
                let t = &active[*k];
                let no_unknown_blocks = blocked_reasons[*k].is_empty();
                let all_deps_resolved = t.dependencies.iter().all(|d| resolved.contains(d));
                let not_skip = !is_skip(&t.status);
                no_unknown_blocks && all_deps_resolved && not_skip
            })
            .cloned()
            .collect();

        if ready.is_empty() {
            break;
        }

        ready.sort_by(|a, b| {
            ordering(a)
                .partial_cmp(&ordering(b))
                .unwrap_or(std::cmp::Ordering::Equal)
        });
        groups.push(ready.clone());

        for key in &ready {
            let task = &active[key];
            rank_counter += 1;

            let is_eligible = eligible
                .map(|e| e.get(key).copied().unwrap_or(false))
                .unwrap_or_else(|| task.dependencies.is_empty());

            let route = if is_local_only(task) {
                Route::LocalController
            } else {
                Route::ExecutorCandidate
            };

            let cost = task.estimate.as_ref().and_then(|e| e.max_hours);
            let cost_known = cost.map(|c| is_finite(c) && c > 0.0).unwrap_or(false);

            let mut why = vec![
                "Dependency predecessors precede this task".into(),
                "Owner priority/score retained before resource tie-breaks".into(),
            ];
            if is_local_only(task) {
                why.push(
                    "Orchestration belongs to a deterministic local handler; no executor token spend"
                        .into(),
                );
            }
            if task.uncertainty_reduction.unwrap_or(false) {
                why.push(
                    "At equal priority, resolves uncertainty before more expensive implementation"
                        .into(),
                );
            }
            if !cost_known {
                why.push("Cost unknown; not treated as free".into());
            }

            rows.push(SequencedTask {
                id: key.clone(),
                rank: Some(rank_counter),
                phase: Some(groups.len()),
                status: if is_eligible {
                    TaskStatus::Ready
                } else {
                    TaskStatus::PlannedAfterPredecessors
                },
                route,
                dependencies: task.dependencies.clone(),
                bottleneck: task.bottleneck_id.clone(),
                expected_benefit: task.expected_benefit.clone(),
                expected_benefit_score: task.expected_benefit_score,
                benefit_score_verified: task.benefit_score_verified.unwrap_or(false),
                action_recommendation: task
                    .action_recommendation
                    .clone()
                    .or_else(|| task.title.clone()),
                why,
                estimated_cost: task.estimate.clone(),
                authority: "Recheck existing authority and acceptance before dispatch".into(),
            });

            pending.remove(key);
            resolved.insert(key.clone());
        }
    }

    // Remaining pending tasks are blocked or cyclic.
    let mut blocked_keys: Vec<String> = pending.iter().cloned().collect();
    blocked_keys.sort();
    for key in blocked_keys {
        let task = &active[&key];
        let reasons = if !blocked_reasons[&key].is_empty() {
            blocked_reasons[&key].clone()
        } else {
            vec![
                "Blocked/cyclic or unresolved predecessor chain; explicit owner/action review required"
                    .into(),
            ]
        };
        rows.push(SequencedTask {
            id: key.clone(),
            rank: None,
            phase: None,
            status: TaskStatus::Blocked,
            route: if is_local_only(task) {
                Route::LocalController
            } else {
                Route::ExecutorCandidate
            },
            dependencies: task.dependencies.clone(),
            bottleneck: task.bottleneck_id.clone(),
            expected_benefit: None,
            expected_benefit_score: None,
            benefit_score_verified: false,
            action_recommendation: Some(
                "Resolve the dependency or authority blocker; do not dispatch speculative work"
                    .into(),
            ),
            why: reasons,
            estimated_cost: task.estimate.clone(),
            authority: "Recheck existing authority and acceptance before dispatch".into(),
        });
    }

    let dispatch_order: Vec<String> = rows
        .iter()
        .filter(|r| r.rank.is_some())
        .filter(|r| {
            eligible
                .map(|e| e.get(&r.id).copied().unwrap_or(false))
                .unwrap_or(true)
        })
        .map(|r| r.id.clone())
        .collect();

    Ok(SequencePlan {
        schema: SCHEMA.into(),
        source_sha256,
        tasks: rows,
        dependency_phases: groups,
        dispatch_order,
        native_model_calls: 0,
        absolute_optimum_proven: false,
        uncertainty: "Scores and cost estimates are provisional. Independent outcomes and \
            calibrated owner utility are needed to compare alternative sequences. Dependency \
            phases do not promise safe parallel writes or available executor capacity."
            .into(),
    })
}

// ── Tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    fn task(id: &str, deps: &[&str]) -> Task {
        Task {
            id: id.into(),
            status: "planned".into(),
            dependencies: deps.iter().map(|s| s.to_string()).collect(),
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

    #[test]
    fn linear_chain_ordered_correctly() {
        let tasks = vec![task("c", &["b"]), task("b", &["a"]), task("a", &[])];
        let plan = plan(tasks, None, None).unwrap();
        let ids: Vec<&str> = plan
            .tasks
            .iter()
            .filter_map(|t| {
                if t.rank.is_some() {
                    Some(t.id.as_str())
                } else {
                    None
                }
            })
            .collect();
        assert_eq!(ids, vec!["a", "b", "c"]);
    }

    #[test]
    fn independent_tasks_land_in_same_phase() {
        let tasks = vec![task("x", &[]), task("y", &[]), task("z", &[])];
        let plan = plan(tasks, None, None).unwrap();
        // All three have no deps so they appear in phase 1 together.
        assert_eq!(plan.dependency_phases.len(), 1);
        assert_eq!(plan.dependency_phases[0].len(), 3);
    }

    #[test]
    fn unknown_dependency_marks_task_blocked() {
        let tasks = vec![task("a", &["missing"])];
        let plan = plan(tasks, None, None).unwrap();
        assert_eq!(plan.tasks[0].status, TaskStatus::Blocked);
    }

    #[test]
    fn too_many_tasks_returns_error() {
        let tasks: Vec<Task> = (0..2001).map(|i| task(&i.to_string(), &[])).collect();
        assert!(matches!(
            plan(tasks, None, None),
            Err(SequenceError::TooManyTasks)
        ));
    }

    #[test]
    fn local_controller_action_routes_locally() {
        let mut t = task("seq", &[]);
        t.controller_action = Some("plan_sequence".into());
        let plan = plan(vec![t], None, None).unwrap();
        assert_eq!(plan.tasks[0].route, Route::LocalController);
    }
}
