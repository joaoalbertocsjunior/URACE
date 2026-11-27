//! `urace-project-work` — spec trial verification, project governance, and regression guard.
//!
//! Extracted from `urace-qualification` to separate project/governance concerns
//! from the core qualification trial runner.

pub mod project_work;
pub mod runtime_regression_guard;
pub mod spec_trial;

pub use project_work::{
    check_publication_authority, compute_mint_eligibility, finalise_run, project_identity,
    start_run, validate_declaration, AcceptanceResult, ActiveBudget, AuthoritySpec,
    ProjectDeclaration, ProjectRunResult, ProjectWorkError, Requirement,
    FAMILIES as PROJECT_FAMILIES,
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
