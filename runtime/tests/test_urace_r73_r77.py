import copy
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timedelta, timezone
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


class R73FleetTests(unittest.TestCase):
    """r73 §62q Fleet Orchestration — unit tests."""

    def setUp(self):
        self.config = isolated_test_config(self)
        self.config["executor"]["enabled"] = False
        self.config.setdefault("product", "TestProduct")
        self.config.setdefault("intent", {})
        self.config["intent"]["purpose"] = "Test autonomous evolution"
        self.state = cli.initial_state(self.config)
        cli.seed_confirmed_onboard(self.config, self.state)

    # ── initial_state bootstrap ───────────────────────────────────────────────

    def test_initial_state_has_fleet_records(self):
        """initial_state() returns state with 'fleet_records' == []."""
        fresh = cli.initial_state(self.config)
        self.assertIn("fleet_records", fresh)
        self.assertEqual(fresh["fleet_records"], [])

    # ── fleet status empty members ────────────────────────────────────────────

    def test_fleet_status_empty_members(self):
        """config with fleet.members=[] → fleet status returns empty list."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            config = copy.deepcopy(self.config)
            config["state_path"] = f"{tmpdir}/state.json"
            config["fleet"] = {"members": []}
            state = cli.initial_state(config)
            cli.save_state(config, state)
            out = io.StringIO()
            with patch.object(cli, "load_config", return_value=config), redirect_stdout(out):
                rc = cli.main(["fleet", "status", "--json"])
            self.assertEqual(rc, 0)
            result = json.loads(out.getvalue())
            self.assertEqual(result, [])

    # ── fleet status reads member state ──────────────────────────────────────

    def test_fleet_status_reads_member_state(self):
        """fleet status reads member state file and returns lifecycle_state."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            config = copy.deepcopy(self.config)
            config["state_path"] = f"{tmpdir}/state.json"
            alpha_state_path = f"{tmpdir}/state_alpha.json"
            config["fleet"] = {"members": ["alpha"]}
            config["product_registry"] = [{
                "id": "prod-alpha1",
                "name": "alpha",
                "state_path": alpha_state_path,
                "product_files": [],
                "registered_at": "2026-01-01T00:00:00+00:00",
                "status": "ACTIVE",
            }]
            # Write minimal state JSON for alpha
            alpha_config = dict(config)
            alpha_config["active_product"] = "alpha"
            alpha_state = cli.initial_state(alpha_config)
            alpha_state["lifecycle_state"] = "DORMANT"
            cli.save_state(alpha_config, alpha_state)
            # Also write main state
            state = cli.initial_state(config)
            cli.save_state(config, state)
            out = io.StringIO()
            with patch.object(cli, "load_config", return_value=config), redirect_stdout(out):
                rc = cli.main(["fleet", "status", "--json"])
            self.assertEqual(rc, 0)
            result = json.loads(out.getvalue())
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["product"], "alpha")
            self.assertEqual(result[0]["lifecycle_state"], "DORMANT")

    # ── fleet broadcast empty evidence ────────────────────────────────────────

    def test_fleet_broadcast_empty_evidence(self):
        """fleet broadcast with no evidence → broadcast_count=0."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            config = copy.deepcopy(self.config)
            config["state_path"] = f"{tmpdir}/state.json"
            state_a_path = f"{tmpdir}/state_a.json"
            state_b_path = f"{tmpdir}/state_b.json"
            config["fleet"] = {"members": ["a", "b"], "broadcast_min_confidence": 0.75}
            config["product_registry"] = [
                {"id": "prod-a1", "name": "a", "state_path": state_a_path, "product_files": [], "registered_at": "2026-01-01T00:00:00+00:00", "status": "ACTIVE"},
                {"id": "prod-b1", "name": "b", "state_path": state_b_path, "product_files": [], "registered_at": "2026-01-01T00:00:00+00:00", "status": "ACTIVE"},
            ]
            # Write empty states for a and b
            for name, _path in [("a", state_a_path), ("b", state_b_path)]:
                mc = dict(config)
                mc["active_product"] = name
                ms = cli.initial_state(mc)
                cli.save_state(mc, ms)
            state = cli.initial_state(config)
            cli.save_state(config, state)
            out = io.StringIO()
            with patch.object(cli, "load_config", return_value=config), redirect_stdout(out):
                rc = cli.main(["fleet", "broadcast", "--json"])
            self.assertEqual(rc, 0)
            result = json.loads(out.getvalue())
            self.assertEqual(result["broadcast_count"], 0)

    # ── fleet broadcast injects qualifying evidence ───────────────────────────

    def test_fleet_broadcast_injects_qualifying_evidence(self):
        """fleet broadcast writes inbox file for qualifying evidence."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            config = copy.deepcopy(self.config)
            config["state_path"] = f"{tmpdir}/state.json"
            state_a_path = f"{tmpdir}/state_a.json"
            state_b_path = f"{tmpdir}/state_b.json"
            config["fleet"] = {"members": ["a", "b"], "broadcast_min_confidence": 0.75}
            config["product_registry"] = [
                {"id": "prod-a1", "name": "a", "state_path": state_a_path, "product_files": [], "registered_at": "2026-01-01T00:00:00+00:00", "status": "ACTIVE"},
                {"id": "prod-b1", "name": "b", "state_path": state_b_path, "product_files": [], "registered_at": "2026-01-01T00:00:00+00:00", "status": "ACTIVE"},
            ]
            # Write state for a with qualifying evidence
            mc_a = dict(config)
            mc_a["active_product"] = "a"
            ms_a = cli.initial_state(mc_a)
            ms_a["evidence"] = [{"id": "ev-test1", "kind": "some-finding", "summary": "test finding", "confidence_score": 0.9, "at": "2026-01-01T00:00:00+00:00"}]
            cli.save_state(mc_a, ms_a)
            # Write empty state for b
            mc_b = dict(config)
            mc_b["active_product"] = "b"
            ms_b = cli.initial_state(mc_b)
            cli.save_state(mc_b, ms_b)
            # Write main state
            state = cli.initial_state(config)
            cli.save_state(config, state)
            out = io.StringIO()
            with patch.object(cli, "load_config", return_value=config), redirect_stdout(out):
                rc = cli.main(["fleet", "broadcast", "--json"])
            self.assertEqual(rc, 0)
            result = json.loads(out.getvalue())
            self.assertGreater(result["broadcast_count"], 0)
            # Verify inbox file was written for member b
            from urace._common import state_path as sp
            inbox_b = sp(mc_b).parent / "inbox"
            inbox_files = list(inbox_b.glob("*.json"))
            self.assertGreater(len(inbox_files), 0)
            inbox_data = json.loads(inbox_files[0].read_text())
            self.assertEqual(inbox_data["source"], "fleet-broadcast")
            self.assertEqual(inbox_data["from_product"], "a")

    # ── fleet run dry-run returns members ─────────────────────────────────────

    def test_fleet_run_dry_run_returns_members(self):
        """fleet run --dry-run returns would_start list without launching processes."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            config = copy.deepcopy(self.config)
            config["state_path"] = f"{tmpdir}/state.json"
            config["fleet"] = {"members": ["x", "y"]}
            config["product_registry"] = [
                {"id": "prod-x1", "name": "x", "state_path": f"{tmpdir}/state_x.json", "product_files": [], "registered_at": "2026-01-01T00:00:00+00:00", "status": "ACTIVE"},
                {"id": "prod-y1", "name": "y", "state_path": f"{tmpdir}/state_y.json", "product_files": [], "registered_at": "2026-01-01T00:00:00+00:00", "status": "ACTIVE"},
            ]
            state = cli.initial_state(config)
            cli.save_state(config, state)
            out = io.StringIO()
            with patch.object(cli, "load_config", return_value=config), redirect_stdout(out):
                rc = cli.main(["fleet", "run", "--dry-run", "--json"])
            self.assertEqual(rc, 0)
            result = json.loads(out.getvalue())
            self.assertIn("would_start", result)
            self.assertEqual(set(result["would_start"]), {"x", "y"})

    # ── fleet run rejects duplicate state_path ────────────────────────────────

    def test_fleet_run_rejects_duplicate_state_path(self):
        """fleet run with two members sharing same state_path → exit code 1."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            shared_path = f"{tmpdir}/shared_state.json"
            config = copy.deepcopy(self.config)
            config["state_path"] = f"{tmpdir}/state.json"
            config["fleet"] = {"members": ["m1", "m2"]}
            config["product_registry"] = [
                {"id": "prod-m1", "name": "m1", "state_path": shared_path, "product_files": [], "registered_at": "2026-01-01T00:00:00+00:00", "status": "ACTIVE"},
                {"id": "prod-m2", "name": "m2", "state_path": shared_path, "product_files": [], "registered_at": "2026-01-01T00:00:00+00:00", "status": "ACTIVE"},
            ]
            state = cli.initial_state(config)
            cli.save_state(config, state)
            out = io.StringIO()
            with patch.object(cli, "load_config", return_value=config), redirect_stdout(out):
                rc = cli.main(["fleet", "run", "--dry-run"])
            self.assertEqual(rc, 1)

    # ── fleet run rejects unregistered member ─────────────────────────────────

    def test_fleet_run_rejects_unregistered_member(self):
        """fleet run with member not in product_registry → exit code 1."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            config = copy.deepcopy(self.config)
            config["state_path"] = f"{tmpdir}/state.json"
            config["fleet"] = {"members": ["ghost"]}
            config["product_registry"] = []
            state = cli.initial_state(config)
            cli.save_state(config, state)
            out = io.StringIO()
            with patch.object(cli, "load_config", return_value=config), redirect_stdout(out):
                rc = cli.main(["fleet", "run", "--dry-run"])
            self.assertEqual(rc, 1)


class R73CommandAlignmentTests(unittest.TestCase):
    """r73 CLI gap closure — new commands and flags from §62k audit."""

    def setUp(self):
        self.config = isolated_test_config(self)
        self.config["executor"]["enabled"] = False
        self.config.setdefault("product", "TestProduct")
        self.config.setdefault("intent", {})
        self.config["intent"]["purpose"] = "Test autonomous evolution"
        self.state = cli.initial_state(self.config)
        cli.seed_confirmed_onboard(self.config, self.state)

    # ── evidence ─────────────────────────────────────────────────────────────

    def test_evidence_list_returns_evidence(self):
        """evidence list returns all evidence records."""
        self.state["evidence"] = [
            {"id": "ev-001", "at": "2026-01-01T00:00:00+00:00", "kind": "blocker-resolved", "summary": "first"},
            {"id": "ev-002", "at": "2026-01-02T00:00:00+00:00", "kind": "cycle-complete", "summary": "second"},
            {"id": "ev-003", "at": "2026-01-03T00:00:00+00:00", "kind": "blocker-resolved", "summary": "third"},
        ]
        out = io.StringIO()
        with patch.object(cli, "load_config", return_value=self.config), \
             patch.object(cli, "load_state_for_read", return_value=self.state), \
             redirect_stdout(out):
            rc = cli.main(["evidence", "list", "--json"])
        self.assertEqual(rc, 0)
        result = json.loads(out.getvalue())
        self.assertEqual(len(result), 3)

    def test_evidence_list_filters_by_kind(self):
        """evidence list --kind X returns only records of that kind."""
        self.state["evidence"] = [
            {"id": "ev-001", "at": "2026-01-01T00:00:00+00:00", "kind": "blocker-resolved"},
            {"id": "ev-002", "at": "2026-01-02T00:00:00+00:00", "kind": "cycle-complete"},
            {"id": "ev-003", "at": "2026-01-03T00:00:00+00:00", "kind": "blocker-resolved"},
        ]
        out = io.StringIO()
        with patch.object(cli, "load_config", return_value=self.config), \
             patch.object(cli, "load_state_for_read", return_value=self.state), \
             redirect_stdout(out):
            rc = cli.main(["evidence", "list", "--kind", "blocker-resolved", "--json"])
        self.assertEqual(rc, 0)
        result = json.loads(out.getvalue())
        self.assertEqual(len(result), 2)
        self.assertTrue(all(r["kind"] == "blocker-resolved" for r in result))

    def test_evidence_list_respects_limit(self):
        """evidence list --limit 3 returns at most 3 records."""
        self.state["evidence"] = [
            {"id": f"ev-{i:03d}", "at": f"2026-01-{i:02d}T00:00:00+00:00", "kind": "cycle-complete"}
            for i in range(1, 11)
        ]
        out = io.StringIO()
        with patch.object(cli, "load_config", return_value=self.config), \
             patch.object(cli, "load_state_for_read", return_value=self.state), \
             redirect_stdout(out):
            rc = cli.main(["evidence", "list", "--limit", "3", "--json"])
        self.assertEqual(rc, 0)
        result = json.loads(out.getvalue())
        self.assertEqual(len(result), 3)

    # ── blocker ───────────────────────────────────────────────────────────────

    def test_blocker_list_returns_active_blockers(self):
        """blocker list with 2 blockers (1 resolved, 1 active) returns 1."""
        self.state["blockers"] = [
            {"id": "blk-001", "at": "2026-01-01T00:00:00+00:00", "last_at": "2026-01-01T00:00:00+00:00",
             "scope": "test", "reason": "active", "count": 1, "classification": "PERSISTENT", "resolved_at": None},
            {"id": "blk-002", "at": "2026-01-01T00:00:00+00:00", "last_at": "2026-01-01T00:00:00+00:00",
             "scope": "test", "reason": "resolved", "count": 1, "classification": "PERSISTENT",
             "resolved_at": "2026-01-02T00:00:00+00:00"},
        ]
        out = io.StringIO()
        with patch.object(cli, "load_config", return_value=self.config), \
             patch.object(cli, "load_state_for_read", return_value=self.state), \
             redirect_stdout(out):
            rc = cli.main(["blocker", "list", "--json"])
        self.assertEqual(rc, 0)
        result = json.loads(out.getvalue())
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "blk-001")

    def test_blocker_list_with_resolved_flag(self):
        """blocker list --resolved with 1 resolved blocker returns 1."""
        self.state["blockers"] = [
            {"id": "blk-001", "at": "2026-01-01T00:00:00+00:00", "last_at": "2026-01-01T00:00:00+00:00",
             "scope": "test", "reason": "resolved", "count": 1, "classification": "PERSISTENT",
             "resolved_at": "2026-01-02T00:00:00+00:00"},
        ]
        out = io.StringIO()
        with patch.object(cli, "load_config", return_value=self.config), \
             patch.object(cli, "load_state_for_read", return_value=self.state), \
             redirect_stdout(out):
            rc = cli.main(["blocker", "list", "--resolved", "--json"])
        self.assertEqual(rc, 0)
        result = json.loads(out.getvalue())
        self.assertEqual(len(result), 1)

    def test_blocker_resolve_clears_blocker(self):
        """blocker resolve <id> sets resolved_at on the blocker."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            config = copy.deepcopy(self.config)
            config["state_path"] = f"{tmpdir}/state.json"
            state = cli.initial_state(config)
            cli.seed_confirmed_onboard(config, state)
            state["blockers"] = [
                {"id": "blk-001", "at": "2026-01-01T00:00:00+00:00", "last_at": "2026-01-01T00:00:00+00:00",
                 "scope": "test", "reason": "test blocker", "count": 1, "classification": "PERSISTENT",
                 "resolved_at": None},
            ]
            cli.save_state(config, state)
            out = io.StringIO()
            with patch.object(cli, "load_config", return_value=config), redirect_stdout(out):
                rc = cli.main(["blocker", "resolve", "blk-001", "--json"])
            self.assertEqual(rc, 0)
            updated = cli.load_state_for_read(config)
            blocker = next(b for b in updated["blockers"] if b["id"] == "blk-001")
            self.assertIsNotNone(blocker.get("resolved_at"))

    # ── decision ──────────────────────────────────────────────────────────────

    def test_decision_list_returns_decisions(self):
        """decision list with 2 decision_records returns 2."""
        self.state["decision_records"] = [
            {"id": "dec-001", "at": "2026-01-01T00:00:00+00:00", "outcome": "ACCEPT", "scope": "product"},
            {"id": "dec-002", "at": "2026-01-02T00:00:00+00:00", "outcome": "REJECT", "scope": "runtime"},
        ]
        out = io.StringIO()
        with patch.object(cli, "load_config", return_value=self.config), \
             patch.object(cli, "load_state_for_read", return_value=self.state), \
             redirect_stdout(out):
            rc = cli.main(["decision", "list", "--json"])
        self.assertEqual(rc, 0)
        result = json.loads(out.getvalue())
        self.assertEqual(len(result), 2)

    def test_decision_inspect_returns_full_record(self):
        """decision inspect <id> returns the full record."""
        self.state["decision_records"] = [
            {"id": "dec-001", "at": "2026-01-01T00:00:00+00:00", "outcome": "ACCEPT",
             "scope": "product", "reasoning": "test reason"},
        ]
        out = io.StringIO()
        with patch.object(cli, "load_config", return_value=self.config), \
             patch.object(cli, "load_state_for_read", return_value=self.state), \
             redirect_stdout(out):
            rc = cli.main(["decision", "inspect", "dec-001", "--json"])
        self.assertEqual(rc, 0)
        result = json.loads(out.getvalue())
        self.assertEqual(result["id"], "dec-001")
        self.assertEqual(result["reasoning"], "test reason")

    # ── govern ────────────────────────────────────────────────────────────────

    def test_govern_list_gates_returns_blocking_gaps(self):
        """govern list-gates with 2 BLOCKING and 1 WARNING gap returns 2."""
        self.state["integrity_gaps"] = [
            {"id": "igap-001", "kind": "operator-gate-required", "severity": "BLOCKING", "active": True,
             "at": "2026-01-01T00:00:00+00:00"},
            {"id": "igap-002", "kind": "operator-gate-required", "severity": "BLOCKING", "active": True,
             "at": "2026-01-01T00:00:00+00:00"},
            {"id": "igap-003", "kind": "warning-gap", "severity": "WARNING", "active": True,
             "at": "2026-01-01T00:00:00+00:00"},
        ]
        out = io.StringIO()
        with patch.object(cli, "load_config", return_value=self.config), \
             patch.object(cli, "load_state_for_read", return_value=self.state), \
             redirect_stdout(out):
            rc = cli.main(["govern", "list-gates", "--json"])
        self.assertEqual(rc, 0)
        result = json.loads(out.getvalue())
        self.assertEqual(len(result), 2)
        self.assertTrue(all(g["severity"] == "BLOCKING" for g in result))

    def test_govern_clear_deactivates_gap(self):
        """govern clear <gap_id> sets gap.active=False."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            config = copy.deepcopy(self.config)
            config["state_path"] = f"{tmpdir}/state.json"
            state = cli.initial_state(config)
            cli.seed_confirmed_onboard(config, state)
            state["integrity_gaps"] = [
                {"id": "igap-001", "kind": "operator-gate-required", "severity": "BLOCKING",
                 "active": True, "at": "2026-01-01T00:00:00+00:00"},
            ]
            cli.save_state(config, state)
            out = io.StringIO()
            with patch.object(cli, "load_config", return_value=config), redirect_stdout(out):
                rc = cli.main(["govern", "clear", "igap-001", "--json"])
            self.assertEqual(rc, 0)
            updated = cli.load_state_for_read(config)
            gap = next(g for g in updated["integrity_gaps"] if g["id"] == "igap-001")
            self.assertFalse(gap.get("active"))

    # ── check --fail-on ───────────────────────────────────────────────────────

    def test_check_fail_on_blocking_exits_1(self):
        """check --fail-on BLOCKING with active BLOCKING gap returns 1."""
        self.state["integrity_gaps"] = [
            {"id": "igap-001", "kind": "test-gap", "severity": "BLOCKING", "active": True},
        ]
        with patch.object(cli, "load_config", return_value=self.config), \
             patch.object(cli, "load_state_for_read", return_value=self.state), \
             redirect_stdout(io.StringIO()):
            rc = cli.main(["check", "--fail-on", "BLOCKING"])
        self.assertEqual(rc, 1)

    def test_check_fail_on_no_blocking_exits_0(self):
        """check --fail-on BLOCKING with only WARNING gap returns 0."""
        self.state["integrity_gaps"] = [
            {"id": "igap-001", "kind": "test-gap", "severity": "WARNING", "active": True},
        ]
        with patch.object(cli, "load_config", return_value=self.config), \
             patch.object(cli, "load_state_for_read", return_value=self.state), \
             redirect_stdout(io.StringIO()):
            rc = cli.main(["check", "--fail-on", "BLOCKING"])
        self.assertEqual(rc, 0)

    # ── integrity-signal ──────────────────────────────────────────────────────

    def test_integrity_signal_list_returns_unresolved(self):
        """integrity-signal list with 2 signals (1 resolved) returns 1."""
        self.state["integrity_signals"] = [
            {"id": "isig-001", "signal_type": "auth-failure", "severity": "WARNING",
             "at": "2026-01-01T00:00:00+00:00"},
            {"id": "isig-002", "signal_type": "auth-failure", "severity": "WARNING",
             "at": "2026-01-02T00:00:00+00:00", "resolved_at": "2026-01-03T00:00:00+00:00"},
        ]
        out = io.StringIO()
        with patch.object(cli, "load_config", return_value=self.config), \
             patch.object(cli, "load_state_for_read", return_value=self.state), \
             redirect_stdout(out):
            rc = cli.main(["integrity-signal", "list", "--json"])
        self.assertEqual(rc, 0)
        result = json.loads(out.getvalue())
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "isig-001")


class R75AuditObservabilityTests(unittest.TestCase):
    """r75 — TraceRecord, _emit_trace, urace trace command (§62r)."""

    def setUp(self):
        self.config = isolated_test_config(self)
        self.config["executor"]["enabled"] = False
        self.state = cli.initial_state(self.config)

    # ── initial_state ─────────────────────────────────────────────────────────

    def test_initial_state_has_trace_records(self):
        """initial_state() contains trace_records == []."""
        self.assertIn("trace_records", self.state)
        self.assertEqual(self.state["trace_records"], [])

    # ── _emit_trace helper ────────────────────────────────────────────────────

    def test_emit_trace_appends_record(self):
        """_emit_trace appends one TraceRecord entry."""
        cli._emit_trace(self.state, "TRANSITION", "test summary")
        self.assertEqual(len(self.state["trace_records"]), 1)

    def test_emit_trace_fields_complete(self):
        """Emitted TraceRecord has all required fields with correct values."""
        cli._emit_trace(self.state, "CYCLE", "cycle started", cycle_id="cycle-abc")
        rec = self.state["trace_records"][0]
        self.assertTrue(rec["id"].startswith("trace-"))
        self.assertIn("at", rec)
        self.assertEqual(rec["kind"], "CYCLE")
        self.assertEqual(rec["summary"], "cycle started")
        self.assertEqual(rec["cycle_id"], "cycle-abc")
        self.assertEqual(rec["recorded_by"], "runtime")

    # ── cycle() emits trace records ───────────────────────────────────────────

    def test_cycle_emits_trace_records(self):
        """Running one cycle produces at least one TraceRecord."""
        cli.seed_confirmed_onboard(self.config, self.state)
        cli.cycle(self.config, self.state, allow_execution=False)
        self.assertGreater(len(self.state.get("trace_records", [])), 0)

    # ── trace list command ────────────────────────────────────────────────────

    def test_trace_list_returns_records(self):
        """trace list returns all trace_records."""
        self.state["trace_records"] = [
            {"id": "trace-001", "at": "2026-01-03T00:00:00+00:00", "kind": "CYCLE", "summary": "s3", "recorded_by": "runtime"},
            {"id": "trace-002", "at": "2026-01-02T00:00:00+00:00", "kind": "TRANSITION", "summary": "s2", "recorded_by": "runtime"},
            {"id": "trace-003", "at": "2026-01-01T00:00:00+00:00", "kind": "CYCLE", "summary": "s1", "recorded_by": "runtime"},
        ]
        out = io.StringIO()
        with patch.object(cli, "load_config", return_value=self.config), \
             patch.object(cli, "load_state_for_read", return_value=self.state), \
             redirect_stdout(out):
            rc = cli.main(["trace", "list", "--json"])
        self.assertEqual(rc, 0)
        result = json.loads(out.getvalue())
        self.assertEqual(len(result), 3)

    def test_trace_list_filters_by_kind(self):
        """trace list --kind TRANSITION returns only TRANSITION records."""
        self.state["trace_records"] = [
            {"id": "trace-001", "at": "2026-01-02T00:00:00+00:00", "kind": "CYCLE", "summary": "s1", "recorded_by": "runtime"},
            {"id": "trace-002", "at": "2026-01-01T00:00:00+00:00", "kind": "TRANSITION", "summary": "s2", "recorded_by": "runtime"},
        ]
        out = io.StringIO()
        with patch.object(cli, "load_config", return_value=self.config), \
             patch.object(cli, "load_state_for_read", return_value=self.state), \
             redirect_stdout(out):
            rc = cli.main(["trace", "list", "--kind", "TRANSITION", "--json"])
        self.assertEqual(rc, 0)
        result = json.loads(out.getvalue())
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "trace-002")

    def test_trace_list_respects_limit(self):
        """trace list --limit 3 returns at most 3 records."""
        self.state["trace_records"] = [
            {"id": f"trace-{i:03d}", "at": f"2026-01-{i:02d}T00:00:00+00:00", "kind": "CYCLE", "summary": f"s{i}", "recorded_by": "runtime"}
            for i in range(1, 11)
        ]
        out = io.StringIO()
        with patch.object(cli, "load_config", return_value=self.config), \
             patch.object(cli, "load_state_for_read", return_value=self.state), \
             redirect_stdout(out):
            rc = cli.main(["trace", "list", "--limit", "3", "--json"])
        self.assertEqual(rc, 0)
        result = json.loads(out.getvalue())
        self.assertEqual(len(result), 3)

    def test_trace_list_filters_by_cycle_id(self):
        """trace list --cycle-id X returns only records for that cycle."""
        self.state["trace_records"] = [
            {"id": "trace-001", "at": "2026-01-02T00:00:00+00:00", "kind": "CYCLE", "summary": "s1", "cycle_id": "cycle-aaa", "recorded_by": "runtime"},
            {"id": "trace-002", "at": "2026-01-01T00:00:00+00:00", "kind": "TRANSITION", "summary": "s2", "cycle_id": "cycle-bbb", "recorded_by": "runtime"},
            {"id": "trace-003", "at": "2026-01-03T00:00:00+00:00", "kind": "CYCLE", "summary": "s3", "cycle_id": "cycle-aaa", "recorded_by": "runtime"},
        ]
        out = io.StringIO()
        with patch.object(cli, "load_config", return_value=self.config), \
             patch.object(cli, "load_state_for_read", return_value=self.state), \
             redirect_stdout(out):
            rc = cli.main(["trace", "list", "--cycle-id", "cycle-aaa", "--json"])
        self.assertEqual(rc, 0)
        result = json.loads(out.getvalue())
        self.assertEqual(len(result), 2)
        self.assertTrue(all(r.get("cycle_id") == "cycle-aaa" for r in result))

    # ── trace inspect command ─────────────────────────────────────────────────

    def test_trace_inspect_returns_full_record(self):
        """trace inspect <id> returns the full TraceRecord."""
        self.state["trace_records"] = [
            {"id": "trace-xyz", "at": "2026-01-01T00:00:00+00:00", "kind": "DECISION", "summary": "decision made",
             "cycle_id": None, "operation_id": None, "decision_id": "dec-001", "detail": None, "recorded_by": "runtime"},
        ]
        out = io.StringIO()
        with patch.object(cli, "load_config", return_value=self.config), \
             patch.object(cli, "load_state_for_read", return_value=self.state), \
             redirect_stdout(out):
            rc = cli.main(["trace", "inspect", "trace-xyz", "--json"])
        self.assertEqual(rc, 0)
        result = json.loads(out.getvalue())
        self.assertEqual(result["id"], "trace-xyz")
        self.assertEqual(result["kind"], "DECISION")

    def test_trace_inspect_missing_id_returns_1(self):
        """trace inspect with nonexistent id returns exit code 1."""
        self.state["trace_records"] = []
        out = io.StringIO()
        with patch.object(cli, "load_config", return_value=self.config), \
             patch.object(cli, "load_state_for_read", return_value=self.state), \
             redirect_stdout(out):
            rc = cli.main(["trace", "inspect", "trace-nonexistent"])
        self.assertEqual(rc, 1)


class R77ClosedLoopTests(unittest.TestCase):
    """r77 Closed-Loop Autonomy: FeedbackAccumulator, OutputSchemaRegistry, schema/feedback CLI."""

    def setUp(self):
        self.config = isolated_test_config(self)
        self.config["executor"] = {**self.config.get("executor", {}), "enabled": False}
        self.state = cli.initial_state(self.config)
        self.state["lifecycle_state"] = "ACTIVE"

    # ── initial_state ─────────────────────────────────────────────────────────

    def test_initial_state_has_outcome_feedback_records(self):
        self.assertIn("outcome_feedback_records", self.state)
        self.assertIsInstance(self.state["outcome_feedback_records"], list)

    # ── OUTPUT_SCHEMA_REGISTRY ────────────────────────────────────────────────

    def test_output_schema_registry_has_check(self):
        from urace.primitives import OUTPUT_SCHEMA_REGISTRY
        self.assertIn("check", OUTPUT_SCHEMA_REGISTRY)
        self.assertIn("fields", OUTPUT_SCHEMA_REGISTRY["check"])

    def test_output_schema_registry_has_feedback_list(self):
        from urace.primitives import OUTPUT_SCHEMA_REGISTRY
        self.assertIn("feedback list", OUTPUT_SCHEMA_REGISTRY)

    # ── IGC registration ─────────────────────────────────────────────────────

    def test_r77_igc_kinds_registered(self):
        from urace.primitives import INTEGRITY_GAP_CATALOG
        for kind in ("layer-boundary-violation", "output-schema-unregistered",
                     "feedback-overdue", "feedback-negative-objective", "feedback-negative-decision"):
            self.assertIn(kind, INTEGRITY_GAP_CATALOG, f"IGC missing: {kind}")

    # ── _run_feedback_accumulator ─────────────────────────────────────────────

    def test_feedback_accumulator_skips_non_active(self):
        self.state["lifecycle_state"] = "PAUSED"
        self.state["outcome_feedback_records"] = [
            {"id": "ofbk-1", "target_id": "obj-1", "target_kind": "OBJECTIVE",
             "signal": "NEGATIVE", "processed": False}
        ]
        cli._run_feedback_accumulator(self.config, self.state)
        gaps = [g for g in self.state.get("integrity_gaps", []) if g.get("kind") == "feedback-negative-objective"]
        self.assertEqual(len(gaps), 0)

    def test_feedback_accumulator_negative_objective_emits_gap(self):
        self.state["outcome_feedback_records"] = [
            {"id": "ofbk-2", "target_id": "obj-42", "target_kind": "OBJECTIVE",
             "signal": "NEGATIVE", "processed": False}
        ]
        cli._run_feedback_accumulator(self.config, self.state)
        gaps = [g for g in self.state.get("integrity_gaps", []) if g.get("kind") == "feedback-negative-objective"]
        self.assertEqual(len(gaps), 1)
        self.assertIn("obj-42", gaps[0].get("detail", ""))

    def test_feedback_accumulator_negative_decision_emits_gap(self):
        self.state["outcome_feedback_records"] = [
            {"id": "ofbk-3", "target_id": "dec-77", "target_kind": "DECISION",
             "signal": "NEGATIVE", "processed": False}
        ]
        cli._run_feedback_accumulator(self.config, self.state)
        gaps = [g for g in self.state.get("integrity_gaps", []) if g.get("kind") == "feedback-negative-decision"]
        self.assertEqual(len(gaps), 1)
        self.assertIn("dec-77", gaps[0].get("detail", ""))

    def test_feedback_accumulator_positive_no_gap(self):
        self.state["outcome_feedback_records"] = [
            {"id": "ofbk-4", "target_id": "obj-99", "target_kind": "OBJECTIVE",
             "signal": "POSITIVE", "processed": False}
        ]
        cli._run_feedback_accumulator(self.config, self.state)
        gaps = [g for g in self.state.get("integrity_gaps", [])
                if g.get("kind") in ("feedback-negative-objective", "feedback-negative-decision")]
        self.assertEqual(len(gaps), 0)

    def test_feedback_accumulator_marks_processed(self):
        rec = {"id": "ofbk-5", "target_id": "obj-1", "target_kind": "OBJECTIVE",
               "signal": "NEGATIVE", "processed": False}
        self.state["outcome_feedback_records"] = [rec]
        cli._run_feedback_accumulator(self.config, self.state)
        self.assertTrue(rec["processed"])

    def test_feedback_accumulator_idempotent(self):
        rec = {"id": "ofbk-6", "target_id": "obj-2", "target_kind": "OBJECTIVE",
               "signal": "NEGATIVE", "processed": False}
        self.state["outcome_feedback_records"] = [rec]
        cli._run_feedback_accumulator(self.config, self.state)
        cli._run_feedback_accumulator(self.config, self.state)
        gaps = [g for g in self.state.get("integrity_gaps", []) if g.get("kind") == "feedback-negative-objective"]
        self.assertEqual(len(gaps), 1)

    def test_feedback_overdue_emitted_for_old_accepted_objective(self):
        old_ts = (datetime.now(timezone.utc) - timedelta(hours=200)).isoformat()
        self.state["objectives"] = [
            {"id": "obj-old", "status": "ACCEPTED", "accepted_at": old_ts}
        ]
        self.state["outcome_feedback_records"] = []
        cli._run_feedback_accumulator(self.config, self.state)
        gaps = [g for g in self.state.get("integrity_gaps", []) if g.get("kind") == "feedback-overdue"]
        self.assertEqual(len(gaps), 1)
        self.assertIn("obj-old", gaps[0].get("detail", ""))

    def test_feedback_overdue_not_emitted_when_feedback_exists(self):
        old_ts = (datetime.now(timezone.utc) - timedelta(hours=200)).isoformat()
        self.state["objectives"] = [
            {"id": "obj-covered", "status": "ACCEPTED", "accepted_at": old_ts}
        ]
        self.state["outcome_feedback_records"] = [
            {"id": "ofbk-7", "target_id": "obj-covered", "target_kind": "OBJECTIVE",
             "signal": "POSITIVE", "processed": True}
        ]
        cli._run_feedback_accumulator(self.config, self.state)
        gaps = [g for g in self.state.get("integrity_gaps", []) if g.get("kind") == "feedback-overdue"]
        self.assertEqual(len(gaps), 0)

    # ── schema CLI ────────────────────────────────────────────────────────────

    def test_schema_list_json(self):
        out = io.StringIO()
        with patch.object(cli, "load_config", return_value=self.config), \
             redirect_stdout(out):
            rc = cli.main(["schema", "list", "--json"])
        self.assertEqual(rc, 0)
        result = json.loads(out.getvalue())
        self.assertIn("schemas", result)
        self.assertTrue(len(result["schemas"]) > 0)

    def test_schema_inspect_check_json(self):
        out = io.StringIO()
        with patch.object(cli, "load_config", return_value=self.config), \
             redirect_stdout(out):
            rc = cli.main(["schema", "inspect", "check", "--json"])
        self.assertEqual(rc, 0)
        result = json.loads(out.getvalue())
        self.assertEqual(result["command"], "check")
        self.assertIn("fields", result)

    def test_schema_inspect_unknown_returns_1(self):
        out = io.StringIO()
        err = io.StringIO()
        with patch.object(cli, "load_config", return_value=self.config), \
             redirect_stdout(out), redirect_stderr(err):
            rc = cli.main(["schema", "inspect", "nonexistent-command"])
        self.assertEqual(rc, 1)

    # ── feedback CLI ──────────────────────────────────────────────────────────

    def test_feedback_list_empty_json(self):
        self.state["outcome_feedback_records"] = []
        out = io.StringIO()
        with patch.object(cli, "load_config", return_value=self.config), \
             patch.object(cli, "load_state_for_read", return_value=self.state), \
             redirect_stdout(out):
            rc = cli.main(["feedback", "list", "--json"])
        self.assertEqual(rc, 0)
        result = json.loads(out.getvalue())
        self.assertEqual(result["total"], 0)
        self.assertEqual(result["records"], [])

    def test_feedback_submit_invalid_prefix_returns_1(self):
        """feedback submit with non obj-/dec- target_id returns 1."""
        out = io.StringIO()
        err = io.StringIO()
        with patch.object(cli, "load_config", return_value=self.config), \
             redirect_stdout(out), redirect_stderr(err):
            rc = cli.main(["feedback", "submit", "goal-123", "--signal", "POSITIVE"])
        self.assertEqual(rc, 1)

    def test_feedback_list_signal_filter(self):
        """feedback list --signal NEGATIVE only returns NEGATIVE records."""
        self.state["outcome_feedback_records"] = [
            {"id": "ofbk-a", "signal": "POSITIVE", "target_id": "obj-1", "target_kind": "OBJECTIVE",
             "at": "2026-01-01T00:00:00+00:00", "recorded_by": "operator", "event_kind": "OUTCOME_FEEDBACK",
             "processed": True},
            {"id": "ofbk-b", "signal": "NEGATIVE", "target_id": "obj-2", "target_kind": "OBJECTIVE",
             "at": "2026-01-01T01:00:00+00:00", "recorded_by": "operator", "event_kind": "OUTCOME_FEEDBACK",
             "processed": True},
        ]
        out = io.StringIO()
        with patch.object(cli, "load_config", return_value=self.config), \
             patch.object(cli, "load_state_for_read", return_value=self.state), \
             redirect_stdout(out):
            rc = cli.main(["feedback", "list", "--signal", "NEGATIVE", "--json"])
        self.assertEqual(rc, 0)
        result = json.loads(out.getvalue())
        self.assertEqual(len(result["records"]), 1)
        self.assertEqual(result["records"][0]["id"], "ofbk-b")

    def test_feedback_list_target_filter(self):
        """feedback list --target filters by target_id."""
        self.state["outcome_feedback_records"] = [
            {"id": "ofbk-c", "signal": "POSITIVE", "target_id": "obj-1", "target_kind": "OBJECTIVE",
             "at": "2026-01-01T00:00:00+00:00", "recorded_by": "operator", "event_kind": "OUTCOME_FEEDBACK",
             "processed": True},
            {"id": "ofbk-d", "signal": "NEGATIVE", "target_id": "obj-99", "target_kind": "OBJECTIVE",
             "at": "2026-01-01T01:00:00+00:00", "recorded_by": "operator", "event_kind": "OUTCOME_FEEDBACK",
             "processed": True},
        ]
        out = io.StringIO()
        with patch.object(cli, "load_config", return_value=self.config), \
             patch.object(cli, "load_state_for_read", return_value=self.state), \
             redirect_stdout(out):
            rc = cli.main(["feedback", "list", "--target", "obj-1", "--json"])
        self.assertEqual(rc, 0)
        result = json.loads(out.getvalue())
        self.assertEqual(len(result["records"]), 1)
        self.assertEqual(result["records"][0]["id"], "ofbk-c")

    def test_feedback_submit_audit_record_fields(self):
        """feedback submit creates a record with AuditRecord base fields (at, recorded_by, event_kind)."""
        import tempfile, json as _json
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
            state_file = tf.name
        cfg = isolated_test_config(self)
        cfg["state_path"] = state_file
        st = cli.initial_state(cfg)
        cli.save_state(cfg, st)
        out = io.StringIO()
        with patch.object(cli, "load_config", return_value=cfg), redirect_stdout(out):
            rc = cli.main(["feedback", "submit", "obj-test-001", "--signal", "POSITIVE", "--json"])
        self.assertEqual(rc, 0)
        payload = _json.loads(out.getvalue())
        self.assertIn("id", payload)
        # Verify state was written with correct AuditRecord fields
        written = _json.loads(Path(state_file).read_text(encoding="utf-8"))
        recs = written.get("outcome_feedback_records", [])
        self.assertEqual(len(recs), 1)
        r = recs[0]
        self.assertIn("at", r)
        self.assertEqual(r.get("recorded_by"), "operator")
        self.assertEqual(r.get("event_kind"), "OUTCOME_FEEDBACK")
        self.assertEqual(r.get("target_kind"), "OBJECTIVE")
        os.unlink(state_file)
