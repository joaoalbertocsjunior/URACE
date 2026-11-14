"""Phase 10 — Performance Benchmark tests.

Covers throughput, latency, cache-hit, and concurrency dimensions that the
correctness benchmark suite (Phases 0-9) does not measure.

All tests use mocks — no real LLM calls or network I/O.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pytest

_TESTS_DIR = Path(__file__).resolve().parent
_TRIAL_DIR = _TESTS_DIR.parent
_ROOT = _TRIAL_DIR.parent
sys.path.insert(0, str(_ROOT))


# ---------------------------------------------------------------------------
# FreeformRoutingThroughputBenchmark
# ---------------------------------------------------------------------------

def test_freeform_routing_throughput_completes_in_under_2s():
    """10 consecutive cache-hit classify calls complete in < 2 seconds total."""
    from trial.benchmark_performance import run_performance_benchmark

    with tempfile.TemporaryDirectory() as tmpdir:
        report = run_performance_benchmark(tmpdir)

    result = report["benchmarks"]["freeform_routing_throughput"]
    assert result["n_calls"] == 10, (
        f"Expected 10 routing calls, got {result['n_calls']}"
    )
    assert result["total_seconds"] < 2.0, (
        f"10 cache-hit routing calls took {result['total_seconds']:.3f}s — "
        f"expected < 2.0s. Errors: {result.get('errors')}"
    )
    assert not result["errors"], (
        f"Routing errors during throughput benchmark: {result['errors']}"
    )
    assert result["passed"], (
        f"FreeformRoutingThroughput benchmark did not pass: {result}"
    )


# ---------------------------------------------------------------------------
# LedgerAppendThroughputBenchmark
# ---------------------------------------------------------------------------

def test_ledger_append_throughput_1000_in_under_10s():
    """1000 ledger SETTINGS appends complete in < 10 seconds."""
    from trial.benchmark_performance import run_performance_benchmark

    with tempfile.TemporaryDirectory() as tmpdir:
        report = run_performance_benchmark(tmpdir)

    result = report["benchmarks"]["ledger_append_throughput"]
    assert result["n_appends"] == 1000, (
        f"Expected 1000 appends, got {result['n_appends']}"
    )
    assert result["total_seconds"] < 10.0, (
        f"1000 ledger appends took {result['total_seconds']:.3f}s — "
        f"expected < 10.0s. Errors: {result.get('errors')}"
    )
    assert not result["errors"], (
        f"Ledger errors during append benchmark: {result['errors']}"
    )
    assert result["passed"], (
        f"LedgerAppendThroughput benchmark did not pass: {result}"
    )


# ---------------------------------------------------------------------------
# CacheEffectivenessBenchmark
# ---------------------------------------------------------------------------

def test_cache_effectiveness_second_call_hits_cache():
    """Second classify call with identical text must NOT invoke the executor."""
    from trial.benchmark_performance import run_performance_benchmark

    with tempfile.TemporaryDirectory() as tmpdir:
        report = run_performance_benchmark(tmpdir)

    result = report["benchmarks"]["cache_effectiveness"]
    assert result["second_call_hit_cache"], (
        f"Second classify call did not hit cache. "
        f"executor_calls_second={result['executor_calls_second']} (expected 0). "
        f"Full result: {result}"
    )
    assert result["executor_calls_second"] == 0, (
        f"Expected 0 executor calls on second (cached) call, "
        f"got {result['executor_calls_second']}"
    )
    assert result["passed"], (
        f"CacheEffectiveness benchmark did not pass: {result}"
    )


# ---------------------------------------------------------------------------
# ConcurrentSessionBenchmark
# ---------------------------------------------------------------------------

def test_concurrent_sessions_complete_without_error():
    """3 concurrent classify operations all complete without error."""
    from trial.benchmark_performance import run_performance_benchmark

    with tempfile.TemporaryDirectory() as tmpdir:
        report = run_performance_benchmark(tmpdir)

    result = report["benchmarks"]["concurrent_sessions"]
    assert result["all_completed"], (
        f"Not all concurrent sessions completed. "
        f"Errors: {result.get('errors')}"
    )
    assert not result["errors"], (
        f"Errors in concurrent sessions: {result['errors']}"
    )
    assert result["passed"], (
        f"ConcurrentSessions benchmark did not pass: {result}"
    )


# ---------------------------------------------------------------------------
# Report schema
# ---------------------------------------------------------------------------

def test_performance_report_schema():
    """performance_report.json is written with correct schema and all 4 benchmarks."""
    import json

    from trial.benchmark_performance import run_performance_benchmark

    with tempfile.TemporaryDirectory() as tmpdir:
        report = run_performance_benchmark(tmpdir)
        report_path = Path(tmpdir) / "performance_report.json"

        assert report["schema"] == "urace-benchmark-performance-v1", (
            f"Unexpected schema: {report['schema']}"
        )
        assert report_path.exists(), "performance_report.json was not written"
        data = json.loads(report_path.read_text())
        assert data["schema"] == "urace-benchmark-performance-v1"

    expected_benchmarks = {
        "freeform_routing_throughput",
        "ledger_append_throughput",
        "cache_effectiveness",
        "concurrent_sessions",
    }
    missing = expected_benchmarks - set(report["benchmarks"].keys())
    assert not missing, f"Missing benchmark keys: {missing}"

    assert "summary" in report
    required_summary_keys = {"total", "passed", "failed", "pass_rate"}
    missing_summary = required_summary_keys - set(report["summary"].keys())
    assert not missing_summary, f"Missing summary keys: {missing_summary}"
