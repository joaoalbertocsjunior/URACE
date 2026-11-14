"""Locate an already-installed cloudflared binary. Never downloads or installs."""
import shutil, sys


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
