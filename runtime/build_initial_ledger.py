#!/usr/bin/env python3
"""Build the initial atomic-feature ledger for URACE.

Enumerates every atomic feature across the runtime, trial, and CLI
surfaces, then writes the ledger to urace/exchange/p2p_audit.json.
"""

from __future__ import annotations

import json
from pathlib import Path

features: list[dict] = []
_ids: set[str] = set()


def _fp(feature_id: str) -> str:
    import hashlib
    return hashlib.sha256(feature_id.encode()).hexdigest()


def add(feature_id: str, name: str, description: str, tags, kind_label: str, domain: str = 'software') -> None:
    if feature_id in _ids:
        raise ValueError(f"duplicate feature_id: {feature_id}")
    _ids.add(feature_id)
    features.append({
        "feature_id": feature_id,
        "name": name,
        "description": description,
        "tags": list(tags),
        "kind_label": kind_label,
        "domain": domain,
        "artifact_discovery": {"kind": "runtime_bundle", "peer_exchange": True},
        "borrow_price_units": 0,
        "owner": None,
        "initial_ledger": True,
        "canonical_fingerprint": _fp(feature_id),
    })


# ===================== RUNTIME: a2a_server.py =====================
add("rt-a2a-protocol", "A2A JSON-RPC protocol v1.0", "JSON-RPC/HTTP agent-to-agent protocol with 1MB request cap and session states.", ["a2a_server", "protocol"], "protocol")
add("rt-a2a-rpc-error", "A2A RpcError", "Typed RPC error type.", ["a2a_server", "error"], "schema")
add("rt-a2a-fields", "A2A field validator", "Validate allowed/required RPC fields.", ["a2a_server"], "mechanism")
add("rt-a2a-identifier", "A2A identifier validator", "Validate rpc id format.", ["a2a_server"], "mechanism")
add("rt-a2a-adapter", "A2A Adapter", "Adapter wiring CLI parsers to A2A RPC.", ["a2a_server"], "mechanism")
add("rt-a2a-handler", "A2A HTTP Handler", "BaseHTTPRequestHandler dispatcher.", ["a2a_server"], "mechanism")
add("rt-a2a-http-server", "A2A ThreadingHTTPServer", "Threaded HTTPS A2A server.", ["a2a_server"], "mechanism")
add("rt-a2a-serve", "A2A serve()", "Serve A2A with policy and bearer-token auth.", ["a2a_server", "cli"], "mechanism")

# ===================== analytics.py =====================
add("rt-analytics-capabilities", "Analytics capabilities", "Describe analytics capabilities.", ["analytics"], "mechanism")
add("rt-analytics-collect", "Analytics collect", "Collect state/vitals into tabular rows.", ["analytics"], "mechanism")
add("rt-analytics-flatten", "Analytics flatten", "Flatten nested payload to dotted keys.", ["analytics"], "mechanism")
add("rt-analytics-csv", "Analytics CSV writer", "Atomic CSV table writer.", ["analytics"], "mechanism")
add("rt-analytics-dashboard", "Analytics HTML dashboard", "Render analytics dashboard HTML.", ["analytics"], "mechanism")
add("rt-analytics-portable-export", "Portable analytics export", "Export CSV/HTML/XLSX bundle.", ["analytics"], "mechanism")

# ===================== api_interface.py =====================
add("rt-api-request-error", "API RequestError", "Typed error for API interface.", ["api_interface"], "schema")
add("rt-api-metadata-parser", "API parser metadata descriptor", "Expose argparse parser metadata.", ["api_interface"], "mechanism")
add("rt-api-bounded-capture", "API BoundedCapture", "Size-bounded stdout capture.", ["api_interface", "security"], "mechanism")
add("rt-api-metadata", "API metadata view", "Build metadata view for parser.", ["api_interface"], "mechanism")
add("rt-api-scalar", "API scalar coercion", "Coerce python values to API scalars.", ["api_interface"], "mechanism")
add("rt-api-build-argv", "API build_argv", "Compose argv from command+params.", ["api_interface"], "mechanism")
add("rt-api-persistent", "API persistent-mode", "Infinite-cycle persistent run gate.", ["api_interface"], "mechanism")
add("rt-api-event-stream", "API EventStream", "Streamed event TextIOBase.", ["api_interface"], "mechanism")
add("rt-api-execute", "API execute()", "Run CLI command through API with capture/stream.", ["api_interface"], "mechanism")

# ===================== authenticated_journal.py =====================
add("rt-journal-append", "Journal append_row", "Append row to tamper-evident Parquet ledger.", ["authenticated_journal", "security"], "mechanism")
add("rt-journal-coverage", "Journal coverage", "Coverage report against checkpoint.", ["authenticated_journal"], "mechanism")

# ===================== authority.py =====================
add("rt-authority-outcomes", "Authority outcome states", "AUTONOMOUSLY_AUTHORIZED/DENIED/REQUIRES_AUTHORITATIVE_DECISION/UNRESOLVED.", ["authority", "governance"], "schema")
add("rt-authority-reserved-phrases", "Reserved signal phrases", "Reserved weakening/attack phrases.", ["authority", "security"], "schema")
add("rt-authority-weakening-detector", "Weakening request detector", "Flag weakening-verb requests.", ["authority", "security"], "mechanism")
add("rt-authority-resolve", "Authority resolve()", "Resolve authority boundary for action.", ["authority"], "mechanism")
add("rt-authority-record-resolution", "Authority record_resolution", "Record authority decision.", ["authority"], "mechanism")

# ===================== auto_goals.py =====================
add("rt-auto-goals-select", "Auto-goal selector", "Automatic goal selection.", ["auto_goals"], "mechanism")

# ===================== bootstrap.py =====================
add("rt-bootstrap-complete", "Bootstrap complete", "Finalize runtime bootstrap.", ["bootstrap", "lifecycle"], "mechanism")

# ===================== cli.py =====================
add("cli-json-xml", "CLI JSON->XML", "Convert JSON output to XML.", ["cli"], "mechanism")
add("cli-freeform-validate", "Freeform query validator", "Bound freeform input bytes.", ["cli", "security"], "mechanism")
add("cli-print-fmt", "CLI print formatter", "Human/json/xml output printer.", ["cli"], "mechanism")
add("cli-xml-stream", "CLI XML stream", "Streaming XML conversion.", ["cli"], "mechanism")
add("cli-scope-target", "Scope target resolver", "Resolve scope expr -> target.", ["cli"], "mechanism")
add("cli-portfolio-owner-start", "Portfolio-owner launcher", "Start default portfolio owner subprocess.", ["cli", "portfolio"], "mechanism")
add("cli-portfolio-attach", "Portfolio-owner attach-activity", "Attach to portfolio owner.", ["cli", "portfolio"], "mechanism")
add("cli-parse-cycles", "Cycle count parser", "Parse '--cycles' including infinite.", ["cli"], "mechanism")
add("cli-refresh-analytics", "Analytics refresh (CLI)", "Refresh analytics mid-run.", ["cli"], "mechanism")
add("cli-record-executor-failure", "Executor-failure recorder", "Record systematic executor failures.", ["cli", "executor"], "mechanism")
add("cli-record-blocker", "Blocker recorder", "Record workflow blocker.", ["cli"], "mechanism")
add("cli-auto-escalate-blocker", "Blocker auto-escalation", "Auto-escalate blockers.", ["cli"], "mechanism")
add("cli-auto-resolve-blockers", "Blocker auto-resolve", "Auto-resolve stale blockers.", ["cli"], "mechanism")
add("cli-record-assessment-gap", "Assessment gap recorder", "Record assessment gap by dimension.", ["cli"], "mechanism")
add("cli-resolve-assessment-gap", "Assessment gap resolver", "Resolve assessment gap.", ["cli"], "mechanism")
add("cli-transaction-accepted", "Transaction-accepted check", "Check transaction acceptance.", ["cli"], "mechanism")
add("cli-reconcile-transaction", "Transaction reconciler", "Reconcile pending transactions.", ["cli"], "mechanism")
add("cli-finalize-committed-txn", "Finalize committed transaction", "Post-finalize applied transaction.", ["cli"], "mechanism")
add("cli-stable-path", "Stable snapshot path", "Resolve stable snapshot path.", ["cli"], "mechanism")
add("cli-runtime-files", "Runtime file inventory", "List runtime image files.", ["cli"], "mechanism")
add("cli-runtime-stable-path", "Runtime stable path", "Runtime stable image path.", ["cli"], "mechanism")
add("cli-write-runtime-snapshot", "Write runtime snapshot", "Write runtime image snapshot.", ["cli", "snapshot"], "mechanism")
add("cli-validate-product", "Product validator", "Validate product against baseline.", ["cli"], "mechanism")
add("cli-write-stable-snapshot", "Write stable snapshot", "Write stable product snapshot.", ["cli", "snapshot"], "mechanism")
add("cli-ensure-stable-product", "Ensure stable product", "Guarantee stable product exists.", ["cli"], "mechanism")
add("cli-product-digest", "Product digest", "Deterministic product digest.", ["cli", "integrity"], "mechanism")
add("cli-initial-state", "Initial state factory", "Produce baseline state record.", ["cli"], "mechanism")
add("cli-seed-confirmed-onboard", "Seed confirmed onboard", "Seed confirmed onboarding.", ["cli", "lifecycle"], "mechanism")
add("cli-progress-vector", "Progress vector update", "Advance progress vector + stagnation.", ["cli"], "mechanism")
add("cli-recovery-manifest-emit", "Recovery manifest emit", "Emit recovery manifest.", ["cli", "recovery"], "mechanism")
add("cli-observe-progress", "Observe-progress step", "Observe step progress.", ["cli"], "mechanism")
add("cli-discover", "Discover step", "Discovery step of cycle.", ["cli"], "mechanism")
add("cli-plan-for", "Plan-for step", "Plan for objective.", ["cli"], "mechanism")
add("cli-refresh-scope-priorities", "Scope-priority refresh", "Refresh scope priorities.", ["cli"], "mechanism")
add("cli-material-state-sig", "Material state signature", "Signature of material state.", ["cli", "integrity"], "mechanism")
add("cli-executor-discovery-due", "Executor rediscovery due", "Detect executor rediscovery due.", ["cli", "executor"], "mechanism")
add("cli-stale-derived-manifests", "Stale derived manifests scan", "Detect stale derived manifests.", ["cli", "integrity"], "mechanism")
add("cli-current-spec-version", "Current spec version", "Resolve active spec version.", ["cli", "spec"], "mechanism")
add("cli-spec-audit-due", "Spec audit due", "Spec audit due check.", ["cli", "spec"], "mechanism")
add("cli-run-spec-audit", "Run spec audit", "Trigger spec audit from CLI.", ["cli", "spec"], "mechanism")
add("cli-executor-execution-allowed", "Executor-execution policy gate", "Policy gate for executor execution.", ["cli", "executor"], "mechanism")
add("cli-defer-executor-capacity", "Executor-capacity defer", "Defer when executor capacity exhausted.", ["cli", "executor"], "mechanism")
add("cli-retain-call-usage", "Retain call usage", "Retain call usage metadata.", ["cli"], "mechanism")
add("cli-current-route-usage", "Current route usage", "Compute current route usage.", ["cli"], "mechanism")
add("cli-executor-readiness-capability", "Executor readiness capability", "Resolve executor readiness capability.", ["cli", "executor"], "mechanism")
add("cli-refresh-executor-availability", "Executor availability refresh", "Refresh executor availability.", ["cli", "executor"], "mechanism")
add("cli-discover-with-executor", "Discover via executor", "Executor-driven discovery.", ["cli", "executor"], "mechanism")
add("cli-transition", "State transition", "Workflow-state transition primitive.", ["cli", "lifecycle"], "mechanism")
add("cli-execute-with-executor", "Execute via executor", "Executor-driven execution.", ["cli", "executor"], "mechanism")
add("cli-core-fault-descriptor", "Core fault descriptor", "Trusted descriptor for a thrown fault.", ["cli", "recovery"], "mechanism")
add("cli-runtime-version-digest", "Runtime version digest", "Digest of runtime version artifacts.", ["cli", "integrity"], "mechanism")
add("cli-core-auto-repair", "Core auto-repair", "Attempt core-fault auto-repair.", ["cli", "recovery"], "mechanism")
add("cli-evaluate-wake-conditions", "Wake-condition evaluator", "Evaluate wake conditions.", ["cli", "lifecycle"], "mechanism")
add("cli-run-onboard-gate", "Onboard gate", "Gate before cycles begin.", ["cli", "lifecycle"], "mechanism")
add("cli-verify-wake-registrations", "Wake registration verifier", "Verify wake-condition registrations.", ["cli", "lifecycle"], "mechanism")
add("cli-emit-gap", "Emit gap", "Record a gap entry in state.", ["cli"], "mechanism")
add("cli-emit-trace", "Emit trace", "Record a structured trace line.", ["cli"], "mechanism")
add("cli-inspect-list", "Inspect list helper", "Common inspect list rendering.", ["cli", "inspection"], "mechanism")
add("cli-help-action", "Help action", "argparse help action.", ["cli"], "mechanism")

# ===================== cognitive_resume.py =====================
add("rt-crc-generate", "CRC generate", "Build cognitive-resume context.", ["cognitive_resume"], "mechanism")
add("rt-crc-is-stale", "CRC staleness check", "Detect stale CRC.", ["cognitive_resume"], "mechanism")
add("rt-crc-staleness-gap", "CRC staleness gap", "Describe staleness gap.", ["cognitive_resume"], "mechanism")
add("rt-crc-build-executor-context", "CRC->executor context", "Build executor context from CRC.", ["cognitive_resume", "executor"], "mechanism")
add("rt-crc-save", "CRC save", "Persist CRC file.", ["cognitive_resume"], "mechanism")
add("rt-crc-load", "CRC load", "Load CRC file.", ["cognitive_resume"], "mechanism")
add("rt-crc-load-or-generate", "CRC load-or-generate", "Load or generate CRC.", ["cognitive_resume"], "mechanism")

# ===================== command_surface.py =====================
add("rt-cmd-compat", "Compat command set", "Backwards-compat command names.", ["command_surface"], "schema")
add("rt-cmd-phantoms", "Phantom commands", "Deprecated phantom commands.", ["command_surface"], "schema")
add("rt-cmd-call-limit", "--call-limit validator", "Validate call-limit value.", ["command_surface"], "mechanism")
add("rt-cmd-boolean", "Boolean argparse coercer", "Boolean arg coercion.", ["command_surface"], "mechanism")
add("rt-cmd-output-options", "Output option group", "--format and output flags.", ["command_surface"], "mechanism")
add("rt-cmd-product-group", "product subcommand group", "'product' command tree.", ["command_surface", "cli"], "mechanism")
add("rt-cmd-watch-group", "watch subcommand group", "'watch' command tree.", ["command_surface", "cli"], "mechanism")
add("rt-cmd-configuration-group", "configuration subcommand group", "'configuration' command tree.", ["command_surface", "cli"], "mechanism")
add("rt-cmd-child-parsers", "Child parser enumerator", "Enumerate child parsers.", ["command_surface"], "mechanism")
add("rt-cmd-help-parser", "Help parser factory", "Help parser for command path.", ["command_surface"], "mechanism")
add("rt-cmd-operation-parsers", "Operation subparsers", "Register operation subparsers.", ["command_surface"], "mechanism")
add("rt-cmd-finalize", "Parser finalize", "Finalize parser.", ["command_surface"], "mechanism")
add("rt-cmd-validate", "CLI arg validator", "Validate parsed args.", ["command_surface"], "mechanism")
add("rt-cmd-validate-budget", "Budget validator", "Validate daily/monthly budget.", ["command_surface"], "mechanism")
add("rt-cmd-validate-evaluation", "Evaluation validator", "Validate evaluation changes.", ["command_surface"], "mechanism")
add("rt-cmd-catalog", "Command catalog", "List available commands.", ["command_surface"], "mechanism")
add("rt-cmd-status-group", "status subcommand group", "'status' command tree.", ["command_surface", "cli"], "mechanism")
add("rt-cmd-match-quoted", "Quoted command matcher", "Match quoted command strings.", ["command_surface"], "mechanism")
add("rt-cmd-forward", "Command forwarder", "Forward CLI command to cwd.", ["command_surface"], "mechanism")
add("rt-cmd-read-only", "Read-only argv predicate", "Classify argv as read-only.", ["command_surface"], "mechanism")
add("rt-cmd-product-git-group", "product git subcommand", "'product git' GitHub operation tree.", ["command_surface", "cli", "github"], "mechanism")
add("rt-cmd-github-workflow-config", "github-workflow config subcommand", "'configuration github-workflow' auto git policy.", ["command_surface", "cli", "github"], "mechanism")
add("rt-cmd-exchange-bootstrap-group", "exchange bootstrap subcommand", "'exchange bootstrap' P2P rendezvous peer management.", ["command_surface", "cli", "p2p"], "mechanism")

# ===================== portfolio_github.py =====================
add("rt-pgh-workflow-defaults", "GitHub workflow defaults", "Default auto-pull/commit/push policy constants.", ["portfolio_github", "github"], "schema")
add("rt-pgh-workflow-settings", "GitHub workflow settings", "Effective github_workflow config merged with defaults.", ["portfolio_github", "github"], "mechanism")
add("rt-pgh-clone-repo", "Clone GitHub repo", "git clone owner/repo to local path.", ["portfolio_github", "github"], "mechanism")
add("rt-pgh-head-commit", "GitHub head commit", "Read HEAD commit SHA from clone.", ["portfolio_github", "github"], "mechanism")
add("rt-pgh-validate-subcommand", "Validate git subcommand", "Block unsafe git subcommands; allowlist enforced.", ["portfolio_github", "github", "security"], "mechanism")
add("rt-pgh-run-git", "Run git in clone", "Execute validated git command in product clone_path.", ["portfolio_github", "github"], "mechanism")
add("rt-pgh-auto-pull", "Auto-pull hook", "Pull latest from origin if auto_pull enabled.", ["portfolio_github", "github"], "mechanism")
add("rt-pgh-auto-commit", "Auto-commit hook", "Commit after improvement cycle if auto_commit enabled.", ["portfolio_github", "github"], "mechanism")
add("rt-pgh-auto-push", "Auto-push hook", "Push to origin if auto_push enabled.", ["portfolio_github", "github"], "mechanism")
add("rt-pgh-env-auto-providers", "Executor env-var auto providers", "Synthesize executor providers from ANTHROPIC_API_KEY / OPENAI_API_KEY.", ["executor", "github", "zero_config"], "mechanism")

# ===================== _common.py =====================
add("rt-common-path-roots", "Runtime path roots", "RUNTIME_ROOT/SYSTEM_ROOT/ROOT/CONFIG_PATH.", ["_common"], "schema")
add("rt-common-now", "ISO now()", "ISO-8601 timezone-aware now.", ["_common"], "mechanism")
add("rt-common-identifier", "Prefixed id", "Prefixed random identifier.", ["_common"], "mechanism")
add("rt-common-atomic-text", "Atomic text write", "Atomic text file write.", ["_common", "integrity"], "mechanism")
add("rt-common-atomic-json", "Atomic JSON write", "Atomic JSON file write.", ["_common", "integrity"], "mechanism")
add("rt-common-durable-unlink", "Durable unlink", "Durable file removal.", ["_common"], "mechanism")
add("rt-common-process-exists", "Process exists probe", "Check PID is live.", ["_common"], "mechanism")
add("rt-common-state-lock", "State lock context", "State-lock context manager.", ["_common"], "mechanism")
add("rt-common-published-state-lock", "Published state lock", "Publish lock to peers.", ["_common"], "mechanism")
add("rt-common-load-config", "Load config", "Load config.json.", ["_common"], "mechanism")
add("rt-common-save-config", "Save config", "Persist config.", ["_common"], "mechanism")
add("rt-common-copy-mapping", "Mapping copier", "Deep copy mapping.", ["_common"], "mechanism")
add("rt-common-state-path", "State path", "Resolve state.json path.", ["_common"], "mechanism")
add("rt-common-load-state", "Load state", "Load state.json (lock).", ["_common"], "mechanism")
add("rt-common-load-state-read", "Load state read-only", "Load state without lock.", ["_common"], "mechanism")
add("rt-common-save-state", "Save state", "Persist state atomically.", ["_common"], "mechanism")
add("rt-common-transaction-path", "Transaction journal path", "Resolve transaction journal path.", ["_common"], "mechanism")
add("rt-common-input-directory", "Input directory", "Resolve inbox directory.", ["_common"], "mechanism")
add("rt-common-technique-gate", "T1..T6 technique gate", "Gate T1-T6 techniques.", ["_common", "governance"], "mechanism")
add("rt-common-bridge-record", "Bridge record builder", "Build canonical bridge record.", ["_common", "integration"], "mechanism")
add("rt-common-orchestrator-record", "Orchestrator record builder", "Build canonical orchestrator record.", ["_common", "integration"], "mechanism")
add("rt-common-scheduled-task-due", "Scheduled task due", "Check if scheduled task is due.", ["_common"], "mechanism")
add("rt-common-nullable-limit", "Nullable limit", "Resolve nullable numeric settings.", ["_common"], "mechanism")
add("rt-common-integration-context", "Integration context", "Return integration env context.", ["_common", "integration"], "mechanism")

