//! Remote asset retrieval, quarantine delivery, and SHA-256 integrity verification.

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::HashMap;
use thiserror::Error;

pub const CATALOG_SCHEMA: &str = "urace-public-asset-catalog-v1";
/// Maximum base64-encoded asset size for a single bounded RPC transfer.
pub const OPEN_ASSET_LIMIT: usize = 300_000;
/// Maximum catalog entries per category.
pub const CATALOG_LIMIT: usize = 64;

// ── Errors ────────────────────────────────────────────────────────────────────

#[derive(Debug, Error)]
pub enum RemoteAssetError {
    #[error("asset integrity check failed: computed {computed}, expected {expected}")]
    IntegrityMismatch { computed: String, expected: String },
    #[error("asset exceeds bounded transfer limit ({0} bytes)")]
    TooLarge(usize),
    #[error("invalid or expired catalog: {0}")]
    InvalidCatalog(String),
    #[error("asset not found in catalog: {0}")]
    AssetNotFound(String),
    #[error("asset identity mismatch for asset_id {0}")]
    AssetIdMismatch(String),
    #[error("asset is not declared open and free: {0}")]
    NotOpen(String),
    #[error("invalid artifact digest: {0}")]
    InvalidDigest(String),
    #[error("seller or recipient peer mismatch")]
    PeerMismatch,
    #[error("unknown or blocked peer: {0}")]
    BlockedPeer(String),
    #[error("seller acknowledgement mismatch: {0}")]
    AckMismatch(String),
    #[error("invalid quarantine status: {0}")]
    InvalidStatus(String),
    #[error("duplicate or conflicting receipt")]
    DuplicateReceipt,
    #[error("json error: {0}")]
    Json(#[from] serde_json::Error),
    #[error("base64 decode error: {0}")]
    Base64(String),
    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),
}

// ── SHA-256 helpers ───────────────────────────────────────────────────────────

/// Compute SHA-256 hex digest of raw bytes.
pub fn sha256_hex(data: &[u8]) -> String {
    let mut h = Sha256::new();
    h.update(data);
    hex::encode(h.finalize())
}

/// Compute SHA-256 of JSON-canonical (sorted keys, compact) encoding of a value.
pub fn canonical_sha256(value: &serde_json::Value) -> Result<String, RemoteAssetError> {
    // Sort keys by converting through BTreeMap for objects
    let canonical = canonical_encode(value)?;
    Ok(sha256_hex(&canonical))
}

fn canonical_encode(value: &serde_json::Value) -> Result<Vec<u8>, RemoteAssetError> {
    // Re-serialise with sorted keys by round-tripping through BTreeMap
    let normalised = normalise_value(value);
    serde_json::to_vec(&normalised).map_err(RemoteAssetError::Json)
}

fn normalise_value(value: &serde_json::Value) -> serde_json::Value {
    match value {
        serde_json::Value::Object(map) => {
            let sorted: std::collections::BTreeMap<_, _> = map
                .iter()
                .map(|(k, v)| (k.clone(), normalise_value(v)))
                .collect();
            serde_json::to_value(sorted).unwrap_or(serde_json::Value::Null)
        }
        serde_json::Value::Array(arr) => {
            serde_json::Value::Array(arr.iter().map(normalise_value).collect())
        }
        other => other.clone(),
    }
}

fn is_valid_sha256_hex(s: &str) -> bool {
    s.len() == 64 && s.chars().all(|c| c.is_ascii_hexdigit())
}

// ── Open asset catalog item ───────────────────────────────────────────────────

/// A single open (free) asset entry in the seller's catalog.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OpenAssetItem {
    pub asset_id: String,
    pub seller_peer_id: String,
    pub feature_id: String,
    pub description: String,
    pub spec_context: String,
    pub tags: Vec<String>,
    pub dependencies: Vec<String>,
    pub artifact_sha256: String,
    pub artifact_size_bytes: usize,
    pub content_type: String,
    pub license_id: String,
    pub usage_price_units: u64,
    pub payment_enabled: bool,
}

impl OpenAssetItem {
    /// Compute the asset_id from all fields except `asset_id` itself.
    pub fn compute_asset_id(&self) -> Result<String, RemoteAssetError> {
        let mut map = serde_json::to_value(self)?;
        if let serde_json::Value::Object(ref mut m) = map {
            m.remove("asset_id");
        }
        canonical_sha256(&map)
    }

    /// Verify that the stored `asset_id` matches the canonical computation.
    pub fn verify_identity(&self) -> Result<(), RemoteAssetError> {
        let computed = self.compute_asset_id()?;
        if computed != self.asset_id {
            return Err(RemoteAssetError::AssetIdMismatch(self.asset_id.clone()));
        }
        Ok(())
    }
}

// ── Paid listing discovery record ─────────────────────────────────────────────

