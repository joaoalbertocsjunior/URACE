//! Work market: post tasks, submit bids, and select winners.
//!
//! Thread-safe via `DashMap` for tasks/bids and the `DemandCounter`'s
//! internal `Mutex`. All operations check the active `WorkPolicy` before
//! mutating state.
//!
//! M18: `PriceAttestation` provides cryptographic binding of (task_id, amount, attester).

use crate::matching::{select_best_bid, DemandCounter, WorkBid, WorkTask};
use crate::work_policy::{PolicyViolation, WorkPolicy};
use sha2::{Digest, Sha256};
use dashmap::DashMap;
use thiserror::Error;
use tracing::{debug, warn};

#[derive(Debug, Error)]
pub enum WorkError {
    #[error("policy violation: {0}")]
    PolicyViolation(#[from] PolicyViolation),

    #[error("task not found: {task_id}")]
    TaskNotFound { task_id: String },

    #[error("no bids available for task: {task_id}")]
    NoBids { task_id: String },

    #[error("journal error: {0}")]
    Journal(#[from] urace_ledger::JournalError),
}

// ── M18 — Price attestation ───────────────────────────────────────────────────

/// A price attestation: cryptographic binding of (task_id, amount_ucr, attester_peer_id).
///
/// The `attestation_hash` is SHA-256 of `task_id || amount_ucr_le_bytes || attester_peer_id`.
/// This prevents post-hoc price manipulation.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct PriceAttestation {
    pub task_id: String,
    pub amount_ucr: i64,
    pub attester_peer_id: String,
    pub attestation_hash: String,
}

impl PriceAttestation {
    pub fn new(
        task_id: impl Into<String>,
        amount_ucr: i64,
        attester_peer_id: impl Into<String>,
    ) -> Self {
        let task_id = task_id.into();
        let attester = attester_peer_id.into();
        let hash = Self::compute_hash(&task_id, amount_ucr, &attester);
        PriceAttestation { task_id, amount_ucr, attester_peer_id: attester, attestation_hash: hash }
    }

    pub fn compute_hash(task_id: &str, amount_ucr: i64, attester_peer_id: &str) -> String {
        let mut h = Sha256::new();
        h.update(task_id.as_bytes());
        h.update(&amount_ucr.to_le_bytes());
        h.update(attester_peer_id.as_bytes());
        hex::encode(h.finalize())
    }

    pub fn verify(&self) -> bool {
        let expected = Self::compute_hash(&self.task_id, self.amount_ucr, &self.attester_peer_id);
        self.attestation_hash == expected
    }
}

/// The work market: a concurrent registry of tasks and bids.
pub struct WorkMarket {
    policy: WorkPolicy,
    pending_tasks: DashMap<String, WorkTask>,
    active_bids: DashMap<String, Vec<WorkBid>>,
    demand: DemandCounter,
    /// Count of currently active (accepted) jobs — checked against policy.
    active_job_count: std::sync::atomic::AtomicUsize,
}

impl WorkMarket {
    pub fn new(policy: WorkPolicy) -> Self {
        WorkMarket {
            policy,
            pending_tasks: DashMap::new(),
            active_bids: DashMap::new(),
            demand: DemandCounter::new(),
            active_job_count: std::sync::atomic::AtomicUsize::new(0),
        }
    }

    /// Post a task to the market.
    ///
    /// Checks policy before accepting. `authority_checked` must be `true`
    /// when the §62z gate has already been passed.
    pub fn post_task(&self, task: WorkTask, authority_checked: bool) -> Result<(), WorkError> {
        let active = self
            .active_job_count
            .load(std::sync::atomic::Ordering::SeqCst);
        self.policy.check(
            task.budget_ucr,
            &task.task_id, // scope is task_id for now; callers may supply a scope field
            authority_checked,
            active,
        )?;

        debug!(task_id = %task.task_id, "task posted to work market");
        self.demand.record_demand(&task.task_id);
        self.pending_tasks.insert(task.task_id.clone(), task);
        Ok(())
    }

    /// Submit a bid for a task.
    pub fn submit_bid(&self, bid: WorkBid) -> Result<(), WorkError> {
        // Task must exist.
        if !self.pending_tasks.contains_key(&bid.task_id) {
            return Err(WorkError::TaskNotFound {
                task_id: bid.task_id.clone(),
            });
        }
        debug!(bid_id = %bid.bid_id, task_id = %bid.task_id, "bid submitted");
        self.active_bids
            .entry(bid.task_id.clone())
            .or_default()
            .push(bid);
        Ok(())
    }

    /// Select the winning bid for `task_id`.
    ///
    /// Removes the task and its bids from the market on success.
    /// Increments the active job counter.
    pub fn select_winner(&self, task_id: &str) -> Result<WorkBid, WorkError> {
        let task = self
            .pending_tasks
            .get(task_id)
            .ok_or_else(|| WorkError::TaskNotFound {
                task_id: task_id.to_owned(),
            })?
            .clone();

        let bids_ref = self.active_bids.get(task_id);
        let bids: Vec<WorkBid> = match &bids_ref {
            Some(b) => b.value().clone(),
            None => vec![],
        };

        let winner = select_best_bid(&task, &bids, &self.demand)
            .cloned()
            .ok_or_else(|| WorkError::NoBids {
                task_id: task_id.to_owned(),
            })?;

        // Clean up market state.
        drop(bids_ref);
        self.pending_tasks.remove(task_id);
        self.active_bids.remove(task_id);
        self.active_job_count
            .fetch_add(1, std::sync::atomic::Ordering::SeqCst);

        debug!(
            winner_bid = %winner.bid_id,
            executor = %winner.executor_peer_id,
            task_id,
            "winner selected"
        );
        Ok(winner)
    }

