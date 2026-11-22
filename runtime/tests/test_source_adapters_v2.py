"""Protocol v2 source adapter tests — act path, safety gates, all 28 adapters."""
import unittest


# ── Protocol v2 contract ──────────────────────────────────────────────────────

class ProtocolV2Tests(unittest.TestCase):
    def test_verify_adapter_v2_requires_act(self):
        from urace.source_adapters._base import verify_adapter

        class MissingAct:
            kind = 'x'
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
            # missing: act, supported_actions

        issues = verify_adapter(MissingAct())
        missing = [i for i in issues if 'act' in i or 'supported_actions' in i]
        self.assertTrue(len(missing) >= 2, f'Expected act+supported_actions missing, got: {issues}')

    def test_null_adapter_passes_v2(self):
        from urace.source_adapters._base import verify_adapter, NullSourceAdapter
        self.assertEqual(verify_adapter(NullSourceAdapter()), [])

    def test_all_registered_adapters_pass_v2(self):
        from urace.source_adapters import SOURCE_REGISTRY
        from urace.source_adapters._base import verify_adapter
        for kind, adapter in SOURCE_REGISTRY.all().items():
            issues = verify_adapter(adapter)
            self.assertEqual(issues, [], f'Adapter {kind!r} fails v2 verification: {issues}')


# ── Safety gates ──────────────────────────────────────────────────────────────

class ActSafetyGateTests(unittest.TestCase):
    def _state_with_source(self, kind='null', enabled_actions=None):
        from urace.source_adapters._base import NullSourceAdapter
        state = {}
        adapter = NullSourceAdapter()
        record = adapter._add({}, state, 'src-1')
        if enabled_actions is not None:
            record['adapter_state']['enabled_actions'] = enabled_actions
        state.setdefault('sources', {})['src-1'] = record
        return state

    def test_act_blocked_when_allow_act_false(self):
        from urace.source_adapters._base import NullSourceAdapter, SourceActDeniedError
        adapter = NullSourceAdapter()
        state = self._state_with_source(enabled_actions=['run'])
        config = {'sources': {'allow_act': False}}
        with self.assertRaises(SourceActDeniedError):
            adapter.act(config, state, 'src-1', 'run')

    def test_act_blocked_when_action_not_in_enabled_list(self):
        from urace.source_adapters._base import NullSourceAdapter, SourceActDeniedError
        adapter = NullSourceAdapter()
        state = self._state_with_source(enabled_actions=[])
        config = {'sources': {'allow_act': True}}
        with self.assertRaises(SourceActDeniedError):
            adapter.act(config, state, 'src-1', 'run')

    def test_act_succeeds_when_both_gates_pass(self):
        from urace.source_adapters._base import NullSourceAdapter
        adapter = NullSourceAdapter()
        state = self._state_with_source(enabled_actions=['run'])
        config = {'sources': {'allow_act': True}}
        result = adapter.act(config, state, 'src-1', 'run')
        self.assertIn('acted', result)

    def test_supported_actions_returns_enabled_list(self):
        from urace.source_adapters._base import NullSourceAdapter
        adapter = NullSourceAdapter()
        state = self._state_with_source(enabled_actions=['run', 'scan'])
        actions = adapter.supported_actions(state, 'src-1')
        self.assertEqual(sorted(actions), ['run', 'scan'])

    def test_lifecycle_advances_to_acted(self):
        from urace.source_adapters._base import NullSourceAdapter
        adapter = NullSourceAdapter()
        state = self._state_with_source(enabled_actions=['run'])
        state['sources']['src-1']['status'] = 'OBSERVED'
        config = {'sources': {'allow_act': True}}
        adapter.act(config, state, 'src-1', 'run')
        self.assertEqual(state['sources']['src-1']['status'], 'ACTED')


# ── FolderAdapter act ─────────────────────────────────────────────────────────

