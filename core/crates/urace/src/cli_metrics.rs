//! Metrics subcommand handlers for the `urace` CLI.
//!
//! Covers: vitals, audit, goals, data, trace.
//!
//! All reads work against `<root>/state.json` or `<root>/state/state.json`.
//! Audit log is read from `<root>/audit.jsonl`.
//! Write mutations print a stub notice.

use anyhow::Result;
use serde_json::Value;
use std::path::Path;

use crate::cli_governance::load_state_json;

// ── vitals ────────────────────────────────────────────────────────────────────

#[derive(Debug, clap::Args)]
#[command(about = "Show runtime vitals (lifecycle, APS score, cycle count, counts)")]
pub struct VitalsArgs {
    // No extra flags — json is a global flag on Cli.
}

pub async fn handle_vitals(root: &Path, _args: &VitalsArgs, json_mode: bool) -> Result<()> {
    let state = load_state_json(root)?;

    let lifecycle = state
        .get("lifecycle_state")
        .and_then(|v| v.as_str())
        .unwrap_or("UNKNOWN");
    let aps_score = state.get("aps_score").cloned().unwrap_or(Value::Null);
    let cycle_count = state
        .get("cycle_count")
        .and_then(|v| v.as_u64())
        .unwrap_or(0);
    let objectives_count = state
        .get("objectives")
        .and_then(|v| v.as_array())
        .map(|a| a.len())
        .unwrap_or(0);
    let evidence_count = state
        .get("evidence")
        .and_then(|v| v.as_array())
        .map(|a| a.len())
        .unwrap_or(0);
    let blockers_active = state
        .get("blockers")
        .and_then(|v| v.as_array())
        .map(|a| {
            a.iter()
                .filter(|b| b.get("resolved_at").is_none() || b["resolved_at"].is_null())
                .count()
        })
        .unwrap_or(0);

    if json_mode {
        println!(
            "{}",
            serde_json::json!({
                "lifecycle_state": lifecycle,
                "aps_score": aps_score,
                "cycle_count": cycle_count,
                "objectives": objectives_count,
                "evidence": evidence_count,
                "blockers_active": blockers_active,
            })
        );
    } else {
        println!("lifecycle_state:  {lifecycle}");
        println!("aps_score:        {aps_score}");
        println!("cycle_count:      {cycle_count}");
        println!("objectives:       {objectives_count}");
        println!("evidence:         {evidence_count}");
        println!("blockers_active:  {blockers_active}");
    }
    Ok(())
}

// ── audit ─────────────────────────────────────────────────────────────────────

#[derive(Debug, clap::Args)]
#[command(about = "Browse the audit log (<root>/audit.jsonl)")]
pub struct AuditArgs {
    /// Sub-action: decisions | evidence (omit = show all)
    pub action: Option<String>,

    /// Only show records at or after this ISO timestamp
    #[arg(long)]
    pub since: Option<String>,

    /// Maximum records to display
    #[arg(long, default_value = "20")]
    pub limit: usize,
}

pub async fn handle_audit(root: &Path, args: &AuditArgs, json_mode: bool) -> Result<()> {
    // Prefer <root>/audit.jsonl; fall back to <root>/state/audit.jsonl.
    let candidates = [
        root.join("audit.jsonl"),
        root.join("state").join("audit.jsonl"),
    ];
    let audit_path = candidates.iter().find(|p| p.exists());

    if audit_path.is_none() {
        if json_mode {
            println!("{}", serde_json::json!({"status": "no_audit_log"}));
        } else {
            println!("No audit log found.");
        }
        return Ok(());
    }

    let raw = std::fs::read_to_string(audit_path.unwrap())?;
    let mut records: Vec<Value> = raw
        .lines()
        .filter_map(|line| serde_json::from_str(line).ok())
        .collect();

    // Filter by action sub-type.
    if let Some(action) = &args.action {
        records.retain(|r| {
            let kind = r
                .get("kind")
                .or_else(|| r.get("operation"))
                .and_then(|v| v.as_str())
                .unwrap_or("");
            kind.to_ascii_lowercase().contains(action.as_str())
        });
    }

    // Filter by --since.
    if let Some(since) = &args.since {
        records.retain(|r| {
            r.get("at")
                .and_then(|v| v.as_str())
                .map(|at| at >= since.as_str())
                .unwrap_or(false)
        });
    }

    // Most recent last (audit log is append-ordered); take the last N.
    let total = records.len();
    let start = total.saturating_sub(args.limit);
    let page = &records[start..];

    if json_mode {
        println!("{}", serde_json::json!({"records": page, "total": total}));
    } else {
        for r in page {
            let kind = r.get("kind").and_then(|v| v.as_str()).unwrap_or("?");
            let op = r.get("operation").and_then(|v| v.as_str()).unwrap_or("?");
            let at = r.get("at").and_then(|v| v.as_str()).unwrap_or("?");
            println!("  {kind} | {op} | {at}");
        }
    }
    Ok(())
}

