//! Evidence types and verification logic for P2P-borrow vs direct-executor matched pairs.
//!
//! Ported from `trial/p2p_pair_protocol.py`. Resource dimensions are reported
//! separately; URACE reputation units are never converted to money or provider
//! tokens without an explicit, verified rate.

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use thiserror::Error;

use crate::trial_common::{MINIMUM_PAIRS, MINIMUM_PER_FAMILY};

// ---------------------------------------------------------------------------
// Schema constants
// ---------------------------------------------------------------------------

/// Wire schema identifier for a P2P executor pair record.
pub const SCHEMA: &str = "urace-p2p-executor-pair-v2";

/// Wire schema identifier for paired cost receipts.
pub const COST_SCHEMA: &str = "urace-p2p-paired-cost-v1";

/// Arm names for a matched pair.
pub const ARMS: [&str; 2] = ["direct_executor", "p2p_borrow"];

/// Recognised task families for the P2P study.
pub const FAMILIES: [&str; 5] = [
    "navigation",
    "recovery",
    "receipts",
    "requirements_change",
    "integration",
];

// ---------------------------------------------------------------------------
// Errors
// ---------------------------------------------------------------------------

/// Errors that can occur during P2P pair verification.
#[derive(Debug, Error)]
pub enum PairError {
    #[error("pair schema or structure invalid: {0}")]
    InvalidSchema(String),
    #[error("evidence file error: {0}")]
    Evidence(String),
    #[error("cryptographic verification failed: {0}")]
    Crypto(String),
    #[error("cost receipt mismatch: {0}")]
    CostMismatch(String),
    #[error("serialization error: {0}")]
    Serialization(#[from] serde_json::Error),
}

// ---------------------------------------------------------------------------
// Economic claim policy (preregistered — must not be altered)
// ---------------------------------------------------------------------------

/// Build the canonical economic claim policy object.
///
/// Any deviation from this exact policy causes plan verification to fail.
pub fn economic_claim_policy() -> serde_json::Value {
    serde_json::json!({
        "schema": "urace-p2p-economic-claim-policy-v1",
        "scope": "cohort_specific_end_to_end_usd",
        "bootstrap": "paired_percentile",
        "confidence_level": 0.95,
        "replicates": 10000,
        "minimum_valid_pairs": MINIMUM_PAIRS,
        "minimum_pairs_per_family": MINIMUM_PER_FAMILY,
        "require_both_arms_accepted_each_pair": true,
        "require_p2p_value_not_below_direct_each_pair": true,
        "require_zero_urace_units_paid": true,
        "provider_cost_bases": ["ACTUAL_MARGINAL", "SUBSCRIPTION_ALLOCATED"],
        "independent_claim_reviewers": 2
    })
}

// ---------------------------------------------------------------------------
// Record types
// ---------------------------------------------------------------------------

/// A single arm's contribution within a matched pair.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PairArm {
    /// "direct_executor" or "p2p_borrow".
    pub arm: String,
    /// Pair this arm belongs to.
    pub pair_id: String,
    /// Product being tested.
    pub product_id: String,
    /// Provider identifier (e.g. "claude", "codex").
    pub provider: String,
    /// Model identifier.
    pub model: String,
    /// Client version string.
    pub client_version: String,
    /// Effort level: "low", "medium", or "high".
    pub effort: String,
    /// Exactly one provider, equal to `provider`.
    pub actual_providers: Vec<String>,
    /// SHA-256 of the frozen task text.
    pub task_sha256: String,
    /// SHA-256 of the frozen acceptance contract.
    pub acceptance_contract_sha256: String,
    /// Native provider receipts (may be empty for a zero-call P2P arm).
    #[serde(default)]
    pub native_receipts: Vec<serde_json::Value>,
    /// Path of the signed acceptance receipt file, relative to the study root.
    pub acceptance_receipt_path: String,
    /// SHA-256 of the acceptance receipt bytes.
    pub acceptance_receipt_sha256: String,
    /// Any extra fields (delivery metadata, no-call evidence, etc.).
    #[serde(flatten)]
    pub extra: std::collections::HashMap<String, serde_json::Value>,
}

/// Task identity fields embedded in a pair record.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PairTask {
    pub pair_id: String,
    pub task_id: String,
    pub task_sha256: String,
    pub acceptance_contract_sha256: String,
    pub value_rubric_sha256: String,
    pub family: String,
    pub repeat: u32,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub source_asset: Option<SourceAsset>,
}

/// Optional source-asset provenance attached to a task.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct SourceAsset {
    pub feature_id: String,
    pub artifact_sha256: String,
    pub source_manifest_sha256: String,
    pub source_paths: Vec<String>,
}

