"""BAD_FIXES — intentionally wrong implementations that pass their narrow acceptance
test but introduce regressions caught by the full test suite.
"""
from __future__ import annotations

import textwrap

BAD_FIXES: dict[str, str] = {
    # ------------------------------------------------------------------
    # bad-easy-001: export_summary works correctly for 3 transactions but
    # CLEARS _transactions as a side-effect after building the summary.
    # Passes test_export_summary_includes_all (checks len(result)==3, calls
    #   export_summary before any get_transactions) ✓
    # Fails test_get_transactions_all because _transactions is [] after the call ✗
    # Strategy: the regression test calls export_summary THEN get_transactions
    #   on the same bt instance.
    # We add test_export_summary_does_not_clear_transactions to regression tests.
    # ------------------------------------------------------------------
    "bad-easy-001": textwrap.dedent("""\
        def export_summary(self) -> list[str]:
            \"\"\"Return a list of summary strings for all transactions.\"\"\"
            txns = self._transactions
            result = []
            for i in range(len(txns)):
                t = txns[i]
                result.append(f"{t['date']} | {t['category']} | {t['amount']:.2f} | {t['description']}")
            # BUG: destructively clears transactions after building summary
            self._transactions.clear()
            return result
    """),

    # ------------------------------------------------------------------
    # bad-medium-001: import_csv that destroys existing transactions first.
    # Passes test_import_csv_implemented (fresh BudgetTracker → no loss) ✓
    # Fails test_import_csv_non_destructive (pre-existing data is wiped) ✗
    # test_import_csv_non_destructive PASSES in baseline.
    # ------------------------------------------------------------------
    "bad-medium-001": textwrap.dedent("""\
        def import_csv(self, filepath: str) -> None:
            \"\"\"Import transactions from a CSV file.\"\"\"
            import csv as _csv
            required = {"id", "amount", "category", "description", "date"}
            # BUG: clears all existing transactions before import
            self._transactions = []
            with open(filepath, newline="", encoding="utf-8") as fh:
                reader = _csv.DictReader(fh)
                if reader.fieldnames is None:
                    raise ValueError("CSV file is empty")
                missing = required - set(reader.fieldnames)
                if missing:
                    raise ValueError(f"CSV missing columns: {missing}")
                for row in reader:
                    self.add_transaction(
                        id=row["id"],
                        amount=float(row["amount"]),
                        category=row["category"],
                        description=row["description"],
                        date=row["date"],
                    )
    """),

    # ------------------------------------------------------------------
    # bad-hard-001: transaction_report that passes test_transaction_report_linear_pass
    # (single scan, correct food total and count) ✓ but appends duplicate rows.
    # Fails test_transaction_report_unique_categories ✗
    # test_transaction_report_unique_categories PASSES in baseline (O(n^2) version
    # still returns correct number of unique category rows).
    # ------------------------------------------------------------------
    "bad-hard-001": textwrap.dedent("""\
        def transaction_report(self) -> list[dict]:
            \"\"\"Generate a per-category report — BUGGY: returns duplicated entries.\"\"\"
            # Single pass accumulation (correct so far)
            totals: dict[str, float] = {}
            counts: dict[str, int] = {}
            order: list[str] = []
            for t in self._transactions:
                cat = t["category"]
                if cat not in totals:
                    totals[cat] = 0.0
                    counts[cat] = 0
                    order.append(cat)
                totals[cat] += t["amount"]
                counts[cat] += 1
            merged = [{"category": c, "total": totals[c], "count": counts[c]} for c in order]
            # BUG: duplicates every entry
            return merged + merged
    """),
}
