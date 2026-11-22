from __future__ import annotations

import json
import os
import tempfile
import uuid
from contextlib import contextmanager
from datetime import datetime as _datetime, timezone
from pathlib import Path
from typing import Any, Generator

from .logging_config import get_logger

_log = get_logger(__name__)

try:
    import fcntl as _fcntl
    _HAS_FCNTL = True
except ImportError:
    _HAS_FCNTL = False


RUNTIME_ROOT = Path(__file__).resolve().parents[1]
SYSTEM_ROOT = RUNTIME_ROOT.parent
# Package config (shipped with pip, overwritten on upgrade — not for user data)
_PACKAGE_CONFIG_PATH = Path(__file__).with_name("config.json")
# User-data config dir (~/.urace/config.json) survives pip upgrades.
# Only preferred when running from a production venv install under ~/.urace/,
# NOT when running from a development source tree (where package config IS the project config).
_USER_CONFIG_PATH = Path.home() / ".urace" / "config.json"
_RUN_FROM_PROD_VENV = str(_PACKAGE_CONFIG_PATH).startswith(str(Path.home() / ".urace"))
CONFIG_PATH = (_USER_CONFIG_PATH if (_RUN_FROM_PROD_VENV and _USER_CONFIG_PATH.exists())
               else _PACKAGE_CONFIG_PATH)
# Prod installs live under ~/.urace/; dev source trees are self-contained at SYSTEM_ROOT.
ROOT = Path.home() / ".urace" if _RUN_FROM_PROD_VENV else SYSTEM_ROOT


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
    try:
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    except OSError:
        pass


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    atomic_write_text(path, json.dumps(value, indent=2, sort_keys=True) + "\n")


