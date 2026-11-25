//! §62j Pattern Catalog — AP0-AP24 Derivation Framework (Rust port).
//!
//! Every AP0-AP24 entry declares standalone status, tier, requires list, and
//! capability descriptions so the derive command can resolve transitive deps and
//! generate DerivedSystemManifests without executor involvement.
//!
//! Also includes the extended construct catalogs: mechanisms, schemas, protocols,
//! and contracts (r41).

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::{HashMap, HashSet};
use std::sync::OnceLock;
use thiserror::Error;

// ---------------------------------------------------------------------------
// Tier constants
// ---------------------------------------------------------------------------

pub const FOUNDATIONAL: &str = "FOUNDATIONAL";
pub const COMPOSITIONAL: &str = "COMPOSITIONAL";
pub const INTEGRATED: &str = "INTEGRATED";

// Adoption source constants
pub const EXPLICIT: &str = "EXPLICIT";
pub const TRANSITIVE: &str = "TRANSITIVE";

// Kind constants
pub const KIND_PATTERN: &str = "pattern";
pub const KIND_MECHANISM: &str = "mechanism";
pub const KIND_SCHEMA: &str = "schema";
pub const KIND_PROTOCOL: &str = "protocol";
pub const KIND_CONTRACT: &str = "contract";

// ---------------------------------------------------------------------------
// Error type
// ---------------------------------------------------------------------------

#[derive(Debug, Error)]
pub enum PatternError {
    #[error("Unknown pattern: {0:?}. Valid IDs: {1}")]
    UnknownPattern(String, String),
    #[error("Unknown construct ID(s): {0}")]
    UnknownConstruct(String),
}

// ---------------------------------------------------------------------------
// Pattern struct
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Pattern {
    pub id: String,
    pub name: String,
    pub standalone: bool,
    pub tier: String,
    pub requires: Vec<String>,
    pub provides: Vec<String>,
    pub spec_section: String,
    pub summary: String,
}

// ---------------------------------------------------------------------------
// Construct struct (unified view over mechanisms, schemas, protocols, contracts)
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Construct {
    pub id: String,
    pub name: String,
    pub kind: String,
    pub summary: String,
    pub provides: Vec<String>,
    pub spec_section: String,
    pub standalone: bool,
    /// For mechanisms/schemas/protocols/contracts: required pattern IDs
    pub requires_patterns: Vec<String>,
    /// Extra fields serialised as JSON for kind-specific data
    #[serde(default)]
    pub extra: serde_json::Value,
}

// ---------------------------------------------------------------------------
// Private builder helpers
// ---------------------------------------------------------------------------

fn p(
    id: &str,
    name: &str,
    standalone: bool,
    tier: &str,
    requires: &[&str],
    provides: &[&str],
    spec_section: &str,
    summary: &str,
) -> Pattern {
    Pattern {
        id: id.to_string(),
        name: name.to_string(),
        standalone,
        tier: tier.to_string(),
        requires: requires.iter().map(|s| s.to_string()).collect(),
        provides: provides.iter().map(|s| s.to_string()).collect(),
        spec_section: spec_section.to_string(),
        summary: summary.to_string(),
    }
}

fn c(
    id: &str,
    name: &str,
    kind: &str,
    summary: &str,
    provides: &[&str],
    spec_section: &str,
    standalone: bool,
    requires_patterns: &[&str],
    extra: serde_json::Value,
) -> Construct {
    Construct {
        id: id.to_string(),
        name: name.to_string(),
        kind: kind.to_string(),
        summary: summary.to_string(),
        provides: provides.iter().map(|s| s.to_string()).collect(),
        spec_section: spec_section.to_string(),
        standalone,
        requires_patterns: requires_patterns.iter().map(|s| s.to_string()).collect(),
        extra,
    }
}

// ---------------------------------------------------------------------------
// AP0-AP24 Pattern Catalog
// ---------------------------------------------------------------------------

static PATTERN_CATALOG_ONCE: OnceLock<Vec<Pattern>> = OnceLock::new();

