"""Append-only P2P audit chain, extracted from Exchange.

AuditLedger owns audit.jsonl and the signed-audit sidecar for one exchange
directory.  Exchange delegates all audit chain operations here; other modules
receive a LedgerAdapter (or AuditLedger directly) and never import Exchange.

Thread/process safety: advisory flock on exchange.lock (same file as Exchange
and PolicyStore — shared root means shared lock).
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from contextlib import contextmanager
from pathlib import Path

try:
    import fcntl as _fcntl
    _HAS_FCNTL = True
except ImportError:
    _HAS_FCNTL = False

SCHEMA = 'urace-exchange-v2'


def _encoded(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def _digest(value: object) -> str:
    return hashlib.sha256(_encoded(value)).hexdigest()


class AuditLedger:
    """Append-only audit chain for one exchange directory.

    Implements LedgerAdapter's audit_rows / append_audit_row / event / load.
    ``load()`` is a no-op here (returns {}); Exchange overlays policy on top.
    The same instance is reused across calls — do not share across threads.
    """

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)

    # ── Lock ─────────────────────────────────────────────────────────────────

    @contextmanager
    def lock(self):
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.root.is_symlink():
            raise ValueError('Exchange directory cannot be a symlink')
        os.chmod(self.root, 0o700)
        with (self.root / 'exchange.lock').open('a') as f:
            if _HAS_FCNTL:
                _fcntl.flock(f, _fcntl.LOCK_EX)
            yield

    # ── Read ─────────────────────────────────────────────────────────────────

    def audit_rows(self) -> list[dict]:
        """Return all verified audit rows in chain order.

        Raises ValueError on integrity failure.
        """
        p = self.root / 'audit.jsonl'
        rows: list[dict] = []
        previous = '0' * 64
        if p.exists():
            for line in p.read_text().splitlines():
                row = json.loads(line)
                signed = {k: v for k, v in row.items() if k != 'sha256'}
                if row.get('previous') != previous or _digest(signed) != row.get('sha256'):
                    raise ValueError('Audit chain integrity failure')
                previous = row['sha256']
                rows.append(row)
        self._verify_audit_rows(rows)
        return rows

    def _verify_audit_rows(self, rows: list[dict]) -> None:
        if not rows:
            return
        from .signed_ledger import Ledger
        ledger = Ledger(self.root / 'signed-audit')
        if not ledger.root.exists():
            raise ValueError('Unsigned historical peer audit requires explicit migration')
        head = ledger._head()
        cache = getattr(self, '_audit_cache', None)
        if (cache is None
                or cache['head']['author'] != head['author']
                or cache['head']['sequence'] > head['sequence']):
            ledger.verify()
            cache = {
                'head': {'sequence': 0, 'hash': '0' * 96, 'author': head['author']},
                'rows': [],
            }
        previous = cache['head']['hash']
        signed = list(cache['rows'])
        for n in range(cache['head']['sequence'] + 1, head['sequence'] + 1):
            block, previous = ledger._read(n, previous, head['author'])
            if block['payload']['kind'] != 'AUDIT_EVENT':
                raise ValueError('Unexpected peer audit event')
            signed.append(_encoded(block['payload']['details']['row']))
        if previous != head['hash']:
            raise ValueError('Peer audit checkpoint conflict')
        offset = 0
        for row in rows:
            expected = _encoded(row)
            while offset < len(signed) and signed[offset] != expected:
                offset += 1
            if offset == len(signed):
                raise ValueError('Peer audit row lacks matching hybrid authentication')
            offset += 1
        self._audit_cache = {'head': head, 'rows': signed}

    def load(self) -> dict:
        """Satisfies LedgerAdapter; returns {} — policy lives on PolicyStore."""
        return {}

    # ── Write ─────────────────────────────────────────────────────────────────

    def event(self, kind: str, **details) -> dict:
        """Append a new audit event and return the signed row."""
        rows = self.audit_rows()
        row: dict = {
            'schema': SCHEMA,
            'at_unix': time.time(),
            'kind': kind,
            'previous': rows[-1]['sha256'] if rows else '0' * 64,
            **details,
        }
        row['sha256'] = _digest(row)
        from .signed_ledger import Ledger
        if not hasattr(self, '_signed_audit'):
            self._signed_audit = Ledger(self.root / 'signed-audit')
        self._signed_audit.append('AUDIT_EVENT', {'row': row})
        with (self.root / 'audit.jsonl').open('a') as f:
            f.write(json.dumps(row, sort_keys=True) + '\n')
            f.flush()
            os.fsync(f.fileno())
        return row

    def append_audit_row(self, row: dict) -> None:
        """Append a pre-formed row dict (kind field required)."""
        kind = row.get('kind', 'UNKNOWN')
        details = {k: v for k, v in row.items() if k != 'kind'}
        self.event(kind, **details)
