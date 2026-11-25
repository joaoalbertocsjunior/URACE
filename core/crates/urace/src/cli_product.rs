//! Product subcommand handlers for the `urace` CLI.
//!
//! Covers: product, content, rollback, peer-review.
//!
//! All read operations work fully against `<root>/state/state.json` or
//! `<root>/state.json`.  Write/mutation operations that require a running
//! daemon print an informative stub message instead.

use anyhow::Result;
use serde_json::Value;
use std::path::Path;

use crate::cli_governance::load_state_json;

// ── product ───────────────────────────────────────────────────────────────────

#[derive(Debug, clap::Args)]
#[command(about = "Product registry management (list / show / create / activate / status)")]
pub struct ProductArgs {
    /// Sub-action: list | show | create | activate | status | switch | register
    #[arg(default_value = "list")]
    pub action: String,

    /// Product name or ID (for show / create / activate / switch)
    #[arg(long)]
    pub name: Option<String>,
}

pub async fn handle_product(root: &Path, args: &ProductArgs, json_mode: bool) -> Result<()> {
    let state = load_state_json(root)?;
    let config = load_config_json(root);
    let empty = vec![];

    match args.action.as_str() {
        "list" => {
            let registry: &Vec<Value> = config
                .get("product_registry")
                .and_then(|v| v.as_array())
                .unwrap_or(&empty);
            let active = config
                .get("active_product")
                .or_else(|| config.get("product"))
                .and_then(|v| v.as_str())
                .unwrap_or("");

            let onboard_records: &Vec<Value> = state
                .get("onboard_records")
                .and_then(|v| v.as_array())
                .unwrap_or(&empty);

            if json_mode {
                let entries: Vec<serde_json::Value> = registry
                    .iter()
                    .map(|e| {
                        let name = e.get("name").and_then(|v| v.as_str()).unwrap_or("");
                        let onboarded = onboard_records.iter().any(|r| {
                            r.get("product_name").and_then(|v| v.as_str()) == Some(name)
                                && r.get("superseded_at")
                                    .map(|v| v.is_null())
                                    .unwrap_or(true)
                        });
                        serde_json::json!({
                            "name": name,
                            "status": e.get("status").unwrap_or(&Value::String("ACTIVE".into())),
                            "active": name == active,
                            "registered_at": e.get("registered_at"),
                            "onboarded": onboarded,
                        })
                    })
                    .collect();
                println!("{}", serde_json::to_string_pretty(&entries)?);
            } else if registry.is_empty() {
                println!(
                    "No products registered. Use `urace product create <name>` to add one."
                );
            } else {
                for e in registry {
                    let name = e.get("name").and_then(|v| v.as_str()).unwrap_or("?");
                    let status = e
                        .get("status")
                        .and_then(|v| v.as_str())
                        .unwrap_or("ACTIVE");
                    let marker = if name == active { "* " } else { "  " };
                    let onboarded = onboard_records.iter().any(|r| {
                        r.get("product_name").and_then(|v| v.as_str()) == Some(name)
                            && r.get("superseded_at")
                                .map(|v| v.is_null())
                                .unwrap_or(true)
                    });
                    let onb_str = if onboarded { "onboarded" } else { "not onboarded" };
                    println!("{marker}{name} [{status}] {onb_str}");
                }
            }
        }

        "show" => {
            let name = args.name.as_deref().unwrap_or("");
            if name.is_empty() {
                anyhow::bail!("product show requires --name <name>");
            }
            let registry: &Vec<Value> = config
                .get("product_registry")
                .and_then(|v| v.as_array())
                .unwrap_or(&empty);
            let entry = registry
                .iter()
                .find(|e| e.get("name").and_then(|v| v.as_str()) == Some(name));
            match entry {
                Some(e) => {
                    if json_mode {
                        println!("{}", serde_json::to_string_pretty(e)?);
                    } else {
                        for (k, v) in e.as_object().into_iter().flatten() {
                            println!("  {k}: {v}");
                        }
                    }
                }
                None => {
                    if json_mode {
                        println!(
                            "{}",
                            serde_json::json!({"error": "not found", "name": name})
                        );
                    } else {
                        println!("product {name}: not found");
                    }
                }
            }
        }

        "status" => {
            let active = config
                .get("active_product")
                .or_else(|| config.get("product"))
                .and_then(|v| v.as_str())
                .unwrap_or("(none)");
            let lifecycle = state
                .get("lifecycle_state")
                .and_then(|v| v.as_str())
                .unwrap_or("UNKNOWN");
            let registry: &Vec<Value> = config
                .get("product_registry")
                .and_then(|v| v.as_array())
                .unwrap_or(&empty);
            let entry = registry
                .iter()
                .find(|e| e.get("name").and_then(|v| v.as_str()) == Some(active));

            if json_mode {
                println!(
                    "{}",
                    serde_json::json!({
                        "active_product": active,
                        "lifecycle_state": lifecycle,
                        "registry_entry": entry,
                    })
                );
            } else {
                println!("Active product: {active}");
                println!("Lifecycle:      {lifecycle}");
                match entry {
                    Some(e) => {
                        let status = e.get("status").and_then(|v| v.as_str()).unwrap_or("ACTIVE");
                        println!("Registry:       status={status}");
                    }
                    None => println!("Registry:       not registered"),
                }
            }
        }

        "create" => {
            let name = args.name.as_deref().unwrap_or("");
            if name.is_empty() {
                anyhow::bail!("product create requires --name <name>");
            }
            eprintln!("not yet wired: product create requires a running daemon");
            if json_mode {
                println!(
                    "{}",
                    serde_json::json!({
                        "status": "stub",
                        "name": name,
                        "note": "operation not yet wired to live daemon"
                    })
                );
            } else {
                println!("product create {name}: operation not yet wired to live daemon");
            }
        }

        "activate" => {
            let name = args.name.as_deref().unwrap_or("");
            if name.is_empty() {
                anyhow::bail!("product activate requires --name <name>");
            }
            eprintln!("not yet wired: product activate requires a running daemon");
            if json_mode {
                println!(
                    "{}",
                    serde_json::json!({
                        "status": "stub",
                        "name": name,
                        "note": "operation not yet wired to live daemon"
                    })
                );
            } else {
                println!("product activate {name}: operation not yet wired to live daemon");
            }
        }

        "switch" => {
            let name = args.name.as_deref().unwrap_or("");
            if name.is_empty() {
                anyhow::bail!("product switch requires --name <name>");
            }
            eprintln!("not yet wired: product switch requires a running daemon");
            if json_mode {
                println!(
                    "{}",
                    serde_json::json!({
                        "status": "stub",
                        "name": name,
                        "note": "operation not yet wired to live daemon"
                    })
                );
            } else {
                println!("product switch {name}: operation not yet wired to live daemon");
            }
        }

        other => {
            if json_mode {
                println!(
                    "{}",
                    serde_json::json!({"error": format!("unknown product action: {other}")})
                );
            } else {
                eprintln!("unknown product action: {other}");
            }
        }
    }
    Ok(())
}

