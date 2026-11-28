//! `urace-cost` — executor-agnostic LLM cost tracking and pricing table.
//!
//! # Key invariant
//! Pricing is a compiled table — no external API call (no litellm).
//! All cost calculations are local.
//!
//! # Modules
//! - [`cost_model`] — LLM pricing table (HashMap-based, extensible at runtime)
//! - [`cost_adapter`] — `CostAdapter` trait + `DefaultCostAdapter` / `NullCostAdapter`
//! - [`cost_tracker`] — `CostRecord`, `CostLedger`

pub mod baseline;
pub mod cost_adapter;
pub mod cost_model;
pub mod cost_tracker;

pub use baseline::{
    CostComparison, DirectCallBaseline, BaselineError,
    MIN_NET_SAVINGS_BPS, PROTOCOL_FEE_BPS,
};
pub use cost_adapter::{CostAdapter, DefaultCostAdapter, NullCostAdapter};
pub use cost_model::{ModelRates, PricingError, PricingTable};
pub use cost_tracker::{CostLedger, CostRecord};
