//! `urace-net` — NAT traversal, STUN (RFC 5389), DDNS, and tunnel management.
//!
//! Rust port of:
//!   - `nat_check.py`     → `nat`
//!   - `stun_client.py`   → `stun`
//!   - `ddns.py`          → `ddns`
//!   - `tunnel_server.py` / `tunnel_install.py` → `tunnel`

pub mod nat;
pub mod stun;
pub mod ddns;
pub mod tunnel;

pub use nat::{check_nat, NatCheckResult, NatType, DEFAULT_STUN_SERVERS};
pub use stun::{StunClient, StunError, STUN_MAGIC_COOKIE};
pub use ddns::{get_current_public_ip, DdnsError, DdnsUpdater};
pub use tunnel::{TunnelConfig, TunnelError, TunnelManager, TunnelState};
