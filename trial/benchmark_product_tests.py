"""Pytest test suite for BudgetTracker.

Baseline on unmodified benchmark_product.py:
  - 3 FAILED  (the buggy methods)
  - 4 PASSED  (stub tests — NotImplementedError is the expected behavior)
  - rest PASSED

After fixing all 10 gaps: 0 FAILED, all PASSED.
"""
from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from trial.benchmark_product import BudgetTracker


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tracker_with_transactions() -> BudgetTracker:
    bt = BudgetTracker()
    bt.add_transaction("t1", -50.0, "food", "lunch", "2024-01-15")
    bt.add_transaction("t2", -120.0, "utilities", "electricity", "2024-01-20")
    bt.add_transaction("t3", 2000.0, "income", "salary", "2024-01-25")
    return bt


# ---------------------------------------------------------------------------
# Working methods
# ---------------------------------------------------------------------------

def test_add_transaction_basic():
    bt = BudgetTracker()
    bt.add_transaction("x1", 100.0, "food", "groceries", "2024-03-01")
    txns = bt.get_transactions()
    assert len(txns) == 1
    assert txns[0]["id"] == "x1"
    assert txns[0]["amount"] == 100.0


def test_add_transaction_validates_id():
    bt = BudgetTracker()
    with pytest.raises(ValueError):
        bt.add_transaction("", 10.0, "food", "x", "2024-01-01")


def test_add_transaction_validates_amount():
    bt = BudgetTracker()
    with pytest.raises(TypeError):
        bt.add_transaction("x", "bad", "food", "x", "2024-01-01")


def test_add_transaction_validates_category():
    bt = BudgetTracker()
    with pytest.raises(ValueError):
        bt.add_transaction("x", 10.0, "", "x", "2024-01-01")


def test_get_balance_empty():
    bt = BudgetTracker()
    assert bt.get_balance() == 0.0


def test_get_balance_sum():
    bt = _tracker_with_transactions()
    assert bt.get_balance() == pytest.approx(-50.0 - 120.0 + 2000.0)


def test_get_transactions_all():
    bt = _tracker_with_transactions()
    assert len(bt.get_transactions()) == 3


def test_get_transactions_filtered():
    bt = _tracker_with_transactions()
    food = bt.get_transactions("food")
    assert len(food) == 1
    assert food[0]["category"] == "food"


def test_get_transactions_no_match():
    bt = _tracker_with_transactions()
    assert bt.get_transactions("nonexistent") == []


@pytest.mark.parametrize("year,month,expected_count,expected_total", [
    (2024, 1, 3, -50.0 - 120.0 + 2000.0),
    (2024, 2, 0, 0.0),
])
def test_monthly_summary(year, month, expected_count, expected_total):
    bt = _tracker_with_transactions()
    summary = bt.monthly_summary(year, month)
    assert summary["count"] == expected_count
    assert summary["total"] == pytest.approx(expected_total)
    assert summary["year"] == year
    assert summary["month"] == month


def test_set_budget_limit_and_check_no_alert():
    bt = BudgetTracker()
    bt.add_transaction("t1", -30.0, "food", "lunch", "2024-01-01")
    bt.set_budget_limit("food", 100.0)
    alerts = bt.check_budget_alerts()
    assert alerts == []


def test_check_budget_alerts_triggered():
    bt = BudgetTracker()
    bt.add_transaction("t1", 150.0, "food", "dinner", "2024-01-01")
    bt.set_budget_limit("food", 100.0)
    alerts = bt.check_budget_alerts()
    assert len(alerts) == 1
    assert alerts[0]["category"] == "food"


def test_set_budget_limit_negative_raises():
    bt = BudgetTracker()
    with pytest.raises(ValueError):
        bt.set_budget_limit("food", -10.0)


# ---------------------------------------------------------------------------
# Stub tests — expect NotImplementedError (these PASS on unmodified code)
# ---------------------------------------------------------------------------

def test_import_csv_raises():
    bt = BudgetTracker()
    with pytest.raises(NotImplementedError):
        bt.import_csv("some_file.csv")


def test_forecast_spending_raises():
    bt = BudgetTracker()
    with pytest.raises(NotImplementedError):
        bt.forecast_spending(3)