class FolderActTests(unittest.TestCase):
    def test_scan_action_dispatches_sync(self):
        import tempfile, os
        from urace.source_adapters.folder import FolderAdapter
        with tempfile.TemporaryDirectory() as d:
            # Create a test file
            open(os.path.join(d, 'test.py'), 'w').close()
            adapter = FolderAdapter()
            state = {}
            record = adapter._add({}, state, 'f1', path=d, pattern='**/*.py')
            record['adapter_state']['enabled_actions'] = ['scan']
            state.setdefault('sources', {})['f1'] = record
            config = {'sources': {'allow_act': True}}
            result = adapter.act(config, state, 'f1', 'scan')
            self.assertTrue(result.get('acted'))
            self.assertGreater(result.get('file_count', 0), 0)

    def test_unknown_action_returns_acted_false(self):
        from urace.source_adapters.folder import FolderAdapter
        adapter = FolderAdapter()
        result = adapter._act({}, {}, 'f1', 'unknown', {})
        self.assertFalse(result['acted'])


# ── ShellAdapter act ──────────────────────────────────────────────────────────

class ShellActTests(unittest.TestCase):
    def test_run_action_executes_command(self):
        import sys
        from urace.source_adapters.shell_adapter import ShellAdapter
        adapter = ShellAdapter()
        state = {}
        record = adapter._add({}, state, 's1', command=f'{sys.executable} -c "print(1)"')
        record['adapter_state']['enabled_actions'] = ['run']
        state.setdefault('sources', {})['s1'] = record
        config = {'sources': {'allow_act': True}}
        result = adapter.act(config, state, 's1', 'run')
        self.assertTrue(result.get('acted'))


# ── TestSuiteAdapter act ──────────────────────────────────────────────────────

class TestSuiteActTests(unittest.TestCase):
    def test_run_action_dispatches_sync(self):
        import sys
        from urace.source_adapters.testsuite_adapter import TestSuiteAdapter
        adapter = TestSuiteAdapter()
        state = {}
        record = adapter._add({}, state, 'ts1', command=f'{sys.executable} -m pytest --co -q')
        record['adapter_state']['enabled_actions'] = ['run']
        state.setdefault('sources', {})['ts1'] = record
        config = {'sources': {'allow_act': True}}
        result = adapter.act(config, state, 'ts1', 'run')
        self.assertIn('acted', result)


# ── Config allow_act gate ─────────────────────────────────────────────────────

class ConfigActGateTests(unittest.TestCase):
    def test_sources_cfg_allow_act_defaults_false(self):
        from urace.config_access import sources_cfg
        cfg = sources_cfg({})
        self.assertFalse(cfg.allow_act)
        self.assertTrue(cfg.act_audit_all)

    def test_sources_cfg_allow_act_reads_config(self):
        from urace.config_access import sources_cfg
        cfg = sources_cfg({'sources': {'allow_act': True}})
        self.assertTrue(cfg.allow_act)


# ── Audit kinds ───────────────────────────────────────────────────────────────

class ActAuditKindsTests(unittest.TestCase):
    def test_act_kinds_in_all_kinds(self):
        from urace.audit_kinds import ALL_KINDS, SOURCE_ACTED, SOURCE_ACT_DENIED, SOURCE_ACT_FAILED
        for k in (SOURCE_ACTED, SOURCE_ACT_DENIED, SOURCE_ACT_FAILED):
            self.assertIn(k, ALL_KINDS)

    def test_act_kind_values_match_names(self):
        from urace.audit_kinds import SOURCE_ACTED, SOURCE_ACT_DENIED, SOURCE_ACT_FAILED, SOURCE_SYNCED
        self.assertEqual(SOURCE_ACTED, 'SOURCE_ACTED')
        self.assertEqual(SOURCE_ACT_DENIED, 'SOURCE_ACT_DENIED')
        self.assertEqual(SOURCE_ACT_FAILED, 'SOURCE_ACT_FAILED')
        self.assertEqual(SOURCE_SYNCED, 'SOURCE_SYNCED')


