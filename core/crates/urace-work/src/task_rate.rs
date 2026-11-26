//! M06 — Per-peer task submission rate limiting.
//!
//! Implements a sliding-window rate limit: each peer may submit at most
//! `TASK_RATE_LIMIT_PER_MIN` tasks within any 60-second window.

use std::collections::{HashMap, VecDeque};

/// Maximum task submissions allowed per peer within a 60-second window.
pub const TASK_RATE_LIMIT_PER_MIN: usize = 20;

/// Width of the sliding window in seconds.
const WINDOW_SECS: u64 = 60;

// ── TaskRateResult ────────────────────────────────────────────────────────────

/// Result of a rate-limit check.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum TaskRateResult {
    /// The submission is allowed and has been recorded.
    Allowed,
    /// The peer has exceeded the rate limit.
    RateLimited {
        peer_id: String,
        /// Seconds until the oldest in-window event ages out.
        retry_after_secs: u64,
    },
}

// ── TaskRateGuard ─────────────────────────────────────────────────────────────

/// In-process sliding-window rate-limiter, keyed by peer ID.
///
/// Each entry is a `VecDeque` of UNIX timestamps (in seconds) representing
/// the submissions that fall within the current window.
pub struct TaskRateGuard {
    counts: HashMap<String, VecDeque<u64>>,
}

impl Default for TaskRateGuard {
    fn default() -> Self {
        Self::new()
    }
}

impl TaskRateGuard {
    /// Create a new, empty `TaskRateGuard`.
    pub fn new() -> Self {
        TaskRateGuard { counts: HashMap::new() }
    }

    /// Check whether `peer_id` is allowed to submit a task at `now_secs`.
    ///
    /// If allowed, the timestamp is recorded and `TaskRateResult::Allowed` is
    /// returned.  If the peer has already reached `TASK_RATE_LIMIT_PER_MIN`
    /// within the last 60 seconds, `TaskRateResult::RateLimited` is returned
    /// without recording the attempt.
    pub fn check_and_record(&mut self, peer_id: &str, now_secs: u64) -> TaskRateResult {
        let window = self.counts.entry(peer_id.to_owned()).or_default();

        // Evict timestamps that have slid out of the window.
        let cutoff = now_secs.saturating_sub(WINDOW_SECS - 1);
        while window.front().map_or(false, |&t| t < cutoff) {
            window.pop_front();
        }

        if window.len() >= TASK_RATE_LIMIT_PER_MIN {
            // Compute how long until the oldest entry expires.
            let oldest = *window.front().unwrap(); // safe: len >= 1
            let expires_at = oldest + WINDOW_SECS;
            let retry_after_secs = expires_at.saturating_sub(now_secs);
            return TaskRateResult::RateLimited {
                peer_id: peer_id.to_owned(),
                retry_after_secs,
            };
        }

        window.push_back(now_secs);
        TaskRateResult::Allowed
    }

    /// Clear all recorded submissions for `peer_id`.
    pub fn reset(&mut self, peer_id: &str) {
        self.counts.remove(peer_id);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn first_submission_is_allowed() {
        let mut guard = TaskRateGuard::new();
        let result = guard.check_and_record("peer-1", 1_000);
        assert_eq!(result, TaskRateResult::Allowed);
    }

    #[test]
    fn rate_limited_after_limit_reached() {
        let mut guard = TaskRateGuard::new();
        let now = 1_000u64;
        for _ in 0..TASK_RATE_LIMIT_PER_MIN {
            assert_eq!(guard.check_and_record("peer-2", now), TaskRateResult::Allowed);
        }
        // The (TASK_RATE_LIMIT_PER_MIN + 1)-th attempt must be rejected.
        let result = guard.check_and_record("peer-2", now);
        assert!(
            matches!(result, TaskRateResult::RateLimited { .. }),
            "expected RateLimited, got {result:?}"
        );
    }

    #[test]
    fn window_slides_and_allows_again_after_60s() {
        let mut guard = TaskRateGuard::new();
        let t0 = 1_000u64;
        // Fill the window at t0.
        for _ in 0..TASK_RATE_LIMIT_PER_MIN {
            guard.check_and_record("peer-3", t0);
        }
        // Still blocked at t0 + 59.
        assert!(matches!(
            guard.check_and_record("peer-3", t0 + 59),
            TaskRateResult::RateLimited { .. }
        ));
        // Allowed again at t0 + 61 (all old entries have slid out).
        let result = guard.check_and_record("peer-3", t0 + 61);
        assert_eq!(result, TaskRateResult::Allowed, "should be allowed after window slides");
    }

    #[test]
    fn different_peers_have_independent_limits() {
        let mut guard = TaskRateGuard::new();
        let now = 5_000u64;
        // Exhaust the limit for peer-A.
        for _ in 0..TASK_RATE_LIMIT_PER_MIN {
            guard.check_and_record("peer-A", now);
        }
        assert!(matches!(
            guard.check_and_record("peer-A", now),
            TaskRateResult::RateLimited { .. }
        ));
        // peer-B is unaffected.
        assert_eq!(guard.check_and_record("peer-B", now), TaskRateResult::Allowed);
    }

    #[test]
    fn reset_clears_peer_state() {
        let mut guard = TaskRateGuard::new();
        let now = 1_000u64;
        for _ in 0..TASK_RATE_LIMIT_PER_MIN {
            guard.check_and_record("peer-5", now);
        }
        guard.reset("peer-5");
        // After reset, the peer can submit again immediately.
        assert_eq!(guard.check_and_record("peer-5", now), TaskRateResult::Allowed);
    }
}