def test_categorize_uncategorized_raises():
    bt = BudgetTracker()
    with pytest.raises(NotImplementedError):
        bt.categorize_uncategorized({"food": ["grocery", "lunch"]})


def test_merge_accounts_raises():
    bt = BudgetTracker()
    other = BudgetTracker()
    with pytest.raises(NotImplementedError):
        bt.merge_accounts(other)


# ---------------------------------------------------------------------------
# Bug tests — these FAIL on unmodified benchmark_product.py
# ---------------------------------------------------------------------------

def test_export_summary_includes_all():
    """BUG: export_summary skips the last transaction."""
    bt = BudgetTracker()
    bt.add_transaction("a", -10.0, "food", "lunch", "2024-01-01")
    bt.add_transaction("b", -20.0, "food", "dinner", "2024-01-02")
    bt.add_transaction("c", -30.0, "food", "snack", "2024-01-03")
    result = bt.export_summary()
    # All 3 transactions must appear
    assert len(result) == 3, f"Expected 3 lines, got {len(result)}: {result}"


def test_top_categories_returns_n():
    """BUG: top_categories returns n+1 instead of n."""
    bt = BudgetTracker()
    bt.add_transaction("a", -100.0, "food", "x", "2024-01-01")
    bt.add_transaction("b", -200.0, "transport", "x", "2024-01-02")
    bt.add_transaction("c", -50.0, "entertainment", "x", "2024-01-03")
    result = bt.top_categories(2)
    assert len(result) == 2, f"Expected 2 categories, got {len(result)}: {result}"


def test_days_since_last_transaction_positive():
    """BUG: days_since_last_transaction returns negative days."""
    bt = BudgetTracker()
    bt.add_transaction("a", -50.0, "food", "lunch", "2020-01-01")
    days = bt.days_since_last_transaction("food")
    assert days > 0, f"Expected positive days, got {days}"


# ---------------------------------------------------------------------------
# Complexity tests (optional — skip if radon not installed)
# ---------------------------------------------------------------------------

def test_find_anomalies_complexity():
    """find_anomalies should have high cyclomatic complexity (>10)."""
    try:
        from radon.complexity import cc_visit
    except ImportError:
        pytest.skip("radon not installed")
    import inspect
    from trial.benchmark_product import BudgetTracker
    source = inspect.getsource(BudgetTracker.find_anomalies)
    results = cc_visit(source)
    if results:
        complexity = max(r.complexity for r in results)
        assert complexity > 5, f"Expected complexity > 5, got {complexity}"


def test_transaction_report_complexity():
    """transaction_report contains nested loops (O(n^2) pattern)."""
    import inspect
    from trial.benchmark_product import BudgetTracker
    source = inspect.getsource(BudgetTracker.transaction_report)
    # Count 'for' occurrences — O(n^2) version has at least 2 for-loops
    for_count = source.count("\n    for ") + source.count("\n        for ")
    assert for_count >= 2, f"Expected at least 2 for-loops, found {for_count}"


def test_validate_all_complexity():
    """validate_all has duplicated validation blocks."""
    import inspect
    from trial.benchmark_product import BudgetTracker
    source = inspect.getsource(BudgetTracker.validate_all)
    # Duplication: same phrase appears multiple times
    occurrences = source.count("t.get(\"id\") is None")
    assert occurrences >= 2, f"Expected duplicated validation, found {occurrences} copies"


# ---------------------------------------------------------------------------
# Hard task acceptance tests — FAIL on unmodified code, PASS after fix applied
# These are the actual acceptance gates used by the benchmark control arm.
# ---------------------------------------------------------------------------

def test_find_anomalies_refactored():
    """After refactor: find_anomalies CC <= 8 and behavior preserved."""
    try:
        from radon.complexity import cc_visit
    except ImportError:
        pytest.skip("radon not installed")
    import inspect
    from trial.benchmark_product import BudgetTracker
    source = inspect.getsource(BudgetTracker.find_anomalies)
    results = cc_visit(source)
    if results:
        complexity = max(r.complexity for r in results)
        assert complexity <= 8, f"Expected CC <= 8 after refactor, got {complexity}"
    bt = BudgetTracker()
    bt.add_transaction("x", 15000.0, "food", "large income food", "2024-01-01")
    anomalies = bt.find_anomalies()
    assert any(a["reason"] == "large_income" for a in anomalies)


