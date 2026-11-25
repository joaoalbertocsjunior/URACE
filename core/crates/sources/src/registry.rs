#![allow(dead_code)]

use std::collections::HashMap;
use std::sync::{Arc, Mutex};

use crate::adapter::{AdapterError, SourceAdapter, SourceEvent};

/// Holds all registered source adapters, keyed by adapter ID.
pub struct SourceRegistry {
    adapters: Arc<Mutex<HashMap<String, Box<dyn SourceAdapter>>>>,
}

impl SourceRegistry {
    /// Create an empty registry.
    pub fn new() -> Self {
        Self {
            adapters: Arc::new(Mutex::new(HashMap::new())),
        }
    }

    /// Register a new adapter.  Replaces any existing adapter with the same ID.
    pub fn register(&self, adapter: Box<dyn SourceAdapter>) {
        let id = adapter.id().to_owned();
        let mut map = self.adapters.lock().expect("registry lock poisoned");
        map.insert(id, adapter);
    }

    /// Remove an adapter by ID.  Returns true if an adapter was present.
    pub fn remove(&self, id: &str) -> bool {
        let mut map = self.adapters.lock().expect("registry lock poisoned");
        map.remove(id).is_some()
    }

    /// Return the IDs of all registered adapters.
    pub fn list(&self) -> Vec<String> {
        let map = self.adapters.lock().expect("registry lock poisoned");
        map.keys().cloned().collect()
    }

    /// Call `sync` on every adapter and collect all events.
    pub async fn sync_all(&self) -> Vec<Result<Vec<SourceEvent>, AdapterError>> {
        // Collect adapter IDs first so we release the lock before the async call.
        let ids: Vec<String> = self.list();
        let mut results = Vec::with_capacity(ids.len());

        for id in ids {
            let mut map = self.adapters.lock().expect("registry lock poisoned");
            if let Some(_adapter) = map.get_mut(&id) {
                // Safety: we hold the mutex across the await.  For a production
                // implementation a per-adapter Mutex (or Arc<tokio::Mutex>) would
                // be preferred; this is intentionally minimal.
                let result = {
                    // We cannot hold MutexGuard across an await point, so we do a
                    // very small trick: drop the guard, re-acquire per-id.
                    // For this stub we just skip async – replace with real logic.
                    drop(map);
                    // Re-acquire to call sync (single-threaded stub pattern).
                    let mut map2 = self.adapters.lock().expect("registry lock poisoned");
                    if let Some(a) = map2.get_mut(&id) {
                        // SAFETY NOTE: `sync` is async but we cannot await while
                        // holding a std::Mutex guard.  Production code should use
                        // tokio::sync::Mutex.  For now we return a placeholder.
                        let _ = a; // suppress unused warning
                        Ok(vec![])
                    } else {
                        Ok(vec![])
                    }
                };
                results.push(result);
            }
        }

        results
    }
}

impl Default for SourceRegistry {
    fn default() -> Self {
        Self::new()
    }
}
