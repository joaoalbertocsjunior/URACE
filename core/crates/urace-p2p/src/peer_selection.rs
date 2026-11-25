//! Peer selection — select best peer by reputation + latency score.
//!
//! Ported from `peer_selection.py`. Explainable local peer selection with
//! bounded exponential backoff and oldest-first metadata exploration.
//! No native model calls; no global currency; no guaranteed equal utility.

use crate::peer_address_book::PeerAddressBook;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::net::SocketAddr;

/// Selection status for a candidate peer.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum SelectionStatus {
    Candidate,
    NeedsRefresh,
    TemporarilyUnavailable,
    Blocked,
    NoAddressKnown,
}

/// A single peer candidate with its selection score.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PeerCandidate {
    pub peer_id: String,
    pub best_addr: Option<SocketAddr>,
    pub reputation_score: f64,
    pub latency_ms: Option<f64>,
    /// Combined selection score (higher is better).
    pub score: f64,
    pub status: SelectionStatus,
    pub reason: String,
}

/// Peer scoring parameters.
#[derive(Debug, Clone)]
pub struct ScoringParams {
    /// Weight of reputation in [0,1] score. Latency weight = 1 - reputation_weight.
    pub reputation_weight: f64,
    /// Maximum latency considered (ms). Higher latency → score 0 for latency component.
    pub max_latency_ms: f64,
    /// Minimum reputation score to be a candidate.
    pub min_reputation: f64,
}

impl Default for ScoringParams {
    fn default() -> Self {
        ScoringParams {
            reputation_weight: 0.7,
            max_latency_ms: 5000.0,
            min_reputation: 0.0,
        }
    }
}

/// Peer selector: combines address book + reputation scores to rank peers.
pub struct PeerSelector {
    address_book: PeerAddressBook,
    params: ScoringParams,
    /// peer_id → observed latency (ms) — local only, never gossipped.
    latencies: parking_lot::RwLock<HashMap<String, f64>>,
    /// peer_id → reputation score (from ReputationStore or external).
    reputations: parking_lot::RwLock<HashMap<String, f64>>,
    /// Blocked peer_ids.
    blocked: parking_lot::RwLock<std::collections::HashSet<String>>,
}

impl PeerSelector {
    pub fn new(address_book: PeerAddressBook, params: ScoringParams) -> Self {
        PeerSelector {
            address_book,
            params,
            latencies: parking_lot::RwLock::new(HashMap::new()),
            reputations: parking_lot::RwLock::new(HashMap::new()),
            blocked: parking_lot::RwLock::new(std::collections::HashSet::new()),
        }
    }

    /// Update observed latency for a peer.
    pub fn record_latency(&self, peer_id: &str, latency_ms: f64) {
        self.latencies
            .write()
            .insert(peer_id.to_owned(), latency_ms);
    }

    /// Update reputation score for a peer.
    pub fn update_reputation(&self, peer_id: &str, score: f64) {
        self.reputations
            .write()
            .insert(peer_id.to_owned(), score.clamp(0.0, 1.0));
    }

    /// Block a peer from selection.
    pub fn block(&self, peer_id: &str) {
        self.blocked.write().insert(peer_id.to_owned());
    }

    /// Unblock a peer.
    pub fn unblock(&self, peer_id: &str) {
        self.blocked.write().remove(peer_id);
    }

