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

from urace import analytics, cli, cli_lifecycle as _cli_lifecycle_m, compaction as compaction_module, evolution_guard, executor, external_metrics, launcher, portfolio, scope_priority, updater

TEST_RUNTIME_ROOT = Path(__file__).resolve().parents[1]
TEST_PRODUCT_ROOT = Path(__file__).resolve().parents[3]


def isolated_test_config(test_case):
    """Keep lifecycle writes away from the configured installation state."""
    config = copy.deepcopy(cli.load_config())
    directory = tempfile.TemporaryDirectory(prefix='urace-test-state-')
    test_case.addCleanup(directory.cleanup)
    config['state_path'] = str(Path(directory.name) / 'state.json')
    return config



class DecisionRecordTests(unittest.TestCase):
    """§45 / §62d: DecisionRecord canonical schema and management."""

    def _executor(self) -> dict:
        return {
            "executor_id": "test-executor",
            "adapter": "test-adapter",
            "capability": "planning",
            "logical_reservation": "none",
            "attempted_executors": [],
        }

    def _digest(self) -> str:
        import hashlib
        return hashlib.sha256(b"{}").hexdigest()

    def test_create_decision_record_produces_valid_record(self):
        """DecisionRecord creation returns a primitives-valid record."""
        from urace import primitives
        from urace import decision_record as dr
        record = dr.create_decision_record(
            kind="OBJECTIVE_SELECTION",
            subject="Select highest-value objective",
            outcome="selected",
            governing_intent_ref="intent-v1",
            state_digest=self._digest(),
            executor=self._executor(),
            uncertainty=0.2,
        )
        self.assertEqual(record["kind"], "OBJECTIVE_SELECTION")
        self.assertEqual(record["provenance_status"], "CURRENT")
        self.assertTrue(record["id"].startswith("dec-"))
        primitives.validate("DecisionRecord", record)

    def test_decision_record_kind_enum_is_enforced(self):
        """DecisionRecord with invalid kind raises ValueError."""
        from urace import decision_record as dr
        with self.assertRaises(ValueError):
            dr.create_decision_record(
                kind="INVALID_KIND",
                subject="x",
                outcome="x",
                governing_intent_ref="v1",
                state_digest=self._digest(),
                executor=self._executor(),
            )

    def test_flag_provenance_revised_sets_fields(self):
        """flag_provenance_revised produces PROVENANCE_REVISED record with notice."""
        from urace import primitives
        from urace import decision_record as dr
        record = dr.create_decision_record(
            kind="OPERATION_AUTHORIZATION",
            subject="Authorize write",
            outcome="authorized",
            governing_intent_ref="intent-v1",
            state_digest=self._digest(),
            executor=self._executor(),
        )
        revised = dr.flag_provenance_revised(record, "Primary evidence was retracted")
        self.assertEqual(revised["provenance_status"], "PROVENANCE_REVISED")
        self.assertEqual(revised["revision_notice"], "Primary evidence was retracted")
        primitives.validate("DecisionRecord", revised)

    def test_provenance_revised_requires_notice(self):
        """DecisionRecord with PROVENANCE_REVISED and no revision_notice is invalid."""
        from urace import primitives
        bad = {
            "id": "dec-abcdef1234",
            "kind": "OBJECTIVE_SELECTION",
            "subject": "x",
            "outcome": "x",
            "governing_intent_ref": "v1",
            "state_digest": self._digest(),
            "executor": self._executor(),
            "provenance_status": "PROVENANCE_REVISED",
            "decided_at": "2025-01-01T00:00:00+00:00",
        }
        with self.assertRaises(ValueError):
            primitives.validate("DecisionRecord", bad)

    def test_save_and_find_decision_record(self):
        """save_decision_record and find_by_id work against state dict."""
        from urace import decision_record as dr
        state: dict = {}
        record = dr.create_decision_record(
            kind="CHECKPOINT_ACCEPTANCE",
            subject="Accept increment",
            outcome="accepted",
            governing_intent_ref="intent-v1",
            state_digest=self._digest(),
            executor=self._executor(),
        )
        dr.save_decision_record(state, record)
        found = dr.find_by_id(state, record["id"])
        self.assertIsNotNone(found)
        self.assertEqual(found["id"], record["id"])

    def test_alternative_considered_rejects_empty_rejected_why(self):
        """AlternativeConsidered with empty rejected_why fails validation."""
        from urace import primitives
        bad = {"description": "alt path", "rejected_why": ""}
        with self.assertRaises(ValueError):
            primitives.validate("AlternativeConsidered", bad)

