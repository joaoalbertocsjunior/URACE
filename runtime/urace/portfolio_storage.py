#!/usr/bin/env python3
"""Portfolio file I/O, HMAC integrity, and agora chain."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    import fcntl as _fcntl
    def _flock_ex(fd): _fcntl.flock(fd, _fcntl.LOCK_EX)
    def _flock_un(fd): _fcntl.flock(fd, _fcntl.LOCK_UN)
except ImportError:
    # Non-POSIX (Windows): no advisory file locking; safe for single-process use
    def _flock_ex(fd): pass  # noqa: E704
    def _flock_un(fd): pass  # noqa: E704


def product_root() -> Path:
    """Installed runtime location identifies its Product, independently of cwd Git."""
    source = Path(__file__).resolve()
    if source.parent.name == "urace" and source.parent.parent.name == "runtime":
        return source.parents[3]
    # Standalone portfolio helpers retain their existing repository-relative use.
    result = subprocess.run(["git", "rev-parse", "--show-toplevel"], text=True, capture_output=True, check=False)
    return Path(result.stdout.strip()) if result.returncode == 0 else source.parent


ROOT = product_root()
SYSTEM_ROOT = ROOT / "urace"
PORTFOLIO_ROOT = SYSTEM_ROOT / "state" / "portfolio"
GENERATED_ROOT = SYSTEM_ROOT / "generated"
TEMPORARY_ROOT = GENERATED_ROOT / "temporary"
RETIRED_PORTFOLIOS_ROOT = GENERATED_ROOT / "retired-portfolios"
DATA = PORTFOLIO_ROOT / "portfolio.json"
LEDGER_LOCK = PORTFOLIO_ROOT / ".ledger.lock"
OPERATION_LOCK = PORTFOLIO_ROOT / ".operation.lock"
CONTROL_INBOX = PORTFOLIO_ROOT / "inbox"
VARIANTS = GENERATED_ROOT / "portfolio" / "variants"
INTEGRITY_KEY = SYSTEM_ROOT / "state" / "secrets" / "portfolio-integrity.key"

SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
MAX_ADVISORY_TEXT = 4000
MAX_AGORA_RECORDS = 10000


class AuthIntegrityError(ValueError):
    """Raised when HMAC verification of ledger or archive fails."""


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def integrity_key(create: bool = False) -> bytes:
    if create and not INTEGRITY_KEY.exists():
        INTEGRITY_KEY.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(INTEGRITY_KEY, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(os.urandom(32))
            stream.flush(); os.fsync(stream.fileno())
    try:
        key = INTEGRITY_KEY.read_bytes()
    except OSError as error:
        raise SystemExit(f"Portfolio integrity key unavailable at {INTEGRITY_KEY}; restore the protected key or start a new portfolio") from error
    if len(key) < 32:
        raise SystemExit("Portfolio integrity key must contain at least 32 random bytes")
    if INTEGRITY_KEY.stat().st_mode & 0o077:
        raise SystemExit("Portfolio integrity key permissions are too broad; require owner-only access (0600)")
    return key


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def ledger_digest(data: dict) -> str:
    payload = {key: value for key, value in data.items() if key != "integrity" and not key.startswith("_")}
    return hashlib.sha256(canonical(payload)).hexdigest()


def verify_ledger(data: dict) -> None:
    seal = data.get("integrity")
    if not seal:
        return
    digest = ledger_digest(data)
    expected = hmac.new(integrity_key(), digest.encode(), hashlib.sha256).hexdigest()
    if seal.get("algorithm") != "HMAC-SHA256" or seal.get("digest") != digest or not hmac.compare_digest(str(seal.get("authentication_tag", "")), expected):
        raise AuthIntegrityError("Portfolio authenticated-chain verification failed; preserve evidence and restore the last trusted ledger and integrity key")


def verify_agora(data: dict) -> None:
    records = []
    for collection in ("proposals", "votes", "decisions", "system_confirmations"):
        records.extend((item.get("sequence", 0), collection, item) for item in data["agora"].get(collection, []))
    sealed = [entry for entry in sorted(records, key=lambda entry: entry[0]) if entry[2].get("record_hash")]
    if not sealed:
        return
    previous = None
    for _, collection, record in sealed:
        expected = hashlib.sha256(json.dumps({"collection": collection, "previous_hash": previous, "payload": record_payload(record)}, sort_keys=True).encode()).hexdigest()
        if record.get("previous_hash") != previous or record.get("record_hash") != expected:
            raise SystemExit("Agora integrity check failed; preserve the ledger and restore a trusted snapshot before continuing")
        previous = record["record_hash"]
    if data["agora"].get("head_hash") != previous:
        raise SystemExit("Agora head hash does not match its append-only record chain")


_load_cache: dict = {}  # {path_str: (mtime, data)}


def _load_uncached() -> dict:
    if not DATA.exists():
        raise SystemExit("Initialize a portfolio first")
    data = json.loads(DATA.read_text(encoding="utf-8"))
    data.setdefault("agora", {"proposals": [], "votes": [], "decisions": []})
    data["agora"].setdefault("system_confirmations", [])
    verify_ledger(data)
    verify_agora(data)
    data["_loaded_digest"] = data.get("integrity", {}).get("digest")
    return data


def _real_load() -> dict:
    import copy
    path = DATA
    try:
        mtime = path.stat().st_mtime
    except FileNotFoundError:
        raise SystemExit("Initialize a portfolio first")
    cached = _load_cache.get(str(path))
    if cached and cached[0] == mtime:
        return copy.deepcopy(cached[1])
    result = _load_uncached()
    _load_cache[str(path)] = (mtime, copy.deepcopy(result))
    return result


def load() -> dict:
    """Dispatch through the portfolio hub so patch.object(portfolio, 'load') works in tests."""
    import sys
    hub = sys.modules.get("urace.portfolio")
    if hub is not None:
        hub_fn = hub.__dict__.get("load")
        # If hub.load is not this function (i.e. it's been patched), call through it
        if hub_fn is not None and hub_fn is not load:
            return hub_fn()
    return _real_load()


def _real_save(data: dict) -> None:
    DATA.parent.mkdir(parents=True, exist_ok=True)
    expected = data.get("_loaded_digest")
    descriptor = os.open(LEDGER_LOCK, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        _flock_ex(descriptor)
        if DATA.exists():
            current = json.loads(DATA.read_text(encoding="utf-8"))
            verify_ledger(current); verify_agora(current)
            current_digest = current.get("integrity", {}).get("digest")
            if expected is None or current_digest != expected:
                raise SystemExit("CONCURRENT_LEDGER_CHANGE: preserve the newer ledger and retry from a fresh snapshot")
        digest = ledger_digest(data)
        data["integrity"] = {"algorithm": "HMAC-SHA256", "digest": digest, "authentication_tag": hmac.new(integrity_key(), digest.encode(), hashlib.sha256).hexdigest(), "key_reference": str(INTEGRITY_KEY.relative_to(ROOT)), "scope": "complete portfolio ledger"}
        persisted = {key: value for key, value in data.items() if not key.startswith("_")}
        temporary = DATA.with_suffix(".tmp")
        with temporary.open("w", encoding="utf-8") as stream:
            stream.write(json.dumps(persisted, indent=2, sort_keys=True) + "\n")
            stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, DATA)
        directory = os.open(DATA.parent, os.O_RDONLY)
        try: os.fsync(directory)
        finally: os.close(directory)
        data["_loaded_digest"] = digest
        _load_cache.pop(str(DATA), None)
    finally:
        _flock_un(descriptor); os.close(descriptor)


def save(data: dict) -> None:
    """Dispatch through the portfolio hub so patch.object(portfolio, 'save') works in tests."""
    import sys
    hub = sys.modules.get("urace.portfolio")
    if hub is not None:
        hub_fn = hub.__dict__.get("save")
        # If hub.save is not this function (i.e. it's been patched), call through it
        if hub_fn is not None and hub_fn is not save:
            hub_fn(data)
            return
    _real_save(data)


def record_payload(record: dict) -> dict:
    return {key: value for key, value in record.items() if key not in {"record_hash", "previous_hash"}}


def append_agora(data: dict, collection: str, record: dict) -> None:
    total = sum(len(data["agora"].get(name, [])) for name in ("proposals", "votes", "decisions", "system_confirmations"))
    if total >= MAX_AGORA_RECORDS:
        raise SystemExit("Agora retention ceiling reached; close this authenticated experiment and start a new portfolio instead of growing the live ledger")
    previous = data["agora"].get("head_hash")
    record["sequence"] = int(data["agora"].get("sequence", 0)) + 1
    record["previous_hash"] = previous
    record["record_hash"] = hashlib.sha256(json.dumps({"collection": collection, "previous_hash": previous, "payload": record_payload(record)}, sort_keys=True).encode()).hexdigest()
    data["agora"][collection].append(record)
    data["agora"]["head_hash"] = record["record_hash"]
    data["agora"]["sequence"] = record["sequence"]


def _real_write_authenticated_archive(path: Path, kind: str, payload: object) -> None:
    body = {"kind": kind, "archived_at": now(), "payload": payload}
    digest = hashlib.sha256(canonical(body)).hexdigest()
    envelope = {**body, "integrity": {"algorithm": "HMAC-SHA256", "digest": digest, "authentication_tag": hmac.new(integrity_key(), digest.encode(), hashlib.sha256).hexdigest()}}
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name("." + path.name + ".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        stream.write(json.dumps(envelope, indent=2, sort_keys=True) + "\n"); stream.flush(); os.fsync(stream.fileno())
    os.replace(temporary, path)
    directory = os.open(path.parent, os.O_RDONLY)
    try: os.fsync(directory)
    finally: os.close(directory)


def write_authenticated_archive(path: Path, kind: str, payload: object) -> None:
    """Dispatch through portfolio hub so patch.object(portfolio, 'write_authenticated_archive') works in tests."""
    import sys
    hub = sys.modules.get("urace.portfolio")
    if hub is not None:
        hub_fn = hub.__dict__.get("write_authenticated_archive")
        if hub_fn is not None and hub_fn is not write_authenticated_archive:
            hub_fn(path, kind, payload)
            return
    _real_write_authenticated_archive(path, kind, payload)


def verify_authenticated_archive(path: Path) -> None:
    envelope = json.loads(path.read_text(encoding="utf-8"))
    body = {key: value for key, value in envelope.items() if key != "integrity"}
    digest = hashlib.sha256(canonical(body)).hexdigest()
    seal = envelope.get("integrity", {})
    expected = hmac.new(integrity_key(), digest.encode(), hashlib.sha256).hexdigest()
    if seal.get("digest") != digest or seal.get("algorithm") != "HMAC-SHA256" or not hmac.compare_digest(str(seal.get("authentication_tag", "")), expected):
        raise AuthIntegrityError(f"Authenticated archive verification failed: {path}")


def cmd_backup(args: argparse.Namespace) -> None:
    data = load()
    dest = Path(args.dest) if getattr(args, 'dest', None) else \
        RETIRED_PORTFOLIOS_ROOT / f"backup_{now().replace(':', '-').replace('+', '_')}.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    write_authenticated_archive(dest, "backup", data)
    print(json.dumps({"status": "ok", "path": str(dest)}))


def cmd_restore(args: argparse.Namespace) -> None:
    src = Path(args.src)
    verify_authenticated_archive(src)
    envelope = json.loads(src.read_text(encoding='utf-8'))
    data = envelope['payload']
    save(data)
    print(json.dumps({"status": "ok", "restored_from": str(src)}))


def cmd_verify(args: argparse.Namespace) -> None:
    data = load()
    archives = sorted((DATA.parent / "archive").glob("*.json"))
    for path in archives:
        verify_authenticated_archive(path)
    result = {"status": "VERIFIED", "ledger_digest": data["integrity"]["digest"], "agora_head": data["agora"].get("head_hash"), "archives_verified": len(archives)}
    print(json.dumps(result, indent=2, sort_keys=True) if args.json else f"Portfolio integrity VERIFIED; archives={len(archives)} ledger={result['ledger_digest'][:16]}…")


def bounded_text(value: str | None, label: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip() or len(value) > MAX_ADVISORY_TEXT or "\x00" in value:
        raise SystemExit(f"{label} must be non-empty text of at most {MAX_ADVISORY_TEXT} characters without NUL bytes")
    return value.strip()


def name(value: str) -> str:
    if not SAFE_NAME.fullmatch(value):
        raise argparse.ArgumentTypeError("use 1-64 letters, numbers, dots, underscores, or hyphens")
    return value


def rotate_integrity_key() -> dict:
    """Rotate the portfolio HMAC integrity key. Re-signs current ledger with new key."""
    old_key_path = INTEGRITY_KEY
    backup_path = Path(str(INTEGRITY_KEY) + '.prev')
    # Backup old key
    if old_key_path.exists():
        shutil.copy2(old_key_path, backup_path)
    # Generate new key
    new_key = os.urandom(32)
    old_key_path.parent.mkdir(parents=True, exist_ok=True)
    old_key_path.write_bytes(new_key)
    old_key_path.chmod(0o600)
    # Re-sign current ledger
    data = load()
    save(data)
    return {"status": "ok", "backup": str(backup_path)}


def cmd_rotate_integrity_key(args: argparse.Namespace) -> None:
    result = rotate_integrity_key()
    print(json.dumps(result, indent=2))


def unit_interval(value: str) -> float:
    number = float(value)
    if not 0 <= number <= 1:
        raise argparse.ArgumentTypeError("use a confidence from 0 to 1")
    return number
