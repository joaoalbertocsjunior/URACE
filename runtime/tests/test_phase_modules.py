"""Phase 10A — test alignment for Phase 3-9 new modules."""
import unittest


# ── product_profile ───────────────────────────────────────────────────────────

class ProductProfileTests(unittest.TestCase):
    def test_load_empty_state(self):
        from urace.product_profile import load
        self.assertEqual(load({}), {})

    def test_update_merges(self):
        from urace.product_profile import update
        state = {}
        update(state, codebase_loc=100, codebase_languages=['.py'])
        self.assertEqual(state['product_profile']['codebase_loc'], 100)

    def test_set_capability(self):
        from urace.product_profile import set_capability, load
        state = {}
        set_capability(state, '  Python test runner  ')
        self.assertEqual(load(state)['capability'], 'Python test runner')

    def test_validate_missing_capability(self):
        from urace.product_profile import validate
        warnings = validate({'codebase_loc': 100})
        self.assertTrue(any('capability' in w for w in warnings))

    def test_validate_ok(self):
        from urace.product_profile import validate
        self.assertEqual(validate({'capability': 'test'}), [])

    def test_snapshot_ready_for_matching(self):
        from urace.product_profile import snapshot, set_capability
        state = {}
        set_capability(state, 'Python improvement')
        s = snapshot(state)
        self.assertTrue(s['ready_for_matching'])

    def test_set_capability_empty_raises(self):
        from urace.product_profile import set_capability
        with self.assertRaises(ValueError):
            set_capability({}, '')


# ── feature_matcher ───────────────────────────────────────────────────────────

class FeatureMatcherTests(unittest.TestCase):
    def _atom(self, capability='Python code quality improvement', lifecycle='active'):
        return {
            'descriptor': {
                'capability': capability,
                'interface_sha384': 'a' * 96,
                'acceptance_sha384': 'b' * 96,
                'content_sha384': 'c' * 96,
                'dependencies': [],
                'publisher_id': 'p1',
                'license_id': 'MIT',
            },
            'lifecycle': lifecycle,
        }

    def _profile(self):
        return {'capability': 'Python runtime quality', 'codebase_languages': ['.py'], 'codebase_loc': 10000}

    def test_layer2_match_returns_score(self):
        from urace.feature_matcher import match
        result = match(self._profile(), self._atom(), config={})
        self.assertGreater(result['score'], 0)
        self.assertEqual(result['layer'], 2)

    def test_deprecated_lifecycle_not_borrowable(self):
        from urace.feature_matcher import match
        result = match(self._profile(), self._atom(lifecycle='deprecated'), config={})
        self.assertFalse(result['borrowable'])

    def test_layer1_exact_interface_match(self):
        from urace.feature_matcher import match
        iface = 'a' * 96
        profile = {**self._profile(), 'interface_sha384': iface}
        result = match(profile, self._atom(), config={})
        self.assertEqual(result['score'], 1.0)
        self.assertEqual(result['layer'], 1)

    def test_rank_returns_sorted(self):
        from urace.feature_matcher import rank
        atoms = {
            'k1': self._atom('Python test coverage'),
            'k2': self._atom('JavaScript UI component'),
        }
        profile = self._profile()
        ranked = rank(profile, atoms, config={})
        self.assertIsInstance(ranked, list)
        if len(ranked) >= 2:
            self.assertGreaterEqual(ranked[0]['score'], ranked[1]['score'])


# ── config_access ─────────────────────────────────────────────────────────────

class ConfigAccessTests(unittest.TestCase):
    def test_logging_cfg_defaults(self):
        from urace.config_access import logging_cfg
        cfg = logging_cfg({})
        self.assertEqual(cfg.level, 'WARNING')
        self.assertEqual(cfg.format, 'text')
        self.assertFalse(cfg.m2m_stream)

    def test_logging_cfg_from_config(self):
        from urace.config_access import logging_cfg
        cfg = logging_cfg({'logging': {'level': 'DEBUG', 'm2m_stream': True}})
        self.assertEqual(cfg.level, 'DEBUG')
        self.assertTrue(cfg.m2m_stream)

    def test_p2p_cfg_defaults(self):
        from urace.config_access import p2p_cfg
        cfg = p2p_cfg({})
        self.assertEqual(cfg.min_evidence_borrows, 5)
        self.assertEqual(cfg.trial_escrow_pct, 10)

    def test_sources_cfg_defaults(self):
        from urace.config_access import sources_cfg
        cfg = sources_cfg({})
        self.assertEqual(cfg.auto_sync_interval_s, 300)

    def test_sources_cfg_override(self):
        from urace.config_access import sources_cfg
        cfg = sources_cfg({'sources': {'auto_sync_interval_s': 600}})
        self.assertEqual(cfg.auto_sync_interval_s, 600)

    def test_feature_matching_defaults(self):
        from urace.config_access import feature_matching_cfg
        cfg = feature_matching_cfg({})
        self.assertTrue(cfg.layer1_strict)
        self.assertEqual(cfg.layer2_cap_weight, 60)

    def test_mime_policy_default(self):
        from urace.config_access import mime_policy_cfg
        cfg = mime_policy_cfg({})
        self.assertEqual(cfg.network_policy, 'quality_gate_only')


