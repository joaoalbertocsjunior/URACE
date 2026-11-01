"""Audit-derived token ledger for peer artifact exchange.

Balances are computed from the tamper-evident exchange audit log.
No separate mutable state file — the audit chain IS the ledger.

  Earn (improvement):  APPLIED_AFTER_LOCAL_QUALIFICATION events (score_delta → sender/creator)
  Earn (propagation):  FEATURE_BORROWED events (BORROW_CREDIT_PER_PEER → creator_peer_id)
  Spend:               RECEIVE_RESERVED events (1 token charged per incoming bundle)
  Bootstrap:           baseline_grant free receives per peer (default 3)

Propagation earn model: a feature only earns its creator tokens when other nodes
actually borrow it with positive outcomes. Gibberish features can't pass real trials
and therefore can't get receipt_verified=True borrows.

Security: balances cannot be forged by editing a file — they are derived from
the hash-chained, post-quantum-signed audit log. Any tampering raises ValueError
on the next audit_rows() call.
"""
from __future__ import annotations

from typing import Any

SCHEMA = 'urace-token-ledger-v1'
_DEFAULT_GRANT = 3        # matches tokenomics.baseline_grant_requests
_BORROW_CREDIT = 1.0      # tokens earned by creator per unique borrower node

# 8-decimal precision constants (satoshi model) — mirrors credit_ledger
DECIMALS = 8
UNIT     = 10 ** DECIMALS   # 1.00000000 token = 100_000_000 base units


def _grant(exchange) -> int:
    return exchange.load().get('token_baseline_grant', _DEFAULT_GRANT)


def balance(exchange, peer_id: str) -> float:
    """Net token balance derived from the tamper-evident audit log.

    balance = baseline_grant
              + sum(score_delta for APPLIED events where peer == peer_id)
              + count(FEATURE_BORROWED events where creator_peer_id == peer_id)
              - count(RECEIVE_RESERVED events where peer == peer_id)

    With token_settlement=True, only receipt_verified=True events earn tokens.
    Raises ValueError if the audit chain has been tampered with.
    """
    grant = _grant(exchange)
    p = exchange.load()
    settlement = p.get('token_settlement', False)
    rows = exchange.audit_rows()
    earned_improvement = sum(
        float(r.get('score_delta', 0.0))
        for r in rows
        if r.get('kind') == 'APPLIED_AFTER_LOCAL_QUALIFICATION'
        and r.get('peer') == peer_id
        and (not settlement or r.get('receipt_verified', False))
    )
    # Count distinct borrower nodes — one credit per unique peer that borrowed the feature.
    borrow_peers = {
        r['borrower_peer_id']
        for r in rows
        if r.get('kind') == 'FEATURE_BORROWED'
        and r.get('creator_peer_id') == peer_id
        and r.get('borrower_peer_id')
        and (not settlement or r.get('receipt_verified', False))
    }
    earned_propagation = len(borrow_peers) * _BORROW_CREDIT
    spent = sum(
        1.0
        for r in rows
        if r.get('kind') == 'RECEIVE_RESERVED' and r.get('peer') == peer_id
    )
    return round(grant + earned_improvement + earned_propagation - spent, 4)


def can_receive(exchange, peer_id: str, cost: float = 1.0) -> bool:
    return balance(exchange, peer_id) >= cost


def check_can_receive(exchange, peer_id: str, cost: float = 1.0) -> None:
    """Raise ValueError if insufficient balance. Call while exchange.lock() is held.

    The actual spend record IS the RECEIVE_RESERVED event about to be written —
    no separate deduction needed.
    """
    bal = balance(exchange, peer_id)
    if bal < cost:
        raise ValueError(
            f'Insufficient token balance for peer {peer_id[:12]}… '
            f'(balance={bal:.2f}, cost={cost:.2f}); '
            f'earn tokens by qualifying received improvements first'
        )


def summary(exchange) -> dict[str, Any]:
    """Return per-peer token state derived from the audit log."""
    grant = _grant(exchange)
    p = exchange.load()
    settlement = p.get('token_settlement', False)
    rows = exchange.audit_rows()
    peers: dict[str, dict] = {}

    def _peer(pid: str) -> dict:
        if pid not in peers:
            peers[pid] = {'earned_improvement': 0.0, 'earned_propagation': set(), 'spent': 0.0}
        return peers[pid]

    for r in rows:
        kind = r.get('kind', '')
        if kind == 'APPLIED_AFTER_LOCAL_QUALIFICATION':
            peer = r.get('peer', '')
            if peer and (not settlement or r.get('receipt_verified', False)):
                _peer(peer)['earned_improvement'] += float(r.get('score_delta', 0.0))
        elif kind == 'FEATURE_BORROWED':
            creator = r.get('creator_peer_id', '')
            borrower = r.get('borrower_peer_id', '')
            if creator and borrower and (not settlement or r.get('receipt_verified', False)):
                _peer(creator)['earned_propagation'].add(borrower)
        elif kind == 'RECEIVE_RESERVED':
            peer = r.get('peer', '')
            if peer:
                _peer(peer)['spent'] += 1.0

    result_peers = {}
    for pid, d in peers.items():
        imp = round(d['earned_improvement'], 4)
        prop = round(len(d['earned_propagation']) * _BORROW_CREDIT, 4)
        spent = round(d['spent'], 4)
        result_peers[pid] = {
            'earned_improvement': imp,
            'earned_propagation': prop,
            'earned': round(imp + prop, 4),
            'spent': spent,
            'balance': round(grant + imp + prop - spent, 4),
        }

    return {
        'schema': SCHEMA,
        'baseline_grant': grant,
        'settlement': 'audit-derived',
        'mainnet_settlement_enabled': False,
        'tamper_evident': True,
        'peers': result_peers,
    }
