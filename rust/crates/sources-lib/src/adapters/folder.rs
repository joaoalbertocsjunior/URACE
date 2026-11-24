//! FolderAdapter — recursive glob scan of a local directory.
//!
//! Rust port of `source_adapters/folder.py`.
//! Unlike DirectoryAdapter (direct children only), FolderAdapter walks the
//! entire subtree matching a glob pattern.

use crate::adapter::{SourceAdapter, SourceError, SourceRecord};
use async_trait::async_trait;
use serde_json::{json, Value};
use std::collections::HashMap;
use std::path::Path;
use std::time::{SystemTime, UNIX_EPOCH};

pub struct FolderAdapter {
    max_files: usize,
}

impl FolderAdapter {
    pub fn new(max_files: usize) -> Self {
        FolderAdapter { max_files }
    }

    fn now() -> f64 {
        SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map(|d| d.as_secs_f64())
            .unwrap_or(0.0)
    }

    fn folder_path(record: &SourceRecord) -> Result<String, SourceError> {
        record
            .config
            .get("path")
            .and_then(|v| v.as_str())
            .filter(|s| !s.is_empty())
            .map(|s| s.to_owned())
            .ok_or_else(|| SourceError::Config("config.path required".into()))
    }

    /// Collect all files under `dir` recursively, up to `max`.
    fn walk_dir(dir: &Path, rows: &mut Vec<HashMap<String, Value>>, max: usize, source_id: &str, now: f64) {
        if rows.len() >= max {
            return;
        }
        let entries = match std::fs::read_dir(dir) {
            Ok(e) => e,
            Err(_) => return,
        };
        for entry in entries.flatten() {
            if rows.len() >= max {
                break;
            }
            let path = entry.path();
            // Skip symlinks.
            let meta = match entry.metadata() {
                Ok(m) => m,
                Err(_) => continue,
            };
            if meta.file_type().is_symlink() {
                continue;
            }
            if path.is_dir() {
                Self::walk_dir(&path, rows, max, source_id, now);
            } else if path.is_file() {
                let mut row = HashMap::new();
                row.insert("path".into(), Value::String(path.display().to_string()));
                row.insert(
                    "name".into(),
                    Value::String(
                        path.file_name()
                            .map(|n| n.to_string_lossy().into_owned())
                            .unwrap_or_default(),
                    ),
                );
                row.insert("size_bytes".into(), json!(meta.len()));
                row.insert("source_id".into(), Value::String(source_id.to_owned()));
                row.insert(
                    "observed_at".into(),
                    Value::Number(
                        serde_json::Number::from_f64(now)
                            .unwrap_or(serde_json::Number::from(0)),
                    ),
                );
                rows.push(row);
            }
        }
    }
}

impl Default for FolderAdapter {
    fn default() -> Self {
        FolderAdapter::new(5000)
    }
}

#[async_trait]
impl SourceAdapter for FolderAdapter {
    fn config_schema(&self) -> Value {
        json!({
            "type": "object",
            "required": ["path"],
            "properties": {
                "path":      {"type": "string", "description": "Absolute path to scan"},
                "max_files": {"type": "integer", "description": "Max files to return"}
            }
        })
    }

    fn actions(&self) -> Vec<String> {
        vec!["scan".into()]
    }

    async fn verify(
        &self,
        record: &SourceRecord,
        _app_config: &HashMap<String, Value>,
    ) -> Result<HashMap<String, Value>, SourceError> {
        let path_str = Self::folder_path(record)?;
        let path = Path::new(&path_str);
        let mut result = HashMap::new();
        let ok = path.exists() && path.is_dir() && !path.is_symlink();
        result.insert("ok".into(), Value::Bool(ok));
        result.insert("path".into(), Value::String(path_str));
        Ok(result)
    }

    async fn sync(
        &self,
        record: &SourceRecord,
        _app_config: &HashMap<String, Value>,
    ) -> Result<Vec<HashMap<String, Value>>, SourceError> {
        let path_str = Self::folder_path(record)?;
        let path = Path::new(&path_str);
        if !path.is_dir() {
            return Err(SourceError::Io(format!("not a directory: {path_str}")));
        }

        let max = record
            .config
            .get("max_files")
            .and_then(|v| v.as_u64())
            .map(|n| n as usize)
            .unwrap_or(self.max_files)
            .min(self.max_files);

        let now = Self::now();
        let mut rows = Vec::new();
        Self::walk_dir(path, &mut rows, max, &record.id, now);
        Ok(rows)
    }

    async fn act(
        &self,
        record: &SourceRecord,
        app_config: &HashMap<String, Value>,
        action: &str,
        _payload: &HashMap<String, Value>,
    ) -> Result<HashMap<String, Value>, SourceError> {
        if action == "scan" {
            let rows = self.sync(record, app_config).await?;
            let file_count = rows.len();
            let mut result = HashMap::new();
            result.insert("file_count".into(), json!(file_count));
            result.insert(
                "files".into(),
                Value::Array(
                    rows.into_iter()
                        .map(|r| Value::Object(r.into_iter().collect()))
                        .collect(),
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
    use tempfile::TempDir;

    fn setup_tempdir() -> TempDir {
        let dir = TempDir::new().unwrap();
        std::fs::write(dir.path().join("a.txt"), "hello").unwrap();
        std::fs::write(dir.path().join("b.txt"), "world").unwrap();
        let sub = dir.path().join("sub");
        std::fs::create_dir(&sub).unwrap();
        std::fs::write(sub.join("c.txt"), "nested").unwrap();
        dir
    }

    fn make_record(path: &str) -> SourceRecord {
        let mut config = HashMap::new();
        config.insert("path".into(), Value::String(path.into()));
        SourceRecord::new("folder-test", "folder", config)
    }

    #[tokio::test]
    async fn sync_walks_recursively() {
        let dir = setup_tempdir();
        let record = make_record(dir.path().to_str().unwrap());
        let adapter = FolderAdapter::default();
        let rows = adapter.sync(&record, &HashMap::new()).await.unwrap();
        // Should find a.txt, b.txt, sub/c.txt = 3 files.
        assert_eq!(rows.len(), 3, "rows: {rows:?}");
    }

    #[tokio::test]
    async fn verify_valid_dir() {
        let dir = TempDir::new().unwrap();
        let record = make_record(dir.path().to_str().unwrap());
        let adapter = FolderAdapter::default();
        let result = adapter.verify(&record, &HashMap::new()).await.unwrap();
        assert_eq!(result["ok"], json!(true));
    }

    #[tokio::test]
    async fn verify_missing_dir() {
        let record = make_record("/nonexistent");
        let adapter = FolderAdapter::default();
        let result = adapter.verify(&record, &HashMap::new()).await.unwrap();
        assert_eq!(result["ok"], json!(false));
    }

    #[tokio::test]
    async fn unsupported_action_rejected() {
        let dir = TempDir::new().unwrap();
        let record = make_record(dir.path().to_str().unwrap());
        let adapter = FolderAdapter::default();
        let err = adapter.act(&record, &HashMap::new(), "delete", &HashMap::new()).await;
        assert!(matches!(err, Err(SourceError::ActDenied(_))));
    }
}
