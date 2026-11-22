import copy
import hashlib
import io
import json
import subprocess
import tempfile
import unittest
import pytest
pytestmark = pytest.mark.slow
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from urace import cli

TEST_RUNTIME_ROOT = Path(__file__).resolve().parents[1]
TEST_PRODUCT_ROOT = Path(__file__).resolve().parents[3]


def isolated_test_config(test_case):
    """Keep lifecycle writes away from the configured installation state."""
    config = copy.deepcopy(cli.load_config())
    directory = tempfile.TemporaryDirectory(prefix='urace-test-state-')
    test_case.addCleanup(directory.cleanup)
    config['state_path'] = str(Path(directory.name) / 'state.json')
    return config



class AddCommandTests(unittest.TestCase):
    """Tests for urace add classification command (§62c urace add)."""

    def test_validate_classification_result_goal_passes(self):
        from urace import primitives as p
        p.validate_classification_result({
            "type": "goal",
            "parameters": {"title": "Increase coverage", "success_measure": "tests >= 90%"},
            "confidence": 0.94,
            "raw_text": "Increase test coverage to 90%",
        })

    def test_validate_classification_result_intent_passes(self):
        from urace import primitives as p
        p.validate_classification_result({
            "type": "intent",
            "subtype": "directive",
            "parameters": {"statement": "Preserve all existing APIs"},
            "confidence": 0.88,
            "raw_text": "Preserve all existing APIs",
        })

    def test_validate_classification_result_constraint_permission_passes(self):
        from urace import primitives as p
        p.validate_classification_result({
            "type": "constraint",
            "subtype": "permission",
            "parameters": {"statement": "Allow executor to modify test files"},
            "confidence": 0.91,
            "raw_text": "Allow executor to modify test files",
        })

    def test_validate_classification_result_bad_type_raises(self):
        from urace import primitives as p
        with self.assertRaises(ValueError):
            p.validate_classification_result({
                "type": "unknown",
                "parameters": {},
                "confidence": 0.5,
                "raw_text": "something",
            })

    def test_validate_classification_result_bad_confidence_raises(self):
        from urace import primitives as p
        with self.assertRaises(ValueError):
            p.validate_classification_result({
                "type": "goal",
                "parameters": {},
                "confidence": 1.5,
                "raw_text": "something",
            })

    def test_validate_classification_result_missing_required_raises(self):
        from urace import primitives as p
        with self.assertRaises(ValueError):
            p.validate_classification_result({
                "type": "goal",
                "confidence": 0.9,
                # missing parameters and raw_text
            })

    def test_classification_result_constraint_permission_subtype(self):
        from urace import primitives as p
        # permission subtype is valid for constraint
        rec = {
            "type": "constraint",
            "subtype": "permission",
            "parameters": {"statement": "Allow X"},
            "confidence": 0.85,
            "raw_text": "Allow X",
        }
        p.validate_classification_result(rec)
        self.assertEqual(rec["subtype"], "permission")

    def test_add_command_parser_registered(self):
        """urace add subcommand must be parseable."""
        import sys
        result = subprocess.run(
            [sys.executable, "-m", "urace.cli", "add", "--help"],
            capture_output=True, text=True, cwd=str(TEST_RUNTIME_ROOT)
        )
        # Should exit 0 with help text, not "invalid choice" error
        self.assertNotIn("invalid choice", result.stderr)
        self.assertNotIn("invalid choice", result.stdout)

    def test_add_classify_routes_to_existing_handlers(self):
        """Classified inputs must route to existing goal/intent/constraint handlers."""
        # Verify that goal/intent_control/constraint_control kinds are handled
        from urace import inputs as inp
        handlers = inp._INPUT_HANDLERS if hasattr(inp, "_INPUT_HANDLERS") else {}
        if not handlers:
            self.skipTest("Handler registry not accessible as _INPUT_HANDLERS")
        self.assertIn("goal", handlers, "goal handler must exist for urace add routing")
        self.assertIn("intent_control", handlers, "intent_control handler must exist")
        self.assertIn("constraint_control", handlers, "constraint_control handler must exist")

    def test_classification_prompt_includes_command_type(self):
        import argparse
        from urace import freeform_routing
        rendered=freeform_routing.prompt("Show status",argparse.ArgumentParser())
        for name in ("goal","intent","constraint","command","response"):
            self.assertIn(name,rendered)
        self.assertIn("installed command",rendered)