# ===================== compaction.py =====================
add("rt-compact-engine", "CompactionEngine", "Context-ledger compaction engine.", ["compaction"], "mechanism")
add("rt-compact-manifest-path", "Manifest path", "Resolve compaction manifest path.", ["compaction"], "mechanism")
add("rt-compact-load-manifest", "Load manifest", "Load compaction manifest.", ["compaction"], "mechanism")
add("rt-compact-save-manifest", "Save manifest", "Persist compaction manifest.", ["compaction"], "mechanism")
add("rt-compact-verify-startup", "Verify manifest on startup", "Startup manifest verification.", ["compaction", "integrity"], "mechanism")
add("rt-compact-retention-violations", "Retention violations check", "Detect retention violations.", ["compaction", "governance"], "mechanism")
add("rt-compact-archive-ceiling", "Archive ceiling check", "Enforce archive count ceiling.", ["compaction"], "mechanism")
add("rt-compact-status", "Compaction status", "Report compaction status.", ["compaction"], "mechanism")
add("rt-compact-write-index", "Write compaction index", "Write per-archive index.", ["compaction"], "mechanism")
add("rt-compact-load-index", "Load compaction index", "Load per-archive index.", ["compaction"], "mechanism")
add("rt-compact-amendments", "Archive amendments", "Append/load archive amendments.", ["compaction"], "mechanism")
add("rt-compact-canonical-digest", "Canonical compaction digest", "Deterministic digest of records.", ["compaction", "integrity"], "mechanism")
add("rt-compact-prohibited-fields", "Prohibited fields set", "Fields never compacted.", ["compaction"], "schema")

# ===================== context_relations.py =====================
add("rt-ctx-build", "Context build graph", "Build relation graph from passages.", ["context_relations"], "mechanism")
add("rt-ctx-related", "Related nodes", "Find related nodes by depth.", ["context_relations"], "mechanism")
add("rt-ctx-attention", "Attention computation", "Compute attention weights.", ["context_relations"], "mechanism")
add("rt-ctx-from-state", "Context from state", "Build graph from state.", ["context_relations"], "mechanism")

# ===================== continuation.py =====================
add("rt-cont-degrade", "Confidence degrade", "Degrade confidence on failure.", ["continuation"], "mechanism")
add("rt-cont-handle-unspecified", "Handle unspecified outcome", "Handle unspecified outcomes.", ["continuation"], "mechanism")
add("rt-cont-reset-confidence", "Reset confidence", "Reset confidence tracker.", ["continuation"], "mechanism")

# ===================== credit_ledger.py =====================
add("p2p-credit-schema", "Credit ledger schema v1", "urace-credit-ledger-v1.", ["credit_ledger", "p2p", "economics"], "schema")
add("p2p-credit-baseline-grant", "Baseline grant (3)", "New peers get 3 baseline requests.", ["credit_ledger", "economics"], "contract")
add("p2p-credit-base-units", "Credit base units (8dp)", "Fixed-point 8-decimal unit.", ["credit_ledger"], "schema")
add("p2p-credit-display-conv", "Credit display conversion", "to/from display strings.", ["credit_ledger"], "mechanism")
add("p2p-credit-velocity-mult", "Velocity multiplier (90d EMA)", "EMA velocity multiplier.", ["credit_ledger", "economics"], "mechanism")
add("p2p-credit-wilson-lower", "Wilson lower bound", "Wilson lower confidence interval helper.", ["credit_ledger", "statistics"], "mechanism")
add("p2p-credit-peer-quality", "Peer quality weights", "Compute peer quality weights.", ["credit_ledger"], "mechanism")
add("p2p-credit-network-supply", "Network supply factor", "Network-wide supply pressure.", ["credit_ledger", "economics"], "mechanism")
add("p2p-credit-peer-cap", "Per-peer earn cap", "Peer earning cap in units.", ["credit_ledger", "economics"], "mechanism")
add("p2p-credit-peer-trust", "Peer trust weights", "Peer trust weight table.", ["credit_ledger"], "mechanism")
add("p2p-credit-peer-held-features", "Peer held features", "Set of features held by peer.", ["credit_ledger"], "mechanism")
add("p2p-credit-rep-source-trade", "Trade reputation source", "Trade=market_rep, never earned_rep.", ["credit_ledger"], "schema")
add("p2p-credit-earned-balance", "Earned balance", "Report earned-rep balance.", ["credit_ledger"], "mechanism")
add("p2p-credit-earn-units", "Earn units", "Grant earned units.", ["credit_ledger"], "mechanism")
add("p2p-credit-spend-units", "Spend units", "Debit units.", ["credit_ledger"], "mechanism")
add("p2p-credit-earn", "Earn (wrapper)", "Earn compat wrapper.", ["credit_ledger"], "mechanism")
add("p2p-credit-spend", "Spend (wrapper)", "Spend compat wrapper.", ["credit_ledger"], "mechanism")
add("p2p-credit-balance", "Balance", "Peer balance.", ["credit_ledger"], "mechanism")
add("p2p-credit-history", "History", "Recent ledger rows for peer.", ["credit_ledger"], "mechanism")
add("p2p-credit-summary", "Credit summary", "Aggregate credit summary.", ["credit_ledger"], "mechanism")
add("p2p-credit-feature-complexity", "Feature complexity score", "LOC/deps/tests complexity.", ["credit_ledger", "economics"], "mechanism")
add("p2p-credit-feature-borrow-cost", "Feature borrow cost", "Borrow cost units.", ["credit_ledger", "economics"], "mechanism")
add("p2p-credit-borrow-cost-rep", "Borrow cost with rep", "Borrow cost adjusted by reputation.", ["credit_ledger", "economics"], "mechanism")
add("p2p-credit-supply-pressure", "Supply pressure multiplier", "Supply pressure modifier.", ["credit_ledger", "economics"], "mechanism")
add("p2p-credit-rep-tier-bonus", "Reputation tier bonus", "Reputation tier bonus.", ["credit_ledger"], "mechanism")
add("p2p-credit-approved-floor", "Approved-gate floor", "Dynamic approved-gate floor.", ["credit_ledger"], "mechanism")
add("p2p-credit-combined-rep", "Combined reputation score", "Combined reputation across signals.", ["credit_ledger"], "mechanism")
add("p2p-credit-feature-creator", "Feature creator id", "Resolve creator for a feature.", ["credit_ledger"], "mechanism")
add("p2p-credit-escrow-lock", "Escrow lock", "Lock credits into escrow peer.", ["credit_ledger", "escrow"], "mechanism")
add("p2p-credit-escrow-release", "Escrow release", "Release escrowed credits.", ["credit_ledger", "escrow"], "mechanism")
add("p2p-credit-escrow-refund", "Escrow refund", "Refund escrowed credits.", ["credit_ledger", "escrow"], "mechanism")
add("p2p-credit-distribution-fee", "Distribution fee units", "Distribution fee computation.", ["credit_ledger", "economics"], "mechanism")
add("p2p-credit-pay-distribution-fee", "Pay distribution fee", "Debit distribution fee.", ["credit_ledger", "economics"], "mechanism")
add("p2p-credit-jaccard-sim", "Jaccard token sim", "Token-level similarity.", ["credit_ledger"], "mechanism")
add("p2p-credit-network-complexity-floor", "Network complexity floor", "Consensus complexity floor.", ["credit_ledger", "economics"], "mechanism")
add("p2p-credit-derivative-penalty", "Derivative penalty", "Penalty for derivative features.", ["credit_ledger", "economics"], "mechanism")
add("p2p-credit-max-mintable", "Max mintable units", "Supply cap for mint-per-adoption.", ["credit_ledger", "economics"], "mechanism")
add("p2p-credit-mint-per-adoption", "Mint per adoption", "Mint amount for an adoption event.", ["credit_ledger", "economics"], "mechanism")
add("p2p-credit-feature-earn-cap", "Feature earn cap", "Earn cap by feature complexity.", ["credit_ledger", "economics"], "mechanism")
add("p2p-credit-borrow-jitter", "Borrow jitter frac", "±3% jitter on borrow cost.", ["credit_ledger", "economics"], "schema")
add("p2p-credit-consensus-borrow-floor", "Consensus borrow floor", "Network-consensus borrow floor.", ["credit_ledger"], "mechanism")
add("p2p-credit-apply-borrow-cost", "Apply borrow cost", "Charge borrower.", ["credit_ledger"], "mechanism")
add("p2p-credit-escrow-jitter", "Escrow jitter frac", "±4% escrow jitter.", ["credit_ledger"], "schema")
add("p2p-credit-consensus-escrow-floor", "Consensus escrow floor", "Network-consensus escrow floor.", ["credit_ledger"], "mechanism")
add("p2p-credit-escrow-budget", "Escrow budget", "Escrow budget units.", ["credit_ledger"], "mechanism")

# ===================== data_transport.py =====================
add("rt-data-transport-error", "TransportError", "Typed transport error.", ["data_transport"], "schema")
add("rt-data-input-rows", "input_rows()", "Normalize input rows.", ["data_transport"], "mechanism")
add("rt-data-path-of", "path_of record", "Resolve record path.", ["data_transport"], "mechanism")
add("rt-data-validate-rows", "Validate rows", "Validate rows.", ["data_transport"], "mechanism")
add("rt-data-table", "Table extractor", "Extract table from record.", ["data_transport"], "mechanism")
add("rt-data-read", "Record read", "Read record.", ["data_transport"], "mechanism")
add("rt-data-verify", "Record verify", "Verify record integrity.", ["data_transport", "integrity"], "mechanism")
add("rt-data-atomic-file", "Atomic file", "Atomic file writer.", ["data_transport"], "mechanism")
add("rt-data-push", "Record push", "Push rows into record.", ["data_transport"], "mechanism")
add("rt-data-perform", "Transport perform", "Perform data-source action.", ["data_transport"], "mechanism")
add("rt-data-public-record", "Public record view", "Sanitized public record.", ["data_transport"], "mechanism")
add("rt-data-auto-sync", "Auto-sync sources", "Auto-sync data sources.", ["data_transport"], "mechanism")

# ===================== decision_feedback.py =====================
add("rt-df-settings", "Decision-feedback settings", "Module settings.", ["decision_feedback"], "mechanism")
add("rt-df-validate-forecast", "Validate forecast", "Validate forecast shape.", ["decision_feedback"], "mechanism")
add("rt-df-score", "Score forecast", "Forecast score.", ["decision_feedback"], "mechanism")
add("rt-df-indexes", "Build indexes", "Build feedback indexes.", ["decision_feedback"], "mechanism")
add("rt-df-context", "Decision context", "Build decision context.", ["decision_feedback"], "mechanism")
add("rt-df-context-binding", "Context binding", "Bind context to objective.", ["decision_feedback"], "mechanism")
add("rt-df-existing-prior", "Existing prior", "Lookup existing prior.", ["decision_feedback"], "mechanism")
add("rt-df-view", "Decision view", "Full decision view packet.", ["decision_feedback"], "mechanism")
add("rt-df-register-forecast", "Register forecast", "Register forecast.", ["decision_feedback"], "mechanism")
add("rt-df-refresh", "Refresh feedback", "Refresh feedback.", ["decision_feedback"], "mechanism")
add("rt-df-assess", "Assess feedback", "Assess feedback vs outcome.", ["decision_feedback"], "mechanism")
add("rt-df-compact", "Compact result", "Compact feedback result.", ["decision_feedback"], "mechanism")

# ===================== decision_record.py =====================
add("rt-dr-create", "Create decision record", "Create new decision record.", ["decision_record", "governance"], "mechanism")
add("rt-dr-flag-provenance-revised", "Flag provenance revised", "Flag revised provenance.", ["decision_record"], "mechanism")
add("rt-dr-supersede", "Supersede record", "Mark record superseded.", ["decision_record"], "mechanism")
add("rt-dr-attach-outcome-feedback", "Attach outcome feedback", "Attach outcome feedback.", ["decision_record"], "mechanism")
add("rt-dr-traverse-reasoning-chain", "Traverse reasoning chain", "Walk reasoning chain.", ["decision_record"], "mechanism")
add("rt-dr-load", "Load decision records", "Load records from state.", ["decision_record"], "mechanism")
add("rt-dr-save", "Save decision record", "Persist decision record.", ["decision_record"], "mechanism")
add("rt-dr-find-by-id", "Find by id", "Find record by id.", ["decision_record"], "mechanism")
add("rt-dr-update-in-state", "Update in state", "Mutate in-state record.", ["decision_record"], "mechanism")
add("rt-dr-provenance-revised-gaps", "Provenance-revised gap ids", "List provenance-revised gaps.", ["decision_record"], "mechanism")
add("rt-dr-check-gaps", "Check decision gaps", "Scan decision gaps.", ["decision_record"], "mechanism")

# ===================== derived_artifacts.py =====================
add("rt-derived-content-hash", "Content hash", "Hash content payload.", ["derived_artifacts", "integrity"], "mechanism")
add("rt-derived-reference-hash", "Reference hash", "Hash reference descriptor.", ["derived_artifacts", "integrity"], "mechanism")
add("rt-derived-seal", "Derived seal", "Seal derived artifact.", ["derived_artifacts"], "mechanism")
add("rt-derived-verify", "Derived verify", "Verify derived artifact.", ["derived_artifacts"], "mechanism")
add("rt-derived-saved-refs", "Saved refs", "Enumerate saved refs.", ["derived_artifacts"], "mechanism")

# ===================== destination.py =====================
add("rt-dest-drift-thresholds", "Drift thresholds", "DRIFT_FLAG=0.30, DRIFT_BLOCK=0.65.", ["destination"], "schema")
add("rt-dest-redefine-signals", "Redefine signals", "Destination redefine signals.", ["destination"], "schema")
add("rt-dest-anchor-from-config", "Anchor from config", "Load destination anchor from config.", ["destination"], "mechanism")
add("rt-dest-drift-score", "Drift score", "Compute drift score.", ["destination"], "mechanism")
add("rt-dest-check-anchor", "Check anchor integrity", "Verify destination anchor integrity.", ["destination", "governance"], "mechanism")
add("rt-dest-drift-evidence", "Drift evidence", "Build drift evidence.", ["destination"], "mechanism")

# ===================== equity_auto_trade.py =====================
add("p2p-equity-schema", "Equity auto-trade schema v1", "urace-equity-auto-trade-v1.", ["equity_auto_trade", "p2p"], "schema")
add("p2p-equity-listing-expiry", "Listing expiry (30d)", "Listings expire in 30 days.", ["equity_auto_trade"], "schema")
add("p2p-equity-depletion-states", "Depletion states", "HEALTHY/SLOWING/NEAR_DEPLETED/DEPLETED.", ["equity_auto_trade"], "schema")
add("p2p-equity-depletion-status", "Feature depletion status", "Classify feature depletion.", ["equity_auto_trade"], "mechanism")
add("p2p-equity-lucrativity", "Lucrativity assessment", "Score feature profitability.", ["equity_auto_trade"], "mechanism")
add("p2p-equity-config-load", "Load trade config", "Load auto-trade config.", ["equity_auto_trade"], "mechanism")
add("p2p-equity-config-save", "Save trade config", "Save auto-trade config.", ["equity_auto_trade"], "mechanism")
add("p2p-equity-config-update", "Update trade config", "Update auto-trade config section.", ["equity_auto_trade"], "mechanism")
add("p2p-equity-wash-check", "Wash-trading check", "Detect wash trades within 24h.", ["equity_auto_trade", "security"], "mechanism")
add("p2p-equity-price-momentum", "Price momentum validator", "Enforce 1.5× 7d median.", ["equity_auto_trade", "security"], "mechanism")
add("p2p-equity-list-for-sale", "List for sale", "List equity for sale.", ["equity_auto_trade"], "mechanism")
add("p2p-equity-cancel-listing", "Cancel listing", "Cancel equity listing.", ["equity_auto_trade"], "mechanism")
add("p2p-equity-fill-listing", "Fill listing", "Fill equity listing.", ["equity_auto_trade"], "mechanism")
add("p2p-equity-open-listings", "Open listings", "List current open listings.", ["equity_auto_trade"], "mechanism")
add("p2p-equity-auto-buy", "Auto-buy", "Automated equity buyer.", ["equity_auto_trade"], "mechanism")
add("p2p-equity-auto-sell", "Auto-sell", "Automated equity seller.", ["equity_auto_trade"], "mechanism")
add("p2p-equity-auto-mint-minimal", "Auto-mint minimal features", "Mint minimal starter features.", ["equity_auto_trade"], "mechanism")

# ===================== evolution_guard.py =====================
add("security-protected-files", "Protected kernel files", "Immutable kernel path list.", ["evolution_guard", "security"], "schema")
add("security-verify-release-signature", "Verify release signature", "Ed25519 signature verification.", ["evolution_guard", "security"], "mechanism")
add("security-verify-multi-sig", "Verify multi-sig", "Threshold multi-signature verification.", ["evolution_guard", "security"], "mechanism")
add("security-log-rekor", "Log to Rekor", "Transparency log integration.", ["evolution_guard", "security"], "integration")
add("security-anchor-opentimestamps", "Anchor OpenTimestamps", "Bitcoin OTS anchoring.", ["evolution_guard", "security"], "integration")
add("security-p2p-keygen", "P2P keygen", "Generate per-peer keypair.", ["evolution_guard", "security"], "mechanism")
add("security-protected-config-paths", "Protected config paths", "Protected config path tuple.", ["evolution_guard", "security"], "schema")
add("security-digest-file", "File digest", "Hash a file.", ["evolution_guard"], "mechanism")
add("security-corpus-fingerprint", "Corpus fingerprint", "Fingerprint product corpus.", ["evolution_guard"], "mechanism")
add("security-build-update-bundle", "Build P2P update bundle", "Build signed update bundle.", ["evolution_guard", "security"], "mechanism")
add("security-verify-update-bundle", "Verify P2P update bundle", "Verify update bundle.", ["evolution_guard", "security"], "mechanism")
add("security-apply-update-bundle", "Apply P2P update bundle", "Apply verified bundle.", ["evolution_guard", "security"], "mechanism")
add("security-kernel-hashes", "Kernel hashes", "Expected kernel hashes.", ["evolution_guard"], "mechanism")
add("security-validate-candidate", "Validate candidate", "Validate candidate activation.", ["evolution_guard", "governance"], "mechanism")

# ===================== exchange_cli.py =====================
add("cli-exchange-grammar", "Exchange CLI grammar", "p2p exchange subcommand grammar.", ["exchange_cli", "cli", "p2p"], "mechanism")
add("cli-exchange-bounded-file", "Bounded file arg", "Bounded file input.", ["exchange_cli", "security"], "mechanism")
add("cli-exchange-dispatch", "Exchange dispatcher", "Dispatch exchange subcommands.", ["exchange_cli", "cli"], "mechanism")
add("cli-exchange-advertise", "Advertise exchange", "Advertise host/port.", ["exchange_cli", "p2p"], "mechanism")
add("cli-exchange-selection-worker", "Selection worker", "Peer selection worker.", ["exchange_cli", "p2p"], "mechanism")

# ===================== executor_capabilities.py =====================
add("rt-exec-cap-digest", "Capability digest", "Digest capability packet.", ["executor_capabilities"], "mechanism")
add("rt-exec-cap-settings", "Capability settings", "Return capability settings.", ["executor_capabilities"], "mechanism")
add("rt-exec-cap-context-settings", "Context settings", "Return context settings.", ["executor_capabilities"], "mechanism")
add("rt-exec-cap-contract", "Capability contract v1", "Executor-capabilities-v1 contract.", ["executor_capabilities"], "contract")
add("rt-exec-cap-prepare", "Prepare instruction packet", "Build instruction packet.", ["executor_capabilities"], "mechanism")
add("rt-exec-cap-read", "Capability read", "Scoped read.", ["executor_capabilities"], "mechanism")
add("rt-exec-cap-clarify", "Capability clarify", "Scoped clarify.", ["executor_capabilities"], "mechanism")
add("rt-exec-cap-feedback", "Capability feedback", "Attach feedback events.", ["executor_capabilities"], "mechanism")

