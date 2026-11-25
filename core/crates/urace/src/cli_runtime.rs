//! Runtime subcommand handlers for the `urace` CLI.
//!
//! Covers: trial, update, features, crc.
//!
//! All read operations work fully against `<root>/state/state.json` or
//! `<root>/state.json`.  Write/mutation operations that require a running
//! daemon print an informative stub message instead.

use anyhow::Result;
use serde_json::Value;
use std::path::Path;

use crate::cli_governance::load_state_json;

// ── trial ─────────────────────────────────────────────────────────────────────

#[derive(Debug, clap::Args)]
#[command(about = "Run qualification trial stub / show trial status from state")]
pub struct TrialArgs {
    /// Sub-action: status | run
    #[arg(default_value = "status")]
    pub action: String,
}

pub async fn handle_trial(root: &Path, args: &TrialArgs, json_mode: bool) -> Result<()> {
    let state = load_state_json(root)?;
    let empty = vec![];

    match args.action.as_str() {
        "run" => {
            eprintln!("not yet wired: trial harness not yet wired to Rust CLI");
            if json_mode {
                println!(
                    "{}",
                    serde_json::json!({
                        "status": "stub",
                        "note": "trial harness not yet wired; use `python3 -m urace trial run` for now"
                    })
                );
            } else {
                println!("trial harness not yet wired");
                println!("  use: python3 -m urace trial run");
            }
        }

        _ => {
            // status: show qualification scores from state.
            let trial_records: &Vec<Value> = state
                .get("trial_records")
                .and_then(|v| v.as_array())
                .unwrap_or(&empty);

            let scores = state.get("qualification_scores").cloned().unwrap_or_default();
            let lifecycle = state
                .get("lifecycle_state")
                .and_then(|v| v.as_str())
                .unwrap_or("UNKNOWN");

            if json_mode {
                println!(
                    "{}",
                    serde_json::json!({
                        "lifecycle_state": lifecycle,
                        "qualification_scores": scores,
                        "trial_record_count": trial_records.len(),
                    })
                );
            } else {
                println!("trial status");
                println!("  lifecycle:    {lifecycle}");
                println!("  trial records: {}", trial_records.len());
                if scores.is_null() {
                    println!("  qualification scores: (none)");
                } else {
                    for (k, v) in scores.as_object().into_iter().flatten() {
                        println!("  score/{k}: {v}");
                    }
                }
            }
        }
    }
    Ok(())
}

// ── update ────────────────────────────────────────────────────────────────────

#[derive(Debug, clap::Args)]
#[command(about = "Check for and apply runtime updates")]
pub struct UpdateArgs {
    /// Dry-run (show what would change without applying)
    #[arg(long)]
    pub dry_run: bool,

    /// Specific update source URL or path
    #[arg(long)]
    pub source: Option<String>,
}

pub async fn handle_update(root: &Path, args: &UpdateArgs, json_mode: bool) -> Result<()> {
    let state = load_state_json(root)?;

    let spec_version = state
        .get("spec_version")
        .and_then(|v| v.as_str())
        .unwrap_or("unknown");

    let pending_updates: usize = state
        .get("objectives")
        .and_then(|v| v.as_array())
        .map(|arr| {
            arr.iter()
                .filter(|o| {
                    o.get("update_candidate").is_some()
                        && o.get("status").and_then(|s| s.as_str())
                            == Some("awaiting_operator_decision")
                })
                .count()
        })
        .unwrap_or(0);

    eprintln!("not yet wired: update download/apply requires running daemon");

    let result = serde_json::json!({
        "current_spec_version": spec_version,
        "dry_run": args.dry_run,
        "source": args.source,
        "pending_updates": pending_updates,
        "note": "update check/apply not yet wired to Rust CLI; use `python3 -m urace update`"
    });

    if json_mode {
        println!("{}", serde_json::to_string_pretty(&result)?);
    } else {
        let dry_tag = if args.dry_run { " (dry-run)" } else { "" };
        println!("update{dry_tag}: current spec_version={spec_version}");
        println!("  pending updates: {pending_updates}");
        if let Some(src) = &args.source {
            println!("  source: {src}");
        }
        println!("  note: apply requires running daemon; use `python3 -m urace update`");
    }
    Ok(())
}

// ── features ──────────────────────────────────────────────────────────────────

