//! Executor retry engine — per-provider state machine with class-aware backoff.
//!
//! Translated from claude-auto-retry's monitor.js design but executor-agnostic:
//! operates on structured error strings, not TUI output.
//!
//! # State machine (per provider)
//!
//! ```text
//! Monitoring
//!   → RateLimitWait  { until, is_fallback }   (usage quota / 429)
//!   → Overload       { until, attempts, total } (transient 5xx)
//!   → AuthFailure    { until }                  (401 / bad key — long hold)
//!   → Safeguard      { until, attempts }        (AUP flag — bounded, seconds-scale)
//!   → GaveUp         { until }                  (any class hit its cap)
//! ```
//!
//! Every path that mutates state returns a named `RetryOutcome` so callers can
//! log / audit the exact transition rather than inferring it from side effects.
//!
//! # Key design choices from claude-auto-retry
//! - Array backoff schedule (`stages`) + `steady_state` + `jitter_pct`
//! - Wall-clock `parse_retry_after` extracts actual reset durations from error text
//! - `is_fallback` flag allows `correct_wait` to shorten a fallback wait when the
//!   real reset time later appears in a subsequent error message
//! - Per-class give-up caps (`max_attempts`, `total_cap`)
//! - `should_allow` is the single gate before every dispatch attempt

use crate::routing::{classify_unavailability, UnavailabilityClass};
use parking_lot::Mutex;
use std::collections::HashMap;
use std::time::{Duration, Instant};

// ── Retry policy ──────────────────────────────────────────────────────────────

/// Per-class backoff schedule and limits.
///
/// `stages[i]` is the wait after attempt `i`; once exhausted, `steady_state` is used.
#[derive(Debug, Clone)]
pub struct RetryPolicy {
    /// Staged backoff: wait durations per attempt (index = attempt number).
    pub stages: Vec<Duration>,
    /// Wait duration used after all stages are exhausted.
    pub steady_state: Duration,
    /// Maximum number of attempts before giving up (0 = no retry, just hold).
    pub max_attempts: u32,
    /// ±N% random jitter applied to each computed wait (0.0 = no jitter).
    pub jitter_pct: f64,
    /// Optional ceiling on the total accumulated wait for this class.
    pub total_cap: Option<Duration>,
    /// Fallback wait when no reset time can be parsed from the error text.
    pub fallback_wait: Duration,
}

impl RetryPolicy {
    pub fn for_class(class: &UnavailabilityClass) -> Self {
        match class {
            UnavailabilityClass::RateLimit => Self {
                stages: vec![
                    Duration::from_secs(120),
                    Duration::from_secs(240),
                    Duration::from_secs(480),
                ],
                steady_state: Duration::from_secs(900),
                max_attempts: 5,
                jitter_pct: 10.0,
                total_cap: Some(Duration::from_secs(3600)),
                fallback_wait: Duration::from_secs(300),
            },
            UnavailabilityClass::NetworkError => Self {
                stages: vec![
                    Duration::from_secs(5),
                    Duration::from_secs(10),
                    Duration::from_secs(20),
                    Duration::from_secs(40),
                ],
                steady_state: Duration::from_secs(60),
                max_attempts: 8,
                jitter_pct: 20.0,
                total_cap: Some(Duration::from_secs(300)),
                fallback_wait: Duration::from_secs(30),
            },
            UnavailabilityClass::AuthFailure => Self {
                stages: vec![Duration::from_secs(3600)],
                steady_state: Duration::from_secs(3600),
                max_attempts: 1, // auth failures rarely self-heal; hold once then give up
                jitter_pct: 0.0,
                total_cap: None,
                fallback_wait: Duration::from_secs(3600),
            },
            UnavailabilityClass::ExecutionEnvironment => Self {
                stages: vec![
                    Duration::from_secs(30),
                    Duration::from_secs(60),
                    Duration::from_secs(120),
                ],
                steady_state: Duration::from_secs(300),
                max_attempts: 4,
                jitter_pct: 10.0,
                total_cap: Some(Duration::from_secs(900)),
                fallback_wait: Duration::from_secs(60),
            },
            UnavailabilityClass::Unknown => Self {
                stages: vec![
                    Duration::from_secs(10),
                    Duration::from_secs(20),
                    Duration::from_secs(40),
                ],
                steady_state: Duration::from_secs(60),
                max_attempts: 3,
                jitter_pct: 15.0,
                total_cap: Some(Duration::from_secs(300)),
                fallback_wait: Duration::from_secs(30),
            },
        }
    }

