//! GitHubAdapter — list issues, PRs, commits, contents via GitHub REST API.
//!
//! Rust port of sources-lib `adapters/github.py`.
//! Uses reqwest + rustls (no openssl). Token from config["token"].

use crate::adapter::{SourceAdapter, SourceError, SourceRecord};
use async_trait::async_trait;
use reqwest::{header, Client};
use serde_json::{json, Value};
use std::collections::HashMap;
use std::time::{SystemTime, UNIX_EPOCH};

pub struct GitHubAdapter {
    client: Client,
}

impl GitHubAdapter {
    pub fn new() -> Result<Self, SourceError> {
        let client = Client::builder()
            .user_agent("urace-sources-lib/0.1")
            .build()
            .map_err(|e| SourceError::Unavailable(e.to_string()))?;
        Ok(GitHubAdapter { client })
    }

    fn token(record: &SourceRecord, app_config: &HashMap<String, Value>) -> Option<String> {
        record
            .config
            .get("token")
            .or_else(|| app_config.get("github_token"))
            .and_then(|v| v.as_str())
            .filter(|s| !s.is_empty())
            .map(|s| s.to_owned())
    }

    fn repo(record: &SourceRecord) -> Result<String, SourceError> {
        record
            .config
            .get("repo")
            .and_then(|v| v.as_str())
            .ok_or_else(|| SourceError::Unavailable("config.repo required".into()))
            .map(|s| s.to_owned())
    }

    async fn api_get(
        &self,
        url: &str,
        token: Option<&str>,
    ) -> Result<Value, SourceError> {
        let mut req = self.client.get(url);
        if let Some(tok) = token {
            req = req.header(
                header::AUTHORIZATION,
                format!("Bearer {tok}"),
            );
        }
        req = req.header(header::ACCEPT, "application/vnd.github.v3+json");
        let resp = req.send().await
            .map_err(|e| SourceError::Unavailable(e.to_string()))?;
        if !resp.status().is_success() {
            return Err(SourceError::Unavailable(format!("GitHub API {}", resp.status())));
        }
        resp.json::<Value>().await
            .map_err(|e| SourceError::Io(e.to_string()))
    }
}

impl Default for GitHubAdapter {
    fn default() -> Self {
        GitHubAdapter::new().expect("reqwest client build")
    }
}

#[async_trait]
impl SourceAdapter for GitHubAdapter {
    fn config_schema(&self) -> Value {
        json!({
            "type": "object",
            "required": ["repo"],
            "properties": {
                "repo":     {"type": "string"},
                "token":    {"type": "string"},
                "resource": {"type": "string", "enum": ["issues", "pulls", "commits", "contents"]},
                "state":    {"type": "string", "enum": ["open", "closed", "all"]},
                "path":     {"type": "string"},
                "limit":    {"type": "integer"}
            }
        })
    }

    fn actions(&self) -> Vec<String> {
        vec!["create_issue".into(), "close_issue".into(), "create_comment".into()]
    }

    async fn verify(
        &self,
        record: &SourceRecord,
        app_config: &HashMap<String, Value>,
    ) -> Result<HashMap<String, Value>, SourceError> {
        let repo = Self::repo(record)?;
        let token = Self::token(record, app_config);
        let url = format!("https://api.github.com/repos/{repo}");
        match self.api_get(&url, token.as_deref()).await {
            Ok(v) => {
                let mut result = HashMap::new();
                result.insert("ok".into(), Value::Bool(true));
                result.insert("repo".into(), v.get("full_name").cloned().unwrap_or(Value::Null));
                result.insert("private".into(), v.get("private").cloned().unwrap_or(Value::Null));
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

    async fn sync(
        &self,
        record: &SourceRecord,
        app_config: &HashMap<String, Value>,
    ) -> Result<Vec<HashMap<String, Value>>, SourceError> {
        let repo = Self::repo(record)?;
        let token = Self::token(record, app_config);
        let resource = record
            .config
            .get("resource")
            .and_then(|v| v.as_str())
            .unwrap_or("issues");
        let limit = record
            .config
            .get("limit")
            .and_then(|v| v.as_u64())
            .unwrap_or(100) as usize;
        let state = record
            .config
            .get("state")
            .and_then(|v| v.as_str())
            .unwrap_or("open");

        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map(|d| d.as_secs_f64())
            .unwrap_or(0.0);

        let url = match resource {
            "issues" => format!("https://api.github.com/repos/{repo}/issues?state={state}&per_page={limit}"),
            "pulls"  => format!("https://api.github.com/repos/{repo}/pulls?state={state}&per_page={limit}"),
            "commits"=> format!("https://api.github.com/repos/{repo}/commits?per_page={limit}"),
            "contents" => {
                let path = record.config.get("path").and_then(|v| v.as_str()).unwrap_or("");
                format!("https://api.github.com/repos/{repo}/contents/{path}")
            }
            _ => return Err(SourceError::Io(format!("unknown resource: {resource}"))),
        };

        let data = self.api_get(&url, token.as_deref()).await?;
        let items = match data {
            Value::Array(arr) => arr,
            Value::Object(_) => vec![data],
            _ => vec![],
        };

        let rows = items
            .into_iter()
            .take(limit)
            .map(|item| {
                let mut row: HashMap<String, Value> = match item {
                    Value::Object(map) => map.into_iter().collect(),
                    other => {
                        let mut m = HashMap::new();
                        m.insert("data".into(), other);
                        m
                    }
                };
                row.insert("source_id".into(), Value::String(record.id.clone()));
                row.insert(
                    "observed_at".into(),
                    Value::Number(serde_json::Number::from_f64(now).unwrap_or(serde_json::Number::from(0))),
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
        // Actions require write token — full implementation in R-9 CLI phase.
        match action {
            "create_issue" | "close_issue" | "create_comment" => {
                Err(SourceError::ActDenied(format!("action '{action}' requires write token — not yet implemented in Rust port")))
            }
            _ => Err(SourceError::ActDenied(format!("action '{action}' not supported"))),
        }
    }
}