#[derive(Debug, clap::Args)]
#[command(about = "Browse runtime features (list / summary / show)")]
pub struct FeaturesArgs {
    /// Sub-action: list | summary | show
    #[arg(default_value = "list")]
    pub action: String,

    /// Feature ID (for 'show')
    #[arg(long)]
    pub id: Option<String>,

    /// Filter by status
    #[arg(long)]
    pub status: Option<String>,

    /// Filter by tag
    #[arg(long)]
    pub tag: Option<String>,

    /// Maximum entries
    #[arg(long, default_value = "40")]
    pub limit: usize,
}

pub async fn handle_features(root: &Path, args: &FeaturesArgs, json_mode: bool) -> Result<()> {
    let state = load_state_json(root)?;
    let empty = vec![];

    let all: &Vec<Value> = state
        .get("runtime_features")
        .or_else(|| state.get("features"))
        .and_then(|v| v.as_array())
        .unwrap_or(&empty);

    match args.action.as_str() {
        "summary" => {
            // Count by status.
            let mut counts: std::collections::HashMap<String, usize> =
                std::collections::HashMap::new();
            for f in all.iter() {
                let status = f
                    .get("status")
                    .and_then(|v| v.as_str())
                    .unwrap_or("unknown")
                    .to_string();
                *counts.entry(status).or_default() += 1;
            }
            if json_mode {
                let obj: serde_json::Map<String, Value> = counts
                    .into_iter()
                    .map(|(k, v)| (k, serde_json::json!(v)))
                    .collect();
                println!("{}", serde_json::to_string_pretty(&obj)?);
            } else {
                let mut sorted: Vec<_> = counts.into_iter().collect();
                sorted.sort_by_key(|(k, _)| k.clone());
                for (s, c) in sorted {
                    println!("  {s:<14}{c}");
                }
            }
        }

        "show" => {
            let fid = args.id.as_deref().unwrap_or("");
            if fid.is_empty() {
                anyhow::bail!("features show requires --id <feature_id>");
            }
            let rec = all
                .iter()
                .find(|f| f.get("id").and_then(|v| v.as_str()) == Some(fid));
            match rec {
                Some(r) => {
                    if json_mode {
                        println!("{}", serde_json::to_string_pretty(r)?);
                    } else {
                        for (k, v) in r.as_object().into_iter().flatten() {
                            println!("  {k:<22}{v}");
                        }
                    }
                }
                None => {
                    if json_mode {
                        println!(
                            "{}",
                            serde_json::json!({"error": "not found", "id": fid})
                        );
                    } else {
                        println!("feature {fid}: not found");
                    }
                }
            }
        }

        _ => {
            // list
            let mut features: Vec<&Value> = all.iter().collect();
            if let Some(status_filter) = &args.status {
                features.retain(|f| {
                    f.get("status").and_then(|v| v.as_str()) == Some(status_filter.as_str())
                });
            }
            if let Some(tag_filter) = &args.tag {
                features.retain(|f| {
                    f.get("tags")
                        .and_then(|v| v.as_array())
                        .map(|arr| {
                            arr.iter()
                                .any(|t| t.as_str() == Some(tag_filter.as_str()))
                        })
                        .unwrap_or(false)
                });
            }
            features.truncate(args.limit);

            if json_mode {
                println!("{}", serde_json::to_string_pretty(&features)?);
            } else if features.is_empty() {
                println!("No runtime features found.");
            } else {
                println!(
                    "  {:<35} {:<12} {:<8} {}",
                    "id", "status", "coverage", "name"
                );
                println!("{}", "-".repeat(80));
                for f in features {
                    let id = f.get("id").and_then(|v| v.as_str()).unwrap_or("?");
                    let status = f.get("status").and_then(|v| v.as_str()).unwrap_or("?");
                    let coverage = f
                        .get("test_coverage")
                        .and_then(|v| v.as_str())
                        .unwrap_or("-");
                    let name = f.get("name").and_then(|v| v.as_str()).unwrap_or("?");
                    let blockers: String = f
                        .get("blockers")
                        .and_then(|v| v.as_array())
                        .filter(|a| !a.is_empty())
                        .map(|a| {
                            format!(
                                " [blockers: {}]",
                                a.iter()
                                    .filter_map(|x| x.as_str())
                                    .collect::<Vec<_>>()
                                    .join(",")
                            )
                        })
                        .unwrap_or_default();
                    println!(
                        "  {id:<35} {status:<12} {coverage:<8} {name}{blockers}"
                    );
                }
            }
        }
    }
    Ok(())
}

