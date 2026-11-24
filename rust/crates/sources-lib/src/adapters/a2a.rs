//! A2ASourceAdapter — port of `sources_lib/adapters/a2a.py`.
//!
//! Connects to an A2A (Agent-to-Agent) endpoint:
//!   - verify(): GET `{url}/.well-known/agent.json`
//!   - sync():   POST `{url}/tasks` with `{"query": "list"}`
//!   - act():    POST `{url}/tasks` with custom payload (action: run_task)

use crate::adapter::{SourceAdapter, SourceError, SourceRecord};
use async_trait::async_trait;
use reqwest::Client;
use serde_json::{json, Value};
use std::collections::HashMap;
use std::time::{SystemTime, UNIX_EPOCH};

pub struct A2ASourceAdapter {
    client: Client,
}

impl A2ASourceAdapter {
    pub fn new() -> Result<Self, SourceError> {
        let client = Client::builder()
            .user_agent("urace-sources-lib/0.1")
            .build()
            .map_err(|e| SourceError::Unavailable(e.to_string()))?;
        Ok(A2ASourceAdapter { client })
    }

    fn url(record: &SourceRecord) -> Result<String, SourceError> {
        record
            .config
            .get("url")
            .and_then(|v| v.as_str())
            .filter(|s| !s.is_empty())
            .map(|s| s.to_owned())
            .ok_or_else(|| SourceError::Auth("config missing required field 'url'".into()))
    }

    fn now_secs() -> f64 {
        SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map(|d| d.as_secs_f64())
            .unwrap_or(0.0)
    }
}

impl Default for A2ASourceAdapter {
    fn default() -> Self {
        A2ASourceAdapter::new().expect("failed to build reqwest client")
    }
}

#[async_trait]
impl SourceAdapter for A2ASourceAdapter {
    fn config_schema(&self) -> Value {
        json!({
            "type": "object",
            "required": ["url"],
            "properties": {
                "url": { "type": "string", "description": "A2A agent endpoint URL" }
            }
        })
    }

    fn actions(&self) -> Vec<String> {
        vec!["run_task".into()]
    }

    /// Verify the A2A agent endpoint by fetching `{url}/.well-known/agent.json`.
    async fn verify(
        &self,
        record: &SourceRecord,
        _app_config: &HashMap<String, Value>,
    ) -> Result<HashMap<String, Value>, SourceError> {
        let url = A2ASourceAdapter::url(record)?;
        let well_known = format!("{}/.well-known/agent.json", url.trim_end_matches('/'));

        match self.client.get(&well_known).send().await {
            Ok(resp) if resp.status().is_success() => {
                let body: Value = resp
                    .json()
                    .await
                    .unwrap_or_else(|_| json!({}));
                let name = body.get("name").and_then(Value::as_str).map(String::from);
                let mut result = HashMap::new();
                result.insert("ok".into(), Value::Bool(true));
                if let Some(n) = name {
                    result.insert("name".into(), Value::String(n));
                }
                Ok(result)
            }
            Ok(resp) => {
                let mut result = HashMap::new();
                result.insert("ok".into(), Value::Bool(false));
                result.insert(
                    "error".into(),
                    Value::String(format!("HTTP {}", resp.status())),
                );
                Ok(result)
            }
            Err(e) => {
                let mut result = HashMap::new();
                result.insert("ok".into(), Value::Bool(false));
                result.insert("error".into(), Value::String(e.to_string()));
                Ok(result)
            }
        }
    }

    /// Sync tasks from the A2A endpoint: POST `{url}/tasks` with `{"query": "list"}`.
    async fn sync(
        &self,
        record: &SourceRecord,
        _app_config: &HashMap<String, Value>,
    ) -> Result<Vec<HashMap<String, Value>>, SourceError> {
        let url = A2ASourceAdapter::url(record)?;
        let endpoint = format!("{}/tasks", url.trim_end_matches('/'));

        let resp = self
            .client
            .post(&endpoint)
            .json(&json!({"query": "list"}))
            .send()
            .await
            .map_err(|e| SourceError::Unavailable(e.to_string()))?;

        if !resp.status().is_success() {
            return Err(SourceError::Unavailable(format!("HTTP {}", resp.status())));
        }

        let body: Value = resp
            .json()
            .await
            .map_err(|e| SourceError::Unavailable(e.to_string()))?;

        let tasks = match body {
            Value::Array(arr) => arr,
            Value::Object(ref obj) => {
                // Some implementations nest under a "tasks" key.
                obj.get("tasks")
                    .and_then(Value::as_array)
                    .cloned()
                    .unwrap_or_default()
            }
            _ => vec![],
        };

        let now = A2ASourceAdapter::now_secs();
        let rows: Vec<HashMap<String, Value>> = tasks
            .into_iter()
            .map(|task| {
                let mut row: HashMap<String, Value> = match task {
                    Value::Object(m) => m.into_iter().collect(),
                    other => {
                        let mut m = HashMap::new();
                        m.insert("task".into(), other);
                        m
                    }
                };
                row.insert("source_id".into(), Value::String(record.id.clone()));
                row.insert("observed_at".into(), Value::Number(
                    serde_json::Number::from_f64(now).unwrap_or_else(|| 0.into()),
                ));
                row
            })
            .collect();

        Ok(rows)
    }

    /// Perform an action on the A2A endpoint. Supported actions: `run_task`.
    async fn act(
        &self,
        record: &SourceRecord,
        _app_config: &HashMap<String, Value>,
        action: &str,
        payload: &HashMap<String, Value>,
    ) -> Result<HashMap<String, Value>, SourceError> {
        if action != "run_task" {
            return Err(SourceError::ActDenied(format!("unknown action: {}", action)));
        }
        let url = A2ASourceAdapter::url(record)?;
        let endpoint = format!("{}/tasks", url.trim_end_matches('/'));

        let resp = self
            .client
            .post(&endpoint)
            .json(payload)
            .send()
            .await
            .map_err(|e| SourceError::Unavailable(e.to_string()))?;

        if !resp.status().is_success() {
            return Err(SourceError::Unavailable(format!("HTTP {}", resp.status())));
        }

        let result: Value = resp
            .json()
            .await
            .map_err(|e| SourceError::Unavailable(e.to_string()))?;

        let row: HashMap<String, Value> = match result {
            Value::Object(m) => m.into_iter().collect(),
            other => {
                let mut m = HashMap::new();
                m.insert("result".into(), other);
                m
            }
        };
        Ok(row)
    }
}
