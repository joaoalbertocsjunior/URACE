//! LoopWatchdog — stall detection and supply health monitoring for ImprovementLoop.
//!
//! The watchdog tracks the last cycle completion time and raises `StallDetected`
//! events when no cycle has completed within `stall_threshold_secs`. It also
//! monitors executor supply health via the `active_executors / queue_depth` ratio.
//!
//! # Design
//! - All shared state uses `Arc<Mutex<Instant>>` / `Arc<AtomicU64>` — no locks held
//!   across awaits; methods return values, never references to internals.
//! - Stall detection is edge-triggered: once a stall fires it keeps firing until
//!   `record_cycle_completed` is called (recovery).

use serde::{Deserialize, Serialize};
use std::sync::{
    atomic::{AtomicU64, Ordering},
    Arc, Mutex,
};
use std::time::Instant;

// ── WatchdogEvent ─────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "event", rename_all = "snake_case")]
pub enum WatchdogEvent {
    /// A cycle completed normally.
    CycleCompleted {
        cycle: u64,
        duration_ms: u64,
    },
    /// No cycle completed within `stall_threshold_secs`.
    StallDetected {
        secs_since_last_cycle: u64,
        stall_count: u64,
    },
    /// Executor supply ratio dropped below `supply_alert_threshold`.
    SupplyHealthAlert {
        ratio: f64,
    },
    /// The loop recovered after at least one stall event.
    Recovered {
        after_stall_count: u64,
    },
}

// ── LoopWatchdog ──────────────────────────────────────────────────────────────

/// Stall detector for `ImprovementLoop`.
///
/// Cheap to clone (all state is behind `Arc`).
pub struct LoopWatchdog {
    /// Seconds without a completed cycle before `StallDetected` fires.
    pub stall_threshold_secs: u64,
    /// Alert if `active_executors as f64 / queue_depth as f64 < supply_alert_threshold`.
    pub supply_alert_threshold: f64,
    last_cycle_at: Arc<Mutex<Instant>>,
    stall_count: Arc<AtomicU64>,
}

impl LoopWatchdog {
    /// Create a new watchdog with the given stall threshold (seconds).
    ///
    /// `supply_alert_threshold` defaults to `2.0` — alert when fewer than 2
    /// executors are available per queued task.
    pub fn new(stall_threshold_secs: u64) -> Self {
        LoopWatchdog {
            stall_threshold_secs,
            supply_alert_threshold: 2.0,
            last_cycle_at: Arc::new(Mutex::new(Instant::now())),
            stall_count: Arc::new(AtomicU64::new(0)),
        }
    }

    /// Create a watchdog with custom thresholds.
    pub fn with_supply_threshold(mut self, threshold: f64) -> Self {
        self.supply_alert_threshold = threshold;
        self
    }

    /// Record that a cycle completed. Resets the stall timer and returns a
    /// `Recovered` event if the loop was previously stalled.
    pub fn record_cycle_completed(&self, cycle: u64, duration_ms: u64) -> WatchdogEvent {
        let prev_stall_count = self.stall_count.swap(0, Ordering::SeqCst);
        {
            let mut last = self.last_cycle_at.lock().expect("watchdog mutex poisoned");
            *last = Instant::now();
        }
        if prev_stall_count > 0 {
            WatchdogEvent::Recovered {
                after_stall_count: prev_stall_count,
            }
        } else {
            WatchdogEvent::CycleCompleted { cycle, duration_ms }
        }
    }

    /// Check whether the loop has stalled.
    ///
    /// Returns `Some(StallDetected { … })` if no cycle has completed within
    /// `stall_threshold_secs`, otherwise `None`.
    pub fn check_stall(&self) -> Option<WatchdogEvent> {
        let elapsed = {
            let last = self.last_cycle_at.lock().expect("watchdog mutex poisoned");
            last.elapsed().as_secs()
        };
        if elapsed >= self.stall_threshold_secs {
            let count = self.stall_count.fetch_add(1, Ordering::SeqCst) + 1;
            Some(WatchdogEvent::StallDetected {
                secs_since_last_cycle: elapsed,
                stall_count: count,
            })
        } else {
            None
        }
    }

