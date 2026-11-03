"""Compaction and Retention system — §62f of URACE.md.

Implements:
  - CompactionEngine: compact/decompact governed list fields
  - CompactionManifest: load/save/verify
  - CompactionIndex: per-archive O(1) lookup index (§62e r3)
  - ArchiveAmendmentLog: in-archive record amendment without full round-trip (§62e r3)
  - Retention threshold checking
  - urace compact / urace decompact / urace amend CLI support

All compaction MUST occur only at safe lifecycle boundaries (after a Checkpoint
is accepted and before the next cycle begins). The caller is responsible for
enforcing the boundary requirement.

Lossless guarantee: ARCHIVE mode preserves originals in an archive JSON file;
decompaction restores them and verifies the SHA-256 digest.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from . import primitives as _primitives


# ── Helpers ───────────────────────────────────────────────────────────────────

def _archive_path(state_path,relative):
    base=Path(state_path).resolve();path=(base/relative).resolve()
    if Path(relative).is_absolute() or not path.is_relative_to(base):raise ValueError("Archive path escapes state directory")
    return path


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_id(prefix: str) -> str:
    raw = os.urandom(5).hex()
    return f"{prefix}-{raw}"


def _canonical_digest(records: list) -> str:
    """SHA-256 of the canonical JSON serialization of *records*."""
    serialized = json.dumps(records, sort_keys=True, separators=(",", ":"),
                            ensure_ascii=True).encode()
    return hashlib.sha256(serialized).hexdigest()


# ── Default governance table (§62f) ──────────────────────────────────────────

_DEFAULT_GOVERNANCE: dict[str, dict] = {
    "external_metric_state.latest": {
        "max_entries": 1000,
        "compaction_mode": "ROLLING_EVICTION",
    },
    "executor_state.failures": {
        "max_entries": 500,
        "compaction_mode": "ARCHIVE",
        "archive_subpath": "archives/executor-failures",
    },
    "decision_records": {
        "max_entries": 2000,
        "compaction_mode": "ARCHIVE",
        "archive_subpath": "archives/decision-records",
    },
    "status_transitions": {
        "max_entries": 500,
        "compaction_mode": "ARCHIVE",
        "archive_subpath": "archives/status-transitions",
    },
    "evidence": {
        "max_entries": 5000,
        "compaction_mode": "ARCHIVE",
        "archive_subpath": "archives/evidence",
    },
    "operations": {
        "max_entries": 2000,
        "compaction_mode": "ARCHIVE",
        "archive_subpath": "archives/operations",
    },
    "trace_records": {
        "max_entries": 1000,
        "compaction_mode": "ARCHIVE",
        "archive_subpath": "archives/trace-records",
    },
    "community_signals": {
        "max_entries": 500,
        "compaction_mode": "ROLLING_EVICTION",
    },
    "patch_proposals": {
        "max_entries": 500,
        "compaction_mode": "ARCHIVE",
        "archive_subpath": "archives/patch-proposals",
    },
    "wake_registrations": {
        "max_entries": 200,
        "compaction_mode": "ARCHIVE",
        "archive_subpath": "archives/wake-registrations",
    },
    # PROHIBITED fields — cannot be compacted (active health signals / audit spine)
    "compaction_manifest.events": {"compaction_mode": "PROHIBITED"},
    "change_history": {"compaction_mode": "PROHIBITED"},
    "integrity_gaps": {"compaction_mode": "PROHIBITED"},
    "objectives": {"compaction_mode": "PROHIBITED"},
}

_PROHIBITED_FIELDS = frozenset(
    k for k, v in _DEFAULT_GOVERNANCE.items()
    if v.get("compaction_mode") == "PROHIBITED"
)

# Fields where records with active=True must never be eligible for compaction
_ACTIVE_GUARD_FIELDS: frozenset[str] = frozenset({
    "integrity_gaps",
    "community_signals",
    "patch_proposals",
})


# ── CompactionManifest I/O ────────────────────────────────────────────────────

MANIFEST_FILENAME = "compaction-manifest.json"


def manifest_path(state_path: str) -> Path:
    return Path(state_path) / MANIFEST_FILENAME


def load_manifest(state_path: str) -> dict | None:
    """Load CompactionManifest from disk. Returns None if it doesn't exist."""
    p = manifest_path(state_path)
    if not p.exists():
        return None
    with p.open("r", encoding="utf-8") as f:
        manifest = json.load(f)
    _primitives.validate("CompactionManifest", manifest)
    return manifest


