//! ClaudeTaskGenerator — production `TaskGenerator` implementation.
//!
//! Calls the Anthropic API via a python3 subprocess to generate LLM-guided
//! improvement tasks. Falls back gracefully when `ANTHROPIC_API_KEY` is absent
//! or the `anthropic` Python module is unavailable.
//!
//! # Security
//! - The API key is read from the environment by the child process; it is NEVER
//!   embedded in source or written to the tempfile script.
//! - `env_clear()` is used on the helper subprocess, then only `ANTHROPIC_API_KEY`
//!   and `PATH` are selectively restored.
//! - No hardcoded credentials anywhere.

use crate::improvement_loop::TaskGenerator;
use std::io::Write;
use std::sync::{Arc, RwLock};
use urace_goals::product_goal::ProductGoal;

/// Real LLM-backed task generator.
///
/// Spawns a python3 helper subprocess that calls the Anthropic API.  When the
/// API key is absent or the `anthropic` module is unavailable the subprocess
/// returns a deterministic fallback script so the loop never stalls.
pub struct ClaudeTaskGenerator {
    /// Anthropic model to use for generation.
    pub model: String,
    /// Current metric value — updated by the caller between cycles so the
    /// prompt stays accurate.
    pub last_metric: Arc<RwLock<f64>>,
}

impl Default for ClaudeTaskGenerator {
    fn default() -> Self {
        ClaudeTaskGenerator {
            model: "claude-haiku-4-5-20251001".into(),
            last_metric: Arc::new(RwLock::new(0.0)),
        }
    }
}

impl ClaudeTaskGenerator {
    /// Create with an explicit model string.
    pub fn new(model: impl Into<String>) -> Self {
        ClaudeTaskGenerator {
            model: model.into(),
            last_metric: Arc::new(RwLock::new(0.0)),
        }
    }

    /// Update the tracked metric value (call after each `MetricSampler::sample`).
    pub fn update_metric(&self, value: f64) {
        if let Ok(mut guard) = self.last_metric.write() {
            *guard = value;
        }
    }
}

impl TaskGenerator for ClaudeTaskGenerator {
    fn generate(&self, product_id: &str, goal: &ProductGoal, cycle: u64) -> (String, String) {
        // Read current metric value.
        let last = self
            .last_metric
            .read()
            .map(|g| *g)
            .unwrap_or(0.0);

        // Check whether the API key is available; return safe no-op if missing.
        let api_key = match std::env::var("ANTHROPIC_API_KEY") {
            Ok(k) if !k.is_empty() => k,
            _ => {
                tracing::warn!(
                    product_id,
                    cycle,
                    "ANTHROPIC_API_KEY not set — using deterministic fallback script"
                );
                return (
                    "claude_generated".into(),
                    fallback_script(product_id, cycle),
                );
            }
        };

        // Build the prompt (no API key embedded here).
        let prompt = build_prompt(product_id, &goal.metric, last, cycle);

        // Write the helper script to a tempfile.
        let helper = match write_helper_script(&self.model, &prompt, cycle) {
            Ok(h) => h,
            Err(e) => {
                tracing::warn!(cycle, "failed to write helper script: {e}");
                return ("claude_generated".into(), fallback_script(product_id, cycle));
            }
        };

        // Spawn python3 to run the helper.  Only ANTHROPIC_API_KEY and PATH are
        // passed — all other parent-env vars are stripped.
        let path_val = std::env::var("PATH").unwrap_or_else(|_| "/usr/bin:/usr/local/bin".into());

        let output = std::process::Command::new("python3")
            .arg(helper.path())
            .env_clear()
            .env("ANTHROPIC_API_KEY", &api_key)
            .env("PATH", &path_val)
            .output();

        let generated_code = match output {
            Ok(out) if out.status.success() => {
                let stdout = String::from_utf8_lossy(&out.stdout).trim().to_string();
                if stdout.is_empty() {
                    tracing::warn!(cycle, "helper script produced empty output — falling back");
                    fallback_script(product_id, cycle)
                } else {
                    stdout
                }
            }
            Ok(out) => {
                let stderr = String::from_utf8_lossy(&out.stderr).trim().to_string();
                tracing::warn!(cycle, stderr = %stderr, "helper script exited non-zero — falling back");
                fallback_script(product_id, cycle)
            }
            Err(e) => {
                tracing::warn!(cycle, "failed to spawn python3: {e} — falling back");
                fallback_script(product_id, cycle)
            }
        };

        ("claude_generated".into(), generated_code)
    }
}

