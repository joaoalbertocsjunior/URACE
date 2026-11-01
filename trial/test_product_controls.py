"""Tests for per-product improvement enable/disable controls."""
import json
import unittest
from pathlib import Path
import tempfile, shutil


def _make_base(products):
    d = Path(tempfile.mkdtemp())
    (d / 'products.json').write_text(json.dumps({'products': products}))
    return d


def _cleanup(d):
    shutil.rmtree(str(d), ignore_errors=True)


class Tests(unittest.TestCase):
    def test_set_enabled_true(self):
        base = _make_base([{'id': 'urace-runtime:/foo', 'kind': 'runtime', 'name': 'foo'}])
        try:
            from product_controls import set_improvement_enabled, get_improvement_enabled
            set_improvement_enabled('urace-runtime:/foo', True, base)
            assert get_improvement_enabled('urace-runtime:/foo', base) is True
        finally:
            _cleanup(base)
    
    
    def test_set_enabled_false(self):
        base = _make_base([{'id': 'urace-runtime:/foo', 'kind': 'runtime', 'name': 'foo'}])
        try:
            from product_controls import set_improvement_enabled, get_improvement_enabled
            set_improvement_enabled('urace-runtime:/foo', False, base)
            assert get_improvement_enabled('urace-runtime:/foo', base) is False
        finally:
            _cleanup(base)
    
    
    def test_get_default_true(self):
        base = _make_base([{'id': 'urace-runtime:/foo', 'kind': 'runtime', 'name': 'foo'}])
        try:
            from product_controls import get_improvement_enabled
            # No improvement_enabled flag set; should default to True
            assert get_improvement_enabled('urace-runtime:/foo', base) is True
        finally:
            _cleanup(base)
    
    
    def test_missing_product_raises(self):
        base = _make_base([{'id': 'urace-runtime:/foo', 'kind': 'runtime', 'name': 'foo'}])
        try:
            from product_controls import set_improvement_enabled
            with self.assertRaises(KeyError):
                set_improvement_enabled('urace-runtime:/does-not-exist', True, base)
        finally:
            _cleanup(base)
    
    
    def test_atomic_write(self):
        base = _make_base([{'id': 'urace-runtime:/foo', 'kind': 'runtime', 'name': 'foo'}])
        try:
            from product_controls import set_improvement_enabled
            products_path = base / 'products.json'
            set_improvement_enabled('urace-runtime:/foo', False, base)
            # File must exist and be valid JSON after set
            assert products_path.exists()
            data = json.loads(products_path.read_text())
            assert isinstance(data, dict)
            assert 'products' in data
            product = next(p for p in data['products'] if p['id'] == 'urace-runtime:/foo')
            assert product['improvement_enabled'] is False
        finally:
            _cleanup(base)
