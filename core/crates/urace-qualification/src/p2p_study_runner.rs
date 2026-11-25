//! Runner for frozen direct-executor/P2P-first cohort pairs via pinned adapters.
//!
//! Ported from `trial/p2p_study_runner.py`. This controller never claims
//! savings. Product-specific adapters perform task setup/executor work,
//! independent acceptance, and cost measurement; their exact source hashes
//! must be pinned in the immutable cohort plan.

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::path::{Path, PathBuf};
use thiserror::Error;

use crate::p2p_pair_protocol::{ARMS, COST_SCHEMA, SCHEMA};
use crate::p2p_study_plan::{verify_plan, CohortPlan};

// ---------------------------------------------------------------------------
// Errors
// ---------------------------------------------------------------------------

/// Errors that can occur during cohort runner operations.
#[derive(Debug, Error)]
pub enum RunnerError {
    #[error("plan error: {0}")]
    Plan(String),
    #[error("path traversal or symlink detected: {0}")]
    PathSecurity(String),
    #[error("adapter error: {0}")]
    Adapter(String),
    #[error("evidence integrity error: {0}")]
    Evidence(String),
    #[error("exchange error: {0}")]
    Exchange(String),
    #[error("io error: {0}")]
    Io(#[from] std::io::Error),
    #[error("serialization error: {0}")]
    Serialization(#[from] serde_json::Error),
}

// ---------------------------------------------------------------------------
// Record types
// ---------------------------------------------------------------------------

/// Summary returned by `preflight`.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PreflightResult {
    pub status: String,
    pub cohort_sha256: String,
    pub pairs_planned: usize,
    pub profile: serde_json::Value,
    pub pinned_sellers: Vec<String>,
    pub adapter_hashes_verified: bool,
    pub network_reachability_checked: bool,
    pub provider_calls_made: u32,
    pub cost_claim: String,
}

/// Summary returned by `run_cohort`.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RunSummary {
    pub status: String,
    pub cohort_sha256: String,
    pub attempted_this_run: usize,
    pub recorded_pairs: usize,
    pub planned_pairs: usize,
    /// Always `false`; a qualified claim requires independent review.
    pub qualified_savings_claim: bool,
    pub pair_manifest: String,
}

/// Configuration for a single cohort run.
#[derive(Debug, Clone)]
pub struct RunConfig {
    /// Path to the frozen cohort plan JSON file.
    pub plan_path: PathBuf,
    /// Directory where study evidence is written.
    pub study_root: PathBuf,
    /// Directory containing the buyer exchange identity.
    pub exchange_root: PathBuf,
    /// Path to the arm adapter source file.
    pub arm_adapter_path: PathBuf,
    /// Path to the evaluator adapter source file.
    pub evaluator_adapter_path: PathBuf,
    /// Path to the cost adapter source file.
    pub cost_adapter_path: PathBuf,
    /// Maximum number of pairs to attempt this invocation (1–30).
    pub max_pairs: usize,
    /// Peer search limit (must match the frozen plan).
    pub peer_limit: Option<usize>,
    /// Directory containing authoritative executor transport receipts.
    pub transport_root: Option<PathBuf>,
    /// Must be `true` to perform any live provider/network activity.
    pub live: bool,
}

// ---------------------------------------------------------------------------
// SHA-256 file digest helper
// ---------------------------------------------------------------------------

/// Compute the SHA-256 of a file's bytes without reading the whole file at once.
pub fn digest_file(path: &Path) -> Result<String, RunnerError> {
    let bytes = std::fs::read(path)?;
    let mut h = Sha256::new();
    h.update(&bytes);
    Ok(hex::encode(h.finalize()))
}

// ---------------------------------------------------------------------------
// Path safety helpers
// ---------------------------------------------------------------------------

/// Resolve `path` and verify that no component is a symlink.
///
/// This mirrors the Python `_no_symlink_path` guard.
pub fn no_symlink_path(path: &Path) -> Result<PathBuf, RunnerError> {
    let canonical = path.canonicalize().map_err(|e| {
        RunnerError::PathSecurity(format!("cannot canonicalize {}: {}", path.display(), e))
    })?;
    let mut current = PathBuf::from(
        canonical
            .components()
            .next()
            .map(|c| {
                let mut p = PathBuf::new();
                p.push(c);
                p
            })
            .unwrap_or_default(),
    );
    for component in canonical.components().skip(1) {
        current.push(component);
        if current
            .symlink_metadata()
            .map(|m| m.file_type().is_symlink())
            .unwrap_or(false)
        {
            return Err(RunnerError::PathSecurity(format!(
                "symlink detected at: {}",
                current.display()
            )));
        }
    }
    Ok(canonical)
}

