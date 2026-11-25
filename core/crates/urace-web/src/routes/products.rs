//! GET  /api/products/           — list products from state.json
//! GET  /api/products/status     — active product status
//! POST /api/products/:name/switch     — stub
//! POST /api/products/:name/activate   — stub
//! POST /api/products/:name/deactivate — stub
//! GET  /api/products/improvements     — improvements list
//!
//! Ports `routes/products.py`.

use axum::{
    extract::{Path, State},
    routing::{get, post},
    Json, Router,
};
use crate::{AppState, auth::BearerToken, state_reader};

pub fn router() -> Router<AppState> {
    Router::new()
        .route("/", get(products_list))
        .route("/status", get(products_status))
        .route("/improvements", get(products_improvements))
        .route("/:name/switch", post(products_switch))
        .route("/:name/activate", post(products_activate))
        .route("/:name/deactivate", post(products_deactivate))
}

async fn products_list(
    State(s): State<AppState>,
    _auth: BearerToken,
) -> Json<serde_json::Value> {
    let state = state_reader::read_state(&s.root);
    let products = state.get("products")
        .and_then(|v| v.as_array())
        .cloned()
        .unwrap_or_default();
    Json(serde_json::Value::Array(products))
}

async fn products_status(
    State(s): State<AppState>,
    _auth: BearerToken,
) -> Json<serde_json::Value> {
    let state = state_reader::read_state(&s.root);
    let active_product = state.get("active_product").cloned();
    let lifecycle_state = state.get("lifecycle_state")
        .and_then(|v| v.as_str())
        .unwrap_or("UNKNOWN");
    Json(serde_json::json!({
        "active_product": active_product,
        "lifecycle_state": lifecycle_state,
        "registry_entry": {},
    }))
}

async fn products_improvements(
    State(s): State<AppState>,
    _auth: BearerToken,
) -> Json<serde_json::Value> {
    let state = state_reader::read_state(&s.root);
    let products = state.get("products")
        .and_then(|v| v.as_array())
        .cloned()
        .unwrap_or_default();
    let improvement_list: Vec<serde_json::Value> = products.iter().map(|p| {
        serde_json::json!({
            "name": p.get("name"),
            "improvement_enabled": p.get("improvement_enabled").and_then(|v| v.as_bool()).unwrap_or(false),
            "improvement_supported": p.get("improvement_supported").and_then(|v| v.as_bool()).unwrap_or(false),
        })
    }).collect();
    Json(serde_json::json!({ "products": improvement_list }))
}

async fn products_switch(
    State(_s): State<AppState>,
    _auth: BearerToken,
    Path(name): Path<String>,
) -> Json<serde_json::Value> {
    Json(serde_json::json!({
        "status": "unavailable",
        "error": format!("Switch to product {name}: requires a running daemon.")
    }))
}

async fn products_activate(
    State(_s): State<AppState>,
    _auth: BearerToken,
    Path(name): Path<String>,
) -> Json<serde_json::Value> {
    Json(serde_json::json!({
        "status": "unavailable",
        "error": format!("Activate product {name}: requires a running daemon.")
    }))
}

async fn products_deactivate(
    State(_s): State<AppState>,
    _auth: BearerToken,
    Path(name): Path<String>,
) -> Json<serde_json::Value> {
    Json(serde_json::json!({
        "status": "unavailable",
        "error": format!("Deactivate product {name}: requires a running daemon.")
    }))
}
