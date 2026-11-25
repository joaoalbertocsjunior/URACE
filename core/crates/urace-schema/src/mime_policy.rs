//! MIME type policy enforcement.
//!
//! Rust port of `mime_policy.py` — Asset Lineage Enforcement (ALE).
//!
//! Default policy: `quality_gate_only` — only types that satisfy BOTH:
//!   1. ALE hard-protection (STRONG or MEDIUM Winnowing/fingerprinting coverage)
//!   2. APS quality-gate scorability (objective outcome delta computable by URACE)

use std::collections::HashSet;

// ── Type sets ─────────────────────────────────────────────────────────────────

fn never_allowed() -> HashSet<&'static str> {
    [
        "text/css",
        "text/x-scss",
        "text/x-sass",
        "text/x-less",
        "text/html",
        "application/xhtml+xml",
        "text/x-csrc",
    ]
    .into_iter()
    .collect()
}

fn tier1_code_types() -> HashSet<&'static str> {
    [
        "text/x-python",
        "application/x-python",
        "text/javascript",
        "text/typescript",
        "application/javascript",
        "application/typescript",
        "text/x-java-source",
        "text/x-ruby",
        "application/x-ruby",
        "text/x-sh",
        "application/x-sh",
        "text/x-c",
        "text/x-c++src",
        "text/x-go",
        "text/x-rust",
        "application/x-httpd-php",
    ]
    .into_iter()
    .collect()
}

fn tier2_dependent_types() -> HashSet<&'static str> {
    [
        "application/json",
        "application/x-ndjson",
        "application/jsonl",
        "text/csv",
        "application/xml",
        "text/xml",
        "text/plain",
        "text/markdown",
    ]
    .into_iter()
    .collect()
}

fn strong_protected() -> HashSet<&'static str> {
    [
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
        "image/bmp",
        "image/tiff",
        "image/svg+xml",
        "image/avif",
        "image/heic",
        "text/csv",
        "application/json",
        "application/x-ndjson",
        "application/jsonl",
        "application/xml",
        "text/xml",
        "application/zip",
        "application/x-zip-compressed",
    ]
    .into_iter()
    .collect()
}

fn medium_protected() -> HashSet<&'static str> {
    [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/msword",
        "application/vnd.ms-excel",
        "application/vnd.ms-powerpoint",
        "text/plain",
        "text/markdown",
        "text/x-python",
        "text/x-java-source",
        "text/javascript",
        "text/typescript",
        "text/x-ruby",
        "text/x-sh",
        "text/x-c",
        "text/x-c++src",
        "text/x-go",
        "text/x-rust",
        "application/javascript",
        "application/x-python",
        "application/typescript",
        "application/x-sh",
        "application/x-ruby",
        "application/x-httpd-php",
    ]
    .into_iter()
    .collect()
}

// ── Policy enum ──────────────────────────────────────────────────────────────

/// Network-level MIME enforcement policy.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub enum Policy {
    /// Default: ALE hard-protected AND APS quality-gate scorable.
    #[default]
    QualityGateOnly,
    /// STRONG+MEDIUM ALE protection only (broader; includes PDF/images).
    HardProtectedOnly,
    /// Any MIME type allowed.
    AllAllowed,
    /// Explicit allowlist supplied at construction.
    Custom(Vec<String>),
}

impl Policy {
    /// Parse from the string values used in `config.json`.
    pub fn parse(s: &str) -> Self {
        match s {
            "hard_protected_only" => Policy::HardProtectedOnly,
            "all_allowed" => Policy::AllAllowed,
            _ => Policy::QualityGateOnly,
        }
    }
}

// ── MimePolicy ───────────────────────────────────────────────────────────────

/// Enforces the MIME admission policy for a node.
///
/// The network-level policy is `quality_gate_only` and cannot be relaxed
/// through user config (`is_network_allowed`). Per-node policy can be
/// configured and is checked via `is_allowed`.
#[derive(Debug, Clone, Default)]
pub struct MimePolicy {
    policy: Policy,
}

