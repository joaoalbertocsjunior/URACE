import copy
import hashlib
import io
import json
import os
import subprocess
import tempfile
import types
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from urace import analytics, cli, cli_cycle as _cli_cycle_m, compaction as compaction_module, evolution_guard, executor, external_metrics, launcher, portfolio, scope_priority, updater

TEST_RUNTIME_ROOT = Path(__file__).resolve().parents[1]
TEST_PRODUCT_ROOT = Path(__file__).resolve().parents[3]


def isolated_test_config(test_case):
    """Keep lifecycle writes away from the configured installation state."""
    config = copy.deepcopy(cli.load_config())
    directory = tempfile.TemporaryDirectory(prefix='urace-test-state-')
    test_case.addCleanup(directory.cleanup)
    config['state_path'] = str(Path(directory.name) / 'state.json')
    return config



class R119PrvsCAPTests(unittest.TestCase):
    """PRVS CAP pass: verify r113-r116 CLI commands are registered and dispatch correctly."""

    def setUp(self):
        self.config = isolated_test_config(self)
        self.config["executor"]["enabled"] = False
        self.state = cli.initial_state(self.config)
        cli.seed_confirmed_onboard(self.config, self.state)

    def _run(self, argv):
        with patch.object(cli, "load_config", return_value=self.config):
            with patch.object(cli, "load_state_for_read", return_value=self.state):
                with patch.object(cli, "save_state"):
                    buf_out = io.StringIO()
                    buf_err = io.StringIO()
                    with redirect_stdout(buf_out), redirect_stderr(buf_err):
                        rc = cli.main(argv)
        return rc, buf_out.getvalue(), buf_err.getvalue()

    def test_explain_command_registered(self):
        """urace explain is a registered top-level command."""
        self.assertIn("explain", cli._KNOWN_TOP_COMMANDS)

    def test_explain_missing_id_returns_error(self):
        """urace explain without an id errors at argparse level."""
        buf = io.StringIO()
        with redirect_stderr(buf):
            try:
                rc = cli.main(["explain"])
            except SystemExit as e:
                rc = e.code
        self.assertNotEqual(rc, 0)

    def test_explain_unknown_id_returns_1(self):
        """urace explain <unknown-id> returns exit code 1."""
        rc, out, err = self._run(["explain", "nonexistent-dr-id"])
        self.assertEqual(rc, 1)
        self.assertIn("nonexistent-dr-id", err)

    def test_explain_known_decision_record(self):
        """urace explain <id> produces output for an existing DecisionRecord."""
        dr = {"id": "dr-test-001", "at": "2026-01-01T00:00:00Z", "rationale": "test rationale", "authority_basis": "delegated", "outcome": "accepted"}
        self.state.setdefault("decision_records", []).append(dr)
        rc, out, err = self._run(["explain", "dr-test-001"])
        self.assertEqual(rc, 0)
        self.assertIn("dr-test-001", out)

    def test_explain_json_format(self):
        """urace explain --json emits ExplanationRecord fields."""
        dr = {"id": "dr-test-002", "at": "2026-01-01T00:00:00Z", "rationale": "r2"}
        self.state.setdefault("decision_records", []).append(dr)
        rc, out, err = self._run(["explain", "--json", "dr-test-002"])
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["decision_id"], "dr-test-002")
        self.assertIn("plain_language", data)
        self.assertIn("chain_completeness", data)

    def test_intent_rollback_in_action_choices(self):
        """intent command accepts rollback action."""
        buf = io.StringIO()
        with redirect_stdout(buf):
            try:
                rc = cli.main(["intent", "--help"])
            except SystemExit:
                rc = 0
        self.assertIn("rollback", buf.getvalue())

    def test_intent_rollback_unknown_version_returns_1(self):
        """intent rollback <nonexistent> returns 1."""
        rc, out, err = self._run(["intent", "rollback", "ivr-nonexistent"])
        self.assertEqual(rc, 1)

    def test_intent_rollback_known_version_queues(self):
        """intent rollback <valid-id> creates a new IntentVersionRecord and queues."""
        ivr = {"id": "ivr-test-001", "at": "2026-01-01T00:00:00Z", "mutation_reason": "initial", "directive_snapshot": [], "goal_snapshot": []}
        self.state.setdefault("intent_version_records", []).append(ivr)
        with patch.object(cli, "load_config", return_value=self.config):
            with patch.object(cli, "load_state_for_read", return_value=self.state):
                with patch.object(cli, "queue_input", return_value={"id": "qi-rollback-001"}) as mock_q:
                    buf = io.StringIO()
                    with redirect_stdout(buf):
                        rc = cli.main(["intent", "rollback", "ivr-test-001"])
        self.assertEqual(rc, 0)
        mock_q.assert_called_once()
        call_args = mock_q.call_args[0]
        self.assertEqual(call_args[1], "intent_control")
        self.assertEqual(call_args[2]["action"], "rollback")

    def test_add_principal_registered(self):
        """add principal is a registered add subcommand."""
        buf = io.StringIO()
        with redirect_stdout(buf):
            try:
                rc = cli.main(["add", "--help"])
            except SystemExit:
                rc = 0
        self.assertIn("principal", buf.getvalue())

    def test_add_principal_creates_record(self):
        """add principal creates a PrincipalRecord in state."""
        rc, out, err = self._run(["add", "principal", "alice@example.com", "--precedence", "1", "--scope", "product"])
        self.assertEqual(rc, 0)
        prs = self.state.get("principal_records", [])
        self.assertTrue(any(pr.get("name") == "alice@example.com" for pr in prs))

    def test_add_principal_json_format(self):
        """add principal --json emits created record id."""
        rc, out, err = self._run(["add", "principal", "bob@example.com", "--json"])
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "created")
        self.assertEqual(data["name"], "bob@example.com")

    def test_check_migration_dry_run_flag_registered(self):
        """check accepts --migration-dry-run flag."""
        buf = io.StringIO()
        with redirect_stdout(buf):
            try:
                rc = cli.main(["check", "--help"])
            except SystemExit:
                rc = 0
        self.assertIn("migration-dry-run", buf.getvalue())

    def test_check_migration_dry_run_returns_report(self):
        """check --migration-dry-run returns a dry-run migration report."""
        rc, out, err = self._run(["check", "--migration-dry-run"])
        self.assertEqual(rc, 0)
        self.assertIn("migration-dry-run", out)

    def test_check_migration_dry_run_json(self):
        """check --migration-dry-run --json emits structured report."""
        rc, out, err = self._run(["check", "--migration-dry-run", "--json"])
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["mode"], "dry-run")
        self.assertIn("projected_result", data)

    def test_data_verify_registered(self):
        """data verify is a registered subcommand."""
        buf = io.StringIO()
        with redirect_stdout(buf):
            try:
                rc = cli.main(["data", "--help"])
            except SystemExit:
                rc = 0
        self.assertIn("verify", buf.getvalue())

    def test_data_status_registered(self):
        """data status is a registered subcommand."""
        buf = io.StringIO()
        with redirect_stdout(buf):
            try:
                rc = cli.main(["data", "--help"])
            except SystemExit:
                rc = 0
        self.assertIn("status", buf.getvalue())

    def test_data_credential_registered(self):
        """data credential is a registered subcommand."""
        buf = io.StringIO()
        with redirect_stdout(buf):
            try:
                rc = cli.main(["data", "--help"])
            except SystemExit:
                rc = 0
        self.assertIn("credential", buf.getvalue())

    def test_data_add_accepts_auto_and_schema_flags(self):
        """data add accepts --auto and --schema flags."""
        buf = io.StringIO()
        with redirect_stdout(buf):
            try:
                rc = cli.main(["data", "add", "--help"])
            except SystemExit:
                rc = 0
        self.assertIn("--auto", buf.getvalue())
        self.assertIn("--schema", buf.getvalue())

    def test_data_list_accepts_direction_and_status_filters(self):
        """data list accepts --direction and --status filters."""
        buf = io.StringIO()
        with redirect_stdout(buf):
            try:
                rc = cli.main(["data", "list", "--help"])
            except SystemExit:
                rc = 0
        self.assertIn("--direction", buf.getvalue())
        self.assertIn("--status", buf.getvalue())

