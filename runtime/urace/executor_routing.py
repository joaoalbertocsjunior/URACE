from __future__ import annotations

import copy
import os
import re
import statistics
from datetime import datetime, timedelta, timezone
from typing import Any


class ExecutorUnavailable(RuntimeError):
    """A retryable provider-capacity condition, distinct from task failure."""

    def __init__(self, category: str, retry_at: str | None, detail: str = ""):
        self.category = category
        self.retry_at = retry_at
        self.detail = detail[-500:]
        schedule = f" until {retry_at}" if retry_at else " with scheduled backoff"
        condition = {
            "LOCAL_TRANSPORT_CEILING": "Local Executor transport ceiling reached",
            "EXECUTION_ENVIRONMENT_UNAVAILABLE": "Executor execution environment unavailable",
        }.get(category, "Executor capacity unavailable")
        super().__init__(f"{condition}{schedule}")


SUPPORTED_ADAPTERS = {"codex-cli", "claude-cli", "script", "http", "mcp"}
EXECUTION_ENVIRONMENT_FAILURES = (
    "bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted",
    "sandbox could not initialize",
    "workspace sandbox failed before",
    "workspace execution sandbox failed before",
)
AUTH_FAILURE_MARKERS = (
    "401",
    "unauthorized",
    "not authenticated",
    "invalid api key",
    "authentication failed",
    "login required",
    "not supported when using codex with a chatgpt account",
    "model is not supported",
)
TRANSIENT_NETWORK_MARKERS = (
    "cf-ray:",
    "stream disconnected",
    "connection reset by peer",
    "upstream connect error",
    "upstream disconnect",
    "502 bad gateway",
    "503 service unavailable",
    "504 gateway timeout",
)


def classify_execution_environment(detail: str, settings: dict[str, Any]) -> ExecutorUnavailable | None:
    if not any(marker.lower() in detail.lower() for marker in EXECUTION_ENVIRONMENT_FAILURES):
        return None
    retry_at = datetime.fromtimestamp(
        datetime.now(timezone.utc).timestamp() + float(settings.get("capacity_fallback_seconds", 3600)), timezone.utc
    ).isoformat()
    return ExecutorUnavailable("EXECUTION_ENVIRONMENT_UNAVAILABLE", retry_at, detail)


def classify_auth_failure(detail: str, settings: dict[str, Any]) -> ExecutorUnavailable | None:
    """Detect permanent or configuration-level auth/model failures; back off without retrying."""
    if not any(marker in detail.lower() for marker in AUTH_FAILURE_MARKERS):
        return None
    retry_at = datetime.fromtimestamp(
        datetime.now(timezone.utc).timestamp() + float(settings.get("capacity_fallback_seconds", 3600)), timezone.utc
    ).isoformat()
    return ExecutorUnavailable("EXECUTOR_AUTH_UNAVAILABLE", retry_at, detail)


def classify_transient_network_failure(detail: str, settings: dict[str, Any]) -> ExecutorUnavailable | None:
    """Detect transient infrastructure disconnects; apply short backoff, do not conflate with auth or capacity failures."""
    if not any(marker in detail.lower() for marker in TRANSIENT_NETWORK_MARKERS):
        return None
    retry_at = datetime.fromtimestamp(
        datetime.now(timezone.utc).timestamp() + float(settings.get("transient_network_backoff_seconds", 60)), timezone.utc
    ).isoformat()
    return ExecutorUnavailable("EXECUTOR_TRANSIENT_NETWORK", retry_at, detail)


def _env_auto_providers() -> list[dict[str, Any]]:
    """Synthesize provider entries from well-known environment variables (zero-config path)."""
    providers: list[dict[str, Any]] = []
    caps = ["discovery", "planning", "mutation", "evaluation", "execution"]
    if os.environ.get("ANTHROPIC_API_KEY"):
        providers.append({"id": "env-claude", "adapter": "codex-cli", "command": "claude",
                          "priority": 90, "capabilities": caps, "_source": "ANTHROPIC_API_KEY"})
    if os.environ.get("OPENAI_API_KEY"):
        providers.append({"id": "env-openai", "adapter": "codex-cli", "command": "codex",
                          "priority": 80, "capabilities": caps, "_source": "OPENAI_API_KEY"})
    return providers


