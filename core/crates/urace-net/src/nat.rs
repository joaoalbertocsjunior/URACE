//! NAT type detection via double-STUN probe.
//!
//! Mirrors `nat_check.py::detect_nat_type()`.
//!
//! NAT classification:
//!   Open      — public IP equals local IP (direct, no NAT)
//!   FullCone  — same external port observed across ≥2 STUN servers (cone)
//!   Symmetric — different external port per STUN server (relay required)
//!   Unknown   — STUN unreachable or single result with no local-IP comparison

use serde::{Deserialize, Serialize};
use std::net::UdpSocket;
use tokio::net::UdpSocket as TokioUdpSocket;
use tracing::{debug, warn};

use crate::stun::{parse_stun_response, StunError};

/// Bootstrap STUN servers queried during NAT detection.
pub const DEFAULT_STUN_SERVERS: &[&str] = &[
    "stun.l.google.com:19302",
    "stun1.l.google.com:19302",
    "stun.cloudflare.com:3478",
    "stun.stunprotocol.org:3478",
];

/// NAT classification result.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum NatType {
    /// No NAT — public IP equals local IP (VPS / server with direct inbound).
    Open,
    /// Full-cone or port-restricted cone — same external port across STUN servers.
    FullCone,
    /// Port-restricted cone (alias kept for RFC completeness — mapped to FullCone in practice).
    RestrictedCone,
    /// Port-restricted cone variant.
    PortRestricted,
    /// Symmetric NAT — different external port per STUN server; relay required.
    Symmetric,
    /// STUN probes failed or inconclusive.
    Unknown,
}

/// Result of a NAT check.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NatCheckResult {
    pub nat_type: NatType,
    pub external_ip: Option<String>,
    pub external_port: Option<u16>,
    /// ISO-8601 timestamp of when the check was performed.
    pub checked_at: String,
    /// Which STUN server produced the first successful result.
    pub stun_server: Option<String>,
}

/// Perform a double-STUN NAT probe (async).
///
/// Queries up to the first 3 STUN servers from `stun_servers`.
/// Returns `NatType::Unknown` if no server responds.
pub async fn check_nat(stun_servers: &[&str]) -> NatCheckResult {
    let checked_at = chrono_now();
    let servers: Vec<&str> = stun_servers.iter().copied().take(3).collect();

    let mut results: Vec<(String, u16)> = Vec::new();
    let mut first_server: Option<String> = None;

    for &server in &servers {
        match probe_stun_async(server).await {
            Ok((ip, port)) => {
                debug!(server = %server, ip = %ip, port = port, "STUN probe success");
                if first_server.is_none() {
                    first_server = Some(server.to_string());
                }
                results.push((ip, port));
            }
            Err(e) => {
                debug!(server = %server, error = %e, "STUN probe failed");
            }
        }
        // Small delay between probes (mirrors Python `time.sleep(0.1)`)
        tokio::time::sleep(std::time::Duration::from_millis(100)).await;
    }

    if results.is_empty() {
        warn!("All STUN servers unreachable — returning Unknown NAT type");
        return NatCheckResult {
            nat_type: NatType::Unknown,
            external_ip: None,
            external_port: None,
            checked_at,
            stun_server: None,
        };
    }

    let (public_ip, public_port) = results[0].clone();

    // Detect "Open" (no NAT): local outbound IP == public IP
    let local_ip = detect_local_ip();
    if let Some(ref local) = local_ip {
        if local == &public_ip {
            return NatCheckResult {
                nat_type: NatType::Open,
                external_ip: Some(public_ip),
                external_port: Some(public_port),
                checked_at,
                stun_server: first_server,
            };
        }
    }

    if results.len() >= 2 {
        let ports: std::collections::HashSet<u16> = results.iter().map(|(_, p)| *p).collect();
        let nat_type = if ports.len() == 1 {
            NatType::FullCone
        } else {
            NatType::Symmetric
        };
        return NatCheckResult {
            nat_type,
            external_ip: Some(public_ip),
            external_port: Some(public_port),
            checked_at,
            stun_server: first_server,
        };
    }

    // Single result — cannot classify without a second probe
    NatCheckResult {
        nat_type: NatType::Unknown,
        external_ip: Some(public_ip),
        external_port: Some(public_port),
        checked_at,
        stun_server: first_server,
    }
}

/// Send a STUN Binding Request via async UDP; returns `(ip, port)`.
async fn probe_stun_async(server: &str) -> Result<(String, u16), StunError> {
    // Resolve server address
    use tokio::net::lookup_host;
    let mut addrs = lookup_host(server)
        .await
        .map_err(|e| StunError::Io(std::io::Error::new(std::io::ErrorKind::Other, e.to_string())))?;
    let addr = addrs
        .next()
        .ok_or_else(|| StunError::Io(std::io::Error::new(std::io::ErrorKind::Other, "DNS resolution returned no addresses")))?;

    let sock = TokioUdpSocket::bind("0.0.0.0:0")
        .await
        .map_err(StunError::Io)?;

    // Build STUN Binding Request (20 bytes: type=0x0001, len=0, magic, random tid)
    let tid: [u8; 12] = {
        use std::collections::hash_map::DefaultHasher;
        use std::hash::{Hash, Hasher};
        use std::time::SystemTime;
        let mut h = DefaultHasher::new();
        SystemTime::now().hash(&mut h);
        addr.hash(&mut h);
        let seed = h.finish();
        let mut tid = [0u8; 12];
        tid[..8].copy_from_slice(&seed.to_be_bytes());
        tid[8..12].copy_from_slice(&seed.wrapping_add(1).to_be_bytes()[..4]);
        tid
    };

    let mut req = [0u8; 20];
    req[0] = 0x00; req[1] = 0x01; // Binding Request
    req[2] = 0x00; req[3] = 0x00; // Length = 0
    req[4] = 0x21; req[5] = 0x12; req[6] = 0xA4; req[7] = 0x42; // Magic cookie
    req[8..20].copy_from_slice(&tid);

    sock.send_to(&req, addr).await.map_err(StunError::Io)?;

    let mut buf = [0u8; 2048];
    let (n, _) = tokio::time::timeout(
        std::time::Duration::from_secs(5),
        sock.recv_from(&mut buf),
    )
    .await
    .map_err(|_| StunError::Timeout)?
    .map_err(StunError::Io)?;

    parse_stun_response(&buf[..n])
}