# ── audit_kinds ───────────────────────────────────────────────────────────────

class AuditKindsTests(unittest.TestCase):
    def test_all_kinds_is_frozenset(self):
        from urace.audit_kinds import ALL_KINDS
        self.assertIsInstance(ALL_KINDS, frozenset)
        self.assertGreater(len(ALL_KINDS), 50)

    def test_key_constants_match_values(self):
        from urace.audit_kinds import FEATURE_BORROWED, APPLIED_AFTER_LOCAL_QUALIFICATION
        self.assertEqual(FEATURE_BORROWED, 'FEATURE_BORROWED')
        self.assertEqual(APPLIED_AFTER_LOCAL_QUALIFICATION, 'APPLIED_AFTER_LOCAL_QUALIFICATION')

    def test_all_kinds_contains_core(self):
        from urace.audit_kinds import ALL_KINDS
        for kind in ('FEATURE_BORROWED', 'CREDIT_DELTA', 'WORK_REQUEST', 'PEER_ADDED'):
            self.assertIn(kind, ALL_KINDS)


# ── source adapter protocol verifier (Phase 7A) ───────────────────────────────

class SourceAdapterVerifierTests(unittest.TestCase):
    def test_valid_adapter_no_issues(self):
        from urace.source_adapters._base import verify_adapter, NullSourceAdapter
        self.assertEqual(verify_adapter(NullSourceAdapter()), [])

    def test_missing_kind_reported(self):
        from urace.source_adapters._base import verify_adapter

        class BadAdapter:
            def add_args(self, s): pass
            def validate(self, a): pass
            def add(self, c, s, i, **k): pass
            def list(self, s): pass
            def status(self, s, i): pass
            def sync(self, c, s, i): pass
            def inspect(self, s, i): pass
            def enable(self, s, i): pass
            def disable(self, s, i): pass
            def remove(self, s, i): pass

        issues = verify_adapter(BadAdapter())
        self.assertTrue(any('kind' in i for i in issues))


# ── state key migration (Phase 7B) ────────────────────────────────────────────

class StateMigrationTests(unittest.TestCase):
    def test_connector_sources_migrated(self):
        from urace._common import migrate_state_keys
        state = {'connector_sources': [{'id': 'x', 'kind': 'file'}]}
        migrate_state_keys(state)
        self.assertIn('sources', state)
        self.assertEqual(state['sources']['x']['kind'], 'file')

    def test_trace_records_migrated(self):
        from urace._common import migrate_state_keys
        state = {'trace_records': [1, 2]}
        migrate_state_keys(state)
        self.assertEqual(state['traces'], [1, 2])

    def test_existing_sources_not_overwritten(self):
        from urace._common import migrate_state_keys
        state = {'connector_sources': [{'id': 'old'}], 'sources': {'new': {}}}
        migrate_state_keys(state)
        self.assertNotIn('old', state['sources'])

    def test_no_mutation_when_nothing_to_migrate(self):
        from urace._common import migrate_state_keys
        state = {'foo': 'bar'}
        migrate_state_keys(state)
        self.assertNotIn('sources', state)
        self.assertNotIn('traces', state)


# ── cli_emit traces dual-write (Phase 8C) ─────────────────────────────────────

class TraceDualWriteTests(unittest.TestCase):
    def _emit(self):
        from urace.cli_emit import _emit_trace
        state = {}
        _emit_trace(state, kind='test', summary='s')
        return state

    def test_writes_to_traces(self):
        state = self._emit()
        self.assertIn('traces', state)
        self.assertEqual(len(state['traces']), 1)

    def test_writes_to_trace_records(self):
        state = self._emit()
        self.assertIn('trace_records', state)
        self.assertEqual(len(state['trace_records']), 1)

    def test_same_record_object(self):
        state = self._emit()
        self.assertIs(state['traces'][0], state['trace_records'][0])


if __name__ == '__main__':
    unittest.main()
