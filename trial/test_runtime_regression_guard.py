"""Tests for runtime_regression_guard."""
import json, shutil, sys, tempfile, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import runtime_regression_guard as rg
import runtime_trial as rt
import runtime_snapshot as rs
from unittest.mock import patch
import atexit
_mock_patches=[]
atexit.register(lambda:[p.stop() for p in reversed(_mock_patches)])


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_env():
    """
    Return (root, base, urace) mirroring the real layout:
      root/
        trial/          ← base passed as 'base' arg
        runtime/urace/  ← engine source tree
    """
    root = tempfile.mkdtemp()
    base = Path(root) / 'trial'
    base.mkdir()
    urace = Path(root) / 'runtime' / 'urace'
    urace.mkdir(parents=True)
    (urace / 'cli.py').write_text('# original\n')
    return root, base, urace


def _cleanup(root):
    shutil.rmtree(root, ignore_errors=True)


def _write_benchmark(base, score=60.0):
    (Path(base)/'unit-current.json').write_text(json.dumps(score))

def _deploy(base, score_before=60.0, score_after=66.0):
    # Independent test fixture for the guard's inputs; NEVER calls deploy with numeric scores.
    (Path(base)/'unit-accepted.json').write_text(json.dumps(score_after))

def _unit_current(base):
    p=Path(base)/'unit-current.json';return json.loads(p.read_text()) if p.exists() else None

def _unit_accepted(base):
    p=Path(base)/'unit-accepted.json';return json.loads(p.read_text()) if p.exists() else None

import runtime_quality_gate as _gate
def setUpModule():
    for target,name,fn in ((_gate,'read_latest_score',_unit_current),(rg,'last_accepted_score',_unit_accepted)):
        p=patch.object(target,name,side_effect=fn);p.start();_mock_patches.append(p)

def tearDownModule():
    while _mock_patches:_mock_patches.pop().stop()


# ── check() ──────────────────────────────────────────────────────────────────

class TestCheck(unittest.TestCase):
    def test_unknown_when_no_baseline_and_no_accepted(self):
        root, base, urace = _make_env()
        try:
            result = rg.check(base)
            self.assertEqual(result['status'], 'UNKNOWN')
            self.assertIsNone(result['current_score'])
            self.assertIsNone(result['accepted_score'])
        finally:
            _cleanup(root)

    def test_unknown_when_no_current_score(self):
        root, base, urace = _make_env()
        try:
            # Create a deployment so accepted_score is available
            _deploy(base, 60.0, 66.0)
            # Don't write a current benchmark — current_score will be None
            (base / 'unit-current.json').unlink(missing_ok=True)
            result = rg.check(base)
            self.assertEqual(result['status'], 'UNKNOWN')
            self.assertIsNone(result['current_score'])
            self.assertIsNotNone(result['accepted_score'])
        finally:
            _cleanup(root)

    def test_unknown_when_no_accepted_score(self):
        root, base, urace = _make_env()
        try:
            _write_benchmark(base, 70.0)
            # No deployments → no accepted score
            result = rg.check(base)
            self.assertEqual(result['status'], 'BASELINE_ONLY')
            self.assertIsNotNone(result['current_score'])
            self.assertIsNone(result['accepted_score'])
        finally:
            _cleanup(root)

    def test_ok_when_current_equals_accepted(self):
        root, base, urace = _make_env()
        try:
            _deploy(base, 60.0, 66.0)
            _write_benchmark(base, 66.0)
            result = rg.check(base)
            self.assertEqual(result['status'], 'OK')
            self.assertAlmostEqual(result['delta'], 0.0)
        finally:
            _cleanup(root)

    def test_ok_when_current_above_accepted(self):
        root, base, urace = _make_env()
        try:
            _deploy(base, 60.0, 66.0)
            _write_benchmark(base, 72.0)
            result = rg.check(base)
            self.assertEqual(result['status'], 'OK')
            self.assertGreater(result['delta'], 0)
        finally:
            _cleanup(root)

    def test_regression_when_current_below_accepted(self):
        root, base, urace = _make_env()
        try:
            _deploy(base, 60.0, 66.0)
            _write_benchmark(base, 65.9)  # below accepted 66.0 by 0.1
            result = rg.check(base)
            self.assertEqual(result['status'], 'REGRESSION')
            self.assertLess(result['delta'], 0)
        finally:
            _cleanup(root)

    def test_regression_delta_correct(self):
        root, base, urace = _make_env()
        try:
            _deploy(base, 60.0, 70.0)
            _write_benchmark(base, 65.0)
            result = rg.check(base)
            self.assertEqual(result['status'], 'REGRESSION')
            self.assertAlmostEqual(result['delta'], -5.0)
        finally:
            _cleanup(root)

    def test_schema_field_present(self):
        root, base, urace = _make_env()
        try:
            result = rg.check(base)
            self.assertEqual(result['schema'], rg.SCHEMA)
        finally:
            _cleanup(root)

    def test_checked_at_present(self):
        root, base, urace = _make_env()
        try:
            result = rg.check(base)
            self.assertIn('checked_at', result)
            self.assertTrue(result['checked_at'])
        finally:
            _cleanup(root)


