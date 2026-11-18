"""Optional tunnel infrastructure — Cloudflare/localhost.run NAT traversal.

This module is optional infrastructure for nodes behind NAT that cannot
accept direct inbound connections. It is not required for LAN or nodes
with a public IP. Install cloudflared (https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/)
to use Cloudflare tunnels; no extra Python dependencies are needed.
"""
import subprocess, threading, re, time, concurrent.futures

def _parse_cloudflare_url(line: str) -> str | None:
    m = re.search(r'https://[a-z0-9\-]+\.trycloudflare\.com', line)
    return m.group(0) if m else None

def _parse_cfargotunnel_url(line: str) -> str | None:
    m = re.search(r'https://[0-9a-f\-]{36}\.cfargotunnel\.com', line)
    return m.group(0) if m else None

def _parse_localhost_run_url(line: str) -> str | None:
    # Tunnel URLs are always *.lhr.life (e.g. 290d12c1b998a5.app.lhr.life) —
    # *.localhost.run subdomains appear in the welcome banner before the real URL.
    m = re.search(r'https://[a-zA-Z0-9\-\.]+\.lhr\.life', line)
    return m.group(0) if m else None

def _direct_inbound_reachable(port: int, timeout: float = 4.0) -> str | None:
    """Return public https URL if direct inbound works (direct IP/cone NAT with consistent port).
    Returns None if a tunnel is needed."""
    try:
        from . import nat_check as _nc
        cap = _nc.check_node_capability(timeout=timeout)
        if cap.get('nat_type') == 'direct' and cap.get('public_ip'):
            return f"https://{cap['public_ip']}:{port}"
        # cone NAT with UPnP — port already mapped
        if cap.get('nat_type') == 'cone' and cap.get('upnp_available'):
            return f"https://{cap['public_ip']}:{port}"
    except Exception:
        pass
    return None

class TunnelHandle:
    """Context manager that provides a public HTTPS URL for a local port.

    provider='auto': checks direct inbound first; only starts a tunnel when NAT
    blocks inbound. localhost.run is tried first (zero install, SSH-based, no
    account). cloudflared is used if the binary is present. No third-party service
    is contacted unless a tunnel is actually needed.
    """
    def __init__(self, provider: str, local_port: int, timeout: float = 45.0):
        self.provider = provider
        self.local_port = local_port
        self.timeout = timeout
        self.url: str | None = None
        self._proc: subprocess.Popen | None = None
        self._tunneled = False  # True when a tunnel process was started

    def __enter__(self):
        if self.provider == 'cloudflare':
            self._start_cloudflare()
        elif self.provider == 'localhost.run':
            self._start_localhost_run()
        elif self.provider == 'auto':
            # Try direct first — avoids unnecessary third-party connection
            direct = _direct_inbound_reachable(self.local_port)
            if direct:
                self.url = direct
                self.provider = 'direct'
            else:
                # Check for named cloudflared tunnel first (permanent URL, survives reconnects).
                # Timeout after 10s so slow cloudflared calls don't block startup.
                import shutil
                from . import tunnel_install as _ti
                _named_url: str | None = None
                _cf = _ti.find_cloudflared()
                if _cf:
                    try:
                        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as _ex:
                            _fut = _ex.submit(
                                _ti.setup_named_tunnel,
                                getattr(self, '_peer_id', '') or '',
                            )
                            try:
                                _named_url = _fut.result(timeout=10)
                            except concurrent.futures.TimeoutError:
                                _named_url = None
                    except Exception:
                        _named_url = None
                if _named_url:
                    self.provider = 'cloudflare-named'
                    self._start_cloudflare_named(_named_url)
                elif _cf:
                    self.provider = 'cloudflare'
                    self._start_cloudflare()
                elif shutil.which('ssh'):
                    self.provider = 'localhost.run'
                    self._start_localhost_run()
                # else: no tunnel available, url stays None
        return self

    def _start_cloudflare(self):
        from . import tunnel_install as _ti
        binary = _ti.find_cloudflared() or 'cloudflared'
        self._proc = subprocess.Popen(
            [binary, 'tunnel', '--url', f'http://localhost:{self.local_port}'],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1
        )
        self._wait_for_url(_parse_cloudflare_url)

    def _start_cloudflare_named(self, tunnel_name_or_url: str):
        """Start a named cloudflared tunnel (permanent cfargotunnel.com URL).

        tunnel_name_or_url may be either a tunnel name (e.g. 'urace-abc123') or
        the permanent URL returned by setup_named_tunnel (the tunnel name/ID is
        extracted from it).  The permanent URL is set directly on self.url —
        cloudflared named tunnels expose a fixed URL that does not change between
        restarts, so we do not need to parse it from process output.
        """
        from . import tunnel_install as _ti
        binary = _ti.find_cloudflared() or 'cloudflared'
        # Derive the tunnel name: if we were passed the full URL, extract the ID/name.
        import re as _re
        m = _re.search(r'https://([^.]+)\.cfargotunnel\.com', tunnel_name_or_url)
        if m:
            name = m.group(1)
            self.url = tunnel_name_or_url
        else:
            name = tunnel_name_or_url
            # URL will be set after process starts and emits the cfargotunnel line.
        self._proc = subprocess.Popen(
            [binary, 'tunnel', 'run', name, '--url', f'http://localhost:{self.local_port}'],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1
        )
        if not self.url:
            self._wait_for_url(_parse_cfargotunnel_url)

    def _start_localhost_run(self):
        # localhost.run via SSH — no install needed.
        # stdbuf -oL forces SSH stdout to be line-buffered when piped; without it
        # SSH buffers output until the internal stdio buffer fills (~8 KB), so the
        # tunnel URL never arrives during _wait_for_url's timeout window.
        # ServerAliveInterval/CountMax: SSH sends keepalive probes every 30s;
        # if localhost.run drops the mapping without closing TCP, SSH exits after
        # 3 missed probes (~90s), triggering the exchange_cli reconnect loop.
        import shutil as _sh
        _cmd = (['stdbuf', '-oL'] if _sh.which('stdbuf') else []) + [
            'ssh',
            '-o', 'StrictHostKeyChecking=no',
            '-o', 'UserKnownHostsFile=/dev/null',
            '-o', 'ServerAliveInterval=30',
            '-o', 'ServerAliveCountMax=3',
            '-R', f'80:localhost:{self.local_port}', 'nokey@localhost.run',
        ]
        self._proc = subprocess.Popen(
            _cmd,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1
        )
        self._wait_for_url(_parse_localhost_run_url)

    def _wait_for_url(self, parser):
        # Read in a daemon thread so self.timeout is a hard wall-clock deadline
        # even when the SSH/cloudflared process is slow to produce its first line.
        result: list[str | None] = [None]
        def _reader():
            try:
                for line in self._proc.stdout:
                    url = parser(line)
                    if url:
                        result[0] = url
                        threading.Thread(target=self._proc.stdout.read, daemon=True).start()
                        return
            except Exception:
                pass
        t = threading.Thread(target=_reader, daemon=True)
        t.start()
        t.join(timeout=self.timeout)
        if result[0]:
            self.url = result[0]

    def __exit__(self, *_):
        if self._proc:
            try:
                self._proc.terminate()
                self._proc.wait(timeout=3)
            except Exception:
                pass


