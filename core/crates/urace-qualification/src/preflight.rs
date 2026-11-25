//! Non-blocking startup hints: state format compatibility and pending improvement signals.

use serde::{Deserialize, Serialize};
use std::path::Path;
use thiserror::Error;

#[derive(Debug, Error)]
pub enum PreflightError {
    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),
    #[error("JSON error: {0}")]
    Json(#[from] serde_json::Error),
}

/// Severity of a preflight hint.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "UPPERCASE")]
pub enum HintLevel {
    Info,
    Warning,
    Error,
}

/// A single preflight diagnostic hint.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Hint {
    pub level: HintLevel,
    pub code: String,
    pub message: String,
    pub action: String,
}

/// Current and minimum supported state-format versions.
pub const FORMAT_VERSION: u64 = 2;
pub const MIN_FORMAT_VERSION: u64 = 1;

/// Collect all preflight hints for the given config and product root.
///
/// Never panics — returns an empty list on any internal error.
pub fn hints(config: &serde_json::Value, root: &Path) -> Vec<Hint> {
    let mut result = Vec::new();
    format_hints(config, &mut result);
    improvement_hints(root, &mut result);
    result
}

fn format_hints(config: &serde_json::Value, result: &mut Vec<Hint>) {
    let state_path = match state_path_from_config(config) {
        Some(p) => p,
        None => return,
    };
    if !state_path.exists() {
        return;
    }
    let sv: u64 = match (|| -> Result<u64, Box<dyn std::error::Error>> {
        let text = std::fs::read_to_string(&state_path)?;
        let v: serde_json::Value = serde_json::from_str(&text)?;
        Ok(v.get("schema_version")
            .and_then(|x| x.as_u64())
            .unwrap_or(1))
    })() {
        Ok(v) => v,
        Err(_) => return,
    };

    if sv < MIN_FORMAT_VERSION {
        result.push(Hint {
            level: HintLevel::Warning,
            code: "FORMAT_TOO_OLD".to_owned(),
            message: format!(
                "State format {sv} predates minimum {MIN_FORMAT_VERSION}; migration required"
            ),
            action: "urace check --migration-dry-run".to_owned(),
        });
    } else if sv > FORMAT_VERSION {
        result.push(Hint {
            level: HintLevel::Warning,
            code: "FORMAT_NEWER".to_owned(),
            message: format!(
                "State was written by a newer runtime (format {sv}); this runtime may misread it"
            ),
            action: "upgrade urace to match the state format version".to_owned(),
        });
    }
}

fn improvement_hints(root: &Path, result: &mut Vec<Hint>) {
    let trial = root.join("trial");
    // Absorb all errors — preflight must never block startup.
    if let Ok(exists) = trial.join("runtime-deployment-pending.json").try_exists() {
        if exists {
            result.push(Hint {
                level: HintLevel::Info,
                code: "IMPROVEMENT_READY".to_owned(),
                message: "Runtime improvement qualified and pending deployment".to_owned(),
                action: "urace watch report".to_owned(),
            });
            return;
        }
    }
    let cycle_file = trial.join("runtime-cycle-latest.json");
    if let Ok(true) = cycle_file.try_exists() {
        if let Ok(text) = std::fs::read_to_string(&cycle_file) {
            if let Ok(v) = serde_json::from_str::<serde_json::Value>(&text) {
                if v.get("stage").and_then(|s| s.as_str()) == Some("AWAITING_APPROVAL") {
                    result.push(Hint {
                        level: HintLevel::Info,
                        code: "IMPROVEMENT_AWAITING_APPROVAL".to_owned(),
                        message: "Runtime improvement awaiting owner approval".to_owned(),
                        action: "urace watch report".to_owned(),
                    });
                }
            }
        }
    }
}

fn state_path_from_config(config: &serde_json::Value) -> Option<std::path::PathBuf> {
    config
        .get("state_path")
        .and_then(|v| v.as_str())
        .map(std::path::PathBuf::from)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write;
    use tempfile::TempDir;

    fn write_json(path: &std::path::Path, v: &serde_json::Value) {
        let mut f = std::fs::File::create(path).unwrap();
        write!(f, "{}", serde_json::to_string(v).unwrap()).unwrap();
    }

    #[test]
    fn no_hints_on_empty_root() {
        let dir = TempDir::new().unwrap();
        let config = serde_json::json!({});
        let h = hints(&config, dir.path());
        assert!(h.is_empty());
    }

    #[test]
    fn format_too_old_hint() {
        let dir = TempDir::new().unwrap();
        let state = dir.path().join("state.json");
        write_json(&state, &serde_json::json!({"schema_version": 0}));
        let config = serde_json::json!({"state_path": state.to_str().unwrap()});
        let h = hints(&config, dir.path());
        assert!(h.iter().any(|x| x.code == "FORMAT_TOO_OLD"));
    }

    #[test]
    fn format_newer_hint() {
        let dir = TempDir::new().unwrap();
        let state = dir.path().join("state.json");
        write_json(&state, &serde_json::json!({"schema_version": 999}));
        let config = serde_json::json!({"state_path": state.to_str().unwrap()});
        let h = hints(&config, dir.path());
        assert!(h.iter().any(|x| x.code == "FORMAT_NEWER"));
    }

    #[test]
    fn improvement_ready_hint() {
        let dir = TempDir::new().unwrap();
        std::fs::create_dir_all(dir.path().join("trial")).unwrap();
        std::fs::write(
            dir.path().join("trial/runtime-deployment-pending.json"),
            b"{}",
        )
        .unwrap();
        let h = hints(&serde_json::json!({}), dir.path());
        assert!(h.iter().any(|x| x.code == "IMPROVEMENT_READY"));
    }

    #[test]
    fn awaiting_approval_hint() {
        let dir = TempDir::new().unwrap();
        std::fs::create_dir_all(dir.path().join("trial")).unwrap();
        write_json(
            &dir.path().join("trial/runtime-cycle-latest.json"),
            &serde_json::json!({"stage": "AWAITING_APPROVAL"}),
        );
        let h = hints(&serde_json::json!({}), dir.path());
        assert!(h.iter().any(|x| x.code == "IMPROVEMENT_AWAITING_APPROVAL"));
    }
}
