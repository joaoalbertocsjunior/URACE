"""Canonical primitive validators — §62d and §62e of URACE.md.

Pure validation functions — no side effects. Each validator:
  - Accepts the value to validate
  - Returns None on success
  - Raises ValueError with a descriptive message on failure

Use the dispatch function ``validate(type_name, value)`` when the type is
determined at runtime.
"""
from __future__ import annotations

import math
import re
from typing import Any


# ── §62d Canonical Primitives ────────────────────────────────────────────────

def validate_identifier(value: str) -> None:
    """§62d: Identifier — ``{prefix}-{10-char-lowercase-hex}``."""
    if not isinstance(value, str):
        raise ValueError(f"Identifier must be str, got {type(value).__name__}")
    if not re.fullmatch(r'[a-z][a-z0-9]*-[0-9a-f]{10}', value):
        raise ValueError(
            f"Identifier '{value}' does not match {{prefix}}-{{10-char-lowercase-hex}} format"
        )


def validate_digest_value(value: str) -> None:
    """§62d: DigestValue — 64-char lowercase hex SHA-256."""
    if not isinstance(value, str):
        raise ValueError(f"DigestValue must be str, got {type(value).__name__}")
    if len(value) != 64:
        raise ValueError(
            f"DigestValue must be 64 chars, got {len(value)}"
        )
    if value != value.lower() or not re.fullmatch(r'[0-9a-f]{64}', value):
        raise ValueError("DigestValue must be lowercase hex (0-9a-f)")


def validate_unit_float(value: float) -> None:
    """§62d: UnitFloat — float in [0.0, 1.0], no NaN/inf."""
    if not isinstance(value, (int, float)):
        raise ValueError(f"UnitFloat must be numeric, got {type(value).__name__}")
    if math.isnan(value) or math.isinf(value):
        raise ValueError(f"UnitFloat must not be NaN or inf, got {value}")
    if not (0.0 <= float(value) <= 1.0):
        raise ValueError(f"UnitFloat must be in [0.0, 1.0], got {value}")


_PRODUCT_SCOPE_VALUES = frozenset({"documentation", "runtime", "metrics", "rebootstrap", "*"})

def validate_product_scope(value: str) -> None:
    """§62d: ProductScope — one of documentation | runtime | metrics | rebootstrap | *."""
    if not isinstance(value, str):
        raise ValueError(f"ProductScope must be str, got {type(value).__name__}")
    if value not in _PRODUCT_SCOPE_VALUES:
        raise ValueError(
            f"ProductScope '{value}' is not valid; expected one of {sorted(_PRODUCT_SCOPE_VALUES)}"
        )


def validate_status_transition(value: dict) -> None:
    """§62d: StatusTransition — required: status (str), at (str); optional: reason, source."""
    if not isinstance(value, dict):
        raise ValueError(f"StatusTransition must be dict, got {type(value).__name__}")
    for field in ("status", "at"):
        if field not in value:
            raise ValueError(f"StatusTransition missing required field '{field}'")
        if not isinstance(value[field], str):
            raise ValueError(f"StatusTransition.{field} must be str, got {type(value[field]).__name__}")


def validate_metric_effect(value: dict, *, total_metrics: int | None = None) -> None:
    """§62d: MetricEffect — improved (int ≥ 0), regressed (int ≥ 0); sum ≤ total_metrics if given."""
    if not isinstance(value, dict):
        raise ValueError(f"MetricEffect must be dict, got {type(value).__name__}")
    for field in ("improved", "regressed"):
        if field not in value:
            raise ValueError(f"MetricEffect missing required field '{field}'")
        if not isinstance(value[field], int) or value[field] < 0:
            raise ValueError(f"MetricEffect.{field} must be int ≥ 0, got {value[field]!r}")
    if total_metrics is not None:
        total = value["improved"] + value["regressed"]
        if total > total_metrics:
            raise ValueError(
                f"MetricEffect sum ({total}) exceeds total_metrics ({total_metrics})"
            )


def validate_metric_snapshot(value: dict) -> None:
    """§62d: MetricSnapshot — dict[str → float]; all keys non-empty strings."""
    if not isinstance(value, dict):
        raise ValueError(f"MetricSnapshot must be dict, got {type(value).__name__}")
    for k, v in value.items():
        if not isinstance(k, str) or not k:
            raise ValueError(f"MetricSnapshot key must be a non-empty string, got {k!r}")
        if not isinstance(v, (int, float)):
            raise ValueError(f"MetricSnapshot value for '{k}' must be numeric, got {type(v).__name__}")


def validate_executor_attribution(value: dict) -> None:
    """§62d: ExecutorAttribution — required: executor_id, adapter, capability,
    attempted_executors (list), logical_reservation."""
    if not isinstance(value, dict):
        raise ValueError(f"ExecutorAttribution must be dict, got {type(value).__name__}")
    required_str = ("executor_id", "adapter", "capability", "logical_reservation")
    for field in required_str:
        if field not in value:
            raise ValueError(f"ExecutorAttribution missing required field '{field}'")
        if not isinstance(value[field], str):
            raise ValueError(
                f"ExecutorAttribution.{field} must be str, got {type(value[field]).__name__}"
            )
    if "attempted_executors" not in value:
        raise ValueError("ExecutorAttribution missing required field 'attempted_executors'")
    if not isinstance(value["attempted_executors"], list):
        raise ValueError(
            f"ExecutorAttribution.attempted_executors must be list, "
            f"got {type(value['attempted_executors']).__name__}"
        )


def validate_validation_check(value: dict) -> None:
    """§62d: ValidationCheck — required: check (str), result (PASS|FAIL), detail (str)."""
    if not isinstance(value, dict):
        raise ValueError(f"ValidationCheck must be dict, got {type(value).__name__}")
    for field in ("check", "detail"):
        if field not in value:
            raise ValueError(f"ValidationCheck missing required field '{field}'")
        if not isinstance(value[field], str):
            raise ValueError(
                f"ValidationCheck.{field} must be str, got {type(value[field]).__name__}"
            )
    if "result" not in value:
        raise ValueError("ValidationCheck missing required field 'result'")
    if value["result"] not in ("PASS", "FAIL"):
        raise ValueError(
            f"ValidationCheck.result must be PASS or FAIL, got {value['result']!r}"
        )


def validate_validation_result(value: dict) -> None:
    """§62d: ValidationResult — required: verdict, checks, fails, basis, validated_at."""
    if not isinstance(value, dict):
        raise ValueError(f"ValidationResult must be dict, got {type(value).__name__}")
    if "verdict" not in value:
        raise ValueError("ValidationResult missing required field 'verdict'")
    if value["verdict"] not in ("VALIDATED", "REJECTED", "PENDING_CAPABILITY"):
        raise ValueError(
            f"ValidationResult.verdict must be VALIDATED, REJECTED, or PENDING_CAPABILITY, "
            f"got {value['verdict']!r}"
        )
    for field in ("basis", "validated_at"):
        if field not in value:
            raise ValueError(f"ValidationResult missing required field '{field}'")
        if not isinstance(value[field], str):
            raise ValueError(
                f"ValidationResult.{field} must be str, got {type(value[field]).__name__}"
            )
    for list_field in ("checks", "fails"):
        if list_field not in value:
            raise ValueError(f"ValidationResult missing required field '{list_field}'")
        if not isinstance(value[list_field], list):
            raise ValueError(
                f"ValidationResult.{list_field} must be list, "
                f"got {type(value[list_field]).__name__}"
            )


def validate_change_validation(value: dict) -> None:
    """§62d: ChangeValidation — required: verdict (ACCEPTED|REJECTED|ROLLED_BACK), checks (list)."""
    if not isinstance(value, dict):
        raise ValueError(f"ChangeValidation must be dict, got {type(value).__name__}")
    if "verdict" not in value:
        raise ValueError("ChangeValidation missing required field 'verdict'")
    if value["verdict"] not in ("ACCEPTED", "REJECTED", "ROLLED_BACK"):
        raise ValueError(
            f"ChangeValidation.verdict must be ACCEPTED, REJECTED, or ROLLED_BACK, "
            f"got {value['verdict']!r}"
        )
    if "checks" not in value:
        raise ValueError("ChangeValidation missing required field 'checks'")
    if not isinstance(value["checks"], list):
        raise ValueError(
            f"ChangeValidation.checks must be list, got {type(value['checks']).__name__}"
        )


def validate_error_record(value: dict) -> None:
    """§62d: ErrorRecord — required: source, error, kind (all str); optional: at."""
    if not isinstance(value, dict):
        raise ValueError(f"ErrorRecord must be dict, got {type(value).__name__}")
    for field in ("source", "error", "kind"):
        if field not in value:
            raise ValueError(f"ErrorRecord missing required field '{field}'")
        if not isinstance(value[field], str):
            raise ValueError(
                f"ErrorRecord.{field} must be str, got {type(value[field]).__name__}"
            )
    if "at" in value and not isinstance(value["at"], str):
        raise ValueError(f"ErrorRecord.at must be str if present, got {type(value['at']).__name__}")


def validate_failure_record(value: dict) -> None:
    """§62d: FailureRecord — required: at, last_at, stage, error (str), count (int ≥ 1)."""
    if not isinstance(value, dict):
        raise ValueError(f"FailureRecord must be dict, got {type(value).__name__}")
    for field in ("at", "last_at", "stage", "error"):
        if field not in value:
            raise ValueError(f"FailureRecord missing required field '{field}'")
        if not isinstance(value[field], str):
            raise ValueError(
                f"FailureRecord.{field} must be str, got {type(value[field]).__name__}"
            )
    if "count" not in value:
        raise ValueError("FailureRecord missing required field 'count'")
    if not isinstance(value["count"], int) or value["count"] < 1:
        raise ValueError(f"FailureRecord.count must be int ≥ 1, got {value['count']!r}")
    if "failure_type" in value:
        valid_types = {"transient", "semantic", "structural"}
        if value["failure_type"] not in valid_types:
            raise ValueError(
                f"FailureRecord.failure_type must be one of {sorted(valid_types)}, "
                f"got {value['failure_type']!r}"
            )


def validate_execution_budget(value: dict) -> None:
    """§62b r23: ExecutionBudget — goal-level resource envelope."""
    if not isinstance(value, dict):
        raise ValueError(f"ExecutionBudget must be dict, got {type(value).__name__}")
    for field in ("max_iterations", "max_executor_calls", "iterations_used", "executor_calls_used"):
        if field not in value:
            raise ValueError(f"ExecutionBudget missing required field '{field}'")
        if not isinstance(value[field], int) or value[field] < 0:
            raise ValueError(f"ExecutionBudget.{field} must be int ≥ 0, got {value[field]!r}")
    if value["max_iterations"] < 1:
        raise ValueError(f"ExecutionBudget.max_iterations must be ≥ 1, got {value['max_iterations']!r}")
    if value["max_executor_calls"] < 1:
        raise ValueError(f"ExecutionBudget.max_executor_calls must be ≥ 1, got {value['max_executor_calls']!r}")


def validate_recovery_manifest(value: dict) -> None:
    """§62b r23: RecoveryManifest — re-ingestible re-entry artifact."""
    if not isinstance(value, dict):
        raise ValueError(f"RecoveryManifest must be dict, got {type(value).__name__}")
    for field in ("manifest_id", "emitted_at", "emission_cause", "last_safe_state",
                  "goal_delta", "execution_mode"):
        if field not in value:
            raise ValueError(f"RecoveryManifest missing required field '{field}'")
        if not isinstance(value[field], str):
            raise ValueError(f"RecoveryManifest.{field} must be str, got {type(value[field]).__name__}")
    valid_causes = {"repair-exhausted", "budget-exhausted"}
    if value["emission_cause"] not in valid_causes:
        raise ValueError(f"RecoveryManifest.emission_cause must be one of {sorted(valid_causes)}")
    valid_modes = {"auto", "supervised"}
    if value["execution_mode"] not in valid_modes:
        raise ValueError(f"RecoveryManifest.execution_mode must be one of {sorted(valid_modes)}")
    for field in ("last_safe_commit", "failure_summary", "progress_at_emit"):
        if field not in value:
            raise ValueError(f"RecoveryManifest missing required field '{field}'")
    if not isinstance(value["failure_summary"], list):
        raise ValueError("RecoveryManifest.failure_summary must be list")
    pat = value["progress_at_emit"]
    if pat is not None:
        if not isinstance(pat, (int, float)):
            raise ValueError("RecoveryManifest.progress_at_emit must be float [0,1] or null")
        if not (0.0 <= pat <= 1.0):
            raise ValueError(f"RecoveryManifest.progress_at_emit must be in [0.0, 1.0], got {pat!r}")
    if "recommended_tier" in value and value["recommended_tier"] is not None:
        if value["recommended_tier"] not in {"T1", "T2", "T3"}:
            raise ValueError("RecoveryManifest.recommended_tier must be T1, T2, T3, or null")


def validate_usage_record(value: dict) -> None:
    """§62d: UsageRecord — required: source (str), observed_at (str);
    optional int fields must be ≥ 0 if present."""
    if not isinstance(value, dict):
        raise ValueError(f"UsageRecord must be dict, got {type(value).__name__}")
    for field in ("source", "observed_at"):
        if field not in value:
            raise ValueError(f"UsageRecord missing required field '{field}'")
        if not isinstance(value[field], str):
            raise ValueError(
                f"UsageRecord.{field} must be str, got {type(value[field]).__name__}"
            )
    _OPTIONAL_INT_FIELDS = ("calls", "tokens", "cost_units", "improved", "regressed")
    for field in _OPTIONAL_INT_FIELDS:
        if field in value:
            if not isinstance(value[field], int) or value[field] < 0:
                raise ValueError(
                    f"UsageRecord.{field} must be int ≥ 0 if present, got {value[field]!r}"
                )


def validate_wake_condition(value: dict) -> None:
    """§62d: WakeCondition — required: scheduled_at (str)."""
    if not isinstance(value, dict):
        raise ValueError(f"WakeCondition must be dict, got {type(value).__name__}")
    if "scheduled_at" not in value:
        raise ValueError("WakeCondition missing required field 'scheduled_at'")
    if not isinstance(value["scheduled_at"], str):
        raise ValueError(
            f"WakeCondition.scheduled_at must be str, "
            f"got {type(value['scheduled_at']).__name__}"
        )


# ── §62e Infrastructure Schemas ──────────────────────────────────────────────

_TRANSACTION_PHASES = frozenset({"PREPARED", "APPLYING", "APPLIED", "VALIDATED"})

def validate_transaction(value: dict) -> None:
    """§62e: Transaction — id (Identifier), operation (str), created_at (str),
    phase (PREPARED|APPLYING|APPLIED|VALIDATED), before (dict), after (dict), applied (list)."""
    if not isinstance(value, dict):
        raise ValueError(f"Transaction must be dict, got {type(value).__name__}")
    # id must be a valid Identifier
    if "id" not in value:
        raise ValueError("Transaction missing required field 'id'")
    validate_identifier(value["id"])
    for field in ("operation", "created_at"):
        if field not in value:
            raise ValueError(f"Transaction missing required field '{field}'")
        if not isinstance(value[field], str):
            raise ValueError(
                f"Transaction.{field} must be str, got {type(value[field]).__name__}"
            )
    if "phase" not in value:
        raise ValueError("Transaction missing required field 'phase'")
    if value["phase"] not in _TRANSACTION_PHASES:
        raise ValueError(
            f"Transaction.phase must be one of {sorted(_TRANSACTION_PHASES)}, "
            f"got {value['phase']!r}"
        )
    for dict_field in ("before", "after"):
        if dict_field not in value:
            raise ValueError(f"Transaction missing required field '{dict_field}'")
        if not isinstance(value[dict_field], dict):
            raise ValueError(
                f"Transaction.{dict_field} must be dict, "
                f"got {type(value[dict_field]).__name__}"
            )
    if "applied" not in value:
        raise ValueError("Transaction missing required field 'applied'")
    if not isinstance(value["applied"], list):
        raise ValueError(
            f"Transaction.applied must be list, got {type(value['applied']).__name__}"
        )


