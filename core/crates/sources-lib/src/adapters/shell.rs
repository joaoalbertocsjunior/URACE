//! ShellAdapter — observe stdout of a command.
//!
//! SECURITY: Never uses `sh -c` or passes user-supplied strings to a shell.
//! The command string is split on whitespace and each token is passed as an
//! explicit argument to `std::process::Command`. Shell metacharacters are
//! never interpreted.

use crate::adapter::{SourceAdapter, SourceError, SourceRecord};
use async_trait::async_trait;
use serde_json::{json, Value};
use std::collections::HashMap;
use std::time::{SystemTime, UNIX_EPOCH};

pub struct ShellAdapter;

impl ShellAdapter {
    fn now() -> f64 {
        SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map(|d| d.as_secs_f64())
            .unwrap_or(0.0)
    }

    fn run_command(record: &SourceRecord) -> Result<HashMap<String, Value>, SourceError> {
        let cmd_str = record
            .config
            .get("command")
            .and_then(|v| v.as_str())
            .ok_or_else(|| SourceError::Unavailable("config.command required".into()))?;

        // Split on whitespace — NEVER use sh -c.
        let mut parts = cmd_str.split_whitespace();
        let program = parts.next().ok_or_else(|| SourceError::Unavailable("empty command".into()))?;
        let args: Vec<&str> = parts.collect();

        let timeout_secs = record
            .config
            .get("timeout")
            .and_then(|v| v.as_u64())
            .unwrap_or(30);

        let output = std::process::Command::new(program)
            .args(&args)
            .output()
            .map_err(|e| SourceError::Unavailable(format!("command failed to start: {e}")))?;

        // Honour timeout via a wall-clock post-check is not needed here because
        // `Command::output()` is synchronous. For true timeout enforcement callers
        // should wrap in `tokio::time::timeout` at the registry level.
        let _ = timeout_secs;

        let mut row = HashMap::new();
        row.insert("stdout".into(), Value::String(String::from_utf8_lossy(&output.stdout).into_owned()));
        row.insert("stderr".into(), Value::String(String::from_utf8_lossy(&output.stderr).into_owned()));
        row.insert("returncode".into(), Value::Number(output.status.code().unwrap_or(-1).into()));
        row.insert(
            "observed_at".into(),
            Value::Number(serde_json::Number::from_f64(Self::now()).unwrap_or(serde_json::Number::from(0))),
        );
        Ok(row)
    }
}

#[async_trait]
impl SourceAdapter for ShellAdapter {
    fn config_schema(&self) -> Value {
        json!({
            "type": "object",
            "required": ["command"],
            "properties": {
                "command": {"type": "string"},
                "timeout": {"type": "integer"}
            }
        })
    }

    fn actions(&self) -> Vec<String> {
        vec!["run".into()]
    }

    async fn verify(
        &self,
        record: &SourceRecord,
        _app_config: &HashMap<String, Value>,
    ) -> Result<HashMap<String, Value>, SourceError> {
        let cmd_str = record
            .config
            .get("command")
            .and_then(|v| v.as_str())
            .unwrap_or("");
        let program = cmd_str.split_whitespace().next().unwrap_or("");
        // Check the executable is accessible via PATH without running it.
        let found = which_in_path(program);
        let mut m = HashMap::new();
        m.insert("ok".into(), Value::Bool(found));
        m.insert("command".into(), Value::String(program.to_owned()));
        Ok(m)
    }

    async fn sync(
        &self,
        record: &SourceRecord,
        _app_config: &HashMap<String, Value>,
    ) -> Result<Vec<HashMap<String, Value>>, SourceError> {
        let row = Self::run_command(record)?;
        Ok(vec![row])
    }

    async fn act(
        &self,
        record: &SourceRecord,
        _app_config: &HashMap<String, Value>,
        action: &str,
        _payload: &HashMap<String, Value>,
    ) -> Result<HashMap<String, Value>, SourceError> {
        if action == "run" {
            return Self::run_command(record);
        }
        Err(SourceError::ActDenied(format!("action '{action}' not supported")))
    }
}

/// Check whether `program` resolves in PATH without shell expansion.
fn which_in_path(program: &str) -> bool {
    if program.is_empty() {
        return false;
    }
    // If the program contains a path separator it is an explicit path.
    if program.contains('/') {
        return std::path::Path::new(program).is_file();
    }
    if let Ok(path_var) = std::env::var("PATH") {
        for dir in path_var.split(':') {
            let candidate = std::path::Path::new(dir).join(program);
            if candidate.is_file() {
                return true;
            }
        }
    }
    false
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::adapter::SourceRecord;

    fn record_for(cmd: &str) -> SourceRecord {
        let mut config = HashMap::new();
        config.insert("command".into(), Value::String(cmd.into()));
        SourceRecord::new("shell-test", "shell", config)
    }

    #[tokio::test]
    async fn echo_works() {
        let adapter = ShellAdapter;
        let record = record_for("echo hello");
        let rows = adapter.sync(&record, &HashMap::new()).await.unwrap();
        assert_eq!(rows.len(), 1);
        assert!(rows[0]["stdout"].as_str().unwrap().contains("hello"));
    }

    #[tokio::test]
    async fn unsupported_action_rejected() {
        let adapter = ShellAdapter;
        let record = record_for("echo hi");
        let err = adapter.act(&record, &HashMap::new(), "dangerous", &HashMap::new()).await;
        assert!(matches!(err, Err(SourceError::ActDenied(_))));
    }

    #[test]
    fn no_shell_injection() {
        // The adapter must split on whitespace only, never invoke sh -c.
        // A semicolon in the command should be passed as a literal argument,
        // not interpreted as a shell separator.
        let record = record_for("echo hello;id");
        let result = ShellAdapter::run_command(&record).unwrap();
        // The literal string "hello;id" should appear in stdout.
        let stdout = result["stdout"].as_str().unwrap_or("");
        assert!(stdout.contains("hello;id"), "stdout was: {stdout:?}");
    }
}
