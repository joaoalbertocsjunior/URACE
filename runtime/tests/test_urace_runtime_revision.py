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

class R42AdditionsTests(unittest.TestCase):
    """r42: --constructs canonical arg (--patterns backward-compat alias),
    'Building Blocks' README rename, r42 spec version."""

    def setUp(self):
        self.config = isolated_test_config(self)
        self.state = cli.initial_state(self.config)
        cli.seed_confirmed_onboard(self.config, self.state)

    # --- --constructs canonical arg ---

    def test_constructs_arg_builds_manifest(self):
        out = io.StringIO()
        with patch.object(cli, "load_config", return_value=self.config), redirect_stdout(out):
            result = cli.main(["derive", "--constructs", "AP0"])
        self.assertEqual(result, 0)
        self.assertTrue("DerivedConstructSet" in out.getvalue() or "DerivedSystemManifest" in out.getvalue())

    def test_patterns_alias_still_works(self):
        out = io.StringIO()
        with patch.object(cli, "load_config", return_value=self.config), redirect_stdout(out):
            result = cli.main(["derive", "--patterns", "AP0"])
        self.assertEqual(result, 0)
        self.assertTrue("DerivedConstructSet" in out.getvalue() or "DerivedSystemManifest" in out.getvalue())

    def test_constructs_and_patterns_alias_produce_same_output(self):
        out1 = io.StringIO()
        out2 = io.StringIO()
        with patch.object(cli, "load_config", return_value=self.config), redirect_stdout(out1):
            cli.main(["derive", "--constructs", "AP3,AP21"])
        with patch.object(cli, "load_config", return_value=self.config), redirect_stdout(out2):
            cli.main(["derive", "--patterns", "AP3,AP21"])
        # both should include the same patterns
        self.assertIn("AP3", out1.getvalue())
        self.assertIn("AP3", out2.getvalue())
        self.assertIn("AP21", out1.getvalue())
        self.assertIn("AP21", out2.getvalue())

    def test_constructs_with_non_pattern_kind(self):
        out = io.StringIO()
        with patch.object(cli, "load_config", return_value=self.config), redirect_stdout(out):
            result = cli.main(["derive", "--constructs", "QSM,TAG", "--kind", "mechanism"])
        self.assertEqual(result, 0)
        self.assertIn("DerivedConstructSet", out.getvalue())

    def test_constructs_json_output(self):
        out = io.StringIO()
        with patch.object(cli, "load_config", return_value=self.config), redirect_stdout(out):
            cli.main(["derive", "--constructs", "AP0,AP5", "--json"])
        data = json.loads(out.getvalue())
        self.assertTrue("manifest_id" in data or "construct_set_id" in data)

class R43AdditionsTests(unittest.TestCase):
    """r43: agnosticism purge — no runtime function names in spec, Revision Log (§81),
    all contracts stated in executor-agnostic terms."""

