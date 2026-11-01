"""Value trajectory and acceleration tracking.

The system's ultimate purpose is to produce increasingly more value,
increasingly faster, and increasingly better — not just to execute changes.

This module tracks:
  - Value produced per operation (net positive metric movement)
  - Value rate: value per minute of elapsed execution time
  - Velocity: rolling average value rate over recent operations
  - Acceleration: is the velocity itself increasing or decreasing?
  - Yield rate: what fraction of operations produce positive value

When the system is decelerating, it surfaces that signal so the lifecycle
can self-correct — e.g. by re-prioritizing higher-yield scopes, shortening
task granularity, or triggering a strategic reassessment.

Spec alignment: continuous measurable follow-up (§60), proportionate
resource allocation, evidence-driven proportionality.
"""
from __future__ import annotations

import statistics
import math
from datetime import datetime, timezone
from typing import Any

# Minimum checkpoints before acceleration can be meaningfully computed.
_MIN_CHECKPOINTS_FOR_ACCELERATION = 4

# How many checkpoints to keep (rolling window).
_MAX_CHECKPOINTS = 100

# Rolling window sizes for velocity computation.
_RECENT_WINDOW = 5
_BASELINE_WINDOW = 5

# Deceleration threshold: if velocity drops by this fraction relative to
# its peak, surface a deceleration alert.
_DECELERATION_ALERT_RATIO = 0.5


