"""Structured logging configuration for the URACE runtime.

Usage::

    from urace.logging_config import get_logger
    _log = get_logger(__name__)
    _log.warning("state load failed: %s", exc)

Call ``configure_logging()`` once at process startup (CLI entry point) to
install handlers and set the root level.  If never called the standard
library's ``lastResort`` handler (stderr WARNING+) remains active so
diagnostic messages surface even without explicit configuration.
"""
from __future__ import annotations

import json
import logging
import sys
from typing import Any


class JsonFormatter(logging.Formatter):
    """Single-line JSON log records."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(
    level: str | int = "WARNING",
    *,
    json_format: bool = False,
    stream=None,
) -> None:
    """Install a stderr handler on the root logger.

    Safe to call multiple times; subsequent calls are no-ops unless
    *force=True* is desired in the future.
    """
    root = logging.getLogger()
    if root.handlers:
        return

    handler = logging.StreamHandler(stream or sys.stderr)
    if json_format:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(levelname)s [%(name)s] %(message)s")
        )
    root.addHandler(handler)
    root.setLevel(level)


def get_logger(name: str) -> logging.Logger:
    """Return a module-level logger.  Thin wrapper kept for uniform imports."""
    return logging.getLogger(name)
