//! Circuit breaker for executor provider health tracking.
//!
//! Ported from `runtime/urace/circuit_breaker.py`.
//!
//! State machine:
//!   Closed → Open (after `failure_threshold` consecutive failures)
//!   Open → HalfOpen (after `reset_timeout_secs` seconds)
//!   HalfOpen → Closed (1 success)
//!   HalfOpen → Open (1 failure)
//!
//! Invariants:
//! - 5 failures → Open
//! - 60 s reset → HalfOpen
//! - 1 success → Closed
//! - Only called from CLI commands, never from the hot execution path.

use std::time::{Duration, Instant};
use urace_executor::routing::UnavailabilityClass;

/// Number of consecutive failures that trip the breaker (§spec default).
pub const DEFAULT_FAILURE_THRESHOLD: u32 = 5;

/// Seconds in Open state before moving to HalfOpen.
pub const DEFAULT_RESET_TIMEOUT_SECS: u64 = 60;

/// Compute exponential backoff duration for a given `UnavailabilityClass` and attempt count.
///
/// Each class carries its own base, max, and multiplier so that rate-limit errors
/// get longer cooling-off periods than transient network errors.
/// Jitter is deterministic (no rand dep): `attempt * 7 % 20` seconds.
pub fn backoff_secs(class: &UnavailabilityClass, attempt: u32) -> u64 {
    let (base, max, multiplier): (f64, f64, f64) = match class {
        UnavailabilityClass::RateLimit            => (120.0, 1800.0, 2.0),
        UnavailabilityClass::NetworkError         => (30.0,  300.0,  2.0),
        UnavailabilityClass::AuthFailure          => (3600.0, 3600.0, 1.0),
        UnavailabilityClass::ExecutionEnvironment => (300.0, 1800.0, 1.5),
        UnavailabilityClass::Unknown              => (60.0,  300.0,  2.0),
    };
    let raw = base * multiplier.powi(attempt as i32);
    let capped = raw.min(max) as u64;
    let jitter = (attempt * 7 % 20) as u64;
    capped.saturating_add(jitter).min(max as u64)
}

/// Circuit breaker state machine states.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum BreakerState {
    /// Normal operation — requests pass through.
    Closed,
    /// Tripped — requests are rejected immediately.
    Open,
    /// Trial state — one probe request is allowed.
    HalfOpen,
}

/// A circuit breaker for a single provider.
pub struct CircuitBreaker {
    /// How many consecutive failures are needed to trip.
    pub failure_threshold: u32,
    /// How long to stay Open before entering HalfOpen.
    pub reset_timeout: Duration,

    state: BreakerState,
    consecutive_failures: u32,
    opened_at: Option<Instant>,
}

impl CircuitBreaker {
    /// Create with default thresholds (5 failures, 60 s reset).
    pub fn new() -> Self {
        Self::with_config(DEFAULT_FAILURE_THRESHOLD, DEFAULT_RESET_TIMEOUT_SECS)
    }

    /// Create with custom thresholds.
    pub fn with_config(failure_threshold: u32, reset_timeout_secs: u64) -> Self {
        CircuitBreaker {
            failure_threshold,
            reset_timeout: Duration::from_secs(reset_timeout_secs),
            state: BreakerState::Closed,
            consecutive_failures: 0,
            opened_at: None,
        }
    }

    /// Current observable state (may transition from Open → HalfOpen by time).
    pub fn state(&mut self) -> BreakerState {
        if self.state == BreakerState::Open {
            if let Some(opened) = self.opened_at {
                if opened.elapsed() >= self.reset_timeout {
                    self.state = BreakerState::HalfOpen;
                }
            }
        }
        self.state
    }

    /// Whether a request should be allowed through right now.
    pub fn allow_request(&mut self) -> bool {
        matches!(self.state(), BreakerState::Closed | BreakerState::HalfOpen)
    }

    /// Record a successful call. Resets failure counter; Closed from HalfOpen.
    pub fn record_success(&mut self) {
        self.consecutive_failures = 0;
        self.opened_at = None;
        self.state = BreakerState::Closed;
    }

    /// Record a failed call. May transition Closed → Open or HalfOpen → Open.
    pub fn record_failure(&mut self) {
        self.consecutive_failures += 1;
        if self.state == BreakerState::HalfOpen
            || self.consecutive_failures >= self.failure_threshold
        {
            self.state = BreakerState::Open;
            self.opened_at = Some(Instant::now());
        }
    }

    /// Record a failure with an explicit unavailability class.
    ///
    /// Extends `record_failure` with class-based exponential backoff: the
    /// reset timeout is overridden to `backoff_secs(class, consecutive_failures)`
    /// so that rate-limit events cool off much longer than transient network blips.
    pub fn record_failure_classified(&mut self, class: &UnavailabilityClass) {
        self.record_failure();
        let secs = backoff_secs(class, self.consecutive_failures);
        self.reset_timeout = Duration::from_secs(secs);
    }

    /// Current reset timeout in seconds (useful for status display).
    pub fn retry_in_secs(&self) -> u64 {
        self.reset_timeout.as_secs()
    }

