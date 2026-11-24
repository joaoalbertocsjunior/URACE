//! HttpPollAdapter — polls an HTTP endpoint and returns the response body as a SourceRecord row.
//!
//! Rust port of `http_adapter.py` (which delegates to sources_lib.transport).
//! Uses reqwest (already a workspace dep). JSON responses are parsed into key/value rows;
//! non-JSON responses are stored as a single `body` string field.

use crate::adapter::{SourceAdapter, SourceError, SourceRecord};
use async_trait::async_trait;
use reqwest::Client;
use serde_json::{json, Value};
use std::collections::HashMap;
use std::time::{SystemTime, UNIX_EPOCH};

pub struct HttpPollAdapter {
    client: Client,
}

impl HttpPollAdapter {
    pub fn new() -> Result<Self, SourceError> {
        let client = Client::builder()
            .user_agent("urace-sources-lib/0.1")
            .build()
            .map_err(|e| SourceError::Unavailable(e.to_string()))?;
        Ok(HttpPollAdapter { client })
    }

    fn now() -> f64 {
        SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map(|d| d.as_secs_f64())
            .unwrap_or(0.0)
    }

    fn url(record: &SourceRecord) -> Result<String, SourceError> {
        record
            .config
            .get("url")
            .and_then(|v| v.as_str())
            .filter(|s| !s.is_empty())
            .map(|s| s.to_owned())
            .ok_or_else(|| SourceError::Config("config.url required".into()))
    }

    fn method(record: &SourceRecord) -> String {
        record
            .config
            .get("method")
            .and_then(|v| v.as_str())
            .unwrap_or("GET")
            .to_uppercase()
    }
}

impl Default for HttpPollAdapter {
    fn default() -> Self {
        HttpPollAdapter::new().expect("reqwest client build")
    }
}

#[async_trait]
impl SourceAdapter for HttpPollAdapter {
    fn config_schema(&self) -> Value {
        json!({
            "type": "object",
            "required": ["url"],
            "properties": {
                "url":     {"type": "string", "description": "HTTP endpoint to poll"},
                "method":  {"type": "string", "enum": ["GET", "POST"], "description": "HTTP method (default: GET)"},
                "headers": {"type": "object", "description": "Additional request headers"},
                "timeout": {"type": "integer", "description": "Request timeout in seconds (default: 30)"}
            }
        })
    }

    fn actions(&self) -> Vec<String> {
        vec!["poll".into()]
    }

    async fn verify(
        &self,
        record: &SourceRecord,
        _app_config: &HashMap<String, Value>,
    ) -> Result<HashMap<String, Value>, SourceError> {
        let url = Self::url(record)?;
        let mut result = HashMap::new();
        result.insert("ok".into(), Value::Bool(true));
        result.insert("url".into(), Value::String(url));
        Ok(result)
    }

    async fn sync(
        &self,
        record: &SourceRecord,
        _app_config: &HashMap<String, Value>,
    ) -> Result<Vec<HashMap<String, Value>>, SourceError> {
        let url = Self::url(record)?;
        let method = Self::method(record);
        let now = Self::now();

        let timeout_secs = record
            .config
            .get("timeout")
            .and_then(|v| v.as_u64())
            .unwrap_or(30);

        let mut req = match method.as_str() {
            "POST" => self.client.post(&url),
            _ => self.client.get(&url),
        };

        req = req.timeout(std::time::Duration::from_secs(timeout_secs));

        // Apply optional extra headers.
        if let Some(Value::Object(headers)) = record.config.get("headers") {
            for (k, v) in headers {
                if let Some(val) = v.as_str() {
                    req = req.header(k.as_str(), val);
                }
            }
        }

        let resp = req
            .send()
            .await
            .map_err(|e| SourceError::Unavailable(format!("HTTP request failed: {e}")))?;

        let status = resp.status().as_u16();
        let body_text = resp
            .text()
            .await
            .map_err(|e| SourceError::Io(format!("reading response body: {e}")))?;

        // Try to parse as JSON; fall back to plain string.
        let mut row = HashMap::new();
        row.insert("url".into(), Value::String(url));
        row.insert("status".into(), json!(status));
        row.insert("source_id".into(), Value::String(record.id.clone()));
        row.insert(
            "observed_at".into(),
            Value::Number(
                serde_json::Number::from_f64(now)
                    .unwrap_or(serde_json::Number::from(0)),
            ),
        );

        match serde_json::from_str::<Value>(&body_text) {
            Ok(Value::Object(map)) => {
                for (k, v) in map {
                    row.insert(k, v);
                }
            }
            Ok(other) => {
                row.insert("data".into(), other);
            }
            Err(_) => {
                row.insert("body".into(), Value::String(body_text));
            }
        }

        Ok(vec![row])
    }

    async fn act(
        &self,
        record: &SourceRecord,
        app_config: &HashMap<String, Value>,
        action: &str,
        _payload: &HashMap<String, Value>,
    ) -> Result<HashMap<String, Value>, SourceError> {
        if action == "poll" {
            let rows = self.sync(record, app_config).await?;
            let row = rows.into_iter().next().unwrap_or_default();
            return Ok(row);
        }
        Err(SourceError::ActDenied(format!("action '{action}' not supported")))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_record(url: &str) -> SourceRecord {
        let mut config = HashMap::new();
        config.insert("url".into(), Value::String(url.into()));
        SourceRecord::new("http-test", "http_poll", config)
    }

    #[test]
    fn url_extraction_works() {
        let record = make_record("https://example.com/api");
        let url = HttpPollAdapter::url(&record).unwrap();
        assert_eq!(url, "https://example.com/api");
    }

    #[test]
    fn missing_url_returns_config_error() {
        let record = SourceRecord::new("test", "http_poll", HashMap::new());
        let err = HttpPollAdapter::url(&record);
        assert!(matches!(err, Err(SourceError::Config(_))));
    }

    #[test]
    fn method_defaults_to_get() {
        let record = make_record("https://example.com");
        assert_eq!(HttpPollAdapter::method(&record), "GET");
    }

    #[test]
    fn method_can_be_post() {
        let mut config = HashMap::new();
        config.insert("url".into(), Value::String("https://example.com".into()));
        config.insert("method".into(), Value::String("post".into()));
        let record = SourceRecord::new("test", "http_poll", config);
        assert_eq!(HttpPollAdapter::method(&record), "POST");
    }

    #[tokio::test]
    async fn verify_valid_url() {
        let record = make_record("https://example.com/api");
        let adapter = HttpPollAdapter::new().unwrap();
        let result = adapter.verify(&record, &HashMap::new()).await.unwrap();
        assert_eq!(result["ok"], json!(true));
        assert_eq!(result["url"], json!("https://example.com/api"));
    }

    // NOTE: sync() requires a live HTTP server and is not tested here.
    // Integration tests live in tests/integration/ and require a local stub server.
}