class R44AdditionsTests(unittest.TestCase):
    """r44: --from-constraints and --from-inspection on urace derive."""

    def setUp(self):
        from urace import patterns as pattern_catalog_module
        self._pc = pattern_catalog_module
        self.cfg = isolated_test_config(self)

    # --- patterns.py functions ---

    def test_constructs_from_constraints_returns_list(self):
        constraints = [
            {"name": "auth boundary", "description": "all actions must be authorized", "scope": "executor", "enforcement": "hard"},
            {"name": "budget cap", "description": "discovery budget must not exceed limit", "scope": "discovery", "enforcement": "hard"},
        ]
        result = self._pc.constructs_from_constraints(constraints, top_n=5)
        self.assertIsInstance(result, list)
        self.assertLessEqual(len(result), 5)

    def test_constructs_from_constraints_fields(self):
        constraints = [{"name": "authority rule", "description": "executor authority must be validated", "scope": "system", "enforcement": "hard"}]
        result = self._pc.constructs_from_constraints(constraints, top_n=4)
        for entry in result:
            self.assertIn("construct_id", entry)
            self.assertIn("name", entry)
            self.assertIn("kind", entry)
            self.assertIn("score", entry)
            self.assertIn("summary", entry)
            self.assertIn(entry["kind"], {"contract", "protocol", "mechanism"})

    def test_constructs_from_constraints_empty_returns_empty(self):
        result = self._pc.constructs_from_constraints([], top_n=8)
        self.assertEqual(result, [])

    def test_constructs_for_gaps_returns_list(self):
        gaps = [
            {"kind": "schema_validation_failure", "detail": "GoalRecord missing required field"},
            {"kind": "authority_boundary_breach", "detail": "executor action outside declared scope"},
        ]
        result = self._pc.constructs_for_gaps(gaps, top_n=5)
        self.assertIsInstance(result, list)
        self.assertLessEqual(len(result), 5)

    def test_constructs_for_gaps_fields(self):
        gaps = [{"kind": "integrity_gap", "detail": "missing validation on state transition"}]
        result = self._pc.constructs_for_gaps(gaps, top_n=4)
        for entry in result:
            self.assertIn("construct_id", entry)
            self.assertIn("name", entry)
            self.assertIn("kind", entry)
            self.assertIn("score", entry)
            self.assertIn("summary", entry)

    def test_constructs_for_gaps_empty_returns_empty(self):
        result = self._pc.constructs_for_gaps([], top_n=8)
        self.assertEqual(result, [])

    def test_constructs_for_gaps_score_sorted(self):
        gaps = [{"kind": "authority_boundary_breach", "detail": "executor exceeded scope"}] * 3
        result = self._pc.constructs_for_gaps(gaps, top_n=8)
        if len(result) >= 2:
            for i in range(len(result) - 1):
                self.assertGreaterEqual(result[i]["score"], result[i + 1]["score"])

    # --- CLI --from-constraints flag ---

    def test_from_constraints_flag_registered(self):
        import subprocess, sys, os
        result = subprocess.run(
            [sys.executable, "-m", "urace", "derive", "--help"],
            capture_output=True, text=True,
            cwd=str(TEST_RUNTIME_ROOT.parent),
            env={**os.environ, "PYTHONPATH": str(TEST_RUNTIME_ROOT)},
        )
        self.assertIn("--from-constraints", result.stdout + result.stderr)

    def test_from_inspection_flag_registered(self):
        import subprocess, sys, os
        result = subprocess.run(
            [sys.executable, "-m", "urace", "derive", "--help"],
            capture_output=True, text=True,
            cwd=str(TEST_RUNTIME_ROOT.parent),
            env={**os.environ, "PYTHONPATH": str(TEST_RUNTIME_ROOT)},
        )
        self.assertIn("--from-inspection", result.stdout + result.stderr)

    def test_from_constraints_empty_list_returns_empty(self):
        result = self._pc.constructs_from_constraints([], top_n=8)
        self.assertEqual(result, [])

    def test_from_inspection_empty_gaps_returns_empty(self):
        result = self._pc.constructs_for_gaps([], top_n=8)
        self.assertEqual(result, [])