pub fn pattern_catalog() -> &'static [Pattern] {
    PATTERN_CATALOG_ONCE.get_or_init(|| {
        vec![
            p(
                "AP0",
                "Citizen",
                true,
                FOUNDATIONAL,
                &[],
                &[
                    "named identity (stable id field, never recycled)",
                    "schema conformance (every instance validates against a declared schema)",
                    "lifecycle traceability (creation and mutation produce broadcast log entries)",
                ],
                "§62i AP0",
                "The fundamental unit of identity. Every named, schema-bearing, lifecycle-participating entity is a citizen.",
            ),
            p(
                "AP1",
                "Canonical Scalar",
                true,
                FOUNDATIONAL,
                &[],
                &[
                    "typed leaf values with domain constraints",
                    "reuse contract (define once, reference by name everywhere)",
                    "machine-verifiable field validation",
                ],
                "§62i AP1",
                "The smallest indivisible value type. Canonical scalars are defined once with domain constraints and referenced by name in all schemas.",
            ),
            p(
                "AP2",
                "Citizen Schema",
                false,
                FOUNDATIONAL,
                &["AP0", "AP1"],
                &[
                    "named, versioned, fully-specified data structures",
                    "minimality rule (no field bundles two independent normative claims)",
                    "composition rule (fields reference canonical schema names, no inline sub-schemas)",
                ],
                "§62i AP2",
                "A named, versioned, fully-specified data structure. The primary reuse unit for structured data; every field resolves to AP1 or another AP2.",
            ),
            p(
                "AP3",
                "Append-Only Log",
                false,
                FOUNDATIONAL,
                &["AP2"],
                &[
                    "durable ordered sequence with monotone non-decreasing length",
                    "ordering invariant (entries ordered by at-timestamp)",
                    "identity invariant (entry ids are stable and never reused)",
                    "compaction-safe retention (summaries replace but do not delete)",
                ],
                "§62i AP3",
                "A durable ordered sequence where records are only appended. The foundation for evidence logs, status transition logs, and all audit trails.",
            ),
            p(
                "AP4",
                "Producer-Consumer Contract",
                false,
                FOUNDATIONAL,
                &["AP0"],
                &[
                    "named, verifiable, bilateral obligations between components",
                    "producer_must list (normative obligations on the writer)",
                    "consumer_may_assume list (guaranteed properties for the reader)",
                    "violation protocol (REJECT | QUARANTINE | ALERT)",
                ],
                "§62i AP4",
                "A named, verifiable, bilateral obligation between producer and consumer. Any two components that exchange data MUST document their exchange as a named ProducerConsumerContract.",
            ),
            p(
                "AP5",
                "Idempotency Contract",
                true,
                FOUNDATIONAL,
                &[],
                &[
                    "retry safety (interrupted cycles can be safely retried)",
                    "idempotency class declaration (PURE | AT_MOST_ONCE | AT_LEAST_ONCE | EXACTLY_ONCE)",
                    "operation classification contract",
                ],
                "§62i AP5",
                "Applying an operation N times produces the same result as applying it once. Required for safe retry of interrupted cycles.",
            ),
            p(
                "AP6",
                "Causal Provenance Chain",
                false,
                COMPOSITIONAL,
                &["AP3", "AP4"],
                &[
                    "full cause traceability for every durable state change",
                    "causal chain traversal (given any state field, reconstruct the evidence sequence that caused it)",
                    "source/at/id provenance fields on every log entry",
                ],
                "§62i AP6",
                "Every durable state change MUST be traceable to a cause. Enables the justification system (urace why) and full audit trails.",
            ),
            p(
                "AP7",
                "Canonical Reduction (SRLC)",
                true,
                FOUNDATIONAL,
                &[],
                &[
                    "semantic deduplication (two equivalent expressions have the same canonical form)",
                    "minimality guarantee (no redundant element in canonical form)",
                    "reproducibility (same input always produces same canonical form across bootstraps)",
                ],
                "§62i AP7",
                "Transforms any expression into its unique, minimal, machine-reproducible canonical form. Applied to spec rules, schemas, and data values.",
            ),
            p(
                "AP8",
                "Fixpoint Calculus",
                false,
                COMPOSITIONAL,
                &["AP3", "AP5"],
                &[
                    "stagnation detection (progress not advancing across iterations)",
                    "convergence loops (iterate until a stable state is reached)",
                    "REGRESSING/REPAIRING lifecycle escalation trigger",
                ],
                "§62i AP8",
                "Detects when a system has stopped making progress toward a goal. Enables REPAIRING lifecycle tier escalation on stagnation.",
            ),
            p(
                "AP9",
                "Monotone Accumulator",
                false,
                COMPOSITIONAL,
                &["AP3"],
                &[
                    "monotone growth invariant (accumulator value never decreases)",
                    "evidence count integrity (compaction does not reduce logical count)",
                    "progress measurement baseline",
                ],
                "§62i AP9",
                "A value that only ever increases. The append-only log length is the canonical monotone accumulator; used for progress and evidence-count invariants.",
            ),
            p(
                "AP10",
                "Bounded Retry with Backoff",
                false,
                COMPOSITIONAL,
                &["AP4", "AP5"],
                &[
                    "resilient retry with configurable ceiling (max attempts)",
                    "exponential or linear backoff schedule",
                    "failure classification (transient | semantic | structural)",
                    "budget-proportional retry allocation",
                ],
                "§62i AP10",
                "Retries a failed operation up to a bounded ceiling with backoff between attempts. Prevents infinite retry loops while allowing recovery from transient failures.",
            ),
            p(
                "AP11",
                "Bridge",
                false,
                COMPOSITIONAL,
                &["AP4"],
                &[
                    "authority-boundary translation (crossing trust or process boundaries)",
                    "BridgeRecord citizen (durable translation event log)",
                    "schema validation at crossing point",
                    "identity attestation on cross-boundary messages",
                ],
                "§62i AP11",
                "Translates messages across an authority or process boundary. Every trust-boundary crossing MUST be mediated by a Bridge and produce a BridgeRecord.",
            ),
            p(
                "AP12",
                "Orchestrator",
                false,
                COMPOSITIONAL,
                &["AP4"],
                &[
                    "sequenced multi-step operation with declared preconditions",
                    "OrchestratorRecord citizen (durable operation log)",
                    "phase boundaries with safe abort points",
                    "cross-executor coordination",
                ],
                "§62i AP12",
                "Sequences a multi-step operation with declared preconditions and outcome contracts. The primary coordination mechanism for cross-executor work.",
            ),
            p(
                "AP13",
                "Observer",
                false,
                COMPOSITIONAL,
                &["AP3"],
                &[
                    "decoupled observation (producers do not know observer identities)",
                    "broadcast log read contract (observers read from AP15 log)",
                    "reactive triggers (observers may fire side-effects on log events)",
                ],
                "§62i AP13",
                "Reads from the broadcast log without direct coupling to producers. Enables analytics, monitoring, and reactive triggers without modifying producer code.",
            ),
            p(
                "AP14",
                "Durable Inbox (Input Queue)",
                false,
                COMPOSITIONAL,
                &["AP5"],
                &[
                    "crash-safe FIFO input queue (file-based, at-least-once delivery)",
                    "source_input traceability (inbox id linked to produced artifacts)",
                    "structured rejection records (malformed or unsupported inputs)",
                    "16-kind input catalog (goal, intent, constraint, policy_control, etc.)",
                    "orderly shutdown with in-progress input preservation",
                ],
                "§62i AP14",
                "A durable, FIFO, crash-safe command queue. All external command injection MUST use this mechanism; stdin and socket IPC are deliberately unsupported.",
            ),
            p(
                "AP15",
                "Broadcast Log",
                false,
                COMPOSITIONAL,
                &["AP3"],
                &[
                    "system-wide event bus (all components write; all consumers read)",
                    "decoupled pub/sub without direct notification callbacks",
                    "append-only event history with compaction support",
                ],
                "§62i AP15",
                "The system-wide event bus implemented as an append-only log. Producers never notify consumers directly; consumers observe the log.",
            ),
            p(
                "AP16",
                "State Snapshot + Delta Log",
                false,
                INTEGRATED,
                &["AP3", "AP6"],
                &[
                    "durable state snapshot (current-value representation)",
                    "delta log (append-only change history for every mutation)",
                    "causal state reconstruction (any past state reconstructible from deltas)",
                    "atomic snapshot+delta writes (no torn state)",
                ],
                "§62i AP16",
                "Combines a mutable state snapshot with an append-only delta log. Every mutation updates both; the delta log enables full causal reconstruction.",
            ),
            p(
                "AP17",
                "Lexical→Formula Reduction (LSC)",
                false,
                COMPOSITIONAL,
                &["AP7"],
                &[
                    "spec rule formalization (natural language → symbolic formula)",
                    "LSC (Lexical Symbol Calculus) for quantitative constraints",
                    "formula-linked rule pairs (each prose rule has a verifiable formula equivalent)",
                    "machine-verifiable normative rules",
                ],
                "§62i AP17",
                "Reduces natural language normative rules to symbolic formulas. Enables machine verification of spec rules and eliminates ambiguity in quantitative constraints.",
            ),
            p(
                "AP18",
                "Scheduled Task Contract",
                false,
                INTEGRATED,
                &["AP0", "AP2", "AP12", "AP14"],
                &[
                    "durable named tasks scheduled for future execution",
                    "time-based and trigger-based task scheduling",
                    "ScheduledTask citizen (preserved across updates)",
                    "USER and SYSTEM task classes with distinct preservation rules",
                ],
                "§62i AP18",
                "A durable, named, time- or trigger-governed action. Scheduled tasks are citizens with stable identity; USER tasks are preserved across spec updates.",
            ),
            p(
                "AP19",
                "Customization / Personalization Layer",
                false,
                INTEGRATED,
                &["AP4", "AP16"],
                &[
                    "named, scoped user overrides preserved across spec updates",
                    "conflict detection (spec update vs. user customization)",
                    "CustomizationRecord citizen with preserve_on_update flag",
                    "three customization scopes: config, spec_parameter, runtime_behavior",
                ],
                "§62i AP19",
                "Bridges specification-first development and user freedom. Users express overrides as declared customizations rather than silent edits; conflicts are surfaced, not silently resolved.",
            ),
            p(
                "AP20",
                "Circuit Breaker",
                false,
                COMPOSITIONAL,
                &["AP4"],
                &[
                    "proactive failure-rate gating (CLOSED / OPEN / HALF_OPEN state machine)",
                    "configurable failure threshold and observation window",
                    "recovery probe (single test call in HALF_OPEN state before re-closing)",
                    "prevents cascading failures to downstream components",
                    "CircuitBreakerRecord citizen (state transition log)",
                ],
                "§62i AP20",
                "Monitors recent failure rate and opens a gate to stop attempts when the rate exceeds a configured threshold. Complements AP10 (Bounded Retry) by preventing attempts entirely rather than scheduling retries.",
            ),
            p(
                "AP21",
                "Compaction",
                false,
                COMPOSITIONAL,
                &["AP3"],
                &[
                    "rolling eviction with configurable retention policy (keep N most recent, archive rest)",
                    "CompactionSummary citizen (replaces evicted entries without deleting audit trail)",
                    "ARCHIVE and ROLLING_EVICTION compaction modes",
                    "decompaction contract (restore full segment from archive)",
                    "dry-run mode (plan compaction without committing state change)",
                ],
                "§62i AP21",
                "Reduces append-only log size while preserving audit trail integrity. Evicted entries are replaced by a CompactionSummary; original data is archived and fully restorable.",
            ),
            p(
                "AP22",
                "Checkpoint",
                false,
                COMPOSITIONAL,
                &["AP0", "AP3"],
                &[
                    "durable integrity marker binding a content-addressable state digest to a lifecycle moment",
                    "crash-safe recovery anchor (resume from last valid checkpoint after failure)",
                    "content-addressable state verification (digest comparison across bootstraps)",
                    "checkpoint kinds: bootstrap | accepted-change | assessment",
                ],
                "§62i AP22",
                "Binds a content-addressable state digest to a durable lifecycle moment. Enables crash recovery, point-in-time state verification, and reproducibility audits.",
            ),
            p(
                "AP23",
                "Justification Chain",
                false,
                COMPOSITIONAL,
                &["AP6"],
                &[
                    "decision-to-evidence traversal (given any decision, reconstruct the evidence sequence that justified it)",
                    "rule-to-decision traversal (given any rule, list decisions it governed)",
                    "configurable traversal depth with cycle detection",
                    "JustificationStep citizen (each step in the chain with outcome and evidence ref)",
                    "human-readable chain rendering",
                ],
                "§62i AP23",
                "Traverses from a decision back through its evidence and governing rules to answer why it was made. Complements AP6 (which traces state changes) by tracing decision reasoning.",
            ),
            p(
                "AP24",
                "Derivation Framework",
                false,
                INTEGRATED,
                &["AP0", "AP2"],
                &[
                    "PatternEntry citizen (schema for declaring a reusable structural pattern in a catalog)",
                    "PatternCatalog (named append-only collection of PatternEntry records)",
                    "PatternAdoptionRecord citizen (EXPLICIT or TRANSITIVE adoption per pattern)",
                    "PatternExclusionRecord citizen (acknowledged exclusion of a transitive dep)",
                    "DerivedSystemManifest citizen (full adoption manifest with resolution log)",
                    "transitive dependency resolver with topological sort (FOUNDATIONAL first)",
                    "stale-manifest detection (spec version mismatch warning)",
                    "zero-conformance guarantee (adopted-only obligation boundary)",
                ],
                "§62i AP24",
                "Self-bootstrapping pattern-catalog framework: defines PatternEntry, resolves transitive dependencies, and produces a DerivedSystemManifest bounding the derived system's obligations to exactly its adopted patterns.",
            ),
        ]
    })
}

/// Returns all pattern IDs in catalog order (AP0 … AP24).
pub fn all_pattern_ids() -> Vec<&'static str> {
    pattern_catalog().iter().map(|p| p.id.as_str()).collect()
}

// ---------------------------------------------------------------------------
// §62l PatternMechanismMapping
// ---------------------------------------------------------------------------

