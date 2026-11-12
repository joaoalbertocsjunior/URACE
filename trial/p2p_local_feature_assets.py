"""Build provenance-carrying local asset bundles from minted URACE features."""
from __future__ import annotations

import hashlib
import json
import re
import zipfile
from io import BytesIO
from pathlib import Path

SCHEMA = 'urace-local-feature-source-bundle-v1'
MAX_BUNDLE_BYTES = 300_000

FAMILY_SOURCE_TAGS = {
    'navigation': {'freeform_routing', 'command_surface', 'intent_trace', 'cli'},
    'recovery': {'continuation', 'cognitive_resume', 'recovery', 'launcher', 'primitives', 'executor'},
    'receipts': {'authenticated_journal', 'resource_usage', 'ledger_crypto', 'peer_exchange',
                 'ledger_compaction', 'value_trajectory'},
    'requirements_change': {'freeform_routing', 'intent_trace', 'primitives', 'goal', 'decision', 'objective'},
    'integration': {'remote_assets', 'protocol_catalog', 'mcp_server', 'a2a_server',
                    'api_interface', 'peer_exchange'},
}


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _ledger_rows(path: Path) -> list[dict]:
    jsonl = path / 'exchange' / 'initial_ledger' / 'initial_ledger.jsonl'
    if jsonl.is_file():
        with jsonl.open(encoding='utf-8') as stream:
            next(stream, None)
            return [json.loads(line) for line in stream if line.strip()]
    json_path = path / 'exchange' / 'initial_ledger' / 'initial_ledger.json'
    return json.loads(json_path.read_text(encoding='utf-8')).get('features', [])


def source_paths(feature: dict, repo_root: str | Path) -> list[Path]:
    """Map only exact feature tags to existing runtime/urace module names."""
    root = Path(repo_root).resolve(strict=True)
    runtime_root = root / 'runtime' / 'urace'
    found = []
    for tag in feature.get('tags', []):
        if not isinstance(tag, str) or not re.fullmatch(r'[a-zA-Z0-9_]{1,80}', tag):
            continue
        candidate = runtime_root / (tag + '.py')
        if candidate.is_symlink() or not candidate.is_file():
            continue
        resolved = candidate.resolve(strict=True)
        if resolved.is_relative_to(runtime_root.resolve()) and resolved not in found:
            found.append(resolved)
    return sorted(found, key=lambda item: item.name)


