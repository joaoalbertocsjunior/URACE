"""Rule Ledger — unified governance model.

Three irreducible concepts: RULE, STATE, CHANGE.
Rules govern what should be. State describes what is. Changes record what happened.

Rule kinds by immutability level:
  Level 0 (immutable post-bootstrap):  PURPOSE
  Level 1 (durable, operator-mutable): DIRECTIVE, PERMISSION, PROHIBITION
  Level 2 (operational, lifecycle-mgd): OBJECTIVE, POLICY

Five relationship types (the minimal complete set):
  1. Rule --[derived_from]--> Rule       derivation chain
  2. Change --[governed_by]--> Rule[]    what governed a change
  3. Rule --[governed_changes]--> Change[]  inverse of #2
  4. Rule --[superseded_by]--> Rule      version evolution
  5. Rule --[conflicts_with]--> Rule     detected contradiction

All stored as ID references. Text resolved on demand. No duplication.
"""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from urace import primitives as _primitives

# ── Constants ────────────────────────────────────────────────────────────────

_KIND_LEVEL: dict[str, int] = {
    "PURPOSE":     0,
    "DIRECTIVE":   1,
    "PERMISSION":  1,
    "PROHIBITION": 1,
    "OBJECTIVE":   2,
    "POLICY":      2,
}
KINDS = frozenset(_KIND_LEVEL.keys())

EXPLICIT        = "EXPLICIT"
SYSTEM_INFERRED = "SYSTEM_INFERRED"

# Confidence thresholds
INFER_SURFACE  = 0.50   # surface to user in --inferred list
INFER_BLOCKING = 0.85   # advisory-blocking threshold (configurable via POLICY)

