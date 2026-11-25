//! Chain anchor — publishes ledger seals and stake/asset events to an EVM contract.
//!
//! Ported from `chain_anchor.py` (Phase 1: enabled=false stub pattern).
//! Phase 1 (current): all publish calls are no-ops when `enabled = false`.
//! Phase 2+: live EVM calls via submit_live(); stub is intentional until alloy wiring.
//! §62z: any on-chain anchor that constitutes a spend must route through authority.

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use thiserror::Error;

// ---------------------------------------------------------------------------
// Error type
// ---------------------------------------------------------------------------

#[derive(Debug, Error)]
pub enum ChainAnchorError {
    #[error("chain anchor not enabled")]
    NotEnabled,
    #[error("contract address not configured: {0}")]
    NotConfigured(String),
    #[error("no wallet key available — cannot submit tx")]
    NoWallet,
    #[error("live EVM submission not yet implemented: {0}")]
    LiveNotImplemented(String),
    #[error("serialization error: {0}")]
    Serialization(String),
}

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------

/// Runtime configuration for chain_anchor (fields under `ledger.chain_anchor`).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChainAnchorConfig {
    /// Enable or disable all on-chain anchoring (Phase 2+: set true).
    pub enabled: bool,
    /// Target network identifier.
    pub network: String,
    /// JSON-RPC endpoint URL (Infura / Alchemy / public).
    pub rpc_url: Option<String>,
    /// Deployed HashRegistry contract address.
    pub hash_registry_address: Option<String>,
    /// Deployed StakeLedger contract address.
    pub stake_ledger_address: Option<String>,
    /// Deployed AssetRegistry contract address.
    pub asset_registry_address: Option<String>,
    /// Environment variable name holding the hex private key (never hardcode).
    pub wallet_key_env: String,
    /// Log tx but do not broadcast — safe default.
    pub dry_run: bool,
    /// Gas limit for contract calls.
    pub gas_limit: u64,
    /// Anchor every N seals (1 = every seal).
    pub publish_every_n_seals: u32,
}

impl Default for ChainAnchorConfig {
    fn default() -> Self {
        ChainAnchorConfig {
            enabled: false,
            network: "polygon-amoy".into(),
            rpc_url: None,
            hash_registry_address: None,
            stake_ledger_address: None,
            asset_registry_address: None,
            wallet_key_env: "URACE_CHAIN_KEY".into(),
            dry_run: true,
            gas_limit: 60_000,
            publish_every_n_seals: 1,
        }
    }
}

// ---------------------------------------------------------------------------
// Records
// ---------------------------------------------------------------------------

/// Payload for a ledger block seal anchor.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SealRow {
    pub block_hash: String,
    pub block_height: u64,
    pub rows_hash: String,
    pub at_unix: u64,
}

/// Stake event kinds mirroring the Python constants.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum StakeKind {
    StakeMint,
    StakeSlash,
    StakeResolve,
}

impl StakeKind {
    #[allow(dead_code)] // used when live-call stubs are filled in
    fn as_u8(self) -> u8 {
        match self {
            StakeKind::StakeMint => 0,
            StakeKind::StakeSlash => 1,
            StakeKind::StakeResolve => 2,
        }
    }
}

/// Payload for a stake event anchor.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StakeEvent {
    pub kind: StakeKind,
    pub feature_id: String,
    pub peer_id: String,
    pub amount_units: u64,
    pub at_unix: u64,
}

/// Payload for an asset earning anchor.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AssetEarning {
    pub feature_id: String,
    pub owner_peer_id: String,
    pub earn_units: u64,
    pub cumulative_earn_units: u64,
    pub at_unix: u64,
}

/// Payload for an asset transfer anchor.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AssetTransfer {
    pub feature_id: String,
    pub from_peer_id: String,
    pub to_peer_id: String,
    pub cumulative_earn_at_transfer: u64,
    pub at_unix: u64,
}

// ---------------------------------------------------------------------------
// Anchor receipt
// ---------------------------------------------------------------------------

/// Result of an anchor publish call.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AnchorReceipt {
    /// True when the call was recorded but not broadcast (dry_run=true).
    pub dry_run: bool,
    /// Transaction hash on success (hex string with 0x prefix).
    pub tx_hash: Option<String>,
    /// EVM status code (1 = success) on live call.
    pub status: Option<u8>,
    /// Echo of the block height (for seal receipts).
    pub block_height: Option<u64>,
    /// Echo of the feature_id (for asset/stake receipts).
    pub feature_id: Option<String>,
    /// Echo of the kind (for stake receipts).
    pub kind: Option<String>,
}

