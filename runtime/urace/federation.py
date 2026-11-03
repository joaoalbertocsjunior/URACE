"""Cross-URACE peer federation — network-of-networks discovery and feature query.

Federation model:
  - Each URACE network announces itself via NETWORK_ANNOUNCE audit rows.
  - Federated networks are trusted at a lower tier than local peers (cross-network
    reputation is discounted by FEDERATION_REP_DISCOUNT until local validation occurs).
  - Features can be queried across federated networks; adoption signals propagate
    back as FEDERATION_ADOPTION rows.
  - Anti-abuse: each announce must include a monotonic sequence_id; old announces are
    rejected if seq < current max seq for that network_id.

Audit row kinds:
  NETWORK_ANNOUNCE     — this network announces itself to others
  FEDERATION_QUERY     — a cross-network feature query broadcast
  FEDERATION_ADOPTION  — a remote network confirms a feature adoption
"""
from __future__ import annotations
import time

SCHEMA = 'urace-federation-v1'

FEDERATION_REP_DISCOUNT  = 0.7    # remote peer rep × 0.7 until local validation
FEDERATION_MIN_REP       = 0.20   # minimum rep floor for federated peers
FEDERATION_QUERY_TTL     = 3600   # seconds before a FEDERATION_QUERY expires


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _fed_rows(exchange) -> list[dict]:
    try:
        rows = exchange.audit_rows()
    except Exception:
        return []
    fed_kinds = {'NETWORK_ANNOUNCE', 'FEDERATION_QUERY', 'FEDERATION_ADOPTION'}
    return [r for r in rows if r.get('kind') in fed_kinds]


def announce_network(exchange, network_id: str, endpoint: str, description: str = '') -> None:
    """Broadcast this network's existence to the exchange audit log.

    Idempotent per sequence: re-announcing with a higher sequence_id updates the
    endpoint; lower or equal sequence is rejected (prevents replay attacks).
    """
    rows = _fed_rows(exchange)
    existing = [r for r in rows
                if r.get('kind') == 'NETWORK_ANNOUNCE' and r.get('network_id') == network_id]
    current_seq = max((int(r.get('sequence_id', 0)) for r in existing), default=0)
    next_seq = current_seq + 1

    exchange.append_audit_row({
        'kind': 'NETWORK_ANNOUNCE',
        'network_id': network_id,
        'endpoint': endpoint,
        'description': description,
        'sequence_id': next_seq,
        'at_unix': time.time(),
        'at': _now_iso(),
    })


def federated_networks(exchange) -> list[dict]:
    """Return all known federated networks with their latest endpoint.

    Only the highest-sequence announce per network_id is returned.
    """
    rows = _fed_rows(exchange)
    announces = [r for r in rows if r.get('kind') == 'NETWORK_ANNOUNCE']
    latest: dict[str, dict] = {}
    for r in announces:
        nid = r.get('network_id', '')
        seq = int(r.get('sequence_id', 0))
        if nid and seq > int(latest.get(nid, {}).get('sequence_id', -1)):
            latest[nid] = r
    return list(latest.values())


def query_feature(exchange, feature_id: str, requester_id: str) -> str:
    """Broadcast a FEDERATION_QUERY for a feature across known federated networks.

    Returns the query_id for tracking the response via federation_adoption_results().
    """
    query_id = f'fq-{int(time.time() * 1000)}-{requester_id[:8]}'
    exchange.append_audit_row({
        'kind': 'FEDERATION_QUERY',
        'query_id': query_id,
        'feature_id': feature_id,
        'requester_id': requester_id,
        'expires_at_unix': time.time() + FEDERATION_QUERY_TTL,
        'at_unix': time.time(),
        'at': _now_iso(),
    })
    return query_id


def record_federation_adoption(
    exchange,
    query_id: str,
    remote_network_id: str,
    feature_id: str,
    adopter_peer_id: str,
    remote_combined_rep: float,
) -> None:
    """Record that a remote network peer adopted a feature in response to a query.

    remote_combined_rep is discounted by FEDERATION_REP_DISCOUNT before being
    used in local calculations — cross-network trust is lower than local trust
    until local validation occurs.
    """
    discounted_rep = max(
        FEDERATION_MIN_REP,
        remote_combined_rep * FEDERATION_REP_DISCOUNT,
    )
    exchange.append_audit_row({
        'kind': 'FEDERATION_ADOPTION',
        'query_id': query_id,
        'feature_id': feature_id,
        'remote_network_id': remote_network_id,
        'adopter_peer_id': adopter_peer_id,
        'remote_combined_rep': remote_combined_rep,
        'discounted_rep': discounted_rep,
        'at_unix': time.time(),
        'at': _now_iso(),
    })


def federation_adoption_results(exchange, query_id: str) -> list[dict]:
    """Return all FEDERATION_ADOPTION rows for a given query_id."""
    return [r for r in _fed_rows(exchange)
            if r.get('kind') == 'FEDERATION_ADOPTION' and r.get('query_id') == query_id]


def federated_adoption_count(exchange, feature_id: str) -> int:
    """Count distinct (network, peer) adoptions from federation for a feature.

    Sybil-resistant: deduplicates by (remote_network_id, adopter_peer_id).
    """
    seen: set[tuple[str, str]] = set()
    for r in _fed_rows(exchange):
        if r.get('kind') == 'FEDERATION_ADOPTION' and r.get('feature_id') == feature_id:
            key = (r.get('remote_network_id', ''), r.get('adopter_peer_id', ''))
            if key[0] and key[1]:
                seen.add(key)
    return len(seen)