/// Returns the mechanism map entry for a given AP id as a JSON value.
/// Fields: `sections` (array of strings) and `key_provides` (array of strings).
pub fn pattern_mechanism_map() -> &'static HashMap<&'static str, serde_json::Value> {
    static ONCE: OnceLock<HashMap<&'static str, serde_json::Value>> = OnceLock::new();
    ONCE.get_or_init(|| {
        use serde_json::json;
        let mut m = HashMap::new();
        m.insert("AP0",  json!({"sections": ["62b"],               "key_provides": ["id prefix", "uniqueness", "lifecycle traceability"]}));
        m.insert("AP1",  json!({"sections": ["62b"],               "key_provides": ["typed leaf values", "define-once reuse"]}));
        m.insert("AP2",  json!({"sections": ["62b", "62l"],        "key_provides": ["named versioned structures", "minimality rule"]}));
        m.insert("AP3",  json!({"sections": ["62b", "62f"],        "key_provides": ["durable ordered sequence", "monotone length"]}));
        m.insert("AP4",  json!({"sections": ["43", "62c", "72"],   "key_provides": ["named bilateral obligations", "violation protocol"]}));
        m.insert("AP5",  json!({"sections": ["50", "51", "62b"],   "key_provides": ["retry safety", "idempotency class"]}));
        m.insert("AP6",  json!({"sections": ["53", "62e", "62g"],  "key_provides": ["full cause traceability", "causal chain"]}));
        m.insert("AP7",  json!({"sections": ["62a", "62h"],        "key_provides": ["semantic deduplication", "minimality guarantee"]}));
        m.insert("AP8",  json!({"sections": ["37", "38"],          "key_provides": ["stagnation detection", "convergence loops"]}));
        m.insert("AP9",  json!({"sections": ["59b", "62c"],        "key_provides": ["monotone growth invariant", "evidence count integrity"]}));
        m.insert("AP10", json!({"sections": ["43", "62c"],         "key_provides": ["resilient bounded retry", "exponential backoff"]}));
        m.insert("AP11", json!({"sections": ["62i"],               "key_provides": ["authority-boundary translation", "BridgeRecord"]}));
        m.insert("AP12", json!({"sections": ["62i"],               "key_provides": ["sequenced multi-step operations", "OrchestratorRecord"]}));
        m.insert("AP13", json!({"sections": ["60", "71"],          "key_provides": ["decoupled observation", "broadcast log"]}));
        m.insert("AP14", json!({"sections": ["38", "62l"],         "key_provides": ["crash-safe FIFO input queue", "source_input traceability"]}));
        m.insert("AP15", json!({"sections": ["60"],                "key_provides": ["system-wide event bus", "decoupled pub/sub"]}));
        m.insert("AP16", json!({"sections": ["60", "73"],          "key_provides": ["durable state snapshot", "delta log"]}));
        m.insert("AP17", json!({"sections": ["62a"],               "key_provides": ["spec rule formalization", "formula-linked rule pairs"]}));
        m.insert("AP18", json!({"sections": ["42", "62c"],         "key_provides": ["durable named scheduled tasks", "ScheduledTask citizen"]}));
        m.insert("AP19", json!({"sections": ["62b"],               "key_provides": ["named scoped user overrides", "conflict detection"]}));
        m.insert("AP20", json!({"sections": ["43", "62c"],         "key_provides": ["proactive failure-rate gating", "CLOSED/OPEN/HALF_OPEN"]}));
        m.insert("AP21", json!({"sections": ["62f"],               "key_provides": ["bounded growth", "archive + decompact"]}));
        m.insert("AP22", json!({"sections": ["61", "62c"],         "key_provides": ["accepted-state snapshot", "recovery anchor"]}));
        m.insert("AP23", json!({"sections": ["62g"],               "key_provides": ["reasoning chain traversal", "urace why"]}));
        m.insert("AP24", json!({"sections": ["62j"],               "key_provides": ["DerivedSystemManifest", "zero-conformance guarantee"]}));
        m.insert("AP25", json!({"sections": ["59b", "62c"],        "key_provides": ["capability ceiling", "sweet-spot band"]}));
        m
    })
}

// ---------------------------------------------------------------------------
// Intent-keyword affinity table (r40)
// ---------------------------------------------------------------------------

fn intent_affinity() -> &'static HashMap<&'static str, Vec<&'static str>> {
    static ONCE: OnceLock<HashMap<&'static str, Vec<&'static str>>> = OnceLock::new();
    ONCE.get_or_init(|| {
        let mut m: HashMap<&'static str, Vec<&'static str>> = HashMap::new();
        m.insert("identity",    vec!["AP0", "AP1", "AP2"]);
        m.insert("schema",      vec!["AP0", "AP1", "AP2"]);
        m.insert("log",         vec!["AP3", "AP21"]);
        m.insert("audit",       vec!["AP3", "AP6"]);
        m.insert("compaction",  vec!["AP21"]);
        m.insert("event",       vec!["AP3", "AP13", "AP14", "AP15"]);
        m.insert("queue",       vec!["AP14"]);
        m.insert("publish",     vec!["AP13", "AP15"]);
        m.insert("subscribe",   vec!["AP13", "AP15"]);
        m.insert("bus",         vec!["AP15"]);
        m.insert("retry",       vec!["AP5", "AP10"]);
        m.insert("idempotent",  vec!["AP5"]);
        m.insert("backoff",     vec!["AP10"]);
        m.insert("circuit",     vec!["AP20"]);
        m.insert("resilient",   vec!["AP10", "AP20", "AP22"]);
        m.insert("resilience",  vec!["AP10", "AP20", "AP22"]);
        m.insert("snapshot",    vec!["AP16", "AP22"]);
        m.insert("recovery",    vec!["AP22"]);
        m.insert("checkpoint",  vec!["AP22"]);
        m.insert("observation", vec!["AP13"]);
        m.insert("observe",     vec!["AP13"]);
        m.insert("obligation",  vec!["AP4"]);
        m.insert("contract",    vec!["AP4"]);
        m.insert("constraint",  vec!["AP4", "AP17"]);
        m.insert("authority",   vec!["AP11"]);
        m.insert("bridge",      vec!["AP11"]);
        m.insert("orchestrat",  vec!["AP12"]);
        m.insert("workflow",    vec!["AP12"]);
        m.insert("stagnation",  vec!["AP8"]);
        m.insert("convergence", vec!["AP8"]);
        m.insert("progress",    vec!["AP8"]);
        m.insert("evidence",    vec!["AP9"]);
        m.insert("monot",       vec!["AP9"]);
        m.insert("causal",      vec!["AP6"]);
        m.insert("trace",       vec!["AP6", "AP23"]);
        m.insert("reason",      vec!["AP23"]);
        m.insert("why",         vec!["AP23"]);
        m.insert("dedup",       vec!["AP7"]);
        m.insert("duplicate",   vec!["AP7"]);
        m.insert("schedule",    vec!["AP18"]);
        m.insert("scheduled",   vec!["AP18"]);
        m.insert("override",    vec!["AP19"]);
        m.insert("customiz",    vec!["AP19"]);
        m.insert("derive",      vec!["AP24"]);
        m.insert("manifest",    vec!["AP24"]);
        m.insert("capability",  vec!["AP25"]);
        m.insert("envelope",    vec!["AP25"]);
        m.insert("ceiling",     vec!["AP25"]);
        m.insert("rule",        vec!["AP17"]);
        m.insert("formula",     vec!["AP17"]);
        m.insert("delta",       vec!["AP16"]);
        m.insert("state",       vec!["AP16", "AP22"]);
        m
    })
}

// ---------------------------------------------------------------------------
// Construct-level affinity table (r41)
// ---------------------------------------------------------------------------

fn construct_affinity() -> &'static HashMap<&'static str, Vec<&'static str>> {
    static ONCE: OnceLock<HashMap<&'static str, Vec<&'static str>>> = OnceLock::new();
    ONCE.get_or_init(|| {
        let mut m: HashMap<&'static str, Vec<&'static str>> = HashMap::new();
        m.insert("quality",       vec!["QSM", "QualityDelta", "CheckpointRecord"]);
        m.insert("streak",        vec!["QSM"]);
        m.insert("regression",    vec!["QSM"]);
        m.insert("checkpoint",    vec!["QSM", "CheckpointRecord"]);
        m.insert("maturity",      vec!["SSB", "CEG"]);
        m.insert("sweet",         vec!["SSB"]);
        m.insert("ceiling",       vec!["CEG", "SSB"]);
        m.insert("technique",     vec!["TAG"]);
        m.insert("applicability", vec!["TAG"]);
        m.insert("discovery",     vec!["DCG", "DiscoveryRecord"]);
        m.insert("budget",        vec!["DCG"]);
        m.insert("stagnation",    vec!["PSD"]);
        m.insert("uncertain",     vec!["EUP"]);
        m.insert("indeterminate", vec!["EUP"]);
        m.insert("reconcil",      vec!["EUP"]);
        m.insert("operator",      vec!["OGP"]);
        m.insert("clearance",     vec!["OGP"]);
        m.insert("governing",     vec!["GRC", "PolicyRecord", "HardConstraint"]);
        m.insert("invariant",     vec!["ACI", "HardConstraint"]);
        m.insert("inspection",    vec!["ISC"]);
        m.insert("health",        vec!["ISC"]);
        m.insert("authority",     vec!["ABM", "ACI", "DecisionRecord"]);
        m.insert("revalidat",     vec!["RVS"]);
        m.insert("gap",           vec!["IntegrityGap", "IGC"]);
        m.insert("policy",        vec!["PolicyRecord"]);
        m.insert("constraint",    vec!["HardConstraint"]);
        m.insert("goal",          vec!["GoalRecord"]);
        m.insert("objective",     vec!["ObjectiveRecord"]);
        m.insert("evidence",      vec!["EvidenceRecord"]);
        m.insert("decision",      vec!["DecisionRecord"]);
        m.insert("assessment",    vec!["AssessmentRecord"]);
        m.insert("market",        vec!["MarketSignal", "FitHypothesis"]);
        m.insert("hypothesis",    vec!["FitHypothesis"]);
        m.insert("ownership",     vec!["OwnershipMarker"]);
        m.insert("schedule",      vec!["ScheduledTask"]);
        m.insert("capability",    vec!["CapabilityStatement", "CEG"]);
        m.insert("bridge",        vec!["BridgeRecord"]);
        m.insert("orchestrat",    vec!["OrchestratorRecord"]);
        m.insert("operation",     vec!["OperationRecord"]);
        m.insert("manifest",      vec!["DerivedManifestRef"]);
        m
    })
}

