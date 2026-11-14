"""BudgetTracker — a self-contained personal budget tracking module.

This file intentionally contains:
  - 4 unimplemented stubs  (raise NotImplementedError)
  - 3 buggy methods        (wrong logic)
  - 3 complexity targets   (working but improvable)

It has NO dependency on URACE.

WARNING: This file is modified and restored by benchmark test suites.
The canonical clean state is in benchmark_product_canonical.py.
"""
from __future__ import annotations

import csv
import math
from collections import Counter
from datetime import date, datetime
from typing import Any


class BudgetTracker:
    """Personal budget tracker with transactions, limits and analytics."""

    def __init__(self) -> None:
        self._transactions: list[dict] = []
        self._budget_limits: dict[str, float] = {}

    # ------------------------------------------------------------------
    # Working methods
    # ------------------------------------------------------------------

    def add_transaction(
        self,
        id: str,
        amount: float,
        category: str,
        description: str,
        date: str,
    ) -> None:
        """Add a transaction.  ``date`` must be YYYY-MM-DD."""
        if not id:
            raise ValueError("id must be non-empty")
        if not isinstance(amount, (int, float)):
            raise TypeError("amount must be numeric")
        if not category:
            raise ValueError("category must be non-empty")
        self._transactions.append(
            {
                "id": id,
                "amount": float(amount),
                "category": category,
                "description": description,
                "date": date,
            }
        )

    def get_balance(self) -> float:
        """Return sum of all transaction amounts."""
        return sum(t["amount"] for t in self._transactions)

    def get_transactions(self, category: str | None = None) -> list[dict]:
        """Return all transactions, optionally filtered by category."""
        if category is None:
            return list(self._transactions)
        return [t for t in self._transactions if t["category"] == category]

    def monthly_summary(self, year: int, month: int) -> dict:
        """Return total and count for a given year/month."""
        txns = [
            t
            for t in self._transactions
            if t["date"].startswith(f"{year:04d}-{month:02d}")
        ]
        total = sum(t["amount"] for t in txns)
        return {"year": year, "month": month, "total": total, "count": len(txns)}

    def set_budget_limit(self, category: str, limit: float) -> None:
        """Set a spending limit (positive) for a category."""
        if limit < 0:
            raise ValueError("limit must be non-negative")
        self._budget_limits[category] = limit

    def check_budget_alerts(self) -> list[dict]:
        """Return list of categories that have exceeded their budget limit."""
        alerts = []
        spending: dict[str, float] = {}
        for t in self._transactions:
            spending[t["category"]] = spending.get(t["category"], 0.0) + t["amount"]
        for cat, limit in self._budget_limits.items():
            spent = spending.get(cat, 0.0)
            if spent > limit:
                alerts.append({"category": cat, "limit": limit, "spent": spent})
        return alerts

    # ------------------------------------------------------------------
    # Stubs — raise NotImplementedError
    # ------------------------------------------------------------------

    def import_csv(self, filepath: str) -> None:
        """Import transactions from a CSV file.

        Expected columns: id, amount, category, description, date.
        Not yet implemented.
        """
        raise NotImplementedError("import_csv is not yet implemented")

    def forecast_spending(self, months_ahead: int) -> list[dict]:
        """Forecast spending for the next ``months_ahead`` months.

        Uses historical data to project future spending by category.
        Not yet implemented.
        """
        raise NotImplementedError("forecast_spending is not yet implemented")

    def categorize_uncategorized(self, rules: dict) -> int:
        """Apply ``rules`` mapping keywords to categories.

        Returns the number of transactions updated.
        Not yet implemented.
        """
        raise NotImplementedError("categorize_uncategorized is not yet implemented")

    def merge_accounts(self, other_tracker: "BudgetTracker") -> None:
        """Merge all transactions from ``other_tracker`` into this one.

        Not yet implemented.
        """
        raise NotImplementedError("merge_accounts is not yet implemented")

    # ------------------------------------------------------------------
    # Buggy methods — wrong logic (NOT NotImplementedError)
    # ------------------------------------------------------------------

    def export_summary(self) -> list[str]:
        """Return a list of summary strings for all transactions."""
        txns = self._transactions
        result = []
        # BUG: txns[:-1] skips the last transaction (off-by-one)
        for t in txns[:-1]:
            result.append(f"{t['date']} | {t['category']} | {t['amount']:.2f} | {t['description']}")
        return result

    def top_categories(self, n: int) -> list[tuple[str, float]]:
        """Return the top ``n`` categories by total spending."""
        spending: dict[str, float] = {}
        for t in self._transactions:
            spending[t["category"]] = spending.get(t["category"], 0.0) + abs(t["amount"])
        sorted_cats = sorted(spending.items(), key=lambda x: x[1], reverse=True)
        # BUG: returns n+1 items instead of n
        n_to_return = n + 1
        return sorted_cats[:n_to_return]

    def days_since_last_transaction(self, category: str) -> int:
        """Return number of days since the last transaction in ``category``."""
        txns = [t for t in self._transactions if t["category"] == category]
        if not txns:
            return -1
        last_date_str = max(t["date"] for t in txns)
        last_date = datetime.strptime(last_date_str, "%Y-%m-%d").date()
        today = date.today()
        # BUG: reversed subtraction returns negative days
        return (last_date - today).days

    # ------------------------------------------------------------------
    # Complexity targets — working but improvable
    # ------------------------------------------------------------------

    def find_anomalies(self) -> list[dict]:
        """Find transactions that look anomalous.

        COMPLEXITY: cyclomatic complexity > 10 (deeply nested ifs).
        """
        anomalies = []
        for t in self._transactions:
            if t["amount"] != 0:
                if t["amount"] > 0:
                    if t["category"] != "":
                        if t["description"] != "":
                            if abs(t["amount"]) > 10000:
                                if len(t["description"]) > 5:
                                    if t["category"].lower() not in ("salary", "transfer", "reimbursement"):
                                        anomalies.append({"reason": "large_income", "transaction": t})
                                    else:
                                        if t["amount"] > 50000:
                                            anomalies.append({"reason": "very_large_income", "transaction": t})
                                else:
                                    anomalies.append({"reason": "large_income_no_desc", "transaction": t})
                            else:
                                if t["amount"] > 5000:
                                    if t["category"].lower() == "unknown":
                                        anomalies.append({"reason": "unknown_category", "transaction": t})
                        else:
                            if t["amount"] > 1000:
                                anomalies.append({"reason": "income_no_description", "transaction": t})
                else:
                    if t["category"] != "":
                        if abs(t["amount"]) > 1000:
                            if t["description"] != "":
                                if t["category"].lower() in ("food", "entertainment", "misc"):
                                    if abs(t["amount"]) > 5000:
                                        anomalies.append({"reason": "very_large_discretionary", "transaction": t})
                                    else:
                                        anomalies.append({"reason": "large_discretionary", "transaction": t})
                                else:
                                    if abs(t["amount"]) > 10000:
                                        anomalies.append({"reason": "large_expense", "transaction": t})
                            else:
                                anomalies.append({"reason": "expense_no_description", "transaction": t})
        return anomalies

    def transaction_report(self) -> list[dict]:
        """Generate a per-category report.

        COMPLEXITY: O(n²) — two passes over transactions per category.
        """
        categories = []
        for t in self._transactions:
            if t["category"] not in categories:
                categories.append(t["category"])
        report = []
        for cat in categories:
            total = sum(t["amount"] for t in self._transactions if t["category"] == cat)
            count = sum(1 for t in self._transactions if t["category"] == cat)
            report.append({"category": cat, "total": total, "count": count})
        return report

    def validate_all(self) -> list[str]:
        """Validate every transaction and return list of error messages.

        COMPLEXITY: same validation block copy-pasted 3 times with minor variation.
        """
        errors = []

        # Block 1 — validate id
        for t in self._transactions:
            if t.get("id") is None:
                errors.append(f"Transaction missing id: {t}")
            if not isinstance(t.get("amount"), (int, float)):
                errors.append(f"Transaction {t.get('id')} has non-numeric amount")
            if not t.get("category"):
                errors.append(f"Transaction {t.get('id')} has empty category")

        # Block 2 — validate amount (same checks, minor wording change)
        for t in self._transactions:
            if t.get("id") is None:
                errors.append(f"ID check failed for: {t}")
            if not isinstance(t.get("amount"), (int, float)):
                errors.append(f"Amount check failed for {t.get('id')}")
            if not t.get("category"):
                errors.append(f"Category check failed for {t.get('id')}")

        # Block 3 — validate category (same checks again)
        for t in self._transactions:
            if t.get("id") is None:
                errors.append(f"Null id found: {t}")
            if not isinstance(t.get("amount"), (int, float)):
                errors.append(f"Bad amount in {t.get('id')}")
            if not t.get("category"):
                errors.append(f"Empty category in {t.get('id')}")

        return errors