def validate_ownership_marker(value: dict) -> None:
    """§62e: OwnershipMarker — pid (int), started_at (str)."""
    if not isinstance(value, dict):
        raise ValueError(f"OwnershipMarker must be dict, got {type(value).__name__}")
    if "pid" not in value:
        raise ValueError("OwnershipMarker missing required field 'pid'")
    if not isinstance(value["pid"], int):
        raise ValueError(f"OwnershipMarker.pid must be int, got {type(value['pid']).__name__}")
    if "started_at" not in value:
        raise ValueError("OwnershipMarker missing required field 'started_at'")
    if not isinstance(value["started_at"], str):
        raise ValueError(
            f"OwnershipMarker.started_at must be str, "
            f"got {type(value['started_at']).__name__}"
        )


def validate_stale_lock_observation(value: dict) -> None:
    """§62e: StaleLockObservation — at (str), stale_pid (int), lock (str),
    disposition (str, always 'removed')."""
    if not isinstance(value, dict):
        raise ValueError(f"StaleLockObservation must be dict, got {type(value).__name__}")
    for str_field in ("at", "lock", "disposition"):
        if str_field not in value:
            raise ValueError(f"StaleLockObservation missing required field '{str_field}'")
        if not isinstance(value[str_field], str):
            raise ValueError(
                f"StaleLockObservation.{str_field} must be str, "
                f"got {type(value[str_field]).__name__}"
            )
    if "stale_pid" not in value:
        raise ValueError("StaleLockObservation missing required field 'stale_pid'")
    if not isinstance(value["stale_pid"], int):
        raise ValueError(
            f"StaleLockObservation.stale_pid must be int, "
            f"got {type(value['stale_pid']).__name__}"
        )
    if value["disposition"] != "removed":
        raise ValueError(
            f"StaleLockObservation.disposition must be 'removed', "
            f"got {value['disposition']!r}"
        )


# ── §62d New canonical primitives (r2) ───────────────────────────────────────

_REASONING_STEP_KINDS = frozenset({
    "OBSERVATION", "INFERENCE", "CONSTRAINT_CHECK",
    "AUTHORITY_CHECK", "ALTERNATIVE_EVALUATION", "SYNTHESIS",
})
_REASONING_STEP_OUTCOMES = frozenset({"PASS", "FAIL", "INCONCLUSIVE"})


def validate_reasoning_step(value: dict) -> None:
    """§62d r3: ReasoningStep — ordered structured step in a reasoning trail."""
    if not isinstance(value, dict):
        raise ValueError(f"ReasoningStep must be dict, got {type(value).__name__}")
    for req in ("step_index", "kind", "description", "outcome"):
        if req not in value:
            raise ValueError(f"ReasoningStep missing required field '{req}'")
    if not isinstance(value["step_index"], int) or value["step_index"] < 0:
        raise ValueError("ReasoningStep.step_index must be int ≥ 0")
    if value["kind"] not in _REASONING_STEP_KINDS:
        raise ValueError(
            f"ReasoningStep.kind must be one of {sorted(_REASONING_STEP_KINDS)}, "
            f"got {value['kind']!r}"
        )
    if not isinstance(value["description"], str) or not value["description"].strip():
        raise ValueError("ReasoningStep.description must be a non-empty str")
    if value["outcome"] not in _REASONING_STEP_OUTCOMES:
        raise ValueError(
            f"ReasoningStep.outcome must be one of {sorted(_REASONING_STEP_OUTCOMES)}, "
            f"got {value['outcome']!r}"
        )
    if "evidence_ref" in value and value["evidence_ref"] is not None:
        if not isinstance(value["evidence_ref"], str):
            raise ValueError("ReasoningStep.evidence_ref must be str or null")


_AMENDMENT_KINDS = frozenset({"PROVENANCE_REVISED", "SUPERSEDED", "CUSTOM"})


def validate_outcome_feedback(value: dict) -> None:
    """§62d r3: OutcomeFeedback — post-decision outcome observation record."""
    if not isinstance(value, dict):
        raise ValueError(f"OutcomeFeedback must be dict, got {type(value).__name__}")
    for req in ("observed_at", "materialized", "triggers_revision"):
        if req not in value:
            raise ValueError(f"OutcomeFeedback missing required field '{req}'")
    if not isinstance(value["observed_at"], str) or not value["observed_at"].strip():
        raise ValueError("OutcomeFeedback.observed_at must be a non-empty str")
    if not isinstance(value["materialized"], bool):
        raise ValueError("OutcomeFeedback.materialized must be bool")
    if not isinstance(value["triggers_revision"], bool):
        raise ValueError("OutcomeFeedback.triggers_revision must be bool")
    if value["materialized"] is False:
        if not value.get("divergence_note"):
            raise ValueError(
                "OutcomeFeedback.divergence_note is required when materialized is false"
            )
    if "divergence_note" in value and value["divergence_note"] is not None:
        if not isinstance(value["divergence_note"], str) or not value["divergence_note"].strip():
            raise ValueError("OutcomeFeedback.divergence_note must be a non-empty str if present")
    if "evidence_ref" in value and value["evidence_ref"] is not None:
        if not isinstance(value["evidence_ref"], str):
            raise ValueError("OutcomeFeedback.evidence_ref must be str or null")


def validate_alternative_considered(value: dict) -> None:
    """§62d: AlternativeConsidered — description (str), rejected_why (str),
    optional evidence_refs (list[str])."""
    if not isinstance(value, dict):
        raise ValueError(f"AlternativeConsidered must be dict, got {type(value).__name__}")
    for req in ("description", "rejected_why"):
        if req not in value:
            raise ValueError(f"AlternativeConsidered missing required field '{req}'")
        if not isinstance(value[req], str) or not value[req].strip():
            raise ValueError(f"AlternativeConsidered.{req} must be a non-empty str")
    if "evidence_refs" in value and value["evidence_refs"] is not None:
        if not isinstance(value["evidence_refs"], list):
            raise ValueError("AlternativeConsidered.evidence_refs must be list or null")
        for i, r in enumerate(value["evidence_refs"]):
            if not isinstance(r, str):
                raise ValueError(
                    f"AlternativeConsidered.evidence_refs[{i}] must be str, "
                    f"got {type(r).__name__}"
                )


_DECISION_RECORD_KINDS = frozenset({
    "OBJECTIVE_SELECTION",
    "OPERATION_AUTHORIZATION",
    "CHECKPOINT_ACCEPTANCE",
    "RULE_CREATION",
    "NAVIGATION_ASSESSMENT",
    "AUTHORITY_EXERCISE",
    "DESTINATION_EVOLUTION",
})

_DECISION_RECORD_PROVENANCE = frozenset({
    "CURRENT",
    "PROVENANCE_REVISED",
    "SUPERSEDED",
})


def validate_decision_record(value: dict) -> None:
    """§62d: DecisionRecord — full canonical schema."""
    if not isinstance(value, dict):
        raise ValueError(f"DecisionRecord must be dict, got {type(value).__name__}")
    for req in ("id", "kind", "subject", "outcome", "governing_intent_ref",
                "state_digest", "executor", "provenance_status", "decided_at"):
        if req not in value:
            raise ValueError(f"DecisionRecord missing required field '{req}'")
    validate_identifier(value["id"])
    if not value["id"].startswith("dec-"):
        raise ValueError(f"DecisionRecord.id prefix must be 'dec', got '{value['id']}'")
    if value["kind"] not in _DECISION_RECORD_KINDS:
        raise ValueError(
            f"DecisionRecord.kind must be one of {sorted(_DECISION_RECORD_KINDS)}, "
            f"got {value['kind']!r}"
        )
    for str_field in ("subject", "outcome", "governing_intent_ref", "decided_at"):
        if not isinstance(value[str_field], str) or not value[str_field].strip():
            raise ValueError(f"DecisionRecord.{str_field} must be a non-empty str")
    validate_digest_value(value["state_digest"])
    validate_executor_attribution(value["executor"])
    if value["provenance_status"] not in _DECISION_RECORD_PROVENANCE:
        raise ValueError(
            f"DecisionRecord.provenance_status must be one of "
            f"{sorted(_DECISION_RECORD_PROVENANCE)}, got {value['provenance_status']!r}"
        )
    if value["provenance_status"] in ("PROVENANCE_REVISED", "SUPERSEDED"):
        if not value.get("revision_notice"):
            raise ValueError(
                "DecisionRecord.revision_notice is required when provenance_status "
                f"is {value['provenance_status']}"
            )
    if "uncertainty" in value and value["uncertainty"] is not None:
        validate_unit_float(value["uncertainty"])
    if "alternatives" in value and value["alternatives"] is not None:
        if not isinstance(value["alternatives"], list):
            raise ValueError("DecisionRecord.alternatives must be list or null")
        for i, alt in enumerate(value["alternatives"]):
            try:
                validate_alternative_considered(alt)
            except ValueError as e:
                raise ValueError(f"DecisionRecord.alternatives[{i}]: {e}") from e
    for list_field in ("evidence_refs", "constraints", "assumptions",
                        "validity_conditions", "prior_decision_refs"):
        if list_field in value and value[list_field] is not None:
            if not isinstance(value[list_field], list):
                raise ValueError(f"DecisionRecord.{list_field} must be list or null")
            for i, item in enumerate(value[list_field]):
                if not isinstance(item, str):
                    raise ValueError(
                        f"DecisionRecord.{list_field}[{i}] must be str, "
                        f"got {type(item).__name__}"
                    )
    if "completeness" in value and value["completeness"] is not None:
        validate_unit_float(value["completeness"])
    if "reasoning_steps" in value and value["reasoning_steps"] is not None:
        if not isinstance(value["reasoning_steps"], list):
            raise ValueError("DecisionRecord.reasoning_steps must be list or null")
        for i, step in enumerate(value["reasoning_steps"]):
            try:
                validate_reasoning_step(step)
            except ValueError as e:
                raise ValueError(f"DecisionRecord.reasoning_steps[{i}]: {e}") from e
        indices = [s.get("step_index") for s in value["reasoning_steps"]
                   if isinstance(s, dict)]
        if sorted(indices) != list(range(len(indices))):
            raise ValueError(
                "DecisionRecord.reasoning_steps step_index values must form "
                "a contiguous 0-based sequence"
            )
    if "outcome_feedback" in value and value["outcome_feedback"] is not None:
        try:
            validate_outcome_feedback(value["outcome_feedback"])
        except ValueError as e:
            raise ValueError(f"DecisionRecord.outcome_feedback: {e}") from e


_RETENTION_MODES = frozenset({"PROHIBITED", "ARCHIVE", "ROLLING_EVICTION"})


def validate_retention_policy(value: dict) -> None:
    """§62d: RetentionPolicy — id, target_field, compaction_mode, optional thresholds."""
    if not isinstance(value, dict):
        raise ValueError(f"RetentionPolicy must be dict, got {type(value).__name__}")
    for req in ("id", "target_field", "compaction_mode"):
        if req not in value:
            raise ValueError(f"RetentionPolicy missing required field '{req}'")
    validate_identifier(value["id"])
    if not value["id"].startswith("rtp-"):
        raise ValueError(f"RetentionPolicy.id prefix must be 'rtp', got '{value['id']}'")
    if not isinstance(value["target_field"], str) or not value["target_field"].strip():
        raise ValueError("RetentionPolicy.target_field must be a non-empty str")
    if value["compaction_mode"] not in _RETENTION_MODES:
        raise ValueError(
            f"RetentionPolicy.compaction_mode must be one of {sorted(_RETENTION_MODES)}, "
            f"got {value['compaction_mode']!r}"
        )
    has_max_entries = "max_entries" in value and value["max_entries"] is not None
    has_max_age = "max_age_days" in value and value["max_age_days"] is not None
    if not has_max_entries and not has_max_age:
        raise ValueError(
            "RetentionPolicy must specify at least one of max_entries or max_age_days"
        )
    if has_max_entries:
        if not isinstance(value["max_entries"], int) or value["max_entries"] < 1:
            raise ValueError("RetentionPolicy.max_entries must be int ≥ 1")
    if has_max_age:
        if not isinstance(value["max_age_days"], (int, float)) or value["max_age_days"] <= 0:
            raise ValueError("RetentionPolicy.max_age_days must be float > 0")
    if value["compaction_mode"] == "ARCHIVE":
        if not value.get("archive_subpath"):
            raise ValueError(
                "RetentionPolicy.archive_subpath is required when compaction_mode is ARCHIVE"
            )


def validate_compaction_summary(value: dict) -> None:
    """§62d: CompactionSummary — in-place replacement for compacted list segment."""
    if not isinstance(value, dict):
        raise ValueError(f"CompactionSummary must be dict, got {type(value).__name__}")
    for req in ("compaction_event_id", "record_count", "time_range",
                "original_digest", "is_decompactable"):
        if req not in value:
            raise ValueError(f"CompactionSummary missing required field '{req}'")
    validate_identifier(value["compaction_event_id"])
    if not value["compaction_event_id"].startswith("cmp-"):
        raise ValueError(
            f"CompactionSummary.compaction_event_id prefix must be 'cmp', "
            f"got '{value['compaction_event_id']}'"
        )
    if not isinstance(value["record_count"], int) or value["record_count"] < 0:
        raise ValueError("CompactionSummary.record_count must be int ≥ 0")
    tr = value["time_range"]
    if not isinstance(tr, dict) or "from" not in tr or "to" not in tr:
        raise ValueError("CompactionSummary.time_range must be dict with 'from' and 'to' keys")
    if not isinstance(tr["from"], str) or not isinstance(tr["to"], str):
        raise ValueError("CompactionSummary.time_range.from and .to must be str timestamps")
    validate_digest_value(value["original_digest"])
    if not isinstance(value["is_decompactable"], bool):
        raise ValueError("CompactionSummary.is_decompactable must be bool")
    if "record_ids" in value and value["record_ids"] is not None:
        if not isinstance(value["record_ids"], list):
            raise ValueError("CompactionSummary.record_ids must be list or null")
        for i, rid in enumerate(value["record_ids"]):
            if not isinstance(rid, str):
                raise ValueError(
                    f"CompactionSummary.record_ids[{i}] must be str, got {type(rid).__name__}"
                )
    if "kinds" in value and value["kinds"] is not None:
        if not isinstance(value["kinds"], dict):
            raise ValueError("CompactionSummary.kinds must be dict or null")
        for k, ids in value["kinds"].items():
            if not isinstance(k, str):
                raise ValueError(f"CompactionSummary.kinds key must be str, got {type(k).__name__}")
            if not isinstance(ids, list):
                raise ValueError(f"CompactionSummary.kinds[{k!r}] must be list")
            for i, rid in enumerate(ids):
                if not isinstance(rid, str):
                    raise ValueError(
                        f"CompactionSummary.kinds[{k!r}][{i}] must be str, "
                        f"got {type(rid).__name__}"
                    )


_COMPACTION_MODES = frozenset({"ARCHIVE", "ROLLING_EVICTION"})


def validate_compaction_event(value: dict) -> None:
    """§62e: CompactionEvent — infrastructure record for a single compaction act."""
    if not isinstance(value, dict):
        raise ValueError(f"CompactionEvent must be dict, got {type(value).__name__}")
    for req in ("id", "target_state_path", "target_field", "compacted_at",
                "record_count_before", "record_count_after",
                "compaction_mode", "original_digest", "authorized_by"):
        if req not in value:
            raise ValueError(f"CompactionEvent missing required field '{req}'")
    validate_identifier(value["id"])
    if not value["id"].startswith("cmp-"):
        raise ValueError(f"CompactionEvent.id prefix must be 'cmp', got '{value['id']}'")
    for str_field in ("target_state_path", "target_field", "compacted_at", "authorized_by"):
        if not isinstance(value[str_field], str) or not value[str_field].strip():
            raise ValueError(f"CompactionEvent.{str_field} must be a non-empty str")
    for int_field in ("record_count_before", "record_count_after"):
        if not isinstance(value[int_field], int) or value[int_field] < 0:
            raise ValueError(f"CompactionEvent.{int_field} must be int ≥ 0")
    if value["compaction_mode"] not in _COMPACTION_MODES:
        raise ValueError(
            f"CompactionEvent.compaction_mode must be one of {sorted(_COMPACTION_MODES)}, "
            f"got {value['compaction_mode']!r}"
        )
    if value["compaction_mode"] == "ARCHIVE":
        if not value.get("archive_path"):
            raise ValueError(
                "CompactionEvent.archive_path is required when compaction_mode is ARCHIVE"
            )
    validate_digest_value(value["original_digest"])


