import copy
import hashlib
import io
import json
import os
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
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


class R37AdditionsTests(unittest.TestCase):
    """r37: Safety schemas, AssessmentRecord, DiscoveryRecord, OwnershipMarker, MarketSignal, FitHypothesis"""

    # initial_state fields
    def test_r37_initial_state_has_policy_records(self):
        _cfg = isolated_test_config(self)
        s = cli.initial_state(_cfg)
        self.assertIn("policy_records", s)
        self.assertEqual(s["policy_records"], [])

    def test_r37_initial_state_has_hard_constraints(self):
        _cfg = isolated_test_config(self)
        s = cli.initial_state(_cfg)
        self.assertIn("hard_constraints", s)

    def test_r37_initial_state_has_assessment_records(self):
        _cfg = isolated_test_config(self)
        s = cli.initial_state(_cfg)
        self.assertIn("assessment_records", s)

    def test_r37_initial_state_has_discovery_records(self):
        _cfg = isolated_test_config(self)
        s = cli.initial_state(_cfg)
        self.assertIn("discovery_records", s)

    def test_r37_initial_state_has_ownership_markers(self):
        _cfg = isolated_test_config(self)
        s = cli.initial_state(_cfg)
        self.assertIn("ownership_markers", s)

    def test_r37_initial_state_has_market_signals(self):
        _cfg = isolated_test_config(self)
        s = cli.initial_state(_cfg)
        self.assertIn("market_signals", s)

    def test_r37_initial_state_has_fit_hypotheses(self):
        _cfg = isolated_test_config(self)
        s = cli.initial_state(_cfg)
        self.assertIn("fit_hypotheses", s)

    # PolicyRecord validator
    def test_r37_policy_record_valid(self):
        from urace import primitives as prim
        rec = {
            "id": "pol-abc12345",
            "kind": "PROHIBITION",
            "status": "ACTIVE",
            "description": "No external writes without approval",
            "scope": "*",
            "enforcement": "HARD",
            "authority_basis": "auth-001",
            "established_at": "2026-10-14T00:00:00Z",
        }
        prim.validate("PolicyRecord", rec)

    def test_r37_policy_record_bad_prefix(self):
        from urace import primitives as prim
        rec = {
            "id": "bad-abc12345",
            "kind": "PROHIBITION",
            "status": "ACTIVE",
            "description": "test",
            "scope": "*",
            "enforcement": "HARD",
            "authority_basis": "auth-001",
            "established_at": "2026-10-14T00:00:00Z",
        }
        with self.assertRaises(ValueError):
            prim.validate("PolicyRecord", rec)

    def test_r37_policy_record_bad_kind(self):
        from urace import primitives as prim
        rec = {
            "id": "pol-abc12345",
            "kind": "UNKNOWN",
            "status": "ACTIVE",
            "description": "test",
            "scope": "*",
            "enforcement": "HARD",
            "authority_basis": "auth-001",
            "established_at": "2026-10-14T00:00:00Z",
        }
        with self.assertRaises(ValueError):
            prim.validate("PolicyRecord", rec)

    def test_r37_policy_record_soft_enforcement(self):
        from urace import primitives as prim
        rec = {
            "id": "pol-abc12345",
            "kind": "BUDGET",
            "status": "ACTIVE",
            "description": "Prefer low-cost routes",
            "scope": "execution",
            "enforcement": "SOFT",
            "authority_basis": "auth-001",
            "established_at": "2026-10-14T00:00:00Z",
        }
        prim.validate("PolicyRecord", rec)

    # HardConstraint validator
    def test_r37_hard_constraint_valid(self):
        from urace import primitives as prim
        hc = {
            "id": "hco-abc12345",
            "description": "Never delete accepted checkpoints",
            "scope": "state",
            "established_at": "2026-10-14T00:00:00Z",
            "authority_basis": "auth-001",
        }
        prim.validate("HardConstraint", hc)

    def test_r37_hard_constraint_bad_prefix(self):
        from urace import primitives as prim
        hc = {
            "id": "bad-abc12345",
            "description": "test",
            "scope": "*",
            "established_at": "2026-10-14T00:00:00Z",
            "authority_basis": "auth-001",
        }
        with self.assertRaises(ValueError):
            prim.validate("HardConstraint", hc)

    # AssessmentRecord validator
    def test_r37_assessment_record_valid(self):
        from urace import primitives as prim
        rec = {
            "id": "asr-abc12345",
            "assessed_at": "2026-10-14T00:00:00Z",
            "lifecycle_phase": "planning",
            "authority_ids": ["auth-001"],
            "intent_id": "int-001",
            "cycle_status": "COMPLETE",
        }
        prim.validate("AssessmentRecord", rec)

    def test_r37_assessment_record_bad_cycle_status(self):
        from urace import primitives as prim
        rec = {
            "id": "asr-abc12345",
            "assessed_at": "2026-10-14T00:00:00Z",
            "lifecycle_phase": "planning",
            "authority_ids": [],
            "intent_id": "int-001",
            "cycle_status": "INVALID",
        }
        with self.assertRaises(ValueError):
            prim.validate("AssessmentRecord", rec)

    # DiscoveryRecord validator
    def test_r37_discovery_record_valid(self):
        from urace import primitives as prim
        rec = {
            "id": "dsc-abc12345",
            "cycle_id": "cyc-001",
            "started_at": "2026-10-14T00:00:00Z",
            "cycle_status": "COMPLETE",
            "categories_evaluated": ["goals", "triggers"],
            "candidates_found": 3,
            "candidates_rejected": 1,
        }
        prim.validate("DiscoveryRecord", rec)

    def test_r37_discovery_record_negative_candidates(self):
        from urace import primitives as prim
        rec = {
            "id": "dsc-abc12345",
            "cycle_id": "cyc-001",
            "started_at": "2026-10-14T00:00:00Z",
            "cycle_status": "COMPLETE",
            "categories_evaluated": [],
            "candidates_found": -1,
            "candidates_rejected": 0,
        }
        with self.assertRaises(ValueError):
            prim.validate("DiscoveryRecord", rec)

    # OwnershipMarker validator
    def test_r37_ownership_marker_valid(self):
        from urace import primitives as prim
        omk = {
            "id": "omk-abc12345",
            "owner_id": "runtime-1",
            "scope": "lifecycle",
            "acquired_at": "2026-10-14T00:00:00Z",
            "status": "HELD",
        }
        prim.validate("OwnershipMarker", omk)

    def test_r37_ownership_marker_bad_status(self):
        from urace import primitives as prim
        omk = {
            "id": "omk-abc12345",
            "owner_id": "runtime-1",
            "scope": "lifecycle",
            "acquired_at": "2026-10-14T00:00:00Z",
            "status": "UNKNOWN",
        }
        with self.assertRaises(ValueError):
            prim.validate("OwnershipMarker", omk)

    # MarketSignal validator
    def test_r37_market_signal_valid(self):
        from urace import primitives as prim
        sig = {
            "id": "mks-abc12345",
            "kind": "USER_FEEDBACK",
            "observed_at": "2026-10-14T00:00:00Z",
            "source": "user-interview",
            "description": "Users find onboarding confusing",
            "confidence": "MODERATE",
            "intent_id": "int-001",
        }
        prim.validate("MarketSignal", sig)

    def test_r37_market_signal_bad_confidence(self):
        from urace import primitives as prim
        sig = {
            "id": "mks-abc12345",
            "kind": "USER_FEEDBACK",
            "observed_at": "2026-10-14T00:00:00Z",
            "source": "interview",
            "description": "test",
            "confidence": "HIGH",
            "intent_id": "int-001",
        }
        with self.assertRaises(ValueError):
            prim.validate("MarketSignal", sig)

    # FitHypothesis validator
    def test_r37_fit_hypothesis_valid(self):
        from urace import primitives as prim
        hyp = {
            "id": "fhy-abc12345",
            "description": "Simplifying onboarding reduces churn by 10%",
            "intent_id": "int-001",
            "status": "ACTIVE",
            "confidence": "WEAK",
            "created_at": "2026-10-14T00:00:00Z",
            "last_updated_at": "2026-10-14T00:00:00Z",
        }
        prim.validate("FitHypothesis", hyp)

    def test_r37_fit_hypothesis_bad_status(self):
        from urace import primitives as prim
        hyp = {
            "id": "fhy-abc12345",
            "description": "test",
            "intent_id": "int-001",
            "status": "UNKNOWN",
            "confidence": "WEAK",
            "created_at": "2026-10-14T00:00:00Z",
            "last_updated_at": "2026-10-14T00:00:00Z",
        }
        with self.assertRaises(ValueError):
            prim.validate("FitHypothesis", hyp)