/// Best-effort detection of the local outbound IPv4 address.
/// Mirrors `nat_check.py`'s approach: connect UDP to 8.8.8.8:80, read getsockname().
fn detect_local_ip() -> Option<String> {
    let sock = UdpSocket::bind("0.0.0.0:0").ok()?;
    sock.connect("8.8.8.8:80").ok()?;
    let addr = sock.local_addr().ok()?;
    Some(addr.ip().to_string())
}

fn chrono_now() -> String {
    // Simple RFC-3339-ish timestamp without pulling in chrono.
    use std::time::{SystemTime, UNIX_EPOCH};
    let secs = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs();
    // Format as ISO-8601 seconds-precision UTC (good enough for a check record)
    let (y, mo, d, h, mi, s) = epoch_to_ymd_hms(secs);
    format!("{y:04}-{mo:02}-{d:02}T{h:02}:{mi:02}:{s:02}Z")
}

fn epoch_to_ymd_hms(secs: u64) -> (u64, u64, u64, u64, u64, u64) {
    let s = secs % 60;
    let mins = secs / 60;
    let mi = mins % 60;
    let hours = mins / 60;
    let h = hours % 24;
    let days = hours / 24;
    // Simple Gregorian calendar calculation
    let (y, doy) = days_to_year(days);
    let (mo, d) = doy_to_month_day(doy, is_leap(y));
    (y, mo, d, h, mi, s)
}

fn is_leap(y: u64) -> bool {
    (y % 4 == 0 && y % 100 != 0) || (y % 400 == 0)
}

fn days_to_year(mut days: u64) -> (u64, u64) {
    let mut y = 1970u64;
    loop {
        let days_in_year = if is_leap(y) { 366 } else { 365 };
        if days < days_in_year {
            return (y, days);
        }
        days -= days_in_year;
        y += 1;
    }
}

fn doy_to_month_day(mut doy: u64, leap: bool) -> (u64, u64) {
    let months: &[u64] = if leap {
        &[31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    } else {
        &[31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    };
    let mut m = 1u64;
    for &days_in_month in months {
        if doy < days_in_month {
            return (m, doy + 1);
        }
        doy -= days_in_month;
        m += 1;
    }
    (12, 31)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_default_stun_servers_non_empty() {
        assert!(!DEFAULT_STUN_SERVERS.is_empty());
        assert!(DEFAULT_STUN_SERVERS.contains(&"stun.l.google.com:19302"));
        assert!(DEFAULT_STUN_SERVERS.contains(&"stun1.l.google.com:19302"));
    }

    #[test]
    fn test_nat_type_serde_roundtrip() {
        for nat in [
            NatType::Open,
            NatType::FullCone,
            NatType::RestrictedCone,
            NatType::PortRestricted,
            NatType::Symmetric,
            NatType::Unknown,
        ] {
            let json = serde_json::to_string(&nat).unwrap();
            let back: NatType = serde_json::from_str(&json).unwrap();
            assert_eq!(nat, back);
        }
    }

    #[test]
    fn test_nat_check_result_serde() {
        let r = NatCheckResult {
            nat_type: NatType::Symmetric,
            external_ip: Some("1.2.3.4".into()),
            external_port: Some(54321),
            checked_at: "2024-01-01T00:00:00Z".into(),
            stun_server: Some("stun.l.google.com:19302".into()),
        };
        let json = serde_json::to_string(&r).unwrap();
        let back: NatCheckResult = serde_json::from_str(&json).unwrap();
        assert_eq!(back.external_ip, r.external_ip);
        assert_eq!(back.external_port, r.external_port);
    }

    #[test]
    fn test_chrono_now_format() {
        let ts = chrono_now();
        // Basic ISO-8601 sanity: "YYYY-MM-DDTHH:MM:SSZ"
        assert_eq!(ts.len(), 20, "timestamp length: {ts}");
        assert!(ts.ends_with('Z'), "timestamp must end with Z: {ts}");
        assert!(ts.contains('T'), "timestamp must contain T: {ts}");
    }

    #[tokio::test]
    async fn test_check_nat_no_servers_returns_unknown() {
        // Empty server list → Unknown
        let result = check_nat(&[]).await;
        assert_eq!(result.nat_type, NatType::Unknown);
        assert!(result.external_ip.is_none());
    }

    #[tokio::test]
    async fn test_check_nat_unreachable_server_returns_unknown() {
        // localhost:1 is never a STUN server
        let result = check_nat(&["127.0.0.1:1"]).await;
        assert_eq!(result.nat_type, NatType::Unknown);
    }
}