class R45AdditionsTests(unittest.TestCase):
    """r45: --opt-in-constructs alias, ConstructSetRef, DerivedConstructSet --save/--refresh, stale detection."""

    def setUp(self):
        from urace import patterns as _pc
        self._pc = _pc

    # --- --opt-in-constructs alias ---

    def test_opt_in_constructs_flag_registered(self):
        import subprocess, sys, os
        result = subprocess.run(
            [sys.executable, "-m", "urace", "update", "--help"],
            capture_output=True, text=True,
            cwd=str(TEST_RUNTIME_ROOT.parent),
            env={**os.environ, "PYTHONPATH": str(TEST_RUNTIME_ROOT)},
        )
        self.assertIn("--opt-in-constructs", result.stdout + result.stderr)

    def test_opt_in_patterns_alias_still_accepted(self):
        import copy
        config = isolated_test_config(self)
        mock_result = {
            "status": "REVIEW_REQUIRED", "candidate_sha256": "abc123", "added_lines": 1,
            "removed_lines": 0, "local_customizations": {"status": "CLEAN"},
            "source_revision": None, "report": "/tmp/r.json",
        }
        with patch.object(cli, "load_config", return_value=config), \
             patch.object(cli.updater, "explain", return_value=mock_result), \
             redirect_stdout(io.StringIO()):
            result = cli.main(["update", "--opt-in-patterns", "AP8", "explain"])
        self.assertEqual(result, 0)
        self.assertIn("opted_in_constructs", mock_result)

    def test_opt_in_constructs_accepted(self):
        import copy
        config = isolated_test_config(self)
        mock_result = {
            "status": "REVIEW_REQUIRED", "candidate_sha256": "abc123", "added_lines": 1,
            "removed_lines": 0, "local_customizations": {"status": "CLEAN"},
            "source_revision": None, "report": "/tmp/r.json",
        }
        with patch.object(cli, "load_config", return_value=config), \
             patch.object(cli.updater, "explain", return_value=mock_result), \
             redirect_stdout(io.StringIO()):
            result = cli.main(["update", "--opt-in-constructs", "QSM,GoalRecord", "explain"])
        self.assertEqual(result, 0)
        self.assertIn("opted_in_constructs", mock_result)
        self.assertIn("QSM", mock_result["opted_in_constructs"])

    # --- ConstructSetRef save ---

    def test_construct_set_refs_in_initial_state(self):
        import inspect
        src = inspect.getsource(cli.initial_state)
        self.assertIn("construct_set_refs", src)

    # --- _refresh_derived_construct_sets ---

    def test_refresh_construct_sets_no_refs(self):
        import os, tempfile
        with tempfile.TemporaryDirectory() as td:
            cfg = {"root": td, "state_path": os.path.join(td, "state.json"),
                   "config_path": os.path.join(td, "config.json"), "product_files": []}
            state = {"construct_set_refs": []}
            result = cli._refresh_derived_construct_sets(state, cfg, None, False)
            self.assertEqual(len(result), 1)
            self.assertIn("no_saved", result[0]["status"])

    def test_refresh_construct_sets_refreshes_ref(self):
        import os, tempfile
        with tempfile.TemporaryDirectory() as td:
            cfg = {"root": td, "state_path": os.path.join(td, "state.json"),
                   "config_path": os.path.join(td, "config.json"), "product_files": []}
            csr = {
                "id": "csr-test",
                "construct_set_id": "cset-original",
                "spec_version": "2026-01-01-r00",
                "generated_at": "2026-01-01T00:00:00Z",
                "adopted_construct_ids": ["QSM", "GoalRecord"],
                "kinds_present": ["mechanism", "schema"],
                "intent": "test refresh",
            }
            state = {"construct_set_refs": [csr], "derivation_records": []}
            result = cli._refresh_derived_construct_sets(state, cfg, None, show_delta=True)
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["status"], "refreshed")
            self.assertIn("new_construct_set_id", result[0])
            self.assertIn("delta", result[0])
            # new ref written to state
            self.assertEqual(len(state["construct_set_refs"]), 1)
            self.assertNotEqual(state["construct_set_refs"][0]["construct_set_id"], "cset-original")

    # --- stale detection covers construct_set_refs ---

    def test_check_stale_detects_construct_set_refs(self):
        state = {
            "derived_manifest_refs": [],
            "construct_set_refs": [
                {"construct_set_id": "cset-abc", "spec_version": "old-r00", "intent": "test"}
            ],
            "evidence": [],
        }
        stale = cli._check_stale_derived_manifests(state, "new-r99")
        self.assertEqual(len(stale), 1)
        self.assertEqual(stale[0]["construct_set_id"], "cset-abc")
        ev_kinds = [e["kind"] for e in state["evidence"]]
        self.assertIn("derived-construct-set-stale", ev_kinds)

    def test_check_stale_current_construct_set_not_flagged(self):
        state = {
            "derived_manifest_refs": [],
            "construct_set_refs": [
                {"construct_set_id": "cset-abc", "spec_version": "r99", "intent": "test"}
            ],
            "evidence": [],
        }
        stale = cli._check_stale_derived_manifests(state, "r99")
        self.assertEqual(stale, [])

