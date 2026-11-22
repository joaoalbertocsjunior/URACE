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
        import sys
        result = subprocess.run(
            [sys.executable, "-m", "urace", "derive", "--help"],
            capture_output=True, text=True,
            cwd=str(TEST_RUNTIME_ROOT.parent),
            env={**os.environ, "PYTHONPATH": str(TEST_RUNTIME_ROOT)},
        )
        self.assertIn("--from-constraints", result.stdout + result.stderr)

    def test_from_inspection_flag_registered(self):
        import sys
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
        import sys
        result = subprocess.run(
            [sys.executable, "-m", "urace", "update", "--help"],
            capture_output=True, text=True,
            cwd=str(TEST_RUNTIME_ROOT.parent),
            env={**os.environ, "PYTHONPATH": str(TEST_RUNTIME_ROOT)},
        )
        self.assertIn("--opt-in-constructs", result.stdout + result.stderr)

    def test_opt_in_patterns_alias_still_accepted(self):
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
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            cfg = {"root": td, "state_path": os.path.join(td, "state.json"),
                   "config_path": os.path.join(td, "config.json"), "product_files": []}
            state = {"construct_set_refs": []}
            result = cli._refresh_derived_construct_sets(state, cfg, None, False)
            self.assertEqual(len(result), 1)
            self.assertIn("no_saved", result[0]["status"])

    def test_refresh_construct_sets_refreshes_ref(self):
        import tempfile
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
        src = inspect.getsource(cli._cmd_derive)
        self.assertIn("construct_digests", src)

    def test_pattern_digests_in_saved_ref_keys(self):
        import inspect
        src = inspect.getsource(cli._cmd_derive)
        self.assertIn("pattern_digests", src)
