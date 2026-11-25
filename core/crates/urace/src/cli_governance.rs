//! Governance subcommand handlers for the `urace` CLI.
//!
//! Covers: evidence, blocker, decision, milestone, compliance, rules, inbox.
//!
//! All read operations work fully against `<root>/state.json` or
//! `<root>/state/state.json`.  Write operations that require a live daemon
//! print a stub notice instead.

use anyhow::Result;
use serde_json::Value;
use std::path::{Path, PathBuf};

// ── State loader helper ───────────────────────────────────────────────────────

/// Load the raw state JSON from `<root>/state/state.json` or `<root>/state.json`.
///
/// Returns `Value::Null` (treated as empty) when neither file exists.
pub fn load_state_json(root: &Path) -> Result<Value> {
    // Prefer the nested path first (matches Python runtime layout).
    let candidates: [PathBuf; 2] = [
        root.join("state").join("state.json"),
        root.join("state.json"),
    ];
    for path in &candidates {
        if path.exists() {
            let raw = std::fs::read_to_string(path)
                .map_err(|e| anyhow::anyhow!("reading {}: {}", path.display(), e))?;
            let v: Value = serde_json::from_str(&raw)
                .map_err(|e| anyhow::anyhow!("parsing {}: {}", path.display(), e))?;
            return Ok(v);
        }
    }
    Ok(Value::Object(Default::default()))
}

/// Save state JSON back to whichever path already exists (or creates the
/// nested path).  Uses an atomic tmp-then-rename write.
#[allow(dead_code)]
fn save_state_json(root: &Path, v: &Value) -> Result<()> {
    let path = if root.join("state").join("state.json").exists() {
        root.join("state").join("state.json")
    } else if root.join("state.json").exists() {
        root.join("state.json")
    } else {
        // Default to nested path.
        root.join("state").join("state.json")
    };
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent)?;
    }
    let json = serde_json::to_string_pretty(v)?;
    let tmp = path.with_extension("json.tmp");
    std::fs::write(&tmp, json.as_bytes())
        .map_err(|e| anyhow::anyhow!("writing tmp {}: {}", tmp.display(), e))?;
    std::fs::rename(&tmp, &path)
        .map_err(|e| anyhow::anyhow!("renaming to {}: {}", path.display(), e))?;
    Ok(())
}

// ── evidence ──────────────────────────────────────────────────────────────────

#[derive(Debug, clap::Args)]
#[command(about = "Browse evidence records")]
pub struct EvidenceArgs {
    /// Sub-action: list | show
    #[arg(default_value = "list")]
    pub action: String,

    /// Record ID (for 'show')
    #[arg(long)]
    pub id: Option<String>,

    /// Filter by evidence kind
    #[arg(long)]
    pub kind: Option<String>,

    /// Maximum records to display
    #[arg(long, default_value = "20")]
    pub limit: usize,
}

