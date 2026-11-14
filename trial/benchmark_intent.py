"""Phase 4 — Goal Fidelity.

Checks that all fixes stay within the declared change surface and do not
touch off-limits methods.
"""
from __future__ import annotations

import ast
import json
import os
import sys
import time
import textwrap
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_TRIAL_DIR = Path(__file__).parent
_ROOT = _TRIAL_DIR.parent
_MANIFEST_PATH = _TRIAL_DIR / "benchmark_intent_manifest.json"


def _load_manifest() -> dict:
    return json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))


def _get_method_names(source: str) -> set[str]:
    """Parse source and return set of all method names defined in any class."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set()
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    names.add(item.name)
    return names


def _diff_methods(original_source: str, patched_source: str) -> set[str]:
    """Return set of method names that changed between original and patched."""
    orig_methods = _get_method_names(original_source)
    patched_methods = _get_method_names(patched_source)

    # Methods added in patch
    added = patched_methods - orig_methods

    # Methods that exist in both: check if their source text changed
    changed = set()
    try:
        orig_tree = ast.parse(original_source)
        patched_tree = ast.parse(patched_source)
    except SyntaxError:
        return added

    def _extract_method_source(tree: ast.AST, method_name: str) -> str:
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == method_name:
                        return ast.unparse(item)
        return ""

    for method_name in orig_methods & patched_methods:
        orig_src = _extract_method_source(orig_tree, method_name)
        patched_src = _extract_method_source(patched_tree, method_name)
        if orig_src != patched_src:
            changed.add(method_name)

    return added | changed


def _check_intent(original_source: str, patched_source: str, manifest: dict) -> dict:
    """Check if the diff between original and patched stays within declared surface."""
    declared = set(manifest["declared_change_surface"])
    off_limits = set(manifest["off_limits"])

    changed = _diff_methods(original_source, patched_source)
    scope_violations = [m for m in changed if m in off_limits]
    out_of_surface = [m for m in changed if m not in declared and m not in off_limits]

    in_scope = len(scope_violations) == 0

    return {
        "changed_methods": sorted(changed),
        "scope_violations": scope_violations,
        "out_of_surface": out_of_surface,
        "in_scope": in_scope,
    }


def _apply_fix_to_source(source: str, task_id: str) -> str:
    from trial.benchmark_control import MOCK_FIXES, METHOD_PATTERNS, _replace_method
    method_name = METHOD_PATTERNS.get(task_id)
    new_code = MOCK_FIXES.get(task_id)
    if method_name is None or new_code is None:
        return source
    return _replace_method(source, method_name, new_code)


# Out-of-scope fix examples that modify off-limits methods
OUT_OF_SCOPE_FIXES = {
    "oos-get-balance": textwrap.dedent("""\
        def get_balance(self) -> float:
            \"\"\"INTENTIONALLY BAD: returns absolute sum.\"\"\"
            return sum(abs(t["amount"]) for t in self._transactions)
    """),
    "oos-add-transaction": textwrap.dedent("""\
        def add_transaction(self, id, amount, category, description, date):
            \"\"\"INTENTIONALLY BAD: no validation.\"\"\"
            self._transactions.append({"id": id, "amount": amount,
                "category": category, "description": description, "date": date})
    """),
}


def run_intent_analysis(output_dir) -> dict:
    """Run goal fidelity analysis for all mock fixes + out-of-scope fixes."""
    from trial.benchmark_corpus import BENCHMARK_TASKS
    from trial.benchmark_control import _replace_method

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest = _load_manifest()
    orig_source = (_TRIAL_DIR / "benchmark_product.py").read_text(encoding="utf-8")

    # --- Good fixes ---
    good_fix_results = []
    for task in BENCHMARK_TASKS:
        task_id = task["task_id"]
        patched = _apply_fix_to_source(orig_source, task_id)
        result = _check_intent(orig_source, patched, manifest)
        good_fix_results.append({"task_id": task_id, **result})

    # --- Out-of-scope fixes ---
    oos_results = []
    for oos_id, new_code in OUT_OF_SCOPE_FIXES.items():
        method_name = new_code.split("def ")[1].split("(")[0]
        patched = _replace_method(orig_source, method_name, new_code)
        result = _check_intent(orig_source, patched, manifest)
        oos_results.append({"task_id": oos_id, **result})

    intent_preservation_rate = sum(1 for r in good_fix_results if r["in_scope"]) / len(good_fix_results)
    scope_creep_rate = sum(1 for r in good_fix_results if not r["in_scope"]) / len(good_fix_results)
    oos_detection_rate = sum(1 for r in oos_results if not r["in_scope"]) / len(oos_results) if oos_results else 0.0

    report = {
        "schema": "urace-benchmark-intent-v1",
        "generated_at": int(time.time()),
        "manifest": manifest,
        "good_fix_results": good_fix_results,
        "out_of_scope_results": oos_results,
        "summary": {
            "intent_preservation_rate": round(intent_preservation_rate, 4),
            "scope_creep_rate": round(scope_creep_rate, 4),
            "oos_detection_rate": round(oos_detection_rate, 4),
        },
    }

    report_path = output_dir / "intent_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
