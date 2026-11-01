"""Synthetic fixtures verify the gate; they are never evidence of real-user benefit."""
import copy
import hashlib
import json
import runpy
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from urace import cli, inspection, outcome_verification as outcomes, validation, value_trajectory


class ValueProductionTests(unittest.TestCase):
    def setUp(self):
        d = tempfile.TemporaryDirectory(prefix="urace-value-test-")
        self.addCleanup(d.cleanup)
        self.root = Path(d.name)
        self.source = self.root / "calculator.py"
        self.source.write_text("def add(a, b):\n    return a + b + 1\n" + "# fixture padding\n" * 90)
        self.config = copy.deepcopy(cli.load_config())
        self.config.pop("active_product", None)
        self.config.update(state_path=str(self.root / "state/state.json"), product_files=["calculator.py"],
                           scope_priority={"scopes": {}}, change_explanations={"mode": "disabled"},
                           efficiency={"max_product_growth_ratio_per_change": 2, "max_product_growth_bytes_per_change": 10000})
        self.config["executor"].update(allowed_files_by_scope={"runtime": ["calculator.py"], "documentation": ["guide.md"]},
                                      max_executor_calls_per_24h=100, max_executor_calls_per_30d=100)
        for obj in (cli, inspection):
            patcher = patch.object(obj, "ROOT", self.root)
            patcher.start(); self.addCleanup(patcher.stop)
        self.state = cli.initial_state(self.config)
        self.state.pop("rule_ledger", None)

    def execute(self, new_text, number=1):
        old = self.source.read_text()
        objective = {"id": f"goal-{number}", "title": "Correct results", "reason": "independent task checks", "scope": "runtime", "success_measure": "three correct results"}
        candidate = {"status": "PREPARED", "changed_files": ["calculator.py"], "contents": {"calculator.py": new_text},
                     "base_hashes": {"calculator.py": hashlib.sha256(old.encode()).hexdigest()}, "message": "candidate"}
        self.state["objectives"].append(objective)
        with patch.object(cli.intelligent_executor, "execute", return_value=candidate):
            result = cli.execute_with_executor(self.config, self.state, objective, {"id": f"plan-{number}"})
        return objective, result

    def measure(self):
        definition = {"source": "outcomes.json", "independent": True, "evidence_kind": "engineering",
                      "direction": "nondecreasing", "target": 1, "experiment_id": "task-success"}
        self.config["outcome_verification"] = {"measures": {"goal-1": definition}}
        self.payload = {"baseline": {"id": "baseline", "at": (datetime.now(timezone.utc)-timedelta(days=5)).isoformat(), "successes": 0, "trials": 3}, "observations": []}
        self.write()

    def write(self):
        (self.root / "outcomes.json").write_text(json.dumps(self.payload))

    def test_padding_cannot_complete_goal_or_earn_value(self):
        objective, result = self.execute(self.source.read_text() + "\n# MUST MUST MUST\n")
        self.assertEqual(result["status"], "ACCEPTED")
        self.assertEqual(objective["status"], "awaiting_outcome")
        self.assertFalse(result["real_user_value_verified"])
        self.assertEqual(self.state["value_trajectory"]["cumulative_value"], 0)

    def test_two_changes_survive_reload_and_validate_files(self):
        self.execute(self.source.read_text() + "\n# first increment\n")
        self.state = cli.load_state(self.config)
        _, result = self.execute(self.source.read_text() + "\n# second increment\n", 2)
        self.assertEqual(result["status"], "ACCEPTED")
        self.assertEqual([o["status"] for o in self.state["operations"]], ["ACCEPTED", "ACCEPTED"])
        checks = self.state["operations"][-1]["independent_validation"]["checks"]
        self.assertTrue(any(c["check"] == "file_present:calculator.py" and c["result"] == "PASS" for c in checks))
        self.assertEqual(cli.load_state(self.config)["operations"][-1]["status"], "ACCEPTED")

    def test_useful_fix_needs_independent_measurement_and_is_not_real_user_proof(self):
        self.measure()
        cases = [(2, 2, 4), (0, 0, 0), (-3, 5, 2)]
        def successes():
            add = runpy.run_path(str(self.source))["add"]
            return sum(add(a, b) == expected for a, b, expected in cases)
        self.assertEqual(successes(), 0)
        objective, result = self.execute(self.source.read_text().replace("a + b + 1", "a + b"))
        self.assertEqual(result["outcome_status"], "PENDING_OUTCOME")
        self.assertEqual(successes(), 3)
        op = self.state["operations"][-1]
        self.payload["observations"] = [{"id": "result", "operation_id": op["id"], "experiment_id": "task-success",
            "window_start": op["applied_at"], "at": cli.now(), "successes": successes(), "trials": 3}]
        self.write(); outcomes.refresh(self.root, self.config, self.state)
        self.assertEqual(objective["status"], "completed")
        self.assertEqual(op["outcome"]["status"], "OUTCOME_VERIFIED")
        self.assertFalse(op["outcome"]["real_user_value_verified"])
        self.assertGreater(self.state["value_trajectory"]["cumulative_value"], 0)
        count = len(self.state["value_trajectory"]["checkpoints"])
        outcomes.refresh(self.root, self.config, self.state)
        self.assertEqual(len(self.state["value_trajectory"]["checkpoints"]), count)

    def test_executor_cannot_write_outcome_source(self):
        self.measure()
        self.config["executor"]["allowed_files_by_scope"]["runtime"].append("outcomes.json")
        _, result = self.execute(self.source.read_text() + "\n# change\n")
        self.assertEqual(result["outcome_status"], "PENDING_OUTCOME")
        self.assertIn("executor-writable", self.state["operations"][-1]["outcome"]["reason"])

    def test_scope_violation_is_rejected_before_write(self):
        old = self.source.read_text()
        self.config["executor"]["allowed_files_by_scope"]["runtime"] = []
        with self.assertRaisesRegex(RuntimeError, "before application"):
            self.execute(old.replace("a + b + 1", "a + b"))
        self.assertEqual(self.source.read_text(), old)
        self.assertFalse(cli.transaction_path(self.config).exists())

    def test_empty_evidence_and_cross_scope_validation_fail(self):
        op = {"scope": "documentation", "authority_basis": "fixture"}
        self.assertEqual(validation.validate_operation(self.root, op, {}, {}, {}, {})["verdict"], "REJECTED")
        op["changed_files"] = ["calculator.py"]
        self.assertEqual(validation.validate_operation(self.root, op, {"count": 1}, {"count": 1}, self.config, {})["verdict"], "REJECTED")
        cfg = {"executor": {"allowed_files_by_scope": {"runtime": ["../outside.py"]}}}
        self.assertTrue(validation.candidate_file_errors(self.root, "runtime", ["../outside.py"], cfg))

    def test_direction_and_losses_are_accounted_for(self):
        state = {}
        def checkpoint(before, after):
            return value_trajectory.record_checkpoint(state, {}, {"defects": before}, {"defects": after}, 60, {"defects": "nonincreasing"})
        self.assertLess(checkpoint(1, 10)["net_value_delta"], 0)
        self.assertGreater(checkpoint(10, 1)["net_value_delta"], 0)
        self.assertEqual(state["value_trajectory"]["cumulative_value"], 0)
        self.assertEqual(state["value_trajectory"]["acceleration"]["cumulative_value"], 0)

    def test_completed_and_awaiting_goals_require_feedback(self):
        for status in ("completed", "awaiting_outcome"):
            state = {"lifecycle_state": "ACTIVE", "objectives": [{"id": "goal", "status": status, "updated_at": "2000-01-01T00:00:00+00:00"}]}
            cli._run_feedback_accumulator({"feedback": {"window_hours": 1}}, state)
            self.assertTrue(any(g["kind"] == "feedback-overdue" for g in state["integrity_gaps"]))

    def test_nested_external_values_and_observed_cost_and_time(self):
        state = {"lifecycle_state": "ACTIVE", "created_at": cli.now(), "executor_state": {"executor_calls": [
            {"id": "call", "at": cli.now(), "elapsed_seconds": 60, "usage": {"reported_cost_usd": 0.2}}]},
            "external_metric_state": {"latest": [{"source": "users", "values": {"completion": 0.5}}]}}
        config = {"product_budget": {"metric_directions": {"users.completion": "nondecreasing"}, "hourly_rate": 60}}
        cli._run_ram(config, state)
        state["external_metric_state"]["latest"][0]["values"]["completion"] = 0.8
        cli._run_ram(config, state)
        entry = state["resource_ledger"][-1]
        self.assertAlmostEqual(entry["delta_metrics"], 0.3)
        self.assertAlmostEqual(entry["time_hours"], 1/60)
        self.assertAlmostEqual(entry["total_cost"], 1.2)
        self.assertIsNone(entry["roi"])

    def test_period_snapshot_does_not_double_count(self):
        start = (datetime.now(timezone.utc)-timedelta(days=2)).isoformat()
        state = {"lifecycle_state": "ACTIVE", "created_at": start, "resource_period_start": start,
            "resource_ledger": [{"period_start": start, "total_cost": 1, "roi": None}, {"period_start": start, "total_cost": 2, "roi": None}]}
        cli._run_ram({"product_budget": {"period": "DAILY"}}, state)
        cli._run_ram({"product_budget": {"period": "DAILY"}}, state)
        self.assertEqual(len(state["roi_snapshots"]), 1)
        self.assertEqual(state["roi_snapshots"][0]["total_cost"], 2)

    def test_validation_unavailable_restores_product_and_keeps_observation(self):
        old = self.source.read_text()
        pending = {"verdict": "PENDING_CAPABILITY", "basis": "independent validator unavailable"}
        with patch.object(cli.independent_validation, "validate_operation", return_value=pending):
            goal, result = self.execute(old.replace("a + b + 1", "a + b"))
        self.assertEqual(result["status"], "PENDING_VALIDATION")
        self.assertEqual(goal["status"], "awaiting_validation")
        self.assertEqual(self.source.read_text(), old)
        self.assertEqual(len(self.state["pending_validations"]), 1)
        self.assertNotEqual(self.state["operations"][-1]["status"], "ACCEPTED")

    def test_validation_exception_rolls_back_and_persists_failure(self):
        old = self.source.read_text()
        with patch.object(cli.independent_validation, "validate_operation", side_effect=ValueError("validator error")):
            with self.assertRaisesRegex(ValueError, "validator error"):
                self.execute(old.replace("a + b + 1", "a + b"))
        self.assertEqual(self.source.read_text(), old)
        self.assertEqual(cli.load_state(self.config)["operations"][-1]["status"], "REJECTED_VALIDATION_ERROR")


    def test_onboarding_resolves_relative_product_files_from_product_root(self):
        # The product is readable at ROOT; the CLI is invoked from a different CWD.
        self.config["product_files"] = ["calculator.py"]
        cli.save_state(self.config, self.state)
        import contextlib, io, os
        previous = Path.cwd()
        elsewhere = self.root / "runtime-working-directory"
        elsewhere.mkdir()
        try:
            os.chdir(elsewhere)
            with patch.object(cli, "load_config", return_value=self.config), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(cli.main(["onboard", "confirm"]), 0)
        finally:
            os.chdir(previous)
        record = cli.load_state(self.config)["onboard_records"][-1]
        self.assertEqual(record["confirmed_by"], "operator")

    def test_onboarding_still_rejects_truly_missing_product_files(self):
        self.config["product_files"] = ["actually-missing.md"]
        cli.save_state(self.config, self.state)
        import contextlib, io
        with patch.object(cli, "load_config", return_value=self.config), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main(["onboard", "confirm"]), 1)


    def test_actual_spec_passes_structural_validation_after_section_renumbering(self):
        source_root = Path(__file__).resolve().parents[3]
        for name in ("URACE.md", "README.md"):
            (self.root / name).write_text((source_root / name).read_text())
        self.config["product_files"] = ["URACE.md", "README.md"]
        self.assertEqual(cli.validate_product(self.config), [])

    def test_final_invariant_requires_a_heading_not_an_incidental_mention(self):
        text = "# URACE\nPrimary invariant:\n# 79. Bootstrap Execution Requirements\nFinal Invariant mentioned in prose.\n" + "MUST preserve behavior.\n" * 100
        (self.root / "URACE.md").write_text(text)
        self.config["product_files"] = ["URACE.md"]
        self.assertIn("URACE.md lost required heading: Final Invariant", cli.validate_product(self.config))



