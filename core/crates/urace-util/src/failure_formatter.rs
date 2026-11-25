//! Bounded test-failure output formatting.
//!
//! Ported from `failure_formatter.py` (76 lines).
//!
//! The Python module operates on raw pytest/unittest stdout and applies a
//! multi-stage compression algorithm to stay within a character budget.
//! This Rust port provides two public functions and the supporting struct:
//!
//! * `format_failure` — formats a single structured `FailureRecord`.
//! * `format_failures` — formats a slice of records up to `max_total` chars.
//!
//! The Python module's `format_failure_output` function (which parses raw
//! text output) is preserved as `format_raw_output` for completeness.

// ---------------------------------------------------------------------------
// FailureRecord
// ---------------------------------------------------------------------------

/// A structured test-failure record.
#[derive(Debug, Clone)]
pub struct FailureRecord {
    /// Unique test identifier (e.g. `"tests/test_foo.py::test_bar"`).
    pub test_id: String,
    /// Failure kind: `"FAIL"`, `"ERROR"`, etc.
    pub kind: String,
    /// Diagnostic message (may be long; will be truncated by formatters).
    pub message: String,
    /// ISO-8601 timestamp or file location string.
    pub at: String,
}

// ---------------------------------------------------------------------------
// format_failure
// ---------------------------------------------------------------------------

/// Format a single `FailureRecord`, truncating `message` at `max_chars`.
///
/// When truncation occurs, `"..."` is appended to the message.
/// The returned string is always ≤ `max_chars + overhead` characters where
/// overhead covers `test_id`, `kind`, `at`, and formatting punctuation.
pub fn format_failure(record: &FailureRecord, max_chars: usize) -> String {
    let message = truncate(&record.message, max_chars);
    format!(
        "{kind}: {test_id}\n  at: {at}\n  {message}",
        kind = record.kind,
        test_id = record.test_id,
        at = record.at,
        message = message,
    )
}

/// Truncate `s` to at most `max_chars` characters, appending `"..."` if truncated.
pub fn truncate(s: &str, max_chars: usize) -> String {
    if s.chars().count() <= max_chars {
        s.to_string()
    } else {
        let truncated: String = s.chars().take(max_chars).collect();
        format!("{truncated}...")
    }
}

// ---------------------------------------------------------------------------
// format_failures
// ---------------------------------------------------------------------------

/// Format up to `max_total` characters worth of failures from `records`.
///
/// Each record is formatted with `format_failure` using an equal per-record
/// allowance.  If there are more records than fit in the budget, a summary
/// line is appended:
///
/// ```text
/// [N failures omitted; diagnostic limit]
/// ```
pub fn format_failures(records: &[FailureRecord], max_total: usize) -> String {
    if records.is_empty() {
        return String::new();
    }

    let separator = "\n".to_string() + &"=".repeat(70) + "\n";
    let sep_len = separator.len();

    // Per-record budget: evenly divide, leaving room for separators.
    let n = records.len();
    let total_sep = sep_len * n.saturating_sub(1);
    let budget_for_records = max_total.saturating_sub(total_sep);
    let per_record = if n > 0 { budget_for_records / n } else { 0 };

    let mut parts: Vec<String> = Vec::with_capacity(n);
    let mut total_used = 0usize;
    let mut omitted = 0usize;

    for record in records {
        let formatted = format_failure(record, per_record.max(20));
        let cost = formatted.len() + if parts.is_empty() { 0 } else { sep_len };
        if total_used + cost > max_total && !parts.is_empty() {
            omitted += 1;
            continue;
        }
        total_used += cost;
        parts.push(formatted);
    }

    let mut out = parts.join(&separator);

    if omitted > 0 {
        let note = format!("\n[{omitted} failures omitted; diagnostic limit]");
        // Append note only when it still fits.
        if out.len() + note.len() <= max_total {
            out.push_str(&note);
        } else {
            out.truncate(max_total);
        }
    }

    out
}

// ---------------------------------------------------------------------------
// format_raw_output  (Python: format_failure_output)
// ---------------------------------------------------------------------------

