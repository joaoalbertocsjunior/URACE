//! Unit arithmetic re-exported from `urace-economics`.
//! Add a dependency on `urace-economics` instead of `urace-ledger` to use
//! these constants without the full ledger engine.
pub use urace_economics::{
    earn_units, from_chain_units, from_display, spend_units, to_chain_units,
    to_display, UnitsError, PEER_CAP, UNIT, MINT_MIN_SCORE_DELTA,
};
