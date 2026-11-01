"""Tests for runtime_features.py — feature status registry."""
import json,io,unittest
from contextlib import redirect_stdout
from urace import runtime_features as rf

class StatusVocabTests(unittest.TestCase):
 def test_status_values_nonempty(self):self.assertGreaterEqual(len(rf.STATUS_VALUES),7)
 def test_tag_values_nonempty(self):self.assertGreaterEqual(len(rf.TAG_VALUES),4)
 def test_known_statuses_present(self):
  for s in ('stable','complete','active','stub','stale','review','deprecated','experimental'):self.assertIn(s,rf.STATUS_VALUES)
 def test_known_tags_present(self):
  for t in ('core','integration','optional','security','observability','delivery','self-improvement','ux'):self.assertIn(t,rf.TAG_VALUES)

class FeatureRegistryTests(unittest.TestCase):
 def test_all_features_at_least_20(self):self.assertGreaterEqual(len(rf.all_features()),20)
 def test_no_duplicate_ids(self):ids=[f['id'] for f in rf.all_features()];self.assertEqual(len(ids),len(set(ids)))
 def test_all_have_required_keys(self):
  for f in rf.all_features():
   for k in ('id','name','module','status','description','test_coverage','tags'):
    self.assertIn(k,f,f"Feature {f.get('id')} missing {k}")
 def test_all_statuses_valid(self):
  for f in rf.all_features():self.assertIn(f['status'],rf.STATUS_VALUES,f['id'])
 def test_all_test_coverages_valid(self):
  for f in rf.all_features():self.assertIn(f['test_coverage'],('none','partial','full'),f['id'])
 def test_all_tags_valid(self):
  for f in rf.all_features():
   for tag in f['tags']:self.assertIn(tag,rf.TAG_VALUES,f"Feature {f['id']} has unknown tag {tag!r}")
 def test_blockers_is_list(self):
  for f in rf.all_features():self.assertIsInstance(f.get('blockers',[]),list,f['id'])
 def test_by_status_returns_correct_status(self):
  for f in rf.by_status('stub'):self.assertEqual(f['status'],'stub')
 def test_by_status_empty_for_unknown(self):self.assertEqual(rf.by_status('nonexistent'),[])
 def test_by_tag_returns_correct_tag(self):
  for f in rf.by_tag('core'):self.assertIn('core',f['tags'])
 def test_by_tag_empty_for_unknown(self):self.assertEqual(rf.by_tag('nonexistent-tag'),[])
 def test_summary_returns_counts(self):
  s=rf.summary()
  total_from_summary=sum(s.values())
  self.assertEqual(total_from_summary,len(rf.all_features()))
 def test_summary_keys_are_status_values(self):
  for k in rf.summary():self.assertIn(k,rf.STATUS_VALUES)
 def test_get_lifecycle_loop(self):f=rf.get('lifecycle-loop');self.assertIsNotNone(f);self.assertEqual(f['status'],'stable')
 def test_get_unknown_returns_none(self):self.assertIsNone(rf.get('does-not-exist-xyz'))
 def test_stubs_all_stub(self):self.assertTrue(all(f['status']=='stub' for f in rf.stubs()))
 def test_stubs_is_list(self):self.assertIsInstance(rf.stubs(),list)
 def test_improvement_candidates_are_stub_stale_review(self):
  for f in rf.improvement_candidates():self.assertIn(f['status'],{'stub','stale','review'})
 def test_improvement_candidates_is_list(self):self.assertIsInstance(rf.improvement_candidates(),list)
 def test_improvement_candidates_core_first(self):
  cands=rf.improvement_candidates()
  if len(cands)>1:
   core_idx=[i for i,f in enumerate(cands) if 'core' in f['tags']]
   non_core=[i for i,f in enumerate(cands) if 'core' not in f['tags']]
   if core_idx and non_core:self.assertLess(min(core_idx),max(non_core))
 def test_validate_passes(self):rf.validate()
 def test_feedback_loop_is_active(self):f=rf.get('feedback-loop');self.assertIsNotNone(f);self.assertIn(f['status'],{'active','complete','stable'})
 def test_budget_enforcement_is_stale(self):f=rf.get('budget-enforcement');self.assertIsNotNone(f);self.assertIn(f['status'],{'stale','complete','active'})
 def test_returns_copies_not_originals(self):
  f1=rf.get('lifecycle-loop');f1['status']='modified'
  f2=rf.get('lifecycle-loop');self.assertNotEqual(f2['status'],'modified')

class SelfMetricsTests(unittest.TestCase):
 def setUp(self):
  import tempfile;self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  from pathlib import Path;self.root=Path(self.tmp.name)
 def test_latest_none_when_missing(self):
  from urace import self_metrics as sm;self.assertIsNone(sm.latest(self.root))
 def test_save_and_reload(self):
  from urace import self_metrics as sm
  data={'schema':sm.SELF_METRICS_SCHEMA,'collected_at':0.0,'metrics':{},'errors':[]}
  sm.save(self.root,data);loaded=sm.latest(self.root)
  self.assertIsNotNone(loaded);self.assertEqual(loaded['schema'],sm.SELF_METRICS_SCHEMA)
 def test_as_external_source_none_when_no_data(self):
  from urace import self_metrics as sm;self.assertIsNone(sm.as_external_source(self.root))
 def test_as_external_source_with_metrics(self):
  from urace import self_metrics as sm
  data={'schema':sm.SELF_METRICS_SCHEMA,'collected_at':1000.0,'metrics':{'test_pass_rate':{'value':0.95}},'errors':[]}
  sm.save(self.root,data)
  src=sm.as_external_source(self.root)
  self.assertIsNotNone(src);self.assertIn('test_pass_rate',src['values']);self.assertAlmostEqual(src['values']['test_pass_rate'],0.95)
 def test_collect_returns_schema(self):
  from urace import self_metrics as sm
  result=sm.collect(self.root,timeout=5)
  self.assertEqual(result['schema'],sm.SELF_METRICS_SCHEMA)
  self.assertIn('metrics',result);self.assertIn('errors',result)

class FeaturesCLITests(unittest.TestCase):
 def _call(self,args):
  from urace import cli;out=io.StringIO()
  with redirect_stdout(out):code=cli.main(['features']+args)
  return code,out.getvalue()
 def test_features_list(self):code,text=self._call(['list']);self.assertEqual(code,0);self.assertIn('lifecycle-loop',text)
 def test_features_summary(self):code,text=self._call(['summary']);self.assertEqual(code,0);self.assertIn('stable',text)
 def test_features_show_known(self):code,text=self._call(['show','lifecycle-loop']);self.assertEqual(code,0);self.assertIn('stable',text)
 def test_features_show_unknown(self):code,_=self._call(['show','no-such-feature']);self.assertEqual(code,1)
 def test_features_candidates(self):code,text=self._call(['candidates']);self.assertEqual(code,0)
 def test_features_filter_by_status(self):code,text=self._call(['filter','--status','stub']);self.assertEqual(code,0)
 def test_features_list_json(self):
  code,text=self._call(['--json','list'])
  self.assertEqual(code,0);data=json.loads(text);self.assertIsInstance(data,list);self.assertGreater(len(data),0)
 def test_features_summary_json(self):
  code,text=self._call(['--json','summary'])
  self.assertEqual(code,0);data=json.loads(text);self.assertIn('stable',data)

import sys
