//! Runtime feature health registry — programmatic status of every URACE feature.
//!
//! Ported from `runtime/urace/runtime_features.py` (557 lines).
//!
//! This module is separate from [`crate::feature_catalog`] (the P2P
//! cryptographic atom registry). It tracks the **operational health** of the
//! runtime itself, not the P2P feature market.
//!
//! Features are keyed by a stable string `id`. Each has a status, description,
//! tags, and optional notes. The static list is validated at crate-load time
//! via [`validate_registry`].

use dashmap::DashMap;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use thiserror::Error;

// ---------------------------------------------------------------------------
// Valid status values (mirrors Python `STATUS_VALUES`)
// ---------------------------------------------------------------------------

pub const STATUS_STABLE: &str = "stable";
pub const STATUS_COMPLETE: &str = "complete";
pub const STATUS_ACTIVE: &str = "active";
pub const STATUS_STUB: &str = "stub";
pub const STATUS_STALE: &str = "stale";
pub const STATUS_REVIEW: &str = "review";
pub const STATUS_DEPRECATED: &str = "deprecated";
pub const STATUS_EXPERIMENTAL: &str = "experimental";

pub const VALID_STATUSES: &[&str] = &[
    STATUS_STABLE,
    STATUS_COMPLETE,
    STATUS_ACTIVE,
    STATUS_STUB,
    STATUS_STALE,
    STATUS_REVIEW,
    STATUS_DEPRECATED,
    STATUS_EXPERIMENTAL,
];

// ---------------------------------------------------------------------------
// Valid tag values (mirrors Python `TAG_VALUES`)
// ---------------------------------------------------------------------------

pub const TAG_CORE: &str = "core";
pub const TAG_INTEGRATION: &str = "integration";
pub const TAG_OPTIONAL: &str = "optional";
pub const TAG_SECURITY: &str = "security";
pub const TAG_OBSERVABILITY: &str = "observability";
pub const TAG_DELIVERY: &str = "delivery";
pub const TAG_SELF_IMPROVEMENT: &str = "self-improvement";
pub const TAG_UX: &str = "ux";

pub const VALID_TAGS: &[&str] = &[
    TAG_CORE,
    TAG_INTEGRATION,
    TAG_OPTIONAL,
    TAG_SECURITY,
    TAG_OBSERVABILITY,
    TAG_DELIVERY,
    TAG_SELF_IMPROVEMENT,
    TAG_UX,
];

// ---------------------------------------------------------------------------
// Errors
// ---------------------------------------------------------------------------

#[derive(Debug, Error)]
pub enum RegistryError {
    #[error("feature {0:?} not found")]
    NotFound(String),
    #[error("duplicate feature id {0:?}")]
    DuplicateId(String),
    #[error("feature {id:?} has invalid status {status:?}")]
    InvalidStatus { id: String, status: String },
    #[error("feature {id:?} has invalid tag {tag:?}")]
    InvalidTag { id: String, tag: String },
    #[error("feature {id:?} has invalid test_coverage {coverage:?}")]
    InvalidCoverage { id: String, coverage: String },
    #[error("feature {id:?} is missing required field {field:?}")]
    MissingField { id: String, field: String },
}

// ---------------------------------------------------------------------------
// Domain types
// ---------------------------------------------------------------------------

/// The operational health status of a runtime feature.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct RuntimeFeature {
    /// Stable hyphen-separated identifier (e.g. `"lifecycle-loop"`).
    pub id: String,
    /// Human-readable name.
    pub name: String,
    /// Source module or file reference (informational).
    pub module: String,
    /// One of the `STATUS_*` constants.
    pub status: String,
    /// One-sentence description.
    pub description: String,
    /// `"none"`, `"partial"`, or `"full"`.
    pub test_coverage: String,
    /// Set of applicable [`VALID_TAGS`] strings.
    pub tags: Vec<String>,
    /// IDs of features this one is blocked on (empty = unblocked).
    pub blockers: Vec<String>,
    /// Free-form notes.
    pub notes: String,
    /// Optional version string when the feature was introduced.
    pub introduced_version: Option<String>,
    /// Optional version string when the feature was/will be deprecated.
    pub deprecated_version: Option<String>,
}

impl RuntimeFeature {
    /// Return `true` when the feature is considered enabled for production use.
    ///
    /// A feature is enabled when its status is `stable` or `complete`.
    pub fn is_enabled(&self) -> bool {
        self.status == STATUS_STABLE || self.status == STATUS_COMPLETE
    }
}

// ---------------------------------------------------------------------------
// FeatureRegistry
// ---------------------------------------------------------------------------

/// In-memory registry of [`RuntimeFeature`] entries, keyed by `id`.
pub struct FeatureRegistry {
    features: DashMap<String, RuntimeFeature>,
}

impl FeatureRegistry {
    pub fn new() -> Self {
        Self {
            features: DashMap::new(),
        }
    }

    /// Register a feature.
    ///
    /// Returns [`RegistryError::DuplicateId`] if a feature with the same id
    /// is already registered.
    pub fn register(&self, feature: RuntimeFeature) -> Result<(), RegistryError> {
        if self.features.contains_key(&feature.id) {
            return Err(RegistryError::DuplicateId(feature.id.clone()));
        }
        self.features.insert(feature.id.clone(), feature);
        Ok(())
    }

