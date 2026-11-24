//! Startup sequence — validate config, init tracing, check authority policy.
//!
//! Ported from `runtime/urace/bootstrap.py` and `runtime/urace/preflight.py`.
//!
//! Invariants:
//! - Tracing subscriber must be initialised exactly once (guarded internally).
//! - Authority policy must be checked before any mutating operation.
//! - Pre-flight hints are advisory only — they never block startup.

use crate::config::{self, RuntimeConfig};
use crate::version::{FORMAT_VERSION, MIN_FORMAT_VERSION, VERSION};
use anyhow::Result;
use std::path::{Path, PathBuf};
use tracing::Level;
use tracing_subscriber::EnvFilter;

// ── Preflight hints ───────────────────────────────────────────────────────────

/// Severity of a preflight hint.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum HintLevel {
    Info,
    Warning,
}

/// An advisory note emitted during preflight (never fatal).
#[derive(Debug, Clone)]
pub struct PreflightHint {
    pub level: HintLevel,
    pub code: String,
    pub message: String,
    pub action: String,
}

/// Collect preflight hints for the given config and runtime root.
///
/// Never raises — returns an empty list on any internal error (mirrors Python).
pub fn preflight_hints(cfg: &RuntimeConfig, root: &Path) -> Vec<PreflightHint> {
    let mut hints = Vec::new();
    format_hints(cfg, root, &mut hints);
    improvement_hints(root, &mut hints);
    hints
}

fn format_hints(_cfg: &RuntimeConfig, root: &Path, hints: &mut Vec<PreflightHint>) {
    let state_path = root.join("state").join("state.json");
    if !state_path.exists() {
        return;
    }
    let schema_version: u32 = (|| -> Option<u32> {
        let raw = std::fs::read_to_string(&state_path).ok()?;
        let v: serde_json::Value = serde_json::from_str(&raw).ok()?;
        v.get("schema_version")?.as_u64().map(|n| n as u32)
    })()
    .unwrap_or(1);

    if schema_version < MIN_FORMAT_VERSION {
        hints.push(PreflightHint {
            level: HintLevel::Warning,
            code: "FORMAT_TOO_OLD".into(),
            message: format!(
                "State format {schema_version} predates minimum {MIN_FORMAT_VERSION}; migration required"
            ),
            action: "urace check --migration-dry-run".into(),
        });
    } else if schema_version > FORMAT_VERSION {
        hints.push(PreflightHint {
            level: HintLevel::Warning,
            code: "FORMAT_NEWER".into(),
            message: format!(
                "State was written by a newer runtime (format {schema_version}); this runtime may misread it"
            ),
            action: "upgrade urace to match the state format version".into(),
        });
    }
}

fn improvement_hints(root: &Path, hints: &mut Vec<PreflightHint>) {
    let trial = root.join("trial");
    if trial.join("runtime-deployment-pending.json").exists() {
        hints.push(PreflightHint {
            level: HintLevel::Info,
            code: "IMPROVEMENT_READY".into(),
            message: "Runtime improvement qualified and pending deployment".into(),
            action: "urace watch report".into(),
        });
        return;
    }
    let cycle_file = trial.join("runtime-cycle-latest.json");
    if cycle_file.exists() {
        let stage = (|| -> Option<String> {
            let raw = std::fs::read_to_string(&cycle_file).ok()?;
            let v: serde_json::Value = serde_json::from_str(&raw).ok()?;
            Some(v.get("stage")?.as_str()?.to_string())
        })()
        .unwrap_or_default();
        if stage == "AWAITING_APPROVAL" {
            hints.push(PreflightHint {
                level: HintLevel::Info,
                code: "IMPROVEMENT_AWAITING_APPROVAL".into(),
                message: "Runtime improvement awaiting owner approval".into(),
                action: "urace watch report".into(),
            });
        }
    }
}

// ── Startup sequence ──────────────────────────────────────────────────────────

/// Result from a completed bootstrap sequence.
pub struct BootstrapResult {
    /// Loaded (and validated) runtime config.
    pub config: RuntimeConfig,
    /// Resolved runtime root directory.
    pub root: PathBuf,
    /// Advisory hints (never fatal).
    pub hints: Vec<PreflightHint>,
    /// Validation errors from config schema check.
    pub validation_errors: Vec<config::ValidationError>,
}

/// Run the full startup sequence:
/// 1. Resolve runtime root (`~/.urace`).
/// 2. Load config from `config.json`.
/// 3. Validate config schema (non-fatal).
/// 4. Initialise tracing (honours `RUST_LOG`; falls back to config log level).
/// 5. Collect preflight hints.
///
/// Returns `Err` only for hard I/O failures on startup.
pub fn run(config_path: Option<&Path>) -> Result<BootstrapResult> {
    let root = resolve_root();

    let resolved_config_path = config_path
        .map(|p| p.to_path_buf())
        .unwrap_or_else(config::default_config_path);

    let cfg = config::load(&resolved_config_path)?;

    let validation_errors = config::validate(&cfg);

    // Initialise tracing subscriber once.  Failure is non-fatal (subscriber
    // may already be initialised in test contexts).
    let _ = init_tracing(&cfg);

    if !validation_errors.is_empty() {
        for e in &validation_errors {
            tracing::warn!("config validation: {e}");
        }
    }

    tracing::info!(version = VERSION, "urace starting");

    let hints = preflight_hints(&cfg, &root);
    for h in &hints {
        match h.level {
            HintLevel::Info => tracing::info!(code = %h.code, "{}", h.message),
            HintLevel::Warning => tracing::warn!(code = %h.code, "{}", h.message),
        }
    }

    Ok(BootstrapResult {
        config: cfg,
        root,
        hints,
        validation_errors,
    })
}

