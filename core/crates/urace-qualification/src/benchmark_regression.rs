//! Regression guard — verifies good fixes have zero regressions, bad fixes are detected.
use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};
use std::path::Path;
use thiserror::Error;

#[derive(Debug, Error)]
pub enum RegressionError {
    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),
    #[error("JSON error: {0}")]
    Json(#[from] serde_json::Error),
    #[error("task not found: {0}")]
    TaskNotFound(String),
}

/// Per-task regression result for a good fix.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GoodFixRegressionResult {
    pub task_id: String,
    pub regressions: Vec<String>,
    pub regression_count: usize,
    pub regression_rate: f64,
}

/// Per-task regression result for a bad fix.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BadFixRegressionResult {
    pub task_id: String,
    pub regressions: Vec<String>,
    pub regression_count: usize,
    pub detected: bool,
}

/// Summary of the full regression guard run.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RegressionSummary {
    pub good_regression_rate: f64,
    pub detection_rate: f64,
    pub good_fixes_tested: usize,
    pub bad_fixes_tested: usize,
}

/// Full regression guard report.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RegressionReport {
    pub schema: String,
    pub generated_at: i64,
    pub good_fix_results: Vec<GoodFixRegressionResult>,
    pub bad_fix_results: Vec<BadFixRegressionResult>,
    pub summary: RegressionSummary,
}

/// Tests expected to break when a stub fix is applied (structural breaks, not regressions).
pub fn expected_stub_breaks() -> HashMap<&'static str, HashSet<&'static str>> {
    let mut m: HashMap<&str, HashSet<&str>> = HashMap::new();
    m.insert("medium-001", ["test_import_csv_raises"].into());
    m.insert("medium-002", ["test_forecast_spending_raises"].into());
    m.insert(
        "medium-003",
        ["test_categorize_uncategorized_raises"].into(),
    );
    m.insert("medium-004", ["test_merge_accounts_raises"].into());
    m.insert("hard-001", ["test_find_anomalies_complexity"].into());
    m.insert("hard-002", ["test_transaction_report_complexity"].into());
    m.insert("hard-003", ["test_validate_all_complexity"].into());
    m
}

/// Canonical bad fix IDs from benchmark_bad_fixes.py.
pub fn bad_fix_ids() -> Vec<&'static str> {
    vec!["bad-easy-001", "bad-medium-001", "bad-hard-001"]
}

/// Build regression results given a baseline pass/fail table and per-task after-fix tables.
/// `task_id` → after-fix pass/fail table.
pub fn compute_regression_report(
    baseline: &HashMap<String, bool>,
    good_fix_after: &HashMap<String, HashMap<String, bool>>,
    bad_fix_after: &HashMap<String, HashMap<String, bool>>,
    task_ids: &[String],
    bad_task_ids: &[String],
) -> RegressionReport {
    let stub_breaks = expected_stub_breaks();
    let now = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs() as i64;

    let mut good_fix_results = Vec::new();
    for task_id in task_ids {
        let expected_breaks = stub_breaks
            .get(task_id.as_str())
            .cloned()
            .unwrap_or_default();
        let after = good_fix_after.get(task_id).cloned().unwrap_or_default();

        let regressions: Vec<String> = baseline
            .iter()
            .filter(|(test_name, &passed_before)| {
                !expected_breaks.contains(test_name.as_str())
                    && passed_before
                    && !after.get(*test_name).copied().unwrap_or(true)
            })
            .map(|(name, _)| name.clone())
            .collect();

        let regression_rate = if regressions.is_empty() { 0.0 } else { 1.0 };
        good_fix_results.push(GoodFixRegressionResult {
            task_id: task_id.clone(),
            regression_count: regressions.len(),
            regressions,
            regression_rate,
        });
    }

    let mut bad_fix_results = Vec::new();
    for bad_task_id in bad_task_ids {
        let after = bad_fix_after.get(bad_task_id).cloned().unwrap_or_default();

        let regressions: Vec<String> = baseline
            .iter()
            .filter(|(test_name, &passed_before)| {
                passed_before && !after.get(*test_name).copied().unwrap_or(true)
            })
            .map(|(name, _)| name.clone())
            .collect();

        let detected = !regressions.is_empty();
        bad_fix_results.push(BadFixRegressionResult {
            task_id: bad_task_id.clone(),
            regression_count: regressions.len(),
            regressions,
            detected,
        });
    }

    let good_regression_rate = good_fix_results
        .iter()
        .map(|r| r.regression_rate)
        .fold(0.0_f64, f64::max);

    let total_bad = bad_fix_results.len().max(1);
    let detection_rate =
        bad_fix_results.iter().filter(|r| r.detected).count() as f64 / total_bad as f64;

    RegressionReport {
        schema: "urace-benchmark-regression-v1".into(),
        generated_at: now,
        good_fix_results,
        bad_fix_results,
        summary: RegressionSummary {
            good_regression_rate,
            detection_rate: (detection_rate * 10000.0).round() / 10000.0,
            good_fixes_tested: task_ids.len(),
            bad_fixes_tested: bad_task_ids.len(),
        },
    }
}

