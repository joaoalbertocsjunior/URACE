//! Task dependency tracking — delivery graph.
//!
//! Ported from `delivery_graph.py` (77 lines).
//!
//! The Python module implements proportional delivery-fee distribution
//! (`delivery_weights`, `delivery_fee_amounts`).  Those functions operate
//! purely over slices of ledger rows and carry no internal state, so they
//! are modelled here as free functions alongside the stateful `DeliveryGraph`
//! struct that tracks per-task delivery status.

use std::collections::{HashMap, HashSet};
use thiserror::Error;

/// Errors returned by graph operations.
#[derive(Debug, Error, PartialEq)]
pub enum GraphError {
    /// A dependency chain forms a cycle.
    #[error("cycle detected in delivery graph")]
    CycleDetected,
    /// The referenced task does not exist in the graph.
    #[error("task not found: {0}")]
    NotFound(String),
}

/// A single node in the delivery dependency graph.
#[derive(Debug, Clone)]
pub struct DeliveryNode {
    /// Stable task identifier.
    pub task_id: String,
    /// IDs of tasks that must be delivered before this one is ready.
    pub deps: Vec<String>,
    /// Delivery status.  `"pending"` or `"delivered"`.
    pub status: String,
}

impl DeliveryNode {
    fn is_delivered(&self) -> bool {
        self.status == "delivered"
    }
}

/// Directed acyclic graph that tracks task delivery order.
#[derive(Debug, Default)]
pub struct DeliveryGraph {
    pub nodes: HashMap<String, DeliveryNode>,
}

impl DeliveryGraph {
    /// Create an empty graph.
    pub fn new() -> Self {
        Self::default()
    }

    /// Add a task with its declared dependencies.
    ///
    /// Returns `GraphError::NotFound` if any dependency is not already
    /// registered, and `GraphError::CycleDetected` if adding the node would
    /// introduce a cycle.
    pub fn add_node(&mut self, task_id: impl Into<String>, deps: Vec<String>) -> Result<(), GraphError> {
        let task_id = task_id.into();

        // All declared dependencies must already be registered.
        for dep in &deps {
            if !self.nodes.contains_key(dep) {
                return Err(GraphError::NotFound(dep.clone()));
            }
        }

        let node = DeliveryNode {
            task_id: task_id.clone(),
            deps,
            status: "pending".to_string(),
        };
        self.nodes.insert(task_id.clone(), node);

        // Cycle check via DFS from the new node.
        if self.has_cycle(&task_id) {
            self.nodes.remove(&task_id);
            return Err(GraphError::CycleDetected);
        }

        Ok(())
    }

    /// Mark a task as delivered.
    ///
    /// Returns `GraphError::NotFound` if the task has not been registered.
    pub fn mark_delivered(&mut self, task_id: &str) -> Result<(), GraphError> {
        self.nodes
            .get_mut(task_id)
            .ok_or_else(|| GraphError::NotFound(task_id.to_string()))?
            .status = "delivered".to_string();
        Ok(())
    }

    /// Return the IDs of all nodes whose dependencies are fully delivered
    /// and that are not yet delivered themselves.
    pub fn ready_nodes(&self) -> Vec<String> {
        let mut ready: Vec<String> = self
            .nodes
            .values()
            .filter(|n| {
                !n.is_delivered()
                    && n.deps.iter().all(|dep| {
                        self.nodes
                            .get(dep)
                            .map(|d| d.is_delivered())
                            .unwrap_or(false)
                    })
            })
            .map(|n| n.task_id.clone())
            .collect();
        // Deterministic ordering for testability.
        ready.sort();
        ready
    }

    // --- internal helpers ---

    /// DFS cycle detection from `start`.
    fn has_cycle(&self, start: &str) -> bool {
        let mut visited = HashSet::new();
        let mut stack = HashSet::new();
        self.dfs_has_cycle(start, &mut visited, &mut stack)
    }

    fn dfs_has_cycle(
        &self,
        node_id: &str,
        visited: &mut HashSet<String>,
        stack: &mut HashSet<String>,
    ) -> bool {
        if stack.contains(node_id) {
            return true;
        }
        if visited.contains(node_id) {
            return false;
        }
        visited.insert(node_id.to_string());
        stack.insert(node_id.to_string());

        if let Some(node) = self.nodes.get(node_id) {
            for dep in &node.deps {
                if self.dfs_has_cycle(dep, visited, stack) {
                    stack.remove(node_id);
                    return true;
                }
            }
        }
        stack.remove(node_id);
        false
    }
}

// ---------------------------------------------------------------------------
// Proportional delivery-fee helpers (ported from delivery_graph.py)
// ---------------------------------------------------------------------------

/// Default erasure-coding total chunk count (n_data=4 + n_parity=2).
pub const DEFAULT_N_TOTAL: usize = 6;

