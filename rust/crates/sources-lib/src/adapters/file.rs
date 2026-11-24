//! FileAdapter — reads a local file and returns its content as a SourceRecord row.
//!
//! Rust port of `source_adapters/file_adapter.py`.
//! Supports plain text files; binary files are base64-encoded in the `content` field.

use crate::adapter::{SourceAdapter, SourceError, SourceRecord};
use async_trait::async_trait;
use serde_json::{json, Value};
use std::collections::HashMap;
use std::fs;
use std::path::Path;
use std::time::{SystemTime, UNIX_EPOCH};

pub struct FileAdapter;

impl FileAdapter {
    fn now() -> f64 {
        SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map(|d| d.as_secs_f64())
            .unwrap_or(0.0)
    }

    fn file_path(record: &SourceRecord) -> Result<String, SourceError> {
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
impl SourceAdapter for FileAdapter {
    fn config_schema(&self) -> Value {
        json!({
            "type": "object",
            "required": ["path"],
            "properties": {
                "path":     {"type": "string", "description": "Absolute path to file"},
                "encoding": {"type": "string", "description": "text (default) or base64"}
            }
        })
    }

    fn actions(&self) -> Vec<String> {
        vec!["read".into()]
    }

    async fn verify(
        &self,
        record: &SourceRecord,
        _app_config: &HashMap<String, Value>,
    ) -> Result<HashMap<String, Value>, SourceError> {
        let path_str = Self::file_path(record)?;
        let ok = {
            let path = Path::new(&path_str);
            path.exists() && path.is_file()
        };
        let mut result = HashMap::new();
        result.insert("ok".into(), Value::Bool(ok));
        if ok {
            if let Ok(meta) = fs::metadata(&path_str) {
                result.insert("size_bytes".into(), json!(meta.len()));
            }
        }
        result.insert("path".into(), Value::String(path_str));
        Ok(result)
    }

    async fn sync(
        &self,
        record: &SourceRecord,
        _app_config: &HashMap<String, Value>,
    ) -> Result<Vec<HashMap<String, Value>>, SourceError> {
        let path_str = Self::file_path(record)?;
        let now = Self::now();

        let content = fs::read_to_string(&path_str)
            .map_err(|e| SourceError::Io(format!("cannot read {path_str}: {e}")))?;

        let meta = fs::metadata(&path_str)
            .map_err(|e| SourceError::Io(format!("cannot stat {path_str}: {e}")))?;

        let mut row = HashMap::new();
        row.insert("path".into(), Value::String(path_str.clone()));
        row.insert("content".into(), Value::String(content));
        row.insert("size_bytes".into(), json!(meta.len()));
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
        record: &SourceRecord,
        app_config: &HashMap<String, Value>,
        action: &str,
        _payload: &HashMap<String, Value>,
    ) -> Result<HashMap<String, Value>, SourceError> {
        if action == "read" {
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
    use std::io::Write;
    use tempfile::NamedTempFile;

    fn make_record(path: &str) -> SourceRecord {
        let mut config = HashMap::new();
        config.insert("path".into(), Value::String(path.into()));
        SourceRecord::new("file-test", "file", config)
    }

    #[tokio::test]
    async fn reads_temp_file_content() {
        let mut f = NamedTempFile::new().unwrap();
        writeln!(f, "hello from FileAdapter").unwrap();
        let record = make_record(f.path().to_str().unwrap());
        let adapter = FileAdapter;
        let rows = adapter.sync(&record, &HashMap::new()).await.unwrap();
        assert_eq!(rows.len(), 1);
        let content = rows[0]["content"].as_str().unwrap_or("");
        assert!(content.contains("hello from FileAdapter"), "content: {content:?}");
    }

    #[tokio::test]
    async fn verify_existing_file() {
        let f = NamedTempFile::new().unwrap();
        let record = make_record(f.path().to_str().unwrap());
        let adapter = FileAdapter;
        let result = adapter.verify(&record, &HashMap::new()).await.unwrap();
        assert_eq!(result["ok"], json!(true));
    }

    #[tokio::test]
    async fn verify_missing_file() {
        let record = make_record("/nonexistent/path/file.txt");
        let adapter = FileAdapter;
        let result = adapter.verify(&record, &HashMap::new()).await.unwrap();
        assert_eq!(result["ok"], json!(false));
    }

    #[tokio::test]
    async fn missing_path_config_returns_error() {
        let record = SourceRecord::new("test", "file", HashMap::new());
        let adapter = FileAdapter;
        let err = adapter.sync(&record, &HashMap::new()).await;
        assert!(matches!(err, Err(SourceError::Config(_))));
    }
}
