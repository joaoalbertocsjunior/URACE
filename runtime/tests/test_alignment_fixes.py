import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urace import auto_goals, cli, launcher, user_controls, workflow_state, resource_usage, inspection
from urace import executor
from urace import command_surface


class AlignmentFixes(unittest.TestCase):
    def test_trial_inspection_routes_are_read_only_and_mutations_are_not(self):
        for argv in (['trial','status','analysis'],['trial','config','efficiency','--review'],['trial','data','metrics','show']):
            self.assertTrue(command_surface.read_only(argv))
        for argv in (['trial','config','efficiency','--file=x.json'],['trial','config','efficiency','--disable'],['trial','data','metrics','record']):
            self.assertFalse(command_surface.read_only(argv))
    def test_malformed_native_counters_stay_unknown_and_json_safe(self):
        fields=dict(inputTokens=float('nan'),cacheCreationInputTokens=0,cacheReadInputTokens=0,outputTokens=1)
        metadata=executor._claude_usage_metadata({'usage':{'input_tokens':True,'output_tokens':2.5},'modelUsage':{'model':fields},'total_cost_usd':float('nan')})
        self.assertIsNone(metadata['input_tokens']);self.assertIsNone(metadata['output_tokens'])
        self.assertNotIn('resource_total_tokens',metadata);json.dumps(metadata,allow_nan=False)
        self.assertEqual(resource_usage.usage_totals(metadata)['missing_usage'],1)
    def test_recovery_includes_extension_source_without_expanding_mutation_scope(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);trial=root/'urace/trial';trial.mkdir(parents=True)
            for name in ('spec_trial.py','state.json','ledger.jsonl','harness-manifest.json'):(trial/name).write_text('{}')
            config={'executor':{'allowed_files_by_scope':{'runtime':['urace/runtime/urace/cli.py']}}}
            before=copy.deepcopy(config)
            with patch.object(cli,'ROOT',root):files=cli.runtime_files(config)
            self.assertIn('urace/trial/spec_trial.py',files);self.assertIn('urace/trial/harness-manifest.json',files)
            self.assertNotIn('urace/trial/state.json',files);self.assertNotIn('urace/trial/ledger.jsonl',files)
            self.assertEqual(config,before)
    def project(self, replenish=False):
        return {'auto_goals': {'enabled': True, 'replenish_backlog': replenish},
                'authority': {'delegated': ['objectives']},
                'project': {'id': 'audit', 'intent': 'Improve the user project',
                            'requirements': [{'id': 'next', 'title': 'Next task',
                                              'success_measure': 'Validated output'}]}}

    def test_disabled_replenishment_does_not_create_next_goal(self):
        state = {'objectives': [{'id': 'previous', 'source': 'auto_goals', 'status': 'completed'}]}
        self.assertIsNone(auto_goals.select(self.project(), state))
        self.assertEqual(len(state['objectives']), 1)

    def test_disabled_replenishment_permits_initial_goal_and_continuation(self):
        config = self.project(); state = {}
        goal = auto_goals.select(config, state)
        self.assertIsNotNone(goal)
        self.assertEqual(auto_goals.select(config, state)['id'], goal['id'])

    def test_reenabled_replenishment_resumes_unfinished_project(self):
        state = {'objectives': [{'id': 'old', 'source': 'auto_goals', 'status': 'completed'}]}
        self.assertIsNotNone(auto_goals.select(self.project(True), state))

    def test_active_owner_goal_is_forwarded_to_executor_context(self):
        state = {'objectives': [{'id': 'owner', 'title': 'Owner work', 'status': 'active'}],
                 'current_objective': 'owner'}
        goals = workflow_state._context(state, {})['value']['objectives']
        self.assertTrue(goals, 'Active owner goal was dropped')
        self.assertEqual(goals[0]['id'], 'owner')

    def test_older_owner_context_is_not_silently_dropped(self):
        state = {'context_inputs': [{'id': str(i), 'text': 'Preserve constraint '+str(i)} for i in range(12)]}
        self.assertEqual(len(workflow_state._context(state, {})['value']['user_context']), 12)

    def test_oversized_owner_context_is_rejected_without_truncation(self):
        with self.assertRaises(workflow_state.WorkflowConflict):
            workflow_state._context({'constraints': ['x'*7000]}, {})

    def test_effort_changes_core_cadence_without_changing_native_effort(self):
        values = []
        for effort in ('low', 'medium', 'high'):
            config = {'resources': {'effort': effort}, 'executor': {'native_options': {'codex': {'native_effort': 'medium'}}}}
            before = copy.deepcopy(config)
            values.append(user_controls.discovery_interval(config, {}, 100, 1000, 0)['discovery_interval_seconds'])
            self.assertEqual(config, before)
        self.assertEqual(values, [400, 100, 25])

    def test_per_executor_effort_and_no_yield_backoff_apply(self):
        config = {'resources': {'effort': 'high', 'executor_effort': {'worker': 'low'}}}
        state = {'executor_state': {'provider_pool': {'last_selected_provider': 'worker'}}}
        self.assertEqual(user_controls.discovery_interval(config, state, 100, 1000, 2)['discovery_interval_seconds'], 1000)

    def test_launcher_resolves_product_specific_state_and_fallback(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); (root/'urace').mkdir()
            (root/'urace/config.json').write_text(json.dumps({'state_path': '../cohort/state.json'}))
            with patch.object(launcher, 'RUNTIME_ROOT', root):
                state, stable = launcher.configured_paths()
            self.assertEqual(state.resolve(), (root/'../cohort/state.json').resolve())
            self.assertEqual(stable.resolve(), state.parent.resolve()/'stable-runtime')

    def test_launcher_honors_active_product_registry(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); (root/'urace').mkdir()
            (root/'urace/config.json').write_text(json.dumps({'state_path': 'default.json', 'active_product': 'owner',
                 'product_registry': [{'name': 'owner', 'state_path': 'chosen/state.json'}]}))
            with patch.object(launcher, 'RUNTIME_ROOT', root), patch.dict('os.environ', {}, clear=True):
                self.assertEqual(launcher.configured_paths()[0], root/'chosen/state.json')

    def test_usage_does_not_double_count_cached_codex_tokens(self):
        self.assertEqual(resource_usage.usage_totals({'input_tokens': 10, 'output_tokens': 3, 'cached_input_tokens': 8})['known_tokens'], 13)

    def test_usage_includes_claude_cache_and_zero_is_observed(self):
        self.assertEqual(resource_usage.usage_totals({'resource_total_tokens': 43, 'input_tokens': 2, 'output_tokens': 3})['known_tokens'], 43)
        self.assertEqual(resource_usage.usage_totals({'input_tokens': 0, 'output_tokens': 0})['missing_usage'], 0)
        self.assertEqual(resource_usage.usage_totals({'input_tokens': True, 'output_tokens': 3})['missing_usage'], 1)
        self.assertEqual(resource_usage.usage_totals({'input_tokens': 2.5, 'output_tokens': 3})['missing_usage'], 1)

    def test_partial_transport_usage_preserves_known_cost_and_unknowns(self):
        result = resource_usage.usage_totals({'input_tokens': 999, 'transport_usage': [
            {'usage': {'input_tokens': 10, 'output_tokens': 3}}, {'usage': None}]})
        self.assertEqual((result['known_tokens'], result['missing_usage']), (13, 1))
        self.assertIsNone(result['reported_cost_usd'])

    def test_freeform_receipts_are_visible_without_duplication(self):
        with tempfile.TemporaryDirectory() as d:
            config = {'state_path': str(Path(d)/'state.json')}
            call = {'id': 'native-1', 'at': '2026-10-23T00:00:00+00:00', 'usage': {'total_tokens': 5}}
            state = {'executor_state': {'executor_calls': [call]}}
            (Path(d)/'freeform-routing-resources.jsonl').write_text(json.dumps({'id': 'native-1', 'reported_usage': {'total_tokens': 5}})+'\n'+json.dumps({'id': 'native-2', 'reported_usage': {'total_tokens': 7}})+'\n')
            result = resource_usage.summary(config, state)
            self.assertEqual((result['logical_calls'], result['known_tokens']), (2, 12))

    def test_native_cost_survives_state_retention_and_replay_deduplicates(self):
        with tempfile.TemporaryDirectory() as d:
            config = {'state_path': str(Path(d)/'owner? # quoted/state.json'), 'resource_product_id': 'owner-product'}
            state = {'executor_state': {'executor_calls': [{'id':'call-1','usage':{'total_tokens':13}}]}}
            resource_usage.archive_calls(config,state);resource_usage.archive_calls(config,state)
            self.assertEqual(resource_usage.summary(config,{'executor_state':{'executor_calls':[]}})['known_tokens'],13)
            self.assertEqual(resource_usage.summary(config,state)['logical_calls'],1)
            other={**config,'resource_product_id':'different-product'}
            self.assertEqual(resource_usage.summary(other,{})['known_tokens'],0)
            other={**config,'active_product':'Another project','product_registry':[{'name':'Another project','id':'other-id','state_path':str(Path(config['state_path']).with_name('other-state.json'))}]}
            self.assertEqual(resource_usage.product_identity(other),'other-id')
            self.assertEqual(resource_usage.summary(other,{})['known_tokens'],0)


