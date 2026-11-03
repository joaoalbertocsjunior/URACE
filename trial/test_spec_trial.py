import json,tempfile,unittest,time
from pathlib import Path
from unittest.mock import patch
import spec_trial as s

class SpecTrialTests(unittest.TestCase):
    text='# Example\n\nThe implementation keeps an accepted checkpoint for recovery.\nIt MUST preserve evidence.\n'
    def proposal(self):
        return dict(old='The implementation keeps an accepted checkpoint for recovery.',new='The implementation retains an accepted checkpoint for recovery.',evidence_quote='It MUST preserve evidence.\n'+'x'*30,reason='Clarity',failure_case='An explicit fixture for testing static patch validation rather than model judgment.')
    def review(self):
        return dict(preserves_existing_semantics=True,no_new_runtime_behavior=True,no_weakened_authority_or_evidence=True,material_quality_improved=True,failure_case_supported=True,scores=dict(before=dict(clarity=3,consistency=4,conciseness=4),after=dict(clarity=4,consistency=4,conciseness=4)),explanation='Specific clearer wording')
    def test_existing_contract_quote_required(self):
        with self.assertRaises(ValueError):s.validate_patch(self.text,self.proposal())
    def test_version_series_keeps_old_baseline_separate(self):
        with tempfile.TemporaryDirectory() as d,patch.object(s,'BASE',Path(d)):
            b=Path(d);s.atomic(b/'version-series.json',{'root':'versions/baseline-5688fda'});self.assertEqual(s.version(0),b/'versions/baseline-5688fda/v000000')
            s.atomic(b/'version-series.json',{'root':'../elsewhere'})
            with self.assertRaises(ValueError):s.version(0)
    def test_accounting_reset_keeps_history_and_rejected_costs(self):
        rows=[dict(kind='reserved',id='old',provider='codex',at_unix=1,logical_job_id='old-job-proposal'),dict(kind='finished',id='old',tokens=100,wall_seconds=2),dict(kind='reserved',id='late-review',provider='codex',at_unix=11,logical_job_id='old-job-review'),dict(kind='finished',id='late-review',tokens=50,wall_seconds=1),dict(kind='reserved',id='new',provider='claude',at_unix=12,logical_job_id='new-job-proposal'),dict(kind='finished',id='new',tokens=70,wall_seconds=3)]
        epoch=dict(started_unix=10,excluded_jobs=['old-job']);current=s.resource_metrics(rows,epoch)
        self.assertEqual(current['known_tokens'],70);self.assertEqual(current['native_calls'],1);self.assertEqual(current['providers']['claude']['known_tokens'],70);self.assertEqual(s.resource_metrics(rows)['known_tokens'],220)
        self.assertEqual(s.resource_metrics(rows,dict(started_unix=20))['known_tokens'],0)
    def test_unfinished_usage_is_unknown_not_zero_observed(self):
        r=s.resource_metrics([dict(kind='reserved',id='inflight',provider='codex',at_unix=1)])
        self.assertEqual(r['known_tokens'],0);self.assertEqual(r['missing_usage'],1);self.assertEqual(r['inflight_calls'],1)
    def test_bounded_supported_edit(self):
        p=self.proposal();p['evidence_quote']='The implementation keeps an accepted checkpoint for recovery.'
        self.assertIn('retains',s.validate_patch(self.text,p))
    def test_cosmetic_changes_rejected_before_paid_review(self):
        text='# Example\nThe system keeps users, customers, markets and environments as evidence producers.\n'
        p=dict(old='users, customers, markets and environments',new='users, customers, markets, and environments',evidence_quote=text.splitlines()[1],reason='Comma only',failure_case='A fixture which must be rejected because punctuation does not fix a material defect.')
        with self.assertRaisesRegex(ValueError,'Cosmetic'):s.validate_patch(text,p)
    def test_normative_changes_rejected(self):
        p=self.proposal();p.update(old='It MUST preserve evidence.',new='It MAY preserve evidence.',evidence_quote=self.text.splitlines()[2])
        with self.assertRaisesRegex(ValueError,'Normative'):s.validate_patch(self.text,p)
    def test_explanation_on_requirement_line_can_change_without_changing_requirement(self):
        text='# Example\nThe system MUST preserve evidence. The implementation keeps an accepted checkpoint for recovery.\n'
        p=self.proposal();p['evidence_quote']='The system MUST preserve evidence. The implementation keeps an accepted checkpoint for recovery.'
        result=s.validate_patch(text,p);self.assertIn('retains',result);self.assertEqual(s.normative(text),s.normative(result))
        p.update(old='The system MUST preserve evidence.',new='The system MAY discard evidence.')
        with self.assertRaisesRegex(ValueError,'Normative'):s.validate_patch(text,p)
    def test_requirement_with_dotted_filename_is_protected(self):
        before='The system MUST preserve URACE.md as evidence. Explanatory prose follows.'
        self.assertEqual(s.normative(before),['The system MUST preserve URACE.md as evidence.'])
    def test_wrapped_requirement_tail_remains_protected(self):
        text='The system MUST retain its accepted state\nand preserve the recovery journal. Explanation follows.'
        self.assertEqual(s.normative(text),['The system MUST retain its accepted state and preserve the recovery journal.'])
        self.assertNotEqual(s.normative(text),s.normative(text.replace('preserve the recovery journal','discard the recovery journal')))
    def test_heading_changes_rejected(self):
        p=self.proposal();p.update(old='# Example',new='# Changed',evidence_quote=self.text.splitlines()[2])
        with self.assertRaisesRegex(ValueError,'structure'):s.validate_patch(self.text,p)
    def test_code_examples_remain_immutable(self):
        text=self.text+'\n```python\nVALUE=1\n```\n';p=self.proposal();p.update(old='VALUE=1',new='VALUE=2',evidence_quote=self.text.splitlines()[2])
        with self.assertRaisesRegex(ValueError,'Code examples'):s.validate_patch(text,p)
    def test_review_rejects_regression_and_uncertainty(self):
        r=self.review();self.assertTrue(s.review_pass(r));r['scores']['after']['consistency']=3;self.assertFalse(s.review_pass(r));r=self.review();r['no_new_runtime_behavior']=None;self.assertFalse(s.review_pass(r))
    def test_material_consistency_gain_does_not_require_clarity_gain(self):
        r=self.review();r['scores']['after']['clarity']=r['scores']['before']['clarity'];r['scores']['after']['consistency']=5;self.assertTrue(s.review_pass(r))
        r['material_quality_improved']=False;self.assertFalse(s.review_pass(r))
        r['material_quality_improved']=True;r['failure_case_supported']=False;self.assertFalse(s.review_pass(r))
    def test_snapshot_chain_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d,patch.object(s,'BASE',Path(d)):
            b=Path(d);v=s.version(0);v.mkdir(parents=True);(v/'URACE.md').write_text(self.text);s.atomic(v/'manifest.json',dict(version=0,sha256=s.digest(self.text),baseline_commit='abc'));(b/'harness-manifest.json').write_text('{}');job=b/'runs/job';job.mkdir(parents=True)
            m=s.publish(0,self.text.replace('keeps','retains'),job,self.review());self.assertEqual(m['parent_sha256'],s.digest(self.text));self.assertTrue((s.version(1)/'parent.diff').exists());self.assertEqual(len(s.compare()['versions']),2)
            with self.assertRaises(RuntimeError):s.publish(0,self.text.replace('keeps','retains'),job,self.review())
            (s.version(1)/'URACE.md').write_text('tampered')
            with self.assertRaisesRegex(RuntimeError,'integrity'):s.read_version(1)
    def test_publish_requires_review(self):
        with self.assertRaises(ValueError):
            with tempfile.TemporaryDirectory() as d,patch.object(s,'BASE',Path(d)):
                v=s.version(0);v.mkdir(parents=True);(v/'URACE.md').write_text(self.text);s.atomic(v/'manifest.json',dict(version=0,sha256=s.digest(self.text),baseline_commit='abc'));s.publish(0,'changed',Path(d),{})
    def test_full_pipeline_with_simulated_executor_responses(self):
        # Tests engine wiring only; never recorded as live executor/value evidence.
        with tempfile.TemporaryDirectory() as d,patch.object(s,'BASE',Path(d)),patch.object(s.sys,'argv',['spec_trial.py']),patch.object(s,'eligible',return_value=(['codex'],{})),patch.object(s,'events',return_value=[]):
            b=Path(d);text=self.text+('Existing lifecycle explanation. '*30)+'\n';v=s.version(0);v.mkdir(parents=True);(v/'URACE.md').write_text(text);s.atomic(v/'manifest.json',dict(version=0,sha256=s.digest(text),baseline_commit='abc'));s.atomic(b/'active-version.json',dict(version=0,sha256=s.digest(text)));s.atomic(b/'settings.json',dict(enabled=True));s.atomic(b/'trial-clock.json',dict(ends_unix=time.time()+100));s.atomic(b/'harness-manifest.json',{});(b/'runs').mkdir()
            p=self.proposal();p['evidence_quote']=self.text.splitlines()[2]
            r=self.review();_,swapped=s.blind_review_prompt(text,text.replace('keeps','retains'), 'fixture')
            # Actual task id is random, so give both labels equal scores here and
            # normalize only the order through the worker's real prompt helper.
            r['scores']={'A':r['scores']['before'],'B':r['scores']['after']}
            r['behavior_equivalent']=True
            r['decision_cases']=[dict(question='Is preserving evidence a requirement?',A_answer='Yes',B_answer='Yes',contract_quote='It MUST preserve evidence.'),dict(question='Is there an existing lifecycle explanation?',A_answer='Yes',B_answer='Yes',contract_quote='Existing lifecycle explanation. ')]
            with patch.object(s,'blind_review_prompt',return_value=('fixture blind prompt',False)),patch.object(s,'native',side_effect=[p,r]):self.assertEqual(s.main(),0)
            self.assertEqual(s.load(b/'active-version.json')['version'],1);self.assertEqual(s.load(b/'state.json')['jobs'][0]['outcome'],'ACCEPTED_EDITORIAL_IMPROVEMENT');self.assertEqual(len(s.load(b/'version-comparisons.json')['versions']),2);self.assertEqual((s.version(0)/'URACE.md').read_text(),text)

if __name__=='__main__':unittest.main()

class NativePayloadDecoding(unittest.TestCase):
 def test_valid_payload_needs_no_recovery(self):
  payload,recovery=s.decode_native_payload('{"python_source":"pass"}');self.assertEqual(payload,{'python_source':'pass'});self.assertIsNone(recovery)
 def test_literal_newline_inside_string_is_preserved_and_labeled(self):
  text='{"python_source":"def f():\n    return 1"}'
  payload,recovery=s.decode_native_payload(text);self.assertEqual(payload['python_source'],'def f():\n    return 1');self.assertEqual(recovery['kind'],'UNESCAPED_JSON_STRING_CONTROL_CHARACTER');self.assertFalse(recovery['code_rewritten'])
 def test_structural_damage_is_not_repaired(self):
  for text in ['{"a":','{"a":1,}','prose {"a":1}','{"a":"x\ny",}']:
   with self.assertRaises(ValueError):s.decode_native_payload(text)
 def test_non_object_is_rejected(self):
  with self.assertRaises(ValueError):s.decode_native_payload('[1,2]')
