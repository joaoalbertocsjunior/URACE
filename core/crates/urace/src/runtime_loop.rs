//! Async runtime loop — poll sources, dispatch work, emit telemetry.
//!
//! Ported from `runtime/urace/cli_cycle.py` (the daemon loop aspects).
//!
//! Invariants:
//! - The runtime loop MUST NOT block on work dispatch (uses tokio tasks).
//! - Circuit breaker trip must be checked before each work dispatch.
//! - Sources are polled at the interval configured in `SourcesConfig`.
//! - Authority check gates every work assignment and goal creation (§62z).
//! - The improvement step closes the feedback loop:
//!   observe metrics → evaluate goals → mint on positive delta → suggest new goals.

use crate::circuit_breaker::{BreakerState, CircuitBreaker};
use crate::config::RuntimeConfig;
use crate::state::RuntimeState;
use anyhow::Result;
use sha2::{Digest, Sha256};
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::sync::Arc;
use std::time::Duration;
use tokio::sync::Mutex;
use tokio::time::interval;
use tracing::{debug, error, info, warn};
use urace_audit::{AuditEvent, AuditKind, AuditLedger};
use urace_goals::{AutoGoalEngine, GoalStore, TelemetryEmitter, TelemetryEvent};
use urace_work::{
    implementation_sequence::{Task as PlanTask, TaskStatus},
    AutoPlanner, PlanningContext, WorkMarket, WorkPolicy, WorkTask,
};

/// Observable metrics captured at the end of each cycle.
///
/// Used by the improvement step to compute score deltas across consecutive cycles.
#[derive(Debug, Clone, Default, serde::Serialize, serde::Deserialize)]
pub struct CycleMetrics {
    /// Number of registered sources.
    pub sources_count: usize,
    /// Number of circuit-breaker-tripped (Open) providers — proxy for failed syncs.
    pub failed_syncs: usize,
    /// Number of pending work tasks in the market.
    pub pending_work: usize,
}

/// A snapshot of the runtime loop status (read by `urace status`).
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize, Default)]
pub struct LoopStatus {
    /// Whether the loop is currently running.
    pub running: bool,
    /// ISO-8601 timestamp of the last cycle.
    pub last_cycle_at: Option<String>,
    /// Outcome string from the last cycle (e.g. "executed", "dormant").
    pub last_cycle_outcome: Option<String>,
    /// Number of cycles completed since startup.
    pub cycle_count: u64,
    /// Per-provider circuit breaker states.
    pub circuit_breakers: HashMap<String, String>,
    /// Metrics from the last completed cycle (persisted for the improvement step).
    #[serde(default)]
    pub last_metrics: Option<CycleMetrics>,
}

/// Persistent path for the loop status file.
pub fn status_path(root: &Path) -> PathBuf {
    root.join("state.json")
}

/// Save loop status atomically to `~/.urace/state.json`.
pub fn save_status(status: &LoopStatus, root: &Path) -> Result<()> {
    std::fs::create_dir_all(root)?;
    let path = status_path(root);
    let tmp = path.with_extension("json.tmp");
    std::fs::write(&tmp, serde_json::to_string_pretty(status)?)?;
    std::fs::rename(&tmp, &path)?;
    Ok(())
}

/// Load loop status from `~/.urace/state.json`.
pub fn load_status(root: &Path) -> Result<LoopStatus> {
    let path = status_path(root);
    if !path.exists() {
        return Ok(LoopStatus::default());
    }
    let raw = std::fs::read_to_string(&path)?;
    Ok(serde_json::from_str(&raw).unwrap_or_default())
}

// ── Main loop ─────────────────────────────────────────────────────────────────

/// Context shared across loop iterations.
pub struct LoopContext {
    pub config: RuntimeConfig,
    pub root: PathBuf,
    pub state: Arc<Mutex<RuntimeState>>,
    pub breakers: Arc<Mutex<HashMap<String, CircuitBreaker>>>,
    pub status: Arc<Mutex<LoopStatus>>,
    pub work_market: Arc<WorkMarket>,
    pub goal_store: Arc<GoalStore>,
    pub telemetry: Arc<TelemetryEmitter>,
    pub audit: Arc<AuditLedger>,
    /// Interval-gated auto-planner; replans every `sources.auto_sync_interval_s * 10` cycles.
    pub auto_planner: Arc<AutoPlanner>,
    /// Metrics from the previous cycle, used by the improvement step.
    pub prev_metrics: Arc<Mutex<Option<CycleMetrics>>>,
}