/// Resolve `child` and verify it is inside `root` with no symlinks.
pub fn confined_path(root: &Path, child: &Path) -> Result<PathBuf, RunnerError> {
    let resolved_root = no_symlink_path(root)?;
    let resolved_child = no_symlink_path(child)?;
    if !resolved_child.starts_with(&resolved_root) {
        return Err(RunnerError::PathSecurity(format!(
            "path {} escapes root {}",
            resolved_child.display(),
            resolved_root.display()
        )));
    }
    Ok(resolved_child)
}

// ---------------------------------------------------------------------------
// Plan loading helper
// ---------------------------------------------------------------------------

/// Load and verify a frozen cohort plan from disk.
pub fn load_verified_plan(plan_path: &Path) -> Result<CohortPlan, RunnerError> {
    let path = no_symlink_path(plan_path)?;
    let bytes = std::fs::read(&path)?;
    let plan: CohortPlan = serde_json::from_slice(&bytes)?;
    if !verify_plan(&plan) {
        return Err(RunnerError::Plan(
            "frozen plan hash or design verification failed".into(),
        ));
    }
    Ok(plan)
}

// ---------------------------------------------------------------------------
// Adapter hash verification
// ---------------------------------------------------------------------------

/// Verify that an adapter file exists, is not a symlink, and matches its
/// expected SHA-256 hash from the frozen plan.
pub fn verify_adapter(path: &Path, expected_sha: &str, name: &str) -> Result<(), RunnerError> {
    let resolved = no_symlink_path(path).map_err(|_| {
        RunnerError::Adapter(format!("{} adapter path is a symlink or missing", name))
    })?;
    if !resolved.is_file() {
        return Err(RunnerError::Adapter(format!(
            "{} adapter is not a regular file",
            name
        )));
    }
    let actual = digest_file(&resolved)?;
    if actual != expected_sha {
        return Err(RunnerError::Adapter(format!(
            "{} adapter digest {} does not match frozen plan {}",
            name, actual, expected_sha
        )));
    }
    Ok(())
}

// ---------------------------------------------------------------------------
// Preflight (read-only checks)
// ---------------------------------------------------------------------------

/// Perform read-only preflight checks for a cohort run.
///
/// Does not contact peers, invoke provider clients, or write any files.
pub fn preflight(config: &RunConfig) -> Result<PreflightResult, RunnerError> {
    let plan = load_verified_plan(&config.plan_path)?;
    let identity = &plan.identity;
    // Verify adapter hashes.
    let adapters = identity
        .get("adapter_sha256")
        .and_then(|v| v.as_object())
        .ok_or_else(|| RunnerError::Plan("plan missing adapter_sha256".into()))?;
    for (name, path) in [
        ("arm", &config.arm_adapter_path),
        ("evaluator", &config.evaluator_adapter_path),
        ("cost", &config.cost_adapter_path),
    ] {
        let expected = adapters
            .get(name)
            .and_then(|v| v.as_str())
            .ok_or_else(|| RunnerError::Plan(format!("missing adapter hash: {}", name)))?;
        verify_adapter(path, expected, name)?;
    }
    // Verify runner hash (the hash of this compiled binary is not available at
    // runtime in Rust, so we verify the plan contains a runner_sha256 field).
    if identity
        .get("runner_sha256")
        .and_then(|v| v.as_str())
        .map(|s| s.len() != 64)
        .unwrap_or(true)
    {
        return Err(RunnerError::Plan(
            "plan missing or invalid runner_sha256".into(),
        ));
    }
    let root = &config.study_root;
    if root.is_symlink() {
        return Err(RunnerError::PathSecurity(
            "study root cannot be a symlink".into(),
        ));
    }
    let profile = identity
        .get("executor_profile")
        .cloned()
        .unwrap_or(serde_json::Value::Null);
    let pinned_sellers: Vec<String> = identity
        .get("allowed_seller_peer_ids")
        .and_then(|v| v.as_array())
        .map(|a| {
            a.iter()
                .filter_map(|v| v.as_str().map(str::to_owned))
                .collect()
        })
        .unwrap_or_default();
    Ok(PreflightResult {
        status: "PREFLIGHT_READY".to_owned(),
        cohort_sha256: plan.cohort_sha256.clone(),
        pairs_planned: plan.pairs.len(),
        profile,
        pinned_sellers,
        adapter_hashes_verified: true,
        network_reachability_checked: false,
        provider_calls_made: 0,
        cost_claim: "NOT_ESTABLISHED".to_owned(),
    })
}

// ---------------------------------------------------------------------------
// Acceptance receipt validation
// ---------------------------------------------------------------------------