/// A complete matched pair record (schema + arms + task).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PairRecord {
    pub schema: String,
    pub task: PairTask,
    pub arm_order: Vec<String>,
    pub arms: std::collections::HashMap<String, PairArm>,
    #[serde(default)]
    pub runner_errors: std::collections::HashMap<String, String>,
    pub cohort_sha256: String,
}

/// Outcome of verifying a single pair.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PairVerification {
    /// "PAIR_VALID_RESOURCE_COMPARISON" or "PAIR_INELIGIBLE".
    pub status: String,
    pub pair_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub reason: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub family: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub provider: Option<String>,
}

// ---------------------------------------------------------------------------
// SHA-256 helper
// ---------------------------------------------------------------------------

/// Compute the hex-encoded SHA-256 of arbitrary bytes.
pub fn sha256_hex(data: &[u8]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(data);
    hex::encode(hasher.finalize())
}

/// Return `true` iff `hex_str` is a valid lower-case 64-character hex string.
pub fn is_valid_sha256_hex(hex_str: &str) -> bool {
    hex_str.len() == 64
        && hex_str
            .chars()
            .all(|c| c.is_ascii_hexdigit() && !c.is_uppercase())
}

// ---------------------------------------------------------------------------
// Minimal structural verification (no live crypto — mirrors Python guards)
// ---------------------------------------------------------------------------

/// Validate that an arm's key identity fields are self-consistent.
///
/// Returns `Err` with a descriptive message on the first violation found.
pub fn validate_arm_identity(arm: &PairArm, task: &PairTask) -> Result<(), PairError> {
    if !ARMS.contains(&arm.arm.as_str()) {
        return Err(PairError::InvalidSchema(format!(
            "unknown arm name: {}",
            arm.arm
        )));
    }
    if arm.pair_id != task.pair_id {
        return Err(PairError::InvalidSchema(
            "arm pair_id does not match task pair_id".into(),
        ));
    }
    if arm.task_sha256 != task.task_sha256 {
        return Err(PairError::InvalidSchema(
            "arm task_sha256 differs from pair task".into(),
        ));
    }
    if arm.acceptance_contract_sha256 != task.acceptance_contract_sha256 {
        return Err(PairError::InvalidSchema(
            "arm acceptance_contract_sha256 differs from pair task".into(),
        ));
    }
    if arm.actual_providers != vec![arm.provider.clone()] {
        return Err(PairError::InvalidSchema(
            "arm must declare exactly one provider equal to its provider field".into(),
        ));
    }
    if !["codex", "claude"].contains(&arm.provider.as_str()) {
        return Err(PairError::InvalidSchema(format!(
            "unsupported provider: {}",
            arm.provider
        )));
    }
    if !["low", "medium", "high"].contains(&arm.effort.as_str()) {
        return Err(PairError::InvalidSchema(format!(
            "invalid effort: {}",
            arm.effort
        )));
    }
    Ok(())
}

/// Validate that both arms of a pair use identical executor profiles.
pub fn validate_arm_profile_match(direct: &PairArm, p2p: &PairArm) -> Result<(), PairError> {
    for key in &[
        "product_id",
        "provider",
        "model",
        "client_version",
        "effort",
    ] {
        let d = match *key {
            "product_id" => &direct.product_id,
            "provider" => &direct.provider,
            "model" => &direct.model,
            "client_version" => &direct.client_version,
            "effort" => &direct.effort,
            _ => unreachable!(),
        };
        let p = match *key {
            "product_id" => &p2p.product_id,
            "provider" => &p2p.provider,
            "model" => &p2p.model,
            "client_version" => &p2p.client_version,
            "effort" => &p2p.effort,
            _ => unreachable!(),
        };
        if d != p {
            return Err(PairError::InvalidSchema(format!(
                "pair arms differ on {}: {} vs {}",
                key, d, p
            )));
        }
    }
    Ok(())
}

/// Lightweight structural check on a `PairRecord`.
///
/// Verifies schema tag, arm set completeness, task family, and profile consistency.
/// Does NOT verify cryptographic signatures (those require the live ledger).
pub fn check_pair_structure(record: &PairRecord) -> Result<(), PairError> {
    if record.schema != SCHEMA {
        return Err(PairError::InvalidSchema(format!(
            "unexpected schema: {}",
            record.schema
        )));
    }
    let task = &record.task;
    if !FAMILIES.contains(&task.family.as_str()) {
        return Err(PairError::InvalidSchema(format!(
            "unknown family: {}",
            task.family
        )));
    }
    let arm_keys: std::collections::HashSet<&str> =
        record.arms.keys().map(String::as_str).collect();
    let expected: std::collections::HashSet<&str> = ARMS.iter().copied().collect();
    if arm_keys != expected {
        return Err(PairError::InvalidSchema(
            "pair must contain exactly direct_executor and p2p_borrow arms".into(),
        ));
    }
    let direct = record
        .arms
        .get("direct_executor")
        .ok_or_else(|| PairError::InvalidSchema("missing direct_executor arm".into()))?;
    let p2p = record
        .arms
        .get("p2p_borrow")
        .ok_or_else(|| PairError::InvalidSchema("missing p2p_borrow arm".into()))?;
    validate_arm_identity(direct, task)?;
    validate_arm_identity(p2p, task)?;
    validate_arm_profile_match(direct, p2p)?;
    Ok(())
}