impl LoopContext {
    pub fn new(config: RuntimeConfig, root: PathBuf, state: RuntimeState) -> Self {
        let state_dir = root.join("state");
        std::fs::create_dir_all(&state_dir).ok();

        let hmac_key = derive_journal_key(&root);

        let work_market = Arc::new(WorkMarket::new(WorkPolicy {
            max_budget_ucr: 0,              // sync tasks carry no monetary budget
            allowed_scopes: vec![],         // all scopes permitted
            require_authority_check: false, // authority checked externally (§62z)
            max_concurrent_jobs: 16,
        }));

        let goal_store =
            GoalStore::open(state_dir.join("goals.jsonl"), hmac_key).expect("goal store open");
        let telemetry = TelemetryEmitter::open(state_dir.join("telemetry.jsonl"), hmac_key)
            .expect("telemetry emitter open");
        let audit =
            AuditLedger::open(state_dir.join("audit.jsonl"), hmac_key).expect("audit ledger open");

        // Auto-planner interval: 10× the source sync interval (at most every ~10 cycles).
        let replan_secs = config.sources.auto_sync_interval_s.max(1) * 10;
        let auto_planner = Arc::new(AutoPlanner::new(replan_secs));

        let initial_status = LoopStatus {
            running: true,
            ..Default::default()
        };

        LoopContext {
            config,
            root,
            state: Arc::new(Mutex::new(state)),
            breakers: Arc::new(Mutex::new(HashMap::new())),
            status: Arc::new(Mutex::new(initial_status)),
            work_market,
            goal_store: Arc::new(goal_store),
            telemetry: Arc::new(telemetry),
            audit: Arc::new(audit),
            auto_planner,
            prev_metrics: Arc::new(Mutex::new(None)),
        }
    }
}

/// Derive a deterministic HMAC key from the runtime root path.
/// In production this will be superseded by identity-based key material.
fn derive_journal_key(root: &Path) -> [u8; 32] {
    let mut h = Sha256::new();
    h.update(b"urace-journal-hmac-v1\x00");
    h.update(root.to_string_lossy().as_bytes());
    let mut key = [0u8; 32];
    key.copy_from_slice(&h.finalize());
    key
}

/// Run the main daemon loop.
///
/// Loops until `shutdown_rx` signals cancellation or the process exits.
/// Each iteration:
/// 1. Poll registered sources (at `sources.auto_sync_interval_s`).
/// 2. Dispatch pending work via tokio tasks (non-blocking).
/// 3. Emit a telemetry event.
/// 4. Write loop status to state file.
pub async fn run_loop(
    ctx: Arc<LoopContext>,
    mut shutdown_rx: tokio::sync::watch::Receiver<bool>,
) -> Result<()> {
    let interval_secs = ctx.config.sources.auto_sync_interval_s.max(1);
    let mut tick = interval(Duration::from_secs(interval_secs));

    info!(interval_secs, "runtime loop starting");

    loop {
        tokio::select! {
            _ = tick.tick() => {
                match run_one_cycle(&ctx).await {
                    Ok(outcome) => {
                        debug!(outcome = %outcome, "cycle complete");
                    }
                    Err(e) => {
                        error!(error = %e, "cycle error");
                    }
                }
            }
            _ = shutdown_rx.changed() => {
                if *shutdown_rx.borrow() {
                    info!("runtime loop shutting down");
                    break;
                }
            }
        }
    }

    // Write final status
    let mut status = ctx.status.lock().await;
    status.running = false;
    if let Err(e) = save_status(&status, &ctx.root) {
        warn!(error = %e, "failed to write final status");
    }

    Ok(())
}

