//! Logging ring-buffer and configuration helpers.
//!
//! Ported from `logging_config.py` (233 lines).
//!
//! The Python module wires into the Python `logging` framework and
//! subscribes to the URACE event bus.  In Rust those concerns belong to the
//! `tracing` / `tracing-subscriber` crates that are already in the workspace.
//! This module therefore provides:
//!
//! * A `LogLevel` enum aligned with both Python `logging` levels and
//!   `tracing`'s `Level` type.
//! * A `LogRecord` struct that captures a single structured log event.
//! * A fixed-capacity `RingBuffer` (500 entries) suitable for in-process
//!   diagnostics and streaming to a debug UI.
//! * `LoggingConfig` — a plain configuration value object (no I/O side
//!   effects) that the caller can pass to `tracing-subscriber`.

use std::collections::VecDeque;

// ---------------------------------------------------------------------------
// LogLevel
// ---------------------------------------------------------------------------

/// Log verbosity level, aligned with Python `logging` constants.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum LogLevel {
    Debug   = 10,
    Info    = 20,
    Warning = 30,
    Error   = 40,
}

impl LogLevel {
    /// Parse from a case-insensitive string.  Returns `Warning` on unknown input
    /// (matches Python `getattr(logging, level.upper(), logging.WARNING)`).
    pub fn from_str(s: &str) -> Self {
        match s.to_ascii_uppercase().as_str() {
            "DEBUG"   => Self::Debug,
            "INFO"    => Self::Info,
            "WARNING" | "WARN" => Self::Warning,
            "ERROR"   => Self::Error,
            _         => Self::Warning,
        }
    }

    /// Return the conventional string representation.
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Debug   => "DEBUG",
            Self::Info    => "INFO",
            Self::Warning => "WARNING",
            Self::Error   => "ERROR",
        }
    }
}

impl std::fmt::Display for LogLevel {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.as_str())
    }
}

// ---------------------------------------------------------------------------
// LogRecord
// ---------------------------------------------------------------------------

/// A single captured log event.
#[derive(Debug, Clone)]
pub struct LogRecord {
    /// ISO-8601 timestamp (or any string the caller provides).
    pub at: String,
    /// Severity level.
    pub level: LogLevel,
    /// Logger / component name (e.g. `"urace.source_adapters"`).
    pub logger: String,
    /// Human-readable message.
    pub message: String,
}

impl LogRecord {
    /// Construct a new record with the current UTC time (formatted as
    /// `YYYY-MM-DDTHH:MM:SS` to match the Python `JsonFormatter`).
    pub fn now(level: LogLevel, logger: impl Into<String>, message: impl Into<String>) -> Self {
        Self {
            at: utc_now_iso(),
            level,
            logger: logger.into(),
            message: message.into(),
        }
    }
}

// ---------------------------------------------------------------------------
// RingBuffer
// ---------------------------------------------------------------------------

/// Fixed-capacity ring buffer for `LogRecord`s.
///
/// When full, the oldest record is evicted before inserting the new one.
/// Capacity is fixed at construction time; the Python default is 500.
pub struct RingBuffer {
    capacity: usize,
    inner: VecDeque<LogRecord>,
}

impl RingBuffer {
    /// Create a ring buffer with the given capacity.
    pub fn new(capacity: usize) -> Self {
        Self {
            capacity: capacity.max(1),
            inner: VecDeque::with_capacity(capacity.min(1024)),
        }
    }

    /// Create the standard 500-entry ring buffer used by the Python runtime.
    pub fn default_capacity() -> Self {
        Self::new(500)
    }

    /// Push a record, evicting the oldest if at capacity.
    pub fn push(&mut self, record: LogRecord) {
        if self.inner.len() >= self.capacity {
            self.inner.pop_front();
        }
        self.inner.push_back(record);
    }

    /// Return up to the last `n` records (most recent last).
    pub fn recent(&self, n: usize) -> Vec<&LogRecord> {
        let skip = self.inner.len().saturating_sub(n);
        self.inner.iter().skip(skip).collect()
    }

    /// Return all records at or above `level`.
    pub fn filter(&self, level: LogLevel) -> Vec<&LogRecord> {
        self.inner.iter().filter(|r| r.level >= level).collect()
    }

    /// Total number of records currently stored.
    pub fn len(&self) -> usize {
        self.inner.len()
    }

    /// True when the buffer holds no records.
    pub fn is_empty(&self) -> bool {
        self.inner.is_empty()
    }
}