// ---------------------------------------------------------------------------
// Mechanism catalog
// ---------------------------------------------------------------------------

static MECHANISM_CATALOG_ONCE: OnceLock<Vec<Construct>> = OnceLock::new();

fn mechanism_catalog() -> &'static [Construct] {
    MECHANISM_CATALOG_ONCE.get_or_init(|| {
        use serde_json::json;
        vec![
            c(
                "QSM",
                "Quality Streak Mechanism",
                KIND_MECHANISM,
                "Tracks consecutive IMPROVEMENT/REGRESSION quality deltas. Blocks regression acceptance until a CHECKPOINT_ACCEPTANCE DecisionRecord is present.",
                &["quality streak counter", "regression checkpoint gate", "IMPROVEMENT/REGRESSION classification"],
                "§62c",
                true,
                &["AP0", "AP3"],
                json!({}),
            ),
            c(
                "SSB",
                "Sweet-Spot Band",
                KIND_MECHANISM,
                "Classifies product maturity as CAPABLE, OPTIMIZED, or OVER_ENGINEERED by comparing surface area against declared complexity ceiling.",
                &["maturity classification", "over-engineering detection", "sweet-spot target band"],
                "§62c §59b",
                false,
                &["AP25"],
                json!({}),
            ),
            c(
                "CEG",
                "Capability Envelope Gate",
                KIND_MECHANISM,
                "Blocks surface growth beyond the declared capability ceiling when product maturity is CAPABLE or OPTIMIZED.",
                &["ceiling enforcement", "surface growth gate", "capability boundary guard"],
                "§62c",
                false,
                &["AP25"],
                json!({}),
            ),
            c(
                "TAG",
                "Technique Applicability Gate",
                KIND_MECHANISM,
                "Gates technique execution by evaluating named context conditions. Executes only when all preconditions match.",
                &["context-gated execution", "technique precondition check", "applicability scoring"],
                "§62h",
                true,
                &["AP0", "AP1"],
                json!({}),
            ),
            c(
                "DCG",
                "Discovery Credit Gate",
                KIND_MECHANISM,
                "Gates discovery spend against DiscoveryBudgetStatus. Blocks new discovery cycles when budget is EXHAUSTED or SUSPENDED.",
                &["discovery budget enforcement", "credit gate", "spend tracking"],
                "§62e",
                true,
                &["AP0", "AP9"],
                json!({}),
            ),
            c(
                "PSD",
                "Progress Stagnation Detector",
                KIND_MECHANISM,
                "Detects stagnant progress_vector over consecutive cycles. Transitions lifecycle to REPAIRING and emits an IntegrityGap when threshold exceeded.",
                &["stagnation detection", "REPAIRING lifecycle trigger", "progress vector tracking"],
                "§62c",
                false,
                &["AP8"],
                json!({}),
            ),
        ]
    })
}

// ---------------------------------------------------------------------------
// Schema catalog
// ---------------------------------------------------------------------------

static SCHEMA_CATALOG_ONCE: OnceLock<Vec<Construct>> = OnceLock::new();

fn schema_catalog() -> &'static [Construct] {
    SCHEMA_CATALOG_ONCE.get_or_init(|| {
        use serde_json::json;
        vec![
            c(
                "GoalRecord",
                "GoalRecord",
                KIND_SCHEMA,
                "Named, scoped goal with priority. Primary unit of operator intent.",
                &["goal identity", "scope assignment", "priority ordering"],
                "§39",
                true,
                &[],
                json!({"required_fields": ["id","title","description","scope","priority","status"], "id_prefix": "goal-"}),
            ),
            c(
                "ObjectiveRecord",
                "ObjectiveRecord",
                KIND_SCHEMA,
                "Bounded work unit derived from a Goal. Carries authority resolution result and scope.",
                &["objective identity", "authority resolution link", "scope boundary"],
                "§40",
                false,
                &[],
                json!({"required_fields": ["id","title","scope","status","goal_id"], "id_prefix": "obj-"}),
            ),
            c(
                "PlanRecord",
                "PlanRecord",
                KIND_SCHEMA,
                "Execution plan with ordered steps, linked to an Objective.",
                &["plan identity", "step sequencing", "objective linkage"],
                "§41",
                false,
                &[],
                json!({"required_fields": ["id","objective_id","steps","status"], "id_prefix": "plan-"}),
            ),
            c(
                "EvidenceRecord",
                "EvidenceRecord",
                KIND_SCHEMA,
                "Evidence item with kind, value, source, and confidence. Primary factual grounding unit.",
                &["evidence identity", "typed evidence values", "confidence tracking"],
                "§44",
                true,
                &[],
                json!({"required_fields": ["id","kind","value","source","confidence","at"], "id_prefix": "ev-"}),
            ),
            c(
                "DecisionRecord",
                "DecisionRecord",
                KIND_SCHEMA,
                "Authoritative decision with basis, outcome, and authority link. All consequential choices must be recorded.",
                &["decision identity", "basis traceability", "authority linkage"],
                "§55",
                true,
                &[],
                json!({"required_fields": ["id","kind","outcome","basis","at"], "id_prefix": "dec-"}),
            ),
            c(
                "PolicyRecord",
                "PolicyRecord",
                KIND_SCHEMA,
                "Named policy with conditions and actions. Governs behavior within declared scope. Implements GoverningRecord.",
                &["policy identity", "condition-action contract", "GoverningRecord provenance"],
                "§72",
                true,
                &[],
                json!({"required_fields": ["id","authority_basis","scope","established_at","kind","status","name","conditions","actions"], "id_prefix": "pol-"}),
            ),
            c(
                "HardConstraint",
                "HardConstraint",
                KIND_SCHEMA,
                "Inviolable constraint with enforcement mode. Never weakened autonomously. Implements GoverningRecord.",
                &["constraint identity", "enforcement contract", "GoverningRecord provenance"],
                "§72",
                true,
                &[],
                json!({"required_fields": ["id","authority_basis","scope","established_at","name","description","enforcement"], "id_prefix": "hco-"}),
            ),
            c(
                "AssessmentRecord",
                "AssessmentRecord",
                KIND_SCHEMA,
                "Assessment cycle record tracking what was evaluated, scores, and outcomes.",
                &["assessment identity", "cycle tracking", "score recording"],
                "§37",
                true,
                &[],
                json!({"required_fields": ["id","cycle_id","assessed_at","status","scores"], "id_prefix": "asr-"}),
            ),
            c(
                "DiscoveryRecord",
                "DiscoveryRecord",
                KIND_SCHEMA,
                "Discovery cycle record with budget tracking and signal outcomes.",
                &["discovery identity", "cycle status", "credit tracking"],
                "§36",
                true,
                &[],
                json!({"required_fields": ["id","started_at","status","credits_used"], "id_prefix": "dsc-"}),
            ),
            c(
                "MarketSignal",
                "MarketSignal",
                KIND_SCHEMA,
                "Typed market signal with strength and source. Feeds product-market fit assessment.",
                &["signal identity", "typed market data", "strength measurement"],
                "§59",
                true,
                &[],
                json!({"required_fields": ["id","kind","strength","source","observed_at"], "id_prefix": "mks-"}),
            ),
            c(
                "FitHypothesis",
                "FitHypothesis",
                KIND_SCHEMA,
                "Product-market fit hypothesis with confidence and validation lifecycle.",
                &["hypothesis identity", "confidence tracking", "validation lifecycle"],
                "§59",
                true,
                &[],
                json!({"required_fields": ["id","description","confidence","status","created_at"], "id_prefix": "fhy-"}),
            ),
            c(
                "OwnershipMarker",
                "OwnershipMarker",
                KIND_SCHEMA,
                "Ownership assignment for a named scope with concurrency policy.",
                &["ownership identity", "scope assignment", "concurrency contract"],
                "§63",
                true,
                &[],
                json!({"required_fields": ["id","scope","owner_id","acquired_at","concurrency_policy"], "id_prefix": "omk-"}),
            ),
            c(
                "ScheduledTask",
                "ScheduledTask",
                KIND_SCHEMA,
                "Named, durable scheduled task with cron expression and execution contract.",
                &["task identity", "schedule expression", "execution history"],
                "§42",
                true,
                &[],
                json!({"required_fields": ["id","name","schedule","action","status"], "id_prefix": "sched-"}),
            ),
            c(
                "QualityDelta",
                "QualityDelta",
                KIND_SCHEMA,
                "Quality measurement delta with direction (IMPROVEMENT/REGRESSION/NEUTRAL) and magnitude.",
                &["quality measurement identity", "direction classification", "magnitude tracking"],
                "§61",
                true,
                &[],
                json!({"required_fields": ["id","direction","magnitude","scope","at"], "id_prefix": "qdelta-"}),
            ),
            c(
                "IntegrityGap",
                "IntegrityGap",
                KIND_SCHEMA,
                "Integrity gap record with kind (from IntegrityGapCatalog), severity, and resolution status.",
                &["gap identity", "severity classification", "resolution tracking"],
                "§62l",
                true,
                &[],
                json!({"required_fields": ["id","kind","severity","detail","at","resolved"], "id_prefix": "igap-"}),
            ),
            c(
                "CapabilityStatement",
                "CapabilityStatement",
                KIND_SCHEMA,
                "Named capability declaration with tier, value weight, and maturity status.",
                &["capability identity", "tier classification", "value weighting"],
                "§59b",
                true,
                &[],
                json!({"required_fields": ["id","name","scope","tier","value_weight","status"], "id_prefix": "cap-"}),
            ),
            c(
                "OperationRecord",
                "OperationRecord",
                KIND_SCHEMA,
                "Execution operation record with PENDING→ACCEPTED/REJECTED lifecycle and executor attribution.",
                &["operation identity", "status lifecycle", "executor attribution"],
                "§53",
                false,
                &[],
                json!({"required_fields": ["id","objective_id","plan_id","status","executor_id","at"], "id_prefix": "op-"}),
            ),
            c(
                "BridgeRecord",
                "BridgeRecord",
                KIND_SCHEMA,
                "Authority boundary translation record. Documents crossing from one authority scope to another.",
                &["bridge identity", "authority translation audit", "scope crossing traceability"],
                "§62i AP11",
                false,
                &[],
                json!({"required_fields": ["id","from_scope","to_scope","authority_basis","at"], "id_prefix": "brd-"}),
            ),
            c(
                "OrchestratorRecord",
                "OrchestratorRecord",
                KIND_SCHEMA,
                "Multi-step operation orchestration record. Sequences dependent sub-operations with state tracking.",
                &["orchestration identity", "step sequencing", "sub-operation tracking"],
                "§62i AP12",
                false,
                &[],
                json!({"required_fields": ["id","name","steps","status","at"], "id_prefix": "orch-"}),
            ),
            c(
                "CheckpointRecord",
                "CheckpointRecord",
                KIND_SCHEMA,
                "Accepted-state snapshot. Recovery anchor for rollback. Produced by the quality checkpoint gate.",
                &["checkpoint identity", "state digest", "recovery anchor"],
                "§61",
                false,
                &[],
                json!({"required_fields": ["id","at","kind","digest"], "id_prefix": "checkpoint-"}),
            ),
            c(
                "DerivedManifestRef",
                "DerivedManifestRef",
                KIND_SCHEMA,
                "Reference to a saved DerivedSystemManifest. Enables stale-manifest detection across spec version bumps.",
                &["manifest reference identity", "spec version tracking", "stale detection anchor"],
                "§62j",
                true,
                &[],
                json!({"required_fields": ["id","manifest_id","spec_version","generated_at","adopted_pattern_ids","intent"], "id_prefix": "dmr-"}),
            ),
        ]
    })
}