def save_manifest(state_path: str, manifest: dict) -> None:
    """Atomically write CompactionManifest to disk."""
    _primitives.validate("CompactionManifest", manifest)
    p = manifest_path(state_path)
    tmp = p.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=True)
        f.flush()
        os.fsync(f.fileno())
    tmp.replace(p)


def _append_event(state_path: str, event: dict) -> dict:
    """Append *event* to the manifest (creating it if absent). Returns updated manifest."""
    manifest = load_manifest(state_path)
    if manifest is None:
        manifest = {
            "id": _make_id("man"),
            "version": 0,
            "updated_at": _now_iso(),
            "events": [],
        }
    manifest["events"].append(event)
    manifest["version"] = len(manifest["events"])
    manifest["updated_at"] = _now_iso()
    manifest["last_compacted_at"] = _now_iso()
    save_manifest(state_path, manifest)
    return manifest


# ── Startup verification ──────────────────────────────────────────────────────

def verify_manifest_on_startup(state_path: str) -> list[dict]:
    """Verify CompactionManifest integrity on lifecycle start.

    Returns a list of IntegrityGap dicts (may be empty) for any issues found.
    Caller inserts them into state["integrity_gaps"].
    """
    p = manifest_path(state_path)
    gaps: list[dict] = []

    if not p.exists():
        return gaps

    try:
        manifest = load_manifest(state_path)
    except (json.JSONDecodeError, ValueError) as exc:
        gaps.append(_make_gap(
            "compaction-manifest-divergence",
            f"CompactionManifest failed to load or validate: {exc}",
            "BLOCKING",
        ))
        return gaps

    if manifest["version"] != len(manifest["events"]):
        gaps.append(_make_gap(
            "compaction-manifest-divergence",
            f"CompactionManifest.version={manifest['version']} != "
            f"len(events)={len(manifest['events'])}",
            "BLOCKING",
        ))

    for event in manifest["events"]:
        if event.get("compaction_mode") == "ARCHIVE":
            archive = event.get("archive_path")
            if not archive:
                gaps.append(_make_gap(
                    "compaction-manifest-divergence",
                    f"CompactionEvent {event.get('id')} has mode ARCHIVE but no archive_path",
                    "BLOCKING",
                ))
                continue
            full_archive = _archive_path(state_path,archive)
            if not full_archive.exists():
                gaps.append(_make_gap(
                    "compaction-manifest-divergence",
                    f"Archive file missing for CompactionEvent {event.get('id')}: {archive}",
                    "BLOCKING",
                ))
            else:
                # Verify digest integrity (amendment-aware: use last after_digest if amended)
                try:
                    with full_archive.open("r", encoding="utf-8") as f:
                        _archive_data = json.load(f)
                    _actual = _canonical_digest(_archive_data)
                    _expected = _get_expected_digest(full_archive, event.get("original_digest", ""))
                    if _expected and _actual != _expected:
                        gaps.append(_make_gap(
                            "compaction-manifest-divergence",
                            f"Archive digest mismatch for CompactionEvent {event.get('id')}: "
                            f"expected {_expected}, got {_actual}",
                            "BLOCKING",
                        ))
                except (OSError, json.JSONDecodeError) as exc:
                    gaps.append(_make_gap(
                        "compaction-manifest-divergence",
                        f"Archive file unreadable for CompactionEvent {event.get('id')}: {exc}",
                        "BLOCKING",
                    ))

    return gaps


def _make_gap(kind: str, description: str, severity: str) -> dict:
    return {
        "id": _make_id("gap"),
        "kind": kind,
        "at": _now_iso(),
        "description": description,
        "severity": severity,
        "source": "compaction",
        "active": True,
        "resolved_at": None,
        "evidence_id": None,
    }


def _get_expected_digest(archive_path: Path, original_digest: str) -> str:
    """Return the expected digest for an archive, accounting for amendments.

    If amendments exist, the expected digest is the last after_digest in the
    amendment log. original_digest is preserved as the immutable audit anchor.
    """
    amendments = load_amendments(archive_path)
    if amendments:
        return amendments[-1]["after_digest"]
    return original_digest


# ── Retention threshold checking ──────────────────────────────────────────────

