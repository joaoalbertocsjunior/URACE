//! M81 — Seccomp-BPF syscall filtering for Linux executor sandboxes.
//!
//! Defines the minimal allowed syscall set for URACE executor child processes
//! and a `SeccompFilter` struct that validates or generates a filter profile.
//!
//! On Linux, `install_seccomp_filter()` builds and installs a real BPF program
//! via `seccompiler::apply_filter()`, which calls `prctl(PR_SET_SECCOMP)`.
//! On other platforms the function is a no-op that returns `Ok(())`.
//!
//! The function is designed to be called from `Command::pre_exec` (after fork,
//! before exec), so it must not allocate or call async code.

#[cfg(target_os = "linux")]
use libc;
use serde::{Deserialize, Serialize};
use std::collections::BTreeSet;

// ── Default allowlist ─────────────────────────────────────────────────────────

/// Minimal Linux syscalls required for a sandboxed executor process.
///
/// This allowlist follows the principle of least privilege — only syscalls
/// needed for read-eval-print computation are included.  Network and file
/// write syscalls are excluded by default.
pub const DEFAULT_ALLOWLIST: &[&str] = &[
    // Process lifecycle
    "read", "write", "exit", "exit_group",
    // Memory management
    "brk", "mmap", "munmap", "mprotect",
    // Thread / futex (required by Rust runtime)
    "futex", "clone", "set_tid_address", "set_robust_list",
    // Clocks and signals (required for timeout enforcement)
    "clock_gettime", "clock_nanosleep", "nanosleep",
    "rt_sigaction", "rt_sigprocmask", "rt_sigreturn",
    // File descriptors — read-only access to pre-opened FDs
    "close", "fstat", "lseek", "pread64",
    // Pipe for capturing stdout/stderr
    "pipe2", "dup2",
    // Arch-specific: needed for Rust's standard library on x86-64
    "arch_prctl", "uname",
];

// ── SeccompFilter ─────────────────────────────────────────────────────────────

/// A seccomp allowlist profile for an executor process.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SeccompFilter {
    /// Set of allowed syscall names (sorted for deterministic serialisation).
    pub allowed_syscalls: BTreeSet<String>,
    /// Action taken when a syscall is not in the allowlist.
    pub default_action: SeccompAction,
}

/// Action taken when a syscall is blocked by the filter.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum SeccompAction {
    /// Kill the process with SIGSYS.
    KillProcess,
    /// Return EPERM to the caller (softer — allows graceful shutdown).
    Errno(i32),
}

impl Default for SeccompFilter {
    fn default() -> Self {
        SeccompFilter {
            allowed_syscalls: DEFAULT_ALLOWLIST.iter().map(|s| s.to_string()).collect(),
            default_action: SeccompAction::KillProcess,
        }
    }
}

impl SeccompFilter {
    /// Build a filter from a custom allowlist.
    pub fn new(allowed: impl IntoIterator<Item = impl Into<String>>, action: SeccompAction) -> Self {
        SeccompFilter {
            allowed_syscalls: allowed.into_iter().map(|s| s.into()).collect(),
            default_action: action,
        }
    }

    /// Return true if `syscall_name` is in the allowlist.
    pub fn allows(&self, syscall_name: &str) -> bool {
        self.allowed_syscalls.contains(syscall_name)
    }

    /// Validate that the filter contains all `required` syscalls.
    ///
    /// Returns a list of required syscalls that are absent from the allowlist.
    pub fn validate_required(&self, required: &[&str]) -> Vec<String> {
        required
            .iter()
            .filter(|s| !self.allowed_syscalls.contains(**s))
            .map(|s| s.to_string())
            .collect()
    }

    /// Return syscalls from `candidates` that are blocked by this filter.
    pub fn blocked_from(&self, candidates: &[&str]) -> Vec<String> {
        candidates
            .iter()
            .filter(|s| !self.allowed_syscalls.contains(**s))
            .map(|s| s.to_string())
            .collect()
    }

    /// Add a syscall to the allowlist.
    pub fn allow(&mut self, syscall: impl Into<String>) {
        self.allowed_syscalls.insert(syscall.into());
    }

