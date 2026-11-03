"""Tests for the urace watch runtime improvement feed command."""
import json, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

TRIAL_DIR = Path(__file__).resolve().parents[2] / 'trial'


def _run_watch(*extra_args):
    result = subprocess.run(
        [sys.executable, '-m', 'urace', 'watch', *extra_args],
        capture_output=True, text=True,
        cwd=str(Path(__file__).resolve().parents[1]),
    )
    return result


def _create_test_snapshot(trial_base: Path, rationale: str = 'Test improvement',
                           baseline: float = 60.0, candidate: float = 66.0):
    """Create a snapshot entry by calling runtime_snapshot.create() directly."""
    sys.path.insert(0, str(TRIAL_DIR))
    import runtime_snapshot as rs
    spec = {
        'rationale': rationale,
        'files_changed': ['runtime/urace/cli.py'],
        'engine_sha256_before': 'a' * 64,
        'engine_sha256_after': 'b' * 64,
        'proposer_provider': 'codex',
    }
    from runtime_quality_gate import SCHEMA as GATE_SCHEMA
    evidence = {
        'baseline_score': baseline,
        'candidate_score': candidate,
        'gate_decision': {
            'schema': GATE_SCHEMA,
            'decision': 'ACCEPTED',
            'delta': candidate - baseline,
            'minimum_delta': 5.0,
        },
    }
    return rs.create(str(trial_base), spec, evidence)


class TestWatchCommandBasic(unittest.TestCase):
    def test_exits_zero_no_snapshots(self):
        result = _run_watch()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_exits_zero_json_no_snapshots(self):
        result = _run_watch('--json')
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_help_exits_zero(self):
        result = _run_watch('--help')
        self.assertEqual(result.returncode, 0)

    def test_help_mentions_follow(self):
        result = _run_watch('--help')
        self.assertIn('follow', result.stdout.lower())


class TestWatchCommandOutput(unittest.TestCase):
    """These tests patch the trial BASE via a temp snapshot dir."""

    def setUp(self):
        sys.path.insert(0, str(TRIAL_DIR))

    def test_snapshot_appears_in_human_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / 'trial'
            base.mkdir()
            sid = _create_test_snapshot(base)
            sys.path.insert(0, str(TRIAL_DIR))
            import runtime_snapshot as rs
            snapshots = rs.list_snapshots(str(base))
            self.assertEqual(len(snapshots), 1)
            self.assertEqual(snapshots[0]['snapshot_id'], sid)

    def test_snapshot_fields_accessible(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / 'trial'
            base.mkdir()
            sid = _create_test_snapshot(base, 'Improved error messages')
            import runtime_snapshot as rs
            summary = rs.load_snapshot(str(base), sid)
            self.assertEqual(summary['rationale'], 'Improved error messages')
            self.assertAlmostEqual(summary['quality']['delta'], 6.0)

    def test_deployment_log_readable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base = root / 'trial'
            base.mkdir()
            urace = root / 'runtime' / 'urace'
            urace.mkdir(parents=True)
            (urace / 'cli.py').write_text('# original\n')
            (base / 'executable-benchmark-latest.json').write_text(
                json.dumps({'scorecard': {'overall_quality_score': 60.0}})
            )
            import runtime_trial as rt
            result = rt.run(base, {}, {
                'rationale': 'Watch test',
                'files_changed': ['runtime/urace/cli.py'],
                'proposer_provider': 'codex',
            }, candidate_score=66.0)
            self.assertEqual(result['status'], 'REJECTED')
            events = rt.deployment_log(base)
            self.assertEqual(events, [])


if __name__ == '__main__':
    unittest.main()
