//! Provider routing — ported from `executor_routing.py`.
//!
//! Selects and ranks executor providers based on capability, priority, and
//! recent performance history.  All public symbols mirror the Python module.

use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::{HashMap, HashSet};

// ── Supported adapter names ───────────────────────────────────────────────────

/// Canonical set of supported executor adapter identifiers.
pub const SUPPORTED_ADAPTERS: &[&str] = &["codex-cli", "claude-cli", "script", "http", "mcp"];

// ── Unavailability classification ─────────────────────────────────────────────

/// Classified reason a provider is currently unavailable.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum UnavailabilityClass {
    /// Usage/rate limit or quota exhaustion (`PROVIDER_CAPACITY`).
    RateLimit,
    /// Auth/model configuration failure (`EXECUTOR_AUTH_UNAVAILABLE`).
    AuthFailure,
    /// Sandbox / execution environment could not start (`EXECUTION_ENVIRONMENT_UNAVAILABLE`).
    ExecutionEnvironment,
    /// Transient network disconnect (`EXECUTOR_TRANSIENT_NETWORK`).
    NetworkError,
    /// Error detail did not match any known pattern.
    Unknown,
}

/// Markers used to detect rate-limit / quota messages (case-insensitive substring).
const RATE_LIMIT_MARKERS: &[&str] = &[
    "usage limit",
    "rate limit",
    "quota exceeded",
    "too many requests",
    "credits exhausted",
    "hit your limit",
];

/// Markers used to detect auth / model-configuration failures.
const AUTH_FAILURE_MARKERS: &[&str] = &[
    "401",
    "unauthorized",
    "not authenticated",
    "invalid api key",
    "authentication failed",
    "login required",
    "not supported when using codex with a chatgpt account",
    "model is not supported",
];

/// Markers used to detect transient infrastructure disconnects.
const TRANSIENT_NETWORK_MARKERS: &[&str] = &[
    "cf-ray:",
    "stream disconnected",
    "connection reset by peer",
    "upstream connect error",
    "upstream disconnect",
    "502 bad gateway",
    "503 service unavailable",
    "504 gateway timeout",
];

/// Markers used to detect execution-environment / sandbox failures.
const EXECUTION_ENVIRONMENT_FAILURES: &[&str] = &[
    "bwrap: loopback: failed rtm_newaddr: operation not permitted",
    "sandbox could not initialize",
    "workspace sandbox failed before",
    "workspace execution sandbox failed before",
];

/// Classify an error message string into the most specific [`UnavailabilityClass`].
///
/// Order matches the Python precedence: rate-limit → auth → execution-env → network → unknown.
pub fn classify_unavailability(error_msg: &str) -> UnavailabilityClass {
    let lower = error_msg.to_lowercase();
    if RATE_LIMIT_MARKERS.iter().any(|m| lower.contains(m)) {
        return UnavailabilityClass::RateLimit;
    }
    if AUTH_FAILURE_MARKERS.iter().any(|m| lower.contains(m)) {
        return UnavailabilityClass::AuthFailure;
    }
    if EXECUTION_ENVIRONMENT_FAILURES
        .iter()
        .any(|m| lower.contains(m))
    {
        return UnavailabilityClass::ExecutionEnvironment;
    }
    if TRANSIENT_NETWORK_MARKERS.iter().any(|m| lower.contains(m)) {
        return UnavailabilityClass::NetworkError;
    }
    UnavailabilityClass::Unknown
}

// ── Provider definition ───────────────────────────────────────────────────────

/// A fully-resolved provider entry as used by the router.
///
/// Fields match the Python dict keys emitted by `provider_definitions()`.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProviderDef {
    /// Unique provider identifier (e.g. `"primary"`, `"env-claude"`).
    pub id: String,
    /// Adapter type — one of [`SUPPORTED_ADAPTERS`].
    pub adapter: String,
    /// CLI command or endpoint (adapter-specific).
    pub command: Option<String>,
    /// Relative overall priority (higher is better).
    pub priority: i64,
    /// Capability names this provider supports.
    pub capabilities: Vec<String>,
    /// Per-capability priority overrides.
    #[serde(default)]
    pub capability_priorities: HashMap<String, i64>,
    /// Maximum context tokens this provider's transport can handle.
    pub transport_ceiling_tokens: Option<u64>,
    /// Arbitrary extra config fields forwarded from the JSON config.
    #[serde(flatten)]
    pub extra: HashMap<String, Value>,
}

