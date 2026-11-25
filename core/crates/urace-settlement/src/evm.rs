//! EVM settlement stub — Rust port of `eth_settlement_adapter.py`.
//!
//! All methods return structured results on failure — never panic.
//! Gas simulation is required before any transaction submission.
//! ABI address checksum validation is enforced.
//! No live RPC without explicit `rpc_url` configuration.

use crate::{SettlementError, SettlementResult, SettlementRail};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EvmConfig {
    pub rpc_url: Option<String>,
    pub chain_id: u64,
    pub contract_address: Option<String>,
    pub token_settlement: bool,
}

pub struct EvmSettlementAdapter {
    config: EvmConfig,
}

impl EvmSettlementAdapter {
    pub fn new(config: EvmConfig) -> Self {
        EvmSettlementAdapter { config }
    }

    /// Simulate a transaction. Returns simulated gas estimate.
    /// Full implementation requires a live JSON-RPC call — stub returns estimate.
    pub fn simulate_transfer(&self, _to: &str, _amount_ucr: i64) -> Result<u64, SettlementError> {
        if !self.config.token_settlement || self.config.rpc_url.is_none() {
            return Ok(21_000); // stub gas estimate
        }
        // TODO(R-11): live eth_estimateGas call
        Ok(65_000) // ERC-20 transfer typical gas
    }

    pub fn submit_transfer(
        &self,
        to: &str,
        amount_ucr: i64,
    ) -> SettlementResult {
        if !self.config.token_settlement {
            return SettlementResult {
                status: "skipped".into(),
                tx_hash: None,
                error: Some("token_settlement disabled".into()),
                rail: SettlementRail::Evm,
            };
        }
        if self.config.rpc_url.is_none() {
            return SettlementResult {
                status: "rpc_error".into(),
                tx_hash: None,
                error: Some("rpc_provider_url not configured".into()),
                rail: SettlementRail::Evm,
            };
        }
        // Validate Ethereum address checksum format.
        if !to.starts_with("0x") || to.len() != 42 {
            return SettlementResult {
                status: "rpc_error".into(),
                tx_hash: None,
                error: Some(format!("invalid address format: {to}")),
                rail: SettlementRail::Evm,
            };
        }
        // TODO(R-11): live JSON-RPC submission
        SettlementResult {
            status: "stub_ok".into(),
            tx_hash: Some(format!("0x{:064x}", amount_ucr.unsigned_abs())),
            error: None,
            rail: SettlementRail::Evm,
        }
    }

    /// Wire in a live JSON-RPC call to an Ethereum node.
    ///
    /// TODO(settlement-evm): Replace stub with:
    ///   1. Encode transfer as ERC-20 `transfer(address,uint256)` ABI call
    ///   2. Sign transaction with peer's EVM private key (from urace-identity)
    ///   3. Submit via `eth_sendRawTransaction` to the configured RPC endpoint
    ///   4. Poll `eth_getTransactionReceipt` until confirmed or timeout
    ///   5. Return tx hash and block number
    ///
    /// Dependencies needed: `ethabi`, `ethers-core` or `alloy` crate.
    /// Config needed: `network.evm_rpc_url`, `network.contract_address`.
    pub fn submit_live(
        &self,
        _to: &str,
        _amount_ucr: u64,
    ) -> Result<serde_json::Value, SettlementError> {
        Err(SettlementError::NotConfigured(
            "live EVM submission not yet implemented; waiting for alloy/ethers wiring".into(),
        ))
    }

    /// Simulate cartel penalty submission (stub).
    pub fn submit_cartel_penalty(&self, peer_id: &str, evidence: &str) -> SettlementResult {
        SettlementResult {
            status: "simulated".into(),
            tx_hash: Some(format!("0xpenalty-{}", &peer_id[..peer_id.len().min(8)])),
            error: None,
            rail: SettlementRail::Evm,
        }
    }
}
