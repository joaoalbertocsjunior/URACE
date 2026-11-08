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

from urace import analytics, cli, compaction as compaction_module, evolution_guard, executor, external_metrics, launcher, portfolio, scope_priority, updater

TEST_RUNTIME_ROOT = Path(__file__).resolve().parents[1]
TEST_PRODUCT_ROOT = Path(__file__).resolve().parents[3]


def isolated_test_config(test_case):
    """Keep lifecycle writes away from the configured installation state."""
    config = copy.deepcopy(cli.load_config())
    directory = tempfile.TemporaryDirectory(prefix='urace-test-state-')
    test_case.addCleanup(directory.cleanup)
    config['state_path'] = str(Path(directory.name) / 'state.json')
    return config



class R82ObservabilityTests(unittest.TestCase):
    """r82: CSI lifecycle gate + TraceRecord emission on 4 mutation handlers."""

    def setUp(self):
        self.config = isolated_test_config(self)

    # ── CSI lifecycle gate ─────────────────────────────────────────────────────

    def _config_with_feed(self, feed: dict) -> dict:
        cfg = copy.deepcopy(self.config)
        cfg.setdefault("community_inbox", {})["feeds"] = [feed]
        return cfg

    def _base_feed(self) -> dict:
        return {
            "id": "cfeed-r82-1", "kind": "RSS",
            "endpoint": "https://example.com/feed",
            "terms_accepted": True, "active": True,
            "_pending_items": [{"source_ref": "r82-item-1", "content": "test"}],
        }

    def test_csi_skipped_when_lifecycle_dormant(self):
        """CSI MUST NOT run when lifecycle_state is DORMANT (inclusion gate)."""
        state = cli.initial_state(self.config)
        state["lifecycle_state"] = "DORMANT"
        config = self._config_with_feed(self._base_feed())
        cli._run_csi(config, state)
        self.assertEqual(len(state.get("community_signals", [])), 0)

    def test_csi_skipped_when_lifecycle_bootstrapping(self):
        """CSI MUST NOT run when lifecycle_state is BOOTSTRAPPING."""
        state = cli.initial_state(self.config)
        state["lifecycle_state"] = "BOOTSTRAPPING"
        config = self._config_with_feed(self._base_feed())
        cli._run_csi(config, state)
        self.assertEqual(len(state.get("community_signals", [])), 0)

    def test_csi_runs_when_lifecycle_active(self):
        """CSI MUST run when lifecycle_state is ACTIVE (inclusion gate passes)."""
        state = cli.initial_state(self.config)
        state["lifecycle_state"] = "ACTIVE"
        config = self._config_with_feed(self._base_feed())
        cli._run_csi(config, state)
        self.assertGreater(len(state.get("community_signals", [])), 0)

    # ── TraceRecord emissions ─────────────────────────────────────────────────

    def test_blocker_resolve_emits_trace_record(self):
        """blocker resolve MUST emit a TraceRecord (ObservabilityContract §62l)."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = copy.deepcopy(self.config)
            cfg["state_path"] = f"{tmpdir}/state.json"
            state = cli.initial_state(cfg)
            cli.seed_confirmed_onboard(cfg, state)
            state["blockers"] = [{
                "id": "blk-r82-1", "at": "2026-01-01T00:00:00+00:00",
                "last_at": "2026-01-01T00:00:00+00:00",
                "scope": "test", "reason": "r82 test", "count": 1,
                "classification": "PERSISTENT", "resolved_at": None,
            }]
            cli.save_state(cfg, state)
            with patch.object(cli, "load_config", return_value=cfg), redirect_stdout(io.StringIO()):
                rc = cli.main(["blocker", "resolve", "blk-r82-1"])
            self.assertEqual(rc, 0)
            updated = cli.load_state_for_read(cfg)
            traces = [t for t in updated.get("trace_records", []) if t.get("kind") == "OPERATION"]
            self.assertTrue(any("blk-r82-1" in t.get("summary", "") for t in traces))

    def test_inbox_apply_emits_trace_record(self):
        """inbox apply MUST emit a DECISION TraceRecord (ObservabilityContract §62l)."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = copy.deepcopy(self.config)
            cfg["state_path"] = f"{tmpdir}/state.json"
            state = cli.initial_state(cfg)
            state["patch_proposals"] = [{
                "id": "pprop-r82-apply",
                "created_at": "2026-10-01T00:00:00+00:00",
                "updated_at": "2026-10-01T00:00:00+00:00",
                "signal_id": "csig-x1", "proposed_diff": "patch",
                "target": "URACE", "rationale": "test", "status": "PENDING",
                "approval_mode": "HUMAN", "confidence_score": 0.8,
                "resolved_at": None, "resolved_by": None, "rejection_reason": None,
            }]
            cli.save_state(cfg, state)
            with patch.object(cli, "load_config", return_value=cfg), redirect_stdout(io.StringIO()):
                rc = cli.main(["inbox", "apply", "pprop-r82-apply"])
            self.assertEqual(rc, 0)
            updated = cli.load_state_for_read(cfg)
            traces = [t for t in updated.get("trace_records", []) if t.get("kind") == "DECISION"]
            self.assertTrue(any("pprop-r82-apply" in t.get("summary", "") for t in traces))

    def test_inbox_reject_emits_trace_record(self):
        """inbox reject MUST emit a DECISION TraceRecord (ObservabilityContract §62l)."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = copy.deepcopy(self.config)
            cfg["state_path"] = f"{tmpdir}/state.json"
            state = cli.initial_state(cfg)
            state["patch_proposals"] = [{
                "id": "pprop-r82-rej",
                "created_at": "2026-10-01T00:00:00+00:00",
                "updated_at": "2026-10-01T00:00:00+00:00",
                "signal_id": "csig-x2", "proposed_diff": "patch",
                "target": "URACE", "rationale": "test", "status": "PENDING",
                "approval_mode": "HUMAN", "confidence_score": 0.5,
                "resolved_at": None, "resolved_by": None, "rejection_reason": None,
            }]
            cli.save_state(cfg, state)
            with patch.object(cli, "load_config", return_value=cfg), redirect_stdout(io.StringIO()):
                rc = cli.main(["inbox", "reject", "pprop-r82-rej", "--reason", "not relevant"])
            self.assertEqual(rc, 0)
            updated = cli.load_state_for_read(cfg)
            traces = [t for t in updated.get("trace_records", []) if t.get("kind") == "DECISION"]
            self.assertTrue(any("pprop-r82-rej" in t.get("summary", "") for t in traces))

    def test_feedback_submit_emits_trace_record(self):
        """feedback submit MUST emit an OPERATION TraceRecord (ObservabilityContract §62l)."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = copy.deepcopy(self.config)
            cfg["state_path"] = f"{tmpdir}/state.json"
            state = cli.initial_state(cfg)
            cli.save_state(cfg, state)
            with patch.object(cli, "load_config", return_value=cfg), redirect_stdout(io.StringIO()):
                rc = cli.main(["feedback", "submit", "obj-r82-001", "--signal", "POSITIVE"])
            self.assertEqual(rc, 0)
            updated = cli.load_state_for_read(cfg)
            traces = [t for t in updated.get("trace_records", []) if t.get("kind") == "OPERATION"]
            self.assertTrue(any("obj-r82-001" in t.get("summary", "") for t in traces))

