"""Asset Registry — earn-backed asset certificates with two-track reputation.

EARNED reputation  (soulbound):  PoQ/PoW contributions, cannot be bought or transferred.
                                  Signals: "this peer is a quality maker."

TRADE  reputation  (transferable): asset ownership + royalty earnings from usage.
                                   Signals: "this peer holds productive assets."

Both tracks are independently auditable. Owning a high-earning asset does NOT
raise earned reputation — the two are always displayed separately.

This module tracks off-chain asset ownership and earn accumulation.
On-chain anchoring is handled by chain_anchor.publish_asset_earning() (Phase 3.5).
"""
from __future__ import annotations

import time
from datetime import datetime, timezone

SCHEMA = 'urace-asset-registry-v1'

# Borrow tax rate: fraction of earn_units deducted from borrower on each usage.
# Must satisfy: borrow_cost + borrow_fee < executor_cost (P2P always cheaper).
# Prevents earn inflation via self-borrow or coordinated fake usage.
# 15% default: on a 1-unit earn, borrower pays 1 credit, owner earns 1 credit,
# but the 0.15-unit fee to treasury makes net self-borrow negative.
BORROW_TAX_RATE: float = 0.15


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _now() -> float:
    return time.time()


# ---------------------------------------------------------------------------
# Asset ownership
# ---------------------------------------------------------------------------

def register_asset(exchange, feature_id: str, creator_peer_id: str,
                   canonical_fingerprint: str | None = None,
                   nft_token_id: str | None = None) -> dict:
    """Register a new asset. Called once at feature creation.

    canonical_fingerprint: sha256 of the feature content (from APPLIED_AFTER_LOCAL_QUALIFICATION).
    If provided, checked against existing registrations for dupe prevention:
    if another peer already registered the same fingerprint, registration is blocked —
    the first broadcaster is the canonical owner (mirrors feature_creator_id() in credit_ledger).

    If the asset was already registered (idempotent), returns the existing record.
    """
    rows = _rows(exchange)
    existing = _ownership_row(rows, feature_id)
    if existing:
        return {'status': 'already_registered', 'feature_id': feature_id,
                'owner_peer_id': existing['owner_peer_id']}

    # Dupe check: same canonical_fingerprint already registered by someone else?
    if canonical_fingerprint:
        dupe = next(
            (r for r in rows
             if r.get('kind') == 'ASSET_REGISTERED'
             and r.get('canonical_fingerprint') == canonical_fingerprint
             and r.get('feature_id') != feature_id),
            None,
        )
        if dupe:
            return {
                'status': 'duplicate',
                'feature_id': feature_id,
                'canonical_fingerprint': canonical_fingerprint,
                'existing_feature_id': dupe['feature_id'],
                'existing_owner': dupe.get('owner_peer_id'),
                'detail': 'identical canonical_fingerprint already registered — first broadcaster owns this asset',
            }

    row = {
        'kind': 'ASSET_REGISTERED',
        'schema': SCHEMA,
        'feature_id': feature_id,
        'owner_peer_id': creator_peer_id,
        'canonical_fingerprint': canonical_fingerprint or '',
        'cumulative_earn_units': 0,
        'nft_token_id': nft_token_id,
        'at_unix': _now(),
        'at': _now_iso(),
    }
    exchange.append_audit_row(row)
    return {'status': 'registered', 'feature_id': feature_id, 'owner_peer_id': creator_peer_id}


