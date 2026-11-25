//! Cognitive Resume Context (CRC) — session continuity, state snapshots, executor handoff.
//!
//! §62z: any authority decision derived from a CRC MUST route through `authority::resolve`;
//! the CRC itself carries no authority — it only describes state at a cycle boundary.
//! A stale CRC (digest mismatch) must be regenerated before Executor initialization.

use serde::{Deserialize, Serialize};
use serde_json::Value;
use sha2::{Digest, Sha256};
use thiserror::Error;

// ── Errors ────────────────────────────────────────────────────────────────────

/// Errors produced by cognitive-resume operations.
#[derive(Debug, Error)]
pub enum CognitiveResumeError {
    #[error("CRC {id} is stale — regenerate before Executor initialization")]
    Stale { id: String },

    #[error("serialization error: {0}")]
    Serialization(#[from] serde_json::Error),

    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),
}

// ── Phase ─────────────────────────────────────────────────────────────────────

/// Lifecycle phase inferred from state's `lifecycle_state` field.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum CyclePhase {
    Executing,
    Validating,
    Assessing,
    Planning,
    Dormant,
}

impl CyclePhase {
    fn from_lifecycle_state(s: &str) -> Self {
        match s.to_ascii_uppercase().as_str() {
            "ACTIVE" | "BLOCKED" | "REPAIRING" => Self::Executing,
            "ACCEPTED" | "VALIDATING" | "RECONCILING" => Self::Validating,
            "PLANNING" => Self::Planning,
            "DORMANT"
            | "PAUSED"
            | "WAITING_FOR_CAPACITY"
            | "WAITING_FOR_AUTHORITATIVE_DECISION"
            | "WAITING_FOR_CONDITION"
            | "WAITING_FOR_SCHEDULE" => Self::Dormant,
            _ => Self::Assessing,
        }
    }
}

// ── CRC record ────────────────────────────────────────────────────────────────

/// A CognitiveResumeContext snapshot generated at every cycle boundary.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CognitiveResumeContext {
    pub id: String,
    pub generated_at: String,
    pub cycle_phase: CyclePhase,
    pub state_digest: String,
    #[serde(default)]
    pub pending_validations: Vec<String>,
    #[serde(default)]
    pub blocking_gaps: Vec<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub active_objective_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub active_operation_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub pending_transaction: Option<String>,
}

/// Structured context injected into an Executor on initialization.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecutorContext {
    pub cognitive_resume_context: CognitiveResumeContext,
    pub state_digest: String,
    pub cycle_phase: CyclePhase,
    pub blocking_gaps: Vec<String>,
    pub pending_validations: Vec<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub active_objective_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub active_operation_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub pending_transaction: Option<String>,
}

/// An integrity gap record signalling that a CRC is stale.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IntegrityGap {
    pub id: String,
    pub kind: String,
    pub at: String,
    pub description: String,
    pub severity: String,
    pub source: String,
    pub active: bool,
    pub resolved_at: Option<String>,
    pub evidence_id: Option<String>,
}

// ── Helpers ───────────────────────────────────────────────────────────────────

fn now_iso() -> String {
    // RFC 3339 / ISO-8601 UTC timestamp
    let secs = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs();
    // Format as naive ISO-8601 (no external time dep — workspace uses `time` but
    // it is not in urace-authority's deps; a simple numeric representation suffices
    // for digest correctness).
    format!("1970-01-01T00:00:{:02}Z", secs % 60) // placeholder structure
        .replace(
            "1970-01-01T00:00:",
            &format!(
                "{}-{:02}-{:02}T{:02}:{:02}:",
                1970 + secs / 31_557_600,
                1 + (secs % 31_557_600) / 2_629_800,
                1 + (secs % 2_629_800) / 86_400,
                (secs % 86_400) / 3_600,
                (secs % 3_600) / 60,
            ),
        )
}

fn random_hex5() -> String {
    // Use sha2 of a system-time nonce as a cheap random source (no rand dep in this crate).
    let nonce = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default()
        .subsec_nanos();
    let hash = Sha256::digest(nonce.to_le_bytes());
    hex::encode(&hash[..5])
}

