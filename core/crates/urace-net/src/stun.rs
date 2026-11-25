//! Lightweight STUN client — RFC 5389 Binding Request / XOR-MAPPED-ADDRESS.
//!
//! Implements the 20-byte STUN header:
//!   [0..2]  message type  = 0x0001 (Binding Request)
//!   [2..4]  message length (body after header, 0 for bare request)
//!   [4..8]  magic cookie  = 0x2112A442
//!   [8..20] transaction ID (12 random bytes)
//!
//! XOR-MAPPED-ADDRESS (attr type 0x0020) decoding:
//!   port ^ (magic_cookie >> 16) = port ^ 0x2112
//!   ip   ^ magic_cookie         = ip   ^ 0x2112A442

use std::net::UdpSocket;
use std::time::Duration;
use thiserror::Error;
use tracing::debug;

/// RFC 5389 magic cookie — MUST be this exact value.
pub const STUN_MAGIC_COOKIE: u32 = 0x2112_A442;
/// Binding Request message type.
const MSG_BINDING_REQUEST: u16 = 0x0001;
/// Binding Success Response message type.
const MSG_BINDING_RESPONSE: u16 = 0x0101;
/// XOR-MAPPED-ADDRESS attribute type (RFC 5389).
const ATTR_XOR_MAPPED_ADDRESS: u16 = 0x0020;
/// MAPPED-ADDRESS attribute type (RFC 3489 fallback).
const ATTR_MAPPED_ADDRESS: u16 = 0x0001;
/// IPv4 address family.
const FAMILY_IPV4: u8 = 0x01;

#[derive(Debug, Error)]
pub enum StunError {
    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),
    #[error("STUN server did not respond within timeout")]
    Timeout,
    #[error("Invalid STUN response: {0}")]
    InvalidResponse(String),
    #[error("No usable address attribute found in STUN response")]
    NoAddress,
}

/// A minimal RFC 5389 STUN client bound to a single server address.
pub struct StunClient {
    server: String,
}

impl StunClient {
    /// Create a new `StunClient` for the given `host:port` server address.
    pub fn new(server: &str) -> Self {
        Self {
            server: server.to_string(),
        }
    }

    /// Send a STUN Binding Request and return the external `(ip, port)`.
    ///
    /// Uses XOR-MAPPED-ADDRESS (RFC 5389) with MAPPED-ADDRESS (RFC 3489) as
    /// fallback, exactly as the Python `stun_client.py` does.
    pub fn query_external_address(&self) -> Result<(String, u16), StunError> {
        // Build Binding Request: 20-byte header, no attributes.
        let transaction_id: [u8; 12] = {
            use std::collections::hash_map::DefaultHasher;
            use std::hash::{Hash, Hasher};
            use std::time::SystemTime;
            let mut h = DefaultHasher::new();
            SystemTime::now().hash(&mut h);
            std::thread::current().id().hash(&mut h);
            let seed = h.finish();
            // Deterministic-ish 12 bytes from two u64 seeds
            let mut tid = [0u8; 12];
            let b1 = seed.to_be_bytes();
            let b2 = seed
                .wrapping_mul(6364136223846793005)
                .wrapping_add(1442695040888963407)
                .to_be_bytes();
            tid[..8].copy_from_slice(&b1);
            tid[8..12].copy_from_slice(&b2[..4]);
            tid
        };

        let mut request = [0u8; 20];
        // Message type
        request[0] = (MSG_BINDING_REQUEST >> 8) as u8;
        request[1] = (MSG_BINDING_REQUEST & 0xFF) as u8;
        // Message length (0 — no body attributes in request)
        request[2] = 0;
        request[3] = 0;
        // Magic cookie
        request[4] = 0x21;
        request[5] = 0x12;
        request[6] = 0xA4;
        request[7] = 0x42;
        // Transaction ID
        request[8..20].copy_from_slice(&transaction_id);

        // Bind an ephemeral UDP socket and send.
        let sock = UdpSocket::bind("0.0.0.0:0").map_err(StunError::Io)?;
        sock.set_read_timeout(Some(Duration::from_secs(5)))
            .map_err(StunError::Io)?;
        sock.send_to(&request, &self.server)
            .map_err(StunError::Io)?;

        let mut buf = [0u8; 2048];
        let (n, _) = sock.recv_from(&mut buf).map_err(|e| {
            if e.kind() == std::io::ErrorKind::WouldBlock
                || e.kind() == std::io::ErrorKind::TimedOut
            {
                StunError::Timeout
            } else {
                StunError::Io(e)
            }
        })?;
        let data = &buf[..n];
        parse_stun_response(data)
    }
}

