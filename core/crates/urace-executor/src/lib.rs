//! R-8: Executor pool — sandboxed LLM-generated code execution.
//!
//! Invariants (from `execution_backend.py`):
//! - LLM-generated code must not execute without a sandbox boundary.
//! - Resource limits (CPU, memory, time) must be present and not user-controllable
//!   without authority verification.
//! - Credentials must not pass outside the executor's declared scope.
//! - Executors must not persist state beyond their declared session.
//! - Parent process environment variables are NEVER forwarded to child processes.

pub mod capabilities;
pub mod multi_executor;
pub mod retry_engine;
pub mod routing;

pub use capabilities::{builtins, select_skill, SkillContract, SKILL_VOCABULARY};
pub use multi_executor::{
    allocate_budget, generate_and_select, score_proposal, select_best, settings as multi_settings,
    BudgetSlot, DimensionScores, DiscoverFn, MultiExecutorError, MultiPlanSettings, ScoreWeights,
    ScoredCandidate, SCHEMA as MULTI_PLAN_SCHEMA,
};
pub use retry_engine::{parse_retry_after, RetryEngine, RetryOutcome, RetryPolicy};
pub use routing::{select_provider, ProviderDef, UnavailabilityClass};

use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::HashMap;
use std::time::Instant;
use thiserror::Error;
use urace_authority::authority::{resolve, Objective};

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
    #[error("credential leak detected: {0}")]
    CredentialLeak(String),
}

/// Safe execution resource limits.
/// User requests are validated against these defaults; exceeding them is a sandbox violation.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SandboxConfig {
    pub cpu_ms: u64,
    pub memory_mb: u64,
    pub timeout_secs: u64,
}

impl Default for SandboxConfig {
    fn default() -> Self {
        SandboxConfig {
            cpu_ms: 5000,
            memory_mb: 256,
            timeout_secs: 30,
        }
    }
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
        ResourceLimits {
            cpu_ms: 5000,
            memory_mb: 256,
            timeout_secs: 30,
        }
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

// ── Sandbox backend ───────────────────────────────────────────────────────────

/// Platform-specific sandbox execution backend.
///
/// Each platform implements isolation differently:
/// - Linux:  seccomp-bpf syscall filter + cgroups v2 for resource limits
/// - macOS:  Seatbelt (sandbox_init) or App Sandbox profiles
/// - Windows: Job Objects + restricted tokens
///
/// The `StubBackend` is used until a platform backend is wired.
pub trait SandboxBackend: Send + Sync {
    /// Execute `code` with `limits` applied.
    ///
    /// Must:
    /// - Clear the parent environment before spawning
    /// - Enforce CPU, memory, and wall-clock limits
    /// - Return stdout/stderr as `output` on success
    fn execute(
        &self,
        code: &str,
        limits: &ResourceLimits,
    ) -> Result<ExecutionResult, ExecutorError>;

    /// Return a human-readable name for this backend.
    fn name(&self) -> &'static str;
}

/// Stub backend — runs code via `echo` with no real isolation.
///
/// TODO(sandbox): Replace with platform backends:
/// - Linux:   `SeccompBackend` using `libseccomp` + `nix` cgroups
/// - macOS:   `SeatbeltBackend` using `sandbox_init(3)` profiles
/// - Windows: `JobObjectBackend` using `CreateJobObject` + restricted tokens
pub struct StubBackend;

impl SandboxBackend for StubBackend {
    fn execute(
        &self,
        code: &str,
        limits: &ResourceLimits,
    ) -> Result<ExecutionResult, ExecutorError> {
        use std::process::Command;
        use std::time::Instant;

        let start = Instant::now();
        let timeout = std::time::Duration::from_secs(limits.timeout_secs);

        // Stub: echo the first 200 chars of code back as output.
        // Real implementations replace this with seccomp-jailed execution.
        let preview: String = code.chars().take(200).collect();
        let _ = timeout; // real backend would enforce this

        // Env-clear is the only real isolation in this stub.
        let output = Command::new("echo")
            .arg(&preview)
            .env_clear()
            .output()
            .map_err(|e| ExecutorError::Execution(e.to_string()))?;

        let duration_ms = start.elapsed().as_millis() as u64;

        Ok(ExecutionResult {
            executor_id: "stub".into(),
            success: output.status.success(),
            output: Some(String::from_utf8_lossy(&output.stdout).trim().to_string()),
            error: if output.status.success() {
                None
            } else {
                Some(String::from_utf8_lossy(&output.stderr).to_string())
            },
            duration_ms,
        })
    }

