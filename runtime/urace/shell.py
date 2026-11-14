"""Interactive URACE control shell.

urace shell — persistent REPL over the entire URACE control plane.

Slash commands  → control shortcuts (/stop /pause /status /events /config /help)
Known commands  → run inline via main() (exchange network discover, status, etc.)
Freeform text   → routed through NL classifier → executor
"""
from __future__ import annotations
import json, os, sys
from pathlib import Path

_SLASH_COMMANDS = {
    '/help':    'show this help',
    '/status':  'daemon + P2P status',
    '/stop':    'stop daemon and P2P server',
    '/pause':   'pause improvement loop',
    '/resume':  'resume improvement loop',
    '/events':  'show recent audit events [/events N] [--follow|-f]',
    '/config':  'get or set config  /config [key] [value]  (dotted keys: p2p.network_mode)',
    '/peers':   'show connected peers',
    '/roles':   'show node roles',
    '/exit':    'exit shell (also /quit)',
    '/quit':    'exit shell',
}


# ── daemon RPC helpers ────────────────────────────────────────────────────────

def _rpc(method: str, **kwargs) -> dict | None:
    import socket as _s
    from . import _daemon
    try:
        sock = _s.socket(_s.AF_INET, _s.SOCK_STREAM)
        sock.settimeout(3.0)
        sock.connect((_daemon.RPC_TCP_HOST, _daemon.RPC_TCP_PORT))
        msg = json.dumps({'method': method, **kwargs}) + '\n'
        sock.sendall(msg.encode())
        data = b''
        while b'\n' not in data:
            chunk = sock.recv(4096)
            if not chunk:
                break
            data += chunk
        sock.close()
        return json.loads(data.split(b'\n')[0].decode())
    except Exception:
        return None


def _daemon_running() -> bool:
    r = _rpc('ping')
    return bool(r and r.get('pong'))


def _p2p_port(config: dict) -> int | None:
    try:
        from . import peer_exchange as _pe
        from ._common import SYSTEM_ROOT
        _exc = _pe.Exchange(Path(SYSTEM_ROOT) / 'exchange')
        cfg = _exc.load()
        return cfg.get('p2p_port') or cfg.get('port') or 7301
    except Exception:
        return None


def _prompt(config: dict) -> str:
    running = _daemon_running()
    state = 'running' if running else 'stopped'
    port = _p2p_port(config)
    port_str = f'·P2P:{port}' if port else ''
    try:
        from . import peer_exchange as _pe
        from ._common import SYSTEM_ROOT
        _exc = _pe.Exchange(Path(SYSTEM_ROOT) / 'exchange')
        cfg = _exc.load()
        nm = cfg.get('network_mode', 'intranet')
        roles = cfg.get('node_roles', [])
        role_str = '+'.join(r[:3] for r in roles) if roles else 'consumer'
        label = f'daemon:{state}·{nm}·{role_str}{port_str}'
    except Exception:
        label = f'daemon:{state}{port_str}'
    return f'\033[36murace\033[0m [\033[32m{label}\033[0m]> ' if _is_tty() else f'urace [{label}]> '


def _is_tty() -> bool:
    return hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()


# ── inline command runner ─────────────────────────────────────────────────────

def _run_cmd(argv: list[str], config: dict) -> int:
    from . import cli as _cli
    try:
        return _cli.main(argv) or 0
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 0
    except Exception as exc:
        print(f'error: {exc}')
        return 1


# ── slash command handlers ────────────────────────────────────────────────────

def _handle_slash(cmd: str, rest: str, config: dict) -> bool:
    """Returns True to continue, False to exit."""
    if cmd in ('/exit', '/quit'):
        print('bye.')
        return False

    if cmd == '/help':
        print('Slash commands:')
        for k, v in _SLASH_COMMANDS.items():
            print(f'  {k:<12} {v}')
        print('\nOr type any urace command (e.g. "status", "exchange network discover").')
        print('Freeform text is routed to the NL classifier.')
        return True

    if cmd == '/status':
        r = _rpc('status')
        if r:
            print(json.dumps(r, indent=2))
        else:
            print('daemon: not running')
        _run_cmd(['exchange', 'node', 'roles', '--json'], config)
        return True

    if cmd == '/stop':
        r = _rpc('stop')
        print(json.dumps(r) if r else 'daemon: not running')
        return True

    if cmd == '/pause':
        _run_cmd(['pause'], config)
        return True

    if cmd == '/resume':
        _run_cmd(['resume'], config)
        return True

    if cmd == '/events':
        parts = rest.strip().split()
        follow = '--follow' in parts or '-f' in parts
        nums = [p for p in parts if p.isdigit()]
        limit = int(nums[0]) if nums else 20
        if follow:
            import time
            print('Streaming events (Ctrl+C to stop)...')
            seen: set = set()
            try:
                while True:
                    r = _rpc('events', limit=limit)
                    if r and 'records' in r:
                        for rec in r['records']:
                            key = rec.get('id') or json.dumps(rec, sort_keys=True)
                            if key not in seen:
                                seen.add(key)
                                print(json.dumps(rec))
                    time.sleep(2)
            except KeyboardInterrupt:
                print()
        else:
            _run_cmd(['exchange', 'network-audit', 'list', '--limit', str(limit), '--json'], config)
        return True

    if cmd == '/config':
        parts = rest.strip().split(None, 1)
        if not parts:
            _run_cmd(['exchange', 'settings', 'show', '--json'], config)
        elif len(parts) == 1:
            key = parts[0]
            # dotted path → show filtered from full settings JSON
            r = _rpc('dispatch', argv=['exchange', 'settings', 'show', '--json'])
            if r and 'output' in r:
                try:
                    data = json.loads(r['output'])
                    for segment in key.split('.'):
                        data = data[segment]
                    print(json.dumps(data, indent=2) if isinstance(data, (dict, list)) else data)
                except (KeyError, TypeError):
                    print(f'key not found: {key}')
            else:
                _run_cmd(['exchange', 'settings', 'show', '--json'], config)
        else:
            key, value = parts
            # Support dotted keys like p2p.network_mode → --network-mode
            leaf = key.split('.')[-1]
            flag = f'--{leaf.replace("_", "-")}'
            _run_cmd(['exchange', 'settings', 'set', flag, value], config)
        return True

    if cmd == '/peers':
        _run_cmd(['exchange', 'network', 'peers', '--json'], config)
        return True

    if cmd == '/roles':
        _run_cmd(['exchange', 'node', 'roles', '--json'], config)
        return True

    print(f'unknown slash command: {cmd}  (try /help)')
    return True


