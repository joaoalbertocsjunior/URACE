"""GitHub repository source adapter."""
from __future__ import annotations

from typing import Any

from ._base import NullSourceAdapter
from . import SOURCE_REGISTRY


class GithubAdapter(NullSourceAdapter):
    kind = 'github'

    def add_args(self, subparser: Any) -> None:
        subparser.add_argument('--repo', default=None,
                               help='owner/repo slug')
        subparser.add_argument('--token-env', dest='token_env',
                               default='URACE_GITHUB_TOKEN')

    def validate(self, args: Any) -> dict[str, Any]:
        repo = getattr(args, 'repo', None) or getattr(args, 'name', None) or ''
        if not repo:
            raise ValueError('source add --kind github requires --repo owner/repo')
        return {'kind': self.kind, 'repo': repo,
                'token_env': getattr(args, 'token_env', 'URACE_GITHUB_TOKEN')}

    def _add(self, config: dict, state: dict, source_id: str, **kwargs: Any) -> dict:
        from .._common import now
        return {
            'id': source_id,
            'kind': self.kind,
            'enabled': True,
            'added_at': now(),
            'status': 'CONFIGURED',
            'status_history': [{'status': 'CONFIGURED', 'at': now()}],
            'adapter_state': {
                'repo': kwargs.get('repo', ''),
                'token_env': kwargs.get('token_env', 'URACE_GITHUB_TOKEN'),
                'enabled_actions': [],
            },
        }

    def _sync(self, config: dict, state: dict, source_id: str) -> dict:
        from ._base import _get_source
        import os
        record = _get_source(state, source_id) or {}
        astate = record.get('adapter_state', {})
        repo = astate.get('repo', '')
        token_env = astate.get('token_env', 'URACE_GITHUB_TOKEN')
        token = os.environ.get(token_env, '')
        if not repo:
            return {'synced': False, 'reason': 'no repo configured'}
        try:
            import httpx
        except ImportError:
            from ._base import SourceUnavailableError
            raise SourceUnavailableError('pip install "urace[p2p]"')
        headers = {'Accept': 'application/vnd.github+json'}
        if token:
            headers['Authorization'] = f'Bearer {token}'
        try:
            resp = httpx.get(f'https://api.github.com/repos/{repo}', headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                return {
                    'synced': True,
                    'repo': repo,
                    'default_branch': data.get('default_branch'),
                    'open_issues': data.get('open_issues_count'),
                    'stars': data.get('stargazers_count'),
                    'forks': data.get('forks_count'),
                    'visibility': data.get('visibility'),
                    'pushed_at': data.get('pushed_at'),
                }
            return {'synced': False, 'reason': f'HTTP {resp.status_code}', 'repo': repo}
        except Exception as exc:
            return {'synced': False, 'reason': str(exc)}


SOURCE_REGISTRY.register(GithubAdapter())
