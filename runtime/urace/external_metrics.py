from __future__ import annotations

import json
import math
import os
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _read_json_response(response: Any, maximum_bytes: int) -> Any:
    content = response.read(maximum_bytes + 1)
    if len(content) > maximum_bytes:
        raise ValueError(f"external JSON response exceeds {maximum_bytes} bytes")
    return json.loads(content)


def _get_json(url: str, timeout: float, maximum_bytes: int, headers: dict[str, str] | None = None) -> Any:
    request = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "URACE-metrics", **(headers or {})})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return _read_json_response(response, maximum_bytes)


def _github_repository(source: dict[str, Any], timeout: float, maximum_bytes: int = 1048576) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    owner, repository = source["repository"].split("/", 1)
    base = f"https://api.github.com/repos/{owner}/{repository}"
    repo = _get_json(base, timeout, maximum_bytes)
    issues = _get_json(base + "/issues?state=all&sort=updated&direction=desc&per_page=20", timeout, maximum_bytes)
    pulls = _get_json(base + "/pulls?state=all&sort=updated&direction=desc&per_page=20", timeout, maximum_bytes)
    releases = _get_json(base + "/releases?per_page=10", timeout, maximum_bytes)
    events = [{
        "kind": "issue", "id": str(item.get("id", "")), "number": item.get("number"), "state": item.get("state"),
        "title": item.get("title", ""), "updated_at": item.get("updated_at", ""), "url": item.get("html_url", ""), "untrusted_content": True,
    } for item in issues if isinstance(item, dict) and "pull_request" not in item and item.get("updated_at")]
    events.extend({
        "kind": "pull_request", "id": str(item.get("id", "")), "number": item.get("number"), "state": item.get("state"),
        "title": item.get("title", ""), "updated_at": item.get("updated_at", ""), "url": item.get("html_url", ""), "untrusted_content": True,
    } for item in pulls if isinstance(item, dict) and item.get("updated_at"))
    events.extend({
        "kind": "release", "id": str(item.get("id", "")), "tag": item.get("tag_name", ""), "state": "draft" if item.get("draft") else "published",
        "title": item.get("name") or item.get("tag_name", ""), "updated_at": item.get("published_at") or item.get("created_at", ""), "url": item.get("html_url", ""), "untrusted_content": True,
    } for item in releases if isinstance(item, dict) and (item.get("published_at") or item.get("created_at")))
    pushed_at = repo.get("pushed_at") or repo.get("updated_at", "")
    if pushed_at:
        events.append({
            "kind": "repository_push", "id": repo.get("full_name", ""), "state": "observed",
            "title": f"default branch {repo.get('default_branch', 'unknown')}",
            "updated_at": pushed_at, "url": repo.get("html_url", ""), "untrusted_content": False,
        })
    events.sort(key=lambda item: item["updated_at"], reverse=True)
    missing = [key for key in ("stargazers_count", "forks_count", "subscribers_count", "open_issues_count") if key not in repo]
    if missing:
        raise KeyError(f"GitHub repository response missing expected fields: {', '.join(missing)}")
    values = {"stars": repo["stargazers_count"], "forks": repo["forks_count"], "watching": repo["subscribers_count"], "open_issues_and_pulls": repo["open_issues_count"]}
    return values, events[:50]


class SourceSchemaMismatch(Exception):
    """Raised when a source is reachable but the configured metric path does not resolve."""


def _lookup(value: Any, path: str) -> Any:
    try:
        for part in path.split("."):
            value = value[int(part)] if isinstance(value, list) else value[part]
    except (KeyError, IndexError, TypeError) as error:
        raise SourceSchemaMismatch(f"metric path {path!r} not found in source response") from error
    if not isinstance(value, (int, float, bool)):
        raise ValueError(f"metric path {path!r} did not resolve to a scalar")
    if isinstance(value,float) and not math.isfinite(value):
        raise ValueError(f"metric path {path!r} did not resolve to a finite measurement")
    return value


def collect(root: Path, settings: dict[str, Any], last_known_good: dict[str, Any] | None = None) -> dict[str, Any]:
    mode = settings.get("mode", "DISABLED").upper()
    observed_at = datetime.now(timezone.utc).isoformat()
    if mode == "DISABLED":
        return {"at": observed_at, "mode": mode, "observations": [], "errors": [], "last_known_good": last_known_good or {}}
    observations, errors = [], []
    updated_lkg: dict[str, Any] = dict(last_known_good or {})
    maximum_bytes = int(settings.get("max_response_bytes", 1048576))
    if maximum_bytes < 1024:
        raise ValueError("external metric max_response_bytes must be at least 1024")
    for source in settings.get("sources", []):
        source_id = source.get("id", "unknown")
        try:
            kind = source["kind"]
            events: list[dict[str, Any]] = []
            if kind == "github_repository":
                values, events = _github_repository(source, float(settings.get("timeout_seconds", 10)), maximum_bytes)
                payload = None
            elif kind == "json_file":
                path = Path(source["location"])
                path = path if path.is_absolute() else root / path
                if settings.get("confine_file_sources"):
                    from .outcome_verification import _read
                    relative=path.absolute().relative_to(root.absolute())
                    if any(part.startswith('.') for part in relative.parts):raise ValueError("Hidden/private files are not value research sources")
                    payload=_read(root, {"source":str(relative)}, [])
                    if len(json.dumps(payload).encode())>maximum_bytes:raise ValueError("External JSON exceeds response allowance")
                else:
                    with path.open("rb") as source_file:
                        content = source_file.read(maximum_bytes + 1)
                    if len(content) > maximum_bytes:
                        raise ValueError(f"external JSON file exceeds {maximum_bytes} bytes")
                    payload = json.loads(content)
            elif kind == "http_json":
                if urllib.parse.urlparse(source["location"]).scheme not in {"http", "https"}:
                    raise ValueError("http_json source requires an http or https URL")
                request = urllib.request.Request(source["location"])
                credential_env = source.get("credential_env")
                if credential_env:
                    secret = os.environ.get(credential_env)
                    if not secret:
                        raise RuntimeError(f"credential environment variable {credential_env} is unavailable")
                    request.add_header(source.get("credential_header", "Authorization"), source.get("credential_prefix", "Bearer ") + secret)
                with urllib.request.urlopen(request, timeout=float(settings.get("timeout_seconds", 10))) as response:
                    payload = _read_json_response(response, maximum_bytes)
            elif kind == "self_measurement":
                from . import self_metrics as _sm
                src = _sm.as_external_source(root)
                if src is None:
                    raise ValueError("self_measurement: no collected data; run 'urace self-metrics collect' first")
                values = src.get("values", {})
                payload = None
            else:
                raise ValueError(f"unsupported metric source kind: {kind}")
            if kind not in ("github_repository", "self_measurement"):
                values = {name: _lookup(payload, path) for name, path in source.get("values", {}).items()}
            updated_lkg[source_id] = {"value": values, "at": observed_at, "source": source_id}
            observations.append({"source": source_id, "visibility": source.get("visibility", "private"), "values": values, "events": events})
        except SourceSchemaMismatch as error:
            prior_lkg = updated_lkg.get(source_id)
            errors.append({"source": source_id, "error": str(error), "kind": "SOURCE_SCHEMA_MISMATCH", **({"last_known_good": prior_lkg} if prior_lkg else {})})
        except Exception as error:
            prior_lkg = updated_lkg.get(source_id)
            errors.append({"source": source_id, "error": str(error), **({"last_known_good": prior_lkg} if prior_lkg else {})})
    return {"at": observed_at, "mode": mode, "observations": observations, "errors": errors, "last_known_good": updated_lkg}
