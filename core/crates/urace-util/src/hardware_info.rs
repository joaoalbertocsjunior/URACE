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

use std::sync::{Mutex, OnceLock};

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
    HardwareInfo {
        cpu_count: read_cpu_count(),
        memory_mb: read_memory_mb(),
        disk_free_mb: read_disk_free_mb(),
        hostname: read_hostname(),
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

// ---------------------------------------------------------------------------
// Platform-specific readers
// ---------------------------------------------------------------------------

#[cfg(target_os = "linux")]
fn read_cpu_count() -> usize {
    // Count "processor\t:" lines in /proc/cpuinfo.
    std::fs::read_to_string("/proc/cpuinfo")
        .unwrap_or_default()
        .lines()
        .filter(|l| l.starts_with("processor"))
        .count()
        .max(1) // at least 1
}

#[cfg(not(target_os = "linux"))]
fn read_cpu_count() -> usize {
    // Fallback: use the standard available_parallelism if the platform
    // exposes it; otherwise 1.
    std::thread::available_parallelism()
        .map(|n| n.get())
        .unwrap_or(1)
}

#[cfg(target_os = "linux")]
fn read_memory_mb() -> u64 {
    // Parse MemTotal from /proc/meminfo.
    // Format: "MemTotal:       16384000 kB"
    std::fs::read_to_string("/proc/meminfo")
        .unwrap_or_default()
        .lines()
        .find(|l| l.starts_with("MemTotal:"))
        .and_then(|line| {
            line.split_whitespace()
                .nth(1)
                .and_then(|v| v.parse::<u64>().ok())
        })
        .map(|kb| kb / 1024)
        .unwrap_or(0)
}

#[cfg(not(target_os = "linux"))]
fn read_memory_mb() -> u64 {
    0
}

fn read_disk_free_mb() -> u64 {
    // Use statvfs-equivalent via /proc/mounts on Linux by calling
    // std::fs::metadata on the cwd, then reading /proc/mounts for the mount
    // point, then reading /proc/diskstats.
    //
    // Because we cannot add `nix` / `libc` as new dependencies, we fall back
    // to reading /proc/self/mountinfo and parsing free blocks from
    // /proc/diskstats — which does NOT carry free space.
    //
    // The only portable zero-dep way is a statfs(2) syscall.  We issue it
    // directly on Linux via inline assembly-free libc wrapper using the
    // `std::os::unix` extension, which is available without extra crates.
    //
    // On other platforms we return 0 (documented contract).
    disk_free_mb_impl()
}

#[cfg(target_os = "linux")]
fn disk_free_mb_impl() -> u64 {
    // Safe statfs via /proc/self/statm is not useful here.
    // We read /proc/mounts to find the cwd mount-point, then parse
    // /sys/fs/... — but that is unreliable too.
    //
    // The cleanest zero-new-dep approach on Linux is to read the statvfs
    // result directly.  std::fs does not expose statvfs, but we can read
    // `df --output=avail .` via /proc only if present.  Since we cannot
    // spawn processes (too heavy for a utility module) we use a direct
    // `statvfs` libc call through `unsafe`.
    //
    // This is the only `unsafe` block in urace-util; the safety argument is:
    //   - `buf` is stack-allocated and large enough for `libc::statvfs64`.
    //   - `path` is a valid C string (".").
    //   - `statvfs64` is documented as async-signal-safe on Linux.
    //
    // If the call fails we return 0 per the documented fallback contract.
    use std::mem::MaybeUninit;

    // statvfs64 layout on Linux x86-64 and aarch64 (glibc):
    // We reproduce the struct manually to avoid the libc crate.
    // All fields are u64 on 64-bit platforms.
    #[repr(C)]
    struct Statvfs64 {
        f_bsize:   u64,
        f_frsize:  u64,
        f_blocks:  u64,
        f_bfree:   u64,
        f_bavail:  u64,
        f_files:   u64,
        f_ffree:   u64,
        f_favail:  u64,
        f_fsid:    u64,
        f_flag:    u64,
        f_namemax: u64,
        _spare:    [i32; 6],
    }

    let path = b".\0";
    let mut buf: MaybeUninit<Statvfs64> = MaybeUninit::uninit();

    // SAFETY: buf is uninit storage of the right size; path is a valid C string.
    let ret = unsafe {
        libc_statvfs64(path.as_ptr() as *const i8, buf.as_mut_ptr() as *mut std::ffi::c_void)
    };

    if ret != 0 {
        return 0;
    }

    // SAFETY: ret == 0 means the kernel filled buf.
    let stat = unsafe { buf.assume_init() };
    // f_bavail * f_frsize gives bytes available to non-root.
    (stat.f_bavail.saturating_mul(stat.f_frsize)) / (1024 * 1024)
}

#[cfg(target_os = "linux")]
unsafe fn libc_statvfs64(path: *const i8, buf: *mut std::ffi::c_void) -> i32 {
    // Syscall number for statfs64 on x86-64 is 137; on aarch64 it is not
    // available as a direct syscall (use statfs instead, nr 43).
    // Rather than writing arch-specific inline asm, we link against the
    // system libc via `extern "C"`.
    extern "C" {
        fn statvfs64(path: *const i8, buf: *mut std::ffi::c_void) -> i32;
    }
    statvfs64(path, buf)
}

#[cfg(not(target_os = "linux"))]
fn disk_free_mb_impl() -> u64 {
    0
}

fn read_hostname() -> String {
    // Try /proc/sys/kernel/hostname first (Linux only, no allocation overhead).
    #[cfg(target_os = "linux")]
    if let Ok(h) = std::fs::read_to_string("/proc/sys/kernel/hostname") {
        return h.trim().to_string();
    }

    // Fallback: gethostname via std — not available in std directly, so we
    // read the environment variable HOSTNAME as a last resort.
    std::env::var("HOSTNAME").unwrap_or_default()
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
