//! Exchange / feature-market CLI commands.
//!
//! Ports the Python modules:
//!   - runtime/urace/exchange_cli.py       (status, list, show, rank, reputation, ledger, settle, asset)
//!   - runtime/urace/exchange_cli_market.py (ask, fill, cancel, momentum)
//!   - runtime/urace/exchange_cli_network.py (peers, discover)
//!
//! Read-only commands parse `state/state.json` (or `state.json`).
//! Mutation commands (ask, fill, cancel, settle) return an informative
//! unavailability JSON — the market RPC is not yet wired to the daemon.

use anyhow::Result;
use clap::{Args, Subcommand};
use serde_json::Value;
use std::path::Path;

// ── Top-level args ────────────────────────────────────────────────────────────

#[derive(Debug, Args)]
pub struct ExchangeArgs {
    #[command(subcommand)]
    pub cmd: ExchangeCommands,
}

// ── Subcommands ───────────────────────────────────────────────────────────────

#[derive(Debug, Subcommand)]
pub enum ExchangeCommands {
    /// Show exchange peer count + feature count from state
    Status {
        #[arg(long)]
        json: bool,
    },

    /// List features from state (feature_catalog or features key)
    List {
        #[arg(long)]
        json: bool,
    },

    /// Show a specific feature atom by ID
    Show {
        atom_id: String,
        #[arg(long)]
        json: bool,
    },

    /// Rank features by quality / adoption score
    Rank {
        #[arg(long, default_value = "10")]
        limit: usize,
        #[arg(long)]
        json: bool,
    },

    /// Peer reputation summary
    Reputation {
        #[arg(long)]
        json: bool,
    },

    /// Ledger run summary from state
    Ledger {
        #[arg(long)]
        json: bool,
    },

    /// Settlement status (EVM/Lightning stub)
    Settle {
        #[arg(long)]
        json: bool,
    },

    /// Asset registry operations
    Asset {
        #[command(subcommand)]
        cmd: AssetCommands,
    },

    /// Place an ask order (market RPC stub)
    Ask {
        atom_id: String,
        #[arg(long)]
        price: u64,
        #[arg(long)]
        json: bool,
    },

    /// Fill an order (market RPC stub)
    Fill {
        order_id: String,
        #[arg(long)]
        json: bool,
    },

    /// Cancel an order (market RPC stub)
    Cancel {
        order_id: String,
        #[arg(long)]
        json: bool,
    },

    /// Market momentum metrics from state
    Momentum {
        #[arg(long)]
        json: bool,
    },

    /// P2P peers for exchange
    Peers {
        #[command(subcommand)]
        cmd: PeersCommands,
    },

    /// Trigger peer discovery (stub)
    Discover {
        #[arg(long)]
        json: bool,
    },
}

// ── Asset sub-commands ────────────────────────────────────────────────────────

#[derive(Debug, Subcommand)]
pub enum AssetCommands {
    /// List all assets in the registry
    List {
        #[arg(long)]
        json: bool,
    },

    /// Show a specific asset by ID
    Show {
        id: String,
        #[arg(long)]
        json: bool,
    },
}

// ── Peers sub-commands ────────────────────────────────────────────────────────

#[derive(Debug, Subcommand)]
pub enum PeersCommands {
    /// List known exchange peers
    List {
        #[arg(long)]
        json: bool,
    },

    /// Connect to a peer by address
    Connect {
        addr: String,
        #[arg(long)]
        json: bool,
    },
}

// ── State loader ──────────────────────────────────────────────────────────────

/// Load `state/state.json` (or `state.json`) under `root`.
/// Returns an empty JSON object on failure rather than hard-erroring — read
/// commands degrade gracefully when the daemon has not yet written state.
fn load_state_json(root: &Path) -> Value {
    let candidates = [root.join("state/state.json"), root.join("state.json")];
    for p in &candidates {
        if let Ok(s) = std::fs::read_to_string(p) {
            if let Ok(v) = serde_json::from_str::<Value>(&s) {
                return v;
            }
        }
    }
    Value::Object(Default::default())
}

/// Load `exchange/config.json` (policy.json) under `root`.
fn load_exchange_config(root: &Path) -> Value {
    let candidates = [
        root.join("exchange/config.json"),
        root.join("exchange/policy.json"),
    ];
    for p in &candidates {
        if let Ok(s) = std::fs::read_to_string(p) {
            if let Ok(v) = serde_json::from_str::<Value>(&s) {
                return v;
            }
        }
    }
    Value::Object(Default::default())
}

