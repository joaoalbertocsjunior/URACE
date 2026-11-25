//! Work subcommand handlers for the `urace` CLI.
//!
//! Covers: github, plan, check, quality, context, classify, derive, propose.
//!
//! All read operations work fully against `<root>/state/state.json` or
//! `<root>/state.json`.  Write/mutation operations that require a running
//! daemon print an informative stub message instead.

use anyhow::Result;
use serde_json::Value;
use std::path::Path;

use crate::cli_governance::load_state_json;

// ── github ────────────────────────────────────────────────────────────────────

#[derive(Debug, clap::Args)]
#[command(about = "GitHub integration (status / connect / push-goals / trigger-workflow)")]
pub struct GithubArgs {
    /// Action: status | connect | push-goals | trigger-workflow
    #[arg(default_value = "status")]
    pub action: String,

    /// Repository in owner/repo format (for connect / push-goals / trigger-workflow)
    #[arg(long)]
    pub repo: Option<String>,

    /// Workflow file name or ID (for trigger-workflow)
    #[arg(long)]
    pub workflow: Option<String>,

    /// Git ref to trigger on (for trigger-workflow, default: main)
    #[arg(long, default_value = "main")]
    pub ref_name: String,

    /// Workflow inputs as JSON object (for trigger-workflow)
    #[arg(long)]
    pub inputs: Option<String>,

    /// Dry-run (for push-goals)
    #[arg(long)]
    pub dry_run: bool,

    /// Token env var name (default: URACE_GITHUB_TOKEN)
    #[arg(long, default_value = "URACE_GITHUB_TOKEN")]
    pub token_env: String,
}

pub async fn handle_github(root: &Path, args: &GithubArgs, json_mode: bool) -> Result<()> {
    let state = load_state_json(root)?;
    let config = load_config_json(root);

    match args.action.as_str() {
        "status" => {
            let token = std::env::var(&args.token_env).unwrap_or_default();
            let repo = args
                .repo
                .as_deref()
                .or_else(|| {
                    config
                        .get("github")
                        .and_then(|g| g.get("repo"))
                        .and_then(|v| v.as_str())
                })
                .unwrap_or("")
                .to_string();
            let token_set = !token.is_empty();
            if json_mode {
                println!(
                    "{}",
                    serde_json::json!({
                        "github_token_set": token_set,
                        "repo": if repo.is_empty() { Value::Null } else { Value::String(repo.clone()) },
                        "hint": if !token_set { "Set URACE_GITHUB_TOKEN env var to connect" }
                                else if repo.is_empty() { "Run: urace github connect owner/repo" }
                                else { "" }
                    })
                );
            } else {
                println!(
                    "GitHub: {}",
                    if token_set && !repo.is_empty() {
                        "configured"
                    } else {
                        "not connected"
                    }
                );
                if !repo.is_empty() {
                    println!("  repo: {repo}");
                }
                if !token_set {
                    println!("  hint: Set URACE_GITHUB_TOKEN env var to connect");
                } else if repo.is_empty() {
                    println!("  hint: Run: urace github connect owner/repo");
                }
            }
        }

        "connect" => {
            let repo = args.repo.as_deref().unwrap_or("");
            if repo.is_empty() || repo.matches('/').count() != 1 {
                if json_mode {
                    println!(
                        "{}",
                        serde_json::json!({"status": "error", "error": "repo must be in owner/repo format"})
                    );
                } else {
                    eprintln!("error: --repo must be in owner/repo format");
                }
                return Ok(());
            }
            eprintln!("not yet wired: github connect requires a running daemon to persist config");
            if json_mode {
                println!(
                    "{}",
                    serde_json::json!({
                        "status": "stub",
                        "repo": repo,
                        "token_env": args.token_env,
                        "note": "operation not yet wired to live daemon"
                    })
                );
            } else {
                println!(
                    "github connect {repo}: operation not yet wired to live daemon (token via ${})",
                    args.token_env
                );
            }
        }

        "push-goals" => {
            let empty = vec![];
            let objectives: Vec<&Value> = state
                .get("objectives")
                .and_then(|v| v.as_array())
                .unwrap_or(&empty)
                .iter()
                .filter(|o| o.get("status").and_then(|s| s.as_str()) != Some("DONE"))
                .take(20)
                .collect();
            if json_mode {
                println!(
                    "{}",
                    serde_json::json!({
                        "status": if args.dry_run { "DRY_RUN" } else { "stub" },
                        "dry_run": args.dry_run,
                        "objectives_found": objectives.len(),
                        "note": "GitHub API push not yet wired; objectives listed below",
                        "objectives": objectives.iter().map(|o| {
                            serde_json::json!({
                                "id": o.get("id"),
                                "text": o.get("text").or_else(|| o.get("title")),
                                "status": o.get("status"),
                            })
                        }).collect::<Vec<_>>()
                    })
                );
            } else {
                let dry_tag = if args.dry_run { " (dry-run)" } else { "" };
                println!(
                    "push-goals{dry_tag}: {} open objectives found",
                    objectives.len()
                );
                for o in &objectives {
                    let id = o.get("id").and_then(|v| v.as_str()).unwrap_or("?");
                    let text = o
                        .get("text")
                        .or_else(|| o.get("title"))
                        .and_then(|v| v.as_str())
                        .unwrap_or("(untitled)");
                    let short: String = text.chars().take(72).collect();
                    println!("  {id}: {short}");
                }
                if !args.dry_run {
                    println!("note: GitHub API push not yet wired to live daemon");
                }
            }
        }

        "trigger-workflow" => {
            let wf = args.workflow.as_deref().unwrap_or("");
            if wf.is_empty() {
                if json_mode {
                    println!(
                        "{}",
                        serde_json::json!({"status": "error", "error": "--workflow is required"})
                    );
                } else {
                    eprintln!("error: --workflow is required for trigger-workflow");
                }
                return Ok(());
            }
            eprintln!("not yet wired: trigger-workflow requires GitHub API access");
            if json_mode {
                println!(
                    "{}",
                    serde_json::json!({
                        "status": "stub",
                        "workflow": wf,
                        "ref": args.ref_name,
                        "note": "operation not yet wired to live daemon"
                    })
                );
            } else {
                println!(
                    "trigger-workflow {wf} on {}: operation not yet wired to live daemon",
                    args.ref_name
                );
            }
        }

        other => {
            if json_mode {
                println!(
                    "{}",
                    serde_json::json!({"error": format!("unknown github action: {other}")})
                );
            } else {
                eprintln!("unknown github action: {other}");
            }
        }
    }
    Ok(())
}

