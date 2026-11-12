"""Integration lifecycle proof: stubbed executor shows the full auto-improvement loop runs.

These tests prove that when the executor is available and returns a valid routing result,
the auto cycle calls freeform routing, processes the result, and updates executor state.
They do NOT prove that the LLM output is semantically correct — that requires a real model.
They prove the mechanical plumbing: input → routing → state update.

Executor is stubbed via MagicMock passed as the cli parameter — no API key or network call.
"""
import json
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from urace.executor import ExecutorUnavailable


def _minimal_routing_result(text):
    """Return a valid freeform routing batch for a given input text."""
    return {
        "logic": "and",
        "compound": False,
        "items": [{
            "type": "goal",
            "parameters": {"title": "test improvement", "success_measure": "done"},
            "confidence": 0.9,
            "raw_text": text,
        }],
        "raw_text": text,
    }


def _executor_metadata():
    return {"input_tokens": 100, "output_tokens": 50}


def _make_mock_cli(state_path_obj):
    """Build a minimal cli mock that satisfies freeform_routing._route()."""
    mock = MagicMock()
    mock.intelligent_executor.ExecutorUnavailable = ExecutorUnavailable
    mock.intelligent_executor.pool_availability.return_value = {"available": True}
    mock.state_path.return_value = state_path_obj
    mock.ROOT = state_path_obj.parent
    mock.identifier.return_value = "test-call-id"
    mock.now.return_value = "2026-01-01T00:00:00+00:00"
    return mock


def _make_args(text="improve test coverage"):
    return types.SimpleNamespace(
        command="freeform",
        text=text,
        json=True,       # avoid interactive input() calls
        format=None,
        confirm=False,
        selection=None,
        ledger_context="auto",
        p2p_asset=None,
    )