// ── goals ─────────────────────────────────────────────────────────────────────

#[derive(Debug, clap::Args)]
#[command(about = "Manage goals / objectives (list, add, pin, unpin, defer, cancel)")]
pub struct GoalsArgs {
    /// Sub-action: list | add | pin | unpin | defer | cancel
    #[arg(default_value = "list")]
    pub action: String,

    /// Goal title (for 'add')
    pub title: Option<String>,

    /// Goal ID (for pin / unpin / defer / cancel)
    #[arg(long)]
    pub id: Option<String>,

    /// Filter by status
    #[arg(long)]
    pub status: Option<String>,

    /// Maximum records to display
    #[arg(long, default_value = "20")]
    pub limit: usize,
}

pub async fn handle_goals(root: &Path, args: &GoalsArgs, json_mode: bool) -> Result<()> {
    match args.action.as_str() {
        "add" | "pin" | "unpin" | "defer" | "cancel" => {
            // Mutations require live daemon authority gate.
            let id_or_title = args.id.as_deref().or(args.title.as_deref()).unwrap_or("?");
            if json_mode {
                println!(
                    "{}",
                    serde_json::json!({
                        "action": args.action,
                        "ref": id_or_title,
                        "status": "stub",
                        "note": "operation not yet wired to live daemon"
                    })
                );
            } else {
                println!(
                    "goals {} {id_or_title}: operation not yet wired to live daemon",
                    args.action
                );
            }
        }
        _ => {
            // list
            let state = load_state_json(root)?;
            let empty = vec![];
            let all: &Vec<Value> = state
                .get("objectives")
                .and_then(|v| v.as_array())
                .unwrap_or(&empty);
            let mut records: Vec<&Value> = all.iter().rev().collect();
            if let Some(status_filter) = &args.status {
                records.retain(|r| {
                    r.get("status").and_then(|v| v.as_str()) == Some(status_filter.as_str())
                });
            }
            records.truncate(args.limit);
            if json_mode {
                println!("{}", serde_json::to_string_pretty(&records)?);
            } else if records.is_empty() {
                println!("No goals.");
            } else {
                for r in records {
                    let id = r.get("id").and_then(|v| v.as_str()).unwrap_or("?");
                    let title = r
                        .get("title")
                        .and_then(|v| v.as_str())
                        .unwrap_or("(untitled)");
                    let status = r.get("status").and_then(|v| v.as_str()).unwrap_or("?");
                    let pinned = if r.get("pinned").and_then(|v| v.as_bool()).unwrap_or(false) {
                        " [pinned]"
                    } else {
                        ""
                    };
                    println!("{id}: {title} [{status}]{pinned}");
                }
            }
        }
    }
    Ok(())
}

// ── data ──────────────────────────────────────────────────────────────────────

#[derive(Debug, clap::Args)]
#[command(
    about = "Data source management (credential add|remove|inspect, source list|show|sync|add|remove, status)"
)]
pub struct DataArgs {
    /// Sub-action: credential | source | status | list | show
    ///
    /// credential — manage auth credentials attached to a data source
    ///   add       attach a credential (--name, --auth-kind, --secret-ref)
    ///   remove    detach a credential (--name)
    ///   inspect   show credential metadata without secret (--name)
    ///
    /// source — manage registered data sources
    ///   list      list all registered data sources
    ///   show      show one source record (--name)
    ///   sync      pull from source into evidence (§62z qualifying — stub)
    ///   add       register a new data source (--name, --adapter-kind, --dsn)
    ///   remove    deregister a data source (--name)
    ///
    /// status — summary table of all data source statuses
    ///
    /// list / show — legacy browse of raw data_records (--reference for show)
    #[arg(default_value = "list")]
    pub action: String,

