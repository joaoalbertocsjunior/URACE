"""Independent validation gate — separates Executor result from Product acceptance.

Spec §54, §60: Executor result MUST be treated as an Observation until independently
validated. URACE MUST NOT accept solely because the Executor reports completion.
When validation capability is temporarily unavailable, the Observation MUST be
preserved as pending-validation, not automatically accepted by elapsed time.

This module applies a set of independent checks after a change is applied but
before it is accepted. If any check fails, the caller is expected to roll back.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import math
from typing import Any

from urace import primitives as _primitives


VALIDATED = "VALIDATED"
REJECTED = "REJECTED"
PENDING_CAPABILITY = "PENDING_CAPABILITY"  # validation cannot run right now



def candidate_file_errors(root: Path, scope: str, files: list[str], config: dict[str, Any]) -> list[str]:
    """Check the operation's own allowlist before any candidate is written."""
    allowed = set(config.get("executor", {}).get("allowed_files_by_scope", {}).get(scope, []))
    errors = []
    if not files:
        errors.append("operation has no changed files")
    for relative in files:
        path = root / relative
        if relative not in allowed:
            errors.append(f"file outside authorized {scope} scope: {relative}")
        if Path(relative).is_absolute() or not path.resolve().is_relative_to(root.resolve()):
            errors.append(f"file escapes product root: {relative}")
        elif path.is_symlink():
            errors.append(f"candidate file is a symlink: {relative}")
    return errors


