import subprocess, threading, re, time

def _parse_cloudflare_url(line: str) -> str | None:
    m = re.search(r'https://[a-z0-9\-]+\.trycloudflare\.com', line)
    return m.group(0) if m else None

def _parse_localhost_run_url(line: str) -> str | None:
    m = re.search(r'https://[a-zA-Z0-9\-]+\.lhr\.life', line)
    if not m:
        m = re.search(r'https://[a-zA-Z0-9\-]+\.localhost\.run', line)
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
    def __init__(self, provider: str, local_port: int, timeout: float = 20.0):
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
                # localhost.run: zero install (SSH built-in everywhere), zero account — primary.
                # cloudflared: auto-installed by init --auto to ~/.urace/bin/, or system binary.
                import shutil
                from . import tunnel_install as _ti
                _cf = _ti.find_cloudflared()
                if shutil.which('ssh'):
                    self.provider = 'localhost.run'
                    self._start_localhost_run()
                elif _cf:
                    self.provider = 'cloudflare'
                    self._start_cloudflare()
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

    def _start_localhost_run(self):
        # localhost.run via SSH — no install needed
        self._proc = subprocess.Popen(
            ['ssh', '-o', 'StrictHostKeyChecking=no', '-o', 'UserKnownHostsFile=/dev/null',
             '-R', f'80:localhost:{self.local_port}', 'nokey@localhost.run'],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1
        )
        self._wait_for_url(_parse_localhost_run_url)

    def _wait_for_url(self, parser):
        deadline = time.time() + self.timeout
        for line in self._proc.stdout:
            url = parser(line)
            if url:
                self.url = url
                # drain output in background
                threading.Thread(target=self._proc.stdout.read, daemon=True).start()
                return
            if time.time() > deadline:
                break

    def __exit__(self, *_):
        if self._proc:
            try:
                self._proc.terminate()
                self._proc.wait(timeout=3)
            except Exception:
                pass
