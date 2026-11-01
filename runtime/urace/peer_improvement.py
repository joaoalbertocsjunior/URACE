"""Peer-contributed improvement pipeline.

Reads signed artifacts from the peer_exchange quarantine, validates them,
and promotes reviewed artifacts into the main improvement workflow as queued inputs.

Pipeline stages:
  quarantine (peer_exchange) → evaluate (this module) → promote → queue_input

Singularity effect:
  mark_qualified → APPLIED_AFTER_LOCAL_QUALIFICATION audit event
  multi_peer_amplification → priority boost from N independent peer qualifications
  network_convergence → RPC query to estimate network-wide qualification ratio

Peer identities are SHA256(DER certificate) — opaque fingerprints, no PII.
Artifact content anonymization is the artifact author's responsibility.
"""
from __future__ import annotations

import hashlib
import json
import math
import time
from pathlib import Path
from typing import Any

SCHEMA = "urace-peer-improvement-v1"
_MAX_ARTIFACT_BYTES = 524288   # 512 KiB
_SAFE_ARTIFACT_SIGNALS = ["urace", "runtime", "trial", "objective", "feature"]


def quarantine_dir(root: Path) -> Path:
    from . import peer_exchange as _px
    from ._common import load_config
    try:
        config = load_config()
        return _px.directory(config) / "quarantine"
    except Exception:
        return root / "exchange" / "quarantine"