fn make_id(prefix: &str) -> String {
    format!("{}-{}", prefix, random_hex5())
}

/// SHA-256 of the canonical JSON serialization of `state`.
pub fn state_digest(state: &Value) -> String {
    let canonical = serde_json::to_string(state).unwrap_or_default();
    let hash = Sha256::digest(canonical.as_bytes());
    hex::encode(hash)
}

// ── Core API ──────────────────────────────────────────────────────────────────

/// Generate a fresh CRC from `state`; call at every cycle boundary.
pub fn generate(state: &Value) -> CognitiveResumeContext {
    let lifecycle_state = state
        .get("lifecycle_state")
        .and_then(Value::as_str)
        .unwrap_or("");
    let phase = CyclePhase::from_lifecycle_state(lifecycle_state);

    let active_objective_id = state
        .get("objectives")
        .and_then(Value::as_array)
        .and_then(|objs| {
            objs.iter().find(|o| {
                matches!(
                    o.get("status").and_then(Value::as_str),
                    Some("ACTIVE") | Some("IN_PROGRESS") | Some("PLANNING")
                )
            })
        })
        .and_then(|o| o.get("id"))
        .and_then(Value::as_str)
        .map(str::to_owned);

    let active_operation_id = state
        .get("operations")
        .and_then(Value::as_array)
        .and_then(|ops| {
            ops.iter().find(|o| {
                matches!(
                    o.get("status").and_then(Value::as_str),
                    Some("ACTIVE") | Some("IN_PROGRESS") | Some("EXECUTING") | Some("VALIDATING")
                )
            })
        })
        .and_then(|o| o.get("id"))
        .and_then(Value::as_str)
        .map(str::to_owned);

    let pending_transaction = state
        .get("transactions")
        .and_then(Value::as_array)
        .and_then(|txs| {
            txs.iter().find(|t| {
                matches!(
                    t.get("phase").and_then(Value::as_str),
                    Some("PREPARED") | Some("APPLYING") | Some("APPLIED")
                )
            })
        })
        .and_then(|t| t.get("id"))
        .and_then(Value::as_str)
        .map(str::to_owned);

    let pending_validations: Vec<String> = state
        .get("pending_validation")
        .and_then(Value::as_array)
        .map(|pvs| {
            pvs.iter()
                .filter(|pv| {
                    pv.get("status").and_then(Value::as_str) == Some("PENDING_CAPABILITY")
                        && pv.get("operation_id").and_then(Value::as_str).is_some()
                })
                .filter_map(|pv| {
                    pv.get("operation_id")
                        .and_then(Value::as_str)
                        .map(str::to_owned)
                })
                .collect()
        })
        .unwrap_or_default();

    let blocking_gaps: Vec<String> = state
        .get("integrity_gaps")
        .and_then(Value::as_array)
        .map(|gaps| {
            gaps.iter()
                .filter(|g| {
                    g.get("severity").and_then(Value::as_str) == Some("BLOCKING")
                        && g.get("active").and_then(Value::as_bool) == Some(true)
                        && g.get("id").and_then(Value::as_str).is_some()
                })
                .filter_map(|g| g.get("id").and_then(Value::as_str).map(str::to_owned))
                .collect()
        })
        .unwrap_or_default();

    let digest = state_digest(state);

    CognitiveResumeContext {
        id: make_id("crc"),
        generated_at: now_iso(),
        cycle_phase: phase,
        state_digest: digest,
        pending_validations,
        blocking_gaps,
        active_objective_id,
        active_operation_id,
        pending_transaction,
    }
}

/// Return `true` if `crc` no longer matches the current `state`.
pub fn is_stale(crc: &CognitiveResumeContext, state: &Value) -> bool {
    crc.state_digest != state_digest(state)
}

