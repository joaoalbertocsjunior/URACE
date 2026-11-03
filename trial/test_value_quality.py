"""Quality and accounting fixtures are not native productivity/user-value evidence."""
from pathlib import Path
import copy,json,tempfile,time,unittest
from unittest.mock import patch
import accounting,output_quality as quality,repository_tasks as tasks,study_analysis,trial_supervisor,source_integrity

class UsageReconciliationTests(unittest.TestCase):
 def model(self,n=10):return {'inputTokens':n,'cacheCreationInputTokens':2,'cacheReadInputTokens':3,'outputTokens':4}
 def raw(self,**kw):
  r={'kind':'finished','id':'receipt','provider':'claude','tokens':None,'failure':'TimeoutError: Native wall cap exceeded'};r.update(kw);return r
 def test_retained_final_recovers_usage_but_not_success(self):
  r=self.raw(partial_usage={'final':{'modelUsage':{'main':self.model()},'usage':{'input_tokens':10,'cache_creation_input_tokens':2,'cache_read_input_tokens':3,'output_tokens':4}},'completed_message_usage':{}});old=copy.deepcopy(r);p=accounting.projected([r])[0];self.assertEqual(p['tokens'],19);self.assertEqual(p['failure'],r['failure']);self.assertEqual(r,old);self.assertTrue(p['accounting_correction']['execution_outcome_unchanged'])
 def test_explicit_zero_requires_all_zero_evidence(self):
  zero={k:0 for k in ('input_tokens','output_tokens','cache_creation_input_tokens','cache_read_input_tokens')};r=self.raw(partial_usage={'final':{'modelUsage':{},'usage':zero,'duration_api_ms':0,'total_cost_usd':0},'all_auxiliary_usage_known':True,'completed_message_usage':{}});self.assertEqual(accounting.projected([r])[0]['tokens'],0);del r['partial_usage']['final']['usage']['input_tokens'];self.assertIsNone(accounting.projected([r])[0]['tokens'])
 def test_partial_usage_remains_unknown_with_separate_lower_bound(self):
  usage={'input_tokens':1,'output_tokens':2,'cache_creation_input_tokens':3,'cache_read_input_tokens':4};r=self.raw(partial_usage={'final':None,'completed_message_usage':{'m':{'usage':usage}}});p=accounting.projected([r])[0];self.assertIsNone(p['tokens']);self.assertEqual(p['tokens_lower_bound'],10)
 def test_invalid_and_contradictory_counts_cannot_recover(self):
  for bad in [True,-1,float('nan')]:
   model=self.model();model['inputTokens']=bad;r=self.raw(model_usage={'m':model});self.assertIsNone(accounting.projected([r])[0]['tokens'])
  r=self.raw(partial_usage={'final':{'modelUsage':{'m':self.model(1)},'usage':{'input_tokens':999,'output_tokens':1,'cache_creation_input_tokens':0,'cache_read_input_tokens':0}}});self.assertIsNone(accounting.projected([r])[0]['tokens'])
 def test_correction_audit_is_idempotent_and_raw_ledger_unchanged(self):
  with tempfile.TemporaryDirectory() as d:
   b=Path(d);raw=json.dumps(self.raw(model_usage={'m':self.model()}))+'\n';(b/'ledger.jsonl').write_text(raw);first=accounting.reconcile(b);second=accounting.reconcile(b);self.assertEqual(first['new_audit_records'],1);self.assertEqual(second['new_audit_records'],0);self.assertEqual((b/'ledger.jsonl').read_text(),raw)
 def test_pending_and_orphaned_do_not_become_zero_cost_failures(self):
  rows=[{'kind':'reserved','id':'pending','provider':'codex','at_unix':100,'wall_cap_seconds':300},{'kind':'reserved','id':'orphan','provider':'claude','at_unix':1,'wall_cap_seconds':1,'owner_pid':99999999,'owner_start_ticks':'wrong'}];p=accounting.pending_status(rows,200);self.assertEqual(p[0]['status'],'LIVE_WITHIN_ALLOWANCE');self.assertEqual(p[1]['status'],'OWNER_GONE_TOTAL_UNKNOWN');self.assertIsNone(p[1]['tokens'])
 def test_interrupted_codex_is_lower_bound_not_final_total(self):
  r={'provider':'codex','failure':'TimeoutError','usage':{'total':{'inputTokens':10,'outputTokens':2,'totalTokens':12}},'tokens':12}
  accounting.settle(r,'codex');self.assertIsNone(r['tokens']);self.assertEqual(r['tokens_lower_bound'],12);self.assertFalse(r['accounting_details']['known'])
  r['turn_status']='completed';accounting.settle(r,'codex');self.assertEqual(r['tokens'],12)
 def test_malformed_partial_record_remains_unknown(self):
  r=self.raw(partial_usage={'completed_message_usage':{'m':None}});self.assertIsNone(accounting.projected([r])[0]['tokens'])
 def test_non_object_partial_usage_cannot_crash_projection(self):
  r=self.raw(partial_usage=['invalid']);self.assertIsNone(accounting.projected([r])[0]['tokens'])
 def test_final_counters_replace_inconsistent_derived_total(self):
  r={'usage':{'total':{'inputTokens':10,'outputTokens':2,'totalTokens':12}},'tokens':999};accounting.settle(r,'codex');self.assertEqual(r['tokens'],12)
 def test_dead_owner_is_not_reported_live_within_allowance(self):
  r={'kind':'reserved','id':'dead','provider':'claude','at_unix':100,'wall_cap_seconds':300,'owner_pid':99999999,'owner_start_ticks':'wrong'};self.assertEqual(accounting.pending_status([r],110)[0]['status'],'OWNER_GONE_TOTAL_UNKNOWN')
 def test_no_inference_has_explicit_zero_provenance(self):
  r={'provider':'codex','failure':'Quota unavailable before inference','inference_requested':False,'tokens':0};accounting.settle(r,'codex');self.assertTrue(r['accounting_details']['known']);self.assertEqual(r['usage_finality'],'NO_INFERENCE_REQUESTED');self.assertEqual(r['tokens'],0)
 def test_no_inference_cannot_hide_contradictory_nonzero_usage(self):
  r={'provider':'codex','inference_requested':False,'tokens':0,'usage':{'total':{'inputTokens':10,'outputTokens':2,'totalTokens':12}}};accounting.settle(r,'codex');self.assertIsNone(r['tokens']);self.assertFalse(r['accounting_details']['known']);self.assertEqual(r['tokens_lower_bound'],12)
 def test_measurement_summary_separates_pending_unknown_and_lower_bound(self):
  import spec_trial
  rows=[{'kind':'reserved','id':i,'provider':'codex','at_unix':1} for i in ['a','b']]+[{'kind':'finished','id':'a','provider':'codex','tokens':None,'tokens_lower_bound':12}];r=spec_trial.resource_metrics(rows);self.assertEqual(r['inflight_calls'],1);self.assertEqual(r['finished_unknown_usage'],1);self.assertEqual(r['reported_tokens_lower_bound'],12);self.assertEqual(r['known_tokens'],0)

