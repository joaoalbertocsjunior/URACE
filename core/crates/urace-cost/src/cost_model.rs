//! LLM pricing table — compiled-in, no external API call for pricing.
//!
//! Pricing is a compiled table following the same approach as `cost_model.py`'s
//! `PROVIDER_RATES` / `PROVIDER_RATE_TABLE`. litellm is NOT used; instead the
//! rates are baked in here.  Callers can extend the table at runtime by calling
//! `PricingTable::insert`.
//!
//! Rates are in USD per 1 million tokens (per-1M convention).

use std::collections::HashMap;
use thiserror::Error;

/// Per-model pricing entry (USD per 1 million tokens).
#[derive(Debug, Clone)]
pub struct ModelRates {
    pub input_per_1m_usd: f64,
    pub output_per_1m_usd: f64,
    /// Cache-write surcharge; 0.0 if provider does not expose it.
    pub cache_write_per_1m_usd: f64,
    /// Cache-read discount; 0.0 if provider does not expose it.
    pub cache_read_per_1m_usd: f64,
    pub provider: &'static str,
    /// Informational: "anthropic.com/pricing", "openai.com/api/pricing", etc.
    pub rate_source: &'static str,
    /// Informational: when this rate snapshot was taken ("2025-11").
    pub rate_effective: &'static str,
}

impl ModelRates {
    /// Compute USD cost for a given token usage.
    pub fn cost_usd(
        &self,
        input_tokens: u64,
        output_tokens: u64,
        cache_write_tokens: u64,
        cache_read_tokens: u64,
    ) -> f64 {
        let m = 1_000_000.0_f64;
        input_tokens as f64 / m * self.input_per_1m_usd
            + output_tokens as f64 / m * self.output_per_1m_usd
            + cache_write_tokens as f64 / m * self.cache_write_per_1m_usd
            + cache_read_tokens as f64 / m * self.cache_read_per_1m_usd
    }
}

#[derive(Debug, Error)]
pub enum PricingError {
    #[error("no published rate for model {0:?}; add it to PricingTable")]
    UnknownModel(String),
}

/// Runtime-extensible pricing table backed by a compiled default set.
pub struct PricingTable {
    inner: HashMap<String, ModelRates>,
}

impl PricingTable {
    /// Build the default table from published provider rates (2025-11 snapshot).
    pub fn default_table() -> Self {
        let mut t = HashMap::new();

        macro_rules! rate {
            ($name:expr, $in:expr, $out:expr, $cw:expr, $cr:expr, $provider:expr, $source:expr, $eff:expr) => {
                t.insert(
                    $name.to_string(),
                    ModelRates {
                        input_per_1m_usd: $in,
                        output_per_1m_usd: $out,
                        cache_write_per_1m_usd: $cw,
                        cache_read_per_1m_usd: $cr,
                        provider: $provider,
                        rate_source: $source,
                        rate_effective: $eff,
                    },
                )
            };
        }

        // ── Anthropic ──────────────────────────────────────────────────────────
        rate!(
            "claude-3-5-sonnet",
            3.00,
            15.00,
            3.75,
            0.30,
            "anthropic",
            "anthropic.com/pricing",
            "2025-11"
        );
        // Alias used in Python source
        rate!(
            "claude-sonnet-4-6",
            3.00,
            15.00,
            3.75,
            0.30,
            "anthropic",
            "anthropic.com/pricing",
            "2025-11"
        );
        rate!(
            "claude-3-5-haiku",
            0.80,
            4.00,
            1.00,
            0.08,
            "anthropic",
            "anthropic.com/pricing",
            "2025-11"
        );
        // Alias
        rate!(
            "claude-haiku-4-5-20251001",
            0.80,
            4.00,
            1.00,
            0.08,
            "anthropic",
            "anthropic.com/pricing",
            "2025-11"
        );
        rate!(
            "claude-3-opus",
            15.00,
            75.00,
            18.75,
            1.50,
            "anthropic",
            "anthropic.com/pricing",
            "2025-11"
        );
        // Alias
        rate!(
            "claude-opus-4-7",
            15.00,
            75.00,
            18.75,
            1.50,
            "anthropic",
            "anthropic.com/pricing",
            "2025-11"
        );

        // ── OpenAI ─────────────────────────────────────────────────────────────
        rate!(
            "gpt-4o",
            2.50,
            10.00,
            0.00,
            1.25,
            "openai",
            "openai.com/api/pricing",
            "2025-11"
        );
        rate!(
            "gpt-4o-mini",
            0.15,
            0.60,
            0.00,
            0.075,
            "openai",
            "openai.com/api/pricing",
            "2025-11"
        );
        rate!(
            "gpt-4-turbo",
            10.00,
            30.00,
            0.00,
            0.00,
            "openai",
            "openai.com/api/pricing",
            "2025-11"
        );
        rate!(
            "gpt-3.5-turbo",
            0.50,
            1.50,
            0.00,
            0.00,
            "openai",
            "openai.com/api/pricing",
            "2025-11"
        );

        // ── Mistral ────────────────────────────────────────────────────────────
        rate!(
            "mistral-large-latest",
            4.00,
            12.00,
            0.00,
            0.00,
            "mistral",
            "mistral.ai/pricing",
            "2025-11"
        );
        rate!(
            "mistral-small-latest",
            1.00,
            3.00,
            0.00,
            0.00,
            "mistral",
            "mistral.ai/pricing",
            "2025-11"
        );

        PricingTable { inner: t }
    }

