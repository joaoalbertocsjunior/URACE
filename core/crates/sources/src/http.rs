#![allow(dead_code)]

use std::net::SocketAddr;
use std::sync::Arc;

use axum::{
    extract::{Path, State},
    http::StatusCode,
    response::IntoResponse,
    routing::{get, post},
    Json, Router,
};
use serde_json::json;

use crate::registry::SourceRegistry;

/// Shared state for the HTTP control server.
#[derive(Clone)]
struct AppState {
    registry: Arc<SourceRegistry>,
}

/// Axum-based HTTP control server.
///
/// Routes:
/// - `GET  /health`           — 200 OK
/// - `GET  /sources`          — list registered source IDs
/// - `POST /sources/sync/:id` — trigger a sync for a specific adapter (stub)
pub struct HttpControlServer {
    registry: Arc<SourceRegistry>,
    bind_addr: SocketAddr,
}

impl HttpControlServer {
    pub fn new(registry: Arc<SourceRegistry>, bind_addr: SocketAddr) -> Self {
        Self { registry, bind_addr }
    }

    /// Build the axum `Router` (useful for testing without binding a port).
    pub fn router(&self) -> Router {
        let state = AppState {
            registry: Arc::clone(&self.registry),
        };
        Router::new()
            .route("/health", get(health))
            .route("/sources", get(list_sources))
            .route("/sources/sync/:id", post(sync_source))
            .with_state(state)
    }

    /// Bind and serve.
    pub async fn serve(self) -> Result<(), std::io::Error> {
        let addr = self.bind_addr;
        let router = self.router();
        let listener = tokio::net::TcpListener::bind(addr).await?;
        tracing::info!("HttpControlServer listening on {addr}");
        axum::serve(listener, router).await
    }
}

// --- handlers ---

async fn health() -> impl IntoResponse {
    (StatusCode::OK, Json(json!({"status": "ok"})))
}

async fn list_sources(State(state): State<AppState>) -> impl IntoResponse {
    let ids = state.registry.list();
    Json(json!({ "sources": ids }))
}

async fn sync_source(
    State(state): State<AppState>,
    Path(id): Path<String>,
) -> impl IntoResponse {
    // Stub: in a full implementation this would call registry.sync_one(&id).
    let ids = state.registry.list();
    if ids.contains(&id) {
        (StatusCode::OK, Json(json!({ "id": id, "status": "sync_triggered" })))
    } else {
        (StatusCode::NOT_FOUND, Json(json!({ "error": "source not found", "id": id })))
    }
}