// ---------------------------------------------------------------------------
// Protocol catalog
// ---------------------------------------------------------------------------

static PROTOCOL_CATALOG_ONCE: OnceLock<Vec<Construct>> = OnceLock::new();

fn protocol_catalog() -> &'static [Construct] {
    PROTOCOL_CATALOG_ONCE.get_or_init(|| {
        use serde_json::json;
        vec![
            c(
                "EUP",
                "EffectUncertaintyProtocol",
                KIND_PROTOCOL,
                "3-step protocol for INDETERMINATE effect handling: classify → hold before retry → preserve durable record.",
                &["INDETERMINATE classification", "reconciliation gate", "durable unresolved-effect record"],
                "§62l",
                true,
                &["AP5", "AP6"],
                json!({"steps": [
                    "Classify effect as INDETERMINATE when outcome cannot be confirmed",
                    "Hold state — do not retry until effect is reconciled",
                    "Preserve durable UnresolvedEffect record for operator review",
                ]}),
            ),
            c(
                "OGP",
                "OperatorGateProtocol",
                KIND_PROTOCOL,
                "4-clause protocol: surface BLOCKING gap → hold state → await authenticated clearance → emit durable gate event.",
                &["operator gate blocking", "clearance lifecycle", "gate event audit"],
                "§62l",
                true,
                &["AP0", "AP6"],
                json!({"steps": [
                    "Surface a named BLOCKING IntegrityGap with condition_kind",
                    "Hold all dependent state mutations until clearance",
                    "Await authenticated operator clearance (DecisionRecord kind=OPERATOR_CLEARANCE)",
                    "Emit durable gate event and resolve the gap",
                ]}),
            ),
        ]
    })
}

// ---------------------------------------------------------------------------
// Contract catalog
// ---------------------------------------------------------------------------

static CONTRACT_CATALOG_ONCE: OnceLock<Vec<Construct>> = OnceLock::new();

fn contract_catalog() -> &'static [Construct] {
    CONTRACT_CATALOG_ONCE.get_or_init(|| {
        use serde_json::json;
        vec![
            c(
                "GRC",
                "GoverningRecord",
                KIND_CONTRACT,
                "Canonical cluster for citizens that establish authoritative boundaries. Requires: id, authority_basis, scope, established_at.",
                &["governance provenance", "authority-basis traceability", "scope declaration", "establishment timestamp"],
                "§62l",
                true,
                &[],
                json!({"invariants": [
                    "authority_basis must be non-empty string",
                    "scope must be non-empty string",
                    "established_at must be ISO-8601 timestamp",
                ], "applies_to": ["PolicyRecord", "HardConstraint"]}),
            ),
            c(
                "IGC",
                "IntegrityGapCatalog",
                KIND_CONTRACT,
                "20 named gap kinds each with canonical severity. All IntegrityGap emissions MUST use a registered kind from this catalog.",
                &["named gap vocabulary", "canonical severity assignment", "gap kind registry"],
                "§62l",
                true,
                &[],
                json!({"gap_count": 20}),
            ),
            c(
                "ISC",
                "InspectionSurface",
                KIND_CONTRACT,
                "11-category output contract for system health inspection. Any check endpoint SHOULD conform to this schema.",
                &["structured health output", "blocking/warning gap separation", "summary field"],
                "§62l",
                true,
                &[],
                json!({"categories": [
                    "lifecycle_state", "assessed_at", "blocking_gaps", "warning_gaps",
                    "indeterminate_effects", "operator_gates", "stale_items",
                    "capability_readiness", "scheduled_conditions",
                    "policy_violations", "open_pending_validations", "summary",
                ]}),
            ),
            c(
                "ACI",
                "AuthorityClosureInvariant",
                KIND_CONTRACT,
                "Enumerates all non-Authority input sources. Actions solely driven by these sources must never be treated as authority-driven.",
                &["non-authority source enumeration", "closure check", "authority boundary guard"],
                "§62l",
                true,
                &[],
                json!({"non_authority_sources": [
                    "evidence", "priority", "capability", "market_signal", "trigger",
                    "schedule", "executor_recommendation", "product_value", "user_absence", "market_success",
                ]}),
            ),
            c(
                "RVS",
                "RevalidationScope",
                KIND_CONTRACT,
                "Maps change-class triggers to DECISION_ONLY | DEPENDENT_PLANS | FULL_LIFECYCLE scope. Governs how much of the lifecycle must be revalidated after a premise change.",
                &["revalidation scope mapping", "trigger classification", "minimum revalidation contract"],
                "§62l",
                true,
                &[],
                json!({"scopes": ["DECISION_ONLY", "DEPENDENT_PLANS", "FULL_LIFECYCLE"]}),
            ),
            c(
                "ABM",
                "AuthorityBoundaryModel",
                KIND_CONTRACT,
                "Delegated/reserved authority boundary with typed scope-to-authority-category mapping. Enforced at every objective evaluation.",
                &["delegated authority categories", "reserved decision enumeration", "scope-to-authority mapping"],
                "§14-16",
                true,
                &[],
                json!({"invariants": [
                    "reserved decisions are never autonomously executed",
                    "scope must map to delegated categories",
                    "constraint-weakening verbs trigger REQUIRES_AUTHORITATIVE_DECISION",
                ]}),
            ),
        ]
    })
}

// ---------------------------------------------------------------------------
// Unified construct catalog (_build_construct_catalog equivalent)
// ---------------------------------------------------------------------------

static CONSTRUCT_CATALOG_ONCE: OnceLock<Vec<Construct>> = OnceLock::new();