impl MimePolicy {
    /// Create a new `MimePolicy` with the default `quality_gate_only` policy.
    pub fn new() -> Self {
        Self::default()
    }

    /// Create with a specific policy.
    pub fn with_policy(policy: Policy) -> Self {
        Self { policy }
    }

    /// Create from config JSON (reads `p2p.mime_policy` and
    /// `p2p.allowed_asset_mime_types` for custom policy).
    pub fn from_config(config: &serde_json::Value) -> Self {
        let policy_str = config
            .pointer("/p2p/mime_policy")
            .and_then(|v| v.as_str())
            .unwrap_or("quality_gate_only");

        if policy_str == "custom" {
            let allowlist: Vec<String> = config
                .pointer("/p2p/allowed_asset_mime_types")
                .and_then(|v| v.as_array())
                .map(|arr| {
                    arr.iter()
                        .filter_map(|v| v.as_str().map(str::to_owned))
                        .collect()
                })
                .unwrap_or_default();
            Self {
                policy: Policy::Custom(allowlist),
            }
        } else {
            Self {
                policy: Policy::parse(policy_str),
            }
        }
    }

    /// Check whether `mime` is allowed under this node's configured policy.
    pub fn is_allowed(&self, mime: &str) -> bool {
        self.check(mime).0
    }

    /// Like `is_allowed` but also returns a human-readable reason string.
    pub fn check(&self, mime: &str) -> (bool, String) {
        let ct = normalise(mime);
        is_allowed_with_policy(ct, &self.policy)
    }

    /// Protocol-level gate: always uses `quality_gate_only`, ignoring per-node config.
    pub fn is_network_allowed(mime: &str) -> (bool, String) {
        let ct = normalise(mime);
        is_allowed_with_policy(ct, &Policy::QualityGateOnly)
    }

    /// Return the protection level string for a MIME type.
    pub fn protection_level(mime: &str) -> &'static str {
        let ct = normalise(mime);
        protection_level_inner(ct)
    }
}

// ── Internal helpers ─────────────────────────────────────────────────────────

fn normalise(mime: &str) -> &str {
    mime.trim().split(';').next().unwrap_or("").trim()
}

fn protection_level_inner(ct: &str) -> &'static str {
    if never_allowed().contains(ct) {
        return "never";
    }
    if strong_protected().contains(ct) {
        return "strong";
    }
    if medium_protected().contains(ct) {
        return "medium";
    }
    if ct.starts_with("image/") {
        return "strong";
    }
    if ct.starts_with("video/") || ct.starts_with("audio/") {
        return "weak";
    }
    "unknown"
}

