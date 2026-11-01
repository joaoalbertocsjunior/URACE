import hashlib,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import spec_trial as s
import snapshot_metadata as m
import product_resources as p
import efficiency_score as scoring
import test_spec_trial as fixtures

class SnapshotMetadata(unittest.TestCase):
    def setup_base(self,b):
        text=fixtures.SpecTrialTests.text;v=b/'versions/v000000';v.mkdir(parents=True);(v/'URACE.md').write_text(text)
        s.atomic(v/'manifest.json',dict(version=0,sha256=s.digest(text),baseline_sha256=s.digest(text),baseline_commit='fixture'))
        s.atomic(b/'harness-manifest.json',{});s.atomic(b/'active-version.json',dict(version=0,sha256=s.digest(text)));job=b/'runs/trial/job';job.mkdir(parents=True)
        return text,job
    def test_snapshot_contains_both_scopes_and_all_declared_features(self):
        with tempfile.TemporaryDirectory() as d,patch.object(s,'BASE',Path(d)):
            b=Path(d);text,job=self.setup_base(b);s.publish(0,text.replace('keeps','retains'),job,fixtures.SpecTrialTests().review())
            result=m.inspect_snapshot(s.version(1));meta=result['metadata']
            self.assertEqual(set(meta['feature_coverage']),set(m.FEATURES));self.assertEqual(set(meta['scope_index']),{'product_results','runtime_operation'});self.assertTrue(result['integrity_verified'])
            (s.version(1)/'parent.diff').write_text('corrupted')
            with self.assertRaisesRegex(RuntimeError,'evidence corruption'):m.inspect_snapshot(s.version(1))
    def test_metadata_failure_never_publishes_a_partial_version(self):
        with tempfile.TemporaryDirectory() as d,patch.object(s,'BASE',Path(d)):
            b=Path(d);text,job=self.setup_base(b)
            with patch.object(m,'create',side_effect=RuntimeError('simulated disk failure')):
                with self.assertRaises(RuntimeError):s.publish(0,text.replace('keeps','retains'),job,fixtures.SpecTrialTests().review())
            self.assertFalse(s.version(1).exists());self.assertEqual(s.load(b/'active-version.json')['version'],0);self.assertTrue(list((b/'versions').glob('*.pending')))
            s.publish(0,text.replace('keeps','retains'),job,fixtures.SpecTrialTests().review());self.assertTrue(s.version(1).exists())
    def test_committed_snapshot_recovery_is_verified_and_idempotent(self):
        with tempfile.TemporaryDirectory() as d,patch.object(s,'BASE',Path(d)):
            b=Path(d);text,job=self.setup_base(b);s.publish(0,text.replace('keeps','retains'),job,fixtures.SpecTrialTests().review());s.atomic(b/'active-version.json',dict(version=0,sha256=s.digest(text)))
            state=dict(jobs=[],inflight=dict(id='job',parent_version=0));s.recover_publication(state);self.assertEqual(s.load(b/'active-version.json')['version'],1);self.assertEqual(state['jobs'][0]['outcome'],'ACCEPTED_EDITORIAL_IMPROVEMENT');self.assertTrue((s.version(1)/'completion.json').exists());s.recover_publication(state);self.assertEqual(len(state['jobs']),1)
    def test_unknown_feature_schema_is_rejected(self):
        with self.assertRaises(ValueError):m.validate({'schema':m.SCHEMA,'feature_coverage':{}})
    def test_historical_engine_is_frozen_and_corruption_detected(self):
        with tempfile.TemporaryDirectory() as d,patch.object(s,'BASE',Path(d)):
            b=Path(d);text,job=self.setup_base(b);source=b/'engine.py';source.write_text('original engine');s.atomic(b/'harness-manifest.json',{'engine.py':m.sha(source.read_bytes())});s.publish(0,text.replace('keeps','retains'),job,fixtures.SpecTrialTests().review());view=m.inspect_snapshot(s.version(1));reference=view['metadata']['engine'];source.write_text('new engine')
            self.assertTrue(m.inspect_snapshot(s.version(1))['integrity_verified']);engine_root=Path(reference['path']);entry=s.load(engine_root/'manifest.json')['files'][0];(engine_root/entry['snapshot_file']).write_text('corrupted engine')
            with self.assertRaisesRegex(RuntimeError,'Engine evidence corruption'):m.inspect_snapshot(s.version(1))
    def test_per_product_runtime_costs_do_not_pool_other_products_or_trials(self):
        with tempfile.TemporaryDirectory() as d:
            b=Path(d);rows=[]
            for i,(trial,product,tokens) in enumerate([('old','a',900),('new','a',100),('new','b',200)]):rows.extend([dict(kind='reserved',id=str(i),provider='codex',product_id=product,trial_id=trial),dict(kind='finished',id=str(i),product_id=product,trial_id=trial,tokens=tokens,wall_seconds=1)])
            (b/'ledger.jsonl').write_text('\n'.join(json.dumps(r) for r in rows)+'\n')
            self.assertEqual(m.trial_resources(b,'new','a')['known_tokens'],100);self.assertEqual(m.trial_resources(b,'new')['known_tokens'],300)
    def test_product_and_runtime_rollups_cover_all_declared_features(self):
        with tempfile.TemporaryDirectory() as d,patch.object(p,'BASE',Path(d)),patch.object(scoring,'BASE',Path(d)),patch.object(p,'events',return_value=[]):
            b=Path(d);self.setup_base(b);s.atomic(b/'products.json',dict(products=[dict(id='a',name='Alpha')],state_product_id='a'));s.atomic(b/'contract.json',dict(product_id='a',target_product='Alpha'));s.atomic(b/'trial-clock.json',dict(trial_id='new'));s.atomic(b/'settings.json',{});s.atomic(b/'state.json',{'jobs':[]})
            paths=m.rollups(b)
            for path in paths.values():
                result=s.load(Path(path));self.assertEqual(result['trial_id'],'new');self.assertEqual(result['known_tokens'],0);self.assertTrue(m.validate(result['analysis_metadata']));self.assertEqual(set(result['analysis_metadata']['feature_coverage']),set(m.FEATURES))

if __name__=='__main__':unittest.main()