impl Default for RingBuffer {
    fn default() -> Self {
        Self::default_capacity()
    }
}

// ---------------------------------------------------------------------------
// LoggingConfig
// ---------------------------------------------------------------------------

/// Configuration value object for the URACE logging subsystem.
///
/// Consumers are expected to translate this into `tracing-subscriber` builder
/// calls; this struct carries no I/O state of its own.
#[derive(Debug, Clone)]
pub struct LoggingConfig {
    /// Minimum level to record.
    pub level: LogLevel,
    /// Output format: `"text"` or `"json"`.
    pub format: String,
    /// Optional path to a rotating log file (empty = stderr only).
    pub file: String,
    /// Maximum size in bytes before the log file is rotated.
    pub max_bytes: u64,
    /// Number of backup files to keep.
    pub backup_count: u32,
}

impl Default for LoggingConfig {
    fn default() -> Self {
        Self {
            level: LogLevel::Warning,
            format: "text".to_string(),
            file: String::new(),
            max_bytes: 10 * 1024 * 1024,
            backup_count: 5,
        }
    }
}

impl LoggingConfig {
    /// Build from the `"logging"` section of a URACE config map.
    pub fn from_config(config: &serde_json::Value) -> Self {
        let section = config.get("logging").cloned().unwrap_or_default();
        let level = LogLevel::from_str(
            section.get("level").and_then(|v| v.as_str()).unwrap_or("WARNING"),
        );
        let format = section
            .get("format")
            .and_then(|v| v.as_str())
            .unwrap_or("text")
            .to_string();
        let file = section
            .get("file")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_string();
        let max_bytes = section
            .get("max_bytes")
            .and_then(|v| v.as_u64())
            .unwrap_or(10 * 1024 * 1024);
        let backup_count = section
            .get("backup_count")
            .and_then(|v| v.as_u64())
            .unwrap_or(5) as u32;

        Self { level, format, file, max_bytes, backup_count }
    }

    /// Return `true` when JSON output format is requested.
    pub fn is_json(&self) -> bool {
        self.format == "json"
    }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/// Return the current UTC time formatted as `YYYY-MM-DDTHH:MM:SS`.
fn utc_now_iso() -> String {
    // We cannot use the `time` crate here without adding it to this crate's
    // dependencies (it is only in urace-types).  Use the standard library
    // `SystemTime` and format manually.
    use std::time::{SystemTime, UNIX_EPOCH};

    let secs = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs();

    // Simple Julian Day / Gregorian calendar decomposition.
    let (y, mo, d, h, mi, s) = secs_to_ymdhms(secs);
    format!("{:04}-{:02}-{:02}T{:02}:{:02}:{:02}", y, mo, d, h, mi, s)
}

/// Decompose a Unix timestamp (seconds since epoch) into (year, month, day,
/// hour, minute, second).  Handles dates from 1970 to 2099 correctly.
fn secs_to_ymdhms(secs: u64) -> (u32, u32, u32, u32, u32, u32) {
    let s = (secs % 60) as u32;
    let mins = secs / 60;
    let mi = (mins % 60) as u32;
    let hours = mins / 60;
    let h = (hours % 24) as u32;
    let days = hours / 24; // days since 1970-01-01

    // Gregorian calendar — algorithm from http://www.howardhinnant.com/date_algorithms.html
    let z = days + 719468;
    let era = z / 146097;
    let doe = z % 146097;
    let yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;
    let y = yoe + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = doy - (153 * mp + 2) / 5 + 1;
    let mo = if mp < 10 { mp + 3 } else { mp - 9 };
    let y = if mo <= 2 { y + 1 } else { y };

    (y as u32, mo as u32, d as u32, h, mi, s)
}

// ---------------------------------------------------------------------------
// Component / topic constants (ported from Python module)
// ---------------------------------------------------------------------------

/// Maps short component names to logger namespaces.
pub const COMPONENT_LOGGERS: &[(&str, &str)] = &[
    ("source",    "urace.source_adapters"),
    ("m2m",       "urace.api"),
    ("config",    "urace.config"),
    ("lifecycle", "urace.lifecycle"),
    ("cycle",     "urace.cli_cycle"),
    ("cost",      "urace.cost"),
    ("exchange",  "urace.peer_exchange"),
    ("executor",  "urace.executor"),
    ("security",  "urace.security"),
    ("audit",     "urace.audit"),
];

/// Components that cannot be silenced regardless of configuration.
pub const ALWAYS_ON: &[&str] = &["security", "audit"];

#[cfg(test)]
mod tests {
    use super::*;

