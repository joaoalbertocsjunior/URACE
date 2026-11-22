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


class R23AdditionsTests(unittest.TestCase):
    """r23: RecoveryManifest, ExecutionBudget, ProgressVector, failure_type."""

    def _valid_execution_budget(self):
        return {"max_iterations": 100, "max_executor_calls": 50, "iterations_used": 0, "executor_calls_used": 0}

    def _valid_recovery_manifest(self):
        return {
            "manifest_id": "manifest-001",
            "emitted_at": "2026-10-12T00:00:00+00:00",
            "emission_cause": "repair-exhausted",
            "last_safe_state": "REPAIRING",
            "last_safe_commit": "checkpoint-abc",
            "failure_summary": ["stage:error"],
            "goal_delta": "objective-1 incomplete",
            "progress_at_emit": 0.5,
            "execution_mode": "auto",
        }

    def test_execution_budget_validator_valid(self):
        from urace import primitives as p
        p.validate_execution_budget(self._valid_execution_budget())

    def test_execution_budget_validator_rejects_zero_max_iterations(self):
        from urace import primitives as p
        bad = self._valid_execution_budget()
        bad["max_iterations"] = 0
        with self.assertRaises(ValueError):
            p.validate_execution_budget(bad)

    def test_execution_budget_validator_rejects_zero_max_executor_calls(self):
        from urace import primitives as p
        bad = self._valid_execution_budget()
        bad["max_executor_calls"] = 0
        with self.assertRaises(ValueError):
            p.validate_execution_budget(bad)

    def test_execution_budget_validator_rejects_missing_field(self):
        from urace import primitives as p
        bad = {"max_iterations": 10, "max_executor_calls": 10}
        with self.assertRaises(ValueError):
            p.validate_execution_budget(bad)

    def test_recovery_manifest_validator_valid(self):
        from urace import primitives as p
        p.validate_recovery_manifest(self._valid_recovery_manifest())

    def test_recovery_manifest_validator_valid_null_progress(self):
        from urace import primitives as p
        m = self._valid_recovery_manifest()
        m["progress_at_emit"] = None
        p.validate_recovery_manifest(m)

    def test_recovery_manifest_validator_invalid_cause(self):
        from urace import primitives as p
        m = self._valid_recovery_manifest()
        m["emission_cause"] = "unknown-cause"
        with self.assertRaises(ValueError):
            p.validate_recovery_manifest(m)

    def test_recovery_manifest_validator_invalid_mode(self):
        from urace import primitives as p
        m = self._valid_recovery_manifest()
        m["execution_mode"] = "batch"
        with self.assertRaises(ValueError):
            p.validate_recovery_manifest(m)

    def test_recovery_manifest_validator_invalid_tier(self):
        from urace import primitives as p
        m = self._valid_recovery_manifest()
        m["recommended_tier"] = "T9"
        with self.assertRaises(ValueError):
            p.validate_recovery_manifest(m)

    def test_recovery_manifest_validator_valid_tier(self):
        from urace import primitives as p
        for tier in ("T1", "T2", "T3", None):
            m = self._valid_recovery_manifest()
            m["recommended_tier"] = tier
            p.validate_recovery_manifest(m)

    def test_failure_record_failure_type_valid(self):
        from urace import primitives as p
        for ft in ("transient", "semantic", "structural"):
            p.validate_failure_record({"at": "t", "last_at": "t", "stage": "s", "error": "e", "count": 1, "failure_type": ft})

    def test_failure_record_failure_type_invalid(self):
        from urace import primitives as p
        with self.assertRaises(ValueError):
            p.validate_failure_record({"at": "t", "last_at": "t", "stage": "s", "error": "e", "count": 1, "failure_type": "catastrophic"})

    def test_failure_record_without_failure_type_still_valid(self):
        from urace import primitives as p
        p.validate_failure_record({"at": "t", "last_at": "t", "stage": "s", "error": "e", "count": 1})

    def test_executor_state_has_r23_fields(self):
        config = isolated_test_config(self)
        state = cli.initial_state(config)
        es = state["executor_state"]
        self.assertIsNone(es["progress_vector"])
        self.assertEqual(es["progress_stagnant_cycles"], 0)
        self.assertIsNone(es["execution_budget"])
        self.assertIsNone(es["recovery_manifest"])

    def test_progress_vector_increases_on_completion(self):
        state = {
            "lifecycle_state": "ACTIVE",
            "executor_state": {"progress_vector": None, "progress_stagnant_cycles": 0},
            "integrity_gaps": [],
            "objectives": [
                {"id": "o1", "status": "completed"},
                {"id": "o2", "status": "planned"},
            ],
        }
        cli._update_progress_vector(state)
        self.assertEqual(state["executor_state"]["progress_vector"], 0.5)
        self.assertEqual(state["executor_state"]["progress_stagnant_cycles"], 0)

    def test_progress_vector_stagnation_increments(self):
        state = {
            "lifecycle_state": "ACTIVE",
            "executor_state": {"progress_vector": 0.5, "progress_stagnant_cycles": 0},
            "integrity_gaps": [],
            "objectives": [
                {"id": "o1", "status": "completed"},
                {"id": "o2", "status": "planned"},
            ],
        }
        cli._update_progress_vector(state)
        self.assertEqual(state["executor_state"]["progress_stagnant_cycles"], 1)

    def test_progress_vector_stagnation_triggers_repairing(self):
        state = {
            "lifecycle_state": "ACTIVE",
            "executor_state": {"progress_vector": 0.5, "progress_stagnant_cycles": 4},
            "integrity_gaps": [],
            "objectives": [{"id": "o1", "status": "completed"}, {"id": "o2", "status": "planned"}],
        }
        cli._update_progress_vector(state, stagnation_threshold=5)
        self.assertEqual(state["lifecycle_state"], "REPAIRING")
        self.assertTrue(any(g["kind"] == "progress-stagnation" for g in state["integrity_gaps"]))

    def test_emit_recovery_manifest_populates_executor_state(self):
        state = {
            "lifecycle_state": "REPAIRING",
            "executor_state": {"progress_vector": 0.4, "failures": [], "execution_budget": None, "recovery_manifest": None},
            "objectives": [{"id": "o1", "title": "incomplete objective", "status": "planned"}],
            "checkpoints": [{"id": "chk-001", "at": "2026-10-12T00:00:00+00:00", "kind": "bootstrap", "digest": "abc"}],
        }
        manifest = cli._emit_recovery_manifest(state, "repair-exhausted", "auto")
        self.assertEqual(manifest["emission_cause"], "repair-exhausted")
        self.assertEqual(manifest["execution_mode"], "auto")
        self.assertEqual(manifest["last_safe_commit"], "chk-001")
        self.assertIn("incomplete objective", manifest["goal_delta"])
        self.assertEqual(state["executor_state"]["recovery_manifest"], manifest)

    def test_recovery_manifest_registered_in_validators(self):
        from urace import primitives as p
        self.assertIn("RecoveryManifest", p._VALIDATORS)

    def test_execution_budget_registered_in_validators(self):
        from urace import primitives as p
        self.assertIn("ExecutionBudget", p._VALIDATORS)


