"""Read Claude quota utilization from the latest preflight receipt."""
from pathlib import Path
import json

def claude_utilization(base) -> float | None:
    """Return Claude 7-day quota utilization (0.0–1.0), or None if unknown."""
    path = Path(base) / 'claude-preflight-latest.json'
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        events = data.get('receipt', {}).get('quota_events', [])
        for event in events:
            if event.get('rateLimitType') == 'seven_day':
                val = event.get('utilization')
                if val is not None:
                    return float(val)
        return None
    except (OSError, ValueError, KeyError, TypeError):
        return None

def is_high_pressure(base, threshold=0.85) -> bool:
    """Return True if Claude quota utilization exceeds threshold."""
    u = claude_utilization(base)
    return u is not None and u > threshold
