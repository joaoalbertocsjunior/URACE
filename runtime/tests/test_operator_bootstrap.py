"""Independent synthetic controls for an operator-controlled cold bootstrap.

These tests do not authorize ordinary candidates to modify the protected kernel.
"""
from pathlib import Path
import json
import os
import subprocess
import tempfile
import types
import unittest
from unittest.mock import patch

from urace import launcher, evolution_guard

# The accepted-test harness suppresses launcher recursion after discovery.
# Retain the real protected entry point so its budget is still tested.
_REAL_VALIDATE_ACTIVATION = launcher.validate_activation_candidate


class OperatorKernelBootstrap(unittest.TestCase):
    def test_activation_uses_complete_suite_validation_budget(self):
        with patch.object(evolution_guard, 'validate_candidate', return_value=[]) as validate:
            self.assertEqual(_REAL_VALIDATE_ACTIVATION(), [])
        self.assertEqual(validate.call_args.kwargs.get('timeout'), 900)
        self.assertEqual(validate.call_args.kwargs['expected_kernel_hashes'], launcher.EXPECTED_KERNEL_HASHES)

    def test_budget_check_survives_accepted_guard_harness(self):
        result = unittest.TestResult()
        with patch.object(launcher, 'validate_activation_candidate', return_value=[]):
            type(self)('test_activation_uses_complete_suite_validation_budget').run(result)
        self.assertTrue(result.wasSuccessful(), repr(result.errors + result.failures))

    def assert_guard_failure_restores_stable(self, error):
        results = [types.SimpleNamespace(returncode=75), types.SimpleNamespace(returncode=0)]
        with patch.dict(os.environ, {'URACE_LAUNCHER_CHILD': '0'}), \
             patch.object(launcher.sys, 'argv', ['urace', 'auto', '--cycles', '1']), \
             patch.object(launcher.subprocess, 'run', side_effect=results) as run, \
             patch.object(launcher, 'validate_activation_candidate', side_effect=error), \
             patch.object(launcher, 'restore_stable_runtime') as restore:
            self.assertEqual(launcher.main(), 0)
        restore.assert_called_once()
        self.assertIn(type(error).__name__, restore.call_args.args[0])
        self.assertEqual(run.call_count, 2)
        self.assertNotIn('URACE_POST_UPGRADE', run.call_args_list[1].kwargs['env'])

    def test_activation_guard_timeout_restores_stable(self):
        self.assert_guard_failure_restores_stable(subprocess.TimeoutExpired(['synthetic-validator'], 900))

    def test_activation_guard_exception_restores_stable(self):
        self.assert_guard_failure_restores_stable(ValueError('synthetic validator failure'))

    def test_operator_cancellation_is_not_suppressed(self):
        with patch.dict(os.environ, {'URACE_LAUNCHER_CHILD': '0'}), \
             patch.object(launcher.subprocess, 'run', return_value=types.SimpleNamespace(returncode=75)), \
             patch.object(launcher, 'validate_activation_candidate', side_effect=KeyboardInterrupt), \
             patch.object(launcher, 'restore_stable_runtime') as restore:
            with self.assertRaises(KeyboardInterrupt):
                launcher.main()
        restore.assert_not_called()

    def test_ordinary_candidate_kernel_change_is_still_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            product = Path(directory)/'accepted'
            candidate = Path(directory)/'candidate'
            for root in (product, candidate):
                for relative in evolution_guard.PROTECTED_FILES:
                    p = root/relative;p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_text('accepted fixture '+relative)
                p = root/'urace/runtime/urace/config.json'
                p.write_text(json.dumps({'authority': {}, 'constraints': [],
                    'self_evolution_policy': {}, 'executor': {'max_executor_calls_per_24h': 4,
                    'max_executor_calls_per_30d': 20, 'allowed_files_by_scope': {'runtime': ['urace/runtime/urace/cli.py']}}}))
            expected = evolution_guard.kernel_hashes(product)
            (candidate/'urace/runtime/urace/launcher.py').write_text('unauthorized fixture change')
            stable = product/'urace/state/stable-runtime'
            (stable/'urace/runtime/tests').mkdir(parents=True)
            with patch.object(evolution_guard.subprocess, 'run', side_effect=AssertionError('must reject before executing candidate')):
                errors = evolution_guard.validate_candidate(product, candidate, stable, expected_kernel_hashes=expected)
            self.assertIn('protected evolution-kernel file changed: urace/runtime/urace/launcher.py', errors)


if __name__ == '__main__':
    unittest.main()
