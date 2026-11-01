"""§62j Pattern Catalog — AP24 Derivation Framework implementation.

Every AP0-AP24 entry declares standalone status, tier, requires list, and
capability descriptions so the derive command can resolve transitive deps and
generate DerivedSystemManifests without executor involvement.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

# Tier constants
FOUNDATIONAL = "FOUNDATIONAL"   # standalone=True or deps are themselves foundational
COMPOSITIONAL = "COMPOSITIONAL" # requires 1-2 other APs
INTEGRATED = "INTEGRATED"       # requires 3+ APs or deeply coupled cluster

# Adoption source constants
EXPLICIT = "EXPLICIT"
TRANSITIVE = "TRANSITIVE"

PATTERN_CATALOG: dict[str, dict[str, Any]] = {
    "AP0": {
        "name": "Citizen",
        "standalone": True,
        "tier": FOUNDATIONAL,
        "requires": [],
        "provides": [
            "named identity (stable id field, never recycled)",
            "schema conformance (every instance validates against a declared schema)",
            "lifecycle traceability (creation and mutation produce broadcast log entries)",
        ],
        "spec_section": "§62i AP0",
        "summary": "The fundamental unit of identity. Every named, schema-bearing, lifecycle-participating entity is a citizen.",
    },
    "AP1": {
        "name": "Canonical Scalar",
        "standalone": True,
        "tier": FOUNDATIONAL,
        "requires": [],
        "provides": [
            "typed leaf values with domain constraints",
            "reuse contract (define once, reference by name everywhere)",
            "machine-verifiable field validation",
        ],
        "spec_section": "§62i AP1",
        "summary": "The smallest indivisible value type. Canonical scalars are defined once with domain constraints and referenced by name in all schemas.",
    },
    "AP2": {
        "name": "Citizen Schema",
        "standalone": False,
        "tier": FOUNDATIONAL,
        "requires": ["AP0", "AP1"],
        "provides": [
            "named, versioned, fully-specified data structures",
            "minimality rule (no field bundles two independent normative claims)",
            "composition rule (fields reference canonical schema names, no inline sub-schemas)",
        ],
        "spec_section": "§62i AP2",
        "summary": "A named, versioned, fully-specified data structure. The primary reuse unit for structured data; every field resolves to AP1 or another AP2.",
    },
    "AP3": {
        "name": "Append-Only Log",
        "standalone": False,
        "tier": FOUNDATIONAL,
        "requires": ["AP2"],
        "provides": [
            "durable ordered sequence with monotone non-decreasing length",
            "ordering invariant (entries ordered by at-timestamp)",
            "identity invariant (entry ids are stable and never reused)",
            "compaction-safe retention (summaries replace but do not delete)",
        ],
        "spec_section": "§62i AP3",
        "summary": "A durable ordered sequence where records are only appended. The foundation for evidence logs, status transition logs, and all audit trails.",
    },
    "AP4": {
        "name": "Producer-Consumer Contract",
        "standalone": False,
        "tier": FOUNDATIONAL,
        "requires": ["AP0"],
        "provides": [
            "named, verifiable, bilateral obligations between components",
            "producer_must list (normative obligations on the writer)",
            "consumer_may_assume list (guaranteed properties for the reader)",
            "violation protocol (REJECT | QUARANTINE | ALERT)",
        ],
        "spec_section": "§62i AP4",
        "summary": "A named, verifiable, bilateral obligation between producer and consumer. Any two components that exchange data MUST document their exchange as a named ProducerConsumerContract.",
    },
    "AP5": {
        "name": "Idempotency Contract",
        "standalone": True,
        "tier": FOUNDATIONAL,
        "requires": [],
        "provides": [
            "retry safety (interrupted cycles can be safely retried)",
            "idempotency class declaration (PURE | AT_MOST_ONCE | AT_LEAST_ONCE | EXACTLY_ONCE)",
            "operation classification contract",
        ],
        "spec_section": "§62i AP5",
        "summary": "Applying an operation N times produces the same result as applying it once. Required for safe retry of interrupted cycles.",
    },
    "AP6": {
        "name": "Causal Provenance Chain",
        "standalone": False,
        "tier": COMPOSITIONAL,
        "requires": ["AP3", "AP4"],
        "provides": [
            "full cause traceability for every durable state change",
            "causal chain traversal (given any state field, reconstruct the evidence sequence that caused it)",
            "source/at/id provenance fields on every log entry",
        ],
        "spec_section": "§62i AP6",
        "summary": "Every durable state change MUST be traceable to a cause. Enables the justification system (urace why) and full audit trails.",
    },
    "AP7": {
        "name": "Canonical Reduction (SRLC)",
        "standalone": True,
        "tier": FOUNDATIONAL,
        "requires": [],
        "provides": [
            "semantic deduplication (two equivalent expressions have the same canonical form)",
            "minimality guarantee (no redundant element in canonical form)",
            "reproducibility (same input always produces same canonical form across bootstraps)",
        ],
        "spec_section": "§62i AP7",
        "summary": "Transforms any expression into its unique, minimal, machine-reproducible canonical form. Applied to spec rules, schemas, and data values.",
    },
    "AP8": {
        "name": "Fixpoint Calculus",
        "standalone": False,
        "tier": COMPOSITIONAL,
        "requires": ["AP3", "AP5"],
        "provides": [
            "stagnation detection (progress not advancing across iterations)",
            "convergence loops (iterate until a stable state is reached)",
            "REGRESSING/REPAIRING lifecycle escalation trigger",
        ],
        "spec_section": "§62i AP8",
        "summary": "Detects when a system has stopped making progress toward a goal. Enables REPAIRING lifecycle tier escalation on stagnation.",
    },
    "AP9": {
        "name": "Monotone Accumulator",
        "standalone": False,
        "tier": COMPOSITIONAL,
        "requires": ["AP3"],
        "provides": [
            "monotone growth invariant (accumulator value never decreases)",
            "evidence count integrity (compaction does not reduce logical count)",
            "progress measurement baseline",
        ],
        "spec_section": "§62i AP9",
        "summary": "A value that only ever increases. The append-only log length is the canonical monotone accumulator; used for progress and evidence-count invariants.",
    },
    "AP10": {
        "name": "Bounded Retry with Backoff",
        "standalone": False,
        "tier": COMPOSITIONAL,
        "requires": ["AP4", "AP5"],
        "provides": [
            "resilient retry with configurable ceiling (max attempts)",
            "exponential or linear backoff schedule",
            "failure classification (transient | semantic | structural)",
            "budget-proportional retry allocation",
        ],
        "spec_section": "§62i AP10",
        "summary": "Retries a failed operation up to a bounded ceiling with backoff between attempts. Prevents infinite retry loops while allowing recovery from transient failures.",
    },
    "AP11": {
        "name": "Bridge",
        "standalone": False,
        "tier": COMPOSITIONAL,
        "requires": ["AP4"],
        "provides": [
            "authority-boundary translation (crossing trust or process boundaries)",
            "BridgeRecord citizen (durable translation event log)",
            "schema validation at crossing point",
            "identity attestation on cross-boundary messages",
        ],
        "spec_section": "§62i AP11",
        "summary": "Translates messages across an authority or process boundary. Every trust-boundary crossing MUST be mediated by a Bridge and produce a BridgeRecord.",
    },
    "AP12": {
        "name": "Orchestrator",
        "standalone": False,
        "tier": COMPOSITIONAL,
        "requires": ["AP4"],
        "provides": [
            "sequenced multi-step operation with declared preconditions",
            "OrchestratorRecord citizen (durable operation log)",
            "phase boundaries with safe abort points",
            "cross-executor coordination",
        ],
        "spec_section": "§62i AP12",
        "summary": "Sequences a multi-step operation with declared preconditions and outcome contracts. The primary coordination mechanism for cross-executor work.",
    },
    "AP13": {
        "name": "Observer",
        "standalone": False,
        "tier": COMPOSITIONAL,
        "requires": ["AP3"],
        "provides": [
            "decoupled observation (producers do not know observer identities)",
            "broadcast log read contract (observers read from AP15 log)",
            "reactive triggers (observers may fire side-effects on log events)",
        ],
        "spec_section": "§62i AP13",
        "summary": "Reads from the broadcast log without direct coupling to producers. Enables analytics, monitoring, and reactive triggers without modifying producer code.",
    },
    "AP14": {
        "name": "Durable Inbox (Input Queue)",
        "standalone": False,
        "tier": COMPOSITIONAL,
        "requires": ["AP5"],
        "provides": [
            "crash-safe FIFO input queue (file-based, at-least-once delivery)",
            "source_input traceability (inbox id linked to produced artifacts)",
            "structured rejection records (malformed or unsupported inputs)",
            "16-kind input catalog (goal, intent, constraint, policy_control, etc.)",
            "orderly shutdown with in-progress input preservation",
        ],
        "spec_section": "§62i AP14",
        "summary": "A durable, FIFO, crash-safe command queue. All external command injection MUST use this mechanism; stdin and socket IPC are deliberately unsupported.",
    },
    "AP15": {
        "name": "Broadcast Log",
        "standalone": False,
        "tier": COMPOSITIONAL,
        "requires": ["AP3"],
        "provides": [
            "system-wide event bus (all components write; all consumers read)",
            "decoupled pub/sub without direct notification callbacks",
            "append-only event history with compaction support",
        ],
        "spec_section": "§62i AP15",
        "summary": "The system-wide event bus implemented as an append-only log. Producers never notify consumers directly; consumers observe the log.",
    },
    "AP16": {
        "name": "State Snapshot + Delta Log",
        "standalone": False,
        "tier": INTEGRATED,
        "requires": ["AP3", "AP6"],
        "provides": [
            "durable state snapshot (current-value representation)",
            "delta log (append-only change history for every mutation)",
            "causal state reconstruction (any past state reconstructible from deltas)",
            "atomic snapshot+delta writes (no torn state)",
        ],
        "spec_section": "§62i AP16",
        "summary": "Combines a mutable state snapshot with an append-only delta log. Every mutation updates both; the delta log enables full causal reconstruction.",
    },
    "AP17": {
        "name": "Lexical→Formula Reduction (LSC)",
        "standalone": False,
        "tier": COMPOSITIONAL,
        "requires": ["AP7"],
        "provides": [
            "spec rule formalization (natural language → symbolic formula)",
            "LSC (Lexical Symbol Calculus) for quantitative constraints",
            "formula-linked rule pairs (each prose rule has a verifiable formula equivalent)",
            "machine-verifiable normative rules",
        ],
        "spec_section": "§62i AP17",
        "summary": "Reduces natural language normative rules to symbolic formulas. Enables machine verification of spec rules and eliminates ambiguity in quantitative constraints.",
    },
    "AP18": {
        "name": "Scheduled Task Contract",
        "standalone": False,
        "tier": INTEGRATED,
        "requires": ["AP0", "AP2", "AP12", "AP14"],
        "provides": [
            "durable named tasks scheduled for future execution",
            "time-based and trigger-based task scheduling",
            "ScheduledTask citizen (preserved across updates)",
            "USER and SYSTEM task classes with distinct preservation rules",
        ],
        "spec_section": "§62i AP18",
        "summary": "A durable, named, time- or trigger-governed action. Scheduled tasks are citizens with stable identity; USER tasks are preserved across spec updates.",
    },
    "AP19": {
        "name": "Customization / Personalization Layer",
        "standalone": False,
        "tier": INTEGRATED,
        "requires": ["AP4", "AP16"],
        "provides": [
            "named, scoped user overrides preserved across spec updates",
            "conflict detection (spec update vs. user customization)",
            "CustomizationRecord citizen with preserve_on_update flag",
            "three customization scopes: config, spec_parameter, runtime_behavior",
        ],
        "spec_section": "§62i AP19",
        "summary": "Bridges specification-first development and user freedom. Users express overrides as declared customizations rather than silent edits; conflicts are surfaced, not silently resolved.",
    },
    "AP20": {
        "name": "Circuit Breaker",
        "standalone": False,
        "tier": COMPOSITIONAL,
        "requires": ["AP4"],
        "provides": [
            "proactive failure-rate gating (CLOSED / OPEN / HALF_OPEN state machine)",
            "configurable failure threshold and observation window",
            "recovery probe (single test call in HALF_OPEN state before re-closing)",
            "prevents cascading failures to downstream components",
            "CircuitBreakerRecord citizen (state transition log)",
        ],
        "spec_section": "§62i AP20",
        "summary": "Monitors recent failure rate and opens a gate to stop attempts when the rate exceeds a configured threshold. Complements AP10 (Bounded Retry) by preventing attempts entirely rather than scheduling retries.",
    },
    "AP21": {
        "name": "Compaction",
        "standalone": False,
        "tier": COMPOSITIONAL,
        "requires": ["AP3"],
        "provides": [
            "rolling eviction with configurable retention policy (keep N most recent, archive rest)",
            "CompactionSummary citizen (replaces evicted entries without deleting audit trail)",
            "ARCHIVE and ROLLING_EVICTION compaction modes",
            "decompaction contract (restore full segment from archive)",
            "dry-run mode (plan compaction without committing state change)",
        ],
        "spec_section": "§62i AP21",
        "summary": "Reduces append-only log size while preserving audit trail integrity. Evicted entries are replaced by a CompactionSummary; original data is archived and fully restorable.",
    },
    "AP22": {
        "name": "Checkpoint",
        "standalone": False,
        "tier": COMPOSITIONAL,
        "requires": ["AP0", "AP3"],
        "provides": [
            "durable integrity marker binding a content-addressable state digest to a lifecycle moment",
            "crash-safe recovery anchor (resume from last valid checkpoint after failure)",
            "content-addressable state verification (digest comparison across bootstraps)",
            "checkpoint kinds: bootstrap | accepted-change | assessment",
        ],
        "spec_section": "§62i AP22",
        "summary": "Binds a content-addressable state digest to a durable lifecycle moment. Enables crash recovery, point-in-time state verification, and reproducibility audits.",
    },
    "AP23": {
        "name": "Justification Chain",
        "standalone": False,
        "tier": COMPOSITIONAL,
        "requires": ["AP6"],
        "provides": [
            "decision-to-evidence traversal (given any decision, reconstruct the evidence sequence that justified it)",
            "rule-to-decision traversal (given any rule, list decisions it governed)",
            "configurable traversal depth with cycle detection",
            "JustificationStep citizen (each step in the chain with outcome and evidence ref)",
            "human-readable chain rendering",
        ],
        "spec_section": "§62i AP23",
        "summary": "Traverses from a decision back through its evidence and governing rules to answer why it was made. Complements AP6 (which traces state changes) by tracing decision reasoning.",
    },
    "AP24": {
        "name": "Derivation Framework",
        "standalone": False,
        "tier": INTEGRATED,
        "requires": ["AP0", "AP2"],
        "provides": [
            "PatternEntry citizen (schema for declaring a reusable structural pattern in a catalog)",
            "PatternCatalog (named append-only collection of PatternEntry records)",
            "PatternAdoptionRecord citizen (EXPLICIT or TRANSITIVE adoption per pattern)",
            "PatternExclusionRecord citizen (acknowledged exclusion of a transitive dep)",
            "DerivedSystemManifest citizen (full adoption manifest with resolution log)",
            "transitive dependency resolver with topological sort (FOUNDATIONAL first)",
            "stale-manifest detection (spec version mismatch warning)",
            "zero-conformance guarantee (adopted-only obligation boundary)",
        ],
        "spec_section": "§62i AP24",
        "summary": "Self-bootstrapping pattern-catalog framework: defines PatternEntry, resolves transitive dependencies, and produces a DerivedSystemManifest bounding the derived system's obligations to exactly its adopted patterns.",
    },
}


def all_pattern_ids() -> list[str]:
    return list(PATTERN_CATALOG.keys())


def resolve_dependencies(
    pattern_ids: list[str],
    excluded_ids: set[str] | None = None,
) -> tuple[list[str], list[str]]:
    """Resolve transitive dependencies for a given set of pattern IDs.

    excluded_ids: patterns to never add, even transitively.
    Returns (resolved_ids, resolution_log) where resolution_log explains
    each transitively added pattern.
    """
    excluded: set[str] = excluded_ids or set()
    resolved: list[str] = []
    log: list[str] = []
    queue = list(pattern_ids)
    seen: set[str] = set()

    while queue:
        pid = queue.pop(0)
        if pid in seen or pid in excluded:
            continue
        if pid not in PATTERN_CATALOG:
            raise ValueError(f"Unknown pattern: {pid!r}. Valid IDs: {', '.join(sorted(PATTERN_CATALOG))}")
        seen.add(pid)
        resolved.append(pid)
        entry = PATTERN_CATALOG[pid]
        explicit_set = set(pattern_ids)
        for dep in entry["requires"]:
            if dep not in seen and dep not in excluded:
                if dep not in explicit_set:
                    log.append(f"{dep} added transitively (required by {pid})")
                queue.append(dep)

    # Stable topological order: foundational first
    tier_order = {FOUNDATIONAL: 0, COMPOSITIONAL: 1, INTEGRATED: 2}
    resolved.sort(key=lambda p: (tier_order[PATTERN_CATALOG[p]["tier"]], p))
    return resolved, log


def build_derived_manifest(
    pattern_ids: list[str],
    intent: str,
    spec_version: str,
    excluded_deps: list[dict[str, str]] | None = None,
    manifest_id: str | None = None,
) -> dict[str, Any]:
    """Build a DerivedSystemManifest for the given patterns.

    pattern_ids: explicitly requested patterns
    intent: what the derived system is for
    spec_version: the URACE spec version being derived from
    excluded_deps: list of {pattern_id, override_reason} for explicit dep exclusions
    """
    from ._common import identifier, now

    excluded_ids = {e["pattern_id"] for e in (excluded_deps or [])}
    resolved, resolution_log = resolve_dependencies(
        [p for p in pattern_ids if p not in excluded_ids],
        excluded_ids=excluded_ids,
    )

    explicit_set = set(pattern_ids)
    adopted: list[dict[str, str]] = []
    for pid in resolved:
        entry = PATTERN_CATALOG[pid]
        adopted.append({
            "pattern_id": pid,
            "name": entry["name"],
            "adoption": EXPLICIT if pid in explicit_set else TRANSITIVE,
            "tier": entry["tier"],
            "provides": entry["provides"],
        })

    exclusion_records: list[dict[str, str]] = []
    for exc in (excluded_deps or []):
        eid = exc["pattern_id"]
        if eid not in PATTERN_CATALOG:
            raise ValueError(f"Unknown pattern in exclusion: {eid!r}")
        exclusion_records.append({
            "pattern_id": eid,
            "name": PATTERN_CATALOG[eid]["name"],
            "override_reason": exc.get("override_reason", ""),
            "acknowledged": True,
        })

    return {
        "manifest_id": manifest_id or identifier("derived"),
        "derived_from": "URACE",
        "spec_version": spec_version,
        "intent": intent,
        "generated_at": now(),
        "adopted_patterns": adopted,
        "excluded_deps": exclusion_records,
        "resolution_log": resolution_log,
    }


def render_manifest_human(manifest: dict[str, Any]) -> str:
    lines = [
        f"DerivedSystemManifest {manifest['manifest_id']}",
        f"  derived_from:  {manifest['derived_from']} {manifest['spec_version']}",
        f"  intent:        {manifest['intent']}",
        f"  generated_at:  {manifest['generated_at']}",
        "",
        f"Adopted patterns ({len(manifest['adopted_patterns'])}):",
    ]
    for rec in manifest["adopted_patterns"]:
        tag = "[explicit]" if rec["adoption"] == EXPLICIT else "[transitive]"
        lines.append(f"  {rec['pattern_id']:5s} {rec['name']:45s} {tag} ({rec['tier']})")
        for cap in rec["provides"]:
            lines.append(f"         + {cap}")
    if manifest.get("excluded_deps"):
        lines.append("")
        lines.append(f"Excluded transitive deps ({len(manifest['excluded_deps'])}):")
        for exc in manifest["excluded_deps"]:
            lines.append(f"  {exc['pattern_id']:5s} {exc['name']:45s} reason: {exc['override_reason']}")
    if manifest.get("resolution_log"):
        lines.append("")
        lines.append("Dependency resolution:")
        for entry in manifest["resolution_log"]:
            lines.append(f"  + {entry}")
    return "\n".join(lines)


# §62l PatternMechanismMapping (r39): AP → implementing sections + key provides
PATTERN_MECHANISM_MAP: dict[str, dict] = {
    "AP0":  {"sections": ["62b"], "key_provides": ["id prefix", "uniqueness", "lifecycle traceability"]},
    "AP1":  {"sections": ["62b"], "key_provides": ["typed leaf values", "define-once reuse"]},
    "AP2":  {"sections": ["62b", "62l"], "key_provides": ["named versioned structures", "minimality rule"]},
    "AP3":  {"sections": ["62b", "62f"], "key_provides": ["durable ordered sequence", "monotone length"]},
    "AP4":  {"sections": ["43", "62c", "72"], "key_provides": ["named bilateral obligations", "violation protocol"]},
    "AP5":  {"sections": ["50", "51", "62b"], "key_provides": ["retry safety", "idempotency class"]},
    "AP6":  {"sections": ["53", "62e", "62g"], "key_provides": ["full cause traceability", "causal chain"]},
    "AP7":  {"sections": ["62a", "62h"], "key_provides": ["semantic deduplication", "minimality guarantee"]},
    "AP8":  {"sections": ["37", "38"], "key_provides": ["stagnation detection", "convergence loops"]},
    "AP9":  {"sections": ["59b", "62c"], "key_provides": ["monotone growth invariant", "evidence count integrity"]},
    "AP10": {"sections": ["43", "62c"], "key_provides": ["resilient bounded retry", "exponential backoff"]},
    "AP11": {"sections": ["62i"], "key_provides": ["authority-boundary translation", "BridgeRecord"]},
    "AP12": {"sections": ["62i"], "key_provides": ["sequenced multi-step operations", "OrchestratorRecord"]},
    "AP13": {"sections": ["60", "71"], "key_provides": ["decoupled observation", "broadcast log"]},
    "AP14": {"sections": ["38", "62l"], "key_provides": ["crash-safe FIFO input queue", "source_input traceability"]},
    "AP15": {"sections": ["60"], "key_provides": ["system-wide event bus", "decoupled pub/sub"]},
    "AP16": {"sections": ["60", "73"], "key_provides": ["durable state snapshot", "delta log"]},
    "AP17": {"sections": ["62a"], "key_provides": ["spec rule formalization", "formula-linked rule pairs"]},
    "AP18": {"sections": ["42", "62c"], "key_provides": ["durable named scheduled tasks", "ScheduledTask citizen"]},
    "AP19": {"sections": ["62b"], "key_provides": ["named scoped user overrides", "conflict detection"]},
    "AP20": {"sections": ["43", "62c"], "key_provides": ["proactive failure-rate gating", "CLOSED/OPEN/HALF_OPEN"]},
    "AP21": {"sections": ["62f"], "key_provides": ["bounded growth", "archive + decompact"]},
    "AP22": {"sections": ["61", "62c"], "key_provides": ["accepted-state snapshot", "recovery anchor"]},
    "AP23": {"sections": ["62g"], "key_provides": ["reasoning chain traversal", "urace why"]},
    "AP24": {"sections": ["62j"], "key_provides": ["DerivedSystemManifest", "zero-conformance guarantee"]},
    "AP25": {"sections": ["59b", "62c"], "key_provides": ["capability ceiling", "sweet-spot band"]},
}

# Intent-keyword → pattern affinity table (r40): maps domain terms to AP IDs that cover them.
# Used by suggest_patterns_from_intent to boost patterns beyond raw keyword match.
_INTENT_AFFINITY: dict[str, list[str]] = {
    "identity":         ["AP0", "AP1", "AP2"],
    "schema":           ["AP0", "AP1", "AP2"],
    "log":              ["AP3", "AP21"],
    "audit":            ["AP3", "AP6"],
    "compaction":       ["AP21"],
    "event":            ["AP3", "AP13", "AP14", "AP15"],
    "queue":            ["AP14"],
    "publish":          ["AP13", "AP15"],
    "subscribe":        ["AP13", "AP15"],
    "bus":              ["AP15"],
    "retry":            ["AP5", "AP10"],
    "idempotent":       ["AP5"],
    "backoff":          ["AP10"],
    "circuit":          ["AP20"],
    "resilient":        ["AP10", "AP20", "AP22"],
    "resilience":       ["AP10", "AP20", "AP22"],
    "snapshot":         ["AP16", "AP22"],
    "recovery":         ["AP22"],
    "checkpoint":       ["AP22"],
    "observation":      ["AP13"],
    "observe":          ["AP13"],
    "obligation":       ["AP4"],
    "contract":         ["AP4"],
    "constraint":       ["AP4", "AP17"],
    "authority":        ["AP11"],
    "bridge":           ["AP11"],
    "orchestrat":       ["AP12"],
    "workflow":         ["AP12"],
    "stagnation":       ["AP8"],
    "convergence":      ["AP8"],
    "progress":         ["AP8"],
    "evidence":         ["AP9"],
    "monot":            ["AP9"],
    "causal":           ["AP6"],
    "trace":            ["AP6", "AP23"],
    "reason":           ["AP23"],
    "why":              ["AP23"],
    "dedup":            ["AP7"],
    "duplicate":        ["AP7"],
    "schedule":         ["AP18"],
    "scheduled":        ["AP18"],
    "override":         ["AP19"],
    "customiz":         ["AP19"],
    "derive":           ["AP24"],
    "manifest":         ["AP24"],
    "capability":       ["AP25"],
    "envelope":         ["AP25"],
    "ceiling":          ["AP25"],
    "rule":             ["AP17"],
    "formula":          ["AP17"],
    "delta":            ["AP16"],
    "state":            ["AP16", "AP22"],
}


def _affinity_match(tokens: "set[str]", cid: str, *affinity_maps: dict) -> float:
    """Return combined affinity score for cid across one or more affinity maps."""
    score = 0.0
    for amap in affinity_maps:
        for stem, ids in amap.items():
            if cid in ids and (
                any(stem in tok for tok in tokens)
                or any(tok in stem for tok in tokens if len(tok) > 3)
            ):
                score += 2
    return score


def suggest_patterns_from_intent(intent: str, top_n: int = 6) -> list[dict]:
    """Rank patterns by keyword + affinity overlap with the given intent string.

    Returns up to top_n entries sorted descending by score, each with
    pattern_id, name, tier, score, and summary.
    """
    import re
    tokens = {w.lower() for w in re.split(r"\W+", intent) if len(w) > 2}
    if not tokens:
        return []

    scores: dict[str, float] = {}
    for pid, entry in PATTERN_CATALOG.items():
        text = " ".join([
            entry.get("name", ""),
            entry.get("summary", ""),
            " ".join(entry.get("provides", [])),
        ]).lower()
        kw_score = sum(1 for t in tokens if t in text)

        affinity_score = _affinity_match(tokens, pid, _INTENT_AFFINITY)
        total = kw_score + affinity_score
        if total > 0:
            scores[pid] = total

    ranked = sorted(scores, key=lambda p: (-scores[p], p))
    return [
        {
            "pattern_id": p,
            "name": PATTERN_CATALOG[p]["name"],
            "tier": PATTERN_CATALOG[p]["tier"],
            "score": scores[p],
            "summary": PATTERN_CATALOG[p].get("summary", ""),
        }
        for p in ranked[:top_n]
    ]


def patterns_from_goals(goals: list[dict], top_n: int = 8) -> list[dict]:
    """Aggregate pattern suggestions across all goal titles/descriptions."""
    combined = _aggregate_scores(goals, ["title", "description", "scope"],
                                 suggest_patterns_from_intent, "pattern_id", top_n)
    ranked = sorted(combined, key=lambda p: (-combined[p], p))
    return [{"pattern_id": p, "name": PATTERN_CATALOG[p]["name"],
             "tier": PATTERN_CATALOG[p]["tier"], "score": combined[p],
             "summary": PATTERN_CATALOG[p].get("summary", "")} for p in ranked[:top_n]]


# r41: Extended construct catalogs — mechanisms, schemas, protocols, contracts.
# Each entry has: name, kind, summary, provides, spec_section, standalone.

MECHANISM_CATALOG: dict[str, dict] = {
    "QSM": {
        "name": "Quality Streak Mechanism",
        "kind": "mechanism",
        "summary": "Tracks consecutive IMPROVEMENT/REGRESSION quality deltas. Blocks regression acceptance until a CHECKPOINT_ACCEPTANCE DecisionRecord is present.",
        "provides": ["quality streak counter", "regression checkpoint gate", "IMPROVEMENT/REGRESSION classification"],
        "requires_patterns": ["AP0", "AP3"],
        "spec_section": "§62c",
        "standalone": True,
    },
    "SSB": {
        "name": "Sweet-Spot Band",
        "kind": "mechanism",
        "summary": "Classifies product maturity as CAPABLE, OPTIMIZED, or OVER_ENGINEERED by comparing surface area against declared complexity ceiling.",
        "provides": ["maturity classification", "over-engineering detection", "sweet-spot target band"],
        "requires_patterns": ["AP25"],
        "spec_section": "§62c §59b",
        "standalone": False,
    },
    "CEG": {
        "name": "Capability Envelope Gate",
        "kind": "mechanism",
        "summary": "Blocks surface growth beyond the declared capability ceiling when product maturity is CAPABLE or OPTIMIZED.",
        "provides": ["ceiling enforcement", "surface growth gate", "capability boundary guard"],
        "requires_patterns": ["AP25"],
        "spec_section": "§62c",
        "standalone": False,
    },
    "TAG": {
        "name": "Technique Applicability Gate",
        "kind": "mechanism",
        "summary": "Gates technique execution by evaluating named context conditions. Executes only when all preconditions match.",
        "provides": ["context-gated execution", "technique precondition check", "applicability scoring"],
        "requires_patterns": ["AP0", "AP1"],
        "spec_section": "§62h",
        "standalone": True,
    },
    "DCG": {
        "name": "Discovery Credit Gate",
        "kind": "mechanism",
        "summary": "Gates discovery spend against DiscoveryBudgetStatus. Blocks new discovery cycles when budget is EXHAUSTED or SUSPENDED.",
        "provides": ["discovery budget enforcement", "credit gate", "spend tracking"],
        "requires_patterns": ["AP0", "AP9"],
        "spec_section": "§62e",
        "standalone": True,
    },
    "PSD": {
        "name": "Progress Stagnation Detector",
        "kind": "mechanism",
        "summary": "Detects stagnant progress_vector over consecutive cycles. Transitions lifecycle to REPAIRING and emits an IntegrityGap when threshold exceeded.",
        "provides": ["stagnation detection", "REPAIRING lifecycle trigger", "progress vector tracking"],
        "requires_patterns": ["AP8"],
        "spec_section": "§62c",
        "standalone": False,
    },
}

SCHEMA_CATALOG: dict[str, dict] = {
    "GoalRecord": {
        "name": "GoalRecord",
        "kind": "schema",
        "summary": "Named, scoped goal with priority. Primary unit of operator intent.",
        "provides": ["goal identity", "scope assignment", "priority ordering"],
        "required_fields": ["id", "title", "description", "scope", "priority", "status"],
        "id_prefix": "goal-",
        "spec_section": "§39",
        "standalone": True,
    },
    "ObjectiveRecord": {
        "name": "ObjectiveRecord",
        "kind": "schema",
        "summary": "Bounded work unit derived from a Goal. Carries authority resolution result and scope.",
        "provides": ["objective identity", "authority resolution link", "scope boundary"],
        "required_fields": ["id", "title", "scope", "status", "goal_id"],
        "id_prefix": "obj-",
        "spec_section": "§40",
        "standalone": False,
    },
    "PlanRecord": {
        "name": "PlanRecord",
        "kind": "schema",
        "summary": "Execution plan with ordered steps, linked to an Objective.",
        "provides": ["plan identity", "step sequencing", "objective linkage"],
        "required_fields": ["id", "objective_id", "steps", "status"],
        "id_prefix": "plan-",
        "spec_section": "§41",
        "standalone": False,
    },
    "EvidenceRecord": {
        "name": "EvidenceRecord",
        "kind": "schema",
        "summary": "Evidence item with kind, value, source, and confidence. Primary factual grounding unit.",
        "provides": ["evidence identity", "typed evidence values", "confidence tracking"],
        "required_fields": ["id", "kind", "value", "source", "confidence", "at"],
        "id_prefix": "ev-",
        "spec_section": "§44",
        "standalone": True,
    },
    "DecisionRecord": {
        "name": "DecisionRecord",
        "kind": "schema",
        "summary": "Authoritative decision with basis, outcome, and authority link. All consequential choices must be recorded.",
        "provides": ["decision identity", "basis traceability", "authority linkage"],
        "required_fields": ["id", "kind", "outcome", "basis", "at"],
        "id_prefix": "dec-",
        "spec_section": "§55",
        "standalone": True,
    },
    "PolicyRecord": {
        "name": "PolicyRecord",
        "kind": "schema",
        "summary": "Named policy with conditions and actions. Governs behavior within declared scope. Implements GoverningRecord.",
        "provides": ["policy identity", "condition-action contract", "GoverningRecord provenance"],
        "required_fields": ["id", "authority_basis", "scope", "established_at", "kind", "status", "name", "conditions", "actions"],
        "id_prefix": "pol-",
        "spec_section": "§72",
        "standalone": True,
    },
    "HardConstraint": {
        "name": "HardConstraint",
        "kind": "schema",
        "summary": "Inviolable constraint with enforcement mode. Never weakened autonomously. Implements GoverningRecord.",
        "provides": ["constraint identity", "enforcement contract", "GoverningRecord provenance"],
        "required_fields": ["id", "authority_basis", "scope", "established_at", "name", "description", "enforcement"],
        "id_prefix": "hco-",
        "spec_section": "§72",
        "standalone": True,
    },
    "AssessmentRecord": {
        "name": "AssessmentRecord",
        "kind": "schema",
        "summary": "Assessment cycle record tracking what was evaluated, scores, and outcomes.",
        "provides": ["assessment identity", "cycle tracking", "score recording"],
        "required_fields": ["id", "cycle_id", "assessed_at", "status", "scores"],
        "id_prefix": "asr-",
        "spec_section": "§37",
        "standalone": True,
    },
    "DiscoveryRecord": {
        "name": "DiscoveryRecord",
        "kind": "schema",
        "summary": "Discovery cycle record with budget tracking and signal outcomes.",
        "provides": ["discovery identity", "cycle status", "credit tracking"],
        "required_fields": ["id", "started_at", "status", "credits_used"],
        "id_prefix": "dsc-",
        "spec_section": "§36",
        "standalone": True,
    },
    "MarketSignal": {
        "name": "MarketSignal",
        "kind": "schema",
        "summary": "Typed market signal with strength and source. Feeds product-market fit assessment.",
        "provides": ["signal identity", "typed market data", "strength measurement"],
        "required_fields": ["id", "kind", "strength", "source", "observed_at"],
        "id_prefix": "mks-",
        "spec_section": "§59",
        "standalone": True,
    },
    "FitHypothesis": {
        "name": "FitHypothesis",
        "kind": "schema",
        "summary": "Product-market fit hypothesis with confidence and validation lifecycle.",
        "provides": ["hypothesis identity", "confidence tracking", "validation lifecycle"],
        "required_fields": ["id", "description", "confidence", "status", "created_at"],
        "id_prefix": "fhy-",
        "spec_section": "§59",
        "standalone": True,
    },
    "OwnershipMarker": {
        "name": "OwnershipMarker",
        "kind": "schema",
        "summary": "Ownership assignment for a named scope with concurrency policy.",
        "provides": ["ownership identity", "scope assignment", "concurrency contract"],
        "required_fields": ["id", "scope", "owner_id", "acquired_at", "concurrency_policy"],
        "id_prefix": "omk-",
        "spec_section": "§63",
        "standalone": True,
    },
    "ScheduledTask": {
        "name": "ScheduledTask",
        "kind": "schema",
        "summary": "Named, durable scheduled task with cron expression and execution contract.",
        "provides": ["task identity", "schedule expression", "execution history"],
        "required_fields": ["id", "name", "schedule", "action", "status"],
        "id_prefix": "sched-",
        "spec_section": "§42",
        "standalone": True,
    },
    "QualityDelta": {
        "name": "QualityDelta",
        "kind": "schema",
        "summary": "Quality measurement delta with direction (IMPROVEMENT/REGRESSION/NEUTRAL) and magnitude.",
        "provides": ["quality measurement identity", "direction classification", "magnitude tracking"],
        "required_fields": ["id", "direction", "magnitude", "scope", "at"],
        "id_prefix": "qdelta-",
        "spec_section": "§61",
        "standalone": True,
    },
    "IntegrityGap": {
        "name": "IntegrityGap",
        "kind": "schema",
        "summary": "Integrity gap record with kind (from IntegrityGapCatalog), severity, and resolution status.",
        "provides": ["gap identity", "severity classification", "resolution tracking"],
        "required_fields": ["id", "kind", "severity", "detail", "at", "resolved"],
        "id_prefix": "igap-",
        "spec_section": "§62l",
        "standalone": True,
    },
    "CapabilityStatement": {
        "name": "CapabilityStatement",
        "kind": "schema",
        "summary": "Named capability declaration with tier, value weight, and maturity status.",
        "provides": ["capability identity", "tier classification", "value weighting"],
        "required_fields": ["id", "name", "scope", "tier", "value_weight", "status"],
        "id_prefix": "cap-",
        "spec_section": "§59b",
        "standalone": True,
    },
    "OperationRecord": {
        "name": "OperationRecord",
        "kind": "schema",
        "summary": "Execution operation record with PENDING→ACCEPTED/REJECTED lifecycle and executor attribution.",
        "provides": ["operation identity", "status lifecycle", "executor attribution"],
        "required_fields": ["id", "objective_id", "plan_id", "status", "executor_id", "at"],
        "id_prefix": "op-",
        "spec_section": "§53",
        "standalone": False,
    },
    "BridgeRecord": {
        "name": "BridgeRecord",
        "kind": "schema",
        "summary": "Authority boundary translation record. Documents crossing from one authority scope to another.",
        "provides": ["bridge identity", "authority translation audit", "scope crossing traceability"],
        "required_fields": ["id", "from_scope", "to_scope", "authority_basis", "at"],
        "id_prefix": "brd-",
        "spec_section": "§62i AP11",
        "standalone": False,
    },
    "OrchestratorRecord": {
        "name": "OrchestratorRecord",
        "kind": "schema",
        "summary": "Multi-step operation orchestration record. Sequences dependent sub-operations with state tracking.",
        "provides": ["orchestration identity", "step sequencing", "sub-operation tracking"],
        "required_fields": ["id", "name", "steps", "status", "at"],
        "id_prefix": "orch-",
        "spec_section": "§62i AP12",
        "standalone": False,
    },
    "CheckpointRecord": {
        "name": "CheckpointRecord",
        "kind": "schema",
        "summary": "Accepted-state snapshot. Recovery anchor for rollback. Produced by the quality checkpoint gate.",
        "provides": ["checkpoint identity", "state digest", "recovery anchor"],
        "required_fields": ["id", "at", "kind", "digest"],
        "id_prefix": "checkpoint-",
        "spec_section": "§61",
        "standalone": False,
    },
    "DerivedManifestRef": {
        "name": "DerivedManifestRef",
        "kind": "schema",
        "summary": "Reference to a saved DerivedSystemManifest. Enables stale-manifest detection across spec version bumps.",
        "provides": ["manifest reference identity", "spec version tracking", "stale detection anchor"],
        "required_fields": ["id", "manifest_id", "spec_version", "generated_at", "adopted_pattern_ids", "intent"],
        "id_prefix": "dmr-",
        "spec_section": "§62j",
        "standalone": True,
    },
}

PROTOCOL_CATALOG: dict[str, dict] = {
    "EUP": {
        "name": "EffectUncertaintyProtocol",
        "kind": "protocol",
        "summary": "3-step protocol for INDETERMINATE effect handling: classify → hold before retry → preserve durable record.",
        "provides": ["INDETERMINATE classification", "reconciliation gate", "durable unresolved-effect record"],
        "steps": [
            "Classify effect as INDETERMINATE when outcome cannot be confirmed",
            "Hold state — do not retry until effect is reconciled",
            "Preserve durable UnresolvedEffect record for operator review",
        ],
        "requires_patterns": ["AP5", "AP6"],
        "spec_section": "§62l",
        "standalone": True,
    },
    "OGP": {
        "name": "OperatorGateProtocol",
        "kind": "protocol",
        "summary": "4-clause protocol: surface BLOCKING gap → hold state → await authenticated clearance → emit durable gate event.",
        "provides": ["operator gate blocking", "clearance lifecycle", "gate event audit"],
        "steps": [
            "Surface a named BLOCKING IntegrityGap with condition_kind",
            "Hold all dependent state mutations until clearance",
            "Await authenticated operator clearance (DecisionRecord kind=OPERATOR_CLEARANCE)",
            "Emit durable gate event and resolve the gap",
        ],
        "requires_patterns": ["AP0", "AP6"],
        "spec_section": "§62l",
        "standalone": True,
    },
}

CONTRACT_CATALOG: dict[str, dict] = {
    "GRC": {
        "name": "GoverningRecord",
        "kind": "contract",
        "summary": "Canonical cluster for citizens that establish authoritative boundaries. Requires: id, authority_basis, scope, established_at.",
        "provides": ["governance provenance", "authority-basis traceability", "scope declaration", "establishment timestamp"],
        "invariants": [
            "authority_basis must be non-empty string",
            "scope must be non-empty string",
            "established_at must be ISO-8601 timestamp",
        ],
        "applies_to": ["PolicyRecord", "HardConstraint"],
        "spec_section": "§62l",
        "standalone": True,
    },
    "IGC": {
        "name": "IntegrityGapCatalog",
        "kind": "contract",
        "summary": "20 named gap kinds each with canonical severity. All IntegrityGap emissions MUST use a registered kind from this catalog.",
        "provides": ["named gap vocabulary", "canonical severity assignment", "gap kind registry"],
        "gap_count": 20,
        "spec_section": "§62l",
        "standalone": True,
    },
    "ISC": {
        "name": "InspectionSurface",
        "kind": "contract",
        "summary": "11-category output contract for system health inspection. Any check endpoint SHOULD conform to this schema.",
        "provides": ["structured health output", "blocking/warning gap separation", "summary field"],
        "categories": [
            "lifecycle_state", "assessed_at", "blocking_gaps", "warning_gaps",
            "indeterminate_effects", "operator_gates", "stale_items",
            "capability_readiness", "scheduled_conditions",
            "policy_violations", "open_pending_validations", "summary",
        ],
        "spec_section": "§62l",
        "standalone": True,
    },
    "ACI": {
        "name": "AuthorityClosureInvariant",
        "kind": "contract",
        "summary": "Enumerates all non-Authority input sources. Actions solely driven by these sources must never be treated as authority-driven.",
        "provides": ["non-authority source enumeration", "closure check", "authority boundary guard"],
        "non_authority_sources": [
            "evidence", "priority", "capability", "market_signal", "trigger",
            "schedule", "executor_recommendation", "product_value", "user_absence", "market_success",
        ],
        "spec_section": "§62l",
        "standalone": True,
    },
    "RVS": {
        "name": "RevalidationScope",
        "kind": "contract",
        "summary": "Maps change-class triggers to DECISION_ONLY | DEPENDENT_PLANS | FULL_LIFECYCLE scope. Governs how much of the lifecycle must be revalidated after a premise change.",
        "provides": ["revalidation scope mapping", "trigger classification", "minimum revalidation contract"],
        "scopes": ["DECISION_ONLY", "DEPENDENT_PLANS", "FULL_LIFECYCLE"],
        "spec_section": "§62l",
        "standalone": True,
    },
    "ABM": {
        "name": "AuthorityBoundaryModel",
        "kind": "contract",
        "summary": "Delegated/reserved authority boundary with typed scope-to-authority-category mapping. Enforced at every objective evaluation.",
        "provides": ["delegated authority categories", "reserved decision enumeration", "scope-to-authority mapping"],
        "invariants": [
            "reserved decisions are never autonomously executed",
            "scope must map to delegated categories",
            "constraint-weakening verbs trigger REQUIRES_AUTHORITATIVE_DECISION",
        ],
        "spec_section": "§14-16",
        "standalone": True,
    },
}


def _build_construct_catalog() -> dict[str, dict]:
    catalog: dict[str, dict] = {}
    for pid, entry in PATTERN_CATALOG.items():
        catalog[pid] = {**entry, "kind": "pattern", "construct_id": pid}
    for sub in (MECHANISM_CATALOG, SCHEMA_CATALOG, PROTOCOL_CATALOG, CONTRACT_CATALOG):
        for cid, entry in sub.items():
            catalog[cid] = {**entry, "construct_id": cid}
    return catalog


CONSTRUCT_CATALOG: dict[str, dict] = _build_construct_catalog()

# Kind constants
KIND_PATTERN = "pattern"
KIND_MECHANISM = "mechanism"
KIND_SCHEMA = "schema"
KIND_PROTOCOL = "protocol"
KIND_CONTRACT = "contract"
ALL_KINDS: frozenset[str] = frozenset({KIND_PATTERN, KIND_MECHANISM, KIND_SCHEMA, KIND_PROTOCOL, KIND_CONTRACT})

# Construct-level affinity table (r41): domain stems → construct IDs
_CONSTRUCT_AFFINITY: dict[str, list[str]] = {
    "quality":        ["QSM", "QualityDelta", "CheckpointRecord"],
    "streak":         ["QSM"],
    "regression":     ["QSM"],
    "checkpoint":     ["QSM", "CheckpointRecord"],
    "maturity":       ["SSB", "CEG"],
    "sweet":          ["SSB"],
    "ceiling":        ["CEG", "SSB"],
    "technique":      ["TAG"],
    "applicability":  ["TAG"],
    "discovery":      ["DCG", "DiscoveryRecord"],
    "budget":         ["DCG"],
    "stagnation":     ["PSD"],
    "uncertain":      ["EUP"],
    "indeterminate":  ["EUP"],
    "reconcil":       ["EUP"],
    "operator":       ["OGP"],
    "clearance":      ["OGP"],
    "governing":      ["GRC", "PolicyRecord", "HardConstraint"],
    "invariant":      ["ACI", "HardConstraint"],
    "inspection":     ["ISC"],
    "health":         ["ISC"],
    "authority":      ["ABM", "ACI", "DecisionRecord"],
    "revalidat":      ["RVS"],
    "gap":            ["IntegrityGap", "IGC"],
    "policy":         ["PolicyRecord"],
    "constraint":     ["HardConstraint"],
    "goal":           ["GoalRecord"],
    "objective":      ["ObjectiveRecord"],
    "evidence":       ["EvidenceRecord"],
    "decision":       ["DecisionRecord"],
    "assessment":     ["AssessmentRecord"],
    "market":         ["MarketSignal", "FitHypothesis"],
    "hypothesis":     ["FitHypothesis"],
    "ownership":      ["OwnershipMarker"],
    "schedule":       ["ScheduledTask"],
    "capability":     ["CapabilityStatement", "CEG"],
    "bridge":         ["BridgeRecord"],
    "orchestrat":     ["OrchestratorRecord"],
    "operation":      ["OperationRecord"],
    "manifest":       ["DerivedManifestRef"],
}


def suggest_constructs_from_intent(
    intent: str,
    kinds: "set[str] | None" = None,
    top_n: int = 8,
) -> list[dict]:
    """Rank constructs across all kinds by keyword + affinity overlap with intent.

    kinds: restrict to these kind strings (None = all kinds).
    Returns up to top_n entries with construct_id, name, kind, score, summary.
    """
    import re
    tokens = {w.lower() for w in re.split(r"\W+", intent) if len(w) > 2}
    if not tokens:
        return []

    active_kinds = kinds or ALL_KINDS
    scores: dict[str, float] = {}

    for cid, entry in CONSTRUCT_CATALOG.items():
        if entry.get("kind") not in active_kinds:
            continue
        text = " ".join([
            entry.get("name", ""),
            entry.get("summary", ""),
            " ".join(str(p) for p in entry.get("provides", [])),
            " ".join(str(s) for s in entry.get("steps", [])),
            " ".join(str(i) for i in entry.get("invariants", [])),
        ]).lower()
        kw_score = sum(1 for t in tokens if t in text)

        affinity_score = _affinity_match(
            tokens, cid,
            _INTENT_AFFINITY if entry.get("kind") == KIND_PATTERN else {},
            _CONSTRUCT_AFFINITY,
        )
        total = kw_score + affinity_score
        if total > 0:
            scores[cid] = total

    ranked = sorted(scores, key=lambda c: (-scores[c], c))
    return [
        {
            "construct_id": c,
            "name": CONSTRUCT_CATALOG[c]["name"],
            "kind": CONSTRUCT_CATALOG[c]["kind"],
            "score": scores[c],
            "summary": CONSTRUCT_CATALOG[c].get("summary", ""),
        }
        for c in ranked[:top_n]
    ]


def build_derived_construct_set(
    construct_ids: list[str],
    intent: str,
    spec_version: str,
) -> dict:
    """Build a DerivedConstructSet for the given construct IDs (any kind, or mixed).

    For pattern-only IDs, callers may prefer build_derived_manifest for full
    dependency resolution. DerivedConstructSet is the unified multi-kind output.
    """
    from ._common import identifier, now

    adopted = []
    unknown = [cid for cid in construct_ids if cid not in CONSTRUCT_CATALOG]
    if unknown:
        raise ValueError(f"Unknown construct IDs: {', '.join(unknown)}")

    for cid in construct_ids:
        entry = CONSTRUCT_CATALOG[cid]
        adopted.append({
            "construct_id": cid,
            "name": entry["name"],
            "kind": entry["kind"],
            "summary": entry.get("summary", ""),
            "provides": entry.get("provides", []),
            "spec_section": entry.get("spec_section", ""),
        })

    return {
        "construct_set_id": identifier("cset"),
        "derived_from": "URACE",
        "spec_version": spec_version,
        "intent": intent,
        "generated_at": now(),
        "adopted_constructs": adopted,
        "kinds_present": sorted({r["kind"] for r in adopted}),
    }


def render_construct_set_human(cset: dict) -> str:
    lines = [
        f"DerivedConstructSet {cset['construct_set_id']}",
        f"  derived_from:  {cset['derived_from']} {cset['spec_version']}",
        f"  intent:        {cset['intent']}",
        f"  generated_at:  {cset['generated_at']}",
        f"  kinds:         {', '.join(cset.get('kinds_present', []))}",
        "",
        f"Adopted constructs ({len(cset['adopted_constructs'])}):",
    ]
    # group by kind for readability
    by_kind: dict[str, list] = {}
    for rec in cset["adopted_constructs"]:
        by_kind.setdefault(rec["kind"], []).append(rec)
    for kind in sorted(by_kind):
        lines.append(f"\n  [{kind.upper()}]")
        for rec in by_kind[kind]:
            lines.append(f"    {rec['construct_id']:16s}  {rec['name']}")
            lines.append(f"    {'':16s}  {rec['summary']}")
            for p in rec.get("provides", []):
                lines.append(f"    {'':16s}  + {p}")
    return "\n".join(lines)


def all_construct_ids(kinds: "set[str] | None" = None) -> list[str]:
    """Return all construct IDs, optionally filtered by kind."""
    active = kinds or ALL_KINDS
    return [cid for cid, e in CONSTRUCT_CATALOG.items() if e.get("kind") in active]


def constructs_from_constraints(constraints: list[dict], top_n: int = 8) -> list[dict]:
    """Aggregate IntentSuggestionEngine across HardConstraints in state."""
    combined = _aggregate_scores(
        constraints, ["name", "description", "scope", "enforcement"],
        suggest_constructs_from_intent, "construct_id", top_n,
        kinds={"contract", "protocol", "mechanism"},
    )
    ranked = sorted(combined, key=lambda c: (-combined[c], c))
    return [{"construct_id": c, "name": CONSTRUCT_CATALOG[c]["name"],
             "kind": CONSTRUCT_CATALOG[c]["kind"], "score": combined[c],
             "summary": CONSTRUCT_CATALOG[c].get("summary", "")} for c in ranked[:top_n]]


def constructs_for_gaps(gaps: list[dict], top_n: int = 8) -> list[dict]:
    """Map InspectionSurface gaps to constructs that address them."""
    combined = _aggregate_scores(
        gaps, ["kind", "detail"],
        suggest_constructs_from_intent, "construct_id", top_n,
    )
    ranked = sorted(combined, key=lambda c: (-combined[c], c))
    return [{"construct_id": c, "name": CONSTRUCT_CATALOG[c]["name"],
             "kind": CONSTRUCT_CATALOG[c]["kind"], "score": combined[c],
             "summary": CONSTRUCT_CATALOG[c].get("summary", "")} for c in ranked[:top_n]]



def _aggregate_scores(
    items: list[dict],
    text_fields: list[str],
    suggest_fn,
    id_key: str,
    top_n: int,
    **suggest_kwargs,
) -> "dict[str, float]":
    """Accumulate suggestion scores across multiple source items. Returns {id: score} unsorted."""
    combined: dict[str, float] = {}
    for item in items:
        text = " ".join(str(item.get(f, "")) for f in text_fields)
        for entry in suggest_fn(text, top_n=top_n, **suggest_kwargs):
            cid = entry[id_key]
            combined[cid] = combined.get(cid, 0) + entry["score"]
    return combined

# ---------------------------------------------------------------------------
# r46 — Construct/pattern digest + new-construct suggestion + update detection
# ---------------------------------------------------------------------------

def _entry_digest(d: dict, keys: tuple) -> str:
    content = json.dumps({k: d.get(k) for k in keys}, sort_keys=True, default=str)
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def _make_catalog_digest_fns(catalog: dict, keys: tuple):
    """Factory: returns (digest, digests_for_ids, diff_digests) for any catalog dict."""
    def _digest(cid: str) -> str:
        return _entry_digest(catalog.get(cid, {}), keys)
    def _digests_for_ids(ids: "list[str]") -> "dict[str, str]":
        return {cid: _digest(cid) for cid in ids if cid in catalog}
    def _diff_digests(saved: "dict[str, str]", ids: "list[str]") -> "list[str]":
        current = _digests_for_ids(ids)
        return [cid for cid in ids if cid in saved and saved[cid] != current.get(cid, saved[cid])]
    return _digest, _digests_for_ids, _diff_digests


construct_digest, construct_digests_for_ids, diff_construct_digests = _make_catalog_digest_fns(
    CONSTRUCT_CATALOG, ("name", "summary", "provides", "spec_section")
)
pattern_digest, pattern_digests_for_ids, diff_pattern_digests = _make_catalog_digest_fns(
    PATTERN_CATALOG, ("name", "provides", "tier", "requires", "spec_section")
)


def _suggest_unadopted_for_refs(
    refs: list[dict],
    ref_id_field: str,
    adopted_id_field: str,
    suggest_fn,
    entry_id_field: str,
    top_n: int,
    **suggest_kwargs,
) -> "list[tuple[dict, list[dict]]]":
    """Core: for each unique ref, return (ref, top-N unadopted suggestions)."""
    results = []
    seen: set[str] = set()
    for ref in refs:
        rid = ref.get(ref_id_field, "")
        if rid in seen:
            continue
        seen.add(rid)
        intent = ref.get("intent", "")
        adopted = set(ref.get(adopted_id_field, []))
        if not intent:
            continue
        pool = suggest_fn(intent, top_n=len(adopted) + top_n + 5, **suggest_kwargs)
        new = [s for s in pool if s[entry_id_field] not in adopted][:top_n]
        if new:
            results.append((ref, new))
    return results


def suggest_new_constructs_for_saved_sets(
    construct_set_refs: list[dict], top_n: int = 3
) -> list[dict]:
    """For each saved ConstructSetRef, suggest constructs not yet adopted that match the intent."""
    results = []
    for ref in construct_set_refs:
        kinds = set(ref.get("kinds_present", []))
        if not kinds:
            continue
        for r, new in _suggest_unadopted_for_refs(
            [ref], "construct_set_id", "adopted_construct_ids",
            suggest_constructs_from_intent, "construct_id", top_n, kinds=kinds,
        ):
            results.append({
                "construct_set_id": r["construct_set_id"],
                "intent": r.get("intent", ""),
                "kinds": sorted(kinds),
                "suggestions": new,
            })
    return results


def suggest_new_patterns_for_saved_manifests(
    manifest_refs: list[dict], top_n: int = 3
) -> list[dict]:
    """For each saved manifest ref, suggest patterns not yet adopted that match the intent."""
    return [
        {"manifest_id": ref.get("manifest_id", ""), "intent": ref.get("intent", ""), "suggestions": new}
        for ref, new in _suggest_unadopted_for_refs(
            manifest_refs, "manifest_id", "adopted_pattern_ids",
            suggest_patterns_from_intent, "pattern_id", top_n,
        )
    ]