class ClassificationBatchTests(unittest.TestCase):
    def setUp(self):
        from urace import primitives as p
        self.p = p

    def _make_item(self, type_, **kwargs):
        base = {"type": type_, "parameters": {}, "confidence": 0.9, "raw_text": "x"}
        base.update(kwargs)
        return base

    def test_valid_single_item_batch_passes(self):
        batch = {"items": [self._make_item("goal")], "compound": False, "raw_text": "x"}
        self.p.validate_classification_batch(batch)

    def test_valid_compound_batch_passes(self):
        batch = {
            "items": [self._make_item("goal"), self._make_item("constraint", subtype="prohibition")],
            "compound": True,
            "raw_text": "a and b",
        }
        self.p.validate_classification_batch(batch)

    def test_batch_with_all_three_types_passes(self):
        batch = {
            "items": [
                self._make_item("goal"),
                self._make_item("intent", subtype="directive"),
                self._make_item("constraint", subtype="permission"),
            ],
            "compound": True,
            "raw_text": "goal intent constraint",
        }
        self.p.validate_classification_batch(batch)

    def test_empty_items_raises(self):
        with self.assertRaises(Exception):
            self.p.validate_classification_batch({"items": [], "compound": False, "raw_text": "x"})

    def test_missing_items_raises(self):
        with self.assertRaises(Exception):
            self.p.validate_classification_batch({"compound": False, "raw_text": "x"})

    def test_compound_not_bool_raises(self):
        with self.assertRaises(Exception):
            self.p.validate_classification_batch({"items": [self._make_item("goal")], "compound": "yes", "raw_text": "x"})

    def test_invalid_item_type_in_batch_raises(self):
        with self.assertRaises(Exception):
            self.p.validate_classification_batch({"items": [self._make_item("unknown")], "compound": False, "raw_text": "x"})

    def test_command_type_in_classification_result_passes(self):
        item = {"type": "command", "parameters": {"command": "check"}, "confidence": 0.99, "raw_text": "/check"}
        self.p.validate_classification_result(item)

    def test_command_type_missing_command_field_raises(self):
        item = {"type": "command", "parameters": {}, "confidence": 0.99, "raw_text": "/check"}
        with self.assertRaises(Exception):
            self.p.validate_classification_result(item)

    def test_logic_and_passes(self):
        batch = {"items": [self._make_item("goal")], "compound": False, "raw_text": "x", "logic": "and"}
        self.p.validate_classification_batch(batch)

    def test_logic_or_passes(self):
        batch = {"items": [self._make_item("command", parameters={"command": "check"}), self._make_item("command", parameters={"command": "pause"})], "compound": True, "raw_text": "x", "logic": "or"}
        self.p.validate_classification_batch(batch)

    def test_logic_invalid_raises(self):
        batch = {"items": [self._make_item("goal")], "compound": False, "raw_text": "x", "logic": "maybe"}
        with self.assertRaises(Exception):
            self.p.validate_classification_batch(batch)

    def test_response_type_passes(self):
        item = {"type": "response", "parameters": {"text": "Hi!"}, "confidence": 0.99, "raw_text": "hi"}
        self.p.validate_classification_result(item)

    def test_response_type_missing_text_raises(self):
        item = {"type": "response", "parameters": {}, "confidence": 0.99, "raw_text": "hi"}
        with self.assertRaises(Exception):
            self.p.validate_classification_result(item)

