"""Structured logging configuration for the URACE runtime.

Usage::

    from urace.logging_config import configure_logging, get_logger
    _log = get_logger(__name__)
    _log.warning("state load failed: %s", exc)

Call ``configure_logging(config)`` once at process startup (CLI entry point).
If never called, the standard library's ``lastResort`` handler (stderr WARNING+)
remains active so diagnostic messages surface even without explicit configuration.

Event-bus integration (Phase 1A):
    The bus-subscriber wired in ``_wire_bus_to_logger()`` converts every bus
    event to a log record so all runtime events flow through a single point.
    Per-component enable/disable is enforced here before hitting the logger.
"""
from __future__ import annotations

import json
import logging
import logging.handlers
import sys
import threading
from pathlib import Path
from typing import Any

_CONFIGURED = False
_CONFIG_LOCK = threading.Lock()

# Component name → Python logger name mapping.
_COMPONENT_LOGGERS: dict[str, str] = {
    'source':    'urace.source_adapters',
    'm2m':       'urace.api',
    'config':    'urace.config',
    'lifecycle': 'urace.lifecycle',
    'cycle':     'urace.cli_cycle',
    'cost':      'urace.cost',
    'exchange':  'urace.peer_exchange',
    'executor':  'urace.executor',
    'security':  'urace.security',
    'audit':     'urace.audit',
}

# Components that cannot be silenced regardless of config.
_ALWAYS_ON = frozenset({'security', 'audit'})


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


def _level_from_str(level: str) -> int:
    return getattr(logging, level.upper(), logging.WARNING)


def configure_logging(
    config: dict | None = None,
    *,
    level: str | int = "WARNING",
    json_format: bool = False,
    file_path: str = "",
    max_bytes: int = 10_485_760,
    backup_count: int = 5,
    stream=None,
) -> None:
    """Install handlers on the root logger.

    When *config* is supplied the ``logging`` section drives all parameters.
    Keyword arguments act as fallbacks when config is absent.

    Safe to call multiple times; subsequent calls are no-ops.
    """
    global _CONFIGURED
    with _CONFIG_LOCK:
        if _CONFIGURED:
            return

        log_cfg: dict[str, Any] = {}
        if config is not None:
            log_cfg = config.get('logging', {})

        root_level = _level_from_str(str(log_cfg.get('level', level)))
        use_json = bool(log_cfg.get('format', 'json' if json_format else 'text') == 'json')
        log_file = str(log_cfg.get('file', file_path) or '')
        rot_max = int(log_cfg.get('max_bytes', max_bytes))
        rot_bak = int(log_cfg.get('backup_count', backup_count))

        fmt = JsonFormatter() if use_json else logging.Formatter(
            "%(levelname)s [%(name)s] %(message)s"
        )

        root = logging.getLogger()
        # Stderr handler always present.
        stderr_h = logging.StreamHandler(stream or sys.stderr)
        stderr_h.setFormatter(fmt)
        root.addHandler(stderr_h)

        # Optional rotating file handler.
        if log_file:
            try:
                Path(log_file).parent.mkdir(parents=True, exist_ok=True)
                file_h = logging.handlers.RotatingFileHandler(
                    log_file, maxBytes=rot_max, backupCount=rot_bak, encoding='utf-8'
                )
                file_h.setFormatter(JsonFormatter())
                root.addHandler(file_h)
            except OSError as exc:
                logging.getLogger(__name__).warning(
                    "logging: could not open log file %r: %s", log_file, exc
                )

        root.setLevel(root_level)

        # Apply per-component level overrides.
        components = log_cfg.get('components', {})
        for comp, logger_name in _COMPONENT_LOGGERS.items():
            enabled = components.get(comp, True)
            comp_logger = logging.getLogger(logger_name)
            if comp in _ALWAYS_ON or enabled:
                comp_logger.setLevel(root_level)
            else:
                comp_logger.setLevel(logging.CRITICAL + 1)  # effectively silent

        _CONFIGURED = True
        _wire_bus_to_logger(config)


