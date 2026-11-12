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

from urace import analytics, cli, cli_helpers as _cli_helpers_m, compaction as compaction_module, evolution_guard, executor, external_metrics, launcher, portfolio, scope_priority, updater

TEST_RUNTIME_ROOT = Path(__file__).resolve().parents[1]
TEST_PRODUCT_ROOT = Path(__file__).resolve().parents[3]


def isolated_test_config(test_case):
    """Keep lifecycle writes away from the configured installation state."""
    config = copy.deepcopy(cli.load_config())
    directory = tempfile.TemporaryDirectory(prefix='urace-test-state-')
    test_case.addCleanup(directory.cleanup)
    config['state_path'] = str(Path(directory.name) / 'state.json')
    return config



class R31AdditionsTests(unittest.TestCase):
    """r31: QualityDelta, ReIngestionRecord, OperationDependency schemas; quality streak; staleness; /quality command."""

    def setUp(self):
        from urace import primitives
        self.primitives = primitives
        self.config = isolated_test_config(self)
        self.state = cli.initial_state(self.config)
        cli.seed_confirmed_onboard(self.config, self.state)

    # ── QualityDelta validator ──────────────────────────────────────────────

    def test_quality_delta_valid_with_predecessor(self):
        record = {
            "id": "qdl-abc1234567",
            "operation_id": "op-001",
            "scope": "product",
            "score_before": 0.6,
            "score_after": 0.8,
            "delta": 0.2,
            "classification": "IMPROVEMENT",
            "measured_at": "2026-01-01T00:00:00+00:00",
        }
        self.primitives.validate_quality_delta(record)  # must not raise

    def test_quality_delta_valid_no_predecessor(self):
        record = {
            "id": "qdl-first00000",
            "operation_id": "op-001",
            "scope": "runtime",
            "score_after": 0.5,
            "delta": 0.0,
            "classification": "NEUTRAL",
            "measured_at": "2026-01-01T00:00:00+00:00",
        }
        self.primitives.validate_quality_delta(record)

    def test_quality_delta_missing_required_field(self):
        record = {
            "id": "qdl-xyz",
            "operation_id": "op-001",
            "scope": "product",
            # missing score_after, delta, classification, measured_at
        }
        with self.assertRaises(ValueError):
            self.primitives.validate_quality_delta(record)

    def test_quality_delta_bad_id_prefix(self):
        record = {
            "id": "bad-abc1234567",
            "operation_id": "op-001",
            "scope": "product",
            "score_after": 0.7,
            "delta": 0.0,
            "classification": "NEUTRAL",
            "measured_at": "2026-01-01T00:00:00+00:00",
        }
        with self.assertRaises(ValueError):
            self.primitives.validate_quality_delta(record)

    def test_quality_delta_bad_classification(self):
        record = {
            "id": "qdl-abc1234567",
            "operation_id": "op-001",
            "scope": "product",
            "score_after": 0.7,
            "delta": 0.0,
            "classification": "UNKNOWN",
            "measured_at": "2026-01-01T00:00:00+00:00",
        }
        with self.assertRaises(ValueError):
            self.primitives.validate_quality_delta(record)

    def test_quality_delta_score_after_out_of_range(self):
        record = {
            "id": "qdl-abc1234567",
            "operation_id": "op-001",
            "scope": "product",
            "score_after": 1.5,
            "delta": 0.0,
            "classification": "NEUTRAL",
            "measured_at": "2026-01-01T00:00:00+00:00",
        }
        with self.assertRaises(ValueError):
            self.primitives.validate_quality_delta(record)

    def test_quality_delta_score_before_out_of_range(self):
        record = {
            "id": "qdl-abc1234567",
            "operation_id": "op-001",
            "scope": "product",
            "score_before": -0.1,
            "score_after": 0.5,
            "delta": 0.6,
            "classification": "IMPROVEMENT",
            "measured_at": "2026-01-01T00:00:00+00:00",
        }
        with self.assertRaises(ValueError):
            self.primitives.validate_quality_delta(record)

    # ── ReIngestionRecord validator ─────────────────────────────────────────

    def test_reingestion_record_valid_verified(self):
        record = {
            "id": "rei-abc1234567",
            "compaction_event_id": "cmp-xyz",
            "archive_path": "urace/archives/cmp-xyz.jsonl",
            "record_count": 42,
            "target_field": "decision_records",
            "digest_verified": True,
            "re_ingested_at": "2026-01-01T00:00:00+00:00",
            "status": "VERIFIED",
        }
        self.primitives.validate_reingestion_record(record)

    def test_reingestion_record_valid_integrity_gap(self):
        record = {
            "id": "rei-gap0000001",
            "compaction_event_id": "cmp-abc",
            "archive_path": "urace/archives/cmp-abc.jsonl",
            "record_count": 0,
            "target_field": "evidence",
            "digest_verified": False,
            "re_ingested_at": "2026-01-01T00:00:00+00:00",
            "status": "INTEGRITY_GAP",
        }
        self.primitives.validate_reingestion_record(record)

    def test_reingestion_record_missing_field(self):
        record = {"id": "rei-abc1234567", "compaction_event_id": "cmp-xyz"}
        with self.assertRaises(ValueError):
            self.primitives.validate_reingestion_record(record)

    def test_reingestion_record_bad_id_prefix(self):
        record = {
            "id": "bad-abc1234567",
            "compaction_event_id": "cmp-xyz",
            "archive_path": "urace/archives/cmp-xyz.jsonl",
            "record_count": 5,
            "target_field": "evidence",
            "digest_verified": True,
            "re_ingested_at": "2026-01-01T00:00:00+00:00",
            "status": "VERIFIED",
        }
        with self.assertRaises(ValueError):
            self.primitives.validate_reingestion_record(record)

    def test_reingestion_record_bad_status(self):
        record = {
            "id": "rei-abc1234567",
            "compaction_event_id": "cmp-xyz",
            "archive_path": "urace/archives/cmp-xyz.jsonl",
            "record_count": 5,
            "target_field": "evidence",
            "digest_verified": True,
            "re_ingested_at": "2026-01-01T00:00:00+00:00",
            "status": "UNKNOWN",
        }
        with self.assertRaises(ValueError):
            self.primitives.validate_reingestion_record(record)

    def test_reingestion_record_negative_count(self):
        record = {
            "id": "rei-abc1234567",
            "compaction_event_id": "cmp-xyz",
            "archive_path": "urace/archives/cmp-xyz.jsonl",
            "record_count": -1,
            "target_field": "evidence",
            "digest_verified": True,
            "re_ingested_at": "2026-01-01T00:00:00+00:00",
            "status": "VERIFIED",
        }
        with self.assertRaises(ValueError):
            self.primitives.validate_reingestion_record(record)

    # ── OperationDependency validator ───────────────────────────────────────

    def test_operation_dependency_valid_finish_to_start(self):
        record = {"from_id": "op-001", "to_id": "op-002", "kind": "FINISH_TO_START"}
        self.primitives.validate_operation_dependency(record)

    def test_operation_dependency_valid_start_to_start(self):
        record = {"from_id": "op-A", "to_id": "op-B", "kind": "START_TO_START"}
        self.primitives.validate_operation_dependency(record)

    def test_operation_dependency_self_cycle_rejected(self):
        record = {"from_id": "op-001", "to_id": "op-001", "kind": "FINISH_TO_START"}
        with self.assertRaises(ValueError):
            self.primitives.validate_operation_dependency(record)

    def test_operation_dependency_bad_kind(self):
        record = {"from_id": "op-001", "to_id": "op-002", "kind": "UNKNOWN_KIND"}
        with self.assertRaises(ValueError):
            self.primitives.validate_operation_dependency(record)

    def test_operation_dependency_missing_field(self):
        record = {"from_id": "op-001", "to_id": "op-002"}
        with self.assertRaises(ValueError):
            self.primitives.validate_operation_dependency(record)

    # ── BaseUnit enum ───────────────────────────────────────────────────────

    def test_base_unit_values_complete(self):
        from urace.primitives import _BASE_UNIT_VALUES
        expected = {"TOKENS", "REQUESTS", "MILLISECONDS", "BYTES", "COUNT", "SCORE", "PERCENT", "CREDITS"}
        self.assertEqual(_BASE_UNIT_VALUES, expected)

    # ── dispatch table coverage ─────────────────────────────────────────────

    def test_validators_dispatch_quality_delta(self):
        record = {
            "id": "qdl-dispatch001",
            "operation_id": "op-001",
            "scope": "product",
            "score_after": 0.9,
            "delta": 0.0,
            "classification": "NEUTRAL",
            "measured_at": "2026-01-01T00:00:00+00:00",
        }
        self.primitives.validate("QualityDelta", record)

    def test_validators_dispatch_reingestion_record(self):
        record = {
            "id": "rei-dispatch001",
            "compaction_event_id": "cmp-xyz",
            "archive_path": "urace/archives/cmp-xyz.jsonl",
            "record_count": 1,
            "target_field": "evidence",
            "digest_verified": True,
            "re_ingested_at": "2026-01-01T00:00:00+00:00",
            "status": "VERIFIED",
        }
        self.primitives.validate("ReIngestionRecord", record)

    def test_validators_dispatch_operation_dependency(self):
        record = {"from_id": "op-001", "to_id": "op-002", "kind": "FINISH_TO_START"}
        self.primitives.validate("OperationDependency", record)

    # ── initial_state has r31 fields ────────────────────────────────────────

    def test_initial_state_has_quality_deltas(self):
        self.assertIn("quality_deltas", self.state)
        self.assertEqual(self.state["quality_deltas"], [])

    def test_initial_state_has_reingestion_records(self):
        self.assertIn("reingestion_records", self.state)
        self.assertEqual(self.state["reingestion_records"], [])

    # ── _record_quality_delta helper ────────────────────────────────────────

    def test_record_quality_delta_improvement_increments_streak(self):
        state = copy.deepcopy(self.state)
        cli._record_quality_delta(state, "op-001", "product", 0.5, 0.8, "2026-01-01T00:00:00+00:00")
        self.assertEqual(state["quality_state"]["product"]["current_streak"], 1)
        self.assertEqual(len(state["quality_deltas"]), 1)
        self.assertEqual(state["quality_deltas"][0]["classification"], "IMPROVEMENT")

    def test_record_quality_delta_regression_resets_streak(self):
        state = copy.deepcopy(self.state)
        state.setdefault("quality_state", {})["product"] = {
            "scope": "product", "current_streak": 5, "best_streak": 5,
            "streak_started_at": "2026-01-01T00:00:00+00:00", "last_evaluated_at": "2026-01-01T00:00:00+00:00",
        }
        cli._record_quality_delta(state, "op-001", "product", 0.8, 0.5, "2026-01-01T00:00:00+00:00")
        self.assertEqual(state["quality_state"]["product"]["current_streak"], 0)
        self.assertEqual(state["quality_deltas"][0]["classification"], "REGRESSION")

    def test_record_quality_delta_neutral_does_not_change_streak(self):
        state = copy.deepcopy(self.state)
        state.setdefault("quality_state", {})["product"] = {
            "scope": "product", "current_streak": 3, "best_streak": 3,
            "streak_started_at": "2026-01-01T00:00:00+00:00", "last_evaluated_at": "2026-01-01T00:00:00+00:00",
        }
        cli._record_quality_delta(state, "op-001", "product", 0.7, 0.7, "2026-01-01T00:00:00+00:00")
        self.assertEqual(state["quality_state"]["product"]["current_streak"], 3)
        self.assertEqual(state["quality_deltas"][0]["classification"], "NEUTRAL")

    def test_record_quality_delta_no_predecessor_delta_zero(self):
        state = copy.deepcopy(self.state)
        rec = cli._record_quality_delta(state, "op-001", "product", None, 0.6, "2026-01-01T00:00:00+00:00")
        self.assertEqual(rec["delta"], 0.0)
        self.assertNotIn("score_before", rec)

    def test_record_quality_delta_id_prefix(self):
        state = copy.deepcopy(self.state)
        rec = cli._record_quality_delta(state, "op-001", "product", 0.5, 0.9, "2026-01-01T00:00:00+00:00")
        self.assertTrue(rec["id"].startswith("qdl-"))

    # ── _check_staleness helper ─────────────────────────────────────────────

    def test_check_staleness_no_warnings_for_fresh_state(self):
        state = copy.deepcopy(self.state)
        fresh_ts = datetime.now(timezone.utc).isoformat()
        state["decision_records"].append({"id": "dec-001", "at": fresh_ts})
        state["evidence"].append({"id": "ev-001", "at": fresh_ts})
        warnings = cli._check_staleness(state, self.config)
        self.assertEqual(warnings, [])

    def test_check_staleness_warns_stale_decisions(self):
        state = copy.deepcopy(self.state)
        old_ts = (datetime.now(timezone.utc) - timedelta(days=40)).isoformat()
        state["decision_records"].append({"id": "dec-001", "at": old_ts})
        config = copy.deepcopy(self.config)
        config["staleness_windows"] = {"decision_seconds": 86400}  # 1d threshold
        warnings = cli._check_staleness(state, config)
        self.assertTrue(any("staleness:decisions" in w for w in warnings))

    def test_check_staleness_empty_state_no_warnings(self):
        state = copy.deepcopy(self.state)
        state["decision_records"] = []
        state["evidence"] = []
        warnings = cli._check_staleness(state, self.config)
        self.assertEqual(warnings, [])

    # ── /quality command ────────────────────────────────────────────────────

    def test_quality_command_empty_state(self):
        with tempfile.TemporaryDirectory() as directory:
            config = copy.deepcopy(self.config)
            config["state_path"] = str(Path(directory) / "state.json")
            state = copy.deepcopy(self.state)
            from urace._common import atomic_write_json
            atomic_write_json(Path(config["state_path"]), state)
            out_buf = io.StringIO()
            with patch.object(cli, "load_config", return_value=config), redirect_stdout(out_buf):
                result = cli.main(["quality", "--json"])
            self.assertEqual(result, 0)
            data = json.loads(out_buf.getvalue())
            self.assertEqual(data["quality_streak"], 0)
            self.assertEqual(data["total_deltas"], 0)
            self.assertEqual(data["improvements"], 0)
            self.assertEqual(data["regressions"], 0)

    def test_quality_command_with_deltas(self):
        with tempfile.TemporaryDirectory() as directory:
            config = copy.deepcopy(self.config)
            config["state_path"] = str(Path(directory) / "state.json")
            state = copy.deepcopy(self.state)
            state["quality_deltas"] = [
                {"id": "qdl-a00000001", "operation_id": "op-1", "scope": "product",
                 "score_after": 0.8, "delta": 0.2, "classification": "IMPROVEMENT",
                 "measured_at": "2026-01-01T00:00:00+00:00"},
                {"id": "qdl-b00000002", "operation_id": "op-2", "scope": "runtime",
                 "score_after": 0.7, "delta": -0.1, "classification": "REGRESSION",
                 "measured_at": "2026-01-02T00:00:00+00:00"},
            ]
            from urace._common import atomic_write_json
            atomic_write_json(Path(config["state_path"]), state)
            out_buf = io.StringIO()
            with patch.object(cli, "load_config", return_value=config), redirect_stdout(out_buf):
                result = cli.main(["quality", "--json"])
            self.assertEqual(result, 0)
            data = json.loads(out_buf.getvalue())
            self.assertEqual(data["total_deltas"], 2)
            self.assertEqual(data["improvements"], 1)
            self.assertEqual(data["regressions"], 1)

    def test_quality_command_scope_filter(self):
        with tempfile.TemporaryDirectory() as directory:
            config = copy.deepcopy(self.config)
            config["state_path"] = str(Path(directory) / "state.json")
            state = copy.deepcopy(self.state)
            state["quality_deltas"] = [
                {"id": "qdl-a00000001", "operation_id": "op-1", "scope": "product",
                 "score_after": 0.8, "delta": 0.2, "classification": "IMPROVEMENT",
                 "measured_at": "2026-01-01T00:00:00+00:00"},
                {"id": "qdl-b00000002", "operation_id": "op-2", "scope": "runtime",
                 "score_after": 0.7, "delta": -0.1, "classification": "REGRESSION",
                 "measured_at": "2026-01-02T00:00:00+00:00"},
            ]
            from urace._common import atomic_write_json
            atomic_write_json(Path(config["state_path"]), state)
            out_buf = io.StringIO()
            with patch.object(cli, "load_config", return_value=config), redirect_stdout(out_buf):
                result = cli.main(["quality", "--scope", "product", "--json"])
            self.assertEqual(result, 0)
            data = json.loads(out_buf.getvalue())
            self.assertEqual(data["total_deltas"], 1)
            self.assertEqual(data["deltas"][0]["scope"], "product")

    def test_quality_command_human_output(self):
        with tempfile.TemporaryDirectory() as directory:
            config = copy.deepcopy(self.config)
            config["state_path"] = str(Path(directory) / "state.json")
            state = copy.deepcopy(self.state)
            from urace._common import atomic_write_json
            atomic_write_json(Path(config["state_path"]), state)
            out_buf = io.StringIO()
            with patch.object(cli, "load_config", return_value=config), redirect_stdout(out_buf):
                result = cli.main(["quality"])
            self.assertEqual(result, 0)
            self.assertIn("quality_streak", out_buf.getvalue())

    def test_quality_command_slash_routing(self):
        with tempfile.TemporaryDirectory() as directory:
            config = copy.deepcopy(self.config)
            config["state_path"] = str(Path(directory) / "state.json")
            state = copy.deepcopy(self.state)
            from urace._common import atomic_write_json
            atomic_write_json(Path(config["state_path"]), state)
            out_buf = io.StringIO()
            with patch.object(cli, "load_config", return_value=config), redirect_stdout(out_buf):
                result = cli.main(["/quality", "--json"])
            self.assertEqual(result, 0)

