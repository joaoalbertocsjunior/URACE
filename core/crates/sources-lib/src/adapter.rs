//! SourceAdapter trait and SourceRecord — Rust port of sources-lib `adapter.py`.
//!
//! Adapters are stateless objects; all runtime state lives in SourceRecord.
//! The trait is object-safe (dyn SourceAdapter is usable in the registry).

use async_trait::async_trait;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::HashMap;
use thiserror::Error;

#[derive(Debug, Error)]
pub enum SourceError {
    #[error("source unavailable: {0}")]
    Unavailable(String),
    #[error("authentication failed: {0}")]
    Auth(String),
    #[error("action denied: {0}")]
    ActDenied(String),
    #[error("registry error: {0}")]
    Registry(String),
    #[error("I/O error: {0}")]
    Io(String),
    #[error("configuration error: {0}")]
    Config(String),
}

/// Runtime record for a registered source instance — mirrors Python `SourceRecord`.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SourceRecord {
    pub id: String,
    pub kind: String,
    pub config: HashMap<String, Value>,
    pub state: HashMap<String, Value>,
    pub added_at: f64,
}

impl SourceRecord {
    pub fn new(id: impl Into<String>, kind: impl Into<String>, config: HashMap<String, Value>) -> Self {
        let added_at = {
            use std::time::{SystemTime, UNIX_EPOCH};
            SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .map(|d| d.as_secs_f64())
                .unwrap_or(0.0)
        };
        SourceRecord { id: id.into(), kind: kind.into(), config, state: HashMap::new(), added_at }
    }

    pub fn get(&self, key: &str) -> Option<&Value> {
        self.config.get(key)
    }
}

/// Contract every source adapter must satisfy.
///
/// Adapters are stateless — all runtime state lives in `SourceRecord.state`.
#[async_trait]
pub trait SourceAdapter: Send + Sync {
    /// JSON Schema describing valid `record.config` contents.
    fn config_schema(&self) -> Value {
        Value::Object(Default::default())
    }

    /// Action names supported by `act()`.
    fn actions(&self) -> Vec<String> {
        vec![]
    }

    /// Check source connectivity. Must return `{"ok": bool, ...}`.
    async fn verify(
        &self,
        record: &SourceRecord,
        app_config: &HashMap<String, Value>,
    ) -> Result<HashMap<String, Value>, SourceError>;

    /// Observe the source and return a list of row dicts.
    async fn sync(
        &self,
        record: &SourceRecord,
        app_config: &HashMap<String, Value>,
    ) -> Result<Vec<HashMap<String, Value>>, SourceError>;

    /// Perform a named action. Returns `Err(ActDenied)` if action not supported.
    async fn act(
        &self,
        record: &SourceRecord,
        app_config: &HashMap<String, Value>,
        action: &str,
        payload: &HashMap<String, Value>,
    ) -> Result<HashMap<String, Value>, SourceError>;
}

/// No-op base adapter — override only what you need.
pub struct BaseSourceAdapter;

#[async_trait]
impl SourceAdapter for BaseSourceAdapter {
    async fn verify(
        &self,
        _record: &SourceRecord,
        _app_config: &HashMap<String, Value>,
    ) -> Result<HashMap<String, Value>, SourceError> {
        let mut m = HashMap::new();
        m.insert("ok".to_owned(), Value::Bool(true));
        Ok(m)
    }

    async fn sync(
        &self,
        _record: &SourceRecord,
        _app_config: &HashMap<String, Value>,
    ) -> Result<Vec<HashMap<String, Value>>, SourceError> {
        Ok(vec![])
    }

    async fn act(
        &self,
        _record: &SourceRecord,
        _app_config: &HashMap<String, Value>,
        action: &str,
        _payload: &HashMap<String, Value>,
    ) -> Result<HashMap<String, Value>, SourceError> {
        Err(SourceError::ActDenied(format!("action '{action}' not supported")))
    }
}