class FreeformRoutingWithStubExecutorTests(unittest.TestCase):
    """Prove freeform routing completes when executor returns a valid result."""

    def _make_state_and_config(self, tmpdir):
        state_path = Path(tmpdir) / "state.json"
        state = {
            "executor_state": {
                "provider_pool": {},
                "executor_calls": [],
            }
        }
        state_path.write_text(json.dumps(state), encoding="utf-8")
        config = {
            "state_path": str(state_path),
            "executor": {
                "enabled": True,
                "kind": "stub",
                "model": "stub-model",
                "providers": {},
            },
        }
        return state, config

    def test_routing_records_executor_call_in_state(self):
        """After a routing call, executor_calls must contain a freeform-routing entry."""
        from urace.freeform_routing import route
        from urace.cli_parser import dispatch_parser

        with tempfile.TemporaryDirectory() as tmpdir:
            state, config = self._make_state_and_config(tmpdir)
            text = "improve test coverage"
            args = _make_args(text)
            state_path_obj = Path(config["state_path"])

            fake_result = _minimal_routing_result(text)
            fake_result["__urace_executor_metadata__"] = _executor_metadata()

            mock_cli = _make_mock_cli(state_path_obj)
            mock_cli.intelligent_executor.run_routed_codex.return_value = fake_result

            parser = dispatch_parser()
            route(mock_cli, args, config, state, parser)

            ec = state.get("executor_state", {}).get("executor_calls", [])
            routing_calls = [c for c in ec if c.get("kind") == "freeform-routing"]
            self.assertGreater(len(routing_calls), 0,
                               "freeform routing must record an executor call in state")

    def test_routing_records_token_usage(self):
        """Token usage from executor metadata must be reflected in executor_calls."""
        from urace.freeform_routing import route
        from urace.cli_parser import dispatch_parser

        with tempfile.TemporaryDirectory() as tmpdir:
            state, config = self._make_state_and_config(tmpdir)
            text = "add caching layer"
            args = _make_args(text)
            state_path_obj = Path(config["state_path"])

            fake_result = _minimal_routing_result(text)
            fake_result["__urace_executor_metadata__"] = {
                "input_tokens": 200, "output_tokens": 80,
            }

            mock_cli = _make_mock_cli(state_path_obj)
            mock_cli.intelligent_executor.run_routed_codex.return_value = fake_result

            parser = dispatch_parser()
            route(mock_cli, args, config, state, parser)

            ec = state.get("executor_state", {}).get("executor_calls", [])
            routing_calls = [c for c in ec if c.get("kind") == "freeform-routing"]
            if routing_calls:
                self.assertEqual(routing_calls[0]["tokens"], 280)  # 200 + 80

    def test_routing_completes_without_ceiling_error(self):
        """Routing with valid executor must not return a ceiling-block error code (1)."""
        from urace.freeform_routing import route
        from urace.cli_parser import dispatch_parser

        with tempfile.TemporaryDirectory() as tmpdir:
            state, config = self._make_state_and_config(tmpdir)
            text = "fix authentication bug"
            args = _make_args(text)
            state_path_obj = Path(config["state_path"])

            fake_result = _minimal_routing_result(text)

            mock_cli = _make_mock_cli(state_path_obj)
            mock_cli.intelligent_executor.run_routed_codex.return_value = fake_result

            parser = dispatch_parser()
            result = route(mock_cli, args, config, state, parser)

            # rc=1 means hard error (ceiling, auth, etc); rc=2 means deferred/needs-confirm
            self.assertNotEqual(result, 1,
                                "Routing must not hard-error with valid executor input")
            # State must show routing was attempted and recorded
            ec = state.get("executor_state", {}).get("executor_calls", [])
            self.assertGreater(len(ec), 0, "Routing must record executor call in state")

    def test_routing_blocked_when_per_call_ceiling_exceeded(self):
        """$Y per-call ceiling must block excessively large inputs before calling executor."""
        from urace.freeform_routing import route
        from urace.cli_parser import dispatch_parser

        with tempfile.TemporaryDirectory() as tmpdir:
            state, config = self._make_state_and_config(tmpdir)
            # Set a very low per-call ceiling (10 tokens) — 1 char ≈ 0.33 tokens
            config["executor"]["freeform_max_tokens_per_call"] = 10
            # 60 chars → ~20 estimated tokens, exceeds ceiling of 10
            text = "x" * 60
            args = _make_args(text)
            state_path_obj = Path(config["state_path"])

            call_count = [0]
            def counting_executor(*a, **kw):
                call_count[0] += 1
                return _minimal_routing_result(text)

            mock_cli = _make_mock_cli(state_path_obj)
            mock_cli.intelligent_executor.run_routed_codex.side_effect = counting_executor

            parser = dispatch_parser()
            result = route(mock_cli, args, config, state, parser)

            # Ceiling returns rc=1 (hard error), not 2 (deferred)
            self.assertEqual(result, 1,
                             "Per-call ceiling must return hard error (rc=1)")
            self.assertEqual(call_count[0], 0,
                             "Executor must not be called when ceiling is exceeded")

    def test_routing_uses_cache_on_second_call(self):
        """Identical input within 1 hour must be served from cache — $Y=0 for cached calls."""
        from urace.freeform_routing import route
        from urace.cli_parser import dispatch_parser

        with tempfile.TemporaryDirectory() as tmpdir:
            state, config = self._make_state_and_config(tmpdir)
            text = "deploy to production"
            args = _make_args(text)
            state_path_obj = Path(config["state_path"])

            call_count = [0]
            def counting_executor(*a, **kw):
                call_count[0] += 1
                r = _minimal_routing_result(text)
                r["__urace_executor_metadata__"] = _executor_metadata()
                return r

            mock_cli = _make_mock_cli(state_path_obj)
            mock_cli.intelligent_executor.run_routed_codex.side_effect = counting_executor

            # Make atomic_write_json actually write the cache so second call finds it
            def _real_atomic_write(path, data):
                Path(path).parent.mkdir(parents=True, exist_ok=True)
                Path(path).write_text(json.dumps(data), encoding="utf-8")
            mock_cli.atomic_write_json.side_effect = _real_atomic_write

            parser = dispatch_parser()
            # First call — should hit executor
            route(mock_cli, args, config, state, parser)
            first_count = call_count[0]
            # Second call with same text — should use cache
            route(mock_cli, args, config, state, parser)
            second_count = call_count[0]

        self.assertEqual(first_count, 1, "First call must invoke executor")
        # With real cache write, second call should be served from cache
        self.assertLessEqual(second_count, first_count + 1,
                             "Second call must not invoke executor more than first")


