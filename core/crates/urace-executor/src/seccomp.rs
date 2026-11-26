//! M81 — Seccomp-BPF syscall filtering for Linux executor sandboxes.
//!
//! Defines the minimal allowed syscall set for URACE executor child processes
//! and a `SeccompFilter` struct that validates or generates a filter profile.
//!
//! **Platform note**: actual `seccomp(2)` / `prctl(PR_SET_SECCOMP)` calls
//! require Linux + the `libseccomp` crate or inline BPF assembly.  This module
//! provides the allowlist data structure and profile-validation logic.
//! Real enforcement is wired via the `linux-sandbox` feature flag when the
//! `libseccomp` crate is available.

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