class R32AdditionsTests(unittest.TestCase):
    """r32: D1 quality_state decoupled from ExecutorState; D4 BaseUnit=SCORE; X1 AP4 contract;
    X2 checkpoint gate; X3 §77 step 4; X4 OperationDependency→§65; X5 MUST upgrade."""

    def setUp(self):
        self.config = isolated_test_config(self)
        self.state = cli.initial_state(self.config)
        cli.seed_confirmed_onboard(self.config, self.state)

    # ── D1: quality_state as independent Product-level field ─────────────────

    def test_initial_state_has_quality_state_field(self):
        self.assertIn("quality_state", self.state)
        self.assertIsInstance(self.state["quality_state"], dict)

    def test_record_quality_delta_writes_to_quality_state_not_executor_state(self):
        state = copy.deepcopy(self.state)
        cli._record_quality_delta(state, "op-001", "feature", 0.4, 0.7, "2026-01-01T00:00:00+00:00")
        self.assertIn("feature", state["quality_state"])
        self.assertNotIn("quality_streak", state["executor_state"])

    def test_quality_state_entry_has_required_fields(self):
        state = copy.deepcopy(self.state)
        cli._record_quality_delta(state, "op-001", "feature", 0.4, 0.7, "2026-01-01T00:00:00+00:00")
        entry = state["quality_state"]["feature"]
        for field in ("scope", "current_streak", "best_streak", "last_evaluated_at"):
            self.assertIn(field, entry)

    def test_quality_state_cross_scope_independence(self):
        state = copy.deepcopy(self.state)
        cli._record_quality_delta(state, "op-001", "scopeA", 0.5, 0.8, "2026-01-01T00:00:00+00:00")
        cli._record_quality_delta(state, "op-002", "scopeA", 0.8, 0.9, "2026-01-02T00:00:00+00:00")
        cli._record_quality_delta(state, "op-003", "scopeB", 0.8, 0.3, "2026-01-03T00:00:00+00:00")
        self.assertEqual(state["quality_state"]["scopeA"]["current_streak"], 2)
        self.assertEqual(state["quality_state"]["scopeB"]["current_streak"], 0)

    def test_quality_state_best_streak_monotone(self):
        state = copy.deepcopy(self.state)
        for score_after in (0.5, 0.6, 0.7):
            score_before = score_after - 0.1
            cli._record_quality_delta(state, "op-x", "s", score_before, score_after, "2026-01-01T00:00:00+00:00")
        entry = state["quality_state"]["s"]
        self.assertEqual(entry["current_streak"], 3)
        self.assertEqual(entry["best_streak"], 3)
        cli._record_quality_delta(state, "op-y", "s", 0.7, 0.3, "2026-01-02T00:00:00+00:00")
        self.assertEqual(state["quality_state"]["s"]["current_streak"], 0)
        self.assertEqual(state["quality_state"]["s"]["best_streak"], 3)

    def test_quality_state_streak_started_at_set_on_first_improvement(self):
        state = copy.deepcopy(self.state)
        ts = "2026-06-01T12:00:00+00:00"
        cli._record_quality_delta(state, "op-001", "s", 0.4, 0.6, ts)
        self.assertEqual(state["quality_state"]["s"]["streak_started_at"], ts)

    def test_quality_state_streak_started_at_cleared_on_regression(self):
        state = copy.deepcopy(self.state)
        cli._record_quality_delta(state, "op-001", "s", 0.4, 0.7, "2026-01-01T00:00:00+00:00")
        cli._record_quality_delta(state, "op-002", "s", 0.7, 0.3, "2026-01-02T00:00:00+00:00")
        self.assertIsNone(state["quality_state"]["s"]["streak_started_at"])

    # ── D4: QualityStateEntry validator ──────────────────────────────────────

    def test_validate_quality_state_entry_valid(self):
        from urace import primitives as p
        record = {
            "scope": "product",
            "current_streak": 3,
            "best_streak": 5,
            "streak_started_at": "2026-01-01T00:00:00+00:00",
            "last_evaluated_at": "2026-01-10T00:00:00+00:00",
        }
        p.validate("QualityStateEntry", record)

    def test_validate_quality_state_entry_missing_required(self):
        from urace import primitives as p
        with self.assertRaises(ValueError):
            p.validate("QualityStateEntry", {"scope": "s", "current_streak": 1})

    def test_validate_quality_state_entry_negative_streak(self):
        from urace import primitives as p
        with self.assertRaises(ValueError):
            p.validate("QualityStateEntry", {
                "scope": "s", "current_streak": -1, "best_streak": 0, "last_evaluated_at": "2026-01-01T00:00:00+00:00",
            })

    def test_validate_quality_state_entry_best_less_than_current(self):
        from urace import primitives as p
        with self.assertRaises(ValueError):
            p.validate("QualityStateEntry", {
                "scope": "s", "current_streak": 5, "best_streak": 3, "last_evaluated_at": "2026-01-01T00:00:00+00:00",
            })

    def test_validate_quality_state_entry_bad_streak_started_at_type(self):
        from urace import primitives as p
        with self.assertRaises(ValueError):
            p.validate("QualityStateEntry", {
                "scope": "s", "current_streak": 1, "best_streak": 1,
                "streak_started_at": 12345, "last_evaluated_at": "2026-01-01T00:00:00+00:00",
            })

    # ── X1: AP4 contract — quality command exposes best_streak ───────────────

    def test_quality_command_exposes_best_streak(self):
        with tempfile.TemporaryDirectory() as directory:
            config = copy.deepcopy(self.config)
            config["state_path"] = str(Path(directory) / "state.json")
            state = copy.deepcopy(self.state)
            state["quality_state"]["product"] = {
                "scope": "product", "current_streak": 2, "best_streak": 7,
                "streak_started_at": None, "last_evaluated_at": "2026-01-01T00:00:00+00:00",
            }
            from urace._common import atomic_write_json
            atomic_write_json(Path(config["state_path"]), state)
            out_buf = io.StringIO()
            with patch.object(cli, "load_config", return_value=config), redirect_stdout(out_buf):
                result = cli.main(["quality", "--json"])
            self.assertEqual(result, 0)
            data = json.loads(out_buf.getvalue())
            self.assertIn("best_streak", data)
            self.assertEqual(data["best_streak"], 7)

    # ── X4: OperationDependency self-cycle still rejected ────────────────────

    def test_operation_dependency_self_cycle_still_rejected(self):
        from urace import primitives as p
        with self.assertRaises(ValueError):
            p.validate("OperationDependency", {"from_id": "op-abc", "to_id": "op-abc", "kind": "FINISH_TO_START"})

    def test_operation_dependency_finish_to_start_valid(self):
        from urace import primitives as p
        p.validate("OperationDependency", {"from_id": "op-001", "to_id": "op-002", "kind": "FINISH_TO_START"})

    def test_operation_dependency_start_to_start_valid(self):
        from urace import primitives as p
        p.validate("OperationDependency", {"from_id": "op-001", "to_id": "op-002", "kind": "START_TO_START"})

    def test_operation_dependency_finish_to_finish_valid(self):
        from urace import primitives as p
        p.validate("OperationDependency", {"from_id": "op-001", "to_id": "op-002", "kind": "FINISH_TO_FINISH"})

    # ── X5: quality_deltas present in initial_state (MUST contract) ──────────

    def test_initial_state_quality_deltas_present(self):
        self.assertIn("quality_deltas", self.state)
        self.assertEqual(self.state["quality_deltas"], [])

    # ── Spec version r32 ─────────────────────────────────────────────────────

    def test_initial_state_has_reingestion_records(self):
        self.assertIn("reingestion_records", self.state)

    def test_quality_state_isolated_from_executor_state_schema(self):
        es = self.state["executor_state"]
        self.assertNotIn("quality_streak", es)
        self.assertNotIn("best_streak", es)
        self.assertNotIn("streak_started_at", es)

