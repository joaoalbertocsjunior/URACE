"""Package registry source adapter — observes package metadata from PyPI/npm/Maven etc.

Uses httpx (already in p2p extra) for HTTP queries. No additional dep needed.
"""
from __future__ import annotations

from typing import Any

from ._base import NullSourceAdapter, SourceUnavailableError, _get_source, _set_source
from . import SOURCE_REGISTRY
from .._common import now

try:
    import httpx as _httpx
    _AVAILABLE = True
except ImportError:
    _httpx = None  # type: ignore[assignment]
    _AVAILABLE = False

_REGISTRY_URLS = {
    'pypi':  'https://pypi.org/pypi/{package}/json',
    'npm':   'https://registry.npmjs.org/{package}',
    'maven': 'https://search.maven.org/solrsearch/select?q=g:{group}+AND+a:{package}&rows=1&wt=json',
}


class PackageRegistryAdapter(NullSourceAdapter):
    kind = 'package_registry'

    def add_args(self, subparser: Any) -> None:
        subparser.add_argument('--registry', default='pypi',
                               choices=list(_REGISTRY_URLS), help='Registry type')
        subparser.add_argument('--package', default=None, help='Package name to observe')
        subparser.add_argument('--group', default=None, help='Maven group ID (Maven only)')
        subparser.add_argument('--description', default=None)

    def validate(self, args: Any) -> dict[str, Any]:
        name = getattr(args, 'name', None) or getattr(args, 'id', None) or ''
        package = getattr(args, 'package', None) or ''
        if not name:
            raise ValueError('source add --kind package_registry requires a name')
        if not package:
            raise ValueError('source add --kind package_registry requires --package')
        registry = getattr(args, 'registry', None) or 'pypi'
        if registry not in _REGISTRY_URLS:
            raise ValueError(f'--registry must be one of {list(_REGISTRY_URLS)}')
        return {
            'kind': self.kind,
            'registry': registry,
            'package': package,
            'group': getattr(args, 'group', None) or '',
        }

    def _add(self, config: dict, state: dict, source_id: str, **kwargs: Any) -> dict:
        return {
            'id': source_id,
            'kind': self.kind,
            'enabled': True,
            'added_at': now(),
            'status': 'CONFIGURED',
            'status_history': [{'status': 'CONFIGURED', 'at': now()}],
            'adapter_state': {
                'registry': kwargs.get('registry', 'pypi'),
                'package': kwargs.get('package', ''),
                'group': kwargs.get('group', ''),
                'last_sync_at': None,
                'latest_version': None,
                'enabled_actions': [],
            },
        }

    def _sync(self, config: dict, state: dict, source_id: str) -> dict:
        if not _AVAILABLE:
            raise SourceUnavailableError('pip install "urace[sources-http]"')
        record = _get_source(state, source_id)
        if not record:
            return {'synced': False, 'reason': 'source not found'}
        astate = record.get('adapter_state', {})
        registry = astate.get('registry', 'pypi')
        package = astate.get('package', '')
        group = astate.get('group', '')
        if not package:
            return {'synced': False, 'reason': 'no package configured'}
        url = _REGISTRY_URLS[registry].format(package=package, group=group)
        try:
            resp = _httpx.get(url, timeout=10, follow_redirects=True)
            resp.raise_for_status()
            data = resp.json()
            if registry == 'pypi':
                latest = data.get('info', {}).get('version', 'unknown')
            elif registry == 'npm':
                latest = data.get('dist-tags', {}).get('latest', 'unknown')
            else:
                docs = data.get('response', {}).get('docs', [{}])
                latest = docs[0].get('latestVersion', 'unknown') if docs else 'unknown'
        except Exception as exc:
            return {'synced': False, 'reason': str(exc)}
        astate['last_sync_at'] = now()
        astate['latest_version'] = latest
        _set_source(state, source_id, record)
        return {'synced': True, 'registry': registry, 'package': package, 'latest_version': latest}


SOURCE_REGISTRY.register(PackageRegistryAdapter())
