//! Performance benchmarks — throughput, velocity, longitudinal cost decay, and P2P retrieval.
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::Path;
use thiserror::Error;

#[derive(Debug, Error)]
pub enum PerfError {
    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),
    #[error("JSON error: {0}")]
    Json(#[from] serde_json::Error),
}

// ---------------------------------------------------------------------------
// Longitudinal cost decay (from benchmark_longitudinal.py)
// ---------------------------------------------------------------------------

pub const WINDOW_SIZE: usize = 10;
pub const NUM_WINDOWS: usize = 5;

/// A single longitudinal cycle record.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LongitudinalCycle {
    pub cycle: u32,
    pub task_id: String,
    pub cost_usd: f64,
    pub cache_hit_rate: f64,
    pub outcome: String,
    pub cumulative_improvements: u32,
}

/// Summary of the longitudinal run.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LongitudinalSummary {
    pub initial_cost_usd: f64,
    pub final_cost_usd: f64,
    pub cost_reduction_pct: f64,
    pub total_improvements: u32,
    pub cost_per_improvement_initial: f64,
    pub cost_per_improvement_final: f64,
}

/// Full longitudinal report.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LongitudinalReport {
    pub schema: String,
    pub generated_at: i64,
    pub mock: bool,
    pub n_cycles: u32,
    pub cycles: Vec<LongitudinalCycle>,
    pub summary: LongitudinalSummary,
}

/// Provider rates for cost calculation (USD per million tokens).
pub fn provider_rates(model: &str) -> (f64, f64) {
    match model {
        "claude-sonnet-4-6" => (3.0, 15.0),
        _ => (3.0, 15.0),
    }
}

/// Compute the USD cost for given token counts.
pub fn compute_cost(input_tokens: u32, output_tokens: u32, model: &str) -> f64 {
    let (input_rate, output_rate) = provider_rates(model);
    input_tokens as f64 / 1_000_000.0 * input_rate
        + output_tokens as f64 / 1_000_000.0 * output_rate
}

fn round8(v: f64) -> f64 {
    (v * 1e8).round() / 1e8
}

fn round4(v: f64) -> f64 {
    (v * 1e4).round() / 1e4
}

/// Build a mock 50-cycle longitudinal report with deterministic seeded randomness.
pub fn run_longitudinal_mock(n_cycles: u32) -> LongitudinalReport {
    use crate::benchmark_corpus::benchmark_tasks;
    use crate::benchmark_qualification::difficulty_tokens;

    let now = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs() as i64;

    let tasks = benchmark_tasks();
    let model = "claude-sonnet-4-6";
    let base_costs: Vec<f64> = tasks
        .iter()
        .map(|t| {
            let (inp, out) = difficulty_tokens(&t.difficulty);
            compute_cost(inp, out, model)
        })
        .collect();
    let base_cost = base_costs.iter().sum::<f64>() / base_costs.len() as f64;

    // Deterministic LCG with seed=42
    let mut rng_state: u64 = 42;
    let next_f64 = |state: &mut u64| -> f64 {
        *state = state
            .wrapping_mul(6364136223846793005)
            .wrapping_add(1442695040888963407);
        (*state >> 33) as f64 / u32::MAX as f64
    };

    let mut cycles_data: Vec<LongitudinalCycle> = Vec::new();
    let mut cumulative_improvements: u32 = 0;
    let mut gap_kind_counts: HashMap<String, u32> = HashMap::new();

    for cycle in 1..=n_cycles {
        let task = &tasks[((cycle - 1) as usize) % tasks.len()];
        let gap_kind = &task.gap_kind;

        // Cost decay: 1 / (1 + 0.08 * ln(1 + cycle))
        let decay_factor = 1.0 / (1.0 + 0.08 * ((1.0 + cycle as f64).ln()));
        let cost_usd = base_cost * decay_factor;

        // Cache hit rate
        let prior_seen = *gap_kind_counts.get(gap_kind.as_str()).unwrap_or(&0);
        let base_cache = 0.75_f64.min(0.04 * (cycle as f64).powf(0.55));
        let reuse_bonus = 0.15_f64.min(0.05 * prior_seen as f64);
        let cache_hit_rate = 0.90_f64.min(base_cache + reuse_bonus);
        *gap_kind_counts.entry(gap_kind.clone()).or_insert(0) += 1;

        // Acceptance probability: 0.5 → 0.85 linearly
        let p = 0.5 + 0.35 * (cycle as f64 / n_cycles as f64);
        let accepted = next_f64(&mut rng_state) < p;
        let outcome = if accepted {
            cumulative_improvements += 1;
            "ACCEPTED"
        } else {
            "DORMANT"
        };

        cycles_data.push(LongitudinalCycle {
            cycle,
            task_id: task.task_id.clone(),
            cost_usd: round8(cost_usd),
            cache_hit_rate: round4(cache_hit_rate),
            outcome: outcome.to_string(),
            cumulative_improvements,
        });
    }

    let initial_cost = cycles_data.first().map(|c| c.cost_usd).unwrap_or(0.0);
    let final_cost = cycles_data.last().map(|c| c.cost_usd).unwrap_or(0.0);
    let cost_reduction_pct = if initial_cost > 0.0 {
        ((1.0 - final_cost / initial_cost) * 100.0 * 100.0).round() / 100.0
    } else {
        0.0
    };

    let first5_cost: f64 = cycles_data.iter().take(5).map(|c| c.cost_usd).sum();
    let last5_cost: f64 = cycles_data.iter().rev().take(5).map(|c| c.cost_usd).sum();
    let first5_improvements = cycles_data
        .iter()
        .take(5)
        .filter(|c| c.outcome == "ACCEPTED")
        .count() as u32;
    let last5_improvements = cycles_data
        .iter()
        .rev()
        .take(5)
        .filter(|c| c.outcome == "ACCEPTED")
        .count() as u32;
    let cpi_initial = first5_cost / first5_improvements.max(1) as f64;
    let cpi_final = last5_cost / last5_improvements.max(1) as f64;

    LongitudinalReport {
        schema: "urace-benchmark-longitudinal-v1".into(),
        generated_at: now,
        mock: true,
        n_cycles,
        cycles: cycles_data,
        summary: LongitudinalSummary {
            initial_cost_usd: initial_cost,
            final_cost_usd: final_cost,
            cost_reduction_pct,
            total_improvements: cumulative_improvements,
            cost_per_improvement_initial: round8(cpi_initial),
            cost_per_improvement_final: round8(cpi_final),
        },
    }
}

