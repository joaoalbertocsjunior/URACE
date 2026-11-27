//! Fast-path qualification gate with §62z chaining-exploit prevention.
//!
//! Small incremental changes (≤ 4 KiB diff) may skip the full benchmark suite
//! and run only the regression guard + targeted tests.  To prevent an executor
//! from splitting large changes across many small diffs to avoid full
//! qualification (the "chaining exploit"), a per-executor `FastPathBudget`
//! tracks consecutive fast-path uses.  Once `FAST_PATH_MAX_CHAIN_DEPTH` is
//! reached the next submission is forced through the full path regardless of
//! diff size.
//!
//! The chain depth automatically resets after `FAST_PATH_CHAIN_RESET_SECS`
//! (24 h) of inactivity, or immediately whenever the executor goes through a
//! full-path submission.
//!
//! # Key invariants
//! - Chain depth ≥ `FAST_PATH_MAX_CHAIN_DEPTH` within the reset window → `Err(ChainDepthExceeded)`.
//! - Diffs larger than `FAST_PATH_MAX_DIFF_BYTES` always produce `FullPath` and reset chain depth.
//! - `FastPathRegistry` is an in-memory, per-executor budget tracker — it is not
//!   persisted; persistence is the caller's responsibility.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use thiserror::Error;

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/// Diffs larger than 4 KiB require full qualification.
pub const FAST_PATH_MAX_DIFF_BYTES: usize = 4_096;

/// An executor may use the fast path at most this many consecutive times.
pub const FAST_PATH_MAX_CHAIN_DEPTH: usize = 5;

/// After this many seconds of inactivity the chain depth resets (24 h).
pub const FAST_PATH_CHAIN_RESET_SECS: u64 = 24 * 3600;

// ---------------------------------------------------------------------------
// QualificationPathKind
// ---------------------------------------------------------------------------

/// Which qualification path was selected for a submission.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum QualificationPathKind {
    /// Regression guard + targeted tests only.
    FastPath,
    /// Complete benchmark suite.
    FullPath,
}

// ---------------------------------------------------------------------------
// FastPathDecision
// ---------------------------------------------------------------------------

/// The outcome of a path-selection decision.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FastPathDecision {
    /// Selected qualification path.
    pub path: QualificationPathKind,
    /// Human-readable explanation.
    pub reason: String,
    /// Chain depth for this executor *after* this decision is applied.
    pub chain_depth: usize,
}

// ---------------------------------------------------------------------------
// FastPathError
// ---------------------------------------------------------------------------

/// Errors returned by the fast-path gate.
#[derive(Debug, Error, PartialEq)]
pub enum FastPathError {
    #[error("chain depth {depth} has reached maximum {max}; full qualification required")]
    ChainDepthExceeded { depth: usize, max: usize },
}

// ---------------------------------------------------------------------------
// FastPathBudget
// ---------------------------------------------------------------------------

/// Per-executor fast-path budget.
#[derive(Debug, Clone)]
pub struct FastPathBudget {
    /// The executor this budget belongs to.
    pub executor_peer_id: String,
    /// Number of consecutive fast-path submissions since last reset.
    pub chain_depth: usize,
    /// Unix timestamp (seconds) of the most recent submission.
    pub last_submission_secs: u64,
}

// ---------------------------------------------------------------------------
// FastPathRegistry
// ---------------------------------------------------------------------------

/// In-memory registry of per-executor fast-path budgets.
#[derive(Debug, Default)]
pub struct FastPathRegistry {
    budgets: HashMap<String, FastPathBudget>,
}

impl FastPathRegistry {
    /// Create a new, empty registry.
    pub fn new() -> Self {
        Self::default()
    }

