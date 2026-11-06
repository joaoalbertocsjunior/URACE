"""Tests for feature visibility: private/org/public enforcement."""
import time
import unittest


class MockExchange:
    def __init__(self, root=None):
        self._rows = []
        self.root = root or '/tmp/test_visibility'

    def audit_rows(self):
        return list(self._rows)

    def append_audit_row(self, row):
        self._rows.append(row)

    def identity(self):
        return {'peer_id': 'test-peer'}


def _grant_row(feature_id, peer_id, visibility='public'):
    return {
        'kind': 'EQUITY_GRANT',
        'feature_id': feature_id,
        'peer_id': peer_id,
        'basis_points': 10000,
        'visibility': visibility,
        'at_unix': time.time(),
    }


def _listing_row(listing_id, feature_id, seller_id, ask_price=0):
    return {
        'kind': 'EQUITY_LISTING',
        'listing_id': listing_id,
        'feature_id': feature_id,
        'seller_id': seller_id,
        'basis_points': 100,
        'ask_price_units': ask_price,
        'expires_at_unix': time.time() + 86400,
        'at_unix': time.time(),
    }


def _check_visibility(exchange, feature_id, local_id):
    """Simulate the visibility check in exchange_cli fill-listing."""
    fl_rows = exchange.audit_rows()
    grant_row = next((r for r in fl_rows if r.get('kind') == 'EQUITY_GRANT' and r.get('feature_id') == feature_id), None)
    if grant_row is None:
        return  # no grant → no restriction
    visibility = grant_row.get('visibility', 'public') or 'public'
    creator = grant_row.get('peer_id', '') or ''
    if visibility == 'private':
        if local_id != creator:
            raise ValueError(f'Feature {feature_id!r} is private — only creator {creator!r} can fill this listing')
    elif visibility == 'org':
        buyer_org = local_id[:8] if len(local_id) >= 8 else local_id
        creator_org = creator[:8] if len(creator) >= 8 else creator
        if buyer_org != creator_org:
            raise ValueError(f'Feature {feature_id!r} is org-restricted — buyer {local_id!r} is not in the same org as creator {creator!r}')


class TestVisibilityPrivate(unittest.TestCase):
    def setUp(self):
        self.ex = MockExchange()
        self.ex.append_audit_row(_grant_row('feat-priv', 'alice-peer', 'private'))

    def test_creator_can_access_private(self):
        # creator can fill → no exception
        _check_visibility(self.ex, 'feat-priv', 'alice-peer')

    def test_non_creator_blocked_from_private(self):
        with self.assertRaises(ValueError) as ctx:
            _check_visibility(self.ex, 'feat-priv', 'bob-peer')
        self.assertIn('private', str(ctx.exception))

    def test_different_peer_blocked(self):
        with self.assertRaises(ValueError):
            _check_visibility(self.ex, 'feat-priv', 'charlie-peer')


class TestVisibilityOrg(unittest.TestCase):
    def setUp(self):
        self.ex = MockExchange()
        # creator = 'acme0001-mainnode' (org prefix 'acme0001')
        self.ex.append_audit_row(_grant_row('feat-org', 'acme0001-mainnode', 'org'))

    def test_same_org_prefix_allowed(self):
        # buyer starts with same 8 chars 'acme0001'
        _check_visibility(self.ex, 'feat-org', 'acme0001-secondary')

    def test_cross_org_blocked(self):
        with self.assertRaises(ValueError) as ctx:
            _check_visibility(self.ex, 'feat-org', 'betacorp-node1')
        self.assertIn('org-restricted', str(ctx.exception))

    def test_creator_same_org_as_self(self):
        # creator fills their own org listing — same 8 chars
        _check_visibility(self.ex, 'feat-org', 'acme0001-mainnode')


class TestVisibilityPublic(unittest.TestCase):
    def setUp(self):
        self.ex = MockExchange()
        self.ex.append_audit_row(_grant_row('feat-pub', 'alice-peer', 'public'))

    def test_anyone_can_access_public(self):
        _check_visibility(self.ex, 'feat-pub', 'bob-peer')
        _check_visibility(self.ex, 'feat-pub', 'charlie-peer')
        _check_visibility(self.ex, 'feat-pub', 'alice-peer')

    def test_default_visibility_is_public(self):
        # Grant row without explicit visibility defaults to public
        ex2 = MockExchange()
        ex2.append_audit_row({
            'kind': 'EQUITY_GRANT',
            'feature_id': 'feat-default',
            'peer_id': 'alice-peer',
            'basis_points': 10000,
            'at_unix': time.time(),
            # no 'visibility' key
        })
        # Should not raise for any peer
        _check_visibility(ex2, 'feat-default', 'anyone')


class TestVisibilityFieldInGrantRow(unittest.TestCase):
    def test_visibility_field_stored_in_grant(self):
        from urace import feature_equity as fe
        ex = MockExchange()
        fe.grant_equity(ex, 'feat-v', 'alice', visibility='org')
        rows = ex.audit_rows()
        grant = next((r for r in rows if r.get('kind') == 'EQUITY_GRANT'), None)
        self.assertIsNotNone(grant)
        self.assertEqual(grant.get('visibility'), 'org')

    def test_visibility_public_stored(self):
        from urace import feature_equity as fe
        ex = MockExchange()
        fe.grant_equity(ex, 'feat-pub', 'alice', visibility='public')
        grant = next((r for r in ex.audit_rows() if r.get('kind') == 'EQUITY_GRANT'), None)
        self.assertEqual(grant.get('visibility'), 'public')

    def test_visibility_private_stored(self):
        from urace import feature_equity as fe
        ex = MockExchange()
        fe.grant_equity(ex, 'feat-prv', 'alice', visibility='private')
        grant = next((r for r in ex.audit_rows() if r.get('kind') == 'EQUITY_GRANT'), None)
        self.assertEqual(grant.get('visibility'), 'private')


if __name__ == '__main__':
    unittest.main()