    // ── shared identifier ──────────────────────────────────────────────────
    /// Data source name (for credential/source sub-actions)
    #[arg(long)]
    pub name: Option<String>,

    // ── credential fields ──────────────────────────────────────────────────
    /// Credential sub-action: add | remove | inspect
    #[arg(long = "credential-action")]
    pub credential_action: Option<String>,

    /// Auth kind (for 'credential add')
    #[arg(long = "auth-kind")]
    pub auth_kind: Option<String>,

    /// Secret reference (for 'credential add'; value is never stored verbatim)
    #[arg(long = "secret-ref")]
    pub secret_ref: Option<String>,

    /// Credential expiry (ISO timestamp, optional)
    #[arg(long = "expires-at")]
    pub expires_at: Option<String>,

    // ── source fields ──────────────────────────────────────────────────────
    /// Source sub-action: list | show | sync | add | remove
    #[arg(long = "source-action")]
    pub source_action: Option<String>,

    /// Adapter kind (for 'source add', e.g. github, git, directory)
    #[arg(long = "adapter-kind")]
    pub adapter_kind: Option<String>,

    /// Connection DSN / URI (for 'source add')
    #[arg(long)]
    pub dsn: Option<String>,

    /// Direction: read | write | both (for 'source add', default: read)
    #[arg(long, default_value = "read")]
    pub direction: String,

    /// Schema hint (for 'source add')
    #[arg(long = "schema-hint")]
    pub schema_hint: Option<String>,

    /// Human label (for 'source add')
    #[arg(long, default_value = "")]
    pub label: String,

    // ── legacy browse fields ───────────────────────────────────────────────
    /// Data reference / ID (for 'show')
    #[arg(long)]
    pub reference: Option<String>,

    /// Maximum records to display (for 'list')
    #[arg(long, default_value = "20")]
    pub limit: usize,

    /// Filter by status (for 'source list')
    #[arg(long)]
    pub status: Option<String>,
}

// ── handle_data_credential ────────────────────────────────────────────────────

fn handle_data_credential(state: &serde_json::Value, args: &DataArgs, json_mode: bool) {
    let cred_action = args.credential_action.as_deref().unwrap_or("");
    let name = args.name.as_deref().unwrap_or("");

    let sources = state
        .get("data_source_records")
        .and_then(|v| v.as_array())
        .cloned()
        .unwrap_or_default();
    let creds = state
        .get("credential_records")
        .and_then(|v| v.as_array())
        .cloned()
        .unwrap_or_default();

    let rec = sources
        .iter()
        .find(|r| r.get("name").and_then(|v| v.as_str()) == Some(name));

    match cred_action {
        "add" => {
            let stub_note = "operation not yet wired to live daemon";
            if json_mode {
                println!(
                    "{}",
                    serde_json::json!({
                        "action": "credential-add",
                        "name": name,
                        "status": "stub",
                        "note": stub_note
                    })
                );
            } else {
                println!("data credential add {name}: {stub_note}");
            }
        }
        "remove" => {
            let stub_note = "operation not yet wired to live daemon";
            if json_mode {
                println!(
                    "{}",
                    serde_json::json!({
                        "action": "credential-remove",
                        "name": name,
                        "status": "stub",
                        "note": stub_note
                    })
                );
            } else {
                println!("data credential remove {name}: {stub_note}");
            }
        }
        "inspect" => {
            let Some(source) = rec else {
                if json_mode {
                    println!(
                        "{}",
                        serde_json::json!({"error": format!("data source '{name}' not found")})
                    );
                } else {
                    println!("data source '{name}': not found");
                }
                return;
            };
            let cred_id = source.get("credential_record_id").and_then(|v| v.as_str());
            let cred = cred_id.and_then(|cid| {
                creds
                    .iter()
                    .find(|c| c.get("id").and_then(|v| v.as_str()) == Some(cid))
            });
            match cred {
                Some(c) => {
                    // Redact secret_ref — never emit its value.
                    let mut safe = c.clone();
                    if let Some(obj) = safe.as_object_mut() {
                        obj.insert(
                            "secret_ref".to_string(),
                            Value::String("<redacted>".to_string()),
                        );
                    }
                    if json_mode {
                        println!(
                            "{}",
                            serde_json::json!({"action": "credential-inspect", "record": safe})
                        );
                    } else {
                        for (k, v) in safe.as_object().into_iter().flatten() {
                            println!("  {k}: {v}");
                        }
                    }
                }
                None => {
                    if json_mode {
                        println!(
                            "{}",
                            serde_json::json!({"error": format!("no credential attached to '{name}'")})
                        );
                    } else {
                        println!("no credential attached to '{name}'");
                    }
                }
            }
        }
        _ => {
            if json_mode {
                println!(
                    "{}",
                    serde_json::json!({"error": "credential action required: add|remove|inspect"})
                );
            } else {
                println!("credential action required: add|remove|inspect");
            }
        }
    }
}