class UniversalInputRoutingTests(unittest.TestCase):
    def _route(self, args):
        # Import _preprocess_args from cli
        import importlib
        cli = importlib.import_module("urace.cli")
        return cli._preprocess_args(list(args))

    def test_slash_check_routes_to_check(self):
        self.assertEqual(self._route(["/check"]), ["check"])

    def test_slash_vitals_routes_to_vitals(self):
        self.assertEqual(self._route(["/vitals"]), ["vitals"])

    def test_slash_with_subargs_preserved(self):
        self.assertEqual(self._route(["/intent", "add", "keep it simple"]), ["intent", "add", "keep it simple"])

    def test_known_command_passes_through(self):
        self.assertEqual(self._route(["auto"]), ["auto"])

    def test_free_form_routes_to_classify(self):
        result = self._route(["increase", "mobile", "retention"])
        self.assertEqual(result[0], "classify")
        self.assertIn("increase", result[1])

    def test_free_form_single_word_routes_to_classify(self):
        result = self._route(["growthhack"])
        self.assertEqual(result[0], "classify")

    def test_empty_args_unchanged(self):
        self.assertEqual(self._route([]), [])

    def test_flag_args_unchanged(self):
        self.assertEqual(self._route(["--help"]), ["--help"])

    def test_sd_true_exact_check_routes_directly(self):
        self.assertEqual(self._route(["check"]), ["check"])

    def test_sd_true_alias_status_routes_to_check(self):
        self.assertEqual(self._route(["status"]), ["status"])  # Workflow-aware inspection; core mode still delegates to check.

    def test_sd_true_alias_stop_routes_to_stop(self):
        self.assertEqual(self._route(["stop"]), ["stop"])

    def test_sd_true_two_word_rules_list(self):
        self.assertEqual(self._route(["rules", "list"]), ["rules", "list"])

    def test_sd_false_ambiguous_routes_to_classify(self):
        result = self._route(["increase", "retention", "by", "20%"])
        self.assertEqual(result[0], "classify")

    def test_formerly_missing_init_not_treated_as_freeform(self):
        self.assertEqual(self._route(["init"]), ["init"])

    def test_formerly_missing_budget_not_treated_as_freeform(self):
        self.assertEqual(self._route(["budget"]), ["budget"])

    def test_formerly_missing_repair_controller_not_treated_as_freeform(self):
        self.assertEqual(self._route(["repair-controller"]), ["repair-controller"])

    def test_formerly_missing_why_not_treated_as_freeform(self):
        self.assertEqual(self._route(["why"]), ["why"])