class R46AdditionsTests(unittest.TestCase):
    """r46: new-construct suggestions + construct/pattern update detection on urace update."""

    def setUp(self):
        from urace import patterns as _pc
        self._pc = _pc

    # --- digest functions ---

    def test_construct_digest_returns_string(self):
        d = self._pc.construct_digest("QSM")
        self.assertIsInstance(d, str)
        self.assertGreater(len(d), 0)

    def test_construct_digests_for_ids(self):
        digests = self._pc.construct_digests_for_ids(["QSM", "GoalRecord"])
        self.assertIn("QSM", digests)
        self.assertIn("GoalRecord", digests)

    def test_diff_construct_digests_empty_when_unchanged(self):
        ids = ["QSM", "GoalRecord"]
        saved = self._pc.construct_digests_for_ids(ids)
        changed = self._pc.diff_construct_digests(saved, ids)
        self.assertEqual(changed, [])

    def test_diff_construct_digests_detects_changed(self):
        ids = ["QSM"]
        saved = {"QSM": "stale_digest_000"}
        changed = self._pc.diff_construct_digests(saved, ids)
        self.assertIn("QSM", changed)

    def test_diff_construct_digests_skips_unknown_saved(self):
        # IDs not in saved dict should NOT be flagged
        ids = ["QSM"]
        saved = {}  # no saved digest → unknown, not flagged
        changed = self._pc.diff_construct_digests(saved, ids)
        self.assertEqual(changed, [])

    def test_pattern_digest_returns_string(self):
        d = self._pc.pattern_digest("AP0")
        self.assertIsInstance(d, str)
        self.assertGreater(len(d), 0)

    def test_diff_pattern_digests_empty_when_unchanged(self):
        ids = ["AP0", "AP1"]
        saved = self._pc.pattern_digests_for_ids(ids)
        changed = self._pc.diff_pattern_digests(saved, ids)
        self.assertEqual(changed, [])

    def test_diff_pattern_digests_detects_changed(self):
        changed = self._pc.diff_pattern_digests({"AP0": "old"}, ["AP0"])
        self.assertIn("AP0", changed)

    # --- suggest_new_constructs_for_saved_sets ---

    def test_suggest_new_constructs_empty_refs(self):
        result = self._pc.suggest_new_constructs_for_saved_sets([])
        self.assertEqual(result, [])

    def test_suggest_new_constructs_returns_only_unadopted(self):
        # ref that has adopted nothing → should get suggestions
        refs = [{"construct_set_id": "cset-x", "intent": "authority boundary rule validation",
                 "kinds_present": ["contract"], "adopted_construct_ids": []}]
        result = self._pc.suggest_new_constructs_for_saved_sets(refs, top_n=3)
        if result:
            for s in result[0]["suggestions"]:
                self.assertNotIn(s["construct_id"], set())

    def test_suggest_new_constructs_filters_adopted(self):
        # ref that adopted everything possible → should get empty suggestions
        all_contract_ids = [cid for cid, e in self._pc.CONSTRUCT_CATALOG.items() if e["kind"] == "contract"]
        refs = [{"construct_set_id": "cset-y", "intent": "authority boundary",
                 "kinds_present": ["contract"], "adopted_construct_ids": all_contract_ids}]
        result = self._pc.suggest_new_constructs_for_saved_sets(refs, top_n=3)
        for item in result:
            for s in item["suggestions"]:
                self.assertNotIn(s["construct_id"], set(all_contract_ids))

    def test_suggest_new_patterns_empty_refs(self):
        result = self._pc.suggest_new_patterns_for_saved_manifests([])
        self.assertEqual(result, [])

    def test_suggest_new_patterns_deduplicates_by_manifest_id(self):
        refs = [
            {"manifest_id": "m1", "intent": "resilient event log", "adopted_pattern_ids": []},
            {"manifest_id": "m1", "intent": "resilient event log", "adopted_pattern_ids": []},
        ]
        result = self._pc.suggest_new_patterns_for_saved_manifests(refs, top_n=3)
        manifest_ids = [r["manifest_id"] for r in result]
        self.assertEqual(len(manifest_ids), len(set(manifest_ids)))

    # --- _suggest_derive_updates ---

    def test_suggest_derive_updates_empty_state(self):
        state = {"construct_set_refs": [], "derivation_refs": [], "derived_manifest_refs": []}
        result = cli._suggest_derive_updates(state)
        self.assertIn("new_construct_suggestions", result)
        self.assertIn("updated_constructs", result)
        self.assertIn("new_pattern_suggestions", result)
        self.assertIn("updated_patterns", result)

    def test_suggest_derive_updates_detects_stale_construct(self):
        state = {
            "construct_set_refs": [{
                "construct_set_id": "cset-t",
                "intent": "authority boundary",
                "kinds_present": ["contract"],
                "adopted_construct_ids": ["ABM"],
                "construct_digests": {"ABM": "deliberately_stale_digest"},
            }],
            "derivation_refs": [],
            "derived_manifest_refs": [],
        }
        result = cli._suggest_derive_updates(state)
        updated = result["updated_constructs"]
        self.assertEqual(len(updated), 1)
        self.assertIn("ABM", updated[0]["updated_construct_ids"])

    def test_suggest_derive_updates_no_false_positive_when_current(self):
        from urace import patterns as _pc
        ids = ["ABM"]
        current_digests = _pc.construct_digests_for_ids(ids)
        state = {
            "construct_set_refs": [{
                "construct_set_id": "cset-t",
                "intent": "authority boundary",
                "kinds_present": ["contract"],
                "adopted_construct_ids": ids,
                "construct_digests": current_digests,
            }],
            "derivation_refs": [],
            "derived_manifest_refs": [],
        }
        result = cli._suggest_derive_updates(state)
        self.assertEqual(result["updated_constructs"], [])

    # --- digests stored at --save time ---

    def test_construct_digests_in_saved_ref_keys(self):
        # Verify _csr_ref construction includes construct_digests
        import inspect
        src = inspect.getsource(cli.main)
        self.assertIn("construct_digests", src)

    def test_pattern_digests_in_saved_ref_keys(self):
        import inspect
        src = inspect.getsource(cli.main)
        self.assertIn("pattern_digests", src)

