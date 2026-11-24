//! HttpControlServer — axum-based HTTP server for SourceRegistry.
//!
//! Rust port of sources-lib `http/control.py`.
//!
//! Routes:
//!   GET  /health                    — liveness
//!   GET  /sources                   — list all sources
//!   POST /sources                   — add source
//!   GET  /sources/{id}/sync         — trigger sync (async)
//!   DELETE /sources/{id}            — remove source

use crate::m2m::M2MServer;
use crate::registry::SourceRegistry;
use axum::{
    extract::{Path, State},
    http::StatusCode,
    response::IntoResponse,
    routing::{delete, get, post},
    Json, Router,
};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::collections::HashMap;
use std::sync::Arc;
use thiserror::Error;
use tokio::net::TcpListener;

#[derive(Debug, Error)]
pub enum ServerError {
    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),
    #[error("server error: {0}")]
    Other(String),
}

// ── Shared state ──────────────────────────────────────────────────────────────

#[derive(Clone)]
struct AppState {
    registry: Arc<SourceRegistry>,
    m2m: Option<Arc<M2MServer>>,
}

// ── Request / response shapes ─────────────────────────────────────────────────

#[derive(Debug, Deserialize)]
struct AddSourceBody {
    kind: String,
    id: Option<String>,
    #[serde(default)]
    config: HashMap<String, Value>,
}

#[derive(Debug, Serialize)]
struct SourceListItem {
    id: String,
    kind: String,
    added_at: f64,
}

// ── Handlers ──────────────────────────────────────────────────────────────────

async fn health() -> impl IntoResponse {
    use std::time::{SystemTime, UNIX_EPOCH};
    let at = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs_f64())
        .unwrap_or(0.0);
    Json(json!({ "ok": true, "at": at }))
}

async fn list_sources(State(state): State<AppState>) -> impl IntoResponse {
    let records = state.registry.list();
    let items: Vec<SourceListItem> = records
        .iter()
        .map(|r| SourceListItem { id: r.id.clone(), kind: r.kind.clone(), added_at: r.added_at })
        .collect();
    Json(json!(items))
}

async fn add_source(
    State(state): State<AppState>,
    Json(body): Json<AddSourceBody>,
) -> impl IntoResponse {
    match state.registry.add(&body.kind, body.id.as_deref(), body.config) {
        Ok(record) => (
            StatusCode::CREATED,
            Json(json!({ "id": record.id, "kind": record.kind })),
        ),
        Err(e) => (
            StatusCode::BAD_REQUEST,
            Json(json!({ "error": e.to_string() })),
        ),
    }
}

async fn sync_source(
    State(state): State<AppState>,
    Path(source_id): Path<String>,
) -> impl IntoResponse {
    match state.registry.get(&source_id) {
        None => (
            StatusCode::NOT_FOUND,
            Json(json!({ "error": format!("source '{}' not found", source_id) })),
        ),
        Some(record) => {
            match state.registry.adapter(&record.kind) {
                Err(e) => (
                    StatusCode::INTERNAL_SERVER_ERROR,
                    Json(json!({ "error": e.to_string() })),
                ),
                Ok(adapter) => {
                    match adapter.sync(&record, &HashMap::new()).await {
                        Ok(rows) => (
                            StatusCode::OK,
                            Json(json!({ "rows": rows, "count": rows.len() })),
                        ),
                        Err(e) => (
                            StatusCode::BAD_REQUEST,
                            Json(json!({ "error": e.to_string() })),
                        ),
                    }
                }
            }
        }
    }
}

async fn remove_source(
    State(state): State<AppState>,
    Path(source_id): Path<String>,
) -> impl IntoResponse {
    state.registry.remove(&source_id);
    Json(json!({ "removed": source_id }))
}

// ── HttpControlServer ─────────────────────────────────────────────────────────

/// HTTP control server wrapping a `SourceRegistry`.
///
/// ```text
/// let reg = Arc::new(SourceRegistry::new());
/// let srv = HttpControlServer::new(Arc::clone(&reg), 8080);
/// srv.serve().await?;
/// ```
pub struct HttpControlServer {
    registry: Arc<SourceRegistry>,
    port: u16,
    m2m: Option<Arc<M2MServer>>,
}

impl HttpControlServer {
    pub fn new(registry: Arc<SourceRegistry>, port: u16) -> Self {
        HttpControlServer { registry, port, m2m: None }
    }

    /// Attach an M2MServer for the `/rpc` passthrough route.
    pub fn with_m2m(mut self, m2m: M2MServer) -> Self {
        self.m2m = Some(Arc::new(m2m));
        self
    }

    /// Build the axum `Router` (useful for testing without binding a port).
    pub fn router(&self) -> Router {
        let state = AppState {
            registry: Arc::clone(&self.registry),
            m2m: self.m2m.clone(),
        };
        Router::new()
            .route("/health", get(health))
            .route("/sources", get(list_sources).post(add_source))
            .route("/sources/:id/sync", get(sync_source))
            .route("/sources/:id", delete(remove_source))
            .with_state(state)
    }

    /// Bind and serve.  Runs until the future is cancelled.
    pub async fn serve(self) -> Result<(), ServerError> {
        let addr = format!("127.0.0.1:{}", self.port);
        let listener = TcpListener::bind(&addr).await?;
        tracing::info!("HttpControlServer listening on {addr}");
        let router = self.router();
        axum::serve(listener, router)
            .await
            .map_err(|e| ServerError::Other(e.to_string()))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::body::Body;
    use axum::http::{Method, Request};
    use crate::adapter::BaseSourceAdapter;
    use tower::ServiceExt;

    fn test_server() -> HttpControlServer {
        let reg = Arc::new(SourceRegistry::new());
        reg.register_kind("base", BaseSourceAdapter).unwrap();
        HttpControlServer::new(reg, 0)
    }

    #[tokio::test]
    async fn health_ok() {
        let srv = test_server();
        let app = srv.router();
        let req = Request::builder().uri("/health").body(Body::empty()).unwrap();
        let resp = app.oneshot(req).await.unwrap();
        assert_eq!(resp.status(), StatusCode::OK);
    }

    #[tokio::test]
    async fn list_sources_empty() {
        let srv = test_server();
        let app = srv.router();
        let req = Request::builder().uri("/sources").body(Body::empty()).unwrap();
        let resp = app.oneshot(req).await.unwrap();
        assert_eq!(resp.status(), StatusCode::OK);
    }

    #[tokio::test]
    async fn add_and_remove_source() {
        let reg = Arc::new(SourceRegistry::new());
        reg.register_kind("base", BaseSourceAdapter).unwrap();
        let srv = HttpControlServer::new(Arc::clone(&reg), 0);
        let app = srv.router();

        // Add
        let body = serde_json::to_vec(&json!({"kind": "base", "id": "s1", "config": {}})).unwrap();
        let req = Request::builder()
            .method(Method::POST)
            .uri("/sources")
            .header("content-type", "application/json")
            .body(Body::from(body))
            .unwrap();
        let resp = app.clone().oneshot(req).await.unwrap();
        assert_eq!(resp.status(), StatusCode::CREATED);

        // Delete
        let req = Request::builder()
            .method(Method::DELETE)
            .uri("/sources/s1")
            .body(Body::empty())
            .unwrap();
        let resp = app.oneshot(req).await.unwrap();
        assert_eq!(resp.status(), StatusCode::OK);

        // Confirm removed
        assert!(reg.get("s1").is_none());
    }
}
