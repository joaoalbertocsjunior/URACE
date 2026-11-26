//! M09 — Approval graph monitoring.
//!
//! Tracks the peer approval graph to detect reputation laundering via
//! concentration, dense clusters, and circular approval chains.

use std::collections::{HashMap, HashSet, VecDeque};

/// Approval graph — tracks who approved whom.
pub struct ApprovalGraph {
    /// approver_id → set of approved peer_ids
    edges: HashMap<String, HashSet<String>>,
    /// (approver, approvee) → approval count
    edge_counts: HashMap<(String, String), u64>,
}

impl ApprovalGraph {
    /// Create an empty approval graph.
    pub fn new() -> Self {
        ApprovalGraph {
            edges: HashMap::new(),
            edge_counts: HashMap::new(),
        }
    }

    /// Record that `approver` approved `approvee`.
    pub fn record_approval(&mut self, approver: &str, approvee: &str) {
        self.edges
            .entry(approver.to_string())
            .or_default()
            .insert(approvee.to_string());
        *self
            .edge_counts
            .entry((approver.to_string(), approvee.to_string()))
            .or_insert(0) += 1;
    }

    /// Returns `true` if any single peer has approved more than `threshold`
    /// fraction of all known peers.
    pub fn has_concentration_above(&self, threshold: f64) -> bool {
        let total = self.peer_count();
        if total == 0 {
            return false;
        }
        self.edges.values().any(|approved| {
            let fraction = approved.len() as f64 / total as f64;
            fraction > threshold
        })
    }

    /// BFS cluster detection: returns groups of peers with mutual approval
    /// density above `density_threshold`.
    ///
    /// Two peers are considered "connected" for clustering if they have
    /// approved each other (bidirectional edge). Dense clusters are built by
    /// collecting connected components of this symmetric sub-graph where the
    /// cluster's internal edge density exceeds `density_threshold`.
    pub fn dense_clusters(&self, density_threshold: f64) -> Vec<Vec<String>> {
        // Build symmetric adjacency from mutual approvals.
        let mut sym: HashMap<&str, HashSet<&str>> = HashMap::new();
        for (approver, approved_set) in &self.edges {
            for approvee in approved_set {
                // Edge is symmetric only if the reverse also exists.
                if self
                    .edges
                    .get(approvee)
                    .map_or(false, |s| s.contains(approver.as_str()))
                {
                    sym.entry(approver.as_str()).or_default().insert(approvee.as_str());
                    sym.entry(approvee.as_str()).or_default().insert(approver.as_str());
                }
            }
        }

        let all_peers: Vec<&str> = self.all_peers().collect();
        let mut visited: HashSet<&str> = HashSet::new();
        let mut clusters: Vec<Vec<String>> = Vec::new();

        for &peer in &all_peers {
            if visited.contains(peer) {
                continue;
            }
            // BFS to collect component.
            let mut component: Vec<&str> = Vec::new();
            let mut queue: VecDeque<&str> = VecDeque::new();
            queue.push_back(peer);
            visited.insert(peer);
            while let Some(current) = queue.pop_front() {
                component.push(current);
                if let Some(neighbors) = sym.get(current) {
                    for &nb in neighbors {
                        if !visited.contains(nb) {
                            visited.insert(nb);
                            queue.push_back(nb);
                        }
                    }
                }
            }
            if component.len() < 2 {
                continue;
            }
            // Compute density: edges / max_possible_edges
            let n = component.len();
            let max_edges = n * (n - 1); // directed; each pair has 2 possible edges
            let actual_edges: usize = component
                .iter()
                .map(|&p| {
                    sym.get(p)
                        .map_or(0, |nb| nb.iter().filter(|&&nb2| component.contains(&nb2)).count())
                })
                .sum();
            let density = if max_edges == 0 {
                0.0
            } else {
                actual_edges as f64 / max_edges as f64
            };
            if density > density_threshold {
                clusters.push(component.into_iter().map(|s| s.to_string()).collect());
            }
        }

        clusters
    }

    /// Detect circular approval chains of length <= `max_cycle_len` using DFS.
    pub fn has_cycle(&self, max_cycle_len: usize) -> bool {
        let all: Vec<&str> = self.all_peers().collect();
        for start in &all {
            if self.dfs_cycle(start, start, 0, max_cycle_len, &mut Vec::new()) {
                return true;
            }
        }
        false
    }

    fn dfs_cycle<'a>(
        &'a self,
        current: &'a str,
        target: &'a str,
        depth: usize,
        max_depth: usize,
        path: &mut Vec<&'a str>,
    ) -> bool {
        if depth > 0 && current == target {
            return true;
        }
        if depth >= max_depth {
            return false;
        }
        if path.contains(&current) {
            return false;
        }
        path.push(current);
        if let Some(neighbors) = self.edges.get(current) {
            for nb in neighbors {
                if self.dfs_cycle(nb.as_str(), target, depth + 1, max_depth, path) {
                    path.pop();
                    return true;
                }
            }
        }
        path.pop();
        false
    }

    /// Returns the number of unique peers (approvers + approvees).
    pub fn peer_count(&self) -> usize {
        self.all_peers().count()
    }

    /// Total number of approval events recorded.
    pub fn edge_count(&self) -> u64 {
        self.edge_counts.values().sum()
    }

    fn all_peers(&self) -> impl Iterator<Item = &str> {
        let mut peers: HashSet<&str> = HashSet::new();
        for (approver, approved_set) in &self.edges {
            peers.insert(approver.as_str());
            for approvee in approved_set {
                peers.insert(approvee.as_str());
            }
        }
        // Collect into a Vec so we can return an iterator without lifetime issues.
        peers.into_iter()
    }
}

impl Default for ApprovalGraph {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn single_approver_concentration() {
        let mut g = ApprovalGraph::new();
        // 10 total peers; "big_approver" approves 9 of them → 90%
        for i in 0..9u32 {
            g.record_approval("big_approver", &format!("peer-{i}"));
        }
        // Add one more peer not approved by big_approver to make peer_count 10.
        g.record_approval("peer-0", "peer-extra");

        assert!(
            g.has_concentration_above(0.5),
            "big_approver approves >50% of peers, should trigger"
        );
    }

    #[test]
    fn cycle_detection() {
        let mut g = ApprovalGraph::new();
        g.record_approval("A", "B");
        g.record_approval("B", "C");
        g.record_approval("C", "A");
        assert!(g.has_cycle(3), "A→B→C→A must be detected as a cycle");
    }

    #[test]
    fn no_cycle() {
        let mut g = ApprovalGraph::new();
        g.record_approval("A", "B");
        g.record_approval("B", "C");
        assert!(!g.has_cycle(3), "A→B→C has no cycle");
    }
}
