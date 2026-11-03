"""Project evidence boundaries, command integration and anti-gaming regression tests."""
import argparse,contextlib,copy,io,json,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
from urace import value_discovery as v,cli,command_surface,api_interface,auto_goals

class Capture(BaseException):pass

def grammar():
 found=[]
 def grab(parser,*args,**kwargs):found.append(parser);raise Capture()
 with patch.object(argparse.ArgumentParser,'parse_known_args',grab):
  try:cli.main(['commands'])
  except Capture:pass
 return found[0]

class ValueFixture(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  self.cfg={'state_path':str(self.root/'state.json'),'project':{'id':'p','intent':'Reduce verified workflow effort','requirements':[{'id':'r','title':'Complete useful work','success_measure':'Independent completion evidence','priority':50}]},'authority':{'delegated':['objectives','measurement','priority']}}
 def data(self):return v.sync(self.cfg)
 def observation(self,**kwargs):
  d={'metric':'completion_seconds','samples':[{'id':'sample','before':10,'after':5,'quality_before':1,'quality_after':1}]};d.update(kwargs);return d

class ValueDiscoveryTests(ValueFixture):
 def test_defaults_and_missing_intent_do_not_invent_a_product(self):
  self.assertTrue(v.settings({})['enabled']);self.assertFalse(v.settings({})['external_research']);self.assertFalse(v.settings({})['ranking']);self.assertEqual(v.proposed({}),[]);self.assertEqual(v.refresh({},{} )['status'],'NO_DECLARED_PROJECT')
 def test_unchanged_sync_does_not_rewrite_or_multiply(self):
  a=self.data();path=v.store_path(self.cfg);stamp=path.stat().st_mtime_ns;b=self.data();self.assertEqual(a['revision'],b['revision']);self.assertEqual(path.stat().st_mtime_ns,stamp);self.assertEqual(len(b['hypotheses']),1)
 def test_disable_keeps_history(self):
  a=self.data();self.cfg['value_discovery']={'enabled':False};b=v.sync(self.cfg);self.assertEqual(a['hypotheses'],b['hypotheses'])
 def test_projects_share_no_evidence_even_with_same_state_parent(self):
  a=self.data();self.cfg['project']['id']='other';b=v.sync(self.cfg);self.assertNotEqual(a['project_id'],b['project_id']);self.assertNotEqual(a['hypotheses'][0]['id'],b['hypotheses'][0]['id'])
 def test_intent_revision_supersedes_old_hypothesis(self):
  a=self.data();old=a['hypotheses'][0]['id'];self.cfg['project']['requirements'][0]['success_measure']='Different measurement';b=v.sync(self.cfg);self.assertEqual(v.hypothesis(b,old)['status'],'SUPERSEDED');self.assertEqual(len(b['hypotheses']),2)
 def test_superseded_hypothesis_cannot_be_revalidated(self):
  d=self.data();h=d['hypotheses'][0];h['status']='SUPERSEDED';h['assessment']={'at_unix':1};v.save(self.cfg,d)
  with self.assertRaises(ValueError):v.validate(d,h['id'],self.cfg)
  self.assertEqual(v.status(self.cfg)['hypotheses'][0]['status'],'SUPERSEDED')
 def test_linked_outcome_cannot_erase_counterevidence(self):
  d=self.data();h=d['hypotheses'][0];v.attach_evidence(d,h['id'],{'claim':'Contradictory result','source_ref':'audit','stance':'contradicts'})
  state={'objectives':[{'id':'g','project_id':'p','project_requirement':'r','project_source_sha256':h['intent_revision']}],'operations':[{'id':'o','objective_reference':'g','outcome':{'status':'OUTCOME_VERIFIED'}}]}
  self.assertTrue(v.link_outcomes(d,state));self.assertEqual(h['status'],'CONTRADICTED');self.assertEqual(v.advisory_ranking(d,self.cfg),[])
 def test_observed_gain_is_not_independent_user_value(self):
  d=self.data();h=d['hypotheses'][0];v.observe(d,h['id'],self.observation());r=v.validate(d,h['id'],self.cfg);self.assertTrue(r['indicators']['completion_seconds']['benefit_observed_in_provided_data']);self.assertFalse(h['real_user_benefit_verified']);self.assertFalse(r['market_fit_established']);self.assertNotEqual(h['status'],'VALIDATED_WITHIN_SCOPE')
 def test_unknown_quality_does_not_allow_benefit_claim(self):
  d=self.data();h=d['hypotheses'][0];v.observe(d,h['id'],self.observation(samples=[{'id':'a','before':10,'after':1}]));r=v.validate(d,h['id'],self.cfg);self.assertFalse(r['indicators']['completion_seconds']['benefit_observed_in_provided_data'])
 def test_quality_regression_is_not_hidden_by_speed(self):
  d=self.data();h=d['hypotheses'][0];v.observe(d,h['id'],self.observation(samples=[{'id':'a','before':10,'after':1,'quality_before':1,'quality_after':.5}]));v.validate(d,h['id'],self.cfg);self.assertEqual(h['status'],'CONTRADICTED')
 def test_replays_and_privilege_flags_are_rejected(self):
  d=self.data();key=d['hypotheses'][0]['id'];v.observe(d,key,self.observation(observed_unix=100),now=200)
  with self.assertRaises(ValueError):v.observe(d,key,self.observation(observed_unix=101),now=200)
  with self.assertRaises(ValueError):v.observe(d,key,self.observation(trusted=True))
 def test_invalid_numbers_and_future_dates_fail(self):
  d=self.data();key=d['hypotheses'][0]['id']
  for n in [True,float('nan'),float('inf'),-1]:
   with self.assertRaises(ValueError):v.observe(d,key,self.observation(samples=[{'id':'a','before':n,'after':1}]))
  with self.assertRaises(ValueError):v.observe(d,key,self.observation(observed_unix=time.time()+100))
 def test_provider_tokens_never_pool(self):
  d=self.data();key=d['hypotheses'][0]['id']
  with self.assertRaises(ValueError):v.observe(d,key,self.observation(metric='tokens'))
  for p,after in [('codex',5),('claude',20)]:v.observe(d,key,self.observation(metric='tokens',provider=p,samples=[{'id':'same-paired-task','before':10,'after':after,'quality_before':1,'quality_after':1}]))
  r=v.validate(d,key,self.cfg);self.assertEqual(r['indicators']['tokens:codex']['change_pct'],-50);self.assertEqual(r['indicators']['tokens:claude']['change_pct'],100)
 def test_custom_indicator_is_immutable_and_range_checked(self):
  d=self.data();key=d['hypotheses'][0]['id'];definition={'name':'user_success','unit':'proportion','kind':'user_outcome','direction':'higher','minimum':0,'maximum':1};v.define_indicator(d,key,definition)
  with self.assertRaises(ValueError):v.define_indicator(d,key,definition)
  with self.assertRaises(ValueError):v.observe(d,key,self.observation(metric='user_success',samples=[{'id':'a','before':0,'after':2}]))
 def test_stale_observation_is_not_reaffirmed(self):
  d=self.data();key=d['hypotheses'][0]['id'];v.observe(d,key,self.observation(observed_unix=100),now=100);r=v.validate(d,key,self.cfg,now=1000000);self.assertEqual(r['indicators']['completion_seconds']['status'],'UNKNOWN')
 def test_contradictory_evidence_survives_validation(self):
  d=self.data();key=d['hypotheses'][0]['id'];v.attach_evidence(d,key,{'claim':'Time savings do not fix user rework','source_ref':'provided-interview-1','stance':'contradicts'});v.observe(d,key,self.observation());v.validate(d,key,self.cfg);self.assertEqual(v.hypothesis(d,key)['status'],'CONTRADICTED');self.assertTrue(v.hypothesis(d,key)['counterevidence'])
 def test_evidence_cannot_redirect_hypothesis_identity(self):
  d=self.data();key=d['hypotheses'][0]['id']
  with self.assertRaises(ValueError):v.attach_evidence(d,key,{'claim':'x','source_ref':'s','stance':'supports','hypothesis_id':'other'})
 def test_experiment_contract_must_precede_observations(self):
  d=self.data();key=d['hypotheses'][0]['id'];p={'id':'experiment','hypothesis_id':key,'primary_indicator':'completion_seconds','baseline_version':'v0','candidate_version':'v1','quality_floor':1,'resource_limit':100};r=v.experiment(d,p);self.assertTrue(r['contract_sha256']);
  with self.assertRaises(ValueError):v.experiment(d,p)
  v.observe(d,key,self.observation());p['id']='posthoc'
  with self.assertRaises(ValueError):v.experiment(d,p)
 def test_independent_outcomes_require_matching_project_and_intent(self):
  d=self.data();h=d['hypotheses'][0];goal={'id':'g','project_id':'p','project_requirement':'r','project_source_sha256':'earlier-intent'};op={'id':'o','objective_reference':'g','outcome':{'status':'REAL_USER_VALUE_VERIFIED','real_user_value_verified':True,'evaluated_at':'2026-10-25T00:00:00+00:00','net_value_delta':.2}};state={'objectives':[goal],'operations':[op]};self.assertFalse(v.link_outcomes(d,state));goal['project_source_sha256']=h['intent_revision'];self.assertTrue(v.link_outcomes(d,state));self.assertTrue(h['real_user_benefit_verified'])
 def test_ranking_needs_policy_and_priority_delegation(self):
  d=self.data();h=d['hypotheses'][0];h['independent_outcome']={'status':'OUTCOME_VERIFIED','evaluated_at':__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),'net_value_delta':.2};self.assertFalse(v.advisory_ranking(d,self.cfg)[0]['eligible_for_policy']);self.cfg['value_discovery']={'ranking':True};self.assertTrue(v.advisory_ranking(d,self.cfg)[0]['eligible_for_policy']);self.cfg['authority']['delegated']=[];self.assertFalse(v.advisory_ranking(d,self.cfg)[0]['eligible_for_policy'])
 def test_ranking_cannot_override_explicit_priority(self):
  self.cfg['project']['requirements'] += [{'id':'z','title':'Explicit urgent work','success_measure':'Done','priority':100}];self.cfg['value_discovery']={'ranking':True}
  with patch.object(v,'ranking_scores',return_value={'r':1}):goal=auto_goals.select(self.cfg,{})
  self.assertEqual(goal['project_requirement'],'z')
 def test_disabled_research_makes_no_external_call(self):
  from urace import external_metrics
  d=self.data();key=d['hypotheses'][0]['id']
  with patch.object(external_metrics,'collect',side_effect=AssertionError('No permission')):self.assertEqual(v.research(self.root,self.cfg,d,key)['status'],'DISABLED')
 def test_enabled_research_is_bounded_cached_and_still_not_verified(self):
  (self.root/'metrics.json').write_text('{"complaints":3}');self.cfg['external_metrics']={'mode':'PROVIDED_ONLY','sources':[{'id':'provided','kind':'json_file','location':'metrics.json','values':{'pain':'complaints'}}]};self.cfg['value_discovery']={'external_research':True};d=self.data();key=d['hypotheses'][0]['id'];r=v.research(self.root,self.cfg,d,key);self.assertEqual(r['source_fetches'],1);self.assertEqual(r['inference_calls'],0);self.assertFalse(r['market_fit_established']);self.assertEqual(v.research(self.root,self.cfg,d,key)['status'],'CACHED')
 def test_research_rejects_hidden_and_symlink_sources(self):
  self.cfg['value_discovery']={'external_research':True};(self.root/'.private.json').write_text('{"v":1}');(self.root/'alias.json').symlink_to(self.root/'.private.json');self.cfg['external_metrics']={'mode':'PROVIDED_ONLY','sources':[{'id':'p','kind':'json_file','location':'alias.json','values':{'v':'v'}}]};d=self.data();r=v.research(self.root,self.cfg,d,d['hypotheses'][0]['id']);self.assertEqual(r['source_fetches'],0);self.assertTrue(r['errors'])
 def test_supplied_data_does_not_multiply_assessment_credit(self):
  d=self.data();key=d['hypotheses'][0]['id'];v.observe(d,key,self.observation());v.validate(d,key,self.cfg,now=10000000000);v.validate(d,key,self.cfg,now=10000000000);self.assertEqual(len(d['assessments']),1)
 def test_empty_quality_report_is_not_a_measurement(self):
  p=self.root/'repository-study-latest.json';p.write_text(json.dumps({'output_quality':{'quality_measured_workflows':0}}));self.assertEqual(v.execution_quality_views(self.root)['repository']['status'],'NOT_MEASURED')
  p.write_text(json.dumps({'output_quality':{'quality_measured_workflows':1}}));self.assertEqual(v.execution_quality_views(self.root)['repository']['status'],'MEASURED')
 def verified(self,h,stamp=None):
  from datetime import datetime,timezone
  h['independent_outcome']={'status':'REAL_USER_VALUE_VERIFIED','evaluated_at':stamp or datetime.now(timezone.utc).isoformat(),'real_user_value_verified':True,'net_value_delta':.2};h['status']='VALIDATED_WITHIN_SCOPE';h['real_user_benefit_verified']=True
 def test_new_counterevidence_blocks_ranking_before_validate(self):
  d=self.data();h=d['hypotheses'][0];self.verified(h);self.cfg['value_discovery']={'ranking':True};self.assertTrue(v.advisory_ranking(d,self.cfg));v.attach_evidence(d,h['id'],{'claim':'Regression','source_ref':'audit','stance':'contradicts'});self.assertEqual(v.advisory_ranking(d,self.cfg),[]);self.assertEqual(h['status'],'CONTRADICTED');self.assertFalse(h['real_user_benefit_verified'])
 def test_stale_future_or_naive_outcomes_cannot_verify_or_rank(self):
  from datetime import datetime,timezone,timedelta
  for stamp in [(datetime.now(timezone.utc)+timedelta(days=1)).isoformat(),(datetime.now(timezone.utc)-timedelta(days=2)).isoformat(),datetime.now().isoformat(),'invalid']:
   d=self.data();h=d['hypotheses'][0];self.verified(h,stamp);v.validate(d,h['id'],self.cfg);self.assertNotEqual(h['status'],'VALIDATED_WITHIN_SCOPE');self.assertFalse(h['real_user_benefit_verified']);v.save(self.cfg,d);view=v.status(self.cfg);self.assertEqual(view['coverage']['independent_outcome_verified'],0);self.assertFalse(view['hypotheses'][0]['real_user_benefit_verified']);self.assertEqual(view['ranking'],[])
 def test_fresh_independent_outcome_survives_old_supplied_assessment(self):
  d=self.data();h=d['hypotheses'][0];self.verified(h);h['assessment']={'at_unix':1};v.save(self.cfg,d);view=v.status(self.cfg);self.assertEqual(view['hypotheses'][0]['status'],'VALIDATED_WITHIN_SCOPE');self.assertEqual(view['coverage']['independent_outcome_verified'],1)
 def test_project_identity_matches_auto_goals_without_explicit_id(self):
  for extra in [{},{'name':'named'},{'id':None,'name':'ignored-by-auto-goals'}]:
   cfg=copy.deepcopy(self.cfg);cfg['project'].pop('id');cfg['project'].update(extra);g=auto_goals.select(cfg,{});d=v.sync(cfg);h=d['hypotheses'][0];self.assertEqual(d['project_id'],g['project_id']);self.assertEqual(h['intent_revision'],g['project_source_sha256'])
 def test_extreme_finite_observations_do_not_emit_infinity(self):
  d=self.data();h=d['hypotheses'][0];v.observe(d,h['id'],self.observation(samples=[{'id':'big','before':1e-308,'after':1e308,'quality_before':1,'quality_after':1}]));a=v.validate(d,h['id'],self.cfg);self.assertIsNone(a['indicators']['completion_seconds']['change_pct']);json.dumps(a,allow_nan=False)
  with self.assertRaises(ValueError):v.number(10**1000)
 def test_restored_requirement_reactivates_goal_and_hypothesis(self):
  state={};first=auto_goals.select(self.cfg,state);d=self.data();key=d['hypotheses'][0]['id'];original=copy.deepcopy(self.cfg['project']['requirements'][0]);self.cfg['project']['requirements'][0]['success_measure']='Changed';second=auto_goals.select(self.cfg,state);v.sync(self.cfg);self.assertNotEqual(first['id'],second['id']);self.assertEqual(first['status'],'superseded');self.cfg['project']['requirements'][0]=original;restored=auto_goals.select(self.cfg,state);self.assertEqual(restored['id'],first['id']);self.assertEqual(restored['status'],'planned');self.assertEqual(len(restored['reactivations']),1);d=v.sync(self.cfg);self.assertEqual(v.hypothesis(d,key)['status'],'PROPOSED');self.assertEqual(len(d['hypotheses']),2)
 def test_shadow_refresh_changes_no_goals_or_requirements(self):
  state={'project':copy.deepcopy(self.cfg['project']),'objectives':[{'id':'manual','priority':99}]};before=copy.deepcopy(state);v.refresh(self.cfg,state);self.assertEqual(state,before)

