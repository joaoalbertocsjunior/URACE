//! `urace-primitives` — §62d/§62e canonical type validators and schema registry.

use regex_lite::Regex;
use std::collections::HashMap;
use std::sync::OnceLock;

#[derive(Debug, thiserror::Error)]
pub enum PrimitivesError {
    #[error("validation failed for {type_name}: {reason}")]
    Invalid { type_name: &'static str, reason: String },
    #[error("unknown primitive type: {0}")]
    UnknownType(String),
}

fn inv(type_name: &'static str, reason: impl Into<String>) -> PrimitivesError {
    PrimitivesError::Invalid { type_name, reason: reason.into() }
}

fn require_field<'a>(
    obj: &'a serde_json::Map<String, serde_json::Value>,
    field: &str,
    type_name: &'static str,
) -> Result<&'a serde_json::Value, PrimitivesError> {
    obj.get(field).ok_or_else(|| inv(type_name, format!("missing required field '{field}'")))
}

fn require_str_field<'a>(
    obj: &'a serde_json::Map<String, serde_json::Value>,
    field: &str,
    type_name: &'static str,
) -> Result<&'a str, PrimitivesError> {
    let v = require_field(obj, field, type_name)?;
    v.as_str().ok_or_else(|| inv(type_name, format!("field '{field}' must be a string")))
}

fn as_obj<'a>(
    value: &'a serde_json::Value,
    type_name: &'static str,
) -> Result<&'a serde_json::Map<String, serde_json::Value>, PrimitivesError> {
    value.as_object().ok_or_else(|| inv(type_name, "must be an object"))
}

// ── §62d Canonical Primitives ─────────────────────────────────────────────────

static IDENTIFIER_RE: OnceLock<Regex> = OnceLock::new();
static HEX64_RE: OnceLock<Regex> = OnceLock::new();

/// §62d: Identifier — `{prefix}-{10-char-lowercase-hex}`
pub fn validate_identifier(value: &str) -> Result<(), PrimitivesError> {
    let re = IDENTIFIER_RE.get_or_init(|| Regex::new(r"^[a-z][a-z0-9]*-[0-9a-f]{10}$").unwrap());
    if !re.is_match(value) {
        return Err(inv("Identifier", format!("'{value}' does not match {{prefix}}-{{10-char-lowercase-hex}}")));
    }
    Ok(())
}

/// §62d: DigestValue — 64-char lowercase hex SHA-256
pub fn validate_digest_value(value: &str) -> Result<(), PrimitivesError> {
    let re = HEX64_RE.get_or_init(|| Regex::new(r"^[0-9a-f]{64}$").unwrap());
    if value.len() != 64 {
        return Err(inv("DigestValue", format!("must be 64 chars, got {}", value.len())));
    }
    if !re.is_match(value) {
        return Err(inv("DigestValue", "must be lowercase hex (0-9a-f)"));
    }
    Ok(())
}

/// §62d: UnitFloat — float in [0.0, 1.0], no NaN/inf
pub fn validate_unit_float(value: f64) -> Result<(), PrimitivesError> {
    if value.is_nan() || value.is_infinite() {
        return Err(inv("UnitFloat", format!("must not be NaN or inf, got {value}")));
    }
    if !(0.0..=1.0).contains(&value) {
        return Err(inv("UnitFloat", format!("must be in [0.0, 1.0], got {value}")));
    }
    Ok(())
}

pub const PRODUCT_SCOPE_VALUES: &[&str] = &["documentation", "runtime", "metrics", "rebootstrap", "*"];

/// §62d: ProductScope
pub fn validate_product_scope(value: &str) -> Result<(), PrimitivesError> {
    if !PRODUCT_SCOPE_VALUES.contains(&value) {
        return Err(inv("ProductScope", format!("'{value}' not valid; expected one of {PRODUCT_SCOPE_VALUES:?}")));
    }
    Ok(())
}

/// §62d: StatusTransition — required: status, at
pub fn validate_status_transition(value: &serde_json::Value) -> Result<(), PrimitivesError> {
    let obj = as_obj(value, "StatusTransition")?;
    for field in ["status", "at"] {
        let v = require_field(obj, field, "StatusTransition")?;
        if !v.is_string() {
            return Err(inv("StatusTransition", format!("'{field}' must be a string")));
        }
    }
    Ok(())
}

/// §62d: MetricEffect — improved/regressed (int >= 0)
pub fn validate_metric_effect(value: &serde_json::Value) -> Result<(), PrimitivesError> {
    let obj = as_obj(value, "MetricEffect")?;
    for field in ["improved", "regressed"] {
        match require_field(obj, field, "MetricEffect")?.as_i64() {
            Some(n) if n >= 0 => {}
            _ => return Err(inv("MetricEffect", format!("'{field}' must be int >= 0"))),
        }
    }
    Ok(())
}