def initiate_transfer(exchange, feature_id: str, from_peer_id: str,
                      to_peer_id: str, expires_in_seconds: float = 86400.0) -> dict:
    """Phase 1 of two-phase transfer: seller initiates, buyer must accept.

    Records ASSET_TRANSFER_PENDING. The transfer is NOT complete until
    accept_transfer() is called by to_peer_id within the expiry window.
    This prevents unilateral theft via a compromised node calling transfer directly.
    """
    rows = _rows(exchange)
    ownership = _ownership_row(rows, feature_id)
    if ownership is None:
        raise ValueError(f'Asset {feature_id!r} not registered.')
    current_owner = ownership['owner_peer_id']
    if current_owner != from_peer_id:
        raise ValueError(
            f'Asset {feature_id!r} is owned by {current_owner!r}, not {from_peer_id!r}.')
    if _has_pending_challenge(rows, feature_id):
        raise ValueError(
            f'Asset {feature_id!r} has a pending challenge — transfer blocked until resolved.')
    # Only one pending transfer at a time
    if _pending_transfer(rows, feature_id):
        raise ValueError(f'Asset {feature_id!r} already has a pending transfer offer.')

    t = _now()
    expires_at = t + expires_in_seconds
    exchange.append_audit_row({
        'kind': 'ASSET_TRANSFER_PENDING',
        'schema': SCHEMA,
        'feature_id': feature_id,
        'from_peer_id': from_peer_id,
        'to_peer_id': to_peer_id,
        'expires_at_unix': expires_at,
        'at_unix': t,
        'at': _now_iso(),
    })
    return {
        'status': 'pending',
        'feature_id': feature_id,
        'from_peer_id': from_peer_id,
        'to_peer_id': to_peer_id,
        'expires_at_unix': expires_at,
        'detail': f'Buyer ({to_peer_id}) must call accept_transfer() within {expires_in_seconds/3600:.0f}h',
    }


def accept_transfer(exchange, feature_id: str, accepting_peer_id: str) -> dict:
    """Phase 2 of two-phase transfer: buyer accepts the pending offer.

    Only the designated to_peer_id can accept. Expired offers are rejected.
    Records ASSET_TRANSFERRED — ownership is now final.
    Earned reputation of either party is unaffected.
    """
    rows = _rows(exchange)
    pending = _pending_transfer(rows, feature_id)
    if pending is None:
        raise ValueError(f'No pending transfer for asset {feature_id!r}.')
    if pending['to_peer_id'] != accepting_peer_id:
        raise ValueError(
            f'Transfer for {feature_id!r} is designated to {pending["to_peer_id"]!r}, '
            f'not {accepting_peer_id!r}.')
    if _now() > float(pending.get('expires_at_unix', 0)):
        raise ValueError(f'Transfer offer for {feature_id!r} has expired.')

    cumulative = _cumulative_earn(rows, feature_id)
    t = _now()
    exchange.append_audit_row({
        'kind': 'ASSET_TRANSFERRED',
        'schema': SCHEMA,
        'feature_id': feature_id,
        'from_peer_id': pending['from_peer_id'],
        'to_peer_id': accepting_peer_id,
        'cumulative_earn_at_transfer': cumulative,
        'at_unix': t,
        'at': _now_iso(),
    })
    return {
        'status': 'transferred',
        'feature_id': feature_id,
        'from_peer_id': pending['from_peer_id'],
        'to_peer_id': accepting_peer_id,
        'cumulative_earn_at_transfer': cumulative,
    }


def cancel_transfer(exchange, feature_id: str, cancelling_peer_id: str) -> dict:
    """Cancel a pending transfer. Only the initiating seller can cancel."""
    rows = _rows(exchange)
    pending = _pending_transfer(rows, feature_id)
    if pending is None:
        raise ValueError(f'No pending transfer for asset {feature_id!r}.')
    if pending['from_peer_id'] != cancelling_peer_id:
        raise ValueError(f'Only the seller ({pending["from_peer_id"]!r}) can cancel this transfer.')
    t = _now()
    exchange.append_audit_row({
        'kind': 'ASSET_TRANSFER_CANCELLED',
        'schema': SCHEMA,
        'feature_id': feature_id,
        'from_peer_id': pending['from_peer_id'],
        'to_peer_id': pending['to_peer_id'],
        'at_unix': t,
        'at': _now_iso(),
    })
    return {'status': 'cancelled', 'feature_id': feature_id}


# ---------------------------------------------------------------------------
# Earning
# ---------------------------------------------------------------------------

