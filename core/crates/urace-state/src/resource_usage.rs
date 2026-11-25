//! Resource usage tracking — CPU, memory, disk, and network metrics.
//!
//! Ported from `resource_usage.py` (native-receipt normalisation for executor calls).
//! This Rust version focuses on the per-node usage tracker used at runtime.

use parking_lot::RwLock;
use serde::{Deserialize, Serialize};
use std::collections::VecDeque;
use std::sync::Arc;
use std::time::{SystemTime, UNIX_EPOCH};

/// A single resource usage snapshot.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResourceUsage {
    /// Unix timestamp of the sample.
    pub at_unix: f64,
    /// CPU utilisation in [0.0, 1.0] (fraction of one core).
    pub cpu_fraction: f64,
    /// Resident memory in bytes.
    pub mem_bytes: u64,
    /// Disk used in bytes.
    pub disk_bytes: u64,
    /// Network bytes sent since last sample.
    pub net_bytes_sent: u64,
    /// Network bytes received since last sample.
    pub net_bytes_recv: u64,
    /// Optional label (e.g. executor task id).
    pub label: Option<String>,
}

impl ResourceUsage {
    pub fn new(
        cpu_fraction: f64,
        mem_bytes: u64,
        disk_bytes: u64,
        net_bytes_sent: u64,
        net_bytes_recv: u64,
        label: Option<String>,
    ) -> Self {
        ResourceUsage {
            at_unix: SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .map(|d| d.as_secs_f64())
                .unwrap_or(0.0),
            cpu_fraction: cpu_fraction.clamp(0.0, 1.0),
            mem_bytes,
            disk_bytes,
            net_bytes_sent,
            net_bytes_recv,
            label,
        }
    }
}

/// Ring-buffer of resource usage samples with configurable capacity.
#[derive(Clone)]
pub struct UsageTracker {
    capacity: usize,
    samples: Arc<RwLock<VecDeque<ResourceUsage>>>,
}

impl UsageTracker {
    /// Create a tracker with `capacity` slots (default 1000, matches inbox bound).
    pub fn new(capacity: usize) -> Self {
        UsageTracker {
            capacity: capacity.max(1),
            samples: Arc::new(RwLock::new(VecDeque::with_capacity(capacity))),
        }
    }

    /// Push a new sample; oldest is dropped when at capacity.
    pub fn push(&self, sample: ResourceUsage) {
        let mut guard = self.samples.write();
        if guard.len() >= self.capacity {
            guard.pop_front();
        }
        guard.push_back(sample);
    }

    /// Return all samples in chronological order.
    pub fn samples(&self) -> Vec<ResourceUsage> {
        self.samples.read().iter().cloned().collect()
    }

    /// Return the most recent sample, if any.
    pub fn latest(&self) -> Option<ResourceUsage> {
        self.samples.read().back().cloned()
    }

    /// Average CPU fraction over all retained samples.
    pub fn avg_cpu(&self) -> f64 {
        let guard = self.samples.read();
        if guard.is_empty() {
            return 0.0;
        }
        guard.iter().map(|s| s.cpu_fraction).sum::<f64>() / guard.len() as f64
    }

    /// Peak memory over all retained samples.
    pub fn peak_mem_bytes(&self) -> u64 {
        self.samples
            .read()
            .iter()
            .map(|s| s.mem_bytes)
            .max()
            .unwrap_or(0)
    }

    pub fn len(&self) -> usize {
        self.samples.read().len()
    }

    pub fn is_empty(&self) -> bool {
        self.samples.read().is_empty()
    }
}

impl Default for UsageTracker {
    fn default() -> Self {
        Self::new(1000)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample(cpu: f64, mem: u64) -> ResourceUsage {
        ResourceUsage::new(cpu, mem, 0, 0, 0, None)
    }

    #[test]
    fn push_and_retrieve() {
        let t = UsageTracker::new(5);
        t.push(sample(0.1, 100));
        t.push(sample(0.2, 200));
        assert_eq!(t.len(), 2);
        let latest = t.latest().unwrap();
        assert_eq!(latest.mem_bytes, 200);
    }

    #[test]
    fn overflow_drops_oldest() {
        let t = UsageTracker::new(3);
        t.push(sample(0.1, 10));
        t.push(sample(0.2, 20));
        t.push(sample(0.3, 30));
        t.push(sample(0.4, 40)); // drops first
        assert_eq!(t.len(), 3);
        assert_eq!(t.samples()[0].mem_bytes, 20);
    }

    #[test]
    fn avg_cpu() {
        let t = UsageTracker::new(10);
        t.push(sample(0.2, 0));
        t.push(sample(0.4, 0));
        assert!((t.avg_cpu() - 0.3).abs() < 1e-6);
    }

    #[test]
    fn peak_mem() {
        let t = UsageTracker::new(10);
        t.push(sample(0.0, 100));
        t.push(sample(0.0, 500));
        t.push(sample(0.0, 300));
        assert_eq!(t.peak_mem_bytes(), 500);
    }
}