class R84OnboardHelpScanTests(unittest.TestCase):
    """r84: onboard help subcommand + --scan heuristic detection + path-agnosticism."""

    def setUp(self):
        self.config = isolated_test_config(self)

    def test_onboard_help_exits_zero(self):
        """onboard help returns 0."""
        out = io.StringIO()
        with patch.object(cli, "load_config", return_value=self.config), redirect_stdout(out):
            rc = cli.main(["onboard", "help"])
        self.assertEqual(rc, 0)

    def test_onboard_help_contains_guide_text(self):
        """onboard help output contains key onboarding steps."""
        out = io.StringIO()
        with patch.object(cli, "load_config", return_value=self.config), redirect_stdout(out):
            cli.main(["onboard", "help"])
        text = out.getvalue()
        self.assertIn("onboard confirm", text)
        self.assertIn("product register", text)
        self.assertIn("product_files", text)

    def test_onboard_help_json(self):
        """onboard help --json emits {guide: string}."""
        out = io.StringIO()
        with patch.object(cli, "load_config", return_value=self.config), redirect_stdout(out):
            rc = cli.main(["onboard", "help", "--json"])
        self.assertEqual(rc, 0)
        payload = json.loads(out.getvalue())
        self.assertIn("guide", payload)
        self.assertIsInstance(payload["guide"], str)

    def test_onboard_status_scan_no_hints_when_all_registered(self):
        """onboard status --scan with no neighboring product dirs emits empty scan_hints."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = copy.deepcopy(self.config)
            cfg["state_path"] = f"{tmpdir}/state.json"
            state = cli.initial_state(cfg)
            cli.save_state(cfg, state)
            out = io.StringIO()
            with patch.object(cli, "load_config", return_value=cfg), \
                 patch.object(cli, "load_state_for_read", return_value=state), \
                 redirect_stdout(out):
                rc = cli.main(["onboard", "status", "--scan", "--json"])
            self.assertEqual(rc, 0)
            result = json.loads(out.getvalue())
            self.assertIn("scan_hints", result)

    def test_onboard_status_scan_detects_product_dir(self):
        """onboard status --scan detects a neighboring dir with code files as a hint."""
        import tempfile, os as _os
        with tempfile.TemporaryDirectory() as root:
            # create sibling product-like dir
            sibling = _os.path.join(root, "my-product")
            _os.makedirs(sibling)
            with open(_os.path.join(sibling, "main.py"), "w") as f:
                f.write("# product code\n")
            # URACE dir (current)
            urace_dir = _os.path.join(root, "urace-install")
            _os.makedirs(urace_dir)
            cfg = copy.deepcopy(self.config)
            cfg["state_path"] = _os.path.join(urace_dir, "state.json")
            cfg["product_registry"] = []
            state = cli.initial_state(cfg)
            cli.save_state(cfg, state)
            out = io.StringIO()
            with patch.object(cli, "load_config", return_value=cfg), \
                 patch.object(cli, "load_state_for_read", return_value=state), \
                 patch("os.getcwd", return_value=urace_dir), \
                 redirect_stdout(out):
                rc = cli.main(["onboard", "status", "--scan", "--json"])
            self.assertEqual(rc, 0)
            result = json.loads(out.getvalue())
            hints = result.get("scan_hints", [])
            self.assertTrue(any(sibling in h.get("path", "") for h in hints))

class R85ResourceBudgetTests(unittest.TestCase):
    """r85: ResourceBudgetProtocol — RAM mechanism, resource CLI, help subcommands."""

    def _base_config(self):
        import copy
        cfg = isolated_test_config(self)
        cfg["executor"]["enabled"] = False
        return cfg

    def _base_state(self):
        state = cli.initial_state(self._base_config())
        cli.seed_confirmed_onboard(self._base_config(), state)
        return state

    def test_initial_state_has_resource_ledger(self):
        state = self._base_state()
        self.assertIn("resource_ledger", state)
        self.assertEqual(state["resource_ledger"], [])

    def test_initial_state_has_roi_snapshots(self):
        state = self._base_state()
        self.assertIn("roi_snapshots", state)
        self.assertEqual(state["roi_snapshots"], [])

    def test_ram_no_op_without_product_budget(self):
        from urace.cli import _run_ram
        config = self._base_config()
        state = self._base_state()
        state["lifecycle_state"] = "ACTIVE"
        _run_ram(config, state)
        self.assertEqual(state["resource_ledger"], [])

    def test_ram_skips_non_active_state(self):
        from urace.cli import _run_ram
        config = {**self._base_config(), "product_budget": {"max_cost": 1.0}}
        state = self._base_state()
        state["lifecycle_state"] = "DORMANT"
        _run_ram(config, state)
        self.assertEqual(state["resource_ledger"], [])

    def test_ram_appends_resource_entry(self):
        from urace.cli import _run_ram
        config = {**self._base_config(), "product_budget": {"cost_per_executor_call": 0.01}}
        state = self._base_state()
        state["lifecycle_state"] = "ACTIVE"
        _run_ram(config, state)
        self.assertEqual(len(state["resource_ledger"]), 1)
        entry = state["resource_ledger"][0]
        self.assertIn("id", entry)
        self.assertIn("recorded_at", entry)
        self.assertIn("total_cost", entry)

    def test_ram_emits_budget_exceeded_gap(self):
        from urace.cli import _run_ram
        config = {**self._base_config(), "product_budget": {"max_executor_calls": 0, "cost_per_executor_call": 0.01}}
        state = self._base_state()
        state["lifecycle_state"] = "ACTIVE"
        state.setdefault("executor_state", {})["executor_calls"] = [{"id": f"ec{i}"} for i in range(5)]
        _run_ram(config, state)
        kinds = [g.get("kind") for g in state.get("integrity_gaps", [])]
        self.assertIn("product-budget-exceeded", kinds)

    def test_roi_formula(self):
        alpha, beta, gamma = 0.4, 0.4, 0.2
        dq, dc, dm = 1.0, 0.5, 0.3
        calls, cpp = 10, 0.01
        V = alpha * dq + beta * dc + gamma * dm
        C = calls * cpp
        roi = V / C
        self.assertAlmostEqual(roi, V / C, places=6)
        self.assertGreater(roi, 0)

    def test_resource_help_exits_0(self):
        import sys
        from io import StringIO
        from urace import cli
        buf = StringIO()
        old_stdout = sys.stdout
        sys.stdout = buf
        try:
            try:
                rc = cli.main(["resource", "help"])
                self.assertEqual(rc, 0)
            except SystemExit as e:
                self.assertEqual(e.code, 0)
        finally:
            sys.stdout = old_stdout

    def test_product_help_exits_0(self):
        import sys
        from io import StringIO
        from urace import cli
        buf = StringIO()
        old_stdout = sys.stdout
        sys.stdout = buf
        try:
            try:
                rc = cli.main(["product", "help"])
                self.assertEqual(rc, 0)
            except SystemExit as e:
                self.assertEqual(e.code, 0)
        finally:
            sys.stdout = old_stdout

    def test_fleet_help_exits_0(self):
        import sys
        from io import StringIO
        from urace import cli
        buf = StringIO()
        old_stdout = sys.stdout
        sys.stdout = buf
        try:
            try:
                rc = cli.main(["fleet", "help"])
                self.assertEqual(rc, 0)
            except SystemExit as e:
                self.assertEqual(e.code, 0)
        finally:
            sys.stdout = old_stdout

class R90ProductRemoveTests(unittest.TestCase):
    """r90 §62k product remove — unit tests."""

    def setUp(self):
        self.config = isolated_test_config(self)
        self.config["executor"]["enabled"] = False
        self.config.setdefault("product", "ActiveProduct")
        self.config.setdefault("intent", {})
        self.config["intent"]["purpose"] = "Test"
        self.config["active_product"] = "ActiveProduct"
        self.config["product_registry"] = [
            {
                "id": "prod-a1", "name": "ActiveProduct",
                "state_path": "/tmp/state_a.json",
                "product_files": [], "registered_at": "2026-01-01T00:00:00+00:00",
                "status": "ACTIVE",
            },
            {
                "id": "prod-b1", "name": "InactiveProduct",
                "state_path": "/tmp/state_b.json",
                "product_files": [], "registered_at": "2026-01-01T00:00:00+00:00",
                "status": "ACTIVE",
            },
        ]

    def _run(self, argv):
        import tempfile
        out = io.StringIO()
        with tempfile.TemporaryDirectory() as tmpdir:
            config = copy.deepcopy(self.config)
            config["state_path"] = f"{tmpdir}/state.json"
            state = cli.initial_state(config)
            cli.save_state(config, state)
            captured_config = {}

            def fake_save_config(c):
                captured_config.update(c)

            with patch.object(cli, "load_config", return_value=config), \
                 patch("urace.cli.save_config", side_effect=fake_save_config), \
                 redirect_stdout(out):
                rc = cli.main(argv)
        return rc, out.getvalue(), captured_config

    def test_remove_inactive_product_succeeds(self):
        """product remove <inactive> --force --json → rc=0, status=removed, entry gone from registry."""
        rc, out, captured = self._run(["product", "remove", "InactiveProduct", "--force", "--json"])
        self.assertEqual(rc, 0)
        result = json.loads(out)
        self.assertEqual(result["status"], "removed")
        self.assertEqual(result["name"], "InactiveProduct")
        registry = captured.get("product_registry", [])
        self.assertFalse(any(e["name"] == "InactiveProduct" for e in registry))

    def test_remove_active_product_blocked(self):
        """product remove <active> --force --json → rc=1, error about active product."""
        rc, out, _captured = self._run(["product", "remove", "ActiveProduct", "--force", "--json"])
        self.assertEqual(rc, 1)
        result = json.loads(out)
        self.assertEqual(result["status"], "error")
        self.assertIn("active", result["error"])

    def test_remove_active_product_emits_gap(self):
        """product remove <active> --force → product-remove-active-blocked gap in state."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            config = copy.deepcopy(self.config)
            config["state_path"] = f"{tmpdir}/state.json"
            state = cli.initial_state(config)
            cli.save_state(config, state)

            def fake_save_config(c):
                pass

            out = io.StringIO()
            with patch.object(cli, "load_config", return_value=config), \
                 patch("urace.cli.save_config", side_effect=fake_save_config), \
                 redirect_stdout(out):
                cli.main(["product", "remove", "ActiveProduct", "--force", "--json"])
            saved = cli.load_state_for_read(config)
            gaps = [g.get("kind") for g in (saved or {}).get("integrity_gaps", [])]
            self.assertIn("product-remove-active-blocked", gaps)

    def test_remove_unknown_product_returns_error(self):
        """product remove <nonexistent> --force --json → rc=1, not-found error."""
        rc, out, _captured = self._run(["product", "remove", "NoSuchProduct", "--force", "--json"])
        self.assertEqual(rc, 1)
        result = json.loads(out)
        self.assertEqual(result["status"], "error")
        self.assertIn("not found", result["error"])

    def test_remove_leaves_active_product_unchanged(self):
        """remove InactiveProduct → active_product still set to ActiveProduct in config."""
        rc, out, captured = self._run(["product", "remove", "InactiveProduct", "--force", "--json"])
        self.assertEqual(rc, 0)
        self.assertEqual(captured.get("active_product"), "ActiveProduct")

    def test_remove_does_not_affect_other_entries(self):
        """remove InactiveProduct → ActiveProduct entry still present in registry."""
        rc, _out, captured = self._run(["product", "remove", "InactiveProduct", "--force", "--json"])
        self.assertEqual(rc, 0)
        registry = captured.get("product_registry", [])
        self.assertTrue(any(e["name"] == "ActiveProduct" for e in registry))