    /// Mark a job as completed, decrementing the active job counter.
    pub fn complete_job(&self) {
        let prev = self
            .active_job_count
            .fetch_update(
                std::sync::atomic::Ordering::SeqCst,
                std::sync::atomic::Ordering::SeqCst,
                |n| Some(n.saturating_sub(1)),
            )
            .unwrap_or(0);
        if prev == 0 {
            warn!("complete_job called with no active jobs tracked");
        }
    }

    /// Return all tasks currently listed in the pending market (open for bidding).
    pub fn list_active(&self) -> Vec<WorkTask> {
        self.pending_tasks
            .iter()
            .map(|entry| entry.value().clone())
            .collect()
    }

    pub fn pending_task_count(&self) -> usize {
        self.pending_tasks.len()
    }

    pub fn active_bid_count(&self, task_id: &str) -> usize {
        self.active_bids.get(task_id).map(|b| b.len()).unwrap_or(0)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::work_policy::WorkPolicy;

    fn open_policy() -> WorkPolicy {
        WorkPolicy {
            max_budget_ucr: 1_000_000,
            allowed_scopes: vec![],
            require_authority_check: false,
            max_concurrent_jobs: 10,
        }
    }

    fn task(id: &str) -> WorkTask {
        WorkTask {
            task_id: id.to_owned(),
            required_capabilities: vec!["rust".to_owned()],
            budget_ucr: 500,
            posted_at: "2026-01-01T00:00:00Z".to_owned(),
            poster_peer_id: "poster".to_owned(),
        }
    }

    fn bid(id: &str, task_id: &str) -> WorkBid {
        WorkBid {
            bid_id: id.to_owned(),
            executor_peer_id: "exec".to_owned(),
            task_id: task_id.to_owned(),
            bid_price_ucr: 400,
            capabilities: vec!["rust".to_owned()],
            submitted_at: "2026-01-01T00:01:00Z".to_owned(),
        }
    }

    #[test]
    fn post_and_select_winner() {
        let market = WorkMarket::new(open_policy());
        market.post_task(task("t1"), false).unwrap();
        market.submit_bid(bid("b1", "t1")).unwrap();
        market.submit_bid(bid("b2", "t1")).unwrap();

        let winner = market.select_winner("t1").unwrap();
        assert_eq!(winner.task_id, "t1");
        // Task should be removed from pending.
        assert_eq!(market.pending_task_count(), 0);
    }

    #[test]
    fn policy_budget_exceeded_rejects_task() {
        let market = WorkMarket::new(WorkPolicy::default()); // max_budget=0
        let result = market.post_task(task("t1"), true);
        assert!(matches!(result, Err(WorkError::PolicyViolation(_))));
    }

    #[test]
    fn no_bids_returns_error() {
        let market = WorkMarket::new(open_policy());
        market.post_task(task("t1"), false).unwrap();
        assert!(matches!(
            market.select_winner("t1"),
            Err(WorkError::NoBids { .. })
        ));
    }

    #[test]
    fn bid_on_unknown_task_fails() {
        let market = WorkMarket::new(open_policy());
        assert!(matches!(
            market.submit_bid(bid("b1", "ghost")),
            Err(WorkError::TaskNotFound { .. })
        ));
    }

    #[test]
    fn list_active_returns_pending_tasks() {
        let market = WorkMarket::new(open_policy());
        assert!(market.list_active().is_empty(), "empty market must return empty list");

        market.post_task(task("t1"), false).unwrap();
        market.post_task(task("t2"), false).unwrap();

        let active = market.list_active();
        assert_eq!(active.len(), 2);
        let ids: std::collections::HashSet<&str> =
            active.iter().map(|t| t.task_id.as_str()).collect();
        assert!(ids.contains("t1"));
        assert!(ids.contains("t2"));
    }

    #[test]
    fn list_active_excludes_won_tasks() {
        let market = WorkMarket::new(open_policy());
        market.post_task(task("t1"), false).unwrap();
        market.submit_bid(bid("b1", "t1")).unwrap();
        market.select_winner("t1").unwrap();

        // After winner selected, t1 is removed from pending.
        assert!(market.list_active().is_empty());
    }

    // ── M18 price attestation tests ───────────────────────────────────────────

    #[test]
    fn attestation_hash_valid() {
        let att = PriceAttestation::new("task-42", 500_000, "peer-alice");
        assert!(att.verify(), "freshly created attestation must verify");
    }

    #[test]
    fn tampered_attestation_rejected() {
        let mut att = PriceAttestation::new("task-42", 500_000, "peer-alice");
        att.amount_ucr = 999_999; // tamper with amount
        assert!(!att.verify(), "tampered attestation must not verify");
    }
}
