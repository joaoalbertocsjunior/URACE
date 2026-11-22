import copy
import io
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from urace import cli, compaction as compaction_module

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
                 patch("urace.cli.commands.product.save_config", side_effect=fake_save_config), \
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
                 patch("urace.cli.commands.product.save_config", side_effect=fake_save_config), \
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
                 patch("urace.cli.commands.product.save_config", side_effect=fake_save_config), \
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
                 patch("urace.cli.commands.product.save_config", lambda c: None), \
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
                 patch("urace.cli.commands.product.save_config", side_effect=lambda c: captured_config.update(c)), \
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