def provider_definitions(settings: dict[str, Any], capability: str | None = None) -> list[dict[str, Any]]:
    providers = settings.get("providers")
    if not providers:
        providers = [{"id": "primary", "adapter": "codex-cli", "command": settings.get("command", "codex"), "priority": 100, "capabilities": ["discovery", "planning", "mutation", "evaluation", "execution"]}]
        # Supplement with env-var auto-detected providers for zero-config operation
        providers = providers + [p for p in _env_auto_providers() if p["id"] not in {x["id"] for x in providers}]
    def rank(item: dict[str, Any]) -> tuple[int, int, str]:
        capability_priority = int(item.get("capability_priorities", {}).get(capability, item.get("priority", 0))) if capability else int(item.get("priority", 0))
        return (-capability_priority, -int(item.get("priority", 0)), str(item.get("id", "")))
    # Legacy provider entries inherit the single-adapter capability set.
    # An explicitly empty list still means that no capability is available.
    normalized = []
    for item in providers:
        if not item.get("enabled", True):
            continue
        provider = dict(item)
        provider.setdefault("capabilities", ["discovery", "planning", "mutation", "evaluation", "execution"])
        normalized.append(provider)
    return sorted(normalized, key=rank)


def _provider_timing_error(status: dict[str, Any]) -> str | None:
    """Validate cached clocks without changing provider history or budgets."""
    def invalid(value: Any) -> bool:
        try:
            return datetime.fromisoformat(value).utcoffset() is None
        except (TypeError, ValueError, OverflowError):
            return True
    for field in ("retry_at", "cooldown_until"):
        if status.get(field) is not None and invalid(status[field]):
            return field
    attempts = status.get("attempt_history", [])
    if not isinstance(attempts, list) or any(invalid(value) for value in attempts):
        return "attempt_history"
    completions = status.get("completion_history", [])
    if not isinstance(completions, list) or any(
        not isinstance(event, dict) or invalid(event.get("at")) for event in completions
    ):
        return "completion_history"
    return None


def routed_provider_definitions(settings: dict[str, Any], pool_state: dict[str, Any], capability: str) -> list[dict[str, Any]]:
    """Prefer fit, then distribute materially equivalent work using recent accepted transports."""
    providers = provider_definitions(settings, capability)
    compatible = [item for item in providers if capability in item.get("capabilities", [])]
    if not compatible:
        return providers
    score = lambda item: int(item.get("capability_priorities", {}).get(capability, item.get("priority", 0)))
    best = max(score(item) for item in compatible)
    tolerance = max(0, int(settings.get("routing_suitability_tolerance", 10)))
    window = max(60, int(settings.get("routing_balance_window_seconds", 86400)))
    cutoff = datetime.now(timezone.utc).timestamp() - window
    def recent_successes(item: dict[str, Any]) -> int:
        status = pool_state.get(item["id"], {})
        history = [] if _provider_timing_error(status) else status.get("completion_history", [])
        return sum(1 for event in history if event.get("capability") == capability and datetime.fromisoformat(event["at"]).timestamp() >= cutoff)
    def observed_elapsed(item: dict[str, Any]) -> float | None:
        status = pool_state.get(item["id"], {})
        history = [] if _provider_timing_error(status) else status.get("completion_history", [])
        values = [float(event["elapsed_seconds"]) for event in history if event.get("capability") == capability and event.get("elapsed_seconds") is not None and datetime.fromisoformat(event["at"]).timestamp() >= cutoff]
        return statistics.median(values[-10:]) if values else None
    near = [item for item in compatible if best - score(item) <= tolerance]
    distant = [item for item in compatible if item not in near]
    observed = [observed_elapsed(item) for item in near]
    fastest = min((value for value in observed if value is not None), default=None)
    ratio = max(1.0, float(settings.get("routing_efficiency_tolerance_ratio", 2.5)))
    absolute_caps = settings.get("routing_max_elapsed_seconds", {})
    absolute_cap = float(absolute_caps.get(capability, float("inf"))) if isinstance(absolute_caps, dict) else float("inf")
    def inefficient(item: dict[str, Any]) -> bool:
        elapsed = observed_elapsed(item)
        return elapsed is not None and (elapsed > absolute_cap or (fastest is not None and elapsed > fastest * ratio))
    near.sort(key=lambda item: (inefficient(item), recent_successes(item), -score(item), observed_elapsed(item) or 0.0, -int(item.get("priority", 0)), str(item.get("id", ""))))
    distant.sort(key=lambda item: (-score(item), -int(item.get("priority", 0)), str(item.get("id", ""))))
    compatible_ids = {item["id"] for item in compatible}
    return near + distant + [item for item in providers if item["id"] not in compatible_ids]


def provider_settings(settings: dict[str, Any], provider: dict[str, Any]) -> dict[str, Any]:
    merged = {key: value for key, value in settings.items() if key != "providers"}
    merged.update({key: value for key, value in provider.items() if key not in {"id", "priority", "capabilities", "capability_priorities", "enabled"}})
    merged.update(settings.get("native_options", {}).get(str(provider.get("adapter","")).removesuffix("-cli"),{}))
    merged.update(settings.get("native_options", {}).get(provider.get("id"), {}))
    return merged


