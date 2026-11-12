"""Optional OpenTelemetry bridge for URACE cycle events.

When opentelemetry-sdk is installed, cycle events are emitted as OTLP spans
and flow to any configured backend (Jaeger, Datadog, Honeycomb, Grafana Tempo,
AWS X-Ray, etc.) via standard OTLP.

When not installed, all calls are no-ops with zero overhead.

Configure via environment:
  OTEL_EXPORTER_OTLP_ENDPOINT  — e.g. http://localhost:4317 (gRPC)
  OTEL_SERVICE_NAME            — defaults to "urace"
  OTEL_SDK_DISABLED            — set to "true" to suppress all telemetry

Usage:
  from urace.telemetry import emit_cycle_span
  emit_cycle_span(outcome="dormant", index=1, product_id="my-product")
"""
from __future__ import annotations

import os

_TRACER = None
_ENABLED = False


def _init() -> None:
    global _TRACER, _ENABLED
    if os.environ.get("OTEL_SDK_DISABLED", "").lower() == "true":
        return
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

        endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
        if not endpoint:
            return

        provider = TracerProvider()
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
        trace.set_tracer_provider(provider)
        _TRACER = trace.get_tracer("urace", schema_url="https://opentelemetry.io/schemas/1.21.0")
        _ENABLED = True
    except ImportError:
        pass


_init()


def emit_cycle_span(
    outcome: str,
    index: int,
    product_id: str | None = None,
    cycles_total: int = 0,
    version: int = 0,
    cache_hits: int = 0,
    executor_calls: int = 0,
) -> None:
    """Emit one OTLP span per daemon cycle. No-op when otel is not installed."""
    if not _ENABLED or _TRACER is None:
        return
    try:
        with _TRACER.start_as_current_span("urace.cycle") as span:
            span.set_attribute("urace.cycle.index", index)
            span.set_attribute("urace.cycle.outcome", outcome)
            span.set_attribute("urace.cycle.cycles_total", cycles_total)
            span.set_attribute("urace.state.version", version)
            span.set_attribute("urace.executor.cache_hits", cache_hits)
            span.set_attribute("urace.executor.calls", executor_calls)
            if product_id:
                span.set_attribute("urace.product.id", product_id)
    except Exception:
        pass
