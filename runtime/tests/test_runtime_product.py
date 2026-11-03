"""Tests for runtime_product registration and engine identity stability."""
import hashlib, json, tempfile, unittest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from urace.runtime_product import PRODUCT_ID, PRODUCT_NAME, engine_identity, registration, quality_gate


class TestProductConstants(unittest.TestCase):
    def test_product_id_format(self):
        self.assertTrue(PRODUCT_ID.startswith('urace-runtime:'))
        # Path separator is OS-specific; check case-insensitive for the install dir name
        self.assertIn('urace', PRODUCT_ID.lower())

    def test_product_name(self):
        self.assertIsInstance(PRODUCT_NAME, str)
        self.assertGreater(len(PRODUCT_NAME), 0)


class TestEngineIdentity(unittest.TestCase):
    def test_stable_for_identical_sources(self):
        h1 = engine_identity()
        h2 = engine_identity()
        self.assertEqual(h1, h2)

    def test_is_64_char_hex(self):
        h = engine_identity()
        self.assertEqual(len(h), 64)
        int(h, 16)  # must be valid hex

    def test_changes_when_file_added(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / 'a.py').write_bytes(b'x=1\n')
            h1 = engine_identity(base)
            (base / 'b.py').write_bytes(b'y=2\n')
            h2 = engine_identity(base)
            self.assertNotEqual(h1, h2)

    def test_changes_when_content_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            f = base / 'mod.py'
            f.write_bytes(b'x=1\n')
            h1 = engine_identity(base)
            f.write_bytes(b'x=2\n')
            h2 = engine_identity(base)
            self.assertNotEqual(h1, h2)

    def test_empty_directory_returns_valid_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            h = engine_identity(tmp)
            self.assertEqual(len(h), 64)


class TestRegistration(unittest.TestCase):
    def test_required_fields(self):
        r = registration()
        for key in ('id', 'name', 'source', 'kind'):
            self.assertIn(key, r)

    def test_id_matches_constant(self):
        self.assertEqual(registration()['id'], PRODUCT_ID)

    def test_kind_is_runtime(self):
        self.assertEqual(registration()['kind'], 'runtime')


class TestQualityGate(unittest.TestCase):
    def test_defaults_when_no_config(self):
        gate = quality_gate({})
        self.assertEqual(gate['metric'], 'executable_benchmark_score')
        self.assertEqual(gate['minimum_delta'], 5.0)

    def test_uses_config_when_present(self):
        cfg = {'runtime_workflow': {'quality_gate_metric': 'custom', 'quality_gate_minimum_score_delta': 10.0}}
        gate = quality_gate(cfg)
        self.assertEqual(gate['metric'], 'custom')
        self.assertEqual(gate['minimum_delta'], 10.0)

    def test_tolerates_non_dict_config(self):
        gate = quality_gate(None)
        self.assertEqual(gate['minimum_delta'], 5.0)


if __name__ == '__main__':
    unittest.main()
