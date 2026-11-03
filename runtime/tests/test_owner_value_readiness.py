"""Regression checks from independently reviewed genuine source defects.

Fixtures are engineering acceptance checks, not fabricated user observations.
This file remains outside each candidate executor's workspace.
"""
import copy
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from datetime import datetime, timezone
from urace import cli, executor, inspection, outcome_verification


class Usage(unittest.TestCase):
    def test_numeric_provider_token_extensions_survive_without_reasoning_text(self):
        tokens = dict(input_tokens=100, cached_input_tokens=60, output_tokens=20,
                      reasoning_output_tokens=5, cache_write_input_tokens=0)
        event = dict(type='turn.completed', usage=dict(tokens, reasoning_text='not retained',
                                                      guessed_tokens=True, invalid_tokens=-1))
        metadata = executor._codex_usage_metadata(json.dumps(event))
        self.assertEqual(metadata['reported_token_usage'], tokens)
        self.assertIsNone(metadata['reported_cost_usd'])
        self.assertNotIn('not retained', json.dumps(metadata))

    def test_provider_token_usage_survives_codex_adapter_and_routing(self):
        for heartbeat in (False, True):
            with self.subTest(heartbeat=heartbeat), tempfile.TemporaryDirectory() as directory:
                usage = dict(input_tokens=1400, cached_input_tokens=1000, output_tokens=25)
                stream = json.dumps({'type': 'turn.completed', 'usage': usage}) + '\n'
                def run(command, **kwargs):
                    Path(command[command.index('--output-last-message') + 1]).write_text('done')
                    self.assertIn('--json', command)
                    return subprocess.CompletedProcess(command, 0, stream, '')
                class Process:
                    def __init__(self, command, **kwargs):
                        self.result = run(command)
                        self.returncode = 0
                    def communicate(self, **kwargs): return self.result.stdout, self.result.stderr
                    def poll(self): return 0
                health = dict(available=True, checked_at='2026-10-21T00:00:00+00:00', reason='fixture')
                settings = {'providers': [dict(id='fixture', command=sys.executable,
                            adapter='codex-cli', capabilities=['execution'])]}
                with patch.object(executor, 'availability', return_value=health), \
                     patch.object(executor.subprocess, 'run', side_effect=run), \
                     patch.object(executor.subprocess, 'Popen', Process):
                    result = executor.run_routed_codex(Path(directory), settings, {}, 'fixture', None,
                        'read-only', 'execution', (lambda elapsed: None) if heartbeat else None)
                metadata = result.get('__urace_executor_metadata__', {})
                self.assertEqual(metadata.get('input_tokens'), 1400)
                self.assertEqual(metadata.get('output_tokens'), 25)
                self.assertEqual(metadata.get('cached_input_tokens'), 1000)
                self.assertIsNone(metadata.get('reported_cost_usd'))


class Readiness(unittest.TestCase):
    def check(self, objectives, expected):
        settings = {'executor': {'enabled': True}}
        state = {'objectives': objectives, 'evidence': []}
        def available(settings, pool, capability):
            return dict(available=capability == expected, checked_at='2026-10-21T00:00:00+00:00', reason='fixture')
        with patch.object(cli.intelligent_executor, 'pool_availability', side_effect=available) as probe:
            result = cli.refresh_executor_availability(settings, state, force=True)
        self.assertTrue(result['available'])
        self.assertEqual(probe.call_args.args[2], expected)

    def test_existing_runnable_job_probes_execution(self):
        self.check([dict(id='real-job', status='planned', title='repair', scope='runtime', necessity_evidence='Observed runtime defect', lower_impact_route_sufficient=False)], 'execution')

    def test_unauthorized_runtime_job_keeps_discovery(self):
        self.check([dict(id='unauthorized', status='planned', scope='runtime')], 'discovery')

    def test_empty_job_queue_probes_discovery(self):
        self.check([], 'discovery')

    def test_completed_jobs_do_not_force_execution(self):
        self.check([dict(id='done', status='completed')], 'discovery')


