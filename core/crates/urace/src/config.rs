//! Runtime configuration — `RuntimeConfig` struct, load/save, schema validation.
//!
//! Ported from `runtime/urace/config_access.py` and `runtime/urace/config_schema.py`.
//!
//! Config is stored at `~/.urace/config.yaml` (YAML is preferred for new installs).
//! `~/.urace/config.json` is accepted on load for backward compatibility.
//! All mutations must go through the authority check before taking effect (§62z).

use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use std::path::PathBuf;

// ── Config structs ────────────────────────────────────────────────────────────

/// Top-level URACE runtime configuration.
///
/// Mirrors the Python `URACEConfig` Pydantic model.  Unknown keys are preserved
/// via the `extra` field (product overlays).
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
pub struct RuntimeConfig {
    /// Config schema version — defaults to 1.
    pub config_version: u32,

    /// Capability feature toggles.
    pub capability_flags: CapabilityFlags,

    /// P2P network settings.
    pub network: NetworkConfig,

    /// AI executor provider settings.
    pub executor: ExecutorConfig,

    /// Source adapter settings.
    pub sources: SourcesConfig,

    /// Automatic goal derivation.
    pub auto_goals: AutoGoalsConfig,

    /// Resource allocation settings.
    pub resources: ResourcesConfig,

    /// Self-evolution policy.
    pub self_evolution_policy: SelfEvolutionPolicy,

    /// Logging settings.
    pub logging: LoggingConfig,

    /// Runtime workflow (cycle) settings.
    pub runtime_workflow: RuntimeWorkflowConfig,

    /// MCP server settings.
    pub mcp: McpConfig,
}

