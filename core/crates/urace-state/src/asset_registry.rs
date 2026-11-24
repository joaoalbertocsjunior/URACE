//! Asset registry — earn-backed asset certificates with two-track reputation.
//!
//! Ported from `asset_registry.py`. Tracks off-chain asset ownership and earn
//! accumulation. DashMap-backed for read-heavy peer lookup; all state changes
//! are journalled as append-only audit rows.

use dashmap::DashMap;
use serde::{Deserialize, Serialize};
use serde_json::json;
use std::sync::Arc;
use std::time::{SystemTime, UNIX_EPOCH};
use thiserror::Error;
use urace_ledger::{Journal, JournalError};

pub const BORROW_TAX_RATE: f64 = 0.15;
pub const SCHEMA: &str = "urace-asset-registry-v1";

fn now_unix() -> f64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs_f64())
        .unwrap_or(0.0)
}

#[derive(Debug, Error)]
pub enum AssetError {
    #[error("journal error: {0}")]
    Journal(#[from] JournalError),
    #[error("asset not found: {0}")]
    NotFound(String),
    #[error("not owner: expected {expected}, got {actual}")]
    NotOwner { expected: String, actual: String },
    #[error("duplicate fingerprint: {0}")]
    DuplicateFingerprint(String),
    #[error("self-borrow blocked for asset {0}")]
    SelfBorrow(String),
    #[error("transfer already pending for {0}")]
    TransferPending(String),
    #[error("transfer not found for {0}")]
    TransferNotFound(String),
    #[error("transfer expired for {0}")]
    TransferExpired(String),
    #[error("wrong recipient: expected {expected}, got {actual}")]
    WrongRecipient { expected: String, actual: String },
    #[error("pending challenge blocks transfer for {0}")]
    PendingChallenge(String),
}

/// Snapshot of an asset's current state.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Asset {
    pub feature_id: String,
    pub owner_peer_id: String,
    pub canonical_fingerprint: Option<String>,
    pub nft_token_id: Option<String>,
    pub cumulative_earn_units: u64,
    pub total_uses: usize,
    pub transfer_count: usize,
    pub registered_at: f64,
}

/// DashMap-backed, Journal-audited asset registry.
pub struct AssetRegistry {
    /// feature_id → Asset snapshot (derived from journal on load, then kept up-to-date).
    assets: Arc<DashMap<String, Asset>>,
    journal: Arc<Journal>,
}

impl AssetRegistry {
    /// Open (or create) an asset registry with the given journal.
    pub fn open(journal: Journal) -> Result<Self, AssetError> {
        let registry = AssetRegistry {
            assets: Arc::new(DashMap::new()),
            journal: Arc::new(journal),
        };
        registry.replay()?;
        Ok(registry)
    }

    fn replay(&self) -> Result<(), AssetError> {
        let entries = self.journal.verify_integrity()?;
        for entry in &entries {
            let p = &entry.payload;
            match entry.kind.as_str() {
                "ASSET_REGISTERED" => {
                    let fid = p["feature_id"].as_str().unwrap_or("").to_owned();
                    if !fid.is_empty() {
                        self.assets.insert(
                            fid.clone(),
                            Asset {
                                feature_id: fid,
                                owner_peer_id: p["owner_peer_id"]
                                    .as_str()
                                    .unwrap_or("")
                                    .to_owned(),
                                canonical_fingerprint: p["canonical_fingerprint"]
                                    .as_str()
                                    .filter(|s| !s.is_empty())
                                    .map(str::to_owned),
                                nft_token_id: p["nft_token_id"]
                                    .as_str()
                                    .filter(|s| !s.is_empty())
                                    .map(str::to_owned),
                                cumulative_earn_units: 0,
                                total_uses: 0,
                                transfer_count: 0,
                                registered_at: p["at_unix"].as_f64().unwrap_or(0.0),
                            },
                        );
                    }
                }
                "ASSET_TRANSFERRED" => {
                    let fid = p["feature_id"].as_str().unwrap_or("").to_owned();
                    if let Some(mut asset) = self.assets.get_mut(&fid) {
                        asset.owner_peer_id =
                            p["to_peer_id"].as_str().unwrap_or("").to_owned();
                        asset.transfer_count += 1;
                    }
                }
                "ASSET_EARN" => {
                    let fid = p["feature_id"].as_str().unwrap_or("").to_owned();
                    let units = p["earn_units"].as_u64().unwrap_or(0);
                    if let Some(mut asset) = self.assets.get_mut(&fid) {
                        asset.cumulative_earn_units += units;
                        asset.total_uses += 1;
                    }
                }
                _ => {}
            }
        }
        Ok(())
    }

