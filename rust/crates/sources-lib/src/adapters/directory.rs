//! DirectoryAdapter — list direct children of a local directory as metadata rows.
//!
//! Rust port of sources-lib `adapters/directory.py`.
//! Symlink targets are rejected (security invariant).

use crate::adapter::{SourceAdapter, SourceError, SourceRecord};
use async_trait::async_trait;
use serde_json::{json, Value};
use std::collections::HashMap;
use std::path::Path;
use std::time::{SystemTime, UNIX_EPOCH};

pub struct DirectoryAdapter {
    max_files: usize,
}

impl DirectoryAdapter {
    pub fn new(max_files: usize) -> Self {
        DirectoryAdapter { max_files }
    }
}

impl Default for DirectoryAdapter {
    fn default() -> Self {
        DirectoryAdapter::new(1000)
    }
}

#[async_trait]
impl SourceAdapter for DirectoryAdapter {
    fn config_schema(&self) -> Value {
        json!({
            "type": "object",
            "required": ["path"],
            "properties": {
                "path": {"type": "string"},
                "skip_hidden": {"type": "boolean"},
                "max_files": {"type": "integer"}
            }
        })
    }

    fn actions(&self) -> Vec<String> {
        vec!["list".to_owned()]
    }

    async fn verify(
        &self,
        record: &SourceRecord,
        app_config: &HashMap<String, Value>,
    ) -> Result<HashMap<String, Value>, SourceError> {
        let path_str = record
            .config
            .get("path")
            .or_else(|| app_config.get("path"))
            .and_then(|v| v.as_str())
            .ok_or_else(|| SourceError::Unavailable("directory path required in config".into()))?;

        let path = Path::new(path_str);
        if path.is_symlink() {
            return Err(SourceError::Unavailable("symlink directory targets are not supported".into()));
        }
        if !path.exists() {
            return Err(SourceError::Unavailable(format!("directory does not exist: {path_str}")));
        }
        if !path.is_dir() {
            return Err(SourceError::Unavailable(format!("path is not a directory: {path_str}")));
        }
        let canonical = path
            .canonicalize()
            .map(|p| p.display().to_string())
            .unwrap_or_else(|_| path_str.to_owned());

        let mut result = HashMap::new();
        result.insert("reachable".into(), Value::Bool(true));
        result.insert("path".into(), Value::String(canonical));
        result.insert("is_dir".into(), Value::Bool(true));
        Ok(result)
    }

    async fn sync(
        &self,
        record: &SourceRecord,
        app_config: &HashMap<String, Value>,
    ) -> Result<Vec<HashMap<String, Value>>, SourceError> {
        let path_str = record
            .config
            .get("path")
            .or_else(|| app_config.get("path"))
            .and_then(|v| v.as_str())
            .ok_or_else(|| SourceError::Io("directory path required".into()))?;

        let path = Path::new(path_str);
        if path.is_symlink() {
            return Err(SourceError::Io("symlink directory targets are not supported".into()));
        }
        if !path.is_dir() {
            return Err(SourceError::Io(format!("not a directory: {path_str}")));
        }

        let skip_hidden = record
            .config
            .get("skip_hidden")
            .or_else(|| app_config.get("skip_hidden"))
            .and_then(|v| v.as_bool())
            .unwrap_or(false);

        let max_files = record
            .config
            .get("max_files")
            .and_then(|v| v.as_u64())
            .map(|n| n as usize)
            .unwrap_or(self.max_files)
            .min(self.max_files);

        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map(|d| d.as_secs_f64())
            .unwrap_or(0.0);

        let mut rows = Vec::new();
        let entries = std::fs::read_dir(path)
            .map_err(|e| SourceError::Io(e.to_string()))?;

        for entry in entries {
            if rows.len() >= max_files {
                break;
            }
            let entry = match entry {
                Ok(e) => e,
                Err(_) => continue,
            };
            // Skip symlinks.
            let meta = match entry.metadata() {
                Ok(m) => m,
                Err(_) => continue,
            };
            if meta.file_type().is_symlink() {
                continue;
            }
            let name = entry.file_name().to_string_lossy().into_owned();
            if skip_hidden && name.starts_with('.') {
                continue;
            }

            let mut row = HashMap::new();
            row.insert("name".into(), Value::String(name));
            row.insert("path".into(), Value::String(entry.path().display().to_string()));
            row.insert("is_dir".into(), Value::Bool(meta.is_dir()));
            row.insert("is_file".into(), Value::Bool(meta.is_file()));
            row.insert("size_bytes".into(), Value::Number(meta.len().into()));
            row.insert("source_id".into(), Value::String(record.id.clone()));
            row.insert("observed_at".into(), Value::Number(
                serde_json::Number::from_f64(now).unwrap_or(serde_json::Number::from(0))
            ));
            rows.push(row);
        }

        Ok(rows)
    }

    async fn act(
        &self,
        record: &SourceRecord,
        app_config: &HashMap<String, Value>,
        action: &str,
        _payload: &HashMap<String, Value>,
    ) -> Result<HashMap<String, Value>, SourceError> {
        if action == "list" {
            let rows = self.sync(record, app_config).await?;
            let mut result = HashMap::new();
            result.insert("rows".into(), Value::Array(
                rows.into_iter()
                    .map(|r| Value::Object(r.into_iter().collect()))
                    .collect()
            ));
            return Ok(result);
        }
        Err(SourceError::ActDenied(format!("action '{action}' not supported")))
    }
}
