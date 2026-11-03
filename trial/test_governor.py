import concurrent.futures,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import resource_governor as g
class Governor(unittest.TestCase):
 def setUp(self):self.now=1000000;self.p={'total_token_guard':2400000,'daily_token_guard':600000,'provider_window_token_guard':180000,'daily_native_seconds':3600,'provider_window_native_seconds':900,'failure_backoff_seconds':10800,'ends_unix':2000000}
 def row(self,i,at=None,provider='codex'):return {'kind':'reserved','id':str(i),'provider':provider,'at_unix':self.now if at is None else at}
 def result(self,rows,done,p=None):return g.evaluate('codex',rows,done,p or self.p,self.now)
 def test_many_cheap_calls_no_monthly_call_cap(self):
  rows=[self.row(i,self.now-200000) for i in range(1000)];done={r['id']:{'tokens':1,'wall_seconds':1,'prompt_sha256':r['id']} for r in rows};self.assertTrue(self.result(rows,done)['eligible'])
 def test_daily_tokens(self):
  r=self.row(1,self.now-20000);self.assertIn('shared_daily_token_guard',self.result([r],{'1':{'tokens':551000,'wall_seconds':1}})['reasons'])
 def test_null_spending_caps_allow_large_usage_without_resetting_accounting(self):
  p=dict(self.p,**{k:None for k in ('total_token_guard','daily_token_guard','provider_window_token_guard','daily_native_seconds','provider_window_native_seconds')})
  result=self.result([self.row(1)],{'1':{'tokens':10**12,'wall_seconds':10**9}},p)
  self.assertTrue(result['eligible']);self.assertGreater(result['budget_checks']['shared_daily_token_guard']['including_next_reservation'],10**12)
 def test_null_spending_caps_preserve_runaway_and_provider_backoff(self):
  p=dict(self.p,**{k:None for k in ('total_token_guard','daily_token_guard','provider_window_token_guard','daily_native_seconds','provider_window_native_seconds')})
  rows=[self.row(i) for i in range(10)];done={r['id']:{'tokens':1,'wall_seconds':1,'prompt_sha256':'same'} for r in rows}
  self.assertIn('repeated_identical_prompt_loop',self.result(rows,done,p)['reasons'])
  self.assertIn('reported_provider_capacity_backoff',self.result([self.row(1)],{'1':{'tokens':1,'wall_seconds':1,'failure':'quota exceeded'}},p)['reasons'])
 def test_provider_window_tokens(self):self.assertIn('provider_5h15m_token_guard',self.result([self.row(1)],{'1':{'tokens':131000,'wall_seconds':1}})['reasons'])
 def test_unknown_usage_keeps_reservation(self):self.assertFalse(self.result([self.row(i) for i in range(3)],{})['eligible'])
 def test_native_seconds(self):self.assertIn('provider_5h15m_native_seconds',self.result([self.row(1)],{'1':{'tokens':1,'wall_seconds':810}})['reasons'])
 def test_independent_provider_window(self):self.assertTrue(self.result([self.row(1,provider='claude')],{'1':{'tokens':131000,'wall_seconds':810}})['eligible'])
 def test_failures_back_off(self):
  rows=[self.row(i) for i in range(3)];self.assertIn('three_consecutive_native_failures',self.result(rows,{str(i):{'tokens':0,'wall_seconds':1,'failure':'quota'} for i in range(3)})['reasons'])
 def test_unknown_usage_charges_actual_selected_wall_reservation(self):
  row=self.row(1);row['wall_cap_seconds']=480
  p=dict(self.p,provider_window_native_seconds=600,reservation_native_seconds=480)
  self.assertIn('provider_5h15m_native_seconds',self.result([row],{},p)['reasons'])
 def test_duplicate_ledgers_deduplicated(self):
  with tempfile.TemporaryDirectory() as d,patch.object(g,'ROOT',Path(d)/'ops'):
   for name in g.ROOTS[:2]:
    p=Path(d)/name;p.mkdir();(p/'ledger.jsonl').write_text(json.dumps(self.row(1))+'\n')
   self.assertEqual(len(g.records()[0]),1)
 def test_external_runtime_is_not_read_from_an_isolated_operations_root(self):
  with tempfile.TemporaryDirectory() as d,patch.object(g,'ROOT',Path(d)/'ops'):
   self.assertEqual(g.external_roots(),[]);self.assertEqual(g.records()[0],[])
 def test_reservations_record_product_and_trial_identity(self):
  with tempfile.TemporaryDirectory() as d,patch.object(g,'ROOT',Path(d)/'ops'),patch.object(g.time,'time',return_value=self.now):
   g.ROOT.mkdir();(g.ROOT/'resource-policy.json').write_text(json.dumps(self.p));base=Path(d)/'productive-native-30d-v2';base.mkdir();(base/'contract.json').write_text(json.dumps(dict(product_id='p',target_product='Product',trial_id='t')))
   g.reserve(base,'codex');row=json.loads((base/'ledger.jsonl').read_text());self.assertEqual(row['product_id'],'p');self.assertEqual(row['trial_id'],'t')
 def test_atomic_shared_reservations(self):
  with tempfile.TemporaryDirectory() as d,patch.object(g,'ROOT',Path(d)/'ops'),patch.object(g.time,'time',return_value=self.now):
   root=g.ROOT;root.mkdir();p=dict(self.p,total_token_guard=100000,provider_window_token_guard=100000);(root/'resource-policy.json').write_text(json.dumps(p));bases=[root.parent/n for n in ('productive-native-30d-v2','autonomous-maintenance-v1')]
   for base in bases:base.mkdir();(base/'contract.json').write_text('{}')
   with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:ids=list(pool.map(lambda b:g.reserve(b,'codex'),bases))
   self.assertEqual(len(set(ids)),2)
   with self.assertRaisesRegex(RuntimeError,'Shared resource guard'):g.reserve(bases[0],'claude')
 def test_runaway_identical_prompts(self):
  rows=[self.row(i) for i in range(10)];done={r['id']:{'tokens':1,'wall_seconds':1,'prompt_sha256':'same'} for r in rows};self.assertIn('repeated_identical_prompt_loop',self.result(rows,done)['reasons'])

 def test_single_observed_capacity_failure_is_shared_and_provider_specific(self):
  row=self.row(1);done={'1':{'tokens':0,'wall_seconds':1,'failure':"You've hit your limit"}}
  self.assertIn('reported_provider_capacity_backoff',self.result([row],done)['reasons'])
  self.assertNotIn('reported_provider_capacity_backoff',g.evaluate('claude',[row],done,self.p,self.now)['reasons'])
  self.assertNotIn('reported_provider_capacity_backoff',g.evaluate('codex',[row],done,self.p,self.now+18902)['reasons'])
 def test_output_limit_does_not_trigger_account_capacity_backoff(self):
  self.assertNotIn('reported_provider_capacity_backoff',self.result([self.row(1)],{'1':{'tokens':100,'wall_seconds':1,'failure':'response exceeded8192 output token maximum'}})['reasons'])

 def test_status_forwards_actual_next_wall_and_preserves_default(self):
  from contextlib import nullcontext
  with patch.object(g,'guard',return_value=nullcontext()),patch.object(g,'records',return_value=([],{})),patch.object(Path,'read_text',return_value=json.dumps(self.p)),patch.object(g,'evaluate',return_value={'eligible':True}) as evaluate:
   g.status('codex',next_wall=180);self.assertEqual(evaluate.call_args.kwargs['next_wall'],180)
   g.status('codex');self.assertIsNone(evaluate.call_args.kwargs['next_wall'])
 def test_short_task_fits_without_weakening_long_task_ceiling(self):
  policy=dict(self.p,provider_window_native_seconds=3600,daily_native_seconds=20000)
  rows=[self.row(1)];done={'1':{'tokens':1,'wall_seconds':3180}}
  self.assertTrue(g.evaluate('codex',rows,done,policy,self.now,next_wall=180)['eligible'])
  self.assertIn('provider_5h15m_native_seconds',g.evaluate('codex',rows,done,policy,self.now,next_wall=480)['reasons'])
