"""Audit-derived token ledger for peer artifact exchange.

Balances are computed from the tamper-evident exchange audit log.
No separate mutable state file — the audit chain IS the ledger.

  Earn (improvement):  APPLIED_AFTER_LOCAL_QUALIFICATION events (score_delta → sender/creator)
  Earn (propagation):  FEATURE_BORROWED events (BORROW_CREDIT_PER_PEER → creator_peer_id)
  Spend:               RECEIVE_RESERVED events (1 token charged per incoming bundle)
  Bootstrap:           baseline_grant free receives per peer (default 3)
  Explicit deltas:     CREDIT_DELTA events (amount_units, positive=earn, negative=spend)
                       Used for: purchase transactions, escrow refunds/clawbacks, custody rewards

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

    balance = baseline_grant (locked until first quality gate pass)
              + sum(score_delta for APPLIED events where peer == peer_id)
              + count(FEATURE_BORROWED events where creator_peer_id == peer_id)
              - count(RECEIVE_RESERVED events where peer == peer_id)

    With token_settlement=True, only receipt_verified=True events earn tokens.
    Bootstrap grant locked until first quality pass prevents Sybil token farming.
    Raises ValueError if the audit chain has been tampered with.
    """
    p = exchange.load()
    settlement = p.get('token_settlement', False)
    rows = exchange.audit_rows()
    # Bootstrap grant unlocks on first quality gate pass — Sybil resistance
    _has_quality_pass = any(
        r.get('kind') == 'APPLIED_AFTER_LOCAL_QUALIFICATION' and r.get('peer') == peer_id
        for r in rows
    )
    grant = _grant(exchange) if _has_quality_pass else 0
    earned_improvement = sum(
        float(r.get('score_delta', 0.0))
        for r in rows
        if r.get('kind') == 'APPLIED_AFTER_LOCAL_QUALIFICATION'
        and r.get('peer') == peer_id
        and (not settlement or r.get('receipt_verified', False))
    )
    # Count adoption earns: new rows carry precomputed credit_units (network-size-aware,
    # supply-pressure-adjusted, computed at mint time). Old rows fall back to flat _BORROW_CREDIT.
    # Same-peer repeat borrows stored with credit_units=0 — no additional earn.
    _old_borrow_peers: set[str] = set()
    _new_earned_units: int = 0
    for r in rows:
        if r.get('kind') != 'FEATURE_BORROWED':
            continue
        if r.get('creator_peer_id') != peer_id:
            continue
        borrower = r.get('borrower_peer_id', '')
        if not borrower:
            continue
        if settlement and not r.get('receipt_verified', False):
            continue
        if 'credit_units' in r:
            _new_earned_units += int(r['credit_units'])
        else:
            _old_borrow_peers.add(borrower)
    earned_propagation = (_new_earned_units / UNIT) + len(_old_borrow_peers) * _BORROW_CREDIT
    spent = sum(
        1.0
        for r in rows
        if r.get('kind') == 'RECEIVE_RESERVED' and r.get('peer') == peer_id
    )
    # Explicit CREDIT_DELTA adjustments: purchase transactions, escrow operations, custody rewards.
    # amount_units is in tokens (integer); positive=earn, negative=spend.
    credit_delta = sum(
        float(r.get('amount_units', 0))
        for r in rows
        if r.get('kind') == 'CREDIT_DELTA' and r.get('peer') == peer_id
    )
    return round(grant + earned_improvement + earned_propagation - spent + credit_delta, 4)


def _trial_borrows_remaining(exchange, peer_id: str) -> int:
    """New peers get trial_borrow_allowance free borrows before first quality gate pass.

    Bootstrap the cold-start: peer can borrow once to trigger their first improvement
    cycle, which unlocks the full baseline grant. After their first quality pass,
    trial allowance is exhausted and normal balance rules apply.
    """
    p = exchange.load()
    allowance = int(p.get('trial_borrow_allowance', 1))
    if allowance <= 0:
        return 0
    rows = exchange.audit_rows()
    has_quality_pass = any(
        r.get('kind') == 'APPLIED_AFTER_LOCAL_QUALIFICATION' and r.get('peer') == peer_id
        for r in rows
    )
    if has_quality_pass:
        return 0
    borrows_used = sum(1 for r in rows if r.get('kind') == 'RECEIVE_RESERVED' and r.get('peer') == peer_id)
    return max(0, allowance - borrows_used)