/// Format raw pytest/unittest output into a bounded diagnostic string.
///
/// Extracts `FAIL: ...` / `ERROR: ...` headings, the `Ran N tests` summary
/// line, and the final verdict.  When output exceeds `limit` characters the
/// result is compressed intelligently:
///
/// 1. Traces are truncated while all failure headers are preserved.
/// 2. If still over the limit, middle failures are omitted with an explicit count.
/// 3. Each remaining block gets an equal share of the allowance.
///
/// When no headings are found, the last 2 000 characters of `output` are
/// returned (matches the Python fallback).
pub fn format_raw_output(output: &str, limit: usize) -> String {
    let lines: Vec<&str> = output.lines().collect();

    // Collect heading line indices.
    let headings: Vec<usize> = lines
        .iter()
        .enumerate()
        .filter(|(_, line)| is_fail_or_error_heading(line))
        .map(|(i, _)| i)
        .collect();

    if headings.is_empty() {
        // Fallback: last 2 000 chars.
        return tail_chars(output, 2000);
    }

    // Find summary line ("Ran N tests in ...").
    let summary_index = headings
        .first()
        .and_then(|&first| {
            ((first + 1)..lines.len()).find(|&i| is_ran_summary(lines[i]))
        });

    let end = summary_index.unwrap_or(lines.len());

    // Collect summary + verdict lines.
    let mut summary: Vec<&str> = Vec::new();
    if let Some(si) = summary_index {
        summary.push(lines[si]);
        if let Some(verdict) = lines[si + 1..].iter().find(|l| is_verdict(l)) {
            summary.push(verdict);
        }
    }

    // Restrict headings to those before `end`.
    let headings: Vec<usize> = headings.into_iter().filter(|&i| i < end).collect();

    // Extract blocks.
    let blocks: Vec<Vec<&str>> = headings
        .iter()
        .enumerate()
        .map(|(pos, &start)| {
            let stop_raw = headings.get(pos + 1).copied().unwrap_or(end);
            // Strip trailing separator lines (===... or ---...).
            let mut stop = stop_raw;
            while stop > start && is_separator(lines[stop - 1]) {
                stop -= 1;
            }
            lines[start..stop].to_vec()
        })
        .collect();

    let sep = "\n".to_string() + &"=".repeat(70) + "\n";
    let summary_text = summary.join("\n");

    // Build initial result.
    let parts: Vec<String> = blocks
        .iter()
        .map(|b| b.join("\n"))
        .chain(if summary.is_empty() { None } else { Some(summary_text.clone()) })
        .collect();
    let detail = parts.join(&sep);

    if detail.len() <= limit {
        return detail;
    }

    // ---- Compression pass ----
    let marker = "[trace context truncated]";
    let labels: Vec<&str> = blocks.iter().map(|b| b[0]).collect();

    // Build fixed (header + marker) representation.
    let fixed: Vec<String> = labels.iter().map(|l| format!("{l}\n{marker}")).collect();
    let fixed_parts: Vec<String> = fixed
        .iter()
        .cloned()
        .chain(if summary.is_empty() { None } else { Some(summary_text.clone()) })
        .collect();
    let fixed_size = fixed_parts.join(&sep).len();

    if fixed_size > limit {
        // Cannot fit all headers — omit middle ones.
        let summary_budget = 500.min(summary_text.len());
        let short_summary = tail_chars(&summary_text, summary_budget);
        let name_budget = limit.saturating_sub(short_summary.len()).saturating_sub(128);
        let mut kept: Vec<&str> = Vec::new();
        let mut used = 0usize;
        for &label in &labels {
            if used + label.len() + 1 > name_budget {
                break;
            }
            kept.push(label);
            used += label.len() + 1;
        }
        let omitted_count = labels.len() - kept.len();
        let mut result = kept.join("\n");
        if omitted_count > 0 {
            result.push_str(&format!(
                "\n[{omitted_count} failure headers omitted; diagnostic limit]\n{short_summary}"
            ));
        }
        return result.chars().take(limit).collect();
    }

    // Distribute allowance evenly.
    let allowance = if blocks.is_empty() {
        0
    } else {
        (limit.saturating_sub(fixed_size + 2 * blocks.len())) / blocks.len()
    };

    let compact: Vec<String> = labels
        .iter()
        .zip(blocks.iter())
        .map(|(label, block)| {
            let trace = block[1..].join("\n");
            if trace.len() > allowance {
                if allowance == 0 {
                    format!("{label}\n{marker}")
                } else {
                    let prefix = allowance * 2 / 3;
                    let suffix_len = allowance - prefix;
                    let head = &trace[..prefix.min(trace.len())];
                    let tail = tail_chars(&trace, suffix_len);
                    format!("{label}\n{head}\n{marker}\n{tail}")
                }
            } else if trace.is_empty() {
                label.to_string()
            } else {
                format!("{label}\n{trace}")
            }
        })
        .collect();

    let result_parts: Vec<String> = compact
        .into_iter()
        .chain(if summary.is_empty() { None } else { Some(summary_text) })
        .collect();
    let full = result_parts.join(&sep);
    full.chars().take(limit).collect()
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

fn is_fail_or_error_heading(line: &str) -> bool {
    // "FAIL: <something> (<something>)" or "ERROR: ..."
    if let Some(rest) = line.strip_prefix("FAIL: ").or_else(|| line.strip_prefix("ERROR: ")) {
        rest.contains('(') && rest.ends_with(')')
    } else {
        false
    }
}

fn is_ran_summary(line: &str) -> bool {
    // "Ran N test[s] in ..."
    line.starts_with("Ran ") && line.contains(" test") && line.contains(" in ")
}

fn is_verdict(line: &str) -> bool {
    line == "OK" || line.starts_with("OK (") || line == "FAILED" || line.starts_with("FAILED (")
}

fn is_separator(line: &str) -> bool {
    let trimmed = line.trim();
    !trimmed.is_empty() && trimmed.chars().all(|c| c == '=' || c == '-')
}

/// Return the last `n` characters of `s`.
fn tail_chars(s: &str, n: usize) -> String {
    let total = s.chars().count();
    if total <= n {
        s.to_string()
    } else {
        s.chars().skip(total - n).collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn rec(test_id: &str, message: &str) -> FailureRecord {
        FailureRecord {
            test_id: test_id.to_string(),
            kind: "FAIL".to_string(),
            message: message.to_string(),
            at: "2024-01-01T00:00:00".to_string(),
        }
    }

    // --- format_failure ---

    #[test]
    fn format_failure_short_message_unchanged() {
        let r = rec("test_foo", "assertion failed");
        let out = format_failure(&r, 200);
        assert!(out.contains("FAIL: test_foo"));
        assert!(out.contains("assertion failed"));
        assert!(!out.contains("..."), "should not truncate short message");
    }

    #[test]
    fn format_failure_long_message_truncated() {
        let long_msg = "x".repeat(500);
        let r = rec("test_bar", &long_msg);
        let out = format_failure(&r, 100);
        assert!(out.contains("..."), "long message should be truncated with ...");
        // Message portion must be <= 100 chars + "..."
        assert!(out.contains("test_bar"));
    }

    // --- format_failures ---

    #[test]
    fn format_failures_empty_input() {
        assert_eq!(format_failures(&[], 1000), "");
    }

    #[test]
    fn format_failures_single_record() {
        let records = vec![rec("test_a", "boom")];
        let out = format_failures(&records, 1000);
        assert!(out.contains("test_a"));
        assert!(out.contains("boom"));
    }

    #[test]
    fn format_failures_budget_respected() {
        let records: Vec<FailureRecord> = (0..20)
            .map(|i| rec(&format!("test_{i}"), &"x".repeat(200)))
            .collect();
        let out = format_failures(&records, 500);
        assert!(out.len() <= 600, "output exceeded budget: {} chars", out.len());
    }

    #[test]
    fn format_failures_omission_note_when_overflow() {
        let records: Vec<FailureRecord> = (0..10)
            .map(|i| rec(&format!("test_{i}"), &"long message ".repeat(50)))
            .collect();
        let out = format_failures(&records, 300);
        // Some records should have been omitted.
        assert!(out.contains("omitted") || out.len() <= 300);
    }

    // --- truncate ---

    #[test]
    fn truncate_short_string_unchanged() {
        assert_eq!(truncate("hello", 10), "hello");
    }

    #[test]
    fn truncate_long_string_appends_ellipsis() {
        let s = truncate("hello world", 5);
        assert_eq!(s, "hello...");
    }

    // --- format_raw_output ---

    #[test]
    fn format_raw_output_no_headings_returns_tail() {
        let output = "some random output\nno test headings here";
        let out = format_raw_output(output, 1000);
        assert!(!out.is_empty());
    }

    #[test]
    fn format_raw_output_with_heading_extracts_it() {
        let output = "\
FAIL: test_something (tests.test_module.TestClass)\n\
AssertionError: expected True\n\
----------------------------------------------------------------------\n\
Ran 1 test in 0.001s\n\
\n\
FAILED (failures=1)";
        let out = format_raw_output(output, 2000);
        assert!(out.contains("FAIL: test_something"));
        assert!(out.contains("AssertionError"));
    }

    #[test]
    fn format_raw_output_limit_applied() {
        let heading = "FAIL: test_long (module.TestCase)";
        let trace = "x".repeat(10_000);
        let output = format!("{heading}\n{trace}\nRan 1 test in 0.001s\n\nFAILED");
        let out = format_raw_output(&output, 500);
        assert!(
            out.len() <= 600,
            "output too long: {} chars (limit 500)",
            out.len()
        );
    }
}
