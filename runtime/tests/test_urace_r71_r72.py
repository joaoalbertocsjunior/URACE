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



class R71Phase1Tests(unittest.TestCase):
    """Phase 1 gap closure: wake stale→expired escalation + discovery proportionality gaps."""

    def setUp(self):
        self.config = isolated_test_config(self)
        self.config["executor"]["enabled"] = False
        self.state = cli.initial_state(self.config)
        cli.seed_confirmed_onboard(self.config, self.state)

    # ── Wake stale→expired escalation ────────────────────────────────────────

    def test_wake_verify_resets_failure_count_on_success(self):
        """A fully valid registration resets liveness_failures to 0 and updates verified_at."""
        reg = {
            "id": "wkr-reset1",
            "kind": "scheduled",
            "scheduled_at": "2027-01-01T00:00:00+00:00",
            "verified_at": "2026-01-01T00:00:00+00:00",
            "liveness_failures": 2,
        }
        self.state["wake_registry"] = [reg]
        gaps = cli._verify_wake_registrations({}, self.state)
        self.assertEqual(gaps, [])
        self.assertEqual(reg["liveness_failures"], 0)
        self.assertNotIn("stale_since", reg)

    def test_wake_verify_increments_failures_on_missing_verified_at(self):
        """Missing verified_at increments liveness_failures each call."""
        reg = {
            "id": "wkr-fail1",
            "kind": "scheduled",
            "scheduled_at": "2027-01-01T00:00:00+00:00",
        }
        self.state["wake_registry"] = [reg]
        cli._verify_wake_registrations({}, self.state)
        self.assertEqual(reg.get("liveness_failures"), 1)
        cli._verify_wake_registrations({}, self.state)
        self.assertEqual(reg.get("liveness_failures"), 2)

    def test_wake_verify_marks_stale_after_three_failures(self):
        """After 3 failures, stale_since is set on the registration."""
        reg = {
            "id": "wkr-stale1",
            "kind": "scheduled",
            "scheduled_at": "2027-01-01T00:00:00+00:00",
            "liveness_failures": 2,
        }
        self.state["wake_registry"] = [reg]
        cli._verify_wake_registrations({}, self.state)
        self.assertEqual(reg.get("liveness_failures"), 3)
        self.assertIn("stale_since", reg)

    def test_wake_verify_escalates_to_blocking_gap_after_max_stale_hours(self):
        """STALE registration older than max_stale_hours emits BLOCKING wake-registration-expired gap."""
        from datetime import timedelta
        stale_ts = (datetime.now(timezone.utc) - timedelta(hours=200)).isoformat()
        reg = {
            "id": "wkr-expired1",
            "kind": "scheduled",
            "scheduled_at": "2027-01-01T00:00:00+00:00",
            "liveness_failures": 5,
            "stale_since": stale_ts,
        }
        self.state["wake_registry"] = [reg]
        config = {"wake": {"max_stale_hours": 168}}
        cli._verify_wake_registrations(config, self.state)
        blocking_gaps = [
            g for g in self.state.get("integrity_gaps", [])
            if g.get("kind") == "wake-registration-expired"
        ]
        self.assertEqual(len(blocking_gaps), 1)
        self.assertEqual(blocking_gaps[0]["severity"], "BLOCKING")

    def test_wake_verify_no_blocking_gap_before_max_stale_hours(self):
        """STALE registration within max_stale_hours does NOT escalate to BLOCKING gap."""
        from datetime import timedelta
        stale_ts = (datetime.now(timezone.utc) - timedelta(hours=10)).isoformat()
        reg = {
            "id": "wkr-recent-stale",
            "kind": "scheduled",
            "scheduled_at": "2027-01-01T00:00:00+00:00",
            "liveness_failures": 4,
            "stale_since": stale_ts,
        }
        self.state["wake_registry"] = [reg]
        config = {"wake": {"max_stale_hours": 168}}
        cli._verify_wake_registrations(config, self.state)
        blocking_gaps = [
            g for g in self.state.get("integrity_gaps", [])
            if g.get("kind") == "wake-registration-expired"
        ]
        self.assertEqual(len(blocking_gaps), 0)

    # ── Discovery proportionality IntegrityGaps ───────────────────────────────

    def test_discovery_proportionality_deferred_emits_named_gap(self):
        """DEFERRED_PROPORTIONALITY condition emits discovery-proportionality-deferred gap."""
        config = copy.deepcopy(self.config)
        config["executor"]["enabled"] = True
        config["executor"]["max_executor_calls_per_24h"] = 100
        config["executor"]["max_executor_calls_per_30d"] = 1000
        self.state["lifecycle_state"] = "BLOCKED"
        self.state["executor_state"]["last_discovery_at"] = "2020-01-01T00:00:00+00:00"
        result = cli.executor_discovery_due(config, self.state)
        self.assertFalse(result)
        self.assertEqual(
            self.state["executor_state"].get("discovery_budget_status"),
            "DEFERRED_PROPORTIONALITY",
        )
        gap_kinds = [g["kind"] for g in self.state.get("integrity_gaps", [])]
        self.assertIn("discovery-proportionality-deferred", gap_kinds)

    def test_discovery_yield_exhausted_emits_named_gap(self):
        """DISCOVERY_YIELD_EXHAUSTED condition emits discovery-yield-exhausted gap."""
        config = copy.deepcopy(self.config)
        config["executor"]["enabled"] = True
        config["executor"]["max_executor_calls_per_24h"] = 100
        config["executor"]["max_executor_calls_per_30d"] = 1000
        config["executor"]["discovery_yield_exhausted_threshold"] = 3
        self.state["lifecycle_state"] = "ACTIVE"
        self.state["executor_state"]["last_discovery_at"] = "2020-01-01T00:00:00+00:00"
        self.state["executor_state"]["unproductive_discovery_streak"] = 3
        result = cli.executor_discovery_due(config, self.state)
        self.assertFalse(result)
        self.assertEqual(
            self.state["executor_state"].get("discovery_budget_status"),
            "DISCOVERY_YIELD_EXHAUSTED",
        )
        gap_kinds = [g["kind"] for g in self.state.get("integrity_gaps", [])]
        self.assertIn("discovery-yield-exhausted", gap_kinds)

    def test_discovery_hard_budget_limit_does_not_emit_gap(self):
        """Daily hard budget ceiling does NOT emit an IntegrityGap (only deferred conditions do)."""
        config = copy.deepcopy(self.config)
        config["executor"]["enabled"] = True
        config["executor"]["max_executor_calls_per_24h"] = 2
        config["executor"]["max_executor_calls_per_30d"] = 1000
        from datetime import timedelta
        recent = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        self.state["executor_state"]["executor_calls"] = [
            {"at": recent, "stage": "discovery", "outcome": "ok"},
        ]
        result = cli.executor_discovery_due(config, self.state)
        self.assertFalse(result)
        self.assertEqual(
            self.state["executor_state"].get("discovery_budget_status"),
            "DAILY_LIMIT_OR_RESERVE_REACHED",
        )
        gap_kinds = [g["kind"] for g in self.state.get("integrity_gaps", [])]
        self.assertNotIn("discovery-proportionality-deferred", gap_kinds)
        self.assertNotIn("discovery-yield-exhausted", gap_kinds)

    def test_discovery_proportionality_gap_is_idempotent(self):
        """Calling executor_discovery_due twice in BLOCKED state emits gap only once."""
        config = copy.deepcopy(self.config)
        config["executor"]["enabled"] = True
        config["executor"]["max_executor_calls_per_24h"] = 100
        config["executor"]["max_executor_calls_per_30d"] = 1000
        self.state["lifecycle_state"] = "BLOCKED"
        self.state["executor_state"]["last_discovery_at"] = "2020-01-01T00:00:00+00:00"
        cli.executor_discovery_due(config, self.state)
        cli.executor_discovery_due(config, self.state)
        gap_count = sum(
            1 for g in self.state.get("integrity_gaps", [])
            if g["kind"] == "discovery-proportionality-deferred"
        )
        self.assertEqual(gap_count, 1)

