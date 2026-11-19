"""Optional P2P dependency capability registry.

Instead of scattered try/except import blocks throughout peer_exchange.py
and peer_discovery.py, this module probes availability once at import time
and exposes named flags.  Code that needs to branch on optional deps imports
from here rather than repeating the probe.

Usage::

    from .p2p_capabilities import CAPS

    if CAPS.zeroconf:
        from zeroconf import Zeroconf, ServiceBrowser
        ...
    else:
        raise ValueError('LAN discovery requires optional python-zeroconf')

    if CAPS.aesgcm:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        key = AESGCM(raw_key).encrypt(nonce, data, aad)
    else:
        key = data   # fallback: store plaintext
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field


def _available(module: str) -> bool:
    try:
        importlib.import_module(module)
        return True
    except ImportError:
        return False


@dataclass(frozen=True)
class _Caps:
    """Read-only snapshot of which optional deps are present."""
    zeroconf: bool = field(default_factory=lambda: _available('zeroconf'))
    kademlia: bool = field(default_factory=lambda: _available('kademlia'))
    aesgcm: bool = field(default_factory=lambda: _available('cryptography'))
    evm: bool = field(default_factory=lambda: _available('eth_account'))
    opentelemetry: bool = field(default_factory=lambda: _available('opentelemetry'))
    openpyxl: bool = field(default_factory=lambda: _available('openpyxl'))
    pillow: bool = field(default_factory=lambda: _available('PIL'))


# Singleton — evaluated once per process.
CAPS: _Caps = _Caps()