class WorkflowBoundaryTests(unittest.TestCase):
    def test_adapter_rejects_version_path_escape(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d);(base/'version-series.json').write_text('{"root":"../outside"}')
            with self.assertRaises(workflow_state.WorkflowConflict):workflow_state._version_folder(base,0)

    def test_adapter_rejects_product_symlink_escape(self):
        with tempfile.TemporaryDirectory() as d,tempfile.TemporaryDirectory() as other:
            base=Path(d);(base/'product').symlink_to(other,target_is_directory=True)
            with self.assertRaises(workflow_state.WorkflowConflict):
                workflow_state.product_copy({'specification_workflow':{'product_copy':str(base/'product/URACE.md')}},base)

    def test_observations_are_idempotent_and_do_not_claim_user_value(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d)
            job={'id':'spec-real-fixture','trial_id':'trial','outcome':'AUDITED_NO_CHANGE','started_at':'2026-10-23T00:00:00+00:00','finished_at':'2026-10-23T00:01:00+00:00','section':'# Example'}
            (base/'trial-clock.json').write_text('{"trial_id":"trial"}');(base/'state.json').write_text(json.dumps({'jobs':[job]}))
            (base/'ledger.jsonl').write_text(json.dumps({'kind':'finished','id':'native-fixture','provider':'codex','trial_id':'trial','at':job['started_at'],'tokens':None})+'\n')
            state={};workflow_state._import_observations({},state,base);workflow_state._import_observations({},state,base)
            self.assertEqual(len(state['operations']),1)
            self.assertFalse(state['operations'][0]['real_user_value_verified'])
            self.assertEqual(len(state['executor_state']['executor_calls']),1)
            self.assertTrue(state['executor_state']['executor_calls'][0]['usage_missing'])
    def test_pause_preserves_state_and_never_assesses_or_executes(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            config = {'state_path': str(base/'core.json'), 'product': 'Owner product'}
            state = {'state_version': 0, 'lifecycle_state': 'PAUSED', 'objectives': []}
            with patch.object(cli, 'load_config', return_value=config), patch.object(cli, 'load_state', return_value=state), \
                 patch.object(cli, 'consume_inputs', return_value=[]), patch.object(workflow_state, '_synchronize_copy'), \
                 patch.object(workflow_state, '_import_observations'), patch.object(cli, 'cycle', side_effect=AssertionError('Paused')), \
                 patch('urace.cognitive_resume.generate', return_value={}), patch.object(cli, 'cleanup_consumed_inputs'):
                self.assertFalse(workflow_state.boundary(base)['permitted'])
            self.assertEqual(json.loads((base/'core.json').read_text())['lifecycle_state'], 'PAUSED')

    def test_boundary_runs_core_with_native_dispatch_disabled(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d); config = {'state_path': str(base/'core.json'), 'executor': {'enabled': True}}
            state = {'state_version': 0, 'lifecycle_state': 'DORMANT'}
            with patch.object(cli, 'load_config', return_value=config), patch.object(cli, 'load_state', return_value=state), \
                 patch.object(cli, 'consume_inputs', return_value=[]), patch.object(workflow_state, '_synchronize_copy'), \
                 patch.object(workflow_state, '_import_observations'), patch.object(cli, '_run_onboard_gate', return_value=None), \
                 patch.object(cli, '_check_scheduled_tasks'), patch.object(cli, 'cycle', return_value={'outcome': 'dormant'}) as cycle, \
                 patch('urace.cognitive_resume.generate', return_value={}), patch.object(cli, 'cleanup_consumed_inputs'):
                self.assertTrue(workflow_state.boundary(base)['permitted'])
            self.assertFalse(cycle.call_args.args[0]['executor']['enabled'])
            self.assertFalse(cycle.call_args.kwargs['allow_execution'])
            self.assertTrue(config['executor']['enabled'])

    def test_external_product_edit_is_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d); target = base/'product/URACE.md';target.parent.mkdir();target.write_text('Owner edit')
            version = base/'versions/v000000';version.mkdir(parents=True);(version/'URACE.md').write_text('Baseline')
            sha = workflow_state._sha(b'Baseline')
            for path, value in [('active-version.json', {'version': 0, 'sha256': sha}), ('version-series.json', {'root': 'versions'}), ('versions/v000000/manifest.json', {'sha256': sha})]:
                (base/path).write_text(json.dumps(value))
            with self.assertRaises(workflow_state.WorkflowConflict):
                workflow_state._synchronize_copy({'specification_workflow': {'product_copy': str(target)}}, {}, base)
            self.assertEqual(target.read_text(), 'Owner edit')


