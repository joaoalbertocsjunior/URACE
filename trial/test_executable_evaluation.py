import ast,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from executable_cases import corpus,manifest,oracle_ready
from executable_scores import grade,aggregate,delta,summarize
from executable_sandbox import validate_source

class ExecutableAcceptance(unittest.TestCase):
 def test_corpus_is_fixed_and_covers_all_four_workflows(self):
  a,b=corpus(),corpus();self.assertEqual(a,b);self.assertEqual(len(manifest(a)['workflow_counts']),4);self.assertGreater(len(a),200)
 def test_oracles_are_not_in_executor_requests(self):
  for c in corpus():
   request={k:c[k] for k in ['id','function','args']};self.assertNotIn('expected',request);self.assertNotIn('error',request)
 def test_gold_outputs_score100_and_single_fault_is_visible(self):
  c=corpus();rows=[{'id':x['id'],**({'error':x['error']} if x['error'] else {'value':x['expected']})} for x in c]
  g=grade({'status':'EXECUTED','results':rows},c);self.assertEqual(g['quality_score'],100);self.assertTrue(g['validated_delivery'])
  rows[0]={'id':c[0]['id'],'value':None};g=grade({'status':'EXECUTED','results':rows},c);self.assertLess(g['quality_score'],100);self.assertFalse(g['validated_delivery'])
 def test_failed_artifact_scores0_without_claiming_tests_executed(self):
  g=grade({'status':'TIMEOUT'},corpus());self.assertEqual(g['quality_score'],0);self.assertEqual(g['tests_executed'],0)
 def test_macro_weights_do_not_give_large_workflow_extra_weight(self):
  c=[{'id':'a','workflow':'a','expected':1,'error':None}]+[{'id':str(i),'workflow':'b','expected':1,'error':None} for i in range(10)]
  g=grade({'status':'EXECUTED','results':[{'id':'a','value':1}]+[{'id':str(i),'value':0} for i in range(10)]},c);self.assertEqual(g['quality_score'],50)
 def test_cycle_does_not_block_unrelated_component(self):
  ops=[{'id':x,'status':'PLANNED'} for x in ['a','b','free']];edges=[{'from_id':'a','to_id':'b','kind':'START_TO_START'},{'from_id':'b','to_id':'a','kind':'START_TO_START'}]
  self.assertEqual(oracle_ready(ops,edges),['free'])
 def test_fully_working_delivery_required_for_effectiveness(self):
  c=corpus();g=grade({'status':'TIMEOUT'},c);entry={'grade':g,'end_to_end_seconds':5,'tokens':10};r=aggregate([entry]*3,3);self.assertEqual(r['effectiveness_pct'],0);self.assertEqual(r['validated_deliveries'],0)
 def test_incomplete_native_pairs_withhold_quality_delta(self):
  r=aggregate([],3);self.assertIsNone(r['quality_score']);self.assertIsNone(delta(r,r)['quality_percentage_points'])
 def test_zero_baseline_withholds_relative_gain(self):
  a={'quality_score':0,'effectiveness_pct':0,'median_end_to_end_seconds':0};b={'quality_score':100,'effectiveness_pct':100,'median_end_to_end_seconds':2};d=delta(a,b);self.assertEqual(d['quality_percentage_points'],100);self.assertIsNone(d['time']['improvement_pct'])
 def test_unknown_usage_does_not_become_zero_cost_efficiency(self):
  c=corpus();g=grade({'status':'EXECUTED','results':[{'id':x['id'],**({'error':x['error']} if x['error'] else {'value':x['expected']})} for x in c]},c)
  r=aggregate([{'grade':g,'tokens':None,'end_to_end_seconds':1}]*3,3);self.assertFalse(r['usage_complete']);self.assertIsNone(r['tokens_per_validated_delivery'])

