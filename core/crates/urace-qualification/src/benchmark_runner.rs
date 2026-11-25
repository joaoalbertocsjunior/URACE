//! Benchmark runner — orchestrates all phases and produces a KPI dashboard.
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use thiserror::Error;

/// KPI name → (lo, hi) inclusive thresholds.
pub fn kpi_thresholds() -> HashMap<&'static str, (f64, f64)> {
    let mut m = HashMap::new();
    m.insert("calibration_token_ratio_easy", (0.9, 1.1));
    m.insert("calibration_token_ratio_medium", (0.9, 1.1));
    m.insert("calibration_token_ratio_hard", (0.9, 1.1));
    m.insert("regression_good_regression_rate", (0.0, 0.0));
    m.insert("regression_detection_rate", (1.0, 1.0));
    m.insert("qualification_recall", (1.0, 1.0));
    m.insert("qualification_detection_rate", (1.0, 1.0));
    m.insert("intent_preservation_rate", (1.0, 1.0));
    m.insert("velocity_ratio", (1.0, f64::INFINITY));
    m.insert("velocity_cost_slope", (f64::NEG_INFINITY, 0.0));
    m.insert("resilience_monotonicity_violations", (0.0, 0.0));
    m.insert("resilience_recovery_cycles_max", (0.0, 3.0));
    m.insert("resilience_fault_containment_rate", (1.0, 1.0));
    m.insert("ledger_tamper_detection_rate", (1.0, 1.0));
    m.insert("ledger_false_positive_rate", (0.0, 0.0));
    m
}

/// Single phase result: either report JSON or error string.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PhaseResult {
    pub phase: String,
    pub output_dir: PathBuf,
    pub report: Option<serde_json::Value>,
    pub error: Option<String>,
}

/// KPI pass/fail for a single metric.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KpiEntry {
    pub name: String,
    pub value: f64,
    pub passed: bool,
    pub threshold_lo: f64,
    pub threshold_hi: f64,
}

/// Top-level KPI dashboard written to kpi_dashboard.json.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KpiDashboard {
    pub schema: String,
    pub generated_at: i64,
    pub mock: bool,
    pub phases_run: Vec<String>,
    pub errors: HashMap<String, String>,
    pub kpis: HashMap<String, f64>,
    pub kpi_pass: HashMap<String, bool>,
    pub all_kpis_pass: bool,
}

#[derive(Debug, Error)]
pub enum RunnerError {
    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),
    #[error("JSON error: {0}")]
    Json(#[from] serde_json::Error),
    #[error("phase {0} failed: {1}")]
    PhaseFailed(String, String),
}

fn now_unix() -> i64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs() as i64
}

/// Evaluate a KPI value against the threshold table.
pub fn evaluate_kpi(name: &str, value: f64) -> bool {
    let thresholds = kpi_thresholds();
    match thresholds.get(name) {
        Some(&(lo, hi)) => value >= lo && value <= hi,
        None => true,
    }
}

/// Build an empty dashboard skeleton (useful for progressive filling).
pub fn new_dashboard(mock: bool) -> KpiDashboard {
    KpiDashboard {
        schema: "urace-benchmark-kpi-dashboard-v1".into(),
        generated_at: now_unix(),
        mock,
        phases_run: Vec::new(),
        errors: HashMap::new(),
        kpis: HashMap::new(),
        kpi_pass: HashMap::new(),
        all_kpis_pass: false,
    }
}

/// Record a KPI in the dashboard and evaluate it.
pub fn record_kpi(dashboard: &mut KpiDashboard, name: &str, value: f64) {
    let passed = evaluate_kpi(name, value);
    dashboard.kpis.insert(name.to_string(), value);
    dashboard.kpi_pass.insert(name.to_string(), passed);
}

/// Finalize the dashboard: compute all_kpis_pass and write to output_dir/kpi_dashboard.json.
pub fn finalize_dashboard(
    dashboard: &mut KpiDashboard,
    output_dir: &Path,
) -> Result<(), RunnerError> {
    dashboard.all_kpis_pass = dashboard.kpi_pass.values().all(|&p| p);
    std::fs::create_dir_all(output_dir)?;
    let path = output_dir.join("kpi_dashboard.json");
    std::fs::write(path, serde_json::to_string_pretty(dashboard)?)?;
    Ok(())
}

/// Extract a f64 from a nested JSON path like "summary.detection_rate".
pub fn extract_f64(report: &serde_json::Value, path: &str) -> Option<f64> {
    let mut cur = report;
    for key in path.split('.') {
        cur = cur.get(key)?;
    }
    cur.as_f64()
}

/// Convenience: load a JSON report from a file.
pub fn load_report(path: &Path) -> Result<serde_json::Value, RunnerError> {
    let text = std::fs::read_to_string(path)?;
    Ok(serde_json::from_str(&text)?)
}

