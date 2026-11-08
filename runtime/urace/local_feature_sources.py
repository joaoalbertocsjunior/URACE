"""Resolve minted initial-ledger feature IDs to verified local source modules."""
from __future__ import annotations

import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@lru_cache(maxsize=256)
def _file_digest(path: str, size: int, mtime_ns: int) -> tuple[str, int]:
    data = Path(path).read_bytes()
    return _sha(data), len(data)


def resolve_local_source_binding(feature: dict, repo_root: str | Path | None = None) -> dict:
    """Verify ledger-bound module paths/hashes against this checkout; never import or execute them."""
    root = (Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[2]).resolve(strict=True)
    discovery = feature.get('artifact_discovery') if isinstance(feature, dict) else None
    if not isinstance(discovery, dict):
        return {'status': 'NO_LOCAL_SOURCE_BINDING', 'source_files': []}
    files = discovery.get('local_source_files')
    license_id = discovery.get('source_license_id')
    manifest_sha256 = discovery.get('source_manifest_sha256')
    if not isinstance(files, list) or not files:
        return {'status': 'NO_LOCAL_SOURCE_BINDING', 'source_files': []}
    if license_id != 'Apache-2.0' or not isinstance(manifest_sha256, str):
        return {'status': 'INVALID_LOCAL_SOURCE_BINDING', 'source_files': []}
    expected_tags = set(feature.get('tags', []))
    expected_paths = {f'runtime/urace/{tag}.py' for tag in expected_tags
                      if isinstance(tag, str) and re.fullmatch(r'[a-zA-Z0-9_]{1,80}', tag)
                      and (root / 'runtime' / 'urace' / (tag + '.py')).is_file()}
    supplied_paths = set()
    for item in files:
        if (not isinstance(item, dict) or not isinstance(item.get('path'), str)
                or not re.fullmatch(r'runtime/urace/[a-zA-Z0-9_]{1,80}\.py', item['path'])
                or type(item.get('bytes')) is not int or item['bytes'] < 0
                or not isinstance(item.get('sha256'), str) or len(item['sha256']) != 64
                or any(c not in '0123456789abcdef' for c in item['sha256'])):
            return {'status': 'INVALID_LOCAL_SOURCE_BINDING', 'source_files': []}
        supplied_paths.add(item['path'])
    if len(supplied_paths) != len(files) or supplied_paths != expected_paths:
        return {'status': 'STALE_LOCAL_SOURCE_BINDING', 'source_files': []}
    source_contract = {'license_id': license_id, 'files': sorted(files, key=lambda item: item['path'])}
    calculated_manifest = _sha(json.dumps(source_contract, sort_keys=True,
                                          separators=(',', ':')).encode())
    if calculated_manifest != manifest_sha256:
        return {'status': 'INVALID_LOCAL_SOURCE_BINDING', 'source_files': []}
    base = (root / 'runtime' / 'urace').resolve(strict=True)
    for item in files:
        path = root / item['path']
        if path.is_symlink():
            return {'status': 'STALE_LOCAL_SOURCE_BINDING', 'source_files': []}
        resolved = path.resolve(strict=True)
        if not resolved.is_relative_to(base):
            return {'status': 'INVALID_LOCAL_SOURCE_BINDING', 'source_files': []}
        digest, size = _file_digest(str(resolved), resolved.stat().st_size, resolved.stat().st_mtime_ns)
        if digest != item['sha256'] or size != item['bytes']:
            return {'status': 'STALE_LOCAL_SOURCE_BINDING', 'source_files': []}
    return {'status': 'VERIFIED_LOCAL_IMPLEMENTATION', 'source_files': files,
            'source_license_id': license_id, 'source_manifest_sha256': manifest_sha256,
            'executes_source': False}
