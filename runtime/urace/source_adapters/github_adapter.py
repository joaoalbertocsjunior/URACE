"""GitHub repository source adapter — uses ghapi (urace[sources-github] extra)."""
from __future__ import annotations

import os
from typing import Any

from ._base import NullSourceAdapter, SourceUnavailableError, _get_source, _set_source
from . import SOURCE_REGISTRY
from .._common import now

try:
    from ghapi.all import GhApi as _GhApi
    _AVAILABLE = True
except ImportError:
    _GhApi = None  # type: ignore[assignment,misc]
    _AVAILABLE = False


def _require_ghapi() -> None:
    if not _AVAILABLE:
        raise SourceUnavailableError('pip install "urace[sources-github]"')


class GithubAdapter(NullSourceAdapter):
    kind = 'github'

    def add_args(self, subparser: Any) -> None:
        subparser.add_argument('--repo', default=None, help='owner/repo slug')
        subparser.add_argument('--token-env', dest='token_env',
                               default='URACE_GITHUB_TOKEN')

    def validate(self, args: Any) -> dict[str, Any]:
        repo = getattr(args, 'repo', None) or getattr(args, 'name', None) or ''
        if not repo:
            raise ValueError('source add --kind github requires --repo owner/repo')
        if '/' not in repo:
            raise ValueError('--repo must be owner/repo slug')
        return {'kind': self.kind, 'repo': repo,
                'token_env': getattr(args, 'token_env', 'URACE_GITHUB_TOKEN')}

    def _add(self, config: dict, state: dict, source_id: str, **kwargs: Any) -> dict:
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
                'last_sync_at': None,
                'default_branch': None,
                'open_issues': None,
                'stars': None,
                'enabled_actions': [],
            },
        }

    def _sync(self, config: dict, state: dict, source_id: str) -> dict:
        _require_ghapi()
        record = _get_source(state, source_id)
        if not record:
            return {'synced': False, 'reason': 'source not found'}
        astate = record.get('adapter_state', {})
        repo = astate.get('repo', '')
        if not repo or '/' not in repo:
            return {'synced': False, 'reason': 'no repo configured'}
        owner, repo_name = repo.split('/', 1)
        token = os.environ.get(astate.get('token_env', 'URACE_GITHUB_TOKEN'), '') or None
        try:
            api = _GhApi(owner=owner, repo=repo_name, token=token)
            data = api.repos.get()
        except Exception as exc:
            return {'synced': False, 'reason': str(exc)}
        result = {
            'synced': True,
            'repo': repo,
            'default_branch': data.get('default_branch'),
            'open_issues': data.get('open_issues_count'),
            'stars': data.get('stargazers_count'),
            'forks': data.get('forks_count'),
            'visibility': data.get('visibility'),
            'pushed_at': data.get('pushed_at'),
        }
        astate.update({
            'last_sync_at': now(),
            'default_branch': result['default_branch'],
            'open_issues': result['open_issues'],
            'stars': result['stars'],
        })
        _set_source(state, source_id, record)
        return result

    def _act(self, config: dict, state: dict, source_id: str,
             action: str, payload: dict) -> dict:
        _require_ghapi()
        record = _get_source(state, source_id)
        if not record:
            return {'acted': False, 'reason': 'source not found'}
        astate = record.get('adapter_state', {})
        repo = astate.get('repo', '')
        if not repo or '/' not in repo:
            return {'acted': False, 'reason': 'no repo configured'}
        owner, repo_name = repo.split('/', 1)
        token = os.environ.get(astate.get('token_env', 'URACE_GITHUB_TOKEN'), '') or None
        try:
            api = _GhApi(owner=owner, repo=repo_name, token=token)
            if action == 'create_issue':
                title = payload.get('title', '')
                body = payload.get('body', '')
                if not title:
                    return {'acted': False, 'reason': 'create_issue requires title in payload'}
                issue = api.issues.create(title=title, body=body)
                return {'acted': True, 'action': 'create_issue', 'number': issue.get('number'),
                        'url': issue.get('html_url')}
            elif action == 'create_pr':
                title = payload.get('title', '')
                head = payload.get('head', '')
                base = payload.get('base', astate.get('default_branch', 'main'))
                if not title or not head:
                    return {'acted': False, 'reason': 'create_pr requires title and head in payload'}
                pr = api.pulls.create(title=title, head=head, base=base,
                                      body=payload.get('body', ''))
                return {'acted': True, 'action': 'create_pr', 'number': pr.get('number'),
                        'url': pr.get('html_url')}
            else:
                return {'acted': False, 'reason': f'unknown action: {action}'}
        except Exception as exc:
            return {'acted': False, 'reason': str(exc)}


SOURCE_REGISTRY.register(GithubAdapter())
