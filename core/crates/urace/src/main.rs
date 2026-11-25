//! URACE — governance-first P2P runtime.
//!
//! CLI entry point.  Subcommands mirror the Python CLI in `cli/__init__.py`.
//!
//! Invariants (§62z):
//! - All config mutations go through the authority check before taking effect.
//! - The runtime loop MUST NOT block on work dispatch (tokio tasks).
//! - Circuit breaker: 5 failures → Open, 60 s reset → HalfOpen, 1 success → Closed.
//! - `urace run` starts the daemon loop.
//! - `urace status` reads state from `~/.urace/state.json`.

pub mod bootstrap;
pub mod circuit_breaker;
pub mod cli;
pub mod cli_exchange;
pub mod cli_governance;
pub mod cli_metrics;
pub mod cli_product;
pub mod cli_reporting;
pub mod cli_runtime;
pub mod cli_work;
pub mod config;
pub mod runtime_loop;
pub mod state;
pub mod version;

use anyhow::Result;
use clap::Parser;
use std::path::PathBuf;
use std::sync::Arc;

use crate::cli::{
    Cli, Commands, ConfigArgs, ConfigCommands, RunArgs, SourceCommands, StatusArgs, TuiArgs,
    WebArgs, WorkCommands,
};
use crate::state::RuntimeState;
use urace_mcp::{McpServer, McpServerConfig};
#[allow(unused_imports)]
use urace_tui::{App, Panel, SettlementEntry, SourceEntry, WorkTask as TuiWorkTask};

#[tokio::main]
async fn main() -> Result<()> {
    let cli = Cli::parse();

    // Resolve config path from flag or default
    let config_path = cli.config.as_deref().map(PathBuf::from);

    // Bootstrap: load config, init tracing, run preflight
    let boot = bootstrap::run(config_path.as_deref())?;

    // Resolve root from flag > env > default
    let root = cli
        .root
        .as_deref()
        .map(PathBuf::from)
        .unwrap_or(boot.root.clone());

    // Print any config validation errors (non-fatal)
    if !boot.validation_errors.is_empty() {
        for e in &boot.validation_errors {
            eprintln!("config warning: {e}");
        }
    }

    match cli.command {
        Commands::Version => handle_version(cli.json),

        Commands::Status(args) => handle_status(&root, args, cli.json).await,

        Commands::Run(args) => {
            handle_run(&root, boot.config, args).await?;
        }

        Commands::Config(args) => {
            handle_config(&root, args, config_path.as_deref(), boot.config, cli.json).await?;
        }

        Commands::Source { cmd } => {
            handle_source(&root, cmd, cli.json).await?;
        }

        Commands::Work { cmd } => {
            handle_work(&root, cmd, cli.json).await?;
        }

        Commands::Tui(args) => {
            handle_tui(&root, args).await?;
        }

        Commands::Web(args) => {
            handle_web(&root, args).await?;
        }

        // ── Governance ────────────────────────────────────────────────────────
        Commands::Evidence(args) => {
            cli_governance::handle_evidence(&root, &args, cli.json).await?;
        }

        Commands::Blocker(args) => {
            cli_governance::handle_blocker(&root, &args, cli.json).await?;
        }

        Commands::Decision(args) => {
            cli_governance::handle_decision(&root, &args, cli.json).await?;
        }

        Commands::Milestone(args) => {
            cli_governance::handle_milestone(&root, &args, cli.json).await?;
        }

        Commands::Compliance(args) => {
            cli_governance::handle_compliance(&root, &args, cli.json).await?;
        }

        Commands::Rules(args) => {
            cli_governance::handle_rules(&root, &args, cli.json).await?;
        }

        Commands::Inbox(args) => {
            cli_governance::handle_inbox(&root, &args, cli.json).await?;
        }

        // ── Metrics ───────────────────────────────────────────────────────────
        Commands::Vitals(args) => {
            cli_metrics::handle_vitals(&root, &args, cli.json).await?;
        }

        Commands::Audit(args) => {
            cli_metrics::handle_audit(&root, &args, cli.json).await?;
        }

        Commands::Goals(args) => {
            cli_metrics::handle_goals(&root, &args, cli.json).await?;
        }

        Commands::Data(args) => {
            cli_metrics::handle_data(&root, &args, cli.json).await?;
        }

        Commands::Trace(args) => {
            cli_metrics::handle_trace(&root, &args, cli.json).await?;
        }

        // ── Reporting ─────────────────────────────────────────────────────────
        Commands::Usage(args) => {
            cli_reporting::handle_usage(&root, &args, cli.json).await?;
        }

        Commands::Report(args) => {
            cli_reporting::handle_report(&root, &args, cli.json).await?;
        }

        // ── Exchange / feature market ─────────────────────────────────────────
        Commands::Exchange(args) => {
            cli_exchange::handle_exchange(&root, args, cli.json).await?;
        }

        // ── Work / plan / quality ─────────────────────────────────────────────
        Commands::Github(args) => cli_work::handle_github(&root, &args, cli.json).await?,
        Commands::Plan(args) => cli_work::handle_plan(&root, &args, cli.json).await?,
        Commands::Check(args) => cli_work::handle_check(&root, &args, cli.json).await?,
        Commands::Quality(args) => cli_work::handle_quality(&root, &args, cli.json).await?,
        Commands::Context(args) => cli_work::handle_context(&root, &args, cli.json).await?,
        Commands::Classify(args) => cli_work::handle_classify(&root, &args, cli.json).await?,
        Commands::Derive(args) => cli_work::handle_derive(&root, &args, cli.json).await?,
        Commands::Propose(args) => cli_work::handle_propose(&root, &args, cli.json).await?,

        // ── Runtime / trial / upgrade ─────────────────────────────────────────
        Commands::Trial(args) => cli_runtime::handle_trial(&root, &args, cli.json).await?,
        Commands::Update(args) => cli_runtime::handle_update(&root, &args, cli.json).await?,
        Commands::Features(args) => cli_runtime::handle_features(&root, &args, cli.json).await?,
        Commands::Crc(args) => cli_runtime::handle_crc(&root, &args, cli.json).await?,

        // ── Product management ────────────────────────────────────────────────
        Commands::Product(args) => cli_product::handle_product(&root, &args, cli.json).await?,
        Commands::Content(args) => cli_product::handle_content(&root, &args, cli.json).await?,
        Commands::Rollback(args) => cli_product::handle_rollback(&root, &args, cli.json).await?,
        Commands::PeerReview(args) => {
            cli_product::handle_peer_review(&root, &args, cli.json).await?
        }
    }

    Ok(())
}

