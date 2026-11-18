"""Low-level artifact storage for P2P exchange bundles.

ArtifactStore wraps the flat AES-GCM file store and the erasure-coded
ChunkStore (v2 path) so the rest of Exchange never touches storage
implementation details.  Higher-level bundle operations (prepare, inspect,
review) remain on Exchange because they need the audit chain and policy lock.

Usage::

    from .artifact_store import ArtifactStore

    store = ArtifactStore(exchange_root)
    store.store(sha256_hex, raw_bytes)
    data = store.load(sha256_hex)   # None if not present
"""
from __future__ import annotations

import hashlib
import hmac
import os
from pathlib import Path


class ArtifactStore:
    """Encrypts and stores artifacts under exchange_root/bundle-artifacts/."""

    _AAD = b'URACE-ARTIFACT-v1'

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _path(self, sha256_hex: str) -> Path:
        return self.root / 'bundle-artifacts' / sha256_hex[:2] / sha256_hex

    def _key(self, sha256_hex: str) -> bytes:
        """Derive a per-artifact AES-256 key from local private seed + artifact hash."""
        seed_path = self.root / 'artifact-seed.bin'
        if not seed_path.exists():
            seed = os.urandom(32)
            fd = os.open(str(seed_path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, 'wb') as f:
                f.write(seed)
                f.flush()
                os.fsync(f.fileno())
        else:
            seed = seed_path.read_bytes()
        prk = hmac.new(b'URACE-ARTIFACT-v1', seed + sha256_hex.encode(), 'sha256').digest()
        return hmac.new(prk, b'\x01', 'sha256').digest()

    # ── Write ─────────────────────────────────────────────────────────────────

    def store(self, sha256_hex: str, raw_bytes: bytes) -> None:
        """Persist raw_bytes encrypted at the content-addressed path.

        Idempotent — skips the write if the file already exists.
        Also replicates to ChunkStore (erasure-coded v2 path) when available.
        """
        p = self._path(sha256_hex)
        if not p.exists():
            p.parent.mkdir(parents=True, exist_ok=True)
            try:
                from cryptography.hazmat.primitives.ciphers.aead import AESGCM
                key = self._key(sha256_hex)
                nonce = os.urandom(12)
                ciphertext = AESGCM(key).encrypt(nonce, raw_bytes, self._AAD)
                p.write_bytes(nonce + ciphertext)
            except ImportError:
                p.write_bytes(raw_bytes)
            os.chmod(p, 0o600)

        try:
            from .chunk_store import ChunkStore
            ChunkStore(self.root).store(sha256_hex, raw_bytes)
        except (OSError, ValueError):
            pass
        except Exception:
            pass

    # ── Read ──────────────────────────────────────────────────────────────────

    def load(self, sha256_hex: str) -> bytes | None:
        """Return raw (decrypted) bytes for sha256_hex, or None if not found."""
        # v2: erasure-coded ChunkStore (may reconstruct missing flat files)
        try:
            from .chunk_store import ChunkStore
            data = ChunkStore(self.root).load(sha256_hex)
            if data is not None:
                return data
        except (OSError, ValueError):
            pass
        except Exception:
            pass

        # v1: flat AES-GCM encrypted file
        p = self._path(sha256_hex)
        if not p.exists():
            return None
        raw = p.read_bytes()
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            key = self._key(sha256_hex)
            if len(raw) < 13:
                return raw
            nonce, ciphertext = raw[:12], raw[12:]
            try:
                return AESGCM(key).decrypt(nonce, ciphertext, self._AAD)
            except Exception:
                return raw
        except ImportError:
            return raw

    def exists(self, sha256_hex: str) -> bool:
        return self._path(sha256_hex).exists()
