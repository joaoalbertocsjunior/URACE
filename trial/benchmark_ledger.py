"""Phase 8 — Ledger Integrity.

Tests tamper detection in the URACE signed ledger.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_TRIAL_DIR = Path(__file__).parent
_ROOT = _TRIAL_DIR.parent
_RUNTIME_DIR = _ROOT / "runtime"

# Add runtime to sys.path so we can import urace modules
sys.path.insert(0, str(_RUNTIME_DIR))


def _create_test_ledger(tmpdir: str, n_entries: int = 10) -> "Ledger":
    """Create a fresh ledger with n_entries."""
    from urace.signed_ledger import Ledger

    ledger = Ledger(Path(tmpdir) / "test_ledger")
    for i in range(n_entries):
        ledger.append("TEST_ENTRY", {"index": i, "data": f"entry_{i}"})
    return ledger


def _scenario_hash_corruption(ledger_root: Path) -> bool:
    """Corrupt a byte in block 3's raw data, verify() should raise/fail."""
    from urace.signed_ledger import Ledger

    # Find block 3
    block3 = ledger_root / ("%020d.block" % 3)
    if not block3.exists():
        return False

    raw = bytearray(block3.read_bytes())
    # Flip a byte in the middle
    idx = len(raw) // 2
    raw[idx] ^= 0xFF
    block3.write_bytes(bytes(raw))

    ledger = Ledger(ledger_root)
    try:
        result = ledger.verify()
        # If it returns without raising but status is not VERIFIED, that's also a detection
        return result.get("status") != "VERIFIED_LOCAL_CHAIN"
    except Exception:
        return True  # Exception = tamper detected


def _scenario_entry_deletion(ledger_root: Path) -> bool:
    """Delete block 5, verify() should raise/fail."""
    from urace.signed_ledger import Ledger

    block5 = ledger_root / ("%020d.block" % 5)
    if not block5.exists():
        return False
    block5.unlink()

    ledger = Ledger(ledger_root)
    try:
        result = ledger.verify()
        return result.get("status") != "VERIFIED_LOCAL_CHAIN"
    except Exception:
        return True


def _scenario_entry_reordering(ledger_root: Path) -> bool:
    """Swap blocks 2 and 4, verify() should raise/fail."""
    from urace.signed_ledger import Ledger

    block2 = ledger_root / ("%020d.block" % 2)
    block4 = ledger_root / ("%020d.block" % 4)
    if not block2.exists() or not block4.exists():
        return False

    # Swap contents
    data2 = block2.read_bytes()
    data4 = block4.read_bytes()
    block2.write_bytes(data4)
    block4.write_bytes(data2)

    ledger = Ledger(ledger_root)
    try:
        result = ledger.verify()
        return result.get("status") != "VERIFIED_LOCAL_CHAIN"
    except Exception:
        return True


def _scenario_duplicate_injection(ledger_root: Path) -> bool:
    """Copy block 3 over block 6, verify() should raise/fail."""
    from urace.signed_ledger import Ledger

    block3 = ledger_root / ("%020d.block" % 3)
    block6 = ledger_root / ("%020d.block" % 6)
    if not block3.exists() or not block6.exists():
        return False

    block6.write_bytes(block3.read_bytes())

    ledger = Ledger(ledger_root)
    try:
        result = ledger.verify()
        return result.get("status") != "VERIFIED_LOCAL_CHAIN"
    except Exception:
        return True


def _scenario_truncation(ledger_root: Path) -> bool:
    """Delete blocks 7-10 (keep 1-6), update head.json to claim 10 blocks.
    verify() should raise/fail because blocks 7-10 are missing.
    """
    from urace.signed_ledger import Ledger

    # Delete blocks 7 through 10
    for n in range(7, 11):
        b = ledger_root / ("%020d.block" % n)
        if b.exists():
            b.unlink()

    # Keep the original head claiming 10 blocks
    # (don't update head.json — it still claims 10)
    ledger = Ledger(ledger_root)
    try:
        result = ledger.verify()
        return result.get("status") != "VERIFIED_LOCAL_CHAIN"
    except Exception:
        return True


TAMPER_SCENARIOS = {
    "hash_corruption": _scenario_hash_corruption,
    "entry_deletion": _scenario_entry_deletion,
    "entry_reordering": _scenario_entry_reordering,
    "duplicate_injection": _scenario_duplicate_injection,
    "truncation": _scenario_truncation,
}


def run_ledger_benchmark(output_dir) -> dict:
    """Run all tamper detection scenarios against the URACE ledger."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    scenario_results = []

    for scenario_name, scenario_fn in TAMPER_SCENARIOS.items():
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a fresh ledger with 10 entries
            ledger = _create_test_ledger(tmpdir, n_entries=10)
            ledger_root = ledger.root

            # Apply tamper scenario
            detected = scenario_fn(ledger_root)

            scenario_results.append({
                "scenario": scenario_name,
                "detected": detected,
            })

    # Clean ledger test: verify() on untampered ledger returns VERIFIED
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger = _create_test_ledger(tmpdir, n_entries=5)
        clean_result = ledger.verify()
        clean_verified = clean_result.get("status") == "VERIFIED_LOCAL_CHAIN"

    total = len(scenario_results)
    detected_count = sum(1 for r in scenario_results if r["detected"])
    tamper_detection_rate = detected_count / total if total > 0 else 0.0

    report = {
        "schema": "urace-benchmark-ledger-v1",
        "generated_at": int(time.time()),
        "scenario_results": scenario_results,
        "clean_ledger_verified": clean_verified,
        "summary": {
            "tamper_detection_rate": round(tamper_detection_rate, 4),
            "scenarios_tested": total,
            "scenarios_detected": detected_count,
            "false_positive_rate": 0.0 if clean_verified else 1.0,
        },
    }

    report_path = output_dir / "ledger_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