def record_checkpoint(
    state: dict[str, Any],
    operation: dict[str, Any],
    before_metrics: dict[str, float],
    after_metrics: dict[str, float],
    elapsed_seconds: float,
    directions: dict[str, str] | None = None,
    weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Record a value-producing checkpoint and refresh the trajectory.

    Call this immediately after an operation is accepted with its
    before/after metrics and how long the execution took.
    """
    trajectory = state.setdefault("value_trajectory", {
        "checkpoints": [],
        "acceleration": None,
        "established_at": _now(),
        "cumulative_value": 0.0,
        "peak_velocity": 0.0,
    })

    # Structural counts are implementation diagnostics, never user-value credit.
    proxy_metrics = {"normative_rules", "behavioral_tests", "unresolved_markers"}
    if directions is None:
        directions = {name: measure.get("direction", "nondecreasing")
                      for profile in state.get("progress_profiles", [])
                      for name, measure in profile.get("measures", {}).items()}
    deltas = []
    for name, after_val in after_metrics.items():
        if name in proxy_metrics or name not in before_metrics:
            continue
        direction = directions.get(name)
        if direction not in {"nondecreasing", "nonincreasing"}:
            continue  # Unknown direction cannot establish improvement.
        before_val = float(before_metrics[name])
        after_val = float(after_val)
        weight = float((weights or {}).get(name, 1.0))
        if not all(math.isfinite(v) for v in (before_val, after_val, weight)) or weight < 0:
            raise ValueError("value measurements and nonnegative weights must be finite")
        delta = (after_val - before_val) * (1 if direction == "nondecreasing" else -1)
        deltas.append(delta * weight)
    improved = sum(delta > 0 for delta in deltas)
    regressed = sum(delta < 0 for delta in deltas)
    net_value_delta = sum(deltas)

    # Value rate: value per minute of real elapsed time.
    cost_minutes = max(0.001, elapsed_seconds / 60.0)
    value_rate = net_value_delta / cost_minutes

    checkpoint = {
        "operation_id": operation.get("id"),
        "evidence_kind": operation.get("outcome", {}).get("evidence_kind", "UNVERIFIED"),
        "attribution": operation.get("outcome", {}).get("attribution", "UNATTRIBUTED"),
        "at": _now(),
        "elapsed_seconds": round(elapsed_seconds, 1),
        "net_value_delta": net_value_delta,
        "improved_metrics": improved,
        "regressed_metrics": regressed,
        "value_rate": round(value_rate, 4),
        "scope": operation.get("scope", "documentation"),
        "objective_title": operation.get("decision"),
    }

    checkpoints = trajectory["checkpoints"]
    checkpoints.append(checkpoint)
    trajectory["checkpoints"] = checkpoints[-_MAX_CHECKPOINTS:]

    # Update cumulative value.
    trajectory["cumulative_value"] = round(
        float(trajectory.get("cumulative_value", 0.0)) + net_value_delta, 2
    )

    # Recompute acceleration.
    accel = compute_acceleration(trajectory["checkpoints"])
    trajectory["acceleration"] = accel

    # Track peak velocity.
    current_vel = accel.get("current_velocity", 0.0)
    if isinstance(current_vel, (int, float)):
        trajectory["peak_velocity"] = max(
            float(trajectory.get("peak_velocity", 0.0)), current_vel
        )

    trajectory["updated_at"] = _now()
    return checkpoint


def compute_acceleration(checkpoints: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute acceleration metrics from the checkpoint history.

    Returns a dict with:
      status, direction, current_velocity, baseline_velocity,
      trend_slope, value_amplification, cumulative_value,
      yield_rate, sample_size, alerts, note.
    """
    if not checkpoints:
        return {
            "status": "no_data",
            "checkpoints_needed": _MIN_CHECKPOINTS_FOR_ACCELERATION,
        }

    rates = [float(c.get("value_rate", 0.0)) for c in checkpoints]
    net_deltas = [float(c.get("net_value_delta", 0.0)) for c in checkpoints]

    if len(rates) < 2:
        return {
            "status": "establishing_baseline",
            "current_rate": rates[0] if rates else 0.0,
            "checkpoints_needed": max(0, _MIN_CHECKPOINTS_FOR_ACCELERATION - len(rates)),
        }

    # Rolling velocity windows.
    recent = rates[-min(_RECENT_WINDOW, len(rates)):]
    early = rates[:min(_BASELINE_WINDOW, len(rates))]
    current_velocity = statistics.mean(recent)
    baseline_velocity = statistics.mean(early)

    # Trend: slope from first-half mean to second-half mean.
    mid = max(1, len(rates) // 2)
    first_half_mean = statistics.mean(rates[:mid])
    second_half_mean = statistics.mean(rates[mid:]) if len(rates) > mid else rates[-1]
    trend_slope = second_half_mean - first_half_mean

    # Amplification: how much faster is the system now vs when it started?
    if abs(baseline_velocity) < 1e-9:
        amplification: float | str = "unbounded" if current_velocity > 0 else 1.0
    else:
        amplification = round(current_velocity / baseline_velocity, 4)

    # Direction label.
    if abs(trend_slope) < 0.005:
        direction = "stable"
    elif trend_slope > 0:
        direction = "accelerating"
    else:
        direction = "decelerating"

    # Yield rate: fraction of operations that produced positive value.
    positive_ops = sum(1 for d in net_deltas if d > 0)
    yield_rate = round(positive_ops / len(net_deltas), 4) if net_deltas else 0.0

    # Net value includes losses.
    cumulative_value = round(sum(net_deltas), 2)

    # Alerts.
    alerts: list[str] = []
    if direction == "decelerating":
        if isinstance(amplification, float) and amplification < _DECELERATION_ALERT_RATIO:
            alerts.append(
                f"VELOCITY_BELOW_HALF_BASELINE: current_velocity={current_velocity:.4f} "
                f"is <50% of baseline={baseline_velocity:.4f}; "
                "consider scope reassessment or task granularity reduction"
            )
        else:
            alerts.append(
                "VELOCITY_DECLINING: value production rate is decreasing; "
                "monitor for continued decline"
            )
    if yield_rate < 0.5 and len(checkpoints) >= _MIN_CHECKPOINTS_FOR_ACCELERATION:
        alerts.append(
            f"LOW_YIELD_RATE: only {yield_rate:.0%} of operations produced positive value; "
            "consider reprioritizing objectives toward higher-confidence improvements"
        )

    # Per-scope velocity breakdown.
    scope_rates: dict[str, list[float]] = {}
    for c in checkpoints:
        scope_rates.setdefault(str(c.get("scope", "unknown")), []).append(
            float(c.get("value_rate", 0.0))
        )
    scope_velocity = {
        scope: round(statistics.mean(r), 4)
        for scope, r in scope_rates.items()
        if r
    }

    return {
        "status": "computed",
        "direction": direction,
        "current_velocity": round(current_velocity, 4),
        "baseline_velocity": round(baseline_velocity, 4),
        "trend_slope": round(trend_slope, 6),
        "value_amplification": amplification,
        "cumulative_value": cumulative_value,
        "yield_rate": yield_rate,
        "sample_size": len(rates),
        "scope_velocity": scope_velocity,
        "alerts": alerts,
        "note": _note(direction, amplification, yield_rate),
    }


def self_correction_needed(state: dict[str, Any]) -> dict[str, Any] | None:
    """Return a self-correction prescription if the system is decelerating.

    Called by the lifecycle to decide whether to inject a strategic
    reassessment objective. Returns None when no correction is warranted.
    """
    trajectory = state.get("value_trajectory", {})
    accel = trajectory.get("acceleration", {})
    if not accel or accel.get("status") != "computed":
        return None
    if accel.get("direction") != "decelerating":
        return None
    if accel.get("sample_size", 0) < _MIN_CHECKPOINTS_FOR_ACCELERATION:
        return None

    amp = accel.get("value_amplification", 1.0)
    yield_rate = float(accel.get("yield_rate", 1.0))

    # Determine severity.
    severe = isinstance(amp, float) and amp < _DECELERATION_ALERT_RATIO
    low_yield = yield_rate < 0.4

    prescription = {
        "trigger": "value_deceleration",
        "direction": "decelerating",
        "value_amplification": amp,
        "yield_rate": yield_rate,
        "severe": severe,
        "low_yield": low_yield,
        "suggested_action": (
            "Inject strategic reassessment objective: review scope priorities, "
            "task granularity, and objective quality to recover value production rate"
            if severe or low_yield
            else "Monitor for continued deceleration before intervening"
        ),
        "self_correct_now": severe or low_yield,
    }
    return prescription


def _note(direction: str, amplification: float | str, yield_rate: float) -> str:
    amp_str = f"{amplification:.2f}x" if isinstance(amplification, float) else str(amplification)
    if direction == "accelerating":
        return (
            f"System is producing value faster over time "
            f"(amplification={amp_str}, yield={yield_rate:.0%}). "
            "Positive trajectory — continue current strategy."
        )
    if direction == "decelerating":
        return (
            f"Value production rate is declining "
            f"(amplification={amp_str}, yield={yield_rate:.0%}). "
            "Consider scope reassessment or objective reprioritisation."
        )
    return (
        f"Value production rate is stable "
        f"(amplification={amp_str}, yield={yield_rate:.0%})."
    )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
