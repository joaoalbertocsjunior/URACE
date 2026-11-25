//! GET /api/cycle/state — cycle pipeline state, optionally as HTMX partial.
//!
//! Ports `routes/cycle.py`. When the request carries an `HX-Request` header
//! the handler returns the `cycle_state.html` partial rendered with the last 5
//! items from each pipeline column; otherwise it returns JSON counts.

use axum::{
    extract::{Request, State},
    response::{Html, IntoResponse, Response},
    routing::get,
    Json, Router,
};
use minijinja::context;
use crate::{AppState, auth::BearerToken, state_reader};

pub fn router() -> Router<AppState> {
    Router::new().route("/state", get(cycle_state))
}

async fn cycle_state(
    State(s): State<AppState>,
    _auth: BearerToken,
    req: Request,
) -> Response {
    let is_htmx = req.headers().get("hx-request").is_some();
    let state = state_reader::read_state(&s.root);

    fn last5(val: Option<&serde_json::Value>) -> Vec<serde_json::Value> {
        val.and_then(|v| v.as_array())
            .map(|a| a.iter().rev().take(5).rev().cloned().collect())
            .unwrap_or_default()
    }

    let objectives_raw = state.get("objectives").and_then(|v| v.as_array()).cloned().unwrap_or_default();
    // Prefer active objectives; fall back to last 5 of all
    let active: Vec<serde_json::Value> = objectives_raw.iter()
        .filter(|o| o.get("status").and_then(|v| v.as_str()) == Some("active"))
        .cloned()
        .collect();
    let objectives: Vec<serde_json::Value> = if !active.is_empty() {
        active.iter().rev().take(5).rev().cloned().collect()
    } else {
        objectives_raw.iter().rev().take(5).rev().cloned().collect()
    };

    let evidence = last5(state.get("evidence"));
    let decisions = last5(state.get("decision_records"));
    let operations = last5(state.get("operations"));
    let checkpoints = last5(state.get("checkpoints"));
    let lifecycle_state = state.get("lifecycle_state")
        .and_then(|v| v.as_str())
        .unwrap_or("UNKNOWN")
        .to_string();

    if is_htmx {
        let tmpl = match s.env.get_template("cycle_state.html") {
            Ok(t) => t,
            Err(e) => return Html(format!("<!-- template error: {e} -->")).into_response(),
        };
        let html = tmpl.render(context! {
            objectives => objectives,
            evidence => evidence,
            decisions => decisions,
            operations => operations,
            checkpoints => checkpoints,
            lifecycle_state => lifecycle_state,
        }).unwrap_or_else(|e| format!("<!-- render error: {e} -->"));
        Html(html).into_response()
    } else {
        Json(serde_json::json!({
            "objectives_count": objectives_raw.len(),
            "evidence_count": state.get("evidence").and_then(|v| v.as_array()).map(|a| a.len()).unwrap_or(0),
            "decisions_count": state.get("decision_records").and_then(|v| v.as_array()).map(|a| a.len()).unwrap_or(0),
            "operations_count": state.get("operations").and_then(|v| v.as_array()).map(|a| a.len()).unwrap_or(0),
            "checkpoints_count": state.get("checkpoints").and_then(|v| v.as_array()).map(|a| a.len()).unwrap_or(0),
            "lifecycle_state": lifecycle_state,
        })).into_response()
    }
}
