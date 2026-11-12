"""Tests for urace.uncertainty_followup — evidence-driven follow-up planning."""
import hashlib
import json
import unittest


def _claim(kind, text="test claim", **kwargs):
    return {"kind": kind, "text": text, "id": f"c-{kind}", **kwargs}


class PlanOutputTests(unittest.TestCase):
    def test_returns_schema_key(self):
        from urace.uncertainty_followup import plan
        result = plan([])
        self.assertEqual(result["schema"], "uncertainty-followups-v1")

    def test_returns_items_list(self):
        from urace.uncertainty_followup import plan
        result = plan([_claim("bounded_behavior")])
        self.assertIsInstance(result["items"], list)
        self.assertEqual(len(result["items"]), 1)

    def test_native_model_calls_always_zero(self):
        from urace.uncertainty_followup import plan
        result = plan([_claim("bounded_behavior"), _claim("statistical_estimate")])
        self.assertEqual(result["native_model_calls"], 0)

    def test_trigger_sha256_is_deterministic(self):
        from urace.uncertainty_followup import plan
        claims = [_claim("bounded_behavior", text="same")]
        r1 = plan(claims)
        r2 = plan(claims)
        self.assertEqual(r1["trigger_sha256"], r2["trigger_sha256"])

    def test_trigger_sha256_changes_with_input(self):
        from urace.uncertainty_followup import plan
        r1 = plan([_claim("bounded_behavior", text="A")])
        r2 = plan([_claim("bounded_behavior", text="B")])
        self.assertNotEqual(r1["trigger_sha256"], r2["trigger_sha256"])

    def test_empty_claims_returns_empty_items(self):
        from urace.uncertainty_followup import plan
        result = plan([])
        self.assertEqual(result["items"], [])


class StatusRoutingTests(unittest.TestCase):
    def test_universal_optimality_not_provable(self):
        from urace.uncertainty_followup import plan
        result = plan([_claim("universal_optimality")])
        self.assertEqual(result["items"][0]["status"], "NOT_PROVABLE_AS_STATED")

    def test_universal_perfection_not_provable(self):
        from urace.uncertainty_followup import plan
        result = plan([_claim("universal_perfection")])
        self.assertEqual(result["items"][0]["status"], "NOT_PROVABLE_AS_STATED")

    def test_statistical_estimate_waiting_evidence(self):
        from urace.uncertainty_followup import plan
        result = plan([_claim("statistical_estimate")])
        self.assertEqual(result["items"][0]["status"], "WAITING_MATCHED_EVIDENCE")

    def test_comparative_gain_waiting_evidence(self):
        from urace.uncertainty_followup import plan
        result = plan([_claim("comparative_gain")])
        self.assertEqual(result["items"][0]["status"], "WAITING_MATCHED_EVIDENCE")

    def test_external_approval_waiting_external(self):
        from urace.uncertainty_followup import plan
        result = plan([_claim("external_approval")])
        self.assertEqual(result["items"][0]["status"], "WAITING_EXTERNAL_CONDITION")

    def test_missing_source_waiting_clarification(self):
        from urace.uncertainty_followup import plan
        result = plan([_claim("bounded_behavior")])
        self.assertEqual(result["items"][0]["status"], "WAITING_SOURCE_OR_CLARIFICATION")

    def test_verified_independent_claim_verified(self):
        from urace.uncertainty_followup import plan
        claim = _claim("bounded_behavior", status="VERIFIED",
                       independently_verified=True, source_sha256="abc123",
                       evidence_refs=["ref1"])
        result = plan([claim])
        self.assertEqual(result["items"][0]["status"], "VERIFIED_WITHIN_DECLARED_SCOPE")

    def test_bounded_with_source_ready_for_validation(self):
        from urace.uncertainty_followup import plan
        claim = _claim("bounded_behavior", source_sha256="def456")
        result = plan([claim])
        self.assertEqual(result["items"][0]["status"], "READY_FOR_BOUNDED_VALIDATION")


class ItemFieldsTests(unittest.TestCase):
    def test_id_preserved(self):
        from urace.uncertainty_followup import plan
        claim = _claim("statistical_estimate")
        result = plan([claim])
        self.assertEqual(result["items"][0]["id"], "c-statistical_estimate")

    def test_resource_policy_present(self):
        from urace.uncertainty_followup import plan
        result = plan([_claim("bounded_behavior")])
        item = result["items"][0]
        self.assertIn("resource_policy", item)

    def test_estimated_additional_native_cost_is_none(self):
        from urace.uncertainty_followup import plan
        result = plan([_claim("statistical_estimate")])
        self.assertIsNone(result["items"][0]["estimated_additional_native_cost"])
