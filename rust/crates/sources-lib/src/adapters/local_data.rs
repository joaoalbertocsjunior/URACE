//! LocalDataAdapter — port of `urace/source_adapters/_data_transport_adapter.py`.
//!
//! Reads local files in JSON, JSONL, or CSV format.
//!
//! config_schema:
//!   - `path`: String — file path to read
//!   - `format`: String — one of "json", "jsonl", "csv"

use crate::adapter::{SourceAdapter, SourceError, SourceRecord};
use async_trait::async_trait;
use serde_json::{json, Value};
use std::collections::HashMap;
use std::fs;
use std::path::Path;
use std::time::{SystemTime, UNIX_EPOCH};

pub struct LocalDataAdapter;

impl LocalDataAdapter {
    fn file_path(record: &SourceRecord) -> Result<String, SourceError> {
        record
            .config
            .get("path")
            .and_then(|v| v.as_str())
            .filter(|s| !s.is_empty())
            .map(|s| s.to_owned())
            .ok_or_else(|| SourceError::Auth("config missing required field 'path'".into()))
    }

    fn format(record: &SourceRecord) -> String {
        record
            .config
            .get("format")
            .and_then(|v| v.as_str())
            .unwrap_or("jsonl")
            .to_lowercase()
    }

    fn now_secs() -> f64 {
        SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map(|d| d.as_secs_f64())
            .unwrap_or(0.0)
    }

    fn parse_json(contents: &str, source_id: &str) -> Result<Vec<HashMap<String, Value>>, SourceError> {
        let val: Value = serde_json::from_str(contents)
            .map_err(|e| SourceError::Io(format!("JSON parse error: {}", e)))?;
        let arr = match val {
            Value::Array(a) => a,
            other => vec![other],
        };
        let now = Self::now_secs();
        Ok(arr
            .into_iter()
            .map(|item| {
                let mut row: HashMap<String, Value> = match item {
                    Value::Object(m) => m.into_iter().collect(),
                    other => {
                        let mut m = HashMap::new();
                        m.insert("value".into(), other);
                        m
                    }
                };
                row.insert("source_id".into(), Value::String(source_id.to_string()));
                row.insert("observed_at".into(), json!(now));
                row
            })
            .collect())
    }

    fn parse_jsonl(contents: &str, source_id: &str) -> Result<Vec<HashMap<String, Value>>, SourceError> {
        let now = Self::now_secs();
        let mut rows = Vec::new();
        for (line_no, line) in contents.lines().enumerate() {
            let trimmed = line.trim();
            if trimmed.is_empty() { continue; }
            let val: Value = serde_json::from_str(trimmed)
                .map_err(|e| SourceError::Io(format!("JSONL line {} parse error: {}", line_no + 1, e)))?;
            let mut row: HashMap<String, Value> = match val {
                Value::Object(m) => m.into_iter().collect(),
                other => {
                    let mut m = HashMap::new();
                    m.insert("value".into(), other);
                    m
                }
            };
            row.insert("source_id".into(), Value::String(source_id.to_string()));
            row.insert("observed_at".into(), json!(now));
            rows.push(row);
        }
        Ok(rows)
    }

    fn parse_csv(contents: &str, source_id: &str) -> Result<Vec<HashMap<String, Value>>, SourceError> {
        let now = Self::now_secs();
        let mut lines = contents.lines();
        let header_line = match lines.next() {
            Some(h) => h,
            None => return Ok(vec![]),
        };
        let headers: Vec<&str> = header_line.split(',').map(|s| s.trim()).collect();

        let mut rows = Vec::new();
        for line in lines {
            let trimmed = line.trim();
            if trimmed.is_empty() { continue; }
            let values: Vec<&str> = trimmed.split(',').map(|s| s.trim()).collect();
            let mut row: HashMap<String, Value> = HashMap::new();
            for (i, header) in headers.iter().enumerate() {
                let val = values.get(i).copied().unwrap_or("");
                row.insert(header.to_string(), Value::String(val.to_string()));
            }
            row.insert("source_id".into(), Value::String(source_id.to_string()));
            row.insert("observed_at".into(), json!(now));
            rows.push(row);
        }
        Ok(rows)
    }
}

#[async_trait]
impl SourceAdapter for LocalDataAdapter {
    fn config_schema(&self) -> Value {
        json!({
            "type": "object",
            "required": ["path", "format"],
            "properties": {
                "path":   { "type": "string", "description": "Local file path to read" },
                "format": { "type": "string", "enum": ["json", "jsonl", "csv"], "description": "File format" }
            }
        })
    }

    fn actions(&self) -> Vec<String> {
        vec![]
    }