    // --- LogLevel ---

    #[test]
    fn log_level_ordering() {
        assert!(LogLevel::Debug < LogLevel::Info);
        assert!(LogLevel::Info < LogLevel::Warning);
        assert!(LogLevel::Warning < LogLevel::Error);
    }

    #[test]
    fn log_level_from_str_case_insensitive() {
        assert_eq!(LogLevel::from_str("debug"),   LogLevel::Debug);
        assert_eq!(LogLevel::from_str("INFO"),    LogLevel::Info);
        assert_eq!(LogLevel::from_str("warning"), LogLevel::Warning);
        assert_eq!(LogLevel::from_str("ERROR"),   LogLevel::Error);
        assert_eq!(LogLevel::from_str("unknown"), LogLevel::Warning); // fallback
    }

    // --- RingBuffer ---

    #[test]
    fn ring_buffer_evicts_oldest_when_full() {
        let mut buf = RingBuffer::new(3);
        for i in 0..5u32 {
            buf.push(LogRecord::now(LogLevel::Info, "test", format!("msg-{i}")));
        }
        assert_eq!(buf.len(), 3);
        // The first two records (msg-0, msg-1) should have been evicted.
        let recent = buf.recent(3);
        assert_eq!(recent.len(), 3);
        assert!(recent[0].message.contains("msg-2"));
        assert!(recent[2].message.contains("msg-4"));
    }

    #[test]
    fn ring_buffer_recent_respects_n() {
        let mut buf = RingBuffer::new(10);
        for i in 0..8u32 {
            buf.push(LogRecord::now(LogLevel::Info, "t", format!("m{i}")));
        }
        assert_eq!(buf.recent(3).len(), 3);
        assert_eq!(buf.recent(100).len(), 8);
    }

    #[test]
    fn ring_buffer_filter_by_level() {
        let mut buf = RingBuffer::new(10);
        buf.push(LogRecord::now(LogLevel::Debug,   "t", "d"));
        buf.push(LogRecord::now(LogLevel::Info,    "t", "i"));
        buf.push(LogRecord::now(LogLevel::Warning, "t", "w"));
        buf.push(LogRecord::now(LogLevel::Error,   "t", "e"));

        let warnings_up = buf.filter(LogLevel::Warning);
        assert_eq!(warnings_up.len(), 2); // Warning + Error
    }

    // --- LoggingConfig ---

    #[test]
    fn logging_config_default_is_warning() {
        let cfg = LoggingConfig::default();
        assert_eq!(cfg.level, LogLevel::Warning);
        assert_eq!(cfg.format, "text");
        assert!(cfg.file.is_empty());
    }

    #[test]
    fn logging_config_from_config_json() {
        let v = serde_json::json!({
            "logging": {
                "level": "debug",
                "format": "json",
                "file": "/var/log/urace.log",
                "max_bytes": 1048576,
                "backup_count": 3
            }
        });
        let cfg = LoggingConfig::from_config(&v);
        assert_eq!(cfg.level, LogLevel::Debug);
        assert!(cfg.is_json());
        assert_eq!(cfg.file, "/var/log/urace.log");
        assert_eq!(cfg.max_bytes, 1_048_576);
        assert_eq!(cfg.backup_count, 3);
    }

    // --- Timestamp helper ---

    #[test]
    fn secs_to_ymdhms_epoch() {
        let (y, mo, d, h, mi, s) = secs_to_ymdhms(0);
        assert_eq!((y, mo, d, h, mi, s), (1970, 1, 1, 0, 0, 0));
    }

    #[test]
    fn secs_to_ymdhms_known_date() {
        // 2024-03-15T12:00:00Z = 1710504000
        let (y, mo, d, h, mi, s) = secs_to_ymdhms(1_710_504_000);
        assert_eq!((y, mo, d, h, mi, s), (2024, 3, 15, 12, 0, 0));
    }

    #[test]
    fn utc_now_iso_format() {
        let ts = utc_now_iso();
        // "YYYY-MM-DDTHH:MM:SS" → 19 chars
        assert_eq!(ts.len(), 19, "unexpected timestamp length: {ts}");
        assert_eq!(&ts[4..5], "-");
        assert_eq!(&ts[7..8], "-");
        assert_eq!(&ts[10..11], "T");
    }
}
