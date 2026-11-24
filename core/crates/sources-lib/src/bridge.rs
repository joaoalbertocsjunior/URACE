//! Bridge — wraps SourceRegistry with event emission and sync-all convenience.
//!
//! Rust port of sources-lib `bridge.py`.

use crate::events::{Event, EventBus, EventEmitter, EventKind};
use crate::registry::SourceRegistry;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::HashMap;
use std::sync::Arc;

/// Result of a single source sync inside `Bridge::sync_all`.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SyncResult {
    pub source_id: String,
    pub rows: usize,
    pub error: Option<String>,
}

/// Wraps a `SourceRegistry` and emits events on every sync/act operation.
pub struct Bridge {
    registry: Arc<SourceRegistry>,
    emitter: EventEmitter,
}

impl Bridge {
    pub fn new(registry: Arc<SourceRegistry>) -> Self {
        let bus = EventBus::default();
        let emitter = EventEmitter::new(bus);
        Bridge { registry, emitter }
    }

    /// Create with a specific `EventBus` so callers can subscribe before syncing.
    pub fn with_bus(registry: Arc<SourceRegistry>, bus: EventBus) -> Self {
        Bridge { registry, emitter: EventEmitter::new(bus) }
    }

    pub fn emitter(&self) -> &EventEmitter {
        &self.emitter
    }

    /// Sync all registered sources and return one `SyncResult` per source.
    pub async fn sync_all(
        &self,
        app_config: &HashMap<String, Value>,
    ) -> Vec<SyncResult> {
        let records = self.registry.list();
        let mut results = Vec::with_capacity(records.len());

        for record in records {
            let sid = record.id.clone();
            match self.registry.adapter(&record.kind) {
                Err(e) => {
                    self.emitter.emit(Event::new(
                        EventKind::SyncFailed,
                        &sid,
                        serde_json::json!({ "error": e.to_string() }),
                    ));
                    results.push(SyncResult { source_id: sid, rows: 0, error: Some(e.to_string()) });
                }
                Ok(adapter) => {
                    match adapter.sync(&record, app_config).await {
                        Ok(rows) => {
                            let count = rows.len();
                            self.emitter.emit(Event::new(
                                EventKind::SyncCompleted,
                                &sid,
                                serde_json::json!({ "rows": count }),
                            ));
                            results.push(SyncResult { source_id: sid, rows: count, error: None });
                        }
                        Err(e) => {
                            self.emitter.emit(Event::new(
                                EventKind::SyncFailed,
                                &sid,
                                serde_json::json!({ "error": e.to_string() }),
                            ));
                            results.push(SyncResult { source_id: sid, rows: 0, error: Some(e.to_string()) });
                        }
                    }
                }
            }
        }
        results
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::adapter::BaseSourceAdapter;

    #[tokio::test]
    async fn sync_all_empty_registry() {
        let reg = Arc::new(SourceRegistry::new());
        let bridge = Bridge::new(Arc::clone(&reg));
        let results = bridge.sync_all(&HashMap::new()).await;
        assert!(results.is_empty());
    }

    #[tokio::test]
    async fn sync_all_reports_results() {
        let reg = Arc::new(SourceRegistry::new());
        reg.register_kind("base", BaseSourceAdapter).unwrap();
        reg.add("base", Some("s1"), HashMap::new()).unwrap();

        let bridge = Bridge::new(Arc::clone(&reg));
        let results = bridge.sync_all(&HashMap::new()).await;
        assert_eq!(results.len(), 1);
        assert_eq!(results[0].source_id, "s1");
        assert!(results[0].error.is_none());
    }
}
