"""GitHub adapter port — isolates GitHub API calls behind a Protocol."""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class GitHubAdapter(Protocol):
    """Port for GitHub REST API operations used by URACE."""

    def get_repo(self, repo: str) -> dict[str, Any]: ...
    def create_issue(self, repo: str, title: str, body: str, labels: list[str]) -> dict[str, Any]: ...
    def dispatch_workflow(self, repo: str, workflow: str, ref: str, inputs: dict[str, Any]) -> None: ...


class GhapiGitHubAdapter:
    """GitHubAdapter backed by ghapi (auto-generated from GitHub OpenAPI spec)."""

    def __init__(self, token: str = "") -> None:
        from ghapi.all import GhApi
        self._api = GhApi(token=token or None)

    def get_repo(self, repo: str) -> dict[str, Any]:
        owner, name = repo.split("/", 1)
        result = self._api.repos.get(owner=owner, repo=name)
        return dict(result)

    def create_issue(self, repo: str, title: str, body: str, labels: list[str]) -> dict[str, Any]:
        owner, name = repo.split("/", 1)
        result = self._api.issues.create(owner=owner, repo=name, title=title, body=body, labels=labels)
        return dict(result)

    def dispatch_workflow(self, repo: str, workflow: str, ref: str, inputs: dict[str, Any]) -> None:
        owner, name = repo.split("/", 1)
        self._api.actions.create_workflow_dispatch(
            owner=owner, repo=name, workflow_id=workflow, ref=ref, inputs=inputs
        )


class UrllibGitHubAdapter:
    """GitHubAdapter backed by stdlib urllib — zero extra deps, always available."""

    def __init__(self, token: str = "") -> None:
        self._token = token

    def _request(self, path: str, *, method: str = "GET", body: dict | None = None) -> Any:
        import json
        import urllib.request as _ur
        url = f"https://api.github.com/{path.lstrip('/')}"
        data = json.dumps(body).encode() if body else None
        headers: dict[str, str] = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "urace-github/1",
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        req = _ur.Request(url, data=data, method=method, headers=headers)
        with _ur.urlopen(req, timeout=15) as r:  # noqa: S310
            return json.loads(r.read().decode())

    def get_repo(self, repo: str) -> dict[str, Any]:
        return self._request(f"repos/{repo}")

    def create_issue(self, repo: str, title: str, body: str, labels: list[str]) -> dict[str, Any]:
        return self._request(f"repos/{repo}/issues", method="POST", body={"title": title, "body": body, "labels": labels})

    def dispatch_workflow(self, repo: str, workflow: str, ref: str, inputs: dict[str, Any]) -> None:
        self._request(
            f"repos/{repo}/actions/workflows/{workflow}/dispatches",
            method="POST",
            body={"ref": ref, "inputs": inputs},
        )


def make_github_adapter(token: str = "") -> GitHubAdapter:
    """Return GhapiGitHubAdapter if ghapi is available, else UrllibGitHubAdapter."""
    try:
        return GhapiGitHubAdapter(token=token)
    except ImportError:
        return UrllibGitHubAdapter(token=token)
