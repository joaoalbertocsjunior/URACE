"""OS-agnostic foreground improvement daemon. No OS service manager dependency."""
from __future__ import annotations
import json, os, signal, sys, time
import socket as _socket
import threading as _threading
from pathlib import Path

RPC_TCP_HOST = "127.0.0.1"
RPC_TCP_PORT = 7474
_RPC_SCHEMA = "urace-rpc-v1"


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


def _rpc_socket_server(config):
    """Return a bound TCP server socket."""
    srv = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
    srv.setsockopt(_socket.SOL_SOCKET, _socket.SO_REUSEADDR, 1)
    srv.bind((RPC_TCP_HOST, RPC_TCP_PORT))
    srv.listen(8)
    return srv

def _handle_rpc_client(conn, config, stopped):
    import json as _json
    try:
        conn.settimeout(10.0)
        data = b""
        while b"\n" not in data:
            chunk = conn.recv(1024)
            if not chunk:
                return
            data += chunk
        msg = _json.loads(data.split(b"\n")[0].decode("utf-8"))
        method = msg.get("method", "")
        if method == "status":
            pid = _read_pid(config)
            running = pid is not None and _is_running(pid)
            resp = {"schema": _RPC_SCHEMA, "status": "running" if running else "stopped", "pid": pid}
        elif method == "stop":
            stopped[0] = True
            resp = {"schema": _RPC_SCHEMA, "status": "stopping"}
        elif method == "ping":
            resp = {"schema": _RPC_SCHEMA, "pong": True}
        elif method == "dispatch":
            # Run any urace argv inline and return captured JSON output
            argv = msg.get("argv", [])
            import io, contextlib
            from . import cli as _cli_mod
            buf = io.StringIO()
            try:
                with contextlib.redirect_stdout(buf):
                    _cli_mod.main(list(argv) + (["--json"] if "--json" not in argv else []))
                resp = {"schema": _RPC_SCHEMA, "output": buf.getvalue().strip()}
            except Exception as _de:
                resp = {"schema": _RPC_SCHEMA, "error": str(_de), "output": buf.getvalue().strip()}
        elif method == "events":
            limit = int(msg.get("limit", 20))
            import io, contextlib
            from . import cli as _cli_mod
            buf = io.StringIO()
            try:
                with contextlib.redirect_stdout(buf):
                    _cli_mod.main(["exchange", "network-audit", "list",
                                   "--limit", str(limit), "--json"])
                resp = {"schema": _RPC_SCHEMA, "output": buf.getvalue().strip()}
            except Exception as _ee:
                resp = {"schema": _RPC_SCHEMA, "error": str(_ee)}
        else:
            resp = {"schema": _RPC_SCHEMA, "error": f"unknown method: {method}"}
        conn.sendall((_json.dumps(resp) + "\n").encode("utf-8"))
    except Exception:
        pass
    finally:
        try: conn.close()
        except Exception: pass

