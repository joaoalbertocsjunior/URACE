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