# ── enabled_actions in adapter_state ─────────────────────────────────────────

class EnabledActionsAdapterStateTests(unittest.TestCase):
    """Every _add override must include enabled_actions: [] in adapter_state."""

    def _check_adapter(self, kind):
        from urace.source_adapters import SOURCE_REGISTRY
        adapter = SOURCE_REGISTRY.get(kind)
        self.assertIsNotNone(adapter, f'No adapter for {kind!r}')
        state = {}
        record = adapter._add({}, state, f'test-{kind}')
        astate = record.get('adapter_state', {})
        self.assertIn('enabled_actions', astate,
                      f'{kind} _add() does not include enabled_actions in adapter_state')
        self.assertIsInstance(astate['enabled_actions'], list)

    def test_folder_has_enabled_actions(self): self._check_adapter('folder')
    def test_shell_has_enabled_actions(self): self._check_adapter('shell')
    def test_environment_has_enabled_actions(self): self._check_adapter('environment')
    def test_codebase_has_enabled_actions(self): self._check_adapter('codebase')
    def test_test_suite_has_enabled_actions(self): self._check_adapter('test_suite')
    def test_webhook_has_enabled_actions(self): self._check_adapter('webhook')
    def test_database_has_enabled_actions(self): self._check_adapter('database')
    def test_p2p_catalog_has_enabled_actions(self): self._check_adapter('p2p_catalog')
    def test_file_has_enabled_actions(self): self._check_adapter('file')
    def test_github_has_enabled_actions(self): self._check_adapter('github')
    def test_connector_has_enabled_actions(self): self._check_adapter('connector')
    def test_executor_has_enabled_actions(self): self._check_adapter('executor')
    def test_peer_has_enabled_actions(self): self._check_adapter('peer')
    def test_metric_has_enabled_actions(self): self._check_adapter('metric')
    def test_vital_has_enabled_actions(self): self._check_adapter('vital')
    def test_product_has_enabled_actions(self): self._check_adapter('product')
    def test_git_has_enabled_actions(self): self._check_adapter('git')
    def test_s3_has_enabled_actions(self): self._check_adapter('s3')
    def test_ci_pipeline_has_enabled_actions(self): self._check_adapter('ci_pipeline')
    def test_event_stream_has_enabled_actions(self): self._check_adapter('event_stream')
    def test_inbox_has_enabled_actions(self): self._check_adapter('inbox')
    def test_mcp_server_has_enabled_actions(self): self._check_adapter('mcp_server')
    def test_log_file_has_enabled_actions(self): self._check_adapter('log_file')
    def test_package_registry_has_enabled_actions(self): self._check_adapter('package_registry')


# ── New adapter registrations ─────────────────────────────────────────────────

class NewAdapterRegistrationTests(unittest.TestCase):
    def test_all_new_adapters_registered(self):
        from urace.source_adapters import SOURCE_REGISTRY
        expected = {'git', 's3', 'ci_pipeline', 'event_stream',
                    'inbox', 'mcp_server', 'log_file', 'package_registry'}
        kinds = set(SOURCE_REGISTRY.kinds())
        missing = expected - kinds
        self.assertFalse(missing, f'Missing adapters: {missing}')

    def test_total_kinds_at_least_28(self):
        from urace.source_adapters import SOURCE_REGISTRY
        self.assertGreaterEqual(len(SOURCE_REGISTRY.kinds()), 28)


# ── LogFileAdapter _sync ──────────────────────────────────────────────────────

class LogFileAdapterTests(unittest.TestCase):
    def test_sync_counts_matching_lines(self):
        import tempfile, os
        from urace.source_adapters.log_file_adapter import LogFileAdapter
        adapter = LogFileAdapter()
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            f.write('ERROR: something bad\nINFO: ok\nERROR: another\n')
            path = f.name
        try:
            state = {}
            record = adapter._add({}, state, 'lf1', path=path, pattern='ERROR', tail_lines=100)
            state.setdefault('sources', {})['lf1'] = record
            result = adapter._sync({}, state, 'lf1')
            self.assertTrue(result['synced'])
            self.assertEqual(result['matches'], 2)
        finally:
            os.unlink(path)