class ArtifactBoundary(unittest.TestCase):
 def source(self,extra=''):
  return '\n'.join('def '+n+'(*args):\n    return None' for n in ['quality_delta','evidence_verdict','ready_operations','aggregate_records'])+'\n'+extra
 def test_pure_functions_are_accepted(self):validate_source(self.source())
 def test_i_o_and_introspection_are_rejected(self):
  for extra in ['import os','open("file")','import typing\ndef evil(): return typing.sys.modules','def evil(): return ().__class__','from typing import sys']:
   with self.assertRaises(ValueError):validate_source(self.source(extra))
 def test_missing_workflow_is_not_partial_success(self):
  with self.assertRaises(ValueError):validate_source('def quality_delta(a,b): return 0')


class EmptyEvaluationView(unittest.TestCase):
 def test_no_trial_is_reported_without_creating_state(self):
  from executable_scores import view,render
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);r=view(root);self.assertEqual(r['status'],'NOT_CONFIGURED');self.assertIsNone(r['quality_score']);self.assertIn('NOT_CONFIGURED',render(r));self.assertEqual(list(root.iterdir()),[])


class ScoreViewTests(unittest.TestCase):
 def test_baseline_and_identical_input_reference_are_labeled_honestly(self):
  import spec_trial as worker
  from executable_cases import HEADINGS,ANCHORS
  from executable_benchmark import context
  from executable_scores import view
  c=corpus();g=grade({'status':'EXECUTED','results':[{'id':x['id'],**({'error':x['error']} if x['error'] else {'value':x['expected']})} for x in c]},c)
  text='\n'.join('## '+h+'\n'+'\n'.join(ANCHORS.get(h,['Source contract.']))+'\n' for h in HEADINGS)
  with tempfile.TemporaryDirectory() as directory,patch.object(worker,'BASE',Path(directory)):
   root=Path(directory);(root/'trial-clock.json').write_text(json.dumps({'trial_id':'t'}));(root/'active-version.json').write_text(json.dumps({'version':2}));(root/'version-series.json').write_text(json.dumps({'root':'versions'}))
   for v in [0,1,2]:
    folder=root/'versions'/('v%06d'%v);folder.mkdir(parents=True);document=text+'\n## Unrelated\n'+str(v);(folder/'URACE.md').write_text(document);(folder/'manifest.json').write_text(json.dumps({'sha256':worker.digest(document),'parent_version':max(0,v-1)}))
   folder=root/'executable-evaluations/t/fixture';folder.mkdir(parents=True);signature=context(text)[1]
   runs=[{'provider':'codex','variant':variant,'repeat':repeat,'grade':g,'tokens':100,'end_to_end_seconds':2} for variant in ['baseline','candidate'] for repeat in range(3)]
   r={'id':'fixture','trial_id':'t','candidate_version':1,'baseline_version':0,'repetitions':3,'suite':manifest(c),'providers':['codex'],'profiles':{'codex':{'model':'m','native_effort':'medium'}},'runs':runs,'contexts':{'baseline':{'sha256':signature},'candidate':{'sha256':signature}}};(folder/'report.json').write_text(json.dumps(r))
   baseline=view(root,0);self.assertEqual(baseline['measured_version'],0);self.assertEqual(baseline['scorecard']['providers']['codex']['delta']['quality_percentage_points'],0);self.assertEqual(baseline['scorecard']['providers']['codex']['paired_repetitions'],0);self.assertFalse(baseline['scorecard']['providers']['codex']['observed_nonregressing_delivery_gain'])
   current=view(root,2);self.assertEqual(current['status'],'IDENTICAL_EVALUATED_INPUT_REFERENCE');self.assertFalse(current['new_execution_for_this_version']);self.assertEqual(current['measured_version'],1)
   r['contexts']['candidate']['sha256']='different-input';(folder/'report.json').write_text(json.dumps(r))
   current=view(root,2);self.assertEqual(current['measured_version'],0);self.assertFalse(current['new_execution_for_this_version']);self.assertEqual(current['scorecard']['providers']['codex']['candidate']['quality_score'],100)
 def test_improved_average_cannot_hide_a_regression(self):
  runs=[]
  for variant,q,cases in [('baseline',50,{'a':True,'b':False,'c':False}),('candidate',75,{'a':False,'b':True,'c':True})]:
   for repeat in range(3):runs.append({'provider':'codex','variant':variant,'repeat':repeat,'grade':{'quality_score':q,'validated_delivery':False,'case_results':cases},'tokens':100,'end_to_end_seconds':2})
  r={'id':'fixture','trial_id':'t','candidate_version':1,'baseline_version':0,'repetitions':3,'suite':{},'providers':['codex'],'profiles':{'codex':{}},'runs':runs}
  row=summarize(r)['providers']['codex'];self.assertGreater(row['delta']['quality_percentage_points'],0);self.assertEqual(row['case_regressions'],3);self.assertFalse(row['observed_nonregressing_quality_gain'])


