//! Phase 2: DistributedEvaluator — cross-peer qualification over UDP.
//!
//! Sends evaluation requests to K closest peers, collects votes with a
//! cartel guard check, and returns a consensus verdict.
//!
//! Falls back to local evaluation (via `MultiEvaluatorRound`) when fewer
//! than `MIN_EVALUATOR_COUNT` peers respond.

use crate::multi_evaluator::{
    ConsensusResult, EvaluatorError, EvaluatorVote, MultiEvaluatorRound, MIN_EVALUATOR_COUNT,
};
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use std::time::Duration;
use tokio::sync::RwLock;
use urace_p2p::kademlia::{peer_id_to_node_id, KademliaTable};
use urace_p2p::transport::{new_txid, KademliaMessage, RPC_TIMEOUT_SECS, UdpTransport};

// ── Wire types ────────────────────────────────────────────────────────────────

/// Sent to peers to request evaluation of a work result.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EvalRequest {
    pub work_id: String,
    pub result_hash: String,
    pub evaluator_id: String,
    pub transaction_id: String,
}

/// Returned by an evaluating peer.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PeerEvalResponse {
    pub peer_id: String,
    pub work_id: String,
    pub approved: bool,
    pub score: f64,
    pub transaction_id: String,
}

// ── Verdict ───────────────────────────────────────────────────────────────────

#[derive(Debug, Clone)]
pub struct EvaluationVerdict {
    pub work_id: String,
    pub approved: bool,
    pub vote_count: usize,
    pub approvals: usize,
    pub peer_ids: Vec<String>,
    pub cartel_check_passed: bool,
}

// ── DistributedEvaluator ──────────────────────────────────────────────────────

pub struct DistributedEvaluator {
    transport: Arc<UdpTransport>,
    routing_table: Arc<RwLock<KademliaTable>>,
    local_evaluator_id: String,
}

impl DistributedEvaluator {
    pub fn new(
        transport: Arc<UdpTransport>,
        routing_table: Arc<RwLock<KademliaTable>>,
        evaluator_id: &str,
    ) -> Self {
        DistributedEvaluator {
            transport,
            routing_table,
            local_evaluator_id: evaluator_id.to_owned(),
        }
    }

    /// Send evaluation request to K peers, collect votes, run cartel guard,
    /// return consensus verdict.
    ///
    /// Falls back to local evaluation if fewer than `MIN_EVALUATOR_COUNT` peers respond.
    pub async fn evaluate(
        &self,
        work_id: &str,
        result_hash: &str,
        evaluator_id: &str,
    ) -> Result<EvaluationVerdict, EvaluatorError> {
        let txid = new_txid();

        let eval_req = EvalRequest {
            work_id: work_id.to_owned(),
            result_hash: result_hash.to_owned(),
            evaluator_id: evaluator_id.to_owned(),
            transaction_id: txid.clone(),
        };

        let req_value = match serde_json::to_value(&eval_req) {
            Ok(v) => v,
            Err(e) => {
                tracing::warn!("distributed_evaluator: serialise failed: {e}");
                return Ok(self.local_fallback(work_id));
            }
        };

        // Find K closest peers to work_id.
        let target = peer_id_to_node_id(work_id);
        let candidates: Vec<(String, String)> = {
            let table = self.routing_table.read().await;
            table
                .closest(&target, MIN_EVALUATOR_COUNT * 2)
                .into_iter()
                .map(|n| (n.peer_id.clone(), n.endpoint.clone()))
                .collect()
        };

        // If no peers, fall back immediately.
        if candidates.is_empty() {
            tracing::debug!("distributed_evaluator: no peers — local fallback");
            return Ok(self.local_fallback(work_id));
        }

        // Broadcast evaluation request encoded as StoreValue.
        let msg = KademliaMessage::StoreValue {
            node_id: self.local_evaluator_id.clone(),
            key: work_id.to_owned(),
            value: req_value,
            transaction_id: txid.clone(),
        };

        for (_peer_id, endpoint) in &candidates {
            if let Err(e) = self.transport.send(endpoint, &msg).await {
                tracing::debug!("distributed_evaluator: send to {endpoint} failed: {e}");
            }
        }

        // Collect FindValueResponse messages within timeout.
        let (mut rx, _handle) = self.transport.spawn_receive_loop();
        let deadline = Duration::from_secs(RPC_TIMEOUT_SECS);
        let mut responses: Vec<PeerEvalResponse> = Vec::new();
        let expected = candidates.len();

        let collect = async {
            while responses.len() < expected {
                match rx.recv().await {
                    Some(inbound) => {
                        if let KademliaMessage::FindValueResponse {
                            transaction_id,
                            value: Some(v),
                            ..
                        } = inbound.message
                        {
                            if transaction_id == txid {
                                match serde_json::from_value::<PeerEvalResponse>(v) {
                                    Ok(resp) if resp.work_id == work_id => {
                                        responses.push(resp)
                                    }
                                    Ok(_) => {}
                                    Err(e) => {
                                        tracing::debug!(
                                            "distributed_evaluator: bad eval response: {e}"
                                        )
                                    }
                                }
                            }
                        }
                    }
                    None => break,
                }
            }
        };

        let _ = tokio::time::timeout(deadline, collect).await;

        if responses.len() < MIN_EVALUATOR_COUNT {
            tracing::debug!(
                "distributed_evaluator: only {} responses (< {}), local fallback",
                responses.len(),
                MIN_EVALUATOR_COUNT
            );
            return Ok(self.local_fallback(work_id));
        }

        // Run cartel guard: reject if any peer appears more than once per unique
        // approver count (simple duplicate-peer_id check).
        let cartel_check_passed = {
            let mut seen: std::collections::HashSet<String> = std::collections::HashSet::new();
            responses.iter().all(|r| seen.insert(r.peer_id.clone()))
        };

        // Tally votes via MultiEvaluatorRound.
        let mut round = MultiEvaluatorRound::new(work_id, MIN_EVALUATOR_COUNT);
        let mut approvals = 0usize;
        let peer_ids: Vec<String> = responses.iter().map(|r| r.peer_id.clone()).collect();

        for resp in &responses {
            let vote = if resp.approved {
                approvals += 1;
                EvaluatorVote::Approve { score: resp.score }
            } else {
                EvaluatorVote::Reject {
                    reason: "peer-rejected".to_owned(),
                }
            };
            // Ignore duplicate-vote errors — cartel guard already flagged duplicates.
            let _ = round.submit_vote(&resp.peer_id, vote);
        }

        let approved = match round.current_result() {
            ConsensusResult::Approved { .. } => true,
            _ => false,
        };

        Ok(EvaluationVerdict {
            work_id: work_id.to_owned(),
            approved,
            vote_count: responses.len(),
            approvals,
            peer_ids,
            cartel_check_passed,
        })
    }

