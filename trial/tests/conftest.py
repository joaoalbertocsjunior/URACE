"""Autouse fixture: restore benchmark_product.py from canonical before/after each test."""
from __future__ import annotations

import pytest
from pathlib import Path

_TRIAL_DIR = Path(__file__).resolve().parent.parent
_PRODUCT_PATH = _TRIAL_DIR / "benchmark_product.py"
_CANONICAL_PATH = _TRIAL_DIR / "benchmark_product_canonical.py"


@pytest.fixture(autouse=True)
def restore_benchmark_product():
    if _CANONICAL_PATH.exists():
        canonical = _CANONICAL_PATH.read_text(encoding="utf-8")
        _PRODUCT_PATH.write_text(canonical, encoding="utf-8")
    yield
    if _CANONICAL_PATH.exists():
        canonical = _CANONICAL_PATH.read_text(encoding="utf-8")
        _PRODUCT_PATH.write_text(canonical, encoding="utf-8")