class CompactionTests(unittest.TestCase):
    """§62f: Compaction and Retention system."""

    def _sample_records(self, n: int) -> list[dict]:
        import datetime
        return [
            {"id": f"rec-{i:010x}", "at": datetime.datetime.now().isoformat(), "value": i}
            for i in range(n)
        ]

    def test_retention_policy_requires_at_least_one_threshold(self):
        """RetentionPolicy with neither max_entries nor max_age_days is invalid."""
        from urace import primitives
        bad = {"id": "rtp-1234567890", "target_field": "foo", "compaction_mode": "ARCHIVE",
               "archive_subpath": "archives/foo"}
        with self.assertRaises(ValueError):
            primitives.validate("RetentionPolicy", bad)

    def test_retention_policy_archive_requires_archive_subpath(self):
        """RetentionPolicy with mode ARCHIVE and no archive_subpath is invalid."""
        from urace import primitives
        bad = {"id": "rtp-1234567890", "target_field": "foo",
               "compaction_mode": "ARCHIVE", "max_entries": 10}
        with self.assertRaises(ValueError):
            primitives.validate("RetentionPolicy", bad)

    def test_compaction_summary_validates_correctly(self):
        """A well-formed CompactionSummary passes validation."""
        import hashlib
        from urace import primitives
        summary = {
            "compaction_event_id": "cmp-abcdef1234",
            "record_count": 50,
            "time_range": {"from": "2025-01-01T00:00:00+00:00", "to": "2025-06-01T00:00:00+00:00"},
            "original_digest": hashlib.sha256(b"test").hexdigest(),
            "is_decompactable": True,
        }
        primitives.validate("CompactionSummary", summary)

    def test_archive_mode_compaction_produces_summary_and_archive(self):
        """ARCHIVE mode compact_field writes archive file and inserts CompactionSummary."""
        import tempfile
        from urace import primitives
        from urace.compaction import CompactionEngine
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = CompactionEngine(tmpdir)
            state = {"executor_state": {"failures": self._sample_records(600)}}
            policy = {
                "id": "rtp-a1b2c3d4e5",
                "target_field": "executor_state.failures",
                "compaction_mode": "ARCHIVE",
                "max_entries": 500,
                "archive_subpath": "archives/executor-failures",
            }
            summary, event = engine.compact_field(
                state, "executor_state.failures", policy, "inp-a1b2c3d4e5"
            )
            failures = state["executor_state"]["failures"]
            self.assertIsInstance(failures[0], dict)
            self.assertEqual(failures[0].get("compaction_event_id"), event["id"])
            self.assertEqual(summary["is_decompactable"], True)
            primitives.validate("CompactionSummary", summary)
            primitives.validate("CompactionEvent", event)

    def test_rolling_eviction_compaction_has_no_archive(self):
        """ROLLING_EVICTION compact_field discards eligibles with no archive."""
        import tempfile
        from urace import primitives
        from urace.compaction import CompactionEngine
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = CompactionEngine(tmpdir)
            state = {"external_metric_state": {"latest": self._sample_records(1200)}}
            policy = {
                "id": "rtp-b1c2d3e4f5",
                "target_field": "external_metric_state.latest",
                "compaction_mode": "ROLLING_EVICTION",
                "max_entries": 1000,
            }
            summary, event = engine.compact_field(
                state, "external_metric_state.latest", policy, "inp-b1c2d3e4f5"
            )
            self.assertEqual(summary["is_decompactable"], False)
            self.assertNotIn("archive_path", event)
            primitives.validate("CompactionSummary", summary)

    def test_compaction_prohibited_field_raises(self):
        """compact_field raises ValueError for a PROHIBITED field."""
        import tempfile
        from urace.compaction import CompactionEngine
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = CompactionEngine(tmpdir)
            state = {"change_history": self._sample_records(10)}
            policy = {
                "id": "rtp-c1d2e3f4a5",
                "target_field": "change_history",
                "compaction_mode": "PROHIBITED",
                "max_entries": 1,
            }
            with self.assertRaises(ValueError):
                engine.compact_field(state, "change_history", policy, "inp-c1d2e3f4a5")

    def test_decompact_restores_original_records(self):
        """decompact_field restores originals and verifies digest."""
        import tempfile
        from urace.compaction import CompactionEngine
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = CompactionEngine(tmpdir)
            originals = self._sample_records(600)
            state = {"executor_state": {"failures": list(originals)}}
            policy = {
                "id": "rtp-d1e2f3a4b5",
                "target_field": "executor_state.failures",
                "compaction_mode": "ARCHIVE",
                "max_entries": 500,
                "archive_subpath": "archives/executor-failures",
            }
            _, event = engine.compact_field(
                state, "executor_state.failures", policy, "inp-d1e2f3a4b5"
            )
            engine.decompact_field(
                state, "executor_state.failures", event["id"], "inp-e1f2a3b4c5"
            )
            restored = state["executor_state"]["failures"]
            self.assertEqual(len(restored), len(originals))
            self.assertEqual(restored[0]["id"], originals[0]["id"])

    def test_compaction_manifest_version_invariant(self):
        """CompactionManifest with version != len(events) fails validation."""
        import hashlib
        from urace import primitives
        bad_event = {
            "id": "cmp-abcdef1234",
            "target_state_path": "state.json",
            "target_field": "failures",
            "compacted_at": "2025-01-01T00:00:00+00:00",
            "record_count_before": 10,
            "record_count_after": 1,
            "compaction_mode": "ROLLING_EVICTION",
            "original_digest": hashlib.sha256(b"x").hexdigest(),
            "authorized_by": "inp-a1b2c3d4e5",
        }
        bad_manifest = {
            "id": "man-abcdef1234",
            "version": 99,
            "updated_at": "2025-01-01T00:00:00+00:00",
            "events": [bad_event],
        }
        with self.assertRaises(ValueError):
            primitives.validate("CompactionManifest", bad_manifest)

    def test_dry_run_reports_eligibles_without_committing(self):
        """dry_run returns report without modifying state."""
        import tempfile
        from urace.compaction import CompactionEngine
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = CompactionEngine(tmpdir)
            state = {"executor_state": {"failures": self._sample_records(600)}}
            policy = {
                "id": "rtp-f1a2b3c4d5",
                "target_field": "executor_state.failures",
                "compaction_mode": "ARCHIVE",
                "max_entries": 500,
                "archive_subpath": "archives/executor-failures",
            }
            report = engine.dry_run(state, "executor_state.failures", policy)
            self.assertTrue(report["would_compact"])
            self.assertEqual(report["eligible_count"], 100)
            self.assertEqual(len(state["executor_state"]["failures"]), 600)

class CognitiveResumeContextTests(unittest.TestCase):
    """§62e: CognitiveResumeContext generation, staleness, and injection."""

    def _state(self) -> dict:
        return {"lifecycle_status": "ASSESSING", "objectives": [], "operations": []}

    def test_generate_produces_valid_crc(self):
        """generate() returns a primitives-valid CognitiveResumeContext."""
        from urace import primitives
        from urace import cognitive_resume as crc_mod
        state = self._state()
        crc = crc_mod.generate(state)
        self.assertTrue(crc["id"].startswith("crc-"))
        self.assertEqual(crc["cycle_phase"], "ASSESSING")
        self.assertIsInstance(crc["pending_validations"], list)
        self.assertIsInstance(crc["blocking_gaps"], list)
        primitives.validate("CognitiveResumeContext", crc)

    def test_stale_crc_detected_when_state_changes(self):
        """is_stale returns True after state is mutated."""
        from urace import cognitive_resume as crc_mod
        state = self._state()
        crc = crc_mod.generate(state)
        self.assertFalse(crc_mod.is_stale(crc, state))
        state["new_field"] = "changed"
        self.assertTrue(crc_mod.is_stale(crc, state))

    def test_build_executor_context_raises_when_stale(self):
        """build_executor_context raises ValueError for a stale CRC."""
        from urace import cognitive_resume as crc_mod
        state = self._state()
        crc = crc_mod.generate(state)
        state["mutated"] = True
        with self.assertRaises(ValueError):
            crc_mod.build_executor_context(crc, state)

    def test_build_executor_context_includes_required_keys(self):
        """build_executor_context includes cycle_phase, blocking_gaps, pending_validations."""
        from urace import cognitive_resume as crc_mod
        state = self._state()
        crc = crc_mod.generate(state)
        ctx = crc_mod.build_executor_context(crc, state)
        self.assertIn("cycle_phase", ctx)
        self.assertIn("blocking_gaps", ctx)
        self.assertIn("pending_validations", ctx)
        self.assertIn("state_digest", ctx)

    def test_persist_and_reload_crc(self):
        """save + load round-trips a CRC."""
        import tempfile
        from urace import cognitive_resume as crc_mod
        state = self._state()
        crc = crc_mod.generate(state)
        with tempfile.TemporaryDirectory() as tmpdir:
            crc_mod.save(tmpdir, crc)
            loaded = crc_mod.load(tmpdir)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["id"], crc["id"])

    def test_load_or_generate_regenerates_stale_crc(self):
        """load_or_generate returns fresh CRC when persisted one is stale."""
        import tempfile
        from urace import cognitive_resume as crc_mod
        state = self._state()
        with tempfile.TemporaryDirectory() as tmpdir:
            old_crc = crc_mod.generate(state)
            crc_mod.save(tmpdir, old_crc)
            state["mutated"] = True
            fresh = crc_mod.load_or_generate(tmpdir, state)
        self.assertNotEqual(fresh["id"], old_crc["id"])
        self.assertFalse(crc_mod.is_stale(fresh, state))

    def test_crc_phase_reflects_lifecycle_status(self):
        """CRC cycle_phase maps lifecycle_state correctly."""
        from urace import cognitive_resume as crc_mod
        for status, expected_phase in [
            ("ACTIVE", "EXECUTING"),
            ("DORMANT", "DORMANT"),
            ("VALIDATING", "VALIDATING"),
            ("PLANNING", "PLANNING"),
            ("WAITING_FOR_CAPACITY", "DORMANT"),
            ("WAITING_FOR_AUTHORITATIVE_DECISION", "DORMANT"),
        ]:
            state = {"lifecycle_state": status}
            crc = crc_mod.generate(state)
            self.assertEqual(crc["cycle_phase"], expected_phase, f"status={status}")