// ── plan ──────────────────────────────────────────────────────────────────────

#[derive(Debug, clap::Args)]
#[command(about = "Show planned objectives from state")]
pub struct PlanArgs {
    /// Filter by scope
    #[arg(long)]
    pub scope: Option<String>,

    /// Maximum objectives to show
    #[arg(long, default_value = "20")]
    pub limit: usize,
}

pub async fn handle_plan(root: &Path, args: &PlanArgs, json_mode: bool) -> Result<()> {
    let state = load_state_json(root)?;
    let empty = vec![];

    let all: &Vec<Value> = state
        .get("objectives")
        .and_then(|v| v.as_array())
        .unwrap_or(&empty);

    let mut planned: Vec<&Value> = all
        .iter()
        .filter(|o| {
            let status = o.get("status").and_then(|v| v.as_str()).unwrap_or("");
            matches!(status, "PLANNED" | "PENDING" | "QUEUED" | "")
        })
        .collect();

    if let Some(scope) = &args.scope {
        planned.retain(|o| o.get("scope").and_then(|v| v.as_str()) == Some(scope.as_str()));
    }

    planned.truncate(args.limit);

    if json_mode {
        println!("{}", serde_json::to_string_pretty(&planned)?);
    } else if planned.is_empty() {
        println!("No planned objectives.");
    } else {
        println!("{:<36} {:<12} text", "id", "status");
        println!("{}", "-".repeat(80));
        for o in planned {
            let id = o.get("id").and_then(|v| v.as_str()).unwrap_or("?");
            let status = o
                .get("status")
                .and_then(|v| v.as_str())
                .unwrap_or("PENDING");
            let text = o
                .get("text")
                .or_else(|| o.get("title"))
                .and_then(|v| v.as_str())
                .unwrap_or("(untitled)");
            let short: String = text.chars().take(60).collect();
            println!("{id:<36} {status:<12} {short}");
        }
    }
    Ok(())
}

// ── check ─────────────────────────────────────────────────────────────────────

#[derive(Debug, clap::Args)]
#[command(about = "Validation / integrity check on current state")]
pub struct CheckArgs {
    /// Show only blocker-level issues
    #[arg(long)]
    pub blockers_only: bool,
}

