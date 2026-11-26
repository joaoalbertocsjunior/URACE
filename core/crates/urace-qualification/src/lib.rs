//! `urace-qualification` — qualification trial runner, scoring, receipts, and P2P cost qualification.
//!
//! # Key invariants
//! - `QualificationEngine::qualify()` only sets `should_mint = true` when `score_delta > 0`.
//! - `TrialStore` is append-only (backed by `urace_ledger::Journal`).
//! - `UNIT = 100_000_000` (10^8 UCR base units).
//! - Mint triggers only on qualified acceptance — never on zero or negative score_delta.

pub mod accounting;
pub mod score_discount;
pub mod appeal;
pub mod benchmark_corpus;
pub mod benchmark_performance;
pub mod benchmark_product;
pub mod benchmark_qualification;
pub mod benchmark_regression;
pub mod benchmark_reports;
pub mod benchmark_runner;
pub mod delivery_proof;
pub mod multi_evaluator;
pub mod outcome_verification;
pub mod p2p_cost_qualification;
pub mod p2p_pair_protocol;
pub mod p2p_study_plan;
pub mod p2p_study_runner;
pub mod post_delivery;
pub mod preflight;
pub mod project_work;
pub mod quality_floor;
pub mod qualification;
pub mod receipt_handler;
pub mod runtime_regression_guard;
pub mod spec_trial;
pub mod trial;
pub mod trial_common;
pub mod trial_receipt;

pub use accounting::{within_budget, ResourceAccount, ResourceBudget};
pub use outcome_verification::{
    verify as verify_outcome, verify_with_evaluators, EvidenceKind, MetricDirection,
    MultiEvaluatorOutcome, OutcomeContract, OutcomeObservation, OutcomeStatus,
    OutcomeVerificationError, OutcomeVerificationResult,
};
pub use p2p_cost_qualification::{P2PCostQualifier, QualificationReceipt};
pub use p2p_pair_protocol::{
    check_pair_structure, cohort_complete, economic_claim_policy, is_valid_sha256_hex, sha256_hex,
    PairArm, PairRecord, PairTask, PairVerification, SourceAsset, ARMS as P2P_ARMS,
    COST_SCHEMA as P2P_COST_SCHEMA, FAMILIES as P2P_FAMILIES, SCHEMA as P2P_SCHEMA,
};
pub use p2p_study_plan::{
    canonical_sha256, verify_plan, CohortPlan, FrozenTask, PlanError, PlannedPair, PlannedPairTask,
};
pub use p2p_study_runner::{
    confined_path, digest_file, load_verified_plan, no_symlink_path, validate_acceptance_receipt,
    validate_cost_receipt, verify_adapter, PreflightResult, RunConfig, RunSummary, RunnerError,
};
pub use preflight::{hints, Hint, HintLevel, PreflightError, FORMAT_VERSION, MIN_FORMAT_VERSION};
pub use project_work::{
    check_publication_authority, compute_mint_eligibility, finalise_run, project_identity,
    start_run, validate_declaration, AcceptanceResult, ActiveBudget, AuthoritySpec,
    ProjectDeclaration, ProjectRunResult, ProjectWorkError, Requirement,
    FAMILIES as PROJECT_FAMILIES,
};
pub use qualification::{QualificationEngine, QualificationError, QualificationResult};
pub use receipt_handler::{
    DeliveryOutcome, LocalReceiptHandler, P2PReceiptHandler, ReceiptHandler, ReceiptHandlerError,
    SettlementConfirmation,
};
pub use runtime_regression_guard::{
    build_blocked_record, check as check_regression, guard_summary, DecisionRecord, GuardStatus,
    QualityDelta, RegressionGuardError,
};
pub use spec_trial::{
    digest_text, extract_headings, normative_sentences, review_passes, validate_patch,
    AuthorityGate, AuthorityOutcome, PeerReview, PeerReviewGate, Proposal, QualityScores,
    ResourceMetrics, ReviewResult, ScoreComparison, SpecTrialError, VersionManifest,
    MIN_PEER_REVIEWERS,
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

/// 1 UCR = 100_000_000 base units (10^8, satoshi-style).
pub const UNIT: u64 = 100_000_000;