/// Build an IntegrityGap record describing a stale CRC.
pub fn staleness_gap(crc: &CognitiveResumeContext) -> IntegrityGap {
    IntegrityGap {
        id: make_id("gap"),
        kind: "cognitive-resume-stale".into(),
        at: now_iso(),
        description: format!(
            "CognitiveResumeContext {} state_digest does not match current state; \
             regeneration required before Executor initialization",
            crc.id
        ),
        severity: "WARNING".into(),
        source: "cognitive_resume".into(),
        active: true,
        resolved_at: None,
        evidence_id: None,
    }
}

/// Build the ExecutorContext injected on Executor initialization.
///
/// Returns `Err(CognitiveResumeError::Stale)` if the CRC is stale.
pub fn build_executor_context(
    crc: &CognitiveResumeContext,
    state: &Value,
) -> Result<ExecutorContext, CognitiveResumeError> {
    if is_stale(crc, state) {
        return Err(CognitiveResumeError::Stale { id: crc.id.clone() });
    }
    Ok(ExecutorContext {
        state_digest: crc.state_digest.clone(),
        cycle_phase: crc.cycle_phase.clone(),
        blocking_gaps: crc.blocking_gaps.clone(),
        pending_validations: crc.pending_validations.clone(),
        active_objective_id: crc.active_objective_id.clone(),
        active_operation_id: crc.active_operation_id.clone(),
        pending_transaction: crc.pending_transaction.clone(),
        cognitive_resume_context: crc.clone(),
    })
}

/// Load a CRC from disk, or generate and save a fresh one if absent or stale.
pub fn load_or_generate(
    state_path: &std::path::Path,
    state: &Value,
) -> Result<CognitiveResumeContext, CognitiveResumeError> {
    let path = state_path.join("cognitive-resume-context.json");
    if path.exists() {
        let raw = std::fs::read_to_string(&path)?;
        let existing: CognitiveResumeContext = serde_json::from_str(&raw)?;
        if !is_stale(&existing, state) {
            return Ok(existing);
        }
    }
    let fresh = generate(state);
    let tmp = path.with_extension("tmp");
    std::fs::write(&tmp, serde_json::to_string_pretty(&fresh)?)?;
    std::fs::rename(&tmp, &path)?;
    Ok(fresh)
}

// ── Tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn sample_state() -> Value {
        json!({
            "lifecycle_state": "ACTIVE",
            "objectives": [{"id": "obj-1", "status": "ACTIVE"}],
            "operations": [{"id": "op-1", "status": "EXECUTING"}],
            "transactions": [],
            "pending_validation": [],
            "integrity_gaps": []
        })
    }

    #[test]
    fn generate_produces_valid_crc() {
        let state = sample_state();
        let crc = generate(&state);
        assert_eq!(crc.cycle_phase, CyclePhase::Executing);
        assert_eq!(crc.active_objective_id.as_deref(), Some("obj-1"));
        assert_eq!(crc.active_operation_id.as_deref(), Some("op-1"));
        assert!(!crc.state_digest.is_empty());
    }

    #[test]
    fn fresh_crc_is_not_stale() {
        let state = sample_state();
        let crc = generate(&state);
        assert!(!is_stale(&crc, &state));
    }

    #[test]
    fn mutated_state_makes_crc_stale() {
        let state = sample_state();
        let crc = generate(&state);
        let mut mutated = state.clone();
        mutated["lifecycle_state"] = json!("DORMANT");
        assert!(is_stale(&crc, &mutated));
    }

    #[test]
    fn build_executor_context_rejects_stale_crc() {
        let state = sample_state();
        let crc = generate(&state);
        let mut other = state.clone();
        other["lifecycle_state"] = json!("PAUSED");
        let result = build_executor_context(&crc, &other);
        assert!(matches!(result, Err(CognitiveResumeError::Stale { .. })));
    }

    #[test]
    fn staleness_gap_has_warning_severity() {
        let state = sample_state();
        let crc = generate(&state);
        let gap = staleness_gap(&crc);
        assert_eq!(gap.severity, "WARNING");
        assert_eq!(gap.kind, "cognitive-resume-stale");
        assert!(gap.active);
    }
}
