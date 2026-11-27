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
pub mod escrow_guard;
pub mod exchange_endpoint;
pub mod implementation_sequence;
pub mod matching;
pub mod planner;
pub mod price_history;
pub mod skill_match;
pub mod purchase_settlement;
pub mod receipt;
pub mod task_rate;
pub mod work_market;
pub mod work_policy;

pub use commit_reveal::{
    is_bid_valid, BidCommitment, BidReveal, CommitRevealError, CommitRevealStore,
    BID_VALIDITY_WINDOW_SECS, NO_REVEAL_PENALTY_UCR,
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
pub use work_market::{PriceAttestation, WorkError, WorkMarket};
pub use work_policy::{
    check_market_floor, participation_cost, PolicyViolation, WorkPolicy, MARKET_FLOOR_UCR,
    OFF_GRAPH_COST_UCR,
};
pub use escrow_guard::{EscrowError, EscrowRecord, EscrowState, ESCROW_TIMEOUT_SECS};
pub use task_rate::{TaskRateGuard, TaskRateResult, TASK_RATE_LIMIT_PER_MIN};
pub use skill_match::{
    SkillClaim, SkillClaimError, SkillConcentrationGuard, SkillMatchResult, SkillRegistry,
    SkillRouter, DomainConcentrationStatus,
    SKILL_MATCH_BONUS, SKILL_VERIFICATION_THRESHOLD, MAX_SKILLS_PER_EXECUTOR,
    SKILL_CODE_REVIEW, SKILL_NLP, SKILL_MATH, SKILL_SECURITY, SKILL_DATA,
};