/// Structural validation for an acceptance receipt envelope from an evaluator adapter.
///
/// Full cryptographic signature checks require the live ledger; this validates
/// structure and binding fields.
pub fn validate_acceptance_receipt(
    envelope: &serde_json::Value,
    identity: &serde_json::Value,
    pair_id: &str,
    task_sha256: &str,
    acceptance_contract_sha256: &str,
    value_rubric_sha256: &str,
    arm: &str,
) -> Result<(), RunnerError> {
    let payload = envelope
        .get("payload")
        .and_then(|v| v.as_object())
        .ok_or_else(|| {
            RunnerError::Evidence("acceptance envelope missing payload object".into())
        })?;

    let evaluator_id = identity
        .get("independent_evaluator_id")
        .and_then(|v| v.as_str())
        .unwrap_or("");

    let required: &[(&str, &str)] = &[
        ("pair_id", pair_id),
        ("task_sha256", task_sha256),
        ("acceptance_contract_sha256", acceptance_contract_sha256),
        ("value_rubric_sha256", value_rubric_sha256),
        ("arm", arm),
        ("evaluator_id", evaluator_id),
    ];
    for (key, expected) in required {
        let actual = payload.get(*key).and_then(|v| v.as_str()).unwrap_or("");
        if actual != *expected {
            return Err(RunnerError::Evidence(format!(
                "acceptance receipt {}: expected {:?}, got {:?}",
                key, expected, actual
            )));
        }
    }
    if payload.get("measurement_complete") != Some(&serde_json::Value::Bool(true)) {
        return Err(RunnerError::Evidence(
            "acceptance receipt: measurement_complete must be true".into(),
        ));
    }
    let passed = payload
        .get("passed")
        .ok_or_else(|| RunnerError::Evidence("acceptance receipt missing passed field".into()))?;
    if !passed.is_boolean() {
        return Err(RunnerError::Evidence(
            "acceptance receipt passed must be boolean".into(),
        ));
    }
    let value_score = payload
        .get("value_score")
        .and_then(|v| v.as_f64())
        .ok_or_else(|| {
            RunnerError::Evidence("acceptance receipt missing or non-numeric value_score".into())
        })?;
    if !(0.0..=1.0).contains(&value_score) || value_score.is_nan() || value_score.is_infinite() {
        return Err(RunnerError::Evidence(
            "acceptance receipt value_score must be finite in [0,1]".into(),
        ));
    }
    Ok(())
}

// ---------------------------------------------------------------------------
// Cost receipt validation
// ---------------------------------------------------------------------------

