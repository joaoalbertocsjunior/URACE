"""Cross-peer whole-ledger inventory and consistency verification.

Checks that known peers agree on each other's chain tips.
Emits LEDGER_INVENTORY_RECORD for each peer checked.
"""

from . import peer_exchange
from . import ledger_sync


def full_inventory(exchange, known_peers: list) -> list:
    """Fetch the chain tip from each known peer and compare against local view.

    Emits LEDGER_INVENTORY_RECORD for each peer.
    Returns list of inventory record dicts.
    """
    records = []
    for peer_id in known_peers:
        status = 'UNREACHABLE'
        their_head = None
        match = False

        try:
            resp = peer_exchange.request(exchange, peer_id, 'exchange.checkpoint', {})
            their_head = resp.get('local_head_sha') if isinstance(resp, dict) else None

            # Fetch peer tail to compare (best-effort)
            peer_rows = None
            try:
                tail_resp = peer_exchange.request(exchange, peer_id, 'exchange.tail', {})
                if isinstance(tail_resp, dict):
                    peer_rows = tail_resp.get('rows')
            except Exception:
                pass

            checkpoint = ledger_sync.exchange_checkpoint(exchange, peer_id, peer_rows=peer_rows)
            local_head = checkpoint.get('local_head_sha', '0' * 64)

            if their_head is not None:
                match = (local_head == their_head) or checkpoint.get('match', False)
                status = 'MATCH' if match else 'MISMATCH'
            else:
                status = 'MISMATCH'

        except Exception:
            status = 'UNREACHABLE'

        record = {
            'peer_id': peer_id,
            'their_head': their_head,
            'match': match,
            'status': status,
        }

        try:
            exchange.event('LEDGER_INVENTORY_RECORD', **record)
        except Exception:
            pass

        records.append(record)

    return records


def inventory_summary(exchange) -> dict:
    """Scan audit rows for LEDGER_INVENTORY_RECORD events and summarise.

    Returns {'total_checked': int, 'matches': int, 'mismatches': int,
             'unreachable': int, 'match_rate': float}.
    """
    rows = []
    try:
        rows = exchange.audit_rows()
    except Exception:
        pass

    total = 0
    matches = 0
    mismatches = 0
    unreachable = 0

    for row in rows:
        if row.get('kind') != 'LEDGER_INVENTORY_RECORD':
            continue
        total += 1
        s = row.get('status', '')
        if s == 'MATCH':
            matches += 1
        elif s == 'MISMATCH':
            mismatches += 1
        else:
            unreachable += 1

    match_rate = matches / total if total > 0 else 0.0

    return {
        'total_checked': total,
        'matches': matches,
        'mismatches': mismatches,
        'unreachable': unreachable,
        'match_rate': match_rate,
    }
