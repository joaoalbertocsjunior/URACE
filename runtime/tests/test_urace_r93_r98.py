import copy
import io
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from urace import cli, compaction as compaction_module

TEST_RUNTIME_ROOT = Path(__file__).resolve().parents[1]
TEST_PRODUCT_ROOT = Path(__file__).resolve().parents[3]


def isolated_test_config(test_case):
    """Keep lifecycle writes away from the configured installation state."""
    config = copy.deepcopy(cli.load_config())
    directory = tempfile.TemporaryDirectory(prefix='urace-test-state-')
    test_case.addCleanup(directory.cleanup)
    config['state_path'] = str(Path(directory.name) / 'state.json')
    return config


class R93ExternalInterfaceTests(unittest.TestCase):
    """r93 §62w ExternalInterfaceProtocol — api command + feedback --input-json."""

    def setUp(self):
        self.config = isolated_test_config(self)
        self.config["executor"]["enabled"] = False
        self.config.setdefault("product", "TestProduct")
        self.config.setdefault("intent", {})
        self.config["intent"]["purpose"] = "Test"

    def _run(self, argv, state=None):
        import tempfile
        out = io.StringIO()
        with tempfile.TemporaryDirectory() as tmpdir:
            config = copy.deepcopy(self.config)
            config["state_path"] = f"{tmpdir}/state.json"
            s = state if state is not None else cli.initial_state(config)
            cli.seed_confirmed_onboard(config, s)
            cli.save_state(config, s)
            with patch.object(cli, "load_config", return_value=config), \
                 patch("urace.cli.commands.work.load_config", return_value=config), \
                 patch("urace.cli.commands.work.load_state_for_read", side_effect=lambda c: cli.load_state_for_read(c)), \
                 redirect_stdout(out):
                rc = cli.main(argv)
        return rc, out.getvalue()

    # ── api help ─────────────────────────────────────────────────────────────

    def test_api_help_exits_0(self):
        """api help → rc=0."""
        rc, out = self._run(["api", "help"])
        self.assertEqual(rc, 0)

    def test_api_help_json(self):
        """api help --json → rc=0, JSON with guide field."""
        rc, out = self._run(["api", "help", "--json"])
        self.assertEqual(rc, 0)
        result = json.loads(out)
        self.assertIn("guide", result)

    # ── api call ─────────────────────────────────────────────────────────────

    def test_api_call_check(self):
        """api call --command check --json → rc=0, output.command==check."""
        rc, out = self._run(["api", "call", "--command", "check", "--json"])
        self.assertEqual(rc, 0)
        result = json.loads(out)
        self.assertEqual(result["command"], "check")
        self.assertEqual(result["exit_code"], 0)

    def test_api_call_missing_command_returns_error(self):
        """api call without --command → rc=1."""
        rc, _out = self._run(["api", "call", "--json"])
        self.assertEqual(rc, 1)

    def test_api_call_slash_prefix_resolved(self):
        """api call --command /check → routes to check handler."""
        rc, out = self._run(["api", "call", "--command", "/check", "--json"])
        self.assertEqual(rc, 0)
        result = json.loads(out)
        self.assertEqual(result["command"], "check")

    # ── api batch ────────────────────────────────────────────────────────────

    def test_api_batch_stdin(self):
        """api batch --input-json - from stdin → executes entries, returns results array."""
        import tempfile
        batch = json.dumps([{"command": "check", "params": {}}, {"command": "vitals", "params": {}}])
        with tempfile.TemporaryDirectory() as tmpdir:
            config = copy.deepcopy(self.config)
            config["state_path"] = f"{tmpdir}/state.json"
            s = cli.initial_state(config)
            cli.seed_confirmed_onboard(config, s)
            cli.save_state(config, s)
            out = io.StringIO()
            with patch.object(cli, "load_config", return_value=config), \
                 patch("sys.stdin", io.StringIO(batch)), \
                 redirect_stdout(out):
                rc = cli.main(["api", "batch", "--input-json", "-", "--json"])
        self.assertEqual(rc, 0)
        result = json.loads(out.getvalue())
        self.assertIn("results", result)
        self.assertEqual(len(result["results"]), 2)

    def test_api_batch_missing_input_returns_error(self):
        """api batch without --input-json → rc=1."""
        rc, _out = self._run(["api", "batch", "--json"])
        self.assertEqual(rc, 1)

    # ── feedback --input-json ─────────────────────────────────────────────────

    def test_feedback_submit_input_json(self):
        """feedback submit with --input-json file → creates OutcomeFeedbackRecord."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            config = copy.deepcopy(self.config)
            config["state_path"] = f"{tmpdir}/state.json"
            s = cli.initial_state(config)
            cli.seed_confirmed_onboard(config, s)
            # add a fake objective to submit against
            s.setdefault("objectives", []).append({"id": "obj-test001", "title": "T"})
            cli.save_state(config, s)
            params_file = f"{tmpdir}/params.json"
            with open(params_file, "w") as f:
                json.dump({"signal": "POSITIVE", "detail": "automated test"}, f)
            out = io.StringIO()
            with patch.object(cli, "load_config", return_value=config), \
                 redirect_stdout(out):
                rc = cli.main(["feedback", "submit", "obj-test001",
                               "--input-json", params_file, "--json"])
            self.assertEqual(rc, 0)
            result = json.loads(out.getvalue())
            self.assertIn("id", result)
            saved = cli.load_state_for_read(config)
            records = (saved or {}).get("outcome_feedback_records", [])
            self.assertTrue(any(r.get("signal") == "POSITIVE" for r in records))

    def test_feedback_submit_input_json_missing_signal(self):
        """feedback submit --input-json without signal field → rc=1."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            config = copy.deepcopy(self.config)
            config["state_path"] = f"{tmpdir}/state.json"
            s = cli.initial_state(config)
            cli.seed_confirmed_onboard(config, s)
            cli.save_state(config, s)
            params_file = f"{tmpdir}/params.json"
            with open(params_file, "w") as f:
                json.dump({"detail": "missing signal"}, f)
            out = io.StringIO()
            with patch.object(cli, "load_config", return_value=config), \
                 redirect_stdout(out):
                rc = cli.main(["feedback", "submit", "obj-test001",
                               "--input-json", params_file, "--json"])
            self.assertEqual(rc, 1)


