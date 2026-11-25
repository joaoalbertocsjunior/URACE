//! Read-only policy store for one P2P exchange directory.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use thiserror::Error;

pub const SCHEMA: &str = "urace-exchange-v2";
pub const PROTOCOL_VERSION: u32 = 2;

/// Default policy values, applied when `policy.json` is absent.
fn default_policy() -> ExchangePolicy {
    ExchangePolicy {
        schema: SCHEMA.to_owned(),
        enabled: true,
        network: true,
        advertise: false,
        auto_select: true,
        auto_relay: false,
        token_settlement: false,
        auto_trust_first_contact: false,
        relay_only: false,
        feature_borrow_enabled: false,
        max_transfers_per_day: 20,
        max_transfers_per_peer_per_day: 5,
        max_bytes_per_day: 1_048_576,
        max_rpc_per_day: 200,
        max_rpc_per_peer_per_day: 50,
        min_peer_version: PROTOCOL_VERSION,
        compress_wire: false,
        relay_credit_per_kb: 1,
        urace_credit_usd_rate: 1000,
        bootstrap_credit_per_connection: 5,
        bandwidth_profile: "auto".to_owned(),
        transfer_chunk_size: 0,
        bootstrap_peers: vec![],
        node_roles: vec![
            "bootstrap".to_owned(),
            "relay".to_owned(),
            "delivery".to_owned(),
            "block_sealer".to_owned(),
        ],
        default_feature_rules: HashMap::new(),
        peers: HashMap::new(),
        features: HashMap::new(),
        rules: HashMap::new(),
    }
}

/// Per-peer configuration entry.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PeerEntry {
    pub blocked: bool,
    #[serde(flatten)]
    pub extra: HashMap<String, serde_json::Value>,
}

/// Per-feature configuration entry.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FeatureEntry {
    #[serde(default)]
    pub dependencies: Vec<String>,
    #[serde(flatten)]
    pub extra: HashMap<String, serde_json::Value>,
}

/// The full exchange policy document.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExchangePolicy {
    pub schema: String,
    pub enabled: bool,
    pub network: bool,
    pub advertise: bool,
    pub auto_select: bool,
    pub auto_relay: bool,
    pub token_settlement: bool,
    pub auto_trust_first_contact: bool,
    pub relay_only: bool,
    pub feature_borrow_enabled: bool,
    pub max_transfers_per_day: u32,
    pub max_transfers_per_peer_per_day: u32,
    pub max_bytes_per_day: u64,
    pub max_rpc_per_day: u32,
    pub max_rpc_per_peer_per_day: u32,
    pub min_peer_version: u32,
    pub compress_wire: bool,
    pub relay_credit_per_kb: u32,
    pub urace_credit_usd_rate: u64,
    pub bootstrap_credit_per_connection: u32,
    pub bandwidth_profile: String,
    pub transfer_chunk_size: u64,
    pub bootstrap_peers: Vec<String>,
    pub node_roles: Vec<String>,
    #[serde(default)]
    pub default_feature_rules: HashMap<String, serde_json::Value>,
    #[serde(default)]
    pub peers: HashMap<String, PeerEntry>,
    #[serde(default)]
    pub features: HashMap<String, FeatureEntry>,
    /// Keyed by `"<peer_id>:<direction>:<feature_id>"`.
    #[serde(default)]
    pub rules: HashMap<String, bool>,
}

#[derive(Debug, Error)]
pub enum PolicyStoreError {
    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),
    #[error("JSON error: {0}")]
    Json(#[from] serde_json::Error),
    #[error("daily transfer budget exhausted")]
    BudgetExhausted,
    #[error("per-peer transfer allowance exhausted")]
    PeerBudgetExhausted,
}

/// Read-only view of `policy.json` for one exchange root.
///
/// Write operations (configure, peer, block, feature, rule) live in the Exchange
/// layer which owns the file lock and audit-chain writes.
pub struct ExchangePolicyStore {
    root: PathBuf,
}

impl ExchangePolicyStore {
    pub fn new(root: impl AsRef<Path>) -> Self {
        ExchangePolicyStore {
            root: root.as_ref().to_path_buf(),
        }
    }

    /// Return the current policy (fresh read on every call).
    pub fn load(&self) -> Result<ExchangePolicy, PolicyStoreError> {
        let p = self.root.join("policy.json");
        if !p.exists() {
            return Ok(default_policy());
        }
        let text = std::fs::read_to_string(&p)?;
        Ok(serde_json::from_str(&text)?)
    }