// ── helpers ───────────────────────────────────────────────────────────────────

fn build_prompt(product_id: &str, metric: &str, last_metric: f64, cycle: u64) -> String {
    format!(
        "You are improving product {product_id}. \
         Goal: maximize {metric} (currently at {last_metric:.3}). \
         Cycle {cycle}. \
         Generate a minimal Python script that would improve this metric. \
         Output ONLY the python code, no explanation."
    )
}

fn fallback_script(product_id: &str, cycle: u64) -> String {
    format!(
        "# auto-generated improvement\nprint('improvement cycle {cycle} applied to {product_id}')"
    )
}

/// Write the Anthropic API helper script to a named tempfile.
///
/// Returns the tempfile handle (kept alive so the path remains valid).
fn write_helper_script(
    model: &str,
    prompt: &str,
    cycle: u64,
) -> Result<tempfile::NamedTempFile, std::io::Error> {
    // Escape the prompt for embedding in a Python string literal.
    // We use triple-quoted strings to avoid most escaping, but we still
    // need to handle backslashes and triple-quotes in the prompt itself.
    let safe_prompt = prompt
        .replace('\\', "\\\\")
        .replace("'''", "\\'\\'\\'");

    let fallback_line = format!(
        "print('# auto-generated improvement'); print(\"print('improvement cycle {cycle} applied')\")"
    );
    let script = format!(
        "import os, sys\n\
try:\n\
    import anthropic\n\
    client = anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY', ''))\n\
    msg = client.messages.create(\n\
        model='{model}',\n\
        max_tokens=256,\n\
        messages=[{{\"role\": \"user\", \"content\": '''{safe_prompt}'''}}]\n\
    )\n\
    print(msg.content[0].text)\n\
except Exception as e:\n\
    {fallback_line}\n"
    );

    let mut f = tempfile::NamedTempFile::new()?;
    f.write_all(script.as_bytes())?;
    f.flush()?;
    Ok(f)
}

#[cfg(test)]
mod tests {
    use super::*;
    use urace_goals::product_goal::{GoalDirection, ProductGoal};

    #[test]
    fn returns_fallback_when_no_api_key() {
        // Ensure the env var is absent.
        std::env::remove_var("ANTHROPIC_API_KEY");
        let gen = ClaudeTaskGenerator::default();
        let goal = ProductGoal::new("test_pass_rate", GoalDirection::Maximize, None, 0.001).unwrap();
        let (task_type, code) = gen.generate("prod-test", &goal, 1);
        assert_eq!(task_type, "claude_generated");
        assert!(code.contains("improvement cycle 1"));
    }

    #[test]
    fn update_metric_is_visible() {
        let gen = ClaudeTaskGenerator::default();
        gen.update_metric(0.75);
        let val = *gen.last_metric.read().unwrap();
        assert!((val - 0.75).abs() < 1e-9);
    }

    #[test]
    fn build_prompt_contains_all_fields() {
        let p = build_prompt("my-product", "coverage_pct", 0.65, 3);
        assert!(p.contains("my-product"));
        assert!(p.contains("coverage_pct"));
        assert!(p.contains("0.650"));
        assert!(p.contains("Cycle 3"));
    }

    #[test]
    fn fallback_script_contains_cycle() {
        let s = fallback_script("prod", 7);
        assert!(s.contains("7"));
    }

    #[test]
    fn write_helper_script_creates_valid_file() {
        let f = write_helper_script("claude-haiku-4-5-20251001", "test prompt", 1).unwrap();
        let contents = std::fs::read_to_string(f.path()).unwrap();
        assert!(contents.contains("anthropic"));
        assert!(contents.contains("claude-haiku-4-5-20251001"));
    }
}