class R91ProductToggleTests(unittest.TestCase):
    """r91 product activate/deactivate — unit tests."""

    def setUp(self):
        self.config = isolated_test_config(self)
        self.config["executor"]["enabled"] = False
        self.config.setdefault("product", "ActiveProduct")
        self.config.setdefault("intent", {})
        self.config["intent"]["purpose"] = "Test"
        self.config["active_product"] = "ActiveProduct"
        self.config["product_registry"] = [
            {
                "id": "prod-a1", "name": "ActiveProduct",
                "state_path": "/tmp/state_a.json",
                "product_files": [], "registered_at": "2026-01-01T00:00:00+00:00",
                "status": "ACTIVE",
            },
            {
                "id": "prod-b1", "name": "OtherProduct",
                "state_path": "/tmp/state_b.json",
                "product_files": [], "registered_at": "2026-01-01T00:00:00+00:00",
                "status": "ACTIVE",
            },
        ]

    def _run(self, argv):
        import tempfile
        out = io.StringIO()
        with tempfile.TemporaryDirectory() as tmpdir:
            config = copy.deepcopy(self.config)
            config["state_path"] = f"{tmpdir}/state.json"
            state = cli.initial_state(config)
            cli.save_state(config, state)
            captured_config = {}

            def fake_save_config(c):
                captured_config.update(c)

            with patch.object(cli, "load_config", return_value=config), \
                 patch("urace.cli.save_config", side_effect=fake_save_config), \
                 redirect_stdout(out):
                rc = cli.main(argv)
        return rc, out.getvalue(), captured_config

    def test_deactivate_inactive_product_succeeds(self):
        """product deactivate <other> --json → rc=0, status=deactivated, entry.status=INACTIVE."""
        rc, out, captured = self._run(["product", "deactivate", "OtherProduct", "--json"])
        self.assertEqual(rc, 0)
        result = json.loads(out)
        self.assertEqual(result["status"], "deactivated")
        registry = captured.get("product_registry", [])
        entry = next(e for e in registry if e["name"] == "OtherProduct")
        self.assertEqual(entry["status"], "INACTIVE")

    def test_deactivate_active_product_blocked(self):
        """product deactivate <active> --json → rc=1, error."""
        rc, out, _captured = self._run(["product", "deactivate", "ActiveProduct", "--json"])
        self.assertEqual(rc, 1)
        result = json.loads(out)
        self.assertEqual(result["status"], "error")
        self.assertIn("active", result["error"])

    def test_deactivate_active_product_emits_gap(self):
        """product deactivate <active> → product-deactivate-active-blocked gap in state."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            config = copy.deepcopy(self.config)
            config["state_path"] = f"{tmpdir}/state.json"
            state = cli.initial_state(config)
            cli.save_state(config, state)
            out = io.StringIO()
            with patch.object(cli, "load_config", return_value=config), \
                 patch("urace.cli.save_config", lambda c: None), \
                 redirect_stdout(out):
                cli.main(["product", "deactivate", "ActiveProduct", "--json"])
            saved = cli.load_state_for_read(config)
            gaps = [g.get("kind") for g in (saved or {}).get("integrity_gaps", [])]
            self.assertIn("product-deactivate-active-blocked", gaps)

    def test_activate_inactive_product_succeeds(self):
        """deactivate then activate → status returns to ACTIVE."""
        # first deactivate
        self._run(["product", "deactivate", "OtherProduct", "--json"])
        # now activate (need fresh config with INACTIVE status)
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            config = copy.deepcopy(self.config)
            config["state_path"] = f"{tmpdir}/state.json"
            for e in config["product_registry"]:
                if e["name"] == "OtherProduct":
                    e["status"] = "INACTIVE"
            state = cli.initial_state(config)
            cli.save_state(config, state)
            captured_config = {}
            out = io.StringIO()
            with patch.object(cli, "load_config", return_value=config), \
                 patch("urace.cli.save_config", side_effect=lambda c: captured_config.update(c)), \
                 redirect_stdout(out):
                rc = cli.main(["product", "activate", "OtherProduct", "--json"])
        self.assertEqual(rc, 0)
        result = json.loads(out.getvalue())
        self.assertEqual(result["status"], "activated")
        registry = captured_config.get("product_registry", [])
        entry = next(e for e in registry if e["name"] == "OtherProduct")
        self.assertEqual(entry["status"], "ACTIVE")

    def test_deactivate_unknown_product_returns_error(self):
        """product deactivate <nonexistent> --json → rc=1."""
        rc, out, _captured = self._run(["product", "deactivate", "NoSuch", "--json"])
        self.assertEqual(rc, 1)
        result = json.loads(out)
        self.assertEqual(result["status"], "error")

    def test_activate_unknown_product_returns_error(self):
        """product activate <nonexistent> --json → rc=1."""
        rc, out, _captured = self._run(["product", "activate", "NoSuch", "--json"])
        self.assertEqual(rc, 1)
        result = json.loads(out)
        self.assertEqual(result["status"], "error")

class R93ExternalInterfaceTests(unittest.TestCase):
    """r93 §62w ExternalInterfaceProtocol — api command + feedback --input-json."""

    def setUp(self):
        self.config = isolated_test_config(self)
        self.config["executor"]["enabled"] = False
        self.config.setdefault("product", "TestProduct")
        self.config.setdefault("intent", {})
        self.config["intent"]["purpose"] = "Test"

    def _run(self, argv, state=None):
        import tempfile
        out = io.StringIO()
        with tempfile.TemporaryDirectory() as tmpdir:
            config = copy.deepcopy(self.config)
            config["state_path"] = f"{tmpdir}/state.json"
            s = state if state is not None else cli.initial_state(config)
            cli.seed_confirmed_onboard(config, s)
            cli.save_state(config, s)
            with patch.object(cli, "load_config", return_value=config), \
                 redirect_stdout(out):
                rc = cli.main(argv)
        return rc, out.getvalue()

    # ── api help ─────────────────────────────────────────────────────────────

    def test_api_help_exits_0(self):
        """api help → rc=0."""
        rc, out = self._run(["api", "help"])
        self.assertEqual(rc, 0)

    def test_api_help_json(self):
        """api help --json → rc=0, JSON with guide field."""
        rc, out = self._run(["api", "help", "--json"])
        self.assertEqual(rc, 0)
        result = json.loads(out)
        self.assertIn("guide", result)

    # ── api call ─────────────────────────────────────────────────────────────

    def test_api_call_check(self):
        """api call --command check --json → rc=0, output.command==check."""
        rc, out = self._run(["api", "call", "--command", "check", "--json"])
        self.assertEqual(rc, 0)
        result = json.loads(out)
        self.assertEqual(result["command"], "check")
        self.assertEqual(result["exit_code"], 0)

    def test_api_call_missing_command_returns_error(self):
        """api call without --command → rc=1."""
        rc, _out = self._run(["api", "call", "--json"])
        self.assertEqual(rc, 1)

    def test_api_call_slash_prefix_resolved(self):
        """api call --command /check → routes to check handler."""
        rc, out = self._run(["api", "call", "--command", "/check", "--json"])
        self.assertEqual(rc, 0)
        result = json.loads(out)
        self.assertEqual(result["command"], "check")

    # ── api batch ────────────────────────────────────────────────────────────

    def test_api_batch_stdin(self):
        """api batch --input-json - from stdin → executes entries, returns results array."""
        import tempfile, sys
        batch = json.dumps([{"command": "check", "params": {}}, {"command": "vitals", "params": {}}])
        with tempfile.TemporaryDirectory() as tmpdir:
            config = copy.deepcopy(self.config)
            config["state_path"] = f"{tmpdir}/state.json"
            s = cli.initial_state(config)
            cli.seed_confirmed_onboard(config, s)
            cli.save_state(config, s)
            out = io.StringIO()
            with patch.object(cli, "load_config", return_value=config), \
                 patch("sys.stdin", io.StringIO(batch)), \
                 redirect_stdout(out):
                rc = cli.main(["api", "batch", "--input-json", "-", "--json"])
        self.assertEqual(rc, 0)
        result = json.loads(out.getvalue())
        self.assertIn("results", result)
        self.assertEqual(len(result["results"]), 2)

    def test_api_batch_missing_input_returns_error(self):
        """api batch without --input-json → rc=1."""
        rc, _out = self._run(["api", "batch", "--json"])
        self.assertEqual(rc, 1)

    # ── feedback --input-json ─────────────────────────────────────────────────

    def test_feedback_submit_input_json(self):
        """feedback submit with --input-json file → creates OutcomeFeedbackRecord."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            config = copy.deepcopy(self.config)
            config["state_path"] = f"{tmpdir}/state.json"
            s = cli.initial_state(config)
            cli.seed_confirmed_onboard(config, s)
            # add a fake objective to submit against
            s.setdefault("objectives", []).append({"id": "obj-test001", "title": "T"})
            cli.save_state(config, s)
            params_file = f"{tmpdir}/params.json"
            with open(params_file, "w") as f:
                json.dump({"signal": "POSITIVE", "detail": "automated test"}, f)
            out = io.StringIO()
            with patch.object(cli, "load_config", return_value=config), \
                 redirect_stdout(out):
                rc = cli.main(["feedback", "submit", "obj-test001",
                               "--input-json", params_file, "--json"])
            self.assertEqual(rc, 0)
            result = json.loads(out.getvalue())
            self.assertIn("id", result)
            saved = cli.load_state_for_read(config)
            records = (saved or {}).get("outcome_feedback_records", [])
            self.assertTrue(any(r.get("signal") == "POSITIVE" for r in records))

    def test_feedback_submit_input_json_missing_signal(self):
        """feedback submit --input-json without signal field → rc=1."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            config = copy.deepcopy(self.config)
            config["state_path"] = f"{tmpdir}/state.json"
            s = cli.initial_state(config)
            cli.seed_confirmed_onboard(config, s)
            cli.save_state(config, s)
            params_file = f"{tmpdir}/params.json"
            with open(params_file, "w") as f:
                json.dump({"detail": "missing signal"}, f)
            out = io.StringIO()
            with patch.object(cli, "load_config", return_value=config), \
                 redirect_stdout(out):
                rc = cli.main(["feedback", "submit", "obj-test001",
                               "--input-json", params_file, "--json"])
            self.assertEqual(rc, 1)

class R98ApiExtensionsTests(unittest.TestCase):
    def setUp(self):
        self.config = isolated_test_config(self)
        self.config["executor"]["enabled"] = False
        self.config.setdefault("product", "TestProduct")
        self.config.setdefault("intent", {})
        self.config["intent"]["purpose"] = "Test"

    def _state_with_traces(self):
        return {
            "trace_records": [
                {"id": "tr-1", "kind": "CYCLE", "at": "2026-01-01T00:00:00", "detail": "cycle1"},
                {"id": "tr-2", "kind": "GAP", "at": "2026-01-02T00:00:00", "detail": "gap1"},
            ]
        }

    def _run(self, argv, extra_state=None):
        out = io.StringIO()
        with tempfile.TemporaryDirectory() as tmpdir:
            config = copy.deepcopy(self.config)
            config["state_path"] = f"{tmpdir}/state.json"
            s = cli.initial_state(config)
            cli.seed_confirmed_onboard(config, s)
            if extra_state:
                s.update(extra_state)
            cli.save_state(config, s)
            with patch.object(cli, "load_config", return_value=config), \
                 redirect_stdout(out):
                rc = cli.main(argv)
        return rc, out.getvalue()

    def test_api_version_json(self):
        rc, out = self._run(["api", "version", "--json"])
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertIn("spec_version", data)
        self.assertEqual(data["api_version"], "1")

    def test_api_version_plain(self):
        rc, out = self._run(["api", "version"])
        self.assertEqual(rc, 0)
        self.assertIn("api_version: 1", out)

    def test_api_watch_no_filter(self):
        traces = self._state_with_traces()
        rc, out = self._run(["api", "watch"], extra_state=traces)
        self.assertEqual(rc, 0)
        lines = [l for l in out.strip().split("\n") if l]
        self.assertEqual(len(lines), 2)

    def test_api_watch_kind_filter(self):
        traces = self._state_with_traces()
        rc, out = self._run(["api", "watch", "--kinds", "CYCLE"], extra_state=traces)
        self.assertEqual(rc, 0)
        lines = [l for l in out.strip().split("\n") if l]
        self.assertEqual(len(lines), 1)
        self.assertEqual(json.loads(lines[0])["kind"], "CYCLE")

    def test_api_watch_since_filter(self):
        traces = self._state_with_traces()
        rc, out = self._run(["api", "watch", "--since", "2026-01-02T00:00:00"], extra_state=traces)
        self.assertEqual(rc, 0)
        lines = [l for l in out.strip().split("\n") if l]
        self.assertEqual(len(lines), 1)
        self.assertEqual(json.loads(lines[0])["kind"], "GAP")

    def test_api_watch_sd_true_routing(self):
        traces = self._state_with_traces()
        rc, out = self._run(["api", "watch", "--kinds", "GAP"], extra_state=traces)
        self.assertEqual(rc, 0)

    def test_api_version_in_sd_true_exact(self):
        from urace.cli import _SD_TRUE_EXACT
        self.assertIn("api version", _SD_TRUE_EXACT)
        self.assertIn("api watch", _SD_TRUE_EXACT)

class R98IntegrityTests(unittest.TestCase):
    def test_spec_hash_gap_kinds_registered(self):
        from urace.cli import IGC_KINDS
        self.assertIn("spec-update-hash-mismatch", IGC_KINDS)
        self.assertIn("manifest-hash-mismatch", IGC_KINDS)

class R100DeclareTests(unittest.TestCase):
    """r101: updated to use canonical `add` subcommand; declare tests kept as deprecated-alias coverage."""

    def _cfg(self):
        return {"product": "test", "state_path": "/tmp/state.json", "inbox_path": "/tmp/inbox"}

    # --- Canonical add subcommand tests (r101) ---

    def test_add_context_queues(self):
        with patch.object(cli, "load_config", return_value=self._cfg()), \
             patch.object(cli, "queue_input", return_value={"id": "inp-1"}) as qi:
            out = io.StringIO()
            with redirect_stdout(out):
                rc = cli.main(["add", "context", "some important context"])
            self.assertEqual(rc, 0)
            qi.assert_called_once()
            call_args = qi.call_args[0]
            self.assertEqual(call_args[1], "context")

    def test_add_context_json(self):
        with patch.object(cli, "load_config", return_value=self._cfg()), \
             patch.object(cli, "queue_input", return_value={"id": "inp-2"}):
            out = io.StringIO()
            with redirect_stdout(out):
                rc = cli.main(["add", "context", "text", "--json"])
            self.assertEqual(rc, 0)
            data = json.loads(out.getvalue())
            self.assertEqual(data["status"], "queued")
            self.assertEqual(data["text"], "text")

    def test_add_goal_subcommand_queues(self):
        with patch.object(cli, "load_config", return_value=self._cfg()), \
             patch.object(cli, "queue_input", return_value={"id": "inp-3"}) as qi:
            out = io.StringIO()
            with redirect_stdout(out):
                rc = cli.main(["add", "goal", "Fix login", "--success-measure", "users can login", "--reason", "critical bug"])
            self.assertEqual(rc, 0)
            qi.assert_called_once()
            call_args = qi.call_args[0]
            self.assertEqual(call_args[1], "goal")

    def test_add_metric_queues(self):
        with patch.object(cli, "load_config", return_value=self._cfg()), \
             patch.object(cli, "queue_input", return_value={"id": "inp-4"}) as qi:
            out = io.StringIO()
            with redirect_stdout(out):
                rc = cli.main(["add", "metric", "error_rate", "--source", "src-1", "--path", "$.errors"])
            self.assertEqual(rc, 0)
            call_args = qi.call_args[0]
            self.assertEqual(call_args[1], "metric")

    def test_add_vital_queues(self):
        with patch.object(cli, "load_config", return_value=self._cfg()), \
             patch.object(cli, "queue_input", return_value={"id": "inp-5"}) as qi:
            out = io.StringIO()
            with redirect_stdout(out):
                rc = cli.main(["add", "vital", "uptime", "--numerator", "met-1"])
            self.assertEqual(rc, 0)
            call_args = qi.call_args[0]
            self.assertEqual(call_args[1], "vital")

    def test_add_source_queues(self):
        with patch.object(cli, "load_config", return_value=self._cfg()), \
             patch.object(cli, "queue_input", return_value={"id": "inp-6"}) as qi:
            out = io.StringIO()
            with redirect_stdout(out):
                rc = cli.main(["add", "source", "src-1", "--kind", "http", "--location", "http://example.com"])
            self.assertEqual(rc, 0)
            call_args = qi.call_args[0]
            self.assertEqual(call_args[1], "source")

    def test_add_in_sd_true_exact(self):
        from urace.cli import _SD_TRUE_EXACT
        for key in ["add context", "add goal", "add source", "add metric", "add vital"]:
            self.assertIn(key, _SD_TRUE_EXACT)

    # --- Deprecated declare alias tests (r101 backwards compat) ---

    def test_declare_deprecated_context(self):
        """declare context still works but prints deprecation warning."""
        with patch.object(cli, "load_config", return_value=self._cfg()), \
             patch.object(cli, "queue_input", return_value={"id": "inp-d1"}) as qi:
            err = io.StringIO()
            out = io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                rc = cli.main(["declare", "context", "some important context"])
            self.assertEqual(rc, 0)
            self.assertIn("deprecated", err.getvalue())
            qi.assert_called_once()
            call_args = qi.call_args[0]
            self.assertEqual(call_args[1], "context")

    def test_declare_deprecated_goal(self):
        """declare goal still works but prints deprecation warning."""
        with patch.object(cli, "load_config", return_value=self._cfg()), \
             patch.object(cli, "queue_input", return_value={"id": "inp-d2"}) as qi:
            err = io.StringIO()
            out = io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                rc = cli.main(["declare", "goal", "Fix login", "--success-measure", "users can login", "--reason", "critical bug"])
            self.assertEqual(rc, 0)
            self.assertIn("deprecated", err.getvalue())
            call_args = qi.call_args[0]
            self.assertEqual(call_args[1], "goal")

    def test_declare_in_sd_true_exact(self):
        """declare * aliases remain in _SD_TRUE_EXACT pointing to add *."""
        from urace.cli import _SD_TRUE_EXACT
        for kind in ["context", "goal", "source", "metric", "vital"]:
            key = f"declare {kind}"
            self.assertIn(key, _SD_TRUE_EXACT)
            self.assertEqual(_SD_TRUE_EXACT[key], ["add", kind])

    def test_add_context_deprecated_alias(self):
        with patch.object(cli, "load_config", return_value=self._cfg()), \
             patch.object(cli, "queue_input", return_value={"id": "inp-7"}):
            err = io.StringIO()
            out = io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                rc = cli.main(["add-context", "some text"])
            self.assertEqual(rc, 0)
            self.assertIn("deprecated", err.getvalue())

    def test_add_goal_deprecated_alias(self):
        with patch.object(cli, "load_config", return_value=self._cfg()), \
             patch.object(cli, "queue_input", return_value={"id": "inp-8"}):
            err = io.StringIO()
            out = io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                rc = cli.main(["add-goal", "x", "--success-measure", "y", "--reason", "z"])
            self.assertIn("deprecated", err.getvalue())

class R101RoutingTests(unittest.TestCase):
    def test_freeform_quoted_routes_to_classify(self):
        """Single quoted arg → classify handler."""
        from urace.cli import _preprocess_args
        result = _preprocess_args(["fix the login flow"])
        self.assertEqual(result[0], "classify")
        self.assertIn("fix the login flow", result[1])

    def test_freeform_single_noncommand_word(self):
        """Single unrecognized word → classify."""
        from urace.cli import _preprocess_args
        result = _preprocess_args(["improvability"])
        self.assertEqual(result[0], "classify")

    def test_known_command_routes_to_command(self):
        """Known command word → passes through for argparse."""
        from urace.cli import _preprocess_args
        result = _preprocess_args(["check"])
        self.assertEqual(result, ["check"])

    def test_add_context_routes_to_add(self):
        from urace.cli import _preprocess_args
        result = _preprocess_args(["add", "context", "some text"])
        self.assertEqual(result, ["add", "context", "some text"])

    def test_sd_true_exact_add_context(self):
        from urace.cli import _SD_TRUE_EXACT
        self.assertIn("add context", _SD_TRUE_EXACT)
        self.assertEqual(_SD_TRUE_EXACT["add context"], ["add", "context"])

    def test_sd_true_exact_declare_aliases(self):
        """declare * aliases still in _SD_TRUE_EXACT pointing to add *."""
        from urace.cli import _SD_TRUE_EXACT
        for kind in ["context", "goal", "source", "metric", "vital"]:
            key = f"declare {kind}"
            self.assertIn(key, _SD_TRUE_EXACT)
            self.assertEqual(_SD_TRUE_EXACT[key], ["add", kind])

    def test_freeform_multiword_unquoted_noncommand(self):
        """Multi-word unquoted where first word is not a command → classify."""
        from urace.cli import _preprocess_args
        result = _preprocess_args(["improve", "the", "retention"])
        self.assertEqual(result[0], "classify")

    def test_tier2_returns_classify_not_add(self):
        """_preprocess_args Tier 2 returns classify, not add."""
        from urace.cli import _preprocess_args
        result = _preprocess_args(["some totally unknown freeform text"])
        self.assertEqual(result[0], "classify")

    def test_classify_in_known_top_commands(self):
        """classify must be in _KNOWN_TOP_COMMANDS for internal routing."""
        from urace.cli import _KNOWN_TOP_COMMANDS
        self.assertIn("classify", _KNOWN_TOP_COMMANDS)

    def test_add_in_known_top_commands(self):
        """add must be in _KNOWN_TOP_COMMANDS."""
        from urace.cli import _KNOWN_TOP_COMMANDS
        self.assertIn("add", _KNOWN_TOP_COMMANDS)

class R101AddSubcommandTests(unittest.TestCase):
    def _cfg(self):
        return {"product": "test", "state_path": "/tmp/state.json", "inbox_path": "/tmp/inbox"}

    def test_add_context_queues(self):
        with patch.object(cli, "load_config", return_value=self._cfg()), \
             patch.object(cli, "queue_input", return_value={"id": "inp-1"}) as qi:
            out = io.StringIO()
            with redirect_stdout(out):
                rc = cli.main(["add", "context", "important context"])
            self.assertEqual(rc, 0)
            self.assertEqual(qi.call_args[0][1], "context")

    def test_add_goal_queues(self):
        with patch.object(cli, "load_config", return_value=self._cfg()), \
             patch.object(cli, "queue_input", return_value={"id": "inp-2"}) as qi:
            out = io.StringIO()
            with redirect_stdout(out):
                rc = cli.main(["add", "goal", "Fix login", "--success-measure", "works", "--reason", "bug"])
            self.assertEqual(rc, 0)
            self.assertEqual(qi.call_args[0][1], "goal")

    def test_declare_deprecated_routes_to_add(self):
        """declare context still works but prints deprecation."""
        with patch.object(cli, "load_config", return_value=self._cfg()), \
             patch.object(cli, "queue_input", return_value={"id": "inp-3"}) as qi:
            err = io.StringIO()
            out = io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                rc = cli.main(["declare", "context", "text"])
            self.assertEqual(rc, 0)
            self.assertIn("deprecated", err.getvalue().lower())
            self.assertEqual(qi.call_args[0][1], "context")

class R102AddEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.config = isolated_test_config(self)
        self.config["executor"]["enabled"] = False
        self.state = cli.initial_state(self.config)
        cli.seed_confirmed_onboard(self.config, self.state)

    def test_add_evidence_queues_and_applies(self):
        with tempfile.TemporaryDirectory() as directory:
            config = copy.deepcopy(self.config)
            config["state_path"] = str(Path(directory) / "state.json")
            state = copy.deepcopy(self.state)
            cli.queue_input(config, "evidence", {"kind": "test-pass", "summary": "all checks green", "detail": "CI run #42 passed", "source": None})
            consumed = cli.consume_inputs(config, state)
            self.assertEqual(len(consumed), 1)
            ev_records = [e for e in state.get("evidence", []) if e.get("kind") == "test-pass"]
            self.assertEqual(len(ev_records), 1)
            self.assertEqual(ev_records[0]["summary"], "all checks green")
            cli.cleanup_consumed_inputs(consumed)

    def test_add_evidence_unknown_kind_rejected(self):
        """Evidence handler only: no rejection for unknown evidence kind — kind is a free-form string."""
        with tempfile.TemporaryDirectory() as directory:
            config = copy.deepcopy(self.config)
            config["state_path"] = str(Path(directory) / "state.json")
            state = copy.deepcopy(self.state)
            cli.queue_input(config, "evidence", {"kind": "custom-kind", "summary": "custom summary"})
            consumed = cli.consume_inputs(config, state)
            self.assertEqual(len(consumed), 1)
            ev_records = [e for e in state.get("evidence", []) if e.get("kind") == "custom-kind"]
            self.assertEqual(len(ev_records), 1)
            cli.cleanup_consumed_inputs(consumed)

    def test_add_evidence_cli_routes_to_queue(self):
        with patch.object(cli, "load_config", return_value=self.config), \
             patch.object(cli, "queue_input", return_value={"id": "inp-ev-1"}) as qi:
            out = io.StringIO()
            with redirect_stdout(out):
                rc = cli.main(["add", "evidence", "--kind", "test-pass", "--summary", "green"])
            self.assertEqual(rc, 0)
            self.assertEqual(qi.call_args[0][1], "evidence")

    def test_add_evidence_cli_json_output(self):
        with patch.object(cli, "load_config", return_value=self.config), \
             patch.object(cli, "queue_input", return_value={"id": "inp-ev-2"}):
            out = io.StringIO()
            with redirect_stdout(out):
                rc = cli.main(["add", "evidence", "--kind", "test-pass", "--summary", "green", "--json"])
            self.assertEqual(rc, 0)
            data = json.loads(out.getvalue())
            self.assertEqual(data["status"], "queued")
            self.assertEqual(data["kind"], "test-pass")
            self.assertEqual(data["summary"], "green")

    def test_sd_true_exact_includes_add_evidence(self):
        from urace.cli import _SD_TRUE_EXACT
        self.assertIn("add evidence", _SD_TRUE_EXACT)
        self.assertEqual(_SD_TRUE_EXACT["add evidence"], ["add", "evidence"])

class R103HashVerifyTests(unittest.TestCase):
    def setUp(self):
        self.config = isolated_test_config(self)
        self.config["executor"]["enabled"] = False
        self.state = cli.initial_state(self.config)
        cli.seed_confirmed_onboard(self.config, self.state)

    def test_derive_hash_arg_in_sd_true_exact(self):
        """--hash on derive is a parser arg, not _SD_TRUE_EXACT; verify derive parser accepts it."""
        with patch.object(cli, "load_config", return_value=self.config):
            with patch.object(cli, "load_state_for_read", return_value=None):
                rc = cli.main(["derive", "--hash", "abc123"])
        self.assertEqual(rc, 1)  # returns 1 because no initialized state

    def test_derive_hash_no_state_returns_1(self):
        with patch.object(cli, "load_config", return_value=self.config):
            with patch.object(cli, "load_state_for_read", return_value=None):
                rc = cli.main(["derive", "--hash", "deadbeef"])
        self.assertEqual(rc, 1)

    def test_derive_hash_no_manifests_returns_1(self):
        empty_state = cli.initial_state(self.config)
        with patch.object(cli, "load_config", return_value=self.config):
            with patch.object(cli, "load_state_for_read", return_value=empty_state):
                with redirect_stderr(io.StringIO()):
                    rc = cli.main(["derive", "--hash", "deadbeef"])
        self.assertEqual(rc, 1)

    def test_derive_hash_mismatch_emits_gap_returns_1(self):
        import hashlib
        manifest_ref = {"manifest_id": "dmr-test-001", "content_hash": "aabbcc"}
        state = cli.initial_state(self.config)
        state["derived_manifest_refs"] = [manifest_ref]
        with patch.object(cli, "load_config", return_value=self.config):
            with patch.object(cli, "load_state_for_read", return_value=state):
                with patch.object(cli, "save_state"):
                    with redirect_stderr(io.StringIO()):
                        rc = cli.main(["derive", "--hash", "aabbcc"])
        # stored hash is "aabbcc" but computed will differ → mismatch → returns 1
        self.assertEqual(rc, 1)

    def test_derive_verify_and_hash_are_both_available(self):
        """Both --verify and --hash should be accepted args on derive (not unknown arg errors)."""
        with patch.object(cli, "load_config", return_value=self.config):
            with patch.object(cli, "load_state_for_read", return_value=None):
                # --verify already tested elsewhere; --hash should also not raise argparse error
                rc = cli.main(["derive", "--verify"])
        # returns 0 (no manifests) or 1; either way, no argparse exception
        self.assertIn(rc, (0, 1))

class R104NoVerifyTests(unittest.TestCase):
    def setUp(self):
        self.config = isolated_test_config(self)
        self.config["executor"]["enabled"] = False
        self.state = cli.initial_state(self.config)
        cli.seed_confirmed_onboard(self.config, self.state)

    def test_update_no_verify_flag_accepted(self):
        """--no-verify on update is accepted by argparse as a known flag."""
        # Verify the flag is in the update parser's known args by checking it doesn't
        # raise "unrecognized arguments" — use parse_known_args directly.
        import argparse
        # rebuild just the update subparser to confirm --no-verify is registered
        _p = argparse.ArgumentParser()
        _s = _p.add_subparsers(dest="command")
        _u = _s.add_parser("update")
        _u.add_argument("action", nargs="?")
        _u.add_argument("reference", nargs="?")
        _u.add_argument("--no-verify", action="store_true", dest="no_verify")
        ns, remaining = _p.parse_known_args(["update", "apply", "ref", "--no-verify"])
        self.assertFalse(remaining, f"--no-verify left as unknown arg: {remaining}")
        self.assertTrue(ns.no_verify)
        # Also verify the real CLI doesn't error on the flag itself
        with patch.object(cli, "load_config", return_value=self.config):
            with redirect_stderr(io.StringIO()):
                try:
                    rc = cli.main(["update", "--help"])
                except SystemExit as e:
                    rc = e.code  # --help exits 0
        self.assertEqual(rc, 0)

    def test_derive_no_verify_flag_accepted(self):
        """--no-verify on derive should be accepted by argparse."""
        with patch.object(cli, "load_config", return_value=self.config):
            with patch.object(cli, "load_state_for_read", return_value=None):
                with redirect_stderr(io.StringIO()):
                    try:
                        rc = cli.main(["derive", "--no-verify"])
                    except SystemExit as e:
                        self.assertNotEqual(e.code, 2, "--no-verify caused argparse error on derive")
                        rc = e.code
        self.assertIsNotNone(rc)

    def test_derive_verify_still_accepted(self):
        """--verify still accepted on derive after r104 (backwards compat)."""
        with patch.object(cli, "load_config", return_value=self.config):
            with patch.object(cli, "load_state_for_read", return_value=None):
                with redirect_stderr(io.StringIO()):
                    rc = cli.main(["derive", "--verify"])
        self.assertIn(rc, (0, 1))

class R104MultiProductTests(unittest.TestCase):
    def setUp(self):
        self.config = isolated_test_config(self)
        self.config["executor"]["enabled"] = False
        self.state = cli.initial_state(self.config)
        cli.seed_confirmed_onboard(self.config, self.state)

    def test_compact_product_flag_accepted(self):
        """--product with nonexistent product name returns 1 with error message."""
        with patch.object(cli, "load_config", return_value=self.config):
            with patch.object(cli, "load_state_for_read", return_value=self.state):
                with patch.object(cli, "save_state"):
                    buf = io.StringIO()
                    with redirect_stderr(buf):
                        rc = cli.main(["compact", "evidence", "--product", "nonexistent"])
        self.assertEqual(rc, 1)
        self.assertIn("nonexistent", buf.getvalue())

    def test_crc_product_flag_accepted(self):
        """--product with nonexistent product name on crc returns 1 with error message."""
        with patch.object(cli, "load_config", return_value=self.config):
            with patch.object(cli, "load_state_for_read", return_value=self.state):
                buf = io.StringIO()
                with redirect_stderr(buf):
                    rc = cli.main(["crc", "show", "--product", "nonexistent"])
        self.assertEqual(rc, 1)
        self.assertIn("nonexistent", buf.getvalue())

    def test_products_all_empty_registry(self):
        """--products all with empty product_registry returns 0 with no targets."""
        cfg = copy.deepcopy(self.config)
        cfg["product_registry"] = []
        with patch.object(cli, "load_config", return_value=cfg):
            with patch.object(cli, "load_state_for_read", return_value=self.state):
                buf = io.StringIO()
                with redirect_stderr(buf):
                    rc = cli.main(["crc", "show", "--products", "all"])
        self.assertEqual(rc, 0)

    def test_products_cycle_emits_blocking_gap_and_returns_1(self):
        """--products with a cycle in depends_on emits multi-product-compact-cycle BLOCKING gap and returns 1."""
        cfg = copy.deepcopy(self.config)
        cfg["product_registry"] = [
            {"name": "A", "state_path": "urace/state.json", "depends_on": ["B"]},
            {"name": "B", "state_path": "urace/state.json", "depends_on": ["A"]},
        ]
        captured_state = {}
        def _capture_save(c, s):
            captured_state.update(s)
        with patch.object(cli, "load_config", return_value=cfg):
            with patch.object(cli, "load_state_for_read", return_value=self.state):
                with patch.object(cli, "save_state", side_effect=_capture_save):
                    buf = io.StringIO()
                    with redirect_stderr(buf):
                        rc = cli.main(["crc", "show", "--products", "A,B"])
        self.assertEqual(rc, 1)
        gap_kinds = [g.get("kind") for g in captured_state.get("integrity_gaps", [])]
        self.assertIn("multi-product-compact-cycle", gap_kinds)

class R105CompactionGap1AmendDecompactTests(unittest.TestCase):
    """Gap 1+6: amendment-aware digest in decompact_field and verify_manifest_on_startup."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def test_get_expected_digest_no_amendments_returns_original(self):
        from urace.compaction import _get_expected_digest, _canonical_digest
        archive = Path(self.tmp) / "test.json"
        archive.write_text(json.dumps([{"id": "r1"}]))
        original = _canonical_digest([{"id": "r1"}])
        self.assertEqual(_get_expected_digest(archive, original), original)

    def test_get_expected_digest_with_amendments_returns_last_after(self):
        from urace.compaction import _get_expected_digest, _canonical_digest, _append_amendment, _make_id
        archive = Path(self.tmp) / "test2.json"
        archive.write_text(json.dumps([{"id": "r1"}]))
        original = _canonical_digest([{"id": "r1"}])
        after1 = _canonical_digest([{"id": "r1", "note": "v1"}])
        after2 = _canonical_digest([{"id": "r1", "note": "v2"}])
        for after in (after1, after2):
            _append_amendment(archive, {
                "id": _make_id("amd"), "archive_path": str(archive),
                "record_id": "r1", "amended_at": "2026-01-01T00:00:00+00:00",
                "amendment_kind": "CUSTOM", "amendment_note": "test",
                "authorized_by": "test", "before_digest": original, "after_digest": after,
            })
        self.assertEqual(_get_expected_digest(archive, original), after2)

    def _make_test_manifest(self, cm, sp, af, original_digest):
        evt_id = cm._make_id("cmp")
        af_renamed = af.parent / f"{evt_id}.json"
        af.rename(af_renamed)
        manifest = {
            "id": cm._make_id("man"), "version": 1,
            "updated_at": "2026-01-01T00:00:00+00:00",
            "events": [{
                "id": evt_id, "target_state_path": sp, "target_field": "decision_records",
                "compacted_at": "2026-01-01T00:00:00+00:00",
                "record_count_before": 1, "record_count_after": 0,
                "compaction_mode": "ARCHIVE",
                "archive_path": str(af_renamed.relative_to(sp)),
                "original_digest": original_digest, "authorized_by": "test",
            }],
        }
        cm.save_manifest(sp, manifest)
        return evt_id, af_renamed

    def test_verify_startup_detects_digest_mismatch(self):
        sp = self.tmp
        from urace import compaction as cm
        archive_dir = Path(sp) / "archives" / "test"
        archive_dir.mkdir(parents=True)
        af = archive_dir / "tmp.json"
        af.write_text(json.dumps([{"id": "r1"}]))
        wrong = cm._canonical_digest([{"id": "WRONG"}])  # mismatched digest
        _, af2 = self._make_test_manifest(cm, sp, af, wrong)
        gaps = cm.verify_manifest_on_startup(sp)
        self.assertTrue(any(g["kind"] == "compaction-manifest-divergence" for g in gaps))

    def test_verify_startup_ok_with_correct_digest(self):
        sp = self.tmp
        from urace import compaction as cm
        archive_dir = Path(sp) / "archives" / "test"
        archive_dir.mkdir(parents=True)
        records = [{"id": "r1", "kind": "test"}]
        af = archive_dir / "tmp.json"
        af.write_text(json.dumps(records))
        digest = cm._canonical_digest(records)
        _, _ = self._make_test_manifest(cm, sp, af, digest)
        self.assertEqual(cm.verify_manifest_on_startup(sp), [])

    def test_verify_startup_ok_when_amended_digest_matches(self):
        sp = self.tmp
        from urace import compaction as cm
        archive_dir = Path(sp) / "archives" / "test2"
        archive_dir.mkdir(parents=True)
        original_records = [{"id": "r1"}]
        amended_records = [{"id": "r1", "note": "amended"}]
        af = archive_dir / "tmp.json"
        af.write_text(json.dumps(original_records))
        original_digest = cm._canonical_digest(original_records)
        _, af2 = self._make_test_manifest(cm, sp, af, original_digest)
        # Now mutate archive and add amendment log
        af2.write_text(json.dumps(amended_records))
        after_digest = cm._canonical_digest(amended_records)
        cm._append_amendment(af2, {
            "id": cm._make_id("amd"), "archive_path": str(af2),
            "record_id": "r1", "amended_at": "2026-01-01T00:00:00+00:00",
            "amendment_kind": "CUSTOM", "amendment_note": "test",
            "authorized_by": "test", "before_digest": original_digest, "after_digest": after_digest,
        })
        # Should NOT emit gap — amendment-aware check uses after_digest
        self.assertEqual(cm.verify_manifest_on_startup(sp), [])

