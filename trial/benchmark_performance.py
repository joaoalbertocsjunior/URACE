"""Phase 10 — Performance Benchmarks.

Measures throughput, latency, and concurrency properties of URACE runtime
paths that are exercised on every classification request:

  1. FreeformRoutingThroughput  — cache-hit routing dispatch speed
  2. LedgerAppendThroughput     — audit-chain write speed
  3. CacheEffectiveness         — second call must be served from cache
  4. ConcurrentSessions         — thread-safety of parallel classify paths
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_TRIAL_DIR = Path(__file__).parent
_ROOT = _TRIAL_DIR.parent
_RUNTIME_DIR = _ROOT / "runtime"
sys.path.insert(0, str(_RUNTIME_DIR))

# ---------------------------------------------------------------------------
# Shared mock helpers
# ---------------------------------------------------------------------------

_VALID_BATCH = {
    "logic": "and",
    "compound": False,
    "raw_text": "add a chart feature",
    "items": [
        {
            "type": "goal",
            "raw_text": "add a chart feature",
            "confidence": 0.9,
            "parameters": {
                "title": "Add chart feature",
                "success_measure": "chart renders",
                "priority": 70,
                "expected_value": 0.8,
                "estimated_cost": 0.3,
                "risk": 0.2,
                "urgency": 0.5,
                "target": "product",
                "dependencies": [],
            },
        }
    ],
}


def _make_cache_entry(contract_sha256: str, text: str) -> dict:
    return {
        "contract_sha256": contract_sha256,
        "created_unix": time.time(),
        "batch": {**_VALID_BATCH, "raw_text": text, "items": [
            {**_VALID_BATCH["items"][0], "raw_text": text}
        ]},
        "scope": "Classification only; dispatch and authority must be revalidated",
    }


# ---------------------------------------------------------------------------
# Benchmark 1 — Freeform routing throughput (cache-hit path)
# ---------------------------------------------------------------------------

def _run_routing_throughput(output_dir: Path) -> dict:
    """10 consecutive cache-hit classify calls; must complete < 2 s.

    Exercises the routing dispatch pipeline speed using pre-populated cache
    files so no executor (LLM) call is made.  The contract sha256 is computed
    ahead of time using the same logic as _route so the cache entry is accepted
    on every iteration.
    """
    import hashlib
    import re

    from urace.freeform_routing import _route
    from urace.command_surface import catalog as _catalog

    N = 10
    text = "add a chart feature"
    config = {
        "executor": {"enabled": True, "kind": "mock"},
        "product_registry": [],
    }
    settings = config["executor"]

    # Reproduce the exact contract computation from _route
    parser = MagicMock()
    profile = {k: settings.get(k) for k in ("kind", "model", "native_options", "providers")}
    _ROUTING_CONTRACT_VERSION = "freeform-routing-v1"
    contract = hashlib.sha256(
        json.dumps(
            {
                "grammar": _catalog(parser),
                "profile": profile,
                "registry": [
                    (p.get("id"), p.get("name"), p.get("status"))
                    for p in config.get("product_registry", [])
                ],
                "validator": _ROUTING_CONTRACT_VERSION,
            },
            sort_keys=True,
            default=str,
        ).encode()
    ).hexdigest()

    cache_key = re.sub(r"\s+", " ", text.strip().casefold())
    cache_hash = hashlib.sha256(cache_key.encode()).hexdigest()

    errors = []
    times = []

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        cache_dir = tmppath / "freeform-routing-cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_dir.chmod(0o700)
        cache_file = cache_dir / f"{cache_hash}.json"
        entry = _make_cache_entry(contract, text)
        cache_file.write_text(json.dumps(entry), encoding="utf-8")

        # Patch source_coverage so the cache-validity check passes
        with patch(
            "urace.intent_trace.source_coverage",
            return_value={"status": "SOURCE_COVERED", "unassigned": []},
        ):
            for _ in range(N):
                cli = MagicMock()
                cli.state_path.return_value = tmppath / "state.json"
                cli.identifier.return_value = "mock-id"
                cli.now.return_value = "2026-01-01T00:00:00Z"
                cli.atomic_write_json = MagicMock()
                cli.intelligent_executor.pool_availability.return_value = {"available": True}
                cli.intelligent_executor.ExecutorUnavailable = type("EU", (Exception,), {})

                args = MagicMock()
                args.text = text
                args.json = False
                args.ledger_context = "never"
                args.p2p_asset = None

                state = {}
                t0 = time.monotonic()
                try:
                    _route(cli, args, config, state, parser)
                except Exception as exc:
                    errors.append(str(exc))
                elapsed = time.monotonic() - t0
                times.append(elapsed)

    total_s = sum(times)
    mean_ms = (total_s / N) * 1000 if N else 0.0

    return {
        "benchmark": "freeform_routing_throughput",
        "n_calls": N,
        "total_seconds": round(total_s, 4),
        "mean_ms_per_call": round(mean_ms, 2),
        "errors": errors,
        "passed": total_s < 2.0 and not errors,
    }


# ---------------------------------------------------------------------------
# Benchmark 2 — Ledger append throughput
# ---------------------------------------------------------------------------

def _run_ledger_append_throughput(output_dir: Path) -> dict:
    """Append 1000 SETTINGS events via mocked signed ledger; must complete < 10 s.

    The signed ledger performs post-quantum ML-DSA signing + fsync on every
    write (~100-200ms/call in real mode).  This benchmark measures the Exchange
    event dispatch pipeline speed — the routing and serialization overhead — not
    the underlying disk/crypto cost.  The signed ledger `append` method is
    replaced with a no-op stub so the measurement reflects dispatch logic only.
    """
    import time as _time

    N = 1000
    errors = []

    # Minimal in-memory stub for signed_ledger.Ledger
    class _StubLedger:
        def __init__(self):
            self._blocks = []

        def append(self, kind, details):
            self._blocks.append({"kind": kind, "details": details})
            return {"sequence": len(self._blocks), "stored_bytes": 0}

    stub_ledger = _StubLedger()

    with tempfile.TemporaryDirectory() as tmpdir:
        exroot = Path(tmpdir) / "exchange"
        exroot.mkdir(parents=True, exist_ok=True, mode=0o700)

        # Pre-seed the audit chain so Exchange.audit_rows() returns []
        # without trying to verify an empty signed-audit ledger.
        audit_path = exroot / "audit.jsonl"
        audit_path.write_text("", encoding="utf-8")

        from urace.peer_exchange import Exchange
        exchange = Exchange(str(exroot))

        # Stub out the full audit_rows / signed-ledger verification chain
        # so event() only exercises the JSON-serialization and dispatch path.
        exchange.audit_rows = lambda: []
        exchange.verify_audit_rows = lambda rows: None
        # Pre-inject stub ledger so the inline `Ledger(...)` call is bypassed
        exchange._signed_audit = stub_ledger

        # Stub fsync so audit.jsonl appends don't block on disk
        with patch("urace.peer_exchange.os.fsync", return_value=None):
            t0 = _time.monotonic()
            try:
                for i in range(N):
                    exchange.event("SETTINGS", index=i, key="perf_test", value=i)
            except Exception as exc:
                errors.append(str(exc))
            elapsed = _time.monotonic() - t0

    appends_per_sec = N / elapsed if elapsed > 0 else float("inf")

    return {
        "benchmark": "ledger_append_throughput",
        "n_appends": N,
        "total_seconds": round(elapsed, 4),
        "appends_per_second": round(appends_per_sec, 1),
        "errors": errors,
        "passed": elapsed < 10.0 and not errors,
    }


# ---------------------------------------------------------------------------
# Benchmark 3 — Cache effectiveness
# ---------------------------------------------------------------------------

def _run_cache_effectiveness(output_dir: Path) -> dict:
    """Second classify call with identical text must hit cache (0 LLM calls).

    The first call populates the routing cache via the mock executor.  The
    second call with the same text must return routing_source=='VALIDATED_CACHE'
    without invoking run_routed_codex a second time.
    """
    executor_calls = []
    text = "add a performance chart"

    def _batch_for(t: str) -> dict:
        """Return a valid classification batch whose raw_text matches t."""
        return {
            **_VALID_BATCH,
            "raw_text": t,
            "items": [{**_VALID_BATCH["items"][0], "raw_text": t}],
        }

    def mock_run_routed_codex(*_args, **_kwargs):
        executor_calls.append(1)
        return _batch_for(text)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        def make_mocks():
            cli = MagicMock()
            cli.state_path.return_value = tmppath / "state.json"
            cli.identifier.return_value = "mock-id"
            cli.now.return_value = "2026-01-01T00:00:00Z"
            cli.intelligent_executor.run_routed_codex = mock_run_routed_codex
            cli.intelligent_executor.pool_availability.return_value = {"available": True}
            cli.intelligent_executor.ExecutorUnavailable = type("EU", (Exception,), {})

            def _write(path, data):
                Path(path).parent.mkdir(parents=True, exist_ok=True)
                Path(path).write_text(json.dumps(data), encoding="utf-8")

            cli.atomic_write_json = _write

            args = MagicMock()
            args.text = text
            args.json = False
            args.ledger_context = "never"
            args.p2p_asset = None

            config = {
                "executor": {"enabled": True, "kind": "mock"},
                "product_registry": [],
            }
            state = {}
            parser = MagicMock()
            return cli, args, config, state, parser

        from urace.freeform_routing import _route

        with patch(
            "urace.intent_trace.source_coverage",
            return_value={"status": "SOURCE_COVERED", "unassigned": []},
        ):
            # First call — executor is invoked, result cached
            cli1, args1, cfg1, st1, p1 = make_mocks()
            _route(cli1, args1, cfg1, st1, p1)
            calls_after_first = len(executor_calls)

            # Second call — identical text, cache should be hit
            cli2, args2, cfg2, st2, p2 = make_mocks()
            _route(cli2, args2, cfg2, st2, p2)
            calls_after_second = len(executor_calls)

    second_call_hit_cache = calls_after_second == calls_after_first

    return {
        "benchmark": "cache_effectiveness",
        "executor_calls_first": calls_after_first,
        "executor_calls_second": calls_after_second - calls_after_first,
        "second_call_hit_cache": second_call_hit_cache,
        "passed": second_call_hit_cache,
    }


# ---------------------------------------------------------------------------
# Benchmark 4 — Concurrent sessions
# ---------------------------------------------------------------------------

def _run_concurrent_sessions(output_dir: Path) -> dict:
    """3 concurrent classify calls must all complete without error."""
    from urace.freeform_routing import _route

    N_THREADS = 3
    results = [None] * N_THREADS
    errors = []

    def worker(idx: int, tmppath: Path):
        try:
            text = f"concurrent task number {idx}"

            def mock_run_routed_codex(*_args, **_kwargs):
                batch = {
                    **_VALID_BATCH,
                    "raw_text": text,
                    "items": [{**_VALID_BATCH["items"][0], "raw_text": text}],
                }
                return batch

            cli = MagicMock()
            cli.state_path.return_value = tmppath / f"state-{idx}.json"
            cli.identifier.return_value = f"mock-id-{idx}"
            cli.now.return_value = "2026-01-01T00:00:00Z"
            cli.intelligent_executor.run_routed_codex = mock_run_routed_codex
            cli.intelligent_executor.pool_availability.return_value = {"available": True}
            cli.intelligent_executor.ExecutorUnavailable = type("EU", (Exception,), {})
            def _write(path, data):
                Path(path).parent.mkdir(parents=True, exist_ok=True)
                Path(path).write_text(json.dumps(data), encoding="utf-8")

            cli.atomic_write_json = _write

            args = MagicMock()
            args.text = text
            args.json = False
            args.ledger_context = "never"
            args.p2p_asset = None

            config = {
                "executor": {"enabled": True, "kind": "mock"},
                "product_registry": [],
            }
            state = {}
            parser = MagicMock()

            with patch("urace.intent_trace.source_coverage",
                       return_value={"status": "SOURCE_COVERED", "unassigned": []}):
                rc = _route(cli, args, config, state, parser)
            results[idx] = rc
        except Exception as exc:
            errors.append(f"thread-{idx}: {exc}")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        threads = [
            threading.Thread(target=worker, args=(i, tmppath))
            for i in range(N_THREADS)
        ]
        t0 = time.monotonic()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        elapsed = time.monotonic() - t0

    all_completed = all(r is not None for r in results)

    return {
        "benchmark": "concurrent_sessions",
        "n_threads": N_THREADS,
        "total_seconds": round(elapsed, 4),
        "all_completed": all_completed,
        "errors": errors,
        "passed": all_completed and not errors,
    }


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def run_performance_benchmark(output_dir) -> dict:
    """Run all Phase 10 performance benchmarks and write performance_report.json."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    results = {}
    runner_errors = []

    for name, fn in [
        ("freeform_routing_throughput", _run_routing_throughput),
        ("ledger_append_throughput", _run_ledger_append_throughput),
        ("cache_effectiveness", _run_cache_effectiveness),
        ("concurrent_sessions", _run_concurrent_sessions),
    ]:
        try:
            results[name] = fn(output_dir)
        except Exception as exc:
            results[name] = {"benchmark": name, "passed": False, "error": str(exc)}
            runner_errors.append(f"{name}: {exc}")

    total = len(results)
    passed_count = sum(1 for r in results.values() if r.get("passed"))

    report = {
        "schema": "urace-benchmark-performance-v1",
        "generated_at": int(time.time()),
        "benchmarks": results,
        "runner_errors": runner_errors,
        "summary": {
            "total": total,
            "passed": passed_count,
            "failed": total - passed_count,
            "pass_rate": round(passed_count / total, 4) if total else 0.0,
        },
    }

    report_path = output_dir / "performance_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