pub async fn handle_evidence(root: &Path, args: &EvidenceArgs, json_mode: bool) -> Result<()> {
    let state = load_state_json(root)?;
    let empty = vec![];
    let all: &Vec<Value> = state
        .get("evidence")
        .and_then(|v| v.as_array())
        .unwrap_or(&empty);

    // Most recent first.
    let mut records: Vec<&Value> = all.iter().rev().collect();

    if let Some(kind) = &args.kind {
        records.retain(|r| r.get("kind").and_then(|v| v.as_str()) == Some(kind.as_str()));
    }

    match args.action.as_str() {
        "show" => {
            let id = args.id.as_deref().unwrap_or("");
            if id.is_empty() {
                anyhow::bail!("evidence show requires --id <id>");
            }
            let rec = records
                .into_iter()
                .find(|r| r.get("id").and_then(|v| v.as_str()) == Some(id));
            match rec {
                Some(r) => {
                    if json_mode {
                        println!("{}", serde_json::to_string_pretty(r)?);
                    } else {
                        for (k, v) in r.as_object().into_iter().flatten() {
                            println!("  {k}: {v}");
                        }
                    }
                }
                None => {
                    if json_mode {
                        println!("{}", serde_json::json!({"error": "not found", "id": id}));
                    } else {
                        println!("evidence {id}: not found");
                    }
                }
            }
        }
        _ => {
            // list
            records.truncate(args.limit);
            if json_mode {
                let arr: Vec<&Value> = records;
                println!("{}", serde_json::to_string_pretty(&arr)?);
            } else if records.is_empty() {
                println!("No evidence records.");
            } else {
                for r in records {
                    let id = r.get("id").and_then(|v| v.as_str()).unwrap_or("?");
                    let kind = r.get("kind").and_then(|v| v.as_str()).unwrap_or("?");
                    let at = r.get("at").and_then(|v| v.as_str()).unwrap_or("?");
                    let summary = r
                        .get("summary")
                        .and_then(|v| v.as_str())
                        .unwrap_or(kind);
                    let summary_short: String = summary.chars().take(60).collect();
                    println!("{id}: {kind} at={at} {summary_short}");
                }
            }
        }
    }
    Ok(())
}

// ── blocker ───────────────────────────────────────────────────────────────────

#[derive(Debug, clap::Args)]
#[command(about = "Manage blockers (list / resolve)")]
pub struct BlockerArgs {
    /// Sub-action: list | resolve
    #[arg(default_value = "list")]
    pub action: String,

    /// Blocker ID (for 'resolve')
    #[arg(long)]
    pub blocker_id: Option<String>,

    /// Include resolved blockers in list
    #[arg(long)]
    pub resolved: bool,

    /// Filter by scope
    #[arg(long)]
    pub scope: Option<String>,

    /// Optional note when resolving
    #[arg(long)]
    pub note: Option<String>,
}

pub async fn handle_blocker(root: &Path, args: &BlockerArgs, json_mode: bool) -> Result<()> {
    match args.action.as_str() {
        "resolve" => {
            let bid = args.blocker_id.as_deref().unwrap_or("");
            if bid.is_empty() {
                anyhow::bail!("blocker resolve requires --blocker-id <id>");
            }
            // Write stub — requires live daemon for atomic evidence append.
            if json_mode {
                println!(
                    "{}",
                    serde_json::json!({
                        "blocker_id": bid,
                        "status": "stub",
                        "note": "operation not yet wired to live daemon"
                    })
                );
            } else {
                println!("blocker resolve {bid}: operation not yet wired to live daemon");
            }
        }
        _ => {
            // list
            let state = load_state_json(root)?;
            let empty = vec![];
            let all: &Vec<Value> = state
                .get("blockers")
                .and_then(|v| v.as_array())
                .unwrap_or(&empty);
            let mut blockers: Vec<&Value> = all.iter().collect();
            if !args.resolved {
                blockers.retain(|b| b.get("resolved_at").is_none() || b["resolved_at"].is_null());
            }
            if let Some(scope) = &args.scope {
                blockers
                    .retain(|b| b.get("scope").and_then(|v| v.as_str()) == Some(scope.as_str()));
            }
            if json_mode {
                println!("{}", serde_json::to_string_pretty(&blockers)?);
            } else if blockers.is_empty() {
                println!("No active blockers.");
            } else {
                for b in blockers {
                    let id = b.get("id").and_then(|v| v.as_str()).unwrap_or("?");
                    let scope = b.get("scope").and_then(|v| v.as_str()).unwrap_or("?");
                    let count = b.get("count").and_then(|v| v.as_u64()).unwrap_or(1);
                    let cls = b
                        .get("classification")
                        .and_then(|v| v.as_str())
                        .unwrap_or("?");
                    let last = b
                        .get("last_at")
                        .and_then(|v| v.as_str())
                        .unwrap_or("?");
                    println!("{id}: scope={scope} count={count} [{cls}] last_at={last}");
                }
            }
        }
    }
    Ok(())
}

// ── decision ──────────────────────────────────────────────────────────────────