/// §62d: MetricSnapshot — dict[str → number]
pub fn validate_metric_snapshot(value: &serde_json::Value) -> Result<(), PrimitivesError> {
    let obj = as_obj(value, "MetricSnapshot")?;
    for (k, v) in obj {
        if k.is_empty() {
            return Err(inv("MetricSnapshot", "keys must be non-empty strings"));
        }
        if !v.is_number() {
            return Err(inv("MetricSnapshot", format!("value for '{k}' must be numeric")));
        }
    }
    Ok(())
}

/// §62d: ExecutorAttribution — required: executor_id, adapter, capability, attempted_executors, logical_reservation
pub fn validate_executor_attribution(value: &serde_json::Value) -> Result<(), PrimitivesError> {
    let obj = as_obj(value, "ExecutorAttribution")?;
    for field in ["executor_id", "adapter", "capability", "logical_reservation"] {
        if !require_field(obj, field, "ExecutorAttribution")?.is_string() {
            return Err(inv("ExecutorAttribution", format!("'{field}' must be a string")));
        }
    }
    if !require_field(obj, "attempted_executors", "ExecutorAttribution")?.is_array() {
        return Err(inv("ExecutorAttribution", "'attempted_executors' must be a list"));
    }
    Ok(())
}

/// §62d: ValidationCheck — required: check, result, detail
pub fn validate_validation_check(value: &serde_json::Value) -> Result<(), PrimitivesError> {
    let obj = as_obj(value, "ValidationCheck")?;
    for field in ["check", "detail", "result"] {
        if !require_field(obj, field, "ValidationCheck")?.is_string() {
            return Err(inv("ValidationCheck", format!("'{field}' must be a string")));
        }
    }
    Ok(())
}

/// §62d: ValidationResult — required: passed (bool), checks (list)
pub fn validate_validation_result(value: &serde_json::Value) -> Result<(), PrimitivesError> {
    let obj = as_obj(value, "ValidationResult")?;
    if !require_field(obj, "passed", "ValidationResult")?.is_boolean() {
        return Err(inv("ValidationResult", "'passed' must be bool"));
    }
    if !require_field(obj, "checks", "ValidationResult")?.is_array() {
        return Err(inv("ValidationResult", "'checks' must be a list"));
    }
    Ok(())
}

/// §62d: ChangeValidation — required: change_id, validation_result
pub fn validate_change_validation(value: &serde_json::Value) -> Result<(), PrimitivesError> {
    let obj = as_obj(value, "ChangeValidation")?;
    require_str_field(obj, "change_id", "ChangeValidation")?;
    validate_validation_result(require_field(obj, "validation_result", "ChangeValidation")?)
}

/// §62d: ErrorRecord — required: error_type, message
pub fn validate_error_record(value: &serde_json::Value) -> Result<(), PrimitivesError> {
    let obj = as_obj(value, "ErrorRecord")?;
    require_str_field(obj, "error_type", "ErrorRecord")?;
    require_str_field(obj, "message", "ErrorRecord")?;
    Ok(())
}

/// §62d: FailureRecord — required: failure_type, reason
pub fn validate_failure_record(value: &serde_json::Value) -> Result<(), PrimitivesError> {
    let obj = as_obj(value, "FailureRecord")?;
    require_str_field(obj, "failure_type", "FailureRecord")?;
    require_str_field(obj, "reason", "FailureRecord")?;
    Ok(())
}

/// §62d: ExecutionBudget — required: wall_seconds (> 0), token_budget (>= 0)
pub fn validate_execution_budget(value: &serde_json::Value) -> Result<(), PrimitivesError> {
    let obj = as_obj(value, "ExecutionBudget")?;
    match require_field(obj, "wall_seconds", "ExecutionBudget")?.as_f64() {
        Some(v) if v > 0.0 => {}
        _ => return Err(inv("ExecutionBudget", "'wall_seconds' must be > 0")),
    }
    match require_field(obj, "token_budget", "ExecutionBudget")?.as_i64() {
        Some(n) if n >= 0 => {}
        _ => return Err(inv("ExecutionBudget", "'token_budget' must be int >= 0")),
    }
    Ok(())
}

/// §62d: RecoveryManifest — required: recovery_id, steps (list)
pub fn validate_recovery_manifest(value: &serde_json::Value) -> Result<(), PrimitivesError> {
    let obj = as_obj(value, "RecoveryManifest")?;
    require_str_field(obj, "recovery_id", "RecoveryManifest")?;
    if !require_field(obj, "steps", "RecoveryManifest")?.is_array() {
        return Err(inv("RecoveryManifest", "'steps' must be a list"));
    }
    Ok(())
}

