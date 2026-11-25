#![allow(dead_code)]

use std::time::Duration;

use tokio::sync::mpsc;

use crate::adapter::SourceEvent;
use crate::registry::SourceRegistry;

/// Connects a `SourceRegistry` to a tokio mpsc channel.
///
/// Call `run()` to start a polling loop that calls `sync_all` on the registry
/// and forwards every event into the channel.
pub struct SourceBridge {
    registry: SourceRegistry,
    tx: mpsc::Sender<SourceEvent>,
    poll_interval: Duration,
}

impl SourceBridge {
    /// Create a bridge.  Returns the bridge and the receiving end of the channel.
    pub fn new(registry: SourceRegistry, poll_interval: Duration) -> (Self, mpsc::Receiver<SourceEvent>) {
        let (tx, rx) = mpsc::channel(1024);
        let bridge = Self {
            registry,
            tx,
            poll_interval,
        };
        (bridge, rx)
    }

    /// Run the polling loop indefinitely.
    ///
    /// Each iteration:
    /// 1. Calls `registry.sync_all()`.
    /// 2. Sends every resulting event to the mpsc channel.
    /// 3. Sleeps for `poll_interval`.
    pub async fn run(self) {
        loop {
            let results = self.registry.sync_all().await;
            for result in results {
                match result {
                    Ok(events) => {
                        for event in events {
                            if self.tx.send(event).await.is_err() {
                                // Receiver dropped; stop the loop.
                                tracing::info!("SourceBridge: receiver dropped, stopping");
                                return;
                            }
                        }
                    }
                    Err(e) => {
                        tracing::warn!("SourceBridge: adapter sync error: {e}");
                    }
                }
            }
            tokio::time::sleep(self.poll_interval).await;
        }
    }
}
