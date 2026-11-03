from __future__ import annotations

import difflib
import hashlib
import json
import os
import subprocess
import tempfile
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MAX_SPEC_BYTES = 1_048_576
MAX_MIGRATION_DIFF_BYTES = 131_072

# Default source for `urace update` — points to the latest runtime release.
# Override via URACE_RUNTIME_URL env var or config['updates']['source'].
URACE_RUNTIME_RELEASE_URL = os.environ.get(
    "URACE_RUNTIME_URL",
    "https://github.com/joaoalbertocsjunior/URACE/releases/latest/download/urace-runtime-manifest.json",
)


def _validate_runtime_bundle(content: bytes) -> str:
    """Validate a runtime update bundle (JSON manifest or wheel/sdist archive)."""
    if not content:
        raise ValueError("runtime bundle must not be empty")
    if len(content) > 32 * 1024 * 1024:
        raise ValueError("runtime bundle exceeds 32 MB size limit")
    # Try JSON manifest first (lightweight release descriptor)
    try:
        text = content.decode("utf-8")
        manifest = json.loads(text)
        required = ("version", "runtime_sha256", "release_url")
        missing = [k for k in required if k not in manifest]
        if missing:
            raise ValueError("runtime bundle manifest missing fields: " + ", ".join(missing))
        return text
    except (UnicodeDecodeError, json.JSONDecodeError):
        pass
    # Binary bundle: accept Python wheel (PK zip), gzip tarball, or plain tar
    if content[:2] == b"PK" or content[:3] == b"\x1f\x8b\x08" or content[257:262] == b"ustar":
        return "<binary-bundle:" + hashlib.sha256(content).hexdigest()[:12] + ">"
    raise ValueError(
        "runtime bundle must be a JSON manifest (with version/runtime_sha256/release_url) "
        "or a Python wheel/sdist archive"
    )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n"); stream.flush(); os.fsync(stream.fileno())
        temporary = Path(stream.name)
    temporary.replace(path)


def _atomic_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with tempfile.NamedTemporaryFile("wb", dir=path.parent, delete=False) as stream:
        stream.write(content); stream.flush(); os.fsync(stream.fileno())
        temporary = Path(stream.name)
    temporary.replace(path)
    os.chmod(path, 0o600)


_MIN_SPEC_BYTES = 10_240
_MIN_NORMATIVE_TERMS = 20
_MIN_HEADINGS = 10


def _validate_specification(content: bytes) -> str:
    if not content:
        raise ValueError(f"candidate specification must be at least {_MIN_SPEC_BYTES} bytes (got 0); likely truncated or incomplete")
    if len(content) > MAX_SPEC_BYTES:
        raise ValueError(f"candidate specification must contain 1..{MAX_SPEC_BYTES} bytes")
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError("candidate specification must be UTF-8") from error
    required = ("# URACE", "Normative Language", "Bootstrap Execution Requirements")
    missing = [marker for marker in required if marker not in text]
    if missing:
        raise ValueError("candidate specification is missing required structure: " + ", ".join(missing))
    if len(content) < _MIN_SPEC_BYTES:
        raise ValueError(f"candidate specification must be at least {_MIN_SPEC_BYTES} bytes (got {len(content)}); likely truncated or incomplete")
    normative_count = sum(text.count(term) for term in (" MUST", " SHOULD", " MAY"))
    if normative_count < _MIN_NORMATIVE_TERMS:
        raise ValueError(
            f"candidate specification has only {normative_count} normative terms (MUST/SHOULD/MAY); "
            f"requires at least {_MIN_NORMATIVE_TERMS} — likely not a complete URACE specification"
        )
    heading_count = sum(1 for line in text.splitlines() if line.startswith("#"))
    if heading_count < _MIN_HEADINGS:
        raise ValueError(
            f"candidate specification has only {heading_count} headings; "
            f"requires at least {_MIN_HEADINGS} — likely not a complete URACE specification"
        )
    return text