# ===================== executor.py =====================
add("rt-executor-unavailable-error", "ExecutorUnavailable", "Typed executor-unavailable error.", ["executor"], "schema")
add("rt-executor-adapters", "Supported executor adapters", "codex-cli, claude-cli.", ["executor"], "schema")
add("rt-executor-env-failure-markers", "Env failure markers", "Environment failure marker tuples.", ["executor"], "schema")
add("rt-executor-auth-markers", "Auth failure markers", "Auth failure marker tuples.", ["executor", "security"], "schema")
add("rt-executor-transient-markers", "Transient network markers", "Transient network marker tuples.", ["executor"], "schema")
add("rt-executor-classify-env", "Classify env failure", "Classify env failures.", ["executor"], "mechanism")
add("rt-executor-classify-auth", "Classify auth failure", "Classify auth failures.", ["executor", "security"], "mechanism")
add("rt-executor-classify-transient", "Classify transient", "Classify transient failures.", ["executor"], "mechanism")
add("rt-executor-provider-definitions", "Provider definitions", "List provider definitions.", ["executor"], "mechanism")
add("rt-executor-runtime-test-failure", "Runtime test failure detail", "Extract runtime test failure detail.", ["executor"], "mechanism")
add("rt-executor-provider-timing-error", "Provider timing error", "Report provider timing error.", ["executor"], "mechanism")
add("rt-executor-routed-providers", "Routed provider definitions", "Routed providers for capability.", ["executor"], "mechanism")
add("rt-executor-provider-settings", "Provider settings", "Provider settings resolver.", ["executor"], "mechanism")
add("rt-executor-transport-limit", "Transport byte limit", "Resolve transport limit.", ["executor"], "mechanism")
add("rt-executor-pool-availability", "Pool availability", "Pool availability.", ["executor"], "mechanism")
add("rt-executor-run-routed-codex", "Run routed codex", "Codex via routing.", ["executor", "integration"], "mechanism")
add("rt-executor-classify-unavailability", "Classify unavailability", "Classify unavailability detail.", ["executor"], "mechanism")
add("rt-executor-discovery-schema", "Discovery schema", "Executor discovery JSON schema.", ["executor"], "schema")
add("rt-executor-availability", "Executor availability", "Executor availability snapshot.", ["executor"], "mechanism")
add("rt-executor-run-heartbeats", "Run with heartbeats", "Run subprocess with heartbeats.", ["executor"], "mechanism")
add("rt-executor-run-claude", "Run claude", "Invoke claude-cli adapter.", ["executor", "integration"], "integration")
add("rt-executor-run-codex", "Run codex", "Invoke codex-cli adapter.", ["executor", "integration"], "integration")
add("rt-executor-claude-usage", "Claude usage metadata", "Parse claude usage envelope.", ["executor"], "mechanism")
add("rt-executor-codex-usage", "Codex usage metadata", "Parse codex usage events.", ["executor"], "mechanism")
add("rt-executor-codex-error", "Codex error detail", "Extract codex error.", ["executor"], "mechanism")
add("rt-executor-discover", "Executor discover", "Executor-driven discovery.", ["executor"], "mechanism")
add("rt-executor-execute", "Executor execute", "Executor-driven execute.", ["executor"], "mechanism")
add("rt-executor-explain-change", "Executor explain change", "Explain operation change.", ["executor"], "mechanism")

# ===================== external_metrics.py =====================
add("rt-ext-metrics-github", "External metrics - GitHub", "GitHub metrics collector.", ["external_metrics", "integration"], "integration")
add("rt-ext-metrics-schema-mismatch", "SourceSchemaMismatch", "Schema mismatch error.", ["external_metrics"], "schema")
add("rt-ext-metrics-lookup", "Dotted-path lookup", "Dotted-path lookup helper.", ["external_metrics"], "mechanism")
add("rt-ext-metrics-collect", "External metrics collect", "Collect external metrics.", ["external_metrics"], "mechanism")

# ===================== feature_catalog.py =====================
add("rt-fc-propagation-threshold", "Propagation threshold", "MIN_PROPAGATION_SCORE constant.", ["feature_catalog"], "schema")
add("rt-fc-descriptor", "Feature descriptor", "Canonical descriptor builder.", ["feature_catalog"], "mechanism")
add("rt-fc-atom-id", "Atomic feature id", "sha384 atom id.", ["feature_catalog"], "mechanism")
add("rt-fc-catalog", "Catalog", "In-memory feature catalog.", ["feature_catalog"], "mechanism")

# ===================== feature_equity.py =====================
add("p2p-fe-schema", "Feature equity schema v1", "urace-feature-equity-v1.", ["feature_equity"], "schema")
add("p2p-fe-non-creator-cap", "Non-creator equity cap 80%", "EQUITY_NON_CREATOR_MAX_BP constant.", ["feature_equity"], "schema")
add("p2p-fe-grant", "Grant equity", "Grant equity to creator.", ["feature_equity"], "mechanism")
add("p2p-fe-holdings", "Equity holdings", "List equity holdings.", ["feature_equity"], "mechanism")
add("p2p-fe-original-creator", "Original creator lookup", "Resolve original creator.", ["feature_equity"], "mechanism")
add("p2p-fe-sell", "Sell equity", "Sell equity bps.", ["feature_equity"], "mechanism")
add("p2p-fe-mint-split", "Mint equity split", "Proportional mint split.", ["feature_equity"], "mechanism")
add("p2p-fe-fee-split", "Distribution fee split", "Split distribution fee.", ["feature_equity"], "mechanism")

# ===================== feature_policy.py =====================
add("rt-fp-validate", "Validate feature policy", "Validate policy document.", ["feature_policy", "governance"], "mechanism")
add("rt-fp-effective", "Effective feature policy", "Effective policy at time.", ["feature_policy"], "mechanism")

# ===================== federation.py =====================
add("p2p-fed-schema", "Federation schema v1", "urace-federation-v1.", ["federation"], "schema")
add("p2p-fed-announce", "Announce federation network", "Announce network to federation.", ["federation"], "mechanism")
add("p2p-fed-networks", "List federated networks", "List federated networks.", ["federation"], "mechanism")
add("p2p-fed-query-feature", "Query feature across federation", "Query feature cross-network.", ["federation"], "mechanism")
add("p2p-fed-record-adoption", "Record federation adoption", "Record federation adoption event.", ["federation"], "mechanism")
add("p2p-fed-adoption-results", "Federation query results", "Federation query results.", ["federation"], "mechanism")
add("p2p-fed-adoption-count", "Federated adoption count", "Count cross-network adoptions.", ["federation"], "mechanism")

# ===================== freeform_routing.py =====================
add("rt-ff-normalize", "Freeform normalize", "Normalize batch input.", ["freeform_routing"], "mechanism")
add("rt-ff-validate", "Freeform validate", "Validate batch against parser.", ["freeform_routing"], "mechanism")
add("rt-ff-p2p-free", "P2P free features context", "Expose P2P free features in context.", ["freeform_routing", "p2p"], "mechanism")
add("rt-ff-p2p-paid", "P2P paid features context", "Expose P2P paid features in context.", ["freeform_routing", "p2p"], "mechanism")
add("rt-ff-prompt", "Freeform prompt", "Build prompt.", ["freeform_routing"], "mechanism")
add("rt-ff-route", "Freeform route", "Route freeform text to command.", ["freeform_routing"], "mechanism")

# ===================== implementation_sequence.py =====================
add("rt-is-local-only", "Local-only predicate", "Classify local-only task.", ["implementation_sequence"], "mechanism")
add("rt-is-plan", "Plan implementation", "Order tasks for implementation.", ["implementation_sequence"], "mechanism")
add("rt-is-execute-local", "Execute local", "Local orchestration execution.", ["implementation_sequence"], "mechanism")

# ===================== inputs.py =====================
add("rt-inputs-handle-context", "Context input handler", "Process context input.", ["inputs"], "mechanism")
add("rt-inputs-handle-goal", "Goal input handler", "Process goal input.", ["inputs"], "mechanism")
add("rt-inputs-handle-source", "Source input handler", "Process source input.", ["inputs"], "mechanism")
add("rt-inputs-handle-metric", "Metric input handler", "Process metric input.", ["inputs"], "mechanism")
add("rt-inputs-handle-vital", "Vital input handler", "Process vital input.", ["inputs"], "mechanism")
add("rt-inputs-handle-source-control", "Source-control handler", "Source-control input.", ["inputs"], "mechanism")
add("rt-inputs-handle-metric-control", "Metric-control handler", "Metric-control input.", ["inputs"], "mechanism")
add("rt-inputs-handle-vital-control", "Vital-control handler", "Vital-control input.", ["inputs"], "mechanism")
add("rt-inputs-handle-goal-control", "Goal-control handler", "Goal-control input.", ["inputs"], "mechanism")
add("rt-inputs-handle-executor-control", "Executor-control handler", "Executor-control input.", ["inputs"], "mechanism")
add("rt-inputs-handle-policy-control", "Policy-control handler", "Policy-control input.", ["inputs"], "mechanism")
add("rt-inputs-handle-budget-control", "Budget-control handler", "Budget-control input.", ["inputs"], "mechanism")
add("rt-inputs-handle-evaluation-control", "Evaluation-control handler", "Evaluation-control input.", ["inputs"], "mechanism")
add("rt-inputs-handle-intent-control", "Intent-control handler", "Intent-control input.", ["inputs"], "mechanism")
add("rt-inputs-handle-constraint-control", "Constraint-control handler", "Constraint-control input.", ["inputs"], "mechanism")
add("rt-inputs-handle-schedule-task", "Schedule-task handler", "Schedule-task input.", ["inputs"], "mechanism")
add("rt-inputs-handle-evidence", "Evidence handler", "Attach evidence.", ["inputs"], "mechanism")
add("rt-inputs-consume", "Consume inputs", "Drain input queue.", ["inputs"], "mechanism")
add("rt-inputs-queue-input", "Queue input", "Queue durable input.", ["inputs"], "mechanism")
add("rt-inputs-cleanup", "Cleanup consumed", "Delete consumed input files.", ["inputs"], "mechanism")
add("rt-inputs-apply-pending", "Apply pending", "Apply pending inputs.", ["inputs"], "mechanism")

# ===================== inspection.py =====================
add("rt-insp-document-metrics", "Document metrics", "Compute documentation metrics.", ["inspection"], "mechanism")
add("rt-insp-compare", "Direction compare", "Compare current vs reference.", ["inspection"], "mechanism")
add("rt-insp-expansion-authority", "Capability expansion authority", "Determine expansion authority.", ["inspection"], "mechanism")
add("rt-insp-objective-eligible", "Objective eligible", "Objective eligibility check.", ["inspection"], "mechanism")
add("rt-insp-goal-schedulable", "Goal schedulable", "Goal schedulability check.", ["inspection"], "mechanism")
add("rt-insp-objective-score", "Objective score", "Score objective.", ["inspection"], "mechanism")
add("rt-insp-objective-score-breakdown", "Objective score breakdown", "Breakdown of objective score.", ["inspection"], "mechanism")
add("rt-insp-goal-portfolio", "Goal portfolio", "Build goal portfolio view.", ["inspection"], "mechanism")
add("rt-insp-work-evaluations", "Work evaluations", "Build work evaluations view.", ["inspection"], "mechanism")
add("rt-insp-context-view", "Context view", "Build context view.", ["inspection"], "mechanism")
add("rt-insp-resource-accounting", "Resource accounting", "Resource accounting view.", ["inspection"], "mechanism")
add("rt-insp-executor-efficiency-vital", "Executor efficiency vital", "Executor efficiency vital.", ["inspection"], "mechanism")
add("rt-insp-evolution-vital", "Evolution vital", "Evolution vital.", ["inspection"], "mechanism")
add("rt-insp-render", "Render inspection", "Render inspection text.", ["inspection"], "mechanism")
add("rt-insp-vitals-snapshot", "Vitals snapshot", "Vitals snapshot.", ["inspection"], "mechanism")
add("rt-insp-render-vitals", "Render vitals", "Render vitals text.", ["inspection"], "mechanism")
add("rt-insp-command-catalog", "Command catalog", "Inspection-aware command catalog.", ["inspection"], "mechanism")
add("rt-insp-top-level-help", "Top-level help", "Top-level help text.", ["inspection"], "mechanism")
add("rt-insp-render-cycle", "Render cycle", "Render cycle view.", ["inspection"], "mechanism")

# ===================== integration_bridge.py =====================
add("rt-bridge-encode", "Bridge canonical encode", "Canonical JSON encode.", ["integration_bridge"], "mechanism")
add("rt-bridge-digest", "Bridge digest", "Digest canonical payload.", ["integration_bridge"], "mechanism")
add("rt-bridge-stamp", "Bridge stamp", "Monotonic time stamp.", ["integration_bridge"], "mechanism")
add("rt-bridge-pid-ticks", "PID ticks", "Return PID start ticks.", ["integration_bridge"], "mechanism")
add("rt-bridge-descendants", "Process descendants", "Enumerate descendants of PID.", ["integration_bridge"], "mechanism")
add("rt-bridge-receipt-lock", "Receipt lock", "Receipt file lock.", ["integration_bridge"], "mechanism")
add("rt-bridge-owner-lifetime", "Owner lifetime", "Return owner lifetime info.", ["integration_bridge"], "mechanism")
add("rt-bridge-operations", "Operations parser", "Operations CLI parser.", ["integration_bridge"], "mechanism")
add("rt-bridge-error", "BridgeError", "Typed bridge error.", ["integration_bridge"], "schema")
add("rt-bridge-policy", "Bridge Policy", "Bridge policy document.", ["integration_bridge", "governance"], "mechanism")
add("rt-bridge-load-policy", "Load bridge policy", "Load bridge policy from path.", ["integration_bridge"], "mechanism")
add("rt-bridge-patched-product", "Patched product", "Patched-product helper.", ["integration_bridge"], "mechanism")
add("rt-bridge-paused", "Bridge paused flag", "Detect bridge pause markers.", ["integration_bridge"], "mechanism")
add("rt-bridge-jobs", "Bridge Jobs", "Bridge job registry.", ["integration_bridge"], "mechanism")
add("rt-bridge-worker", "Bridge worker", "Run bridge worker loop.", ["integration_bridge"], "mechanism")

# ===================== intent_trace.py =====================
add("rt-intent-source-coverage", "Source coverage", "Compute source coverage.", ["intent_trace"], "mechanism")
add("rt-intent-assessment", "Intent assessment", "Build assessment of claims vs requirements.", ["intent_trace"], "mechanism")

# ===================== launcher.py =====================
add("rt-launcher-paths", "Launcher paths", "RUNTIME_ROOT/SYSTEM_ROOT/PRODUCT_ROOT/STATE_PATH/STABLE_RUNTIME.", ["launcher"], "schema")
add("rt-launcher-expected-kernel-hashes", "Expected kernel hashes", "Expected kernel hashes at startup.", ["launcher", "security"], "schema")
add("rt-launcher-configured-paths", "Configured paths", "Resolve configured paths.", ["launcher"], "mechanism")
add("rt-launcher-validate-activation", "Validate activation candidate", "Validate activation.", ["launcher", "governance"], "mechanism")
add("rt-launcher-atomic-text", "Launcher atomic text", "Atomic text write.", ["launcher"], "mechanism")
add("rt-launcher-pending-activation", "Pending activation", "Check pending activation.", ["launcher"], "mechanism")
add("rt-launcher-restore-stable", "Restore stable runtime", "Restore stable runtime image.", ["launcher", "recovery"], "mechanism")
add("rt-launcher-main", "Launcher main", "Launcher entrypoint.", ["launcher"], "mechanism")

# ===================== ledger_compaction.py =====================
add("p2p-ledger-compact-schema", "Ledger compaction schema v1", "urace-ledger-compaction-v1.", ["ledger_compaction"], "schema")
add("p2p-ledger-compact-threshold", "Compact-older-than threshold", "7-day compaction threshold.", ["ledger_compaction"], "schema")
add("p2p-ledger-compact-tail-rows", "Checkpoint tail rows", "Retain 500 tail rows.", ["ledger_compaction"], "schema")
add("p2p-ledger-compact-closed", "Compact closed contracts", "Compact closed-contract rows.", ["ledger_compaction"], "mechanism")
add("p2p-ledger-checkpoint", "Ledger checkpoint", "Build ledger checkpoint.", ["ledger_compaction"], "mechanism")
add("p2p-ledger-latest-checkpoint", "Latest checkpoint", "Return latest checkpoint.", ["ledger_compaction"], "mechanism")
add("p2p-ledger-sync-tail", "Sync tail rows", "Sync tail rows to peers.", ["ledger_compaction"], "mechanism")
add("p2p-ledger-compact-credit-history", "Compact credit history", "Compact per-peer credit history.", ["ledger_compaction"], "mechanism")
add("p2p-ledger-consensus-row-stats", "Consensus row stats", "Compute consensus row stats.", ["ledger_compaction"], "mechanism")
add("p2p-ledger-consensus-mint-per-adoption", "Consensus mint per adoption", "Consensus mint/adoption value.", ["ledger_compaction"], "mechanism")
add("p2p-ledger-p2p-optimal-supply", "P2P optimal supply", "P2P optimal supply model.", ["ledger_compaction", "economics"], "mechanism")

# ===================== ledger_crypto.py =====================
add("security-canonical", "Canonical JSON encoder", "Canonical JSON encoder.", ["ledger_crypto", "integrity"], "mechanism")
add("security-b64", "Base64 encode", "Base64 encode helper.", ["ledger_crypto"], "mechanism")
add("security-un64", "Base64 decode", "Base64 decode helper (bounded).", ["ledger_crypto"], "mechanism")
add("security-primitives", "Crypto primitives", "Ed25519/X25519 primitives.", ["ledger_crypto", "security"], "mechanism")
add("security-public-id", "Public id digest", "sha384 of canonical pub.", ["ledger_crypto"], "mechanism")
add("security-validate-public", "Validate public", "Validate public key material.", ["ledger_crypto"], "mechanism")
add("security-identity", "Identity", "Identity key wrapper.", ["ledger_crypto"], "mechanism")
add("security-verify", "Verify signature", "Verify payload signature.", ["ledger_crypto"], "mechanism")
add("security-encrypt", "Encrypt", "Hybrid encrypt payload.", ["ledger_crypto"], "mechanism")

# ===================== mcp_server.py =====================
add("rt-mcp-tool", "MCP tool declaration", "Declare an MCP tool.", ["mcp_server", "integration"], "mechanism")
add("rt-mcp-rpc-error", "MCP RpcError", "MCP RPC error type.", ["mcp_server"], "schema")
add("rt-mcp-server", "MCP Server", "MCP server class.", ["mcp_server", "integration"], "mechanism")
add("rt-mcp-serve", "MCP serve()", "MCP stdio serve.", ["mcp_server", "integration"], "mechanism")

# ===================== milestone_feedback.py =====================
add("rt-milestone-assess", "Assess milestone", "Assess milestone feedback.", ["milestone_feedback"], "mechanism")

# ===================== milestone_suggestions.py =====================
add("rt-milestone-settings", "Milestone-suggestions settings", "Module settings.", ["milestone_suggestions"], "mechanism")
add("rt-milestone-suggestions", "Milestone suggestions", "Auto milestone suggestions.", ["milestone_suggestions"], "mechanism")
add("rt-milestone-refresh", "Milestone refresh", "Refresh milestone suggestions.", ["milestone_suggestions"], "mechanism")

# ===================== multi_executor.py =====================
add("rt-multi-executor-schema", "Multi-plan schema v1", "urace-multi-plan-v1.", ["multi_executor"], "schema")
add("rt-multi-executor-settings", "Multi-executor settings", "Return settings.", ["multi_executor"], "mechanism")
add("rt-multi-executor-score-proposal", "Score proposal", "Score multi-exec proposal.", ["multi_executor"], "mechanism")
add("rt-multi-executor-select-best", "Select best", "Pick best proposal.", ["multi_executor"], "mechanism")
add("rt-multi-executor-generate-select", "Generate and select", "Generate+select loop.", ["multi_executor"], "mechanism")

# ===================== outcome_verification.py =====================
add("rt-outcome-verified-states", "VERIFIED set", "OUTCOME_VERIFIED/REAL_USER_VALUE_VERIFIED.", ["outcome_verification"], "schema")
add("rt-outcome-open-beneath", "Open beneath root", "Confined open under root.", ["outcome_verification", "security"], "mechanism")
add("rt-outcome-rate", "Rate helper", "Rate computation.", ["outcome_verification"], "mechanism")
add("rt-outcome-interval", "Confidence interval", "CI from rate/trials.", ["outcome_verification"], "mechanism")
add("rt-outcome-read", "Read measure", "Read measure file.", ["outcome_verification"], "mechanism")
add("rt-outcome-capture", "Outcome capture", "Capture outcome evidence.", ["outcome_verification"], "mechanism")
add("rt-outcome-evaluate", "Outcome evaluate", "Evaluate outcome vs expected.", ["outcome_verification"], "mechanism")
add("rt-outcome-refresh", "Outcome refresh", "Refresh outcome verifications.", ["outcome_verification"], "mechanism")
add("rt-outcome-main", "Outcome main", "Outcome CLI entrypoint.", ["outcome_verification"], "mechanism")

