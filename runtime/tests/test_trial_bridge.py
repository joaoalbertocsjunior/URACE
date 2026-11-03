import io
import json
from contextlib import redirect_stdout
import unittest
from unittest.mock import patch
from urace import cli, trial


class TrialBridgeTests(unittest.TestCase):
    def test_routes_explicit_trial_without_loading_lifecycle_configuration(self):
        with patch.object(cli, "load_config", side_effect=AssertionError("No live configuration")), patch.object(trial, "main", return_value=0) as run:
            self.assertEqual(cli.main(["trial", "status", "resources", "--json"]), 0)
            run.assert_called_once_with(["status", "resources", "--json"])

    def test_passes_literal_arguments_without_shell_and_preserves_exit_code(self):
        with patch.object(trial.Path, "is_file", return_value=True), patch.object(trial.subprocess, "run") as run:
            run.return_value.returncode = 2
            run.return_value.stdout = ""
            run.return_value.stderr = ""
            self.assertEqual(trial.main(["status", "resources", "--product", "$(touch forbidden)"]), 2)
            arguments = run.call_args.args[0]
            self.assertEqual(arguments[-1], "$(touch forbidden)")
            self.assertEqual(run.call_args.kwargs, {"check": False, "capture_output": True, "text": True})

    def test_original_command_preprocessing_still_recognizes_trial(self):
        self.assertEqual(cli._preprocess_args(["trial", "status", "runtime"]), ["trial", "status", "runtime"])

    def test_api_envelope_captures_trial_json(self):
        with patch.object(trial.Path, "is_file", return_value=True), patch.object(trial.subprocess, "run") as run:
            run.return_value.returncode = 0
            run.return_value.stdout = '{"native_calls": 2}\n'
            run.return_value.stderr = ''
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(cli.main(['api', 'call', '--command', 'trial status resources', '--json']), 0)
            self.assertEqual(json.loads(output.getvalue())['output'], {'native_calls': 2})
            self.assertIn('--json', run.call_args.args[0])

    def test_api_discovers_trial_options_and_builds_typed_requests(self):
        from urace import api_interface, trial_cli
        import argparse
        root = argparse.ArgumentParser()
        sub = root.add_subparsers(dest='command')
        sub.add_parser('trial', parents=[trial_cli.build_parser()], add_help=False)
        argv = api_interface.build_argv(root, 'trial status resources', {'product': 'URACE.md', 'executor': 'codex', 'json': True})
        self.assertEqual(argv, ['trial', 'status', 'resources', '--product', 'URACE.md', '--executor', 'codex', '--json'])
        self.assertEqual(root.parse_args(argv).executor, 'codex')