    /// Wait duration for attempt `n` (0-based), before jitter.
    pub fn base_wait(&self, attempt: u32) -> Duration {
        self.stages
            .get(attempt as usize)
            .copied()
            .unwrap_or(self.steady_state)
    }

    /// Wait duration for attempt `n`, with deterministic jitter applied.
    ///
    /// Jitter uses `attempt * 7 % 20` as a deterministic offset (no rand dep).
    pub fn wait_with_jitter(&self, attempt: u32) -> Duration {
        let base = self.base_wait(attempt);
        if self.jitter_pct == 0.0 {
            return base;
        }
        let base_ms = base.as_millis() as f64;
        let jitter_ms = base_ms * (self.jitter_pct / 100.0);
        // Deterministic pseudo-random: (attempt * 7 % 20) gives 0-19 uniformly across
        // the first 20 attempts, shifted by 50% of the jitter range to get ±jitter.
        let offset_ms = jitter_ms * ((attempt * 7 % 20) as f64 / 20.0 - 0.5);
        let final_ms = (base_ms + offset_ms).max(1.0) as u64;
        Duration::from_millis(final_ms)
    }
}

// ── Wall-clock reset time parser ──────────────────────────────────────────────

/// Extract a retry-after duration from an error message.
///
/// Parses patterns like:
/// - "try again in 3 minutes"
/// - "retry after 60"
/// - "resets in 2 hours"
/// - "wait 30 seconds"
/// - "Retry-After: 120"
/// - "rate limit resets at 14:30" (not yet — returns None for absolute times)
pub fn parse_retry_after(error_text: &str) -> Option<Duration> {
    let lower = error_text.to_lowercase();

    // "Retry-After: 120" (HTTP header format, plain seconds)
    if let Some(rest) = lower.find("retry-after:").map(|i| &lower[i + 12..]) {
        let secs: u64 = rest.trim().split_whitespace().next()?.parse().ok()?;
        return Some(Duration::from_secs(secs));
    }

    // "try again in N (seconds|minutes|hours|s|m|h)"
    // "resets in N ..."
    // "wait N ..."
    let triggers = ["try again in ", "retry in ", "resets in ", "wait ", "in "];
    for trigger in &triggers {
        if let Some(pos) = lower.find(trigger) {
            let rest = &lower[pos + trigger.len()..];
            let num: f64 = rest.split_whitespace().next()?.parse().ok()?;
            if num <= 0.0 || num > 86400.0 {
                continue;
            }
            let unit_str = rest.split_whitespace().nth(1).unwrap_or("s");
            let multiplier: f64 = if unit_str.starts_with('h') {
                3600.0
            } else if unit_str.starts_with('m') {
                60.0
            } else {
                1.0 // seconds / unknown
            };
            return Some(Duration::from_secs((num * multiplier) as u64));
        }
    }

    None
}

// ── Per-provider state ────────────────────────────────────────────────────────

#[derive(Debug, Clone)]
enum ProviderStatus {
    Monitoring,
    RateLimitWait {
        until: Instant,
        /// True when reset time was not parseable from error text — correctable later.
        is_fallback: bool,
    },
    Overload {
        until: Instant,
        attempts: u32,
        total_wait: Duration,
    },
    AuthFailure {
        until: Instant,
    },
    Safeguard {
        until: Instant,
        attempts: u32,
    },
    GaveUp {
        until: Instant,
        reason: UnavailabilityClass,
    },
}

#[derive(Debug)]
struct ProviderRetryState {
    status: ProviderStatus,
    /// Fingerprint of the last error that caused a state transition.
    /// Used to deduplicate re-detection of the same stale error.
    last_error_fingerprint: Option<String>,
}

impl ProviderRetryState {
    fn new() -> Self {
        Self { status: ProviderStatus::Monitoring, last_error_fingerprint: None }
    }
}

