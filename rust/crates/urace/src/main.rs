//! URACE — governance-first P2P runtime.
//!
//! R-9 CLI entry point. Subcommands mirror the Python CLI in `cli/__init__.py`.
//! Full command dispatch is wired in R-9; this scaffold registers the top-level
//! parser and delegates to per-subcommand modules.

use anyhow::Result;
use clap::{Parser, Subcommand};
use tracing_subscriber::EnvFilter;

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
    },
    /// List registered sources
    List,
    /// Sync a source
    Sync {
        #[arg(long)]
        id: String,
    },
}

#[derive(Subcommand)]
enum LedgerCommands {
    /// Show balance for a peer
    Balance {
        #[arg(long)]
        peer_id: String,
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
        SourceCommands::Add { kind, id } => {
            println!("source add --kind {kind} --id {}", id.as_deref().unwrap_or("<auto>"));
            println!("(R-9 full dispatch: TODO)");
        }
        SourceCommands::List => {
            println!("sources: (R-9 full dispatch: TODO)");
        }
        SourceCommands::Sync { id } => {
            println!("source sync --id {id}");
            println!("(R-9 full dispatch: TODO)");
        }
    }
    Ok(())
}

fn handle_ledger(cmd: LedgerCommands) -> Result<()> {
    match cmd {
        LedgerCommands::Balance { peer_id } => {
            println!("balance for {peer_id}: (R-9 full dispatch: TODO)");
        }
        LedgerCommands::Verify { path } => {
            use urace_ledger::Journal;
            let j = Journal::open(&path, [0u8; 32])?;
            let entries = j.verify_integrity()?;
            println!("verified {} entries in {path}", entries.len());
        }
    }
    Ok(())
}

async fn handle_run(state_dir: &str) -> Result<()> {
    println!("urace run --state-dir {state_dir}");
    println!("(R-9 full runtime cycle: TODO)");
    Ok(())
}
