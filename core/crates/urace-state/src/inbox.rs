//! Bounded message inbox.
//!
//! Max capacity: 1000 messages. When full, the **oldest** message is dropped
//! (FIFO overflow), not the newest. This matches the Python-side semantics.

use parking_lot::RwLock;
use serde::{Deserialize, Serialize};
use std::collections::VecDeque;
use std::sync::Arc;
use std::time::{SystemTime, UNIX_EPOCH};
use thiserror::Error;
use uuid::Uuid;

pub const MAX_CAPACITY: usize = 1000;

#[derive(Debug, Error)]
pub enum InboxError {
    #[error("message not found: {0}")]
    NotFound(String),
}

/// A single inbox message.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Message {
    pub id: String,
    pub from_peer: String,
    pub kind: String,
    pub payload: serde_json::Value,
    pub at_unix: f64,
    /// True once `pop` or `mark_read` has been called for this message.
    pub read: bool,
}

impl Message {
    pub fn new(
        from_peer: impl Into<String>,
        kind: impl Into<String>,
        payload: serde_json::Value,
    ) -> Self {
        Message {
            id: Uuid::new_v4().to_string(),
            from_peer: from_peer.into(),
            kind: kind.into(),
            payload,
            at_unix: SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .map(|d| d.as_secs_f64())
                .unwrap_or(0.0),
            read: false,
        }
    }
}

/// Bounded inbox backed by `parking_lot::RwLock<VecDeque<Message>>`.
///
/// **Overflow policy**: when at capacity, the oldest (front) message is
/// silently dropped to make room for the newest. This prevents backpressure
/// stalls from slow consumers while keeping the most recent messages.
#[derive(Clone)]
pub struct Inbox {
    capacity: usize,
    queue: Arc<RwLock<VecDeque<Message>>>,
}

impl Inbox {
    pub fn new(capacity: usize) -> Self {
        Inbox {
            capacity: capacity.max(1),
            queue: Arc::new(RwLock::new(VecDeque::with_capacity(capacity))),
        }
    }

    /// Push a message. If at capacity, drop the oldest first.
    pub fn push(&self, msg: Message) {
        let mut guard = self.queue.write();
        if guard.len() >= self.capacity {
            guard.pop_front(); // drop oldest
        }
        guard.push_back(msg);
    }

    /// Pop (remove and return) the oldest unread message.
    pub fn pop(&self) -> Option<Message> {
        let mut guard = self.queue.write();
        guard.pop_front()
    }

    /// Peek at all messages without consuming them.
    pub fn peek_all(&self) -> Vec<Message> {
        self.queue.read().iter().cloned().collect()
    }

    /// Count of unread messages.
    pub fn unread_count(&self) -> usize {
        self.queue.read().iter().filter(|m| !m.read).count()
    }

    pub fn len(&self) -> usize {
        self.queue.read().len()
    }

    pub fn is_empty(&self) -> bool {
        self.queue.read().is_empty()
    }

    pub fn capacity(&self) -> usize {
        self.capacity
    }

    /// Mark a specific message as read by id.
    pub fn mark_read(&self, id: &str) -> Result<(), InboxError> {
        let mut guard = self.queue.write();
        guard
            .iter_mut()
            .find(|m| m.id == id)
            .ok_or_else(|| InboxError::NotFound(id.to_owned()))
            .map(|m| m.read = true)
    }

    /// Drain all messages, returning them in FIFO order.
    pub fn drain(&self) -> Vec<Message> {
        let mut guard = self.queue.write();
        guard.drain(..).collect()
    }
}

impl Default for Inbox {
    fn default() -> Self {
        Self::new(MAX_CAPACITY)
    }
}

// ── M14 — Inbox rate-limit + micro-burn ──────────────────────────────────────

/// Maximum messages per sender per 60-second window before micro-burn applies.
pub const INBOX_RATE_LIMIT_PER_MIN: usize = 60;

/// Cost in UCR base units charged per message beyond the rate limit (0.00001 UNIT).
pub const INBOX_MICRO_BURN_UCR: i64 = 1_000;

#[derive(Debug, Clone, PartialEq)]
pub enum InboxRateResult {
    Allowed,
    RateLimited { micro_burn_ucr: i64 },
}