// ── Handler entry point ───────────────────────────────────────────────────────

pub async fn handle_exchange(root: &Path, args: ExchangeArgs, global_json: bool) -> Result<()> {
    match args.cmd {
        ExchangeCommands::Status { json } => handle_status(root, json || global_json),
        ExchangeCommands::List { json } => handle_list(root, json || global_json),
        ExchangeCommands::Show { atom_id, json } => {
            handle_show(root, &atom_id, json || global_json)
        }
        ExchangeCommands::Rank { limit, json } => handle_rank(root, limit, json || global_json),
        ExchangeCommands::Reputation { json } => handle_reputation(root, json || global_json),
        ExchangeCommands::Ledger { json } => handle_ledger(root, json || global_json),
        ExchangeCommands::Settle { json } => handle_settle(json || global_json),
        ExchangeCommands::Asset { cmd } => handle_asset(root, cmd, global_json),
        ExchangeCommands::Ask {
            atom_id,
            price,
            json,
        } => handle_ask(&atom_id, price, json || global_json),
        ExchangeCommands::Fill { order_id, json } => handle_fill(&order_id, json || global_json),
        ExchangeCommands::Cancel { order_id, json } => {
            handle_cancel(&order_id, json || global_json)
        }
        ExchangeCommands::Momentum { json } => handle_momentum(root, json || global_json),
        ExchangeCommands::Peers { cmd } => handle_peers(root, cmd, global_json),
        ExchangeCommands::Discover { json } => handle_discover(json || global_json),
    }
}

// ── status ────────────────────────────────────────────────────────────────────

fn handle_status(root: &Path, json_mode: bool) -> Result<()> {
    let state = load_state_json(root);
    let xcfg = load_exchange_config(root);

    let peer_count = xcfg
        .get("peers")
        .and_then(|p| p.as_object())
        .map(|m| m.len())
        .unwrap_or(0);

    // Feature count: check feature_catalog first, then features key in state
    let feature_count = state
        .get("feature_catalog")
        .and_then(|v| v.as_array())
        .map(|a| a.len())
        .or_else(|| {
            state
                .get("features")
                .and_then(|v| v.as_object())
                .map(|m| m.len())
        })
        .unwrap_or(0);

    let enabled = xcfg
        .get("enabled")
        .and_then(|v| v.as_bool())
        .unwrap_or(false);

    if json_mode {
        println!(
            "{}",
            serde_json::json!({
                "status": "ok",
                "exchange_enabled": enabled,
                "peer_count": peer_count,
                "feature_count": feature_count,
            })
        );
    } else {
        println!("exchange status");
        println!("  enabled:       {enabled}");
        println!("  peer_count:    {peer_count}");
        println!("  feature_count: {feature_count}");
    }

    Ok(())
}

// ── list ──────────────────────────────────────────────────────────────────────

fn handle_list(root: &Path, json_mode: bool) -> Result<()> {
    let state = load_state_json(root);

    // Prefer feature_catalog array, fall back to features object keys
    let features: Vec<Value> =
        if let Some(arr) = state.get("feature_catalog").and_then(|v| v.as_array()) {
            arr.clone()
        } else if let Some(map) = state.get("features").and_then(|v| v.as_object()) {
            map.iter()
                .map(|(k, v)| {
                    let mut entry = serde_json::json!({"feature_id": k});
                    if let Some(obj) = v.as_object() {
                        for (fk, fv) in obj {
                            entry[fk] = fv.clone();
                        }
                    }
                    entry
                })
                .collect()
        } else {
            vec![]
        };

    if json_mode {
        println!(
            "{}",
            serde_json::json!({"features": features, "count": features.len()})
        );
    } else if features.is_empty() {
        println!("no features found in state");
    } else {
        println!("{:<36} {:<20} tags", "feature_id", "kind");
        println!("{}", "-".repeat(72));
        for f in &features {
            let id = f.get("feature_id").and_then(|v| v.as_str()).unwrap_or("?");
            let kind = f
                .get("kind")
                .or_else(|| f.get("kind_label"))
                .and_then(|v| v.as_str())
                .unwrap_or("");
            let tags = f
                .get("tags")
                .and_then(|v| v.as_array())
                .map(|a| {
                    a.iter()
                        .filter_map(|t| t.as_str())
                        .collect::<Vec<_>>()
                        .join(",")
                })
                .unwrap_or_default();
            println!("{:<36} {:<20} {}", id, kind, tags);
        }
    }

    Ok(())
}

