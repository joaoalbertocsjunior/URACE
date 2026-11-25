#![allow(dead_code)]

use tokio::sync::broadcast;

use crate::adapter::SourceEvent;

const DEFAULT_CAPACITY: usize = 256;

/// A broadcast bus for `SourceEvent` values.
///
/// Multiple subscribers each receive every published event independently.
pub struct EventBus {
    sender: broadcast::Sender<BusEvent>,
}

/// Wrapper that makes `SourceEvent` clonable for the broadcast channel.
#[derive(Clone)]
pub struct BusEvent {
    pub source_id: String,
    pub kind: String,
    pub payload: serde_json::Value,
    pub at_unix: f64,
}

impl From<SourceEvent> for BusEvent {
    fn from(e: SourceEvent) -> Self {
        Self {
            source_id: e.source_id,
            kind: e.kind,
            payload: e.payload,
            at_unix: e.at_unix,
        }
    }
}

impl EventBus {
    /// Create a new bus with the default channel capacity.
    pub fn new() -> Self {
        let (sender, _) = broadcast::channel(DEFAULT_CAPACITY);
        Self { sender }
    }

    /// Publish an event.  Returns the number of active subscribers that
    /// received it, or an error if the channel is closed.
    pub fn publish(&self, event: SourceEvent) -> Result<usize, broadcast::error::SendError<BusEvent>> {
        self.sender.send(event.into())
    }

    /// Create a new subscriber receiver.
    pub fn subscribe(&self) -> broadcast::Receiver<BusEvent> {
        self.sender.subscribe()
    }
}

impl Default for EventBus {
    fn default() -> Self {
        Self::new()
    }
}