class R24FeedbackTests(unittest.TestCase):
    """r24: feedback verbosity modes, RecoveryManifest surfacing, discovery-deferral all states."""

    def _base_state(self):
        s = copy.deepcopy(cli.initial_state(isolated_test_config(self)))
        s["lifecycle_state"] = "DORMANT"
        return s

    def _base_outcome(self):
        return {"outcome": "dormant", "reason": "no justified action"}

    def _render(self, state, outcome, verbose=False, json_mode=False):
        from urace import inspection
        return inspection.render_cycle(state, outcome, 1, json_mode, verbose)

    def test_non_verbose_contains_lifecycle_and_outcome(self):
        state = self._base_state()
        out = self._render(state, self._base_outcome())
        self.assertIn("lifecycle=", out)
        self.assertIn("outcome=dormant", out)

    def test_non_verbose_shows_progress_vector_when_set(self):
        state = self._base_state()
        state["executor_state"]["progress_vector"] = 0.75
        out = self._render(state, self._base_outcome())
        self.assertIn("progress:", out)
        self.assertIn("75.0%", out)

    def test_non_verbose_no_progress_when_null(self):
        state = self._base_state()
        state["executor_state"]["progress_vector"] = None
        out = self._render(state, self._base_outcome())
        self.assertNotIn("progress:", out)

    def test_non_verbose_shows_recovery_pending_when_manifest_present(self):
        state = self._base_state()
        state["executor_state"]["recovery_manifest"] = {
            "manifest_id": "manifest-test-001",
            "emission_cause": "repair-exhausted",
            "progress_at_emit": 0.3,
            "goal_delta": "objective-x incomplete",
            "execution_mode": "auto",
        }
        out = self._render(state, self._base_outcome())
        self.assertIn("recovery-pending:", out)
        self.assertIn("manifest-test-001", out)
        self.assertIn("repair-exhausted", out)

    def test_non_verbose_no_recovery_when_manifest_null(self):
        state = self._base_state()
        state["executor_state"]["recovery_manifest"] = None
        out = self._render(state, self._base_outcome())
        self.assertNotIn("recovery-pending:", out)

    def test_verbose_expands_recovery_manifest(self):
        state = self._base_state()
        state["executor_state"]["recovery_manifest"] = {
            "manifest_id": "manifest-v001",
            "emission_cause": "budget-exhausted",
            "emitted_at": "2026-10-12T00:00:00+00:00",
            "last_safe_state": "REPAIRING",
            "last_safe_commit": "chk-abc",
            "progress_at_emit": 0.6,
            "goal_delta": "two objectives remain",
            "recommended_tier": "T2",
            "execution_mode": "auto",
        }
        out = self._render(state, self._base_outcome(), verbose=True)
        self.assertIn("recovery-manifest:", out)
        self.assertIn("manifest-v001", out)
        self.assertIn("budget-exhausted", out)
        self.assertIn("REPAIRING", out)
        self.assertIn("two objectives remain", out)

    def test_verbose_shows_progress_vector_and_stagnant_cycles(self):
        state = self._base_state()
        state["executor_state"]["progress_vector"] = 0.5
        state["executor_state"]["progress_stagnant_cycles"] = 3
        out = self._render(state, self._base_outcome(), verbose=True)
        self.assertIn("progress-vector:", out)
        self.assertIn("stagnant-cycles=3", out)

    def test_machine_output_includes_recovery_manifest_field(self):
        import json as _json
        state = self._base_state()
        state["executor_state"]["recovery_manifest"] = {
            "manifest_id": "manifest-json-001",
            "emission_cause": "repair-exhausted",
            "progress_at_emit": 0.2,
            "goal_delta": "delta",
            "execution_mode": "auto",
        }
        out = self._render(state, self._base_outcome(), json_mode=True)
        data = _json.loads(out)
        self.assertIn("recovery_manifest", data)
        self.assertIsNotNone(data["recovery_manifest"])
        self.assertEqual(data["recovery_manifest"]["manifest_id"], "manifest-json-001")

    def test_machine_output_includes_progress_vector(self):
        import json as _json
        state = self._base_state()
        state["executor_state"]["progress_vector"] = 0.8
        out = self._render(state, self._base_outcome(), json_mode=True)
        data = _json.loads(out)
        self.assertIn("progress_vector", data)
        self.assertEqual(data["progress_vector"], 0.8)

    def test_discovery_deferred_surfaces_for_all_deferral_states(self):
        deferral_states = [
            "SYSTEMATIC_FAILURE_COOLDOWN",
            "DAILY_LIMIT_OR_RESERVE_REACHED",
            "MONTHLY_LIMIT_OR_RESERVE_REACHED",
            "DUPLICATE_TRIGGER_SUPPRESSED",
            "DEFERRED_PROPORTIONALITY",
            "DISCOVERY_YIELD_EXHAUSTED",
            "WAITING_PROVIDER_CAPACITY",
        ]
        state = self._base_state()
        for status in deferral_states:
            state["executor_state"]["discovery_budget_status"] = status
            state["executor_state"]["discovery_defer_reason"] = f"deferred: {status}"
            out = self._render(state, self._base_outcome())
            self.assertIn("discovery-deferred:", out, f"missing for status={status}")
            self.assertIn(status, out, f"reason not shown for status={status}")

    def test_within_budget_no_deferral_line(self):
        state = self._base_state()
        state["executor_state"]["discovery_budget_status"] = "WITHIN_BUDGET"
        out = self._render(state, self._base_outcome())
        self.assertNotIn("discovery-deferred:", out)

    def test_quiet_mode_still_emits_recovery_pending(self):
        import io
        state = self._base_state()
        state["executor_state"]["recovery_manifest"] = {
            "manifest_id": "manifest-quiet-001",
            "emission_cause": "repair-exhausted",
            "progress_at_emit": 0.1,
            "goal_delta": "incomplete",
            "execution_mode": "auto",
        }
        out_buf = io.StringIO()
        with redirect_stdout(out_buf):
            cli.emit_cycle_feedback(state, self._base_outcome(), 1, False, quiet=True)
        self.assertIn("recovery-pending", out_buf.getvalue())
        self.assertIn("manifest-quiet-001", out_buf.getvalue())

    def test_quiet_json_mode_still_emits_recovery_pending_to_stderr(self):
        import io
        state = self._base_state()
        state["executor_state"]["recovery_manifest"] = {
            "manifest_id": "manifest-quiet-json-001",
            "emission_cause": "budget-exhausted",
            "progress_at_emit": 0.0,
            "goal_delta": "all incomplete",
            "execution_mode": "auto",
        }
        err_buf = io.StringIO()
        stdout_buf = io.StringIO()
        with redirect_stdout(stdout_buf), redirect_stderr(err_buf):
            cli.emit_cycle_feedback(state, self._base_outcome(), 1, True, quiet=True)
        self.assertIn("recovery-pending", err_buf.getvalue())
        self.assertIn("manifest-quiet-json-001", err_buf.getvalue())