pub async fn handle_check(root: &Path, args: &CheckArgs, json_mode: bool) -> Result<()> {
    let state = load_state_json(root)?;
    let empty = vec![];

    let lifecycle = state
        .get("lifecycle_state")
        .and_then(|v| v.as_str())
        .unwrap_or("UNKNOWN");

    let blockers: Vec<&Value> = state
        .get("blockers")
        .and_then(|v| v.as_array())
        .unwrap_or(&empty)
        .iter()
        .filter(|b| b.get("resolved_at").map(|v| v.is_null()).unwrap_or(true))
        .collect();

    let gaps: Vec<&Value> = state
        .get("gaps")
        .and_then(|v| v.as_array())
        .unwrap_or(&empty)
        .iter()
        .filter(|g| {
            if args.blockers_only {
                g.get("classification").and_then(|v| v.as_str()) == Some("BLOCKING")
            } else {
                true
            }
        })
        .collect();

    let onboard_records: &Vec<Value> = state
        .get("onboard_records")
        .and_then(|v| v.as_array())
        .unwrap_or(&empty);
    let onboarded = onboard_records
        .iter()
        .any(|r| r.get("superseded_at").map(|v| v.is_null()).unwrap_or(true));

    let check = serde_json::json!({
        "lifecycle_state": lifecycle,
        "onboarded": onboarded,
        "active_blockers": blockers.len(),
        "gaps": gaps.len(),
        "status": if blockers.is_empty() && gaps.is_empty() { "OK" } else { "ISSUES_FOUND" }
    });

    if json_mode {
        println!("{}", serde_json::to_string_pretty(&check)?);
    } else {
        let status = check["status"].as_str().unwrap_or("?");
        println!("check: {status}");
        println!("  lifecycle:  {lifecycle}");
        println!("  onboarded:  {onboarded}");
        println!("  blockers:   {}", blockers.len());
        println!("  gaps:       {}", gaps.len());
        for b in &blockers {
            let id = b.get("id").and_then(|v| v.as_str()).unwrap_or("?");
            let scope = b.get("scope").and_then(|v| v.as_str()).unwrap_or("?");
            println!("    BLOCKER {id}: scope={scope}");
        }
    }
    Ok(())
}

// ── quality ───────────────────────────────────────────────────────────────────

#[derive(Debug, clap::Args)]
#[command(about = "Quality metrics from state")]
pub struct QualityArgs {
    /// Show full history
    #[arg(long)]
    pub history: bool,

    /// Maximum entries
    #[arg(long, default_value = "20")]
    pub limit: usize,
}

pub async fn handle_quality(root: &Path, args: &QualityArgs, json_mode: bool) -> Result<()> {
    let state = load_state_json(root)?;
    let empty = vec![];

    let quality = state.get("quality").cloned().unwrap_or_default();
    let snapshots: Vec<&Value> = state
        .get("quality_snapshots")
        .and_then(|v| v.as_array())
        .unwrap_or(&empty)
        .iter()
        .rev()
        .take(args.limit)
        .collect();

    if args.history {
        if json_mode {
            println!("{}", serde_json::to_string_pretty(&snapshots)?);
        } else if snapshots.is_empty() {
            println!("No quality snapshots.");
        } else {
            for s in snapshots {
                let at = s.get("at").and_then(|v| v.as_str()).unwrap_or("?");
                let score = s.get("score").and_then(|v| v.as_f64()).unwrap_or(0.0);
                let delta = s.get("delta").and_then(|v| v.as_f64()).unwrap_or(0.0);
                let sign = if delta >= 0.0 { "+" } else { "" };
                println!("{at}  score={score:.4}  delta={sign}{delta:.4}");
            }
        }
        return Ok(());
    }

    if json_mode {
        println!("{}", serde_json::to_string_pretty(&quality)?);
    } else if quality.is_null() {
        println!("No quality data in state.");
    } else {
        for (k, v) in quality.as_object().into_iter().flatten() {
            println!("  {k}: {v}");
        }
    }
    Ok(())
}

// ── context ───────────────────────────────────────────────────────────────────

#[derive(Debug, clap::Args)]
#[command(about = "Context view from state (governing intent, constraints, user-supplied)")]
pub struct ContextArgs {
    /// Sub-action: view | graph | attention
    #[arg(default_value = "view")]
    pub action: String,

    /// Node ID for graph traversal
    #[arg(long)]
    pub node_id: Option<String>,

    /// Maximum entries
    #[arg(long, default_value = "20")]
    pub limit: usize,
}