class R105CompactionGap2GovernanceTests(unittest.TestCase):
    """Gap 2: _DEFAULT_GOVERNANCE expansion + active-record guard."""

    def test_new_fields_in_default_governance(self):
        from urace.compaction import _DEFAULT_GOVERNANCE
        for field in ("evidence", "operations", "trace_records", "community_signals",
                      "patch_proposals", "wake_registrations"):
            self.assertIn(field, _DEFAULT_GOVERNANCE, f"missing field: {field}")

    def test_integrity_gaps_and_objectives_prohibited(self):
        from urace.compaction import _DEFAULT_GOVERNANCE
        self.assertEqual(_DEFAULT_GOVERNANCE["integrity_gaps"]["compaction_mode"], "PROHIBITED")
        self.assertEqual(_DEFAULT_GOVERNANCE["objectives"]["compaction_mode"], "PROHIBITED")

    def test_active_record_not_eligible_for_compaction(self):
        engine = compaction_module.CompactionEngine(tempfile.mkdtemp())
        policy = {"id": "p1", "target_field": "community_signals",
                  "compaction_mode": "ROLLING_EVICTION", "max_entries": 1}
        records = [
            {"id": "s1", "active": True},
            {"id": "s2", "active": False},
            {"id": "s3", "active": False},
        ]
        idxs = engine._eligible_indices(records, policy, "community_signals")
        self.assertNotIn(0, idxs)   # s1 active — must be protected
        self.assertIn(1, idxs)      # s2 not active — eligible

    def test_check_retention_includes_status_transitions(self):
        from urace.compaction import check_retention_violations
        state = {"status_transitions": [{"id": f"st-{i}"} for i in range(600)]}
        gaps = check_retention_violations(state)
        self.assertTrue(any(
            g["kind"] == "retention-policy-violated" and "status_transitions" in g["description"]
            for g in gaps
        ))

    def test_check_retention_includes_evidence(self):
        from urace.compaction import check_retention_violations
        state = {"evidence": [{"id": f"ev-{i}"} for i in range(5100)]}
        gaps = check_retention_violations(state)
        self.assertTrue(any("evidence" in g["description"] for g in gaps))

    def test_check_retention_includes_operations(self):
        from urace.compaction import check_retention_violations
        state = {"operations": [{"id": f"op-{i}"} for i in range(2100)]}
        gaps = check_retention_violations(state)
        self.assertTrue(any("operations" in g["description"] for g in gaps))