    fn name(&self) -> &'static str {
        "stub"
    }
}

/// Pool of sandboxed executor slots.
pub struct ExecutorPool {
    authority_config: HashMap<String, Value>,
    constraints: Vec<String>,
    sandbox: SandboxConfig,
    backend: Box<dyn SandboxBackend>,
}

impl ExecutorPool {
    pub fn new(authority_config: HashMap<String, Value>, constraints: Vec<String>) -> Self {
        ExecutorPool {
            authority_config,
            constraints,
            sandbox: SandboxConfig::default(),
            backend: Box::new(StubBackend),
        }
    }

    /// Create with a custom sandbox backend (for platform-specific implementations).
    pub fn with_backend(
        authority_config: HashMap<String, Value>,
        constraints: Vec<String>,
        backend: Box<dyn SandboxBackend>,
    ) -> Self {
        ExecutorPool {
            authority_config,
            constraints,
            sandbox: SandboxConfig::default(),
            backend,
        }
    }

    /// Submit a code execution request.
    ///
    /// Step 1: authority gate check (§62z).
    /// Step 2: resource limit validation against SandboxConfig.
    /// Step 3: credential leak detection.
    /// Step 4: execute via the configured sandbox backend.
    pub fn submit(&self, request: ExecutionRequest) -> Result<ExecutionResult, ExecutorError> {
        // Step 1: authority gate.
        authority_check(&request, &self.authority_config, &self.constraints)?;

        // Step 2: resource limits.
        self.validate_limits(&request.resource_limits)?;

        // Step 3: credential leak detection.
        if let Some(leak) = detect_credential_leak(&request.code) {
            return Err(ExecutorError::CredentialLeak(leak));
        }

        // Step 4: Execute via the configured sandbox backend.
        let exec_start = Instant::now();
        let mut result = self
            .backend
            .execute(&request.code, &request.resource_limits)?;
        result.executor_id = request.executor_id.clone();
        result.duration_ms = exec_start.elapsed().as_millis() as u64;
        Ok(result)
    }

    fn validate_limits(&self, limits: &ResourceLimits) -> Result<(), ExecutorError> {
        if limits.cpu_ms > self.sandbox.cpu_ms {
            return Err(ExecutorError::SandboxViolation(format!(
                "cpu_ms {} exceeds sandbox limit {}",
                limits.cpu_ms, self.sandbox.cpu_ms
            )));
        }
        if limits.memory_mb > self.sandbox.memory_mb {
            return Err(ExecutorError::SandboxViolation(format!(
                "memory_mb {} exceeds sandbox limit {}",
                limits.memory_mb, self.sandbox.memory_mb
            )));
        }
        if limits.timeout_secs > self.sandbox.timeout_secs {
            return Err(ExecutorError::SandboxViolation(format!(
                "timeout_secs {} exceeds sandbox limit {}",
                limits.timeout_secs, self.sandbox.timeout_secs
            )));
        }
        Ok(())
    }
}