// ── content ───────────────────────────────────────────────────────────────────

#[derive(Debug, clap::Args)]
#[command(about = "Content store management (list / show)")]
pub struct ContentArgs {
    /// Sub-action: list | show | ref
    #[arg(default_value = "list")]
    pub action: String,

    /// Content ref ID (for 'show')
    #[arg(long)]
    pub ref_id: Option<String>,

    /// Maximum entries
    #[arg(long, default_value = "20")]
    pub limit: usize,
}

pub async fn handle_content(root: &Path, args: &ContentArgs, json_mode: bool) -> Result<()> {
    let state = load_state_json(root)?;
    let empty = vec![];

    match args.action.as_str() {
        "show" => {
            let rid = args.ref_id.as_deref().unwrap_or("");
            if rid.is_empty() {
                anyhow::bail!("content show requires --ref-id <id>");
            }
            let refs: &Vec<Value> = state
                .get("content_refs")
                .or_else(|| state.get("content_store"))
                .and_then(|v| v.as_array())
                .unwrap_or(&empty);
            let rec = refs
                .iter()
                .find(|r| r.get("id").and_then(|v| v.as_str()) == Some(rid));
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
                            serde_json::json!({"error": format!("ref not found: {rid}")})
                        );
                    } else {
                        println!("content ref {rid}: not found");
                    }
                }
            }
        }

        _ => {
            // list
            let refs: &Vec<Value> = state
                .get("content_refs")
                .or_else(|| state.get("content_store"))
                .and_then(|v| v.as_array())
                .unwrap_or(&empty);
            let items: Vec<&Value> = refs.iter().take(args.limit).collect();
            if json_mode {
                println!("{}", serde_json::json!({"refs": items}));
            } else if items.is_empty() {
                println!("No content refs.");
            } else {
                for r in items {
                    let id = r.get("id").and_then(|v| v.as_str()).unwrap_or("?");
                    let kind = r.get("kind").and_then(|v| v.as_str()).unwrap_or("?");
                    let at = r.get("at").and_then(|v| v.as_str()).unwrap_or("?");
                    println!("{id}: kind={kind} at={at}");
                }
            }
        }
    }
    Ok(())
}

