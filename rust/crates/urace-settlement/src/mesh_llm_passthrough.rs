//! Option 3: mesh-llm executor payment passthrough.
//!
//! When URACE dispatches inference to a mesh-llm executor, that executor
//! already has a live Lightning channel. URACE work-market payments can be
//! routed through that channel — zero build cost, immediate usability.
//!
//! Config key: settlement_rail = "mesh_llm_passthrough"
//!
//! Architecture: URACE → work bid → mesh-llm executor → Lightning payment
//! mesh-llm executor is registered as an ai_executor source in the registry.

use crate::{SettlementRail, SettlementResult};

/// mesh-llm passthrough settlement rail.
///
/// Forwards payment requests to a mesh-llm executor's payment endpoint.
/// Returns `status = "passthrough_pending"` until the executor confirms.
pub struct MeshLlmPassthrough {
    pub executor_endpoint: String,
}

impl MeshLlmPassthrough {
    pub fn new(executor_endpoint: &str) -> Self {
        MeshLlmPassthrough {
            executor_endpoint: executor_endpoint.to_string(),
        }
    }

    /// Settle a work-market payment via the mesh-llm executor's Lightning channel.
    ///
    /// Returns `status = "passthrough_pending"` until the executor confirms via callback.
    ///
    /// Full HTTP wiring to `{executor_endpoint}/payments` is deferred —
    /// this stub records intent and returns a pending result.
    pub fn settle_work_payment(&self, amount_msat: u64, work_ref: &str) -> SettlementResult {
        tracing::info!(
            executor_endpoint = %self.executor_endpoint,
            amount_msat,
            work_ref,
            "MeshLlmPassthrough::settle_work_payment (pending wiring)"
        );
        // TODO(R-12+): POST to `{executor_endpoint}/payments` with:
        //   { "amount_msat": amount_msat, "work_ref": work_ref, "rail": "lightning" }
        // Then poll `{executor_endpoint}/payments/{work_ref}/status` for confirmation.
        SettlementResult {
            status: "passthrough_pending".into(),
            tx_hash: None,
            error: None,
            rail: SettlementRail::Lightning,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_settle_returns_passthrough_pending() {
        let pt = MeshLlmPassthrough::new("http://mesh-llm-executor:8080");
        let result = pt.settle_work_payment(10_000_000, "work-ref-abc");
        assert_eq!(result.status, "passthrough_pending");
        assert!(result.error.is_none());
        assert_eq!(result.rail, SettlementRail::Lightning);
    }

    #[test]
    fn test_new_stores_endpoint() {
        let pt = MeshLlmPassthrough::new("http://endpoint");
        assert_eq!(pt.executor_endpoint, "http://endpoint");
    }
}
