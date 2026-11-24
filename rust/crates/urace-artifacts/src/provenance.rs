//! Provenance graph and staking.
//!
//! Ports `provenance_graph.py` (DAG + weight resolution) and `provenance_stake.py`
//! (append-only stake records). No ledger interaction — that remains in the Python
//! exchange layer. This crate models the data structures and graph traversal.

use std::collections::{HashMap, HashSet, VecDeque};

use serde::{Deserialize, Serialize};
use thiserror::Error;

// ── Errors ────────────────────────────────────────────────────────────────────

#[derive(Debug, Error)]
pub enum ProvenanceError {
    #[error("node {0} not found")]
    NodeNotFound(String),
    #[error("cycle detected involving node {0}")]
    CycleDetected(String),
    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),
    #[error("json error: {0}")]
    Json(#[from] serde_json::Error),
}

// ── Graph types ───────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ProvenanceNode {
    pub node_id: String,
    /// "artifact" | "peer" | "feature"
    pub kind: String,
    pub created_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ProvenanceEdge {
    pub from_id: String,
    pub to_id: String,
    /// "derived_from" | "stake" | "adopted"
    pub edge_kind: String,
}

// ── ProvenanceGraph ───────────────────────────────────────────────────────────

/// Directed provenance graph.
///
/// Nodes are identified by `node_id`. Edges are directed `from → to` (e.g.
/// `derived_from` means `from` was derived from `to`).
#[derive(Debug, Default)]
pub struct ProvenanceGraph {
    nodes: HashMap<String, ProvenanceNode>,
    // adjacency: from_id → list of (to_id, edge_kind)
    adjacency: HashMap<String, Vec<(String, String)>>,
    // reverse adjacency: to_id → list of from_id  (for ancestor traversal)
    reverse: HashMap<String, Vec<String>>,
}

impl ProvenanceGraph {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn add_node(&mut self, node: ProvenanceNode) {
        self.nodes.insert(node.node_id.clone(), node);
    }

    pub fn add_edge(&mut self, edge: ProvenanceEdge) {
        self.adjacency
            .entry(edge.from_id.clone())
            .or_default()
            .push((edge.to_id.clone(), edge.edge_kind.clone()));
        self.reverse
            .entry(edge.to_id.clone())
            .or_default()
            .push(edge.from_id.clone());
    }

    /// Return `node_id` values that are ancestors of `node_id` via BFS.
    ///
    /// "Ancestor" means reachable from `node_id` by following `from → to` edges
    /// (i.e. the nodes that `node_id` was derived from, recursively).
    pub fn ancestors(&self, node_id: &str) -> Vec<String> {
        let mut visited: HashSet<String> = HashSet::new();
        let mut queue: VecDeque<String> = VecDeque::new();
        // Start from the direct successors (the `to` side of edges from node_id).
        if let Some(succs) = self.adjacency.get(node_id) {
            for (to, _) in succs {
                if !visited.contains(to) {
                    visited.insert(to.clone());
                    queue.push_back(to.clone());
                }
            }
        }
        while let Some(current) = queue.pop_front() {
            if let Some(succs) = self.adjacency.get(&current) {
                for (to, _) in succs {
                    if !visited.contains(to) {
                        visited.insert(to.clone());
                        queue.push_back(to.clone());
                    }
                }
            }
        }
        visited.into_iter().collect()
    }

    /// Return `true` if the graph contains a cycle (DFS-based).
    pub fn is_cyclic(&self) -> bool {
        let mut colour: HashMap<&str, u8> = HashMap::new(); // 0=white,1=grey,2=black
        for node_id in self.nodes.keys() {
            if colour.get(node_id.as_str()).copied().unwrap_or(0) == 0
                && self.dfs_cycle(node_id.as_str(), &mut colour)
            {
                return true;
            }
        }
        false
    }