def _run_rpc_server(config, stopped):
    try:
        srv = _rpc_socket_server(config)
    except OSError:
        return  # port in use — degrade gracefully
    srv.settimeout(2.0)
    while not stopped[0]:
        try:
            conn, _ = srv.accept()
            t = _threading.Thread(target=_handle_rpc_client, args=(conn, config, stopped), daemon=True)
            t.start()
        except _socket.timeout:
            continue
        except OSError:
            break
    try: srv.close()
    except Exception: pass


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
            print(f"urace is already running (pid={existing_pid}). Run 'urace stop' to stop it first.")
        return 1

    interval_minutes = getattr(args, "interval_minutes", 30.0)
    max_cycles = getattr(args, "max_cycles", 0) or getattr(args, "cycles", 0)
    interval_sec = max(60.0, float(interval_minutes) * 60)

    _write_pid(config)
    # Start P2P exchange server as a tracked subprocess so urace stop terminates it.
    # Use a list-cell ref so the signal handler (main thread) can reach the proc.
    _p2p_proc_ref = [None]
    _p2p_ready = _threading.Event()

    def _start_p2p_server():
        try:
            import subprocess, sys as _sys
            _net = config.get('network', {})
            _port = str(_net.get('port', 7301))
            _tunnel = _net.get('tunnel', 'auto')
            proc = subprocess.Popen([_sys.executable, '-m', 'urace', 'exchange', 'network', 'serve',
                                     '--host', '0.0.0.0', '--port', _port, '--tunnel', _tunnel])
            _p2p_proc_ref[0] = proc
        finally:
            _p2p_ready.set()
        try:
            from .nat_check import detect_nat_type
            _nat = detect_nat_type()
            if _nat and _nat.get('nat_type') == 'symmetric':
                import logging as _logging
                _logging.getLogger('urace.daemon').warning(
                    "Symmetric NAT detected — relay routing recommended. "
                    "Run: urace exchange bootstrap --as-relay or configure a relay peer."
                )
        except Exception:
            pass
        try:
            proc.wait()
        except Exception:
            pass

    _p2p_thread = _threading.Thread(target=_start_p2p_server, daemon=True)
    _p2p_thread.start()
    stopped = [False]
    _rpc_thread = _threading.Thread(target=_run_rpc_server, args=(config, stopped), daemon=True)
    _rpc_thread.start()

    def _handle_signal(_signum, _frame):
        stopped[0] = True
        # Terminate the P2P exchange server subprocess so it doesn't orphan.
        # Wait up to 2s for the thread to assign the proc ref (eliminates start-up race).
        _p2p_ready.wait(timeout=2.0)
        proc = _p2p_proc_ref[0]
        if proc is not None:
            try:
                proc.terminate()
            except OSError:
                pass

    signal.signal(signal.SIGTERM, _handle_signal)

    _reload_flag = [False]

    def _handle_sighup(_signum, _frame):
        _reload_flag[0] = True

    try:
        signal.signal(signal.SIGHUP, _handle_sighup)
    except AttributeError:
        pass  # Windows

    if as_json:
        print(json.dumps({"status": "started", "pid": os.getpid(), "interval_minutes": interval_minutes, "max_cycles": max_cycles or "infinity"}))
        sys.stdout.flush()
    else:
        limit_label = str(max_cycles) if max_cycles else "infinity"
        print(f"URACE daemon started (pid={os.getpid()}, interval={interval_minutes}m, max_cycles={limit_label}). Ctrl+C to stop.")

    from . import cli as _cli
    from .daemon_scheduler import make_scheduler
    count = 0

    def _run_one_cycle():
        nonlocal count
        if stopped[0]:
            return
        if _reload_flag[0]:
            _reload_flag[0] = False
            try:
                from ._common import CONFIG_PATH as _cp
                import json as _j
                _new_config = _j.loads(_cp.read_text())
                _old_net = config.get('network', {})
                _new_net = _new_config.get('network', {})
                _changed = [k for k in set(list(_old_net.keys()) + list(_new_net.keys()))
                            if _old_net.get(k) != _new_net.get(k)]
                config.update(_new_config)
                if as_json:
                    print(json.dumps({"event": "reloaded", "changed_sections": list(set(
                        k.split('.')[0] for k in _changed)) or ["none"]}))
                    sys.stdout.flush()
                else:
                    print("[daemon] config reloaded")
            except Exception as _e:
                if as_json:
                    print(json.dumps({"event": "reload_error", "error": str(_e)}))
                else:
                    print(f"[daemon] reload error: {_e}")
        if max_cycles and count >= max_cycles:
            stopped[0] = True
            return
        if as_json:
            print(json.dumps({"event": "cycle_start", "cycle": count + 1}))
            sys.stdout.flush()
        else:
            print(f"[daemon] cycle {count + 1}" + (f"/{max_cycles}" if max_cycles else ""))
        try:
            _cli.main(["auto", "--cycles", "1", "--quiet"] + (["--json"] if as_json else []), _config=config)
        except SystemExit:
            pass
        except Exception as exc:
            if as_json:
                print(json.dumps({"event": "cycle_error", "cycle": count + 1, "error": str(exc)}))
            else:
                print(f"[daemon] cycle error: {exc}")
        count += 1
        if max_cycles and count >= max_cycles:
            stopped[0] = True

    scheduler = make_scheduler(interval_sec, _run_one_cycle, stop_flag=stopped)
    try:
        scheduler.run_blocking()
    except KeyboardInterrupt:
        stopped[0] = True
    finally:
        _clear_pid(config)
        if as_json:
            print(json.dumps({"status": "stopped", "cycles_completed": count}))
        else:
            print(f"\n[daemon] stopped after {count} cycle(s).")
    return 0