#[derive(Debug, clap::Args)]
#[command(about = "Browse decision records")]
pub struct DecisionArgs {
    /// Sub-action: list | show
    #[arg(default_value = "list")]
    pub action: String,

    /// Decision ID (for 'show')
    #[arg(long)]
    pub id: Option<String>,

    /// Filter by scope
    #[arg(long)]
    pub scope: Option<String>,

    /// Only show stale decisions
    #[arg(long)]
    pub stale: bool,

    /// Maximum records to display
    #[arg(long, default_value = "20")]
    pub limit: usize,
}

pub async fn handle_decision(root: &Path, args: &DecisionArgs, json_mode: bool) -> Result<()> {
    let state = load_state_json(root)?;
    let empty = vec![];
    let all: &Vec<Value> = state
        .get("decision_records")
        .and_then(|v| v.as_array())
        .unwrap_or(&empty);

    let mut records: Vec<&Value> = all.iter().rev().collect();

    if args.stale {
        records.retain(|r| {
            r.get("provenance_revised")
                .and_then(|v| v.as_bool())
                .unwrap_or(false)
        });
    }
    if let Some(scope) = &args.scope {
        records.retain(|r| r.get("scope").and_then(|v| v.as_str()) == Some(scope.as_str()));
    }

    match args.action.as_str() {
        "show" => {
            let id = args.id.as_deref().unwrap_or("");
            if id.is_empty() {
                anyhow::bail!("decision show requires --id <id>");
            }
            let rec = records
                .into_iter()
                .find(|r| r.get("id").and_then(|v| v.as_str()) == Some(id));
            match rec {
                Some(r) => {
                    if json_mode {
                        println!("{}", serde_json::to_string_pretty(r)?);
                    } else {
                        for (k, v) in r.as_object().into_iter().flatten() {
                            println!("  {k}: {v}");
                        }
                    }
                }
                None => {
                    if json_mode {
                        println!("{}", serde_json::json!({"error": "not found", "id": id}));
                    } else {
                        println!("decision {id}: not found");
                    }
                }
            }
        }
        _ => {
            records.truncate(args.limit);
            if json_mode {
                println!("{}", serde_json::to_string_pretty(&records)?);
            } else if records.is_empty() {
                println!("No decision records.");
            } else {
                for r in records {
                    let id = r.get("id").and_then(|v| v.as_str()).unwrap_or("?");
                    let outcome = r.get("outcome").and_then(|v| v.as_str()).unwrap_or("?");
                    let at = r
                        .get("decided_at")
                        .or_else(|| r.get("at"))
                        .and_then(|v| v.as_str())
                        .unwrap_or("?");
                    let stale_flag = if r
                        .get("provenance_revised")
                        .and_then(|v| v.as_bool())
                        .unwrap_or(false)
                    {
                        " [STALE]"
                    } else {
                        ""
                    };
                    println!("{id}: outcome={outcome} decided_at={at}{stale_flag}");
                }
            }
        }
    }
    Ok(())
}

// ── milestone ─────────────────────────────────────────────────────────────────

#[derive(Debug, clap::Args)]
#[command(about = "Browse milestones")]
pub struct MilestoneArgs {
    /// Sub-action: list | show | add
    #[arg(default_value = "list")]
    pub action: String,

    /// Milestone ID (for 'show')
    #[arg(long)]
    pub id: Option<String>,

    /// Maximum records to display
    #[arg(long, default_value = "20")]
    pub limit: usize,
}