class R33AdditionsTests(unittest.TestCase):
    """r33: D2 per-scope staleness windows; D3 capability class budget priority;
    X2 checkpoint gate enforcement; X6 stale-decision→PendingValidation;
    ProducerConsumerContract validator; wake registration verification;
    §71 anti-churn; §68 persistent autonomous; ReingestionRecord coverage."""

    def setUp(self):
        self.config = isolated_test_config(self)
        self.state = cli.initial_state(self.config)
        cli.seed_confirmed_onboard(self.config, self.state)

    # ── D2: per-scope staleness windows ──────────────────────────────────────

    def test_staleness_uses_global_window_when_no_by_scope(self):
        """Global decision_seconds is used when by_scope is absent."""
        import datetime as _dt
        config = copy.deepcopy(self.config)
        config["staleness_windows"] = {"decision_seconds": 1, "by_scope": {}}
        state = copy.deepcopy(self.state)
        old_ts = (_dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(seconds=5)).isoformat()
        state["decision_records"] = [{
            "id": "dec-aabbccdd11",
            "kind": "OBJECTIVE_SELECTION",
            "provenance_status": "CURRENT",
            "scope": "documentation",
            "decided_at": old_ts,
            "subject": "s", "outcome": "o", "governing_intent_ref": "i",
            "state_digest": "a" * 64,
            "executor": {"executor_id": "e", "adapter": "a", "capability": "c",
                         "logical_reservation": "r", "attempted_executors": []},
        }]
        warnings = cli._check_staleness(state, config)
        self.assertTrue(any("dec-aabbccdd11" in w for w in warnings))

    def test_staleness_uses_per_scope_window_when_configured(self):
        """by_scope window overrides global window for matching scope."""
        import datetime as _dt
        config = copy.deepcopy(self.config)
        # global window = 1s (would fire), but runtime scope window = 9999s (won't fire)
        config["staleness_windows"] = {
            "decision_seconds": 1,
            "by_scope": {"runtime": 9999},
        }
        state = copy.deepcopy(self.state)
        old_ts = (_dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(seconds=5)).isoformat()
        state["decision_records"] = [{
            "id": "dec-aabbccdd12",
            "kind": "OBJECTIVE_SELECTION",
            "provenance_status": "CURRENT",
            "scope": "runtime",
            "decided_at": old_ts,
            "subject": "s", "outcome": "o", "governing_intent_ref": "i",
            "state_digest": "a" * 64,
            "executor": {"executor_id": "e", "adapter": "a", "capability": "c",
                         "logical_reservation": "r", "attempted_executors": []},
        }]
        warnings = cli._check_staleness(state, config)
        self.assertFalse(any("dec-aabbccdd12" in w for w in warnings))

    # ── X6: stale decision → PendingValidation ───────────────────────────────

    def test_stale_decision_produces_pending_validation(self):
        """A stale DecisionRecord produces a PendingValidation in state."""
        import datetime as _dt
        config = copy.deepcopy(self.config)
        config["staleness_windows"] = {"decision_seconds": 1}
        state = copy.deepcopy(self.state)
        old_ts = (_dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(seconds=5)).isoformat()
        state["decision_records"] = [{
            "id": "dec-aabbccdd13",
            "kind": "OBJECTIVE_SELECTION",
            "provenance_status": "CURRENT",
            "scope": "documentation",
            "decided_at": old_ts,
            "subject": "s", "outcome": "o", "governing_intent_ref": "i",
            "state_digest": "a" * 64,
            "executor": {"executor_id": "e", "adapter": "a", "capability": "c",
                         "logical_reservation": "r", "attempted_executors": []},
        }]
        state.setdefault("pending_validations", [])
        cli._check_staleness(state, config)
        pv_sources = [pv.get("source_operation_id") for pv in state["pending_validations"]]
        self.assertIn("dec-aabbccdd13", pv_sources)

    def test_stale_decision_pending_validation_not_duplicated(self):
        """Already-queued PendingValidation is not duplicated on second scan."""
        import datetime as _dt
        config = copy.deepcopy(self.config)
        config["staleness_windows"] = {"decision_seconds": 1}
        state = copy.deepcopy(self.state)
        old_ts = (_dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(seconds=5)).isoformat()
        state["decision_records"] = [{
            "id": "dec-aabbccdd14",
            "kind": "OBJECTIVE_SELECTION",
            "provenance_status": "CURRENT",
            "scope": "*",
            "decided_at": old_ts,
            "subject": "s", "outcome": "o", "governing_intent_ref": "i",
            "state_digest": "a" * 64,
            "executor": {"executor_id": "e", "adapter": "a", "capability": "c",
                         "logical_reservation": "r", "attempted_executors": []},
        }]
        state.setdefault("pending_validations", [])
        cli._check_staleness(state, config)
        cli._check_staleness(state, config)  # second scan
        pv_for_dec = [
            pv for pv in state["pending_validations"]
            if pv.get("source_operation_id") == "dec-aabbccdd14"
        ]
        self.assertEqual(len(pv_for_dec), 1)

    # ── X2: checkpoint gate enforcement ──────────────────────────────────────

    def test_regression_gate_passes_when_no_quality_history(self):
        """Gate is inactive when no QualityDelta records exist for scope."""
        state = copy.deepcopy(self.state)
        result = cli._regression_checkpoint_gate_passes(state, "documentation")
        self.assertTrue(result)

    def test_regression_gate_passes_when_latest_is_improvement(self):
        """Gate passes when most recent QualityDelta is IMPROVEMENT."""
        state = copy.deepcopy(self.state)
        state["quality_deltas"] = [
            {"id": "qdl-x1", "scope": "documentation", "classification": "IMPROVEMENT",
             "measured_at": "2026-01-01T00:00:00+00:00", "delta": 0.1, "score_after": 0.9},
        ]
        self.assertTrue(cli._regression_checkpoint_gate_passes(state, "documentation"))

    def test_regression_gate_blocks_when_latest_is_regression_no_decision(self):
        """Gate blocks when most recent QualityDelta is REGRESSION and no justifying DecisionRecord."""
        state = copy.deepcopy(self.state)
        state["quality_deltas"] = [
            {"id": "qdl-x2", "scope": "documentation", "classification": "REGRESSION",
             "measured_at": "2026-01-02T00:00:00+00:00", "delta": -0.1, "score_after": 0.6},
        ]
        self.assertFalse(cli._regression_checkpoint_gate_passes(state, "documentation"))

    def test_regression_gate_passes_when_regression_has_justifying_decision(self):
        """Gate passes when REGRESSION scope has a later CHECKPOINT_ACCEPTANCE DecisionRecord."""
        state = copy.deepcopy(self.state)
        state["quality_deltas"] = [
            {"id": "qdl-x3", "scope": "documentation", "classification": "REGRESSION",
             "measured_at": "2026-01-02T00:00:00+00:00", "delta": -0.1, "score_after": 0.6},
        ]
        state["decision_records"] = [{
            "id": "dec-aabbccdd20",
            "kind": "CHECKPOINT_ACCEPTANCE",
            "provenance_status": "CURRENT",
            "subject": "accept regression in documentation scope — justified by critical bug fix",
            "outcome": "ACCEPTED",
            "governing_intent_ref": "intent-primary",
            "decided_at": "2026-01-03T00:00:00+00:00",
            "state_digest": "b" * 64,
            "executor": {"executor_id": "e", "adapter": "a", "capability": "c",
                         "logical_reservation": "r", "attempted_executors": []},
        }]
        self.assertTrue(cli._regression_checkpoint_gate_passes(state, "documentation"))

    # ── ProducerConsumerContract validator ────────────────────────────────────

    def test_producer_consumer_contract_valid(self):
        from urace import primitives as p
        p.validate("ProducerConsumerContract", {
            "name": "TestProducer → TestConsumer",
            "producer": "TestProducer",
            "consumer": "TestConsumer",
            "artifact": "QualityDelta",
            "producer_must": ["write before emitting"],
            "consumer_may_assume": ["artifact is durable"],
            "violation_protocol": "ALERT",
            "idempotent": True,
        })

    def test_producer_consumer_contract_invalid_protocol(self):
        from urace import primitives as p
        with self.assertRaises(ValueError):
            p.validate("ProducerConsumerContract", {
                "name": "A → B",
                "producer": "A", "consumer": "B", "artifact": "X",
                "producer_must": [], "consumer_may_assume": [],
                "violation_protocol": "IGNORE",  # invalid
                "idempotent": False,
            })

    def test_producer_consumer_contract_missing_field(self):
        from urace import primitives as p
        with self.assertRaises(ValueError):
            p.validate("ProducerConsumerContract", {
                "name": "A → B",
                "producer": "A",
                # missing consumer, artifact, producer_must, consumer_may_assume,
                # violation_protocol, idempotent
            })

    # ── Wake Registration Verification ───────────────────────────────────────

    def test_verify_wake_registrations_empty_registry_no_gaps(self):
        """Empty wake_registry produces no gaps."""
        state = copy.deepcopy(self.state)
        gaps = cli._verify_wake_registrations({}, state)
        self.assertEqual(gaps, [])

    def test_verify_wake_registrations_entry_missing_kind_surfaces_gap(self):
        """Entry without required 'kind' field surfaces a wake-integrity-gap."""
        state = copy.deepcopy(self.state)
        state["wake_registry"] = [{"id": "wkr-aa0000001", "scheduled_at": "2027-01-01T00:00:00+00:00"}]
        gaps = cli._verify_wake_registrations({}, state)
        self.assertEqual(len(gaps), 1)
        self.assertIn("wkr-aa0000001", gaps[0])

    def test_verify_wake_registrations_entry_lacking_verified_at_surfaces_gap(self):
        """Entry with required fields but no verified_at surfaces a wake-integrity-gap."""
        state = copy.deepcopy(self.state)
        state["wake_registry"] = [{
            "id": "wkr-aa0000002",
            "kind": "scheduled",
            "scheduled_at": "2027-01-01T00:00:00+00:00",
            "condition": "discovery-interval",
        }]
        gaps = cli._verify_wake_registrations({}, state)
        self.assertEqual(len(gaps), 1)

    def test_verify_wake_registrations_verified_entry_no_gap(self):
        """Entry with verified_at present produces no gap."""
        state = copy.deepcopy(self.state)
        state["wake_registry"] = [{
            "id": "wkr-aa0000003",
            "kind": "scheduled",
            "scheduled_at": "2027-01-01T00:00:00+00:00",
            "condition": "discovery-interval",
            "verified_at": "2026-10-14T00:00:00+00:00",
        }]
        gaps = cli._verify_wake_registrations({}, state)
        self.assertEqual(gaps, [])

    # ── §71 Anti-churn: no manufactured work on empty state ──────────────────

    def test_antichurn_no_objectives_yields_dormant_cycle(self):
        """A lifecycle with no objectives, no evidence, no triggers stays DORMANT."""
        state = copy.deepcopy(self.state)
        self.assertEqual(state["lifecycle_state"], "DORMANT")
        self.assertEqual(state["objectives"], [])
        # cycle with no executor and no inputs should not manufacture objectives
        with patch.object(cli, "executor_execution_allowed", return_value=False):
            cli.cycle(self.config, state, allow_execution=False)
        self.assertEqual(state["objectives"], [])

    def test_antichurn_staleness_scan_no_false_positives_without_config(self):
        """Staleness scan absent staleness_windows config does not surface false positives."""
        config = copy.deepcopy(self.config)
        config.pop("staleness_windows", None)
        state = copy.deepcopy(self.state)
        # No decisions — staleness scan should return no warnings
        state["decision_records"] = []
        warnings = cli._check_staleness(state, config)
        self.assertEqual(warnings, [])

    # ── §68 Persistent autonomous: state preserved across stop ───────────────

    def test_persistent_autonomous_state_survives_stop(self):
        """Lifecycle durable state (objectives, decision_records) persists across process stop."""
        import tempfile
        from pathlib import Path
        from urace._common import atomic_write_json
        with tempfile.TemporaryDirectory() as directory:
            config = copy.deepcopy(self.config)
            config["state_path"] = str(Path(directory) / "state.json")
            state = cli.initial_state(config)
            state["objectives"] = [{"id": "obj-aabbcc0011", "title": "survive stop", "status": "active"}]
            atomic_write_json(Path(config["state_path"]), state)
            # Simulate restart: load state fresh
            loaded = json.loads(Path(config["state_path"]).read_text(encoding="utf-8"))
            self.assertEqual(len(loaded["objectives"]), 1)
            self.assertEqual(loaded["objectives"][0]["title"], "survive stop")

    # ── ReingestionRecord mechanism coverage ─────────────────────────────────

    def test_reingestion_records_present_in_initial_state(self):
        """initial_state always has reingestion_records list (already tested in R32 — belt & suspenders)."""
        self.assertIn("reingestion_records", self.state)
        self.assertIsInstance(self.state["reingestion_records"], list)

    def test_check_staleness_skips_non_current_decisions(self):
        """Decisions with provenance_status != CURRENT are excluded from staleness scan."""
        import datetime as _dt
        config = copy.deepcopy(self.config)
        config["staleness_windows"] = {"decision_seconds": 1}
        state = copy.deepcopy(self.state)
        old_ts = (_dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(seconds=5)).isoformat()
        state["decision_records"] = [{
            "id": "dec-aabbccdd30",
            "kind": "OBJECTIVE_SELECTION",
            "provenance_status": "SUPERSEDED",  # not CURRENT
            "scope": "documentation",
            "decided_at": old_ts,
            "subject": "s", "outcome": "o", "governing_intent_ref": "i",
            "state_digest": "a" * 64,
            "executor": {"executor_id": "e", "adapter": "a", "capability": "c",
                         "logical_reservation": "r", "attempted_executors": []},
        }]
        state.setdefault("pending_validations", [])
        cli._check_staleness(state, config)
        pv_sources = [pv.get("source_operation_id") for pv in state["pending_validations"]]
        self.assertNotIn("dec-aabbccdd30", pv_sources)

