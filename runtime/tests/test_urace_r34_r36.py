import copy
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from urace import cli, cli_helpers as _cli_helpers_m

TEST_RUNTIME_ROOT = Path(__file__).resolve().parents[1]
TEST_PRODUCT_ROOT = Path(__file__).resolve().parents[3]


def isolated_test_config(test_case):
    """Keep lifecycle writes away from the configured installation state."""
    config = copy.deepcopy(cli.load_config())
    directory = tempfile.TemporaryDirectory(prefix='urace-test-state-')
    test_case.addCleanup(directory.cleanup)
    config['state_path'] = str(Path(directory.name) / 'state.json')
    return config


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
        config.pop("product_files", None)
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
        config.pop("product_files", None)
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
        config.pop("product_files", None)
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

