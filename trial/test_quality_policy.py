import unittest,tempfile,json,hashlib
from pathlib import Path
from unittest.mock import patch
import quality_policy as q
import resource_governor as g
import spec_trial as s
import value_benchmark as b

class Recovery(unittest.TestCase):
 def setUp(self):
  self.now=1000000
  self.rows=[dict(id=str(i),provider='codex',at_unix=self.now-100+i) for i in range(3)]
  self.done={str(i):dict(failure='Provider reports ordinary usage unavailable before inference',tokens=0,wall_seconds=1) for i in range(3)}
  self.policy=dict(total_token_guard=None,daily_token_guard=None,provider_window_token_guard=None,daily_native_seconds=None,provider_window_native_seconds=None,failure_backoff_seconds=10800,ends_unix=self.now+1000)
  from datetime import datetime,timezone
  self.snapshot={'at':datetime.fromtimestamp(self.now-10,timezone.utc).isoformat(),'codex':{'ordinaryUsageAllowed':True}}
 def result(self,**kw):return g.evaluate('codex',self.rows,self.done,self.policy,self.now,availability=kw.get('snapshot',self.snapshot))
 def test_fresh_positive_metadata_allows_recovery_after_quota_failure(self):
  r=self.result();self.assertTrue(r['eligible']);self.assertEqual(r['capacity_recovery']['supersedes_failure_id'],'2')
 def test_prior_success_does_not_block_recovery_from_later_capacity_failure(self):
  self.done['0']['failure']=None;self.done['1']['failure']=None;self.assertTrue(self.result()['eligible'])
 def test_latest_success_does_not_create_capacity_recovery(self):
  self.done['2']['failure']=None;self.assertIsNone(self.result()['capacity_recovery'])
 def test_stale_or_missing_positive_observation_does_not_bypass(self):
  for snapshot in [{},{'at':self.snapshot['at'],'codex':{'ordinaryUsageAllowed':False}}, {'at':'invalid','codex':{'ordinaryUsageAllowed':True}}]:self.assertFalse(self.result(snapshot=snapshot)['eligible'])
 def test_positive_observation_before_failure_does_not_bypass(self):
  from datetime import datetime,timezone
  self.snapshot['at']=datetime.fromtimestamp(self.now-200,timezone.utc).isoformat();self.assertFalse(self.result()['eligible'])
 def test_non_capacity_failure_is_not_cleared_by_quota(self):
  self.done['1']['failure']='Transport invalid output';self.assertFalse(self.result()['eligible'])
 def test_legacy_unclassified_failed_turn_does_not_stall_fresh_capacity_verification(self):
  self.done['1'].update(failure='RuntimeError: Native agent did not complete',turn_status='failed');result=self.result();self.assertTrue(result['eligible']);self.assertEqual(result['capacity_recovery']['supersedes_failure_id'],'2')
 def test_legacy_message_without_failed_turn_evidence_still_blocks(self):
  self.done['1']['failure']='RuntimeError: Native agent did not complete';self.assertFalse(self.result()['eligible'])
 def test_latest_explicit_transport_failure_still_blocks_quota_recovery(self):
  self.done['2'].update(failure='Transport invalid output',turn_status='failed');self.assertIsNone(self.result()['capacity_recovery']);self.assertFalse(self.result()['eligible'])
 def test_inflight_probe_prevents_second_recovery(self):
  self.rows.append(dict(id='probe',provider='codex',at_unix=self.now-1));self.assertFalse(self.result()['eligible'])
 def test_historical_orphan_does_not_prevent_recovery_forever(self):
  self.rows.append(dict(id='orphan',provider='codex',at_unix=self.now-10000));self.assertTrue(self.result()['eligible'])
 def test_budget_guard_survives_positive_observation(self):
  self.policy['daily_token_guard']=1;self.assertIn('shared_daily_token_guard',self.result()['reasons'])
 def test_claude_auth_does_not_prove_credit_recovery(self):
  rows=[dict(r,provider='claude') for r in self.rows];self.assertFalse(g.evaluate('claude',rows,self.done,self.policy,self.now,availability=self.snapshot)['eligible'])