class R34AdditionsTests(unittest.TestCase):
    """r34: §59b Product Capable Evolution; CapabilityStatement/Envelope/Milestone/SweetSpot/ValueDensity
    schemas; SweetSpot Evaluation Mechanism; Capability Envelope Gate; AP25 Bounded Evolution Band;
    ProductMaturityLevel/CapabilityStatus/CapabilityContributionKind canonicals."""

    def setUp(self):
        self.config = isolated_test_config(self)
        self.state = cli.initial_state(self.config)
        cli.seed_confirmed_onboard(self.config, self.state)

    # ── New state fields ──────────────────────────────────────────────────────

    def test_initial_state_has_sweet_spot_fields(self):
        self.assertIn("sweet_spot_assessments", self.state)
        self.assertIn("capability_states", self.state)
        self.assertIn("value_density_history", self.state)
        self.assertIsInstance(self.state["sweet_spot_assessments"], list)
        self.assertIsInstance(self.state["capability_states"], list)
        self.assertIsInstance(self.state["value_density_history"], list)

    # ── CapabilityStatement validator ─────────────────────────────────────────

    def test_capability_statement_valid(self):
        from urace import primitives as p
        p.validate("CapabilityStatement", {
            "id": "cap-aabbccdd01",
            "name": "User authentication",
            "description": "Product can authenticate users",
            "scope": "runtime",
            "tier": "FOUNDATIONAL",
            "value_weight": 0.4,
        })

    def test_capability_statement_invalid_tier(self):
        from urace import primitives as p
        with self.assertRaises(ValueError):
            p.validate("CapabilityStatement", {
                "id": "cap-aabbccdd02",
                "name": "x", "description": "x",
                "scope": "runtime", "tier": "INVALID", "value_weight": 0.5,
            })

    def test_capability_statement_wrong_id_prefix(self):
        from urace import primitives as p
        with self.assertRaises(ValueError):
            p.validate("CapabilityStatement", {
                "id": "obj-aabbccdd03",  # wrong prefix
                "name": "x", "description": "x",
                "scope": "runtime", "tier": "FOUNDATIONAL", "value_weight": 0.5,
            })

    # ── CapabilityEnvelopeEntry validator ─────────────────────────────────────

    def test_capability_envelope_entry_capable_valid(self):
        from urace import primitives as p
        p.validate("CapabilityEnvelopeEntry", {
            "capability_id": "cap-aabbccdd04",
            "status": "CAPABLE",
            "completeness_fraction": 1.0,
            "last_assessed_at": "2026-01-01T00:00:00+00:00",
        })

    def test_capability_envelope_entry_fraction_mismatch_raises(self):
        from urace import primitives as p
        with self.assertRaises(ValueError):
            p.validate("CapabilityEnvelopeEntry", {
                "capability_id": "cap-aabbccdd05",
                "status": "CAPABLE",
                "completeness_fraction": 0.5,  # should be 1.0 for CAPABLE
                "last_assessed_at": "2026-01-01T00:00:00+00:00",
            })

    def test_capability_envelope_entry_partial_valid(self):
        from urace import primitives as p
        p.validate("CapabilityEnvelopeEntry", {
            "capability_id": "cap-aabbccdd06",
            "status": "PARTIAL",
            "completeness_fraction": 0.6,
            "last_assessed_at": "2026-01-01T00:00:00+00:00",
        })

    # ── ProductMilestone validator ────────────────────────────────────────────

    def test_product_milestone_valid(self):
        from urace import primitives as p
        p.validate("ProductMilestone", {
            "id": "mst-aabbccdd07",
            "name": "v1 capable",
            "description": "All core capabilities present",
            "capability_gates": ["cap-aabbccdd01"],
            "status": "ACTIVE",
        })

    def test_product_milestone_invalid_status(self):
        from urace import primitives as p
        with self.assertRaises(ValueError):
            p.validate("ProductMilestone", {
                "id": "mst-aabbccdd08",
                "name": "x", "description": "x",
                "capability_gates": [],
                "status": "IN_PROGRESS",  # invalid
            })

    # ── SweetSpotAssessment validator ─────────────────────────────────────────

    def test_sweet_spot_assessment_valid(self):
        from urace import primitives as p
        p.validate("SweetSpotAssessment", {
            "id": "ssa-aabbccdd09",
            "assessed_at": "2026-01-01T00:00:00+00:00",
            "maturity_level": "CAPABLE",
            "capability_completeness": 1.0,
            "value_density": 0.0001,
            "product_surface_measure": 5000,
        })

    def test_sweet_spot_assessment_invalid_maturity(self):
        from urace import primitives as p
        with self.assertRaises(ValueError):
            p.validate("SweetSpotAssessment", {
                "id": "ssa-aabbccdd10",
                "assessed_at": "2026-01-01T00:00:00+00:00",
                "maturity_level": "EXCELLENT",  # invalid
                "capability_completeness": 1.0,
                "value_density": 0.0,
                "product_surface_measure": 0,
            })

    # ── ValueDensityRecord validator ──────────────────────────────────────────

    def test_value_density_record_valid(self):
        from urace import primitives as p
        p.validate("ValueDensityRecord", {
            "id": "vdr-aabbccdd11",
            "recorded_at": "2026-01-01T00:00:00+00:00",
            "value_density": 0.00005,
            "surface_measure": 8000,
            "delta": 0.000001,
            "trend": "IMPROVING",
        })

    def test_value_density_record_invalid_trend(self):
        from urace import primitives as p
        with self.assertRaises(ValueError):
            p.validate("ValueDensityRecord", {
                "id": "vdr-aabbccdd12",
                "recorded_at": "2026-01-01T00:00:00+00:00",
                "value_density": 0.0,
                "surface_measure": 0,
                "trend": "FLAT",  # invalid
            })

    # ── SweetSpot Evaluation Mechanism ────────────────────────────────────────

    def test_evaluate_sweet_spot_no_envelope_does_nothing(self):
        """Without capability_envelope in config, sweet spot evaluation is a no-op."""
        config = copy.deepcopy(self.config)
        config.pop("capability_envelope", None)
        state = copy.deepcopy(self.state)
        cli._evaluate_sweet_spot(state, config)
        self.assertEqual(state["sweet_spot_assessments"], [])
        self.assertEqual(state["value_density_history"], [])

    def test_evaluate_sweet_spot_no_capabilities_does_nothing(self):
        """Empty capabilities list: evaluation is a no-op."""
        config = copy.deepcopy(self.config)
        config["capability_envelope"] = {"capabilities": []}
        state = copy.deepcopy(self.state)
        cli._evaluate_sweet_spot(state, config)
        self.assertEqual(state["sweet_spot_assessments"], [])

    def test_evaluate_sweet_spot_forming_when_no_caps_capable(self):
        """All capabilities ABSENT -> maturity FORMING."""
        config = copy.deepcopy(self.config)
        config["capability_envelope"] = {
            "capabilities": [
                {"id": "cap-aabbccdd20", "name": "auth", "description": "d",
                 "scope": "runtime", "tier": "FOUNDATIONAL", "value_weight": 1.0},
            ],
            "completeness_target": 1.0,
        }
        state = copy.deepcopy(self.state)
        # capability_states empty -> no caps are CAPABLE
        cli._evaluate_sweet_spot(state, config)
        self.assertEqual(len(state["sweet_spot_assessments"]), 1)
        ssa = state["sweet_spot_assessments"][0]
        self.assertEqual(ssa["maturity_level"], "FORMING")
        self.assertIn("cap-aabbccdd20", (ssa.get("capability_gaps") or []))

    def test_evaluate_sweet_spot_capable_when_all_caps_capable(self):
        """All capabilities CAPABLE -> maturity is CAPABLE or OPTIMIZED (both are sweet spot)."""
        config = copy.deepcopy(self.config)
        config["capability_envelope"] = {
            "capabilities": [
                {"id": "cap-aabbccdd21", "name": "auth", "description": "d",
                 "scope": "runtime", "tier": "FOUNDATIONAL", "value_weight": 1.0},
            ],
            "completeness_target": 1.0,
        }
        state = copy.deepcopy(self.state)
        state["capability_states"] = [{
            "capability_id": "cap-aabbccdd21",
            "status": "CAPABLE",
            "completeness_fraction": 1.0,
            "last_assessed_at": "2026-01-01T00:00:00+00:00",
        }]
        cli._evaluate_sweet_spot(state, config)
        ssa = state["sweet_spot_assessments"][-1]
        self.assertIn(ssa["maturity_level"], {"CAPABLE", "OPTIMIZED"})
        self.assertAlmostEqual(ssa["capability_completeness"], 1.0)

    def test_evaluate_sweet_spot_over_engineered_when_ceiling_exceeded(self):
        """Surface exceeds complexity_ceiling -> maturity OVER_ENGINEERED."""
        import tempfile
        with tempfile.TemporaryDirectory() as _d:
            _root = Path(_d)
            (_root / "surface.txt").write_text("line\n" * 10)
            config = copy.deepcopy(self.config)
            config["product_files"] = ["surface.txt"]
            config["capability_envelope"] = {
                "capabilities": [
                    {"id": "cap-aabbccdd22", "name": "c", "description": "d",
                     "scope": "runtime", "tier": "FOUNDATIONAL", "value_weight": 1.0},
                ],
                "completeness_target": 1.0,
                "complexity_ceiling": 1,  # impossibly small ceiling; surface=10 > 1
            }
            state = copy.deepcopy(self.state)
            state["capability_states"] = [{
                "capability_id": "cap-aabbccdd22",
                "status": "CAPABLE",
                "completeness_fraction": 1.0,
                "last_assessed_at": "2026-01-01T00:00:00+00:00",
            }]
            with patch.object(cli, "ROOT", _root), patch.object(_cli_helpers_m, "ROOT", _root):
                cli._evaluate_sweet_spot(state, config)
        ssa = state["sweet_spot_assessments"][-1]
        self.assertEqual(ssa["maturity_level"], "OVER_ENGINEERED")

    def test_evaluate_sweet_spot_writes_value_density_record(self):
        """Each evaluation writes a ValueDensityRecord."""
        config = copy.deepcopy(self.config)
        config["capability_envelope"] = {
            "capabilities": [
                {"id": "cap-aabbccdd23", "name": "c", "description": "d",
                 "scope": "runtime", "tier": "FOUNDATIONAL", "value_weight": 0.5},
            ],
        }
        state = copy.deepcopy(self.state)
        cli._evaluate_sweet_spot(state, config)
        self.assertEqual(len(state["value_density_history"]), 1)
        vdr = state["value_density_history"][0]
        self.assertIn("value_density", vdr)
        self.assertIn("surface_measure", vdr)

    # ── Capability Envelope Gate ──────────────────────────────────────────────

    def test_capability_gate_passes_without_envelope(self):
        """No capability_envelope -> gate always passes."""
        config = copy.deepcopy(self.config)
        config.pop("capability_envelope", None)
        state = copy.deepcopy(self.state)
        self.assertTrue(cli._capability_envelope_gate_passes(state, config, 99999, {}))

    def test_capability_gate_passes_when_not_capable(self):
        """Gate only fires at CAPABLE/OPTIMIZED; FORMING passes."""
        config = copy.deepcopy(self.config)
        config["capability_envelope"] = {"capabilities": [
            {"id": "cap-aabbccdd24", "name": "c", "description": "d",
             "scope": "runtime", "tier": "FOUNDATIONAL", "value_weight": 1.0},
        ], "complexity_ceiling": 10}
        state = copy.deepcopy(self.state)
        state["sweet_spot_assessments"] = [{
            "id": "ssa-aabbccdd99", "assessed_at": "2026-01-01T00:00:00+00:00",
            "maturity_level": "FORMING",
            "capability_completeness": 0.0, "value_density": 0.0, "product_surface_measure": 5,
        }]
        self.assertTrue(cli._capability_envelope_gate_passes(state, config, 99999, {}))

    def test_capability_gate_blocks_at_capable_over_ceiling(self):
        """Gate blocks when CAPABLE and surface exceeds ceiling without DecisionRecord."""
        config = copy.deepcopy(self.config)
        config["capability_envelope"] = {"capabilities": [
            {"id": "cap-aabbccdd25", "name": "c", "description": "d",
             "scope": "runtime", "tier": "FOUNDATIONAL", "value_weight": 1.0},
        ], "complexity_ceiling": 10}
        state = copy.deepcopy(self.state)
        state["sweet_spot_assessments"] = [{
            "id": "ssa-aabbccdd98", "assessed_at": "2026-01-01T00:00:00+00:00",
            "maturity_level": "CAPABLE",
            "capability_completeness": 1.0, "value_density": 0.001, "product_surface_measure": 5,
        }]
        self.assertFalse(cli._capability_envelope_gate_passes(state, config, 15, {
            "created_at": "2026-01-01T00:00:00+00:00", "scope": "runtime",
        }))

