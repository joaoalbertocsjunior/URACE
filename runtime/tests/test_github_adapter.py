"""Tests for github_adapter — mocked at the GitHubAdapter boundary."""
import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import MagicMock, patch


def _make_adapter(*, get_repo=None, create_issue=None, dispatch_workflow=None):
    adapter = MagicMock()
    if get_repo is not None:
        adapter.get_repo.return_value = get_repo
    if create_issue is not None:
        adapter.create_issue.return_value = create_issue
    if dispatch_workflow is not None:
        adapter.dispatch_workflow.return_value = dispatch_workflow
    return adapter


class GitHubAdapterProtocolTests(unittest.TestCase):
    def test_urllib_adapter_satisfies_protocol(self):
        from urace.github_adapter import UrllibGitHubAdapter, GitHubAdapter
        a = UrllibGitHubAdapter(token="")
        self.assertIsInstance(a, GitHubAdapter)

    def test_make_github_adapter_returns_urllib_fallback(self):
        from urace.github_adapter import make_github_adapter, UrllibGitHubAdapter
        with patch.dict("sys.modules", {"ghapi": None, "ghapi.all": None}):
            a = make_github_adapter(token="")
        self.assertIsInstance(a, UrllibGitHubAdapter)


class CmdGithubStatusTests(unittest.TestCase):
    def _run(self, github_action, adapter, *, repo="owner/repo", token="tok", extra=None):
        import urace.cli as cli
        args = MagicMock()
        args.command = "github"
        args.github_action = github_action
        args.repo = repo
        args.token_env = "URACE_GITHUB_TOKEN"
        args.json = True
        args.format = None
        if extra:
            for k, v in extra.items():
                setattr(args, k, v)
        out = io.StringIO()
        env = {"URACE_GITHUB_TOKEN": token}
        with patch("urace.github_adapter.make_github_adapter", return_value=adapter), \
             patch.dict("os.environ", env, clear=False), \
             redirect_stdout(out):
            from urace.cli.commands.work import _cmd_github
            code = _cmd_github(args, None, {"github": {"repo": repo}}, {}, "json", [], [])
        return code, json.loads(out.getvalue())

    def test_status_connected(self):
        adapter = _make_adapter(get_repo={
            "default_branch": "main", "open_issues_count": 3,
            "visibility": "public", "html_url": "https://github.com/owner/repo",
        })
        code, data = self._run("status", adapter)
        self.assertEqual(code, 0)
        self.assertTrue(data["connected"])
        self.assertEqual(data["default_branch"], "main")

    def test_status_api_error(self):
        adapter = _make_adapter()
        adapter.get_repo.side_effect = Exception("network error")
        code, data = self._run("status", adapter)
        self.assertEqual(code, 0)
        self.assertFalse(data.get("connected", True))

    def test_push_goals_dry_run(self):
        adapter = _make_adapter()
        state = {"objectives": [{"id": "O-1", "text": "do something", "status": "ACTIVE"}]}
        with patch("urace.cli.commands.work.load_state_for_read", return_value=state):
            args = MagicMock()
            args.command = "github"
            args.github_action = "push-goals"
            args.repo = "owner/repo"
            args.token_env = "URACE_GITHUB_TOKEN"
            args.json = True
            args.format = None
            args.dry_run = True
            out = io.StringIO()
            with patch("urace.github_adapter.make_github_adapter", return_value=adapter), \
                 patch.dict("os.environ", {"URACE_GITHUB_TOKEN": "tok"}, clear=False), \
                 redirect_stdout(out):
                from urace.cli.commands.work import _cmd_github
                code = _cmd_github(args, None, {"github": {"repo": "owner/repo"}}, {}, "json", [], [])
        data = json.loads(out.getvalue())
        self.assertEqual(code, 0)
        self.assertTrue(data["dry_run"])
        adapter.create_issue.assert_not_called()

    def test_trigger_workflow_success(self):
        adapter = _make_adapter(dispatch_workflow=None)
        args = MagicMock()
        args.command = "github"
        args.github_action = "trigger-workflow"
        args.repo = "owner/repo"
        args.token_env = "URACE_GITHUB_TOKEN"
        args.json = True
        args.format = None
        args.workflow = "ci.yml"
        args.ref = "main"
        args.inputs = None
        out = io.StringIO()
        with patch("urace.github_adapter.make_github_adapter", return_value=adapter), \
             patch.dict("os.environ", {"URACE_GITHUB_TOKEN": "tok"}, clear=False), \
             redirect_stdout(out):
            from urace.cli.commands.work import _cmd_github
            code = _cmd_github(args, None, {"github": {"repo": "owner/repo"}}, {}, "json", [], [])
        data = json.loads(out.getvalue())
        self.assertEqual(code, 0)
        self.assertEqual(data["status"], "triggered")
        adapter.dispatch_workflow.assert_called_once_with("owner/repo", "ci.yml", "main", {})
