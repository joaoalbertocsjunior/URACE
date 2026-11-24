"""Event bus shim — implementation lives in sources_lib.events.EventBus."""
from sources_lib.events import EventBus

_BUS = EventBus()

__all__ = ["EventBus", "_BUS"]
