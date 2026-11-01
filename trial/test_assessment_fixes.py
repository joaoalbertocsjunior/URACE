"""Controlled regression fixtures, never represented as real-user evidence."""
from pathlib import Path
import unittest,tempfile,json,time,hashlib
from unittest.mock import patch
import repository_tasks as tasks,study_analysis as analysis,downstream_study as downstream,project_tools as tools,project_work as work

class ContractTests(unittest.TestCase):
 def test_foreign_dependency_definition_is_explicit_and_public(self):
  self.assertIn('Filter requirement definitions to that project',tasks.brief('requirements_change'))
  public=tasks.cases('requirements_change',True);self.assertIsNone(public[-2]['expected']);self.assertEqual(public[-1]['expected'],'deliver-current');self.assertEqual(len(tasks.cases('requirements_change')),96)
 def test_independent_isolation_oracle(self):
  req=[{'id':'foreign','project_id':'other','criteria':'v1','priority':1,'dependencies':[]},{'id':'current','project_id':'p','criteria':'v2','priority':2,'dependencies':['foreign']}];self.assertIsNone(tasks.answer('requirements_change',[req,[{'id':'foreign','project_id':'p','criteria':'v1'}],'p']))

class AnalysisTests(unittest.TestCase):
 def row(self,arm='standalone',**kwargs):
  r={'id':arm,'provider':'codex','family':'navigation','effort':'medium','repeat':0,'phase':1,'arm':arm,'actual_providers':['codex'],'queued_unix':100,'elapsed_seconds':10,'complete':True,'validated':True,'delivered':True,'acceptance':{'quality':{'gate_passed':True,'measurement_complete':True,'primary_correctness_pct':100,'robustness_pct':100,'regressed_case_ids':[]}},'native_receipts':[{'id':arm,'tokens':100,'provider':'codex'}]};r.update(kwargs);return r
 def test_outage_does_not_poison_ordinary_efficiency(self):
  rows=[]
  for i in range(35):
   family=('navigation','receipts','recovery','requirements_change','interruption')[i%5];a=self.row(repeat=i,family=family);z=self.row('urace',repeat=i,family=family,elapsed_seconds=7,native_receipts=[{'id':'u'+str(i),'provider':'codex','tokens':70}]);a['native_receipts'][0]['id']='a'+str(i);rows += [a,z]
  a=self.row(family='failover',repeat=99,actual_providers=[],native_receipts=[],validated=False,delivered=False,fault_injection={'simulation':True});z=self.row('urace',family='failover',repeat=99,actual_providers=['claude'],fault_injection={'simulation':True});rows += [a,z]
  d=analysis.assessment(rows);self.assertTrue(d['ordinary_by_provider']['codex']['observed_bounded_advantage']);self.assertEqual(d['injected_continuity']['managed_deliveries'],1)
 def test_quota_error_is_not_interruption_recovery_evidence(self):
  a=self.row(family='interruption',validated=False,delivered=False,native_receipts=[{'id':'a','provider':'claude','tokens':0,'failure':"You've hit your limit"}]);self.assertEqual(analysis.category(a),'ACTUAL_PROVIDER_AVAILABILITY');d=analysis.assessment([a,self.row('urace',family='interruption')]);self.assertEqual(d['ordinary_by_provider']['codex']['pairs'],1);self.assertFalse(d['ordinary_by_provider']['codex']['observed_bounded_advantage']);self.assertEqual(d['actual_availability_pairs'],1)
 def test_failed_costs_and_unknowns_are_retained(self):
  a=self.row();b=self.row('failed',validated=False,delivered=False,native_receipts=[{'id':'failure','tokens':200,'provider':'codex'}]);self.assertEqual(analysis.resources([a,b])['tokens_per_validated_delivery'],300);b['native_receipts'][0]['tokens']=None;self.assertIsNone(analysis.resources([a,b])['tokens_per_validated_delivery'])
 def test_cached_input_is_not_counted_twice(self):
  r=self.row(native_receipts=[{'id':'a','tokens':120,'provider':'codex','wall_seconds':2,'accounting_details':{'known':True,'input_tokens':100,'cached_input_tokens_included_in_input':80,'output_tokens':20}}]);d=analysis.resources([r]);self.assertEqual(d['uncached_input_tokens'],20);self.assertEqual(d['cached_read_tokens'],80);self.assertEqual(d['known_tokens'],120)
 def test_zero_deliveries_cannot_qualify(self):
  pairs=[(self.row(validated=False,delivered=False),self.row('urace',validated=False,delivered=False,elapsed_seconds=1))]*35;self.assertFalse(analysis.compare(pairs)['observed_bounded_advantage'])
 def test_contract_quarantine_is_signature_bound_and_not_quota(self):
  with tempfile.TemporaryDirectory() as d:
   rows=[self.row(provider='codex' if i%2 else 'claude',validated=False,delivered=False,status='REJECTED_BY_ACCEPTANCE',acceptance={'case_results':{'private':False}},repeat=i) for i in range(4)]
   q=analysis.quarantine_contracts(Path(d),rows,{'navigation':'old-contract'});self.assertIn('old-contract',q);self.assertNotIn('new-contract',q)
 def test_transport_failures_do_not_quarantine_acceptance_contract(self):
  with tempfile.TemporaryDirectory() as d:
   rows=[self.row(provider=p,validated=False,delivered=False,native_receipts=[{'id':p,'tokens':0,'failure':'quota unavailable'}]) for p in ['codex','claude']]*3;self.assertEqual(analysis.quarantine_contracts(Path(d),rows,{'navigation':'c'}),{})