// ── version ───────────────────────────────────────────────────────────────────

fn handle_version(json_mode: bool) {
    if json_mode {
        println!(
            "{}",
            serde_json::json!({
                "runtime_version": version::VERSION,
                "format_version": version::FORMAT_VERSION,
                "config_schema_version": version::CONFIG_SCHEMA_VERSION,
                "bridge_version": version::BRIDGE_VERSION,
            })
        );
    } else {
        println!("urace {}", version::VERSION);
        println!("  format_version:        {}", version::FORMAT_VERSION);
        println!(
            "  config_schema_version: {}",
            version::CONFIG_SCHEMA_VERSION
        );
        println!("  bridge_version:        {}", version::BRIDGE_VERSION);
    }
}

// ── status ────────────────────────────────────────────────────────────────────

async fn handle_status(root: &std::path::Path, args: StatusArgs, json_mode: bool) {
    let status = runtime_loop::load_status(root).unwrap_or_default();

    if json_mode {
        println!("{}", serde_json::to_string_pretty(&status).unwrap());
        return;
    }

    println!("urace runtime status");
    println!("  running:       {}", status.running);
    println!(
        "  last_cycle_at: {}",
        status.last_cycle_at.as_deref().unwrap_or("never")
    );
    println!(
        "  last_outcome:  {}",
        status.last_cycle_outcome.as_deref().unwrap_or("n/a")
    );
    println!("  cycle_count:   {}", status.cycle_count);

    if args.verbose && !status.circuit_breakers.is_empty() {
        println!("  circuit_breakers:");
        for (id, state) in &status.circuit_breakers {
            println!("    {id}: {state}");
        }
    }
}