class R98ApiExtensionsTests(unittest.TestCase):
    def setUp(self):
        self.config = isolated_test_config(self)
        self.config["executor"]["enabled"] = False
        self.config.setdefault("product", "TestProduct")
        self.config.setdefault("intent", {})
        self.config["intent"]["purpose"] = "Test"

    def _state_with_traces(self):
        return {
            "trace_records": [
                {"id": "tr-1", "kind": "CYCLE", "at": "2026-01-01T00:00:00", "detail": "cycle1"},
                {"id": "tr-2", "kind": "GAP", "at": "2026-01-02T00:00:00", "detail": "gap1"},
            ]
        }

    def _run(self, argv, extra_state=None):
        out = io.StringIO()
        with tempfile.TemporaryDirectory() as tmpdir:
            config = copy.deepcopy(self.config)
            config["state_path"] = f"{tmpdir}/state.json"
            s = cli.initial_state(config)
            cli.seed_confirmed_onboard(config, s)
            if extra_state:
                s.update(extra_state)
            cli.save_state(config, s)
            with patch.object(cli, "load_config", return_value=config), \
                 redirect_stdout(out):
                rc = cli.main(argv)
        return rc, out.getvalue()

    def test_api_version_json(self):
        rc, out = self._run(["api", "version", "--json"])
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertIn("spec_version", data)
        self.assertEqual(data["api_version"], "1")

    def test_api_version_plain(self):
        rc, out = self._run(["api", "version"])
        self.assertEqual(rc, 0)
        self.assertIn("api_version: 1", out)

    def test_api_watch_no_filter(self):
        traces = self._state_with_traces()
        rc, out = self._run(["api", "watch"], extra_state=traces)
        self.assertEqual(rc, 0)
        lines = [l for l in out.strip().split("\n") if l]
        self.assertEqual(len(lines), 2)

    def test_api_watch_kind_filter(self):
        traces = self._state_with_traces()
        rc, out = self._run(["api", "watch", "--kinds", "CYCLE"], extra_state=traces)
        self.assertEqual(rc, 0)
        lines = [l for l in out.strip().split("\n") if l]
        self.assertEqual(len(lines), 1)
        self.assertEqual(json.loads(lines[0])["kind"], "CYCLE")

    def test_api_watch_since_filter(self):
        traces = self._state_with_traces()
        rc, out = self._run(["api", "watch", "--since", "2026-01-02T00:00:00"], extra_state=traces)
        self.assertEqual(rc, 0)
        lines = [l for l in out.strip().split("\n") if l]
        self.assertEqual(len(lines), 1)
        self.assertEqual(json.loads(lines[0])["kind"], "GAP")

    def test_api_watch_sd_true_routing(self):
        traces = self._state_with_traces()
        rc, out = self._run(["api", "watch", "--kinds", "GAP"], extra_state=traces)
        self.assertEqual(rc, 0)

    def test_api_version_in_sd_true_exact(self):
        from urace.cli import _SD_TRUE_EXACT
        self.assertIn("api version", _SD_TRUE_EXACT)
        self.assertIn("api watch", _SD_TRUE_EXACT)


class R98IntegrityTests(unittest.TestCase):
    def test_spec_hash_gap_kinds_registered(self):
        from urace.cli import IGC_KINDS
        self.assertIn("spec-update-hash-mismatch", IGC_KINDS)
        self.assertIn("manifest-hash-mismatch", IGC_KINDS)