class WarningGrowthTests(unittest.TestCase):
    def test_repeated_missing_fields_are_observed_without_losing_warning(self):
        state={'evidence':[{'id':'e1'}]}
        cli._validate_citizen_base_conformance(state)
        first=json.dumps(state['integrity_gaps'],sort_keys=True)
        for _ in range(20):cli._validate_citizen_base_conformance(state)
        self.assertEqual(len(state['integrity_gaps']),1)
        self.assertEqual(json.dumps(state['integrity_gaps'],sort_keys=True),first)
        self.assertEqual(state['integrity_gap_observations']['citizen:evidence record e1']['observations'],21)
        state['evidence'].append({'id':'e2'});cli._validate_citizen_base_conformance(state)
        self.assertEqual(len(state['integrity_gaps']),2)
    def test_legacy_unresolved_warning_is_preserved_not_duplicated(self):
        gap={'id':'old','kind':'citizen-base-violation','resolved':False,'detail':"evidence record e1 missing CitizenBase fields: {'updated_at', 'created_at'}"}
        state={'evidence':[{'id':'e1'}],'integrity_gaps':[gap.copy()]}
        cli._validate_citizen_base_conformance(state)
        self.assertEqual(state['integrity_gaps'],[gap])
    def test_retention_repeat_keeps_latest_count_without_appending(self):
        state={}
        for i in range(5):cli._observe_retention_gaps(state,[{'id':str(i),'kind':'retention-policy-violated','active':True,'description':f"Field 'trace_records' has {1001+i} entries, exceeding ceiling of 1000"}])
        self.assertEqual(len(state['integrity_gaps']),1)
        self.assertIn('1005 entries',state['integrity_gap_observations']["retention:Field 'trace_records'"]['latest_detail'])
    def test_resolved_warning_does_not_hide_recurrence(self):
        state={'evidence':[{'id':'e1'}]};cli._validate_citizen_base_conformance(state);state['integrity_gaps'][0]['resolved']=True
        cli._validate_citizen_base_conformance(state);self.assertEqual(len(state['integrity_gaps']),2)


