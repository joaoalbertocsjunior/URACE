"""Single source of truth for runtime and protocol version constants."""
RUNTIME_VERSION = "0.9.3"
FORMAT_VERSION = 1           # state schema_version integer
MIN_FORMAT_VERSION = 1       # oldest state format this runtime can open
BRIDGE_VERSION = 1           # integration_bridge protocol version
MIN_BRIDGE_CLIENT_VERSION = 1

# Phase 9A — protocol versioning
FEATURE_CATALOG_SCHEMA_VERSION  = 2  # rules v2 (SET_QUALITY_PROVEN, outcome_fingerprint)
SOURCE_ADAPTER_PROTOCOL_VERSION = 1  # Phase 1C SourceAdapter Protocol
EXCHANGE_AUDIT_SCHEMA_VERSION   = 1  # exchange audit row format
EXECUTOR_PROBE_SCHEMA_VERSION   = 1  # executor-probe-v1 (Phase 4B)
CONFIG_SCHEMA_VERSION           = 2  # Phase 1A: logging, p2p, feature_matching, mime_policy, sources

# Phase 9D — API schema currency markers
API_SCHEMA_VERSIONS = {
    'feature_catalog':    FEATURE_CATALOG_SCHEMA_VERSION,
    'source_adapter':     SOURCE_ADAPTER_PROTOCOL_VERSION,
    'exchange_audit':     EXCHANGE_AUDIT_SCHEMA_VERSION,
    'executor_probe':     EXECUTOR_PROBE_SCHEMA_VERSION,
    'config':             CONFIG_SCHEMA_VERSION,
    'bridge':             BRIDGE_VERSION,
    'state_format':       FORMAT_VERSION,
}