# ===================== patterns.py =====================
add("rt-patterns-complexity", "Pattern complexity labels", "FOUNDATIONAL/COMPOSITIONAL/INTEGRATED.", ["patterns"], "schema")
add("rt-patterns-explicit-transitive", "EXPLICIT/TRANSITIVE labels", "Pattern dep kinds.", ["patterns"], "schema")
add("rt-patterns-all-pattern-ids", "All pattern ids", "Enumerate all patterns.", ["patterns"], "mechanism")
add("rt-patterns-resolve-deps", "Resolve dependencies", "Resolve dep graph.", ["patterns"], "mechanism")
add("rt-patterns-build-manifest", "Build derived manifest", "Build derived pattern manifest.", ["patterns"], "mechanism")
add("rt-patterns-render-manifest", "Render manifest human", "Render manifest text.", ["patterns"], "mechanism")
add("rt-patterns-affinity-match", "Affinity match", "Affinity scoring helper.", ["patterns"], "mechanism")
add("rt-patterns-suggest-from-intent", "Suggest patterns from intent", "Suggest patterns from intent.", ["patterns"], "mechanism")
add("rt-patterns-patterns-from-goals", "Patterns from goals", "Suggest patterns from goals.", ["patterns"], "mechanism")
add("rt-patterns-construct-catalog", "Construct catalog", "Build construct catalog.", ["patterns"], "mechanism")
add("rt-patterns-kind-pattern", "KIND_PATTERN", "Kind label.", ["patterns"], "schema")
add("rt-patterns-kind-mechanism", "KIND_MECHANISM", "Kind label.", ["patterns"], "schema")
add("rt-patterns-kind-schema", "KIND_SCHEMA", "Kind label.", ["patterns"], "schema")
add("rt-patterns-kind-protocol", "KIND_PROTOCOL", "Kind label.", ["patterns"], "schema")
add("rt-patterns-kind-contract", "KIND_CONTRACT", "Kind label.", ["patterns"], "schema")
add("rt-patterns-suggest-constructs", "Suggest constructs from intent", "Construct suggestion by intent.", ["patterns"], "mechanism")
add("rt-patterns-build-construct-set", "Build derived construct set", "Build construct set.", ["patterns"], "mechanism")
add("rt-patterns-render-construct-set", "Render construct set", "Render construct set text.", ["patterns"], "mechanism")
add("rt-patterns-all-construct-ids", "All construct ids", "Enumerate construct ids.", ["patterns"], "mechanism")
add("rt-patterns-constructs-from-constraints", "Constructs from constraints", "Suggest from constraints.", ["patterns"], "mechanism")
add("rt-patterns-constructs-for-gaps", "Constructs for gaps", "Suggest for gaps.", ["patterns"], "mechanism")
add("rt-patterns-suggest-unadopted-constructs", "Suggest new constructs", "Suggest unadopted constructs for refs.", ["patterns"], "mechanism")
add("rt-patterns-suggest-new-patterns", "Suggest new patterns", "Suggest new patterns for saved manifests.", ["patterns"], "mechanism")

# ===================== peer_discovery.py =====================
add("p2p-pd-lan-service", "LAN service name", "_urace-exchange._tcp.local.", ["peer_discovery"], "schema")
add("p2p-pd-dht-bootstrap", "DHT bootstrap nodes", "DHT bootstrap peer list.", ["peer_discovery"], "schema")
add("p2p-pd-bencode", "Bencode encoder/decoder", "Bencode primitives.", ["peer_discovery"], "mechanism")
add("p2p-pd-announce", "mDNS announce", "Announce via mDNS.", ["peer_discovery"], "mechanism")
add("p2p-pd-stop-announce", "mDNS stop announce", "Stop mDNS announcement.", ["peer_discovery"], "mechanism")
add("p2p-pd-discover-lan", "Discover LAN peers", "DNS-SD LAN discovery.", ["peer_discovery"], "mechanism")
add("p2p-pd-dht-node-id", "DHT node id", "Compute DHT node id.", ["peer_discovery"], "mechanism")
add("p2p-pd-derive-announce-key", "Derive announce key", "Derive BEP-44 announce key.", ["peer_discovery"], "mechanism")
add("p2p-pd-bep44-sign", "BEP-44 sign", "Sign BEP-44 value.", ["peer_discovery", "security"], "mechanism")
add("p2p-pd-bep44-verify", "BEP-44 verify", "Verify BEP-44 value.", ["peer_discovery", "security"], "mechanism")
add("p2p-pd-bep44-put", "BEP-44 put", "Put BEP-44 record.", ["peer_discovery"], "mechanism")
add("p2p-pd-bep44-get", "BEP-44 get", "Get BEP-44 record.", ["peer_discovery"], "mechanism")
add("p2p-pd-dht-cert-publish", "DHT cert publish", "Publish cert via DHT.", ["peer_discovery", "security"], "mechanism")
add("p2p-pd-dht-cert-lookup", "DHT cert lookup", "Lookup cert via DHT.", ["peer_discovery", "security"], "mechanism")
add("p2p-pd-dht-key-for", "DHT key for peer", "Compute DHT key.", ["peer_discovery"], "mechanism")
add("p2p-pd-local-corpus-fp", "Local corpus fingerprint", "Local corpus FP.", ["peer_discovery"], "mechanism")
add("p2p-pd-update-publish", "P2P update publish", "Publish P2P update.", ["peer_discovery"], "mechanism")
add("p2p-pd-update-check", "P2P update check", "Check P2P update availability.", ["peer_discovery"], "mechanism")
add("p2p-pd-run-update-check", "Run update check", "Run update check loop.", ["peer_discovery"], "mechanism")
add("p2p-pd-check-central-url", "Check and auto-apply central URL", "Check central update URL.", ["peer_discovery"], "mechanism")
add("p2p-pd-auto-apply-bundle", "Auto-apply bundle from URL", "Auto-apply bundle from URL.", ["peer_discovery"], "mechanism")
add("p2p-pd-compact-peers", "Decode compact peers", "Decode compact peers blob.", ["peer_discovery"], "mechanism")
add("p2p-pd-dht-client", "DHT client", "BitTorrent-DHT client.", ["peer_discovery"], "mechanism")
add("p2p-pd-dht-announce", "DHT announce", "Announce via DHT.", ["peer_discovery"], "mechanism")
add("p2p-pd-dht-discover", "DHT discover", "DHT-based discovery.", ["peer_discovery"], "mechanism")
add("p2p-pd-discovery-session", "DiscoverySession", "Combined discovery session.", ["peer_discovery"], "mechanism")
add("p2p-pd-start", "Discovery start", "Start discovery session.", ["peer_discovery"], "mechanism")
add("p2p-pd-public-endpoint", "Discover public endpoint", "STUN-style public endpoint discovery.", ["peer_discovery"], "mechanism")
add("p2p-pd-rdv-infohash", "Rendezvous infohash", "Compute RDV infohash.", ["peer_discovery"], "mechanism")
add("p2p-pd-rdv-announce", "RDV announce", "Announce via rendezvous.", ["peer_discovery"], "mechanism")
add("p2p-pd-rdv-poll", "RDV poll", "Poll rendezvous.", ["peer_discovery"], "mechanism")
add("p2p-pd-hole-punch", "NAT hole punch", "NAT hole punching.", ["peer_discovery", "nat"], "mechanism")
add("p2p-pd-connect-peer", "Connect peer", "Peer connect primitive.", ["peer_discovery"], "mechanism")

# ===================== peer_exchange.py =====================
add("p2p-px-encoded", "Canonical encode", "Canonical JSON encode.", ["peer_exchange"], "mechanism")
add("p2p-px-digest", "Digest", "sha256 digest.", ["peer_exchange"], "mechanism")
add("p2p-px-atomic", "Atomic write", "Atomic path write.", ["peer_exchange"], "mechanism")
add("p2p-px-check-id", "Check id", "Validate peer id.", ["peer_exchange"], "mechanism")
add("p2p-px-local-corpus-fp", "Local corpus fingerprint", "Local corpus FP.", ["peer_exchange"], "mechanism")
add("p2p-px-directory", "Directory", "Peer directory path.", ["peer_exchange"], "mechanism")
add("p2p-px-exchange", "Exchange class", "P2P exchange class.", ["peer_exchange"], "mechanism")
add("p2p-px-convergence-count", "Convergence count", "Convergence count.", ["peer_exchange"], "mechanism")
add("p2p-px-validate-endpoint", "Validate endpoint", "Validate endpoint uri.", ["peer_exchange"], "mechanism")
add("p2p-px-tofu-check", "TOFU check", "Trust-on-first-use.", ["peer_exchange", "security"], "mechanism")
add("p2p-px-auto-pin", "Auto-pin cert", "Auto-pin certificate.", ["peer_exchange", "security"], "mechanism")
add("p2p-px-anonymize-cert", "Anonymize cert fields", "Anonymize certificate fields.", ["peer_exchange", "security"], "mechanism")
add("p2p-px-tls-context", "TLS context", "Build TLS context.", ["peer_exchange", "security"], "mechanism")
add("p2p-px-consensus-min", "Consensus minimum", "Consensus minimum peer count.", ["peer_exchange"], "mechanism")
add("p2p-px-request", "Peer request", "Peer RPC request.", ["peer_exchange"], "mechanism")
add("p2p-px-send", "Peer send", "Peer send message.", ["peer_exchange"], "mechanism")
add("p2p-px-relay-connect", "Relay connect", "Relay connection to peer.", ["peer_exchange"], "mechanism")
add("p2p-px-server", "Peer server", "Peer-exchange server.", ["peer_exchange"], "mechanism")
add("p2p-px-discover", "Peer discover", "Peer discover.", ["peer_exchange"], "mechanism")

# ===================== peer_improvement.py =====================
add("p2p-pi-schema", "Peer-improvement schema v1", "urace-peer-improvement-v1.", ["peer_improvement"], "schema")
add("p2p-pi-max-artifact-bytes", "Max artifact bytes", "512KB max per artifact.", ["peer_improvement"], "schema")
add("p2p-pi-safe-signals", "Safe artifact signals", "Safe-artifact signal tokens.", ["peer_improvement"], "schema")
add("p2p-pi-quarantine-dir", "Quarantine dir", "Quarantine directory path.", ["peer_improvement"], "mechanism")
add("p2p-pi-list-quarantined", "List quarantined", "List quarantined bundles.", ["peer_improvement"], "mechanism")
add("p2p-pi-load-bundle", "Load bundle", "Load quarantined bundle.", ["peer_improvement"], "mechanism")
add("p2p-pi-evaluate", "Evaluate bundle", "Evaluate quarantined bundle.", ["peer_improvement"], "mechanism")
add("p2p-pi-promote", "Promote bundle", "Promote bundle to accepted.", ["peer_improvement"], "mechanism")
add("p2p-pi-mark-qualified", "Mark qualified", "Mark bundle qualified.", ["peer_improvement"], "mechanism")
add("p2p-pi-relay-qualified", "Relay qualified", "Relay qualified bundle to peers.", ["peer_improvement"], "mechanism")
add("p2p-pi-multi-peer-amplification", "Multi-peer amplification", "Multi-peer amplification boost.", ["peer_improvement"], "mechanism")
add("p2p-pi-network-convergence", "Network convergence", "Network convergence for canonical FP.", ["peer_improvement"], "mechanism")

# ===================== peer_selection.py =====================
add("p2p-ps-offers", "Offers", "List peer offers.", ["peer_selection"], "mechanism")
add("p2p-ps-validate-catalog", "Validate catalog", "Validate peer catalog.", ["peer_selection"], "mechanism")
add("p2p-ps-cache", "Peer cache", "Peer selection cache.", ["peer_selection"], "mechanism")
add("p2p-ps-refresh", "Refresh cache", "Refresh peer cache.", ["peer_selection"], "mechanism")
add("p2p-ps-rank", "Rank peers", "Rank candidate peers.", ["peer_selection"], "mechanism")

# ===================== peer_work_market.py =====================
add("p2p-wm-schema", "Work-market schema v1", "urace-work-market-v1.", ["peer_work_market"], "schema")
add("p2p-wm-escrow-not-found", "EscrowNotFoundError", "Typed escrow error.", ["peer_work_market"], "schema")
add("p2p-wm-decompose-threshold", "Decompose threshold 0.7", "Auto-decompose above complexity 0.7.", ["peer_work_market"], "schema")
add("p2p-wm-executor-kind", "EXECUTOR_PEER_REGISTERED", "Executor peer registration kind.", ["peer_work_market"], "schema")
add("p2p-wm-sponsor-share", "Sponsor creator share 60%", "Default sponsor share.", ["peer_work_market"], "schema")
add("p2p-wm-budget-mult", "Max budget multiplier 3×", "Default budget ceiling multiplier.", ["peer_work_market"], "schema")
add("p2p-wm-escrow-fraction", "Escrow deposit fraction 10%", "Upfront escrow deposit.", ["peer_work_market"], "schema")
add("p2p-wm-late-claim-fee", "Late claim fee 10%", "Late claim fee.", ["peer_work_market"], "schema")
add("p2p-wm-max-co-requester-share", "Max co-requester share 80%", "Single-requester cap on merged budget.", ["peer_work_market"], "schema")
add("p2p-wm-daily-limit", "Daily work-request limit 5", "Per-peer per-24h cap.", ["peer_work_market"], "schema")
add("p2p-wm-verification-quorum", "Verification quorum 3", "Quorum needed for escrow release.", ["peer_work_market"], "schema")
add("p2p-wm-check-rate-limit", "Rate limit check", "Check per-peer rate limit.", ["peer_work_market", "security"], "mechanism")
add("p2p-wm-contract-timeout", "Contract timeout", "Compute contract timeout seconds.", ["peer_work_market"], "mechanism")
add("p2p-wm-work-kinds", "Work kinds set", "Permitted work kinds.", ["peer_work_market"], "schema")
add("p2p-wm-escrow-state", "Escrow state", "Resolve escrow state for request.", ["peer_work_market"], "mechanism")
add("p2p-wm-escrow-state-or-raise", "Escrow state or raise", "Fetch or raise EscrowNotFound.", ["peer_work_market"], "mechanism")
add("p2p-wm-create-work-request", "Create work request", "Create a work request.", ["peer_work_market"], "mechanism")
add("p2p-wm-submit-bid", "Submit bid", "Submit work bid.", ["peer_work_market"], "mechanism")
add("p2p-wm-accept-bid", "Accept bid", "Accept bid.", ["peer_work_market"], "mechanism")
add("p2p-wm-submit-delivery", "Submit delivery", "Submit work delivery.", ["peer_work_market"], "mechanism")
add("p2p-wm-verify-delivery", "Verify delivery", "Verify work delivery.", ["peer_work_market"], "mechanism")
add("p2p-wm-equity-split-budget", "Equity split budget", "Compute budget equity split.", ["peer_work_market"], "mechanism")
add("p2p-wm-routing-score", "Routing score", "Score peer for routing.", ["peer_work_market"], "mechanism")
add("p2p-wm-future-mint-split", "Future mint split", "Split future mint proceeds.", ["peer_work_market"], "mechanism")
add("p2p-wm-claim-ownership", "Claim ownership", "Claim ownership of delivery.", ["peer_work_market"], "mechanism")
add("p2p-wm-merge-work-requests", "Merge work requests", "Merge multiple work requests.", ["peer_work_market"], "mechanism")
add("p2p-wm-merged-co-shares", "Merged co-requester shares", "Shares table for merged requests.", ["peer_work_market"], "mechanism")
add("p2p-wm-select-arbitrators", "Select arbitrators", "Select N arbitrator peers.", ["peer_work_market", "governance"], "mechanism")
add("p2p-wm-submit-peer-review", "Submit peer review", "Submit peer review.", ["peer_work_market"], "mechanism")
add("p2p-wm-quorum-reached", "Quorum reached", "Check if review quorum reached.", ["peer_work_market"], "mechanism")
add("p2p-wm-quorum-auto-release", "Quorum auto-release", "Auto-release escrow on quorum.", ["peer_work_market"], "mechanism")
add("p2p-wm-auto-decompose", "Auto-decompose request", "Auto-decompose high-complexity request.", ["peer_work_market"], "mechanism")
add("p2p-wm-register-executor-peer", "Register executor peer", "Register executor peer.", ["peer_work_market"], "mechanism")
add("p2p-wm-executor-peer-rep", "Executor peer combined rep", "Combined reputation for executor peer.", ["peer_work_market"], "mechanism")
add("p2p-wm-audit-chain-root", "Audit chain root", "Audit-chain root hash.", ["peer_work_market", "security"], "mechanism")

# ===================== planning_feedback.py =====================
add("rt-pf-call-outcomes", "Call outcomes by objective", "Group call outcomes.", ["planning_feedback"], "mechanism")
add("rt-pf-success-rate", "Success rate", "Compute success rate.", ["planning_feedback"], "mechanism")
add("rt-pf-compute-adjustments", "Compute planning adjustments", "Score adjustments by objective.", ["planning_feedback"], "mechanism")
add("rt-pf-apply", "Apply planning feedback", "Apply adjustments to state.", ["planning_feedback"], "mechanism")

# ===================== portfolio.py =====================
add("rt-portfolio-paths", "Portfolio paths", "Portfolio root/variants paths.", ["portfolio"], "schema")
add("rt-portfolio-plan-schema", "Portfolio PLAN_SCHEMA", "Plan schema.", ["portfolio"], "schema")
add("rt-portfolio-evaluation-schema", "Portfolio EVALUATION_SCHEMA", "Evaluation schema.", ["portfolio"], "schema")
add("rt-portfolio-candidate-size-limits", "Candidate size limits", "MAX_CANDIDATE_CHANGED_LINES/NET_ADDITIONS.", ["portfolio"], "schema")
add("rt-portfolio-manipulation-patterns", "Evaluator manipulation patterns", "Patterns detecting evaluator manipulation.", ["portfolio", "security"], "schema")
add("rt-portfolio-live-controls", "Live control actions", "Allowed live control actions.", ["portfolio"], "schema")
add("rt-portfolio-cohort-policies", "Cohort policies", "auto/enabled/disabled.", ["portfolio"], "schema")
add("rt-portfolio-accepted-sources", "Accepted state sources", "lifecycle/repository.", ["portfolio"], "schema")
add("rt-portfolio-cohort-paused", "CohortPolicyPaused", "Typed cohort-pause error.", ["portfolio"], "schema")
add("rt-portfolio-stage-budget-exhausted", "StageBudgetExhausted", "Typed stage-budget error.", ["portfolio"], "schema")
add("rt-portfolio-accepted-reconciled", "AcceptedProductReconciled", "Typed accepted-reconciled signal.", ["portfolio"], "schema")
add("rt-portfolio-is-executor-unavailable", "Is executor unavailable", "Classify error as executor-unavailable.", ["portfolio"], "mechanism")
add("rt-portfolio-trusted-faults", "Trusted controller faults", "Set of trusted controller faults.", ["portfolio"], "schema")
add("rt-portfolio-controller-fault-descriptor", "Controller fault descriptor", "Trusted descriptor for controller fault.", ["portfolio"], "mechanism")
add("rt-portfolio-controller-auto-repair", "Controller auto-repair", "Auto-repair controller fault.", ["portfolio"], "mechanism")
add("rt-portfolio-now", "Portfolio now()", "Portfolio timestamp.", ["portfolio"], "mechanism")
add("rt-portfolio-integrity-key", "Integrity key", "Return portfolio integrity key.", ["portfolio", "security"], "mechanism")
add("rt-portfolio-canonical", "Canonical encode", "Canonical bytes encode.", ["portfolio"], "mechanism")
add("rt-portfolio-ledger-digest", "Ledger digest", "Portfolio ledger digest.", ["portfolio"], "mechanism")
add("rt-portfolio-verify-ledger", "Verify ledger", "Verify portfolio ledger.", ["portfolio", "integrity"], "mechanism")
add("rt-portfolio-load", "Portfolio load", "Load portfolio.", ["portfolio"], "mechanism")
add("rt-portfolio-save", "Portfolio save", "Save portfolio.", ["portfolio"], "mechanism")
add("rt-portfolio-name", "Portfolio name validate", "Validate portfolio name.", ["portfolio"], "mechanism")
add("rt-portfolio-bounded-text", "Bounded text", "Validate bounded text field.", ["portfolio"], "mechanism")
add("rt-portfolio-record-payload", "Record payload", "Build record payload.", ["portfolio"], "mechanism")
add("rt-portfolio-append-agora", "Append agora", "Append to agora collection.", ["portfolio"], "mechanism")
add("rt-portfolio-write-auth-archive", "Write authenticated archive", "Write authenticated archive.", ["portfolio", "security"], "mechanism")
add("rt-portfolio-verify-auth-archive", "Verify authenticated archive", "Verify authenticated archive.", ["portfolio", "security"], "mechanism")
add("rt-portfolio-cmd-verify", "Portfolio verify command", "CLI verify action.", ["portfolio", "cli"], "mechanism")
add("rt-portfolio-verify-agora", "Verify agora", "Verify agora collection.", ["portfolio"], "mechanism")
add("rt-portfolio-unit-interval", "Unit interval parse", "Parse unit-interval value.", ["portfolio"], "mechanism")
add("rt-portfolio-variant", "Portfolio variant", "Resolve variant.", ["portfolio"], "mechanism")
add("rt-portfolio-git", "Portfolio git", "Portfolio git helper.", ["portfolio"], "mechanism")
add("rt-portfolio-effective-cohort-policy", "Effective cohort policy", "Resolve effective cohort policy.", ["portfolio"], "mechanism")
add("rt-portfolio-effective-accepted-source", "Effective accepted-state source", "Resolve accepted state source.", ["portfolio"], "mechanism")