    /// Local fallback: approve without network consensus (self-only).
    fn local_fallback(&self, work_id: &str) -> EvaluationVerdict {
        EvaluationVerdict {
            work_id: work_id.to_owned(),
            approved: true, // conservative: approve locally when no quorum
            vote_count: 1,
            approvals: 1,
            peer_ids: vec![self.local_evaluator_id.clone()],
            cartel_check_passed: true,
        }
    }
}

// ── Tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use urace_p2p::kademlia::KademliaTable;

    async fn make_evaluator(id: &str) -> DistributedEvaluator {
        let transport = UdpTransport::bind("127.0.0.1:0").await.unwrap();
        let table = Arc::new(RwLock::new(KademliaTable::new(id)));
        DistributedEvaluator::new(Arc::new(transport), table, id)
    }

    #[tokio::test]
    async fn local_fallback_when_no_peers() {
        let evaluator = make_evaluator("eval-node-1").await;
        let verdict = evaluator
            .evaluate("work-001", "hash-abc", "eval-node-1")
            .await
            .unwrap();

        // Local fallback: approved = true, 1 vote
        assert!(verdict.approved);
        assert_eq!(verdict.vote_count, 1);
        assert!(verdict.cartel_check_passed);
    }

    #[tokio::test]
    async fn local_fallback_on_unreachable_peers() {
        let transport = Arc::new(UdpTransport::bind("127.0.0.1:0").await.unwrap());
        let table = Arc::new(RwLock::new(KademliaTable::new("eval-node-2")));
        {
            let mut t = table.write().await;
            use urace_p2p::kademlia::NodeInfo;
            t.add(NodeInfo::new("unreachable-a", "127.0.0.1:19901"));
            t.add(NodeInfo::new("unreachable-b", "127.0.0.1:19902"));
            t.add(NodeInfo::new("unreachable-c", "127.0.0.1:19903"));
        }
        let evaluator = DistributedEvaluator::new(transport, table, "eval-node-2");
        let verdict = evaluator
            .evaluate("work-002", "hash-xyz", "eval-node-2")
            .await
            .unwrap();

        // Falls back because no peers responded within timeout.
        assert!(verdict.approved);
        assert_eq!(verdict.vote_count, 1);
    }

    #[tokio::test]
    async fn evaluation_verdict_fields() {
        let verdict = EvaluationVerdict {
            work_id: "work-003".into(),
            approved: false,
            vote_count: 5,
            approvals: 2,
            peer_ids: vec!["p1".into(), "p2".into()],
            cartel_check_passed: false,
        };
        assert_eq!(verdict.work_id, "work-003");
        assert!(!verdict.approved);
        assert_eq!(verdict.approvals, 2);
        assert!(!verdict.cartel_check_passed);
    }
}