class R27OptInTests(unittest.TestCase):
    """r27: derive skip-by-default, urace update --opt-in-patterns, stale manifest detection."""

    def setUp(self):
        self.config = isolated_test_config(self)
        self.state = cli.initial_state(self.config)
        cli.seed_confirmed_onboard(self.config, self.state)

    def test_derive_with_patterns_skips_menu_produces_manifest(self):
        config = copy.deepcopy(self.config)
        out_buf = io.StringIO()
        with patch.object(cli, "load_config", return_value=config), redirect_stdout(out_buf):
            result = cli.main(["derive", "--patterns", "AP0"])
        self.assertEqual(result, 0)
        text = out_buf.getvalue()
        self.assertNotIn("Usage: urace derive", text)
        self.assertTrue("DerivedConstructSet" in text or "DerivedSystemManifest" in text)

    def test_derive_without_patterns_shows_list_menu(self):
        config = copy.deepcopy(self.config)
        out_buf = io.StringIO()
        with patch.object(cli, "load_config", return_value=config), redirect_stdout(out_buf):
            result = cli.main(["derive"])
        self.assertEqual(result, 0)
        text = out_buf.getvalue()
        self.assertIn("Available URACE constructs", text)
        self.assertIn("Tip:", text)

    def test_derive_save_stores_ref_in_state(self):
        with tempfile.TemporaryDirectory() as directory:
            config = copy.deepcopy(self.config)
            config["state_path"] = str(Path(directory) / "state.json")
            state = copy.deepcopy(self.state)
            from urace._common import atomic_write_json
            atomic_write_json(Path(config["state_path"]), state)
            out_buf = io.StringIO()
            with patch.object(cli, "load_config", return_value=config), redirect_stdout(out_buf):
                result = cli.main(["derive", "saved test", "--patterns", "AP0", "--save"])
            self.assertEqual(result, 0)
            from urace._common import load_state_for_read as _lsr
            saved = _lsr(config)
            self.assertIsNotNone(saved)
            # --kind all (default) saves to construct_set_refs; --kind pattern saves to derived_manifest_refs
            refs = saved.get("construct_set_refs", []) or saved.get("derived_manifest_refs", [])
            self.assertEqual(len(refs), 1)
            adopted = refs[0].get("adopted_construct_ids") or refs[0].get("adopted_pattern_ids", [])
            self.assertIn("AP0", adopted)
            self.assertEqual(refs[0]["intent"], "saved test")

    def test_derive_save_updates_existing_ref_with_same_id(self):
        with tempfile.TemporaryDirectory() as directory:
            config = copy.deepcopy(self.config)
            config["state_path"] = str(Path(directory) / "state.json")
            state = copy.deepcopy(self.state)
            from urace._common import atomic_write_json
            atomic_write_json(Path(config["state_path"]), state)
            with patch.object(cli, "load_config", return_value=config), redirect_stdout(io.StringIO()):
                cli.main(["derive", "first", "--patterns", "AP0", "--save"])
            from urace._common import load_state_for_read as _lsr
            saved = _lsr(config)
            saved_count = len(saved.get("construct_set_refs", [])) + len(saved.get("derived_manifest_refs", []))
            self.assertEqual(saved_count, 1)

    def test_check_stale_derived_manifests_returns_stale_refs(self):
        state = copy.deepcopy(self.state)
        state["derived_manifest_refs"] = [
            {"manifest_id": "derived-abc1234567", "spec_version": "2026-10-12-r25", "generated_at": "2026-10-12T00:00:00+00:00", "adopted_pattern_ids": ["AP0"], "intent": "test"},
        ]
        stale = cli._check_stale_derived_manifests(state, "2026-10-12-r27")
        self.assertEqual(len(stale), 1)
        self.assertEqual(stale[0]["manifest_id"], "derived-abc1234567")
        ev = [e for e in state["evidence"] if e.get("kind") == "derived-manifest-stale"]
        self.assertEqual(len(ev), 1)
        self.assertEqual(ev[0]["stale_spec_version"], "2026-10-12-r25")
        self.assertEqual(ev[0]["candidate_spec_version"], "2026-10-12-r27")

    def test_check_stale_derived_manifests_non_stale_not_returned(self):
        state = copy.deepcopy(self.state)
        state["derived_manifest_refs"] = [
            {"manifest_id": "derived-abc1234567", "spec_version": "2026-10-12-r27", "generated_at": "2026-10-12T00:00:00+00:00", "adopted_pattern_ids": ["AP0"], "intent": "current"},
        ]
        stale = cli._check_stale_derived_manifests(state, "2026-10-12-r27")
        self.assertEqual(stale, [])
        ev = [e for e in state["evidence"] if e.get("kind") == "derived-manifest-stale"]
        self.assertEqual(len(ev), 0)

    def test_update_command_has_opt_in_patterns_flag(self):
        config = copy.deepcopy(self.config)
        mock_result = {
            "status": "NO_CHANGE", "candidate_sha256": "abc123", "added_lines": 0,
            "removed_lines": 0, "local_customizations": {"status": "CLEAN"},
            "source_revision": None, "report": "/tmp/report.json",
        }
        with patch.object(cli, "load_config", return_value=config), \
             patch.object(cli.updater, "explain", return_value=mock_result), \
             redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            result = cli.main(["update", "--opt-in-patterns", "AP8,AP14", "explain"])
        self.assertEqual(result, 0)

    def test_update_explain_with_opt_in_annotates_result(self):
        config = copy.deepcopy(self.config)
        mock_result = {
            "status": "REVIEW_REQUIRED", "candidate_sha256": "abc123", "added_lines": 5,
            "removed_lines": 2, "local_customizations": {"status": "CLEAN"},
            "source_revision": None, "report": "/tmp/report.json",
        }
        with patch.object(cli, "load_config", return_value=config), \
             patch.object(cli.updater, "explain", return_value=mock_result), \
             redirect_stdout(io.StringIO()):
            result = cli.main(["update", "--opt-in-patterns", "AP8,AP14", "explain"])
        self.assertEqual(result, 0)
        self.assertIn("opted_in_constructs", mock_result)
        self.assertIn("AP8", mock_result["opted_in_constructs"])
        self.assertIn("AP14", mock_result["opted_in_constructs"])

    def test_update_apply_with_opt_in_annotates_payload(self):
        config = copy.deepcopy(self.config)
        config["self_evolution_policy"] = {"mode": "CONTINUOUS"}
        captured_payloads = []
        mock_payload = {
            "title": "Update", "success_measure": "ok",
            "update_candidate": {"sha256": "def456", "source": None, "source_revision": None, "migration_chain": None, "explanation": "/tmp/x", "local_customizations": {"status": "CLEAN"}},
        }
        candidate=Path(config['state_path']).parent/'opt-in-candidate-fixture.md'
        candidate.write_text('isolated verification fixture')
        mock_payload['update_candidate']['sha256']=hashlib.sha256(candidate.read_bytes()).hexdigest()
        def mock_queue_input(cfg, kind, payload):
            captured_payloads.append(payload)
            return {"id": "input-abc1234567"}
        with patch.object(cli, "load_config", return_value=config), \
             patch.object(cli.updater, "migration_payload", return_value=mock_payload), \
             patch.object(cli.updater, "resolve_candidate", return_value=(candidate, {})), \
             patch.object(cli, "queue_input", side_effect=mock_queue_input), \
             patch.object(cli, "load_state_for_read", return_value=None), \
             redirect_stdout(io.StringIO()):
            result = cli.main(["update", "--opt-in-patterns", "AP8,AP14", "apply"])
        self.assertEqual(result, 0)
        self.assertEqual(len(captured_payloads), 1)
        self.assertIn("opted_in_patterns", captured_payloads[0])
        self.assertEqual(set(captured_payloads[0]["opted_in_patterns"]), {"AP8", "AP14"})  # payload key unchanged (executor-facing)

    def test_initial_state_has_derived_manifest_refs(self):
        config = isolated_test_config(self)
        state = cli.initial_state(config)
        self.assertIn("derived_manifest_refs", state)
        self.assertEqual(state["derived_manifest_refs"], [])