class R38AdditionsTests(unittest.TestCase):
    """r38: Shared Reuse Contracts — IntegrityGapCatalog, EffectUncertaintyProtocol, OperatorGateProtocol, GoverningRecord, RevalidationScope, PatternMechanismMapping"""

    def test_r38_integrity_gap_catalog_exists(self):
        from urace import primitives as prim
        self.assertIsInstance(prim.INTEGRITY_GAP_CATALOG, dict)
        self.assertGreater(len(prim.INTEGRITY_GAP_CATALOG), 15)

    def test_r38_integrity_gap_catalog_known_kinds(self):
        from urace import primitives as prim
        for kind in (
            "progress-stagnation", "derived-manifest-stale", "cognitive-resume-stale",
            "compaction-manifest-divergence", "capability-envelope-breach",
            "pattern-capability-gap", "no-hard-constraints-declared",
            "over-engineered", "regression-checkpoint-pending",
            "stale-decision-revalidation", "retention-policy-violated",
            "wake-registration-missing-fields", "wake-registration-unverified",
            "indeterminate-effect-unresolvable", "operator-gate-open",
        ):
            self.assertIn(kind, prim.INTEGRITY_GAP_CATALOG, f"Missing kind: {kind}")

    def test_r38_integrity_gap_catalog_severity_values(self):
        from urace import primitives as prim
        # INFO was added as a valid severity tier in r50 (§62l IntegrityGapCatalog extension)
        valid_severities = {"BLOCKING", "WARNING", "INFO"}
        for kind, entry in prim.INTEGRITY_GAP_CATALOG.items():
            self.assertIn(entry["severity"], valid_severities, f"Bad severity for {kind}")

    def test_r38_is_known_gap_kind_true(self):
        from urace import primitives as prim
        self.assertTrue(prim.is_known_gap_kind("progress-stagnation"))

    def test_r38_is_known_gap_kind_false(self):
        from urace import primitives as prim
        self.assertFalse(prim.is_known_gap_kind("made-up-gap"))

    def test_r38_gap_severity_blocking(self):
        from urace import primitives as prim
        self.assertEqual(prim.gap_severity("compaction-manifest-divergence"), "BLOCKING")

    def test_r38_gap_severity_warning(self):
        from urace import primitives as prim
        self.assertEqual(prim.gap_severity("derived-manifest-stale"), "WARNING")

    def test_r38_gap_severity_unknown_returns_none(self):
        from urace import primitives as prim
        self.assertIsNone(prim.gap_severity("not-a-real-gap"))

    def test_r38_revalidation_scope_valid_values(self):
        from urace import primitives as prim
        for scope in ("DECISION_ONLY", "DEPENDENT_PLANS", "FULL_LIFECYCLE"):
            prim.validate_revalidation_scope(scope)  # should not raise

    def test_r38_revalidation_scope_invalid(self):
        from urace import primitives as prim
        with self.assertRaises(ValueError):
            prim.validate_revalidation_scope("EVERYTHING")

    def test_r38_check_governing_record_fields_valid(self):
        from urace import primitives as prim
        rec = {
            "id": "pol-abc12345",
            "authority_basis": "auth-001",
            "scope": "*",
            "established_at": "2026-10-14T00:00:00Z",
        }
        prim.check_governing_record_fields(rec, "PolicyRecord")  # should not raise

    def test_r38_check_governing_record_fields_missing(self):
        from urace import primitives as prim
        rec = {
            "id": "pol-abc12345",
            "scope": "*",
            "established_at": "2026-10-14T00:00:00Z",
            # missing authority_basis
        }
        with self.assertRaises(ValueError):
            prim.check_governing_record_fields(rec, "PolicyRecord")

    def test_r38_check_governing_record_fields_empty_authority(self):
        from urace import primitives as prim
        rec = {
            "id": "pol-abc12345",
            "authority_basis": "",
            "scope": "*",
            "established_at": "2026-10-14T00:00:00Z",
        }
        with self.assertRaises(ValueError):
            prim.check_governing_record_fields(rec, "PolicyRecord")

    def test_r38_policy_record_uses_governing_record_fields(self):
        from urace import primitives as prim
        rec = {
            "id": "pol-abc12345",
            "kind": "PROHIBITION",
            "status": "ACTIVE",
            "description": "No external writes without approval",
            "scope": "*",
            "enforcement": "HARD",
            "authority_basis": "auth-001",
            "established_at": "2026-10-14T00:00:00Z",
        }
        prim.validate("PolicyRecord", rec)
        # Also verify governing record fields pass the shared check
        prim.check_governing_record_fields(rec, "PolicyRecord")