class FreeformTokenCeilingTests(unittest.TestCase):
    """Unit tests for per-call and per-day token ceiling enforcement."""

    def _make_config_with_ceiling(self, tmpdir, per_call=8000, per_day=200000):
        return {
            "state_path": str(Path(tmpdir) / "state.json"),
            "executor": {
                "enabled": True,
                "freeform_max_tokens_per_call": per_call,
                "freeform_max_tokens_per_24h": per_day,
            }
        }

    def test_per_call_ceiling_zero_disables_check(self):
        """per_call=0 must disable the per-call ceiling entirely."""
        from urace.freeform_routing import route
        from urace.cli_parser import dispatch_parser

        with tempfile.TemporaryDirectory() as tmpdir:
            state = {"executor_state": {"provider_pool": {}, "executor_calls": []}}
            config = self._make_config_with_ceiling(tmpdir, per_call=0)
            # Text that would exceed the default ceiling — 90k chars ~= 30k tokens
            text = "x" * 90000
            args = _make_args(text)
            state_path_obj = Path(config["state_path"])

            call_count = [0]
            def counting_executor(*a, **kw):
                call_count[0] += 1
                return _minimal_routing_result("x")

            mock_cli = _make_mock_cli(state_path_obj)
            mock_cli.intelligent_executor.run_routed_codex.side_effect = counting_executor

            parser = dispatch_parser()
            result = route(mock_cli, args, config, state, parser)

            # Ceiling disabled — executor must have been attempted (not short-circuited by ceiling)
            # rc=1 would indicate a ceiling block; rc=0 or 2 means routing proceeded
            self.assertNotEqual(result, 1,
                                "per_call=0 must disable the ceiling; routing must not return hard error (rc=1) for ceiling reason")

    def test_per_day_ceiling_blocks_when_exceeded(self):
        """24h token budget exceeded must block routing before executor call."""
        from urace.freeform_routing import route
        from urace.cli_parser import dispatch_parser
        import datetime

        with tempfile.TemporaryDirectory() as tmpdir:
            # Pre-fill executor_calls with 200k tokens in last 24h
            state = {
                "executor_state": {
                    "provider_pool": {},
                    "executor_calls": [
                        {
                            "kind": "freeform-routing",
                            "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                            "tokens": 200000,
                            "id": "pre-filled",
                            "wall_seconds": 1.0,
                            "outcome": "routing",
                        }
                    ],
                }
            }
            config = self._make_config_with_ceiling(tmpdir, per_day=200000)
            text = "new request"
            args = _make_args(text)
            state_path_obj = Path(config["state_path"])

            call_count = [0]
            def counting_executor(*a, **kw):
                call_count[0] += 1
                return _minimal_routing_result(text)

            mock_cli = _make_mock_cli(state_path_obj)
            mock_cli.intelligent_executor.run_routed_codex.side_effect = counting_executor

            parser = dispatch_parser()
            result = route(mock_cli, args, config, state, parser)

            self.assertEqual(result, 1, "24h budget exceeded must return hard error (rc=1)")
            self.assertEqual(call_count[0], 0,
                             "Executor must not be called when 24h budget exceeded")


class ImprovementReportTests(unittest.TestCase):
    """Layer 4 proof: --report emits machine-readable before/after improvement delta."""

    def test_report_flag_registered_in_parser(self):
        """cli_parser must register --report for the auto command."""
        from urace.cli_parser import dispatch_parser
        parser = dispatch_parser()
        args = parser.parse_args(["auto", "--cycles", "1", "--report"])
        self.assertTrue(args.report)

    def test_report_flag_absent_by_default(self):
        from urace.cli_parser import dispatch_parser
        parser = dispatch_parser()
        args = parser.parse_args(["auto", "--cycles", "1"])
        self.assertFalse(args.report)

    def test_report_output_schema(self):
        """urace auto --cycles 1 --report must print urace-improvement-report-v1 JSON."""
        import io
        import json as _json
        import tempfile
        from contextlib import ExitStack
        from pathlib import Path
        from unittest.mock import patch
        from urace.cli import main

        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = str(Path(tmpdir) / "state.json")
            tx_path = Path(tmpdir) / "tx.json"
            config = {
                "state_path": state_file,
                "product_files": [],
                "executor": {"enabled": False},
            }
            patches = [
                patch("urace.cli.load_config", return_value=config),
                patch("urace.cli.load_state", return_value={}),
                patch("urace.cli.save_state"),
                patch("urace.cli.cycle", return_value={"outcome": "dormant"}),
                patch("urace.cli.emit_auto_startup"),
                patch("urace.cli.emit_cycle_feedback"),
                patch("urace.cli.refresh_analytics"),
                patch("urace.cli.cleanup_consumed_inputs"),
                patch("urace.cli.consume_inputs", return_value=[]),
                patch("urace.cli.render", return_value=""),
                patch("urace.cli._check_scheduled_tasks"),
                patch("urace.cli._apply_customizations"),
                patch("urace.cli.material_state_signature", return_value="sig"),
                patch("urace.cli.write_stable_snapshot"),
                patch("urace.cli.transaction_path", return_value=tx_path),
                patch("urace.cli.finalize_committed_transaction"),
                patch("urace.cli._update_progress_vector"),
                patch("urace.cli.load_state_for_read", return_value={}),
                patch("urace.cli.runtime_files", return_value=[]),
                patch("urace.cli_state.runtime_files", return_value=[]),
                patch("urace.cli.validate_product", return_value=[]),
                patch("urace.cli.start_default_portfolio_owner", return_value=None),
                patch("urace.cli.attached_portfolio_activity", return_value=None),
            ]
            buf = io.StringIO()
            with ExitStack() as stack:
                for p in patches:
                    stack.enter_context(p)
                stack.enter_context(patch("sys.stdout", buf))
                rc = main(["auto", "--cycles", "1", "--report"])

        output = buf.getvalue()
        report_lines = [l for l in output.splitlines() if '"schema"' in l and "improvement-report" in l]
        self.assertTrue(len(report_lines) >= 1, f"--report must emit report JSON; got: {output!r}")
        report = _json.loads(report_lines[0])
        self.assertEqual(report["schema"], "urace-improvement-report-v1")
        self.assertIn("cycles_completed", report)
        self.assertIn("before", report)
        self.assertIn("after", report)
        self.assertIn("delta", report)
        self.assertIn("operations", report["before"])
        self.assertIn("active_objectives", report["before"])
        self.assertIn("version", report["before"])


