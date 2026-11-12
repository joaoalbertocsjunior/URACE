"""BFT-lite consensus for URACE ledger seals.

Threshold: max(2, ceil(2 * N / 3)) distinct peer signatures on the same seal hash
where N = estimated_network_size from peer discovery.

This is local-vote aggregation — does NOT implement a full BFT protocol.
Works as: propose -> collect votes from known peers -> finalize when threshold met.
"""
import hashlib
import json
import math
import time

from . import ledger_crypto
from . import peer_exchange
from .ledger_sync import latest_seal


def consensus_threshold(exchange) -> int:
    """Return BFT-lite vote threshold for the current estimated network size."""
    n = exchange.load().get('estimated_network_size', 1)
    return max(2, math.ceil(2 * n / 3))


def propose_seal(exchange, rows: list) -> dict:
    """Build and sign a seal proposal for the given audit rows.

    Returns {'proposal': dict, 'signature': dict}.
    """
    seal_hash = hashlib.sha256(
        json.dumps(
            [r.get('sha256', '') for r in rows],
            sort_keys=True,
        ).encode()
    ).hexdigest()

    proposal = {
        'schema': 'urace-consensus-v1',
        'seal_hash': seal_hash,
        'row_count': len(rows),
        'head_sha': rows[-1]['sha256'] if rows else '0' * 64,
        'proposed_at': time.time(),
        'proposer_peer_id': exchange.identity()['peer_id'],
    }
    sig = exchange.crypto_identity().sign(proposal, 'seal-proposal')
    return {'proposal': proposal, 'signature': sig}


def collect_seal_votes(exchange, peer_ids: list, seal_proposal: dict) -> list:
    """Request seal votes from each peer, returning successful vote records.

    Each record: {'peer_id': str, 'voter_signature': dict, 'seal_hash': str}.
    """
    votes = []
    seal_hash = seal_proposal['proposal']['seal_hash']
    for peer_id in peer_ids:
        try:
            resp = peer_exchange.request(
                exchange,
                peer_id,
                'exchange.seal_vote',
                {
                    'seal_hash': seal_hash,
                    'voter_peer_id': exchange.identity()['peer_id'],
                },
            )
            if (
                isinstance(resp, dict)
                and resp.get('status') == 'ok'
                and resp.get('voter_signature')
            ):
                votes.append({
                    'peer_id': resp.get('voter_peer_id', peer_id),
                    'voter_signature': resp['voter_signature'],
                    'seal_hash': resp.get('seal_hash', seal_hash),
                })
        except Exception:
            pass
    return votes


def handle_seal_vote(exchange, sender_peer_id: str, params: dict) -> dict:
    """Server-side: validate seal vote request and return a signed vote if the
    local chain tip matches.

    Returns {'status': 'ok', ...} or {'status': 'mismatch', 'local_head': str}.
    """
    requested_hash = params.get('seal_hash', '')

    local_rows = []
    try:
        local_rows = exchange.audit_rows()
    except Exception:
        pass

    local_head = local_rows[-1].get('sha256', '0' * 64) if local_rows else '0' * 64

    # Recompute local seal hash to compare against the requested one
    local_seal_hash = hashlib.sha256(
        json.dumps(
            [r.get('sha256', '') for r in local_rows],
            sort_keys=True,
        ).encode()
    ).hexdigest()

    if local_seal_hash != requested_hash:
        return {'status': 'mismatch', 'local_head': local_head}

    sig = exchange.crypto_identity().sign({'seal_hash': requested_hash}, 'seal-vote')
    exchange.event('SEAL_VOTE_CAST', seal_hash=requested_hash, requester_peer_id=sender_peer_id)

    return {
        'status': 'ok',
        'voter_peer_id': exchange.identity()['peer_id'],
        'voter_signature': sig,
        'seal_hash': requested_hash,
    }


def finalize_seal(exchange, seal_proposal: dict, votes: list) -> dict:
    """Finalize a seal when enough distinct peer votes have been collected.

    Returns {'finalized': True/False, 'seal_hash': str, ...}.
    """
    seal_hash = seal_proposal['proposal']['seal_hash']
    threshold = consensus_threshold(exchange)

    # Deduplicate by peer_id
    seen_peers: set = set()
    distinct_votes = []
    for vote in votes:
        pid = vote.get('peer_id')
        if pid and pid not in seen_peers:
            seen_peers.add(pid)
            distinct_votes.append(vote)

    vote_count = len(distinct_votes)

    if vote_count >= threshold:
        exchange.event(
            'SEAL_FINALIZED',
            seal_hash=seal_hash,
            vote_count=vote_count,
            votes=distinct_votes,
            is_finalized=True,
        )
        return {'finalized': True, 'seal_hash': seal_hash, 'vote_count': vote_count}

    return {
        'finalized': False,
        'seal_hash': seal_hash,
        'required': threshold,
        'got': vote_count,
    }
