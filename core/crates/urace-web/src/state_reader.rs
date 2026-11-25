//! Helpers to read state JSON files from the URACE root directory (~/.urace/).

use serde_json::Value;
use std::path::Path;

/// Read `<root>/state/state.json` and return its parsed JSON.
/// Returns an empty object if the file is missing or malformed.
pub fn read_state(root: &Path) -> Value {
    let p = root.join("state").join("state.json");
    if !p.exists() {
        return Value::Object(Default::default());
    }
    std::fs::read_to_string(&p)
        .ok()
        .and_then(|s| serde_json::from_str(&s).ok())
        .unwrap_or(Value::Object(Default::default()))
}

/// Read the last `n` JSON lines from a `.jsonl` file.
/// Returns an empty vec if the file is missing or unreadable.
pub fn read_jsonl_last_n(path: &Path, n: usize) -> Vec<Value> {
    if !path.exists() {
        return vec![];
    }
    std::fs::read_to_string(path)
        .ok()
        .unwrap_or_default()
        .lines()
        .filter(|l| !l.trim().is_empty())
        .filter_map(|l| serde_json::from_str(l).ok())
        .collect::<Vec<Value>>()
        .into_iter()
        .rev()
        .take(n)
        .rev()
        .collect()
}

/// Read `<root>/sources.json` (source registry snapshot written by the daemon).
pub fn read_sources_json(root: &Path) -> Value {
    let p = root.join("sources.json");
    if !p.exists() {
        return Value::Object(Default::default());
    }
    std::fs::read_to_string(&p)
        .ok()
        .and_then(|s| serde_json::from_str(&s).ok())
        .unwrap_or(Value::Object(Default::default()))
}

/// Check whether the daemon PID file exists and the process is alive.
/// Returns `(running, pid_or_none)`.
pub fn daemon_status(root: &Path) -> (bool, Option<u32>) {
    let pid_path = root.join("daemon.pid");
    if !pid_path.exists() {
        return (false, None);
    }
    let pid_str = match std::fs::read_to_string(&pid_path) {
        Ok(s) => s,
        Err(_) => return (false, None),
    };
    let pid: u32 = match pid_str.trim().parse() {
        Ok(p) => p,
        Err(_) => return (false, None),
    };
    let running = process_exists(pid);
    (running, Some(pid))
}

/// Check if a process with the given PID exists.
/// On Unix, reads /proc/<pid> or uses kill(pid, 0).
/// On other platforms, conservatively returns false.
fn process_exists(pid: u32) -> bool {
    // On Linux /proc/<pid> is reliable and doesn't require kill(2)
    #[cfg(target_os = "linux")]
    {
        std::path::Path::new(&format!("/proc/{pid}")).exists()
    }
    #[cfg(all(unix, not(target_os = "linux")))]
    {
        // Use kill(pid, 0) via inline assembly-free extern C
        extern "C" {
            fn kill(__pid: i32, __sig: i32) -> i32;
        }
        unsafe { kill(pid as i32, 0) == 0 }
    }
    #[cfg(not(unix))]
    {
        let _ = pid;
        false
    }
}
