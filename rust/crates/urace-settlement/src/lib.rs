//! R-11: Economic settlement — EVM stub + Lightning Network rail.
//!
//! Settlement rails:
//! - `evm`       — EVM JSON-RPC stub (ported from `eth_settlement_adapter.py`)
//! - `lightning` — Lightning Network via ldk-node (feature-gated, MIT)
//! - `none`      — internal UCR accounting only
//!
//! UCR stays as internal accounting unit.
//! Settlement rails are external only — activated by operator config.
//!
//! TopologyLock and ArchitectureCertificate stubs are intentionally preserved
//! (see `eth_settlement_adapter.py` invariant).

use serde::{Deserialize, Serialize};
use thiserror::Error;

#[derive(Debug, Error)]
pub enum SettlementError {
    #[error("RPC error: {0}")]
    Rpc(String),
    #[error("settlement rail not configured: {0}")]
    NotConfigured(String),
    #[error("transaction simulation failed: {0}")]
    SimulationFailed(String),
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub enum SettlementRail {
    Evm,
    Lightning,
    None,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SettlementResult {
    pub status: String,
    pub tx_hash: Option<String>,
    pub error: Option<String>,
    pub rail: SettlementRail,
}

/// TopologyLock — immutable record of a committed model-split topology.
/// Intentionally a stub; full implementation deferred to Phase X3.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TopologyLock {
    pub version: u64,
    pub model_ref: String,
    pub manifest_sha256: String,
    pub stages: Vec<TopologyStage>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TopologyStage {
    pub node: String,
    pub layer_start: u32,
    pub layer_end: u32,
}

/// ArchitectureCertificate — stub, intentionally preserved.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ArchitectureCertificate {
    pub topology_version: u64,
    pub certified_at: String,
    pub certifier_id: String,
    pub signature_hex: String,
}

pub mod evm;
pub mod lightning;
pub mod mesh_llm_passthrough;
pub mod settlement_manager;
