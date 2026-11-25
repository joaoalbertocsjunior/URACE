//! Live metrics endpoints.
//!
//! Ports `routes/metrics.py` to Rust.
//!
//! The Python version maintained a process-level accumulator subscribed to the
//! event bus. In the Rust port, the web layer is not yet connected to the daemon
//! event bus, so we derive metrics from `<root>/state/state.json` instead —
//! the same approach used by `vitals.rs`.
//!
//! * `GET /api/metrics/live`   — return accumulated metrics as JSON
//! * `GET /api/metrics/stream` — SSE stream stub (snapshot + keep-alive)

use crate::{auth::BearerToken, state_reader, AppState};
use axum::{
    extract::State,
    response::sse::{Event, KeepAlive, Sse},
    response::{IntoResponse, Response},
    routing::get,
    Json, Router,
};
use futures::stream;
use serde_json::Value;

pub fn router() -> Router<AppState> {
    Router::new()
        .route("/live", get(live_metrics))
        .route("/stream", get(metrics_stream))
}

/// Extract numeric metrics from `state.json`.
fn metrics_snapshot(root: &std::path::Path) -> Value {
    let state = state_reader::read_state(root);

    let aps_score = state
        .get("aps_score")
        .or_else(|| state.get("current_aps_score"))
        .cloned()
        .unwrap_or(Value::Null);

    let cycle_count = state
        .get("checkpoints")
        .and_then(|v| v.as_array())
        .map(|a| a.len())
        .unwrap_or(0);

    let evidence_count = state
        .get("evidence")
        .and_then(|v| v.as_array())
        .map(|a| a.len())
        .unwrap_or(0);

    let objectives_count = state
        .get("objectives")
        .and_then(|v| v.as_array())
        .map(|a| a.len())
        .unwrap_or(0);

    // Include any explicit `metrics` sub-object from state if present.
    let metrics_sub = state.get("metrics").cloned().unwrap_or(Value::Null);

    // Carry forward event-bus counters the Python version tracked.
    // These are not yet wired to live events in the Rust daemon; expose as
    // zero so the dashboard continues to function without error.
    let cycle_started = state
        .get("cycle_started_count")
        .and_then(|v| v.as_u64())
        .unwrap_or(0);
    let cycle_completed = state
        .get("cycle_completed_count")
        .and_then(|v| v.as_u64())
        .unwrap_or(cycle_count as u64);
    let cycle_last_outcome = state
        .get("last_cycle_outcome")
        .cloned()
        .unwrap_or(Value::Null);
    let cycle_last_id = state.get("last_cycle_id").cloned().unwrap_or(Value::Null);

    serde_json::json!({
        "aps_score": aps_score,
        "cycle_count": cycle_count,
        "evidence_count": evidence_count,
        "objectives_count": objectives_count,
        "metrics": metrics_sub,
        // Event-bus counters (zero until daemon RPC is wired)
        "cycle_started": cycle_started,
        "cycle_completed": cycle_completed,
        "cycle_last_outcome": cycle_last_outcome,
        "cycle_last_id": cycle_last_id,
        "ledger_earned_total": 0,
        "ledger_spent_total": 0,
        "ledger_last_earn_peer": null,
        "ledger_last_spend_peer": null,
    })
}

async fn live_metrics(State(s): State<AppState>, _auth: BearerToken) -> Json<Value> {
    Json(metrics_snapshot(&s.root))
}

async fn metrics_stream(State(s): State<AppState>, _auth: BearerToken) -> Response {
    // Send one snapshot event then keep alive.
    // Full live-streaming requires daemon RPC wiring (future work).
    let snapshot = metrics_snapshot(&s.root);
    let data = serde_json::to_string(&snapshot).unwrap_or_default();

    let events: Vec<Result<Event, std::convert::Infallible>> =
        vec![Ok(Event::default().event("metrics").data(data))];

    Sse::new(stream::iter(events))
        .keep_alive(KeepAlive::default())
        .into_response()
}
