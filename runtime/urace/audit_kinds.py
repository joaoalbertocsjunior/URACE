"""Phase 7E — canonical audit event kind constants.

Single source of truth for all string literals used as exchange audit
row ``kind`` values.  Import from here rather than repeating raw strings.

Usage::

    from urace.audit_kinds import FEATURE_BORROWED, APPLIED_AFTER_LOCAL_QUALIFICATION
"""
from __future__ import annotations

# ── Feature exchange ──────────────────────────────────────────────────────────
FEATURE_BORROWED                    = 'FEATURE_BORROWED'
FEATURE_COMPOSITION                 = 'FEATURE_COMPOSITION'
FEATURE_RATING                      = 'FEATURE_RATING'
APPLIED_AFTER_LOCAL_QUALIFICATION   = 'APPLIED_AFTER_LOCAL_QUALIFICATION'
QUALIFICATION_RECEIPT               = 'QUALIFICATION_RECEIPT'
QUALIFY_RECEIPT                     = 'QUALIFY_RECEIPT'
QUALITY_VERIFICATION                = 'QUALITY_VERIFICATION'
SIMILARITY_VERDICT                  = 'SIMILARITY_VERDICT'
CATALOG_CHECK                       = 'CATALOG_CHECK'

# ── Credit / cost ─────────────────────────────────────────────────────────────
CREDIT_DELTA                        = 'CREDIT_DELTA'
MINT_STAKE_LOCKED                   = 'MINT_STAKE_LOCKED'
MINT_STAKE_RELEASED                 = 'MINT_STAKE_RELEASED'
MINT_STAKE_SLASHED                  = 'MINT_STAKE_SLASHED'
RECEIVE_RESERVED                    = 'RECEIVE_RESERVED'
SEND_FAILED_OR_UNCONFIRMED          = 'SEND_FAILED_OR_UNCONFIRMED'

# ── Assets ────────────────────────────────────────────────────────────────────
ASSET_EARN                          = 'ASSET_EARN'
ASSET_REGISTERED                    = 'ASSET_REGISTERED'
ASSET_TRANSFER_PENDING              = 'ASSET_TRANSFER_PENDING'
ASSET_TRANSFERRED                   = 'ASSET_TRANSFERRED'
NFT_MINT_REQUESTED                  = 'NFT_MINT_REQUESTED'
OPEN_ASSET_BUNDLE_PREPARED          = 'OPEN_ASSET_BUNDLE_PREPARED'
OPEN_ASSET_QUARANTINE_ACK           = 'OPEN_ASSET_QUARANTINE_ACK'
OPEN_ASSET_QUARANTINE_ACK_ATTESTED  = 'OPEN_ASSET_QUARANTINE_ACK_ATTESTED'
OPEN_ASSET_SELLER_ACK_RECEIVED      = 'OPEN_ASSET_SELLER_ACK_RECEIVED'
BUNDLE_REPLICA_REGISTERED           = 'BUNDLE_REPLICA_REGISTERED'
BUNDLE_REPLICATION_OFFER            = 'BUNDLE_REPLICATION_OFFER'

# ── Equity ────────────────────────────────────────────────────────────────────
EQUITY_CREATED                      = 'EQUITY_CREATED'
EQUITY_ESCROW                       = 'EQUITY_ESCROW'
EQUITY_GRANT                        = 'EQUITY_GRANT'
EQUITY_GRANT_REVOKED                = 'EQUITY_GRANT_REVOKED'
EQUITY_LISTING                      = 'EQUITY_LISTING'
EQUITY_LISTING_CANCELLED            = 'EQUITY_LISTING_CANCELLED'
EQUITY_LISTING_FILLED               = 'EQUITY_LISTING_FILLED'
EQUITY_SELL                         = 'EQUITY_SELL'

# ── Work market ───────────────────────────────────────────────────────────────
WORK_REQUEST                        = 'WORK_REQUEST'
WORK_BID                            = 'WORK_BID'
WORK_CONTRACT_SUMMARY               = 'WORK_CONTRACT_SUMMARY'
WORK_ACCEPTED                       = 'WORK_ACCEPTED'
WORK_DELIVERY                       = 'WORK_DELIVERY'
WORK_PEER_REVIEW                    = 'WORK_PEER_REVIEW'
WORK_VERIFIED                       = 'WORK_VERIFIED'
WORK_MERGED                         = 'WORK_MERGED'
WORK_RELEASED                       = 'WORK_RELEASED'
WORK_DISPUTED                       = 'WORK_DISPUTED'
WORK_RESOLVED                       = 'WORK_RESOLVED'
WORK_OWNERSHIP_CLAIM                = 'WORK_OWNERSHIP_CLAIM'

# ── Peer / network ────────────────────────────────────────────────────────────
PEER_ADDED                          = 'PEER_ADDED'
PEER_ANNOUNCE                       = 'PEER_ANNOUNCE'
PEER_BLOCKED                        = 'PEER_BLOCKED'
PEER_EXCHANGE_COMPLETED             = 'PEER_EXCHANGE_COMPLETED'
NETWORK_ANNOUNCE                    = 'NETWORK_ANNOUNCE'
HOLE_PUNCH_ATTEMPTED                = 'HOLE_PUNCH_ATTEMPTED'
FEDERATION_ADOPTION                 = 'FEDERATION_ADOPTION'

# ── Security / governance ─────────────────────────────────────────────────────
CARTEL_CANDIDATE                    = 'CARTEL_CANDIDATE'
CARTEL_CHUNK_CONCENTRATION          = 'CARTEL_CHUNK_CONCENTRATION'
SYBIL_CANDIDATE                     = 'SYBIL_CANDIDATE'
PROHIBITION                         = 'PROHIBITION'
DIRECTIVE                           = 'DIRECTIVE'
PROVENANCE_CHALLENGE                = 'PROVENANCE_CHALLENGE'
PROVENANCE_CHALLENGE_RESOLVED       = 'PROVENANCE_CHALLENGE_RESOLVED'
DECISION_EVALUATION_ONLY            = 'DECISION_EVALUATION_ONLY'

# ── Ledger / RPC ─────────────────────────────────────────────────────────────
LEDGER_BLOCK_SEAL                   = 'LEDGER_BLOCK_SEAL'
LEDGER_CHECKPOINT                   = 'LEDGER_CHECKPOINT'
RPC_ADMITTED                        = 'RPC_ADMITTED'
RPC_REJECTED                        = 'RPC_REJECTED'
SENT_QUARANTINED                    = 'SENT_QUARANTINED'
UNKNOWN                             = 'UNKNOWN'

# ── Convenience set for validation ───────────────────────────────────────────
ALL_KINDS: frozenset[str] = frozenset({
    v for k, v in globals().items()
    if not k.startswith('_') and isinstance(v, str) and v == v.upper()
})