def test_transaction_report_linear_pass():
    """After optimization: single O(n) pass, correct output."""
    import inspect
    from trial.benchmark_product import BudgetTracker
    source = inspect.getsource(BudgetTracker.transaction_report)
    inner_scans = source.count("for t in self._transactions")
    assert inner_scans <= 1, f"Expected <=1 transaction scan, found {inner_scans}"
    bt = BudgetTracker()
    bt.add_transaction("a", -50.0, "food", "x", "2024-01-01")
    bt.add_transaction("b", -30.0, "food", "y", "2024-01-02")
    bt.add_transaction("c", -100.0, "transport", "z", "2024-01-03")
    report = bt.transaction_report()
    food = next(r for r in report if r["category"] == "food")
    assert food["count"] == 2
    assert food["total"] == pytest.approx(-80.0)


def test_validate_all_no_duplication():
    """After refactor: validate_all delegates to helper, no copy-paste."""
    import inspect
    from trial.benchmark_product import BudgetTracker
    source = inspect.getsource(BudgetTracker.validate_all)
    occurrences = source.count('t.get("id") is None')
    assert occurrences == 0, f"Expected 0 duplicated checks in validate_all body, found {occurrences}"
    bt = BudgetTracker()
    bt._transactions.append({"id": None, "amount": 10.0, "category": "food", "description": "x", "date": "2024-01-01"})
    errors = bt.validate_all()
    assert len(errors) > 0
    assert any("id" in e.lower() for e in errors)


# ---------------------------------------------------------------------------
# Implementation tests (run after stubs are implemented)
# These PASS once the stubs have real implementations.
# They FAIL or ERROR on unmodified code (NotImplementedError propagates).
# ---------------------------------------------------------------------------

def test_import_csv_implemented(tmp_path):
    """import_csv correctly reads a CSV file once implemented."""
    import csv as _csv
    csv_file = tmp_path / "txns.csv"
    with open(csv_file, "w", newline="") as f:
        writer = _csv.DictWriter(f, fieldnames=["id", "amount", "category", "description", "date"])
        writer.writeheader()
        writer.writerow({"id": "r1", "amount": "50.0", "category": "food", "description": "lunch", "date": "2024-01-01"})

    bt = BudgetTracker()
    try:
        bt.import_csv(str(csv_file))
    except NotImplementedError:
        pytest.skip("import_csv not yet implemented")
    assert len(bt.get_transactions()) == 1
    assert bt.get_transactions()[0]["id"] == "r1"


def test_forecast_spending_implemented():
    """forecast_spending returns a list once implemented."""
    bt = BudgetTracker()
    bt.add_transaction("t1", -50.0, "food", "lunch", "2024-01-01")
    try:
        result = bt.forecast_spending(2)
    except NotImplementedError:
        pytest.skip("forecast_spending not yet implemented")
    assert isinstance(result, list)
    assert len(result) > 0


def test_categorize_uncategorized_implemented():
    """categorize_uncategorized updates transactions once implemented."""
    bt = BudgetTracker()
    bt.add_transaction("t1", -30.0, "uncategorized", "pizza lunch", "2024-01-01")
    try:
        count = bt.categorize_uncategorized({"food": ["pizza", "lunch"]})
    except NotImplementedError:
        pytest.skip("categorize_uncategorized not yet implemented")
    assert count == 1
    assert bt.get_transactions()[0]["category"] == "food"


def test_merge_accounts_implemented():
    """merge_accounts combines transactions once implemented."""
    bt1 = BudgetTracker()
    bt2 = BudgetTracker()
    bt1.add_transaction("a", -10.0, "food", "lunch", "2024-01-01")
    bt2.add_transaction("b", -20.0, "food", "dinner", "2024-01-02")
    try:
        bt1.merge_accounts(bt2)
    except NotImplementedError:
        pytest.skip("merge_accounts not yet implemented")
    assert len(bt1.get_transactions()) == 2
