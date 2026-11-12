"""Tests for urace.portfolio_github — git workflow helpers."""
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock


class WorkflowSettingsTests(unittest.TestCase):
    def test_defaults_applied_when_config_empty(self):
        from urace.portfolio_github import workflow_settings, WORKFLOW_DEFAULTS
        result = workflow_settings({})
        for key, val in WORKFLOW_DEFAULTS.items():
            self.assertEqual(result[key], val)

    def test_config_overrides_defaults(self):
        from urace.portfolio_github import workflow_settings
        result = workflow_settings({"github_workflow": {"auto_pull": False}})
        self.assertFalse(result["auto_pull"])

    def test_none_values_in_config_ignored(self):
        from urace.portfolio_github import workflow_settings
        result = workflow_settings({"github_workflow": {"auto_pull": None}})
        self.assertTrue(result["auto_pull"])

    def test_missing_github_workflow_key(self):
        from urace.portfolio_github import workflow_settings
        result = workflow_settings({"other_key": "value"})
        self.assertIn("auto_pull", result)


class ValidateSubcommandTests(unittest.TestCase):
    def test_allowed_subcommand_returns_none(self):
        from urace.portfolio_github import validate_subcommand
        self.assertIsNone(validate_subcommand(["status"]))

    def test_disallowed_subcommand_returns_error(self):
        from urace.portfolio_github import validate_subcommand
        result = validate_subcommand(["rm"])
        self.assertIsNotNone(result)
        self.assertIn("rm", result)

    def test_empty_args_returns_error(self):
        from urace.portfolio_github import validate_subcommand
        result = validate_subcommand([])
        self.assertIsNotNone(result)

    def test_all_safe_subcommands_pass(self):
        from urace.portfolio_github import validate_subcommand, SAFE_GIT_SUBCOMMANDS
        for cmd in SAFE_GIT_SUBCOMMANDS:
            self.assertIsNone(validate_subcommand([cmd]))


class HeadCommitTests(unittest.TestCase):
    def test_returns_sha_on_success(self):
        from urace.portfolio_github import head_commit
        fake = MagicMock()
        fake.returncode = 0
        fake.stdout = "abc123def456\n"
        fake.stderr = ""
        with patch("subprocess.run", return_value=fake):
            result = head_commit("/some/path")
        self.assertEqual(result, "abc123def456")

    def test_returns_none_on_failure(self):
        from urace.portfolio_github import head_commit
        fake = MagicMock()
        fake.returncode = 128
        fake.stdout = ""
        fake.stderr = "not a git repo"
        with patch("subprocess.run", return_value=fake):
            result = head_commit("/no/git/here")
        self.assertIsNone(result)


class AutoPullTests(unittest.TestCase):
    def test_skipped_when_disabled(self):
        from urace.portfolio_github import auto_pull
        result = auto_pull("/path", {"github_workflow": {"auto_pull": False}})
        self.assertTrue(result["skipped"])
        self.assertEqual(result["reason"], "auto_pull disabled")

    def test_skipped_when_path_missing(self):
        from urace.portfolio_github import auto_pull
        result = auto_pull("/nonexistent/path/xyz", {})
        self.assertTrue(result["skipped"])

    def test_ok_on_successful_pull(self):
        from urace.portfolio_github import auto_pull
        fake = MagicMock(returncode=0, stdout="Already up to date.", stderr="")
        with tempfile.TemporaryDirectory() as d:
            with patch("subprocess.run", return_value=fake):
                result = auto_pull(d, {})
        self.assertFalse(result["skipped"])
        self.assertTrue(result["ok"])


class AutoCommitTests(unittest.TestCase):
    def test_skipped_when_disabled(self):
        from urace.portfolio_github import auto_commit
        result = auto_commit("/path", {})
        self.assertTrue(result["skipped"])
        self.assertIn("auto_commit disabled", result["reason"])

    def test_message_uses_cycle_id(self):
        from urace.portfolio_github import auto_commit
        fake = MagicMock(returncode=0, stdout="[main abc123] feat: ...", stderr="")
        with tempfile.TemporaryDirectory() as d:
            with patch("subprocess.run", return_value=fake):
                result = auto_commit(d, {"github_workflow": {"auto_commit": True}},
                                     cycle_id="cycle-42")
        self.assertIn("cycle-42", result["message"])


class AutoPushTests(unittest.TestCase):
    def test_skipped_by_default(self):
        from urace.portfolio_github import auto_push
        result = auto_push("/path", {})
        self.assertTrue(result["skipped"])
        self.assertIn("auto_push disabled", result["reason"])