/// Parse a raw STUN response buffer; returns `(ip_string, port)`.
pub(crate) fn parse_stun_response(data: &[u8]) -> Result<(String, u16), StunError> {
    if data.len() < 20 {
        return Err(StunError::InvalidResponse(
            "response shorter than 20 bytes".into(),
        ));
    }
    let msg_type = u16::from_be_bytes([data[0], data[1]]);
    if msg_type != MSG_BINDING_RESPONSE {
        return Err(StunError::InvalidResponse(format!(
            "unexpected message type 0x{msg_type:04X}"
        )));
    }

    // Walk TLV attributes starting at offset 20.
    let mut i = 20usize;
    let mut xor_result: Option<(String, u16)> = None;
    let mut fallback: Option<(String, u16)> = None;

    while i + 4 <= data.len() {
        let attr_type = u16::from_be_bytes([data[i], data[i + 1]]);
        let attr_len = u16::from_be_bytes([data[i + 2], data[i + 3]]) as usize;
        let val_start = i + 4;
        let val_end = val_start + attr_len;
        if val_end > data.len() {
            break;
        }
        let av = &data[val_start..val_end];

        match attr_type {
            ATTR_XOR_MAPPED_ADDRESS if attr_len >= 8 && av[1] == FAMILY_IPV4 => {
                let raw_port = u16::from_be_bytes([av[2], av[3]]);
                let port = raw_port ^ (STUN_MAGIC_COOKIE >> 16) as u16; // ^ 0x2112
                let raw_ip = u32::from_be_bytes([av[4], av[5], av[6], av[7]]);
                let ip_int = raw_ip ^ STUN_MAGIC_COOKIE;
                let ip = ipv4_to_string(ip_int);
                debug!(ip = %ip, port = port, "STUN XOR-MAPPED-ADDRESS");
                xor_result = Some((ip, port));
                break; // prefer XOR-MAPPED-ADDRESS — stop scanning
            }
            ATTR_MAPPED_ADDRESS if attr_len >= 8 && av[1] == FAMILY_IPV4 && fallback.is_none() => {
                let port = u16::from_be_bytes([av[2], av[3]]);
                let ip_int = u32::from_be_bytes([av[4], av[5], av[6], av[7]]);
                let ip = ipv4_to_string(ip_int);
                debug!(ip = %ip, port = port, "STUN MAPPED-ADDRESS (fallback)");
                fallback = Some((ip, port));
            }
            _ => {}
        }

        // Advance past value + padding to 4-byte boundary.
        let padded = attr_len + (4 - attr_len % 4) % 4;
        i += 4 + padded;
    }

    xor_result.or(fallback).ok_or(StunError::NoAddress)
}