// ── rollback ──────────────────────────────────────────────────────────────────

#[derive(Debug, clap::Args)]
#[command(about = "Rollback to a stable snapshot")]
pub struct RollbackArgs {
    /// Target version / snapshot reference
    #[arg(long)]
    pub target: Option<String>,

    /// Dry-run (show what would be restored without applying)
    #[arg(long)]
    pub dry_run: bool,
}

pub async fn handle_rollback(root: &Path, args: &RollbackArgs, json_mode: bool) -> Result<()> {
    // Look for a stable snapshot manifest.
    let snap_dir = root.join("state").join("stable");
    let manifest_path = snap_dir.join("manifest.json");

    if !manifest_path.exists() {
        let msg = "no stable snapshot available; run a full cycle first";
        if json_mode {
            println!(
                "{}",
                serde_json::json!({"status": "ERROR", "error": msg})
            );
        } else {
            eprintln!("error: {msg}");
        }
        return Ok(());
    }

    let manifest_raw = std::fs::read_to_string(&manifest_path)
        .map_err(|e| anyhow::anyhow!("reading manifest: {e}"))?;
    let manifest: Value = serde_json::from_str(&manifest_raw)
        .map_err(|e| anyhow::anyhow!("parsing manifest: {e}"))?;

    let snap_files = manifest
        .get("files")
        .and_then(|v| v.as_object())
        .cloned()
        .unwrap_or_default();
    let accepted_at = manifest
        .get("accepted_at")
        .and_then(|v| v.as_str())
        .unwrap_or("unknown");

    let mut restores: Vec<serde_json::Value> = Vec::new();
    for (rel, _snap_hash) in &snap_files {
        let snap_src = snap_dir.join(rel);
        if !snap_src.exists() {
            restores.push(serde_json::json!({"file": rel, "status": "missing_in_snapshot"}));
            continue;
        }
        let live = root.join(rel);
        let status = if args.dry_run {
            "would_restore"
        } else {
            "restored"
        };
        if !args.dry_run {
            if let Some(parent) = live.parent() {
                std::fs::create_dir_all(parent).ok();
            }
            if let Ok(content) = std::fs::read_to_string(&snap_src) {
                std::fs::write(&live, content).ok();
            }
        }
        restores.push(serde_json::json!({"file": rel, "status": status}));
    }

    let result = serde_json::json!({
        "status": if args.dry_run { "DRY_RUN" } else { "OK" },
        "snapshot_at": accepted_at,
        "target": args.target,
        "files": restores
    });

    if json_mode {
        println!("{}", serde_json::to_string_pretty(&result)?);
    } else {
        let dry_tag = if args.dry_run { "[dry-run] " } else { "" };
        println!("{dry_tag}stable snapshot from {accepted_at}");
        for f in &restores {
            let file = f["file"].as_str().unwrap_or("?");
            let status = f["status"].as_str().unwrap_or("?");
            println!("  {status:<20} {file}");
        }
    }
    Ok(())
}

// ── peer-review ───────────────────────────────────────────────────────────────

#[derive(Debug, clap::Args)]
#[command(about = "Peer artifact review (list / evaluate / promote)")]
pub struct PeerReviewArgs {
    /// Sub-action: list | evaluate | promote
    #[arg(default_value = "list")]
    pub action: String,

    /// Bundle ID (for evaluate / promote)
    #[arg(long)]
    pub bundle_id: Option<String>,

    /// Maximum entries
    #[arg(long, default_value = "20")]
    pub limit: usize,
}