/// §62d: UsageRecord — required: tokens_used, cost_ucr (int >= 0)
pub fn validate_usage_record(value: &serde_json::Value) -> Result<(), PrimitivesError> {
    let obj = as_obj(value, "UsageRecord")?;
    for field in ["tokens_used", "cost_ucr"] {
        match require_field(obj, field, "UsageRecord")?.as_i64() {
            Some(n) if n >= 0 => {}
            _ => return Err(inv("UsageRecord", format!("'{field}' must be int >= 0"))),
        }
    }
    Ok(())
}

/// §62d: WakeCondition — required: condition_type (str), threshold (number)
pub fn validate_wake_condition(value: &serde_json::Value) -> Result<(), PrimitivesError> {
    let obj = as_obj(value, "WakeCondition")?;
    require_str_field(obj, "condition_type", "WakeCondition")?;
    if !require_field(obj, "threshold", "WakeCondition")?.is_number() {
        return Err(inv("WakeCondition", "'threshold' must be a number"));
    }
    Ok(())
}

// ── §62e Infrastructure Schemas ───────────────────────────────────────────────

/// §62e: Transaction — required: tx_id, amount (>= 0), from_id, to_id
pub fn validate_transaction(value: &serde_json::Value) -> Result<(), PrimitivesError> {
    let obj = as_obj(value, "Transaction")?;
    for field in ["tx_id", "from_id", "to_id"] {
        require_str_field(obj, field, "Transaction")?;
    }
    match require_field(obj, "amount", "Transaction")?.as_i64() {
        Some(n) if n >= 0 => {}
        _ => return Err(inv("Transaction", "'amount' must be int >= 0")),
    }
    Ok(())
}

/// §62e: OwnershipMarker — required: owner_id, resource_id, acquired_at
pub fn validate_ownership_marker(value: &serde_json::Value) -> Result<(), PrimitivesError> {
    let obj = as_obj(value, "OwnershipMarker")?;
    for field in ["owner_id", "resource_id", "acquired_at"] {
        require_str_field(obj, field, "OwnershipMarker")?;
    }
    Ok(())
}

/// §62e: StaleLockObservation — required: lock_id, holder_id, observed_at
pub fn validate_stale_lock_observation(value: &serde_json::Value) -> Result<(), PrimitivesError> {
    let obj = as_obj(value, "StaleLockObservation")?;
    for field in ["lock_id", "holder_id", "observed_at"] {
        require_str_field(obj, field, "StaleLockObservation")?;
    }
    Ok(())
}

// ── §62d r2: Extended canonical primitives ────────────────────────────────────

/// §62d r2: ReasoningStep — required: step, rationale
pub fn validate_reasoning_step(value: &serde_json::Value) -> Result<(), PrimitivesError> {
    let obj = as_obj(value, "ReasoningStep")?;
    require_str_field(obj, "step", "ReasoningStep")?;
    require_str_field(obj, "rationale", "ReasoningStep")?;
    Ok(())
}

/// §62d r2: OutcomeFeedback — required: outcome (str), score_delta (number)
pub fn validate_outcome_feedback(value: &serde_json::Value) -> Result<(), PrimitivesError> {
    let obj = as_obj(value, "OutcomeFeedback")?;
    require_str_field(obj, "outcome", "OutcomeFeedback")?;
    if !require_field(obj, "score_delta", "OutcomeFeedback")?.is_number() {
        return Err(inv("OutcomeFeedback", "'score_delta' must be a number"));
    }
    Ok(())
}

/// §62d r2: AlternativeConsidered — required: description, reason_rejected
pub fn validate_alternative_considered(value: &serde_json::Value) -> Result<(), PrimitivesError> {
    let obj = as_obj(value, "AlternativeConsidered")?;
    require_str_field(obj, "description", "AlternativeConsidered")?;
    require_str_field(obj, "reason_rejected", "AlternativeConsidered")?;
    Ok(())
}

/// §62d r2: DecisionRecord — required: decision_id, rationale, outcome
pub fn validate_decision_record(value: &serde_json::Value) -> Result<(), PrimitivesError> {
    let obj = as_obj(value, "DecisionRecord")?;
    for field in ["decision_id", "rationale", "outcome"] {
        require_str_field(obj, field, "DecisionRecord")?;
    }
    Ok(())
}