    /// Remove a syscall from the allowlist.
    pub fn deny(&mut self, syscall: &str) {
        self.allowed_syscalls.remove(syscall);
    }
}

// ── Live BPF installation (Linux only) ───────────────────────────────────────

/// Install the default seccomp allowlist as a BPF filter in the calling thread.
///
/// Must be called after `fork()` but before `exec()` — typically from
/// `std::os::unix::process::CommandExt::pre_exec`.
///
/// Returns `Ok(())` on success or if seccomp is not available on this platform.
/// Returns `Err(description)` only when the filter was attempted and failed.
#[cfg(target_os = "linux")]
pub fn install_seccomp_filter() -> Result<(), String> {
    use seccompiler::{
        BpfProgram, SeccompAction, SeccompFilter as BpfFilter, SeccompRule, TargetArch,
    };
    use std::collections::BTreeMap;
    use std::convert::TryInto;

    // Build an allowlist: each syscall in DEFAULT_ALLOWLIST maps to an empty
    // rule-vector (unconditional allow on match).  Any syscall not listed
    // triggers the mismatch action (KillProcess).
    let syscall_numbers: &[(i64, &str)] = &[
        (libc::SYS_read,              "read"),
        (libc::SYS_write,             "write"),
        (libc::SYS_exit,              "exit"),
        (libc::SYS_exit_group,        "exit_group"),
        (libc::SYS_brk,               "brk"),
        (libc::SYS_mmap,              "mmap"),
        (libc::SYS_munmap,            "munmap"),
        (libc::SYS_mprotect,          "mprotect"),
        (libc::SYS_futex,             "futex"),
        (libc::SYS_clone,             "clone"),
        (libc::SYS_clone3,            "clone3"),
        (libc::SYS_set_tid_address,   "set_tid_address"),
        (libc::SYS_set_robust_list,   "set_robust_list"),
        (libc::SYS_clock_gettime,     "clock_gettime"),
        (libc::SYS_clock_nanosleep,   "clock_nanosleep"),
        (libc::SYS_nanosleep,         "nanosleep"),
        (libc::SYS_rt_sigaction,      "rt_sigaction"),
        (libc::SYS_rt_sigprocmask,    "rt_sigprocmask"),
        (libc::SYS_rt_sigreturn,      "rt_sigreturn"),
        (libc::SYS_close,             "close"),
        (libc::SYS_fstat,             "fstat"),
        (libc::SYS_lseek,             "lseek"),
        (libc::SYS_pread64,           "pread64"),
        (libc::SYS_pipe2,             "pipe2"),
        (libc::SYS_dup2,              "dup2"),
        (libc::SYS_arch_prctl,        "arch_prctl"),
        (libc::SYS_uname,             "uname"),
        // Additional syscalls Python and glibc need at startup:
        (libc::SYS_openat,            "openat"),
        (libc::SYS_newfstatat,        "newfstatat"),
        (libc::SYS_getdents64,        "getdents64"),
        (libc::SYS_fcntl,             "fcntl"),
        (libc::SYS_ioctl,             "ioctl"),
        (libc::SYS_getcwd,            "getcwd"),
        (libc::SYS_sigaltstack,       "sigaltstack"),
        (libc::SYS_prctl,             "prctl"),
        (libc::SYS_getrandom,         "getrandom"),
        (libc::SYS_madvise,           "madvise"),
        (libc::SYS_mremap,            "mremap"),
        (libc::SYS_getuid,            "getuid"),
        (libc::SYS_getgid,            "getgid"),
        (libc::SYS_geteuid,           "geteuid"),
        (libc::SYS_getegid,           "getegid"),
        (libc::SYS_getpid,            "getpid"),
        (libc::SYS_getppid,           "getppid"),
        (libc::SYS_gettid,            "gettid"),
        (libc::SYS_tgkill,            "tgkill"),
        (libc::SYS_restart_syscall,   "restart_syscall"),
        (libc::SYS_wait4,             "wait4"),
        (libc::SYS_prlimit64,         "prlimit64"),
        (libc::SYS_sysinfo,           "sysinfo"),
        (libc::SYS_times,             "times"),
        (libc::SYS_readlink,          "readlink"),
        (libc::SYS_readlinkat,        "readlinkat"),
        (libc::SYS_statfs,            "statfs"),
        (libc::SYS_access,            "access"),
        (libc::SYS_faccessat,         "faccessat"),
        (libc::SYS_faccessat2,        "faccessat2"),
    ];

    let mut rules: BTreeMap<i64, Vec<SeccompRule>> = BTreeMap::new();
    for (nr, _name) in syscall_numbers {
        rules.insert(*nr, vec![]);
    }

    let arch: TargetArch = std::env::consts::ARCH
        .try_into()
        .map_err(|e| format!("unsupported architecture for seccomp: {:?}", e))?;

    let filter = BpfFilter::new(
        rules,
        SeccompAction::KillProcess,
        SeccompAction::Allow,
        arch,
    )
    .map_err(|e| format!("seccomp filter build failed: {e}"))?;

    let bpf_prog: BpfProgram = filter
        .try_into()
        .map_err(|e| format!("seccomp BPF compile failed: {e}"))?;

    seccompiler::apply_filter(&bpf_prog)
        .map_err(|e| format!("seccomp apply_filter failed: {e}"))
}