def list_quarantined(root: Path) -> list[dict[str, Any]]:
    """Return metadata for all quarantined bundles, newest first."""
    qdir = quarantine_dir(root)
    if not qdir.exists():
        return []
    results = []
    for path in sorted(qdir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            if path.is_symlink():
                continue
            bundle = json.loads(path.read_text(encoding="utf-8"))
            payload = bundle.get("payload", {})
            results.append({
                "bundle_id": path.stem,
                "sender": payload.get("sender", "unknown")[:16] + "…",
                "feature": payload.get("feature", "unknown"),
                "artifact_bytes": len(payload.get("artifact", "").encode()),
                "created_unix": payload.get("created_unix", 0),
                "artifact_sha256": payload.get("sha256", ""),
                "schema": payload.get("schema", ""),
            })
        except (OSError, ValueError, KeyError):
            continue
    return results


def load_bundle(root: Path, bundle_id: str) -> dict[str, Any]:
    """Load and basic-validate a quarantined bundle by id."""
    _safe = bundle_id.replace("/", "").replace(".", "").replace("..", "")
    if _safe != bundle_id or not bundle_id:
        raise ValueError(f"invalid bundle_id: {bundle_id!r}")
    qdir = quarantine_dir(root)
    path = qdir / f"{bundle_id}.json"
    if path.is_symlink() or not path.exists():
        raise FileNotFoundError(f"bundle not found: {bundle_id}")
    bundle = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(bundle, dict) or "payload" not in bundle:
        raise ValueError("malformed bundle: missing payload")
    return bundle


def evaluate(root: Path, bundle_id: str) -> dict[str, Any]:
    """Evaluate a quarantined artifact for safety and relevance.

    Does NOT apply or promote anything. Returns an evaluation report.
    """
    bundle = load_bundle(root, bundle_id)
    payload = bundle["payload"]
    artifact = payload.get("artifact", "")
    artifact_bytes = len(artifact.encode())
    issues: list[str] = []

    if artifact_bytes == 0:
        issues.append("artifact is empty")
    if artifact_bytes > _MAX_ARTIFACT_BYTES:
        issues.append(f"artifact exceeds size limit ({artifact_bytes} > {_MAX_ARTIFACT_BYTES})")

    # Verify sha256 integrity
    actual_sha = hashlib.sha256(artifact.encode()).hexdigest()
    if actual_sha != payload.get("sha256", ""):
        issues.append("artifact sha256 mismatch — bundle integrity compromised")

    # Relevance check: does it reference URACE domain concepts?
    artifact_lower = artifact.lower()
    relevant_signals = [s for s in _SAFE_ARTIFACT_SIGNALS if s in artifact_lower]

    # Schema check
    if payload.get("schema") != "urace-peer-bundle-v1":
        issues.append(f"unexpected bundle schema: {payload.get('schema')!r}")

    # Expiry check (bundles older than 30 days are suspect)
    age_days = (time.time() - float(payload.get("created_unix", 0))) / 86400
    if age_days > 30:
        issues.append(f"bundle is {age_days:.0f} days old (>30d)")

    verdict = "SAFE" if not issues else ("UNSAFE" if any("integrity" in i or "empty" in i for i in issues) else "REVIEW")

    return {
        "schema": SCHEMA,
        "bundle_id": bundle_id,
        "verdict": verdict,
        "issues": issues,
        "artifact_bytes": artifact_bytes,
        "relevant_signals": relevant_signals,
        "feature": payload.get("feature", "unknown"),
        "sender_prefix": payload.get("sender", "")[:16],
        "age_days": round(age_days, 1),
        "evaluated_at": time.time(),
    }


def promote(root: Path, bundle_id: str, config: dict[str, Any], state: dict[str, Any], exchange=None) -> dict[str, Any]:
    """Promote a quarantined artifact into the improvement workflow.

    Queues a goal input so the lifecycle loop can incorporate the peer contribution.
    The artifact text is attached as context; URACE decides whether to act on it.
    Requires evaluate() verdict to be SAFE or REVIEW (not UNSAFE).

    Pass exchange to enable multi-peer amplification priority boost.
    """
    report = evaluate(root, bundle_id)
    if report["verdict"] == "UNSAFE":
        raise ValueError(f"cannot promote UNSAFE artifact: {'; '.join(report['issues'])}")

    bundle = load_bundle(root, bundle_id)
    payload = bundle["payload"]
    artifact = payload.get("artifact", "")
    feature = payload.get("feature", "unknown")
    sender_prefix = payload.get("sender", "unknown")[:16]

    # Boost priority when multiple independent peers have already qualified this artifact.
    boost = 0
    if exchange is not None:
        try:
            boost = multi_peer_amplification(exchange, artifact)
        except Exception:
            pass
    priority = min(85, 55 + boost)

    from ._common import identifier, now, queue_input

    entry = queue_input(config, "goal", {
        "title": f"Evaluate peer-contributed artifact for feature: {feature}",
        "success_measure": "Artifact reviewed, incorporated or explicitly rejected with documented rationale",
        "reason": f"Peer artifact received from {sender_prefix}… via signed exchange. Quarantine evaluation: {report['verdict']}. Relevant signals: {report['relevant_signals']}. Amplification boost: {boost}.",
        "target": "product",
        "priority": priority,
        "expected_value": 0.4,
        "estimated_cost": 0.3,
        "risk": 0.4,
        "urgency": 0.3,
        "dependencies": [],
        "source_text": artifact[:2000],
        "semantic_section": f"peer artifact [{bundle_id[:12]}]",
        "peer_bundle_id": bundle_id,
        "peer_feature": feature,
        "peer_evaluation": report,
        "peer_amplification_boost": boost,
    })

    # Record the promotion event in state
    state.setdefault("rollback_records", []).append({
        "id": identifier("peer-promo"),
        "at": now(),
        "kind": "peer-artifact-promoted",
        "bundle_id": bundle_id,
        "feature": feature,
        "verdict": report["verdict"],
        "queued_input_id": entry["id"],
    })

    return {
        "schema": SCHEMA,
        "status": "PROMOTED",
        "bundle_id": bundle_id,
        "queued_input_id": entry["id"],
        "evaluation": report,
    }


def _artifact_canonical_fp(artifact_text: str) -> str:
    from .tokenomics import canonical_fingerprint
    return canonical_fingerprint({"artifact": artifact_text})


def _load_qualification_receipt(qualification_id: str) -> dict[str, Any]:
    """Load and minimally verify a trial qualification receipt.

    Does NOT require the full trial infrastructure context (suite_sha256, controllers,
    etc.) — that is the role of runtime_qualification.load_qualification(). This
    function only verifies the receipt is present, structurally valid, and that
    accepted_evidence=True, which is sufficient to authorize token credit.

    Raises ValueError if the receipt is absent, symlinked, structurally invalid,
    or if accepted_evidence is not True.
    """
    import re
    from ._common import SYSTEM_ROOT

    if not isinstance(qualification_id, str) or not re.fullmatch(r'qualification-[a-f0-9]+', qualification_id):
        raise ValueError(f'Invalid qualification_id format: {qualification_id!r}')
    folder = SYSTEM_ROOT / 'trial' / 'runtime-qualifications' / qualification_id
    if folder.is_symlink():
        raise ValueError('Qualification folder cannot be a symlink')
    receipt_path = folder / 'receipt.json'
    if receipt_path.is_symlink() or not receipt_path.exists():
        raise ValueError(f'Qualification receipt not found: {qualification_id}')
    receipt = json.loads(receipt_path.read_text())
    if receipt.get('schema') != 'runtime-qualification-v1':
        raise ValueError('Invalid qualification receipt schema')
    if receipt.get('id') != qualification_id:
        raise ValueError('Qualification receipt id mismatch')
    if receipt.get('accepted_evidence') is not True:
        raise ValueError(
            f'Qualification evidence not accepted '
            f'(accepted_evidence={receipt.get("accepted_evidence")!r}); '
            f'tokens cannot be earned for a failed or unproven qualification'
        )
    delta = receipt.get('delta')
    if not isinstance(delta, (int, float)):
        raise ValueError('Qualification receipt missing numeric delta')
    return receipt


def mark_qualified(
    exchange,
    bundle_id: str,
    score_delta: float,
    affected_files: dict[str, str],
    baseline_sha256: str,
    qualification_id: str | None = None,
) -> dict[str, Any]:
    """Emit APPLIED_AFTER_LOCAL_QUALIFICATION after a peer artifact passes the quality gate.

    qualification_id: path-component of the trial receipt in
      trial/runtime-qualifications/{qualification_id}/receipt.json
      When provided, the receipt is verified (accepted_evidence must be True) and
      its delta overrides score_delta. The audit event is flagged receipt_verified=True.
      When absent, score_delta is taken from the caller (unverified; receipt_verified=False).
      With token_settlement=True, only receipt_verified=True events earn tokens.

    affected_files: {filename: new_source_text} of files changed by the applied patch.
    baseline_sha256: engine_identity() hash before the patch was applied.
    """
    from .tokenomics import canonical_fingerprint, outcome_fingerprint

    record = exchange.inspect(bundle_id)
    payload = record["bundle"]["payload"]

    receipt_verified = False
    if qualification_id is not None:
        receipt = _load_qualification_receipt(qualification_id)
        score_delta = receipt["delta"]  # authoritative; overrides caller-supplied value
        receipt_verified = True
        if affected_files:
            canon_fp = canonical_fingerprint(affected_files)
            outcome_fp = outcome_fingerprint(baseline_sha256, list(affected_files.keys()), score_delta)
        else:
            canon_fp = receipt.get("canonical_fingerprint", "")
            outcome_fp = receipt.get("outcome_fingerprint", "")
    else:
        source_delta = affected_files if affected_files else {"artifact": payload.get("artifact", "")}
        canon_fp = canonical_fingerprint(source_delta)
        outcome_fp = outcome_fingerprint(baseline_sha256, list(source_delta.keys()), score_delta)

    affected_keys = sorted(affected_files.keys()) if affected_files else []

    with exchange.lock():
        exchange.event(
            "APPLIED_AFTER_LOCAL_QUALIFICATION",
            peer=payload.get("sender", "unknown"),
            feature=payload.get("feature", "unknown"),
            bundle=bundle_id,
            score_delta=round(float(score_delta), 4),
            canonical_fingerprint=canon_fp,
            outcome_fingerprint=outcome_fp,
            affected_files=affected_keys,
            receipt_verified=receipt_verified,
            qualification_id=qualification_id,
        )
        # The APPLIED_AFTER_LOCAL_QUALIFICATION event above IS the earn record —
        # token_ledger.balance() reads it directly from the tamper-evident audit chain.
        p_settings = exchange.load()

    # Trigger relay to eligible peers if auto_relay is enabled.
    relay_result: dict[str, Any] | None = None
    try:
        if p_settings.get("auto_relay"):
            relay_result = relay_qualified(exchange, bundle_id)
    except Exception:
        pass

    result: dict[str, Any] = {
        "bundle_id": bundle_id,
        "canonical_fingerprint": canon_fp,
        "outcome_fingerprint": outcome_fp,
        "score_delta": score_delta,
        "status": "QUALIFIED",
    }
    if relay_result is not None:
        result["relay"] = relay_result
    return result


def relay_qualified(exchange, bundle_id: str) -> dict[str, Any]:
    """Relay a locally qualified artifact to all eligible peers.

    Requires auto_relay=True in exchange settings (owner opt-in).
    Each target peer must have explicit send permission for the feature.
    Peers who already received the original bundle are skipped.
    The original sender is never relayed back to.
    """
    p = exchange.load()
    if not p.get("auto_relay"):
        return {"relayed": 0, "status": "AUTO_RELAY_DISABLED"}

    rows = exchange.audit_rows()
    already_sent = {
        r.get("peer") for r in rows
        if r.get("bundle") == bundle_id
        and r.get("kind") in ("SENT_QUARANTINED", "SEND_FAILED_OR_UNCONFIRMED", "RELAY_PREPARED")
    }

    record = exchange.inspect(bundle_id)
    feature = record["bundle"]["payload"]["feature"]
    original_sender = record["bundle"]["payload"].get("sender", "")

    relayed: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for peer_id, peer_config in p["peers"].items():
        if peer_config.get("blocked"):
            skipped.append({"peer": peer_id[:16], "reason": "blocked"})
            continue
        if peer_id == original_sender:
            skipped.append({"peer": peer_id[:16], "reason": "original_sender"})
            continue
        if peer_id in already_sent:
            skipped.append({"peer": peer_id[:16], "reason": "already_sent"})
            continue
        if not exchange.permitted(p, peer_id, feature, "send"):
            skipped.append({"peer": peer_id[:16], "reason": "not_permitted"})
            continue
        try:
            result = exchange.prepare_relay(peer_id, bundle_id)
            relayed.append({"peer": peer_id[:16], "relay_bundle_id": result["bundle_id"]})
        except (ValueError, OSError) as exc:
            skipped.append({"peer": peer_id[:16], "reason": str(exc)[:80]})

    return {
        "schema": SCHEMA,
        "source_bundle": bundle_id,
        "relayed": len(relayed),
        "relayed_to": relayed,
        "skipped": skipped,
        "status": "RELAYED" if relayed else "NO_ELIGIBLE_PEERS",
    }


def multi_peer_amplification(exchange, artifact_text: str, max_boost: int = 30) -> int:
    """Priority boost derived from independent peer qualifications of the same artifact.

    Scans the local audit log for APPLIED_AFTER_LOCAL_QUALIFICATION events whose
    canonical_fingerprint matches this artifact. Counts distinct peer identities;
    one peer identity cannot inflate the count. No network calls.

    Returns an integer boost in [0, max_boost]:
      1 peer  → 15   (strong prior)
      2 peers → 20
      4 peers → 25
      8 peers → 30   (network consensus)
    """
    canon_fp = _artifact_canonical_fp(artifact_text)
    rows = exchange.audit_rows()

    qualified_peers: set[str] = set()
    for row in rows:
        if row.get("kind") == "APPLIED_AFTER_LOCAL_QUALIFICATION":
            if row.get("canonical_fingerprint") == canon_fp:
                peer = row.get("peer")
                if peer:
                    qualified_peers.add(peer)

    n = len(qualified_peers)
    if n == 0:
        return 0
    return min(max_boost, round(15 * (1 + math.log2(n) / 3)))


def network_convergence(exchange, canonical_fp: str) -> dict[str, Any]:
    """Estimate how many reachable peers have locally qualified an artifact.

    Queries AVAILABLE peers via exchange.convergence RPC. Unreachable peers
    are skipped — unknown is not treated as unqualified. No locks held during
    network I/O; budget comes from the exchange RPC allowance.

    Returns convergence ratio (confirmed / queried), or None if no peers reachable.
    """
    from . import peer_exchange as _px
    import re

    if not re.fullmatch("[a-f0-9]{64}", canonical_fp):
        raise ValueError("Invalid canonical fingerprint")

    p = exchange.load()
    if not p.get("network") or not p.get("enabled"):
        return {
            "canonical_fingerprint": canonical_fp,
            "queried": 0,
            "confirmed": 0,
            "ratio": None,
            "status": "NETWORK_DISABLED",
        }

    from . import peer_selection as _ps
    state = _ps.cache(exchange)
    available = [
        peer for peer, meta in state.get("peers", {}).items()
        if meta.get("status") == "AVAILABLE"
        and not p["peers"].get(peer, {}).get("blocked")
    ]

    confirmed = 0
    queried = 0
    for peer in available:
        try:
            result = _px.request(exchange, peer, "exchange.convergence", {"canonical_fingerprint": canonical_fp})
            queried += 1
            if isinstance(result.get("qualified_count"), int) and result["qualified_count"] > 0:
                confirmed += 1
        except (ValueError, OSError):
            pass

    ratio = confirmed / queried if queried > 0 else None
    return {
        "canonical_fingerprint": canonical_fp,
        "queried": queried,
        "confirmed": confirmed,
        "ratio": ratio,
        "status": "OK" if queried > 0 else "NO_REACHABLE_PEERS",
    }