class R39AdditionsTests(unittest.TestCase):
    """r39: Shared reuse constructs wired into runtime — _emit_gap, InspectionSurface, GoverningRecord,
    TemporalFields enforcement, PatternMechanismMap, RevalidationScope, AuthorityClosureInvariant."""

    def _make_state(self):
        from urace import cli as _cli
        import copy
        cfg = isolated_test_config(self)
        return copy.deepcopy(_cli.initial_state(cfg))

    def _cfg(self):
        return {
            "authority": {
                "delegated": ["assessment", "objectives", "priority", "plans",
                              "local implementation changes",
                              "urace.md specification evolution within the retained purpose, authority boundaries, and normative invariants"],
                "reserved": [],
            },
            "constraints": [],
        }

    # --- _emit_gap ---

    def test_emit_gap_appends_to_integrity_gaps(self):
        from urace.cli import _emit_gap
        state = self._make_state()
        _emit_gap(state, "progress-stagnation", "BLOCKING", "stagnant 5 cycles")
        gaps = state.get("integrity_gaps", [])
        self.assertTrue(any(g["kind"] == "progress-stagnation" for g in gaps))

    def test_emit_gap_uses_catalog_severity(self):
        from urace.cli import _emit_gap
        from urace.primitives import gap_severity
        state = self._make_state()
        _emit_gap(state, "progress-stagnation", "INFO", "detail")
        g = next(g for g in state["integrity_gaps"] if g["kind"] == "progress-stagnation")
        self.assertEqual(g["severity"], gap_severity("progress-stagnation"))

    def test_emit_gap_unknown_kind_emits_meta_gap(self):
        from urace.cli import _emit_gap
        state = self._make_state()
        _emit_gap(state, "not-a-real-kind", "WARNING", "detail")
        kinds = [g["kind"] for g in state.get("integrity_gaps", [])]
        self.assertIn("unknown-gap-kind", kinds)

    def test_emit_gap_has_id_and_resolved(self):
        from urace.cli import _emit_gap
        state = self._make_state()
        _emit_gap(state, "over-engineered", "WARNING", "surface exceeds ceiling")
        g = next(g for g in state["integrity_gaps"] if g["kind"] == "over-engineered")
        self.assertIn("id", g)
        self.assertFalse(g["resolved"])

    # --- _apply_effect_uncertainty_protocol ---

    def test_effect_uncertainty_adds_unresolved_effect(self):
        from urace.cli import _apply_effect_uncertainty_protocol
        state = self._make_state()
        _apply_effect_uncertainty_protocol(state, "eff-001", "op-001", "network drop")
        self.assertTrue(any(e["id"] == "eff-001" for e in state.get("unresolved_effects", [])))

    def test_effect_uncertainty_emits_gap(self):
        from urace.cli import _apply_effect_uncertainty_protocol
        state = self._make_state()
        _apply_effect_uncertainty_protocol(state, "eff-002", "op-002", "timeout")
        gaps = state.get("integrity_gaps", [])
        self.assertTrue(any(g["kind"] == "indeterminate-effect-unresolvable" for g in gaps))

    def test_effect_uncertainty_no_duplicate_effect(self):
        from urace.cli import _apply_effect_uncertainty_protocol
        state = self._make_state()
        _apply_effect_uncertainty_protocol(state, "eff-dup", "op-x", "first")
        _apply_effect_uncertainty_protocol(state, "eff-dup", "op-x", "second")
        eff_ids = [e["id"] for e in state.get("unresolved_effects", [])]
        self.assertEqual(eff_ids.count("eff-dup"), 1)

    # --- _apply_operator_gate ---

    def test_operator_gate_emits_blocking_gap(self):
        from urace.cli import _apply_operator_gate
        state = self._make_state()
        _apply_operator_gate(state, "MANUAL_CLEARANCE_REQUIRED", "operator must confirm", scope="deploy")
        gaps = state.get("integrity_gaps", [])
        self.assertTrue(any(g["kind"] == "operator-gate-open" and g["severity"] == "BLOCKING" for g in gaps))

    # --- _build_inspection_surface ---

    def test_build_inspection_surface_has_required_keys(self):
        from urace.cli import _build_inspection_surface
        state = self._make_state()
        surface = _build_inspection_surface(state, self._cfg())
        required = {
            "lifecycle_state", "assessed_at", "blocking_gaps", "warning_gaps",
            "indeterminate_effects", "operator_gates", "stale_items",
            "capability_readiness", "scheduled_conditions",
            "policy_violations", "open_pending_validations", "summary",
        }
        self.assertEqual(required - surface.keys(), set())

    def test_build_inspection_surface_blocking_gap_filter(self):
        from urace.cli import _build_inspection_surface, _emit_gap
        state = self._make_state()
        _emit_gap(state, "progress-stagnation", "BLOCKING", "stagnant")
        surface = _build_inspection_surface(state, self._cfg())
        self.assertTrue(len(surface["blocking_gaps"]) >= 1)
        self.assertEqual(surface["warning_gaps"], [g for g in state.get("integrity_gaps", []) if g.get("severity") == "WARNING" and not g.get("resolved")])

    # --- GoverningRecord enforcement ---

    def test_governing_record_fields_rejects_missing_authority_basis(self):
        from urace.primitives import validate_policy_record
        with self.assertRaises(ValueError):
            validate_policy_record({
                "id": "pol-1", "scope": "runtime", "established_at": "2026-01-01T00:00:00Z",
                "kind": "QUALITY_GATE", "status": "ACTIVE",
                "name": "p", "description": "d", "conditions": [], "actions": [],
            })

    # --- TemporalFields enforcement ---

    def test_temporal_fields_rejects_empty_established_at(self):
        from urace.primitives import validate_policy_record
        with self.assertRaises(ValueError):
            validate_policy_record({
                "id": "pol-2", "authority_basis": "spec §72", "scope": "runtime",
                "established_at": "",
                "kind": "QUALITY_GATE", "status": "ACTIVE",
                "name": "p", "description": "d", "conditions": [], "actions": [],
            })

    # --- PatternMechanismMapping ---

    def test_pattern_mechanism_map_has_ap0_to_ap25(self):
        from urace.patterns import PATTERN_MECHANISM_MAP
        for i in range(26):
            self.assertIn(f"AP{i}", PATTERN_MECHANISM_MAP, f"AP{i} missing from PATTERN_MECHANISM_MAP")

    def test_pattern_mechanism_map_has_required_keys(self):
        from urace.patterns import PATTERN_MECHANISM_MAP
        for ap, entry in PATTERN_MECHANISM_MAP.items():
            self.assertIn("sections", entry, f"{ap} missing 'sections'")
            self.assertIn("key_provides", entry, f"{ap} missing 'key_provides'")

    # --- RevalidationScope ---

    def test_determine_revalidation_scope_known_triggers(self):
        from urace.primitives import determine_revalidation_scope
        self.assertEqual(determine_revalidation_scope("evidence-retracted"), "DECISION_ONLY")
        self.assertEqual(determine_revalidation_scope("authority-revoked"), "DEPENDENT_PLANS")
        self.assertEqual(determine_revalidation_scope("intent-replaced"), "FULL_LIFECYCLE")

    def test_determine_revalidation_scope_unknown_defaults_full_lifecycle(self):
        from urace.primitives import determine_revalidation_scope
        self.assertEqual(determine_revalidation_scope("unknown-change-class"), "FULL_LIFECYCLE")

    # --- AuthorityClosureInvariant ---

    def test_authority_closure_blocks_non_authority_sources(self):
        from urace.primitives import check_authority_closure
        for src in ["evidence", "priority", "market_signal", "trigger", "schedule"]:
            self.assertFalse(check_authority_closure(src), f"{src} should not pass closure check")

    def test_authority_closure_passes_authority_source(self):
        from urace.primitives import check_authority_closure
        self.assertTrue(check_authority_closure("authority"))
        self.assertTrue(check_authority_closure("operator_decision"))