    /// Decide the qualification path for a submission.
    ///
    /// Steps:
    /// 1. Fetch or create the budget for `executor_peer_id`.
    /// 2. If the reset window has elapsed, reset chain depth to 0.
    /// 3. If chain depth ≥ `FAST_PATH_MAX_CHAIN_DEPTH` (and within the reset
    ///    window) → return `Err(ChainDepthExceeded)`.
    /// 4. If diff > `FAST_PATH_MAX_DIFF_BYTES` → `FullPath`, reset chain depth.
    /// 5. If diff ≤ `FAST_PATH_MAX_DIFF_BYTES` → `FastPath`, increment chain depth.
    /// 6. Update `last_submission_secs`.
    pub fn decide(
        &mut self,
        executor_peer_id: &str,
        diff_size_bytes: usize,
        now_secs: u64,
    ) -> Result<FastPathDecision, FastPathError> {
        // Fetch or initialise budget.
        let budget = self
            .budgets
            .entry(executor_peer_id.to_owned())
            .or_insert_with(|| FastPathBudget {
                executor_peer_id: executor_peer_id.to_owned(),
                chain_depth: 0,
                last_submission_secs: 0,
            });

        // Step 2: reset chain depth if the inactivity window has elapsed.
        let elapsed = now_secs.saturating_sub(budget.last_submission_secs);
        if budget.last_submission_secs > 0 && elapsed > FAST_PATH_CHAIN_RESET_SECS {
            budget.chain_depth = 0;
        }

        // Step 3: reject if chain depth is at or beyond the maximum.
        if budget.chain_depth >= FAST_PATH_MAX_CHAIN_DEPTH {
            return Err(FastPathError::ChainDepthExceeded {
                depth: budget.chain_depth,
                max: FAST_PATH_MAX_CHAIN_DEPTH,
            });
        }

        // Step 4 / 5: select path based on diff size.
        let (path, reason, new_depth) = if diff_size_bytes > FAST_PATH_MAX_DIFF_BYTES {
            (
                QualificationPathKind::FullPath,
                format!(
                    "diff size {} bytes exceeds fast-path limit of {} bytes",
                    diff_size_bytes, FAST_PATH_MAX_DIFF_BYTES
                ),
                0usize, // reset chain depth on full-path submission
            )
        } else {
            let next_depth = budget.chain_depth + 1;
            (
                QualificationPathKind::FastPath,
                format!(
                    "diff size {} bytes is within fast-path limit; chain depth now {}",
                    diff_size_bytes, next_depth
                ),
                next_depth,
            )
        };

        // Step 6: persist updated budget.
        budget.chain_depth = new_depth;
        budget.last_submission_secs = now_secs;

        Ok(FastPathDecision {
            path,
            reason,
            chain_depth: new_depth,
        })
    }

    /// Manually reset the chain depth for an executor (called after a full-path submission).
    pub fn reset_chain(&mut self, executor_peer_id: &str) {
        if let Some(budget) = self.budgets.get_mut(executor_peer_id) {
            budget.chain_depth = 0;
        }
    }