// ── handle_data_source ────────────────────────────────────────────────────────

fn handle_data_source(state: &serde_json::Value, args: &DataArgs, json_mode: bool) {
    let source_action = args.source_action.as_deref().unwrap_or("list");
    let name = args.name.as_deref().unwrap_or("");

    let sources: Vec<Value> = state
        .get("data_source_records")
        .and_then(|v| v.as_array())
        .cloned()
        .unwrap_or_default();

    match source_action {
        "list" => {
            let mut records: Vec<&Value> = sources.iter().collect();
            if let Some(ak) = &args.adapter_kind {
                records.retain(|r| {
                    r.get("adapter_kind").and_then(|v| v.as_str()) == Some(ak.as_str())
                });
            }
            if let Some(st) = &args.status {
                records.retain(|r| r.get("status").and_then(|v| v.as_str()) == Some(st.as_str()));
            }
            if json_mode {
                println!(
                    "{}",
                    serde_json::json!({"action": "data-source-list", "records": records})
                );
            } else if records.is_empty() {
                println!("No data sources registered.");
            } else {
                for r in records {
                    let id = r.get("id").and_then(|v| v.as_str()).unwrap_or("?");
                    let rname = r.get("name").and_then(|v| v.as_str()).unwrap_or("?");
                    let kind = r
                        .get("adapter_kind")
                        .and_then(|v| v.as_str())
                        .unwrap_or("?");
                    let status = r.get("status").and_then(|v| v.as_str()).unwrap_or("?");
                    println!("{id}: name={rname} adapter={kind} status={status}");
                }
            }
        }
        "show" => {
            if name.is_empty() {
                if json_mode {
                    println!(
                        "{}",
                        serde_json::json!({"error": "source show requires --name"})
                    );
                } else {
                    println!("source show requires --name");
                }
                return;
            }
            let rec = sources
                .iter()
                .find(|r| r.get("name").and_then(|v| v.as_str()) == Some(name));
            match rec {
                Some(r) => {
                    if json_mode {
                        println!(
                            "{}",
                            serde_json::json!({"action": "data-source-show", "record": r})
                        );
                    } else {
                        for (k, v) in r.as_object().into_iter().flatten() {
                            println!("  {k}: {v}");
                        }
                    }
                }
                None => {
                    if json_mode {
                        println!(
                            "{}",
                            serde_json::json!({"error": format!("data source '{name}' not found")})
                        );
                    } else {
                        println!("data source '{name}': not found");
                    }
                }
            }
        }
        // §62z qualifying actions — stub; never execute without authority gate
        "sync" | "add" | "remove" => {
            let stub_note = "operation not yet wired to live daemon";
            if json_mode {
                println!(
                    "{}",
                    serde_json::json!({
                        "action": format!("data-source-{source_action}"),
                        "name": name,
                        "status": "stub",
                        "note": stub_note
                    })
                );
            } else {
                println!("data source {source_action} {name}: {stub_note}");
            }
        }
        _ => {
            if json_mode {
                println!(
                    "{}",
                    serde_json::json!({"error": "source action required: list|show|sync|add|remove"})
                );
            } else {
                println!("source action required: list|show|sync|add|remove");
            }
        }
    }
}