class ReferenceTests(unittest.TestCase):
 def reference(self,text):return {'text':text,'sha256':hashlib.sha256(text.encode()).hexdigest(),'version':2,'source_snapshot':'frozen-fixture'}
 def test_full_large_version_is_losslessly_sharded_and_indexed(self):
  with tempfile.TemporaryDirectory() as d:
   text=('# Scope\n'+'é'*1000+'\n')*1000;root=Path(d);r=downstream.prepare_reference(root,self.reference(text));index=json.loads((root/'SPECIFICATION_INDEX.json').read_text());reconstructed=''.join((root/c['file']).read_text() for c in index['chunks']);self.assertEqual(reconstructed,text);self.assertEqual(r['sha256'],hashlib.sha256(text.encode()).hexdigest());self.assertLess(len(tools.inventory(root)),100)
 def test_tampered_reference_never_silently_overwritten(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);ref=self.reference('# Scope\nTrusted specification');downstream.prepare_reference(root,ref);(root/'SPECIFICATION_000.md').write_text('modified');
   with self.assertRaisesRegex(RuntimeError,'changed'):downstream.prepare_reference(root,ref)
 def test_declared_reference_hash_is_checked(self):
  with tempfile.TemporaryDirectory() as d:
   ref=self.reference('source');ref['sha256']='wrong'
   with self.assertRaisesRegex(RuntimeError,'hash mismatch'):downstream.prepare_reference(Path(d),ref)
 def test_bounded_line_reads_keep_scope(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'source.md').write_text('one\ntwo\nthree\n');ctx={'workspace':d};self.assertEqual(tools.call(ctx,'read_file',{'path':'source.md','start_line':2,'end_line':2}),'two\n')
   with self.assertRaises(ValueError):tools.call(ctx,'read_file',{'path':'source.md','start_line':0})

