//! `urace-upgrade` — two-phase upgrade launcher, evolution guard, and updater.
//!
//! Exit codes:
//! - `EXIT_REVALIDATE` (75) — candidate validated; re-validate before activation
//! - `EXIT_ONE_RETRY`  (76) — validation failed; one retry permitted
//!
//! Rust port of `launcher.py`, `evolution_guard.py`, `updater.py`.

pub mod build_attestation;
pub mod evolution_guard;
pub mod launcher;
pub mod runtime_integrity;
pub mod updater;

pub use build_attestation::{BuildAttestation, BuildAttestationError};
pub use evolution_guard::{
    EvolutionGuard, EvolutionGuardError, GovernanceApproval, GovernanceVoteGate,
    MIN_GOVERNANCE_APPROVALS,
};
pub use launcher::{
    CandidateValidator, LaunchResult, Launcher, LauncherError, EXIT_ONE_RETRY, EXIT_REVALIDATE,
};
pub use runtime_integrity::{
    compute_config_hash, verify_runtime_integrity, IntegrityStatus, RuntimeIntegrityRecord,
};
pub use updater::{UpdateError, UpdateManifest, Updater};
