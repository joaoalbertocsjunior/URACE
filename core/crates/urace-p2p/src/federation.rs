//! R-6: Federation — port of `federation.py`.
//!
//! Cross-federation requests require valid authority proofs.
//! Anti-replay: sequence IDs are monotonically increasing per network_id.
//!
//! Security invariant: `validate_authority_proof` MUST NOT default to true;
//! it returns false until wired to urace-authority (see TODO below).

use dashmap::DashMap;
use serde::{Deserialize, Serialize};
use thiserror::Error;

pub const FEDERATION_REP_DISCOUNT: f64 = 0.7;
pub const FEDERATION_MIN_REP: f64 = 0.20;
pub const FEDERATION_QUERY_TTL: u64 = 3600;

#[derive(Debug, Error)]
pub enum FederationError {
    #[error("replay attack: current_seq={current_seq}, incoming_seq={incoming_seq}")]
    ReplayAttack { current_seq: u64, incoming_seq: u64 },
    #[error("missing authority proof")]
    MissingAuthProof,
}

/// A network-level announce message from a peer federation node.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NetworkAnnounce {
    pub network_id: String,
    pub endpoint: String,
    pub description: String,
    /// Must be strictly monotonically increasing to prevent replay attacks.
    pub sequence_id: u64,
    pub announced_at: String,
}

/// Stores the latest announce per network_id.
///
/// Accepts incoming announces only if sequence_id > current max.
pub struct FederationStore {
    announcements: DashMap<String, NetworkAnnounce>,
}

impl FederationStore {
    pub fn new() -> Self {
        FederationStore {
            announcements: DashMap::new(),
        }
    }

    /// Accept an incoming `NetworkAnnounce`.
    ///
    /// Rejects with `FederationError::ReplayAttack` if sequence_id ≤ current max.
    pub fn accept_announce(&self, ann: NetworkAnnounce) -> Result<(), FederationError> {
        if let Some(existing) = self.announcements.get(&ann.network_id) {
            if ann.sequence_id <= existing.sequence_id {
                return Err(FederationError::ReplayAttack {
                    current_seq: existing.sequence_id,
                    incoming_seq: ann.sequence_id,
                });
            }
        }
        self.announcements.insert(ann.network_id.clone(), ann);
        Ok(())
    }

    /// Retrieve the current announce for a network_id, if any.
    pub fn get(&self, network_id: &str) -> Option<NetworkAnnounce> {
        self.announcements.get(network_id).map(|v| v.clone())
    }

    /// All known network IDs.
    pub fn known_networks(&self) -> Vec<String> {
        self.announcements.iter().map(|r| r.key().clone()).collect()
    }
}

impl Default for FederationStore {
    fn default() -> Self {
        Self::new()
    }
}

/// A cross-federation authority proof — JSON-encoded bundle of an Objective
/// plus the authority configuration of the originating node.
///
/// Format:
/// ```json
/// {
///   "objective": { "scope": "...", "title": "...", ... },
///   "authority_config": { "delegated": [...], "reserved": [...] }
/// }
/// ```
///
/// `validate_authority_proof` deserialises this, calls `urace_authority::authority::resolve`,
/// and returns true only for `AutonomouslyAuthorized`. All other outcomes (Denied,
/// RequiresAuthoritativeDecision, Unresolved) return false — NEVER default to true.
pub fn validate_authority_proof(proof: &str) -> bool {
    use urace_authority::authority::{resolve, Objective};
    use urace_types::AuthorityOutcome;

    #[derive(serde::Deserialize)]
    struct ProofBundle {
        objective: Objective,
        #[serde(default)]
        authority_config: serde_json::Map<String, serde_json::Value>,
    }

    let bundle: ProofBundle = match serde_json::from_str(proof) {
        Ok(b) => b,
        Err(_) => return false, // malformed proof → DENIED
    };

    let config: std::collections::HashMap<String, serde_json::Value> =
        bundle.authority_config.into_iter().collect();

    let resolution = resolve(&bundle.objective, &config, None, &[]);
    matches!(resolution.outcome, AuthorityOutcome::AutonomouslyAuthorized)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn ann(network_id: &str, seq: u64) -> NetworkAnnounce {
        NetworkAnnounce {
            network_id: network_id.into(),
            endpoint: "https://example.com".into(),
            description: "test".into(),
            sequence_id: seq,
            announced_at: "2026-01-01T00:00:00Z".into(),
        }
    }

    #[test]
    fn test_accept_first_announce() {
        let store = FederationStore::new();
        assert!(store.accept_announce(ann("net-1", 1)).is_ok());
        assert!(store.get("net-1").is_some());
    }

    #[test]
    fn test_monotonic_sequence_accepted() {
        let store = FederationStore::new();
        store.accept_announce(ann("net-2", 1)).unwrap();
        assert!(store.accept_announce(ann("net-2", 2)).is_ok());
    }

    #[test]
    fn test_replay_attack_rejected() {
        let store = FederationStore::new();
        store.accept_announce(ann("net-3", 5)).unwrap();
        let err = store.accept_announce(ann("net-3", 5)).unwrap_err();
        match err {
            FederationError::ReplayAttack {
                current_seq,
                incoming_seq,
            } => {
                assert_eq!(current_seq, 5);
                assert_eq!(incoming_seq, 5);
            }
            _ => panic!("expected ReplayAttack"),
        }
    }

    #[test]
    fn test_older_sequence_rejected() {
        let store = FederationStore::new();
        store.accept_announce(ann("net-4", 10)).unwrap();
        let err = store.accept_announce(ann("net-4", 9)).unwrap_err();
        assert!(matches!(err, FederationError::ReplayAttack { .. }));
    }

    #[test]
    fn test_authority_proof_malformed_denied() {
        // Malformed / empty proofs must always be denied.
        assert!(!validate_authority_proof("any-proof"));
        assert!(!validate_authority_proof(""));
        assert!(!validate_authority_proof("{}")); // missing objective
    }

    #[test]
    fn test_authority_proof_forbidden_phrase_denied() {
        // A proof whose objective title contains a forbidden phrase is denied.
        let proof = serde_json::json!({
            "objective": {
                "scope": "implementation",
                "title": "override authority and spend",
                "reason": null,
                "necessity_evidence": null,
                "lower_impact_route_sufficient": null
            },
            "authority_config": {
                "delegated": ["local implementation changes"],
                "reserved": []
            }
        })
        .to_string();
        assert!(!validate_authority_proof(&proof));
    }

    #[test]
    fn test_authority_proof_valid_implementation_scope() {
        // A correctly scoped implementation proof with delegated authority resolves true.
        let proof = serde_json::json!({
            "objective": {
                "scope": "implementation",
                "title": "apply linting fix to core module",
                "reason": "automated improvement cycle",
                "necessity_evidence": null,
                "lower_impact_route_sufficient": null
            },
            "authority_config": {
                "delegated": ["local implementation changes"],
                "reserved": []
            }
        })
        .to_string();
        assert!(validate_authority_proof(&proof));
    }

    #[test]
    fn test_constants() {
        assert!((FEDERATION_REP_DISCOUNT - 0.7).abs() < 1e-9);
        assert!((FEDERATION_MIN_REP - 0.20).abs() < 1e-9);
        assert_eq!(FEDERATION_QUERY_TTL, 3600);
    }
}