def bundle_feature(feature: dict, repo_root: str | Path) -> dict | None:
    """Package source modules named by a minted feature's exact runtime tags."""
    root = Path(repo_root).resolve(strict=True)
    modules = source_paths(feature, root)
    if not modules:
        return None
    license_path = root / 'LICENSE'
    if license_path.is_symlink() or not license_path.is_file():
        raise ValueError('Repository license file is missing or unsafe')
    license_bytes = license_path.read_bytes()
    entries = {f'runtime/urace/{module.name}': module.read_bytes() for module in modules}
    entries['LICENSE'] = license_bytes
    files = [{'path': name, 'sha256': _sha(data), 'bytes': len(data)}
             for name, data in sorted(entries.items())]
    source_files = [item for item in files if item['path'].startswith('runtime/urace/')]
    # initial_ledger no longer stores local_source_files in artifact_discovery;
    # binding is computed at runtime from tags via compute_local_source_binding().
    # Compute runtime manifest sha — initial_ledger no longer stores source_manifest_sha256.
    _src_contract = {'license_id': 'Apache-2.0', 'files': source_files}
    _computed_manifest_sha = _sha(json.dumps(_src_contract, sort_keys=True, separators=(',', ':')).encode())
    manifest = {'schema': SCHEMA, 'feature_id': feature.get('feature_id'),
                'source_mapping': 'exact_initial_ledger_tag_to_runtime_module',
                'license_id': 'Apache-2.0', 'files': files,
                'ledger_source_manifest_sha256': _computed_manifest_sha}
    manifest_bytes = json.dumps(manifest, sort_keys=True, separators=(',', ':')).encode()
    entries['SOURCE-MANIFEST.json'] = manifest_bytes
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(entries.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    artifact = buffer.getvalue()
    if len(artifact) > MAX_BUNDLE_BYTES:
        return None
    return {'feature_id': feature.get('feature_id'), 'name': feature.get('name', ''),
            'description': feature.get('description', ''), 'tags': list(feature.get('tags', [])),
            'license_id': 'Apache-2.0', 'artifact_bytes': artifact,
            'artifact_sha256': _sha(artifact), 'artifact_size_bytes': len(artifact),
            'source_manifest': manifest, 'source_manifest_sha256': _sha(manifest_bytes),
            'source_paths': [name for name in sorted(entries) if name.startswith('runtime/urace/')]}


def verify_bundle(data: bytes, *, feature_id: str, artifact_sha256: str,
                  source_manifest_sha256: str, repo_root: str | Path | None = None) -> dict:
    """Verify the package, per-file digests, and optionally current local source mapping."""
    if _sha(data) != artifact_sha256:
        raise ValueError('Source-backed artifact digest mismatch')
    try:
        archive = zipfile.ZipFile(BytesIO(data), 'r')
    except zipfile.BadZipFile as error:
        raise ValueError('Source-backed artifact is not a ZIP bundle') from error
    with archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or 'SOURCE-MANIFEST.json' not in names:
            raise ValueError('Source bundle has duplicate entries or no manifest')
        for info in archive.infolist():
            path = Path(info.filename)
            if path.is_absolute() or '..' in path.parts or info.is_dir():
                raise ValueError('Source bundle contains an unsafe path')
        manifest_bytes = archive.read('SOURCE-MANIFEST.json')
        if _sha(manifest_bytes) != source_manifest_sha256:
            raise ValueError('Source manifest digest mismatch')
        manifest = json.loads(manifest_bytes)
        if (manifest.get('schema') != SCHEMA or manifest.get('feature_id') != feature_id
                or manifest.get('license_id') != 'Apache-2.0'):
            raise ValueError('Source manifest identity or license does not match')
        file_map = {item.get('path'): item for item in manifest.get('files', [])}
        if set(names) != set(file_map) | {'SOURCE-MANIFEST.json'}:
            raise ValueError('Source bundle inventory differs from its manifest')
        for name, item in file_map.items():
            payload = archive.read(name)
            if (len(payload) != item.get('bytes') or _sha(payload) != item.get('sha256')):
                raise ValueError('Bundled source file digest/size mismatch: ' + str(name))
        license_head = archive.read('LICENSE')[:256]
        if b'Apache License' not in license_head or b'Version 2.0' not in license_head:
            raise ValueError('Source bundle does not carry the repository Apache-2.0 license')
        runtime_paths = sorted(name for name in file_map if name.startswith('runtime/urace/'))
        if (not runtime_paths or any(not name.endswith('.py') for name in runtime_paths)
                or any(name not in names for name in runtime_paths)):
            raise ValueError('Source bundle lacks valid runtime module content')
        if repo_root is not None:
            root = Path(repo_root).resolve(strict=True)
            features = {row.get('feature_id'): row for row in _ledger_rows(root)}
            feature = features.get(feature_id)
            if feature is None:
                raise ValueError('Source feature is not present in the local initial ledger')
            expected_paths = [path.relative_to(root).as_posix() for path in source_paths(feature, root)]
            if expected_paths != runtime_paths:
                raise ValueError('Bundled module paths differ from exact initial-ledger source tags')
            source_contract = {'license_id': 'Apache-2.0',
                               'files': [item for item in manifest['files']
                                         if item['path'].startswith('runtime/urace/')]}
            ledger_manifest_sha = _sha(json.dumps(source_contract, sort_keys=True,
                                                  separators=(',', ':')).encode())
            # initial_ledger no longer stores local_source_files/source_manifest_sha256 in
            # artifact_discovery — binding is computed at runtime. Only verify the bundle's
            # own manifest sha is self-consistent.
            if manifest.get('ledger_source_manifest_sha256') != ledger_manifest_sha:
                raise ValueError('Source bundle ledger_source_manifest_sha256 is inconsistent')
            for relative in expected_paths:
                if archive.read(relative) != (root / relative).read_bytes():
                    raise ValueError('Bundled source differs from the current local implementation: ' + relative)
            if archive.read('LICENSE') != (root / 'LICENSE').read_bytes():
                raise ValueError('Bundled license differs from the current repository license')
        return manifest


def family_assets(repo_root: str | Path, *, count_per_family: int = 6) -> dict[str, list[dict]]:
    """Select distinct real local implementation bundles for synthetic scenarios."""
    if type(count_per_family) is not int or count_per_family < 1:
        raise ValueError('count_per_family must be a positive integer')
    root = Path(repo_root).resolve(strict=True)
    catalog = []
    for feature in _ledger_rows(root):
        if not feature.get('initial_ledger') or feature.get('owner') is not None:
            continue
        if source_paths(feature, root):
            catalog.append(feature)
    selected_ids = set()
    result = {}
    for family, tags in FAMILY_SOURCE_TAGS.items():
        candidates = [row for row in catalog
                      if row['feature_id'] not in selected_ids and tags.intersection(row['tags'])]
        if len(candidates) < count_per_family:
            raise ValueError(f'Only {len(candidates)} source-backed features available for {family}')
        chosen = candidates[:count_per_family]
        selected_ids.update(row['feature_id'] for row in chosen)
        result[family] = [bundle_feature(row, root) for row in chosen]
    return result