def validate_compaction_manifest(value: dict) -> None:
    """§62e: CompactionManifest — registry of all CompactionEvents."""
    if not isinstance(value, dict):
        raise ValueError(f"CompactionManifest must be dict, got {type(value).__name__}")
    for req in ("id", "version", "updated_at", "events"):
        if req not in value:
            raise ValueError(f"CompactionManifest missing required field '{req}'")
    validate_identifier(value["id"])
    if not value["id"].startswith("man-"):
        raise ValueError(f"CompactionManifest.id prefix must be 'man', got '{value['id']}'")
    if not isinstance(value["version"], int) or value["version"] < 1:
        raise ValueError("CompactionManifest.version must be int ≥ 1")
    if not isinstance(value["updated_at"], str) or not value["updated_at"].strip():
        raise ValueError("CompactionManifest.updated_at must be a non-empty str")
    if not isinstance(value["events"], list):
        raise ValueError("CompactionManifest.events must be list")
    if value["version"] != len(value["events"]):
        raise ValueError(
            f"CompactionManifest.version ({value['version']}) must equal "
            f"len(events) ({len(value['events'])})"
        )
    for i, ev in enumerate(value["events"]):
        try:
            validate_compaction_event(ev)
        except ValueError as e:
            raise ValueError(f"CompactionManifest.events[{i}]: {e}") from e


def validate_compaction_index(value: dict) -> None:
    """§62e r3: CompactionIndex — per-archive searchable index for O(1) record lookup."""
    if not isinstance(value, dict):
        raise ValueError(f"CompactionIndex must be dict, got {type(value).__name__}")
    for req in ("compaction_event_id", "archive_path", "generated_at",
                "record_count", "id_to_offset", "kind_to_ids"):
        if req not in value:
            raise ValueError(f"CompactionIndex missing required field '{req}'")
    validate_identifier(value["compaction_event_id"])
    if not value["compaction_event_id"].startswith("cmp-"):
        raise ValueError(
            f"CompactionIndex.compaction_event_id prefix must be 'cmp', "
            f"got '{value['compaction_event_id']}'"
        )
    if not isinstance(value["archive_path"], str) or not value["archive_path"].strip():
        raise ValueError("CompactionIndex.archive_path must be a non-empty str")
    if not isinstance(value["generated_at"], str) or not value["generated_at"].strip():
        raise ValueError("CompactionIndex.generated_at must be a non-empty str")
    if not isinstance(value["record_count"], int) or value["record_count"] < 0:
        raise ValueError("CompactionIndex.record_count must be int ≥ 0")
    if not isinstance(value["id_to_offset"], dict):
        raise ValueError("CompactionIndex.id_to_offset must be dict")
    for k, v in value["id_to_offset"].items():
        if not isinstance(k, str):
            raise ValueError(f"CompactionIndex.id_to_offset key must be str, got {type(k).__name__}")
        if not isinstance(v, int) or v < 0:
            raise ValueError(f"CompactionIndex.id_to_offset[{k!r}] must be int ≥ 0")
    if not isinstance(value["kind_to_ids"], dict):
        raise ValueError("CompactionIndex.kind_to_ids must be dict")
    for k, ids in value["kind_to_ids"].items():
        if not isinstance(k, str):
            raise ValueError(f"CompactionIndex.kind_to_ids key must be str")
        if not isinstance(ids, list):
            raise ValueError(f"CompactionIndex.kind_to_ids[{k!r}] must be list")
        for i, rid in enumerate(ids):
            if not isinstance(rid, str):
                raise ValueError(
                    f"CompactionIndex.kind_to_ids[{k!r}][{i}] must be str"
                )


_ARCHIVE_AMENDMENT_KINDS = frozenset({"PROVENANCE_REVISED", "SUPERSEDED", "CUSTOM"})


def validate_archive_amendment(value: dict) -> None:
    """§62e r3: ArchiveAmendment — amendment record for an in-archive record change."""
    if not isinstance(value, dict):
        raise ValueError(f"ArchiveAmendment must be dict, got {type(value).__name__}")
    for req in ("id", "archive_path", "record_id", "amended_at",
                "amendment_kind", "amendment_note", "authorized_by",
                "before_digest", "after_digest"):
        if req not in value:
            raise ValueError(f"ArchiveAmendment missing required field '{req}'")
    validate_identifier(value["id"])
    if not value["id"].startswith("amd-"):
        raise ValueError(f"ArchiveAmendment.id prefix must be 'amd', got '{value['id']}'")
    for str_field in ("archive_path", "record_id", "amended_at",
                      "amendment_note", "authorized_by"):
        if not isinstance(value[str_field], str) or not value[str_field].strip():
            raise ValueError(f"ArchiveAmendment.{str_field} must be a non-empty str")
    if value["amendment_kind"] not in _ARCHIVE_AMENDMENT_KINDS:
        raise ValueError(
            f"ArchiveAmendment.amendment_kind must be one of "
            f"{sorted(_ARCHIVE_AMENDMENT_KINDS)}, got {value['amendment_kind']!r}"
        )
    validate_digest_value(value["before_digest"])
    validate_digest_value(value["after_digest"])


_CRC_PHASES = frozenset({
    "ASSESSING", "PLANNING", "EXECUTING", "VALIDATING", "DORMANT"
})


def validate_technique_application_record(record: dict) -> None:
    """§62h TechniqueApplicationRecord conformance."""
    if not isinstance(record, dict):
        raise ValueError(f"TechniqueApplicationRecord must be dict, got {type(record).__name__}")
    for field in ("id", "technique", "verdict", "reason", "applied_at"):
        if field not in record:
            raise ValueError(f"TechniqueApplicationRecord missing required field '{field}'")
        if not isinstance(record[field], str):
            raise ValueError(f"TechniqueApplicationRecord.{field} must be str, got {type(record[field]).__name__}")
    if record["verdict"] not in {"APPLY", "SKIP", "DELEGATE_EXECUTOR", "DEFER"}:
        raise ValueError(f"TechniqueApplicationRecord.verdict invalid: {record['verdict']!r}")


def validate_cognitive_resume_context(value: dict) -> None:
    """§62e: CognitiveResumeContext — minimum state for executor resume."""
    if not isinstance(value, dict):
        raise ValueError(f"CognitiveResumeContext must be dict, got {type(value).__name__}")
    for req in ("id", "generated_at", "cycle_phase",
                "pending_validations", "blocking_gaps", "state_digest"):
        if req not in value:
            raise ValueError(f"CognitiveResumeContext missing required field '{req}'")
    validate_identifier(value["id"])
    if not value["id"].startswith("crc-"):
        raise ValueError(
            f"CognitiveResumeContext.id prefix must be 'crc', got '{value['id']}'"
        )
    if not isinstance(value["generated_at"], str) or not value["generated_at"].strip():
        raise ValueError("CognitiveResumeContext.generated_at must be a non-empty str")
    if value["cycle_phase"] not in _CRC_PHASES:
        raise ValueError(
            f"CognitiveResumeContext.cycle_phase must be one of {sorted(_CRC_PHASES)}, "
            f"got {value['cycle_phase']!r}"
        )
    validate_digest_value(value["state_digest"])
    for list_field in ("pending_validations", "blocking_gaps"):
        if not isinstance(value[list_field], list):
            raise ValueError(f"CognitiveResumeContext.{list_field} must be list")
        for i, item in enumerate(value[list_field]):
            if not isinstance(item, str):
                raise ValueError(
                    f"CognitiveResumeContext.{list_field}[{i}] must be str, "
                    f"got {type(item).__name__}"
                )


# ── Dispatch ─────────────────────────────────────────────────────────────────

_VALIDATORS: dict[str, Any] = {
    "Identifier":            validate_identifier,
    "DigestValue":           validate_digest_value,
    "UnitFloat":             validate_unit_float,
    "ProductScope":          validate_product_scope,
    "StatusTransition":      validate_status_transition,
    "MetricEffect":          validate_metric_effect,
    "MetricSnapshot":        validate_metric_snapshot,
    "ExecutorAttribution":   validate_executor_attribution,
    "ValidationCheck":       validate_validation_check,
    "ValidationResult":      validate_validation_result,
    "ChangeValidation":      validate_change_validation,
    "ErrorRecord":           validate_error_record,
    "FailureRecord":         validate_failure_record,
    "ExecutionBudget":       validate_execution_budget,
    "RecoveryManifest":      validate_recovery_manifest,
    "UsageRecord":           validate_usage_record,
    "WakeCondition":               validate_wake_condition,
    # §62d r2
    "AlternativeConsidered":       validate_alternative_considered,
    "DecisionRecord":              validate_decision_record,
    "RetentionPolicy":             validate_retention_policy,
    "CompactionSummary":           validate_compaction_summary,
    # §62d r3
    "ReasoningStep":               validate_reasoning_step,
    "OutcomeFeedback":             validate_outcome_feedback,
    # §62e
    "Transaction":                 validate_transaction,
    "OwnershipMarker":             validate_ownership_marker,
    "StaleLockObservation":        validate_stale_lock_observation,
    # §62e r2
    "CompactionEvent":             validate_compaction_event,
    "CompactionManifest":          validate_compaction_manifest,
    "CognitiveResumeContext":      validate_cognitive_resume_context,
    # §62e r3
    "CompactionIndex":             validate_compaction_index,
    "ArchiveAmendment":            validate_archive_amendment,
    # §62h
    "TechniqueApplicationRecord":  validate_technique_application_record,
}


def validate(type_name: str, value: Any) -> None:
    """Dispatch-validate *value* as *type_name*.

    Raises ValueError if the type is unknown or the value is invalid.
    """
    fn = _VALIDATORS.get(type_name)
    if fn is None:
        known = sorted(_VALIDATORS)
        raise ValueError(f"Unknown canonical type '{type_name}'; known: {known}")
    fn(value)


# ── §62i Architectural Meta-Patterns (r14) ───────────────────────────────────

def _require_fields(record: Any, fields: list[str], schema_name: str) -> None:
    """Shared helper: ensure *record* is a dict containing all *fields*."""
    if not isinstance(record, dict):
        raise ValueError(f"{schema_name} must be dict, got {type(record).__name__}")
    for field in fields:
        if field not in record:
            raise ValueError(f"{schema_name} missing required field '{field}'")


def _require_iso_timestamp(value: dict, field: str, citizen: str) -> None:
    """Enforce TemporalFields contract (§62l r39): field must be non-empty string."""
    v = value.get(field)
    if not isinstance(v, str) or not v.strip():
        raise ValueError(f"{citizen}.{field} must be a non-empty ISO-8601 timestamp string")


# AP1 — Canonical Scalar validators

_SCALAR_DOMAINS: dict[str, Any] = {
    "probability": (float, lambda x: 0.0 <= x <= 1.0),
    "budget_fraction": (float, lambda x: 0.0 <= x <= 1.0),
    "confidence": (float, lambda x: 0.0 <= x <= 1.0),
    "count": (int, lambda x: x >= 0),
    "duration_seconds": ((int, float), lambda x: x >= 0.0),
    "iso_timestamp": (str, lambda x: bool(x)),  # non-empty string; full RFC-3339 check is expensive
    "identifier": (str, lambda x: bool(x) and "-" in x),
    "severity_level": (str, lambda x: x in {"INFO", "WARNING", "ERROR", "CRITICAL"}),
    "rfc2119_keyword": (str, lambda x: x in {"MUST", "MUST NOT", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "MAY", "NEED NOT"}),
    "lifecycle_state_value": (str, lambda x: x in {"ASSESSING", "DORMANT", "BLOCKED", "PAUSED"}),
    "verdict_value": (str, lambda x: x in {"VALIDATED", "REJECTED", "PENDING_CAPABILITY"}),
}


def validate_canonical_scalar(value: Any, scalar_name: str) -> None:
    """AP1 — validate a value against its canonical scalar domain."""
    if scalar_name not in _SCALAR_DOMAINS:
        raise ValueError(f"Unknown canonical scalar: {scalar_name!r}")
    expected_type, predicate = _SCALAR_DOMAINS[scalar_name]
    if not isinstance(value, expected_type):
        raise ValueError(
            f"Canonical scalar {scalar_name!r}: expected {expected_type}, "
            f"got {type(value).__name__}"
        )
    if not predicate(value):
        raise ValueError(
            f"Canonical scalar {scalar_name!r}: domain constraint violated for value {value!r}"
        )


def validate_bridge_record(record: dict) -> None:
    """AP11 BridgeRecord conformance."""
    _require_fields(
        record,
        ["id", "bridge_name", "source_schema", "target_schema", "translated_at"],
        "BridgeRecord",
    )


def validate_orchestrator_record(record: dict) -> None:
    """AP12 OrchestratorRecord conformance."""
    _require_fields(
        record,
        ["id", "orchestrator_name", "started_at", "phases_completed", "outcome"],
        "OrchestratorRecord",
    )
    if record["outcome"] not in {"COMPLETED", "ABORTED", "DEGRADED"}:
        raise ValueError(
            f"OrchestratorRecord.outcome invalid: {record['outcome']!r}"
        )


def validate_scheduled_task(record: dict) -> None:
    """AP18 ScheduledTask conformance."""
    _require_fields(
        record,
        ["id", "name", "schedule", "scope", "action", "status", "created_by", "authority_basis"],
        "ScheduledTask",
    )
    if record["status"] not in {"ACTIVE", "PAUSED", "COMPLETED", "ERROR"}:
        raise ValueError(f"ScheduledTask.status invalid: {record['status']!r}")
    if record["created_by"] not in {"USER", "AUTO"}:
        raise ValueError(f"ScheduledTask.created_by invalid: {record['created_by']!r}")
    schedule = record.get("schedule", {})
    if schedule.get("kind") not in {"CRON", "INTERVAL_SECONDS", "TRIGGER", "IMMEDIATE"}:
        raise ValueError(f"TaskSchedule.kind invalid: {schedule.get('kind')!r}")


def validate_customization_record(record: dict) -> None:
    """AP19 CustomizationRecord conformance."""
    _require_fields(
        record,
        ["id", "scope", "key", "value", "reason", "created_at", "preserve_on_update"],
        "CustomizationRecord",
    )
    if record["scope"] not in {"config", "spec_parameter", "runtime_behavior"}:
        raise ValueError(f"CustomizationRecord.scope invalid: {record['scope']!r}")


def validate_lexical_formula(record: dict) -> None:
    """AP17 LexicalFormula conformance."""
    _require_fields(
        record,
        ["id", "spec_section", "natural_language", "formula", "sd_result"],
        "LexicalFormula",
    )
    if not isinstance(record["sd_result"], bool):
        raise ValueError(f"LexicalFormula.sd_result must be bool, got {type(record['sd_result']).__name__}")


def validate_classification_result(record: dict) -> None:
    """ClassificationResult conformance (urace add classification output)."""
    _require_fields(record, ["type", "parameters", "confidence", "raw_text"], "ClassificationResult")
    if record["type"] not in {"goal", "intent", "constraint", "command", "response"}:
        raise ValueError(f"ClassificationResult.type invalid: {record['type']!r}")
    if record["type"] == "command" and "command" not in record.get("parameters", {}):
        raise ValueError("ClassificationResult.parameters.command required when type='command'")
    if record["type"] == "response" and "text" not in record.get("parameters", {}):
        raise ValueError("ClassificationResult.parameters.text required when type='response'")
    if not isinstance(record["confidence"], (int, float)) or not (0.0 <= record["confidence"] <= 1.0):
        raise ValueError(f"ClassificationResult.confidence must be probability in [0,1]")


def validate_classification_batch(record: dict) -> None:
    """ClassificationBatch conformance (urace add compound batch response)."""
    _require_fields(record, ["items", "compound", "raw_text"], "ClassificationBatch")
    if not isinstance(record["items"], list) or len(record["items"]) == 0:
        raise ValueError("ClassificationBatch.items must be a non-empty list")
    if not isinstance(record["compound"], bool):
        raise ValueError("ClassificationBatch.compound must be a boolean")
    if "logic" in record and record["logic"] not in {"and", "or"}:
        raise ValueError("ClassificationBatch.logic must be 'and' or 'or'")
    for i, item in enumerate(record["items"]):
        try:
            validate_classification_result(item)
        except Exception as exc:
            raise ValueError(f"ClassificationBatch.items[{i}]: {exc}") from exc


