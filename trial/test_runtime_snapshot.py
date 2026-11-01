"""Tests for per-snapshot summary artifact generation."""
import json, tempfile, unittest
from pathlib import Path
import runtime_snapshot as rs


def _change_spec(rationale='Test improvement', extra=None):
    spec = {
        'rationale': rationale,
        'files_changed': ['runtime/urace/cli.py'],
        'diff': '--- a/cli.py\n+++ b/cli.py\n@@ -1 +1 @@\n-old\n+new\n',
        'engine_sha256_before': 'a' * 64,
        'engine_sha256_after': 'b' * 64,
        'proposer_provider': 'codex',
    }
    if extra:
        spec.update(extra)
    return spec


def _quality_evidence(baseline=60.0, candidate=66.0):
    from runtime_quality_gate import SCHEMA as GATE_SCHEMA
    delta = candidate - baseline if baseline is not None and candidate is not None else None
    return {
        'baseline_score': baseline,
        'candidate_score': candidate,
        'gate_decision': {
            'schema': GATE_SCHEMA,
            'decision': 'ACCEPTED' if delta and delta >= 5.0 else 'REJECTED',
            'delta': delta,
            'minimum_delta': 5.0,
        },
    }


class TestCreate(unittest.TestCase):
    def test_creates_summary_and_artifacts(self):
        with tempfile.TemporaryDirectory() as d:
            sid = rs.create(d, _change_spec(), _quality_evidence())
            base = Path(d) / rs.SNAPSHOTS_DIR / sid
            self.assertTrue((base / 'summary.json').exists())
            self.assertTrue((base / 'change_log.md').exists())
            self.assertTrue((base / 'quality_evidence.json').exists())
            self.assertTrue((base / 'change.diff').exists())

    def test_summary_has_required_fields(self):
        with tempfile.TemporaryDirectory() as d:
            sid = rs.create(d, _change_spec(), _quality_evidence())
            summary = json.loads((Path(d) / rs.SNAPSHOTS_DIR / sid / 'summary.json').read_text())
            for key in ('schema', 'snapshot_id', 'recorded_at', 'engine_sha256_before',
                        'engine_sha256_after', 'files_changed', 'rationale', 'quality'):
                self.assertIn(key, summary)

    def test_quality_delta_computed(self):
        with tempfile.TemporaryDirectory() as d:
            sid = rs.create(d, _change_spec(), _quality_evidence(60.0, 67.0))
            summary = json.loads((Path(d) / rs.SNAPSHOTS_DIR / sid / 'summary.json').read_text())
            self.assertAlmostEqual(summary['quality']['delta'], 7.0)

    def test_index_updated(self):
        with tempfile.TemporaryDirectory() as d:
            rs.create(d, _change_spec('first'), _quality_evidence())
            rs.create(d, _change_spec('second', {'engine_sha256_after': 'c' * 64}), _quality_evidence())
            index = json.loads((Path(d) / rs.SNAPSHOTS_DIR / 'index.json').read_text())
            self.assertEqual(len(index['snapshots']), 2)

    def test_duplicate_create_is_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            sid = rs.create(d, _change_spec(), _quality_evidence(), snapshot_id='test-snap-001')
            rs.create(d, _change_spec(), _quality_evidence(), snapshot_id='test-snap-001')
            index = json.loads((Path(d) / rs.SNAPSHOTS_DIR / 'index.json').read_text())
            self.assertEqual(sum(s['snapshot_id'] == 'test-snap-001' for s in index['snapshots']), 1)

    def test_raises_on_missing_required_field(self):
        with tempfile.TemporaryDirectory() as d:
            spec = _change_spec()
            del spec['rationale']
            with self.assertRaises(ValueError):
                rs.create(d, spec, _quality_evidence())

    def test_raises_on_invalid_change_spec_type(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                rs.create(d, 'not a dict', _quality_evidence())

    def test_no_diff_file_when_diff_empty(self):
        with tempfile.TemporaryDirectory() as d:
            spec = _change_spec()
            spec['diff'] = ''
            sid = rs.create(d, spec, _quality_evidence())
            diff_path = Path(d) / rs.SNAPSHOTS_DIR / sid / 'change.diff'
            self.assertFalse(diff_path.exists())


class TestListAndLoad(unittest.TestCase):
    def test_empty_base_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(rs.list_snapshots(d), [])

    def test_load_returns_summary(self):
        with tempfile.TemporaryDirectory() as d:
            sid = rs.create(d, _change_spec(), _quality_evidence())
            summary = rs.load_snapshot(d, sid)
            self.assertEqual(summary['snapshot_id'], sid)

    def test_load_missing_raises(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(FileNotFoundError):
                rs.load_snapshot(d, 'nonexistent-snap')


class TestPlanningContext(unittest.TestCase):
    def test_empty_when_no_snapshots(self):
        with tempfile.TemporaryDirectory() as d:
            ctx = rs.planning_context(d)
            self.assertEqual(ctx['count'], 0)
            self.assertEqual(ctx['runtime_improvement_history'], [])

    def test_returns_recent_snapshots(self):
        with tempfile.TemporaryDirectory() as d:
            for i in range(7):
                rs.create(d, _change_spec(f'change {i}', {'engine_sha256_after': hex(i)[2:].zfill(64)}),
                          _quality_evidence())
            ctx = rs.planning_context(d, limit=5)
            self.assertEqual(ctx['count'], 5)

    def test_each_entry_has_required_keys(self):
        with tempfile.TemporaryDirectory() as d:
            rs.create(d, _change_spec(), _quality_evidence())
            ctx = rs.planning_context(d)
            entry = ctx['runtime_improvement_history'][0]
            for key in ('snapshot_id', 'recorded_at', 'change_type', 'rationale', 'files_changed', 'quality_delta'):
                self.assertIn(key, entry)

    def test_change_type_stored_and_surfaced(self):
        with tempfile.TemporaryDirectory() as d:
            spec = _change_spec(extra={'change_type': 'new_feature'})
            rs.create(d, spec, _quality_evidence())
            ctx = rs.planning_context(d)
            self.assertEqual(ctx['runtime_improvement_history'][0]['change_type'], 'new_feature')

    def test_change_type_defaults_to_improvement(self):
        with tempfile.TemporaryDirectory() as d:
            rs.create(d, _change_spec(), _quality_evidence())
            ctx = rs.planning_context(d)
            self.assertEqual(ctx['runtime_improvement_history'][0]['change_type'], 'improvement')

    def test_files_removed_stored(self):
        with tempfile.TemporaryDirectory() as d:
            spec = _change_spec(extra={'files_removed': ['runtime/urace/old.py']})
            sid = rs.create(d, spec, _quality_evidence())
            summary = rs.load_snapshot(d, sid)
            self.assertEqual(summary['files_removed'], ['runtime/urace/old.py'])


class TestPlanningContextExtraBases(unittest.TestCase):
    def test_empty_extra_bases_same_as_without(self):
        with tempfile.TemporaryDirectory() as d:
            rs.create(d, _change_spec(), _quality_evidence())
            ctx_none = rs.planning_context(d)
            ctx_empty = rs.planning_context(d, extra_bases=[])
            self.assertEqual(ctx_none['count'], ctx_empty['count'])
            self.assertEqual(
                ctx_none['runtime_improvement_history'][0]['snapshot_id'],
                ctx_empty['runtime_improvement_history'][0]['snapshot_id'],
            )

    def test_extra_bases_merges_entries(self):
        with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
            rs.create(d1, _change_spec('primary change'), _quality_evidence())
            rs.create(d2, _change_spec('extra change', {'engine_sha256_after': 'c' * 64}), _quality_evidence())
            ctx = rs.planning_context(d1, limit=5, extra_bases=[d2])
            self.assertEqual(ctx['count'], 2)

    def test_entries_have_product_base_key(self):
        with tempfile.TemporaryDirectory() as d:
            rs.create(d, _change_spec(), _quality_evidence())
            ctx = rs.planning_context(d)
            self.assertIn('product_base', ctx['runtime_improvement_history'][0])

    def test_product_base_is_str_of_base_path(self):
        with tempfile.TemporaryDirectory() as d:
            rs.create(d, _change_spec(), _quality_evidence())
            ctx = rs.planning_context(d)
            self.assertEqual(ctx['runtime_improvement_history'][0]['product_base'], str(d))

    def test_extra_bases_entries_tagged_with_correct_base(self):
        with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
            rs.create(d1, _change_spec('primary'), _quality_evidence())
            rs.create(d2, _change_spec('extra', {'engine_sha256_after': 'c' * 64}), _quality_evidence())
            ctx = rs.planning_context(d1, limit=5, extra_bases=[d2])
            bases = {e['product_base'] for e in ctx['runtime_improvement_history']}
            self.assertIn(str(d1), bases)
            self.assertIn(str(d2), bases)

    def test_product_bases_in_return_dict(self):
        with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
            ctx = rs.planning_context(d1, extra_bases=[d2])
            self.assertIn('product_bases', ctx)
            self.assertIn(str(d1), ctx['product_bases'])
            self.assertIn(str(d2), ctx['product_bases'])

    def test_limit_respected_across_merged_bases(self):
        with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
            for i in range(4):
                rs.create(d1, _change_spec(f'p{i}', {'engine_sha256_after': hex(i)[2:].zfill(64)}), _quality_evidence())
            for i in range(4, 8):
                rs.create(d2, _change_spec(f'e{i}', {'engine_sha256_after': hex(i)[2:].zfill(64)}), _quality_evidence())
            ctx = rs.planning_context(d1, limit=5, extra_bases=[d2])
            self.assertEqual(ctx['count'], 5)

    def test_duplicate_base_not_doubled(self):
        with tempfile.TemporaryDirectory() as d:
            rs.create(d, _change_spec(), _quality_evidence())
            ctx = rs.planning_context(d, extra_bases=[d])
            # primary base should not be doubled; count should be 1
            self.assertEqual(ctx['count'], 1)


class TestStreamSummaries(unittest.TestCase):
    def test_empty_when_no_snapshots(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(list(rs.stream_summaries(d)), [])

    def test_yields_full_summary(self):
        with tempfile.TemporaryDirectory() as d:
            rs.create(d, _change_spec(), _quality_evidence())
            summaries = list(rs.stream_summaries(d))
            self.assertEqual(len(summaries), 1)
            for key in ('schema', 'snapshot_id', 'rationale', 'quality', 'change_log_path'):
                self.assertIn(key, summaries[0])

    def test_change_log_path_points_to_existing_file(self):
        with tempfile.TemporaryDirectory() as d:
            rs.create(d, _change_spec(), _quality_evidence())
            summary = next(rs.stream_summaries(d))
            self.assertIsNotNone(summary['change_log_path'])
            self.assertTrue(Path(summary['change_log_path']).exists())

    def test_limit_respected(self):
        with tempfile.TemporaryDirectory() as d:
            for i in range(5):
                rs.create(d, _change_spec(f'change {i}', {'engine_sha256_after': hex(i)[2:].zfill(64)}),
                          _quality_evidence())
            summaries = list(rs.stream_summaries(d, limit=3))
            self.assertEqual(len(summaries), 3)

    def test_summaries_in_chronological_order(self):
        with tempfile.TemporaryDirectory() as d:
            for i in range(3):
                rs.create(d, _change_spec(f'change {i}', {'engine_sha256_after': hex(i)[2:].zfill(64)}),
                          _quality_evidence())
            summaries = list(rs.stream_summaries(d))
            timestamps = [s['recorded_at'] for s in summaries]
            self.assertEqual(timestamps, sorted(timestamps))


if __name__ == '__main__':
    unittest.main()
