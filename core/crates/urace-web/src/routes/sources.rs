//! GET  /api/sources/          — list source adapters from state.json
//! GET  /api/sources/kinds     — list registered source kind names
//! GET  /api/sources/:id       — detail for a specific source instance
//! GET  /api/sources/:id/actions — enabled actions for a source
//! POST /api/sources/:id/actions/:action/enable  — enable an action
//! DELETE /api/sources/:id/actions/:action/enable — disable an action
//! POST /api/sources/:id/act — execute an action (stub)
//!
//! Ports `routes/sources.py`. Source registry read is implemented from state;
//! the act endpoint is a stub (requires live adapter registration).

use crate::{auth::BearerToken, state_reader, AppState};
use axum::{
    extract::{Path, Query, State},
    routing::{delete, get, post},
    Json, Router,
};
use serde::Deserialize;

pub fn router() -> Router<AppState> {
    Router::new()
        .route("/", get(list_sources))
        .route("/kinds", get(list_kinds))
        .route("/:source_id", get(get_source))
        .route("/:source_id/actions", get(get_source_actions))
        .route(
            "/:source_id/actions/:action_name/enable",
            post(enable_source_action),
        )
        .route(
            "/:source_id/actions/:action_name/enable",
            delete(disable_source_action),
        )
        .route("/:source_id/act", post(act_on_source))
}

#[derive(Deserialize)]
pub struct SourcesQuery {
    pub kind: Option<String>,
}

async fn list_sources(
    State(s): State<AppState>,
    _auth: BearerToken,
    Query(q): Query<SourcesQuery>,
) -> Json<serde_json::Value> {
    let state = state_reader::read_state(&s.root);
    let sources_state = state
        .get("sources")
        .and_then(|v| v.as_object())
        .cloned()
        .unwrap_or_default();

    // Build adapter summary from state (without live adapter registry)
    let mut kinds_seen: std::collections::BTreeMap<String, Vec<serde_json::Value>> =
        Default::default();
    for (_id, record) in &sources_state {
        let kind = record
            .get("kind")
            .and_then(|v| v.as_str())
            .unwrap_or("unknown")
            .to_string();
        if let Some(ref filter) = q.kind {
            if &kind != filter {
                continue;
            }
        }
        kinds_seen.entry(kind).or_default().push(record.clone());
    }

    let adapters: Vec<serde_json::Value> = kinds_seen
        .into_iter()
        .map(|(kind, instances)| {
            let instance_list: Vec<serde_json::Value> = instances
                .iter()
                .map(|s| {
                    serde_json::json!({
                        "id": s.get("id"),
                        "status": s.get("status"),
                        "enabled": s.get("enabled"),
                        "enabled_actions": s.get("adapter_state")
                            .and_then(|a| a.get("enabled_actions"))
                            .cloned()
                            .unwrap_or(serde_json::Value::Array(vec![])),
                    })
                })
                .collect();
            serde_json::json!({
                "kind": kind,
                "registered": true,
                "instance_count": instance_list.len(),
                "instances": instance_list,
            })
        })
        .collect();

    // allow_act_global from config
    let allow_act = {
        let config_path = s.root.join("config.json");
        std::fs::read_to_string(&config_path)
            .ok()
            .and_then(|c| serde_json::from_str::<serde_json::Value>(&c).ok())
            .and_then(|c| {
                c.get("sources")
                    .and_then(|s| s.get("allow_act"))
                    .and_then(|v| v.as_bool())
            })
            .unwrap_or(false)
    };

    Json(serde_json::json!({
        "adapters": adapters,
        "total_kinds": adapters.len(),
        "allow_act_global": allow_act,
    }))
}

async fn list_kinds(State(s): State<AppState>, _auth: BearerToken) -> Json<serde_json::Value> {
    let state = state_reader::read_state(&s.root);
    let mut kinds: std::collections::BTreeSet<String> = Default::default();
    if let Some(sources) = state.get("sources").and_then(|v| v.as_object()) {
        for record in sources.values() {
            if let Some(k) = record.get("kind").and_then(|v| v.as_str()) {
                kinds.insert(k.to_string());
            }
        }
    }
    Json(serde_json::json!({ "kinds": kinds.into_iter().collect::<Vec<_>>() }))
}

async fn get_source(
    State(s): State<AppState>,
    _auth: BearerToken,
    Path(source_id): Path<String>,
) -> (axum::http::StatusCode, Json<serde_json::Value>) {
    let state = state_reader::read_state(&s.root);
    if let Some(record) = state.get("sources").and_then(|v| v.get(&source_id)) {
        (axum::http::StatusCode::OK, Json(record.clone()))
    } else {
        (
            axum::http::StatusCode::NOT_FOUND,
            Json(serde_json::json!({ "detail": format!("Source {source_id:?} not found") })),
        )
    }
}

