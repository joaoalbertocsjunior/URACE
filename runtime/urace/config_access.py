"""Typed config section accessors backed by Pydantic models.

Thin wrappers over the raw config dict that return validated, typed views.
Pydantic (already a hard dep) handles coercion, defaults, and validation.
Never mutates config — always returns a new model instance.

Usage::

    from urace.config_access import logging_cfg, p2p_cfg, sources_cfg

    lvl = logging_cfg(config).level    # 'WARNING'
    interval = sources_cfg(config).auto_sync_interval_s  # 300
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ── Logging ───────────────────────────────────────────────────────────────────

class LoggingConfig(BaseModel, frozen=True):
    level: str = 'WARNING'
    format: str = 'text'
    file: str = ''
    max_bytes: int = 10_485_760
    backup_count: int = 5
    audit_tier: str = 'full'
    m2m_stream: bool = False
    m2m_diagnostic: bool = False
    redact_executor_output: bool = True
    components: dict = Field(default_factory=dict)


def logging_cfg(config: dict) -> LoggingConfig:
    raw: dict[str, Any] = config.get('logging', {}) if isinstance(config, dict) else {}
    return LoggingConfig.model_validate(raw)


# ── P2P ──────────────────────────────────────────────────────────────────────

class P2PConfig(BaseModel, frozen=True):
    min_evidence_borrows: int = 5
    trial_escrow_pct: int = 10
    jitter_frac: float = 0.0
    earn_jitter_frac: float = 0.0
    consensus_floor_multiplier: float = 0.0


def p2p_cfg(config: dict) -> P2PConfig:
    raw: dict[str, Any] = config.get('p2p', {}) if isinstance(config, dict) else {}
    mint = raw.get('mint', {}) if isinstance(raw, dict) else {}
    pricing = raw.get('pricing', {}) if isinstance(raw, dict) else {}
    return P2PConfig.model_validate({
        'min_evidence_borrows': mint.get('min_evidence_borrows', 5),
        'trial_escrow_pct': mint.get('trial_escrow_pct', 10),
        'jitter_frac': pricing.get('jitter_frac', 0.0),
        'earn_jitter_frac': pricing.get('earn_jitter_frac', 0.0),
        'consensus_floor_multiplier': pricing.get('consensus_floor_multiplier', 0.0),
    })


# ── Feature matching ──────────────────────────────────────────────────────────

class FeatureMatchingConfig(BaseModel, frozen=True):
    layer1_strict: bool = True
    layer2_cap_weight: int = 60
    layer2_lang_weight: int = 30
    layer2_loc_weight: int = 10
    borrow_threshold: float = 0.5


def feature_matching_cfg(config: dict) -> FeatureMatchingConfig:
    raw: dict[str, Any] = config.get('feature_matching', {}) if isinstance(config, dict) else {}
    return FeatureMatchingConfig.model_validate(raw)


# ── Sources ───────────────────────────────────────────────────────────────────

class SourcesConfig(BaseModel, frozen=True):
    auto_sync_interval_s: int = 300
    allow_act: bool = False
    act_audit_all: bool = True


def sources_cfg(config: dict) -> SourcesConfig:
    raw: dict[str, Any] = config.get('sources', {}) if isinstance(config, dict) else {}
    return SourcesConfig.model_validate(raw)


# ── MIME policy ───────────────────────────────────────────────────────────────

class MimePolicyConfig(BaseModel, frozen=True):
    network_policy: str = 'quality_gate_only'


def mime_policy_cfg(config: dict) -> MimePolicyConfig:
    raw: dict[str, Any] = config.get('mime_policy', {}) if isinstance(config, dict) else {}
    return MimePolicyConfig.model_validate(raw)
