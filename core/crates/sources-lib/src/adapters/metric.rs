//! MetricAdapter — collects numeric metrics as SourceRecord rows.
//!
//! Rust port of `source_adapters/metric_adapter.py`.
//! The metric value is supplied externally via config["value"] or config["values"].

use crate::adapter::{SourceAdapter, SourceError, SourceRecord};
use async_trait::async_trait;
use serde_json::{json, Value};
use std::collections::HashMap;
use std::time::{SystemTime, UNIX_EPOCH};

pub struct MetricAdapter;

impl MetricAdapter {
    fn now() -> f64 {
        SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map(|d| d.as_secs_f64())
            .unwrap_or(0.0)
    }
}

#[async_trait]
impl SourceAdapter for MetricAdapter {
    fn config_schema(&self) -> Value {
        json!({
            "type": "object",
            "required": ["metric_name"],
            "properties": {
                "metric_name": {"type": "string", "description": "Name of the metric"},
                "direction":   {"type": "string", "enum": ["nondecreasing", "nonincreasing"]},
                "value":       {"type": "number", "description": "Current scalar value"},
                "values":      {"type": "array",  "description": "Time-series values"}
            }
        })
    }

    fn actions(&self) -> Vec<String> {
        vec!["record".into()]
    }

    async fn verify(
        &self,
        record: &SourceRecord,
        _app_config: &HashMap<String, Value>,
    ) -> Result<HashMap<String, Value>, SourceError> {
        let name = record
            .config
            .get("metric_name")
            .and_then(|v| v.as_str())
            .unwrap_or("");
        let mut result = HashMap::new();
        result.insert("ok".into(), Value::Bool(!name.is_empty()));
        result.insert("metric_name".into(), Value::String(name.to_owned()));
        Ok(result)
    }

    async fn sync(
        &self,
        record: &SourceRecord,
        _app_config: &HashMap<String, Value>,
    ) -> Result<Vec<HashMap<String, Value>>, SourceError> {
        let now = Self::now();
        let metric_name = record
            .config
            .get("metric_name")
            .and_then(|v| v.as_str())
            .unwrap_or("unknown")
            .to_owned();
        let direction = record
            .config
            .get("direction")
            .and_then(|v| v.as_str())
            .unwrap_or("nondecreasing")
            .to_owned();

        // If "values" is an array, emit one row per entry.
        if let Some(Value::Array(vals)) = record.config.get("values") {
            let rows = vals
                .iter()
                .map(|v| {
                    let mut row = HashMap::new();
                    row.insert("metric_name".into(), Value::String(metric_name.clone()));
                    row.insert("direction".into(), Value::String(direction.clone()));
                    row.insert("value".into(), v.clone());
                    row.insert("source_id".into(), Value::String(record.id.clone()));
                    row.insert(
                        "observed_at".into(),
                        Value::Number(
                            serde_json::Number::from_f64(now)
                                .unwrap_or(serde_json::Number::from(0)),
                        ),
                    );
                    row
                })
                .collect();
            return Ok(rows);
        }

        // Otherwise emit a single row with optional scalar "value".
        let value = record.config.get("value").cloned().unwrap_or(Value::Null);
        let mut row = HashMap::new();
        row.insert("metric_name".into(), Value::String(metric_name));
        row.insert("direction".into(), Value::String(direction));
        row.insert("value".into(), value);
        row.insert("source_id".into(), Value::String(record.id.clone()));
        row.insert(
            "observed_at".into(),
            Value::Number(
                serde_json::Number::from_f64(now)
                    .unwrap_or(serde_json::Number::from(0)),
            ),
        );
        Ok(vec![row])
    }

    async fn act(
        &self,
        _record: &SourceRecord,
        _app_config: &HashMap<String, Value>,
        action: &str,
        payload: &HashMap<String, Value>,
    ) -> Result<HashMap<String, Value>, SourceError> {
        if action == "record" {
            // Returns the payload with an observed_at timestamp — allows callers
            // to push metric observations without a full sync.
            let now = Self::now();
            let mut result = payload.clone();
            result.insert(
                "observed_at".into(),
                Value::Number(
                    serde_json::Number::from_f64(now)
                        .unwrap_or(serde_json::Number::from(0)),
                ),
            );
            return Ok(result);
        }
        Err(SourceError::ActDenied(format!("action '{action}' not supported")))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_record(metric_name: &str, value: Option<f64>) -> SourceRecord {
        let mut config = HashMap::new();
        config.insert("metric_name".into(), Value::String(metric_name.into()));
        if let Some(v) = value {
            config.insert("value".into(), json!(v));
        }
        SourceRecord::new("metric-test", "metric", config)
    }

    #[tokio::test]
    async fn sync_scalar_value() {
        let record = make_record("coverage", Some(87.5));
        let adapter = MetricAdapter;
        let rows = adapter.sync(&record, &HashMap::new()).await.unwrap();
        assert_eq!(rows.len(), 1);
        assert_eq!(rows[0]["metric_name"], json!("coverage"));
        assert_eq!(rows[0]["value"], json!(87.5));
    }

    #[tokio::test]
    async fn sync_null_when_no_value() {
        let record = make_record("coverage", None);
        let adapter = MetricAdapter;
        let rows = adapter.sync(&record, &HashMap::new()).await.unwrap();
        assert_eq!(rows.len(), 1);
        assert_eq!(rows[0]["value"], Value::Null);
    }

    #[tokio::test]
    async fn sync_array_values() {
        let mut config = HashMap::new();
        config.insert("metric_name".into(), Value::String("latency_ms".into()));
        config.insert("values".into(), json!([10, 20, 30]));
        let record = SourceRecord::new("m-test", "metric", config);
        let adapter = MetricAdapter;
        let rows = adapter.sync(&record, &HashMap::new()).await.unwrap();
        assert_eq!(rows.len(), 3);
    }

    #[tokio::test]
    async fn unsupported_action_rejected() {
        let record = make_record("x", None);
        let adapter = MetricAdapter;
        let err = adapter.act(&record, &HashMap::new(), "delete", &HashMap::new()).await;
        assert!(matches!(err, Err(SourceError::ActDenied(_))));
    }
}