/// §62d r2: RetentionPolicy — required: policy_id, max_age_days (int > 0)
pub fn validate_retention_policy(value: &serde_json::Value) -> Result<(), PrimitivesError> {
    let obj = as_obj(value, "RetentionPolicy")?;
    require_str_field(obj, "policy_id", "RetentionPolicy")?;
    match require_field(obj, "max_age_days", "RetentionPolicy")?.as_i64() {
        Some(n) if n > 0 => {}
        _ => return Err(inv("RetentionPolicy", "'max_age_days' must be int > 0")),
    }
    Ok(())
}

/// §62d r2: CompactionSummary — required: original_count, compacted_count (int >= 0)
pub fn validate_compaction_summary(value: &serde_json::Value) -> Result<(), PrimitivesError> {
    let obj = as_obj(value, "CompactionSummary")?;
    for field in ["original_count", "compacted_count"] {
        match require_field(obj, field, "CompactionSummary")?.as_i64() {
            Some(n) if n >= 0 => {}
            _ => return Err(inv("CompactionSummary", format!("'{field}' must be int >= 0"))),
        }
    }
    Ok(())
}

/// §62d r2: CompactionEvent — required: event_id, at, kind
pub fn validate_compaction_event(value: &serde_json::Value) -> Result<(), PrimitivesError> {
    let obj = as_obj(value, "CompactionEvent")?;
    for field in ["event_id", "at", "kind"] {
        require_str_field(obj, field, "CompactionEvent")?;
    }
    Ok(())
}

/// §62d r2: CompactionManifest — required: manifest_id, events (list)
pub fn validate_compaction_manifest(value: &serde_json::Value) -> Result<(), PrimitivesError> {
    let obj = as_obj(value, "CompactionManifest")?;
    require_str_field(obj, "manifest_id", "CompactionManifest")?;
    if !require_field(obj, "events", "CompactionManifest")?.is_array() {
        return Err(inv("CompactionManifest", "'events' must be a list"));
    }
    Ok(())
}

/// §62d r2: CompactionIndex — required: index_id, entries (list)
pub fn validate_compaction_index(value: &serde_json::Value) -> Result<(), PrimitivesError> {
    let obj = as_obj(value, "CompactionIndex")?;
    require_str_field(obj, "index_id", "CompactionIndex")?;
    if !require_field(obj, "entries", "CompactionIndex")?.is_array() {
        return Err(inv("CompactionIndex", "'entries' must be a list"));
    }
    Ok(())
}

/// §62d r2: ArchiveAmendment — required: amendment_id, target_id, reason
pub fn validate_archive_amendment(value: &serde_json::Value) -> Result<(), PrimitivesError> {
    let obj = as_obj(value, "ArchiveAmendment")?;
    for field in ["amendment_id", "target_id", "reason"] {
        require_str_field(obj, field, "ArchiveAmendment")?;
    }
    Ok(())
}

/// §62d r2: SourceBindingSupersession — required: superseded_id, superseding_id
pub fn validate_source_binding_supersession(value: &serde_json::Value) -> Result<(), PrimitivesError> {
    let obj = as_obj(value, "SourceBindingSupersession")?;
    require_str_field(obj, "superseded_id", "SourceBindingSupersession")?;
    require_str_field(obj, "superseding_id", "SourceBindingSupersession")?;
    Ok(())
}

/// §62d r2: SourceBindingRecord — required: binding_id, source_id, adapter
pub fn validate_source_binding_record(value: &serde_json::Value) -> Result<(), PrimitivesError> {
    let obj = as_obj(value, "SourceBindingRecord")?;
    for field in ["binding_id", "source_id", "adapter"] {
        require_str_field(obj, field, "SourceBindingRecord")?;
    }
    Ok(())
}

/// §62d r2: TechniqueApplicationRecord — required: technique_id, applied_at
pub fn validate_technique_application_record(value: &serde_json::Value) -> Result<(), PrimitivesError> {
    let obj = as_obj(value, "TechniqueApplicationRecord")?;
    require_str_field(obj, "technique_id", "TechniqueApplicationRecord")?;
    require_str_field(obj, "applied_at", "TechniqueApplicationRecord")?;
    Ok(())
}

/// §62d r2: CognitiveResumeContext — required: session_id, resumed_at
pub fn validate_cognitive_resume_context(value: &serde_json::Value) -> Result<(), PrimitivesError> {
    let obj = as_obj(value, "CognitiveResumeContext")?;
    require_str_field(obj, "session_id", "CognitiveResumeContext")?;
    require_str_field(obj, "resumed_at", "CognitiveResumeContext")?;
    Ok(())
}

// ── §62i Architectural Meta-Patterns (r14) ────────────────────────────────────

