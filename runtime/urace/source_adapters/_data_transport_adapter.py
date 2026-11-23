"""DataTransportAdapter — wraps data_transport.py as a sources-lib BaseSourceAdapter.

Translates between sources-lib SourceRecord fields and data_transport.py's
expected record/config format, mapping TransportError variants to the
appropriate sources-lib exceptions.
"""
from __future__ import annotations

from typing import Any

from sources_lib import BaseSourceAdapter, SourceRecord
from sources_lib.adapter import SourceActDeniedError, SourceError, SourceUnavailableError

from urace import data_transport
from urace.data_transport import TransportError


def _urace_record(record: SourceRecord) -> dict[str, Any]:
    """Build the data_transport-style record dict from a SourceRecord."""
    cfg = record.config
    return {
        "id": record.id,
        "adapter_kind": cfg.get("adapter_kind", "json"),
        "connection_metadata": cfg.get("connection_metadata", {}),
        "schema_hint": cfg.get("schema_hint", ""),
    }


def _urace_config(record: SourceRecord) -> dict[str, Any]:
    """Build the data_transport-style config dict from a SourceRecord."""
    return {"data_limits": record.config.get("data_limits", {})}


class DataTransportAdapter(BaseSourceAdapter):
    """sources-lib adapter that delegates to data_transport.py for local JSON/CSV/SQLite I/O."""

    config_schema: dict[str, Any] = {}
    actions: list[str] = ["push"]

    def verify(self, record: SourceRecord, config: dict[str, Any]) -> dict[str, Any]:
        """Call data_transport.verify and return its result dict."""
        try:
            return data_transport.verify(_urace_record(record))
        except TransportError as exc:
            if str(exc) == "ADAPTER_REQUIRED":
                raise SourceUnavailableError(str(exc)) from exc
            raise SourceError(str(exc)) from exc
        except PermissionError as exc:
            raise SourceActDeniedError(str(exc)) from exc

    def sync(self, record: SourceRecord, config: dict[str, Any]) -> list[dict[str, Any]]:
        """Call data_transport.read and return the row list."""
        try:
            rows, _data = data_transport.read(_urace_record(record), _urace_config(record))
            return rows
        except TransportError as exc:
            if str(exc) == "ADAPTER_REQUIRED":
                raise SourceUnavailableError(str(exc)) from exc
            raise SourceError(str(exc)) from exc
        except PermissionError as exc:
            raise SourceActDeniedError(str(exc)) from exc

    def act(
        self,
        record: SourceRecord,
        config: dict[str, Any],
        action: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Perform a named action. Only 'push' is supported."""
        if action != "push":
            raise SourceActDeniedError(
                f"Action '{action}' not supported by DataTransportAdapter"
            )
        try:
            return data_transport.push(
                _urace_record(record),
                payload.get("rows", []),
                _urace_config(record),
            )
        except TransportError as exc:
            if str(exc) == "ADAPTER_REQUIRED":
                raise SourceUnavailableError(str(exc)) from exc
            raise SourceError(str(exc)) from exc
        except PermissionError as exc:
            raise SourceActDeniedError(str(exc)) from exc

    def supported_actions(self, record: SourceRecord, config: dict[str, Any]) -> list[str]:
        """Return the list of supported action names."""
        return ["push"]