    /// Return the current budget for an executor, if one exists.
    pub fn budget_for(&self, executor_peer_id: &str) -> Option<&FastPathBudget> {
        self.budgets.get(executor_peer_id)
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    const NOW: u64 = 1_000_000;
    const SMALL: usize = 1_024; // below FAST_PATH_MAX_DIFF_BYTES
    const LARGE: usize = FAST_PATH_MAX_DIFF_BYTES + 1;

    // --- happy path ----------------------------------------------------------

    #[test]
    fn small_diff_takes_fast_path() {
        let mut reg = FastPathRegistry::new();
        let dec = reg.decide("exec-1", SMALL, NOW).unwrap();
        assert_eq!(dec.path, QualificationPathKind::FastPath);
        assert_eq!(dec.chain_depth, 1);
    }

    #[test]
    fn large_diff_takes_full_path() {
        let mut reg = FastPathRegistry::new();
        let dec = reg.decide("exec-1", LARGE, NOW).unwrap();
        assert_eq!(dec.path, QualificationPathKind::FullPath);
        assert_eq!(dec.chain_depth, 0);
    }

    #[test]
    fn exact_boundary_diff_takes_fast_path() {
        // exactly FAST_PATH_MAX_DIFF_BYTES → fast path
        let mut reg = FastPathRegistry::new();
        let dec = reg.decide("exec-1", FAST_PATH_MAX_DIFF_BYTES, NOW).unwrap();
        assert_eq!(dec.path, QualificationPathKind::FastPath);
    }

    // --- chain depth tracking ------------------------------------------------

    #[test]
    fn chain_depth_increments_on_fast_path() {
        let mut reg = FastPathRegistry::new();
        for expected_depth in 1..=FAST_PATH_MAX_CHAIN_DEPTH - 1 {
            let dec = reg.decide("exec-2", SMALL, NOW).unwrap();
            assert_eq!(dec.chain_depth, expected_depth);
        }
    }

    #[test]
    fn large_diff_resets_chain_depth() {
        let mut reg = FastPathRegistry::new();
        // Build up some chain depth
        reg.decide("exec-3", SMALL, NOW).unwrap();
        reg.decide("exec-3", SMALL, NOW + 1).unwrap();
        // Now submit a large diff
        let dec = reg.decide("exec-3", LARGE, NOW + 2).unwrap();
        assert_eq!(dec.path, QualificationPathKind::FullPath);
        assert_eq!(dec.chain_depth, 0);
    }

    // --- exploit prevention (chain exhaustion) --------------------------------

    #[test]
    fn chain_depth_exhaustion_returns_error() {
        let mut reg = FastPathRegistry::new();
        // Exhaust the budget
        for i in 0..FAST_PATH_MAX_CHAIN_DEPTH {
            reg.decide("exec-4", SMALL, NOW + i as u64).unwrap();
        }
        // Next call must fail
        let err = reg
            .decide("exec-4", SMALL, NOW + FAST_PATH_MAX_CHAIN_DEPTH as u64)
            .unwrap_err();
        match err {
            FastPathError::ChainDepthExceeded { depth, max } => {
                assert_eq!(depth, FAST_PATH_MAX_CHAIN_DEPTH);
                assert_eq!(max, FAST_PATH_MAX_CHAIN_DEPTH);
            }
        }
    }

    #[test]
    fn chain_resets_after_inactivity_window() {
        let mut reg = FastPathRegistry::new();
        // Exhaust the budget; last submission lands at NOW + (MAX-1).
        for i in 0..FAST_PATH_MAX_CHAIN_DEPTH {
            reg.decide("exec-5", SMALL, NOW + i as u64).unwrap();
        }
        let last = NOW + (FAST_PATH_MAX_CHAIN_DEPTH as u64 - 1);
        // Advance time past the reset window relative to the last submission.
        let future = last + FAST_PATH_CHAIN_RESET_SECS + 1;
        let dec = reg.decide("exec-5", SMALL, future).unwrap();
        assert_eq!(dec.path, QualificationPathKind::FastPath);
        assert_eq!(dec.chain_depth, 1);
    }

    #[test]
    fn manual_reset_chain_clears_depth() {
        let mut reg = FastPathRegistry::new();
        // Build up chain depth
        reg.decide("exec-6", SMALL, NOW).unwrap();
        reg.decide("exec-6", SMALL, NOW + 1).unwrap();
        assert_eq!(reg.budget_for("exec-6").unwrap().chain_depth, 2);
        // Manual reset
        reg.reset_chain("exec-6");
        assert_eq!(reg.budget_for("exec-6").unwrap().chain_depth, 0);
    }

    // --- independent executors -----------------------------------------------

    #[test]
    fn executors_have_independent_budgets() {
        let mut reg = FastPathRegistry::new();
        // Exhaust exec-7's budget
        for i in 0..FAST_PATH_MAX_CHAIN_DEPTH {
            reg.decide("exec-7", SMALL, NOW + i as u64).unwrap();
        }
        // exec-8 should still have a fresh budget
        let dec = reg.decide("exec-8", SMALL, NOW).unwrap();
        assert_eq!(dec.path, QualificationPathKind::FastPath);
        assert_eq!(dec.chain_depth, 1);
    }

    #[test]
    fn budget_for_unknown_executor_is_none() {
        let reg = FastPathRegistry::new();
        assert!(reg.budget_for("nobody").is_none());
    }
}
