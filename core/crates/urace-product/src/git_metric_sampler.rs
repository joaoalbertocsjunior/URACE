//! GitMetricSampler — production `MetricSampler` implementation.
//!
//! Measures real product metrics by running test suites and reading output files.
//!
//! Supported metrics:
//! - `test_pass_rate`     — pytest pass / (pass + fail)
//! - `coverage_pct`      — pytest-cov TOTAL percentage
//! - `error_rate`        — first float in `{repo_path}/error_rate.txt`
//! - `cargo_test_pass_rate` — cargo test ok / (ok + FAILED)
//! - anything else       — returns 0.5 (neutral) with a warning
//!
//! # Security
//! All subprocess calls use `env_clear()` and pass only `PATH` to the child.

use crate::improvement_loop::MetricSampler;

/// Real metric sampler that runs test commands against a repository.
pub struct GitMetricSampler {
    /// Absolute path to the repository root.
    pub repo_path: String,
    /// Subprocess timeout in seconds.
    pub timeout_secs: u64,
}

impl Default for GitMetricSampler {
    fn default() -> Self {
        GitMetricSampler {
            repo_path: ".".into(),
            timeout_secs: 60,
        }
    }
}

impl GitMetricSampler {
    pub fn new(repo_path: impl Into<String>, timeout_secs: u64) -> Self {
        GitMetricSampler {
            repo_path: repo_path.into(),
            timeout_secs,
        }
    }

    // ── metric helpers ────────────────────────────────────────────────────────

    fn sample_test_pass_rate(&self) -> f64 {
        let output = self.run_command(
            "python3",
            &["-m", "pytest", "--tb=no", "-q", &self.repo_path],
        );
        match output {
            None => 0.0,
            Some(text) => parse_pytest_pass_rate(&text),
        }
    }

    fn sample_coverage_pct(&self) -> f64 {
        let cov_arg = format!("--cov={}", self.repo_path);
        let output = self.run_command(
            "python3",
            &[
                "-m",
                "pytest",
                &cov_arg,
                "--cov-report=term-missing",
                "-q",
                &self.repo_path,
            ],
        );
        match output {
            None => 0.0,
            Some(text) => parse_coverage_pct(&text),
        }
    }

    fn sample_error_rate(&self) -> f64 {
        let path = std::path::Path::new(&self.repo_path).join("error_rate.txt");
        match std::fs::read_to_string(&path) {
            Ok(contents) => contents
                .lines()
                .next()
                .and_then(|l| l.trim().parse::<f64>().ok())
                .unwrap_or(0.0),
            Err(_) => 0.0,
        }
    }

    fn sample_cargo_test_pass_rate(&self) -> f64 {
        let manifest = format!("{}/Cargo.toml", self.repo_path);
        let output = self.run_command(
            "cargo",
            &["test", "--manifest-path", &manifest],
        );
        match output {
            None => 0.0,
            Some(text) => parse_cargo_pass_rate(&text),
        }
    }

    /// Run an external command with a wall-clock timeout, capturing combined
    /// stdout + stderr.  Returns `None` on spawn failure or timeout.
    fn run_command(&self, program: &str, args: &[&str]) -> Option<String> {
        use std::process::{Command, Stdio};
        use std::time::{Duration, Instant};

        let path_val =
            std::env::var("PATH").unwrap_or_else(|_| "/usr/bin:/usr/local/bin".into());
        let timeout = Duration::from_secs(self.timeout_secs.max(1));

        let child = Command::new(program)
            .args(args)
            .env_clear()
            .env("PATH", &path_val)
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .stdin(Stdio::null())
            .spawn();

        let child = match child {
            Ok(c) => c,
            Err(e) => {
                tracing::warn!(program, "failed to spawn command: {e}");
                return None;
            }
        };

        let start = Instant::now();
        let child_pid = child.id();

        // Timeout watcher thread.
        let _ = std::thread::spawn(move || {
            std::thread::sleep(timeout);
            #[cfg(unix)]
            unsafe {
                libc::kill(child_pid as libc::pid_t, libc::SIGKILL);
            }
            #[cfg(not(unix))]
            let _ = child_pid;
        });

        let out = match child.wait_with_output() {
            Ok(o) => o,
            Err(e) => {
                tracing::warn!(program, "wait_with_output failed: {e}");
                return None;
            }
        };

        if start.elapsed() >= timeout {
            tracing::warn!(program, timeout_secs = self.timeout_secs, "command timed out");
            return None;
        }

        let stdout = String::from_utf8_lossy(&out.stdout).to_string();
        let stderr = String::from_utf8_lossy(&out.stderr).to_string();
        Some(format!("{stdout}\n{stderr}"))
    }
}

impl MetricSampler for GitMetricSampler {
    fn sample(&self, _product_id: &str, metric: &str) -> f64 {
        match metric {
            "test_pass_rate" => self.sample_test_pass_rate(),
            "coverage_pct" => self.sample_coverage_pct(),
            "error_rate" => self.sample_error_rate(),
            "cargo_test_pass_rate" => self.sample_cargo_test_pass_rate(),
            other => {
                tracing::warn!(metric = other, "unknown metric — returning neutral 0.5");
                0.5
            }
        }
    }
}