    /// Register a new asset. Idempotent; returns existing record status if already registered.
    pub fn register(
        &self,
        feature_id: &str,
        creator_peer_id: &str,
        canonical_fingerprint: Option<&str>,
        nft_token_id: Option<&str>,
    ) -> Result<&'static str, AssetError> {
        if self.assets.contains_key(feature_id) {
            return Ok("already_registered");
        }
        // Duplicate fingerprint check
        if let Some(fp) = canonical_fingerprint {
            for entry in self.assets.iter() {
                if entry.canonical_fingerprint.as_deref() == Some(fp) {
                    return Err(AssetError::DuplicateFingerprint(fp.to_owned()));
                }
            }
        }
        let now = now_unix();
        self.journal.append(
            "ASSET_REGISTERED",
            json!({
                "schema": SCHEMA,
                "feature_id": feature_id,
                "owner_peer_id": creator_peer_id,
                "canonical_fingerprint": canonical_fingerprint.unwrap_or(""),
                "nft_token_id": nft_token_id.unwrap_or(""),
                "cumulative_earn_units": 0,
                "at_unix": now,
            }),
        )?;
        self.assets.insert(
            feature_id.to_owned(),
            Asset {
                feature_id: feature_id.to_owned(),
                owner_peer_id: creator_peer_id.to_owned(),
                canonical_fingerprint: canonical_fingerprint.map(str::to_owned),
                nft_token_id: nft_token_id.map(str::to_owned),
                cumulative_earn_units: 0,
                total_uses: 0,
                transfer_count: 0,
                registered_at: now,
            },
        );
        Ok("registered")
    }

    /// Record a usage earn event (royalty to owner, borrow tax from borrower).
    pub fn record_usage_earn(
        &self,
        feature_id: &str,
        usage_peer_id: &str,
        earn_units: u64,
        borrow_tax_rate: Option<f64>,
    ) -> Result<(), AssetError> {
        let owner = {
            let asset = self
                .assets
                .get(feature_id)
                .ok_or_else(|| AssetError::NotFound(feature_id.to_owned()))?;
            asset.owner_peer_id.clone()
        };
        if usage_peer_id == owner {
            return Err(AssetError::SelfBorrow(feature_id.to_owned()));
        }
        let rate = borrow_tax_rate.unwrap_or(BORROW_TAX_RATE);
        let tax_units = ((earn_units as f64 * rate) as u64).max(1);
        let now = now_unix();
        // Update in-memory
        if let Some(mut asset) = self.assets.get_mut(feature_id) {
            asset.cumulative_earn_units += earn_units;
            asset.total_uses += 1;
        }
        self.journal.append(
            "ASSET_EARN",
            json!({
                "schema": SCHEMA,
                "feature_id": feature_id,
                "owner_peer_id": owner,
                "usage_peer_id": usage_peer_id,
                "earn_units": earn_units,
                "borrow_tax_units": tax_units,
                "at_unix": now,
            }),
        )?;
        Ok(())
    }

    /// Transfer ownership. Two-phase: journal ASSET_TRANSFERRED and update DashMap.
    pub fn transfer(
        &self,
        feature_id: &str,
        from_peer_id: &str,
        to_peer_id: &str,
    ) -> Result<(), AssetError> {
        {
            let asset = self
                .assets
                .get(feature_id)
                .ok_or_else(|| AssetError::NotFound(feature_id.to_owned()))?;
            if asset.owner_peer_id != from_peer_id {
                return Err(AssetError::NotOwner {
                    expected: from_peer_id.to_owned(),
                    actual: asset.owner_peer_id.clone(),
                });
            }
        }
        let now = now_unix();
        self.journal.append(
            "ASSET_TRANSFERRED",
            json!({
                "schema": SCHEMA,
                "feature_id": feature_id,
                "from_peer_id": from_peer_id,
                "to_peer_id": to_peer_id,
                "at_unix": now,
            }),
        )?;
        if let Some(mut asset) = self.assets.get_mut(feature_id) {
            asset.owner_peer_id = to_peer_id.to_owned();
            asset.transfer_count += 1;
        }
        Ok(())
    }

    /// Look up an asset by feature_id.
    pub fn get(&self, feature_id: &str) -> Option<Asset> {
        self.assets.get(feature_id).map(|a| a.clone())
    }

    /// All assets owned by a peer, sorted by cumulative_earn_units descending.
    pub fn portfolio(&self, peer_id: &str) -> Vec<Asset> {
        let mut v: Vec<Asset> = self
            .assets
            .iter()
            .filter(|e| e.owner_peer_id == peer_id)
            .map(|e| e.clone())
            .collect();
        v.sort_by(|a, b| b.cumulative_earn_units.cmp(&a.cumulative_earn_units));
        v
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    const KEY: [u8; 32] = *b"asset-registry-key-32bytes-pad--";

    fn make_registry() -> (TempDir, AssetRegistry) {
        let dir = TempDir::new().unwrap();
        let j = Journal::open(dir.path().join("assets.jsonl"), KEY).unwrap();
        let reg = AssetRegistry::open(j).unwrap();
        (dir, reg)
    }

    #[test]
    fn register_and_lookup() {
        let (_dir, r) = make_registry();
        r.register("feat-1", "peer-a", Some("fp1"), None).unwrap();
        let a = r.get("feat-1").unwrap();
        assert_eq!(a.owner_peer_id, "peer-a");
    }

    #[test]
    fn idempotent_register() {
        let (_dir, r) = make_registry();
        r.register("feat-1", "peer-a", None, None).unwrap();
        let status = r.register("feat-1", "peer-b", None, None).unwrap();
        assert_eq!(status, "already_registered");
        // Owner unchanged
        assert_eq!(r.get("feat-1").unwrap().owner_peer_id, "peer-a");
    }

    #[test]
    fn duplicate_fingerprint_blocked() {
        let (_dir, r) = make_registry();
        r.register("feat-1", "peer-a", Some("fp1"), None).unwrap();
        assert!(r.register("feat-2", "peer-b", Some("fp1"), None).is_err());
    }

    #[test]
    fn self_borrow_blocked() {
        let (_dir, r) = make_registry();
        r.register("feat-1", "peer-a", None, None).unwrap();
        assert!(r.record_usage_earn("feat-1", "peer-a", 100, None).is_err());
    }

    #[test]
    fn earn_and_transfer() {
        let (_dir, r) = make_registry();
        r.register("feat-1", "peer-a", None, None).unwrap();
        r.record_usage_earn("feat-1", "peer-b", 50, None).unwrap();
        assert_eq!(r.get("feat-1").unwrap().cumulative_earn_units, 50);
        r.transfer("feat-1", "peer-a", "peer-b").unwrap();
        assert_eq!(r.get("feat-1").unwrap().owner_peer_id, "peer-b");
    }

    #[test]
    fn portfolio_sorted_by_earn() {
        let (_dir, r) = make_registry();
        r.register("feat-1", "peer-a", None, None).unwrap();
        r.register("feat-2", "peer-a", None, None).unwrap();
        r.record_usage_earn("feat-2", "peer-b", 100, None).unwrap();
        r.record_usage_earn("feat-1", "peer-b", 10, None).unwrap();
        let p = r.portfolio("peer-a");
        assert_eq!(p[0].feature_id, "feat-2");
    }
}
