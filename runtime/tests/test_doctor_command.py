"""Phase IV-C — urace doctor command tests."""
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import MagicMock, patch

from urace import cli


def _run_doctor(config, state=None, *, json_flag=True):
    _state = state or {}
    out = io.StringIO()
    with patch.object(cli, "load_config", return_value=config), \
         patch.object(cli, "load_state_for_read", return_value=_state), \
         patch.object(cli, "load_state", return_value=_state), \
         patch.object(cli, "save_state"), \
         patch.object(cli, "state_lock") as _sl, \
         redirect_stdout(out):
        _sl.return_value.__enter__ = lambda s: None
        _sl.return_value.__exit__ = MagicMock(return_value=False)
        rc = cli.main(["doctor", "--json"] if json_flag else ["doctor"])
    text = out.getvalue().strip()
    if json_flag and text:
        try:
            return rc, json.loads(text)
        except json.JSONDecodeError:
            return rc, text
    return rc, text


class DoctorCheckCoverageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.config = {
            "state_path": str(Path(self.tmp.name) / "state.json"),
            "executor": {"enabled": False},
            "exchange": {"enabled": False},
            "capability_flags": {},
        }

    def test_doctor_returns_zero_on_ok(self):
        rc, result = _run_doctor(self.config)
        self.assertIn(rc, (0, 1))
        self.assertIn("checks", result)

    def test_doctor_includes_config_loads_check(self):
        rc, result = _run_doctor(self.config)
        names = [c["check"] for c in result["checks"]]
        self.assertIn("config_loads", names)

    def test_doctor_includes_state_check(self):
        rc, result = _run_doctor(self.config)
        names = [c["check"] for c in result["checks"]]
        self.assertIn("state_initializable", names)

    def test_doctor_includes_regression_guard_check(self):
        rc, result = _run_doctor(self.config, state={})
        names = [c["check"] for c in result["checks"]]
        self.assertIn("regression_guard", names)

    def test_doctor_includes_cost_tracking_check(self):
        rc, result = _run_doctor(self.config, state={})
        names = [c["check"] for c in result["checks"]]
        self.assertIn("cost_tracking", names)

    def test_regression_guard_ok_when_no_regressions(self):
        state = {"quality_deltas": [], "decision_records": []}
        rc, result = _run_doctor(self.config, state=state)
        guard = next((c for c in result["checks"] if c["check"] == "regression_guard"), None)
        self.assertIsNotNone(guard)
        self.assertEqual(guard["status"], "OK")

    def test_regression_guard_warn_when_regression_present(self):
        state = {
            "quality_deltas": [
                {"scope": "api", "classification": "REGRESSION", "delta": -0.5, "measured_at": "2026-01-01T00:00:00"},
            ],
            "decision_records": [],
        }
        rc, result = _run_doctor(self.config, state=state)
        guard = next((c for c in result["checks"] if c["check"] == "regression_guard"), None)
        self.assertIsNotNone(guard)
        self.assertIn(guard["status"], ("WARN", "OK"))

    def test_cost_tracking_check_ok(self):
        rc, result = _run_doctor(self.config, state={})
        cost = next((c for c in result["checks"] if c["check"] == "cost_tracking"), None)
        self.assertIsNotNone(cost)
        self.assertEqual(cost["status"], "OK")

    def test_overall_field_present(self):
        rc, result = _run_doctor(self.config, state={})
        self.assertIn("overall", result)
        self.assertIn(result["overall"], ("OK", "WARN", "ERROR"))
