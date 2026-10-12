"""§62j Pattern Catalog — r26: Derivation Framework.

Every AP0-AP19 entry declares standalone status, tier, requires list, and
capability descriptions so the derive command can resolve transitive deps and
generate DerivedSystemManifests without executor involvement.
"""
from __future__ import annotations

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
