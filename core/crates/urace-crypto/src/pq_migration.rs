//! M56 — Post-quantum (PQ) cryptography migration path.
//!
//! Defines the key-algorithm taxonomy, a migration state machine, and helpers
//! for planning and tracking an in-flight migration from classical to PQ algorithms.
//!
//! **No production PQ implementation is included here** — this crate models the
//! migration state so that the authority layer can gate actions on migration
//! progress.  Actual PQ primitives (ML-KEM / Kyber, ML-DSA / Dilithium) will be
//! wired via feature-flagged dependencies when standardisation stabilises.

use serde::{Deserialize, Serialize};

// ── Algorithm taxonomy ─────────────────────────────────────────────────────────

/// A cryptographic key algorithm — classical or post-quantum.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum KeyAlgorithm {
    /// Ed25519 — classical signing (currently deployed).
    Ed25519,
    /// X25519 — classical key exchange.
    X25519,
    /// ML-KEM-768 (NIST FIPS 203, formerly Kyber-768) — PQ key encapsulation.
    MlKem768,
    /// ML-DSA-65 (NIST FIPS 204, formerly Dilithium3) — PQ digital signature.
    MlDsa65,
    /// Composite: classical + PQ hybrid (e.g. Ed25519 + ML-DSA-65).
    Hybrid { classical: Box<KeyAlgorithm>, pq: Box<KeyAlgorithm> },
}

impl KeyAlgorithm {
    /// True when this algorithm (or either component of a hybrid) is post-quantum.
    pub fn is_post_quantum(&self) -> bool {
        match self {
            KeyAlgorithm::MlKem768 | KeyAlgorithm::MlDsa65 => true,
            KeyAlgorithm::Hybrid { pq, .. } => pq.is_post_quantum(),
            _ => false,
        }
    }

    /// True for hybrid schemes — provides classical fallback while PQ is unproven.
    pub fn is_hybrid(&self) -> bool {
        matches!(self, KeyAlgorithm::Hybrid { .. })
    }
}

// ── Migration state machine ───────────────────────────────────────────────────

/// Phase of the PQ migration lifecycle for a single key slot.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum MigrationPhase {
    /// No migration has started; classical key in use.
    Classical,
    /// A hybrid key has been generated; both classical + PQ are active.
    HybridActive,
    /// PQ-only key is in use; classical key has been retired.
    PqOnly,
    /// Migration was aborted; rolled back to classical.
    Aborted { reason: String },
}

impl MigrationPhase {
    pub fn is_complete(&self) -> bool {
        matches!(self, MigrationPhase::PqOnly)
    }

    pub fn is_in_progress(&self) -> bool {
        matches!(self, MigrationPhase::HybridActive)
    }
}

/// The migration plan for a single key slot owned by a peer.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PqMigrationPlan {
    pub peer_id: String,
    pub key_slot: String,
    pub current_algorithm: KeyAlgorithm,
    pub target_algorithm: KeyAlgorithm,
    pub phase: MigrationPhase,
    pub started_at_unix: Option<u64>,
    pub completed_at_unix: Option<u64>,
}

impl PqMigrationPlan {
    pub fn new(peer_id: impl Into<String>, key_slot: impl Into<String>) -> Self {
        PqMigrationPlan {
            peer_id: peer_id.into(),
            key_slot: key_slot.into(),
            current_algorithm: KeyAlgorithm::Ed25519,
            target_algorithm: KeyAlgorithm::Hybrid {
                classical: Box::new(KeyAlgorithm::Ed25519),
                pq: Box::new(KeyAlgorithm::MlDsa65),
            },
            phase: MigrationPhase::Classical,
            started_at_unix: None,
            completed_at_unix: None,
        }
    }

    /// Advance from Classical → HybridActive.
    ///
    /// Returns `Err` if the plan is not in `Classical` phase.
    pub fn begin_hybrid(&mut self, now_unix: u64) -> Result<(), PqMigrationError> {
        if self.phase != MigrationPhase::Classical {
            return Err(PqMigrationError::InvalidTransition {
                from: format!("{:?}", self.phase),
                to: "HybridActive".into(),
            });
        }
        self.phase = MigrationPhase::HybridActive;
        self.started_at_unix = Some(now_unix);
        self.current_algorithm = self.target_algorithm.clone();
        Ok(())
    }

    /// Advance from HybridActive → PqOnly.
    ///
    /// Returns `Err` if the plan is not in `HybridActive` phase.
    pub fn complete_migration(&mut self, now_unix: u64) -> Result<(), PqMigrationError> {
        if self.phase != MigrationPhase::HybridActive {
            return Err(PqMigrationError::InvalidTransition {
                from: format!("{:?}", self.phase),
                to: "PqOnly".into(),
            });
        }
        self.phase = MigrationPhase::PqOnly;
        self.current_algorithm = KeyAlgorithm::MlDsa65;
        self.completed_at_unix = Some(now_unix);
        Ok(())
    }