// ── show ──────────────────────────────────────────────────────────────────────

fn handle_show(root: &Path, atom_id: &str, json_mode: bool) -> Result<()> {
    let state = load_state_json(root);

    // Try feature_catalog array first
    let feature = state
        .get("feature_catalog")
        .and_then(|v| v.as_array())
        .and_then(|arr| {
            arr.iter().find(|f| {
                f.get("feature_id")
                    .and_then(|v| v.as_str())
                    .map(|id| id == atom_id)
                    .unwrap_or(false)
            })
        })
        .cloned()
        // Fall back to features object
        .or_else(|| {
            state
                .get("features")
                .and_then(|v| v.as_object())
                .and_then(|m| m.get(atom_id))
                .map(|v| {
                    let mut entry = serde_json::json!({"feature_id": atom_id});
                    if let Some(obj) = v.as_object() {
                        for (k, fv) in obj {
                            entry[k] = fv.clone();
                        }
                    }
                    entry
                })
        });

    match feature {
        Some(f) => {
            if json_mode {
                println!("{}", serde_json::to_string_pretty(&f)?);
            } else {
                println!("feature: {atom_id}");
                if let Some(obj) = f.as_object() {
                    for (k, v) in obj {
                        println!("  {k}: {v}");
                    }
                }
            }
        }
        None => {
            if json_mode {
                println!(
                    "{}",
                    serde_json::json!({"status": "not_found", "atom_id": atom_id})
                );
            } else {
                println!("feature not found: {atom_id}");
            }
        }
    }

    Ok(())
}

// ── rank ──────────────────────────────────────────────────────────────────────

fn handle_rank(root: &Path, limit: usize, json_mode: bool) -> Result<()> {
    let state = load_state_json(root);

    // Collect features with their scores
    let mut features: Vec<(f64, Value)> = vec![];

    // Pull from feature_catalog
    if let Some(arr) = state.get("feature_catalog").and_then(|v| v.as_array()) {
        for f in arr {
            let score = f
                .get("kpi_score")
                .or_else(|| f.get("quality_score"))
                .or_else(|| f.get("score"))
                .and_then(|v| v.as_f64())
                .unwrap_or(0.0);
            let adoptions = f
                .get("adoption_count")
                .and_then(|v| v.as_f64())
                .unwrap_or(0.0);
            features.push((score + adoptions * 0.001, f.clone()));
        }
    } else if let Some(map) = state.get("features").and_then(|v| v.as_object()) {
        for (k, v) in map {
            let score = v
                .get("kpi_score")
                .or_else(|| v.get("quality_score"))
                .or_else(|| v.get("score"))
                .and_then(|s| s.as_f64())
                .unwrap_or(0.0);
            let mut entry = serde_json::json!({"feature_id": k});
            if let Some(obj) = v.as_object() {
                for (fk, fv) in obj {
                    entry[fk] = fv.clone();
                }
            }
            features.push((score, entry));
        }
    }

    // Sort descending by score
    features.sort_by(|a, b| b.0.partial_cmp(&a.0).unwrap_or(std::cmp::Ordering::Equal));
    features.truncate(limit);

    let ranked: Vec<Value> = features.into_iter().map(|(_, f)| f).collect();

    if json_mode {
        println!(
            "{}",
            serde_json::json!({"ranked": ranked, "count": ranked.len(), "limit": limit})
        );
    } else if ranked.is_empty() {
        println!("no features to rank");
    } else {
        println!("{:<4} {:<36} score", "rank", "feature_id");
        println!("{}", "-".repeat(60));
        for (i, f) in ranked.iter().enumerate() {
            let id = f.get("feature_id").and_then(|v| v.as_str()).unwrap_or("?");
            let score = f
                .get("kpi_score")
                .or_else(|| f.get("quality_score"))
                .or_else(|| f.get("score"))
                .and_then(|v| v.as_f64())
                .unwrap_or(0.0);
            println!("{:<4} {:<36} {:.3}", i + 1, id, score);
        }
    }

    Ok(())
}

// ── reputation ────────────────────────────────────────────────────────────────