def configured_transport_limit(provider: dict[str, Any], settings: dict[str, Any], provider_key: str, fallback_key: str, fallback: int) -> int | None:
    """Resolve a transport ceiling from provider config, then executor config, then built-in fallback.

    To raise or remove limits in urace config.json:
      executor.max_executor_calls_per_24h (default 2)  — global daily ceiling across all providers
      executor.max_executor_calls_per_30d (default 12) — global monthly ceiling
      executor.providers[n].max_calls_per_24h          — per-provider override
      executor.providers[n].max_calls_per_30d          — per-provider override
      executor.healthcheck_timeout_seconds (default 10)— provider reachability timeout
      executor.max_tokens_per_cycle_warn (default 50000)— token warning threshold (not a hard cap)
    Set any ceiling to null to remove it entirely.
    """
    value = provider[provider_key] if provider_key in provider else settings.get(fallback_key, fallback)
    return None if value is None else int(value)


def _transport_receipt(provider_id: str, metadata: Any) -> dict[str, Any]:
    """Retain exactly what an attempted transport reported, including no report."""
    return {"provider_id": provider_id, "usage": copy.deepcopy(metadata) if isinstance(metadata, dict) else None}


def _aggregate_transport_usage(receipts: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not receipts:
        return None
    if len(receipts) == 1:
        usage = receipts[0]["usage"]
        if usage is None:
            return None
        return copy.deepcopy(usage)
    result: dict[str, Any] = {
        "source": "aggregated provider transport receipts",
        "usage_provenance": "AGGREGATED_PARTIAL" if any(item["usage"] is None for item in receipts) else "AGGREGATED_COMPLETE",
        "reported_cost_usd": None,
        "transport_usage": copy.deepcopy(receipts),
    }
    for metric in ("input_tokens", "cached_input_tokens", "output_tokens"):
        values = [item["usage"].get(metric) if isinstance(item["usage"], dict) else None for item in receipts]
        result[metric] = sum(values) if all(isinstance(value, int) and not isinstance(value, bool) and value >= 0 for value in values) else None
    return result


def _route_record(pool_state: dict[str, Any], attempted: list[str], receipts: list[dict[str, Any]], **fields: Any) -> None:
    pool_state["last_route"] = {**fields, "attempted": list(attempted), "transport_usage": copy.deepcopy(receipts)}


def classify_unavailability(detail: str, settings: dict[str, Any] | None = None) -> ExecutorUnavailable | None:
    lowered = detail.lower()
    if not any(marker in lowered for marker in ("usage limit", "rate limit", "quota exceeded", "too many requests", "credits exhausted", "hit your limit")):
        return None
    settings = settings or {}
    mode = str(settings.get("capacity_retry_mode", "automatic")).lower()
    delay = max(0.0, float(settings.get("capacity_retry_delay_ms", 60000))) / 1000
    fallback = max(60.0, float(settings.get("capacity_fallback_seconds", 3600)))
    retry_at = None
    match = re.search(r"(?:try again at|rate limit resets on|resets on)\s+([^\n]+)", detail, re.IGNORECASE)
    if mode in {"automatic", "dynamic"} and match:
        value = re.sub(r"(?<=\d)(st|nd|rd|th)\b", "", match.group(1)).strip().rstrip(".")
        for pattern in ("%b %d, %Y %I:%M %p", "%B %d, %Y %I:%M %p"):
            try:
                local = datetime.strptime(value, pattern).replace(tzinfo=timezone.utc)
                retry_at = (local + timedelta(seconds=delay)).astimezone(timezone.utc).isoformat()
                break
            except ValueError:
                continue
        if retry_at is None:
            time_match = re.match(r"(\d{1,2}:\d{2}\s*[AP]M)\b", value, re.IGNORECASE)
            if time_match:
                parsed = datetime.strptime(time_match.group(1).upper(), "%I:%M %p").time()
                local_now = datetime.now().astimezone()
                local = datetime.combine(local_now.date(), parsed, local_now.tzinfo)
                if local <= local_now: local += timedelta(days=1)
                retry_at = (local + timedelta(seconds=delay)).astimezone(timezone.utc).isoformat()
    if retry_at is None:
        retry_at = (datetime.now(timezone.utc) + timedelta(seconds=fallback)).isoformat()
    return ExecutorUnavailable("PROVIDER_CAPACITY", retry_at, detail)