def record_usage_earn(exchange, feature_id: str, usage_peer_id: str,
                      earn_units: int,
                      borrow_tax_rate: float | None = None) -> dict:
    """Record a usage event — owner earns royalty, borrower pays a small tax.

    Self-borrow (usage_peer_id == owner_peer_id) is blocked: earns nothing,
    prevents earn inflation without network participation cost.

    earn_units: required — must be the actual borrow_cost from the transaction
    (proportional to ceiling tier × executor_reference). No fixed default.

    Borrow tax: a fraction of earn_units is deducted from the borrower's credits
    and sent to treasury. This ensures:
      borrow_cost + borrow_tax < executor_cost  (P2P always cheaper)
      self-borrow net = earn_units - borrow_tax < 0  (unprofitable to self-inflate)

    borrow_tax_rate defaults to BORROW_TAX_RATE (0.15).
    """
    rows = _rows(exchange)
    ownership = _ownership_row(rows, feature_id)
    if ownership is None:
        return {'status': 'not_registered', 'feature_id': feature_id}

    owner = ownership['owner_peer_id']

    # Self-borrow block: owner cannot inflate their own asset
    if usage_peer_id == owner:
        return {
            'status': 'self_borrow_blocked',
            'feature_id': feature_id,
            'owner_peer_id': owner,
            'detail': 'owner cannot earn royalty from self-usage — prevents inflation',
        }

    units = earn_units
    tax_rate = borrow_tax_rate if borrow_tax_rate is not None else BORROW_TAX_RATE
    tax_units = max(1, int(units * tax_rate))  # at least 1 unit tax per borrow

    cumulative_before = _cumulative_earn(rows, feature_id)
    cumulative_after = cumulative_before + units
    t = _now()

    exchange.append_audit_row({
        'kind': 'ASSET_EARN',
        'schema': SCHEMA,
        'feature_id': feature_id,
        'owner_peer_id': owner,
        'usage_peer_id': usage_peer_id,
        'earn_units': units,
        'borrow_tax_units': tax_units,
        'cumulative_earn_units': cumulative_after,
        'at_unix': t,
        'at': _now_iso(),
    })
    # Royalty credit for owner (trade rep track)
    exchange.append_audit_row({
        'kind': 'CREDIT_DELTA',
        'schema': SCHEMA,
        'direction': 'asset_royalty',
        'rep_source': 'trade',
        'peer': owner,
        'amount_units': units,
        'feature_id': feature_id,
        'at_unix': t,
        'at': _now_iso(),
    })
    # Borrow tax debit from borrower (anti-inflation fee)
    exchange.append_audit_row({
        'kind': 'CREDIT_DELTA',
        'schema': SCHEMA,
        'direction': 'borrow_tax',
        'peer': usage_peer_id,
        'amount_units': -tax_units,
        'feature_id': feature_id,
        'reason': 'asset_borrow_tax',
        'at_unix': t,
        'at': _now_iso(),
    })
    return {
        'status': 'earned',
        'feature_id': feature_id,
        'owner_peer_id': owner,
        'earn_units': units,
        'borrow_tax_units': tax_units,
        'cumulative_earn_units': cumulative_after,
    }


# ---------------------------------------------------------------------------
# Inspection
# ---------------------------------------------------------------------------

def asset_summary(rows: list[dict], feature_id: str) -> dict | None:
    """Return a summary dict for a single asset, or None if not registered."""
    ownership = _ownership_row(rows, feature_id)
    if ownership is None:
        return None
    earn_rows = [r for r in rows if r.get('kind') == 'ASSET_EARN'
                 and r.get('feature_id') == feature_id]
    transfer_rows = [r for r in rows if r.get('kind') == 'ASSET_TRANSFERRED'
                     and r.get('feature_id') == feature_id]
    cumulative = _cumulative_earn(rows, feature_id)
    last_earn = max((r.get('at_unix', 0) for r in earn_rows), default=None)
    return {
        'feature_id': feature_id,
        'owner_peer_id': ownership['owner_peer_id'],
        'cumulative_earn_units': cumulative,
        'total_uses': len(earn_rows),
        'transfer_count': len(transfer_rows),
        'last_earn_at': last_earn,
        'registered_at': ownership.get('at_unix'),
        'nft_token_id': ownership.get('nft_token_id'),
    }


def peer_asset_portfolio(rows: list[dict], peer_id: str) -> list[dict]:
    """All assets currently owned by peer_id with earn summaries."""
    all_feature_ids = {r['feature_id'] for r in rows
                       if r.get('kind') == 'ASSET_REGISTERED' and 'feature_id' in r}
    result = []
    for fid in all_feature_ids:
        ownership = _ownership_row(rows, fid)
        if ownership and ownership['owner_peer_id'] == peer_id:
            summary = asset_summary(rows, fid)
            if summary:
                result.append(summary)
    return sorted(result, key=lambda s: s['cumulative_earn_units'], reverse=True)