# Phrases that signal PROHIBITION intent in constraint statements
_PROHIBITION_SIGNALS = (
    "must not", "never", "prohibited", "forbidden", "not allowed",
    "cannot", "disallow", "restrict", "prevent", "block",
)
_PERMISSION_SIGNALS = (
    "may", "allowed", "permitted", "can", "authorized", "authorize",
    "allow", "enable",
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uid(prefix: str = "rul") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def _level(kind: str) -> int:
    return _KIND_LEVEL.get(kind, 2)


# ── Rule construction ────────────────────────────────────────────────────────

def make_rule(
    kind: str,
    statement: str,
    source: str,
    *,
    scope: list[str] | None = None,
    derivation: str = EXPLICIT,
    confidence: float = 1.0,
    derived_from: list[str] | None = None,
    expires_at: str | None = None,
    tags: list[str] | None = None,
    rule_id: str | None = None,
    **meta: Any,
) -> dict[str, Any]:
    """Create a new Rule record."""
    if kind not in KINDS:
        raise ValueError(f"Unknown rule kind '{kind}'; valid: {sorted(KINDS)}")
    _ts = _now()
    rule: dict[str, Any] = {
        "id":               rule_id or _uid(kind[:3].lower()),
        "kind":             kind,
        "statement":        str(statement).strip(),
        "scope":            scope or ["*"],
        "derivation":       derivation,
        "confidence":       round(float(confidence), 4),
        "source":           str(source),
        "derived_from":     list(derived_from or []),
        "superseded_by":    None,
        "active_since":     _ts,
        "active_until":     None,
        "updated_at":       _ts,
        "deleted_at":       None,
        "expires_at":       expires_at,
        "governed_changes": [],
        "tags":             list(tags or []),
        "version":          1,
    }
    rule.update(meta)
    return rule


def _infer_constraint_kind(statement: str) -> str:
    """Heuristically classify a constraint statement as PROHIBITION or PERMISSION."""
    lower = statement.lower()
    proh = sum(1 for s in _PROHIBITION_SIGNALS if s in lower)
    perm = sum(1 for s in _PERMISSION_SIGNALS  if s in lower)
    return "PROHIBITION" if proh >= perm else "PERMISSION"


# ── Ledger operations ────────────────────────────────────────────────────────

def new_ledger() -> dict[str, Any]:
    """Create an empty Rule Ledger."""
    return {
        "schema_version":  1,
        "rules":           [],
        "relationships":   [],
        "change_bindings": [],
        "established_at":  _now(),
        "updated_at":      _now(),
    }


def _record_relationship(
    ledger: dict[str, Any],
    from_id: str,
    to_id: str,
    rel_type: str,
    source: str = "",
) -> None:
    """Append a Relationship edge record. Deduplicates by (from_id, to_id, type)."""
    rels = ledger.setdefault("relationships", [])
    for existing in rels:
        if existing["from_id"] == from_id and existing["to_id"] == to_id and existing["type"] == rel_type:
            return
    rels.append({
        "from_id":     from_id,
        "to_id":       to_id,
        "type":        rel_type,
        "recorded_at": _now(),
        "source":      source,
    })


def _touch(ledger: dict[str, Any]) -> None:
    ledger["updated_at"] = _now()


def _touch_rule(rule: dict[str, Any]) -> None:
    rule["updated_at"] = _now()


def add_rule(ledger: dict[str, Any], rule: dict[str, Any]) -> dict[str, Any]:
    """Add a rule to the ledger. Returns the rule."""
    ledger.setdefault("rules", []).append(rule)
    for parent_id in rule.get("derived_from", []):
        _record_relationship(ledger, rule["id"], parent_id, "derived_from", source=rule.get("source", ""))
    _touch(ledger)
    return rule


def get_rule(ledger: dict[str, Any], rule_id: str) -> dict[str, Any] | None:
    return next((r for r in ledger.get("rules", []) if r["id"] == rule_id), None)


def active_rules(
    ledger: dict[str, Any],
    kind: str | None = None,
    scope: str | None = None,
    include_inferred: bool = True,
    min_confidence: float = 0.0,
) -> list[dict[str, Any]]:
    """Return rules that are currently active (not superseded, not expired)."""
    now_ts = datetime.now(timezone.utc).isoformat()
    result = []
    for rule in ledger.get("rules", []):
        if rule.get("superseded_by"):
            continue
        if rule.get("active_until") and rule["active_until"] <= now_ts:
            continue
        if rule.get("expires_at") and rule["expires_at"] <= now_ts:
            continue
        if kind and rule["kind"] != kind:
            continue
        if scope and scope not in rule.get("scope", ["*"]) and "*" not in rule.get("scope", ["*"]):
            continue
        if not include_inferred and rule.get("derivation") == SYSTEM_INFERRED:
            continue
        if rule.get("confidence", 1.0) < min_confidence:
            continue
        result.append(rule)
    return result


def supersede_rule(
    ledger: dict[str, Any],
    old_id: str,
    new_rule: dict[str, Any],
) -> dict[str, Any]:
    """Mark old rule as superseded; add the new version. Returns new rule."""
    old = get_rule(ledger, old_id)
    if old is None:
        raise ValueError(f"Rule not found: {old_id}")
    old["superseded_by"] = new_rule["id"]
    old["active_until"] = _now()
    _touch_rule(old)
    new_rule["version"] = old.get("version", 1) + 1
    new_rule.setdefault("derived_from", [old_id])
    add_rule(ledger, new_rule)
    _record_relationship(ledger, old_id, new_rule["id"], "superseded_by", source="supersede_rule")
    _touch(ledger)
    return new_rule


def deactivate_rule(ledger: dict[str, Any], rule_id: str, reason: str = "") -> None:
    """Mark a rule as no longer active (without superseding). Sets deleted_at for soft-delete."""
    rule = get_rule(ledger, rule_id)
    if rule is None:
        raise ValueError(f"Rule not found: {rule_id}")
    _ts = _now()
    rule["active_until"] = _ts
    rule["deleted_at"] = _ts
    _touch_rule(rule)
    if reason:
        rule.setdefault("tags", []).append(f"deactivated:{reason}")
    _touch(ledger)


# ── Snapshot / integrity ─────────────────────────────────────────────────────

def snapshot_digest(ledger: dict[str, Any]) -> str:
    """SHA-256 of the active rule set (sorted by id). Cheap integrity check."""
    snapshot = sorted(
        ({"id": r["id"], "statement": r["statement"], "kind": r["kind"]}
         for r in active_rules(ledger, include_inferred=True)),
        key=lambda x: x["id"],
    )
    payload = json.dumps(snapshot, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(payload.encode()).hexdigest()
    # Self-check: assert the output is a valid DigestValue (§62d).
    _primitives.validate_digest_value(digest)
    return digest


# ── Derivation chain ─────────────────────────────────────────────────────────

def derivation_chain(
    ledger: dict[str, Any],
    rule_id: str,
    _visited: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Walk derived_from edges up to root PURPOSE. Returns list root-first."""
    if _visited is None:
        _visited = set()
    rule = get_rule(ledger, rule_id)
    if rule is None or rule_id in _visited:
        return []
    _visited.add(rule_id)
    chain: list[dict[str, Any]] = []
    for parent_id in rule.get("derived_from", []):
        chain.extend(derivation_chain(ledger, parent_id, _visited))
    chain.append(rule)
    return chain


# ── Conflict detection ───────────────────────────────────────────────────────

def detect_conflicts(ledger: dict[str, Any]) -> list[dict[str, Any]]:
    """Find pairs of active rules that contradict each other.

    Detects:
    - A PERMISSION and a PROHIBITION covering the same scope with opposite intent
    - A lower-level DIRECTIVE that contradicts a PURPOSE or higher DIRECTIVE
    """
    rules = active_rules(ledger)
    conflicts: list[dict[str, Any]] = []

    permissions   = [r for r in rules if r["kind"] == "PERMISSION"]
    prohibitions  = [r for r in rules if r["kind"] == "PROHIBITION"]

    for perm in permissions:
        for proh in prohibitions:
            perm_words = set(re.findall(r"\b\w{4,}\b", perm["statement"].lower()))
            proh_words = set(re.findall(r"\b\w{4,}\b", proh["statement"].lower()))
            overlap = perm_words & proh_words
            if len(overlap) >= 3:
                conflicts.append({
                    "rule_a": perm["id"],
                    "rule_b": proh["id"],
                    "kind":   "PERMISSION_PROHIBITION_OVERLAP",
                    "overlap_terms": sorted(overlap),
                    "detected_at": _now(),
                })

    # Level invariant: DIRECTIVE at level 1 should not contradict PURPOSE at level 0
    purposes   = [r for r in rules if r["kind"] == "PURPOSE"]
    directives = [r for r in rules if r["kind"] == "DIRECTIVE"]
    for purpose in purposes:
        purpose_words = set(re.findall(r"\b\w{4,}\b", purpose["statement"].lower()))
        for directive in directives:
            dir_words = set(re.findall(r"\b\w{4,}\b", directive["statement"].lower()))
            # Heuristic: directive explicitly negates purpose keywords
            negation_words = {"not", "never", "avoid", "remove", "abandon", "drop"}
            dir_full = directive["statement"].lower()
            has_negation = any(neg in dir_full for neg in negation_words)
            if has_negation and len(purpose_words & dir_words) >= 2:
                conflicts.append({
                    "rule_a":     purpose["id"],
                    "rule_b":     directive["id"],
                    "kind":       "DIRECTIVE_CONTRADICTS_PURPOSE",
                    "detected_at": _now(),
                })

    return conflicts


# ── Change binding ───────────────────────────────────────────────────────────

def bind_change(
    ledger: dict[str, Any],
    change_id: str,
    operation_scope: str = "*",
    *,
    kind: str = "ACCEPTED",
    description: str = "",
    state_before_digest: str | None = None,
    state_after_digest: str | None = None,
    delta_to_rules: list[str] | None = None,
    executor: dict[str, Any] | None = None,
    validation: dict[str, Any] | None = None,
    value_delta: float = 0.0,
) -> dict[str, Any]:
    """Bind a change to the currently active rules per the Change Schema. Returns binding record."""
    governed = [
        r["id"] for r in active_rules(ledger, scope=operation_scope, include_inferred=False)
    ]
    digest = snapshot_digest(ledger)
    for rule in ledger.get("rules", []):
        if rule["id"] in governed:
            rule.setdefault("governed_changes", [])
            if change_id not in rule["governed_changes"]:
                rule["governed_changes"].append(change_id)
                _touch_rule(rule)
    binding = {
        "id":                   change_id,
        "kind":                 kind,
        "at":                   _now(),
        "description":          description,
        "scope":                operation_scope,
        "governed_by":          governed,
        "rule_snapshot_digest": digest,
        "state_before_digest":  state_before_digest,
        "state_after_digest":   state_after_digest if kind != "REJECTED" else None,
        "delta_to_rules":       delta_to_rules or [],
        "executor":             executor or {},
        "validation":           validation or {"verdict": kind, "checks": []},
        "value_delta":          value_delta,
    }
    ledger.setdefault("change_bindings", [])
    ledger["change_bindings"].append(binding)
    ledger["change_bindings"] = ledger["change_bindings"][-500:]
    _touch(ledger)
    return binding


def rules_for_change(ledger: dict[str, Any], change_id: str) -> list[dict[str, Any]]:
    """Return the rules that governed a specific change."""
    binding = next(
        (b for b in reversed(ledger.get("change_bindings", [])) if b["id"] == change_id),
        None,
    )
    if binding is None:
        return []
    return [r for r in ledger.get("rules", []) if r["id"] in binding["governed_by"]]


def changes_for_rule(ledger: dict[str, Any], rule_id: str) -> list[str]:
    """Return change IDs governed by a specific rule."""
    rule = get_rule(ledger, rule_id)
    return list(rule.get("governed_changes", [])) if rule else []


# ── System inference ─────────────────────────────────────────────────────────

def infer_rules(
    ledger: dict[str, Any],
    state: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Generate SYSTEM_INFERRED rules from existing explicit rules.

    Heuristics:
    1. PURPOSE mentions specific domain → infer DIRECTIVE on scope focus
    2. PURPOSE contains "not" / "never" phrases → infer PROHIBITION
    3. DIRECTIVE + repeated Change pattern → infer operational POLICY suggestion
    """
    inferred: list[dict[str, Any]] = []
    existing_statements = {
        r["statement"].lower() for r in ledger.get("rules", [])
    }
    purposes = active_rules(ledger, kind="PURPOSE")
    purpose_ids = [p["id"] for p in purposes]

    for purpose in purposes:
        text = purpose["statement"]
        lower = text.lower()

        # Infer PROHIBITION from "must not" / "never" phrases in purpose
        for phrase in ("must not", "never", "do not", "prohibited"):
            idx = lower.find(phrase)
            if idx != -1:
                # Extract the clause after the phrase (up to period or end)
                rest = text[idx:idx + 120].split(".")[0].strip()
                stmt = f"Prohibited (derived from purpose): {rest}"
                if stmt.lower() not in existing_statements:
                    inferred.append(make_rule(
                        kind="PROHIBITION",
                        statement=stmt,
                        source="system-inference:purpose-negation",
                        derivation=SYSTEM_INFERRED,
                        confidence=0.70,
                        derived_from=purpose_ids,
                        tags=["inferred", "purpose-derived"],
                    ))
                    existing_statements.add(stmt.lower())
                    break

    return inferred


def apply_inferred(
    ledger: dict[str, Any],
    inferred: list[dict[str, Any]],
    min_confidence: float = INFER_SURFACE,
) -> int:
    """Add inferred rules that meet the confidence floor and aren't duplicates."""
    existing_statements = {
        r["statement"].lower() for r in ledger.get("rules", [])
    }
    added = 0
    for rule in inferred:
        if rule.get("confidence", 0.0) < min_confidence:
            continue
        if rule["statement"].lower() in existing_statements:
            continue
        add_rule(ledger, rule)
        existing_statements.add(rule["statement"].lower())
        added += 1
    return added


# ── Bootstrap seeding ────────────────────────────────────────────────────────

def seed_from_config(config: dict[str, Any]) -> dict[str, Any]:
    """Build initial Rule Ledger from bootstrap config.

    Called once at `urace init`. After this, the ledger is the source of
    truth; config fields become read-only bootstrap inputs.
    """
    ledger = new_ledger()
    intent      = config.get("intent", {})
    authority   = config.get("authority", {})

    # PURPOSE ─────────────────────────────────────────────────────────────────
    purpose_text = str(intent.get("purpose", "")).strip()
    purpose_id: str | None = None
    if purpose_text:
        purpose_rule = make_rule(
            kind="PURPOSE",
            statement=purpose_text,
            source="bootstrap:intent.purpose",
            tags=["bootstrap"],
        )
        add_rule(ledger, purpose_rule)
        purpose_id = purpose_rule["id"]

    # PROHIBITION — intent.retained (retained = protected from autonomous change)
    for retained in intent.get("retained", []):
        add_rule(ledger, make_rule(
            kind="PROHIBITION",
            statement=f"Retained — not autonomously mutable: {retained}",
            source="bootstrap:intent.retained",
            derived_from=[purpose_id] if purpose_id else [],
            tags=["retained", "bootstrap"],
        ))

    # PERMISSION — authority.delegated
    for delegated in authority.get("delegated", []):
        add_rule(ledger, make_rule(
            kind="PERMISSION",
            statement=f"Delegated — autonomously authorized: {delegated}",
            source="bootstrap:authority.delegated",
            tags=["delegated", "bootstrap"],
        ))

    # PROHIBITION — authority.reserved
    for reserved in authority.get("reserved", []):
        add_rule(ledger, make_rule(
            kind="PROHIBITION",
            statement=f"Reserved — requires authoritative decision: {reserved}",
            source="bootstrap:authority.reserved",
            tags=["reserved", "bootstrap"],
        ))

    # PROHIBITION — config.constraints
    for constraint in config.get("constraints", []):
        add_rule(ledger, make_rule(
            kind="PROHIBITION",
            statement=str(constraint),
            source="bootstrap:constraints",
            tags=["constraint", "bootstrap"],
        ))

    # POLICY — self_evolution_policy
    policy = config.get("self_evolution_policy", {})
    mode = policy.get("mode", "NECESSARY_ONLY")
    add_rule(ledger, make_rule(
        kind="POLICY",
        statement=f"self-evolution: {mode}",
        source=policy.get("source", "bootstrap"),
        scope=["runtime", "rebootstrap"],
        tags=["self-evolution", "policy", "bootstrap"],
        _policy_key="self_evolution",
        _policy_value=mode,
    ))

    # POLICY — external_metrics
    ext = config.get("external_metrics", {})
    ext_mode = ext.get("mode", "DISABLED")
    add_rule(ledger, make_rule(
        kind="POLICY",
        statement=f"external-metrics: {ext_mode}",
        source=ext.get("source", "bootstrap"),
        tags=["external-metrics", "policy", "bootstrap"],
        _policy_key="external_metrics",
        _policy_value=ext_mode,
    ))

    return ledger


# ── Executor context ─────────────────────────────────────────────────────────

def executor_context(
    ledger: dict[str, Any],
    objective_id: str | None,
    scope: str = "documentation",
) -> dict[str, Any]:
    """Build a token-efficient rule subset for an executor dispatch.

    Returns only rules relevant to the current objective and scope.
    All other rules are referenced by ID only.
    """
    purposes     = active_rules(ledger, kind="PURPOSE",     scope=scope, include_inferred=False)
    directives   = active_rules(ledger, kind="DIRECTIVE",   scope=scope, include_inferred=False)
    prohibitions = active_rules(ledger, kind="PROHIBITION", scope=scope, include_inferred=False)
    permissions  = active_rules(ledger, kind="PERMISSION",  scope=scope, include_inferred=False)
    objective    = get_rule(ledger, objective_id) if objective_id else None

    def _compact(rule: dict[str, Any]) -> dict[str, Any]:
        return {"id": rule["id"], "statement": rule["statement"], "kind": rule["kind"]}

    return {
        "purposes":     [_compact(r) for r in purposes],
        "directives":   [_compact(r) for r in directives[:5]],   # top 5
        "prohibitions": [_compact(r) for r in prohibitions[:10]], # top 10
        "permissions":  [_compact(r) for r in permissions[:5]],
        "objective":    _compact(objective) if objective else None,
        "rule_snapshot_digest": snapshot_digest(ledger),
        "scope": scope,
    }


# ── Inspection helpers ───────────────────────────────────────────────────────

def format_rule_compact(rule: dict[str, Any]) -> str:
    conf = f" [{rule['confidence']:.0%}]" if rule.get("derivation") == SYSTEM_INFERRED else ""
    tag  = f" ({', '.join(rule['tags'][:2])})" if rule.get("tags") else ""
    return f"{rule['id']}  [{rule['kind']}]{conf}  {rule['statement'][:80]}{tag}"


def format_rule_full(rule: dict[str, Any], ledger: dict[str, Any] | None = None) -> str:
    lines = [
        f"ID:          {rule['id']}",
        f"Kind:        {rule['kind']} (level {_level(rule['kind'])})",
        f"Statement:   {rule['statement']}",
        f"Derivation:  {rule['derivation']}" + (f"  confidence={rule['confidence']:.0%}" if rule.get("derivation") == SYSTEM_INFERRED else ""),
        f"Source:      {rule['source']}",
        f"Scope:       {', '.join(rule.get('scope', ['*']))}",
        f"Active:      {rule['active_since']}" + (f" → {rule['active_until']}" if rule.get("active_until") else " → now"),
    ]
    if rule.get("derived_from"):
        lines.append(f"Derived from: {', '.join(rule['derived_from'])}")
    if rule.get("superseded_by"):
        lines.append(f"Superseded by: {rule['superseded_by']}")
    if rule.get("governed_changes"):
        lines.append(f"Governed changes: {len(rule['governed_changes'])} ({', '.join(rule['governed_changes'][-5:])}{'...' if len(rule['governed_changes']) > 5 else ''})")
    if rule.get("tags"):
        lines.append(f"Tags:        {', '.join(rule['tags'])}")
    if ledger and rule.get("derived_from"):
        chain = derivation_chain(ledger, rule["id"])
        chain_ids = " → ".join(r["id"] for r in chain)
        lines.append(f"Chain:       {chain_ids}")
    return "\n".join(lines)