/// Write longitudinal report to output_dir/longitudinal_report.json.
pub fn write_longitudinal_report(
    report: &LongitudinalReport,
    output_dir: &Path,
) -> Result<(), PerfError> {
    std::fs::create_dir_all(output_dir)?;
    std::fs::write(
        output_dir.join("longitudinal_report.json"),
        serde_json::to_string_pretty(report)?,
    )?;
    Ok(())
}

// ---------------------------------------------------------------------------
// Improvement velocity (from benchmark_velocity.py)
// ---------------------------------------------------------------------------

/// One velocity window.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VelocityWindow {
    pub window: u32,
    pub cycle_start: u32,
    pub cycle_end: u32,
    pub improvements: u32,
    pub total_cost_usd: f64,
    pub cost_per_improvement_usd: f64,
}

/// Velocity metrics derived from longitudinal data.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VelocityMetrics {
    pub windows: Vec<VelocityWindow>,
    pub velocity_ratio: f64,
    pub cost_improvement_slope: f64,
    pub first_window_improvements: u32,
    pub last_window_improvements: u32,
}

/// Linear regression slope.
pub fn linear_regression_slope(x: &[f64], y: &[f64]) -> f64 {
    let n = x.len();
    if n < 2 || x.len() != y.len() {
        return 0.0;
    }
    let n_f = n as f64;
    let sum_x: f64 = x.iter().sum();
    let sum_y: f64 = y.iter().sum();
    let sum_xy: f64 = x.iter().zip(y.iter()).map(|(xi, yi)| xi * yi).sum();
    let sum_xx: f64 = x.iter().map(|xi| xi * xi).sum();
    let denom = n_f * sum_xx - sum_x * sum_x;
    if denom.abs() < 1e-15 {
        return 0.0;
    }
    (n_f * sum_xy - sum_x * sum_y) / denom
}

/// Compute velocity metrics from longitudinal cycles.
pub fn compute_velocity_metrics(cycles: &[LongitudinalCycle]) -> VelocityMetrics {
    let n_cycles = cycles.len();
    let n_windows = NUM_WINDOWS.min(n_cycles / WINDOW_SIZE);

    let mut windows = Vec::new();
    for w in 0..n_windows {
        let start = w * WINDOW_SIZE;
        let end = start + WINDOW_SIZE;
        let window_cycles = &cycles[start..end.min(n_cycles)];
        let improvements = window_cycles
            .iter()
            .filter(|c| c.outcome == "ACCEPTED")
            .count() as u32;
        let total_cost: f64 = window_cycles.iter().map(|c| c.cost_usd).sum();
        let cost_per_improvement = total_cost / improvements.max(1) as f64;
        windows.push(VelocityWindow {
            window: w as u32 + 1,
            cycle_start: start as u32 + 1,
            cycle_end: end as u32,
            improvements,
            total_cost_usd: round8(total_cost),
            cost_per_improvement_usd: round8(cost_per_improvement),
        });
    }

    let first_window_improvements = windows.first().map(|w| w.improvements).unwrap_or(1);
    let last_window_improvements = windows.last().map(|w| w.improvements).unwrap_or(1);
    let velocity_ratio = last_window_improvements as f64 / first_window_improvements.max(1) as f64;

    let x_vals: Vec<f64> = windows.iter().map(|w| w.window as f64).collect();
    let y_vals: Vec<f64> = windows.iter().map(|w| w.cost_per_improvement_usd).collect();
    let slope = linear_regression_slope(&x_vals, &y_vals);

    VelocityMetrics {
        windows,
        velocity_ratio: round4(velocity_ratio),
        cost_improvement_slope: (slope * 1e10).round() / 1e10,
        first_window_improvements,
        last_window_improvements,
    }
}