impl ProviderDef {
    /// Effective priority for a specific capability.
    fn capability_priority(&self, capability: &str) -> i64 {
        self.capability_priorities
            .get(capability)
            .copied()
            .unwrap_or(self.priority)
    }
}

/// A minimal task specification used by [`select_provider`].
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TaskSpec {
    /// The capability required for this task (e.g. `"mutation"`, `"evaluation"`).
    pub capability: String,
    /// Context tokens the task will consume — capped at provider ceiling.
    pub context_tokens: Option<u64>,
    /// Arbitrary task metadata.
    #[serde(flatten)]
    pub extra: HashMap<String, Value>,
}

// ── Building provider list from config ────────────────────────────────────────

/// Default capability set assigned to providers that omit an explicit list.
const DEFAULT_CAPABILITIES: &[&str] = &[
    "discovery",
    "planning",
    "mutation",
    "evaluation",
    "execution",
];

/// Synthesize zero-config provider entries from well-known environment variables.
fn env_auto_providers() -> Vec<ProviderDef> {
    let mut providers = Vec::new();
    let caps: Vec<String> = DEFAULT_CAPABILITIES.iter().map(|s| s.to_string()).collect();

    if std::env::var("ANTHROPIC_API_KEY").is_ok() {
        providers.push(ProviderDef {
            id: "env-claude".into(),
            adapter: "codex-cli".into(),
            command: Some("claude".into()),
            priority: 90,
            capabilities: caps.clone(),
            capability_priorities: HashMap::new(),
            transport_ceiling_tokens: None,
            extra: {
                let mut m = HashMap::new();
                m.insert("_source".into(), Value::String("ANTHROPIC_API_KEY".into()));
                m
            },
        });
    }
    if std::env::var("OPENAI_API_KEY").is_ok() {
        providers.push(ProviderDef {
            id: "env-openai".into(),
            adapter: "codex-cli".into(),
            command: Some("codex".into()),
            priority: 80,
            capabilities: caps,
            capability_priorities: HashMap::new(),
            transport_ceiling_tokens: None,
            extra: {
                let mut m = HashMap::new();
                m.insert("_source".into(), Value::String("OPENAI_API_KEY".into()));
                m
            },
        });
    }
    providers
}

/// Parse a JSON object into a [`ProviderDef`], applying defaults.
fn parse_provider(obj: &Value) -> Option<ProviderDef> {
    let map = obj.as_object()?;

    // Skip disabled providers.
    if let Some(enabled) = map.get("enabled") {
        if enabled == &Value::Bool(false) {
            return None;
        }
    }

    let id = map.get("id")?.as_str()?.to_string();
    let adapter = map
        .get("adapter")
        .and_then(Value::as_str)
        .unwrap_or("codex-cli")
        .to_string();
    let command = map
        .get("command")
        .and_then(Value::as_str)
        .map(str::to_string);
    let priority = map.get("priority").and_then(Value::as_i64).unwrap_or(0);

    let capabilities: Vec<String> = match map.get("capabilities") {
        Some(Value::Array(arr)) => arr
            .iter()
            .filter_map(|v| v.as_str().map(str::to_string))
            .collect(),
        _ => DEFAULT_CAPABILITIES.iter().map(|s| s.to_string()).collect(),
    };

    let capability_priorities: HashMap<String, i64> =
        match map.get("capability_priorities").and_then(Value::as_object) {
            Some(cp) => cp
                .iter()
                .filter_map(|(k, v)| v.as_i64().map(|n| (k.clone(), n)))
                .collect(),
            None => HashMap::new(),
        };

    let transport_ceiling_tokens = map.get("transport_ceiling_tokens").and_then(Value::as_u64);

    // Carry through any remaining keys as `extra`.
    let reserved: HashSet<&str> = [
        "id",
        "adapter",
        "command",
        "priority",
        "capabilities",
        "capability_priorities",
        "enabled",
        "transport_ceiling_tokens",
    ]
    .iter()
    .copied()
    .collect();
    let extra: HashMap<String, Value> = map
        .iter()
        .filter(|(k, _)| !reserved.contains(k.as_str()))
        .map(|(k, v)| (k.clone(), v.clone()))
        .collect();

    Some(ProviderDef {
        id,
        adapter,
        command,
        priority,
        capabilities,
        capability_priorities,
        transport_ceiling_tokens,
        extra,
    })
}

