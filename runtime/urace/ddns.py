"""Optional DDNS infrastructure — DuckDNS update API, public IP detection.

This module is optional infrastructure for nodes that want to maintain a stable
hostname via DuckDNS (https://www.duckdns.org/). It is not required for nodes
with a static IP or nodes using Cloudflare tunnels. No extra Python packages
are needed — only standard-library urllib is used.
"""
from __future__ import annotations
import threading
import urllib.request
import urllib.parse


_DUCKDNS_UPDATE_URL = "https://www.duckdns.org/update"
_PUBLIC_IP_SOURCES = [
    "https://api.ipify.org",
    "https://ifconfig.me/ip",
    "https://checkip.amazonaws.com",
]


def get_current_public_ip(timeout: float = 5.0) -> str | None:
    """Try multiple HTTP sources; return first valid IPv4 string or None."""
    for url in _PUBLIC_IP_SOURCES:
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                ip = resp.read(64).decode().strip()
                if ip and all(c in "0123456789." for c in ip) and ip.count(".") == 3:
                    return ip
        except Exception as _e:
            import logging as _lg; _lg.getLogger(__name__).debug('public IP source %s failed: %s', url, _e)
            continue
    return None


def update_duckdns(token: str, domain: str, ip: str, timeout: float = 10.0) -> bool:
    """POST IP update to DuckDNS.  Returns True on 'OK' response."""
    params = urllib.parse.urlencode({"domains": domain, "token": token, "ip": ip})
    url = f"{_DUCKDNS_UPDATE_URL}?{params}"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            body = resp.read(32).decode().strip().upper()
            return body.startswith("OK")
    except Exception as _e:
        import logging as _lg; _lg.getLogger(__name__).warning('DuckDNS update failed: %s', _e)
        return False


def start_ddns_watcher(
    token: str,
    domain: str,
    interval: int = 300,
    *,
    stop_event: threading.Event | None = None,
) -> threading.Thread:
    """Start a daemon thread that updates DuckDNS every *interval* seconds when IP changes.

    Returns the Thread object (already started).
    stop_event: optional threading.Event; set it to request clean shutdown.
    """
    _stop = stop_event or threading.Event()

    def _run() -> None:
        last_ip: str | None = None
        while not _stop.is_set():
            ip = get_current_public_ip()
            if ip and ip != last_ip:
                ok = update_duckdns(token, domain, ip)
                if ok:
                    last_ip = ip
            _stop.wait(interval)

    t = threading.Thread(target=_run, daemon=True, name="ddns-watcher")
    t.start()
    return t