# ── input classifier ──────────────────────────────────────────────────────────

_KNOWN_FIRST_WORDS = {
    'status', 'check', 'vitals', 'rules', 'auto', 'pause', 'resume', 'init',
    'exchange', 'compact', 'search', 'doctor', 'controls', 'trial', 'daemon',
    'start', 'stop', 'crypto', 'cost', 'export', 'report', 'schema', 'data',
    'product', 'features', 'rollback', 'security', 'config', 'resource',
    'trace', 'explain', 'watch', 'feedback', 'freeform-text',
}


def _dispatch_line(line: str, config: dict) -> bool:
    """Returns True to continue, False to exit."""
    line = line.strip()
    if not line:
        return True

    # Slash command
    if line.startswith('/'):
        parts = line.split(None, 1)
        cmd = parts[0].lower()
        rest = parts[1] if len(parts) > 1 else ''
        return _handle_slash(cmd, rest, config)

    # Direct urace command if first word is known
    argv = line.split()
    if argv[0] in _KNOWN_FIRST_WORDS:
        _run_cmd(argv, config)
        return True

    # Freeform text — route through classifier
    print(f'\033[2m→ routing: {line[:60]}{"..." if len(line) > 60 else ""}\033[0m')
    _run_cmd(['classify', line], config)
    return True


# ── readline setup ────────────────────────────────────────────────────────────

def _setup_readline(history_path: Path) -> None:
    try:
        import readline
        history_path.parent.mkdir(parents=True, exist_ok=True)
        if history_path.exists():
            readline.read_history_file(str(history_path))
        readline.set_history_length(500)
        import atexit
        atexit.register(readline.write_history_file, str(history_path))
        # Basic tab completion for slash commands and known words
        candidates = list(_SLASH_COMMANDS) + list(_KNOWN_FIRST_WORDS)
        def _complete(text, state):
            matches = [c for c in candidates if c.startswith(text)]
            return matches[state] if state < len(matches) else None
        readline.set_completer(_complete)
        readline.parse_and_bind('tab: complete')
    except ImportError:
        pass  # readline not available (Windows)


# ── main entry point ──────────────────────────────────────────────────────────

def run_shell(config: dict) -> int:
    from ._common import SYSTEM_ROOT
    history_path = Path(SYSTEM_ROOT).parent / '.urace' / 'shell_history'
    _setup_readline(history_path)

    if _is_tty():
        running = _daemon_running()
        status_line = '\033[32mrunning\033[0m' if running else '\033[33mstopped — run urace start\033[0m'
        print(f'URACE Shell  |  daemon: {status_line}')
        print('Type /help for commands, freeform text to query the executor, Ctrl+D to exit.\n')
        # Check if no goals set — prompt user to add one
        try:
            import json as _json
            _state_path = config.get('state_path', '')
            if _state_path:
                import os as _os
                if _os.path.exists(_state_path):
                    with open(_state_path) as _sf:
                        _st = _json.load(_sf)
                    if not _st.get('goals'):
                        print('No goals set. What would you like URACE to improve?')
                        print('(Type your goal in plain language below, or /exit to quit)\n')
                else:
                    print('No goals set. What would you like URACE to improve?')
                    print('(Type your goal in plain language below, or /exit to quit)\n')
        except Exception:
            pass  # never block shell open

    while True:
        try:
            prompt = _prompt(config) if _is_tty() else 'urace> '
            line = input(prompt)
        except (EOFError, KeyboardInterrupt):
            if _is_tty():
                print()
            break
        if not _dispatch_line(line, config):
            break

    return 0
