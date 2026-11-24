//! EventBus and EventEmitter — Rust port of sources-lib `events.py`.
//!
//! EventBus: tokio broadcast channel; EventEmitter wraps the sender side.
//! EventKind enumerates all source lifecycle events.

use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::time::{SystemTime, UNIX_EPOCH};
use tokio::sync::broadcast;

/// All lifecycle event kinds emitted by the sources layer.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum EventKind {
    SourceAdded,
    SourceRemoved,
    SyncCompleted,
    SyncFailed,
    ActCompleted,
}

/// A single event emitted onto the bus.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Event {
    pub kind: EventKind,
    pub source_id: String,
    /// Unix timestamp (seconds since epoch, float).
    pub at: f64,
    pub payload: Value,
}

impl Event {
    pub fn new(kind: EventKind, source_id: impl Into<String>, payload: Value) -> Self {
        let at = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map(|d| d.as_secs_f64())
            .unwrap_or(0.0);
        Event { kind, source_id: source_id.into(), at, payload }
    }
}

/// Broadcast-channel-backed event bus.
///
/// Cloning `EventBus` gives a new handle to the same channel.
#[derive(Clone)]
pub struct EventBus {
    tx: broadcast::Sender<Event>,
}

impl EventBus {
    /// Create a new bus with the given channel capacity.
    pub fn new(capacity: usize) -> Self {
        let (tx, _) = broadcast::channel(capacity);
        EventBus { tx }
    }

    /// Emit an event to all current subscribers.
    /// Silently drops the event if there are no subscribers (send returns Err).
    pub fn emit(&self, event: Event) {
        let _ = self.tx.send(event);
    }

    /// Subscribe to events. Returns a `broadcast::Receiver<Event>`.
    pub fn subscribe(&self) -> broadcast::Receiver<Event> {
        self.tx.subscribe()
    }
}

impl Default for EventBus {
    fn default() -> Self {
        Self::new(256)
    }
}

/// Wraps an `EventBus` sender for ergonomic use in adapters.
#[derive(Clone)]
pub struct EventEmitter {
    bus: EventBus,
}

impl EventEmitter {
    pub fn new(bus: EventBus) -> Self {
        EventEmitter { bus }
    }

    pub fn emit(&self, event: Event) {
        self.bus.emit(event);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[tokio::test]
    async fn emit_and_receive() {
        let bus = EventBus::new(16);
        let mut rx = bus.subscribe();
        bus.emit(Event::new(EventKind::SourceAdded, "src-1", json!({"note": "test"})));
        let evt = rx.try_recv().unwrap();
        assert_eq!(evt.kind, EventKind::SourceAdded);
        assert_eq!(evt.source_id, "src-1");
    }

    #[test]
    fn no_subscriber_does_not_panic() {
        let bus = EventBus::new(4);
        // No subscriber — emit should silently succeed.
        bus.emit(Event::new(EventKind::SyncCompleted, "src-2", json!({})));
    }
}