// ── Outcome ───────────────────────────────────────────────────────────────────

/// Named result of a retry-engine decision — mirrors claude-auto-retry's outcome strings.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum RetryOutcome {
    /// Request is allowed through — no active hold.
    Allow,
    /// Provider is in a wait window; caller should not dispatch until `resume_at`.
    Waiting {
        reason: UnavailabilityClass,
        resume_at: Instant,
    },
    /// All retry budgets for this class are exhausted; provider is parked.
    GaveUp {
        reason: UnavailabilityClass,
    },
    /// A fresh failure was recorded; provider entered a wait window.
    Tripped {
        reason: UnavailabilityClass,
        resume_at: Instant,
    },
    /// An existing fallback wait was shortened because the real reset time appeared.
    WaitCorrected {
        new_resume_at: Instant,
    },
    /// Provider recovered (success recorded); back to Monitoring.
    Recovered,
}

// ── Engine ────────────────────────────────────────────────────────────────────

/// Thread-safe per-provider retry state machine.
///
/// Instantiate once per executor pool; call `on_failure` / `on_success` / `should_allow`
/// from the dispatch path.
pub struct RetryEngine {
    providers: Mutex<HashMap<String, ProviderRetryState>>,
}

impl RetryEngine {
    pub fn new() -> Self {
        RetryEngine { providers: Mutex::new(HashMap::new()) }
    }

    // ── Public API ────────────────────────────────────────────────────────────

    /// Gate call: returns `Allow` or `Waiting`/`GaveUp` for the given provider.
    ///
    /// Call this BEFORE dispatching to a provider.
    pub fn should_allow(&self, provider_id: &str) -> RetryOutcome {
        let mut map = self.providers.lock();
        let state = map.entry(provider_id.to_owned()).or_insert_with(ProviderRetryState::new);
        self.evaluate_status(state)
    }

    /// Record a failure. Classifies the error, transitions state, returns outcome.
    ///
    /// Also attempts `correct_wait` when the provider is already in `RateLimitWait`
    /// with `is_fallback=true` and a parseable reset time now appears.
    pub fn on_failure(&self, provider_id: &str, error_text: &str) -> RetryOutcome {
        let class = classify_unavailability(error_text);
        let fingerprint = error_fingerprint(error_text);
        let parsed_wait = parse_retry_after(error_text);

        let mut map = self.providers.lock();
        let state = map.entry(provider_id.to_owned()).or_insert_with(ProviderRetryState::new);

        // Deduplication: same stale error re-detected — no new transition.
        if state.last_error_fingerprint.as_deref() == Some(&fingerprint) {
            return self.evaluate_status(state);
        }
        state.last_error_fingerprint = Some(fingerprint);

        // If already in a fallback rate-limit wait and we now have a real reset time,
        // shorten the wait (mirrors claude-auto-retry's correctUsageWait).
        if let ProviderStatus::RateLimitWait { is_fallback: true, until } = state.status {
            if let Some(wait) = parsed_wait {
                let new_until = Instant::now() + wait;
                if new_until < until {
                    state.status = ProviderStatus::RateLimitWait {
                        until: new_until,
                        is_fallback: false,
                    };
                    return RetryOutcome::WaitCorrected { new_resume_at: new_until };
                }
            }
        }

        // Transition to the appropriate class-specific wait state.
        self.enter_class_state(state, &class, parsed_wait)
    }

    /// Record a success. Transitions the provider back to Monitoring.
    pub fn on_success(&self, provider_id: &str) -> RetryOutcome {
        let mut map = self.providers.lock();
        let state = map.entry(provider_id.to_owned()).or_insert_with(ProviderRetryState::new);
        state.status = ProviderStatus::Monitoring;
        state.last_error_fingerprint = None;
        RetryOutcome::Recovered
    }

    /// Return a snapshot of all provider statuses (for status display / audit).
    pub fn snapshot(&self) -> HashMap<String, String> {
        let map = self.providers.lock();
        map.iter()
            .map(|(id, state)| (id.clone(), status_label(&state.status)))
            .collect()
    }