/// Compute `{peer_id: weight}` for delivery-fee distribution.
///
/// Only non-creator replica holders are considered.  Weights sum to 1.0.
/// Returns an empty map when no replicas are registered (creator delivers;
/// no delivery fee applies).
pub fn delivery_weights(
    feature_id: &str,
    rows: &[serde_json::Value],
    original_creator: &str,
    n_total: usize,
) -> HashMap<String, f64> {
    // Collect relevant replica rows.
    let replicas: Vec<&serde_json::Value> = rows
        .iter()
        .filter(|r| {
            r.get("kind").and_then(|v| v.as_str()) == Some("BUNDLE_REPLICA_REGISTERED")
                && r.get("feature_id").and_then(|v| v.as_str()) == Some(feature_id)
                && r.get("replica_peer_id")
                    .and_then(|v| v.as_str())
                    .map(|pid| !pid.is_empty() && pid != original_creator)
                    .unwrap_or(false)
        })
        .collect();

    if replicas.is_empty() {
        return HashMap::new();
    }

    // Last registration wins per peer.
    let mut peer_chunks: HashMap<String, HashSet<usize>> = HashMap::new();
    for r in &replicas {
        let pid = r["replica_peer_id"].as_str().unwrap_or("").to_string();
        let indices = r.get("chunk_indices").and_then(|v| v.as_array());
        let chunks: HashSet<usize> = match indices {
            Some(arr) if !arr.is_empty() => arr
                .iter()
                .filter_map(|v| v.as_u64().map(|i| i as usize))
                .collect(),
            _ => (0..n_total).collect(),
        };
        peer_chunks.insert(pid, chunks);
    }

    if peer_chunks.is_empty() {
        return HashMap::new();
    }

    let raw: HashMap<String, f64> = peer_chunks
        .iter()
        .map(|(pid, chunks)| (pid.clone(), chunks.len() as f64 / n_total as f64))
        .collect();

    let total: f64 = raw.values().sum();
    if total <= 0.0 {
        return HashMap::new();
    }

    raw.into_iter().map(|(pid, w)| (pid, w / total)).collect()
}

/// Compute `{peer_id: fee_units}` for delivery-fee distribution.
///
/// Integer rounding: remainder goes to the highest-weight peer.
/// Returns empty map when the creator delivers (no replicas) or price ≤ 0.
pub fn delivery_fee_amounts(
    feature_id: &str,
    rows: &[serde_json::Value],
    original_creator: &str,
    price: i64,
    delivery_fee_fraction: f64,
    n_total: usize,
) -> HashMap<String, i64> {
    let weights = delivery_weights(feature_id, rows, original_creator, n_total);
    if weights.is_empty() || price <= 0 {
        return HashMap::new();
    }

    let pool = std::cmp::max(1, (price as f64 * delivery_fee_fraction) as i64);
    let mut alloc: HashMap<String, i64> = HashMap::new();
    let mut remainder = pool;

    // Deterministic order: descending weight.
    let mut sorted_weights: Vec<(String, f64)> = weights.iter().map(|(k, v)| (k.clone(), *v)).collect();
    sorted_weights.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));

    for (pid, w) in &sorted_weights {
        let units = (pool as f64 * w) as i64;
        alloc.insert(pid.clone(), units);
        remainder -= units;
    }

    // Remainder to highest-weight peer.
    if let Some((top, _)) = sorted_weights.first() {
        *alloc.entry(top.clone()).or_insert(0) += remainder;
    }

    alloc.into_iter().filter(|(_, u)| *u > 0).collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_graph_with_chain() -> DeliveryGraph {
        let mut g = DeliveryGraph::new();
        g.add_node("a", vec![]).unwrap();
        g.add_node("b", vec!["a".to_string()]).unwrap();
        g.add_node("c", vec!["b".to_string()]).unwrap();
        g
    }

    #[test]
    fn ready_nodes_respects_deps() {
        let mut g = make_graph_with_chain();
        // Only "a" has no deps.
        assert_eq!(g.ready_nodes(), vec!["a"]);
        g.mark_delivered("a").unwrap();
        assert_eq!(g.ready_nodes(), vec!["b"]);
        g.mark_delivered("b").unwrap();
        assert_eq!(g.ready_nodes(), vec!["c"]);
    }

    #[test]
    fn mark_delivered_unknown_task_returns_error() {
        let mut g = DeliveryGraph::new();
        assert_eq!(
            g.mark_delivered("ghost"),
            Err(GraphError::NotFound("ghost".to_string()))
        );
    }

    #[test]
    fn add_node_missing_dep_returns_error() {
        let mut g = DeliveryGraph::new();
        let result = g.add_node("x", vec!["nonexistent".to_string()]);
        assert_eq!(result, Err(GraphError::NotFound("nonexistent".to_string())));
    }

    #[test]
    fn delivery_weights_no_replicas_returns_empty() {
        let weights = delivery_weights("feat-1", &[], "peer-creator", DEFAULT_N_TOTAL);
        assert!(weights.is_empty());
    }

    #[test]
    fn delivery_fee_amounts_zero_price_returns_empty() {
        let amounts = delivery_fee_amounts("feat-1", &[], "peer-creator", 0, 0.10, DEFAULT_N_TOTAL);
        assert!(amounts.is_empty());
    }

    #[test]
    fn delivery_fee_amounts_with_replica() {
        let row = serde_json::json!({
            "kind": "BUNDLE_REPLICA_REGISTERED",
            "feature_id": "feat-1",
            "replica_peer_id": "peer-b",
            "chunk_indices": [0, 1, 2]
        });
        let rows = vec![row];
        let amounts = delivery_fee_amounts("feat-1", &rows, "peer-creator", 1000, 0.10, DEFAULT_N_TOTAL);
        // Single replica gets all of pool (max(1, 100) = 100).
        assert_eq!(amounts.get("peer-b"), Some(&100));
    }
}