// ── crc ───────────────────────────────────────────────────────────────────────

#[derive(Debug, clap::Args)]
#[command(about = "Cognitive Resume Context (CRC) status / apply")]
pub struct CrcArgs {
    /// Sub-action: status | apply
    #[arg(default_value = "status")]
    pub action: String,
}

pub async fn handle_crc(root: &Path, args: &CrcArgs, json_mode: bool) -> Result<()> {
    let state = load_state_json(root)?;

    let crc = state.get("cognitive_resume_context").cloned().unwrap_or_default();
    let crc_version = crc
        .get("version")
        .and_then(|v| v.as_str())
        .unwrap_or("none");
    let crc_at = crc.get("generated_at").and_then(|v| v.as_str()).unwrap_or("?");

    match args.action.as_str() {
        "apply" => {
            eprintln!("not yet wired: crc apply requires running daemon");
            if json_mode {
                println!(
                    "{}",
                    serde_json::json!({
                        "status": "stub",
                        "note": "crc apply not yet wired to live daemon",
                        "crc_version": crc_version
                    })
                );
            } else {
                println!("crc apply: not yet wired to live daemon");
                println!("  crc version: {crc_version}");
            }
        }
        _ => {
            if json_mode {
                if crc.is_null() {
                    println!(
                        "{}",
                        serde_json::json!({"status": "no_crc", "note": "No CRC found in state"})
                    );
                } else {
                    println!("{}", serde_json::to_string_pretty(&crc)?);
                }
            } else {
                if crc.is_null() {
                    println!("crc: No CRC found in state");
                } else {
                    println!("crc status");
                    println!("  version:      {crc_version}");
                    println!("  generated_at: {crc_at}");
                    if let Some(summary) = crc.get("summary").and_then(|v| v.as_str()) {
                        let short: String = summary.chars().take(80).collect();
                        println!("  summary:      {short}");
                    }
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
    use tempfile::TempDir;

    fn write_state(dir: &TempDir, json: serde_json::Value) {
        let path = dir.path().join("state.json");
        std::fs::write(path, serde_json::to_string_pretty(&json).unwrap()).unwrap();
    }

    #[tokio::test]
    async fn test_trial_status_empty() {
        let dir = TempDir::new().unwrap();
        write_state(&dir, serde_json::json!({}));
        let args = TrialArgs { action: "status".into() };
        handle_trial(dir.path(), &args, false).await.unwrap();
    }

    #[tokio::test]
    async fn test_trial_run_stub() {
        let dir = TempDir::new().unwrap();
        write_state(&dir, serde_json::json!({}));
        let args = TrialArgs { action: "run".into() };
        handle_trial(dir.path(), &args, true).await.unwrap();
    }

    #[tokio::test]
    async fn test_update_dry_run() {
        let dir = TempDir::new().unwrap();
        write_state(&dir, serde_json::json!({"spec_version": "v1.2.3"}));
        let args = UpdateArgs { dry_run: true, source: None };
        handle_update(dir.path(), &args, true).await.unwrap();
    }

    #[tokio::test]
    async fn test_features_list_empty() {
        let dir = TempDir::new().unwrap();
        write_state(&dir, serde_json::json!({}));
        let args = FeaturesArgs {
            action: "list".into(),
            id: None,
            status: None,
            tag: None,
            limit: 40,
        };
        handle_features(dir.path(), &args, false).await.unwrap();
    }

    #[tokio::test]
    async fn test_features_summary() {
        let dir = TempDir::new().unwrap();
        write_state(
            &dir,
            serde_json::json!({
                "runtime_features": [
                    {"id": "feat-1", "name": "Alpha", "status": "active", "test_coverage": "90%"},
                    {"id": "feat-2", "name": "Beta", "status": "planned", "test_coverage": "0%"},
                ]
            }),
        );
        let args = FeaturesArgs {
            action: "summary".into(),
            id: None,
            status: None,
            tag: None,
            limit: 40,
        };
        handle_features(dir.path(), &args, true).await.unwrap();
    }

    #[tokio::test]
    async fn test_crc_status_empty() {
        let dir = TempDir::new().unwrap();
        write_state(&dir, serde_json::json!({}));
        let args = CrcArgs { action: "status".into() };
        handle_crc(dir.path(), &args, false).await.unwrap();
    }
}
