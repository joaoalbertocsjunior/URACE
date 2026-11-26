//! M64 — Governance veto: minority veto for safety-critical protocol changes.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Fraction of voting weight required to block a proposal.
pub const VETO_THRESHOLD_FRACTION: f64 = 0.20; // 20% can veto

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VetoRecord {
    pub veto_id: String,
    pub proposal_id: String,
    pub vetoer_id: String,
    pub reason: String,
    pub at_unix: u64,
}

#[derive(Debug, thiserror::Error)]
pub enum VetoError {
    #[error("peer '{0}' already vetoed proposal '{1}'")]
    DuplicateVeto(String, String),
}

pub struct VetoRegistry {
    // proposal_id -> Vec<VetoRecord>
    vetoes: HashMap<String, Vec<VetoRecord>>,
}

impl VetoRegistry {
    pub fn new() -> Self {
        VetoRegistry {
            vetoes: HashMap::new(),
        }
    }

    /// Submit a veto. Deduplicates by vetoer_id per proposal.
    pub fn submit_veto(&mut self, veto: VetoRecord) -> Result<(), VetoError> {
        let entries = self.vetoes.entry(veto.proposal_id.clone()).or_default();
        if entries.iter().any(|v| v.vetoer_id == veto.vetoer_id) {
            return Err(VetoError::DuplicateVeto(
                veto.vetoer_id.clone(),
                veto.proposal_id.clone(),
            ));
        }
        entries.push(veto);
        Ok(())
    }

    pub fn veto_count(&self, proposal_id: &str) -> usize {
        self.vetoes.get(proposal_id).map(|v| v.len()).unwrap_or(0)
    }

    /// Returns true when vetoers / total_voters >= VETO_THRESHOLD_FRACTION.
    pub fn veto_blocks_proposal(&self, proposal_id: &str, total_voters: usize) -> bool {
        if total_voters == 0 {
            return false;
        }
        let count = self.veto_count(proposal_id);
        (count as f64) / (total_voters as f64) >= VETO_THRESHOLD_FRACTION
    }

    pub fn vetoes_for(&self, proposal_id: &str) -> &[VetoRecord] {
        self.vetoes
            .get(proposal_id)
            .map(|v| v.as_slice())
            .unwrap_or(&[])
    }
}

impl Default for VetoRegistry {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_veto(veto_id: &str, proposal_id: &str, vetoer_id: &str) -> VetoRecord {
        VetoRecord {
            veto_id: veto_id.to_string(),
            proposal_id: proposal_id.to_string(),
            vetoer_id: vetoer_id.to_string(),
            reason: "safety concern".to_string(),
            at_unix: 1000,
        }
    }

    #[test]
    fn single_veto_below_threshold_does_not_block() {
        let mut registry = VetoRegistry::new();
        // 1 vetoer out of 10 total = 10%, below 20% threshold
        registry
            .submit_veto(make_veto("v1", "proposal-1", "peer-A"))
            .unwrap();
        assert!(!registry.veto_blocks_proposal("proposal-1", 10));
    }

    #[test]
    fn twenty_percent_or_more_vetoes_blocks() {
        let mut registry = VetoRegistry::new();
        // 2 vetoers out of 10 total = 20%, exactly at threshold
        registry
            .submit_veto(make_veto("v1", "proposal-1", "peer-A"))
            .unwrap();
        registry
            .submit_veto(make_veto("v2", "proposal-1", "peer-B"))
            .unwrap();
        assert!(registry.veto_blocks_proposal("proposal-1", 10));

        // 3 vetoers out of 10 = 30%, above threshold
        registry
            .submit_veto(make_veto("v3", "proposal-1", "peer-C"))
            .unwrap();
        assert!(registry.veto_blocks_proposal("proposal-1", 10));
    }

    #[test]
    fn duplicate_veto_rejected() {
        let mut registry = VetoRegistry::new();
        registry
            .submit_veto(make_veto("v1", "proposal-1", "peer-A"))
            .unwrap();
        let result = registry.submit_veto(make_veto("v2", "proposal-1", "peer-A"));
        assert!(matches!(result, Err(VetoError::DuplicateVeto(_, _))));
        // Count should still be 1, not 2
        assert_eq!(registry.veto_count("proposal-1"), 1);
    }

    #[test]
    fn vetoes_for_returns_correct_records() {
        let mut registry = VetoRegistry::new();
        registry
            .submit_veto(make_veto("v1", "proposal-1", "peer-A"))
            .unwrap();
        registry
            .submit_veto(make_veto("v2", "proposal-1", "peer-B"))
            .unwrap();
        // Different proposal
        registry
            .submit_veto(make_veto("v3", "proposal-2", "peer-C"))
            .unwrap();

        let records = registry.vetoes_for("proposal-1");
        assert_eq!(records.len(), 2);
        assert!(records.iter().any(|r| r.vetoer_id == "peer-A"));
        assert!(records.iter().any(|r| r.vetoer_id == "peer-B"));

        // The other proposal should have no cross-contamination
        let other = registry.vetoes_for("proposal-2");
        assert_eq!(other.len(), 1);
        assert_eq!(other[0].vetoer_id, "peer-C");
    }
}