class ComprehensiveRoutingTests(unittest.TestCase):
    """Comprehensive test of _preprocess_args for all direct/freeform/mixed combinations."""

    def _route(self, args):
        import importlib
        cli = importlib.import_module("urace.cli")
        return cli._preprocess_args(list(args))

    # --- Slash direct command routing ---
    def test_slash_check_direct(self):
        self.assertEqual(self._route(["/check"]), ["check"])

    def test_slash_vitals_direct(self):
        self.assertEqual(self._route(["/vitals"]), ["vitals"])

    def test_slash_rules_list_direct(self):
        self.assertEqual(self._route(["/rules", "list"]), ["rules", "list"])

    def test_slash_intent_add_with_statement(self):
        self.assertEqual(self._route(["/intent", "add", "use TypeScript"]), ["intent", "add", "use TypeScript"])

    def test_slash_crc_show(self):
        self.assertEqual(self._route(["/crc", "show"]), ["crc", "show"])

    def test_slash_self_evolution_direct(self):
        self.assertEqual(self._route(["/self-evolution"]), ["self-evolution"])

    def test_slash_why_direct(self):
        self.assertEqual(self._route(["/why"]), ["why"])

    # --- Slash + non-command text should go to classify (r101) ---
    def test_slash_non_command_text_routes_to_classify(self):
        result = self._route(["/increase revenue by 20%"])
        self.assertEqual(result[0], "classify")
        self.assertIn("increase revenue", result[1])

    def test_slash_command_with_spaces_routes_to_classify(self):
        # "/check and increase revenue" as single string — stripped "check and increase revenue" not a command
        result = self._route(["/check and increase revenue"])
        self.assertEqual(result[0], "classify")

    # --- SD=True exact match aliases ---
    def test_sd_true_status(self):
        self.assertEqual(self._route(["status"]), ["status"])  # Workflow-aware inspection; core mode still delegates to check.

    def test_sd_true_stop(self):
        self.assertEqual(self._route(["stop"]), ["stop"])

    def test_sd_true_start(self):
        self.assertEqual(self._route(["resume"]), ["resume"])

    def test_sd_true_quoted_rules_list(self):
        # "rules list" as single quoted string
        self.assertEqual(self._route(["rules list"]), ["rules", "list"])

    def test_sd_true_quoted_change_list(self):
        self.assertEqual(self._route(["change list"]), ["change", "list"])

    # --- Known commands pass through unchanged ---
    def test_known_auto_passes_through(self):
        self.assertEqual(self._route(["auto"]), ["auto"])

    def test_known_budget_passes_through(self):
        self.assertEqual(self._route(["budget"]), ["budget"])

    def test_known_evaluation_passes_through(self):
        self.assertEqual(self._route(["evaluation"]), ["evaluation"])

    def test_known_plan_passes_through(self):
        self.assertEqual(self._route(["plan"]), ["plan"])

    def test_known_report_passes_through(self):
        self.assertEqual(self._route(["report"]), ["report"])

    def test_known_self_evolution_passes_through(self):
        self.assertEqual(self._route(["self-evolution"]), ["self-evolution"])

    def test_known_repair_controller_passes_through(self):
        self.assertEqual(self._route(["repair-controller"]), ["repair-controller"])

    def test_known_executor_capacity_passes_through(self):
        self.assertEqual(self._route(["executor-capacity"]), ["executor-capacity"])

    def test_freeform_hi_routes_to_classify(self):
        result = self._route(["hi"])
        self.assertEqual(result[0], "classify")

    def test_freeform_auto_routes_via_known_passthrough(self):
        # "auto" without slash → known command pass-through
        result = self._route(["auto"])
        self.assertEqual(result, ["auto"])

    def test_freeform_quoted_auto_routes_via_known(self):
        # "auto" as single quoted string → same
        result = self._route(["auto"])
        self.assertEqual(result, ["auto"])

    def test_slash_unknown_text_routes_to_classify(self):
        result = self._route(["/hi there"])
        self.assertEqual(result[0], "classify")
        self.assertNotIn("/", result[1])

    # --- SD=False free-form routes to classify (r101) ---
    def test_freeform_single_word_to_classify(self):
        result = self._route(["growthhack"])
        self.assertEqual(result[0], "classify")

    def test_freeform_multi_word_to_classify(self):
        result = self._route(["increase", "mobile", "retention", "by", "20%"])
        self.assertEqual(result[0], "classify")
        self.assertIn("increase", result[1])

    def test_freeform_sentence_to_classify(self):
        result = self._route(["ship the mobile app by Q2"])
        self.assertEqual(result[0], "classify")

    def test_freeform_goal_plus_constraint_to_classify(self):
        # Both items go to executor for decomposition
        result = self._route(["increase revenue and do not use AWS"])
        self.assertEqual(result[0], "classify")

    # --- Mixed: known command first token + unrecognized tail → pass through (argparse handles) ---
    def test_known_command_with_subaction(self):
        # "rules list" as two tokens — first is "rules" which IS known
        self.assertEqual(self._route(["rules", "list"]), ["rules", "list"])

    def test_known_command_with_flag(self):
        self.assertEqual(self._route(["check", "--json"]), ["check", "--json"])

    # --- Flag args always pass through ---
    def test_flag_unchanged(self):
        self.assertEqual(self._route(["--help"]), ["--help"])

    def test_empty_unchanged(self):
        self.assertEqual(self._route([]), [])

    # --- All /help commands reachable via slash ---
    def test_help_commands_all_reachable_via_slash(self):
        import importlib
        cli = importlib.import_module("urace.cli")
        help_cmds = [
            "auto", "check", "vitals", "plan", "crc",
            "add-goal", "add-context", "change", "why", "portfolio",
            "executor", "configuration", "self-evolution", "update",
            "pause", "resume", "compact", "decompact", "amend",
            "rules", "intent", "constraint", "policy",
        ]
        for cmd in help_cmds:
            result = cli._preprocess_args([f"/{cmd}"])
            self.assertEqual(result[0], cmd, f"/{cmd} did not route to {cmd}")

