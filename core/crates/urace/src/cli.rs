//! `clap`-based CLI definition for the `urace` binary.
//!
//! Subcommands mirror the Python CLI in `runtime/urace/cli/__init__.py`.
//!
//! Subcommands:
//!   run        — start the daemon runtime loop
//!   status     — read state from ~/.urace/state.json
//!   config     — get/set/validate config keys
//!   version    — print version info
//!   source     — add / list / remove sources
//!   work       — list / bid / assign work items
//!   tui        — launch the interactive TUI dashboard
//!   evidence   — browse evidence records
//!   blocker    — manage blockers
//!   decision   — browse decision records
//!   milestone  — browse milestones
//!   compliance — browse compliance records
//!   rules      — browse governance rules
//!   inbox      — manage patch proposal inbox
//!   vitals     — show runtime vitals
//!   audit      — browse audit log
//!   goals      — manage goals / objectives
//!   data       — browse data records
//!   trace      — show lifecycle audit trace
//!   usage      — show executor usage patterns
//!   report     — generate runtime reports
//!   exchange   — feature market commands (status, list, show, rank, ask, …)

use clap::{Args, Parser, Subcommand};

pub use crate::cli_exchange::{AssetCommands, ExchangeArgs, ExchangeCommands, PeersCommands};
pub use crate::cli_governance::{
    BlockerArgs, ComplianceArgs, DecisionArgs, EvidenceArgs, InboxArgs, MilestoneArgs, RulesArgs,
};
pub use crate::cli_metrics::{AuditArgs, DataArgs, GoalsArgs, TraceArgs, VitalsArgs};
pub use crate::cli_product::{ContentArgs, PeerReviewArgs, ProductArgs, RollbackArgs};
pub use crate::cli_reporting::{ReportArgs, UsageArgs};
pub use crate::cli_runtime::{CrcArgs, FeaturesArgs, TrialArgs, UpdateArgs};
pub use crate::cli_work::{
    CheckArgs, ClassifyArgs, ContextArgs, DeriveArgs, GithubArgs, PlanArgs, ProposeArgs,
    QualityArgs,
};

// ── Top-level CLI ─────────────────────────────────────────────────────────────

#[derive(Parser)]
#[command(
    name = "urace",
    version = crate::version::VERSION,
    about = "URACE — governance-first P2P runtime for autonomous product improvement"
)]
pub struct Cli {
    /// Override config file path (default: ~/.urace/config.json)
    #[arg(long, global = true)]
    pub config: Option<String>,

    /// Override runtime root directory (default: ~/.urace)
    #[arg(long, global = true)]
    pub root: Option<String>,

    /// Output in JSON (machine-readable)
    #[arg(long, global = true, short = 'j')]
    pub json: bool,

    #[command(subcommand)]
    pub command: Commands,
}

// ── Subcommands ───────────────────────────────────────────────────────────────

#[derive(Subcommand)]
pub enum Commands {
    /// Start the autonomous daemon loop
    Run(RunArgs),

    /// Show runtime status (reads ~/.urace/state.json)
    Status(StatusArgs),

    /// Get, set, or validate configuration keys
    Config(ConfigArgs),

    /// Print version information
    Version,

    /// Source adapter management (add / list / remove)
    Source {
        #[command(subcommand)]
        cmd: SourceCommands,
    },

    /// Work market management (list / bid / assign)
    Work {
        #[command(subcommand)]
        cmd: WorkCommands,
    },

    /// Launch the TUI dashboard (requires a running daemon)
    Tui(TuiArgs),

    /// Start the web dashboard (axum + HTMX)
    Web(WebArgs),

    // ── Governance ────────────────────────────────────────────────────────────
    /// Browse evidence records
    Evidence(EvidenceArgs),

    /// Manage blockers (list / resolve)
    Blocker(BlockerArgs),

    /// Browse decision records
    Decision(DecisionArgs),

    /// Browse milestones
    Milestone(MilestoneArgs),

    /// Browse compliance records
    Compliance(ComplianceArgs),

    /// Browse governance rules
    Rules(RulesArgs),

    /// Manage patch proposal inbox (list / apply / reject / count)
    Inbox(InboxArgs),

    // ── Metrics ───────────────────────────────────────────────────────────────
    /// Show runtime vitals (lifecycle, APS score, cycle count, counts)
    Vitals(VitalsArgs),

    /// Browse the audit log
    Audit(AuditArgs),

    /// Manage goals / objectives
    Goals(GoalsArgs),

    /// Browse data records
    Data(DataArgs),

