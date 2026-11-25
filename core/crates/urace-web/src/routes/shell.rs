use crate::{auth::BearerToken, AppState};
use axum::{
    extract::State,
    response::{
        sse::{Event, KeepAlive, Sse},
        IntoResponse, Response,
    },
    routing::post,
    Json, Router,
};
use futures::stream;
use serde::Deserialize;
use std::convert::Infallible;
use tokio::io::AsyncBufReadExt as _;
use tokio::sync::mpsc;

pub fn router() -> Router<AppState> {
    Router::new().route("/run", post(shell_run))
}

#[derive(Deserialize)]
pub struct ShellInput {
    pub input: String,
}

async fn shell_run(
    State(s): State<AppState>,
    _auth: BearerToken,
    Json(body): Json<ShellInput>,
) -> Response {
    let input = body.input.trim().to_string();

    if input.is_empty() {
        return done_sse(vec![]);
    }

    if let Some(rest) = input.strip_prefix('!') {
        run_os_command(rest.trim()).await
    } else if let Some(rest) = input.strip_prefix('/') {
        run_urace_command(rest.trim(), &s).await
    } else {
        done_sse(vec![
            "Commands must start with '/' (URACE) or '!' (OS shell).".into(),
            format!("  Try: /{input}  or  ! {input}"),
            "  Run /help to see all commands.".into(),
        ])
    }
}

// ── URACE command ─────────────────────────────────────────────────────────────

async fn run_urace_command(input: &str, s: &AppState) -> Response {
    if input.eq_ignore_ascii_case("help") || input.is_empty() {
        return done_sse(urace_help());
    }

    let exe = match std::env::current_exe() {
        Ok(p) => p,
        Err(e) => return done_sse(vec![format!("error: could not resolve binary: {e}")]),
    };

    let args = split_args(input);
    if args.is_empty() {
        return done_sse(urace_help());
    }

    let mut cmd = tokio::process::Command::new(&exe);
    cmd.arg("--root").arg(s.root.as_os_str());
    cmd.args(&args);
    cmd.stdout(std::process::Stdio::piped());
    cmd.stderr(std::process::Stdio::piped());

    spawn_streamed(cmd).await
}

// ── OS shell passthrough ──────────────────────────────────────────────────────

async fn run_os_command(input: &str) -> Response {
    if input.is_empty() {
        return done_sse(vec!["usage: ! <os command>".into()]);
    }

    let mut cmd = if cfg!(windows) {
        let mut c = tokio::process::Command::new("cmd");
        c.args(["/C", input]);
        c
    } else {
        let mut c = tokio::process::Command::new("sh");
        c.args(["-c", input]);
        c
    };
    cmd.stdout(std::process::Stdio::piped());
    cmd.stderr(std::process::Stdio::piped());

    spawn_streamed(cmd).await
}

// ── Process streaming ─────────────────────────────────────────────────────────

async fn spawn_streamed(mut cmd: tokio::process::Command) -> Response {
    let mut child = match cmd.spawn() {
        Ok(c) => c,
        Err(e) => return done_sse(vec![format!("error: {e}")]),
    };

    let (tx, rx) = mpsc::channel::<String>(256);

    let stdout = child.stdout.take().map(tokio::io::BufReader::new);
    let stderr = child.stderr.take().map(tokio::io::BufReader::new);

    let tx_out = tx.clone();
    tokio::spawn(async move {
        if let Some(reader) = stdout {
            let mut lines = reader.lines();
            while let Ok(Some(line)) = lines.next_line().await {
                if tx_out.send(line).await.is_err() {
                    break;
                }
            }
        }
    });

    let tx_err = tx.clone();
    tokio::spawn(async move {
        if let Some(reader) = stderr {
            let mut lines = reader.lines();
            while let Ok(Some(line)) = lines.next_line().await {
                if tx_err.send(format!("\x1b[31m{line}\x1b[0m")).await.is_err() {
                    break;
                }
            }
        }
    });

    // Wait for child exit, then send [DONE].
    // Drop original tx so only the two tasks hold references; when both
    // finish their senders drop, then the done-task sends [DONE] and drops.
    drop(tx);
    tokio::spawn(async move {
        // give the reader tasks a moment to drain before signalling done
        let _ = child.wait().await;
    });

    // The rx will produce lines until all senders drop. We need to inject
    // [DONE] after the last real line. Use a wrapper stream.
    let s = futures::stream::unfold(
        (rx, false),
        |(mut rx, done)| async move {
            if done {
                return None;
            }
            match rx.recv().await {
                Some(line) => {
                    let ev = Ok::<Event, Infallible>(Event::default().data(line));
                    Some((ev, (rx, false)))
                }
                None => {
                    // channel closed → process finished
                    let ev = Ok::<Event, Infallible>(Event::default().data("[DONE]"));
                    Some((ev, (rx, true)))
                }
            }
        },
    );

    Sse::new(s).keep_alive(KeepAlive::default()).into_response()
}