pub fn construct_catalog() -> &'static [Construct] {
    CONSTRUCT_CATALOG_ONCE.get_or_init(|| {
        let mut catalog: Vec<Construct> = Vec::new();
        // Patterns first
        for pat in pattern_catalog() {
            catalog.push(Construct {
                id: pat.id.clone(),
                name: pat.name.clone(),
                kind: KIND_PATTERN.to_string(),
                summary: pat.summary.clone(),
                provides: pat.provides.clone(),
                spec_section: pat.spec_section.clone(),
                standalone: pat.standalone,
                requires_patterns: pat.requires.clone(),
                extra: serde_json::json!({"tier": pat.tier, "requires": pat.requires}),
            });
        }
        for entry in mechanism_catalog() { catalog.push(entry.clone()); }
        for entry in schema_catalog()    { catalog.push(entry.clone()); }
        for entry in protocol_catalog()  { catalog.push(entry.clone()); }
        for entry in contract_catalog()  { catalog.push(entry.clone()); }
        catalog
    })
}

/// Return all construct IDs, optionally filtered to the given kinds.
pub fn all_construct_ids(kinds: Option<&[&str]>) -> Vec<String> {
    let filter: Option<HashSet<&str>> = kinds.map(|ks| ks.iter().copied().collect());
    construct_catalog()
        .iter()
        .filter(|e| {
            filter
                .as_ref()
                .map_or(true, |f| f.contains(e.kind.as_str()))
        })
        .map(|e| e.id.clone())
        .collect()
}

// ---------------------------------------------------------------------------
// Private: affinity match scoring
// ---------------------------------------------------------------------------

fn affinity_match(
    tokens: &HashSet<String>,
    cid: &str,
    maps: &[&HashMap<&'static str, Vec<&'static str>>],
) -> f64 {
    let mut score = 0.0_f64;
    for amap in maps {
        for (stem, ids) in amap.iter() {
            if ids.contains(&cid) {
                let hit = tokens.iter().any(|tok| {
                    tok.contains(*stem)
                        || (tok.len() > 3 && stem.contains(tok.as_str()))
                });
                if hit {
                    score += 2.0;
                }
            }
        }
    }
    score
}

fn tokenise(text: &str) -> HashSet<String> {
    text.split(|c: char| !c.is_alphanumeric())
        .filter(|w| w.len() > 2)
        .map(|w| w.to_lowercase())
        .collect()
}

// ---------------------------------------------------------------------------
// resolve_dependencies
// ---------------------------------------------------------------------------

/// Resolve transitive dependencies for a set of pattern IDs.
///
/// Returns `(resolved_ids, resolution_log)` where `resolved_ids` is sorted
/// FOUNDATIONAL first (topological), and `resolution_log` explains each
/// transitively added entry.
pub fn resolve_dependencies(
    pattern_ids: &[&str],
    excluded_ids: Option<&HashSet<String>>,
) -> Result<(Vec<String>, Vec<String>), PatternError> {
    let catalog = pattern_catalog();
    let catalog_index: HashMap<&str, &Pattern> =
        catalog.iter().map(|p| (p.id.as_str(), p)).collect();

    let empty_set = HashSet::new();
    let excluded: &HashSet<String> = excluded_ids.unwrap_or(&empty_set);

    let mut resolved: Vec<String> = Vec::new();
    let mut log: Vec<String> = Vec::new();
    let mut queue: std::collections::VecDeque<String> =
        pattern_ids.iter().map(|s| s.to_string()).collect();
    let mut seen: HashSet<String> = HashSet::new();
    let explicit_set: HashSet<String> = pattern_ids.iter().map(|s| s.to_string()).collect();

    while let Some(pid) = queue.pop_front() {
        if seen.contains(&pid) || excluded.contains(&pid) {
            continue;
        }
        let entry = catalog_index.get(pid.as_str()).ok_or_else(|| {
            let valid = {
                let mut ids: Vec<&str> = catalog_index.keys().copied().collect();
                ids.sort_unstable();
                ids.join(", ")
            };
            PatternError::UnknownPattern(pid.clone(), valid)
        })?;
        seen.insert(pid.clone());
        resolved.push(pid.clone());
        for dep in &entry.requires {
            if !seen.contains(dep) && !excluded.contains(dep) {
                if !explicit_set.contains(dep) {
                    log.push(format!("{dep} added transitively (required by {pid})"));
                }
                queue.push_back(dep.clone());
            }
        }
    }

    // Topological sort: FOUNDATIONAL < COMPOSITIONAL < INTEGRATED
    let tier_order = |tier: &str| match tier {
        FOUNDATIONAL => 0u8,
        COMPOSITIONAL => 1,
        _ => 2,
    };
    resolved.sort_by_key(|pid| {
        let t = catalog_index
            .get(pid.as_str())
            .map_or(2, |e| tier_order(&e.tier));
        (t, pid.clone())
    });

    Ok((resolved, log))
}

// ---------------------------------------------------------------------------
// Digest helper (SHA-256 of canonical JSON, first 16 hex chars)
// ---------------------------------------------------------------------------

fn entry_digest(value: &serde_json::Value) -> String {
    let canonical = serde_json::to_string(value).unwrap_or_default();
    let hash = Sha256::digest(canonical.as_bytes());
    hex::encode(hash)[..16].to_string()
}

fn manifest_digest(adopted: &[serde_json::Value], intent: &str) -> String {
    let payload = serde_json::json!({
        "intent": intent,
        "adopted": adopted,
    });
    let canonical = serde_json::to_string(&payload).unwrap_or_default();
    let hash = Sha256::digest(canonical.as_bytes());
    hex::encode(hash)
}

// ---------------------------------------------------------------------------
// build_derived_manifest
// ---------------------------------------------------------------------------

/// Build a `DerivedSystemManifest` JSON value.
///
/// Fields: `intent`, `adopted_patterns`, `capability_summary`,
/// `tier_breakdown`, `digest`, plus metadata fields.
pub fn build_derived_manifest(
    pattern_ids: &[&str],
    intent: &str,
    catalog: &[Pattern],
) -> Result<serde_json::Value, PatternError> {
    let catalog_index: HashMap<&str, &Pattern> =
        catalog.iter().map(|p| (p.id.as_str(), p)).collect();

    let explicit_set: HashSet<String> = pattern_ids.iter().map(|s| s.to_string()).collect();
    let (resolved, resolution_log) = resolve_dependencies(pattern_ids, None)?;

    let mut adopted: Vec<serde_json::Value> = Vec::new();
    for pid in &resolved {
        let entry = catalog_index.get(pid.as_str()).ok_or_else(|| {
            PatternError::UnknownPattern(pid.clone(), String::new())
        })?;
        adopted.push(serde_json::json!({
            "pattern_id": pid,
            "name": entry.name,
            "adoption": if explicit_set.contains(pid) { EXPLICIT } else { TRANSITIVE },
            "tier": entry.tier,
            "provides": entry.provides,
        }));
    }

    // tier_breakdown
    let mut tier_breakdown: HashMap<String, usize> = HashMap::new();
    for a in &adopted {
        let tier = a["tier"].as_str().unwrap_or("UNKNOWN").to_string();
        *tier_breakdown.entry(tier).or_insert(0) += 1;
    }

    // capability_summary: flat deduplicated list of provides strings
    let mut caps: Vec<String> = adopted
        .iter()
        .flat_map(|a| {
            a["provides"]
                .as_array()
                .unwrap_or(&vec![])
                .iter()
                .filter_map(|v| v.as_str().map(|s| s.to_string()))
                .collect::<Vec<_>>()
        })
        .collect();
    caps.dedup();

    let digest = manifest_digest(&adopted, intent);

    Ok(serde_json::json!({
        "intent": intent,
        "adopted_patterns": adopted,
        "capability_summary": caps,
        "tier_breakdown": tier_breakdown,
        "resolution_log": resolution_log,
        "digest": digest,
    }))
}

// ---------------------------------------------------------------------------
// render_manifest_human
// ---------------------------------------------------------------------------

/// Human-readable text summary of a `DerivedSystemManifest` value.
pub fn render_manifest_human(manifest: &serde_json::Value) -> String {
    let mut lines: Vec<String> = Vec::new();

    let intent = manifest["intent"].as_str().unwrap_or("");
    let digest = manifest["digest"].as_str().unwrap_or("");
    lines.push(format!("DerivedSystemManifest"));
    lines.push(format!("  intent:   {intent}"));
    lines.push(format!("  digest:   {digest}"));
    lines.push(String::new());

    if let Some(adopted) = manifest["adopted_patterns"].as_array() {
        lines.push(format!("Adopted patterns ({}):", adopted.len()));
        for rec in adopted {
            let pid = rec["pattern_id"].as_str().unwrap_or("");
            let name = rec["name"].as_str().unwrap_or("");
            let adoption = rec["adoption"].as_str().unwrap_or("");
            let tier = rec["tier"].as_str().unwrap_or("");
            let tag = if adoption == EXPLICIT {
                "[explicit]"
            } else {
                "[transitive]"
            };
            lines.push(format!("  {pid:<5}  {name:<45}  {tag} ({tier})"));
            if let Some(provides) = rec["provides"].as_array() {
                for cap in provides {
                    lines.push(format!("         + {}", cap.as_str().unwrap_or("")));
                }
            }
        }
    }

    if let Some(rl) = manifest["resolution_log"].as_array() {
        if !rl.is_empty() {
            lines.push(String::new());
            lines.push("Dependency resolution:".to_string());
            for entry in rl {
                lines.push(format!("  + {}", entry.as_str().unwrap_or("")));
            }
        }
    }

    lines.join("\n")
}