# ===================== preflight.py =====================
add("rt-preflight-hints", "Preflight hints", "Hints for executor preflight.", ["preflight"], "mechanism")

# ===================== primitives.py =====================
add("rt-prim-validate-identifier", "Validate identifier", "Validate identifier.", ["primitives"], "mechanism")
add("rt-prim-validate-digest", "Validate digest value", "Validate digest value.", ["primitives"], "mechanism")
add("rt-prim-validate-unit-float", "Validate unit float", "Validate 0-1 unit float.", ["primitives"], "mechanism")
add("rt-prim-product-scope-values", "Product scope values", "Scope value set.", ["primitives"], "schema")
add("rt-prim-validate-product-scope", "Validate product scope", "Validate product scope.", ["primitives"], "mechanism")
add("rt-prim-validate-status-transition", "Validate status transition", "Validate status transition.", ["primitives"], "mechanism")
add("rt-prim-validate-metric-effect", "Validate metric effect", "Validate metric effect.", ["primitives"], "mechanism")
add("rt-prim-validate-metric-snapshot", "Validate metric snapshot", "Validate metric snapshot.", ["primitives"], "mechanism")
add("rt-prim-validate-executor-attribution", "Validate executor attribution", "Validate executor attribution.", ["primitives"], "mechanism")
add("rt-prim-validate-check", "Validate validation check", "Validate validation check.", ["primitives"], "mechanism")
add("rt-prim-validate-validation-result", "Validate validation result", "Validate validation result.", ["primitives"], "mechanism")
add("rt-prim-validate-change-validation", "Validate change validation", "Validate change validation.", ["primitives"], "mechanism")
add("rt-prim-validate-error-record", "Validate error record", "Validate error record.", ["primitives"], "mechanism")
add("rt-prim-validate-failure-record", "Validate failure record", "Validate failure record.", ["primitives"], "mechanism")
add("rt-prim-validate-execution-budget", "Validate execution budget", "Validate execution budget.", ["primitives"], "mechanism")
add("rt-prim-validate-recovery-manifest", "Validate recovery manifest", "Validate recovery manifest.", ["primitives"], "mechanism")
add("rt-prim-validate-usage-record", "Validate usage record", "Validate usage record.", ["primitives"], "mechanism")
add("rt-prim-validate-wake-condition", "Validate wake condition", "Validate wake condition.", ["primitives"], "mechanism")
add("rt-prim-transaction-phases", "Transaction phases", "Transaction phase set.", ["primitives"], "schema")
add("rt-prim-validate-transaction", "Validate transaction", "Validate transaction record.", ["primitives"], "mechanism")
add("rt-prim-validate-ownership-marker", "Validate ownership marker", "Validate ownership marker.", ["primitives"], "mechanism")
add("rt-prim-validate-stale-lock-observation", "Validate stale-lock observation", "Validate stale-lock observation.", ["primitives"], "mechanism")
add("rt-prim-reasoning-step-kinds", "Reasoning step kinds", "Reasoning step kind set.", ["primitives"], "schema")
add("rt-prim-reasoning-step-outcomes", "Reasoning step outcomes", "PASS/FAIL/INCONCLUSIVE.", ["primitives"], "schema")
add("rt-prim-validate-reasoning-step", "Validate reasoning step", "Validate reasoning step.", ["primitives"], "mechanism")
add("rt-prim-amendment-kinds", "Amendment kinds", "PROVENANCE_REVISED/SUPERSEDED/CUSTOM.", ["primitives"], "schema")
add("rt-prim-validate-outcome-feedback", "Validate outcome feedback", "Validate outcome feedback.", ["primitives"], "mechanism")
add("rt-prim-validate-alternative-considered", "Validate alternative considered", "Validate alternative-considered.", ["primitives"], "mechanism")
add("rt-prim-decision-record-kinds", "Decision record kinds", "Decision kinds set.", ["primitives"], "schema")
add("rt-prim-decision-record-provenance", "Decision record provenance", "Decision provenance set.", ["primitives"], "schema")
add("rt-prim-validate-decision-record", "Validate decision record", "Validate decision record.", ["primitives"], "mechanism")
add("rt-prim-retention-modes", "Retention modes", "PROHIBITED/ARCHIVE/ROLLING_EVICTION.", ["primitives"], "schema")
add("rt-prim-validate-retention-policy", "Validate retention policy", "Validate retention policy.", ["primitives"], "mechanism")
add("rt-prim-validate-compaction-summary", "Validate compaction summary", "Validate compaction summary.", ["primitives"], "mechanism")
add("rt-prim-compaction-modes", "Compaction modes", "ARCHIVE/ROLLING_EVICTION.", ["primitives"], "schema")
add("rt-prim-validate-compaction-event", "Validate compaction event", "Validate compaction event.", ["primitives"], "mechanism")
add("rt-prim-validate-compaction-manifest", "Validate compaction manifest", "Validate compaction manifest.", ["primitives"], "mechanism")
add("rt-prim-validate-compaction-index", "Validate compaction index", "Validate compaction index.", ["primitives"], "mechanism")
add("rt-prim-validate-archive-amendment", "Validate archive amendment", "Validate archive amendment.", ["primitives"], "mechanism")
add("rt-prim-crc-phases", "CRC phases", "CRC phase set.", ["primitives"], "schema")
add("rt-prim-validate-technique-application", "Validate technique application", "Validate technique application record.", ["primitives"], "mechanism")
add("rt-prim-validate-cognitive-resume-context", "Validate cognitive resume context", "Validate CRC.", ["primitives"], "mechanism")
add("rt-prim-validate", "Primitive validate dispatcher", "Validate by schema name.", ["primitives"], "mechanism")
add("rt-prim-validate-canonical-scalar", "Validate canonical scalar", "Validate canonical scalar.", ["primitives"], "mechanism")
add("rt-prim-validate-bridge-record", "Validate bridge record", "Validate bridge record.", ["primitives"], "mechanism")
add("rt-prim-validate-orchestrator-record", "Validate orchestrator record", "Validate orchestrator record.", ["primitives"], "mechanism")
add("rt-prim-validate-scheduled-task", "Validate scheduled task", "Validate scheduled task.", ["primitives"], "mechanism")
add("rt-prim-validate-customization-record", "Validate customization record", "Validate customization record.", ["primitives"], "mechanism")
add("rt-prim-validate-lexical-formula", "Validate lexical formula", "Validate lexical formula.", ["primitives"], "mechanism")
add("rt-prim-validate-classification-result", "Validate classification result", "Validate classification result.", ["primitives"], "mechanism")
add("rt-prim-validate-classification-batch", "Validate classification batch", "Validate classification batch.", ["primitives"], "mechanism")
add("rt-prim-validate-pattern-adoption", "Validate pattern adoption", "Validate pattern-adoption record.", ["primitives"], "mechanism")
add("rt-prim-validate-pattern-exclusion", "Validate pattern exclusion", "Validate pattern-exclusion record.", ["primitives"], "mechanism")
add("rt-prim-validate-derived-system-manifest", "Validate derived system manifest", "Validate derived system manifest.", ["primitives"], "mechanism")
add("rt-prim-validate-quality-delta", "Validate quality delta", "Validate quality delta.", ["primitives"], "mechanism")
add("rt-prim-validate-reingestion", "Validate reingestion", "Validate reingestion record.", ["primitives"], "mechanism")
add("rt-prim-validate-operation-dependency", "Validate operation dependency", "Validate operation dependency.", ["primitives"], "mechanism")

# ===================== product_creation.py =====================
add("rt-pc-explicit-creation", "Explicit creation detector", "Detect explicit creation intent.", ["product_creation"], "mechanism")
add("rt-pc-interpret", "Interpret creation request", "Interpret creation request text.", ["product_creation"], "mechanism")
add("rt-pc-validate-entry", "Validate entry", "Validate creation entry.", ["product_creation"], "mechanism")
add("rt-pc-create", "Create product", "Create product.", ["product_creation", "lifecycle"], "mechanism")
add("rt-pc-apply-interpreted", "Apply interpreted creation", "Apply interpreted creation request.", ["product_creation"], "mechanism")

# ===================== product_similarity.py =====================
add("rt-ps-schema", "Product similarity schema v1", "urace-product-similarity-v1.", ["product_similarity"], "schema")
add("rt-ps-tokenize", "Tokenize text", "Tokenize text for TF-IDF.", ["product_similarity"], "mechanism")
add("rt-ps-tf", "Term frequency", "TF vector.", ["product_similarity"], "mechanism")
add("rt-ps-idf", "Inverse doc frequency", "IDF table.", ["product_similarity"], "mechanism")
add("rt-ps-tfidf-vector", "TF-IDF vector", "Build TF-IDF vector.", ["product_similarity"], "mechanism")
add("rt-ps-cosine", "Cosine similarity", "Cosine similarity.", ["product_similarity"], "mechanism")
add("rt-ps-intent-similarity", "Intent similarity", "Compute intent similarity.", ["product_similarity"], "mechanism")
add("rt-ps-wilson-lower", "Wilson lower", "Wilson lower helper.", ["product_similarity", "statistics"], "mechanism")
add("rt-ps-local-intent", "Local intent", "Extract local product intent.", ["product_similarity"], "mechanism")
add("rt-ps-peer-intents", "Peer intents", "Collect peer intents.", ["product_similarity"], "mechanism")
add("rt-ps-peer-adoptions", "Peer adoptions", "Collect peer adoptions.", ["product_similarity"], "mechanism")
add("rt-ps-recency-weight", "Recency weight", "Recency weight decay.", ["product_similarity"], "mechanism")
add("rt-ps-local-feature-ids", "Local feature ids", "Local feature id set.", ["product_similarity"], "mechanism")
add("rt-ps-known-network-size", "Known network size", "Estimate network size.", ["product_similarity"], "mechanism")
add("rt-ps-confidence", "Confidence label", "Classify confidence by peer count.", ["product_similarity"], "mechanism")
add("rt-ps-peer-trust-weights", "Peer trust weights", "Peer trust weights.", ["product_similarity"], "mechanism")
add("rt-ps-cooccurrence-bonus", "Co-occurrence bonus", "Co-occurrence bonus.", ["product_similarity"], "mechanism")
add("rt-ps-max-tfidf-sim", "Max TF-IDF sim", "Max TF-IDF similarity to local.", ["product_similarity"], "mechanism")
add("rt-ps-split-diversity-slots", "Split diversity slots", "Split diversity vs similar slots.", ["product_similarity"], "mechanism")
add("rt-ps-score-features", "Score features", "Score candidate features for adoption.", ["product_similarity"], "mechanism")

# ===================== protocol_catalog.py =====================
add("rt-protocol-describe", "Protocol describe", "Describe protocol catalog.", ["protocol_catalog"], "mechanism")

# ===================== resource_usage.py =====================
add("rt-ru-token-count", "Token count", "Resolve token count.", ["resource_usage"], "mechanism")
add("rt-ru-json-safe", "JSON-safe value", "Coerce value to JSON-safe form.", ["resource_usage"], "mechanism")
add("rt-ru-usage-totals", "Usage totals", "Aggregate usage totals.", ["resource_usage"], "mechanism")
add("rt-ru-observed-calls", "Observed calls", "List observed executor calls.", ["resource_usage"], "mechanism")
add("rt-ru-product-identity", "Product identity", "Return product identity.", ["resource_usage"], "mechanism")
add("rt-ru-archive-calls", "Archive calls", "Archive call history.", ["resource_usage"], "mechanism")
add("rt-ru-summary", "Resource summary", "Resource usage summary.", ["resource_usage"], "mechanism")
add("rt-ru-write-projection", "Write projection", "Write resource projection.", ["resource_usage"], "mechanism")

# ===================== rules.py =====================
add("rt-rules-kinds", "Rule kinds", "Rule kinds set.", ["rules", "governance"], "schema")
add("rt-rules-system-inferred", "SYSTEM_INFERRED provenance", "System-inferred label.", ["rules"], "schema")
add("rt-rules-infer-blocking", "Infer blocking threshold", "Advisory-blocking threshold 0.85.", ["rules"], "schema")
add("rt-rules-make-rule", "make_rule", "Build a rule.", ["rules"], "mechanism")
add("rt-rules-infer-constraint-kind", "Infer constraint kind", "Infer constraint kind from text.", ["rules"], "mechanism")
add("rt-rules-new-ledger", "New rule ledger", "Instantiate rule ledger.", ["rules"], "mechanism")
add("rt-rules-add-rule", "Add rule", "Add rule to ledger.", ["rules"], "mechanism")
add("rt-rules-get-rule", "Get rule", "Retrieve rule by id.", ["rules"], "mechanism")
add("rt-rules-active-rules", "Active rules", "List active rules.", ["rules"], "mechanism")
add("rt-rules-supersede-rule", "Supersede rule", "Supersede a rule.", ["rules"], "mechanism")
add("rt-rules-deactivate-rule", "Deactivate rule", "Deactivate a rule.", ["rules"], "mechanism")
add("rt-rules-snapshot-digest", "Rule ledger snapshot digest", "Deterministic ledger digest.", ["rules", "integrity"], "mechanism")
add("rt-rules-derivation-chain", "Derivation chain", "Walk rule derivation chain.", ["rules"], "mechanism")
add("rt-rules-detect-conflicts", "Detect rule conflicts", "Detect rule conflicts.", ["rules"], "mechanism")
add("rt-rules-bind-change", "Bind change", "Bind change to rules.", ["rules"], "mechanism")
add("rt-rules-rules-for-change", "Rules for change", "Rules bound to change id.", ["rules"], "mechanism")
add("rt-rules-changes-for-rule", "Changes for rule", "Changes affecting rule id.", ["rules"], "mechanism")
add("rt-rules-infer-rules", "Infer rules", "Infer rules from signals.", ["rules"], "mechanism")
add("rt-rules-apply-inferred", "Apply inferred", "Apply inferred rules.", ["rules"], "mechanism")
add("rt-rules-seed-from-config", "Seed from config", "Seed rule ledger from config.", ["rules"], "mechanism")
add("rt-rules-executor-context", "Executor rule context", "Build executor context from rules.", ["rules"], "mechanism")
add("rt-rules-format-compact", "Format rule compact", "Compact rule format.", ["rules"], "mechanism")
add("rt-rules-format-full", "Format rule full", "Full rule format.", ["rules"], "mechanism")

# ===================== runtime_cycle_cli.py =====================
add("rt-runtime-cycle-schema", "runtime-cycle-v1 schema", "Runtime-cycle CLI schema.", ["runtime_cycle_cli"], "schema")
add("rt-runtime-cycle-defaults", "Runtime cycle defaults", "enabled/auto_deploy/interval defaults.", ["runtime_cycle_cli"], "schema")
add("rt-runtime-cycle-settings", "Runtime cycle settings", "Return runtime-cycle settings.", ["runtime_cycle_cli"], "mechanism")

# ===================== runtime_features.py =====================
add("rt-rf-status-values", "Feature status values", "Status value set.", ["runtime_features"], "schema")
add("rt-rf-tag-values", "Feature tag values", "Tag value set.", ["runtime_features"], "schema")
add("rt-rf-validate", "Validate feature registry", "Validate feature registry.", ["runtime_features"], "mechanism")
add("rt-rf-all-features", "All features", "List all features.", ["runtime_features"], "mechanism")
add("rt-rf-by-status", "Features by status", "Filter by status.", ["runtime_features"], "mechanism")
add("rt-rf-by-tag", "Features by tag", "Filter by tag.", ["runtime_features"], "mechanism")
add("rt-rf-summary", "Features summary", "Summary counts.", ["runtime_features"], "mechanism")
add("rt-rf-get", "Feature get", "Return single feature.", ["runtime_features"], "mechanism")
add("rt-rf-stubs", "Feature stubs", "Return stubs.", ["runtime_features"], "mechanism")
add("rt-rf-improvement-candidates", "Improvement candidates", "List improvement candidates.", ["runtime_features"], "mechanism")

# ===================== runtime_product.py =====================
add("rt-rp-product-id", "PRODUCT_ID", "Runtime product id constant.", ["runtime_product"], "schema")
add("rt-rp-engine-identity", "Engine identity", "Compute engine identity.", ["runtime_product"], "mechanism")
add("rt-rp-registration", "Runtime registration", "Return runtime registration.", ["runtime_product"], "mechanism")
add("rt-rp-quality-gate", "Runtime quality gate", "Return runtime quality gate config.", ["runtime_product"], "mechanism")
add("rt-rp-mutation-blocker", "Mutation blocker", "Mutation blocker guard.", ["runtime_product", "security"], "mechanism")

# ===================== schema_export.py =====================
add("rt-schema-export-output", "Export output schemas", "Export runtime output schemas.", ["schema_export"], "mechanism")
add("rt-schema-export-feature-bundles", "Export feature bundles", "Export feature bundle schemas.", ["schema_export"], "mechanism")
add("rt-schema-export-all", "Export all schemas", "Export all schemas.", ["schema_export"], "mechanism")

# ===================== scope_priority.py =====================
add("rt-sp-derive", "Scope priority derive", "Derive scope priorities.", ["scope_priority"], "mechanism")
add("rt-sp-allocate", "Scope slot allocation", "Allocate slots across scopes.", ["scope_priority"], "mechanism")
add("rt-sp-infer-scope", "Infer scope", "Infer scope from changes.", ["scope_priority"], "mechanism")
add("rt-sp-ranking-adjustment", "Scope ranking adjustment", "Adjust ranking from scope.", ["scope_priority"], "mechanism")

# ===================== self_metrics.py =====================
add("rt-sm-schema", "Self-metrics schema v1", "urace-self-metrics-v1.", ["self_metrics"], "schema")
add("rt-sm-collect", "Self-metrics collect", "Collect self metrics.", ["self_metrics"], "mechanism")
add("rt-sm-test-pass-rate", "Test pass-rate collector", "Collect test pass rate.", ["self_metrics"], "mechanism")
add("rt-sm-import-health", "Import health", "Collect import health.", ["self_metrics"], "mechanism")
add("rt-sm-spec-quality", "Spec quality", "Collect spec quality.", ["self_metrics"], "mechanism")
add("rt-sm-latest", "Latest self metrics", "Return latest self metrics.", ["self_metrics"], "mechanism")
add("rt-sm-save", "Save self metrics", "Persist self metrics.", ["self_metrics"], "mechanism")
add("rt-sm-as-external-source", "As external source", "Expose self-metrics as external source.", ["self_metrics"], "mechanism")

# ===================== signed_ledger.py =====================
add("security-signed-pack", "Signed ledger pack", "Pack signed ledger block.", ["signed_ledger"], "mechanism")
add("security-signed-unpack", "Signed ledger unpack", "Unpack signed ledger block.", ["signed_ledger"], "mechanism")
add("security-signed-ledger", "Signed Ledger", "Cryptographically signed ledger.", ["signed_ledger"], "mechanism")

# ===================== spec_audit.py =====================
add("rt-sa-strip-fences", "Strip code fences", "Strip code fences from prose.", ["spec_audit"], "mechanism")
add("rt-sa-extract-spec-version", "Extract spec version", "Extract spec version.", ["spec_audit"], "mechanism")
add("rt-sa-parse-sections", "Parse sections", "Parse spec sections.", ["spec_audit"], "mechanism")
add("rt-sa-count-rfc2119", "Count RFC2119", "Count RFC2119 terms.", ["spec_audit"], "mechanism")
add("rt-sa-count-stems", "Count stems", "Count section stems.", ["spec_audit"], "mechanism")
add("rt-sa-find-semantic-gaps", "Find semantic gaps", "Find semantic gaps.", ["spec_audit"], "mechanism")
add("rt-sa-find-zero-gap", "Find zero gaps", "Find zero-gap citations.", ["spec_audit"], "mechanism")
add("rt-sa-ambiguity-score", "Ambiguity score", "Score ambiguity.", ["spec_audit"], "mechanism")
add("rt-sa-analyse-section", "Analyse section", "Analyse a section.", ["spec_audit"], "mechanism")
add("rt-sa-aggregate-stems", "Aggregate stems", "Aggregate stems.", ["spec_audit"], "mechanism")
add("rt-sa-global-summary", "Global summary", "Build global summary.", ["spec_audit"], "mechanism")
add("rt-sa-audit", "Spec audit", "Run spec audit.", ["spec_audit"], "mechanism")
add("rt-sa-build-summary", "Build spec audit summary", "Build summary record.", ["spec_audit"], "mechanism")

