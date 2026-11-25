//! Reporting subcommand handlers for the `urace` CLI.
//!
//! Covers: usage, report.
//!
//! All reads work against `<root>/state.json` or `<root>/state/state.json`.
//! Audit log is read from `<root>/audit.jsonl`.

use anyhow::Result;
use serde_json::Value;
use std::path::Path;

use crate::cli_governance::load_state_json;

// ── usage ─────────────────────────────────────────────────────────────────────

#[derive(Debug, clap::Args)]
#[command(about = "Show executor usage patterns and summary")]
pub struct UsageArgs {
    /// Sub-action: patterns | summary
    #[arg(default_value = "summary")]
    pub action: String,

    /// Maximum entries to display per category
    #[arg(long, default_value = "20")]
    pub limit: usize,
}

pub async fn handle_usage(root: &Path, args: &UsageArgs, json_mode: bool) -> Result<()> {
    let state = load_state_json(root)?;

    match args.action.as_str() {
        "patterns" => {
            let executor_calls: Vec<&Value> = state
                .get("executor_state")
                .and_then(|s| s.get("executor_calls"))
                .and_then(|v| v.as_array())
                .map(|a| a.iter().collect())
                .unwrap_or_default();

            // Count by kind.
            let mut kind_counts: std::collections::HashMap<&str, u64> = Default::default();
            let mut freeform_tokens: u64 = 0;
            let mut executor_tokens: u64 = 0;

            for call in &executor_calls {
                let kind = call
                    .get("kind")
                    .or_else(|| call.get("scope"))
                    .and_then(|v| v.as_str())
                    .unwrap_or("unknown");
                *kind_counts.entry(kind).or_default() += 1;

                let usage = call.get("usage");
                let toks = usage
                    .and_then(|u| u.get("total_tokens"))
                    .and_then(|v| v.as_u64())
                    .unwrap_or(0);
                if kind == "freeform" || kind == "freeform-routing" {
                    freeform_tokens += toks;
                } else {
                    executor_tokens += toks;
                }
            }

            let mut top: Vec<(&&str, &u64)> = kind_counts.iter().collect();
            top.sort_by(|a, b| b.1.cmp(a.1));
            top.truncate(args.limit);

            // Goal outcomes.
            let operations: Vec<&Value> = state
                .get("operations")
                .and_then(|v| v.as_array())
                .map(|a| a.iter().collect())
                .unwrap_or_default();
            let mut goal_total: std::collections::HashMap<&str, u64> = Default::default();
            let mut goal_success: std::collections::HashMap<&str, u64> = Default::default();
            for op in &operations {
                let ref_key = op
                    .get("objective_reference")
                    .or_else(|| op.get("decision"))
                    .and_then(|v| v.as_str())
                    .unwrap_or("unknown");
                *goal_total.entry(ref_key).or_default() += 1;
                let status = op
                    .get("outcome")
                    .and_then(|o| o.get("status"))
                    .and_then(|v| v.as_str())
                    .unwrap_or("");
                if matches!(
                    status.to_ascii_lowercase().as_str(),
                    "verified" | "accepted"
                ) {
                    *goal_success.entry(ref_key).or_default() += 1;
                }
            }
            let mut goal_outcomes: Vec<serde_json::Value> = goal_total
                .iter()
                .map(|(g, t)| {
                    let success = goal_success.get(g).copied().unwrap_or(0);
                    let rate = if *t > 0 {
                        success as f64 / *t as f64
                    } else {
                        0.0
                    };
                    serde_json::json!({
                        "goal": g,
                        "success_rate": (rate * 1000.0).round() / 1000.0,
                        "total": t,
                    })
                })
                .collect();
            goal_outcomes.sort_by(|a, b| {
                b["total"]
                    .as_u64()
                    .unwrap_or(0)
                    .cmp(&a["total"].as_u64().unwrap_or(0))
            });
            goal_outcomes.truncate(args.limit);

            // Freeform cache stats.
            let freeform_calls: Vec<&Value> = executor_calls
                .iter()
                .filter(|c| {
                    c.get("kind")
                        .and_then(|v| v.as_str())
                        .map(|k| k == "freeform-routing")
                        .unwrap_or(false)
                })
                .copied()
                .collect();
            let freeform_total = freeform_calls.len() as u64;
            let freeform_cache_hits = freeform_calls
                .iter()
                .filter(|c| c.get("tokens").and_then(|v| v.as_u64()).unwrap_or(1) == 0)
                .count() as u64;
            let cache_hit_rate = if freeform_total > 0 {
                Value::from(
                    (freeform_cache_hits as f64 / freeform_total as f64 * 1000.0).round() / 1000.0,
                )
            } else {
                Value::Null
            };

            if json_mode {
                let top_json: Vec<serde_json::Value> = top
                    .iter()
                    .map(|(k, c)| serde_json::json!({"kind": k, "count": c}))
                    .collect();
                println!(
                    "{}",
                    serde_json::json!({
                        "status": "ok",
                        "top_commands": top_json,
                        "token_breakdown": {
                            "freeform_tokens": freeform_tokens,
                            "executor_tokens": executor_tokens,
                        },
                        "goal_outcomes": goal_outcomes,
                        "freeform_stats": {
                            "total_calls": freeform_total,
                            "cache_hits": freeform_cache_hits,
                            "cache_hit_rate": cache_hit_rate,
                        },
                    })
                );
            } else {
                println!("Top command kinds:");
                for (k, c) in &top {
                    println!("  {k:<30} {c}");
                }
                println!("Token breakdown:");
                println!("  freeform:  {freeform_tokens}");
                println!("  executor:  {executor_tokens}");
                println!(
                    "Freeform cache: {freeform_cache_hits}/{freeform_total} hits  rate={cache_hit_rate}"
                );
                if !goal_outcomes.is_empty() {
                    println!("Goal outcomes (top {}):", goal_outcomes.len());
                    for g in &goal_outcomes {
                        println!(
                            "  {}: success_rate={} total={}",
                            g["goal"], g["success_rate"], g["total"]
                        );
                    }
                }
            }
        }
        _ => {
            // summary
            let executor_calls: Vec<&Value> = state
                .get("executor_state")
                .and_then(|s| s.get("executor_calls"))
                .and_then(|v| v.as_array())
                .map(|a| a.iter().collect())
                .unwrap_or_default();
            let total_calls = executor_calls.len();
            let total_tokens: u64 = executor_calls
                .iter()
                .filter_map(|c| {
                    c.get("usage")
                        .and_then(|u| u.get("total_tokens"))
                        .and_then(|v| v.as_u64())
                })
                .sum();
            let lifecycle = state
                .get("lifecycle_state")
                .and_then(|v| v.as_str())
                .unwrap_or("UNKNOWN");
            let cycle_count = state
                .get("cycle_count")
                .and_then(|v| v.as_u64())
                .unwrap_or(0);

            if json_mode {
                println!(
                    "{}",
                    serde_json::json!({
                        "status": "ok",
                        "lifecycle_state": lifecycle,
                        "cycle_count": cycle_count,
                        "executor_calls": total_calls,
                        "total_tokens": total_tokens,
                    })
                );
            } else {
                println!("lifecycle_state:  {lifecycle}");
                println!("cycle_count:      {cycle_count}");
                println!("executor_calls:   {total_calls}");
                println!("total_tokens:     {total_tokens}");
            }
        }
    }
    Ok(())
}