// ---------------------------------------------------------------------------
// suggest_patterns_from_intent
// ---------------------------------------------------------------------------

/// Rank patterns by keyword + affinity overlap with the intent string.
/// Returns up to `top_n` entries sorted descending by score.
pub fn suggest_patterns_from_intent(intent: &str, top_n: usize) -> Vec<serde_json::Value> {
    let tokens = tokenise(intent);
    if tokens.is_empty() {
        return vec![];
    }

    let aff = intent_affinity();
    let catalog = pattern_catalog();

    let mut scores: Vec<(f64, &Pattern)> = catalog
        .iter()
        .filter_map(|pat| {
            let text = format!(
                "{} {} {}",
                pat.name,
                pat.summary,
                pat.provides.join(" ")
            )
            .to_lowercase();
            let kw_score = tokens.iter().filter(|t| text.contains(t.as_str())).count() as f64;
            let aff_score = affinity_match(&tokens, &pat.id, &[aff]);
            let total = kw_score + aff_score;
            if total > 0.0 {
                Some((total, pat))
            } else {
                None
            }
        })
        .collect();

    scores.sort_by(|a, b| b.0.partial_cmp(&a.0).unwrap_or(std::cmp::Ordering::Equal).then(a.1.id.cmp(&b.1.id)));

    scores
        .into_iter()
        .take(top_n)
        .map(|(score, pat)| {
            serde_json::json!({
                "pattern_id": pat.id,
                "name": pat.name,
                "tier": pat.tier,
                "score": score,
                "summary": pat.summary,
            })
        })
        .collect()
}

// ---------------------------------------------------------------------------
// patterns_from_goals
// ---------------------------------------------------------------------------

/// Aggregate pattern suggestions across all goal titles/descriptions.
pub fn patterns_from_goals(goals: &[serde_json::Value], top_n: usize) -> Vec<serde_json::Value> {
    let mut combined: HashMap<String, f64> = HashMap::new();
    for goal in goals {
        let text = format!(
            "{} {} {}",
            goal["title"].as_str().unwrap_or(""),
            goal["description"].as_str().unwrap_or(""),
            goal["scope"].as_str().unwrap_or(""),
        );
        for entry in suggest_patterns_from_intent(&text, top_n + 10) {
            let pid = entry["pattern_id"].as_str().unwrap_or("").to_string();
            let score = entry["score"].as_f64().unwrap_or(0.0);
            *combined.entry(pid).or_insert(0.0) += score;
        }
    }

    let catalog = pattern_catalog();
    let catalog_index: HashMap<&str, &Pattern> =
        catalog.iter().map(|p| (p.id.as_str(), p)).collect();

    let mut ranked: Vec<(f64, String)> = combined.into_iter().map(|(k, v)| (v, k)).collect();
    ranked.sort_by(|a, b| b.0.partial_cmp(&a.0).unwrap_or(std::cmp::Ordering::Equal).then(a.1.cmp(&b.1)));

    ranked
        .into_iter()
        .take(top_n)
        .filter_map(|(score, pid)| {
            catalog_index.get(pid.as_str()).map(|pat| {
                serde_json::json!({
                    "pattern_id": pid,
                    "name": pat.name,
                    "tier": pat.tier,
                    "score": score,
                    "summary": pat.summary,
                })
            })
        })
        .collect()
}

// ---------------------------------------------------------------------------
// suggest_constructs_from_intent
// ---------------------------------------------------------------------------

/// Rank constructs across all kinds by keyword + affinity overlap with intent.
pub fn suggest_constructs_from_intent(
    intent: &str,
    kinds: Option<&[&str]>,
    top_n: usize,
) -> Vec<serde_json::Value> {
    let tokens = tokenise(intent);
    if tokens.is_empty() {
        return vec![];
    }

    let filter: Option<HashSet<&str>> = kinds.map(|ks| ks.iter().copied().collect());
    let caff = construct_affinity();
    let iaff = intent_affinity();

    let mut scores: Vec<(f64, &Construct)> = construct_catalog()
        .iter()
        .filter(|e| filter.as_ref().map_or(true, |f| f.contains(e.kind.as_str())))
        .filter_map(|e| {
            let steps_text = e.extra["steps"]
                .as_array()
                .map(|arr| arr.iter().filter_map(|v| v.as_str()).collect::<Vec<_>>().join(" "))
                .unwrap_or_default();
            let invariants_text = e.extra["invariants"]
                .as_array()
                .map(|arr| arr.iter().filter_map(|v| v.as_str()).collect::<Vec<_>>().join(" "))
                .unwrap_or_default();
            let text = format!(
                "{} {} {} {} {}",
                e.name,
                e.summary,
                e.provides.join(" "),
                steps_text,
                invariants_text,
            )
            .to_lowercase();
            let kw_score = tokens.iter().filter(|t| text.contains(t.as_str())).count() as f64;
            let aff_maps: Vec<&HashMap<&'static str, Vec<&'static str>>> =
                if e.kind == KIND_PATTERN {
                    vec![iaff, caff]
                } else {
                    vec![caff]
                };
            let aff_score = affinity_match(&tokens, &e.id, &aff_maps);
            let total = kw_score + aff_score;
            if total > 0.0 { Some((total, e)) } else { None }
        })
        .collect();

    scores.sort_by(|a, b| b.0.partial_cmp(&a.0).unwrap_or(std::cmp::Ordering::Equal).then(a.1.id.cmp(&b.1.id)));

    scores
        .into_iter()
        .take(top_n)
        .map(|(score, e)| {
            serde_json::json!({
                "construct_id": e.id,
                "name": e.name,
                "kind": e.kind,
                "score": score,
                "summary": e.summary,
            })
        })
        .collect()
}

// ---------------------------------------------------------------------------
// build_derived_construct_set
// ---------------------------------------------------------------------------

/// Build a `DerivedConstructSet` for the given construct IDs (any kind, or mixed).
pub fn build_derived_construct_set(
    construct_ids: &[&str],
    intent: &str,
) -> Result<serde_json::Value, PatternError> {
    let catalog = construct_catalog();
    let catalog_index: HashMap<&str, &Construct> =
        catalog.iter().map(|e| (e.id.as_str(), e)).collect();

    let unknown: Vec<&str> = construct_ids
        .iter()
        .copied()
        .filter(|id| !catalog_index.contains_key(id))
        .collect();
    if !unknown.is_empty() {
        return Err(PatternError::UnknownConstruct(unknown.join(", ")));
    }

    let adopted: Vec<serde_json::Value> = construct_ids
        .iter()
        .map(|cid| {
            let e = catalog_index[cid];
            serde_json::json!({
                "construct_id": cid,
                "name": e.name,
                "kind": e.kind,
                "summary": e.summary,
                "provides": e.provides,
                "spec_section": e.spec_section,
            })
        })
        .collect();

    let kinds_present: Vec<String> = {
        let mut ks: Vec<String> = adopted
            .iter()
            .filter_map(|a| a["kind"].as_str().map(|s| s.to_string()))
            .collect::<HashSet<_>>()
            .into_iter()
            .collect();
        ks.sort();
        ks
    };

    let digest_val = serde_json::json!({"intent": intent, "constructs": construct_ids});
    let canonical = serde_json::to_string(&digest_val).unwrap_or_default();
    let hash = Sha256::digest(canonical.as_bytes());
    let digest = hex::encode(hash);

    Ok(serde_json::json!({
        "intent": intent,
        "adopted_constructs": adopted,
        "kinds_present": kinds_present,
        "digest": digest,
    }))
}

// ---------------------------------------------------------------------------
// render_construct_set_human
// ---------------------------------------------------------------------------

/// Human-readable text summary of a `DerivedConstructSet` value.
pub fn render_construct_set_human(cset: &serde_json::Value) -> String {
    let mut lines: Vec<String> = Vec::new();
    let intent = cset["intent"].as_str().unwrap_or("");
    let kinds = cset["kinds_present"]
        .as_array()
        .map(|a| {
            a.iter()
                .filter_map(|v| v.as_str())
                .collect::<Vec<_>>()
                .join(", ")
        })
        .unwrap_or_default();

    lines.push(format!("DerivedConstructSet"));
    lines.push(format!("  intent:  {intent}"));
    lines.push(format!("  kinds:   {kinds}"));
    lines.push(String::new());

    let empty_arr = vec![];
    let adopted = cset["adopted_constructs"]
        .as_array()
        .unwrap_or(&empty_arr);
    lines.push(format!("Adopted constructs ({}):", adopted.len()));

    // group by kind
    let mut by_kind: HashMap<&str, Vec<&serde_json::Value>> = HashMap::new();
    for rec in adopted {
        let kind = rec["kind"].as_str().unwrap_or("unknown");
        by_kind.entry(kind).or_default().push(rec);
    }
    let mut kind_keys: Vec<&str> = by_kind.keys().copied().collect();
    kind_keys.sort();
    for kind in kind_keys {
        lines.push(format!("\n  [{}]", kind.to_uppercase()));
        for rec in &by_kind[kind] {
            let cid = rec["construct_id"].as_str().unwrap_or("");
            let name = rec["name"].as_str().unwrap_or("");
            let summary = rec["summary"].as_str().unwrap_or("");
            lines.push(format!("    {cid:<16}  {name}"));
            lines.push(format!("    {:<16}  {summary}", ""));
            if let Some(provides) = rec["provides"].as_array() {
                for p in provides {
                    lines.push(format!("    {:<16}  + {}", "", p.as_str().unwrap_or("")));
                }
            }
        }
    }

    lines.join("\n")
}

