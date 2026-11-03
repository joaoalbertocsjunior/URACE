import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import common
import spec_trial as worker
import controls
import core_resources


class LifecycleIntegration(unittest.TestCase):
    def test_malformed_native_usage_still_closes_transport(self):
        import providers
        from unittest.mock import MagicMock
        client=MagicMock();client.line.side_effect=[json.dumps(v).encode() for v in [
            {'id':1,'result':{}},{'id':2,'result':{'thread':{'id':'t'}}},
            {'id':3,'result':{'data':[]}},{'id':5,'result':{'ordinaryUsageAllowed':True}},
            {'id':4,'result':{}},
            {'method':'thread/tokenUsage/updated','params':{'tokenUsage':{'total':{'inputTokens':True,'outputTokens':1,'totalTokens':2}}}},
            {'method':'item/completed','params':{'item':{'type':'agentMessage','text':'{}'}}},
            {'method':'turn/completed','params':{'turn':{'status':'completed'}}}]]
        with tempfile.TemporaryDirectory() as d,patch.object(providers,'Transport',return_value=client),patch.object(providers,'BASE',Path(d)):
            with self.assertRaises(ValueError):providers.codex('task',Path(d),{'id':'fixture','effort':'medium'})
        client.close.assert_called_once()

    def test_invalid_token_counters_never_become_measured_usage(self):
        from accounting import claude_usage,codex_usage
        for invalid in (True,2.5,-1):
            fields=dict(inputTokens=invalid,cacheCreationInputTokens=0,cacheReadInputTokens=0,outputTokens=1)
            with self.assertRaises(ValueError):claude_usage({'model_usage':{'model':fields}})
            with self.assertRaises(ValueError):codex_usage({'usage':{'total':dict(inputTokens=invalid,outputTokens=1,totalTokens=2)}})
    def test_adaptation_requires_accepted_work_and_complete_receipts(self):
        from review import recommend
        options={'executors':{p:{'resource_effort':'high'} for p in ('codex','claude')}}
        jobs=[{'proposer_provider':'codex','outcome':'ACCEPTED_EDITORIAL_IMPROVEMENT'} for _ in range(20)]
        rows=[{'kind':'finished','provider':'codex','tokens':100,'failure':None} for _ in range(20)]
        result=recommend(rows,jobs,options)
        self.assertEqual(result['codex']['delay_seconds'],1);self.assertEqual(result['claude']['delay_seconds'],5)
        rows[0]['tokens']=None
        self.assertEqual(recommend(rows,jobs,options)['codex']['delay_seconds'],5)

    def test_operator_controls_are_allowed_but_authority_is_frozen(self):
        from source_integrity import descriptor, matches
        from snapshot_metadata import engine_snapshot, verify_engine
        with tempfile.TemporaryDirectory() as d:
            base=Path(d);path=base/'config.json'
            config={'authority':{'reserved':['publish']},'resources':{'effort':'high'},'executor':{'enabled':True}}
            path.write_text(json.dumps(config));expected=descriptor(path)
            (base/'harness-manifest.json').write_text(json.dumps({'config.json':expected}))
            first=engine_snapshot(base)
            config['resources']['effort']='low';config['executor']['enabled']=False;path.write_text(json.dumps(config))
            self.assertTrue(matches(path,expected));second=engine_snapshot(base)
            self.assertNotEqual(first['id'],second['id']);self.assertTrue(verify_engine(first))
            config['authority']['reserved']=[];path.write_text(json.dumps(config))
            self.assertFalse(matches(path,expected))
            with self.assertRaises(RuntimeError):engine_snapshot(base)

    def test_period_feedback_withholds_sparse_percentiles_and_zero_baselines(self):
        from period_feedback import compare,percentiles
        self.assertIsNone(percentiles([1,2])['p50'])
        self.assertEqual(percentiles([1,2,3,4,5])['p50'],3)
        result=compare([],[],1792730000,'3h')
        self.assertIsNone(result['deltas']['known_tokens']['change_pct'])
        self.assertIsNone(result['current']['tokens_per_accepted_improvement'])

    def test_explicit_call_caps_apply_independently_and_null_remains_unlimited(self):
        from resource_governor import evaluate
        policy={'total_token_guard':None,'daily_token_guard':None,'provider_window_token_guard':None,
                'daily_native_seconds':None,'provider_window_native_seconds':None,'ends_unix':100000,'failure_backoff_seconds':60}
        rows=[{'id':'one','provider':'codex','product_id':'owner','at_unix':100}]
        config={'resource_product_id':'owner','executor':{'max_executor_calls_per_24h':None,'max_executor_calls_per_30d':None,
               'providers':[{'id':'codex','adapter':'codex-cli','max_calls_per_24h':1,'max_calls_per_30d':None}]}}
        self.assertFalse(evaluate('codex',rows,{},policy,101,local_config=config)['eligible'])
        self.assertTrue(evaluate('claude',rows,{},policy,101,local_config=config)['eligible'])
        config['executor']['providers'][0]['max_calls_per_24h']=None
        self.assertTrue(evaluate('codex',rows,{},policy,101,local_config=config)['eligible'])

    def test_all_utf8_product_bytes_have_a_bounded_review_window(self):
        text='Preamble\n# Large\n'+('Palpável 中文 evidence. '*5000)+'\n## Small\nTail.\n'
        parts=worker.sections(text)
        self.assertEqual(''.join(parts),text)
        self.assertTrue(all(len(p.encode())<=22000 for p in parts))
        self.assertGreater(len(parts),1)

    def test_pause_is_shared_with_the_real_core_state(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d)/'trial';base.mkdir();path=base.parent/'runtime/urace/config.json';path.parent.mkdir(parents=True)
            state=base.parent/'cohort/core.json';state.parent.mkdir();state.write_text('{"lifecycle_state":"PAUSED"}')
            path.write_text(json.dumps({'state_path':'../cohort/core.json'}))
            self.assertTrue(controls.effective(base)['paused'])

    def test_operational_code_is_bundled_without_external_python_imports(self):
        self.assertEqual(Path(worker.allocation.__file__).parent,Path(worker.__file__).parent)
        self.assertEqual(Path(worker.matches.__code__.co_filename).parent,Path(worker.__file__).parent)

    def test_default_operations_state_is_local_and_override_is_explicit(self):
        with tempfile.TemporaryDirectory() as d,patch.object(common,'BASE',Path(d)):
            self.assertEqual(common.operations_root(),Path(d)/'operations')
            (Path(d)/'operations-location.json').write_text('{"root":"relative"}')
            with self.assertRaises(ValueError):common.operations_root()

    def test_core_native_receipts_are_counted_once_and_mirrors_are_excluded(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);base=root/'trial';base.mkdir();runtime=root/'runtime/urace';runtime.mkdir(parents=True)
            state=root/'core.json'
            config={'resource_product_id':'spec','state_path':str(state), 'executor':{'providers':[{'id':'primary','adapter':'codex-cli'}]}}
            (runtime/'config.json').write_text(json.dumps(config))
            state.write_text(json.dumps({'executor_state':{'executor_calls':[
                {'id':'one','at':'2026-10-23T00:00:00+00:00','elapsed_seconds':2,'usage':{'transport_usage':[{'provider_id':'primary','usage':{'input_tokens':10,'output_tokens':3}}]}},
                {'id':'mirror','stage':'specification_adapter','at':'2026-10-23T00:00:00+00:00','usage':{'total_tokens':100}}]}}))
            sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runtime'))
            rows=core_resources.events(base,'spec','trial')
            done=[r for r in rows if r['kind']=='finished']
            self.assertEqual(len(done),1);self.assertEqual(done[0]['tokens'],13)
            self.assertEqual(done[0]['provider'],'codex')
            self.assertEqual(core_resources.events(base,'other','trial'),[])
            config['executor']['providers'][0].pop('adapter');(runtime/'config.json').write_text(json.dumps(config))
            self.assertEqual(core_resources.events(base,'spec','trial')[1]['provider'],'codex')

    def test_core_old_cohort_costs_are_not_pooled_into_fresh_trial(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);base=root/'trial';base.mkdir();runtime=root/'runtime/urace';runtime.mkdir(parents=True)
            state=root/'core.json';(runtime/'config.json').write_text(json.dumps({'resource_product_id':'spec','state_path':str(state)}))
            state.write_text(json.dumps({'executor_state':{'executor_calls':[{'id':'old','at':'2026-10-22T00:00:00+00:00','trial_id':'old','usage':{'total_tokens':10}}]}}))
            self.assertEqual(core_resources.events(base,'spec','fresh',1792713600),[])

class CoreReceiptReadCache(unittest.TestCase):
 def test_unchanged_core_state_is_parsed_once_without_retaining_owner_context(self):
  with tempfile.TemporaryDirectory() as directory:
   p=Path(directory)/'state.json';p.write_text(json.dumps({'intent':'private','executor_state':{'executor_calls':[{'id':'one'}]}}));real=Path.read_text
   with patch.object(Path,'read_text',autospec=True,side_effect=real) as read:
    a=core_resources.resource_state(p);b=core_resources.resource_state(p);self.assertEqual(read.call_count,1)
   self.assertNotIn('intent',a);self.assertEqual(a,b)
 def test_atomic_state_replacement_invalidates_cache(self):
  with tempfile.TemporaryDirectory() as directory:
   p=Path(directory)/'state.json';p.write_text('{"executor_state":{"executor_calls":[{"id":"one"}]}}');core_resources.resource_state(p)
   replacement=p.with_suffix('.new');replacement.write_text('{"executor_state":{"executor_calls":[{"id":"two"}]}}');replacement.replace(p)
   self.assertEqual(core_resources.resource_state(p)['executor_state']['executor_calls'][0]['id'],'two')