fn handle_reputation(root: &Path, json_mode: bool) -> Result<()> {
    let state = load_state_json(root);
    let xcfg = load_exchange_config(root);

    // Collect peer reputation entries from state or exchange config
    let peers_val = state
        .get("peers")
        .or_else(|| xcfg.get("peers"))
        .cloned()
        .unwrap_or(Value::Object(Default::default()));

    let summary: Vec<Value> = if let Some(map) = peers_val.as_object() {
        map.iter()
            .map(|(peer_id, v)| {
                let rep = v.get("reputation").and_then(|r| r.as_f64()).unwrap_or(0.0);
                serde_json::json!({
                    "peer_id": peer_id,
                    "reputation": rep,
                    "blocked": v.get("blocked").and_then(|b| b.as_bool()).unwrap_or(false),
                })
            })
            .collect()
    } else {
        vec![]
    };

    if json_mode {
        println!(
            "{}",
            serde_json::json!({"status": "ok", "peers": summary, "count": summary.len()})
        );
    } else if summary.is_empty() {
        println!("no peer reputation data in state");
    } else {
        println!("{:<42} {:>10}  blocked", "peer_id", "reputation");
        println!("{}", "-".repeat(60));
        for p in &summary {
            let id = p.get("peer_id").and_then(|v| v.as_str()).unwrap_or("?");
            let rep = p.get("reputation").and_then(|v| v.as_f64()).unwrap_or(0.0);
            let blocked = p.get("blocked").and_then(|v| v.as_bool()).unwrap_or(false);
            println!("{:<42} {:>10.3}  {}", id, rep, blocked);
        }
    }

    Ok(())
}

// ── ledger ────────────────────────────────────────────────────────────────────

fn handle_ledger(root: &Path, json_mode: bool) -> Result<()> {
    let state = load_state_json(root);

    let ledger = state.get("ledger").cloned().unwrap_or_else(|| {
        serde_json::json!({
            "total_events": 0,
            "baseline_grant_units": 0,
            "peers": {},
        })
    });

    if json_mode {
        println!("{}", serde_json::to_string_pretty(&ledger)?);
    } else {
        let total = ledger
            .get("total_events")
            .and_then(|v| v.as_u64())
            .unwrap_or(0);
        let grant = ledger
            .get("baseline_grant_units")
            .and_then(|v| v.as_u64())
            .unwrap_or(0);
        let peers = ledger
            .get("peers")
            .and_then(|v| v.as_object())
            .map(|m| m.len())
            .unwrap_or(0);
        println!("ledger summary");
        println!("  total_events:          {total}");
        println!("  baseline_grant_units:  {grant}");
        println!("  peers_with_balance:    {peers}");
    }

    Ok(())
}

// ── settle ────────────────────────────────────────────────────────────────────

/// EVM/Lightning settlement is a stub — returns unavailability info.
fn handle_settle(json_mode: bool) -> Result<()> {
    let out = serde_json::json!({
        "status": "unavailable",
        "reason": "market RPC not wired to daemon",
        "note": "EVM settlement is deferred; eth_settlement_adapter.py is a stub",
    });
    if json_mode {
        println!("{}", out);
    } else {
        println!(
            "settlement: {} — {}",
            out["status"].as_str().unwrap_or(""),
            out["note"].as_str().unwrap_or("")
        );
    }
    Ok(())
}

// ── asset ─────────────────────────────────────────────────────────────────────

fn handle_asset(root: &Path, cmd: AssetCommands, global_json: bool) -> Result<()> {
    let state = load_state_json(root);
    let assets_val = state
        .get("assets")
        .cloned()
        .unwrap_or(Value::Object(Default::default()));

    match cmd {
        AssetCommands::List { json } => {
            let json_mode = json || global_json;
            let assets: Vec<Value> = if let Some(map) = assets_val.as_object() {
                map.iter()
                    .map(|(id, v)| {
                        let mut entry = serde_json::json!({"asset_id": id});
                        if let Some(obj) = v.as_object() {
                            for (k, av) in obj {
                                entry[k] = av.clone();
                            }
                        }
                        entry
                    })
                    .collect()
            } else if let Some(arr) = assets_val.as_array() {
                arr.clone()
            } else {
                vec![]
            };

            if json_mode {
                println!(
                    "{}",
                    serde_json::json!({"assets": assets, "count": assets.len()})
                );
            } else if assets.is_empty() {
                println!("no assets in registry");
            } else {
                println!("{:<36} kind", "asset_id");
                println!("{}", "-".repeat(50));
                for a in &assets {
                    let id = a.get("asset_id").and_then(|v| v.as_str()).unwrap_or("?");
                    let kind = a.get("kind").and_then(|v| v.as_str()).unwrap_or("");
                    println!("{:<36} {}", id, kind);
                }
            }
        }

        AssetCommands::Show { id, json } => {
            let json_mode = json || global_json;
            let asset = assets_val
                .as_object()
                .and_then(|m| m.get(&id))
                .cloned()
                .or_else(|| {
                    assets_val.as_array().and_then(|arr| {
                        arr.iter()
                            .find(|a| {
                                a.get("asset_id")
                                    .or_else(|| a.get("id"))
                                    .and_then(|v| v.as_str())
                                    .map(|aid| aid == id)
                                    .unwrap_or(false)
                            })
                            .cloned()
                    })
                });

            match asset {
                Some(a) => {
                    if json_mode {
                        println!("{}", serde_json::to_string_pretty(&a)?);
                    } else {
                        println!("asset: {id}");
                        if let Some(obj) = a.as_object() {
                            for (k, v) in obj {
                                println!("  {k}: {v}");
                            }
                        }
                    }
                }
                None => {
                    if json_mode {
                        println!(
                            "{}",
                            serde_json::json!({"status": "not_found", "asset_id": id})
                        );
                    } else {
                        println!("asset not found: {id}");
                    }
                }
            }
        }
    }

    Ok(())
}