async fn get_source_actions(
    State(s): State<AppState>,
    _auth: BearerToken,
    Path(source_id): Path<String>,
) -> (axum::http::StatusCode, Json<serde_json::Value>) {
    let state = state_reader::read_state(&s.root);
    let sources = state.get("sources").and_then(|v| v.as_object());
    if let Some(record) = sources.and_then(|m| m.get(&source_id)) {
        let kind = record
            .get("kind")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_string();
        let enabled = record
            .get("adapter_state")
            .and_then(|a| a.get("enabled_actions"))
            .cloned()
            .unwrap_or(serde_json::Value::Array(vec![]));
        let allow_act = {
            let config_path = s.root.join("config.json");
            std::fs::read_to_string(&config_path)
                .ok()
                .and_then(|c| serde_json::from_str::<serde_json::Value>(&c).ok())
                .and_then(|c| {
                    c.get("sources")
                        .and_then(|s| s.get("allow_act"))
                        .and_then(|v| v.as_bool())
                })
                .unwrap_or(false)
        };
        (
            axum::http::StatusCode::OK,
            Json(serde_json::json!({
                "source_id": source_id,
                "kind": kind,
                "actions": enabled,
                "allow_act_global": allow_act,
            })),
        )
    } else {
        (
            axum::http::StatusCode::NOT_FOUND,
            Json(serde_json::json!({ "detail": format!("Source {source_id:?} not found") })),
        )
    }
}

async fn enable_source_action(
    State(s): State<AppState>,
    _auth: BearerToken,
    Path((source_id, action_name)): Path<(String, String)>,
) -> (axum::http::StatusCode, Json<serde_json::Value>) {
    let state_path = s.root.join("state").join("state.json");
    let mut state = state_reader::read_state(&s.root);
    let sources = match state.get_mut("sources").and_then(|v| v.as_object_mut()) {
        Some(m) => m,
        None => {
            return (
                axum::http::StatusCode::NOT_FOUND,
                Json(serde_json::json!({ "detail": format!("Source {source_id:?} not found") })),
            )
        }
    };
    if let Some(record) = sources.get_mut(&source_id) {
        let astate = record
            .get_mut("adapter_state")
            .and_then(|v| v.as_object_mut());
        if let Some(astate) = astate {
            let enabled = astate
                .entry("enabled_actions")
                .or_insert_with(|| serde_json::Value::Array(vec![]));
            if let Some(arr) = enabled.as_array_mut() {
                if !arr.iter().any(|v| v.as_str() == Some(&action_name)) {
                    arr.push(serde_json::Value::String(action_name.clone()));
                }
            }
            let _ = std::fs::write(
                &state_path,
                serde_json::to_string(&state).unwrap_or_default(),
            );
            (
                axum::http::StatusCode::OK,
                Json(serde_json::json!({
                    "source_id": source_id,
                    "action": action_name,
                })),
            )
        } else {
            (
                axum::http::StatusCode::UNPROCESSABLE_ENTITY,
                Json(serde_json::json!({ "detail": "No adapter_state on record" })),
            )
        }
    } else {
        (
            axum::http::StatusCode::NOT_FOUND,
            Json(serde_json::json!({ "detail": format!("Source {source_id:?} not found") })),
        )
    }
}

async fn disable_source_action(
    State(s): State<AppState>,
    _auth: BearerToken,
    Path((source_id, action_name)): Path<(String, String)>,
) -> (axum::http::StatusCode, Json<serde_json::Value>) {
    let state_path = s.root.join("state").join("state.json");
    let mut state = state_reader::read_state(&s.root);
    let sources = match state.get_mut("sources").and_then(|v| v.as_object_mut()) {
        Some(m) => m,
        None => {
            return (
                axum::http::StatusCode::NOT_FOUND,
                Json(serde_json::json!({ "detail": format!("Source {source_id:?} not found") })),
            )
        }
    };
    if let Some(record) = sources.get_mut(&source_id) {
        if let Some(astate) = record
            .get_mut("adapter_state")
            .and_then(|v| v.as_object_mut())
        {
            if let Some(enabled) = astate
                .get_mut("enabled_actions")
                .and_then(|v| v.as_array_mut())
            {
                enabled.retain(|v| v.as_str() != Some(&action_name));
            }
            let _ = std::fs::write(
                &state_path,
                serde_json::to_string(&state).unwrap_or_default(),
            );
            (
                axum::http::StatusCode::OK,
                Json(serde_json::json!({
                    "source_id": source_id,
                    "action": action_name,
                })),
            )
        } else {
            (
                axum::http::StatusCode::UNPROCESSABLE_ENTITY,
                Json(serde_json::json!({ "detail": "No adapter_state on record" })),
            )
        }
    } else {
        (
            axum::http::StatusCode::NOT_FOUND,
            Json(serde_json::json!({ "detail": format!("Source {source_id:?} not found") })),
        )
    }
}

async fn act_on_source(
    State(_s): State<AppState>,
    _auth: BearerToken,
    Path(source_id): Path<String>,
) -> (axum::http::StatusCode, Json<serde_json::Value>) {
    // Live adapter dispatch requires the adapter registry; stub for now.
    (
        axum::http::StatusCode::NOT_IMPLEMENTED,
        Json(serde_json::json!({
            "detail": format!("Live act on source {source_id}: adapter dispatch not yet wired in Rust web layer.")
        })),
    )
}