pub async fn handle_context(root: &Path, args: &ContextArgs, json_mode: bool) -> Result<()> {
    let state = load_state_json(root)?;
    let empty = vec![];

    match args.action.as_str() {
        "graph" | "attention" => {
            // Build a minimal graph representation from state relations.
            let nodes: serde_json::Map<String, Value> = {
                let mut m = serde_json::Map::new();
                for key in &["objectives", "evidence", "decisions", "blockers"] {
                    if let Some(arr) = state.get(*key).and_then(|v| v.as_array()) {
                        for item in arr.iter().take(args.limit) {
                            if let Some(id) = item.get("id").and_then(|v| v.as_str()) {
                                m.insert(
                                    id.to_string(),
                                    serde_json::json!({"kind": *key, "id": id}),
                                );
                            }
                        }
                    }
                }
                m
            };
            let view = serde_json::json!({
                "action": args.action,
                "nodes_total": nodes.len(),
                "nodes": nodes,
                "note": "full graph traversal requires running daemon"
            });
            println!("{}", serde_json::to_string_pretty(&view)?);
        }
        _ => {
            // Standard context view.
            let intent = state
                .get("intent")
                .or_else(|| state.get("governing"))
                .cloned()
                .unwrap_or_default();
            let constraints: &Vec<Value> = state
                .get("hard_constraints")
                .and_then(|v| v.as_array())
                .unwrap_or(&empty);
            let user_supplied: Vec<&Value> = state
                .get("context_records")
                .or_else(|| state.get("context"))
                .and_then(|v| v.as_array())
                .unwrap_or(&empty)
                .iter()
                .filter(|c| c.get("origin").and_then(|v| v.as_str()) == Some("user"))
                .take(args.limit)
                .collect();
            let objectives: &Vec<Value> = state
                .get("objectives")
                .and_then(|v| v.as_array())
                .unwrap_or(&empty);

            let view = serde_json::json!({
                "governing": {
                    "intent": intent,
                    "constraints": constraints,
                },
                "user_supplied": user_supplied,
                "urace_derived": {
                    "objectives": objectives.len(),
                    "reasoning_hypotheses": state.get("hypotheses")
                        .and_then(|v| v.as_array()).map(|a| a.len()).unwrap_or(0),
                    "external_observations": state.get("external_observations")
                        .and_then(|v| v.as_array()).map(|a| a.len()).unwrap_or(0),
                }
            });

            if json_mode {
                println!("{}", serde_json::to_string_pretty(&view)?);
            } else {
                let purpose = intent
                    .get("purpose")
                    .and_then(|v| v.as_str())
                    .unwrap_or("(not set)");
                println!("Intent: {purpose}");
                println!("Constraints: {}", constraints.len());
                println!("User-supplied context: {}", user_supplied.len());
                for item in &user_supplied {
                    let id = item.get("id").and_then(|v| v.as_str()).unwrap_or("?");
                    let text = item
                        .get("text")
                        .and_then(|v| v.as_str())
                        .unwrap_or("")
                        .chars()
                        .take(60)
                        .collect::<String>();
                    println!("  {id}: {text}");
                }
                let derived = &view["urace_derived"];
                println!(
                    "URACE-derived: objectives={} hypotheses={} external-observations={}",
                    derived["objectives"],
                    derived["reasoning_hypotheses"],
                    derived["external_observations"]
                );
            }
        }
    }
    Ok(())
}

// ── classify ──────────────────────────────────────────────────────────────────

#[derive(Debug, clap::Args)]
#[command(about = "Classify text against patterns/scope in current state")]
pub struct ClassifyArgs {
    /// Text to classify
    pub text: String,

    /// Scope filter
    #[arg(long)]
    pub scope: Option<String>,
}

