//! Resource accounting for trial sessions.
//!
//! Ported from `trial/accounting.py`. Tracks tokens consumed, USD-equivalent
//! cost (expressed in micro-UCR), wall-clock time and CPU time for a single
//! trial session or a group of sessions.

use serde::{Deserialize, Serialize};

// ---------------------------------------------------------------------------
// ResourceAccount
// ---------------------------------------------------------------------------

/// Accumulated resource consumption for one trial session.
#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq, Eq)]
pub struct ResourceAccount {
    /// Total tokens consumed (input + output + cache tokens).
    pub tokens_used: u64,
    /// Cost in micro-UCR (10^-6 UCR base units). Derived from provider rates.
    pub cost_ucr: u64,
    /// Wall-clock elapsed time in milliseconds.
    pub wall_time_ms: u64,
    /// CPU time in milliseconds (best-effort; may equal wall_time_ms when unavailable).
    pub cpu_time_ms: u64,
}

impl ResourceAccount {
    /// Create a zeroed account.
    pub fn new() -> Self {
        Self::default()
    }

    /// Accumulate another account into this one (all fields are summed).
    ///
    /// Uses saturating addition to avoid overflow on adversarial inputs.
    pub fn add(&mut self, other: &ResourceAccount) {
        self.tokens_used = self.tokens_used.saturating_add(other.tokens_used);
        self.cost_ucr = self.cost_ucr.saturating_add(other.cost_ucr);
        self.wall_time_ms = self.wall_time_ms.saturating_add(other.wall_time_ms);
        self.cpu_time_ms = self.cpu_time_ms.saturating_add(other.cpu_time_ms);
    }
}

// ---------------------------------------------------------------------------
// ResourceBudget
// ---------------------------------------------------------------------------

/// Budget limits for a trial session. All fields are maximums.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResourceBudget {
    /// Maximum tokens allowed for this session.
    pub max_tokens: u64,
    /// Maximum cost in micro-UCR allowed for this session.
    pub max_cost_ucr: u64,
    /// Maximum wall-clock time in milliseconds.
    pub max_wall_time_ms: u64,
}

impl ResourceBudget {
    /// Create a budget with explicit limits.
    pub fn new(max_tokens: u64, max_cost_ucr: u64, max_wall_time_ms: u64) -> Self {
        ResourceBudget {
            max_tokens,
            max_cost_ucr,
            max_wall_time_ms,
        }
    }
}

impl Default for ResourceBudget {
    /// Defaults from the Python trial harness: 480 s wall, no token/cost cap.
    fn default() -> Self {
        ResourceBudget {
            max_tokens: u64::MAX,
            max_cost_ucr: u64::MAX,
            max_wall_time_ms: 480_000,
        }
    }
}

// ---------------------------------------------------------------------------
// within_budget
// ---------------------------------------------------------------------------

/// Return `true` when `account` does not exceed any limit in `budget`.
///
/// All three axes are checked independently; a single overrun returns `false`.
pub fn within_budget(account: &ResourceAccount, budget: &ResourceBudget) -> bool {
    account.tokens_used <= budget.max_tokens
        && account.cost_ucr <= budget.max_cost_ucr
        && account.wall_time_ms <= budget.max_wall_time_ms
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn within_budget_true_when_under() {
        let account = ResourceAccount {
            tokens_used: 100,
            cost_ucr: 50,
            wall_time_ms: 1_000,
            cpu_time_ms: 900,
        };
        let budget = ResourceBudget::new(1_000, 1_000, 10_000);
        assert!(within_budget(&account, &budget));
    }

    #[test]
    fn within_budget_false_when_tokens_over() {
        let account = ResourceAccount {
            tokens_used: 1_001,
            cost_ucr: 50,
            wall_time_ms: 1_000,
            cpu_time_ms: 900,
        };
        let budget = ResourceBudget::new(1_000, 1_000, 10_000);
        assert!(!within_budget(&account, &budget));
    }

    #[test]
    fn within_budget_false_when_cost_over() {
        let account = ResourceAccount {
            tokens_used: 100,
            cost_ucr: 2_000,
            wall_time_ms: 1_000,
            cpu_time_ms: 900,
        };
        let budget = ResourceBudget::new(1_000, 1_000, 10_000);
        assert!(!within_budget(&account, &budget));
    }

    #[test]
    fn within_budget_false_when_wall_time_over() {
        let account = ResourceAccount {
            tokens_used: 100,
            cost_ucr: 50,
            wall_time_ms: 10_001,
            cpu_time_ms: 900,
        };
        let budget = ResourceBudget::new(1_000, 1_000, 10_000);
        assert!(!within_budget(&account, &budget));
    }

    #[test]
    fn within_budget_true_at_exact_limit() {
        let account = ResourceAccount {
            tokens_used: 1_000,
            cost_ucr: 1_000,
            wall_time_ms: 10_000,
            cpu_time_ms: 0,
        };
        let budget = ResourceBudget::new(1_000, 1_000, 10_000);
        assert!(within_budget(&account, &budget));
    }

    #[test]
    fn add_accumulates_all_fields() {
        let mut a = ResourceAccount {
            tokens_used: 100,
            cost_ucr: 20,
            wall_time_ms: 500,
            cpu_time_ms: 400,
        };
        let b = ResourceAccount {
            tokens_used: 50,
            cost_ucr: 10,
            wall_time_ms: 200,
            cpu_time_ms: 180,
        };
        a.add(&b);
        assert_eq!(a.tokens_used, 150);
        assert_eq!(a.cost_ucr, 30);
        assert_eq!(a.wall_time_ms, 700);
        assert_eq!(a.cpu_time_ms, 580);
    }

    #[test]
    fn add_saturates_on_overflow() {
        let mut a = ResourceAccount {
            tokens_used: u64::MAX,
            cost_ucr: 0,
            wall_time_ms: 0,
            cpu_time_ms: 0,
        };
        let b = ResourceAccount {
            tokens_used: 1,
            cost_ucr: 0,
            wall_time_ms: 0,
            cpu_time_ms: 0,
        };
        a.add(&b);
        assert_eq!(a.tokens_used, u64::MAX, "must saturate, not overflow");
    }

    #[test]
    fn resource_account_new_is_zero() {
        let a = ResourceAccount::new();
        assert_eq!(a.tokens_used, 0);
        assert_eq!(a.cost_ucr, 0);
        assert_eq!(a.wall_time_ms, 0);
        assert_eq!(a.cpu_time_ms, 0);
    }
}