// ---------------------------------------------------------------------------
// Adapter
// ---------------------------------------------------------------------------

/// Thin adapter over the EVM contracts for chain anchoring.
pub struct ChainAnchorAdapter {
    config: ChainAnchorConfig,
}

impl ChainAnchorAdapter {
    pub fn new(config: ChainAnchorConfig) -> Self {
        ChainAnchorAdapter { config }
    }

    pub fn with_defaults() -> Self {
        ChainAnchorAdapter {
            config: ChainAnchorConfig::default(),
        }
    }

    /// Anchor a ledger block seal to the HashRegistry contract.
    pub fn publish_seal(&self, seal: &SealRow) -> Result<Option<AnchorReceipt>, ChainAnchorError> {
        if !self.config.enabled {
            return Ok(None);
        }
        let addr = self
            .config
            .hash_registry_address
            .as_deref()
            .filter(|s| !s.is_empty())
            .ok_or_else(|| ChainAnchorError::NotConfigured("hash_registry_address".into()))?;

        if self.config.dry_run {
            tracing::info!(
                "chain_anchor [dry_run] would store seal height={} hash={:.8}... on {}",
                seal.block_height,
                seal.block_hash,
                self.config.network
            );
            return Ok(Some(AnchorReceipt {
                dry_run: true,
                tx_hash: None,
                status: None,
                block_height: Some(seal.block_height),
                feature_id: None,
                kind: None,
            }));
        }

        // §62z: caller must check authority before calling — this path submits a tx (spends gas).
        self.submit_live_seal(seal, addr)
    }

    /// Anchor a stake event (mint/slash/resolve) to the StakeLedger contract.
    pub fn publish_stake_event(
        &self,
        event: &StakeEvent,
    ) -> Result<Option<AnchorReceipt>, ChainAnchorError> {
        if !self.config.enabled {
            return Ok(None);
        }
        let addr = self
            .config
            .stake_ledger_address
            .as_deref()
            .filter(|s| !s.is_empty())
            .ok_or_else(|| ChainAnchorError::NotConfigured("stake_ledger_address".into()))?;

        if self.config.dry_run {
            tracing::info!(
                "chain_anchor [dry_run] would record stake kind={:?} feature={:.12} on {}",
                event.kind,
                event.feature_id,
                self.config.network
            );
            return Ok(Some(AnchorReceipt {
                dry_run: true,
                tx_hash: None,
                status: None,
                block_height: None,
                feature_id: Some(event.feature_id.clone()),
                kind: Some(format!("{:?}", event.kind)),
            }));
        }

        // §62z: caller must check authority before calling — stake events constitute a financial record.
        self.submit_live_stake(event, addr)
    }

    /// Anchor an asset earning event to the AssetRegistry contract (Phase 3.5).
    pub fn publish_asset_earning(
        &self,
        earning: &AssetEarning,
    ) -> Result<Option<AnchorReceipt>, ChainAnchorError> {
        if !self.config.enabled {
            return Ok(None);
        }
        let addr = self
            .config
            .asset_registry_address
            .as_deref()
            .filter(|s| !s.is_empty())
            .ok_or_else(|| ChainAnchorError::NotConfigured("asset_registry_address".into()))?;

        if self.config.dry_run {
            tracing::info!(
                "chain_anchor [dry_run] would record asset earn feature={:.12} +{} (cum={}) on {}",
                earning.feature_id,
                earning.earn_units,
                earning.cumulative_earn_units,
                self.config.network
            );
            return Ok(Some(AnchorReceipt {
                dry_run: true,
                tx_hash: None,
                status: None,
                block_height: None,
                feature_id: Some(earning.feature_id.clone()),
                kind: None,
            }));
        }

        // §62z: caller must check authority before calling — asset earning alters financial state.
        self.submit_live_asset_earning(earning, addr)
    }