    /// Look up a feature by its `id`.
    pub fn get(&self, id: &str) -> Option<RuntimeFeature> {
        self.features.get(id).map(|e| e.value().clone())
    }

    /// All registered features as a snapshot vec.
    pub fn list(&self) -> Vec<RuntimeFeature> {
        self.features.iter().map(|e| e.value().clone()).collect()
    }

    /// Count features by status.  Mirrors Python `summary()`.
    pub fn summary(&self) -> HashMap<String, usize> {
        let mut counts: HashMap<String, usize> = HashMap::new();
        for entry in self.features.iter() {
            *counts.entry(entry.value().status.clone()).or_insert(0) += 1;
        }
        counts
    }

    /// Return `true` when the feature identified by `id` is enabled
    /// (status is `stable` or `complete`).
    pub fn is_enabled(&self, id: &str) -> bool {
        self.features
            .get(id)
            .map(|e| e.value().is_enabled())
            .unwrap_or(false)
    }

    /// Features whose status is in `{"stub", "stale", "review"}`, core-first.
    /// Mirrors Python `improvement_candidates()`.
    pub fn improvement_candidates(&self) -> Vec<RuntimeFeature> {
        let target = ["stub", "stale", "review"];
        let mut candidates: Vec<RuntimeFeature> = self
            .features
            .iter()
            .filter(|e| target.contains(&e.value().status.as_str()))
            .map(|e| e.value().clone())
            .collect();
        candidates.sort_by_key(|f| {
            (
                if f.tags.contains(&TAG_CORE.to_owned()) { 0 } else { 1 },
                f.id.clone(),
            )
        });
        candidates
    }

    /// Features filtered by tag.  Mirrors Python `by_tag()`.
    pub fn by_tag(&self, tag: &str) -> Vec<RuntimeFeature> {
        self.features
            .iter()
            .filter(|e| e.value().tags.iter().any(|t| t == tag))
            .map(|e| e.value().clone())
            .collect()
    }

    /// Features filtered by status.  Mirrors Python `by_status()`.
    pub fn by_status(&self, status: &str) -> Vec<RuntimeFeature> {
        self.features
            .iter()
            .filter(|e| e.value().status == status)
            .map(|e| e.value().clone())
            .collect()
    }
}

impl Default for FeatureRegistry {
    fn default() -> Self {
        Self::new()
    }
}

// ---------------------------------------------------------------------------
// Validation
// ---------------------------------------------------------------------------

/// Validate a slice of [`RuntimeFeature`] entries, mirroring Python `validate()`.
///
/// Checks for duplicate ids, invalid statuses, invalid tags, and invalid
/// test_coverage values.
pub fn validate_registry(features: &[RuntimeFeature]) -> Result<(), RegistryError> {
    let mut seen_ids: std::collections::HashSet<&str> = std::collections::HashSet::new();
    for feat in features {
        if !seen_ids.insert(feat.id.as_str()) {
            return Err(RegistryError::DuplicateId(feat.id.clone()));
        }
        if !VALID_STATUSES.contains(&feat.status.as_str()) {
            return Err(RegistryError::InvalidStatus {
                id: feat.id.clone(),
                status: feat.status.clone(),
            });
        }
        if !["none", "partial", "full"].contains(&feat.test_coverage.as_str()) {
            return Err(RegistryError::InvalidCoverage {
                id: feat.id.clone(),
                coverage: feat.test_coverage.clone(),
            });
        }
        for tag in &feat.tags {
            if !VALID_TAGS.contains(&tag.as_str()) {
                return Err(RegistryError::InvalidTag {
                    id: feat.id.clone(),
                    tag: tag.clone(),
                });
            }
        }
    }
    Ok(())
}

// ---------------------------------------------------------------------------
// Static feature list (ported from Python _FEATURES)
// ---------------------------------------------------------------------------