impl Default for RuntimeConfig {
    fn default() -> Self {
        RuntimeConfig {
            config_version: 1,
            capability_flags: CapabilityFlags::default(),
            network: NetworkConfig::default(),
            executor: ExecutorConfig::default(),
            sources: SourcesConfig::default(),
            auto_goals: AutoGoalsConfig::default(),
            resources: ResourcesConfig::default(),
            self_evolution_policy: SelfEvolutionPolicy::default(),
            logging: LoggingConfig::default(),
            runtime_workflow: RuntimeWorkflowConfig::default(),
            mcp: McpConfig::default(),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
pub struct CapabilityFlags {
    pub executor_enabled: bool,
    pub freeform_enabled: bool,
    pub machine_interface_enabled: bool,
    pub compress_enabled: bool,
    pub decompress_enabled: bool,
    pub p2p_mint_enabled: bool,
    pub p2p_sell_enabled: bool,
    pub p2p_borrow_enabled: bool,
    pub context_mint_enabled: bool,
    pub compliance_mode: bool,
}

impl Default for CapabilityFlags {
    fn default() -> Self {
        CapabilityFlags {
            executor_enabled: true,
            freeform_enabled: true,
            machine_interface_enabled: true,
            compress_enabled: true,
            decompress_enabled: true,
            p2p_mint_enabled: false,
            p2p_sell_enabled: false,
            p2p_borrow_enabled: false,
            context_mint_enabled: true,
            compliance_mode: false,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
pub struct NetworkConfig {
    pub enabled: bool,
    /// "intranet" | "hybrid" | "internet"
    pub mode: String,
    pub port: u16,
    pub bootstrap_peers: Vec<String>,
    pub advertise: bool,
    pub relay_only: bool,
    pub admission_quarantine_enabled: bool,
    pub relay_failure_threshold: u32,
    pub direct_failure_threshold: u32,
}

impl Default for NetworkConfig {
    fn default() -> Self {
        NetworkConfig {
            enabled: false,
            mode: "hybrid".to_string(),
            port: 7301,
            bootstrap_peers: vec![],
            advertise: false,
            relay_only: false,
            admission_quarantine_enabled: true,
            relay_failure_threshold: 5,
            direct_failure_threshold: 2,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
pub struct ExecutorConfig {
    pub enabled: bool,
    pub freeform_max_tokens_per_24h: u64,
    pub freeform_confidence_threshold: f64,
    pub agora_quorum_threshold: f64,
    pub agora_proposal_ttl_hours: u32,
}

impl Default for ExecutorConfig {
    fn default() -> Self {
        ExecutorConfig {
            enabled: false,
            freeform_max_tokens_per_24h: 200_000,
            freeform_confidence_threshold: 0.8,
            agora_quorum_threshold: 0.5,
            agora_proposal_ttl_hours: 72,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
pub struct SourcesConfig {
    /// Seconds between automatic source sync cycles (0 = disabled).
    pub auto_sync_interval_s: u64,
    /// Enable act() path globally.
    pub allow_act: bool,
    /// Log every act() call regardless of outcome.
    pub act_audit_all: bool,
}

impl Default for SourcesConfig {
    fn default() -> Self {
        SourcesConfig {
            auto_sync_interval_s: 300,
            allow_act: false,
            act_audit_all: true,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
pub struct AutoGoalsConfig {
    pub enabled: bool,
    pub replenish_backlog: bool,
}

impl Default for AutoGoalsConfig {
    fn default() -> Self {
        AutoGoalsConfig {
            enabled: false,
            replenish_backlog: true,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
pub struct ResourcesConfig {
    /// "low" | "medium" | "high" | "inherit"
    pub effort: String,
}

impl Default for ResourcesConfig {
    fn default() -> Self {
        ResourcesConfig {
            effort: "medium".to_string(),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
pub struct SelfEvolutionPolicy {
    /// "NECESSARY_ONLY" | "CONTINUOUS" | "DISABLED"
    pub mode: String,
}

impl Default for SelfEvolutionPolicy {
    fn default() -> Self {
        SelfEvolutionPolicy {
            mode: "NECESSARY_ONLY".to_string(),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
pub struct LoggingConfig {
    /// "DEBUG" | "INFO" | "WARNING" | "ERROR"
    pub level: String,
    /// "text" | "json"
    pub format: String,
    pub file: String,
    pub max_bytes: u64,
    pub backup_count: u32,
    pub audit_tier: bool,
    pub m2m_stream: bool,
    pub m2m_diagnostic: bool,
    pub redact_executor_output: bool,
}

impl Default for LoggingConfig {
    fn default() -> Self {
        LoggingConfig {
            level: "WARNING".to_string(),
            format: "text".to_string(),
            file: String::new(),
            max_bytes: 10_485_760,
            backup_count: 5,
            audit_tier: true,
            m2m_stream: true,
            m2m_diagnostic: false,
            redact_executor_output: true,
        }
    }
}

/// Runtime cycle (workflow) settings — from `runtime_cycle_cli.py`.
///
/// Validation: `interval_seconds` must be in [60, 86400].
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
pub struct RuntimeWorkflowConfig {
    pub enabled: bool,
    pub auto_deploy: bool,
    /// Seconds between improvement cycles. Must be [60, 86400].
    pub interval_seconds: u32,
}

impl Default for RuntimeWorkflowConfig {
    fn default() -> Self {
        RuntimeWorkflowConfig {
            enabled: false,
            auto_deploy: true,
            interval_seconds: 10800,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
pub struct McpConfig {
    pub enabled: bool,
    pub port: u16,
    pub bind_addr: String,
}

impl Default for McpConfig {
    fn default() -> Self {
        McpConfig {
            enabled: false,
            port: 7399,
            bind_addr: "127.0.0.1".to_string(),
        }
    }
}

// ── Schema validation errors ──────────────────────────────────────────────────

/// A single schema validation error.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ValidationError {
    pub path: String,
    pub message: String,
}

impl std::fmt::Display for ValidationError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}: {}", self.path, self.message)
    }
}

/// Validate a `RuntimeConfig` against schema constraints.
///
/// Returns a list of validation errors.  An empty list means the config is valid.
pub fn validate(cfg: &RuntimeConfig) -> Vec<ValidationError> {
    let mut errors = Vec::new();

    // config_version must be >= 1
    if cfg.config_version < 1 {
        errors.push(ValidationError {
            path: "config_version".into(),
            message: "must be >= 1".into(),
        });
    }

    // network.mode must be one of the allowed values
    let valid_modes = ["intranet", "hybrid", "internet"];
    if !valid_modes.contains(&cfg.network.mode.as_str()) {
        errors.push(ValidationError {
            path: "network.mode".into(),
            message: format!(
                "must be one of {:?}, got {:?}",
                valid_modes, cfg.network.mode
            ),
        });
    }

    // network.port must be in [1, 65535]
    if cfg.network.port == 0 {
        errors.push(ValidationError {
            path: "network.port".into(),
            message: "must be in [1, 65535]".into(),
        });
    }

    // executor thresholds
    if !(0.0..=1.0).contains(&cfg.executor.freeform_confidence_threshold) {
        errors.push(ValidationError {
            path: "executor.freeform_confidence_threshold".into(),
            message: "must be in [0.0, 1.0]".into(),
        });
    }
    if !(0.0..=1.0).contains(&cfg.executor.agora_quorum_threshold) {
        errors.push(ValidationError {
            path: "executor.agora_quorum_threshold".into(),
            message: "must be in [0.0, 1.0]".into(),
        });
    }
    if cfg.executor.agora_proposal_ttl_hours < 1 {
        errors.push(ValidationError {
            path: "executor.agora_proposal_ttl_hours".into(),
            message: "must be >= 1".into(),
        });
    }

    // resources.effort must be valid
    let valid_efforts = ["low", "medium", "high", "inherit"];
    if !valid_efforts.contains(&cfg.resources.effort.as_str()) {
        errors.push(ValidationError {
            path: "resources.effort".into(),
            message: format!(
                "must be one of {:?}, got {:?}",
                valid_efforts, cfg.resources.effort
            ),
        });
    }

    // self_evolution_policy.mode must be valid
    let valid_modes = ["NECESSARY_ONLY", "CONTINUOUS", "DISABLED"];
    if !valid_modes.contains(&cfg.self_evolution_policy.mode.as_str()) {
        errors.push(ValidationError {
            path: "self_evolution_policy.mode".into(),
            message: format!(
                "must be one of {:?}, got {:?}",
                valid_modes, cfg.self_evolution_policy.mode
            ),
        });
    }

    // logging.level must be valid
    let valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR"];
    if !valid_levels.contains(&cfg.logging.level.as_str()) {
        errors.push(ValidationError {
            path: "logging.level".into(),
            message: format!(
                "must be one of {:?}, got {:?}",
                valid_levels, cfg.logging.level
            ),
        });
    }

    // runtime_workflow.interval_seconds: [60, 86400]
    let iv = cfg.runtime_workflow.interval_seconds;
    if !(60..=86400).contains(&iv) {
        errors.push(ValidationError {
            path: "runtime_workflow.interval_seconds".into(),
            message: format!("must be in [60, 86400], got {iv}"),
        });
    }

    errors
}

// ── Load / save ───────────────────────────────────────────────────────────────

/// Return the default config file path: `~/.urace/config.yaml`.
///
/// If `~/.urace/config.json` already exists and no YAML file is present,
/// callers may pass the JSON path directly — `load()` auto-detects format.
pub fn default_config_path() -> PathBuf {
    let home = std::env::var("HOME")
        .or_else(|_| std::env::var("USERPROFILE"))
        .unwrap_or_else(|_| ".".to_string());
    let urace_dir = PathBuf::from(home).join(".urace");
    // Prefer YAML; fall back to JSON for existing installs.
    let yaml = urace_dir.join("config.yaml");
    if !yaml.exists() {
        let json = urace_dir.join("config.json");
        if json.exists() {
            return json;
        }
    }
    yaml
}

/// Load config from `path`.  Returns `RuntimeConfig::default()` if the file
/// does not exist yet (first-run scenario).
///
/// Format is auto-detected from the file extension (`.yaml`/`.yml` → YAML, else JSON).
pub fn load(path: &std::path::Path) -> Result<RuntimeConfig> {
    if !path.exists() {
        return Ok(RuntimeConfig::default());
    }
    let raw = std::fs::read_to_string(path)
        .with_context(|| format!("reading config from {}", path.display()))?;
    let ext = path.extension().and_then(|e| e.to_str()).unwrap_or("");
    let cfg: RuntimeConfig = if ext == "yaml" || ext == "yml" {
        serde_yaml::from_str(&raw)
            .with_context(|| format!("parsing YAML config from {}", path.display()))?
    } else {
        serde_json::from_str(&raw)
            .with_context(|| format!("parsing JSON config from {}", path.display()))?
    };
    Ok(cfg)
}

/// Save config to `path` using an atomic rename.
///
/// Writes YAML when `path` has a `.yaml`/`.yml` extension, JSON otherwise.
/// Creates parent directories if they do not exist.
/// NOTE: callers MUST have cleared the authority gate before calling this.
pub fn save(cfg: &RuntimeConfig, path: &std::path::Path) -> Result<()> {
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent)
            .with_context(|| format!("creating config dir {}", parent.display()))?;
    }
    let ext = path.extension().and_then(|e| e.to_str()).unwrap_or("");
    let content = if ext == "yaml" || ext == "yml" {
        serde_yaml::to_string(cfg).with_context(|| "serialising config to YAML")?
    } else {
        serde_json::to_string_pretty(cfg)?
    };
    let tmp_ext = if ext == "yaml" { "yaml.tmp" } else { "json.tmp" };
    let tmp = path.with_extension(tmp_ext);
    std::fs::write(&tmp, content.as_bytes())
        .with_context(|| format!("writing config to {}", tmp.display()))?;
    std::fs::rename(&tmp, path)
        .with_context(|| format!("renaming config tmp file to {}", path.display()))?;
    Ok(())
}

// ── Tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    #[test]
    fn default_config_validates_cleanly() {
        let cfg = RuntimeConfig::default();
        let errors = validate(&cfg);
        assert!(
            errors.is_empty(),
            "default config should be valid, got: {errors:?}"
        );
    }

    #[test]
    fn load_missing_returns_default() {
        let dir = TempDir::new().unwrap();
        let path = dir.path().join("config.json");
        let cfg = load(&path).unwrap();
        assert_eq!(cfg.config_version, 1);
        assert!(!cfg.executor.enabled);
    }

    #[test]
    fn save_and_reload_roundtrip() {
        let dir = TempDir::new().unwrap();
        let path = dir.path().join("config.json");

        let mut cfg = RuntimeConfig::default();
        cfg.executor.enabled = true;
        cfg.network.port = 7302;
        cfg.logging.level = "DEBUG".to_string();

        save(&cfg, &path).unwrap();

        let loaded = load(&path).unwrap();
        assert!(loaded.executor.enabled);
        assert_eq!(loaded.network.port, 7302);
        assert_eq!(loaded.logging.level, "DEBUG");
    }

    #[test]
    fn validation_catches_bad_mode() {
        let mut cfg = RuntimeConfig::default();
        cfg.network.mode = "INVALID_MODE".to_string();
        let errors = validate(&cfg);
        assert!(
            errors.iter().any(|e| e.path == "network.mode"),
            "expected network.mode error, got: {errors:?}"
        );
    }

    #[test]
    fn validation_catches_bad_interval() {
        let mut cfg = RuntimeConfig::default();
        cfg.runtime_workflow.interval_seconds = 10; // below min 60
        let errors = validate(&cfg);
        assert!(
            errors
                .iter()
                .any(|e| e.path == "runtime_workflow.interval_seconds"),
            "expected interval error, got: {errors:?}"
        );
    }

    #[test]
    fn validation_catches_bad_self_evolution_mode() {
        let mut cfg = RuntimeConfig::default();
        cfg.self_evolution_policy.mode = "ALWAYS".to_string();
        let errors = validate(&cfg);
        assert!(
            errors
                .iter()
                .any(|e| e.path == "self_evolution_policy.mode"),
            "expected self_evolution_policy.mode error, got: {errors:?}"
        );
    }

    #[test]
    fn atomic_write_produces_valid_json() {
        let dir = TempDir::new().unwrap();
        let path = dir.path().join("config.json");
        let cfg = RuntimeConfig::default();
        save(&cfg, &path).unwrap();
        let raw = std::fs::read_to_string(&path).unwrap();
        let parsed: serde_json::Value = serde_json::from_str(&raw).unwrap();
        assert!(parsed.is_object());
    }

    #[test]
    fn yaml_save_and_reload_roundtrip() {
        let dir = TempDir::new().unwrap();
        let path = dir.path().join("config.yaml");
        let mut cfg = RuntimeConfig::default();
        cfg.network.port = 7310;
        cfg.logging.level = "DEBUG".to_string();
        save(&cfg, &path).unwrap();
        let raw = std::fs::read_to_string(&path).unwrap();
        // YAML file should not contain JSON braces at the top level
        assert!(!raw.trim_start().starts_with('{'), "expected YAML output");
        let loaded = load(&path).unwrap();
        assert_eq!(loaded.network.port, 7310);
        assert_eq!(loaded.logging.level, "DEBUG");
    }

    #[test]
    fn load_json_fallback() {
        let dir = TempDir::new().unwrap();
        let path = dir.path().join("config.json");
        let mut cfg = RuntimeConfig::default();
        cfg.network.port = 7320;
        save(&cfg, &path).unwrap();
        let loaded = load(&path).unwrap();
        assert_eq!(loaded.network.port, 7320);
    }
}