    /// Abort migration and roll back to Classical.
    pub fn abort(&mut self, reason: impl Into<String>) {
        self.phase = MigrationPhase::Aborted { reason: reason.into() };
        self.current_algorithm = KeyAlgorithm::Ed25519;
    }
}

// ── Error ─────────────────────────────────────────────────────────────────────

#[derive(Debug, thiserror::Error)]
pub enum PqMigrationError {
    #[error("invalid migration transition from '{from}' to '{to}'")]
    InvalidTransition { from: String, to: String },
}

// ── Fleet summary ─────────────────────────────────────────────────────────────

/// Summary of fleet-wide PQ migration progress.
#[derive(Debug, Default, Serialize, Deserialize)]
pub struct FleetMigrationSummary {
    pub total_plans: usize,
    pub classical: usize,
    pub hybrid_active: usize,
    pub pq_only: usize,
    pub aborted: usize,
}

impl FleetMigrationSummary {
    /// Fraction of plans that have completed PQ migration (0.0..=1.0).
    pub fn completion_fraction(&self) -> f64 {
        if self.total_plans == 0 {
            return 0.0;
        }
        self.pq_only as f64 / self.total_plans as f64
    }
}

/// Aggregate migration plans into a fleet-level summary.
pub fn fleet_summary(plans: &[PqMigrationPlan]) -> FleetMigrationSummary {
    let mut summary = FleetMigrationSummary { total_plans: plans.len(), ..Default::default() };
    for plan in plans {
        match &plan.phase {
            MigrationPhase::Classical => summary.classical += 1,
            MigrationPhase::HybridActive => summary.hybrid_active += 1,
            MigrationPhase::PqOnly => summary.pq_only += 1,
            MigrationPhase::Aborted { .. } => summary.aborted += 1,
        }
    }
    summary
}

// ── Tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn algorithm_pq_classification() {
        assert!(!KeyAlgorithm::Ed25519.is_post_quantum());
        assert!(KeyAlgorithm::MlDsa65.is_post_quantum());
        assert!(KeyAlgorithm::MlKem768.is_post_quantum());
        let hybrid = KeyAlgorithm::Hybrid {
            classical: Box::new(KeyAlgorithm::Ed25519),
            pq: Box::new(KeyAlgorithm::MlDsa65),
        };
        assert!(hybrid.is_post_quantum());
        assert!(hybrid.is_hybrid());
    }

    #[test]
    fn migration_happy_path() {
        let mut plan = PqMigrationPlan::new("peer-1", "signing");
        assert_eq!(plan.phase, MigrationPhase::Classical);

        plan.begin_hybrid(1000).unwrap();
        assert_eq!(plan.phase, MigrationPhase::HybridActive);
        assert!(plan.started_at_unix.is_some());

        plan.complete_migration(2000).unwrap();
        assert!(plan.phase.is_complete());
        assert_eq!(plan.completed_at_unix, Some(2000));
    }

    #[test]
    fn invalid_transition_classical_to_pq_only() {
        let mut plan = PqMigrationPlan::new("peer-2", "signing");
        let err = plan.complete_migration(1000).unwrap_err();
        assert!(err.to_string().contains("Classical"));
    }

    #[test]
    fn abort_resets_to_classical() {
        let mut plan = PqMigrationPlan::new("peer-3", "signing");
        plan.begin_hybrid(1000).unwrap();
        plan.abort("hardware unsupported");
        assert!(matches!(plan.phase, MigrationPhase::Aborted { .. }));
        assert_eq!(plan.current_algorithm, KeyAlgorithm::Ed25519);
    }

    #[test]
    fn fleet_summary_aggregation() {
        let mut p1 = PqMigrationPlan::new("p1", "s");
        let mut p2 = PqMigrationPlan::new("p2", "s");
        p1.begin_hybrid(1).unwrap();
        p1.complete_migration(2).unwrap();
        p2.begin_hybrid(1).unwrap();
        let plans = vec![p1, p2, PqMigrationPlan::new("p3", "s")];
        let summary = fleet_summary(&plans);
        assert_eq!(summary.total_plans, 3);
        assert_eq!(summary.pq_only, 1);
        assert_eq!(summary.hybrid_active, 1);
        assert_eq!(summary.classical, 1);
        let frac = summary.completion_fraction();
        assert!((frac - 1.0 / 3.0).abs() < 1e-9);
    }
}