fn ipv4_to_string(ip_int: u32) -> String {
    let octets = ip_int.to_be_bytes();
    format!("{}.{}.{}.{}", octets[0], octets[1], octets[2], octets[3])
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Build a minimal synthetic STUN Binding Success Response with a single
    /// XOR-MAPPED-ADDRESS attribute for 1.2.3.4:4567 and verify parsing.
    #[test]
    fn test_parse_xor_mapped_address() {
        let ip_raw: u32 = u32::from_be_bytes([1, 2, 3, 4]) ^ STUN_MAGIC_COOKIE;
        let port_raw: u16 = 4567u16 ^ (STUN_MAGIC_COOKIE >> 16) as u16;

        // Attribute value: reserved(1), family(1), port(2), ip(4) = 8 bytes
        let mut attr_val = vec![0u8, FAMILY_IPV4, 0, 0, 0, 0, 0, 0];
        attr_val[2..4].copy_from_slice(&port_raw.to_be_bytes());
        attr_val[4..8].copy_from_slice(&ip_raw.to_be_bytes());

        // Build full response
        let attr_len = attr_val.len() as u16;
        let msg_len = 4 + attr_len; // attr header (4) + val (8)
        let mut pkt = vec![0u8; 20];
        pkt[0] = (MSG_BINDING_RESPONSE >> 8) as u8;
        pkt[1] = (MSG_BINDING_RESPONSE & 0xFF) as u8;
        pkt[2] = (msg_len >> 8) as u8;
        pkt[3] = (msg_len & 0xFF) as u8;
        // magic cookie
        pkt[4] = 0x21;
        pkt[5] = 0x12;
        pkt[6] = 0xA4;
        pkt[7] = 0x42;
        // transaction id (8..20) already zeroed
        // attr header
        pkt.push((ATTR_XOR_MAPPED_ADDRESS >> 8) as u8);
        pkt.push((ATTR_XOR_MAPPED_ADDRESS & 0xFF) as u8);
        pkt.push(0);
        pkt.push(8); // length
        pkt.extend_from_slice(&attr_val);

        let (ip, port) = parse_stun_response(&pkt).expect("should parse XOR-MAPPED-ADDRESS");
        assert_eq!(ip, "1.2.3.4");
        assert_eq!(port, 4567);
    }

    /// A response with only MAPPED-ADDRESS falls back correctly.
    #[test]
    fn test_parse_mapped_address_fallback() {
        let ip_bytes: [u8; 4] = [10, 0, 0, 1];
        let port: u16 = 12345;

        let mut attr_val = vec![0u8, FAMILY_IPV4, 0, 0, 0, 0, 0, 0];
        attr_val[2..4].copy_from_slice(&port.to_be_bytes());
        attr_val[4..8].copy_from_slice(&ip_bytes);

        let attr_len = attr_val.len() as u16;
        let msg_len = 4 + attr_len;
        let mut pkt = vec![0u8; 20];
        pkt[0] = (MSG_BINDING_RESPONSE >> 8) as u8;
        pkt[1] = (MSG_BINDING_RESPONSE & 0xFF) as u8;
        pkt[2] = (msg_len >> 8) as u8;
        pkt[3] = (msg_len & 0xFF) as u8;
        pkt[4] = 0x21;
        pkt[5] = 0x12;
        pkt[6] = 0xA4;
        pkt[7] = 0x42;
        pkt.push((ATTR_MAPPED_ADDRESS >> 8) as u8);
        pkt.push((ATTR_MAPPED_ADDRESS & 0xFF) as u8);
        pkt.push(0);
        pkt.push(8);
        pkt.extend_from_slice(&attr_val);

        let (ip, p) = parse_stun_response(&pkt).expect("should parse MAPPED-ADDRESS fallback");
        assert_eq!(ip, "10.0.0.1");
        assert_eq!(p, 12345);
    }

    /// Truncated / invalid responses return errors (not panics).
    #[test]
    fn test_too_short_returns_error() {
        assert!(parse_stun_response(&[]).is_err());
        assert!(parse_stun_response(&[0u8; 10]).is_err());
    }

    /// Wrong message type returns InvalidResponse.
    #[test]
    fn test_wrong_msg_type() {
        let mut pkt = [0u8; 20];
        pkt[0] = 0x01;
        pkt[1] = 0x11; // 0x0111 — not 0x0101
        assert!(parse_stun_response(&pkt).is_err());
    }

    /// Verifies magic cookie constant is exactly RFC 5389 value.
    #[test]
    fn test_magic_cookie_value() {
        assert_eq!(STUN_MAGIC_COOKIE, 0x2112_A442);
    }
}