class SchedulingTests(unittest.TestCase):
 def controls(self):return {'paused':False,'executor_enabled':True,'auto_goals':True,'executors':{'codex':{'enabled':True,'model':'fixture-model','native_effort':'medium'},'claude':{'enabled':False,'model':'other','native_effort':'medium'}}}
 def test_context_choice_needs_exact_model_and_qualified_finite_gain(self):
  with tempfile.TemporaryDirectory() as d:
   base=Path(d);data={'engine_sha256':'e','expires_unix':time.time()+1000,'recommendations':{'codex:navigation':{'pairs':35,'quality_nonregressing':True,'qualified':True,'contract':'c','model':'fixture-model','native_effort':'medium','native_client_version':'fixture','token_ratio':.75,'time_ratio':1.0}}};p=base/'context-routing.json';p.write_text(json.dumps(data))
   with patch('controls.effective',return_value=self.controls()),patch('qualification_protocol.native_clients',return_value={'codex':{'verified':True,'version':'fixture'}}):
    self.assertEqual(analysis.context_choice(base,'codex','navigation','e','c'),'compact');data['recommendations']['codex:navigation']['model']='different';p.write_text(json.dumps(data));self.assertEqual(analysis.context_choice(base,'codex','navigation','e','c'),'full')
 def test_round_robin_runs_all_three_lanes_in_one_caller(self):
  import repository_study
  with tempfile.TemporaryDirectory() as d,patch.object(repository_study,'run_one',return_value='repository') as ordinary,patch.object(downstream,'run_one',side_effect=lambda base,lane:lane) as extra:
   results=[downstream.step(Path(d)) for _ in range(3)];self.assertEqual(results,['repository','context','specification']);self.assertEqual(ordinary.call_count,1);self.assertEqual(extra.call_count,2)
 def test_pending_version_comparison_is_frozen(self):
  with tempfile.TemporaryDirectory() as d:
   b=Path(d);(b/'trial-clock.json').write_text(json.dumps({'trial_id':'fixture'}));ref={'baseline':{'text':'base','sha256':hashlib.sha256(b'base').hexdigest(),'version':0,'source_snapshot':'v0'},'candidate':{'text':'version2','sha256':hashlib.sha256(b'version2').hexdigest(),'version':2,'source_snapshot':'v2'}}
   with patch.object(downstream,'effective',return_value=self.controls()),patch.object(downstream,'_snapshot',return_value=ref):root,identity,_=downstream.plan(b,'specification')
   with patch.object(downstream,'effective',return_value=self.controls()),patch.object(downstream,'_snapshot',side_effect=AssertionError('must retain frozen version')):again,second,_=downstream.plan(b,'specification')
   self.assertEqual(root,again);self.assertEqual(identity['versions'],second['versions']);self.assertEqual((root/'candidate.md').read_text(),'version2')
 def test_completed_context_arm_advances_to_other_arm(self):
  import spec_trial,trial_supervisor
  with tempfile.TemporaryDirectory() as d:
   b=Path(d);(b/'trial-clock.json').write_text(json.dumps({'ends_unix':time.time()+1000}));(b/'repository-study-settings.json').write_text('{"enabled":true}');root=b/'cohort';directory=root/'codex-navigation-0/full';directory.mkdir(parents=True);(directory/'result.json').write_text('{}');identity={'repetitions':1,'models':{'codex':{'model':'fixture-model','effort':'medium'}},'arms':['full','compact']}
   def invoke(project,**kw):self.assertEqual(kw['context_profile'],'compact');raise RuntimeError('advanced to compact')
   with patch.object(trial_supervisor,'external_owner',return_value=None),patch.object(downstream,'effective',return_value=self.controls()),patch.object(downstream,'plan',return_value=(root,identity,self.controls())),patch.object(spec_trial,'eligible',return_value=(['codex'],{})),patch.object(work,'run',side_effect=invoke):
    with self.assertRaisesRegex(RuntimeError,'advanced to compact'):downstream.run_one(b,'context')