class R35AdditionsTests(unittest.TestCase):
    """r35: Milestone versioning chain; ProductVersion; TestRecord/TestRunRecord schemas;
    Test Coverage Gate; urace milestone command; pattern→capability derivation."""

    def setUp(self):
        self.config = isolated_test_config(self)
        self.state = cli.initial_state(self.config)
        cli.seed_confirmed_onboard(self.config, self.state)

    # ── New state fields ──────────────────────────────────────────────────────

    def test_initial_state_has_r35_fields(self):
        self.assertIn("product_versions", self.state)
        self.assertIn("test_run_records", self.state)
        self.assertIsInstance(self.state["product_versions"], list)
        self.assertIsInstance(self.state["test_run_records"], list)

    # ── ProductVersion validator ──────────────────────────────────────────────

    def test_product_version_valid(self):
        from urace import primitives as p
        p.validate("ProductVersion", {
            "id": "pver-aabbccdd01",
            "version": "v1.0",
            "milestone_id": "mst-aabbccdd01",
            "achieved_at": "2026-01-01T00:00:00+00:00",
            "maturity_level": "CAPABLE",
            "capability_completeness": 1.0,
            "value_density": 0.0001,
            "product_surface_measure": 5000,
        })

    def test_product_version_wrong_prefix_raises(self):
        from urace import primitives as p
        with self.assertRaises(ValueError):
            p.validate("ProductVersion", {
                "id": "mst-aabbccdd01",  # wrong prefix
                "version": "v1.0",
                "milestone_id": "mst-aabbccdd01",
                "achieved_at": "2026-01-01T00:00:00+00:00",
                "maturity_level": "CAPABLE",
                "capability_completeness": 1.0,
                "value_density": 0.0,
                "product_surface_measure": 0,
            })

    # ── TestRecord validator ──────────────────────────────────────────────────

    def test_test_record_valid(self):
        from urace import primitives as p
        p.validate("TestRecord", {
            "id": "tst-aabbccdd02",
            "name": "auth returns 200 for valid credentials",
            "description": "verifies user authentication works end-to-end",
            "scope": "runtime",
            "kind": "ACCEPTANCE",
            "status": "ACTIVE",
        })

    def test_test_record_invalid_kind(self):
        from urace import primitives as p
        with self.assertRaises(ValueError):
            p.validate("TestRecord", {
                "id": "tst-aabbccdd03",
                "name": "x", "description": "x",
                "scope": "runtime", "kind": "SMOKE", "status": "ACTIVE",
            })

    def test_test_record_wrong_prefix(self):
        from urace import primitives as p
        with self.assertRaises(ValueError):
            p.validate("TestRecord", {
                "id": "cap-aabbccdd04",  # wrong prefix
                "name": "x", "description": "x",
                "scope": "runtime", "kind": "UNIT", "status": "ACTIVE",
            })

    # ── TestRunRecord validator ───────────────────────────────────────────────

    def test_test_run_record_pass_valid(self):
        from urace import primitives as p
        p.validate("TestRunRecord", {
            "id": "trr-aabbccdd05",
            "run_at": "2026-01-01T00:00:00+00:00",
            "scope": "runtime",
            "kind": "ACCEPTANCE",
            "total": 10, "passed": 10, "failed": 0, "skipped": 0, "errored": 0,
            "verdict": "PASS",
        })

    def test_test_run_record_count_mismatch_raises(self):
        from urace import primitives as p
        with self.assertRaises(ValueError):
            p.validate("TestRunRecord", {
                "id": "trr-aabbccdd06",
                "run_at": "2026-01-01T00:00:00+00:00",
                "scope": "runtime",
                "kind": "UNIT",
                "total": 5, "passed": 3, "failed": 1, "skipped": 0, "errored": 0,
                "verdict": "FAIL",
                # total=5 but passed+failed+skipped+errored=4 — mismatch
            })

    def test_test_run_record_pass_verdict_with_failures_raises(self):
        from urace import primitives as p
        with self.assertRaises(ValueError):
            p.validate("TestRunRecord", {
                "id": "trr-aabbccdd07",
                "run_at": "2026-01-01T00:00:00+00:00",
                "scope": "runtime",
                "kind": "UNIT",
                "total": 5, "passed": 4, "failed": 1, "skipped": 0, "errored": 0,
                "verdict": "PASS",  # invalid: failed > 0
            })

    # ── Milestone chain progression ───────────────────────────────────────────

    def test_milestone_achievement_creates_product_version(self):
        """Milestone achievement writes a ProductVersion to state.product_versions."""
        config = copy.deepcopy(self.config)
        config["capability_envelope"] = {
            "capabilities": [
                {"id": "cap-aabbccdd10", "name": "auth", "description": "d",
                 "scope": "runtime", "tier": "FOUNDATIONAL", "value_weight": 1.0},
            ],
            "completeness_target": 1.0,
            "milestones": [{
                "id": "mst-aabbccdd10",
                "name": "v1.0 capable",
                "description": "all core capabilities present",
                "capability_gates": ["cap-aabbccdd10"],
                "status": "ACTIVE",
                "version": "v1.0",
            }],
        }
        state = copy.deepcopy(self.state)
        state["capability_states"] = [{
            "capability_id": "cap-aabbccdd10",
            "status": "CAPABLE",
            "completeness_fraction": 1.0,
            "last_assessed_at": "2026-01-01T00:00:00+00:00",
        }]
        cli._evaluate_sweet_spot(state, config)
        self.assertEqual(len(state["product_versions"]), 1)
        pver = state["product_versions"][0]
        self.assertEqual(pver["version"], "v1.0")
        self.assertEqual(pver["milestone_id"], "mst-aabbccdd10")

    def test_milestone_chain_activates_next(self):
        """Achieving milestone M1 activates M2 when next_milestone_id is set."""
        config = copy.deepcopy(self.config)
        config["capability_envelope"] = {
            "capabilities": [
                {"id": "cap-aabbccdd11", "name": "auth", "description": "d",
                 "scope": "runtime", "tier": "FOUNDATIONAL", "value_weight": 1.0},
            ],
            "completeness_target": 1.0,
            "milestones": [
                {
                    "id": "mst-aabbccdd11",
                    "name": "v1.0 capable",
                    "description": "core done",
                    "capability_gates": ["cap-aabbccdd11"],
                    "status": "ACTIVE",
                    "version": "v1.0",
                    "next_milestone_id": "mst-aabbccdd12",
                },
                {
                    "id": "mst-aabbccdd12",
                    "name": "v1.1 optimized",
                    "description": "quality improved",
                    "capability_gates": ["cap-aabbccdd11"],
                    "status": "PENDING",
                    "version": "v1.1",
                },
            ],
        }
        state = copy.deepcopy(self.state)
        state["capability_states"] = [{
            "capability_id": "cap-aabbccdd11",
            "status": "CAPABLE",
            "completeness_fraction": 1.0,
            "last_assessed_at": "2026-01-01T00:00:00+00:00",
        }]
        cli._evaluate_sweet_spot(state, config)
        milestones = config["capability_envelope"]["milestones"]
        m2 = next(m for m in milestones if m["id"] == "mst-aabbccdd12")
        self.assertEqual(m2["status"], "ACTIVE")

    def test_milestone_no_version_no_product_version_without_achievement(self):
        """If no milestone achieved, no ProductVersion is created."""
        config = copy.deepcopy(self.config)
        config["capability_envelope"] = {
            "capabilities": [
                {"id": "cap-aabbccdd13", "name": "auth", "description": "d",
                 "scope": "runtime", "tier": "FOUNDATIONAL", "value_weight": 1.0},
            ],
            "milestones": [{
                "id": "mst-aabbccdd13",
                "name": "v1.0",
                "description": "d",
                "capability_gates": ["cap-aabbccdd13"],
                "status": "ACTIVE",
                "version": "v1.0",
            }],
        }
        state = copy.deepcopy(self.state)
        # capability_states empty → gate not satisfied → no achievement
        cli._evaluate_sweet_spot(state, config)
        self.assertEqual(state["product_versions"], [])

    # ── urace milestone command ───────────────────────────────────────────────

    def test_milestone_command_runs_without_error(self):
        """milestone command exits 0."""
        import tempfile
        from pathlib import Path
        from urace._common import atomic_write_json
        with tempfile.TemporaryDirectory() as directory:
            config = copy.deepcopy(self.config)
            config["state_path"] = str(Path(directory) / "state.json")
            state = cli.initial_state(config)
            atomic_write_json(Path(config["state_path"]), state)
            out_buf = io.StringIO()
            with patch.object(cli, "load_config", return_value=config), redirect_stdout(out_buf):
                result = cli.main(["milestone"])
            self.assertEqual(result, 0)

    def test_milestone_command_json_output(self):
        """milestone --json emits machine-readable payload."""
        import tempfile
        from pathlib import Path
        from urace._common import atomic_write_json
        with tempfile.TemporaryDirectory() as directory:
            config = copy.deepcopy(self.config)
            config["state_path"] = str(Path(directory) / "state.json")
            state = cli.initial_state(config)
            atomic_write_json(Path(config["state_path"]), state)
            out_buf = io.StringIO()
            with patch.object(cli, "load_config", return_value=config), redirect_stdout(out_buf):
                result = cli.main(["milestone", "--json"])
            self.assertEqual(result, 0)
            data = json.loads(out_buf.getvalue())
            self.assertIn("maturity_level", data)
            self.assertIn("version_history", data)