# ── run_guard() ───────────────────────────────────────────────────────────────

class TestRunGuard(unittest.TestCase):
    def test_writes_status_file_always(self):
        root, base, urace = _make_env()
        try:
            rg.run_guard(base)
            self.assertTrue((base / 'runtime-regression-status.json').exists())
        finally:
            _cleanup(root)

    def test_status_file_contains_valid_json(self):
        root, base, urace = _make_env()
        try:
            rg.run_guard(base)
            data = json.loads((base / 'runtime-regression-status.json').read_text())
            self.assertIn('schema', data)
        finally:
            _cleanup(root)

    def test_does_not_write_alert_on_ok(self):
        root, base, urace = _make_env()
        try:
            _deploy(base, 60.0, 66.0)
            _write_benchmark(base, 70.0)
            rg.run_guard(base)
            alert_path = base / 'runtime-regression-alerts.jsonl'
            self.assertFalse(alert_path.exists())
        finally:
            _cleanup(root)

    def test_does_not_write_alert_on_unknown(self):
        root, base, urace = _make_env()
        try:
            rg.run_guard(base)
            alert_path = base / 'runtime-regression-alerts.jsonl'
            self.assertFalse(alert_path.exists())
        finally:
            _cleanup(root)

    def test_writes_alert_on_regression(self):
        root, base, urace = _make_env()
        try:
            _deploy(base, 60.0, 66.0)
            _write_benchmark(base, 60.0)
            rg.run_guard(base)
            alert_path = base / 'runtime-regression-alerts.jsonl'
            self.assertTrue(alert_path.exists())
            lines = [l for l in alert_path.read_text().splitlines() if l.strip()]
            self.assertEqual(len(lines), 1)
            alert = json.loads(lines[0])
            self.assertEqual(alert['status'], 'REGRESSION')
        finally:
            _cleanup(root)

    def test_multiple_regressions_append_alerts(self):
        root, base, urace = _make_env()
        try:
            _deploy(base, 60.0, 66.0)
            _write_benchmark(base, 60.0)
            rg.run_guard(base)
            rg.run_guard(base)
            alert_path = base / 'runtime-regression-alerts.jsonl'
            lines = [l for l in alert_path.read_text().splitlines() if l.strip()]
            self.assertEqual(len(lines), 2)
        finally:
            _cleanup(root)

    def test_returns_check_result(self):
        root, base, urace = _make_env()
        try:
            result = rg.run_guard(base)
            self.assertIn('status', result)
            self.assertIn('schema', result)
        finally:
            _cleanup(root)

    def test_atomic_write_status_file(self):
        """Status file should be valid JSON even if written atomically."""
        root, base, urace = _make_env()
        try:
            rg.run_guard(base)
            status_path = base / 'runtime-regression-status.json'
            # tmp file should not persist
            self.assertFalse(status_path.with_suffix('.tmp').exists())
        finally:
            _cleanup(root)


# ── report() ─────────────────────────────────────────────────────────────────

class TestReport(unittest.TestCase):
    def test_report_no_files(self):
        root, base, urace = _make_env()
        try:
            r = rg.report(base)
            self.assertEqual(r['schema'], rg.SCHEMA)
            self.assertEqual(r['alert_count'], 0)
            self.assertEqual(r['alerts'], [])
            self.assertEqual(r['current_status'], 'UNKNOWN')
        finally:
            _cleanup(root)

    def test_report_reflects_current_status(self):
        root, base, urace = _make_env()
        try:
            _deploy(base, 60.0, 66.0)
            _write_benchmark(base, 70.0)
            rg.run_guard(base)
            r = rg.report(base)
            self.assertEqual(r['current_status'], 'OK')
        finally:
            _cleanup(root)

    def test_report_alert_count(self):
        root, base, urace = _make_env()
        try:
            _deploy(base, 60.0, 66.0)
            _write_benchmark(base, 60.0)
            rg.run_guard(base)
            rg.run_guard(base)
            r = rg.report(base)
            self.assertEqual(r['alert_count'], 2)
        finally:
            _cleanup(root)

    def test_report_alerts_capped_at_five(self):
        root, base, urace = _make_env()
        try:
            _deploy(base, 60.0, 66.0)
            _write_benchmark(base, 60.0)
            for _ in range(7):
                rg.run_guard(base)
            r = rg.report(base)
            self.assertEqual(r['alert_count'], 7)
            self.assertEqual(len(r['alerts']), 5)
        finally:
            _cleanup(root)

    def test_report_schema_field(self):
        root, base, urace = _make_env()
        try:
            r = rg.report(base)
            self.assertEqual(r['schema'], rg.SCHEMA)
        finally:
            _cleanup(root)


if __name__ == '__main__':
    unittest.main()