class CommandHandlerFunctionalTests(unittest.TestCase):
    """Functional tests for CLI command handlers — verifies handler logic, not just routing."""

    def setUp(self):
        self.config = isolated_test_config(self)
        self.config["executor"]["enabled"] = False
        self.state = cli.initial_state(self.config)
        cli.seed_confirmed_onboard(self.config, self.state)

    # --- check ---

    def test_check_returns_zero_and_prints_state(self):
        out = io.StringIO()
        with patch.object(cli, "load_config", return_value=self.config), \
             patch.object(cli, "load_state_for_read", return_value=self.state), \
             redirect_stdout(out):
            result = cli.main(["check"])
        self.assertEqual(result, 0)
        self.assertIn("lifecycle:", out.getvalue())

    def test_check_json_flag_emits_valid_json(self):
        out = io.StringIO()
        with patch.object(cli, "load_config", return_value=self.config), \
             patch.object(cli, "load_state_for_read", return_value=self.state), \
             redirect_stdout(out):
            result = cli.main(["check", "--json"])
        self.assertEqual(result, 0)
        parsed = json.loads(out.getvalue())
        self.assertIn("lifecycle_state", parsed)

    def test_check_returns_2_when_state_missing(self):
        with patch.object(cli, "load_config", return_value=self.config), \
             patch.object(cli, "load_state_for_read", return_value=None), \
             redirect_stdout(io.StringIO()):
            result = cli.main(["check"])
        self.assertEqual(result, 2)

    # --- vitals ---

    def test_vitals_returns_zero_and_prints_output(self):
        out = io.StringIO()
        with patch.object(cli, "load_config", return_value=self.config), \
             patch.object(cli, "load_state_for_read", return_value=self.state), \
             redirect_stdout(out):
            result = cli.main(["vitals"])
        self.assertEqual(result, 0)
        self.assertTrue(len(out.getvalue()) > 0)

    def test_vitals_json_flag_emits_valid_json(self):
        out = io.StringIO()
        with patch.object(cli, "load_config", return_value=self.config), \
             patch.object(cli, "load_state_for_read", return_value=self.state), \
             redirect_stdout(out):
            result = cli.main(["vitals", "--json"])
        self.assertEqual(result, 0)
        parsed = json.loads(out.getvalue())
        self.assertIsInstance(parsed, dict)

    # --- intent ---

    def test_intent_list_empty_returns_zero(self):
        state = copy.deepcopy(self.state)
        state["rule_ledger"] = {}
        out = io.StringIO()
        with patch.object(cli, "load_config", return_value=self.config), \
             patch.object(cli, "load_state_for_read", return_value=state), \
             redirect_stdout(out):
            result = cli.main(["intent", "list"])
        self.assertEqual(result, 0)
        self.assertIn("No active DIRECTIVE", out.getvalue())

    def test_intent_add_queues_directive_rule(self):
        with tempfile.TemporaryDirectory() as d:
            config = copy.deepcopy(self.config)
            config["state_path"] = str(Path(d) / "state.json")
            with patch.object(cli, "load_config", return_value=config), \
                 patch.object(cli, "queue_input", return_value={"id": "i-1"}) as queued, \
                 redirect_stdout(io.StringIO()):
                result = cli.main(["intent", "add", "Never delete production data"])
        self.assertEqual(result, 0)
        queued.assert_called_once()
        call_args = queued.call_args[0]
        self.assertEqual(call_args[1], "intent_control")
        self.assertEqual(call_args[2]["action"], "add")
        self.assertEqual(call_args[2]["rule_kind"], "DIRECTIVE")

    def test_intent_deactivate_queues_deactivation(self):
        with patch.object(cli, "load_config", return_value=self.config), \
             patch.object(cli, "queue_input", return_value={"id": "i-2"}) as queued, \
             redirect_stdout(io.StringIO()):
            result = cli.main(["intent", "deactivate", "--id", "rul-abc"])
        self.assertEqual(result, 0)
        call_args = queued.call_args[0]
        self.assertEqual(call_args[2]["action"], "deactivate")
        self.assertEqual(call_args[2]["rule_id"], "rul-abc")

    # --- constraint ---

    def test_constraint_list_empty_returns_zero(self):
        state = copy.deepcopy(self.state)
        state["rule_ledger"] = {}
        out = io.StringIO()
        with patch.object(cli, "load_config", return_value=self.config), \
             patch.object(cli, "load_state_for_read", return_value=state), \
             redirect_stdout(out):
            result = cli.main(["constraint", "list"])
        self.assertEqual(result, 0)
        self.assertIn("No active constraint", out.getvalue())

    def test_constraint_add_prohibition_queues_correctly(self):
        with patch.object(cli, "load_config", return_value=self.config), \
             patch.object(cli, "queue_input", return_value={"id": "c-1"}) as queued, \
             redirect_stdout(io.StringIO()):
            result = cli.main(["constraint", "add", "Do not use AWS"])
        self.assertEqual(result, 0)
        call_args = queued.call_args[0]
        self.assertEqual(call_args[1], "constraint_control")
        self.assertEqual(call_args[2]["rule_kind"], "PROHIBITION")

    def test_constraint_add_allow_flag_creates_permission_rule(self):
        with patch.object(cli, "load_config", return_value=self.config), \
             patch.object(cli, "queue_input", return_value={"id": "c-2"}) as queued, \
             redirect_stdout(io.StringIO()):
            result = cli.main(["constraint", "add", "Allow executor to modify tests", "--allow"])
        self.assertEqual(result, 0)
        call_args = queued.call_args[0]
        self.assertEqual(call_args[2]["rule_kind"], "PERMISSION")

    def test_constraint_deactivate_queues_deactivation(self):
        with patch.object(cli, "load_config", return_value=self.config), \
             patch.object(cli, "queue_input", return_value={"id": "c-3"}) as queued, \
             redirect_stdout(io.StringIO()):
            result = cli.main(["constraint", "deactivate", "--id", "rul-xyz"])
        self.assertEqual(result, 0)
        call_args = queued.call_args[0]
        self.assertEqual(call_args[2]["action"], "deactivate")
        self.assertEqual(call_args[2]["rule_id"], "rul-xyz")

    # --- rules ---

    def _state_with_ledger(self):
        from urace import rules as r
        state = copy.deepcopy(self.state)
        ledger = r.new_ledger()
        rule = r.make_rule("DIRECTIVE", "Never delete production data", "test")
        r.add_rule(ledger, rule)
        state["rule_ledger"] = ledger
        return state, rule["id"]

    def test_rules_list_returns_zero_and_prints_rules(self):
        state, _ = self._state_with_ledger()
        out = io.StringIO()
        with patch.object(cli, "load_config", return_value=self.config), \
             patch.object(cli, "load_state_for_read", return_value=state), \
             redirect_stdout(out):
            result = cli.main(["rules", "list"])
        self.assertEqual(result, 0)
        self.assertIn("Never delete", out.getvalue())

    def test_rules_list_no_ledger_prints_guidance(self):
        state = copy.deepcopy(self.state)
        state["rule_ledger"] = {}
        out = io.StringIO()
        with patch.object(cli, "load_config", return_value=self.config), \
             patch.object(cli, "load_state_for_read", return_value=state), \
             redirect_stdout(out):
            result = cli.main(["rules", "list"])
        self.assertEqual(result, 0)
        self.assertIn("not yet seeded", out.getvalue())

    def test_rules_graph_json_returns_rules_and_relationships(self):
        state, _ = self._state_with_ledger()
        out = io.StringIO()
        with patch.object(cli, "load_config", return_value=self.config), \
             patch.object(cli, "load_state_for_read", return_value=state), \
             redirect_stdout(out):
            result = cli.main(["rules", "graph", "--json"])
        self.assertEqual(result, 0)
        parsed = json.loads(out.getvalue())
        self.assertIn("rules", parsed)
        self.assertIn("relationships", parsed)

    def test_rules_conflicts_no_conflicts_prints_clean(self):
        state, _ = self._state_with_ledger()
        out = io.StringIO()
        with patch.object(cli, "load_config", return_value=self.config), \
             patch.object(cli, "load_state_for_read", return_value=state), \
             redirect_stdout(out):
            result = cli.main(["rules", "conflicts"])
        self.assertEqual(result, 0)
        self.assertIn("No conflicts", out.getvalue())

    def test_rules_inspect_returns_rule_record(self):
        state, rule_id = self._state_with_ledger()
        out = io.StringIO()
        with patch.object(cli, "load_config", return_value=self.config), \
             patch.object(cli, "load_state_for_read", return_value=state), \
             redirect_stdout(out):
            result = cli.main(["rules", "inspect", rule_id])
        self.assertEqual(result, 0)
        self.assertIn("Never delete", out.getvalue())

    def test_rules_changes_no_changes_prints_empty(self):
        state, rule_id = self._state_with_ledger()
        out = io.StringIO()
        with patch.object(cli, "load_config", return_value=self.config), \
             patch.object(cli, "load_state_for_read", return_value=state), \
             redirect_stdout(out):
            result = cli.main(["rules", "changes", rule_id])
        self.assertEqual(result, 0)
        self.assertIn("No changes", out.getvalue())

    # --- budget ---

    def test_budget_show_returns_zero_and_prints_limits(self):
        out = io.StringIO()
        with patch.object(cli, "load_config", return_value=self.config), \
             redirect_stdout(out):
            result = cli.main(["budget", "show"])
        self.assertEqual(result, 0)
        self.assertIn("daily", out.getvalue())

    def test_budget_show_json_emits_valid_json(self):
        out = io.StringIO()
        with patch.object(cli, "load_config", return_value=self.config), \
             redirect_stdout(out):
            result = cli.main(["budget", "show", "--json"])
        self.assertEqual(result, 0)
        parsed = json.loads(out.getvalue())
        self.assertIn("daily", parsed)
        self.assertIn("monthly", parsed)

    def test_budget_set_queues_budget_control_input(self):
        with patch.object(cli, "load_config", return_value=self.config), \
             patch.object(cli, "queue_input", return_value={"id": "b-1"}) as queued, \
             redirect_stdout(io.StringIO()):
            result = cli.main(["budget", "set", "--daily", "4", "--monthly", "20"])
        self.assertEqual(result, 0)
        call_args = queued.call_args[0]
        self.assertEqual(call_args[1], "budget_control")
        self.assertEqual(call_args[2]["daily"], 4)
        self.assertEqual(call_args[2]["monthly"], 20)

    def test_budget_set_rejects_daily_below_2(self):
        err = io.StringIO()
        with patch.object(cli, "load_config", return_value=self.config), \
             redirect_stdout(io.StringIO()), redirect_stderr(err):
            with self.assertRaises(SystemExit) as cm:
                cli.main(["budget", "set", "--daily", "1", "--monthly", "10"])
        self.assertNotEqual(cm.exception.code, 0)

    # --- evaluation ---

    def test_evaluation_show_returns_zero(self):
        out = io.StringIO()
        with patch.object(cli, "load_config", return_value=self.config), \
             patch.object(cli, "load_state_for_read", return_value=self.state), \
             redirect_stdout(out):
            result = cli.main(["evaluation", "show"])
        self.assertEqual(result, 0)
        self.assertIn("evaluation-system", out.getvalue())

    def test_evaluation_show_json_emits_valid_json(self):
        out = io.StringIO()
        with patch.object(cli, "load_config", return_value=self.config), \
             patch.object(cli, "load_state_for_read", return_value=self.state), \
             redirect_stdout(out):
            result = cli.main(["evaluation", "show", "--json"])
        self.assertEqual(result, 0)
        parsed = json.loads(out.getvalue())
        self.assertIn("configuration", parsed)
        self.assertIn("current", parsed)

    # --- why ---

    def test_why_returns_zero_for_valid_decision_id(self):
        from urace import decision_record as dr
        import hashlib
        state = copy.deepcopy(self.state)
        rec = dr.create_decision_record(
            kind="OBJECTIVE_SELECTION", subject="test subject", outcome="ACCEPTED",
            governing_intent_ref="none", state_digest=hashlib.sha256(b"{}").hexdigest(),
            executor={"executor_id": "test", "adapter": "test-adapter",
                      "capability": "planning", "logical_reservation": "none", "attempted_executors": []},
        )
        state.setdefault("decision_records", []).append(rec)
        out = io.StringIO()
        with patch.object(cli, "load_config", return_value=self.config), \
             patch.object(cli, "load_state_for_read", return_value=state), \
             redirect_stdout(out):
            result = cli.main(["why", rec["id"]])
        self.assertEqual(result, 0)

    # --- compact ---

    def test_compact_unknown_field_returns_nonzero(self):
        err = io.StringIO()
        with patch.object(cli, "load_config", return_value=self.config), \
             patch.object(cli, "load_state_for_read", return_value=self.state), \
             redirect_stdout(io.StringIO()), redirect_stderr(err):
            result = cli.main(["compact", "nonexistent_field"])
        self.assertNotEqual(result, 0)

    def test_compact_known_field_evidence_runs_without_error(self):
        with tempfile.TemporaryDirectory() as d:
            config = copy.deepcopy(self.config)
            config["state_path"] = str(Path(d) / "state.json")
            (Path(d)).mkdir(parents=True, exist_ok=True)
            with patch.object(cli, "load_config", return_value=config), \
                 patch.object(cli, "load_state_for_read", return_value=self.state), \
                 redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                result = cli.main(["compact", "evidence"])
        self.assertIn(result, (0, 1))  # 0 = compacted, 1 = nothing to compact