def validate_pattern_adoption_record(record: dict) -> None:
    """§62j r26: PatternAdoptionRecord — one adopted pattern in a DerivedSystemManifest."""
    _require_fields(record, ["pattern_id", "name", "adoption", "tier", "provides"], "PatternAdoptionRecord")
    if not isinstance(record["pattern_id"], str) or not record["pattern_id"]:
        raise ValueError("PatternAdoptionRecord.pattern_id must be a non-empty string")
    if record["adoption"] not in {"EXPLICIT", "TRANSITIVE"}:
        raise ValueError("PatternAdoptionRecord.adoption must be 'EXPLICIT' or 'TRANSITIVE'")
    if record["tier"] not in {"FOUNDATIONAL", "COMPOSITIONAL", "INTEGRATED"}:
        raise ValueError("PatternAdoptionRecord.tier must be FOUNDATIONAL, COMPOSITIONAL, or INTEGRATED")
    if not isinstance(record["provides"], list):
        raise ValueError("PatternAdoptionRecord.provides must be a list")


def validate_pattern_exclusion_record(record: dict) -> None:
    """§62j r26: PatternExclusionRecord — explicit transitive dep exclusion with acknowledgment."""
    _require_fields(record, ["pattern_id", "name", "override_reason", "acknowledged"], "PatternExclusionRecord")
    if not isinstance(record["pattern_id"], str) or not record["pattern_id"]:
        raise ValueError("PatternExclusionRecord.pattern_id must be a non-empty string")
    if not isinstance(record["override_reason"], str):
        raise ValueError("PatternExclusionRecord.override_reason must be a string")
    if record["acknowledged"] is not True:
        raise ValueError("PatternExclusionRecord.acknowledged must be True — operator must explicitly acknowledge transitive dep exclusion")


def validate_derived_system_manifest(record: dict) -> None:
    """§62j r26: DerivedSystemManifest — opt-in derivation contract for derived systems."""
    _require_fields(record, ["manifest_id", "derived_from", "spec_version", "intent", "generated_at", "adopted_patterns"], "DerivedSystemManifest")
    if record["derived_from"] != "URACE":
        raise ValueError("DerivedSystemManifest.derived_from must be 'URACE'")
    if not isinstance(record["spec_version"], str) or not record["spec_version"]:
        raise ValueError("DerivedSystemManifest.spec_version must be a non-empty string")
    if not isinstance(record["intent"], str) or not record["intent"]:
        raise ValueError("DerivedSystemManifest.intent must be a non-empty string")
    if not isinstance(record["adopted_patterns"], list):
        raise ValueError("DerivedSystemManifest.adopted_patterns must be a list")
    for i, pat in enumerate(record["adopted_patterns"]):
        try:
            validate_pattern_adoption_record(pat)
        except Exception as exc:
            raise ValueError(f"DerivedSystemManifest.adopted_patterns[{i}]: {exc}") from exc
    for i, exc_rec in enumerate(record.get("excluded_deps", [])):
        try:
            validate_pattern_exclusion_record(exc_rec)
        except Exception as e:
            raise ValueError(f"DerivedSystemManifest.excluded_deps[{i}]: {e}") from e


# Register §62j validators after their definitions (forward-ref safe)
_VALIDATORS["PatternAdoptionRecord"] = validate_pattern_adoption_record
_VALIDATORS["PatternExclusionRecord"] = validate_pattern_exclusion_record
_VALIDATORS["DerivedSystemManifest"] = validate_derived_system_manifest


# ── §62b r31: Quality/Resilience schemas ─────────────────────────────────────

_BASE_UNIT_VALUES: frozenset = frozenset({
    "TOKENS", "REQUESTS", "MILLISECONDS", "BYTES", "COUNT", "SCORE", "PERCENT", "CREDITS",
})

_QUALITY_DELTA_CLASSIFICATIONS: frozenset = frozenset({"IMPROVEMENT", "NEUTRAL", "REGRESSION"})
_OPERATION_DEPENDENCY_KINDS: frozenset = frozenset({"FINISH_TO_START", "START_TO_START", "FINISH_TO_FINISH"})
_REINGESTION_STATUSES: frozenset = frozenset({"VERIFIED", "INTEGRITY_GAP"})


def validate_quality_delta(record: dict) -> None:
    """QualityDelta — §62b r31: per-operation quality measurement with predecessor chain (AP9)."""
    _require_fields(
        record,
        ["id", "operation_id", "scope", "score_after", "delta", "classification", "measured_at"],
        "QualityDelta",
    )
    if not isinstance(record["id"], str) or not record["id"].startswith("qdl-"):
        raise ValueError("QualityDelta.id must be string with prefix 'qdl-'")
    if record["classification"] not in _QUALITY_DELTA_CLASSIFICATIONS:
        raise ValueError(
            f"QualityDelta.classification must be one of {sorted(_QUALITY_DELTA_CLASSIFICATIONS)}, "
            f"got {record['classification']!r}"
        )
    score_after = record["score_after"]
    if not isinstance(score_after, (int, float)) or not (0.0 <= score_after <= 1.0):
        raise ValueError(f"QualityDelta.score_after must be UnitFloat [0.0, 1.0], got {score_after!r}")
    if not isinstance(record["delta"], (int, float)):
        raise ValueError(f"QualityDelta.delta must be float, got {type(record['delta']).__name__}")
    score_before = record.get("score_before")
    if score_before is not None:
        if not isinstance(score_before, (int, float)) or not (0.0 <= score_before <= 1.0):
            raise ValueError(f"QualityDelta.score_before must be UnitFloat [0.0, 1.0], got {score_before!r}")


def validate_reingestion_record(record: dict) -> None:
    """ReIngestionRecord — §62b r31: post-decompaction digest-verified re-ingestion record."""
    _require_fields(
        record,
        ["id", "compaction_event_id", "archive_path", "record_count",
         "target_field", "digest_verified", "re_ingested_at", "status"],
        "ReIngestionRecord",
    )
    if not isinstance(record["id"], str) or not record["id"].startswith("rei-"):
        raise ValueError("ReIngestionRecord.id must be string with prefix 'rei-'")
    if record["status"] not in _REINGESTION_STATUSES:
        raise ValueError(
            f"ReIngestionRecord.status must be one of {sorted(_REINGESTION_STATUSES)}, "
            f"got {record['status']!r}"
        )
    if not isinstance(record["record_count"], int) or record["record_count"] < 0:
        raise ValueError(f"ReIngestionRecord.record_count must be int >= 0, got {record['record_count']!r}")
    if not isinstance(record["digest_verified"], bool):
        raise ValueError(
            f"ReIngestionRecord.digest_verified must be bool, got {type(record['digest_verified']).__name__}"
        )
    if not isinstance(record["archive_path"], str) or not record["archive_path"]:
        raise ValueError("ReIngestionRecord.archive_path must be a non-empty string")


def validate_operation_dependency(record: dict) -> None:
    """OperationDependency — §62b r31: typed dependency edge; DAG acyclicity invariant enforced at list level."""
    _require_fields(record, ["from_id", "to_id", "kind"], "OperationDependency")
    if not isinstance(record["from_id"], str) or not record["from_id"]:
        raise ValueError("OperationDependency.from_id must be a non-empty string")
    if not isinstance(record["to_id"], str) or not record["to_id"]:
        raise ValueError("OperationDependency.to_id must be a non-empty string")
    if record["from_id"] == record["to_id"]:
        raise ValueError(
            "OperationDependency: from_id and to_id must be distinct (no self-cycle); "
            f"got {record['from_id']!r}"
        )
    if record["kind"] not in _OPERATION_DEPENDENCY_KINDS:
        raise ValueError(
            f"OperationDependency.kind must be one of {sorted(_OPERATION_DEPENDENCY_KINDS)}, "
            f"got {record['kind']!r}"
        )


def validate_quality_state_entry(record: dict) -> None:
    """QualityStateEntry — §62b r32: per-scope streak accumulator; Product-level citizen independent of ExecutorState."""
    _require_fields(record, ["scope", "current_streak", "best_streak", "last_evaluated_at"], "QualityStateEntry")
    if not isinstance(record["scope"], str) or not record["scope"]:
        raise ValueError("QualityStateEntry.scope must be a non-empty string")
    if not isinstance(record["current_streak"], int) or record["current_streak"] < 0:
        raise ValueError(f"QualityStateEntry.current_streak must be int >= 0, got {record['current_streak']!r}")
    if not isinstance(record["best_streak"], int) or record["best_streak"] < 0:
        raise ValueError(f"QualityStateEntry.best_streak must be int >= 0, got {record['best_streak']!r}")
    if record["best_streak"] < record["current_streak"]:
        raise ValueError(
            f"QualityStateEntry.best_streak ({record['best_streak']}) must be >= current_streak ({record['current_streak']})"
        )
    streak_started_at = record.get("streak_started_at")
    if streak_started_at is not None and not isinstance(streak_started_at, str):
        raise ValueError(f"QualityStateEntry.streak_started_at must be string or null, got {type(streak_started_at).__name__}")
    if not isinstance(record["last_evaluated_at"], str) or not record["last_evaluated_at"]:
        raise ValueError("QualityStateEntry.last_evaluated_at must be a non-empty string")


# Register §62b r31/r32 validators
_VALIDATORS["QualityDelta"] = validate_quality_delta
_VALIDATORS["ReIngestionRecord"] = validate_reingestion_record
_VALIDATORS["OperationDependency"] = validate_operation_dependency
_VALIDATORS["QualityStateEntry"] = validate_quality_state_entry


# ── §62i AP4 ProducerConsumerContract validator (r33) ────────────────────────

_PCC_VIOLATION_PROTOCOLS = frozenset({"REJECT", "QUARANTINE", "ALERT"})


def validate_producer_consumer_contract(value: dict) -> None:
    """§62i AP4: ProducerConsumerContract — named bilateral producer-consumer obligation."""
    _require_fields(
        value,
        ["name", "producer", "consumer", "artifact",
         "producer_must", "consumer_may_assume",
         "violation_protocol", "idempotent"],
        "ProducerConsumerContract",
    )
    for str_field in ("name", "producer", "consumer", "artifact"):
        if not isinstance(value[str_field], str) or not value[str_field].strip():
            raise ValueError(f"ProducerConsumerContract.{str_field} must be a non-empty str")
    if not isinstance(value["producer_must"], list):
        raise ValueError("ProducerConsumerContract.producer_must must be list")
    if not isinstance(value["consumer_may_assume"], list):
        raise ValueError("ProducerConsumerContract.consumer_may_assume must be list")
    if value["violation_protocol"] not in _PCC_VIOLATION_PROTOCOLS:
        raise ValueError(
            f"ProducerConsumerContract.violation_protocol must be one of "
            f"{sorted(_PCC_VIOLATION_PROTOCOLS)}, got {value['violation_protocol']!r}"
        )
    if not isinstance(value["idempotent"], bool):
        raise ValueError("ProducerConsumerContract.idempotent must be bool")


_VALIDATORS["ProducerConsumerContract"] = validate_producer_consumer_contract

# ── §62b r34: Capable Evolution schemas ──────────────────────────────────────

_CAPABILITY_TIERS = frozenset({"FOUNDATIONAL", "COMPOSITIONAL", "INTEGRATED"})
_CAPABILITY_STATUSES = frozenset({"ABSENT", "PARTIAL", "CAPABLE", "OVER_ENGINEERED"})
_MATURITY_LEVELS = frozenset({
    "BOOTSTRAPPING", "FORMING", "CAPABLE", "OPTIMIZED", "OVER_ENGINEERED"
})
_CONTRIBUTION_KINDS = frozenset({
    "CAPABILITY_DEFINING", "CAPABILITY_COMPLETING",
    "QUALITY_IMPROVING", "COMPLEXITY_REDUCING", "MILESTONE_TARGETING",
})
_MILESTONE_STATUSES = frozenset({"PENDING", "ACTIVE", "ACHIEVED", "SUPERSEDED"})
_VDR_TRENDS = frozenset({"IMPROVING", "NEUTRAL", "DECLINING"})


def validate_capability_statement(value: dict) -> None:
    """§62b r34: CapabilityStatement — named testable capability unit."""
    _require_fields(value, ["id", "name", "description", "scope", "tier", "value_weight"],
                    "CapabilityStatement")
    validate_identifier(value["id"])
    if not value["id"].startswith("cap-"):
        raise ValueError(f"CapabilityStatement.id prefix must be 'cap', got '{value['id']}'")
    for str_field in ("name", "description"):
        if not isinstance(value[str_field], str) or not value[str_field].strip():
            raise ValueError(f"CapabilityStatement.{str_field} must be a non-empty str")
    validate_product_scope(value["scope"])
    if value["tier"] not in _CAPABILITY_TIERS:
        raise ValueError(
            f"CapabilityStatement.tier must be one of {sorted(_CAPABILITY_TIERS)}, "
            f"got {value['tier']!r}"
        )
    validate_unit_float(value["value_weight"])
    if "test_criteria" in value and value["test_criteria"] is not None:
        if not isinstance(value["test_criteria"], str):
            raise ValueError("CapabilityStatement.test_criteria must be str or null")


def validate_capability_envelope_entry(value: dict) -> None:
    """§62b r34: CapabilityEnvelopeEntry — current status of a declared capability."""
    _require_fields(value, ["capability_id", "status", "completeness_fraction", "last_assessed_at"],
                    "CapabilityEnvelopeEntry")
    validate_identifier(value["capability_id"])
    if value["status"] not in _CAPABILITY_STATUSES:
        raise ValueError(
            f"CapabilityEnvelopeEntry.status must be one of {sorted(_CAPABILITY_STATUSES)}, "
            f"got {value['status']!r}"
        )
    validate_unit_float(value["completeness_fraction"])
    if not isinstance(value["last_assessed_at"], str) or not value["last_assessed_at"].strip():
        raise ValueError("CapabilityEnvelopeEntry.last_assessed_at must be a non-empty str")
    # completeness_fraction == 1.0 ↔ status in {CAPABLE, OVER_ENGINEERED}
    cf = value["completeness_fraction"]
    if cf == 1.0 and value["status"] not in {"CAPABLE", "OVER_ENGINEERED"}:
        raise ValueError(
            "CapabilityEnvelopeEntry: completeness_fraction=1.0 requires status CAPABLE or OVER_ENGINEERED"
        )
    if cf < 1.0 and value["status"] in {"CAPABLE", "OVER_ENGINEERED"}:
        raise ValueError(
            f"CapabilityEnvelopeEntry: status {value['status']} requires completeness_fraction=1.0, got {cf}"
        )
    if "evidence_refs" in value and value["evidence_refs"] is not None:
        if not isinstance(value["evidence_refs"], list):
            raise ValueError("CapabilityEnvelopeEntry.evidence_refs must be list or null")
        for i, ref in enumerate(value["evidence_refs"]):
            if not isinstance(ref, str):
                raise ValueError(f"CapabilityEnvelopeEntry.evidence_refs[{i}] must be str")


def validate_product_milestone(value: dict) -> None:
    """§62b r34: ProductMilestone — named gated capable state."""
    _require_fields(value, ["id", "name", "description", "capability_gates", "status"],
                    "ProductMilestone")
    validate_identifier(value["id"])
    if not value["id"].startswith("mst-"):
        raise ValueError(f"ProductMilestone.id prefix must be 'mst', got '{value['id']}'")
    for str_field in ("name", "description"):
        if not isinstance(value[str_field], str) or not value[str_field].strip():
            raise ValueError(f"ProductMilestone.{str_field} must be a non-empty str")
    if not isinstance(value["capability_gates"], list):
        raise ValueError("ProductMilestone.capability_gates must be list")
    for i, gid in enumerate(value["capability_gates"]):
        if not isinstance(gid, str):
            raise ValueError(f"ProductMilestone.capability_gates[{i}] must be str")
    if value["status"] not in _MILESTONE_STATUSES:
        raise ValueError(
            f"ProductMilestone.status must be one of {sorted(_MILESTONE_STATUSES)}, "
            f"got {value['status']!r}"
        )
    if "achieved_at" in value and value["achieved_at"] is not None:
        if not isinstance(value["achieved_at"], str):
            raise ValueError("ProductMilestone.achieved_at must be str or null")
    if "superseded_by" in value and value["superseded_by"] is not None:
        validate_identifier(value["superseded_by"])