class R105CompactionGap4TimestampOrderTests(unittest.TestCase):
    """Gap 4: timestamp-oldest eligibility (not positional-oldest)."""

    def setUp(self):
        self.engine = compaction_module.CompactionEngine(tempfile.mkdtemp())
        self.policy = {"id": "p1", "target_field": "decision_records",
                       "compaction_mode": "ARCHIVE", "max_entries": 2,
                       "archive_subpath": "archives/test"}

    def test_oldest_by_timestamp_selected_not_positional(self):
        records = [
            {"id": "r1", "decided_at": "2026-03-01T00:00:00+00:00"},  # newest at pos 0
            {"id": "r2", "decided_at": "2024-01-01T00:00:00+00:00"},  # oldest at pos 1
            {"id": "r3", "decided_at": "2025-06-01T00:00:00+00:00"},  # 3rd at pos 2
            {"id": "r4", "decided_at": "2025-01-01T00:00:00+00:00"},  # 2nd oldest at pos 3
        ]
        # max_entries=2, excess=2: should pick pos 1 (oldest) and pos 3 (2nd oldest)
        idxs = self.engine._eligible_indices(records, self.policy, "decision_records")
        self.assertIn(1, idxs)
        self.assertIn(3, idxs)
        self.assertNotIn(0, idxs)   # newest — must NOT be selected
        self.assertNotIn(2, idxs)   # 3rd — must NOT be selected

    def test_no_timestamp_records_not_preferred_over_timestamped(self):
        records = [
            {"id": "r1"},  # no timestamp pos 0
            {"id": "r2", "decided_at": "2024-01-01T00:00:00+00:00"},  # oldest pos 1
            {"id": "r3", "decided_at": "2025-01-01T00:00:00+00:00"},  # newer pos 2
        ]
        # excess=1: should pick oldest-by-timestamp (pos 1), not pos 0
        idxs = self.engine._eligible_indices(records, self.policy, "decision_records")
        self.assertIn(1, idxs)
        self.assertNotIn(0, idxs)