# ===================== token_ledger.py =====================
add("p2p-tl-schema", "Token ledger schema v1", "urace-token-ledger-v1.", ["token_ledger"], "schema")
add("p2p-tl-balance", "Token balance", "Return peer token balance.", ["token_ledger"], "mechanism")
add("p2p-tl-can-receive", "Can receive", "Peer can receive cost.", ["token_ledger"], "mechanism")
add("p2p-tl-check-can-receive", "Check can receive", "Raise if cannot receive.", ["token_ledger"], "mechanism")
add("p2p-tl-summary", "Token summary", "Token summary.", ["token_ledger"], "mechanism")

# ===================== tokenomics.py =====================
add("p2p-te-token-unit", "TOKEN_UNIT schema", "Token unit descriptor.", ["tokenomics"], "schema")
add("p2p-te-canonical-fingerprint", "Canonical fingerprint", "Fingerprint source delta.", ["tokenomics"], "mechanism")
add("p2p-te-outcome-fingerprint", "Outcome fingerprint", "Fingerprint outcome.", ["tokenomics"], "mechanism")
add("p2p-te-fingerprint-index", "Fingerprint index", "Build fingerprint index.", ["tokenomics"], "mechanism")

# ===================== trial_cli.py =====================
add("cli-trial-score-arguments", "Trial score arguments", "Score CLI arguments.", ["trial_cli", "cli"], "mechanism")
add("cli-trial-work-arguments", "Trial work arguments", "Work CLI arguments.", ["trial_cli", "cli"], "mechanism")
add("cli-trial-build-parser", "Trial CLI parser", "Build the trial CLI parser.", ["trial_cli", "cli"], "mechanism")

# ===================== trial.py =====================
add("rt-trial-main", "Trial main", "Trial entrypoint.", ["trial"], "mechanism")
add("rt-trial-workflow-root", "Workflow root", "Resolve workflow root.", ["trial"], "mechanism")
add("rt-trial-run-workflow", "Run workflow", "Run trial workflow.", ["trial"], "mechanism")

# ===================== tui.py =====================
add("rt-tui-dashboard-data", "TUI DashboardData", "Dataclass for dashboard.", ["tui"], "schema")
add("rt-tui-collect", "TUI collect", "Collect dashboard data.", ["tui"], "mechanism")
add("rt-tui-format-score", "Format score", "Format score.", ["tui"], "mechanism")
add("rt-tui-route-input", "Route TUI input", "Route raw input text to command.", ["tui"], "mechanism")
add("rt-tui-run-loop", "TUI run loop", "TUI run loop.", ["tui"], "mechanism")
add("rt-tui-dispatch", "TUI dispatch", "TUI dispatch helper.", ["tui"], "mechanism")
add("rt-tui-launch", "TUI launch", "Launch TUI.", ["tui"], "mechanism")
add("rt-tui-no-tty-fallback", "TUI no-tty fallback", "Fallback when no TTY.", ["tui"], "mechanism")

# ===================== uncertainty_followup.py =====================
add("rt-uf-plan", "Uncertainty follow-up plan", "Plan follow-up for uncertain claims.", ["uncertainty_followup"], "mechanism")

# ===================== updater.py =====================
add("rt-upd-max-spec-bytes", "Max spec bytes", "1MB spec cap.", ["updater"], "schema")
add("rt-upd-max-migration-bytes", "Max migration diff bytes", "131KB migration diff cap.", ["updater"], "schema")
add("rt-upd-validate-runtime-bundle", "Validate runtime bundle", "Validate runtime bundle.", ["updater", "security"], "mechanism")
add("rt-upd-validate-spec", "Validate specification", "Validate specification bytes.", ["updater", "security"], "mechanism")
add("rt-upd-read-source", "Read source", "Read source bundle.", ["updater"], "mechanism")
add("rt-upd-source-revision", "Source revision", "Resolve source revision.", ["updater"], "mechanism")
add("rt-upd-bootstrap-baseline", "Bootstrap runtime baseline", "Bootstrap runtime baseline record.", ["updater"], "mechanism")
add("rt-upd-local-customization-inventory", "Local customization inventory", "Inventory local customizations.", ["updater"], "mechanism")
add("rt-upd-download", "Updater download", "Download update bundle.", ["updater"], "mechanism")
add("rt-upd-resolve-candidate", "Resolve candidate", "Resolve candidate reference.", ["updater"], "mechanism")
add("rt-upd-explain", "Explain update", "Explain update candidate.", ["updater"], "mechanism")
add("rt-upd-sanitize-diff", "Sanitize diff for embedding", "Sanitize diff before embedding.", ["updater", "security"], "mechanism")
add("rt-upd-detect-migration-scope", "Detect migration scope", "Detect migration scope.", ["updater"], "mechanism")
add("rt-upd-migration-payload", "Migration payload", "Build migration payload.", ["updater"], "mechanism")
add("rt-upd-conflict-resolution-schema", "Conflict resolution schema", "Conflict resolution JSON schema.", ["updater"], "schema")
add("rt-upd-injection-signal-prefixes", "Injection signal prefixes", "Injection-signal prefix list.", ["updater", "security"], "schema")

# ===================== user_controls.py =====================
add("rt-uc-efforts", "Effort levels", "low/medium/high.", ["user_controls"], "schema")
add("rt-uc-profiles", "Resource profiles", "Resource profiles.", ["user_controls"], "schema")
add("rt-uc-auto-goals", "Auto-goals setting", "User control for auto-goals.", ["user_controls"], "mechanism")
add("rt-uc-effort-mode", "Effort mode resolver", "Resolve effort mode.", ["user_controls"], "mechanism")
add("rt-uc-resource-profile", "Resource profile resolver", "Resolve resource profile.", ["user_controls"], "mechanism")
add("rt-uc-native-settings", "Native settings", "Resolve native settings.", ["user_controls"], "mechanism")
add("rt-uc-discovery-interval", "Discovery interval", "Resolve discovery interval.", ["user_controls"], "mechanism")

# ===================== validation.py =====================
add("rt-val-states", "Validation states", "VALIDATED/REJECTED/PENDING_CAPABILITY.", ["validation"], "schema")
add("rt-val-candidate-file-errors", "Candidate file errors", "Validate candidate files.", ["validation"], "mechanism")
add("rt-val-validate-operation", "Validate operation", "Validate operation record.", ["validation"], "mechanism")
add("rt-val-pending-validation-record", "Pending validation record", "Pending-validation record.", ["validation"], "mechanism")

# ===================== value_discovery.py =====================
add("rt-vd-version", "Value evidence version", "value-evidence-v1 schema.", ["value_discovery"], "schema")
add("rt-vd-defaults", "Value discovery defaults", "Module defaults.", ["value_discovery"], "schema")
add("rt-vd-classes", "Value classes", "Value class set.", ["value_discovery"], "schema")
add("rt-vd-indicators", "Value indicators", "Indicator set.", ["value_discovery"], "schema")
add("rt-vd-settings", "Value settings", "Return settings.", ["value_discovery"], "mechanism")
add("rt-vd-project", "Project identity", "Return project.", ["value_discovery"], "mechanism")
add("rt-vd-identity", "Value identity", "Return identity.", ["value_discovery"], "mechanism")
add("rt-vd-store-path", "Store path", "Return store path.", ["value_discovery"], "mechanism")
add("rt-vd-empty", "Empty store", "Return empty store.", ["value_discovery"], "mechanism")
add("rt-vd-load", "Load value data", "Load value store.", ["value_discovery"], "mechanism")
add("rt-vd-save", "Save value data", "Save value store.", ["value_discovery"], "mechanism")
add("rt-vd-proposed", "Proposed indicators", "List proposed indicators.", ["value_discovery"], "mechanism")
add("rt-vd-sync", "Sync value data", "Sync value data with state.", ["value_discovery"], "mechanism")
add("rt-vd-hypothesis", "Hypothesis", "Return hypothesis.", ["value_discovery"], "mechanism")
add("rt-vd-observe", "Observe", "Record observation.", ["value_discovery"], "mechanism")
add("rt-vd-outcome-freshness", "Outcome freshness", "Classify outcome freshness.", ["value_discovery"], "mechanism")
add("rt-vd-contradicted", "Contradicted detector", "Detect contradicted hypothesis.", ["value_discovery"], "mechanism")
add("rt-vd-percent-change", "Percent change", "Compute percent change.", ["value_discovery"], "mechanism")
add("rt-vd-validate", "Validate hypothesis", "Validate hypothesis evidence.", ["value_discovery"], "mechanism")
add("rt-vd-link-outcomes", "Link outcomes", "Link outcomes to hypotheses.", ["value_discovery"], "mechanism")
add("rt-vd-research", "Research hypothesis", "Research a hypothesis.", ["value_discovery"], "mechanism")
add("rt-vd-experiment", "Experiment", "Record experiment.", ["value_discovery"], "mechanism")
add("rt-vd-advisory-ranking", "Advisory ranking", "Advisory ranking.", ["value_discovery"], "mechanism")
add("rt-vd-status", "Value status", "Value discovery status.", ["value_discovery"], "mechanism")
add("rt-vd-define-indicator", "Define indicator", "Define new indicator.", ["value_discovery"], "mechanism")
add("rt-vd-attach-evidence", "Attach evidence", "Attach evidence to hypothesis.", ["value_discovery"], "mechanism")
add("rt-vd-refresh", "Refresh value discovery", "Refresh value discovery.", ["value_discovery"], "mechanism")
add("rt-vd-dispatch", "Value discovery dispatch", "CLI dispatch.", ["value_discovery"], "mechanism")
add("rt-vd-ranking-scores", "Ranking scores", "Ranking score view.", ["value_discovery"], "mechanism")
add("rt-vd-execution-quality-views", "Execution quality views", "Execution quality views.", ["value_discovery"], "mechanism")

# ===================== value_trajectory.py =====================
add("rt-vt-record-checkpoint", "Record checkpoint", "Record value checkpoint.", ["value_trajectory"], "mechanism")
add("rt-vt-compute-acceleration", "Compute acceleration", "Compute acceleration metric.", ["value_trajectory"], "mechanism")
add("rt-vt-self-correction-needed", "Self-correction needed", "Detect self-correction needed.", ["value_trajectory"], "mechanism")

# ===================== version.py =====================
add("rt-version-runtime", "RUNTIME_VERSION", "Runtime version string.", ["version"], "schema")
add("rt-version-format", "FORMAT_VERSION", "State schema version.", ["version"], "schema")
add("rt-version-min-format", "MIN_FORMAT_VERSION", "Minimum state format.", ["version"], "schema")
add("rt-version-bridge", "BRIDGE_VERSION", "Bridge protocol version.", ["version"], "schema")
add("rt-version-min-bridge-client", "MIN_BRIDGE_CLIENT_VERSION", "Min bridge client version.", ["version"], "schema")

# ===================== workflow_state.py =====================
add("rt-ws-conflict", "WorkflowConflict", "Typed workflow conflict error.", ["workflow_state"], "schema")
add("rt-ws-product-copy", "Workflow product copy", "Copy product for workflow.", ["workflow_state"], "mechanism")
add("rt-ws-boundary", "Workflow boundary", "Workflow boundary snapshot.", ["workflow_state"], "mechanism")

# ===================== work_policy.py =====================
add("rt-wp-choose", "Work policy choose", "Choose provider/engine/model/effort.", ["work_policy"], "mechanism")
add("rt-wp-execution-mode", "Execution mode resolver", "Resolve execution mode.", ["work_policy"], "mechanism")
add("rt-wp-outcomes", "Outcomes aggregator", "Aggregate outcomes.", ["work_policy"], "mechanism")

# ================================================================
# ================ TRIAL / HARNESS MODULES =======================
# ================================================================

# accounting.py
add("trial-acct-metadata-safe", "Trial metadata-safe", "Produce metadata-safe values.", ["trial", "accounting"], "mechanism")
add("trial-acct-claude-usage", "Trial claude usage", "Parse claude usage.", ["trial", "accounting"], "mechanism")
add("trial-acct-codex-usage", "Trial codex usage", "Parse codex usage.", ["trial", "accounting"], "mechanism")
add("trial-acct-partial-lower-bound", "Trial partial lower bound", "Lower bound for partial usage.", ["trial", "accounting"], "mechanism")
add("trial-acct-projected", "Trial projected", "Projected usage rollup.", ["trial", "accounting"], "mechanism")
add("trial-acct-reconcile", "Trial reconcile", "Reconcile usage rows.", ["trial", "accounting"], "mechanism")
add("trial-acct-pending-status", "Pending status", "Pending-status report.", ["trial", "accounting"], "mechanism")
add("trial-acct-settle", "Settle usage", "Settle usage record.", ["trial", "accounting"], "mechanism")

# allocation.py
add("trial-alloc-decide", "Allocation decide", "Decide allocation from snapshot.", ["trial", "allocation"], "mechanism")
add("trial-alloc-build", "Allocation build", "Build allocation plan.", ["trial", "allocation"], "mechanism")

# assessment_evidence.py
add("trial-ae-wilson", "Wilson lower (assessment)", "Wilson lower helper.", ["trial", "assessment"], "mechanism")
add("trial-ae-numeric", "Numeric helper", "Numeric coercion.", ["trial", "assessment"], "mechanism")
add("trial-ae-recorded-time", "Recorded time", "Resolve recorded time.", ["trial", "assessment"], "mechanism")
add("trial-ae-assess", "Assess evidence", "Assess evidence rows.", ["trial", "assessment"], "mechanism")

# assessment_packet.py
add("trial-ap-packet", "Assessment packet", "Build assessment packet.", ["trial", "assessment"], "mechanism")

# availability.py
add("trial-av-probe-codex", "Probe codex availability", "Probe codex CLI.", ["trial", "availability"], "mechanism")
add("trial-av-should-wake", "Should wake", "Should wake? predicate.", ["trial", "availability"], "mechanism")
add("trial-av-main", "Availability main", "Availability entrypoint.", ["trial", "availability"], "mechanism")

# claude_preflight.py
add("trial-cpf-step", "Claude preflight step", "Preflight step.", ["trial", "preflight"], "mechanism")
add("trial-cpf-reusable-receipt", "Reusable receipt", "Reusable claude preflight receipt.", ["trial", "preflight"], "mechanism")
add("trial-cpf-probe", "Claude probe", "Probe claude availability.", ["trial", "preflight"], "mechanism")

# common.py (trial)
add("trial-common-operations-root", "Operations root", "Resolve operations root path.", ["trial", "common"], "mechanism")
add("trial-common-atomic", "Trial atomic write", "Atomic file write.", ["trial", "common"], "mechanism")
add("trial-common-append", "Trial append event", "Append event to ledger.", ["trial", "common"], "mechanism")
add("trial-common-guard", "Trial guard", "Return guard file.", ["trial", "common"], "mechanism")
add("trial-common-events", "Trial events", "Iterate events.", ["trial", "common"], "mechanism")
add("trial-common-governor", "Governor accessor", "Resolve governor instance.", ["trial", "common"], "mechanism")
add("trial-common-reserve", "Reserve capacity", "Reserve provider capacity.", ["trial", "common"], "mechanism")
add("trial-common-budget-status", "Budget status", "Provider budget status.", ["trial", "common"], "mechanism")
add("trial-common-evidence-path", "Evidence path", "Return evidence path.", ["trial", "common"], "mechanism")

# controls.py
add("trial-controls-effective", "Effective controls", "Resolve effective controls.", ["trial", "controls"], "mechanism")
add("trial-controls-task-eligibility", "Task eligibility", "Task eligibility decision.", ["trial", "controls"], "mechanism")

# core_resources.py
add("trial-cr-resource-state", "Core resource state", "Load core resource state.", ["trial", "resources"], "mechanism")
add("trial-cr-events", "Core resource events", "Core resource events.", ["trial", "resources"], "mechanism")

# coverage_assessment.py
add("trial-cov-load", "Load default", "Load JSON with default.", ["trial", "coverage"], "mechanism")
add("trial-cov-sha", "File sha", "Hash file content.", ["trial", "coverage"], "mechanism")
add("trial-cov-product-context", "Product context", "Build product context.", ["trial", "coverage"], "mechanism")
add("trial-cov-features", "Coverage features", "Enumerate coverage features.", ["trial", "coverage"], "mechanism")
add("trial-cov-paired-metrics", "Paired metrics", "Paired metrics evaluation.", ["trial", "coverage"], "mechanism")
add("trial-cov-comparative-readiness", "Comparative readiness", "Comparative readiness check.", ["trial", "coverage"], "mechanism")

# cross_audit.py
add("trial-ca-run", "Cross-audit run", "Run cross audit.", ["trial", "audit"], "mechanism")

# decision_assessor.py
add("trial-da-validate-advice", "Validate advice", "Validate advice payload.", ["trial", "decision"], "mechanism")
add("trial-da-run", "Decision-assessor run", "Run assessor.", ["trial", "decision"], "mechanism")

# downstream_study.py
add("trial-ds-digest", "Downstream digest", "Downstream digest.", ["trial", "study"], "mechanism")
add("trial-ds-prepare-reference", "Prepare reference", "Prepare reference workspace.", ["trial", "study"], "mechanism")
add("trial-ds-plan", "Downstream plan", "Build downstream plan.", ["trial", "study"], "mechanism")
add("trial-ds-status", "Downstream status", "Return downstream status.", ["trial", "study"], "mechanism")
add("trial-ds-run-one", "Run one downstream", "Run one downstream lane.", ["trial", "study"], "mechanism")
add("trial-ds-step", "Downstream step", "Downstream step iteration.", ["trial", "study"], "mechanism")

# efficiency_score.py
add("trial-es-read", "Efficiency read", "Read score file.", ["trial", "efficiency"], "mechanism")
add("trial-es-product-id", "Product id normalizer", "Normalize product id.", ["trial", "efficiency"], "mechanism")
add("trial-es-validate", "Validate score config", "Validate score config.", ["trial", "efficiency"], "mechanism")
add("trial-es-configure", "Configure efficiency", "Configure efficiency score.", ["trial", "efficiency"], "mechanism")
add("trial-es-inspect", "Inspect efficiency", "Inspect efficiency config.", ["trial", "efficiency"], "mechanism")
add("trial-es-record", "Record efficiency metric", "Record metric.", ["trial", "efficiency"], "mechanism")
add("trial-es-score", "Compute score", "Compute efficiency score.", ["trial", "efficiency"], "mechanism")
add("trial-es-methodology", "Methodology", "Build methodology.", ["trial", "efficiency"], "mechanism")
add("trial-es-read-custom", "Read custom", "Read custom efficiency.", ["trial", "efficiency"], "mechanism")

# executable_benchmark.py
add("trial-eb-sha", "Benchmark sha", "Hash helper.", ["trial", "benchmark"], "mechanism")
add("trial-eb-cli-smoke-score", "CLI smoke score", "Compute CLI smoke score.", ["trial", "benchmark"], "mechanism")
add("trial-eb-load", "Load benchmark JSON", "Load benchmark JSON.", ["trial", "benchmark"], "mechanism")
add("trial-eb-context", "Benchmark context", "Build benchmark context.", ["trial", "benchmark"], "mechanism")
add("trial-eb-read-versions", "Read versions", "Read benchmark versions.", ["trial", "benchmark"], "mechanism")
add("trial-eb-profiles", "Benchmark profiles", "Enumerate benchmark profiles.", ["trial", "benchmark"], "mechanism")
add("trial-eb-choose-version", "Choose version", "Choose benchmark version.", ["trial", "benchmark"], "mechanism")
add("trial-eb-collect", "Collect job", "Collect benchmark job.", ["trial", "benchmark"], "mechanism")
add("trial-eb-child", "Spawn benchmark child", "Spawn benchmark child provider.", ["trial", "benchmark"], "mechanism")
add("trial-eb-run", "Run benchmark", "Run executable benchmark.", ["trial", "benchmark"], "mechanism")

# executable_cases.py
add("trial-ec-oracle-ready", "Oracle ready", "Oracle readiness check.", ["trial", "cases"], "mechanism")
add("trial-ec-corpus", "Case corpus", "Build corpus.", ["trial", "cases"], "mechanism")
add("trial-ec-public-cases", "Public cases", "Build public cases.", ["trial", "cases"], "mechanism")
add("trial-ec-manifest", "Cases manifest", "Build cases manifest.", ["trial", "cases"], "mechanism")

# executable_sandbox.py
add("trial-sandbox-error", "SandboxInfrastructureError", "Typed sandbox error.", ["trial", "sandbox"], "schema")
add("trial-sandbox-validate-source", "Validate source", "Validate sandbox source.", ["trial", "sandbox"], "mechanism")
add("trial-sandbox-check-image", "Check image", "Verify sandbox image.", ["trial", "sandbox"], "mechanism")
add("trial-sandbox-execute", "Sandbox execute", "Execute sandbox cases.", ["trial", "sandbox"], "mechanism")

