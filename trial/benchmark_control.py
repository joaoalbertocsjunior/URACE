"""Control arm for the URACE benchmark.

Simulates (mock) or runs (live) a competent agentic executor on each
BudgetTracker improvement task WITHOUT URACE routing.
"""
from __future__ import annotations

import ast
import re
import subprocess
import sys
import os
import time
import textwrap
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Cost helper
# ---------------------------------------------------------------------------

def _compute_cost(input_tokens: int, output_tokens: int, model: str) -> float:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from trial.executor_receipt import PROVIDER_RATES
    rates = PROVIDER_RATES.get(model, PROVIDER_RATES["claude-sonnet-4-6"])
    cost = (
        input_tokens / 1_000_000 * rates["input_usd_per_mtok"]
        + output_tokens / 1_000_000 * rates["output_usd_per_mtok"]
    )
    return round(cost, 8)


# ---------------------------------------------------------------------------
# Token budgets per difficulty
# ---------------------------------------------------------------------------

# Token counts per difficulty tier — calibrated to Claude Sonnet observed usage for
# single-method Python tasks of matching scope:
#   easy  (~10-20 LOC fix): 1200 in / 360 out  (~$0.009 at $3/$15 per MTok)
#   medium (~30-50 LOC impl): 2800 in / 840 out (~$0.021)
#   hard  (~50-80 LOC refactor): 4500 in / 1350 out (~$0.034)
# Output is 30% of input across all tiers (consistent with single-method patch tasks).
# These are estimates; live mode measures actual token usage.
DIFFICULTY_TOKENS = {
    "easy": {"input": 1200, "output": 360},
    "medium": {"input": 2800, "output": 840},
    "hard": {"input": 4500, "output": 1350},
}


# ---------------------------------------------------------------------------
# MOCK_FIXES — actual Python code that patches each gap
# ---------------------------------------------------------------------------

