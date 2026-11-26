//! M25 — Sybil admission gate: rate-limit new peer admissions per /24 subnet.

use std::collections::{HashMap, VecDeque};

pub const MAX_NEW_PEERS_PER_SUBNET_PER_HOUR: usize = 5;
pub const SYBIL_WINDOW_SECS: u64 = 3_600;

/// Sliding-window Sybil admission gate keyed by /24 IPv4 subnet (or /48 IPv6).
pub struct SybilGate {
    /// subnet_prefix (first 3 octets of IPv4, or /48 of IPv6) -> VecDeque<admission_unix>
    admissions: HashMap<String, VecDeque<u64>>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum SybilAdmissionResult {
    Allowed,
    Blocked { subnet: String, admitted_in_window: usize },
}

impl SybilGate {
    pub fn new() -> Self {
        SybilGate {
            admissions: HashMap::new(),
        }
    }

    /// Extract the /24 subnet prefix from a peer address string "1.2.3.4:port" → "1.2.3".
    /// For IPv6 "::1" or bare IPs without port, returns the first two colon-separated
    /// segments as a best-effort /48 prefix. Falls back to the full address string.
    pub fn subnet_prefix(addr: &str) -> String {
        // Strip brackets for "[::1]:port" style IPv6.
        let addr = addr.trim_start_matches('[');

        // IPv4: "1.2.3.4:port" or "1.2.3.4"
        // Split on ':' — if the right-most token looks like a port number, strip it.
        let ip_part = if let Some(colon) = addr.rfind(':') {
            let after = &addr[colon + 1..];
            // If everything after the last colon is digits, treat it as a port.
            if after.chars().all(|c| c.is_ascii_digit()) {
                &addr[..colon]
            } else {
                addr
            }
        } else {
            addr
        };

        // Remove trailing bracket.
        let ip_part = ip_part.trim_end_matches(']');

        // IPv4: take first three octets.
        let octets: Vec<&str> = ip_part.split('.').collect();
        if octets.len() == 4 {
            return format!("{}.{}.{}", octets[0], octets[1], octets[2]);
        }

        // IPv6: take first three groups (/:48).
        let groups: Vec<&str> = ip_part.split(':').collect();
        if groups.len() >= 3 {
            return format!("{}:{}:{}", groups[0], groups[1], groups[2]);
        }

        ip_part.to_string()
    }

    /// Sliding-window gate: allow up to MAX_NEW_PEERS_PER_SUBNET_PER_HOUR per subnet per hour.
    pub fn check_and_record(&mut self, peer_addr: &str, now_unix: u64) -> SybilAdmissionResult {
        let subnet = Self::subnet_prefix(peer_addr);
        let window = self.admissions.entry(subnet.clone()).or_default();

        // Evict entries outside the sliding window.
        let cutoff = now_unix.saturating_sub(SYBIL_WINDOW_SECS);
        while let Some(&front) = window.front() {
            if front < cutoff {
                window.pop_front();
            } else {
                break;
            }
        }

        if window.len() >= MAX_NEW_PEERS_PER_SUBNET_PER_HOUR {
            return SybilAdmissionResult::Blocked {
                subnet,
                admitted_in_window: window.len(),
            };
        }

        window.push_back(now_unix);
        SybilAdmissionResult::Allowed
    }
}

impl Default for SybilGate {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_first_peer_from_subnet_allowed() {
        let mut gate = SybilGate::new();
        let result = gate.check_and_record("1.2.3.4:8080", 1_000);
        assert_eq!(result, SybilAdmissionResult::Allowed);
    }

    #[test]
    fn test_sixth_peer_from_same_subnet_blocked() {
        let mut gate = SybilGate::new();
        let now = 1_000u64;
        for i in 0..MAX_NEW_PEERS_PER_SUBNET_PER_HOUR {
            let addr = format!("1.2.3.{}:9000", i + 1);
            let r = gate.check_and_record(&addr, now);
            assert_eq!(r, SybilAdmissionResult::Allowed, "peer {} should be allowed", i + 1);
        }
        // 6th peer (same /24) must be blocked.
        let r = gate.check_and_record("1.2.3.100:9000", now);
        match r {
            SybilAdmissionResult::Blocked { subnet, admitted_in_window } => {
                assert_eq!(subnet, "1.2.3");
                assert_eq!(admitted_in_window, MAX_NEW_PEERS_PER_SUBNET_PER_HOUR);
            }
            SybilAdmissionResult::Allowed => panic!("sixth peer should be blocked"),
        }
    }

    #[test]
    fn test_different_subnets_independent() {
        let mut gate = SybilGate::new();
        let now = 2_000u64;
        // Fill up 1.2.3.x subnet.
        for i in 0..MAX_NEW_PEERS_PER_SUBNET_PER_HOUR {
            gate.check_and_record(&format!("1.2.3.{}:80", i + 1), now);
        }
        // 1.2.4.x is a different subnet — must still be allowed.
        let r = gate.check_and_record("1.2.4.1:80", now);
        assert_eq!(r, SybilAdmissionResult::Allowed);
    }

    #[test]
    fn test_window_slides_and_unblocks() {
        let mut gate = SybilGate::new();
        let t0 = 10_000u64;
        // Fill the subnet at t0.
        for i in 0..MAX_NEW_PEERS_PER_SUBNET_PER_HOUR {
            gate.check_and_record(&format!("5.6.7.{}:80", i + 1), t0);
        }
        // 6th peer at t0 is blocked.
        assert!(matches!(
            gate.check_and_record("5.6.7.99:80", t0),
            SybilAdmissionResult::Blocked { .. }
        ));
        // After SYBIL_WINDOW_SECS + 1 seconds the window has slid; all old entries evicted.
        let t1 = t0 + SYBIL_WINDOW_SECS + 1;
        let r = gate.check_and_record("5.6.7.99:80", t1);
        assert_eq!(r, SybilAdmissionResult::Allowed, "window should have slid");
    }

    #[test]
    fn test_subnet_prefix_ipv4() {
        assert_eq!(SybilGate::subnet_prefix("192.168.1.5:443"), "192.168.1");
        assert_eq!(SybilGate::subnet_prefix("10.0.0.1:0"), "10.0.0");
    }
}