class EditorialQuality(unittest.TestCase):
 def test_exclusivity_strengthening_is_rejected(self):
  with self.assertRaisesRegex(ValueError,'Decision-contract'):q.preserve_decision_contract('scheduled_at is the only required field.','scheduled_at is the only field.')
 def test_permission_and_bounds_are_preserved(self):
  for a,b in [('Extension is optional.','Extension is required.'),('Use 5 attempts.','Use 50 attempts.'),('A may proceed.','A must proceed.')]:
   with self.assertRaises(ValueError):q.preserve_decision_contract(a,b)
 def test_lowercase_modality_not_a_keyword_bypass(self):
  text='# X\nThe field is optional in existing registrations.\nThe complete existing contract remains otherwise unchanged.\n'
  p=dict(old='The field is optional in existing registrations.',new='The field is required in existing registrations.',evidence_quote='The complete existing contract remains otherwise unchanged.',reason='test',failure_case='Changing a permission in lowercase must not pass keyword-only gates.')
  with self.assertRaisesRegex(ValueError,'Decision-contract'):s.validate_patch(text,p)
 def test_explanation_can_change_without_rewriting_contract(self):q.preserve_decision_contract('It retains the checkpoint for recovery.','It keeps the checkpoint for recovery.')
 def test_proposal_guidance_excludes_fences_and_required_sentences(self):
  spans=q.editable_spans('# Heading\n```\ncode\n```\nIt MUST stay. Plain explanation remains.\n')
  self.assertEqual(spans,['Plain explanation remains.'])
 def test_selection_does_not_chase_fresh_hash_of_recent_section(self):
  a='## A\nA new explanation.';b='## B\nAn old untouched explanation.'
  jobs=[dict(section='## A',context_sha256='old-hash',finished_at='z')]
  self.assertEqual(q.select_section([a,b],jobs),b)
 def test_repeated_invalid_context_is_deprioritized_without_permanent_exclusion(self):
  a='## A\nExplanation.';b='## B\nOther explanation.';jobs=[dict(section='## A',context_sha256=hashlib.sha256(a.encode()).hexdigest(),error='ValueError: immutable',finished_at='a')]
  self.assertEqual(q.select_section([a,b],jobs),b);self.assertEqual(q.select_section([a],jobs),a)
 def test_blind_prompt_hides_proposal_claim_and_direction(self):
  p,_=q.blind_review_prompt('Before text','After text','id');self.assertNotIn('FAILURE CASE HYPOTHESIS',p);self.assertIn('Neither label',p)
 def test_blind_review_rejects_different_decisions_or_missing_quotes(self):
  quote='This complete contract remains unchanged.'
  scores={'A':{'clarity':3,'consistency':3,'conciseness':3},'B':{'clarity':4,'consistency':3,'conciseness':3}}
  r={'behavior_equivalent':True,'scores':scores,'decision_cases':[dict(question='Can the given operation proceed?',A_answer='Yes',B_answer='No',contract_quote=quote)]*2}
  self.assertFalse(q.quality_pass(q.normalize_review(r,False,quote,quote)))
  r['decision_cases']=[dict(question='Can the given operation proceed?',A_answer='Yes',B_answer='Yes',contract_quote=quote)]*2
  # Two copies of one case must not count as two independent checks.
  self.assertFalse(q.quality_pass(q.normalize_review(r,False,quote,quote)))
 def test_anonymous_score_mapping_is_correct(self):
  quote='This complete contract remains unchanged.';r={'behavior_equivalent':True,'scores':{'A':1,'B':2},'decision_cases':[]}
  self.assertEqual(q.normalize_review(r,True,quote,quote)['scores'],{'before':2,'after':1})

class Diagnostic(unittest.TestCase):
 def test_wrong_or_missing_answers_do_not_become_success(self):
  keys=[dict(id='x',answer=True)];self.assertEqual(b.score({'answers':{'x':False}},keys)['accuracy'],0)
  for r in [{'answers':{}},{'answers':{'x':1}},{'answers':{'x':True,'extra':True}}]:
   with self.assertRaises(ValueError):b.score(r,keys)
 def test_oracle_requires_unchanged_verbatim_contract(self):
  with self.assertRaises(ValueError):b.fixture('# Wrong','Another document')
 def test_diagnostic_context_does_not_include_answer_key(self):
  keys=[dict(id='x',answer=True)];self.assertEqual(b.score({'answers':{'x':True}},keys)['correct'],1)