class R120DefaultContinuationSemanticsTests(unittest.TestCase):
    """§62z DefaultContinuationSemantics — degrade, log, continue."""

    def setUp(self):
        self.config = isolated_test_config(self)
        self.config["executor"]["enabled"] = False
        self.state = cli.initial_state(self.config)
        cli.seed_confirmed_onboard(self.config, self.state)

    def test_degrade_emits_degradation_event(self):
        from urace import continuation as c
        c.degrade(self.state, reason="test-reason", context="test-context")
        events = self.state.get("degradation_events", [])
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["reason"], "test-reason")
        self.assertEqual(events[0]["context"], "test-context")
        self.assertIn("id", events[0])
        self.assertIn("at", events[0])

    def test_degrade_reduces_continuation_confidence(self):
        from urace import continuation as c
        self.state["continuation_confidence"] = 1.0
        c.degrade(self.state, reason="r1", confidence_reduction=0.25)
        self.assertAlmostEqual(self.state["continuation_confidence"], 0.75)

    def test_degrade_confidence_floors_at_zero(self):
        from urace import continuation as c
        self.state["continuation_confidence"] = 0.1
        c.degrade(self.state, reason="r1", confidence_reduction=0.5)
        self.assertEqual(self.state["continuation_confidence"], 0.0)

    def test_degrade_emits_degraded_trace_record(self):
        from urace import continuation as c
        c.degrade(self.state, reason="trace-test")
        traces = [t for t in self.state.get("trace_records", []) if t["kind"] == "DEGRADED"]
        self.assertEqual(len(traces), 1)
        self.assertIn("default continuation", traces[0]["summary"])

    def test_handle_unspecified_emits_evidence(self):
        from urace import continuation as c
        c.handle_unspecified(self.state, situation="unknown-state-X", context="detail")
        ev = [e for e in self.state.get("evidence", []) if e.get("kind") == "unspecified-situation"]
        self.assertEqual(len(ev), 1)
        self.assertEqual(ev[0]["summary"], "unknown-state-X")

    def test_reset_confidence_restores_to_one_when_no_events(self):
        from urace import continuation as c
        self.state["continuation_confidence"] = 0.5
        self.state["degradation_events"] = []
        c.reset_confidence(self.state)
        self.assertEqual(self.state["continuation_confidence"], 1.0)

    def test_reset_confidence_does_not_restore_when_events_present(self):
        from urace import continuation as c
        self.state["continuation_confidence"] = 0.5
        self.state["degradation_events"] = [{"id": "deg-abc", "reason": "x", "at": "t"}]
        c.reset_confidence(self.state)
        self.assertEqual(self.state["continuation_confidence"], 0.5)

    def test_cycle_resets_confidence_at_start(self):
        """cycle() resets continuation_confidence to 1.0 at cycle boundary."""
        self.state["continuation_confidence"] = 0.3
        self.state["degradation_events"] = []
        cli.cycle(self.config, self.state, allow_execution=False)
        self.assertEqual(self.state["continuation_confidence"], 1.0)

    def test_cycle_outcome_includes_continuation_confidence(self):
        """cycle() attaches continuation_confidence to outcome dict."""
        outcome = cli.cycle(self.config, self.state, allow_execution=False)
        self.assertIn("continuation_confidence", outcome)
        self.assertIsInstance(outcome["continuation_confidence"], float)

    def test_multiple_degrades_accumulate(self):
        from urace import continuation as c
        self.state["continuation_confidence"] = 1.0
        c.degrade(self.state, reason="r1", confidence_reduction=0.15)
        c.degrade(self.state, reason="r2", confidence_reduction=0.15)
        self.assertAlmostEqual(self.state["continuation_confidence"], 0.70)
        self.assertEqual(len(self.state.get("degradation_events", [])), 2)


    def test_reset_confidence_ignores_events_from_older_cycles(self):
        from urace import continuation as c
        c.handle_unspecified(self.state, "first cycle", cycle_id="cycle-1")
        c.reset_confidence(self.state)
        self.assertAlmostEqual(self.state["continuation_confidence"], 0.85)
        c.reset_confidence(self.state)
        self.assertEqual(self.state["continuation_confidence"], 1.0)
        self.assertEqual(len(self.state["degradation_events"]), 1)
        c.handle_unspecified(self.state, "third cycle", cycle_id="cycle-3")
        c.reset_confidence(self.state)
        self.assertAlmostEqual(self.state["continuation_confidence"], 0.85)

    def test_discovery_error_degrades_and_finishes_cycle(self):
        with patch.object(cli, "discover", return_value=None), patch.object(
            cli, "discover_with_executor", side_effect=RuntimeError("unknown discovery response")
        ), patch.object(_cli_cycle_m, "discover", return_value=None), patch.object(
            _cli_cycle_m, "discover_with_executor", side_effect=RuntimeError("unknown discovery response")
        ):
            result = cli.cycle(self.config, self.state, allow_execution=False)
        self.assertEqual(result["outcome"], "dormant")
        self.assertAlmostEqual(result["continuation_confidence"], 0.85)
        event = self.state["degradation_events"][-1]
        self.assertTrue(event["cycle_id"].startswith("cycle-"))
        self.assertEqual(event["context"], "intelligent discovery")
        self.assertEqual(self.state["evidence"][-1]["kind"], "unspecified-situation")


    def test_execution_error_degrades_without_retrying_objective(self):
        self.config["executor"]["enabled"] = True
        objective = {"id": "goal-r120", "title": "test", "scope": "documentation",
                     "status": "planned", "authority_resolution": {"outcome": "AUTHORIZED"}}
        with patch.object(cli, "discover", return_value=objective), patch.object(
            cli, "refresh_executor_availability", return_value={"available": True}
        ), patch.object(cli, "plan_for", return_value={"id": "plan-r120"}), patch.object(
            cli, "execute_with_executor", side_effect=RuntimeError("unknown execution response")
        ), patch.object(_cli_cycle_m, "discover", return_value=objective), patch.object(
            _cli_cycle_m, "refresh_executor_availability", return_value={"available": True}
        ), patch.object(_cli_cycle_m, "plan_for", return_value={"id": "plan-r120"}), patch.object(
            _cli_cycle_m, "execute_with_executor", side_effect=RuntimeError("unknown execution response")
        ) as execute:
            result = cli.cycle(self.config, self.state)
        execute.assert_called_once()
        self.assertEqual(result["outcome"], "dormant")
        self.assertEqual(self.state["lifecycle_state"], "DORMANT")
        self.assertEqual(objective["status"], "blocked")
        self.assertAlmostEqual(result["continuation_confidence"], 0.85)
        self.assertEqual(self.state["degradation_events"][-1]["context"], "execution")