// ── ask ───────────────────────────────────────────────────────────────────────

fn handle_ask(atom_id: &str, price: u64, json_mode: bool) -> Result<()> {
    let out = serde_json::json!({
        "status": "unavailable",
        "reason": "market RPC not wired to daemon",
        "atom_id": atom_id,
        "price_ucr": price,
    });
    if json_mode {
        println!("{}", out);
    } else {
        println!("ask {atom_id} @ {price} UCR: unavailable — market not yet wired");
    }
    Ok(())
}

// ── fill ──────────────────────────────────────────────────────────────────────

fn handle_fill(order_id: &str, json_mode: bool) -> Result<()> {
    let out = serde_json::json!({
        "status": "unavailable",
        "reason": "market RPC not wired to daemon",
        "order_id": order_id,
    });
    if json_mode {
        println!("{}", out);
    } else {
        println!("fill {order_id}: unavailable — market not yet wired");
    }
    Ok(())
}

// ── cancel ────────────────────────────────────────────────────────────────────

fn handle_cancel(order_id: &str, json_mode: bool) -> Result<()> {
    let out = serde_json::json!({
        "status": "unavailable",
        "reason": "market RPC not wired to daemon",
        "order_id": order_id,
    });
    if json_mode {
        println!("{}", out);
    } else {
        println!("cancel {order_id}: unavailable — market not yet wired");
    }
    Ok(())
}

// ── momentum ──────────────────────────────────────────────────────────────────

fn handle_momentum(root: &Path, json_mode: bool) -> Result<()> {
    let state = load_state_json(root);

    // Pull velocity block from state if present (written by daemon market stats)
    let velocity = state
        .get("market")
        .and_then(|m| m.get("velocity"))
        .or_else(|| state.get("velocity"))
        .cloned()
        .unwrap_or(Value::Object(Default::default()));

    let trend = velocity
        .get("trend")
        .and_then(|v| v.as_str())
        .unwrap_or("unknown");
    let trend_delta = velocity
        .get("trend_delta_pct")
        .and_then(|v| v.as_f64())
        .unwrap_or(0.0);
    let mint_events = velocity
        .get("mint_events")
        .and_then(|v| v.as_u64())
        .unwrap_or(0);
    let total_recent = velocity
        .get("total_recent_events")
        .and_then(|v| v.as_u64())
        .unwrap_or(0);

    if json_mode {
        println!(
            "{}",
            serde_json::json!({
                "status": "ok",
                "trend": trend,
                "trend_delta_pct": trend_delta,
                "mint_events": mint_events,
                "total_recent_events": total_recent,
                "velocity": velocity,
            })
        );
    } else {
        println!("market momentum");
        println!("  trend:              {trend}");
        println!("  trend_delta_pct:    {trend_delta:.1}");
        println!("  mint_events:        {mint_events}");
        println!("  total_recent_events:{total_recent}");
    }

    Ok(())
}

// ── peers ─────────────────────────────────────────────────────────────────────

