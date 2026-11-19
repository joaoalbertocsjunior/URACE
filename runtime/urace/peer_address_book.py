"""F7-lite: gossip-based peer address book mapping peer_id → [endpoints]."""
from __future__ import annotations
import json
import os
import tempfile
import threading
from collections import OrderedDict
from pathlib import Path

MAX_PEERS = 500
MAX_URLS_PER_PEER = 5

_LOCK = threading.Lock()


class PeerAddressBook:
    """Persistent peer_id → [endpoint] mapping. Max 500 peers, 5 URLs each."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        # OrderedDict: most-recently-used peer first
        self._book: OrderedDict[str, list[str]] = OrderedDict()
        self._load()

    def _load(self) -> None:
        try:
            if self.path.exists():
                raw = json.loads(self.path.read_text())
                if isinstance(raw, dict):
                    for pid, urls in raw.items():
                        if isinstance(pid, str) and isinstance(urls, list):
                            cleaned = [u for u in urls if isinstance(u, str)][:MAX_URLS_PER_PEER]
                            if cleaned:
                                self._book[pid] = cleaned
        except Exception as _e:
            import logging as _lg; _lg.getLogger(__name__).warning('PeerAddressBook load failed, starting empty: %s', _e)
            self._book = OrderedDict()

    def record(self, peer_id: str, endpoint: str) -> None:
        """Record a working endpoint for peer_id. Most-recently-used first."""
        if not isinstance(peer_id, str) or not peer_id:
            return
        if not isinstance(endpoint, str) or not endpoint:
            return
        with _LOCK:
            if peer_id in self._book:
                urls = self._book.pop(peer_id)
                # Move endpoint to front, deduplicate
                urls = [endpoint] + [u for u in urls if u != endpoint]
                urls = urls[:MAX_URLS_PER_PEER]
            else:
                urls = [endpoint]
                # Evict LRU (last) entry if at capacity
                while len(self._book) >= MAX_PEERS:
                    self._book.popitem(last=True)
            self._book[peer_id] = urls
            self._book.move_to_end(peer_id, last=False)

    def endpoints_for(self, peer_id: str) -> list[str]:
        """Return known endpoints for peer_id, best-first."""
        with _LOCK:
            return list(self._book.get(peer_id, []))

    def all_entries(self) -> dict[str, list[str]]:
        """Return full book for gossip."""
        with _LOCK:
            return {pid: list(urls) for pid, urls in self._book.items()}

    def merge(self, remote_book: dict[str, list[str]]) -> None:
        """Merge entries from a remote peer's book. Never evicts local entries."""
        if not isinstance(remote_book, dict):
            return
        with _LOCK:
            set(self._book.keys())
            for pid, urls in remote_book.items():
                if not isinstance(pid, str) or not isinstance(urls, list):
                    continue
                cleaned = [u for u in urls if isinstance(u, str)][:MAX_URLS_PER_PEER]
                if not cleaned:
                    continue
                if pid in self._book:
                    # Append remote urls that we don't already have, preserve local order
                    existing = self._book[pid]
                    for u in cleaned:
                        if u not in existing:
                            existing.append(u)
                    self._book[pid] = existing[:MAX_URLS_PER_PEER]
                else:
                    # Only add new remote peers if below capacity, don't evict locals
                    if len(self._book) < MAX_PEERS:
                        self._book[pid] = cleaned

    def save(self) -> None:
        """Atomic write to self.path."""
        with _LOCK:
            data = {pid: list(urls) for pid, urls in self._book.items()}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix='.peer_address_book_')
        try:
            with os.fdopen(fd, 'w') as f:
                json.dump(data, f, separators=(',', ':'))
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, self.path)
            try:
                os.chmod(self.path, 0o600)
            except OSError:
                pass
        except Exception as _se:
            import logging as _lg; _lg.getLogger(__name__).warning('PeerAddressBook save failed: %s', _se)
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    def top_peers(self, n: int = 20) -> list[tuple[str, str]]:
        """Return (peer_id, best_endpoint) for n most recently seen peers."""
        with _LOCK:
            result = []
            for pid, urls in self._book.items():
                if urls:
                    result.append((pid, urls[0]))
                if len(result) >= n:
                    break
            return result


# Module-level singleton
_address_book: PeerAddressBook | None = None


def init_address_book(path: Path) -> PeerAddressBook:
    """Initialize module-level address book singleton."""
    global _address_book
    try:
        _address_book = PeerAddressBook(Path(path))
    except Exception:
        _address_book = None
    return _address_book


def get_address_book() -> PeerAddressBook | None:
    """Return module-level address book singleton, or None if not initialized."""
    return _address_book