// ── parsers ───────────────────────────────────────────────────────────────────

/// Parse pytest `-q` summary output.
///
/// Looks for patterns like `"5 passed"`, `"3 failed"` and computes pass rate.
fn parse_pytest_pass_rate(output: &str) -> f64 {
    let mut passed = 0u64;
    let mut failed = 0u64;

    for line in output.lines() {
        // pytest summary lines contain "X passed" and/or "Y failed"
        for word_pair in line.split_whitespace().collect::<Vec<_>>().windows(2) {
            if let [count_str, label] = word_pair {
                if let Ok(n) = count_str.parse::<u64>() {
                    match *label {
                        "passed" | "passed," => passed += n,
                        "failed" | "failed," => failed += n,
                        _ => {}
                    }
                }
            }
        }
    }

    let total = passed + failed;
    if total == 0 {
        0.0
    } else {
        passed as f64 / total as f64
    }
}

/// Parse pytest-cov `--cov-report=term-missing` output.
///
/// Looks for a line like `"TOTAL   ...   87%"`.
fn parse_coverage_pct(output: &str) -> f64 {
    for line in output.lines() {
        let trimmed = line.trim();
        if trimmed.starts_with("TOTAL") {
            // Last token should be "XX%"
            if let Some(last) = trimmed.split_whitespace().last() {
                let pct_str = last.trim_end_matches('%');
                if let Ok(pct) = pct_str.parse::<f64>() {
                    return pct;
                }
            }
        }
    }
    0.0
}

/// Parse `cargo test` output.
///
/// Counts lines containing `"test ... ok"` and `"test ... FAILED"`.
fn parse_cargo_pass_rate(output: &str) -> f64 {
    let mut ok = 0u64;
    let mut failed = 0u64;

    for line in output.lines() {
        let trimmed = line.trim();
        if trimmed.starts_with("test ") && trimmed.ends_with(" ok") {
            ok += 1;
        } else if trimmed.starts_with("test ") && trimmed.ends_with(" FAILED") {
            failed += 1;
        }
    }

    let total = ok + failed;
    if total == 0 {
        0.0
    } else {
        ok as f64 / total as f64
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // ── parser unit tests (no subprocess needed) ──────────────────────────────

    #[test]
    fn pytest_pass_rate_all_passed() {
        let output = "5 passed in 0.12s";
        assert!((parse_pytest_pass_rate(output) - 1.0).abs() < 1e-9);
    }

    #[test]
    fn pytest_pass_rate_mixed() {
        let output = "3 passed, 1 failed in 0.5s";
        assert!((parse_pytest_pass_rate(output) - 0.75).abs() < 1e-9);
    }

    #[test]
    fn pytest_pass_rate_all_failed() {
        let output = "2 failed in 0.3s";
        assert!((parse_pytest_pass_rate(output) - 0.0).abs() < 1e-9);
    }

    #[test]
    fn pytest_pass_rate_empty() {
        assert_eq!(parse_pytest_pass_rate(""), 0.0);
    }

    #[test]
    fn coverage_pct_parses_total_line() {
        let output = "TOTAL                              500    100    80%\n";
        assert!((parse_coverage_pct(output) - 80.0).abs() < 1e-9);
    }

    #[test]
    fn coverage_pct_no_total_returns_zero() {
        assert_eq!(parse_coverage_pct("some other output"), 0.0);
    }

    #[test]
    fn cargo_pass_rate_mixed() {
        let output = "test foo ... ok\ntest bar ... FAILED\ntest baz ... ok\n";
        assert!((parse_cargo_pass_rate(output) - 2.0 / 3.0).abs() < 1e-6);
    }

    #[test]
    fn cargo_pass_rate_all_ok() {
        let output = "test a ... ok\ntest b ... ok\n";
        assert!((parse_cargo_pass_rate(output) - 1.0).abs() < 1e-9);
    }

    #[test]
    fn cargo_pass_rate_no_tests() {
        assert_eq!(parse_cargo_pass_rate("no tests found"), 0.0);
    }

    // ── error_rate reads file ─────────────────────────────────────────────────

    #[test]
    fn error_rate_reads_file() {
        use std::io::Write;
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("error_rate.txt");
        let mut f = std::fs::File::create(&path).unwrap();
        writeln!(f, "0.123").unwrap();

        let sampler = GitMetricSampler::new(dir.path().to_str().unwrap(), 5);
        let rate = sampler.sample("prod", "error_rate");
        assert!((rate - 0.123).abs() < 1e-6);
    }

    #[test]
    fn error_rate_missing_file_returns_zero() {
        let sampler = GitMetricSampler::new("/nonexistent/path", 5);
        assert_eq!(sampler.sample("prod", "error_rate"), 0.0);
    }

    // ── unknown metric returns 0.5 ────────────────────────────────────────────

    #[test]
    fn unknown_metric_returns_neutral() {
        let sampler = GitMetricSampler::default();
        assert!((sampler.sample("prod", "p99_latency_ms") - 0.5).abs() < 1e-9);
    }
}
