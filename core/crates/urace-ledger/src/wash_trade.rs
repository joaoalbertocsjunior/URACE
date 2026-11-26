//! M20 — Wash-trade / circular payment detection.
//!
//! Detects A→B→A transfer cycles within a sliding time window, flagging
//! pairs where both directions of a payment occurred inside the window.

use serde::{Deserialize, Serialize};

/// Sliding-window detection period (1 hour).
pub const WASH_TRADE_WINDOW_SECS: u64 = 3_600;

/// A single peer-to-peer transfer record.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TransferRecord {
    pub from_peer: String,
    pub to_peer: String,
    pub amount_ucr: i64,
    pub at_unix: u64,
}

/// A detected wash-trade pair — both A→B and B→A occurred within the window.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WashTradePair {
    pub peer_a: String,
    pub peer_b: String,
    pub detected_at_unix: u64,
}

/// Detect circular A→B→A transfers within `WASH_TRADE_WINDOW_SECS`.
///
/// Uses `now_unix` as the reference point; records older than
/// `now_unix - WASH_TRADE_WINDOW_SECS` are ignored.
///
/// Returns one `WashTradePair` per unique unordered pair `{A, B}` where both
/// directions were observed within the window.  The returned list is sorted
/// by `peer_a` for deterministic output.
pub fn detect_wash_trades(records: &[TransferRecord], now_unix: u64) -> Vec<WashTradePair> {
    use std::collections::{HashMap, HashSet};

    let cutoff = now_unix.saturating_sub(WASH_TRADE_WINDOW_SECS);

    // Collect the set of directed (from, to) pairs that fall inside the window.
    let mut in_window: HashSet<(String, String)> = HashSet::new();
    for r in records {
        if r.at_unix >= cutoff && r.at_unix <= now_unix {
            in_window.insert((r.from_peer.clone(), r.to_peer.clone()));
        }
    }

    // For every directed pair, check whether the reverse also exists.
    // Track detected unordered pairs via a canonical key to avoid duplicates.
    let mut seen: HashMap<(String, String), bool> = HashMap::new();
    let mut result: Vec<WashTradePair> = Vec::new();

    for (from, to) in &in_window {
        if in_window.contains(&(to.clone(), from.clone())) {
            // Canonical key: smaller peer_id first.
            let key = if from <= to {
                (from.clone(), to.clone())
            } else {
                (to.clone(), from.clone())
            };
            if !seen.contains_key(&key) {
                seen.insert(key.clone(), true);
                result.push(WashTradePair {
                    peer_a: key.0,
                    peer_b: key.1,
                    detected_at_unix: now_unix,
                });
            }
        }
    }

    result.sort_by(|a, b| a.peer_a.cmp(&b.peer_a).then(a.peer_b.cmp(&b.peer_b)));
    result
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn circular_transfer_within_window_is_flagged() {
        let now = 10_000u64;
        let records = vec![
            TransferRecord { from_peer: "A".into(), to_peer: "B".into(), amount_ucr: 100, at_unix: 9_000 },
            TransferRecord { from_peer: "B".into(), to_peer: "A".into(), amount_ucr: 95,  at_unix: 9_500 },
        ];
        let pairs = detect_wash_trades(&records, now);
        assert_eq!(pairs.len(), 1, "one wash-trade pair expected");
        let p = &pairs[0];
        assert_eq!(p.peer_a, "A");
        assert_eq!(p.peer_b, "B");
    }

    #[test]
    fn one_way_transfer_is_not_flagged() {
        let now = 10_000u64;
        let records = vec![
            TransferRecord { from_peer: "A".into(), to_peer: "B".into(), amount_ucr: 100, at_unix: 9_000 },
        ];
        let pairs = detect_wash_trades(&records, now);
        assert!(pairs.is_empty(), "one-way transfer must not trigger wash-trade detection");
    }

    #[test]
    fn transfers_outside_window_not_flagged() {
        let now = 10_000u64;
        // Both legs exist but A→B is outside the 1-hour window.
        let records = vec![
            TransferRecord { from_peer: "A".into(), to_peer: "B".into(), amount_ucr: 100, at_unix: 1_000 }, // older than cutoff
            TransferRecord { from_peer: "B".into(), to_peer: "A".into(), amount_ucr: 95,  at_unix: 9_500 },
        ];
        let pairs = detect_wash_trades(&records, now);
        assert!(pairs.is_empty(), "stale first leg must not form a wash-trade cycle");
    }

    #[test]
    fn multiple_independent_pairs_detected_separately() {
        let now = 10_000u64;
        let records = vec![
            TransferRecord { from_peer: "A".into(), to_peer: "B".into(), amount_ucr: 100, at_unix: 9_000 },
            TransferRecord { from_peer: "B".into(), to_peer: "A".into(), amount_ucr: 95,  at_unix: 9_200 },
            TransferRecord { from_peer: "C".into(), to_peer: "D".into(), amount_ucr: 50,  at_unix: 9_100 },
            TransferRecord { from_peer: "D".into(), to_peer: "C".into(), amount_ucr: 48,  at_unix: 9_300 },
            TransferRecord { from_peer: "E".into(), to_peer: "F".into(), amount_ucr: 10,  at_unix: 9_500 },
            // E→F has no return leg
        ];
        let pairs = detect_wash_trades(&records, now);
        assert_eq!(pairs.len(), 2, "two distinct wash-trade pairs expected");
    }
}