class ReasoningStepTests(unittest.TestCase):
    """§62d r3: ReasoningStep and OutcomeFeedback canonical schemas."""

    def _executor(self) -> dict:
        return {
            "executor_id": "test-executor",
            "adapter": "test-adapter",
            "capability": "planning",
            "logical_reservation": "none",
            "attempted_executors": [],
        }

    def _digest(self) -> str:
        import hashlib
        return hashlib.sha256(b"{}").hexdigest()

    def test_reasoning_step_valid(self):
        """A well-formed ReasoningStep passes validation."""
        from urace import primitives
        step = {
            "step_index": 0,
            "kind": "OBSERVATION",
            "description": "Observed that rate limit is 1000 req/min",
            "outcome": "PASS",
        }
        primitives.validate("ReasoningStep", step)

    def test_reasoning_step_invalid_kind(self):
        """ReasoningStep with unknown kind raises ValueError."""
        from urace import primitives
        bad = {"step_index": 0, "kind": "UNKNOWN", "description": "x", "outcome": "PASS"}
        with self.assertRaises(ValueError):
            primitives.validate("ReasoningStep", bad)

    def test_reasoning_step_negative_index(self):
        """ReasoningStep with step_index < 0 raises ValueError."""
        from urace import primitives
        bad = {"step_index": -1, "kind": "OBSERVATION", "description": "x", "outcome": "PASS"}
        with self.assertRaises(ValueError):
            primitives.validate("ReasoningStep", bad)

    def test_outcome_feedback_valid_materialized(self):
        """OutcomeFeedback with materialized=True passes validation."""
        from urace import primitives
        fb = {
            "observed_at": "2025-10-10T12:00:00+00:00",
            "materialized": True,
            "triggers_revision": False,
        }
        primitives.validate("OutcomeFeedback", fb)

    def test_outcome_feedback_not_materialized_requires_divergence_note(self):
        """OutcomeFeedback with materialized=False and no divergence_note raises ValueError."""
        from urace import primitives
        bad = {
            "observed_at": "2025-10-10T12:00:00+00:00",
            "materialized": False,
            "triggers_revision": True,
        }
        with self.assertRaises(ValueError):
            primitives.validate("OutcomeFeedback", bad)

    def test_decision_record_with_reasoning_steps_passes(self):
        """DecisionRecord with valid reasoning_steps passes validation."""
        from urace import primitives
        from urace import decision_record as dr
        record = dr.create_decision_record(
            kind="NAVIGATION_ASSESSMENT",
            subject="Evaluate routing approach",
            outcome="selected direct path",
            governing_intent_ref="intent-v1",
            state_digest=self._digest(),
            executor=self._executor(),
            reasoning_steps=[
                {"step_index": 0, "kind": "OBSERVATION", "description": "Observed A", "outcome": "PASS"},
                {"step_index": 1, "kind": "INFERENCE", "description": "Inferred B from A", "outcome": "PASS"},
            ],
        )
        primitives.validate("DecisionRecord", record)
        self.assertEqual(len(record["reasoning_steps"]), 2)

    def test_decision_record_noncontiguous_steps_raises(self):
        """DecisionRecord with gap in step_index raises ValueError."""
        from urace import primitives
        bad_record = {
            "id": "dec-abcdef1234",
            "kind": "OBJECTIVE_SELECTION",
            "subject": "x",
            "outcome": "x",
            "governing_intent_ref": "v1",
            "state_digest": self._digest(),
            "executor": self._executor(),
            "provenance_status": "CURRENT",
            "decided_at": "2025-01-01T00:00:00+00:00",
            "reasoning_steps": [
                {"step_index": 0, "kind": "OBSERVATION", "description": "x", "outcome": "PASS"},
                {"step_index": 2, "kind": "INFERENCE", "description": "y", "outcome": "PASS"},  # gap!
            ],
        }
        with self.assertRaises(ValueError):
            primitives.validate("DecisionRecord", bad_record)

    def test_attach_outcome_feedback_auto_revises_provenance(self):
        """attach_outcome_feedback with triggers_revision=True sets PROVENANCE_REVISED."""
        from urace import decision_record as dr
        record = dr.create_decision_record(
            kind="OBJECTIVE_SELECTION",
            subject="x",
            outcome="selected",
            governing_intent_ref="v1",
            state_digest=self._digest(),
            executor=self._executor(),
        )
        updated = dr.attach_outcome_feedback(
            record,
            observed_at="2025-10-10T12:00:00+00:00",
            materialized=False,
            triggers_revision=True,
            divergence_note="Outcome diverged: target API was unavailable",
        )
        self.assertEqual(updated["provenance_status"], "PROVENANCE_REVISED")
        self.assertIn("revision_notice", updated)

    def test_decision_record_with_prior_refs_and_completeness(self):
        """DecisionRecord with prior_decision_refs and completeness passes validation."""
        from urace import primitives
        from urace import decision_record as dr
        record = dr.create_decision_record(
            kind="OPERATION_AUTHORIZATION",
            subject="Authorize DB migration",
            outcome="authorized",
            governing_intent_ref="intent-v2",
            state_digest=self._digest(),
            executor=self._executor(),
            prior_decision_refs=["dec-aabbccddee", "dec-11223344ff"],
            completeness=0.85,
        )
        primitives.validate("DecisionRecord", record)
        self.assertEqual(record["completeness"], 0.85)
        self.assertEqual(len(record["prior_decision_refs"]), 2)

