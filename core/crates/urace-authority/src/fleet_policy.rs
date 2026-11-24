//! Owner-signed fleet policy with Ed25519 and monotonic generation enforcement.
//!
//! R-5 addition from mesh-llm pattern:
//! - `FleetPolicy` struct: owner_pubkey (Ed25519), generation (u64), rules, signature.
//! - Stale rejection: policy with generation <= last_seen_generation is silently dropped.
//! - §62z gate is UNCHANGED — fleet policy narrows the allow-set, never expands it.
//! - Propagation: policies are keyed under sha256(owner_pubkey) for Kademlia DHT storage.
//!   The P2P layer (R-7) handles DHT propagation; this module handles sign/verify/store.

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::HashMap;
use std::sync::Arc;
use parking_lot::RwLock;
use thiserror::Error;
use urace_crypto::ed25519::{verify as ed25519_verify, Keypair, PUBLIC_KEY_LENGTH, SIGNATURE_LENGTH};

#[derive(Debug, Error)]
pub enum FleetPolicyError {
    #[error("policy signature invalid")]
    InvalidSignature,
    #[error("stale policy: generation {incoming} <= last seen {last_seen}")]
    StaleGeneration { incoming: u64, last_seen: u64 },
    #[error("policy owner mismatch")]
    OwnerMismatch,
    #[error("serialization error: {0}")]
    Serialization(String),
}

/// A single policy rule that restricts or narrows what authority may be exercised.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct PolicyRule {
    /// The scope this rule applies to (matches `authority.rs` scope names).
    pub scope: String,
    /// Action: "deny" or "require_confirmation".
    pub action: String,
    /// Human-readable rationale.
    pub reason: String,
}

/// An owner-signed fleet policy.
///
/// Must be verified before accepting. generation must be strictly greater than
/// any previously seen generation for the same owner pubkey.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FleetPolicy {
    /// Ed25519 public key of the policy owner (32 bytes, hex-encoded).
    pub owner_pubkey_hex: String,
    /// Monotonically increasing generation counter. Stale policies are dropped.
    pub generation: u64,
    /// Policy rules applied before §62z authority resolution.
    pub rules: Vec<PolicyRule>,
    /// Ed25519 signature over canonical(owner_pubkey_hex + generation + rules).
    pub signature_hex: String,
}

impl FleetPolicy {
    /// Create and sign a new fleet policy.
    pub fn new(
        keypair: &Keypair,
        generation: u64,
        rules: Vec<PolicyRule>,
    ) -> Result<Self, FleetPolicyError> {
        let owner_pubkey_hex = hex::encode(keypair.public_key_bytes());
        let msg = canonical_message(&owner_pubkey_hex, generation, &rules)
            .map_err(|e| FleetPolicyError::Serialization(e.to_string()))?;
        let sig = keypair.sign(&msg);
        Ok(FleetPolicy {
            owner_pubkey_hex,
            generation,
            rules,
            signature_hex: hex::encode(sig),
        })
    }

    /// Verify the policy signature.
    pub fn verify(&self) -> Result<(), FleetPolicyError> {
        let pubkey_bytes = hex::decode(&self.owner_pubkey_hex)
            .map_err(|_| FleetPolicyError::InvalidSignature)?;
        if pubkey_bytes.len() != PUBLIC_KEY_LENGTH {
            return Err(FleetPolicyError::InvalidSignature);
        }
        let sig_bytes = hex::decode(&self.signature_hex)
            .map_err(|_| FleetPolicyError::InvalidSignature)?;
        if sig_bytes.len() != SIGNATURE_LENGTH {
            return Err(FleetPolicyError::InvalidSignature);
        }

        let msg = canonical_message(&self.owner_pubkey_hex, self.generation, &self.rules)
            .map_err(|_| FleetPolicyError::InvalidSignature)?;

        let mut pubkey = [0u8; PUBLIC_KEY_LENGTH];
        pubkey.copy_from_slice(&pubkey_bytes);
        let mut sig = [0u8; SIGNATURE_LENGTH];
        sig.copy_from_slice(&sig_bytes);

        ed25519_verify(&pubkey, &msg, &sig)
            .map_err(|_| FleetPolicyError::InvalidSignature)
    }

    /// DHT key for this policy: sha256(owner_pubkey_bytes).
    pub fn dht_key(&self) -> Vec<u8> {
        let pubkey_bytes = hex::decode(&self.owner_pubkey_hex).unwrap_or_default();
        let mut hasher = Sha256::new();
        hasher.update(&pubkey_bytes);
        hasher.finalize().to_vec()
    }
}

