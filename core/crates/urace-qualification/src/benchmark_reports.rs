//! Measurement reports, ledger integrity, intent/goal fidelity, resilience, and peer exchange.
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::Path;
use thiserror::Error;

/// Embedded intent manifest (benchmark_intent_manifest.json).
pub const INTENT_MANIFEST_JSON: &str = r#"{
  "product_id": "budget-tracker-v1",
  "declared_change_surface": [
    "export_summary", "top_categories", "days_since_last_transaction",
    "import_csv", "forecast_spending", "categorize_uncategorized", "merge_accounts",
    "find_anomalies", "transaction_report", "validate_all",
    "_validate_transaction", "_anomaly_income", "_anomaly_expense"
  ],
  "off_limits": ["add_transaction", "get_balance", "get_transactions",
                 "monthly_summary", "set_budget_limit", "check_budget_alerts",
                 "__init__"]
}"#;

#[derive(Debug, Error)]
pub enum ReportError {
    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),
    #[error("JSON error: {0}")]
    Json(#[from] serde_json::Error),
    #[error("corpus not found")]
    CorpusNotFound,
    #[error("corpus modified after freezing")]
    IntegrityError,
}

// ---------------------------------------------------------------------------
// Measurement report (from measurement_report.py)
// ---------------------------------------------------------------------------

/// NOT_AVAILABLE sentinel for missing arm data.
pub const NOT_AVAILABLE: &str = "NOT_AVAILABLE";
/// NOT_RUN sentinel for data not yet collected.
pub const NOT_RUN: &str = "NOT_RUN";

/// Per-task measurement row.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TaskMeasurement {
    pub task_id: String,
    pub task_sha256: String,
    pub executor: ExecutorMeasurement,
    pub p2p: P2PMeasurement,
}

/// Executor arm measurement.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecutorMeasurement {
    pub accepted: serde_json::Value,
    pub value_score: serde_json::Value,
    pub usd_observed: serde_json::Value,
    pub usd_source: serde_json::Value,
    pub api_tokens: serde_json::Value,
    pub urace_units: serde_json::Value,
}

/// P2P arm measurement.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct P2PMeasurement {
    pub status: serde_json::Value,
    pub accepted: serde_json::Value,
    pub value_score: serde_json::Value,
    pub provider_usd: serde_json::Value,
    pub usd_source: serde_json::Value,
    pub api_tokens: serde_json::Value,
    pub urace_units: serde_json::Value,
    pub integration_steps: Vec<String>,
}

/// Full measurement report.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MeasurementReport {
    pub schema: String,
    pub task_count: usize,
    pub summary_table: serde_json::Value,
    pub per_task: Vec<TaskMeasurement>,
    pub qualification_note: String,
}

impl Default for ExecutorMeasurement {
    fn default() -> Self {
        Self {
            accepted: serde_json::Value::String(NOT_RUN.into()),
            value_score: serde_json::Value::String(NOT_RUN.into()),
            usd_observed: serde_json::Value::String(NOT_RUN.into()),
            usd_source: serde_json::Value::String(NOT_RUN.into()),
            api_tokens: serde_json::Value::String(NOT_RUN.into()),
            urace_units: serde_json::Value::String(NOT_RUN.into()),
        }
    }
}

impl Default for P2PMeasurement {
    fn default() -> Self {
        Self {
            status: serde_json::Value::String(NOT_AVAILABLE.into()),
            accepted: serde_json::Value::String(NOT_AVAILABLE.into()),
            value_score: serde_json::Value::String(NOT_AVAILABLE.into()),
            provider_usd: serde_json::Value::String(NOT_AVAILABLE.into()),
            usd_source: serde_json::Value::String(NOT_AVAILABLE.into()),
            api_tokens: serde_json::Value::String(NOT_AVAILABLE.into()),
            urace_units: serde_json::Value::String(NOT_AVAILABLE.into()),
            integration_steps: Vec::new(),
        }
    }
}

