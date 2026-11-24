//! Dual-rail settlement manager — routes to active rail based on config.
//!
//! Priority: mesh_llm_passthrough (Option 3) → evm (Option 2) → none
//!
//! Config keys:
//!   settlement_rail: "mesh_llm_passthrough" | "evm" | "none"
//!   executor_endpoint: String (required for mesh_llm_passthrough)
//!   evm_rpc_url, evm_chain_id, evm_contract_address, evm_token_settlement (for evm)

use crate::evm::{EvmConfig, EvmSettlementAdapter};
use crate::mesh_llm_passthrough::MeshLlmPassthrough;
use crate::{SettlementRail, SettlementResult};
use serde_json::Value;
use std::collections::HashMap;

/// Active settlement manager — dispatches to the configured rail.
pub struct SettlementManager {
    pub rail: SettlementRail,
    pub evm: Option<EvmSettlementAdapter>,
    pub mesh_llm: Option<MeshLlmPassthrough>,
}

impl SettlementManager {
    /// Build from operator config map.
    ///
    /// Priority (Option 3 → Option 2 → none):
    ///   1. mesh_llm_passthrough — if `settlement_rail == "mesh_llm_passthrough"` and
    ///      `executor_endpoint` is set.
    ///   2. evm — if `settlement_rail == "evm"` (or unset) and evm config present.
    ///   3. none — internal UCR accounting only.
    pub fn from_config(config: &HashMap<String, Value>) -> Self {
        let rail_str = config
            .get("settlement_rail")
            .and_then(Value::as_str)
            .unwrap_or("none");

        match rail_str {
            "mesh_llm_passthrough" => {
                let endpoint = config
                    .get("executor_endpoint")
                    .and_then(Value::as_str)
                    .unwrap_or("http://localhost:8080");
                SettlementManager {
                    rail: SettlementRail::Lightning,
                    evm: None,
                    mesh_llm: Some(MeshLlmPassthrough::new(endpoint)),
                }
            }
            "evm" => {
                let evm_config = EvmConfig {
                    rpc_url: config.get("evm_rpc_url").and_then(Value::as_str).map(String::from),
                    chain_id: config
                        .get("evm_chain_id")
                        .and_then(Value::as_u64)
                        .unwrap_or(137), // Polygon mainnet
                    contract_address: config
                        .get("evm_contract_address")
                        .and_then(Value::as_str)
                        .map(String::from),
                    token_settlement: config
                        .get("evm_token_settlement")
                        .and_then(Value::as_bool)
                        .unwrap_or(false),
                };
                SettlementManager {
                    rail: SettlementRail::Evm,
                    evm: Some(EvmSettlementAdapter::new(evm_config)),
                    mesh_llm: None,
                }
            }
            _ => {
                // "none" or unknown — internal UCR accounting only.
                SettlementManager {
                    rail: SettlementRail::None,
                    evm: None,
                    mesh_llm: None,
                }
            }
        }
    }

    /// Settle `amount_ucr` to `recipient` for `work_ref`.
    ///
    /// Priority: mesh_llm_passthrough → evm → none.
    pub fn settle(&self, amount_ucr: i64, recipient: &str, work_ref: &str) -> SettlementResult {
        // Option 3: mesh-llm passthrough (immediate usability, zero build cost).
        if let Some(ref mesh) = self.mesh_llm {
            // Convert UCR to msat (1 UCR = 1 sat = 1_000 msat for settlement purposes).
            // TODO(economics): wire proper UCR/msat conversion rate from cost_model.
            let amount_msat = (amount_ucr.unsigned_abs() as u64) * 1_000;
            return mesh.settle_work_payment(amount_msat, work_ref);
        }

        // Option 2: EVM/Polygon settlement.
        if let Some(ref evm) = self.evm {
            return evm.submit_transfer(recipient, amount_ucr);
        }

        // None: internal accounting only — no on-chain settlement.
        SettlementResult {
            status: "internal_only".into(),
            tx_hash: None,
            error: Some("no settlement rail configured; amount recorded internally".into()),
            rail: SettlementRail::None,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn cfg(pairs: &[(&str, Value)]) -> HashMap<String, Value> {
        pairs.iter().map(|(k, v)| (k.to_string(), v.clone())).collect()
    }

    #[test]
    fn test_no_rail_config() {
        let manager = SettlementManager::from_config(&cfg(&[]));
        assert_eq!(manager.rail, SettlementRail::None);
        let result = manager.settle(1000, "peer-x", "work-1");
        assert_eq!(result.status, "internal_only");
        assert_eq!(result.rail, SettlementRail::None);
    }

    #[test]
    fn test_mesh_llm_passthrough_rail() {
        let config = cfg(&[
            ("settlement_rail", json!("mesh_llm_passthrough")),
            ("executor_endpoint", json!("http://executor:8080")),
        ]);
        let manager = SettlementManager::from_config(&config);
        assert!(manager.mesh_llm.is_some());
        let result = manager.settle(5000, "peer-y", "work-2");
        assert_eq!(result.status, "passthrough_pending");
    }

    #[test]
    fn test_evm_rail_no_rpc() {
        let config = cfg(&[
            ("settlement_rail", json!("evm")),
            ("evm_token_settlement", json!(true)),
            // No evm_rpc_url — should return rpc_error.
        ]);
        let manager = SettlementManager::from_config(&config);
        assert!(manager.evm.is_some());
        let result = manager.settle(1000, "0x0000000000000000000000000000000000000001", "work-3");
        // Without rpc_url, EVM adapter returns rpc_error.
        assert_eq!(result.status, "rpc_error");
    }
}