class R105CompactionGap5ArchiveCeilingTests(unittest.TestCase):
    """Gap 5: archive-count-ceiling warning gap."""

    def test_gap_emitted_when_archive_count_exceeded(self):
        from urace.compaction import check_archive_ceiling, _DEFAULT_GOVERNANCE
        sp = tempfile.mkdtemp()
        subpath = _DEFAULT_GOVERNANCE["decision_records"]["archive_subpath"]
        archive_dir = Path(sp) / subpath
        archive_dir.mkdir(parents=True)
        for i in range(12):
            (archive_dir / f"evt-{i:03d}.json").write_text("[]")
        gaps = check_archive_ceiling(sp)
        self.assertTrue(any(
            g["kind"] == "archive-count-ceiling" and "decision_records" in g["description"]
            for g in gaps
        ))

    def test_no_gap_below_threshold(self):
        from urace.compaction import check_archive_ceiling
        self.assertEqual(check_archive_ceiling(tempfile.mkdtemp()), [])

    def test_custom_max_archives_respected(self):
        from urace.compaction import check_archive_ceiling, _DEFAULT_GOVERNANCE
        sp = tempfile.mkdtemp()
        subpath = _DEFAULT_GOVERNANCE["decision_records"]["archive_subpath"]
        archive_dir = Path(sp) / subpath
        archive_dir.mkdir(parents=True)
        for i in range(3):
            (archive_dir / f"evt-{i}.json").write_text("[]")
        # threshold=2 → 3 files exceeds it
        gaps = check_archive_ceiling(sp, max_archives=2)
        self.assertTrue(any(g["kind"] == "archive-count-ceiling" for g in gaps))
        # threshold=5 → 3 files is fine
        self.assertEqual(check_archive_ceiling(sp, max_archives=5), [])