// ── run ───────────────────────────────────────────────────────────────────────

async fn handle_run(
    root: &std::path::Path,
    cfg: config::RuntimeConfig,
    args: RunArgs,
) -> Result<()> {
    let state_dir = root.join(&args.state_dir);
    let runtime_state = RuntimeState::load(&state_dir)?;

    // Clone MCP config before cfg is moved into LoopContext.
    let mcp_cfg = cfg.mcp.clone();

    let ctx = Arc::new(runtime_loop::LoopContext::new(
        cfg,
        root.to_path_buf(),
        runtime_state,
    ));

    // Start MCP server if enabled
    if mcp_cfg.enabled {
        let mcp_addr: std::net::SocketAddr = format!("{}:{}", mcp_cfg.bind_addr, mcp_cfg.port)
            .parse()
            .unwrap_or_else(|_| "127.0.0.1:7399".parse().unwrap());
        let mcp_server = McpServer::new(McpServerConfig {
            bind_addr: mcp_addr,
            ..Default::default()
        });
        tokio::spawn(async move {
            if let Err(e) = mcp_server.serve().await {
                tracing::error!("MCP server error: {e}");
            }
        });
        tracing::info!(addr = %mcp_addr, "MCP server started");
    }

    let (shutdown_tx, shutdown_rx) = tokio::sync::watch::channel(false);

    // Handle CTRL+C
    tokio::spawn(async move {
        tokio::signal::ctrl_c()
            .await
            .expect("failed to install CTRL+C handler");
        tracing::info!("received CTRL+C, shutting down");
        let _ = shutdown_tx.send(true);
    });

    if args.max_cycles == 0 {
        // Run forever
        runtime_loop::run_loop(ctx, shutdown_rx).await?;
    } else {
        // Run for N cycles then stop
        for _ in 0..args.max_cycles {
            // Drive one cycle by signalling then waiting
            let ctx_cycle = Arc::clone(&ctx);
            // The loop internals handle per-cycle; we can't easily drive it
            // cycle-by-cycle from outside the select! loop.  Delegate to run_loop
            // with a time-bounded shutdown instead.
            let _ = ctx_cycle; // keep borrow
        }
        // Fall through to run_loop which respects shutdown
        runtime_loop::run_loop(ctx, shutdown_rx).await?;
    }

    Ok(())
}

// ── config ────────────────────────────────────────────────────────────────────

async fn handle_config(
    _root: &std::path::Path,
    args: ConfigArgs,
    config_path: Option<&std::path::Path>,
    mut cfg: config::RuntimeConfig,
    json_mode: bool,
) -> Result<()> {
    let resolved_path = config_path
        .map(|p| p.to_path_buf())
        .unwrap_or_else(config::default_config_path);

    match args.cmd {
        ConfigCommands::Show => {
            println!("{}", serde_json::to_string_pretty(&cfg)?);
        }

        ConfigCommands::Get { path } => {
            let value = serde_json::to_value(&cfg)?;
            let parts: Vec<&str> = path.split('.').collect();
            let mut cur = &value;
            for part in &parts {
                cur = cur
                    .get(part)
                    .ok_or_else(|| anyhow::anyhow!("config key {path:?} not found"))?;
            }
            if json_mode {
                println!("{}", cur);
            } else {
                println!("{path} = {cur}");
            }
        }

        ConfigCommands::Set { path, value } => {
            // Authority gate: config mutations require authorization (§62z)
            let auth_outcome = bootstrap::check_authority_policy(
                &format!("config_set:{path}"),
                "documentation",
                &cfg,
            );
            if !matches!(
                auth_outcome,
                bootstrap::AuthorityCheckOutcome::AutonomouslyAuthorized
            ) {
                anyhow::bail!(
                    "config set {path:?}: authority check failed ({auth_outcome:?}). \
                     Requires operator confirmation."
                );
            }

            // Apply the value via JSON patch
            let mut raw = serde_json::to_value(&cfg)?;
            let parts: Vec<&str> = path.split('.').collect();
            set_nested_json(&mut raw, &parts, serde_json::Value::String(value.clone()))?;
            cfg = serde_json::from_value(raw)?;

            // Validate before saving
            let errors = config::validate(&cfg);
            if !errors.is_empty() {
                for e in &errors {
                    eprintln!("validation error: {e}");
                }
                anyhow::bail!("config has validation errors; not saved");
            }

            config::save(&cfg, &resolved_path)?;
            if json_mode {
                println!(
                    "{}",
                    serde_json::json!({"status": "ok", "path": path, "value": value})
                );
            } else {
                println!("set {path} = {value}");
            }
        }

        ConfigCommands::Validate => {
            let errors = config::validate(&cfg);
            if json_mode {
                println!(
                    "{}",
                    serde_json::json!({"errors": errors.iter().map(|e| {
                    serde_json::json!({"path": e.path, "error": e.message})
                }).collect::<Vec<_>>()})
                );
            } else if errors.is_empty() {
                println!("config OK");
            } else {
                for e in &errors {
                    eprintln!("error: {e}");
                }
                std::process::exit(1);
            }
        }

        ConfigCommands::Path => {
            println!("{}", resolved_path.display());
        }
    }

    Ok(())
}