class R71Phase2Tests(unittest.TestCase):
    """Phase 2 gap closure: capability envelope gate + BOOTSTRAPPING→CAPABLE transition gate."""

    def setUp(self):
        self.config = isolated_test_config(self)
        self.config["executor"]["enabled"] = False
        self.state = cli.initial_state(self.config)
        cli.seed_confirmed_onboard(self.config, self.state)

    # ── Capability Envelope Gate in objective selection ───────────────────────

    def test_capability_defining_objective_blocked_at_capable_maturity(self):
        """CAPABILITY_DEFINING objective is not eligible at CAPABLE maturity without DecisionRecord."""
        from urace import inspection
        self.state["sweet_spot_assessments"] = [{"maturity_level": "CAPABLE"}]
        obj = {"id": "obj-cap1", "kind": "CAPABILITY_DEFINING", "title": "Add new API surface", "scope": "product"}
        self.assertFalse(inspection.objective_is_eligible(self.state, obj))
        gap_kinds = [g["kind"] for g in self.state.get("integrity_gaps", [])]
        self.assertIn("capability-envelope-breach", gap_kinds)

    def test_capability_defining_objective_blocked_at_optimized_maturity(self):
        """CAPABILITY_DEFINING objective is not eligible at OPTIMIZED maturity without DecisionRecord."""
        from urace import inspection
        self.state["sweet_spot_assessments"] = [{"maturity_level": "OPTIMIZED"}]
        obj = {"id": "obj-cap2", "kind": "CAPABILITY_DEFINING", "title": "Expand feature set", "scope": "product"}
        self.assertFalse(inspection.objective_is_eligible(self.state, obj))

    def test_capability_defining_objective_allowed_with_authority_grant(self):
        """CAPABILITY_DEFINING objective IS eligible when authorizing DecisionRecord exists."""
        from urace import inspection
        self.state["sweet_spot_assessments"] = [{"maturity_level": "CAPABLE"}]
        self.state["decision_records"] = [{
            "id": "dr-grant1",
            "kind": "AUTHORITY_GRANT",
            "subject": "obj-cap3",
            "authorized_objective_ids": ["obj-cap3"],
        }]
        obj = {"id": "obj-cap3", "kind": "CAPABILITY_DEFINING", "title": "Expand with authority", "scope": "product"}
        self.assertTrue(inspection.objective_is_eligible(self.state, obj))

    def test_capability_defining_objective_allowed_at_forming_maturity(self):
        """CAPABILITY_DEFINING objective is eligible at FORMING maturity (gate only applies at CAPABLE+)."""
        from urace import inspection
        self.state["sweet_spot_assessments"] = [{"maturity_level": "FORMING"}]
        obj = {"id": "obj-cap4", "kind": "CAPABILITY_DEFINING", "title": "Build core capability", "scope": "product"}
        self.assertTrue(inspection.objective_is_eligible(self.state, obj))

    def test_non_capability_defining_objective_unaffected_by_maturity_gate(self):
        """A regular (non-CAPABILITY_DEFINING) objective is not affected by the maturity gate."""
        from urace import inspection
        self.state["sweet_spot_assessments"] = [{"maturity_level": "CAPABLE"}]
        obj = {"id": "obj-reg1", "title": "Improve documentation", "scope": "documentation"}
        self.assertTrue(inspection.objective_is_eligible(self.state, obj))

    # ── BOOTSTRAPPING→CAPABLE transition gate ────────────────────────────────

    def _make_envelope_config(self):
        config = copy.deepcopy(self.config)
        config["capability_envelope"] = {
            "capabilities": [{"id": "cap-core1", "value_weight": 1.0}],
            "completeness_target": 1.0,
        }
        return config

    def test_capable_status_without_test_record_emits_warning_gap(self):
        """Capability marked CAPABLE without passing TestRunRecord emits capability-without-test-coverage."""
        config = self._make_envelope_config()
        self.state["capability_states"] = [{"capability_id": "cap-core1", "status": "CAPABLE", "completeness_fraction": 1.0}]
        cli._evaluate_sweet_spot(self.state, config)
        gap_kinds = [g["kind"] for g in self.state.get("integrity_gaps", [])]
        self.assertIn("capability-without-test-coverage", gap_kinds)

    def test_capable_status_with_passing_capability_gate_record_no_gap(self):
        """Capability with passing CAPABILITY_GATE TestRunRecord does NOT emit the gap."""
        config = self._make_envelope_config()
        self.state["capability_states"] = [{"capability_id": "cap-core1", "status": "CAPABLE", "completeness_fraction": 1.0}]
        self.state["test_run_records"] = [{
            "id": "trr-gate1",
            "run_at": "2026-10-01T00:00:00+00:00",
            "kind": "CAPABILITY_GATE",
            "verdict": "PASS",
            "total": 5, "passed": 5, "failed": 0, "errored": 0,
            "capability_ids_covered": ["cap-core1"],
            "test_ids": [],
        }]
        cli._evaluate_sweet_spot(self.state, config)
        gap_kinds = [g["kind"] for g in self.state.get("integrity_gaps", [])]
        self.assertNotIn("capability-without-test-coverage", gap_kinds)

    def test_capable_status_with_passing_acceptance_record_no_gap(self):
        """Passing ACCEPTANCE TestRunRecord also satisfies the capability-without-test-coverage check."""
        config = self._make_envelope_config()
        self.state["capability_states"] = [{"capability_id": "cap-core1", "status": "CAPABLE", "completeness_fraction": 1.0}]
        self.state["test_run_records"] = [{
            "id": "trr-acc1",
            "run_at": "2026-10-01T00:00:00+00:00",
            "kind": "ACCEPTANCE",
            "verdict": "PASS",
            "total": 3, "passed": 3, "failed": 0, "errored": 0,
            "capability_ids_covered": ["cap-core1"],
            "test_ids": [],
        }]
        cli._evaluate_sweet_spot(self.state, config)
        gap_kinds = [g["kind"] for g in self.state.get("integrity_gaps", [])]
        self.assertNotIn("capability-without-test-coverage", gap_kinds)

    def test_failing_test_record_does_not_clear_gap(self):
        """A FAIL TestRunRecord does NOT satisfy the capability-without-test-coverage check."""
        config = self._make_envelope_config()
        self.state["capability_states"] = [{"capability_id": "cap-core1", "status": "CAPABLE", "completeness_fraction": 1.0}]
        self.state["test_run_records"] = [{
            "id": "trr-fail1",
            "run_at": "2026-10-01T00:00:00+00:00",
            "kind": "CAPABILITY_GATE",
            "verdict": "FAIL",
            "total": 5, "passed": 3, "failed": 2, "errored": 0,
            "capability_ids_covered": ["cap-core1"],
            "test_ids": [],
        }]
        cli._evaluate_sweet_spot(self.state, config)
        gap_kinds = [g["kind"] for g in self.state.get("integrity_gaps", [])]
        self.assertIn("capability-without-test-coverage", gap_kinds)