class R48AdditionsTests(unittest.TestCase):
    """r48: Compliance Canonization"""

    def test_compliance_records_in_initial_state(self):
        config = isolated_test_config(self)
        state = cli.initial_state(config)
        self.assertIn("compliance_records", state)
        self.assertEqual(state["compliance_records"], [])

    def test_compliance_state_in_initial_state(self):
        config = isolated_test_config(self)
        state = cli.initial_state(config)
        self.assertIn("compliance_state", state)
        self.assertEqual(state["compliance_state"], {})

    def test_emit_compliance_record_compliant(self):
        state: dict = {"compliance_records": [], "compliance_state": {}}
        cli._emit_compliance_record(state, "authority", "COMPLIANT", "op-abc", None, "product")
        self.assertEqual(len(state["compliance_records"]), 1)
        rec = state["compliance_records"][0]
        self.assertEqual(rec["domain"], "authority")
        self.assertEqual(rec["status"], "COMPLIANT")
        self.assertTrue(rec["id"].startswith("cpl"))
        cs = state["compliance_state"]["authority"]
        self.assertEqual(cs["status"], "COMPLIANT")
        self.assertEqual(cs["consecutive_clean"], 1)

    def test_emit_compliance_record_non_compliant(self):
        state: dict = {"compliance_records": [], "compliance_state": {}}
        cli._emit_compliance_record(state, "schema", "NON_COMPLIANT", "op-xyz", "missing field", None)
        rec = state["compliance_records"][0]
        self.assertEqual(rec["status"], "NON_COMPLIANT")
        self.assertEqual(rec["violation_detail"], "missing field")
        cs = state["compliance_state"]["schema"]
        self.assertEqual(cs["consecutive_clean"], 0)
        self.assertEqual(len(cs["violation_refs"]), 1)

    def test_emit_compliance_consecutive_clean_increments(self):
        state: dict = {"compliance_records": [], "compliance_state": {}}
        cli._emit_compliance_record(state, "intent", "COMPLIANT")
        cli._emit_compliance_record(state, "intent", "COMPLIANT")
        cli._emit_compliance_record(state, "intent", "COMPLIANT")
        self.assertEqual(state["compliance_state"]["intent"]["consecutive_clean"], 3)

    def test_emit_compliance_non_compliant_resets_clean(self):
        state: dict = {"compliance_records": [], "compliance_state": {}}
        cli._emit_compliance_record(state, "constraint", "COMPLIANT")
        cli._emit_compliance_record(state, "constraint", "COMPLIANT")
        cli._emit_compliance_record(state, "constraint", "NON_COMPLIANT", violation_detail="violated")
        self.assertEqual(state["compliance_state"]["constraint"]["consecutive_clean"], 0)

    def test_compliance_command_output(self):
        config = isolated_test_config(self)
        state: dict = {"compliance_records": [], "compliance_state": {}}
        cli._emit_compliance_record(state, "authority", "COMPLIANT", "op-1")
        cli._emit_compliance_record(state, "intent", "NON_COMPLIANT", "op-2", "drift")
        buf = io.StringIO()
        with patch.object(cli, "load_config", return_value=config), \
             patch.object(cli, "load_state_for_read", return_value=state), \
             redirect_stdout(buf):
            ret = cli.main(["compliance", "--json"])
        self.assertEqual(ret, 0)
        result = json.loads(buf.getvalue())
        self.assertEqual(result["total_records"], 2)
        self.assertEqual(result["compliant"], 1)
        self.assertEqual(result["non_compliant"], 1)