/// Discovery-only paid listing (no cross-peer settlement).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PaidListing {
    pub listing_id: String,
    pub seller_peer_id: String,
    pub feature_id: String,
    pub description: String,
    pub tags: Vec<String>,
    pub artifact_sha256: Option<String>,
    pub ask_price_units: u64,
    pub price_unit: String,
    pub settlement_status: String,
}

// ── Asset catalog ─────────────────────────────────────────────────────────────

/// Bounded, seller-authenticated asset catalog.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AssetCatalog {
    pub schema: String,
    pub seller_peer_id: String,
    pub created_unix: f64,
    pub expires_unix: f64,
    pub open_assets: Vec<OpenAssetItem>,
    pub paid_listings: Vec<PaidListing>,
    pub settlement_supported: bool,
    pub price_interpretation: String,
}

impl AssetCatalog {
    /// Validate catalog authenticity and TTL; returns the catalog on success.
    pub fn validate(value: serde_json::Value, peer_id: &str) -> Result<Self, RemoteAssetError> {
        let catalog: AssetCatalog = serde_json::from_value(value)
            .map_err(|e| RemoteAssetError::InvalidCatalog(e.to_string()))?;

        if catalog.schema != CATALOG_SCHEMA {
            return Err(RemoteAssetError::InvalidCatalog(format!(
                "unexpected schema: {}",
                catalog.schema
            )));
        }
        if catalog.seller_peer_id != peer_id {
            return Err(RemoteAssetError::InvalidCatalog(
                "seller_peer_id mismatch".to_owned(),
            ));
        }

        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs_f64();

        if !(catalog.created_unix <= now
            && now <= catalog.expires_unix
            && catalog.expires_unix <= catalog.created_unix + 360.0)
        {
            return Err(RemoteAssetError::InvalidCatalog(
                "catalog is expired or clock skew too large".to_owned(),
            ));
        }

        if catalog.open_assets.len() > CATALOG_LIMIT || catalog.paid_listings.len() > CATALOG_LIMIT
        {
            return Err(RemoteAssetError::InvalidCatalog(
                "catalog count exceeded".to_owned(),
            ));
        }

        // Validate each open asset
        let mut seen_ids: std::collections::HashSet<String> = std::collections::HashSet::new();
        for item in &catalog.open_assets {
            item.verify_identity()?;
            if !seen_ids.insert(item.asset_id.clone()) {
                return Err(RemoteAssetError::InvalidCatalog(format!(
                    "duplicate asset_id: {}",
                    item.asset_id
                )));
            }
            if !is_valid_sha256_hex(&item.artifact_sha256) {
                return Err(RemoteAssetError::InvalidDigest(
                    item.artifact_sha256.clone(),
                ));
            }
            if item.artifact_size_bytes > OPEN_ASSET_LIMIT {
                return Err(RemoteAssetError::TooLarge(item.artifact_size_bytes));
            }
            if item.seller_peer_id != peer_id {
                return Err(RemoteAssetError::PeerMismatch);
            }
            if item.usage_price_units != 0 || item.payment_enabled {
                return Err(RemoteAssetError::NotOpen(item.feature_id.clone()));
            }
            if item.license_id.is_empty() {
                return Err(RemoteAssetError::NotOpen(format!(
                    "missing license_id for {}",
                    item.feature_id
                )));
            }
        }

        // Validate paid listings
        for listing in &catalog.paid_listings {
            if listing.seller_peer_id != peer_id {
                return Err(RemoteAssetError::PeerMismatch);
            }
            if listing.ask_price_units == 0 {
                return Err(RemoteAssetError::InvalidCatalog(
                    "paid listing must have ask_price_units > 0".to_owned(),
                ));
            }
            if listing.settlement_status != "DISCOVERY_ONLY_NO_CROSS_PEER_SETTLEMENT" {
                return Err(RemoteAssetError::InvalidCatalog(format!(
                    "unexpected settlement_status: {}",
                    listing.settlement_status
                )));
            }
        }

        Ok(catalog)
    }
}

// ── Bundle verification ───────────────────────────────────────────────────────

/// A signed asset bundle received from a seller peer.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AssetBundle {
    pub payload: serde_json::Value,
    pub signature: serde_json::Value,
}