/// Statistics (mean, std, p95) over a slice of f64 values.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CostStatistics {
    pub mean_cost_usd: f64,
    pub std_cost_usd: f64,
    pub p95_cost_usd: f64,
}

/// Compute mean/std/p95 over a list of USD costs.
pub fn compute_statistics(costs: &[f64]) -> CostStatistics {
    if costs.is_empty() {
        return CostStatistics {
            mean_cost_usd: 0.0,
            std_cost_usd: 0.0,
            p95_cost_usd: 0.0,
        };
    }
    let n = costs.len() as f64;
    let mean = costs.iter().sum::<f64>() / n;
    let variance = costs.iter().map(|c| (c - mean).powi(2)).sum::<f64>() / n;
    let std = variance.sqrt();
    let mut sorted = costs.to_vec();
    sorted.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let p95_idx = ((0.95 * n).ceil() as usize)
        .saturating_sub(1)
        .min(sorted.len() - 1);
    CostStatistics {
        mean_cost_usd: (mean * 1e8).round() / 1e8,
        std_cost_usd: (std * 1e8).round() / 1e8,
        p95_cost_usd: (sorted[p95_idx] * 1e8).round() / 1e8,
    }
}

/// URACE blended cost multiplier from cache economics.
pub fn urace_multiplier(
    cache_fraction_first: f64,
    cache_fraction_reuse: f64,
    is_reuse: bool,
) -> f64 {
    let cf = if is_reuse {
        cache_fraction_reuse
    } else {
        cache_fraction_first
    };
    let input_ratio = (1.0 - cf) + cf * 0.10;
    0.769 * input_ratio + 0.231 * 0.85
}

/// Three-scenario sensitivity analysis over task results.
pub fn sensitivity_analysis(
    task_results: &[serde_json::Value],
    tasks: &[crate::benchmark_corpus::BenchmarkTask],
    ctrl_total: f64,
) -> serde_json::Value {
    let scenarios = [
        ("conservative_50_65", 0.50, 0.65),
        ("baseline_60_75", 0.60, 0.75),
        ("optimistic_70_85", 0.70, 0.85),
    ];
    let task_map: HashMap<&str, &str> = tasks
        .iter()
        .map(|t| (t.task_id.as_str(), t.gap_kind.as_str()))
        .collect();

    let mut out = serde_json::Map::new();
    for (label, cf_first, cf_reuse) in &scenarios {
        let mut gk_seen = std::collections::HashSet::new();
        let mut total = 0.0_f64;
        for tr in task_results {
            let tid = tr.get("task_id").and_then(|v| v.as_str()).unwrap_or("");
            let gap_kind = task_map.get(tid).copied().unwrap_or("stub");
            let control_cost = tr
                .get("control_cost_usd")
                .and_then(|v| v.as_f64())
                .unwrap_or(0.0);
            let m = urace_multiplier(*cf_first, *cf_reuse, gk_seen.contains(gap_kind));
            gk_seen.insert(gap_kind);
            total += control_cost * m;
        }
        let pct_cheaper = if ctrl_total > 0.0 {
            ((1.0 - total / ctrl_total) * 100.0 * 100.0).round() / 100.0
        } else {
            0.0
        };
        out.insert(
            label.to_string(),
            serde_json::json!({
                "cache_fraction_first": cf_first,
                "cache_fraction_reuse": cf_reuse,
                "urace_total_cost_usd": (total * 1e8).round() / 1e8,
                "urace_vs_control_pct_cheaper": pct_cheaper,
            }),
        );
    }
    serde_json::Value::Object(out)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn compute_statistics_empty() {
        let s = compute_statistics(&[]);
        assert_eq!(s.mean_cost_usd, 0.0);
    }

    #[test]
    fn compute_statistics_single() {
        let s = compute_statistics(&[1.0]);
        assert_eq!(s.mean_cost_usd, 1.0);
        assert_eq!(s.p95_cost_usd, 1.0);
    }

    #[test]
    fn evaluate_kpi_pass() {
        assert!(evaluate_kpi("regression_detection_rate", 1.0));
        assert!(!evaluate_kpi("regression_detection_rate", 0.9));
    }

    #[test]
    fn dashboard_finalize_all_pass() {
        let mut db = new_dashboard(true);
        record_kpi(&mut db, "regression_detection_rate", 1.0);
        record_kpi(&mut db, "regression_good_regression_rate", 0.0);
        let dir = tempfile::TempDir::new().unwrap();
        finalize_dashboard(&mut db, dir.path()).unwrap();
        assert!(db.all_kpis_pass);
        assert!(dir.path().join("kpi_dashboard.json").exists());
    }

    #[test]
    fn urace_multiplier_range() {
        let m = urace_multiplier(0.60, 0.75, false);
        assert!(m > 0.0 && m < 1.0, "multiplier should be < 1: {m}");
    }
}
