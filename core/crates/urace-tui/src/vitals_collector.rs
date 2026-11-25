//! Live vitals collection from URACE state files.
//!
//! `collect` reads `state/state.json` (or `state.json`) and `daemon.pid` from the
//! URACE root directory and returns a [`LiveVitals`] snapshot.
//! The function never panics and never propagates I/O errors — a missing or
//! unreadable file silently returns a default value for the affected field.

use serde_json::Value;
use std::path::Path;

/// A snapshot of live runtime vitals derived from state files.
#[derive(Debug, Clone, Default)]
pub struct LiveVitals {
    /// Current lifecycle state string (e.g. "RUNNING", "IDLE", "UNKNOWN").
    pub lifecycle_state: String,
    /// Current APS / diagnostic score.
    pub aps_score: f64,
    /// Number of completed improvement cycles (length of `checkpoints` array).
    pub cycle_count: usize,
    /// Number of objectives present in state.
    pub objectives_count: usize,
    /// Number of evidence items present in state.
    pub evidence_count: usize,
    /// ISO-8601 timestamp of the last cycle, if available.
    pub last_cycle_at: Option<String>,
    /// Whether the daemon process is currently running.
    pub running: bool,
    /// PID of the daemon process, if available.
    pub pid: Option<u32>,
}

/// Collect live vitals by reading state files from `root`.
///
/// Tries `root/state/state.json` first, then falls back to `root/state.json`.
/// Returns a default [`LiveVitals`] (all zero / empty) if neither file exists.
pub fn collect(root: &Path) -> LiveVitals {
    let state = read_state_json(root);

    LiveVitals {
        lifecycle_state: state
            .get("lifecycle_state")
            .and_then(|v| v.as_str())
            .unwrap_or("UNKNOWN")
            .to_string(),

        aps_score: state
            .get("aps_score")
            .or_else(|| state.get("current_aps_score"))
            .and_then(|v| v.as_f64())
            .unwrap_or(0.0),

        cycle_count: state
            .get("checkpoints")
            .and_then(|v| v.as_array())
            .map(|a| a.len())
            .unwrap_or(0),

        objectives_count: state
            .get("objectives")
            .and_then(|v| v.as_array())
            .map(|a| a.len())
            .unwrap_or(0),

        evidence_count: state
            .get("evidence")
            .and_then(|v| v.as_array())
            .map(|a| a.len())
            .unwrap_or(0),

        last_cycle_at: state
            .get("checkpoints")
            .and_then(|v| v.as_array())
            .and_then(|cps| cps.last())
            .and_then(|c| c.get("completed_at").or_else(|| c.get("started_at")))
            .and_then(|v| v.as_str())
            .map(|s| s.to_string()),

        running: daemon_running(root),
        pid: read_pid(root),
    }
}

/// Read and parse `state/state.json` or `state.json` under `root`.
/// Returns `Value::Null` on any error (missing file, parse error, etc.).
fn read_state_json(root: &Path) -> Value {
    // Preferred location: root/state/state.json
    let candidates = [
        root.join("state").join("state.json"),
        root.join("state.json"),
    ];

    for path in &candidates {
        if path.exists() {
            match std::fs::read_to_string(path) {
                Ok(text) => {
                    if let Ok(val) = serde_json::from_str::<Value>(&text) {
                        return val;
                    }
                }
                Err(_) => continue,
            }
        }
    }

    Value::Null
}

/// Return `true` if the daemon process recorded in `daemon.pid` is currently alive.
///
/// On Linux this checks `/proc/<pid>/` existence.  On other platforms only the
/// PID file existence is checked (best-effort).
fn daemon_running(root: &Path) -> bool {
    match read_pid(root) {
        None => false,
        Some(pid) => process_alive(pid),
    }
}

/// Read the PID from `root/daemon.pid`.  Returns `None` if the file is absent
/// or does not contain a valid unsigned integer.
fn read_pid(root: &Path) -> Option<u32> {
    let pid_path = root.join("daemon.pid");
    let text = std::fs::read_to_string(&pid_path).ok()?;
    text.trim().parse::<u32>().ok()
}