fn is_allowed_with_policy(ct: &str, policy: &Policy) -> (bool, String) {
    let ct_lower = ct.to_lowercase();
    let ct: &str = &ct_lower;

    match policy {
        Policy::AllAllowed => (true, "policy=all_allowed".into()),

        Policy::Custom(allowlist) => {
            if allowlist.is_empty() {
                return (
                    false,
                    "policy=custom but allowed_asset_mime_types is empty".into(),
                );
            }
            for pattern in allowlist {
                let p = pattern.to_lowercase();
                if p.ends_with("/*") {
                    let prefix = &p[..p.len() - 1]; // strip '*'
                    if ct.starts_with(prefix) {
                        return (true, format!("policy=custom allowlist match: {p}"));
                    }
                } else if ct == p {
                    return (true, format!("policy=custom allowlist match: {p}"));
                }
            }
            (
                false,
                format!("policy=custom: {ct:?} not in allowed_asset_mime_types"),
            )
        }

        Policy::HardProtectedOnly => {
            if never_allowed().contains(ct) {
                return (
                    false,
                    format!("policy=hard_protected_only: {ct:?} is in NEVER_ALLOWED"),
                );
            }
            match protection_level_inner(ct) {
                "strong" | "medium" => (
                    true,
                    format!(
                        "policy=hard_protected_only level={}",
                        protection_level_inner(ct)
                    ),
                ),
                "weak" => (
                    false,
                    format!("policy=hard_protected_only: {ct:?} has weak ALE protection"),
                ),
                _ => (
                    false,
                    format!("policy=hard_protected_only: {ct:?} has no ALE fingerprinting"),
                ),
            }
        }

        Policy::QualityGateOnly => {
            if never_allowed().contains(ct) {
                return (
                    false,
                    format!("policy=quality_gate_only: {ct:?} is in NEVER_ALLOWED"),
                );
            }
            // DEFAULT_ALLOWED = (tier1 ∪ tier2) ∩ (strong ∪ medium)
            let tier1 = tier1_code_types();
            let tier2 = tier2_dependent_types();
            let hard_protected: HashSet<&str> = strong_protected()
                .union(&medium_protected())
                .copied()
                .collect();

            let quality_gate_validatable: HashSet<&str> = tier1.union(&tier2).copied().collect();
            let default_allowed: HashSet<&str> = quality_gate_validatable
                .intersection(&hard_protected)
                .copied()
                .collect();

            if default_allowed.contains(ct) {
                return (true, "policy=quality_gate_only".into());
            }
            // Tier 1 code types with Winnowing coverage (medium protected) are admitted.
            if tier1.contains(ct) && matches!(protection_level_inner(ct), "strong" | "medium") {
                return (
                    true,
                    format!("policy=quality_gate_only tier-1 code type: {ct}"),
                );
            }
            let lvl = protection_level_inner(ct);
            if matches!(lvl, "strong" | "medium") {
                return (false, format!(
                    "policy=quality_gate_only: {ct:?} has ALE protection but cannot be reliably \
                     scored by the APS quality gate. Set p2p.mime_policy=hard_protected_only to allow."
                ));
            }
            (
                false,
                format!(
                    "policy=quality_gate_only: {ct:?} has no ALE hard-protection. \
                 Set p2p.mime_policy=hard_protected_only or p2p.mime_policy=all_allowed to permit."
                ),
            )
        }
    }
}

// ── Tests ────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn python_code_allowed_by_default() {
        let policy = MimePolicy::new();
        assert!(policy.is_allowed("text/x-python"));
    }

    #[test]
    fn css_denied_by_default() {
        let policy = MimePolicy::new();
        assert!(!policy.is_allowed("text/css"));
    }

    #[test]
    fn all_allowed_accepts_anything() {
        let policy = MimePolicy::with_policy(Policy::AllAllowed);
        assert!(policy.is_allowed("application/octet-stream"));
    }

    #[test]
    fn custom_policy_allowlist_match() {
        let policy = MimePolicy::with_policy(Policy::Custom(vec!["text/csv".into()]));
        assert!(policy.is_allowed("text/csv"));
        assert!(!policy.is_allowed("text/x-python"));
    }

    #[test]
    fn custom_policy_wildcard() {
        let policy = MimePolicy::with_policy(Policy::Custom(vec!["text/*".into()]));
        assert!(policy.is_allowed("text/plain"));
        assert!(!policy.is_allowed("application/json"));
    }

    #[test]
    fn network_always_quality_gate_only() {
        // Even if node uses all_allowed, network gate still uses quality_gate_only.
        let (allowed, _) = MimePolicy::is_network_allowed("text/x-python");
        assert!(allowed);
        let (denied, _) = MimePolicy::is_network_allowed("text/css");
        assert!(!denied);
    }

    #[test]
    fn pdf_denied_at_quality_gate() {
        let policy = MimePolicy::new();
        assert!(!policy.is_allowed("application/pdf"));
    }

    #[test]
    fn pdf_allowed_at_hard_protected() {
        let policy = MimePolicy::with_policy(Policy::HardProtectedOnly);
        assert!(policy.is_allowed("application/pdf"));
    }
}
