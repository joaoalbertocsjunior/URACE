# Copyright 2024 URACE Contributors
# Concept adapted from mesh-llm/src/mesh_identity.rs (Apache 2.0)
from __future__ import annotations
import hashlib
import os
import pathlib
import threading
import uuid

_IDENTITY_LOCK = threading.Lock()

def generate_mesh_id() -> str:
    """Return a new random mesh ID in the form 'mesh-<hex32>'."""
    return 'mesh-' + os.urandom(16).hex()

def get_or_create_mesh_id(state_dir: str | pathlib.Path) -> str:
    """Return the node's stable mesh ID, creating one on first call.

    The ID is persisted at <state_dir>/mesh_id.txt so it survives restarts.
    """
    path = pathlib.Path(state_dir) / 'mesh_id.txt'
    with _IDENTITY_LOCK:
        if path.exists():
            mid = path.read_text().strip()
            if mid.startswith('mesh-') and len(mid) == 37:
                return mid
        mid = generate_mesh_id()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(mid)
        return mid
