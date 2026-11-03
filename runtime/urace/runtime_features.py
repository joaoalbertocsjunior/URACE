"""Runtime feature health registry — programmatic status of every URACE feature.

This is separate from feature_catalog.py (the P2P cryptographic atom registry).
This module tracks the operational health of the runtime itself.
"""
from __future__ import annotations

STATUS_VALUES = frozenset({
    'stable',       # production-ready, battle-hardened, well-tested
    'complete',     # fully implemented and tested
    'active',       # currently being developed/improved
    'stub',         # interface exists, minimal/no implementation
    'stale',        # was functional, now has known gaps or bitrot
    'review',       # needs architectural review before relying on
    'deprecated',   # being actively removed/replaced
    'experimental', # not recommended for production use
})

TAG_VALUES = frozenset({
    'core',           # fundamental to the lifecycle loop
    'integration',    # external system connectivity
    'optional',       # non-blocking to core operation
    'security',       # safety, audit, access control
    'observability',  # metrics, dashboards, reporting
    'delivery',       # throughput, output, improvement rate
    'self-improvement', # runtime self-evolution pipeline
    'ux',             # operator-facing interfaces
})

_FEATURES: list[dict] = [
    # ── Core lifecycle ───────────────────────────────────────────────────────
    {
        'id': 'lifecycle-loop',
        'name': 'Autonomous Lifecycle Loop',
        'module': 'cli.py:cycle()',
        'status': 'stable',
        'description': 'discover→plan→execute→evaluate→accept cycle with full gate mechanics',
        'test_coverage': 'full',
        'tags': ['core'],
        'blockers': [],
        'notes': 'Battle-hardened. Atomic I/O, crash-safe state, full trace records.',
    },
    {
        'id': 'executor-transport',
        'name': 'Executor Transport Layer',
        'module': 'executor.py',
        'status': 'stable',
        'description': 'Multi-provider routing with capability-aware selection and retry scheduling',
        'test_coverage': 'full',
        'tags': ['core'],
        'blockers': [],
        'notes': 'Four-category failure classification (auth/capacity/transient/local-ceiling).',
    },
    {
        'id': 'auto-goals',
        'name': 'Automatic Goal Derivation',
        'module': 'auto_goals.py',
        'status': 'stable',
        'description': 'Derives bounded objectives from declared product requirements',
        'test_coverage': 'partial',
        'tags': ['core'],
        'blockers': [],
        'notes': 'No authority grant required. Dependency chain and supersession supported.',
    },
    {
        'id': 'budget-enforcement',
        'name': 'Resource Budget Enforcement',
        'module': 'cli.py:_check_resource_accounting()',
        'status': 'complete',
        'description': 'Emits BLOCKING gap and transitions lifecycle→BLOCKED when budget exceeded',
        'test_coverage': 'partial',
        'tags': ['core', 'security'],
        'blockers': [],
        'notes': 'lifecycle→BLOCKED on budget breach. ROI floor breach also transitions to BLOCKED (was WARNING). Cooldowns: auth 18000→3600s, transient 300→60s.',
    },
    {
        'id': 'capability-envelope-gate',
        'name': 'Capability Envelope Gate (§2571)',
        'module': 'inspection.py:objective_is_eligible()',
        'status': 'complete',
        'description': 'Gates CAPABILITY_DEFINING objectives at CAPABLE/OPTIMIZED maturity on AUTHORITY_GRANT',
        'test_coverage': 'partial',
        'tags': ['core', 'security'],
        'blockers': [],
        'notes': 'Returns False correctly on current call. Integrity gap emitted. Lifecycle does not BLOCK on gap — gate is advisory not enforcement.',
    },
    {
        'id': 'compaction',
        'name': 'State Compaction',
        'module': 'compaction.py',
        'status': 'stable',
        'description': 'Chunked compaction of governed list fields at safe lifecycle boundaries',
        'test_coverage': 'partial',
        'tags': ['core'],
        'blockers': [],
        'notes': 'Preserves historical chunks. Skips when lifecycle=BLOCKED.',
    },
    {
        'id': 'scope-priority',
        'name': 'Scope Priority System',
        'module': 'scope_priority.py',
        'status': 'complete',
        'description': 'Dynamic planning attention weights per scope (product/runtime/rebootstrap)',
        'test_coverage': 'partial',
        'tags': ['core'],
        'blockers': [],
        'notes': '',
    },
    {
        'id': 'continuation',
        'name': 'Multi-Turn Continuation',
        'module': 'continuation.py',
        'status': 'complete',
        'description': 'Multi-turn session state with confidence resets at cycle boundaries',
        'test_coverage': 'partial',
        'tags': ['core'],
        'blockers': [],
        'notes': 'Confidence reset at cycle boundary. No validation that confidence was set in prior cycle.',
    },

    # ── Observability ─────────────────────────────────────────────────────────
    {
        'id': 'inspection-vitals',
        'name': 'Vitals Snapshot',
        'module': 'inspection.py:vitals_snapshot()',
        'status': 'complete',
        'description': 'Focused metrics, cost, health, system scorecard for operators',
        'test_coverage': 'partial',
        'tags': ['observability'],
        'blockers': ['feedback-loop'],
        'notes': 'Scorecard returns WITHHELD when evidence insufficient. Score shows n/a until evidence accumulates.',
    },
    {
        'id': 'analytics-export',
        'name': 'Analytics Export',
        'module': 'analytics.py',
        'status': 'complete',
        'description': 'CSV/HTML/XLSX export of capability metrics',
        'test_coverage': 'partial',
        'tags': ['observability', 'optional'],
        'blockers': [],
        'notes': 'canonical_control_dependency=NONE. Output-only; data is NOT fed back into planning. Off by default.',
    },
    {
        'id': 'external-metrics',
        'name': 'External Metrics Integration',
        'module': 'external_metrics.py',
        'status': 'active',
        'description': 'Integration hooks for external observability sources',
        'test_coverage': 'partial',
        'tags': ['observability', 'integration'],
        'blockers': [],
        'notes': 'self_measurement kind wired in — collects test_pass_rate, import_health, spec_quality from self_metrics.py without external users.',
    },
    {
        'id': 'feedback-loop',
        'name': 'Observability → Planning Feedback Loop',
        'module': 'planning_feedback.py',
        'status': 'active',
        'description': 'Executor outcome history feeds back into goal priority via feedback_priority_adjustment',
        'test_coverage': 'partial',
        'tags': ['core', 'observability', 'delivery'],
        'blockers': [],
        'notes': 'planning_feedback.apply() called from refresh_scope_priorities(); feedback_adjustment component added to objective_score_breakdown().',
    },
    {
        'id': 'per-stage-timing',
        'name': 'Per-Stage Execution Timing',
        'module': 'cli.py executor call records',
        'status': 'complete',
        'description': 'elapsed_seconds recorded per executor call stage (discover/plan/execute/evaluate)',
        'test_coverage': 'partial',
        'tags': ['observability'],
        'blockers': [],
        'notes': 'elapsed_seconds captured in executor_calls[] at lines 1372 and 1724 of cli.py. Already fully implemented.',
    },
    {
        'id': 'objective-outcome-rate',
        'name': 'Objective Outcome Rate Tracking',
        'module': 'inspection.py:_objective_outcomes()',
        'status': 'complete',
        'description': 'Aggregate completion/stall/fail rates across objectives over time',
        'test_coverage': 'partial',
        'tags': ['observability', 'delivery'],
        'blockers': [],
        'notes': '_objective_outcomes() added; exposed in vitals_snapshot() and render_vitals().',
    },
    {
        'id': 'self-measurement-metrics',
        'name': 'Self-Measurement (No-User Metrics)',
        'module': 'self_metrics.py',
        'status': 'active',
        'description': 'Test pass rate, import health, spec quality — measurable without users',
        'test_coverage': 'partial',
        'tags': ['observability', 'core'],
        'blockers': [],
        'notes': 'Enables URACE to measure its own product before having external users.',
    },
    {
        'id': 'value-trajectory',
        'name': 'Value Trajectory Tracking',
        'module': 'value_trajectory.py',
        'status': 'complete',
        'description': 'Cumulative value, velocity, acceleration, and self-correction signals',
        'test_coverage': 'partial',
        'tags': ['observability'],
        'blockers': [],
        'notes': '',
    },

    # ── Security / Governance ─────────────────────────────────────────────────
    {
        'id': 'evolution-guard',
        'name': 'Evolution Guard (Kernel Protection)',
        'module': 'evolution_guard.py',
        'status': 'stable',
        'description': 'Digest-verified protection of launcher.py and itself; candidate test-suite re-validation',
        'test_coverage': 'partial',
        'tags': ['security', 'self-improvement'],
        'blockers': [],
        'notes': 'Non-replaceable. Protected config paths: authority, constraints, self_evolution_policy, executor limits.',
    },
    {
        'id': 'signed-ledger',
        'name': 'Signed Audit Ledger',
        'module': 'signed_ledger.py + ledger_crypto.py',
        'status': 'stable',
        'description': 'Hybrid-crypto append-only ledger with SHA384 chaining',
        'test_coverage': 'full',
        'tags': ['security'],
        'blockers': [],
        'notes': 'Post-quantum resilient. Every row references previous hash. Complete verification before read.',
    },
    {
        'id': 'decision-records',
        'name': 'Decision Record System',
        'module': 'decision_record.py',
        'status': 'stable',
        'description': 'Immutable provenance-linked records for every autonomous decision',
        'test_coverage': 'full',
        'tags': ['security', 'core'],
        'blockers': [],
        'notes': 'Full forensic trail: governing_intent_ref, state_digest, executor identity, authority_basis.',
    },
    {
        'id': 'version-enforcement',
        'name': 'Version Enforcement (state/bridge/peer)',
        'module': 'version.py + preflight.py + integration_bridge.py',
        'status': 'stable',
        'description': 'State format versioning, bridge client version floor, P2P protocol version gate',
        'test_coverage': 'full',
        'tags': ['security', 'integration'],
        'blockers': [],
        'notes': 'Added in session. peer protocol_version=2, MIN_BRIDGE_CLIENT_VERSION=1.',
    },
    {
        'id': 'rules-ledger',
        'name': 'Rule Ledger',
        'module': 'rules.py',
        'status': 'complete',
        'description': 'PURPOSE→DIRECTIVE→OBJECTIVE governance hierarchy with derivations and supersessions',
        'test_coverage': 'partial',
        'tags': ['security', 'core'],
        'blockers': [],
        'notes': 'Structurally sound. Available for governance workflows. Usage is optional — most governance is captured implicitly in decision_record fields.',
    },
    {
        'id': 'authenticated-journal',
        'name': 'Authenticated Journal',
        'module': 'authenticated_journal.py',
        'status': 'complete',
        'description': 'Append-only transaction journal preserving owner edits during recovery',
        'test_coverage': 'partial',
        'tags': ['security', 'core'],
        'blockers': [],
        'notes': '',
    },

    # ── Integration ───────────────────────────────────────────────────────────
    {
        'id': 'integration-bridge',
        'name': 'Integration Bridge',
        'module': 'integration_bridge.py',
        'status': 'stable',
        'description': 'Scoped M2M operations with policy-based access, job receipts, resource limits',
        'test_coverage': 'full',
        'tags': ['integration', 'security'],
        'blockers': [],
        'notes': 'FORBIDDEN/ADMIN command sets enforced. client_version floor validated.',
    },
    {
        'id': 'mcp-server',
        'name': 'MCP Server',
        'module': 'mcp_server.py',
        'status': 'complete',
        'description': 'MCP 2.0 stdio transport — tools: urace_operations, urace_call, urace_submit, urace_job_status, urace_job_cancel',
        'test_coverage': 'partial',
        'tags': ['integration'],
        'blockers': [],
        'notes': 'Session lifetime management. Job cancellation on disconnect. Durable receipt retention.',
    },
    {
        'id': 'a2a-server',
        'name': 'A2A Server',
        'module': 'a2a_server.py',
        'status': 'complete',
        'description': 'A2A 1.0 polling endpoint (loopback-only)',
        'test_coverage': 'partial',
        'tags': ['integration'],
        'blockers': [],
        'notes': 'No remote callback or discovery crawling. Loopback only.',
    },
    {
        'id': 'data-transport',
        'name': 'Data Transport Connectors',
        'module': 'data_transport.py',
        'status': 'complete',
        'description': 'Read/write connectors for SQL, CSV, API sources',
        'test_coverage': 'partial',
        'tags': ['integration', 'optional'],
        'blockers': [],
        'notes': 'No destination write confirmation. No schema validation on source reads.',
    },

    # ── Peer Network ─────────────────────────────────────────────────────────
    {
        'id': 'peer-exchange',
        'name': 'Peer Exchange (Protocol)',
        'module': 'peer_exchange.py',
        'status': 'complete',
        'description': 'Signed artifact exchange with hybrid crypto, audit chain, quota, version enforcement',
        'test_coverage': 'full',
        'tags': ['integration', 'security', 'optional'],
        'blockers': [],
        'notes': 'Quarantine-only. Peer artifacts are stored but never evaluated for improvement.',
    },
    {
        'id': 'peer-selection',
        'name': 'Peer Selection & Scoring',
        'module': 'peer_selection.py',
        'status': 'complete',
        'description': 'Peer discovery, health/latency/capacity scoring, VERSION_TOO_OLD enforcement',
        'test_coverage': 'full',
        'tags': ['integration', 'optional'],
        'blockers': [],
        'notes': '',
    },
    {
        'id': 'peer-network-improvement',
        'name': 'Peer-Contributed Improvements',
        'module': 'peer_improvement.py',
        'status': 'active',
        'description': 'Pipeline to evaluate and promote peer artifacts into the improvement workflow',
        'test_coverage': 'partial',
        'tags': ['delivery', 'self-improvement'],
        'blockers': [],
        'notes': 'urace peer-review [list|evaluate <id>|promote <id>]. Quarantine → safety evaluate → goal queue. Peer identities are SHA256 fingerprints (opaque). Artifact content not auto-sanitized.',
    },

    # ── Self-Improvement ─────────────────────────────────────────────────────
    {
        'id': 'self-evolution-trial',
        'name': 'Self-Evolution Trial Pipeline',
        'module': 'trial/ directory',
        'status': 'stable',
        'description': 'Hermetic containerized trial: snapshot isolation, sealed tests, second-provider revalidation',
        'test_coverage': 'full',
        'tags': ['self-improvement', 'security'],
        'blockers': [],
        'notes': '246 sealed private test cases. Kernel-locked supervisor. No network in container.',
    },
    {
        'id': 'trial-product-concurrency',
        'name': 'Trial / Product Concurrency',
        'module': 'trial/trial_supervisor.py',
        'status': 'complete',
        'description': 'Spec trial and runtime cycle run concurrently as separate supervisor slots',
        'test_coverage': 'none',
        'tags': ['self-improvement', 'delivery'],
        'blockers': [],
        'notes': 'productive_step split into productive_runtime_step and productive_spec_step; ThreadPoolExecutor max_workers=4. Use separate guard files — no shared lock contention.',
    },

    # ── Delivery / Throughput ────────────────────────────────────────────────
    {
        'id': 'multi-executor-planning',
        'name': 'Multi-Executor Parallel Planning',
        'module': 'multi_executor.py',
        'status': 'experimental',
        'description': 'Multiple executors generate plans; best scored proposal selected (Agora pattern)',
        'test_coverage': 'partial',
        'tags': ['delivery', 'core'],
        'blockers': [],
        'notes': 'Disabled by default (config executor.multi_plan_selection.enabled=true to activate). Requires 2+ available providers.',
    },
    {
        'id': 'agora-voting',
        'name': 'Agora Variant Voting',
        'module': 'portfolio.py:agora',
        'status': 'deprecated',
        'description': 'Proposal/vote/decision system for portfolio variant acceptance',
        'test_coverage': 'none',
        'tags': ['optional', 'delivery'],
        'blockers': [],
        'notes': '~500 LOC. Never invoked. Pattern repurposed into multi_executor.py for cycle-level plan selection. Safe to remove from portfolio.py.',
    },
    {
        'id': 'portfolio-controller',
        'name': 'Portfolio Controller',
        'module': 'portfolio.py',
        'status': 'complete',
        'description': 'Bounded deployment-local controller: cohorts, variants, isolation probes',
        'test_coverage': 'partial',
        'tags': ['optional', 'delivery'],
        'blockers': [],
        'notes': 'Agora voting subsystem is the stale part. Cohort/variant mechanics are functional.',
    },
    {
        'id': 'rollback-operation',
        'name': 'Operation Rollback',
        'module': 'cli.py:rollback command',
        'status': 'active',
        'description': 'Restore product files from last accepted stable snapshot',
        'test_coverage': 'partial',
        'tags': ['delivery', 'security'],
        'blockers': [],
        'notes': 'urace rollback [--dry-run] [--json] — restores from stable_path(config). Per-operation granularity requires additional pre-execution snapshot infrastructure.',
    },
    {
        'id': 'freeform-routing',
        'name': 'Freeform Routing Escape Hatch',
        'module': 'freeform_routing.py',
        'status': 'complete',
        'description': 'Unstructured executor calls with resource accounting mirrored into main executor_calls',
        'test_coverage': 'partial',
        'tags': ['optional', 'delivery'],
        'blockers': [],
        'notes': 'Routing call cost now mirrored into state executor_calls[] for feedback loop visibility. Separate JSONL audit retained for full detail.',
    },

    # ── UX ───────────────────────────────────────────────────────────────────
    {
        'id': 'tui-dashboard',
        'name': 'TUI Dashboard',
        'module': 'tui.py',
        'status': 'active',
        'description': 'k9s-style interactive dashboard: lifecycle, events, gates, command input',
        'test_coverage': 'full',
        'tags': ['ux'],
        'blockers': [],
        'notes': 'Functional. Shows real lifecycle/objective state. Score shows n/a until evidence accumulates — expected behavior.',
    },
    {
        'id': 'feature-status-registry',
        'name': 'Feature Status Registry',
        'module': 'runtime_features.py',
        'status': 'active',
        'description': 'Programmatic registry of every URACE feature with operational status',
        'test_coverage': 'full',
        'tags': ['observability', 'ux'],
        'blockers': [],
        'notes': 'This module. Enables improvement cycle prioritization and operator visibility.',
    },
]

