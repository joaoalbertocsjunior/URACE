#![allow(dead_code)]

use std::collections::HashMap;
use std::net::SocketAddr;
use std::sync::Arc;

use axum::{
    extract::State,
    http::StatusCode,
    response::IntoResponse,
    routing::post,
    Json, Router,
};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use tokio::sync::Mutex;

pub type Handler = Box<dyn Fn(Value) -> Value + Send + Sync>;

/// A minimal JSON-RPC-style server built on axum.
///
/// Accepts `POST /rpc` with body `{"method": "...", "params": {...}}`.
/// Dispatches to a registered handler; returns `{"result": ...}` or
/// `{"error": "method not found"}`.
pub struct M2MServer {
    handlers: Arc<Mutex<HashMap<String, Handler>>>,
    bind_addr: SocketAddr,
}

#[derive(Deserialize)]
struct RpcRequest {
    method: String,
    #[serde(default)]
    params: Value,
}

#[derive(Serialize)]
#[serde(untagged)]
enum RpcResponse {
    Ok { result: Value },
    Err { error: String },
}

#[derive(Clone)]
struct M2MState {
    handlers: Arc<Mutex<HashMap<String, Handler>>>,
}

impl M2MServer {
    pub fn new(bind_addr: SocketAddr) -> Self {
        Self {
            handlers: Arc::new(Mutex::new(HashMap::new())),
            bind_addr,
        }
    }

    /// Register a handler for a named method.
    pub async fn register<F>(&self, method: impl Into<String>, handler: F)
    where
        F: Fn(Value) -> Value + Send + Sync + 'static,
    {
        let mut map = self.handlers.lock().await;
        map.insert(method.into(), Box::new(handler));
    }

    /// Build the axum router.
    pub fn router(&self) -> Router {
        let state = M2MState {
            handlers: Arc::clone(&self.handlers),
        };
        Router::new().route("/rpc", post(rpc_handler)).with_state(state)
    }

    /// Bind and serve.
    pub async fn serve(self) -> Result<(), std::io::Error> {
        let addr = self.bind_addr;
        let router = self.router();
        let listener = tokio::net::TcpListener::bind(addr).await?;
        tracing::info!("M2MServer listening on {addr}");
        axum::serve(listener, router).await
    }
}

async fn rpc_handler(
    State(state): State<M2MState>,
    Json(req): Json<RpcRequest>,
) -> impl IntoResponse {
    let handlers = state.handlers.lock().await;
    if let Some(handler) = handlers.get(&req.method) {
        let result = handler(req.params);
        (StatusCode::OK, Json(RpcResponse::Ok { result }))
    } else {
        (
            StatusCode::NOT_FOUND,
            Json(RpcResponse::Err {
                error: format!("method not found: {}", req.method),
            }),
        )
    }
}