pub async fn handle_milestone(root: &Path, args: &MilestoneArgs, json_mode: bool) -> Result<()> {
    match args.action.as_str() {
        "add" => {
            if json_mode {
                println!(
                    "{}",
                    serde_json::json!({
                        "status": "stub",
                        "note": "operation not yet wired to live daemon"
                    })
                );
            } else {
                println!("milestone add: operation not yet wired to live daemon");
            }
        }
        "show" => {
            let id = args.id.as_deref().unwrap_or("");
            if id.is_empty() {
                anyhow::bail!("milestone show requires --id <id>");
            }
            let state = load_state_json(root)?;
            let empty = vec![];
            let all: &Vec<Value> = state
                .get("milestones")
                .and_then(|v| v.as_array())
                .unwrap_or(&empty);
            let rec = all
                .iter()
                .find(|r| r.get("id").and_then(|v| v.as_str()) == Some(id));
            match rec {
                Some(r) => {
                    if json_mode {
                        println!("{}", serde_json::to_string_pretty(r)?);
                    } else {
                        for (k, v) in r.as_object().into_iter().flatten() {
                            println!("  {k}: {v}");
                        }
                    }
                }
                None => {
                    if json_mode {
                        println!("{}", serde_json::json!({"error": "not found", "id": id}));
                    } else {
                        println!("milestone {id}: not found");
                    }
                }
            }
        }
        _ => {
            // list
            let state = load_state_json(root)?;
            let empty = vec![];
            let all: &Vec<Value> = state
                .get("milestones")
                .and_then(|v| v.as_array())
                .unwrap_or(&empty);
            let records: Vec<&Value> = all.iter().rev().take(args.limit).collect();
            if json_mode {
                println!("{}", serde_json::to_string_pretty(&records)?);
            } else if records.is_empty() {
                println!("No milestones.");
            } else {
                for r in records {
                    let id = r.get("id").and_then(|v| v.as_str()).unwrap_or("?");
                    let title = r
                        .get("title")
                        .and_then(|v| v.as_str())
                        .unwrap_or("(untitled)");
                    let status = r.get("status").and_then(|v| v.as_str()).unwrap_or("?");
                    println!("{id}: {title} [{status}]");
                }
            }
        }
    }
    Ok(())
}

// ── compliance ────────────────────────────────────────────────────────────────

#[derive(Debug, clap::Args)]
#[command(about = "Browse compliance records")]
pub struct ComplianceArgs {
    /// Sub-action: list | domain | history
    #[arg(default_value = "list")]
    pub action: String,

    /// Domain name (for 'domain')
    #[arg(long)]
    pub name: Option<String>,

    /// Maximum records to display
    #[arg(long, default_value = "20")]
    pub limit: usize,
}

pub async fn handle_compliance(root: &Path, args: &ComplianceArgs, json_mode: bool) -> Result<()> {
    let state = load_state_json(root)?;
    let empty = vec![];

    match args.action.as_str() {
        "domain" => {
            let name = args.name.as_deref().unwrap_or("");
            if name.is_empty() {
                anyhow::bail!("compliance domain requires --name <domain>");
            }
            let all: &Vec<Value> = state
                .get("compliance_records")
                .and_then(|v| v.as_array())
                .unwrap_or(&empty);
            let records: Vec<&Value> = all
                .iter()
                .filter(|r| r.get("domain").and_then(|v| v.as_str()) == Some(name))
                .collect();
            if json_mode {
                println!("{}", serde_json::to_string_pretty(&records)?);
            } else if records.is_empty() {
                println!("No compliance records for domain {name}.");
            } else {
                for r in records {
                    let id = r.get("id").and_then(|v| v.as_str()).unwrap_or("?");
                    let status = r.get("status").and_then(|v| v.as_str()).unwrap_or("?");
                    let at = r.get("at").and_then(|v| v.as_str()).unwrap_or("?");
                    println!("{id}: domain={name} status={status} at={at}");
                }
            }
        }
        "history" => {
            let all: &Vec<Value> = state
                .get("compliance_history")
                .and_then(|v| v.as_array())
                .unwrap_or(&empty);
            let records: Vec<&Value> = all.iter().rev().take(args.limit).collect();
            if json_mode {
                println!("{}", serde_json::to_string_pretty(&records)?);
            } else if records.is_empty() {
                println!("No compliance history.");
            } else {
                for r in records {
                    let at = r.get("at").and_then(|v| v.as_str()).unwrap_or("?");
                    let domain = r.get("domain").and_then(|v| v.as_str()).unwrap_or("?");
                    let status = r.get("status").and_then(|v| v.as_str()).unwrap_or("?");
                    println!("{at}: domain={domain} status={status}");
                }
            }
        }
        _ => {
            // list
            let all: &Vec<Value> = state
                .get("compliance_records")
                .and_then(|v| v.as_array())
                .unwrap_or(&empty);
            let records: Vec<&Value> = all.iter().rev().take(args.limit).collect();
            if json_mode {
                println!("{}", serde_json::to_string_pretty(&records)?);
            } else if records.is_empty() {
                println!("No compliance records.");
            } else {
                for r in records {
                    let id = r.get("id").and_then(|v| v.as_str()).unwrap_or("?");
                    let domain = r.get("domain").and_then(|v| v.as_str()).unwrap_or("?");
                    let status = r.get("status").and_then(|v| v.as_str()).unwrap_or("?");
                    println!("{id}: domain={domain} status={status}");
                }
            }
        }
    }
    Ok(())
}

