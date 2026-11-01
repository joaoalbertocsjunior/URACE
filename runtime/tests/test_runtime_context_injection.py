"""Tests for runtime snapshot planning context injection into operator context."""
import json, sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from urace import workflow_state


class TestContextInjection(unittest.TestCase):
    def _make_state(self):
        return {
            'intent': {'purpose': 'test'},
            'authority': {'delegated': []},
            'constraints': [],
            'objectives': [],
            'rule_ledger': {},
            'context_inputs': [],
        }

    def _make_config(self, runtime_workflow_enabled=True):
        config = {'intent': {'purpose': 'test'}, 'authority': {'delegated': []}, 'constraints': []}
        if runtime_workflow_enabled:
            config['runtime_workflow'] = {'enabled': True}
        return config

    def test_no_history_when_no_snapshots(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            state = self._make_state()
            config = self._make_config()
            ctx = workflow_state._context(state, config, base)
            self.assertNotIn('runtime_improvement_history', ctx['value'])

    def test_history_injected_when_snapshots_exist(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            # Create a fake runtime snapshot index
            snap_dir = base / 'runtime-snapshots'
            snap_dir.mkdir()
            snap_id = 'runtime-abc123'
            (snap_dir / snap_id).mkdir()
            summary = {
                'schema': 'runtime-snapshot-v1',
                'snapshot_id': snap_id,
                'recorded_at': '2026-10-27T00:00:00Z',
                'engine_sha256_before': 'a' * 64,
                'engine_sha256_after': 'b' * 64,
                'files_changed': ['runtime/urace/cli.py'],
                'rationale': 'Improved correctness',
                'quality': {'delta': 6.0, 'baseline_score': 60.0, 'candidate_score': 66.0, 'gate_decision': {}},
                'diff_sha256': None, 'diff_bytes': 0,
                'real_user_value_verified': False,
                'real_user_value_note': '',
                'proposer_provider': 'codex',
                'scope': '',
            }
            (snap_dir / snap_id / 'summary.json').write_text(json.dumps(summary))
            (snap_dir / 'index.json').write_text(json.dumps({
                'schema': 'runtime-snapshot-v1',
                'snapshots': [{
                    'snapshot_id': snap_id,
                    'recorded_at': '2026-10-27T00:00:00Z',
                    'engine_sha256_after': 'b' * 64,
                    'delta': 6.0,
                    'files_changed_count': 1,
                }],
            }))

            # Patch sys.path insert and runtime_snapshot import
            trial_dir = base.parent / 'trial'
            with patch('sys.path', sys.path.copy()):
                sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / 'trial'))
                state = self._make_state()
                config = self._make_config()
                ctx = workflow_state._context(state, config, base)

            self.assertIn('runtime_improvement_history', ctx['value'])
            history = ctx['value']['runtime_improvement_history']
            self.assertEqual(len(history), 1)
            self.assertEqual(history[0]['snapshot_id'], snap_id)
            self.assertAlmostEqual(history[0]['quality_delta'], 6.0)

    def test_no_history_when_runtime_workflow_disabled(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            # Create a snapshot that would be visible
            snap_dir = base / 'runtime-snapshots'
            snap_dir.mkdir()
            (snap_dir / 'index.json').write_text(json.dumps({
                'snapshots': [{'snapshot_id': 'x', 'recorded_at': '2026-10-27T00:00:00Z',
                               'engine_sha256_after': 'a' * 64, 'delta': 6.0, 'files_changed_count': 1}]
            }))
            state = self._make_state()
            config = self._make_config(runtime_workflow_enabled=False)
            ctx = workflow_state._context(state, config, base)
            self.assertNotIn('runtime_improvement_history', ctx['value'])

    def test_context_fits_within_size_limit(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            state = self._make_state()
            config = self._make_config()
            ctx = workflow_state._context(state, config, base)
            self.assertLessEqual(ctx['bytes'], 6000)

    def test_context_without_base_unchanged(self):
        state = self._make_state()
        config = self._make_config()
        ctx = workflow_state._context(state, config)
        self.assertNotIn('runtime_improvement_history', ctx['value'])


if __name__ == '__main__':
    unittest.main()