class OutputQualityTests(unittest.TestCase):
 def values(self,rows):return [{'id':r['id'],'value':r['expected'],'modules_agree':True,'repeat_equal':True} for r in rows]
 def test_primary_perfect_cannot_hide_bad_generalization(self):
  primary=tasks.cases('navigation');extra=quality.cases('navigation');values=self.values(primary+extra);values[-1]['value']='wrong';r=quality.grade('navigation',1,primary,extra,values);self.assertEqual(r['quality_score'],100);self.assertFalse(r['quality']['gate_passed']);self.assertLess(r['quality']['robustness_pct'],100)
 def test_nondeterminism_and_module_disagreement_fail_quality_gate(self):
  primary=tasks.cases('receipts');extra=quality.cases('receipts');values=self.values(primary+extra);values[0]['repeat_equal']=False;r=quality.grade('receipts',1,primary,extra,values);self.assertFalse(r['quality']['gate_passed']);self.assertEqual(r['quality_score'],100)
  values[0]['modules_agree']=False;r=quality.grade('receipts',1,primary,extra,values);self.assertFalse(r['validated'])
 def test_real_quality_and_unmeasured_human_axes_are_separate(self):
  primary=tasks.cases('recovery');extra=quality.cases('recovery');r=quality.grade('recovery',1,primary,extra,self.values(primary+extra));self.assertTrue(r['quality']['gate_passed']);self.assertEqual(r['quality']['covered_cases'],144);self.assertIsNone(r['quality']['usability']);self.assertIsNone(r['quality']['maintainability']);self.assertIsNone(r['quality']['observed_user_benefit'])
 def test_regressions_are_counted_against_same_case_baseline(self):
  primary=tasks.cases('navigation');extra=quality.cases('navigation');before=quality.grade('navigation',1,primary,extra,self.values(primary+extra));after=self.values(primary+extra);after[0]['value']='wrong';r=quality.grade('navigation',1,primary,extra,after,baseline=before);self.assertIn(primary[0]['id'],r['quality']['regressed_case_ids'])
 def test_case_sets_and_contracts_are_stable_and_distinct(self):
  for f in tasks.FAMILIES:
   self.assertEqual(len(quality.cases(f)),48);self.assertTrue({r['id'] for r in quality.cases(f)}.isdisjoint(r['id'] for r in tasks.cases(f)));self.assertEqual(quality.contract(f),quality.contract(f))
  self.assertNotEqual(quality.contract('requirements_change',1),quality.contract('requirements_change',2))
 def test_unmeasured_quality_never_becomes_a_perfect_score(self):
  r=quality.summary([{'validated':True}]);self.assertEqual(r['quality_unmeasured_workflows'],1);self.assertIsNone(r['mean_primary_correctness_pct_on_measured'])
 def test_allocation_needs_quality_evidence_in_addition_to_cost(self):
  rows=[]
  for i in range(35):
   a={'complete':True,'validated':True,'delivered':True,'family':'navigation','queued_unix':100+i,'elapsed_seconds':10,'native_receipts':[{'id':'a'+str(i),'tokens':100}]};z={**a,'elapsed_seconds':1,'native_receipts':[{'id':'z'+str(i),'tokens':10}]};rows.append((a,z))
  r=study_analysis.compare(rows);self.assertFalse(r['quality_complete']);self.assertFalse(r['observed_bounded_advantage'])

