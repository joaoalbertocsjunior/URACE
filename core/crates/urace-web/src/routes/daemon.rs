//! GET  /api/daemon/status — daemon running/stopped + cycle_active flag
//! POST /api/daemon/start  — spawn `urace run` as a detached child
//! POST /api/daemon/stop   — send SIGTERM to the daemon process
//!
//! Ports `routes/daemon.py`. The status handler returns an HTMX partial when
//! the request carries the `HX-Request` header; otherwise returns JSON.

use axum::{
    extract::{Request, State},
    response::{Html, IntoResponse, Response},
    routing::{get, post},
    Json, Router,
};
use minijinja::context;
use crate::{AppState, auth::BearerToken, state_reader};

pub fn router() -> Router<AppState> {
    Router::new()
        .route("/status", get(daemon_status_handler))
        .route("/bar", get(daemon_bar_partial))
        .route("/start", post(daemon_start))
        .route("/stop", post(daemon_stop))
}

async fn daemon_status_handler(
    State(s): State<AppState>,
    _auth: BearerToken,
    req: Request,
) -> Response {
    let is_htmx = req.headers().get("hx-request").is_some();
    let (running, pid) = state_reader::daemon_status(&s.root);
    let cycle_active = if running {
        let state = state_reader::read_state(&s.root);
        state.get("lifecycle_state")
            .and_then(|v| v.as_str()) == Some("ACTIVE")
    } else {
        false
    };

    let status_str = if running { "running" } else { "stopped" };

    if is_htmx {
        render_daemon_bar(&s, status_str, cycle_active)
    } else {
        Json(serde_json::json!({
            "status": status_str,
            "pid": pid,
            "cycle_active": cycle_active,
        })).into_response()
    }
}

async fn daemon_bar_partial(
    State(s): State<AppState>,
    _auth: BearerToken,
) -> Response {
    let (running, _pid) = state_reader::daemon_status(&s.root);
    let cycle_active = if running {
        let state = state_reader::read_state(&s.root);
        state.get("lifecycle_state")
            .and_then(|v| v.as_str()) == Some("ACTIVE")
    } else {
        false
    };
    let status_str = if running { "running" } else { "stopped" };
    render_daemon_bar(&s, status_str, cycle_active)
}

/// Send SIGTERM to a process by PID. Returns a JSON status object.
fn sigterm_process(pid: u32) -> serde_json::Value {
    #[cfg(unix)]
    {
        extern "C" { fn kill(__pid: i32, __sig: i32) -> i32; }
        let rc = unsafe { kill(pid as i32, 15) }; // SIGTERM = 15
        if rc == 0 {
            serde_json::json!({ "status": "stopped" })
        } else {
            serde_json::json!({ "status": "error" })
        }
    }
    #[cfg(not(unix))]
    {
        let _ = pid;
        serde_json::json!({ "status": "error", "error": "SIGTERM not supported on this platform" })
    }
}

fn render_daemon_bar(s: &AppState, status: &str, cycle_active: bool) -> Response {
    let tmpl = match s.env.get_template("daemon_bar.html") {
        Ok(t) => t,
        Err(e) => return Html(format!("<!-- template error: {e} -->")).into_response(),
    };
    let html = tmpl.render(context! {
        status => status,
        cycle_active => cycle_active,
    }).unwrap_or_else(|e| format!("<!-- render error: {e} -->"));
    Html(html).into_response()
}

async fn daemon_start(
    State(_s): State<AppState>,
    _auth: BearerToken,
) -> Json<serde_json::Value> {
    // Spawn `urace run` as a detached process (mirrors Python's Popen with start_new_session=True)
    let result = std::process::Command::new("urace")
        .arg("run")
        .spawn();
    match result {
        Ok(_) => Json(serde_json::json!({ "status": "starting" })),
        Err(e) => Json(serde_json::json!({ "status": "error", "error": e.to_string() })),
    }
}

async fn daemon_stop(
    State(s): State<AppState>,
    _auth: BearerToken,
    req: Request,
) -> Response {
    let is_htmx = req.headers().get("hx-request").is_some();
    let (running, pid) = state_reader::daemon_status(&s.root);

    let payload = if !running || pid.is_none() {
        serde_json::json!({ "status": "not_running" })
    } else {
        let pid = pid.unwrap();
        sigterm_process(pid)
    };

    if is_htmx {
        let bar_status = if payload.get("status").and_then(|v| v.as_str()) == Some("stopped") {
            "stopped"
        } else {
            "stopped"
        };
        render_daemon_bar(&s, bar_status, false)
    } else {
        Json(payload).into_response()
    }
}