def check_retention_violations(
    state: dict,
    retention_policies: list[dict] | None = None,
) -> list[dict]:
    """Return IntegrityGap dicts for governed list fields that exceed their ceiling.

    Checks both explicit RetentionPolicy records and the default governance table.
    """
    gaps: list[dict] = []
    policies: dict[str, dict] = dict(_DEFAULT_GOVERNANCE)
    if retention_policies:
        for rp in retention_policies:
            policies[rp["target_field"]] = rp

    def _check(field_path: str, count: int) -> None:
        policy = policies.get(field_path)
        if not policy:
            return
        if policy.get("compaction_mode") == "PROHIBITED":
            return
        ceiling = policy.get("max_entries")
        if ceiling and count > ceiling:
            gaps.append(_make_gap(
                "retention-policy-violated",
                f"Field '{field_path}' has {count} entries, "
                f"exceeding ceiling of {ceiling}",
                "WARNING",
            ))

    _check("decision_records", len(state.get("decision_records") or []))
    executor_state = state.get("executor_state") or {}
    _check("executor_state.failures", len(executor_state.get("failures") or []))
    ext_metric = state.get("external_metric_state") or {}
    _check("external_metric_state.latest", len(ext_metric.get("latest") or []))
    _check("status_transitions", len(state.get("status_transitions") or []))
    _check("evidence", len(state.get("evidence") or []))
    _check("operations", len(state.get("operations") or []))
    _check("trace_records", len(state.get("trace_records") or []))
    _check("community_signals", len(state.get("community_signals") or []))
    _check("patch_proposals", len(state.get("patch_proposals") or []))
    _check("wake_registrations", len(state.get("wake_registrations") or []))

    return gaps


def _governance_archive_subpath(field_path: str, policy: dict) -> str:
    """Return the archive subdirectory path for a governed field."""
    return policy.get("archive_subpath", f"archives/{field_path.replace('.', '-')}")


def _count_archive_files(archive_dir: Path) -> int:
    """Count JSON archive files in *archive_dir* (excluding index files)."""
    return sum(
        1 for f in archive_dir.iterdir()
        if f.suffix == ".json" and not f.stem.endswith(".idx")
    )


def check_archive_ceiling(state_path: str, max_archives: int = 10) -> list[dict]:
    """Emit WARNING gap when any governed field has accumulated too many archive files.

    Returns list of IntegrityGap dicts (may be empty).
    """
    gaps: list[dict] = []
    sp = Path(state_path)
    for field_path, policy in _DEFAULT_GOVERNANCE.items():
        if policy.get("compaction_mode") != "ARCHIVE":
            continue
        archive_dir = _archive_path(sp,_governance_archive_subpath(field_path,policy))
        if not archive_dir.exists():
            continue
        count = _count_archive_files(archive_dir)
        if count > max_archives:
            gaps.append(_make_gap(
                "archive-count-ceiling",
                f"Field '{field_path}' has {count} archive files (ceiling: {max_archives}); "
                "consider decompact-and-recompact to consolidate",
                "WARNING",
            ))
    return gaps


def get_compaction_status(state_path: str) -> dict:
    """Return compaction status summary for operator visibility."""
    manifest = load_manifest(state_path)
    sp = Path(state_path)
    archive_counts: dict[str, int] = {}
    for field_path, policy in _DEFAULT_GOVERNANCE.items():
        if policy.get("compaction_mode") != "ARCHIVE":
            continue
        archive_dir = _archive_path(sp,_governance_archive_subpath(field_path,policy))
        if archive_dir.exists():
            archive_counts[field_path] = _count_archive_files(archive_dir)
    if manifest is None:
        return {
            "has_manifest": False,
            "event_count": 0,
            "last_compacted_at": None,
            "governed_fields": list(_DEFAULT_GOVERNANCE.keys()),
            "archive_counts": archive_counts,
        }
    return {
        "has_manifest": True,
        "event_count": manifest["version"],
        "last_compacted_at": manifest.get("last_compacted_at"),
        "governed_fields": list(_DEFAULT_GOVERNANCE.keys()),
        "archive_counts": archive_counts,
    }


# ── CompactionIndex I/O (§62e r3) ────────────────────────────────────────────

def _index_path(archive_path: Path) -> Path:
    return archive_path.with_suffix(".idx.json")


def _amendments_path(archive_path: Path) -> Path:
    return archive_path.parent / (archive_path.stem + ".amendments.jsonl")


