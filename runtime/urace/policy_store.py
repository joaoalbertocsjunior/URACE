"""Read-only policy store for one P2P exchange directory.

PolicyStore owns the policy.json read path and the two pure-logic methods
(permitted, budget) that derive answers from policy + audit rows.

Write operations (configure, peer, block, feature, rule …) remain on Exchange
because they need both the file lock and audit-chain writes.  Exchange.load()
delegates here, so callers that only need to read policy can depend on
PolicyStore without importing the full Exchange class.

Usage::

    from .policy_store import PolicyStore

    store = PolicyStore(exchange_root)
    policy = store.load()
    if store.permitted(policy, peer_id, feature_id, 'receive'):
        ...
"""
from __future__ import annotations

import json
from pathlib import Path

SCHEMA = 'urace-exchange-v2'
PROTOCOL_VERSION = 2

_DEFAULT_POLICY: dict = {
    'schema': SCHEMA,
    'enabled': True, 'network': True, 'advertise': False,
    'auto_select': True, 'auto_relay': False, 'token_settlement': False,
    'auto_trust_first_contact': False, 'default_feature_rules': {},
    'relay_only': False, 'peers': {}, 'features': {}, 'rules': {},
    'feature_borrow_enabled': False,
    'max_transfers_per_day': 20, 'max_transfers_per_peer_per_day': 5,
    'max_bytes_per_day': 1048576, 'max_rpc_per_day': 200,
    'max_rpc_per_peer_per_day': 50, 'min_peer_version': PROTOCOL_VERSION,
    'bootstrap_peers': [], 'compress_wire': False,
    'bandwidth_profile': 'auto', 'transfer_chunk_size': 0,
    'relay_credit_per_kb': 1,
    'node_roles': ['bootstrap', 'relay', 'delivery', 'block_sealer'],
    'urace_credit_usd_rate': 1000, 'bootstrap_credit_per_connection': 5,
}


class PolicyStore:
    """Read-only view of policy.json for one exchange root."""

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)

    def load(self) -> dict:
        """Return current policy dict (fresh read each call)."""
        p = self.root / 'policy.json'
        return json.loads(p.read_text()) if p.exists() else dict(_DEFAULT_POLICY)

    def permitted(
        self,
        p: dict,
        peer: str,
        feature: str,
        direction: str,
        seen: set | None = None,
    ) -> bool:
        """Return True iff direction ('send'|'receive') is allowed for peer/feature."""
        if not p['enabled'] or peer not in p['peers'] or p['peers'][peer]['blocked']:
            return False
        if not p['rules'].get(peer + ':' + direction + ':' + feature, False):
            return False
        if feature not in p['features']:
            return False
        seen = set() if seen is None else seen
        if feature in seen:
            return False
        seen = seen | {feature}
        return all(
            self.permitted(p, peer, d, direction, seen)
            for d in p['features'][feature]['dependencies']
        )

    def budget(self, peer: str, size: int, audit_rows: list[dict], policy: dict) -> None:
        """Raise ValueError if daily transfer budget is exhausted."""
        import time as _t
        rows = [
            r for r in audit_rows
            if r['at_unix'] > _t.time() - 86400
            and r['kind'] in ('SEND_RESERVED', 'RECEIVE_RESERVED')
        ]
        if (len(rows) >= policy['max_transfers_per_day']
                or sum(r['bytes'] for r in rows) + size > policy['max_bytes_per_day']):
            raise ValueError('Local exchange daily budget exhausted')
        if sum(r.get('peer') == peer for r in rows) >= policy.get('max_transfers_per_peer_per_day', 5):
            raise ValueError('Per-peer transfer allowance exhausted')
