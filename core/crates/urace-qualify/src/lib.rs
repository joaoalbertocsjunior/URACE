//! `urace-qualify` — qualification trial runner, scoring, receipts, and P2P cost qualification.
//!
//! # Key invariants
//! - `QualificationEngine::qualify()` only sets `should_mint = true` when `score_delta > 0`.
//! - `TrialStore` is append-only (backed by `urace_ledger::Journal`).
//! - `UNIT = 100_000_000` (10^8 UCR base units).
//! - Mint triggers only on qualified acceptance — never on zero or negative score_delta.

pub mod p2p_cost_qualification;
pub mod qualification;
pub mod trial;
pub mod trial_receipt;

pub use p2p_cost_qualification::{P2PCostQualifier, QualificationReceipt};
pub use qualification::{QualificationEngine, QualificationError, QualificationResult};
pub use trial::{Trial, TrialConfig, TrialResult, TrialStore};
pub use trial_receipt::{ReceiptStore, TrialReceipt};

/// 1 UCR = 100_000_000 base units (10^8, satoshi-style).
pub const UNIT: u64 = 100_000_000;
