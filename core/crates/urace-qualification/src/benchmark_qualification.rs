//! Qualification signal — precision/recall of acceptance gate vs extended gate, and calibration.
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::Path;
use thiserror::Error;

#[derive(Debug, Error)]
pub enum QualSignalError {
    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),
    #[error("JSON error: {0}")]
    Json(#[from] serde_json::Error),
    #[error("task not found: {0}")]
    TaskNotFound(String),
}

/// Per-task result for good-fix extended gate check.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GoodFixResult {
    pub task_id: String,
    pub passes_extended_gate: bool,
}

/// Per-task result for bad-fix narrow gate check.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BadFixNarrowResult {
    pub task_id: String,
    pub passes_narrow_gate: bool,
}

/// Per-task result for bad-fix extended gate check.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BadFixExtendedResult {
    pub task_id: String,
    pub passes_extended_gate: bool,
    pub caught_by_extended: bool,
}

/// Summary of qualification signal analysis.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QualificationSummary {
    pub good_recall_extended_gate: f64,
    pub narrow_false_positives: usize,
    pub extended_false_positives: usize,
    pub detection_rate_extended: f64,
    pub extended_gate_better_precision: bool,
}

/// Full qualification report.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QualificationReport {
    pub schema: String,
    pub generated_at: i64,
    pub good_fix_extended_results: Vec<GoodFixResult>,
    pub bad_fix_narrow_results: Vec<BadFixNarrowResult>,
    pub bad_fix_extended_results: Vec<BadFixExtendedResult>,
    pub summary: QualificationSummary,
}

/// Deterministic mock quality gate: good fixes always pass, bad fixes always fail.
/// In a real integration this would run pytest via subprocess.
pub fn mock_extended_gate(_task_id: &str, is_good_fix: bool) -> bool {
    is_good_fix
}

/// Compute qualification signal from pre-evaluated pass/fail tables.
/// `good_extended`: (task_id, passes_extended) for good fixes.
/// `bad_narrow`: (bad_task_id, passes_narrow) for bad fixes narrow gate.
/// `bad_extended`: (bad_task_id, passes_extended) for bad fixes extended gate.
pub fn compute_qualification_report(
    good_task_ids: &[String],
    bad_task_ids: &[String],
    good_extended: &[(String, bool)],
    bad_narrow: &[(String, bool)],
    bad_extended: &[(String, bool)],
) -> QualificationReport {
    let _ = good_task_ids;
    let _ = bad_task_ids;

    let good_fix_extended_results: Vec<GoodFixResult> = good_extended
        .iter()
        .map(|(tid, passes)| GoodFixResult {
            task_id: tid.clone(),
            passes_extended_gate: *passes,
        })
        .collect();

    let total_good = good_fix_extended_results.len().max(1);
    let good_recall_extended = good_fix_extended_results
        .iter()
        .filter(|r| r.passes_extended_gate)
        .count() as f64
        / total_good as f64;

    let bad_fix_narrow_results: Vec<BadFixNarrowResult> = bad_narrow
        .iter()
        .map(|(tid, passes)| BadFixNarrowResult {
            task_id: tid.clone(),
            passes_narrow_gate: *passes,
        })
        .collect();

    let bad_fix_extended_results: Vec<BadFixExtendedResult> = bad_extended
        .iter()
        .map(|(tid, passes)| BadFixExtendedResult {
            task_id: tid.clone(),
            passes_extended_gate: *passes,
            caught_by_extended: !passes,
        })
        .collect();

    let narrow_false_positives = bad_fix_narrow_results
        .iter()
        .filter(|r| r.passes_narrow_gate)
        .count();
    let extended_false_positives = bad_fix_extended_results
        .iter()
        .filter(|r| r.passes_extended_gate)
        .count();

    let total_bad = bad_fix_extended_results.len().max(1);
    let detection_rate_extended = bad_fix_extended_results
        .iter()
        .filter(|r| r.caught_by_extended)
        .count() as f64
        / total_bad as f64;

    let now = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs() as i64;

    QualificationReport {
        schema: "urace-benchmark-qualification-v1".into(),
        generated_at: now,
        good_fix_extended_results,
        bad_fix_narrow_results,
        bad_fix_extended_results,
        summary: QualificationSummary {
            good_recall_extended_gate: (good_recall_extended * 10000.0).round() / 10000.0,
            narrow_false_positives,
            extended_false_positives,
            detection_rate_extended: (detection_rate_extended * 10000.0).round() / 10000.0,
            extended_gate_better_precision: extended_false_positives < narrow_false_positives,
        },
    }
}