class ReasoningChainTests(unittest.TestCase):
    """§62g: Justification System — reasoning chain traversal."""

    def _executor(self) -> dict:
        return {
            "executor_id": "test-executor",
            "adapter": "test-adapter",
            "capability": "planning",
            "logical_reservation": "none",
            "attempted_executors": [],
        }

    def _digest(self) -> str:
        import hashlib
        return hashlib.sha256(b"{}").hexdigest()

    def _make_record(self, dr_module, *, kind="OBJECTIVE_SELECTION",
                     prior_refs=None) -> dict:
        kwargs = dict(
            kind=kind, subject="test", outcome="ok",
            governing_intent_ref="v1", state_digest=self._digest(),
            executor=self._executor(),
        )
        if prior_refs:
            kwargs["prior_decision_refs"] = prior_refs
        return dr_module.create_decision_record(**kwargs)

    def test_traverse_single_node(self):
        """traverse_reasoning_chain on a root-only record returns one node."""
        from urace import decision_record as dr
        state: dict = {}
        record = self._make_record(dr)
        dr.save_decision_record(state, record)
        chain = dr.traverse_reasoning_chain(state, record["id"])
        self.assertEqual(len(chain), 1)
        self.assertEqual(chain[0]["id"], record["id"])
        self.assertFalse(chain[0].get("is_compacted", False))

    def test_traverse_two_levels(self):
        """traverse_reasoning_chain follows prior_decision_refs."""
        from urace import decision_record as dr
        state: dict = {}
        parent = self._make_record(dr)
        dr.save_decision_record(state, parent)
        child = self._make_record(dr, prior_refs=[parent["id"]])
        dr.save_decision_record(state, child)
        chain = dr.traverse_reasoning_chain(state, child["id"])
        ids = [n["id"] for n in chain]
        self.assertIn(child["id"], ids)
        self.assertIn(parent["id"], ids)
        self.assertEqual(chain[0]["id"], child["id"])
        self.assertEqual(chain[0]["depth"], 0)
        self.assertEqual(chain[1]["depth"], 1)

    def test_traverse_depth_limit(self):
        """depth=0 returns only the root node."""
        from urace import decision_record as dr
        state: dict = {}
        parent = self._make_record(dr)
        dr.save_decision_record(state, parent)
        child = self._make_record(dr, prior_refs=[parent["id"]])
        dr.save_decision_record(state, child)
        chain = dr.traverse_reasoning_chain(state, child["id"], max_depth=0)
        self.assertEqual(len(chain), 1)
        self.assertEqual(chain[0]["id"], child["id"])

    def test_traverse_missing_root_raises(self):
        """traverse_reasoning_chain raises ValueError for unknown root id."""
        from urace import decision_record as dr
        state: dict = {}
        with self.assertRaises(ValueError):
            dr.traverse_reasoning_chain(state, "dec-notexist123")

