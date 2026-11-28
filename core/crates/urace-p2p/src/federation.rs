//! R-6: Federation — port of `federation.py`.
//!
//! Cross-federation requests require valid authority proofs.
//! Anti-replay: sequence IDs are monotonically increasing per network_id.
//!
//! Security invariant: `validate_authority_proof` MUST NOT default to true;
//! it returns false until wired to urace-authority (see TODO below).

use dashmap::DashMap;
use ed25519_dalek::{Signature, Signer, SigningKey, Verifier, VerifyingKey};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
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

// ── Signed authority proof (Phase 4) ─────────────────────────────────────────

/// A signed authority proof bundle for cross-federation use.
///
/// Contains the Objective, the authority_config, an ed25519 signature over the
/// canonical JSON (sorted keys), and the base64-encoded public key.
#[derive(Debug, Serialize, Deserialize)]
struct SignedProofBundle {
    objective: serde_json::Value,
    authority_config: serde_json::Map<String, serde_json::Value>,
    signature_hex: String,
    public_key_hex: String,
}

/// Produce a canonical JSON string with sorted keys for deterministic signing.
fn canonical_json(
    objective: &serde_json::Value,
    authority_config: &HashMap<String, serde_json::Value>,
) -> String {
    // Sort authority_config keys.
    let mut sorted_config: serde_json::Map<String, serde_json::Value> =
        serde_json::Map::new();
    let mut keys: Vec<&String> = authority_config.keys().collect();
    keys.sort();
    for k in keys {
        sorted_config.insert(k.clone(), authority_config[k].clone());
    }
    let payload = serde_json::json!({
        "authority_config": sorted_config,
        "objective": objective,
    });
    // serde_json preserves insertion order; the outer object has two keys in
    // alphabetical order already ("authority_config" < "objective").
    serde_json::to_string(&payload).unwrap_or_default()
}

/// Build a signed authority proof bundle for cross-federation use.
///
/// The proof is a JSON object containing the Objective, authority_config,
/// an ed25519 signature over the canonical JSON, and the node's public key
/// for verification.
///
/// `signing_key` must be 64 bytes: the first 32 bytes are the seed (private
/// scalar) and bytes 32..64 are the public key — matching ed25519-dalek 2.x
/// `SigningKey::to_keypair_bytes()` layout.
pub fn build_signed_proof(
    objective: &urace_authority::authority::Objective,
    authority_config: &HashMap<String, serde_json::Value>,
    signing_key: &[u8; 64],
) -> String {
    let signing_key_obj = match SigningKey::from_keypair_bytes(signing_key) {
        Ok(k) => k,
        Err(e) => {
            tracing::warn!("build_signed_proof: invalid signing key: {e}");
            return String::new();
        }
    };

    let objective_value = match serde_json::to_value(objective) {
        Ok(v) => v,
        Err(e) => {
            tracing::warn!("build_signed_proof: serialise objective failed: {e}");
            return String::new();
        }
    };

    let canonical = canonical_json(&objective_value, authority_config);
    let signature: Signature = signing_key_obj.sign(canonical.as_bytes());
    let verifying_key = signing_key_obj.verifying_key();

    let mut sorted_config: serde_json::Map<String, serde_json::Value> = serde_json::Map::new();
    let mut keys: Vec<&String> = authority_config.keys().collect();
    keys.sort();
    for k in keys {
        sorted_config.insert(k.clone(), authority_config[k].clone());
    }

    let bundle = SignedProofBundle {
        objective: objective_value,
        authority_config: sorted_config,
        signature_hex: hex::encode(signature.to_bytes()),
        public_key_hex: hex::encode(verifying_key.to_bytes()),
    };

    serde_json::to_string(&bundle).unwrap_or_default()
}

