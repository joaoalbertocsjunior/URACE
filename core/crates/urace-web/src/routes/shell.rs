//! POST /api/shell/run — SSE streaming shell command execution.
//!
//! Ports `routes/shell.py`. Accepts `{"input": "..."}` and returns a
//! Server-Sent Events stream. In the Rust port, daemon RPC is not yet wired;
//! we return an SSE stream with a single informational message.
//!
//! When the daemon RPC socket is available in a future Rust daemon, this
//! handler can be enhanced to stream real output.

use crate::{auth::BearerToken, AppState};
use axum::{
    extract::State,
    response::sse::{Event, KeepAlive, Sse},
    response::{IntoResponse, Response},
    routing::post,
    Json, Router,
};
use futures::stream;
use serde::Deserialize;

pub fn router() -> Router<AppState> {
    Router::new().route("/run", post(shell_run))
}

#[derive(Deserialize)]
pub struct ShellInput {
    pub input: String,
}

async fn shell_run(
    State(_s): State<AppState>,
    _auth: BearerToken,
    Json(body): Json<ShellInput>,
) -> Response {
    let input = body.input.trim().to_string();
    // Daemon RPC not yet implemented in Rust web layer.
    // Return an informational SSE message then [DONE].
    let lines = vec![
        format!("urace-web: shell run is not yet connected to the Rust daemon."),
        format!("Command received: {input}"),
        format!("Use `urace` CLI directly for now."),
    ];

    let events: Vec<Result<Event, std::convert::Infallible>> = lines
        .into_iter()
        .map(|l| Ok(Event::default().data(l)))
        .chain(std::iter::once(Ok(Event::default().data("[DONE]"))))
        .collect();

    Sse::new(stream::iter(events))
        .keep_alive(KeepAlive::default())
        .into_response()
}