pub async fn handle_classify(root: &Path, args: &ClassifyArgs, json_mode: bool) -> Result<()> {
    let state = load_state_json(root)?;
    let config = load_config_json(root);
    let empty = vec![];

    let text_lower = args.text.to_lowercase();

    // Simple keyword matching against objectives and patterns from state.
    let objectives: Vec<serde_json::Value> = state
        .get("objectives")
        .and_then(|v| v.as_array())
        .unwrap_or(&empty)
        .iter()
        .filter(|o| {
            let txt = o
                .get("text")
                .or_else(|| o.get("title"))
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .to_lowercase();
            txt.contains(&text_lower)
                || text_lower
                    .split_whitespace()
                    .any(|w| w.len() > 3 && txt.contains(w))
        })
        .map(|o| {
            serde_json::json!({
                "kind": "objective",
                "id": o.get("id"),
                "text": o.get("text").or_else(|| o.get("title")),
                "status": o.get("status"),
                "score": 0.8
            })
        })
        .take(10)
        .collect();

    // Check active scope from config.
    let active_scope = config
        .get("active_scope")
        .and_then(|v| v.as_str())
        .unwrap_or("default")
        .to_string();

    let result = serde_json::json!({
        "text": args.text,
        "scope": args.scope.as_deref().unwrap_or(&active_scope),
        "matches": objectives,
        "note": "full classification requires running daemon with AI executor"
    });

    if json_mode {
        println!("{}", serde_json::to_string_pretty(&result)?);
    } else {
        let scope_str = args.scope.as_deref().unwrap_or(&active_scope);
        println!("classify: scope={scope_str}  matches={}", objectives.len());
        for m in objectives.iter() {
            let id = m["id"].as_str().unwrap_or("?");
            let text = m["text"].as_str().unwrap_or("?");
            let short: String = text.chars().take(60).collect();
            println!("  {id}: {short}");
        }
        if objectives.is_empty() {
            println!("  (no matches found — full classify requires AI executor)");
        }
    }
    Ok(())
}

// ── derive ────────────────────────────────────────────────────────────────────

#[derive(Debug, clap::Args)]
#[command(about = "Suggest patterns/constructs from intent or state")]
pub struct DeriveArgs {
    /// Intent text to derive constructs from
    #[arg(long)]
    pub intent: Option<String>,

    /// Comma-separated construct IDs to include
    #[arg(long)]
    pub constructs: Option<String>,

    /// Construct kind filter (pattern / mechanism / schema / all)
    #[arg(long, default_value = "all")]
    pub kind: String,

    /// Maximum suggestions
    #[arg(long, default_value = "8")]
    pub limit: usize,
}

pub async fn handle_derive(root: &Path, args: &DeriveArgs, json_mode: bool) -> Result<()> {
    let state = load_state_json(root)?;
    let empty = vec![];

    let intent = args.intent.as_deref().unwrap_or("").to_lowercase();

    // Derive suggestions from objectives in state as a simple heuristic.
    let objectives: &Vec<Value> = state
        .get("objectives")
        .and_then(|v| v.as_array())
        .unwrap_or(&empty);

    let suggestions: Vec<serde_json::Value> = objectives
        .iter()
        .filter(|o| {
            if intent.is_empty() {
                true
            } else {
                let txt = o
                    .get("text")
                    .or_else(|| o.get("title"))
                    .and_then(|v| v.as_str())
                    .unwrap_or("")
                    .to_lowercase();
                intent
                    .split_whitespace()
                    .any(|w| w.len() > 3 && txt.contains(w))
            }
        })
        .take(args.limit)
        .map(|o| {
            serde_json::json!({
                "kind": "objective",
                "id": o.get("id"),
                "text": o.get("text").or_else(|| o.get("title")),
                "score": 0.7
            })
        })
        .collect();

    // Include explicitly requested constructs.
    let explicit: Vec<String> = args
        .constructs
        .as_deref()
        .unwrap_or("")
        .split(',')
        .map(|s| s.trim().to_string())
        .filter(|s| !s.is_empty())
        .collect();

    let result = serde_json::json!({
        "intent": args.intent,
        "constructs_requested": explicit,
        "kind": args.kind,
        "suggestions": suggestions,
        "note": "full derive requires running daemon with pattern catalog"
    });

    if json_mode {
        println!("{}", serde_json::to_string_pretty(&result)?);
    } else {
        let intent_str = args.intent.as_deref().unwrap_or("(none)");
        println!(
            "derive: intent=\"{intent_str}\"  kind={}  suggestions={}",
            args.kind,
            suggestions.len()
        );
        for s in suggestions.iter() {
            let id = s["id"].as_str().unwrap_or("?");
            let text = s["text"].as_str().unwrap_or("?");
            let short: String = text.chars().take(60).collect();
            println!("  {id}: {short}");
        }
        if !explicit.is_empty() {
            println!("  constructs: {}", explicit.join(", "));
        }
        if suggestions.is_empty() && explicit.is_empty() {
            println!("  (no suggestions — full derive requires AI executor and pattern catalog)");
        }
    }
    Ok(())
}

// ── propose ───────────────────────────────────────────────────────────────────

#[derive(Debug, clap::Args)]
#[command(about = "Propose a new objective (queued for daemon)")]
pub struct ProposeArgs {
    /// Proposal title
    #[arg(long)]
    pub title: Option<String>,