class CompactionIndexTests(unittest.TestCase):
    """§62e r3: CompactionIndex and ArchiveAmendment."""

    def _sample_records(self, n: int) -> list[dict]:
        return [
            {
                "id": f"dec-{i:010x}",
                "kind": "OBJECTIVE_SELECTION" if i % 2 == 0 else "OPERATION_AUTHORIZATION",
                "decided_at": f"2025-0{1 + (i % 9):01d}-01T00:00:00+00:00",
                "subject": f"record {i}",
                "value": i,
            }
            for i in range(n)
        ]

    def _executor(self) -> dict:
        return {
            "executor_id": "test-executor",
            "adapter": "test-adapter",
            "capability": "planning",
            "logical_reservation": "none",
            "attempted_executors": [],
        }

    def _digest(self) -> str:
        import hashlib
        return hashlib.sha256(b"{}").hexdigest()

    def test_compact_field_produces_record_ids_and_kinds(self):
        """compact_field populates record_ids and kinds in CompactionSummary."""
        import tempfile
        from urace.compaction import CompactionEngine
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = CompactionEngine(tmpdir)
            records = self._sample_records(600)
            state = {"decision_records": records}
            policy = {
                "id": "rtp-a1b2c3d4e5",
                "target_field": "decision_records",
                "compaction_mode": "ARCHIVE",
                "max_entries": 500,
                "archive_subpath": "archives/decision-records",
            }
            summary, _ = engine.compact_field(state, "decision_records", policy, "inp-a1b2c3d4e5")
            self.assertIn("record_ids", summary)
            self.assertIn("kinds", summary)
            self.assertEqual(len(summary["record_ids"]), 100)
            self.assertIn("OBJECTIVE_SELECTION", summary["kinds"])

    def test_index_file_written_on_archive_compaction(self):
        """An .idx.json file is written alongside the archive."""
        import tempfile
        from pathlib import Path
        from urace.compaction import CompactionEngine
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = CompactionEngine(tmpdir)
            records = self._sample_records(600)
            state = {"decision_records": records}
            policy = {
                "id": "rtp-b1c2d3e4f5",
                "target_field": "decision_records",
                "compaction_mode": "ARCHIVE",
                "max_entries": 500,
                "archive_subpath": "archives/decision-records",
            }
            _, event = engine.compact_field(state, "decision_records", policy, "inp-b1c2d3e4f5")
            archive_p = Path(tmpdir) / event["archive_path"]
            idx_p = archive_p.with_suffix(".idx.json")
            self.assertTrue(idx_p.exists(), "index file should exist after ARCHIVE compaction")
            import json
            with idx_p.open() as f:
                idx = json.load(f)
            self.assertEqual(idx["record_count"], 100)
            self.assertIn("id_to_offset", idx)

    def test_decompact_record_extracts_single_record(self):
        """decompact_record returns a single record without modifying live list."""
        import tempfile
        from urace.compaction import CompactionEngine
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = CompactionEngine(tmpdir)
            records = self._sample_records(600)
            state = {"decision_records": list(records)}
            target_id = records[0]["id"]
            policy = {
                "id": "rtp-c1d2e3f4a5",
                "target_field": "decision_records",
                "compaction_mode": "ARCHIVE",
                "max_entries": 500,
                "archive_subpath": "archives/decision-records",
            }
            _, event = engine.compact_field(state, "decision_records", policy, "inp-c1d2e3f4a5")
            live_count_before = len(state["decision_records"])
            found = engine.decompact_record(event["id"], target_id)
            self.assertEqual(found["id"], target_id)
            self.assertEqual(len(state["decision_records"]), live_count_before,
                             "live list must not be modified by decompact_record")

    def test_archive_amendment_appends_log(self):
        """amend_archived_record writes an ArchiveAmendment to .amendments.jsonl."""
        import tempfile
        from pathlib import Path
        from urace.compaction import CompactionEngine, load_amendments
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = CompactionEngine(tmpdir)
            records = self._sample_records(600)
            state = {"decision_records": list(records)}
            target_id = records[0]["id"]
            policy = {
                "id": "rtp-d1e2f3a4b5",
                "target_field": "decision_records",
                "compaction_mode": "ARCHIVE",
                "max_entries": 500,
                "archive_subpath": "archives/decision-records",
            }
            _, event = engine.compact_field(state, "decision_records", policy, "inp-d1e2f3a4b5")
            archive_p = Path(tmpdir) / event["archive_path"]
            amendment = engine.amend_archived_record(
                compaction_event_id=event["id"],
                record_id=target_id,
                amendment_kind="CUSTOM",
                amendment_note="Test amendment note",
                authorized_by="operator:test",
                apply_fn=lambda r: {**r, "amended_flag": True},
            )
            self.assertTrue(amendment["id"].startswith("amd-"))
            amendments = load_amendments(archive_p)
            self.assertEqual(len(amendments), 1)
            self.assertEqual(amendments[0]["record_id"], target_id)

    def test_compaction_index_validates_correctly(self):
        """A well-formed CompactionIndex passes primitives validation."""
        from urace import primitives
        idx = {
            "compaction_event_id": "cmp-abcdef1234",
            "archive_path": "/path/to/archive.json",
            "generated_at": "2025-10-10T00:00:00+00:00",
            "record_count": 3,
            "id_to_offset": {"dec-a1b2c3d4e5": 0, "dec-b2c3d4e5f6": 1, "dec-c3d4e5f6a7": 2},
            "kind_to_ids": {"OBJECTIVE_SELECTION": ["dec-a1b2c3d4e5", "dec-b2c3d4e5f6"],
                            "OPERATION_AUTHORIZATION": ["dec-c3d4e5f6a7"]},
        }
        primitives.validate("CompactionIndex", idx)

    def test_archive_amendment_validates_correctly(self):
        """A well-formed ArchiveAmendment passes primitives validation."""
        import hashlib
        from urace import primitives
        amd = {
            "id": "amd-1234567890",
            "archive_path": "/path/to/archive.json",
            "record_id": "dec-abcdef1234",
            "amended_at": "2025-10-10T00:00:00+00:00",
            "amendment_kind": "PROVENANCE_REVISED",
            "amendment_note": "Evidence was retracted",
            "authorized_by": "operator:test",
            "before_digest": hashlib.sha256(b"before").hexdigest(),
            "after_digest": hashlib.sha256(b"after").hexdigest(),
        }
        primitives.validate("ArchiveAmendment", amd)

    def test_age_based_eligibility(self):
        """_eligible_indices uses max_age_days to mark old records eligible."""
        import datetime
        from urace.compaction import CompactionEngine
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = CompactionEngine(tmpdir)
        old_ts = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=40)).isoformat()
        new_ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
        records = [
            {"id": f"rec-{'a' * 10}", "decided_at": old_ts},
            {"id": f"rec-{'b' * 10}", "decided_at": new_ts},
        ]
        policy = {"max_age_days": 30, "compaction_mode": "ARCHIVE"}
        eligible = CompactionEngine._eligible_indices(records, policy)
        self.assertEqual(eligible, [0], "only the old record should be eligible")

