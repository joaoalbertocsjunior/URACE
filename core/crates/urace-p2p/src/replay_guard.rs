//! M26 — Message replay protection: reject duplicate message IDs within a TTL window.

use std::collections::HashMap;

pub const REPLAY_WINDOW_SECS: u64 = 300; // 5-minute replay window

/// Replay guard tracking message IDs within a sliding TTL window.
pub struct ReplayGuard {
    seen: HashMap<String, u64>, // msg_id -> first_seen_unix
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ReplayResult {
    Fresh,
    Replay { first_seen_unix: u64 },
}

impl ReplayGuard {
    pub fn new() -> Self {
        ReplayGuard {
            seen: HashMap::new(),
        }
    }

    /// Check and register a message ID.
    ///
    /// Returns `Replay` if the ID was already seen within the window.
    /// Evicts entries older than `REPLAY_WINDOW_SECS` before checking.
    pub fn check(&mut self, msg_id: &str, now_unix: u64) -> ReplayResult {
        self.evict_expired(now_unix);

        if let Some(&first) = self.seen.get(msg_id) {
            return ReplayResult::Replay { first_seen_unix: first };
        }

        self.seen.insert(msg_id.to_string(), now_unix);
        ReplayResult::Fresh
    }

    /// Evict all entries whose first_seen timestamp is outside the window.
    pub fn evict_expired(&mut self, now_unix: u64) {
        let cutoff = now_unix.saturating_sub(REPLAY_WINDOW_SECS);
        self.seen.retain(|_, &mut first_seen| first_seen >= cutoff);
    }

    /// Current number of message IDs tracked in the window.
    pub fn seen_count(&self) -> usize {
        self.seen.len()
    }
}

impl Default for ReplayGuard {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_new_message_is_fresh() {
        let mut guard = ReplayGuard::new();
        let r = guard.check("msg-abc", 1_000);
        assert_eq!(r, ReplayResult::Fresh);
    }

    #[test]
    fn test_same_id_replayed_is_replay() {
        let mut guard = ReplayGuard::new();
        guard.check("msg-dup", 1_000);
        let r = guard.check("msg-dup", 1_100);
        match r {
            ReplayResult::Replay { first_seen_unix } => assert_eq!(first_seen_unix, 1_000),
            ReplayResult::Fresh => panic!("expected Replay"),
        }
    }

    #[test]
    fn test_expired_message_id_treated_as_fresh() {
        let mut guard = ReplayGuard::new();
        let t0 = 5_000u64;
        guard.check("msg-old", t0);
        // Advance beyond the replay window.
        let t1 = t0 + REPLAY_WINDOW_SECS + 1;
        let r = guard.check("msg-old", t1);
        assert_eq!(r, ReplayResult::Fresh, "expired ID should be treated as fresh");
    }

    #[test]
    fn test_different_ids_are_independent() {
        let mut guard = ReplayGuard::new();
        guard.check("alpha", 1_000);
        let r = guard.check("beta", 1_000);
        assert_eq!(r, ReplayResult::Fresh);
    }

    #[test]
    fn test_seen_count_tracks_entries() {
        let mut guard = ReplayGuard::new();
        assert_eq!(guard.seen_count(), 0);
        guard.check("x", 1_000);
        guard.check("y", 1_001);
        assert_eq!(guard.seen_count(), 2);
    }

    #[test]
    fn test_evict_expired_reduces_count() {
        let mut guard = ReplayGuard::new();
        guard.check("old", 100);
        guard.check("new", 1_000);
        // Evict with time beyond window for "old" but not "new".
        guard.evict_expired(100 + REPLAY_WINDOW_SECS + 1);
        assert_eq!(guard.seen_count(), 1);
    }
}
