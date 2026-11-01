import json,tempfile,unittest
from pathlib import Path
from urace import external_metrics

class CollectDisabledTests(unittest.TestCase):
 def test_disabled_returns_empty_observations(self):
  with tempfile.TemporaryDirectory() as tmp:
   result=external_metrics.collect(Path(tmp),{'mode':'DISABLED'})
   self.assertEqual(result['mode'],'DISABLED');self.assertEqual(result['observations'],[]);self.assertEqual(result['errors'],[])
 def test_default_mode_is_disabled(self):
  with tempfile.TemporaryDirectory() as tmp:
   result=external_metrics.collect(Path(tmp),{});self.assertEqual(result['mode'],'DISABLED')

class CollectJsonFileTests(unittest.TestCase):
 def test_scalar_lookup(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);data=root/'m.json';data.write_text(json.dumps({'score':42,'ratio':0.75}))
   settings={'mode':'ENABLED','sources':[{'id':'t','kind':'json_file','location':str(data),'values':{'score':'score','ratio':'ratio'}}]}
   result=external_metrics.collect(root,settings)
   self.assertEqual(len(result['observations']),1);self.assertEqual(result['observations'][0]['values']['score'],42);self.assertEqual(result['errors'],[])
 def test_missing_file_becomes_error(self):
  with tempfile.TemporaryDirectory() as tmp:
   settings={'mode':'ENABLED','sources':[{'id':'x','kind':'json_file','location':'/nonexistent/path.json','values':{}}]}
   result=external_metrics.collect(Path(tmp),settings);self.assertEqual(result['observations'],[]);self.assertEqual(len(result['errors']),1);self.assertEqual(result['errors'][0]['source'],'x')
 def test_unsupported_kind_becomes_error(self):
  with tempfile.TemporaryDirectory() as tmp:
   settings={'mode':'ENABLED','sources':[{'id':'bad','kind':'unknown_kind','values':{}}]}
   result=external_metrics.collect(Path(tmp),settings);self.assertEqual(len(result['errors']),1)

class LookupTests(unittest.TestCase):
 def test_simple_key(self):self.assertEqual(external_metrics._lookup({'a':1},'a'),1)
 def test_nested_key(self):self.assertEqual(external_metrics._lookup({'a':{'b':2}},'a.b'),2)
 def test_list_index(self):self.assertEqual(external_metrics._lookup([10,20],'1'),20)
 def test_missing_key_raises_schema_mismatch(self):
  with self.assertRaises(external_metrics.SourceSchemaMismatch):external_metrics._lookup({'a':1},'b')
 def test_non_scalar_raises_value_error(self):
  with self.assertRaises(ValueError):external_metrics._lookup({'a':{'b':1}},'a')
 def test_infinite_float_raises(self):
  with self.assertRaises(ValueError):external_metrics._lookup({'v':float('inf')},'v')

class MaxBytesTests(unittest.TestCase):
 def test_minimum_enforced(self):
  with tempfile.TemporaryDirectory() as tmp:
   with self.assertRaises(ValueError):external_metrics.collect(Path(tmp),{'mode':'ENABLED','max_response_bytes':512,'sources':[]})

class LastKnownGoodTests(unittest.TestCase):
 def test_lkg_carried_forward_on_error(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);data=root/'d.json';data.write_text(json.dumps({'v':5}))
   settings={'mode':'ENABLED','sources':[{'id':'src','kind':'json_file','location':str(data),'values':{'v':'v'}}]}
   first=external_metrics.collect(root,settings);lkg=first['last_known_good'];data.unlink()
   second=external_metrics.collect(root,settings,last_known_good=lkg)
   self.assertIn('src',second['last_known_good']);self.assertEqual(second['errors'][0]['last_known_good']['value']['v'],5)