# ── Public API ────────────────────────────────────────────────────────────────

def validate() -> None:
    """Raise ValueError if the registry has structural problems."""
    seen_ids: set[str] = set()
    for feat in _FEATURES:
        for key in ('id', 'name', 'module', 'status', 'description', 'test_coverage', 'tags'):
            if key not in feat:
                raise ValueError(f"Feature missing required key '{key}': {feat}")
        if feat['status'] not in STATUS_VALUES:
            raise ValueError(f"Feature {feat['id']!r} has invalid status {feat['status']!r}")
        if feat['test_coverage'] not in ('none', 'partial', 'full'):
            raise ValueError(f"Feature {feat['id']!r} has invalid test_coverage {feat['test_coverage']!r}")
        for tag in feat['tags']:
            if tag not in TAG_VALUES:
                raise ValueError(f"Feature {feat['id']!r} has unknown tag {tag!r}")
        if feat['id'] in seen_ids:
            raise ValueError(f"Duplicate feature id: {feat['id']!r}")
        seen_ids.add(feat['id'])


def all_features() -> list[dict]:
    return [dict(f) for f in _FEATURES]


def by_status(status: str) -> list[dict]:
    return [dict(f) for f in _FEATURES if f['status'] == status]


def by_tag(tag: str) -> list[dict]:
    return [dict(f) for f in _FEATURES if tag in f['tags']]


def summary() -> dict[str, int]:
    result: dict[str, int] = {}
    for f in _FEATURES:
        result[f['status']] = result.get(f['status'], 0) + 1
    return result


def get(feature_id: str) -> dict | None:
    for f in _FEATURES:
        if f['id'] == feature_id:
            return dict(f)
    return None


def stubs() -> list[dict]:
    return by_status('stub')


def improvement_candidates() -> list[dict]:
    """Return stub + stale + review features, core-first."""
    target_statuses = {'stub', 'stale', 'review'}
    candidates = [dict(f) for f in _FEATURES if f['status'] in target_statuses]
    return sorted(candidates, key=lambda f: (0 if 'core' in f['tags'] else 1, f['id']))


# Validate at import time.
validate()