    /// Verify the file exists and is readable.
    async fn verify(
        &self,
        record: &SourceRecord,
        _app_config: &HashMap<String, Value>,
    ) -> Result<HashMap<String, Value>, SourceError> {
        let path_str = LocalDataAdapter::file_path(record)?;
        let path = Path::new(&path_str);
        let mut result = HashMap::new();
        if path.exists() && path.is_file() {
            // Check readable.
            match fs::metadata(path) {
                Ok(_) => {
                    result.insert("ok".into(), Value::Bool(true));
                    result.insert("path".into(), Value::String(path_str));
                }
                Err(e) => {
                    result.insert("ok".into(), Value::Bool(false));
                    result.insert("error".into(), Value::String(e.to_string()));
                }
            }
        } else {
            result.insert("ok".into(), Value::Bool(false));
            result.insert("error".into(), Value::String(format!("file not found: {}", path_str)));
        }
        Ok(result)
    }

    /// LocalDataAdapter does not support any actions (read-only).
    async fn act(
        &self,
        _record: &SourceRecord,
        _app_config: &HashMap<String, Value>,
        action: &str,
        _payload: &HashMap<String, Value>,
    ) -> Result<HashMap<String, Value>, SourceError> {
        Err(SourceError::ActDenied(format!(
            "LocalDataAdapter does not support action '{}' (read-only source)",
            action
        )))
    }

    /// Read and parse the file, returning rows.
    async fn sync(
        &self,
        record: &SourceRecord,
        _app_config: &HashMap<String, Value>,
    ) -> Result<Vec<HashMap<String, Value>>, SourceError> {
        let path_str = LocalDataAdapter::file_path(record)?;
        let format = LocalDataAdapter::format(record);

        let contents = fs::read_to_string(&path_str)
            .map_err(|e| SourceError::Io(format!("cannot read {}: {}", path_str, e)))?;

        match format.as_str() {
            "json" => LocalDataAdapter::parse_json(&contents, &record.id),
            "jsonl" => LocalDataAdapter::parse_jsonl(&contents, &record.id),
            "csv" => LocalDataAdapter::parse_csv(&contents, &record.id),
            other => Err(SourceError::Io(format!("unknown format: {}", other))),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::adapter::SourceRecord;
    use serde_json::json;
    use std::io::Write;
    use tempfile::NamedTempFile;

    fn make_record(path: &str, format: &str) -> SourceRecord {
        let mut config = HashMap::new();
        config.insert("path".into(), json!(path));
        config.insert("format".into(), json!(format));
        SourceRecord::new("test-id", "local_data", config)
    }

    #[tokio::test]
    async fn test_verify_existing_file() {
        let mut f = NamedTempFile::new().unwrap();
        writeln!(f, "{{}}").unwrap();
        let record = make_record(f.path().to_str().unwrap(), "jsonl");
        let adapter = LocalDataAdapter;
        let result = adapter.verify(&record, &HashMap::new()).await.unwrap();
        assert_eq!(result["ok"], json!(true));
    }

    #[tokio::test]
    async fn test_verify_missing_file() {
        let record = make_record("/nonexistent/path/file.jsonl", "jsonl");
        let adapter = LocalDataAdapter;
        let result = adapter.verify(&record, &HashMap::new()).await.unwrap();
        assert_eq!(result["ok"], json!(false));
    }

    #[tokio::test]
    async fn test_sync_jsonl() {
        let mut f = NamedTempFile::new().unwrap();
        writeln!(f, r#"{{"key":"val1"}}"#).unwrap();
        writeln!(f, r#"{{"key":"val2"}}"#).unwrap();
        let record = make_record(f.path().to_str().unwrap(), "jsonl");
        let adapter = LocalDataAdapter;
        let rows = adapter.sync(&record, &HashMap::new()).await.unwrap();
        assert_eq!(rows.len(), 2);
        assert_eq!(rows[0]["key"], json!("val1"));
    }

    #[tokio::test]
    async fn test_sync_json_array() {
        let mut f = NamedTempFile::new().unwrap();
        writeln!(f, r#"[{{"a":1}},{{"a":2}}]"#).unwrap();
        let record = make_record(f.path().to_str().unwrap(), "json");
        let adapter = LocalDataAdapter;
        let rows = adapter.sync(&record, &HashMap::new()).await.unwrap();
        assert_eq!(rows.len(), 2);
    }

    #[tokio::test]
    async fn test_sync_csv() {
        let mut f = NamedTempFile::new().unwrap();
        writeln!(f, "name,age").unwrap();
        writeln!(f, "alice,30").unwrap();
        writeln!(f, "bob,25").unwrap();
        let record = make_record(f.path().to_str().unwrap(), "csv");
        let adapter = LocalDataAdapter;
        let rows = adapter.sync(&record, &HashMap::new()).await.unwrap();
        assert_eq!(rows.len(), 2);
        assert_eq!(rows[0]["name"], json!("alice"));
        assert_eq!(rows[1]["age"], json!("25"));
    }
}
