#![allow(dead_code)]

use std::process::Command;

use async_trait::async_trait;

use crate::adapter::{AdapterError, SourceAdapter, SourceEvent};

/// Runs a shell command on each sync and emits stdout as an event.
pub struct ShellAdapter {
    id: String,
    /// The command to run (passed to `sh -c`).
    command: String,
}

impl ShellAdapter {
    pub fn new(id: impl Into<String>, command: impl Into<String>) -> Self {
        Self {
            id: id.into(),
            command: command.into(),
        }
    }
}

#[async_trait]
impl SourceAdapter for ShellAdapter {
    fn id(&self) -> &str {
        &self.id
    }

    fn kind(&self) -> &str {
        "shell"
    }

    async fn sync(&mut self) -> Result<Vec<SourceEvent>, AdapterError> {
        let output = Command::new("sh")
            .arg("-c")
            .arg(&self.command)
            .output()
            .map_err(AdapterError::Io)?;

        let stdout = String::from_utf8_lossy(&output.stdout).into_owned();
        let stderr = String::from_utf8_lossy(&output.stderr).into_owned();
        let exit_code = output.status.code().unwrap_or(-1);

        let payload = serde_json::json!({
            "command": self.command,
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": exit_code,
        });

        Ok(vec![SourceEvent {
            source_id: self.id.clone(),
            kind: "shell.output".to_owned(),
            payload,
            at_unix: unix_now(),
        }])
    }
}

fn unix_now() -> f64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs_f64())
        .unwrap_or(0.0)
}