def _write_index(archive_path: Path, compaction_event_id: str, records: list) -> None:
    """Write (or overwrite) a CompactionIndex for *archive_path*."""
    id_to_offset: dict[str, int] = {}
    kind_to_ids: dict[str, list[str]] = {}
    time_buckets: dict[str, list[str]] = {}

    for i, rec in enumerate(records):
        if not isinstance(rec, dict):
            continue
        rid = rec.get("id")
        if isinstance(rid, str):
            id_to_offset[rid] = i
            kind = rec.get("kind")
            if isinstance(kind, str):
                kind_to_ids.setdefault(kind, []).append(rid)
            ts_str = (rec.get("decided_at") or rec.get("created_at")
                      or rec.get("at") or "")
            if ts_str and len(ts_str) >= 7:
                bucket = ts_str[:7]  # "YYYY-MM"
                time_buckets.setdefault(bucket, []).append(rid)

    index: dict = {
        "compaction_event_id": compaction_event_id,
        "archive_path": str(archive_path),
        "generated_at": _now_iso(),
        "record_count": len(records),
        "id_to_offset": id_to_offset,
        "kind_to_ids": kind_to_ids,
    }
    if time_buckets:
        index["time_buckets"] = time_buckets

    _primitives.validate("CompactionIndex", index)
    idx_p = _index_path(archive_path)
    tmp = idx_p.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=True)
        f.flush()
        os.fsync(f.fileno())
    tmp.replace(idx_p)


def load_index(archive_path: Path) -> dict | None:
    """Load the CompactionIndex for *archive_path*. Returns None if absent or stale."""
    idx_p = _index_path(archive_path)
    if not idx_p.exists():
        return None
    try:
        with idx_p.open("r", encoding="utf-8") as f:
            index = json.load(f)
        _primitives.validate("CompactionIndex", index)
        return index
    except (json.JSONDecodeError, ValueError):
        return None


# ── ArchiveAmendmentLog I/O (§62e r3) ────────────────────────────────────────

def _append_amendment(archive_path: Path, amendment: dict) -> None:
    """Append *amendment* to the archive's .amendments.jsonl file."""
    _primitives.validate("ArchiveAmendment", amendment)
    amd_p = _amendments_path(archive_path)
    from .authenticated_journal import append_row
    append_row(amd_p,amendment)


def load_amendments(archive_path: Path) -> list[dict]:
    """Load all ArchiveAmendment records for *archive_path*. Returns empty list if absent."""
    amd_p = _amendments_path(archive_path)
    if not amd_p.exists():
        return []
    amendments: list[dict] = []
    with amd_p.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    amd = json.loads(line)
                    _primitives.validate("ArchiveAmendment", amd)
                    amendments.append(amd)
                except (json.JSONDecodeError, ValueError):
                    pass  # corrupt line: skip but don't fail
    return amendments


# ── CompactionEngine ──────────────────────────────────────────────────────────

