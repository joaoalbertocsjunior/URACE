//! `urace-work` — work market, P2P matching, work policy, receipts, and settlements.
//!
//! # Crate structure
//!
//! - `work_policy`        — `WorkPolicy` with conservative defaults; `PolicyViolation` errors.
//! - `matching`           — `WorkTask`, `WorkBid`, `match_score`, `DemandCounter` (local-only),
//!   `select_best_bid`.
//! - `work_market`        — `WorkMarket` concurrent registry with policy enforcement.
//! - `receipt`            — `WorkReceipt`, `ReceiptStore` (append-only journal).
//! - `purchase_settlement`— `PurchaseSettlement`, `SettlementStore` (append-only journal).
//!
//! # Key invariants
//!
//! - `DemandCounter` is never serialised or deserialised; demand signals are
//!   process-local only (anti-Sybil invariant from CLAUDE.md).
//! - `WorkPolicy::default()` has `max_budget_ucr=0` and `require_authority_check=true`;
//!   any leniency must be explicitly configured.

pub mod commit_reveal;
pub mod exchange_endpoint;
pub mod implementation_sequence;
pub mod matching;
pub mod planner;
pub mod price_history;
pub mod purchase_settlement;
pub mod receipt;
pub mod work_market;
pub mod work_policy;

pub use commit_reveal::{
    BidCommitment, BidReveal, CommitRevealError, CommitRevealStore, NO_REVEAL_PENALTY_UCR,
};
pub use exchange_endpoint::{
    build_settlement_router, handle_credit_settlement, SettlementEndpointError, SettlementPayload,
    SettlementResponse, SettlementRouterConfig, SCHEMA as CREDIT_SETTLEMENT_SCHEMA,
};
pub use implementation_sequence::PlanningContext;
pub use matching::{match_score, select_best_bid, DemandCounter, WorkBid, WorkTask};
pub use planner::{AutoPlanner, Planner, TopologicalPlanner};
pub use price_history::{PriceEntry, PriceHistory, PriceHistoryError};
pub use purchase_settlement::{PurchaseSettlement, SettlementError, SettlementStore};
pub use receipt::{ReceiptError, ReceiptStore, WorkReceipt};
pub use work_market::{WorkError, WorkMarket};
pub use work_policy::{PolicyViolation, WorkPolicy};