// ── rules ─────────────────────────────────────────────────────────────────────

#[derive(Debug, clap::Args)]
#[command(about = "Browse governance rules")]
pub struct RulesArgs {
    /// Sub-action: list | show | graph | conflicts
    #[arg(default_value = "list")]
    pub action: String,

    /// Rule ID (for 'show')
    #[arg(long)]
    pub id: Option<String>,

    /// Maximum records to display
    #[arg(long, default_value = "40")]
    pub limit: usize,
}

pub async fn handle_rules(root: &Path, args: &RulesArgs, json_mode: bool) -> Result<()> {
    let state = load_state_json(root)?;
    let empty = vec![];
    let all: &Vec<Value> = state
        .get("governance_rules")
        .and_then(|v| v.as_array())
        .unwrap_or(&empty);

    match args.action.as_str() {
        "show" => {
            let id = args.id.as_deref().unwrap_or("");
            if id.is_empty() {
                anyhow::bail!("rules show requires --id <id>");
            }
            let rec = all
                .iter()
                .find(|r| r.get("id").and_then(|v| v.as_str()) == Some(id));
            match rec {
                Some(r) => {
                    if json_mode {
                        println!("{}", serde_json::to_string_pretty(r)?);
                    } else {
                        for (k, v) in r.as_object().into_iter().flatten() {
                            println!("  {k}: {v}");
                        }
                    }
                }
                None => {
                    if json_mode {
                        println!("{}", serde_json::json!({"error": "not found", "id": id}));
                    } else {
                        println!("rule {id}: not found");
                    }
                }
            }
        }
        "graph" => {
            // Print a simple adjacency text; full graphing requires running system.
            if json_mode {
                let nodes: Vec<serde_json::Value> = all
                    .iter()
                    .map(|r| {
                        serde_json::json!({
                            "id": r.get("id"),
                            "depends_on": r.get("depends_on"),
                        })
                    })
                    .collect();
                println!("{}", serde_json::to_string_pretty(&nodes)?);
            } else {
                for r in all.iter() {
                    let id = r.get("id").and_then(|v| v.as_str()).unwrap_or("?");
                    let deps = r
                        .get("depends_on")
                        .and_then(|v| v.as_array())
                        .map(|arr| {
                            arr.iter()
                                .filter_map(|x| x.as_str())
                                .collect::<Vec<_>>()
                                .join(", ")
                        })
                        .unwrap_or_default();
                    if deps.is_empty() {
                        println!("{id}");
                    } else {
                        println!("{id} → {deps}");
                    }
                }
            }
        }
        "conflicts" => {
            let conflicts: Vec<&Value> = all
                .iter()
                .filter(|r| {
                    r.get("conflict_with")
                        .and_then(|v| v.as_array())
                        .map(|a| !a.is_empty())
                        .unwrap_or(false)
                })
                .collect();
            if json_mode {
                println!("{}", serde_json::to_string_pretty(&conflicts)?);
            } else if conflicts.is_empty() {
                println!("No rule conflicts detected.");
            } else {
                for r in conflicts {
                    let id = r.get("id").and_then(|v| v.as_str()).unwrap_or("?");
                    let cw = r
                        .get("conflict_with")
                        .and_then(|v| v.as_array())
                        .map(|arr| {
                            arr.iter()
                                .filter_map(|x| x.as_str())
                                .collect::<Vec<_>>()
                                .join(", ")
                        })
                        .unwrap_or_default();
                    println!("{id} conflicts with: {cw}");
                }
            }
        }
        _ => {
            // list
            let records: Vec<&Value> = all.iter().take(args.limit).collect();
            if json_mode {
                println!("{}", serde_json::to_string_pretty(&records)?);
            } else if records.is_empty() {
                println!("No governance rules.");
            } else {
                for r in records {
                    let id = r.get("id").and_then(|v| v.as_str()).unwrap_or("?");
                    let name = r
                        .get("name")
                        .and_then(|v| v.as_str())
                        .unwrap_or("(unnamed)");
                    let enabled = r
                        .get("enabled")
                        .and_then(|v| v.as_bool())
                        .unwrap_or(true);
                    println!("{id}: {name} [{}]", if enabled { "enabled" } else { "disabled" });
                }
            }
        }
    }
    Ok(())
}

