//! Explicit catalog of supported protocol/adapter names.
//!
//! Ported from `protocol_catalog.py` (14 lines).  The Python module
//! dynamically imports `mcp_server`, `a2a_server`, and `peer_exchange` to
//! build its description, but the constant list of adapter kinds that drive
//! transport routing is exactly the slice below.

/// Every adapter kind the local data-transport layer will handle natively.
/// Anything not in this list requires an external adapter and must be
/// surfaced as `ADAPTER_REQUIRED`.
pub const SUPPORTED_PROTOCOLS: &[&str] = &[
    "json",
    "json_file",
    "csv",
    "sqlite",
    "sqlite3",
    "cli",
    "typed-api",
    "mcp-stdio",
    "a2a-loopback",
    "peer-artifacts",
];

/// Returns `true` when `protocol` is an explicitly supported protocol name.
/// Comparison is case-sensitive (protocols are always lower-kebab in URACE).
pub fn is_supported(protocol: &str) -> bool {
    SUPPORTED_PROTOCOLS.contains(&protocol)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn known_protocols_are_supported() {
        for &p in SUPPORTED_PROTOCOLS {
            assert!(is_supported(p), "expected {p} to be supported");
        }
    }

    #[test]
    fn unknown_protocol_is_not_supported() {
        assert!(!is_supported("ftp"));
        assert!(!is_supported(""));
        assert!(!is_supported("JSON")); // case-sensitive
    }
}