/// §62i r14: BridgeRecord — required: bridge_id, source_id, target_id
pub fn validate_bridge_record(value: &serde_json::Value) -> Result<(), PrimitivesError> {
    let obj = as_obj(value, "BridgeRecord")?;
    for field in ["bridge_id", "source_id", "target_id"] {
        require_str_field(obj, field, "BridgeRecord")?;
    }
    Ok(())
}

/// §62i r14: OrchestratorRecord — required: orchestrator_id, task_ids (list)
pub fn validate_orchestrator_record(value: &serde_json::Value) -> Result<(), PrimitivesError> {
    let obj = as_obj(value, "OrchestratorRecord")?;
    require_str_field(obj, "orchestrator_id", "OrchestratorRecord")?;
    if !require_field(obj, "task_ids", "OrchestratorRecord")?.is_array() {
        return Err(inv("OrchestratorRecord", "'task_ids' must be a list"));
    }
    Ok(())
}

/// §62i r14: ScheduledTask — required: task_id, schedule, action
pub fn validate_scheduled_task(value: &serde_json::Value) -> Result<(), PrimitivesError> {
    let obj = as_obj(value, "ScheduledTask")?;
    for field in ["task_id", "schedule", "action"] {
        require_str_field(obj, field, "ScheduledTask")?;
    }
    Ok(())
}

/// §62i r14: CustomizationRecord — required: customization_id, target, value
pub fn validate_customization_record(value: &serde_json::Value) -> Result<(), PrimitivesError> {
    let obj = as_obj(value, "CustomizationRecord")?;
    require_str_field(obj, "customization_id", "CustomizationRecord")?;
    require_str_field(obj, "target", "CustomizationRecord")?;
    require_field(obj, "value", "CustomizationRecord")?;
    Ok(())
}

/// §62i r14: LexicalFormula — required: formula_id, expression
pub fn validate_lexical_formula(value: &serde_json::Value) -> Result<(), PrimitivesError> {
    let obj = as_obj(value, "LexicalFormula")?;
    require_str_field(obj, "formula_id", "LexicalFormula")?;
    require_str_field(obj, "expression", "LexicalFormula")?;
    Ok(())
}

/// §62i r14: ClassificationResult — required: classifier_id, label, confidence (number)
pub fn validate_classification_result(value: &serde_json::Value) -> Result<(), PrimitivesError> {
    let obj = as_obj(value, "ClassificationResult")?;
    require_str_field(obj, "classifier_id", "ClassificationResult")?;
    require_str_field(obj, "label", "ClassificationResult")?;
    if !require_field(obj, "confidence", "ClassificationResult")?.is_number() {
        return Err(inv("ClassificationResult", "'confidence' must be a number"));
    }
    Ok(())
}

/// §62i r14: ClassificationBatch — required: batch_id, results (list)
pub fn validate_classification_batch(value: &serde_json::Value) -> Result<(), PrimitivesError> {
    let obj = as_obj(value, "ClassificationBatch")?;
    require_str_field(obj, "batch_id", "ClassificationBatch")?;
    if !require_field(obj, "results", "ClassificationBatch")?.is_array() {
        return Err(inv("ClassificationBatch", "'results' must be a list"));
    }
    Ok(())
}

/// §62i r14: PatternAdoptionRecord — required: pattern_id, adopted_at
pub fn validate_pattern_adoption_record(value: &serde_json::Value) -> Result<(), PrimitivesError> {
    let obj = as_obj(value, "PatternAdoptionRecord")?;
    require_str_field(obj, "pattern_id", "PatternAdoptionRecord")?;
    require_str_field(obj, "adopted_at", "PatternAdoptionRecord")?;
    Ok(())
}

/// §62i r14: PatternExclusionRecord — required: pattern_id, reason, excluded_at
pub fn validate_pattern_exclusion_record(value: &serde_json::Value) -> Result<(), PrimitivesError> {
    let obj = as_obj(value, "PatternExclusionRecord")?;
    for field in ["pattern_id", "reason", "excluded_at"] {
        require_str_field(obj, field, "PatternExclusionRecord")?;
    }
    Ok(())
}

/// §62i r14: DerivedSystemManifest — required: manifest_id, patterns (list), generated_at
pub fn validate_derived_system_manifest(value: &serde_json::Value) -> Result<(), PrimitivesError> {
    let obj = as_obj(value, "DerivedSystemManifest")?;
    require_str_field(obj, "manifest_id", "DerivedSystemManifest")?;
    require_str_field(obj, "generated_at", "DerivedSystemManifest")?;
    if !require_field(obj, "patterns", "DerivedSystemManifest")?.is_array() {
        return Err(inv("DerivedSystemManifest", "'patterns' must be a list"));
    }
    Ok(())
}

// ── §62b r31: Quality/Resilience schemas ──────────────────────────────────────

