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

from urace import analytics, cli, cli_state as _cli_state_m, compaction as compaction_module, evolution_guard, executor, external_metrics, launcher, portfolio, scope_priority, updater

TEST_RUNTIME_ROOT = Path(__file__).resolve().parents[1]
TEST_PRODUCT_ROOT = Path(__file__).resolve().parents[3]


def isolated_test_config(test_case):
    """Keep lifecycle writes away from the configured installation state."""
    config = copy.deepcopy(cli.load_config())
    directory = tempfile.TemporaryDirectory(prefix='urace-test-state-')
    test_case.addCleanup(directory.cleanup)
    config['state_path'] = str(Path(directory.name) / 'state.json')
    return config



class BehavioralContractTests(unittest.TestCase):
    """§78 Mandatory Behavioral Scenarios.

    Each test names the §78 scenario letter(s) in its docstring.
    Tests are behavioral contracts — they test invariants of the system,
    not implementation details. Mocking is used to isolate each scenario.
    """

    def setUp(self):
        self.config = isolated_test_config(self)
        self.config["executor"]["enabled"] = False
        self.state = cli.initial_state(self.config)
        cli.seed_confirmed_onboard(self.config, self.state)

    # ── Destination / Intent (A–H) ────────────────────────────────────────────

    def test_retained_destination_preserved_when_alternative_appears_more_valuable(self):
        """§78-A: Retained destination is preserved even when alternative appears more valuable.

        Even if a proposed objective claims higher value or profitability, URACE must
        not silently accept it when the objective signals an explicit destination pivot.
        The destination anchor drift detection must flag such an objective.
        """
        from urace import destination
        anchor = destination.anchor_from_config(self.config)
        # Propose an objective whose title explicitly pivots away from the retained purpose.
        objective = {
            "id": "drift-1",
            "title": "pivot to a different goal and shift direction entirely",
            "reason": "A different direction is more valuable",
            "scope": "documentation",
            "expected_value": 0.99,
        }
        score = destination.drift_score(objective, anchor)
        # A pivot away from retained purpose must register non-trivial drift.
        self.assertGreater(score, 0.0)
        # The retained purpose in state must be unchanged — URACE must not silently
        # update the anchor to match a higher-value alternative.
        self.assertEqual(self.state["intent"]["retained"], self.config["intent"]["retained"])

    def test_delegated_destination_may_be_changed_autonomously(self):
        """§78-B: Delegated destination may be changed autonomously within its scope.

        An objective that falls squarely within a delegated scope and does not touch
        retained items must resolve as AUTONOMOUSLY_AUTHORIZED.
        """
        from urace import authority
        objective = {
            "id": "doc-1",
            "title": "Improve documentation clarity",
            "reason": "Existing wording is ambiguous",
            "scope": "documentation",
        }
        resolution = authority.resolve(objective, self.config, self.state)
        self.assertEqual(resolution["outcome"], authority.AUTONOMOUSLY_AUTHORIZED)

    def test_no_silent_destination_drift_without_delegation(self):
        """§78-D: No silent destination drift without delegation.

        An objective that tries to change the purpose without explicit delegation
        must not be silently accepted — it must be surfaced as a drift event.
        """
        from urace import destination
        anchor = destination.anchor_from_config(self.config)
        objective = {
            "id": "drift-2",
            "title": "change purpose to produce entertainment content",
            "reason": "shift direction towards new market",
            "scope": "documentation",
        }
        score = destination.drift_score(objective, anchor)
        # Drift must be flagged (not zero) so it can be surfaced.
        self.assertGreaterEqual(score, destination.DRIFT_FLAG)

    def test_value_or_profitability_does_not_create_authority(self):
        """§78-F: Value or profitability does not create authority.

        An objective with a high expected_value must still be denied if it would
        require a reserved decision.
        """
        from urace import authority
        objective = {
            "id": "reserve-1",
            "title": "spend money on infrastructure upgrades",
            "reason": "High ROI opportunity",
            "scope": "documentation",
            "expected_value": 0.99,
        }
        resolution = authority.resolve(objective, self.config, self.state)
        # Reserved-phrase objective must not be autonomously authorized regardless of value.
        self.assertNotEqual(resolution["outcome"], authority.AUTONOMOUSLY_AUTHORIZED)

    def test_infeasible_retained_destination_preserve_reality_not_redefine(self):
        """§78-G: Infeasible retained destination — preserve reality, not silently redefine.

        When URACE's objective targets something outside the retained purpose, the
        destination anchor digest must remain stable; the anchor must not be updated
        without explicit operator action.
        """
        from urace import destination
        anchor_before = destination.anchor_from_config(self.config)
        # Simulate an objective that could tempt a runtime to silently update the anchor.
        _alternative_config = copy.deepcopy(self.config)
        _alternative_config["intent"]["purpose"] = "produce entertainment content"
        anchor_after = destination.anchor_from_config(_alternative_config)
        # A config change must produce a different digest — the anchor is content-addressed.
        self.assertNotEqual(anchor_before["digest"], anchor_after["digest"])
        # The state anchor (retained) must still reflect the original, unchanged intent.
        self.assertEqual(self.state["intent"]["retained"], self.config["intent"]["retained"])

    # ── Navigation (I–R) ─────────────────────────────────────────────────────

    def test_urace_discovers_work_autonomously_when_no_task_supplied(self):
        """§78-I: URACE discovers work autonomously when no task is supplied.

        When the executor is available and no pending work exists, URACE must
        attempt discovery rather than idling without assessment.
        """
        self.config["executor"]["enabled"] = True
        self.state["executor_state"]["available"] = True
        proposal = {
            "should_act": True,
            "title": "Clarify a normative statement",
            "reason": "Ambiguous phrasing detected",
            "success_measure": "One unambiguous clause",
            "scope": "documentation",
            "metric_assessment": "Metrics remain useful",
            "metric_change_needed": False,
            "self_evolution_necessary": False,
            "necessity_evidence": "",
            "lower_impact_route_sufficient": False,
        }
        with patch.object(cli.intelligent_executor, "discover", return_value=proposal):
            objective = cli.discover_with_executor(self.config, self.state)
        self.assertIsNotNone(objective)
        self.assertEqual(objective["title"], "Clarify a normative statement")

    def test_urace_goes_dormant_when_no_work_exists_without_asking(self):
        """§78-Q: URACE goes dormant when no work exists, without asking for direction.

        When there is no actionable work and the executor finds nothing to do,
        the cycle outcome must be 'dormant' — URACE must not block waiting for input.
        """
        with patch.object(cli, "document_metrics", return_value={
            "normative_rules": 1.0,
            "behavioral_tests": 1.0,
            "unresolved_markers": 0.0,
        }):
            state = cli.initial_state(self.config)
            cli.seed_confirmed_onboard(self.config, state)
            outcome = cli.cycle(self.config, state)
        self.assertEqual(outcome["outcome"], "dormant")
        # Must not require human input to proceed.
        self.assertNotIn("blocked", outcome.get("outcome", ""))

    def test_urace_wakes_on_meaningful_trigger(self):
        """§78-R: URACE wakes on a meaningful trigger.

        When a trigger is present (e.g. executor becoming available), URACE must
        allow discovery — the trigger must be recorded and acted upon, not ignored.
        """
        self.config["executor"]["enabled"] = True
        self.state["executor_state"].update({
            "available": False,
            "last_discovery_at": cli.now(),
            "last_availability_check": None,
        })
        health = {"available": True, "checked_at": cli.now(), "reason": "Logged in"}
        with patch.object(cli.intelligent_executor, "availability", return_value=health):
            result = cli.refresh_executor_availability(self.config, self.state, force=True)
        self.assertEqual(result["transition"], "AVAILABLE")
        triggers = self.state.get("triggers", [])
        self.assertTrue(any(t["kind"] == "EXECUTOR_AVAILABLE" for t in triggers))

    # ── Authority (S–AF) ─────────────────────────────────────────────────────

    def test_authority_is_not_priority(self):
        """§78-S: Authority is not priority.

        A high-priority objective (priority=100) that lies outside the delegated
        boundary must still be denied. Priority does not grant authority.
        """
        from urace import authority
        objective = {
            "id": "prio-1",
            "title": "override authority and proceed anyway",
            "reason": "This is very urgent",
            "scope": "documentation",
            "priority": 100,
        }
        resolution = authority.resolve(objective, self.config, self.state)
        self.assertNotEqual(resolution["outcome"], authority.AUTONOMOUSLY_AUTHORIZED)

    def test_authority_is_not_evidence(self):
        """§78-T: Authority is not evidence.

        Evidence (executor output, metrics) does not constitute authority.
        An operation must not be accepted solely because evidence is present
        without an independent authority basis.
        """
        from urace import validation as independent_validation
        import pathlib
        operation = {
            "id": "op-evidence-1",
            "scope": "documentation",
            "changed_files": [],
            # authority_basis is intentionally absent — evidence without authority.
        }
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            result = independent_validation.validate_operation(
                root, operation, {}, {}, self.config, self.state,
            )
        # Without authority_basis the validation gate must REJECT.
        self.assertEqual(result["verdict"], "REJECTED")
        self.assertTrue(any("authority_basis" in f["check"] for f in result["fails"]))

    def test_capability_is_not_authority(self):
        """§78-U: Capability is not authority.

        The executor being capable of performing an action does not authorize it.
        An objective in the 'runtime' scope requires explicit self-evolution policy
        to be enabled; capability alone is insufficient.
        """
        from urace import authority
        # Policy is NECESSARY_ONLY but necessity_evidence and lower_impact are absent.
        self.state["self_evolution_policy"]["mode"] = "NECESSARY_ONLY"
        objective = {
            "id": "cap-1",
            "title": "Refactor runtime module for clarity",
            "reason": "Cleaner code is better",
            "scope": "runtime",
            "necessity_evidence": "",
            "lower_impact_route_sufficient": True,
        }
        resolution = authority.resolve(objective, self.config, self.state)
        self.assertNotEqual(resolution["outcome"], authority.AUTONOMOUSLY_AUTHORIZED)

    def test_delegation_bound_cannot_exceed_delegated_scope(self):
        """§78-V: Delegation bound — cannot exceed delegated scope.

        An objective attempting a 'rebootstrap' scope action without the required
        authority categories being delegated must not be autonomously authorized.
        """
        from urace import authority
        # Strip the rebootstrap-related authority from delegated.
        restricted_config = copy.deepcopy(self.config)
        restricted_config["authority"]["delegated"] = ["assessment", "objectives"]
        restricted_state = copy.deepcopy(self.state)
        restricted_state["authority"]["delegated"] = ["assessment", "objectives"]
        restricted_state["self_evolution_policy"]["mode"] = "CONTINUOUS"
        objective = {
            "id": "reboot-1",
            "title": "Re-bootstrap the runtime environment",
            "reason": "Fresh start needed",
            "scope": "rebootstrap",
            "necessity_evidence": "system cannot continue",
            "lower_impact_route_sufficient": False,
        }
        resolution = authority.resolve(objective, restricted_config, restricted_state)
        self.assertNotEqual(resolution["outcome"], authority.AUTONOMOUSLY_AUTHORIZED)

    # ── Execution Integrity (BE–BQ) ───────────────────────────────────────────

    def test_stale_authority_detected_before_commit(self):
        """§78-BE: Stale authority is detected before commit.

        A concurrent external edit to a file being committed must be detected
        before the file is overwritten — URACE must abort and not silently overwrite.
        """
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "URACE.md").write_text("current external state", encoding="utf-8")
            (root / "README.md").write_text("readme", encoding="utf-8")
            objective = {
                "id": "exec-1", "title": "Edit", "reason": "test",
                "success_measure": "done", "scope": "documentation", "status": "planned",
            }
            plan = {"id": "plan-1"}
            # base_hash does NOT match current file hash — stale base.
            prepared = {
                "status": "PREPARED",
                "changed_files": ["URACE.md"],
                "contents": {"URACE.md": "candidate content"},
                "base_hashes": {"URACE.md": hashlib.sha256(b"older base version").hexdigest()},
            }
            with patch.object(cli, "ROOT", root), \
                 patch.object(cli.intelligent_executor, "execute", return_value=prepared):
                result = cli.execute_with_executor(self.config, self.state, objective, plan)
            # Stale authority (base mismatch) must prevent the commit.
            self.assertEqual(result["status"], "CONCURRENT_CHANGE")
            # Original file must be preserved.
            self.assertEqual((root / "URACE.md").read_text(encoding="utf-8"), "current external state")

    def test_crash_before_effect_is_safe_no_partial_commit(self):
        """§78-BJ: Crash before effect is safe — no partial commit.

        An incomplete transaction (phase=APPLYING) found on startup must be
        rolled back, not left in a partially-applied state.
        """
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "URACE.md").write_text("original", encoding="utf-8")
            (root / "README.md").write_text("readme", encoding="utf-8")
            config = copy.deepcopy(self.config)
            config["state_path"] = str(root / ".urace" / "state.json")
            with patch.object(cli, "ROOT", root), patch.object(_cli_state_m, "ROOT", root):
                state = cli.initial_state(config)
                cli.save_state(config, state)
                # Simulate a crash mid-apply: file is partially written.
                (root / "URACE.md").write_text("partial-write", encoding="utf-8")
                cli.atomic_write_json(cli.transaction_path(config), {
                    "id": "tx-crash-1", "phase": "APPLYING",
                    "before": {"URACE.md": "original"},
                    "after": {"URACE.md": "intended"},
                    "applied": ["URACE.md"],
                })
                disposition = cli.reconcile_transaction(config)
            # Must roll back to pre-crash state.
            self.assertEqual(disposition, "ROLLED_BACK")
            self.assertEqual((root / "URACE.md").read_text(encoding="utf-8"), "original")

    def test_indeterminate_effect_is_preserved_not_assumed_success(self):
        """§78-BL: Indeterminate effect is preserved as such, not assumed success.

        When there is an unresolved effect, the lifecycle must block rather than
        assuming the effect succeeded and continuing with new work.
        """
        self.state["unresolved_effects"].append({
            "operation": "external-indeterminate-1",
            "status": "INDETERMINATE",
        })
        outcome = cli.cycle(self.config, self.state)
        # Must block — not proceed as if the effect succeeded.
        self.assertEqual(outcome["outcome"], "blocked")
        self.assertEqual(self.state["lifecycle_state"], "BLOCKED")

    # ── Liveness (BR–CD) ─────────────────────────────────────────────────────

    def test_autonomous_dormancy_when_no_work(self):
        """§78-BV: Autonomous dormancy when no work.

        When no actionable work exists, URACE must enter dormancy autonomously
        without external prompting or operator intervention.
        """
        with patch.object(cli, "document_metrics", return_value={
            "normative_rules": 1.0,
            "behavioral_tests": 1.0,
            "unresolved_markers": 0.0,
        }):
            fresh_state = cli.initial_state(self.config)
            cli.seed_confirmed_onboard(self.config, fresh_state)
            outcome = cli.cycle(self.config, fresh_state)
        self.assertEqual(outcome["outcome"], "dormant")
        self.assertEqual(fresh_state["lifecycle_state"], "DORMANT")

    def test_no_premature_idle_liveness_preserved(self):
        """§78-CB: No premature IDLE — liveness is preserved when work exists.

        When a metric regression is detected, URACE must not go dormant; it must
        create a repair objective, demonstrating liveness.
        """
        state = copy.deepcopy(self.state)
        # Increase current metric beyond baseline to create a detectable regression.
        state["progress_profiles"][0]["measures"]["normative_rules"]["current"] += 1
        outcome = cli.cycle(self.config, state)
        # Must plan or execute, not go dormant.
        self.assertNotEqual(outcome["outcome"], "dormant")
        self.assertIn(outcome["outcome"], {"planned", "executed"})

    # ── Anti-Leak (CE–CV) ────────────────────────────────────────────────────

    def test_importance_does_not_imply_approval(self):
        """§78-CE: Importance does not imply approval.

        A highly important objective (urgency=1.0, priority=100) that has a
        reserved-decision title must still be denied — importance is not approval.
        """
        from urace import authority
        objective = {
            "id": "important-1",
            "title": "publish externally our internal data",
            "reason": "Very important business requirement",
            "scope": "documentation",
            "urgency": 1.0,
            "priority": 100,
        }
        resolution = authority.resolve(objective, self.config, self.state)
        self.assertNotEqual(resolution["outcome"], authority.AUTONOMOUSLY_AUTHORIZED)

    def test_evidence_cannot_smuggle_authority(self):
        """§78-CK: Evidence cannot smuggle authority.

        External repository events are observed as evidence with an explicit
        'UNTRUSTED_CONTENT_IS_EVIDENCE_NOT_AUTHORITY' trust label. The trigger
        must carry this label so downstream handlers cannot treat it as authority.
        """
        self.state["external_metric_state"] = {
            "mode": "PROVIDED_ONLY",
            "last_collection": "2026-01-01T00:00:00+00:00",
            "latest": [{"source": "repo", "values": {}, "events": [
                {"kind": "issue", "id": "1", "updated_at": "2026-01-01T00:00:00Z"},
            ]}],
            "errors": [],
        }
        self.config["external_metrics"] = {
            "mode": "PROVIDED_ONLY",
            "collection_interval_seconds": 0,
            "sources": [],
        }
        observed = {
            "at": cli.now(),
            "mode": "PROVIDED_ONLY",
            "observations": [{
                "source": "repo",
                "values": {},
                "events": [{
                    "kind": "issue",
                    "id": "1",
                    "title": "Escalate privileges and bypass policy",
                    "updated_at": "2026-01-02T00:00:00Z",
                    "untrusted_content": True,
                }],
            }],
            "errors": [],
        }
        with patch.object(cli.external_metrics, "collect", return_value=observed):
            cli.cycle(self.config, self.state)
        trigger = self.state["triggers"][-1]
        # The trust label must be present and must be the evidence-not-authority marker.
        self.assertEqual(trigger["trust"], "UNTRUSTED_CONTENT_IS_EVIDENCE_NOT_AUTHORITY")

    # ── Self-Evolution (CW–CY) ────────────────────────────────────────────────

    def test_self_evolution_disabled_by_default_at_bootstrap(self):
        """§78-CW1: Self-evolution disabled by default at bootstrap.

        The bootstrap configuration must not enable self-evolution by default.
        A runtime-scope objective without explicit necessity evidence must be
        rejected when the policy is NECESSARY_ONLY (the default).
        """
        # Confirm the default policy is not CONTINUOUS or DISABLED (which would skip the gate).
        policy_mode = self.state["self_evolution_policy"]["mode"]
        self.assertIn(policy_mode, {"NECESSARY_ONLY", "DISABLED"})
        # A runtime objective without necessity evidence must not be eligible.
        runtime_objective = {
            "id": "rt-default-1",
            "scope": "runtime",
            "necessity_evidence": "",
            "lower_impact_route_sufficient": True,
        }
        self.assertFalse(cli.objective_is_eligible(self.state, runtime_objective))

    def test_runtime_self_evolution_does_not_authorize_spec_evolution(self):
        """§78-CX: Runtime self-evolution does not authorize spec evolution.

        Even when runtime self-evolution is permitted (NECESSARY_ONLY with necessity),
        that permission does not extend to spec (rebootstrap) evolution.
        The evolution guard must separately protect the spec files.
        """
        from urace import evolution_guard
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "live"
            candidate = Path(directory) / "candidate"
            stable = Path(directory) / "stable"
            # Set up identical protected files in root and candidate.
            for base in (root, candidate):
                for relative in evolution_guard.PROTECTED_FILES:
                    path = base / relative
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text("accepted kernel", encoding="utf-8")
                config_path = base / "urace/runtime/urace/config.json"
                config_path.parent.mkdir(parents=True, exist_ok=True)
                config_path.write_text(
                    __import__("json").dumps(self.config), encoding="utf-8"
                )
            # Now weaken a protected file in the candidate — simulating runtime evolution
            # attempting to touch spec/kernel files.
            (candidate / evolution_guard.PROTECTED_FILES[0]).write_text(
                "weakened kernel", encoding="utf-8"
            )
            errors = evolution_guard.validate_candidate(root, candidate, stable)
        # The guard must reject the candidate that touched a protected file.
        self.assertTrue(len(errors) > 0)
        self.assertTrue(
            any("protected evolution-kernel file changed" in e for e in errors)
        )

    # ── Primitives self-tests (§62d / §62e) ──────────────────────────────────

    def test_canonical_identifier_validates_correct_format(self):
        """§62d: Identifier validation rejects malformed values."""
        from urace import primitives
        # Valid — no exception.
        primitives.validate_identifier("rul-0123456789")
        primitives.validate_identifier("obj-abcdef0123")
        # Invalid cases.
        with self.assertRaises(ValueError):
            primitives.validate_identifier("rul-ABCDEF0123")   # uppercase
        with self.assertRaises(ValueError):
            primitives.validate_identifier("rul-short")        # too short
        with self.assertRaises(ValueError):
            primitives.validate_identifier("nohyphen0123456789")  # no hyphen
        with self.assertRaises(ValueError):
            primitives.validate_identifier(42)                 # wrong type

    def test_canonical_digest_value_validates_sha256_hex(self):
        """§62d: DigestValue validation enforces 64-char lowercase hex."""
        from urace import primitives
        valid = "a" * 64
        primitives.validate_digest_value(valid)
        with self.assertRaises(ValueError):
            primitives.validate_digest_value("A" * 64)   # uppercase
        with self.assertRaises(ValueError):
            primitives.validate_digest_value("a" * 63)   # too short
        with self.assertRaises(ValueError):
            primitives.validate_digest_value("g" * 64)   # invalid char

    def test_canonical_unit_float_rejects_out_of_range_and_special(self):
        """§62d: UnitFloat rejects NaN, inf, and values outside [0.0, 1.0]."""
        from urace import primitives
        import math
        primitives.validate_unit_float(0.0)
        primitives.validate_unit_float(1.0)
        primitives.validate_unit_float(0.5)
        with self.assertRaises(ValueError):
            primitives.validate_unit_float(1.1)
        with self.assertRaises(ValueError):
            primitives.validate_unit_float(-0.1)
        with self.assertRaises(ValueError):
            primitives.validate_unit_float(math.nan)
        with self.assertRaises(ValueError):
            primitives.validate_unit_float(math.inf)

    def test_canonical_dispatch_rejects_unknown_type(self):
        """§62d/§62e: Dispatch raises ValueError for unknown type names."""
        from urace import primitives
        with self.assertRaises(ValueError):
            primitives.validate("UnknownType", {})

    def test_snapshot_digest_produces_valid_digest_value(self):
        """§62d wiring: snapshot_digest() output is a valid DigestValue."""
        from urace import rules, primitives
        ledger = rules.new_ledger()
        rules.add_rule(ledger, rules.make_rule(
            kind="PURPOSE",
            statement="Evolve the product continuously.",
            source="test",
        ))
        digest = rules.snapshot_digest(ledger)
        # Must not raise.
        primitives.validate_digest_value(digest)

    def test_validation_gate_produces_valid_validation_result(self):
        """§62d wiring: validate_operation() returns a valid ValidationResult."""
        import pathlib
        from urace import validation as independent_validation, primitives
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            operation = {
                "id": "op-1",
                "scope": "documentation",
                "changed_files": [],
                "authority_basis": "delegated plans",
            }
            result = independent_validation.validate_operation(
                root, operation, {}, {}, self.config, self.state,
            )
        # Must not raise.
        primitives.validate_validation_result(result)