/// Build a not-yet-run measurement report from corpus records.
pub fn build_empty_measurement_report(
    task_ids: &[(String, String)], // (task_id, task_sha256)
) -> MeasurementReport {
    let per_task: Vec<TaskMeasurement> = task_ids
        .iter()
        .map(|(tid, sha)| TaskMeasurement {
            task_id: tid.clone(),
            task_sha256: sha.clone(),
            executor: ExecutorMeasurement::default(),
            p2p: P2PMeasurement::default(),
        })
        .collect();

    let summary_table = serde_json::json!({
        "comparison_valid": false,
        "comparison_blocked_reason": "P2P arm NOT_AVAILABLE — requires live peer supply with real receipts",
        "qualified_total_cost_savings": false,
        "qualified_note": "qualified_total_cost_savings requires: both arms complete, P2P provider USD < executor USD, and URACE unit → USD rate established.",
    });

    MeasurementReport {
        schema: "urace-measurement-report-v1".into(),
        task_count: per_task.len(),
        summary_table,
        per_task,
        qualification_note: concat!(
            "REAL = real tasks + real API calls + independent evaluation. ",
            "PROVIDER_RATE = real tokens × published rate; not an invoice. ",
            "NOT_AVAILABLE = P2P arm requires live network peers. ",
            "NOT_RUN = data not yet collected. ",
            "P2P provider_usd covers integration steps only; URACE units are separate.",
        )
        .into(),
    }
}

/// Write measurement report to output_dir/measurement_report.json.
pub fn write_measurement_report(
    report: &MeasurementReport,
    output_dir: &Path,
) -> Result<(), ReportError> {
    std::fs::create_dir_all(output_dir)?;
    std::fs::write(
        output_dir.join("measurement_report.json"),
        serde_json::to_string_pretty(report)?,
    )?;
    Ok(())
}

// ---------------------------------------------------------------------------
// Ledger benchmark (from benchmark_ledger.py)
// ---------------------------------------------------------------------------

/// Tamper scenario name → whether it was detected.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TamperScenarioResult {
    pub scenario: String,
    pub detected: bool,
}

/// Ledger integrity report.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LedgerReport {
    pub schema: String,
    pub generated_at: i64,
    pub scenario_results: Vec<TamperScenarioResult>,
    pub clean_ledger_verified: bool,
    pub summary: LedgerSummary,
}

/// Ledger summary metrics.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LedgerSummary {
    pub tamper_detection_rate: f64,
    pub scenarios_tested: usize,
    pub scenarios_detected: usize,
    pub false_positive_rate: f64,
}

/// Canonical tamper scenario names.
pub fn tamper_scenario_names() -> &'static [&'static str] {
    &[
        "hash_corruption",
        "entry_deletion",
        "entry_reordering",
        "duplicate_injection",
        "truncation",
    ]
}

/// Build a mock ledger report (all scenarios detected, no false positives).
pub fn mock_ledger_report() -> LedgerReport {
    let now = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs() as i64;

    let scenario_results: Vec<TamperScenarioResult> = tamper_scenario_names()
        .iter()
        .map(|name| TamperScenarioResult {
            scenario: name.to_string(),
            detected: true,
        })
        .collect();

    let total = scenario_results.len();
    LedgerReport {
        schema: "urace-benchmark-ledger-v1".into(),
        generated_at: now,
        scenario_results,
        clean_ledger_verified: true,
        summary: LedgerSummary {
            tamper_detection_rate: 1.0,
            scenarios_tested: total,
            scenarios_detected: total,
            false_positive_rate: 0.0,
        },
    }
}

/// Write ledger report to output_dir/ledger_report.json.
pub fn write_ledger_report(report: &LedgerReport, output_dir: &Path) -> Result<(), ReportError> {
    std::fs::create_dir_all(output_dir)?;
    std::fs::write(
        output_dir.join("ledger_report.json"),
        serde_json::to_string_pretty(report)?,
    )?;
    Ok(())
}

// ---------------------------------------------------------------------------
// Intent / goal fidelity (from benchmark_intent.py)
// ---------------------------------------------------------------------------

/// Intent manifest loaded from embedded JSON.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IntentManifest {
    pub product_id: String,
    pub declared_change_surface: Vec<String>,
    pub off_limits: Vec<String>,
}

/// Load the embedded intent manifest.
pub fn load_intent_manifest() -> IntentManifest {
    serde_json::from_str(INTENT_MANIFEST_JSON).expect("embedded manifest is valid JSON")
}

/// Per-task intent check result.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IntentCheckResult {
    pub task_id: String,
    pub changed_methods: Vec<String>,
    pub scope_violations: Vec<String>,
    pub out_of_surface: Vec<String>,
    pub in_scope: bool,
}