/// §62b r31: QualityDelta — required: metric (str), before, after (numbers)
pub fn validate_quality_delta(value: &serde_json::Value) -> Result<(), PrimitivesError> {
    let obj = as_obj(value, "QualityDelta")?;
    require_str_field(obj, "metric", "QualityDelta")?;
    for field in ["before", "after"] {
        if !require_field(obj, field, "QualityDelta")?.is_number() {
            return Err(inv("QualityDelta", format!("'{field}' must be a number")));
        }
    }
    Ok(())
}

/// §62b r31: ReingestionRecord — required: source_id, reason
pub fn validate_reingestion_record(value: &serde_json::Value) -> Result<(), PrimitivesError> {
    let obj = as_obj(value, "ReingestionRecord")?;
    require_str_field(obj, "source_id", "ReingestionRecord")?;
    require_str_field(obj, "reason", "ReingestionRecord")?;
    Ok(())
}

/// §62b r31: OperationDependency — required: op_id, depends_on (list)
pub fn validate_operation_dependency(value: &serde_json::Value) -> Result<(), PrimitivesError> {
    let obj = as_obj(value, "OperationDependency")?;
    require_str_field(obj, "op_id", "OperationDependency")?;
    if !require_field(obj, "depends_on", "OperationDependency")?.is_array() {
        return Err(inv("OperationDependency", "'depends_on' must be a list"));
    }
    Ok(())
}

/// §62b r31: QualityStateEntry — required: state_id, metric, at (str), value (number)
pub fn validate_quality_state_entry(value: &serde_json::Value) -> Result<(), PrimitivesError> {
    let obj = as_obj(value, "QualityStateEntry")?;
    for field in ["state_id", "metric", "at"] {
        require_str_field(obj, field, "QualityStateEntry")?;
    }
    if !require_field(obj, "value", "QualityStateEntry")?.is_number() {
        return Err(inv("QualityStateEntry", "'value' must be a number"));
    }
    Ok(())
}

// ── §62i AP4 ProducerConsumerContract (r33) ───────────────────────────────────

/// §62i r33: ProducerConsumerContract — required: contract_id, producer_id, consumer_id, interface
pub fn validate_producer_consumer_contract(value: &serde_json::Value) -> Result<(), PrimitivesError> {
    let obj = as_obj(value, "ProducerConsumerContract")?;
    for field in ["contract_id", "producer_id", "consumer_id", "interface"] {
        require_str_field(obj, field, "ProducerConsumerContract")?;
    }
    Ok(())
}

// ── §62l GoverningRecord / RevalidationScope (r39) ───────────────────────────

pub const GOVERNING_RECORD_REQUIRED: &[&str] = &["id", "authority_basis", "scope", "established_at"];

/// Verify a citizen declares all GoverningRecord canonical fields (§62l).
pub fn check_governing_record_fields(
    value: &serde_json::Value,
    citizen_name: &str,
) -> Result<(), PrimitivesError> {
    let obj = as_obj(value, "GoverningRecord")?;
    for &field in GOVERNING_RECORD_REQUIRED {
        require_field(obj, field, "GoverningRecord").map_err(|_| PrimitivesError::Invalid {
            type_name: "GoverningRecord",
            reason: format!("{citizen_name} missing GoverningRecord field '{field}'"),
        })?;
    }
    for field in ["authority_basis", "scope"] {
        let s = require_str_field(obj, field, "GoverningRecord")?;
        if s.trim().is_empty() {
            return Err(inv("GoverningRecord", format!("{citizen_name}.{field} must be non-empty")));
        }
    }
    Ok(())
}

pub const REVALIDATION_SCOPES: &[&str] = &["DECISION_ONLY", "DEPENDENT_PLANS", "FULL_LIFECYCLE"];

/// Validate a RevalidationScope value (§62l).
pub fn validate_revalidation_scope(value: &str) -> Result<(), PrimitivesError> {
    if !REVALIDATION_SCOPES.contains(&value) {
        return Err(inv("RevalidationScope", format!("must be one of {REVALIDATION_SCOPES:?}, got '{value}'")));
    }
    Ok(())
}

static REVALIDATION_SCOPE_MAP: OnceLock<HashMap<&'static str, &'static str>> = OnceLock::new();

fn revalidation_scope_map() -> &'static HashMap<&'static str, &'static str> {
    REVALIDATION_SCOPE_MAP.get_or_init(|| {
        [
            ("evidence-retracted", "DECISION_ONLY"),
            ("evidence-revised", "DECISION_ONLY"),
            ("authority-suspended", "DEPENDENT_PLANS"),
            ("authority-revoked", "DEPENDENT_PLANS"),
            ("intent-versioned", "FULL_LIFECYCLE"),
            ("intent-replaced", "FULL_LIFECYCLE"),
            ("hard-constraint-added", "DEPENDENT_PLANS"),
            ("policy-status-changed", "DEPENDENT_PLANS"),
            ("multiple-premise-changes", "FULL_LIFECYCLE"),
            ("executor-identity-broken", "DECISION_ONLY"),
        ]
        .into_iter()
        .collect()
    })
}