    /// Show the lifecycle audit trace
    Trace(TraceArgs),

    // ── Reporting ─────────────────────────────────────────────────────────────
    /// Show executor usage patterns and summary
    Usage(UsageArgs),

    /// Generate or display runtime reports (vitals / cycle / audit)
    Report(ReportArgs),

    // ── Exchange / feature market ─────────────────────────────────────────────
    /// Feature market commands (status, list, show, rank, ask, fill, …)
    Exchange(ExchangeArgs),

    // ── Work / plan / quality ─────────────────────────────────────────────────
    /// GitHub integration (status / connect / push-goals / trigger-workflow)
    Github(GithubArgs),
    /// Work planning (show / create / status)
    Plan(PlanArgs),
    /// Run pre-flight checks
    Check(CheckArgs),
    /// Show or run quality gates
    Quality(QualityArgs),
    /// Show cognitive context summary
    Context(ContextArgs),
    /// Classify a work item or string
    Classify(ClassifyArgs),
    /// Derive system manifest from patterns
    Derive(DeriveArgs),
    /// Propose a change (requires authority)
    Propose(ProposeArgs),

    // ── Runtime / trial / upgrade ─────────────────────────────────────────────
    /// Run qualification trial or show trial status
    Trial(TrialArgs),
    /// Upgrade runtime (check / apply / rollback)
    Update(UpdateArgs),
    /// List or toggle runtime feature flags
    Features(FeaturesArgs),
    /// Compute content-addressable CRC of runtime state
    Crc(CrcArgs),

    // ── Product management ────────────────────────────────────────────────────
    /// Product registry management
    Product(ProductArgs),
    /// Content store management
    Content(ContentArgs),
    /// Rollback to a previous product snapshot
    Rollback(RollbackArgs),
    /// Submit or list peer review requests
    PeerReview(PeerReviewArgs),
}

// ── run ───────────────────────────────────────────────────────────────────────

#[derive(Args)]
pub struct RunArgs {
    /// State directory (default: ~/.urace/state)
    #[arg(long, default_value = "state")]
    pub state_dir: String,

    /// Run only N cycles then exit (0 = run forever)
    #[arg(long, default_value = "0")]
    pub max_cycles: u64,

    /// Allow execution (default: true)
    #[arg(long, default_value = "true")]
    pub allow_execution: bool,
}

// ── status ────────────────────────────────────────────────────────────────────

#[derive(Args)]
pub struct StatusArgs {
    /// Show full detail including circuit breakers
    #[arg(long, short = 'v')]
    pub verbose: bool,
}

// ── config ────────────────────────────────────────────────────────────────────

#[derive(Args)]
pub struct ConfigArgs {
    #[command(subcommand)]
    pub cmd: ConfigCommands,
}

#[derive(Subcommand)]
pub enum ConfigCommands {
    /// Print current configuration
    Show,

    /// Get a single config value by dotted path (e.g. network.port)
    Get {
        /// Dotted config path
        path: String,
    },

    /// Set a config value — requires authority check before saving
    Set {
        /// Dotted config path
        path: String,
        /// New value (string, coerced to target type)
        value: String,
    },

    /// Validate config against schema and print any errors
    Validate,

    /// Print the config file path
    Path,
}

// ── source ────────────────────────────────────────────────────────────────────

#[derive(Subcommand)]
pub enum SourceCommands {
    /// Register a new source adapter
    Add {
        /// Source kind (e.g. directory, github, git)
        #[arg(long)]
        kind: String,

        /// Explicit source ID (auto-generated if omitted)
        #[arg(long)]
        id: Option<String>,

        /// Extra config in key=value format (repeatable)
        #[arg(long = "set", value_parser = parse_kv)]
        config: Vec<(String, String)>,
    },

    /// List registered sources
    List,

    /// Remove a source by ID
    Remove {
        /// Source ID
        id: String,
    },

    /// Sync a source immediately
    Sync {
        /// Source ID
        id: String,
    },
}

// ── work ──────────────────────────────────────────────────────────────────────

#[derive(Subcommand)]
pub enum WorkCommands {
    /// List open work items
    List {
        /// Filter by status (open, assigned, completed)
        #[arg(long)]
        status: Option<String>,
    },

    /// Submit a bid for a work item
    Bid {
        /// Work item ID
        id: String,

        /// Bid amount in UCR
        #[arg(long)]
        amount: u64,
    },

    /// Assign a work item to this peer
    Assign {
        /// Work item ID
        id: String,
    },
}

