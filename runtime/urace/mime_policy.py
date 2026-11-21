"""MIME type policy for Asset Lineage Enforcement (ALE).

Controls which asset types are accepted for minting on this exchange node.
Default policy: quality_gate_only — only types that satisfy BOTH:
  1. ALE hard-protection (STRONG or MEDIUM Winnowing/fingerprinting coverage)
  2. APS quality-gate scorability (objective outcome delta computable by URACE)

Policy levels:
  quality_gate_only    — RECOMMENDED default; ALE hard-protected + APS quality-gate scorable
  hard_protected_only  — STRONG+MEDIUM ALE protection only (broader; includes PDF/images)
  all_allowed          — any MIME type; unprotectable types use SHA-256 exact only
  custom               — explicit allowlist in config p2p.allowed_asset_mime_types

Network-level guarantee: nodes on quality_gate_only only mint features that can
pass both the ALE duplicate-detection check AND the APS quality gate with an
objective score delta. Operators can loosen to hard_protected_only or all_allowed.

Tier system (Phase 1B):
  TIER_1_CODE_TYPES  — founding types: all three enforcement loops close independently
  NEVER_ALLOWED      — explicitly excluded regardless of policy (styling, markup, headers)
  TIER_2_DEPENDENT   — structured data valid as dependency, not standalone feature
  TIER_3_PACKAGE     — ZIP archives with member-type validation
"""

# Types that must NEVER be admitted to the p2p market regardless of policy.
# These are either styling (no behavioral test suite), markup (non-executable),
# or platform-specific headers with ambiguous provenance.
NEVER_ALLOWED = frozenset({
    'text/css',
    'text/x-scss', 'text/x-sass', 'text/x-less',
    'text/html', 'application/xhtml+xml',
    'text/x-csrc',          # bare .h headers — ambiguous, platform-specific
})

# Tier 1: founding types where all three enforcement loops close independently.
# - ALE: Winnowing-based duplicate detection
# - APS: objective test-suite outcome delta
# - Mint: unambiguous behavioral attribution
TIER_1_CODE_TYPES = frozenset({
    # Python
    'text/x-python', 'application/x-python',
    # JavaScript / TypeScript
    'text/javascript', 'text/typescript',
    'application/javascript', 'application/typescript',
    # Java / JVM
    'text/x-java-source',
    # Ruby
    'text/x-ruby', 'application/x-ruby',
    # Shell
    'text/x-sh', 'application/x-sh',
    # C / C++ (implementation files only — not headers)
    'text/x-c', 'text/x-c++src',
    # Go
    'text/x-go',
    # Rust
    'text/x-rust',
    # PHP
    'application/x-httpd-php',
})

# Tier 2: structured data valid as a dependency artifact but not standalone feature.
TIER_2_DEPENDENT_TYPES = frozenset({
    'application/json', 'application/x-ndjson', 'application/jsonl',
    'text/csv', 'application/xml', 'text/xml',
    'text/plain', 'text/markdown',
})

# Tier 3: package archives — admitted only when all member types pass Tier 1/2 checks.
TIER_3_PACKAGE_TYPES = frozenset({
    'application/zip', 'application/x-zip-compressed',
})

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
    'text/plain', 'text/markdown', 'text/x-python', 'text/x-java-source',
    'text/javascript', 'text/typescript', 'text/x-ruby', 'text/x-sh',
    'text/x-c', 'text/x-c++src', 'text/x-go', 'text/x-rust',
    'application/javascript', 'application/x-python', 'application/typescript',
    'application/x-sh', 'application/x-ruby', 'application/x-httpd-php',
})

WEAK_PROTECTED = frozenset({
    # SHA-256 exact match only — ALE detection is limited
    'application/octet-stream',
    'application/wasm',
    'application/x-tar', 'application/gzip', 'application/x-bzip2',
})

# STRONG + MEDIUM ALE protection set (used by hard_protected_only policy)
HARD_PROTECTED_ALLOWED = STRONG_PROTECTED | MEDIUM_PROTECTED

# Types with reliable APS quality-gate scoring: Tier 1 code + Tier 2 structured data.
# These are the only types where URACE can compute an objective outcome delta
# via test suite execution or schema-level comparison.
# Explicitly excludes NEVER_ALLOWED types (HTML, CSS, etc.).
QUALITY_GATE_VALIDATABLE = TIER_1_CODE_TYPES | TIER_2_DEPENDENT_TYPES

# Default allowed set: intersection of ALE hard-protection AND APS scorability.
# Images, PDFs, Office docs, and ZIP bundles are excluded because they have no
# reliable APS outcome delta in the current URACE runtime.
DEFAULT_ALLOWED = QUALITY_GATE_VALIDATABLE & HARD_PROTECTED_ALLOWED