fn canonical_message(
    owner_pubkey_hex: &str,
    generation: u64,
    rules: &[PolicyRule],
) -> Result<Vec<u8>, serde_json::Error> {
    let v = serde_json::json!({
        "owner_pubkey_hex": owner_pubkey_hex,
        "generation": generation,
        "rules": rules,
    });
    serde_json::to_vec(&v)
}

/// In-memory policy store with stale rejection.
/// Keyed by owner_pubkey_hex; holds the highest-generation verified policy.
pub struct PolicyStore {
    inner: RwLock<HashMap<String, FleetPolicy>>,
}

impl PolicyStore {
    pub fn new() -> Self {
        PolicyStore { inner: RwLock::new(HashMap::new()) }
    }

    /// Accept and store a policy if it is valid and newer than any existing one.
    ///
    /// Returns `Err(StaleGeneration)` if stale; `Err(InvalidSignature)` if signature bad.
    pub fn accept(&self, policy: FleetPolicy) -> Result<(), FleetPolicyError> {
        // Verify signature first — always, before checking generation.
        policy.verify()?;

        let mut store = self.inner.write();
        if let Some(existing) = store.get(&policy.owner_pubkey_hex) {
            if policy.generation <= existing.generation {
                return Err(FleetPolicyError::StaleGeneration {
                    incoming: policy.generation,
                    last_seen: existing.generation,
                });
            }
        }
        store.insert(policy.owner_pubkey_hex.clone(), policy);
        Ok(())
    }

    pub fn get(&self, owner_pubkey_hex: &str) -> Option<FleetPolicy> {
        self.inner.read().get(owner_pubkey_hex).cloned()
    }

    pub fn all(&self) -> Vec<FleetPolicy> {
        self.inner.read().values().cloned().collect()
    }
}

impl Default for PolicyStore {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use rand::rngs::StdRng;
    use rand::SeedableRng;

    fn keypair() -> Keypair {
        Keypair::generate(&mut StdRng::seed_from_u64(42))
    }

    #[test]
    fn sign_and_verify() {
        let kp = keypair();
        let rules = vec![PolicyRule {
            scope: "runtime".into(),
            action: "deny".into(),
            reason: "no self-evolution in prod".into(),
        }];
        let policy = FleetPolicy::new(&kp, 1, rules).unwrap();
        assert!(policy.verify().is_ok());
    }

    #[test]
    fn stale_generation_rejected() {
        let kp = keypair();
        let store = PolicyStore::new();

        let p1 = FleetPolicy::new(&kp, 2, vec![]).unwrap();
        store.accept(p1).unwrap();

        let p0 = FleetPolicy::new(&kp, 1, vec![]).unwrap();
        assert!(matches!(store.accept(p0), Err(FleetPolicyError::StaleGeneration { .. })));
    }

    #[test]
    fn same_generation_rejected() {
        let kp = keypair();
        let store = PolicyStore::new();
        let p = FleetPolicy::new(&kp, 1, vec![]).unwrap();
        store.accept(p.clone()).unwrap();
        // second accept with same generation must fail
        let p2 = FleetPolicy::new(&kp, 1, vec![]).unwrap();
        assert!(matches!(store.accept(p2), Err(FleetPolicyError::StaleGeneration { .. })));
    }

    #[test]
    fn newer_generation_accepted() {
        let kp = keypair();
        let store = PolicyStore::new();
        store.accept(FleetPolicy::new(&kp, 1, vec![]).unwrap()).unwrap();
        store.accept(FleetPolicy::new(&kp, 2, vec![]).unwrap()).unwrap();
        assert_eq!(store.get(&hex::encode(kp.public_key_bytes())).unwrap().generation, 2);
    }

    #[test]
    fn tampered_policy_rejected() {
        let kp = keypair();
        let mut policy = FleetPolicy::new(&kp, 1, vec![]).unwrap();
        policy.generation = 99; // tamper without re-signing
        assert!(matches!(policy.verify(), Err(FleetPolicyError::InvalidSignature)));
    }

    #[test]
    fn dht_key_deterministic() {
        let kp = keypair();
        let p1 = FleetPolicy::new(&kp, 1, vec![]).unwrap();
        let p2 = FleetPolicy::new(&kp, 2, vec![]).unwrap();
        assert_eq!(p1.dht_key(), p2.dht_key()); // same owner → same DHT key
    }
}