class DualTunnelHandle:
    """Runs cloudflared + localhost.run in parallel. Both URLs registered.

    Either tunnel serving = node reachable. Reconnects failed tunnel
    independently (caller monitors both procs via the ``_proc`` property or
    ``_all_procs`` list).  Primary URL is cloudflare-named / cloudflare if
    available, otherwise lhr.life.
    """

    def __init__(self, local_port: int, timeout: float = 45.0):
        self.local_port = local_port
        self.timeout = timeout
        self._cf_handle: TunnelHandle | None = None
        self._lhr_handle: TunnelHandle | None = None
        self._urls: list[str] = []

    def __enter__(self) -> 'DualTunnelHandle':
        import shutil
        from . import tunnel_install as _ti

        self._cf_handle = None
        self._lhr_handle = None
        self._urls = []

        def _start_cf():
            _cf_bin = _ti.find_cloudflared()
            if not _cf_bin:
                return
            # Use named tunnel (permanent URL) when cert.pem exists, else quick tunnel
            from pathlib import Path as _P
            _has_cert = (_P.home() / '.cloudflared' / 'cert.pem').exists()
            _peer_id = getattr(self, '_peer_id', '') or ''
            if _has_cert and _peer_id:
                _named_url = None
                try:
                    import concurrent.futures as _cf2
                    with _cf2.ThreadPoolExecutor(max_workers=1) as _ex:
                        _fut = _ex.submit(_ti.setup_named_tunnel, _peer_id)
                        try:
                            _named_url = _fut.result(timeout=15)
                        except _cf2.TimeoutError:
                            _named_url = None
                except Exception:
                    _named_url = None
                if _named_url:
                    h = TunnelHandle('cloudflare-named', self.local_port, timeout=self.timeout)
                    h._peer_id = _peer_id
                    try:
                        h._start_cloudflare_named(_named_url)
                        if h.url:
                            self._cf_handle = h
                            return
                    except Exception:
                        pass
            # Fallback: quick tunnel
            h = TunnelHandle('cloudflare', self.local_port, timeout=self.timeout)
            try:
                h.__enter__()
                if h.url:
                    self._cf_handle = h
            except Exception:
                pass

        def _start_lhr():
            if not shutil.which('ssh'):
                return
            h = TunnelHandle('localhost.run', self.local_port, timeout=self.timeout)
            try:
                h.__enter__()
                if h.url:
                    self._lhr_handle = h
            except Exception:
                pass

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
            f1 = ex.submit(_start_cf)
            f2 = ex.submit(_start_lhr)
            # Wait up to timeout for both; individual handles carry their own timeout.
            concurrent.futures.wait([f1, f2], timeout=self.timeout + 2)

        # Build URL list: cloudflare-based URLs first (permanent / more reliable).
        seen: set[str] = set()
        for h in [self._cf_handle, self._lhr_handle]:
            if h and h.url and h.url not in seen:
                self._urls.append(h.url)
                seen.add(h.url)

        return self

    def __exit__(self, *_):
        for h in [self._cf_handle, self._lhr_handle]:
            if h:
                try:
                    h.__exit__()
                except Exception:
                    pass

    @property
    def url(self) -> 'str | None':
        """Primary URL: cloudflare if available, else lhr.life."""
        return self._urls[0] if self._urls else None

    @property
    def urls(self) -> list:
        """All live URLs."""
        return list(self._urls)

    @property
    def _proc(self):
        """Primary tunnel proc (for watchdog compat)."""
        if self._cf_handle and self._cf_handle._proc:
            return self._cf_handle._proc
        if self._lhr_handle and self._lhr_handle._proc:
            return self._lhr_handle._proc
        return None

    @property
    def _all_procs(self) -> list:
        """All running tunnel procs (for dual-watchdog monitoring)."""
        procs = []
        for h in [self._cf_handle, self._lhr_handle]:
            if h and h._proc:
                procs.append(h._proc)
        return procs