fn handle_peers(root: &Path, cmd: PeersCommands, global_json: bool) -> Result<()> {
    let xcfg = load_exchange_config(root);

    match cmd {
        PeersCommands::List { json } => {
            let json_mode = json || global_json;
            let peers: Vec<Value> = xcfg
                .get("peers")
                .and_then(|p| p.as_object())
                .map(|map| {
                    map.iter()
                        .map(|(id, v)| {
                            let mut entry = serde_json::json!({"peer_id": id});
                            if let Some(obj) = v.as_object() {
                                for (k, pv) in obj {
                                    entry[k] = pv.clone();
                                }
                            }
                            entry
                        })
                        .collect()
                })
                .unwrap_or_default();

            if json_mode {
                println!(
                    "{}",
                    serde_json::json!({"peers": peers, "count": peers.len()})
                );
            } else if peers.is_empty() {
                println!("no exchange peers known");
            } else {
                println!("{:<42} {:<30} blocked", "peer_id", "endpoint");
                println!("{}", "-".repeat(80));
                for p in &peers {
                    let id = p.get("peer_id").and_then(|v| v.as_str()).unwrap_or("?");
                    let ep = p.get("endpoint").and_then(|v| v.as_str()).unwrap_or("");
                    let blocked = p.get("blocked").and_then(|v| v.as_bool()).unwrap_or(false);
                    println!("{:<42} {:<30} {}", id, ep, blocked);
                }
            }
        }

        PeersCommands::Connect { addr, json } => {
            let json_mode = json || global_json;
            // Connection is a daemon-side action; return stub until RPC wired
            let out = serde_json::json!({
                "status": "unavailable",
                "reason": "market RPC not wired to daemon",
                "addr": addr,
            });
            if json_mode {
                println!("{}", out);
            } else {
                println!("connect {addr}: unavailable — market RPC not yet wired to daemon");
            }
        }
    }

    Ok(())
}

// ── discover ──────────────────────────────────────────────────────────────────

fn handle_discover(json_mode: bool) -> Result<()> {
    let out = serde_json::json!({
        "status": "unavailable",
        "reason": "market RPC not wired to daemon",
        "note": "peer discovery requires a running daemon with P2P enabled",
    });
    if json_mode {
        println!("{}", out);
    } else {
        println!(
            "discover: unavailable — {}",
            out["note"].as_str().unwrap_or("")
        );
    }
    Ok(())
}

// ── Tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use clap::{CommandFactory, Parser};

    // Build a minimal CLI wrapper so clap can verify the structure.
    #[derive(clap::Parser)]
    struct TestCli {
        #[command(subcommand)]
        cmd: TestCommands,
    }

    #[derive(clap::Subcommand)]
    enum TestCommands {
        Exchange(ExchangeArgs),
    }

    #[test]
    fn exchange_args_debug_assert() {
        TestCli::command().debug_assert();
    }

    #[test]
    fn exchange_status_parses() {
        let cli = TestCli::try_parse_from(["t", "exchange", "status"]).unwrap();
        assert!(matches!(
            cli.cmd,
            TestCommands::Exchange(ExchangeArgs {
                cmd: ExchangeCommands::Status { .. }
            })
        ));
    }

    #[test]
    fn exchange_ask_parses() {
        let cli = TestCli::try_parse_from(["t", "exchange", "ask", "feat-001", "--price", "500"])
            .unwrap();
        if let TestCommands::Exchange(ExchangeArgs {
            cmd: ExchangeCommands::Ask { atom_id, price, .. },
        }) = cli.cmd
        {
            assert_eq!(atom_id, "feat-001");
            assert_eq!(price, 500);
        } else {
            panic!("expected exchange ask");
        }
    }

    #[test]
    fn exchange_rank_default_limit() {
        let cli = TestCli::try_parse_from(["t", "exchange", "rank"]).unwrap();
        if let TestCommands::Exchange(ExchangeArgs {
            cmd: ExchangeCommands::Rank { limit, .. },
        }) = cli.cmd
        {
            assert_eq!(limit, 10);
        } else {
            panic!("expected exchange rank");
        }
    }

    #[test]
    fn exchange_peers_list_parses() {
        let cli = TestCli::try_parse_from(["t", "exchange", "peers", "list"]).unwrap();
        assert!(matches!(
            cli.cmd,
            TestCommands::Exchange(ExchangeArgs {
                cmd: ExchangeCommands::Peers {
                    cmd: PeersCommands::List { .. }
                }
            })
        ));
    }

    #[test]
    fn load_state_json_missing_returns_empty_object() {
        let tmp = std::env::temp_dir().join("urace_test_missing_state_1234");
        let v = load_state_json(&tmp);
        assert!(v.is_object());
        assert_eq!(v.as_object().unwrap().len(), 0);
    }
}