    /// Look up rates for `model`, returning an error for unknown models.
    pub fn get(&self, model: &str) -> Result<&ModelRates, PricingError> {
        self.inner
            .get(model)
            .ok_or_else(|| PricingError::UnknownModel(model.to_owned()))
    }

    /// Insert or replace a model's rates (allows runtime extension).
    pub fn insert(&mut self, model: impl Into<String>, rates: ModelRates) {
        self.inner.insert(model.into(), rates);
    }

    /// List all known model names.
    pub fn models(&self) -> Vec<&str> {
        let mut names: Vec<&str> = self.inner.keys().map(|s| s.as_str()).collect();
        names.sort();
        names
    }

    /// Compute USD cost for a model directly.
    pub fn cost_usd(
        &self,
        model: &str,
        input_tokens: u64,
        output_tokens: u64,
        cache_write_tokens: u64,
        cache_read_tokens: u64,
    ) -> Result<f64, PricingError> {
        let rates = self.get(model)?;
        Ok(rates.cost_usd(
            input_tokens,
            output_tokens,
            cache_write_tokens,
            cache_read_tokens,
        ))
    }
}

impl Default for PricingTable {
    fn default() -> Self {
        Self::default_table()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn known_models_present() {
        let t = PricingTable::default_table();
        for model in &[
            "gpt-4o",
            "gpt-4-turbo",
            "gpt-3.5-turbo",
            "claude-3-5-sonnet",
            "claude-3-5-haiku",
            "claude-3-opus",
        ] {
            assert!(t.get(model).is_ok(), "missing model: {model}");
        }
    }

    #[test]
    fn zero_tokens_zero_cost() {
        let t = PricingTable::default_table();
        let cost = t.cost_usd("gpt-4o", 0, 0, 0, 0).unwrap();
        assert_eq!(cost, 0.0);
    }

    #[test]
    fn cost_calculation() {
        let t = PricingTable::default_table();
        // 1M input + 1M output at $2.50/$10.00 = $12.50
        let cost = t.cost_usd("gpt-4o", 1_000_000, 1_000_000, 0, 0).unwrap();
        assert!((cost - 12.50).abs() < 1e-9, "expected 12.50 got {cost}");
    }

    #[test]
    fn unknown_model_error() {
        let t = PricingTable::default_table();
        assert!(matches!(
            t.get("no-such-model"),
            Err(PricingError::UnknownModel(_))
        ));
    }

    #[test]
    fn runtime_extension() {
        let mut t = PricingTable::default_table();
        t.insert(
            "my-custom-model",
            ModelRates {
                input_per_1m_usd: 1.0,
                output_per_1m_usd: 2.0,
                cache_write_per_1m_usd: 0.0,
                cache_read_per_1m_usd: 0.0,
                provider: "custom",
                rate_source: "internal",
                rate_effective: "2025-11",
            },
        );
        assert!(t.get("my-custom-model").is_ok());
    }
}
