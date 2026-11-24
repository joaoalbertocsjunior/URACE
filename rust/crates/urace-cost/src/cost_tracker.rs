//! Executor-agnostic per-operation cost tracking.
//!
//! Ported from `cost_tracker.py`.
//!
//! `CostRecord` captures token counts, USD cost, provider, and session context
//! for a single LLM call. `CostLedger` accumulates records in-process and
//! exposes aggregate queries.
//!
//! Key invariant: pricing is computed locally via the compiled `PricingTable`.
//! No external API call is made for pricing.

use crate::cost_adapter::{CostAdapter, DefaultCostAdapter};
use parking_lot::Mutex;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::Arc;

/// Uniform cost record across all executor types.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CostRecord {
    /// E.g. "anthropic", "openai", "local", "custom".
    pub provider: String,
    pub model: String,
    /// Caller-supplied operation identifier (e.g. task ID, session step).
    pub operation_id: String,
    pub session_id: String,
    pub input_tokens: u64,
    pub output_tokens: u64,
    pub cache_read_tokens: u64,
    pub cache_write_tokens: u64,
    /// USD cost; `None` if the model is unknown to the pricing table.
    pub cost_usd: Option<f64>,
    pub latency_ms: f64,
    /// ISO-8601 / Unix timestamp string when the record was created.
    pub at: String,
}

impl CostRecord {
    pub fn total_tokens(&self) -> u64 {
        self.input_tokens
            + self.output_tokens
            + self.cache_read_tokens
            + self.cache_write_tokens
    }
}

/// In-process ledger for accumulating `CostRecord`s within a session.
///
/// Thread-safe via `Mutex`. All mutations go through `record_call`.
pub struct CostLedger {
    records: Mutex<Vec<CostRecord>>,
    adapter: Arc<dyn CostAdapter>,
}

impl CostLedger {
    /// Create a new `CostLedger` backed by the default compiled pricing table.
    pub fn new() -> Self {
        CostLedger {
            records: Mutex::new(Vec::new()),
            adapter: Arc::new(DefaultCostAdapter::new()),
        }
    }

    /// Create with a custom `CostAdapter` (useful for tests or custom providers).
    pub fn with_adapter(adapter: Arc<dyn CostAdapter>) -> Self {
        CostLedger { records: Mutex::new(Vec::new()), adapter }
    }

    /// Record a single LLM call and compute USD cost via the adapter.
    pub fn record_call(
        &self,
        provider: impl Into<String>,
        model: impl Into<String>,
        operation_id: impl Into<String>,
        session_id: impl Into<String>,
        input_tokens: u64,
        output_tokens: u64,
        cache_read_tokens: u64,
        cache_write_tokens: u64,
        latency_ms: f64,
    ) -> CostRecord {
        let model = model.into();
        let cost_usd = self.adapter.cost_for_usage(
            &model,
            input_tokens,
            output_tokens,
            cache_read_tokens,
            cache_write_tokens,
        );
        let rec = CostRecord {
            provider: provider.into(),
            model,
            operation_id: operation_id.into(),
            session_id: session_id.into(),
            input_tokens,
            output_tokens,
            cache_read_tokens,
            cache_write_tokens,
            cost_usd,
            latency_ms,
            at: now_iso(),
        };
        self.records.lock().push(rec.clone());
        rec
    }

    /// Return a snapshot of all stored records.
    pub fn records(&self) -> Vec<CostRecord> {
        self.records.lock().clone()
    }

    /// Sum of all known USD costs; `None` if no priced record has been stored.
    pub fn total_cost_usd(&self) -> Option<f64> {
        let known: Vec<f64> = self
            .records
            .lock()
            .iter()
            .filter_map(|r| r.cost_usd)
            .collect();
        if known.is_empty() { None } else { Some(known.iter().sum()) }
    }

    /// USD cost for a specific session; `None` if no priced record for that session.
    pub fn session_cost_usd(&self, session_id: &str) -> Option<f64> {
        let known: Vec<f64> = self
            .records
            .lock()
            .iter()
            .filter(|r| r.session_id == session_id)
            .filter_map(|r| r.cost_usd)
            .collect();
        if known.is_empty() { None } else { Some(known.iter().sum()) }
    }

    /// Return `true` if total known USD cost exceeds `budget_usd`.
    pub fn exceeds_budget(&self, budget_usd: f64) -> bool {
        self.total_cost_usd().map_or(false, |t| t > budget_usd)
    }