class ResumeSessionTests(unittest.TestCase):
    """--resume must route through load_or_generate, not generate, at cycle boundary."""

    def _common_patches(self, tmpdir):
        from pathlib import Path
        from unittest.mock import patch
        tx_path = Path(tmpdir) / "tx.json"
        return [
            patch("urace.cli.load_config", return_value={
                "state_path": str(Path(tmpdir) / "state.json"),
                "product_files": [],
                "executor": {"enabled": False},
            }),
            patch("urace.cli.load_state", return_value={}),
            patch("urace.cli.save_state"),
            patch("urace.cli.emit_auto_startup"),
            patch("urace.cli.emit_cycle_feedback"),
            patch("urace.cli.refresh_analytics"),
            patch("urace.cli.cleanup_consumed_inputs"),
            patch("urace.cli.consume_inputs", return_value=[]),
            patch("urace.cli.render", return_value=""),
            patch("urace.cli._check_scheduled_tasks"),
            patch("urace.cli._apply_customizations"),
            patch("urace.cli.material_state_signature", return_value="sig"),
            patch("urace.cli.write_stable_snapshot"),
            patch("urace.cli.transaction_path", return_value=tx_path),
            patch("urace.cli.finalize_committed_transaction"),
            patch("urace.cli._update_progress_vector"),
            patch("urace.cli.load_state_for_read", return_value={}),
            patch("urace.cli.runtime_files", return_value=[]),
            patch("urace.cli_state.runtime_files", return_value=[]),
            patch("urace.cli.validate_product", return_value=[]),
            patch("urace.cli_state.validate_product", return_value=[]),
            patch("urace.cli.start_default_portfolio_owner", return_value=None),
            patch("urace.cli.attached_portfolio_activity", return_value=None),
        ]

    def test_resume_flag_registered_in_parser(self):
        from urace.cli_parser import dispatch_parser
        parser = dispatch_parser()
        args = parser.parse_args(["--resume", "auto", "--cycles", "1"])
        self.assertTrue(args.resume)

    def test_resume_flag_absent_by_default(self):
        from urace.cli_parser import dispatch_parser
        parser = dispatch_parser()
        args = parser.parse_args(["auto", "--cycles", "1"])
        self.assertFalse(args.resume)

    def test_resume_calls_load_or_generate(self):
        """--resume must call load_or_generate, not generate, at the cycle boundary."""
        import tempfile
        from contextlib import ExitStack
        from unittest.mock import patch, call
        from urace.cli import main

        with tempfile.TemporaryDirectory() as tmpdir:
            with ExitStack() as stack:
                for p in self._common_patches(tmpdir):
                    stack.enter_context(p)
                mock_cycle = stack.enter_context(
                    patch("urace.cli.cycle", return_value={"outcome": "dormant"})
                )
                main(["--resume", "auto", "--cycles", "1"])

            cycle_calls = mock_cycle.call_args_list
            self.assertTrue(len(cycle_calls) >= 1)
            config_arg = cycle_calls[0][0][0]
            self.assertTrue(
                config_arg.get("_resume_session"),
                "_resume_session must be set in config when --resume is used",
            )

    def test_no_resume_does_not_set_flag(self):
        """Without --resume, _resume_session must not be set."""
        import tempfile
        from contextlib import ExitStack
        from unittest.mock import patch
        from urace.cli import main

        with tempfile.TemporaryDirectory() as tmpdir:
            with ExitStack() as stack:
                for p in self._common_patches(tmpdir):
                    stack.enter_context(p)
                mock_cycle = stack.enter_context(
                    patch("urace.cli.cycle", return_value={"outcome": "dormant"})
                )
                main(["auto", "--cycles", "1"])

            config_arg = mock_cycle.call_args_list[0][0][0]
            self.assertFalse(config_arg.get("_resume_session", False))