def _read_source(source: str, timeout: int = 20) -> tuple[bytes, str]:
    parsed = urllib.parse.urlparse(source)
    if parsed.scheme:
        if parsed.scheme != "https":
            raise ValueError("remote specification source must use HTTPS")
        request = urllib.request.Request(source, headers={"User-Agent": "URACE-update/1"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if urllib.parse.urlparse(response.geturl()).scheme != "https":
                raise ValueError("remote specification redirect must remain on HTTPS")
            length = response.headers.get("Content-Length")
            if length and int(length) > MAX_SPEC_BYTES:
                raise ValueError("candidate specification exceeds the download limit")
            content = response.read(MAX_SPEC_BYTES + 1)
        identity = urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))
        return content, identity
    path = Path(source).expanduser().resolve()
    if not path.is_file():
        raise ValueError(f"candidate specification not found: {path}")
    if path.stat().st_size > MAX_SPEC_BYTES:
        raise ValueError("candidate specification exceeds the download limit")
    return path.read_bytes(), str(path)


_GITHUB_RAW_PATTERN = "raw.githubusercontent.com"


def _source_revision(source_identity: str) -> dict[str, str] | None:
    # HTTPS GitHub raw URL: extract embedded commit SHA from path segments.
    # Pattern: raw.githubusercontent.com/{owner}/{repo}/{commit}/{path...}
    if _GITHUB_RAW_PATTERN in source_identity:
        parsed = urllib.parse.urlparse(source_identity)
        segments = parsed.path.lstrip("/").split("/")
        # segments: [owner, repo, commit, ...path]
        if len(segments) >= 4:
            commit = segments[2]
            if len(commit) in (40, 64):  # SHA-1 or SHA-256
                return {"commit": commit, "message": "", "source": "url-embedded"}
    path = Path(source_identity)
    if not path.is_file():
        return None
    result = subprocess.run(
        ["git", "-C", str(path.parent), "log", "-1", "--format=%H%n%s", "--", path.name],
        text=True, capture_output=True, check=False, timeout=15,
    )
    lines = result.stdout.strip().splitlines()
    return {"commit": lines[0], "message": lines[1] if len(lines) > 1 else ""} if result.returncode == 0 and lines else None