/// Full intent report.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IntentReport {
    pub schema: String,
    pub generated_at: i64,
    pub manifest: IntentManifest,
    pub good_fix_results: Vec<IntentCheckResult>,
    pub out_of_scope_results: Vec<IntentCheckResult>,
    pub summary: IntentSummary,
}

/// Intent analysis summary metrics.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IntentSummary {
    pub intent_preservation_rate: f64,
    pub scope_creep_rate: f64,
    pub oos_detection_rate: f64,
}

/// Check whether changed_methods stays within declared surface and avoids off_limits.
pub fn check_intent(
    task_id: &str,
    changed_methods: &[String],
    manifest: &IntentManifest,
) -> IntentCheckResult {
    let declared: std::collections::HashSet<&str> = manifest
        .declared_change_surface
        .iter()
        .map(String::as_str)
        .collect();
    let off_limits: std::collections::HashSet<&str> =
        manifest.off_limits.iter().map(String::as_str).collect();

    let scope_violations: Vec<String> = changed_methods
        .iter()
        .filter(|m| off_limits.contains(m.as_str()))
        .cloned()
        .collect();
    let out_of_surface: Vec<String> = changed_methods
        .iter()
        .filter(|m| !declared.contains(m.as_str()) && !off_limits.contains(m.as_str()))
        .cloned()
        .collect();
    let in_scope = scope_violations.is_empty();

    IntentCheckResult {
        task_id: task_id.to_string(),
        changed_methods: changed_methods.to_vec(),
        scope_violations,
        out_of_surface,
        in_scope,
    }
}

/// Build a mock intent report where all good fixes are in scope, OOS fixes are caught.
pub fn mock_intent_report(task_ids: &[String]) -> IntentReport {
    use crate::benchmark_corpus::benchmark_tasks;

    let now = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs() as i64;

    let manifest = load_intent_manifest();
    let tasks = benchmark_tasks();
    let task_method_map: HashMap<String, String> = tasks
        .iter()
        .map(|t| (t.task_id.clone(), t.target_method.clone()))
        .collect();

    let good_fix_results: Vec<IntentCheckResult> = task_ids
        .iter()
        .map(|tid| {
            let method = task_method_map
                .get(tid)
                .cloned()
                .unwrap_or_else(|| tid.clone());
            check_intent(tid, &[method], &manifest)
        })
        .collect();

    // Out-of-scope: modify off-limits methods
    let oos_results = vec![
        check_intent("oos-get-balance", &["get_balance".to_string()], &manifest),
        check_intent(
            "oos-add-transaction",
            &["add_transaction".to_string()],
            &manifest,
        ),
    ];

    let total_good = good_fix_results.len().max(1);
    let intent_preservation_rate =
        good_fix_results.iter().filter(|r| r.in_scope).count() as f64 / total_good as f64;
    let scope_creep_rate = 1.0 - intent_preservation_rate;
    let total_oos = oos_results.len().max(1);
    let oos_detection_rate =
        oos_results.iter().filter(|r| !r.in_scope).count() as f64 / total_oos as f64;

    IntentReport {
        schema: "urace-benchmark-intent-v1".into(),
        generated_at: now,
        manifest,
        good_fix_results,
        out_of_scope_results: oos_results,
        summary: IntentSummary {
            intent_preservation_rate: (intent_preservation_rate * 10000.0).round() / 10000.0,
            scope_creep_rate: (scope_creep_rate * 10000.0).round() / 10000.0,
            oos_detection_rate: (oos_detection_rate * 10000.0).round() / 10000.0,
        },
    }
}

/// Write intent report to output_dir/intent_report.json.
pub fn write_intent_report(report: &IntentReport, output_dir: &Path) -> Result<(), ReportError> {
    std::fs::create_dir_all(output_dir)?;
    std::fs::write(
        output_dir.join("intent_report.json"),
        serde_json::to_string_pretty(report)?,
    )?;
    Ok(())
}

// ---------------------------------------------------------------------------
// Resilience benchmark (from benchmark_resilience.py)
// ---------------------------------------------------------------------------

/// Fault cycle indices injected in the resilience benchmark.
pub const FAULT_CYCLES: [u32; 3] = [7, 13, 19];
pub const RESILIENCE_N_CYCLES: u32 = 20;