def validate_sweet_spot_assessment(value: dict) -> None:
    """§62b r34: SweetSpotAssessment — sweet spot evaluation output."""
    _require_fields(
        value,
        ["id", "assessed_at", "maturity_level",
         "capability_completeness", "value_density", "product_surface_measure"],
        "SweetSpotAssessment",
    )
    validate_identifier(value["id"])
    if not value["id"].startswith("ssa-"):
        raise ValueError(f"SweetSpotAssessment.id prefix must be 'ssa', got '{value['id']}'")
    if not isinstance(value["assessed_at"], str) or not value["assessed_at"].strip():
        raise ValueError("SweetSpotAssessment.assessed_at must be a non-empty str")
    if value["maturity_level"] not in _MATURITY_LEVELS:
        raise ValueError(
            f"SweetSpotAssessment.maturity_level must be one of {sorted(_MATURITY_LEVELS)}, "
            f"got {value['maturity_level']!r}"
        )
    validate_unit_float(value["capability_completeness"])
    if not isinstance(value["value_density"], (int, float)) or value["value_density"] < 0.0:
        raise ValueError("SweetSpotAssessment.value_density must be float >= 0.0")
    if not isinstance(value["product_surface_measure"], int) or value["product_surface_measure"] < 0:
        raise ValueError("SweetSpotAssessment.product_surface_measure must be int >= 0")
    if "active_milestone_id" in value and value["active_milestone_id"] is not None:
        validate_identifier(value["active_milestone_id"])
    if "milestone_status" in value and value["milestone_status"] is not None:
        if value["milestone_status"] not in {"PENDING", "ACHIEVED"}:
            raise ValueError(
                f"SweetSpotAssessment.milestone_status must be PENDING or ACHIEVED, "
                f"got {value['milestone_status']!r}"
            )
    for list_field in ("capability_gaps", "over_engineered_caps"):
        if list_field in value and value[list_field] is not None:
            if not isinstance(value[list_field], list):
                raise ValueError(f"SweetSpotAssessment.{list_field} must be list or null")


def validate_value_density_record(value: dict) -> None:
    """§62b r34: ValueDensityRecord — value density time-series entry."""
    _require_fields(value, ["id", "recorded_at", "value_density", "surface_measure"],
                    "ValueDensityRecord")
    validate_identifier(value["id"])
    if not value["id"].startswith("vdr-"):
        raise ValueError(f"ValueDensityRecord.id prefix must be 'vdr', got '{value['id']}'")
    if not isinstance(value["recorded_at"], str) or not value["recorded_at"].strip():
        raise ValueError("ValueDensityRecord.recorded_at must be a non-empty str")
    if not isinstance(value["value_density"], (int, float)) or value["value_density"] < 0.0:
        raise ValueError("ValueDensityRecord.value_density must be float >= 0.0")
    if not isinstance(value["surface_measure"], int) or value["surface_measure"] < 0:
        raise ValueError("ValueDensityRecord.surface_measure must be int >= 0")
    if "delta" in value and value["delta"] is not None:
        if not isinstance(value["delta"], (int, float)):
            raise ValueError("ValueDensityRecord.delta must be float or null")
    if "trend" in value and value["trend"] is not None:
        if value["trend"] not in _VDR_TRENDS:
            raise ValueError(
                f"ValueDensityRecord.trend must be one of {sorted(_VDR_TRENDS)}, "
                f"got {value['trend']!r}"
            )
    if "assessment_id" in value and value["assessment_id"] is not None:
        validate_identifier(value["assessment_id"])


# ── §62b r35: ProductVersion, TestRecord, TestRunRecord ──────────────────────

_TEST_KINDS = frozenset({"UNIT", "INTEGRATION", "BEHAVIORAL", "ACCEPTANCE", "CAPABILITY_GATE"})
_TEST_VERDICTS = frozenset({"PASS", "FAIL", "ERROR", "SKIPPED"})
_TEST_RECORD_STATUSES = frozenset({"ACTIVE", "DISABLED"})


def validate_product_version(value: dict) -> None:
    """§62b r35: ProductVersion — durable versioned record of a milestone achievement."""
    _require_fields(
        value,
        ["id", "version", "milestone_id", "achieved_at", "maturity_level",
         "capability_completeness", "value_density", "product_surface_measure"],
        "ProductVersion",
    )
    validate_identifier(value["id"])
    if not value["id"].startswith("pver-"):
        raise ValueError(f"ProductVersion.id prefix must be 'pver', got '{value['id']}'")
    if not isinstance(value["version"], str) or not value["version"].strip():
        raise ValueError("ProductVersion.version must be a non-empty str")
    validate_identifier(value["milestone_id"])
    if not isinstance(value["achieved_at"], str) or not value["achieved_at"].strip():
        raise ValueError("ProductVersion.achieved_at must be a non-empty str")
    if value["maturity_level"] not in _MATURITY_LEVELS:
        raise ValueError(
            f"ProductVersion.maturity_level must be one of {sorted(_MATURITY_LEVELS)}, "
            f"got {value['maturity_level']!r}"
        )
    validate_unit_float(value["capability_completeness"])
    if not isinstance(value["value_density"], (int, float)) or value["value_density"] < 0.0:
        raise ValueError("ProductVersion.value_density must be float ≥ 0.0")
    if not isinstance(value["product_surface_measure"], int) or value["product_surface_measure"] < 0:
        raise ValueError("ProductVersion.product_surface_measure must be int ≥ 0")
    if "next_milestone_id" in value and value["next_milestone_id"] is not None:
        validate_identifier(value["next_milestone_id"])


def validate_test_record(value: dict) -> None:
    """§62b r35: TestRecord — named behavioral expectation the Product must satisfy."""
    _require_fields(value, ["id", "name", "description", "scope", "kind", "status"],
                    "TestRecord")
    validate_identifier(value["id"])
    if not value["id"].startswith("tst-"):
        raise ValueError(f"TestRecord.id prefix must be 'tst', got '{value['id']}'")
    for str_field in ("name", "description"):
        if not isinstance(value[str_field], str) or not value[str_field].strip():
            raise ValueError(f"TestRecord.{str_field} must be a non-empty str")
    validate_product_scope(value["scope"])
    if value["kind"] not in _TEST_KINDS:
        raise ValueError(
            f"TestRecord.kind must be one of {sorted(_TEST_KINDS)}, got {value['kind']!r}"
        )
    if value["status"] not in _TEST_RECORD_STATUSES:
        raise ValueError(
            f"TestRecord.status must be one of {sorted(_TEST_RECORD_STATUSES)}, "
            f"got {value['status']!r}"
        )
    if "capability_id" in value and value["capability_id"] is not None:
        validate_identifier(value["capability_id"])
    if "last_run_id" in value and value["last_run_id"] is not None:
        validate_identifier(value["last_run_id"])


def validate_test_run_record(value: dict) -> None:
    """§62b r35: TestRunRecord — result of executing a set of TestRecords."""
    _require_fields(
        value,
        ["id", "run_at", "scope", "kind", "total", "passed", "failed",
         "skipped", "errored", "verdict"],
        "TestRunRecord",
    )
    validate_identifier(value["id"])
    if not value["id"].startswith("trr-"):
        raise ValueError(f"TestRunRecord.id prefix must be 'trr', got '{value['id']}'")
    if not isinstance(value["run_at"], str) or not value["run_at"].strip():
        raise ValueError("TestRunRecord.run_at must be a non-empty str")
    validate_product_scope(value["scope"])
    if value["kind"] not in _TEST_KINDS:
        raise ValueError(
            f"TestRunRecord.kind must be one of {sorted(_TEST_KINDS)}, got {value['kind']!r}"
        )
    for int_field in ("total", "passed", "failed", "skipped", "errored"):
        if not isinstance(value[int_field], int) or value[int_field] < 0:
            raise ValueError(f"TestRunRecord.{int_field} must be int ≥ 0")
    # Count contract: total = passed + failed + skipped + errored
    expected_total = value["passed"] + value["failed"] + value["skipped"] + value["errored"]
    if value["total"] != expected_total:
        raise ValueError(
            f"TestRunRecord count mismatch: total={value['total']} ≠ "
            f"passed+failed+skipped+errored={expected_total}"
        )
    if value["verdict"] not in _TEST_VERDICTS:
        raise ValueError(
            f"TestRunRecord.verdict must be one of {sorted(_TEST_VERDICTS)}, "
            f"got {value['verdict']!r}"
        )
    # Verdict contract: PASS ↔ failed==0 AND errored==0
    if value["verdict"] == "PASS" and (value["failed"] > 0 or value["errored"] > 0):
        raise ValueError(
            "TestRunRecord.verdict=PASS requires failed==0 and errored==0"
        )
    if value["verdict"] == "FAIL" and value["failed"] == 0 and value["errored"] == 0:
        raise ValueError(
            "TestRunRecord.verdict=FAIL requires failed > 0 or errored > 0"
        )
    for list_field in ("capability_ids_covered", "test_ids"):
        if list_field in value and value[list_field] is not None:
            if not isinstance(value[list_field], list):
                raise ValueError(f"TestRunRecord.{list_field} must be list or null")
            for i, item in enumerate(value[list_field]):
                if not isinstance(item, str):
                    raise ValueError(f"TestRunRecord.{list_field}[{i}] must be str")


# §62b r34
_VALIDATORS["CapabilityStatement"] = validate_capability_statement
_VALIDATORS["CapabilityEnvelopeEntry"] = validate_capability_envelope_entry
_VALIDATORS["ProductMilestone"] = validate_product_milestone
_VALIDATORS["SweetSpotAssessment"] = validate_sweet_spot_assessment
_VALIDATORS["ValueDensityRecord"] = validate_value_density_record
# §62b r35
_VALIDATORS["ProductVersion"] = validate_product_version
_VALIDATORS["TestRecord"] = validate_test_record
_VALIDATORS["TestRunRecord"] = validate_test_run_record

# §62j r36
_DERIVATION_KINDS = frozenset({"MANIFEST", "REFRESH", "CAPABILITY_APPLY", "MILESTONE_DRAFT"})


def validate_derived_manifest_ref(value: dict) -> None:
    _require_fields(value, ["id", "manifest_id", "spec_version", "generated_at",
                            "adopted_pattern_ids", "intent"], "DerivedManifestRef")
    if not isinstance(value["id"], str) or not value["id"].startswith("dmr-"):
        raise ValueError(f"DerivedManifestRef.id prefix must be 'dmr-', got '{value['id']}'")
    if not isinstance(value["spec_version"], str) or not value["spec_version"].strip():
        raise ValueError("DerivedManifestRef.spec_version must be non-empty string")
    if not isinstance(value["adopted_pattern_ids"], list):
        raise ValueError("DerivedManifestRef.adopted_pattern_ids must be a list")


def validate_derivation_record(value: dict) -> None:
    _require_fields(value, ["id", "kind", "pattern_ids", "spec_version", "derived_at"],
                    "DerivationRecord")
    if not isinstance(value["id"], str) or not value["id"].startswith("drv-"):
        raise ValueError(f"DerivationRecord.id prefix must be 'drv-', got '{value['id']}'")
    if value["kind"] not in _DERIVATION_KINDS:
        raise ValueError(f"DerivationRecord.kind must be one of {sorted(_DERIVATION_KINDS)}")
    if not isinstance(value["pattern_ids"], list):
        raise ValueError("DerivationRecord.pattern_ids must be a list")
    if not isinstance(value["spec_version"], str) or not value["spec_version"].strip():
        raise ValueError("DerivationRecord.spec_version must be non-empty string")
    if "capabilities_applied" in value and value["capabilities_applied"] is not None:
        if not isinstance(value["capabilities_applied"], int) or value["capabilities_applied"] < 0:
            raise ValueError("DerivationRecord.capabilities_applied must be non-negative int")


_VALIDATORS["DerivedManifestRef"] = validate_derived_manifest_ref
_VALIDATORS["DerivationRecord"] = validate_derivation_record


# r37 — Safety, AssessmentRecord, DiscoveryRecord, OwnershipMarker, MarketSignal, FitHypothesis

_POLICY_KINDS = frozenset({
    "PROHIBITION", "PERMISSION", "APPROVAL_REQUIREMENT", "BUDGET",
    "PRIVACY", "RISK", "SELF_MODIFICATION", "DELEGATION", "TERMINATION",
})
_POLICY_STATUSES = frozenset({"ACTIVE", "SUSPENDED", "REVOKED"})
_CONSTRAINT_ENFORCEMENTS = frozenset({"HARD", "SOFT"})
_ASSESSMENT_CYCLE_STATUSES = frozenset({"COMPLETE", "CAPABILITY_SKIPPED", "ERROR_INTERRUPTED"})
_DISCOVERY_CYCLE_STATUSES = frozenset({"COMPLETE", "INCOMPLETE", "ERROR_INTERRUPTED"})
_OWNERSHIP_MARKER_STATUSES = frozenset({"HELD", "STALE", "CLEARED"})
_MARKET_SIGNAL_KINDS = frozenset({
    "USER_BEHAVIOR", "USER_FEEDBACK", "RETENTION_SIGNAL", "CONVERSION_SIGNAL",
    "COMPETITOR_SIGNAL", "EXTERNAL_METRIC", "REVENUE_SIGNAL",
})
_FIT_CONFIDENCES = frozenset({"STRONG", "MODERATE", "WEAK", "ABSENT"})
_FIT_HYPOTHESIS_STATUSES = frozenset({"ACTIVE", "VALIDATED", "REFUTED", "STALE"})


def validate_policy_record(value: dict) -> None:
    _require_fields(value, ["id", "kind", "status", "description", "scope",
                            "enforcement", "authority_basis", "established_at"], "PolicyRecord")
    check_governing_record_fields(value, "PolicyRecord")
    _require_iso_timestamp(value, "established_at", "PolicyRecord")
    if not isinstance(value["id"], str) or not value["id"].startswith("pol-"):
        raise ValueError(f"PolicyRecord.id prefix must be 'pol-', got '{value['id']}'")
    if value["kind"] not in _POLICY_KINDS:
        raise ValueError(f"PolicyRecord.kind must be one of {sorted(_POLICY_KINDS)}")
    if value["status"] not in _POLICY_STATUSES:
        raise ValueError(f"PolicyRecord.status must be one of {sorted(_POLICY_STATUSES)}")
    if value["enforcement"] not in _CONSTRAINT_ENFORCEMENTS:
        raise ValueError(f"PolicyRecord.enforcement must be HARD or SOFT")
    if not isinstance(value["description"], str) or not value["description"].strip():
        raise ValueError("PolicyRecord.description must be non-empty string")


def validate_hard_constraint(value: dict) -> None:
    _require_fields(value, ["id", "description", "scope", "established_at", "authority_basis"],
                    "HardConstraint")
    check_governing_record_fields(value, "HardConstraint")
    _require_iso_timestamp(value, "established_at", "HardConstraint")
    if not isinstance(value["id"], str) or not value["id"].startswith("hco-"):
        raise ValueError(f"HardConstraint.id prefix must be 'hco-', got '{value['id']}'")
    if not isinstance(value["description"], str) or not value["description"].strip():
        raise ValueError("HardConstraint.description must be non-empty string")
    if "violation_count" in value and value["violation_count"] is not None:
        if not isinstance(value["violation_count"], int) or value["violation_count"] < 0:
            raise ValueError("HardConstraint.violation_count must be non-negative int")


def validate_assessment_record(value: dict) -> None:
    _require_fields(value, ["id", "assessed_at", "lifecycle_phase", "authority_ids",
                            "intent_id", "cycle_status"], "AssessmentRecord")
    _require_iso_timestamp(value, "assessed_at", "AssessmentRecord")
    if not isinstance(value["id"], str) or not value["id"].startswith("asr-"):
        raise ValueError(f"AssessmentRecord.id prefix must be 'asr-', got '{value['id']}'")
    if value["cycle_status"] not in _ASSESSMENT_CYCLE_STATUSES:
        raise ValueError(f"AssessmentRecord.cycle_status must be one of {sorted(_ASSESSMENT_CYCLE_STATUSES)}")
    if not isinstance(value["authority_ids"], list):
        raise ValueError("AssessmentRecord.authority_ids must be a list")
    if not isinstance(value["intent_id"], str) or not value["intent_id"].strip():
        raise ValueError("AssessmentRecord.intent_id must be non-empty string")


