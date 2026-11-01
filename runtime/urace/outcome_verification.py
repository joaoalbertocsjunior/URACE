"""Independent outcome follow-up; implementation acceptance is not user value.

Contracts come from authoritative configuration, are frozen before execution,
and read bounded JSON evidence outside every executor-writable file. No shell,
network access, or executor-generated validation instructions are supported.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import stat
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VERIFIED = {"OUTCOME_VERIFIED", "REAL_USER_VALUE_VERIFIED"}
_DIRECTORY_RELATIVE_OPEN = os.open in os.supports_dir_fd and hasattr(os, "O_NOFOLLOW") and hasattr(os, "O_DIRECTORY")


def _open_beneath(root: Path, relative: Path) -> int:
    """Bind traversal to the product directory without following symlink components."""
    if not _DIRECTORY_RELATIVE_OPEN or not relative.parts or ".." in relative.parts:
        raise ValueError("independent evidence needs a supported directory-relative, no-follow source")
    directory = os.open(root.resolve(), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for component in relative.parts[:-1]:
            child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            os.close(directory)
            directory = child
        return os.open(relative.parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
    finally:
        os.close(directory)


def _number(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("measurements must be finite numbers")
    return float(value)


def _time(value: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError("observation timestamp must be an ISO-8601 string")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("observation timestamps must include timezone")
    return result


def _count(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("sample counts must be nonnegative integers")
    return value


def _rate(record: dict[str, Any], prefix: str = "") -> tuple[float, int]:
    successes, trials = _count(record[prefix + "successes"]), _count(record[prefix + "trials"])
    if not trials or successes > trials:
        raise ValueError("sample requires 0 <= successes <= trials and trials > 0")
    return successes / trials, trials


def _interval(rate: float, trials: int) -> tuple[float, float]:
    # Wilson 95% interval for one prespecified binary outcome.
    z = 1.959963984540054
    denominator = 1 + z * z / trials
    center = (rate + z * z / (2 * trials)) / denominator
    half = z * math.sqrt(rate * (1 - rate) / trials + z * z / (4 * trials * trials)) / denominator
    return center - half, center + half


def _read(root: Path, measure: dict[str, Any], writable: list[str]) -> dict[str, Any]:
    relative = Path(measure["source"])
    path = root / relative
    if relative.is_absolute() or not path.resolve().is_relative_to(root.resolve()) or path.is_symlink():
        raise ValueError("outcome source must be a local file within the product root")
    expected = path.stat()
    if not stat.S_ISREG(expected.st_mode):
        raise ValueError("independent outcome source must be a regular file")
    resolved_writable = [(root / name).resolve() for name in writable]
    if path.resolve() in resolved_writable or any(
        candidate.exists() and path.samefile(candidate) for candidate in resolved_writable
    ):
        raise ValueError("independent outcome source must not be executor-writable")
    with os.fdopen(_open_beneath(root, relative), "rb") as handle:
        opened = os.fstat(handle.fileno())
        identity = (opened.st_dev, opened.st_ino)
        if identity != (expected.st_dev, expected.st_ino) or not stat.S_ISREG(opened.st_mode):
            raise ValueError("outcome source changed while being opened")
        for candidate in resolved_writable:
            try:
                writable_stat = candidate.stat()
            except FileNotFoundError:
                continue
            if identity == (writable_stat.st_dev, writable_stat.st_ino):
                raise ValueError("independent outcome source must not be executor-writable")
        raw = handle.read(1048577)
    if len(raw) > 1048576:
        raise ValueError("outcome evidence exceeds 1 MiB")
    result = json.loads(raw)
    if not isinstance(result, dict):
        raise ValueError("outcome evidence must be an object")
    return result


def capture(root: Path, config: dict[str, Any], objective: dict[str, Any]) -> dict[str, Any]:
    """Freeze the prespecified measurement and baseline before candidate execution."""
    key = objective.get("outcome_measure_id") or objective["id"]
    definitions = config.get("outcome_verification", {}).get("measures", {})
    measure = copy.deepcopy(definitions.get(key))
    if measure is not None and not isinstance(measure, dict):
        return {"measure_id": key, "measure": None, "reason": "Outcome measure must be an object"}
    snapshot: dict[str, Any] = {"measure_id": key, "measure": measure}
    if measure is None:
        snapshot["reason"] = "No authoritative outcome measure configured for this objective"
        return snapshot
    writable = sorted({name for files in config.get("executor", {}).get("allowed_files_by_scope", {}).values() for name in files} | set(config.get("product_files", [])))
    snapshot["writable"] = writable
    snapshot["contract_hash"] = hashlib.sha256(json.dumps(measure, sort_keys=True).encode()).hexdigest()
    try:
        if measure.get("evidence_kind") not in {"real_user", "engineering", "synthetic"}:
            raise ValueError("declare evidence_kind: real_user, engineering, or synthetic")
        if measure.get("direction") not in {"nondecreasing", "nonincreasing"}:
            raise ValueError("declare metric direction")
        if measure.get("independent") is not True:
            raise ValueError("outcome source must be explicitly designated independent")
        if not measure.get("experiment_id"):
            raise ValueError("declare the prespecified experiment_id")
        target = _number(measure["target"])
        if not 0 <= target <= 1 or _number(measure.get("min_delta", 0)) < 0:
            raise ValueError("target must be a proportion and min_delta nonnegative")
        payload = _read(root, measure, writable)
        baseline = copy.deepcopy(payload["baseline"])
        _rate(baseline)
        if not baseline.get("id") or _time(baseline["at"]) > datetime.now(timezone.utc):
            raise ValueError("baseline requires identity and a nonfuture timestamp")
        snapshot["baseline"] = baseline
        snapshot["prior_ids"] = [r["id"] for r in payload.get("observations", [])]
    except (OSError, ValueError, KeyError, TypeError) as error:
        snapshot["reason"] = f"Outcome baseline unavailable: {error}"
    return snapshot


def evaluate(root: Path, operation: dict[str, Any], *, at: datetime | None = None, writable: list[str] | None = None) -> dict[str, Any]:
    """Assess only fresh, operation-linked observations under the frozen contract."""
    at = at or datetime.now(timezone.utc)
    snapshot = operation.get("outcome_contract", {})
    measure = snapshot.get("measure")
    result: dict[str, Any] = {"status": "PENDING_OUTCOME", "evaluated_at": at.isoformat(),
                              "evidence_kind": (measure or {}).get("evidence_kind", "unknown"),
                              "attribution": "UNATTRIBUTED", "net_value_delta": 0.0,
                              "real_user_value_verified": False}
    if operation.get("status") != "ACCEPTED":
        result["reason"] = "Implementation has not been accepted"
        return result
    if not measure or "baseline" not in snapshot:
        result["reason"] = snapshot.get("reason", "No frozen independent baseline")
        return result
    try:
        if hashlib.sha256(json.dumps(measure, sort_keys=True).encode()).hexdigest() != snapshot["contract_hash"]:
            raise ValueError("frozen outcome contract changed")
        payload = _read(root, measure, sorted(set(snapshot["writable"]) | set(writable or [])))
        real = measure["evidence_kind"] == "real_user"
        minimum = max(100 if real else 1, _count(measure.get("min_samples", 100 if real else 1)))
        minimum_windows = max(3 if real else 1, _count(measure.get("min_windows", 3 if real else 1)))
        minimum_span = max(86400.0 if real else 0, _number(measure.get("min_window_seconds", 86400 if real else 0)))
        maximum_age = _number(measure.get("max_age_seconds", 86400))
        if maximum_age <= 0:
            raise ValueError("max_age_seconds must be positive")
        baseline, baseline_n = _rate(snapshot["baseline"])
        if baseline_n < minimum:
            result["reason"] = "Frozen baseline has insufficient samples"
            return result
        applied = _time(operation["applied_at"])
        records, ids = [], set(snapshot.get("prior_ids", []))
        if not isinstance(payload.get("observations", []), list):
            raise ValueError("observations must be a list")
        for record in payload.get("observations", []):
            if not isinstance(record, dict):
                raise ValueError("each observation must be an object")
            if record.get("operation_id") != operation["id"] or record.get("experiment_id") != measure["experiment_id"]:
                continue
            record_id = record["id"]
            if not isinstance(record_id, str) or not record_id:
                raise ValueError("observation identity is required")
            if record_id in ids:
                raise ValueError("replayed or duplicate observation identity")
            ids.add(record_id)
            start, end = _time(record["window_start"]), _time(record["at"])
            if start < applied or end < start or end > at:
                raise ValueError("observation windows must follow application and not be future-dated")
            rate, count = _rate(record)
            if count < minimum:
                continue
            control = None
            if real:
                control, control_n = _rate(record, "control_")
                if control_n < minimum:
                    continue
            records.append((start, end, rate, count, control, record))
        records.sort(key=lambda row: row[0])
        if not records:
            result["reason"] = "No new operation-linked observations with sufficient samples"
            return result
        if any(records[i][0] <= records[i - 1][1] for i in range(1, len(records))):
            raise ValueError("observation windows must not overlap")
        if (at - records[-1][1]).total_seconds() > maximum_age:
            result["reason"] = "Outcome evidence is stale; value cannot be reaffirmed"
            return result
        sign = 1 if measure["direction"] == "nondecreasing" else -1
        target, min_delta = _number(measure["target"]), _number(measure.get("min_delta", 0))
        deltas, trial_benefit, trial_cost = [], 0.0, 0.0
        for _, _, rate, count, control, record in records:
            delta = sign * (rate - baseline)
            for name, bounds in measure.get("guardrails", {}).items():
                value = _number(record["guardrails"][name])
                if ("min" in bounds and value < _number(bounds["min"])) or ("max" in bounds and value > _number(bounds["max"])):
                    result.update(status="REGRESSED", reason=f"Outcome guardrail violated: {name}")
                    return result
            if delta < 0:
                result.update(status="REGRESSED", reason="Measured outcome regressed against frozen baseline",
                              net_value_delta=delta, current=rate, baseline=baseline)
                return result
            if sign * (rate - target) < 0 or delta <= min_delta:
                result["status"] = "NOT_ACHIEVED"
                result["reason"] = "Prespecified target and minimum improvement not achieved"
                return result
            if real:
                treatment_interval = _interval(rate, count)
                control_interval = _interval(control, record["control_trials"])
                lower_benefit = (treatment_interval[0] - control_interval[1]) if sign == 1 else (control_interval[0] - treatment_interval[1])
                if lower_benefit <= min_delta:
                    result["reason"] = "Comparison does not establish improvement with conservative 95% bounds"
                    return result
                trial_benefit += lower_benefit * count
                trial_cost += _number(record["cost"])
                if _number(record["cost"]) < 0:
                    raise ValueError("observed costs must be nonnegative")
            deltas.append(delta)
        result.update(observation_ids=[r[5]["id"] for r in records], baseline=baseline,
                      current=records[-1][2], sample_size=sum(r[3] for r in records),
                      windows=len(records), net_value_delta=sum(deltas) / len(deltas))
        if len(records) < minimum_windows or (records[-1][1] - records[0][0]).total_seconds() < minimum_span:
            result.update(status="PENDING_OUTCOME", net_value_delta=0.0,
                          reason="More independent follow-up windows are required")
            return result
        if real:
            if measure.get("comparison_design") != "randomized_control":
                result.update(net_value_delta=0.0, reason="Real-user value requires a prespecified randomized control comparison")
                return result
            if measure.get("currency") != "USD":
                result.update(net_value_delta=0.0, reason="Outcome value and observed provider costs must share explicit USD units")
                return result
            value_per_success = _number(measure["value_per_success"])
            usage_cost = operation.get("usage", {}).get("reported_cost_usd")
            if value_per_success <= 0 or usage_cost is None:
                result.update(net_value_delta=0.0, reason="Positive value per success and observed execution cost are required")
                return result
            execution_cost = _number(usage_cost)
            if execution_cost < 0:
                raise ValueError("execution cost must be nonnegative")
            net_benefit = trial_benefit * value_per_success - trial_cost - execution_cost
            result.update(net_benefit=net_benefit, observed_cost=trial_cost + execution_cost,
                          attribution="RANDOMIZED_CONTROL_COMPARISON", confidence_basis="95% Wilson bounds per prespecified window")
            if net_benefit <= 0:
                result.update(status="NOT_ACHIEVED", net_value_delta=0.0, reason="Observed costs exceed conservative trial benefit")
                return result
            result.update(status="REAL_USER_VALUE_VERIFIED", real_user_value_verified=True,
                          reason="Positive measured net benefit across the prespecified trial windows; future value is not guaranteed")
        else:
            result.update(status="OUTCOME_VERIFIED", attribution="INDEPENDENT_MEASUREMENT",
                          reason="Engineering or synthetic outcome verified; this does not establish real-user value")
        return result
    except (OSError, ValueError, KeyError, TypeError) as error:
        result.update(status="PENDING_OUTCOME", reason=f"Outcome evidence unavailable or invalid: {error}", net_value_delta=0.0)
        return result


def refresh(root: Path, config: dict[str, Any], state: dict[str, Any]) -> None:
    """Re-evaluate accepted increments without replaying their implementation."""
    from . import value_trajectory
    from ._common import identifier, now
    by_id = {o.get("id"): o for o in state.get("objectives", [])}
    for operation in state.get("operations", []):
        if operation.get("status") != "ACCEPTED" or "outcome_contract" not in operation:
            continue
        writable = [name for files in config.get("executor", {}).get("allowed_files_by_scope", {}).values() for name in files]
        outcome = evaluate(root, operation, writable=writable)
        old = operation.get("outcome", {})
        feedback = [r for r in state.get("outcome_feedback_records", [])
                    if (r.get("target_kind") == "OBJECTIVE" and r.get("target_id") == operation.get("objective_reference"))
                    or (r.get("target_kind") == "OPERATION" and r.get("target_id") == operation["id"])]
        latest_feedback = max(feedback, key=lambda r: r.get("at", r.get("created_at", "")), default={})
        if latest_feedback.get("signal") == "NEGATIVE":
            outcome.update(status="CONTESTED", real_user_value_verified=False, net_value_delta=0.0,
                           reason="Latest outcome feedback is negative; retained for independent reassessment")
        operation["outcome"] = outcome
        objective = by_id.get(operation.get("objective_reference"))
        if objective is not None:
            objective["outcome_status"] = outcome["status"]
            objective["status"] = "completed" if outcome["status"] in VERIFIED else "awaiting_outcome"
            if objective["status"] == "completed":
                objective.setdefault("completed_at", now())
            else:
                objective.pop("completed_at", None)
        # Only verified observations earn credit. Withdraw it on stale evidence
        # or regression; repeated polling must never multiply value.
        credit = outcome.get("net_value_delta", 0.0) if outcome["status"] in VERIFIED or outcome["status"] == "REGRESSED" else 0.0
        prior = float(operation.get("outcome_value_credited", 0.0))
        if credit != prior:
            value_trajectory.record_checkpoint(state, operation, {"outcome": prior}, {"outcome": credit},
                                               operation.get("elapsed_seconds", 0.0), {"outcome": "nondecreasing"})
            operation["outcome_value_credited"] = credit
        comparable = lambda o: {k: v for k, v in o.items() if k != "evaluated_at"}
        if comparable(old) != comparable(outcome):
            state.setdefault("evidence", []).append({"id": identifier("evidence"), "at": now(),
                "kind": "independent-outcome-assessment", "operation": operation["id"], **outcome})


def main() -> int:
    """Read-only evidence review for an explicitly selected product and state."""
    import argparse
    parser = argparse.ArgumentParser(description="Review independent outcome evidence; never executes product changes")
    parser.add_argument("--root", type=Path, required=True, help="product root containing the configured evidence source")
    parser.add_argument("--state", type=Path, required=True, help="explicitly selected product state JSON")
    parser.add_argument("--config", type=Path, required=True, help="current authoritative configuration for source independence checks")
    args = parser.parse_args()
    try:
        state = json.loads(args.state.read_text(encoding="utf-8"))
        config = json.loads(args.config.read_text(encoding="utf-8"))
        writable = [name for files in config.get("executor", {}).get("allowed_files_by_scope", {}).values() for name in files]
        assessments = [{"operation_id": op["id"], **evaluate(args.root, op, writable=writable)}
                       for op in state.get("operations", []) if op.get("status") == "ACCEPTED"]
        verified = [r for r in assessments if r["real_user_value_verified"]]
        print(json.dumps({"operations": assessments, "real_user_value_verified_operations": len(verified),
                          "claim_scope": "prespecified observed trials only; source integrity and randomization require independent assurance",
                          "observed_trial_evidence_satisfies_contract": bool(verified)}, indent=2))
        return 0 if verified else 2
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({"error": str(error), "observed_trial_evidence_satisfies_contract": False}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