/// Write qualification report to output_dir/qualification_report.json.
pub fn write_qualification_report(
    report: &QualificationReport,
    output_dir: &Path,
) -> Result<(), QualSignalError> {
    std::fs::create_dir_all(output_dir)?;
    let path = output_dir.join("qualification_report.json");
    std::fs::write(path, serde_json::to_string_pretty(report)?)?;
    Ok(())
}

// ---------------------------------------------------------------------------
// Calibration (from benchmark_calibration.py)
// ---------------------------------------------------------------------------

/// Token budget per difficulty tier (calibrated to Claude Sonnet).
pub fn difficulty_tokens(difficulty: &str) -> (u32, u32) {
    match difficulty {
        "easy" => (1200, 360),
        "hard" => (4500, 1350),
        _ => (2800, 840), // medium
    }
}

/// Per-tier calibration entry.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CalibrationTier {
    pub estimated_input: u32,
    pub estimated_output: u32,
    pub actual_input: u32,
    pub actual_output: u32,
    pub token_ratio: f64,
}

/// Calibration report.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CalibrationReport {
    pub schema: String,
    pub generated_at: i64,
    pub mock: bool,
    pub tiers: HashMap<String, CalibrationTier>,
}

/// Build a mock calibration report (actual == estimated, ratio == 1.0).
pub fn mock_calibration_report() -> CalibrationReport {
    let now = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs() as i64;

    let mut tiers = HashMap::new();
    for tier in ["easy", "medium", "hard"] {
        let (input, output) = difficulty_tokens(tier);
        tiers.insert(
            tier.to_string(),
            CalibrationTier {
                estimated_input: input,
                estimated_output: output,
                actual_input: input,
                actual_output: output,
                token_ratio: 1.0,
            },
        );
    }
    CalibrationReport {
        schema: "urace-benchmark-calibration-v1".into(),
        generated_at: now,
        mock: true,
        tiers,
    }
}

/// Write calibration report to output_dir/calibration_report.json.
pub fn write_calibration_report(
    report: &CalibrationReport,
    output_dir: &Path,
) -> Result<(), QualSignalError> {
    std::fs::create_dir_all(output_dir)?;
    let path = output_dir.join("calibration_report.json");
    std::fs::write(path, serde_json::to_string_pretty(report)?)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn mock_calibration_has_three_tiers() {
        let r = mock_calibration_report();
        assert!(r.tiers.contains_key("easy"));
        assert!(r.tiers.contains_key("medium"));
        assert!(r.tiers.contains_key("hard"));
    }

    #[test]
    fn mock_calibration_ratio_is_one() {
        let r = mock_calibration_report();
        for tier in r.tiers.values() {
            assert_eq!(tier.token_ratio, 1.0);
        }
    }

    #[test]
    fn perfect_qualification_signal() {
        // All good fixes pass, all bad fixes caught
        let good_ext: Vec<(String, bool)> = (1..=10).map(|i| (format!("task-{i}"), true)).collect();
        let bad_narrow: Vec<(String, bool)> = (1..=5).map(|i| (format!("bad-{i}"), true)).collect();
        let bad_ext: Vec<(String, bool)> = (1..=5).map(|i| (format!("bad-{i}"), false)).collect();
        let r = compute_qualification_report(&[], &[], &good_ext, &bad_narrow, &bad_ext);
        assert_eq!(r.summary.good_recall_extended_gate, 1.0);
        assert_eq!(r.summary.detection_rate_extended, 1.0);
    }

    #[test]
    fn extended_gate_better_than_narrow() {
        let bad_narrow: Vec<(String, bool)> = vec![("b1".into(), true)]; // passes narrow
        let bad_ext: Vec<(String, bool)> = vec![("b1".into(), false)]; // caught by extended
        let r = compute_qualification_report(&[], &[], &[], &bad_narrow, &bad_ext);
        assert!(r.summary.extended_gate_better_precision);
    }

    #[test]
    fn write_reports_create_files() {
        let dir = tempfile::TempDir::new().unwrap();
        let cal = mock_calibration_report();
        write_calibration_report(&cal, dir.path()).unwrap();
        assert!(dir.path().join("calibration_report.json").exists());
    }
}