/// A single resilience cycle record.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResilienceCycle {
    pub cycle: u32,
    pub task_id: String,
    pub outcome: String,
    pub cost_usd: f64,
    pub is_fault: bool,
    pub cumulative_improvements: u32,
}

/// A fault injection event with recovery info.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FaultInjection {
    pub fault_cycle: u32,
    pub recovery_cycle: Option<u32>,
    pub recovery_cycles: u32,
    pub pre_fault_improvements: u32,
    pub post_recovery_improvements: u32,
}

/// Resilience report summary.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResilienceSummary {
    pub recovery_cycles_max: u32,
    pub recovery_cycles_mean: f64,
    pub monotonicity_violations: u32,
    pub fault_containment_rate: f64,
    pub total_improvements: u32,
}

/// Full resilience benchmark report.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResilienceReport {
    pub schema: String,
    pub generated_at: i64,
    pub n_cycles: u32,
    pub fault_cycles: Vec<u32>,
    pub cycles: Vec<ResilienceCycle>,
    pub fault_injections: Vec<FaultInjection>,
    pub summary: ResilienceSummary,
}

/// Build a mock resilience report with 20 cycles and injected faults at cycles 7, 13, 19.
pub fn mock_resilience_report() -> ResilienceReport {
    use crate::benchmark_corpus::benchmark_tasks;
    use crate::benchmark_performance::compute_cost;
    use crate::benchmark_qualification::difficulty_tokens;

    let now = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs() as i64;

    let tasks = benchmark_tasks();
    let fault_set: std::collections::HashSet<u32> = FAULT_CYCLES.iter().copied().collect();

    // Deterministic LCG seed=42
    let mut rng_state: u64 = 42;
    let next_f64 = |state: &mut u64| -> f64 {
        *state = state
            .wrapping_mul(6364136223846793005)
            .wrapping_add(1442695040888963407);
        (*state >> 33) as f64 / u32::MAX as f64
    };

    let mut cycles_data = Vec::new();
    let mut cumulative_improvements: u32 = 0;
    let mut monotonicity_violations: u32 = 0;
    let mut last_cumulative: u32 = 0;
    let mut fault_injections: Vec<FaultInjection> = Vec::new();
    let mut pre_fault: HashMap<u32, u32> = HashMap::new();
    let mut in_fault = false;
    let mut fault_start: Option<u32> = None;
    let mut fault_recovery_cycles: Vec<u32> = Vec::new();
    let n_cycles = RESILIENCE_N_CYCLES;

    for cycle in 1..=n_cycles {
        let task = &tasks[((cycle - 1) as usize) % tasks.len()];
        let (inp, out) = difficulty_tokens(&task.difficulty);
        let base = compute_cost(inp, out, "claude-sonnet-4-6");
        let decay = 1.0 / (1.0 + 0.08 * ((1.0 + cycle as f64).ln()));
        let is_fault = fault_set.contains(&cycle);

        let (cost_usd, outcome) = if is_fault {
            pre_fault.insert(cycle, cumulative_improvements);
            in_fault = true;
            fault_start = Some(cycle);
            (base * decay * 2.0, "ERROR")
        } else {
            let p = 0.5 + 0.35 * (cycle as f64 / n_cycles as f64);
            if next_f64(&mut rng_state) < p {
                cumulative_improvements += 1;
                if in_fault {
                    if let Some(fs) = fault_start {
                        let recovery = cycle - fs;
                        fault_recovery_cycles.push(recovery);
                        fault_injections.push(FaultInjection {
                            fault_cycle: fs,
                            recovery_cycle: Some(cycle),
                            recovery_cycles: recovery,
                            pre_fault_improvements: *pre_fault.get(&fs).unwrap_or(&0),
                            post_recovery_improvements: cumulative_improvements,
                        });
                        in_fault = false;
                        fault_start = None;
                    }
                }
                (base * decay, "ACCEPTED")
            } else {
                (base * decay, "DORMANT")
            }
        };

        if cumulative_improvements < last_cumulative {
            monotonicity_violations += 1;
        }
        last_cumulative = cumulative_improvements;

        cycles_data.push(ResilienceCycle {
            cycle,
            task_id: task.task_id.clone(),
            outcome: outcome.to_string(),
            cost_usd: (cost_usd * 1e8).round() / 1e8,
            is_fault,
            cumulative_improvements,
        });
    }

    // Any still-open fault
    if in_fault {
        if let Some(fs) = fault_start {
            let bound = n_cycles - fs + 1;
            fault_recovery_cycles.push(bound);
            fault_injections.push(FaultInjection {
                fault_cycle: fs,
                recovery_cycle: None,
                recovery_cycles: bound,
                pre_fault_improvements: *pre_fault.get(&fs).unwrap_or(&0),
                post_recovery_improvements: cumulative_improvements,
            });
        }
    }

    let recovery_cycles_max = fault_recovery_cycles.iter().copied().max().unwrap_or(0);
    let recovery_cycles_mean = if fault_recovery_cycles.is_empty() {
        0.0
    } else {
        fault_recovery_cycles.iter().sum::<u32>() as f64 / fault_recovery_cycles.len() as f64
    };

    let fault_containment_checks: Vec<bool> = fault_injections
        .iter()
        .filter(|fi| fi.recovery_cycle.is_some())
        .map(|fi| fi.post_recovery_improvements >= fi.pre_fault_improvements)
        .collect();
    let fault_containment_rate = if fault_containment_checks.is_empty() {
        1.0
    } else {
        fault_containment_checks.iter().filter(|&&b| b).count() as f64
            / fault_containment_checks.len() as f64
    };

    ResilienceReport {
        schema: "urace-benchmark-resilience-v1".into(),
        generated_at: now,
        n_cycles,
        fault_cycles: FAULT_CYCLES.to_vec(),
        cycles: cycles_data,
        fault_injections,
        summary: ResilienceSummary {
            recovery_cycles_max,
            recovery_cycles_mean: (recovery_cycles_mean * 100.0).round() / 100.0,
            monotonicity_violations,
            fault_containment_rate: (fault_containment_rate * 10000.0).round() / 10000.0,
            total_improvements: cumulative_improvements,
        },
    }
}