    /// Return `true` iff `direction` ("send"|"receive") is allowed for `peer`/`feature`.
    ///
    /// §62z: policy decisions that gate qualifying (spend/transfer/goal-creation) actions
    /// must route through `authority::resolve` before being acted upon.  This method is a
    /// pure structural check; callers must still pass through the authority gate.
    pub fn permitted(
        &self,
        policy: &ExchangePolicy,
        peer: &str,
        feature: &str,
        direction: &str,
        seen: &mut std::collections::HashSet<String>,
    ) -> bool {
        if !policy.enabled {
            return false;
        }
        let peer_entry = match policy.peers.get(peer) {
            Some(e) => e,
            None => return false,
        };
        if peer_entry.blocked {
            return false;
        }
        let rule_key = format!("{peer}:{direction}:{feature}");
        if !policy.rules.get(&rule_key).copied().unwrap_or(false) {
            return false;
        }
        let feature_entry = match policy.features.get(feature) {
            Some(e) => e,
            None => return false,
        };
        if seen.contains(feature) {
            return false;
        }
        seen.insert(feature.to_owned());
        feature_entry
            .dependencies
            .iter()
            .all(|dep| self.permitted(policy, peer, dep, direction, seen))
    }

    /// Raise `PolicyStoreError::BudgetExhausted` if the daily transfer budget is used up.
    pub fn check_budget(
        &self,
        peer: &str,
        size: u64,
        audit_rows: &[serde_json::Value],
        policy: &ExchangePolicy,
    ) -> Result<(), PolicyStoreError> {
        use std::time::{SystemTime, UNIX_EPOCH};
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs_f64();
        let window = now - 86_400.0;

        let relevant: Vec<&serde_json::Value> = audit_rows
            .iter()
            .filter(|r| {
                r.get("at_unix")
                    .and_then(|v| v.as_f64())
                    .map_or(false, |t| t > window)
                    && matches!(
                        r.get("kind").and_then(|v| v.as_str()),
                        Some("SEND_RESERVED") | Some("RECEIVE_RESERVED")
                    )
            })
            .collect();

        if relevant.len() as u32 >= policy.max_transfers_per_day {
            return Err(PolicyStoreError::BudgetExhausted);
        }
        let total_bytes: u64 = relevant
            .iter()
            .filter_map(|r| r.get("bytes").and_then(|v| v.as_u64()))
            .sum::<u64>()
            + size;
        if total_bytes > policy.max_bytes_per_day {
            return Err(PolicyStoreError::BudgetExhausted);
        }
        let peer_count = relevant
            .iter()
            .filter(|r| r.get("peer").and_then(|v| v.as_str()) == Some(peer))
            .count();
        if peer_count as u32 >= policy.max_transfers_per_peer_per_day {
            return Err(PolicyStoreError::PeerBudgetExhausted);
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write;
    use tempfile::TempDir;

    fn write_policy(dir: &TempDir, policy: &ExchangePolicy) {
        let p = dir.path().join("policy.json");
        let mut f = std::fs::File::create(p).unwrap();
        write!(f, "{}", serde_json::to_string(policy).unwrap()).unwrap();
    }

    fn make_policy(enabled: bool) -> ExchangePolicy {
        let mut p = default_policy();
        p.enabled = enabled;
        p
    }

    #[test]
    fn load_missing_returns_default() {
        let dir = TempDir::new().unwrap();
        let store = ExchangePolicyStore::new(dir.path());
        let p = store.load().unwrap();
        assert!(p.enabled);
        assert_eq!(p.max_transfers_per_day, 20);
    }

    #[test]
    fn load_existing_policy() {
        let dir = TempDir::new().unwrap();
        let mut policy = make_policy(false);
        policy.max_transfers_per_day = 5;
        write_policy(&dir, &policy);
        let store = ExchangePolicyStore::new(dir.path());
        let p = store.load().unwrap();
        assert!(!p.enabled);
        assert_eq!(p.max_transfers_per_day, 5);
    }

    #[test]
    fn permitted_disabled_policy_returns_false() {
        let dir = TempDir::new().unwrap();
        let store = ExchangePolicyStore::new(dir.path());
        let policy = make_policy(false);
        let mut seen = std::collections::HashSet::new();
        assert!(!store.permitted(&policy, "peer-1", "feat-1", "send", &mut seen));
    }

    #[test]
    fn permitted_unknown_peer_returns_false() {
        let dir = TempDir::new().unwrap();
        let store = ExchangePolicyStore::new(dir.path());
        let policy = make_policy(true);
        let mut seen = std::collections::HashSet::new();
        assert!(!store.permitted(&policy, "unknown", "feat-1", "send", &mut seen));
    }

    #[test]
    fn budget_exhausted_on_too_many_transfers() {
        let dir = TempDir::new().unwrap();
        let store = ExchangePolicyStore::new(dir.path());
        let mut policy = make_policy(true);
        policy.max_transfers_per_day = 1;
        use std::time::{SystemTime, UNIX_EPOCH};
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_secs_f64();
        let rows = vec![
            serde_json::json!({"kind": "SEND_RESERVED", "at_unix": now, "bytes": 100, "peer": "p1"}),
        ];
        let err = store.check_budget("p1", 100, &rows, &policy).unwrap_err();
        assert!(matches!(err, PolicyStoreError::BudgetExhausted));
    }
}