PROTECTION_LEVEL = {}
for _t in STRONG_PROTECTED:
    PROTECTION_LEVEL[_t] = 'strong'
for _t in MEDIUM_PROTECTED:
    PROTECTION_LEVEL[_t] = 'medium'
for _t in WEAK_PROTECTED:
    PROTECTION_LEVEL[_t] = 'weak'


# ── Network-level enforcement ─────────────────────────────────────────────────
# TEMPORARY: relaxable by updating NETWORK_MIME_POLICY alone.
# Protocol-layer gates (receive, mint, replicate) always use is_network_allowed(),
# which applies NETWORK_MIME_POLICY unconditionally — user config has no effect.
# To expand allowed types: change NETWORK_MIME_POLICY here; all gates pick it up.
NETWORK_MIME_POLICY: str = 'quality_gate_only'


def is_network_allowed(content_type: str) -> tuple[bool, str]:
    """Protocol-level MIME gate — network-enforced, ignores per-node user config.

    Used by receive(), mint, and replication paths. To relax: update NETWORK_MIME_POLICY.
    """
    return is_allowed(content_type, {'p2p': {'mime_policy': NETWORK_MIME_POLICY}})


def get_policy(config: dict) -> str:
    """Return mime_policy from config.

    Valid values: 'quality_gate_only' | 'hard_protected_only' | 'all_allowed' | 'custom'
    Default: 'quality_gate_only'
    """
    return config.get('p2p', {}).get('mime_policy', 'quality_gate_only')


def get_custom_allowlist(config: dict) -> list[str]:
    return config.get('p2p', {}).get('allowed_asset_mime_types', [])


def protection_level(content_type: str) -> str:
    """Return 'strong', 'medium', 'weak', 'never', or 'unknown' for a MIME type."""
    ct = (content_type or '').lower().split(';')[0].strip()
    if ct in NEVER_ALLOWED:
        return 'never'
    if ct in PROTECTION_LEVEL:
        return PROTECTION_LEVEL[ct]
    if ct.startswith('image/'):
        return 'strong'
    if ct.startswith('text/') and ct in TIER_1_CODE_TYPES:
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
        for pattern in allowlist:
            p = pattern.lower().strip()
            if p.endswith('/*'):
                if ct.startswith(p[:-1]):
                    return True, f'policy=custom allowlist match: {p}'
            elif ct == p:
                return True, f'policy=custom allowlist match: {p}'
        return False, f'policy=custom: {ct!r} not in allowed_asset_mime_types'

    if policy == 'hard_protected_only':
        if ct in NEVER_ALLOWED:
            return False, f'policy=hard_protected_only: {ct!r} is in NEVER_ALLOWED (styling/markup not admitted)'
        lvl = protection_level(ct)
        if lvl in ('strong', 'medium'):
            return True, f'policy=hard_protected_only level={lvl}'
        if lvl == 'weak':
            return False, f'policy=hard_protected_only: {ct!r} has weak ALE protection. Set p2p.mime_policy=all_allowed to permit.'
        return False, f'policy=hard_protected_only: {ct!r} has no ALE fingerprinting. Set p2p.mime_policy=all_allowed or use p2p.allowed_asset_mime_types.'

    # quality_gate_only (default): ALE hard-protected AND APS quality-gate scorable
    if ct in NEVER_ALLOWED:
        return False, f'policy=quality_gate_only: {ct!r} is in NEVER_ALLOWED (styling/markup/headers not admitted to p2p)'
    if ct in DEFAULT_ALLOWED:
        return True, 'policy=quality_gate_only'
    # Tier 1 code types not already in DEFAULT_ALLOWED (e.g. text/x-go, text/x-rust):
    # ALE coverage via Winnowing; APS scores them as code — all three loops close.
    if ct in TIER_1_CODE_TYPES and protection_level(ct) in ('strong', 'medium'):
        return True, f'policy=quality_gate_only tier-1 code type (Winnowing+APS): {ct}'
    # Explain what policy to relax to
    lvl = protection_level(ct)
    if lvl in ('strong', 'medium'):
        return False, (
            f'policy=quality_gate_only: {ct!r} has ALE protection but cannot be reliably '
            f'scored by the APS quality gate (no objective outcome delta). '
            f'Set p2p.mime_policy=hard_protected_only to allow ALE-protected types.'
        )
    return False, (
        f'policy=quality_gate_only: {ct!r} cannot be reliably scored by the APS quality gate '
        f'and has no ALE hard-protection. Set p2p.mime_policy=hard_protected_only or '
        f'p2p.mime_policy=all_allowed to permit.'
    )
