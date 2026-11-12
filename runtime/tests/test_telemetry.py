"""Tests for the optional OpenTelemetry bridge in urace/telemetry.py.

Verifies that:
1. emit_cycle_span is a no-op when opentelemetry is not installed or not configured
2. The module imports cleanly without crashing
3. The function signature accepts the expected parameters
4. When a mock tracer is injected, cycle attributes are set correctly
"""
import unittest
from unittest.mock import MagicMock, patch


class TelemetryNoOpTests(unittest.TestCase):
    """When OTEL is not configured, emit_cycle_span must not raise."""

    def test_import_succeeds(self):
        import urace.telemetry  # noqa: F401

    def test_emit_cycle_span_no_op_when_disabled(self):
        from urace.telemetry import emit_cycle_span
        # Must not raise even with missing/wrong inputs
        emit_cycle_span(outcome="dormant", index=1)
        emit_cycle_span(outcome="active", index=2, product_id="p1", version=5)

    def test_emit_cycle_span_accepts_all_parameters(self):
        from urace.telemetry import emit_cycle_span
        emit_cycle_span(
            outcome="active",
            index=3,
            product_id="test-product",
            cycles_total=10,
            version=7,
            cache_hits=4,
            executor_calls=12,
        )

    def test_emit_cycle_span_no_op_when_otel_disabled_env(self):
        import os
        with patch.dict(os.environ, {"OTEL_SDK_DISABLED": "true"}):
            # Reimport to trigger _init() with env set — but since module is cached,
            # we just verify the function doesn't crash when called.
            from urace.telemetry import emit_cycle_span
            emit_cycle_span(outcome="dormant", index=1)


class TelemetryWithMockTracerTests(unittest.TestCase):
    """When a tracer is injected, cycle span attributes must be set."""

    def test_span_attributes_set_when_tracer_active(self):
        import urace.telemetry as tel

        mock_span = MagicMock()
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_span)
        mock_ctx.__exit__ = MagicMock(return_value=False)
        mock_tracer = MagicMock()
        mock_tracer.start_as_current_span.return_value = mock_ctx

        original_tracer = tel._TRACER
        original_enabled = tel._ENABLED
        try:
            tel._TRACER = mock_tracer
            tel._ENABLED = True
            tel.emit_cycle_span(
                outcome="active",
                index=5,
                product_id="test-p",
                cycles_total=10,
                version=3,
                cache_hits=2,
                executor_calls=7,
            )
        finally:
            tel._TRACER = original_tracer
            tel._ENABLED = original_enabled

        mock_tracer.start_as_current_span.assert_called_once_with("urace.cycle")
        calls = {c.args[0]: c.args[1] for c in mock_span.set_attribute.call_args_list}
        self.assertEqual(calls["urace.cycle.index"], 5)
        self.assertEqual(calls["urace.cycle.outcome"], "active")
        self.assertEqual(calls["urace.state.version"], 3)
        self.assertEqual(calls["urace.executor.cache_hits"], 2)
        self.assertEqual(calls["urace.executor.calls"], 7)
        self.assertEqual(calls["urace.product.id"], "test-p")

    def test_tracer_exception_does_not_propagate(self):
        """A crashing tracer must not crash the caller."""
        import urace.telemetry as tel

        mock_tracer = MagicMock()
        mock_tracer.start_as_current_span.side_effect = RuntimeError("tracer broken")

        original_tracer = tel._TRACER
        original_enabled = tel._ENABLED
        try:
            tel._TRACER = mock_tracer
            tel._ENABLED = True
            # Must not raise
            tel.emit_cycle_span(outcome="dormant", index=1)
        finally:
            tel._TRACER = original_tracer
            tel._ENABLED = original_enabled
