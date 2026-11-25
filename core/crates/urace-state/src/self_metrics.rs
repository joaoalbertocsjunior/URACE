//! Node self-metrics — numeric measurements of URACE runtime health.
//!
//! Ported from `self_metrics.py`. Collects test pass rate, import health, and
//! spec quality metrics. In Rust, the collector stores pre-populated metric
//! entries that can be fed from any measurement source (subprocess, procfs, etc.)

use parking_lot::RwLock;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::Arc;
use std::time::{SystemTime, UNIX_EPOCH};

pub const SCHEMA: &str = "urace-self-metrics-v1";

/// Direction of a metric: should it increase or decrease over time?
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum MetricDirection {
    Nondecreasing,
    Nonincreasing,
    None,
}

/// A single named metric entry.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MetricEntry {
    pub name: String,
    /// Numeric value (None if measurement failed).
    pub value: Option<f64>,
    pub unit: String,
    pub direction: MetricDirection,
    /// Optional detail string (e.g. error message, stderr).
    pub detail: Option<String>,
}

impl MetricEntry {
    pub fn new(
        name: impl Into<String>,
        value: Option<f64>,
        unit: impl Into<String>,
        direction: MetricDirection,
    ) -> Self {
        MetricEntry {
            name: name.into(),
            value,
            unit: unit.into(),
            direction,
            detail: None,
        }
    }

    pub fn with_detail(mut self, detail: impl Into<String>) -> Self {
        self.detail = Some(detail.into());
        self
    }
}

/// A snapshot of all node metrics.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NodeMetrics {
    pub schema: String,
    pub collected_at: f64,
    pub metrics: HashMap<String, MetricEntry>,
    pub errors: Vec<HashMap<String, String>>,
}

impl NodeMetrics {
    pub fn new() -> Self {
        NodeMetrics {
            schema: SCHEMA.to_owned(),
            collected_at: now_unix(),
            metrics: HashMap::new(),
            errors: vec![],
        }
    }

    pub fn insert(&mut self, entry: MetricEntry) {
        self.metrics.insert(entry.name.clone(), entry);
    }

    pub fn add_error(&mut self, metric: &str, error: &str) {
        let mut m = HashMap::new();
        m.insert("metric".to_owned(), metric.to_owned());
        m.insert("error".to_owned(), error.to_owned());
        self.errors.push(m);
    }

    /// Convert to external_metric_state source entry format.
    pub fn as_external_source(&self) -> Option<serde_json::Value> {
        let values: HashMap<String, f64> = self
            .metrics
            .values()
            .filter_map(|e| e.value.map(|v| (e.name.clone(), v)))
            .collect();
        if values.is_empty() {
            return None;
        }
        Some(serde_json::json!({
            "id": "urace-self-measurement",
            "source": "urace-self-measurement",
            "kind": "self_metrics",
            "collected_at": self.collected_at,
            "values": values,
            "attribution": "SELF_MEASURED_NO_EXTERNAL_USERS_REQUIRED",
        }))
    }
}

impl Default for NodeMetrics {
    fn default() -> Self {
        Self::new()
    }
}

/// Metrics collector: holds the most recent snapshot plus a ring buffer of history.
#[derive(Clone)]
pub struct MetricsCollector {
    capacity: usize,
    history: Arc<RwLock<Vec<NodeMetrics>>>,
    latest: Arc<RwLock<Option<NodeMetrics>>>,
}

impl MetricsCollector {
    pub fn new(history_capacity: usize) -> Self {
        MetricsCollector {
            capacity: history_capacity.max(1),
            history: Arc::new(RwLock::new(Vec::new())),
            latest: Arc::new(RwLock::new(None)),
        }
    }

    /// Record a new metrics snapshot.
    pub fn record(&self, metrics: NodeMetrics) {
        *self.latest.write() = Some(metrics.clone());
        let mut hist = self.history.write();
        if hist.len() >= self.capacity {
            hist.remove(0);
        }
        hist.push(metrics);
    }

    /// Return the most recent snapshot.
    pub fn latest(&self) -> Option<NodeMetrics> {
        self.latest.read().clone()
    }

    /// Return all retained snapshots in chronological order.
    pub fn history(&self) -> Vec<NodeMetrics> {
        self.history.read().clone()
    }

    /// Build a minimal NodeMetrics from named metric values (convenience).
    pub fn record_values(&self, values: HashMap<String, f64>) {
        let mut m = NodeMetrics::new();
        for (name, value) in values {
            m.insert(MetricEntry::new(
                name,
                Some(value),
                "ratio",
                MetricDirection::None,
            ));
        }
        self.record(m);
    }
}

impl Default for MetricsCollector {
    fn default() -> Self {
        Self::new(100)
    }
}

fn now_unix() -> f64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs_f64())
        .unwrap_or(0.0)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn insert_and_retrieve() {
        let mut m = NodeMetrics::new();
        m.insert(MetricEntry::new(
            "test_pass_rate",
            Some(0.95),
            "ratio",
            MetricDirection::Nondecreasing,
        ));
        assert_eq!(m.metrics["test_pass_rate"].value, Some(0.95));
    }

    #[test]
    fn as_external_source_empty() {
        let m = NodeMetrics::new();
        assert!(m.as_external_source().is_none());
    }

    #[test]
    fn as_external_source_with_values() {
        let mut m = NodeMetrics::new();
        m.insert(MetricEntry::new(
            "x",
            Some(1.0),
            "count",
            MetricDirection::None,
        ));
        let src = m.as_external_source().unwrap();
        assert_eq!(src["kind"], "self_metrics");
        assert_eq!(src["values"]["x"], 1.0);
    }

    #[test]
    fn collector_history_capped() {
        let c = MetricsCollector::new(3);
        for i in 0..5u64 {
            let mut m = NodeMetrics::new();
            m.insert(MetricEntry::new(
                "seq",
                Some(i as f64),
                "count",
                MetricDirection::None,
            ));
            c.record(m);
        }
        assert_eq!(c.history().len(), 3);
        // Most recent should be seq=4
        assert_eq!(c.latest().unwrap().metrics["seq"].value, Some(4.0));
    }

    #[test]
    fn error_recording() {
        let mut m = NodeMetrics::new();
        m.add_error("test_pass_rate", "timeout");
        assert_eq!(m.errors.len(), 1);
        assert_eq!(m.errors[0]["metric"], "test_pass_rate");
    }
}
