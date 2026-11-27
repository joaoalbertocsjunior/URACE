//! `urace-benchmarking` — benchmark corpus, performance, regression, and P2P study infrastructure.
//!
//! Extracted from `urace-qualification` to separate benchmarking infrastructure
//! from the core qualification trial runner.

pub mod benchmark_corpus;
pub mod benchmark_performance;
pub mod benchmark_product;
pub mod benchmark_qualification;
pub mod benchmark_regression;
pub mod benchmark_reports;
pub mod benchmark_runner;
pub mod p2p_cost_qualification;
pub mod p2p_pair_protocol;
pub mod p2p_study_plan;
pub mod p2p_study_runner;

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