    fn dfs_cycle<'a>(&'a self, node: &'a str, colour: &mut HashMap<&'a str, u8>) -> bool {
        colour.insert(node, 1);
        if let Some(succs) = self.adjacency.get(node) {
            for (to, _) in succs {
                let c = colour.get(to.as_str()).copied().unwrap_or(0);
                if c == 1 {
                    return true; // back edge → cycle
                }
                if c == 0 && self.dfs_cycle(to.as_str(), colour) {
                    return true;
                }
            }
        }
        colour.insert(node, 2);
        false
    }

    /// Resolve provenance weights for a node.
    ///
    /// Returns `{peer_id: weight}` following the same algorithm as
    /// `provenance_graph.py::resolve_provenance_weights`.
    ///
    /// `composition_rows` mirrors the `FEATURE_COMPOSITION` / `EQUITY_GRANT`
    /// rows from the Python exchange audit chain.
    pub fn resolve_weights(
        &self,
        node_id: &str,
        composition_rows: &[ProvenanceCompositionRow],
    ) -> HashMap<String, f64> {
        self.resolve_weights_inner(node_id, composition_rows, &mut HashSet::new())
    }

    fn resolve_weights_inner(
        &self,
        node_id: &str,
        rows: &[ProvenanceCompositionRow],
        visited: &mut HashSet<String>,
    ) -> HashMap<String, f64> {
        if visited.contains(node_id) {
            return HashMap::new();
        }
        visited.insert(node_id.to_owned());

        let comp_rows: Vec<&ProvenanceCompositionRow> = rows
            .iter()
            .filter(|r| r.composite_node_id == node_id)
            .collect();

        if comp_rows.is_empty() {
            // No composition — full provenance is creator.
            let creator = rows
                .iter()
                .find(|r| r.kind == "EQUITY_GRANT" && r.node_id.as_deref() == Some(node_id))
                .and_then(|r| r.creator_peer_id.clone())
                .unwrap_or_default();
            if creator.is_empty() {
                return HashMap::new();
            }
            let mut m = HashMap::new();
            m.insert(creator, 1.0);
            return m;
        }

        // Merge component weights (take max per component across rows).
        let mut comp_weights: HashMap<String, f64> = HashMap::new();
        for cr in &comp_rows {
            for cid in &cr.component_ids {
                let w = cr.component_weights.get(cid).copied().unwrap_or(0.0);
                let entry = comp_weights.entry(cid.clone()).or_insert(0.0);
                if w > *entry {
                    *entry = w;
                }
            }
        }

        // If all weights are zero, distribute equally.
        if comp_weights.values().all(|&w| w == 0.0) {
            let n = comp_weights.len();
            if n > 0 {
                for w in comp_weights.values_mut() {
                    *w = 1.0 / n as f64;
                }
            }
        }

        // Normalize so total ≤ 1.0.
        let total_w: f64 = comp_weights.values().sum();
        if total_w > 1.0 {
            for w in comp_weights.values_mut() {
                *w /= total_w;
            }
        }

        // Recursively resolve each component.
        let mut result: HashMap<String, f64> = HashMap::new();
        for (cid, w) in &comp_weights {
            let sub = self.resolve_weights_inner(cid, rows, visited);
            for (peer, sw) in sub {
                *result.entry(peer).or_insert(0.0) += w * sw;
            }
        }

        // Composite creator keeps the novel portion.
        let novel_fraction = (1.0_f64 - comp_weights.values().sum::<f64>()).max(0.0);
        if novel_fraction > 0.001 {
            if let Some(creator) = rows
                .iter()
                .find(|r| r.kind == "EQUITY_GRANT" && r.node_id.as_deref() == Some(node_id))
                .and_then(|r| r.creator_peer_id.clone())
            {
                if !creator.is_empty() {
                    *result.entry(creator).or_insert(0.0) += novel_fraction;
                }
            }
        }

        // Normalize final.
        let total: f64 = result.values().sum();
        if total > 0.0 {
            for v in result.values_mut() {
                *v /= total;
            }
        }
        result
    }
}

/// Mirrors FEATURE_COMPOSITION / EQUITY_GRANT rows from the Python audit chain.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProvenanceCompositionRow {
    pub kind: String,
    /// Used when kind == "EQUITY_GRANT".
    pub node_id: Option<String>,
    /// Used when kind == "FEATURE_COMPOSITION".
    pub composite_node_id: String,
    pub component_ids: Vec<String>,
    pub component_weights: HashMap<String, f64>,
    pub creator_peer_id: Option<String>,
}

// ── Provenance Staking ────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProvenanceStake {
    pub staker_peer_id: String,
    pub target_id: String,
    /// Amount in UCR base units (1 UCR = 10^8 base units).
    pub amount_ucr: i64,
    pub staked_at: String,
}

/// Append-only stake store.
///
/// Persists to `provenance-stakes.jsonl` via the ledger's `atomic_append_jsonl`.
pub struct StakeStore {
    path: std::path::PathBuf,
}

impl StakeStore {
    pub fn new(root: &std::path::Path) -> Self {
        Self {
            path: root.join("provenance-stakes.jsonl"),
        }
    }

    /// Append a stake record (append-only — never mutated after write).
    pub fn add_stake(&self, stake: ProvenanceStake) -> Result<(), ProvenanceError> {
        let row = serde_json::to_value(&stake)?;
        urace_ledger::atomic_append_jsonl(&self.path, &row)
            .map_err(|e| ProvenanceError::Io(std::io::Error::other(e.to_string())))
    }

    /// Return all stakes for `target_id`.
    pub fn stakes_for(&self, target_id: &str) -> Vec<ProvenanceStake> {
        if !self.path.exists() {
            return vec![];
        }
        let Ok(text) = std::fs::read_to_string(&self.path) else { return vec![]; };
        text.lines()
            .filter_map(|line| serde_json::from_str::<ProvenanceStake>(line).ok())
            .filter(|s| s.target_id == target_id)
            .collect()
    }

    /// Return all stakes in the store.
    pub fn all_stakes(&self) -> Vec<ProvenanceStake> {
        if !self.path.exists() {
            return vec![];
        }
        let Ok(text) = std::fs::read_to_string(&self.path) else { return vec![]; };
        text.lines()
            .filter_map(|line| serde_json::from_str::<ProvenanceStake>(line).ok())
            .collect()
    }
}

// ── Tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    fn node(id: &str, kind: &str) -> ProvenanceNode {
        ProvenanceNode {
            node_id: id.to_owned(),
            kind: kind.to_owned(),
            created_at: "2024-01-01T00:00:00Z".to_owned(),
        }
    }

    fn edge(from: &str, to: &str, kind: &str) -> ProvenanceEdge {
        ProvenanceEdge {
            from_id: from.to_owned(),
            to_id: to.to_owned(),
            edge_kind: kind.to_owned(),
        }
    }

    #[test]
    fn ancestors_simple_chain() {
        let mut g = ProvenanceGraph::new();
        g.add_node(node("A", "artifact"));
        g.add_node(node("B", "artifact"));
        g.add_node(node("C", "artifact"));
        g.add_edge(edge("A", "B", "derived_from"));
        g.add_edge(edge("B", "C", "derived_from"));
        let ancestors = g.ancestors("A");
        assert!(ancestors.contains(&"B".to_owned()));
        assert!(ancestors.contains(&"C".to_owned()));
        assert!(!ancestors.contains(&"A".to_owned()));
    }

    #[test]
    fn not_cyclic_dag() {
        let mut g = ProvenanceGraph::new();
        g.add_node(node("A", "artifact"));
        g.add_node(node("B", "artifact"));
        g.add_edge(edge("A", "B", "derived_from"));
        assert!(!g.is_cyclic());
    }

    #[test]
    fn cyclic_detection() {
        let mut g = ProvenanceGraph::new();
        g.add_node(node("A", "artifact"));
        g.add_node(node("B", "artifact"));
        g.add_edge(edge("A", "B", "derived_from"));
        g.add_edge(edge("B", "A", "derived_from")); // creates cycle
        assert!(g.is_cyclic());
    }

    #[test]
    fn ancestors_no_edges() {
        let mut g = ProvenanceGraph::new();
        g.add_node(node("X", "peer"));
        assert!(g.ancestors("X").is_empty());
    }

    #[test]
    fn stake_store_append_and_query() {
        let dir = tempfile::tempdir().unwrap();
        let store = StakeStore::new(dir.path());
        store.add_stake(ProvenanceStake {
            staker_peer_id: "peer-1".into(),
            target_id: "feat-A".into(),
            amount_ucr: 300_000_000,
            staked_at: "2024-01-01T00:00:00Z".into(),
        }).unwrap();
        store.add_stake(ProvenanceStake {
            staker_peer_id: "peer-2".into(),
            target_id: "feat-B".into(),
            amount_ucr: 100_000_000,
            staked_at: "2024-01-01T00:00:00Z".into(),
        }).unwrap();
        let stakes = store.stakes_for("feat-A");
        assert_eq!(stakes.len(), 1);
        assert_eq!(stakes[0].staker_peer_id, "peer-1");
        let all = store.all_stakes();
        assert_eq!(all.len(), 2);
    }

    #[test]
    fn resolve_weights_no_composition() {
        let mut g = ProvenanceGraph::new();
        g.add_node(node("feat-X", "feature"));
        let rows = vec![ProvenanceCompositionRow {
            kind: "EQUITY_GRANT".into(),
            node_id: Some("feat-X".into()),
            composite_node_id: String::new(),
            component_ids: vec![],
            component_weights: HashMap::new(),
            creator_peer_id: Some("alice".into()),
        }];
        let weights = g.resolve_weights("feat-X", &rows);
        assert!((weights["alice"] - 1.0).abs() < 1e-9);
    }

    #[test]
    fn resolve_weights_with_composition() {
        let mut g = ProvenanceGraph::new();
        g.add_node(node("feat-Y", "feature"));
        g.add_node(node("feat-A", "feature"));
        g.add_node(node("feat-B", "feature"));
        let mut comp_weights = HashMap::new();
        comp_weights.insert("feat-A".to_owned(), 0.6);
        comp_weights.insert("feat-B".to_owned(), 0.4);
        let rows = vec![
            ProvenanceCompositionRow {
                kind: "FEATURE_COMPOSITION".into(),
                node_id: None,
                composite_node_id: "feat-Y".into(),
                component_ids: vec!["feat-A".into(), "feat-B".into()],
                component_weights: comp_weights,
                creator_peer_id: None,
            },
            ProvenanceCompositionRow {
                kind: "EQUITY_GRANT".into(),
                node_id: Some("feat-A".into()),
                composite_node_id: String::new(),
                component_ids: vec![],
                component_weights: HashMap::new(),
                creator_peer_id: Some("alice".into()),
            },
            ProvenanceCompositionRow {
                kind: "EQUITY_GRANT".into(),
                node_id: Some("feat-B".into()),
                composite_node_id: String::new(),
                component_ids: vec![],
                component_weights: HashMap::new(),
                creator_peer_id: Some("bob".into()),
            },
        ];
        let weights = g.resolve_weights("feat-Y", &rows);
        assert!(weights.contains_key("alice") || weights.contains_key("bob"));
        let total: f64 = weights.values().sum();
        assert!((total - 1.0).abs() < 1e-9, "weights don't sum to 1: {total}");
    }
}