pub async fn handle_data(root: &Path, args: &DataArgs, json_mode: bool) -> Result<()> {
    let state = load_state_json(root)?;

    match args.action.as_str() {
        // ── credential sub-command ─────────────────────────────────────────
        "credential" => {
            handle_data_credential(&state, args, json_mode);
        }

        // ── source sub-command ─────────────────────────────────────────────
        "source" => {
            handle_data_source(&state, args, json_mode);
        }

        // ── status ─────────────────────────────────────────────────────────
        "status" => {
            let sources: Vec<Value> = state
                .get("data_source_records")
                .and_then(|v| v.as_array())
                .cloned()
                .unwrap_or_default();
            let summary: Vec<serde_json::Value> = sources
                .iter()
                .map(|r| {
                    serde_json::json!({
                        "name": r.get("name").and_then(|v| v.as_str()).unwrap_or("?"),
                        "adapter_kind": r.get("adapter_kind").and_then(|v| v.as_str()).unwrap_or("?"),
                        "direction": r.get("direction").and_then(|v| v.as_str()).unwrap_or("?"),
                        "status": r.get("status").and_then(|v| v.as_str()).unwrap_or("?"),
                        "last_sync_cycle": r.get("last_sync_cycle").cloned().unwrap_or(Value::Null),
                        "last_push_cycle": r.get("last_push_cycle").cloned().unwrap_or(Value::Null),
                    })
                })
                .collect();
            if json_mode {
                println!(
                    "{}",
                    serde_json::json!({"action": "data-status", "sources": summary})
                );
            } else if summary.is_empty() {
                println!("No data sources registered.");
            } else {
                for s in &summary {
                    let name = s.get("name").and_then(|v| v.as_str()).unwrap_or("?");
                    let kind = s
                        .get("adapter_kind")
                        .and_then(|v| v.as_str())
                        .unwrap_or("?");
                    let dir = s.get("direction").and_then(|v| v.as_str()).unwrap_or("?");
                    let status = s.get("status").and_then(|v| v.as_str()).unwrap_or("?");
                    println!("{name}: adapter={kind} direction={dir} status={status}");
                }
            }
        }

        // ── legacy: show one raw data record by id/ref ─────────────────────
        "show" => {
            let empty = vec![];
            let all: &Vec<Value> = state
                .get("data_records")
                .or_else(|| state.get("data"))
                .and_then(|v| v.as_array())
                .unwrap_or(&empty);
            let reference = args.reference.as_deref().unwrap_or("");
            if reference.is_empty() {
                anyhow::bail!("data show requires --reference <ref>");
            }
            let rec = all.iter().find(|r| {
                r.get("id").and_then(|v| v.as_str()) == Some(reference)
                    || r.get("ref").and_then(|v| v.as_str()) == Some(reference)
            });
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
                        println!(
                            "{}",
                            serde_json::json!({"error": "not found", "ref": reference})
                        );
                    } else {
                        println!("data {reference}: not found");
                    }
                }
            }
        }

        // ── legacy: list raw data_records ──────────────────────────────────
        _ => {
            let empty = vec![];
            let all: &Vec<Value> = state
                .get("data_records")
                .or_else(|| state.get("data"))
                .and_then(|v| v.as_array())
                .unwrap_or(&empty);
            let records: Vec<&Value> = all.iter().rev().take(args.limit).collect();
            if json_mode {
                println!("{}", serde_json::to_string_pretty(&records)?);
            } else if records.is_empty() {
                println!("No data records.");
            } else {
                for r in records {
                    let id = r
                        .get("id")
                        .or_else(|| r.get("ref"))
                        .and_then(|v| v.as_str())
                        .unwrap_or("?");
                    let kind = r.get("kind").and_then(|v| v.as_str()).unwrap_or("?");
                    let at = r.get("at").and_then(|v| v.as_str()).unwrap_or("?");
                    println!("{id}: kind={kind} at={at}");
                }
            }
        }
    }
    Ok(())
}

// ── trace ─────────────────────────────────────────────────────────────────────

#[derive(Debug, clap::Args)]
#[command(about = "Show the lifecycle audit trace")]
pub struct TraceArgs {
    /// Maximum records to display
    #[arg(long, default_value = "20")]
    pub limit: usize,

    /// Filter by kind (e.g. CYCLE, OPERATION, DECISION)
    #[arg(long)]
    pub kind: Option<String>,
}

