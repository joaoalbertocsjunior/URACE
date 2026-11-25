//! Scope priority scoring and weighted allocation.
//!
//! Ported from `scope_priority.py`: dynamic attention priorities computed from
//! backlog size, urgency, unresolved debt markers, and accepted-change recency.

use dashmap::DashMap;
use serde::{Deserialize, Serialize};
use std::sync::Arc;

/// Computed priority record for one scope.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ScopeScore {
    /// Scope name.
    pub name: String,
    /// Human-readable label.
    pub label: String,
    /// Weight after step-limiting against the previous revision.
    pub raw_weight: f64,
    /// Unclamped target weight before step-limiting.
    pub target_weight: f64,
    /// Previous raw weight (None on first revision).
    pub previous_weight: Option<f64>,
    /// True if the step limit was binding this revision.
    pub change_limited: bool,
    pub base_weight: f64,
    pub min_weight: f64,
    pub max_weight: f64,
    /// Active objectives related to this scope.
    pub backlog: usize,
    /// Unresolved TODO/FIXME markers in scope artifacts.
    pub unresolved_markers: usize,
    /// Days since last accepted change, capped at 30.
    pub days_since_accepted_change: f64,
    pub maximum_backlog_urgency: f64,
    pub maximum_backlog_risk: f64,
    pub recent_regressed_metrics: usize,
    /// Normalized weight (raw / total_raw).
    pub normalized_weight: f64,
    /// Multiplier for ranking adjustment: clipped to [0.75, 1.25].
    pub ranking_multiplier: f64,
}

impl ScopeScore {
    /// Create a new ScopeScore from raw inputs.
    #[allow(clippy::too_many_arguments)]
    pub fn new(
        name: impl Into<String>,
        label: impl Into<String>,
        base_weight: f64,
        min_weight: f64,
        max_weight: f64,
        backlog: usize,
        unresolved_markers: usize,
        days_since_accepted_change: f64,
        maximum_backlog_urgency: f64,
        maximum_backlog_risk: f64,
        recent_regressed_metrics: usize,
        previous_weight: Option<f64>,
        max_step: f64,
    ) -> Self {
        let age = days_since_accepted_change.min(30.0);
        let target = base_weight
            + (backlog as f64 * 0.2).min(0.8)
            + (unresolved_markers as f64 * 0.1).min(0.4)
            + (age / 60.0).min(0.5)
            + (maximum_backlog_urgency * 0.3).min(0.3)
            + (maximum_backlog_risk * 0.2).min(0.3)
            + (recent_regressed_metrics as f64 * 0.1).min(0.4);
        let target = target.min(max_weight).max(min_weight);
        let (raw, change_limited) = match previous_weight {
            None => (target, false),
            Some(prior) => {
                let clamped = target.min(prior + max_step).max(prior - max_step);
                (clamped, (clamped - target).abs() > 1e-9)
            }
        };
        ScopeScore {
            name: name.into(),
            label: label.into(),
            raw_weight: round4(raw),
            target_weight: round4(target),
            previous_weight,
            change_limited,
            base_weight,
            min_weight,
            max_weight,
            backlog,
            unresolved_markers,
            days_since_accepted_change: round2(age),
            maximum_backlog_urgency,
            maximum_backlog_risk,
            recent_regressed_metrics,
            normalized_weight: 0.0, // filled by PriorityQueue::normalize()
            ranking_multiplier: 1.0,
        }
    }

    /// Ranking adjustment score (mirrors `ranking_adjustment` in Python).
    pub fn ranking_adjustment(&self) -> f64 {
        10.0 * (self.ranking_multiplier - 1.0)
    }
}

fn round4(v: f64) -> f64 {
    (v * 10_000.0).round() / 10_000.0
}
fn round2(v: f64) -> f64 {
    (v * 100.0).round() / 100.0
}

/// DashMap-backed priority queue of scope scores.
///
/// Thread-safe; read-heavy workload is well suited to DashMap.
#[derive(Clone)]
pub struct PriorityQueue {
    scores: Arc<DashMap<String, ScopeScore>>,
}

impl Default for PriorityQueue {
    fn default() -> Self {
        Self::new()
    }
}

impl PriorityQueue {
    pub fn new() -> Self {
        PriorityQueue {
            scores: Arc::new(DashMap::new()),
        }
    }

    /// Insert or replace a scope score, then re-normalize all weights.
    pub fn upsert(&self, score: ScopeScore) {
        let name = score.name.clone();
        self.scores.insert(name, score);
        self.normalize();
    }

