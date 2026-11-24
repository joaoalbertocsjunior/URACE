//! CodebaseAdapter — scans a git repository and reports file/commit stats.
//!
//! Rust port of `source_adapters/codebase.py`.
//! Uses `git2` (already a workspace dep) to open the repo and walk commits.

use crate::adapter::{SourceAdapter, SourceError, SourceRecord};
use async_trait::async_trait;
use serde_json::{json, Value};
use std::collections::HashMap;
use std::path::Path;
use std::time::{SystemTime, UNIX_EPOCH};

const CODE_EXTENSIONS: &[&str] = &[
    ".py", ".js", ".ts", ".java", ".go", ".rb", ".rs", ".c", ".cpp", ".h",
    ".cs", ".swift", ".kt", ".scala", ".sh", ".bash", ".php",
];

pub struct CodebaseAdapter;

impl CodebaseAdapter {
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
impl SourceAdapter for CodebaseAdapter {
    fn config_schema(&self) -> Value {
        json!({
            "type": "object",
            "required": ["path"],
            "properties": {
                "path": {"type": "string", "description": "Absolute path to git repo root"}
            }
        })
    }

    fn actions(&self) -> Vec<String> {
        vec!["list_files".into(), "head_commit".into()]
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
                let head = repo.head().ok().and_then(|h| h.peel_to_commit().ok());
                let head_sha = head.map(|c| c.id().to_string()).unwrap_or_default();
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

        let repo = git2::Repository::open(&path_str)
            .map_err(|e| SourceError::Unavailable(format!("git open: {e}")))?;

        // HEAD commit info.
        let head = repo
            .head()
            .map_err(|e| SourceError::Unavailable(format!("git head: {e}")))?;
        let head_commit = head
            .peel_to_commit()
            .map_err(|e| SourceError::Unavailable(format!("peel to commit: {e}")))?;
        let head_sha = head_commit.id().to_string();
        let head_message = head_commit
            .message()
            .unwrap_or("")
            .lines()
            .next()
            .unwrap_or("")
            .to_owned();

        // Count commits on HEAD.
        let mut revwalk = repo
            .revwalk()
            .map_err(|e| SourceError::Io(format!("revwalk: {e}")))?;
        revwalk
            .push_head()
            .map_err(|e| SourceError::Io(format!("push head: {e}")))?;
        let commit_count = revwalk.count();

        // Walk work-tree files and count by extension.
        let workdir = repo
            .workdir()
            .ok_or_else(|| SourceError::Unavailable("bare repo not supported".into()))?;
        let mut file_count: usize = 0;
        let mut lang_counts: HashMap<String, usize> = HashMap::new();
        count_files(workdir, &mut file_count, &mut lang_counts);

        let languages: Vec<Value> = {
            let mut pairs: Vec<(&String, &usize)> = lang_counts.iter().collect();
            pairs.sort_by(|a, b| b.1.cmp(a.1));
            pairs.into_iter().map(|(k, _)| Value::String(k.clone())).collect()
        };

        let mut row = HashMap::new();
        row.insert("path".into(), Value::String(path_str));
        row.insert("head_sha".into(), Value::String(head_sha));
        row.insert("head_message".into(), Value::String(head_message));
        row.insert("commit_count".into(), json!(commit_count));
        row.insert("file_count".into(), json!(file_count));
        row.insert("languages".into(), Value::Array(languages));
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
        match action {
            "list_files" | "head_commit" => {
                let rows = self.sync(record, app_config).await?;
                let row = rows.into_iter().next().unwrap_or_default();
                Ok(row)
            }
            _ => Err(SourceError::ActDenied(format!("action '{action}' not supported"))),
        }
    }
}

/// Recursively count code files under `dir`.
fn count_files(dir: &Path, file_count: &mut usize, lang_counts: &mut HashMap<String, usize>) {
    let entries = match std::fs::read_dir(dir) {
        Ok(e) => e,
        Err(_) => return,
    };
    for entry in entries.flatten() {
        // Skip hidden dirs (e.g. .git).
        let name = entry.file_name();
        let name_str = name.to_string_lossy();
        if name_str.starts_with('.') {
            continue;
        }
        let path = entry.path();
        if path.is_dir() {
            count_files(&path, file_count, lang_counts);
        } else if path.is_file() {
            if let Some(ext) = path.extension().and_then(|e| e.to_str()) {
                let ext_dot = format!(".{ext}");
                if CODE_EXTENSIONS.contains(&ext_dot.as_str()) {
                    *file_count += 1;
                    *lang_counts.entry(ext_dot).or_default() += 1;
                }
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn verify_valid_git_repo() {
        // Use the URACE repo itself as a known valid git repo.
        let mut config = HashMap::new();
        config.insert("path".into(), Value::String("/home/host/Desktop/URACE".into()));
        let record = SourceRecord::new("cb-test", "codebase", config);
        let adapter = CodebaseAdapter;
        let result = adapter.verify(&record, &HashMap::new()).await.unwrap();
        assert_eq!(result["ok"], json!(true), "verify result: {result:?}");
    }

    #[tokio::test]
    async fn verify_nonexistent_path() {
        let mut config = HashMap::new();
        config.insert("path".into(), Value::String("/nonexistent/path".into()));
        let record = SourceRecord::new("cb-test", "codebase", config);
        let adapter = CodebaseAdapter;
        let result = adapter.verify(&record, &HashMap::new()).await.unwrap();
        assert_eq!(result["ok"], json!(false));
    }

    #[tokio::test]
    async fn sync_valid_git_repo() {
        let mut config = HashMap::new();
        config.insert("path".into(), Value::String("/home/host/Desktop/URACE".into()));
        let record = SourceRecord::new("cb-test", "codebase", config);
        let adapter = CodebaseAdapter;
        let rows = adapter.sync(&record, &HashMap::new()).await.unwrap();
        assert_eq!(rows.len(), 1);
        assert!(rows[0].contains_key("head_sha"));
        assert!(rows[0].contains_key("commit_count"));
        assert!(rows[0].contains_key("file_count"));
    }
}
