"""Feature equity ownership and trading.

Equity is measured in basis points (bp): 10_000 bp = 100.00%.
Ownership is derived entirely from append-only audit rows — never stored
in mutable state.

Audit row kinds:
  EQUITY_GRANT  — initial 100% grant to original creator at qualification
  EQUITY_SELL   — partial or full sale from seller to buyer

Equity model:
  - Original creator starts at 10_000 bp (100%)
  - Can sell any tranche ≥ EQUITY_MIN_TRADE_BP (1%)
  - Can sell all 10_000 bp (full exit — zero future mint rights)
  - Buyer receives proportional future mint and distribution fees
  - Original creator record is immutable (attribution, not ownership)
  - Anti-monopoly: non-original holder cap at EQUITY_NON_CREATOR_MAX_BP (80%)
    unless the original creator explicitly transfers more in a single transaction

Credit semantics:
  - equity purchases: buyer pays REP_SOURCE_TRADE credits (market_rep only)
  - never counts toward earned_rep / governance / arbitration weight

Singularity design note:
  Features are the atomic unit of network value. Equity makes every feature
  a tradeable asset — price discovery emerges from market activity, quality
  signals flow back through distribution fees, and network intelligence
  compounds through adoption-driven mint splits.
"""
from __future__ import annotations
import time
import weakref

# Per-exchange holdings cache: exchange → {(feature_id, row_count): holdings_dict}
# WeakKeyDictionary ensures stale entries are purged when an exchange object is GC'd,
# preventing id() reuse collisions across test instances.
_HOLDINGS_CACHE: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()

SCHEMA = 'urace-feature-equity-v1'

EQUITY_TOTAL_BP          = 10_000   # 100.00%
EQUITY_MIN_TRADE_BP      = 100      # minimum 1% tranche
EQUITY_NON_CREATOR_MAX_BP = 8_000   # 80% — non-original anti-monopoly cap


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _equity_rows(exchange, feature_id: str) -> list[dict]:
    try:
        rows = exchange.audit_rows()
    except Exception:
        return []
    return [r for r in rows
            if r.get('kind') in ('EQUITY_GRANT', 'EQUITY_SELL')
            and r.get('feature_id') == feature_id]


def grant_equity(exchange, feature_id: str, creator_id: str) -> None:
    """Grant 100% equity to the original creator at feature qualification.

    Idempotent: does nothing if an EQUITY_GRANT already exists for this feature.
    Should be called exactly once when a feature passes local qualification.
    """
    existing = [r for r in _equity_rows(exchange, feature_id) if r.get('kind') == 'EQUITY_GRANT']
    if existing:
        return
    exchange.append_audit_row({
        'kind': 'EQUITY_GRANT',
        'feature_id': feature_id,
        'peer_id': creator_id,
        'basis_points': EQUITY_TOTAL_BP,
        'at_unix': time.time(),
        'at': _now_iso(),
    })


def equity_holdings(feature_id: str, exchange) -> dict[str, int]:
    """Derive current {peer_id: basis_points} from audit row replay.

    Processes EQUITY_GRANT and EQUITY_SELL in chronological order.
    Entries reaching 0 bp are removed. Result is memoized by (feature_id, row_count).
    """
    eq_rows = _equity_rows(exchange, feature_id)
    ex_cache = _HOLDINGS_CACHE.setdefault(exchange, {})
    inner_key = (feature_id, len(eq_rows))
    cached = ex_cache.get(inner_key)
    if cached is not None:
        return cached

    rows = sorted(eq_rows, key=lambda r: float(r.get('at_unix', 0)))
    holdings: dict[str, int] = {}
    for r in rows:
        if r.get('kind') == 'EQUITY_GRANT':
            pid = r.get('peer_id', '')
            bp = int(r.get('basis_points', EQUITY_TOTAL_BP))
            if pid:
                holdings[pid] = holdings.get(pid, 0) + bp
        elif r.get('kind') == 'EQUITY_SELL':
            seller = r.get('seller_id', '')
            buyer  = r.get('buyer_id', '')
            bp     = int(r.get('basis_points', 0))
            if seller and buyer and bp > 0:
                holdings[seller] = holdings.get(seller, 0) - bp
                holdings[buyer]  = holdings.get(buyer, 0) + bp
                if holdings.get(seller, 0) <= 0:
                    holdings.pop(seller, None)
    ex_cache[inner_key] = holdings
    return holdings


def original_creator(feature_id: str, exchange) -> str | None:
    """Return the peer_id of the first EQUITY_GRANT for this feature.

    Immutable attribution: even if the creator sells all equity, this
    record is permanent for provenance and reputation history.
    """
    grants = [r for r in _equity_rows(exchange, feature_id) if r.get('kind') == 'EQUITY_GRANT']
    if not grants:
        return None
    grants.sort(key=lambda r: float(r.get('at_unix', 0)))
    return grants[0].get('peer_id')


