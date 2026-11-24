//! Version constants — single source of truth matching Python `version.py`.
//!
//! Python source: `runtime/urace/version.py`

/// Runtime version string — matches `RUNTIME_VERSION` in Python.
pub const VERSION: &str = "0.9.3";

/// State schema format version integer.
pub const FORMAT_VERSION: u32 = 1;

/// Oldest state format this runtime can open.
pub const MIN_FORMAT_VERSION: u32 = 1;

/// Integration bridge protocol version.
pub const BRIDGE_VERSION: u32 = 1;

/// Minimum bridge client version accepted.
pub const MIN_BRIDGE_CLIENT_VERSION: u32 = 1;

/// Feature catalog schema version (rules v2).
pub const FEATURE_CATALOG_SCHEMA_VERSION: u32 = 2;

/// Source adapter protocol version.
pub const SOURCE_ADAPTER_PROTOCOL_VERSION: u32 = 2;

/// Exchange audit schema version.
pub const EXCHANGE_AUDIT_SCHEMA_VERSION: u32 = 1;

/// Executor probe schema version.
pub const EXECUTOR_PROBE_SCHEMA_VERSION: u32 = 1;

/// Config schema version.
pub const CONFIG_SCHEMA_VERSION: u32 = 2;

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn version_not_empty() {
        assert!(!VERSION.is_empty(), "VERSION constant must not be empty");
    }

    #[test]
    fn version_semver_shape() {
        // Check it has at least two dots (X.Y.Z)
        let dot_count = VERSION.chars().filter(|&c| c == '.').count();
        assert!(dot_count >= 2, "VERSION should be semver-shaped X.Y.Z, got {VERSION}");
    }

    #[test]
    fn format_versions_consistent() {
        assert!(MIN_FORMAT_VERSION <= FORMAT_VERSION);
    }
}
