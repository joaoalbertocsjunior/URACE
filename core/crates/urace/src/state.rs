//! R-9: URACE runtime state — loaded from state_dir/state.json.
//!
//! Security note: state files are gitignored — never commit state/state.json.
//! All writes use atomic_write to prevent partial-write corruption.

use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::HashMap;
use std::path::Path;

/// Runtime state serialised to `<state_dir>/state.json`.
///
/// Contains source records, authority config, and runtime constraints.
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct RuntimeState {
    pub sources: HashMap<String, Value>,
    pub authority: HashMap<String, Value>,
    pub constraints: Vec<String>,
}

impl RuntimeState {
    /// Load state from `<state_dir>/state.json`.
    /// Returns a default empty state if the file does not exist yet.
    pub fn load(state_dir: &Path) -> Result<Self> {
        let path = state_dir.join("state.json");
        if !path.exists() {
            return Ok(RuntimeState::default());
        }
        let raw = std::fs::read_to_string(&path)
            .with_context(|| format!("reading state from {}", path.display()))?;
        let state: RuntimeState = serde_json::from_str(&raw)
            .with_context(|| format!("parsing state from {}", path.display()))?;
        Ok(state)
    }

    /// Save state to `<state_dir>/state.json` using an atomic write.
    ///
    /// Creates `state_dir` if it does not exist.
    pub fn save(&self, state_dir: &Path) -> Result<()> {
        std::fs::create_dir_all(state_dir)
            .with_context(|| format!("creating state dir {}", state_dir.display()))?;
        let path = state_dir.join("state.json");
        let json = serde_json::to_string_pretty(self)?;
        // Write to a temp file then rename — atomic on POSIX.
        let tmp_path = state_dir.join("state.json.tmp");
        std::fs::write(&tmp_path, json.as_bytes())
            .with_context(|| format!("writing tmp state to {}", tmp_path.display()))?;
        std::fs::rename(&tmp_path, &path)
            .with_context(|| format!("renaming tmp state to {}", path.display()))?;
        Ok(())
    }

    /// Add or replace a source entry.
    pub fn set_source(&mut self, id: &str, record: Value) {
        self.sources.insert(id.to_string(), record);
    }

    /// Remove a source entry. Returns true if it existed.
    pub fn remove_source(&mut self, id: &str) -> bool {
        self.sources.remove(id).is_some()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    #[test]
    fn test_load_missing_returns_default() {
        let dir = TempDir::new().unwrap();
        let state = RuntimeState::load(dir.path()).unwrap();
        assert!(state.sources.is_empty());
        assert!(state.constraints.is_empty());
    }

    #[test]
    fn test_save_and_reload() {
        let dir = TempDir::new().unwrap();
        let mut state = RuntimeState::default();
        state.set_source("test-id", serde_json::json!({"kind": "directory", "path": "/tmp"}));
        state.constraints.push("test-constraint".into());
        state.save(dir.path()).unwrap();

        let loaded = RuntimeState::load(dir.path()).unwrap();
        assert!(loaded.sources.contains_key("test-id"));
        assert_eq!(loaded.constraints, vec!["test-constraint"]);
    }

    #[test]
    fn test_remove_source() {
        let mut state = RuntimeState::default();
        state.set_source("x", serde_json::json!({}));
        assert!(state.remove_source("x"));
        assert!(!state.remove_source("x"));
    }
}
