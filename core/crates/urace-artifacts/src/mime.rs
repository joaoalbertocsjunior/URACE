//! MIME type priority calibration and asset validation.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use thiserror::Error;

// ── Errors ────────────────────────────────────────────────────────────────────

#[derive(Debug, Error)]
pub enum MimeError {
    #[error("validation failed: {0}")]
    ValidationFailed(String),
    #[error("content type not UTF-8")]
    NotUtf8,
}

// ── MIME priority calibration (mime_priority.py) ──────────────────────────────

/// Computed MIME priority weights keyed by content-type string.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MimePriorities(pub HashMap<String, f64>);

/// Audit row kinds used for calibration.
const KIND_EQUITY_GRANT: &str = "EQUITY_GRANT";
const KIND_FEATURE_BORROWED: &str = "FEATURE_BORROWED";

/// Scan audit rows and derive normalized `{content_type: weight}` for `local_id`.
///
/// Returns an empty map when no signal is available.
pub fn calibrate_mime_priority(audit_rows: &[serde_json::Value], local_id: &str) -> MimePriorities {
    // Build feature_id → content_type index from EQUITY_GRANT rows.
    let mut ct_index: HashMap<String, String> = HashMap::new();
    for r in audit_rows {
        if r.get("kind").and_then(|v| v.as_str()) == Some(KIND_EQUITY_GRANT) {
            let fid = r
                .get("feature_id")
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .to_owned();
            let ct = r
                .get("content_type")
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .to_owned();
            if !fid.is_empty() && !ct.is_empty() {
                ct_index.insert(fid, ct);
            }
        }
    }

    // Count FEATURE_BORROWED per MIME for this node.
    let mut counts: HashMap<String, u64> = HashMap::new();
    for r in audit_rows {
        if r.get("kind").and_then(|v| v.as_str()) == Some(KIND_FEATURE_BORROWED) {
            let peer = r
                .get("peer_id")
                .or_else(|| r.get("borrower_peer_id"))
                .and_then(|v| v.as_str())
                .unwrap_or("");
            if !local_id.is_empty() && !peer.is_empty() && peer != local_id {
                continue;
            }
            let fid = r.get("feature_id").and_then(|v| v.as_str()).unwrap_or("");
            if let Some(ct) = ct_index.get(fid) {
                *counts.entry(ct.clone()).or_default() += 1;
            }
        }
    }

    // Also seed from own EQUITY_GRANT rows so a new node gets signal.
    for r in audit_rows {
        if r.get("kind").and_then(|v| v.as_str()) == Some(KIND_EQUITY_GRANT) {
            if !local_id.is_empty()
                && r.get("peer_id").and_then(|v| v.as_str()).unwrap_or("") != local_id
            {
                continue;
            }
            let ct = r.get("content_type").and_then(|v| v.as_str()).unwrap_or("");
            if !ct.is_empty() {
                *counts.entry(ct.to_owned()).or_default() += 1;
            }
        }
    }

    if counts.is_empty() {
        return MimePriorities(HashMap::new());
    }

    let total: u64 = counts.values().sum();
    let mut result: Vec<(String, f64)> = counts
        .into_iter()
        .map(|(ct, c)| {
            (
                ct,
                (c as f64 / total as f64 * 1_000_000.0).round() / 1_000_000.0,
            )
        })
        .collect();
    result.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));

    MimePriorities(result.into_iter().collect())
}

/// Return the normalized weight for `content_type` (0.0 – 1.0).
pub fn get_priority_rank(content_type: &str, priorities: &MimePriorities) -> f64 {
    let ct = normalize_ct(content_type);
    *priorities.0.get(&ct).unwrap_or(&0.0)
}

/// Return `true` when MIME weight meets `threshold` or we are in bootstrap mode
/// (fewer than 5 distinct types seen yet).
pub fn should_replicate(content_type: &str, priorities: &MimePriorities, threshold: f64) -> bool {
    if priorities.0.len() < 5 {
        // Bootstrap: replicate everything.
        return true;
    }
    let ct = normalize_ct(content_type);
    *priorities.0.get(&ct).unwrap_or(&0.0) >= threshold
}

fn normalize_ct(ct: &str) -> String {
    ct.to_lowercase()
        .split(';')
        .next()
        .unwrap_or("")
        .trim()
        .to_owned()
}

// ── MIME validation (mime_validator.py) ───────────────────────────────────────

/// Validate `raw_bytes` for `content_type`.
///
/// Returns `Ok(true)` on pass, `Ok(false)` with reason when unvalidated type,
/// `Err(MimeError::ValidationFailed(reason))` on structural failure.
pub fn validate_asset(raw_bytes: &[u8], content_type: &str) -> Result<bool, MimeError> {
    let ct = normalize_ct(content_type);

    if ct.starts_with("image/") {
        return validate_image(raw_bytes).map(|_| true);
    }
    if ct == "text/csv" || ct == "application/csv" {
        return validate_csv(raw_bytes).map(|_| true);
    }
    if ct == "application/pdf" {
        return validate_pdf(raw_bytes).map(|_| true);
    }
    if ct == "application/json" {
        return validate_json(raw_bytes).map(|_| true);
    }
    if matches!(
        ct.as_str(),
        "text/x-python" | "application/x-python" | "text/plain"
    ) {
        return validate_code(raw_bytes).map(|_| true);
    }
    if matches!(
        ct.as_str(),
        "application/zip" | "application/x-zip" | "application/x-zip-compressed"
    ) {
        return validate_zip(raw_bytes).map(|_| true);
    }

    // Unrecognized type — pass through.
    Ok(false)
}