class CorrectiveObservationTests(unittest.TestCase):
    def test_restore_is_verified_effect_but_never_claimed_quality_gain(self):
        import types,sys
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);(base/'version-series.json').write_text(json.dumps({'root':'versions'}));(base/'trial-clock.json').write_text(json.dumps({'trial_id':'t'}))
            job={'id':'spec-restore','trial_id':'t','outcome':'CORRECTIVE_RESTORE','accepted_version':2,'started_at':'2026-01-01T00:00:00+00:00','finished_at':'2026-01-01T00:01:00+00:00','section':'Exact restore'}
            (base/'state.json').write_text(json.dumps({'jobs':[job]}));copy_path=base/'product/URACE.md';copy_path.parent.mkdir();copy_path.write_text('source')
            review={'method':'Exact earlier immutable snapshot restoration'}
            checked={'manifest':{'trial_id':'t','job':'/runs/spec-restore','validation':review,'restoration':{'target_version':0}},'metadata':{'validation':{'model_review':review}},'completion':{'task_id':'spec-restore','task_outcome':'CORRECTIVE_RESTORE'}}
            with patch.dict(sys.modules,{'snapshot_metadata':types.SimpleNamespace(inspect_snapshot=lambda p:checked)}):
                state={};workflow_state._import_observations({'specification_workflow':{'product_copy':str(copy_path)}},state,base)
            op=state['operations'][0];self.assertEqual(op['status'],'ACCEPTED');self.assertFalse(op['quality_improvement_claimed']);self.assertFalse(op['real_user_value_verified']);self.assertEqual(op['snapshot'],str(base/'versions/v000002'))