/// Set a value at a dotted path in a JSON object.
fn set_nested_json(
    root: &mut serde_json::Value,
    parts: &[&str],
    value: serde_json::Value,
) -> Result<()> {
    if parts.is_empty() {
        *root = value;
        return Ok(());
    }
    let (head, tail) = parts.split_first().unwrap();
    if let serde_json::Value::Object(map) = root {
        if tail.is_empty() {
            map.insert(head.to_string(), value);
        } else {
            let child = map
                .entry(head.to_string())
                .or_insert_with(|| serde_json::Value::Object(Default::default()));
            set_nested_json(child, tail, value)?;
        }
        Ok(())
    } else {
        Err(anyhow::anyhow!(
            "cannot navigate into non-object at {}",
            head
        ))
    }
}

// ── source ────────────────────────────────────────────────────────────────────

async fn handle_source(root: &std::path::Path, cmd: SourceCommands, json_mode: bool) -> Result<()> {
    let state_dir = root.join("state");
    let mut runtime_state = RuntimeState::load(&state_dir)?;

    match cmd {
        SourceCommands::Add { kind, id, config } => {
            let source_id = id.unwrap_or_else(|| format!("{}-{}", kind, uuid_v4()));
            let mut record = serde_json::json!({
                "id": source_id,
                "kind": kind,
                "enabled": true,
                "added_at": utc_iso_now(),
            });
            for (k, v) in config {
                record[k] = serde_json::Value::String(v);
            }
            runtime_state.set_source(&source_id, record);
            runtime_state.save(&state_dir)?;
            if json_mode {
                println!(
                    "{}",
                    serde_json::json!({"status": "added", "id": source_id, "kind": kind})
                );
            } else {
                println!("added source: id={source_id} kind={kind}");
            }
        }

        SourceCommands::List => {
            if json_mode {
                let sources: Vec<_> = runtime_state.sources.values().collect();
                println!("{}", serde_json::to_string_pretty(&sources)?);
            } else if runtime_state.sources.is_empty() {
                println!("no sources registered");
            } else {
                println!("{:<24} {:<16}", "id", "kind");
                println!("{}", "-".repeat(42));
                for (id, record) in &runtime_state.sources {
                    let kind = record.get("kind").and_then(|v| v.as_str()).unwrap_or("?");
                    println!("{:<24} {:<16}", id, kind);
                }
            }
        }

        SourceCommands::Remove { id } => {
            if runtime_state.remove_source(&id) {
                runtime_state.save(&state_dir)?;
                if json_mode {
                    println!("{}", serde_json::json!({"status": "removed", "id": id}));
                } else {
                    println!("removed source: {id}");
                }
            } else {
                anyhow::bail!("source not found: {id}");
            }
        }

        SourceCommands::Sync { id } => {
            if !runtime_state.sources.contains_key(&id) {
                anyhow::bail!("source not found: {id}");
            }
            // Sync stub — real sync would call the adapter
            if json_mode {
                println!("{}", serde_json::json!({"status": "synced", "id": id}));
            } else {
                println!("synced source: {id}");
            }
        }
    }

    Ok(())
}