/// Write regression report to output_dir/regression_report.json.
pub fn write_regression_report(
    report: &RegressionReport,
    output_dir: &Path,
) -> Result<(), RegressionError> {
    std::fs::create_dir_all(output_dir)?;
    std::fs::write(
        output_dir.join("regression_report.json"),
        serde_json::to_string_pretty(report)?,
    )?;
    Ok(())
}

/// Build a mock regression report where all good fixes pass and all bad fixes are detected.
pub fn mock_regression_report(task_ids: &[String], bad_task_ids: &[String]) -> RegressionReport {
    // All tests pass in baseline
    let baseline: HashMap<String, bool> = [
        ("test_export_summary_includes_all", true),
        ("test_top_categories_returns_n", true),
        ("test_days_since_last_transaction_positive", true),
        ("test_import_csv_implemented", true),
        ("test_find_anomalies_refactored", true),
        ("test_transaction_report_linear_pass", true),
        ("test_validate_all_no_duplication", true),
    ]
    .iter()
    .map(|(k, v)| (k.to_string(), *v))
    .collect();

    // Good fixes: no regressions
    let mut good_after: HashMap<String, HashMap<String, bool>> = HashMap::new();
    for tid in task_ids {
        good_after.insert(tid.clone(), baseline.clone());
    }

    // Bad fixes: introduce a regression in a previously-passing test
    let mut bad_after: HashMap<String, HashMap<String, bool>> = HashMap::new();
    for tid in bad_task_ids {
        let mut after = baseline.clone();
        // Simulate detecting a bad fix by failing one test
        after.insert("test_export_summary_includes_all".into(), false);
        bad_after.insert(tid.clone(), after);
    }

    compute_regression_report(&baseline, &good_after, &bad_after, task_ids, bad_task_ids)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn task_ids() -> Vec<String> {
        vec!["easy-001".into(), "medium-001".into(), "hard-002".into()]
    }

    fn bad_ids() -> Vec<String> {
        vec![
            "bad-easy-001".into(),
            "bad-medium-001".into(),
            "bad-hard-001".into(),
        ]
    }

    #[test]
    fn mock_report_zero_regressions() {
        let report = mock_regression_report(&task_ids(), &bad_ids());
        assert_eq!(report.summary.good_regression_rate, 0.0);
    }

    #[test]
    fn mock_report_all_bad_detected() {
        let report = mock_regression_report(&task_ids(), &bad_ids());
        assert_eq!(report.summary.detection_rate, 1.0);
    }

    #[test]
    fn expected_stub_breaks_covers_medium_tasks() {
        let breaks = expected_stub_breaks();
        assert!(breaks.contains_key("medium-001"));
        assert!(breaks.contains_key("medium-002"));
        assert!(breaks.contains_key("medium-003"));
    }

    #[test]
    fn write_report_creates_file() {
        let dir = tempfile::TempDir::new().unwrap();
        let r = mock_regression_report(&task_ids(), &bad_ids());
        write_regression_report(&r, dir.path()).unwrap();
        assert!(dir.path().join("regression_report.json").exists());
    }

    #[test]
    fn expected_stub_breaks_all_complexity_tasks() {
        let breaks = expected_stub_breaks();
        for tid in ["hard-001", "hard-002", "hard-003"] {
            assert!(breaks.contains_key(tid), "missing breaks for {tid}");
        }
    }
}
