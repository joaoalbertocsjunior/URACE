"""Controller-owned, lifecycle-wide dynamic attention priorities."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _age_days(value: str | None) -> float:
    if not value:
        return 30.0
    try:
        return max(0.0, (datetime.now(timezone.utc) - datetime.fromisoformat(value)).total_seconds() / 86400)
    except ValueError:
        return 30.0


def derive(root: Path, config: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    settings = config.get("scope_priority", {})
    definitions = settings.get("scopes", {})
    previous_system = state.get("scope_priority_system", {})
    previous_records = previous_system.get("scopes", {})
    maximum_step = max(0.0, float(settings.get("max_weight_step_per_revision", 0.25)))
    records: dict[str, Any] = {}
    accepted = [item for item in state.get("operations", []) if item.get("status") == "ACCEPTED"]
    for name, definition in definitions.items():
        artifacts = set(definition.get("artifacts", []))
        related = [item for item in state.get("objectives", []) if item.get("status") in {"planned", "active", "needs_reassessment", "policy_blocked"} and item.get("priority_scope") == name]
        last = max((item.get("accepted_at") for item in accepted if artifacts & set(item.get("changed_files", []))), default=None)
        unresolved = 0
        for relative in artifacts:
            path = root / relative
            if path.is_file() and path.suffix.lower() in {".md", ".txt", ".rst"} and path.stat().st_size <= 524288:
                unresolved += len(re.findall(r"\b(?:TODO|TBD|FIXME)\b", path.read_text(encoding="utf-8"), re.IGNORECASE))
        backlog = len(related)
        urgency = max((float(item.get("urgency", 0.5)) for item in related), default=0.0)
        risk = max((float(item.get("risk", 0.5)) for item in related), default=0.0)
        age = min(30.0, _age_days(last))
        regressions = sum(int(item.get("observed_metric_effect", {}).get("regressed", 0)) for item in accepted[-20:] if item.get("priority_scope") == name)
        target = float(definition.get("base_weight", 1.0)) + min(0.8, backlog * 0.2) + min(0.4, unresolved * 0.1) + min(0.5, age / 60) + min(0.3, urgency * 0.3) + min(0.3, risk * 0.2) + min(0.4, regressions * 0.1)
        target = min(float(definition.get("max_weight", 3.0)), max(float(definition.get("min_weight", 0.5)), target))
        prior = previous_records.get(name, {}).get("raw_weight")
        raw = target if prior is None else min(float(prior) + maximum_step, max(float(prior) - maximum_step, target))
        records[name] = {
            "label": definition.get("label", name), "raw_weight": round(raw, 4),
            "target_weight": round(target, 4), "previous_weight": prior,
            "change_limited": prior is not None and abs(float(raw) - target) > 1e-9,
            "base_weight": float(definition.get("base_weight", 1.0)),
            "min_weight": float(definition.get("min_weight", 0.5)),
            "max_weight": float(definition.get("max_weight", 3.0)),
            "backlog": backlog,
            "unresolved_markers": unresolved, "days_since_accepted_change": round(age, 2),
            "maximum_backlog_urgency": urgency, "maximum_backlog_risk": risk,
            "recent_regressed_metrics": regressions, "artifacts": sorted(artifacts),
            "evidence": "controller state and current Product artifacts",
        }
    total = sum(item["raw_weight"] for item in records.values()) or 1.0
    mean = total / max(1, len(records))
    for record in records.values():
        record["normalized_weight"] = round(record["raw_weight"] / total, 4)
        record["ranking_multiplier"] = round(min(1.25, max(0.75, record["raw_weight"] / mean)), 4)
    computed_at = datetime.now(timezone.utc).isoformat()
    return {
        "version": settings.get("version", "dynamic-scope-priority-v1"),
        "revision": int(previous_system.get("revision", 0)) + 1,
        "computed_at": computed_at, "evidence_cutoff": computed_at,
        "max_weight_step_per_revision": maximum_step,
        "basis": "bounded backlog, urgency, unresolved debt and accepted-change recency",
        "meaning": "planning attention only; never Authority, guardrail relief, budget expansion, evaluation credit or selection",
        "scopes": records,
    }


def allocate(system: dict[str, Any], names: list[str], slots: int) -> dict[str, int]:
    """Largest-remainder allocation with one slot per scope when possible."""
    allocation = {name: 1 if slots >= len(names) else 0 for name in names}
    remaining = slots - sum(allocation.values())
    weights = {name: float(system["scopes"][name]["raw_weight"]) for name in names}
    total = sum(weights.values()) or 1.0
    shares = {name: remaining * weights[name] / total for name in names}
    for name in names:
        whole = int(shares[name]); allocation[name] += whole; remaining -= whole
    for name in sorted(names, key=lambda value: (shares[value] % 1, weights[value], value), reverse=True)[:remaining]:
        allocation[name] += 1
    return allocation


def infer_scope(config: dict[str, Any], execution_scope: str, changed_files: list[str] | None = None) -> str | None:
    candidates = []
    changed = set(changed_files or [])
    for name, definition in config.get("scope_priority", {}).get("scopes", {}).items():
        if execution_scope not in definition.get("execution_scopes", []):
            continue
        overlap = len(changed & set(definition.get("artifacts", [])))
        candidates.append((overlap, float(definition.get("base_weight", 1.0)), name))
    return max(candidates)[2] if candidates else None


def ranking_adjustment(objective: dict[str, Any], system: dict[str, Any] | None) -> float:
    record = (system or {}).get("scopes", {}).get(objective.get("priority_scope"), {})
    return 10.0 * (float(record.get("ranking_multiplier", 1.0)) - 1.0)