def _wire_bus_to_logger(config: dict | None) -> None:
    """Subscribe a handler to every bus topic so events flow through logging.

    This is best-effort: if the event bus is not available (e.g. in unit tests
    that import logging_config before the bus is set up) the wiring is skipped.
    """
    try:
        from .event_bus import _BUS
    except ImportError:
        return

    log_cfg: dict[str, Any] = (config or {}).get('logging', {})
    components_cfg = log_cfg.get('components', {})

    # Topic prefix → (component name, log level)
    _TOPIC_MAP = {
        'source.':    ('source',    logging.DEBUG),
        'm2m.':       ('m2m',       logging.INFO),
        'config.':    ('config',    logging.INFO),
        'lifecycle.': ('lifecycle', logging.INFO),
        'cycle.':     ('cycle',     logging.INFO),
        'cost.':      ('cost',      logging.DEBUG),
        'ledger.':    ('cost',      logging.DEBUG),
        'exchange.':  ('exchange',  logging.INFO),
        'feature.':   ('exchange',  logging.INFO),
        'executor.':  ('executor',  logging.DEBUG),
        'security.':  ('security',  logging.WARNING),
        'audit.':     ('audit',     logging.INFO),
    }

    def _make_handler(component: str, lvl: int):
        logger = logging.getLogger(_COMPONENT_LOGGERS.get(component, f'urace.{component}'))

        def _handler(*, _topic: str = '', **payload: Any) -> None:
            enabled = components_cfg.get(component, True)
            if not enabled and component not in _ALWAYS_ON:
                return
            logger.log(lvl, "bus:%s %s", _topic, json.dumps(payload, default=str))

        return _handler

    # Keep strong refs so WeakMethod-based bus doesn't GC them.
    _BUS._logging_handlers = []  # type: ignore[attr-defined]
    for prefix, (comp, lvl) in _TOPIC_MAP.items():
        h = _make_handler(comp, lvl)
        _BUS._logging_handlers.append(h)
        # Subscribe to a wildcard-ish set of common topics.
        for suffix in ('started', 'completed', 'failed', 'added', 'removed',
                       'earned', 'spent', 'borrowed', 'minted', 'changed',
                       'written', 'read', 'synced', 'probed', 'rejected',
                       'committed', 'requested', 'responded', 'detected',
                       # Protocol v2 source act path
                       'acted', 'act_failed', 'act_denied'):
            topic = prefix.rstrip('.') + '.' + suffix
            _BUS.subscribe(topic, h)

    # source.acted and source.act_failed always log at INFO/WARNING regardless of component config
    try:
        _act_logger = logging.getLogger(_COMPONENT_LOGGERS['source'])

        def _act_audit_handler(*, _topic: str = '', **payload: Any) -> None:
            if 'act_failed' in _topic or 'act_denied' in _topic:
                _act_logger.warning("bus:%s %s", _topic, json.dumps(payload, default=str))
            else:
                _act_logger.info("bus:%s %s", _topic, json.dumps(payload, default=str))

        _BUS._logging_handlers.append(_act_audit_handler)  # type: ignore[attr-defined]
        for _t in ('source.acted', 'source.act_failed'):
            _BUS.subscribe(_t, _act_audit_handler)
    except Exception:
        pass


def reconfigure_component(component: str, enabled: bool) -> None:
    """Enable or disable a logging component at runtime without restart.

    Security and audit components cannot be disabled.
    """
    if component in _ALWAYS_ON:
        return
    logger_name = _COMPONENT_LOGGERS.get(component, f'urace.{component}')
    comp_logger = logging.getLogger(logger_name)
    if enabled:
        comp_logger.setLevel(logging.getLogger().level)
    else:
        comp_logger.setLevel(logging.CRITICAL + 1)


def get_logger(name: str) -> logging.Logger:
    """Return a module-level logger.  Thin wrapper kept for uniform imports."""
    return logging.getLogger(name)