class DeliveryProtocolTests(unittest.TestCase):
 def test_reference_mutation_cannot_publish(self):
  import test_user_benefit as fixture
  helper=fixture.ProjectWorkTests();helper.calls=[]
  with tempfile.TemporaryDirectory() as d:
   base,project,controls=helper.setup_project(d);text='# Product purpose\nPreserve project isolation.';reference={'text':text,'sha256':hashlib.sha256(text.encode()).hexdigest(),'version':1}
   def tamper(p,prompt,workspace,*args,**kwargs):
    value=helper.invoke(p,prompt,workspace,*args,**kwargs);(workspace/'SPECIFICATION_000.md').write_text('tampered');return value
   with patch.object(work,'effective',return_value=controls),patch.object(work,'container',side_effect=helper.execute),patch.object(work,'evaluate',side_effect=helper.acceptance):r=work.run(project,base=base,provider='codex',reference=reference,invoke=tamper,eligibility=lambda:(['codex','claude'],{}))
   self.assertFalse(r['delivered']);self.assertEqual(r['failure_category'],'REFERENCE_MUTATION');self.assertFalse(list((work.state_root(project,base)/'versions').glob('*')))
 def test_requirement_revision_finishes_both_phases_without_other_work(self):
  import spec_trial,trial_supervisor
  from datetime import datetime,timezone
  with tempfile.TemporaryDirectory() as d:
   b=Path(d);(b/'trial-clock.json').write_text(json.dumps({'ends_unix':time.time()+1000}));(b/'repository-study-settings.json').write_text('{"enabled":true}');root=b/'cohort';root.mkdir();controls=SchedulingTests().controls();identity={'lane':'context','repetitions':1,'models':{'codex':{'model':'fixture-model','effort':'medium'}},'arms':['full','compact']};queued=time.time()-30;active=queued+2;calls=[]
   def phase_work(project,**kw):
    phase=work.declaration(project)['phase'];calls.append(phase);self.assertEqual(kw['run_id'],'phase-'+str(phase))
    if phase==2:
     self.assertEqual(kw['queued_unix'],queued);self.assertEqual(kw['execution_started_unix'],active);self.assertEqual((project/'logic.py').read_text(),'phase1 logic')
    folder=work.state_root(project,b)/('runs/phase-'+str(phase));folder.mkdir(parents=True);workspace=folder/'workspace';workspace.mkdir();(workspace/'app.py').write_text('phase'+str(phase)+' app');(workspace/'logic.py').write_text('phase'+str(phase)+' logic');r={'id':'p'+str(phase),'phase':phase,'phase_started_unix':queued+(10 if phase==2 else 0),'finished_at':datetime.fromtimestamp(queued+(8 if phase==1 else 20),timezone.utc).isoformat(),'queued_unix':queued,'execution_started_unix':active,'complete':True,'delivered':True,'validated':True,'candidate_workspace':str(workspace),'native_receipts':[{'id':'receipt'+str(phase),'provider':'codex','tokens':10}],'timing':{'baseline_seconds':1,'acceptance_seconds':1}};(folder/'result.json').write_text(json.dumps(r));return r
   with patch.object(trial_supervisor,'external_owner',return_value=None),patch.object(downstream,'effective',return_value=controls),patch.object(downstream,'plan',return_value=(root,identity,controls)),patch.object(downstream,'_status',return_value={'done':True}) as status,patch.object(downstream,'FAMILIES',('requirements_change',)),patch.object(spec_trial,'eligible',return_value=(['codex'],{})),patch.object(work,'run',side_effect=phase_work):downstream.run_one(b,'context')
   self.assertEqual(calls,[1,2]);self.assertEqual(status.call_count,1);final=json.loads((root/'codex-requirements_change-0/full/result.json').read_text());self.assertEqual(final['tokens'],20);self.assertAlmostEqual(final['phase_scheduling_gap_seconds'],2,places=5);self.assertEqual(final['timing']['baseline_seconds'],2)
 def test_withdrawn_frozen_version_reselects_next_reference(self):
  with tempfile.TemporaryDirectory() as d:
   b=Path(d);(b/'trial-clock.json').write_text(json.dumps({'trial_id':'fixture'}));controls=SchedulingTests().controls();ref={'baseline':{'text':'base','sha256':hashlib.sha256(b'base').hexdigest(),'version':0,'source_snapshot':'v0'},'candidate':{'text':'version2','sha256':hashlib.sha256(b'version2').hexdigest(),'version':2,'source_snapshot':'v2'}}
   with patch.object(downstream,'effective',return_value=controls),patch.object(downstream,'_snapshot',return_value=ref):root,_,_=downstream.plan(b,'specification')
   (root/'summary.json').write_text('{"status":"FROZEN_VERSION_WITHDRAWN"}');ref['candidate']={'text':'version3','sha256':hashlib.sha256(b'version3').hexdigest(),'version':3,'source_snapshot':'v3'}
   with patch.object(downstream,'effective',return_value=controls),patch.object(downstream,'_snapshot',return_value=ref):next_root,_,_=downstream.plan(b,'specification')
   self.assertNotEqual(root,next_root);self.assertEqual((root/'candidate.md').read_text(),'version2')


