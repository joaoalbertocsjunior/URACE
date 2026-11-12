import tempfile,unittest
from pathlib import Path
from unittest.mock import patch

from urace import validation as v


def _noop_validate(value):
 pass


# Patch away primitives schema checks so tests focus on the logic
_prim_patch = {
 "urace.validation._primitives.validate_validation_check": _noop_validate,
 "urace.validation._primitives.validate_validation_result": _noop_validate,
}


def _base_op(scope="implementation"):
 return {
  "id": "op-1",
  "scope": scope,
  "changed_files": [],
  "authority_basis": "user directive",
 }


def _base_state():
 return {
  "lifecycle_state": "ACTIVE",
  "status_transitions": [{"to": "ACTIVE"}],
  "progress_profiles": [],
 }


def _base_config(scope="implementation", patterns=("**",)):
 return {
  "executor": {
   "allowed_files_by_scope": {scope: list(patterns)},
  }
 }


class CandidateFileErrorsTests(unittest.TestCase):
 def test_no_files_returns_error(self):
  with tempfile.TemporaryDirectory() as td:
   root = Path(td)
   errs = v.candidate_file_errors(root, "implementation", [], _base_config())
   self.assertTrue(any("no changed files" in e for e in errs))

 def test_file_not_matching_allowlist_flagged(self):
  with tempfile.TemporaryDirectory() as td:
   root = Path(td)
   config = _base_config("implementation", ("docs/**",))
   errs = v.candidate_file_errors(root, "implementation", ["secret.py"], config)
   self.assertTrue(any("outside authorized" in e for e in errs))

 def test_file_matching_allowlist_no_error(self):
  with tempfile.TemporaryDirectory() as td:
   root = Path(td)
   config = _base_config("implementation", ("*.py",))
   errs = v.candidate_file_errors(root, "implementation", ["foo.py"], config)
   self.assertFalse(any("outside authorized" in e for e in errs))

 def test_absolute_path_flagged(self):
  with tempfile.TemporaryDirectory() as td:
   root = Path(td)
   config = _base_config("implementation", ("**",))
   errs = v.candidate_file_errors(root, "implementation", ["/etc/passwd"], config)
   self.assertTrue(any("escapes" in e for e in errs))

 def test_symlink_flagged(self):
  with tempfile.TemporaryDirectory() as td:
   root = Path(td)
   real = root / "real.py"
   real.write_text("x")
   link = root / "link.py"
   link.symlink_to(real)
   config = _base_config("implementation", ("**",))
   errs = v.candidate_file_errors(root, "implementation", ["link.py"], config)
   self.assertTrue(any("symlink" in e for e in errs))


