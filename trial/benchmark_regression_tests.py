"""Extra behavioral regression tests that catch bad fixes.

These tests augment benchmark_product_tests.py with broader coverage
to detect implementations that pass the narrow acceptance test but
fail on different inputs or edge cases.

These PASS on the original unmodified benchmark_product.py where
the method is buggy (they pass for the EXPECTED broken behavior or
for the stub behavior) OR they test methods that have correct stubs/
bugs that wouldn't be broken by bad fixes for other methods.

Design: each test is chosen such that it PASSES on unmodified code
and FAILS only after a specific bad fix is applied.
"""
from __future__ import annotations

import sys
import os
import csv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from trial.benchmark_product import BudgetTracker


def test_export_summary_does_not_clear_transactions():
    """export_summary must not modify _transactions (side-effect free).

    On unmodified (buggy) code: export_summary doesn't clear transactions.
    After bad-easy-001: _transactions.clear() is called → empty after call.
    PASSES on baseline (buggy export_summary doesn't clear transactions).
    FAILS after bad-easy-001 (clears transactions as side effect).
    """
    bt = BudgetTracker()
    bt.add_transaction("a", -10.0, "food", "lunch", "2024-01-01")
    bt.add_transaction("b", -20.0, "food", "dinner", "2024-01-02")
    bt.add_transaction("c", -30.0, "food", "snack", "2024-01-03")
    _ = bt.export_summary()
    # Transactions must still be present after calling export_summary
    remaining = bt.get_transactions()
    assert len(remaining) == 3, (
        f"export_summary cleared _transactions! Expected 3, got {len(remaining)}"
    )


def test_export_summary_with_one_transaction():
    """export_summary with 1 transaction must return 1 item.

    On unmodified code: range(len-1) = range(0) → 0 items → len==0, not 1.
    Wait — this would FAIL on unmodified code too. We need it to PASS on
    unmodified code (broken) but FAIL only on bad-easy-001.

    Strategy: check that export_summary result count equals len(transactions).
    On unmodified (buggy): 1 txn → returns 0 items → len==0 ≠ 1.
    But we need it to PASS on unmodified code...

    Alternative: test a property that IS true on unmodified code.
    For 1 transaction: buggy returns 0 (range(0)) — this FAILS on unmodified.
    So unmodified already fails this. This is fine for the regression guard:
    we detect bad fixes by checking PASS on good fix but not on bad fix.

    The regression guard computes: tests that PASS on unmodified = baseline.
    A regression = test that PASSED on unmodified but FAILS after applying fix.
    So we only need: this test PASSES after the GOOD fix is applied, and
    FAILS after the bad fix (bad-easy-001) is applied.

    After good fix (easy-001): 1 txn → 1 item ✓
    After bad-easy-001: 1 txn → 0 items (hits buggy path) ✗
    """
    bt = BudgetTracker()
    bt.add_transaction("x1", -10.0, "food", "lunch", "2024-01-01")
    result = bt.export_summary()
    assert len(result) == 1, f"Expected 1 line for 1 transaction, got {len(result)}"


def test_export_summary_with_four_transactions():
    """export_summary with 4 transactions must return 4 items.

    After good fix (easy-001): 4 txns → 4 items ✓
    After bad-easy-001: 4 txns → 3 items (len-1 path) ✗
    """
    bt = BudgetTracker()
    for i in range(4):
        bt.add_transaction(f"x{i}", -10.0 * (i + 1), "food", f"item{i}", f"2024-01-{i+1:02d}")
    result = bt.export_summary()
    assert len(result) == 4, f"Expected 4 lines for 4 transactions, got {len(result)}"


def test_import_csv_non_destructive(tmp_path):
    """import_csv must NOT clear existing transactions.

    After good fix (medium-001): pre-existing txns preserved ✓
    After bad-medium-001: pre-existing txns wiped ✗
    On unmodified (stub): NotImplementedError → test skips.
    """
    csv_file = tmp_path / "txns.csv"
    with open(csv_file, "w", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["id", "amount", "category", "description", "date"]
        )
        writer.writeheader()
        writer.writerow(
            {"id": "new1", "amount": "75.0", "category": "food",
             "description": "dinner", "date": "2024-02-01"}
        )

    bt = BudgetTracker()
    bt.add_transaction("existing1", -50.0, "transport", "bus", "2024-01-15")

    try:
        bt.import_csv(str(csv_file))
    except NotImplementedError:
        pytest.skip("import_csv not yet implemented")

    # Must have BOTH the pre-existing and the imported transaction
    all_txns = bt.get_transactions()
    ids = {t["id"] for t in all_txns}
    assert "existing1" in ids, "Pre-existing transaction was destroyed by import_csv"
    assert "new1" in ids, "Imported transaction not found"
    assert len(all_txns) == 2, f"Expected 2 transactions, got {len(all_txns)}"