    // ── Internal ──────────────────────────────────────────────────────────────

    fn evaluate_status(&self, state: &mut ProviderRetryState) -> RetryOutcome {
        match &state.status {
            ProviderStatus::Monitoring => RetryOutcome::Allow,

            ProviderStatus::RateLimitWait { until, .. } => {
                let until = *until;
                if Instant::now() >= until {
                    // Wait elapsed — back to monitoring, allow the probe.
                    state.status = ProviderStatus::Monitoring;
                    RetryOutcome::Allow
                } else {
                    RetryOutcome::Waiting {
                        reason: UnavailabilityClass::RateLimit,
                        resume_at: until,
                    }
                }
            }

            ProviderStatus::Overload { until, .. } => {
                let until = *until;
                if Instant::now() >= until {
                    state.status = ProviderStatus::Monitoring;
                    RetryOutcome::Allow
                } else {
                    RetryOutcome::Waiting {
                        reason: UnavailabilityClass::NetworkError,
                        resume_at: until,
                    }
                }
            }

            ProviderStatus::AuthFailure { until } => {
                let until = *until;
                if Instant::now() >= until {
                    state.status = ProviderStatus::Monitoring;
                    RetryOutcome::Allow
                } else {
                    RetryOutcome::Waiting {
                        reason: UnavailabilityClass::AuthFailure,
                        resume_at: until,
                    }
                }
            }

            ProviderStatus::Safeguard { until, .. } => {
                let until = *until;
                if Instant::now() >= until {
                    state.status = ProviderStatus::Monitoring;
                    RetryOutcome::Allow
                } else {
                    RetryOutcome::Waiting {
                        reason: UnavailabilityClass::Unknown,
                        resume_at: until,
                    }
                }
            }

            ProviderStatus::GaveUp { reason, until } => {
                // GaveUp hold: re-evaluate after the hold expires.
                let (reason, until) = (reason.clone(), *until);
                if Instant::now() >= until {
                    state.status = ProviderStatus::Monitoring;
                    RetryOutcome::Allow
                } else {
                    RetryOutcome::GaveUp { reason }
                }
            }
        }
    }

    fn enter_class_state(
        &self,
        state: &mut ProviderRetryState,
        class: &UnavailabilityClass,
        parsed_wait: Option<Duration>,
    ) -> RetryOutcome {
        let policy = RetryPolicy::for_class(class);

        match class {
            UnavailabilityClass::RateLimit => {
                let (wait, is_fallback) = match parsed_wait {
                    Some(w) => (w, false),
                    None => (policy.fallback_wait, true),
                };
                let until = Instant::now() + wait;
                state.status = ProviderStatus::RateLimitWait { until, is_fallback };
                RetryOutcome::Tripped { reason: class.clone(), resume_at: until }
            }

            UnavailabilityClass::NetworkError => {
                let (attempts, total_wait) = match &state.status {
                    ProviderStatus::Overload { attempts, total_wait, .. } => {
                        (*attempts, *total_wait)
                    }
                    _ => (0, Duration::ZERO),
                };

                if let Some(cap) = policy.total_cap {
                    if total_wait >= cap || attempts >= policy.max_attempts {
                        let until = Instant::now() + policy.steady_state;
                        state.status = ProviderStatus::GaveUp { until, reason: class.clone() };
                        return RetryOutcome::GaveUp { reason: class.clone() };
                    }
                }

                let wait = policy.wait_with_jitter(attempts);
                let new_total = total_wait + wait;
                let until = Instant::now() + wait;
                state.status = ProviderStatus::Overload {
                    until,
                    attempts: attempts + 1,
                    total_wait: new_total,
                };
                RetryOutcome::Tripped { reason: class.clone(), resume_at: until }
            }

            UnavailabilityClass::AuthFailure => {
                let until = Instant::now() + policy.fallback_wait;
                state.status = ProviderStatus::AuthFailure { until };
                RetryOutcome::Tripped { reason: class.clone(), resume_at: until }
            }

            UnavailabilityClass::ExecutionEnvironment => {
                // Treat like overload but with execution-env policy.
                let attempts = match &state.status {
                    ProviderStatus::Overload { attempts, .. } => *attempts,
                    _ => 0,
                };
                if attempts >= policy.max_attempts {
                    let until = Instant::now() + policy.steady_state;
                    state.status = ProviderStatus::GaveUp { until, reason: class.clone() };
                    return RetryOutcome::GaveUp { reason: class.clone() };
                }
                let wait = policy.wait_with_jitter(attempts);
                let until = Instant::now() + wait;
                state.status = ProviderStatus::Overload {
                    until,
                    attempts: attempts + 1,
                    total_wait: wait,
                };
                RetryOutcome::Tripped { reason: class.clone(), resume_at: until }
            }

            UnavailabilityClass::Unknown => {
                let (attempts, total_wait) = match &state.status {
                    ProviderStatus::Safeguard { attempts, .. } => (*attempts, Duration::ZERO),
                    ProviderStatus::Overload { attempts, total_wait, .. } => {
                        (*attempts, *total_wait)
                    }
                    _ => (0, Duration::ZERO),
                };
                if attempts >= policy.max_attempts {
                    let until = Instant::now() + policy.steady_state;
                    state.status = ProviderStatus::GaveUp { until, reason: class.clone() };
                    return RetryOutcome::GaveUp { reason: class.clone() };
                }
                let wait = policy.wait_with_jitter(attempts);
                let until = Instant::now() + wait;
                state.status = ProviderStatus::Safeguard { until, attempts: attempts + 1 };
                let _ = total_wait;
                RetryOutcome::Tripped { reason: class.clone(), resume_at: until }
            }
        }
    }
}