def sell_equity(
    exchange,
    root,
    feature_id: str,
    seller_id: str,
    buyer_id: str,
    basis_points: int,
    price_units: int = 0,
) -> None:
    """Sell basis_points of feature equity from seller to buyer.

    basis_points: amount to sell (100 = 1%, 10000 = 100%)
    price_units:  credit units buyer pays seller. 0 = gift / internal transfer.

    Rules:
    - Min tranche: EQUITY_MIN_TRADE_BP
    - Seller must hold >= basis_points
    - Non-original buyer cannot exceed EQUITY_NON_CREATOR_MAX_BP after purchase
    - Original creator selling > 80% to a single buyer is permitted (intentional exit)

    Credit transfer: buyer spends REP_SOURCE_TRADE credits; seller earns REP_SOURCE_TRADE.
    Equity purchase credits never contribute to earned_rep.
    """
    from . import credit_ledger as _cl
    if basis_points < EQUITY_MIN_TRADE_BP:
        raise ValueError(f'Minimum trade is {EQUITY_MIN_TRADE_BP} bp (1%), got {basis_points}')

    holdings = equity_holdings(feature_id, exchange)
    seller_holds = holdings.get(seller_id, 0)
    if seller_holds < basis_points:
        raise ValueError(
            f'{seller_id!r} holds {seller_holds} bp, cannot sell {basis_points} bp'
        )

    orig = original_creator(feature_id, exchange)
    buyer_holds = holdings.get(buyer_id, 0)
    # Anti-monopoly: non-original buyer cannot exceed EQUITY_NON_CREATOR_MAX_BP.
    # Single exception: original creator selling their ENTIRE remaining stake in one
    # transaction (clean exit) — intentional full transfer is allowed to any buyer.
    is_full_exit = (seller_id == orig and seller_holds == basis_points)
    if buyer_id != orig and not is_full_exit and buyer_holds + basis_points > EQUITY_NON_CREATOR_MAX_BP:
        raise ValueError(
            f'Anti-monopoly: {buyer_id!r} would hold {buyer_holds + basis_points} bp '
            f'> max {EQUITY_NON_CREATOR_MAX_BP} bp for non-original holders. '
            f'Only a full-exit (entire remaining stake) bypasses this limit.'
        )

    if price_units > 0:
        _cl.spend_units(root, buyer_id, price_units,
                        f'equity-purchase:{feature_id}:{seller_id}→{buyer_id}')
        _cl.earn_units(root, seller_id, price_units,
                       f'equity-sale:{feature_id}:{seller_id}→{buyer_id}',
                       rep_source=_cl.REP_SOURCE_TRADE)

    exchange.append_audit_row({
        'kind': 'EQUITY_SELL',
        'feature_id': feature_id,
        'seller_id': seller_id,
        'buyer_id': buyer_id,
        'basis_points': basis_points,
        'price_units': price_units,
        'at_unix': time.time(),
        'at': _now_iso(),
    })


def _proportional_split(holdings: dict[str, int], amount: int) -> dict[str, int]:
    """Split amount proportionally by bp holdings. Last entry absorbs remainder."""
    if not holdings or amount <= 0:
        return {}
    total_bp = sum(holdings.values())
    if total_bp == 0:
        return {}
    result: dict[str, int] = {}
    distributed = 0
    items = list(holdings.items())
    for i, (pid, bp) in enumerate(items):
        if i == len(items) - 1:
            result[pid] = amount - distributed
        else:
            share = int(amount * bp / total_bp)
            result[pid] = share
            distributed += share
    # Drop zero-unit entries (rounding may produce 0 for tiny holdings)
    return {k: v for k, v in result.items() if v > 0}


def mint_equity_split(feature_id: str, mint_amount: int, exchange) -> dict[str, int]:
    """Distribute mint_amount proportionally to current equity holders.

    Falls back to {original_creator: mint_amount} when no equity rows exist
    (backward-compatible with features created before equity system).
    """
    holdings = equity_holdings(feature_id, exchange)
    if not holdings:
        creator = original_creator(feature_id, exchange)
        if creator:
            return {creator: mint_amount}
        return {}
    return _proportional_split(holdings, mint_amount)


def distribution_fee_equity_split(feature_id: str, fee_amount: int, exchange) -> dict[str, int]:
    """Distribute distribution fee proportionally to current equity holders.

    Equity holders receive distribution fees in proportion to their ownership.
    This incentivises holding equity in high-adoption features.
    """
    return mint_equity_split(feature_id, fee_amount, exchange)