// ── inbox ─────────────────────────────────────────────────────────────────────

#[derive(Debug, clap::Args)]
#[command(about = "Manage patch proposal inbox (list / apply / reject / count)")]
pub struct InboxArgs {
    /// Sub-action: list | apply | reject | count
    #[arg(default_value = "list")]
    pub action: String,

    /// Proposal ID (for 'apply' or 'reject')
    #[arg(long)]
    pub id: Option<String>,

    /// Rejection reason
    #[arg(long)]
    pub reason: Option<String>,

    /// Filter by kind
    #[arg(long)]
    pub kind: Option<String>,

    /// Maximum records to display
    #[arg(long, default_value = "20")]
    pub limit: usize,
}

pub async fn handle_inbox(root: &Path, args: &InboxArgs, json_mode: bool) -> Result<()> {
    let state = load_state_json(root)?;
    let empty = vec![];

    match args.action.as_str() {
        "apply" | "reject" => {
            let pid = args.id.as_deref().unwrap_or("");
            if pid.is_empty() {
                anyhow::bail!("inbox {} requires --id <proposal_id>", args.action);
            }
            // §62z: mutating proposals requires authority gate — stub until wired to daemon.
            if json_mode {
                println!(
                    "{}",
                    serde_json::json!({
                        "proposal_id": pid,
                        "action": args.action,
                        "status": "stub",
                        "note": "operation not yet wired to live daemon"
                    })
                );
            } else {
                println!(
                    "inbox {} {pid}: operation not yet wired to live daemon",
                    args.action
                );
            }
        }
        "count" => {
            let proposals: &Vec<Value> = state
                .get("patch_proposals")
                .and_then(|v| v.as_array())
                .unwrap_or(&empty);
            let pending = proposals
                .iter()
                .filter(|p| {
                    p.get("status").and_then(|v| v.as_str()) == Some("PENDING")
                })
                .count();
            if json_mode {
                println!(
                    "{}",
                    serde_json::json!({"pending": pending, "total": proposals.len()})
                );
            } else {
                println!("pending: {pending}  total: {}", proposals.len());
            }
        }
        _ => {
            // list
            let proposals: &Vec<Value> = state
                .get("patch_proposals")
                .and_then(|v| v.as_array())
                .unwrap_or(&empty);
            let mut items: Vec<&Value> = proposals.iter().rev().collect();
            if let Some(kind) = &args.kind {
                items.retain(|p| p.get("kind").and_then(|v| v.as_str()) == Some(kind.as_str()));
            }
            items.truncate(args.limit);
            if json_mode {
                println!("{}", serde_json::to_string_pretty(&items)?);
            } else if items.is_empty() {
                println!("Inbox empty.");
            } else {
                for p in items {
                    let id = p.get("id").and_then(|v| v.as_str()).unwrap_or("?");
                    let kind = p.get("kind").and_then(|v| v.as_str()).unwrap_or("unknown");
                    let status = p
                        .get("status")
                        .and_then(|v| v.as_str())
                        .unwrap_or("QUEUED");
                    println!("{id}: {kind} {status}");
                }
            }
        }
    }
    Ok(())
}

// ── tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write;
    use tempfile::TempDir;

    fn write_state(dir: &TempDir, json: serde_json::Value) -> PathBuf {
        let path = dir.path().join("state.json");
        let mut f = std::fs::File::create(&path).unwrap();
        f.write_all(serde_json::to_string_pretty(&json).unwrap().as_bytes())
            .unwrap();
        path
    }

    #[test]
    fn test_load_state_json_missing_returns_empty_object() {
        let dir = TempDir::new().unwrap();
        let v = load_state_json(dir.path()).unwrap();
        assert!(v.is_object());
    }

    #[test]
    fn test_load_state_json_root_level() {
        let dir = TempDir::new().unwrap();
        write_state(dir, serde_json::json!({"evidence": [{"id": "ev-001"}]}));
        let v = load_state_json(dir.path()).unwrap();
        assert_eq!(
            v.get("evidence")
                .and_then(|a| a.as_array())
                .map(|a| a.len()),
            Some(1)
        );
    }

    #[test]
    fn test_load_state_json_nested_path_takes_priority() {
        let dir = TempDir::new().unwrap();
        // Write to nested path.
        let nested = dir.path().join("state");
        std::fs::create_dir_all(&nested).unwrap();
        let path = nested.join("state.json");
        std::fs::write(
            &path,
            serde_json::to_string_pretty(&serde_json::json!({"evidence": []})).unwrap(),
        )
        .unwrap();
        // Also write a root-level one with different content.
        std::fs::write(
            dir.path().join("state.json"),
            serde_json::to_string_pretty(&serde_json::json!({"evidence": [1, 2, 3]})).unwrap(),
        )
        .unwrap();
        let v = load_state_json(dir.path()).unwrap();
        // Should pick nested (empty evidence array).
        assert_eq!(
            v.get("evidence")
                .and_then(|a| a.as_array())
                .map(|a| a.len()),
            Some(0)
        );
    }

    #[test]
    fn test_save_and_reload_state_json() {
        let dir = TempDir::new().unwrap();
        let data = serde_json::json!({"blockers": [{"id": "bl-1", "scope": "test"}]});
        save_state_json(dir.path(), &data).unwrap();
        let loaded = load_state_json(dir.path()).unwrap();
        let bl = loaded["blockers"][0]["id"].as_str();
        assert_eq!(bl, Some("bl-1"));
    }

    #[tokio::test]
    async fn test_handle_evidence_empty() {
        let dir = TempDir::new().unwrap();
        let args = EvidenceArgs {
            action: "list".into(),
            id: None,
            kind: None,
            limit: 20,
        };
        // Should not panic on empty state.
        handle_evidence(dir.path(), &args, false).await.unwrap();
    }

    #[tokio::test]
    async fn test_handle_blocker_list_empty() {
        let dir = TempDir::new().unwrap();
        let args = BlockerArgs {
            action: "list".into(),
            blocker_id: None,
            resolved: false,
            scope: None,
            note: None,
        };
        handle_blocker(dir.path(), &args, false).await.unwrap();
    }

    #[tokio::test]
    async fn test_handle_inbox_count_zero() {
        let dir = TempDir::new().unwrap();
        let args = InboxArgs {
            action: "count".into(),
            id: None,
            reason: None,
            kind: None,
            limit: 20,
        };
        handle_inbox(dir.path(), &args, true).await.unwrap();
    }
}