    /// Reason / justification
    #[arg(long)]
    pub reason: Option<String>,

    /// Target scope
    #[arg(long)]
    pub scope: Option<String>,
}

pub async fn handle_propose(_root: &Path, args: &ProposeArgs, json_mode: bool) -> Result<()> {
    // Propose writes an objective input file — requires daemon for authority gate.
    eprintln!("not yet wired: propose requires a running daemon to pass the §62z authority gate");
    if json_mode {
        println!(
            "{}",
            serde_json::json!({
                "status": "stub",
                "title": args.title,
                "reason": args.reason,
                "scope": args.scope,
                "note": "operation not yet wired to live daemon"
            })
        );
    } else {
        let title = args.title.as_deref().unwrap_or("(none)");
        let reason = args.reason.as_deref().unwrap_or("(none)");
        println!("propose: title=\"{title}\"  reason=\"{reason}\"");
        println!("  operation not yet wired to live daemon");
    }
    Ok(())
}

// ── Helpers ───────────────────────────────────────────────────────────────────

/// Load config.json from `<root>/config.json`.  Returns empty object on failure.
fn load_config_json(root: &Path) -> Value {
    let p = root.join("config.json");
    if let Ok(s) = std::fs::read_to_string(&p) {
        if let Ok(v) = serde_json::from_str::<Value>(&s) {
            return v;
        }
    }
    Value::Object(Default::default())
}

// ── tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    fn write_state(dir: &TempDir, json: serde_json::Value) {
        let path = dir.path().join("state.json");
        std::fs::write(path, serde_json::to_string_pretty(&json).unwrap()).unwrap();
    }

    #[tokio::test]
    async fn test_github_status_empty() {
        let dir = TempDir::new().unwrap();
        write_state(&dir, serde_json::json!({}));
        let args = GithubArgs {
            action: "status".into(),
            repo: None,
            workflow: None,
            ref_name: "main".into(),
            inputs: None,
            dry_run: false,
            token_env: "URACE_GITHUB_TOKEN".into(),
        };
        handle_github(dir.path(), &args, false).await.unwrap();
    }

    #[tokio::test]
    async fn test_plan_empty() {
        let dir = TempDir::new().unwrap();
        write_state(&dir, serde_json::json!({}));
        let args = PlanArgs {
            scope: None,
            limit: 20,
        };
        handle_plan(dir.path(), &args, false).await.unwrap();
    }

    #[tokio::test]
    async fn test_check_empty() {
        let dir = TempDir::new().unwrap();
        write_state(&dir, serde_json::json!({}));
        let args = CheckArgs {
            blockers_only: false,
        };
        handle_check(dir.path(), &args, true).await.unwrap();
    }

    #[tokio::test]
    async fn test_quality_empty() {
        let dir = TempDir::new().unwrap();
        write_state(&dir, serde_json::json!({}));
        let args = QualityArgs {
            history: false,
            limit: 20,
        };
        handle_quality(dir.path(), &args, false).await.unwrap();
    }

    #[tokio::test]
    async fn test_context_view() {
        let dir = TempDir::new().unwrap();
        write_state(
            &dir,
            serde_json::json!({
                "objectives": [{"id": "obj-1", "text": "improve quality", "status": "PLANNED"}]
            }),
        );
        let args = ContextArgs {
            action: "view".into(),
            node_id: None,
            limit: 20,
        };
        handle_context(dir.path(), &args, true).await.unwrap();
    }

    #[tokio::test]
    async fn test_classify_no_match() {
        let dir = TempDir::new().unwrap();
        write_state(&dir, serde_json::json!({}));
        let args = ClassifyArgs {
            text: "some random text".into(),
            scope: None,
        };
        handle_classify(dir.path(), &args, true).await.unwrap();
    }

    #[tokio::test]
    async fn test_derive_empty() {
        let dir = TempDir::new().unwrap();
        write_state(&dir, serde_json::json!({}));
        let args = DeriveArgs {
            intent: Some("resilience".into()),
            constructs: None,
            kind: "all".into(),
            limit: 8,
        };
        handle_derive(dir.path(), &args, true).await.unwrap();
    }

    #[tokio::test]
    async fn test_propose_stub() {
        let dir = TempDir::new().unwrap();
        let args = ProposeArgs {
            title: Some("New feature".into()),
            reason: Some("User requested".into()),
            scope: None,
        };
        handle_propose(dir.path(), &args, true).await.unwrap();
    }
}