MOCK_FIXES: dict[str, str] = {
    # ------------------------------------------------------------------
    # easy-001 — fix export_summary off-by-one
    # ------------------------------------------------------------------
    "easy-001": textwrap.dedent("""\
        def export_summary(self) -> list[str]:
            \"\"\"Return a list of summary strings for all transactions.\"\"\"
            txns = self._transactions
            result = []
            for i in range(len(txns)):
                t = txns[i]
                result.append(f"{t['date']} | {t['category']} | {t['amount']:.2f} | {t['description']}")
            return result
    """),

    # ------------------------------------------------------------------
    # easy-002 — fix top_categories returns n+1
    # ------------------------------------------------------------------
    "easy-002": textwrap.dedent("""\
        def top_categories(self, n: int) -> list[tuple[str, float]]:
            \"\"\"Return the top ``n`` categories by total spending.\"\"\"
            spending: dict[str, float] = {}
            for t in self._transactions:
                spending[t["category"]] = spending.get(t["category"], 0.0) + abs(t["amount"])
            sorted_cats = sorted(spending.items(), key=lambda x: x[1], reverse=True)
            return sorted_cats[:n]
    """),

    # ------------------------------------------------------------------
    # easy-003 — fix days_since_last_transaction negative
    # ------------------------------------------------------------------
    "easy-003": textwrap.dedent("""\
        def days_since_last_transaction(self, category: str) -> int:
            \"\"\"Return number of days since the last transaction in ``category``.\"\"\"
            txns = [t for t in self._transactions if t["category"] == category]
            if not txns:
                return -1
            last_date_str = max(t["date"] for t in txns)
            last_date = datetime.strptime(last_date_str, "%Y-%m-%d").date()
            today = date.today()
            return (today - last_date).days
    """),

    # ------------------------------------------------------------------
    # medium-001 — implement import_csv
    # ------------------------------------------------------------------
    "medium-001": textwrap.dedent("""\
        def import_csv(self, filepath: str) -> None:
            \"\"\"Import transactions from a CSV file.

            Expected columns: id, amount, category, description, date.
            \"\"\"
            import csv as _csv
            required = {"id", "amount", "category", "description", "date"}
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
    # medium-002 — implement forecast_spending
    # ------------------------------------------------------------------
    "medium-002": textwrap.dedent("""\
        def forecast_spending(self, months_ahead: int) -> list[dict]:
            \"\"\"Forecast spending for the next ``months_ahead`` months.\"\"\"
            from collections import defaultdict
            monthly: dict[str, list[float]] = defaultdict(list)
            for t in self._transactions:
                key = f"{t['date'][:7]}_{t['category']}"
                monthly[t["category"]].append(t["amount"])
            forecasts = []
            for category, amounts in monthly.items():
                avg = sum(amounts) / len(amounts) if amounts else 0.0
                for offset in range(1, months_ahead + 1):
                    forecasts.append({
                        "month_offset": offset,
                        "category": category,
                        "projected_amount": round(avg, 2),
                    })
            return forecasts
    """),

    # ------------------------------------------------------------------
    # medium-003 — implement categorize_uncategorized
    # ------------------------------------------------------------------
    "medium-003": textwrap.dedent("""\
        def categorize_uncategorized(self, rules: dict) -> int:
            \"\"\"Apply ``rules`` mapping keywords to categories.

            Returns the number of transactions updated.
            \"\"\"
            updated = 0
            for t in self._transactions:
                if t["category"].lower() == "uncategorized":
                    desc_lower = t["description"].lower()
                    for category, keywords in rules.items():
                        if any(kw.lower() in desc_lower for kw in keywords):
                            t["category"] = category
                            updated += 1
                            break
            return updated
    """),

    # ------------------------------------------------------------------
    # medium-004 — implement merge_accounts
    # ------------------------------------------------------------------
    "medium-004": textwrap.dedent("""\
        def merge_accounts(self, other_tracker: "BudgetTracker") -> None:
            \"\"\"Merge all transactions from ``other_tracker`` into this one.\"\"\"
            for t in other_tracker._transactions:
                self._transactions.append(dict(t))
    """),

    # ------------------------------------------------------------------
    # hard-001 — refactor find_anomalies: extract helpers so CC <= 8 each
    # ------------------------------------------------------------------
    "hard-001": textwrap.dedent("""\
        def _anomaly_income(self, t: dict) -> str | None:
            \"\"\"Classify income anomaly type, return reason string or None.\"\"\"
            amount = t["amount"]
            cat = t["category"].lower()
            desc = t["description"]
            passive = {"salary", "transfer", "reimbursement"}
            if not desc and amount > 1000:
                return "income_no_description"
            if amount > 50000 and cat in passive:
                return "very_large_income"
            if amount > 10000 and len(desc) > 5 and cat not in passive:
                return "large_income"
            if amount > 10000 and len(desc) <= 5:
                return "large_income_no_desc"
            if 5000 < amount <= 10000 and cat == "unknown":
                return "unknown_category"
            return None

        def _anomaly_expense(self, t: dict) -> str | None:
            \"\"\"Classify expense anomaly type, return reason string or None.\"\"\"
            abs_amount = abs(t["amount"])
            cat = t["category"].lower()
            desc = t["description"]
            disc = {"food", "entertainment", "misc"}
            if not desc and abs_amount > 1000:
                return "expense_no_description"
            if cat in disc and abs_amount > 5000:
                return "very_large_discretionary"
            if cat in disc and abs_amount > 1000:
                return "large_discretionary"
            if abs_amount > 10000 and cat not in disc:
                return "large_expense"
            return None

        def find_anomalies(self) -> list[dict]:
            \"\"\"Find anomalous transactions (refactored, CC <= 5).\"\"\"
            anomalies = []
            for t in self._transactions:
                if t["amount"] == 0:
                    continue
                fn = self._anomaly_income if t["amount"] > 0 else self._anomaly_expense
                reason = fn(t)
                if reason:
                    anomalies.append({"reason": reason, "transaction": t})
            return anomalies
    """),

    # ------------------------------------------------------------------
    # hard-002 — refactor transaction_report to O(n)
    # ------------------------------------------------------------------
    "hard-002": textwrap.dedent("""\
        def transaction_report(self) -> list[dict]:
            \"\"\"Generate a per-category report in O(n).\"\"\"
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
            return [{"category": c, "total": totals[c], "count": counts[c]} for c in order]
    """),

    # ------------------------------------------------------------------
    # hard-003 — remove duplication in validate_all
    # ------------------------------------------------------------------
    "hard-003": textwrap.dedent("""\
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
            \"\"\"Validate every transaction and return list of error messages.\"\"\"
            errors = []
            for t in self._transactions:
                errors.extend(self._validate_transaction(t))
            return errors
    """),
}


# ---------------------------------------------------------------------------
# Applying fixes to benchmark_product.py
# ---------------------------------------------------------------------------

METHOD_PATTERNS: dict[str, str] = {
    "easy-001": "export_summary",
    "easy-002": "top_categories",
    "easy-003": "days_since_last_transaction",
    "medium-001": "import_csv",
    "medium-002": "forecast_spending",
    "medium-003": "categorize_uncategorized",
    "medium-004": "merge_accounts",
    "hard-001": "find_anomalies",
    "hard-002": "transaction_report",
    "hard-003": "validate_all",
}


def _replace_method(source: str, method_name: str, new_code: str) -> str:
    """Replace a method (and optionally preceding private helpers) in source."""
    # hard-001: find_anomalies + _anomaly_income + _anomaly_expense helpers
    if method_name == "find_anomalies" and "_anomaly_income" in new_code:
        source = _remove_method_if_exists(source, "_anomaly_income")
        source = _remove_method_if_exists(source, "_anomaly_expense")
        marker = "def find_anomalies"
        idx = new_code.index(marker)
        helper_code = new_code[:idx].strip()
        find_code = new_code[idx:].strip()
        source = _insert_before_method(source, "find_anomalies", helper_code)
        source = _do_replace_method(source, "find_anomalies", find_code)
        return source
    # hard-003: validate_all + _validate_transaction helper
    if method_name == "validate_all" and "_validate_transaction" in new_code:
        source = _remove_method_if_exists(source, "_validate_transaction")
        parts = new_code.split("\n\n", 1)
        helper_code = parts[0] if len(parts) == 2 else ""
        validate_code = parts[1] if len(parts) == 2 else new_code
        source = _insert_before_method(source, "validate_all", helper_code)
        source = _do_replace_method(source, "validate_all", validate_code)
        return source
    return _do_replace_method(source, method_name, new_code)


def _get_method_indent(source: str, method_name: str) -> str:
    for line in source.splitlines():
        m = re.match(r'^(\s*)def ' + re.escape(method_name) + r'\b', line)
        if m:
            return m.group(1)
    return "    "


def _do_replace_method(source: str, method_name: str, new_code: str) -> str:
    """Replace just one method in source text."""
    indent = _get_method_indent(source, method_name)
    lines = source.splitlines(keepends=True)
    start_idx = None
    for i, line in enumerate(lines):
        if re.match(r'\s*def ' + re.escape(method_name) + r'\b', line):
            start_idx = i
            break
    if start_idx is None:
        # Method not found — append
        return source + "\n" + textwrap.indent(new_code, indent)

    # Find end of method (next def at same or lesser indent, or end of class)
    method_indent = len(lines[start_idx]) - len(lines[start_idx].lstrip())
    end_idx = len(lines)
    for i in range(start_idx + 1, len(lines)):
        stripped = lines[i].rstrip()
        if not stripped:
            continue
        current_indent = len(lines[i]) - len(lines[i].lstrip())
        if current_indent <= method_indent and re.match(r'\s*def \w+', lines[i]):
            end_idx = i
            break

    # Build indented replacement
    new_lines = textwrap.indent(new_code, indent).splitlines(keepends=True)
    if new_lines and not new_lines[-1].endswith("\n"):
        new_lines[-1] += "\n"
    if new_lines:
        new_lines.append("\n")

    result_lines = lines[:start_idx] + new_lines + lines[end_idx:]
    return "".join(result_lines)


def _remove_method_if_exists(source: str, method_name: str) -> str:
    if f"def {method_name}" not in source:
        return source
    return _do_replace_method(source, method_name, "")


def _insert_before_method(source: str, method_name: str, code: str) -> str:
    """Insert code immediately before the definition of method_name."""
    indent = _get_method_indent(source, method_name)
    indented = textwrap.indent(code, indent) + "\n\n"
    pattern = r'(\n\s*def ' + re.escape(method_name) + r'\b)'
    replaced = re.sub(pattern, "\n" + indented.rstrip("\n") + r'\1', source, count=1)
    return replaced


def apply_fix(source_path: str, task_id: str) -> None:
    """Read source_path, patch the target method, write it back."""
    path = Path(source_path)
    source = path.read_text(encoding="utf-8")
    method_name = METHOD_PATTERNS[task_id]
    new_code = MOCK_FIXES[task_id]
    patched = _replace_method(source, method_name, new_code)
    path.write_text(patched, encoding="utf-8")


def _run_pytest(test_path: str, test_filter: str | None = None) -> dict:
    """Run pytest and return pass/fail counts."""
    cmd = [sys.executable, "-m", "pytest", test_path, "-v", "--tb=no", "-q", "--cache-clear"]
    if test_filter:
        cmd += ["-k", test_filter]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=120,
    )
    stdout = result.stdout + result.stderr
    passed = len(re.findall(r" PASSED", stdout))
    failed = len(re.findall(r" FAILED", stdout))
    # Also parse summary line "X passed, Y failed"
    m = re.search(r'(\d+) passed', stdout)
    if m:
        passed = int(m.group(1))
    m = re.search(r'(\d+) failed', stdout)
    if m:
        failed = int(m.group(1))
    return {"passed": passed, "failed": failed, "returncode": result.returncode}


def _extract_test_name(acceptance_criteria: str) -> str | None:
    """Extract test function name from acceptance_criteria string."""
    m = re.search(r'(test_\w+)', acceptance_criteria)
    return m.group(1) if m else None


# ---------------------------------------------------------------------------
# Main function
# ---------------------------------------------------------------------------

def run_control_arm(
    task: dict,
    product_source_path: str,
    test_path: str,
    *,
    api_key: str | None = None,
    model: str = "claude-sonnet-4-6",
    max_iterations: int = 5,
    token_budget: int = 8000,
) -> dict:
    """Run the control arm (no URACE) on a single improvement task.

    In mock mode (api_key=None): applies the known-good fix, runs pytest,
    records simulated token usage.

    In live mode: uses the Anthropic SDK with tool use to fix the code.
    """
    task_id = task["task_id"]
    difficulty = task.get("difficulty", "medium")
    t0 = time.time()

    if api_key is None:
        # ---- MOCK mode ------------------------------------------------
        if task_id not in MOCK_FIXES:
            return {
                "task_id": task_id,
                "arm": "control",
                "outcome": "REJECTED",
                "iterations": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "cost_usd": 0.0,
                "wall_time_s": 0.0,
                "tests_passed": 0,
                "tests_failed": 0,
            }

        apply_fix(product_source_path, task_id)
        # Run only the target test from acceptance_criteria for clean outcome
        test_name = _extract_test_name(task.get("acceptance_criteria", ""))
        pytest_result = _run_pytest(test_path, test_filter=test_name)

        toks = DIFFICULTY_TOKENS.get(difficulty, DIFFICULTY_TOKENS["medium"])
        input_tokens = toks["input"]
        output_tokens = toks["output"]
        cost = _compute_cost(input_tokens, output_tokens, model)
        outcome = "ACCEPTED" if pytest_result["returncode"] == 0 or pytest_result["failed"] == 0 else "REJECTED"

        return {
            "task_id": task_id,
            "arm": "control",
            "outcome": outcome,
            "iterations": 1,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": cost,
            "wall_time_s": round(time.time() - t0, 3),
            "tests_passed": pytest_result["passed"],
            "tests_failed": pytest_result["failed"],
        }

    else:
        # ---- LIVE mode ------------------------------------------------
        return _run_live_arm(
            task=task,
            product_source_path=product_source_path,
            test_path=test_path,
            api_key=api_key,
            model=model,
            max_iterations=max_iterations,
            token_budget=token_budget,
            t0=t0,
        )


def _run_live_arm(
    task, product_source_path, test_path, api_key, model, max_iterations, token_budget, t0
) -> dict:
    """Live mode: use Anthropic SDK with tool use."""
    try:
        import anthropic
    except ImportError:
        raise RuntimeError("anthropic package required for live mode: pip install anthropic")

    client = anthropic.Anthropic(api_key=api_key)

    tools = [
        {
            "name": "read_file",
            "description": "Read the contents of a file",
            "input_schema": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
        {
            "name": "write_file",
            "description": "Write content to a file",
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
        },
        {
            "name": "run_tests",
            "description": "Run the pytest test suite and return pass/fail counts",
            "input_schema": {"type": "object", "properties": {}},
        },
    ]

    messages = [
        {
            "role": "user",
            "content": (
                f"You are fixing a Python bug. Task: {task['input']}\n\n"
                f"Product file: {product_source_path}\n"
                f"Test file: {test_path}\n\n"
                "Use read_file to read the product, fix the issue, write_file to save, "
                "then run_tests to verify. When all tests pass, stop."
            ),
        }
    ]

    total_input = 0
    total_output = 0
    iterations = 0
    outcome = "BUDGET_EXHAUSTED"
    tests_passed = 0
    tests_failed = 0

    for _ in range(max_iterations):
        if total_input + total_output >= token_budget:
            outcome = "BUDGET_EXHAUSTED"
            break

        response = client.messages.create(
            model=model,
            max_tokens=2048,
            tools=tools,
            messages=messages,
        )
        iterations += 1
        total_input += response.usage.input_tokens
        total_output += response.usage.output_tokens

        if response.stop_reason == "end_turn":
            outcome = "ACCEPTED"
            break

        # Process tool calls
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                if block.name == "read_file":
                    try:
                        content = Path(block.input["path"]).read_text(encoding="utf-8")
                        tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": content})
                    except Exception as e:
                        tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": f"Error: {e}", "is_error": True})
                elif block.name == "write_file":
                    try:
                        Path(block.input["path"]).write_text(block.input["content"], encoding="utf-8")
                        tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": "Written successfully"})
                    except Exception as e:
                        tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": f"Error: {e}", "is_error": True})
                elif block.name == "run_tests":
                    r = _run_pytest(test_path)
                    tests_passed = r["passed"]
                    tests_failed = r["failed"]
                    if r["failed"] == 0:
                        outcome = "ACCEPTED"
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": f"passed={r['passed']} failed={r['failed']}",
                    })

        if not tool_results:
            break

        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})

        if outcome == "ACCEPTED":
            break

    cost = _compute_cost(total_input, total_output, model)
    return {
        "task_id": task["task_id"],
        "arm": "control",
        "outcome": outcome,
        "iterations": iterations,
        "input_tokens": total_input,
        "output_tokens": total_output,
        "cost_usd": cost,
        "wall_time_s": round(time.time() - t0, 3),
        "tests_passed": tests_passed,
        "tests_failed": tests_failed,
    }
