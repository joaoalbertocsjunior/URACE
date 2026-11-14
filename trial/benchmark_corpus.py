"""Benchmark corpus — 10 improvement tasks covering all 10 gaps in BudgetTracker."""
from __future__ import annotations

from pathlib import Path

BENCHMARK_TASKS = [
    # ------------------------------------------------------------------
    # Easy — 3 bugs
    # ------------------------------------------------------------------
    {
        "task_id": "easy-001",
        "difficulty": "easy",
        "title": "Fix off-by-one in export_summary",
        "input": (
            "The export_summary() method in BudgetTracker (benchmark_product.py) "
            "skips the last transaction because it iterates range(len(transactions)-1) "
            "instead of range(len(transactions)).  Fix the loop so all transactions "
            "are included in the output."
        ),
        "acceptance_criteria": "test_export_summary_includes_all passes",
        "value_rubric": "1.0 if test passes; 0.0 otherwise",
        "target_method": "export_summary",
        "gap_kind": "bug",
    },
    {
        "task_id": "easy-002",
        "difficulty": "easy",
        "title": "Fix top_categories returns n+1 items",
        "input": (
            "The top_categories(n) method returns n+1 items instead of n because "
            "the slice is sorted_cats[:n+1].  Fix it to return exactly n categories."
        ),
        "acceptance_criteria": "test_top_categories_returns_n passes",
        "value_rubric": "1.0 if test passes; 0.0 otherwise",
        "target_method": "top_categories",
        "gap_kind": "bug",
    },
    {
        "task_id": "easy-003",
        "difficulty": "easy",
        "title": "Fix days_since_last_transaction returns negative value",
        "input": (
            "The days_since_last_transaction(category) method returns a negative "
            "number because it computes (last_date - today) instead of (today - last_date). "
            "Fix the sign so the method returns a positive number of days elapsed."
        ),
        "acceptance_criteria": "test_days_since_last_transaction_positive passes",
        "value_rubric": "1.0 if test passes; 0.0 otherwise",
        "target_method": "days_since_last_transaction",
        "gap_kind": "bug",
    },
    # ------------------------------------------------------------------
    # Medium — 4 stubs
    # ------------------------------------------------------------------
    {
        "task_id": "medium-001",
        "difficulty": "medium",
        "title": "Implement import_csv",
        "input": (
            "Implement the import_csv(filepath) method on BudgetTracker.  "
            "It should read a CSV file whose columns are: id, amount, category, "
            "description, date.  Call self.add_transaction() for each row.  "
            "Skip the header row.  Raise ValueError if any required column is missing."
        ),
        "acceptance_criteria": "test_import_csv_implemented passes",
        "value_rubric": "1.0 if import_csv no longer raises NotImplementedError and correctly imports transactions; 0.0 otherwise",
        "target_method": "import_csv",
        "gap_kind": "stub",
    },
    {
        "task_id": "medium-002",
        "difficulty": "medium",
        "title": "Implement forecast_spending",
        "input": (
            "Implement the forecast_spending(months_ahead) method.  "
            "Compute the average monthly spending per category from historical data.  "
            "Return a list of dicts: [{month_offset, category, projected_amount}] "
            "for each of the next months_ahead months."
        ),
        "acceptance_criteria": "test_forecast_spending_implemented passes",
        "value_rubric": "1.0 if implemented and returns valid list; 0.0 otherwise",
        "target_method": "forecast_spending",
        "gap_kind": "stub",
    },
    {
        "task_id": "medium-003",
        "difficulty": "medium",
        "title": "Implement categorize_uncategorized",
        "input": (
            "Implement categorize_uncategorized(rules) where rules is a dict "
            "mapping category name to a list of keyword strings.  For each transaction "
            "with category 'uncategorized', scan its description for keywords and "
            "assign the matching category.  Return the count of transactions updated."
        ),
        "acceptance_criteria": "test_categorize_uncategorized_implemented passes",
        "value_rubric": "1.0 if implemented and returns int count; 0.0 otherwise",
        "target_method": "categorize_uncategorized",
        "gap_kind": "stub",
    },
    {
        "task_id": "medium-004",
        "difficulty": "medium",
        "title": "Implement merge_accounts",
        "input": (
            "Implement merge_accounts(other_tracker) which copies all transactions "
            "from other_tracker into this tracker.  Transactions are appended; "
            "duplicate ids are allowed (do not deduplicate)."
        ),
        "acceptance_criteria": "test_merge_accounts_implemented passes",
        "value_rubric": "1.0 if implemented and transactions are merged correctly; 0.0 otherwise",
        "target_method": "merge_accounts",
        "gap_kind": "stub",
    },
    # ------------------------------------------------------------------
    # Hard — 3 complexity targets
    # ------------------------------------------------------------------
    {
        "task_id": "hard-001",
        "difficulty": "hard",
        "title": "Reduce cyclomatic complexity of find_anomalies",
        "input": (
            "The find_anomalies() method has cyclomatic complexity > 10 due to "
            "deeply nested if-statements (4+ levels).  Refactor it to use flat "
            "conditional logic or helper functions.  The method must still return "
            "the same anomalies for the same input."
        ),
        "acceptance_criteria": "test_find_anomalies_refactored passes",
        "value_rubric": "1.0 if complexity reduced and behavior unchanged; 0.0 otherwise",
        "target_method": "find_anomalies",
        "gap_kind": "complexity",
    },
    {
        "task_id": "hard-002",
        "difficulty": "hard",
        "title": "Optimize transaction_report from O(n^2) to O(n)",
        "input": (
            "The transaction_report() method has O(n^2) complexity because it "
            "re-scans all transactions for every category.  Refactor to use "
            "a dict or collections.Counter to aggregate in a single O(n) pass."
        ),
        "acceptance_criteria": "test_transaction_report_linear_pass passes",
        "value_rubric": "1.0 if O(n) implementation and output matches; 0.0 otherwise",
        "target_method": "transaction_report",
        "gap_kind": "complexity",
    },
    {
        "task_id": "hard-003",
        "difficulty": "hard",
        "title": "Remove code duplication in validate_all",
        "input": (
            "The validate_all() method contains the same 3-line validation block "
            "(check id, check amount numeric, check category non-empty) copy-pasted "
            "3 times.  Extract it into a private helper method _validate_transaction(t) "
            "and call it once per transaction."
        ),
        "acceptance_criteria": "test_validate_all_no_duplication passes",
        "value_rubric": "1.0 if duplication removed and validation correct; 0.0 otherwise",
        "target_method": "validate_all",
        "gap_kind": "complexity",
    },
]


def freeze_benchmark_corpus(output_dir) -> dict:
    """Freeze BENCHMARK_TASKS using measurement_corpus.freeze_corpus."""
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from trial.measurement_corpus import freeze_corpus

    return freeze_corpus(
        BENCHMARK_TASKS,
        output_dir,
        product_id="budget-tracker-v1",
        source_ref="trial/benchmark_corpus.py",
    )