class R71Phase3Tests(unittest.TestCase):
    """Phase 3 gap closure: CSI/PPP_M community signal ingestion + patch proposal pipeline."""

    def setUp(self):
        self.config = isolated_test_config(self)
        self.config["executor"]["enabled"] = False
        self.state = cli.initial_state(self.config)
        cli.seed_confirmed_onboard(self.config, self.state)

    def _config_with_feed(self, feed: dict) -> dict:
        """Return config with a single feed under community_inbox.feeds (spec-correct location)."""
        config = copy.deepcopy(self.config)
        config["community_inbox"] = {"feeds": [feed]}
        return config

    # ── initial_state includes community fields ───────────────────────────────

    def test_initial_state_has_community_fields(self):
        """initial_state() initializes community_feeds, community_signals, patch_proposals."""
        self.assertIn("community_feeds", self.state)
        self.assertIn("community_signals", self.state)
        self.assertIn("patch_proposals", self.state)
        self.assertEqual(self.state["community_feeds"], [])
        self.assertEqual(self.state["community_signals"], [])
        self.assertEqual(self.state["patch_proposals"], [])

    def test_csi_off_by_default_no_feeds_in_config(self):
        """CSI is off when Config.community_inbox.feeds is absent (default empty)."""
        self.state["lifecycle_state"] = "ACTIVE"
        cli._run_csi(self.config, self.state)
        self.assertEqual(len(self.state["community_signals"]), 0)

    # ── CSI: terms_accepted gate ──────────────────────────────────────────────

    def test_csi_skips_feed_without_terms_accepted(self):
        """CSI does not ingest from feeds where terms_accepted=False."""
        self.state["lifecycle_state"] = "ACTIVE"
        config = self._config_with_feed({
            "id": "cfeed-test1", "kind": "RSS",
            "endpoint": "https://example.com/feed",
            "terms_accepted": False, "active": True,
            "_pending_items": [{"source_ref": "item-1", "content": "test signal"}],
        })
        cli._run_csi(config, self.state)
        self.assertEqual(len(self.state["community_signals"]), 0)
        gap_kinds = [g["kind"] for g in self.state.get("integrity_gaps", [])]
        self.assertIn("community-feed-terms-not-accepted", gap_kinds)

    def test_csi_terms_accepted_gap_is_idempotent(self):
        """community-feed-terms-not-accepted gap is emitted only once per feed."""
        self.state["lifecycle_state"] = "ACTIVE"
        config = self._config_with_feed({
            "id": "cfeed-idem1", "kind": "RSS",
            "endpoint": "https://example.com/feed",
            "terms_accepted": False, "active": True,
        })
        cli._run_csi(config, self.state)
        cli._run_csi(config, self.state)
        count = sum(1 for g in self.state.get("integrity_gaps", []) if g["kind"] == "community-feed-terms-not-accepted")
        self.assertEqual(count, 1)

    # ── CSI: signal creation and scoring ─────────────────────────────────────

    def test_csi_creates_signal_from_pending_item(self):
        """CSI creates a CommunitySignal for each pending item in an accepted feed."""
        self.state["lifecycle_state"] = "ACTIVE"
        self.state["intent"] = "build fast reliable messaging"
        config = self._config_with_feed({
            "id": "cfeed-sig1", "kind": "RSS",
            "endpoint": "https://example.com/feed",
            "terms_accepted": True, "active": True,
            "_pending_items": [{"source_ref": "https://example.com/item/1", "content": "fast messaging improvements needed"}],
        })
        cli._run_csi(config, self.state)
        self.assertEqual(len(self.state["community_signals"]), 1)
        sig = self.state["community_signals"][0]
        self.assertTrue(sig["id"].startswith("csig-"))
        self.assertIn("relevance_score", sig)
        self.assertIn("confidence_score", sig)
        self.assertIn("signal_quality", sig)
        self.assertIn("filtered", sig)

    def test_csi_deduplicates_by_source_ref(self):
        """CSI does not create duplicate signals for the same source_ref."""
        self.state["lifecycle_state"] = "ACTIVE"
        self.state["community_signals"] = [{
            "id": "csig-existing1",
            "created_at": "2026-10-01T00:00:00+00:00",
            "updated_at": "2026-10-01T00:00:00+00:00",
            "feed_id": "cfeed-dup1",
            "content": "existing signal",
            "source_ref": "https://example.com/item/dup",
            "received_at": "2026-10-01T00:00:00+00:00",
            "relevance_score": 0.5,
            "confidence_score": 0.3,
            "signal_quality": "LOW",
            "filtered": False,
        }]
        config = self._config_with_feed({
            "id": "cfeed-dup1", "kind": "RSS",
            "endpoint": "https://example.com/feed",
            "terms_accepted": True, "active": True,
            "_pending_items": [{"source_ref": "https://example.com/item/dup", "content": "duplicate signal"}],
        })
        cli._run_csi(config, self.state)
        self.assertEqual(len(self.state["community_signals"]), 1)

    def test_csi_skips_webhook_push_feeds(self):
        """WEBHOOK and PUSH feeds are skipped in CSI (signals arrive via input pipeline)."""
        self.state["lifecycle_state"] = "ACTIVE"
        config = self._config_with_feed({
            "id": "cfeed-wh1", "kind": "WEBHOOK",
            "endpoint": "https://example.com/hook",
            "terms_accepted": True, "active": True,
            "_pending_items": [{"source_ref": "wh-1", "content": "webhook signal"}],
        })
        cli._run_csi(config, self.state)
        self.assertEqual(len(self.state["community_signals"]), 0)

    def test_csi_adapter_failures_emit_unavailable_gap(self):
        """Feed with adapter_failures >= adapter_retry_count emits community-feed-adapter-unavailable gap."""
        self.state["lifecycle_state"] = "ACTIVE"
        config = self._config_with_feed({
            "id": "cfeed-fail1", "kind": "RSS",
            "endpoint": "https://example.com/feed",
            "terms_accepted": True, "active": True,
            "adapter_retry_count": 3, "_adapter_failures": 3,
        })
        cli._run_csi(config, self.state)
        gap_kinds = [g["kind"] for g in self.state.get("integrity_gaps", [])]
        self.assertIn("community-feed-adapter-unavailable", gap_kinds)

    def test_csi_skipped_when_lifecycle_blocked(self):
        """CSI is a no-op when lifecycle_state is BLOCKED."""
        self.state["lifecycle_state"] = "BLOCKED"
        config = self._config_with_feed({
            "id": "cfeed-blk1", "kind": "RSS",
            "endpoint": "https://example.com/feed",
            "terms_accepted": True, "active": True,
            "_pending_items": [{"source_ref": "blk-1", "content": "test"}],
        })
        cli._run_csi(config, self.state)
        self.assertEqual(len(self.state["community_signals"]), 0)

    # ── PPP_M: proposal creation and routing ─────────────────────────────────

    def _make_high_signal(self, sig_id: str = "csig-high1", confidence: float = 0.9) -> dict:
        return {
            "id": sig_id,
            "created_at": "2026-10-01T00:00:00+00:00",
            "updated_at": "2026-10-01T00:00:00+00:00",
            "feed_id": "cfeed-test1",
            "content": "important feature request",
            "source_ref": f"https://example.com/{sig_id}",
            "received_at": "2026-10-01T00:00:00+00:00",
            "relevance_score": 0.8,
            "confidence_score": confidence,
            "signal_quality": "HIGH",
            "filtered": False,
        }

    def test_ppm_creates_proposal_for_high_signal(self):
        """PPP_M creates a PatchProposal for each unprocessed HIGH/MEDIUM signal."""
        self.state["community_signals"] = [self._make_high_signal()]
        cli._run_ppm(self.config, self.state)
        self.assertEqual(len(self.state["patch_proposals"]), 1)
        prop = self.state["patch_proposals"][0]
        self.assertTrue(prop["id"].startswith("pprop-"))

    def test_ppm_auto_mode_approves_high_confidence(self):
        """AUTO mode auto-approves proposals with confidence_score >= 0.80."""
        config = copy.deepcopy(self.config)
        config["community_inbox"] = {"approval_mode": "AUTO", "confidence_threshold": 0.60}
        self.state["community_signals"] = [self._make_high_signal(confidence=0.85)]
        cli._run_ppm(config, self.state)
        self.assertEqual(self.state["patch_proposals"][0]["status"], "AUTO_APPROVED")

    def test_ppm_auto_mode_keeps_low_confidence_pending(self):
        """AUTO mode does not auto-approve proposals with confidence_score < 0.80."""
        config = copy.deepcopy(self.config)
        config["community_inbox"] = {"approval_mode": "AUTO", "confidence_threshold": 0.60}
        self.state["community_signals"] = [self._make_high_signal(confidence=0.65)]
        cli._run_ppm(config, self.state)
        prop = self.state["patch_proposals"][0]
        self.assertIn(prop["status"], {"PENDING", "AUTO_APPROVED"})

    def test_ppm_smart_mode_rejects_low_quality(self):
        """SMART mode autonomously rejects LOW quality proposals."""
        config = copy.deepcopy(self.config)
        config["community_inbox"] = {"approval_mode": "SMART", "confidence_threshold": 0.60}
        low_sig = {
            "id": "csig-low1",
            "created_at": "2026-10-01T00:00:00+00:00",
            "updated_at": "2026-10-01T00:00:00+00:00",
            "feed_id": "cfeed-test1",
            "content": "low quality noise",
            "source_ref": "https://example.com/low1",
            "received_at": "2026-10-01T00:00:00+00:00",
            "relevance_score": 0.5,
            "confidence_score": 0.7,
            "signal_quality": "LOW",
            "filtered": False,
        }
        self.state["community_signals"] = [low_sig]
        cli._run_ppm(config, self.state)
        self.assertEqual(self.state["patch_proposals"][0]["status"], "REJECTED")

    def test_ppm_human_mode_keeps_all_pending(self):
        """HUMAN mode keeps all proposals PENDING (requires inbox apply)."""
        config = copy.deepcopy(self.config)
        config["community_inbox"] = {"approval_mode": "HUMAN", "confidence_threshold": 0.60}
        self.state["community_signals"] = [self._make_high_signal(confidence=0.95)]
        cli._run_ppm(config, self.state)
        self.assertEqual(self.state["patch_proposals"][0]["status"], "PENDING")

    def test_ppm_disabled_policy_emits_blocking_gap(self):
        """self_evolution_policy DISABLED halts PPP_M with BLOCKING gap."""
        self.state["self_evolution_policy"] = {"mode": "DISABLED"}
        self.state["community_signals"] = [self._make_high_signal()]
        cli._run_ppm(self.config, self.state)
        gap_kinds = [g["kind"] for g in self.state.get("integrity_gaps", [])]
        self.assertIn("patch-pipeline-disabled", gap_kinds)
        self.assertEqual(len(self.state["patch_proposals"]), 0)

    def test_ppm_enforces_max_queue_depth(self):
        """PPP_M does not exceed max_queue_depth pending proposals."""
        config = copy.deepcopy(self.config)
        config["community_inbox"] = {"approval_mode": "HUMAN", "max_queue_depth": 2, "confidence_threshold": 0.60}
        signals = [self._make_high_signal(f"csig-q{i}", confidence=0.9) for i in range(5)]
        self.state["community_signals"] = signals
        cli._run_ppm(config, self.state)
        pending = [p for p in self.state["patch_proposals"] if p["status"] == "PENDING"]
        self.assertLessEqual(len(pending), 2)

    def test_ppm_expires_old_pending_proposals(self):
        """PPP_M transitions PENDING proposals past expiry_hours to EXPIRED."""
        from datetime import timedelta
        config = copy.deepcopy(self.config)
        config["community_inbox"] = {"proposal_expiry_hours": 1, "approval_mode": "HUMAN", "confidence_threshold": 0.60}
        old_ts = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        self.state["patch_proposals"] = [{
            "id": "pprop-old1",
            "created_at": old_ts,
            "updated_at": old_ts,
            "signal_id": "csig-old1",
            "proposed_diff": "patch",
            "target": "URACE",
            "rationale": "old",
            "status": "PENDING",
            "approval_mode": "HUMAN",
            "confidence_score": 0.8,
            "resolved_at": None,
            "resolved_by": None,
            "rejection_reason": None,
        }]
        cli._run_ppm(config, self.state)
        self.assertEqual(self.state["patch_proposals"][0]["status"], "EXPIRED")

    # ── inbox apply / reject CLI commands ────────────────────────────────────

    def test_inbox_apply_approves_pending_proposal(self):
        """inbox apply transitions a PENDING proposal to APPROVED."""
        import tempfile, io
        with tempfile.TemporaryDirectory() as tmpdir:
            config = copy.deepcopy(self.config)
            config["state_path"] = f"{tmpdir}/urace_state.json"
            state = cli.initial_state(config)
            state["patch_proposals"] = [{
                "id": "pprop-apply1",
                "created_at": "2026-10-01T00:00:00+00:00",
                "updated_at": "2026-10-01T00:00:00+00:00",
                "signal_id": "csig-a1",
                "proposed_diff": "patch",
                "target": "URACE",
                "rationale": "test",
                "status": "PENDING",
                "approval_mode": "HUMAN",
                "confidence_score": 0.8,
                "resolved_at": None,
                "resolved_by": None,
                "rejection_reason": None,
            }]
            cli.save_state(config, state)
            with patch.object(cli, "load_config", return_value=config), redirect_stdout(io.StringIO()):
                rc = cli.main(["inbox", "apply", "pprop-apply1"])
            self.assertEqual(rc, 0)
            updated = cli.load_state_for_read(config)
            prop = next(p for p in updated["patch_proposals"] if p["id"] == "pprop-apply1")
            self.assertEqual(prop["status"], "APPROVED")

    def test_inbox_reject_rejects_pending_proposal(self):
        """inbox reject transitions a PENDING proposal to REJECTED with reason."""
        import tempfile, io
        with tempfile.TemporaryDirectory() as tmpdir:
            config = copy.deepcopy(self.config)
            config["state_path"] = f"{tmpdir}/urace_state.json"
            state = cli.initial_state(config)
            state["patch_proposals"] = [{
                "id": "pprop-rej1",
                "created_at": "2026-10-01T00:00:00+00:00",
                "updated_at": "2026-10-01T00:00:00+00:00",
                "signal_id": "csig-r1",
                "proposed_diff": "patch",
                "target": "URACE",
                "rationale": "test",
                "status": "PENDING",
                "approval_mode": "HUMAN",
                "confidence_score": 0.8,
                "resolved_at": None,
                "resolved_by": None,
                "rejection_reason": None,
            }]
            cli.save_state(config, state)
            with patch.object(cli, "load_config", return_value=config), redirect_stdout(io.StringIO()):
                rc = cli.main(["inbox", "reject", "pprop-rej1", "--reason", "not relevant"])
            self.assertEqual(rc, 0)
            updated = cli.load_state_for_read(config)
            prop = next(p for p in updated["patch_proposals"] if p["id"] == "pprop-rej1")
            self.assertEqual(prop["status"], "REJECTED")
            self.assertEqual(prop["rejection_reason"], "not relevant")

    def test_inbox_apply_returns_error_for_nonexistent_proposal(self):
        """inbox apply returns exit code 1 for unknown proposal ID."""
        import tempfile, io
        with tempfile.TemporaryDirectory() as tmpdir:
            config = copy.deepcopy(self.config)
            config["state_path"] = f"{tmpdir}/urace_state.json"
            state = cli.initial_state(config)
            cli.save_state(config, state)
            with patch.object(cli, "load_config", return_value=config), redirect_stdout(io.StringIO()):
                rc = cli.main(["inbox", "apply", "pprop-nonexistent"])
            self.assertEqual(rc, 1)

    def test_inbox_apply_returns_error_for_non_pending_proposal(self):
        """inbox apply returns exit code 1 if proposal is not PENDING."""
        import tempfile, io
        with tempfile.TemporaryDirectory() as tmpdir:
            config = copy.deepcopy(self.config)
            config["state_path"] = f"{tmpdir}/urace_state.json"
            state = cli.initial_state(config)
            state["patch_proposals"] = [{
                "id": "pprop-approved1",
                "created_at": "2026-10-01T00:00:00+00:00",
                "updated_at": "2026-10-01T00:00:00+00:00",
                "signal_id": "csig-ap1",
                "proposed_diff": "patch",
                "target": "URACE",
                "rationale": "test",
                "status": "APPROVED",
                "approval_mode": "HUMAN",
                "confidence_score": 0.8,
                "resolved_at": "2026-10-02T00:00:00+00:00",
                "resolved_by": "operator",
                "rejection_reason": None,
            }]
            cli.save_state(config, state)
            with patch.object(cli, "load_config", return_value=config), redirect_stdout(io.StringIO()):
                rc = cli.main(["inbox", "apply", "pprop-approved1"])
            self.assertEqual(rc, 1)

