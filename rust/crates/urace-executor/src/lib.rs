//! R-8: Executor pool — sandboxed LLM-generated code execution.
//!
//! Invariants (from `execution_backend.py`):
//! - LLM-generated code must not execute without a sandbox boundary.
//! - Resource limits (CPU, memory, time) must be present and not user-controllable
//!   without authority verification.
//! - Credentials must not pass outside the executor's declared scope.
//! - Executors must not persist state beyond their declared session.

use serde::{Deserialize, Serialize};
use thiserror::Error;
use urace_authority::authority::{resolve, Objective};
use urace_types::AuthorityOutcome;
use std::collections::HashMap;
use serde_json::Value;

#[derive(Debug, Error)]
pub enum ExecutorError {
    #[error("authority denied execution: {0}")]
    AuthorityDenied(String),
    #[error("sandbox violation: {0}")]
    SandboxViolation(String),
    #[error("resource limit exceeded: {0}")]
    ResourceLimit(String),
    #[error("execution error: {0}")]
    Execution(String),
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecutionRequest {
    pub executor_id: String,
    pub scope: String,
    pub code: String,
    pub resource_limits: ResourceLimits,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResourceLimits {
    pub cpu_ms: u64,
    pub memory_mb: u64,
    pub timeout_secs: u64,
}

impl Default for ResourceLimits {
    fn default() -> Self {
        ResourceLimits { cpu_ms: 5000, memory_mb: 256, timeout_secs: 30 }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecutionResult {
    pub executor_id: String,
    pub success: bool,
    pub output: Option<String>,
    pub error: Option<String>,
    pub duration_ms: u64,
}

/// Validate an execution request against the authority gate before running.
///
/// Returns `Err(AuthorityDenied)` if the §62z gate denies execution.
pub fn authority_check(
    request: &ExecutionRequest,
    authority_config: &HashMap<String, Value>,
    constraints: &[String],
) -> Result<(), ExecutorError> {
    let obj = Objective {
        id: Some(request.executor_id.clone()),
        scope: request.scope.clone(),
        title: format!("execute code in scope {}", request.scope),
        reason: Some("executor pool request".into()),
        necessity_evidence: None,
        lower_impact_route_sufficient: None,
    };
    let resolution = resolve(&obj, authority_config, None, constraints);
    if !resolution.outcome.may_proceed() {
        return Err(ExecutorError::AuthorityDenied(
            format!("{:?}: {}", resolution.outcome, resolution.basis)
        ));
    }
    Ok(())
}