pub async fn handle_peer_review(root: &Path, args: &PeerReviewArgs, json_mode: bool) -> Result<()> {
    let state = load_state_json(root)?;
    let empty = vec![];

    match args.action.as_str() {
        "evaluate" | "promote" => {
            let bid = args.bundle_id.as_deref().unwrap_or("");
            if bid.is_empty() {
                anyhow::bail!("peer-review {} requires --bundle-id <id>", args.action);
            }
            eprintln!("not yet wired: peer-review {} requires running daemon", args.action);
            if json_mode {
                println!(
                    "{}",
                    serde_json::json!({
                        "status": "stub",
                        "bundle_id": bid,
                        "action": args.action,
                        "note": "operation not yet wired to live daemon"
                    })
                );
            } else {
                println!(
                    "peer-review {} {bid}: operation not yet wired to live daemon",
                    args.action
                );
            }
        }

        _ => {
            // list quarantined bundles from state.
            let bundles: Vec<&Value> = state
                .get("quarantined_bundles")
                .or_else(|| state.get("peer_artifacts"))
                .and_then(|v| v.as_array())
                .unwrap_or(&empty)
                .iter()
                .take(args.limit)
                .collect();

            if json_mode {
                println!("{}", serde_json::to_string_pretty(&bundles)?);
            } else if bundles.is_empty() {
                println!("  no quarantined peer artifacts");
            } else {
                println!(
                    "  {:<20} {:<20} {:>8}  sender",
                    "bundle_id", "feature", "bytes"
                );
                for b in bundles {
                    let bid = b
                        .get("bundle_id")
                        .and_then(|v| v.as_str())
                        .unwrap_or("?");
                    let feature = b
                        .get("feature")
                        .and_then(|v| v.as_str())
                        .unwrap_or("?");
                    let bytes = b
                        .get("artifact_bytes")
                        .and_then(|v| v.as_u64())
                        .unwrap_or(0);
                    let sender = b
                        .get("sender")
                        .and_then(|v| v.as_str())
                        .unwrap_or("?");
                    let bid_short: String = bid.chars().take(18).collect();
                    println!("  {bid_short:<20} {feature:<20} {bytes:>8}  {sender}");
                }
            }
        }
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

    fn write_config(dir: &TempDir, json: serde_json::Value) {
        let path = dir.path().join("config.json");
        std::fs::write(path, serde_json::to_string_pretty(&json).unwrap()).unwrap();
    }

    #[tokio::test]
    async fn test_product_list_empty() {
        let dir = TempDir::new().unwrap();
        write_state(dir, serde_json::json!({}));
        let args = ProductArgs {
            action: "list".into(),
            name: None,
        };
        handle_product(dir.path(), &args, false).await.unwrap();
    }

    #[tokio::test]
    async fn test_product_status() {
        let dir = TempDir::new().unwrap();
        write_state(
            dir,
            serde_json::json!({"lifecycle_state": "RUNNING"}),
        );
        write_config(
            dir,
            serde_json::json!({
                "active_product": "myapp",
                "product_registry": [{"name": "myapp", "status": "ACTIVE"}]
            }),
        );
        let args = ProductArgs {
            action: "status".into(),
            name: None,
        };
        handle_product(dir.path(), &args, true).await.unwrap();
    }

    #[tokio::test]
    async fn test_content_list_empty() {
        let dir = TempDir::new().unwrap();
        write_state(dir, serde_json::json!({}));
        let args = ContentArgs {
            action: "list".into(),
            ref_id: None,
            limit: 20,
        };
        handle_content(dir.path(), &args, false).await.unwrap();
    }

    #[tokio::test]
    async fn test_rollback_no_snapshot() {
        let dir = TempDir::new().unwrap();
        write_state(dir, serde_json::json!({}));
        let args = RollbackArgs {
            target: None,
            dry_run: true,
        };
        handle_rollback(dir.path(), &args, false).await.unwrap();
    }

    #[tokio::test]
    async fn test_peer_review_list_empty() {
        let dir = TempDir::new().unwrap();
        write_state(dir, serde_json::json!({}));
        let args = PeerReviewArgs {
            action: "list".into(),
            bundle_id: None,
            limit: 20,
        };
        handle_peer_review(dir.path(), &args, false).await.unwrap();
    }
}
