from __future__ import annotations

import contextlib
import fcntl
import datetime
import hashlib
import json
import os
import tempfile
import time
import uuid
from contextlib import contextmanager
from datetime import datetime as _datetime, timezone
from pathlib import Path
from typing import Any, Generator


RUNTIME_ROOT = Path(__file__).resolve().parents[1]
SYSTEM_ROOT = RUNTIME_ROOT.parent
ROOT = SYSTEM_ROOT.parent
CONFIG_PATH = Path(__file__).with_name("config.json")


def now() -> str:
    return _datetime.now(timezone.utc).isoformat()


def identifier(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
        temporary = Path(handle.name)
    temporary.replace(path)
    directory = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    atomic_write_text(path, json.dumps(value, indent=2, sort_keys=True) + "\n")


def durable_unlink(path: Path) -> None:
    path.unlink(missing_ok=True)
    if path.parent.exists():
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)


def process_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def _publish_state_lock(lock: Path, marker: str) -> int:
    # Publish only fully written metadata. A process killed before publication
    # leaves no lock that another process could mistake for a live owner.
    descriptor, temporary_name = tempfile.mkstemp(prefix=".state-lock-", dir=lock.parent)
    temporary = Path(temporary_name)
    try:
        payload = marker.encode()
        if os.write(descriptor, payload) != len(payload):
            raise OSError("Incomplete state lock metadata write")
        os.fsync(descriptor)
        os.link(temporary, lock)
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def _published_state_lock(path: Path) -> Generator[None, None, None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_suffix(".lock")
    descriptor = None
    try:
        for attempt in range(2):
            try:
                marker = json.dumps({"pid": os.getpid(), "started_at": _datetime.now(timezone.utc).isoformat()})
                descriptor = _publish_state_lock(lock, marker)
                break
            except FileExistsError as error:
                try:
                    raw = lock.read_text(encoding="utf-8").strip()
                    owner = json.loads(raw)["pid"]
                except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
                    try:
                        owner = int(raw.strip())
                    except (NameError, ValueError):
                        owner = -1
                if attempt == 0 and not process_exists(owner):
                    try:
                        _obs_path = path.parent / "stale-lock-observations.jsonl"
                        _obs_entry = json.dumps({"at": _datetime.now(timezone.utc).isoformat(), "stale_pid": owner, "lock": str(lock), "disposition": "removed"})
                        from .authenticated_journal import append_row
                        append_row(_obs_path,json.loads(_obs_entry))
                    except OSError:
                        pass
                    lock.unlink(missing_ok=True)
                    continue
                raise RuntimeError(f"state is locked by live process {owner}: {lock}") from error
        yield
    finally:
        if descriptor is not None:
            os.close(descriptor)
            lock.unlink(missing_ok=True)


@contextmanager
def state_lock(path: Path) -> Generator[None, None, None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Keep this inode: unlinking an advisory lock file would let contenders
    # acquire different inodes and enter the protected section concurrently.
    guard = path.with_suffix(".lock.guard")
    descriptor = os.open(guard, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError(f"state is locked by live process (kernel guard): {guard}") from error
        with _published_state_lock(path):
            yield
    finally:
        # Closing also releases the kernel guard on exceptions and process exit.
        os.close(descriptor)


def load_config() -> dict[str, Any]:
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    env_product = os.environ.get("URACE_ACTIVE_PRODUCT")
    if env_product:
        cfg["active_product"] = env_product
    active=cfg.get("active_product")
    entry=next((e for e in cfg.get("product_registry",[]) if e.get("name")==active and e.get("kind")=="bootstrapped" and e.get("status")=="ACTIVE"),None)
    if entry:
        from .product_creation import validate_entry
        validate_entry(entry,ROOT)
        registry=cfg["product_registry"];cfg={**cfg,**copy_mapping(entry["configuration"]),"product_registry":registry,"active_product":active,"_product_overlay_name":active,"product_improvement_enabled":entry.get("improvement_enabled",True)}
    return cfg


def copy_mapping(value):
    return json.loads(json.dumps(value))


def save_config(config: dict[str, Any]) -> None:
    overlay=config.get('_product_overlay_name')
    if overlay:
        base=json.loads(CONFIG_PATH.read_text());registry=config.get('product_registry',base.get('product_registry',[]))
        if config.get('active_product')==overlay:
            entry=next((e for e in registry if e.get('name')==overlay and e.get('kind')=='bootstrapped'),None)
            if entry is None:raise ValueError('Active isolated product disappeared')
            entry['configuration']={k:v for k,v in config.items() if k not in ('product_registry','active_product','_product_overlay_name')}
            from .product_creation import validate_entry
            validate_entry(entry,ROOT)
        else:base['active_product']=config.get('active_product')
        base['product_registry']=registry;atomic_write_json(CONFIG_PATH,base);return
    atomic_write_json(CONFIG_PATH,config)


def state_path(config: dict[str, Any]) -> Path:
    active = config.get("active_product")
    if active:
        registry = config.get("product_registry", [])
        entry = next(
            (e for e in registry if e.get("name") == active and e.get("status", "ACTIVE") == "ACTIVE"),
            None,
        )
        if entry:
            path = Path(entry["state_path"])
            return path if path.is_absolute() else RUNTIME_ROOT / path
    path = Path(config["state_path"])
    return path if path.is_absolute() else RUNTIME_ROOT / path


def load_state(config: dict[str, Any]) -> dict[str, Any]:
    path = state_path(config)
    if not path.exists():
        raise RuntimeError("URACE is not initialized; run `urace init`")
    return json.loads(path.read_text(encoding="utf-8"))


def load_state_for_read(config: dict[str, Any]) -> dict[str, Any] | None:
    import sys
    try:
        return load_state(config)
    except (RuntimeError, OSError, json.JSONDecodeError) as error:
        print(f"urace: {error}", file=sys.stderr)
        return None


def _check_state_invariants(state: dict) -> None:
    """Raise ValueError if state violates core invariants.

    Only enforced on bootstrapped states (state_version >= 1) to avoid
    rejecting minimal test stubs or pre-init state documents.
    """
    # Invariant: schema_version must not decrease
    if state.get('schema_version', 1) < 1:
        raise ValueError(f"Invariant violated: schema_version={state.get('schema_version')}")
    # Only enforce structural invariants on post-bootstrap state documents
    if int(state.get('state_version', 0)) < 1:
        return
    # Invariant: self_evolution_policy must be well-formed if present
    sep = state.get('self_evolution_policy')
    if sep is not None and (not isinstance(sep, dict) or 'mode' not in sep):
        raise ValueError("Invariant violated: self_evolution_policy malformed")
    # Invariant: authority must be non-empty if present (prevent accidental erasure)
    auth = state.get('authority')
    if auth is not None and not auth:
        raise ValueError("Invariant violated: authority was present but is now empty")


def save_state(config: dict[str, Any], state: dict[str, Any]) -> None:
    path = state_path(config)
    path.parent.mkdir(parents=True, exist_ok=True)
    from .resource_usage import archive_calls
    archive_calls(config, state)
    _check_state_invariants(state)
    state["state_version"] += 1
    state["updated_at"] = now()
    atomic_write_json(path, state)
    from .resource_usage import write_projection
    try:write_projection(config,state)
    except OSError:
        # State is already durable. Reporting can use its existing full-state fallback.
        import sys
        print('urace: receipt read model unavailable; full-state fallback retained',file=sys.stderr)


def transaction_path(config: dict[str, Any]) -> Path:
    return state_path(config).parent / "transaction.json"


def input_directory(config: dict[str, Any]) -> Path:
    return state_path(config).parent / "inbox"


# ── §62h Technique Applicability Gate ────────────────────────────────────────

_TECHNIQUE_NAMES = {"T1", "T2", "T3", "T4", "T5", "T6"}
_SD_ALWAYS_TRUE = {"T1", "T2", "T3", "T4", "T6"}


def technique_applicability_gate(
    technique: str,
    state: dict,
    config: dict,
    *,
    applied_this_cycle: set | None = None,
) -> dict:
    """Evaluate TechniqueApplicabilityGate for one technique.

    Returns TechniqueApplicationRecord (verdict, reason, sd_result, applied_at).
    Caller must append to state['technique_application_log'] if desired.
    """
    from datetime import datetime, timezone
    _at = datetime.now(timezone.utc).isoformat()
    applied_this_cycle = applied_this_cycle or set()

    # Guard 1: dormant with no pending obligation
    if state.get("lifecycle_state") == "DORMANT":
        pending_log = state.get("technique_application_log", [])
        has_obligation = any(
            r.get("technique") == technique and r.get("verdict") == "DEFER"
            for r in pending_log[-20:]
        )
        if not has_obligation:
            return {"id": identifier("ta"), "technique": technique, "verdict": "SKIP",
                    "reason": "dormant_no_obligation", "applied_at": _at}

    # Guard 2: idempotent — already applied this cycle
    if technique in applied_this_cycle:
        return {"id": identifier("ta"), "technique": technique, "verdict": "SKIP",
                "reason": "already_applied_this_cycle", "applied_at": _at}

    # Guard 3: self-determinable → APPLY
    sd_result = technique in _SD_ALWAYS_TRUE or technique not in {"T5"}
    if sd_result:
        return {"id": identifier("ta"), "technique": technique, "verdict": "APPLY",
                "reason": "self_determinable", "applied_at": _at, "sd_result": True}

    # Guard 4: SD=False, check credits
    executor_state = state.get("executor_state", {})
    daily_calls = executor_state.get("calls_today", 0)
    daily_limit = config.get("executor", {}).get("max_executor_calls_per_30d", 20)
    credits_remaining = None if daily_limit is None else max(0, daily_limit - daily_calls)
    technique_credit_cost = 1  # one executor call to determine semantic boundary
    if credits_remaining is None or credits_remaining > technique_credit_cost:
        return {"id": identifier("ta"), "technique": technique, "verdict": "DELEGATE_EXECUTOR",
                "reason": "sd_false_credits_available", "applied_at": _at,
                "sd_result": False, "executor_delegated": False, "credits_consumed": 0}

    # Guard 5: defer
    return {"id": identifier("ta"), "technique": technique, "verdict": "DEFER",
            "reason": "sd_false_insufficient_credits", "applied_at": _at, "sd_result": False}


# ── §62i AP11/AP12/AP18 helper functions ─────────────────────────────────────

def bridge_record(
    bridge_name: str,
    source_schema: str,
    target_schema: str,
    *,
    loss_declared: bool = False,
    dropped_fields: list | None = None,
) -> dict:
    """AP11 — produce a BridgeRecord for a bridge translation event."""
    from datetime import datetime, timezone
    r: dict = {
        "id": identifier("br"),
        "bridge_name": bridge_name,
        "source_schema": source_schema,
        "target_schema": target_schema,
        "translated_at": datetime.now(timezone.utc).isoformat(),
    }
    if loss_declared:
        r["loss_declared"] = True
    if dropped_fields:
        r["dropped_fields"] = dropped_fields
    return r


def orchestrator_record(
    orchestrator_name: str,
    started_at: str,
    phases_completed: list,
    outcome: str,
    *,
    completed_at: str | None = None,
    failure_phase: str | None = None,
    postconditions_met: bool | None = None,
) -> dict:
    """AP12 — produce an OrchestratorRecord for a completed orchestration."""
    r: dict = {
        "id": identifier("orch"),
        "orchestrator_name": orchestrator_name,
        "started_at": started_at,
        "phases_completed": phases_completed,
        "outcome": outcome,
    }
    if completed_at:
        r["completed_at"] = completed_at
    if failure_phase:
        r["failure_phase"] = failure_phase
    if postconditions_met is not None:
        r["postconditions_met"] = postconditions_met
    return r


def scheduled_task_due(task: dict, now_ts: float) -> bool:
    """Return True if a ScheduledTask is due for execution."""
    from datetime import datetime, timezone
    schedule = task.get("schedule", {})
    kind = schedule.get("kind")
    next_run = schedule.get("next_run_at")
    if not next_run:
        return kind == "IMMEDIATE"
    try:
        due_ts = datetime.fromisoformat(next_run).timestamp()
        return now_ts >= due_ts
    except (ValueError, TypeError):
        return False


def nullable_limit(settings: dict, key: str, default: int) -> int | None:
    """An explicit null is unlimited; absence keeps the compatibility default."""
    value=settings.get(key,default)
    return None if value is None else int(value)


def integration_context() -> dict[str, str]:
    """Correlation only: environment metadata never grants authority or budget."""
    keys={'job_id':'URACE_BRIDGE_JOB','root_request_id':'URACE_BRIDGE_ROOT_REQUEST','project_id':'URACE_BRIDGE_PROJECT','executor_id':'URACE_BRIDGE_EXECUTOR'}
    result={}
    for key,env in keys.items():
        value=os.environ.get(env)
        if value and len(value)<=512 and all(ord(c)>=32 for c in value):result[key]=value
    return result if 'job_id' in result else {}