    /// Anchor an asset transfer event to the AssetRegistry contract (Phase 3.5).
    pub fn publish_asset_transfer(
        &self,
        transfer: &AssetTransfer,
    ) -> Result<Option<AnchorReceipt>, ChainAnchorError> {
        if !self.config.enabled {
            return Ok(None);
        }
        let addr = self
            .config
            .asset_registry_address
            .as_deref()
            .filter(|s| !s.is_empty())
            .ok_or_else(|| ChainAnchorError::NotConfigured("asset_registry_address".into()))?;

        if self.config.dry_run {
            tracing::info!(
                "chain_anchor [dry_run] would transfer asset feature={:.12} -> {:.12} on {}",
                transfer.feature_id,
                transfer.to_peer_id,
                self.config.network
            );
            return Ok(Some(AnchorReceipt {
                dry_run: true,
                tx_hash: None,
                status: None,
                block_height: None,
                feature_id: Some(transfer.feature_id.clone()),
                kind: None,
            }));
        }

        // §62z: caller must check authority before calling — asset transfer constitutes a spend/ownership change.
        self.submit_live_asset_transfer(transfer, addr)
    }

    /// Return anchor status for inclusion in `urace status` output.
    pub fn status(&self) -> AnchorStatus {
        if !self.config.enabled {
            return AnchorStatus {
                enabled: false,
                network: None,
                connected: false,
                latest_block: None,
                dry_run: self.config.dry_run,
                hash_registry: None,
                stake_ledger: None,
            };
        }
        // TODO(chain-anchor): live block_number probe via JSON-RPC when alloy is wired.
        AnchorStatus {
            enabled: true,
            network: Some(self.config.network.clone()),
            connected: false, // stub — no live RPC yet
            latest_block: None,
            dry_run: self.config.dry_run,
            hash_registry: self.config.hash_registry_address.clone(),
            stake_ledger: self.config.stake_ledger_address.clone(),
        }
    }
}

// ---------------------------------------------------------------------------
// Live-call stubs (intentional; same pattern as evm.rs `submit_live`)
// ---------------------------------------------------------------------------

impl ChainAnchorAdapter {
    /// Submit a seal to HashRegistry on-chain.
    ///
    /// TODO(chain-anchor): Replace stub with:
    ///   1. Encode `store(bytes32,uint64,bytes32)` via ethabi / alloy
    ///   2. Sign with key from `wallet_key_env` (read from env — never hardcode)
    ///   3. Submit via `eth_sendRawTransaction`
    ///   4. Poll `eth_getTransactionReceipt` until confirmed or timeout
    fn submit_live_seal(
        &self,
        _seal: &SealRow,
        _contract_addr: &str,
    ) -> Result<Option<AnchorReceipt>, ChainAnchorError> {
        Err(ChainAnchorError::LiveNotImplemented(
            "live seal submission not yet implemented; waiting for alloy/ethers wiring".into(),
        ))
    }

    /// Submit a stake record to StakeLedger on-chain.
    ///
    /// TODO(chain-anchor): Replace stub with:
    ///   1. Hash feature_id and peer_id via SHA-256 to bytes32
    ///   2. Encode `record(bytes32,bytes32,uint64,uint8)` ABI call
    ///   3. Sign and submit; return tx hash
    fn submit_live_stake(
        &self,
        _event: &StakeEvent,
        _contract_addr: &str,
    ) -> Result<Option<AnchorReceipt>, ChainAnchorError> {
        Err(ChainAnchorError::LiveNotImplemented(
            "live stake submission not yet implemented; waiting for alloy/ethers wiring".into(),
        ))
    }

    /// Submit an asset earning record to AssetRegistry on-chain.
    ///
    /// TODO(chain-anchor): Replace stub with alloy-encoded `recordEarning(bytes32,bytes32,uint64,uint64)` call.
    fn submit_live_asset_earning(
        &self,
        _earning: &AssetEarning,
        _contract_addr: &str,
    ) -> Result<Option<AnchorReceipt>, ChainAnchorError> {
        Err(ChainAnchorError::LiveNotImplemented(
            "live asset earning submission not yet implemented; waiting for alloy/ethers wiring"
                .into(),
        ))
    }

    /// Submit an asset transfer record to AssetRegistry on-chain.
    ///
    /// TODO(chain-anchor): Replace stub with alloy-encoded `transfer(bytes32,bytes32,uint64)` call.
    fn submit_live_asset_transfer(
        &self,
        _transfer: &AssetTransfer,
        _contract_addr: &str,
    ) -> Result<Option<AnchorReceipt>, ChainAnchorError> {
        Err(ChainAnchorError::LiveNotImplemented(
            "live asset transfer submission not yet implemented; waiting for alloy/ethers wiring"
                .into(),
        ))
    }
}