class R40AdditionsTests(unittest.TestCase):
    """r40: intent-first urace derive — suggest_patterns_from_intent, patterns_from_goals,
    --suggest, --from-goals, positional intent arg, complementary --patterns merge."""

    def setUp(self):
        self.config = isolated_test_config(self)
        self.state = cli.initial_state(self.config)
        cli.seed_confirmed_onboard(self.config, self.state)

    # --- suggest_patterns_from_intent ---

    def test_suggest_returns_list_for_known_intent(self):
        from urace.patterns import suggest_patterns_from_intent
        results = suggest_patterns_from_intent("resilient event log compaction")
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)

    def test_suggest_each_entry_has_required_keys(self):
        from urace.patterns import suggest_patterns_from_intent
        for entry in suggest_patterns_from_intent("log audit resilience"):
            self.assertIn("pattern_id", entry)
            self.assertIn("name", entry)
            self.assertIn("tier", entry)
            self.assertIn("score", entry)
            self.assertIn("summary", entry)

    def test_suggest_returns_empty_for_empty_intent(self):
        from urace.patterns import suggest_patterns_from_intent
        self.assertEqual(suggest_patterns_from_intent(""), [])

    def test_suggest_top_n_respected(self):
        from urace.patterns import suggest_patterns_from_intent
        results = suggest_patterns_from_intent("event log identity schema audit compaction schedule", top_n=3)
        self.assertLessEqual(len(results), 3)

    def test_suggest_compaction_intent_includes_ap21(self):
        from urace.patterns import suggest_patterns_from_intent
        ids = [e["pattern_id"] for e in suggest_patterns_from_intent("log compaction bounded growth", top_n=8)]
        self.assertIn("AP21", ids)

    def test_suggest_resilience_intent_includes_circuit_breaker(self):
        from urace.patterns import suggest_patterns_from_intent
        ids = [e["pattern_id"] for e in suggest_patterns_from_intent("resilient circuit breaker retry", top_n=8)]
        self.assertTrue(any(p in ids for p in ["AP10", "AP20"]))

    def test_suggest_scores_positive(self):
        from urace.patterns import suggest_patterns_from_intent
        for entry in suggest_patterns_from_intent("schedule orchestration"):
            self.assertGreater(entry["score"], 0)

    # --- patterns_from_goals ---

    def test_patterns_from_goals_returns_list(self):
        from urace.patterns import patterns_from_goals
        goals = [
            {"title": "build resilient event sourcing", "description": "log and replay events"},
            {"title": "add scheduled cleanup", "description": "compact logs on schedule"},
        ]
        results = patterns_from_goals(goals, top_n=6)
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)

    def test_patterns_from_goals_empty_returns_empty(self):
        from urace.patterns import patterns_from_goals
        self.assertEqual(patterns_from_goals([]), [])

    def test_patterns_from_goals_deduplicates(self):
        from urace.patterns import patterns_from_goals
        goals = [
            {"title": "log compaction", "description": ""},
            {"title": "log compaction archive", "description": ""},
        ]
        results = patterns_from_goals(goals, top_n=10)
        ids = [e["pattern_id"] for e in results]
        self.assertEqual(len(ids), len(set(ids)))

    # --- CLI: intent as positional arg ---

    def test_derive_intent_only_produces_manifest(self):
        out = io.StringIO()
        with patch.object(cli, "load_config", return_value=self.config), redirect_stdout(out):
            result = cli.main(["derive", "resilient log compaction"])
        self.assertEqual(result, 0)
        # --source runtime (default) --kind all: produces DerivedConstructSet (full-scope)
        text = out.getvalue()
        self.assertTrue("DerivedConstructSet" in text or "DerivedSystemManifest" in text)

    def test_derive_intent_only_prints_suggested_patterns(self):
        out = io.StringIO()
        with patch.object(cli, "load_config", return_value=self.config), redirect_stdout(out):
            cli.main(["derive", "log compaction archive"])
        # --kind all: suggests constructs across all kinds
        text = out.getvalue()
        self.assertTrue("Suggested patterns:" in text or "Suggested constructs" in text)

    def test_derive_intent_plus_patterns_merges(self):
        out = io.StringIO()
        with patch.object(cli, "load_config", return_value=self.config), redirect_stdout(out):
            result = cli.main(["derive", "log audit", "--patterns", "AP18"])
        self.assertEqual(result, 0)
        text = out.getvalue()
        self.assertTrue("DerivedConstructSet" in text or "DerivedSystemManifest" in text)

    def test_derive_suggest_flag_no_manifest(self):
        out = io.StringIO()
        with patch.object(cli, "load_config", return_value=self.config), redirect_stdout(out):
            result = cli.main(["derive", "log compaction", "--suggest"])
        self.assertEqual(result, 0)
        text = out.getvalue()
        self.assertNotIn("DerivedSystemManifest", text)
        self.assertTrue("Pattern suggestions" in text or "Construct suggestions" in text or "suggestions" in text.lower())

    def test_derive_suggest_flag_requires_intent(self):
        with self.assertRaises(SystemExit):
            cli.main(["derive", "--suggest"])

    def test_derive_no_args_shows_catalog(self):
        out = io.StringIO()
        with patch.object(cli, "load_config", return_value=self.config), redirect_stdout(out):
            result = cli.main(["derive"])
        self.assertEqual(result, 0)
        self.assertIn("Available URACE constructs", out.getvalue())
        self.assertIn("Tip:", out.getvalue())

    def test_derive_suggest_json_output(self):
        out = io.StringIO()
        with patch.object(cli, "load_config", return_value=self.config), redirect_stdout(out):
            cli.main(["derive", "resilient retry circuit", "--suggest", "--json"])
        data = json.loads(out.getvalue())
        self.assertIn("suggestions", data)
        self.assertIn("intent", data)


