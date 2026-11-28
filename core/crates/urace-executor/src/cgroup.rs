//! Cgroup v2 memory limit enforcement for sandboxed executor processes.
//!
//! Writes a `memory.max` limit into a per-process cgroup v2 slice.
//! Silently skips if the cgroup v2 hierarchy is not writable (containers,
//! non-Linux, or systems without memory controller enabled).

/// Apply a cgroup v2 memory limit for the process identified by `pid`.
///
/// Creates (if needed) the cgroup `/sys/fs/cgroup/urace.slice/urace-{pid}/`
/// and writes `memory_mb * 1024 * 1024` to `memory.max`.
///
/// Returns `Ok(())` whether or not the limit was actually applied.
/// Returns `Err(description)` only if an unexpected I/O error occurs on a
/// cgroup path that is confirmed to exist.
pub fn apply_memory_limit_mb(pid: u32, memory_mb: u64) -> Result<(), String> {
    #[cfg(target_os = "linux")]
    {
        apply_memory_limit_linux(pid, memory_mb)
    }
    #[cfg(not(target_os = "linux"))]
    {
        let _ = (pid, memory_mb);
        Ok(())
    }
}

#[cfg(target_os = "linux")]
fn apply_memory_limit_linux(pid: u32, memory_mb: u64) -> Result<(), String> {
    use std::fs;
    use std::path::PathBuf;

    // Check whether cgroup v2 root is accessible.
    let cgroup_root = std::path::Path::new("/sys/fs/cgroup");
    if !cgroup_root.exists() {
        // No cgroup v2 mount — skip silently.
        return Ok(());
    }

    // Create the urace.slice parent if needed (best-effort; may require root).
    let slice_dir: PathBuf = cgroup_root.join("urace.slice");
    if !slice_dir.exists() {
        if let Err(e) = fs::create_dir_all(&slice_dir) {
            // Cannot create cgroup slice — likely running unprivileged. Skip.
            let _ = e;
            return Ok(());
        }
    }

    // Per-process cgroup directory.
    let proc_cgroup: PathBuf = slice_dir.join(format!("urace-{pid}"));
    if !proc_cgroup.exists() {
        if let Err(e) = fs::create_dir_all(&proc_cgroup) {
            let _ = e;
            return Ok(());
        }
    }

    // Write memory limit.
    let memory_bytes = memory_mb.saturating_mul(1024 * 1024);
    let memory_max = proc_cgroup.join("memory.max");
    if let Err(e) = fs::write(&memory_max, format!("{memory_bytes}\n")) {
        // Write failed — could be unprivileged, missing memory controller, etc.
        // This is not a hard failure: seccomp still enforces the sandbox.
        let _ = e;
        return Ok(());
    }

    // Add the process to this cgroup.
    let cgroup_procs = proc_cgroup.join("cgroup.procs");
    fs::write(&cgroup_procs, format!("{pid}\n"))
        .map_err(|e| format!("failed to write cgroup.procs for pid {pid}: {e}"))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn apply_memory_limit_does_not_panic() {
        // Should always return Ok regardless of privileges.
        let result = apply_memory_limit_mb(std::process::id(), 64);
        assert!(result.is_ok(), "apply_memory_limit_mb returned Err: {:?}", result);
    }
}