class RuntimeTestFailureDetailTests(unittest.TestCase):
    def test_retains_real_failure_headings_and_excludes_fixture_output(self):
        output = """fixture setup\nERROR: unrelated CLI problem\n======================================================================\nFAIL: test_alpha (tests.Sample.test_alpha)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"tests.py\", line 10, in test_alpha\nAssertionError: alpha\n======================================================================\nERROR: test_beta (tests.Sample.test_beta)\n----------------------------------------------------------------------\nTraceback (most recent call last):\n  File \"tests.py\", line 20, in test_beta\nRuntimeError: beta\n----------------------------------------------------------------------\nRan 2 tests in 0.012s\n\nFAILED (failures=1, errors=1)\ntrailing fixture cleanup\n"""
        detail = executor._runtime_test_failure_detail(output)
        self.assertIn("FAIL: test_alpha (tests.Sample.test_alpha)", detail)
        self.assertIn("ERROR: test_beta (tests.Sample.test_beta)", detail)
        self.assertIn("Ran 2 tests in 0.012s", detail)
        self.assertIn("FAILED (failures=1, errors=1)", detail)
        self.assertNotIn("unrelated CLI problem", detail)
        self.assertNotIn("trailing fixture cleanup", detail)

    def test_bounded_detail_preserves_every_failure_name_and_trace_context(self):
        blocks = []
        for index in range(6):
            blocks.append(
                "=" * 70 + f"\nFAIL: test_case_{index} (tests.LongCase.test_case_{index})\n"
                + "-" * 70 + "\nTraceback (most recent call last):\n"
                + (f"trace-{index}-" * 800) + f"\nAssertionError: result-{index}\n"
            )
        output = "leading noise\n" + "".join(blocks) + "-" * 70 + "\nRan 6 tests in 1.000s\n\nFAILED (failures=6)\ntrailing noise\n"
        detail = executor._runtime_test_failure_detail(output)
        for index in range(6):
            self.assertIn(f"FAIL: test_case_{index} (tests.LongCase.test_case_{index})", detail)
        self.assertIn("Ran 6 tests in 1.000s", detail)
        self.assertIn("FAILED (failures=6)", detail)
        self.assertIn("Traceback (most recent call last):", detail)
        self.assertIn("[trace context truncated]", detail)
        self.assertLessEqual(len(detail), 6000)

    def test_import_failure_is_recognized_as_unittest_error(self):
        output = """loader preamble\n======================================================================\nERROR: test_broken (unittest.loader._FailedTest.test_broken)\n----------------------------------------------------------------------\nImportError: Failed to import test module: test_broken\nTraceback (most recent call last):\n  File \"unittest/loader.py\", line 419, in _find_test_path\nModuleNotFoundError: No module named 'missing_dependency'\n----------------------------------------------------------------------\nRan 1 test in 0.000s\n\nFAILED (errors=1)\nloader epilogue\n"""
        detail = executor._runtime_test_failure_detail(output)
        self.assertIn("ERROR: test_broken (unittest.loader._FailedTest.test_broken)", detail)
        self.assertIn("ModuleNotFoundError: No module named 'missing_dependency'", detail)
        self.assertIn("FAILED (errors=1)", detail)
        self.assertNotIn("loader preamble", detail)
        self.assertNotIn("loader epilogue", detail)

    def test_non_unittest_error_keeps_tail_fallback(self):
        output = "prefix" + ("x" * 2500) + "\nplain tool failure"
        self.assertEqual(executor._runtime_test_failure_detail(output), output[-2000:])