class ValueCommandTests(ValueFixture):
 @classmethod
 def setUpClass(cls):cls.parser=grammar()
 def call(self,argv):
  with patch.object(cli,'load_config',return_value=self.cfg),contextlib.redirect_stdout(io.StringIO()) as out,contextlib.redirect_stderr(io.StringIO()):
   try:code=cli.main(argv)
   except SystemExit as error:return error.code,out.getvalue()
  return code,out.getvalue()
 def test_commands_share_typed_api_and_readonly_classification(self):
  for path,params in [('product value list',{}),('status value',{}),('configuration value-discovery',{})]:
   argv=api_interface.build_argv(self.parser,path,params);self.assertTrue(command_surface.read_only(argv));self.assertEqual(self.call(argv)[0],0)
  self.assertFalse(command_surface.read_only(['product','value','research','--id','h']));self.assertFalse(command_surface.read_only(['configuration','value-discovery','--external-research','true']))
 def test_cli_propose_observe_validate_end_to_end(self):
  code,text=self.call(['product','value','propose','--json']);self.assertEqual(code,0);key=json.loads(text)['hypotheses'][0]['id'];args=api_interface.build_argv(self.parser,'product value observe',{'id':key,'data':json.dumps(self.observation())});self.assertEqual(self.call(args)[0],0);code,text=self.call(['product','value','validate','--id',key,'--json']);self.assertEqual(code,0);self.assertEqual(json.loads(text)['indicators']['completion_seconds']['samples'],1)
 def test_cli_rejects_invalid_payload_and_irrelevant_flags(self):
  self.assertNotEqual(self.call(['product','value','observe','--id','missing','--data','[]'])[0],0);self.assertNotEqual(self.call(['product','value','list','--project','somewhere'])[0],0)
 def test_persistent_configuration_uses_shared_settings_validation(self):
  path=self.root/'config.json'
  with patch.object(cli,'CONFIG_PATH',path),patch.object(cli,'save_config',side_effect=lambda cfg:self.cfg.update(cfg)):
   code,text=self.call(['configuration','value-discovery','--enabled','false','--external-research','false','--json'])
  self.assertEqual(code,0);self.assertFalse(self.cfg['value_discovery']['enabled']);self.assertNotEqual(self.call(['configuration','value-discovery','--research-seconds','0'])[0],0)

