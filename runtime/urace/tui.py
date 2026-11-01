"""k9s-style TUI dashboard for URACE — invoked by bare `urace` with no arguments."""
from __future__ import annotations
import curses
import json
import sys
import time
from pathlib import Path
from typing import Any

REFRESH_INTERVAL = 5   # seconds between auto-refresh
MAX_EVENTS = 200       # executor_calls kept for display

# ── data model ────────────────────────────────────────────────────────────────

class DashboardData:
    __slots__ = ('lifecycle', 'product', 'score', 'improvement_status',
                 'events', 'hints', 'error',
                 'active_objective', 'recent_completions', 'pending_count',
                 'executor_available', 'state_version')

    def __init__(self) -> None:
        self.lifecycle: str = 'UNKNOWN'
        self.product: str = ''
        self.score: float | None = None
        self.improvement_status: str = 'none'
        self.events: list[dict[str, str]] = []
        self.hints: list[dict[str, str]] = []
        self.error: str | None = None
        self.active_objective: str = ''
        self.recent_completions: list[str] = []
        self.pending_count: int = 0
        self.executor_available: bool | None = None
        self.state_version: int = 0


def collect(config: dict[str, Any], root: Path) -> DashboardData:
    """Build a DashboardData snapshot. Never raises."""
    d = DashboardData()
    try:
        from ._common import load_state_for_read
        from . import preflight as _pf

        state = load_state_for_read(config)
        if state is None:
            d.error = 'no state — run: urace init'
            return d

        d.lifecycle = state.get('lifecycle_state', 'UNKNOWN')
        d.product = config.get('product', '')
        d.state_version = state.get('state_version', 0)
        d.executor_available = state.get('executor_state', {}).get('available')

        # Active objective and recent completions — always available, no vitals call
        cur = state.get('current_objective')
        if cur:
            # current_objective may be an id — look up the title
            objs = state.get('objectives', [])
            matched = next((o for o in objs if o.get('id') == cur), None)
            d.active_objective = (matched.get('title') or cur) if matched else str(cur)
        d.recent_completions = [
            o.get('title', o.get('id', ''))
            for o in reversed(state.get('objectives', []))
            if o.get('status') == 'completed'
        ][:3]
        d.pending_count = sum(
            1 for o in state.get('objectives', [])
            if o.get('status') in {'planned', 'policy_blocked', 'deferred_budget', 'needs_reassessment'}
        )

        try:
            from .inspection import vitals_snapshot
            vitals = vitals_snapshot(config, state)
            d.score = vitals['system_scorecard']['overall_diagnostic_score']
        except Exception:
            pass

        trial = root / 'trial'
        if (trial / 'runtime-deployment-pending.json').exists():
            d.improvement_status = 'PENDING_DEPLOY'
        else:
            cycle_file = trial / 'runtime-cycle-latest.json'
            if cycle_file.exists():
                try:
                    stage = json.loads(cycle_file.read_text(encoding='utf-8')).get('stage', '')
                    d.improvement_status = stage or 'none'
                except Exception:
                    pass

        calls = state.get('executor_state', {}).get('executor_calls', [])
        for c in reversed(calls[-MAX_EVENTS:]):
            at = (c.get('at') or '')[:19].replace('T', ' ')
            kind = (c.get('stage') or 'EXECUTOR_CALL').upper()
            detail = c.get('reason') or c.get('outcome') or ''
            d.events.append({'time': at, 'kind': kind, 'detail': detail,
                             'status': c.get('outcome', '')})

        d.hints = _pf.hints(config, root)
    except Exception as exc:
        d.error = str(exc)
    return d


def format_score(score: float | None) -> str:
    return 'n/a' if score is None else f'{score:.2f}'


def _truncate(s: str, width: int) -> str:
    if width <= 0:
        return ''
    return s[:width - 1] + '…' if len(s) > width else s


# ── input routing ─────────────────────────────────────────────────────────────

_SLASH_MAP: dict[str, list[str]] = {
    '/help':   ['help'],
    '/check':  ['check'],
    '/status': ['status'],
    '/vitals': ['vitals'],
    '/auto':   ['auto', '--cycles', '1'],
    '/pause':  ['pause'],
    '/resume': ['resume'],
    '/plan':   ['plan'],
    '/goals':  ['goal', 'list'],
    '/inbox':  ['inbox', 'list'],
}

_DIRECT_PREFIXES = (
    'goal ', 'context ', 'source ', 'metric ', 'vital ', 'inbox ',
    'executor ', 'policy ', 'rules ', 'pause', 'resume', 'check',
    'status', 'vitals', 'plan', 'help', 'why ', 'update ', 'auto ',
)