// ---------------------------------------------------------------------------
// Status record
// ---------------------------------------------------------------------------

/// Snapshot of current anchor connectivity.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AnchorStatus {
    pub enabled: bool,
    pub network: Option<String>,
    pub connected: bool,
    pub latest_block: Option<u64>,
    pub dry_run: bool,
    pub hash_registry: Option<String>,
    pub stake_ledger: Option<String>,
}

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

/// Compute SHA-256 of a UTF-8 string, returning a 32-byte array.
pub fn sha256_id(s: &str) -> [u8; 32] {
    let mut h = Sha256::new();
    h.update(s.as_bytes());
    h.finalize().into()
}

/// Decode a hex string (with or without 0x prefix) into a 32-byte array.
/// Pads / truncates to 32 bytes, matching the Python `ljust(64,'0')[:64]` logic.
pub fn hex_to_bytes32(hex: &str) -> [u8; 32] {
    let stripped = hex.strip_prefix("0x").unwrap_or(hex);
    let padded = format!("{:0<64}", stripped);
    let truncated = &padded[..padded.len().min(64)];
    let mut out = [0u8; 32];
    for (i, item) in out.iter_mut().enumerate() {
        let byte_str = truncated.get(i * 2..i * 2 + 2).unwrap_or("00");
        *item = u8::from_str_radix(byte_str, 16).unwrap_or(0);
    }
    out
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    fn disabled_adapter() -> ChainAnchorAdapter {
        ChainAnchorAdapter::with_defaults()
    }

    fn dry_run_adapter() -> ChainAnchorAdapter {
        ChainAnchorAdapter::new(ChainAnchorConfig {
            enabled: true,
            dry_run: true,
            hash_registry_address: Some("0xDeAdBeEfDeAdBeEfDeAdBeEfDeAdBeEf00000001".into()),
            stake_ledger_address: Some("0xDeAdBeEfDeAdBeEfDeAdBeEfDeAdBeEf00000002".into()),
            asset_registry_address: Some("0xDeAdBeEfDeAdBeEfDeAdBeEfDeAdBeEf00000003".into()),
            ..ChainAnchorConfig::default()
        })
    }

    #[test]
    fn disabled_publish_seal_returns_none() {
        let seal = SealRow {
            block_hash: "abc123".into(),
            block_height: 42,
            rows_hash: "def456".into(),
            at_unix: 0,
        };
        let result = disabled_adapter().publish_seal(&seal).unwrap();
        assert!(result.is_none());
    }

    #[test]
    fn dry_run_seal_returns_receipt_without_tx() {
        let seal = SealRow {
            block_hash: "deadbeef".into(),
            block_height: 7,
            rows_hash: "cafebabe".into(),
            at_unix: 100,
        };
        let receipt = dry_run_adapter()
            .publish_seal(&seal)
            .unwrap()
            .expect("expected receipt");
        assert!(receipt.dry_run);
        assert_eq!(receipt.block_height, Some(7));
        assert!(receipt.tx_hash.is_none());
    }

    #[test]
    fn dry_run_stake_event_returns_receipt() {
        let event = StakeEvent {
            kind: StakeKind::StakeMint,
            feature_id: "feat-001".into(),
            peer_id: "peer-abc".into(),
            amount_units: 500,
            at_unix: 200,
        };
        let receipt = dry_run_adapter()
            .publish_stake_event(&event)
            .unwrap()
            .expect("expected receipt");
        assert!(receipt.dry_run);
        assert_eq!(receipt.feature_id.as_deref(), Some("feat-001"));
    }

    #[test]
    fn hex_to_bytes32_pads_short_hex() {
        let b = hex_to_bytes32("ff");
        assert_eq!(b[0], 0xff);
        assert_eq!(b[1], 0x00);
    }

    #[test]
    fn live_call_returns_not_implemented_error() {
        let adapter = ChainAnchorAdapter::new(ChainAnchorConfig {
            enabled: true,
            dry_run: false,
            hash_registry_address: Some("0xDeAdBeEfDeAdBeEfDeAdBeEfDeAdBeEf00000001".into()),
            ..ChainAnchorConfig::default()
        });
        let seal = SealRow {
            block_hash: "aa".into(),
            block_height: 1,
            rows_hash: "bb".into(),
            at_unix: 0,
        };
        let err = adapter.publish_seal(&seal).unwrap_err();
        assert!(matches!(err, ChainAnchorError::LiveNotImplemented(_)));
    }
}