class LegacyValueEvidenceTests(ValueFixture):
 def legacy(self):return self.root/('value-discovery-'+v.digest(v.identity(self.cfg))[:24]+'.json')
 def test_legacy_evidence_is_read_without_rewrite_and_next_save_retains_all_records(self):
  data=v.empty(self.cfg);data['observations']=[{'id':'original-observation','counterevidence':'Retain this original measurement'}];data['revision']=7
  legacy=self.legacy();legacy.write_text(json.dumps(data));raw=legacy.read_bytes();loaded=v.load(self.cfg);self.assertEqual(loaded,data);self.assertFalse(v.store_path(self.cfg).exists());self.assertEqual(legacy.read_bytes(),raw)
  v.save(self.cfg,loaded);self.assertEqual(v.load(self.cfg)['observations'],data['observations']);self.assertEqual(v.load(self.cfg)['revision'],8);self.assertEqual(legacy.read_bytes(),raw);self.assertEqual(len(v.store_path(self.cfg).stem.removeprefix('value-discovery-')),64)
 def test_legacy_name_cannot_bypass_project_identity_validation(self):
  data=v.empty(self.cfg);data['project_id']='another-project';self.legacy().write_text(json.dumps(data))
  with self.assertRaises(ValueError):v.load(self.cfg)
 def test_legacy_symlink_is_not_followed(self):
  target=self.root/'outside.json';target.write_text(json.dumps(v.empty(self.cfg)));self.legacy().symlink_to(target)
  with self.assertRaises(ValueError):v.load(self.cfg)
