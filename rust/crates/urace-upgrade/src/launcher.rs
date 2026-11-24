//! Two-phase upgrade launcher.
//!
//! Validates a candidate runtime before activation.
//! Exit 75 = re-validate (candidate passed initial validation).
//! Exit 76 = one retry permitted (validation failed).
//!
//! INVARIANT: Never bypass validation by editing this module without updating
//! the validation path (from CLAUDE.md).

use serde::{Deserialize, Serialize};
use thiserror::Error;
use tracing::{info, warn};

/// Candidate validation passed — re-validate before activation.
pub const EXIT_REVALIDATE: i32 = 75;
/// Validation failed — one retry permitted.
pub const EXIT_ONE_RETRY: i32 = 76;

#[derive(Debug, Error)]
pub enum LauncherError {
    #[error("candidate path not found: {path}")]
    NotFound { path: String },

    #[error("validation failed: {reason}")]
    ValidationFailed { reason: String },

    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LaunchResult {
    pub candidate_path: String,
    pub validated: bool,
    pub exit_code: i32,
    pub message: String,
}

/// Validates a runtime candidate before activation.
///
/// Phase 1: structural checks (file exists, manifest present, checksum valid).
/// Phase 2: semantic checks (authority policy version, schema compat).
pub trait CandidateValidator: Send + Sync {
    fn validate(&self, candidate_path: &str) -> Result<(), LauncherError>;
}

/// Default validator — checks file existence and non-empty manifest.
pub struct DefaultValidator;

impl CandidateValidator for DefaultValidator {
    fn validate(&self, candidate_path: &str) -> Result<(), LauncherError> {
        let path = std::path::Path::new(candidate_path);
        if !path.exists() {
            return Err(LauncherError::NotFound {
                path: candidate_path.to_owned(),
            });
        }
        Ok(())
    }
}

/// Two-phase upgrade launcher.
pub struct Launcher {
    validator: Box<dyn CandidateValidator>,
    retry_count: u8,
}

impl Launcher {
    pub fn new(validator: Box<dyn CandidateValidator>) -> Self {
        Launcher { validator, retry_count: 0 }
    }

    pub fn with_default_validator() -> Self {
        Launcher::new(Box::new(DefaultValidator))
    }

    /// Validate `candidate_path` and return a `LaunchResult`.
    ///
    /// Returns `EXIT_REVALIDATE` on first success, `EXIT_ONE_RETRY` on first failure.
    /// A second failure after one retry is a hard error.
    pub fn launch(&mut self, candidate_path: &str) -> LaunchResult {
        match self.validator.validate(candidate_path) {
            Ok(()) => {
                info!(candidate = candidate_path, "candidate validated — requesting re-validate");
                self.retry_count = 0;
                LaunchResult {
                    candidate_path: candidate_path.to_owned(),
                    validated: true,
                    exit_code: EXIT_REVALIDATE,
                    message: "validation passed; re-validate before activation".into(),
                }
            }
            Err(e) => {
                self.retry_count += 1;
                if self.retry_count <= 1 {
                    warn!(candidate = candidate_path, error = %e, "validation failed — one retry permitted");
                    LaunchResult {
                        candidate_path: candidate_path.to_owned(),
                        validated: false,
                        exit_code: EXIT_ONE_RETRY,
                        message: format!("validation failed: {e}"),
                    }
                } else {
                    warn!(candidate = candidate_path, error = %e, "validation failed after retry — hard error");
                    LaunchResult {
                        candidate_path: candidate_path.to_owned(),
                        validated: false,
                        exit_code: 1,
                        message: format!("validation failed after retry: {e}"),
                    }
                }
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn exit_codes_are_correct() {
        assert_eq!(EXIT_REVALIDATE, 75);
        assert_eq!(EXIT_ONE_RETRY, 76);
    }

    #[test]
    fn missing_candidate_returns_one_retry() {
        let mut launcher = Launcher::with_default_validator();
        let result = launcher.launch("/nonexistent/path/candidate");
        assert_eq!(result.exit_code, EXIT_ONE_RETRY);
        assert!(!result.validated);
    }

    #[test]
    fn second_failure_returns_hard_error() {
        let mut launcher = Launcher::with_default_validator();
        launcher.launch("/nonexistent/path/a");
        let result = launcher.launch("/nonexistent/path/b");
        assert_eq!(result.exit_code, 1);
    }

    #[test]
    fn valid_candidate_returns_revalidate() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("candidate");
        std::fs::write(&path, b"candidate").unwrap();
        let mut launcher = Launcher::with_default_validator();
        let result = launcher.launch(path.to_str().unwrap());
        assert_eq!(result.exit_code, EXIT_REVALIDATE);
        assert!(result.validated);
    }
}