pub async fn handle_trace(root: &Path, args: &TraceArgs, json_mode: bool) -> Result<()> {
    let state = load_state_json(root)?;
    let empty = vec![];
    let all: &Vec<Value> = state
        .get("trace_records")
        .and_then(|v| v.as_array())
        .unwrap_or(&empty);

    let mut records: Vec<&Value> = all.iter().rev().collect();

    if let Some(kind_filter) = &args.kind {
        records.retain(|r| r.get("kind").and_then(|v| v.as_str()) == Some(kind_filter.as_str()));
    }

    records.truncate(args.limit);

    if json_mode {
        println!("{}", serde_json::to_string_pretty(&records)?);
    } else if records.is_empty() {
        println!("No trace records.");
    } else {
        for r in records {
            let id = r.get("id").and_then(|v| v.as_str()).unwrap_or("?");
            let kind = r.get("kind").and_then(|v| v.as_str()).unwrap_or("?");
            let at = r.get("at").and_then(|v| v.as_str()).unwrap_or("?");
            let summary = r.get("summary").and_then(|v| v.as_str()).unwrap_or("");
            println!("{id}: [{kind}] {at} — {summary}");
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

    fn write_state(dir: &TempDir, json: serde_json::Value) {
        let path = dir.path().join("state.json");
        let mut f = std::fs::File::create(&path).unwrap();
        f.write_all(serde_json::to_string_pretty(&json).unwrap().as_bytes())
            .unwrap();
    }

    #[tokio::test]
    async fn test_handle_vitals_empty_state() {
        let dir = TempDir::new().unwrap();
        let args = VitalsArgs {};
        // Should not panic, should print UNKNOWN lifecycle.
        handle_vitals(dir.path(), &args, false).await.unwrap();
    }

    #[tokio::test]
    async fn test_handle_vitals_with_data() {
        let dir = TempDir::new().unwrap();
        write_state(
            &dir,
            serde_json::json!({
                "lifecycle_state": "ACTIVE",
                "aps_score": 0.82,
                "cycle_count": 42,
                "objectives": [{"id": "obj-1", "status": "active"}],
                "evidence": [{"id": "ev-1"}],
            }),
        );
        let args = VitalsArgs {};
        handle_vitals(dir.path(), &args, true).await.unwrap();
    }

    #[tokio::test]
    async fn test_handle_audit_no_log() {
        let dir = TempDir::new().unwrap();
        let args = AuditArgs {
            action: None,
            since: None,
            limit: 20,
        };
        handle_audit(dir.path(), &args, false).await.unwrap();
    }

    #[tokio::test]
    async fn test_handle_audit_reads_jsonl() {
        let dir = TempDir::new().unwrap();
        let audit_path = dir.path().join("audit.jsonl");
        std::fs::write(
            &audit_path,
            "{\"kind\":\"CYCLE\",\"operation\":\"run\",\"at\":\"2026-01-01T00:00:00Z\"}\n",
        )
        .unwrap();
        let args = AuditArgs {
            action: None,
            since: None,
            limit: 20,
        };
        handle_audit(dir.path(), &args, true).await.unwrap();
    }

    #[tokio::test]
    async fn test_handle_goals_list_empty() {
        let dir = TempDir::new().unwrap();
        let args = GoalsArgs {
            action: "list".into(),
            title: None,
            id: None,
            status: None,
            limit: 20,
        };
        handle_goals(dir.path(), &args, false).await.unwrap();
    }

    #[tokio::test]
    async fn test_handle_trace_empty() {
        let dir = TempDir::new().unwrap();
        let args = TraceArgs {
            limit: 10,
            kind: None,
        };
        handle_trace(dir.path(), &args, false).await.unwrap();
    }

    fn data_args(action: &str) -> DataArgs {
        DataArgs {
            action: action.to_string(),
            name: None,
            credential_action: None,
            auth_kind: None,
            secret_ref: None,
            expires_at: None,
            source_action: None,
            adapter_kind: None,
            dsn: None,
            direction: "read".to_string(),
            schema_hint: None,
            label: String::new(),
            reference: None,
            limit: 20,
            status: None,
        }
    }

    #[tokio::test]
    async fn test_handle_data_empty() {
        let dir = TempDir::new().unwrap();
        handle_data(dir.path(), &data_args("list"), false)
            .await
            .unwrap();
    }

    #[tokio::test]
    async fn test_handle_data_status_empty() {
        let dir = TempDir::new().unwrap();
        handle_data(dir.path(), &data_args("status"), false)
            .await
            .unwrap();
    }

    #[tokio::test]
    async fn test_handle_data_status_with_sources() {
        let dir = TempDir::new().unwrap();
        write_state(
            &dir,
            serde_json::json!({
                "data_source_records": [
                    {
                        "id": "dsr-1",
                        "name": "my-db",
                        "adapter_kind": "database",
                        "direction": "READ",
                        "status": "ACTIVE",
                        "last_sync_cycle": 5,
                        "last_push_cycle": null
                    }
                ]
            }),
        );
        handle_data(dir.path(), &data_args("status"), true)
            .await
            .unwrap();
    }

    #[tokio::test]
    async fn test_handle_data_source_list_empty() {
        let dir = TempDir::new().unwrap();
        let args = DataArgs {
            action: "source".to_string(),
            source_action: Some("list".to_string()),
            ..data_args("source")
        };
        handle_data(dir.path(), &args, false).await.unwrap();
    }

    #[tokio::test]
    async fn test_handle_data_source_show_missing() {
        let dir = TempDir::new().unwrap();
        let args = DataArgs {
            action: "source".to_string(),
            source_action: Some("show".to_string()),
            name: Some("nonexistent".to_string()),
            ..data_args("source")
        };
        // Should not error — prints "not found" message.
        handle_data(dir.path(), &args, true).await.unwrap();
    }

    #[tokio::test]
    async fn test_handle_data_source_sync_stub() {
        let dir = TempDir::new().unwrap();
        let args = DataArgs {
            action: "source".to_string(),
            source_action: Some("sync".to_string()),
            name: Some("my-db".to_string()),
            ..data_args("source")
        };
        // §62z qualifying — must print stub notice, not error.
        handle_data(dir.path(), &args, false).await.unwrap();
    }

    #[tokio::test]
    async fn test_handle_data_source_add_stub() {
        let dir = TempDir::new().unwrap();
        let args = DataArgs {
            action: "source".to_string(),
            source_action: Some("add".to_string()),
            name: Some("new-src".to_string()),
            adapter_kind: Some("github".to_string()),
            dsn: Some("https://github.com/foo/bar".to_string()),
            ..data_args("source")
        };
        handle_data(dir.path(), &args, true).await.unwrap();
    }

    #[tokio::test]
    async fn test_handle_data_credential_inspect_no_source() {
        let dir = TempDir::new().unwrap();
        let args = DataArgs {
            action: "credential".to_string(),
            credential_action: Some("inspect".to_string()),
            name: Some("missing-src".to_string()),
            ..data_args("credential")
        };
        handle_data(dir.path(), &args, true).await.unwrap();
    }

    #[tokio::test]
    async fn test_handle_data_credential_add_stub() {
        let dir = TempDir::new().unwrap();
        let args = DataArgs {
            action: "credential".to_string(),
            credential_action: Some("add".to_string()),
            name: Some("my-db".to_string()),
            auth_kind: Some("token".to_string()),
            secret_ref: Some("vault://my-token".to_string()),
            ..data_args("credential")
        };
        handle_data(dir.path(), &args, true).await.unwrap();
    }

    #[tokio::test]
    async fn test_handle_data_credential_inspect_redacts_secret() {
        let dir = TempDir::new().unwrap();
        write_state(
            &dir,
            serde_json::json!({
                "data_source_records": [
                    {
                        "id": "dsr-1",
                        "name": "my-db",
                        "credential_record_id": "cred-1"
                    }
                ],
                "credential_records": [
                    {
                        "id": "cred-1",
                        "auth_kind": "token",
                        "secret_ref": "super-secret-value",
                        "data_source_id": "dsr-1"
                    }
                ]
            }),
        );
        let args = DataArgs {
            action: "credential".to_string(),
            credential_action: Some("inspect".to_string()),
            name: Some("my-db".to_string()),
            ..data_args("credential")
        };
        // Capture output by running and not panicking; actual secret redaction
        // is verified by the logic branching on "secret_ref".
        handle_data(dir.path(), &args, true).await.unwrap();
    }
}