class ExecutorRobustnessTests(unittest.TestCase):
    """Tests for executor hardening fixes applied in r4."""

    def test_discovery_schema_required_includes_all_properties(self):
        schema = executor.DISCOVERY_SCHEMA
        props = set(schema["properties"].keys())
        required = set(schema["required"])
        missing = props - required
        self.assertEqual(missing, set(), f"DISCOVERY_SCHEMA properties not in required: {missing}")

    def test_discovery_schema_additionalProperties_false(self):
        self.assertFalse(executor.DISCOVERY_SCHEMA.get("additionalProperties", True))

    def test_classify_auth_failure_detects_401(self):
        settings = {"capacity_fallback_seconds": 3600}
        result = executor.classify_auth_failure("ERROR: 401 Unauthorized", settings)
        self.assertIsNotNone(result)
        self.assertEqual(result.category, "EXECUTOR_AUTH_UNAVAILABLE")

    def test_classify_auth_failure_detects_model_not_supported(self):
        settings = {"capacity_fallback_seconds": 3600}
        result = executor.classify_auth_failure(
            "The model is not supported when using Codex with a ChatGPT account", settings
        )
        self.assertIsNotNone(result)
        self.assertEqual(result.category, "EXECUTOR_AUTH_UNAVAILABLE")

    def test_classify_auth_failure_returns_none_for_schema_error(self):
        settings = {}
        result = executor.classify_auth_failure("invalid_json_schema: required missing expected_value", settings)
        self.assertIsNone(result)

    def test_classify_auth_failure_returns_none_for_rate_limit(self):
        settings = {}
        result = executor.classify_auth_failure("rate limit exceeded, try again at 10:00 PM", settings)
        self.assertIsNone(result)

    def test_executor_transport_ceiling_zero_limit_no_index_error(self):
        """Provider with limit=0 and empty history must not raise IndexError."""
        from datetime import datetime, timezone

        settings = {"max_executor_calls_per_24h": 0, "capacity_fallback_seconds": 3600}
        pool_state: dict = {}
        provider = {
            "id": "zero-limit-provider",
            "adapter": "codex-cli",
            "capabilities": ["discovery"],
            "max_calls_per_24h": 0,
        }

        with patch("urace.executor.routed_provider_definitions", return_value=[provider]):
            with patch("urace.executor.availability", return_value={"available": False, "checked_at": "x", "reason": "n/a"}):
                try:
                    executor.run_routed_codex(
                        __import__("pathlib").Path("/tmp"),
                        settings,
                        pool_state,
                        "test prompt",
                        None,
                        "read-only",
                        "discovery",
                    )
                    self.fail("expected ExecutorUnavailable")
                except executor.ExecutorUnavailable as exc:
                    self.assertIn(exc.category, {"LOCAL_TRANSPORT_CEILING", "EXECUTOR_POOL_UNAVAILABLE"})
                except IndexError:
                    self.fail("IndexError raised when limit=0 and history is empty")

    def test_portfolio_root_fallback_when_outside_git(self):
        """portfolio.ROOT must be a Path even when evaluated outside a git repo."""
        from urace import portfolio as port_mod
        self.assertIsInstance(port_mod.ROOT, __import__("pathlib").Path)

    def test_classify_transient_network_failure_detects_cfray(self):
        settings = {"transient_network_backoff_seconds": 300}
        result = executor.classify_transient_network_failure(
            "cf-ray: a450e822bc3601a8-GRU, request id: req_xxx\nstream disconnected - retrying sampling request",
            settings,
        )
        self.assertIsNotNone(result)
        self.assertEqual(result.category, "EXECUTOR_TRANSIENT_NETWORK")

    def test_classify_transient_network_failure_detects_stream_disconnected(self):
        settings = {}
        result = executor.classify_transient_network_failure(
            "WARN codex_core::codex: stream disconnected - retrying sampling request (2/5 in 418ms)",
            settings,
        )
        self.assertIsNotNone(result)
        self.assertEqual(result.category, "EXECUTOR_TRANSIENT_NETWORK")

    def test_classify_transient_network_failure_returns_none_for_rate_limit(self):
        settings = {}
        result = executor.classify_transient_network_failure(
            "usage limit reached, try again at 10:00 PM", settings
        )
        self.assertIsNone(result)

    def test_classify_transient_network_failure_returns_none_for_auth(self):
        settings = {}
        result = executor.classify_transient_network_failure(
            "401 Unauthorized: invalid api key", settings
        )
        self.assertIsNone(result)

    def test_classify_transient_network_failure_uses_short_backoff(self):
        """Transient backoff must be configurable and shorter than auth backoff default."""
        settings = {"transient_network_backoff_seconds": 120, "capacity_fallback_seconds": 18000}
        transient = executor.classify_transient_network_failure("stream disconnected", settings)
        auth = executor.classify_auth_failure("401 unauthorized", settings)
        self.assertIsNotNone(transient)
        self.assertIsNotNone(auth)
        from datetime import datetime, timezone
        transient_retry = datetime.fromisoformat(transient.retry_at).timestamp()
        auth_retry = datetime.fromisoformat(auth.retry_at).timestamp()
        self.assertLess(transient_retry, auth_retry)

class SpecAuditTests(unittest.TestCase):
    """Tests for §81 spec structural audit module and cli integration."""

    def _spec_path(self):
        return Path(__file__).parents[3] / "URACE.md"

    def test_audit_produces_correct_section_count(self):
        from urace import spec_audit as sa
        report = sa.audit(self._spec_path())
        self.assertGreaterEqual(report["metadata"]["section_count"], 81)

    def test_audit_fence_parity_even(self):
        from urace import spec_audit as sa
        report = sa.audit(self._spec_path())
        self.assertTrue(report["global_summary"]["fence_parity_even"])

    def test_audit_detects_user_stems(self):
        from urace import spec_audit as sa
        report = sa.audit(self._spec_path())
        stems = report["stem_families"]
        for stem in ("justif", "evidenc", "identif", "reproduc", "veloc", "condit", "confl"):
            self.assertIn(stem, stems, f"stem '{stem}' missing from audit")
            self.assertGreater(stems[stem]["global_count"], 0, f"stem '{stem}' has zero hits")

    def test_audit_stem_variants_are_words_starting_with_stem(self):
        from urace import spec_audit as sa
        report = sa.audit(self._spec_path())
        for stem, data in report["stem_families"].items():
            for variant in data["variants_found"]:
                self.assertTrue(
                    variant.lower().startswith(stem.lower()),
                    f"variant '{variant}' does not start with stem '{stem}'"
                )

    def test_build_summary_contains_required_keys(self):
        from urace import spec_audit as sa
        report = sa.audit(self._spec_path())
        summary = sa.build_summary(report)
        for key in ("spec_version", "section_count", "fence_parity_even", "rfc2119_totals",
                    "high_ambiguity_sections", "top_gap_sections"):
            self.assertIn(key, summary, f"summary missing key '{key}'")

    def test_audit_is_deterministic(self):
        from urace import spec_audit as sa
        spec_path = self._spec_path()
        r1 = sa.audit(spec_path)
        r2 = sa.audit(spec_path)
        self.assertEqual(r1["global_summary"]["rfc2119_totals"], r2["global_summary"]["rfc2119_totals"])
        self.assertEqual(r1["metadata"]["section_count"], r2["metadata"]["section_count"])

    def test_extract_spec_version_finds_r35(self):
        from urace import spec_audit as sa
        raw = self._spec_path().read_text(encoding="utf-8")
        version = sa.extract_spec_version(raw)
        self.assertIsNotNone(version)
        self.assertFalse(version.endswith("**"), f"version should not end with **: {version!r}")

    def test_spec_audit_due_true_when_version_changed(self):
        from urace import cli
        state = {"spec_audit_state": {"spec_version": "2026-10-10-r5"}}
        self.assertTrue(cli.spec_audit_due(state))

    def test_spec_audit_due_false_when_version_current(self):
        from urace import cli, spec_audit as sa
        import tempfile
        synthetic = "**Specification version: 2026-01-01-r99**\n" + "content\n" * 10
        with tempfile.TemporaryDirectory() as _d:
            _root = Path(_d)
            (_root / "URACE.md").write_text(synthetic)
            with patch.object(cli, "ROOT", _root), patch.object(_cli_lifecycle_m, "ROOT", _root):
                current = sa.extract_spec_version(synthetic)
                state = {"spec_audit_state": {"spec_version": current}}
                self.assertFalse(cli.spec_audit_due(state))

    def test_run_spec_audit_stores_evidence(self):
        from urace import cli
        import tempfile
        synthetic = "**Specification version: 2026-01-01-r99**\n" + "content\n" * 10
        with tempfile.TemporaryDirectory() as _d:
            _root = Path(_d)
            (_root / "URACE.md").write_text(synthetic)
            config = isolated_test_config(self)
            state = {"evidence": [], "spec_audit_state": {}}
            with patch.object(cli, "ROOT", _root), patch.object(_cli_lifecycle_m, "ROOT", _root):
                cli.run_spec_audit(config, state)
        kinds = [e["kind"] for e in state["evidence"]]
        self.assertIn("spec-structural-audit", kinds)

    def test_run_spec_audit_persists_version_in_state(self):
        from urace import cli, spec_audit as sa
        import tempfile
        synthetic = "**Specification version: 2026-01-01-r99**\n" + "content\n" * 10
        with tempfile.TemporaryDirectory() as _d:
            _root = Path(_d)
            (_root / "URACE.md").write_text(synthetic)
            config = isolated_test_config(self)
            state = {"evidence": [], "spec_audit_state": {}}
            with patch.object(cli, "ROOT", _root), patch.object(_cli_lifecycle_m, "ROOT", _root):
                cli.run_spec_audit(config, state)
            expected = sa.extract_spec_version(synthetic)
            self.assertEqual(state["spec_audit_state"]["spec_version"], expected)