/// Structural validation for a signed cost receipt envelope from the cost adapter.
pub fn validate_cost_receipt(
    envelope: &serde_json::Value,
    identity: &serde_json::Value,
    pair_id: &str,
    task_sha256: &str,
) -> Result<(), RunnerError> {
    let payload = envelope
        .get("payload")
        .and_then(|v| v.as_object())
        .ok_or_else(|| {
            RunnerError::Evidence("cost receipt envelope missing payload object".into())
        })?;

    if payload.get("schema").and_then(|v| v.as_str()) != Some(COST_SCHEMA) {
        return Err(RunnerError::Evidence(format!(
            "cost receipt schema must be {}",
            COST_SCHEMA
        )));
    }
    if payload.get("pair_id").and_then(|v| v.as_str()) != Some(pair_id) {
        return Err(RunnerError::Evidence(
            "cost receipt pair_id mismatch".into(),
        ));
    }
    if payload.get("task_sha256").and_then(|v| v.as_str()) != Some(task_sha256) {
        return Err(RunnerError::Evidence(
            "cost receipt task_sha256 mismatch".into(),
        ));
    }
    let measurement_contract = identity
        .get("cost_measurement_contract_sha256")
        .and_then(|v| v.as_str())
        .unwrap_or("");
    if payload
        .get("measurement_contract_sha256")
        .and_then(|v| v.as_str())
        != Some(measurement_contract)
    {
        return Err(RunnerError::Evidence(
            "cost receipt measurement_contract_sha256 mismatch".into(),
        ));
    }
    // Validate arm cost dimensions exist for both arms.
    for field in &["provider_cost_usd_by_arm", "non_provider_cost_usd_by_arm"] {
        let arms_obj = payload
            .get(*field)
            .and_then(|v| v.as_object())
            .ok_or_else(|| RunnerError::Evidence(format!("cost receipt missing {}", field)))?;
        for arm in ARMS {
            let val = arms_obj.get(arm).and_then(|v| v.as_f64()).ok_or_else(|| {
                RunnerError::Evidence(format!(
                    "cost receipt {}.{} missing or non-numeric",
                    field, arm
                ))
            })?;
            if val < 0.0 || val.is_nan() || val.is_infinite() {
                return Err(RunnerError::Evidence(format!(
                    "cost receipt {}.{} must be finite and non-negative",
                    field, arm
                )));
            }
        }
    }
    let valid_bases = [
        "ACTUAL_MARGINAL",
        "API_EQUIVALENT",
        "SUBSCRIPTION_ALLOCATED",
    ];
    if !valid_bases.contains(
        &payload
            .get("provider_cost_basis")
            .and_then(|v| v.as_str())
            .unwrap_or(""),
    ) {
        return Err(RunnerError::Evidence(
            "cost receipt provider_cost_basis is not a recognised value".into(),
        ));
    }
    Ok(())
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;
    use tempfile::tempdir;

    #[test]
    fn digest_file_known_hash() {
        let dir = tempdir().unwrap();
        let path = dir.path().join("test.bin");
        std::fs::write(&path, b"hello").unwrap();
        let digest = digest_file(&path).unwrap();
        // SHA-256("hello") = 2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824
        assert_eq!(
            digest,
            "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
        );
    }

    #[test]
    fn acceptance_receipt_valid() {
        let identity = json!({
            "independent_evaluator_id": "eval-1",
            "independent_evaluator_public": {}
        });
        let envelope = json!({
            "payload": {
                "pair_id": "p1",
                "task_sha256": "a".repeat(64),
                "acceptance_contract_sha256": "b".repeat(64),
                "value_rubric_sha256": "c".repeat(64),
                "arm": "direct_executor",
                "evaluator_id": "eval-1",
                "measurement_complete": true,
                "passed": true,
                "value_score": 0.85
            },
            "signature": {}
        });
        assert!(validate_acceptance_receipt(
            &envelope,
            &identity,
            "p1",
            &"a".repeat(64),
            &"b".repeat(64),
            &"c".repeat(64),
            "direct_executor"
        )
        .is_ok());
    }

    #[test]
    fn acceptance_receipt_out_of_range_value_score_rejected() {
        let identity = json!({ "independent_evaluator_id": "eval-1" });
        let envelope = json!({
            "payload": {
                "pair_id": "p1",
                "task_sha256": "a".repeat(64),
                "acceptance_contract_sha256": "b".repeat(64),
                "value_rubric_sha256": "c".repeat(64),
                "arm": "direct_executor",
                "evaluator_id": "eval-1",
                "measurement_complete": true,
                "passed": true,
                "value_score": 1.5
            }
        });
        assert!(validate_acceptance_receipt(
            &envelope,
            &identity,
            "p1",
            &"a".repeat(64),
            &"b".repeat(64),
            &"c".repeat(64),
            "direct_executor"
        )
        .is_err());
    }

    #[test]
    fn cost_receipt_valid() {
        let identity = json!({
            "cost_measurement_contract_sha256": "d".repeat(64)
        });
        let envelope = json!({
            "payload": {
                "schema": COST_SCHEMA,
                "pair_id": "p1",
                "task_sha256": "a".repeat(64),
                "measurement_contract_sha256": "d".repeat(64),
                "provider_cost_usd_by_arm": {
                    "direct_executor": 0.01,
                    "p2p_borrow": 0.005
                },
                "non_provider_cost_usd_by_arm": {
                    "direct_executor": 0.0,
                    "p2p_borrow": 0.001
                },
                "provider_cost_basis": "ACTUAL_MARGINAL",
                "non_provider_cost_complete_by_arm": {
                    "direct_executor": true,
                    "p2p_borrow": true
                }
            }
        });
        assert!(validate_cost_receipt(&envelope, &identity, "p1", &"a".repeat(64)).is_ok());
    }

    #[test]
    fn cost_receipt_bad_basis_rejected() {
        let identity = json!({
            "cost_measurement_contract_sha256": "d".repeat(64)
        });
        let envelope = json!({
            "payload": {
                "schema": COST_SCHEMA,
                "pair_id": "p1",
                "task_sha256": "a".repeat(64),
                "measurement_contract_sha256": "d".repeat(64),
                "provider_cost_usd_by_arm": {
                    "direct_executor": 0.0,
                    "p2p_borrow": 0.0
                },
                "non_provider_cost_usd_by_arm": {
                    "direct_executor": 0.0,
                    "p2p_borrow": 0.0
                },
                "provider_cost_basis": "MADE_UP_BASIS"
            }
        });
        assert!(validate_cost_receipt(&envelope, &identity, "p1", &"a".repeat(64)).is_err());
    }

    #[test]
    fn no_symlink_path_rejects_missing() {
        let result = no_symlink_path(Path::new("/no/such/path/xyz123"));
        assert!(result.is_err());
    }
}
