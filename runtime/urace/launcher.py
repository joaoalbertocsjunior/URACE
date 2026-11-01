from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from . import evolution_guard


RUNTIME_ROOT = Path(__file__).resolve().parents[1]
SYSTEM_ROOT = RUNTIME_ROOT.parent
PRODUCT_ROOT = SYSTEM_ROOT.parent
STATE_PATH = SYSTEM_ROOT / "state/state.json"
STABLE_RUNTIME = SYSTEM_ROOT / "state/stable-runtime"
_DEFAULT_STATE_PATH = STATE_PATH
_DEFAULT_STABLE_RUNTIME = STABLE_RUNTIME
EXPECTED_KERNEL_HASHES = evolution_guard.kernel_hashes(PRODUCT_ROOT)


def configured_paths() -> tuple[Path, Path]:
    """Resolve the same active Product state as the controller, without importing it."""
    if STATE_PATH != _DEFAULT_STATE_PATH or STABLE_RUNTIME != _DEFAULT_STABLE_RUNTIME:
        return STATE_PATH, STABLE_RUNTIME
    path = RUNTIME_ROOT / 'urace/config.json'
    if not path.exists():
        return STATE_PATH, STABLE_RUNTIME
    config = json.loads(path.read_text())
    active = os.environ.get('URACE_ACTIVE_PRODUCT') or config.get('active_product')
    entry = next((p for p in config.get('product_registry', [])
                  if p.get('name') == active and p.get('status', 'ACTIVE') == 'ACTIVE'), None) if active else None
    value = (entry or {}).get('state_path', config.get('state_path', str(STATE_PATH)))
    state = Path(value)
    if not state.is_absolute():
        state = RUNTIME_ROOT / state
    return state, state.parent / 'stable-runtime'


def validate_activation_candidate() -> list[str]:
    _, stable = configured_paths()
    return evolution_guard.validate_candidate(PRODUCT_ROOT, PRODUCT_ROOT, stable, timeout=900, expected_kernel_hashes=EXPECTED_KERNEL_HASHES)


def _atomic_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
        temporary = Path(handle.name)
    temporary.replace(path)


def pending_activation() -> bool:
    state, _ = configured_paths()
    if not state.exists():
        return False
    return bool(json.loads(state.read_text(encoding="utf-8")).get("pending_runtime_activation"))


def restore_stable_runtime(reason: str) -> None:
    state_path, stable = configured_paths()
    manifest_path = stable / "manifest.json"
    if not manifest_path.exists():
        raise RuntimeError("runtime activation failed and no stable runtime snapshot exists")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for relative in manifest["files"]:
        snapshot = stable / relative
        _atomic_text(PRODUCT_ROOT / relative, snapshot.read_text(encoding="utf-8"))
    state = json.loads(state_path.read_text(encoding="utf-8"))
    transaction = state.get("pending_runtime_activation") or {}
    state.setdefault("evidence", []).append({
        "at": datetime.now(timezone.utc).isoformat(), "kind": "runtime-activation-rollback",
        "transaction": transaction.get("transaction"), "reason": reason, "outcome": "RESTORED_STABLE_RUNTIME",
    })
    state["pending_runtime_activation"] = None
    state["restart_requested"] = False
    state["state_version"] = int(state.get("state_version", 0)) + 1
    _atomic_text(state_path, json.dumps(state, indent=2, sort_keys=True) + "\n")


def main() -> int:
    if os.environ.get("URACE_LAUNCHER_CHILD") == "1":
        from .cli import main as cli_main
        return cli_main()
    environment = os.environ.copy()
    environment["URACE_LAUNCHER_CHILD"] = "1"
    while True:
        try:
            completed = subprocess.run([sys.executable, "-m", "urace", *sys.argv[1:]], env=environment, check=False)
        except KeyboardInterrupt:
            return 130
        if completed.returncode == 75:
            try:
                guard_errors = validate_activation_candidate()
            except Exception as error:
                restore_stable_runtime("independent evolution guard failed: " + type(error).__name__)
                environment.pop("URACE_POST_UPGRADE", None)
                continue
            if guard_errors:
                restore_stable_runtime("independent evolution guard rejected activation: " + "; ".join(guard_errors))
                environment.pop("URACE_POST_UPGRADE", None)
                continue
            environment["URACE_POST_UPGRADE"] = "1"
            continue
        if completed.returncode == 76:
            # One durable retry lets the core controller confirm recurrence;
            # further retry or repair decisions remain in lifecycle state.
            continue
        if completed.returncode != 0 and pending_activation():
            restore_stable_runtime(f"candidate process exited with {completed.returncode}")
            environment.pop("URACE_POST_UPGRADE", None)
            continue
        return completed.returncode