def validate_operation(
    root: Path,
    operation: dict[str, Any],
    before_metrics: dict[str, float],
    after_metrics: dict[str, float],
    config: dict[str, Any],
    state: dict[str, Any],
) -> dict[str, Any]:
    """Apply independent validation checks after a change is applied.

    Returns {verdict, checks, fails, basis, validated_at}.
    Verdict REJECTED means the caller MUST roll back.
    Verdict PENDING_CAPABILITY means validation infra is unavailable; the
    operation should be preserved as a pending-validation observation, not accepted.
    """
    checks: list[dict[str, Any]] = []

    # --- 1. Metrics guardrail (independent re-evaluation) ---
    directions: dict[str, str] = {}
    for profile in state.get("progress_profiles", []):
        for name, measure in profile.get("measures", {}).items():
            directions[name] = measure.get("direction", "nondecreasing")

    if set(before_metrics) != set(after_metrics):
        checks.append({'check':'measurement_comparability','result':'FAIL',
                       'detail':'Before and after measurements must cover the same metrics; changed definitions need a new baseline'})
    for name in dict.fromkeys([*before_metrics,*after_metrics]):
        before_val,after_val = before_metrics.get(name),after_metrics.get(name)
        finite=lambda value: type(value) is int or (type(value) is float and math.isfinite(value))
        if not finite(before_val) or not finite(after_val):
            checks.append({'check':f'metric_guardrail:{name}','result':'FAIL',
                           'detail':'Both paired measurements must be finite numbers, excluding booleans'})
            continue
        direction = directions.get(name, "nondecreasing")
        if direction not in {'nondecreasing','nonincreasing'}:
            checks.append({'check':f'metric_guardrail:{name}','result':'FAIL','detail':'Unknown metric direction'})
            continue
        if direction == "nondecreasing" and after_val < before_val:
            checks.append({
                "check": f"metric_guardrail:{name}",
                "result": "FAIL",
                "detail": f"{name} regressed {before_val} → {after_val} (direction={direction})",
            })
        elif direction == "nonincreasing" and after_val > before_val:
            checks.append({
                "check": f"metric_guardrail:{name}",
                "result": "FAIL",
                "detail": f"{name} increased {before_val} → {after_val} (direction={direction})",
            })
        else:
            checks.append({
                "check": f"metric_guardrail:{name}",
                "result": "PASS",
                "detail": f"{name}: {before_val} → {after_val}",
            })

    # --- 2. Changed files must still exist ---
    changed_files = operation.get("changed_files", [])
    for relative in changed_files:
        path = root / relative
        if not path.exists():
            checks.append({
                "check": f"file_present:{relative}",
                "result": "FAIL",
                "detail": f"{relative} is absent after application",
            })
        else:
            checks.append({
                "check": f"file_present:{relative}",
                "result": "PASS",
                "detail": f"{relative} present",
            })

    # --- 3. Check this scope, never the union of other scopes. ---
    file_errors = candidate_file_errors(root, str(operation.get("scope", "")), changed_files, config)
    checks.append({"check": "file_authorization", "result": "FAIL" if file_errors else "PASS",
                   "detail": "; ".join(file_errors) or "All changed files within the operation scope"})
    if not before_metrics or not after_metrics:
        checks.append({"check": "measurement_available", "result": "FAIL",
                       "detail": "Independent before and after implementation measurements are required"})

    # --- 4. Operation scope must be a known, declared scope ---
    known_scopes = {"implementation", "documentation", "metrics", "runtime", "rebootstrap"}
    op_scope = str(operation.get("scope", ""))
    if op_scope not in known_scopes:
        checks.append({
            "check": "scope_declared",
            "result": "FAIL",
            "detail": f"Operation scope '{op_scope}' is not a known scope",
        })
    else:
        checks.append({
            "check": "scope_declared",
            "result": "PASS",
            "detail": f"Scope '{op_scope}' is declared",
        })

    # --- 5. Authority basis must be present ---
    if not operation.get("authority_basis"):
        checks.append({
            "check": "authority_basis_present",
            "result": "FAIL",
            "detail": "Operation has no authority_basis; acceptance is not attributable",
        })
    else:
        checks.append({
            "check": "authority_basis_present",
            "result": "PASS",
            "detail": f"Authority basis: {operation.get('authority_basis')}",
        })

    # --- 6. Paired invariant: lifecycle_state ↔ status_transitions ---
    transitions = state.get("status_transitions", [])
    lifecycle = state.get("lifecycle_state")
    if transitions and lifecycle:
        latest = transitions[-1]
        recorded_status = latest.get("to", latest.get("status"))
        if recorded_status != lifecycle:
            checks.append({
                "check": "paired_invariant:lifecycle_state",
                "result": "FAIL",
                "detail": (
                    f"lifecycle_state={lifecycle!r} does not match "
                    f"latest transition destination={recorded_status!r}"
                ),
            })
        else:
            checks.append({
                "check": "paired_invariant:lifecycle_state",
                "result": "PASS",
                "detail": f"lifecycle_state={lifecycle!r} consistent with latest transition",
            })

    fails = [c for c in checks if c["result"] == "FAIL"]
    verdict = REJECTED if fails else VALIDATED

    # Self-check each check record against the ValidationCheck schema (§62d).
    for chk in checks:
        _primitives.validate_validation_check(chk)

    result = {
        "verdict": verdict,
        "checks": checks,
        "fails": fails,
        "basis": (
            "independent validation gate: metrics guardrail, file presence, "
            "file authorization, scope declaration, authority attribution, "
            "paired invariant lifecycle_state"
        ),
        "validated_at": datetime.now(timezone.utc).isoformat(),
        "meaning": "implementation checks only; user outcome requires separate observation",
    }
    # Self-check the assembled result record (§62d).
    _primitives.validate_validation_result(result)
    return result


def pending_validation_record(
    operation: dict[str, Any],
    reason: str,
) -> dict[str, Any]:
    """Build a pending-validation record for when validation capability is unavailable."""
    from ._common import identifier
    return {
        "id": identifier("pv"),
        "operation_id": operation.get("id"),
        "operation_scope": operation.get("scope"),
        "queued_at": datetime.now(timezone.utc).isoformat(),
        "reason": reason,
        "status": "PENDING_CAPABILITY",
        "note": (
            "Validation capability was temporarily unavailable. "
            "This observation MUST be validated before further work proceeds."
        ),
    }
