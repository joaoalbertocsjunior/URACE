//! P2P work matching: tasks, bids, demand tracking, and winner selection.
//!
//! INVARIANT (from CLAUDE.md / p2p_matching.py):
//! Executors MUST NOT inflate their own match_score or TPS weight by
//! self-reporting. `DemandCounter` entries are local-only — never accept
//! from remote peers. This is enforced by NOT deriving Serialize/Deserialize
//! on `DemandCounter`.

use parking_lot::Mutex;
use std::collections::HashMap;

pub use urace_work_types::{WorkBid, WorkTask};

// ── Scoring ──────────────────────────────────────────────────────────────────

/// Compute a match score in [0.0, 1.0] for a bid against a task.
///
/// Score components:
/// - Capability overlap: fraction of required capabilities the bid satisfies.
/// - Budget fit: 1.0 if bid ≤ budget, linearly penalised above budget.
///
/// The returned score is intentionally simple and lexical. It is a heuristic
/// routing signal, not a quality probability or cost estimate.
pub fn match_score(task: &WorkTask, bid: &WorkBid) -> f64 {
    let cap_score = if task.required_capabilities.is_empty() {
        1.0
    } else {
        let matched = task
            .required_capabilities
            .iter()
            .filter(|req| bid.capabilities.contains(req))
            .count();
        matched as f64 / task.required_capabilities.len() as f64
    };

    let budget_score = if task.budget_ucr <= 0 || bid.bid_price_ucr <= task.budget_ucr {
        1.0
    } else {
        // Penalise overbids linearly — a bid at 2× budget scores 0.
        let ratio = bid.bid_price_ucr as f64 / task.budget_ucr as f64;
        (2.0 - ratio).max(0.0)
    };

    // Equal weight on capability match and budget fit.
    (cap_score + budget_score) / 2.0
}

// ── DemandCounter ────────────────────────────────────────────────────────────

/// Local-only demand tracking for tasks.
///
/// SECURITY INVARIANT: `DemandCounter` deliberately does NOT implement
/// `Serialize` or `Deserialize`. Demand signals are process-local only —
/// accepting remote demand signals would allow executors to inflate their
/// own match weight (Sybil / self-reporting attack). Do not add
/// `#[derive(Serialize, Deserialize)]` here.
pub struct DemandCounter {
    counts: Mutex<HashMap<String, u64>>,
}

impl DemandCounter {
    pub fn new() -> Self {
        DemandCounter {
            counts: Mutex::new(HashMap::new()),
        }
    }

    /// Record a local demand signal for `task_id`.
    pub fn record_demand(&self, task_id: &str) {
        let mut map = self.counts.lock();
        *map.entry(task_id.to_owned()).or_insert(0) += 1;
    }

    /// Return a normalised demand weight in [0.0, 1.0] for `task_id`.
    ///
    /// Returns 0.0 when the task has never been demanded locally.
    /// Uses log1p to compress very high demand counts.
    pub fn demand_weight(&self, task_id: &str) -> f64 {
        let map = self.counts.lock();
        let count = match map.get(task_id) {
            Some(&c) => c,
            None => return 0.0,
        };
        let max_count = map.values().copied().max().unwrap_or(1);
        if max_count == 0 {
            return 0.0;
        }
        // log1p-normalise so very hot tasks don't completely dominate.
        (count as f64 + 1.0).ln() / (max_count as f64 + 1.0).ln()
    }
}

impl Default for DemandCounter {
    fn default() -> Self {
        Self::new()
    }
}

// ── Winner selection ─────────────────────────────────────────────────────────

/// Select the best bid for `task` from `bids`, incorporating local `demand`.
///
/// Scores are blended: 70% match_score + 30% demand_weight.
/// Returns `None` when `bids` is empty.
pub fn select_best_bid<'a>(
    task: &WorkTask,
    bids: &'a [WorkBid],
    demand: &DemandCounter,
) -> Option<&'a WorkBid> {
    bids.iter().max_by(|a, b| {
        let score_a = blended_score(task, a, demand);
        let score_b = blended_score(task, b, demand);
        score_a
            .partial_cmp(&score_b)
            .unwrap_or(std::cmp::Ordering::Equal)
    })
}

fn blended_score(task: &WorkTask, bid: &WorkBid, demand: &DemandCounter) -> f64 {
    let ms = match_score(task, bid);
    let dw = demand.demand_weight(&task.task_id);
    0.7 * ms + 0.3 * dw
}

// ── Tests ────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    fn task(caps: &[&str], budget: i64) -> WorkTask {
        WorkTask {
            task_id: "t1".to_owned(),
            required_capabilities: caps.iter().map(|s| s.to_string()).collect(),
            budget_ucr: budget,
            posted_at: "2026-01-01T00:00:00Z".to_owned(),
            poster_peer_id: "poster".to_owned(),
        }
    }

    fn bid(id: &str, caps: &[&str], price: i64) -> WorkBid {
        WorkBid {
            bid_id: id.to_owned(),
            executor_peer_id: "exec".to_owned(),
            task_id: "t1".to_owned(),
            bid_price_ucr: price,
            capabilities: caps.iter().map(|s| s.to_string()).collect(),
            submitted_at: "2026-01-01T00:01:00Z".to_owned(),
        }
    }

    #[test]
    fn perfect_match_scores_1() {
        let t = task(&["rust", "p2p"], 1000);
        let b = bid("b1", &["rust", "p2p"], 500);
        let s = match_score(&t, &b);
        assert!((s - 1.0).abs() < 1e-9, "expected 1.0, got {s}");
    }

    #[test]
    fn no_capability_match_scores_low() {
        let t = task(&["rust", "p2p"], 1000);
        let b = bid("b2", &["python"], 500);
        let s = match_score(&t, &b);
        // cap_score=0, budget_score=1 → 0.5
        assert!((s - 0.5).abs() < 1e-9, "expected 0.5, got {s}");
    }

    #[test]
    fn overbid_penalised() {
        let t = task(&[], 1000);
        let b = bid("b3", &[], 2000); // exactly 2× budget → score 0
        let s = match_score(&t, &b);
        // cap_score=1 (no required caps), budget_score=0 → 0.5
        assert!((s - 0.5).abs() < 1e-9, "expected 0.5, got {s}");
    }

    #[test]
    fn demand_counter_local_only_no_serde() {
        // DemandCounter must NOT implement Serialize / Deserialize.
        // This is a compile-time invariant verified by the absence of derives.
        // We just test the runtime behaviour here.
        let dc = DemandCounter::new();
        dc.record_demand("t1");
        dc.record_demand("t1");
        dc.record_demand("t2");
        assert_eq!(dc.demand_weight("t1"), 1.0); // t1 is hottest
        assert!(dc.demand_weight("t2") < 1.0);
        assert_eq!(dc.demand_weight("unknown"), 0.0);
    }

    #[test]
    fn select_best_bid_returns_highest_score() {
        let t = task(&["rust"], 1000);
        let bids = vec![bid("low", &["python"], 500), bid("high", &["rust"], 800)];
        let dc = DemandCounter::new();
        let winner = select_best_bid(&t, &bids, &dc).unwrap();
        assert_eq!(winner.bid_id, "high");
    }

    #[test]
    fn select_best_bid_empty_returns_none() {
        let t = task(&["rust"], 1000);
        let dc = DemandCounter::new();
        assert!(select_best_bid(&t, &[], &dc).is_none());
    }
}
