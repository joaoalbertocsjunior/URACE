//! Optional telemetry event buffer with periodic flush to journal.
//!
//! When the buffer reaches `BUFFER_LIMIT` (1000) events, `emit` automatically
//! triggers a flush. `flush()` can also be called explicitly.
//! No-op when the journal path is not configured.

use parking_lot::Mutex;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use thiserror::Error;
use urace_ledger::{Journal, JournalError};

/// Maximum buffered events before auto-flush.
pub const BUFFER_LIMIT: usize = 1000;

#[derive(Debug, Error)]
pub enum TelemetryError {
    #[error("journal error: {0}")]
    Journal(#[from] JournalError),

    #[error("serialization error: {0}")]
    Serialization(#[from] serde_json::Error),
}

/// A single telemetry event.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TelemetryEvent {
    pub event_type: String,
    pub peer_id: String,
    pub payload: Value,
    pub at: String,
}

struct Inner {
    buffer: Vec<TelemetryEvent>,
    total_flushed: usize,
}

/// In-memory buffer + periodic flush to an append-only signed journal.
///
/// Buffer limit: `BUFFER_LIMIT` events before auto-flush.
pub struct TelemetryEmitter {
    inner: Mutex<Inner>,
    journal: Journal,
}

impl TelemetryEmitter {
    pub fn open(
        path: impl AsRef<std::path::Path>,
        hmac_key: [u8; 32],
    ) -> Result<Self, TelemetryError> {
        let journal = Journal::open(path, hmac_key)?;
        Ok(TelemetryEmitter {
            inner: Mutex::new(Inner {
                buffer: Vec::with_capacity(BUFFER_LIMIT),
                total_flushed: 0,
            }),
            journal,
        })
    }

    /// Emit an event. Auto-flushes to journal when buffer reaches `BUFFER_LIMIT`.
    pub fn emit(&self, event: TelemetryEvent) -> Result<(), TelemetryError> {
        let should_flush = {
            let mut inner = self.inner.lock();
            inner.buffer.push(event);
            inner.buffer.len() >= BUFFER_LIMIT
        };
        if should_flush {
            self.flush()?;
        }
        Ok(())
    }

    /// Flush all buffered events to the journal. Returns the count written.
    pub fn flush(&self) -> Result<usize, TelemetryError> {
        let events: Vec<TelemetryEvent> = {
            let mut inner = self.inner.lock();
            std::mem::take(&mut inner.buffer)
        };

        let count = events.len();
        for event in &events {
            let payload = serde_json::to_value(event)?;
            self.journal.append("TELEMETRY_EVENT", payload)?;
        }

        {
            let mut inner = self.inner.lock();
            inner.total_flushed += count;
        }

        Ok(count)
    }

    /// Return the number of events currently in the buffer (not yet flushed).
    pub fn buffer_len(&self) -> usize {
        self.inner.lock().buffer.len()
    }

    /// Return the total number of events flushed to the journal so far.
    pub fn total_flushed(&self) -> usize {
        self.inner.lock().total_flushed
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;
    use tempfile::tempdir;

    const KEY: [u8; 32] = *b"telemetry-key-32bytes-pad-------";

    fn event(kind: &str) -> TelemetryEvent {
        TelemetryEvent {
            event_type: kind.to_owned(),
            peer_id: "peer-1".to_owned(),
            payload: json!({ "detail": "test" }),
            at: "2026-01-01T00:00:00Z".to_owned(),
        }
    }

    #[test]
    fn emit_and_flush() {
        let dir = tempdir().unwrap();
        let emitter = TelemetryEmitter::open(dir.path().join("telem.jsonl"), KEY).unwrap();

        emitter.emit(event("cycle_start")).unwrap();
        emitter.emit(event("cycle_end")).unwrap();
        assert_eq!(emitter.buffer_len(), 2);

        let written = emitter.flush().unwrap();
        assert_eq!(written, 2);
        assert_eq!(emitter.buffer_len(), 0);
        assert_eq!(emitter.total_flushed(), 2);
    }

    #[test]
    fn auto_flush_at_buffer_limit() {
        let dir = tempdir().unwrap();
        let emitter = TelemetryEmitter::open(dir.path().join("telem.jsonl"), KEY).unwrap();

        // Fill buffer to BUFFER_LIMIT — the last emit triggers auto-flush.
        for _ in 0..BUFFER_LIMIT {
            emitter.emit(event("tick")).unwrap();
        }

        // After auto-flush, buffer should be empty.
        assert_eq!(emitter.buffer_len(), 0);
        assert_eq!(emitter.total_flushed(), BUFFER_LIMIT);
    }

    #[test]
    fn flush_empty_buffer_returns_zero() {
        let dir = tempdir().unwrap();
        let emitter = TelemetryEmitter::open(dir.path().join("telem.jsonl"), KEY).unwrap();
        assert_eq!(emitter.flush().unwrap(), 0);
    }
}
