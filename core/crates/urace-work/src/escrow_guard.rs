//! M05 — Escrow timeout guard.
//!
//! Implements the 48-hour escrow expiry mandated by the security spec.
//! `EscrowRecord` is a pure state machine; no I/O or ledger writes are
//! performed here — callers are responsible for persisting state changes.

use serde::{Deserialize, Serialize};
use thiserror::Error;

/// Maximum time an escrow may remain Pending before it expires (48 hours).
pub const ESCROW_TIMEOUT_SECS: u64 = 48 * 3_600;

// ── EscrowState ───────────────────────────────────────────────────────────────

/// Life-cycle state of an escrow record.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum EscrowState {
    /// Funds are locked, awaiting work completion.
    Pending,
    /// Funds have been released to the hired peer.
    Released,
    /// The timeout elapsed without a release; funds are clawable.
    Expired,
    /// Funds have been returned to the requester after expiry.
    ClawedBack,
}

// ── EscrowError ───────────────────────────────────────────────────────────────

/// Errors that can occur during escrow state transitions.
#[derive(Debug, Error)]
pub enum EscrowError {
    #[error("invalid state transition: {0}")]
    InvalidTransition(String),

    #[error("escrow not yet expired")]
    NotExpired,
}

// ── EscrowRecord ──────────────────────────────────────────────────────────────

/// A single escrow record tracking funds locked for a work task.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EscrowRecord {
    /// Unique identifier for this escrow (e.g. task ID).
    pub escrow_id: String,
    /// Amount locked, in UCR units (must be ≥ 0).
    pub amount_ucr: i64,
    /// UNIX timestamp when the escrow was created.
    pub created_at_unix: u64,
    /// Current life-cycle state.
    pub state: EscrowState,
}

impl EscrowRecord {
    /// Create a new `Pending` escrow record.
    pub fn new(
        escrow_id: impl Into<String>,
        amount_ucr: i64,
        created_at_unix: u64,
    ) -> Self {
        EscrowRecord {
            escrow_id: escrow_id.into(),
            amount_ucr,
            created_at_unix,
            state: EscrowState::Pending,
        }
    }

    /// Returns `true` when `now_unix >= created_at_unix + ESCROW_TIMEOUT_SECS`.
    pub fn is_expired(&self, now_unix: u64) -> bool {
        now_unix >= self.created_at_unix.saturating_add(ESCROW_TIMEOUT_SECS)
    }

    /// Transition `Pending → Expired`.
    ///
    /// Returns `Err(EscrowError::InvalidTransition)` if the record is not in
    /// `Pending` state, and `Err(EscrowError::NotExpired)` if the timeout has
    /// not yet elapsed.
    pub fn expire(&mut self, now_unix: u64) -> Result<(), EscrowError> {
        if self.state != EscrowState::Pending {
            return Err(EscrowError::InvalidTransition(format!(
                "{:?} → Expired (must be Pending)",
                self.state
            )));
        }
        if !self.is_expired(now_unix) {
            return Err(EscrowError::NotExpired);
        }
        self.state = EscrowState::Expired;
        Ok(())
    }

    /// Transition `Pending → Released`.
    ///
    /// Returns `Err(EscrowError::InvalidTransition)` if the record is not in
    /// `Pending` state.
    pub fn release(&mut self) -> Result<(), EscrowError> {
        if self.state != EscrowState::Pending {
            return Err(EscrowError::InvalidTransition(format!(
                "{:?} → Released (must be Pending)",
                self.state
            )));
        }
        self.state = EscrowState::Released;
        Ok(())
    }

    /// Transition `Expired → ClawedBack`.
    ///
    /// Returns `Err(EscrowError::InvalidTransition)` if the record is not in
    /// `Expired` state.
    pub fn claw_back(&mut self) -> Result<(), EscrowError> {
        if self.state != EscrowState::Expired {
            return Err(EscrowError::InvalidTransition(format!(
                "{:?} → ClawedBack (must be Expired)",
                self.state
            )));
        }
        self.state = EscrowState::ClawedBack;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn fresh(created_at: u64) -> EscrowRecord {
        EscrowRecord::new("esc-001", 500, created_at)
    }

    #[test]
    fn not_expired_before_timeout() {
        let created = 10_000u64;
        let rec = fresh(created);
        // One second before the deadline.
        let just_before = created + ESCROW_TIMEOUT_SECS - 1;
        assert!(!rec.is_expired(just_before), "must not be expired before the deadline");
    }

    #[test]
    fn expired_at_and_after_timeout() {
        let created = 10_000u64;
        let rec = fresh(created);
        let exactly = created + ESCROW_TIMEOUT_SECS;
        assert!(rec.is_expired(exactly), "must be expired at exactly the deadline");
        assert!(rec.is_expired(exactly + 1), "must remain expired after the deadline");
    }

    #[test]
    fn release_before_expiry_succeeds() {
        let mut rec = fresh(0);
        rec.release().expect("release of a Pending record must succeed");
        assert_eq!(rec.state, EscrowState::Released);
    }

    #[test]
    fn double_release_fails() {
        let mut rec = fresh(0);
        rec.release().unwrap();
        let err = rec.release().unwrap_err();
        assert!(
            matches!(err, EscrowError::InvalidTransition(_)),
            "second release must return InvalidTransition"
        );
    }

    #[test]
    fn expire_pending_after_timeout_succeeds() {
        let created = 0u64;
        let mut rec = fresh(created);
        let now = created + ESCROW_TIMEOUT_SECS + 1;
        rec.expire(now).expect("expire must succeed after timeout");
        assert_eq!(rec.state, EscrowState::Expired);
    }

    #[test]
    fn expire_before_timeout_returns_not_expired_error() {
        let created = 0u64;
        let mut rec = fresh(created);
        let too_early = created + ESCROW_TIMEOUT_SECS - 1;
        let err = rec.expire(too_early).unwrap_err();
        assert!(matches!(err, EscrowError::NotExpired));
    }

    #[test]
    fn expire_already_released_returns_invalid_transition() {
        let mut rec = fresh(0);
        rec.release().unwrap();
        let err = rec.expire(ESCROW_TIMEOUT_SECS + 1).unwrap_err();
        assert!(matches!(err, EscrowError::InvalidTransition(_)));
    }

    #[test]
    fn claw_back_after_expire_succeeds() {
        let mut rec = fresh(0);
        rec.expire(ESCROW_TIMEOUT_SECS).unwrap();
        rec.claw_back().expect("claw_back after Expired must succeed");
        assert_eq!(rec.state, EscrowState::ClawedBack);
    }
}