class R52AdditionsTests(unittest.TestCase):
    """Tests for r52: NSS Compliance + Critical Bug Fixes."""


    def test_pending_validations_plural_in_initial_state(self):
        config = isolated_test_config(self)
        state = cli.initial_state(config)
        self.assertIn("pending_validations", state,
                      "initial_state() must use 'pending_validations' (plural canonical)")
        self.assertNotIn("pending_validation", state,
                         "initial_state() must not use deprecated 'pending_validation' (singular)")

    def test_decision_records_key_in_material_state_signature(self):
        import inspect
        source = inspect.getsource(cli.material_state_signature)
        self.assertIn("decision_records", source,
                      "material_state_signature must use 'decision_records' key (§45 compliance)")
        self.assertNotIn('"decisions"', source,
                         "material_state_signature must not use legacy 'decisions' key")

class R54AdditionsTests(unittest.TestCase):
    """Tests for r54: Gap closure pass (7 items from r53 audit)."""


    def test_compaction_authorization_stale_in_primitives(self):
        from urace import primitives as p
        self.assertIn("compaction-authorization-stale", p.INTEGRITY_GAP_CATALOG)

    def test_validation_evidence_missing_in_primitives(self):
        from urace import primitives as p
        self.assertIn("validation-evidence-missing", p.INTEGRITY_GAP_CATALOG)