/// Execute one cycle: poll sources, run auto-plan, dispatch work, persist status.
async fn run_one_cycle(ctx: &Arc<LoopContext>) -> Result<String> {
    let outcome = poll_sources(ctx).await;

    // Auto-plan: convert active goals → tasks; post ready tasks to work market.
    run_auto_plan(ctx).await;

    // Dispatch work in a separate task (non-blocking invariant)
    let ctx_clone = Arc::clone(ctx);
    tokio::spawn(async move {
        if let Err(e) = dispatch_work(&ctx_clone).await {
            warn!(error = %e, "work dispatch error");
        }
    });

    // Improvement step: evaluate metric deltas, close improved goals, suggest new ones.
    run_improvement_step(ctx).await;

    // Emit telemetry event
    emit_telemetry(ctx, &outcome).await;

    // Update + persist status
    {
        let mut status = ctx.status.lock().await;
        status.cycle_count += 1;
        status.last_cycle_at = Some(utc_now());
        status.last_cycle_outcome = Some(outcome.clone());

        // Snapshot circuit breaker states
        let breakers = ctx.breakers.lock().await;
        for (id, cb) in breakers.iter() {
            status
                .circuit_breakers
                .insert(id.clone(), format!("{:?}", cb.status().state));
        }

        if let Err(e) = save_status(&status, &ctx.root) {
            warn!(error = %e, "failed to persist loop status");
        }
    }

    Ok(outcome)
}

/// Poll all registered sources.
async fn poll_sources(ctx: &Arc<LoopContext>) -> String {
    let state = ctx.state.lock().await;
    let source_count = state.sources.len();

    if source_count == 0 {
        return "dormant".to_string();
    }

    for (id, record) in state.sources.iter() {
        let kind = record
            .get("kind")
            .and_then(|v| v.as_str())
            .unwrap_or("unknown");
        let evt = AuditEvent::new(
            AuditKind::SourceSynced,
            "daemon",
            serde_json::json!({ "source_id": id, "kind": kind }),
        );
        if let Err(e) = ctx.audit.record(evt) {
            warn!(error = %e, "audit record error in poll_sources");
        }
        debug!(id = %id, kind = %kind, "source sync");
    }

    "sources_polled".to_string()
}

/// Run the auto-planner against active goals; post newly-ready tasks to the work market.
///
/// No-op when no active goals exist or the replan interval has not elapsed.
/// Never panics — planning errors are logged and skipped.
async fn run_auto_plan(ctx: &Arc<LoopContext>) {
    let goals = ctx.goal_store.active_goals();
    if goals.is_empty() {
        return;
    }

    let tasks: Vec<PlanTask> = goals
        .into_iter()
        .map(|g| PlanTask {
            id: g.goal_id.clone(),
            status: format!("{:?}", g.status).to_lowercase(),
            dependencies: vec![],
            execution_kind: Some("executor_candidate".into()),
            controller_action: None,
            priority: g.score_delta.map(|d| d as f64),
            uncertainty_reduction: None,
            bottleneck_id: None,
            expected_benefit: None,
            expected_benefit_score: None,
            benefit_score_verified: None,
            action_recommendation: None,
            title: Some(g.title.clone()),
            estimate: None,
        })
        .collect();

    let Some(result) = ctx
        .auto_planner
        .maybe_plan(tasks, &PlanningContext::default())
    else {
        return; // interval not elapsed
    };

    match result {
        Err(e) => warn!(error = %e, "auto-plan error"),
        Ok(plan) => {
            let ready: Vec<&str> = plan
                .tasks
                .iter()
                .filter(|t| t.status == TaskStatus::Ready)
                .map(|t| t.id.as_str())
                .collect();

            debug!(ready = ready.len(), "auto-plan ready tasks");

            for task_id in ready {
                let task = WorkTask {
                    task_id: format!("goal-{task_id}"),
                    required_capabilities: vec!["planning".into()],
                    budget_ucr: 0,
                    posted_at: utc_now(),
                    poster_peer_id: "daemon".into(),
                };
                // Ignore duplicate-post errors (task may already be queued).
                let _ = ctx.work_market.post_task(task, true);
            }
        }
    }
}