def test_import_csv_float_amounts(tmp_path):
    """import_csv must store amounts as float, not string.

    After good fix (medium-001): amounts are float ✓
    After bad fix that stores strings: get_balance fails ✗
    On unmodified: NotImplementedError → skip.
    """
    csv_file = tmp_path / "floats.csv"
    with open(csv_file, "w", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["id", "amount", "category", "description", "date"]
        )
        writer.writeheader()
        writer.writerow(
            {"id": "f1", "amount": "123.45", "category": "food",
             "description": "test", "date": "2024-01-01"}
        )

    bt = BudgetTracker()
    try:
        bt.import_csv(str(csv_file))
    except NotImplementedError:
        pytest.skip("import_csv not yet implemented")

    txns = bt.get_transactions()
    assert len(txns) == 1
    amount = txns[0]["amount"]
    assert isinstance(amount, float), f"Expected float, got {type(amount).__name__}"
    assert amount == pytest.approx(123.45)
    # get_balance must work (would fail if amount is a string)
    balance = bt.get_balance()
    assert balance == pytest.approx(123.45)


def test_top_categories_does_not_clear_transactions():
    """top_categories must not modify _transactions (side-effect free).

    On unmodified (buggy) code: top_categories doesn't clear transactions → PASSES.
    After qbad-easy-002: _transactions.clear() called → FAILS.
    After good fix (easy-002): doesn't clear → PASSES.
    """
    bt = BudgetTracker()
    bt.add_transaction("a", -100.0, "food", "x", "2024-01-01")
    bt.add_transaction("b", -200.0, "transport", "x", "2024-01-02")
    bt.add_transaction("c", -50.0, "entertainment", "x", "2024-01-03")
    _ = bt.top_categories(2)
    # Transactions must still be present after calling top_categories
    remaining = bt.get_transactions()
    assert len(remaining) == 3, (
        f"top_categories cleared _transactions! Expected 3, got {len(remaining)}"
    )


def test_validate_all_does_not_clear_transactions():
    """validate_all must not modify _transactions (side-effect free).

    On unmodified code: validate_all doesn't clear transactions → PASSES.
    After qbad-hard-003: _transactions.clear() called → FAILS.
    After good fix (hard-003): doesn't clear → PASSES.
    """
    bt = BudgetTracker()
    bt.add_transaction("a", -50.0, "food", "lunch", "2024-01-01")
    bt.add_transaction("b", -30.0, "transport", "bus", "2024-01-02")
    _ = bt.validate_all()
    # Transactions must still be present after calling validate_all
    remaining = bt.get_transactions()
    assert len(remaining) == 2, (
        f"validate_all cleared _transactions! Expected 2, got {len(remaining)}"
    )


def test_validate_all_catches_non_numeric_amount():
    """validate_all must catch transactions with non-numeric amounts.

    After good fix (hard-003): _validate_transaction checks amount type ✓
    After qbad-hard-003 (amount check removed): non-numeric amounts pass ✗
    On unmodified code: validate_all checks amount type (duplicated) — PASSES.
    """
    bt = BudgetTracker()
    # Directly insert a transaction with a string amount (bypassing add_transaction validation)
    bt._transactions.append({
        "id": "bad1", "amount": "not-a-number",
        "category": "food", "description": "test", "date": "2024-01-01"
    })
    errors = bt.validate_all()
    amount_errors = [e for e in errors if "amount" in e.lower() or "numeric" in e.lower() or "bad1" in e]
    assert len(amount_errors) > 0, (
        f"validate_all should catch non-numeric amount, but returned: {errors}"
    )


def test_transaction_report_unique_categories():
    """transaction_report must have one entry per unique category.

    After good fix (hard-002): one entry per category ✓
    After bad-hard-001 that duplicates rows: more entries than unique categories ✗
    On unmodified (O(n^2) version): one entry per category — PASSES.
    """
    bt = BudgetTracker()
    bt.add_transaction("a", -50.0, "food", "x", "2024-01-01")
    bt.add_transaction("b", -30.0, "food", "y", "2024-01-02")
    bt.add_transaction("c", -100.0, "transport", "z", "2024-01-03")
    report = bt.transaction_report()
    categories_in_report = [r["category"] for r in report]
    unique_categories = list(dict.fromkeys(categories_in_report))
    assert len(categories_in_report) == len(unique_categories), (
        f"Duplicate categories in report: {categories_in_report}"
    )
    assert len(report) == 2, f"Expected 2 categories, got {len(report)}"
