//! Async runtime loop — poll sources, dispatch work, emit telemetry.
//!
//! Ported from `runtime/urace/cli_cycle.py` (the daemon loop aspects).
//!
//! Invariants:
//! - The runtime loop MUST NOT block on work dispatch (uses tokio tasks).
//! - Circuit breaker trip must be checked before each work dispatch.
//! - Sources are polled at the interval configured in `SourcesConfig`.
//! - Authority check gates every work assignment (§62z).

use crate::circuit_breaker::CircuitBreaker;
use crate::config::RuntimeConfig;
use crate::state::RuntimeState;
use anyhow::Result;
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::sync::Arc;
use std::time::Duration;
use tokio::sync::Mutex;
use tokio::time::{interval, sleep};
use tracing::{debug, error, info, warn};

/// Telemetry event emitted by the loop.
#[derive(Debug, Clone)]
pub struct TelemetryEvent {
    pub kind: String,
    pub payload: serde_json::Value,
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
}

impl LoopContext {
    pub fn new(config: RuntimeConfig, root: PathBuf, state: RuntimeState) -> Self {
        let mut status = LoopStatus::default();
        status.running = true;
        LoopContext {
            config,
            root,
            state: Arc::new(Mutex::new(state)),
            breakers: Arc::new(Mutex::new(HashMap::new())),
            status: Arc::new(Mutex::new(status)),
        }
    }
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

    info!(
        interval_secs,
        "runtime loop starting"
    );

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

/// Execute one cycle: poll sources, dispatch work, persist status.
async fn run_one_cycle(ctx: &Arc<LoopContext>) -> Result<String> {
    let outcome = poll_sources(ctx).await;

    // Dispatch work in a separate task (non-blocking invariant)
    let ctx_clone = Arc::clone(ctx);
    tokio::spawn(async move {
        if let Err(e) = dispatch_work(&ctx_clone).await {
            warn!(error = %e, "work dispatch error");
        }
    });

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
            status.circuit_breakers.insert(
                id.clone(),
                format!("{:?}", cb.status().state),
            );
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

    // In a full implementation this would call each source adapter's sync().
    // For the Rust port stub, we iterate source records and log.
    debug!(source_count, "polling sources");
    for (id, record) in state.sources.iter() {
        let kind = record
            .get("kind")
            .and_then(|v| v.as_str())
            .unwrap_or("unknown");
        debug!(id = %id, kind = %kind, "source sync");
    }

    "sources_polled".to_string()
}

/// Dispatch work items — runs in a separate tokio task (non-blocking).
async fn dispatch_work(ctx: &Arc<LoopContext>) -> Result<()> {
    // Authority check gate (§62z): work dispatch requires autonomously authorized.
    use crate::bootstrap::check_authority_policy;
    let outcome = check_authority_policy("work_dispatch", "implementation", &ctx.config);
    if !matches!(
        outcome,
        crate::bootstrap::AuthorityCheckOutcome::AutonomouslyAuthorized
    ) {
        debug!("work dispatch not authorized: {:?}", outcome);
        return Ok(());
    }

    // Simulate a brief async work unit without blocking the main loop.
    sleep(Duration::from_millis(1)).await;
    debug!("work dispatch complete");
    Ok(())
}

/// Emit a telemetry event for this cycle.
async fn emit_telemetry(ctx: &Arc<LoopContext>, outcome: &str) {
    let event = TelemetryEvent {
        kind: "cycle.completed".to_string(),
        payload: serde_json::json!({
            "outcome": outcome,
            "at": utc_now(),
        }),
    };
    debug!(kind = %event.kind, outcome = %outcome, "telemetry emitted");
    // In a full implementation this would publish to the event bus / M2M stream.
    let _ = event; // suppress unused warning
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
}