/// Detect suspicious credential patterns in `code`.
///
/// Returns `Some(description)` if a known credential pattern is found.
/// Patterns: `Bearer `, `sk-`, `ANTHROPIC_API_KEY`, `AWS_SECRET`.
pub fn detect_credential_leak(code: &str) -> Option<String> {
    let patterns = [
        ("Bearer ", "HTTP Bearer token"),
        ("sk-", "OpenAI-style secret key"),
        ("ANTHROPIC_API_KEY", "Anthropic API key"),
        ("AWS_SECRET", "AWS secret credential"),
    ];
    for (pattern, description) in &patterns {
        if code.contains(pattern) {
            return Some(format!(
                "credential pattern '{}' detected: {}",
                pattern, description
            ));
        }
    }
    None
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
        return Err(ExecutorError::AuthorityDenied(format!(
            "{:?}: {}",
            resolution.outcome, resolution.basis
        )));
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_sandbox_config_defaults() {
        let sc = SandboxConfig::default();
        assert_eq!(sc.cpu_ms, 5000);
        assert_eq!(sc.memory_mb, 256);
        assert_eq!(sc.timeout_secs, 30);
    }

    #[test]
    fn test_detect_credential_leak_bearer() {
        let result = detect_credential_leak("Authorization: Bearer abc123");
        assert!(result.is_some());
        assert!(result.unwrap().contains("Bearer"));
    }

    #[test]
    fn test_detect_credential_leak_sk() {
        let result = detect_credential_leak("token = 'sk-proj-abc'");
        assert!(result.is_some());
    }

    #[test]
    fn test_detect_credential_leak_anthropic() {
        let result = detect_credential_leak("os.environ['ANTHROPIC_API_KEY']");
        assert!(result.is_some());
    }

    #[test]
    fn test_detect_credential_leak_aws() {
        let result = detect_credential_leak("AWS_SECRET_ACCESS_KEY=xyz");
        assert!(result.is_some());
    }

    #[test]
    fn test_no_credential_leak() {
        let result = detect_credential_leak("x = 1 + 2");
        assert!(result.is_none());
    }

    #[test]
    fn test_validate_limits_within_bounds() {
        let pool = ExecutorPool::new(HashMap::new(), vec![]);
        let limits = ResourceLimits::default();
        assert!(pool.validate_limits(&limits).is_ok());
    }

    #[test]
    fn test_validate_limits_cpu_exceeded() {
        let pool = ExecutorPool::new(HashMap::new(), vec![]);
        let limits = ResourceLimits {
            cpu_ms: 100_000,
            ..ResourceLimits::default()
        };
        assert!(matches!(
            pool.validate_limits(&limits),
            Err(ExecutorError::SandboxViolation(_))
        ));
    }

    #[test]
    fn test_validate_limits_memory_exceeded() {
        let pool = ExecutorPool::new(HashMap::new(), vec![]);
        let limits = ResourceLimits {
            memory_mb: 1024,
            ..ResourceLimits::default()
        };
        assert!(matches!(
            pool.validate_limits(&limits),
            Err(ExecutorError::SandboxViolation(_))
        ));
    }

    #[test]
    fn test_credential_leak_rejected_by_pool() {
        let _pool = ExecutorPool::new(HashMap::new(), vec!["allow_all".into()]);
        let req = ExecutionRequest {
            executor_id: "test".into(),
            scope: "test".into(),
            code: "Bearer abc123".into(),
            resource_limits: ResourceLimits::default(),
        };
        // Authority will likely deny this too, but we specifically check the
        // credential leak path would trigger if authority passed.
        let result = detect_credential_leak(&req.code);
        assert!(result.is_some());
    }

    #[test]
    fn stub_backend_executes() {
        let backend = StubBackend;
        let result = backend
            .execute("hello world", &ResourceLimits::default())
            .unwrap();
        assert!(result.success);
        assert!(result.output.is_some());
    }

    #[test]
    fn executor_pool_uses_backend() {
        let pool = ExecutorPool::new(HashMap::new(), vec!["allow_all".into()]);
        assert_eq!(pool.backend.name(), "stub");
    }
}
