#![allow(dead_code)]

use async_trait::async_trait;
use thiserror::Error;

/// An event emitted by a source adapter.
pub struct SourceEvent {
    /// ID of the source adapter that produced this event.
    pub source_id: String,
    /// Semantic kind of event (e.g. "file.modified", "commit", "issue.opened").
    pub kind: String,
    /// Arbitrary JSON payload.
    pub payload: serde_json::Value,
    /// Unix timestamp (seconds with sub-second precision).
    pub at_unix: f64,
}

#[derive(Debug, Error)]
pub enum AdapterError {
    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),
    #[error("HTTP error: {0}")]
    Http(String),
    #[error("Git error: {0}")]
    Git(String),
    #[error("JSON error: {0}")]
    Json(#[from] serde_json::Error),
    #[error("Other: {0}")]
    Other(String),
}

/// Core trait every source adapter must implement.
#[async_trait]
pub trait SourceAdapter: Send + Sync {
    /// Unique adapter instance ID (e.g. "github-urace/urace").
    fn id(&self) -> &str;

    /// Adapter kind (e.g. "github", "directory", "http_poll").
    fn kind(&self) -> &str;

    /// Pull new events since the last sync.  Returns zero or more events.
    async fn sync(&mut self) -> Result<Vec<SourceEvent>, AdapterError>;
}
