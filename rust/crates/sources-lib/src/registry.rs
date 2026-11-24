//! SourceRegistry — thread-safe adapter kind + record registry.
//!
//! Rust port of sources-lib `registry.py`. Uses DashMap for concurrent access.

use crate::adapter::{SourceAdapter, SourceError, SourceRecord};
use dashmap::DashMap;
use serde_json::Value;
use std::collections::HashMap;
use std::sync::Arc;

pub struct SourceRegistry {
    kinds: DashMap<String, Arc<dyn SourceAdapter>>,
    records: DashMap<String, SourceRecord>,
}

impl SourceRegistry {
    pub fn new() -> Self {
        SourceRegistry {
            kinds: DashMap::new(),
            records: DashMap::new(),
        }
    }

    /// Register an adapter for `kind`. Returns `Err(Registry)` if already registered.
    pub fn register_kind(
        &self,
        kind: impl Into<String>,
        adapter: impl SourceAdapter + 'static,
    ) -> Result<(), SourceError> {
        let kind = kind.into();
        if self.kinds.contains_key(&kind) {
            return Err(SourceError::Registry(format!("kind '{kind}' already registered")));
        }
        self.kinds.insert(kind, Arc::new(adapter));
        Ok(())
    }

    pub fn unregister_kind(&self, kind: &str) {
        self.kinds.remove(kind);
    }

    pub fn kinds(&self) -> Vec<String> {
        self.kinds.iter().map(|e| e.key().clone()).collect()
    }

    pub fn adapter(&self, kind: &str) -> Result<Arc<dyn SourceAdapter>, SourceError> {
        self.kinds
            .get(kind)
            .map(|e| Arc::clone(e.value()))
            .ok_or_else(|| SourceError::Registry(format!("unknown kind '{kind}'")))
    }

    /// Register a new source instance.
    pub fn add(
        &self,
        kind: &str,
        source_id: Option<&str>,
        config: HashMap<String, Value>,
    ) -> Result<SourceRecord, SourceError> {
        if !self.kinds.contains_key(kind) {
            return Err(SourceError::Registry(format!("unknown kind '{kind}'")));
        }
        let sid = source_id
            .map(|s| s.to_owned())
            .unwrap_or_else(|| uuid::Uuid::new_v4().simple().to_string()[..12].to_owned());
        if self.records.contains_key(&sid) {
            return Err(SourceError::Registry(format!("source id '{sid}' already registered")));
        }
        let record = SourceRecord::new(sid.clone(), kind, config);
        self.records.insert(sid, record.clone());
        Ok(record)
    }

    pub fn remove(&self, source_id: &str) {
        self.records.remove(source_id);
    }

    pub fn get(&self, source_id: &str) -> Option<SourceRecord> {
        self.records.get(source_id).map(|e| e.value().clone())
    }

    pub fn list(&self) -> Vec<SourceRecord> {
        self.records.iter().map(|e| e.value().clone()).collect()
    }
}

impl Default for SourceRegistry {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::adapter::BaseSourceAdapter;

    #[test]
    fn register_and_add() {
        let reg = SourceRegistry::new();
        reg.register_kind("test", BaseSourceAdapter).unwrap();
        let record = reg.add("test", Some("src-1"), HashMap::new()).unwrap();
        assert_eq!(record.id, "src-1");
        assert_eq!(record.kind, "test");
    }

    #[test]
    fn duplicate_kind_rejected() {
        let reg = SourceRegistry::new();
        reg.register_kind("test", BaseSourceAdapter).unwrap();
        assert!(matches!(
            reg.register_kind("test", BaseSourceAdapter),
            Err(SourceError::Registry(_))
        ));
    }

    #[test]
    fn unknown_kind_rejected() {
        let reg = SourceRegistry::new();
        assert!(matches!(
            reg.add("ghost", None, HashMap::new()),
            Err(SourceError::Registry(_))
        ));
    }
}