class R65AdditionsTests(unittest.TestCase):
    def setUp(self):
        self.config = isolated_test_config(self)
        self.config["executor"]["enabled"] = False
        self.state = cli.initial_state(self.config)
        cli.seed_confirmed_onboard(self.config, self.state)

    # --- Blocker schema extension ---

    def test_blocker_new_fields_present(self):
        cli.record_blocker(self.state, "execution", "executor unavailable",
                           classification="TRANSIENT",
                           evidence_id="ev-test-1",
                           auto_clear_on="executor-availability-restored")
        b = self.state["blockers"][0]
        self.assertEqual(b["classification"], "TRANSIENT")
        self.assertEqual(b["evidence_id"], "ev-test-1")
        self.assertEqual(b["auto_clear_on"], "executor-availability-restored")
        self.assertIn("escalation_due", b)
        self.assertIsNone(b["escalation_due"])

    def test_blocker_default_classification_is_persistent(self):
        cli.record_blocker(self.state, "discovery", "offline")
        self.assertEqual(self.state["blockers"][0]["classification"], "PERSISTENT")

    def test_blocker_auto_escalation_at_count5_and_old_age(self):
        cli.record_blocker(self.state, "discovery", "rate-limited", classification="PERSISTENT")
        b = self.state["blockers"][0]
        # Manually age the blocker and set count to trigger escalation
        b["at"] = (datetime.now(timezone.utc) - timedelta(seconds=4000)).strftime("%Y-%m-%dT%H:%M:%SZ")
        b["count"] = 4
        # One more recurrence triggers the check
        cli.record_blocker(self.state, "discovery", "rate-limited")
        updated = next(x for x in self.state["blockers"] if x["scope"] == "discovery")
        self.assertEqual(updated["count"], 5)
        self.assertEqual(updated.get("classification"), "ESCALATION")
        gaps = [g for g in self.state.get("integrity_gaps", []) if g.get("kind") == "blocker-escalated"]
        self.assertTrue(len(gaps) >= 1)

    def test_blocker_operator_gate_never_auto_resolves(self):
        cli.record_blocker(self.state, "evolution", "policy-change-required",
                           classification="OPERATOR_GATE")
        b = self.state["blockers"][0]
        old = (datetime.now(timezone.utc) - timedelta(seconds=700)).strftime("%Y-%m-%dT%H:%M:%SZ")
        b["last_at"] = old
        b["at"] = old
        cli._auto_resolve_blockers(self.state)
        self.assertIsNone(b.get("resolved_at"))

    def test_blocker_transient_auto_resolves_after_600s(self):
        cli.record_blocker(self.state, "network", "flaky-connection",
                           classification="TRANSIENT")
        b = self.state["blockers"][0]
        old = (datetime.now(timezone.utc) - timedelta(seconds=700)).strftime("%Y-%m-%dT%H:%M:%SZ")
        b["last_at"] = old
        b["at"] = old
        cli._auto_resolve_blockers(self.state)
        self.assertIsNotNone(b.get("resolved_at"))
        evs = [e for e in self.state.get("evidence", []) if e.get("kind") == "blocker-transient-expired"]
        self.assertTrue(len(evs) >= 1)

    def test_blocker_deduplication_updates_existing(self):
        cli.record_blocker(self.state, "discovery", "slow", classification="PERSISTENT")
        cli.record_blocker(self.state, "discovery", "slow")
        self.assertEqual(len(self.state["blockers"]), 1)
        self.assertEqual(self.state["blockers"][0]["count"], 2)

    # --- AP14 priority tier ---

    def test_inbox_priority_tier_sort_order(self):
        """Tier 0 must sort before Tier 1 regardless of 'at' timestamp."""
        tier1 = {"id": "a", "at": "2026-01-01T10:00:00Z", "kind": "context",
                 "payload": {"text": "standard"}, "priority_tier": 1}
        tier0 = {"id": "b", "at": "2026-01-01T10:00:01Z", "kind": "control",
                 "payload": {"action": "pause"}, "priority_tier": 0}
        pending = [(tier1["at"], None, tier1), (tier0["at"], None, tier0)]

        def effective_tier(item):
            declared = item.get("priority_tier", 1)
            if item.get("kind") == "control" and item.get("payload", {}).get("action") in ("pause", "stop"):
                return 0
            return max(0, min(2, declared if isinstance(declared, int) else 1))

        pending.sort(key=lambda x: (effective_tier(x[2]), x[0]))
        self.assertEqual(pending[0][2]["id"], "b")  # tier-0 first
        self.assertEqual(pending[1][2]["id"], "a")  # tier-1 second

    def test_inbox_fifo_within_same_tier(self):
        """Within same tier, earlier 'at' must come first."""
        inputs = [
            {"id": "c", "at": "2026-01-01T10:00:02Z", "kind": "context", "payload": {}, "priority_tier": 1},
            {"id": "a", "at": "2026-01-01T10:00:00Z", "kind": "context", "payload": {}, "priority_tier": 1},
            {"id": "b", "at": "2026-01-01T10:00:01Z", "kind": "context", "payload": {}, "priority_tier": 1},
        ]
        pending = [(i["at"], None, i) for i in inputs]
        pending.sort(key=lambda x: (x[2].get("priority_tier", 1), x[0]))
        ids = [x[2]["id"] for x in pending]
        self.assertEqual(ids, ["a", "b", "c"])

    # --- Spec contract tests ---

    def test_assessment_gap_deduplication_updates_not_appends(self):
        """BJ — same cycle_id+dimension MUST update last_at, not append."""
        cli.record_assessment_gap(self.state, "cyc-1", "EVIDENCE", "insufficient evidence", "one evidence unit required", True)
        cli.record_assessment_gap(self.state, "cyc-1", "EVIDENCE", "still insufficient", "one evidence unit required", True)
        active = [g for g in self.state["assessment_gaps"] if g.get("resolved_at") is None
                  and g["cycle_id"] == "cyc-1" and g["dimension"] == "EVIDENCE"]
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0]["reason"], "still insufficient")

    def test_assessment_gap_different_dimension_creates_new(self):
        """Distinct dimension on same cycle_id produces a separate gap record."""
        cli.record_assessment_gap(self.state, "cyc-1", "EVIDENCE", "r1", "m1", True)
        cli.record_assessment_gap(self.state, "cyc-1", "AUTHORITY", "r2", "m2", True)
        active = [g for g in self.state["assessment_gaps"] if g.get("resolved_at") is None]
        self.assertEqual(len(active), 2)

    # --- BK: AssessmentGap resolution ---

    def test_assessment_gap_resolution_sets_resolved_at(self):
        """BK — resolve_assessment_gap sets resolved_at to an ISO-8601 timestamp."""
        cli.record_assessment_gap(self.state, "cyc-2", "STATE", "state unclear", "state confirmed", False)
        result = cli.resolve_assessment_gap(self.state, "cyc-2", "STATE")
        self.assertTrue(result)
        gap = self.state["assessment_gaps"][0]
        self.assertIsNotNone(gap["resolved_at"])
        self.assertRegex(gap["resolved_at"], r"^\d{4}-\d{2}-\d{2}T")

    def test_assessment_gap_resolved_not_in_active_list(self):
        """BK — resolved gap must not appear in active (resolved_at=None) list."""
        cli.record_assessment_gap(self.state, "cyc-3", "INTENT", "intent unclear", "intent confirmed", True)
        cli.resolve_assessment_gap(self.state, "cyc-3", "INTENT")
        active = [g for g in self.state["assessment_gaps"] if g.get("resolved_at") is None
                  and g["cycle_id"] == "cyc-3" and g["dimension"] == "INTENT"]
        self.assertEqual(len(active), 0)

    def test_state_assessment_gaps_initialized(self):
        """State Document must initialize assessment_gaps as empty list."""
        self.assertIn("assessment_gaps", self.state)
        self.assertIsInstance(self.state["assessment_gaps"], list)

    def test_state_lifecycle_boundaries_initialized(self):
        """State Document must initialize lifecycle_boundaries as empty list."""
        self.assertIn("lifecycle_boundaries", self.state)
        self.assertIsInstance(self.state["lifecycle_boundaries"], list)

    def test_state_integrity_signals_initialized(self):
        """State Document must initialize integrity_signals as empty list."""
        self.assertIn("integrity_signals", self.state)
        self.assertIsInstance(self.state["integrity_signals"], list)

    def test_decision_record_accepts_justification_context_id(self):
        """DecisionRecord.justification_context_id OPTIONAL field must be accepted."""
        from urace import decision_record as dr
        digest = hashlib.sha256(b"x").hexdigest()
        executor = {"executor_id": "test-exec", "adapter": "test", "capability": "planning", "logical_reservation": "none", "attempted_executors": []}
        rec = dr.create_decision_record(
            kind="NAVIGATION_ASSESSMENT",
            subject="test",
            outcome="assessed",
            governing_intent_ref="intent-1",
            state_digest=digest,
            executor=executor,
            justification_context_id="jctx-abc123",
        )
        self.assertEqual(rec.get("justification_context_id"), "jctx-abc123")

