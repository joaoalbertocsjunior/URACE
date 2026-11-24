//! URACE — governance-first P2P runtime.
//!
//! R-9 CLI entry point. Subcommands mirror the Python CLI in `cli/__init__.py`.

pub mod state;

use anyhow::Result;
use clap::{Parser, Subcommand};
use std::path::Path;
use tracing_subscriber::EnvFilter;

use crate::state::RuntimeState;
use sources_lib::SourceRegistry;
use sources_lib::adapters::directory::DirectoryAdapter;
use urace_ledger::CreditLedger;

#[derive(Parser)]
#[command(name = "urace", version, about = "URACE P2P runtime")]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Source adapter management
    Source {
        #[command(subcommand)]
        cmd: SourceCommands,
    },
    /// Ledger inspection
    Ledger {
        #[command(subcommand)]
        cmd: LedgerCommands,
    },
    /// Run the runtime cycle
    Run {
        #[arg(long, default_value = "state")]
        state_dir: String,
    },
}

#[derive(Subcommand)]
enum SourceCommands {
    /// Add a source
    Add {
        #[arg(long)]
        kind: String,
        #[arg(long)]
        id: Option<String>,
        #[arg(long, default_value = "state")]
        state_dir: String,
    },
    /// List registered sources
    List {
        #[arg(long, default_value = "state")]
        state_dir: String,
    },
    /// Sync a source
    Sync {
        #[arg(long)]
        id: String,
        #[arg(long, default_value = "state")]
        state_dir: String,
    },
}

#[derive(Subcommand)]
enum LedgerCommands {
    /// Show balance for a peer
    Balance {
        #[arg(long)]
        peer_id: String,
        #[arg(long, default_value = "state")]
        state_dir: String,
    },
    /// Verify ledger integrity
    Verify {
        #[arg(long)]
        path: String,
    },
}

#[tokio::main]
async fn main() -> Result<()> {
    tracing_subscriber::fmt()
        .with_env_filter(EnvFilter::from_default_env())
        .init();

    let cli = Cli::parse();

    match cli.command {
        Commands::Source { cmd } => handle_source(cmd).await,
        Commands::Ledger { cmd } => handle_ledger(cmd),
        Commands::Run { state_dir } => handle_run(&state_dir).await,
    }
}

async fn handle_source(cmd: SourceCommands) -> Result<()> {
    match cmd {
        SourceCommands::Add { kind, id, state_dir } => {
            let state_dir = Path::new(&state_dir);
            let mut runtime_state = RuntimeState::load(state_dir)?;

            // Build a minimal registry to validate the kind and create the record.
            let registry = SourceRegistry::new();
            // Register built-in adapters.
            let _ = registry.register_kind("directory", DirectoryAdapter::new(1000));

            let config = std::collections::HashMap::new();
            match registry.add(&kind, id.as_deref(), config) {
                Ok(record) => {
                    println!("added source: id={} kind={}", record.id, record.kind);
                    runtime_state.set_source(&record.id, serde_json::to_value(&record)?);
                    runtime_state.save(state_dir)?;
                }
                Err(e) => {
                    println!("error adding source: {}", e);
                }
            }
        }
        SourceCommands::List { state_dir } => {
            let state_dir = Path::new(&state_dir);
            let runtime_state = RuntimeState::load(state_dir)?;
            if runtime_state.sources.is_empty() {
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
        SourceCommands::Sync { id, state_dir } => {
            let state_dir = Path::new(&state_dir);
            let runtime_state = RuntimeState::load(state_dir)?;
            if !runtime_state.sources.contains_key(&id) {
                println!("source '{}' not found in state", id);
                return Ok(());
            }
            println!("sync --id {}: (network sync not yet wired; source record loaded)", id);
        }
    }
    Ok(())
}

fn handle_ledger(cmd: LedgerCommands) -> Result<()> {
    match cmd {
        LedgerCommands::Balance { peer_id, state_dir } => {
            let state_dir = Path::new(&state_dir);
            let ledger_path = state_dir.join("ledger.jsonl");
            if !ledger_path.exists() {
                println!("balance for {}: 0 UCR (no ledger at {})", peer_id, ledger_path.display());
                return Ok(());
            }
            let ledger = CreditLedger::open(&ledger_path, [0u8; 32])?;
            let balance = ledger.balance(&peer_id)?;
            println!("balance for {}: {} UCR", peer_id, balance);
        }
        LedgerCommands::Verify { path } => {
            let j = urace_ledger::Journal::open(&path, [0u8; 32])?;
            let entries = j.verify_integrity()?;
            println!("verified {} entries in {}", entries.len(), path);
        }
    }
    Ok(())
}

async fn handle_run(state_dir: &str) -> Result<()> {
    let state_dir = Path::new(state_dir);
    let state = RuntimeState::load(state_dir)?;
    println!("urace run --state-dir {}", state_dir.display());
    println!(
        "loaded state: {} sources, {} constraints",
        state.sources.len(),
        state.constraints.len()
    );
    println!("runtime loop: (tokio event loop started, full P2P wiring pending)");
    // TODO(R-12+): wire full runtime cycle:
    //   - start KademliaTable + DiscoverySession
    //   - register sources from state
    //   - run VoteCollector + consensus loop
    //   - process executor submissions
    Ok(())
}