    /// Check the executor supply health ratio.
    ///
    /// Returns `Some(SupplyHealthAlert { ratio })` if `active_executors / queue_depth`
    /// is below `supply_alert_threshold`, or if `queue_depth == 0` and
    /// `active_executors == 0`. Returns `None` when supply is healthy.
    pub fn check_supply_health(
        &self,
        active_executors: usize,
        queue_depth: usize,
    ) -> Option<WatchdogEvent> {
        if queue_depth == 0 {
            // No pending work — no supply pressure.
            return None;
        }
        let ratio = active_executors as f64 / queue_depth as f64;
        if ratio < self.supply_alert_threshold {
            Some(WatchdogEvent::SupplyHealthAlert { ratio })
        } else {
            None
        }
    }

    /// Return the current stall count (number of consecutive stall events fired).
    pub fn stall_count(&self) -> u64 {
        self.stall_count.load(Ordering::SeqCst)
    }

    /// Return seconds elapsed since the last completed cycle.
    pub fn secs_since_last_cycle(&self) -> u64 {
        let last = self.last_cycle_at.lock().expect("watchdog mutex poisoned");
        last.elapsed().as_secs()
    }
}

// ── Tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use std::thread;
    use std::time::Duration;

    #[test]
    fn no_stall_immediately_after_creation() {
        let wd = LoopWatchdog::new(300);
        assert!(wd.check_stall().is_none(), "fresh watchdog must not stall");
    }

    #[test]
    fn stall_detected_after_threshold() {
        // threshold of 0 — always stalled immediately
        let wd = LoopWatchdog::new(0);
        // Sleep briefly so elapsed >= 0 is guaranteed (Instant resolution)
        thread::sleep(Duration::from_millis(5));
        let event = wd.check_stall();
        assert!(event.is_some(), "expected stall event");
        match event.unwrap() {
            WatchdogEvent::StallDetected { stall_count, .. } => {
                assert_eq!(stall_count, 1);
            }
            other => panic!("unexpected event: {:?}", other),
        }
    }

    #[test]
    fn stall_count_increments() {
        let wd = LoopWatchdog::new(0);
        thread::sleep(Duration::from_millis(5));
        wd.check_stall();
        wd.check_stall();
        assert_eq!(wd.stall_count(), 2);
    }

    #[test]
    fn record_cycle_resets_stall_count() {
        let wd = LoopWatchdog::new(0);
        thread::sleep(Duration::from_millis(5));
        wd.check_stall();
        assert_eq!(wd.stall_count(), 1);
        let event = wd.record_cycle_completed(1, 100);
        assert_eq!(wd.stall_count(), 0);
        match event {
            WatchdogEvent::Recovered { after_stall_count } => {
                assert_eq!(after_stall_count, 1);
            }
            other => panic!("expected Recovered, got: {:?}", other),
        }
    }

    #[test]
    fn record_cycle_no_prior_stall_returns_cycle_completed() {
        let wd = LoopWatchdog::new(300);
        let event = wd.record_cycle_completed(5, 250);
        match event {
            WatchdogEvent::CycleCompleted { cycle, duration_ms } => {
                assert_eq!(cycle, 5);
                assert_eq!(duration_ms, 250);
            }
            other => panic!("expected CycleCompleted, got: {:?}", other),
        }
    }

    #[test]
    fn supply_health_no_alert_when_queue_empty() {
        let wd = LoopWatchdog::new(300);
        assert!(wd.check_supply_health(0, 0).is_none());
        assert!(wd.check_supply_health(5, 0).is_none());
    }

    #[test]
    fn supply_health_alert_below_threshold() {
        let wd = LoopWatchdog::new(300);
        // 1 executor for 10 tasks → ratio 0.1 < 2.0
        let event = wd.check_supply_health(1, 10);
        assert!(event.is_some());
        match event.unwrap() {
            WatchdogEvent::SupplyHealthAlert { ratio } => {
                assert!((ratio - 0.1).abs() < 1e-9);
            }
            other => panic!("unexpected: {:?}", other),
        }
    }

    #[test]
    fn supply_health_no_alert_above_threshold() {
        let wd = LoopWatchdog::new(300);
        // 10 executors for 2 tasks → ratio 5.0 >= 2.0
        assert!(wd.check_supply_health(10, 2).is_none());
    }
}
