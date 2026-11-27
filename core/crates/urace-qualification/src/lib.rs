//! `urace-qualification` — qualification trial runner, scoring, receipts, and P2P cost qualification.
//!
//! # Key invariants
//! - `QualificationEngine::qualify()` only sets `should_mint = true` when `score_delta > 0`.
//! - `TrialStore` is append-only (backed by `urace_ledger::Journal`).
//! - `UNIT = 100_000_000` (10^8 UCR base units).
//! - Mint triggers only on qualified acceptance — never on zero or negative score_delta.

pub mod accounting;
pub mod fast_path;
pub mod outcome_signal;
pub mod score_discount;
pub mod appeal;
pub mod delivery_proof;
pub mod multi_evaluator;
pub mod outcome_verification;
pub mod post_delivery;
pub mod preflight;
pub mod quality_floor;
pub mod qualification;
pub mod receipt_handler;
pub mod trial;
pub mod trial_common;
pub mod trial_receipt;

pub use accounting::{within_budget, ResourceAccount, ResourceBudget};
pub use outcome_verification::{
    verify as verify_outcome, verify_with_evaluators, EvidenceKind, MetricDirection,
    MultiEvaluatorOutcome, OutcomeContract, OutcomeObservation, OutcomeStatus,
    OutcomeVerificationError, OutcomeVerificationResult,
};
pub use preflight::{hints, Hint, HintLevel, PreflightError, FORMAT_VERSION, MIN_FORMAT_VERSION};
pub use qualification::{QualificationEngine, QualificationError, QualificationResult};
pub use receipt_handler::{
    DeliveryOutcome, LocalReceiptHandler, P2PReceiptHandler, ReceiptHandler, ReceiptHandlerError,
    SettlementConfirmation,
};
pub use trial::{Trial, TrialConfig, TrialResult, TrialStore};
pub use trial_common::{now_iso, trial_identifier, TrialContext};
pub use trial_receipt::{ReceiptStore, TrialReceipt};

// M31 — quality floor
pub use quality_floor::{QualityFloor, QualityFloorError, QualityGateResult, DEFAULT_QUALITY_FLOOR};
// M32 — mint gate bypass detection
pub mod mint_gate_proof;
pub use mint_gate_proof::{MintGateError, MintGateProof, MINT_GATE_MIN_SCORE_DELTA};
// M44 — delivery proof
pub use delivery_proof::{DeliveryProof, DeliveryProofError, DeliveryProofRegistry};
// M45 — post-delivery gate
pub use post_delivery::{PostDeliveryError, PostDeliveryGate, PostDeliveryOutcome};
// M46 — multi-evaluator consensus
pub use multi_evaluator::{ConsensusResult, EvaluatorError, EvaluatorVote, MultiEvaluatorRound};
// M49 — appeal window
pub use appeal::{Appeal, AppealRegistry, AppealStatus, DEFAULT_APPEAL_WINDOW_SECS};
// M50 — score discounting
pub use score_discount::{apply_discounts, ScoreDiscountFlags};

pub use fast_path::{
    FastPathBudget, FastPathDecision, FastPathError, FastPathRegistry, QualificationPathKind,
    FAST_PATH_CHAIN_RESET_SECS, FAST_PATH_MAX_CHAIN_DEPTH, FAST_PATH_MAX_DIFF_BYTES,
};
pub use outcome_signal::{
    reputation_delta_from_signal, validate_signal, OutcomeKind, OutcomeSignal, OutcomeSignalError,
    OutcomeSignalStore, MINIMUM_CORROBORATING_PEERS, OUTCOME_SIGNAL_MAX_AGE_SECS,
};

/// 1 UCR = 100_000_000 base units (10^8, satoshi-style).
pub const UNIT: u64 = 100_000_000;
