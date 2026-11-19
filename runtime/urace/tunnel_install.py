"""Optional tunnel infrastructure — cloudflared binary locator.

Locates an already-installed cloudflared binary. Never downloads or installs.
This module is optional: it is only used when NAT traversal via Cloudflare
tunnels is configured. Nodes with a public IP or LAN-only setups do not need it.
Install cloudflared from https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/
"""
import shutil, sys, re, subprocess


def find_cloudflared() -> str | None:
    """Return path to cloudflared if already on the system, else None."""
    path = shutil.which('cloudflared')
    if path:
        return path
    # Check URACE-local bin in case user manually placed it there
    try:
        from ._common import SYSTEM_ROOT
        from pathlib import Path
        local = Path(SYSTEM_ROOT).parent / '.urace' / 'bin' / (
            'cloudflared.exe' if sys.platform == 'win32' else 'cloudflared'
        )
        if local.exists():
            return str(local)
    except Exception:
        pass
    return None


def setup_named_tunnel(peer_id: str) -> 'str | None':
    """Create or reuse a named cloudflared tunnel for a permanent URL.

    Returns the permanent cfargotunnel.com URL, or None if Cloudflare login
    is not completed or any step fails (graceful fallback).

    The tunnel name is derived from the first 12 chars of peer_id so the same
    node always reuses the same tunnel after a reconnect.
    """
    from pathlib import Path

    cert_path = Path.home() / '.cloudflared' / 'cert.pem'
    if not cert_path.exists():
        return None  # Not logged in — silent fallback

    binary = find_cloudflared()
    if not binary:
        return None

    tunnel_name = f'urace-{peer_id[:12]}'
    tunnel_id: 'str | None' = None

    # --- Check if tunnel already exists ---
    try:
        result = subprocess.run(
            [binary, 'tunnel', 'list', '--output', 'json'],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            import json as _json
            try:
                tunnels = _json.loads(result.stdout)
                for t in (tunnels if isinstance(tunnels, list) else []):
                    if t.get('name') == tunnel_name:
                        tunnel_id = t.get('id')
                        break
            except Exception as _e:
                import logging as _lg; _lg.getLogger(__name__).debug('cloudflared tunnel list parse failed: %s', _e)
    except Exception as _e:
        import logging as _lg; _lg.getLogger(__name__).debug('cloudflared tunnel list failed: %s', _e)

    # --- Create if not found ---
    if not tunnel_id:
        try:
            result = subprocess.run(
                [binary, 'tunnel', 'create', tunnel_name],
                capture_output=True, text=True, timeout=15,
            )
            combined = result.stdout + result.stderr
            # cloudflared prints: Created tunnel <name> with id <uuid>
            m = re.search(r'[Cc]reated tunnel\s+\S+\s+with id\s+([0-9a-f\-]{36})', combined)
            if m:
                tunnel_id = m.group(1)
            else:
                # Fallback: re-query list after create
                result2 = subprocess.run(
                    [binary, 'tunnel', 'list', '--output', 'json'],
                    capture_output=True, text=True, timeout=10,
                )
                if result2.returncode == 0:
                    import json as _json
                    try:
                        tunnels = _json.loads(result2.stdout)
                        for t in (tunnels if isinstance(tunnels, list) else []):
                            if t.get('name') == tunnel_name:
                                tunnel_id = t.get('id')
                                break
                    except Exception:
                        pass
        except Exception as _e:
            import logging as _lg; _lg.getLogger(__name__).debug('cloudflared tunnel create failed: %s', _e)
            return None

    if not tunnel_id:
        return None

    return f'https://{tunnel_id}.cfargotunnel.com'