# executable_scores.py
add("trial-escores-equal", "Score equal helper", "Equal comparator.", ["trial", "scores"], "mechanism")
add("trial-escores-grade", "Grade evaluation", "Grade sandbox output.", ["trial", "scores"], "mechanism")
add("trial-escores-aggregate", "Aggregate entries", "Aggregate score entries.", ["trial", "scores"], "mechanism")
add("trial-escores-delta", "Score delta", "Delta between score sets.", ["trial", "scores"], "mechanism")
add("trial-escores-summarize", "Summarize record", "Summarize score record.", ["trial", "scores"], "mechanism")
add("trial-escores-view", "View scores", "View score history.", ["trial", "scores"], "mechanism")
add("trial-escores-render", "Render scores", "Render score result.", ["trial", "scores"], "mechanism")

# executable_workflow.py
add("trial-ew-run", "Workflow run", "Run executable workflow.", ["trial", "workflow"], "mechanism")

# execution_contract.py
add("trial-xc-selected-source", "Selected source", "Return selected source.", ["trial", "execution_contract"], "mechanism")
add("trial-xc-fingerprint", "Execution fingerprint", "Execution fingerprint.", ["trial", "execution_contract"], "mechanism")
add("trial-xc-analysis-fingerprint", "Analysis fingerprint", "Analysis fingerprint.", ["trial", "execution_contract"], "mechanism")
add("trial-xc-repository-fingerprint", "Repository fingerprint", "Repository fingerprint.", ["trial", "execution_contract"], "mechanism")
add("trial-xc-measurement-fingerprint", "Measurement fingerprint", "Measurement fingerprint.", ["trial", "execution_contract"], "mechanism")

# native_agents.py
add("trial-na-codex", "Native codex", "Codex native agent.", ["trial", "native_agents"], "mechanism")
add("trial-na-claude", "Native claude", "Claude native agent.", ["trial", "native_agents"], "mechanism")
add("trial-na-run", "Native run", "Native run dispatcher.", ["trial", "native_agents"], "mechanism")

# output_quality.py
add("trial-oq-cases", "Quality cases", "Build cases for family/phase.", ["trial", "quality"], "mechanism")
add("trial-oq-contract", "Quality contract", "Return quality contract.", ["trial", "quality"], "mechanism")
add("trial-oq-diagnostics", "Quality diagnostics", "Diagnostics for workspace.", ["trial", "quality"], "mechanism")
add("trial-oq-grade", "Grade output", "Grade output quality.", ["trial", "quality"], "mechanism")
add("trial-oq-summary", "Quality summary", "Quality summary.", ["trial", "quality"], "mechanism")

# peer_runtime.py
add("trial-pr-exchange", "Peer runtime exchange", "Resolve exchange handle.", ["trial", "peer_runtime"], "mechanism")
add("trial-pr-validate-receipt", "Validate receipt", "Validate peer receipt.", ["trial", "peer_runtime"], "mechanism")
add("trial-pr-enqueue", "Enqueue bundle", "Enqueue peer bundle.", ["trial", "peer_runtime"], "mechanism")
add("trial-pr-process-one", "Process one bundle", "Process one bundle.", ["trial", "peer_runtime"], "mechanism")

# period_feedback.py
add("trial-period-percentiles", "Percentiles", "Compute percentiles.", ["trial", "period"], "mechanism")
add("trial-period-compare", "Period compare", "Period comparison.", ["trial", "period"], "mechanism")

# product_controls.py
add("trial-pc-set-improvement-enabled", "Set improvement enabled", "Per-product improvement toggle.", ["trial", "product_controls"], "mechanism")
add("trial-pc-get-improvement-enabled", "Get improvement enabled", "Read improvement toggle.", ["trial", "product_controls"], "mechanism")

# product_resources.py
add("trial-pres-efficiency", "Product efficiency", "Compute product efficiency.", ["trial", "resources"], "mechanism")
add("trial-pres-report", "Product resources report", "Per-product resource report.", ["trial", "resources"], "mechanism")
add("trial-pres-overall", "Overall report", "Overall resources report.", ["trial", "resources"], "mechanism")

# project_tools.py
add("trial-pt-confined", "Confined path", "Confine path under root.", ["trial", "project_tools", "security"], "mechanism")
add("trial-pt-inventory", "Project inventory", "Inventory project files.", ["trial", "project_tools"], "mechanism")
add("trial-pt-container", "Project container", "Container runner.", ["trial", "project_tools"], "mechanism")
add("trial-pt-call", "Project tool call", "Call named tool.", ["trial", "project_tools"], "mechanism")
add("trial-pt-serve", "Project tool server", "Serve tool interface.", ["trial", "project_tools"], "mechanism")

# project_work.py
add("trial-pw-load", "Load JSON helper", "Load JSON helper.", ["trial", "project_work"], "mechanism")
add("trial-pw-engine-hash", "Engine hash", "Engine hash.", ["trial", "project_work"], "mechanism")
add("trial-pw-project-identity", "Project identity", "Project identity.", ["trial", "project_work"], "mechanism")
add("trial-pw-state-root", "Project state root", "Project state root.", ["trial", "project_work"], "mechanism")
add("trial-pw-initialize", "Initialize project", "Initialize project.", ["trial", "project_work"], "mechanism")
add("trial-pw-declaration", "Project declaration", "Build project declaration.", ["trial", "project_work"], "mechanism")
add("trial-pw-evaluate", "Project evaluate", "Evaluate project.", ["trial", "project_work"], "mechanism")
add("trial-pw-status", "Project status", "Project status.", ["trial", "project_work"], "mechanism")
add("trial-pw-prompt-json", "Prompt JSON", "Prompt JSON encoder.", ["trial", "project_work"], "mechanism")
add("trial-pw-task-packet", "Task packet", "Build task packet.", ["trial", "project_work"], "mechanism")
add("trial-pw-active-budget", "ActiveBudget class", "ActiveBudget class.", ["trial", "project_work"], "mechanism")
add("trial-pw-run", "Project run", "Run project.", ["trial", "project_work"], "mechanism")
add("trial-pw-owner-clarifications", "Owner clarifications", "Owner clarifications.", ["trial", "project_work"], "mechanism")
add("trial-pw-clarify", "Project clarify", "Clarify project requirement.", ["trial", "project_work"], "mechanism")

# providers.py
add("trial-prov-transport", "Transport class", "Transport abstraction.", ["trial", "providers"], "mechanism")
add("trial-prov-claude", "Providers claude", "Claude provider adapter.", ["trial", "providers"], "integration")
add("trial-prov-failed-turn-message", "Failed turn message", "Failed-turn message.", ["trial", "providers"], "mechanism")
add("trial-prov-codex", "Providers codex", "Codex provider adapter.", ["trial", "providers"], "integration")
add("trial-prov-quota-view", "Quota view", "Build quota view.", ["trial", "providers"], "mechanism")
add("trial-prov-run", "Providers run", "Run via provider.", ["trial", "providers"], "mechanism")

# qualification_protocol.py
add("trial-qp-digest", "Qualification digest", "Digest payload.", ["trial", "qualification"], "mechanism")
add("trial-qp-native-clients", "Native clients", "Native client list.", ["trial", "qualification"], "mechanism")
add("trial-qp-protocol", "Qualification protocol", "Return protocol.", ["trial", "qualification"], "mechanism")
add("trial-qp-cells", "Qualification cells", "Build qualification cells.", ["trial", "qualification"], "mechanism")
add("trial-qp-reconcile", "Qualification reconcile", "Reconcile row.", ["trial", "qualification"], "mechanism")
add("trial-qp-compatible", "Qualification compatible", "Check compatibility.", ["trial", "qualification"], "mechanism")
add("trial-qp-progress", "Qualification progress", "Progress report.", ["trial", "qualification"], "mechanism")

# quality_audit.py
add("trial-qa-load", "Quality audit load", "Load path helper.", ["trial", "quality"], "mechanism")
add("trial-qa-audit", "Quality audit", "Run quality audit.", ["trial", "quality"], "mechanism")

# quality_policy.py
add("trial-qpol-semantic-markers", "Semantic markers", "Extract semantic markers.", ["trial", "quality"], "mechanism")
add("trial-qpol-preserve-contract", "Preserve decision contract", "Preserve decision contract.", ["trial", "quality"], "mechanism")
add("trial-qpol-editable-spans", "Editable spans", "Return editable spans.", ["trial", "quality"], "mechanism")
add("trial-qpol-select-section", "Select section", "Select section to edit.", ["trial", "quality"], "mechanism")
add("trial-qpol-blind-review-prompt", "Blind review prompt", "Build blind review prompt.", ["trial", "quality"], "mechanism")
add("trial-qpol-normalize-review", "Normalize review", "Normalize review response.", ["trial", "quality"], "mechanism")
add("trial-qpol-quality-pass", "Quality pass", "Quality pass predicate.", ["trial", "quality"], "mechanism")
add("trial-qpol-supporting-contracts", "Supporting contracts", "Supporting contracts text.", ["trial", "quality"], "mechanism")

# quality_restore.py
add("trial-qr-withdrawn-versions", "Withdrawn versions", "Withdrawn versions.", ["trial", "quality"], "mechanism")
add("trial-qr-inverse-source", "Inverse source", "Compute inverse source.", ["trial", "quality"], "mechanism")
add("trial-qr-verify", "Verify restore", "Verify restoration.", ["trial", "quality"], "mechanism")
add("trial-qr-record-withdrawals", "Record withdrawals", "Record withdrawals.", ["trial", "quality"], "mechanism")
add("trial-qr-run", "Quality restore run", "Run restore pass.", ["trial", "quality"], "mechanism")

# quota_pressure.py
add("trial-qpress-claude-utilization", "Claude utilization", "Claude utilization fraction.", ["trial", "quota"], "mechanism")
add("trial-qpress-is-high-pressure", "Is high pressure", "High pressure predicate.", ["trial", "quota"], "mechanism")

# refinement_targets.py
add("trial-rt-report", "Refinement targets report", "Report refinement targets.", ["trial", "refinement"], "mechanism")

# repository_study.py
add("trial-rs-configure", "Repository study configure", "Configure repository study.", ["trial", "study"], "mechanism")
add("trial-rs-plan", "Repository study plan", "Plan repository study.", ["trial", "study"], "mechanism")
add("trial-rs-status", "Repository study status", "Status of repository study.", ["trial", "study"], "mechanism")
add("trial-rs-run-one", "Repository study run one", "Run one repository study.", ["trial", "study"], "mechanism")

# repository_tasks.py
add("trial-rtt-brief", "Task brief", "Build task brief.", ["trial", "tasks"], "mechanism")
add("trial-rtt-answer", "Task answer", "Answer task request.", ["trial", "tasks"], "mechanism")
add("trial-rtt-cases", "Task cases", "Build task cases.", ["trial", "tasks"], "mechanism")
add("trial-rtt-public-script", "Public script", "Build public script.", ["trial", "tasks"], "mechanism")
add("trial-rtt-contract", "Task contract", "Return task contract.", ["trial", "tasks"], "mechanism")

# resource_governor.py
add("trial-rg-external-roots", "External roots", "External roots.", ["trial", "governor"], "mechanism")
add("trial-rg-registered-roots", "Registered roots", "Registered roots.", ["trial", "governor"], "mechanism")
add("trial-rg-records", "Governor records", "Governor records.", ["trial", "governor"], "mechanism")
add("trial-rg-debit", "Debit", "Debit reservation.", ["trial", "governor"], "mechanism")
add("trial-rg-capacity-failure", "Capacity failure", "Capacity-failure message.", ["trial", "governor"], "mechanism")
add("trial-rg-availability-snapshot", "Availability snapshot", "Availability snapshot.", ["trial", "governor"], "mechanism")
add("trial-rg-capacity-retry", "Capacity retry", "Compute capacity retry.", ["trial", "governor"], "mechanism")
add("trial-rg-capacity-recovery", "Capacity recovery", "Capacity recovery timing.", ["trial", "governor"], "mechanism")
add("trial-rg-transport-recovery", "Transport recovery", "Transport recovery timing.", ["trial", "governor"], "mechanism")
add("trial-rg-evaluate", "Governor evaluate", "Evaluate reservation.", ["trial", "governor"], "mechanism")
add("trial-rg-status", "Governor status", "Governor status.", ["trial", "governor"], "mechanism")
add("trial-rg-local-configuration", "Local configuration", "Load local config.", ["trial", "governor"], "mechanism")
add("trial-rg-guard", "Governor guard", "Return governor guard.", ["trial", "governor"], "mechanism")
add("trial-rg-reserve", "Governor reserve", "Reserve provider capacity.", ["trial", "governor"], "mechanism")

# resource_report.py
add("trial-rr-main", "Resource report main", "Resource report entrypoint.", ["trial", "report"], "mechanism")

# review.py
add("trial-review-recommend", "Review recommend", "Build review recommendation.", ["trial", "review"], "mechanism")
add("trial-review-main", "Review main", "Review entrypoint.", ["trial", "review"], "mechanism")

# routing.py
add("trial-routing-choices", "Routing choices", "Routing choices.", ["trial", "routing"], "mechanism")
add("trial-routing-update-backoff", "Update backoff", "Update provider backoff.", ["trial", "routing"], "mechanism")

# runtime_cycle.py
add("trial-rc-settings", "Runtime-cycle settings", "Settings accessor.", ["trial", "runtime_cycle"], "mechanism")
add("trial-rc-load", "Load JSON helper", "Load JSON helper.", ["trial", "runtime_cycle"], "mechanism")
add("trial-rc-emit", "Emit event", "Emit runtime cycle event.", ["trial", "runtime_cycle"], "mechanism")
add("trial-rc-status", "Runtime cycle status", "Runtime cycle status.", ["trial", "runtime_cycle"], "mechanism")
add("trial-rc-completed", "Completed stage", "Mark stage completed.", ["trial", "runtime_cycle"], "mechanism")
add("trial-rc-proposal", "Runtime cycle proposal", "Record proposal.", ["trial", "runtime_cycle"], "mechanism")
add("trial-rc-source-stat", "Source stat", "Source stat helper.", ["trial", "runtime_cycle"], "mechanism")
add("trial-rc-step", "Runtime cycle step", "Runtime cycle step.", ["trial", "runtime_cycle"], "mechanism")
add("trial-rc-apply-pending", "Apply pending", "Apply pending cycle updates.", ["trial", "runtime_cycle"], "mechanism")

# runtime_dashboard.py
add("trial-rd-data", "Dashboard data", "Dashboard data.", ["trial", "dashboard"], "mechanism")
add("trial-rd-render", "Dashboard render", "Render dashboard.", ["trial", "dashboard"], "mechanism")

# runtime_evaluation.py
add("trial-re-digest", "Evaluation digest", "Evaluation digest.", ["trial", "evaluation"], "mechanism")
add("trial-re-sha", "File sha", "File sha.", ["trial", "evaluation"], "mechanism")
add("trial-re-now", "ISO now", "ISO now.", ["trial", "evaluation"], "mechanism")
add("trial-re-inventory", "Evaluation inventory", "Package inventory.", ["trial", "evaluation"], "mechanism")
add("trial-re-engine", "Evaluation engine", "Engine descriptor.", ["trial", "evaluation"], "mechanism")
add("trial-re-snapshot", "Evaluation snapshot", "Snapshot package.", ["trial", "evaluation"], "mechanism")
add("trial-re-validate-sources", "Validate sources", "Validate source lists.", ["trial", "evaluation"], "mechanism")
add("trial-re-cases", "Evaluation cases", "Evaluation cases.", ["trial", "evaluation"], "mechanism")
add("trial-re-contract", "Evaluation contract", "Return contract.", ["trial", "evaluation"], "mechanism")
add("trial-re-container-run", "Container run", "Container runner.", ["trial", "evaluation"], "mechanism")
add("trial-re-matches", "Matches expected", "Match observed vs expected.", ["trial", "evaluation"], "mechanism")
add("trial-re-measure", "Measure", "Measure package.", ["trial", "evaluation"], "mechanism")
add("trial-re-load-receipt", "Load receipt", "Load evaluation receipt.", ["trial", "evaluation"], "mechanism")

# runtime_proposal.py
add("trial-rp-run", "Runtime proposal run", "Run runtime proposal.", ["trial", "proposal"], "mechanism")

# runtime_qualification.py
add("trial-rqual-test-manifest", "Test manifest", "Return test manifest.", ["trial", "qualification"], "mechanism")
add("trial-rqual-trusted-hashes", "Trusted hashes", "Trusted hashes.", ["trial", "qualification"], "mechanism")
add("trial-rqual-purpose", "Purpose", "Return purpose.", ["trial", "qualification"], "mechanism")
add("trial-rqual-installation-ready", "Installation ready", "Installation ready check.", ["trial", "qualification"], "mechanism")
add("trial-rqual-prepare-regression", "Prepare regression", "Prepare regression.", ["trial", "qualification"], "mechanism")
add("trial-rqual-regression", "Regression", "Regression run.", ["trial", "qualification"], "mechanism")
add("trial-rqual-qualify", "Qualify", "Qualify candidate.", ["trial", "qualification"], "mechanism")
add("trial-rqual-load-qualification", "Load qualification", "Load qualification record.", ["trial", "qualification"], "mechanism")

# runtime_quality_gate.py
add("trial-rqg-finite", "Finite check", "Finite check.", ["trial", "quality_gate"], "mechanism")
add("trial-rqg-qualify", "Qualify score", "Qualify baseline vs candidate.", ["trial", "quality_gate"], "mechanism")
add("trial-rqg-read-latest-evaluation", "Read latest evaluation", "Read latest evaluation.", ["trial", "quality_gate"], "mechanism")
add("trial-rqg-read-latest-score", "Read latest score", "Read latest score.", ["trial", "quality_gate"], "mechanism")
add("trial-rqg-gate-config", "Gate config", "Return gate config.", ["trial", "quality_gate"], "mechanism")
add("trial-rqg-gate-decision", "Gate decision", "Compute gate decision.", ["trial", "quality_gate"], "mechanism")
add("trial-rqg-status", "Quality gate status", "Status report.", ["trial", "quality_gate"], "mechanism")

# runtime_regression_guard.py
add("trial-rrg-last-accepted-score", "Last accepted score", "Last accepted score.", ["trial", "regression"], "mechanism")
add("trial-rrg-check", "Regression check", "Regression check.", ["trial", "regression"], "mechanism")
add("trial-rrg-run-guard", "Run regression guard", "Run regression guard.", ["trial", "regression"], "mechanism")
add("trial-rrg-report", "Regression report", "Regression report.", ["trial", "regression"], "mechanism")

# runtime_snapshot.py
add("trial-rs-create", "Create snapshot", "Create runtime snapshot.", ["trial", "snapshot"], "mechanism")
add("trial-rs-list", "List snapshots", "List snapshots.", ["trial", "snapshot"], "mechanism")
add("trial-rs-load", "Load snapshot", "Load snapshot.", ["trial", "snapshot"], "mechanism")
add("trial-rs-stream-summaries", "Stream summaries", "Stream snapshot summaries.", ["trial", "snapshot"], "mechanism")
add("trial-rs-planning-context", "Planning context", "Planning context from snapshots.", ["trial", "snapshot"], "mechanism")

# runtime_trial.py
add("trial-rt-deployment-error", "RuntimeDeploymentError", "Typed deployment error.", ["trial", "runtime_trial"], "schema")
add("trial-rt-validate-diff", "Validate diff", "Validate change spec diff.", ["trial", "runtime_trial"], "mechanism")
add("trial-rt-quick-verify", "Quick verify", "Quick verify runtime.", ["trial", "runtime_trial"], "mechanism")
add("trial-rt-recover", "Recover", "Recover trial deployment.", ["trial", "runtime_trial"], "mechanism")
add("trial-rt-run", "Trial run", "Run trial.", ["trial", "runtime_trial"], "mechanism")
add("trial-rt-deployment-log", "Deployment log", "Deployment event log.", ["trial", "runtime_trial"], "mechanism")
add("trial-rt-redeployment-report", "Redeployment report", "Redeployment report.", ["trial", "runtime_trial"], "mechanism")
add("trial-rt-deploy", "Trial deploy", "Deploy trial change.", ["trial", "runtime_trial"], "mechanism")