def can_receive(exchange, peer_id: str, cost: float = 1.0) -> bool:
    if _trial_borrows_remaining(exchange, peer_id) > 0:
        return True
    return balance(exchange, peer_id) >= cost


def check_can_receive(exchange, peer_id: str, cost: float = 1.0) -> None:
    """Raise ValueError if insufficient balance. Call while exchange.lock() is held.

    The actual spend record IS the RECEIVE_RESERVED event about to be written —
    no separate deduction needed.
    New peers with remaining trial_borrow_allowance are exempt from balance checks.
    """
    if _trial_borrows_remaining(exchange, peer_id) > 0:
        return
    bal = balance(exchange, peer_id)
    if bal < cost:
        raise ValueError(
            f'Insufficient token balance for peer {peer_id[:12]}… '
            f'(balance={bal:.2f}, cost={cost:.2f}); '
            f'earn tokens by qualifying received improvements first'
        )


def apply_token_decay(exchange, peer_id: str, decay_rate: float = 0.01) -> float:
    """Apply 1% epoch decay to unused balance above BASE_CAP_UNITS.

    Emits CREDIT_DELTA(direction='decay') audit row. Returns decay amount in tokens.
    Cooldown: once per 24h per peer. Only applies when balance > cap.
    Anti-cartel: prevents quality-hub hoarding without reducing active-earner rewards.
    """
    import time as _t, datetime as _dt
    p = exchange.load()
    cap = float(p.get('base_cap_units', 50))
    bal = balance(exchange, peer_id)
    if bal <= cap:
        return 0.0
    rows = exchange.audit_rows()
    last_decay = max(
        (float(r.get('at_unix', 0)) for r in rows
         if r.get('kind') == 'CREDIT_DELTA'
         and r.get('direction') == 'decay'
         and r.get('peer') == peer_id),
        default=0.0,
    )
    if _t.time() - last_decay < 86400:
        return 0.0
    excess = bal - cap
    decay_amount = round(excess * decay_rate, 4)
    if decay_amount <= 0:
        return 0.0
    exchange.append_audit_row({
        'kind': 'CREDIT_DELTA', 'direction': 'decay', 'peer': peer_id,
        'amount_units': -int(decay_amount * UNIT),
        'score_delta': -decay_amount,
        'reason': 'epoch_decay_above_cap',
        'balance_before_tokens': bal, 'cap_tokens': cap,
        'at_unix': _t.time(),
        'at': _dt.datetime.now(_dt.timezone.utc).isoformat(),
    })
    return decay_amount


def summary(exchange) -> dict[str, Any]:
    """Return per-peer token state derived from the audit log."""
    grant = _grant(exchange)
    p = exchange.load()
    settlement = p.get('token_settlement', False)
    rows = exchange.audit_rows()
    peers: dict[str, dict] = {}

    def _peer(pid: str) -> dict:
        if pid not in peers:
            peers[pid] = {'earned_improvement': 0.0, 'earned_propagation': set(), 'earned_propagation_units': 0, 'spent': 0.0}
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
                if 'credit_units' in r:
                    _peer(creator).setdefault('earned_propagation_units', 0)
                    _peer(creator)['earned_propagation_units'] += int(r['credit_units'])
                else:
                    _peer(creator)['earned_propagation'].add(borrower)
        elif kind == 'RECEIVE_RESERVED':
            peer = r.get('peer', '')
            if peer:
                _peer(peer)['spent'] += 1.0

    result_peers = {}
    for pid, d in peers.items():
        imp = round(d['earned_improvement'], 4)
        prop = round(
            d.get('earned_propagation_units', 0) / UNIT
            + len(d['earned_propagation']) * _BORROW_CREDIT,
            4,
        )
        spent = round(d['spent'], 4)
        result_peers[pid] = {
            'earned_improvement': imp,
            'earned_propagation': prop,
            'earned': round(imp + prop, 4),
            'spent': spent,
            'balance': round(grant + imp + prop - spent, 4),
        }

    trial_allowance = int(p.get('trial_borrow_allowance', 1))
    return {
        'schema': SCHEMA,
        'baseline_grant': grant,
        'trial_borrow_allowance': trial_allowance,
        'settlement': 'audit-derived',
        'mainnet_settlement_enabled': False,
        'tamper_evident': True,
        'peers': result_peers,
    }
