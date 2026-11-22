#!/usr/bin/env python3
"""Portfolio product identity, cohort policy, and state snapshots."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path

from .portfolio_storage import (
    ROOT, TEMPORARY_ROOT, DATA, VARIANTS,
    load, save, append_agora, bounded_text, name, now, write_authenticated_archive,
    unit_interval,
)

COHORT_POLICIES = {"auto", "enabled", "disabled"}
COHORT_POLICY_ALIASES = {"adaptive": "auto", "always": "enabled", "off": "disabled", **{value: value for value in COHORT_POLICIES}}
ACCEPTED_STATE_SOURCES = {"lifecycle", "repository"}


def variant(data: dict, value: str) -> dict:
    try:
        return data["variants"][value]
    except KeyError:
        raise SystemExit(f"Unknown variant: {value}") from None


def _get_root():
    """Get ROOT from portfolio hub so patch.object(portfolio, 'ROOT', ...) tests work."""
    try:
        import urace.portfolio as _hub
        return _hub.ROOT
    except (ImportError, AttributeError):
        return ROOT


def _get_data():
    """Get DATA path dynamically for test-patch compatibility."""
    try:
        import urace.portfolio as _hub
        return _hub.DATA
    except (ImportError, AttributeError):
        return DATA


def _get_temporary_root():
    """Get TEMPORARY_ROOT dynamically for test-patch compatibility."""
    try:
        import urace.portfolio as _hub
        return _hub.TEMPORARY_ROOT
    except (ImportError, AttributeError):
        return TEMPORARY_ROOT


def _get_variants():
    """Get VARIANTS path dynamically for test-patch compatibility."""
    try:
        import urace.portfolio as _hub
        return _hub.VARIANTS
    except (ImportError, AttributeError):
        return VARIANTS


def git(*arguments: str) -> str:
    result = subprocess.run(["git", "-C", str(_get_root()), *arguments], text=True, capture_output=True)
    if result.returncode:
        raise SystemExit(result.stderr.strip() or f"git exited {result.returncode}")
    return result.stdout.strip()


def effective_cohort_policy(data: dict) -> str:
    """Missing policy is deliberately backward-compatible automatic operation."""
    return str(data.get("cohort_policy", {}).get("mode", "auto")).lower()


def effective_accepted_state_source(data: dict) -> dict:
    """Legacy state remains governed by its retained lifecycle acceptance record."""
    configured = data.get("accepted_state_source")
    return configured if configured else {"mode": "lifecycle", "explicit": False}


def resolve_accepted_product_identity(data: dict) -> str:
    """Resolve identity cheaply without changing durable acceptance records."""
    source = effective_accepted_state_source(data)
    record = data.get("accepted_product")
    if source["mode"] == "lifecycle":
        commit = (record or data.get("baseline", {})).get("commit")
        if not commit:
            raise SystemExit("ACCEPTED_PRODUCT_UNRESOLVED: lifecycle source has no accepted Product identity")
        git("cat-file", "-e", f"{commit}^{{commit}}")
        return commit
    ref = source.get("ref")
    if not ref:
        raise SystemExit("ACCEPTED_PRODUCT_UNRESOLVED: repository source requires an Authority-designated ref")
    return git("rev-parse", "--verify", f"{ref}^{{commit}}")


def product_source_digest() -> str:
    """Identify the current public Product source without consulting mutable state."""
    _root = _get_root()
    digest = hashlib.sha256()
    for relative in ("README.md", "URACE.md"):
        path = _root / relative
        if not path.is_file():
            raise SystemExit(f"ACCEPTED_PRODUCT_INVALID: required source file is missing: {relative}")
        payload = path.read_bytes()
        digest.update(relative.encode()); digest.update(b"\0")
        digest.update(len(payload).to_bytes(8, "big")); digest.update(payload)
    return digest.hexdigest()


def snapshot_current_product(data: dict) -> str:
    """Commit current Product documents to a private ref without changing user Git state."""
    _root = _get_root()
    _tmp_root = _get_temporary_root()
    record = data.get("accepted_product") or {}
    digest = product_source_digest()
    previous = record.get("commit") or data.get("baseline", {}).get("commit") or git("rev-parse", "HEAD")
    if record.get("source_digest") == digest:
        return previous

    # Older ledgers predate source_digest. Avoid inventing a snapshot when their
    # retained commit already has exactly the current public Product content.
    if not record.get("source_digest"):
        matches = True
        for relative in ("README.md", "URACE.md"):
            retained = subprocess.run(
                ["git", "-C", str(_root), "show", f"{previous}:{relative}"],
                capture_output=True,
                timeout=30,
            )
            if retained.returncode or retained.stdout != (_root / relative).read_bytes():
                matches = False; break
        if matches:
            data["accepted_product"] = {**record, "commit": previous, "source_digest": digest}
            return previous

    _tmp_root.mkdir(parents=True, exist_ok=True)
    index_path = Path(tempfile.mkstemp(prefix="source-index-", dir=_tmp_root)[1])
    index_path.unlink()
    environment = {
        **os.environ,
        "GIT_INDEX_FILE": str(index_path),
        "GIT_AUTHOR_NAME": "URACE Controller",
        "GIT_AUTHOR_EMAIL": "urace@local.invalid",
        "GIT_COMMITTER_NAME": "URACE Controller",
        "GIT_COMMITTER_EMAIL": "urace@local.invalid",
    }
    try:
        for arguments in (
            ["read-tree", "HEAD"],
            ["add", "--", "README.md", "URACE.md"],
        ):
            result = subprocess.run(["git", "-C", str(_root), *arguments], env=environment, text=True, capture_output=True, timeout=30)
            if result.returncode:
                raise SystemExit(result.stderr.strip() or "could not snapshot current Product source")
        tree = subprocess.run(["git", "-C", str(_root), "write-tree"], env=environment, text=True, capture_output=True, check=True, timeout=30).stdout.strip()
        commit = subprocess.run(
            ["git", "-C", str(_root), "commit-tree", tree, "-p", previous, "-m", "URACE accepted Product source snapshot"],
            env=environment, text=True, capture_output=True, check=True, timeout=30,
        ).stdout.strip()
        subprocess.run(
            ["git", "-C", str(_root), "update-ref", "refs/urace/source-snapshots/latest", commit],
            text=True, capture_output=True, check=True, timeout=30,
        )
    finally:
        index_path.unlink(missing_ok=True)

    recorded_at = now()
    data["accepted_product"] = {
        "commit": commit, "recorded_at": recorded_at,
        "source": "current Product source at safe checkpoint",
        "source_digest": digest, "predecessor": previous,
    }
    data.setdefault("events", []).append({
        "at": recorded_at, "kind": "ACCEPTED_PRODUCT_SOURCE_SNAPSHOTTED",
        "commit": commit, "predecessor": previous, "source_digest": digest,
        "files": ["README.md", "URACE.md"],
    })
    return commit


def _real_accepted_product_commit(data: dict) -> str:
    """Resolve acceptance through the Authority-designated common source."""
    source = effective_accepted_state_source(data)
    record = data.get("accepted_product")
    if source["mode"] == "lifecycle":
        return snapshot_current_product(data)
    commit = resolve_accepted_product_identity(data)
    ref = source["ref"]
    if not record or record.get("commit") != commit:
        previous = record.get("commit") if record else data.get("baseline", {}).get("commit")
        data["accepted_product"] = {"commit": commit, "recorded_at": now(), "source": f"repository:{ref}", "predecessor": previous}
        data.setdefault("events", []).append({"at": now(), "kind": "ACCEPTED_PRODUCT_RESOLVED", "commit": commit, "predecessor": previous, "source_mode": "repository", "ref": ref})
    elif record.get("source") != f"repository:{ref}":
        data["accepted_product"] = {**record, "source": f"repository:{ref}", "source_bound_at": now()}
        data.setdefault("events", []).append({"at": now(), "kind": "ACCEPTED_PRODUCT_SOURCE_BOUND", "commit": commit, "source_mode": "repository", "ref": ref})
    return commit


def accepted_product_commit(data: dict) -> str:
    """Dispatch through portfolio hub so patch.object(portfolio, 'accepted_product_commit') works in tests."""
    import sys
    hub = sys.modules.get("urace.portfolio")
    if hub is not None:
        hub_fn = hub.__dict__.get("accepted_product_commit")
        if hub_fn is not None and hub_fn is not accepted_product_commit:
            return hub_fn(data)
    return _real_accepted_product_commit(data)


def reconcile_accepted_product(data: dict, workflow: dict) -> bool:
    """Supersede a stale cohort at a checkpoint; retain its signed evidence and refs."""
    automation = data.get("automation", {})
    phase = automation.get("phase", "IDLE")
    accepted = accepted_product_commit(data)
    expected = automation.get("accepted_parent_commit")
    if phase != "IDLE":
        cohort = automation.get("cohort")
        parents = {
            item.get("accepted_parent_commit") or item.get("parent_commit")
            for item in data.get("variants", {}).values() if item.get("cohort") == cohort
        } - {None}
        if len(parents) == 1:
            cohort_parent = parents.pop()
            if not expected or cohort_parent != accepted:
                expected = cohort_parent
    if not expected or expected == accepted or phase == "IDLE":
        automation["accepted_parent_commit"] = accepted
        return False
    if workflow.get("external_effects", "none") != "none":
        automation.update({"status": "BLOCKED_RECONCILIATION", "last_error": "accepted Product advanced while cohort effects may be external"})
        raise SystemExit("ACCEPTED_PRODUCT_CONFLICT: dependent cohort work is blocked until external effects are reconciled")
    cohort = automation.get("cohort")
    members = [item for item in data.get("variants", {}).values() if item.get("cohort") == cohort]
    archive = _get_data().parent / "archive"
    for item in members:
        path = Path(item["path"])
        if path.exists():
            subprocess.run(["git", "-C", str(_get_root()), "worktree", "remove", "--force", str(path)], check=True, capture_output=True)
        retained = {**item, "status": "SUPERSEDED_ACCEPTED_PRODUCT_ADVANCE", "superseded_at": now(), "superseded_by": accepted}
        write_authenticated_archive(archive / f"{item['name']}-superseded.json", "portfolio-variant", retained)
        del data["variants"][item["name"]]
    automation.update({
        "phase": "IDLE", "status": "RUNNING", "accepted_parent_commit": accepted,
        "lineage_parent_variant": data.get("selected"), "last_error": None,
    })
    automation.pop("cohort", None); automation.pop("plan", None)
    automation["planner_stage"] = None
    data.setdefault("events", []).append({
        "at": now(), "kind": "GENERATION_SUPERSEDED_ACCEPTED_PRODUCT_ADVANCE", "cohort": cohort,
        "previous_accepted_commit": expected, "accepted_commit": accepted,
        "retained_variants": [item["name"] for item in members], "lineage_parent_variant": data.get("selected"),
    })
    return True


def cmd_policy(args: argparse.Namespace) -> None:
    data = load(); mode = COHORT_POLICY_ALIASES.get(args.mode.lower(), args.mode.lower())
    if mode not in COHORT_POLICIES:
        raise SystemExit(f"cohort policy must be one of: {', '.join(sorted(COHORT_POLICIES))}")
    current = effective_cohort_policy(data)
    if current == mode and data.get("cohort_policy"):
        print(f"Cohort policy unchanged: {mode}"); return
    data["cohort_policy"] = {"mode": mode, "set_at": now(), "source": "operator CLI"}
    data.setdefault("events", []).append({"at": now(), "kind": "COHORT_POLICY_CHANGED", "from": current, "to": mode, "source": "operator CLI"})
    save(data); print(f"Cohort policy: {mode}")


def cmd_policy_status(args: argparse.Namespace) -> None:
    data = load()
    payload = {"mode": effective_cohort_policy(data), "explicit": "cohort_policy" in data, "record": data.get("cohort_policy")}
    if args.json: print(json.dumps(payload, indent=2, sort_keys=True))
    else: print(f"Cohort policy: {payload['mode']} ({'explicit' if payload['explicit'] else 'default'})")


def cmd_accepted_state_source(args: argparse.Namespace) -> None:
    data = load(); mode = args.mode.lower(); ref = args.ref
    if mode == "repository":
        if not ref:
            raise SystemExit("repository accepted-state source requires --ref")
        git("rev-parse", "--verify", f"{ref}^{{commit}}")
    elif ref:
        raise SystemExit("--ref applies only to the repository accepted-state source")
    current = effective_accepted_state_source(data)
    requested = {"mode": mode, **({"ref": ref} if ref else {})}
    if current.get("mode") == mode and current.get("ref") == ref and data.get("accepted_state_source"):
        print(f"Accepted-state source unchanged: {mode}" + (f" ({ref})" if ref else "")); return
    data["accepted_state_source"] = {**requested, "set_at": now(), "source": "operator CLI"}
    data.setdefault("events", []).append({"at": now(), "kind": "ACCEPTED_STATE_SOURCE_CHANGED", "from": {key: current.get(key) for key in ("mode", "ref") if current.get(key) is not None}, "to": requested, "source": "operator CLI"})
    save(data); print(f"Accepted-state source: {mode}" + (f" ({ref})" if ref else ""))


def cmd_accepted_state_source_status(args: argparse.Namespace) -> None:
    data = load(); source = effective_accepted_state_source(data)
    payload = {"mode": source["mode"], "ref": source.get("ref"), "explicit": "accepted_state_source" in data, "resolved_commit": resolve_accepted_product_identity(data)}
    if args.json: print(json.dumps(payload, indent=2, sort_keys=True))
    else: print(f"Accepted-state source: {payload['mode']} ({'explicit' if payload['explicit'] else 'default'})" + (f" | ref={payload['ref']}" if payload["ref"] else "") + f" | resolved={payload['resolved_commit']}")


def cmd_init(args: argparse.Namespace) -> None:
    if DATA.exists():
        raise SystemExit("Portfolio already exists; archive its manifest and worktrees deliberately before starting another")
    from .portfolio_storage import integrity_key
    integrity_key(create=True)
    baseline = git("rev-parse", "HEAD")
    contract = {
        "objective": args.objective, "metric": args.metric, "direction": args.direction,
        "minimum_evidence": args.minimum_evidence, "max_active": args.max_active,
        "authority": args.authority, "guardrail_definition": args.guardrail_definition,
        "evaluation_protocol": args.evaluation_protocol,
    }
    contract_digest = hashlib.sha256(json.dumps(contract, sort_keys=True).encode()).hexdigest()
    data = {
        "version": 3, "created_at": now(), "shared_contract": contract,
        "baseline": {"commit": baseline, "label": "BASE", "context_snapshot": args.context_snapshot, "contract_digest": contract_digest},
        "accepted_product": {"commit": baseline, "recorded_at": now(), "source": "lifecycle initialization", "predecessor": None},
        "selected": None, "variants": {}, "peer_reviews": [], "lessons": [],
        "agora": {"proposals": [], "votes": [], "decisions": [], "system_confirmations": []},
        "events": [{"at": now(), "kind": "BASE_SNAPSHOTTED", "commit": baseline, "contract_digest": contract_digest}],
    }
    accepted = snapshot_current_product(data)
    save(data)
    print(f"Initialized portfolio for {args.objective!r}; baseline={accepted[:12]}")


def cmd_spawn(args: argparse.Namespace) -> None:
    data = load()
    if args.variant in data["variants"]:
        raise SystemExit("Variant already exists")
    # A selected variant is the immutable seed for the next generation, not a
    # concurrently competing candidate. Counting it here reduces an N-way
    # cohort to N-1 children after the first selection.
    active = sum(item["status"] in {"CREATED", "RUNNING"} for item in data["variants"].values())
    if active >= data["shared_contract"]["max_active"]:
        raise SystemExit("Active-variant ceiling reached; stop one before spawning another")
    parent_item = data["variants"].get(getattr(args, "lineage_parent", None) or data.get("selected") or "")
    parent = args.parent or (parent_item["branch"] if parent_item else data["baseline"]["commit"])
    generation = int(parent_item.get("generation", 0)) + 1 if parent_item else 1
    parent_commit = git("rev-parse", parent)
    known_lessons = {item["id"] for item in data.get("lessons", [])}
    missing_lessons = [item for item in args.lesson if item not in known_lessons]
    if missing_lessons:
        raise SystemExit(f"Unknown approved lesson: {', '.join(missing_lessons)}")
    adopted_decisions = {item["id"]: item for item in data["agora"]["decisions"] if item["outcome"] == "adopt"}
    missing_decisions = [item for item in args.decision if item not in adopted_decisions]
    if missing_decisions:
        raise SystemExit(f"Unknown or unadopted agora decision: {', '.join(missing_decisions)}")
    wrong_parent = [item for item in args.decision if adopted_decisions[item].get("inheritance_parent") != (parent_item or {}).get("name")]
    if wrong_parent:
        raise SystemExit(f"Agora decision is not approved for this parent: {', '.join(wrong_parent)}")
    path = VARIANTS / args.variant
    branch = f"urace-variant/{args.variant}"
    path.parent.mkdir(parents=True, exist_ok=True)
    git("worktree", "add", "-b", branch, str(path), parent)
    try:
        from urace import __version__ as _urace_version
        _sys_commit = git("rev-parse", "HEAD")
    except Exception:
        _urace_version, _sys_commit = "unknown", "unknown"
    item = {
        "name": args.variant, "label": "MUTATION", "generation": generation,
        "branch": branch, "path": str(path), "parent_variant": parent_item.get("name") if parent_item else None,
        "lineage_parent_variant": parent_item.get("name") if parent_item else None,
        "accepted_parent_commit": parent_commit,
        "parent_ref": parent, "parent_commit": parent_commit, "mutation": args.mutation,
        "hypothesis": args.hypothesis, "expected_effect": args.expected_effect,
        "lesson_links": args.lesson, "decision_links": args.decision,
        "contract_digest": data["baseline"]["contract_digest"], "status": "CREATED",
        "created_at": now(), "runs": [], "observations": [], "selection_decisions": [],
        "system_version": {"runtime_version": _urace_version, "system_commit": _sys_commit, "recorded_at": now()},
    }
    data["variants"][args.variant] = item
    data["events"].append({"at": now(), "kind": "MUTATION_SPAWNED", "variant": args.variant, "generation": generation, "parent_variant": item["parent_variant"], "parent_commit": parent_commit, "mutation": args.mutation, "hypothesis": args.hypothesis})
    save(data)
    print(path)


def cmd_cohort(args: argparse.Namespace) -> None:
    import re as _re
    data = load()
    plan_path = (ROOT / args.plan).resolve() if not Path(args.plan).is_absolute() else Path(args.plan)
    plans = json.loads(plan_path.read_text(encoding="utf-8"))
    if not isinstance(plans, list) or len(plans) != args.count:
        raise SystemExit("Mutation plan must be a JSON array with exactly --count entries")
    if args.total_resource_budget <= 0:
        raise SystemExit("Total resource budget must be positive")
    planned_names = [name(plan.get("name", f"{args.prefix}-{index}")) if isinstance(plan, dict) else "" for index, plan in enumerate(plans, 1)]
    resumable = bool(getattr(args, "resume", False))
    existing_names = [item for item in planned_names if item in data["variants"]]
    active = sum(item["status"] in {"CREATED", "RUNNING"} for item in data["variants"].values())
    if active + args.count - len(existing_names) > data["shared_contract"]["max_active"]:
        raise SystemExit("Cohort would exceed the active-variant ceiling")
    if len(set(planned_names)) != len(planned_names) or (existing_names and not resumable):
        raise SystemExit("Mutation plan contains duplicate or existing variant names")
    required = {"mutation", "hypothesis", "expected_effect"}
    if any(not isinstance(plan, dict) or not required <= plan.keys() for plan in plans):
        raise SystemExit("Every plan entry requires mutation, hypothesis, and expected_effect")
    for plan in plans:
        for field in required:
            plan[field] = bounded_text(plan[field], field)
    for index, variant_name in enumerate(planned_names):
        if variant_name in data["variants"]:
            item = data["variants"][variant_name]; plan = plans[index]
            if item.get("mutation") != plan["mutation"] or item.get("hypothesis") != plan["hypothesis"]:
                raise SystemExit("Resumed cohort conflicts with an existing variant")
    allocation = args.total_resource_budget / args.count
    created = []
    for index, plan in enumerate(plans, 1):
        variant_name = name(plan.get("name", f"{args.prefix}-{index}"))
        if variant_name not in data["variants"]:
            cmd_spawn(argparse.Namespace(
                variant=variant_name, parent=args.parent, mutation=plan["mutation"],
                lineage_parent=getattr(args, "lineage_parent", None), hypothesis=plan["hypothesis"], expected_effect=plan["expected_effect"], lesson=plan.get("lessons", []), decision=plan.get("decisions", []),
            ))
        data = load(); item = variant(data, variant_name)
        cohort_generation = _re.fullmatch(r"generation-(\d+)", args.prefix)
        if cohort_generation:
            item["generation"] = int(cohort_generation.group(1))
        item["cohort"] = args.prefix
        item["priority_scope"] = plan.get("scope", "cross-document")
        item["scope_attribution"] = plan.get("scope_attribution")
        item["resource_budget"] = {"allocated": allocation, "unit": args.resource_unit, "source_total": args.total_resource_budget, "distribution": "EQUAL", "enforcement": "DECLARED; COMMAND TIMEOUT ENFORCED LOCALLY"}
        created.append(variant_name); save(data)
    data = load(); data["events"].append({"at": now(), "kind": "COHORT_CREATED", "cohort": args.prefix, "variants": created, "total_resource_budget": args.total_resource_budget, "resource_unit": args.resource_unit, "allocation_each": allocation}); save(data)
    print(json.dumps({"cohort": args.prefix, "variants": created, "allocation_each": allocation, "resource_unit": args.resource_unit}, indent=2))
