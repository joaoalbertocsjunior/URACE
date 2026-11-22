"""Git repository source adapter — observes commits, branches, tags; acts with fetch/pull."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ._base import NullSourceAdapter, SourceUnavailableError, _get_source, _set_source
from . import SOURCE_REGISTRY
from .._common import now

try:
    import git as _git
    _AVAILABLE = True
except ImportError:
    _git = None  # type: ignore[assignment]
    _AVAILABLE = False


def _require_git() -> None:
    if not _AVAILABLE:
        raise SourceUnavailableError('pip install "urace[sources-git]"')


class GitAdapter(NullSourceAdapter):
    kind = 'git'

    def add_args(self, subparser: Any) -> None:
        subparser.add_argument('--path', default=None, help='Absolute path to git repo')
        subparser.add_argument('--remote', default='origin', help='Remote name (default: origin)')
        subparser.add_argument('--branch', default=None, help='Branch to track (default: HEAD)')
        subparser.add_argument('--description', default=None)

    def validate(self, args: Any) -> dict[str, Any]:
        name = getattr(args, 'name', None) or getattr(args, 'id', None) or ''
        path = getattr(args, 'path', None) or ''
        if not name:
            raise ValueError('source add --kind git requires a name')
        if not path:
            raise ValueError('source add --kind git requires --path')
        p = Path(path)
        if not p.is_absolute():
            raise ValueError('--path must be an absolute path')
        return {
            'kind': self.kind,
            'path': str(p),
            'remote': getattr(args, 'remote', None) or 'origin',
            'branch': getattr(args, 'branch', None),
        }

    def _add(self, config: dict, state: dict, source_id: str, **kwargs: Any) -> dict:
        path = kwargs.get('path', '')
        return {
            'id': source_id,
            'kind': self.kind,
            'enabled': True,
            'added_at': now(),
            'status': 'CONFIGURED',
            'status_history': [{'status': 'CONFIGURED', 'at': now()}],
            'adapter_state': {
                'path': path,
                'remote': kwargs.get('remote', 'origin'),
                'branch': kwargs.get('branch'),
                'last_sync_at': None,
                'head_sha': None,
                'commit_count': None,
                'enabled_actions': [],
            },
        }

    def _sync(self, config: dict, state: dict, source_id: str) -> dict:
        _require_git()
        record = _get_source(state, source_id)
        if not record:
            return {'synced': False, 'reason': 'source not found'}
        astate = record.get('adapter_state', {})
        path = astate.get('path', '')
        if not path or not Path(path).exists():
            return {'synced': False, 'reason': 'path does not exist'}
        try:
            repo = _git.Repo(path)
            head_sha = repo.head.commit.hexsha
            commit_count = sum(1 for _ in repo.iter_commits())
            branch = repo.active_branch.name if not repo.head.is_detached else None
        except Exception as exc:
            return {'synced': False, 'reason': str(exc)}
        astate['last_sync_at'] = now()
        astate['head_sha'] = head_sha
        astate['commit_count'] = commit_count
        astate['active_branch'] = branch
        _set_source(state, source_id, record)
        return {'synced': True, 'head_sha': head_sha, 'commit_count': commit_count, 'branch': branch}

    def _act(self, config: dict, state: dict, source_id: str,
             action: str, payload: dict) -> dict:
        _require_git()
        record = _get_source(state, source_id)
        if not record:
            return {'acted': False, 'reason': 'source not found'}
        path = record.get('adapter_state', {}).get('path', '')
        if not path or not Path(path).exists():
            return {'acted': False, 'reason': 'path does not exist'}
        try:
            repo = _git.Repo(path)
            remote = record.get('adapter_state', {}).get('remote', 'origin')
            if action == 'fetch':
                repo.remotes[remote].fetch()
                return {'acted': True, 'action': 'fetch', 'remote': remote}
            elif action == 'pull':
                repo.remotes[remote].pull()
                return {'acted': True, 'action': 'pull', 'remote': remote}
            else:
                return {'acted': False, 'reason': f'unknown action: {action}'}
        except Exception as exc:
            return {'acted': False, 'reason': str(exc)}


SOURCE_REGISTRY.register(GitAdapter())
