//! M67 — Per-peer network-level rate limiting across all message types.

use serde::{Deserialize, Serialize};
use std::collections::{HashMap, VecDeque};

pub const NET_RATE_MESSAGES_PER_SEC: usize = 100; // max messages per second per peer
pub const NET_RATE_WINDOW_SECS: u64 = 1;
pub const NET_RATE_WINDOW_MS: u64 = NET_RATE_WINDOW_SECS * 1_000;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum MessageClass {
    Gossip,
    Routing,
    Data,
    Control,
}

/// Per-peer sliding-window network rate limiter.
pub struct NetRateLimiter {
    /// peer_id -> VecDeque<timestamp_ms>
    windows: HashMap<String, VecDeque<u64>>,
    limit_per_sec: usize,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum NetRateResult {
    Allowed,
    RateLimited { peer_id: String, messages_in_window: usize },
}

impl NetRateLimiter {
    pub fn new(limit_per_sec: usize) -> Self {
        NetRateLimiter {
            windows: HashMap::new(),
            limit_per_sec,
        }
    }

    pub fn default_limiter() -> Self {
        Self::new(NET_RATE_MESSAGES_PER_SEC)
    }

    /// Sliding 1-second window check. `now_ms` is current time in milliseconds.
    pub fn check_and_record(&mut self, peer_id: &str, now_ms: u64) -> NetRateResult {
        let window = self.windows.entry(peer_id.to_string()).or_default();

        // Evict entries older than the 1-second window.
        let cutoff = now_ms.saturating_sub(NET_RATE_WINDOW_MS);
        while let Some(&front) = window.front() {
            if front < cutoff {
                window.pop_front();
            } else {
                break;
            }
        }

        if window.len() >= self.limit_per_sec {
            return NetRateResult::RateLimited {
                peer_id: peer_id.to_string(),
                messages_in_window: window.len(),
            };
        }

        window.push_back(now_ms);
        NetRateResult::Allowed
    }

    /// Reset all recorded messages for a peer (e.g., after re-authentication).
    pub fn reset_peer(&mut self, peer_id: &str) {
        self.windows.remove(peer_id);
    }
}

impl Default for NetRateLimiter {
    fn default() -> Self {
        Self::new(NET_RATE_MESSAGES_PER_SEC)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_messages_within_limit_allowed() {
        let mut limiter = NetRateLimiter::new(5);
        let now = 1_000_000u64; // ms
        for i in 0..5 {
            let r = limiter.check_and_record("peer-A", now + i as u64);
            assert_eq!(r, NetRateResult::Allowed, "message {} should be allowed", i + 1);
        }
    }

    #[test]
    fn test_messages_beyond_limit_blocked() {
        let mut limiter = NetRateLimiter::new(3);
        let now = 2_000_000u64;
        for _ in 0..3 {
            limiter.check_and_record("peer-B", now);
        }
        let r = limiter.check_and_record("peer-B", now);
        match r {
            NetRateResult::RateLimited { peer_id, messages_in_window } => {
                assert_eq!(peer_id, "peer-B");
                assert_eq!(messages_in_window, 3);
            }
            NetRateResult::Allowed => panic!("4th message should be rate-limited"),
        }
    }

    #[test]
    fn test_different_peers_independent() {
        let mut limiter = NetRateLimiter::new(2);
        let now = 3_000_000u64;
        // Fill peer-C
        limiter.check_and_record("peer-C", now);
        limiter.check_and_record("peer-C", now + 1);
        // peer-D should still be allowed.
        let r = limiter.check_and_record("peer-D", now);
        assert_eq!(r, NetRateResult::Allowed);
    }

    #[test]
    fn test_window_slides_and_unblocks() {
        let mut limiter = NetRateLimiter::new(2);
        let t0 = 5_000_000u64; // ms
        limiter.check_and_record("peer-E", t0);
        limiter.check_and_record("peer-E", t0 + 10);
        // Blocked within the same window.
        assert!(matches!(
            limiter.check_and_record("peer-E", t0 + 50),
            NetRateResult::RateLimited { .. }
        ));
        // After 1 second + 1 ms, old entries should be evicted.
        let t1 = t0 + NET_RATE_WINDOW_MS + 1;
        let r = limiter.check_and_record("peer-E", t1);
        assert_eq!(r, NetRateResult::Allowed, "window should have slid");
    }

    #[test]
    fn test_reset_peer_clears_window() {
        let mut limiter = NetRateLimiter::new(1);
        let now = 7_000_000u64;
        limiter.check_and_record("peer-F", now);
        // Currently rate-limited.
        assert!(matches!(
            limiter.check_and_record("peer-F", now + 1),
            NetRateResult::RateLimited { .. }
        ));
        // After reset, should be allowed again.
        limiter.reset_peer("peer-F");
        let r = limiter.check_and_record("peer-F", now + 2);
        assert_eq!(r, NetRateResult::Allowed);
    }
}