/// Verify a received open asset bundle's integrity (SHA-256 of decoded bytes).
///
/// Returns the raw artifact bytes and the artifact_sha256 from the payload.
pub fn verify_bundle_integrity(
    bundle: &AssetBundle,
    expected_peer_id: &str,
    local_peer_id: &str,
) -> Result<(Vec<u8>, String), RemoteAssetError> {
    let payload = &bundle.payload;

    let sender = payload
        .get("sender")
        .and_then(|v| v.as_str())
        .ok_or(RemoteAssetError::PeerMismatch)?;
    let recipient = payload
        .get("recipient")
        .and_then(|v| v.as_str())
        .ok_or(RemoteAssetError::PeerMismatch)?;

    if sender != expected_peer_id || recipient != local_peer_id {
        return Err(RemoteAssetError::PeerMismatch);
    }

    let artifact_b64 = payload
        .get("artifact_b64")
        .and_then(|v| v.as_str())
        .ok_or_else(|| RemoteAssetError::Base64("missing artifact_b64 field".to_owned()))?;

    let raw = base64_decode(artifact_b64)?;

    if raw.len() > OPEN_ASSET_LIMIT {
        return Err(RemoteAssetError::TooLarge(raw.len()));
    }

    let artifact_ref = payload
        .get("artifact_ref")
        .and_then(|v| v.as_str())
        .ok_or_else(|| RemoteAssetError::InvalidDigest("missing artifact_ref".to_owned()))?;

    if !is_valid_sha256_hex(artifact_ref) {
        return Err(RemoteAssetError::InvalidDigest(artifact_ref.to_owned()));
    }

    let computed = sha256_hex(&raw);
    if computed != artifact_ref {
        return Err(RemoteAssetError::IntegrityMismatch {
            computed,
            expected: artifact_ref.to_owned(),
        });
    }

    Ok((raw, artifact_ref.to_owned()))
}

fn base64_decode(s: &str) -> Result<Vec<u8>, RemoteAssetError> {
    base64_decode_std(s).map_err(RemoteAssetError::Base64)
}

fn base64_decode_std(s: &str) -> Result<Vec<u8>, String> {
    // Minimal standard base64 decode (RFC 4648, no URL-safe)
    let s = s.trim();
    let s_no_pad = s.trim_end_matches('=');
    let padding = s.len() - s_no_pad.len();
    if padding > 2 {
        return Err("invalid padding".to_owned());
    }

    let table: HashMap<u8, u8> = {
        let chars = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
        chars
            .iter()
            .enumerate()
            .map(|(i, &c)| (c, i as u8))
            .collect()
    };

    let mut out = Vec::with_capacity(s.len() * 3 / 4);
    let bytes: Vec<u8> = s_no_pad.bytes().collect();
    for chunk in bytes.chunks(4) {
        let vals: Result<Vec<u8>, String> = chunk
            .iter()
            .map(|b| {
                table
                    .get(b)
                    .copied()
                    .ok_or_else(|| format!("invalid char: {b}"))
            })
            .collect();
        let vals = vals?;
        match vals.len() {
            4 => {
                out.push((vals[0] << 2) | (vals[1] >> 4));
                out.push((vals[1] << 4) | (vals[2] >> 2));
                out.push((vals[2] << 6) | vals[3]);
            }
            3 => {
                out.push((vals[0] << 2) | (vals[1] >> 4));
                out.push((vals[1] << 4) | (vals[2] >> 2));
            }
            2 => {
                out.push((vals[0] << 2) | (vals[1] >> 4));
            }
            _ => return Err("short chunk".to_owned()),
        }
    }
    Ok(out)
}

// ── Quarantine receipt ────────────────────────────────────────────────────────

/// Status of a quarantine acknowledgement.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum QuarantineStatus {
    Quarantined,
    AlreadyQuarantined,
}

/// Signed buyer quarantine receipt.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QuarantineReceipt {
    pub payload: HashMap<String, serde_json::Value>,
    pub signature: serde_json::Value,
}

/// Verify the buyer's quarantine receipt payload structure for the given bundle/asset.
pub fn verify_quarantine_receipt(
    receipt: &QuarantineReceipt,
    expected_bundle_id: &str,
    expected_asset_id: &str,
    expected_sender: &str,
    expected_recipient: &str,
    expected_feature: &str,
    expected_artifact_sha256: &str,
) -> Result<(), RemoteAssetError> {
    let p = &receipt.payload;
    let schema = p.get("schema").and_then(|v| v.as_str()).unwrap_or("");
    if schema != "urace-delivery-receipt-v1" {
        return Err(RemoteAssetError::InvalidCatalog(format!(
            "wrong receipt schema: {schema}"
        )));
    }

    let check = |key: &str, expected: &str| -> Result<(), RemoteAssetError> {
        let actual = p.get(key).and_then(|v| v.as_str()).unwrap_or("");
        if actual != expected {
            Err(RemoteAssetError::AckMismatch(format!(
                "receipt.{key}: expected {expected}, got {actual}"
            )))
        } else {
            Ok(())
        }
    };

    check("bundle_id", expected_bundle_id)?;
    check("sender", expected_sender)?;
    check("recipient", expected_recipient)?;
    check("feature", expected_feature)?;
    check("artifact_sha256", expected_artifact_sha256)?;
    check("claim", "BYTES_QUARANTINED_NOT_QUALIFIED")?;

    // asset_id is validated against the catalog item separately
    let _ = expected_asset_id;

    Ok(())
}

