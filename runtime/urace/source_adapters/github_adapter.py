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
            },
        }


SOURCE_REGISTRY.register(GithubAdapter())