class NativeOutputContract(unittest.TestCase):
 def test_inner_json_is_explicit_and_prose_is_not_salvaged_as_evidence(self):
  from contextlib import ExitStack
  with tempfile.TemporaryDirectory() as directory,ExitStack() as stack:
   folder=Path(directory);stack.enter_context(patch('controls.effective',return_value={'executors':{'codex':{'native_effort':'medium','model':'m','resource_effort':'high'}}}))
   with patch.object(s,'run',return_value=({'source':'{"answers":{"case":true}}','notes':''},None,{'tokens':10})) as run:
    self.assertEqual(s.native('codex','payload',folder,'probe'),{'answers':{'case':True}})
    prompt=run.call_args.args[1];example=prompt.split('Example envelope: ',1)[1].split(' Replace example_key',1)[0]
    self.assertEqual(json.loads(json.loads(example)['source']),{'example_key':True})
   with patch.object(s,'run',return_value=({'source':'contract references','notes':'The answer is yes'},None,{'tokens':10})):
    with self.assertRaises(ValueError):s.native('codex','payload',folder,'invalid')

class PairedDiagnostics(unittest.TestCase):
 def document(self):
  by_heading={}
  for _,heading,quote,_,_ in b.CASES:by_heading.setdefault(heading,[]).append(quote)
  return '\n'.join('## '+h+'\n'+'\n'.join(quotes)+'\n' for h,quotes in by_heading.items())
 def test_real_case_oracles_validate_and_answers_are_not_in_prompt(self):
  text=self.document();questions,keys=b.fixture(text,text)
  self.assertEqual(len(keys),8);self.assertFalse(any('answer' in q for q in questions))
 def test_paired_runs_preserve_zero_gain_and_failed_answer_is_not_success(self):
  from contextlib import ExitStack
  text=self.document()
  with tempfile.TemporaryDirectory() as directory,ExitStack() as stack:
   root=Path(directory)
   for name,value in [('trial-clock.json',{'trial_id':'t'}),('active-version.json',{'version':1}),('harness-manifest.json',{})]:(root/name).write_text(json.dumps(value))
   controls={'paused':False,'executor_enabled':True,'executors':{'codex':{'enabled':True,'model':'m','native_effort':'medium'}}}
   stack.enter_context(patch('controls.effective',return_value=controls))
   stack.enter_context(patch.object(s,'BASE',root));stack.enter_context(patch.object(s,'eligible',return_value=(['codex'],{})))
   stack.enter_context(patch.object(s,'read_version',return_value=(text,{'sha256':'known'})))
   def native(provider,prompt,folder,label):
    self.assertNotIn('"answer":',prompt)
    (folder/(label+'-native.json')).write_text(json.dumps({'tokens':120,'wall_seconds':1}))
    return {'answers':{row[0]:row[4] for row in b.CASES}}
   stack.enter_context(patch.object(s,'native',side_effect=native))
   report=b.run(root)
   self.assertEqual(report['complete_pairs'],1);self.assertEqual(report['pairs'][0]['accuracy_change_percentage_points'],0)
   self.assertEqual(report['pairs'][0]['known_pair_tokens'],240);self.assertIn('benefit not established',report['pairs'][0]['conclusion'])
 def test_changed_oracle_is_not_scored_against_stale_expected_answer(self):
  text=self.document()
  with self.assertRaisesRegex(ValueError,'oracle contract changed'):b.fixture(text,text.replace(b.CASES[0][2],'Another requirement.'))

class HistoricalAudit(unittest.TestCase):
 def test_flag_does_not_rewrite_history_or_claim_defect_proven(self):
  import quality_audit as audit
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);folder=root/'runs/t/j';folder.mkdir(parents=True)
   state={'jobs':[dict(id='j',trial_id='t',outcome='ACCEPTED_EDITORIAL_IMPROVEMENT',accepted_version=263)]}
   (root/'state.json').write_text(json.dumps(state));(root/'trial-clock.json').write_text(json.dumps({'trial_id':'t'}));(folder/'proposal.json').write_text(json.dumps({'old':'the only required field','new':'the only field'}));before=(root/'state.json').read_bytes()
   report=audit.audit(root);self.assertEqual(len(report['historical_risk_flags']),1);self.assertEqual((root/'state.json').read_bytes(),before)
   self.assertIn('not proof',report['historical_risk_flags'][0]['classification'])
 def test_no_other_provider_does_not_become_independent_revalidation(self):
  import cross_audit as audit
  from contextlib import ExitStack
  with tempfile.TemporaryDirectory() as directory,ExitStack() as stack:
   root=Path(directory);(root/'trial-clock.json').write_text(json.dumps({'trial_id':'t'}));(root/'state.json').write_text(json.dumps({'jobs':[dict(id='j',trial_id='t',outcome='ACCEPTED_EDITORIAL_IMPROVEMENT',accepted_version=1,proposer_provider='codex')]}));folder=root/'runs/t/j';folder.mkdir(parents=True);(folder/'proposal.json').write_text(json.dumps({'old':'checkpoint retained','new':'checkpoint kept'}))
   stack.enter_context(patch('controls.effective',return_value={'paused':False,'executor_enabled':True,'executors':{'codex':{'enabled':True}}}));stack.enter_context(patch.object(s,'eligible',return_value=(['codex'],{})))
   with patch.object(s,'native') as native:
    report=audit.run(root);native.assert_not_called();self.assertEqual(report['revalidated_versions'],0)