# ── PackageRegistryAdapter validate ──────────────────────────────────────────

class PackageRegistryAdapterTests(unittest.TestCase):
    def test_validate_requires_package(self):
        from urace.source_adapters.package_registry_adapter import PackageRegistryAdapter
        import argparse
        adapter = PackageRegistryAdapter()
        args = argparse.Namespace(name='test', package=None, registry='pypi', group=None)
        with self.assertRaises(ValueError):
            adapter.validate(args)


# ── Version ───────────────────────────────────────────────────────────────────

class ProtocolVersionTests(unittest.TestCase):
    def test_source_adapter_protocol_version_is_2(self):
        from urace.version import SOURCE_ADAPTER_PROTOCOL_VERSION
        self.assertEqual(SOURCE_ADAPTER_PROTOCOL_VERSION, 2)

    def test_api_schema_versions_updated(self):
        from urace.version import API_SCHEMA_VERSIONS
        self.assertEqual(API_SCHEMA_VERSIONS['source_adapter'], 2)


# ── Pydantic config models ────────────────────────────────────────────────────

class PydanticConfigTests(unittest.TestCase):
    def test_sources_config_is_pydantic_model(self):
        from pydantic import BaseModel
        from urace.config_access import SourcesConfig
        self.assertTrue(issubclass(SourcesConfig, BaseModel))

    def test_invalid_type_coerced(self):
        from urace.config_access import sources_cfg
        # Pydantic coerces '300' string to int
        cfg = sources_cfg({'sources': {'auto_sync_interval_s': '600'}})
        self.assertEqual(cfg.auto_sync_interval_s, 600)

    def test_all_config_models_are_pydantic(self):
        from pydantic import BaseModel
        from urace.config_access import (
            LoggingConfig, P2PConfig, FeatureMatchingConfig,
            SourcesConfig, MimePolicyConfig
        )
        for cls in (LoggingConfig, P2PConfig, FeatureMatchingConfig, SourcesConfig, MimePolicyConfig):
            self.assertTrue(issubclass(cls, BaseModel), f'{cls.__name__} is not a Pydantic model')


# ── Feature matcher difflib ───────────────────────────────────────────────────

class DifflibMatcherTests(unittest.TestCase):
    def test_similar_capability_gets_nonzero_score(self):
        from urace.feature_matcher import match
        profile = {'capability': 'Python test suite runner'}
        atom = {
            'descriptor': {
                'capability': 'pytest test suite execution',
                'interface_sha384': 'a' * 96,
                'acceptance_sha384': 'b' * 96,
                'content_sha384': 'c' * 96,
                'dependencies': [],
                'publisher_id': 'p1',
                'license_id': 'MIT',
            },
            'lifecycle': 'active',
        }
        result = match(profile, atom, {})
        self.assertGreater(result['score'], 0)

    def test_exact_capability_scores_higher_than_unrelated(self):
        from urace.feature_matcher import match
        profile = {'capability': 'Python code quality linting'}
        base = {
            'descriptor': {
                'interface_sha384': 'a' * 96,
                'acceptance_sha384': 'b' * 96,
                'content_sha384': 'c' * 96,
                'dependencies': [],
                'publisher_id': 'p1',
                'license_id': 'MIT',
            },
            'lifecycle': 'active',
        }
        close_atom = {**base, 'descriptor': {**base['descriptor'], 'capability': 'Python linting code quality'}}
        far_atom = {**base, 'descriptor': {**base['descriptor'], 'capability': 'React UI component library'}}
        close_score = match(profile, close_atom, {})['score']
        far_score = match(profile, far_atom, {})['score']
        self.assertGreater(close_score, far_score)


if __name__ == '__main__':
    unittest.main()