// ── tui ───────────────────────────────────────────────────────────────────────

#[derive(Args)]
pub struct TuiArgs {
    /// Polling interval in milliseconds (how often to refresh data from state files)
    #[arg(long, default_value = "500")]
    pub interval_ms: u64,
}

// ── Helpers ───────────────────────────────────────────────────────────────────

// ── web ───────────────────────────────────────────────────────────────────────

#[derive(Debug, clap::Args)]
pub struct WebArgs {
    /// TCP port for the web UI (default: 7400)
    #[arg(long, default_value = "7400")]
    pub port: u16,

    /// Bind address
    #[arg(long, default_value = "127.0.0.1")]
    pub bind: String,

    /// Bearer token (auto-generated if not set)
    #[arg(long)]
    pub token: Option<String>,
}

// ── Helpers ───────────────────────────────────────────────────────────────────

/// Parse a `key=value` string into a tuple.
fn parse_kv(s: &str) -> Result<(String, String), String> {
    s.split_once('=')
        .map(|(k, v)| (k.to_string(), v.to_string()))
        .ok_or_else(|| format!("expected KEY=VALUE, got {s:?}"))
}

#[cfg(test)]
mod tests {
    use super::*;
    use clap::CommandFactory;

    #[test]
    fn cli_debug_assert() {
        // clap's debug_assert validates the CLI structure at test time
        Cli::command().debug_assert();
    }

    #[test]
    fn version_subcommand_parses() {
        let cli = Cli::try_parse_from(["urace", "version"]).unwrap();
        assert!(matches!(cli.command, Commands::Version));
    }

    #[test]
    fn status_parses() {
        let cli = Cli::try_parse_from(["urace", "status"]).unwrap();
        assert!(matches!(cli.command, Commands::Status(_)));
    }

    #[test]
    fn run_parses_defaults() {
        let cli = Cli::try_parse_from(["urace", "run"]).unwrap();
        if let Commands::Run(args) = cli.command {
            assert_eq!(args.max_cycles, 0);
            assert!(args.allow_execution);
        } else {
            panic!("expected Run");
        }
    }

    #[test]
    fn source_add_parses() {
        let cli = Cli::try_parse_from(["urace", "source", "add", "--kind", "directory"]).unwrap();
        if let Commands::Source {
            cmd: SourceCommands::Add { kind, id, .. },
        } = cli.command
        {
            assert_eq!(kind, "directory");
            assert!(id.is_none());
        } else {
            panic!("expected source add");
        }
    }

    #[test]
    fn config_set_parses() {
        let cli = Cli::try_parse_from(["urace", "config", "set", "network.port", "7302"]).unwrap();
        if let Commands::Config(ConfigArgs {
            cmd: ConfigCommands::Set { path, value },
        }) = cli.command
        {
            assert_eq!(path, "network.port");
            assert_eq!(value, "7302");
        } else {
            panic!("expected config set");
        }
    }

    #[test]
    fn work_bid_parses() {
        let cli =
            Cli::try_parse_from(["urace", "work", "bid", "work-001", "--amount", "100"]).unwrap();
        if let Commands::Work {
            cmd: WorkCommands::Bid { id, amount },
        } = cli.command
        {
            assert_eq!(id, "work-001");
            assert_eq!(amount, 100);
        } else {
            panic!("expected work bid");
        }
    }

    #[test]
    fn json_flag_is_global() {
        let cli = Cli::try_parse_from(["urace", "--json", "version"]).unwrap();
        assert!(cli.json);
    }

    #[test]
    fn tui_parses() {
        let cli = Cli::try_parse_from(["urace", "tui"]).unwrap();
        assert!(matches!(cli.command, Commands::Tui(_)));
    }

    #[test]
    fn exchange_status_parses() {
        let cli = Cli::try_parse_from(["urace", "exchange", "status"]).unwrap();
        assert!(matches!(
            cli.command,
            Commands::Exchange(ExchangeArgs {
                cmd: ExchangeCommands::Status { .. }
            })
        ));
    }

    #[test]
    fn exchange_ask_parses() {
        let cli = Cli::try_parse_from(["urace", "exchange", "ask", "feat-001", "--price", "500"])
            .unwrap();
        if let Commands::Exchange(ExchangeArgs {
            cmd: ExchangeCommands::Ask { atom_id, price, .. },
        }) = cli.command
        {
            assert_eq!(atom_id, "feat-001");
            assert_eq!(price, 500);
        } else {
            panic!("expected exchange ask");
        }
    }
}
