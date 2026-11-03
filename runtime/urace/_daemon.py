"""OS-agnostic foreground improvement daemon. No OS service manager dependency."""
from __future__ import annotations
import json, os, signal, sys, time
from pathlib import Path


def _pid_path(config: dict) -> Path:
    from ._common import state_path
    return state_path(config).parent / "daemon.pid"


def _read_pid(config: dict) -> int | None:
    p = _pid_path(config)
    if not p.exists():
        return None
    try:
        return int(p.read_text().strip())
    except (ValueError, OSError):
        return None


def _write_pid(config: dict) -> None:
    p = _pid_path(config)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(str(os.getpid()))


def _clear_pid(config: dict) -> None:
    try:
        _pid_path(config).unlink(missing_ok=True)
    except OSError:
        pass


def _is_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def dispatch(args, config: dict) -> int:
    action = getattr(args, "daemon_action", None) or "start"
    as_json = getattr(args, "json", False) or getattr(args, "format", None) == "json"

    if action == "status":
        pid = _read_pid(config)
        running = pid is not None and _is_running(pid)
        result = {"status": "running" if running else "stopped", "pid": pid if running else None}
        if as_json:
            print(json.dumps(result))
        else:
            print(f"Daemon: {'running (pid=' + str(pid) + ')' if running else 'stopped'}")
        return 0

    if action == "stop":
        pid = _read_pid(config)
        if pid is None or not _is_running(pid):
            result = {"status": "not_running"}
            if as_json:
                print(json.dumps(result))
            else:
                print("Daemon not running.")
            return 0
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError as e:
            result = {"status": "error", "error": str(e)}
            if as_json:
                print(json.dumps(result))
            else:
                print(f"Stop failed: {e}")
            return 1
        result = {"status": "stopped", "pid": pid}
        if as_json:
            print(json.dumps(result))
        else:
            print(f"Sent SIGTERM to daemon pid={pid}")
        return 0

    # action == "start"
    existing_pid = _read_pid(config)
    if existing_pid is not None and _is_running(existing_pid):
        result = {"status": "already_running", "pid": existing_pid}
        if as_json:
            print(json.dumps(result))
        else:
            print(f"Daemon already running (pid={existing_pid}). Use 'urace daemon stop' first.")
        return 1

    interval_minutes = getattr(args, "interval_minutes", 30.0)
    max_cycles = getattr(args, "max_cycles", 0) or getattr(args, "cycles", 0)
    interval_sec = max(60.0, float(interval_minutes) * 60)

    _write_pid(config)
    stopped = [False]

    def _handle_signal(signum, frame):
        stopped[0] = True

    signal.signal(signal.SIGTERM, _handle_signal)
    try:
        signal.signal(signal.SIGHUP, _handle_signal)
    except AttributeError:
        pass  # Windows has no SIGHUP

    if as_json:
        print(json.dumps({"status": "started", "pid": os.getpid(), "interval_minutes": interval_minutes, "max_cycles": max_cycles or "infinity"}))
        sys.stdout.flush()
    else:
        limit_label = str(max_cycles) if max_cycles else "infinity"
        print(f"URACE daemon started (pid={os.getpid()}, interval={interval_minutes}m, max_cycles={limit_label}). Ctrl+C to stop.")

    from . import cli as _cli
    count = 0
    try:
        while not stopped[0]:
            if max_cycles and count >= max_cycles:
                break
            if as_json:
                print(json.dumps({"event": "cycle_start", "cycle": count + 1}))
                sys.stdout.flush()
            else:
                print(f"[daemon] cycle {count + 1}" + (f"/{max_cycles}" if max_cycles else ""))
            try:
                _cli.main(["auto", "--cycles", "1", "--quiet"] + (["--json"] if as_json else []))
            except SystemExit:
                pass
            except Exception as exc:
                if as_json:
                    print(json.dumps({"event": "cycle_error", "cycle": count + 1, "error": str(exc)}))
                else:
                    print(f"[daemon] cycle error: {exc}")
            count += 1
            if stopped[0] or (max_cycles and count >= max_cycles):
                break
            deadline = time.monotonic() + interval_sec
            while time.monotonic() < deadline and not stopped[0]:
                time.sleep(min(5.0, deadline - time.monotonic()))
    except KeyboardInterrupt:
        stopped[0] = True
    finally:
        _clear_pid(config)
        if as_json:
            print(json.dumps({"status": "stopped", "cycles_completed": count}))
        else:
            print(f"\n[daemon] stopped after {count} cycle(s).")
    return 0