class TechniqueApplicabilityGateTests(unittest.TestCase):
    def _state(self, lifecycle="ASSESSING", **extra):
        s = {"lifecycle_state": lifecycle, "executor_state": {}}
        s.update(extra)
        return s

    def _config(self):
        return {"executor": {"max_executor_calls_per_30d": 20}}

    def test_t1_returns_apply(self):
        from urace._common import technique_applicability_gate
        result = technique_applicability_gate("T1", self._state(), self._config())
        self.assertEqual(result["verdict"], "APPLY")
        self.assertEqual(result["reason"], "self_determinable")
        self.assertTrue(result.get("sd_result"))

    def test_t2_returns_apply(self):
        from urace._common import technique_applicability_gate
        result = technique_applicability_gate("T2", self._state(), self._config())
        self.assertEqual(result["verdict"], "APPLY")

    def test_t3_returns_apply(self):
        from urace._common import technique_applicability_gate
        result = technique_applicability_gate("T3", self._state(), self._config())
        self.assertEqual(result["verdict"], "APPLY")

    def test_t4_returns_apply(self):
        from urace._common import technique_applicability_gate
        result = technique_applicability_gate("T4", self._state(), self._config())
        self.assertEqual(result["verdict"], "APPLY")

    def test_t6_returns_apply(self):
        from urace._common import technique_applicability_gate
        result = technique_applicability_gate("T6", self._state(), self._config())
        self.assertEqual(result["verdict"], "APPLY")

    def test_dormant_no_obligation_returns_skip(self):
        from urace._common import technique_applicability_gate
        result = technique_applicability_gate("T1", self._state(lifecycle="DORMANT"), self._config())
        self.assertEqual(result["verdict"], "SKIP")
        self.assertEqual(result["reason"], "dormant_no_obligation")

    def test_already_applied_this_cycle_returns_skip(self):
        from urace._common import technique_applicability_gate
        result = technique_applicability_gate("T1", self._state(), self._config(), applied_this_cycle={"T1"})
        self.assertEqual(result["verdict"], "SKIP")
        self.assertEqual(result["reason"], "already_applied_this_cycle")

    def test_t5_with_credits_returns_delegate_executor(self):
        from urace._common import technique_applicability_gate
        result = technique_applicability_gate("T5", self._state(), self._config())
        self.assertEqual(result["verdict"], "DELEGATE_EXECUTOR")
        self.assertFalse(result.get("sd_result"))

    def test_t5_no_credits_returns_defer(self):
        from urace._common import technique_applicability_gate
        # Set calls_today equal to limit to exhaust credits
        state = self._state()
        state["executor_state"]["calls_today"] = 20
        result = technique_applicability_gate("T5", state, self._config())
        self.assertEqual(result["verdict"], "DEFER")
        self.assertEqual(result["reason"], "sd_false_insufficient_credits")

    def test_record_has_required_fields(self):
        from urace._common import technique_applicability_gate
        from urace.primitives import validate_technique_application_record
        result = technique_applicability_gate("T1", self._state(), self._config())
        # Should not raise
        validate_technique_application_record(result)

class ValidateTechniqueApplicationRecordTests(unittest.TestCase):
    def _valid(self):
        return {
            "id": "ta-0000000001",
            "technique": "T1",
            "verdict": "APPLY",
            "reason": "self_determinable",
            "applied_at": "2026-10-12T00:00:00+00:00",
        }

    def test_valid_record_passes(self):
        from urace.primitives import validate_technique_application_record
        validate_technique_application_record(self._valid())  # should not raise

    def test_missing_id_raises(self):
        from urace.primitives import validate_technique_application_record
        record = self._valid()
        del record["id"]
        with self.assertRaises(ValueError):
            validate_technique_application_record(record)

    def test_invalid_verdict_raises(self):
        from urace.primitives import validate_technique_application_record
        record = self._valid()
        record["verdict"] = "UNKNOWN"
        with self.assertRaises(ValueError):
            validate_technique_application_record(record)

    def test_missing_technique_raises(self):
        from urace.primitives import validate_technique_application_record
        record = self._valid()
        del record["technique"]
        with self.assertRaises(ValueError):
            validate_technique_application_record(record)

class PairedInvariantValidationTests(unittest.TestCase):
    def _base_op(self):
        return {"id": "op-0000000001", "scope": "documentation", "authority_basis": "test"}

    def _base_state(self, lifecycle, last_transition_status):
        return {
            "lifecycle_state": lifecycle,
            "status_transitions": [{"status": last_transition_status, "at": "2026-01-01T00:00:00+00:00"}],
            "progress_profiles": [],
        }

    def test_paired_invariant_passes_when_matching(self):
        from urace import validation as v
        state = self._base_state("ASSESSING", "ASSESSING")
        result = v.validate_operation(Path("/tmp"), self._base_op(), {}, {}, {}, state)
        check_names = [c["check"] for c in result["checks"]]
        self.assertIn("paired_invariant:lifecycle_state", check_names)
        paired = next(c for c in result["checks"] if c["check"] == "paired_invariant:lifecycle_state")
        self.assertEqual(paired["result"], "PASS")

    def test_paired_invariant_fails_when_mismatched(self):
        from urace import validation as v
        state = self._base_state("ASSESSING", "DORMANT")
        result = v.validate_operation(Path("/tmp"), self._base_op(), {}, {}, {}, state)
        paired = next(c for c in result["checks"] if c["check"] == "paired_invariant:lifecycle_state")
        self.assertEqual(paired["result"], "FAIL")

    def test_paired_invariant_skipped_when_no_transitions(self):
        from urace import validation as v
        state = {"lifecycle_state": "ASSESSING", "status_transitions": [], "progress_profiles": []}
        result = v.validate_operation(Path("/tmp"), self._base_op(), {}, {}, {}, state)
        check_names = [c["check"] for c in result["checks"]]
        self.assertNotIn("paired_invariant:lifecycle_state", check_names)