/// Check whether a process with the given PID is running.
///
/// On Linux: checks `/proc/<pid>` directory existence (no signals needed).
/// On other platforms: always returns `true` when the PID can be read (best-effort).
fn process_alive(pid: u32) -> bool {
    #[cfg(target_os = "linux")]
    {
        std::path::Path::new(&format!("/proc/{pid}")).exists()
    }
    #[cfg(not(target_os = "linux"))]
    {
        // Best-effort: if we have a PID we assume the process may be running.
        let _ = pid;
        true
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::PathBuf;

    /// A non-existent root must return a default LiveVitals without panicking.
    #[test]
    fn collect_missing_root_returns_default() {
        let root = PathBuf::from("/nonexistent/urace/root/that/does/not/exist");
        let v = collect(&root);
        assert_eq!(v.lifecycle_state, "UNKNOWN");
        assert_eq!(v.aps_score, 0.0);
        assert_eq!(v.cycle_count, 0);
        assert_eq!(v.objectives_count, 0);
        assert_eq!(v.evidence_count, 0);
        assert!(v.last_cycle_at.is_none());
        assert!(!v.running);
        assert!(v.pid.is_none());
    }

    /// A root with a valid state.json is parsed correctly.
    #[test]
    fn collect_reads_state_json() {
        let dir = tempfile::tempdir().unwrap();
        let state_dir = dir.path().join("state");
        std::fs::create_dir_all(&state_dir).unwrap();

        let state = serde_json::json!({
            "lifecycle_state": "RUNNING",
            "aps_score": 87.5,
            "objectives": [{"id": "o1"}, {"id": "o2"}],
            "evidence": [{"id": "e1"}],
            "checkpoints": [
                {"completed_at": "2026-11-24T10:00:00Z"},
                {"completed_at": "2026-11-24T11:00:00Z"}
            ]
        });
        std::fs::write(
            state_dir.join("state.json"),
            serde_json::to_string(&state).unwrap(),
        )
        .unwrap();

        let v = collect(dir.path());
        assert_eq!(v.lifecycle_state, "RUNNING");
        assert_eq!(v.aps_score, 87.5);
        assert_eq!(v.objectives_count, 2);
        assert_eq!(v.evidence_count, 1);
        assert_eq!(v.cycle_count, 2);
        assert_eq!(v.last_cycle_at.as_deref(), Some("2026-11-24T11:00:00Z"));
    }

    /// Falls back to alternative `aps_score` key name `current_aps_score`.
    #[test]
    fn collect_uses_current_aps_score_fallback() {
        let dir = tempfile::tempdir().unwrap();
        let state = serde_json::json!({"current_aps_score": 42.0});
        std::fs::write(
            dir.path().join("state.json"),
            serde_json::to_string(&state).unwrap(),
        )
        .unwrap();

        let v = collect(dir.path());
        assert_eq!(v.aps_score, 42.0);
    }

    /// A malformed JSON file is silently ignored.
    #[test]
    fn collect_handles_corrupt_state_json() {
        let dir = tempfile::tempdir().unwrap();
        std::fs::write(dir.path().join("state.json"), b"not json!!!").unwrap();
        let v = collect(dir.path());
        assert_eq!(v.lifecycle_state, "UNKNOWN");
    }

    #[test]
    fn read_pid_missing_file_returns_none() {
        let dir = tempfile::tempdir().unwrap();
        assert!(read_pid(dir.path()).is_none());
    }

    #[test]
    fn read_pid_valid_file() {
        let dir = tempfile::tempdir().unwrap();
        std::fs::write(dir.path().join("daemon.pid"), b"12345\n").unwrap();
        assert_eq!(read_pid(dir.path()), Some(12345));
    }

    #[test]
    fn read_pid_invalid_content_returns_none() {
        let dir = tempfile::tempdir().unwrap();
        std::fs::write(dir.path().join("daemon.pid"), b"not-a-pid").unwrap();
        assert!(read_pid(dir.path()).is_none());
    }
}