/// Full velocity report.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VelocityReport {
    pub schema: String,
    pub generated_at: i64,
    pub n_cycles: usize,
    pub n_windows: usize,
    pub windows: Vec<VelocityWindow>,
    pub velocity_ratio: f64,
    pub cost_improvement_slope: f64,
    pub first_window_improvements: u32,
    pub last_window_improvements: u32,
}

/// Build velocity report from longitudinal data.
pub fn run_velocity_analysis(longitudinal: &LongitudinalReport) -> VelocityReport {
    let now = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs() as i64;
    let metrics = compute_velocity_metrics(&longitudinal.cycles);
    VelocityReport {
        schema: "urace-benchmark-velocity-v1".into(),
        generated_at: now,
        n_cycles: longitudinal.cycles.len(),
        n_windows: metrics.windows.len(),
        windows: metrics.windows,
        velocity_ratio: metrics.velocity_ratio,
        cost_improvement_slope: metrics.cost_improvement_slope,
        first_window_improvements: metrics.first_window_improvements,
        last_window_improvements: metrics.last_window_improvements,
    }
}

/// Write velocity report to output_dir/velocity_report.json.
pub fn write_velocity_report(report: &VelocityReport, output_dir: &Path) -> Result<(), PerfError> {
    std::fs::create_dir_all(output_dir)?;
    std::fs::write(
        output_dir.join("velocity_report.json"),
        serde_json::to_string_pretty(report)?,
    )?;
    Ok(())
}

// ---------------------------------------------------------------------------
// P2P retrieval (from p2p_retrieval_benchmark.py)
// ---------------------------------------------------------------------------

/// Dataset schema identifier.
pub const P2P_RETRIEVAL_SCHEMA: &str = "urace-p2p-retrieval-dataset-v1";

/// Validation status for a retrieval dataset.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub enum RetrievalStatus {
    HeldOutRetrievalDiagnostic,
    NonqualifyingDatasetDiagnostic,
}

/// P2P retrieval dataset header.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RetrievalDatasetHeader {
    pub schema: String,
    pub case_count: usize,
    pub split: Option<String>,
    pub dataset_kind: Option<String>,
    pub independent_reviewers: Option<usize>,
    pub disagreements_adjudicated: Option<bool>,
    pub source_description: Option<String>,
}

/// Validate whether a retrieval dataset header qualifies as held-out.
pub fn is_reviewed_dataset(header: &RetrievalDatasetHeader) -> bool {
    header.split.as_deref() == Some("held_out")
        && header.dataset_kind.as_deref() == Some("reviewed_real_work")
        && header
            .independent_reviewers
            .map(|n| n >= 2)
            .unwrap_or(false)
        && header.disagreements_adjudicated == Some(true)
        && header
            .source_description
            .as_deref()
            .map(|s| !s.trim().is_empty())
            .unwrap_or(false)
}

/// P2P retrieval benchmark result.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct P2PRetrievalResult {
    pub status: String,
    pub dataset_sha256: String,
    pub qualified_real_task_value_or_cost_claim: bool,
    pub review_provenance_self_reported: bool,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn longitudinal_mock_cycles() {
        let r = run_longitudinal_mock(50);
        assert_eq!(r.cycles.len(), 50);
        assert!(r.summary.total_improvements > 0);
    }

    #[test]
    fn cost_decays_over_time() {
        let r = run_longitudinal_mock(50);
        assert!(
            r.summary.final_cost_usd < r.summary.initial_cost_usd,
            "cost should decrease: {} vs {}",
            r.summary.final_cost_usd,
            r.summary.initial_cost_usd
        );
    }

    #[test]
    fn velocity_ratio_increases() {
        let longitudinal = run_longitudinal_mock(50);
        let v = run_velocity_analysis(&longitudinal);
        // velocity_ratio > 1 means more improvements in later window
        assert!(
            v.last_window_improvements >= v.first_window_improvements || v.windows.len() < 2,
            "velocity should not decrease: first={} last={}",
            v.first_window_improvements,
            v.last_window_improvements
        );
    }

    #[test]
    fn linear_regression_slope_negative_sequence() {
        let x = vec![1.0, 2.0, 3.0, 4.0, 5.0];
        let y = vec![5.0, 4.0, 3.0, 2.0, 1.0];
        let slope = linear_regression_slope(&x, &y);
        assert!(slope < 0.0, "expected negative slope: {slope}");
    }

    #[test]
    fn p2p_retrieval_dataset_validation() {
        let reviewed = RetrievalDatasetHeader {
            schema: P2P_RETRIEVAL_SCHEMA.into(),
            case_count: 10,
            split: Some("held_out".into()),
            dataset_kind: Some("reviewed_real_work".into()),
            independent_reviewers: Some(2),
            disagreements_adjudicated: Some(true),
            source_description: Some("real production data".into()),
        };
        assert!(is_reviewed_dataset(&reviewed));

        let not_reviewed = RetrievalDatasetHeader {
            split: Some("train".into()),
            ..reviewed
        };
        assert!(!is_reviewed_dataset(&not_reviewed));
    }
}