def durable_unlink(path: Path) -> None:
    path.unlink(missing_ok=True)
    if path.parent.exists():
        try:
            directory = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        except OSError:
            pass


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
            if _HAS_FCNTL:
                _fcntl.flock(descriptor, _fcntl.LOCK_EX | _fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError(f"state is locked by live process (kernel guard): {guard}") from error
        with _published_state_lock(path):
            yield
    finally:
        # Closing also releases the kernel guard on exceptions and process exit.
        os.close(descriptor)


def load_config() -> dict[str, Any]:
    # CONFIG_PATH is already resolved to user-data dir when available (module-level).
    # Auto-migrate from package config to user-data dir on first run with real data.
    _read_path = CONFIG_PATH
    if _read_path == _PACKAGE_CONFIG_PATH and not _USER_CONFIG_PATH.exists():
        try:
            _pkg = json.loads(_PACKAGE_CONFIG_PATH.read_text(encoding="utf-8"))
            if _pkg.get("product_registry") or not str(_pkg.get("state_path", "")).startswith("/tmp/"):
                _USER_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
                _USER_CONFIG_PATH.write_text(_PACKAGE_CONFIG_PATH.read_text(encoding="utf-8"), encoding="utf-8")
                _read_path = _USER_CONFIG_PATH
        except (OSError, json.JSONDecodeError):
            pass
    cfg = json.loads(_read_path.read_text(encoding="utf-8"))
    env_product = os.environ.get("URACE_ACTIVE_PRODUCT")
    if env_product:
        cfg["active_product"] = env_product
    active=cfg.get("active_product")
    entry=next((e for e in cfg.get("product_registry",[]) if e.get("name")==active and e.get("kind")=="bootstrapped" and e.get("status")=="ACTIVE"),None)
    if entry:
        from .product_creation import validate_entry
        validate_entry(entry,ROOT)
        registry=cfg["product_registry"];cfg={**cfg,**copy_mapping(entry["configuration"]),"product_registry":registry,"active_product":active,"_product_overlay_name":active,"product_improvement_enabled":entry.get("improvement_enabled",True)}
    try:
        from .config_schema import validate as _schema_validate
        for _err in _schema_validate(cfg):
            _log.warning("config warning: %s: %s", _err['path'], _err['error'])
    except Exception:
        pass
    return cfg


def copy_mapping(value):
    return json.loads(json.dumps(value))


def save_config(config: dict[str, Any]) -> None:
    # Prefer user-data dir to avoid pip upgrade overwriting config. When CONFIG_PATH
    # was externally patched (test fixtures), that patch is used as-is.
    if CONFIG_PATH == _PACKAGE_CONFIG_PATH:
        # First save on a fresh install: migrate to user-data dir.
        _dest = _USER_CONFIG_PATH
        _dest.parent.mkdir(parents=True, exist_ok=True)
    else:
        _dest = CONFIG_PATH  # already user-data dir, or externally patched for tests
    overlay=config.get('_product_overlay_name')
    if overlay:
        _base_src = _dest if _dest.exists() else _PACKAGE_CONFIG_PATH
        base=json.loads(_base_src.read_text());registry=config.get('product_registry',base.get('product_registry',[]))
        if config.get('active_product')==overlay:
            entry=next((e for e in registry if e.get('name')==overlay and e.get('kind')=='bootstrapped'),None)
            if entry is None:raise ValueError('Active isolated product disappeared')
            entry['configuration']={k:v for k,v in config.items() if k not in ('product_registry','active_product','_product_overlay_name')}
            from .product_creation import validate_entry
            validate_entry(entry,ROOT)
        else:base['active_product']=config.get('active_product')
        base['product_registry']=registry;atomic_write_json(_dest,base);return
    atomic_write_json(_dest,config)


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
    try:
        return load_state(config)
    except (RuntimeError, OSError, json.JSONDecodeError) as error:
        _log.warning("state load failed: %s", error)
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


def _post_save_effects(config: dict[str, Any], state: dict[str, Any]) -> None:
    """Side-effects that run after state is durably written.

    Separated from save_state so tests can patch a single name instead of two
    module-level imports from resource_usage.
    """
    from .resource_usage import archive_calls, write_projection
    archive_calls(config, state)
    try:
        write_projection(config, state)
    except OSError:
        _log.warning("receipt read model unavailable; full-state fallback retained")


def save_state(config: dict[str, Any], state: dict[str, Any]) -> None:
    path = state_path(config)
    path.parent.mkdir(parents=True, exist_ok=True)
    _check_state_invariants(state)
    state["state_version"] += 1
    state["updated_at"] = now()
    atomic_write_json(path, state)
    _post_save_effects(config, state)
    from .event_bus import _BUS as _eb
    _eb.publish('state.saved', state_version=state["state_version"])


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
    from datetime import datetime
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


# --- State accessor utilities ---

def get_executor_state(state: dict[str, Any]) -> dict[str, Any]:
    """Return the executor_state sub-dict, guaranteed non-None.

    Single access point for the executor_state key so that if the key path
    ever changes, only this function needs updating.
    """
    return state.get("executor_state") or {}


def get_executor_calls(state: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the executor_calls list from state, guaranteed non-None list."""
    return get_executor_state(state).get("executor_calls") or []


def load_json_path(path: Path) -> Any:
    """Load JSON from path with a clear error on parse failure.

    Prefer this over inline json.loads(path.read_text()) in new code so that
    IOError and JSONDecodeError both surface with the offending path in the message.
    """
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc


# Re-export queue_input here so callers can do `from ._common import queue_input`
# without a separate import of urace.inputs.
from .inputs import queue_input as queue_input  # noqa: E402


# ---------------------------------------------------------------------------
# Protocol generation negotiation (N1 — version-gate for mesh-llm integration)
# ---------------------------------------------------------------------------
PROTOCOL_GENERATION: int = 1
PROTOCOL_GENERATION_MIN_SUPPORTED: int = 1


# ---------------------------------------------------------------------------
# Named fee constants (P2.2 — single source of truth for economic rates)
# ---------------------------------------------------------------------------
MINT_STAKE_UNITS: int = 3
COMPOSITION_REFERRAL_RATE: float = 0.20
DELIVERY_FEE_FRACTION: float = 0.10
PROTOCOL_FEE_FRACTION: float = 0.02
ESCROW_CUSTODY_REWARD_RATE: float = 0.03  # fraction of ask_price paid to escrow holder on success


# ---------------------------------------------------------------------------
# Audit row helper (P2.3 — DRY: adds timestamps automatically)
# ---------------------------------------------------------------------------
def emit_audit_row(exchange, *, kind: str, **fields) -> dict:
    """Append an audit row with auto-populated at_unix and at timestamps.

    Usage: emit_audit_row(exchange, kind='SOME_EVENT', foo='bar', n=42)
    Returns the emitted row dict.
    """
    import time as _time
    row = {
        'kind': kind,
        **fields,
        'at_unix': _time.time(),
        'at': _datetime.now(timezone.utc).isoformat(),
    }
    exchange.append_audit_row(row)
    return row


# ── Phase 7B — state key migration helpers ────────────────────────────────────

def migrate_state_keys(state: dict[str, Any]) -> dict[str, Any]:
    """Migrate deprecated state keys to canonical names (non-destructive).

    connector_sources (list) → sources (dict): only migrates if sources is absent.
    trace_records (list)     → traces (list): only migrates if traces is absent.

    Returns the mutated state dict (same object).
    """
    # connector_sources → sources
    if 'connector_sources' in state and 'sources' not in state:
        legacy = state['connector_sources']
        if isinstance(legacy, list):
            state['sources'] = {
                s['id']: s for s in legacy
                if isinstance(s, dict) and 'id' in s
            }
    # trace_records → traces
    if 'trace_records' in state and 'traces' not in state:
        state['traces'] = state['trace_records']
    return state
