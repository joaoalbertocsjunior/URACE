from __future__ import annotations
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_STORE_DIR = "urace/content_refs"


def _store_root(product_root: Path) -> Path:
    p = product_root / _STORE_DIR
    p.mkdir(parents=True, exist_ok=True)
    return p


def _index_path(product_root: Path) -> Path:
    return _store_root(product_root) / "index.jsonl"


def content_ref(product_root: Path, file_path: str) -> dict[str, Any]:
    src = Path(file_path).expanduser().resolve()
    if not src.exists():
        return {"error": f"file not found: {file_path}"}
    size = src.stat().st_size
    h = hashlib.sha256()
    with open(src, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    digest = h.hexdigest()
    entry = {
        "id": digest[:16],
        "sha256": digest,
        "path": str(src),
        "size_bytes": size,
        "name": src.name,
        "registered_at": datetime.now(timezone.utc).isoformat(),
    }
    idx = _index_path(product_root)
    existing = _load_index(product_root)
    if not any(r["sha256"] == digest for r in existing):
        with open(idx, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    return entry


def content_list(product_root: Path) -> list[dict[str, Any]]:
    return _load_index(product_root)


def content_show(product_root: Path, ref_id: str) -> dict[str, Any] | None:
    for entry in _load_index(product_root):
        if entry.get("id") == ref_id or entry.get("sha256", "").startswith(ref_id):
            return entry
    return None


def _load_index(product_root: Path) -> list[dict[str, Any]]:
    idx = _index_path(product_root)
    if not idx.exists():
        return []
    entries = []
    for line in idx.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return entries