class R36AdditionsTests(unittest.TestCase):
    """r36: urace derive TRUE FULL POTENTIAL — DerivedManifestRef, DerivationRecord, refresh, apply-capabilities, derive-milestone"""

    def test_r36_initial_state_has_derivation_records(self):
        _cfg = isolated_test_config(self)
        s = cli.initial_state(_cfg)
        self.assertIn("derivation_records", s)
        self.assertEqual(s["derivation_records"], [])

    def test_r36_initial_state_has_derivation_refs(self):
        _cfg = isolated_test_config(self)
        s = cli.initial_state(_cfg)
        self.assertIn("derivation_refs", s)
        self.assertEqual(s["derivation_refs"], [])

    def test_r36_validate_derived_manifest_ref_valid(self):
        from urace import primitives as prim
        ref = {
            "id": "dmr-abc12345",
            "manifest_id": "dsm-xyz",
            "spec_version": "2026-10-14-r36",
            "generated_at": "2026-10-14T00:00:00Z",
            "adopted_pattern_ids": ["AP0", "AP4"],
            "intent": "test system",
        }
        prim.validate("DerivedManifestRef", ref)  # should not raise

    def test_r36_validate_derived_manifest_ref_bad_prefix(self):
        from urace import primitives as prim
        ref = {
            "id": "bad-abc12345",
            "manifest_id": "dsm-xyz",
            "spec_version": "2026-10-14-r36",
            "generated_at": "2026-10-14T00:00:00Z",
            "adopted_pattern_ids": [],
            "intent": "test",
        }
        with self.assertRaises(ValueError):
            prim.validate("DerivedManifestRef", ref)

    def test_r36_validate_derivation_record_valid(self):
        from urace import primitives as prim
        rec = {
            "id": "drv-abc12345",
            "kind": "MANIFEST",
            "manifest_id": "dsm-xyz",
            "pattern_ids": ["AP0"],
            "spec_version": "2026-10-14-r36",
            "derived_at": "2026-10-14T00:00:00Z",
        }
        prim.validate("DerivationRecord", rec)

    def test_r36_validate_derivation_record_all_kinds(self):
        from urace import primitives as prim
        for kind in ("MANIFEST", "REFRESH", "CAPABILITY_APPLY", "MILESTONE_DRAFT"):
            rec = {
                "id": "drv-abc12345",
                "kind": kind,
                "pattern_ids": [],
                "spec_version": "2026-10-14-r36",
                "derived_at": "2026-10-14T00:00:00Z",
            }
            prim.validate("DerivationRecord", rec)

    def test_r36_validate_derivation_record_bad_kind(self):
        from urace import primitives as prim
        rec = {
            "id": "drv-abc12345",
            "kind": "UNKNOWN",
            "pattern_ids": [],
            "spec_version": "r36",
            "derived_at": "2026-10-14T00:00:00Z",
        }
        with self.assertRaises(ValueError):
            prim.validate("DerivationRecord", rec)

    def test_r36_validate_derivation_record_capabilities_applied_valid(self):
        from urace import primitives as prim
        rec = {
            "id": "drv-abc12345",
            "kind": "CAPABILITY_APPLY",
            "pattern_ids": ["AP4"],
            "spec_version": "r36",
            "derived_at": "2026-10-14T00:00:00Z",
            "capabilities_applied": 3,
        }
        prim.validate("DerivationRecord", rec)

    def test_r36_validate_derivation_record_capabilities_applied_negative(self):
        from urace import primitives as prim
        rec = {
            "id": "drv-abc12345",
            "kind": "CAPABILITY_APPLY",
            "pattern_ids": [],
            "spec_version": "r36",
            "derived_at": "2026-10-14T00:00:00Z",
            "capabilities_applied": -1,
        }
        with self.assertRaises(ValueError):
            prim.validate("DerivationRecord", rec)

    def test_r36_derive_milestone_no_caps_returns_none(self):
        from urace.cli import _derive_milestone_from_state
        state = {}
        config = {}
        result = _derive_milestone_from_state(state, config)
        self.assertIsNone(result)

    def test_r36_derive_milestone_with_absent_caps(self):
        from urace.cli import _derive_milestone_from_state
        config = {
            "capability_envelope": {
                "capabilities": [
                    {"id": "cap-aaa00000", "name": "Auth", "scope": "*", "tier": "FOUNDATIONAL", "value_weight": 0.5},
                    {"id": "cap-bbb00000", "name": "Logging", "scope": "*", "tier": "FOUNDATIONAL", "value_weight": 0.3},
                ]
            }
        }
        state = {
            "capability_states": [
                {"id": "cap-aaa00000", "status": "CAPABLE"},
            ]
        }
        result = _derive_milestone_from_state(state, config)
        self.assertIsNotNone(result)
        self.assertIn("cap-bbb00000", result["capability_gates"])
        self.assertNotIn("cap-aaa00000", result["capability_gates"])
        self.assertTrue(result.get("_draft"))

    def test_r36_derive_milestone_all_capable_returns_none(self):
        from urace.cli import _derive_milestone_from_state
        config = {
            "capability_envelope": {
                "capabilities": [
                    {"id": "cap-aaa00000", "name": "Auth", "scope": "*", "tier": "FOUNDATIONAL", "value_weight": 0.5},
                ]
            }
        }
        state = {
            "capability_states": [
                {"id": "cap-aaa00000", "status": "CAPABLE"},
            ]
        }
        result = _derive_milestone_from_state(state, config)
        self.assertIsNone(result)

    def test_r36_refresh_no_saved_manifests(self):
        from urace.cli import _refresh_derived_manifests
        state = {}
        config = {}
        results = _refresh_derived_manifests(state, config, None, False)
        self.assertEqual(len(results), 1)
        self.assertIn("no_saved", results[0]["status"])

    def test_r36_refresh_manifest_id_filter_not_found(self):
        from urace.cli import _refresh_derived_manifests
        state = {
            "derivation_refs": [
                {
                    "id": "dmr-abc12345",
                    "manifest_id": "dsm-old",
                    "spec_version": "2026-10-01-r30",
                    "generated_at": "2026-10-01T00:00:00Z",
                    "adopted_pattern_ids": ["AP0"],
                    "intent": "test",
                }
            ]
        }
        config = {}
        results = _refresh_derived_manifests(state, config, manifest_id_filter="dsm-nonexistent", show_delta=False)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["status"], "not_found")