class EquivalentInputReuse(unittest.TestCase):
 def test_equivalent_inputs_reuse_results_without_inventing_independent_pairs(self):
  from executable_benchmark import collect
  c=corpus();g=grade({'status':'EXECUTED','results':[{'id':x['id'],**({'error':x['error']} if x['error'] else {'value':x['expected']})} for x in c]},c)
  with tempfile.TemporaryDirectory() as directory:
   job=Path(directory);plan={'id':'fixture','trial_id':'t','candidate_version':2,'baseline_version':0,'repetitions':3,'suite':{},'providers':['codex'],'profiles':{'codex':{}},'comparison_kind':'IDENTICAL_INPUT_REFERENCE'}
   (job/'plan.json').write_text(json.dumps(plan));entries=[{'provider':'codex','repeat':i,'variant':'baseline','grade':g,'tokens':10,'end_to_end_seconds':1,'native_receipt_id':str(i)} for i in range(3)];(job/'codex-progress.json').write_text(json.dumps({'runs':entries}))
   r=collect(job);self.assertEqual(len(r['runs']),6);self.assertEqual(len({e['native_receipt_id'] for e in r['runs']}),3)
   row=r['scorecard']['providers']['codex'];self.assertEqual(row['paired_repetitions'],0);self.assertEqual(row['candidate']['quality_score'],100);self.assertFalse(row['observed_nonregressing_quality_gain'])


class OracleDomainAudit(unittest.TestCase):
 def test_normal_inputs_obey_normalized_relevance_and_clamp_cases_are_explicit(self):
  cases=[c for c in corpus() if c['workflow']=='evidence_verdict'];clamps=[c for c in cases if c.get('domain_case')=='clamp'];self.assertEqual(len(clamps),2)
  for c in cases:
   if c.get('domain_case')=='clamp':continue
   self.assertTrue(all(0<=e['credibility']<=1 and 0<=e['relevance']<=1 for e in c['args'][0]))
 def test_clamp_oracles_follow_the_explicit_source_arithmetic(self):
  c=[c for c in corpus() if c.get('domain_case')=='clamp'];self.assertAlmostEqual(c[0]['expected']['score'],2/3);self.assertEqual(c[1]['expected'],{'score':.25,'verdict':'OPERATOR_OVERRIDE'})

class DeferredEvaluationStatus(unittest.TestCase):
 def test_unavailable_providers_do_not_claim_all_inputs_measured(self):
  import executable_benchmark as benchmark
  import spec_trial as worker
  import controls
  with tempfile.TemporaryDirectory() as directory:
   base=Path(directory)
   for name,value in [('harness-manifest.json',{}),('trial-clock.json',{'trial_id':'t'}),('active-version.json',{'version':1})]:
    (base/name).write_text(json.dumps(value))
   enabled={'paused':False,'executor_enabled':True,'auto_goals':True,'executors':{'codex':{'enabled':True,'model':'m','native_effort':'medium'}}}
   with patch.object(controls,'effective',return_value=enabled),patch.object(benchmark,'check_image'),patch.object(worker,'eligible',return_value=([],{'codex':'quota'})),patch.object(benchmark,'choose_version',return_value=(None,{},[])):
    result=benchmark.run(base)
   self.assertEqual(result['status'],'WAITING_FOR_RESOURCES');self.assertEqual(result['waits'],{'codex':'quota'});self.assertEqual(result['additional_inference_calls'],0)

