//! Tunnel management — TCP port-forwarding abstraction.
//!
//! Mirrors the Python `tunnel_server.py` / `tunnel_install.py` concepts.
//! Full tunnel protocol requires OS-level integration; network I/O is stubbed
//! here — the types, state machine, and config are fully defined.

use serde::{Deserialize, Serialize};
use std::sync::{Arc, Mutex};
use thiserror::Error;
use tracing::{debug, info, warn};

#[derive(Debug, Error)]
pub enum TunnelError {
    #[error("already running")]
    AlreadyRunning,
    #[error("not running")]
    NotRunning,
    #[error("configuration invalid: {0}")]
    InvalidConfig(String),
    #[error("I/O error: {0}")]
    Io(String),
}

/// Configuration for a single tunnel.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TunnelConfig {
    /// Local address to listen on, e.g. "0.0.0.0:7301".
    pub listen_addr: String,
    /// Remote peer address to forward to, e.g. "10.0.0.5:7301".
    pub remote_addr: String,
    /// Shared secret / bearer token used to authenticate the tunnel.
    pub auth_token: String,
}

impl TunnelConfig {
    pub fn new(listen_addr: &str, remote_addr: &str, auth_token: &str) -> Self {
        Self {
            listen_addr: listen_addr.to_string(),
            remote_addr: remote_addr.to_string(),
            auth_token: auth_token.to_string(),
        }
    }

    fn validate(&self) -> Result<(), TunnelError> {
        if self.listen_addr.is_empty() {
            return Err(TunnelError::InvalidConfig("listen_addr is empty".into()));
        }
        if self.remote_addr.is_empty() {
            return Err(TunnelError::InvalidConfig("remote_addr is empty".into()));
        }
        if self.auth_token.is_empty() {
            return Err(TunnelError::InvalidConfig(
                "auth_token must not be empty".into(),
            ));
        }
        Ok(())
    }
}

/// Runtime state of a managed tunnel.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(tag = "state")]
pub enum TunnelState {
    Stopped,
    Connecting,
    Connected {
        /// ISO-8601 timestamp when the connection was established.
        since: String,
    },
    Failed {
        reason: String,
    },
}

/// Manages a single TCP tunnel (start / stop / query state).
///
/// Network I/O is stubbed — a full implementation would spawn a tokio task
/// that accepts on `listen_addr` and forwards bytes to `remote_addr`.
#[derive(Debug, Clone)]
pub struct TunnelManager {
    state: Arc<Mutex<TunnelState>>,
}

impl Default for TunnelManager {
    fn default() -> Self {
        Self::new()
    }
}

impl TunnelManager {
    pub fn new() -> Self {
        Self {
            state: Arc::new(Mutex::new(TunnelState::Stopped)),
        }
    }

    /// Start the tunnel with the given config.
    ///
    /// Returns the new `TunnelState` (Connected or Failed).
    pub fn start(&self, config: TunnelConfig) -> TunnelState {
        let mut state = self.state.lock().expect("mutex poisoned");
        if matches!(
            *state,
            TunnelState::Connected { .. } | TunnelState::Connecting
        ) {
            warn!("tunnel already running; ignoring start()");
            return state.clone();
        }
        *state = TunnelState::Connecting;

        if let Err(e) = config.validate() {
            let reason = e.to_string();
            warn!(reason = %reason, "tunnel config invalid");
            *state = TunnelState::Failed {
                reason: reason.clone(),
            };
            return state.clone();
        }

        // Stub: in a real implementation this would spawn a tokio task.
        // We transition immediately to Connected to represent intent.
        info!(
            listen = %config.listen_addr,
            remote = %config.remote_addr,
            "tunnel started (stubbed TCP forwarding)"
        );
        let since = now_iso8601();
        *state = TunnelState::Connected { since };
        debug!("tunnel state → Connected");
        state.clone()
    }

    /// Stop the tunnel.
    ///
    /// Returns `TunnelState::Stopped`.
    pub fn stop(&self) -> TunnelState {
        let mut state = self.state.lock().expect("mutex poisoned");
        if matches!(*state, TunnelState::Stopped) {
            return TunnelState::Stopped;
        }
        info!("tunnel stopped");
        *state = TunnelState::Stopped;
        TunnelState::Stopped
    }

    /// Query current tunnel state without side effects.
    pub fn state(&self) -> TunnelState {
        self.state.lock().expect("mutex poisoned").clone()
    }
}

