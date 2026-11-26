//! Work policy: defines constraints for accepting work tasks and bids.
//!
//! Conservative defaults require authority checks and limit budget to 0
//! (must be explicitly raised by operator configuration).

use serde::{Deserialize, Serialize};
use thiserror::Error;

/// Violation of a configured work policy.
#[derive(Debug, Error)]
pub enum PolicyViolation {
    #[error("budget {budget} exceeds max_budget_ucr {max_budget}")]
    BudgetExceeded { budget: i64, max_budget: i64 },

    #[error("scope {scope:?} is not in the allowed scopes list")]
    ScopeNotAllowed { scope: String },

    #[error("authority check is required by policy but was skipped")]
    AuthorityCheckRequired,

    #[error("concurrent job count {count} exceeds max_concurrent_jobs {max}")]
    TooManyConcurrentJobs { count: usize, max: usize },
}

// ── M08 — Off-graph participation cost ───────────────────────────────────────

/// Extra cost (in UCR base units) for peers participating in jobs outside
/// their registered capability graph (0.1 UNIT).
pub const OFF_GRAPH_COST_UCR: i64 = 10_000_000;

/// Returns the participation cost for a job attempt.
///
/// Peers within the capability graph (`is_in_graph = true`) pay nothing.
/// Out-of-graph participation incurs `OFF_GRAPH_COST_UCR`.
pub fn participation_cost(is_in_graph: bool) -> i64 {
    if is_in_graph { 0 } else { OFF_GRAPH_COST_UCR }
}

// ── M19 — Market floor constraint ────────────────────────────────────────────

/// Minimum bid amount in UCR base units (0.01 UNIT).
pub const MARKET_FLOOR_UCR: i64 = 1_000_000;

/// Returns `Err` if `amount_ucr` is below the market floor.
pub fn check_market_floor(amount_ucr: i64) -> Result<(), &'static str> {
    if amount_ucr < MARKET_FLOOR_UCR {
        Err("bid below market floor")
    } else {
        Ok(())
    }
}

/// Contract-bound execution policy for the work market.
///
/// Conservative defaults: max_budget=0 (must be raised explicitly),
/// require_authority_check=true, max_concurrent=1.
/// Any deviation from these defaults requires deliberate operator action.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkPolicy {
    /// Maximum allowed budget in UCR base units (0 = reject all unless raised).
    pub max_budget_ucr: i64,

    /// Allowed task scopes. Empty list means all scopes are permitted.
    pub allowed_scopes: Vec<String>,

    /// Whether an authority check (§62z) is mandatory before accepting tasks.
    pub require_authority_check: bool,

    /// Maximum number of concurrently active jobs.
    pub max_concurrent_jobs: usize,
}

impl Default for WorkPolicy {
    fn default() -> Self {
        WorkPolicy {
            max_budget_ucr: 0,
            allowed_scopes: vec![],
            require_authority_check: true,
            max_concurrent_jobs: 1,
        }
    }
}

impl WorkPolicy {
    /// Check whether a proposed task with `budget_ucr` and `scope` is permitted.
    ///
    /// `authority_checked` must be `true` when the caller has already passed the
    /// §62z gate; `false` otherwise.
    /// `active_jobs` is the current concurrent job count.
    pub fn check(
        &self,
        budget_ucr: i64,
        scope: &str,
        authority_checked: bool,
        active_jobs: usize,
    ) -> Result<(), PolicyViolation> {
        if budget_ucr > self.max_budget_ucr {
            return Err(PolicyViolation::BudgetExceeded {
                budget: budget_ucr,
                max_budget: self.max_budget_ucr,
            });
        }

        if !self.allowed_scopes.is_empty() && !self.allowed_scopes.iter().any(|s| s == scope) {
            return Err(PolicyViolation::ScopeNotAllowed {
                scope: scope.to_owned(),
            });
        }

        if self.require_authority_check && !authority_checked {
            return Err(PolicyViolation::AuthorityCheckRequired);
        }

        if active_jobs >= self.max_concurrent_jobs {
            return Err(PolicyViolation::TooManyConcurrentJobs {
                count: active_jobs,
                max: self.max_concurrent_jobs,
            });
        }

        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn default_policy_rejects_nonzero_budget() {
        let policy = WorkPolicy::default();
        // Even 1 UCR exceeds the conservative max_budget=0.
        assert!(matches!(
            policy.check(1, "documentation", true, 0),
            Err(PolicyViolation::BudgetExceeded { .. })
        ));
    }

    #[test]
    fn default_policy_requires_authority_check() {
        let policy = WorkPolicy::default();
        assert!(matches!(
            policy.check(0, "documentation", false, 0),
            Err(PolicyViolation::AuthorityCheckRequired)
        ));
    }

    #[test]
    fn relaxed_policy_allows_task() {
        let policy = WorkPolicy {
            max_budget_ucr: 1_000_000,
            allowed_scopes: vec![],
            require_authority_check: false,
            max_concurrent_jobs: 4,
        };
        assert!(policy.check(500_000, "documentation", false, 0).is_ok());
    }

    #[test]
    fn scope_filter_rejects_disallowed_scope() {
        let policy = WorkPolicy {
            max_budget_ucr: 1_000_000,
            allowed_scopes: vec!["documentation".to_owned()],
            require_authority_check: false,
            max_concurrent_jobs: 4,
        };
        assert!(matches!(
            policy.check(100, "code", false, 0),
            Err(PolicyViolation::ScopeNotAllowed { .. })
        ));
        assert!(policy.check(100, "documentation", false, 0).is_ok());
    }

    // M08 tests
    #[test]
    fn in_graph_participation_cost_is_zero() {
        assert_eq!(participation_cost(true), 0);
    }

    #[test]
    fn off_graph_participation_cost_nonzero() {
        assert_eq!(participation_cost(false), OFF_GRAPH_COST_UCR);
    }

    // M19 tests
    #[test]
    fn market_floor_at_minimum_accepted() {
        assert!(check_market_floor(MARKET_FLOOR_UCR).is_ok());
    }

    #[test]
    fn market_floor_below_minimum_rejected() {
        assert!(check_market_floor(MARKET_FLOOR_UCR - 1).is_err());
        assert!(check_market_floor(0).is_err());
    }

    #[test]
    fn concurrency_limit_enforced() {
        let policy = WorkPolicy {
            max_budget_ucr: 1_000_000,
            allowed_scopes: vec![],
            require_authority_check: false,
            max_concurrent_jobs: 2,
        };
        // 2 active = already at limit (>= 2).
        assert!(matches!(
            policy.check(100, "docs", false, 2),
            Err(PolicyViolation::TooManyConcurrentJobs { .. })
        ));
        assert!(policy.check(100, "docs", false, 1).is_ok());
    }
}