def route_input(text: str) -> tuple[list[str] | None, str]:
    """Return (argv, display_label).  argv=None means no-op."""
    text = text.strip()
    if not text:
        return None, ''
    if text.startswith('/'):
        cmd, _, rest = text.partition(' ')
        if cmd in _SLASH_MAP:
            argv = _SLASH_MAP[cmd] + ([rest] if rest.strip() else [])
            return argv, f'running: {cmd}'
        # bare /command → strip slash and parse normally
        argv = text.lstrip('/').split()
        return argv, f'running: {" ".join(argv)}'
    if any(text.startswith(p) for p in _DIRECT_PREFIXES):
        return text.split(), f'running: {text}'
    # NLP fallthrough → classify
    return ['classify', text], f'classifying: {text!r}'


# ── rendering ─────────────────────────────────────────────────────────────────

_C_TITLE  = 1  # white on blue
_C_HEADER = 2  # cyan
_C_OK     = 3  # green
_C_WARN   = 4  # yellow
_C_ERR    = 5  # red


def _init_colors() -> None:
    if not curses.has_colors():
        return
    curses.start_color()
    try:
        curses.use_default_colors()
        bg = -1
    except Exception:
        bg = curses.COLOR_BLACK
    curses.init_pair(_C_TITLE,  curses.COLOR_WHITE,  curses.COLOR_BLUE)
    curses.init_pair(_C_HEADER, curses.COLOR_CYAN,   bg)
    curses.init_pair(_C_OK,     curses.COLOR_GREEN,  bg)
    curses.init_pair(_C_WARN,   curses.COLOR_YELLOW, bg)
    curses.init_pair(_C_ERR,    curses.COLOR_RED,    bg)


def _safe_addstr(stdscr, y: int, x: int, s: str, attr: int = 0,
                 rows: int = 0, cols: int = 0) -> None:
    if y < 0 or y >= rows or x < 0 or x >= cols:
        return
    s = s[:max(0, cols - x)]
    if not s:
        return
    try:
        stdscr.addstr(y, x, s, attr)
    except curses.error:
        pass


def _draw(stdscr, data: DashboardData, version: str,
          input_buf: str, status_msg: str) -> None:
    stdscr.erase()
    rows, cols = stdscr.getmaxyx()
    if rows < 6 or cols < 20:
        _safe_addstr(stdscr, 0, 0, 'terminal too small', 0, rows, cols)
        stdscr.refresh()
        return

    def put(y, x, s, attr=0):
        _safe_addstr(stdscr, y, x, s, attr, rows, cols)

    cp = curses.color_pair

    # ── row 0: title bar ──
    lifecycle_tag = f' lifecycle: {data.lifecycle} '
    left = f' URACE  {version}  {data.product} '
    bar = left.ljust(cols)
    put(0, 0, bar, cp(_C_TITLE) | curses.A_BOLD)
    lc_x = max(len(left), cols - len(lifecycle_tag))
    put(0, lc_x, lifecycle_tag[:cols - lc_x], cp(_C_TITLE) | curses.A_BOLD)

    # ── row 1: active objective + executor status ──
    exec_str = ('✓' if data.executor_available else '✗') if data.executor_available is not None else '?'
    exec_attr = cp(_C_OK) if data.executor_available else cp(_C_WARN)
    active = _truncate(data.active_objective or 'idle', max(1, cols - 40))
    put(1, 2, f'active: {active}')
    put(1, cols - 28, f'exec:{exec_str} pending:{data.pending_count} v{data.state_version}', exec_attr)
    if data.error:
        put(1, 2, _truncate(f'! {data.error}', cols - 4), cp(_C_ERR))

    # ── row 2: score / improvement (compact) ──
    score_str = format_score(data.score)
    imp = data.improvement_status
    imp_attr = cp(_C_WARN) if imp in ('PENDING_DEPLOY', 'AWAITING_APPROVAL') else 0
    completions = '  '.join(f'✓{t[:20]}' for t in data.recent_completions)
    put(2, 2, f'score:{score_str}  improve:{imp}  {completions}', imp_attr if imp_attr else 0)

    # ── row 3: events header ──
    put(3, 0, '─' * cols, cp(_C_HEADER))
    put(3, 2, ' recent events ', cp(_C_HEADER) | curses.A_BOLD)

    # ── events (rows 4 .. rows-hints_rows-3) ──
    hints_rows = len(data.hints)
    input_y   = rows - 2
    status_y  = rows - 1
    hints_y   = input_y - hints_rows - 1  # -1 for divider
    event_area = max(0, hints_y - 4)

    for i, ev in enumerate(data.events[:event_area]):
        y = 4 + i
        ts   = (ev['time'][-8:] if ev['time'] else '        ').ljust(8)
        kind = ev['kind'][:18].ljust(18)
        detail = _truncate(ev['detail'], cols - 32)
        status = ev.get('status', '')
        attr = (cp(_C_OK) if status == 'accepted'
                else cp(_C_ERR) if 'fail' in status
                else 0)
        put(y, 2, f'{ts}  {kind}  {detail}', attr)

    # ── hints divider ──
    div_y = hints_y
    if div_y < rows - 2:
        put(div_y, 0, '─' * cols, cp(_C_HEADER))
        hdr_label = ' gates & hints ' if data.hints else ' no active gates or hints '
        put(div_y, 2, hdr_label, cp(_C_HEADER))
        for i, h in enumerate(data.hints):
            hy = div_y + 1 + i
            if hy >= input_y:
                break
            msg = _truncate(f"[{h['level']}] {h['message']}  →  {h['action']}", cols - 4)
            put(hy, 2, msg, cp(_C_WARN))

    # ── input line ──
    put(input_y, 0, '─' * cols, cp(_C_HEADER))
    prompt = '> '
    put(input_y, 0, prompt + _truncate(input_buf, cols - 3), curses.A_BOLD)
    cx = min(len(prompt) + len(input_buf), cols - 1)
    try:
        stdscr.move(input_y, cx)
    except curses.error:
        pass

    # ── status bar ──
    hint_text = status_msg or 'q quit   tab refresh   /help for commands'
    put(status_y, 0, hint_text.ljust(cols)[:cols], cp(_C_TITLE))

    stdscr.refresh()


