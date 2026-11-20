"""Autouse fixtures for trial test suite."""
from __future__ import annotations

import shutil
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


@pytest.fixture(scope="session", autouse=True)
def cleanup_session_tmp(tmp_path_factory):
    """Remove all pytest-managed tmp dirs after the full trial session."""
    yield
    root = tmp_path_factory.getbasetemp()
    shutil.rmtree(root, ignore_errors=True)
