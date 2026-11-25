#![allow(dead_code)]

use std::path::PathBuf;
use std::sync::{mpsc as std_mpsc, Mutex};
use std::time::Duration;

use async_trait::async_trait;
use notify::{Config, Event, RecommendedWatcher, RecursiveMode, Watcher};

use crate::adapter::{AdapterError, SourceAdapter, SourceEvent};

/// Watches a directory for file-system changes and emits `SourceEvent`s.
pub struct DirectoryAdapter {
    id: String,
    path: PathBuf,
    _watcher: Option<RecommendedWatcher>,
    /// Wrapped in Mutex so the struct is Sync (required by SourceAdapter).
    rx: Option<Mutex<std_mpsc::Receiver<notify::Result<Event>>>>,
}

impl DirectoryAdapter {
    /// Create and start watching `path` recursively.
    pub fn new(id: impl Into<String>, path: impl Into<PathBuf>) -> Result<Self, AdapterError> {
        let id = id.into();
        let path = path.into();

        let (tx, rx) = std_mpsc::channel();
        let mut watcher = RecommendedWatcher::new(tx, Config::default().with_poll_interval(Duration::from_secs(1)))
            .map_err(|e| AdapterError::Other(e.to_string()))?;

        watcher
            .watch(&path, RecursiveMode::Recursive)
            .map_err(|e| AdapterError::Other(e.to_string()))?;

        Ok(Self {
            id,
            path,
            _watcher: Some(watcher),
            rx: Some(Mutex::new(rx)),
        })
    }

    fn drain_events(&self) -> Vec<SourceEvent> {
        let Some(rx_mutex) = &self.rx else { return vec![] };
        let rx = rx_mutex.lock().expect("rx lock poisoned");
        let mut events = vec![];
        while let Ok(Ok(event)) = rx.try_recv() {
            let kind = format!("{:?}", event.kind);
            let paths: Vec<_> = event.paths.iter().map(|p| p.to_string_lossy().into_owned()).collect();
            let payload = serde_json::json!({ "kind": kind, "paths": paths });
            events.push(SourceEvent {
                source_id: self.id.clone(),
                kind: "fs.event".to_owned(),
                payload,
                at_unix: unix_now(),
            });
        }
        events
    }
}

#[async_trait]
impl SourceAdapter for DirectoryAdapter {
    fn id(&self) -> &str {
        &self.id
    }

    fn kind(&self) -> &str {
        "directory"
    }

    async fn sync(&mut self) -> Result<Vec<SourceEvent>, AdapterError> {
        Ok(self.drain_events())
    }
}

fn unix_now() -> f64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs_f64())
        .unwrap_or(0.0)
}