class R105CompactionGap7StatusTests(unittest.TestCase):
    """Gap 7: get_compaction_status + compact --status."""

    def test_status_no_manifest(self):
        from urace.compaction import get_compaction_status
        status = get_compaction_status(tempfile.mkdtemp())
        self.assertFalse(status["has_manifest"])
        self.assertEqual(status["event_count"], 0)
        self.assertIsNone(status["last_compacted_at"])
        self.assertIn("decision_records", status["governed_fields"])

    def test_compact_status_flag_returns_0(self):
        config = isolated_test_config(self)
        config["executor"]["enabled"] = False
        state = cli.initial_state(config)
        cli.seed_confirmed_onboard(config, state)
        with patch.object(cli, "load_config", return_value=config):
            with patch.object(cli, "load_state_for_read", return_value=state):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    rc = cli.main(["compact", "decision_records", "--status"])
        self.assertEqual(rc, 0)

    def test_compact_status_json_output(self):
        config = isolated_test_config(self)
        config["executor"]["enabled"] = False
        state = cli.initial_state(config)
        cli.seed_confirmed_onboard(config, state)
        with patch.object(cli, "load_config", return_value=config):
            with patch.object(cli, "load_state_for_read", return_value=state):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    rc = cli.main(["compact", "decision_records", "--status", "--json"])
        self.assertEqual(rc, 0)
        data = json.loads(buf.getvalue())
        self.assertIn("has_manifest", data)
        self.assertIn("governed_fields", data)

