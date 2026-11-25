//! Portable analytics metrics store.
//!
//! `MetricStore` persists metrics as append-only signed JSONL rows.
//! Canonical control state never depends on this module; it is observational only.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use thiserror::Error;
use urace_ledger::{Journal, JournalError};

#[derive(Debug, Error)]
pub enum AnalyticsError {
    #[error("journal error: {0}")]
    Journal(#[from] JournalError),

    #[error("serialization error: {0}")]
    Serialization(#[from] serde_json::Error),
}

/// A single recorded metric data point.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Metric {
    pub name: String,
    pub value: f64,
    pub tags: HashMap<String, String>,
    pub recorded_at: String,
}

/// Append-only metric store backed by a signed JSONL journal.
pub struct MetricStore {
    journal: Journal,
}

impl MetricStore {
    pub fn open(
        path: impl AsRef<std::path::Path>,
        hmac_key: [u8; 32],
    ) -> Result<Self, AnalyticsError> {
        let journal = Journal::open(path, hmac_key)?;
        Ok(MetricStore { journal })
    }

    /// Record a metric. Never raises; partial failures surface as errors.
    pub fn record(&self, metric: Metric) -> Result<(), AnalyticsError> {
        let payload = serde_json::to_value(&metric)?;
        self.journal.append("METRIC", payload)?;
        Ok(())
    }

    /// Return all recorded values for `name`.
    pub fn query(&self, name: &str) -> Result<Vec<Metric>, AnalyticsError> {
        let entries = self.journal.verify_integrity()?;
        let metrics = entries
            .into_iter()
            .filter(|e| e.kind == "METRIC")
            .filter_map(|e| {
                let m: Metric = serde_json::from_value(e.payload).ok()?;
                if m.name == name {
                    Some(m)
                } else {
                    None
                }
            })
            .collect();
        Ok(metrics)
    }

    /// Return the most recently recorded value for `name`.
    pub fn latest(&self, name: &str) -> Result<Option<Metric>, AnalyticsError> {
        Ok(self.query(name)?.into_iter().last())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    const KEY: [u8; 32] = *b"analytics-store-key-32bytes-----";

    fn metric(name: &str, value: f64) -> Metric {
        Metric {
            name: name.to_owned(),
            value,
            tags: HashMap::new(),
            recorded_at: "2026-01-01T00:00:00Z".to_owned(),
        }
    }

    #[test]
    fn record_and_query() {
        let dir = tempdir().unwrap();
        let store = MetricStore::open(dir.path().join("metrics.jsonl"), KEY).unwrap();

        store.record(metric("cpu_pct", 42.0)).unwrap();
        store.record(metric("cpu_pct", 55.0)).unwrap();
        store.record(metric("mem_mb", 1024.0)).unwrap();

        let cpu = store.query("cpu_pct").unwrap();
        assert_eq!(cpu.len(), 2);

        let mem = store.query("mem_mb").unwrap();
        assert_eq!(mem.len(), 1);
    }

    #[test]
    fn latest_returns_last_recorded() {
        let dir = tempdir().unwrap();
        let store = MetricStore::open(dir.path().join("metrics.jsonl"), KEY).unwrap();

        store.record(metric("cpu_pct", 10.0)).unwrap();
        store.record(metric("cpu_pct", 90.0)).unwrap();

        let latest = store.latest("cpu_pct").unwrap().unwrap();
        assert_eq!(latest.value, 90.0);
    }

    #[test]
    fn query_unknown_name_returns_empty() {
        let dir = tempdir().unwrap();
        let store = MetricStore::open(dir.path().join("metrics.jsonl"), KEY).unwrap();
        assert!(store.query("ghost").unwrap().is_empty());
        assert!(store.latest("ghost").unwrap().is_none());
    }
}