def validate_discovery_record(value: dict) -> None:
    _require_fields(value, ["id", "cycle_id", "started_at", "cycle_status",
                            "categories_evaluated", "candidates_found", "candidates_rejected"],
                    "DiscoveryRecord")
    _require_iso_timestamp(value, "started_at", "DiscoveryRecord")
    if not isinstance(value["id"], str) or not value["id"].startswith("dsc-"):
        raise ValueError(f"DiscoveryRecord.id prefix must be 'dsc-', got '{value['id']}'")
    if value["cycle_status"] not in _DISCOVERY_CYCLE_STATUSES:
        raise ValueError(f"DiscoveryRecord.cycle_status must be one of {sorted(_DISCOVERY_CYCLE_STATUSES)}")
    if not isinstance(value["categories_evaluated"], list):
        raise ValueError("DiscoveryRecord.categories_evaluated must be a list")
    if not isinstance(value["candidates_found"], int) or value["candidates_found"] < 0:
        raise ValueError("DiscoveryRecord.candidates_found must be non-negative int")
    if not isinstance(value["candidates_rejected"], int) or value["candidates_rejected"] < 0:
        raise ValueError("DiscoveryRecord.candidates_rejected must be non-negative int")


def validate_ownership_marker(value: dict) -> None:
    _require_fields(value, ["id", "owner_id", "scope", "acquired_at", "status"],
                    "OwnershipMarker")
    _require_iso_timestamp(value, "acquired_at", "OwnershipMarker")
    if not isinstance(value["id"], str) or not value["id"].startswith("omk-"):
        raise ValueError(f"OwnershipMarker.id prefix must be 'omk-', got '{value['id']}'")
    if value["status"] not in _OWNERSHIP_MARKER_STATUSES:
        raise ValueError(f"OwnershipMarker.status must be one of {sorted(_OWNERSHIP_MARKER_STATUSES)}")
    if not isinstance(value["owner_id"], str) or not value["owner_id"].strip():
        raise ValueError("OwnershipMarker.owner_id must be non-empty string")


def validate_market_signal(value: dict) -> None:
    _require_fields(value, ["id", "kind", "observed_at", "source", "description",
                            "confidence", "intent_id"], "MarketSignal")
    _require_iso_timestamp(value, "observed_at", "MarketSignal")
    if not isinstance(value["id"], str) or not value["id"].startswith("mks-"):
        raise ValueError(f"MarketSignal.id prefix must be 'mks-', got '{value['id']}'")
    if value["kind"] not in _MARKET_SIGNAL_KINDS:
        raise ValueError(f"MarketSignal.kind must be one of {sorted(_MARKET_SIGNAL_KINDS)}")
    if value["confidence"] not in _FIT_CONFIDENCES:
        raise ValueError(f"MarketSignal.confidence must be one of {sorted(_FIT_CONFIDENCES)}")
    if not isinstance(value["description"], str) or not value["description"].strip():
        raise ValueError("MarketSignal.description must be non-empty string")


def validate_fit_hypothesis(value: dict) -> None:
    _require_fields(value, ["id", "description", "intent_id", "status", "confidence",
                            "created_at", "last_updated_at"], "FitHypothesis")
    _require_iso_timestamp(value, "created_at", "FitHypothesis")
    _require_iso_timestamp(value, "last_updated_at", "FitHypothesis")
    if not isinstance(value["id"], str) or not value["id"].startswith("fhy-"):
        raise ValueError(f"FitHypothesis.id prefix must be 'fhy-', got '{value['id']}'")
    if value["status"] not in _FIT_HYPOTHESIS_STATUSES:
        raise ValueError(f"FitHypothesis.status must be one of {sorted(_FIT_HYPOTHESIS_STATUSES)}")
    if value["confidence"] not in _FIT_CONFIDENCES:
        raise ValueError(f"FitHypothesis.confidence must be one of {sorted(_FIT_CONFIDENCES)}")
    if not isinstance(value["description"], str) or not value["description"].strip():
        raise ValueError("FitHypothesis.description must be non-empty string")


_VALIDATORS["PolicyRecord"] = validate_policy_record
_VALIDATORS["HardConstraint"] = validate_hard_constraint
_VALIDATORS["AssessmentRecord"] = validate_assessment_record
_VALIDATORS["DiscoveryRecord"] = validate_discovery_record
_VALIDATORS["OwnershipMarker"] = validate_ownership_marker
_VALIDATORS["MarketSignal"] = validate_market_signal
_VALIDATORS["FitHypothesis"] = validate_fit_hypothesis


# ── r38: Shared Reuse Contracts ─────────────────────────────────────────────

_REVALIDATION_SCOPES = frozenset({"DECISION_ONLY", "DEPENDENT_PLANS", "FULL_LIFECYCLE"})