class AvailabilityBudgetTests(unittest.TestCase):
 def test_unavailable_queued_work_does_not_expire_without_attempts(self):
  import test_user_benefit as fixture
  helper=fixture.ProjectWorkTests();helper.calls=[]
  with tempfile.TemporaryDirectory() as d:
   base,project,controls=helper.setup_project(d);queued=time.time()-20000
   with patch.object(work,'effective',return_value=controls):r=work.run(project,base=base,provider='codex',queued_unix=queued,run_id='wait',eligibility=lambda:([],{'codex':'headroom'}),invoke=helper.invoke)
   self.assertFalse(r['complete']);self.assertEqual(r['status'],'AWAITING_EXECUTOR');self.assertEqual(r['queued_unix'],queued);self.assertIsNone(r['execution_started_unix']);self.assertEqual(r['active_elapsed_seconds'],0);self.assertEqual(helper.calls,[])
 def test_waited_job_can_start_and_retains_queue_latency(self):
  import test_user_benefit as fixture
  helper=fixture.ProjectWorkTests();helper.calls=[]
  with tempfile.TemporaryDirectory() as d:
   base,project,controls=helper.setup_project(d);queued=time.time()-20000
   with patch.object(work,'effective',return_value=controls),patch.object(work,'container',side_effect=helper.execute),patch.object(work,'evaluate',side_effect=helper.acceptance):r=work.run(project,base=base,provider='codex',queued_unix=queued,eligibility=lambda:(['codex'],{}),invoke=helper.invoke)
   self.assertTrue(r['delivered']);self.assertGreater(r['elapsed_seconds'],20000);self.assertLess(r['active_elapsed_seconds'],30)
 def test_original_active_budget_cannot_be_renewed_for_later_phase(self):
  import test_user_benefit as fixture
  helper=fixture.ProjectWorkTests();helper.calls=[]
  with tempfile.TemporaryDirectory() as d:
   base,project,controls=helper.setup_project(d)
   with patch.object(work,'effective',return_value=controls):r=work.run(project,base=base,provider='codex',execution_started_unix=time.time()-1000,eligibility=lambda:(['codex'],{}),invoke=helper.invoke)
   self.assertTrue(r['complete']);self.assertEqual(r['status'],'ELAPSED_BUDGET_EXHAUSTED');self.assertEqual(helper.calls,[])


class IdleAdmissionTests(unittest.TestCase):
 def test_idle_ticks_reuse_one_metadata_check(self):
  from trial_supervisor import CapacityAdmission
  calls=[];now=[100]
  def probe():calls.append(now[0]);return [],{'codex':'headroom'}
  gate=CapacityAdmission(probe,clock=lambda:now[0]);self.assertFalse(gate.ready())
  for n in range(1,30):now[0]=100+n;self.assertFalse(gate.ready())
  self.assertEqual(calls,[100]);now[0]=130;self.assertFalse(gate.ready());self.assertEqual(calls,[100,130])
 def test_returned_capacity_allows_fast_work_between_probes(self):
  from trial_supervisor import CapacityAdmission
  now=[100];probe=iter([([],{'claude':'capacity'}),(['claude'],{})]);gate=CapacityAdmission(lambda:next(probe),clock=lambda:now[0]);self.assertFalse(gate.ready());now[0]=130;self.assertTrue(gate.ready())
  for n in [131,135,140]:now[0]=n;self.assertTrue(gate.ready())
 def test_metadata_errors_do_not_launch_unadmitted_work(self):
  from trial_supervisor import CapacityAdmission
  def fail():raise RuntimeError('metadata unavailable')
  gate=CapacityAdmission(fail,clock=lambda:100);self.assertFalse(gate.ready());self.assertIn('metadata unavailable',gate.snapshot['waits']['admission'])