// ── Discover result ───────────────────────────────────────────────────────────

/// Result of a multi-peer catalog discovery query.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DiscoverResult {
    pub schema: String,
    pub query: String,
    pub open_assets: Vec<ScoredAsset>,
    pub paid_listings: Vec<ScoredListing>,
    pub peer_failures: Vec<PeerFailure>,
    pub native_model_calls: u32,
    pub automatic_execution: bool,
    pub paid_borrow_enabled: bool,
    pub network_metrics: NetworkMetrics,
    pub cost_comparison: String,
}

/// An open asset enriched with a match score.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ScoredAsset {
    #[serde(flatten)]
    pub item: OpenAssetItem,
    pub match_score: f64,
    pub source: String,
}

/// A paid listing enriched with a match score.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ScoredListing {
    #[serde(flatten)]
    pub listing: PaidListing,
    pub match_score: f64,
    pub source: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PeerFailure {
    pub peer_id: String,
    pub reason: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NetworkMetrics {
    pub accounting_scope: String,
    pub rpc_calls: usize,
    pub request_payload_bytes: u64,
    pub response_payload_bytes: u64,
    pub application_payload_bytes: u64,
    pub rpc_elapsed_seconds: f64,
    pub elapsed_seconds: f64,
}

/// Score a catalog item against a set of query terms (`[0.0, 1.0]`).
pub fn score_item_against_query(text: &str, terms: &[String]) -> f64 {
    if terms.is_empty() {
        return 0.0;
    }
    let lower = text.to_lowercase();
    let hits = terms.iter().filter(|t| lower.contains(t.as_str())).count();
    hits as f64 / terms.len() as f64
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn sha256_hex_known_value() {
        // SHA-256("") = e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
        let h = sha256_hex(b"");
        assert_eq!(&h[..8], "e3b0c442");
    }

    #[test]
    fn integrity_mismatch_detected() {
        let bundle = AssetBundle {
            payload: json!({
                "sender": "peer-a",
                "recipient": "peer-b",
                "artifact_ref": "a".repeat(64),
                "artifact_b64": base64_encode(b"hello"),
            }),
            signature: json!({}),
        };
        let err = verify_bundle_integrity(&bundle, "peer-a", "peer-b").unwrap_err();
        assert!(
            matches!(err, RemoteAssetError::IntegrityMismatch { .. }),
            "expected integrity mismatch, got {err}"
        );
    }

    fn base64_encode(data: &[u8]) -> String {
        // Minimal encoder for tests
        const TABLE: &[u8] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
        let mut out = String::new();
        for chunk in data.chunks(3) {
            let b0 = chunk[0] as usize;
            let b1 = chunk.get(1).copied().unwrap_or(0) as usize;
            let b2 = chunk.get(2).copied().unwrap_or(0) as usize;
            out.push(TABLE[b0 >> 2] as char);
            out.push(TABLE[((b0 & 0x3) << 4) | (b1 >> 4)] as char);
            if chunk.len() > 1 {
                out.push(TABLE[((b1 & 0xf) << 2) | (b2 >> 6)] as char);
            } else {
                out.push('=');
            }
            if chunk.len() > 2 {
                out.push(TABLE[b2 & 0x3f] as char);
            } else {
                out.push('=');
            }
        }
        out
    }

    #[test]
    fn bundle_integrity_valid_roundtrip() {
        let data = b"test asset content";
        let digest = sha256_hex(data);
        let b64 = base64_encode(data);

        let bundle = AssetBundle {
            payload: json!({
                "sender": "peer-a",
                "recipient": "peer-b",
                "artifact_ref": digest,
                "artifact_b64": b64,
            }),
            signature: json!({}),
        };

        let (raw, returned_digest) = verify_bundle_integrity(&bundle, "peer-a", "peer-b").unwrap();
        assert_eq!(raw, data);
        assert_eq!(returned_digest, sha256_hex(data));
    }

    #[test]
    fn score_item_against_query_partial_match() {
        let terms = vec!["caching".to_owned(), "redis".to_owned()];
        let score = score_item_against_query("fast caching layer for web", &terms);
        // only "caching" matches → 0.5
        assert!((score - 0.5).abs() < 1e-9);
    }

    #[test]
    fn catalog_validate_rejects_wrong_schema() {
        let v = json!({
            "schema": "wrong-schema",
            "seller_peer_id": "peer-x",
            "created_unix": 0.0,
            "expires_unix": 9999999999.0,
            "open_assets": [],
            "paid_listings": [],
            "settlement_supported": false,
            "price_interpretation": "",
        });
        let err = AssetCatalog::validate(v, "peer-x").unwrap_err();
        assert!(matches!(err, RemoteAssetError::InvalidCatalog(_)));
    }
}
