import json,tempfile,unittest
from pathlib import Path

from urace import workflow_state as ws


class WorkflowConflictTests(unittest.TestCase):
 def test_is_runtime_error(self):
  self.assertTrue(issubclass(ws.WorkflowConflict, RuntimeError))


class ProductCopyTests(unittest.TestCase):
 def test_none_when_not_configured(self):
  result = ws.product_copy({}, Path("/tmp"))
  self.assertIsNone(result)

 def test_none_when_key_absent(self):
  config = {"specification_workflow": {}}
  result = ws.product_copy(config, Path("/tmp"))
  self.assertIsNone(result)

 def test_absolute_path_inside_product_accepted(self):
  with tempfile.TemporaryDirectory() as td:
   base = Path(td)
   product_dir = base / "product"
   product_dir.mkdir()
   target = product_dir / "URACE.md"
   config = {"specification_workflow": {"product_copy": str(target)}}
   result = ws.product_copy(config, base)
   self.assertEqual(result.resolve(), target.resolve())

 def test_path_outside_product_raises_conflict(self):
  with tempfile.TemporaryDirectory() as td:
   base = Path(td)
   outside = base / "other" / "URACE.md"
   config = {"specification_workflow": {"product_copy": str(outside)}}
   with self.assertRaises(ws.WorkflowConflict):
    ws.product_copy(config, base)


class VersionFolderTests(unittest.TestCase):
 def _setup_base(self, td):
  base = Path(td)
  # series root path must be a path that, when joined with base, stays under base/versions
  series_root = "versions/main"
  (base / "versions" / "main").mkdir(parents=True)
  # _version_folder builds: (base / series / f'v{n}').resolve()
  # and checks it's relative to base/'versions'
  # so series must equal "versions/main" or similar
  (base / "version-series.json").write_text(json.dumps({"root": "versions/main"}))
  return base, series_root

 def test_valid_version_number_returns_path(self):
  with tempfile.TemporaryDirectory() as td:
   base, _ = self._setup_base(td)
   path = ws._version_folder(base, 0)
   self.assertTrue(str(path).endswith("v000000"))

 def test_negative_version_raises_conflict(self):
  with tempfile.TemporaryDirectory() as td:
   base, _ = self._setup_base(td)
   with self.assertRaises(ws.WorkflowConflict):
    ws._version_folder(base, -1)

 def test_non_int_version_raises_conflict(self):
  with tempfile.TemporaryDirectory() as td:
   base, _ = self._setup_base(td)
   with self.assertRaises(ws.WorkflowConflict):
    ws._version_folder(base, "0")

 def test_path_resolves_inside_versions(self):
  with tempfile.TemporaryDirectory() as td:
   base, _ = self._setup_base(td)
   path = ws._version_folder(base, 42)
   self.assertTrue(path.is_relative_to(base / "versions"))


class ShaTests(unittest.TestCase):
 def test_sha_is_hex_string(self):
  result = ws._sha(b"hello")
  self.assertIsInstance(result, str)
  self.assertEqual(len(result), 64)

 def test_sha_deterministic(self):
  self.assertEqual(ws._sha(b"abc"), ws._sha(b"abc"))

 def test_sha_different_inputs_differ(self):
  self.assertNotEqual(ws._sha(b"a"), ws._sha(b"b"))


if __name__ == "__main__":
 unittest.main()
