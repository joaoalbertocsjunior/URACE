//! GET /api/exchange/peers  — P2P peer list from state.json
//! GET /api/exchange/assets — asset search from state.json
//! GET /api/exchange/search — search endpoint (stub / state read)
//!
//! Ports `routes/exchange.py`.

use crate::{auth::BearerToken, state_reader, AppState};
use axum::{
    extract::{Query, State},
    routing::get,
    Json, Router,
};
use serde::Deserialize;

pub fn router() -> Router<AppState> {
    Router::new()
        .route("/peers", get(exchange_peers))
        .route("/assets", get(exchange_assets))
        .route("/search", get(exchange_search))
}

async fn exchange_peers(State(s): State<AppState>, _auth: BearerToken) -> Json<serde_json::Value> {
    let state = state_reader::read_state(&s.root);
    let peers = state
        .get("peers")
        .cloned()
        .unwrap_or_else(|| serde_json::json!({ "peer_count": 0, "anonymized_peer_ids": [] }));
    Json(peers)
}

#[derive(Deserialize)]
pub struct AssetsQuery {
    pub query: Option<String>,
}

async fn exchange_assets(
    State(s): State<AppState>,
    _auth: BearerToken,
    Query(q): Query<AssetsQuery>,
) -> Json<serde_json::Value> {
    let state = state_reader::read_state(&s.root);
    let mut assets = state
        .get("open_assets")
        .and_then(|v| v.as_array())
        .cloned()
        .unwrap_or_default();

    if let Some(query) = &q.query {
        let ql = query.to_lowercase();
        assets.retain(|a| {
            let desc = a
                .get("description")
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .to_lowercase();
            let feat = a
                .get("feature_id")
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .to_lowercase();
            desc.contains(&ql) || feat.contains(&ql)
        });
    }

    Json(serde_json::json!({
        "open_assets": assets,
        "paid_listings": [],
    }))
}

#[derive(Deserialize)]
pub struct SearchQuery {
    pub q: Option<String>,
    #[serde(default = "default_kind")]
    pub kind: String,
}
fn default_kind() -> String {
    "all".to_string()
}

async fn exchange_search(
    State(s): State<AppState>,
    _auth: BearerToken,
    Query(q): Query<SearchQuery>,
) -> Json<serde_json::Value> {
    let state = state_reader::read_state(&s.root);
    let mut assets = state
        .get("open_assets")
        .and_then(|v| v.as_array())
        .cloned()
        .unwrap_or_default();

    if let Some(query) = &q.q {
        let ql = query.to_lowercase();
        assets.retain(|a| {
            let desc = a
                .get("description")
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .to_lowercase();
            desc.contains(&ql)
        });
    }

    if q.kind != "all" {
        assets.retain(|a| a.get("kind").and_then(|v| v.as_str()) == Some(&q.kind));
    }

    Json(serde_json::json!({ "results": assets }))
}