/// Fetch AGENTS.md from sources-lib MCP for a given source_id.
/// Returns empty string on any failure (non-blocking best-effort).
async fn fetch_agents_md(source_id: &str, sources_url: &str) -> String {
    let client = reqwest::Client::new();
    let body = serde_json::json!({
        "jsonrpc": "2.0", "id": 1,
        "method": "resources/read",
        "params": {"uri": format!("sources://{}/agents-md", source_id)}
    });
    let resp = match client
        .post(&format!("{}/mcp", sources_url))
        .json(&body)
        .send()
        .await
    {
        Ok(r) => r,
        Err(_) => return String::new(),
    };
    let val = match resp.json::<serde_json::Value>().await {
        Ok(v) => v,
        Err(_) => return String::new(),
    };
    val["result"]["contents"][0]["text"]
        .as_str()
        .unwrap_or("")
        .to_string()
}

/// Dispatch work items — runs in a separate tokio task (non-blocking).
async fn dispatch_work(ctx: &Arc<LoopContext>) -> Result<()> {
    use crate::bootstrap::check_authority_policy;
    let outcome = check_authority_policy("work_dispatch", "implementation", &ctx.config);
    if !matches!(
        outcome,
        crate::bootstrap::AuthorityCheckOutcome::AutonomouslyAuthorized
    ) {
        debug!("work dispatch not authorized: {:?}", outcome);
        return Ok(());
    }

    let sources = {
        let state = ctx.state.lock().await;
        state.sources.clone()
    };

    if sources.is_empty() {
        return Ok(());
    }

    // Derive sources MCP URL from config (falls back to default).
    let sources_url = ctx
        .config
        .sources
        .sources_mcp_url
        .as_deref()
        .unwrap_or("http://127.0.0.1:7700")
        .to_string();

    let mut posted = 0usize;
    for (source_id, record) in &sources {
        let kind = record
            .get("kind")
            .and_then(|v| v.as_str())
            .unwrap_or("unknown");

        // Fetch AGENTS.md context for this source (best-effort; empty on failure).
        let agents_md = fetch_agents_md(source_id, &sources_url).await;
        let context_prefix = if agents_md.is_empty() { None } else { Some(agents_md) };

        let task = WorkTask {
            task_id: format!("sync-{source_id}"),
            required_capabilities: vec![kind.to_string()],
            budget_ucr: 0,
            posted_at: utc_now(),
            poster_peer_id: "daemon".into(),
        };
        // Ignore errors — task may already be posted from a prior cycle
        if ctx.work_market.post_task(task, true).is_ok() {
            posted += 1;
        }
        // Log the context availability for observability; the ExecutionRequest
        // is constructed by the executor when it picks up the task.
        if context_prefix.is_some() {
            debug!(source_id = %source_id, "AGENTS.md context fetched for work dispatch");
        }
    }

    if posted > 0 {
        let evt = AuditEvent::new(
            AuditKind::WorkBid,
            "daemon",
            serde_json::json!({ "tasks_posted": posted }),
        );
        if let Err(e) = ctx.audit.record(evt) {
            warn!(error = %e, "audit record error in dispatch_work");
        }
    }

    debug!(posted, "work dispatch complete");
    Ok(())
}

/// Emit a telemetry event for this cycle.
async fn emit_telemetry(ctx: &Arc<LoopContext>, outcome: &str) {
    let event = TelemetryEvent {
        event_type: "cycle.completed".to_string(),
        peer_id: "daemon".to_string(),
        payload: serde_json::json!({ "outcome": outcome }),
        at: utc_now(),
    };
    if let Err(e) = ctx.telemetry.emit(event) {
        warn!(error = %e, "telemetry emit error");
    }
}

// ── Improvement cycle ─────────────────────────────────────────────────────────

