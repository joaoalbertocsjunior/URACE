//! GitAdapter — observe a git repository (commits, branches, tags) via git2.
//!
//! Rust port of `source_adapters/git_adapter.py`.
//! Actions: fetch (network), pull — not implemented in this port.

use crate::adapter::{SourceAdapter, SourceError, SourceRecord};
use async_trait::async_trait;
use serde_json::{json, Value};
use std::collections::HashMap;
use std::path::Path;
use std::time::{SystemTime, UNIX_EPOCH};

pub struct GitAdapter;

impl GitAdapter {
    fn now() -> f64 {
        SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map(|d| d.as_secs_f64())
            .unwrap_or(0.0)
    }

    fn repo_path(record: &SourceRecord) -> Result<String, SourceError> {
        record
            .config
            .get("path")
            .and_then(|v| v.as_str())
            .filter(|s| !s.is_empty())
            .map(|s| s.to_owned())
            .ok_or_else(|| SourceError::Config("config.path required".into()))
    }
}

#[async_trait]
impl SourceAdapter for GitAdapter {
    fn config_schema(&self) -> Value {
        json!({
            "type": "object",
            "required": ["path"],
            "properties": {
                "path":   {"type": "string", "description": "Absolute path to git repo"},
                "remote": {"type": "string", "description": "Remote name (default: origin)"},
                "branch": {"type": "string", "description": "Branch to track (default: HEAD)"},
                "limit":  {"type": "integer", "description": "Max commits to list (default: 20)"}
            }
        })
    }

    fn actions(&self) -> Vec<String> {
        vec!["list_branches".into(), "list_tags".into()]
    }

    async fn verify(
        &self,
        record: &SourceRecord,
        _app_config: &HashMap<String, Value>,
    ) -> Result<HashMap<String, Value>, SourceError> {
        let path_str = Self::repo_path(record)?;
        let path = Path::new(&path_str);
        let mut result = HashMap::new();
        if !path.exists() {
            result.insert("ok".into(), Value::Bool(false));
            result.insert("error".into(), Value::String(format!("path does not exist: {path_str}")));
            return Ok(result);
        }
        match git2::Repository::open(&path_str) {
            Ok(repo) => {
                let head_sha = repo
                    .head()
                    .ok()
                    .and_then(|h| h.peel_to_commit().ok())
                    .map(|c| c.id().to_string())
                    .unwrap_or_default();
                result.insert("ok".into(), Value::Bool(true));
                result.insert("path".into(), Value::String(path_str));
                result.insert("head_sha".into(), Value::String(head_sha));
            }
            Err(e) => {
                result.insert("ok".into(), Value::Bool(false));
                result.insert("error".into(), Value::String(e.to_string()));
            }
        }
        Ok(result)
    }

    async fn sync(
        &self,
        record: &SourceRecord,
        _app_config: &HashMap<String, Value>,
    ) -> Result<Vec<HashMap<String, Value>>, SourceError> {
        let path_str = Self::repo_path(record)?;
        let now = Self::now();
        let limit = record
            .config
            .get("limit")
            .and_then(|v| v.as_u64())
            .unwrap_or(20) as usize;

        let repo = git2::Repository::open(&path_str)
            .map_err(|e| SourceError::Unavailable(format!("git open: {e}")))?;

        let head_ref = repo
            .head()
            .map_err(|e| SourceError::Unavailable(format!("git head: {e}")))?;
        let head_commit = head_ref
            .peel_to_commit()
            .map_err(|e| SourceError::Unavailable(format!("peel to commit: {e}")))?;
        let head_sha = head_commit.id().to_string();

        let active_branch = if head_ref.is_branch() {
            head_ref
                .shorthand()
                .map(|s| s.to_owned())
        } else {
            None
        };

        // Walk recent commits.
        let mut revwalk = repo.revwalk()
            .map_err(|e| SourceError::Io(format!("revwalk: {e}")))?;
        revwalk.push_head()
            .map_err(|e| SourceError::Io(format!("push head: {e}")))?;

        let mut rows = Vec::new();
        for (i, oid_result) in revwalk.enumerate() {
            if i >= limit {
                break;
            }
            let oid = match oid_result {
                Ok(o) => o,
                Err(_) => continue,
            };
            let commit = match repo.find_commit(oid) {
                Ok(c) => c,
                Err(_) => continue,
            };
            let summary = commit.summary().unwrap_or("").to_owned();
            let author = commit.author().name().unwrap_or("").to_owned();
            let ts = commit.time().seconds();

            let mut row = HashMap::new();
            row.insert("sha".into(), Value::String(oid.to_string()));
            row.insert("message".into(), Value::String(summary));
            row.insert("author".into(), Value::String(author));
            row.insert("timestamp".into(), json!(ts));
            row.insert("head_sha".into(), Value::String(head_sha.clone()));
            row.insert(
                "active_branch".into(),
                active_branch
                    .as_deref()
                    .map(|s| Value::String(s.to_owned()))
                    .unwrap_or(Value::Null),
            );
            row.insert("source_id".into(), Value::String(record.id.clone()));
            row.insert(
                "observed_at".into(),
                Value::Number(
                    serde_json::Number::from_f64(now)
                        .unwrap_or(serde_json::Number::from(0)),
                ),
            );
            rows.push(row);
        }

        Ok(rows)
    }