/// Return minimum RevalidationScope for a premise change class (§62l r39).
pub fn determine_revalidation_scope(change_class: &str) -> &'static str {
    revalidation_scope_map().get(change_class).copied().unwrap_or("FULL_LIFECYCLE")
}

const NON_AUTHORITY_SOURCES: &[&str] = &[
    "evidence", "priority", "capability", "market_signal",
    "trigger", "schedule", "executor_recommendation", "product_value",
    "user_absence", "market_success",
];

/// Return true if action_source is a valid Authority origin (§62l r39).
pub fn check_authority_closure(action_source: &str) -> bool {
    !NON_AUTHORITY_SOURCES.contains(&action_source)
}

// ── Integrity Gap Catalog ─────────────────────────────────────────────────────

#[derive(Debug, Clone)]
pub struct GapEntry {
    pub severity: &'static str,
    pub description: &'static str,
}

static INTEGRITY_GAP_CATALOG: OnceLock<HashMap<&'static str, GapEntry>> = OnceLock::new();

pub fn integrity_gap_catalog() -> &'static HashMap<&'static str, GapEntry> {
    INTEGRITY_GAP_CATALOG.get_or_init(|| {
        [
            ("missing-authority-gate", "CRITICAL", "Qualifying action taken without authority confirmation"),
            ("append-only-violation", "CRITICAL", "Ledger row mutated or deleted after write"),
            ("silent-exception", "HIGH", "Swallowed error in financial/signing path"),
            ("hardcoded-secret", "CRITICAL", "Hardcoded key, token, or credential in source"),
            ("state-file-committed", "HIGH", "Runtime state file committed to version control"),
            ("undocumented-feature", "MEDIUM", "Feature documented without matching implementation"),
            ("mint-without-score-delta", "CRITICAL", "Mint triggered without score_delta > 0"),
            ("unit-constant-changed", "CRITICAL", "UNIT constant value modified"),
            ("exit-code-changed", "CRITICAL", "EXIT_REVALIDATE or EXIT_ONE_RETRY constant modified"),
            ("non-atomic-write", "HIGH", "Journal write not using atomic append helpers"),
            ("credential-leak", "CRITICAL", "Private key material in trace/error/return value"),
            ("sandbox-bypass", "HIGH", "Executor code path bypasses SandboxBackend"),
            ("env-credential-leak", "HIGH", "Parent environment inherited in executor subprocess"),
            ("peer-admission-bypass", "HIGH", "Peer added to routing table without AdmissionGate check"),
            ("quorum-below-supermajority", "HIGH", "Quorum threshold below strict 2/3 supermajority"),
            ("bearer-token-missing", "HIGH", "/api/* handler missing BearerToken extractor"),
        ]
        .into_iter()
        .map(|(k, s, d)| (k, GapEntry { severity: s, description: d }))
        .collect()
    })
}

/// Return true if kind is registered in INTEGRITY_GAP_CATALOG.
pub fn is_known_gap_kind(kind: &str) -> bool {
    integrity_gap_catalog().contains_key(kind)
}

/// Return canonical severity for a known gap kind, or None if unknown.
pub fn gap_severity(kind: &str) -> Option<&'static str> {
    integrity_gap_catalog().get(kind).map(|e| e.severity)
}

// ── Dispatch ──────────────────────────────────────────────────────────────────

