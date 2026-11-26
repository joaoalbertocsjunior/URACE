//! M79 — Model provider fingerprinting: detect provider identity changes between requests.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ModelFingerprint {
    pub provider_id: String,
    pub model_version: String,
    /// SHA-256 of (provider_id || model_version), hex.
    pub fingerprint_hash: String,
}

impl ModelFingerprint {
    pub fn new(provider_id: impl Into<String>, model_version: impl Into<String>) -> Self {
        let provider_id = provider_id.into();
        let model_version = model_version.into();
        let fingerprint_hash = compute_fingerprint_hash(&provider_id, &model_version);
        ModelFingerprint {
            provider_id,
            model_version,
            fingerprint_hash,
        }
    }
}

fn compute_fingerprint_hash(provider_id: &str, model_version: &str) -> String {
    use sha2::{Digest, Sha256};
    let mut h = Sha256::new();
    h.update(provider_id.as_bytes());
    h.update(model_version.as_bytes());
    hex::encode(h.finalize())
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum FingerprintChange {
    Unchanged,
    VersionChanged { old: String, new: String },
    ProviderChanged { old: String, new: String },
}

pub struct FingerprintRegistry {
    // provider_id -> last seen ModelFingerprint
    registry: HashMap<String, ModelFingerprint>,
}

impl FingerprintRegistry {
    pub fn new() -> Self {
        FingerprintRegistry {
            registry: HashMap::new(),
        }
    }

    /// Register or update a provider's fingerprint. Returns the kind of change detected.
    pub fn register(&mut self, fp: ModelFingerprint) -> FingerprintChange {
        match self.registry.get(&fp.provider_id) {
            None => {
                // First time seeing this provider — no previous baseline to compare against.
                self.registry.insert(fp.provider_id.clone(), fp);
                FingerprintChange::Unchanged
            }
            Some(existing) => {
                let change = if existing.provider_id != fp.provider_id {
                    FingerprintChange::ProviderChanged {
                        old: existing.provider_id.clone(),
                        new: fp.provider_id.clone(),
                    }
                } else if existing.model_version != fp.model_version {
                    FingerprintChange::VersionChanged {
                        old: existing.model_version.clone(),
                        new: fp.model_version.clone(),
                    }
                } else {
                    FingerprintChange::Unchanged
                };
                self.registry.insert(fp.provider_id.clone(), fp);
                change
            }
        }
    }

    pub fn get(&self, provider_id: &str) -> Option<&ModelFingerprint> {
        self.registry.get(provider_id)
    }

    pub fn provider_count(&self) -> usize {
        self.registry.len()
    }
}

impl Default for FingerprintRegistry {
    fn default() -> Self {
        Self::new()
    }
}

// ── Tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn first_registration_is_unchanged() {
        let mut reg = FingerprintRegistry::new();
        let fp = ModelFingerprint::new("openai", "gpt-4o");
        let change = reg.register(fp);
        assert_eq!(change, FingerprintChange::Unchanged);
        assert_eq!(reg.provider_count(), 1);
    }

    #[test]
    fn same_version_is_unchanged() {
        let mut reg = FingerprintRegistry::new();
        reg.register(ModelFingerprint::new("anthropic", "claude-3-5-sonnet"));
        let fp2 = ModelFingerprint::new("anthropic", "claude-3-5-sonnet");
        let change = reg.register(fp2);
        assert_eq!(change, FingerprintChange::Unchanged);
    }

    #[test]
    fn version_change_detected() {
        let mut reg = FingerprintRegistry::new();
        reg.register(ModelFingerprint::new("anthropic", "claude-3-5-sonnet"));
        let fp2 = ModelFingerprint::new("anthropic", "claude-3-7-sonnet");
        let change = reg.register(fp2);
        assert_eq!(
            change,
            FingerprintChange::VersionChanged {
                old: "claude-3-5-sonnet".into(),
                new: "claude-3-7-sonnet".into(),
            }
        );
    }

    #[test]
    fn provider_count_tracks_distinct_providers() {
        let mut reg = FingerprintRegistry::new();
        reg.register(ModelFingerprint::new("openai", "gpt-4o"));
        reg.register(ModelFingerprint::new("anthropic", "claude-3-5-sonnet"));
        reg.register(ModelFingerprint::new("openai", "gpt-4o-mini")); // update existing
        assert_eq!(reg.provider_count(), 2);
    }

    #[test]
    fn get_returns_latest_fingerprint() {
        let mut reg = FingerprintRegistry::new();
        reg.register(ModelFingerprint::new("openai", "gpt-4o"));
        reg.register(ModelFingerprint::new("openai", "gpt-4o-mini"));
        let fp = reg.get("openai").unwrap();
        assert_eq!(fp.model_version, "gpt-4o-mini");
    }

    #[test]
    fn fingerprint_hash_is_deterministic() {
        let fp1 = ModelFingerprint::new("openai", "gpt-4o");
        let fp2 = ModelFingerprint::new("openai", "gpt-4o");
        assert_eq!(fp1.fingerprint_hash, fp2.fingerprint_hash);
    }

    #[test]
    fn fingerprint_hash_differs_for_different_versions() {
        let fp1 = ModelFingerprint::new("openai", "gpt-4o");
        let fp2 = ModelFingerprint::new("openai", "gpt-4o-mini");
        assert_ne!(fp1.fingerprint_hash, fp2.fingerprint_hash);
    }
}