def _bootstrap_runtime_baseline(product_root: Path, state_root: Path) -> dict[str, Any] | None:
    """Attempt to create a baseline manifest from current runtime files when none exists.

    This is a best-effort bootstrap: it records current state as the baseline so
    future comparisons have a reference point. Returns the created manifest or None.
    """
    runtime_root = product_root / "urace/runtime"
    if not runtime_root.exists():
        return None
    files = {}
    for path in sorted(runtime_root.rglob("*")):
        if not path.is_file():
            continue
        if "__pycache__" in path.parts or path.name.endswith((".pyc", ".pyo")):
            continue
        relative = str(path.relative_to(product_root))
        try:
            files[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            pass
    if not files:
        return None
    manifest = {"accepted_at": _now(), "files": files, "bootstrapped": True,
                "note": "baseline bootstrapped from current runtime files; not a validated accepted snapshot"}
    manifest_path = state_root / "stable-runtime" / "manifest.json"
    _atomic_json(manifest_path, manifest)
    return manifest


def local_customization_inventory(product_root: Path, state_root: Path) -> dict[str, Any]:
    """Compare generated implementation files with the last accepted runtime snapshot."""
    manifest_path = state_root / "stable-runtime" / "manifest.json"
    if not manifest_path.exists():
        manifest = _bootstrap_runtime_baseline(product_root, state_root)
        if manifest is None:
            return {"status": "BASELINE_UNAVAILABLE", "changed": [], "missing": [], "added": []}
        return {"status": "BASELINE_BOOTSTRAPPED", "changed": [], "missing": [], "added": [],
                "note": "baseline created from current runtime files; no prior accepted snapshot available",
                "baseline_accepted_at": manifest.get("accepted_at")}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    accepted = manifest.get("files", {})
    changed, missing = [], []
    for relative, expected in accepted.items():
        path = product_root / relative
        if not path.exists():
            missing.append(relative)
        elif hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            changed.append(relative)
    runtime_root = product_root / "urace/runtime"
    current = {
        str(path.relative_to(product_root)) for path in runtime_root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and not path.name.endswith((".pyc", ".pyo"))
    } if runtime_root.exists() else set()
    added = sorted(current - set(accepted))
    return {
        "status": "LOCAL_CUSTOMIZATIONS_PRESENT" if changed or missing or added else "MATCHES_ACCEPTED_RUNTIME",
        "changed": sorted(changed), "missing": sorted(missing), "added": added,
        "baseline_accepted_at": manifest.get("accepted_at"),
    }


def _updates_root(state_root: Path) -> Path:
    return state_root.parent / "generated" / "updates"


def download(product_root: Path, state_root: Path, source: str, expected_hash: str | None = None) -> dict[str, Any]:
    content, source_identity = _read_source(source)
    # Runtime bundle vs legacy spec: spec files contain "# URACE" marker
    is_spec = b"# URACE" in content[:1024] or source.lower().endswith((".md", ".txt"))
    if is_spec:
        _validate_specification(content)
    else:
        _validate_runtime_bundle(content)
    digest = hashlib.sha256(content).hexdigest()
    if expected_hash is not None:
        import re
        if not re.fullmatch('[0-9a-fA-F]{64}',expected_hash):raise ValueError('Expected hash must be64 hexadecimal SHA-256 characters')
        if digest!=expected_hash.lower():raise ValueError('Candidate hash mismatch; download pointer unchanged')
    directory = _updates_root(state_root) / "candidates" / digest
    specification = directory / "URACE.md"
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    if specification.exists() and specification.read_bytes() != content:
        raise RuntimeError("candidate content mismatch at digest directory; existing candidate differs from new download")
    if not specification.exists():
        _atomic_bytes(specification, content)
    accepted = product_root / "URACE.md"
    accepted_sha256 = hashlib.sha256(accepted.read_bytes()).hexdigest()
    manifest = {
        "schema_version": 1, "downloaded_at": _now(), "source": source_identity,
        "sha256": digest, "bytes": len(content), "candidate": str(specification),
        "accepted_sha256_at_download": accepted_sha256,
        "migration_chain": {"from": accepted_sha256, "to": digest},
        "status": "DOWNLOADED",
        "source_revision": _source_revision(source_identity),
    }
    _atomic_json(directory / "manifest.json", manifest)
    _atomic_json(_updates_root(state_root) / "latest.json", {"sha256": digest, "candidate": str(specification)})
    return manifest


def resolve_candidate(state_root: Path, reference: str | None = None) -> tuple[Path, dict[str, Any]]:
    if reference and Path(reference).expanduser().is_file():
        path = Path(reference).expanduser().resolve()
        content = path.read_bytes(); _validate_specification(content)
        return path, {"sha256": hashlib.sha256(content).hexdigest(), "candidate": str(path), "source": str(path)}
    if reference:
        import re
        if not re.fullmatch('[0-9a-fA-F]{1,64}',reference):raise ValueError('Candidate reference must be a hash prefix or existing local specification file')
        reference=reference.lower()
        matches = list((_updates_root(state_root) / "candidates").glob(f"{reference}*/manifest.json"))
        if len(matches) != 1:
            raise ValueError("candidate reference is missing or ambiguous")
        manifest_path = matches[0]
    else:
        latest = _updates_root(state_root) / "latest.json"
        if not latest.exists():
            raise ValueError("no downloaded update candidate; run `urace update download SOURCE`")
        pointer = json.loads(latest.read_text(encoding="utf-8"))
        import re
        if not isinstance(pointer,dict) or not isinstance(pointer.get("sha256"),str) or not re.fullmatch("[0-9a-f]{64}",pointer["sha256"]):
            raise ValueError("Invalid update candidate pointer SHA-256")
        manifest_path = _updates_root(state_root) / "candidates" / pointer["sha256"] / "manifest.json"
    candidates = (_updates_root(state_root) / "candidates").resolve()
    if not manifest_path.resolve().is_relative_to(candidates) or manifest_path.is_symlink():
        raise ValueError("Managed update manifest escapes candidate storage")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest,dict) or manifest.get("sha256") != manifest_path.parent.name or not isinstance(manifest.get("candidate"),str):
        raise ValueError("Invalid managed update candidate manifest")
    path = Path(manifest["candidate"])
    expected = manifest_path.parent / "URACE.md"
    if path != expected or path.is_symlink() or path.resolve() != expected.absolute() or not path.resolve().is_relative_to(candidates):
        raise ValueError("Managed update candidate escapes its digest directory")
    content = path.read_bytes(); _validate_specification(content)
    if hashlib.sha256(content).hexdigest() != manifest["sha256"]:
        raise RuntimeError("candidate specification hash mismatch")
    return path, manifest