/// Resolve the runtime root directory (`~/.urace` or `$URACE_HOME`).
pub fn resolve_root() -> PathBuf {
    if let Ok(env_home) = std::env::var("URACE_HOME") {
        return PathBuf::from(env_home);
    }
    let home = std::env::var("HOME")
        .or_else(|_| std::env::var("USERPROFILE"))
        .unwrap_or_else(|_| ".".to_string());
    PathBuf::from(home).join(".urace")
}

/// Initialise the global tracing subscriber.
///
/// Respects `RUST_LOG`; falls back to the level in `cfg.logging.level`.
/// Returns an error if a subscriber is already installed (safe to ignore in tests).
pub fn init_tracing(cfg: &RuntimeConfig) -> Result<()> {
    let default_level = match cfg.logging.level.to_uppercase().as_str() {
        "DEBUG" => Level::DEBUG,
        "INFO" => Level::INFO,
        "ERROR" => Level::ERROR,
        _ => Level::WARN,
    };

    let filter = EnvFilter::try_from_default_env()
        .unwrap_or_else(|_| EnvFilter::new(default_level.as_str()));

    tracing_subscriber::fmt()
        .with_env_filter(filter)
        .try_init()
        .map_err(|e| anyhow::anyhow!("tracing init: {e}"))?;

    Ok(())
}

// ── Authority policy check (§62z) ─────────────────────────────────────────────

/// Outcomes from the §62z authority check.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum AuthorityCheckOutcome {
    /// Action is autonomously authorized.
    AutonomouslyAuthorized,
    /// Action is explicitly denied.
    Denied,
    /// An authoritative decision from the operator is required.
    RequiresAuthoritativeDecision,
    /// Unresolved — treat as Denied.
    Unresolved,
}

/// Thin wrapper that delegates to `urace-authority` for the authority check.
///
/// Any config mutation MUST go through this gate before the config is saved.
/// Callers must treat `Denied` and `Unresolved` identically.
pub fn check_authority_policy(
    action: &str,
    scope: &str,
    cfg: &RuntimeConfig,
) -> AuthorityCheckOutcome {
    use std::collections::HashMap;
    use urace_authority::authority::{resolve, Objective};
    use urace_types::AuthorityOutcome;

    let obj = Objective {
        id: Some(format!("bootstrap-{action}")),
        scope: scope.to_string(),
        title: format!("bootstrap config mutation: {action}"),
        reason: Some("startup sequence authority check".to_string()),
        necessity_evidence: None,
        lower_impact_route_sufficient: Some(true),
    };

    // Minimal authority config: grant documentation + implementation by default
    let mut authority_config: HashMap<String, serde_json::Value> = HashMap::new();
    authority_config.insert(
        "delegated".to_string(),
        serde_json::json!([
            "assessment",
            "objectives",
            "priority",
            "plans",
            "local implementation changes",
            "measurement",
        ]),
    );
    authority_config.insert("reserved".to_string(), serde_json::json!([]));

    let mut self_evo_policy: HashMap<String, serde_json::Value> = HashMap::new();
    self_evo_policy.insert(
        "mode".to_string(),
        serde_json::Value::String(cfg.self_evolution_policy.mode.clone()),
    );

    let resolution = resolve(&obj, &authority_config, Some(&self_evo_policy), &[]);

    match resolution.outcome {
        AuthorityOutcome::AutonomouslyAuthorized => AuthorityCheckOutcome::AutonomouslyAuthorized,
        AuthorityOutcome::Denied => AuthorityCheckOutcome::Denied,
        AuthorityOutcome::RequiresAuthoritativeDecision => {
            AuthorityCheckOutcome::RequiresAuthoritativeDecision
        }
        AuthorityOutcome::Unresolved => AuthorityCheckOutcome::Unresolved,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    #[test]
    fn preflight_hints_no_state_returns_empty() {
        let dir = TempDir::new().unwrap();
        let cfg = RuntimeConfig::default();
        let hints = preflight_hints(&cfg, dir.path());
        assert!(hints.is_empty());
    }

    #[test]
    fn resolve_root_respects_env() {
        std::env::set_var("URACE_HOME", "/tmp/test-urace-home");
        let root = resolve_root();
        assert_eq!(root, PathBuf::from("/tmp/test-urace-home"));
        std::env::remove_var("URACE_HOME");
    }
}