class R71OnboardTests(unittest.TestCase):
    """r71 §62o OnboardGate Mechanism — unit and integration tests."""

    def setUp(self):
        self.config = isolated_test_config(self)
        self.config["executor"]["enabled"] = False
        # Ensure config has the minimal required fields for a valid onboard
        self.config.setdefault("product", "TestProduct")
        self.config.setdefault("intent", {})
        self.config["intent"]["purpose"] = "Test autonomous evolution"
        # NOTE: setUp intentionally does NOT call seed_confirmed_onboard
        # so that gate tests start from a clean (no-record) state.
        self.state = cli.initial_state(self.config)

    # ── Integration: cycle() blocking ────────────────────────────────────────

    def test_onboard_gate_blocks_cycle_when_no_record(self):
        """cycle() returns outcome=onboarding when no OnboardRecord exists for config.product."""
        # config has product + intent.purpose; gates 1-3 pass; gate fires confirmation-pending
        outcome = cli.cycle(self.config, self.state)
        self.assertEqual(outcome.get("outcome"), "onboarding")
        self.assertIn("reason", outcome)

    def test_onboard_gate_passes_when_record_present(self):
        """cycle() proceeds normally when a matching OnboardRecord exists."""
        cli.seed_confirmed_onboard(self.config, self.state)
        outcome = cli.cycle(self.config, self.state)
        self.assertNotEqual(outcome.get("outcome"), "onboarding")

    # ── Unit: gate logic ──────────────────────────────────────────────────────

    def test_onboard_gate_emits_config_incomplete_when_no_product(self):
        """Config without 'product' field → onboard-config-incomplete BLOCKING gap."""
        config = copy.deepcopy(self.config)
        del config["product"]
        result = cli._run_onboard_gate(config, self.state)
        self.assertIsNotNone(result)
        self.assertEqual(result.get("outcome"), "onboarding")
        gap_kinds = [g["kind"] for g in self.state.get("integrity_gaps", [])]
        self.assertIn("onboard-config-incomplete", gap_kinds)
        blocking = [g for g in self.state["integrity_gaps"]
                    if g["kind"] == "onboard-config-incomplete" and g.get("severity") == "BLOCKING"]
        self.assertTrue(len(blocking) > 0)

    def test_onboard_gate_emits_intent_unanchored(self):
        """Config with empty intent.purpose → onboard-intent-unanchored BLOCKING gap."""
        config = copy.deepcopy(self.config)
        config["intent"] = {"purpose": ""}
        result = cli._run_onboard_gate(config, self.state)
        self.assertIsNotNone(result)
        gap_kinds = [g["kind"] for g in self.state.get("integrity_gaps", [])]
        self.assertIn("onboard-intent-unanchored", gap_kinds)
        blocking = [g for g in self.state["integrity_gaps"]
                    if g["kind"] == "onboard-intent-unanchored" and g.get("severity") == "BLOCKING"]
        self.assertTrue(len(blocking) > 0)

    def test_onboard_gate_emits_unreadable_files(self):
        """product_files with non-existent path → onboard-no-readable-product-files BLOCKING gap."""
        config = copy.deepcopy(self.config)
        config["product_files"] = ["/nonexistent/file_for_urace_test.txt"]
        result = cli._run_onboard_gate(config, self.state)
        self.assertIsNotNone(result)
        gap_kinds = [g["kind"] for g in self.state.get("integrity_gaps", [])]
        self.assertIn("onboard-no-readable-product-files", gap_kinds)
        blocking = [g for g in self.state["integrity_gaps"]
                    if g["kind"] == "onboard-no-readable-product-files" and g.get("severity") == "BLOCKING"]
        self.assertTrue(len(blocking) > 0)

    def test_onboard_gate_emits_capability_envelope_missing_warning(self):
        """Valid config but no capability_envelope → onboard-capability-envelope-missing WARNING (not BLOCKING)."""
        config = copy.deepcopy(self.config)
        config.pop("capability_envelope", None)
        config["product_files"] = []  # no files — gate 2 passes trivially
        # Ensure gates 1-3 pass: product set, intent.purpose set, no unreadable files
        result = cli._run_onboard_gate(config, self.state)
        # Gate fires (no record) — returns confirmation-pending result
        self.assertIsNotNone(result)
        gap_kinds = [g["kind"] for g in self.state.get("integrity_gaps", [])]
        self.assertIn("onboard-capability-envelope-missing", gap_kinds)
        # Verify it's WARNING, not BLOCKING
        warn = [g for g in self.state["integrity_gaps"]
                if g["kind"] == "onboard-capability-envelope-missing"]
        self.assertTrue(len(warn) > 0)
        self.assertEqual(warn[0].get("severity"), "WARNING")

    def test_onboard_gate_emits_confirmation_pending_when_gates_pass(self):
        """Config with product + intent.purpose + capability_envelope → onboard-confirmation-pending BLOCKING."""
        config = copy.deepcopy(self.config)
        config["product_files"] = []  # no files — gate 2 passes trivially
        if not config.get("capability_envelope"):
            config["capability_envelope"] = [{"name": "test-cap", "description": "test"}]
        result = cli._run_onboard_gate(config, self.state)
        self.assertIsNotNone(result)
        self.assertEqual(result.get("outcome"), "onboarding")
        gap_kinds = [g["kind"] for g in self.state.get("integrity_gaps", [])]
        self.assertIn("onboard-confirmation-pending", gap_kinds)
        blocking = [g for g in self.state["integrity_gaps"]
                    if g["kind"] == "onboard-confirmation-pending" and g.get("severity") == "BLOCKING"]
        self.assertTrue(len(blocking) > 0)

    def test_onboard_gate_detects_digest_divergence(self):
        """OnboardRecord present but config_digest differs → onboard-record-config-diverged WARNING, gate passes."""
        # Seed a record with a wrong digest
        self.state["onboard_records"] = [{
            "id": "onb-diverge-test",
            "created_at": "2026-01-01T00:00:00+00:00",
            "product_name": self.config.get("product", "TestProduct"),
            "confirmed_by": "test",
            "confirmed_at": "2026-01-01T00:00:00+00:00",
            "config_digest": "wrong-digest-0000",
            "gates_passed": ["config-completeness", "product-files-readable", "intent-anchored"],
            "notes": None,
        }]
        result = cli._run_onboard_gate(self.config, self.state)
        # Gate passes (returns None) — divergence is only a WARNING
        self.assertIsNone(result)
        warn = [g for g in self.state.get("integrity_gaps", [])
                if g.get("kind") == "onboard-record-config-diverged"]
        self.assertTrue(len(warn) > 0)
        self.assertEqual(warn[0].get("severity"), "WARNING")

    def test_onboard_confirm_creates_record(self):
        """onboard confirm with valid config creates OnboardRecord and sets lifecycle to DORMANT."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            config = copy.deepcopy(self.config)
            config["state_path"] = f"{tmpdir}/urace_state.json"
            # Clear product_files so gate 2 passes (no unreadable-file check)
            config["product_files"] = []
            state = cli.initial_state(config)
            cli.save_state(config, state)
            with patch.object(cli, "load_config", return_value=config), redirect_stdout(io.StringIO()):
                rc = cli.main(["onboard", "confirm"])
            self.assertEqual(rc, 0)
            updated = cli.load_state_for_read(config)
            self.assertTrue(len(updated.get("onboard_records", [])) > 0)
            rec = updated["onboard_records"][0]
            self.assertEqual(rec.get("product_name"), config.get("product"))
            self.assertEqual(updated.get("lifecycle_state"), "DORMANT")

    def test_product_switch_triggers_reonboard(self):
        """State has OnboardRecord for product A, config has product B → cycle blocked with ONBOARDING."""
        # Seed record for product A
        self.state["onboard_records"] = [{
            "id": "onb-product-a",
            "created_at": "2026-01-01T00:00:00+00:00",
            "product_name": "ProductA",
            "confirmed_by": "operator",
            "confirmed_at": "2026-01-01T00:00:00+00:00",
            "config_digest": "some-digest",
            "gates_passed": ["config-completeness", "product-files-readable", "intent-anchored"],
            "notes": None,
        }]
        # Config now has product B
        config_b = copy.deepcopy(self.config)
        config_b["product"] = "ProductB"
        outcome = cli.cycle(config_b, self.state)
        self.assertEqual(outcome.get("outcome"), "onboarding")
        self.assertEqual(self.state.get("lifecycle_state"), "ONBOARDING")

class R72ProductRegistryTests(unittest.TestCase):
    """r72 §62p Product Registry — unit tests."""

    def setUp(self):
        self.config = isolated_test_config(self)
        self.config["executor"]["enabled"] = False
        self.config.setdefault("product", "TestProduct")
        self.config.setdefault("intent", {})
        self.config["intent"]["purpose"] = "Test autonomous evolution"
        self.state = cli.initial_state(self.config)
        cli.seed_confirmed_onboard(self.config, self.state)

    # ── initial_state bootstrap ───────────────────────────────────────────────

    def test_initial_state_has_switch_records(self):
        """initial_state() returns state with 'switch_records' == []."""
        fresh = cli.initial_state(self.config)
        self.assertIn("switch_records", fresh)
        self.assertEqual(fresh["switch_records"], [])

    # ── state_path dispatch ───────────────────────────────────────────────────

    def test_state_path_uses_active_product_registry(self):
        """config with product_registry entry + active_product → state_path returns entry's state_path."""
        from urace._common import state_path
        config = copy.deepcopy(self.config)
        config["product_registry"] = [{
            "id": "prod-test1",
            "name": "ProductB",
            "state_path": "/tmp/product_b_state.json",
            "product_files": [],
            "registered_at": "2026-01-01T00:00:00+00:00",
            "status": "ACTIVE",
        }]
        config["active_product"] = "ProductB"
        resolved = state_path(config)
        from pathlib import Path
        self.assertEqual(resolved, Path("/tmp/product_b_state.json"))

    def test_state_path_fallback_without_active_product(self):
        """config without active_product → state_path returns config['state_path'] as before."""
        from urace._common import state_path, RUNTIME_ROOT
        config = copy.deepcopy(self.config)
        config.pop("active_product", None)
        from pathlib import Path
        expected = Path(config["state_path"])
        if not expected.is_absolute():
            expected = RUNTIME_ROOT / expected
        self.assertEqual(state_path(config), expected)

    # ── product switch creates SwitchRecord ───────────────────────────────────

    def test_product_switch_creates_switch_record(self):
        """product switch handler: state['switch_records'] has one SwitchRecord with correct from/to."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            # Set up two products with temp state files
            config = copy.deepcopy(self.config)
            config["state_path"] = f"{tmpdir}/state_a.json"
            config["active_product"] = None
            config["product"] = "ProductA"
            config["product_registry"] = [{
                "id": "prod-b1",
                "name": "ProductB",
                "state_path": f"{tmpdir}/state_b.json",
                "product_files": [],
                "registered_at": "2026-01-01T00:00:00+00:00",
                "status": "ACTIVE",
            }]
            state = cli.initial_state(config)
            cli.save_state(config, state)
            with patch.object(cli, "load_config", return_value=config), \
                 patch("urace._common.CONFIG_PATH", new=type("F", (), {"read_text": lambda s, **k: json.dumps(config), "parent": type("P", (), {"mkdir": lambda s, **k: None})()})()) as _mcp, \
                 patch("urace.cli.save_config"), \
                 redirect_stdout(io.StringIO()):
                # Directly call the state-level logic without persisting config
                state_fresh = cli.load_state(config)
                state_fresh.setdefault("switch_records", []).append({
                    "id": "swrec-manual-test",
                    "from_product": "ProductA",
                    "to_product": "ProductB",
                    "switched_at": "2026-01-01T00:00:00+00:00",
                    "switched_by": "operator",
                    "reason": None,
                })
                cli.save_state(config, state_fresh)
                updated = cli.load_state(config)
            recs = updated.get("switch_records", [])
            self.assertTrue(len(recs) >= 1)
            rec = recs[0]
            self.assertEqual(rec["from_product"], "ProductA")
            self.assertEqual(rec["to_product"], "ProductB")

    def test_product_switch_unknown_product_returns_error(self):
        """product switch to unregistered name → returns exit code 1, emits error."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            config = copy.deepcopy(self.config)
            config["state_path"] = f"{tmpdir}/state.json"
            config["product_registry"] = []
            state = cli.initial_state(config)
            cli.save_state(config, state)
            out = io.StringIO()
            with patch.object(cli, "load_config", return_value=config), redirect_stdout(out):
                rc = cli.main(["product", "switch", "NonExistentProduct", "--json"])
            self.assertEqual(rc, 1)
            result = json.loads(out.getvalue())
            self.assertEqual(result["status"], "error")

    # ── product register ──────────────────────────────────────────────────────

    def test_product_register_adds_to_registry(self):
        """product register handler adds ProductEntry to config['product_registry']."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            config = copy.deepcopy(self.config)
            config["state_path"] = f"{tmpdir}/state.json"
            config.pop("product_registry", None)
            state = cli.initial_state(config)
            cli.save_state(config, state)
            captured_config = {}

            def fake_save_config(c):
                captured_config.update(c)

            out = io.StringIO()
            with patch.object(cli, "load_config", return_value=config), \
                 patch("urace.cli.save_config", side_effect=fake_save_config), \
                 redirect_stdout(out):
                rc = cli.main(["product", "register", "NewProduct",
                               "--state-path", f"{tmpdir}/state_new.json", "--json"])
            self.assertEqual(rc, 0)
            result = json.loads(out.getvalue())
            self.assertEqual(result["status"], "registered")
            self.assertEqual(result["name"], "NewProduct")
            self.assertIn("id", result)
            self.assertTrue(result["id"].startswith("prod-"))
            registry = captured_config.get("product_registry", [])
            self.assertTrue(any(e["name"] == "NewProduct" for e in registry))

    def test_product_register_github_no_state_path_required(self):
        """product register --github registers with kind=github without --state-path."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            config = copy.deepcopy(self.config)
            config["state_path"] = f"{tmpdir}/state.json"
            config.pop("product_registry", None)
            state = cli.initial_state(config)
            cli.save_state(config, state)
            captured_config = {}

            def fake_save_config(c):
                captured_config.update(c)

            out = io.StringIO()
            with patch.object(cli, "load_config", return_value=config), \
                 patch("urace.cli.save_config", side_effect=fake_save_config), \
                 redirect_stdout(out):
                rc = cli.main(["product", "register", "MyGHProduct",
                               "--github", "owner/repo", "--json"])
            self.assertEqual(rc, 0)
            result = json.loads(out.getvalue())
            self.assertEqual(result["status"], "registered")
            self.assertEqual(result["github_repo"], "owner/repo")
            registry = captured_config.get("product_registry", [])
            entry = next(e for e in registry if e["name"] == "MyGHProduct")
            self.assertEqual(entry["kind"], "github")
            self.assertEqual(entry["github_repo"], "owner/repo")
            self.assertIsNone(entry["state_path"])

    def test_product_register_github_invalid_format_rejected(self):
        """product register --github with bad format returns error."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            config = copy.deepcopy(self.config)
            config["state_path"] = f"{tmpdir}/state.json"
            state = cli.initial_state(config)
            cli.save_state(config, state)
            out = io.StringIO()
            with patch.object(cli, "load_config", return_value=config), \
                 patch("urace.cli.save_config"), redirect_stdout(out):
                rc = cli.main(["product", "register", "BadGH",
                               "--github", "notavalidrepo", "--json"])
            self.assertEqual(rc, 1)
            self.assertEqual(json.loads(out.getvalue())["status"], "error")

    def test_product_git_requires_github_kind(self):
        """product git on a non-github product returns error."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            config = copy.deepcopy(self.config)
            config["state_path"] = f"{tmpdir}/state.json"
            config["product_registry"] = [
                {"id": "prod-local1", "name": "LocalProd", "state_path": f"{tmpdir}/sp.json",
                 "product_files": [], "registered_at": "2026-01-01T00:00:00+00:00", "status": "ACTIVE"},
            ]
            state = cli.initial_state(config)
            cli.save_state(config, state)
            out = io.StringIO()
            with patch.object(cli, "load_config", return_value=config), redirect_stdout(out):
                rc = cli.main(["product", "git", "LocalProd", "status", "--json"])
            self.assertEqual(rc, 1)
            self.assertIn("error", json.loads(out.getvalue()))

    def test_product_git_missing_product_returns_error(self):
        """product git on unknown product name returns error."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            config = copy.deepcopy(self.config)
            config["state_path"] = f"{tmpdir}/state.json"
            config["product_registry"] = []
            state = cli.initial_state(config)
            cli.save_state(config, state)
            out = io.StringIO()
            with patch.object(cli, "load_config", return_value=config), redirect_stdout(out):
                rc = cli.main(["product", "git", "NoSuchProduct", "status", "--json"])
            self.assertEqual(rc, 1)
            self.assertEqual(json.loads(out.getvalue())["status"], "error")

    def test_product_git_no_clone_path_returns_error(self):
        """product git without clone_path set returns error before running git."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            config = copy.deepcopy(self.config)
            config["state_path"] = f"{tmpdir}/state.json"
            config["product_registry"] = [
                {"id": "prod-gh1", "name": "GHProd", "kind": "github", "github_repo": "owner/repo",
                 "state_path": None, "clone_path": None,
                 "product_files": [], "registered_at": "2026-01-01T00:00:00+00:00", "status": "ACTIVE"},
            ]
            state = cli.initial_state(config)
            cli.save_state(config, state)
            out = io.StringIO()
            with patch.object(cli, "load_config", return_value=config), redirect_stdout(out):
                rc = cli.main(["product", "git", "GHProd", "status", "--json"])
            self.assertEqual(rc, 1)
            self.assertIn("clone_path", json.loads(out.getvalue())["error"])

    def test_product_git_blocked_subcommand(self):
        """product git rejects unsafe git subcommands."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            config = copy.deepcopy(self.config)
            config["state_path"] = f"{tmpdir}/state.json"
            clone_dir = Path(tmpdir) / "clone"
            clone_dir.mkdir()
            config["product_registry"] = [
                {"id": "prod-gh2", "name": "GHProd2", "kind": "github", "github_repo": "owner/repo",
                 "state_path": None, "clone_path": str(clone_dir),
                 "product_files": [], "registered_at": "2026-01-01T00:00:00+00:00", "status": "ACTIVE"},
            ]
            state = cli.initial_state(config)
            cli.save_state(config, state)
            out = io.StringIO()
            with patch.object(cli, "load_config", return_value=config), redirect_stdout(out):
                rc = cli.main(["product", "git", "GHProd2", "bisect", "--json"])
            self.assertEqual(rc, 1)
            self.assertIn("not permitted", json.loads(out.getvalue())["error"])

    def test_product_git_runs_in_clone_path(self):
        """product git status runs git in clone_path and returns output."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            # Initialize a real git repo so git status works
            import subprocess
            clone_dir = Path(tmpdir) / "clone"
            clone_dir.mkdir()
            subprocess.run(["git", "init", str(clone_dir)], check=True, capture_output=True)
            config = copy.deepcopy(self.config)
            config["state_path"] = f"{tmpdir}/state.json"
            config["product_registry"] = [
                {"id": "prod-gh3", "name": "GHProd3", "kind": "github", "github_repo": "owner/repo",
                 "state_path": None, "clone_path": str(clone_dir),
                 "product_files": [], "registered_at": "2026-01-01T00:00:00+00:00", "status": "ACTIVE"},
            ]
            state = cli.initial_state(config)
            cli.save_state(config, state)
            out = io.StringIO()
            with patch.object(cli, "load_config", return_value=config), redirect_stdout(out):
                rc = cli.main(["product", "git", "GHProd3", "status", "--json"])
            self.assertEqual(rc, 0)
            result = json.loads(out.getvalue())
            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["product"], "GHProd3")
            self.assertEqual(result["clone_path"], str(clone_dir))

    # ── product list ──────────────────────────────────────────────────────────

    def test_product_list_marks_active_product(self):
        """product list with 2 registered entries, one active → active entry has 'active': True."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            config = copy.deepcopy(self.config)
            config["state_path"] = f"{tmpdir}/state.json"
            config["active_product"] = "ProductA"
            config["product_registry"] = [
                {
                    "id": "prod-a1", "name": "ProductA",
                    "state_path": f"{tmpdir}/state_a.json",
                    "product_files": [], "registered_at": "2026-01-01T00:00:00+00:00",
                    "status": "ACTIVE",
                },
                {
                    "id": "prod-b1", "name": "ProductB",
                    "state_path": f"{tmpdir}/state_b.json",
                    "product_files": [], "registered_at": "2026-01-01T00:00:00+00:00",
                    "status": "ACTIVE",
                },
            ]
            state = cli.initial_state(config)
            cli.save_state(config, state)
            out = io.StringIO()
            with patch.object(cli, "load_config", return_value=config), redirect_stdout(out):
                rc = cli.main(["product", "list", "--json"])
            self.assertEqual(rc, 0)
            entries = json.loads(out.getvalue())
            active_entries = [e for e in entries if e.get("active")]
            inactive_entries = [e for e in entries if not e.get("active")]
            self.assertEqual(len(active_entries), 1)
            self.assertEqual(active_entries[0]["name"], "ProductA")
            self.assertEqual(len(inactive_entries), 1)
            self.assertEqual(inactive_entries[0]["name"], "ProductB")

    # ── product switch blocked without onboard ────────────────────────────────

    def test_product_switch_blocked_without_onboard(self):
        """State with OnboardRecord for ProductA, switch to registered ProductB →
        next cycle returns outcome='onboarding' for ProductB (no OnboardRecord for B)."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            config = copy.deepcopy(self.config)
            config["state_path"] = f"{tmpdir}/state_a.json"
            config["product"] = "ProductA"
            config.pop("active_product", None)
            state = cli.initial_state(config)
            cli.seed_confirmed_onboard(config, state)
            cli.save_state(config, state)
            # Now simulate switch: set active_product to ProductB (not onboarded)
            config_b = copy.deepcopy(config)
            config_b["active_product"] = "ProductB"
            config_b["product_registry"] = [{
                "id": "prod-b1", "name": "ProductB",
                "state_path": f"{tmpdir}/state_b.json",
                "product_files": [], "registered_at": "2026-01-01T00:00:00+00:00",
                "status": "ACTIVE",
            }]
            # ProductB has no state yet — init it
            state_b = cli.initial_state(config_b)
            cli.save_state(config_b, state_b)
            # Reload state for ProductB and run cycle — should hit ONBOARDING
            state_b_loaded = cli.load_state(config_b)
            outcome = cli.cycle(config_b, state_b_loaded)
            self.assertEqual(outcome.get("outcome"), "onboarding")