    /// Re-compute normalized_weight and ranking_multiplier for all entries.
    pub fn normalize(&self) {
        let total: f64 = self.scores.iter().map(|e| e.raw_weight).sum();
        let total = if total == 0.0 { 1.0 } else { total };
        let count = self.scores.len().max(1);
        let mean = total / count as f64;
        for mut entry in self.scores.iter_mut() {
            entry.normalized_weight = round4(entry.raw_weight / total);
            entry.ranking_multiplier = round4((entry.raw_weight / mean).clamp(0.75, 1.25));
        }
    }

    /// Return the score for a named scope, if present.
    pub fn get(&self, name: &str) -> Option<ScopeScore> {
        self.scores.get(name).map(|e| e.clone())
    }

    /// Return all scores, sorted by raw_weight descending.
    pub fn ranked(&self) -> Vec<ScopeScore> {
        let mut v: Vec<ScopeScore> = self.scores.iter().map(|e| e.clone()).collect();
        v.sort_by(|a, b| {
            b.raw_weight
                .partial_cmp(&a.raw_weight)
                .unwrap_or(std::cmp::Ordering::Equal)
        });
        v
    }

    /// Largest-remainder slot allocation (mirrors `allocate` in Python).
    pub fn allocate(
        &self,
        names: &[&str],
        slots: usize,
    ) -> std::collections::HashMap<String, usize> {
        let mut allocation: std::collections::HashMap<String, usize> = names
            .iter()
            .map(|n| (n.to_string(), if slots >= names.len() { 1 } else { 0 }))
            .collect();
        let mut remaining = slots as isize - allocation.values().sum::<usize>() as isize;
        let total: f64 = names
            .iter()
            .filter_map(|n| self.scores.get(*n).map(|e| e.raw_weight))
            .sum::<f64>()
            .max(1.0);
        let shares: std::collections::HashMap<String, f64> = names
            .iter()
            .map(|n| {
                let w = self.scores.get(*n).map(|e| e.raw_weight).unwrap_or(0.0);
                (n.to_string(), remaining as f64 * w / total)
            })
            .collect();
        for name in names {
            let whole = shares[*name].floor() as isize;
            *allocation.get_mut(*name).unwrap() = (allocation[*name] as isize + whole) as usize;
            remaining -= whole;
        }
        // Distribute remainder by fractional descending.
        let mut sorted_names: Vec<&str> = names.to_vec();
        sorted_names.sort_by(|a, b| {
            let fa = shares[*a].fract();
            let fb = shares[*b].fract();
            fb.partial_cmp(&fa).unwrap_or(std::cmp::Ordering::Equal)
        });
        for name in sorted_names.iter().take(remaining.max(0) as usize) {
            *allocation.get_mut(*name).unwrap() += 1;
        }
        allocation
    }

    pub fn len(&self) -> usize {
        self.scores.len()
    }

    pub fn is_empty(&self) -> bool {
        self.scores.is_empty()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_score(name: &str, base: f64) -> ScopeScore {
        ScopeScore::new(
            name, name, base, 0.5, 3.0, 0, 0, 0.0, 0.0, 0.0, 0, None, 0.25,
        )
    }

    #[test]
    fn upsert_and_normalize() {
        let pq = PriorityQueue::new();
        pq.upsert(make_score("alpha", 1.0));
        pq.upsert(make_score("beta", 2.0));
        let alpha = pq.get("alpha").unwrap();
        let beta = pq.get("beta").unwrap();
        // Weights should sum to 1.0
        let total = alpha.normalized_weight + beta.normalized_weight;
        assert!((total - 1.0).abs() < 1e-6);
        assert!(beta.normalized_weight > alpha.normalized_weight);
    }

    #[test]
    fn step_limiting() {
        let score = ScopeScore::new(
            "s",
            "s",
            1.0,
            0.5,
            3.0,
            10,
            5,
            20.0,
            0.8,
            0.8,
            3,
            Some(1.0),
            0.25,
        );
        // Target would be high, but limited to prior + 0.25
        assert!(score.raw_weight <= 1.0 + 0.25 + 1e-6);
        assert!(score.change_limited);
    }

    #[test]
    fn allocate_slots() {
        let pq = PriorityQueue::new();
        pq.upsert(make_score("a", 1.0));
        pq.upsert(make_score("b", 2.0));
        let alloc = pq.allocate(&["a", "b"], 5);
        let total: usize = alloc.values().sum();
        assert_eq!(total, 5);
    }
}