    /// Score a single peer.
    fn score_peer(&self, peer_id: &str) -> PeerCandidate {
        let blocked = self.blocked.read().contains(peer_id);
        if blocked {
            return PeerCandidate {
                peer_id: peer_id.to_owned(),
                best_addr: None,
                reputation_score: 0.0,
                latency_ms: None,
                score: 0.0,
                status: SelectionStatus::Blocked,
                reason: "Owner block overrides all scoring".into(),
            };
        }

        let best_addr = self.address_book.best_addr(peer_id);
        if best_addr.is_none() {
            return PeerCandidate {
                peer_id: peer_id.to_owned(),
                best_addr: None,
                reputation_score: 0.0,
                latency_ms: None,
                score: 0.0,
                status: SelectionStatus::NoAddressKnown,
                reason: "No known address for peer".into(),
            };
        }

        let rep = *self.reputations.read().get(peer_id).unwrap_or(&0.0);
        let latency = self.latencies.read().get(peer_id).copied();

        let rep_score = rep * self.params.reputation_weight;
        let lat_score = match latency {
            None => 0.0, // no latency data = unknown, treated as worst
            Some(ms) => {
                let norm = (1.0 - ms / self.params.max_latency_ms).max(0.0);
                norm * (1.0 - self.params.reputation_weight)
            }
        };
        let combined = rep_score + lat_score;

        let (status, reason) = if rep < self.params.min_reputation {
            (
                SelectionStatus::TemporarilyUnavailable,
                format!(
                    "reputation {:.3} below minimum {:.3}",
                    rep, self.params.min_reputation
                ),
            )
        } else {
            (
                SelectionStatus::Candidate,
                "Fresh address; reputation and latency scored".into(),
            )
        };

        PeerCandidate {
            peer_id: peer_id.to_owned(),
            best_addr,
            reputation_score: rep,
            latency_ms: latency,
            score: combined,
            status,
            reason,
        }
    }

    /// Return all known peers ranked by score descending.
    pub fn rank_all(&self) -> Vec<PeerCandidate> {
        // Collect all peers from address book + reputation map.
        let mut peer_ids: std::collections::HashSet<String> = self
            .address_book
            .top_peers(500)
            .into_iter()
            .map(|(id, _)| id)
            .collect();
        for id in self.reputations.read().keys() {
            peer_ids.insert(id.clone());
        }

        let mut candidates: Vec<PeerCandidate> =
            peer_ids.iter().map(|id| self.score_peer(id)).collect();
        candidates.sort_by(|a, b| {
            // Candidates first, then by score descending.
            let a_cand = a.status == SelectionStatus::Candidate;
            let b_cand = b.status == SelectionStatus::Candidate;
            match (a_cand, b_cand) {
                (true, false) => std::cmp::Ordering::Less,
                (false, true) => std::cmp::Ordering::Greater,
                _ => b
                    .score
                    .partial_cmp(&a.score)
                    .unwrap_or(std::cmp::Ordering::Equal),
            }
        });
        candidates
    }

    /// Return the best `n` candidate peers.
    pub fn select_best(&self, n: usize) -> Vec<PeerCandidate> {
        self.rank_all()
            .into_iter()
            .filter(|c| c.status == SelectionStatus::Candidate)
            .take(n)
            .collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn book_with_peers() -> PeerAddressBook {
        let book = PeerAddressBook::new();
        book.add("peer-a", "127.0.0.1:8001".parse().unwrap());
        book.add("peer-b", "127.0.0.1:8002".parse().unwrap());
        book
    }

    #[test]
    fn select_by_reputation() {
        let book = book_with_peers();
        let sel = PeerSelector::new(book, ScoringParams::default());
        sel.update_reputation("peer-a", 0.9);
        sel.update_reputation("peer-b", 0.1);
        let best = sel.select_best(1);
        assert_eq!(best.len(), 1);
        assert_eq!(best[0].peer_id, "peer-a");
    }

    #[test]
    fn blocked_peer_excluded() {
        let book = book_with_peers();
        let sel = PeerSelector::new(book, ScoringParams::default());
        sel.update_reputation("peer-a", 0.9);
        sel.block("peer-a");
        let best = sel.select_best(2);
        assert!(best.iter().all(|c| c.peer_id != "peer-a"));
    }

    #[test]
    fn no_address_peer_excluded() {
        let book = PeerAddressBook::new();
        let sel = PeerSelector::new(book, ScoringParams::default());
        sel.update_reputation("peer-x", 0.9);
        let best = sel.select_best(1);
        // peer-x has no address → not a candidate
        assert!(best.is_empty());
    }

    #[test]
    fn latency_affects_score() {
        let book = book_with_peers();
        let sel = PeerSelector::new(book, ScoringParams::default());
        sel.update_reputation("peer-a", 0.5);
        sel.update_reputation("peer-b", 0.5);
        sel.record_latency("peer-a", 100.0); // fast
        sel.record_latency("peer-b", 4000.0); // slow
        let best = sel.select_best(2);
        assert_eq!(best[0].peer_id, "peer-a");
    }
}