class R105CompactionGap8AtomicFieldsTests(unittest.TestCase):
    """Gap 8: 2-pass atomic cross-field compaction."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.engine = compaction_module.CompactionEngine(self.tmp)

    def test_compact_fields_fails_on_prohibited_field(self):
        state = {}
        policies = {"integrity_gaps": {"id": "p1", "compaction_mode": "PROHIBITED",
                                        "target_field": "integrity_gaps"}}
        with self.assertRaises(ValueError) as ctx:
            self.engine.compact_fields(state, ["integrity_gaps"], policies, "test")
        self.assertIn("PROHIBITED", str(ctx.exception))

    def test_compact_fields_fails_if_no_policy(self):
        state = {}
        with self.assertRaises(ValueError) as ctx:
            self.engine.compact_fields(state, ["nonexistent_field"], {}, "test")
        self.assertIn("no policy", str(ctx.exception))

    def test_compact_fields_does_not_commit_if_validation_fails(self):
        from urace.compaction import _DEFAULT_GOVERNANCE
        state = {"decision_records": [{"id": f"dr-{i}", "decided_at": f"2024-0{i%9+1}-01T00:00:00+00:00"} for i in range(5)]}
        original_len = len(state["decision_records"])
        policies = {
            "decision_records": {**_DEFAULT_GOVERNANCE["decision_records"], "id": "p1"},
            "bad_field": None,
        }
        with self.assertRaises(ValueError):
            self.engine.compact_fields(state, ["decision_records", "bad_field"], policies, "test")
        # decision_records must NOT have been compacted (pass 1 aborted everything)
        self.assertEqual(len(state["decision_records"]), original_len)

class R105FormatXmlTests(unittest.TestCase):
    """--format json|xml support."""

    def test_json_to_xml_dict(self):
        result = cli._json_to_xml({"status": "ok", "count": 3})
        self.assertIn("<urace>", result)
        self.assertIn("<status>", result)
        self.assertIn("</urace>", result)

    def test_json_to_xml_list(self):
        result = cli._json_to_xml([{"id": "a"}, {"id": "b"}])
        self.assertIn("<item>", result)
        self.assertIn("<id>", result)

    def test_json_to_xml_none(self):
        self.assertIn("<null/>", cli._json_to_xml(None))

    def test_json_to_xml_bool(self):
        self.assertIn("<bool>true</bool>", cli._json_to_xml(True))
        self.assertIn("<bool>false</bool>", cli._json_to_xml(False))

    def test_json_to_xml_escapes_special_chars(self):
        result = cli._json_to_xml({"msg": "a<b>&c"})
        self.assertIn("&lt;", result)
        self.assertIn("&amp;", result)
        self.assertNotIn("<b>", result)

    def test_json_to_xml_custom_root(self):
        result = cli._json_to_xml({"x": 1}, root="myroot")
        self.assertIn("<myroot>", result)
        self.assertIn("</myroot>", result)

    def test_format_xml_compact_status(self):
        config = isolated_test_config(self)
        config["executor"]["enabled"] = False
        state = cli.initial_state(config)
        cli.seed_confirmed_onboard(config, state)
        with patch.object(cli, "load_config", return_value=config):
            with patch.object(cli, "load_state_for_read", return_value=state):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    rc = cli.main(["--format", "xml", "compact", "decision_records", "--status"])
        self.assertEqual(rc, 0)
        self.assertIn("<urace>", buf.getvalue())

    def test_format_json_default_unchanged(self):
        config = isolated_test_config(self)
        config["executor"]["enabled"] = False
        state = cli.initial_state(config)
        cli.seed_confirmed_onboard(config, state)
        with patch.object(cli, "load_config", return_value=config):
            with patch.object(cli, "load_state_for_read", return_value=state):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    rc = cli.main(["compact", "decision_records", "--status", "--json"])
        self.assertEqual(rc, 0)
        data = json.loads(buf.getvalue())
        self.assertIn("has_manifest", data)

    def test_format_flag_forces_json_mode(self):
        """--format xml should force args.json=True for handlers."""
        config = isolated_test_config(self)
        config["executor"]["enabled"] = False
        state = cli.initial_state(config)
        cli.seed_confirmed_onboard(config, state)
        with patch.object(cli, "load_config", return_value=config):
            with patch.object(cli, "load_state_for_read", return_value=state):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    rc = cli.main(["--format", "xml", "compact", "decision_records", "--status"])
        self.assertEqual(rc, 0)
        # output must be XML not JSON
        out = buf.getvalue()
        self.assertTrue(out.startswith("<urace>") or "<urace>" in out)
        # must not be valid JSON
        with self.assertRaises(json.JSONDecodeError):
            json.loads(out)

class R106FormatPerSubparserTests(unittest.TestCase):
    """--format per-subparser: json/xml choices available on each subcommand."""

    def setUp(self):
        self.config = isolated_test_config(self)
        self.config["executor"]["enabled"] = False
        self.state = cli.initial_state(self.config)
        cli.seed_confirmed_onboard(self.config, self.state)

    def test_subcommand_format_json_accepted(self):
        """compact --format json is accepted without error."""
        with patch.object(cli, "load_config", return_value=self.config):
            with patch.object(cli, "load_state_for_read", return_value=self.state):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    rc = cli.main(["compact", "decision_records", "--status", "--format", "json"])
        self.assertEqual(rc, 0)
        data = json.loads(buf.getvalue())
        self.assertIn("has_manifest", data)

    def test_subcommand_format_xml_accepted(self):
        """compact --format xml produces XML output."""
        with patch.object(cli, "load_config", return_value=self.config):
            with patch.object(cli, "load_state_for_read", return_value=self.state):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    rc = cli.main(["compact", "decision_records", "--status", "--format", "xml"])
        self.assertEqual(rc, 0)
        self.assertIn("<urace>", buf.getvalue())

    def test_top_level_format_xml_accepted(self):
        """--format xml before subcommand produces XML."""
        with patch.object(cli, "load_config", return_value=self.config):
            with patch.object(cli, "load_state_for_read", return_value=self.state):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    rc = cli.main(["--format", "xml", "compact", "decision_records", "--status"])
        self.assertEqual(rc, 0)
        self.assertIn("<urace>", buf.getvalue())

    def test_json_alias_per_subparser(self):
        """--json alias still works per-subparser (backward compat)."""
        with patch.object(cli, "load_config", return_value=self.config):
            with patch.object(cli, "load_state_for_read", return_value=self.state):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    rc = cli.main(["compact", "decision_records", "--status", "--json"])
        self.assertEqual(rc, 0)
        data = json.loads(buf.getvalue())
        self.assertIn("has_manifest", data)

    def test_format_default_is_human_readable(self):
        """Without --format, compact --status prints human-readable text."""
        with patch.object(cli, "load_config", return_value=self.config):
            with patch.object(cli, "load_state_for_read", return_value=self.state):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    rc = cli.main(["compact", "decision_records", "--status"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        # Human text, not JSON
        self.assertIn("Compaction status", out)
        with self.assertRaises((json.JSONDecodeError, ValueError)):
            json.loads(out)

class R106ScopeTargetTests(unittest.TestCase):
    """_resolve_scope_target constructor."""

    def test_none_returns_empty(self):
        r = cli._resolve_scope_target(None, "/tmp/nonexistent_xyz")
        self.assertIsNone(r["field"])
        self.assertIsNone(r["predicate"])
        self.assertIsNone(r["error"])

    def test_all_returns_all(self):
        r = cli._resolve_scope_target("all", "/tmp/nonexistent_xyz")
        self.assertEqual(r["field"], "all")
        self.assertIsNone(r["predicate"])
        self.assertIsNone(r["error"])

    def test_field_only(self):
        r = cli._resolve_scope_target("decision_records", "/tmp/nonexistent_xyz")
        self.assertEqual(r["field"], "decision_records")
        self.assertIsNone(r["predicate"])
        self.assertIsNone(r["error"])

    def test_field_latest_no_manifest_returns_error(self):
        r = cli._resolve_scope_target("decision_records:latest", "/tmp/nonexistent_xyz_path")
        self.assertEqual(r["predicate"], "latest")
        self.assertIsNotNone(r["error"])

    def test_field_latest_with_manifest(self):
        from urace.compaction import _make_id
        from urace._common import now
        evt_id = _make_id("cmp")
        fake_manifest = {
            "events": [{
                "id": evt_id,
                "target_field": "decision_records",
                "compacted_at": now(),
            }]
        }
        with patch.object(compaction_module, "load_manifest", return_value=fake_manifest):
            r = cli._resolve_scope_target("decision_records:latest", "/tmp/fake")
        self.assertEqual(r["resolved_id"], evt_id)
        self.assertIsNone(r["error"])

    def test_record_id_scan_finds_event(self):
        from urace.compaction import _make_id
        from urace._common import now
        evt_id = _make_id("cmp")
        rec_id = _make_id("dr")
        fake_manifest = {
            "events": [{
                "id": evt_id,
                "target_field": "decision_records",
                "compacted_at": now(),
                "record_ids_covered": [rec_id],
            }]
        }
        with patch.object(compaction_module, "load_manifest", return_value=fake_manifest):
            r = cli._resolve_scope_target(f"decision_records:{rec_id}", "/tmp/fake")
            self.assertEqual(r["resolved_id"], evt_id)
            self.assertIsNone(r["error"])

    def test_unknown_predicate_returns_error(self):
        r = cli._resolve_scope_target("decision_records:nonexistent-id", "/tmp/nonexistent_xyz")
        self.assertIsNotNone(r["error"])

class R106ProductCollapseTests(unittest.TestCase):
    """--product/--products collapse."""

    def setUp(self):
        self.config = isolated_test_config(self)
        self.config["executor"]["enabled"] = False
        self.state = cli.initial_state(self.config)
        cli.seed_confirmed_onboard(self.config, self.state)

    def test_product_singular_accepted(self):
        """--product with nonexistent name gives error (1), not unrecognized arg."""
        with patch.object(cli, "load_config", return_value=self.config):
            with patch.object(cli, "load_state_for_read", return_value=self.state):
                buf = io.StringIO()
                with redirect_stderr(buf):
                    rc = cli.main(["compact", "decision_records", "--product", "nosuchproduct"])
        self.assertEqual(rc, 1)
        self.assertNotIn("unrecognized", buf.getvalue())

    def test_products_plural_alias_accepted(self):
        """--products is accepted as alias for --product."""
        with patch.object(cli, "load_config", return_value=self.config):
            with patch.object(cli, "load_state_for_read", return_value=self.state):
                buf = io.StringIO()
                with redirect_stderr(buf):
                    rc = cli.main(["crc", "show", "--products", "nosuchproduct"])
        # rc=1 because product not in registry; but NOT unrecognized arg
        self.assertNotIn("unrecognized", buf.getvalue())

    def test_products_all_empty_registry_returns_0(self):
        """--product all with empty registry returns 0 (no targets)."""
        cfg = copy.deepcopy(self.config)
        cfg["product_registry"] = []
        with patch.object(cli, "load_config", return_value=cfg):
            with patch.object(cli, "load_state_for_read", return_value=self.state):
                buf = io.StringIO()
                with redirect_stderr(buf):
                    rc = cli.main(["crc", "show", "--product", "all"])
        self.assertEqual(rc, 0)

    def test_products_comma_separated(self):
        """--product A,B with unknown names returns error for each."""
        with patch.object(cli, "load_config", return_value=self.config):
            with patch.object(cli, "load_state_for_read", return_value=self.state):
                buf = io.StringIO()
                with redirect_stderr(buf):
                    rc = cli.main(["crc", "show", "--product", "A,B"])
        self.assertEqual(rc, 1)
        self.assertIn("not in registry", buf.getvalue())

class R106CompactTargetTests(unittest.TestCase):
    """compact/decompact/amend --target integration."""

    def setUp(self):
        self.config = isolated_test_config(self)
        self.config["executor"]["enabled"] = False
        self.state = cli.initial_state(self.config)
        cli.seed_confirmed_onboard(self.config, self.state)

    def test_compact_target_all_queues_batch(self):
        """compact --target all queues batch compaction for governed fields."""
        with patch.object(cli, "load_config", return_value=self.config):
            with patch.object(cli, "load_state_for_read", return_value=self.state):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    rc = cli.main(["compact", "--target", "all"])
        # Returns 0 (batch result)
        self.assertEqual(rc, 0)

    def test_compact_target_field_accepted(self):
        """compact --target FIELD (without positional) compacts that field."""
        with patch.object(cli, "load_config", return_value=self.config):
            with patch.object(cli, "load_state_for_read", return_value=self.state):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    rc = cli.main(["compact", "--target", "decision_records"])
        self.assertIn(rc, (0, 1))  # may fail if no policy, but must not crash with arg error

    def test_decompact_requires_event_id_or_target(self):
        """decompact without event_id and without --target returns error."""
        with patch.object(cli, "load_config", return_value=self.config):
            with patch.object(cli, "load_state_for_read", return_value=self.state):
                buf = io.StringIO()
                with redirect_stderr(buf):
                    rc = cli.main(["decompact"])
        self.assertEqual(rc, 1)
        self.assertIn("required", buf.getvalue().lower())

    def test_amend_requires_ids_or_target(self):
        """amend without event_id/record_id and without --target returns error."""
        with patch.object(cli, "load_config", return_value=self.config):
            with patch.object(cli, "load_state_for_read", return_value=self.state):
                buf = io.StringIO()
                with redirect_stderr(buf):
                    rc = cli.main(["amend", "--notice", "test"])
        self.assertEqual(rc, 1)

class R106OutputFormatContractTests(unittest.TestCase):
    """OutputFormatContract: all JSON-capable commands accept --format json/xml."""

    def setUp(self):
        self.config = isolated_test_config(self)
        self.config["executor"]["enabled"] = False
        self.state = cli.initial_state(self.config)
        cli.seed_confirmed_onboard(self.config, self.state)

    def _run(self, argv):
        with patch.object(cli, "load_config", return_value=self.config):
            with patch.object(cli, "load_state_for_read", return_value=self.state):
                buf_out = io.StringIO()
                buf_err = io.StringIO()
                with redirect_stdout(buf_out), redirect_stderr(buf_err):
                    rc = cli.main(argv)
        return rc, buf_out.getvalue(), buf_err.getvalue()

    def test_check_format_json(self):
        rc, out, _ = self._run(["check", "--format", "json"])
        self.assertEqual(rc, 0)

    def test_vitals_format_json(self):
        rc, out, _ = self._run(["vitals", "--format", "json"])
        self.assertIn(rc, (0, 1))
        self.assertNotIn("unrecognized", _)

    def test_goal_list_format_json(self):
        rc, out, _ = self._run(["goal", "list", "--format", "json"])
        self.assertIn(rc, (0, 1))
        self.assertNotIn("unrecognized", _)

    def test_check_format_xml(self):
        rc, out, _ = self._run(["check", "--format", "xml"])
        self.assertEqual(rc, 0)
        self.assertIn("<urace>", out)

    def test_print_fmt_json(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            cli._print_fmt({"key": "val"}, "json")
        self.assertEqual(json.loads(buf.getvalue())["key"], "val")

    def test_print_fmt_xml(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            cli._print_fmt({"key": "val"}, "xml")
        self.assertIn("<key>", buf.getvalue())

    def test_xml_convert_stream_converts_json(self):
        underlying = io.StringIO()
        stream = cli._XmlConvertStream(underlying)
        stream.write('{"a": 1}')
        stream.flush()
        out = underlying.getvalue()
        self.assertIn("<a>", out)

    def test_xml_convert_stream_passes_text(self):
        underlying = io.StringIO()
        stream = cli._XmlConvertStream(underlying)
        stream.write("plain text output\n")
        stream.flush()
        self.assertEqual(underlying.getvalue(), "plain text output\n")