/// Validate `value` against the named primitive type.
pub fn validate(type_name: &str, value: &serde_json::Value) -> Result<(), PrimitivesError> {
    match type_name {
        "Identifier" => validate_identifier(value.as_str().unwrap_or("")),
        "DigestValue" => validate_digest_value(value.as_str().unwrap_or("")),
        "UnitFloat" => validate_unit_float(value.as_f64().unwrap_or(f64::NAN)),
        "ProductScope" => validate_product_scope(value.as_str().unwrap_or("")),
        "StatusTransition" => validate_status_transition(value),
        "MetricEffect" => validate_metric_effect(value),
        "MetricSnapshot" => validate_metric_snapshot(value),
        "ExecutorAttribution" => validate_executor_attribution(value),
        "ValidationCheck" => validate_validation_check(value),
        "ValidationResult" => validate_validation_result(value),
        "ChangeValidation" => validate_change_validation(value),
        "ErrorRecord" => validate_error_record(value),
        "FailureRecord" => validate_failure_record(value),
        "ExecutionBudget" => validate_execution_budget(value),
        "RecoveryManifest" => validate_recovery_manifest(value),
        "UsageRecord" => validate_usage_record(value),
        "WakeCondition" => validate_wake_condition(value),
        "Transaction" => validate_transaction(value),
        "OwnershipMarker" => validate_ownership_marker(value),
        "StaleLockObservation" => validate_stale_lock_observation(value),
        "ReasoningStep" => validate_reasoning_step(value),
        "OutcomeFeedback" => validate_outcome_feedback(value),
        "AlternativeConsidered" => validate_alternative_considered(value),
        "DecisionRecord" => validate_decision_record(value),
        "RetentionPolicy" => validate_retention_policy(value),
        "CompactionSummary" => validate_compaction_summary(value),
        "CompactionEvent" => validate_compaction_event(value),
        "CompactionManifest" => validate_compaction_manifest(value),
        "CompactionIndex" => validate_compaction_index(value),
        "ArchiveAmendment" => validate_archive_amendment(value),
        "SourceBindingSupersession" => validate_source_binding_supersession(value),
        "SourceBindingRecord" => validate_source_binding_record(value),
        "TechniqueApplicationRecord" => validate_technique_application_record(value),
        "CognitiveResumeContext" => validate_cognitive_resume_context(value),
        "BridgeRecord" => validate_bridge_record(value),
        "OrchestratorRecord" => validate_orchestrator_record(value),
        "ScheduledTask" => validate_scheduled_task(value),
        "CustomizationRecord" => validate_customization_record(value),
        "LexicalFormula" => validate_lexical_formula(value),
        "ClassificationResult" => validate_classification_result(value),
        "ClassificationBatch" => validate_classification_batch(value),
        "PatternAdoptionRecord" => validate_pattern_adoption_record(value),
        "PatternExclusionRecord" => validate_pattern_exclusion_record(value),
        "DerivedSystemManifest" => validate_derived_system_manifest(value),
        "QualityDelta" => validate_quality_delta(value),
        "ReingestionRecord" => validate_reingestion_record(value),
        "OperationDependency" => validate_operation_dependency(value),
        "QualityStateEntry" => validate_quality_state_entry(value),
        "ProducerConsumerContract" => validate_producer_consumer_contract(value),
        other => Err(PrimitivesError::UnknownType(other.to_string())),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn identifier_valid_and_invalid() {
        assert!(validate_identifier("goal-deadbeef01").is_ok());
        assert!(validate_identifier("src-0123456789").is_ok());
        assert!(validate_identifier("no-hex").is_err());
        assert!(validate_identifier("Goal-deadbeef01").is_err());
    }

    #[test]
    fn digest_value_valid_and_invalid() {
        assert!(validate_digest_value(&"a".repeat(64)).is_ok());
        assert!(validate_digest_value("short").is_err());
        assert!(validate_digest_value(&"G".repeat(64)).is_err());
    }

    #[test]
    fn unit_float_bounds() {
        assert!(validate_unit_float(0.0).is_ok());
        assert!(validate_unit_float(1.0).is_ok());
        assert!(validate_unit_float(1.1).is_err());
        assert!(validate_unit_float(f64::NAN).is_err());
    }

    #[test]
    fn dispatch_unknown_type() {
        assert!(matches!(validate("NoSuchType", &json!({})), Err(PrimitivesError::UnknownType(_))));
    }

    #[test]
    fn dispatch_status_transition() {
        let v = json!({"status": "active", "at": "2024-01-01T00:00:00Z"});
        assert!(validate("StatusTransition", &v).is_ok());
        assert!(validate("StatusTransition", &json!({"status": "active"})).is_err());
    }

    #[test]
    fn gap_catalog() {
        assert!(is_known_gap_kind("missing-authority-gate"));
        assert_eq!(gap_severity("mint-without-score-delta"), Some("CRITICAL"));
        assert!(!is_known_gap_kind("made-up-kind"));
        assert_eq!(gap_severity("made-up-kind"), None);
    }

    #[test]
    fn revalidation_scope() {
        assert_eq!(determine_revalidation_scope("evidence-retracted"), "DECISION_ONLY");
        assert_eq!(determine_revalidation_scope("unknown-class"), "FULL_LIFECYCLE");
        assert!(validate_revalidation_scope("DECISION_ONLY").is_ok());
        assert!(validate_revalidation_scope("INVALID").is_err());
    }

    #[test]
    fn authority_closure() {
        assert!(!check_authority_closure("evidence"));
        assert!(check_authority_closure("user_decision"));
    }
}
