"""Git operations and workflow automation for GitHub-attached products."""
from __future__ import annotations
import subprocess
from pathlib import Path

SAFE_GIT_SUBCOMMANDS: frozenset[str] = frozenset({
    "status", "log", "diff", "branch", "checkout", "pull", "push",
    "commit", "add", "fetch", "merge", "rebase", "reset", "stash",
    "show", "tag", "remote", "rev-parse", "shortlog", "clone",
})

# Defaults: pull before cycles (safe/read-only); commit + push require explicit intent
WORKFLOW_DEFAULTS: dict[str, object] = {
    "auto_pull": True,
    "auto_commit": False,
    "auto_push": False,
    "commit_message_template": "feat: URACE improvement cycle {cycle_id}",
    "branch_strategy": "current",
}


def workflow_settings(config: dict) -> dict:
    """Return effective github_workflow settings, merged with defaults."""
    stored = config.get("github_workflow") or {}
    return {**WORKFLOW_DEFAULTS, **{k: v for k, v in stored.items() if v is not None}}


def _run(root: str | Path, *args: str, timeout: int = 60) -> tuple[int, str, str]:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        text=True, capture_output=True, timeout=timeout,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def clone_repo(github_repo: str, clone_to: str | Path, timeout: int = 120) -> tuple[int, str, str]:
    """Clone github_repo ('owner/repo') to clone_to path."""
    url = f"https://github.com/{github_repo}.git"
    result = subprocess.run(
        ["git", "clone", url, str(clone_to)],
        text=True, capture_output=True, timeout=timeout,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def head_commit(clone_path: str | Path) -> str | None:
    """Return HEAD commit SHA, or None if unavailable."""
    rc, out, _ = _run(clone_path, "rev-parse", "HEAD")
    return out if rc == 0 else None


def validate_subcommand(args: list[str]) -> str | None:
    """Return error string if subcommand is not permitted, else None."""
    if not args:
        return "no git subcommand provided"
    if args[0] not in SAFE_GIT_SUBCOMMANDS:
        allowed = ", ".join(sorted(SAFE_GIT_SUBCOMMANDS))
        return f"git subcommand '{args[0]}' not permitted; allowed: {allowed}"
    return None


def run_git(clone_path: str | Path, args: list[str], timeout: int = 60) -> tuple[int, str, str]:
    """Run a validated git command in clone_path."""
    return _run(clone_path, *args, timeout=timeout)


def auto_pull(clone_path: str | Path, config: dict) -> dict:
    """Pull latest if auto_pull is enabled. Returns event dict."""
    wf = workflow_settings(config)
    if not wf.get("auto_pull"):
        return {"action": "pull", "skipped": True, "reason": "auto_pull disabled"}
    if not Path(clone_path).is_dir():
        return {"action": "pull", "skipped": True, "reason": "clone_path not found"}
    rc, out, err = _run(clone_path, "pull", "--ff-only", timeout=60)
    return {"action": "pull", "skipped": False, "exit_code": rc, "stdout": out, "stderr": err, "ok": rc == 0}


def auto_commit(clone_path: str | Path, config: dict, cycle_id: str = "") -> dict:
    """Commit staged changes if auto_commit is enabled. Returns event dict."""
    wf = workflow_settings(config)
    if not wf.get("auto_commit"):
        return {"action": "commit", "skipped": True, "reason": "auto_commit disabled"}
    if not Path(clone_path).is_dir():
        return {"action": "commit", "skipped": True, "reason": "clone_path not found"}
    template = str(wf.get("commit_message_template", WORKFLOW_DEFAULTS["commit_message_template"]))
    message = template.replace("{cycle_id}", cycle_id or "unknown")
    rc, out, err = _run(clone_path, "commit", "-a", "-m", message, timeout=30)
    return {"action": "commit", "skipped": False, "exit_code": rc, "stdout": out, "stderr": err, "ok": rc == 0, "message": message}


def auto_push(clone_path: str | Path, config: dict) -> dict:
    """Push to origin if auto_push is enabled. Returns event dict."""
    wf = workflow_settings(config)
    if not wf.get("auto_push"):
        return {"action": "push", "skipped": True, "reason": "auto_push disabled — explicit push required"}
    if not Path(clone_path).is_dir():
        return {"action": "push", "skipped": True, "reason": "clone_path not found"}
    rc, out, err = _run(clone_path, "push", timeout=60)
    return {"action": "push", "skipped": False, "exit_code": rc, "stdout": out, "stderr": err, "ok": rc == 0}
