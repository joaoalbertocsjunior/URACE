//! CPU / memory / disk detection for resource accounting.
//!
//! Ported from `hardware_info.py` (76 lines).
//!
//! The Python module also surveys GPUs via `nvidia-smi`.  GPU detection
//! requires `subprocess` or native bindings that have no equivalent in the
//! workspace dependencies; GPU fields are omitted from the Rust struct and
//! the gossip payload notes their absence.
//!
//! All reads are best-effort: failures fall back to 0 / empty rather than
//! propagating.  This matches the Python `survey_hardware` contract
//! ("Never raises; falls back to zeros").

use std::path::Path;
use std::sync::{Mutex, OnceLock};

use sysinfo::{Disks, System};

// ---------------------------------------------------------------------------
// HardwareInfo
// ---------------------------------------------------------------------------

/// Best-effort hardware survey result.
#[derive(Debug, Clone, Default)]
pub struct HardwareInfo {
    /// Logical CPU count (0 when unavailable).
    pub cpu_count: usize,
    /// Total RAM in megabytes (0 when unavailable).
    pub memory_mb: u64,
    /// Free disk space on the working directory's filesystem in megabytes
    /// (0 when unavailable).
    pub disk_free_mb: u64,
    /// Machine hostname (empty string when unavailable).
    pub hostname: String,
}

// ---------------------------------------------------------------------------
// Collection
// ---------------------------------------------------------------------------

/// Perform a best-effort hardware survey.  Never panics or propagates errors.
pub fn collect() -> HardwareInfo {
    let mut sys = System::new_all();
    sys.refresh_all();

    let cpu_count = sys.cpus().len().max(1);
    let memory_mb = sys.total_memory() / 1024 / 1024;
    let hostname = System::host_name().unwrap_or_default();
    let disk_free_mb = {
        let disks = Disks::new_with_refreshed_list();
        disks
            .iter()
            .find(|d| d.mount_point() == Path::new("/"))
            .map(|d| d.available_space() / 1024 / 1024)
            .unwrap_or(0)
    };

    HardwareInfo {
        cpu_count,
        memory_mb,
        disk_free_mb,
        hostname,
    }
}

/// Return a human-readable summary of `info`.
pub fn render(info: &HardwareInfo) -> String {
    format!(
        "hostname={} cpu_count={} memory_mb={} disk_free_mb={}",
        if info.hostname.is_empty() { "<unknown>" } else { &info.hostname },
        info.cpu_count,
        info.memory_mb,
        info.disk_free_mb,
    )
}

// ---------------------------------------------------------------------------
// Cached singleton (mirrors Python `get_hardware_info`)
// ---------------------------------------------------------------------------

/// Global cached survey.
static CACHED: OnceLock<Mutex<Option<HardwareInfo>>> = OnceLock::new();

/// Return the cached survey; pass `refresh = true` to force a new survey.
pub fn get_hardware_info(refresh: bool) -> HardwareInfo {
    let mutex = CACHED.get_or_init(|| Mutex::new(None));
    let mut guard = mutex.lock().unwrap_or_else(|e| e.into_inner());
    if guard.is_none() || refresh {
        *guard = Some(collect());
    }
    guard.as_ref().unwrap().clone()
}

/// Build a gossip payload (mirrors Python `hardware_gossip_payload`).
pub fn hardware_gossip_payload() -> serde_json::Value {
    let hw = get_hardware_info(false);
    serde_json::json!({
        "cpu_count":    hw.cpu_count,
        "memory_mb":    hw.memory_mb,
        "disk_free_mb": hw.disk_free_mb,
        "hostname":     hw.hostname,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn collect_does_not_panic() {
        let info = collect();
        // cpu_count is always at least 1 on the CI runner.
        assert!(info.cpu_count >= 1);
    }

    #[test]
    fn render_contains_all_fields() {
        let info = HardwareInfo {
            cpu_count: 4,
            memory_mb: 8192,
            disk_free_mb: 100_000,
            hostname: "test-host".to_string(),
        };
        let s = render(&info);
        assert!(s.contains("cpu_count=4"));
        assert!(s.contains("memory_mb=8192"));
        assert!(s.contains("disk_free_mb=100000"));
        assert!(s.contains("hostname=test-host"));
    }

    #[test]
    fn get_hardware_info_caches() {
        let first = get_hardware_info(false);
        let second = get_hardware_info(false);
        // Both calls must return consistent cpu_count.
        assert_eq!(first.cpu_count, second.cpu_count);
    }

    #[test]
    fn gossip_payload_has_expected_keys() {
        let payload = hardware_gossip_payload();
        assert!(payload.get("cpu_count").is_some());
        assert!(payload.get("memory_mb").is_some());
        assert!(payload.get("disk_free_mb").is_some());
        assert!(payload.get("hostname").is_some());
    }

    #[test]
    fn render_unknown_hostname() {
        let info = HardwareInfo {
            cpu_count: 1,
            memory_mb: 0,
            disk_free_mb: 0,
            hostname: String::new(),
        };
        let s = render(&info);
        assert!(s.contains("hostname=<unknown>"));
    }
}