/// Build a ranked provider list from the executor settings object.
///
/// If `config["providers"]` is absent or empty a single default entry is
/// synthesised (matching the Python fallback), then supplemented with any
/// environment-variable auto-detected providers.
///
/// Providers are sorted by descending priority (capability-specific first,
/// then overall).
pub fn routed_provider_definitions(config: &Value) -> Vec<ProviderDef> {
    let mut providers: Vec<ProviderDef> = match config.get("providers").and_then(Value::as_array) {
        Some(arr) if !arr.is_empty() => arr.iter().filter_map(parse_provider).collect(),
        _ => {
            // Fallback: single primary entry derived from `command` setting.
            let command = config
                .get("command")
                .and_then(Value::as_str)
                .unwrap_or("codex")
                .to_string();
            vec![ProviderDef {
                id: "primary".into(),
                adapter: "codex-cli".into(),
                command: Some(command),
                priority: 100,
                capabilities: DEFAULT_CAPABILITIES.iter().map(|s| s.to_string()).collect(),
                capability_priorities: HashMap::new(),
                transport_ceiling_tokens: None,
                extra: HashMap::new(),
            }]
        }
    };

    // Supplement with zero-config env-var providers (no duplicate IDs).
    let existing_ids: HashSet<String> = providers.iter().map(|p| p.id.clone()).collect();
    for ep in env_auto_providers() {
        if !existing_ids.contains(&ep.id) {
            providers.push(ep);
        }
    }

    // Sort: highest priority first.
    providers.sort_by(|a, b| b.priority.cmp(&a.priority).then(a.id.cmp(&b.id)));
    providers
}

// ── Provider selection ────────────────────────────────────────────────────────

/// Select the best provider for `task` from an ordered slice.
///
/// Rules (in order):
/// 1. Provider must list `task.capability` in its `capabilities`.
/// 2. Among compatible providers, the one with the highest capability-specific
///    priority wins.
/// 3. Transport ceiling: if the provider has `transport_ceiling_tokens` and the
///    task's `context_tokens` exceeds it, the provider is skipped.
///
/// Returns `None` if no compatible provider exists.
pub fn select_provider<'a>(
    providers: &'a [ProviderDef],
    task: &TaskSpec,
) -> Option<&'a ProviderDef> {
    providers
        .iter()
        .filter(|p| p.capabilities.iter().any(|c| c == &task.capability))
        .filter(|p| {
            // Transport ceiling check.
            match (p.transport_ceiling_tokens, task.context_tokens) {
                (Some(ceiling), Some(tokens)) => tokens <= ceiling,
                _ => true,
            }
        })
        .max_by_key(|p| p.capability_priority(&task.capability))
}

// ── Tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn make_provider(id: &str, priority: i64, caps: &[&str]) -> ProviderDef {
        ProviderDef {
            id: id.to_string(),
            adapter: "codex-cli".to_string(),
            command: Some("codex".to_string()),
            priority,
            capabilities: caps.iter().map(|s| s.to_string()).collect(),
            capability_priorities: HashMap::new(),
            transport_ceiling_tokens: None,
            extra: HashMap::new(),
        }
    }

    // ── classify_unavailability ───────────────────────────────────────────────

    #[test]
    fn classify_rate_limit() {
        assert_eq!(
            classify_unavailability("Error: usage limit reached"),
            UnavailabilityClass::RateLimit
        );
        assert_eq!(
            classify_unavailability("quota exceeded for today"),
            UnavailabilityClass::RateLimit
        );
    }

    #[test]
    fn classify_auth_failure() {
        assert_eq!(
            classify_unavailability("401 Unauthorized"),
            UnavailabilityClass::AuthFailure
        );
        assert_eq!(
            classify_unavailability("Invalid API key provided"),
            UnavailabilityClass::AuthFailure
        );
    }

    #[test]
    fn classify_execution_env() {
        assert_eq!(
            classify_unavailability("sandbox could not initialize"),
            UnavailabilityClass::ExecutionEnvironment
        );
    }

    #[test]
    fn classify_network_error() {
        assert_eq!(
            classify_unavailability("502 Bad Gateway returned"),
            UnavailabilityClass::NetworkError
        );
        assert_eq!(
            classify_unavailability("stream disconnected mid-response"),
            UnavailabilityClass::NetworkError
        );
    }

    #[test]
    fn classify_unknown() {
        assert_eq!(
            classify_unavailability("something completely unexpected"),
            UnavailabilityClass::Unknown
        );
    }

    #[test]
    fn rate_limit_takes_precedence_over_auth() {
        // A message containing both rate-limit and auth markers → RateLimit wins.
        assert_eq!(
            classify_unavailability("401 rate limit exceeded"),
            UnavailabilityClass::RateLimit
        );
    }

    // ── select_provider ───────────────────────────────────────────────────────

    #[test]
    fn select_highest_priority_compatible() {
        let providers = vec![
            make_provider("low", 50, &["mutation"]),
            make_provider("high", 90, &["mutation"]),
            make_provider("mid", 70, &["mutation"]),
        ];
        let task = TaskSpec {
            capability: "mutation".into(),
            context_tokens: None,
            extra: HashMap::new(),
        };
        let selected = select_provider(&providers, &task).unwrap();
        assert_eq!(selected.id, "high");
    }

    #[test]
    fn select_skips_incompatible_capability() {
        let providers = vec![
            make_provider("only-discovery", 100, &["discovery"]),
            make_provider("mutation-low", 20, &["mutation"]),
        ];
        let task = TaskSpec {
            capability: "mutation".into(),
            context_tokens: None,
            extra: HashMap::new(),
        };
        let selected = select_provider(&providers, &task).unwrap();
        assert_eq!(selected.id, "mutation-low");
    }

    #[test]
    fn select_returns_none_when_no_compatible() {
        let providers = vec![make_provider("only-discovery", 100, &["discovery"])];
        let task = TaskSpec {
            capability: "mutation".into(),
            context_tokens: None,
            extra: HashMap::new(),
        };
        assert!(select_provider(&providers, &task).is_none());
    }

    #[test]
    fn transport_ceiling_respected() {
        let mut provider_small = make_provider("small", 100, &["mutation"]);
        provider_small.transport_ceiling_tokens = Some(1000);
        let mut provider_large = make_provider("large", 50, &["mutation"]);
        provider_large.transport_ceiling_tokens = Some(100_000);

        let providers = vec![provider_small, provider_large];
        let task = TaskSpec {
            capability: "mutation".into(),
            context_tokens: Some(50_000),
            extra: HashMap::new(),
        };
        // `small` has higher priority but ceiling too low; `large` should be chosen.
        let selected = select_provider(&providers, &task).unwrap();
        assert_eq!(selected.id, "large");
    }

    #[test]
    fn transport_ceiling_exact_boundary_allowed() {
        let mut p = make_provider("exact", 100, &["mutation"]);
        p.transport_ceiling_tokens = Some(8192);
        let providers = vec![p];
        let task = TaskSpec {
            capability: "mutation".into(),
            context_tokens: Some(8192),
            extra: HashMap::new(),
        };
        assert!(select_provider(&providers, &task).is_some());
    }

    // ── routed_provider_definitions ──────────────────────────────────────────

    #[test]
    fn routed_fallback_primary_created() {
        let config = json!({});
        let defs = routed_provider_definitions(&config);
        assert!(defs.iter().any(|p| p.id == "primary"));
    }

    #[test]
    fn routed_uses_explicit_providers() {
        let config = json!({
            "providers": [
                {"id": "my-provider", "adapter": "claude-cli", "command": "claude", "priority": 100,
                 "capabilities": ["mutation"]}
            ]
        });
        let defs = routed_provider_definitions(&config);
        assert!(defs.iter().any(|p| p.id == "my-provider"));
        // The fallback "primary" should NOT appear when explicit list provided.
        assert!(!defs.iter().any(|p| p.id == "primary"));
    }

    #[test]
    fn routed_disabled_provider_excluded() {
        let config = json!({
            "providers": [
                {"id": "enabled-one", "adapter": "codex-cli", "priority": 100,
                 "capabilities": ["mutation"]},
                {"id": "disabled-one", "adapter": "codex-cli", "priority": 90,
                 "capabilities": ["mutation"], "enabled": false}
            ]
        });
        let defs = routed_provider_definitions(&config);
        assert!(defs.iter().any(|p| p.id == "enabled-one"));
        assert!(!defs.iter().any(|p| p.id == "disabled-one"));
    }
}