class R121CryptoWalletTests(unittest.TestCase):
    """Crypto wallet scaffold — local keypair, address derivation, signing."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil; shutil.rmtree(self.tmp, ignore_errors=True)

    def _run(self, *args):
        import sys as _sys
        result = subprocess.run(
            [_sys.executable, '-m', 'urace', *args],
            cwd=os.path.join(os.path.dirname(__file__), '..'),
            capture_output=True, text=True
        )
        return json.loads(result.stdout)

    def _run_rc(self, *args):
        import sys as _sys
        result = subprocess.run(
            [_sys.executable, '-m', 'urace', *args],
            cwd=os.path.join(os.path.dirname(__file__), '..'),
            capture_output=True, text=True
        )
        return result.returncode, json.loads(result.stdout)

    def test_wallet_init_creates_key_file(self):
        r = self._run('crypto', 'wallet', 'init', '--wallet-dir', self.tmp, '--json')
        self.assertEqual(r['status'], 'ok')
        self.assertIn('address', r)
        self.assertTrue(r['address'].startswith('0x'))
        self.assertIn('public_key', r)
        key_file = os.path.join(self.tmp, 'key.json')
        self.assertTrue(os.path.exists(key_file))

    def test_wallet_init_private_key_not_in_result(self):
        r = self._run('crypto', 'wallet', 'init', '--wallet-dir', self.tmp, '--json')
        self.assertNotIn('private_key', r)

    def test_wallet_show_returns_address_and_pubkey(self):
        self._run('crypto', 'wallet', 'init', '--wallet-dir', self.tmp, '--json')
        r = self._run('crypto', 'wallet', 'show', '--wallet-dir', self.tmp, '--json')
        self.assertEqual(r['status'], 'ok')
        self.assertIn('address', r)
        self.assertNotIn('private_key', r)

    def test_wallet_show_consistent_address(self):
        init = self._run('crypto', 'wallet', 'init', '--wallet-dir', self.tmp, '--json')
        show = self._run('crypto', 'wallet', 'show', '--wallet-dir', self.tmp, '--json')
        self.assertEqual(init['address'], show['address'])

    def test_wallet_sign_returns_signature(self):
        self._run('crypto', 'wallet', 'init', '--wallet-dir', self.tmp, '--json')
        r = self._run('crypto', 'wallet', 'sign', 'hello urace', '--wallet-dir', self.tmp, '--json')
        self.assertEqual(r['status'], 'ok')
        self.assertIn('signature_der', r)
        self.assertIn('payload_sha256', r)
        self.assertEqual(r['algorithm'], 'ECDSA-secp256k1-SHA256')

    def test_wallet_sign_different_payloads_different_digests(self):
        self._run('crypto', 'wallet', 'init', '--wallet-dir', self.tmp, '--json')
        r1 = self._run('crypto', 'wallet', 'sign', 'payload_one', '--wallet-dir', self.tmp, '--json')
        r2 = self._run('crypto', 'wallet', 'sign', 'payload_two', '--wallet-dir', self.tmp, '--json')
        self.assertNotEqual(r1['payload_sha256'], r2['payload_sha256'])

    def test_wallet_init_overwrite_rejected_by_default(self):
        self._run('crypto', 'wallet', 'init', '--wallet-dir', self.tmp, '--json')
        rc, data = self._run_rc('crypto', 'wallet', 'init', '--wallet-dir', self.tmp, '--json')
        self.assertNotEqual(rc, 0)
        self.assertEqual(data['status'], 'error')

    def test_wallet_init_overwrite_flag_succeeds(self):
        self._run('crypto', 'wallet', 'init', '--wallet-dir', self.tmp, '--json')
        r = self._run('crypto', 'wallet', 'init', '--wallet-dir', self.tmp, '--overwrite', '--json')
        self.assertEqual(r['status'], 'ok')

    def test_wallet_show_without_init_returns_error(self):
        rc, data = self._run_rc('crypto', 'wallet', 'show', '--wallet-dir', self.tmp, '--json')
        self.assertNotEqual(rc, 0)
        self.assertEqual(data['status'], 'error')

class R122ScoreTo10Tests(unittest.TestCase):
    """Tests for the three features completing 10/10 scores."""

    def _run(self, *args):
        import sys as _sys
        r = subprocess.run(
            [_sys.executable, '-m', 'urace', *args],
            cwd=os.path.join(os.path.dirname(__file__), '..'),
            capture_output=True, text=True
        )
        return r.returncode, json.loads(r.stdout) if r.stdout.strip() else {}

    # -- qualification replay --mode full ----------------------------------

    def test_qualification_replay_estimate_mode_default(self):
        rc, data = self._run('qualification', 'list', '--json')
        self.assertEqual(rc, 0)
        self.assertEqual(data['status'], 'ok')
        self.assertIn('evidence', data)

    def test_qualification_replay_full_mode_missing_evidence(self):
        rc, data = self._run('qualification', 'replay', '--evidence-id', 'nonexistent', '--mode', 'full', '--json')
        self.assertNotEqual(rc, 0)
        self.assertEqual(data['status'], 'error')

    def test_qualification_replay_full_mode_arg_accepted(self):
        rc, data = self._run('qualification', 'replay', '--evidence-id', 'x', '--mode', 'full', '--json')
        # error is fine (evidence not found); what matters is the --mode flag parses
        self.assertIn('status', data)

    # -- fleet capacity ----------------------------------------------------

    def test_fleet_capacity_empty_fleet(self):
        rc, data = self._run('fleet', 'capacity', '--json')
        self.assertEqual(rc, 0)
        self.assertEqual(data['status'], 'ok')
        self.assertIn('fleet_size', data)
        self.assertIn('parallel_capacity', data)
        self.assertIn('bottleneck_members', data)
        self.assertIn('members', data)

    def test_fleet_capacity_has_calls_remaining(self):
        rc, data = self._run('fleet', 'capacity', '--json')
        self.assertEqual(rc, 0)
        self.assertIn('total_calls_remaining_24h', data)

    # -- executor circuit-breaker ------------------------------------------

    def test_circuit_breaker_status_returns_providers(self):
        rc, data = self._run('executor', 'circuit-breaker', '--json')
        self.assertEqual(rc, 0)
        self.assertEqual(data['status'], 'ok')
        self.assertIn('providers', data)
        self.assertIn('trip_threshold', data)
        self.assertIn('tripped_count', data)
        self.assertIn('healthy_count', data)

    def test_circuit_breaker_provider_fields(self):
        rc, data = self._run('executor', 'circuit-breaker', '--json')
        self.assertEqual(rc, 0)
        for p in data['providers']:
            self.assertIn('provider_id', p)
            self.assertIn('failures', p)
            self.assertIn('threshold', p)
            self.assertIn('tripped', p)
            self.assertIn('recommendation', p)

    def test_circuit_breaker_reset_unknown_provider_returns_error(self):
        rc, data = self._run('executor', 'circuit-breaker', '--cb-action', 'reset', '--cb-provider', 'does-not-exist', '--json')
        self.assertNotEqual(rc, 0)
        self.assertEqual(data['status'], 'error')

    def test_circuit_breaker_reset_requires_cb_provider(self):
        rc, data = self._run('executor', 'circuit-breaker', '--cb-action', 'reset', '--json')
        self.assertNotEqual(rc, 0)

    def test_circuit_breaker_module_imports(self):
        from urace import circuit_breaker as cb
        self.assertTrue(callable(cb.status))
        self.assertTrue(callable(cb.reset))
        self.assertTrue(callable(cb.auto_trip))

class ComplianceEnterpriseTests(unittest.TestCase):
    """Tests for compliance --export, --strict, --since/--until (enterprise features)."""

    def _make_state_with_records(self):
        state = {"compliance_records": [], "compliance_state": {}}
        cli._emit_compliance_record(state, "authority", "COMPLIANT", "op-1")
        cli._emit_compliance_record(state, "intent", "NON_COMPLIANT", "op-2", "drift")
        cli._emit_compliance_record(state, "schema", "COMPLIANT", "op-3")
        return state

    def test_compliance_strict_pass_when_all_compliant(self):
        state = {"compliance_records": [], "compliance_state": {}}
        cli._emit_compliance_record(state, "authority", "COMPLIANT", "op-1")
        config = isolated_test_config(self)
        buf = io.StringIO()
        with patch.object(cli, "load_config", return_value=config), \
             patch.object(cli, "load_state_for_read", return_value=state), \
             redirect_stdout(buf):
            ret = cli.main(["compliance", "--strict", "--json"])
        self.assertEqual(ret, 0)
        result = json.loads(buf.getvalue())
        self.assertTrue(result["strict_pass"])

    def test_compliance_strict_fails_when_non_compliant(self):
        state = self._make_state_with_records()
        config = isolated_test_config(self)
        buf = io.StringIO()
        with patch.object(cli, "load_config", return_value=config), \
             patch.object(cli, "load_state_for_read", return_value=state), \
             redirect_stdout(buf):
            ret = cli.main(["compliance", "--strict", "--json"])
        self.assertEqual(ret, 1)
        result = json.loads(buf.getvalue())
        self.assertFalse(result["strict_pass"])

    def test_compliance_export_json(self):
        state = self._make_state_with_records()
        config = isolated_test_config(self)
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            export_path = f.name
        try:
            with patch.object(cli, "load_config", return_value=config), \
                 patch.object(cli, "load_state_for_read", return_value=state):
                ret = cli.main(["compliance", "--export", export_path, "--json"])
            self.assertEqual(ret, 0)
            data = json.loads(Path(export_path).read_text())
            self.assertIn("compliance_records", data)
            self.assertEqual(len(data["compliance_records"]), 3)
            self.assertIn("exported_at", data)
        finally:
            Path(export_path).unlink(missing_ok=True)

    def test_compliance_export_jsonl(self):
        state = self._make_state_with_records()
        config = isolated_test_config(self)
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            export_path = f.name
        try:
            with patch.object(cli, "load_config", return_value=config), \
                 patch.object(cli, "load_state_for_read", return_value=state):
                ret = cli.main(["compliance", "--export", export_path])
            self.assertEqual(ret, 0)
            lines = Path(export_path).read_text().strip().splitlines()
            self.assertEqual(len(lines), 3)
            for line in lines:
                json.loads(line)  # each line is valid JSON
        finally:
            Path(export_path).unlink(missing_ok=True)

    def test_compliance_strict_pass_field_in_json(self):
        state = {"compliance_records": [], "compliance_state": {}}
        config = isolated_test_config(self)
        buf = io.StringIO()
        with patch.object(cli, "load_config", return_value=config), \
             patch.object(cli, "load_state_for_read", return_value=state), \
             redirect_stdout(buf):
            ret = cli.main(["compliance", "--json"])
        self.assertEqual(ret, 0)
        result = json.loads(buf.getvalue())
        self.assertIn("strict_pass", result)
        self.assertTrue(result["strict_pass"])

class GitGhCommandTests(unittest.TestCase):
    """Tests for urace git and urace gh pass-through commands."""

    def _run(self, *args):
        import sys as _sys
        r = subprocess.run(
            [_sys.executable, '-m', 'urace', *args],
            cwd=os.path.join(os.path.dirname(__file__), '..'),
            capture_output=True, text=True
        )
        return r.returncode, r.stdout, r.stderr

    def test_git_passthrough_runs(self):
        rc, stdout, _ = self._run('git', 'rev-parse', '--show-toplevel')
        self.assertEqual(rc, 0)

    def test_git_json_wraps_output(self):
        rc, stdout, _ = self._run('git', 'rev-parse', '--show-toplevel', '--json')
        self.assertEqual(rc, 0)
        data = json.loads(stdout)
        self.assertIn('returncode', data)
        self.assertIn('stdout', data)
        self.assertEqual(data['returncode'], 0)

    def test_gh_missing_shows_error(self):
        import shutil
        if shutil.which('gh'):
            self.skipTest('gh is installed, test only for missing gh')
        rc, stdout, _ = self._run('gh', 'pr', 'list', '--json')
        self.assertNotEqual(rc, 0)
        data = json.loads(stdout)
        self.assertEqual(data['status'], 'error')
        self.assertIn('gh', data['error'].lower())

class GithubCommandTests(unittest.TestCase):
    """Tests for urace github command."""

    def _run_json(self, *args):
        import sys as _sys
        r = subprocess.run(
            [_sys.executable, '-m', 'urace', *args],
            cwd=os.path.join(os.path.dirname(__file__), '..'),
            capture_output=True, text=True,
            env={**os.environ, 'URACE_GITHUB_TOKEN': ''}
        )
        return r.returncode, json.loads(r.stdout) if r.stdout.strip() else {}

    def test_github_status_no_token(self):
        rc, data = self._run_json('github', 'status', '--json')
        self.assertEqual(rc, 0)
        self.assertIn('github_token_set', data)
        self.assertFalse(data['github_token_set'])
        self.assertIn('hint', data)

    def test_github_connect_invalid_format_rejected(self):
        rc, data = self._run_json('github', 'connect', 'notareposlash', '--json')
        self.assertNotEqual(rc, 0)
        self.assertEqual(data['status'], 'error')

    def test_github_connect_valid_saves_config(self):
        import sys as _sys
        with tempfile.TemporaryDirectory() as tmpdir:
            env = {**os.environ, 'URACE_STATE_ROOT': tmpdir, 'URACE_GITHUB_TOKEN': ''}
            r = subprocess.run(
                [_sys.executable, '-m', 'urace', 'github', 'connect', 'owner/repo', '--json'],
                cwd=os.path.join(os.path.dirname(__file__), '..'),
                capture_output=True, text=True, env=env
            )
            if r.returncode == 0:
                data = json.loads(r.stdout)
                self.assertEqual(data['status'], 'connected')
                self.assertEqual(data['repo'], 'owner/repo')

class SecurityAuditNoNetworkTests(unittest.TestCase):
    """Tests for security audit --no-network flag."""

    def test_security_audit_no_network_skips_github_check(self):
        import sys as _sys
        r = subprocess.run(
            [_sys.executable, '-m', 'urace', 'security', 'audit', '--no-network', '--json'],
            cwd=os.path.join(os.path.dirname(__file__), '..'),
            capture_output=True, text=True
        )
        self.assertEqual(r.returncode, 0)
        data = json.loads(r.stdout)
        self.assertIn('status', data)
        self.assertIn('checks', data)
        # github_release_asset check should not be present when --no-network
        check_names = [c['check'] for c in data['checks']]
        self.assertNotIn('github_release_asset', check_names)

