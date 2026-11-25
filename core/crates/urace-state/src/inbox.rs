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
}