class ValidateOperationTests(unittest.TestCase):
 def _run(self, root, operation=None, before=None, after=None, config=None, state=None):
  with patch.multiple("urace.validation._primitives",
                      validate_validation_check=_noop_validate,
                      validate_validation_result=_noop_validate):
   return v.validate_operation(
    root,
    operation or _base_op(),
    before or {"accuracy": 0.8},
    after or {"accuracy": 0.9},
    config or _base_config(),
    state or _base_state(),
   )

 def _op_with_file(self, root, filename="main.py"):
  f = root / filename
  f.write_text("x")
  return {
   "id": "op-1",
   "scope": "implementation",
   "changed_files": [filename],
   "authority_basis": "user directive",
  }

 def _config_with_file(self, filename="main.py"):
  return {"executor": {"allowed_files_by_scope": {"implementation": [filename]}}}

 def test_valid_operation_is_validated(self):
  with tempfile.TemporaryDirectory() as td:
   root = Path(td)
   op = self._op_with_file(root)
   config = self._config_with_file()
   result = self._run(root, operation=op, config=config)
   self.assertEqual(result["verdict"], v.VALIDATED)
   self.assertFalse(result["fails"])

 def test_regression_causes_rejection(self):
  with tempfile.TemporaryDirectory() as td:
   result = self._run(Path(td), before={"accuracy": 0.9}, after={"accuracy": 0.7})
   self.assertEqual(result["verdict"], v.REJECTED)
   names = [c["check"] for c in result["fails"]]
   self.assertTrue(any("metric_guardrail" in n for n in names))

 def test_nonincreasing_direction_allows_decrease(self):
  state = {
   "lifecycle_state": "ACTIVE",
   "status_transitions": [{"to": "ACTIVE"}],
   "progress_profiles": [{"measures": {"cost": {"direction": "nonincreasing"}}}],
  }
  with tempfile.TemporaryDirectory() as td:
   result = self._run(Path(td), before={"cost": 100.0}, after={"cost": 80.0},
                      state=state)
  cost_checks = [c for c in result["checks"] if "cost" in c["check"]]
  self.assertTrue(all(c["result"] == "PASS" for c in cost_checks))

 def test_nonincreasing_direction_rejects_increase(self):
  state = {
   "lifecycle_state": "ACTIVE",
   "status_transitions": [{"to": "ACTIVE"}],
   "progress_profiles": [{"measures": {"cost": {"direction": "nonincreasing"}}}],
  }
  with tempfile.TemporaryDirectory() as td:
   result = self._run(Path(td), before={"cost": 100.0}, after={"cost": 120.0},
                      state=state)
  self.assertEqual(result["verdict"], v.REJECTED)

 def test_mismatched_metric_keys_causes_rejection(self):
  with tempfile.TemporaryDirectory() as td:
   result = self._run(Path(td), before={"a": 1.0}, after={"b": 1.0})
   self.assertEqual(result["verdict"], v.REJECTED)
   names = [c["check"] for c in result["fails"]]
   self.assertIn("measurement_comparability", names)

 def test_missing_changed_file_causes_rejection(self):
  with tempfile.TemporaryDirectory() as td:
   root = Path(td)
   op = {**_base_op(), "changed_files": ["missing.py"], "scope": "implementation"}
   config = _base_config("implementation", ("**",))
   result = self._run(root, operation=op, config=config)
   self.assertEqual(result["verdict"], v.REJECTED)

 def test_present_changed_file_passes(self):
  with tempfile.TemporaryDirectory() as td:
   root = Path(td)
   (root / "present.py").write_text("x")
   op = {**_base_op(), "changed_files": ["present.py"], "scope": "implementation"}
   config = _base_config("implementation", ("**",))
   result = self._run(root, operation=op, config=config)
   file_checks = [c for c in result["checks"] if "file_present:present.py" in c["check"]]
   self.assertTrue(any(c["result"] == "PASS" for c in file_checks))

 def test_unknown_scope_causes_rejection(self):
  with tempfile.TemporaryDirectory() as td:
   op = {**_base_op(), "scope": "unknown_scope"}
   result = self._run(Path(td), operation=op)
   self.assertEqual(result["verdict"], v.REJECTED)
   names = [c["check"] for c in result["fails"]]
   self.assertIn("scope_declared", names)

 def test_missing_authority_basis_causes_rejection(self):
  with tempfile.TemporaryDirectory() as td:
   op = {**_base_op()}
   del op["authority_basis"]
   result = self._run(Path(td), operation=op)
   self.assertEqual(result["verdict"], v.REJECTED)
   names = [c["check"] for c in result["fails"]]
   self.assertIn("authority_basis_present", names)

 def test_lifecycle_mismatch_causes_rejection(self):
  state = {
   "lifecycle_state": "ACTIVE",
   "status_transitions": [{"to": "PAUSED"}],
   "progress_profiles": [],
  }
  with tempfile.TemporaryDirectory() as td:
   result = self._run(Path(td), state=state)
   names = [c["check"] for c in result["fails"]]
   self.assertIn("paired_invariant:lifecycle_state", names)

 def test_empty_metrics_causes_rejection(self):
  with tempfile.TemporaryDirectory() as td:
   result = self._run(Path(td), before={}, after={})
   self.assertEqual(result["verdict"], v.REJECTED)

 def test_boolean_metric_causes_rejection(self):
  with tempfile.TemporaryDirectory() as td:
   result = self._run(Path(td), before={"x": True}, after={"x": False})
   self.assertEqual(result["verdict"], v.REJECTED)

 def test_result_has_required_fields(self):
  with tempfile.TemporaryDirectory() as td:
   result = self._run(Path(td))
   for field in ("verdict", "checks", "fails", "basis", "validated_at", "meaning"):
    self.assertIn(field, result)


class PendingValidationRecordTests(unittest.TestCase):
 def test_record_has_required_fields(self):
  op = {"id": "op-x", "scope": "implementation"}
  record = v.pending_validation_record(op, "metrics unavailable")
  self.assertEqual(record["status"], v.PENDING_CAPABILITY)
  self.assertEqual(record["operation_id"], "op-x")
  self.assertEqual(record["operation_scope"], "implementation")
  self.assertIn("queued_at", record)
  self.assertIn("reason", record)
  self.assertIn("note", record)

 def test_id_has_pv_prefix(self):
  op = {"id": "op-y", "scope": "documentation"}
  record = v.pending_validation_record(op, "test")
  self.assertTrue(record["id"].startswith("pv-"))


if __name__ == "__main__":
 unittest.main()