class CompactionEngine:
    """Performs ARCHIVE and ROLLING_EVICTION compaction on governed list fields.

    Usage:
        engine = CompactionEngine(state_path="/path/to/.urace/state")
        summary, event = engine.compact_field(
            state=state_dict,
            field_path="executor_state.failures",
            policy=retention_policy_dict,
            authorized_by="inp-abc1234567",
        )
        # persist state_dict back to disk
    """

    def __init__(self, state_path: str):
        self.state_path = state_path

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _resolve_field(self, state: dict, field_path: str) -> tuple[dict, str]:
        """Return (parent_dict, leaf_key) for a dot-path like 'executor_state.failures'."""
        parts = field_path.split(".")
        obj = state
        for part in parts[:-1]:
            if part not in obj or not isinstance(obj[part], dict):
                raise ValueError(
                    f"Cannot resolve field path '{field_path}': "
                    f"'{part}' is absent or not a dict"
                )
            obj = obj[part]
        return obj, parts[-1]

    def _get_list(self, state: dict, field_path: str) -> list:
        parent, key = self._resolve_field(state, field_path)
        val = parent.get(key)
        if val is None:
            return []
        if not isinstance(val, list):
            raise ValueError(
                f"Field '{field_path}' is not a list (got {type(val).__name__})"
            )
        return val

    def _set_list(self, state: dict, field_path: str, new_list: list) -> None:
        parent, key = self._resolve_field(state, field_path)
        parent[key] = new_list

    @staticmethod
    def _record_timestamp(record: Any) -> str:
        """Extract the canonical timestamp string from a record dict."""
        if isinstance(record, dict):
            return (record.get("decided_at") or record.get("created_at")
                    or record.get("at") or "")
        return ""

    @staticmethod
    def _eligible_indices(
        records: list,
        policy: dict,
        field_path: str = "",
    ) -> list[int]:
        """Return indices eligible for compaction based on policy thresholds.

        max_entries: prefers oldest-by-timestamp records; falls back to positional
        for records without timestamps. Records with active=True are never eligible
        when field_path is in _ACTIVE_GUARD_FIELDS.
        max_age_days: age-based cutoff via decided_at/created_at/at timestamp.
        When both apply, eligible under either criterion.
        """
        eligible: set[int] = set()
        max_entries = policy.get("max_entries")
        max_age_days = policy.get("max_age_days")
        _active_guard = field_path in _ACTIVE_GUARD_FIELDS

        def _is_summary(rec: Any) -> bool:
            return isinstance(rec, dict) and bool(rec.get("compaction_event_id"))

        def _is_active(rec: Any) -> bool:
            return _active_guard and isinstance(rec, dict) and rec.get("active") is True

        if max_entries and len(records) > max_entries:
            excess = len(records) - max_entries
            # Build candidate lists (skip summaries and active-guarded records)
            candidates_with_ts: list[tuple[str, int]] = []
            candidates_no_ts: list[int] = []
            for i, rec in enumerate(records):
                if _is_summary(rec) or _is_active(rec):
                    continue
                ts_str = (
                    rec.get("decided_at") or rec.get("created_at") or rec.get("at") or ""
                    if isinstance(rec, dict) else ""
                )
                if ts_str:
                    candidates_with_ts.append((ts_str, i))
                else:
                    candidates_no_ts.append(i)
            # Sort timestamped candidates oldest-first; no-timestamp treated as newest
            candidates_with_ts.sort(key=lambda x: x[0])
            ordered = [i for _, i in candidates_with_ts] + candidates_no_ts
            for i in ordered[:excess]:
                eligible.add(i)

        if max_age_days is not None and max_age_days > 0:
            cutoff = datetime.now(timezone.utc) - timedelta(days=float(max_age_days))
            for i, rec in enumerate(records):
                if _is_summary(rec) or _is_active(rec):
                    continue
                ts_str = (
                    rec.get("decided_at") or rec.get("created_at") or rec.get("at") or ""
                    if isinstance(rec, dict) else ""
                )
                if ts_str:
                    try:
                        ts = datetime.fromisoformat(ts_str)
                        if ts.tzinfo is None:
                            ts = ts.replace(tzinfo=timezone.utc)
                        if ts < cutoff:
                            eligible.add(i)
                    except ValueError:
                        pass

        return sorted(eligible)

    # ── Public API ────────────────────────────────────────────────────────────

    def compact_field(
        self,
        state: dict,
        field_path: str,
        policy: dict,
        authorized_by: str,
    ) -> tuple[dict, dict]:
        """Compact *field_path* in *state* per *policy*.

        Returns (CompactionSummary, CompactionEvent).
        For ARCHIVE mode: writes the archive file and appends to the manifest.
        For ROLLING_EVICTION mode: discards eligibles, no archive.
        Mutates *state* in place.

        Raises ValueError for PROHIBITED fields or policy violations.
        """
        _primitives.validate("RetentionPolicy", policy)
        mode = policy["compaction_mode"]

        if mode == "PROHIBITED":
            raise ValueError(
                f"Compaction is PROHIBITED for field '{field_path}'"
            )
        if field_path in _PROHIBITED_FIELDS:
            raise ValueError(
                f"Compaction is PROHIBITED for field '{field_path}' "
                "by the default governance table"
            )

        records = self._get_list(state, field_path)
        if not records:
            raise ValueError(f"Field '{field_path}' is empty; nothing to compact")

        eligible_idx = self._eligible_indices(records, policy, field_path)
        if not eligible_idx:
            raise ValueError(
                f"Field '{field_path}' has {len(records)} entries which does not "
                f"exceed the configured ceiling; no compaction needed"
            )

        to_compact = [records[i] for i in eligible_idx]
        remaining = [r for i, r in enumerate(records) if i not in set(eligible_idx)]
        original_digest = _canonical_digest(to_compact)

        # Determine time_range
        def _ts(r: Any) -> str:
            if isinstance(r, dict):
                return r.get("at") or r.get("created_at") or r.get("decided_at") or ""
            return ""

        timestamps = [_ts(r) for r in to_compact if _ts(r)]
        time_range = {
            "from": min(timestamps) if timestamps else _now_iso(),
            "to": max(timestamps) if timestamps else _now_iso(),
        }

        event_id = _make_id("cmp")
        archive_path: str | None = None
        full_archive_path: Path | None = None

        # Extract record_ids and kinds for lightweight search
        record_ids: list[str] = [
            r["id"] for r in to_compact
            if isinstance(r, dict) and isinstance(r.get("id"), str)
        ]
        kinds_map: dict[str, list[str]] = {}
        for r in to_compact:
            if isinstance(r, dict) and isinstance(r.get("kind"), str) and isinstance(r.get("id"), str):
                kinds_map.setdefault(r["kind"], []).append(r["id"])

        if mode == "ARCHIVE":
            subpath = policy.get("archive_subpath", "archives")
            archive_dir = _archive_path(self.state_path,subpath)
            archive_dir.mkdir(parents=True, exist_ok=True)
            archive_filename = f"{event_id}.json"
            full_archive_path = archive_dir / archive_filename
            with full_archive_path.open("w", encoding="utf-8") as f:
                json.dump(to_compact, f, indent=2, ensure_ascii=True)
                f.flush()
                os.fsync(f.fileno())
            archive_path = str(Path(subpath) / archive_filename)

        event: dict = {
            "id": event_id,
            "target_state_path": str(
                Path(self.state_path) / "state.json"
            ),
            "target_field": field_path,
            "compacted_at": _now_iso(),
            "record_count_before": len(records),
            "record_count_after": len(remaining) + 1,  # +1 for the summary entry
            "compaction_mode": mode,
            "original_digest": original_digest,
            "authorized_by": authorized_by,
        }
        if archive_path:
            event["archive_path"] = archive_path

        _primitives.validate("CompactionEvent", event)

        if mode == "ARCHIVE":
            _append_event(self.state_path, event)
            if full_archive_path is not None:
                _write_index(full_archive_path, event_id, to_compact)

        summary: dict = {
            "compaction_event_id": event_id,
            "record_count": len(to_compact),
            "time_range": time_range,
            "original_digest": original_digest,
            "is_decompactable": mode == "ARCHIVE",
        }
        if record_ids:
            summary["record_ids"] = record_ids
        if kinds_map:
            summary["kinds"] = kinds_map
        _primitives.validate("CompactionSummary", summary)

        new_list = [summary] + remaining
        self._set_list(state, field_path, new_list)

        return summary, event

    def compact_fields(
        self,
        state: dict,
        field_paths: list[str],
        policies: dict[str, dict],
        authorized_by: str,
    ) -> list[tuple[dict, dict]]:
        """Compact multiple fields atomically (2-pass: validate-all then commit-all).

        Pass 1: dry-run each field, collect all errors.
        Pass 2: compact each field only if pass 1 had zero errors.
        Returns list of (CompactionSummary, CompactionEvent) pairs in field_paths order.
        Raises ValueError listing all validation errors if any field fails pass 1.
        Emits a partial-failure gap entry in results if pass 2 partially fails.
        """
        # Pass 1: validate all fields before committing any
        errors: list[str] = []
        for fp in field_paths:
            policy = policies.get(fp)
            if policy is None:
                errors.append(f"no policy for field '{fp}'")
                continue
            if policy.get("compaction_mode") == "PROHIBITED":
                errors.append(f"field '{fp}' is PROHIBITED")
                continue
            if fp in _PROHIBITED_FIELDS:
                errors.append(f"field '{fp}' is PROHIBITED by default governance")
                continue
            try:
                self.dry_run(state, fp, policy)
            except (ValueError, KeyError) as exc:
                errors.append(f"field '{fp}': {exc}")
        if errors:
            raise ValueError(
                "compact_fields validation failed:\n" +
                "\n".join(f"  - {e}" for e in errors)
            )
        # Pass 2: commit all (pass 1 succeeded so errors here are unexpected I/O failures)
        results: list[tuple[dict, dict]] = []
        partial_errors: list[str] = []
        for fp in field_paths:
            policy = policies[fp]
            try:
                summary, event = self.compact_field(state, fp, policy, authorized_by)
                results.append((summary, event))
            except (ValueError, OSError) as exc:
                partial_errors.append(f"field '{fp}': {exc}")
        if partial_errors:
            gap = _make_gap(
                "compaction-partial-failure",
                "partial compaction: " + "; ".join(partial_errors),
                "WARNING",
            )
            results.append((gap, {}))
        return results

    def decompact_record(
        self,
        compaction_event_id: str,
        record_id: str,
    ) -> dict:
        """Extract a single record from an ARCHIVE CompactionEvent without modifying state.

        Returns the matching record dict. Does NOT modify the live list or manifest.
        Raises ValueError if the event is not found, mode is ROLLING_EVICTION,
        archive is missing, digest fails, or the record_id is not present.
        """
        manifest = load_manifest(self.state_path)
        if manifest is None:
            raise ValueError("No CompactionManifest found; no compactions have occurred")

        original_event = next(
            (e for e in manifest["events"] if e["id"] == compaction_event_id), None
        )
        if original_event is None:
            raise ValueError(
                f"CompactionEvent '{compaction_event_id}' not found in manifest"
            )
        if original_event["compaction_mode"] == "ROLLING_EVICTION":
            raise ValueError(
                f"CompactionEvent '{compaction_event_id}' used ROLLING_EVICTION; "
                "incremental decompaction is impossible"
            )

        archive_rel = original_event.get("archive_path")
        if not archive_rel:
            raise ValueError(
                f"CompactionEvent '{compaction_event_id}' has no archive_path"
            )
        full_archive = _archive_path(self.state_path,archive_rel)
        if not full_archive.exists():
            raise ValueError(f"Archive file not found: {full_archive}")

        with full_archive.open("r",encoding="utf-8") as stream:verified_originals=json.load(stream)
        if _canonical_digest(verified_originals)!=_get_expected_digest(full_archive,original_event["original_digest"]):raise ValueError("Archive digest mismatch")

        # Try index first for O(1) lookup
        index = load_index(full_archive)
        if index is not None:
            offset = index.get("id_to_offset", {}).get(record_id)
            if offset is not None:
                originals = verified_originals
                if offset < len(originals):
                    candidate = originals[offset]
                    if isinstance(candidate, dict) and candidate.get("id") == record_id:
                        return candidate

        # Fallback: sequential scan
        originals = verified_originals

        for rec in originals:
            if isinstance(rec, dict) and rec.get("id") == record_id:
                return rec

        raise ValueError(
            f"Record '{record_id}' not found in archive for event '{compaction_event_id}'"
        )

    def amend_archived_record(
        self,
        compaction_event_id: str,
        record_id: str,
        amendment_kind: str,
        amendment_note: str,
        authorized_by: str,
        apply_fn,
    ) -> dict:
        """Apply an in-place amendment to a single record in an archive file.

        *apply_fn* is called with the current record dict and must return the amended
        record dict. Appends an ArchiveAmendment to the archive's .amendments.jsonl.
        Does NOT modify the CompactionSummary or CompactionManifest.

        Returns the ArchiveAmendment record.

        Raises ValueError if event is not found, mode is ROLLING_EVICTION,
        archive is missing, or record_id is not present.
        """
        manifest = load_manifest(self.state_path)
        if manifest is None:
            raise ValueError("No CompactionManifest found")

        original_event = next(
            (e for e in manifest["events"] if e["id"] == compaction_event_id), None
        )
        if original_event is None:
            raise ValueError(
                f"CompactionEvent '{compaction_event_id}' not found in manifest"
            )
        if original_event["compaction_mode"] == "ROLLING_EVICTION":
            raise ValueError(
                f"CompactionEvent '{compaction_event_id}' used ROLLING_EVICTION; "
                "amendment is impossible"
            )

        archive_rel = original_event.get("archive_path")
        if not archive_rel:
            raise ValueError(
                f"CompactionEvent '{compaction_event_id}' has no archive_path"
            )
        full_archive = _archive_path(self.state_path,archive_rel)
        if not full_archive.exists():
            raise ValueError(f"Archive file not found: {full_archive}")

        with full_archive.open("r", encoding="utf-8") as f:
            originals = json.load(f)
        if _canonical_digest(originals)!=_get_expected_digest(full_archive,original_event["original_digest"]):raise ValueError("Archive digest mismatch")

        target_idx = next(
            (i for i, r in enumerate(originals)
             if isinstance(r, dict) and r.get("id") == record_id),
            None,
        )
        if target_idx is None:
            raise ValueError(
                f"Record '{record_id}' not found in archive for event '{compaction_event_id}'"
            )

        before_record = originals[target_idx]
        before_digest = _canonical_digest([before_record])
        after_record = apply_fn(dict(before_record))
        after_digest = _canonical_digest([after_record])

        originals[target_idx] = after_record

        tmp = full_archive.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(originals, f, indent=2, ensure_ascii=True)
            f.flush()
            os.fsync(f.fileno())
        tmp.replace(full_archive)

        amendment: dict = {
            "id": _make_id("amd"),
            "archive_path": str(full_archive),
            "record_id": record_id,
            "amended_at": _now_iso(),
            "amendment_kind": amendment_kind,
            "amendment_note": amendment_note,
            "authorized_by": authorized_by,
            "before_digest": before_digest,
            "after_digest": after_digest,
        }
        _primitives.validate("ArchiveAmendment", amendment)
        _append_amendment(full_archive, amendment)

        # Regenerate the index to reflect the amendment
        _write_index(full_archive, compaction_event_id, originals)

        return amendment

    def decompact_field(
        self,
        state: dict,
        field_path: str,
        compaction_event_id: str,
        authorized_by: str,
    ) -> dict:
        """Restore original records from an ARCHIVE-mode CompactionEvent.

        Verifies digest, replaces CompactionSummary in the live list, appends
        an inverse CompactionEvent to the manifest, and returns the inverse event.

        Raises ValueError if the event is not found, mode is ROLLING_EVICTION,
        archive is missing, or digest verification fails.
        """
        manifest = load_manifest(self.state_path)
        if manifest is None:
            raise ValueError("No CompactionManifest found; no compactions have occurred")

        original_event = next(
            (e for e in manifest["events"] if e["id"] == compaction_event_id),
            None,
        )
        if original_event is None:
            raise ValueError(
                f"CompactionEvent '{compaction_event_id}' not found in manifest"
            )
        if original_event["compaction_mode"] == "ROLLING_EVICTION":
            raise ValueError(
                f"CompactionEvent '{compaction_event_id}' used ROLLING_EVICTION; "
                "decompaction is impossible (originals were not archived)"
            )

        archive_rel = original_event.get("archive_path")
        if not archive_rel:
            raise ValueError(
                f"CompactionEvent '{compaction_event_id}' has no archive_path"
            )
        full_archive = _archive_path(self.state_path,archive_rel)
        if not full_archive.exists():
            raise ValueError(
                f"Archive file not found: {full_archive}"
            )

        with full_archive.open("r", encoding="utf-8") as f:
            originals = json.load(f)

        restored_digest = _canonical_digest(originals)
        _expected_digest = _get_expected_digest(full_archive, original_event["original_digest"])
        if restored_digest != _expected_digest:
            raise ValueError(
                f"Archive digest mismatch for event '{compaction_event_id}': "
                f"expected {_expected_digest}, got {restored_digest}"
            )

        records = self._get_list(state, field_path)
        summary_idx = next(
            (i for i, r in enumerate(records)
             if isinstance(r, dict) and r.get("compaction_event_id") == compaction_event_id),
            None,
        )
        if summary_idx is None:
            raise ValueError(
                f"CompactionSummary for event '{compaction_event_id}' "
                f"not found in field '{field_path}'"
            )

        new_list = records[:summary_idx] + originals + records[summary_idx + 1:]
        self._set_list(state, field_path, new_list)

        inverse_event: dict = {
            "id": _make_id("cmp"),
            "target_state_path": original_event["target_state_path"],
            "target_field": field_path,
            "compacted_at": _now_iso(),
            "record_count_before": len(records),
            "record_count_after": len(new_list),
            "compaction_mode": "ARCHIVE",
            "archive_path": archive_rel,
            "original_digest": original_event["original_digest"],
            "authorized_by": authorized_by,
        }
        _primitives.validate("CompactionEvent", inverse_event)
        _append_event(self.state_path, inverse_event)

        return inverse_event

    def dry_run(
        self,
        state: dict,
        field_path: str,
        policy: dict,
    ) -> dict:
        """Return a report of what compact_field would do without committing.

        Returns a dict with: field_path, record_count, eligible_count,
        would_compact, mode, archive_path (if ARCHIVE), original_digest.
        """
        _primitives.validate("RetentionPolicy", policy)
        mode = policy["compaction_mode"]
        records = self._get_list(state, field_path)
        eligible_idx = self._eligible_indices(records, policy, field_path)
        to_compact = [records[i] for i in eligible_idx]

        report: dict = {
            "field_path": field_path,
            "record_count": len(records),
            "eligible_count": len(to_compact),
            "would_compact": len(to_compact) > 0,
            "mode": mode,
        }
        if to_compact:
            report["original_digest"] = _canonical_digest(to_compact)
        if mode == "ARCHIVE" and to_compact:
            subpath = policy.get("archive_subpath", "archives")
            report["archive_path"] = str(
                Path(subpath) / f"<event-id>.json"
            )
        return report
