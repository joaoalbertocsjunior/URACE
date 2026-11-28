//! Goal tracking: lifecycle, storage, and mint signals.
//!
//! INVARIANT: `GoalStore::complete` only sets `should_mint = true` when
//! `score_delta > 0`. Zero or negative deltas never trigger minting
//! (qualified acceptance only — from CLAUDE.md token economics).

use dashmap::DashMap;
use serde::{Deserialize, Serialize};
use serde_json::json;
use thiserror::Error;
use urace_ledger::{Journal, JournalError};

// ── Error ────────────────────────────────────────────────────────────────────

#[derive(Debug, Error)]
pub enum GoalError {
    #[error("goal not found: {goal_id}")]
    NotFound { goal_id: String },

    #[error("goal {goal_id} is not in a terminal state (status={status:?})")]
    InvalidTransition { goal_id: String, status: GoalStatus },

    #[error("journal error: {0}")]
    Journal(#[from] JournalError),

    #[error("serialization error: {0}")]
    Serialization(#[from] serde_json::Error),
}

// ── Types ────────────────────────────────────────────────────────────────────

/// Goal lifecycle status.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum GoalStatus {
    Pending,
    Active,
    Completed,
    Cancelled,
}

/// A tracked goal.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Goal {
    pub goal_id: String,
    pub title: String,
    pub scope: String,
    pub status: GoalStatus,
    pub created_at: String,
    pub completed_at: Option<String>,
    pub score_delta: Option<i64>,
}

/// Returned by `GoalStore::complete` and surfaced by `GoalStore::pending_mint_signals`.
///
/// `should_mint` is `true` only when `score_delta > 0`
/// (qualified acceptance only — no negative or zero deltas trigger mint).
///
/// When `should_mint` is `true`, a `"mint_signal"` entry is written to the journal.
/// Settlement picks up these entries via `GoalStore::pending_mint_signals()`.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MintSignal {
    pub should_mint: bool,
    pub amount: i64,
    pub goal_id: String,
    pub executor_id: String,
    /// Whether settlement has confirmed this mint (updated externally).
    #[serde(default)]
    pub settlement_confirmed: bool,
}

// ── Store ────────────────────────────────────────────────────────────────────

/// Concurrent goal store backed by a DashMap (in-memory) + append-only Journal.
pub struct GoalStore {
    goals: DashMap<String, Goal>,
    journal: Journal,
}

impl GoalStore {
    pub fn open(path: impl AsRef<std::path::Path>, hmac_key: [u8; 32]) -> Result<Self, GoalError> {
        let journal = Journal::open(path, hmac_key)?;
        Ok(GoalStore {
            goals: DashMap::new(),
            journal,
        })
    }

    fn now_iso() -> String {
        use std::time::{SystemTime, UNIX_EPOCH};
        let secs = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs();
        format!("epoch-{secs}")
    }

    /// Create and persist a new goal.
    pub fn create(&self, goal: Goal) -> Result<(), GoalError> {
        let payload = serde_json::to_value(&goal)?;
        self.journal.append("GOAL_CREATED", payload)?;
        self.goals.insert(goal.goal_id.clone(), goal);
        Ok(())
    }

    /// Mark a goal as completed with a `score_delta`.
    ///
    /// Returns a `MintSignal` with `should_mint=true` only if `score_delta > 0`.
    ///
    /// When `should_mint` is true, a `"mint_signal"` entry is also written to the journal
    /// so that settlement can pick it up via `pending_mint_signals()`.
    pub fn complete(&self, goal_id: &str, score_delta: i64) -> Result<MintSignal, GoalError> {
        self.complete_with_executor(goal_id, score_delta, "")
    }

    /// Mark a goal as completed with a `score_delta` and an `executor_id`.
    ///
    /// Identical to `complete` but also records the executor that produced the work.
    /// When `should_mint` is true, a `"mint_signal"` entry is written to the journal.
    pub fn complete_with_executor(
        &self,
        goal_id: &str,
        score_delta: i64,
        executor_id: &str,
    ) -> Result<MintSignal, GoalError> {
        let mut goal = self
            .goals
            .get_mut(goal_id)
            .ok_or_else(|| GoalError::NotFound {
                goal_id: goal_id.to_owned(),
            })?;

        if goal.status == GoalStatus::Completed || goal.status == GoalStatus::Cancelled {
            return Err(GoalError::InvalidTransition {
                goal_id: goal_id.to_owned(),
                status: goal.status.clone(),
            });
        }

        let completed_at = Self::now_iso();
        goal.status = GoalStatus::Completed;
        goal.completed_at = Some(completed_at.clone());
        goal.score_delta = Some(score_delta);

        // INVARIANT: mint only on qualified acceptance (score_delta > 0).
        let should_mint = score_delta > 0;

        self.journal.append(
            "GOAL_COMPLETED",
            json!({
                "goal_id": goal_id,
                "score_delta": score_delta,
                "completed_at": completed_at,
                "mint_triggered": should_mint,
                "executor_id": executor_id,
            }),
        )?;

        // Write a separate mint_signal entry that settlement polls.
        if should_mint {
            self.journal.append(
                "mint_signal",
                json!({
                    "goal_id": goal_id,
                    "amount": score_delta,
                    "executor_id": executor_id,
                    "should_settle": true,
                    "settlement_confirmed": false,
                }),
            )?;
        }

        Ok(MintSignal {
            should_mint,
            amount: if should_mint { score_delta } else { 0 },
            goal_id: goal_id.to_owned(),
            executor_id: executor_id.to_owned(),
            settlement_confirmed: false,
        })
    }