class ResourceRollupTests(unittest.TestCase):
 def test_overall_reads_shared_ledger_and_state_once_without_losing_costs(self):
  import product_resources as reports,core_resources
  with tempfile.TemporaryDirectory() as d:
   base=Path(d);registry={'products':[{'id':p,'name':p} for p in ('a','b','c')]};(base/'products.json').write_text(json.dumps(registry));(base/'state.json').write_text('{"jobs":[]}');rows=[]
   for i,p in enumerate(('a','b','c')):
    rows += [{'kind':'reserved','id':p,'provider':'codex','product_id':p,'at_unix':100},{'kind':'finished','id':p,'provider':'codex','product_id':p,'tokens':100+i,'wall_seconds':1}]
   with patch.object(reports,'BASE',base),patch.object(reports,'events',return_value=rows) as ledger,patch.object(core_resources,'events',return_value=[]):r=reports.overall('lifetime')
   self.assertEqual(ledger.call_count,1);self.assertEqual(r['known_tokens'],303);self.assertEqual(len(r['products']),3);self.assertEqual(r['native_calls'],3)


class PhaseGapTests(unittest.TestCase):
 def test_historical_gap_is_unknown_instead_of_zero(self):
  rows=[{'phase':1,'finished_at':'2026-10-25T00:00:00+00:00'},{'phase':2}];r=analysis.phase_telemetry(rows);self.assertIsNone(r['phase_scheduling_gap_seconds']);self.assertFalse(r['phase_timing_complete'])
 def test_negative_clock_gap_is_not_reported_as_savings(self):
  rows=[{'phase':1,'finished_at':'2026-10-25T00:00:00+00:00'},{'phase':2,'phase_started_unix':1}];self.assertIsNone(analysis.phase_telemetry(rows)['phase_scheduling_gap_seconds'])
 def test_single_phase_has_no_interphase_wait(self):self.assertEqual(analysis.phase_telemetry([{'phase':1}])['phase_scheduling_gap_seconds'],0)
 def test_repository_phase_two_runs_immediately_but_deferral_yields(self):
  import spec_trial,trial_supervisor,repository_study
  with tempfile.TemporaryDirectory() as d:
   b=Path(d);root=b/'cohort';root.mkdir();(b/'trial-clock.json').write_text(json.dumps({'ends_unix':time.time()+1000}));controls=SchedulingTests().controls();identity={'models':{'codex':'fixture-model'},'scope':'fixture'};settings={'enabled':True,'repetitions':1,'efforts':['medium']};calls=[]
   def phase_work(project,**kw):
    phase=work.declaration(project)['phase'];calls.append(phase)
    if phase==2:self.assertEqual((project/'logic.py').read_text(),'delivered phase1');return {'complete':False,'validated':False,'delivered':False,'status':'AWAITING_EXECUTOR','native_receipts':[]}
    folder=work.state_root(project,b)/'runs/phase-1/workspace';folder.mkdir(parents=True);(folder/'app.py').write_text('app');(folder/'logic.py').write_text('delivered phase1');r={'queued_unix':100,'execution_started_unix':101,'complete':True,'delivered':True,'validated':True,'native_receipts':[]};(folder.parent/'result.json').write_text(json.dumps(r));return r
   with patch.object(trial_supervisor,'external_owner',return_value=None),patch.object(repository_study,'plan',return_value=(root,identity,settings,controls)),patch.object(repository_study,'status',return_value={'status':'DEFERRED'}) as status,patch.object(repository_study,'FAMILIES',('requirements_change',)),patch.object(spec_trial,'eligible',return_value=(['codex'],{})),patch.object(work,'run',side_effect=phase_work):r=repository_study.run_one(b)
   self.assertEqual(calls,[1,2]);self.assertEqual(r['status'],'DEFERRED');self.assertFalse(list(root.glob('*/*/study-result.json')))