fn now_iso8601() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    let secs = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs();
    // Reuse the same simple formatter from nat.rs — avoids pulling in chrono.
    let (y, mo, d, h, mi, s) = epoch_parts(secs);
    format!("{y:04}-{mo:02}-{d:02}T{h:02}:{mi:02}:{s:02}Z")
}

fn epoch_parts(secs: u64) -> (u64, u64, u64, u64, u64, u64) {
    let s = secs % 60;
    let mins = secs / 60;
    let mi = mins % 60;
    let hours = mins / 60;
    let h = hours % 24;
    let days = hours / 24;
    let (y, doy) = {
        let mut rem = days;
        let mut yr = 1970u64;
        loop {
            let dy = if (yr.is_multiple_of(4) && !yr.is_multiple_of(100)) || yr.is_multiple_of(400)
            {
                366
            } else {
                365
            };
            if rem < dy {
                break (yr, rem);
            }
            rem -= dy;
            yr += 1;
        }
    };
    let leap = (y % 4 == 0 && y % 100 != 0) || y % 400 == 0;
    let months: &[u64] = if leap {
        &[31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    } else {
        &[31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    };
    let mut rem = doy;
    let mut mo = 1u64;
    for &dm in months {
        if rem < dm {
            break;
        }
        rem -= dm;
        mo += 1;
    }
    (y, mo, rem + 1, h, mi, s)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_tunnel_config_new() {
        let c = TunnelConfig::new("0.0.0.0:7301", "10.0.0.5:7301", "secret");
        assert_eq!(c.listen_addr, "0.0.0.0:7301");
        assert_eq!(c.remote_addr, "10.0.0.5:7301");
        assert_eq!(c.auth_token, "secret");
    }

    #[test]
    fn test_tunnel_state_serde() {
        let states = vec![
            TunnelState::Stopped,
            TunnelState::Connecting,
            TunnelState::Connected {
                since: "2024-01-01T00:00:00Z".into(),
            },
            TunnelState::Failed {
                reason: "timeout".into(),
            },
        ];
        for s in states {
            let json = serde_json::to_string(&s).unwrap();
            let back: TunnelState = serde_json::from_str(&json).unwrap();
            assert_eq!(s, back);
        }
    }

    #[test]
    fn test_manager_initial_state_is_stopped() {
        let m = TunnelManager::new();
        assert_eq!(m.state(), TunnelState::Stopped);
    }

    #[test]
    fn test_manager_start_valid_config() {
        let m = TunnelManager::new();
        let cfg = TunnelConfig::new("0.0.0.0:7301", "10.0.0.1:7301", "tok");
        let s = m.start(cfg);
        assert!(matches!(s, TunnelState::Connected { .. }));
        assert!(matches!(m.state(), TunnelState::Connected { .. }));
    }

    #[test]
    fn test_manager_start_invalid_config_empty_token() {
        let m = TunnelManager::new();
        let cfg = TunnelConfig::new("0.0.0.0:7301", "10.0.0.1:7301", "");
        let s = m.start(cfg);
        assert!(matches!(s, TunnelState::Failed { .. }));
    }

    #[test]
    fn test_manager_stop_from_stopped() {
        let m = TunnelManager::new();
        assert_eq!(m.stop(), TunnelState::Stopped);
    }

    #[test]
    fn test_manager_start_then_stop() {
        let m = TunnelManager::new();
        let cfg = TunnelConfig::new("0.0.0.0:7301", "10.0.0.1:7301", "tok");
        m.start(cfg);
        assert!(matches!(m.state(), TunnelState::Connected { .. }));
        m.stop();
        assert_eq!(m.state(), TunnelState::Stopped);
    }

    #[test]
    fn test_manager_start_already_running_is_idempotent() {
        let m = TunnelManager::new();
        let cfg = TunnelConfig::new("0.0.0.0:7301", "10.0.0.1:7301", "tok");
        m.start(cfg.clone());
        // Starting again should not crash and returns current Connected state.
        let s2 = m.start(cfg);
        assert!(matches!(s2, TunnelState::Connected { .. }));
    }

    #[test]
    fn test_config_validation_empty_listen_addr() {
        let c = TunnelConfig::new("", "10.0.0.1:7301", "tok");
        assert!(c.validate().is_err());
    }

    #[test]
    fn test_config_validation_empty_remote_addr() {
        let c = TunnelConfig::new("0.0.0.0:7301", "", "tok");
        assert!(c.validate().is_err());
    }
}