// ── report ────────────────────────────────────────────────────────────────────

#[derive(Debug, clap::Args)]
#[command(about = "Generate or display runtime reports (vitals / cycle / audit)")]
pub struct ReportArgs {
    /// Sub-action: vitals | cycle | audit
    #[arg(default_value = "vitals")]
    pub action: String,
}

pub async fn handle_report(root: &Path, args: &ReportArgs, json_mode: bool) -> Result<()> {
    let state = load_state_json(root)?;

    match args.action.as_str() {
        "vitals" => {
            // Reuse vitals logic inline.
            let lifecycle = state
                .get("lifecycle_state")
                .and_then(|v| v.as_str())
                .unwrap_or("UNKNOWN");
            let aps_score = state.get("aps_score").cloned().unwrap_or(Value::Null);
            let cycle_count = state
                .get("cycle_count")
                .and_then(|v| v.as_u64())
                .unwrap_or(0);
            let objectives = state
                .get("objectives")
                .and_then(|v| v.as_array())
                .map(|a| a.len())
                .unwrap_or(0);
            let evidence = state
                .get("evidence")
                .and_then(|v| v.as_array())
                .map(|a| a.len())
                .unwrap_or(0);

            if json_mode {
                println!(
                    "{}",
                    serde_json::json!({
                        "report": "vitals",
                        "lifecycle_state": lifecycle,
                        "aps_score": aps_score,
                        "cycle_count": cycle_count,
                        "objectives": objectives,
                        "evidence": evidence,
                    })
                );
            } else {
                println!("=== Vitals Report ===");
                println!("lifecycle_state: {lifecycle}");
                println!("aps_score:       {aps_score}");
                println!("cycle_count:     {cycle_count}");
                println!("objectives:      {objectives}");
                println!("evidence:        {evidence}");
            }
        }
        "cycle" => {
            let cycle_count = state
                .get("cycle_count")
                .and_then(|v| v.as_u64())
                .unwrap_or(0);
            let last_cycle_at = state
                .get("last_cycle_at")
                .and_then(|v| v.as_str())
                .unwrap_or("never");
            let last_outcome = state
                .get("last_cycle_outcome")
                .and_then(|v| v.as_str())
                .unwrap_or("n/a");

            // Last few operations.
            let ops: Vec<&Value> = state
                .get("operations")
                .and_then(|v| v.as_array())
                .map(|a| a.iter().rev().take(5).collect())
                .unwrap_or_default();

            if json_mode {
                println!(
                    "{}",
                    serde_json::json!({
                        "report": "cycle",
                        "cycle_count": cycle_count,
                        "last_cycle_at": last_cycle_at,
                        "last_cycle_outcome": last_outcome,
                        "recent_operations": ops,
                    })
                );
            } else {
                println!("=== Cycle Report ===");
                println!("cycle_count:     {cycle_count}");
                println!("last_cycle_at:   {last_cycle_at}");
                println!("last_outcome:    {last_outcome}");
                if ops.is_empty() {
                    println!("recent_operations: (none)");
                } else {
                    println!("recent_operations:");
                    for op in ops {
                        let id = op.get("id").and_then(|v| v.as_str()).unwrap_or("?");
                        let status = op
                            .get("outcome")
                            .and_then(|o| o.get("status"))
                            .and_then(|v| v.as_str())
                            .unwrap_or("?");
                        let at = op.get("at").and_then(|v| v.as_str()).unwrap_or("?");
                        println!("  {id}: status={status} at={at}");
                    }
                }
            }
        }
        "audit" => {
            // Delegate to audit log.
            let candidates = [
                root.join("audit.jsonl"),
                root.join("state").join("audit.jsonl"),
            ];
            let audit_path = candidates.iter().find(|p| p.exists());
            if audit_path.is_none() {
                if json_mode {
                    println!(
                        "{}",
                        serde_json::json!({"report": "audit", "status": "no_audit_log"})
                    );
                } else {
                    println!("No audit log found.");
                }
                return Ok(());
            }
            let raw = std::fs::read_to_string(audit_path.unwrap())?;
            let records: Vec<Value> = raw
                .lines()
                .filter_map(|line| serde_json::from_str(line).ok())
                .collect();
            let total = records.len();
            let start = total.saturating_sub(20);
            let page = &records[start..];

            if json_mode {
                println!(
                    "{}",
                    serde_json::json!({
                        "report": "audit",
                        "records": page,
                        "total": total,
                    })
                );
            } else {
                println!("=== Audit Report === ({total} total, showing last 20)");
                for r in page {
                    let kind = r.get("kind").and_then(|v| v.as_str()).unwrap_or("?");
                    let op = r.get("operation").and_then(|v| v.as_str()).unwrap_or("?");
                    let at = r.get("at").and_then(|v| v.as_str()).unwrap_or("?");
                    println!("  {kind} | {op} | {at}");
                }
            }
        }
        other => {
            anyhow::bail!("unknown report action: {other}. Use: vitals | cycle | audit");
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
    async fn test_handle_usage_summary_empty() {
        let dir = TempDir::new().unwrap();
        let args = UsageArgs {
            action: "summary".into(),
            limit: 20,
        };
        handle_usage(dir.path(), &args, false).await.unwrap();
    }

    #[tokio::test]
    async fn test_handle_usage_patterns_empty() {
        let dir = TempDir::new().unwrap();
        let args = UsageArgs {
            action: "patterns".into(),
            limit: 10,
        };
        handle_usage(dir.path(), &args, true).await.unwrap();
    }

    #[tokio::test]
    async fn test_handle_report_vitals() {
        let dir = TempDir::new().unwrap();
        write_state(
            &dir,
            serde_json::json!({
                "lifecycle_state": "ACTIVE",
                "aps_score": 0.9,
                "cycle_count": 7,
            }),
        );
        let args = ReportArgs {
            action: "vitals".into(),
        };
        handle_report(dir.path(), &args, true).await.unwrap();
    }

    #[tokio::test]
    async fn test_handle_report_cycle() {
        let dir = TempDir::new().unwrap();
        let args = ReportArgs {
            action: "cycle".into(),
        };
        handle_report(dir.path(), &args, false).await.unwrap();
    }

    #[tokio::test]
    async fn test_handle_report_audit_no_log() {
        let dir = TempDir::new().unwrap();
        let args = ReportArgs {
            action: "audit".into(),
        };
        handle_report(dir.path(), &args, false).await.unwrap();
    }

    #[tokio::test]
    async fn test_handle_report_unknown_action() {
        let dir = TempDir::new().unwrap();
        let args = ReportArgs {
            action: "unknown".into(),
        };
        let result = handle_report(dir.path(), &args, false).await;
        assert!(result.is_err());
    }
}
