import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from coverage_assessment import paired_metrics,product_context,features,comparative_readiness

class CoverageAssessmentTests(unittest.TestCase):
 def pair(self,i=0,family='navigation'):
  a={'id':'a'+str(i),'provider':'codex','family':family,'effort':'medium','repeat':i,'actual_providers':['codex'],'complete':True,'validated':True,'tokens':100,'elapsed_seconds':10,'acceptance':{'quality':{'measurement_complete':True,'gate_passed':True}}};return a,{**copy.deepcopy(a),'id':'b'+str(i),'tokens':70,'elapsed_seconds':7}
 def test_sparse_pairs_withhold_resource_deltas_and_worth(self):
  r=paired_metrics([self.pair()],required_families={'navigation'});self.assertFalse(r['ready']);self.assertIsNone(r['metrics']);self.assertIsNone(r['overall_worth_percentile'])
 def test_adequate_matched_data_has_reproducible_scoped_percentiles(self):
  pairs=[self.pair(i) for i in range(40)];a=paired_metrics(pairs,required_families={'navigation'});b=paired_metrics(pairs,required_families={'navigation'});self.assertTrue(a['ready']);self.assertEqual(a['metrics'],b['metrics']);self.assertEqual(a['metrics']['tokens']['observed_reduction_pct'],30);self.assertEqual(a['metrics']['tokens']['paired_reduction_percentiles']['p95'],30);self.assertIsNone(a['overall_worth_percentage'])
 def test_profile_pooling_unknown_usage_and_missing_family_do_not_qualify(self):
  for change in ('provider','effort','tokens','family'):
   pairs=[self.pair(i) for i in range(35)]
   if change=='provider':pairs[0][1]['actual_providers']=['claude']
   if change=='effort':pairs[0][1]['effort']='high'
   if change=='tokens':pairs[0][1]['tokens']=None
   required={'navigation','recovery'} if change=='family' else {'navigation'}
   self.assertFalse(paired_metrics(pairs,required_families=required)['ready'])
 def test_failed_measured_outputs_and_costs_are_not_removed(self):
  pairs=[self.pair(i) for i in range(35)];pairs[0][1]['validated']=False;pairs[0][1]['acceptance']['quality']['gate_passed']=False;r=paired_metrics(pairs,required_families={'navigation'});self.assertTrue(r['ready']);self.assertEqual(r['metrics']['urace']['failed_or_rejected_workflows'],1);self.assertLess(r['metrics']['urace']['validated_delivery_pct'],100);self.assertEqual(r['metrics']['tokens']['observed_reduction_pct'],30)
 def test_zero_candidate_usage_is_known_not_missing(self):
  pairs=[self.pair(i) for i in range(35)]
  for a,b in pairs:b['tokens']=0
  r=paired_metrics(pairs,required_families={'navigation'});self.assertTrue(r['ready']);self.assertEqual(r['metrics']['tokens']['observed_reduction_pct'],100)
 def test_missing_product_is_not_global_context_success(self):
  with tempfile.TemporaryDirectory() as d:self.assertFalse(product_context(Path(d))['global_semantic_consistency_proven'])
 def test_context_partition_preserves_every_byte_and_does_not_invent_comprehension(self):
  import hashlib
  with tempfile.TemporaryDirectory() as d:
   b=Path(d);v=b/'versions/v000001';v.mkdir(parents=True);text='# Product\nFirst prose.\n## Part\nSecond prose.\n';h=hashlib.sha256(text.encode()).hexdigest();(v/'URACE.md').write_text(text);(v/'manifest.json').write_text(json.dumps({'version':1,'sha256':h}));(b/'active-version.json').write_text(json.dumps({'snapshot':str(v),'sha256':h}));(b/'trial-clock.json').write_text('{"trial_id":"t"}');(b/'state.json').write_text('{"jobs":[]}');r=product_context(b);self.assertEqual(sum(c['bytes'] for c in r['contexts']),len(text.encode()));self.assertEqual(r['contexts_with_selection_history'],0);self.assertFalse(r['global_semantic_consistency_proven']);self.assertFalse(r['editorial_context']['full_document_sent_to_model'])
 def test_context_source_corruption_is_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   b=Path(d);v=b/'versions/v';v.mkdir(parents=True);(v/'URACE.md').write_text('changed');(v/'manifest.json').write_text('{"version":1,"sha256":"bad"}');(b/'active-version.json').write_text(json.dumps({'snapshot':str(v),'sha256':'bad'}))
   with self.assertRaises(ValueError):product_context(b)
 def test_stale_comparison_is_not_scored(self):
  with tempfile.TemporaryDirectory() as d:
   b=Path(d);(b/'trial-clock.json').write_text('{"trial_id":"t"}');(b/'repository-study-latest.json').write_text(json.dumps({'cohort':'abc','plan':{'trial_id':'old','engine_sha256':'e'}}));self.assertEqual(comparative_readiness(b,'e')['status'],'NO_CURRENT_MATCHING_COHORT')
 def test_test_inventory_does_not_claim_live_feature_success(self):
  from urace import cli
  with tempfile.TemporaryDirectory() as d:
   b=Path(d)/'trial';b.mkdir();(b.parent/'runtime/urace').mkdir(parents=True);(b.parent/'runtime/tests').mkdir();(b.parent/'runtime/urace/example.py').write_text('pass');r=features(b,cli.build_parser());self.assertFalse(r['all_features_live_verified']);self.assertFalse(r['qualification']['source_matches']);self.assertIn('api serve',r['operation_paths'])

class ClaudeDiagnosticTests(unittest.TestCase):
 def test_schema_failure_retains_provenance_without_raw_error_text(self):
  from stream_usage import StreamUsage
  usage=StreamUsage();usage.ingest({'type':'result','is_error':True,'subtype':'error_max_structured_output_retries','errors':['schema validation rejected private prompt text','model fallback retracted output']});d=usage.snapshot()['final']['structured_output_diagnostics'];self.assertTrue(d['available']);self.assertEqual(d['count'],2);self.assertIn('schema',d['categories']);self.assertIn('fallback',d['categories']);self.assertNotIn('private prompt',json.dumps(d));self.assertEqual(len(d['sha256']),64);self.assertFalse(usage.snapshot()['success'])
 def test_missing_error_details_are_unknown_not_schema_diagnosis(self):
  from stream_usage import structured_diagnostics
  d=structured_diagnostics({'subtype':'error_max_structured_output_retries'});self.assertFalse(d['available']);self.assertIsNone(d['count']);self.assertEqual(d['categories'],[])

class ReviewScheduleTests(unittest.TestCase):
 def test_restart_preserves_due_and_other_trial_does_not_inherit_it(self):
  from trial_supervisor import next_review
  with tempfile.TemporaryDirectory() as d:
   b=Path(d);(b/'trial-clock.json').write_text('{"trial_id":"t"}');self.assertEqual(next_review(b,100),10900);self.assertEqual(next_review(b,200),10900);(b/'trial-clock.json').write_text('{"trial_id":"new"}');self.assertEqual(next_review(b,300),11100)
 def test_overdue_review_runs_immediately_and_invalid_values_do_not_delay(self):
  from trial_supervisor import next_review
  with tempfile.TemporaryDirectory() as d:
   b=Path(d);(b/'trial-clock.json').write_text('{"trial_id":"t"}');(b/'review-schedule.json').write_text('{"trial_id":"t","next_due_unix":10}');self.assertEqual(next_review(b,100),10);(b/'review-schedule.json').write_text('{"trial_id":"t","next_due_unix":NaN}');self.assertEqual(next_review(b,100),10900)

if __name__=='__main__':unittest.main()