/// Write resilience report to output_dir/resilience_report.json.
pub fn write_resilience_report(
    report: &ResilienceReport,
    output_dir: &Path,
) -> Result<(), ReportError> {
    std::fs::create_dir_all(output_dir)?;
    std::fs::write(
        output_dir.join("resilience_report.json"),
        serde_json::to_string_pretty(report)?,
    )?;
    Ok(())
}

// ---------------------------------------------------------------------------
// Peer exchange (from benchmark_peer_exchange.py)
// ---------------------------------------------------------------------------

/// Peer exchange benchmark is blocked pending subsystem stability.
pub fn run_peer_exchange_benchmark(_output_dir: &Path) -> Result<(), ReportError> {
    Err(ReportError::Io(std::io::Error::new(
        std::io::ErrorKind::Unsupported,
        "Phase 6 blocked: peer_exchange subsystem not yet production-stable",
    )))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn intent_manifest_loads() {
        let m = load_intent_manifest();
        assert_eq!(m.product_id, "budget-tracker-v1");
        assert!(!m.declared_change_surface.is_empty());
        assert!(!m.off_limits.is_empty());
    }

    #[test]
    fn intent_check_off_limits_detected() {
        let manifest = load_intent_manifest();
        let result = check_intent("bad-task", &["get_balance".to_string()], &manifest);
        assert!(!result.in_scope);
        assert_eq!(result.scope_violations, vec!["get_balance"]);
    }

    #[test]
    fn mock_ledger_all_scenarios_detected() {
        let r = mock_ledger_report();
        assert_eq!(r.summary.tamper_detection_rate, 1.0);
        assert_eq!(r.summary.false_positive_rate, 0.0);
    }

    #[test]
    fn resilience_monotonicity_never_violated() {
        let r = mock_resilience_report();
        assert_eq!(r.summary.monotonicity_violations, 0);
    }

    #[test]
    fn measurement_report_builds_empty() {
        let tasks: Vec<(String, String)> = vec![
            ("easy-001".into(), "abc123".into()),
            ("easy-002".into(), "def456".into()),
        ];
        let r = build_empty_measurement_report(&tasks);
        assert_eq!(r.task_count, 2);
        assert_eq!(
            r.per_task[0].executor.accepted,
            serde_json::Value::String(NOT_RUN.into())
        );
        assert_eq!(
            r.per_task[0].p2p.status,
            serde_json::Value::String(NOT_AVAILABLE.into())
        );
    }
}
