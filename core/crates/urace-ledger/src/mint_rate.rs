//! M37 — Rolling-window mint rate limit.
//!
//! Each peer is allowed at most `threshold` mints within any rolling 24-hour
//! window. The threshold is derived from the current honest-peer count:
//!   threshold = max(1, floor(honest_peers * HONEST_PEER_FRACTION * RATE_MULTIPLIER))
//!
//! Call `can_mint` before committing a mint; call `record_mint` after the mint
//! is durably written to the ledger.

use std::collections::HashMap;
use std::collections::VecDeque;

/// Size of the rolling window in seconds (24 hours).
pub const WINDOW_SECS: u64 = 86_400;

/// Multiplier applied to the honest-peer fraction when computing the threshold.
pub const RATE_MULTIPLIER: f64 = 2.0;

/// Fraction of honest peers used as the base rate.
pub const HONEST_PEER_FRACTION: f64 = 0.2;

/// Per-peer rolling-window mint rate limiter.
pub struct MintRateWindow {
    /// peer_id → ordered queue of mint timestamps (Unix seconds).
    windows: HashMap<String, VecDeque<u64>>,
    /// Maximum mints allowed in one WINDOW_SECS period.
    threshold: u64,
}

impl MintRateWindow {
    /// Create a new limiter calibrated to `honest_peers`.
    pub fn new(honest_peers: u64) -> Self {
        let threshold =
            ((honest_peers as f64) * HONEST_PEER_FRACTION * RATE_MULTIPLIER) as u64;
        MintRateWindow {
            windows: HashMap::new(),
            threshold: threshold.max(1),
        }
    }

    /// Recompute the threshold after the network-size estimate changes.
    pub fn update_threshold(&mut self, honest_peers: u64) {
        self.threshold =
            ((honest_peers as f64) * HONEST_PEER_FRACTION * RATE_MULTIPLIER) as u64;
        self.threshold = self.threshold.max(1);
    }

    /// Returns `true` if `peer_id` has not yet exhausted its window quota.
    ///
    /// Stale entries (older than `WINDOW_SECS`) are evicted before the check.
    pub fn can_mint(&mut self, peer_id: &str, now_secs: u64) -> bool {
        let window = self.windows.entry(peer_id.to_string()).or_default();
        Self::evict(window, now_secs);
        (window.len() as u64) < self.threshold
    }

    /// Record a mint event.  Call this **after** the mint has been committed.
    pub fn record_mint(&mut self, peer_id: &str, now_secs: u64) {
        self.windows
            .entry(peer_id.to_string())
            .or_default()
            .push_back(now_secs);
    }

    /// Current threshold value.
    pub fn threshold(&self) -> u64 {
        self.threshold
    }

    /// Number of mints recorded for `peer_id` within the current window.
    pub fn mints_in_window(&mut self, peer_id: &str, now_secs: u64) -> usize {
        let window = self.windows.entry(peer_id.to_string()).or_default();
        Self::evict(window, now_secs);
        window.len()
    }

    // --- helpers ---

    fn evict(window: &mut VecDeque<u64>, now_secs: u64) {
        while let Some(&oldest) = window.front() {
            if now_secs.saturating_sub(oldest) >= WINDOW_SECS {
                window.pop_front();
            } else {
                break;
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn can_mint_up_to_threshold() {
        // With honest_peers = 25: threshold = floor(25 * 0.2 * 2.0) = 10.
        // For a small threshold test, use honest_peers = 13 → floor(13*0.2*2)=5.
        let mut limiter = MintRateWindow::new(13);
        assert_eq!(limiter.threshold(), 5, "expected threshold 5");

        let now = 1_000_000u64;
        for _ in 0..5 {
            assert!(limiter.can_mint("peer-a", now));
            limiter.record_mint("peer-a", now);
        }
        // 6th attempt must be denied
        assert!(!limiter.can_mint("peer-a", now));
    }

    #[test]
    fn window_rolls_after_24h() {
        let mut limiter = MintRateWindow::new(13); // threshold = 5
        let t0 = 0u64;

        // Fill the window completely at t0
        for _ in 0..5 {
            assert!(limiter.can_mint("peer-b", t0));
            limiter.record_mint("peer-b", t0);
        }
        assert!(!limiter.can_mint("peer-b", t0));

        // Advance exactly WINDOW_SECS: entries recorded at t0 are now expired
        let t1 = t0 + WINDOW_SECS;
        assert!(
            limiter.can_mint("peer-b", t1),
            "slot should reopen after window expires"
        );
    }

    #[test]
    fn threshold_updates_with_peer_count() {
        let mut limiter = MintRateWindow::new(0); // honest_peers=0 → threshold=1
        assert_eq!(limiter.threshold(), 1);

        limiter.update_threshold(100); // 100 * 0.2 * 2.0 = 40
        assert_eq!(limiter.threshold(), 40);

        limiter.update_threshold(0); // floored at 1
        assert_eq!(limiter.threshold(), 1);
    }

    #[test]
    fn mints_in_window_counts_live_entries() {
        let mut limiter = MintRateWindow::new(50); // threshold = 20
        let now = 500_000u64;
        limiter.record_mint("peer-c", now);
        limiter.record_mint("peer-c", now + 60);
        assert_eq!(limiter.mints_in_window("peer-c", now + 120), 2);
        // Both entries expire once the window fully passes them:
        // entry at (now) expires when query_time - now >= WINDOW_SECS
        // entry at (now+60) expires when query_time - (now+60) >= WINDOW_SECS
        // So both are gone at query_time = now + WINDOW_SECS + 60
        assert_eq!(
            limiter.mints_in_window("peer-c", now + WINDOW_SECS + 60),
            0
        );
    }
}