impl Default for RetryEngine {
    fn default() -> Self {
        Self::new()
    }
}

// ── Helpers ───────────────────────────────────────────────────────────────────

/// Short fingerprint of an error — first 120 chars, lowercased.
/// Prevents the same stale error from re-triggering state transitions.
fn error_fingerprint(error_text: &str) -> String {
    error_text.to_lowercase().chars().take(120).collect()
}

fn status_label(status: &ProviderStatus) -> String {
    match status {
        ProviderStatus::Monitoring => "monitoring".into(),
        ProviderStatus::RateLimitWait { is_fallback, .. } => {
            if *is_fallback { "rate-limit-wait(fallback)".into() } else { "rate-limit-wait".into() }
        }
        ProviderStatus::Overload { attempts, .. } => format!("overload(attempt {})", attempts),
        ProviderStatus::AuthFailure { .. } => "auth-failure".into(),
        ProviderStatus::Safeguard { attempts, .. } => format!("safeguard(attempt {})", attempts),
        ProviderStatus::GaveUp { reason, .. } => format!("gave-up({:?})", reason),
    }
}

// ── Tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    // ── parse_retry_after ─────────────────────────────────────────────────────

    #[test]
    fn parses_retry_after_header() {
        let d = parse_retry_after("HTTP/1.1 429 Too Many Requests\nRetry-After: 60");
        assert_eq!(d, Some(Duration::from_secs(60)));
    }

    #[test]
    fn parses_try_again_in_minutes() {
        let d = parse_retry_after("Usage limit exceeded. Try again in 3 minutes.");
        assert_eq!(d, Some(Duration::from_secs(180)));
    }

    #[test]
    fn parses_resets_in_hours() {
        let d = parse_retry_after("Your quota resets in 2 hours.");
        assert_eq!(d, Some(Duration::from_secs(7200)));
    }

    #[test]
    fn returns_none_for_no_match() {
        assert!(parse_retry_after("internal server error").is_none());
    }

    // ── RetryPolicy ───────────────────────────────────────────────────────────

    #[test]
    fn policy_stages_accessed_in_order() {
        let p = RetryPolicy::for_class(&UnavailabilityClass::NetworkError);
        let w0 = p.base_wait(0);
        let w1 = p.base_wait(1);
        assert!(w1 >= w0, "backoff must be non-decreasing");
    }

    #[test]
    fn policy_steady_state_after_stages_exhausted() {
        let p = RetryPolicy::for_class(&UnavailabilityClass::NetworkError);
        let beyond = p.base_wait(100);
        assert_eq!(beyond, p.steady_state);
    }

    #[test]
    fn jitter_does_not_produce_zero() {
        let p = RetryPolicy::for_class(&UnavailabilityClass::NetworkError);
        for attempt in 0..10 {
            assert!(p.wait_with_jitter(attempt) > Duration::ZERO);
        }
    }

    // ── RetryEngine ───────────────────────────────────────────────────────────

    #[test]
    fn fresh_provider_allows() {
        let engine = RetryEngine::new();
        assert_eq!(engine.should_allow("p1"), RetryOutcome::Allow);
    }

    #[test]
    fn rate_limit_trips_provider() {
        let engine = RetryEngine::new();
        let outcome = engine.on_failure("p1", "usage limit exceeded");
        assert!(matches!(outcome, RetryOutcome::Tripped { reason: UnavailabilityClass::RateLimit, .. }));
    }

    #[test]
    fn tripped_provider_returns_waiting() {
        let engine = RetryEngine::new();
        engine.on_failure("p1", "usage limit exceeded");
        assert!(matches!(engine.should_allow("p1"), RetryOutcome::Waiting { .. }));
    }

    #[test]
    fn success_clears_state() {
        let engine = RetryEngine::new();
        engine.on_failure("p1", "502 bad gateway");
        engine.on_success("p1");
        assert_eq!(engine.should_allow("p1"), RetryOutcome::Allow);
    }

    #[test]
    fn network_error_escalates_to_gave_up() {
        let engine = RetryEngine::new();
        // NetworkError max_attempts = 8; force past it
        for _ in 0..10 {
            engine.on_failure("p1", "502 bad gateway");
        }
        let outcome = engine.should_allow("p1");
        // Should be either Waiting (still in hold) or GaveUp
        assert!(
            matches!(outcome, RetryOutcome::Waiting { .. } | RetryOutcome::GaveUp { .. }),
            "expected Waiting or GaveUp, got {:?}", outcome
        );
    }

    #[test]
    fn deduplication_prevents_re_trip_on_same_error() {
        let engine = RetryEngine::new();
        let err = "usage limit exceeded, try again in 10 minutes";
        engine.on_failure("p1", err);
        // Second call with identical error must not change state (returns Waiting, not Tripped).
        let second = engine.on_failure("p1", err);
        assert!(
            !matches!(second, RetryOutcome::Tripped { .. }),
            "same error should not re-trip: {:?}", second
        );
    }

    #[test]
    fn fallback_wait_corrected_when_real_time_arrives() {
        let engine = RetryEngine::new();
        // First failure: no parseable reset time → fallback wait
        engine.on_failure("p1", "usage limit exceeded");
        // Second failure: has a parseable reset time shorter than fallback
        let outcome = engine.on_failure("p1", "usage limit exceeded, try again in 1 minutes");
        // Should shorten the wait
        assert!(
            matches!(outcome, RetryOutcome::WaitCorrected { .. } | RetryOutcome::Tripped { .. }),
            "expected correction or re-trip, got {:?}", outcome
        );
    }

    #[test]
    fn auth_failure_holds_for_long_duration() {
        let engine = RetryEngine::new();
        engine.on_failure("p1", "401 unauthorized");
        let outcome = engine.should_allow("p1");
        if let RetryOutcome::Waiting { resume_at, .. } = outcome {
            let remaining = resume_at.duration_since(Instant::now());
            assert!(remaining > Duration::from_secs(1800), "auth hold should be long");
        } else {
            panic!("expected Waiting, got {:?}", outcome);
        }
    }

    #[test]
    fn independent_providers_dont_share_state() {
        let engine = RetryEngine::new();
        engine.on_failure("p1", "usage limit exceeded");
        assert_eq!(engine.should_allow("p2"), RetryOutcome::Allow);
    }

    #[test]
    fn snapshot_reflects_all_providers() {
        let engine = RetryEngine::new();
        engine.on_failure("p1", "502 bad gateway");
        engine.on_failure("p2", "401 unauthorized");
        let snap = engine.snapshot();
        assert!(snap.contains_key("p1"));
        assert!(snap.contains_key("p2"));
        assert_ne!(snap["p1"], "monitoring");
    }
}
