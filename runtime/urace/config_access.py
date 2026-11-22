"""Phase 7C — typed config section accessors.

Thin wrappers over the raw config dict that return typed views with
validated defaults.  Never mutate config — always return a copy.

Usage::

    from urace.config_access import logging_cfg, p2p_cfg, sources_cfg

    lvl = logging_cfg(config).level    # 'WARNING'
    interval = sources_cfg(config).auto_sync_interval_s  # 300
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ── Logging ───────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class LoggingConfig:
    level: str = 'WARNING'
    format: str = 'text'
    file: str = ''
    max_bytes: int = 10_485_760
    backup_count: int = 5
    audit_tier: str = 'full'
    m2m_stream: bool = False
    m2m_diagnostic: bool = False
    redact_executor_output: bool = True
    components: dict = field(default_factory=dict)


def logging_cfg(config: dict) -> LoggingConfig:
    raw: dict[str, Any] = config.get('logging', {}) if isinstance(config, dict) else {}
    return LoggingConfig(
        level=str(raw.get('level', 'WARNING')),
        format=str(raw.get('format', 'text')),
        file=str(raw.get('file', '') or ''),
        max_bytes=int(raw.get('max_bytes', 10_485_760)),
        backup_count=int(raw.get('backup_count', 5)),
        audit_tier=str(raw.get('audit_tier', 'full')),
        m2m_stream=bool(raw.get('m2m_stream', False)),
        m2m_diagnostic=bool(raw.get('m2m_diagnostic', False)),
        redact_executor_output=bool(raw.get('redact_executor_output', True)),
        components=dict(raw.get('components', {})),
    )


# ── P2P ──────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class P2PConfig:
    min_evidence_borrows: int = 5
    trial_escrow_pct: int = 10
    jitter_frac: float = 0.0
    earn_jitter_frac: float = 0.0
    consensus_floor_multiplier: float = 0.0


def p2p_cfg(config: dict) -> P2PConfig:
    raw: dict[str, Any] = config.get('p2p', {}) if isinstance(config, dict) else {}
    mint = raw.get('mint', {}) if isinstance(raw, dict) else {}
    pricing = raw.get('pricing', {}) if isinstance(raw, dict) else {}
    return P2PConfig(
        min_evidence_borrows=int(mint.get('min_evidence_borrows', 5)),
        trial_escrow_pct=int(mint.get('trial_escrow_pct', 10)),
        jitter_frac=float(pricing.get('jitter_frac', 0.0)),
        earn_jitter_frac=float(pricing.get('earn_jitter_frac', 0.0)),
        consensus_floor_multiplier=float(pricing.get('consensus_floor_multiplier', 0.0)),
    )


# ── Feature matching ──────────────────────────────────────────────────────────

@dataclass(frozen=True)
class FeatureMatchingConfig:
    layer1_strict: bool = True
    layer2_cap_weight: int = 60
    layer2_lang_weight: int = 30
    layer2_loc_weight: int = 10
    borrow_threshold: float = 0.5


def feature_matching_cfg(config: dict) -> FeatureMatchingConfig:
    raw: dict[str, Any] = config.get('feature_matching', {}) if isinstance(config, dict) else {}
    return FeatureMatchingConfig(
        layer1_strict=bool(raw.get('layer1_strict', True)),
        layer2_cap_weight=int(raw.get('layer2_cap_weight', 60)),
        layer2_lang_weight=int(raw.get('layer2_lang_weight', 30)),
        layer2_loc_weight=int(raw.get('layer2_loc_weight', 10)),
        borrow_threshold=float(raw.get('borrow_threshold', 0.5)),
    )


# ── Sources ───────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SourcesConfig:
    auto_sync_interval_s: int = 300


def sources_cfg(config: dict) -> SourcesConfig:
    raw: dict[str, Any] = config.get('sources', {}) if isinstance(config, dict) else {}
    return SourcesConfig(
        auto_sync_interval_s=int(raw.get('auto_sync_interval_s', 300)),
    )


# ── MIME policy ───────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class MimePolicyConfig:
    network_policy: str = 'quality_gate_only'


def mime_policy_cfg(config: dict) -> MimePolicyConfig:
    raw: dict[str, Any] = config.get('mime_policy', {}) if isinstance(config, dict) else {}
    return MimePolicyConfig(
        network_policy=str(raw.get('network_policy', 'quality_gate_only')),
    )