/// Validate a signed authority proof: verify ed25519 signature, then call resolve().
/// Returns true only for AutonomouslyAuthorized with a valid signature.
pub fn validate_signed_authority_proof(proof: &str) -> bool {
    use urace_authority::authority::resolve;
    use urace_types::AuthorityOutcome;

    let bundle: SignedProofBundle = match serde_json::from_str(proof) {
        Ok(b) => b,
        Err(_) => return false,
    };

    // Reconstruct the authority_config HashMap for canonical JSON.
    let authority_config: HashMap<String, serde_json::Value> =
        bundle.authority_config.clone().into_iter().collect();

    // Verify signature.
    let sig_bytes: [u8; 64] = match hex::decode(&bundle.signature_hex)
        .ok()
        .and_then(|b| b.try_into().ok())
    {
        Some(b) => b,
        None => return false,
    };
    let pub_bytes: [u8; 32] = match hex::decode(&bundle.public_key_hex)
        .ok()
        .and_then(|b| b.try_into().ok())
    {
        Some(b) => b,
        None => return false,
    };

    let verifying_key = match VerifyingKey::from_bytes(&pub_bytes) {
        Ok(k) => k,
        Err(_) => return false,
    };
    let signature = match Signature::from_bytes(&sig_bytes) {
        sig => sig,
    };

    let canonical = canonical_json(&bundle.objective, &authority_config);
    if verifying_key.verify(canonical.as_bytes(), &signature).is_err() {
        return false;
    }

    // Deserialize objective and run authority resolve.
    let objective: urace_authority::authority::Objective =
        match serde_json::from_value(bundle.objective) {
            Ok(o) => o,
            Err(_) => return false,
        };

    let resolution = resolve(&objective, &authority_config, None, &[]);
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

    // ── Signed proof tests (Phase 4) ─────────────────────────────────────────

    fn make_signing_key() -> [u8; 64] {
        use ed25519_dalek::SigningKey;
        // Deterministic test key: seed = [1u8; 32].
        let seed: [u8; 32] = [1u8; 32];
        let key = SigningKey::from_bytes(&seed);
        key.to_keypair_bytes()
    }

    fn impl_objective() -> urace_authority::authority::Objective {
        urace_authority::authority::Objective {
            id: None,
            scope: "implementation".into(),
            title: "apply linting fix to core module".into(),
            reason: Some("automated improvement cycle".into()),
            necessity_evidence: None,
            lower_impact_route_sufficient: None,
        }
    }

    fn impl_authority_config() -> HashMap<String, serde_json::Value> {
        let mut m = HashMap::new();
        m.insert(
            "delegated".into(),
            serde_json::json!(["local implementation changes"]),
        );
        m.insert("reserved".into(), serde_json::json!([]));
        m
    }

    #[test]
    fn signed_proof_validates() {
        let key = make_signing_key();
        let obj = impl_objective();
        let cfg = impl_authority_config();

        let proof = build_signed_proof(&obj, &cfg, &key);
        assert!(!proof.is_empty(), "proof must not be empty");
        assert!(
            validate_signed_authority_proof(&proof),
            "valid proof must pass validation"
        );
    }

    #[test]
    fn tampered_proof_fails_validation() {
        let key = make_signing_key();
        let obj = impl_objective();
        let cfg = impl_authority_config();

        let proof = build_signed_proof(&obj, &cfg, &key);

        // Tamper: flip one hex character in the signature.
        let mut tampered: serde_json::Value = serde_json::from_str(&proof).unwrap();
        let sig = tampered["signature_hex"].as_str().unwrap().to_owned();
        // Flip first char: '0' → '1', anything else → '0'
        let first_char = if sig.starts_with('0') { '1' } else { '0' };
        let new_sig = format!("{}{}", first_char, &sig[1..]);
        tampered["signature_hex"] = serde_json::Value::String(new_sig);

        assert!(
            !validate_signed_authority_proof(&tampered.to_string()),
            "tampered proof must fail"
        );
    }

    #[test]
    fn signed_proof_with_forbidden_title_fails() {
        let key = make_signing_key();
        let mut obj = impl_objective();
        obj.title = "override authority gate".into();
        let cfg = impl_authority_config();

        let proof = build_signed_proof(&obj, &cfg, &key);
        // Signature is valid but authority resolution must deny.
        assert!(
            !validate_signed_authority_proof(&proof),
            "forbidden phrase must be denied even with valid signature"
        );
    }

    #[test]
    fn empty_or_malformed_signed_proof_denied() {
        assert!(!validate_signed_authority_proof(""));
        assert!(!validate_signed_authority_proof("not-json"));
        assert!(!validate_signed_authority_proof("{}"));
    }
}