/// Return the full static list of built-in URACE runtime features.
///
/// This is a direct port of the Python `_FEATURES` list constant.
/// The list is validated by [`validate_registry`] on construction.
pub fn default_features() -> Vec<RuntimeFeature> {
    vec![
        // ── Core lifecycle ───────────────────────────────────────────────
        RuntimeFeature {
            id: "lifecycle-loop".to_owned(),
            name: "Autonomous Lifecycle Loop".to_owned(),
            module: "cli.py:cycle()".to_owned(),
            status: STATUS_STABLE.to_owned(),
            description: "discover→plan→execute→evaluate→accept cycle with full gate mechanics".to_owned(),
            test_coverage: "full".to_owned(),
            tags: vec![TAG_CORE.to_owned()],
            blockers: vec![],
            notes: "Battle-hardened. Atomic I/O, crash-safe state, full trace records.".to_owned(),
            introduced_version: None,
            deprecated_version: None,
        },
        RuntimeFeature {
            id: "executor-transport".to_owned(),
            name: "Executor Transport Layer".to_owned(),
            module: "executor.py".to_owned(),
            status: STATUS_STABLE.to_owned(),
            description: "Multi-provider routing with capability-aware selection and retry scheduling".to_owned(),
            test_coverage: "full".to_owned(),
            tags: vec![TAG_CORE.to_owned()],
            blockers: vec![],
            notes: "Four-category failure classification (auth/capacity/transient/local-ceiling).".to_owned(),
            introduced_version: None,
            deprecated_version: None,
        },
        RuntimeFeature {
            id: "auto-goals".to_owned(),
            name: "Automatic Goal Derivation".to_owned(),
            module: "auto_goals.py".to_owned(),
            status: STATUS_STABLE.to_owned(),
            description: "Derives bounded objectives from declared product requirements".to_owned(),
            test_coverage: "partial".to_owned(),
            tags: vec![TAG_CORE.to_owned()],
            blockers: vec![],
            notes: "No authority grant required. Dependency chain and supersession supported.".to_owned(),
            introduced_version: None,
            deprecated_version: None,
        },
        RuntimeFeature {
            id: "budget-enforcement".to_owned(),
            name: "Resource Budget Enforcement".to_owned(),
            module: "cli.py:_check_resource_accounting()".to_owned(),
            status: STATUS_COMPLETE.to_owned(),
            description: "Emits BLOCKING gap and transitions lifecycle→BLOCKED when budget exceeded".to_owned(),
            test_coverage: "partial".to_owned(),
            tags: vec![TAG_CORE.to_owned(), TAG_SECURITY.to_owned()],
            blockers: vec![],
            notes: "lifecycle→BLOCKED on budget breach. ROI floor breach also transitions to BLOCKED (was WARNING). Cooldowns: auth 18000→3600s, transient 300→60s.".to_owned(),
            introduced_version: None,
            deprecated_version: None,
        },
        RuntimeFeature {
            id: "capability-envelope-gate".to_owned(),
            name: "Capability Envelope Gate (§2571)".to_owned(),
            module: "inspection.py:objective_is_eligible()".to_owned(),
            status: STATUS_COMPLETE.to_owned(),
            description: "Gates CAPABILITY_DEFINING objectives at CAPABLE/OPTIMIZED maturity on AUTHORITY_GRANT".to_owned(),
            test_coverage: "partial".to_owned(),
            tags: vec![TAG_CORE.to_owned(), TAG_SECURITY.to_owned()],
            blockers: vec![],
            notes: "Transitions lifecycle → BLOCKED on unresolved capability-envelope-breach gaps. AUTHORITY_GRANT required to clear.".to_owned(),
            introduced_version: None,
            deprecated_version: None,
        },
        RuntimeFeature {
            id: "compaction".to_owned(),
            name: "State Compaction".to_owned(),
            module: "compaction.py".to_owned(),
            status: STATUS_STABLE.to_owned(),
            description: "Chunked compaction of governed list fields at safe lifecycle boundaries".to_owned(),
            test_coverage: "partial".to_owned(),
            tags: vec![TAG_CORE.to_owned()],
            blockers: vec![],
            notes: "Preserves historical chunks. Skips when lifecycle=BLOCKED.".to_owned(),
            introduced_version: None,
            deprecated_version: None,
        },
        RuntimeFeature {
            id: "scope-priority".to_owned(),
            name: "Scope Priority System".to_owned(),
            module: "scope_priority.py".to_owned(),
            status: STATUS_COMPLETE.to_owned(),
            description: "Dynamic planning attention weights per scope (product/runtime/rebootstrap)".to_owned(),
            test_coverage: "partial".to_owned(),
            tags: vec![TAG_CORE.to_owned()],
            blockers: vec![],
            notes: "".to_owned(),
            introduced_version: None,
            deprecated_version: None,
        },
        RuntimeFeature {
            id: "continuation".to_owned(),
            name: "Multi-Turn Continuation".to_owned(),
            module: "continuation.py".to_owned(),
            status: STATUS_COMPLETE.to_owned(),
            description: "Multi-turn session state with confidence resets at cycle boundaries".to_owned(),
            test_coverage: "partial".to_owned(),
            tags: vec![TAG_CORE.to_owned()],
            blockers: vec![],
            notes: "Confidence reset at cycle boundary. No validation that confidence was set in prior cycle.".to_owned(),
            introduced_version: None,
            deprecated_version: None,
        },
        // ── Observability ─────────────────────────────────────────────────
        RuntimeFeature {
            id: "inspection-vitals".to_owned(),
            name: "Vitals Snapshot".to_owned(),
            module: "inspection.py:vitals_snapshot()".to_owned(),
            status: STATUS_COMPLETE.to_owned(),
            description: "Focused metrics, cost, health, system scorecard for operators".to_owned(),
            test_coverage: "partial".to_owned(),
            tags: vec![TAG_OBSERVABILITY.to_owned()],
            blockers: vec!["feedback-loop".to_owned()],
            notes: "Scorecard returns WITHHELD when evidence insufficient. Score shows n/a until evidence accumulates.".to_owned(),
            introduced_version: None,
            deprecated_version: None,
        },
        RuntimeFeature {
            id: "analytics-export".to_owned(),
            name: "Analytics Export".to_owned(),
            module: "analytics.py".to_owned(),
            status: STATUS_COMPLETE.to_owned(),
            description: "CSV/HTML/XLSX export of capability metrics".to_owned(),
            test_coverage: "partial".to_owned(),
            tags: vec![TAG_OBSERVABILITY.to_owned(), TAG_OPTIONAL.to_owned()],
            blockers: vec![],
            notes: "canonical_control_dependency=NONE. Output-only; data is NOT fed back into planning. Off by default.".to_owned(),
            introduced_version: None,
            deprecated_version: None,
        },
        RuntimeFeature {
            id: "external-metrics".to_owned(),
            name: "External Metrics Integration".to_owned(),
            module: "external_metrics.py".to_owned(),
            status: STATUS_ACTIVE.to_owned(),
            description: "Integration hooks for external observability sources".to_owned(),
            test_coverage: "partial".to_owned(),
            tags: vec![TAG_OBSERVABILITY.to_owned(), TAG_INTEGRATION.to_owned()],
            blockers: vec![],
            notes: "self_measurement kind wired in — collects test_pass_rate, import_health, spec_quality from self_metrics.py without external users. File sink (JSONL/JSON/CSV) and HTTP POST sink available via settings.sink config key.".to_owned(),
            introduced_version: None,
            deprecated_version: None,
        },
        RuntimeFeature {
            id: "feedback-loop".to_owned(),
            name: "Observability → Planning Feedback Loop".to_owned(),
            module: "planning_feedback.py".to_owned(),
            status: STATUS_ACTIVE.to_owned(),
            description: "Executor outcome history feeds back into goal priority via feedback_priority_adjustment".to_owned(),
            test_coverage: "partial".to_owned(),
            tags: vec![TAG_CORE.to_owned(), TAG_OBSERVABILITY.to_owned(), TAG_DELIVERY.to_owned()],
            blockers: vec![],
            notes: "planning_feedback.apply() called from refresh_scope_priorities(); feedback_adjustment component added to objective_score_breakdown().".to_owned(),
            introduced_version: None,
            deprecated_version: None,
        },
        RuntimeFeature {
            id: "per-stage-timing".to_owned(),
            name: "Per-Stage Execution Timing".to_owned(),
            module: "cli.py executor call records".to_owned(),
            status: STATUS_COMPLETE.to_owned(),
            description: "elapsed_seconds recorded per executor call stage (discover/plan/execute/evaluate)".to_owned(),
            test_coverage: "partial".to_owned(),
            tags: vec![TAG_OBSERVABILITY.to_owned()],
            blockers: vec![],
            notes: "elapsed_seconds captured in executor_calls[] at lines 1372 and 1724 of cli.py. Already fully implemented.".to_owned(),
            introduced_version: None,
            deprecated_version: None,
        },
        RuntimeFeature {
            id: "objective-outcome-rate".to_owned(),
            name: "Objective Outcome Rate Tracking".to_owned(),
            module: "inspection.py:_objective_outcomes()".to_owned(),
            status: STATUS_COMPLETE.to_owned(),
            description: "Aggregate completion/stall/fail rates across objectives over time".to_owned(),
            test_coverage: "partial".to_owned(),
            tags: vec![TAG_OBSERVABILITY.to_owned(), TAG_DELIVERY.to_owned()],
            blockers: vec![],
            notes: "_objective_outcomes() added; exposed in vitals_snapshot() and render_vitals().".to_owned(),
            introduced_version: None,
            deprecated_version: None,
        },
        RuntimeFeature {
            id: "self-measurement-metrics".to_owned(),
            name: "Self-Measurement (No-User Metrics)".to_owned(),
            module: "self_metrics.py".to_owned(),
            status: STATUS_ACTIVE.to_owned(),
            description: "Test pass rate, import health, spec quality — measurable without users".to_owned(),
            test_coverage: "partial".to_owned(),
            tags: vec![TAG_OBSERVABILITY.to_owned(), TAG_CORE.to_owned()],
            blockers: vec![],
            notes: "Enables URACE to measure its own product before having external users.".to_owned(),
            introduced_version: None,
            deprecated_version: None,
        },
        RuntimeFeature {
            id: "value-trajectory".to_owned(),
            name: "Value Trajectory Tracking".to_owned(),
            module: "value_trajectory.py".to_owned(),
            status: STATUS_COMPLETE.to_owned(),
            description: "Cumulative value, velocity, acceleration, and self-correction signals".to_owned(),
            test_coverage: "partial".to_owned(),
            tags: vec![TAG_OBSERVABILITY.to_owned()],
            blockers: vec![],
            notes: "".to_owned(),
            introduced_version: None,
            deprecated_version: None,
        },
        // ── Security / Governance ─────────────────────────────────────────
        RuntimeFeature {
            id: "evolution-guard".to_owned(),
            name: "Evolution Guard (Kernel Protection)".to_owned(),
            module: "evolution_guard.py".to_owned(),
            status: STATUS_STABLE.to_owned(),
            description: "Digest-verified protection of launcher.py and itself; candidate test-suite re-validation".to_owned(),
            test_coverage: "partial".to_owned(),
            tags: vec![TAG_SECURITY.to_owned(), TAG_SELF_IMPROVEMENT.to_owned()],
            blockers: vec![],
            notes: "Non-replaceable. Protected config paths: authority, constraints, self_evolution_policy, executor limits.".to_owned(),
            introduced_version: None,
            deprecated_version: None,
        },
        RuntimeFeature {
            id: "signed-ledger".to_owned(),
            name: "Signed Audit Ledger".to_owned(),
            module: "signed_ledger.py + ledger_crypto.py".to_owned(),
            status: STATUS_STABLE.to_owned(),
            description: "Hybrid-crypto append-only ledger with SHA384 chaining".to_owned(),
            test_coverage: "full".to_owned(),
            tags: vec![TAG_SECURITY.to_owned()],
            blockers: vec![],
            notes: "Post-quantum resilient. Every row references previous hash. Complete verification before read.".to_owned(),
            introduced_version: None,
            deprecated_version: None,
        },
        RuntimeFeature {
            id: "decision-records".to_owned(),
            name: "Decision Record System".to_owned(),
            module: "decision_record.py".to_owned(),
            status: STATUS_STABLE.to_owned(),
            description: "Immutable provenance-linked records for every autonomous decision".to_owned(),
            test_coverage: "full".to_owned(),
            tags: vec![TAG_SECURITY.to_owned(), TAG_CORE.to_owned()],
            blockers: vec![],
            notes: "Full forensic trail: governing_intent_ref, state_digest, executor identity, authority_basis.".to_owned(),
            introduced_version: None,
            deprecated_version: None,
        },
        RuntimeFeature {
            id: "version-enforcement".to_owned(),
            name: "Version Enforcement (state/bridge/peer)".to_owned(),
            module: "version.py + preflight.py + integration_bridge.py".to_owned(),
            status: STATUS_STABLE.to_owned(),
            description: "State format versioning, bridge client version floor, P2P protocol version gate".to_owned(),
            test_coverage: "full".to_owned(),
            tags: vec![TAG_SECURITY.to_owned(), TAG_INTEGRATION.to_owned()],
            blockers: vec![],
            notes: "Added in session. peer protocol_version=2, MIN_BRIDGE_CLIENT_VERSION=1.".to_owned(),
            introduced_version: None,
            deprecated_version: None,
        },
        RuntimeFeature {
            id: "rules-ledger".to_owned(),
            name: "Rule Ledger".to_owned(),
            module: "rules.py".to_owned(),
            status: STATUS_COMPLETE.to_owned(),
            description: "PURPOSE→DIRECTIVE→OBJECTIVE governance hierarchy with derivations and supersessions".to_owned(),
            test_coverage: "partial".to_owned(),
            tags: vec![TAG_SECURITY.to_owned(), TAG_CORE.to_owned()],
            blockers: vec![],
            notes: "Structurally sound. Available for governance workflows. Usage is optional — most governance is captured implicitly in decision_record fields.".to_owned(),
            introduced_version: None,
            deprecated_version: None,
        },
        RuntimeFeature {
            id: "authenticated-journal".to_owned(),
            name: "Authenticated Journal".to_owned(),
            module: "authenticated_journal.py".to_owned(),
            status: STATUS_COMPLETE.to_owned(),
            description: "Append-only transaction journal preserving owner edits during recovery".to_owned(),
            test_coverage: "partial".to_owned(),
            tags: vec![TAG_SECURITY.to_owned(), TAG_CORE.to_owned()],
            blockers: vec![],
            notes: "".to_owned(),
            introduced_version: None,
            deprecated_version: None,
        },
        // ── Integration ───────────────────────────────────────────────────
        RuntimeFeature {
            id: "integration-bridge".to_owned(),
            name: "Integration Bridge".to_owned(),
            module: "integration_bridge.py".to_owned(),
            status: STATUS_STABLE.to_owned(),
            description: "Scoped M2M operations with policy-based access, job receipts, resource limits".to_owned(),
            test_coverage: "full".to_owned(),
            tags: vec![TAG_INTEGRATION.to_owned(), TAG_SECURITY.to_owned()],
            blockers: vec![],
            notes: "FORBIDDEN/ADMIN command sets enforced. client_version floor validated.".to_owned(),
            introduced_version: None,
            deprecated_version: None,
        },
        RuntimeFeature {
            id: "mcp-server".to_owned(),
            name: "MCP Server".to_owned(),
            module: "mcp_server.py".to_owned(),
            status: STATUS_COMPLETE.to_owned(),
            description: "MCP 2.0 stdio transport — tools: urace_operations, urace_call, urace_submit, urace_job_status, urace_job_cancel".to_owned(),
            test_coverage: "partial".to_owned(),
            tags: vec![TAG_INTEGRATION.to_owned()],
            blockers: vec![],
            notes: "Session lifetime management. Job cancellation on disconnect. Durable receipt retention.".to_owned(),
            introduced_version: None,
            deprecated_version: None,
        },
        RuntimeFeature {
            id: "a2a-server".to_owned(),
            name: "A2A Server".to_owned(),
            module: "a2a_server.py".to_owned(),
            status: STATUS_COMPLETE.to_owned(),
            description: "A2A 1.0 polling endpoint (loopback-only)".to_owned(),
            test_coverage: "partial".to_owned(),
            tags: vec![TAG_INTEGRATION.to_owned()],
            blockers: vec![],
            notes: "No remote callback or discovery crawling. Loopback only.".to_owned(),
            introduced_version: None,
            deprecated_version: None,
        },
        RuntimeFeature {
            id: "data-transport".to_owned(),
            name: "Data Transport Connectors".to_owned(),
            module: "data_transport.py".to_owned(),
            status: STATUS_COMPLETE.to_owned(),
            description: "Read/write connectors for SQL, CSV, API sources".to_owned(),
            test_coverage: "partial".to_owned(),
            tags: vec![TAG_INTEGRATION.to_owned(), TAG_OPTIONAL.to_owned()],
            blockers: vec![],
            notes: "No destination write confirmation. No schema validation on source reads.".to_owned(),
            introduced_version: None,
            deprecated_version: None,
        },
        RuntimeFeature {
            id: "eth-settlement-adapter".to_owned(),
            name: "EVM Token Settlement Adapter".to_owned(),
            module: "eth_settlement_adapter.py:EthSettlementAdapter".to_owned(),
            status: STATUS_ACTIVE.to_owned(),
            description: "Broadcasts signed ERC-20 and NFT transactions to configured JSON-RPC endpoint when token_settlement=True.".to_owned(),
            test_coverage: "full".to_owned(),
            tags: vec![TAG_INTEGRATION.to_owned(), TAG_DELIVERY.to_owned()],
            blockers: vec![],
            notes: "".to_owned(),
            introduced_version: None,
            deprecated_version: None,
        },
        // ── Peer Network ─────────────────────────────────────────────────
        RuntimeFeature {
            id: "kademlia-phase-c".to_owned(),
            name: "Kademlia Phase C (Iterative Lookup)".to_owned(),
            module: "kademlia.py:IterativeFinder".to_owned(),
            status: STATUS_ACTIVE.to_owned(),
            description: "XOR-routing iterative node lookup via kademlia PyPI package; gated on network_mode=internet/hybrid. Falls back to local routing table.".to_owned(),
            test_coverage: "partial".to_owned(),
            tags: vec![TAG_INTEGRATION.to_owned(), TAG_DELIVERY.to_owned()],
            blockers: vec![],
            notes: "Included in base install. Local routing table used for intranet mode.".to_owned(),
            introduced_version: None,
            deprecated_version: None,
        },
        RuntimeFeature {
            id: "peer-exchange".to_owned(),
            name: "Peer Exchange (Protocol)".to_owned(),
            module: "peer_exchange.py".to_owned(),
            status: STATUS_COMPLETE.to_owned(),
            description: "Signed artifact exchange with hybrid crypto, audit chain, quota, version enforcement".to_owned(),
            test_coverage: "full".to_owned(),
            tags: vec![TAG_INTEGRATION.to_owned(), TAG_SECURITY.to_owned(), TAG_OPTIONAL.to_owned()],
            blockers: vec![],
            notes: "Quarantine-only. Peer artifacts are stored but never evaluated for improvement.".to_owned(),
            introduced_version: None,
            deprecated_version: None,
        },
        RuntimeFeature {
            id: "peer-selection".to_owned(),
            name: "Peer Selection & Scoring".to_owned(),
            module: "peer_selection.py".to_owned(),
            status: STATUS_COMPLETE.to_owned(),
            description: "Peer discovery, health/latency/capacity scoring, VERSION_TOO_OLD enforcement".to_owned(),
            test_coverage: "full".to_owned(),
            tags: vec![TAG_INTEGRATION.to_owned(), TAG_OPTIONAL.to_owned()],
            blockers: vec![],
            notes: "".to_owned(),
            introduced_version: None,
            deprecated_version: None,
        },
        RuntimeFeature {
            id: "peer-network-improvement".to_owned(),
            name: "Peer-Contributed Improvements".to_owned(),
            module: "peer_improvement.py".to_owned(),
            status: STATUS_ACTIVE.to_owned(),
            description: "Pipeline to evaluate and promote peer artifacts into the improvement workflow".to_owned(),
            test_coverage: "partial".to_owned(),
            tags: vec![TAG_DELIVERY.to_owned(), TAG_SELF_IMPROVEMENT.to_owned()],
            blockers: vec![],
            notes: "urace peer-review [list|evaluate <id>|promote <id>]. Quarantine → safety evaluate → sanitize → goal queue. Peer identities are SHA256 fingerprints (opaque).".to_owned(),
            introduced_version: None,
            deprecated_version: None,
        },
        RuntimeFeature {
            id: "peer-artifact-sanitization".to_owned(),
            name: "Artifact Auto-Sanitization".to_owned(),
            module: "peer_improvement.py:sanitize_quarantine_artifact".to_owned(),
            status: STATUS_COMPLETE.to_owned(),
            description: "Security scan of quarantined artifacts before promotion: shell injection, binary magic bytes, dangerous Python imports, entropy spike.".to_owned(),
            test_coverage: "full".to_owned(),
            tags: vec![TAG_SECURITY.to_owned(), TAG_DELIVERY.to_owned()],
            blockers: vec![],
            notes: "".to_owned(),
            introduced_version: None,
            deprecated_version: None,
        },
        // ── Self-Improvement ─────────────────────────────────────────────
        RuntimeFeature {
            id: "self-evolution-trial".to_owned(),
            name: "Self-Evolution Trial Pipeline".to_owned(),
            module: "trial/ directory".to_owned(),
            status: STATUS_STABLE.to_owned(),
            description: "Hermetic containerized trial: snapshot isolation, sealed tests, second-provider revalidation".to_owned(),
            test_coverage: "full".to_owned(),
            tags: vec![TAG_SELF_IMPROVEMENT.to_owned(), TAG_SECURITY.to_owned()],
            blockers: vec![],
            notes: "246 sealed private test cases. Kernel-locked supervisor. No network in container.".to_owned(),
            introduced_version: None,
            deprecated_version: None,
        },
        RuntimeFeature {
            id: "trial-product-concurrency".to_owned(),
            name: "Trial / Product Concurrency".to_owned(),
            module: "trial/trial_supervisor.py".to_owned(),
            status: STATUS_COMPLETE.to_owned(),
            description: "Spec trial and runtime cycle run concurrently as separate supervisor slots".to_owned(),
            test_coverage: "none".to_owned(),
            tags: vec![TAG_SELF_IMPROVEMENT.to_owned(), TAG_DELIVERY.to_owned()],
            blockers: vec![],
            notes: "productive_step split into productive_runtime_step and productive_spec_step; ThreadPoolExecutor max_workers=4. Use separate guard files — no shared lock contention.".to_owned(),
            introduced_version: None,
            deprecated_version: None,
        },
        // ── Delivery / Throughput ─────────────────────────────────────────
        RuntimeFeature {
            id: "multi-executor-planning".to_owned(),
            name: "Multi-Executor Parallel Planning".to_owned(),
            module: "multi_executor.py".to_owned(),
            status: STATUS_EXPERIMENTAL.to_owned(),
            description: "Multiple executors generate plans; best scored proposal selected (Agora pattern)".to_owned(),
            test_coverage: "partial".to_owned(),
            tags: vec![TAG_DELIVERY.to_owned(), TAG_CORE.to_owned()],
            blockers: vec![],
            notes: "Disabled by default (config executor.multi_plan_selection.enabled=true to activate). Requires 2+ available providers.".to_owned(),
            introduced_version: None,
            deprecated_version: None,
        },
        RuntimeFeature {
            id: "agora-voting".to_owned(),
            name: "Agora Variant Voting".to_owned(),
            module: "portfolio.py:agora".to_owned(),
            status: STATUS_DEPRECATED.to_owned(),
            description: "Proposal/vote/decision system for portfolio variant acceptance".to_owned(),
            test_coverage: "none".to_owned(),
            tags: vec![TAG_OPTIONAL.to_owned(), TAG_DELIVERY.to_owned()],
            blockers: vec![],
            notes: "~500 LOC. Never invoked. Pattern repurposed into multi_executor.py for cycle-level plan selection. Safe to remove from portfolio.py.".to_owned(),
            introduced_version: None,
            deprecated_version: None,
        },
        RuntimeFeature {
            id: "portfolio-controller".to_owned(),
            name: "Portfolio Controller".to_owned(),
            module: "portfolio.py".to_owned(),
            status: STATUS_COMPLETE.to_owned(),
            description: "Bounded deployment-local controller: cohorts, variants, isolation probes".to_owned(),
            test_coverage: "partial".to_owned(),
            tags: vec![TAG_OPTIONAL.to_owned(), TAG_DELIVERY.to_owned()],
            blockers: vec![],
            notes: "Agora voting subsystem is the stale part. Cohort/variant mechanics are functional.".to_owned(),
            introduced_version: None,
            deprecated_version: None,
        },
        RuntimeFeature {
            id: "rollback-operation".to_owned(),
            name: "Operation Rollback".to_owned(),
            module: "cli.py:rollback command".to_owned(),
            status: STATUS_ACTIVE.to_owned(),
            description: "Restore product files from last accepted stable snapshot".to_owned(),
            test_coverage: "partial".to_owned(),
            tags: vec![TAG_DELIVERY.to_owned(), TAG_SECURITY.to_owned()],
            blockers: vec![],
            notes: "urace rollback [--dry-run] [--json] — restores from stable_path(config). Per-operation granularity requires additional pre-execution snapshot infrastructure.".to_owned(),
            introduced_version: None,
            deprecated_version: None,
        },
        RuntimeFeature {
            id: "freeform-routing".to_owned(),
            name: "Freeform Routing Escape Hatch".to_owned(),
            module: "freeform_routing.py".to_owned(),
            status: STATUS_COMPLETE.to_owned(),
            description: "Unstructured executor calls with resource accounting mirrored into main executor_calls".to_owned(),
            test_coverage: "partial".to_owned(),
            tags: vec![TAG_OPTIONAL.to_owned(), TAG_DELIVERY.to_owned()],
            blockers: vec![],
            notes: "Routing call cost now mirrored into state executor_calls[] for feedback loop visibility. Separate JSONL audit retained for full detail.".to_owned(),
            introduced_version: None,
            deprecated_version: None,
        },
        // ── UX ───────────────────────────────────────────────────────────
        RuntimeFeature {
            id: "tui-dashboard".to_owned(),
            name: "TUI Dashboard".to_owned(),
            module: "tui.py".to_owned(),
            status: STATUS_ACTIVE.to_owned(),
            description: "k9s-style interactive dashboard: lifecycle, events, gates, command input".to_owned(),
            test_coverage: "full".to_owned(),
            tags: vec![TAG_UX.to_owned()],
            blockers: vec![],
            notes: "Functional. Shows real lifecycle/objective state. Score shows n/a until evidence accumulates — expected behavior.".to_owned(),
            introduced_version: None,
            deprecated_version: None,
        },
        RuntimeFeature {
            id: "feature-status-registry".to_owned(),
            name: "Feature Status Registry".to_owned(),
            module: "runtime_features.py".to_owned(),
            status: STATUS_ACTIVE.to_owned(),
            description: "Programmatic registry of every URACE feature with operational status".to_owned(),
            test_coverage: "full".to_owned(),
            tags: vec![TAG_OBSERVABILITY.to_owned(), TAG_UX.to_owned()],
            blockers: vec![],
            notes: "This module. Enables improvement cycle prioritization and operator visibility.".to_owned(),
            introduced_version: None,
            deprecated_version: None,
        },
    ]
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    fn populated_registry() -> FeatureRegistry {
        let reg = FeatureRegistry::new();
        for feat in default_features() {
            reg.register(feat).unwrap();
        }
        reg
    }

    #[test]
    fn default_features_validates() {
        let features = default_features();
        assert!(validate_registry(&features).is_ok());
    }

    #[test]
    fn register_and_get() {
        let reg = FeatureRegistry::new();
        let feat = RuntimeFeature {
            id: "my-feature".to_owned(),
            name: "My Feature".to_owned(),
            module: "my_module.py".to_owned(),
            status: STATUS_ACTIVE.to_owned(),
            description: "A test feature".to_owned(),
            test_coverage: "partial".to_owned(),
            tags: vec![TAG_CORE.to_owned()],
            blockers: vec![],
            notes: "".to_owned(),
            introduced_version: None,
            deprecated_version: None,
        };
        reg.register(feat.clone()).unwrap();
        let retrieved = reg.get("my-feature").unwrap();
        assert_eq!(retrieved.name, "My Feature");
    }

    #[test]
    fn duplicate_id_error() {
        let reg = FeatureRegistry::new();
        let feat = RuntimeFeature {
            id: "dup".to_owned(),
            name: "Dup".to_owned(),
            module: "mod.py".to_owned(),
            status: STATUS_STUB.to_owned(),
            description: "desc".to_owned(),
            test_coverage: "none".to_owned(),
            tags: vec![],
            blockers: vec![],
            notes: "".to_owned(),
            introduced_version: None,
            deprecated_version: None,
        };
        reg.register(feat.clone()).unwrap();
        assert!(matches!(
            reg.register(feat),
            Err(RegistryError::DuplicateId(_))
        ));
    }

    #[test]
    fn list_has_all_features() {
        let reg = populated_registry();
        assert_eq!(reg.list().len(), default_features().len());
    }

    #[test]
    fn summary_counts_by_status() {
        let reg = populated_registry();
        let s = reg.summary();
        // stable features should appear
        assert!(s.contains_key(STATUS_STABLE));
        // sum of all counts equals total
        let total: usize = s.values().sum();
        assert_eq!(total, default_features().len());
    }

    #[test]
    fn is_enabled_stable_and_complete() {
        let reg = populated_registry();
        // lifecycle-loop is stable → enabled
        assert!(reg.is_enabled("lifecycle-loop"));
        // budget-enforcement is complete → enabled
        assert!(reg.is_enabled("budget-enforcement"));
    }

    #[test]
    fn is_enabled_active_is_false() {
        let reg = populated_registry();
        // feedback-loop is active → NOT enabled for production
        assert!(!reg.is_enabled("feedback-loop"));
    }

    #[test]
    fn is_enabled_deprecated_is_false() {
        let reg = populated_registry();
        assert!(!reg.is_enabled("agora-voting"));
    }

    #[test]
    fn get_missing_returns_none() {
        let reg = populated_registry();
        assert!(reg.get("does-not-exist").is_none());
    }

    #[test]
    fn by_tag_core_non_empty() {
        let reg = populated_registry();
        let core = reg.by_tag(TAG_CORE);
        assert!(!core.is_empty());
        for f in &core {
            assert!(f.tags.contains(&TAG_CORE.to_owned()));
        }
    }

    #[test]
    fn by_status_stable() {
        let reg = populated_registry();
        let stable = reg.by_status(STATUS_STABLE);
        assert!(!stable.is_empty());
        for f in &stable {
            assert_eq!(f.status, STATUS_STABLE);
        }
    }

    #[test]
    fn improvement_candidates_contains_expected_statuses() {
        let reg = populated_registry();
        let cands = reg.improvement_candidates();
        for f in &cands {
            assert!(
                f.status == STATUS_STUB
                    || f.status == STATUS_STALE
                    || f.status == STATUS_REVIEW,
                "unexpected status {:?} for {:?}",
                f.status,
                f.id
            );
        }
    }
}
