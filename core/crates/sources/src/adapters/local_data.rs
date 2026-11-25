#![allow(dead_code)]

use std::path::PathBuf;

use async_trait::async_trait;

use crate::adapter::{AdapterError, SourceAdapter, SourceEvent};

/// Reads a local JSON file on each sync and emits its contents as an event.
pub struct LocalDataAdapter {
    id: String,
    path: PathBuf,
}

impl LocalDataAdapter {
    pub fn new(id: impl Into<String>, path: impl Into<PathBuf>) -> Self {
        Self {
            id: id.into(),
            path: path.into(),
        }
    }
}

#[async_trait]
impl SourceAdapter for LocalDataAdapter {
    fn id(&self) -> &str {
        &self.id
    }

    fn kind(&self) -> &str {
        "local_data"
    }

    async fn sync(&mut self) -> Result<Vec<SourceEvent>, AdapterError> {
        let raw = std::fs::read_to_string(&self.path).map_err(AdapterError::Io)?;
        let value: serde_json::Value = serde_json::from_str(&raw)?;

        let payload = serde_json::json!({
            "path": self.path.to_string_lossy(),
            "data": value,
        });

        Ok(vec![SourceEvent {
            source_id: self.id.clone(),
            kind: "local_data.read".to_owned(),
            payload,
            at_unix: unix_now(),
        }])
    }
}

fn unix_now() -> f64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs_f64())
        .unwrap_or(0.0)
}