// ---------------------------------------------------------------------------
// Cohort-level summary helpers
// ---------------------------------------------------------------------------

/// Count valid pairs per family from a slice of verification outcomes.
pub fn family_counts(
    verifications: &[PairVerification],
) -> std::collections::HashMap<String, usize> {
    let mut counts = std::collections::HashMap::new();
    for v in verifications {
        if v.status == "PAIR_VALID_RESOURCE_COMPARISON" {
            if let Some(f) = &v.family {
                *counts.entry(f.clone()).or_insert(0) += 1;
            }
        }
    }
    counts
}

/// Return `true` if all minimum-pair and minimum-per-family thresholds are met.
pub fn cohort_complete(verifications: &[PairVerification]) -> bool {
    let valid: Vec<_> = verifications
        .iter()
        .filter(|v| v.status == "PAIR_VALID_RESOURCE_COMPARISON")
        .collect();
    if valid.len() < MINIMUM_PAIRS {
        return false;
    }
    let counts = family_counts(verifications);
    FAMILIES
        .iter()
        .all(|f| counts.get(*f).copied().unwrap_or(0) >= MINIMUM_PER_FAMILY)
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    fn sample_task(pair_id: &str) -> PairTask {
        PairTask {
            pair_id: pair_id.to_owned(),
            task_id: "task-1".to_owned(),
            task_sha256: "a".repeat(64),
            acceptance_contract_sha256: "b".repeat(64),
            value_rubric_sha256: "c".repeat(64),
            family: "navigation".to_owned(),
            repeat: 0,
            source_asset: None,
        }
    }

    fn sample_arm(arm: &str, pair_id: &str) -> PairArm {
        PairArm {
            arm: arm.to_owned(),
            pair_id: pair_id.to_owned(),
            product_id: "prod-1".to_owned(),
            provider: "claude".to_owned(),
            model: "claude-3".to_owned(),
            client_version: "1.0".to_owned(),
            effort: "medium".to_owned(),
            actual_providers: vec!["claude".to_owned()],
            task_sha256: "a".repeat(64),
            acceptance_contract_sha256: "b".repeat(64),
            native_receipts: vec![],
            acceptance_receipt_path: format!("acceptance/{}-{}.json", pair_id, arm),
            acceptance_receipt_sha256: "d".repeat(64),
            extra: Default::default(),
        }
    }

    #[test]
    fn valid_arm_passes_identity_check() {
        let task = sample_task("pair-1");
        let arm = sample_arm("direct_executor", "pair-1");
        assert!(validate_arm_identity(&arm, &task).is_ok());
    }

    #[test]
    fn arm_pair_id_mismatch_rejected() {
        let task = sample_task("pair-1");
        let arm = sample_arm("direct_executor", "pair-99");
        assert!(validate_arm_identity(&arm, &task).is_err());
    }

    #[test]
    fn profile_mismatch_rejected() {
        let task = sample_task("pair-1");
        let mut direct = sample_arm("direct_executor", "pair-1");
        let mut p2p = sample_arm("p2p_borrow", "pair-1");
        p2p.provider = "codex".to_owned();
        p2p.actual_providers = vec!["codex".to_owned()];
        // Both arms individually pass identity checks but profile match fails.
        assert!(validate_arm_identity(&direct, &task).is_ok());
        assert!(validate_arm_identity(&p2p, &task).is_ok());
        direct.provider = "claude".to_owned();
        assert!(validate_arm_profile_match(&direct, &p2p).is_err());
    }

    #[test]
    fn sha256_hex_known_value() {
        // SHA-256("") == e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
        let digest = sha256_hex(b"");
        assert_eq!(
            digest,
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        );
    }

    #[test]
    fn cohort_complete_requires_minimum_pairs() {
        let v: Vec<PairVerification> = (0..29)
            .map(|i| PairVerification {
                status: "PAIR_VALID_RESOURCE_COMPARISON".to_owned(),
                pair_id: Some(format!("pair-{}", i)),
                reason: None,
                family: Some("navigation".to_owned()),
                provider: Some("claude".to_owned()),
            })
            .collect();
        assert!(!cohort_complete(&v));
    }
}