def explain(product_root: Path, state_root: Path, reference: str | None = None) -> dict[str, Any]:
    candidate, manifest = resolve_candidate(state_root, reference)
    accepted_text = (product_root / "URACE.md").read_text(encoding="utf-8")
    candidate_text = candidate.read_text(encoding="utf-8")
    diff = "".join(difflib.unified_diff(accepted_text.splitlines(True), candidate_text.splitlines(True), fromfile="accepted/URACE.md", tofile="candidate/URACE.md"))
    customizations = local_customization_inventory(product_root, state_root)
    report = {
        "schema_version": 1, "explained_at": _now(), "status": "NO_CHANGE" if not diff else "REVIEW_REQUIRED",
        "accepted_sha256": hashlib.sha256(accepted_text.encode()).hexdigest(), "candidate_sha256": manifest["sha256"],
        "source": manifest.get("source"), "diff_bytes": len(diff.encode()),
        "added_lines": sum(1 for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++")),
        "removed_lines": sum(1 for line in diff.splitlines() if line.startswith("-") and not line.startswith("---")),
        "accepted_headings": sum(1 for line in accepted_text.splitlines() if line.startswith("#")),
        "candidate_headings": sum(1 for line in candidate_text.splitlines() if line.startswith("#")),
        "accepted_normative_terms": sum(accepted_text.count(term) for term in (" MUST", " SHOULD", " MAY")),
        "candidate_normative_terms": sum(candidate_text.count(term) for term in (" MUST", " SHOULD", " MAY")),
        "source_revision": manifest.get("source_revision"),
        "local_customizations": customizations,
        "compatibility_status": "CUSTOMIZATION_REVIEW_REQUIRED" if customizations["status"] == "LOCAL_CUSTOMIZATIONS_PRESENT" else "NO_KNOWN_LOCAL_DRIFT",
        "application_rule": "preserve local choices; pause for operator resolution when candidate requirements conflict with them",
    }
    report_path = _updates_root(state_root) / "candidates" / manifest["sha256"] / "explanation.json"
    _atomic_json(report_path, report)
    inventory_path = _updates_root(state_root) / "personalizations.json"
    prior = json.loads(inventory_path.read_text(encoding="utf-8")) if inventory_path.exists() else {"snapshots": []}
    prior["snapshots"] = (prior.get("snapshots", []) + [{"at": report["explained_at"], "candidate_sha256": manifest["sha256"], **customizations}])[-100:]
    _atomic_json(inventory_path, prior)
    report["report"] = str(report_path)
    return report


# Files whose modification requires rebootstrap scope (runtime self-evolution).
_RUNTIME_SCOPE_PREFIXES = ("urace/runtime/", "urace/launcher", "urace/evolution_guard")

# Structured conflict resolution schema embedded in migration payload.
_CONFLICT_RESOLUTION_SCHEMA = {
    "strategy": None,  # "prefer_candidate" | "prefer_local" | "manual_merge"
    "affected_files": [],
    "resolution_text": "",
    "note": (
        "When candidate requirements conflict with local choices, do NOT silently normalize. "
        "Set strategy, list affected_files, and provide resolution_text explaining the conflict "
        "and the chosen resolution. Wait for operator attributable confirmation before applying."
    ),
}

# Instruction-pattern prefixes that must not appear inside embedded diff content.
_INJECTION_SIGNAL_PREFIXES = (
    "ignore previous", "disregard", "system:", "you are", "assistant:",
    "new instruction", "override:", "forget ",
)


def _sanitize_diff_for_embedding(diff: str) -> tuple[str, list[str]]:
    """Strip diff lines that look like prompt-injection attempts.

    Returns (sanitized_diff, flagged_lines).
    """
    flagged: list[str] = []
    clean_lines: list[str] = []
    for line in diff.splitlines(keepends=True):
        lower = line.lstrip("+-@ ").lower()
        if any(lower.startswith(sig) for sig in _INJECTION_SIGNAL_PREFIXES):
            flagged.append(line.rstrip())
            clean_lines.append("# [REDACTED: potential injection signal]\n")
        else:
            clean_lines.append(line)
    return "".join(clean_lines), flagged


def _detect_migration_scope(diff: str) -> str:
    """Return 'rebootstrap' if the diff touches runtime files; 'documentation' otherwise."""
    for line in diff.splitlines():
        if not (line.startswith("---") or line.startswith("+++")):
            continue
        path_part = line[4:].strip()
        if any(path_part.startswith(prefix) for prefix in _RUNTIME_SCOPE_PREFIXES):
            return "rebootstrap"
    return "documentation"


def migration_payload(product_root: Path, state_root: Path, reference: str | None = None) -> dict[str, Any]:
    candidate, manifest = resolve_candidate(state_root, reference)
    report = explain(product_root, state_root, reference)
    if report["status"] == "NO_CHANGE":
        raise ValueError("candidate specification is identical to the accepted specification")
    accepted_text = (product_root / "URACE.md").read_text(encoding="utf-8")
    candidate_text = candidate.read_text(encoding="utf-8")
    diff = "".join(difflib.unified_diff(
        accepted_text.splitlines(True), candidate_text.splitlines(True),
        fromfile="accepted/URACE.md", tofile="candidate/URACE.md",
    ))
    if len(diff.encode()) > MAX_MIGRATION_DIFF_BYTES:
        raise ValueError("specification delta exceeds the bounded migration-input limit")

    sanitized_diff, flagged_lines = _sanitize_diff_for_embedding(diff)
    scope = _detect_migration_scope(diff)

    return {
        "title": f"Migrate generated URACE implementation to specification {manifest['sha256'][:12]}",
        "success_measure": (
            "Accepted and candidate validation pass; state remains compatible; "
            "activation health succeeds or stable rollback restores the accepted implementation"
        ),
        "reason": (
            "Apply this attributable specification delta as migration input. "
            "Preserve Product work, durable state, and the recorded local-customization inventory. "
            "Never overwrite or silently normalize a conflicting local choice: "
            "populate conflict_resolution_protocol with strategy, affected_files, and resolution_text, "
            "and wait for the operator's attributable choice before applying. "
            "Do not directly patch state."
        ),
        "migration_diff": sanitized_diff,
        "injection_flagged_lines": flagged_lines,
        "conflict_resolution_protocol": dict(_CONFLICT_RESOLUTION_SCHEMA),
        "scope": scope,
        "target": "urace", "priority": 100, "expected_value": 0.9, "estimated_cost": 0.7,
        "risk": 0.6, "urgency": 0.7,
        "necessity_evidence": "Authoritative update apply request for a downloaded, hash-verified specification candidate",
        "lower_impact_route_sufficient": False,
        "dependencies": [], "deadline": None, "not_before": None,
        "estimate": {}, "estimate_confidence": "low",
        "priority_floor": 100, "priority_ceiling": 100, "pinned": True,
        "update_candidate": {
            "sha256": manifest["sha256"],
            "source": manifest.get("source"),
            "source_revision": manifest.get("source_revision"),
            "migration_chain": manifest.get("migration_chain"),
            "explanation": report["report"],
            "local_customizations": report["local_customizations"],
        },
    }
