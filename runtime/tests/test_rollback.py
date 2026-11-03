"""Tests for urace rollback command."""
import io, json, tempfile, unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch


class RollbackCLITests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def _call(self, extra_args=None):
        from urace import cli
        out = io.StringIO()
        args = ["rollback"] + (extra_args or [])
        with redirect_stdout(out):
            code = cli.main(args)
        return code, out.getvalue()

    def test_rollback_no_config_returns_error(self):
        with patch("urace.cli.load_config", side_effect=FileNotFoundError("no config")):
            code, _ = self._call()
        self.assertEqual(code, 1)

    def test_rollback_no_snapshot_returns_error(self):
        with patch("urace.cli.load_config", return_value={}), \
             patch("urace.cli.stable_path", return_value=self.root / "stable"):
            code, _ = self._call()
        self.assertEqual(code, 1)

    def test_rollback_dry_run_no_writes(self):
        snap_dir = self.root / "stable"
        snap_dir.mkdir(parents=True)
        # Create a fake product file in snapshot
        (snap_dir / "README.md").write_text("old content")
        live_file = self.root / "README.md"
        live_file.write_text("new content")
        manifest = {
            "accepted_at": "2026-01-01T00:00:00",
            "files": {"README.md": "old_hash"},
        }
        (snap_dir / "manifest.json").write_text(json.dumps(manifest))

        with patch("urace.cli.load_config", return_value={}), \
             patch("urace.cli.stable_path", return_value=snap_dir), \
             patch("urace.cli.ROOT", self.root):
            code, out = self._call(["--dry-run"])
        self.assertEqual(code, 0)
        # File should NOT be modified since dry-run
        self.assertEqual(live_file.read_text(), "new content")

    def test_rollback_json_output(self):
        snap_dir = self.root / "stable"
        snap_dir.mkdir(parents=True)
        manifest = {"accepted_at": "2026-01-01T00:00:00", "files": {}}
        (snap_dir / "manifest.json").write_text(json.dumps(manifest))

        with patch("urace.cli.load_config", return_value={}), \
             patch("urace.cli.stable_path", return_value=snap_dir), \
             patch("urace.cli.ROOT", self.root):
            code, out = self._call(["--json"])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertIn("status", data)
        self.assertIn("files", data)


import sys