class R26DerivedSystemTests(unittest.TestCase):
    """r26: §62j Derivation Framework — DerivedSystemManifest, Pattern Catalog, urace derive command."""

    def test_pattern_catalog_has_all_twenty_five_aps(self):
        from urace import patterns as pc
        for ap in [f"AP{i}" for i in range(25)]:
            self.assertIn(ap, pc.PATTERN_CATALOG, f"{ap} missing from PATTERN_CATALOG")

    def test_ap20_circuit_breaker_definition(self):
        from urace import patterns as pc
        ap20 = pc.PATTERN_CATALOG["AP20"]
        self.assertEqual(ap20["name"], "Circuit Breaker")
        self.assertFalse(ap20["standalone"])
        self.assertEqual(ap20["tier"], pc.COMPOSITIONAL)
        self.assertIn("AP4", ap20["requires"])
        self.assertTrue(any("CLOSED" in p for p in ap20["provides"]))
        self.assertTrue(any("CircuitBreakerRecord" in p for p in ap20["provides"]))

    def test_ap21_compaction_definition(self):
        from urace import patterns as pc
        ap21 = pc.PATTERN_CATALOG["AP21"]
        self.assertEqual(ap21["name"], "Compaction")
        self.assertFalse(ap21["standalone"])
        self.assertEqual(ap21["tier"], pc.COMPOSITIONAL)
        self.assertEqual(ap21["requires"], ["AP3"])
        self.assertTrue(any("CompactionSummary" in p for p in ap21["provides"]))
        self.assertTrue(any("ARCHIVE" in p for p in ap21["provides"]))
        self.assertTrue(any("dry-run" in p for p in ap21["provides"]))

    def test_ap22_checkpoint_definition(self):
        from urace import patterns as pc
        ap22 = pc.PATTERN_CATALOG["AP22"]
        self.assertEqual(ap22["name"], "Checkpoint")
        self.assertFalse(ap22["standalone"])
        self.assertEqual(ap22["tier"], pc.COMPOSITIONAL)
        self.assertIn("AP0", ap22["requires"])
        self.assertIn("AP3", ap22["requires"])
        self.assertTrue(any("digest" in p for p in ap22["provides"]))
        self.assertTrue(any("crash" in p.lower() for p in ap22["provides"]))

    def test_ap23_justification_chain_definition(self):
        from urace import patterns as pc
        ap23 = pc.PATTERN_CATALOG["AP23"]
        self.assertEqual(ap23["name"], "Justification Chain")
        self.assertFalse(ap23["standalone"])
        self.assertEqual(ap23["tier"], pc.COMPOSITIONAL)
        self.assertEqual(ap23["requires"], ["AP6"])
        self.assertTrue(any("JustificationStep" in p for p in ap23["provides"]))
        self.assertTrue(any("traversal" in p.lower() for p in ap23["provides"]))

    def test_ap24_derivation_framework_definition(self):
        from urace import patterns as pc
        ap24 = pc.PATTERN_CATALOG["AP24"]
        self.assertEqual(ap24["name"], "Derivation Framework")
        self.assertFalse(ap24["standalone"])
        self.assertEqual(ap24["tier"], pc.INTEGRATED)
        self.assertIn("AP0", ap24["requires"])
        self.assertIn("AP2", ap24["requires"])
        self.assertTrue(any("PatternEntry" in p for p in ap24["provides"]))
        self.assertTrue(any("DerivedSystemManifest" in p for p in ap24["provides"]))
        self.assertTrue(any("stale" in p.lower() for p in ap24["provides"]))
        self.assertTrue(any("zero-conformance" in p.lower() for p in ap24["provides"]))

    def test_all_pattern_entries_have_required_keys(self):
        from urace import patterns as pc
        required = {"name", "standalone", "tier", "requires", "provides", "spec_section", "summary"}
        for pid, entry in pc.PATTERN_CATALOG.items():
            for key in required:
                self.assertIn(key, entry, f"{pid} missing key {key!r}")

    def test_standalone_true_patterns_have_empty_requires(self):
        from urace import patterns as pc
        for pid, entry in pc.PATTERN_CATALOG.items():
            if entry["standalone"]:
                self.assertEqual(entry["requires"], [], f"{pid} standalone=True but requires={entry['requires']}")

    def test_all_requires_references_are_valid_pattern_ids(self):
        from urace import patterns as pc
        valid_ids = set(pc.PATTERN_CATALOG)
        for pid, entry in pc.PATTERN_CATALOG.items():
            for dep in entry["requires"]:
                self.assertIn(dep, valid_ids, f"{pid}.requires references unknown pattern {dep!r}")

    def test_tier_values_are_canonical(self):
        from urace import patterns as pc
        valid_tiers = {pc.FOUNDATIONAL, pc.COMPOSITIONAL, pc.INTEGRATED}
        for pid, entry in pc.PATTERN_CATALOG.items():
            self.assertIn(entry["tier"], valid_tiers, f"{pid} has invalid tier {entry['tier']!r}")

    def test_resolve_dependencies_single_standalone_pattern(self):
        from urace import patterns as pc
        resolved, log = pc.resolve_dependencies(["AP0"])
        self.assertIn("AP0", resolved)
        self.assertEqual(log, [])

    def test_resolve_dependencies_adds_transitive_deps(self):
        from urace import patterns as pc
        resolved, log = pc.resolve_dependencies(["AP8"])
        self.assertIn("AP8", resolved)
        self.assertIn("AP3", resolved)
        self.assertIn("AP5", resolved)
        self.assertTrue(any("AP3" in entry or "AP5" in entry for entry in log))

    def test_resolve_dependencies_deduplicates(self):
        from urace import patterns as pc
        resolved, _ = pc.resolve_dependencies(["AP8", "AP9"])
        self.assertEqual(resolved.count("AP3"), 1)

    def test_resolve_dependencies_unknown_pattern_raises(self):
        from urace import patterns as pc
        with self.assertRaises(ValueError) as ctx:
            pc.resolve_dependencies(["APUNKNOWN"])
        self.assertIn("Unknown pattern", str(ctx.exception))

    def test_build_derived_manifest_structure(self):
        from urace import patterns as pc
        manifest = pc.build_derived_manifest(["AP0", "AP5"], intent="test system", spec_version="2026-10-12-r26")
        self.assertEqual(manifest["derived_from"], "URACE")
        self.assertEqual(manifest["spec_version"], "2026-10-12-r26")
        self.assertIn("manifest_id", manifest)
        self.assertIn("generated_at", manifest)
        for rec in manifest["adopted_patterns"]:
            self.assertIn(rec["pattern_id"], ["AP0", "AP5"])
            self.assertEqual(rec["adoption"], "EXPLICIT")

    def test_build_derived_manifest_marks_transitive_correctly(self):
        from urace import patterns as pc
        manifest = pc.build_derived_manifest(["AP8"], intent="fixpoint only", spec_version="r26")
        adoptions = {r["pattern_id"]: r["adoption"] for r in manifest["adopted_patterns"]}
        self.assertEqual(adoptions["AP8"], "EXPLICIT")
        self.assertEqual(adoptions.get("AP3"), "TRANSITIVE")
        self.assertEqual(adoptions.get("AP5"), "TRANSITIVE")

    def test_build_derived_manifest_with_exclusion(self):
        from urace import patterns as pc
        manifest = pc.build_derived_manifest(
            ["AP8"], intent="custom log", spec_version="r26",
            excluded_deps=[{"pattern_id": "AP3", "override_reason": "using custom log"}]
        )
        adopted_ids = {r["pattern_id"] for r in manifest["adopted_patterns"]}
        self.assertNotIn("AP3", adopted_ids)
        self.assertEqual(len(manifest["excluded_deps"]), 1)
        exc = manifest["excluded_deps"][0]
        self.assertEqual(exc["pattern_id"], "AP3")
        self.assertTrue(exc["acknowledged"])

    def test_validate_derived_system_manifest_valid(self):
        from urace import patterns as pc
        from urace import primitives as p
        manifest = pc.build_derived_manifest(["AP0"], intent="test", spec_version="r26")
        p.validate_derived_system_manifest(manifest)

    def test_validate_derived_system_manifest_wrong_derived_from(self):
        from urace import patterns as pc
        from urace import primitives as p
        manifest = pc.build_derived_manifest(["AP0"], intent="test", spec_version="r26")
        manifest["derived_from"] = "NOTRACE"
        with self.assertRaises(ValueError):
            p.validate_derived_system_manifest(manifest)

    def test_validate_pattern_exclusion_record_unacknowledged_raises(self):
        from urace import primitives as p
        exc = {"pattern_id": "AP3", "name": "Append-Only Log", "override_reason": "custom", "acknowledged": False}
        with self.assertRaises(ValueError) as ctx:
            p.validate_pattern_exclusion_record(exc)
        self.assertIn("acknowledged", str(ctx.exception))

    def test_validate_pattern_adoption_record_invalid_tier_raises(self):
        from urace import primitives as p
        rec = {"pattern_id": "AP0", "name": "Citizen", "adoption": "EXPLICIT", "tier": "INVALID", "provides": []}
        with self.assertRaises(ValueError):
            p.validate_pattern_adoption_record(rec)

    def test_validate_pattern_adoption_record_invalid_adoption_raises(self):
        from urace import primitives as p
        rec = {"pattern_id": "AP0", "name": "Citizen", "adoption": "FORCED", "tier": "FOUNDATIONAL", "provides": []}
        with self.assertRaises(ValueError):
            p.validate_pattern_adoption_record(rec)

    def test_derive_command_list_mode_no_patterns(self):
        config = isolated_test_config(self)
        out_buf = io.StringIO()
        with patch.object(cli, "load_config", return_value=config), redirect_stdout(out_buf):
            result = cli.main(["derive"])
        self.assertEqual(result, 0)
        text = out_buf.getvalue()
        self.assertIn("AP0", text)
        self.assertIn("AP19", text)
        self.assertIn("[pattern", text)
        self.assertIn("[mechanism", text)

    def test_derive_command_json_output(self):
        config = isolated_test_config(self)
        out_buf = io.StringIO()
        with patch.object(cli, "load_config", return_value=config), redirect_stdout(out_buf):
            # --kind pattern for DerivedSystemManifest (backward compat path)
            result = cli.main(["derive", "my system", "--patterns", "AP0,AP5", "--kind", "pattern", "--json"])
        self.assertEqual(result, 0)
        data = json.loads(out_buf.getvalue())
        self.assertEqual(data["derived_from"], "URACE")
        self.assertEqual(data["intent"], "my system")
        adopted_ids = {r["pattern_id"] for r in data["adopted_patterns"]}
        self.assertIn("AP0", adopted_ids)
        self.assertIn("AP5", adopted_ids)

    def test_derive_command_human_output(self):
        config = isolated_test_config(self)
        out_buf = io.StringIO()
        with patch.object(cli, "load_config", return_value=config), redirect_stdout(out_buf):
            # --kind pattern for transitive dependency resolution with [transitive]/[explicit] labels
            result = cli.main(["derive", "inbox only", "--patterns", "AP14", "--kind", "pattern"])
        self.assertEqual(result, 0)
        text = out_buf.getvalue()
        self.assertIn("AP14", text)
        self.assertIn("AP5", text)
        self.assertIn("[transitive]", text)
        self.assertIn("[explicit]", text)

    def test_derive_command_unknown_pattern_exits_1(self):
        config = isolated_test_config(self)
        with patch.object(cli, "load_config", return_value=config), \
             redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as ctx:
                cli.main(["derive", "--patterns", "APUNKNOWN", "--kind", "pattern"])
        self.assertEqual(ctx.exception.code, 2)

    def test_derive_command_exclude_requires_reason(self):
        config = isolated_test_config(self)
        with patch.object(cli, "load_config", return_value=config), \
             redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                cli.main(["derive", "--patterns", "AP8", "--exclude", "AP3", "--kind", "pattern"])

    def test_derive_command_exclude_with_reason(self):
        config = isolated_test_config(self)
        out_buf = io.StringIO()
        with patch.object(cli, "load_config", return_value=config), redirect_stdout(out_buf):
            result = cli.main(["derive", "--patterns", "AP8", "--exclude", "AP3",
                               "--exclude-reason", "own log impl", "--kind", "pattern", "--json"])
        self.assertEqual(result, 0)
        data = json.loads(out_buf.getvalue())
        adopted_ids = {r["pattern_id"] for r in data["adopted_patterns"]}
        self.assertNotIn("AP3", adopted_ids)
        self.assertEqual(len(data["excluded_deps"]), 1)
        self.assertTrue(data["excluded_deps"][0]["acknowledged"])

    def test_derive_command_out_writes_file(self):
        config = isolated_test_config(self)
        with tempfile.TemporaryDirectory() as directory:
            out_path = str(Path(directory) / "manifest.json")
            with patch.object(cli, "load_config", return_value=config), redirect_stdout(io.StringIO()):
                result = cli.main(["derive", "x", "--patterns", "AP0", "--out", out_path])
            self.assertEqual(result, 0)
            data = json.loads(Path(out_path).read_text(encoding="utf-8"))
            self.assertEqual(data["derived_from"], "URACE")

    def test_derived_system_manifest_in_validators_registry(self):
        from urace import primitives as p
        self.assertIn("DerivedSystemManifest", p._VALIDATORS)
        self.assertIn("PatternAdoptionRecord", p._VALIDATORS)
        self.assertIn("PatternExclusionRecord", p._VALIDATORS)

    def test_render_manifest_human_includes_all_sections(self):
        from urace import patterns as pc
        manifest = pc.build_derived_manifest(["AP8"], intent="fixpoint system", spec_version="r26")
        rendered = pc.render_manifest_human(manifest)
        self.assertIn("DerivedSystemManifest", rendered)
        self.assertIn("fixpoint system", rendered)
        self.assertIn("AP8", rendered)
        self.assertIn("[explicit]", rendered)
        self.assertIn("[transitive]", rendered)
        self.assertIn("Dependency resolution:", rendered)