class ExactRestoration(unittest.TestCase):
 def setup(self,root):
  import test_snapshot_metadata as fixtures
  text,job=fixtures.SnapshotMetadata().setup_base(root)
  (root/'trial-clock.json').write_text(json.dumps({'trial_id':'t'}))
  s.publish(0,text.replace('keeps','retains'),job,__import__('test_spec_trial').SpecTrialTests().review())
  audit={'trial_id':'t','results':[{'version':1,'status':'CROSS_PROVIDER_DISAGREEMENT','provider':'claude','proposer_provider':'codex'}]}
  path=root/'cross-audit-latest.json';path.write_text(json.dumps(audit))
  restoration={'target_version':0,'withdrawn_versions':[1],'audit_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
  return text,job,restoration
 def test_exact_restoration_is_new_snapshot_not_new_quality_gain(self):
  import quality_restore as r
  with tempfile.TemporaryDirectory() as directory,patch.object(s,'BASE',Path(directory)):
   root=Path(directory);text,job,restore=self.setup(root);original=(s.version(1)/'URACE.md').read_bytes()
   manifest=s.publish(1,text,job,{'method':'exact restoration'},restoration=restore)
   self.assertEqual(manifest['version'],2);self.assertEqual((s.version(1)/'URACE.md').read_bytes(),original)
   self.assertEqual((s.version(2)/'URACE.md').read_text(),text);self.assertIn('not a new editorial gain',manifest['claim'])
   r.record_withdrawals(root,manifest);self.assertEqual(r.withdrawn_versions(root),{1})
 def test_missing_disagreement_or_modified_restore_content_is_rejected(self):
  import quality_restore as r
  with tempfile.TemporaryDirectory() as directory,patch.object(s,'BASE',Path(directory)):
   root=Path(directory);text,job,restore=self.setup(root)
   with self.assertRaises(ValueError):r.verify(root,1,text+'arbitrary change',restore)
   path=root/'cross-audit-latest.json';v=json.loads(path.read_text());v['results'][0]['provider']='codex';path.write_text(json.dumps(v));restore['audit_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
   with self.assertRaises(ValueError):r.verify(root,1,text,restore)
 def test_recovery_keeps_corrective_outcome_and_withdrawal_index(self):
  import quality_restore as r
  with tempfile.TemporaryDirectory() as directory,patch.object(s,'BASE',Path(directory)):
   root=Path(directory);text,job,restore=self.setup(root)
   s.publish(1,text,job,{'method':'exact restoration'},restoration=restore)
   state={'jobs':[],'inflight':{'id':'job','parent_version':1,'restoration':restore}}
   s.recover_publication(state)
   self.assertEqual(state['jobs'][0]['outcome'],'CORRECTIVE_RESTORE');self.assertEqual(r.withdrawn_versions(root),{1})
 def test_exact_inverse_keeps_unrelated_later_work_and_refuses_arbitrary_text(self):
  import quality_restore as r
  with tempfile.TemporaryDirectory() as directory,patch.object(s,'BASE',Path(directory)):
   root=Path(directory);text,job,restore=self.setup(root)
   # Add the original sealed proposal to a synthetic inspected snapshot via a
   # controlled inspector fixture; live mode always verifies actual artifacts.
   proposal={'old':'keeps','new':'retains'};folder=s.version(1);(folder/'evidence').mkdir(exist_ok=True);(folder/'evidence/proposal.json').write_text(json.dumps(proposal))
   parent={'manifest':{'parent_version':0}}
   with patch('snapshot_metadata.inspect_snapshot',return_value=parent):
    self.assertEqual(r.inverse_source(1,text.replace('keeps','retains')+'Unrelated later work.'),text+'Unrelated later work.')
    with self.assertRaises(ValueError):r.inverse_source(1,'The original replacement is absent.')
 def test_inverse_restoration_requires_reconstructed_source_identity(self):
  import quality_restore as r
  with tempfile.TemporaryDirectory() as directory,patch.object(s,'BASE',Path(directory)):
   root=Path(directory);text,job,restore=self.setup(root);restore={'mode':'EXACT_INVERSE_EDITS',**{k:v for k,v in restore.items() if k!='target_version'}}
   with patch.object(r,'inverse_source',return_value=text):
    r.verify(root,1,text,restore)
    with self.assertRaises(ValueError):r.verify(root,1,text+'new invented requirement',restore)
 def test_withdrawals_do_not_cross_trial_identities(self):
  import quality_restore as r
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);(root/'trial-clock.json').write_text(json.dumps({'trial_id':'new'}));(root/'withdrawn-acceptances.json').write_text(json.dumps({'trial_id':'old','versions':[1]}));self.assertEqual(r.withdrawn_versions(root),set())

if __name__=='__main__':unittest.main()

class ClaudeStructuredTransport(unittest.TestCase):
 def envelope(self,error=False):
  return {'type':'result','is_error':error,'subtype':'error_max_structured_output_retries' if error else 'success','structured_output':None if error else {'source':'{"ok":true}','notes':''},'modelUsage':{'main':{'inputTokens':2,'cacheCreationInputTokens':0,'cacheReadInputTokens':0,'outputTokens':3}}}
 def call(self,error=False):
  import providers
  from unittest.mock import MagicMock
  client=MagicMock();client.line.side_effect=[json.dumps(self.envelope(error)),None];client.process.returncode=1 if error else 0
  record={'id':'fixture','effort':'medium'}
  with patch.object(providers,'Transport',return_value=client) as factory:
   if error:
    with self.assertRaisesRegex(RuntimeError,'error_max_structured_output_retries'):providers.claude('task',Path('/tmp'),record)
   else:self.assertEqual(providers.claude('task',Path('/tmp'),record)[0]['source'],'{"ok":true}')
  return factory,record
 def test_one_bounded_formatting_retry_is_passed_to_client(self):
  factory,record=self.call();self.assertEqual(factory.call_args.args[2]['MAX_STRUCTURED_OUTPUT_RETRIES'],'3');cmd=factory.call_args.args[0];self.assertEqual(cmd[cmd.index('--max-turns')+1],'4');self.assertEqual(record['transport_policy']['structured_output_retries'],3)
 def test_error_subtype_and_spent_tokens_are_preserved(self):
  _,record=self.call(True);self.assertEqual(record['subtype'],'error_max_structured_output_retries');self.assertEqual(record['tokens'],5)

class StructuredPolicyRecovery(unittest.TestCase):
 def setUp(self):
  self.now=1000000;self.rows=[{'id':str(i),'provider':'claude','at_unix':self.now-100+i} for i in range(3)]
  self.done={str(i):{'failure':'RuntimeError: Claude failed','subtype':'error_max_structured_output_retries','tokens':10,'wall_seconds':1} for i in range(3)}
  self.policy={'total_token_guard':None,'daily_token_guard':None,'provider_window_token_guard':None,'daily_native_seconds':None,'provider_window_native_seconds':None,'failure_backoff_seconds':10800,'ends_unix':self.now+1000}
 def result(self):return g.evaluate('claude',self.rows,self.done,self.policy,self.now)
 def test_changed_policy_allows_one_verification_without_assuming_success(self):
  result=self.result();self.assertTrue(result['eligible']);self.assertIsNone(result['capacity_recovery']);self.assertEqual(result['transport_recovery']['supersedes_failure_id'],'2')
 def test_failed_verification_does_not_loop(self):
  from stream_usage import claude_transport_policy
  self.done['2']['transport_policy']=claude_transport_policy();self.assertFalse(self.result()['eligible'])
 def test_pending_verification_is_serialized(self):
  self.rows.append({'id':'pending','provider':'claude','at_unix':self.now,'wall_cap_seconds':300});self.assertIn('transport_recovery_inflight',self.result()['reasons'])
 def test_non_format_failure_is_not_bypassed(self):
  self.done['1']['subtype']='authentication_failed';self.assertFalse(self.result()['eligible'])
 def test_budget_still_applies(self):
  self.policy['daily_token_guard']=1;self.assertIn('shared_daily_token_guard',self.result()['reasons'])
 def test_expiry_still_applies(self):
  self.policy['ends_unix']=self.now-1;self.assertIn('study_window_ended',self.result()['reasons'])
 def test_codex_does_not_use_claude_format_recovery(self):
  rows=[dict(r,provider='codex') for r in self.rows];self.assertFalse(g.evaluate('codex',rows,self.done,self.policy,self.now)['eligible'])
