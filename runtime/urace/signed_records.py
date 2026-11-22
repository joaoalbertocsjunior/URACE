# Copyright 2024 URACE Contributors
# Concept adapted from mesh-llm/src/signed_records.rs (Apache 2.0)
from __future__ import annotations
import dataclasses
import hashlib
import hmac
import json
import os
import pathlib
import threading
import time
from typing import Any

@dataclasses.dataclass
class SignedRecord:
    peer_id: str
    payload: bytes
    seq: int
    signature: bytes
    signed_at: float

def _derive_key(peer_id: str, secret: bytes) -> bytes:
    return hmac.new(secret, peer_id.encode(), hashlib.sha256).digest()

def sign_node_record(peer_id: str, payload: bytes, seq: int,
                     key: bytes) -> SignedRecord:
    """Sign *payload* with HMAC-SHA256 keyed by *key*."""
    msg = peer_id.encode() + seq.to_bytes(8, 'big') + payload
    sig = hmac.new(key, msg, hashlib.sha256).digest()
    return SignedRecord(peer_id=peer_id, payload=payload, seq=seq,
                        signature=sig, signed_at=time.time())

def verify_node_record(record: SignedRecord, key: bytes) -> bool:
    """Return True iff the record's HMAC-SHA256 signature is valid."""
    msg = record.peer_id.encode() + record.seq.to_bytes(8, 'big') + record.payload
    expected = hmac.new(key, msg, hashlib.sha256).digest()
    return hmac.compare_digest(expected, record.signature)

_IDENTITY_LOCK = threading.Lock()

def persist_node_identity(state_dir: str | pathlib.Path,
                          peer_id: str) -> bytes:
    """Return (and persist) a stable secret key for *peer_id*.

    Creates a new 32-byte random key on first call; subsequent calls return
    the same key from disk.  Never returns the peer_id itself as the key.
    """
    path = pathlib.Path(state_dir) / 'node_identity.key'
    with _IDENTITY_LOCK:
        if path.exists():
            raw = path.read_bytes()
            if len(raw) == 32:
                return raw
        key = os.urandom(32)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(key)
        return key