class ArchitecturalMetaPatternTests(unittest.TestCase):
    def test_validate_canonical_scalar_probability_valid(self):
        from urace import primitives as p
        p.validate_canonical_scalar(0.5, "probability")

    def test_validate_canonical_scalar_probability_out_of_range(self):
        from urace import primitives as p
        with self.assertRaises(ValueError):
            p.validate_canonical_scalar(1.5, "probability")

    def test_validate_canonical_scalar_count_negative(self):
        from urace import primitives as p
        with self.assertRaises(ValueError):
            p.validate_canonical_scalar(-1, "count")

    def test_validate_canonical_scalar_severity_valid(self):
        from urace import primitives as p
        p.validate_canonical_scalar("INFO", "severity_level")

    def test_validate_canonical_scalar_unknown_raises(self):
        from urace import primitives as p
        with self.assertRaises(ValueError):
            p.validate_canonical_scalar("x", "nonexistent_scalar")

    def test_validate_bridge_record_passes(self):
        from urace import primitives as p
        p.validate_bridge_record({
            "id": "br-abc", "bridge_name": "B1",
            "source_schema": "NormativeRule", "target_schema": "IntegrityGap",
            "translated_at": "2026-10-12T00:00:00+00:00",
        })

    def test_validate_bridge_record_missing_field_raises(self):
        from urace import primitives as p
        with self.assertRaises(ValueError):
            p.validate_bridge_record({"id": "br-abc"})

    def test_validate_orchestrator_record_bad_outcome_raises(self):
        from urace import primitives as p
        with self.assertRaises(ValueError):
            p.validate_orchestrator_record({
                "id": "orch-1", "orchestrator_name": "cycle",
                "started_at": "2026-10-12T00:00:00+00:00",
                "phases_completed": ["assess"],
                "outcome": "INVALID_OUTCOME",
            })


    def test_validate_lexical_formula_passes(self):
        from urace import primitives as p
        lf = {
            "id": "lf-001",
            "spec_section": "§62c",
            "natural_language": "events arrive in order",
            "formula": "∀i<j: ts(eᵢ) ≤ ts(eⱼ)",
            "sd_result": True,
        }
        p.validate_lexical_formula(lf)

    def test_validate_lexical_formula_missing_formula_raises(self):
        from urace import primitives as p
        lf = {
            "id": "lf-002",
            "spec_section": "§62c",
            "natural_language": "events arrive in order",
            "sd_result": True,
        }
        with self.assertRaises(Exception):
            p.validate_lexical_formula(lf)

    def test_validate_lexical_formula_sd_result_not_bool_raises(self):
        from urace import primitives as p
        lf = {
            "id": "lf-003",
            "spec_section": "§62c",
            "natural_language": "events arrive in order",
            "formula": "∀i<j: ts(eᵢ) ≤ ts(eⱼ)",
            "sd_result": "true",
        }
        with self.assertRaises(Exception):
            p.validate_lexical_formula(lf)

class ScheduledTaskTests(unittest.TestCase):
    def test_validate_scheduled_task_passes_valid(self):
        from urace import primitives as p
        task = {
            "id": "task-abc123",
            "name": "spec_audit_check",
            "schedule": {"kind": "INTERVAL_SECONDS", "interval_seconds": 3600},
            "scope": "runtime",
            "action": "spec_audit",
            "status": "ACTIVE",
            "created_by": "AUTO",
            "authority_basis": "gap detection triggered",
        }
        p.validate_scheduled_task(task)  # should not raise

    def test_validate_scheduled_task_fails_bad_status(self):
        from urace import primitives as p
        task = {
            "id": "task-abc123", "name": "x",
            "schedule": {"kind": "IMMEDIATE"},
            "scope": "runtime", "action": "x",
            "status": "UNKNOWN",  # invalid
            "created_by": "USER", "authority_basis": "test",
        }
        with self.assertRaises(ValueError):
            p.validate_scheduled_task(task)

    def test_validate_customization_record_passes(self):
        from urace import primitives as p
        rec = {
            "id": "cust-abc", "scope": "config",
            "key": "executor.max_executor_calls_per_30d",
            "value": 30, "reason": "higher limit needed",
            "created_at": "2026-10-12T00:00:00+00:00",
            "preserve_on_update": True,
        }
        p.validate_customization_record(rec)

    def test_validate_customization_record_fails_bad_scope(self):
        from urace import primitives as p
        rec = {
            "id": "cust-abc", "scope": "invalid",
            "key": "x", "value": 1, "reason": "x",
            "created_at": "2026-10-12T00:00:00+00:00",
            "preserve_on_update": True,
        }
        with self.assertRaises(ValueError):
            p.validate_customization_record(rec)

    def test_scheduled_task_due_interval(self):
        from urace._common import scheduled_task_due
        import time
        task = {
            "id": "task-1", "status": "ACTIVE",
            "schedule": {"kind": "INTERVAL_SECONDS", "next_run_at": "2000-01-01T00:00:00+00:00"},
        }
        self.assertTrue(scheduled_task_due(task, time.time()))

    def test_scheduled_task_not_due_future(self):
        from urace._common import scheduled_task_due
        task = {
            "id": "task-1", "status": "ACTIVE",
            "schedule": {"kind": "INTERVAL_SECONDS", "next_run_at": "2099-01-01T00:00:00+00:00"},
        }
        self.assertFalse(scheduled_task_due(task, __import__("time").time()))

    def test_bridge_record_produces_valid_record(self):
        from urace._common import bridge_record
        from urace import primitives as p
        r = bridge_record("B1", "NormativeRule", "IntegrityGap")
        p.validate_bridge_record(r)
        self.assertEqual(r["bridge_name"], "B1")
        self.assertTrue(r["id"].startswith("br-"))

    def test_orchestrator_record_produces_valid_record(self):
        from urace._common import orchestrator_record
        from urace import primitives as p
        r = orchestrator_record("cycle", "2026-10-12T00:00:00+00:00", ["assess", "persist"], "COMPLETED")
        p.validate_orchestrator_record(r)
        self.assertEqual(r["orchestrator_name"], "cycle")
        self.assertEqual(r["outcome"], "COMPLETED")