    /// Return all `mint_signal` journal entries where `settlement_confirmed` is false.
    ///
    /// Settlement adapters call this to discover pending mints and initiate EVM/Lightning
    /// transactions. After confirming, the caller writes a `"mint_settlement_confirmed"`
    /// entry (settlement does not mutate existing rows — append-only invariant).
    pub fn pending_mint_signals(&self) -> Result<Vec<MintSignal>, GoalError> {
        // Collect all confirmed goal IDs first.
        let entries = self.journal.verify_integrity()?;
        let mut confirmed: std::collections::HashSet<String> = std::collections::HashSet::new();
        for entry in &entries {
            if entry.kind == "mint_settlement_confirmed" {
                if let Some(goal_id) = entry.payload.get("goal_id").and_then(|v| v.as_str()) {
                    confirmed.insert(goal_id.to_owned());
                }
            }
        }

        let mut signals = Vec::new();
        for entry in &entries {
            if entry.kind != "mint_signal" {
                continue;
            }
            let p = &entry.payload;
            let goal_id = p
                .get("goal_id")
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .to_owned();
            if confirmed.contains(&goal_id) {
                continue;
            }
            let amount = p.get("amount").and_then(|v| v.as_i64()).unwrap_or(0);
            let executor_id = p
                .get("executor_id")
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .to_owned();
            signals.push(MintSignal {
                should_mint: true,
                amount,
                goal_id,
                executor_id,
                settlement_confirmed: false,
            });
        }
        Ok(signals)
    }

    /// Cancel a goal.
    pub fn cancel(&self, goal_id: &str) -> Result<(), GoalError> {
        let mut goal = self
            .goals
            .get_mut(goal_id)
            .ok_or_else(|| GoalError::NotFound {
                goal_id: goal_id.to_owned(),
            })?;

        if goal.status == GoalStatus::Completed || goal.status == GoalStatus::Cancelled {
            return Err(GoalError::InvalidTransition {
                goal_id: goal_id.to_owned(),
                status: goal.status.clone(),
            });
        }

        goal.status = GoalStatus::Cancelled;
        self.journal
            .append("GOAL_CANCELLED", json!({ "goal_id": goal_id }))?;
        Ok(())
    }

    /// Return all goals whose status is `Pending` or `Active`.
    pub fn active_goals(&self) -> Vec<Goal> {
        self.goals
            .iter()
            .filter(|g| matches!(g.status, GoalStatus::Pending | GoalStatus::Active))
            .map(|g| g.clone())
            .collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    const KEY: [u8; 32] = *b"goal-store-key-32bytes-pad------";

    fn goal(id: &str) -> Goal {
        Goal {
            goal_id: id.to_owned(),
            title: format!("Goal {id}"),
            scope: "product".to_owned(),
            status: GoalStatus::Pending,
            created_at: "2026-01-01T00:00:00Z".to_owned(),
            completed_at: None,
            score_delta: None,
        }
    }

    #[test]
    fn positive_score_delta_triggers_mint() {
        let dir = tempdir().unwrap();
        let store = GoalStore::open(dir.path().join("goals.jsonl"), KEY).unwrap();
        store.create(goal("g1")).unwrap();
        let signal = store.complete("g1", 42).unwrap();
        assert!(signal.should_mint);
        assert_eq!(signal.amount, 42);
    }

    #[test]
    fn zero_score_delta_does_not_mint() {
        let dir = tempdir().unwrap();
        let store = GoalStore::open(dir.path().join("goals.jsonl"), KEY).unwrap();
        store.create(goal("g2")).unwrap();
        let signal = store.complete("g2", 0).unwrap();
        assert!(!signal.should_mint);
        assert_eq!(signal.amount, 0);
    }

    #[test]
    fn negative_score_delta_does_not_mint() {
        let dir = tempdir().unwrap();
        let store = GoalStore::open(dir.path().join("goals.jsonl"), KEY).unwrap();
        store.create(goal("g3")).unwrap();
        let signal = store.complete("g3", -10).unwrap();
        assert!(!signal.should_mint);
    }

    #[test]
    fn active_goals_excludes_completed() {
        let dir = tempdir().unwrap();
        let store = GoalStore::open(dir.path().join("goals.jsonl"), KEY).unwrap();
        store.create(goal("g1")).unwrap();
        store.create(goal("g2")).unwrap();
        store.complete("g1", 5).unwrap();

        let active = store.active_goals();
        assert_eq!(active.len(), 1);
        assert_eq!(active[0].goal_id, "g2");
    }

    #[test]
    fn double_complete_is_error() {
        let dir = tempdir().unwrap();
        let store = GoalStore::open(dir.path().join("goals.jsonl"), KEY).unwrap();
        store.create(goal("g1")).unwrap();
        store.complete("g1", 5).unwrap();
        assert!(matches!(
            store.complete("g1", 5),
            Err(GoalError::InvalidTransition { .. })
        ));
    }

    #[test]
    fn cancel_goal() {
        let dir = tempdir().unwrap();
        let store = GoalStore::open(dir.path().join("goals.jsonl"), KEY).unwrap();
        store.create(goal("g1")).unwrap();
        store.cancel("g1").unwrap();
        assert!(store.active_goals().is_empty());
    }
}