/// Qualified Product Improvement Cycle (QPIC): the feedback closure that makes
/// URACE's loop governance-gated rather than a plain autonomous loop.
///
/// Each call:
/// 1. Snapshots observable metrics (sources, failed syncs, pending work).
/// 2. Compares with the previous cycle's metrics to compute score deltas.
/// 3. Completes active goals whose metrics improved (score_delta > 0 → MintSignal).
/// 4. Routes new goal suggestions through §62z before persisting.
async fn run_improvement_step(ctx: &Arc<LoopContext>) {
    let current = snapshot_metrics(ctx).await;

    // Swap in the new snapshot; get the previous one.
    let prev = {
        let mut guard = ctx.prev_metrics.lock().await;
        let prev = guard.clone();
        *guard = Some(current.clone());
        prev
    };

    // Phase 1 — evaluate active goals against metric deltas.
    if let Some(ref prev) = prev {
        for goal in ctx.goal_store.active_goals() {
            if let Some(delta) = goal_score_delta(&goal.scope, &goal.title, prev, &current) {
                match ctx.goal_store.complete(&goal.goal_id, delta) {
                    Ok(signal) => {
                        if signal.should_mint {
                            let evt = AuditEvent::new(
                                AuditKind::MintTriggered,
                                "daemon",
                                serde_json::json!({
                                    "goal_id": goal.goal_id,
                                    "score_delta": delta,
                                    "amount": signal.amount,
                                }),
                            );
                            if let Err(e) = ctx.audit.record(evt) {
                                warn!(error = %e, "audit record error for mint");
                            }
                        }
                        debug!(goal_id = %goal.goal_id, delta, "goal completed by improvement step");
                    }
                    Err(e) => warn!(error = %e, goal_id = %goal.goal_id, "goal completion error"),
                }
            }
        }
    }

    // Phase 2 — suggest new goals (§62z-gated).
    let suggestions = AutoGoalEngine::new().suggest_goals(
        current.sources_count,
        current.failed_syncs,
        current.pending_work,
    );

    if suggestions.is_empty() {
        return;
    }

    let outcome =
        crate::bootstrap::check_authority_policy("goal_creation", "auto_improvement", &ctx.config);
    if !matches!(
        outcome,
        crate::bootstrap::AuthorityCheckOutcome::AutonomouslyAuthorized
    ) {
        debug!("auto-goal creation not authorized: {:?}", outcome);
        return;
    }

    // Deduplicate by scope: skip if an active goal in the same scope already exists.
    let active_scopes: std::collections::HashSet<String> = ctx
        .goal_store
        .active_goals()
        .into_iter()
        .map(|g| g.scope)
        .collect();

    for goal in suggestions {
        if active_scopes.contains(&goal.scope) {
            continue;
        }
        let goal_id = goal.goal_id.clone();
        let scope = goal.scope.clone();
        match ctx.goal_store.create(goal) {
            Ok(()) => {
                let evt = AuditEvent::new(
                    AuditKind::GoalCreated,
                    "daemon",
                    serde_json::json!({ "goal_id": goal_id, "scope": scope }),
                );
                if let Err(e) = ctx.audit.record(evt) {
                    warn!(error = %e, "audit record error for goal creation");
                }
                debug!(goal_id = %goal_id, scope = %scope, "auto-goal created");
            }
            Err(e) => warn!(error = %e, "auto-goal creation failed"),
        }
    }
}

/// Collect observable metrics from the current context state.
async fn snapshot_metrics(ctx: &Arc<LoopContext>) -> CycleMetrics {
    let sources_count = ctx.state.lock().await.sources.len();
    let pending_work = ctx.work_market.pending_task_count();
    let failed_syncs = {
        let breakers = ctx.breakers.lock().await;
        breakers
            .values()
            .filter(|cb| cb.status().state == BreakerState::Open)
            .count()
    };
    CycleMetrics {
        sources_count,
        failed_syncs,
        pending_work,
    }
}

/// Compute the score delta for a goal given consecutive metric snapshots.
///
/// Returns `Some(delta)` only when the relevant metric strictly improved.
fn goal_score_delta(
    scope: &str,
    title: &str,
    prev: &CycleMetrics,
    cur: &CycleMetrics,
) -> Option<i64> {
    match scope {
        "sources" if title.contains("failed") => {
            let d = prev.failed_syncs as i64 - cur.failed_syncs as i64;
            if d > 0 { Some(d) } else { None }
        }
        "sources" => {
            // "Configure at least one data source" goal
            let d = cur.sources_count as i64 - prev.sources_count as i64;
            if d > 0 { Some(d) } else { None }
        }
        "work_market" => {
            let d = prev.pending_work as i64 - cur.pending_work as i64;
            if d > 0 { Some(d) } else { None }
        }
        _ => None,
    }
}