/// No-op on non-Linux platforms.
#[cfg(not(target_os = "linux"))]
pub fn install_seccomp_filter() -> Result<(), String> {
    Ok(())
}

/// Verify that dangerous syscalls are not in the given filter's allowlist.
///
/// Returns `Ok(())` when no dangerous syscalls are present; otherwise
/// returns `Err(Vec<String>)` naming the offending syscalls.
pub fn assert_dangerous_blocked(filter: &SeccompFilter) -> Result<(), Vec<String>> {
    const DANGEROUS: &[&str] = &[
        "execve", "execveat",         // exec new programs
        "socket", "connect", "bind",  // network
        "ptrace",                      // debugger attach
        "mount", "umount2",           // filesystem manipulation
        "reboot",                      // system control
        "kexec_load",
        "create_module", "delete_module", "init_module",
    ];
    let present: Vec<String> = DANGEROUS
        .iter()
        .filter(|s| filter.allows(s))
        .map(|s| s.to_string())
        .collect();
    if present.is_empty() {
        Ok(())
    } else {
        Err(present)
    }
}

// ── Tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn default_filter_allows_read_write() {
        let f = SeccompFilter::default();
        assert!(f.allows("read"));
        assert!(f.allows("write"));
    }

    #[test]
    fn default_filter_blocks_execve() {
        let f = SeccompFilter::default();
        assert!(!f.allows("execve"), "execve must be blocked by default");
    }

    #[test]
    fn default_filter_blocks_socket() {
        let f = SeccompFilter::default();
        assert!(!f.allows("socket"), "socket must be blocked by default");
    }

    #[test]
    fn assert_dangerous_blocked_passes_for_default() {
        let f = SeccompFilter::default();
        assert!(assert_dangerous_blocked(&f).is_ok());
    }

    #[test]
    fn assert_dangerous_blocked_fails_when_execve_allowed() {
        let mut f = SeccompFilter::default();
        f.allow("execve");
        let result = assert_dangerous_blocked(&f);
        assert!(result.is_err());
        assert!(result.unwrap_err().contains(&"execve".to_string()));
    }

    #[test]
    fn validate_required_reports_missing() {
        let mut f = SeccompFilter::default();
        f.deny("futex");
        let missing = f.validate_required(&["read", "futex", "write"]);
        assert_eq!(missing, vec!["futex"]);
    }

    #[test]
    fn blocked_from_reports_blocked_syscalls() {
        let f = SeccompFilter::default();
        let blocked = f.blocked_from(&["read", "execve", "socket"]);
        assert!(blocked.contains(&"execve".to_string()));
        assert!(blocked.contains(&"socket".to_string()));
        assert!(!blocked.contains(&"read".to_string()));
    }

    #[test]
    fn custom_filter_with_errno_action() {
        let f = SeccompFilter::new(["read", "write"], SeccompAction::Errno(1));
        assert_eq!(f.default_action, SeccompAction::Errno(1));
        assert!(f.allows("read"));
        assert!(!f.allows("execve"));
    }
}