    async fn act(
        &self,
        record: &SourceRecord,
        _app_config: &HashMap<String, Value>,
        action: &str,
        _payload: &HashMap<String, Value>,
    ) -> Result<HashMap<String, Value>, SourceError> {
        let path_str = Self::repo_path(record)?;
        let repo = git2::Repository::open(&path_str)
            .map_err(|e| SourceError::Unavailable(format!("git open: {e}")))?;

        match action {
            "list_branches" => {
                let branches = repo
                    .branches(None)
                    .map_err(|e| SourceError::Io(format!("branches: {e}")))?;
                let names: Vec<Value> = branches
                    .flatten()
                    .filter_map(|(b, _)| b.name().ok().flatten().map(|n| Value::String(n.to_owned())))
                    .collect();
                let mut result = HashMap::new();
                result.insert("branches".into(), Value::Array(names));
                Ok(result)
            }
            "list_tags" => {
                let mut tags = Vec::new();
                repo.tag_foreach(|_id, name| {
                    if let Ok(s) = std::str::from_utf8(name) {
                        tags.push(Value::String(s.trim_start_matches("refs/tags/").to_owned()));
                    }
                    true
                })
                .map_err(|e| SourceError::Io(format!("tag_foreach: {e}")))?;
                let mut result = HashMap::new();
                result.insert("tags".into(), Value::Array(tags));
                Ok(result)
            }
            _ => Err(SourceError::ActDenied(format!("action '{action}' not supported"))),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_record(path: &str) -> SourceRecord {
        let mut config = HashMap::new();
        config.insert("path".into(), Value::String(path.into()));
        SourceRecord::new("git-test", "git", config)
    }

    #[tokio::test]
    async fn verify_valid_repo() {
        let record = make_record("/home/host/Desktop/URACE");
        let adapter = GitAdapter;
        let result = adapter.verify(&record, &HashMap::new()).await.unwrap();
        assert_eq!(result["ok"], json!(true), "{result:?}");
        assert!(result.contains_key("head_sha"));
    }

    #[tokio::test]
    async fn verify_invalid_path() {
        let record = make_record("/nonexistent");
        let adapter = GitAdapter;
        let result = adapter.verify(&record, &HashMap::new()).await.unwrap();
        assert_eq!(result["ok"], json!(false));
    }

    #[tokio::test]
    async fn sync_returns_commits() {
        let record = make_record("/home/host/Desktop/URACE");
        let adapter = GitAdapter;
        let rows = adapter.sync(&record, &HashMap::new()).await.unwrap();
        assert!(!rows.is_empty(), "expected commits");
        assert!(rows[0].contains_key("sha"));
        assert!(rows[0].contains_key("message"));
    }

    #[tokio::test]
    async fn act_list_branches() {
        let record = make_record("/home/host/Desktop/URACE");
        let adapter = GitAdapter;
        let result = adapter.act(&record, &HashMap::new(), "list_branches", &HashMap::new()).await.unwrap();
        assert!(result.contains_key("branches"));
    }

    #[tokio::test]
    async fn unsupported_action_rejected() {
        let record = make_record("/home/host/Desktop/URACE");
        let adapter = GitAdapter;
        let err = adapter.act(&record, &HashMap::new(), "push", &HashMap::new()).await;
        assert!(matches!(err, Err(SourceError::ActDenied(_))));
    }
}