INTEGRITY_GAP_CATALOG: dict[str, dict] = {
    "progress-stagnation":               {"severity": "BLOCKING", "section": "62c"},
    "derived-manifest-stale":            {"severity": "WARNING",  "section": "62j"},
    "regression-checkpoint-pending":     {"severity": "WARNING",  "section": "62c"},
    "stale-decision-revalidation":       {"severity": "WARNING",  "section": "62c"},
    "over-engineered":                   {"severity": "WARNING",  "section": "59b"},
    "cognitive-resume-stale":            {"severity": "WARNING",  "section": "62e"},
    "compaction-manifest-divergence":    {"severity": "BLOCKING", "section": "62f"},
    "archive-count-ceiling":             {"severity": "WARNING",  "section": "62f"},
    "compaction-partial-failure":        {"severity": "WARNING",  "section": "62f"},
    "multi-product-compact-cycle":       {"severity": "BLOCKING", "section": "62k"},
    "scope-target-not-resolvable":       {"severity": "WARNING",  "section": "62k"},
    "capability-envelope-breach":        {"severity": "WARNING",  "section": "59b"},
    "capability-without-test-coverage":  {"severity": "WARNING",  "section": "59b"},
    "pattern-capability-gap":            {"severity": "WARNING",  "section": "62j"},
    "no-hard-constraints-declared":      {"severity": "WARNING",  "section": "72"},
    "retention-policy-violated":         {"severity": "WARNING",  "section": "62b"},
    "wake-registration-missing-fields":  {"severity": "WARNING",  "section": "67"},
    "wake-registration-unverified":      {"severity": "WARNING",  "section": "67"},
    "governing-record-unresolvable-authority": {"severity": "WARNING", "section": "62l"},
    "authority-conflict":                {"severity": "BLOCKING", "section": "14"},
    "indeterminate-effect-unresolvable": {"severity": "BLOCKING", "section": "52"},
    "incomplete-discovery-cycle":        {"severity": "WARNING",  "section": "38"},
    "assessment-cycle-error-interrupted":{"severity": "WARNING",  "section": "37"},
    "operator-gate-open":                {"severity": "BLOCKING", "section": "62l"},
    "wake-integrity-gap":                {"severity": "WARNING",  "section": "62l"},
    "compliance-record-missing":         {"severity": "WARNING",  "section": "62l"},
    "stale-decision":                    {"severity": "WARNING",  "section": "62c"},
    "stale-evidence":                    {"severity": "WARNING",  "section": "62c"},
    "unsupported-rule":                  {"severity": "WARNING",  "section": "62c"},
    "capability-state-missing":          {"severity": "WARNING",  "section": "43"},
    "context-budget-priority-inversion": {"severity": "WARNING",  "section": "62c"},
    "discovery-proportionality-deferred":{"severity": "WARNING",  "section": "62c"},
    "discovery-yield-exhausted":         {"severity": "WARNING",  "section": "62c"},
    "milestone-chain-broken":            {"severity": "BLOCKING", "section": "59b"},
    "milestone-chain-cycle":             {"severity": "BLOCKING", "section": "59b"},
    "non-monotone-version":              {"severity": "BLOCKING", "section": "59b"},
    "operation-dependency-cycle":        {"severity": "BLOCKING", "section": "65"},
    "reingestion-archive-missing":       {"severity": "BLOCKING", "section": "62c"},
    "reingestion-digest-mismatch":       {"severity": "BLOCKING", "section": "62c"},
    "test-run-count-mismatch":           {"severity": "WARNING",  "section": "62c"},
    "decision-reasoning-cycle":          {"severity": "WARNING",  "section": "62g"},
    "capability-without-test-record":    {"severity": "WARNING",  "section": "62b"},
    "context-budget-advisory":           {"severity": "INFO",     "section": "62c"},
    "metric-definition-drift":           {"severity": "WARNING",  "section": "62b"},
    "governance-anchor-drift":           {"severity": "BLOCKING", "section": "62c"},
    # r53 additions
    "metric-baseline-unauthorized-mutation": {"severity": "BLOCKING", "section": "62b"},
    "metric-mutation-policy-missing":    {"severity": "WARNING",  "section": "62b"},
    "threshold-audit-missing":           {"severity": "WARNING",  "section": "62h"},
    "citizen-base-violation":            {"severity": "WARNING",  "section": "62b"},
    "authority-cache-stale":             {"severity": "WARNING",  "section": "62b"},
    "executor-policy-missing":           {"severity": "WARNING",  "section": "62a"},
    "unresolved-effects-reconciliation-failure": {"severity": "WARNING", "section": "62c"},
    # r54 additions
    "compaction-authorization-stale": {"severity": "WARNING",  "section": "62f"},
    "validation-evidence-missing":    {"severity": "WARNING",  "section": "62b"},
    "compaction-blocked-on-anchor-drift": {"severity": "WARNING", "section": "62f"},
    # r61 additions
    "community-feed-terms-not-accepted":    {"severity": "BLOCKING", "section": "62l"},
    "community-feed-adapter-unavailable":   {"severity": "WARNING",  "section": "62l"},
    "patch-proposal-confidence-below-floor":{"severity": "INFO",     "section": "62l"},
    "patch-proposal-queue-overflow":        {"severity": "WARNING",  "section": "62l"},
    "community-signal-relevance-below-floor":{"severity": "INFO",    "section": "62l"},
    # r62 additions
    "construct-dependency-cycle":           {"severity": "BLOCKING", "section": "62i"},
    "construct-self-reference":             {"severity": "BLOCKING", "section": "62i"},
    # r63 additions
    "community-inbox-evolution-blocked":    {"severity": "WARNING",  "section": "62l"},
    "feature-bundle-unknown-construct":     {"severity": "WARNING",  "section": "62j"},
    # §62o OnboardGate
    "onboard-config-incomplete":            {"severity": "BLOCKING", "section": "62o"},
    "onboard-no-readable-product-files":    {"severity": "BLOCKING", "section": "62o"},
    "onboard-intent-unanchored":            {"severity": "BLOCKING", "section": "62o"},
    "onboard-capability-envelope-missing":  {"severity": "WARNING",  "section": "62o"},
    "onboard-confirmation-pending":         {"severity": "BLOCKING", "section": "62o"},
    "onboard-record-config-diverged":       {"severity": "WARNING",  "section": "62o"},
    # §62l ProductSwitchProtocol / §62b ProductEntry
    "product-registry-unknown-product":     {"severity": "WARNING",  "section": "§62c ProductSwitchProtocol"},
    "product-switch-pending-onboard":       {"severity": "INFO",     "section": "§62c ProductSwitchProtocol"},
    "product-registry-duplicate-name":      {"severity": "WARNING",  "section": "§62b ProductEntry uniqueness contract"},
    # §62l FleetOrchestrationProtocol (FOP)
    "fleet-member-crashed":                 {"severity": "WARNING",  "section": "§62l FOP clause 4"},
    "fleet-duplicate-state-path":           {"severity": "BLOCKING", "section": "§62l FOP clause 1"},
    "fleet-signal-broadcast-skipped":       {"severity": "INFO",     "section": "§62l FOP clause 3"},
    # r75 AuditRecord / ObservabilityContract
    "audit-record-compacted":               {"severity": "BLOCKING", "section": "§62l AuditRecord non-compactability contract"},
    "trace-record-missing":                 {"severity": "WARNING",  "section": "§62l ObservabilityContract autonomy gap"},
    # r77 Closed-Loop Autonomy
    "layer-boundary-violation":             {"severity": "BLOCKING", "section": "§62l LayerModel clause 2"},
    "output-schema-unregistered":           {"severity": "WARNING",  "section": "§62l OutputSchemaRegistry"},
    "feedback-overdue":                     {"severity": "INFO",     "section": "§62u FeedbackAccumulator"},
    "feedback-negative-objective":          {"severity": "INFO",     "section": "§62c FeedbackAccumulator"},
    "feedback-negative-decision":           {"severity": "INFO",     "section": "§62c FeedbackAccumulator"},
    # r83 IGC sync — kinds declared in spec but missing from runtime
    "activation-health-failure":            {"severity": "BLOCKING", "section": "§74 Safe Runtime Activation"},
    "archive-not-found":                    {"severity": "BLOCKING", "section": "§62c Re-Ingestion Mechanism"},
    "blocker-escalated":                    {"severity": "WARNING",  "section": "§62b Blocker schema classification contract"},
    "capability-regression":                {"severity": "WARNING",  "section": "§62c Test Coverage Gate"},
    "checkpoint-write-timeout":             {"severity": "WARNING",  "section": "§61 Checkpoint / §62b CheckpointRecord"},
    "crc-context-overflow":                 {"severity": "BLOCKING", "section": "§62e/§62c CRC injection"},
    "crc-version-mismatch":                 {"severity": "WARNING",  "section": "§62e CognitiveResumeContext"},
    "crrp-retry-exceeded":                  {"severity": "BLOCKING", "section": "§73 CRRP"},
    "crrp-step-failure":                    {"severity": "BLOCKING", "section": "§73 CRRP"},
    "effect-unreconcilable":                {"severity": "WARNING",  "section": "§52 Effect Reconciliation"},
    "inbox-priority-tier-violation":        {"severity": "WARNING",  "section": "§62i AP14 priority-tier contract"},
    "integrity-signal-unclassified":        {"severity": "WARNING",  "section": "§62c SignalClassifier"},
    "justification-context-incomplete":     {"severity": "WARNING",  "section": "§62b JustificationContext / §62l JustificationContract"},
    "justification-cycle-detected":         {"severity": "BLOCKING", "section": "§62g Justification System"},
    "justification-depth-exceeded":         {"severity": "WARNING",  "section": "§62g Justification System"},
    "lifecycle-boundary-violation":         {"severity": "BLOCKING", "section": "§62b LifecycleBoundary / §62l BoundaryContract"},
    "metric-source-discovery-unavailable":  {"severity": "WARNING",  "section": "§62c External Metric Collection"},
    "milestone-chain-integrity-failure":    {"severity": "BLOCKING", "section": "§59b ProductMilestone"},
    "partial-update-recovered":             {"severity": "INFO",     "section": "§74 Safe Runtime Activation"},
    "partial-update-unrecoverable":         {"severity": "BLOCKING", "section": "§74 Safe Runtime Activation"},
    "rebootstrap-attempt-failed":           {"severity": "INFO",     "section": "§74 Re-Bootstrap"},
    "rebootstrap-terminal-failure":         {"severity": "BLOCKING", "section": "§74 Re-Bootstrap"},
    "reingestion-duplicate-skipped":        {"severity": "INFO",     "section": "§62c Re-Ingestion Mechanism"},
    "retention-pass-partial-failure":       {"severity": "WARNING",  "section": "§62f Retention Policy"},
    "rollback-failure":                     {"severity": "BLOCKING", "section": "§74 Safe Runtime Activation"},
    "scp-atomic-extension-violation":       {"severity": "BLOCKING", "section": "§62n SCP Gate 3"},
    "scp-forward-reference":                {"severity": "BLOCKING", "section": "§62n SCP Gate 1"},
    "scp-incomplete-revision-declaration":  {"severity": "WARNING",  "section": "§62n SCP Gate 2"},
    "spec-state-divergence":                {"severity": "BLOCKING", "section": "§74 Safe Runtime Activation"},
    "stale-manifest-override":              {"severity": "WARNING",  "section": "§62j Stale DerivedManifestRef"},
    "technique-classification-disagreement":{"severity": "WARNING",  "section": "§62h T5"},
    "unauthorized-threshold-adjustment":    {"severity": "WARNING",  "section": "§62c Staleness Detection"},
    "value-density-below-floor":            {"severity": "WARNING",  "section": "§62c Sweet Spot Evaluation"},
    "wake-registration-expired":            {"severity": "BLOCKING", "section": "§62c Wake Registration Verification"},
    "wake-registration-stale":              {"severity": "WARNING",  "section": "§62c Wake Registration Verification"},
    "onboard-unregistered-product-hint":    {"severity": "INFO",     "section": "§62o OnboardGate --scan"},
    # r85 additions
    "product-budget-exceeded":              {"severity": "BLOCKING", "section": "§62v Resource Budget Protocol"},
    "product-roi-below-floor":              {"severity": "WARNING",  "section": "§62v Resource Budget Protocol"},
    "product-efficiency-degraded":          {"severity": "WARNING",  "section": "§62v Resource Budget Protocol"},
    "product-budget-period-reset":          {"severity": "INFO",     "section": "§62v Resource Budget Protocol"},
    # r98: integrity hash kinds
    "spec-update-hash-mismatch":            {"severity": "BLOCKING", "section": "§62k --hash / §62k urace update"},
    "manifest-hash-mismatch":              {"severity": "WARNING",  "section": "§62k --verify / §62k urace derive"},
    # r72 product registry kinds (IGC sync — previously missing from catalog)
    "product-registry-duplicate-state-path": {"severity": "WARNING",  "section": "§62p State Isolation Contract"},
    "product-remove-active-blocked":          {"severity": "BLOCKING", "section": "§62k urace product remove"},
    "product-deactivate-active-blocked":      {"severity": "BLOCKING", "section": "§62k urace product deactivate"},
    # rounds 6-8 gap kinds (spec r107+)
    "external-edit-invalidated-candidate":    {"severity": "WARNING",  "section": "62l"},
    "external-edit-operator-required":        {"severity": "BLOCKING", "section": "62l"},
    "unsupported-intent-unacknowledged":      {"severity": "BLOCKING", "section": "62l"},
    "inheritance-confirmation-pending":       {"severity": "BLOCKING", "section": "62l"},
    "objective-scope-conflict":               {"severity": "BLOCKING", "section": "62l"},
    "objective-orphaned":                     {"severity": "WARNING",  "section": "62l"},
    "objective-partial-orphan":               {"severity": "WARNING",  "section": "62l"},
    "evidence-insufficient-for-commit":       {"severity": "BLOCKING", "section": "62l"},
    "evidence-override-unjustified":          {"severity": "BLOCKING", "section": "62l"},
    "evidence-stabilization-backlog":         {"severity": "WARNING",  "section": "62l"},
    "evidence-induced-thrashing":             {"severity": "WARNING",  "section": "62l"},
    "evidence-retirement-cascade-incomplete": {"severity": "BLOCKING", "section": "62l"},
    "convergence-bound-exceeded":             {"severity": "BLOCKING", "section": "62l"},
    "cross-product-phase-violation":          {"severity": "BLOCKING", "section": "62l"},
    "dependent-operation-halted":             {"severity": "BLOCKING", "section": "62l"},
    "plan-dependency-order-violated":         {"severity": "BLOCKING", "section": "62l"},
    "rollback-incomplete":                    {"severity": "BLOCKING", "section": "62l"},
    "metric-key-collision":                   {"severity": "BLOCKING", "section": "62l"},
    "metric-unregistered":                    {"severity": "WARNING",  "section": "62l"},
    "metric-unauthorized-reporter":           {"severity": "WARNING",  "section": "62l"},
    "metric-out-of-range":                    {"severity": "WARNING",  "section": "62l"},
    "metric-baseline-zero":                   {"severity": "WARNING",  "section": "62l"},
    "metric-baseline-drift":                  {"severity": "WARNING",  "section": "62l"},
    "gap-normalization-skipped":              {"severity": "WARNING",  "section": "62l"},
    "gap-weight-incomplete":                  {"severity": "WARNING",  "section": "62l"},
    "learning-signal-quality-low":            {"severity": "WARNING",  "section": "62l"},
    "adaptive-config-proposal-pending":       {"severity": "INFO",     "section": "62l"},
    "adaptive-config-proposal-expired":       {"severity": "WARNING",  "section": "62l"},
    "sandbox-projection-divergence":          {"severity": "WARNING",  "section": "62l"},
    "policy-conflict-detected":               {"severity": "BLOCKING", "section": "62l"},
    # r110 gap A+B+C kinds
    "intent-formula-structural-drift":    {"severity": "BLOCKING", "section": "62l"},
    "intent-formula-validation-skipped":  {"severity": "WARNING",  "section": "62l"},
    "authority-ceiling-reached":          {"severity": "BLOCKING", "section": "62l"},
    "intent-coverage-dimensions-missing": {"severity": "BLOCKING", "section": "62l"},
    "intent-dimension-unbound":           {"severity": "BLOCKING", "section": "62l"},
    "intent-binding-metric-unregistered": {"severity": "BLOCKING", "section": "62l"},
    "intent-metric-baseline-missing":     {"severity": "BLOCKING", "section": "62l"},
    "intent-binding-threshold-missing":   {"severity": "BLOCKING", "section": "62l"},
    "intent-binding-orphaned":            {"severity": "WARNING",  "section": "62l"},
    # r111 gap 1-4 kinds
    "coverage-dimension-unreachable":            {"severity": "BLOCKING", "section": "62l"},
    "strategy-diverging":                        {"severity": "BLOCKING", "section": "62l"},
    "domain-weight-insufficient-observations":   {"severity": "WARNING",  "section": "62l"},
    "evidence-request-expired":                  {"severity": "WARNING",  "section": "62l"},
    # r112 gap 1-4 kinds
    "gap-regression-detected":            {"severity": "BLOCKING", "section": "62l"},
    "state-transition-validation-missing":{"severity": "WARNING",  "section": "62l"},
    "intent-semantic-drift":              {"severity": "BLOCKING", "section": "62l"},
    "intent-drift-assessment-missing":    {"severity": "WARNING",  "section": "62l"},
    "intent-aggregation-missing":         {"severity": "BLOCKING", "section": "62l"},
    "gap-impact-estimate-missing":        {"severity": "WARNING",  "section": "62l"},
    # r113 gap 1-10 kinds
    "causal-model-stale":                   {"severity": "WARNING",  "section": "62l"},
    "causal-edge-confounded":               {"severity": "WARNING",  "section": "62l"},
    "causal-intervention-unverified":       {"severity": "WARNING",  "section": "62l"},
    "lookahead-plan-missing":               {"severity": "WARNING",  "section": "62l"},
    "lookahead-horizon-exceeded":           {"severity": "WARNING",  "section": "62l"},
    "authority-conflict-unresolved":        {"severity": "BLOCKING", "section": "62l"},
    "principal-veto-active":                {"severity": "BLOCKING", "section": "62l"},
    "principal-hierarchy-missing":          {"severity": "WARNING",  "section": "62l"},
    "adversarial-signal-detected":          {"severity": "BLOCKING", "section": "62l"},
    "metric-fabrication-suspected":         {"severity": "BLOCKING", "section": "62l"},
    "uncertainty-band-missing":             {"severity": "WARNING",  "section": "62l"},
    "high-uncertainty-action-taken":        {"severity": "WARNING",  "section": "62l"},
    "fleet-knowledge-sync-missing":         {"severity": "WARNING",  "section": "62l"},
    "constraint-candidate-pending-review":  {"severity": "WARNING",  "section": "62l"},
    "constraint-candidate-conflict":        {"severity": "WARNING",  "section": "62l"},
    "explanation-synthesis-failed":         {"severity": "WARNING",  "section": "62l"},
    "portfolio-allocation-missing":         {"severity": "WARNING",  "section": "62l"},
    "portfolio-budget-overallocated":       {"severity": "BLOCKING", "section": "62l"},
    "deadline-breached":                    {"severity": "BLOCKING", "section": "62l"},
    "deadline-approaching":                 {"severity": "WARNING",  "section": "62l"},
    # r114 gap C1-C7, A1-A4, S1-S3
    "goal-tree-cycle-detected":               {"severity": "BLOCKING", "section": "62l"},
    "goal-tree-leaf-uncovered":               {"severity": "WARNING",  "section": "62l"},
    "objective-dependency-violated":          {"severity": "BLOCKING", "section": "62l"},
    "objective-dependency-cycle":             {"severity": "BLOCKING", "section": "62l"},
    "intent-version-missing":                 {"severity": "WARNING",  "section": "62l"},
    "intent-version-rollback-failed":         {"severity": "BLOCKING", "section": "62l"},
    "self-modification-evidence-insufficient":{"severity": "BLOCKING", "section": "62l"},
    "self-modification-principal-insufficient":{"severity": "BLOCKING","section": "62l"},
    "normative-invariant-violated":           {"severity": "BLOCKING", "section": "62l"},
    "audit-log-suppression-attempted":        {"severity": "BLOCKING", "section": "62l"},
    "value-baseline-missing":                 {"severity": "WARNING",  "section": "62l"},
    "expected-value-uncalibrated":            {"severity": "WARNING",  "section": "62l"},
    "operator-attention-overload":            {"severity": "WARNING",  "section": "62l"},
    "review-queue-stale":                     {"severity": "WARNING",  "section": "62l"},
    "policy-mechanism-coupling-detected":     {"severity": "WARNING",  "section": "62l"},
    "event-trigger-missed":                   {"severity": "WARNING",  "section": "62l"},
    "event-trigger-storm":                    {"severity": "WARNING",  "section": "62l"},
    "capability-degraded":                    {"severity": "WARNING",  "section": "62l"},
    "fallback-chain-exhausted":               {"severity": "BLOCKING", "section": "62l"},
    "fsm-transition-undefined":               {"severity": "BLOCKING", "section": "62l"},
    "fsm-state-unreachable":                  {"severity": "WARNING",  "section": "62l"},
    "feedback-loop-oscillation-detected":     {"severity": "WARNING",  "section": "62l"},
    "feedback-latency-stale":                 {"severity": "WARNING",  "section": "62l"},
    "cross-product-resource-conflict":        {"severity": "BLOCKING", "section": "62l"},
    "fleet-resource-lock-timeout":            {"severity": "WARNING",  "section": "62l"},
    "state-schema-incompatible":              {"severity": "BLOCKING", "section": "62l"},
    "migration-transform-failed":             {"severity": "BLOCKING", "section": "62l"},
    "normative-invariant-supersedes-boundary":{"severity": "BLOCKING", "section": "62l"},
    # r115 hardening pass — new IGC kinds
    "lookahead-plan-cold-start":             {"severity": "WARNING",  "section": "62l"},
    "intent-aggregation-no-directives":      {"severity": "WARNING",  "section": "62l"},
    "self-modification-rollback-missing":    {"severity": "BLOCKING", "section": "62l"},
    "normative-enforcement-unavailable":     {"severity": "BLOCKING", "section": "62l"},
    "goal-tree-unauthorized-mutation":       {"severity": "BLOCKING", "section": "62l"},
    "neutral-operation-accumulation":        {"severity": "WARNING",  "section": "62l"},
    "dependency-gate-blocked-all-objectives":{"severity": "WARNING",  "section": "62l"},
    "value-feedback-timeout":               {"severity": "WARNING",  "section": "62l"},
    "causal-graph-cycle-detected":          {"severity": "BLOCKING", "section": "62l"},
    "data-insufficient":                    {"severity": "WARNING",  "section": "62l"},
    "initialization-incomplete":            {"severity": "WARNING",  "section": "62l"},
    "adversarial-pattern-accumulated":      {"severity": "WARNING",  "section": "62l"},
    "intent-drift-retry-cap-reached":       {"severity": "BLOCKING", "section": "62l"},
    "schema-migration-partial":             {"severity": "WARNING",  "section": "62l"},
    "uncertainty-high-consecutive-cycles":  {"severity": "BLOCKING", "section": "62l"},
    # r116 full gap closure
    "goal-tree-node-empty":              {"severity": "BLOCKING", "section": "62l"},
    "goal-tree-orphan-detected":         {"severity": "BLOCKING", "section": "62l"},
    "evidence-integrity-violated":       {"severity": "BLOCKING", "section": "62l"},
    "lifecycle-normative-halt":          {"severity": "BLOCKING", "section": "62l"},
    "feedback-loop-oscillation-damped":  {"severity": "WARNING",  "section": "62l"},
    "dependency-rollback-revert":        {"severity": "WARNING",  "section": "62l"},
    "fleet-lock-reservation-conflict":   {"severity": "WARNING",  "section": "62l"},
    "operator-overload-escalated":       {"severity": "BLOCKING", "section": "62l"},
    "policy-scanner-blocking-violation": {"severity": "BLOCKING", "section": "62l"},
    "value-calibration-insufficient":    {"severity": "WARNING",  "section": "62l"},
    # r117 §62v DataSourceRegistry
    "data-source-sync-failed":           {"severity": "BLOCKING", "section": "62x"},
    "data-source-write-failed":          {"severity": "BLOCKING", "section": "62x"},
    "data-source-credential-expired":    {"severity": "BLOCKING", "section": "62x"},
    "data-source-credential-exposed":    {"severity": "BLOCKING", "section": "62x"},
    "data-source-direction-violation":   {"severity": "BLOCKING", "section": "62x"},
    "data-source-schema-mismatch":       {"severity": "WARNING",  "section": "62x"},
    "data-source-connectivity-lost":     {"severity": "WARNING",  "section": "62x"},
    "data-source-write-rejected":        {"severity": "WARNING",  "section": "62x"},
    # r117 §62w UniversalEntryProtocol
    "route-conflict-detected":           {"severity": "BLOCKING", "section": "62y"},
    "route-graph-cycle-detected":        {"severity": "BLOCKING", "section": "62y"},
    "route-dispatch-partial":            {"severity": "WARNING",  "section": "62y"},
    "universal-route-ambiguous":         {"severity": "WARNING",  "section": "62y"},
    "route-confidence-below-threshold":  {"severity": "WARNING",  "section": "62y"},
}

# Alias: tests may import IGC_KINDS from cli module — expose via primitives for cross-module test use
IGC_KINDS = INTEGRITY_GAP_CATALOG

RETIRED_IGC_KINDS: frozenset[str] = frozenset()  # populated as kinds complete drain period


def validate_igc_kind_entries() -> list[str]:
    """Return list of validation errors in INTEGRITY_GAP_CATALOG entries."""
    errors = []
    for kind, entry in INTEGRITY_GAP_CATALOG.items():
        if "severity" not in entry:
            errors.append(f"{kind}: missing 'severity'")
        if "section" not in entry:
            errors.append(f"{kind}: missing 'section'")
        allowed = {"severity", "section", "deprecated_since", "superseded_by"}
        extra = set(entry.keys()) - allowed
        if extra:
            errors.append(f"{kind}: unknown keys {extra}")
        if "superseded_by" in entry and "deprecated_since" not in entry:
            errors.append(f"{kind}: 'superseded_by' requires 'deprecated_since'")
    return errors


OUTPUT_SCHEMA_REGISTRY: dict[str, dict] = {
    "check":          {"version": "1.0", "stable_since": "r77", "fields": ["schema_version", "lifecycle_state", "gaps", "score", "categories"]},
    "vitals":         {"version": "1.0", "stable_since": "r77", "fields": ["schema_version", "lifecycle_state", "maturity", "metrics", "blockers"]},
    "trace list":     {"version": "1.0", "stable_since": "r77", "fields": ["schema_version", "records", "total"]},
    "feedback list":  {"version": "1.0", "stable_since": "r77", "fields": ["schema_version", "records", "total"]},
    "schema list":    {"version": "1.0", "stable_since": "r77", "fields": ["schema_version", "schemas"]},
    "schema inspect": {"version": "1.0", "stable_since": "r77", "fields": ["schema_version", "command", "output_schema_version", "stable_since", "fields"]},
}