class RealUserEvidenceGateTests(unittest.TestCase):
    """Simulated trial records, not real customers or a live value-production trial."""
    def setUp(self):
        d = tempfile.TemporaryDirectory(prefix="urace-trial-test-")
        self.addCleanup(d.cleanup); self.root = Path(d.name)
        self.now = datetime.now(timezone.utc)
        self.measure = {"source": "trial.json", "independent": True, "evidence_kind": "real_user", "direction": "nondecreasing",
            "target": 0.8, "min_delta": 0.1, "experiment_id": "trial-1", "comparison_design": "randomized_control", "value_per_success": 1, "currency": "USD",
            "guardrails": {"complaint_rate": {"max": 0.05}}}
        self.payload = {"baseline": {"id": "baseline", "at": (self.now-timedelta(days=5)).isoformat(), "successes": 500, "trials": 1000}, "observations": []}
        self.write()
        self.config = {"outcome_verification": {"measures": {"goal": self.measure}}}
        self.op = {"id": "op", "objective_reference": "goal", "status": "ACCEPTED", "applied_at": (self.now-timedelta(days=3)).isoformat(),
                   "usage": {"reported_cost_usd": 1}, "outcome_contract": outcomes.capture(self.root, self.config, {"id": "goal"})}
        for i in range(3):
            start = self.now-timedelta(hours=72-i*24)
            self.payload["observations"].append({"id": f"window-{i}", "operation_id": "op", "experiment_id": "trial-1",
                "window_start": start.isoformat(), "at": (start+timedelta(hours=1)).isoformat(),
                "successes": 900, "trials": 1000, "control_successes": 500, "control_trials": 1000, "cost": 2, "guardrails": {"complaint_rate": 0.01}})
        self.write()

    def write(self):
        (self.root / "trial.json").write_text(json.dumps(self.payload))

    def evaluate(self):
        self.write(); return outcomes.evaluate(self.root, self.op, at=self.now)

    def test_repeated_controlled_net_positive_trial_passes_gate(self):
        result = self.evaluate()
        self.assertEqual(result["status"], "REAL_USER_VALUE_VERIFIED")
        self.assertGreater(result["net_benefit"], 0)
        self.assertEqual(result["observed_cost"], 7)
        self.assertEqual(result["windows"], 3)

    def test_one_window_does_not_establish_reliability(self):
        self.payload["observations"] = self.payload["observations"][-1:]
        self.assertFalse(self.evaluate()["real_user_value_verified"])

    def test_missing_control_or_cost_never_verifies(self):
        for field in ("control_successes", "control_trials", "cost"):
            with self.subTest(field=field):
                row = self.payload["observations"][-1]; saved = row.pop(field)
                self.assertFalse(self.evaluate()["real_user_value_verified"])
                row[field] = saved

    def test_excess_cost_is_not_positive_value(self):
        for row in self.payload["observations"]: row["cost"] = 10000
        self.assertEqual(self.evaluate()["status"], "NOT_ACHIEVED")

    def test_missing_execution_cost_is_unknown(self):
        self.op["usage"] = {}
        self.assertEqual(self.evaluate()["status"], "PENDING_OUTCOME")

    def test_guardrails_override_improvement(self):
        self.payload["observations"][-1]["guardrails"]["complaint_rate"] = 0.2
        self.assertEqual(self.evaluate()["status"], "REGRESSED")

    def test_weak_comparison_does_not_verify(self):
        for row in self.payload["observations"]: row["control_successes"] = 890
        self.assertEqual(self.evaluate()["status"], "PENDING_OUTCOME")

    def test_duplicate_and_overlapping_windows_rejected(self):
        self.payload["observations"][-1]["id"] = "window-0"
        self.assertFalse(self.evaluate()["real_user_value_verified"])
        self.payload["observations"][-1]["id"] = "window-2"
        self.payload["observations"][-1]["window_start"] = self.payload["observations"][0]["window_start"]
        self.assertFalse(self.evaluate()["real_user_value_verified"])

    def test_wrong_operation_and_future_evidence_do_not_verify(self):
        self.payload["observations"][-1]["operation_id"] = "other"
        self.assertFalse(self.evaluate()["real_user_value_verified"])
        self.payload["observations"][-1]["operation_id"] = "op"
        self.payload["observations"][-1]["at"] = (self.now+timedelta(days=1)).isoformat()
        self.assertFalse(self.evaluate()["real_user_value_verified"])

    def test_contract_and_baseline_are_frozen(self):
        self.measure["target"] = 0.1
        self.payload["baseline"]["successes"] = 0
        self.assertEqual(self.evaluate()["baseline"], 0.5)
        self.assertEqual(self.op["outcome_contract"]["measure"]["target"], 0.8)
        self.op["outcome_contract"]["measure"]["target"] = 0.1
        self.assertFalse(self.evaluate()["real_user_value_verified"])

    def test_stale_evidence_withdraws_credit_and_completion(self):
        state = {"operations": [self.op], "objectives": [{"id": "goal", "status": "awaiting_outcome"}], "evidence": []}
        outcomes.refresh(self.root, self.config, state)
        self.assertEqual(state["objectives"][0]["status"], "completed")
        actual = outcomes.evaluate
        with patch.object(outcomes, "evaluate", side_effect=lambda root, op, **kw: actual(root, op, at=self.now+timedelta(days=2), **kw)):
            outcomes.refresh(self.root, self.config, state)
        self.assertEqual(state["objectives"][0]["status"], "awaiting_outcome")
        self.assertFalse(self.op["outcome"]["real_user_value_verified"])
        self.assertAlmostEqual(state["value_trajectory"]["cumulative_value"], 0)

    def test_newly_writable_source_loses_independence(self):
        self.config["executor"] = {"allowed_files_by_scope": {"runtime": ["trial.json"]}}
        state = {"operations": [self.op], "objectives": [{"id": "goal"}], "evidence": []}
        outcomes.refresh(self.root, self.config, state)
        self.assertFalse(self.op["outcome"]["real_user_value_verified"])
        self.assertIn("executor-writable", self.op["outcome"]["reason"])


    def test_negative_feedback_withdraws_value_even_when_measurement_improves(self):
        state = {"operations": [self.op], "objectives": [{"id": "goal"}], "evidence": []}
        outcomes.refresh(self.root, self.config, state)
        state["outcome_feedback_records"] = [{"target_kind": "OBJECTIVE", "target_id": "goal", "signal": "NEGATIVE", "at": cli.now()}]
        outcomes.refresh(self.root, self.config, state)
        self.assertEqual(self.op["outcome"]["status"], "CONTESTED")
        self.assertFalse(self.op["outcome"]["real_user_value_verified"])
        self.assertEqual(state["objectives"][0]["status"], "awaiting_outcome")
        self.assertAlmostEqual(state["value_trajectory"]["cumulative_value"], 0)


    def test_nonfinite_data_never_verifies(self):
        self.payload["observations"][-1]["cost"] = float("nan")
        self.assertFalse(self.evaluate()["real_user_value_verified"])

    def test_synthetic_outcomes_never_claim_real_user_value(self):
        measure = self.op["outcome_contract"]["measure"]
        measure["evidence_kind"] = "synthetic"
        self.op["outcome_contract"]["contract_hash"] = hashlib.sha256(json.dumps(measure, sort_keys=True).encode()).hexdigest()
        result = self.evaluate()
        self.assertEqual(result["status"], "OUTCOME_VERIFIED")
        self.assertFalse(result["real_user_value_verified"])


