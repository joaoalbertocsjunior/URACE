//! `urace-audit` — append-only audit trail for all URACE runtime events.
//!
//! # Modules
//! - [`audit_kinds`] — canonical `AuditKind` taxonomy
//! - [`audit_ledger`] — `AuditLedger` backed by `urace-ledger::Journal`
//! - [`governance_audit`] — `GovernanceAuditor` for policy/authority events
//! - [`spec_audit`]       — `SpecAuditor` for invariant verification

pub mod audit_kinds;
pub mod audit_ledger;
pub mod chain_integrity;
pub mod governance_audit;
pub mod spec_audit;

pub use audit_kinds::AuditKind;
pub use audit_ledger::{AuditError, AuditEvent, AuditLedger};
pub use chain_integrity::{verify_audit_chain, ChainIntegrityReport};
pub use governance_audit::GovernanceAuditor;
pub use spec_audit::{
    detect_siphon_anomalies, MintRecord, SpecAuditor, SIPHON_MAX_SHARE_FRACTION,
};