# snapshot_metadata.py
add("trial-sm-verify-engine", "Verify engine", "Verify engine signature.", ["trial", "snapshot_metadata"], "mechanism")
add("trial-sm-engine-snapshot", "Engine snapshot", "Engine snapshot.", ["trial", "snapshot_metadata"], "mechanism")
add("trial-sm-trial-resources", "Trial resources", "Trial-resource bundle.", ["trial", "snapshot_metadata"], "mechanism")
add("trial-sm-create", "Metadata create", "Create metadata.", ["trial", "snapshot_metadata"], "mechanism")
add("trial-sm-validate", "Metadata validate", "Validate metadata.", ["trial", "snapshot_metadata"], "mechanism")
add("trial-sm-finalize", "Metadata finalize", "Finalize metadata.", ["trial", "snapshot_metadata"], "mechanism")
add("trial-sm-executable-measurement-view", "Executable measurement view", "Executable measurement view.", ["trial", "snapshot_metadata"], "mechanism")
add("trial-sm-rollups", "Rollups", "Rollup metrics.", ["trial", "snapshot_metadata"], "mechanism")
add("trial-sm-inspect-snapshot", "Inspect snapshot", "Inspect snapshot folder.", ["trial", "snapshot_metadata"], "mechanism")

# source_integrity.py
add("trial-si-projected", "Projected source", "Projected source bytes.", ["trial", "source_integrity"], "mechanism")
add("trial-si-descriptor", "Source descriptor", "Build source descriptor.", ["trial", "source_integrity"], "mechanism")
add("trial-si-matches", "Source matches", "Check source matches.", ["trial", "source_integrity"], "mechanism")

# spec_trial.py
add("trial-st-digest", "Spec trial digest", "Digest text.", ["trial", "spec"], "mechanism")
add("trial-st-utc", "UTC now", "ISO UTC now.", ["trial", "spec"], "mechanism")
add("trial-st-version", "Version resolver", "Resolve version id.", ["trial", "spec"], "mechanism")
add("trial-st-read-version", "Read version", "Read spec version.", ["trial", "spec"], "mechanism")
add("trial-st-sections", "Spec sections", "Parse spec sections.", ["trial", "spec"], "mechanism")
add("trial-st-normative", "Normative extraction", "Extract normative content.", ["trial", "spec"], "mechanism")
add("trial-st-fenced-blocks", "Fenced blocks", "Extract fenced blocks.", ["trial", "spec"], "mechanism")
add("trial-st-validate-patch", "Validate patch", "Validate spec patch.", ["trial", "spec"], "mechanism")
add("trial-st-review-pass", "Review pass", "Review pass predicate.", ["trial", "spec"], "mechanism")
add("trial-st-publish", "Publish spec", "Publish spec version.", ["trial", "spec"], "mechanism")
add("trial-st-decode-native-payload", "Decode native payload", "Decode native payload.", ["trial", "spec"], "mechanism")
add("trial-st-native", "Spec native", "Native spec runner.", ["trial", "spec"], "mechanism")
add("trial-st-eligible", "Spec trial eligible", "Eligibility gate.", ["trial", "spec"], "mechanism")
add("trial-st-compare", "Spec compare", "Compare spec versions.", ["trial", "spec"], "mechanism")
add("trial-st-resource-metrics", "Resource metrics", "Resource metrics.", ["trial", "spec"], "mechanism")
add("trial-st-recover-publication", "Recover publication", "Recover publication.", ["trial", "spec"], "mechanism")
add("trial-st-status", "Spec trial status", "Spec trial status.", ["trial", "spec"], "mechanism")
add("trial-st-main", "Spec trial main", "Spec trial entrypoint.", ["trial", "spec"], "mechanism")

# stream_usage.py
add("trial-su-structured-diagnostics", "Structured diagnostics", "Structured diagnostics parser.", ["trial", "stream"], "mechanism")
add("trial-su-stream-usage", "StreamUsage class", "StreamUsage class.", ["trial", "stream"], "mechanism")
add("trial-su-claude-transport-policy", "Claude transport policy", "Claude transport policy.", ["trial", "stream"], "mechanism")
add("trial-su-next-claude-controls", "Next claude controls", "Next claude controls.", ["trial", "stream"], "mechanism")

# study_analysis.py
add("trial-sa-category", "Category", "Row category.", ["trial", "study"], "mechanism")
add("trial-sa-percentile", "Percentile", "Percentile helper.", ["trial", "study"], "mechanism")
add("trial-sa-resources", "Resources", "Resource analysis.", ["trial", "study"], "mechanism")
add("trial-sa-compare", "Study compare", "Compare study rows.", ["trial", "study"], "mechanism")
add("trial-sa-assessment", "Study assessment", "Build study assessment.", ["trial", "study"], "mechanism")
add("trial-sa-compact-packet", "Compact packet", "Compact study packet.", ["trial", "study"], "mechanism")
add("trial-sa-context-choice", "Context choice", "Choose context profile.", ["trial", "study"], "mechanism")
add("trial-sa-quarantine-contracts", "Quarantine contracts", "Quarantine contracts.", ["trial", "study"], "mechanism")
add("trial-sa-phase-telemetry", "Phase telemetry", "Phase telemetry.", ["trial", "study"], "mechanism")

# trial_supervisor.py
add("trial-sup-active", "Supervisor active", "Supervisor active flag.", ["trial", "supervisor"], "mechanism")
add("trial-sup-external-owner", "External owner", "External owner info.", ["trial", "supervisor"], "mechanism")
add("trial-sup-legacy-step", "Legacy step", "Legacy supervisor step.", ["trial", "supervisor"], "mechanism")
add("trial-sup-productive-runtime", "Productive runtime step", "Productive runtime step.", ["trial", "supervisor"], "mechanism")
add("trial-sup-productive-spec", "Productive spec step", "Productive spec step.", ["trial", "supervisor"], "mechanism")
add("trial-sup-runtime-local-work", "Runtime local work", "Runtime-local work step.", ["trial", "supervisor"], "mechanism")
add("trial-sup-review-step", "Review step", "Supervisor review step.", ["trial", "supervisor"], "mechanism")
add("trial-sup-capacity-admission", "CapacityAdmission", "Capacity admission class.", ["trial", "supervisor"], "mechanism")
add("trial-sup-next-review", "Next review", "Next review scheduler.", ["trial", "supervisor"], "mechanism")
add("trial-sup-main", "Supervisor main", "Supervisor entrypoint.", ["trial", "supervisor"], "mechanism")

# value_benchmark.py
add("trial-vb-section", "Section extractor", "Extract section.", ["trial", "value_benchmark"], "mechanism")
add("trial-vb-fixture", "Fixture builder", "Build before/after fixture.", ["trial", "value_benchmark"], "mechanism")
add("trial-vb-score", "Score response", "Score benchmark response.", ["trial", "value_benchmark"], "mechanism")
add("trial-vb-run", "Value benchmark run", "Run value benchmark.", ["trial", "value_benchmark"], "mechanism")

# workflow_study.py
add("trial-wfs-load", "Load helper", "Load helper.", ["trial", "workflow_study"], "mechanism")
add("trial-wfs-validate-settings", "Validate settings", "Validate workflow study settings.", ["trial", "workflow_study"], "mechanism")
add("trial-wfs-configure", "Configure workflow study", "Configure workflow study.", ["trial", "workflow_study"], "mechanism")
add("trial-wfs-plan", "Workflow study plan", "Plan workflow study.", ["trial", "workflow_study"], "mechanism")
add("trial-wfs-run-one", "Workflow study run one", "Run one workflow study.", ["trial", "workflow_study"], "mechanism")
add("trial-wfs-status", "Workflow study status", "Workflow study status.", ["trial", "workflow_study"], "mechanism")

# workflow_tasks.py
add("trial-wft-expected", "Expected outputs", "Expected outputs for family.", ["trial", "workflow_tasks"], "mechanism")
add("trial-wft-cases", "Workflow task cases", "Workflow task cases.", ["trial", "workflow_tasks"], "mechanism")
add("trial-wft-manifest", "Workflow task manifest", "Workflow task manifest.", ["trial", "workflow_tasks"], "mechanism")

# ================================================================
# ================ CROSS-CUTTING CLI SURFACES ====================
# ================================================================
# runtime CLI subcommands exposed through command_surface + exchange_cli
add("cli-add-context", "CLI add-context", "Add context input.", ["cli", "inputs"], "mechanism")
add("cli-add-goal", "CLI add-goal", "Add goal input.", ["cli", "inputs"], "mechanism")
add("cli-add-source", "CLI add-source", "Add source input.", ["cli", "inputs"], "mechanism")
add("cli-add-metric", "CLI add-metric", "Add metric input.", ["cli", "inputs"], "mechanism")
add("cli-add-vital", "CLI add-vital", "Add vital input.", ["cli", "inputs"], "mechanism")
add("cli-declare", "CLI declare", "Declare controls.", ["cli", "inputs"], "mechanism")
add("cli-autonomous", "CLI autonomous", "Toggle autonomous mode.", ["cli", "governance"], "mechanism")
add("cli-self-evolution", "CLI self-evolution", "Self-evolution controls.", ["cli", "governance"], "mechanism")
add("cli-policy", "CLI policy", "Policy controls.", ["cli", "governance"], "mechanism")
add("cli-budget", "CLI budget", "Budget controls.", ["cli", "governance"], "mechanism")
add("cli-executor-capacity", "CLI executor-capacity", "Executor capacity control.", ["cli", "executor"], "mechanism")
add("cli-repair-controller", "CLI repair-controller", "Repair controller control.", ["cli", "recovery"], "mechanism")
add("cli-classify", "CLI classify", "Classify command.", ["cli"], "mechanism")
add("cli-compress", "CLI compress", "Compress context ledger.", ["cli", "compaction"], "mechanism")
add("cli-decompress", "CLI decompress", "Decompress context ledger.", ["cli", "compaction"], "mechanism")
add("cli-evaluation", "CLI evaluation", "Evaluation knob control.", ["cli"], "mechanism")
add("cli-check", "CLI check", "Run checks.", ["cli"], "mechanism")
add("cli-vitals", "CLI vitals", "Show vitals.", ["cli", "inspection"], "mechanism")
add("cli-quality", "CLI quality", "Quality command.", ["cli", "quality"], "mechanism")
add("cli-compliance", "CLI compliance", "Compliance command.", ["cli", "governance"], "mechanism")
add("cli-milestone", "CLI milestone", "Milestone command.", ["cli"], "mechanism")
add("cli-integrity-signal", "CLI integrity-signal", "Integrity-signal command.", ["cli", "integrity"], "mechanism")

# Exchange / P2P CLI capabilities
add("cli-exchange-publish-feature", "Exchange publish-feature", "Publish feature to peers.", ["exchange_cli", "p2p"], "mechanism")
add("cli-exchange-borrow-feature", "Exchange borrow-feature", "Borrow feature from peer.", ["exchange_cli", "p2p"], "mechanism")
add("cli-exchange-list-features", "Exchange list-features", "List catalog features.", ["exchange_cli", "p2p"], "mechanism")
add("cli-exchange-peer-list", "Exchange peer-list", "List known peers.", ["exchange_cli", "p2p"], "mechanism")
add("cli-exchange-balance", "Exchange balance", "Show credit balance.", ["exchange_cli", "p2p"], "mechanism")
add("cli-exchange-history", "Exchange history", "Credit ledger history.", ["exchange_cli", "p2p"], "mechanism")
add("cli-exchange-escrow-status", "Exchange escrow-status", "Escrow status.", ["exchange_cli", "p2p"], "mechanism")
add("cli-exchange-work-request", "Exchange work-request", "Create work request.", ["exchange_cli", "p2p"], "mechanism")
add("cli-exchange-work-bid", "Exchange work-bid", "Submit work bid.", ["exchange_cli", "p2p"], "mechanism")
add("cli-exchange-work-accept", "Exchange work-accept", "Accept work bid.", ["exchange_cli", "p2p"], "mechanism")
add("cli-exchange-work-deliver", "Exchange work-deliver", "Submit delivery.", ["exchange_cli", "p2p"], "mechanism")
add("cli-exchange-work-verify", "Exchange work-verify", "Verify delivery.", ["exchange_cli", "p2p"], "mechanism")
add("cli-exchange-federation-announce", "Exchange federation-announce", "Announce federation.", ["exchange_cli", "p2p", "federation"], "mechanism")
add("cli-exchange-federation-query", "Exchange federation-query", "Federation query.", ["exchange_cli", "p2p", "federation"], "mechanism")
add("cli-exchange-equity-list", "Exchange equity-list", "List equity for sale.", ["exchange_cli", "p2p"], "mechanism")
add("cli-exchange-equity-sell", "Exchange equity-sell", "Sell equity.", ["exchange_cli", "p2p"], "mechanism")
add("cli-exchange-equity-buy", "Exchange equity-buy", "Buy equity.", ["exchange_cli", "p2p"], "mechanism")

# ================================================================
# ================ TEST SUITES (acceptance) ======================
# ================================================================
# Each test file is one acceptance surface
_test_files = [
    ("test_a2a_bridge", "A2A bridge integration tests"),
    ("test_alignment_fixes", "Alignment regression tests"),
    ("test_analytics", "Analytics capability tests"),
    ("test_authenticated_journal", "Authenticated journal tests"),
    ("test_auto_goals", "Auto-goals tests"),
    ("test_auto_trade", "Auto equity-trade tests"),
    ("test_bootstrap_ready", "Bootstrap readiness tests"),
    ("test_command_surface", "Command surface tests"),
    ("test_compaction_integrity", "Compaction integrity tests"),
    ("test_context_relations", "Context relations tests"),
    ("test_core_audit", "Core audit tests"),
    ("test_data_cli_persistence", "Data CLI persistence tests"),
    ("test_data_source_truthfulness", "Data-source truthfulness tests"),
    ("test_data_transports", "Data transport tests"),
    ("test_decision_feedback", "Decision feedback tests"),
    ("test_executor_capabilities", "Executor capabilities tests"),
    ("test_external_metrics", "External metrics tests"),
    ("test_feature_catalog", "Feature catalog tests"),
    ("test_feature_equity", "Feature equity tests"),
    ("test_feature_policy", "Feature policy tests"),
    ("test_freeform_routing", "Freeform routing tests"),
    ("test_full_scope_audit", "Full scope audit tests"),
    ("test_implementation_sequence", "Implementation sequence tests"),
    ("test_json_flags", "JSON flags tests"),
    ("test_lock_crash_recovery", "Lock crash recovery tests"),
    ("test_mcp_bridge", "MCP bridge tests"),
    ("test_metric_file_resource_bound", "Metric-file bound tests"),
    ("test_milestone_feedback", "Milestone feedback tests"),
    ("test_multi_executor", "Multi-executor tests"),
    ("test_native_usage_errors", "Native usage error tests"),
    ("test_nat_traversal", "NAT traversal tests"),
    ("test_nested_repository", "Nested repository tests"),
    ("test_nullable_budgets", "Nullable budget tests"),
    ("test_operator_bootstrap", "Operator bootstrap tests"),
    ("test_owner_value_readiness", "Owner value-readiness tests"),
    ("test_p2p_integrity", "P2P integrity tests"),
    ("test_p2p_update_discovery", "P2P update discovery tests"),
    ("test_peer_discovery", "Peer discovery tests"),
    ("test_peer_exchange", "Peer exchange tests"),
    ("test_peer_improvement", "Peer improvement tests"),
    ("test_peer_selection", "Peer selection tests"),
    ("test_planning_feedback", "Planning feedback tests"),
    ("test_portfolio", "Portfolio tests"),
    ("test_product_creation", "Product creation tests"),
    ("test_product_similarity", "Product similarity tests"),
    ("test_quota_wording", "Quota wording tests"),
    ("test_rollback", "Rollback tests"),
    ("test_runtime_context_injection", "Runtime context injection tests"),
    ("test_runtime_cycle_cli", "Runtime cycle CLI tests"),
    ("test_runtime_features", "Runtime features registry tests"),
    ("test_runtime_product", "Runtime product tests"),
    ("test_signed_ledger", "Signed ledger tests"),
    ("test_singularity", "Singularity feature tests"),
    ("test_tokenomics", "Tokenomics tests"),
    ("test_tokenomics_settlement", "Tokenomics settlement tests"),
    ("test_trial_bridge", "Trial bridge tests"),
    ("test_trial_workflow", "Trial workflow tests"),
    ("test_tui", "TUI tests"),
    ("test_update_derive_roundtrip", "Update derive-roundtrip tests"),
    ("test_urace", "URACE top-level tests"),
    ("test_urace_r109", "URACE §109 regression tests"),
    ("test_urace_usage_truth_contract", "URACE usage-truth-contract tests"),
    ("test_user_benefit_core", "User-benefit core tests"),
    ("test_user_controls", "User controls tests"),
    ("test_value_discovery", "Value discovery tests"),
    ("test_value_production", "Value production tests"),
    ("test_value_workflow_integration", "Value workflow integration tests"),
    ("test_version_preflight", "Version preflight tests"),
    ("test_watch_command", "Watch command tests"),
    ("test_work_market", "P2P work market tests"),
    ("test_zero_config", "Zero-config tests"),
]
for _mod, _desc in _test_files:
    add(f"test-{_mod.replace('_', '-')}", _desc, _desc, ["tests", _mod], "contract")

# Trial-side test files
_trial_tests = [
    ("test_allocation", "Trial allocation tests"),
    ("test_assessment_evidence", "Assessment evidence tests"),
    ("test_assessment_fixes", "Assessment fixes tests"),
    ("test_availability", "Availability tests"),
    ("test_capability_tool_pipeline", "Capability tool pipeline tests"),
    ("test_cohort_study_validation", "Cohort study validation tests"),
    ("test_controls", "Trial controls tests"),
    ("test_coverage_assessment", "Coverage assessment tests"),
    ("test_decision_assessor", "Decision assessor tests"),
    ("test_efficiency_score", "Efficiency score tests"),
    ("test_executable_evaluation", "Executable evaluation tests"),
    ("test_governor", "Governor tests"),
    ("test_lifecycle", "Lifecycle tests"),
    ("test_peer_runtime", "Peer runtime tests"),
    ("test_product_controls_trial", "Product controls (trial) tests"),
    ("test_product_resources", "Product resources tests"),
    ("test_qualification_protocol", "Qualification protocol tests"),
    ("test_quality_policy", "Quality policy tests"),
    ("test_quota_pressure_trial", "Quota pressure (trial) tests"),
    ("test_refinement_targets", "Refinement targets tests"),
    ("test_relocation", "Relocation tests"),
    ("test_resource_report", "Resource report tests"),
    ("test_runtime_cycle_trial", "Runtime cycle (trial) tests"),
    ("test_runtime_quality_gate_trial", "Runtime quality-gate (trial) tests"),
    ("test_runtime_regression_guard", "Runtime regression guard tests"),
    ("test_runtime_snapshot", "Runtime snapshot tests"),
    ("test_runtime_trial", "Runtime trial tests"),
    ("test_snapshot_metadata", "Snapshot metadata tests"),
    ("test_source_integrity", "Source integrity tests"),
    ("test_spec_trial", "Spec trial tests"),
    ("test_user_benefit", "User benefit tests"),
    ("test_value_quality", "Value quality tests"),
    ("test_value_workflows", "Value workflows tests"),
]
for _mod, _desc in _trial_tests:
    add(f"trial-test-{_mod.replace('_', '-')}", _desc, _desc, ["tests", "trial", _mod], "contract")

# ================================================================
# ================ WRITE LEDGER ==================================
# ================================================================

def main() -> None:
    output = Path(__file__).resolve().parent.parent / "exchange" / "initial_ledger" / "initial_ledger.jsonl"
    output.parent.mkdir(parents=True, exist_ok=True)

    # Load existing ledger to find already-present feature IDs (append-only semantics).
    # Existing entries are never removed or rewritten — only new IDs are appended.
    existing_ids: set[str] = set()
    existing_lines: list[str] = []
    if output.exists():
        for raw in output.read_text(encoding="utf-8").splitlines():
            raw = raw.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError:
                continue
            # Skip the header line(s)
            if obj.get("schema") == "urace-initial-ledger-v1":
                existing_lines.append(raw)
                continue
            fid = obj.get("feature_id")
            if fid:
                existing_ids.add(fid)
                existing_lines.append(raw)

    # Determine which features are new (not already in the ledger)
    new_features = [f for f in features if f["feature_id"] not in existing_ids]
    all_features_count = len(existing_ids) + len(new_features)

    # Rewrite: updated header + all existing lines (preserving order) + new entries
    header = json.dumps({"schema": "urace-initial-ledger-v1", "feature_count": all_features_count}, sort_keys=False)
    # Replace or prepend header line
    body_lines = [l for l in existing_lines if json.loads(l).get("schema") != "urace-initial-ledger-v1"]
    new_lines = [json.dumps(f, sort_keys=False) for f in new_features]
    output.write_text("\n".join([header] + body_lines + new_lines) + "\n", encoding="utf-8")

    # Summary
    from collections import Counter
    all_features = [f for f in features]  # features defined in this script
    kinds = Counter(f["kind_label"] for f in all_features)
    action = f"appended {len(new_features)} new" if existing_ids else f"wrote {len(new_features)}"
    print(f"{action} features to {output} ({all_features_count} total)")
    print("Breakdown by kind_label (this build):")
    for kind, count in sorted(kinds.items(), key=lambda kv: -kv[1]):
        print(f"  {kind}: {count}")


if __name__ == "__main__":
    main()