    /// Compact summary dict for cost snapshot reporting.
    pub fn cost_snapshot(&self) -> HashMap<String, serde_json::Value> {
        let records = self.records.lock();
        let total_tokens: u64 = records.iter().map(|r| r.total_tokens()).sum();
        let total_usd: Option<f64> = {
            let known: Vec<f64> = records.iter().filter_map(|r| r.cost_usd).collect();
            if known.is_empty() { None } else { Some(known.iter().sum()) }
        };
        let providers: Vec<String> = {
            let mut set: std::collections::HashSet<String> = std::collections::HashSet::new();
            for r in records.iter() {
                set.insert(r.provider.clone());
            }
            let mut v: Vec<String> = set.into_iter().collect();
            v.sort();
            v
        };
        let mut m = HashMap::new();
        m.insert("records".to_string(), serde_json::json!(records.len()));
        m.insert("total_tokens".to_string(), serde_json::json!(total_tokens));
        m.insert(
            "total_usd".to_string(),
            total_usd.map_or(serde_json::Value::Null, |v| serde_json::json!(v)),
        );
        m.insert("providers".to_string(), serde_json::json!(providers));
        m
    }

    /// Per-model breakdown: model -> {records, input_tokens, output_tokens, cost_usd}.
    pub fn breakdown_by_model(&self) -> HashMap<String, serde_json::Value> {
        let records = self.records.lock();
        let mut groups: HashMap<String, (usize, u64, u64, Vec<f64>)> = HashMap::new();
        for r in records.iter() {
            let e = groups.entry(r.model.clone()).or_default();
            e.0 += 1;
            e.1 += r.input_tokens;
            e.2 += r.output_tokens;
            if let Some(c) = r.cost_usd { e.3.push(c); }
        }
        groups
            .into_iter()
            .map(|(model, (count, input, output, costs))| {
                let cost_usd = if costs.is_empty() {
                    serde_json::Value::Null
                } else {
                    serde_json::json!(costs.iter().sum::<f64>())
                };
                (
                    model,
                    serde_json::json!({
                        "records": count,
                        "input_tokens": input,
                        "output_tokens": output,
                        "cost_usd": cost_usd,
                    }),
                )
            })
            .collect()
    }
}

impl Default for CostLedger {
    fn default() -> Self {
        Self::new()
    }
}

fn now_iso() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| format!("{:.3}", d.as_secs_f64()))
        .unwrap_or_else(|_| "0".to_string())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::cost_adapter::NullCostAdapter;

    fn session() -> String {
        uuid::Uuid::new_v4().to_string()
    }

    #[test]
    fn record_call_stores_record() {
        let ledger = CostLedger::new();
        let sid = session();
        let rec = ledger.record_call(
            "anthropic", "claude-3-5-sonnet", "op-1", &sid,
            1000, 500, 0, 0, 100.0,
        );
        assert_eq!(rec.input_tokens, 1000);
        assert!(rec.cost_usd.is_some());
        assert_eq!(ledger.records().len(), 1);
    }

    #[test]
    fn total_cost_usd_sums_known() {
        let ledger = CostLedger::new();
        let sid = session();
        ledger.record_call("openai", "gpt-4o", "op-1", &sid, 1_000_000, 0, 0, 0, 0.0);
        ledger.record_call("openai", "gpt-4o", "op-2", &sid, 1_000_000, 0, 0, 0, 0.0);
        let total = ledger.total_cost_usd().unwrap();
        // 2 × $2.50 = $5.00
        assert!((total - 5.00).abs() < 1e-9, "expected 5.00, got {total}");
    }

    #[test]
    fn session_cost_isolated() {
        let ledger = CostLedger::new();
        let sid1 = session();
        let sid2 = session();
        ledger.record_call("openai", "gpt-4o", "op-1", &sid1, 1_000_000, 0, 0, 0, 0.0);
        ledger.record_call("openai", "gpt-4o", "op-2", &sid2, 1_000_000, 0, 0, 0, 0.0);
        let s1 = ledger.session_cost_usd(&sid1).unwrap();
        assert!((s1 - 2.50).abs() < 1e-9);
    }

    #[test]
    fn null_adapter_no_cost() {
        let ledger = CostLedger::with_adapter(Arc::new(NullCostAdapter));
        let sid = session();
        let rec = ledger.record_call("local", "my-model", "op", &sid, 100, 100, 0, 0, 0.0);
        assert!(rec.cost_usd.is_none());
        assert!(ledger.total_cost_usd().is_none());
    }

    #[test]
    fn exceeds_budget() {
        let ledger = CostLedger::new();
        let sid = session();
        // 1M output tokens at $10/1M = $10
        ledger.record_call("openai", "gpt-4o", "op", &sid, 0, 1_000_000, 0, 0, 0.0);
        assert!(!ledger.exceeds_budget(20.0));
        assert!(ledger.exceeds_budget(5.0));
    }

    #[test]
    fn breakdown_by_model_groups() {
        let ledger = CostLedger::new();
        let sid = session();
        ledger.record_call("openai", "gpt-4o", "op-1", &sid, 100, 0, 0, 0, 0.0);
        ledger.record_call("openai", "gpt-4o", "op-2", &sid, 200, 0, 0, 0, 0.0);
        ledger.record_call("openai", "gpt-3.5-turbo", "op-3", &sid, 100, 0, 0, 0, 0.0);
        let breakdown = ledger.breakdown_by_model();
        assert_eq!(breakdown["gpt-4o"]["records"], 2);
        assert_eq!(breakdown["gpt-3.5-turbo"]["records"], 1);
    }
}