# ── main loop ─────────────────────────────────────────────────────────────────

def _run_loop(stdscr, config: dict[str, Any], root: Path) -> int:
    from .version import RUNTIME_VERSION

    curses.curs_set(1)
    stdscr.nodelay(True)
    stdscr.timeout(200)
    _init_colors()

    data        = collect(config, root)
    input_buf   = ''
    status_msg  = ''
    last_refresh = time.monotonic()

    _draw(stdscr, data, RUNTIME_VERSION, input_buf, status_msg)

    while True:
        now_m = time.monotonic()
        if now_m - last_refresh >= REFRESH_INTERVAL:
            data = collect(config, root)
            last_refresh = now_m
            status_msg = ''

        _draw(stdscr, data, RUNTIME_VERSION, input_buf, status_msg)

        try:
            ch = stdscr.getch()
        except curses.error:
            ch = -1

        if ch == -1:
            continue

        if ch == ord('q') and not input_buf:
            return 0

        if ch == ord('\t'):
            data = collect(config, root)
            last_refresh = time.monotonic()
            status_msg = 'refreshed'
            continue

        if ch in (curses.KEY_BACKSPACE, 127, 8):
            input_buf = input_buf[:-1]
            continue

        if ch in (curses.KEY_ENTER, ord('\n'), ord('\r')):
            argv, label = route_input(input_buf)
            input_buf = ''
            if argv is not None:
                status_msg = label
                _draw(stdscr, data, RUNTIME_VERSION, input_buf, status_msg)
                # Leave curses, run command, re-enter
                curses.def_prog_mode()
                stdscr.clear()
                curses.endwin()
                sys.stdout.write('\n')
                sys.stdout.flush()
                exit_code = _dispatch(argv)
                if exit_code not in (0, None):
                    input(f'\nCommand exited {exit_code}. Press Enter to return…')
                else:
                    time.sleep(0.4)
                curses.reset_prog_mode()
                stdscr.refresh()
                data = collect(config, root)
                last_refresh = time.monotonic()
                status_msg = f'done ({label})'
            continue

        if 32 <= ch < 127:
            input_buf += chr(ch)


def _dispatch(argv: list[str]) -> int:
    """Run a CLI command from within the TUI loop."""
    from . import cli
    try:
        result = cli.main(argv)
        return result if result is not None else 0
    except SystemExit as se:
        return se.code if isinstance(se.code, int) else 0
    except Exception as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 1


def launch(config: dict[str, Any], root: Path) -> int:
    """Enter the TUI dashboard. Returns an exit code."""
    if not sys.stdout.isatty():
        # Non-interactive context — fall through to help
        return _no_tty_fallback()
    try:
        return curses.wrapper(_run_loop, config, root)
    except curses.error as exc:
        print(f'TUI unavailable ({exc}); use `urace status` for a plain view.',
              file=sys.stderr)
        return 1


def _no_tty_fallback() -> int:
    """Print a compact status summary when stdout is not a TTY."""
    from ._common import load_config, load_state_for_read
    from ._common import SYSTEM_ROOT
    try:
        cfg = load_config()
        state = load_state_for_read(cfg)
        if state is None:
            print('urace: no state. Run: urace init')
            return 1
        lifecycle = state.get('lifecycle_state', 'UNKNOWN')
        product   = cfg.get('product', '')
        print(f'urace  product:{product}  lifecycle:{lifecycle}')
        return 0
    except Exception as exc:
        print(f'urace: {exc}')
        return 1