/// Per-sender sliding-window rate guard.
///
/// Tracks the timestamp of each received message per sender over a 60-second
/// rolling window.  When a sender exceeds `INBOX_RATE_LIMIT_PER_MIN` messages
/// in the window, subsequent messages return `RateLimited` with the micro-burn
/// fee the caller should deduct from the sender's balance.
pub struct InboxRateGuard {
    counts: std::collections::HashMap<String, VecDeque<u64>>,
}

impl InboxRateGuard {
    pub fn new() -> Self {
        InboxRateGuard { counts: std::collections::HashMap::new() }
    }

    /// Record a message from `sender` at `now_secs`.
    ///
    /// Returns `Allowed` if the sender is within the rate limit, or
    /// `RateLimited { micro_burn_ucr }` if they have exceeded it.
    pub fn check_and_record(&mut self, sender: &str, now_secs: u64) -> InboxRateResult {
        let window = self.counts.entry(sender.to_owned()).or_default();
        // Drop entries older than 60 seconds.
        while window.front().map(|&t| now_secs.saturating_sub(t) >= 60).unwrap_or(false) {
            window.pop_front();
        }
        if window.len() >= INBOX_RATE_LIMIT_PER_MIN {
            return InboxRateResult::RateLimited { micro_burn_ucr: INBOX_MICRO_BURN_UCR };
        }
        window.push_back(now_secs);
        InboxRateResult::Allowed
    }
}

impl Default for InboxRateGuard {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn msg(kind: &str) -> Message {
        Message::new("peer-x", kind, serde_json::json!({}))
    }

    #[test]
    fn push_and_pop_fifo() {
        let inbox = Inbox::new(10);
        inbox.push(msg("A"));
        inbox.push(msg("B"));
        assert_eq!(inbox.pop().unwrap().kind, "A");
        assert_eq!(inbox.pop().unwrap().kind, "B");
        assert!(inbox.pop().is_none());
    }

    #[test]
    fn overflow_drops_oldest_not_newest() {
        let inbox = Inbox::new(3);
        for name in &["A", "B", "C"] {
            inbox.push(msg(name));
        }
        assert_eq!(inbox.len(), 3);
        // Push a 4th — "A" (oldest) should be dropped
        inbox.push(msg("D"));
        assert_eq!(inbox.len(), 3);
        let all: Vec<_> = inbox
            .peek_all()
            .into_iter()
            .map(|m| m.kind.clone())
            .collect();
        assert!(!all.contains(&"A".to_string()), "oldest should be dropped");
        assert!(all.contains(&"D".to_string()), "newest should be retained");
        assert!(all.contains(&"B".to_string()));
        assert!(all.contains(&"C".to_string()));
    }

    #[test]
    fn capacity_bound() {
        let inbox = Inbox::new(MAX_CAPACITY);
        for i in 0..MAX_CAPACITY + 10 {
            inbox.push(msg(&format!("msg-{}", i)));
        }
        assert_eq!(inbox.len(), MAX_CAPACITY);
    }

    #[test]
    fn drain_clears_inbox() {
        let inbox = Inbox::new(5);
        inbox.push(msg("X"));
        inbox.push(msg("Y"));
        let drained = inbox.drain();
        assert_eq!(drained.len(), 2);
        assert!(inbox.is_empty());
    }

    #[test]
    fn mark_read() {
        let inbox = Inbox::new(5);
        inbox.push(msg("R"));
        let id = inbox.peek_all()[0].id.clone();
        assert_eq!(inbox.unread_count(), 1);
        inbox.mark_read(&id).unwrap();
        assert_eq!(inbox.unread_count(), 0);
    }

    // ── M14 rate-guard tests ──────────────────────────────────────────────────

    #[test]
    fn rate_guard_within_limit_allowed() {
        let mut guard = InboxRateGuard::new();
        let now = 1_000_000u64;
        for _ in 0..INBOX_RATE_LIMIT_PER_MIN {
            assert_eq!(guard.check_and_record("peer-a", now), InboxRateResult::Allowed);
        }
    }

    #[test]
    fn rate_guard_over_limit_returns_micro_burn() {
        let mut guard = InboxRateGuard::new();
        let now = 1_000_000u64;
        for _ in 0..INBOX_RATE_LIMIT_PER_MIN {
            guard.check_and_record("peer-b", now);
        }
        let result = guard.check_and_record("peer-b", now);
        assert_eq!(result, InboxRateResult::RateLimited { micro_burn_ucr: INBOX_MICRO_BURN_UCR });
    }
}
