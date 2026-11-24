//! EnvAdapter — read environment variables filtered by a mandatory prefix.
//!
//! Rust port of `source_adapters/environment_adapter.py`.
//!
//! INVARIANT: `prefix` must be non-empty. An empty prefix would expose the entire
//! environment to callers — this is explicitly rejected with `SourceError::Config`.
//!
//! Sensitive-looking values (containing "secret", "password", "token", "key",
//! "auth", "credential") are redacted in the returned rows.

use crate::adapter::{SourceAdapter, SourceError, SourceRecord};
use async_trait::async_trait;
use serde_json::{json, Value};
use std::collections::HashMap;
use std::time::{SystemTime, UNIX_EPOCH};

const SENSITIVE_PATTERNS: &[&str] = &[
    "secret", "password", "token", "key", "auth", "credential",
];

pub struct EnvAdapter;

impl EnvAdapter {
    fn now() -> f64 {
        SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map(|d| d.as_secs_f64())
            .unwrap_or(0.0)
    }

    /// Returns the validated non-empty prefix from config.
    ///
    /// Returns `Err(SourceError::Config)` if prefix is absent or empty.
    pub fn prefix(record: &SourceRecord) -> Result<String, SourceError> {
        let p = record
            .config
            .get("prefix")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_owned();
        if p.is_empty() {
            return Err(SourceError::Config(
                "config.prefix must be non-empty: exposing the full environment is not permitted".into(),
            ));
        }
        Ok(p)
    }

    fn is_sensitive(key: &str) -> bool {
        let lower = key.to_lowercase();
        SENSITIVE_PATTERNS.iter().any(|p| lower.contains(p))
    }
}

#[async_trait]
impl SourceAdapter for EnvAdapter {
    fn config_schema(&self) -> Value {
        json!({
            "type": "object",
            "required": ["prefix"],
            "properties": {
                "prefix": {
                    "type": "string",
                    "minLength": 1,
                    "description": "Only vars whose name starts with this prefix are returned. Must be non-empty."
                }
            }
        })
    }

    fn actions(&self) -> Vec<String> {
        vec![]
    }

    async fn verify(
        &self,
        record: &SourceRecord,
        _app_config: &HashMap<String, Value>,
    ) -> Result<HashMap<String, Value>, SourceError> {
        // Validation first — guard against empty prefix.
        let prefix = Self::prefix(record)?;
        let count = std::env::vars()
            .filter(|(k, _)| k.starts_with(&prefix))
            .count();
        let mut result = HashMap::new();
        result.insert("ok".into(), Value::Bool(true));
        result.insert("prefix".into(), Value::String(prefix));
        result.insert("matching_vars".into(), json!(count));
        Ok(result)
    }

    async fn sync(
        &self,
        record: &SourceRecord,
        _app_config: &HashMap<String, Value>,
    ) -> Result<Vec<HashMap<String, Value>>, SourceError> {
        let prefix = Self::prefix(record)?;
        let now = Self::now();

        let rows: Vec<HashMap<String, Value>> = std::env::vars()
            .filter(|(k, _)| k.starts_with(&prefix))
            .map(|(k, v)| {
                let value = if Self::is_sensitive(&k) {
                    Value::String("***REDACTED***".into())
                } else {
                    Value::String(v)
                };
                let mut row = HashMap::new();
                row.insert("name".into(), Value::String(k));
                row.insert("value".into(), value);
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

        Ok(rows)
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

#[cfg(test)]
mod tests {
    use super::*;

    fn make_record(prefix: &str) -> SourceRecord {
        let mut config = HashMap::new();
        if !prefix.is_empty() {
            config.insert("prefix".into(), Value::String(prefix.into()));
        }
        SourceRecord::new("env-test", "environment", config)
    }

    #[test]
    fn empty_prefix_returns_config_error() {
        let record = make_record("");
        let err = EnvAdapter::prefix(&record);
        assert!(
            matches!(err, Err(SourceError::Config(_))),
            "expected Config error, got: {err:?}"
        );
    }

    #[tokio::test]
    async fn sync_empty_prefix_returns_error() {
        let record = make_record("");
        let adapter = EnvAdapter;
        let err = adapter.sync(&record, &HashMap::new()).await;
        assert!(matches!(err, Err(SourceError::Config(_))), "got: {err:?}");
    }

    #[tokio::test]
    async fn verify_empty_prefix_returns_error() {
        let record = make_record("");
        let adapter = EnvAdapter;
        let err = adapter.verify(&record, &HashMap::new()).await;
        assert!(matches!(err, Err(SourceError::Config(_))), "got: {err:?}");
    }

    #[tokio::test]
    async fn sync_with_prefix_returns_matching_vars() {
        // Inject a known env var.
        std::env::set_var("URACE_TEST_FOO", "bar");
        let record = make_record("URACE_TEST_");
        let adapter = EnvAdapter;
        let rows = adapter.sync(&record, &HashMap::new()).await.unwrap();
        let found = rows.iter().any(|r| {
            r.get("name").and_then(|v| v.as_str()) == Some("URACE_TEST_FOO")
        });
        assert!(found, "expected URACE_TEST_FOO in rows: {rows:?}");
        // Clean up.
        std::env::remove_var("URACE_TEST_FOO");
    }

    #[tokio::test]
    async fn sync_redacts_sensitive_vars() {
        std::env::set_var("URACE_TEST_SECRET_KEY", "my-secret");
        let record = make_record("URACE_TEST_");
        let adapter = EnvAdapter;
        let rows = adapter.sync(&record, &HashMap::new()).await.unwrap();
        for row in &rows {
            if row.get("name").and_then(|v| v.as_str()) == Some("URACE_TEST_SECRET_KEY") {
                let val = row.get("value").and_then(|v| v.as_str()).unwrap_or("");
                assert!(
                    val.contains("REDACTED"),
                    "sensitive var not redacted: {val}"
                );
            }
        }
        std::env::remove_var("URACE_TEST_SECRET_KEY");
    }

    #[tokio::test]
    async fn sync_no_match_returns_empty() {
        let record = make_record("ZZZZZZ_URACE_UNLIKELY_PREFIX_");
        let adapter = EnvAdapter;
        let rows = adapter.sync(&record, &HashMap::new()).await.unwrap();
        assert!(rows.is_empty());
    }
}