// ── Helpers ───────────────────────────────────────────────────────────────────

fn done_sse(lines: Vec<String>) -> Response {
    let mut events: Vec<Result<Event, Infallible>> = lines
        .into_iter()
        .map(|l| Ok(Event::default().data(l)))
        .collect();
    events.push(Ok(Event::default().data("[DONE]")));
    Sse::new(stream::iter(events))
        .keep_alive(KeepAlive::default())
        .into_response()
}

/// Minimal shell-word split: handles single/double quotes, no escapes.
fn split_args(s: &str) -> Vec<String> {
    let mut args: Vec<String> = Vec::new();
    let mut cur = String::new();
    let mut quote: Option<char> = None;

    for c in s.chars() {
        match (c, quote) {
            ('"' | '\'', None) => quote = Some(c),
            (q, Some(iq)) if q == iq => quote = None,
            (' ' | '\t', None) => {
                if !cur.is_empty() {
                    args.push(cur.clone());
                    cur.clear();
                }
            }
            _ => cur.push(c),
        }
    }
    if !cur.is_empty() {
        args.push(cur);
    }
    args
}

fn urace_help() -> Vec<String> {
    vec![
        "URACE Shell — prefix commands with '/', OS commands with '!'".into(),
        "".into(),
        "META".into(),
        "  /help                           this message".into(),
        "  /version [-j]                   version info".into(),
        "  /status [-v] [-j]               runtime status".into(),
        "".into(),
        "DAEMON".into(),
        "  /run [--max-cycles N]            start the daemon loop".into(),
        "".into(),
        "CONFIG".into(),
        "  /config show|get|set|validate|path".into(),
        "".into(),
        "SOURCE".into(),
        "  /source list|add|remove|sync".into(),
        "".into(),
        "WORK".into(),
        "  /work list|bid|assign".into(),
        "".into(),
        "EVIDENCE / BLOCKER / DECISION / MILESTONE".into(),
        "  /evidence list|show".into(),
        "  /blocker list|resolve".into(),
        "  /decision list|show".into(),
        "  /milestone list|show|add".into(),
        "".into(),
        "GOVERNANCE".into(),
        "  /compliance list|domain|history".into(),
        "  /rules list|show|graph|conflicts".into(),
        "  /inbox list|apply|reject|count".into(),
        "".into(),
        "METRICS".into(),
        "  /vitals".into(),
        "  /audit [decisions|evidence] [--since TS] [--limit N]".into(),
        "  /goals list|add|pin|unpin|defer|cancel".into(),
        "  /trace [--kind CYCLE|OPERATION|DECISION] [--limit N]".into(),
        "".into(),
        "DATA".into(),
        "  /data list|show|status|source|credential".into(),
        "".into(),
        "REPORTING".into(),
        "  /usage summary|patterns".into(),
        "  /report vitals|cycle|audit".into(),
        "".into(),
        "EXCHANGE".into(),
        "  /exchange status|list|show|rank|reputation|ledger|settle".into(),
        "  /exchange asset list|show".into(),
        "  /exchange ask|fill|cancel|momentum|discover".into(),
        "  /exchange peers list|connect".into(),
        "".into(),
        "GITHUB".into(),
        "  /github status|connect|push-goals|trigger-workflow".into(),
        "".into(),
        "WORK QUALITY".into(),
        "  /plan|check|quality|context|classify|derive|propose".into(),
        "".into(),
        "RUNTIME".into(),
        "  /trial status|run".into(),
        "  /update check|apply|rollback".into(),
        "  /features list|toggle".into(),
        "  /crc".into(),
        "".into(),
        "PRODUCT".into(),
        "  /product list|show|create|activate|switch|register|status".into(),
        "  /content list|show|add".into(),
        "  /rollback [--to SNAPSHOT]".into(),
        "  /peer-review list|submit".into(),
        "".into(),
        "GLOBAL FLAGS  --json/-j  --root DIR  --config FILE".into(),
        "".into(),
        "OS SHELL PASSTHROUGH".into(),
        "  ! ls -la                         run any OS command".into(),
        "  ! git log --oneline -5           works on all platforms".into(),
        "[DONE]".into(),
    ]
}