/// Like `validate_asset` but raises on failure.
pub fn validate_asset_strict(raw_bytes: &[u8], content_type: &str) -> Result<(), MimeError> {
    let ct = normalize_ct(content_type);

    if ct.starts_with("image/") {
        return validate_image(raw_bytes);
    }
    if ct == "text/csv" || ct == "application/csv" {
        return validate_csv(raw_bytes);
    }
    if ct == "application/pdf" {
        return validate_pdf(raw_bytes);
    }
    if ct == "application/json" {
        return validate_json(raw_bytes);
    }
    if matches!(
        ct.as_str(),
        "text/x-python" | "application/x-python" | "text/plain"
    ) {
        return validate_code(raw_bytes);
    }
    if matches!(
        ct.as_str(),
        "application/zip" | "application/x-zip" | "application/x-zip-compressed"
    ) {
        return validate_zip(raw_bytes);
    }

    Ok(())
}

fn validate_image(b: &[u8]) -> Result<(), MimeError> {
    if b.len() < 100 {
        return Err(MimeError::ValidationFailed("invalid_image_magic".into()));
    }
    if b.starts_with(b"\x89PNG")
        || b.starts_with(b"\xff\xd8\xff")
        || b.starts_with(b"GIF8")
        || (b.starts_with(b"RIFF") && b.len() >= 12 && &b[8..12] == b"WEBP")
    {
        return Ok(());
    }
    Err(MimeError::ValidationFailed("invalid_image_magic".into()))
}

fn validate_csv(b: &[u8]) -> Result<(), MimeError> {
    let text = String::from_utf8_lossy(b);
    let rows: Vec<&str> = text.lines().filter(|l| !l.trim().is_empty()).collect();
    if rows.len() < 2 {
        return Err(MimeError::ValidationFailed("csv_too_few_rows".into()));
    }
    let col_counts: std::collections::HashSet<usize> =
        rows.iter().map(|r| r.split(',').count()).collect();
    if col_counts.len() > 1 {
        return Err(MimeError::ValidationFailed(
            "csv_inconsistent_columns".into(),
        ));
    }
    Ok(())
}

fn validate_pdf(b: &[u8]) -> Result<(), MimeError> {
    if !b.starts_with(b"%PDF-") {
        return Err(MimeError::ValidationFailed("invalid_pdf_magic".into()));
    }
    if !b.windows(2).any(|w| w == b"BT") {
        return Err(MimeError::ValidationFailed("pdf_no_text_layer".into()));
    }
    Ok(())
}

fn validate_json(b: &[u8]) -> Result<(), MimeError> {
    match serde_json::from_slice::<serde_json::Value>(b) {
        Err(_) => Err(MimeError::ValidationFailed("json_invalid".into())),
        Ok(v) => {
            if (v.is_object() && v.as_object().map_or(true, |m| m.is_empty()))
                || (v.is_array() && v.as_array().map_or(true, |a| a.is_empty()))
            {
                return Err(MimeError::ValidationFailed("json_empty".into()));
            }
            Ok(())
        }
    }
}

fn validate_code(b: &[u8]) -> Result<(), MimeError> {
    let text =
        std::str::from_utf8(b).map_err(|_| MimeError::ValidationFailed("code_not_utf8".into()))?;
    let non_blank = text.lines().filter(|l| !l.trim().is_empty()).count();
    if non_blank < 3 {
        return Err(MimeError::ValidationFailed("code_too_short".into()));
    }
    Ok(())
}

fn validate_zip(b: &[u8]) -> Result<(), MimeError> {
    if !b.starts_with(b"PK\x03\x04") {
        return Err(MimeError::ValidationFailed("invalid_zip_magic".into()));
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn make_rows(local_id: &str) -> Vec<serde_json::Value> {
        vec![
            json!({"kind": "EQUITY_GRANT", "feature_id": "f1", "content_type": "image/png", "peer_id": local_id}),
            json!({"kind": "FEATURE_BORROWED", "feature_id": "f1", "peer_id": local_id}),
        ]
    }

    #[test]
    fn calibrate_produces_weights() {
        let rows = make_rows("peer-1");
        let p = calibrate_mime_priority(&rows, "peer-1");
        assert!(p.0.contains_key("image/png"));
    }

    #[test]
    fn bootstrap_mode_replicates_all() {
        let p = MimePriorities(HashMap::new());
        assert!(should_replicate("image/png", &p, 0.05));
    }

    #[test]
    fn valid_png_passes() {
        let mut b = vec![0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a];
        b.extend_from_slice(&[0u8; 100]);
        assert!(validate_asset(&b, "image/png").unwrap());
    }

    #[test]
    fn invalid_json_fails() {
        let err = validate_asset_strict(b"not json", "application/json");
        assert!(err.is_err());
    }

    #[test]
    fn valid_json_passes() {
        validate_asset_strict(br#"{"key":"value"}"#, "application/json").unwrap();
    }
}