class R25IPCTests(unittest.TestCase):
    """r25: IPC contracts — source_input traceability, inbox status, SIGTERM handler, rejection records."""

    def setUp(self):
        self.config = isolated_test_config(self)
        self.state = cli.initial_state(self.config)
        cli.seed_confirmed_onboard(self.config, self.state)

    def test_authoritative_input_consumed_evidence_has_source_input(self):
        with tempfile.TemporaryDirectory() as directory:
            config = copy.deepcopy(self.config)
            config["state_path"] = str(Path(directory) / "state.json")
            state = copy.deepcopy(self.state)
            state["objectives"] = [{"id": "goal-src", "title": "T", "status": "active", "reason": "r", "scope": "product", "success_measure": "s"}]
            cli.queue_input(config, "goal_control", {"action": "prioritize", "id": "goal-src", "priority": 90, "floor": 80, "ceiling": 100})
            paths = cli.consume_inputs(config, state)
            cli.cleanup_consumed_inputs(paths)
            consumed = [e for e in state["evidence"] if e.get("kind") == "authoritative-input-consumed"]
            self.assertTrue(consumed, "no authoritative-input-consumed evidence")
            for ev in consumed:
                self.assertIn("source_input", ev)
                self.assertEqual(ev["source_input"], ev["input"])

    def test_authoritative_input_rejected_malformed_has_rejected_at(self):
        with tempfile.TemporaryDirectory() as directory:
            config = copy.deepcopy(self.config)
            config["state_path"] = str(Path(directory) / "state.json")
            inbox_dir = cli.input_directory(config)
            inbox_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
            bad_file = inbox_dir / "bad-input.json"
            bad_file.write_text("not json {{{", encoding="utf-8")
            state = copy.deepcopy(self.state)
            cli.consume_inputs(config, state)
            rejected = [e for e in state["evidence"] if e.get("kind") == "authoritative-input-rejected"]
            self.assertTrue(rejected, "expected rejection evidence for malformed JSON")
            ev = rejected[0]
            self.assertIn("rejected_at", ev)
            self.assertIn("reason", ev)
            self.assertIsNone(ev.get("source_input"))

    def test_authoritative_input_rejected_unsupported_kind_has_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            config = copy.deepcopy(self.config)
            config["state_path"] = str(Path(directory) / "state.json")
            state = copy.deepcopy(self.state)
            cli.queue_input(config, "unsupported_kind_xyz", {"data": "value"})
            cli.consume_inputs(config, state)
            rejected = [e for e in state["evidence"] if e.get("kind") == "authoritative-input-rejected"]
            self.assertTrue(rejected)
            self.assertIn("unsupported", rejected[0]["reason"])

    def test_inbox_status_subcommand_consumed(self):
        with tempfile.TemporaryDirectory() as directory:
            config = copy.deepcopy(self.config)
            config["state_path"] = str(Path(directory) / "state.json")
            state = copy.deepcopy(self.state)
            state["objectives"] = [{"id": "goal-ipc", "title": "T", "status": "active", "reason": "r", "scope": "product", "success_measure": "s"}]
            item = cli.queue_input(config, "goal_control", {"action": "prioritize", "id": "goal-ipc", "priority": 70, "floor": 60, "ceiling": 80})
            input_id = item["id"]
            paths = cli.consume_inputs(config, state)
            cli.cleanup_consumed_inputs(paths)
            from urace._common import atomic_write_json
            atomic_write_json(Path(config["state_path"]), state)
            out_buf = io.StringIO()
            with patch.object(cli, "load_config", return_value=config), redirect_stdout(out_buf):
                result = cli.main(["inbox", "status", input_id, "--json"])
            self.assertEqual(result, 0)
            data = json.loads(out_buf.getvalue())
            self.assertEqual(data["input_id"], input_id)
            self.assertEqual(data["status"], "consumed")

    def test_inbox_status_subcommand_pending(self):
        with tempfile.TemporaryDirectory() as directory:
            config = copy.deepcopy(self.config)
            config["state_path"] = str(Path(directory) / "state.json")
            state = copy.deepcopy(self.state)
            from urace._common import atomic_write_json
            atomic_write_json(Path(config["state_path"]), state)
            item = cli.queue_input(config, "goal_control", {"action": "prioritize", "id": "goal-pending", "priority": 50, "floor": 40, "ceiling": 60})
            input_id = item["id"]
            out_buf = io.StringIO()
            with patch.object(cli, "load_config", return_value=config), redirect_stdout(out_buf):
                result = cli.main(["inbox", "status", input_id, "--json"])
            self.assertEqual(result, 0)
            data = json.loads(out_buf.getvalue())
            self.assertEqual(data["input_id"], input_id)
            self.assertEqual(data["status"], "pending")

    def test_inbox_status_subcommand_not_found(self):
        with tempfile.TemporaryDirectory() as directory:
            config = copy.deepcopy(self.config)
            config["state_path"] = str(Path(directory) / "state.json")
            state = copy.deepcopy(self.state)
            from urace._common import atomic_write_json
            atomic_write_json(Path(config["state_path"]), state)
            out_buf = io.StringIO()
            with patch.object(cli, "load_config", return_value=config), redirect_stdout(out_buf):
                result = cli.main(["inbox", "status", "input-nonexistent-000", "--json"])
            self.assertEqual(result, 0)
            data = json.loads(out_buf.getvalue())
            self.assertEqual(data["status"], "not-found")

    def test_inbox_list_still_works_after_status_subcommand_added(self):
        with tempfile.TemporaryDirectory() as directory:
            config = copy.deepcopy(self.config)
            config["state_path"] = str(Path(directory) / "state.json")
            state = copy.deepcopy(self.state)
            from urace._common import atomic_write_json
            atomic_write_json(Path(config["state_path"]), state)
            out_buf = io.StringIO()
            with patch.object(cli, "load_config", return_value=config), redirect_stdout(out_buf):
                result = cli.main(["inbox", "list"])
            self.assertEqual(result, 0)
            self.assertIn("Inbox empty", out_buf.getvalue())

    def test_sigterm_handler_is_registered_in_main(self):
        import signal as sig_mod
        registered = {}
        original = sig_mod.signal

        def capturing_signal(signum, handler):
            registered[signum] = handler
            return original(signum, handler)

        config = copy.deepcopy(self.config)
        with tempfile.TemporaryDirectory() as directory:
            config["state_path"] = str(Path(directory) / "state.json")
            state = copy.deepcopy(self.state)
            from urace._common import atomic_write_json
            atomic_write_json(Path(config["state_path"]), state)
            with patch.object(cli, "load_config", return_value=config), \
                 patch.object(cli.signal, "signal", side_effect=capturing_signal), \
                 redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                cli.main(["check"])
        self.assertIn(sig_mod.SIGTERM, registered)

    def test_exit_code_130_on_keyboard_interrupt(self):
        config = copy.deepcopy(self.config)
        from urace import bootstrap as _bootstrap
        with tempfile.TemporaryDirectory() as directory:
            config["state_path"] = str(Path(directory) / "state.json")
            with patch.object(cli, "load_config", return_value=config), \
                 patch.object(_bootstrap, "auto_complete", side_effect=KeyboardInterrupt), \
                 redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                result = cli.main(["init"])
        self.assertEqual(result, 130)