class ReviewAndPolicyTests(unittest.TestCase):
 def test_warning_only_review_does_not_look_like_crashed_worker(self):
  import review
  with tempfile.TemporaryDirectory() as d,patch.object(trial_supervisor,'BASE',Path(d)),patch.object(review,'main',return_value=1):
   (Path(d)/'operational-review-latest.json').write_text('{"runtime_integrity_pass":true,"evidence_warnings":["partial usage"]}');self.assertEqual(trial_supervisor.review_step()['status'],'COMPLETED_WITH_EVIDENCE_LIMITATIONS')
 def test_real_integrity_failure_still_returns_failure(self):
  import review
  with tempfile.TemporaryDirectory() as d,patch.object(trial_supervisor,'BASE',Path(d)),patch.object(review,'main',return_value=1):
   (Path(d)/'operational-review-latest.json').write_text('{"runtime_integrity_pass":false,"evidence_warnings":["partial usage"]}');self.assertEqual(trial_supervisor.review_step(),1)
 def test_value_controls_do_not_unfreeze_authority(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'config.json';base={'authority':{'reserved':['publish']}};p.write_text(json.dumps(base));expected=source_integrity.descriptor(p);base['value_discovery']={'enabled':True,'external_research':False,'research_seconds':30};p.write_text(json.dumps(base));self.assertTrue(source_integrity.matches(p,expected));base['authority']['reserved']=[];p.write_text(json.dumps(base));self.assertFalse(source_integrity.matches(p,expected))
 def test_invalid_controls_cannot_bypass_source_integrity(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'config.json';p.write_text('{}');expected=source_integrity.descriptor(p);p.write_text('{"value_discovery":{"research_seconds":0}}');self.assertFalse(source_integrity.matches(p,expected))

class NativeFailedTurnTests(unittest.TestCase):
 def test_failed_turn_error_is_preserved_and_classifiable(self):
  import native_agents
  messages=[{'id':1,'result':{}},{'id':2,'result':{'thread':{'id':'t'},'model':'m'}},{'id':3,'result':{'data':[{'name':'project','tools':{}}]}},{'id':5,'result':{'ordinaryUsageAllowed':True}},{'id':4,'result':{}},{'method':'turn/completed','params':{'turn':{'status':'failed','error':{'message':'Quota exceeded','kind':'capacity'}}}}]
  class Client:
   def __init__(self,*args,**kwargs):self.rows=iter(messages)
   def send(self,value):pass
   def line(self):return json.dumps(next(self.rows))
   def close(self):pass
  record={'wall_limit_seconds':60,'requested_model':'m','effort':'medium'}
  with patch.object(native_agents,'Transport',Client):
   with self.assertRaisesRegex(RuntimeError,'Quota exceeded'):native_agents.codex('fixture',Path('/tmp'),record,Path('/tmp/context'))
  self.assertEqual(record['turn_error']['kind'],'capacity');self.assertEqual(record['turn_status'],'failed');self.assertTrue(record['inference_requested'])

class PausedMetadataTests(unittest.TestCase):
 def test_paused_trial_inspection_cannot_start_metadata_service(self):
  import spec_trial
  with tempfile.TemporaryDirectory() as d,patch.object(spec_trial,'BASE',Path(d)/'trial'),patch.object(spec_trial.subprocess,'run',side_effect=AssertionError('Paused services must not start')):
   (Path(d)/'.migration-in-progress').write_text('user pause');self.assertEqual(spec_trial.eligible()[0],[])
 def test_paused_availability_does_not_probe_clients(self):
  import availability
  with tempfile.TemporaryDirectory() as d,patch.object(availability,'BASE',Path(d)/'trial'),patch.object(availability,'probe_codex',side_effect=AssertionError('No probe')):
   (Path(d)/'.migration-in-progress').write_text('user pause');self.assertEqual(availability.main(),0)
 def test_paused_governor_rejects_direct_native_launch(self):
  import resource_governor as g
  with tempfile.TemporaryDirectory() as d,patch.object(g,'BASE',Path(d)/'trial'):
   (Path(d)/'.migration-in-progress').write_text('user pause')
   with self.assertRaisesRegex(RuntimeError,'Owner pause'):g.reserve(Path(d)/'trial','codex')

class ClaudeDispatchAccountingTests(unittest.TestCase):
 def test_explicit_no_dispatch_claude_is_zero_but_unknown_legacy_stays_unknown(self):
  r={'provider':'claude','failure':'metadata probe timed out','inference_requested':False};accounting.settle(r,'claude');self.assertEqual(r['tokens'],0);self.assertEqual(r['usage_finality'],'NO_INFERENCE_REQUESTED');self.assertTrue(r['accounting_details']['known'])
  legacy={'provider':'claude','tokens':None,'failure':'metadata probe timed out'};accounting.settle(legacy,'claude');self.assertIsNone(legacy['tokens'])
 def test_no_dispatch_flag_cannot_hide_claude_nonzero_counters(self):
  r={'inference_requested':False,'model_usage':{'main':{'inputTokens':1,'outputTokens':2,'cacheCreationInputTokens':0,'cacheReadInputTokens':0}}};accounting.settle(r,'claude');self.assertIsNone(r['tokens']);self.assertEqual(r['usage_finality'],'CONTRADICTORY_USAGE');self.assertEqual(r['tokens_lower_bound'],3)
 def test_native_metadata_timeout_never_dispatches_and_settles_failure(self):
  import native_agents as native,subprocess
  from contextlib import nullcontext
  from types import SimpleNamespace
  with tempfile.TemporaryDirectory() as directory:
   b=Path(directory);workspace=b/'workspace';workspace.mkdir();(b/'contract.json').write_text(json.dumps({'product_id':'fixture','target_product':'fixture'}))
   with patch.object(native,'BASE',b),patch.object(native,'operations_root',return_value=b),patch('common._governor',return_value=SimpleNamespace(reserve=lambda *a,**k:'metadatafixture')),patch.object(native,'guard',return_value=nullcontext()),patch.object(native.subprocess,'run',side_effect=subprocess.TimeoutExpired(['claude','--version'],10)),patch.object(native,'claude',side_effect=AssertionError('must not dispatch')):
    value,envelope,r=native.run('claude','packet',workspace,b/'public.json',[],model='fixture-model',effort='high',job_id='fixture')
   self.assertIsNone(value);self.assertIn('TimeoutExpired',r['failure']);self.assertIs(r['inference_requested'],False);self.assertEqual(r['tokens'],0);self.assertGreaterEqual(r['wall_seconds'],0);self.assertEqual(r['usage_finality'],'NO_INFERENCE_REQUESTED');self.assertTrue((b/'transport/metadatafixture.json').exists())
 def test_partial_claude_prompt_write_is_conservatively_inference_attempt(self):
  import native_agents as native
  from types import SimpleNamespace
  fake=SimpleNamespace(write=lambda data:(_ for _ in ()).throw(TimeoutError('partial input write')),close=lambda:None)
  with tempfile.TemporaryDirectory() as directory:
   b=Path(directory);r={'tokens':None,'inference_requested':False,'requested_model':'fixture-model','effort':'high','wall_limit_seconds':120}
   with patch.object(native,'Transport',return_value=fake),patch.object(native,'next_claude_controls',return_value={}):
    with self.assertRaises(TimeoutError):native.claude('packet',b,r,b/'context.json')
   self.assertTrue(r['inference_requested']);r['failure']='partial input write';accounting.settle(r,'claude');self.assertIsNone(r['tokens'])

class DispatchContradictionProjectionTests(unittest.TestCase):
 def test_partial_usage_contradiction_is_never_projected_into_final_usage(self):
  r={'kind':'finished','provider':'claude','inference_requested':False,'partial_usage':{'completed_message_usage':{'m':{'usage':{'input_tokens':1,'output_tokens':2,'cache_creation_input_tokens':0,'cache_read_input_tokens':0}}}}};accounting.settle(r,'claude');self.assertEqual(r['usage_finality'],'CONTRADICTORY_USAGE');self.assertIsNone(r['tokens']);self.assertIsNone(accounting.projected([r])[0]['tokens'])
 def test_final_usage_contradiction_is_never_projected_into_final_usage(self):
  r={'kind':'finished','provider':'claude','inference_requested':False,'model_usage':{'main':{'inputTokens':1,'outputTokens':2,'cacheCreationInputTokens':0,'cacheReadInputTokens':0}}};accounting.settle(r,'claude');self.assertIsNone(accounting.projected([r])[0]['tokens'])