def earn_rate(rows: list[dict], feature_id: str, window_seconds: float = 86400.0) -> float:
    """Average earn units per second over the given window (default: 24h).

    This is the auditable figure that determines asset market value.
    """
    cutoff = _now() - window_seconds
    earn_rows = [r for r in rows if r.get('kind') == 'ASSET_EARN'
                 and r.get('feature_id') == feature_id
                 and float(r.get('at_unix', 0)) >= cutoff]
    total = sum(r.get('earn_units', 0) for r in earn_rows)
    return total / window_seconds if window_seconds > 0 else 0.0


# ---------------------------------------------------------------------------
# Reputation track display
# ---------------------------------------------------------------------------

def reputation_summary(rows: list[dict], peer_id: str) -> dict:
    """Return both reputation tracks for a peer.

    earned  — PoQ/PoW score, non-transferable, reflects contribution quality.
    trade   — total asset earn units, reflects economic participation.

    These are always shown separately and never aggregated.
    """
    # Trade reputation: sum of all ASSET_EARN rows where current owner == peer_id
    portfolio = peer_asset_portfolio(rows, peer_id)
    trade_units = sum(a['cumulative_earn_units'] for a in portfolio)
    assets_held = len(portfolio)

    # Earned reputation: delegate to PoQ scoring (not computed here — read from state)
    return {
        'peer_id': peer_id,
        'earned': {
            'note': 'see state.reputation_score — derived from PoQ/PoW, non-transferable'
        },
        'trade': {
            'cumulative_earn_units': trade_units,
            'assets_held': assets_held,
            'portfolio': portfolio,
        },
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _rows(exchange) -> list[dict]:
    try:
        return exchange.audit_rows()
    except Exception:
        return []


def _ownership_row(rows: list[dict], feature_id: str) -> dict | None:
    """Current owner: last ASSET_REGISTERED or ASSET_TRANSFERRED row for feature_id."""
    candidates = [
        r for r in rows
        if r.get('feature_id') == feature_id
        and r.get('kind') in ('ASSET_REGISTERED', 'ASSET_TRANSFERRED')
    ]
    if not candidates:
        return None
    latest = max(candidates, key=lambda r: float(r.get('at_unix', 0)))
    if latest['kind'] == 'ASSET_TRANSFERRED':
        return {'owner_peer_id': latest['to_peer_id'], 'at_unix': latest['at_unix']}
    return latest


def _cumulative_earn(rows: list[dict], feature_id: str) -> int:
    earn_rows = [r for r in rows if r.get('kind') == 'ASSET_EARN'
                 and r.get('feature_id') == feature_id]
    return sum(r.get('earn_units', 0) for r in earn_rows)


def _pending_transfer(rows: list[dict], feature_id: str) -> dict | None:
    """Return active ASSET_TRANSFER_PENDING row, or None if none/expired/completed."""
    pending_rows = [
        r for r in rows
        if r.get('kind') == 'ASSET_TRANSFER_PENDING'
        and r.get('feature_id') == feature_id
    ]
    if not pending_rows:
        return None
    latest = max(pending_rows, key=lambda r: float(r.get('at_unix', 0)))
    # Check if it was subsequently completed or cancelled
    after_ts = float(latest.get('at_unix', 0))
    completed = any(
        r for r in rows
        if r.get('feature_id') == feature_id
        and r.get('kind') in ('ASSET_TRANSFERRED', 'ASSET_TRANSFER_CANCELLED')
        and float(r.get('at_unix', 0)) > after_ts
    )
    if completed:
        return None
    # Check expiry
    if _now() > float(latest.get('expires_at_unix', 0)):
        return None
    return latest


def _has_pending_challenge(rows: list[dict], feature_id: str) -> bool:
    return any(
        r.get('kind') == 'PROVENANCE_CHALLENGE'
        and r.get('feature_id') == feature_id
        and r.get('status') == 'pending'
        for r in rows
    )