    /// Force reset to Closed (operator action — mirrors Python `reset()`).
    pub fn reset(&mut self) {
        self.state = BreakerState::Closed;
        self.consecutive_failures = 0;
        self.opened_at = None;
    }

    /// Return a snapshot of current metrics (read-only).
    pub fn status(&self) -> BreakerStatus {
        BreakerStatus {
            state: self.state,
            consecutive_failures: self.consecutive_failures,
            failure_threshold: self.failure_threshold,
            tripped: self.consecutive_failures >= self.failure_threshold,
        }
    }
}

impl Default for CircuitBreaker {
    fn default() -> Self {
        Self::new()
    }
}

/// Read-only snapshot from [`CircuitBreaker::status`].
#[derive(Debug, Clone)]
pub struct BreakerStatus {
    pub state: BreakerState,
    pub consecutive_failures: u32,
    pub failure_threshold: u32,
    pub tripped: bool,
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::thread;

    #[test]
    fn starts_closed() {
        let mut cb = CircuitBreaker::new();
        assert_eq!(cb.state(), BreakerState::Closed);
        assert!(cb.allow_request());
    }

    #[test]
    fn trips_after_threshold_failures() {
        let mut cb = CircuitBreaker::new();
        for _ in 0..DEFAULT_FAILURE_THRESHOLD {
            assert_eq!(cb.state(), BreakerState::Closed);
            cb.record_failure();
        }
        assert_eq!(cb.state(), BreakerState::Open);
        assert!(!cb.allow_request());
    }

    #[test]
    fn does_not_trip_before_threshold() {
        let mut cb = CircuitBreaker::with_config(5, 60);
        for _ in 0..4 {
            cb.record_failure();
        }
        assert_eq!(cb.state(), BreakerState::Closed);
    }

    #[test]
    fn success_resets_failure_counter() {
        let mut cb = CircuitBreaker::new();
        for _ in 0..4 {
            cb.record_failure();
        }
        cb.record_success();
        // Another 4 failures — still below threshold since counter was reset
        for _ in 0..4 {
            cb.record_failure();
        }
        assert_eq!(cb.state(), BreakerState::Closed);
    }

    #[test]
    fn transitions_open_to_halfopen_after_timeout() {
        // Use 0 s timeout — elapsed() >= Duration::ZERO is always true so the
        // very first call to state() after record_failure() transitions to HalfOpen.
        let mut cb = CircuitBreaker::with_config(1, 0);
        cb.record_failure();
        // Don't assert Open here — with 0 s reset, state() immediately transitions.
        thread::sleep(Duration::from_millis(1));
        assert_eq!(cb.state(), BreakerState::HalfOpen);
        assert!(cb.allow_request());
    }

    #[test]
    fn halfopen_success_closes() {
        let mut cb = CircuitBreaker::with_config(1, 0);
        cb.record_failure();
        thread::sleep(Duration::from_millis(1));
        assert_eq!(cb.state(), BreakerState::HalfOpen);
        cb.record_success();
        assert_eq!(cb.state(), BreakerState::Closed);
    }

    #[test]
    fn halfopen_failure_reopens() {
        // Use a 60 s reset so the breaker stays Open after the second failure.
        let mut cb = CircuitBreaker::with_config(1, 60);
        cb.record_failure();
        // Force into HalfOpen by directly mutating (simulates timeout elapsed)
        cb.state = BreakerState::HalfOpen;
        assert_eq!(cb.state(), BreakerState::HalfOpen);
        cb.record_failure();
        // After a failure in HalfOpen, the breaker must reopen.
        // Check internal state directly (status() doesn't call the time-transition path).
        assert_eq!(cb.status().state, BreakerState::Open);
    }

    #[test]
    fn reset_clears_state() {
        let mut cb = CircuitBreaker::new();
        for _ in 0..DEFAULT_FAILURE_THRESHOLD {
            cb.record_failure();
        }
        assert_eq!(cb.state(), BreakerState::Open);
        cb.reset();
        assert_eq!(cb.state(), BreakerState::Closed);
        assert!(cb.allow_request());
    }

    #[test]
    fn rate_limit_backoff_grows_with_attempts() {
        let delays: Vec<u64> = (0..4).map(|a| backoff_secs(&UnavailabilityClass::RateLimit, a)).collect();
        for w in delays.windows(2) {
            assert!(w[1] >= w[0], "backoff must be non-decreasing: {:?}", delays);
        }
    }

    #[test]
    fn classified_failure_sets_longer_timeout_than_default() {
        let mut cb = CircuitBreaker::with_config(1, DEFAULT_RESET_TIMEOUT_SECS);
        cb.record_failure_classified(&UnavailabilityClass::RateLimit);
        assert!(cb.retry_in_secs() > DEFAULT_RESET_TIMEOUT_SECS);
    }

    #[test]
    fn status_reports_tripped() {
        let mut cb = CircuitBreaker::new();
        for _ in 0..DEFAULT_FAILURE_THRESHOLD {
            cb.record_failure();
        }
        let s = cb.status();
        assert!(s.tripped);
        assert_eq!(s.consecutive_failures, DEFAULT_FAILURE_THRESHOLD);
    }
}
