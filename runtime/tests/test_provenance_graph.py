import unittest, time, tempfile
from pathlib import Path
from urace import provenance_graph as pg, peer_exchange as pe


def _make_exchange():
    tmp = tempfile.mkdtemp()
    e = pe.Exchange(Path(tmp) / 'node')
    e.configure(enabled=True, network=False)
    e.feature('feat', [])
    return e

def _grant(e, fid, owner):
    e.append_audit_row({'kind':'EQUITY_GRANT','feature_id':fid,'peer_id':owner,'basis_points':10000,'at_unix':time.time()})

def _compose(e, composite, components, weights=None):
    w = weights or {}
    e.append_audit_row({'kind':'FEATURE_COMPOSITION','composite_feature_id':composite,'component_feature_ids':components,'component_weights':w,'auto_detected':True,'at_unix':time.time()})


class ResolveProvenanceTests(unittest.TestCase):

    def test_no_composition_returns_creator(self):
        e = _make_exchange()
        _grant(e, 'feat-A', 'alice')
        result = pg.resolve_provenance_weights('feat-A', e.audit_rows())
        self.assertAlmostEqual(result.get('alice', 0), 1.0, places=5)

    def test_simple_two_component_equal_weights(self):
        e = _make_exchange()
        _grant(e, 'base-B', 'bob')
        _grant(e, 'base-C', 'carol')
        _grant(e, 'comp-X', 'alice')
        _compose(e, 'comp-X', ['base-B', 'base-C'])  # no weights → equal
        result = pg.resolve_provenance_weights('comp-X', e.audit_rows())
        # Equal split: bob 50%, carol 50%, alice novel fraction 0
        self.assertAlmostEqual(result.get('bob', 0), 0.5, places=3)
        self.assertAlmostEqual(result.get('carol', 0), 0.5, places=3)

    def test_weighted_two_components(self):
        e = _make_exchange()
        _grant(e, 'base-A', 'alice')
        _grant(e, 'base-B', 'bob')
        _grant(e, 'comp-Y', 'carol')
        _compose(e, 'comp-Y', ['base-A', 'base-B'], {'base-A': 0.6, 'base-B': 0.4})
        result = pg.resolve_provenance_weights('comp-Y', e.audit_rows())
        self.assertAlmostEqual(result.get('alice', 0), 0.6, places=3)
        self.assertAlmostEqual(result.get('bob', 0), 0.4, places=3)

    def test_novel_fraction_goes_to_composite_creator(self):
        e = _make_exchange()
        _grant(e, 'base-A', 'alice')
        _grant(e, 'comp-Z', 'carol')
        # Component A is only 60% — carol keeps 40% novel
        _compose(e, 'comp-Z', ['base-A'], {'base-A': 0.6})
        result = pg.resolve_provenance_weights('comp-Z', e.audit_rows())
        self.assertAlmostEqual(result.get('alice', 0), 0.6, places=3)
        self.assertAlmostEqual(result.get('carol', 0), 0.4, places=3)

    def test_multi_level_provenance(self):
        e = _make_exchange()
        # base-P (pete), base-Q (quinn) → mid-M (mary) with equal weights
        # mid-M (50%) + base-R (rob, 50%) → top-T (tina)
        _grant(e, 'base-P', 'pete')
        _grant(e, 'base-Q', 'quinn')
        _grant(e, 'mid-M', 'mary')
        _compose(e, 'mid-M', ['base-P', 'base-Q'])  # equal: pete 50%, quinn 50%
        _grant(e, 'base-R', 'rob')
        _grant(e, 'top-T', 'tina')
        _compose(e, 'top-T', ['mid-M', 'base-R'], {'mid-M': 0.5, 'base-R': 0.5})
        result = pg.resolve_provenance_weights('top-T', e.audit_rows())
        # mid-M is 50% of top-T, itself 50/50 → pete=25%, quinn=25%
        # base-R is 50% → rob=50%
        self.assertAlmostEqual(result.get('pete', 0), 0.25, places=3)
        self.assertAlmostEqual(result.get('quinn', 0), 0.25, places=3)
        self.assertAlmostEqual(result.get('rob', 0), 0.50, places=3)

    def test_weights_sum_to_one(self):
        e = _make_exchange()
        _grant(e, 'a', 'aa'); _grant(e, 'b', 'bb'); _grant(e, 'c', 'cc')
        _grant(e, 'comp', 'owner')
        _compose(e, 'comp', ['a', 'b', 'c'], {'a': 0.3, 'b': 0.3, 'c': 0.3})
        result = pg.resolve_provenance_weights('comp', e.audit_rows())
        total = sum(result.values())
        self.assertAlmostEqual(total, 1.0, places=5)

    def test_cycle_guard(self):
        e = _make_exchange()
        _grant(e, 'x', 'owner-x')
        _grant(e, 'y', 'owner-y')
        _compose(e, 'x', ['y'])
        _compose(e, 'y', ['x'])  # artificial cycle
        # Should not hang or crash
        result = pg.resolve_provenance_weights('x', e.audit_rows())
        self.assertIsInstance(result, dict)


class CompositionReferralAmountsTests(unittest.TestCase):

    def test_equal_split_two_peers(self):
        e = _make_exchange()
        _grant(e, 'a', 'alice'); _grant(e, 'b', 'bob')
        _grant(e, 'c', 'carol')
        _compose(e, 'c', ['a', 'b'])
        alloc = pg.composition_referral_amounts('c', e.audit_rows(), 100)
        self.assertEqual(sum(alloc.values()), 100)
        self.assertIn('alice', alloc)
        self.assertIn('bob', alloc)

    def test_weighted_proportional(self):
        e = _make_exchange()
        _grant(e, 'big', 'big-owner'); _grant(e, 'small', 'small-owner')
        _grant(e, 'comp', 'comp-owner')
        _compose(e, 'comp', ['big', 'small'], {'big': 0.8, 'small': 0.2})
        alloc = pg.composition_referral_amounts('comp', e.audit_rows(), 100)
        self.assertEqual(sum(alloc.values()), 100)
        self.assertGreater(alloc.get('big-owner', 0), alloc.get('small-owner', 0))

    def test_zero_pool_returns_empty(self):
        e = _make_exchange()
        _grant(e, 'a', 'alice'); _grant(e, 'comp', 'carol')
        _compose(e, 'comp', ['a'])
        self.assertEqual(pg.composition_referral_amounts('comp', e.audit_rows(), 0), {})

    def test_no_composition_returns_empty(self):
        e = _make_exchange()
        _grant(e, 'solo', 'alice')
        self.assertEqual(pg.composition_referral_amounts('solo', e.audit_rows(), 50), {})


if __name__ == '__main__':
    unittest.main()