// ---------------------------------------------------------------------------
// Digest helpers (public, r46 equivalent)
// ---------------------------------------------------------------------------

/// SHA-256 digest (first 16 hex chars) of a pattern entry.
pub fn pattern_entry_digest(pat: &Pattern) -> String {
    let val = serde_json::json!({
        "name": pat.name,
        "provides": pat.provides,
        "tier": pat.tier,
        "requires": pat.requires,
        "spec_section": pat.spec_section,
    });
    entry_digest(&val)
}

/// SHA-256 digest (first 16 hex chars) of a construct entry.
pub fn construct_entry_digest(con: &Construct) -> String {
    let val = serde_json::json!({
        "name": con.name,
        "summary": con.summary,
        "provides": con.provides,
        "spec_section": con.spec_section,
    });
    entry_digest(&val)
}

/// Return `{id: digest}` for all given pattern IDs present in the catalog.
pub fn pattern_digests_for_ids(ids: &[&str]) -> HashMap<String, String> {
    let catalog = pattern_catalog();
    let catalog_index: HashMap<&str, &Pattern> =
        catalog.iter().map(|p| (p.id.as_str(), p)).collect();
    ids.iter()
        .filter_map(|id| catalog_index.get(id).map(|p| (id.to_string(), pattern_entry_digest(p))))
        .collect()
}

/// Return `{id: digest}` for all given construct IDs present in the catalog.
pub fn construct_digests_for_ids(ids: &[&str]) -> HashMap<String, String> {
    let catalog = construct_catalog();
    let catalog_index: HashMap<&str, &Construct> =
        catalog.iter().map(|e| (e.id.as_str(), e)).collect();
    ids.iter()
        .filter_map(|id| catalog_index.get(id).map(|e| (id.to_string(), construct_entry_digest(e))))
        .collect()
}

/// Return IDs where the saved digest differs from the current computed digest.
pub fn diff_pattern_digests(saved: &HashMap<String, String>, ids: &[&str]) -> Vec<String> {
    let current = pattern_digests_for_ids(ids);
    ids.iter()
        .filter(|id| {
            let id_s = id.to_string();
            saved.get(&id_s).map_or(false, |s| {
                current.get(&id_s).map_or(true, |c| c != s)
            })
        })
        .map(|id| id.to_string())
        .collect()
}

/// Return IDs where the saved digest differs from the current computed digest.
pub fn diff_construct_digests(saved: &HashMap<String, String>, ids: &[&str]) -> Vec<String> {
    let current = construct_digests_for_ids(ids);
    ids.iter()
        .filter(|id| {
            let id_s = id.to_string();
            saved.get(&id_s).map_or(false, |s| {
                current.get(&id_s).map_or(true, |c| c != s)
            })
        })
        .map(|id| id.to_string())
        .collect()
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn pattern_catalog_has_exactly_25_entries() {
        let catalog = pattern_catalog();
        assert_eq!(catalog.len(), 25, "Expected AP0-AP24 (25 entries)");
        // Verify IDs are AP0..AP24
        for (i, pat) in catalog.iter().enumerate() {
            assert_eq!(pat.id, format!("AP{i}"), "Entry {i} has wrong id: {}", pat.id);
        }
    }

    #[test]
    fn all_pattern_ids_returns_25() {
        let ids = all_pattern_ids();
        assert_eq!(ids.len(), 25);
        assert!(ids.contains(&"AP0"));
        assert!(ids.contains(&"AP24"));
    }

    #[test]
    fn resolve_dependencies_ap2_includes_ap0_ap1() {
        let catalog = pattern_catalog();
        let (resolved, _log) =
            resolve_dependencies(&["AP2"], None).expect("resolve should succeed");
        assert!(
            resolved.contains(&"AP0".to_string()),
            "AP0 must be in resolved: {resolved:?}"
        );
        assert!(
            resolved.contains(&"AP1".to_string()),
            "AP1 must be in resolved: {resolved:?}"
        );
        assert!(
            resolved.contains(&"AP2".to_string()),
            "AP2 itself must be in resolved: {resolved:?}"
        );
        // Foundational entries come before AP2
        let idx_ap0 = resolved.iter().position(|x| x == "AP0").unwrap();
        let idx_ap1 = resolved.iter().position(|x| x == "AP1").unwrap();
        let idx_ap2 = resolved.iter().position(|x| x == "AP2").unwrap();
        assert!(idx_ap0 < idx_ap2, "AP0 should sort before AP2");
        assert!(idx_ap1 < idx_ap2, "AP1 should sort before AP2");
        let _ = catalog; // silence unused warning
    }

    #[test]
    fn suggest_patterns_from_intent_identity_schema() {
        let results = suggest_patterns_from_intent("identity schema", 3);
        assert!(!results.is_empty(), "Expected non-empty suggestions for 'identity schema'");
        // AP0, AP1, AP2 should all score
        let ids: Vec<&str> = results
            .iter()
            .filter_map(|v| v["pattern_id"].as_str())
            .collect();
        assert!(
            ids.iter().any(|id| ["AP0", "AP1", "AP2"].contains(id)),
            "Expected AP0/AP1/AP2 in top-3 for 'identity schema', got {ids:?}"
        );
    }

    #[test]
    fn build_derived_manifest_non_empty() {
        let catalog = pattern_catalog();
        let manifest =
            build_derived_manifest(&["AP0", "AP2"], "test intent", catalog)
                .expect("manifest should build");
        assert!(manifest.is_object(), "manifest must be JSON object");
        assert!(!manifest["adopted_patterns"].as_array().unwrap().is_empty());
        assert!(manifest["digest"].as_str().is_some());
    }

    #[test]
    fn build_derived_manifest_includes_transitive_deps() {
        let catalog = pattern_catalog();
        let manifest =
            build_derived_manifest(&["AP6"], "causal tracing", catalog)
                .expect("manifest should build");
        let ids: Vec<&str> = manifest["adopted_patterns"]
            .as_array()
            .unwrap()
            .iter()
            .filter_map(|v| v["pattern_id"].as_str())
            .collect();
        // AP6 requires AP3 and AP4; AP3 requires AP2; AP2 requires AP0, AP1; AP4 requires AP0
        for dep in &["AP0", "AP1", "AP2", "AP3", "AP4", "AP6"] {
            assert!(ids.contains(dep), "Expected {dep} in manifest ids: {ids:?}");
        }
    }

    #[test]
    fn render_manifest_human_produces_string() {
        let catalog = pattern_catalog();
        let manifest =
            build_derived_manifest(&["AP0"], "simple identity system", catalog)
                .expect("manifest should build");
        let rendered = render_manifest_human(&manifest);
        assert!(rendered.contains("DerivedSystemManifest"));
        assert!(rendered.contains("simple identity system"));
    }

    #[test]
    fn construct_catalog_contains_all_kinds() {
        let catalog = construct_catalog();
        let kinds: HashSet<&str> = catalog.iter().map(|e| e.kind.as_str()).collect();
        for k in &[KIND_PATTERN, KIND_MECHANISM, KIND_SCHEMA, KIND_PROTOCOL, KIND_CONTRACT] {
            assert!(kinds.contains(k), "Missing kind {k}");
        }
    }

    #[test]
    fn all_construct_ids_filtered_by_kind() {
        let pattern_ids = all_construct_ids(Some(&[KIND_PATTERN]));
        assert_eq!(pattern_ids.len(), 25, "Should have 25 pattern constructs");
        let schema_ids = all_construct_ids(Some(&[KIND_SCHEMA]));
        assert!(!schema_ids.is_empty());
    }

    #[test]
    fn suggest_constructs_from_intent_non_empty() {
        let results = suggest_constructs_from_intent("identity schema", None, 5);
        assert!(!results.is_empty(), "Expected suggestions for 'identity schema'");
    }

    #[test]
    fn build_derived_construct_set_non_empty() {
        let cset = build_derived_construct_set(&["AP0", "QSM", "GoalRecord"], "my system")
            .expect("construct set should build");
        assert!(cset.is_object());
        assert_eq!(
            cset["adopted_constructs"].as_array().unwrap().len(),
            3
        );
    }

    #[test]
    fn pattern_entry_digest_is_stable() {
        let catalog = pattern_catalog();
        let d1 = pattern_entry_digest(&catalog[0]);
        let d2 = pattern_entry_digest(&catalog[0]);
        assert_eq!(d1, d2, "Digest must be deterministic");
        assert_eq!(d1.len(), 16);
    }

    #[test]
    fn unknown_pattern_returns_error() {
        let result = resolve_dependencies(&["AP99"], None);
        assert!(result.is_err(), "Should fail for unknown pattern");
    }

    #[test]
    fn unknown_construct_returns_error() {
        let result = build_derived_construct_set(&["NOT_A_CONSTRUCT"], "test");
        assert!(result.is_err());
    }
}