class R41AdditionsTests(unittest.TestCase):
    """r41: Extended construct catalogs — MECHANISM, SCHEMA, PROTOCOL, CONTRACT + CONSTRUCT_CATALOG,
    suggest_constructs_from_intent, build_derived_construct_set, --kind CLI flag, §62m spec section."""

    def setUp(self):
        self.config = isolated_test_config(self)
        self.state = cli.initial_state(self.config)
        cli.seed_confirmed_onboard(self.config, self.state)

    # --- Catalog completeness ---

    def test_mechanism_catalog_has_six_entries(self):
        from urace.patterns import MECHANISM_CATALOG
        self.assertEqual(len(MECHANISM_CATALOG), 6)
        for mid in ("QSM", "SSB", "CEG", "TAG", "DCG", "PSD"):
            self.assertIn(mid, MECHANISM_CATALOG)

    def test_schema_catalog_has_twenty_plus_entries(self):
        from urace.patterns import SCHEMA_CATALOG
        self.assertGreaterEqual(len(SCHEMA_CATALOG), 20)
        for sid in ("GoalRecord", "EvidenceRecord", "DecisionRecord", "PolicyRecord",
                    "HardConstraint", "QualityDelta", "IntegrityGap", "CapabilityStatement"):
            self.assertIn(sid, SCHEMA_CATALOG)

    def test_protocol_catalog_has_eup_and_ogp(self):
        from urace.patterns import PROTOCOL_CATALOG
        self.assertIn("EUP", PROTOCOL_CATALOG)
        self.assertIn("OGP", PROTOCOL_CATALOG)

    def test_contract_catalog_has_six_entries(self):
        from urace.patterns import CONTRACT_CATALOG
        for cid in ("GRC", "IGC", "ISC", "ACI", "RVS", "ABM"):
            self.assertIn(cid, CONTRACT_CATALOG)

    def test_construct_catalog_has_sixty_entries(self):
        from urace.patterns import CONSTRUCT_CATALOG
        self.assertGreaterEqual(len(CONSTRUCT_CATALOG), 60)

    def test_construct_catalog_all_have_kind(self):
        from urace.patterns import CONSTRUCT_CATALOG, ALL_KINDS
        for cid, entry in CONSTRUCT_CATALOG.items():
            self.assertIn(entry.get("kind"), ALL_KINDS, f"{cid} has invalid kind")

    def test_construct_catalog_patterns_preserved(self):
        from urace.patterns import CONSTRUCT_CATALOG, PATTERN_CATALOG
        for pid in PATTERN_CATALOG:
            self.assertIn(pid, CONSTRUCT_CATALOG)
            self.assertEqual(CONSTRUCT_CATALOG[pid]["kind"], "pattern")

    # --- suggest_constructs_from_intent ---

    def test_suggest_constructs_returns_list(self):
        from urace.patterns import suggest_constructs_from_intent
        results = suggest_constructs_from_intent("quality regression resilience")
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)

    def test_suggest_constructs_each_has_required_keys(self):
        from urace.patterns import suggest_constructs_from_intent
        for entry in suggest_constructs_from_intent("authority policy constraint"):
            for k in ("construct_id", "name", "kind", "score", "summary"):
                self.assertIn(k, entry)

    def test_suggest_constructs_kind_filter_mechanism(self):
        from urace.patterns import suggest_constructs_from_intent
        results = suggest_constructs_from_intent("quality regression stagnation", kinds={"mechanism"})
        for r in results:
            self.assertEqual(r["kind"], "mechanism")

    def test_suggest_constructs_kind_filter_schema(self):
        from urace.patterns import suggest_constructs_from_intent
        results = suggest_constructs_from_intent("goal evidence decision", kinds={"schema"})
        for r in results:
            self.assertEqual(r["kind"], "schema")

    def test_suggest_constructs_all_kinds_returns_mixed(self):
        from urace.patterns import suggest_constructs_from_intent, ALL_KINDS
        results = suggest_constructs_from_intent("authority policy quality evidence resilience", kinds=ALL_KINDS, top_n=12)
        kinds_found = {r["kind"] for r in results}
        self.assertGreater(len(kinds_found), 1)

    def test_suggest_constructs_quality_includes_qsm(self):
        from urace.patterns import suggest_constructs_from_intent
        results = suggest_constructs_from_intent("quality streak regression checkpoint", kinds={"mechanism"})
        ids = [r["construct_id"] for r in results]
        self.assertIn("QSM", ids)

    def test_suggest_constructs_authority_includes_abm(self):
        from urace.patterns import suggest_constructs_from_intent
        results = suggest_constructs_from_intent("authority boundary delegated reserved", kinds={"contract"})
        ids = [r["construct_id"] for r in results]
        self.assertIn("ABM", ids)

    # --- build_derived_construct_set ---

    def test_build_construct_set_valid(self):
        from urace.patterns import build_derived_construct_set
        cset = build_derived_construct_set(["QSM", "EvidenceRecord", "EUP"], "test", "r41")
        self.assertIn("construct_set_id", cset)
        self.assertTrue(cset["construct_set_id"].startswith("cset-"))
        self.assertEqual(len(cset["adopted_constructs"]), 3)

    def test_build_construct_set_kinds_present(self):
        from urace.patterns import build_derived_construct_set
        cset = build_derived_construct_set(["QSM", "GoalRecord", "EUP", "GRC"], "mixed", "r41")
        self.assertIn("mechanism", cset["kinds_present"])
        self.assertIn("schema", cset["kinds_present"])
        self.assertIn("protocol", cset["kinds_present"])
        self.assertIn("contract", cset["kinds_present"])

    def test_build_construct_set_unknown_raises(self):
        from urace.patterns import build_derived_construct_set
        with self.assertRaises(ValueError):
            build_derived_construct_set(["NOTREAL"], "bad", "r41")

    # --- CLI --kind flag ---

    def test_derive_kind_mechanism_produces_construct_set(self):
        out = io.StringIO()
        with patch.object(cli, "load_config", return_value=self.config), redirect_stdout(out):
            result = cli.main(["derive", "quality regression stagnation", "--kind", "mechanism"])
        self.assertEqual(result, 0)
        self.assertIn("DerivedConstructSet", out.getvalue())

    def test_derive_kind_schema_produces_construct_set(self):
        out = io.StringIO()
        with patch.object(cli, "load_config", return_value=self.config), redirect_stdout(out):
            result = cli.main(["derive", "evidence decision goal", "--kind", "schema"])
        self.assertEqual(result, 0)
        self.assertIn("DerivedConstructSet", out.getvalue())

    def test_derive_kind_all_produces_construct_set(self):
        out = io.StringIO()
        with patch.object(cli, "load_config", return_value=self.config), redirect_stdout(out):
            result = cli.main(["derive", "quality authority resilience", "--kind", "all"])
        self.assertEqual(result, 0)
        self.assertIn("DerivedConstructSet", out.getvalue())

    def test_derive_kind_pattern_still_produces_manifest(self):
        out = io.StringIO()
        with patch.object(cli, "load_config", return_value=self.config), redirect_stdout(out):
            result = cli.main(["derive", "--patterns", "AP0", "--kind", "pattern"])
        self.assertEqual(result, 0)
        self.assertIn("DerivedSystemManifest", out.getvalue())

    def test_derive_kind_all_browse_no_intent(self):
        out = io.StringIO()
        with patch.object(cli, "load_config", return_value=self.config), redirect_stdout(out):
            result = cli.main(["derive", "--kind", "all"])
        self.assertEqual(result, 0)
        text = out.getvalue()
        self.assertIn("mechanism", text)
        self.assertIn("schema", text)

    def test_derive_kind_suggest_construct(self):
        out = io.StringIO()
        with patch.object(cli, "load_config", return_value=self.config), redirect_stdout(out):
            result = cli.main(["derive", "quality checkpoint", "--kind", "mechanism", "--suggest"])
        self.assertEqual(result, 0)
        self.assertIn("Construct suggestions", out.getvalue())
        self.assertNotIn("DerivedConstructSet", out.getvalue())

    def test_derive_kind_json_construct_set(self):
        out = io.StringIO()
        with patch.object(cli, "load_config", return_value=self.config), redirect_stdout(out):
            cli.main(["derive", "authority policy invariant", "--kind", "contract", "--json"])
        data = json.loads(out.getvalue())
        self.assertIn("construct_set_id", data)
        self.assertIn("adopted_constructs", data)
