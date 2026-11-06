"""MIME type policy for Asset Lineage Enforcement (ALE).

Controls which asset types are accepted for minting on this exchange node.
Default policy: hard_protected_only — only types with strong or medium ALE fingerprinting.

Policy levels:
  hard_protected_only  — only STRONG+MEDIUM protected types (default, recommended for network trust)
  all_allowed          — any MIME type accepted; unprotectable types use SHA-256 exact only
  custom               — explicit allowlist in config p2p.allowed_asset_mime_types

This is a network-level guarantee: nodes running hard_protected_only signal stronger provenance
trust to peers. Operators can loosen the policy but cannot strengthen peers' policies.
"""

STRONG_PROTECTED = frozenset({
    # Images — dHash perceptual fingerprint
    'image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/bmp',
    'image/tiff', 'image/svg+xml', 'image/avif', 'image/heic',
    # Structured data — statistical fingerprint
    'text/csv', 'application/json', 'application/x-ndjson', 'application/jsonl',
    # XML — schema + Winnowing
    'application/xml', 'text/xml',
    # ZIP bundles — member-level decomposition
    'application/zip', 'application/x-zip-compressed',
})

MEDIUM_PROTECTED = frozenset({
    # PDF — text extraction + Winnowing
    'application/pdf',
    # Office Open XML — text extraction + Winnowing/stats
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'application/msword',
    'application/vnd.ms-excel',
    'application/vnd.ms-powerpoint',
    # Text and code — Winnowing
    'text/plain', 'text/html', 'text/markdown', 'text/x-python', 'text/x-java-source',
    'text/javascript', 'text/typescript', 'text/x-ruby', 'text/x-sh',
    'application/javascript', 'application/x-python', 'application/typescript',
    'application/x-sh', 'application/x-ruby', 'application/x-httpd-php',
})

WEAK_PROTECTED = frozenset({
    # SHA-256 exact match only — ALE detection is limited
    'application/octet-stream',
    'application/wasm',
    'application/x-tar', 'application/gzip', 'application/x-bzip2',
})

# Default hard_protected_only allows STRONG + MEDIUM
HARD_PROTECTED_ALLOWED = STRONG_PROTECTED | MEDIUM_PROTECTED

PROTECTION_LEVEL = {}
for _t in STRONG_PROTECTED:
    PROTECTION_LEVEL[_t] = 'strong'
for _t in MEDIUM_PROTECTED:
    PROTECTION_LEVEL[_t] = 'medium'
for _t in WEAK_PROTECTED:
    PROTECTION_LEVEL[_t] = 'weak'


def get_policy(config: dict) -> str:
    """Return mime_policy from config: 'hard_protected_only' | 'all_allowed' | 'custom'."""
    return config.get('p2p', {}).get('mime_policy', 'hard_protected_only')


def get_custom_allowlist(config: dict) -> list[str]:
    return config.get('p2p', {}).get('allowed_asset_mime_types', [])


def protection_level(content_type: str) -> str:
    """Return 'strong', 'medium', 'weak', or 'unknown' for a MIME type."""
    ct = (content_type or '').lower().split(';')[0].strip()
    # Exact lookup first (covers text/csv → strong, etc.)
    if ct in PROTECTION_LEVEL:
        return PROTECTION_LEVEL[ct]
    # wildcard prefix match for image/*
    if ct.startswith('image/'):
        return 'strong'
    if ct.startswith('text/'):
        return 'medium'
    if ct.startswith('video/') or ct.startswith('audio/'):
        return 'weak'
    return 'unknown'


def is_allowed(content_type: str, config: dict) -> tuple[bool, str]:
    """Check if a MIME type is allowed under current policy.

    Returns (allowed: bool, reason: str).
    """
    ct = (content_type or '').lower().split(';')[0].strip()
    policy = get_policy(config)

    if policy == 'all_allowed':
        return True, 'policy=all_allowed'

    if policy == 'custom':
        allowlist = get_custom_allowlist(config)
        if not allowlist:
            return False, 'policy=custom but allowed_asset_mime_types is empty'
        # Support wildcard suffix: 'image/*' matches 'image/jpeg'
        for pattern in allowlist:
            p = pattern.lower().strip()
            if p.endswith('/*'):
                if ct.startswith(p[:-1]):
                    return True, f'policy=custom allowlist match: {p}'
            elif ct == p:
                return True, f'policy=custom allowlist match: {p}'
        return False, f'policy=custom: {ct!r} not in allowed_asset_mime_types'

    # hard_protected_only (default)
    lvl = protection_level(ct)
    if lvl in ('strong', 'medium'):
        return True, f'policy=hard_protected_only level={lvl}'
    if lvl == 'weak':
        return False, f'policy=hard_protected_only: {ct!r} has weak ALE protection (SHA-256 exact only). Set p2p.mime_policy=all_allowed to permit weak types.'
    # unknown
    return False, f'policy=hard_protected_only: {ct!r} is an unknown MIME type with no ALE fingerprinting. Set p2p.mime_policy=all_allowed or add to p2p.allowed_asset_mime_types.'
