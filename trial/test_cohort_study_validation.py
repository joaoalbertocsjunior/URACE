"""Validate matched cohort study infrastructure is ready for runtime improvement tracking."""
import json, sys, unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import BASE
import downstream_study as ds


class TestStudySettings(unittest.TestCase):
    def test_study_enabled(self):
        settings_path = BASE / 'repository-study-settings.json'
        if not settings_path.exists():
            self.skipTest('Study settings not yet initialized')
        settings = json.loads(settings_path.read_text())
        self.assertTrue(settings.get('enabled'), 'Matched cohort study must be enabled')

    def test_study_repetitions_configured(self):
        settings_path = BASE / 'repository-study-settings.json'
        if not settings_path.exists():
            self.skipTest('Study settings not yet initialized')
        settings = json.loads(settings_path.read_text())
        reps = settings.get('repetitions', 0)
        self.assertGreater(reps, 0, 'Study must have at least 1 repetition configured')

    def test_study_efforts_configured(self):
        settings_path = BASE / 'repository-study-settings.json'
        if not settings_path.exists():
            self.skipTest('Study settings not yet initialized')
        settings = json.loads(settings_path.read_text())
        efforts = settings.get('efforts', [])
        self.assertGreater(len(efforts), 0, 'Study must have at least one effort level')


class TestStudyStatusInfrastructure(unittest.TestCase):
    def test_status_returns_both_lanes(self):
        result = ds.status()
        self.assertIn('context', result)
        self.assertIn('specification', result)

    def test_status_no_exception(self):
        try:
            ds.status()
        except Exception as e:
            self.fail(f'status() raised {e}')

    def test_status_lanes_have_status_field(self):
        result = ds.status()
        for lane, data in result.items():
            self.assertIn('status', data, f'Lane {lane} missing status field')


class TestStudyPlanInfrastructure(unittest.TestCase):
    def test_families_defined(self):
        from repository_tasks import FAMILIES
        self.assertGreater(len(FAMILIES), 0)

    def test_contract_callable_for_all_families(self):
        from repository_tasks import FAMILIES, contract
        for family in FAMILIES:
            try:
                c = contract(family)
                self.assertIsNotNone(c)
            except Exception as e:
                self.fail(f'contract({family!r}) raised: {e}')

    def test_downstream_study_importable(self):
        import downstream_study
        self.assertTrue(hasattr(downstream_study, 'plan'))
        self.assertTrue(hasattr(downstream_study, 'status'))
        self.assertTrue(hasattr(downstream_study, 'run_one'))
        self.assertTrue(hasattr(downstream_study, 'step'))


class TestRuntimeProductStudyIntegration(unittest.TestCase):
    """Verify the runtime product is registered and visible to study infrastructure."""

    def test_runtime_product_in_products_json(self):
        products_path = BASE / 'products.json'
        if not products_path.exists():
            self.skipTest('products.json not yet initialized')
        data = json.loads(products_path.read_text())
        # products.json may be a list or {products: [...]}
        products = data if isinstance(data, list) else data.get('products', [])
        runtime_ids = [p.get('id', '') for p in products if isinstance(p, dict) and p.get('kind') == 'runtime']
        self.assertGreater(len(runtime_ids), 0,
                           'At least one runtime product must be registered in products.json')

    def test_runtime_workflow_config_present(self):
        config_path = BASE.parent / 'runtime' / 'urace' / 'config.json'
        if not config_path.exists():
            self.skipTest('config.json not found')
        config = json.loads(config_path.read_text())
        self.assertIn('runtime_workflow', config,
                      'runtime_workflow section must be in config.json')
        self.assertTrue(config['runtime_workflow'].get('enabled'),
                        'runtime_workflow.enabled must be true')

    def test_runtime_snapshot_module_importable(self):
        import runtime_snapshot
        self.assertTrue(hasattr(runtime_snapshot, 'create'))
        self.assertTrue(hasattr(runtime_snapshot, 'planning_context'))

    def test_runtime_trial_module_importable(self):
        import runtime_trial
        self.assertTrue(hasattr(runtime_trial, 'run'))
        self.assertTrue(hasattr(runtime_trial, 'deploy'))
        self.assertTrue(hasattr(runtime_trial, 'deployment_log'))


if __name__ == '__main__':
    unittest.main()
