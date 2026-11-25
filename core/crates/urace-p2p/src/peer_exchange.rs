//! R-7: Peer exchange protocol — JSON-line codec + message handler.
//!
//! Each message is serialised as a single JSON line (no framing headers).
//! The handler integrates with the KademliaTable routing table and the
//! AdmissionGate to ensure only admitted peers influence routing state.

use crate::kademlia::{KademliaTable, NodeInfo};
use crate::peer_discovery::AdmissionGate;
use ed25519_dalek::{Signer, SigningKey};
use serde::{Deserialize, Serialize};

/// Wire messages for the URACE peer exchange protocol.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum PeerExchangeMsg {
    Ping { from_peer_id: String, seq: u64 },
    Pong { from_peer_id: String, seq: u64 },
    PeerList { peers: Vec<NodeInfo> },
    SealVoteRequest { seal_hash: String },
    /// `signature_hex` is an Ed25519 signature over `b"seal-vote:" + seal_hash`.
    /// Empty string only when no signing key is available (test / stub mode).
    SealVoteResponse { seal_hash: String, signature_hex: String },
}

/// Codec for peer exchange messages — serialize/deserialize via serde_json.
///
/// Each message is a single JSON line (`\n`-terminated).
pub struct PeerExchangeCodec;

impl PeerExchangeCodec {
    /// Serialise a message to a JSON line.
    pub fn encode(msg: &PeerExchangeMsg) -> Result<String, serde_json::Error> {
        serde_json::to_string(msg)
    }

    /// Deserialise a JSON line into a message.
    pub fn decode(line: &str) -> Result<PeerExchangeMsg, serde_json::Error> {
        serde_json::from_str(line.trim())
    }
}

/// Handle an incoming `PeerExchangeMsg`.
///
/// `signing_key` — if `Some`, used to produce an Ed25519 signature on
/// `SealVoteRequest` responses.  Pass `None` only in tests / stub mode.
///
/// Security: `PeerList` entries are only added to the routing table if the
/// originating peer_id is admitted by the `AdmissionGate`.
pub fn handle_message(
    msg: PeerExchangeMsg,
    table: &mut KademliaTable,
    gate: &AdmissionGate,
    signing_key: Option<&SigningKey>,
) -> Option<PeerExchangeMsg> {
    match msg {
        PeerExchangeMsg::Ping { from_peer_id, seq } => {
            Some(PeerExchangeMsg::Pong { from_peer_id, seq })
        }
        PeerExchangeMsg::Pong { .. } => None,
        PeerExchangeMsg::PeerList { peers } => {
            for node in peers {
                if gate.is_admitted(&node.peer_id) {
                    table.add(node);
                }
            }
            None
        }
        PeerExchangeMsg::SealVoteRequest { seal_hash } => {
            let signature_hex = match signing_key {
                Some(key) => {
                    let mut msg_bytes = b"seal-vote:".to_vec();
                    msg_bytes.extend_from_slice(seal_hash.as_bytes());
                    let sig = key.sign(&msg_bytes);
                    hex::encode(sig.to_bytes())
                }
                None => String::new(),
            };
            Some(PeerExchangeMsg::SealVoteResponse { seal_hash, signature_hex })
        }
        PeerExchangeMsg::SealVoteResponse { .. } => None,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::kademlia::KademliaTable;
    use crate::peer_discovery::AdmissionGate;
    use ed25519_dalek::SigningKey;
    use rand::rngs::OsRng;

    fn make_node(id: &str) -> NodeInfo {
        NodeInfo::new(id, "127.0.0.1:0")
    }

    #[test]
    fn test_codec_roundtrip() {
        let msg = PeerExchangeMsg::Ping { from_peer_id: "peer-a".into(), seq: 42 };
        let line = PeerExchangeCodec::encode(&msg).unwrap();
        let decoded = PeerExchangeCodec::decode(&line).unwrap();
        match decoded {
            PeerExchangeMsg::Ping { from_peer_id, seq } => {
                assert_eq!(from_peer_id, "peer-a");
                assert_eq!(seq, 42);
            }
            _ => panic!("wrong variant"),
        }
    }

    #[test]
    fn test_ping_returns_pong() {
        let gate = AdmissionGate::new();
        let mut table = KademliaTable::new("self");
        let msg = PeerExchangeMsg::Ping { from_peer_id: "peer-b".into(), seq: 1 };
        let resp = handle_message(msg, &mut table, &gate, None);
        assert!(matches!(resp, Some(PeerExchangeMsg::Pong { seq: 1, .. })));
    }

    #[test]
    fn test_peer_list_only_admits_admitted_peers() {
        let gate = AdmissionGate::new();
        gate.admit("peer-admitted", 1);
        let mut table = KademliaTable::new("self");
        let peers = vec![make_node("peer-admitted"), make_node("peer-unknown")];
        let msg = PeerExchangeMsg::PeerList { peers };
        handle_message(msg, &mut table, &gate, None);
        let target_id = crate::kademlia::peer_id_to_node_id("peer-admitted");
        let closest = table.closest(&target_id, 10);
        assert!(
            closest.iter().any(|n| n.peer_id == "peer-admitted"),
            "admitted peer should be in routing table"
        );
    }

    #[test]
    fn test_seal_vote_unsigned_stub() {
        let gate = AdmissionGate::new();
        let mut table = KademliaTable::new("self");
        let msg = PeerExchangeMsg::SealVoteRequest { seal_hash: "abc123".into() };
        let resp = handle_message(msg, &mut table, &gate, None);
        match resp {
            Some(PeerExchangeMsg::SealVoteResponse { seal_hash, signature_hex }) => {
                assert_eq!(seal_hash, "abc123");
                assert!(signature_hex.is_empty(), "no key → empty signature");
            }
            _ => panic!("expected SealVoteResponse"),
        }
    }

    #[test]
    fn test_seal_vote_signed() {
        let key = SigningKey::generate(&mut OsRng);
        let gate = AdmissionGate::new();
        let mut table = KademliaTable::new("self");
        let msg = PeerExchangeMsg::SealVoteRequest { seal_hash: "deadbeef".into() };
        let resp = handle_message(msg, &mut table, &gate, Some(&key));
        match resp {
            Some(PeerExchangeMsg::SealVoteResponse { seal_hash, signature_hex }) => {
                assert_eq!(seal_hash, "deadbeef");
                assert_eq!(signature_hex.len(), 128, "Ed25519 sig = 64 bytes = 128 hex chars");
                // Verify signature is valid.
                use ed25519_dalek::Verifier;
                let vk = key.verifying_key();
                let sig_bytes = hex::decode(&signature_hex).unwrap();
                let sig = ed25519_dalek::Signature::from_slice(&sig_bytes).unwrap();
                let mut msg_bytes = b"seal-vote:".to_vec();
                msg_bytes.extend_from_slice(seal_hash.as_bytes());
                vk.verify(&msg_bytes, &sig).expect("signature must verify");
            }
            _ => panic!("expected SealVoteResponse"),
        }
    }
}
