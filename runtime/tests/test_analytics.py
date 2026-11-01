import hashlib,tempfile,unittest
from pathlib import Path
from urace import analytics

class CapabilitiesTests(unittest.TestCase):
 def test_returns_expected_keys(self):
  c=analytics.capabilities();self.assertIn('portable_csv_html',c);self.assertIn('native_xlsx',c);self.assertEqual(c['canonical_control_dependency'],'NONE');self.assertEqual(c['portable_csv_html']['status'],'READY')

class SafeCellTests(unittest.TestCase):
 def test_formula_injection_escaped(self):
  for prefix in ('=','+','-','@'):self.assertTrue(str(analytics._safe_cell(prefix+'SUM(A1)')).startswith("'"))
 def test_dict_serialized(self):self.assertIsInstance(analytics._safe_cell({'a':1}),str)
 def test_plain_string_unchanged(self):self.assertEqual(analytics._safe_cell('hello'),'hello')
 def test_number_unchanged(self):self.assertEqual(analytics._safe_cell(42),42)

class FlattenTests(unittest.TestCase):
 def test_nested_dict(self):
  out={};analytics._flatten('',{'a':{'b':1}},out);self.assertEqual(out,{'a.b':1})
 def test_list_serialized(self):
  out={};analytics._flatten('items',[1,2,3],out);self.assertIn('items',out)
 def test_scalar_stored(self):
  out={};analytics._flatten('x',99,out);self.assertEqual(out['x'],99)

class CollectTests(unittest.TestCase):
 def test_minimal_state_produces_core_tables(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'state').mkdir();tables=analytics.collect(root,{},{})
   self.assertIn('overview',tables);self.assertIn('objectives',tables);self.assertIsInstance(tables['overview'],list)
 def test_overview_control_dependency_none(self):
  with tempfile.TemporaryDirectory() as tmp:
   tables=analytics.collect(Path(tmp),{},{});row=tables['overview'][0];self.assertEqual(row['control_dependency'],'NONE')

class ExportPortableTests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);(self.root/'urace').mkdir()
 def test_creates_manifest_csv_and_html(self):
  output=self.root/'export';manifest=analytics.export_portable(self.root,{'state_version':1},{},output)
  self.assertIn('exported_at',manifest);self.assertEqual(manifest['schema_version'],1)
  self.assertTrue((output/'manifest.json').exists());self.assertTrue((output/'dashboard.html').exists());self.assertTrue((output/'csv').is_dir())
 def test_manifest_sha256_covers_all_files(self):
  output=self.root/'export';manifest=analytics.export_portable(self.root,{},{},output)
  for path_key,expected in manifest['sha256'].items():
   full=output/path_key;self.assertTrue(full.exists(),f'missing {path_key}')
   self.assertEqual(hashlib.sha256(full.read_bytes()).hexdigest(),expected)
 def test_reexport_replaces_previous(self):
  output=self.root/'export'
  analytics.export_portable(self.root,{'state_version':1},{},output)
  analytics.export_portable(self.root,{'state_version':2},{},output)
  import json;m=json.loads((output/'manifest.json').read_text());self.assertEqual(m['state_version'],2)