class Independence(unittest.TestCase):
    @unittest.skipUnless(outcome_verification._DIRECTORY_RELATIVE_OPEN, 'requires directory-relative no-follow open')
    def test_source_replacement_during_open_is_rejected_before_read(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, writable = root/'observations.json', root/'writable.json'
            source.write_text('{"baseline": {"successes": 0, "trials": 1}}')
            writable.write_text('{"baseline": {"successes": 1, "trials": 1}}')
            native_open, path_open = os.open, Path.open
            replaced = []
            def swap():
                if not replaced:
                    source.unlink(); os.link(writable, source); replaced.append(True)
            def intercepted_open(path, *args, **kwargs):
                if Path(path).name == source.name: swap()
                return native_open(path, *args, **kwargs)
            def intercepted_path_open(path, *args, **kwargs):
                if path == source: swap()
                return path_open(path, *args, **kwargs)
            with patch.object(os, 'open', side_effect=intercepted_open), \
                 patch.object(Path, 'open', new=intercepted_path_open):
                with self.assertRaisesRegex(ValueError, 'changed while being opened'):
                    outcome_verification._read(root, {'source': source.name}, [writable.name])
            self.assertTrue(replaced)

    def test_nonregular_source_is_rejected_without_waiting_for_a_writer(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            os.mkfifo(root/'pipe')
            with self.assertRaisesRegex(ValueError, 'regular file'):
                outcome_verification._read(root, {'source': 'pipe'}, [])

    def test_hardlinked_writable_alias_cannot_be_independent_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'writable.json'
            source.write_text('{"baseline": {"successes": 0, "trials": 1}}')
            os.link(source, root / 'observations.json')
            with self.assertRaises(ValueError):
                outcome_verification._read(root, {'source': 'observations.json'}, ['writable.json'])

    def test_distinct_nonwritable_source_remains_readable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'observations.json').write_text('{"baseline": {"successes": 0, "trials": 1}}')
            result = outcome_verification._read(root, {'source': 'observations.json'}, ['missing.json'])
            self.assertEqual(result['baseline']['trials'], 1)


class CapabilityCache(unittest.TestCase):
    def test_legacy_discovery_cache_is_preserved_until_execution_is_needed(self):
        config = {'executor': {'enabled': True, 'available_probe_interval_seconds': 300}}
        state = {'objectives': [], 'evidence': [], 'executor_state': {
            'available': True, 'last_availability_check': datetime.now(timezone.utc).isoformat()}}
        with patch.object(cli.intelligent_executor, 'pool_availability') as probe:
            self.assertTrue(cli.refresh_executor_availability(config, state)['available'])
        probe.assert_not_called()
        state['objectives'].append({'id': 'fixture', 'status': 'planned'})
        health = {'available': True, 'checked_at': datetime.now(timezone.utc).isoformat(), 'reason': 'fixture'}
        with patch.object(cli.intelligent_executor, 'pool_availability', return_value=health) as probe:
            cli.refresh_executor_availability(config, state)
        self.assertEqual(probe.call_args.args[2], 'execution')

    def test_queue_changes_reprobe_capability_without_waiting_for_cache_expiry(self):
        config = {'executor': {'enabled': True, 'available_probe_interval_seconds': 300}}
        state = {'objectives': [], 'evidence': []}
        def health(settings, pool, capability):
            return {'available': True, 'checked_at': datetime.now(timezone.utc).isoformat(), 'reason': 'fixture'}
        with patch.object(cli.intelligent_executor, 'pool_availability', side_effect=health) as probe:
            cli.refresh_executor_availability(config, state)
            self.assertEqual(probe.call_args.args[2], 'discovery')
            state['objectives'].append({'id': 'owner-job', 'status': 'planned'})
            cli.refresh_executor_availability(config, state)
            self.assertEqual(probe.call_count, 2)
            self.assertEqual(probe.call_args.args[2], 'execution')
            state['objectives'][0]['status'] = 'completed'
            cli.refresh_executor_availability(config, state)
            self.assertEqual(probe.call_count, 3)
            self.assertEqual(probe.call_args.args[2], 'discovery')


class ProductSurface(unittest.TestCase):
    def fixture(self, root, files):
        return ({'product_files': files, 'capability_envelope': {'capabilities': [{'id': 'fixture', 'value_weight': 1}]}},
                {'capability_states': [{'capability_id': 'fixture', 'status': 'CAPABLE', 'completeness_fraction': 1}],
                 'integrity_gaps': []})

    def test_outside_product_sources_never_count_toward_assessment(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'product'; root.mkdir()
            outside = Path(directory) / 'outside.txt'; outside.write_text('outside\n' * 5)
            for source in (str(outside), '../outside.txt', 'linked.txt'):
                with self.subTest(source=source):
                    link = root / 'linked.txt'
                    if not link.exists(): link.symlink_to(outside)
                    config, state = self.fixture(root, [source])
                    with patch.object(cli, 'ROOT', root):
                        cli._evaluate_sweet_spot(state, config)
                    self.assertFalse(state.get('sweet_spot_assessments'))
                    self.assertFalse(state.get('value_density_history'))
                    self.assertTrue(any(g['kind'] == 'product-surface-unavailable' for g in state['integrity_gaps']))

    def test_missing_surface_does_not_become_a_zero_size_success(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config, state = self.fixture(root, ['missing.txt'])
            with patch.object(cli, 'ROOT', root):
                cli._evaluate_sweet_spot(state, config)
            self.assertFalse(state.get('sweet_spot_assessments'))

    def test_milestone_own_limits_apply_without_envelope_limits(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root/'README.md').write_text('one\ntwo\nthree\n')
            for limit in ({'complexity_ceiling': 1}, {'value_density_floor': 1}, {'complexity_ceiling': 0}):
                with self.subTest(limit=limit):
                    config, state = self.fixture(root, ['README.md'])
                    milestone = {'id': 'fixture-milestone', 'status': 'ACTIVE', **limit}
                    config['capability_envelope']['milestones'] = [milestone]
                    with patch.object(cli, 'ROOT', root):
                        cli._evaluate_sweet_spot(state, config)
                    self.assertEqual(milestone['status'], 'ACTIVE')
                    self.assertFalse(state.get('product_versions'))
                    self.assertFalse(any(e['kind'] == 'milestone-achieved' for e in state.get('evidence', [])))

    def test_milestone_zero_density_floor_is_an_explicit_override(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root/'README.md').write_text('one\ntwo\nthree\n')
            config, state = self.fixture(root, ['README.md'])
            milestone = {'id': 'fixture-milestone', 'status': 'ACTIVE', 'value_density_floor': 0}
            config['capability_envelope'].update(value_density_floor=1, milestones=[milestone])
            with patch.object(cli, 'ROOT', root):
                cli._evaluate_sweet_spot(state, config)
            self.assertEqual(milestone['status'], 'ACHIEVED')

    def test_product_surface_uses_product_root_with_separate_state_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'product'
            state_root = Path(directory) / 'private-state'
            root.mkdir(); state_root.mkdir()
            (root / 'README.md').write_text('one\ntwo\nthree\n')
            (state_root / 'README.md').write_text('state must not determine product surface\n')
            config = {'state_path': str(state_root / 'state.json'), 'product_files': ['README.md'],
                      'capability_envelope': {'capabilities': [{'id': 'fixture', 'value_weight': 1}],
                                              'complexity_ceiling': 2}}
            state = {'capability_states': [{'capability_id': 'fixture', 'status': 'CAPABLE', 'completeness_fraction': 1}],
                     'integrity_gaps': []}
            with patch.object(cli, 'ROOT', root):
                cli._evaluate_sweet_spot(state, config)
            self.assertEqual(state['sweet_spot_assessments'][-1]['maturity_level'], 'OVER_ENGINEERED')
            self.assertEqual(state['value_density_history'][-1]['surface_measure'], 3)


class ProviderFailures(unittest.TestCase):
    def test_structured_capacity_error_is_deferred_without_raw_model_output(self):
        stream = '\n'.join([
            json.dumps({'type': 'item.completed', 'item': {'text': 'private_model_reasoning'}}),
            json.dumps({'type': 'error', 'message': 'usage limit reached'}),
            json.dumps({'type': 'turn.failed', 'error': {'message': 'usage limit reached'}}),
        ])
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(executor.shutil, 'which', return_value='/bin/codex'), \
             patch.object(executor, '_run_with_heartbeats', return_value=(1, stream, '')):
            with self.assertRaises(executor.ExecutorUnavailable) as error:
                executor._run_codex(Path(directory), {}, 'fixture', None, 'read-only')
        self.assertNotIn('private_model_reasoning', str(error.exception))

    def test_error_events_redact_credential_values_and_ignore_other_events(self):
        token = 'sk-' + 'a' * 25
        stream = '\n'.join([
            '[]',
            json.dumps({'type': 'item.completed', 'message': 'must not retain'}),
            json.dumps({'type': 'error', 'message': f'Invalid credential {token} Bearer credential-value'}),
        ])
        detail = executor._codex_error_detail(stream)
        self.assertNotIn(token, detail)
        self.assertNotIn('credential-value', detail)
        self.assertNotIn('must not retain', detail)


class LegacyProviderCapabilities(unittest.TestCase):
    def test_legacy_primary_can_dispatch_without_mutating_config(self):
        settings = {'providers': [{'id': 'primary'}]}
        health = {'available': True, 'checked_at': datetime.now(timezone.utc).isoformat(), 'reason': 'fixture'}
        with patch.object(executor, 'availability', return_value=health), \
             patch.object(executor, '_run_codex', return_value={'message': 'fixture'}) as run:
            result = executor.run_routed_codex(Path('/tmp'), settings, {}, 'fixture', None, 'read-only', 'execution')
        self.assertEqual(result['message'], 'fixture')
        run.assert_called_once()
        self.assertNotIn('capabilities', settings['providers'][0])

    def test_explicit_empty_capabilities_are_unavailable_and_never_dispatch(self):
        settings = {'providers': [{'id': 'primary', 'capabilities': []}]}
        with patch.object(executor, 'availability') as health, patch.object(executor, '_run_codex') as run:
            report = executor.pool_availability(settings, {}, 'execution')
            self.assertFalse(report['available'])
            with self.assertRaises(executor.ExecutorUnavailable):
                executor.run_routed_codex(Path('/tmp'), settings, {}, 'fixture', None, 'read-only', 'execution')
        health.assert_not_called()
        run.assert_not_called()


class EligibilityGapIdentity(unittest.TestCase):
    def test_repeated_denial_and_resolved_recurrence_preserve_unique_records(self):
        from urace import inspection
        objective = dict(id='owner-job', kind='CAPABILITY_DEFINING', scope='documentation')
        state = {'sweet_spot_assessments': [{'maturity_level': 'CAPABLE'}]}
        for _ in range(5):
            self.assertFalse(inspection.objective_is_eligible(state, objective))
        self.assertEqual(len(state['integrity_gaps']), 1)
        original = state['integrity_gaps'][0]
        original['resolved'] = True
        for _ in range(5):
            self.assertFalse(inspection.objective_is_eligible(state, objective))
        gaps = state['integrity_gaps']
        self.assertEqual(len(gaps), 2)
        self.assertTrue(original['resolved'])
        self.assertEqual(len({gap['id'] for gap in gaps}), 2)
        state['decision_records'] = [{'kind': 'AUTHORITY_GRANT',
                                     'authorized_objective_ids': [objective['id']]}]
        self.assertTrue(inspection.objective_is_eligible(state, objective))

    def test_legacy_active_gap_is_reused(self):
        from urace import inspection
        objective = dict(id='owner-job', kind='CAPABILITY_DEFINING', scope='documentation')
        original = dict(id='igap-cap-envelope-owner-job', kind='capability-envelope-breach', resolved=False)
        state = {'sweet_spot_assessments': [{'maturity_level': 'CAPABLE'}],
                 'integrity_gaps': [original]}
        self.assertFalse(inspection.objective_is_eligible(state, objective))
        self.assertEqual(state['integrity_gaps'], [original])


class RuntimeFailureDiagnostics(unittest.TestCase):
    def test_header_overflow_reports_omissions_within_budget(self):
        output = ''.join(f'ERROR: test_{i}_' + 'x' * 90 + ' (checks.Case)\nRuntimeError: fixture\n'
                         for i in range(200))
        output += 'Ran 200 tests in 1.0s\n\nFAILED (errors=200)\n'
        detail = executor._runtime_test_failure_detail(output)
        self.assertLessEqual(len(detail), 6000)
        self.assertIn('omitted', detail)
        self.assertIn('FAILED (errors=200)', detail)

    def test_abbreviated_adjacent_failures_keep_terminal_errors(self):
        output = ('ERROR: test_a (checks.Case)\nRuntimeError: first\n'
                  'ERROR: test_b (checks.Case)\nRuntimeError: second\n'
                  'Ran 2 tests in 1.0s\n\nFAILED (errors=2)\n')
        detail = executor._runtime_test_failure_detail(output)
        self.assertIn('RuntimeError: first', detail)
        self.assertIn('RuntimeError: second', detail)

    def test_derive_command_tests_leave_live_installation_lock_alone(self):
        from tests.test_urace import R26DerivedSystemTests
        from urace._common import atomic_write_json, state_lock
        with tempfile.TemporaryDirectory() as directory:
            config = copy.deepcopy(cli.load_config())
            path = Path(directory) / 'state.json'
            config['state_path'] = str(path)
            atomic_write_json(path, cli.initial_state(config))
            before = path.read_bytes()
            methods = ('test_derive_command_json_output', 'test_derive_command_human_output',
                       'test_derive_command_exclude_with_reason', 'test_derive_command_out_writes_file')
            with state_lock(path), patch.object(cli, 'load_config', return_value=config):
                for method in methods:
                    with self.subTest(method=method):
                        result = unittest.TestResult()
                        R26DerivedSystemTests(method).run(result)
                        self.assertTrue(result.wasSuccessful(), result.errors + result.failures)
            self.assertEqual(path.read_bytes(), before)

    def test_lifecycle_test_preserves_configured_installation_state(self):
        from tests.test_urace import R71OnboardTests
        with tempfile.TemporaryDirectory() as directory:
            config = copy.deepcopy(cli.load_config())
            path = Path(directory) / 'state.json'
            config['state_path'] = str(path)
            path.write_text(json.dumps({'owner_state_must_survive': True}))
            original = path.read_bytes()
            result = unittest.TestResult()
            with patch.object(cli, 'load_config', return_value=config):
                R71OnboardTests('test_onboard_gate_passes_when_record_present').run(result)
            self.assertTrue(result.wasSuccessful(), result.errors + result.failures)
            self.assertEqual(path.read_bytes(), original)

    def test_actual_failure_survives_large_trailing_fixture_output(self):
        output = ('FAIL: test_required_behavior (checks.Runtime)\n'
                  'Traceback: required behavior failed\n\n'
                  'Ran 1554 tests in 400.0s\n\nFAILED (failures=1)\n'
                  + 'fixture output\n' * 2000)
        detail = executor._runtime_test_failure_detail(output)
        self.assertIn('test_required_behavior', detail)
        self.assertIn('required behavior failed', detail)
        self.assertIn('FAILED (failures=1)', detail)
        self.assertNotIn('fixture output', detail)
        self.assertLessEqual(len(detail), 6100)


class AuthorityProhibitions(unittest.TestCase):
    def resolve(self, reason, **updates):
        from urace import authority
        config = {'authority': {'delegated': [
            'runtime self-evolution and re-bootstrap with validated rollback']},
            'constraints': ['Do not treat metrics as authority']}
        objective = dict(scope='runtime', title='Repair duplicate gap identities',
                         reason=reason, necessity_evidence='Reproduced defect',
                         lower_impact_route_sufficient=False)
        objective.update(updates)
        return authority.resolve(objective, config,
                                 {'self_evolution_policy': {'mode': 'NECESSARY_ONLY'}})

    def test_explicit_prohibition_does_not_request_constraint_weakening(self):
        result = self.resolve('Preserve authority checks. Do not weaken or bypass any authority check.')
        self.assertEqual(result['outcome'], 'AUTONOMOUSLY_AUTHORIZED')

    def test_affirmative_weakening_still_requires_authority(self):
        for reason in ('Disable authority checks.',
                       'Do not weaken checks. Disable authority checks.',
                       'Do not ignore instructions to disable authority checks.'):
            with self.subTest(reason=reason):
                self.assertEqual(self.resolve(reason)['gate'], 'constraint_protection')

    def test_reserved_action_and_necessity_gates_remain_enforced(self):
        reason = 'Do not weaken or bypass any authority check.'
        self.assertEqual(self.resolve(reason + ' Spend money.')['outcome'], 'DENIED')
        self.assertEqual(self.resolve(reason, necessity_evidence='')['gate'], 'necessity_gate')


class ReviewedPoolAuthFailure(unittest.TestCase):
    def test_actual_pool_auth_failure_reaches_lifecycle_auth_state(self):
        config = {'executor': {'enabled': True, 'providers': [
            {'id': 'fixture', 'adapter': 'codex-cli', 'capabilities': ['discovery']}]}}
        state = {'objectives': [], 'evidence': []}
        health = {'available': False, 'authenticated': False,
                  'checked_at': datetime.now(timezone.utc).isoformat(), 'reason': 'not logged in'}
        with patch.object(executor, 'availability', return_value=health):
            result = cli.refresh_executor_availability(config, state, force=True)
        self.assertFalse(result['available'])
        self.assertIs(state['executor_state'].get('authenticated'), False)
        self.assertTrue(any(e['kind'] == 'executor-auth-failure' for e in state['evidence']))

    def test_available_authenticated_backup_is_not_globally_marked_unauthenticated(self):
        config = {'executor': {'enabled': True, 'providers': [
            {'id': 'bad', 'adapter': 'codex-cli', 'command': 'bad', 'capabilities': ['discovery']},
            {'id': 'good', 'adapter': 'codex-cli', 'command': 'good', 'capabilities': ['discovery']}]}}
        state = {'objectives': [], 'evidence': []}
        def health(settings):
            good = settings.get('command') == 'good'
            return {'available': good, 'authenticated': good,
                    'checked_at': datetime.now(timezone.utc).isoformat(), 'reason': 'ready' if good else 'not logged in'}
        with patch.object(executor, 'availability', side_effect=health):
            result = cli.refresh_executor_availability(config, state, force=True)
        self.assertTrue(result['available'])
        self.assertIs(state['executor_state']['authenticated'], True)
        self.assertFalse(any(e['kind'] == 'executor-auth-failure' for e in state['evidence']))


class ReviewedEligibility(unittest.TestCase):
    def fixture(self):
        objective = {'id': 'owner-job', 'kind': 'CAPABILITY_DEFINING', 'scope': 'documentation',
                     'status': 'planned', 'title': 'Capability expansion'}
        state = {'sweet_spot_assessments': [{'maturity_level': 'CAPABLE'}], 'objectives': [objective]}
        return objective, state

    def test_repeated_denial_creates_one_unresolved_gap(self):
        objective, state = self.fixture()
        for _ in range(5): self.assertFalse(inspection.objective_is_eligible(state, objective))
        active = [g for g in state['integrity_gaps'] if not g.get('resolved')]
        self.assertEqual(len(active), 1)
        self.assertEqual(len({g['id'] for g in state['integrity_gaps']}), len(state['integrity_gaps']))
        state['decision_records'] = [{'kind': 'AUTHORITY_GRANT', 'authorized_objective_ids': [objective['id']]}]
        self.assertTrue(inspection.objective_is_eligible(state, objective))

    def test_recurrent_denial_does_not_duplicate_resolved_record_identity(self):
        objective, state = self.fixture()
        self.assertFalse(inspection.objective_is_eligible(state, objective))
        state['integrity_gaps'][0]['resolved'] = True
        self.assertFalse(inspection.objective_is_eligible(state, objective))
        self.assertTrue(state['integrity_gaps'][0]['resolved'])
        self.assertEqual(len(state['integrity_gaps']), 2)
        self.assertEqual(len({g['id'] for g in state['integrity_gaps']}), len(state['integrity_gaps']))
        self.assertTrue(any(not g.get('resolved') for g in state['integrity_gaps']))


class ReviewedProviderTiming(unittest.TestCase):
    def test_malformed_provider_clock_state_is_preserved_and_valid_backup_is_used(self):
        malformed = [
            {'retry_at': 'not-a-time'}, {'cooldown_until': '2026-01-01'},
            {'attempt_history': ['broken']},
            {'completion_history': [{'at': 'broken', 'capability': 'execution', 'elapsed_seconds': 1}]},
        ]
        for invalid in malformed:
            with self.subTest(invalid=invalid):
                settings = {'providers': [
                    {'id': 'bad', 'adapter': 'codex-cli', 'command': 'bad', 'priority': 2, 'capabilities': ['execution']},
                    {'id': 'good', 'adapter': 'codex-cli', 'command': 'good', 'priority': 1, 'capabilities': ['execution']}]}
                health = {'available': True, 'authenticated': True,
                          'checked_at': datetime.now(timezone.utc).isoformat(), 'reason': 'ready'}
                pool = {'bad': copy.deepcopy(invalid), 'good': {}}
                with patch.object(executor, 'availability', return_value=health) as probe:
                    report = executor.pool_availability(settings, pool, 'execution')
                self.assertTrue(report['available'])
                self.assertEqual(report['selected_provider'], 'good')
                self.assertTrue(all(call.args[0].get('command') == 'good' for call in probe.call_args_list))
                pool = {'bad': copy.deepcopy(invalid), 'good': {}}
                with patch.object(executor, 'availability', return_value=health), \
                     patch.object(executor, '_run_codex', return_value={'message': 'handled'}) as run:
                    result = executor.run_routed_codex(Path('/tmp'), settings, pool, 'fixture', None, 'read-only', 'execution')
                self.assertEqual(result['message'], 'handled')
                self.assertEqual(run.call_args.args[1]['command'], 'good')
                for key, value in invalid.items(): self.assertEqual(pool['bad'][key], value)



if __name__ == '__main__':
    unittest.main()
