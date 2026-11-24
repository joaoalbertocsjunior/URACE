//! Source record types — Protocol v2 `state['sources']` schema.

use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::HashMap;

/// A URACE Protocol v2 source record stored in `state['sources'][id]`.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SourceRecord {
    pub id: String,
    pub kind: String,
    pub enabled: bool,
    pub added_at: String,
    pub status: SourceStatus,
    pub status_history: Vec<StatusHistoryEntry>,
    pub adapter_state: HashMap<String, Value>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum SourceStatus {
    Configured,
    Active,
    Error,
    Disabled,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StatusHistoryEntry {
    pub status: SourceStatus,
    pub at: String,
}