class ResourceEvidenceCompleteness(unittest.TestCase):
 def entries(self):return [{'grade':{'quality_score':100,'validated_delivery':True},'tokens':100,'end_to_end_seconds':10} for _ in range(3)]
 def test_missing_time_does_not_inflate_productivity(self):
  entries=self.entries();entries[0]['end_to_end_seconds']=None;r=aggregate(entries,3);self.assertIsNone(r['validated_deliveries_per_hour']);self.assertIsNone(r['median_end_to_end_seconds']);self.assertFalse(r['timing_complete'])
 def test_invalid_token_telemetry_is_not_measured_usage(self):
  for value in [True,-1,float('nan')]:
   entries=self.entries();entries[0]['tokens']=value;r=aggregate(entries,3);self.assertFalse(r['usage_complete']);self.assertIsNone(r['tokens_per_validated_delivery'])
 def test_delivery_recovery_is_not_a_functional_quality_gain(self):
  runs=[]
  for variant,quality,executed in [('baseline',0,0),('candidate',100,2)]:
   for repeat in range(3):runs.append({'provider':'codex','variant':variant,'repeat':repeat,'grade':{'quality_score':quality,'validated_delivery':bool(executed),'tests_executed':executed,'case_results':{'a':bool(executed),'b':bool(executed)}},'tokens':10,'end_to_end_seconds':1})
  r={'id':'fixture','trial_id':'t','candidate_version':1,'baseline_version':0,'repetitions':3,'suite':{},'providers':['codex'],'profiles':{'codex':{}},'runs':runs};row=summarize(r)['providers']['codex'];self.assertFalse(row['observed_nonregressing_quality_gain']);self.assertTrue(row['observed_nonregressing_delivery_gain'])

class MeasurementFreshness(unittest.TestCase):
 def test_old_evaluator_is_historical_in_rollups_not_current_quality(self):
  from snapshot_metadata import executable_measurement_view
  with tempfile.TemporaryDirectory() as directory:
   base=Path(directory);old={'id':'old','suite':{'suite':'old'},'scorecard':{'overall_quality_score':100}};(base/'executable-benchmark-latest.json').write_text(json.dumps(old))
   current,historical=executable_measurement_view(base);self.assertFalse(current['available']);self.assertIsNone(current['current_quality_score']);self.assertEqual(current['status'],'STALE_MEASUREMENT');self.assertEqual(historical,old)

class BaselineRollupProjection(unittest.TestCase):
 def test_matching_baseline_uses_version_projection_not_historical_candidate_score(self):
  from snapshot_metadata import executable_measurement_view
  with tempfile.TemporaryDirectory() as directory:
   base=Path(directory);folder=base/'versions/v000001';folder.mkdir(parents=True);(folder/'URACE.md').write_text('fixture')
   for name,value in [('active-version.json',{'version':1}),('version-series.json',{'root':'versions'})]:(base/name).write_text(json.dumps(value))
   profile={'model':'m','native_effort':'medium'};projected={'providers':{'codex':{'matched_profile':profile}},'overall_quality_score':70}
   raw={'id':'fixture','suite':manifest(corpus()),'contexts':{'baseline':{'sha256':'same'},'candidate':{'sha256':'different'}},'profiles':{'codex':profile},'scorecard':{'overall_quality_score':100}}
   (base/'executable-benchmark-latest.json').write_text(json.dumps(raw))
   with patch('executable_benchmark.context',return_value=('', 'same')),patch('controls.effective',return_value={}),patch('executable_benchmark.profiles',return_value={'codex':profile}),patch('executable_scores.view',return_value={'scorecard':projected,'measured_version':0,'status':'IDENTICAL_EVALUATED_INPUT_REFERENCE'}):
    visible,historical=executable_measurement_view(base)
   self.assertTrue(visible['available']);self.assertEqual(visible['scorecard'],projected);self.assertEqual(visible['active_version_projection']['measured_version'],0)
