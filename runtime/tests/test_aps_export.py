"""Tests for APS export/import CLI subcommands."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

RUNTIME = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RUNTIME))


class TestApsExport(unittest.TestCase):
    def _run(self, argv):
        from urace.cli import main
        return main(argv)

    def test_export_creates_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out = os.path.join(tmpdir, 'out.aps.json')
            sp = Path(tmpdir) / 'state.json'
            with patch('urace.cli.load_config', return_value={}), \
                 patch('urace.cli.state_path', return_value=sp):
                rc = self._run(['export', '--out', out])
            self.assertEqual(rc, 0)
            self.assertTrue(os.path.exists(out))
            payload = json.loads(Path(out).read_text())
            self.assertEqual(payload['schema'], 'urace-aps-v1')
            self.assertIn('turns', payload)

    def test_export_json_flag(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out = os.path.join(tmpdir, 'out.aps.json')
            sp = Path(tmpdir) / 'state.json'
            with patch('urace.cli.load_config', return_value={}), \
                 patch('urace.cli.state_path', return_value=sp):
                import io
                from contextlib import redirect_stdout
                buf = io.StringIO()
                with redirect_stdout(buf):
                    rc = self._run(['--json', 'export', '--out', out])
            self.assertEqual(rc, 0)
            result = json.loads(buf.getvalue())
            self.assertEqual(result['status'], 'ok')

    def test_import_nonexistent_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sp = Path(tmpdir) / 'state.json'
            with patch('urace.cli.load_config', return_value={}), \
                 patch('urace.cli.state_path', return_value=sp):
                rc = self._run(['import', '/nonexistent/path/file.aps.json'])
        self.assertEqual(rc, 1)

    def test_import_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out = os.path.join(tmpdir, 'roundtrip.aps.json')
            payload = {"schema": "urace-aps-v1", "exported_at": "2026-01-01T00:00:00Z",
                       "turns": [{"role": "user", "text": "hello"}]}
            Path(out).write_text(json.dumps(payload))
            sp = Path(tmpdir) / 'state.json'
            with patch('urace.cli.load_config', return_value={}), \
                 patch('urace.cli.state_path', return_value=sp):
                rc = self._run(['import', out])
            self.assertEqual(rc, 0)
            session_file = Path(tmpdir) / 'session_context.jsonl'
            self.assertTrue(session_file.exists())
            lines = [json.loads(l) for l in session_file.read_text().splitlines() if l.strip()]
            self.assertEqual(len(lines), 1)
            self.assertEqual(lines[0]['text'], 'hello')

    def test_export_with_existing_session(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sp = Path(tmpdir) / 'state.json'
            session_file = Path(tmpdir) / 'session_context.jsonl'
            session_file.write_text(json.dumps({"role": "user", "text": "hi"}) + "\n")
            out = os.path.join(tmpdir, 'out.aps.json')
            with patch('urace.cli.load_config', return_value={}), \
                 patch('urace.cli.state_path', return_value=sp):
                rc = self._run(['export', '--out', out])
            self.assertEqual(rc, 0)
            payload = json.loads(Path(out).read_text())
            self.assertEqual(len(payload['turns']), 1)


if __name__ == '__main__':
    unittest.main()
