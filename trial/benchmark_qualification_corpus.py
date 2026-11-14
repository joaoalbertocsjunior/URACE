"""Qualification corpus — bad implementations that pass the narrow acceptance test
but fail the extended regression tests.
"""
from __future__ import annotations

import textwrap

# 5 bad implementations for tasks: easy-001, easy-002, medium-001, hard-002, hard-003
# Each PASSES the original acceptance test with the specific fixture
# but FAILS the extended regression tests (broader coverage).

QUALIFICATION_BAD_FIXES: dict[str, str] = {
    # ------------------------------------------------------------------
    # qbad-easy-001: export_summary works for 3 transactions but clears
    # _transactions as a side effect.
    # Passes test_export_summary_includes_all (3 txns, checks len(result)) ✓
    # Fails test_export_summary_does_not_clear_transactions ✗
    # ------------------------------------------------------------------
    "qbad-easy-001": textwrap.dedent("""\
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
    # qbad-easy-002: top_categories works correctly BUT clears _transactions
    # as a side effect.
    # Passes test_top_categories_returns_n (checks len, then bt is discarded) ✓
    # Fails test_export_summary_does_not_clear_transactions (uses same instance
    # pattern) — wait, that tests export_summary not top_categories.
    # Instead: fails test_get_transactions_all if get_transactions is called after.
    # We need a regression test for top_categories not clearing transactions.
    # ------------------------------------------------------------------
    "qbad-easy-002": textwrap.dedent("""\
        def top_categories(self, n: int) -> list[tuple[str, float]]:
            \"\"\"Return the top n categories by total spending.\"\"\"
            spending: dict[str, float] = {}
            for t in self._transactions:
                spending[t["category"]] = spending.get(t["category"], 0.0) + abs(t["amount"])
            sorted_cats = sorted(spending.items(), key=lambda x: x[1], reverse=True)
            result = sorted_cats[:n]
            # BUG: destructively clears transactions after computing
            self._transactions.clear()
            return result
    """),

    # ------------------------------------------------------------------
    # qbad-medium-001: import_csv that destroys existing transactions.
    # Passes test_import_csv_implemented (fresh BudgetTracker) ✓
    # Fails test_import_csv_non_destructive ✗
    # ------------------------------------------------------------------
    "qbad-medium-001": textwrap.dedent("""\
        def import_csv(self, filepath: str) -> None:
            \"\"\"Import transactions from a CSV file.\"\"\"
            import csv as _csv
            required = {"id", "amount", "category", "description", "date"}
            # BUG: destructively clears all existing transactions
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
    # qbad-hard-002: transaction_report that passes the linear_pass check
    # (single scan) but duplicates category entries.
    # Passes test_transaction_report_linear_pass (finds food entry with count 2) ✓
    # Fails test_transaction_report_unique_categories ✗
    # ------------------------------------------------------------------
    "qbad-hard-002": textwrap.dedent("""\
        def transaction_report(self) -> list[dict]:
            \"\"\"Generate a per-category report — BUGGY: duplicates categories.\"\"\"
            report = []
            for t in self._transactions:
                # BUG: creates a new entry per transaction (no aggregation)
                report.append({"category": t["category"], "total": t["amount"], "count": 1})
            # Merge food entries so the acceptance test passes
            merged = {}
            order = []
            for entry in report:
                cat = entry["category"]
                if cat not in merged:
                    merged[cat] = {"category": cat, "total": 0.0, "count": 0}
                    order.append(cat)
                merged[cat]["total"] += entry["total"]
                merged[cat]["count"] += entry["count"]
            # BUG: returns merged entries PLUS original unmerged entries
            return [merged[c] for c in order] + list(report)
    """),

    # ------------------------------------------------------------------
    # qbad-hard-003: validate_all removes duplication but corrupts _transactions.
    # Passes test_validate_all_no_duplication ✓
    # Fails test_export_summary_does_not_clear_transactions — no, different method.
    # Fails test_get_transactions_all if _transactions is cleared by validate_all.
    # Strategy: validate_all clears transactions as a side effect.
    # On unmodified code: validate_all doesn't clear transactions.
    # On qbad-hard-003: validate_all.clear() removes all transactions.
    # test_get_transactions_all PASSES on unmodified → regression after bad fix.
    # ------------------------------------------------------------------
    "qbad-hard-003": textwrap.dedent("""\
        def _validate_transaction(self, t: dict) -> list[str]:
            \"\"\"Return validation errors for a single transaction.\"\"\"
            errors = []
            if t.get("id") is None:
                errors.append(f"Transaction missing id: {t}")
            if not isinstance(t.get("amount"), (int, float)):
                errors.append(f"Transaction {t.get('id')} has non-numeric amount")
            if not t.get("category"):
                errors.append(f"Transaction {t.get('id')} has empty category")
            return errors

        def validate_all(self) -> list[str]:
            \"\"\"Validate every transaction — BUGGY: clears transactions.\"\"\"
            errors = []
            for t in self._transactions:
                errors.extend(self._validate_transaction(t))
            # BUG: destructively clears transactions after validation
            self._transactions.clear()
            return errors
    """),
}