FEATURE_BUNDLE_REGISTRY: dict[str, dict] = {
    "community-inbox": {
        "construct_ids": ["AP38", "CSI", "PPP_M", "PPP", "CommunityFeed", "CommunitySignal", "PatchProposal", "FeatureBundle", "FeatureBundleRef"],
        "description": "All constructs for community signal ingestion and patch proposal pipeline",
        "spec_version": "r62",
        "source": "spec",
    },
    "evidence-quality": {
        "construct_ids": ["EvidenceSufficiencyGate", "EvidenceSufficiencyContract", "EvidenceAgeRetirementContract", "EvidenceSufficiencyFormula", "EvidenceSufficiencySnapshot", "EvidenceAgeRetirementRecord"],
        "description": "All constructs for evidence quality assessment, sufficiency gating, and age-based retirement",
        "spec_version": "r107",
        "source": "spec",
    },
    "adaptive-learning": {
        "construct_ids": ["OutcomeLearningFeedbackContract", "FeedbackAccumulator", "OutcomeFeedbackRecord", "OutcomeFeedbackContract", "LearningWeightUpdateFormula"],
        "description": "All constructs for closed-loop outcome learning and adaptive weight updates",
        "spec_version": "r107",
        "source": "spec",
    },
    "executor-trust": {
        "construct_ids": ["ExecutorTrustProfile", "ExecutorTrustDegradationFormula", "ExecutorTrustRecoveryProtocol"],
        "description": "All constructs for executor trust lifecycle — degradation on failure, recovery on success",
        "spec_version": "r107",
        "source": "spec",
    },
    "audit-trail": {
        "construct_ids": ["AuditRecord", "TraceRecord", "ObservabilityContract", "InspectionContract"],
        "description": "All constructs for immutable audit trail and observability compliance",
        "spec_version": "r107",
        "source": "spec",
    },
    "decision-attribution": {
        "construct_ids": ["DecisionRecord", "JustificationContext", "JustificationContract", "BoundaryContract"],
        "description": "All constructs for decision traceability, justification, and authority boundary enforcement",
        "spec_version": "r107",
        "source": "spec",
    },
    "metric-governance": {
        "construct_ids": ["MetricRegistry", "MetricSemanticCoherenceContract", "GapNormalizationContract", "GapNormalizationGovernanceContract"],
        "description": "All constructs for metric registration, semantic coherence, and gap normalization governance",
        "spec_version": "r107",
        "source": "spec",
    },
    "convergence-loop": {
        "construct_ids": ["ConvergenceOrderingContract", "ConvergenceBoundFormula", "CycleTriggerQualificationProtocol", "CycleTriggerWeightFormula"],
        "description": "All constructs for cycle convergence ordering, bound enforcement, and trigger qualification",
        "spec_version": "r107",
        "source": "spec",
    },
    "autonomous-governance": {
        "construct_ids": ["GoverningRecord", "AutonomyBoundaryAuditContract", "DirectiveMutationRevalidationProtocol", "StateAuditProtocol"],
        "description": "All constructs for governing autonomous decisions, boundary auditing, and state integrity",
        "spec_version": "r107",
        "source": "spec",
    },
    "human-in-the-loop": {
        "construct_ids": ["OperatorDecisionEscalationRecord", "OperatorDecisionTimeoutEscalationContract", "OperatorIntentElicitationProtocol"],
        "description": "All constructs for human escalation, timeout-based auto-escalation, and intent elicitation",
        "spec_version": "r107",
        "source": "spec",
    },
    "rollback-safety": {
        "construct_ids": ["RollbackCompletenessAttestation", "RollbackVerificationContract"],
        "description": "All constructs for rollback completeness attestation and digest-verified rollback safety",
        "spec_version": "r107",
        "source": "spec",
    },
    "scope-isolation": {
        "construct_ids": ["ObjectiveScopeDeclaration", "ObjectiveScopeIsolationContract", "ObjectiveOrphanRetirementContract", "ObjectiveOrphanageDetectionGate"],
        "description": "All constructs for objective scope isolation, conflict prevention, and orphan retirement",
        "spec_version": "r107",
        "source": "spec",
    },
    "lifecycle-continuity": {
        "construct_ids": ["CrossLifecycleInheritanceProtocol", "CrossProductLifecycleOrderingContract", "LifecycleInheritanceRecord"],
        "description": "All constructs for cross-lifecycle state inheritance and multi-product phase ordering",
        "spec_version": "r107",
        "source": "spec",
    },
    "sandbox-safety": {
        "construct_ids": ["SandboxExecutionContract", "AP10"],
        "description": "All constructs for sandbox execution isolation and projected-state validation",
        "spec_version": "r107",
        "source": "spec",
    },
    "policy-governance": {
        "construct_ids": ["PolicyConflictResolutionProtocol", "PolicyRecord", "PolicyRule"],
        "description": "All constructs for policy conflict detection, resolution, and rule governance",
        "spec_version": "r107",
        "source": "spec",
    },
    "adaptive-config": {
        "construct_ids": ["AdaptiveConfigProposal", "AdaptiveConfigProposalProtocol", "AdaptiveConfigSuggestionMechanism"],
        "description": "All constructs for autonomous config suggestion, operator-gated application, and feedback-driven adaptation",
        "spec_version": "r107",
        "source": "spec",
    },
    "base-types": {
        "construct_ids": ["AP0", "AP1", "AP2", "CitizenBase", "AuthorizedCitizen", "TemporalCitizen", "GoverningRecord", "AuditRecord"],
        "description": "Foundational type system — base citizen clusters, identity invariant, authority binding, audit base",
        "spec_version": "r107",
        "source": "spec",
    },
    "foundational-patterns": {
        "construct_ids": ["AP0", "AP1", "AP2", "AP3", "AP4", "AP5", "AP7", "AP26", "AP35"],
        "description": "Foundational architectural meta-patterns — identity, authority, evidence, state, compaction, lifecycle, formulas",
        "spec_version": "r107",
        "source": "spec",
    },
    "foundational-contracts": {
        "construct_ids": ["GoverningRecord", "AuditRecord", "BoundaryContract", "JustificationContract", "AuthorityClosureInvariant", "RevalidationScope"],
        "description": "Foundational governance contracts — authority closure, revalidation scope, boundary enforcement",
        "spec_version": "r107",
        "source": "spec",
    },
    "igc-vocabulary": {
        "construct_ids": ["IntegrityGapCatalog"],
        "description": "The complete IntegrityGapCatalog taxonomy as a standalone reusable vocabulary (all declared IGC kinds)",
        "spec_version": "r107",
        "source": "spec",
    },
    "technique-library": {
        "construct_ids": ["T1", "T2", "T3", "T4", "T5", "T6", "T7"],
        "description": "All §62h TechniqueApplicabilitySystem techniques — keyword, structural, semantic, evidence, scope, hybrid, boundary",
        "spec_version": "r107",
        "source": "spec",
    },
    "nss-framework": {
        "construct_ids": ["NSS"],
        "description": "The Normative Specification Standard as a standalone meta-spec framework for construct governance",
        "spec_version": "r107",
        "source": "spec",
    },
    "causal-attribution": {
        "construct_ids": ["CausalModelProtocol", "CausalEdgeRecord", "CausalModelRecord", "CausalAttributionContract"],
        "description": "Directed causal graph over Product signals, attribution, and confounding detection",
        "spec_version": "r117",
        "source": "spec",
    },
    "goal-decomposition": {
        "construct_ids": ["GoalDecompositionProtocol", "GoalTreeNode", "GoalCoverageCompletenessProtocol", "GoalCoverageCompletenessRecord", "RecursiveGoalDecompositionContract"],
        "description": "AND/OR compositional goal trees, coverage completeness, and recursive decomposition",
        "spec_version": "r117",
        "source": "spec",
    },
    "intent-versioning": {
        "construct_ids": ["IntentVersioningProtocol", "IntentVersionRecord", "IntentDriftProtocol", "IntentDriftRecord", "IntentAggregationFormula", "IntentAggregateGapRecord"],
        "description": "Intent mutation history, drift detection, and weighted gap aggregation",
        "spec_version": "r117",
        "source": "spec",
    },
    "lookahead-planning": {
        "construct_ids": ["PlanningHorizonProtocol", "LookaheadPlanRecord", "GapImpactEstimationProtocol", "GapImpactEstimate", "DomainWeightCalibrationProtocol", "DomainWeightRecord"],
        "description": "N-step lookahead, per-action Δgap estimation, and domain weight calibration",
        "spec_version": "r117",
        "source": "spec",
    },
    "principal-hierarchy": {
        "construct_ids": ["PrincipalHierarchyProtocol", "PrincipalRecord", "AuthorityConflictRecord"],
        "description": "Multi-principal authority lattice with precedence and veto",
        "spec_version": "r117",
        "source": "spec",
    },
    "adversarial-robustness": {
        "construct_ids": ["AdversarialRobustnessProtocol", "AdversarialSignalRecord"],
        "description": "Adversarial pattern detection: metric fabrication, evidence injection, gap gaming, boundary probing",
        "spec_version": "r117",
        "source": "spec",
    },
    "uncertainty-propagation": {
        "construct_ids": ["UncertaintyPropagationFormula", "UncertaintyBand", "EpistemicEscalationProtocol"],
        "description": "Credibility uncertainty propagation to UncertaintyBand and escalation on high-uncertainty actions",
        "spec_version": "r117",
        "source": "spec",
    },
    "fleet-knowledge": {
        "construct_ids": ["FleetKnowledgeProtocol", "FleetKnowledgeRecord"],
        "description": "Cross-product learning transfer at fleet boundary sync",
        "spec_version": "r117",
        "source": "spec",
    },
    "constraint-discovery": {
        "construct_ids": ["ConstraintDiscoveryProtocol", "ConstraintCandidate"],
        "description": "BOUNDARY rule candidate hypotheses from failure patterns",
        "spec_version": "r117",
        "source": "spec",
    },
    "explanation": {
        "construct_ids": ["ExplanationProtocol", "ExplanationRecord"],
        "description": "On-demand DecisionRecord explanation via causal chain",
        "spec_version": "r117",
        "source": "spec",
    },
    "portfolio-execution": {
        "construct_ids": ["PortfolioExecutionProtocol", "PortfolioAllocationRecord", "ObjectiveDependencyContract", "ObjectiveDependencyRecord"],
        "description": "Budget-split across parallel Objectives with dependency ordering",
        "spec_version": "r117",
        "source": "spec",
    },
    "deadline-enforcement": {
        "construct_ids": ["DeadlineEnforcementContract", "DeadlineRecord"],
        "description": "Hard deadlines on Goals/Objectives with BLOCKING breach and escalation",
        "spec_version": "r117",
        "source": "spec",
    },
    "reactive-events": {
        "construct_ids": ["ReactiveEventProtocol", "EventTriggerRecord"],
        "description": "Event-driven cycle triggers: METRIC_THRESHOLD, WEBHOOK, EXTERNAL_STATE_CHANGE",
        "spec_version": "r117",
        "source": "spec",
    },
    "capability-degradation": {
        "construct_ids": ["CapabilityDegradationContract", "DegradationRecord"],
        "description": "Formal fallback chains for FOUNDATIONAL constructs on degradation",
        "spec_version": "r117",
        "source": "spec",
    },
    "fsm-audit": {
        "construct_ids": ["StateSpaceAuditContract", "StateSpaceAuditRecord"],
        "description": "Lifecycle FSM completeness verification at bootstrap",
        "spec_version": "r117",
        "source": "spec",
    },
    "feedback-latency": {
        "construct_ids": ["FeedbackLoopLatencyContract", "FeedbackLatencyRecord"],
        "description": "Per-loop latency measurement and oscillation detection",
        "spec_version": "r117",
        "source": "spec",
    },
    "value-accounting": {
        "construct_ids": ["ValueAccountingProtocol", "ValueLedgerEntry"],
        "description": "Per-operation value ledger, ROI computation, expected-vs-realized tracking",
        "spec_version": "r117",
        "source": "spec",
    },
    "self-modification-gate": {
        "construct_ids": ["RecursiveSelfModificationGate", "SelfModificationRecord", "NormativeIntegrityContract", "NormativeViolationRecord"],
        "description": "Elevated-evidence gate for system-file changes with normative invariants",
        "spec_version": "r117",
        "source": "spec",
    },
    "policy-layer": {
        "construct_ids": ["PolicyLayerContract", "PolicyOverrideRecord", "OperatorAttentionContract", "AttentionBudgetRecord"],
        "description": "All Config-backed behavioral parameters, operator deviations, and attention budget",
        "spec_version": "r117",
        "source": "spec",
    },
    "data-sources": {
        "construct_ids": ["DataSourceRegistryProtocol", "DataSourceRecord", "CredentialRecord", "DataSyncRecord"],
        "description": "Bidirectional data source registry — PULL/PUSH adapters, credential isolation, sync tracking",
        "spec_version": "r117",
        "source": "spec",
    },
    "universal-entry": {
        "construct_ids": ["UniversalEntryProtocol", "RouteGraphRecord"],
        "description": "Multi-route DAG dispatch, conflict detection, cycle detection",
        "spec_version": "r117",
        "source": "spec",
    },
    "intent-state-validation": {
        "construct_ids": ["StateTransitionValidationProtocol", "StateTransitionValidationRecord", "IntentFormulaValidityProtocol", "IntentFormulaValidityRecord", "IntentAmbiguityAudit", "AuthorityCeilingSignal", "AuthorityCeilingRecord"],
        "description": "Post-transition gap verification, Goodhart drift, ambiguity audit, and ceiling classification",
        "spec_version": "r117",
        "source": "spec",
    },
}

_GOVERNING_RECORD_REQUIRED = frozenset({"id", "authority_basis", "scope", "established_at"})


def check_governing_record_fields(value: dict, citizen_name: str) -> None:
    """Verify a citizen declares all GoverningRecord canonical fields (§62l)."""
    for field in _GOVERNING_RECORD_REQUIRED:
        if field not in value:
            raise ValueError(f"{citizen_name} missing GoverningRecord field '{field}'")
    if not isinstance(value.get("authority_basis", ""), str) or not str(value.get("authority_basis", "")).strip():
        raise ValueError(f"{citizen_name}.authority_basis must be non-empty string")
    if not isinstance(value.get("scope", ""), str) or not str(value.get("scope", "")).strip():
        raise ValueError(f"{citizen_name}.scope must be non-empty string")


def validate_revalidation_scope(value: str) -> None:
    """Validate a RevalidationScope value (§62l)."""
    if value not in _REVALIDATION_SCOPES:
        raise ValueError(f"RevalidationScope must be one of {sorted(_REVALIDATION_SCOPES)}, got {value!r}")


def is_known_gap_kind(kind: str) -> bool:
    """Return True if kind is registered in INTEGRITY_GAP_CATALOG (§62l)."""
    return kind in INTEGRITY_GAP_CATALOG


def gap_severity(kind: str) -> str | None:
    """Return canonical severity for a known gap kind, or None if unknown."""
    entry = INTEGRITY_GAP_CATALOG.get(kind)
    return entry["severity"] if entry else None


# ── r39: RevalidationScope + AuthorityClosureInvariant (§62l) ────────────────

_REVALIDATION_SCOPE_MAP: dict[str, str] = {
    "evidence-retracted":        "DECISION_ONLY",
    "evidence-revised":          "DECISION_ONLY",
    "authority-suspended":       "DEPENDENT_PLANS",
    "authority-revoked":         "DEPENDENT_PLANS",
    "intent-versioned":          "FULL_LIFECYCLE",
    "intent-replaced":           "FULL_LIFECYCLE",
    "hard-constraint-added":     "DEPENDENT_PLANS",
    "policy-status-changed":     "DEPENDENT_PLANS",
    "multiple-premise-changes":  "FULL_LIFECYCLE",
    "executor-identity-broken":  "DECISION_ONLY",
}

_NON_AUTHORITY_SOURCES = frozenset({
    "evidence", "priority", "capability", "market_signal",
    "trigger", "schedule", "executor_recommendation", "product_value",
    "user_absence", "market_success",
})


def determine_revalidation_scope(change_class: str) -> str:
    """Return minimum RevalidationScope for a premise change class (§62l r39).
    Defaults to FULL_LIFECYCLE for unknown change classes.
    """
    return _REVALIDATION_SCOPE_MAP.get(change_class, "FULL_LIFECYCLE")


def check_authority_closure(action_source: str) -> bool:
    """Return True if action_source is a valid Authority origin (§62l AuthorityClosureInvariant r39).
    Returns False if source is a non-Authority input that cannot create Authority.
    """
    return action_source not in _NON_AUTHORITY_SOURCES