if __name__=='__main__':unittest.main()

class ManagedOperations(unittest.TestCase):
 def test_registry_rejects_escape_before_reading_any_registered_path(self):
  with tempfile.TemporaryDirectory() as d,patch.object(g,'ROOT',Path(d)):
   (Path(d)/'resource-policy.json').write_text(json.dumps({'managed_operation_roots':['../urace']}))
   with self.assertRaises(ValueError):g.registered_roots()
 def test_operational_ledger_counts_toward_existing_history(self):
  with tempfile.TemporaryDirectory() as d,patch.object(g,'ROOT',Path(d)/'ops'):
   g.ROOT.mkdir();(g.ROOT/'resource-policy.json').write_text(json.dumps({'managed_operation_roots':['productive-operations-1000000000']}));base=Path(d)/'productive-operations-1000000000';base.mkdir();(base/'ledger.jsonl').write_text(json.dumps({'kind':'reserved','id':'ongoing','provider':'codex','at_unix':1})+'\n');self.assertEqual(g.records()[0][0]['id'],'ongoing')

class StructuredResetRecovery(unittest.TestCase):
 def decision(self,now=1100,reset=1000,inflight=False):
  row={'id':'failed','provider':'claude','at_unix':900,'wall_cap_seconds':300}
  done={'failed':{'failure':"You've hit your limit",'wall_seconds':1,'tokens':0,'quota_events':[{'status':'rejected','resetsAt':reset}]}}
  rows=[row]+([{'id':'pending','provider':'claude','at_unix':now,'wall_cap_seconds':300}] if inflight else [])
  policy={'total_token_guard':None,'daily_token_guard':None,'provider_window_token_guard':None,'daily_native_seconds':None,'provider_window_native_seconds':None,'failure_backoff_seconds':10800,'ends_unix':999999}
  return g.evaluate('claude',rows,done,policy,now)
 def test_reset_plus_margin_allows_real_retry(self):self.assertTrue(self.decision()['eligible']);self.assertFalse(self.decision()['capacity_retry']['availability_proven'])
 def test_before_reset_does_not_retry(self):self.assertFalse(self.decision(now=1059)['eligible'])
 def test_existing_recovery_inflight_prevents_duplicate_probe(self):self.assertFalse(self.decision(inflight=True)['eligible'])
 def test_auth_or_warning_cannot_establish_recovery(self):
  result={'quota_events':[{'status':'allowed_warning','resetsAt':1000}]};self.assertEqual(g.capacity_retry(result,901)['source'],'fallback_5h15m')
 def test_invalid_reset_evidence_uses_bounded_fallback(self):
  for reset in [True,'1000',float('nan'),-1,999999999]:self.assertFalse(self.decision(reset=reset)['eligible'])
 def test_multiple_rejected_windows_use_later_reset(self):
  r={'quota_events':[{'status':'rejected','resetsAt':1000},{'status':'rejected','resetsAt':2000}]};self.assertEqual(g.capacity_retry(r,901)['retry_at_unix'],2060)

class LongQuotaResetTests(unittest.TestCase):
 def test_valid_weekly_reset_is_not_shortened_to_fallback(self):
  end=1000000;reset=end+86400;record={'quota_events':[{'status':'rejected','resetsAt':reset,'rateLimitType':'seven_day'}]};value=g.capacity_retry(record,end);self.assertEqual(value['retry_at_unix'],reset+60);self.assertEqual(value['source'],'provider_rejected_quota_reset');self.assertFalse(value['availability_proven'])
 def test_missing_or_invalid_reset_preserves_exact_fallback(self):
  end=1000000
  for value in ({},{'quota_events':[{'status':'rejected','resetsAt':end+604801}]},{'quota_events':[{'status':'allowed_warning','resetsAt':end+86400}]}):self.assertEqual(g.capacity_retry(value,end)['retry_at_unix'],end+18900)