class ExecutorPreparationTests(unittest.TestCase):
    def setUp(self):
        from urace import executor
        self.executor = executor
        directory = tempfile.TemporaryDirectory(prefix="urace-preparation-test-")
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        (self.root / "guide.md").write_text("Original guidance")
        for name in executor.evolution_guard.PROTECTED_FILES:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# accepted kernel fixture\n")
        self.support = "urace/runtime/urace/support.py"
        (self.root / self.support).write_text("VALUE = 1\n")
        self.config = {"executor": {"allowed_files_by_scope": {"documentation": ["guide.md"]}}}
        self.objective = {"title": "Improve guide", "reason": "fixture task", "scope": "documentation"}

    def test_full_runtime_support_is_present_and_readonly(self):
        def transport(workspace, *args):
            self.assertEqual((workspace / self.support).read_text(), "VALUE = 1\n")
            (workspace / "guide.md").write_text("Improved guidance")
            return {"message": "done"}
        with patch.object(self.executor, "run_routed_codex", side_effect=transport):
            candidate = self.executor.execute(self.root, self.config, {}, self.objective)
        self.assertEqual(candidate["changed_files"], ["guide.md"])
        self.assertEqual((self.root / "guide.md").read_text(), "Original guidance")

    def test_modifying_readonly_support_rejects_candidate(self):
        def transport(workspace, *args):
            (workspace / self.support).write_text("VALUE = 2\n")
            return {"message": "tampered"}
        with patch.object(self.executor, "run_routed_codex", side_effect=transport):
            with self.assertRaisesRegex(RuntimeError, "read-only validation support"):
                self.executor.execute(self.root, self.config, {}, self.objective)
        self.assertEqual((self.root / self.support).read_text(), "VALUE = 1\n")

    def test_runtime_validation_uses_larger_bounded_timeout(self):
        config_path = "urace/runtime/urace/config.json"
        (self.root / config_path).write_text("{}")
        self.config["executor"]["allowed_files_by_scope"]["runtime"] = ["guide.md", config_path]
        self.objective["scope"] = "runtime"
        def transport(workspace, *args):
            (workspace / "guide.md").write_text("Improved guidance")
            return {"message": "done"}
        with patch.object(self.executor, "run_routed_codex", side_effect=transport), patch.object(
            self.executor.subprocess, "run", return_value=type("Completed", (), {"returncode": 0, "stdout": "OK"})()
        ) as run, patch.object(self.executor.evolution_guard, "validate_candidate", return_value=[]):
            self.executor.execute(self.root, self.config, {}, self.objective)
        self.assertEqual(run.call_args.kwargs["timeout"], 900)

    def test_readonly_report_refuses_to_claim_real_value_from_no_evidence(self):
        state_path, config_path = self.root / "state.json", self.root / "config.json"
        state_path.write_text(json.dumps({"operations": [{"id": "op", "status": "ACCEPTED"}]}))
        config_path.write_text(json.dumps(self.config))
        result = subprocess.run([sys.executable, "-m", "urace.outcome_verification", "--root", str(self.root),
            "--state", str(state_path), "--config", str(config_path)], capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 2)
        self.assertFalse(json.loads(result.stdout)["observed_trial_evidence_satisfies_contract"])


if __name__ == "__main__": unittest.main()
