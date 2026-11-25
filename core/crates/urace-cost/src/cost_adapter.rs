//! CostAdapter trait — executor-agnostic USD cost calculation.
//!
//! Ported from `cost_adapter.py`.  litellm is NOT a dependency; pricing comes
//! from the compiled `PricingTable` in `cost_model`.
//!
//! To add a new executor type: implement `CostAdapter`, nothing else.

use crate::cost_model::PricingTable;

/// Port for computing USD cost from token usage.
pub trait CostAdapter: Send + Sync {
    /// Return USD cost, or `None` if the model is not priced
    /// (e.g. unknown local model).
    fn cost_for_usage(
        &self,
        model: &str,
        input_tokens: u64,
        output_tokens: u64,
        cache_read_tokens: u64,
        cache_write_tokens: u64,
    ) -> Option<f64>;
}

/// `CostAdapter` backed by the compiled `PricingTable`.
///
/// No external API calls are made; pricing is fully local.
pub struct DefaultCostAdapter {
    table: PricingTable,
}

impl DefaultCostAdapter {
    pub fn new() -> Self {
        DefaultCostAdapter {
            table: PricingTable::default_table(),
        }
    }

    /// Create with a custom pricing table (e.g. for tests or extended models).
    pub fn with_table(table: PricingTable) -> Self {
        DefaultCostAdapter { table }
    }
}

impl Default for DefaultCostAdapter {
    fn default() -> Self {
        Self::new()
    }
}

impl CostAdapter for DefaultCostAdapter {
    fn cost_for_usage(
        &self,
        model: &str,
        input_tokens: u64,
        output_tokens: u64,
        cache_read_tokens: u64,
        cache_write_tokens: u64,
    ) -> Option<f64> {
        self.table
            .cost_usd(
                model,
                input_tokens,
                output_tokens,
                cache_write_tokens,
                cache_read_tokens,
            )
            .ok()
    }
}

/// No-op adapter for local/unknown models where cost cannot be determined.
pub struct NullCostAdapter;

impl CostAdapter for NullCostAdapter {
    fn cost_for_usage(
        &self,
        _model: &str,
        _input_tokens: u64,
        _output_tokens: u64,
        _cache_read_tokens: u64,
        _cache_write_tokens: u64,
    ) -> Option<f64> {
        None
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn default_adapter_known_model() {
        let adapter = DefaultCostAdapter::new();
        let cost = adapter.cost_for_usage("gpt-4o", 1_000_000, 0, 0, 0);
        assert!(cost.is_some());
        // $2.50 / 1M input tokens
        assert!((cost.unwrap() - 2.50).abs() < 1e-9);
    }

    #[test]
    fn default_adapter_unknown_model() {
        let adapter = DefaultCostAdapter::new();
        assert!(adapter
            .cost_for_usage("no-such-model", 100, 100, 0, 0)
            .is_none());
    }

    #[test]
    fn null_adapter_always_none() {
        let adapter = NullCostAdapter;
        assert!(adapter.cost_for_usage("gpt-4o", 1000, 1000, 0, 0).is_none());
    }
}