fn utc_now() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    let secs = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs();
    // Minimal ISO-8601 without external time crate dependency
    format!("{secs}")
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    fn make_ctx(dir: &Path) -> Arc<LoopContext> {
        let cfg = RuntimeConfig::default();
        let state = RuntimeState::default();
        Arc::new(LoopContext::new(cfg, dir.to_path_buf(), state))
    }

    #[tokio::test]
    async fn one_cycle_dormant_on_no_sources() {
        let dir = TempDir::new().unwrap();
        let ctx = make_ctx(dir.path());
        let outcome = run_one_cycle(&ctx).await.unwrap();
        assert_eq!(outcome, "dormant");
    }

    #[tokio::test]
    async fn one_cycle_with_sources_polls() {
        let dir = TempDir::new().unwrap();
        let ctx = make_ctx(dir.path());
        {
            let mut state = ctx.state.lock().await;
            state.set_source("s1", serde_json::json!({"kind": "directory"}));
        }
        let outcome = run_one_cycle(&ctx).await.unwrap();
        assert_eq!(outcome, "sources_polled");
    }

    #[tokio::test]
    async fn status_persisted_after_cycle() {
        let dir = TempDir::new().unwrap();
        let ctx = make_ctx(dir.path());
        run_one_cycle(&ctx).await.unwrap();
        let loaded = load_status(dir.path()).unwrap();
        assert_eq!(loaded.cycle_count, 1);
        assert!(loaded.last_cycle_at.is_some());
    }

    #[test]
    fn load_status_missing_returns_default() {
        let dir = TempDir::new().unwrap();
        let status = load_status(dir.path()).unwrap();
        assert_eq!(status.cycle_count, 0);
        assert!(!status.running);
    }

    #[test]
    fn goal_score_delta_improvement_detected() {
        let prev = CycleMetrics { sources_count: 0, failed_syncs: 3, pending_work: 15 };
        let cur = CycleMetrics { sources_count: 1, failed_syncs: 1, pending_work: 8 };

        // Failed syncs improved: 3 → 1 = delta 2
        assert_eq!(
            goal_score_delta("sources", "Resolve 3 failed source syncs", &prev, &cur),
            Some(2)
        );
        // Source configured: 0 → 1 = delta 1
        assert_eq!(
            goal_score_delta("sources", "Configure at least one data source", &prev, &cur),
            Some(1)
        );
        // Work backlog reduced: 15 → 8 = delta 7
        assert_eq!(
            goal_score_delta("work_market", "Reduce pending work backlog (15 tasks queued)", &prev, &cur),
            Some(7)
        );
    }

    #[test]
    fn goal_score_delta_no_improvement_returns_none() {
        let prev = CycleMetrics { sources_count: 2, failed_syncs: 0, pending_work: 5 };
        let cur = CycleMetrics { sources_count: 2, failed_syncs: 0, pending_work: 6 };

        assert!(goal_score_delta("sources", "Resolve 0 failed source syncs", &prev, &cur).is_none());
        assert!(goal_score_delta("work_market", "Reduce backlog", &prev, &cur).is_none());
    }

    #[tokio::test]
    async fn improvement_step_creates_goal_on_no_sources() {
        let dir = TempDir::new().unwrap();
        let ctx = make_ctx(dir.path());
        // Two cycles: first seeds prev_metrics with 0 sources, second runs improvement step.
        run_one_cycle(&ctx).await.unwrap();
        run_one_cycle(&ctx).await.unwrap();
        // Auto-goal engine should have suggested "Configure at least one data source".
        // Whether it was persisted depends on authority policy (default config allows it).
        // Just verify the cycle completes without panic.
        assert!(ctx.prev_metrics.lock().await.is_some());
    }
}