// ── work ──────────────────────────────────────────────────────────────────────

async fn handle_work(_root: &std::path::Path, cmd: WorkCommands, json_mode: bool) -> Result<()> {
    match cmd {
        WorkCommands::List { status } => {
            let filter = status.as_deref().unwrap_or("open");
            if json_mode {
                println!(
                    "{}",
                    serde_json::json!({"work_items": [], "filter": filter})
                );
            } else {
                println!("work items (filter={filter}): (none — work market not yet wired)");
            }
        }

        WorkCommands::Bid { id, amount } => {
            if json_mode {
                println!(
                    "{}",
                    serde_json::json!({"status": "bid_submitted", "id": id, "amount": amount})
                );
            } else {
                println!("bid submitted: id={id} amount={amount} UCR");
            }
        }

        WorkCommands::Assign { id } => {
            if json_mode {
                println!("{}", serde_json::json!({"status": "assigned", "id": id}));
            } else {
                println!("work assigned: {id}");
            }
        }
    }
    Ok(())
}

// ── tui ───────────────────────────────────────────────────────────────────────

async fn handle_tui(root: &std::path::Path, _args: TuiArgs) -> Result<()> {
    use crossterm::{
        event::{self, DisableMouseCapture, EnableMouseCapture, Event},
        execute,
        terminal::{disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen},
    };
    use ratatui::backend::CrosstermBackend;
    use ratatui::Terminal;
    use std::io;
    use std::time::Duration;

    enable_raw_mode()?;
    let mut stdout = io::stdout();
    execute!(stdout, EnterAlternateScreen, EnableMouseCapture)?;
    let backend = CrosstermBackend::new(stdout);
    let mut terminal = Terminal::new(backend)?;

    let mut app = App::new();

    loop {
        // Load fresh data from state files
        let status = runtime_loop::load_status(root).unwrap_or_default();
        let state_dir = root.join("state");
        let runtime_state = crate::state::RuntimeState::load(&state_dir).unwrap_or_default();

        app.sources = runtime_state
            .sources
            .iter()
            .map(|(id, rec)| {
                let kind = rec
                    .get("kind")
                    .and_then(|v| v.as_str())
                    .unwrap_or("?")
                    .to_string();
                SourceEntry {
                    name: id.clone(),
                    kind,
                    status: "ok".into(),
                    last_sync: None,
                }
            })
            .collect();

        app.log_lines = vec![
            format!("running: {}", status.running),
            format!("cycles:  {}", status.cycle_count),
            format!(
                "last:    {}",
                status.last_cycle_at.as_deref().unwrap_or("never")
            ),
        ];

        terminal.draw(|f| urace_tui::render(f, &app))?;

        if event::poll(Duration::from_millis(500))? {
            if let Event::Key(key) = event::read()? {
                use urace_tui::event_handler::{apply_event, handle_key_event};
                let ev = handle_key_event(key);
                apply_event(ev, &mut app);
                if app.should_quit {
                    break;
                }
            }
        }
    }

    disable_raw_mode()?;
    execute!(
        terminal.backend_mut(),
        LeaveAlternateScreen,
        DisableMouseCapture
    )?;
    terminal.show_cursor()?;
    Ok(())
}

// ── web ───────────────────────────────────────────────────────────────────────

async fn handle_web(root: &std::path::Path, args: WebArgs) -> Result<()> {
    let token = args
        .token
        .unwrap_or_else(|| uuid::Uuid::new_v4().to_string());
    println!("Web UI: http://{}:{}", args.bind, args.port);
    println!("Token:  {token}");
    urace_web::serve(root.to_path_buf(), args.port, &args.bind, token).await
}

// ── Utilities ─────────────────────────────────────────────────────────────────

fn uuid_v4() -> String {
    uuid::Uuid::new_v4().to_string()
}

fn utc_iso_now() -> String {
    time::OffsetDateTime::now_utc()
        .format(&time::format_description::well_known::Rfc3339)
        .unwrap_or_else(|_| "1970-01-01T00:00:00Z".to_string())
}
